"use client";

import { fmt } from "@/lib/format";
import { axis, base, tooltip } from "@/lib/theme";
import type { ChartSpec } from "@/lib/types";
import { EChart } from "./EChart";

/* eslint-disable @typescript-eslint/no-explicit-any */
export function Heatmap({ chart, height = 320 }: { chart: ChartSpec; height?: number }) {
  const d = chart.data;
  const vals: [number, number, number][] = d.values ?? [];
  const nums = vals.map((v) => v[2]).filter((v) => v != null);
  const option: any = {
    ...base,
    tooltip: {
      ...tooltip,
      formatter: (p: any) => `${d.y[p.value[1]]} · ${d.x[p.value[0]]}<br/><b>${fmt(p.value[2], d.format)}</b>`,
    },
    grid: { left: 8, right: 8, top: 8, bottom: 64, containLabel: true },
    xAxis: { type: "category", data: d.x, ...axis, splitArea: { show: false } },
    yAxis: { type: "category", data: d.y, ...axis, inverse: true },
    visualMap: {
      min: Math.min(...nums, 0),
      max: Math.max(...nums, 1),
      calculable: true,
      orient: "horizontal",
      left: "center",
      bottom: 0,
      itemHeight: 140,
      itemWidth: 12,
      textStyle: { color: "#8A8A9A", fontSize: 10 },
      formatter: (v: number) => fmt(v, d.format),
      inRange: { color: ["#1a1426", "#5b2150", "#E94BA8", "#F5A524"] },
    },
    series: [
      {
        type: "heatmap",
        data: vals,
        label: { show: true, color: "#EDEDF2", fontSize: 11, formatter: (p: any) => fmt(p.value[2], d.format) },
        itemStyle: { borderColor: "#0A0A0F", borderWidth: 2, borderRadius: 4 },
        emphasis: { itemStyle: { shadowBlur: 12, shadowColor: "rgba(233,75,168,.5)" } },
      },
    ],
  };
  return <EChart option={option} height={height} />;
}
