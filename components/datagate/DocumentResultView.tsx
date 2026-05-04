"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Download, FileJson, RefreshCcw, Send, ShieldCheck } from "lucide-react";
import { useState } from "react";
import type { DocumentRecord } from "@/lib/document-processing/types";
import { formatBytes, formatDateTime, formatDocumentType } from "@/lib/utils/format";
import { ConfidenceBadge } from "./ConfidenceBadge";
import { FieldEditor } from "./FieldEditor";
import { RawTextViewer } from "./RawTextViewer";
import { StatusBadge } from "./StatusBadge";
import { WarningPanel } from "./WarningPanel";

type ExtractionShape = {
  fields?: Record<string, string | number | boolean | null | Array<unknown> | Record<string, unknown>>;
  warnings?: string[];
};

function getExtraction(document: DocumentRecord): ExtractionShape {
  if (document.extractedData && typeof document.extractedData === "object") {
    return document.extractedData as ExtractionShape;
  }

  return {};
}

export function DocumentResultView({ initialDocument }: { initialDocument: DocumentRecord }) {
  const router = useRouter();
  const [document, setDocument] = useState(initialDocument);
  const [actionError, setActionError] = useState<string | null>(null);
  const extraction = getExtraction(document);
  const fields = extraction.fields ?? {};
  const warnings = Array.from(new Set([...(document.warnings ?? []), ...(extraction.warnings ?? [])]));

  async function mutate(action: "approve" | "review") {
    setActionError(null);
    const response = await fetch(`/api/documents/${document.id}/${action}`, {
      method: "POST"
    });
    const body = await response.json();

    if (!response.ok) {
      setActionError(body.message ?? "Action failed.");
      return;
    }

    setDocument(body.document);
    router.refresh();
  }

  async function saveFields(nextFields: Record<string, unknown>) {
    setActionError(null);
    const currentExtraction =
      document.extractedData && typeof document.extractedData === "object"
        ? (document.extractedData as Record<string, unknown>)
        : {};
    const nextExtraction = {
      ...currentExtraction,
      fields: nextFields
    };
    const response = await fetch(`/api/documents/${document.id}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        extractedData: nextExtraction,
        status: document.status === "approved" ? "approved" : "needs_review"
      })
    });
    const body = await response.json();

    if (!response.ok) {
      setActionError(body.message ?? "Save failed.");
      return;
    }

    setDocument(body.document);
    router.refresh();
  }

  function exportJson() {
    const blob = new Blob([JSON.stringify(document, null, 2)], {
      type: "application/json"
    });
    const url = URL.createObjectURL(blob);
    const link = window.document.createElement("a");
    link.href = url;
    link.download = `${document.originalFilename.replace(/\.[^.]+$/, "")}.json`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="flex flex-col gap-4 border-b border-slate-200 pb-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <Link href="/documents" className="text-sm font-medium text-blue-700 hover:text-blue-900">
            Documents
          </Link>
          <h1 className="mt-2 text-3xl font-semibold tracking-normal text-slate-950">{document.originalFilename}</h1>
          <p className="mt-2 text-sm text-slate-500">
            Processed {formatDateTime(document.createdAt)} • {formatBytes(document.fileSize)}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => mutate("approve")}
            className="inline-flex items-center gap-2 rounded-md bg-slate-950 px-3 py-2 text-sm font-semibold text-white transition hover:bg-slate-800"
          >
            <ShieldCheck className="h-4 w-4" />
            Approve
          </button>
          <button
            type="button"
            onClick={() => mutate("review")}
            className="inline-flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-950 transition hover:bg-slate-50"
          >
            <Send className="h-4 w-4" />
            Send to human review
          </button>
          <button
            type="button"
            onClick={exportJson}
            className="inline-flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-950 transition hover:bg-slate-50"
          >
            <Download className="h-4 w-4" />
            Export JSON
          </button>
          <Link
            href="/upload"
            className="inline-flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-950 transition hover:bg-slate-50"
          >
            <RefreshCcw className="h-4 w-4" />
            Reprocess
          </Link>
        </div>
      </div>

      {actionError ? (
        <div className="mt-5 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{actionError}</div>
      ) : null}

      <div className="mt-8 grid gap-6 lg:grid-cols-[360px_minmax(0,1fr)]">
        <aside className="space-y-4">
          <div className="flex aspect-[4/5] items-center justify-center rounded-md border border-slate-200 bg-slate-100 text-slate-500">
            <div className="text-center">
              <FileJson className="mx-auto h-10 w-10" />
              <p className="mt-3 text-sm font-medium">Document preview</p>
            </div>
          </div>
          <div className="rounded-md border border-slate-200 bg-white p-4">
            <dl className="space-y-4 text-sm">
              <div>
                <dt className="text-slate-500">Detected type</dt>
                <dd className="mt-1 font-medium text-slate-950">{formatDocumentType(document.documentType)}</dd>
              </div>
              <div>
                <dt className="text-slate-500">OCR engine</dt>
                <dd className="mt-1 font-medium text-slate-950">
                  {document.ocrEngine} {document.ocrEngineVersion ? `(${document.ocrEngineVersion})` : ""}
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">Fallback used</dt>
                <dd className="mt-1 font-medium text-slate-950">{document.fallbackUsed ? "Yes" : "No"}</dd>
              </div>
              {document.fallbackReason ? (
                <div>
                  <dt className="text-slate-500">Fallback reason</dt>
                  <dd className="mt-1 text-slate-700">{document.fallbackReason}</dd>
                </div>
              ) : null}
              <div>
                <dt className="text-slate-500">Processing time</dt>
                <dd className="mt-1 font-medium text-slate-950">{document.processingTimeMs}ms</dd>
              </div>
              <div>
                <dt className="text-slate-500">OCR confidence</dt>
                <dd className="mt-1">
                  <ConfidenceBadge value={document.ocrConfidence} />
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">Extraction confidence</dt>
                <dd className="mt-1">
                  <ConfidenceBadge value={document.confidence} />
                </dd>
              </div>
              <div>
                <dt className="text-slate-500">Review status</dt>
                <dd className="mt-1">
                  <StatusBadge status={document.status} />
                </dd>
              </div>
            </dl>
          </div>
          {document.fallbackUsed ? (
            <div className="rounded-md border border-blue-200 bg-blue-50 p-4 text-sm font-medium text-blue-800">
              Processed with fallback OCR engine.
            </div>
          ) : null}
          <WarningPanel warnings={warnings} />
        </aside>

        <main className="space-y-6">
          <section className="rounded-md border border-slate-200 bg-white p-5 shadow-soft">
            <div className="mb-5 flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-slate-950">Extracted fields</h2>
                <p className="mt-1 text-sm text-slate-500">Corrections update the saved structured data.</p>
              </div>
            </div>
            <FieldEditor fields={fields} onSave={saveFields} />
          </section>
          <RawTextViewer rawText={document.rawText} />
        </main>
      </div>
    </div>
  );
}
