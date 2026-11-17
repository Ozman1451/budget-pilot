"""Run the platform-KPI benchmark: sizes × engines × runs → bench/results.csv (REAL measurements only).

python bench/run_all.py [--sizes 10000,100000,1000000,10000000] [--max-rows 1000000] [--runs 3] [--timeout 600]

Each trial runs the job in a fresh subprocess. Wall time is measured from launch to exit (so Spark's JVM
start-up and mrjob's process spawning are included, as a user would feel them); the job also reports its
own compute time. Peak memory = max sampled RSS of the whole process tree (Python + JVM / mrjob workers).
A failing or timed-out engine is recorded as failed/timeout — never filled in. After the runs, every engine's
KPIs are checked against Pandas (rtol 1e-6); a mismatch is recorded and the script exits non-zero.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import psutil

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parent
sys.path.insert(0, str(ROOT))
from data.generate import COLUMNS, generate, label, parquet_path  # noqa: E402

RESULTS = BENCH / "results.csv"
DETAILS = BENCH / "results_detail.json"
ENGINES = {  # name → (script, input format, cli flag)
    "pandas": ("pandas_job.py", "csv", "--input"),
    "mapreduce": ("mr_job.py", "csv", "--bench-input"),
    "spark": ("spark_job.py", "csv", "--input"),
    "pandas_parquet": ("pandas_job.py", "parquet", "--input"),
    "spark_parquet": ("spark_job.py", "parquet", "--input"),
}
COLS = ["engine", "input_format", "rows", "runs_ok", "median_wall_s", "min_wall_s", "max_wall_s",
        "median_compute_s", "median_startup_s", "peak_mem_mb", "status", "agree", "note", "measured_at"]


def ensure_inputs(rows: int) -> tuple[Path, Path]:
    pq_path = parquet_path(rows)
    if not pq_path.exists():
        print(f"  generating {rows:,} rows …", flush=True)
        generate(rows)
    csv_path = pq_path.with_suffix(".csv")
    if not csv_path.exists():  # chunked parquet → CSV (same format as the generator's 10K CSV)
        import pyarrow.parquet as pq
        tmp = csv_path.with_suffix(".csv.tmp")
        first = True
        for batch in pq.ParquetFile(pq_path).iter_batches(batch_size=500_000):
            batch.to_pandas()[COLUMNS].to_csv(tmp, mode="w" if first else "a", header=first, index=False)
            first = False
        tmp.replace(csv_path)
    return pq_path, csv_path


def tree_rss(proc: psutil.Process) -> int:
    total = 0
    try:
        procs = [proc, *proc.children(recursive=True)]
    except psutil.Error:
        return 0
    for p in procs:
        try:
            total += p.memory_info().rss
        except psutil.Error:
            pass
    return total


def kill_tree(proc: psutil.Process) -> None:
    try:
        kids = proc.children(recursive=True)
    except psutil.Error:
        kids = []
    for p in [*kids, proc]:
        try:
            p.kill()
        except psutil.Error:
            pass


def trial(engine: str, path: Path, timeout: float) -> dict:
    script, _, flag = ENGINES[engine]
    cmd = [sys.executable, str(BENCH / script), flag, str(path)]
    env = {**os.environ, "PYTHONWARNINGS": "ignore"}
    t0 = time.perf_counter()
    popen = subprocess.Popen(cmd, cwd=BENCH, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    ps = psutil.Process(popen.pid)
    peak = 0
    status = "ok"
    while popen.poll() is None:
        peak = max(peak, tree_rss(ps))
        if time.perf_counter() - t0 > timeout:
            kill_tree(ps)
            status = "timeout"
            break
        time.sleep(0.05)
    out, err = popen.communicate()
    wall = time.perf_counter() - t0
    if status == "ok" and popen.returncode != 0:
        status = "failed"
    res = None
    if status == "ok":
        try:
            res = json.loads(out.strip().splitlines()[-1])
        except (ValueError, IndexError):
            status = "failed"
    return {"status": status, "wall_s": wall, "peak_mb": peak / 2**20, "res": res,
            "err": (err or "")[-1500:] if status != "ok" else ""}


def agree(a: dict, b: dict, rtol: float = 1e-6) -> bool:
    if set(a) != set(b):
        return False
    for p in a:
        for k in a[p]:
            if not np.isclose(a[p][k], b[p][k], rtol=rtol, atol=1e-6):
                return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", default="10000,100000,1000000,10000000")
    ap.add_argument("--max-rows", type=int, default=None, help="skip sizes above this (e.g. 1000000)")
    ap.add_argument("--engines", default=",".join(ENGINES))
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--timeout", type=float, default=600, help="seconds per single run")
    a = ap.parse_args()
    sizes = [int(s) for s in a.sizes.split(",") if s.strip()]
    if a.max_rows:
        sizes = [s for s in sizes if s <= a.max_rows]
    engines = [e.strip() for e in a.engines.split(",") if e.strip()]

    old = pd.read_csv(RESULTS) if RESULTS.exists() else pd.DataFrame(columns=COLS)
    details = json.loads(DETAILS.read_text()) if DETAILS.exists() else {}
    rows_out, mismatches = [], []
    for n in sizes:
        print(f"== {n:,} rows ({label(n)})", flush=True)
        pq_path, csv_path = ensure_inputs(n)
        per_engine: dict[str, dict] = {}
        for e in engines:
            fmt = ENGINES[e][1]
            path = pq_path if fmt == "parquet" else csv_path
            trials = []
            for r in range(a.runs):
                t = trial(e, path, a.timeout)
                trials.append(t)
                print(f"  {e:15s} run {r + 1}: {t['status']:7s} {t['wall_s']:7.2f}s  {t['peak_mb']:7.0f} MB", flush=True)
                if t["status"] != "ok":
                    break  # no point repeating a failure/timeout
            ok = [t for t in trials if t["status"] == "ok"]
            status = "ok" if len(ok) == len(trials) else trials[-1]["status"]
            row = {"engine": e, "input_format": fmt, "rows": n, "runs_ok": len(ok), "status": status,
                   "measured_at": datetime.now().isoformat(timespec="seconds"), "agree": "", "note": ""}
            if ok:
                walls = [t["wall_s"] for t in ok]
                row.update(median_wall_s=round(statistics.median(walls), 4), min_wall_s=round(min(walls), 4),
                           max_wall_s=round(max(walls), 4),
                           median_compute_s=round(statistics.median(t["res"]["compute_s"] for t in ok), 4),
                           median_startup_s=round(statistics.median(t["res"]["read_s"] for t in ok), 4),
                           peak_mem_mb=round(max(t["peak_mb"] for t in ok), 1))
                per_engine[e] = ok[-1]["res"]["result"]
            if status != "ok":
                row["note"] = " ".join(trials[-1]["err"].split())[-300:]
            rows_out.append(row)
        ref = per_engine.get("pandas")
        for row in rows_out:
            if row["rows"] != n or row["engine"] not in per_engine:
                continue
            if ref is None:
                row["agree"] = "no-reference"
            else:
                ok = agree(ref, per_engine[row["engine"]])
                row["agree"] = "yes" if ok else "NO"
                if not ok:
                    mismatches.append((n, row["engine"]))
        details[str(n)] = per_engine
    new = pd.DataFrame(rows_out, columns=COLS)
    keep = old[~old.set_index(["engine", "rows"]).index.isin(new.set_index(["engine", "rows"]).index)] if len(old) else old
    out = pd.concat([keep, new], ignore_index=True) if len(keep) else new
    out = out.sort_values(["rows", "engine"]).reset_index(drop=True)
    out.to_csv(RESULTS, index=False)
    DETAILS.write_text(json.dumps(details, indent=1))
    print(f"wrote {RESULTS.relative_to(ROOT)}")
    if mismatches:
        print(f"KPI MISMATCH vs pandas: {mismatches}", file=sys.stderr)
        return 1
    print("all engines agree with pandas (rtol 1e-6)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
