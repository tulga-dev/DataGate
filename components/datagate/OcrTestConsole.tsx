"use client";

import Link from "next/link";
import { ChangeEvent, DragEvent, useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, FileSearch, Loader2, UploadCloud } from "lucide-react";
import { documentTypes, ocrEngines } from "@/lib/document-processing/types";
import { formatDocumentType, formatPercent } from "@/lib/utils/format";

type ProcessResponse = {
  mode: string;
  document: {
    id: string;
    originalFilename: string;
    status: string;
    documentType: string;
  };
  processed: {
    ocr: {
      engine: string;
      engineVersion?: string | null;
      rawText: string;
      languageGuess: string;
      confidence: number;
      warnings: string[];
      processingTimeMs: number;
      fallbackUsed: boolean;
      fallbackReason?: string | null;
      pages: Array<{
        pageNumber: number;
        text: string;
        confidence: number;
      }>;
    };
    classification: unknown;
    extraction: {
      confidence: number;
      warnings: string[];
      fields: Record<string, unknown>;
    };
  };
};

const fallbackEngines = ["mock", "paddleocr", "surya"] as const;

export function OcrTestConsole() {
  const [file, setFile] = useState<File | null>(null);
  const [documentType, setDocumentType] = useState("auto");
  const [preferredEngine, setPreferredEngine] = useState("paddleocr");
  const [fallbackEngine, setFallbackEngine] = useState("mock");
  const [forceMock, setForceMock] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ProcessResponse | null>(null);

  const fileLabel = useMemo(() => file?.name ?? "Drop a PDF or image here", [file]);

  function pickFile(event: ChangeEvent<HTMLInputElement>) {
    setFile(event.target.files?.[0] ?? null);
    setError(null);
    setResult(null);
  }

  function onDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setDragging(false);
    setFile(event.dataTransfer.files?.[0] ?? null);
    setError(null);
    setResult(null);
  }

  async function runTest() {
    if (!file) {
      setError("Choose a real PDF or image first.");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("documentType", documentType);
    formData.append("preferredEngine", preferredEngine);
    formData.append("fallbackEngine", fallbackEngine);
    formData.append("forceMock", String(forceMock));

    try {
      const response = await fetch("/api/documents/process", {
        method: "POST",
        body: formData
      });
      const body = await response.json();

      if (!response.ok) {
        throw new Error(body.message ?? "OCR test failed.");
      }

      setResult(body);
    } catch (testError) {
      setError(testError instanceof Error ? testError.message : "OCR test failed.");
    } finally {
      setLoading(false);
    }
  }

  const ocr = result?.processed.ocr;
  const warnings = Array.from(new Set([...(ocr?.warnings ?? []), ...(result?.processed.extraction.warnings ?? [])]));

  return (
    <div className="grid gap-6 lg:grid-cols-[420px_minmax(0,1fr)]">
      <section className="rounded-md border border-slate-200 bg-white p-5 shadow-soft">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-md bg-blue-50 text-blue-700">
            <FileSearch className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-slate-950">Real document OCR test</h2>
            <p className="text-sm text-slate-500">Upload a PDF or image and inspect the OCR response.</p>
          </div>
        </div>

        <div className="mt-5 space-y-4">
          <label
            onDragOver={(event) => {
              event.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            className={`flex min-h-44 cursor-pointer flex-col items-center justify-center rounded-md border border-dashed px-4 text-center transition ${
              dragging ? "border-blue-500 bg-blue-50" : "border-slate-300 bg-slate-50 hover:border-blue-400"
            }`}
          >
            <UploadCloud className="h-8 w-8 text-slate-500" />
            <span className="mt-3 text-sm font-medium text-slate-950">{fileLabel}</span>
            <span className="mt-1 text-xs text-slate-500">PDF, PNG, JPG, JPEG up to 20MB</span>
            <input className="sr-only" type="file" accept=".pdf,.png,.jpg,.jpeg" onChange={pickFile} />
          </label>

          <label className="block space-y-2">
            <span className="text-xs font-semibold uppercase tracking-normal text-slate-500">OCR engine</span>
            <select
              value={preferredEngine}
              onChange={(event) => setPreferredEngine(event.target.value)}
              className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-950 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
            >
              {ocrEngines.map((engine) => (
                <option key={engine} value={engine}>
                  {engine}
                </option>
              ))}
            </select>
          </label>

          <label className="block space-y-2">
            <span className="text-xs font-semibold uppercase tracking-normal text-slate-500">Fallback engine</span>
            <select
              value={fallbackEngine}
              onChange={(event) => setFallbackEngine(event.target.value)}
              className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-950 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
            >
              {fallbackEngines.map((engine) => (
                <option key={engine} value={engine}>
                  {engine}
                </option>
              ))}
            </select>
          </label>

          <label className="block space-y-2">
            <span className="text-xs font-semibold uppercase tracking-normal text-slate-500">Document type hint</span>
            <select
              value={documentType}
              onChange={(event) => setDocumentType(event.target.value)}
              className="w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-950 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
            >
              <option value="auto">Auto-detect</option>
              {documentTypes
                .filter((type) => type !== "unknown")
                .map((type) => (
                  <option key={type} value={type}>
                    {formatDocumentType(type)}
                  </option>
                ))}
            </select>
          </label>

          <label className="flex items-center justify-between gap-3 rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
            <span className="text-sm font-medium text-slate-700">Force mock mode</span>
            <input
              type="checkbox"
              checked={forceMock}
              onChange={(event) => setForceMock(event.target.checked)}
              className="h-4 w-4 accent-blue-600"
            />
          </label>

          {error ? <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}

          <button
            type="button"
            onClick={runTest}
            disabled={!file || loading}
            className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-slate-950 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileSearch className="h-4 w-4" />}
            {loading ? "Running OCR" : "Run OCR test"}
          </button>
        </div>
      </section>

      <section className="space-y-4">
        {!result ? (
          <div className="rounded-md border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">
            Results will appear here after OCR runs.
          </div>
        ) : null}

        {result && ocr ? (
          <>
            <div className="rounded-md border border-slate-200 bg-white p-5 shadow-soft">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-slate-950">OCR result</h2>
                  <p className="mt-1 text-sm text-slate-500">{result.document.originalFilename}</p>
                </div>
                <Link
                  href={`/documents/${result.document.id}`}
                  className="inline-flex items-center justify-center rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-950 transition hover:bg-slate-50"
                >
                  Open saved document
                </Link>
              </div>

              <dl className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                <div className="rounded-md bg-slate-50 p-3">
                  <dt className="text-xs font-semibold uppercase tracking-normal text-slate-500">Engine</dt>
                  <dd className="mt-1 text-sm font-medium text-slate-950">{ocr.engine}</dd>
                </div>
                <div className="rounded-md bg-slate-50 p-3">
                  <dt className="text-xs font-semibold uppercase tracking-normal text-slate-500">Version</dt>
                  <dd className="mt-1 text-sm font-medium text-slate-950">{ocr.engineVersion ?? "N/A"}</dd>
                </div>
                <div className="rounded-md bg-slate-50 p-3">
                  <dt className="text-xs font-semibold uppercase tracking-normal text-slate-500">OCR confidence</dt>
                  <dd className="mt-1 text-sm font-medium text-slate-950">{formatPercent(ocr.confidence)}</dd>
                </div>
                <div className="rounded-md bg-slate-50 p-3">
                  <dt className="text-xs font-semibold uppercase tracking-normal text-slate-500">Language</dt>
                  <dd className="mt-1 text-sm font-medium text-slate-950">{ocr.languageGuess}</dd>
                </div>
                <div className="rounded-md bg-slate-50 p-3">
                  <dt className="text-xs font-semibold uppercase tracking-normal text-slate-500">Processing time</dt>
                  <dd className="mt-1 text-sm font-medium text-slate-950">{ocr.processingTimeMs}ms</dd>
                </div>
                <div className="rounded-md bg-slate-50 p-3">
                  <dt className="text-xs font-semibold uppercase tracking-normal text-slate-500">Pages</dt>
                  <dd className="mt-1 text-sm font-medium text-slate-950">{ocr.pages.length}</dd>
                </div>
              </dl>

              {ocr.fallbackUsed ? (
                <div className="mt-4 rounded-md border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">
                  Processed with fallback OCR engine. {ocr.fallbackReason ?? ""}
                </div>
              ) : (
                <div className="mt-4 flex items-center gap-2 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
                  <CheckCircle2 className="h-4 w-4" />
                  OCR engine completed without fallback.
                </div>
              )}
            </div>

            {warnings.length > 0 ? (
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
            ) : null}

            <div className="rounded-md border border-slate-200 bg-white p-5 shadow-soft">
              <h3 className="text-base font-semibold text-slate-950">Extracted fields</h3>
              <pre className="mt-3 max-h-80 overflow-auto rounded-md bg-slate-950 p-4 text-xs leading-6 text-slate-100">
                {JSON.stringify(result.processed.extraction.fields, null, 2)}
              </pre>
            </div>

            <div className="rounded-md border border-slate-200 bg-white p-5 shadow-soft">
              <h3 className="text-base font-semibold text-slate-950">Raw OCR text</h3>
              <pre className="mt-3 max-h-[520px] overflow-auto rounded-md bg-slate-950 p-4 text-xs leading-6 text-slate-100">
                {ocr.rawText || "No text returned."}
              </pre>
            </div>
          </>
        ) : null}
      </section>
    </div>
  );
}
