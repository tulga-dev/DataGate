"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

export function RawTextViewer({ rawText }: { rawText: string }) {
  const [open, setOpen] = useState(false);

  return (
    <section className="rounded-md border border-slate-200 bg-white">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-semibold text-slate-900"
      >
        Raw OCR text
        {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
      </button>
      {open ? (
        <pre className="max-h-96 overflow-auto border-t border-slate-200 bg-slate-950 p-4 text-xs leading-6 text-slate-100">
          {rawText}
        </pre>
      ) : null}
    </section>
  );
}
