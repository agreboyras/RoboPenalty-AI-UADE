"""Local import behavior with synthetic bytes; no external resource payloads."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'app/RoboPenalty'))
from portability.local_import import scan, import_local, receipt_status
from portability.downloads import digest


class LocalImportTests(unittest.TestCase):
    def setUp(self):
        parent = ROOT/'tests/.tmp'
        parent.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base/'arbitrary source name'
        self.source.mkdir()
        self.root = self.base/'bundle'
        self.root.mkdir()
        self.payload = {'unchanged.py': b'common\n', 'modified.py': b'adapted\n', 'added.py': b'own addition\n'}
        categories = ['official_original', 'tp07_modified', 'tp07_addition']
        self.plan = dict(runtime_profile_sha256='a'*64, resources=[dict(target='RoboNaldo_Deploy/'+name,
            sha256=digest(data), category=category, authorization='pending', source=dict(sha256=digest(b'official\n')))
            for (name,data),category in zip(self.payload.items(), categories)])
        for name,data in self.payload.items():
            (self.source/name).write_bytes(data)

    def test_arbitrary_directory_adapted(self):
        self.assertTrue(scan(self.source, self.plan)['compatible'])

    def test_official_recognized_but_not_imported(self):
        (self.source/'modified.py').write_bytes(b'official\n')
        (self.source/'added.py').unlink()
        result=import_local(self.source, self.root, self.plan)
        self.assertEqual(result['kind'], 'official-compatible')
        self.assertFalse(list(self.root.rglob('*.py')))

    def test_reports_every_missing_file(self):
        for p in self.source.iterdir(): p.unlink()
        self.assertEqual(sum(r['status']=='missing' for r in scan(self.source,self.plan)['files']),3)

    def test_crlf_rejected_unchanged(self):
        p=self.source/'modified.py';p.write_bytes(b'adapted\r\n')
        self.assertIn('different',[r['status'] for r in scan(self.source,self.plan)['files']])
        self.assertFalse(import_local(self.source,self.root,self.plan)['compatible'])
        self.assertEqual(p.read_bytes(),b'adapted\r\n')

    def test_success_notices_and_receipt_no_source_path(self):
        (self.source/'LICENSE').write_bytes(b'example notice\n')
        result=import_local(self.source,self.root,self.plan)
        self.assertTrue(result['receipt']['ready'])
        raw=(self.root/'.cache/local_import.json').read_text()
        self.assertNotIn(str(self.source),raw)
        self.assertTrue(json.loads(raw)['notices'])
        self.assertTrue(receipt_status(self.root,self.plan)['ready'])

    def test_repeat_import_resumes(self):
        import_local(self.source,self.root,self.plan)
        self.assertTrue(import_local(self.source,self.root,self.plan)['receipt']['ready'])

    def test_wrong_destination_no_overwrite_no_partial_copy(self):
        p=self.root/'app/RoboNaldo_Deploy/modified.py';p.parent.mkdir(parents=True);p.write_bytes(b'wrong')
        with self.assertRaises(ValueError): import_local(self.source,self.root,self.plan)
        self.assertFalse((p.parent/'unchanged.py').exists())
        self.assertEqual(p.read_bytes(),b'wrong')

    def test_changed_resource_invalidates_receipt(self):
        import_local(self.source,self.root,self.plan)
        (self.root/'app/RoboNaldo_Deploy/modified.py').write_bytes(b'wrong')
        self.assertFalse(receipt_status(self.root,self.plan)['ready'])

    def test_changed_notice_invalidates_receipt(self):
        (self.source/'NOTICE').write_bytes(b'notice')
        import_local(self.source,self.root,self.plan)
        receipt=json.loads((self.root/'.cache/local_import.json').read_text())
        (self.root/next(iter(receipt['notices']))).write_bytes(b'wrong')
        self.assertFalse(receipt_status(self.root,self.plan)['ready'])

    def test_changed_profile_invalidates_receipt(self):
        import_local(self.source,self.root,self.plan)
        self.plan['runtime_profile_sha256']='b'*64
        self.assertFalse(receipt_status(self.root,self.plan)['ready'])

    def test_overlap_rejected(self):
        with self.assertRaises(ValueError): import_local(self.source,self.source,self.plan)

    def test_no_network_and_source_unchanged(self):
        before={p.name:p.read_bytes() for p in self.source.iterdir()}
        with patch('socket.socket',side_effect=AssertionError('No network')):
            import_local(self.source,self.root,self.plan)
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.source.iterdir()})

    def test_missing_receipt_never_enables_execution(self):
        self.assertFalse(receipt_status(self.root,self.plan)['ready'])

    def test_malformed_receipt_is_diagnostic_not_crash(self):
        p=self.root/'.cache/local_import.json';p.parent.mkdir()
        for value in ([],dict(notices=[]),dict(notices=None)):
            p.write_text(json.dumps(value))
            self.assertFalse(receipt_status(self.root,self.plan)['ready'])

    def test_profile_outputs_and_notice_bytes_never_rewritten(self):
        (self.source/'README.md').write_bytes(b'original attribution\r\n')
        result=import_local(self.source,self.root,self.plan)
        self.assertTrue(result['receipt']['ready'])
        receipt=json.loads((self.root/'.cache/local_import.json').read_text())
        for target in receipt['notices']:
            self.assertEqual((self.root/target).read_bytes(),b'original attribution\r\n')

    def readiness(self, external, local):
        from portability.diagnose import report
        with patch('portability.diagnose.inspect_resources',return_value=dict(ready=external)), \
             patch('portability.diagnose.inspect_inventory',return_value=dict(ready=True)), \
             patch('portability.diagnose.inspect_packages',return_value=dict(ready=True)), \
             patch('portability.diagnose.licensing',return_value=dict(resolved=False)), \
             patch('portability.local_import.receipt_status',return_value=dict(ready=local)):
            return report()

    def test_missing_resource_blocks_even_with_receipt(self):
        self.assertFalse(self.readiness(False,True)['execution_ready'])

    def test_all_resources_without_receipt_do_not_enable(self):
        self.assertFalse(self.readiness(True,False)['execution_ready'])

    def test_local_execution_does_not_resolve_distribution_rights(self):
        r=self.readiness(True,True)
        self.assertTrue(r['execution_ready'])
        self.assertFalse(r['distribution_ready'])


if __name__=='__main__': unittest.main(verbosity=2)
