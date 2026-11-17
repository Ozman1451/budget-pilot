"use client";

import { fmt } from "@/lib/format";
import { axis, base, platformColor, tooltip } from "@/lib/theme";
import type { ChartSpec } from "@/lib/types";
import { EChart } from "./EChart";

/* eslint-disable @typescript-eslint/no-explicit-any */
type P = { x: number[]; y: number[]; point: [number, number]; current: [number, number] };

/** One small response-curve panel per platform, with the recommended (●) and current (○) spend marked. */
export function Curves({ chart, height = 180 }: { chart: ChartSpec; height?: number }) {
  const plats: Record<string, P> = chart.data.platforms ?? {};
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {Object.entries(plats).map(([name, p]) => {
        const c = platformColor(name);
        const option: any = {
          ...base,
          title: { text: name, left: 4, top: 0, textStyle: { color: c, fontSize: 12, fontWeight: 600 } },
          tooltip: {
            ...tooltip,
            trigger: "axis",
            formatter: (ps: any[]) => {
              const q = ps[0];
              return `Spend ${fmt(q.value[0], "pkr")}<br/>Revenue ${fmt(q.value[1], "pkr")}`;
            },
          },
          grid: { left: 6, right: 14, top: 26, bottom: 4, containLabel: true },
          xAxis: { type: "value", ...axis, splitNumber: 3, axisLabel: { ...axis.axisLabel, formatter: (v: number) => fmt(v, "pkr", true) }, splitLine: { show: false } },
          yAxis: { type: "value", ...axis, splitNumber: 4, axisLabel: { ...axis.axisLabel, formatter: (v: number) => fmt(v, "pkr", true) } },
          series: [
            {
              type: "line",
              smooth: true,
              showSymbol: false,
              data: p.x.map((x, i) => [x, p.y[i]]),
              lineStyle: { color: c, width: 2 },
              areaStyle: { color: { type: "linear", x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: c + "40" }, { offset: 1, color: c + "00" }] } },
              markPoint: {
                symbolSize: 12,
                animationDuration: 600,
                data: [
                  { coord: p.point, symbol: "circle", itemStyle: { color: c, borderColor: "#fff", borderWidth: 2 }, name: "Recommended" },
                  { coord: p.current, symbol: "circle", itemStyle: { color: "transparent", borderColor: "#8A8A9A", borderWidth: 2 }, name: "Current" },
                ],
                label: { show: false },
              },
            },
          ],
        };
        return (
          <div key={name} className="rounded-xl border border-border/70 bg-white/[0.015] p-2">
            <EChart option={option} height={height} />
            <div className="flex justify-between px-1 pb-1 text-[11px] text-muted-foreground">
              <span>● {fmt(p.point[0], "pkr", true)} → {fmt(p.point[1], "pkr", true)}</span>
              <span>○ now {fmt(p.current[0], "pkr", true)}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
