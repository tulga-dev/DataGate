import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import type { DocumentRecord, ReviewStatus } from "@/lib/document-processing/types";
import type { ProcessedDocumentPayload } from "@/lib/document-processing/router";

export function hasSupabaseConfig() {
  return Boolean(
    process.env.NEXT_PUBLIC_SUPABASE_URL &&
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY &&
      process.env.SUPABASE_SERVICE_ROLE_KEY
  );
}

export function getSupabaseAdminClient(): SupabaseClient | null {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

  if (!url || !serviceRoleKey) {
    return null;
  }

  return createClient(url, serviceRoleKey, {
    auth: {
      persistSession: false,
      autoRefreshToken: false
    }
  });
}

type DatabaseDocument = {
  id: string;
  original_filename: string;
  file_type: string | null;
  file_size: number | null;
  storage_path: string | null;
  document_type: DocumentRecord["documentType"];
  status: ReviewStatus;
  confidence: number | null;
  raw_text: string | null;
  ocr_markdown: string | null;
  extracted_data: unknown;
  warnings: string[] | null;
  ocr_engine: string | null;
  ocr_engine_version: string | null;
  ocr_confidence: number | null;
  layout_confidence: number | null;
  table_count: number | null;
  stamp_detected: boolean | null;
  processing_time_ms: number | null;
  fallback_used: boolean | null;
  fallback_reason: string | null;
  requires_human_review: boolean | null;
  created_at: string;
  updated_at: string;
};

export function mapDatabaseDocument(row: DatabaseDocument): DocumentRecord {
  return {
    id: row.id,
    originalFilename: row.original_filename,
    fileType: row.file_type,
    fileSize: row.file_size,
    storagePath: row.storage_path,
    documentType: row.document_type,
    status: row.status,
    confidence: row.confidence ?? 0,
    rawText: row.raw_text ?? "",
    ocrMarkdown: row.ocr_markdown,
    extractedData: row.extracted_data,
    warnings: row.warnings ?? [],
    ocrEngine: row.ocr_engine ?? "unknown",
    ocrEngineVersion: row.ocr_engine_version,
    ocrConfidence: row.ocr_confidence ?? 0,
    layoutConfidence: row.layout_confidence,
    tableCount: row.table_count ?? 0,
    stampDetected: row.stamp_detected ?? false,
    processingTimeMs: row.processing_time_ms ?? 0,
    fallbackUsed: row.fallback_used ?? false,
    fallbackReason: row.fallback_reason,
    requiresHumanReview: row.requires_human_review ?? false,
    createdAt: row.created_at,
    updatedAt: row.updated_at
  };
}

export async function listSupabaseDocuments() {
  const supabase = getSupabaseAdminClient();

  if (!supabase) {
    return null;
  }

  const { data, error } = await supabase
    .from("documents")
    .select("*")
    .order("created_at", { ascending: false })
    .limit(25);

  if (error) {
    throw new Error(error.message);
  }

  return (data as DatabaseDocument[]).map(mapDatabaseDocument);
}

export async function getSupabaseDocument(id: string) {
  const supabase = getSupabaseAdminClient();

  if (!supabase) {
    return null;
  }

  const { data, error } = await supabase.from("documents").select("*").eq("id", id).single();

  if (error) {
    throw new Error(error.message);
  }

  return mapDatabaseDocument(data as DatabaseDocument);
}

export async function saveSupabaseProcessedDocument(file: File, payload: ProcessedDocumentPayload) {
  const supabase = getSupabaseAdminClient();

  if (!supabase) {
    return null;
  }

  const warnings = Array.from(new Set([...payload.ocr.warnings, ...payload.extraction.warnings]));
  const requiresHumanReview = warnings.length > 0 || payload.extraction.confidence < 0.78;
  const status: ReviewStatus = requiresHumanReview ? "needs_review" : "auto_processed";

  const { data, error } = await supabase
    .from("documents")
    .insert({
      original_filename: file.name,
      file_type: file.type,
      file_size: file.size,
      document_type: payload.classification.documentType,
      status,
      confidence: payload.extraction.confidence,
      raw_text: payload.ocr.rawText,
      ocr_markdown: payload.ocr.markdown,
      extracted_data: payload.extraction,
      warnings,
      ocr_engine: payload.ocr.engine,
      ocr_engine_version: payload.ocr.engineVersion,
      ocr_confidence: payload.ocr.confidence,
      layout_confidence: payload.ocr.pages[0]?.confidence ?? payload.ocr.confidence,
      table_count: payload.ocr.pages.reduce((count, page) => count + page.tables.length, 0),
      stamp_detected: /тамга|stamp/i.test(payload.ocr.rawText),
      processing_time_ms: payload.ocr.processingTimeMs,
      fallback_used: payload.ocr.fallbackUsed,
      fallback_reason: payload.ocr.fallbackReason,
      requires_human_review: requiresHumanReview
    })
    .select("*")
    .single();

  if (error) {
    throw new Error(error.message);
  }

  await supabase.from("document_events").insert({
    document_id: data.id,
    event_type: "document_processed",
    event_payload: {
      engine: payload.ocr.engine,
      documentType: payload.classification.documentType
    }
  });

  return mapDatabaseDocument(data as DatabaseDocument);
}

export async function updateSupabaseDocument(id: string, values: { extractedData?: unknown; status?: ReviewStatus }) {
  const supabase = getSupabaseAdminClient();

  if (!supabase) {
    return null;
  }

  const update: Record<string, unknown> = {
    updated_at: new Date().toISOString()
  };

  if (values.extractedData !== undefined) {
    update.extracted_data = values.extractedData;
  }

  if (values.status) {
    update.status = values.status;
  }

  const { data, error } = await supabase.from("documents").update(update).eq("id", id).select("*").single();

  if (error) {
    throw new Error(error.message);
  }

  return mapDatabaseDocument(data as DatabaseDocument);
}

export async function setSupabaseReviewStatus(id: string, status: "approved" | "needs_review") {
  const supabase = getSupabaseAdminClient();

  if (!supabase) {
    return null;
  }

  const { data, error } = await supabase
    .from("documents")
    .update({
      status,
      requires_human_review: status === "needs_review",
      updated_at: new Date().toISOString()
    })
    .eq("id", id)
    .select("*")
    .single();

  if (error) {
    throw new Error(error.message);
  }

  await supabase.from("document_events").insert({
    document_id: id,
    event_type: status === "approved" ? "document_approved" : "document_sent_to_review",
    event_payload: { status }
  });

  if (status === "needs_review") {
    await supabase.from("document_reviews").insert({
      document_id: id,
      review_status: "open",
      notes: "Queued from MVP review action."
    });
  }

  return mapDatabaseDocument(data as DatabaseDocument);
}
