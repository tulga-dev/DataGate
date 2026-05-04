import { formatStatus } from "@/lib/utils/format";

export function StatusBadge({ status }: { status?: string | null }) {
  const tone =
    status === "approved"
      ? "border-emerald-200 bg-emerald-50 text-emerald-700"
      : status === "needs_review"
        ? "border-amber-200 bg-amber-50 text-amber-700"
        : status === "rejected"
          ? "border-red-200 bg-red-50 text-red-700"
          : "border-slate-200 bg-slate-50 text-slate-700";

  return (
    <span className={`inline-flex items-center rounded-md border px-2 py-1 text-xs font-medium ${tone}`}>
      {formatStatus(status)}
    </span>
  );
}
