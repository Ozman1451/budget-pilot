"use client";

import { motion } from "framer-motion";
import { fmt } from "@/lib/format";
import type { ChartSpec } from "@/lib/types";

/** Log-scaled horizontal funnel bars (impressions dwarf conversions on a linear scale). */
export function Funnel({ chart }: { chart: ChartSpec }) {
  const stages: { name: string; value: number; rate?: number; rate_label?: string }[] = chart.data.stages ?? [];
  const max = Math.log10(Math.max(...stages.map((s) => s.value), 10));
  const colors = ["#E94BA8", "#F08A6A", "#F5A524"];
  return (
    <div className="space-y-3 py-2">
      {stages.map((s, i) => {
        const w = Math.max(8, (Math.log10(Math.max(s.value, 1)) / max) * 100);
        return (
          <div key={s.name}>
            <div className="mb-1 flex items-baseline justify-between text-xs">
              <span className="text-muted-foreground">{s.name}</span>
              <span className="font-mono text-sm tabular-nums">{fmt(s.value, "int")}</span>
            </div>
            <div className="mx-auto h-9 overflow-hidden rounded-lg bg-white/[0.03]" style={{ width: "100%" }}>
              <motion.div
                className="mx-auto h-full rounded-lg"
                style={{ background: `linear-gradient(90deg, ${colors[i % 3]}55, ${colors[i % 3]})` }}
                initial={{ width: 0 }}
                animate={{ width: `${w}%` }}
                transition={{ duration: 0.9, delay: i * 0.12, ease: "easeOut" }}
              />
            </div>
            {s.rate != null && (
              <div className="mt-1 text-center text-[11px] text-muted-foreground">
                ↓ {s.rate_label} <span className="font-mono text-foreground/80">{fmt(s.rate, "pct")}</span>
              </div>
            )}
          </div>
        );
      })}
      <p className="text-[10px] text-muted-foreground/70">Bar widths on a log scale.</p>
    </div>
  );
}
