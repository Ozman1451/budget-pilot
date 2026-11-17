"use client";

import { motion } from "framer-motion";
import { fmt } from "@/lib/format";
import type { ChartSpec } from "@/lib/types";

interface Tile {
  key: string;
  label: string;
  value: number | string;
  format?: string;
  hint?: string;
}

export function KpiTiles({ chart, compact }: { chart: ChartSpec; compact?: boolean }) {
  const tiles: Tile[] = chart.data.tiles ?? [];
  return (
    <div className={compact ? "grid grid-cols-2 gap-2 sm:grid-cols-4" : "grid grid-cols-2 gap-3 md:grid-cols-4"}>
      {tiles.map((t, i) => (
        <motion.div
          key={t.key}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.04 }}
          className="rounded-xl border border-border/80 bg-white/[0.02] p-3"
        >
          <div className="text-[11px] uppercase tracking-wider text-muted-foreground">{t.label}</div>
          <div className={`mt-1 font-mono font-semibold tabular-nums ${compact ? "text-lg" : "text-2xl"}`}>
            {fmt(t.value, t.format, true)}
          </div>
          {t.hint && <div className="mt-1 text-xs text-muted-foreground">{t.hint}</div>}
        </motion.div>
      ))}
    </div>
  );
}
