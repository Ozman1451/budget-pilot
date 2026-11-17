import json
from typing import Any

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from . import llm, tools
from .agent import run_agent
from .config import settings
from .schemas import ToolResult
from .store import store

app = FastAPI(title="Budget Pilot")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _store():
    try:
        return store.ensure()
    except FileNotFoundError as exc:
        raise HTTPException(503, str(exc)) from exc


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/meta")
def meta() -> dict:
    s = _store()
    return {**s.info(), "datasets": s.available(), "options": s.options(), "tools": list(tools.TOOLS),
            "llm": {"has_key": llm.has_key(), "mock": llm.is_mock_chat(), "model": settings.gemini_chat_model}}


@app.post("/api/tool/{name}", response_model=ToolResult)
def call_tool(name: str, args: dict[str, Any] | None = Body(default=None)) -> ToolResult:
    _store()
    try:
        return tools.call_tool(name, args or {})
    except KeyError as exc:
        raise HTTPException(404, f"unknown tool '{name}'") from exc
    except (tools.ToolError, TypeError) as exc:
        raise HTTPException(400, str(exc)) from exc


class ChatIn(BaseModel):
    messages: list[dict[str, Any]]


def _sse(events):
    for ev in events:
        yield f"event: {ev.event}\ndata: {json.dumps(ev.data, ensure_ascii=False)}\n\n"


@app.post("/api/chat")
def chat(body: ChatIn) -> StreamingResponse:
    return StreamingResponse(_sse(run_agent(body.messages)), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
