"""Platform-level KPI aggregation with Pandas (single process, in memory).

python bench/pandas_job.py --input data/ads_100k.csv|.parquet
"""
import argparse
import time

import pandas as pd

from _common import BASE, emit


def run(path: str) -> dict[str, list[float]]:
    cols = ["platform", *BASE]
    df = pd.read_parquet(path, columns=cols) if path.endswith(".parquet") else pd.read_csv(path, usecols=cols)
    g = df.groupby("platform", observed=True)[BASE].sum()
    return {str(p): [float(x) for x in row] for p, row in g.iterrows()}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    a = ap.parse_args()
    t0 = time.perf_counter()
    sums = run(a.input)
    emit("pandas", a.input, sums, 0.0, time.perf_counter() - t0)
