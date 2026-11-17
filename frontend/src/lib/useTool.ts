"use client";

import { useEffect, useState } from "react";
import { useApp } from "@/components/AppProvider";
import { callTool } from "./api";
import type { ToolResult } from "./types";

/** Call a backend tool whenever `key` (JSON of args) changes; aborts stale requests; keeps the last result while loading. */
export function useTool(name: string, args: Record<string, unknown> | null, delayMs = 0) {
  const { toast } = useApp();
  const [data, setData] = useState<ToolResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const key = JSON.stringify(args);
  useEffect(() => {
    if (key === "null") {
      setLoading(false);
      return;
    }
    const ctl = new AbortController();
    setLoading(true);
    const t = setTimeout(() => {
      callTool(name, JSON.parse(key), ctl.signal)
        .then((r) => {
          setData(r);
          setError(null);
        })
        .catch((e) => {
          if (ctl.signal.aborted) return;
          setError(e.message);
          toast(e.message);
        })
        .finally(() => !ctl.signal.aborted && setLoading(false));
    }, delayMs);
    return () => {
      clearTimeout(t);
      ctl.abort();
    };
  }, [name, key, delayMs, toast]);
  return { data, loading, error };
}

export const clean = (o: Record<string, unknown>) =>
  Object.fromEntries(Object.entries(o).filter(([, v]) => v != null && v !== ""));
