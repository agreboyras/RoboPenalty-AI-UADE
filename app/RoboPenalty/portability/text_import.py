"""Manifest opt-in for local CRLF-to-LF copies; no encoding/content rewriting."""
from pathlib import PurePosixPath

from portability.downloads import digest

TEXT_POLICY = {'encoding': 'utf-8', 'newline_transform': 'crlf-to-lf'}
TEXT_CATEGORIES = frozenset(('official_original', 'tp07_modified', 'tp07_addition'))
TEXT_SUFFIXES = frozenset(('.py', '.xml', '.yaml', '.yml'))


class ResourceMismatch(ValueError):
    """Bytes cannot produce the frozen canonical SHA-256 by an allowed operation."""


def validate_text_policy(entry):
    policy = entry.get('local_import_text')
    if policy is None:
        return False
    if (policy != TEXT_POLICY or entry.get('authorization') != 'pending' or
        entry.get('category') not in TEXT_CATEGORIES or
        PurePosixPath(entry['target']).suffix.lower() not in TEXT_SUFFIXES):
        raise ValueError('Politica de texto local invalida o aplicada a un binario: ' + entry['target'])
    return True


def canonical_bytes(entry, data):
    """Return exact target bytes plus transformation name, or fail closed."""
    enabled = validate_text_policy(entry)
    if digest(data) == entry['sha256']:
        return data, 'none'
    if not enabled:
        raise ResourceMismatch('SHA-256 diferente; este recurso exige bytes exactos.')
    try:
        data.decode('utf-8', errors='strict')  # Validation only: never re-encode.
    except UnicodeDecodeError as exc:
        raise ResourceMismatch('Texto no UTF-8; no se convierte la codificacion.') from exc
    normalized = data.replace(b'\r\n', b'\n')
    if b'\x00' in data or b'\r' in normalized or digest(normalized) != entry['sha256']:
        raise ResourceMismatch('El contenido difiere incluso despues de CRLF->LF autorizado.')
    return normalized, 'crlf-to-lf'
