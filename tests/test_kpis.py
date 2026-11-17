import numpy as np
import pandas as pd
import pytest

from engine.kpis import finalize, kpis_by, norm_filters, safe_div, totals


def test_formulas():
    d = finalize(pd.DataFrame([{"impressions": 1000, "clicks": 50, "spend": 500.0, "conversions": 5, "revenue": 2000.0}]))
    r = d.iloc[0]
    assert r.ctr == pytest.approx(0.05)
    assert r.cpc == pytest.approx(10)
    assert r.cpm == pytest.approx(500)
    assert r.cpa == pytest.approx(100)
    assert r.cvr == pytest.approx(0.1)
    assert r.roas == pytest.approx(4)
    assert r.profit == pytest.approx(1500)
    assert r.aov == pytest.approx(400)


def test_safe_division_never_inf_or_nan():
    d = finalize(pd.DataFrame([{"impressions": 0, "clicks": 0, "spend": 0.0, "conversions": 0, "revenue": 0.0},
                               {"impressions": 10, "clicks": 0, "spend": 5.0, "conversions": 0, "revenue": 0.0}]))
    assert np.isfinite(d.select_dtypes("number").to_numpy()).all()
    assert d.loc[1, "cpc"] == 0 and d.loc[1, "cpa"] == 0
    assert safe_div(1, 0) == 0.0


def test_group_by_sums_match_totals(df):
    t = totals(df)
    for g in ("platform", "city", "age", "gender", "device", "month", "campaign"):
        k = kpis_by(df, g)
        assert k["spend"].sum() == pytest.approx(t["spend"])
        assert k["revenue"].sum() == pytest.approx(t["revenue"])
        assert np.isfinite(k.select_dtypes("number").to_numpy()).all()


def test_filters_normalise():
    opts = {"city": ["Lahore", "Karachi"], "gender": ["M", "F"], "platform": ["Facebook", "YouTube"]}
    assert norm_filters({"city": "karachi", "gender": "female", "platform": "yt"}, opts) == \
        {"city": ["Karachi"], "gender": ["F"], "platform": ["YouTube"]}
    with pytest.raises(ValueError):
        norm_filters({"city": "Quetta"}, opts)
