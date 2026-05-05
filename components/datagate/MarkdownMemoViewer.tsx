"use client";

import { Copy, Download, Printer } from "lucide-react";

function renderInline(text: string) {
  return text.replace(/^[-*]\s+/, "");
}

export function MarkdownMemoViewer({ markdown }: { markdown?: string | null }) {
  const content = markdown || "No credit memo generated yet.";
  const lines = content.split("\n");

  async function copyMarkdown() {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      await navigator.clipboard.writeText(content);
    }
  }

  function downloadMarkdown() {
    const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "datagate-credit-memo.md";
    anchor.click();
    URL.revokeObjectURL(url);
  }

  function printMemo() {
    window.print();
  }

  return (
    <div className="rounded-3xl border border-white/10 bg-white/[0.055] p-4 backdrop-blur">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3 print:hidden">
        <div>
          <p className="text-sm font-semibold text-white">Institutional memo preview</p>
          <p className="mt-1 text-xs text-slate-400">Deterministic Markdown, ready for review and copy-out.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={copyMarkdown} className="memo-action-button">
            <Copy className="h-4 w-4" />
            Copy Markdown
          </button>
          <button type="button" onClick={downloadMarkdown} className="memo-action-button">
            <Download className="h-4 w-4" />
            Download
          </button>
          <button type="button" onClick={printMemo} className="memo-action-button">
            <Printer className="h-4 w-4" />
            Print
          </button>
        </div>
      </div>
      <article className="memo-print mx-auto max-w-4xl rounded-2xl border border-slate-200 bg-white p-8 text-slate-900 shadow-2xl shadow-black/30">
        {lines.map((line, index) => {
          const key = `${index}-${line}`;
          if (line.startsWith("# ")) {
            return (
              <h1 key={key} className="mb-6 mt-2 border-b border-slate-200 pb-4 text-2xl font-semibold tracking-normal text-slate-950">
                {line.replace("# ", "")}
              </h1>
            );
          }
          if (line.startsWith("## ")) {
            return (
              <h2 key={key} className="mb-3 mt-7 text-base font-semibold text-slate-950">
                {line.replace("## ", "")}
              </h2>
            );
          }
          if (line.startsWith("|")) {
            return (
              <pre key={key} className="overflow-x-auto whitespace-pre-wrap border-b border-slate-100 px-3 py-1 text-xs text-slate-700">
                {line}
              </pre>
            );
          }
          if (line.startsWith("- ")) {
            return (
              <p key={key} className="ml-3 py-1 text-sm leading-6 text-slate-700">
                <span className="mr-2 text-slate-950">-</span>
                {renderInline(line)}
              </p>
            );
          }
          if (line.startsWith(">")) {
            return (
              <p key={key} className="border-l border-slate-300 bg-slate-50 py-1 pl-3 text-sm leading-6 text-slate-700">
                {line.replace(/^>\s?/, "")}
              </p>
            );
          }
          return line.trim() ? (
            <p key={key} className="py-1 text-sm leading-7 text-slate-700">
              {line}
            </p>
          ) : (
            <div key={key} className="h-2" />
          );
        })}
      </article>
    </div>
  );
}
