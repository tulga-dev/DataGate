import { AlertTriangle } from "lucide-react";

export function WarningPanel({ warnings }: { warnings: string[] }) {
  if (warnings.length === 0) {
    return (
      <div className="rounded-md border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
        No warnings detected.
      </div>
    );
  }

  return (
    <div className="rounded-md border border-amber-200 bg-amber-50 p-4">
      <div className="flex items-center gap-2 text-sm font-semibold text-amber-900">
        <AlertTriangle className="h-4 w-4" />
        Warnings
      </div>
      <ul className="mt-3 space-y-2 text-sm text-amber-900">
        {warnings.map((warning) => (
          <li key={warning}>• {warning}</li>
        ))}
      </ul>
    </div>
  );
}
