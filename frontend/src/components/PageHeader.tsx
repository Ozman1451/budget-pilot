import { Loader2 } from "lucide-react";
import type { ReactNode } from "react";

export function PageHeader({ title, sub, loading, children }: { title: string; sub: string; loading?: boolean; children?: ReactNode }) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h2 className="flex items-center gap-2 text-2xl font-semibold tracking-tight">
          {title}
          {loading && <Loader2 className="size-4 animate-spin text-[#F5A524]" data-testid="page-loading" />}
        </h2>
        <p className="mt-1 max-w-2xl text-sm text-muted-foreground">{sub}</p>
      </div>
      {children}
    </div>
  );
}

export function ErrorCard({ message }: { message: string }) {
  return (
    <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300" data-testid="error-card">
      {message}
    </div>
  );
}
