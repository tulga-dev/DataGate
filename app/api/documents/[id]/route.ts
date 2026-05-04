import { NextResponse } from "next/server";
import { z } from "zod";
import { reviewStatuses } from "@/lib/document-processing/types";
import { getMockDocument, updateMockDocument } from "@/lib/storage/mock-store";
import { getSupabaseDocument, hasSupabaseConfig, updateSupabaseDocument } from "@/lib/storage/supabase";

export const dynamic = "force-dynamic";

const UpdateDocumentSchema = z.object({
  extractedData: z.unknown().optional(),
  status: z.enum(reviewStatuses).optional()
});

export async function GET(_request: Request, { params }: { params: { id: string } }) {
  try {
    const document = hasSupabaseConfig()
      ? await getSupabaseDocument(params.id)
      : await getMockDocument(params.id);

    if (!document) {
      return NextResponse.json({ error: "not_found", message: "Document not found." }, { status: 404 });
    }

    return NextResponse.json({ document });
  } catch (error) {
    return NextResponse.json(
      {
        error: "database_unavailable",
        message: error instanceof Error ? error.message : "Unable to load document."
      },
      { status: 503 }
    );
  }
}

export async function PATCH(request: Request, { params }: { params: { id: string } }) {
  try {
    const body = UpdateDocumentSchema.parse(await request.json());
    const document = hasSupabaseConfig()
      ? await updateSupabaseDocument(params.id, body)
      : await updateMockDocument(params.id, body);

    if (!document) {
      return NextResponse.json({ error: "not_found", message: "Document not found." }, { status: 404 });
    }

    return NextResponse.json({ document });
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: "schema_validation_failure", message: error.message, issues: error.issues },
        { status: 422 }
      );
    }

    return NextResponse.json(
      {
        error: "database_unavailable",
        message: error instanceof Error ? error.message : "Unable to update document."
      },
      { status: 503 }
    );
  }
}
