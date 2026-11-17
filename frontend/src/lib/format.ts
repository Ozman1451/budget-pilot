/** Number formatting shared by every chart/table. Formats: pkr | pct (0–1) | pct100 (0–100) | x | int | s | mb. */
export function short(v: number): string {
  const a = Math.abs(v);
  if (a >= 1e9) return `${(v / 1e9).toFixed(2)}B`;
  if (a >= 1e6) return `${(v / 1e6).toFixed(2)}M`;
  if (a >= 1e3) return `${(v / 1e3).toFixed(a >= 1e5 ? 0 : 1)}K`;
  return v.toFixed(a < 10 && a % 1 ? 2 : 0);
}

export function fmt(v: unknown, format?: string, compact = false): string {
  if (v == null || v === "") return "–";
  if (typeof v !== "number") return String(v);
  if (!Number.isFinite(v)) return "–";
  switch (format) {
    case "pkr":
      return compact ? `Rs ${short(v)}` : `Rs ${Math.round(v).toLocaleString("en-US")}`;
    case "pct":
      return `${(v * 100).toFixed(v < 0.1 ? 2 : 1)}%`;
    case "pct100":
      return `${v.toFixed(1)}%`;
    case "x":
      return `${v.toFixed(2)}×`;
    case "int":
      return compact ? short(v) : Math.round(v).toLocaleString("en-US");
    case "s":
      return v < 1 ? `${(v * 1000).toFixed(0)} ms` : `${v.toFixed(2)} s`;
    case "mb":
      return v >= 1024 ? `${(v / 1024).toFixed(2)} GB` : `${v.toFixed(0)} MB`;
    case "rows":
      return short(v);
    default:
      return Math.abs(v) >= 1000 ? short(v) : String(Math.round(v * 100) / 100);
  }
}
