"""Strict inventory/provenance for this distribution, without nested Git repositories."""
import hashlib
import json
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
ROOT = APP.parents[1]
PROFILE = Path(__file__).with_name('runtime_profile.json')
METADATA = PROFILE.with_name('distribution_profile.json')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def provenance(profile=PROFILE, metadata=METADATA):
    problems = []
    try:
        raw = json.loads(Path(profile).read_text(encoding='utf-8'))
        meta = json.loads(Path(metadata).read_text(encoding='utf-8'))
        if meta.get('version') != 1 or meta.get('backend') != 'vendored-sha256':
            raise ValueError('Unsupported distribution profile')
        if sha(Path(profile).read_bytes()) != meta['runtime_profile_sha256']:
            problems.append(dict(kind='runtime_profile', message='Frozen runtime profile changed'))
        sources=Path(profile).with_name('external_sources.json')
        if not sources.is_file() or sha(sources.read_bytes())!=meta.get('external_sources_sha256'):
            problems.append(dict(kind='external_sources',message='Reviewed source manifest changed'))
        if set(meta['roots']) != set(raw['revisions']):
            problems.append(dict(kind='provenance', message='Dependency roots differ'))
        for name, revision in raw['revisions'].items():
            for key in ('repository', 'commit'):
                if meta['roots'].get(name, {}).get(key) != revision[key]:
                    problems.append(dict(kind='provenance', root=name, field=key))
        return dict(ready=not problems, problems=problems, roots=meta['roots'])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return dict(ready=False, roots={}, problems=[dict(kind='distribution_profile', message=str(exc))])


def inspect_inventory(root=ROOT):
    """Detect accidental edits. This inventory is not a cryptographic signature."""
    root = Path(root).resolve()
    problems, seen = [], set()
    try:
        raw = json.loads((root/'docs/distribution_inventory.json').read_text(encoding='utf-8'))
        if raw.get('version') != 1 or not raw.get('files'):
            raise ValueError('Missing distribution inventory')
        for row in raw['files']:
            relative = row['path']
            path = (root/relative).resolve()
            if Path(relative).is_absolute() or not path.is_relative_to(root) or relative.casefold() in seen:
                problems.append(dict(kind='inventory_path', resource=relative))
                continue
            seen.add(relative.casefold())
            if not path.is_file() or sha(path.read_bytes()) != row['sha256']:
                problems.append(dict(kind='distribution_file', resource=relative))
        return dict(ready=not problems, checked=len(seen), problems=problems)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return dict(ready=False, checked=0, problems=[dict(kind='inventory', message=str(exc))])


def licensing():
    result = provenance()
    try:
        from portability.install_resources import load_plan
        plan=load_plan()
        resources=[dict(target=e['target'],category=e['category']) for e in plan['resources'] if e['authorization']=='pending']
    except (OSError,ValueError,KeyError,TypeError) as exc:
        return dict(resolved=False,pending=['source_manifest_invalid'],resources=[],note=str(exc))
    pending=sorted({r['target'].split('/')[0] for r in resources})
    return dict(resolved=result['ready'] and not resources, pending=pending, resources=resources,
                note='Public availability and a private repository do not establish redistribution permission.')
