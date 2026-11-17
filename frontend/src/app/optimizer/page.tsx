"use client";

import { motion } from "framer-motion";
import { RotateCcw } from "lucide-react";
import { useMemo, useState } from "react";
import { ChartCard } from "@/components/charts";
import { FilterBar } from "@/components/FilterBar";
import { ErrorCard, PageHeader } from "@/components/PageHeader";
import { ChartSkeleton } from "@/components/Skeleton";
import { fmt } from "@/lib/format";
import { platformColor } from "@/lib/theme";
import { clean, useTool } from "@/lib/useTool";
import type { Filters } from "@/lib/types";

const PLATFORMS = ["Facebook", "Instagram", "Google", "TikTok", "YouTube"];
const DEF_MIN = 5;
const DEF_MAX = 60;
type Caps = Record<string, [number, number]>;
const defaults = (): Caps => Object.fromEntries(PLATFORMS.map((p) => [p, [DEF_MIN, DEF_MAX]]));

export default function Optimizer() {
  const [budget, setBudget] = useState(1_000_000);
  const [horizon, setHorizon] = useState(30);
  const [caps, setCaps] = useState<Caps>(defaults);
  const [filters, setFilters] = useState<Filters>({});
  const minSum = PLATFORMS.reduce((s, p) => s + caps[p][0], 0);
  const maxSum = PLATFORMS.reduce((s, p) => s + caps[p][1], 0);
  const invalid = minSum > 100 ? `Minimums add up to ${minSum}% (> 100%)` : maxSum < 100 ? `Maximums add up to only ${maxSum}% (< 100%)` : null;
  const args = useMemo(
    () => ({
      budget,
      horizon_days: horizon,
      min_pct: Object.fromEntries(PLATFORMS.map((p) => [p, caps[p][0]])),
      max_pct: Object.fromEntries(PLATFORMS.map((p) => [p, caps[p][1]])),
      filters: clean({ ...filters, platform: undefined }),
    }),
    [budget, horizon, caps, filters],
  );
  const { data, loading, error } = useTool("optimizer_page", invalid ? null : args, 450);
  const s = data?.summary;
  const band = s?.band_90pct;
  const by = (t: string) => data?.charts.find((c) => c.type === t);

  return (
    <div className="mx-auto max-w-7xl p-5">
      <PageHeader
        title="Optimizer"
        sub="Fits revenue = a·log(1 + spend/b) per platform on daily data, then splits the budget so every platform's marginal ROAS is equal — within your min/max caps. The band comes from 100 bootstrap refits over days."
        loading={loading && Boolean(data)}
      />
      <div className="grid gap-4 lg:grid-cols-[340px_1fr]">
        <aside className="space-y-4 rounded-2xl border border-border bg-card/90 p-4 lg:sticky lg:top-4 lg:self-start">
          <label className="block">
            <span className="text-[11px] uppercase tracking-wider text-muted-foreground">Budget (PKR)</span>
            <input
              type="number"
              min={10000}
              step={50000}
              value={budget}
              data-testid="budget-input"
              onChange={(e) => setBudget(Math.max(0, Number(e.target.value)))}
              className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 font-mono text-lg outline-none focus:border-[#E94BA8]/50"
            />
            <span className="mt-1 block text-xs text-muted-foreground">{fmt(budget, "pkr")}</span>
          </label>
          <label className="block">
            <span className="text-[11px] uppercase tracking-wider text-muted-foreground">Spent over {horizon} days</span>
            <input type="range" min={7} max={90} value={horizon} onChange={(e) => setHorizon(Number(e.target.value))} className="mt-2 w-full accent-[#E94BA8]" />
          </label>
          <div>
            <div className="mb-2 flex items-center justify-between">
              <span className="text-[11px] uppercase tracking-wider text-muted-foreground">Min / max share per platform</span>
              <button type="button" onClick={() => setCaps(defaults())} className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground">
                <RotateCcw className="size-3" /> reset
              </button>
            </div>
            <div className="space-y-3">
              {PLATFORMS.map((p) => (
                <div key={p}>
                  <div className="flex items-center justify-between text-xs">
                    <span className="flex items-center gap-1.5">
                      <span className="size-2 rounded-full" style={{ background: platformColor(p) }} />
                      {p}
                    </span>
                    <span className="font-mono text-muted-foreground">
                      {caps[p][0]}% – {caps[p][1]}%
                    </span>
                  </div>
                  <div className="mt-1 grid grid-cols-2 gap-2">
                    <input
                      type="range"
                      min={0}
                      max={50}
                      value={caps[p][0]}
                      aria-label={`${p} minimum`}
                      onChange={(e) => {
                        const v = Number(e.target.value);
                        setCaps((c) => ({ ...c, [p]: [v, Math.max(v, c[p][1])] }));
                      }}
                      style={{ accentColor: platformColor(p) }}
                    />
                    <input
                      type="range"
                      min={0}
                      max={100}
                      value={caps[p][1]}
                      aria-label={`${p} maximum`}
                      onChange={(e) => {
                        const v = Number(e.target.value);
                        setCaps((c) => ({ ...c, [p]: [Math.min(v, c[p][0]), v] }));
                      }}
                      style={{ accentColor: platformColor(p) }}
                    />
                  </div>
                </div>
              ))}
            </div>
            {invalid && <p className="mt-2 text-xs text-red-300">{invalid}</p>}
          </div>
          <div>
            <span className="mb-2 block text-[11px] uppercase tracking-wider text-muted-foreground">Target audience (optional)</span>
            <FilterBar value={filters} onChange={setFilters} keys={["city", "age", "gender", "device"]} />
          </div>
        </aside>

        <div className="min-w-0 space-y-4">
          {invalid && <ErrorCard message={`${invalid} — adjust the sliders.`} />}
          {error && !invalid && !data && <ErrorCard message={error} />}
          {!data && !error && (
            <div className="grid gap-4 md:grid-cols-2">
              <ChartSkeleton tall />
              <ChartSkeleton tall />
            </div>
          )}
          {s && (
            <div className={`space-y-4 transition-opacity ${loading ? "opacity-60" : ""}`}>
              <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
                <Stat label="Predicted revenue" value={fmt(s.predicted_revenue, "pkr", true)} sub={band ? `90%: ${fmt(band.revenue_p5, "pkr", true)} – ${fmt(band.revenue_p95, "pkr", true)}` : ""} />
                <Stat label="Predicted ROAS" value={fmt(s.predicted_roas, "x")} sub={band ? `90%: ${fmt(band.roas_p5, "x")} – ${fmt(band.roas_p95, "x")}` : ""} />
                <Stat
                  label="Uplift vs current mix"
                  value={`${s.uplift_vs_current_pct >= 0 ? "+" : ""}${s.uplift_vs_current_pct.toFixed(1)}%`}
                  sub={band ? `90%: ${band.uplift_vs_current_p5.toFixed(1)}% – ${band.uplift_vs_current_p95.toFixed(1)}%` : ""}
                  good={s.uplift_vs_current_pct > 0}
                />
                <Stat label="Uplift vs equal split" value={`${s.uplift_vs_equal_pct >= 0 ? "+" : ""}${s.uplift_vs_equal_pct.toFixed(1)}%`} sub={`equal split ROAS ${fmt(s.equal_split_roas, "x")}`} good={s.uplift_vs_equal_pct > 0} />
              </div>
              <div className="grid gap-4 xl:grid-cols-2">
                {by("donut") && <ChartCard chart={by("donut")!} />}
                {by("bar") && <ChartCard chart={by("bar")!} delay={0.05} />}
              </div>
              {by("curves") && <ChartCard chart={by("curves")!} delay={0.1} />}
              {by("table") && <ChartCard chart={by("table")!} delay={0.15} />}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, sub, good }: { label: string; value: string; sub?: string; good?: boolean }) {
  return (
    <motion.div layout className="rounded-xl border border-border/80 bg-card/90 p-3" data-testid="opt-stat">
      <div className="text-[11px] uppercase tracking-wider text-muted-foreground">{label}</div>
      <motion.div key={value} initial={{ opacity: 0.3, y: 4 }} animate={{ opacity: 1, y: 0 }} className={`mt-1 font-mono text-2xl font-semibold tabular-nums ${good ? "text-emerald-300" : ""}`}>
        {value}
      </motion.div>
      {sub && <div className="mt-0.5 text-[11px] text-muted-foreground">{sub}</div>}
    </motion.div>
  );
}
