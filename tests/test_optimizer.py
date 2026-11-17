import numpy as np
import pytest

from engine.optimizer import PLATFORMS, Curve, allocate, bounds_from_pct, fit_curve, optimize, response


def test_curve_fit_recovers_parameters():
    rng = np.random.default_rng(0)
    s = rng.uniform(1000, 40000, 400)
    y = response(s, 30000, 8000) * rng.lognormal(0, 0.05, 400)
    c = fit_curve(s, y)
    assert c.a == pytest.approx(30000, rel=0.1)
    assert c.b == pytest.approx(8000, rel=0.15)
    assert c.r2 > 0.9


def test_allocation_sums_to_budget_and_respects_caps():
    curves = {p: Curve(p, a, b) for p, a, b in zip(PLATFORMS, [30e3, 36e3, 26e3, 40e3, 22e3], [9e3, 7e3, 3.5e3, 12e3, 12e3])}
    for budget in (1e5, 1e6, 5e6):
        lo, hi = bounds_from_pct(budget, {"YouTube": 10}, {"TikTok": 10, "Google": 30})
        x = allocate(curves, budget, lo, hi, 30)
        assert x.sum() == pytest.approx(budget, rel=1e-9)
        assert (x >= lo - 1e-6).all() and (x <= hi + 1e-6).all()
        assert x[PLATFORMS.index("TikTok")] <= 0.1 * budget + 1e-6
        assert x[PLATFORMS.index("YouTube")] >= 0.1 * budget - 1e-6


def test_interior_optimum_equalises_marginal_roas():
    curves = {p: Curve(p, a, b) for p, a, b in zip(PLATFORMS, [30e3, 36e3, 26e3, 40e3, 22e3], [9e3, 7e3, 3.5e3, 12e3, 12e3])}
    lo, hi = bounds_from_pct(1e6, 0, 100)
    x = allocate(curves, 1e6, lo, hi, 30)
    m = [curves[p].marginal(x[i], 30) for i, p in enumerate(PLATFORMS) if x[i] > 1]
    assert max(m) - min(m) < 1e-3


def test_infeasible_caps_raise():
    with pytest.raises(ValueError):
        bounds_from_pct(1e6, 30, None)  # 5 × 30% > 100%
    with pytest.raises(ValueError):
        bounds_from_pct(1e6, None, 15)  # 5 × 15% < 100%


def test_optimize_end_to_end(df):
    plan = optimize(df, budget=1_000_000, max_pct={"TikTok": 10}, n_boot=15)
    total = sum(a["pkr"] for a in plan.alloc.values())
    assert total == pytest.approx(1_000_000, rel=1e-9)
    assert plan.alloc["TikTok"]["pct"] <= 10 + 1e-6
    assert all(a["pct"] >= 5 - 1e-6 for a in plan.alloc.values())
    assert plan.band["revenue_p5"] <= plan.band["revenue_p95"]
    assert all(a["reason"] for a in plan.alloc.values())


def test_optimize_with_audience_filter(df):
    plan = optimize(df, filters={"city": ["Karachi"], "age": ["18-24"]}, n_boot=10)
    assert sum(a["pct"] for a in plan.alloc.values()) == pytest.approx(100)
    assert plan.curves["TikTok"]["k"] > 0
