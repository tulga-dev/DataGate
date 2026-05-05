import { formatPercent } from "@/lib/utils/format";

export function ConfidenceBadge({ value, dark = false }: { value?: number | null; dark?: boolean }) {
  const confidence = value ?? 0;
  const tone = dark
    ? confidence >= 0.85
      ? "border-emerald-300/30 bg-emerald-400/10 text-emerald-100"
    : confidence >= 0.7
        ? "border-cyan-300/30 bg-cyan-400/10 text-cyan-100"
        : confidence >= 0.55
          ? "border-amber-300/30 bg-amber-400/10 text-amber-100"
          : "border-rose-300/35 bg-rose-400/10 text-rose-100"
    : confidence >= 0.85
      ? "border-emerald-200 bg-emerald-50 text-emerald-700"
      : confidence >= 0.7
        ? "border-blue-200 bg-blue-50 text-blue-700"
        : confidence >= 0.55
          ? "border-amber-200 bg-amber-50 text-amber-700"
          : "border-red-200 bg-red-50 text-red-700";

  return (
    <span className={`inline-flex items-center rounded-md border px-2 py-1 text-xs font-medium ${tone}`}>
      {formatPercent(value)}
    </span>
  );
}
