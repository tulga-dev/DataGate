import { NextResponse } from "next/server";
import { z } from "zod";
import { processDocumentFile } from "@/lib/document-processing/router";
import { documentTypes, ocrEngines } from "@/lib/document-processing/types";
import { saveMockProcessedDocument } from "@/lib/storage/mock-store";
import { hasSupabaseConfig, saveSupabaseProcessedDocument } from "@/lib/storage/supabase";

export const dynamic = "force-dynamic";

const MAX_FILE_SIZE = 20 * 1024 * 1024;
const supportedTypes = new Set(["application/pdf", "image/png", "image/jpeg", "image/jpg"]);

const RequestOptionsSchema = z.object({
  documentType: z.union([z.enum(documentTypes), z.literal("auto")]).default("auto"),
  preferredEngine: z.enum(ocrEngines).optional(),
  fallbackEngine: z.enum(["paddleocr", "surya", "mock"]).default("mock"),
  forceMock: z.boolean().default(false)
});

function parseBoolean(value: FormDataEntryValue | null) {
  return value === "true" || value === "1";
}

export async function POST(request: Request) {
  try {
    const formData = await request.formData();
    const file = formData.get("file");

    if (!(file instanceof File)) {
      return NextResponse.json({ error: "missing_file", message: "A document file is required." }, { status: 400 });
    }

    if (!supportedTypes.has(file.type)) {
      return NextResponse.json(
        { error: "unsupported_file_type", message: "Supported file types are PDF, PNG, JPG, and JPEG." },
        { status: 415 }
      );
    }

    if (file.size > MAX_FILE_SIZE) {
      return NextResponse.json(
        { error: "file_too_large", message: "File size limit is 20MB." },
        { status: 413 }
      );
    }

    const options = RequestOptionsSchema.parse({
      documentType: formData.get("documentType")?.toString() || "auto",
      preferredEngine: formData.get("preferredEngine")?.toString() || undefined,
      fallbackEngine: formData.get("fallbackEngine")?.toString() || "mock",
      forceMock: parseBoolean(formData.get("forceMock"))
    });

    const processed = await processDocumentFile(file, {
      preferredEngine: options.preferredEngine,
      fallbackEngine: options.fallbackEngine,
      forceMock: options.forceMock,
      requestedDocumentType: options.documentType
    });

    const saved = hasSupabaseConfig()
      ? await saveSupabaseProcessedDocument(file, processed)
      : await saveMockProcessedDocument(file, processed);

    if (!saved) {
      const fallback = await saveMockProcessedDocument(file, processed);
      return NextResponse.json({ mode: "mock", document: fallback, processed });
    }

    return NextResponse.json({
      mode: hasSupabaseConfig() ? "supabase" : "mock",
      document: saved,
      processed
    });
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: "schema_validation_failure", message: error.message, issues: error.issues },
        { status: 422 }
      );
    }

    return NextResponse.json(
      {
        error: "ocr_failure",
        message: error instanceof Error ? error.message : "Document processing failed."
      },
      { status: 500 }
    );
  }
}
