import type { FullPipelineResponse } from "@/lib/datagate/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  process.env.VITE_API_BASE_URL ||
  (typeof window !== "undefined" && window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1"
    ? ""
    : "http://localhost:8000");

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

export function getDataGateApiBaseUrl() {
  return API_BASE_URL;
}

export function parseDocument(file: File) {
  return upload<FullPipelineResponse>("/documents/parse", file);
}

export function analyzeFinancials(file: File) {
  return upload<FullPipelineResponse>("/documents/analyze-financials", file);
}

export function generateCreditMemo(file: File, borrowerMetadata?: Record<string, unknown>) {
  return upload<FullPipelineResponse>("/documents/generate-credit-memo", file, borrowerMetadata);
}

export function runFullPipeline(file: File, borrowerMetadata?: Record<string, unknown>) {
  return upload<FullPipelineResponse>("/documents/full-pipeline", file, borrowerMetadata);
}
