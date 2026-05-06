import type { FullPipelineResponse } from "@/lib/datagate/types";
import { extractPdfTextInBrowser, hasReadableClientPdfText } from "@/lib/datagate/pdf-text";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  process.env.VITE_API_BASE_URL ||
  (typeof window !== "undefined" && window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1"
    ? ""
    : "http://localhost:8000");
const VERCEL_SAFE_UPLOAD_BYTES = 3.8 * 1024 * 1024;

async function upload<T>(endpoint: string, file: File, borrowerMetadata?: Record<string, unknown>): Promise<T> {
  const formData = new FormData();
  formData.append("file", file);
  if (borrowerMetadata && Object.keys(borrowerMetadata).length > 0) {
    formData.append("borrower_metadata", JSON.stringify(borrowerMetadata));
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: "POST",
      body: formData
    });
  } catch (error) {
    throw new Error(
      error instanceof Error
        ? `Backend unreachable at ${API_BASE_URL}. ${error.message}`
        : `Backend unreachable at ${API_BASE_URL}.`
    );
  }

  const text = await response.text();
  let payload: Record<string, unknown> = {};
  try {
    payload = text ? (JSON.parse(text) as Record<string, unknown>) : {};
  } catch {
    payload = { message: text || "Backend returned a non-JSON response." };
  }
  if (!response.ok) {
    const detail = payload.detail;
    const message = payload.message;
    throw new Error(
      typeof detail === "string"
        ? detail
        : typeof message === "string"
          ? message
          : `Request failed with status ${response.status}.`
    );
  }
  return payload as T;
}

async function postJson<T>(endpoint: string, body: Record<string, unknown>): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
  } catch (error) {
    throw new Error(
      error instanceof Error
        ? `Backend unreachable at ${API_BASE_URL || "current site"}. ${error.message}`
        : `Backend unreachable at ${API_BASE_URL || "current site"}.`
    );
  }

  const text = await response.text();
  let payload: Record<string, unknown> = {};
  try {
    payload = text ? (JSON.parse(text) as Record<string, unknown>) : {};
  } catch {
    payload = { message: text || "Backend returned a non-JSON response." };
  }
  if (!response.ok) {
    const detail = payload.detail;
    const message = payload.message;
    throw new Error(
      typeof detail === "string"
        ? detail
        : typeof message === "string"
          ? message
          : `Request failed with status ${response.status}.`
    );
  }
  return payload as T;
}

function isDeployedBrowser() {
  return (
    typeof window !== "undefined" &&
    window.location.hostname !== "localhost" &&
    window.location.hostname !== "127.0.0.1"
  );
}

function isPdf(file: File) {
  return file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
}

async function textPipeline<T>(
  endpoint: string,
  file: File,
  borrowerMetadata?: Record<string, unknown>
): Promise<T> {
  const extracted = await extractPdfTextInBrowser(file);
  if (!hasReadableClientPdfText(extracted)) {
    throw new Error(
      "This PDF is too large for direct online upload and does not contain enough embedded text. It is likely scanned; the next storage-upload OCR path is required for this file."
    );
  }
  return postJson<T>(endpoint, {
    filename: extracted.filename,
    pages: extracted.pages,
    document_type: "unknown",
    borrower_metadata: borrowerMetadata ?? {}
  });
}

async function uploadOrTextPipeline<T>(
  binaryEndpoint: string,
  textEndpoint: string,
  file: File,
  borrowerMetadata?: Record<string, unknown>
): Promise<T> {
  if (isDeployedBrowser() && file.size > VERCEL_SAFE_UPLOAD_BYTES) {
    if (!isPdf(file)) {
      throw new Error("This file is too large for online upload. Use a PDF with embedded text or the local backend for large images.");
    }
    return textPipeline<T>(textEndpoint, file, borrowerMetadata);
  }
  return upload<T>(binaryEndpoint, file, borrowerMetadata);
}

export function getDataGateApiBaseUrl() {
  return API_BASE_URL;
}

export function parseDocument(file: File) {
  return uploadOrTextPipeline<FullPipelineResponse>("/documents/parse", "/documents/parse-text", file);
}

export function analyzeFinancials(file: File) {
  return uploadOrTextPipeline<FullPipelineResponse>(
    "/documents/analyze-financials",
    "/documents/analyze-financials-text",
    file
  );
}

export function generateCreditMemo(file: File, borrowerMetadata?: Record<string, unknown>) {
  return uploadOrTextPipeline<FullPipelineResponse>(
    "/documents/generate-credit-memo",
    "/documents/generate-credit-memo-text",
    file,
    borrowerMetadata
  );
}

export function runFullPipeline(file: File, borrowerMetadata?: Record<string, unknown>) {
  return uploadOrTextPipeline<FullPipelineResponse>(
    "/documents/full-pipeline",
    "/documents/full-pipeline-text",
    file,
    borrowerMetadata
  );
}
