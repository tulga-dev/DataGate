"use client";

import { ChangeEvent, DragEvent, useState } from "react";
import { FileText, UploadCloud, X } from "lucide-react";
import { cn, formatBytes } from "@/lib/utils/format";

type FileDropzoneProps = {
  file: File | null;
  onFileChange: (file: File | null) => void;
};

export function FileDropzone({ file, onFileChange }: FileDropzoneProps) {
  const [dragging, setDragging] = useState(false);

  function pickFile(event: ChangeEvent<HTMLInputElement>) {
    onFileChange(event.target.files?.[0] ?? null);
  }

  function dropFile(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setDragging(false);
    onFileChange(event.dataTransfer.files?.[0] ?? null);
  }

  return (
    <label
      onDragOver={(event) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={dropFile}
      className={cn(
        "group relative flex min-h-56 cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed px-5 text-center transition",
        dragging
          ? "border-cyan-300 bg-cyan-400/10"
          : "border-white/15 bg-white/[0.04] hover:border-cyan-300/60 hover:bg-white/[0.06]"
      )}
    >
      <input className="sr-only" type="file" accept=".pdf,.png,.jpg,.jpeg" onChange={pickFile} />
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.06] text-cyan-200 shadow-2xl shadow-cyan-950/40">
        {file ? <FileText className="h-6 w-6" /> : <UploadCloud className="h-6 w-6" />}
      </div>
      <div className="mt-4">
        <p className="text-sm font-semibold text-white">{file ? file.name : "Drop a financial PDF here"}</p>
        <p className="mt-1 text-xs text-slate-400">
          {file ? `${formatBytes(file.size)} selected` : "PDF preferred. PNG/JPG also supported by OCR path."}
        </p>
      </div>
      {file ? (
        <button
          type="button"
          onClick={(event) => {
            event.preventDefault();
            onFileChange(null);
          }}
          className="absolute right-4 top-4 inline-flex h-8 w-8 items-center justify-center rounded-full border border-white/10 bg-white/[0.06] text-slate-300 transition hover:bg-white/10 hover:text-white"
          aria-label="Clear selected file"
        >
          <X className="h-4 w-4" />
        </button>
      ) : null}
    </label>
  );
}
