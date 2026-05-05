"use client";

import { Copy } from "lucide-react";

export function JsonViewer({ value }: { value: unknown }) {
  const json = JSON.stringify(value ?? {}, null, 2);

  async function copyJson() {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      await navigator.clipboard.writeText(json);
    }
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-white/10 bg-[#050812]/95 shadow-2xl shadow-black/25">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 bg-white/[0.035] px-4 py-3">
        <div>
          <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">Raw API Response</span>
          <p className="mt-1 text-xs text-slate-500">Pretty-printed for inspection and issue reports.</p>
        </div>
        <button
          type="button"
          onClick={copyJson}
          className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/[0.06] px-3 py-1.5 text-xs font-semibold text-slate-200 transition hover:bg-white/10"
        >
          <Copy className="h-3.5 w-3.5" />
          Copy JSON
        </button>
      </div>
      <pre className="max-h-[720px] overflow-auto p-5 text-[12px] leading-6 text-cyan-50 selection:bg-cyan-300/20">
        <code>{json}</code>
      </pre>
    </div>
  );
}
