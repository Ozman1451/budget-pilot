"use client";

import { fmt } from "@/lib/format";
import { platformColor } from "@/lib/theme";
import type { ChartSpec } from "@/lib/types";

interface Col {
  key: string;
  label: string;
  format?: string;
  wide?: boolean;
}

export function DataTable({ chart, maxRows }: { chart: ChartSpec; maxRows?: number }) {
  const cols: Col[] = chart.data.columns ?? [];
  const rows: Record<string, unknown>[] = (chart.data.rows ?? []).slice(0, maxRows ?? 1000);
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-[11px] uppercase tracking-wider text-muted-foreground">
            {cols.map((c) => (
              <th key={c.key} className={`whitespace-nowrap px-2 py-2 font-medium first:pl-0 ${c.format ? "text-right" : ""}`}>
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-b border-border/50 transition-colors last:border-0 hover:bg-white/[0.02]">
              {cols.map((c, j) => {
                const v = r[c.key];
                const isPlat = j === 0 && typeof v === "string" && platformColor(v) && ["Facebook", "Instagram", "Google", "TikTok", "YouTube"].includes(v);
                return (
                  <td
                    key={c.key}
                    className={`px-2 py-2 first:pl-0 ${c.wide ? "min-w-[260px] text-xs leading-snug text-muted-foreground" : "whitespace-nowrap"} ${
                      c.format ? "text-right font-mono tabular-nums text-foreground/85" : ""
                    } ${v === "failed" || v === "timeout" || v === "NO" ? "text-red-400" : ""}`}
                  >
                    {isPlat ? (
                      <span className="inline-flex items-center gap-2 font-medium">
                        <span className="size-2 rounded-full" style={{ background: platformColor(v as string) }} />
                        {v as string}
                      </span>
                    ) : (
                      fmt(v, c.format)
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
