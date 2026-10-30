"""Generic verified-pair reconstruction. Contains no Deploy text or derived patch."""
import difflib
from portability.downloads import digest, IntegrityError, PermissionPending, fetch_verified


def recipe_from_pair(base, target, input_sha256, output_sha256):
    if digest(base) != input_sha256 or digest(target) != output_sha256:
        raise IntegrityError('Reconstruction input hash differs')
    a, b = base.splitlines(keepends=True), target.splitlines(keepends=True)
    offsets=[0]
    for line in a:offsets.append(offsets[-1]+len(line))
    recipe=[]
    for kind, i, j, k, l in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if kind == 'equal':recipe.append(('copy',offsets[i],offsets[j]))
        elif kind in ('insert', 'replace'):recipe.append(('insert',b''.join(b[k:l])))
    return recipe


def apply_recipe(base, recipe, input_sha256, output_sha256):
    if digest(base)!=input_sha256:raise IntegrityError('Patch base differs')
    output=[]
    for operation in recipe:
        if operation[0]=='copy' and len(operation)==3:
            _,start,end=operation
            if type(start) is not int or type(end) is not int or not 0<=start<=end<=len(base):
                raise IntegrityError('Patch copy range outside base')
            output.append(base[start:end])
        elif operation[0]=='insert' and len(operation)==2 and isinstance(operation[1],bytes):
            output.append(operation[1])
        else:raise IntegrityError('Invalid patch operation')
        if sum(map(len,output))>16*1024*1024:raise IntegrityError('Patch output exceeds resource bound')
    result=b''.join(output)
    if digest(result) != output_sha256: raise IntegrityError('Reconstructed output hash differs')
    return result


def reconstruct(base, target, input_sha256, output_sha256):
    return apply_recipe(base,recipe_from_pair(base,target,input_sha256,output_sha256),input_sha256,output_sha256)


def from_reviewed_pair(entry, *, authorization, fetch=fetch_verified):
    # No CLI flag grants this status. Current manifest keeps all eight pending.
    if authorization != 'explicit-use-and-modification-reviewed':
        raise PermissionPending('TP07 pair reconstruction disabled: permission review pending')
    base = fetch(entry['source'])
    target = fetch(entry['reconstruction']['verified_target'])
    return reconstruct(base, target, entry['source']['sha256'], entry['sha256'])
