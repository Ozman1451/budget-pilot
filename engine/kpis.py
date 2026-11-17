"""KPI engine: CTR, CPC, CPM, CPA, conversion rate, ROAS, revenue, profit — by any dimension.

All ratios use safe division (0 when the denominator is 0), so output never contains inf/NaN.
`finalize` works on any table of summed base metrics, so the Pandas / MapReduce / Spark benchmark jobs
share exactly the same KPI formulas.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

BASE = ["impressions", "clicks", "spend", "conversions", "revenue"]
DIMENSIONS = ["platform", "campaign", "city", "age", "gender", "device", "month", "date"]
FILTER_KEYS = ["platform", "campaign", "city", "age", "gender", "device", "month"]
KPI_FORMULAS = {
    "ctr": "clicks / impressions",
    "cpc": "spend / clicks",
    "cpm": "spend / impressions × 1000",
    "cpa": "spend / conversions",
    "cvr": "conversions / clicks",
    "roas": "revenue / spend",
    "profit": "revenue − spend",
    "aov": "revenue / conversions",
}


def safe_div(num, den):
    """Elementwise num/den with 0 where den == 0 (scalars or arrays/Series)."""
    num_a = np.asarray(num, dtype="float64")
    den_a = np.asarray(den, dtype="float64")
    out = np.divide(num_a, den_a, out=np.zeros(np.broadcast(num_a, den_a).shape), where=den_a != 0)
    out = np.nan_to_num(out, nan=0.0, posinf=0.0, neginf=0.0)
    if isinstance(num, pd.Series):
        return pd.Series(out, index=num.index)
    return float(out) if out.ndim == 0 else out


def finalize(sums: pd.DataFrame) -> pd.DataFrame:
    """Add KPI columns to a frame that has the BASE sum columns."""
    d = sums.copy()
    d["ctr"] = safe_div(d["clicks"], d["impressions"])
    d["cpc"] = safe_div(d["spend"], d["clicks"])
    d["cpm"] = safe_div(d["spend"], d["impressions"]) * 1000
    d["cpa"] = safe_div(d["spend"], d["conversions"])
    d["cvr"] = safe_div(d["conversions"], d["clicks"])
    d["roas"] = safe_div(d["revenue"], d["spend"])
    d["profit"] = d["revenue"] - d["spend"]
    d["aov"] = safe_div(d["revenue"], d["conversions"])
    return d


def totals(df: pd.DataFrame) -> dict:
    s = df[BASE].sum()
    row = finalize(pd.DataFrame([s.to_dict()])).iloc[0]
    return {k: float(v) for k, v in row.items()}


def norm_filters(filters: dict | None, options: dict[str, list[str]] | None = None) -> dict[str, list[str]]:
    """{'city': 'karachi', 'age': ['18-24']} → {'city': ['Karachi'], 'age': ['18-24']} (case-insensitive,
    validated against `options` when given). Unknown keys / empty values are dropped."""
    out: dict[str, list[str]] = {}
    for k, v in (filters or {}).items():
        k = str(k).lower().strip()
        if k not in FILTER_KEYS or v in (None, "", [], "all", "All"):
            continue
        vals = v if isinstance(v, (list, tuple)) else [v]
        vals = [str(x).strip() for x in vals if str(x).strip() and str(x).lower() != "all"]
        if options and k in options:
            canon = {o.lower(): o for o in options[k]}
            alias = {"male": "m", "female": "f", "men": "m", "women": "f", "mobile phone": "mobile",
                     "phone": "mobile", "pc": "desktop", "fb": "facebook", "ig": "instagram", "yt": "youtube",
                     "55-64": "55+", "65+": "55+"}
            fixed = []
            for x in vals:
                key = alias.get(x.lower(), x.lower())
                if key not in canon:
                    raise ValueError(f"unknown {k} '{x}'; options: {', '.join(options[k])}")
                fixed.append(canon[key])
            vals = fixed
        if vals:
            out[k] = vals
    return out


def apply_filters(df: pd.DataFrame, filters: dict[str, list[str]]) -> pd.DataFrame:
    if not filters:
        return df
    mask = np.ones(len(df), dtype=bool)
    for k, vals in filters.items():
        col = df[k].astype(str) if k == "month" else df[k]
        mask &= col.isin(vals).to_numpy()
    return df[mask]


def with_month(df: pd.DataFrame) -> pd.DataFrame:
    if "month" not in df.columns:
        df = df.assign(month=pd.to_datetime(df["date"]).dt.strftime("%Y-%m"))
    return df


def kpis_by(df: pd.DataFrame, group_by: str | list[str] | None = "platform") -> pd.DataFrame:
    """Sum BASE metrics by `group_by` and add KPIs. group_by None → one 'total' row."""
    if not group_by:
        return pd.DataFrame([{"group": "total", **totals(df)}])
    keys = [group_by] if isinstance(group_by, str) else list(group_by)
    for k in keys:
        if k not in DIMENSIONS:
            raise ValueError(f"unknown group_by '{k}'; options: {', '.join(DIMENSIONS)}")
    if "month" in keys:
        df = with_month(df)
    sums = df.groupby(keys, observed=True, sort=True)[BASE].sum().reset_index()
    for k in keys:
        if isinstance(sums[k].dtype, pd.CategoricalDtype):
            sums[k] = sums[k].astype(str)
    return finalize(sums)


def load(path: str | Path, columns: list[str] | None = None) -> pd.DataFrame:
    path = Path(path)
    if path.suffix == ".csv":
        return pd.read_csv(path, usecols=columns)
    return pd.read_parquet(path, columns=columns)
