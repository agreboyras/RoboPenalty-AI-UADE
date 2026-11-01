from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[2]
for name in ('phase2', 'phase3a', 'phase3b', 'phase4a', 'phase4b',
             'phase5', 'phase6a', 'phase6b', 'phase9a'):
    sys.path.append(str(PROJECT/name))
