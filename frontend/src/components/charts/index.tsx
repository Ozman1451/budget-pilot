"use client";

import { motion } from "framer-motion";
import type { ReactNode } from "react";
import type { ChartSpec } from "@/lib/types";
import { BarChart } from "./BarChart";
import { Curves } from "./Curves";
import { DataTable } from "./DataTable";
import { Donut } from "./Donut";
import { Funnel } from "./Funnel";
import { Heatmap } from "./Heatmap";
import { KpiTiles } from "./KpiTiles";
import { LineChart } from "./LineChart";
import { TextCard } from "./TextCard";

/** Render by chart.type only. `compact` = smaller variant used inline in chat. */
export function ChartBody({ chart, compact }: { chart: ChartSpec; compact?: boolean }) {
  switch (chart.type) {
    case "kpi_tiles":
      return <KpiTiles chart={chart} compact={compact} />;
    case "bar":
      return <BarChart chart={chart} height={compact && !chart.data.horizontal ? 220 : undefined} />;
    case "line":
      return <LineChart chart={chart} height={compact ? 220 : 300} />;
    case "donut":
      return <Donut chart={chart} height={compact ? 260 : 340} />;
    case "heatmap":
      return <Heatmap chart={chart} />;
    case "funnel":
      return <Funnel chart={chart} />;
    case "table":
      return <DataTable chart={chart} maxRows={compact ? 12 : undefined} />;
    case "curves":
      return <Curves chart={chart} height={compact ? 150 : 180} />;
    case "text":
      return <TextCard chart={chart} />;
    default:
      return <pre className="text-xs text-muted-foreground">unsupported chart: {String((chart as ChartSpec).type)}</pre>;
  }
}

export function ChartCard({
  chart,
  compact,
  className = "",
  delay = 0,
  action,
}: {
  chart: ChartSpec;
  compact?: boolean;
  className?: string;
  delay?: number;
  action?: ReactNode;
}) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay, ease: "easeOut" }}
      className={`min-w-0 rounded-2xl border border-border bg-card/90 ${compact ? "p-3" : "p-4"} ${className}`}
      data-testid={`chart-${chart.type}`}
    >
      {(chart.title || action) && (
        <header className="mb-3 flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className={`font-medium tracking-tight ${compact ? "text-sm" : "text-[15px]"}`}>{chart.title}</h3>
            {chart.subtitle && <p className="mt-0.5 text-xs text-muted-foreground">{chart.subtitle}</p>}
          </div>
          {action}
        </header>
      )}
      <ChartBody chart={chart} compact={compact} />
    </motion.section>
  );
}
