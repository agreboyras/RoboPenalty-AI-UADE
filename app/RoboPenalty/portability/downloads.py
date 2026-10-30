"""Owned HTTPS/atomic I/O helpers. No third-party source or patch payloads."""
import hashlib
import hmac
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import build_opener, HTTPRedirectHandler, Request

REPOSITORIES = frozenset({
    ('unitreerobotics/unitree_ros', '38a9b00ecbff0b70e85a7627eb9c65db9a2341f7'),
    ('OpenDriveLab/RoboNaldo_Deploy', 'f60f24459aaabc3aea9187a2b13f8923049b629c'),
    ('agreboyras/TP07-IA-G1-Futbol', 'ce4b34d1bccfd0420a81bf1688271d86feb8a117'),
})


class IntegrityError(ValueError): pass
class DownloadError(RuntimeError): pass
class PermissionPending(RuntimeError): pass


def digest(data): return hashlib.sha256(data).hexdigest()


def relative_path(value):
    if not isinstance(value, str) or not value or '\\' in value or ':' in value or any(ord(c)<32 for c in value):
        raise ValueError('Invalid relative path')
    p = PurePosixPath(value)
    if p.is_absolute() or any(x in ('', '.', '..') for x in value.split('/')):
        raise ValueError('Unsafe relative path')
    return p


def destination(root, relative):
    root = Path(root).resolve()
    path = root.joinpath(*relative_path(relative).parts).resolve()
    if not path.is_relative_to(root): raise ValueError('Destination escapes installation root')
    return path


def canonical_url(repository, revision, path):
    relative_path(path)
    if not re.fullmatch('[0-9a-f]{40}', revision) or (repository, revision) not in REPOSITORIES:
        raise ValueError('Unapproved repository or non-fixed revision')
    return 'https://raw.githubusercontent.com/' + repository + '/' + revision + '/' + quote(path, safe='/')


def validate_source(source):
    expected = canonical_url(source['repository'], source['revision'], source['path'])
    if source.get('url') != expected: raise ValueError('Source URL differs from pinned canonical URL')
    if not re.fullmatch('[0-9a-f]{64}', source.get('sha256', '')): raise ValueError('Invalid SHA-256')
    if type(source.get('bytes')) is not int or not 0 <= source['bytes'] <= 16*1024*1024:
        raise ValueError('Invalid resource size')
    return expected


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise DownloadError('Redirect rejected; only the exact reviewed HTTPS URL is allowed')


def open_https(url, timeout):
    return build_opener(NoRedirect()).open(Request(url, headers={'User-Agent':'RoboPenalty-AI-Installer/1'}), timeout=timeout)


def fetch_verified(source, *, opener=open_https, attempts=3, timeout=20., delay=time.sleep):
    url = validate_source(source)
    if not 1 <= attempts <= 5: raise ValueError('Invalid retry count')
    for attempt in range(attempts):
        try:
            with opener(url, timeout) as response:
                if response.geturl() != url or response.status != 200:
                    raise DownloadError('Unexpected final URL or HTTP status')
                data = bytearray()
                while True:
                    block = response.read(min(65536, source['bytes'] + 1 - len(data)))
                    if not block: break
                    data.extend(block)
                    if len(data) > source['bytes']: raise IntegrityError('Response exceeds reviewed resource size')
                if len(data) != source['bytes']: raise OSError('Incomplete response')
                if not hmac.compare_digest(digest(data), source['sha256']):
                    raise IntegrityError('SHA-256 mismatch; bytes rejected, no normalization')
                return bytes(data)
        except (IntegrityError, DownloadError):
            raise
        except (OSError, URLError, TimeoutError) as exc:
            if attempt + 1 == attempts: raise DownloadError('HTTPS download failed after bounded retries: '+str(exc)) from exc
            delay(min(2**attempt, 4))


def cached(root, relative, expected):
    path = destination(root, relative)
    if not path.exists(): return False
    if not path.is_file() or digest(path.read_bytes()) != expected:
        raise IntegrityError('Existing resource differs; refusing to overwrite: '+relative)
    return True


def atomic_write(root, relative, data, expected):
    if digest(data) != expected: raise IntegrityError('Output digest differs before write')
    path = destination(root, relative)
    if cached(root, relative, expected): return 'cached'
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.'+path.name+'.', suffix='.part', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        if digest(temporary.read_bytes()) != expected: raise IntegrityError('Staged file digest differs')
        # The installer lock serializes writers; do not replace unrelated existing content.
        if path.exists():
            cached(root, relative, expected)
            return 'cached'
        os.replace(temporary, path)
        return 'installed'
    finally:
        if temporary is not None and temporary.exists(): temporary.unlink()


def download_atomic(source, root, relative, *, authorization, opener=open_https, attempts=3, delay=time.sleep):
    if authorization != 'BSD-3-Clause': raise PermissionPending('Resource permission is pending; no request sent')
    validate_source(source)
    if cached(root, relative, source['sha256']): return 'cached'
    return atomic_write(root, relative, fetch_verified(source, opener=opener, attempts=attempts, delay=delay), source['sha256'])
