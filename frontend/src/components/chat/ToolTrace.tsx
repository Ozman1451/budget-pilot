"use client";

import { motion } from "framer-motion";
import { Check, Loader2, X } from "lucide-react";
import type { TraceStep } from "@/lib/types";

const LABEL: Record<string, string> = {
  get_kpis: "Computing KPIs",
  optimize_budget: "Fitting response curves & optimising the split",
  compare_scenarios: "Comparing budget scenarios",
  get_benchmark: "Reading benchmark results",
};

function argText(args: Record<string, unknown>) {
  const parts: string[] = [];
  for (const [k, v] of Object.entries(args)) {
    if (v == null || v === "" || (typeof v === "object" && !Object.keys(v as object).length)) continue;
    if (k === "budget") parts.push(`Rs ${Number(v).toLocaleString("en-US")}`);
    else if (typeof v === "object") parts.push(`${k} ${JSON.stringify(v).replace(/["{}]/g, "").replace(/,/g, ", ")}`);
    else parts.push(`${k}=${v}`);
  }
  return parts.join(" · ");
}

export function ToolTrace({ steps }: { steps: TraceStep[] }) {
  return (
    <ol className="mb-2 space-y-1" data-testid="tool-trace">
      {steps.map((s, i) => (
        <motion.li
          key={i}
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-2 text-xs text-muted-foreground"
        >
          <span className="relative flex size-4 items-center justify-center">
            {s.status === "running" && <Loader2 className="size-3.5 animate-spin text-[#F5A524]" />}
            {s.status === "done" && (
              <motion.span
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: "spring", stiffness: 500, damping: 22 }}
                className="flex size-4 items-center justify-center rounded-full bg-gradient-to-br from-[#E94BA8] to-[#F5A524]"
              >
                <Check className="size-2.5 text-black" strokeWidth={3.5} />
              </motion.span>
            )}
            {s.status === "error" && <X className="size-3.5 text-red-400" />}
          </span>
          <span className={s.status === "done" ? "text-foreground/80" : ""}>
            {LABEL[s.tool] ?? s.tool}
            {s.status === "running" ? "…" : ""}
          </span>
          {argText(s.args) && <span className="font-mono text-[10px] text-muted-foreground/70">{argText(s.args)}</span>}
        </motion.li>
      ))}
    </ol>
  );
}
