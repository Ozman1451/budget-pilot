"""API + agent loop, offline (MOCK_CHAT router — no network)."""
import json

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client(tiny):
    from app import store as store_mod
    from app.config import settings
    s = store_mod.store
    s.df = None
    # load the tiny dataset directly
    import pandas as pd
    df = pd.read_parquet(tiny)
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.strftime("%Y-%m").astype("category")
    s.df, s.dataset, s.path = df, "tiny", tiny
    s._cache.clear()
    settings.n_boot = 10
    settings.mock_chat = True
    from app.main import app
    yield TestClient(app)
    s.df = None
    settings.mock_chat = False


def test_health_and_meta(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    m = client.get("/api/meta").json()
    assert m["rows"] == 3000 and "Karachi" in m["options"]["city"]


@pytest.mark.parametrize("name,args", [
    ("get_kpis", {"group_by": "city", "filters": {"platform": "TikTok"}}),
    ("optimize_budget", {"budget": 500000, "max_pct": {"TikTok": 10}}),
    ("compare_scenarios", {"scenarios": [{"name": "cap", "max_pct": {"TikTok": 10}}]}),
    ("get_benchmark", {}),
    ("dashboard", {"filters": {"city": "Lahore"}}),
])
def test_tools(client, name, args):
    r = client.post(f"/api/tool/{name}", json=args)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["charts"] and "summary" in body
    json.dumps(body, allow_nan=False)  # strict JSON: no NaN/inf


def test_tool_errors_are_400(client):
    assert client.post("/api/tool/get_kpis", json={"group_by": "planet"}).status_code == 400
    assert client.post("/api/tool/optimize_budget", json={"min_pct": 40}).status_code == 400
    assert client.post("/api/tool/nope", json={}).status_code == 404


def test_chat_stream_mock(client):
    with client.stream("POST", "/api/chat", json={"messages": [{"role": "user", "content": "What if TikTok is capped at 10%?"}]}) as r:
        text = "".join(r.iter_text())
    events = [b.split("\n")[0].removeprefix("event: ") for b in text.strip().split("\n\n")]
    assert events[0] == "tool_start" and "tool_result" in events and events[-1] == "done"
    assert "compare_scenarios" in text


def test_mock_router():
    from app.llm import mock_route
    assert mock_route("Where should the next Rs. 1M go?") == ("optimize_budget", {"filters": {}, "budget": 1e6})
    name, args = mock_route("What if TikTok is capped at 10%?")
    assert name == "compare_scenarios" and args["scenarios"][0]["max_pct"] == {"TikTok": 10.0}
    name, args = mock_route("Best platform for Karachi 18-24 on mobile?")
    assert name == "optimize_budget" and args["filters"] == {"city": "Karachi", "age": "18-24", "device": "mobile"}
    assert mock_route("Why is Google better than YouTube?")[0] == "get_kpis"
    assert mock_route("How did Spark compare?")[0] == "get_benchmark"
