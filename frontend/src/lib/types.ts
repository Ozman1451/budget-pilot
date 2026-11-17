export type ChartType = "kpi_tiles" | "bar" | "line" | "donut" | "heatmap" | "funnel" | "table" | "curves" | "text";

/* eslint-disable @typescript-eslint/no-explicit-any */
export interface ChartSpec {
  id: string;
  type: ChartType;
  title: string;
  subtitle: string;
  data: Record<string, any>;
  meta: Record<string, any>;
}

export interface ToolResult {
  summary: Record<string, any>;
  charts: ChartSpec[];
}

export type SSEEvent =
  | { event: "tool_start"; data: { tool: string; args: Record<string, unknown> } }
  | { event: "tool_result"; data: { tool: string; summary: Record<string, unknown>; charts: ChartSpec[] } }
  | { event: "text_delta"; data: { text: string } }
  | { event: "done"; data: Record<string, never> }
  | { event: "error"; data: { message: string } };

export interface TraceStep {
  tool: string;
  args: Record<string, unknown>;
  status: "running" | "done" | "error";
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  steps?: TraceStep[];
  charts?: ChartSpec[];
  error?: string;
  pending?: boolean;
}

export interface Meta {
  dataset: string;
  rows: number;
  date_min: string;
  date_max: string;
  currency: string;
  platforms: string[];
  datasets: Record<string, number>;
  options: Record<"platform" | "campaign" | "city" | "age" | "gender" | "device" | "month", string[]>;
  llm: { has_key: boolean; mock: boolean; model: string };
}

export type Filters = Partial<Record<"platform" | "city" | "age" | "gender" | "device" | "month", string>>;

export type Ask = (text: string) => void;
