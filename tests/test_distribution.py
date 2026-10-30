"""Package-only tests. No Deploy, physics execution, microphone or downloads."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT/'app/RoboPenalty'
sys.path.insert(0, str(APP))
from portability.diagnose import inspect_resources, report
from portability.bundle import provenance, licensing, inspect_inventory


class DistributionTests(unittest.TestCase):
    def temporary(self):
        folder = ROOT/'tests/.tmp'
        folder.mkdir(exist_ok=True)
        return tempfile.TemporaryDirectory(dir=folder)

    def fixture(self, root, data=b'x=1\n', name='a.py'):
        root = Path(root)
        path = root/'RoboNaldo_Deploy'/name
        path.parent.mkdir(parents=True)
        path.write_bytes(data)
        profile = root/'profile.json'
        profile.write_text(json.dumps(dict(version=1, files=[dict(root='RoboNaldo_Deploy', path=name,
            sha256=hashlib.sha256(data).hexdigest())])), encoding='utf-8')
        return path, profile

    def test_all_26_pending_resources_are_reported(self):
        r = inspect_resources()
        self.assertEqual(len(r['files']), 104)
        from portability.local_import import receipt_status
        imported=receipt_status()['ready']
        self.assertEqual(r['ready'], imported)
        self.assertEqual(len(r['problems']), 0 if imported else 26)
        self.assertTrue(all(x['kind']=='missing' and x['resource'].startswith('RoboNaldo_Deploy/') for x in r['problems']))

    def test_all_38_unitree_hashes_match(self):
        rows = [x for x in inspect_resources()['files'] if x['resource'].startswith('unitree_mujoco/')]
        self.assertEqual(len(rows), 38)
        self.assertTrue(all(x['status']=='ok' for x in rows))
        self.assertTrue((ROOT/'app/unitree_mujoco/LICENSE').read_text().startswith('BSD 3-Clause License'))

    def test_historical_209_manifest_unchanged(self):
        p = APP/'portability'
        old = (p/'external_manifest.json').read_bytes()
        runtime = json.loads((p/'runtime_profile.json').read_text())
        self.assertEqual(len(json.loads(old)['files']), 209)
        self.assertEqual(hashlib.sha256(old).hexdigest(), runtime['historical_manifest_sha256'])

    def test_all_37_calibrations_remain_exact(self):
        p = APP/'phase8c'; catalog=json.loads((p/'catalog_v1.json').read_text());seen=set()
        for entry in catalog['actions'].values():
            for name,digest in [(entry['probe'], entry['sha256']), *[(x['source'], x['sha256']) for x in entry['grid']]]:
                self.assertEqual(hashlib.sha256((p/name).read_bytes()).hexdigest(), digest)
                seen.add(name)
        self.assertEqual(len(seen), 37)
        self.assertEqual(len(list((p/'results').rglob('*.json'))), 37)

    def test_only_reviewed_content_in_deploy_folder(self):
        files = sorted(p.relative_to(ROOT/'app/RoboNaldo_Deploy').as_posix()
                       for p in (ROOT/'app/RoboNaldo_Deploy').rglob('*') if p.is_file())
        from portability.install_resources import load_plan
        plan=load_plan()
        permitted={'README_PENDING.md','LICENSE-Unitree-ROS.txt'}
        permitted.update(e['target'].split('/',1)[1] for e in plan['resources'] if e['authorization']!='pending')
        from portability.local_import import receipt_status
        imported=receipt_status()['ready']
        if imported:
            permitted.update(e['target'].split('/',1)[1] for e in plan['resources'])
        self.assertEqual(set(files),permitted)
        for entry in plan['resources']:
            if entry['authorization']=='pending':self.assertEqual((ROOT/'app'/entry['target']).exists(), imported)

    def test_no_nested_git_or_models(self):
        self.assertFalse(any(p.name=='.git' for p in (ROOT/'app').rglob('*')))
        reviewed=json.loads((ROOT/'docs/distribution_inventory.json').read_text())['files']
        self.assertFalse([r for r in reviewed if r['path'].lower().endswith(('.onnx','.npz'))])
        self.assertFalse([r for r in reviewed if r['path'].lower().endswith('.zip')])

    def test_provenance_needs_no_git(self):
        with patch('subprocess.run', side_effect=AssertionError('Git must not run')):
            self.assertTrue(provenance()['ready'])
            from portability.local_import import receipt_status
            self.assertEqual(len(inspect_resources()['problems']), 0 if receipt_status()['ready'] else 26)

    def test_pending_license_is_explicit(self):
        r=licensing()
        self.assertFalse(r['resolved'])
        self.assertEqual(r['pending'], ['RoboNaldo_Deploy'])

    def test_resource_only_does_not_check_python_packages(self):
        with patch('portability.diagnose.inspect_packages', side_effect=AssertionError('Package check forbidden')):
            r=report(resources_only=True)
        self.assertFalse(r['distribution_ready'])
        self.assertFalse(r['python']['checked'])

    def test_missing_files_are_not_fail_fast(self):
        with self.temporary() as folder:
            file,profile=self.fixture(folder)
            raw=json.loads(profile.read_text());raw['files'].append({**raw['files'][0], 'path':'b.py'})
            profile.write_text(json.dumps(raw));file.unlink()
            self.assertEqual(len(inspect_resources(profile,folder,False)['problems']),2)

    def test_crlf_is_rejected_without_rewriting(self):
        with self.temporary() as folder:
            file,profile=self.fixture(folder);file.write_bytes(b'x=1\r\n')
            result=inspect_resources(profile,folder,False)
            self.assertFalse(result['ready']);self.assertEqual(result['problems'][0]['kind'],'line_endings')
            self.assertEqual(file.read_bytes(),b'x=1\r\n')

    def test_binary_change_is_rejected(self):
        with self.temporary() as folder:
            file,profile=self.fixture(folder,b'\x00a\nb','a.onnx');file.write_bytes(b'\x00a\r\nb')
            self.assertEqual(inspect_resources(profile,folder,False)['problems'][0]['kind'],'different')

    def test_paths_and_case_insensitive_duplicates(self):
        with self.temporary() as folder:
            file,profile=self.fixture(folder)
            raw=json.loads(profile.read_text());raw['files'] += [dict(raw['files'][0]),{**raw['files'][0],'path':'../outside'}]
            profile.write_text(json.dumps(raw))
            self.assertEqual(sum(x['kind']=='unsafe_path_or_duplicate' for x in inspect_resources(profile,folder,False)['problems']),2)

    def test_wrong_provenance_is_rejected(self):
        with self.temporary() as folder:
            folder=Path(folder);profile=APP/'portability/runtime_profile.json'
            raw=json.loads((APP/'portability/distribution_profile.json').read_text());raw['roots']['unitree_mujoco']['commit']='0'*40
            m=folder/'metadata.json';m.write_text(json.dumps(raw))
            self.assertFalse(provenance(profile,m)['ready'])

    def test_inventory_detects_changed_bytes(self):
        with self.temporary() as folder:
            folder=Path(folder);(folder/'docs').mkdir();(folder/'a.txt').write_bytes(b'wrong')
            (folder/'docs/distribution_inventory.json').write_text(json.dumps(dict(version=1,files=[dict(path='a.txt',sha256=hashlib.sha256(b'right').hexdigest())])))
            self.assertFalse(inspect_inventory(folder)['ready'])

    def test_distribution_inventory_matches(self):
        self.assertTrue(inspect_inventory()['ready'])

    def test_unchanged_copies_match_their_source_hashes(self):
        rows=json.loads((ROOT/'docs/copied_files.json').read_text())['files']
        for row in rows:
            if row['status']=='unchanged':
                self.assertEqual(hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest(),row['source_sha256'],row['path'])

    def test_all_application_python_parses(self):
        for path in APP.rglob('*.py'):
            ast.parse(path.read_text(encoding='utf-8-sig'),filename=path.relative_to(ROOT).as_posix())


if __name__=='__main__':
    unittest.main(verbosity=2)
