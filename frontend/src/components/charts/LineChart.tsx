"use client";

import { fmt } from "@/lib/format";
import { axis, base, ENGINE_COLOR, PALETTE, platformColor, tooltip } from "@/lib/theme";
import type { ChartSpec } from "@/lib/types";
import { EChart } from "./EChart";

/* eslint-disable @typescript-eslint/no-explicit-any */
export function LineChart({ chart, height = 280 }: { chart: ChartSpec; height?: number }) {
  const d = chart.data;
  const xs: (string | number)[] = d.x ?? [];
  const series: { name: string; values: (number | null)[]; dashed?: boolean; engine?: string }[] = d.series ?? [];
  const f = d.format as string;
  const color = (s: (typeof series)[number], i: number) =>
    s.engine ? ENGINE_COLOR[s.engine] ?? PALETTE[i] : s.name === "All" ? "#EDEDF2" : platformColor(s.name, i);
  const option: any = {
    ...base,
    tooltip: { ...tooltip, trigger: "axis", valueFormatter: (v: number) => fmt(v, f) },
    legend: { top: 0, textStyle: { color: "#8A8A9A", fontSize: 11 }, itemWidth: 14, itemHeight: 8, type: "scroll" },
    grid: { left: 8, right: 20, top: 34, bottom: 8, containLabel: true },
    xAxis: d.log_x
      ? { type: "log", ...axis, logBase: 10, axisLabel: { ...axis.axisLabel, formatter: (v: number) => fmt(v, "rows") }, splitLine: { show: false } }
      : { type: "category", data: xs, boundaryGap: false, ...axis },
    yAxis: {
      type: d.log_y ? "log" : "value",
      ...axis,
      scale: !d.log_y,
      axisLabel: { ...axis.axisLabel, formatter: (v: number) => fmt(v, f) },
    },
    series: series.map((s, i) => ({
      name: s.name,
      type: "line",
      smooth: !d.log_x,
      connectNulls: true,
      showSymbol: d.log_x || xs.length < 16,
      symbolSize: 8,
      data: d.log_x ? xs.map((x, j) => [x, s.values[j]]).filter((p) => p[1] != null) : s.values,
      lineStyle: { width: s.name === "All" ? 2.5 : 2, type: s.dashed ? "dashed" : "solid", color: color(s, i) },
      itemStyle: { color: color(s, i) },
      emphasis: { focus: "series" },
    })),
  };
  return <EChart option={option} height={height} />;
}
