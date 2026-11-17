"""Shared pydantic schemas: every tool returns {summary, charts}; the UI renders charts by `type` only."""
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

ChartType = Literal["kpi_tiles", "bar", "line", "donut", "heatmap", "funnel", "table", "curves", "text"]


class ChartSpec(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: ChartType
    title: str = ""
    subtitle: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    meta: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    summary: dict[str, Any] = Field(default_factory=dict)
    charts: list[ChartSpec] = Field(default_factory=list)


EventType = Literal["tool_start", "tool_result", "text_delta", "done", "error"]


class SSEEvent(BaseModel):
    event: EventType
    data: dict[str, Any] = Field(default_factory=dict)
