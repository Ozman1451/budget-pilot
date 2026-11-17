import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "backend", ROOT / "bench"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


@pytest.fixture(scope="session")
def tiny(tmp_path_factory):
    """3,000-row dataset (Parquet + CSV) in a temp dir."""
    from data.generate import generate
    out = tmp_path_factory.mktemp("data") / "ads_tiny.parquet"
    generate(3000, seed=1, chunk=700, csv=True, out=out)
    return out


@pytest.fixture(scope="session")
def df(tiny):
    import pandas as pd
    return pd.read_parquet(tiny)
