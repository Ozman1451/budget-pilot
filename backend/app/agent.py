"""Gemini function-calling agent loop (reused from Need Map Chat). Yields SSE events:
tool_start {tool,args} · tool_result {tool,summary,charts} · text_delta {text} · done · error {message}."""
import json
import logging
from collections.abc import Iterator

from . import llm, tools
from .schemas import SSEEvent

log = logging.getLogger("budgetpilot.agent")

MAX_STEPS = 4          # tool-calling rounds per user turn
HISTORY = 10           # last N chat messages sent to the model
SUMMARY_CHARS = 7000   # ≈1.7k tokens fed back per tool result

SYSTEM = """You are Budget Pilot, a digital-advertising budget analyst for a Pakistani retail brand. Management asks \
"Where should we spend the next Rs. 1,000,000?" across Facebook, Instagram, Google, TikTok and YouTube. Currency is PKR (write "Rs").
Rules:
- Never invent or compute numbers yourself. Call a tool for ANY number and only quote numbers that appear in tool results \
(round sensibly, e.g. Rs 312,400 or 3.18×). If you need a number no tool gave you, call another tool.
- Budget questions → optimize_budget. "What if…/cap/limit/compare plans" → compare_scenarios (put caps in max_pct as \
percent, e.g. {"TikTok": 10}). Performance, "why is A better than B" → get_kpis (group_by platform) and, for the \
diminishing-returns part, optimize_budget's `curves` (first_rupee_roas, saturation_pkr_per_day). Benchmark / Big Data / \
Spark / MapReduce questions → get_benchmark.
- Audience phrases map to filters: "Karachi 18-24 on mobile" → {"city": "Karachi", "age": "18-24", "device": "mobile"}.
- Always state the predicted range (90% bootstrap band) next to a prediction — it's a model, not a promise.
- Format: 2–4 short sentences, then up to 4 bullets ("- ") with **bold** platform names. Charts and tables appear under \
your message automatically — refer to them, don't repeat every number.
- If a tool returns an error, explain it briefly and suggest a valid alternative.
- The data is synthetic (12 months, 5 platforms); mention it once only if asked about data quality."""


def _ev(event: str, **data) -> SSEEvent:
    return SSEEvent(event=event, data=data)


def to_contents(messages: list[dict]) -> list:
    """[{role: user|assistant, content: str}] → SDK contents (last HISTORY messages, starting with a user turn)."""
    msgs = [m for m in messages if str(m.get("content", "")).strip()][-HISTORY:]
    while msgs and msgs[0].get("role") != "user":
        msgs = msgs[1:]
    return [llm.user_content(m["content"]) if m["role"] == "user" else llm.model_content(m["content"])
            for m in msgs]


def compact(summary: dict) -> dict:
    """Tool summary for the model, capped at SUMMARY_CHARS of JSON (lists trimmed from the end)."""
    s = json.loads(json.dumps(summary, ensure_ascii=False))
    while len(json.dumps(s, ensure_ascii=False)) > SUMMARY_CHARS:
        lists = [(k, v) for k, v in s.items() if isinstance(v, list) and len(v) > 1]
        if not lists:
            s.pop("formulas", None)
            if len(json.dumps(s, ensure_ascii=False)) <= SUMMARY_CHARS:
                break
            return {"truncated": json.dumps(s, ensure_ascii=False)[:SUMMARY_CHARS]}
        k, v = max(lists, key=lambda kv: len(json.dumps(kv[1], ensure_ascii=False)))
        s[k] = v[: max(1, len(v) * 2 // 3)]
        s["truncated"] = True
    return s


def run_agent(messages: list[dict]) -> Iterator[SSEEvent]:
    try:
        if not llm.is_mock_chat() and not llm.has_key():
            yield _ev("error", message="Add GEMINI_API_KEY to .env (copy .env.example) and restart the backend. "
                                       "Or set MOCK_CHAT=1 to try the offline keyword router.")
            return
        contents = to_contents(messages)
        if not contents:
            yield _ev("error", message="empty message")
            return
        decls = tools.declarations()
        for step in range(MAX_STEPS + 1):
            r = llm.chat(contents, decls if step < MAX_STEPS else [], SYSTEM)
            if not r["function_calls"]:
                yield _ev("text_delta", text=r["text"] or "I couldn't produce an answer — please rephrase.")
                break
            contents.append(r["content"] or llm.calls_content(r["function_calls"]))
            responses = []
            for fc in r["function_calls"]:
                name, args = fc["name"], fc["args"]
                yield _ev("tool_start", tool=name, args=args)
                try:
                    res = tools.call_tool(name, args)
                    summary, charts = res.summary, [c.model_dump() for c in res.charts]
                except (tools.ToolError, KeyError, TypeError) as exc:
                    msg = f"unknown tool {name}" if isinstance(exc, KeyError) else str(exc)
                    summary, charts = {"error": msg}, []
                yield _ev("tool_result", tool=name, summary=summary, charts=charts)
                responses.append({"id": fc.get("id"), "name": name, "response": compact(summary)})
            contents.append(llm.responses_content(responses))
        yield _ev("done")
    except Exception as exc:  # quota, network, missing data → one error event for the UI
        quota = isinstance(exc, llm.DailyQuotaExceeded) or getattr(exc, "code", None) == 429
        if isinstance(exc, llm.MissingKey):
            msg = str(exc)
        elif quota:
            log.warning("Gemini quota exceeded")
            msg = "Gemini quota exceeded — try again in a minute (or set MOCK_CHAT=1)."
        else:
            log.exception("agent failed")
            msg = f"{type(exc).__name__}: {str(exc)[:300]}"
        yield _ev("error", message=msg)
