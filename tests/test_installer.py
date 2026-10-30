"""Offline HTTPS/atomic/reconstruction tests use synthetic, owned bytes only."""
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'app/RoboPenalty'))
from portability.downloads import (canonical_url,validate_source,fetch_verified,download_atomic,
    atomic_write,destination,IntegrityError,DownloadError,PermissionPending,NoRedirect)
from portability.install_resources import load_plan,install_authorized,installation_lock
from portability.reconstruction import reconstruct,from_reviewed_pair,recipe_from_pair,apply_recipe


def source(data=b'owned test bytes'):
    repo='unitreerobotics/unitree_ros';rev='38a9b00ecbff0b70e85a7627eb9c65db9a2341f7'
    return dict(repository=repo,revision=rev,path='LICENSE',url=canonical_url(repo,rev,'LICENSE'),
                sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))


class Response(io.BytesIO):
    status=200
    def __init__(self,data,url):super().__init__(data);self.url=url
    def geturl(self):return self.url


class InstallerTests(unittest.TestCase):
    def folder(self):
        p=ROOT/'tests/.tmp';p.mkdir(exist_ok=True)
        return tempfile.TemporaryDirectory(dir=p)
    def opener(self,data):return lambda url,timeout:Response(data,url)

    def test_valid_download_is_atomic_and_exact(self):
        with self.folder() as folder:
            src=source();result=download_atomic(src,folder,'a.bin',authorization='BSD-3-Clause',opener=self.opener(b'owned test bytes'))
            self.assertEqual(result,'installed');self.assertEqual((Path(folder)/'a.bin').read_bytes(),b'owned test bytes')
            self.assertFalse(list(Path(folder).glob('*.part')))

    def test_cached_resource_sends_no_request(self):
        with self.folder() as folder:
            src=source();atomic_write(folder,'a.bin',b'owned test bytes',src['sha256'])
            with patch('portability.downloads.open_https',side_effect=AssertionError):
                self.assertEqual(download_atomic(src,folder,'a.bin',authorization='BSD-3-Clause',opener=lambda *a: self.fail('request')),'cached')

    def test_permission_gate_precedes_network(self):
        with self.folder() as folder:
            with self.assertRaises(PermissionPending):download_atomic(source(),folder,'a.bin',authorization='pending',opener=lambda *a:self.fail('request'))
            self.assertFalse((Path(folder)/'a.bin').exists())

    def test_wrong_hash_is_rejected_without_file(self):
        with self.folder() as folder:
            with self.assertRaisesRegex(IntegrityError,'SHA-256 mismatch'):
                download_atomic(source(),folder,'a.bin',authorization='BSD-3-Clause',opener=self.opener(b'X'*source()['bytes']))
            self.assertFalse((Path(folder)/'a.bin').exists())

    def test_incomplete_response_retries_then_fails(self):
        calls=[]
        def opened(url,timeout):calls.append(url);return Response(b'cut',url)
        with self.assertRaises(DownloadError):fetch_verified(source(),opener=opened,delay=lambda _:None)
        self.assertEqual(len(calls),3)

    def test_network_recovery(self):
        calls=[]
        def opened(url,timeout):
            calls.append(url)
            if len(calls)<3:raise OSError('simulated offline')
            return Response(b'owned test bytes',url)
        self.assertEqual(fetch_verified(source(),opener=opened,delay=lambda _:None),b'owned test bytes')
        self.assertEqual(len(calls),3)

    def test_oversized_response_is_rejected(self):
        with self.assertRaises(IntegrityError):fetch_verified(source(),opener=self.opener(b'owned test bytesEXTRA'))

    def test_redirected_final_url_is_rejected(self):
        with self.assertRaises(DownloadError):fetch_verified(source(),opener=lambda u,t:Response(b'owned test bytes','https://untrusted.invalid/'))

    def test_redirect_handler_rejects_before_following(self):
        with self.assertRaises(DownloadError):NoRedirect().redirect_request(None,None,302,'redirect',{},'https://untrusted.invalid/')

    def test_unknown_host_or_http_rejected(self):
        for url in ('http://raw.githubusercontent.com/x','https://untrusted.invalid/x','https://raw.githubusercontent.com@untrusted.invalid/x'):
            with self.assertRaises(ValueError):validate_source({**source(),'url':url})

    def test_main_is_not_a_revision(self):
        with self.assertRaises(ValueError):canonical_url('unitreerobotics/unitree_ros','main','LICENSE')

    def test_unknown_repository_is_rejected(self):
        with self.assertRaises(ValueError):canonical_url('someone/else','0'*40,'LICENSE')

    def test_destination_traversal_and_windows_paths_rejected(self):
        with self.folder() as folder:
            for path in ('../escape','/absolute','a/../b','a\\b','C:/escape','a:stream','a//b'):
                with self.assertRaises(ValueError):destination(folder,path)

    def test_existing_wrong_file_is_preserved(self):
        with self.folder() as folder:
            p=Path(folder)/'a.bin';p.write_bytes(b'keep me')
            with self.assertRaises(IntegrityError):download_atomic(source(),folder,'a.bin',authorization='BSD-3-Clause',opener=lambda *a:self.fail('request'))
            self.assertEqual(p.read_bytes(),b'keep me')

    def test_failed_replace_leaves_no_partial_destination(self):
        with self.folder() as folder:
            with patch('portability.downloads.os.replace',side_effect=OSError('simulated interruption')):
                with self.assertRaises(OSError):atomic_write(folder,'a.bin',b'x',hashlib.sha256(b'x').hexdigest())
            self.assertFalse((Path(folder)/'a.bin').exists());self.assertFalse(list(Path(folder).glob('*.part')))

    def test_restart_ignores_orphan_part_and_installs(self):
        with self.folder() as folder:
            (Path(folder)/'.a.bin.orphan.part').write_bytes(b'incomplete')
            self.assertEqual(download_atomic(source(),folder,'a.bin',authorization='BSD-3-Clause',opener=self.opener(b'owned test bytes')),'installed')
            self.assertEqual((Path(folder)/'a.bin').read_bytes(),b'owned test bytes')

    def test_partial_multi_file_install_resumes_without_redownloading(self):
        a,b=b'owned A',b'owned B'
        entries=[dict(target=name,authorization='BSD-3-Clause',category='unitree_mesh',action='download',source=source(data))
                 for name,data in [('a.bin',a),('b.bin',b)]]
        plan=dict(notices=[],resources=entries)
        with self.folder() as folder:
            def interrupted(src,root,target,**kwargs):
                def opened(url,timeout):
                    if target=='b.bin':raise OSError('simulated interrupted second transfer')
                    return Response(a,url)
                return download_atomic(src,root,target,opener=opened,attempts=1,**kwargs)
            first=install_authorized(plan,folder,download=interrupted)
            self.assertEqual(len(first['resources']),1);self.assertEqual(len(first['errors']),1)
            requests=[]
            def resumed(src,root,target,**kwargs):
                def opened(url,timeout):requests.append(target);return Response(b,url)
                return download_atomic(src,root,target,opener=opened,**kwargs)
            second=install_authorized(plan,folder,download=resumed)
            self.assertTrue(second['complete']);self.assertEqual(requests,['b.bin'])
            self.assertEqual([x['status'] for x in second['resources']],['cached','installed'])

    def test_source_plan_classification_and_hashes(self):
        p=load_plan();rows=p['resources']
        self.assertEqual(len(rows),66)
        self.assertEqual(sum(x['authorization']=='pending' for x in rows),26)
        self.assertEqual(sum(x['category']=='unitree_mesh' for x in rows),35)
        self.assertEqual(sum(x['category']=='generated_empty' for x in rows),5)
        self.assertEqual(sum(x['category']=='tp07_modified' for x in rows),8)
        self.assertEqual(sum(x['category']=='tp07_addition' for x in rows),3)
        self.assertEqual(sum(x['category']=='onnx' for x in rows),1)
        self.assertEqual(sum(x['category']=='motion_npz' for x in rows),1)

    def test_reconstruction_exact_with_owned_test_data(self):
        a=b'first\nold\nend';b=b'first\nnew owned line\nend\n'
        self.assertEqual(reconstruct(a,b,hashlib.sha256(a).hexdigest(),hashlib.sha256(b).hexdigest()),b)

    def test_reconstruction_rejects_wrong_input(self):
        with self.assertRaises(IntegrityError):reconstruct(b'x',b'y','0'*64,hashlib.sha256(b'y').hexdigest())

    def test_reconstruction_pending_sends_no_requests(self):
        with self.assertRaises(PermissionPending):from_reviewed_pair({},authorization='pending',fetch=lambda *a:self.fail('request'))

    def test_recipe_replays_against_only_the_verified_base(self):
        a=b'owned base\nold\n';b=b'owned base\nchanged\n'
        h1=hashlib.sha256(a).hexdigest();h2=hashlib.sha256(b).hexdigest()
        recipe=recipe_from_pair(a,b,h1,h2)
        self.assertEqual(apply_recipe(a,recipe,h1,h2),b)
        with self.assertRaises(IntegrityError):apply_recipe(a+b'x',recipe,h1,h2)

    def test_recipe_rejects_invalid_ranges_or_output(self):
        h=hashlib.sha256(b'a').hexdigest()
        with self.assertRaises(IntegrityError):apply_recipe(b'a',[('copy',0,200)],h,h)
        with self.assertRaises(IntegrityError):apply_recipe(b'a',[('insert',b'b')],h,h)

    def test_manifest_ships_no_patch_text(self):
        for entry in load_plan()['resources']:
            if entry['action']=='reconstruct_verified_pair':
                self.assertNotIn('patch',entry);self.assertNotIn('content',entry);self.assertNotIn('insert',entry)

    def test_pending_plan_steps_never_download(self):
        entry=dict(target='RoboNaldo_Deploy/not-installed.py',authorization='pending',category='official_original')
        with self.folder() as folder:
            r=install_authorized(dict(notices=[],resources=[entry]),folder,download=lambda *a,**kw:self.fail('request'))
            self.assertEqual(len(r['blocked']),1);self.assertFalse(r['complete']);self.assertFalse(list(Path(folder).iterdir()))

    def test_full_plan_never_requests_pending_sources(self):
        calls=[]
        def downloaded(src,*args,**kwargs):calls.append(src['repository']);return 'test-double'
        with self.folder() as folder:
            result=install_authorized(load_plan(),folder,download=downloaded)
        self.assertTrue(result['authorized_ready']);self.assertEqual(len(result['blocked']),26)
        self.assertEqual(len(calls),36);self.assertEqual(set(calls),{'unitreerobotics/unitree_ros'})

    def test_missing_license_stops_meshes_but_lists_all_pending(self):
        calls=[]
        def failed(*args,**kwargs):calls.append(1);raise DownloadError('simulated license network failure')
        with self.folder() as folder:
            result=install_authorized(load_plan(),folder,download=failed)
        self.assertFalse(result['authorized_ready']);self.assertEqual(len(result['blocked']),26)
        self.assertEqual(len(calls),1);self.assertEqual(len(result['errors']),1)

    def test_os_lock_can_be_reacquired_after_close(self):
        with self.folder() as folder:
            with installation_lock(folder):pass
            with installation_lock(folder):pass


if __name__=='__main__':unittest.main(verbosity=2)
