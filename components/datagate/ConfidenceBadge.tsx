import { formatPercent } from "@/lib/utils/format";

export function ConfidenceBadge({ value }: { value?: number | null }) {
  const confidence = value ?? 0;
  const tone =
    confidence >= 0.85
      ? "border-emerald-200 bg-emerald-50 text-emerald-700"
      : confidence >= 0.7
        ? "border-blue-200 bg-blue-50 text-blue-700"
        : "border-amber-200 bg-amber-50 text-amber-700";

  return (
    <span className={`inline-flex items-center rounded-md border px-2 py-1 text-xs font-medium ${tone}`}>
      {formatPercent(value)}
    </span>
  );
}
