"""Platform-level KPI aggregation as a MapReduce job (mrjob, local runner = real multi-process map/sort/reduce).

mapper   : CSV line → (platform, [impressions, clicks, spend, conversions, revenue])
combiner : partial sums per mapper
reducer  : final sums per platform          (KPIs are computed afterwards by engine.kpis.finalize)

python bench/mr_job.py --bench-input data/ads_100k.csv      # driver mode (prints JSON)
python bench/mr_job.py -r local data/ads_100k.csv           # plain mrjob usage
"""
import csv
import sys
import time

from mrjob.job import MRJob

COLS = ["date", "campaign", "platform", "impressions", "clicks", "spend", "conversions", "revenue",
        "age", "gender", "city", "device"]
I_PLAT, I_IMP, I_CLK, I_SPEND, I_CONV, I_REV = (COLS.index(c) for c in
                                                ("platform", "impressions", "clicks", "spend", "conversions", "revenue"))


class MRPlatformKPI(MRJob):
    def mapper(self, _, line):
        if not line or line.startswith("date,"):
            return
        f = next(csv.reader([line]))
        yield f[I_PLAT], [int(f[I_IMP]), int(f[I_CLK]), float(f[I_SPEND]), int(f[I_CONV]), float(f[I_REV])]

    def combiner(self, platform, values):
        yield platform, _sum(values)

    def reducer(self, platform, values):
        yield platform, _sum(values)


def _sum(values):
    tot = [0, 0, 0.0, 0, 0.0]
    for v in values:
        for i, x in enumerate(v):
            tot[i] += x
    return tot


def run(path: str, runner: str = "local") -> dict:
    job = MRPlatformKPI(args=["-r", runner, "--no-conf", path])
    with job.make_runner() as r:
        r.run()
        return {k: [float(x) for x in v] for k, v in job.parse_output(r.cat_output())}


if __name__ == "__main__":
    if "--bench-input" in sys.argv:
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("--bench-input", required=True)
        ap.add_argument("--runner", default="local")
        a = ap.parse_args()
        from _common import emit
        t0 = time.perf_counter()
        sums = run(a.bench_input, a.runner)
        emit("mapreduce", a.bench_input, sums, 0.0, time.perf_counter() - t0)
    else:
        MRPlatformKPI.run()
