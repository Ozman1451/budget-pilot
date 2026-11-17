"use client";

import { fmt } from "@/lib/format";
import { axis, base, PALETTE, platformColor, tooltip } from "@/lib/theme";
import type { ChartSpec } from "@/lib/types";
import { EChart } from "./EChart";

/* eslint-disable @typescript-eslint/no-explicit-any */
export function BarChart({ chart, height }: { chart: ChartSpec; height?: number }) {
  const d = chart.data;
  const cats: string[] = d.categories ?? [];
  const series: { name: string; values: number[] }[] = d.series ?? [];
  const horiz = Boolean(d.horizontal);
  const f = d.format as string;
  const multi = series.length > 1;
  const pairColors = ["#5A5A6E", "#E94BA8"];
  const valAxis = { type: "value", ...axis, axisLabel: { ...axis.axisLabel, formatter: (v: number) => fmt(v, f, true) } };
  const catAxis = {
    type: "category",
    data: cats,
    ...axis,
    inverse: horiz,
    axisLabel: { ...axis.axisLabel, width: horiz ? 150 : undefined, overflow: "truncate", interval: 0, rotate: !horiz && cats.length > 7 ? 30 : 0 },
  };
  const option: any = {
    ...base,
    tooltip: { ...tooltip, trigger: "axis", axisPointer: { type: "shadow" }, valueFormatter: (v: number) => fmt(v, f) },
    legend: multi || d.line ? { top: 0, textStyle: { color: "#8A8A9A", fontSize: 11 }, itemWidth: 10, itemHeight: 10 } : undefined,
    grid: { left: 8, right: d.line ? 40 : 16, top: multi || d.line ? 30 : 10, bottom: 8, containLabel: true },
    xAxis: horiz ? valAxis : catAxis,
    yAxis: horiz
      ? catAxis
      : d.line
        ? [valAxis, { type: "value", ...axis, splitLine: { show: false }, axisLabel: { ...axis.axisLabel, formatter: (v: number) => fmt(v, d.line.format) } }]
        : valAxis,
    series: [
      ...series.map((s, si) => ({
        name: s.name,
        type: "bar",
        stack: d.stacked ? "all" : undefined,
        barMaxWidth: 28,
        itemStyle: { color: d.stacked ? platformColor(s.name, si) : multi ? (series.length === 2 ? pairColors[si] : PALETTE[si % PALETTE.length]) : "#E94BA8" },
        data: s.values.map((v, i) => ({
          value: v,
          itemStyle: {
            color: d.stacked
              ? platformColor(s.name, si)
              : multi
                ? (series.length === 2 ? pairColors[si] : PALETTE[si % PALETTE.length])
                : d.color_by_platform
                  ? platformColor(cats[i], i)
                  : "#E94BA8",
            borderRadius: d.stacked ? 0 : horiz ? [0, 4, 4, 0] : [4, 4, 0, 0],
          },
        })),
        label: d.stacked
          ? { show: true, color: "#0A0A0F", fontSize: 10, formatter: (p: any) => (p.value >= 8 ? fmt(p.value, f) : "") }
          : undefined,
      })),
      ...(d.line
        ? [{
            name: d.line.name,
            type: "line",
            yAxisIndex: 1,
            data: d.line.values,
            smooth: true,
            symbolSize: 7,
            lineStyle: { color: "#F5A524", width: 2 },
            itemStyle: { color: "#F5A524" },
            tooltip: { valueFormatter: (v: number) => fmt(v, d.line.format) },
          }]
        : []),
    ],
  };
  const h = height ?? (horiz ? Math.max(160, cats.length * (d.stacked ? 34 : 28) + 50) : 260);
  return <EChart option={option} height={h} />;
}
