"""Import canonical user-provided local resources. No downloads or license grants."""
import argparse
import json
import os
from pathlib import Path
import tempfile

from portability.downloads import digest, destination, atomic_write
from portability.install_resources import ROOT, PLAN, load_plan, installation_lock
from portability.text_import import canonical_bytes, ResourceMismatch

RECEIPT = '.cache/local_import.json'


def pending(plan):
    return [e for e in plan['resources'] if e['authorization'] == 'pending']


def scan(source, plan):
    source = Path(source).resolve(strict=True)
    if not source.is_dir():
        raise ValueError('Seleccionar una carpeta Deploy, no un archivo.')
    rows = []
    for entry in pending(plan):
        relative = entry['target'].split('/', 1)[1]
        path = destination(source, relative)
        row = dict(target=entry['target'], expected=entry['sha256'], status='missing')
        if path.is_file():
            data = path.read_bytes()
            actual = digest(data)
            row['sha256'] = actual
            try:
                canonical, transformation = canonical_bytes(entry, data)
                row.update(status='adapted' if transformation == 'none' else 'crlf_to_lf',
                           canonical_sha256=digest(canonical), transformation=transformation)
            except ResourceMismatch as exc:
                row.update(status='different', reason=str(exc))
            if row['status'] == 'different' and entry['category'] == 'tp07_modified':
                try:
                    canonical_bytes({**entry, 'sha256': entry['source']['sha256']}, data)
                    row['status'] = 'official_base'
                except ResourceMismatch:
                    pass
        rows.append(row)
    compatible = all(r['status'] in ('adapted', 'crlf_to_lf') for r in rows)
    official = all(r['status'] in ('adapted', 'crlf_to_lf', 'official_base') or
                   (r['status'] == 'missing' and e['category'] == 'tp07_addition')
                   for r, e in zip(rows, pending(plan))) and any(r['status'] == 'official_base' for r in rows)
    return dict(compatible=compatible, kind='tp07-compatible' if compatible else 'official-compatible' if official else 'incomplete-or-different', files=rows)


def notices(source, plan):
    """Preserve nearby notices/documentation without sweeping unrelated directories."""
    source = Path(source).resolve()
    parents = {source}
    for entry in pending(plan):
        p = destination(source, entry['target'].split('/', 1)[1]).parent
        while p != source:
            parents.add(p)
            p = p.parent
    found = {}
    for parent in sorted(parents):
        if not parent.is_dir():
            continue
        for path in sorted(parent.iterdir()):
            name = path.name.upper()
            if path.is_file() and any(name.startswith(x) for x in ('LICENSE', 'LICENCE', 'NOTICE', 'COPYING', 'COPYRIGHT', 'AUTHORS', 'README')):
                safe = destination(source, path.relative_to(source).as_posix())
                if safe.stat().st_size > 2 * 1024 * 1024:
                    raise ValueError('Aviso demasiado grande; revisar antes de importar: ' + path.name)
                found[path.relative_to(source).as_posix()] = safe.read_bytes()
    return found


def write_receipt(root, receipt):
    path = destination(root, RECEIPT)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='receipt_', suffix='.part', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write((json.dumps(receipt, indent=2) + '\n').encode('utf-8'))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def receipt_status(root=ROOT, plan=None):
    """Receipt attests local import only, never permission to redistribute."""
    try:
        plan = plan or load_plan()
        r = json.loads(destination(root, RECEIPT).read_text(encoding='utf-8'))
        if not isinstance(r, dict) or not isinstance(r.get('notices'), dict):
            raise ValueError('Registro local mal formado; volver a importar.')
        expected = {e['target']: e['sha256'] for e in pending(plan)}
        if (r.get('version') != 1 or r.get('kind') != 'tp07-compatible' or
            r.get('runtime_profile_sha256') != plan['runtime_profile_sha256'] or
            r.get('resources') != expected):
            raise ValueError('Registro de importacion distinto del perfil congelado.')
        for target, sha in expected.items():
            if digest(destination(Path(root)/'app', target).read_bytes()) != sha:
                raise ValueError('Recurso importado diferente: ' + target)
        for target, sha in r['notices'].items():
            if not isinstance(target, str) or not target.startswith('.cache/local_import_notices/'):
                raise ValueError('Ruta de aviso invalida.')
            if digest(destination(root, target).read_bytes()) != sha:
                raise ValueError('Aviso importado diferente: ' + target)
        return dict(ready=True, count=len(expected), basis='User-provided exact local copy; redistribution rights remain independent')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return dict(ready=False, count=0, message=str(exc))


def import_local(source, root=ROOT, plan=None):
    plan = plan or load_plan()
    source = Path(source).resolve(strict=True)
    root = Path(root).resolve()
    if source.is_relative_to(root) or root.is_relative_to(source):
        raise ValueError('La carpeta fuente debe estar fuera de la distribucion de destino.')
    result = scan(source, plan)
    if not result['compatible']:
        return result
    # Validate every source and every existing destination BEFORE writing any resource.
    payloads = {}
    source_hashes, normalizations = {}, {}
    for entry in pending(plan):
        data = destination(source, entry['target'].split('/', 1)[1]).read_bytes()
        canonical, transformation = canonical_bytes(entry, data)
        dest = destination(root/'app', entry['target'])
        if dest.exists() and (not dest.is_file() or digest(dest.read_bytes()) != entry['sha256']):
            raise ValueError('Destino existente diferente; no se sobrescribe: ' + entry['target'])
        payloads[entry['target']] = canonical
        source_hashes[entry['target']] = digest(data)
        if transformation != 'none':
            normalizations[entry['target']] = transformation
        row = next(r for r in result['files'] if r['target'] == entry['target'])
        row.update(sha256=digest(data), canonical_sha256=digest(canonical), transformation=transformation,
                   status='adapted' if transformation == 'none' else 'crlf_to_lf')
    notice_data = notices(source, plan)
    expected = {e['target']: e['sha256'] for e in pending(plan)}
    with installation_lock(root):
        for target, data in payloads.items():
            atomic_write(root/'app', target, data, expected[target])
        saved = {}
        for relative, data in notice_data.items():
            target = '.cache/local_import_notices/' + digest(data) + '/' + relative
            atomic_write(root, target, data, digest(data))
            saved[target] = digest(data)
        write_receipt(root, dict(version=1, kind=result['kind'], runtime_profile_sha256=plan['runtime_profile_sha256'],
            resources={e['target']: e['sha256'] for e in pending(plan)}, notices=saved,
            source_resources=source_hashes, normalizations=normalizations,
            note='Local resources supplied by user. Hashes do not grant use or redistribution rights. No source absolute path recorded.'))
    result['imported'] = len(payloads)
    result['normalized_files'] = len(normalizations)
    result['receipt'] = receipt_status(root, plan)
    if not result['receipt']['ready']:
        raise ValueError('La comprobacion SHA-256 final de los recursos importados fallo.')
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path)
    p.add_argument('--inspect', action='store_true', help='Solo verificar la carpeta; no copiar')
    p.add_argument('--json', action='store_true')
    a = p.parse_args()
    try:
        plan = load_plan()
        result = scan(a.source, plan) if a.inspect else import_local(a.source, plan=plan)
        if a.json:
            print(json.dumps(result, indent=2))
        else:
            print('Deploy:', result['kind'])
            for row in result['files']:
                print(row['status'], row['target'])
            if result['compatible']:
                count = len(result['files'])
                normalized = sum(r['status']=='crlf_to_lf' for r in result['files'])
                print(f'{count}/{count} recursos compatibles; {normalized} requieren CRLF->LF local.')
                print('Inspeccion sin copia; no se modifica la fuente.' if a.inspect else
                      'Importacion local terminada con SHA-256 canonicos exactos; ejecutar verificar.ps1.')
            else:
                print('No se importo nada. Deploy oficial requiere 8 modificaciones y 3 adiciones TP07 verificadas; no se distribuyen parches derivados sin permisos claros. Usar una copia adaptada obtenida legitimamente. Solo los textos explicitamente listados admiten CRLF->LF si resulta el SHA esperado; binarios, codificacion y otros cambios se rechazan.')
        return 0 if result['compatible'] else 2
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        print('Importacion rechazada:', str(exc))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
