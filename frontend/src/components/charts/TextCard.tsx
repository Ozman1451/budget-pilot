"use client";

import type { ChartSpec } from "@/lib/types";

const CODE = /`([^`]+)`/g;

export function TextCard({ chart }: { chart: ChartSpec }) {
  const lines: string[] = chart.data.lines ?? [];
  return (
    <ul className="space-y-2.5 text-sm leading-relaxed">
      {lines.map((l, i) => (
        <li key={i} className="flex gap-2.5">
          <span className="mt-2 size-1.5 shrink-0 rounded-full bg-gradient-to-br from-[#E94BA8] to-[#F5A524]" />
          <span>
            {l.split(CODE).map((part, j) =>
              j % 2 ? (
                <code key={j} className="rounded bg-white/10 px-1 py-0.5 font-mono text-xs">
                  {part}
                </code>
              ) : (
                part
              ),
            )}
          </span>
        </li>
      ))}
    </ul>
  );
}
