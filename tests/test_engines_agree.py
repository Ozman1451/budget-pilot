"""Pandas, MapReduce (mrjob) and PySpark must produce identical platform KPIs (rtol 1e-6)."""
import json
import shutil
import subprocess
import sys

import numpy as np
import pytest

from engine.kpis import finalize

BENCH = __import__("pathlib").Path(__file__).resolve().parents[1] / "bench"


def kpis(sums: dict) -> dict:
    import pandas as pd
    df = pd.DataFrame([{"platform": p, **dict(zip(["impressions", "clicks", "spend", "conversions", "revenue"], v))}
                       for p, v in sorted(sums.items())])
    return finalize(df).set_index("platform").to_dict("index")


def same(a: dict, b: dict) -> bool:
    return set(a) == set(b) and all(np.isclose(a[p][k], b[p][k], rtol=1e-6, atol=1e-6) for p in a for k in a[p])


@pytest.fixture(scope="module")
def reference(tiny):
    import pandas_job
    return kpis(pandas_job.run(str(tiny.with_suffix(".csv"))))


def test_pandas_parquet_equals_csv(tiny, reference):
    import pandas_job
    assert same(reference, kpis(pandas_job.run(str(tiny))))


def test_mapreduce_matches_pandas(tiny, reference):
    import mr_job
    assert same(reference, kpis(mr_job.run(str(tiny.with_suffix(".csv")), runner="inline")))


@pytest.mark.skipif(not (shutil.which("java") or __import__("os").environ.get("JAVA_HOME")), reason="no Java for Spark")
def test_spark_matches_pandas(tiny, reference):
    r = subprocess.run([sys.executable, str(BENCH / "spark_job.py"), "--input", str(tiny.with_suffix(".csv"))],
                       capture_output=True, text=True, timeout=300, cwd=BENCH)
    assert r.returncode == 0, r.stderr[-1500:]
    res = json.loads(r.stdout.strip().splitlines()[-1])["result"]
    assert same(reference, {p: {k: v for k, v in row.items()} for p, row in res.items()})
