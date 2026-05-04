import { CheckCircle2, FileText, Gauge, UserCheck } from "lucide-react";
import type { DocumentStats } from "@/lib/document-processing/types";
import { formatPercent } from "@/lib/utils/format";

export function DashboardCards({ stats }: { stats: DocumentStats }) {
  const cards = [
    {
      label: "Documents processed",
      value: stats.documentsProcessed.toLocaleString(),
      icon: FileText
    },
    {
      label: "Average OCR confidence",
      value: formatPercent(stats.averageOcrConfidence),
      icon: Gauge
    },
    {
      label: "Needs human review",
      value: stats.needsHumanReview.toLocaleString(),
      icon: UserCheck
    },
    {
      label: "Approved documents",
      value: stats.approvedDocuments.toLocaleString(),
      icon: CheckCircle2
    }
  ];

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {cards.map((card) => {
        const Icon = card.icon;

        return (
          <div key={card.label} className="rounded-md border border-slate-200 bg-white p-5 shadow-soft">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-slate-500">{card.label}</span>
              <Icon className="h-4 w-4 text-blue-600" />
            </div>
            <div className="mt-4 text-3xl font-semibold tracking-normal text-slate-950">{card.value}</div>
          </div>
        );
      })}
    </div>
  );
}
