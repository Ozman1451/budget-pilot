"use client";

import { useApp } from "@/components/AppProvider";
import { Chat } from "@/components/chat/Chat";

export default function Home() {
  const { messages, busy, ask, stop, meta } = useApp();
  return (
    <div className="h-full">
      <Chat messages={messages} busy={busy} onAsk={ask} onStop={stop} meta={meta} />
    </div>
  );
}
