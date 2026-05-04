import { NextResponse } from "next/server";
import type { DocumentRecord, DocumentStats, DocumentType } from "@/lib/document-processing/types";
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
    typeDistribution: Array.from(typeCounts.entries()).map(([documentType, count]) => ({
      documentType,
      count
    }))
  };
}

export async function GET() {
  try {
    if (hasSupabaseConfig()) {
      const documents = await listSupabaseDocuments();

      if (documents) {
        return NextResponse.json({
          mode: "supabase",
          documents,
          stats: buildStats(documents)
        });
      }
    }

    const documents = await listMockDocuments();
    const stats = await getMockStats();

    return NextResponse.json({
      mode: "mock",
      documents,
      stats
    });
  } catch (error) {
    return NextResponse.json(
      {
        error: "database_unavailable",
        message: error instanceof Error ? error.message : "Unable to load documents."
      },
      { status: 503 }
    );
  }
}
