export const documentTypes = [
  "loan_agreement",
  "bank_statement",
  "salary_statement",
  "company_certificate",
  "collateral_document",
  "identity_document",
  "invoice_receipt",
  "unknown"
] as const;

export const reviewStatuses = [
  "pending",
  "auto_processed",
  "needs_review",
  "approved",
  "rejected"
] as const;

export const ocrEngines = ["glm_ocr", "paddleocr", "surya", "mock"] as const;

export type DocumentType = (typeof documentTypes)[number];
export type ReviewStatus = (typeof reviewStatuses)[number];
export type OcrEngine = (typeof ocrEngines)[number];

export type OcrOptions = {
  preferredEngine?: OcrEngine;
  fallbackEngine?: Exclude<OcrEngine, "glm_ocr">;
  forceMock?: boolean;
};

export type DocumentRecord = {
  id: string;
  originalFilename: string;
  fileType: string | null;
  fileSize: number | null;
  storagePath: string | null;
  documentType: DocumentType;
  status: ReviewStatus;
  confidence: number;
  rawText: string;
  ocrMarkdown?: string | null;
  extractedData: unknown;
  warnings: string[];
  ocrEngine: OcrEngine | string;
  ocrEngineVersion?: string | null;
  ocrConfidence: number;
  layoutConfidence?: number | null;
  tableCount: number;
  stampDetected: boolean;
  processingTimeMs: number;
  fallbackUsed: boolean;
  fallbackReason?: string | null;
  requiresHumanReview: boolean;
  createdAt: string;
  updatedAt: string;
};

export type DocumentStats = {
  documentsProcessed: number;
  averageOcrConfidence: number;
  needsHumanReview: number;
  approvedDocuments: number;
  typeDistribution: Array<{
    documentType: DocumentType;
    count: number;
  }>;
};

export type ProcessingMetadata = {
  originalFilename: string;
  ocrEngine: string;
  ocrEngineVersion?: string | null;
  markdown?: string | null;
  confidence: number;
};
