import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { DashboardCards } from "@/components/datagate/DashboardCards";
import { DocumentTable } from "@/components/datagate/DocumentTable";
import { DocumentUpload } from "@/components/datagate/DocumentUpload";
import type { DocumentRecord, DocumentStats, DocumentType } from "@/lib/document-processing/types";
import { formatDocumentType } from "@/lib/utils/format";
import { getMockStats, listMockDocuments } from "@/lib/storage/mock-store";
import { hasSupabaseConfig, listSupabaseDocuments } from "@/lib/storage/supabase";

export const dynamic = "force-dynamic";

function buildStats(documents: DocumentRecord[]): DocumentStats {
  const typeCounts = new Map<DocumentType, number>();

  for (const document of documents) {
    typeCounts.set(document.documentType, (typeCounts.get(document.documentType) ?? 0) + 1);
  }

  return {
    documentsProcessed: documents.length,
    averageOcrConfidence:
      documents.reduce((sum, document) => sum + document.ocrConfidence, 0) / Math.max(documents.length, 1),
    needsHumanReview: documents.filter((document) => document.status === "needs_review").length,
    approvedDocuments: documents.filter((document) => document.status === "approved").length,
    typeDistribution: Array.from(typeCounts.entries()).map(([documentType, count]) => ({ documentType, count }))
  };
}

async function loadDashboard() {
  try {
    if (hasSupabaseConfig()) {
      const documents = await listSupabaseDocuments();

      if (documents) {
        return {
          documents,
          stats: buildStats(documents),
          mode: "supabase"
        };
      }
    }
  } catch {
    // The API routes expose database errors. The dashboard stays usable in local mock mode.
  }

  return {
    documents: await listMockDocuments(),
    stats: await getMockStats(),
    mode: "mock"
  };
}

export default async function DashboardPage() {
  const { documents, stats, mode } = await loadDashboard();

  return (
    <main className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <header className="flex flex-col gap-6 border-b border-slate-200 pb-8 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="inline-flex rounded-md border border-blue-200 bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-700">
            {mode === "mock" ? "Local mock mode" : "Supabase mode"}
          </div>
          <h1 className="mt-4 text-4xl font-semibold tracking-normal text-slate-950">DataGate</h1>
          <p className="mt-3 max-w-2xl text-lg text-slate-600">Mongolian Financial Document Intelligence</p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row">
          <Link
            href="/ocr-test"
            className="inline-flex items-center justify-center gap-2 rounded-md border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-slate-50"
          >
            Test real OCR
            <ArrowUpRight className="h-4 w-4" />
          </Link>
          <Link
            href="/upload"
            className="inline-flex items-center justify-center gap-2 rounded-md bg-slate-950 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-800"
          >
            Upload first document
            <ArrowUpRight className="h-4 w-4" />
          </Link>
        </div>
      </header>

      <div className="mt-8 space-y-8">
        <DashboardCards stats={stats} />

        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_380px]">
          <section className="space-y-4">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-lg font-semibold text-slate-950">Recent documents</h2>
              <Link href="/documents" className="text-sm font-semibold text-blue-700 hover:text-blue-900">
                View all
              </Link>
            </div>
            <DocumentTable documents={documents.slice(0, 6)} />
          </section>
          <DocumentUpload />
        </div>

        <section className="rounded-md border border-slate-200 bg-white p-5 shadow-soft">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <h2 className="text-lg font-semibold text-slate-950">Document type distribution</h2>
            <span className="text-sm text-slate-500">MVP placeholder</span>
          </div>
          <div className="mt-5 grid gap-3 md:grid-cols-2 lg:grid-cols-4">
            {stats.typeDistribution.map((item) => (
              <div key={item.documentType} className="rounded-md border border-slate-200 bg-slate-50 p-4">
                <div className="text-sm font-medium text-slate-600">{formatDocumentType(item.documentType)}</div>
                <div className="mt-3 text-2xl font-semibold text-slate-950">{item.count}</div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
