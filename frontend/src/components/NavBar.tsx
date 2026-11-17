"use client";

import { motion } from "framer-motion";
import { BarChart3, FlaskConical, MessageSquare, RotateCcw, SlidersHorizontal } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useApp } from "@/components/AppProvider";
import { Skeleton } from "@/components/Skeleton";
import { cn } from "@/lib/utils";

const TABS = [
  { href: "/", label: "Chat", Icon: MessageSquare },
  { href: "/dashboard", label: "Dashboard", Icon: BarChart3 },
  { href: "/optimizer", label: "Optimizer", Icon: SlidersHorizontal },
  { href: "/lab", label: "Big Data Lab", Icon: FlaskConical },
];

export function NavBar() {
  const path = usePathname();
  const { meta, messages, reset } = useApp();
  return (
    <header className="sticky top-0 z-40 flex flex-wrap items-center gap-x-5 gap-y-2 border-b border-border bg-background/80 px-5 py-3 backdrop-blur">
      <Link href="/" className="flex items-center gap-2">
        <span className="size-2.5 rounded-full shadow-[0_0_12px_#E94BA8]" style={{ backgroundImage: "var(--accent-gradient)" }} />
        <h1 className="bg-clip-text text-lg font-semibold tracking-tight text-transparent" style={{ backgroundImage: "var(--accent-gradient)" }}>
          Budget Pilot
        </h1>
      </Link>
      <nav className="flex rounded-lg border border-border bg-card p-0.5" aria-label="Pages">
        {TABS.map(({ href, label, Icon }) => {
          const active = href === "/" ? path === "/" : path.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              data-testid={`tab-${label.toLowerCase().replace(/ /g, "-")}`}
              className={cn("relative flex items-center gap-1.5 rounded-md px-3 py-1 text-xs transition", active ? "text-foreground" : "text-muted-foreground hover:text-foreground")}
            >
              {active && <motion.span layoutId="tab" className="absolute inset-0 rounded-md bg-white/10" transition={{ type: "spring", stiffness: 500, damping: 38 }} />}
              <Icon className="relative size-3.5" />
              <span className="relative">{label}</span>
            </Link>
          );
        })}
      </nav>
      <div className="ml-auto flex items-center gap-3 text-xs text-muted-foreground">
        {path === "/" && messages.length > 0 && (
          <button type="button" onClick={reset} className="flex items-center gap-1 rounded-lg border border-border px-2.5 py-1 hover:text-foreground">
            <RotateCcw className="size-3.5" /> New chat
          </button>
        )}
        {meta ? (
          <span className="flex items-center gap-2 rounded-lg border border-border bg-card px-2.5 py-1" title="Synthetic dataset (data/generate.py)">
            <span className="font-mono">{meta.rows.toLocaleString()}</span> rows · synthetic · PKR
            <span className={cn("size-1.5 rounded-full", meta.llm.has_key || meta.llm.mock ? "bg-emerald-400" : "bg-[#F5A524]")} title={meta.llm.has_key ? `Gemini: ${meta.llm.model}` : meta.llm.mock ? "offline router" : "no GEMINI_API_KEY"} />
          </span>
        ) : (
          <Skeleton className="h-6 w-44 rounded-lg" />
        )}
      </div>
    </header>
  );
}
