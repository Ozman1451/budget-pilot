"""Agent tools + page endpoints. Every tool returns ToolResult {summary, charts}; numbers come only from here
(the LLM never computes them). Pattern reused from Need Map Chat (registry, clean(), ToolError, call_tool)."""
from __future__ import annotations

import inspect
import math
from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd

from engine.kpis import KPI_FORMULAS, apply_filters, kpis_by, norm_filters, totals
from engine.optimizer import DEFAULT_BUDGET, DEFAULT_HORIZON, PLATFORMS, curve_points, optimize

from .config import settings
from .schemas import ChartSpec, ToolResult
from .store import store

GROUPS = ["platform", "campaign", "city", "age", "gender", "device", "month"]
METRIC_LABEL = {"spend": "Spend", "revenue": "Revenue", "roas": "ROAS", "ctr": "CTR", "cpc": "CPC", "cpa": "CPA",
                "cvr": "Conv. rate", "profit": "Profit", "conversions": "Conversions", "clicks": "Clicks",
                "impressions": "Impressions", "cpm": "CPM", "aov": "AOV"}
METRIC_FMT = {"spend": "pkr", "revenue": "pkr", "profit": "pkr", "cpc": "pkr", "cpa": "pkr", "cpm": "pkr",
              "aov": "pkr", "roas": "x", "ctr": "pct", "cvr": "pct", "conversions": "int", "clicks": "int",
              "impressions": "int"}


class ToolError(ValueError):
    """Bad arguments: reported back to the model / a 400 to the client."""


# ---------------------------------------------------------------- helpers
def clean(o: Any) -> Any:
    """→ plain JSON-safe Python (numpy scalars → python, NaN/inf → None)."""
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, np.ndarray):
        return clean(o.tolist())
    if isinstance(o, np.generic):
        o = o.item()
    if isinstance(o, float) and (math.isnan(o) or math.isinf(o)):
        return None
    if isinstance(o, pd.Timestamp):
        return o.isoformat()
    return o


def result(summary: dict, charts: list[ChartSpec]) -> ToolResult:
    for c in charts:
        c.data, c.meta = clean(c.data), clean(c.meta)
    return ToolResult(summary=clean({"dataset": store.dataset, "currency": "PKR", **summary}), charts=charts)


def filters_of(filters: Any) -> dict[str, list[str]]:
    if filters in (None, "", {}):
        return {}
    if not isinstance(filters, dict):
        raise ToolError("filters must be an object like {\"city\": \"Lahore\", \"age\": \"18-24\"}")
    split = {k: ([x.strip() for x in v.split(",")] if isinstance(v, str) else v) for k, v in filters.items()}
    try:
        return norm_filters(split, store.options())
    except ValueError as exc:
        raise ToolError(str(exc)) from exc


def subset(f: dict[str, list[str]]) -> pd.DataFrame:
    df = apply_filters(store.ensure().df, f)
    if df.empty:
        raise ToolError(f"no rows match filters {f}")
    return df


def fdesc(f: dict) -> str:
    return " · ".join(f"{k}={'/'.join(v)}" for k, v in f.items()) or "all data"


def r(x: float, d: int = 4) -> float:
    return round(float(x), d)


def tiles(t: dict) -> ChartSpec:
    spec = [("spend", "Spend"), ("revenue", "Revenue"), ("roas", "ROAS"), ("profit", "Profit"),
            ("ctr", "CTR"), ("cpc", "CPC"), ("cvr", "Conv. rate"), ("cpa", "CPA")]
    return ChartSpec(type="kpi_tiles", title="Headline KPIs", data={"tiles": [
        {"key": k, "label": lab, "value": t[k], "format": METRIC_FMT[k]} for k, lab in spec]})


# ---------------------------------------------------------------- tool: get_kpis
def get_kpis(filters: dict | None = None, group_by: str = "platform", sort_by: str = "roas", top: int = 12) -> ToolResult:
    """KPIs (spend, revenue, ROAS, CTR, CPC, CPA, conversion rate, profit) grouped by one dimension."""
    f = filters_of(filters)
    group_by = (group_by or "platform").lower()
    if group_by not in GROUPS:
        raise ToolError(f"group_by must be one of {', '.join(GROUPS)}")
    if sort_by not in METRIC_LABEL:
        sort_by = "roas"
    df = subset(f)
    t = totals(df)
    k = kpis_by(df, group_by)
    if group_by == "month":
        k = k.sort_values("month")
    else:
        k = k.sort_values(sort_by, ascending=sort_by in ("cpc", "cpa", "cpm"))
    shown = k.head(max(1, min(int(top or 12), 40)))
    cols = ["spend", "revenue", "roas", "profit", "ctr", "cpc", "cvr", "cpa", "conversions"]
    rows = [{group_by: str(row[group_by]), **{c: r(row[c]) for c in cols}} for _, row in shown.iterrows()]
    best = k.loc[k["roas"].idxmax()]
    worst = k.loc[k["roas"].idxmin()]
    summary = {"filters": f, "group_by": group_by, "sorted_by": sort_by, "rows_scanned": int(len(df)),
               "totals": {c: r(t[c]) for c in cols + ["clicks", "impressions"]}, "groups": rows,
               "groups_total": int(len(k)), "best_roas": {group_by: str(best[group_by]), "roas": r(best["roas"])},
               "worst_roas": {group_by: str(worst[group_by]), "roas": r(worst["roas"])},
               "formulas": KPI_FORMULAS}
    names = [row[group_by] for row in rows]
    charts = [
        tiles(t),
        ChartSpec(type="bar", title=f"ROAS by {group_by}", subtitle=fdesc(f),
                  data={"categories": names, "series": [{"name": "ROAS", "values": [x["roas"] for x in rows]}],
                        "format": "x", "horizontal": group_by == "campaign", "color_by_platform": group_by == "platform"}),
        ChartSpec(type="table", title=f"KPIs by {group_by}", subtitle=f"{fdesc(f)} · {len(df):,} rows",
                  data={"columns": [{"key": group_by, "label": group_by.title()}] +
                        [{"key": c, "label": METRIC_LABEL[c], "format": METRIC_FMT[c]} for c in cols],
                        "rows": rows}),
    ]
    return result(summary, charts)


# ---------------------------------------------------------------- tool: optimize_budget
def _plan(budget, min_pct, max_pct, f, horizon, n_boot):
    key = {"b": budget, "min": min_pct, "max": max_pct, "f": f, "h": horizon, "n": n_boot, "d": store.dataset}
    def run():
        try:
            return optimize(store.ensure().df, budget=budget, min_pct=min_pct, max_pct=max_pct, filters=f,
                            horizon=horizon, n_boot=n_boot)
        except ValueError as exc:
            raise ToolError(str(exc)) from exc
    return store.cached(key, run)


def _pct_arg(v):
    if v in (None, "", {}):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, dict):
        return {k: float(x) for k, x in v.items() if x is not None}
    raise ToolError("min_pct / max_pct must be a number or an object like {\"TikTok\": 10}")


def plan_charts(plan, f: dict, inline_curves: bool = False) -> list[ChartSpec]:
    al = [plan.alloc[p] for p in PLATFORMS]
    s, b = plan.summary, plan.band
    return [
        ChartSpec(type="donut", title="Recommended split",
                  subtitle=f"Rs {plan.budget:,.0f} over {plan.horizon} days · {fdesc(f)}",
                  data={"items": [{"name": a["platform"], "value": a["pkr"], "pct": a["pct"],
                                   "low": a["pct_low"], "high": a["pct_high"]} for a in al],
                        "center": {"label": "Predicted ROAS", "value": s["predicted_roas"], "format": "x",
                                   "low": b["roas_p5"], "high": b["roas_p95"]}}),
        ChartSpec(type="bar", title="Current mix vs recommended", subtitle="PKR per platform for this budget",
                  data={"categories": PLATFORMS, "format": "pkr",
                        "series": [{"name": "Current mix", "values": [a["current_pkr"] for a in al]},
                                   {"name": "Recommended", "values": [a["pkr"] for a in al]}]}),
        ChartSpec(type="curves", title="Response curves", meta={"inline": inline_curves},
                  subtitle=f"Predicted revenue vs spend over {plan.horizon} days · ● recommended ○ current",
                  data={"platforms": curve_points(plan)}),
        ChartSpec(type="table", title="Allocation and reasons", meta={"inline": True},
                  data={"columns": [{"key": "platform", "label": "Platform"},
                                    {"key": "pct", "label": "Share", "format": "pct100"},
                                    {"key": "pkr", "label": "PKR", "format": "pkr"},
                                    {"key": "range", "label": "90% band"},
                                    {"key": "predicted_roas", "label": "Pred. ROAS", "format": "x"},
                                    {"key": "marginal_roas", "label": "Marginal ROAS", "format": "x"},
                                    {"key": "reason", "label": "Why", "wide": True}],
                        "rows": [{**a, "range": f"{a['pct_low']:.0f}–{a['pct_high']:.0f}%"} for a in al]}),
    ]


def optimize_budget(budget: float = DEFAULT_BUDGET, min_pct: Any = None, max_pct: Any = None,
                    filters: dict | None = None, horizon_days: int = DEFAULT_HORIZON) -> ToolResult:
    """Recommend how to split a budget across the 5 platforms to maximise predicted revenue."""
    f = filters_of(filters)
    f.pop("platform", None)
    budget = float(budget or DEFAULT_BUDGET)
    horizon = int(horizon_days or DEFAULT_HORIZON)
    if not 1 <= horizon <= 365:
        raise ToolError("horizon_days must be 1..365")
    plan = _plan(budget, _pct_arg(min_pct), _pct_arg(max_pct), f, horizon, settings.n_boot)
    s = plan.summary
    summary = {
        **{k: r(v, 2) for k, v in s.items()}, "filters": f, "band_90pct": {k: r(v, 3) for k, v in plan.band.items()},
        "allocation": [{"platform": a["platform"], "pct": r(a["pct"], 1), "pkr": r(a["pkr"], 0),
                        "pct_range_90": [r(a["pct_low"], 1), r(a["pct_high"], 1)], "current_pct": r(a["current_pct"], 1),
                        "predicted_revenue": r(a["predicted_revenue"], 0), "predicted_roas": r(a["predicted_roas"], 2),
                        "marginal_roas": r(a["marginal_roas"], 2), "min_pct": r(a["min_pct"], 1),
                        "max_pct": r(a["max_pct"], 1), "reason": a["reason"]} for a in plan.alloc.values()],
        "curves": {p: {"first_rupee_roas": r(c["first_rupee_roas"], 2), "saturation_pkr_per_day": r(c["b"], 0),
                       "audience_multiplier": r(c["k"], 2), "fit_r2": r(c["r2"], 2)} for p, c in plan.curves.items()},
        "method": "revenue = a·log(1+daily_spend/b) per platform (curve_fit on daily data); allocation equalises "
                  "marginal ROAS within min/max caps; 90% band from bootstrap over days",
    }
    return result(summary, plan_charts(plan, f))


# ---------------------------------------------------------------- tool: compare_scenarios
def compare_scenarios(scenarios: list[dict] | None = None, budget: float = DEFAULT_BUDGET,
                      filters: dict | None = None, horizon_days: int = DEFAULT_HORIZON) -> ToolResult:
    """Compare 'what-if' budget scenarios (different budgets / caps / audiences) against the recommended plan,
    the current mix and an equal split."""
    base_f = filters_of(filters)
    base_f.pop("platform", None)
    budget = float(budget or DEFAULT_BUDGET)
    horizon = int(horizon_days or DEFAULT_HORIZON)
    n_boot = max(20, settings.n_boot // 2)
    base = _plan(budget, None, None, base_f, horizon, n_boot)
    rows = [
        {"name": "Recommended (default caps 5–60%)", "budget": budget, "revenue": base.summary["predicted_revenue"],
         "roas": base.summary["predicted_roas"], "low": base.band["revenue_p5"], "high": base.band["revenue_p95"],
         "alloc": {p: base.alloc[p]["pct"] for p in PLATFORMS}},
        {"name": "Current mix", "budget": budget, "revenue": base.summary["current_mix_revenue"],
         "roas": base.summary["current_mix_roas"], "alloc": {p: base.alloc[p]["current_pct"] for p in PLATFORMS}},
        {"name": "Equal split", "budget": budget, "revenue": base.summary["equal_split_revenue"],
         "roas": base.summary["equal_split_roas"], "alloc": {p: 20.0 for p in PLATFORMS}},
    ]
    for i, sc in enumerate((scenarios or [])[:4]):
        if not isinstance(sc, dict):
            raise ToolError("each scenario must be an object {name, budget, min_pct, max_pct, filters}")
        f = {**base_f, **filters_of(sc.get("filters"))}
        f.pop("platform", None)
        b = float(sc.get("budget") or budget)
        p = _plan(b, _pct_arg(sc.get("min_pct")), _pct_arg(sc.get("max_pct")), f, horizon, n_boot)
        rows.append({"name": str(sc.get("name") or f"Scenario {i + 1}"), "budget": b,
                     "revenue": p.summary["predicted_revenue"], "roas": p.summary["predicted_roas"],
                     "low": p.band["revenue_p5"], "high": p.band["revenue_p95"],
                     "alloc": {q: p.alloc[q]["pct"] for q in PLATFORMS},
                     "caps": {"min_pct": sc.get("min_pct"), "max_pct": sc.get("max_pct")}, "filters": f})
    ref = rows[0]["revenue"]
    for row in rows:
        row["vs_recommended_pct"] = (row["revenue"] / ref - 1) * 100 if ref else 0.0
    summary = {"budget": budget, "horizon_days": horizon, "filters": base_f, "scenarios": [
        {"name": x["name"], "budget": r(x["budget"], 0), "predicted_revenue": r(x["revenue"], 0),
         "predicted_roas": r(x["roas"], 3), "vs_recommended_pct": r(x["vs_recommended_pct"], 2),
         **({"revenue_band_90": [r(x["low"], 0), r(x["high"], 0)]} if "low" in x else {}),
         "allocation_pct": {p: r(v, 1) for p, v in x["alloc"].items()}} for x in rows]}
    names = [x["name"] for x in rows]
    charts = [
        ChartSpec(type="bar", title="Predicted revenue by scenario", subtitle=f"{horizon} days · {fdesc(base_f)}",
                  data={"categories": names, "format": "pkr", "horizontal": True,
                        "series": [{"name": "Predicted revenue", "values": [x["revenue"] for x in rows]}]}),
        ChartSpec(type="bar", title="Platform shares by scenario", subtitle="% of budget",
                  data={"categories": names, "format": "pct100", "stacked": True, "horizontal": True,
                        "series": [{"name": p, "values": [x["alloc"][p] for x in rows]} for p in PLATFORMS]}),
    ]
    return result(summary, charts)


# ---------------------------------------------------------------- tool: get_benchmark
ENGINE_LABEL = {"pandas": "Pandas", "mapreduce": "MapReduce (mrjob)", "spark": "PySpark",
                "pandas_parquet": "Pandas · Parquet", "spark_parquet": "PySpark · Parquet"}


def explain_benchmark(ok: pd.DataFrame) -> list[str]:
    """Auto-written 'when to use which' from the measured numbers (rules, no LLM)."""
    out: list[str] = []
    if ok.empty:
        return ["No successful runs yet — run `make bench`."]
    csv = ok[ok["input_format"] == "csv"]
    sizes = sorted(csv["rows"].unique())
    for n in (sizes[0], sizes[-1]) if len(sizes) > 1 else sizes:
        at = csv[csv["rows"] == n].sort_values("median_wall_s")
        if len(at):
            w = at.iloc[0]
            others = ", ".join(f"{ENGINE_LABEL[e]} {t:.2f}s" for e, t in zip(at["engine"][1:], at["median_wall_s"][1:]))
            out.append(f"At {n:,} rows the fastest end-to-end was {ENGINE_LABEL[w['engine']]} ({w['median_wall_s']:.2f}s); {others}.")
    sp = csv[csv["engine"] == "spark"]
    if len(sp):
        st = sp["median_startup_s"].median()
        out.append(f"PySpark pays a fixed ~{st:.1f}s to start its JVM session before reading a single row — "
                   "that dominates at small sizes; its per-row cost is what matters at 10M+ rows or on a cluster.")
    mr = csv[csv["engine"] == "mapreduce"]
    if len(mr) and len(sizes):
        t = mr.set_index("rows")["median_wall_s"]
        n = t.index[-1]
        spark_t = csv[(csv.engine == "spark") & (csv.rows == n)]["median_wall_s"]
        pandas_t = csv[(csv.engine == "pandas") & (csv.rows == n)]["median_wall_s"]
        cmp = []
        if len(pandas_t):
            cmp.append(f"{t.iloc[-1] / pandas_t.iloc[0]:.0f}× slower than Pandas")
        if len(spark_t):
            cmp.append(("faster" if t.iloc[-1] < spark_t.iloc[0] else "slower") + " than local Spark")
        out.append(f"MapReduce (mrjob local) spawns worker processes and writes/sorts intermediate data between map and "
                   f"reduce: {t.iloc[-1]:.2f}s at {n:,} rows ({', '.join(cmp)}). It teaches the model; it pays off only "
                   "on a Hadoop cluster with data already in HDFS.")
    pdp = ok[ok["engine"] == "pandas_parquet"].set_index("rows")["median_wall_s"]
    pdc = csv[csv["engine"] == "pandas"].set_index("rows")["median_wall_s"]
    common = sorted(set(pdp.index) & set(pdc.index))
    if common:
        n = common[-1]
        diff = (pdc[n] - pdp[n]) / pdc[n]
        if diff > 0.1:
            out.append(f"Columnar Parquet helps: Pandas read+aggregate took {pdp[n]:.2f}s on Parquet vs {pdc[n]:.2f}s on "
                       f"CSV at {n:,} rows (only 6 of 12 columns are read).")
        else:
            out.append(f"Parquet vs CSV makes no real difference yet ({pdp[n]:.2f}s vs {pdc[n]:.2f}s at {n:,} rows): "
                       "Python start-up dominates. Columnar reads should pull ahead at 1M+ rows.")
    pd_mem = csv[csv["engine"] == "pandas"].set_index("rows")["peak_mem_mb"]
    sp_mem = csv[csv["engine"] == "spark"].set_index("rows")["peak_mem_mb"]
    if len(pd_mem) >= 2:
        a, b = pd_mem.index[0], pd_mem.index[-1]
        grow = pd_mem[b] / pd_mem[a]
        line = (f"Pandas peak memory went {pd_mem[a]:.0f} MB → {pd_mem[b]:.0f} MB from {a:,} to {b:,} rows "
                f"(×{grow:.1f}); it must hold the data in RAM, so this grows with size.")
        if len(sp_mem) >= 1:
            line += (f" Spark sits at ~{sp_mem.max():.0f} MB mostly for its JVM; it processes partitions as a stream, "
                     "so it can handle data larger than RAM.")
        out.append(line)
    out.append("Rule of thumb: Pandas while the data fits comfortably in RAM (≲ a few GB); Spark when it doesn't, or when "
               "the same code must run on a cluster; MapReduce for teaching the model or legacy Hadoop pipelines.")
    return out


def get_benchmark() -> ToolResult:
    """Measured Pandas vs MapReduce vs Spark timings/memory for the platform KPI aggregation."""
    path = settings.bench_dir / "results.csv"
    if not path.exists():
        return result({"status": "not run", "note": "bench/results.csv not found — run `make bench`"},
                      [ChartSpec(type="text", title="Benchmark not run yet",
                                 data={"lines": ["Run `make bench` (or `make bench MAX_ROWS=100000`) to measure."]})])
    df = pd.read_csv(path)
    ok = df[df["status"] == "ok"].copy()
    engines = [e for e in ENGINE_LABEL if e in set(df["engine"])]
    sizes = sorted(df["rows"].unique())

    def series(metric):
        return [{"name": ENGINE_LABEL[e], "engine": e, "dashed": e.endswith("_parquet"),
                 "values": [(float(v.iloc[0]) if len(v := ok[(ok.engine == e) & (ok.rows == n)][metric]) else None)
                            for n in sizes]} for e in engines]
    lines = explain_benchmark(ok)
    failed = df[df["status"] != "ok"]
    rows = [{"engine": ENGINE_LABEL.get(x.engine, x.engine), "rows": int(x.rows), "status": x.status,
             "median_wall_s": x.median_wall_s, "median_compute_s": x.median_compute_s,
             "median_startup_s": x.median_startup_s, "peak_mem_mb": x.peak_mem_mb, "runs_ok": x.runs_ok,
             "agree": x.agree} for x in df.itertuples()]
    summary = {"sizes": [int(s) for s in sizes], "results": rows, "when_to_use": lines,
               "spark_status": "ok" if len(ok[ok.engine == "spark"]) else "failed or not run",
               "failed": [{"engine": x.engine, "rows": int(x.rows), "status": x.status} for x in failed.itertuples()],
               "all_agree": bool((ok["agree"].astype(str) == "yes").all()) if len(ok) else None,
               "measured_at": str(df["measured_at"].max())}
    charts = [
        ChartSpec(type="line", title="Wall time vs rows", subtitle="median of 3 runs · log–log · includes start-up",
                  data={"x": [int(s) for s in sizes], "series": series("median_wall_s"), "log_x": True, "log_y": True,
                        "format": "s", "x_format": "rows"}),
        ChartSpec(type="line", title="Peak memory vs rows", subtitle="max RSS of the whole process tree (incl. JVM / workers)",
                  data={"x": [int(s) for s in sizes], "series": series("peak_mem_mb"), "log_x": True,
                        "format": "mb", "x_format": "rows"}),
        ChartSpec(type="table", title="Benchmark results", subtitle=f"bench/results.csv · measured {summary['measured_at']}",
                  data={"columns": [{"key": "engine", "label": "Engine"}, {"key": "rows", "label": "Rows", "format": "int"},
                                    {"key": "status", "label": "Status"},
                                    {"key": "median_wall_s", "label": "Wall (s)", "format": "s"},
                                    {"key": "median_compute_s", "label": "Compute (s)", "format": "s"},
                                    {"key": "median_startup_s", "label": "Start-up (s)", "format": "s"},
                                    {"key": "peak_mem_mb", "label": "Peak MB", "format": "mb"},
                                    {"key": "agree", "label": "KPIs = Pandas"}], "rows": rows}),
        ChartSpec(type="text", title="When to use which", data={"lines": lines}),
    ]
    return result(summary, charts)


# ---------------------------------------------------------------- dashboard (page endpoint, not an agent tool)
def dashboard(filters: dict | None = None) -> ToolResult:
    f = filters_of(filters)
    df = subset(f)
    t = totals(df)
    plat = kpis_by(df, "platform").set_index("platform").reindex(PLATFORMS).fillna(0).reset_index()
    month = kpis_by(df, ["month", "platform"])
    months = sorted(month["month"].unique())
    m_tot = kpis_by(df, "month").set_index("month")
    cp = kpis_by(df, ["city", "platform"])
    cities = list(kpis_by(df, "city").sort_values("spend", ascending=False)["city"])
    plats = [p for p in PLATFORMS if p in set(cp["platform"])]
    heat = [[plats.index(row.platform), cities.index(row.city), r(row.roas, 3)] for row in cp.itertuples()]
    charts = [
        tiles(t),
        ChartSpec(type="bar", title="Platform comparison", subtitle="spend vs revenue · ROAS on the right axis",
                  data={"categories": PLATFORMS, "format": "pkr",
                        "series": [{"name": "Spend", "values": plat["spend"].tolist()},
                                   {"name": "Revenue", "values": plat["revenue"].tolist()}],
                        "line": {"name": "ROAS", "values": plat["roas"].tolist(), "format": "x"}}),
        ChartSpec(type="line", title="ROAS trend by month", subtitle="per platform · dashed = all platforms",
                  data={"x": months, "format": "x", "series": [
                      {"name": p, "values": [r(v, 3) if len(v := month[(month.month == m) & (month.platform == p)]["roas"])
                                             and (v := float(v.iloc[0])) else None for m in months]} for p in plats]
                      + [{"name": "All", "dashed": True, "values": [r(m_tot.loc[m, "roas"], 3) for m in months]}]}),
        ChartSpec(type="heatmap", title="ROAS · city × platform", subtitle="revenue / spend",
                  data={"x": plats, "y": cities, "values": heat, "format": "x"}),
        ChartSpec(type="funnel", title="Funnel", subtitle="impressions → clicks → conversions",
                  data={"stages": [{"name": "Impressions", "value": t["impressions"]},
                                   {"name": "Clicks", "value": t["clicks"], "rate": t["ctr"], "rate_label": "CTR"},
                                   {"name": "Conversions", "value": t["conversions"], "rate": t["cvr"],
                                    "rate_label": "Conv. rate"}]}),
        ChartSpec(type="table", title="Platform KPIs",
                  data={"columns": [{"key": "platform", "label": "Platform"}] +
                        [{"key": c, "label": METRIC_LABEL[c], "format": METRIC_FMT[c]}
                         for c in ["spend", "revenue", "roas", "profit", "ctr", "cpc", "cvr", "cpa", "cpm"]],
                        "rows": plat.to_dict("records")}),
    ]
    return result({"filters": f, "rows": int(len(df)), "totals": t}, charts)


def optimizer_page(budget: float = DEFAULT_BUDGET, min_pct: Any = None, max_pct: Any = None,
                   filters: dict | None = None, horizon_days: int = DEFAULT_HORIZON) -> ToolResult:
    res = optimize_budget(budget, min_pct, max_pct, filters, horizon_days)
    for c in res.charts:
        c.meta["inline"] = True
    return res


# ---------------------------------------------------------------- registry
TOOLS: dict[str, Callable[..., ToolResult]] = {
    "get_kpis": get_kpis,
    "optimize_budget": optimize_budget,
    "compare_scenarios": compare_scenarios,
    "get_benchmark": get_benchmark,
}
EXTRA: dict[str, Callable[..., ToolResult]] = {"dashboard": dashboard, "optimizer_page": optimizer_page}

FILTERS_SCHEMA = {
    "type": "object",
    "description": "Optional audience/data filters. Each value is one option or a comma-separated list.",
    "properties": {
        "platform": {"type": "string", "description": "Facebook, Instagram, Google, TikTok, YouTube"},
        "city": {"type": "string", "description": "Lahore, Karachi, Islamabad, Rawalpindi, Faisalabad, Multan, Peshawar"},
        "age": {"type": "string", "description": "18-24, 25-34, 35-44, 45-54, 55+"},
        "gender": {"type": "string", "description": "M or F"},
        "device": {"type": "string", "description": "mobile, desktop, tablet"},
        "campaign": {"type": "string", "description": "exact campaign name"},
        "month": {"type": "string", "description": "YYYY-MM"},
    },
}
PCT_SCHEMA = {
    "type": "object",
    "description": "Per-platform percentage of the budget (0-100), e.g. {\"TikTok\": 10}. Unlisted platforms keep the default.",
    "properties": {p: {"type": "number"} for p in PLATFORMS},
}
DECLS = [
    {"name": "get_kpis",
     "description": "Historical KPIs (spend, revenue, ROAS, CTR, CPC, CPA, conversion rate, profit) grouped by one "
                    "dimension, with optional filters. Use for 'how is X performing', comparisons, 'why is A better than B'.",
     "parameters_json_schema": {"type": "object", "properties": {
         "filters": FILTERS_SCHEMA,
         "group_by": {"type": "string", "enum": GROUPS, "description": "dimension to group by (default platform)"},
         "sort_by": {"type": "string", "enum": ["roas", "spend", "revenue", "profit", "ctr", "cvr", "cpc", "cpa"]},
         "top": {"type": "integer", "description": "max groups to return (default 12)"}}}},
    {"name": "optimize_budget",
     "description": "Recommend how to split a budget across Facebook, Instagram, Google, TikTok, YouTube to maximise "
                    "predicted revenue, using fitted diminishing-returns curves. Returns % and PKR per platform, "
                    "predicted revenue/ROAS with a 90% bootstrap band, uplift vs current mix and equal split, and a "
                    "reason per platform. Filters target an audience (city/age/gender/device).",
     "parameters_json_schema": {"type": "object", "properties": {
         "budget": {"type": "number", "description": "PKR, default 1000000"},
         "min_pct": PCT_SCHEMA | {"description": "minimum % per platform (default 5)"},
         "max_pct": PCT_SCHEMA | {"description": "maximum % per platform (default 60)"},
         "filters": FILTERS_SCHEMA,
         "horizon_days": {"type": "integer", "description": "days the budget is spent over (default 30)"}}}},
    {"name": "compare_scenarios",
     "description": "What-if comparison: the recommended plan, the current mix and an equal split, plus up to 4 custom "
                    "scenarios (e.g. TikTok capped at 10%, a bigger budget, a different audience).",
     "parameters_json_schema": {"type": "object", "properties": {
         "scenarios": {"type": "array", "items": {"type": "object", "properties": {
             "name": {"type": "string"}, "budget": {"type": "number"},
             "min_pct": PCT_SCHEMA, "max_pct": PCT_SCHEMA, "filters": FILTERS_SCHEMA}}},
         "budget": {"type": "number", "description": "PKR for the baselines, default 1000000"},
         "filters": FILTERS_SCHEMA,
         "horizon_days": {"type": "integer"}}}},
    {"name": "get_benchmark",
     "description": "Measured benchmark of the same platform-KPI aggregation in Pandas, MapReduce (mrjob) and PySpark "
                    "at several data sizes: wall time, memory, agreement, and when to use which.",
     "parameters_json_schema": {"type": "object", "properties": {}}},
]


def declarations() -> list[dict]:
    return DECLS


def call_tool(name: str, args: dict[str, Any]) -> ToolResult:
    fn = TOOLS.get(name) or EXTRA[name]  # KeyError → unknown tool
    params = inspect.signature(fn).parameters
    unknown = set(args) - set(params)
    if unknown:
        raise ToolError(f"unknown argument(s) for {name}: {', '.join(sorted(unknown))}")
    store.ensure()
    return fn(**args)
