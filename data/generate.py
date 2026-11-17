"""Synthetic ad-campaign performance data for Budget Pilot (5 platforms, 12 months, PKR).

python data/generate.py --rows 10000|100000|1000000|10000000 [--seed 7] [--chunk 500000]

Realism, not uniform noise:
- each platform has its own CPM, CTR, AOV and audience skew (age / gender / device / city);
- daily spend per platform follows seasonality (11.11, White/Black Friday, 12.12, Ramadan → Eid ul Fitr,
  Eid ul Adha, 14 August) plus day-to-day budget noise;
- **diminishing returns**: expected revenue per platform-day = a_p * log(1 + spend/b_p) * demand(day),
  so the optimizer has a real curve to find;
- within a platform-day, revenue is split across rows by campaign objective (retargeting converts best)
  and audience segment value (e.g. TikTok 18-24 mobile, Google desktop), so filtered analyses differ.

Rows = (date, campaign, platform, age, gender, city, device) breakdown rows. More rows → finer breakdown of
the same business (daily totals do not depend on --rows). Generated in chunks of whole platform-days and
streamed to Parquet (dictionary-encoded strings), so 10M rows never sit in RAM at once.
"""
from __future__ import annotations

import argparse
import time
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

DATA_DIR = Path(__file__).resolve().parent
START = date(2025, 11, 1)
DAYS = 365

PLATFORMS = ["Facebook", "Instagram", "Google", "TikTok", "YouTube"]
AGES = ["18-24", "25-34", "35-44", "45-54", "55+"]
GENDERS = ["M", "F"]
CITIES = ["Lahore", "Karachi", "Islamabad", "Rawalpindi", "Faisalabad", "Multan", "Peshawar"]
DEVICES = ["mobile", "desktop", "tablet"]
COLUMNS = ["date", "campaign", "platform", "impressions", "clicks", "spend", "conversions", "revenue",
           "age", "gender", "city", "device"]

# Per-platform economics. a/b = ROAS of the first rupee, a/(b+s) = marginal ROAS at daily spend s.
P = {
    #            share  CPM   CTR     AOV   a       b
    "Facebook":  (0.32, 150, 0.0110, 3500, 30000, 9000),
    "Instagram": (0.22, 180, 0.0090, 4000, 36000, 7000),
    "Google":    (0.14, 900, 0.0350, 4500, 26000, 3500),
    "TikTok":    (0.17, 70, 0.0140, 2500, 40000, 12000),
    "YouTube":   (0.15, 45, 0.0035, 3000, 22000, 12000),
}
BASE_DAILY_SPEND = 33_000  # PKR/day across all platforms ≈ Rs 1M / month

# Audience mix per platform (probabilities) and conversion-value multipliers.
AGE_MIX = {
    "Facebook":  [0.18, 0.32, 0.25, 0.15, 0.10],
    "Instagram": [0.34, 0.38, 0.17, 0.08, 0.03],
    "Google":    [0.16, 0.33, 0.27, 0.15, 0.09],
    "TikTok":    [0.55, 0.30, 0.10, 0.04, 0.01],
    "YouTube":   [0.28, 0.30, 0.20, 0.13, 0.09],
}
AGE_VALUE = {
    "Facebook":  [0.8, 1.1, 1.15, 1.0, 0.8],
    "Instagram": [1.0, 1.2, 0.9, 0.7, 0.6],
    "Google":    [0.8, 1.1, 1.2, 1.1, 0.9],
    "TikTok":    [1.35, 0.85, 0.6, 0.5, 0.4],
    "YouTube":   [0.9, 1.05, 1.1, 1.0, 0.9],
}
FEMALE_SHARE = {"Facebook": 0.45, "Instagram": 0.60, "Google": 0.42, "TikTok": 0.52, "YouTube": 0.40}
FEMALE_VALUE = {"Facebook": 1.1, "Instagram": 1.15, "Google": 1.0, "TikTok": 1.05, "YouTube": 0.95}
DEVICE_MIX = {
    "Facebook":  [0.82, 0.12, 0.06],
    "Instagram": [0.93, 0.04, 0.03],
    "Google":    [0.58, 0.36, 0.06],
    "TikTok":    [0.97, 0.01, 0.02],
    "YouTube":   [0.62, 0.20, 0.18],
}
DEVICE_VALUE = {
    "Facebook":  [1.0, 1.1, 0.9],
    "Instagram": [1.0, 0.9, 0.9],
    "Google":    [0.85, 1.35, 1.0],
    "TikTok":    [1.0, 0.6, 0.7],
    "YouTube":   [0.9, 1.2, 1.1],
}
CITY_MIX = np.array([0.27, 0.30, 0.11, 0.08, 0.10, 0.08, 0.06])
CITY_VALUE = {  # small per-platform city tilts (Karachi loves TikTok, Islamabad searches)
    "Facebook":  [1.0, 1.0, 1.0, 1.0, 1.05, 1.1, 1.1],
    "Instagram": [1.1, 1.05, 1.1, 0.9, 0.85, 0.85, 0.8],
    "Google":    [1.0, 1.0, 1.25, 1.1, 0.9, 0.9, 0.85],
    "TikTok":    [1.0, 1.25, 0.85, 0.95, 1.0, 0.95, 1.05],
    "YouTube":   [1.0, 0.95, 1.0, 1.0, 1.05, 1.05, 1.1],
}
OBJECTIVE_VALUE = {"Retargeting": 1.8, "Conversions": 1.25, "Traffic": 0.85, "Awareness": 0.45,
                   "Brand Search": 1.6, "Prospecting": 0.9}

# (campaign name, start, end, platforms, objective) — ~40 campaigns.
_ALL = PLATFORMS
_META = ["Facebook", "Instagram"]
CAMPAIGNS: list[tuple[str, date, date, list[str], str]] = [
    ("Always-On – Prospecting", date(2025, 11, 1), date(2026, 10, 31), ["Facebook", "Instagram", "TikTok", "YouTube"], "Prospecting"),
    ("Always-On – Brand Search", date(2025, 11, 1), date(2026, 10, 31), ["Google"], "Brand Search"),
    ("Always-On – Retargeting", date(2025, 11, 1), date(2026, 10, 31), _META + ["Google"], "Retargeting"),
    ("Generic Search – Clothing", date(2025, 11, 1), date(2026, 10, 31), ["Google"], "Conversions"),
    ("YouTube Bumpers – Brand", date(2025, 11, 1), date(2026, 10, 31), ["YouTube"], "Awareness"),
    ("TikTok Spark Ads – Creators", date(2025, 11, 1), date(2026, 10, 31), ["TikTok"], "Traffic"),
    ("Winter Launch – Awareness", date(2025, 11, 1), date(2025, 12, 15), _ALL, "Awareness"),
    ("Winter Launch – Conversions", date(2025, 11, 5), date(2025, 12, 31), _META + ["Google"], "Conversions"),
    ("11.11 Mega Sale – Teaser", date(2025, 11, 3), date(2025, 11, 10), _META + ["TikTok"], "Awareness"),
    ("11.11 Mega Sale – Conversions", date(2025, 11, 9), date(2025, 11, 13), _ALL, "Conversions"),
    ("11.11 Mega Sale – Retargeting", date(2025, 11, 10), date(2025, 11, 14), _META + ["Google"], "Retargeting"),
    ("White Friday – Flash Sale", date(2025, 11, 24), date(2025, 11, 30), _ALL, "Conversions"),
    ("White Friday – Retargeting", date(2025, 11, 26), date(2025, 12, 1), _META + ["Google"], "Retargeting"),
    ("12.12 Sale – Conversions", date(2025, 12, 8), date(2025, 12, 13), _ALL, "Conversions"),
    ("12.12 Sale – Retargeting", date(2025, 12, 10), date(2025, 12, 14), _META, "Retargeting"),
    ("Winter Shawls – Catalog", date(2025, 12, 1), date(2026, 1, 31), _META + ["Google"], "Conversions"),
    ("New Year – Clearance", date(2025, 12, 26), date(2026, 1, 10), _META + ["TikTok", "Google"], "Conversions"),
    ("Valentine's Edit – Traffic", date(2026, 2, 5), date(2026, 2, 14), ["Instagram", "TikTok"], "Traffic"),
    ("Spring Lawn – Awareness", date(2026, 2, 1), date(2026, 3, 10), _ALL, "Awareness"),
    ("Spring Lawn – Conversions", date(2026, 2, 10), date(2026, 4, 15), _META + ["Google", "TikTok"], "Conversions"),
    ("Ramadan Collection – Awareness", date(2026, 2, 12), date(2026, 3, 5), _ALL, "Awareness"),
    ("Ramadan Collection – Traffic", date(2026, 2, 18), date(2026, 3, 12), _META + ["TikTok"], "Traffic"),
    ("Eid Sale – Prospecting", date(2026, 3, 1), date(2026, 3, 19), _ALL, "Prospecting"),
    ("Eid Sale – Conversions", date(2026, 3, 8), date(2026, 3, 20), _META + ["Google", "TikTok"], "Conversions"),
    ("Eid Sale – Retargeting", date(2026, 3, 10), date(2026, 3, 21), _META + ["Google"], "Retargeting"),
    ("Chand Raat – Flash Sale", date(2026, 3, 18), date(2026, 3, 20), _META + ["TikTok"], "Conversions"),
    ("Summer Lawn Vol.2 – Awareness", date(2026, 4, 10), date(2026, 5, 20), _ALL, "Awareness"),
    ("Summer Lawn Vol.2 – Conversions", date(2026, 4, 15), date(2026, 6, 30), _META + ["Google"], "Conversions"),
    ("Eid ul Adha – Prospecting", date(2026, 5, 12), date(2026, 5, 26), _ALL, "Prospecting"),
    ("Eid ul Adha – Retargeting", date(2026, 5, 18), date(2026, 5, 28), _META + ["Google"], "Retargeting"),
    ("Mid-Summer Sale – Conversions", date(2026, 6, 20), date(2026, 7, 15), _ALL, "Conversions"),
    ("Mid-Summer Sale – Retargeting", date(2026, 6, 25), date(2026, 7, 18), _META + ["Google"], "Retargeting"),
    ("Monsoon Edit – Traffic", date(2026, 7, 15), date(2026, 8, 10), ["Instagram", "TikTok", "YouTube"], "Traffic"),
    ("Azadi Sale 14 Aug – Conversions", date(2026, 8, 8), date(2026, 8, 16), _ALL, "Conversions"),
    ("Azadi Sale 14 Aug – Awareness", date(2026, 8, 1), date(2026, 8, 14), ["TikTok", "YouTube", "Facebook"], "Awareness"),
    ("Back to Campus – Prospecting", date(2026, 8, 20), date(2026, 9, 20), ["Instagram", "TikTok", "YouTube"], "Prospecting"),
    ("Festive Formals – Conversions", date(2026, 9, 1), date(2026, 10, 15), _META + ["Google"], "Conversions"),
    ("Wedding Season – Awareness", date(2026, 9, 15), date(2026, 10, 31), _ALL, "Awareness"),
    ("Wedding Season – Retargeting", date(2026, 10, 1), date(2026, 10, 31), _META + ["Google"], "Retargeting"),
    ("Autumn Pret – Catalog", date(2026, 10, 1), date(2026, 10, 31), _META + ["Google", "TikTok"], "Conversions"),
]

# (day offset window, spend multiplier, demand multiplier)
EVENTS = [
    (date(2025, 11, 9), date(2025, 11, 12), 2.6, 1.25),   # 11.11
    (date(2025, 11, 27), date(2025, 11, 30), 2.3, 1.2),   # White / Black Friday
    (date(2025, 12, 10), date(2025, 12, 13), 2.0, 1.15),  # 12.12
    (date(2026, 3, 8), date(2026, 3, 20), 2.4, 1.25),     # Eid ul Fitr run-up + Chand Raat
    (date(2026, 5, 18), date(2026, 5, 27), 1.7, 1.12),    # Eid ul Adha
    (date(2026, 8, 10), date(2026, 8, 14), 1.5, 1.1),     # 14 August
]


def _dates() -> np.ndarray:
    return np.array([np.datetime64(START) + np.timedelta64(i, "D") for i in range(DAYS)])


def platform_days(rng: np.random.Generator) -> pd.DataFrame:
    """One row per (day, platform): planned spend S and expected revenue R (diminishing returns)."""
    days = [START + timedelta(days=i) for i in range(DAYS)]
    spend_mult = np.ones(DAYS)
    demand = np.ones(DAYS)
    for i, d in enumerate(days):
        for s, e, sm, dm in EVENTS:
            if s <= d <= e:
                spend_mult[i] = max(spend_mult[i], sm)
                demand[i] = max(demand[i], dm)
        if d.weekday() in (4, 5, 6):  # Fri–Sun shopping bump
            spend_mult[i] *= 1.08
        if date(2026, 6, 1) <= d <= date(2026, 7, 31):  # summer lull
            demand[i] *= 0.95
    rows = []
    for p, (share, *_rest, a, b) in P.items():
        noise = rng.lognormal(0, 0.45, DAYS)
        s = BASE_DAILY_SPEND * share * spend_mult * noise
        r = a * np.log1p(s / b) * demand
        rows.append(pd.DataFrame({"day": np.arange(DAYS), "platform": p, "S": s, "R": r}))
    return pd.concat(rows).sort_values(["day", "platform"], kind="stable").reset_index(drop=True)


def _active_matrix(pdays: pd.DataFrame) -> np.ndarray:
    """(n_platform_days, n_campaigns) CDF of campaign choice per platform-day (active campaigns only)."""
    w = np.zeros((len(pdays), len(CAMPAIGNS)))
    day_dates = np.array([START + timedelta(days=int(i)) for i in pdays["day"]])
    plats = pdays["platform"].to_numpy()
    for j, (_, s, e, plist, obj) in enumerate(CAMPAIGNS):
        on = (day_dates >= s) & (day_dates <= e) & np.isin(plats, plist)
        w[on, j] = 0.6 if obj in ("Prospecting", "Brand Search") and s == START else 1.0
    w /= w.sum(1, keepdims=True)
    return np.cumsum(w, 1)


def _choice(rng, n: int, p) -> np.ndarray:
    return np.searchsorted(np.cumsum(p), rng.random(n) * np.sum(p)).clip(0, len(p) - 1)


def make_chunk(rng, pdays: pd.DataFrame, cdf: np.ndarray, idx: np.ndarray, counts: np.ndarray) -> dict:
    """Rows for the platform-days `idx` (each with `counts` rows) → dict of column arrays."""
    pd_local = np.repeat(np.arange(len(idx)), counts)
    pd_global = idx[pd_local]
    n = len(pd_local)
    plat_codes = pd.Categorical(pdays["platform"].to_numpy()[pd_global], categories=PLATFORMS).codes
    age = np.empty(n, np.int8)
    gender = np.empty(n, np.int8)
    device = np.empty(n, np.int8)
    city = np.empty(n, np.int8)
    value = np.empty(n)
    cpm = np.empty(n)
    ctr = np.empty(n)
    aov = np.empty(n)
    for k, p in enumerate(PLATFORMS):
        m = plat_codes == k
        nk = int(m.sum())
        if not nk:
            continue
        a_ = _choice(rng, nk, AGE_MIX[p])
        g_ = (rng.random(nk) < FEMALE_SHARE[p]).astype(np.int8)  # 1 = F
        d_ = _choice(rng, nk, DEVICE_MIX[p])
        c_ = _choice(rng, nk, CITY_MIX)
        age[m], gender[m], device[m], city[m] = a_, g_, d_, c_
        value[m] = (np.asarray(AGE_VALUE[p])[a_] * np.where(g_ == 1, FEMALE_VALUE[p], 1.0)
                    * np.asarray(DEVICE_VALUE[p])[d_] * np.asarray(CITY_VALUE[p])[c_])
        _, cpm_p, ctr_p, aov_p, _, _ = P[p]
        cpm[m] = cpm_p * rng.lognormal(0, 0.15, nk) * np.where(d_ == 1, 1.15, 1.0)
        ctr[m] = ctr_p * rng.lognormal(0, 0.2, nk) * np.where(d_ == 1, 1.1, 1.0)
        aov[m] = aov_p
    # campaign per row from that platform-day's active set
    u = rng.random(n)
    camp = (cdf[pd_global] < u[:, None]).sum(1).clip(0, len(CAMPAIGNS) - 1).astype(np.int16)
    obj_val = np.array([OBJECTIVE_VALUE[c[4]] for c in CAMPAIGNS])[camp]

    # spend split within platform-day, revenue split by spend × audience value × objective value
    w = rng.gamma(1.5, 1.0, n)
    v = w * value * obj_val
    w_sum = np.bincount(pd_local, w, len(idx))[pd_local]
    v_sum = np.bincount(pd_local, v, len(idx))[pd_local]
    S = pdays["S"].to_numpy()[pd_global]
    R = pdays["R"].to_numpy()[pd_global]
    spend = np.round(S * w / w_sum, 2)
    impressions = np.maximum(np.round(spend / cpm * 1000), 0).astype(np.int64)
    exp_clicks = impressions * ctr
    clicks = rng.binomial(impressions, np.clip(ctr, 0, 1))
    exp_conv = (R * v / v_sum) / aov
    p_conv = np.clip(exp_conv / np.maximum(exp_clicks, 1e-9), 0, 1)
    conversions = rng.binomial(clicks, p_conv)
    revenue = np.round(conversions * aov * rng.lognormal(-0.03, 0.25, n), 2)
    days = pdays["day"].to_numpy()[pd_global]
    return {"date": (np.datetime64(START) + days.astype("timedelta64[D]")).astype("datetime64[D]"),
            "campaign": camp, "platform": plat_codes.astype(np.int8), "impressions": impressions,
            "clicks": clicks.astype(np.int64), "spend": spend, "conversions": conversions.astype(np.int64),
            "revenue": revenue, "age": age, "gender": gender, "city": city, "device": device}


DICTS = {"campaign": [c[0] for c in CAMPAIGNS], "platform": PLATFORMS, "age": AGES, "gender": GENDERS,
         "city": CITIES, "device": DEVICES}


def to_table(cols: dict) -> pa.Table:
    arrays = {}
    for name in COLUMNS:
        v = cols[name]
        if name in DICTS:
            idx_type = pa.int16() if name == "campaign" else pa.int8()
            arrays[name] = pa.DictionaryArray.from_arrays(pa.array(v.astype(np.int16 if name == "campaign" else np.int8),
                                                                   type=idx_type), pa.array(DICTS[name]))
        elif name == "date":
            arrays[name] = pa.array(v, type=pa.date32())
        else:
            arrays[name] = pa.array(v)
    return pa.table(arrays)


def label(rows: int) -> str:
    for unit, div in (("m", 1_000_000), ("k", 1_000)):
        if rows >= div and rows % div == 0:
            return f"{rows // div}{unit}"
    return str(rows)


def parquet_path(rows: int) -> Path:
    return DATA_DIR / f"ads_{label(rows)}.parquet"


def generate(rows: int, seed: int = 7, chunk: int = 500_000, csv: bool | None = None, out: Path | None = None) -> Path:
    rng = np.random.default_rng(seed)
    pdays = platform_days(np.random.default_rng(seed))  # same business for every --rows
    cdf = _active_matrix(pdays)
    # rows per platform-day ∝ spend, at least 1
    n_pd = len(pdays)
    if rows < n_pd:
        raise SystemExit(f"--rows must be ≥ {n_pd} (one row per platform-day)")
    share = pdays["S"].to_numpy() / pdays["S"].sum()
    counts = 1 + rng.multinomial(rows - n_pd, share)
    out = out or parquet_path(rows)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".parquet.tmp")
    writer = None
    csv = rows <= 10_000 if csv is None else csv
    csv_parts = []
    start, written = 0, 0
    cum = np.cumsum(counts)
    while start < n_pd:
        # whole platform-days until ~chunk rows
        end = int(np.searchsorted(cum, (cum[start - 1] if start else 0) + chunk, side="right"))
        end = max(end, start + 1)
        idx = np.arange(start, min(end, n_pd))
        cols = make_chunk(rng, pdays, cdf, idx, counts[idx])
        table = to_table(cols)
        if writer is None:
            writer = pq.ParquetWriter(tmp, table.schema, compression="snappy")
        writer.write_table(table)
        if csv:
            csv_parts.append(table.to_pandas())
        written += table.num_rows
        start = idx[-1] + 1
    writer.close()
    tmp.replace(out)
    if csv:
        pd.concat(csv_parts).to_csv(out.with_suffix(".csv"), index=False)
    assert written == rows, (written, rows)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--rows", type=int, default=100_000)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--chunk", type=int, default=500_000, help="rows per Parquet row group / RAM chunk")
    ap.add_argument("--csv", action="store_true", help="also write CSV (default only for ≤10K rows)")
    args = ap.parse_args()
    t0 = time.perf_counter()
    path = generate(args.rows, args.seed, args.chunk, csv=args.csv or None)
    print(f"wrote {args.rows:,} rows → {path.relative_to(DATA_DIR.parent)} in {time.perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    main()
