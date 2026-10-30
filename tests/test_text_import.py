"""Synthetic byte fixtures: CRLF opt-in never changes binary/content validation."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'app/RoboPenalty'))
from portability.downloads import digest
from portability.text_import import TEXT_POLICY, canonical_bytes, ResourceMismatch, validate_text_policy
from portability.local_import import scan, import_local, receipt_status
from portability.install_resources import load_plan


class TextImportTests(unittest.TestCase):
    def setUp(self):
        parent=ROOT/'tests/.tmp';parent.mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=parent);self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name);self.source=self.base/'source';self.source.mkdir()
        self.root=self.base/'bundle';self.root.mkdir()
        self.data={'file.py':b'alpha\nbeta\n','robot.xml':b'<robot>\n</robot>\n','config.yaml':b'gain: 1\n',
                   'policy.onnx':b'ONNX\x00\r\n\xff','motion.npz':b'PK\x00\n\xff'}
        entries=[]
        for name,data in self.data.items():
            binary=name.endswith(('.onnx','.npz'))
            e=dict(target='RoboNaldo_Deploy/'+name,sha256=digest(data),authorization='pending',
                   category=('onnx' if name.endswith('.onnx') else 'motion_npz') if binary else 'official_original',
                   source=dict(sha256=digest(b'official base\n')))
            if not binary:e['local_import_text']=dict(TEXT_POLICY)
            entries.append(e);(self.source/name).write_bytes(data)
        self.plan=dict(runtime_profile_sha256='a'*64,resources=entries)
        self.entry=entries[0]

    def crlf(self):
        for e in self.plan['resources']:
            if 'local_import_text' in e:
                name=e['target'].split('/',1)[1]
                (self.source/name).write_bytes(self.data[name].replace(b'\n',b'\r\n'))

    def test_exact_lf_bytes_unchanged(self):
        self.assertEqual(canonical_bytes(self.entry,self.data['file.py']),(self.data['file.py'],'none'))

    def test_crlf_only_authorized(self):
        self.assertEqual(canonical_bytes(self.entry,b'alpha\r\nbeta\r\n'),(self.data['file.py'],'crlf-to-lf'))

    def test_mixed_lf_crlf_is_only_paired_replacement(self):
        self.assertEqual(canonical_bytes(self.entry,b'alpha\nbeta\r\n')[0],self.data['file.py'])

    def test_xml_yaml_explicit_opt_in(self):
        for e in self.plan['resources'][1:3]:
            name=e['target'].split('/',1)[1]
            self.assertEqual(canonical_bytes(e,self.data[name].replace(b'\n',b'\r\n'))[0],self.data[name])

    def test_spaces_tabs_content_changes_rejected(self):
        for data in (b'alpha \r\nbeta\r\n',b'alpha\r\n beta\r\n',b'alpha\r\n\tbeta\r\n',b'Alpha\r\nbeta\r\n'):
            with self.subTest(data=data),self.assertRaises(ResourceMismatch):canonical_bytes(self.entry,data)

    def test_utf8_bom_not_removed(self):
        with self.assertRaises(ResourceMismatch):canonical_bytes(self.entry,b'\xef\xbb\xbfalpha\r\nbeta\r\n')

    def test_utf16_not_transcoded(self):
        with self.assertRaises(ResourceMismatch):canonical_bytes(self.entry,'alpha\r\nbeta\r\n'.encode('utf-16'))

    def test_latin1_not_transcoded(self):
        e={**self.entry,'sha256':digest('café\n'.encode('utf-8'))}
        with self.assertRaises(ResourceMismatch):canonical_bytes(e,'café\r\n'.encode('latin-1'))

    def test_bare_cr_rejected(self):
        with self.assertRaises(ResourceMismatch):canonical_bytes(self.entry,b'alpha\rbeta\r')

    def test_missing_extra_eof_newline_rejected(self):
        for data in (b'alpha\nbeta',b'alpha\nbeta\n\n'):
            with self.subTest(data=data),self.assertRaises(ResourceMismatch):canonical_bytes(self.entry,data)

    def test_unlisted_text_does_not_normalize(self):
        e={k:v for k,v in self.entry.items() if k!='local_import_text'}
        with self.assertRaises(ResourceMismatch):canonical_bytes(e,b'alpha\r\nbeta\r\n')
        self.assertEqual(canonical_bytes(e,self.data['file.py'])[1],'none')

    def test_unknown_policy_rejected(self):
        for policy in ({**TEXT_POLICY,'strip_whitespace':True},{**TEXT_POLICY,'encoding':'utf-16'},True,{}):
            with self.subTest(policy=policy),self.assertRaises(ValueError):canonical_bytes({**self.entry,'local_import_text':policy},self.data['file.py'])

    def test_exact_binary_crlf_preserved(self):
        e=self.plan['resources'][3]
        self.assertEqual(canonical_bytes(e,self.data['policy.onnx']),(self.data['policy.onnx'],'none'))

    def test_binary_newline_mutations_rejected(self):
        for e in self.plan['resources'][3:]:
            name=e['target'].split('/',1)[1];data=self.data[name]
            mutated=data.replace(b'\r\n',b'\n') if b'\r\n' in data else data.replace(b'\n',b'\r\n')
            with self.subTest(name=name),self.assertRaises(ResourceMismatch):canonical_bytes(e,mutated)

    def test_binary_opt_in_rejected_even_for_exact_bytes(self):
        for e in self.plan['resources'][3:]:
            e={**e,'local_import_text':dict(TEXT_POLICY)}
            with self.assertRaises(ValueError):canonical_bytes(e,self.data[e['target'].split('/',1)[1]])

    def test_unreviewed_extension_rejected(self):
        with self.assertRaises(ValueError):validate_text_policy({**self.entry,'target':'RoboNaldo_Deploy/file.json'})

    def test_import_crlf_writes_canonical_and_preserves_source(self):
        self.crlf();before={p.name:p.read_bytes() for p in self.source.iterdir()}
        result=import_local(self.source,self.root,self.plan)
        self.assertEqual(result['normalized_files'],3);self.assertTrue(result['receipt']['ready'])
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.source.iterdir()})
        for e in self.plan['resources']:
            self.assertEqual(digest((self.root/'app'/e['target']).read_bytes()),e['sha256'])
        receipt=json.loads((self.root/'.cache/local_import.json').read_text())
        self.assertEqual(len(receipt['normalizations']),3)
        self.assertEqual(receipt['source_resources'][self.entry['target']],digest(before['file.py']))
        self.assertNotIn(str(self.source),json.dumps(receipt))

    def test_existing_lf_copy_still_imports(self):
        result=import_local(self.source,self.root,self.plan)
        self.assertEqual(result['normalized_files'],0);self.assertTrue(result['receipt']['ready'])

    def test_altered_content_stops_before_resource_writes(self):
        self.crlf();(self.source/'file.py').write_bytes(b'alpha \r\nbeta\r\n')
        self.assertFalse(import_local(self.source,self.root,self.plan)['compatible'])
        self.assertFalse((self.root/'app').exists())

    def test_installed_crlf_tamper_invalidates_receipt(self):
        import_local(self.source,self.root,self.plan)
        (self.root/'app'/self.entry['target']).write_bytes(b'alpha\r\nbeta\r\n')
        self.assertFalse(receipt_status(self.root,self.plan)['ready'])

    def test_wrong_existing_destination_is_never_repaired_silently(self):
        p=self.root/'app'/self.entry['target'];p.parent.mkdir(parents=True);p.write_bytes(b'alpha\r\nbeta\r\n')
        with self.assertRaises(ValueError):import_local(self.source,self.root,self.plan)
        self.assertEqual(p.read_bytes(),b'alpha\r\nbeta\r\n')

    def test_notices_keep_original_crlf_bytes(self):
        self.crlf();notice=b'Example attribution\r\n';(self.source/'NOTICE').write_bytes(notice)
        import_local(self.source,self.root,self.plan)
        receipt=json.loads((self.root/'.cache/local_import.json').read_text())
        self.assertTrue(receipt['notices'])
        for target in receipt['notices']:self.assertEqual((self.root/target).read_bytes(),notice)

    def test_legacy_receipt_without_optional_provenance_remains_valid(self):
        import_local(self.source,self.root,self.plan);path=self.root/'.cache/local_import.json'
        receipt=json.loads(path.read_text());receipt.pop('source_resources');receipt.pop('normalizations')
        path.write_text(json.dumps(receipt))
        self.assertTrue(receipt_status(self.root,self.plan)['ready'])

    def test_source_content_changes_between_scan_and_read_are_rejected(self):
        real_scan=scan
        def changed(source,plan):
            result=real_scan(source,plan);(self.source/'file.py').write_bytes(b'changed\n');return result
        with patch('portability.local_import.scan',side_effect=changed),self.assertRaises(ValueError):
            import_local(self.source,self.root,self.plan)
        self.assertFalse((self.root/'app').exists())

    def test_lf_and_crlf_imports_have_identical_target_bytes(self):
        import_local(self.source,self.root,self.plan);self.crlf();other=self.base/'other';other.mkdir()
        import_local(self.source,other,self.plan)
        for e in self.plan['resources']:
            self.assertEqual((self.root/'app'/e['target']).read_bytes(),(other/'app'/e['target']).read_bytes())

    def test_real_manifest_has_24_opt_ins_two_strict_binaries_and_pending_rights(self):
        plan=load_plan();entries=[e for e in plan['resources'] if e['authorization']=='pending']
        self.assertEqual(len(entries),26)
        self.assertEqual(sum(validate_text_policy(e) for e in entries),24)
        binaries=[e for e in entries if e['category'] in ('onnx','motion_npz')]
        self.assertEqual(len(binaries),2);self.assertTrue(all('local_import_text' not in e for e in binaries))


if __name__=='__main__':unittest.main(verbosity=2)
