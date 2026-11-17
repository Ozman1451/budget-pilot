import numpy as np
import pandas as pd

from data.generate import CITIES, COLUMNS, PLATFORMS


def test_schema_and_values(df, tiny):
    assert list(df.columns) == COLUMNS
    assert len(df) == 3000
    assert set(df["platform"].astype(str)) == set(PLATFORMS)
    assert set(df["city"].astype(str)) <= set(CITIES)
    assert (df["clicks"] <= df["impressions"]).all()
    assert (df["conversions"] <= df["clicks"]).all()
    assert (df[["impressions", "clicks", "spend", "conversions", "revenue"]] >= 0).all().all()
    days = pd.to_datetime(df["date"]).dt.date.nunique()
    assert days == 365
    csv = pd.read_csv(tiny.with_suffix(".csv"))
    assert len(csv) == 3000 and np.isclose(csv["spend"].sum(), df["spend"].sum())


def test_chunking_does_not_change_daily_business(tmp_path):
    """Same seed, different chunk sizes → same platform-day spend totals (whole platform-days per chunk)."""
    from data.generate import generate
    a = pd.read_parquet(generate(2500, seed=3, chunk=400, out=tmp_path / "a.parquet", csv=False))
    b = pd.read_parquet(generate(2500, seed=3, chunk=100000, out=tmp_path / "b.parquet", csv=False))
    ga = a.groupby(["date", "platform"], observed=True)["spend"].sum()
    gb = b.groupby(["date", "platform"], observed=True)["spend"].sum()
    assert np.allclose(ga.values, gb.values, atol=0.05 * 5)


def test_platform_skews(df):
    tt = df[df.platform == "TikTok"]
    g = df[df.platform == "Google"]
    assert (tt["age"] == "18-24").mean() > (g["age"] == "18-24").mean()
    assert (tt["device"] == "mobile").mean() > 0.9
    cvr = lambda d: d["conversions"].sum() / d["clicks"].sum()  # noqa: E731
    assert cvr(g) > cvr(df[df.platform == "YouTube"])
