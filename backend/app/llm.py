"""Sole Gemini gateway (google-genai SDK) — plumbing reused from Need Map Chat.

Model name from env, tenacity backoff on 429/5xx, client-side per-minute rate gate, one function-calling
turn per `chat()` call (automatic function calling off, so the agent loop stays ours).
MOCK_LLM=1 / MOCK_CHAT=1 → deterministic offline keyword router (tests, demos without a key).
"""
from __future__ import annotations

import logging
import os
import re
import threading
import time
from collections import deque
from contextlib import contextmanager

from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential_jitter

from .config import settings

log = logging.getLogger("budgetpilot.llm")


# ---------------------------------------------------------------- plumbing
def is_mock_chat() -> bool:
    env = lambda k: os.environ.get(k, "").lower() in ("1", "true", "yes")  # noqa: E731
    return env("MOCK_LLM") or env("MOCK_CHAT") or settings.mock_llm or settings.mock_chat


def has_key() -> bool:
    return bool(settings.gemini_api_key.strip())


class MissingKey(RuntimeError):
    """No GEMINI_API_KEY: the UI shows an 'Add GEMINI_API_KEY' banner."""


HTTP_TIMEOUT_MS = 120_000
_client_obj = None
_client_lock = threading.Lock()


def _client():
    global _client_obj
    if not has_key():
        raise MissingKey("Add GEMINI_API_KEY to .env (see .env.example) and restart the backend.")
    with _client_lock:  # one shared client; a GC'd duplicate would close its httpx client mid-request
        if _client_obj is None:
            from google import genai
            from google.genai import types
            _client_obj = genai.Client(api_key=settings.gemini_api_key,
                                       http_options=types.HttpOptions(timeout=HTTP_TIMEOUT_MS))
    return _client_obj


class DailyQuotaExceeded(RuntimeError):
    """A 429 naming a per-day quota: retrying today is pointless."""


def is_daily_quota(exc: BaseException) -> bool:
    return getattr(exc, "code", None) == 429 and "PerDay" in str(exc)


def _retryable(exc: BaseException) -> bool:
    import httpx
    from google.genai import errors
    if is_daily_quota(exc):
        return False
    if isinstance(exc, httpx.TimeoutException):
        return True
    return isinstance(exc, errors.APIError) and (exc.code == 429 or (exc.code or 0) >= 500)


def _warn_retry(state) -> None:
    exc = state.outcome.exception()
    log.warning("Gemini %s (attempt %d) — backing off %.0fs", getattr(exc, "code", type(exc).__name__),
                state.attempt_number, state.next_action.sleep if state.next_action else 0)


_retry = retry(retry=retry_if_exception(_retryable), wait=wait_exponential_jitter(initial=5, max=40),
               stop=stop_after_attempt(4), before_sleep=_warn_retry, reraise=True)


class RateGate:
    """Client-side limiter over a sliding 60 s window: ≤ rpm requests, one in flight."""

    def __init__(self, rpm: int, clock=time.monotonic, sleep=time.sleep):
        self.rpm, self.clock, self.sleep = max(1, rpm), clock, sleep
        self.sent: deque[float] = deque()
        self.lock = threading.Lock()

    @contextmanager
    def slot(self):
        with self.lock:
            while True:
                now = self.clock()
                while self.sent and now - self.sent[0] >= 60:
                    self.sent.popleft()
                if len(self.sent) < self.rpm:
                    break
                wait = 60 - (now - self.sent[0]) + 0.05
                log.info("rate limit (%d req/min) reached — waiting %.1fs", self.rpm, wait)
                self.sleep(wait)
            self.sent.append(self.clock())
            yield


_gate = RateGate(settings.gemini_rpm)


# ---------------------------------------------------------------- live chat (agent)
def user_content(text: str):
    from google.genai import types
    return types.Content(role="user", parts=[types.Part(text=text)])


def model_content(text: str):
    from google.genai import types
    return types.Content(role="model", parts=[types.Part(text=text)])


def calls_content(calls: list[dict]):
    """Model turn for function calls when no SDK Content came back (mock)."""
    from google.genai import types
    return types.Content(role="model", parts=[types.Part(function_call=types.FunctionCall(
        id=c.get("id"), name=c["name"], args=c["args"])) for c in calls])


def responses_content(results: list[dict]):
    """results: [{id, name, response: dict}] → one user turn of function responses."""
    from google.genai import types
    return types.Content(role="user", parts=[types.Part(function_response=types.FunctionResponse(
        id=r.get("id"), name=r["name"], response=r["response"])) for r in results])


def chat(contents: list, tools: list[dict], system: str) -> dict:
    """One function-calling turn. tools: FunctionDeclaration dicts (name, description, parameters_json_schema).
    → {"text", "function_calls": [{"id","name","args"}], "content": model Content for history (keeps thought
    signatures, so it must be appended as-is)}."""
    if is_mock_chat():
        return _mock_chat(contents, tools)
    from google.genai import types
    cfg = types.GenerateContentConfig(
        system_instruction=system,
        tools=[types.Tool(function_declarations=[types.FunctionDeclaration(**t) for t in tools])] if tools else None,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    model = settings.gemini_chat_model
    client = _client()

    def call():
        with _gate.slot():
            return client.models.generate_content(model=model, contents=contents, config=cfg)
    try:
        resp = _retry(call)()
    except Exception as exc:
        if is_daily_quota(exc):
            raise DailyQuotaExceeded(str(exc)[:300]) from exc
        raise
    calls = [{"id": fc.id, "name": fc.name, "args": dict(fc.args or {})} for fc in (resp.function_calls or [])]
    content = resp.candidates[0].content if resp.candidates else None
    text = "".join(p.text for p in (content.parts or []) if p.text and not p.thought) if content else ""
    return {"text": "" if calls else text, "function_calls": calls, "content": content}


# ---------------------------------------------------------------- offline router (MOCK_CHAT)
PLATFORM_WORDS = {"facebook": "Facebook", "instagram": "Instagram", "google": "Google", "tiktok": "TikTok",
                  "youtube": "YouTube"}
CITY_WORDS = ["lahore", "karachi", "islamabad", "rawalpindi", "faisalabad", "multan", "peshawar"]


def mock_route(text: str) -> tuple[str, dict]:
    """Keyword router used by MOCK_CHAT and by tests: user text → (tool, args)."""
    t = text.lower()
    filters: dict = {}
    for c in CITY_WORDS:
        if c in t:
            filters["city"] = c.title()
    m = re.search(r"\b(18-24|25-34|35-44|45-54|55\+)", t)
    if m:
        filters["age"] = m.group(1)
    for d in ("mobile", "desktop", "tablet"):
        if d in t:
            filters["device"] = d
    if any(w in t for w in ("benchmark", "spark", "mapreduce", "big data", "pandas")):
        return "get_benchmark", {}
    caps = {}
    for w, p in PLATFORM_WORDS.items():
        m = re.search(rf"{w}[^.%\d]*?(?:capped|cap|max(?:imum)?|at most|limit(?:ed)?)\D{{0,12}}(\d+)\s*%", t) or \
            re.search(rf"(?:cap|limit)\s+{w}\D{{0,12}}(\d+)\s*%", t)
        if m:
            caps[p] = float(m.group(1))
    if caps or "what if" in t or "scenario" in t or "compare" in t and "budget" in t:
        return "compare_scenarios", {"scenarios": [{"name": "Your scenario", "max_pct": caps}] if caps else [],
                                     "filters": filters}
    if any(w in t for w in ("why", " vs ", "versus", "better than")):
        plats = [p for w, p in PLATFORM_WORDS.items() if w in t]
        return "get_kpis", {"group_by": "platform", "filters": {"platform": ",".join(plats)} if plats else {}}
    if any(w in t for w in ("spend", "budget", "allocate", "where should", "next rs", "best platform", "optimi")):
        m = re.search(r"rs\.?\s*([\d.,]+)\s*(m|k|lakh|million)?", t)
        args: dict = {"filters": filters}
        if m:
            v = float(m.group(1).replace(",", ""))
            mult = {"m": 1e6, "million": 1e6, "k": 1e3, "lakh": 1e5}.get(m.group(2) or "", 1)
            args["budget"] = v * mult
        return "optimize_budget", args
    gb = next((g for g in ("city", "age", "gender", "device", "month", "campaign") if g in t), "platform")
    return "get_kpis", {"group_by": gb, "filters": filters}


def _mock_chat(contents: list, tools: list[dict]) -> dict:
    last = contents[-1] if contents else None
    parts = getattr(last, "parts", None) or []
    responses = [p.function_response for p in parts if p.function_response]
    if responses or not tools:
        return {"text": _mock_answer(responses), "function_calls": [], "content": None}
    text = " ".join(p.text for p in parts if p.text)
    name, args = mock_route(text)
    calls = [{"id": "mock-1", "name": name, "args": args}]
    return {"text": "", "function_calls": calls, "content": calls_content(calls)}


def _mock_answer(responses: list) -> str:
    if not responses:
        return "Offline mode: ask me where to spend the budget."
    fr = responses[-1]
    s = dict(fr.response or {})
    if "error" in s:
        return f"Offline mode: {fr.name} failed — {s['error']}"
    if fr.name == "optimize_budget" and "allocation" in s:
        top = sorted(s["allocation"], key=lambda r: -r["pct"])[:3]
        lines = "\n".join(f"- **{r['platform']}** {r['pct']:.0f}% (Rs {r['pkr']:,.0f}) — {r['reason']}" for r in top)
        return (f"Offline mode (MOCK_CHAT): recommended split predicts **Rs {s['predicted_revenue']:,.0f}** revenue "
                f"(ROAS {s['predicted_roas']:.2f}×), {s['uplift_vs_current_pct']:+.1f}% vs the current mix.\n{lines}")
    return f"Offline mode (MOCK_CHAT): {fr.name} returned its results — see the charts below."
