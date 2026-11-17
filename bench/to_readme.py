"""Fill the benchmark table in README.md (between the BENCH markers) from bench/results.csv.

python bench/to_readme.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
START, END = "<!-- BENCH:START -->", "<!-- BENCH:END -->"
LABEL = {"pandas": "Pandas (CSV)", "mapreduce": "MapReduce · mrjob local (CSV)", "spark": "PySpark local[*] (CSV)",
         "pandas_parquet": "Pandas (Parquet)", "spark_parquet": "PySpark local[*] (Parquet)"}
ORDER = list(LABEL)


def table(df: pd.DataFrame) -> str:
    sizes = sorted(df["rows"].unique())
    head = "| Engine | " + " | ".join(f"{n:,} rows" for n in sizes) + " |"
    sep = "|---|" + "---:|" * len(sizes)
    lines = [head, sep]
    for e in [e for e in ORDER if e in set(df["engine"])]:
        cells = []
        for n in sizes:
            r = df[(df.engine == e) & (df.rows == n)]
            if r.empty:
                cells.append("not run")
            elif r.iloc[0].status != "ok":
                cells.append(str(r.iloc[0].status))
            else:
                x = r.iloc[0]
                cells.append(f"{x.median_wall_s:.2f} s · {x.peak_mem_mb:.0f} MB")
        lines.append(f"| {LABEL[e]} | " + " | ".join(cells) + " |")
    ok = df[df.status == "ok"]
    agree = "all engines produced identical KPIs (rtol 1e-6)" if len(ok) and (ok["agree"].astype(str) == "yes").all() \
        else "⚠ see `agree` column in bench/results.csv"
    when = str(df["measured_at"].max())
    lines += ["", f"Median wall time of {int(df['runs_ok'].max())} runs (includes interpreter / JVM start-up) · peak RSS of the "
                  f"whole process tree · {agree} · measured {when} on this machine. Raw: `bench/results.csv`."]
    return "\n".join(lines)


def main() -> None:
    csv = ROOT / "bench" / "results.csv"
    body = table(pd.read_csv(csv)) if csv.exists() else "_Not run yet — `make bench`._"
    text = README.read_text("utf-8")
    if START not in text:
        raise SystemExit("README.md has no BENCH markers")
    a, b = text.index(START) + len(START), text.index(END)
    README.write_text(text[:a] + "\n" + body + "\n" + text[b:], "utf-8")
    print("README benchmark table updated")


if __name__ == "__main__":
    main()
