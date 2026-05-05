import type { ReactNode } from "react";
import { cn } from "@/lib/utils/format";

type SummaryCardProps = {
  label: string;
  value: ReactNode;
  detail?: ReactNode;
  tone?: "default" | "good" | "warning" | "risk";
};

const tones = {
  default: "border-white/10 bg-white/[0.055]",
  good: "border-emerald-300/25 bg-emerald-400/10",
  warning: "border-amber-300/30 bg-amber-400/10",
  risk: "border-rose-300/30 bg-rose-400/10"
};

export function SummaryCard({ label, value, detail, tone = "default" }: SummaryCardProps) {
  return (
    <div className={cn("rounded-2xl border p-4 shadow-2xl shadow-black/20 backdrop-blur", tones[tone])}>
      <p className="text-xs font-medium uppercase tracking-[0.16em] text-slate-400">{label}</p>
      <div className="mt-3 text-2xl font-semibold tracking-normal text-white">{value}</div>
      {detail ? <div className="mt-2 text-xs leading-5 text-slate-400">{detail}</div> : null}
    </div>
  );
}
