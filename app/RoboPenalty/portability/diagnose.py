"""Complete installation preflight; standard-library entrypoint, no auto-repair."""
import argparse
import contextlib
import hashlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
from portability.bundle import provenance, inspect_inventory, licensing

ROOT=Path(__file__).resolve().parents[1]
PROFILE=Path(__file__).with_name('runtime_profile.json')
TEXT={'.py','.xml','.yaml','.yml','.md','.txt','.sh'}

def inspect_resources(profile=PROFILE,workspace=None,check_revisions=True):
    profile=Path(profile);workspace=Path(workspace or ROOT.parent).resolve();problems=[];files=[];repos=[]
    try:raw=json.loads(profile.read_text(encoding='utf-8'))
    except (OSError,ValueError) as exc:return dict(ready=False,files=[],repositories=[],problems=[dict(kind='profile',message=str(exc))])
    if raw.get('version')!=1 or not raw.get('files'):
        return dict(ready=False,files=[],repositories=[],problems=[dict(kind='profile',message='Unsupported or empty profile')])
    historic=profile.with_name('external_manifest.json')
    if 'historical_manifest_sha256' in raw:
        if not historic.is_file() or hashlib.sha256(historic.read_bytes()).hexdigest()!=raw['historical_manifest_sha256']:
            problems.append(dict(kind='historical_manifest',message='Historical 209-resource manifest changed'))
    if check_revisions and profile.resolve()==PROFILE.resolve():
        problems.extend(provenance()['problems'])
    for name,revision in raw.get('revisions',{}).items():
        repos.append(dict(root=name,**revision,verification='Exact vendored SHA-256; revision is provenance, no nested Git HEAD'))
    seen=set()
    for row in raw['files']:
        name=row.get('root');relative=row.get('path','');label=f'{name}/{relative}';entry=dict(resource=label,status='ok')
        if name not in ('RoboNaldo_Deploy','unitree_mujoco'):
            problems.append(dict(kind='unsafe_path',resource=label));continue
        base=(workspace/name).resolve();path=(base/relative).resolve()
        if not relative or Path(relative).is_absolute() or not path.is_relative_to(base) or label.casefold() in seen:
            problems.append(dict(kind='unsafe_path_or_duplicate',resource=label));continue
        seen.add(label.casefold())
        try:
            if not path.is_file():entry['status']='missing'
            else:
                data=path.read_bytes();entry['sha256']=hashlib.sha256(data).hexdigest()
                if entry['sha256']!=row['sha256']:
                    entry['status']='different'
                    if path.suffix.lower() in TEXT or path.name=='LICENSE':
                        if hashlib.sha256(data.replace(b'\r\n',b'\n')).hexdigest()==row['sha256']:
                            entry['status']='line_endings'  # Diagnosis only; never accepted as equivalent.
        except OSError as exc:entry.update(status='unreadable',message=str(exc))
        if entry['status']!='ok':problems.append(dict(kind=entry['status'],resource=label,expected=row['sha256']))
        files.append(entry)
    return dict(ready=not problems,files=files,repositories=repos,problems=problems)

def inspect_packages(root=ROOT,import_checks=True):
    issues=[];packages=[]
    requirements=Path(root)/'requirements-windows.txt'
    if not requirements.exists():requirements=Path(root)/'requirements.txt'
    for line in requirements.read_text().splitlines():
        line=line.strip()
        if not line or line.startswith('#'):continue
        name,expected=line.split('==',1)
        try:actual=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:actual=None
        packages.append(dict(name=name,expected=expected,actual=actual))
        if actual!=expected:issues.append(dict(kind='python_package',name=name,expected=expected,actual=actual))
    if import_checks and not issues:
        os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
        for name in ('numpy','mujoco','onnxruntime','yaml','hydra','omegaconf','pygame','scipy'):
            try:
                with contextlib.redirect_stdout(sys.stderr):importlib.import_module(name)
            except Exception as exc:issues.append(dict(kind='python_import',name=name,message=f'{type(exc).__name__}: {exc}'))
    return dict(ready=not issues,packages=packages,problems=issues)

def report(profile=PROFILE,workspace=None,import_checks=True,resources_only=False):
    external=inspect_resources(profile,workspace)
    python=dict(ready=None,checked=False,packages=[],problems=[]) if resources_only else inspect_packages(import_checks=import_checks)
    inventory=inspect_inventory();rights=licensing()
    platform_ok=os.name=='nt' and sys.version_info[:2]==(3,12)
    resource_ready=external['ready'] and inventory['ready']
    technical=resource_ready and python['ready'] is True and platform_ok
    from portability.local_import import receipt_status
    local=receipt_status()
    execution_basis=rights['resolved'] or local['ready']
    return dict(technical_ready=technical,resource_ready=resource_ready,
        execution_ready=technical and execution_basis,local_import=local,
        resource_execution_ready=resource_ready and execution_basis,
        distribution_ready=technical and rights['resolved'],
        platform_supported=platform_ok,python_version=sys.version.split()[0],python_prefix=sys.prefix,
        external=external,python=python,inventory=inventory,licensing=rights,
        publication_ready=False)

def print_report(result):
    print('RoboPenalty: ejecucion local APTA' if result['execution_ready'] else 'RoboPenalty: ejecucion local NO APTA')
    print('Importacion local verificada:', 'SI' if result['local_import']['ready'] else 'NO')
    print('Dependencias externas:','OK' if result['external']['ready'] else 'ERROR')
    for item in result['external']['problems']:print(' -',json.dumps(item,ensure_ascii=False))
    print('Integridad del paquete:','OK' if result['inventory']['ready'] else 'ERROR')
    for item in result['inventory']['problems']:print(' -',json.dumps(item,ensure_ascii=False))
    print('Paquetes Python:','NO COMPROBADOS' if result['python'].get('checked') is False else 'OK' if result['python']['ready'] else 'ERROR')
    for item in result['python']['problems']:print(' -',json.dumps(item,ensure_ascii=False))
    if not result['platform_supported']:print(' - Configuracion soportada para esta prueba: Windows, Python 3.12.x')
    if not result['external']['ready']:print('Ejecutar scripts/instalar.ps1 -DeployPath <carpeta-local> con una copia adaptada obtenida legitimamente. Los recursos pendientes no se descargan ni se omiten.')
    if not result['python']['ready']:print('Usar el Python del nuevo .venv e instalar requirements-windows.txt. pip no instala las carpetas de los robots.')
    print('Estado tecnico:','APTO' if result['technical_ready'] else 'NO APTO')
    print('Permisos:','RESUELTOS' if result['licensing']['resolved'] else 'PENDIENTES: '+', '.join(result['licensing']['pending']))
    print('Recursos con paso pendiente:',len(result['licensing'].get('resources',[])))
    if result['local_import']['ready']:print('Importacion local valida. La descarga y redistribucion de los 26 recursos sigue pendiente; no es un fallo de ejecucion local.')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--json',action='store_true');p.add_argument('--no-import-check',action='store_true')
    p.add_argument('--historical',action='store_true',help='Archival 209-file check, not the portable runtime profile')
    p.add_argument('--resources-only',action='store_true',help='No exige paquetes; mantiene todos los hashes y permisos')
    a=p.parse_args();r=report(PROFILE.with_name('external_manifest.json') if a.historical else PROFILE,import_checks=not a.no_import_check,resources_only=a.resources_only)
    if a.json:print(json.dumps(r,indent=2))
    else:print_report(r)
    return 0 if (r['resource_execution_ready'] if a.resources_only else r['execution_ready']) else 1
if __name__=='__main__':raise SystemExit(main())
