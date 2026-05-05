import { AlertTriangle, CheckCircle2 } from "lucide-react";

export function RiskFlagList({ items, emptyLabel, tone = "risk" }: { items?: string[]; emptyLabel: string; tone?: "risk" | "good" | "warning" }) {
  const list = items ?? [];
  const Icon = tone === "good" ? CheckCircle2 : AlertTriangle;
  const toneClass =
    tone === "good"
      ? "border-emerald-300/25 bg-emerald-400/10 text-emerald-100 shadow-emerald-950/20"
      : tone === "warning"
        ? "border-amber-300/30 bg-amber-400/10 text-amber-100 shadow-amber-950/20"
        : "border-rose-300/35 bg-rose-400/10 text-rose-100 shadow-rose-950/20";

  if (list.length === 0) {
    return <div className="rounded-xl border border-white/10 bg-white/[0.04] p-4 text-sm text-slate-400">{emptyLabel}</div>;
  }

  return (
    <div className="space-y-2">
      {list.map((item) => (
        <div key={item} className={`flex items-start gap-2 rounded-xl border px-3 py-2 text-sm shadow-lg ${toneClass}`}>
          <Icon className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{item}</span>
        </div>
      ))}
    </div>
  );
}
