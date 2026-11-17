"""In-memory dataset (one Parquet file from data/) + small caches. Loaded lazily, once."""
from __future__ import annotations

import json
import threading
from collections import OrderedDict
from pathlib import Path

import pandas as pd

from engine.kpis import FILTER_KEYS

from .config import settings

PREFERRED = ["100k", "10k", "1m", "10m"]


class Store:
    def __init__(self) -> None:
        self.df: pd.DataFrame | None = None
        self.dataset: str | None = None
        self.path: Path | None = None
        self._lock = threading.Lock()
        self._cache: OrderedDict[str, object] = OrderedDict()

    def available(self) -> dict[str, int]:
        import pyarrow.parquet as pq
        out = {}
        for p in sorted(settings.data_dir.glob("ads_*.parquet")):
            out[p.stem.removeprefix("ads_")] = pq.ParquetFile(p).metadata.num_rows
        return out

    def pick(self) -> str:
        avail = self.available()
        if settings.bp_dataset:
            if settings.bp_dataset not in avail:
                raise FileNotFoundError(f"data/ads_{settings.bp_dataset}.parquet not found — run make data")
            return settings.bp_dataset
        for name in PREFERRED:
            if name in avail:
                return name
        raise FileNotFoundError("no dataset in data/ — run: make data  (python data/generate.py --rows 100000)")

    def ensure(self) -> "Store":
        with self._lock:
            if self.df is None:
                self.load(self.pick())
        return self

    def load(self, name: str) -> None:
        path = settings.data_dir / f"ads_{name}.parquet"
        df = pd.read_parquet(path)
        df["date"] = pd.to_datetime(df["date"])
        df["month"] = df["date"].dt.strftime("%Y-%m").astype("category")
        self.df, self.dataset, self.path = df, name, path
        self._cache.clear()

    def options(self) -> dict[str, list[str]]:
        df = self.ensure().df
        out = {}
        for k in FILTER_KEYS:
            col = df[k]
            cats = list(col.cat.categories) if isinstance(col.dtype, pd.CategoricalDtype) else sorted(col.unique())
            out[k] = [str(c) for c in cats]
        return out

    def info(self) -> dict:
        df = self.ensure().df
        return {"dataset": self.dataset, "rows": int(len(df)), "date_min": df["date"].min().date().isoformat(),
                "date_max": df["date"].max().date().isoformat(), "currency": "PKR",
                "platforms": self.options()["platform"], "is_synthetic": True}

    def cached(self, key: dict, fn):
        k = json.dumps(key, sort_keys=True, default=str)
        if k in self._cache:
            self._cache.move_to_end(k)
            return self._cache[k]
        v = fn()
        self._cache[k] = v
        while len(self._cache) > 64:
            self._cache.popitem(last=False)
        return v


store = Store()
