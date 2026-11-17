"use client";

import { useState } from "react";
import { ChartCard } from "@/components/charts";
import { FilterBar } from "@/components/FilterBar";
import { ErrorCard, PageHeader } from "@/components/PageHeader";
import { ChartSkeleton } from "@/components/Skeleton";
import { clean, useTool } from "@/lib/useTool";
import type { ChartSpec, Filters } from "@/lib/types";

export default function Dashboard() {
  const [filters, setFilters] = useState<Filters>({});
  const { data, loading, error } = useTool("dashboard", { filters: clean(filters) });
  const by = (t: string) => data?.charts.find((c) => c.type === t) as ChartSpec | undefined;
  const bars = by("bar");
  return (
    <div className="mx-auto max-w-7xl p-5">
      <PageHeader title="Dashboard" sub="12 months of campaign performance across five platforms. Filters apply to every card." loading={loading && Boolean(data)}>
        <FilterBar value={filters} onChange={setFilters} />
      </PageHeader>
      {error && !data && <ErrorCard message={error} />}
      {!data && !error && (
        <div className="grid gap-4 lg:grid-cols-2">
          <ChartSkeleton />
          <ChartSkeleton />
          <ChartSkeleton tall />
          <ChartSkeleton tall />
        </div>
      )}
      {data && (
        <div className={`grid gap-4 transition-opacity lg:grid-cols-2 ${loading ? "opacity-60" : ""}`}>
          {by("kpi_tiles") && <ChartCard chart={by("kpi_tiles")!} className="lg:col-span-2" />}
          {bars && <ChartCard chart={bars} delay={0.05} />}
          {by("funnel") && <ChartCard chart={by("funnel")!} delay={0.1} />}
          {by("line") && <ChartCard chart={by("line")!} delay={0.15} className="lg:col-span-2" />}
          {by("heatmap") && <ChartCard chart={by("heatmap")!} delay={0.2} />}
          {by("table") && <ChartCard chart={by("table")!} delay={0.25} />}
        </div>
      )}
    </div>
  );
}
