"""Budget Pilot backend. Makes the repo root importable so `engine/` is shared with bench and tests."""
import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parents[2])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
