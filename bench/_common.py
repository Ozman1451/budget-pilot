"""Shared bits for the benchmark jobs (each job is also runnable on its own)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BASE = ["impressions", "clicks", "spend", "conversions", "revenue"]


def emit(engine: str, path: str, sums: dict[str, list[float]], read_s: float, compute_s: float) -> None:
    """Print one JSON line: platform sums + KPIs (computed by engine.kpis.finalize, shared by all engines)."""
    import pandas as pd
    from engine.kpis import finalize
    df = pd.DataFrame([{"platform": p, **dict(zip(BASE, v))} for p, v in sorted(sums.items())])
    kpis = finalize(df).set_index("platform")
    print(json.dumps({"engine": engine, "input": str(path), "read_s": read_s, "compute_s": compute_s,
                      "result": {p: {k: float(v) for k, v in row.items()} for p, row in kpis.iterrows()}}))
