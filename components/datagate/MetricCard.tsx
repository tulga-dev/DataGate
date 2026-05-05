import { formatPercent } from "@/lib/utils/format";

function formatMetric(value: number | null | undefined) {
  if (typeof value !== "number" || Number.isNaN(value)) return "—";
  if (Math.abs(value) <= 1) return formatPercent(value);
  return value.toFixed(2);
}

export function MetricCard({ label, value }: { label: string; value: number | null | undefined }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.055] p-4 backdrop-blur">
      <p className="text-xs font-medium uppercase tracking-[0.14em] text-slate-400">{label.replaceAll("_", " ")}</p>
      <p className="mt-3 text-2xl font-semibold text-white">{formatMetric(value)}</p>
    </div>
  );
}
