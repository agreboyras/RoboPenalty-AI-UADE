"""Run the unchanged reference evaluator with private output/cache directories."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys
import traceback
from .audit_checkpoint import EXPECTED_SHA
from .environment import configure_cache


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True, help='New private results folder')
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('arguments', nargs=argparse.REMAINDER)
    a = p.parse_args()
    ref = a.reference.resolve()
    checkpoint = ref/'src/assets/soccer/weight/goalkeeper.pt'
    if hashlib.sha256(checkpoint.read_bytes()).hexdigest() != EXPECTED_SHA:
        raise ValueError('External checkpoint differs; evaluator not started')
    output = a.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    configure_cache(a.cache)
    tail = a.arguments[1:] if a.arguments[:1] == ['--'] else a.arguments
    if '--device' in tail or '--checkpoint' in tail:
        p.error('CPU and verified external checkpoint are fixed by this launcher')
    sys.path.insert(0, str(ref))
    script = ref/'scripts/eval_naive_goalkeeper.py'
    sys.argv = [str(script), '--device', 'cpu', '--checkpoint', str(checkpoint), *tail]
    os.chdir(output)
    try:
        runpy.run_path(str(script), run_name='__main__')
    except SystemExit as exc:
        if exc.code not in (0, None):
            raise
    except Exception:
        (output/'exception.txt').write_text(traceback.format_exc(), encoding='utf-8')
        (output/'status.json').write_text(json.dumps(dict(status='original_entry_failed',
            checkpoint_sha256=EXPECTED_SHA, saves_verified=False)), encoding='utf-8')
        raise
    (output/'status.json').write_text(json.dumps(dict(status='original_entry_returned',
        checkpoint_sha256=EXPECTED_SHA, saves_verified=False,
        note='Completion of the entry point does not establish physical save metrics.')), encoding='utf-8')


if __name__ == '__main__':
    main()
