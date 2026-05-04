import { notFound } from "next/navigation";
import { DocumentResultView } from "@/components/datagate/DocumentResultView";
import { getMockDocument } from "@/lib/storage/mock-store";
import { getSupabaseDocument, hasSupabaseConfig } from "@/lib/storage/supabase";

export const dynamic = "force-dynamic";

async function loadDocument(id: string) {
  try {
    if (hasSupabaseConfig()) {
      const document = await getSupabaseDocument(id);

      if (document) {
        return document;
      }
    }
  } catch {
    // Preserve local demo routing when database credentials are incomplete or unavailable.
  }

  return getMockDocument(id);
}

export default async function DocumentDetailPage({ params }: { params: { id: string } }) {
  const document = await loadDocument(params.id);

  if (!document) {
    notFound();
  }

  return <DocumentResultView initialDocument={document} />;
}
