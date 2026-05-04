import Link from "next/link";
import { Plus } from "lucide-react";
import { DocumentTable } from "@/components/datagate/DocumentTable";
import { listMockDocuments } from "@/lib/storage/mock-store";
import { hasSupabaseConfig, listSupabaseDocuments } from "@/lib/storage/supabase";

export const dynamic = "force-dynamic";

async function loadDocuments() {
  try {
    if (hasSupabaseConfig()) {
      const documents = await listSupabaseDocuments();

      if (documents) {
        return documents;
      }
    }
  } catch {
    // Keep local demo mode reachable if configured database is unavailable.
  }

  return listMockDocuments();
}

export default async function DocumentsPage() {
  const documents = await loadDocuments();

  return (
    <main className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <header className="flex flex-col gap-4 border-b border-slate-200 pb-6 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <Link href="/" className="text-sm font-medium text-blue-700 hover:text-blue-900">
            DataGate
          </Link>
          <h1 className="mt-2 text-3xl font-semibold tracking-normal text-slate-950">Documents</h1>
          <p className="mt-2 text-sm text-slate-500">Processed financial documents and review status.</p>
        </div>
        <Link
          href="/upload"
          className="inline-flex items-center justify-center gap-2 rounded-md bg-slate-950 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-800"
        >
          <Plus className="h-4 w-4" />
          Upload document
        </Link>
      </header>

      <section className="mt-8">
        <DocumentTable documents={documents} />
      </section>
    </main>
  );
}
