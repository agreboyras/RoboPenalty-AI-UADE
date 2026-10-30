"""Run package-only tests; optionally execute unchanged core tests with installed packages."""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'app/RoboPenalty'
JOBS=('phase3b/test_agent.py','phase4a/test_evaluation.py','phase4b/test_striker.py',
      'phase9a/test_input.py','phase9a/test_selection.py')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--include-core',action='store_true');args=p.parse_args()
    result=subprocess.run([sys.executable,'-X','utf8','-E','-s','-B',str(ROOT/'tests/test_distribution.py')],cwd=ROOT)
    if result.returncode:return result.returncode
    result=subprocess.run([sys.executable,'-X','utf8','-E','-s','-B',str(ROOT/'tests/test_local_import.py')],cwd=ROOT)
    if result.returncode:return result.returncode
    result=subprocess.run([sys.executable,'-X','utf8','-E','-s','-B',str(ROOT/'tests/test_installer.py')],cwd=ROOT)
    if result.returncode:return result.returncode
    if args.include_core:
        # Explicit paths to THIS bundle. No PYTHONPATH or old project's bootstrap.
        boot="import sys,runpy;from pathlib import Path;r=Path(sys.argv[1]);test=sys.argv[2];sys.argv=[test];sys.path[:0]=[str(r/'phase9a'),str(r/'phase6b'),str(r/'phase5'),str(r/'phase4b'),str(r/'phase4a'),str(r/'phase3b'),str(r/'phase3a'),str(r/'phase2'),str(r)];runpy.run_path(test,run_name='__main__')"
        for name in JOBS:
            print(name,flush=True)
            result=subprocess.run([sys.executable,'-X','utf8','-E','-s','-B','-c',boot,str(APP),str(ROOT/'tests/reference'/name)],cwd=ROOT)
            if result.returncode:return result.returncode
    return 0


if __name__=='__main__':raise SystemExit(main())
