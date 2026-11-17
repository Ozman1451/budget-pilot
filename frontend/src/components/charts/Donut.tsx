"use client";

import { fmt } from "@/lib/format";
import { base, platformColor, tooltip } from "@/lib/theme";
import type { ChartSpec } from "@/lib/types";
import { EChart } from "./EChart";

/* eslint-disable @typescript-eslint/no-explicit-any */
export function Donut({ chart, height = 300 }: { chart: ChartSpec; height?: number }) {
  const items: { name: string; value: number; pct: number; low?: number; high?: number }[] = chart.data.items ?? [];
  const c = chart.data.center;
  const option: any = {
    ...base,
    animationDuration: 1100,
    animationEasing: "cubicInOut",
    animationDurationUpdate: 900,
    tooltip: {
      ...tooltip,
      formatter: (p: any) => {
        const it = items[p.dataIndex];
        const band = it.low != null ? `<br/><span style="color:#8A8A9A">90% band ${it.low.toFixed(0)}–${it.high!.toFixed(0)}%</span>` : "";
        return `<b>${it.name}</b><br/>${fmt(it.value, "pkr")} · ${it.pct.toFixed(1)}%${band}`;
      },
    },
    legend: { bottom: 0, textStyle: { color: "#8A8A9A", fontSize: 11 }, itemWidth: 10, itemHeight: 10 },
    title: c
      ? {
          text: fmt(c.value, c.format),
          subtext: `${c.label}${c.low != null ? `\n${fmt(c.low, c.format)} – ${fmt(c.high, c.format)}` : ""}`,
          left: "center",
          top: "33%",
          textStyle: { color: "#EDEDF2", fontSize: 26, fontWeight: 600, fontFamily: "ui-monospace, Menlo, monospace" },
          subtextStyle: { color: "#8A8A9A", fontSize: 11, lineHeight: 15 },
        }
      : undefined,
    series: [
      {
        type: "pie",
        radius: ["50%", "70%"],
        avoidLabelOverlap: true,
        center: ["50%", "45%"],
        padAngle: 2,
        itemStyle: { borderRadius: 6 },
        label: { show: true, color: "#EDEDF2", fontSize: 11, overflow: "none", bleedMargin: 2, formatter: (p: any) => `${p.name}\n${items[p.dataIndex].pct.toFixed(0)}%` },
        labelLine: { lineStyle: { color: "#23232F" } },
        data: items.map((it, i) => ({ name: it.name, value: it.value, itemStyle: { color: platformColor(it.name, i) } })),
      },
    ],
  };
  return <EChart option={option} height={height} />;
}
