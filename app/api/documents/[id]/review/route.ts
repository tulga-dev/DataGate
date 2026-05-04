import { NextResponse } from "next/server";
import { setMockReviewStatus } from "@/lib/storage/mock-store";
import { hasSupabaseConfig, setSupabaseReviewStatus } from "@/lib/storage/supabase";

export const dynamic = "force-dynamic";

export async function POST(_request: Request, { params }: { params: { id: string } }) {
  try {
    const document = hasSupabaseConfig()
      ? await setSupabaseReviewStatus(params.id, "needs_review")
      : await setMockReviewStatus(params.id, "needs_review");

    if (!document) {
      return NextResponse.json({ error: "not_found", message: "Document not found." }, { status: 404 });
    }

    return NextResponse.json({ document });
  } catch (error) {
    return NextResponse.json(
      {
        error: "database_unavailable",
        message: error instanceof Error ? error.message : "Unable to send document to review."
      },
      { status: 503 }
    );
  }
}
