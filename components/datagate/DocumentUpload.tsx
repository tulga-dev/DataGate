"use client";

import { useRouter } from "next/navigation";
import { ChangeEvent, DragEvent, useMemo, useState } from "react";
import { FileUp, Loader2, UploadCloud } from "lucide-react";
import { documentTypes } from "@/lib/document-processing/types";
import { formatDocumentType } from "@/lib/utils/format";

const loadingSteps = [
  "Uploading document",
  "Running OCR",
  "Classifying document",
  "Extracting fields",
  "Saving result"
];

export function DocumentUpload() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [documentType, setDocumentType] = useState("auto");
  const [isDragging, setIsDragging] = useState(false);
  const [activeStep, setActiveStep] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fileName = useMemo(() => file?.name ?? "PDF, PNG, JPG, JPEG", [file]);

  function pickFile(event: ChangeEvent<HTMLInputElement>) {
    setFile(event.target.files?.[0] ?? null);
    setError(null);
  }

  function onDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setIsDragging(false);
    setFile(event.dataTransfer.files?.[0] ?? null);
    setError(null);
  }

  async function submit() {
    if (!file) {
      setError("Select a supported document first.");
      return;
    }

    setError(null);
    const formData = new FormData();
    formData.append("file", file);
    formData.append("documentType", documentType);

    let stepIndex = 0;
    setActiveStep(loadingSteps[stepIndex]);
    const interval = window.setInterval(() => {
      stepIndex = Math.min(stepIndex + 1, loadingSteps.length - 1);
      setActiveStep(loadingSteps[stepIndex]);
    }, 650);

    try {
      const response = await fetch("/api/documents/process", {
        method: "POST",
        body: formData
      });
      const body = await response.json();

      if (!response.ok) {
        throw new Error(body.message ?? "Document processing failed.");
      }

      router.push(`/documents/${body.document.id}`);
      router.refresh();
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Document processing failed.");
    } finally {
      window.clearInterval(interval);
      setActiveStep(null);
    }
  }

  return (
    <div className="rounded-md border border-slate-200 bg-white p-5 shadow-soft">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-md bg-blue-50 text-blue-700">
          <FileUp className="h-5 w-5" />
        </div>
        <div>
          <h2 className="text-base font-semibold text-slate-950">Upload document</h2>
          <p className="text-sm text-slate-500">PDF, PNG, JPG, JPEG up to 20MB</p>
        </div>
      </div>

      <div className="mt-5 space-y-4">
        <label
          onDragOver={(event) => {
            event.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={onDrop}
          className={`flex min-h-40 cursor-pointer flex-col items-center justify-center rounded-md border border-dashed px-4 text-center transition ${
            isDragging ? "border-blue-500 bg-blue-50" : "border-slate-300 bg-slate-50 hover:border-blue-400"
          }`}
        >
          <UploadCloud className="h-8 w-8 text-slate-500" />
          <span className="mt-3 text-sm font-medium text-slate-950">{fileName}</span>
          <input className="sr-only" type="file" accept=".pdf,.png,.jpg,.jpeg" onChange={pickFile} />
        </label>

        <label className="block space-y-2">
          <span className="text-xs font-semibold uppercase tracking-normal text-slate-500">Document type</span>
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

        {activeStep ? (
          <div className="rounded-md border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">
            <div className="flex items-center gap-2 font-medium">
              <Loader2 className="h-4 w-4 animate-spin" />
              {activeStep}
            </div>
            <div className="mt-3 grid grid-cols-5 gap-2">
              {loadingSteps.map((step) => (
                <div
                  key={step}
                  className={`h-1 rounded-full ${loadingSteps.indexOf(step) <= loadingSteps.indexOf(activeStep) ? "bg-blue-600" : "bg-blue-100"}`}
                />
              ))}
            </div>
          </div>
        ) : null}

        {error ? <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}

        <button
          type="button"
          onClick={submit}
          disabled={!file || Boolean(activeStep)}
          className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-slate-950 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <FileUp className="h-4 w-4" />
          Process document
        </button>
      </div>
    </div>
  );
}
