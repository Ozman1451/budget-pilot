"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { Toasts, useToasts } from "@/components/Toast";
import { getMeta, streamChat } from "@/lib/api";
import type { ChatMessage, Meta } from "@/lib/types";

const uid = () => Math.random().toString(36).slice(2, 10);

interface App {
  meta: Meta | null;
  metaError: string | null;
  toast: (text: string, kind?: "error" | "info") => void;
  messages: ChatMessage[];
  busy: boolean;
  ask: (text: string) => void;
  stop: () => void;
  reset: () => void;
}

const Ctx = createContext<App | null>(null);
export const useApp = () => {
  const v = useContext(Ctx);
  if (!v) throw new Error("useApp outside AppProvider");
  return v;
};

/** Global state: dataset meta, toasts, and the chat thread (kept while switching tabs). Chat loop reused from Need Map Chat. */
export function AppProvider({ children }: { children: ReactNode }) {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [metaError, setMetaError] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const { toasts, toast, dismiss } = useToasts();
  const abort = useRef<AbortController | null>(null);
  const history = useRef<ChatMessage[]>([]);
  history.current = messages;

  useEffect(() => {
    getMeta()
      .then((m) => {
        setMeta(m);
        setMetaError(null);
      })
      .catch((e) => {
        setMetaError(e.message);
        toast(`Backend not reachable (${e.message}). Start it with make app.`);
      });
  }, [toast]);

  const patchLast = (fn: (m: ChatMessage) => ChatMessage) =>
    setMessages((ms) => (ms.length ? [...ms.slice(0, -1), fn(ms[ms.length - 1])] : ms));

  const ask = useCallback(
    async (text: string) => {
      abort.current?.abort();
      const ctl = new AbortController();
      abort.current = ctl;
      const user: ChatMessage = { id: uid(), role: "user", content: text };
      const reply: ChatMessage = { id: uid(), role: "assistant", content: "", steps: [], charts: [], pending: true };
      const sent = [...history.current.filter((m) => !m.pending), user]
        .slice(-10)
        .map(({ role, content }) => ({ role, content }));
      setMessages((ms) => [...ms.map((m) => ({ ...m, pending: false })), user, reply]);
      setBusy(true);
      try {
        await streamChat(
          sent,
          (ev) => {
            switch (ev.event) {
              case "tool_start":
                patchLast((m) => ({ ...m, steps: [...(m.steps ?? []), { tool: ev.data.tool, args: ev.data.args, status: "running" }] }));
                break;
              case "tool_result": {
                const failed = "error" in (ev.data.summary ?? {});
                patchLast((m) => {
                  const steps = [...(m.steps ?? [])];
                  const i = steps.findLastIndex((s) => s.tool === ev.data.tool && s.status === "running");
                  if (i >= 0) steps[i] = { ...steps[i], status: failed ? "error" : "done" };
                  return { ...m, steps, charts: [...(m.charts ?? []), ...(ev.data.charts ?? [])] };
                });
                break;
              }
              case "text_delta":
                patchLast((m) => ({ ...m, content: m.content + ev.data.text }));
                break;
              case "error":
                patchLast((m) => ({ ...m, error: ev.data.message }));
                toast(ev.data.message);
                break;
            }
          },
          ctl.signal,
        );
      } catch (e) {
        if (!ctl.signal.aborted) {
          patchLast((m) => ({ ...m, error: (e as Error).message }));
          toast((e as Error).message);
        }
      } finally {
        if (abort.current === ctl) {
          patchLast((m) => ({ ...m, pending: false }));
          setBusy(false);
        }
      }
    },
    [toast],
  );

  const stop = useCallback(() => abort.current?.abort(), []);
  const reset = useCallback(() => {
    abort.current?.abort();
    setMessages([]);
    setBusy(false);
  }, []);

  return (
    <Ctx.Provider value={{ meta, metaError, toast, messages, busy, ask, stop, reset }}>
      {children}
      <Toasts toasts={toasts} onDismiss={dismiss} />
    </Ctx.Provider>
  );
}
