"""Public launcher: phase9a unchanged, dependency checks from relative manifest."""
from pathlib import Path
import sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))

if __name__=='__main__':
    if not {'--help','-h'}.intersection(sys.argv):
        from portability.diagnose import report,print_report
        preflight=report()
        if not preflight['execution_ready']:
            print_report(preflight);raise SystemExit(2)
    sys.path.insert(0,str(ROOT/'phase9a'))
    from phase9a import run_session
    from portability.resources import components
    # Scoped selection of the resource adapter; the original phase9a entry point remains intact.
    run_session.components=components
    run_session.main()
