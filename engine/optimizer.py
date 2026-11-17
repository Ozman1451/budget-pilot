"""Budget Recommendation Engine.

1. Fit a diminishing-returns response curve per platform on DAILY spend vs revenue:
       revenue_day(s) = a · log(1 + s / b)            (scipy.optimize.curve_fit)
   a/b is the ROAS of the first rupee; marginal ROAS at daily spend s is a / (b + s).
2. A budget B is spent over a horizon of H days (default 30), so x rupees on platform p earn
       H · a_p · log(1 + x / (H · b_p)).
3. Maximise total predicted revenue s.t. Σx = B and min/max % per platform. The objective is concave and
   separable, so the optimum equalises marginal ROAS (KKT "water-filling"): x_p(λ) = clip(H(a_p/λ − b_p), lo, hi),
   with λ found by bisection. Exact, fast enough to run inside a bootstrap.
4. Audience filter (e.g. city=Lahore, age=18-24): the curve SHAPE (saturation b) comes from the whole platform
   (filtered daily data is too thin to fit reliably and would be extrapolated far out of range), and its
   height is rescaled by k = ROAS(audience on p) / ROAS(all on p) — how much better/worse that audience converts
   on that platform.
5. Bootstrap: resample days with replacement, refit, re-optimise (~100×) → 5–95 % bands.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.optimize import OptimizeWarning, curve_fit

from .kpis import apply_filters, safe_div

PLATFORMS = ["Facebook", "Instagram", "Google", "TikTok", "YouTube"]
DEFAULT_BUDGET = 1_000_000.0
DEFAULT_HORIZON = 30
DEFAULT_MIN_PCT = 5.0
DEFAULT_MAX_PCT = 60.0


def response(s, a, b):
    return a * np.log1p(np.asarray(s, dtype=float) / b)


@dataclass
class Curve:
    platform: str
    a: float
    b: float
    k: float = 1.0          # audience multiplier
    r2: float = 0.0
    n_days: int = 0
    spend_min: float = 0.0
    spend_max: float = 0.0
    spend_mean: float = 0.0

    def revenue(self, x, horizon: float) -> np.ndarray:
        """Predicted revenue for total spend x over `horizon` days."""
        return self.k * horizon * response(np.asarray(x, float) / horizon, self.a, self.b)

    def marginal(self, x, horizon: float) -> np.ndarray:
        return self.k * self.a / (self.b + np.asarray(x, float) / horizon)


def daily(df: pd.DataFrame) -> pd.DataFrame:
    """Daily spend/revenue per platform (wide is not needed: long format)."""
    d = df.groupby(["date", "platform"], observed=True)[["spend", "revenue"]].sum().reset_index()
    d["platform"] = d["platform"].astype(str)
    return d


def fit_curve(spend: np.ndarray, revenue: np.ndarray, platform: str = "", p0=None) -> Curve:
    spend = np.asarray(spend, float)
    revenue = np.asarray(revenue, float)
    ok = spend > 0
    spend, revenue = spend[ok], revenue[ok]
    if len(spend) < 5:
        roas = safe_div(revenue.sum(), spend.sum())
        b = max(float(np.mean(spend)) if len(spend) else 1000.0, 1.0)
        return Curve(platform, roas * b, b, n_days=len(spend))
    s_mean = float(spend.mean())
    roas = float(revenue.sum() / spend.sum())
    p0 = list(p0) if p0 is not None else [roas * s_mean * 2, s_mean]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", OptimizeWarning)
        warnings.simplefilter("ignore", RuntimeWarning)
        try:
            (a, b), _ = curve_fit(response, spend, revenue, p0=p0,
                                  bounds=([1e-6, s_mean * 0.02], [np.inf, s_mean * 200]), maxfev=20000)
        except (RuntimeError, ValueError):
            a, b = p0
    pred = response(spend, a, b)
    ss_res = float(((revenue - pred) ** 2).sum())
    ss_tot = float(((revenue - revenue.mean()) ** 2).sum()) or 1.0
    return Curve(platform, float(a), float(b), r2=1 - ss_res / ss_tot, n_days=len(spend),
                 spend_min=float(spend.min()), spend_max=float(spend.max()), spend_mean=s_mean)


def audience_k(df_all: pd.DataFrame, df_aud: pd.DataFrame) -> dict[str, float]:
    """ROAS(audience on p) / ROAS(all on p) per platform; 0 if the audience has no spend there."""
    g_all = df_all.groupby("platform", observed=True)[["spend", "revenue"]].sum()
    g_aud = df_aud.groupby("platform", observed=True)[["spend", "revenue"]].sum()
    out = {}
    for p in PLATFORMS:
        if p not in g_aud.index or g_aud.loc[p, "spend"] <= 0 or p not in g_all.index:
            out[p] = 0.0
            continue
        r_aud = g_aud.loc[p, "revenue"] / g_aud.loc[p, "spend"]
        r_all = safe_div(g_all.loc[p, "revenue"], g_all.loc[p, "spend"])
        out[p] = float(safe_div(r_aud, r_all))
    return out


def wide(day_table: pd.DataFrame, index=None) -> tuple[np.ndarray, np.ndarray]:
    """Long daily table → (spend, revenue) arrays of shape (days, platforms)."""
    w = day_table.pivot_table(index="date", columns="platform", values=["spend", "revenue"], aggfunc="sum")
    if index is not None:
        w = w.reindex(index)
    w = w.fillna(0.0)
    get = lambda m: np.column_stack([w[m][p].to_numpy() if p in w[m].columns else np.zeros(len(w))
                                     for p in PLATFORMS])
    return get("spend"), get("revenue")


def fit_all(day_table: pd.DataFrame, k: dict[str, float] | None = None) -> dict[str, Curve]:
    curves = {}
    for p in PLATFORMS:
        d = day_table[day_table["platform"] == p]
        c = fit_curve(d["spend"].to_numpy(), d["revenue"].to_numpy(), p)
        if k is not None:
            c.k = k.get(p, 0.0)
        curves[p] = c
    return curves


# ---------------------------------------------------------------- allocation
def bounds_from_pct(budget: float, min_pct, max_pct) -> tuple[np.ndarray, np.ndarray]:
    def vec(v, default):
        if v is None:
            return np.full(len(PLATFORMS), default, float)
        if isinstance(v, (int, float)):
            return np.full(len(PLATFORMS), float(v))
        canon = {p.lower(): p for p in PLATFORMS}
        out = np.full(len(PLATFORMS), default, float)
        for key, val in dict(v).items():
            p = canon.get(str(key).lower())
            if p is None:
                raise ValueError(f"unknown platform '{key}'; options: {', '.join(PLATFORMS)}")
            if val is not None:
                out[PLATFORMS.index(p)] = float(val)
        return out
    lo = np.clip(vec(min_pct, DEFAULT_MIN_PCT), 0, 100)
    hi = np.clip(vec(max_pct, DEFAULT_MAX_PCT), 0, 100)
    hi = np.maximum(hi, lo)
    if lo.sum() > 100 + 1e-9:
        raise ValueError(f"minimum shares add up to {lo.sum():.0f}% (> 100%)")
    if hi.sum() < 100 - 1e-9:
        raise ValueError(f"maximum shares add up to only {hi.sum():.0f}% (< 100%) — budget can't be spent")
    return lo / 100 * budget, hi / 100 * budget


def allocate(curves: dict[str, Curve], budget: float, lo: np.ndarray, hi: np.ndarray, horizon: float) -> np.ndarray:
    """Water-filling: equalise marginal ROAS subject to lo ≤ x ≤ hi and Σx = budget."""
    a = np.array([curves[p].a * curves[p].k for p in PLATFORMS])
    b = np.array([curves[p].b for p in PLATFORMS])

    def x_of(lam: float) -> np.ndarray:
        return np.clip(horizon * (a / lam - b), lo, hi)

    lam_lo, lam_hi = 1e-12, max(float((a / b).max()), 1e-9) * 2 + 1
    for _ in range(200):
        mid = 0.5 * (lam_lo + lam_hi)
        if x_of(mid).sum() > budget:
            lam_lo = mid
        else:
            lam_hi = mid
    x = x_of(0.5 * (lam_lo + lam_hi))
    # close any rounding gap on platforms with room (keeps Σx == budget exactly)
    gap = budget - x.sum()
    room = np.where(gap > 0, hi - x, x - lo)
    if abs(gap) > 1e-9 and room.sum() > 0:
        x = x + np.sign(gap) * room / room.sum() * min(abs(gap), room.sum())
    return x


def predict(curves: dict[str, Curve], x: np.ndarray, horizon: float) -> np.ndarray:
    return np.array([curves[p].revenue(x[i], horizon) for i, p in enumerate(PLATFORMS)], dtype=float)


# ---------------------------------------------------------------- public API
@dataclass
class Plan:
    budget: float
    horizon: int
    filters: dict
    alloc: dict = field(default_factory=dict)
    summary: dict = field(default_factory=dict)
    curves: dict = field(default_factory=dict)
    band: dict = field(default_factory=dict)


def current_shares(df: pd.DataFrame) -> np.ndarray:
    g = df.groupby("platform", observed=True)["spend"].sum()
    s = np.array([float(g.get(p, 0.0)) for p in PLATFORMS])
    return s / s.sum() if s.sum() > 0 else np.full(len(PLATFORMS), 1 / len(PLATFORMS))


def _reason(p: str, i: int, x: np.ndarray, lo, hi, c: Curve, horizon: float, lam: float, cur_share: float,
            budget: float) -> str:
    share = x[i] / budget
    mroas = float(c.marginal(x[i], horizon))
    first = c.k * c.a / c.b
    daily_x = x[i] / horizon
    sat = f"its curve flattens past ~Rs {c.b:,.0f}/day" if c.b > 0 else ""
    if c.k == 0:
        return f"No spend history for this audience on {p}, so it only gets the minimum."
    if np.isclose(x[i], hi[i]) and hi[i] < budget:
        return (f"Capped at the {hi[i] / budget:.0%} maximum — still earning Rs {mroas:.2f} per extra rupee "
                f"(more than other platforms), so it would take more if allowed.")
    if np.isclose(x[i], lo[i]) and lo[i] > 0:
        return (f"Kept at the {lo[i] / budget:.0%} minimum: its first-rupee ROAS ({first:.2f}×) is below what "
                f"other platforms still earn at the margin.")
    move = "more than" if share > cur_share + 0.02 else "less than" if share < cur_share - 0.02 else "about the same as"
    return (f"Gets {share:.0%} ({move} today's {cur_share:.0%}) — spend rises until its marginal ROAS falls to "
            f"{mroas:.2f}×, the same as the others; {sat} (≈ Rs {daily_x:,.0f}/day here).")


def optimize(df: pd.DataFrame, budget: float = DEFAULT_BUDGET, min_pct=None, max_pct=None,
             filters: dict | None = None, horizon: int = DEFAULT_HORIZON, n_boot: int = 100,
             seed: int = 0) -> Plan:
    filters = filters or {}
    if budget <= 0:
        raise ValueError("budget must be positive")
    aud_filters = {k: v for k, v in filters.items() if k != "platform"}
    df_aud = apply_filters(df, aud_filters)
    if df_aud.empty:
        raise ValueError("no rows match these filters")
    day_all = daily(df)
    k = audience_k(df, df_aud) if aud_filters else None
    curves = fit_all(day_all, k)
    lo, hi = bounds_from_pct(budget, min_pct, max_pct)
    if k is not None:  # platforms with no audience history: force to their minimum
        hi = np.where(np.array([k[p] for p in PLATFORMS]) == 0, lo, hi)
        if hi.sum() < budget:
            raise ValueError("this audience only exists on platforms whose max caps can't absorb the budget")
    x = allocate(curves, budget, lo, hi, horizon)
    rev = predict(curves, x, horizon)

    cur = current_shares(df_aud) * budget
    eq = np.full(len(PLATFORMS), budget / len(PLATFORMS))
    rev_cur, rev_eq = predict(curves, cur, horizon).sum(), predict(curves, eq, horizon).sum()

    # bootstrap: resample days (wide day × platform arrays → fast)
    rng = np.random.default_rng(seed)
    all_dates = np.sort(day_all["date"].unique())
    S_all, R_all = wide(day_all, index=all_dates)
    if k is not None:
        S_aud, R_aud = wide(daily(df_aud), index=all_dates)
    boot_rev, boot_x, boot_up = [], [], []
    for _ in range(n_boot):
        pick = rng.integers(0, len(S_all), len(S_all))
        cb = {}
        for j, p in enumerate(PLATFORMS):
            cb[p] = fit_curve(S_all[pick, j], R_all[pick, j], p, p0=(curves[p].a, curves[p].b))
            if k is not None:
                ra = safe_div(R_aud[pick, j].sum(), S_aud[pick, j].sum())
                rl = safe_div(R_all[pick, j].sum(), S_all[pick, j].sum())
                cb[p].k = float(safe_div(ra, rl))
        hb = np.where(np.array([cb[p].k for p in PLATFORMS]) == 0, lo, hi) if k is not None else hi
        if hb.sum() < budget:
            continue
        xb = allocate(cb, budget, lo, hb, horizon)
        boot_x.append(xb)
        boot_rev.append(predict(cb, xb, horizon).sum())
        boot_up.append(boot_rev[-1] / max(predict(cb, cur, horizon).sum(), 1e-9) - 1)
    boot_rev = np.array(boot_rev) if boot_rev else np.array([rev.sum()])
    boot_x = np.array(boot_x) if boot_x else x[None, :]
    boot_up = np.array(boot_up) if boot_up else np.array([0.0])

    lam = float(np.median([curves[p].marginal(x[i], horizon) for i, p in enumerate(PLATFORMS)]))
    cur_sh = cur / budget
    plan = Plan(budget=budget, horizon=horizon, filters=filters)
    for i, p in enumerate(PLATFORMS):
        c = curves[p]
        plan.alloc[p] = {
            "platform": p, "pct": float(x[i] / budget * 100), "pkr": float(x[i]),
            "pct_low": float(np.percentile(boot_x[:, i], 5) / budget * 100),
            "pct_high": float(np.percentile(boot_x[:, i], 95) / budget * 100),
            "current_pct": float(cur_sh[i] * 100), "current_pkr": float(cur[i]),
            "predicted_revenue": float(rev[i]), "predicted_roas": float(safe_div(rev[i], x[i])),
            "marginal_roas": float(c.marginal(x[i], horizon)),
            "min_pct": float(lo[i] / budget * 100), "max_pct": float(hi[i] / budget * 100),
            "reason": _reason(p, i, x, lo, hi, c, horizon, lam, float(cur_sh[i]), budget),
        }
        plan.curves[p] = {"a": c.a, "b": c.b, "k": c.k, "r2": c.r2, "n_days": c.n_days,
                          "spend_min": c.spend_min, "spend_max": c.spend_max, "spend_mean": c.spend_mean,
                          "first_rupee_roas": c.k * c.a / c.b if c.b else 0.0}
    total = float(rev.sum())
    plan.summary = {
        "budget": budget, "horizon_days": horizon, "predicted_revenue": total,
        "predicted_roas": float(safe_div(total, budget)), "predicted_profit": total - budget,
        "current_mix_revenue": float(rev_cur), "equal_split_revenue": float(rev_eq),
        "uplift_vs_current_pct": float(safe_div(total - rev_cur, rev_cur) * 100),
        "uplift_vs_equal_pct": float(safe_div(total - rev_eq, rev_eq) * 100),
        "current_mix_roas": float(safe_div(rev_cur, budget)), "equal_split_roas": float(safe_div(rev_eq, budget)),
    }
    plan.band = {
        "n_boot": int(len(boot_rev)),
        "revenue_p5": float(np.percentile(boot_rev, 5)), "revenue_p95": float(np.percentile(boot_rev, 95)),
        "roas_p5": float(np.percentile(boot_rev, 5) / budget), "roas_p95": float(np.percentile(boot_rev, 95) / budget),
        "uplift_vs_current_p5": float(np.percentile(boot_up, 5) * 100),
        "uplift_vs_current_p95": float(np.percentile(boot_up, 95) * 100),
    }
    return plan


def curve_points(plan: Plan, n: int = 40) -> dict:
    """Response curves in 'total spend over the horizon' units for charts, + the chosen point."""
    out = {}
    H = plan.horizon
    for p in PLATFORMS:
        c = plan.curves[p]
        cv = Curve(p, c["a"], c["b"], c["k"])
        x_max = max(plan.budget * 0.8, plan.alloc[p]["pkr"] * 1.6, 1.0)
        xs = np.linspace(0, x_max, n)
        out[p] = {"x": xs.tolist(), "y": cv.revenue(xs, H).tolist(),
                  "point": [plan.alloc[p]["pkr"], plan.alloc[p]["predicted_revenue"]],
                  "current": [plan.alloc[p]["current_pkr"], float(cv.revenue(plan.alloc[p]["current_pkr"], H))]}
    return out
