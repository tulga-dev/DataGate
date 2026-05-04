import { randomUUID } from "crypto";
import { createMockOcrResult } from "@/lib/document-processing/ocr";
import type { ProcessedDocumentPayload } from "@/lib/document-processing/router";
import type { DocumentRecord, DocumentStats, DocumentType, ReviewStatus } from "@/lib/document-processing/types";

function now(offsetMinutes = 0) {
  return new Date(Date.now() - offsetMinutes * 60_000).toISOString();
}

function createDemoDocument(
  id: string,
  originalFilename: string,
  documentType: DocumentType,
  status: ReviewStatus,
  confidence: number,
  fields: Record<string, unknown>,
  warnings: string[] = []
): DocumentRecord {
  const ocr = createMockOcrResult("mock");

  return {
    id,
    originalFilename,
    fileType: "application/pdf",
    fileSize: 1_240_000,
    storagePath: null,
    documentType,
    status,
    confidence,
    rawText: ocr.rawText,
    ocrMarkdown: ocr.markdown,
    extractedData: {
      documentType,
      originalFilename,
      detectedLanguage: "mn-Cyrl",
      rawText: ocr.rawText,
      markdown: ocr.markdown,
      confidence,
      extractedAt: now(30),
      fields,
      warnings
    },
    warnings,
    ocrEngine: "mock",
    ocrEngineVersion: "mock-0.1.0",
    ocrConfidence: 0.91,
    layoutConfidence: 0.88,
    tableCount: documentType === "bank_statement" ? 1 : 0,
    stampDetected: documentType === "loan_agreement",
    processingTimeMs: 180,
    fallbackUsed: false,
    fallbackReason: null,
    requiresHumanReview: status === "needs_review",
    createdAt: now(Math.floor(Math.random() * 300)),
    updatedAt: now(Math.floor(Math.random() * 60))
  };
}

const documents = new Map<string, DocumentRecord>();
const events: Array<{ documentId: string; eventType: string; payload: unknown; createdAt: string }> = [];

function seedDemoDocuments() {
  if (documents.size > 0) {
    return;
  }

  [
    createDemoDocument("demo-loan-001", "bat-erdene-loan-agreement.pdf", "loan_agreement", "auto_processed", 0.86, {
      borrowerName: "Бат-Эрдэнэ Болд / Bat-Erdene Bold",
      lenderName: "Khan Bank",
      loanAmount: 50_000_000,
      currency: "MNT",
      interestRate: "2.2% monthly",
      termMonths: 24,
      startDate: "2026-01-15",
      maturityDate: "2028-01-15",
      collateralDescription: "Toyota Land Cruiser 2021, apartment certificate UB-2024-1188",
      repaymentSchedule: "monthly equal payments",
      signaturesDetected: true
    }),
    createDemoDocument("demo-bank-001", "khan-bank-statement-january.pdf", "bank_statement", "needs_review", 0.73, {
      accountHolderName: "Bat-Erdene Bold",
      bankName: "Khan Bank",
      accountNumberMasked: "**** **** 1290",
      statementPeriodStart: "2026-01-01",
      statementPeriodEnd: "2026-01-31",
      openingBalance: 2_150_000,
      closingBalance: 4_375_000,
      totalIncome: 6_800_000,
      totalExpense: 4_575_000,
      transactionCount: 38,
      suspiciousTransactions: []
    }, ["Low table confidence on transaction section."]),
    createDemoDocument("demo-salary-001", "altan-trade-salary-statement.pdf", "salary_statement", "approved", 0.89, {
      employeeName: "Bat-Erdene Bold",
      employerName: "Altan Trade LLC",
      monthlySalary: 3_500_000,
      currency: "MNT",
      statementMonth: "2026-01",
      socialInsurancePaid: 420_000,
      taxPaid: 350_000
    }),
    createDemoDocument("demo-invoice-001", "altan-trade-invoice-0042.pdf", "invoice_receipt", "auto_processed", 0.84, {
      merchantName: "Altan Trade LLC",
      buyerName: "Bat-Erdene Bold",
      invoiceNumber: "INV-2026-0042",
      invoiceDate: "2026-01-20",
      totalAmount: 1_250_000,
      vatAmount: 125_000,
      currency: "MNT",
      lineItems: [{ description: "Mock financial service invoice line", quantity: 1, amount: 1_250_000 }]
    })
  ].forEach((document) => documents.set(document.id, document));
}

seedDemoDocuments();

export async function listMockDocuments() {
  seedDemoDocuments();
  return Array.from(documents.values()).sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
  );
}

export async function getMockDocument(id: string) {
  seedDemoDocuments();
  return documents.get(id) ?? null;
}

export async function saveMockProcessedDocument(file: File, payload: ProcessedDocumentPayload) {
  const id = randomUUID();
  const warnings = Array.from(new Set([...payload.ocr.warnings, ...payload.extraction.warnings]));
  const requiresHumanReview = warnings.length > 0 || payload.extraction.confidence < 0.78;
  const status: ReviewStatus = requiresHumanReview ? "needs_review" : "auto_processed";
  const createdAt = new Date().toISOString();

  const record: DocumentRecord = {
    id,
    originalFilename: file.name,
    fileType: file.type,
    fileSize: file.size,
    storagePath: null,
    documentType: payload.classification.documentType,
    status,
    confidence: payload.extraction.confidence,
    rawText: payload.ocr.rawText,
    ocrMarkdown: payload.ocr.markdown,
    extractedData: payload.extraction,
    warnings,
    ocrEngine: payload.ocr.engine,
    ocrEngineVersion: payload.ocr.engineVersion ?? null,
    ocrConfidence: payload.ocr.confidence,
    layoutConfidence: payload.ocr.pages[0]?.confidence ?? null,
    tableCount: payload.ocr.pages.reduce((count, page) => count + page.tables.length, 0),
    stampDetected: /тамга|stamp/i.test(payload.ocr.rawText),
    processingTimeMs: payload.ocr.processingTimeMs,
    fallbackUsed: payload.ocr.fallbackUsed,
    fallbackReason: payload.ocr.fallbackReason ?? null,
    requiresHumanReview,
    createdAt,
    updatedAt: createdAt
  };

  documents.set(id, record);
  events.push({
    documentId: id,
    eventType: "document_processed",
    payload: { engine: payload.ocr.engine, documentType: payload.classification.documentType },
    createdAt
  });

  return record;
}

export async function updateMockDocument(id: string, values: { extractedData?: unknown; status?: ReviewStatus }) {
  const existing = documents.get(id);

  if (!existing) {
    return null;
  }

  const updated: DocumentRecord = {
    ...existing,
    extractedData: values.extractedData ?? existing.extractedData,
    status: values.status ?? existing.status,
    updatedAt: new Date().toISOString()
  };

  documents.set(id, updated);
  events.push({
    documentId: id,
    eventType: "document_updated",
    payload: values,
    createdAt: updated.updatedAt
  });

  return updated;
}

export async function setMockReviewStatus(id: string, status: "approved" | "needs_review") {
  const existing = documents.get(id);

  if (!existing) {
    return null;
  }

  const updated: DocumentRecord = {
    ...existing,
    status,
    requiresHumanReview: status === "needs_review",
    updatedAt: new Date().toISOString()
  };

  documents.set(id, updated);
  events.push({
    documentId: id,
    eventType: status === "approved" ? "document_approved" : "document_sent_to_review",
    payload: { status },
    createdAt: updated.updatedAt
  });

  return updated;
}

export async function getMockStats(): Promise<DocumentStats> {
  const all = await listMockDocuments();
  const typeCounts = new Map<DocumentType, number>();

  for (const document of all) {
    typeCounts.set(document.documentType, (typeCounts.get(document.documentType) ?? 0) + 1);
  }

  return {
    documentsProcessed: all.length,
    averageOcrConfidence: all.reduce((sum, document) => sum + document.ocrConfidence, 0) / Math.max(all.length, 1),
    needsHumanReview: all.filter((document) => document.status === "needs_review").length,
    approvedDocuments: all.filter((document) => document.status === "approved").length,
    typeDistribution: Array.from(typeCounts.entries()).map(([documentType, count]) => ({
      documentType,
      count
    }))
  };
}
