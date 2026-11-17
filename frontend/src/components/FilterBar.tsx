"use client";

import { FilterX } from "lucide-react";
import { useApp } from "@/components/AppProvider";
import type { Filters } from "@/lib/types";

const KEYS: { key: keyof Filters; label: string }[] = [
  { key: "platform", label: "All platforms" },
  { key: "city", label: "All cities" },
  { key: "age", label: "All ages" },
  { key: "gender", label: "All genders" },
  { key: "device", label: "All devices" },
  { key: "month", label: "All months" },
];

export function FilterBar({ value, onChange, keys }: { value: Filters; onChange: (f: Filters) => void; keys?: (keyof Filters)[] }) {
  const { meta } = useApp();
  const shown = KEYS.filter((k) => !keys || keys.includes(k.key));
  const active = Object.values(value).some(Boolean);
  return (
    <div className="flex flex-wrap items-center gap-2">
      {shown.map(({ key, label }) => (
        <select
          key={key}
          aria-label={key}
          value={value[key] ?? ""}
          disabled={!meta}
          onChange={(e) => onChange({ ...value, [key]: e.target.value || undefined })}
          className={`rounded-lg border bg-card px-2.5 py-1.5 text-xs outline-none transition focus:border-[#E94BA8]/50 ${
            value[key] ? "border-[#E94BA8]/50 text-foreground" : "border-border text-muted-foreground"
          }`}
        >
          <option value="">{label}</option>
          {(meta?.options[key] ?? []).map((o) => (
            <option key={o} value={o}>
              {key === "gender" ? (o === "F" ? "Female" : "Male") : o}
            </option>
          ))}
        </select>
      ))}
      {active && (
        <button type="button" onClick={() => onChange({})} className="flex items-center gap-1 rounded-lg border border-border px-2.5 py-1.5 text-xs text-muted-foreground hover:text-foreground">
          <FilterX className="size-3.5" /> Clear
        </button>
      )}
    </div>
  );
}
