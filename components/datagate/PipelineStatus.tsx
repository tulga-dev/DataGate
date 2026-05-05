import { AlertTriangle, Check, Clock, Loader2, XCircle } from "lucide-react";
import { cn } from "@/lib/utils/format";
import type { PipelineStep, StepStatus } from "@/lib/datagate/types";

const labels: Record<PipelineStep, string> = {
  upload: "Upload",
  parse: "Parse",
  extract: "Extract",
  audit: "Audit",
  insights: "Insights",
  memo: "Memo"
};

const statusClass: Record<StepStatus, string> = {
  pending: "border-white/10 bg-white/[0.04] text-slate-400",
  running: "border-cyan-300/40 bg-cyan-400/10 text-cyan-100",
  success: "border-emerald-300/30 bg-emerald-400/10 text-emerald-100",
  warning: "border-amber-300/40 bg-amber-400/10 text-amber-100",
  failed: "border-rose-300/40 bg-rose-400/10 text-rose-100"
};

function StatusIcon({ status }: { status: StepStatus }) {
  if (status === "running") return <Loader2 className="h-3.5 w-3.5 animate-spin" />;
  if (status === "success") return <Check className="h-3.5 w-3.5" />;
  if (status === "warning") return <AlertTriangle className="h-3.5 w-3.5" />;
  if (status === "failed") return <XCircle className="h-3.5 w-3.5" />;
  return <Clock className="h-3.5 w-3.5" />;
}

export function PipelineStatus({ statuses }: { statuses: Record<PipelineStep, StepStatus> }) {
  const steps = Object.keys(labels) as PipelineStep[];

  return (
    <div className="grid gap-2 sm:grid-cols-3 xl:grid-cols-6">
      {steps.map((step) => {
        const status = statuses[step];
        return (
          <div
            key={step}
            className={cn("flex items-center gap-2 rounded-xl border px-3 py-3 text-xs font-semibold", statusClass[status])}
          >
            <StatusIcon status={status} />
            <span>{labels[step]}</span>
            <span className="ml-auto capitalize opacity-70">{status}</span>
          </div>
        );
      })}
    </div>
  );
}
