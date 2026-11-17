"use client";

import { ChartCard } from "@/components/charts";
import { ErrorCard, PageHeader } from "@/components/PageHeader";
import { ChartSkeleton } from "@/components/Skeleton";
import { useTool } from "@/lib/useTool";

export default function Lab() {
  const { data, loading, error } = useTool("get_benchmark", {});
  const s = data?.summary;
  const charts = data?.charts ?? [];
  const notRun = s?.status === "not run";
  return (
    <div className="mx-auto max-w-7xl p-5">
      <PageHeader
        title="Big Data Lab"
        sub="The same platform-level KPI aggregation timed three ways — Pandas, MapReduce (mrjob, local runner) and PySpark (local[*]) — at growing data sizes. Real measurements from bench/results.csv; failures are shown, never filled in."
        loading={loading && Boolean(data)}
      >
        {s && !notRun && (
          <div className="flex flex-wrap gap-2 text-xs">
            <Pill label="Sizes" value={(s.sizes as number[]).map((n) => n.toLocaleString()).join(" · ")} />
            <Pill label="Spark" value={String(s.spark_status)} warn={s.spark_status !== "ok"} />
            <Pill label="KPIs identical" value={s.all_agree ? "yes (rtol 1e-6)" : "check table"} warn={!s.all_agree} />
          </div>
        )}
      </PageHeader>
      {error && !data && <ErrorCard message={error} />}
      {!data && !error && (
        <div className="grid gap-4 lg:grid-cols-2">
          <ChartSkeleton tall />
          <ChartSkeleton tall />
        </div>
      )}
      {data && (
        <div className="grid gap-4 lg:grid-cols-2">
          {charts.map((c, i) => (
            <ChartCard key={c.id} chart={c} delay={i * 0.06} className={c.type === "table" || c.type === "text" ? "lg:col-span-2" : ""} />
          ))}
          {!notRun && (
            <p className="text-xs text-muted-foreground lg:col-span-2">
              Bigger sizes: <code className="rounded bg-white/10 px-1 font-mono">make bench</code> (all sizes) or{" "}
              <code className="rounded bg-white/10 px-1 font-mono">make bench MAX_ROWS=1000000</code>. Local Spark on one laptop is not a cluster —
              see README “Limitations”.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function Pill({ label, value, warn }: { label: string; value: string; warn?: boolean }) {
  return (
    <span className={`rounded-lg border px-2.5 py-1 ${warn ? "border-[#F5A524]/40 text-[#F5A524]" : "border-border text-muted-foreground"}`}>
      {label}: <span className="font-mono text-foreground/90">{value}</span>
    </span>
  );
}
