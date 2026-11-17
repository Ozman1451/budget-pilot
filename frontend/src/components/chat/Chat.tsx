"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ArrowUp, KeyRound, Square } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { ChartCard } from "@/components/charts";
import { ChartSkeleton } from "@/components/Skeleton";
import { MessageText } from "./MessageText";
import { ToolTrace } from "./ToolTrace";
import type { Ask, ChatMessage, Meta } from "@/lib/types";

export const PROMPTS = [
  "Where should the next Rs. 1M go?",
  "What if TikTok is capped at 10%?",
  "Best platform for Karachi 18-24 on mobile?",
  "Why is Google better than YouTube?",
  "How did Spark compare to Pandas and MapReduce?",
];

export function Chat({
  messages,
  busy,
  onAsk,
  onStop,
  meta,
}: {
  messages: ChatMessage[];
  busy: boolean;
  onAsk: Ask;
  onStop: () => void;
  meta: Meta | null;
}) {
  const [draft, setDraft] = useState("");
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => {
    end.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  const submit = () => {
    const t = draft.trim();
    if (!t || busy) return;
    setDraft("");
    onAsk(t);
  };
  const noKey = meta && !meta.llm.has_key && !meta.llm.mock;

  return (
    <div className="flex h-full flex-col">
      {noKey && (
        <div className="flex items-center gap-2 border-b border-[#F5A524]/25 bg-[#F5A524]/10 px-5 py-2 text-xs text-[#F5A524]" data-testid="key-banner">
          <KeyRound className="size-3.5" />
          <span>
            <b>Add GEMINI_API_KEY</b> to <code className="font-mono">.env</code> (copy <code className="font-mono">.env.example</code>) and restart the backend.
            Dashboard, Optimizer and Big Data Lab work without it.
          </span>
        </div>
      )}
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-4xl px-5 py-6">
          {messages.length === 0 ? (
            <Empty onAsk={onAsk} meta={meta} />
          ) : (
            <div className="space-y-6">
              {messages.map((m) =>
                m.role === "user" ? (
                  <motion.div key={m.id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="flex justify-end">
                    <div className="max-w-[80%] rounded-2xl rounded-br-md border border-[#E94BA8]/25 bg-gradient-to-br from-[#E94BA8]/15 to-[#F5A524]/10 px-3.5 py-2 text-sm">
                      {m.content}
                    </div>
                  </motion.div>
                ) : (
                  <motion.div key={m.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} data-testid="assistant-msg">
                    {m.steps && m.steps.length > 0 && <ToolTrace steps={m.steps} />}
                    {m.content ? <MessageText text={m.content} onAsk={onAsk} /> : m.pending && !m.steps?.length && <Dots />}
                    {m.error && (
                      <p className="mt-2 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-300">{m.error}</p>
                    )}
                    <InlineCharts m={m} />
                  </motion.div>
                ),
              )}
              {!busy && (
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {PROMPTS.filter((p) => !messages.some((m) => m.content === p))
                    .slice(0, 3)
                    .map((p) => (
                      <PromptChip key={p} text={p} onClick={() => onAsk(p)} small />
                    ))}
                </div>
              )}
            </div>
          )}
          <div ref={end} />
        </div>
      </div>
      <div className="border-t border-border bg-background/80 backdrop-blur">
        <div className="mx-auto w-full max-w-4xl p-3">
          <div className="flex items-end gap-2 rounded-xl border border-border bg-card px-3 py-2 focus-within:border-[#E94BA8]/50 focus-within:shadow-[0_0_0_3px_rgba(233,75,168,0.12)]">
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  submit();
                }
              }}
              rows={1}
              data-testid="chat-input"
              placeholder="Ask about budgets, platforms, audiences or the benchmark…"
              className="max-h-32 min-h-6 flex-1 resize-none bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            />
            {busy ? (
              <button type="button" onClick={onStop} aria-label="Stop" className="rounded-lg bg-white/10 p-1.5 hover:bg-white/15">
                <Square className="size-4" />
              </button>
            ) : (
              <button
                type="button"
                onClick={submit}
                disabled={!draft.trim()}
                aria-label="Send"
                className="rounded-lg p-1.5 text-black transition disabled:opacity-30"
                style={{ backgroundImage: "var(--accent-gradient)" }}
              >
                <ArrowUp className="size-4" strokeWidth={2.5} />
              </button>
            )}
          </div>
          <p className="mt-1.5 text-center text-[10px] text-muted-foreground/70">
            Every number comes from a Python tool over the data — Gemini only picks tools and explains.
          </p>
        </div>
      </div>
    </div>
  );
}

function InlineCharts({ m }: { m: ChatMessage }) {
  const charts = (m.charts ?? []).filter((c) => c.meta?.inline !== false);
  const running = m.pending && (m.steps ?? []).some((s) => s.status === "running");
  if (!charts.length && !running) return null;
  return (
    <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
      <AnimatePresence>
        {charts.map((c, i) => (
          <ChartCard
            key={c.id}
            chart={c}
            compact
            delay={i * 0.06}
            className={c.type === "table" || c.type === "kpi_tiles" || c.type === "curves" || c.data?.horizontal ? "md:col-span-2" : ""}
          />
        ))}
      </AnimatePresence>
      {running && !charts.length && (
        <>
          <ChartSkeleton tall />
          <ChartSkeleton tall />
        </>
      )}
    </div>
  );
}

function Empty({ onAsk, meta }: { onAsk: Ask; meta: Meta | null }) {
  return (
    <div className="flex min-h-[60vh] flex-col justify-center gap-6 py-10">
      <div>
        <h2 className="text-3xl font-semibold tracking-tight">
          Where should we spend the{" "}
          <span className="bg-clip-text text-transparent" style={{ backgroundImage: "var(--accent-gradient)" }}>
            next Rs. 1,000,000
          </span>
          ?
        </h2>
        <p className="mt-3 max-w-xl text-sm text-muted-foreground">
          Ask in plain words. I read 12 months of campaign data across Facebook, Instagram, Google, TikTok and YouTube,
          fit diminishing-returns curves per platform, and recommend a split — with a confidence band, not fake precision.
        </p>
        {meta && (
          <p className="mt-2 font-mono text-[11px] text-muted-foreground/80">
            {meta.rows.toLocaleString()} rows · {meta.date_min} → {meta.date_max} · {meta.llm.mock ? "offline router" : meta.llm.model}
          </p>
        )}
      </div>
      <div className="flex flex-col items-start gap-2">
        {PROMPTS.map((p, i) => (
          <motion.div key={p} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.1 + i * 0.06 }}>
            <PromptChip text={p} onClick={() => onAsk(p)} />
          </motion.div>
        ))}
      </div>
    </div>
  );
}

function PromptChip({ text, onClick, small }: { text: string; onClick: () => void; small?: boolean }) {
  return (
    <button
      type="button"
      onClick={onClick}
      data-testid="prompt-chip"
      className={`rounded-full border border-border bg-card text-left text-foreground/90 transition hover:border-[#E94BA8]/50 hover:text-foreground hover:shadow-[0_0_20px_-6px_rgba(233,75,168,0.6)] ${
        small ? "px-2.5 py-1 text-xs" : "px-3.5 py-1.5 text-sm"
      }`}
    >
      {text}
    </button>
  );
}

function Dots() {
  return (
    <div className="flex gap-1 py-2">
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="size-1.5 rounded-full bg-muted-foreground"
          animate={{ opacity: [0.3, 1, 0.3] }}
          transition={{ duration: 1, repeat: Infinity, delay: i * 0.15 }}
        />
      ))}
    </div>
  );
}
