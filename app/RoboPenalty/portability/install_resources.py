"""Install only reviewed resources; pending third-party steps have no opt-in override."""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sys
from portability.downloads import (digest, destination, validate_source, download_atomic,
    atomic_write, PermissionPending)

APP = Path(__file__).resolve().parents[1]
ROOT = APP.parents[1]
PLAN = Path(__file__).with_name('external_sources.json')
EMPTY_PATHS = frozenset('RoboNaldo_Deploy/'+x for x in (
    'FSM/__init__.py','common/__init__.py','deploy_mujoco/__init__.py',
    'policy/__init__.py','policy/beyondmimic/__init__.py'))


def load_plan(path=PLAN):
    path = Path(path)
    raw = json.loads(path.read_text(encoding='utf-8'))
    profile_path = path.with_name('runtime_profile.json')
    profile = json.loads(profile_path.read_text(encoding='utf-8'))
    meta = json.loads(path.with_name('distribution_profile.json').read_text(encoding='utf-8'))
    if raw.get('version') != 1 or digest(path.read_bytes()) != meta.get('external_sources_sha256'):
        raise ValueError('Resource source manifest changed')
    if raw['runtime_profile_sha256'] != digest(profile_path.read_bytes()):
        raise ValueError('Frozen runtime profile differs')
    expected = {r['root']+'/'+r['path']:r['sha256'] for r in profile['files'] if r['root']=='RoboNaldo_Deploy'}
    found = {}
    for entry in raw['resources']:
        target = entry['target']
        destination(APP.parent, target)
        if target in found or expected.get(target) != entry['sha256']:
            raise ValueError('Duplicate or unreviewed resource target/hash')
        found[target] = entry['sha256']
        if entry['action'] == 'generate_empty':
            if target not in EMPTY_PATHS or entry['sha256'] != digest(b'') or entry['authorization']!='own-empty-structure':
                raise ValueError('Unreviewed generated resource')
        else:
            validate_source(entry['source'])
            if entry['category']=='unitree_mesh':
                if entry['authorization']!='BSD-3-Clause' or entry['source']['repository']!='unitreerobotics/unitree_ros':
                    raise ValueError('Unreviewed mesh authorization')
                if entry['source']['path']!='robots/'+target.split('/',1)[1] or entry['source']['sha256']!=entry['sha256']:
                    raise ValueError('Unitree source mapping differs')
            elif entry['authorization']!='pending':
                raise ValueError('Pending step cannot be enabled without a reviewed implementation/update')
            if entry['action']=='reconstruct_verified_pair':
                validate_source(entry['reconstruction']['verified_target'])
                if entry['reconstruction']['verified_target']['sha256']!=entry['sha256']:
                    raise ValueError('Reconstruction output differs')
    if found != expected: raise ValueError('Source manifest does not cover all 66 resources')
    for notice in raw['notices']:
        validate_source(notice['source'])
        if (notice['target']!='RoboNaldo_Deploy/LICENSE-Unitree-ROS.txt'
            or notice['source']['path']!='LICENSE'
            or notice['source']['repository']!='unitreerobotics/unitree_ros'
            or notice['authorization']!='BSD-3-Clause'
            or notice['source']['sha256']!=notice['sha256']):
            raise ValueError('Unreviewed license notice')
    return raw


@contextmanager
def installation_lock(root):
    """An OS lock is released on process death; a leftover file is not a stale lock."""
    path=destination(root, '.cache/install.lock');path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a+b') as stream:
        if path.stat().st_size==0:stream.write(b'0');stream.flush()
        stream.seek(0)
        if os.name=='nt':
            import msvcrt
            try:msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
            except OSError as exc:raise RuntimeError('Another installer is using this folder') from exc
        else:
            import fcntl
            fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:yield
        finally:
            stream.seek(0)
            if os.name=='nt':msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(stream,fcntl.LOCK_UN)


def install_authorized(plan, workspace, *, download=download_atomic):
    results, errors = [], []
    blocked=[dict(target=e['target'],category=e['category'],reason='permission_review_pending')
             for e in plan['resources'] if e['authorization']=='pending']
    for entry in [*plan['notices'], *plan['resources']]:
        if entry['authorization']=='pending':
            continue
        try:
            if entry['action']=='generate_empty':
                status=atomic_write(workspace,entry['target'],b'',entry['sha256'])
            else:
                status=download(entry['source'],workspace,entry['target'],authorization=entry['authorization'])
            results.append(dict(target=entry['target'],status=status))
        except (OSError,ValueError,RuntimeError) as exc:
            errors.append(dict(target=entry['target'],type=type(exc).__name__,message=str(exc)))
            if entry['category']=='license':break  # Do not install meshes without the mandatory notice.
    return dict(complete=not blocked and not errors,authorized_ready=not errors,
                resources=results,blocked=blocked,errors=errors)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json',action='store_true')
    parser.add_argument('--plan',action='store_true',help='Show reviewed actions without downloading')
    args=parser.parse_args()
    plan=load_plan()
    if args.plan:
        result=dict(authorized_steps=sum(e['authorization']!='pending' for e in plan['resources'])+len(plan['notices']),
                    pending=[dict(target=e['target'],category=e['category']) for e in plan['resources'] if e['authorization']=='pending'])
        print(json.dumps(result,indent=2));return 2 if result['pending'] else 0
    with installation_lock(ROOT):result=install_authorized(plan,APP.parent)
    if args.json:print(json.dumps(result,indent=2))
    else:
        for row in result['resources']:print(row['status'],row['target'])
        for row in result['blocked']:print('PENDIENTE, sin descarga:',row['target'])
        for row in result['errors']:print('ERROR:',json.dumps(row,ensure_ascii=False))
        print('Descargas autorizadas preparadas; quedan descargas pendientes. Una importacion local verificada puede completar la ejecucion; verificar.ps1 informa el estado final.' if result['blocked'] else 'Recursos preparados.')
    return 1 if result['errors'] else 2 if result['blocked'] else 0


if __name__=='__main__':raise SystemExit(main())
