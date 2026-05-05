import { z } from "zod";
import { documentTypes, ocrEngines } from "./types";

const nullableString = z.string().nullable();
const nullableNumber = z.number().nullable();
const nullableBoolean = z.boolean().nullable();

export const DocumentClassificationSchema = z.object({
  documentType: z.enum(documentTypes),
  confidence: z.number().min(0).max(1),
  reasons: z.array(z.string()),
  languageGuess: z.string(),
  warnings: z.array(z.string())
});

export const OcrPageSchema = z.object({
  pageNumber: z.number().int().positive(),
  text: z.string(),
  markdown: z.string().nullable().optional(),
  blocks: z.array(z.unknown()),
  tables: z.array(z.unknown()),
  confidence: z.number().min(0).max(1),
  warnings: z.array(z.string()).optional(),
  strategy: z.enum(["digital", "ocr", "hybrid", "failed"]).nullable().optional(),
  metadata: z
    .object({
      text_char_count: z.number().optional(),
      word_count: z.number().optional(),
      table_candidate_count: z.number().optional(),
      image_area_ratio: z.number().optional(),
      extraction_confidence: z.number().optional(),
      selected_strategy: z.string().optional()
    })
    .passthrough()
    .nullable()
    .optional()
});

export const OcrResultSchema = z.object({
  engine: z.enum(ocrEngines),
  engineVersion: z.string().nullable().optional(),
  rawText: z.string(),
  markdown: z.string().nullable().optional(),
  pages: z.array(OcrPageSchema),
  languageGuess: z.string(),
  confidence: z.number().min(0).max(1),
  warnings: z.array(z.string()),
  processingTimeMs: z.number().int().nonnegative(),
  fallbackUsed: z.boolean(),
  fallbackReason: z.string().nullable().optional(),
  parserResult: z.unknown().optional(),
  parserVersion: z.string().nullable().optional(),
  financialExtraction: z.unknown().optional()
});

export const BaseExtractionSchema = z.object({
  documentType: z.enum(documentTypes),
  originalFilename: z.string(),
  detectedLanguage: z.string(),
  rawText: z.string(),
  markdown: z.string().nullable().optional(),
  confidence: z.number().min(0).max(1),
  extractedAt: z.string(),
  fields: z.record(z.unknown()),
  warnings: z.array(z.string())
});

export const LoanAgreementFieldsSchema = z.object({
  borrowerName: nullableString,
  lenderName: nullableString,
  loanAmount: nullableNumber,
  currency: nullableString,
  interestRate: nullableString,
  termMonths: nullableNumber,
  startDate: nullableString,
  maturityDate: nullableString,
  collateralDescription: nullableString,
  repaymentSchedule: nullableString,
  signaturesDetected: nullableBoolean
});

export const BankStatementFieldsSchema = z.object({
  accountHolderName: nullableString,
  bankName: nullableString,
  accountNumberMasked: nullableString,
  statementPeriodStart: nullableString,
  statementPeriodEnd: nullableString,
  openingBalance: nullableNumber,
  closingBalance: nullableNumber,
  totalIncome: nullableNumber,
  totalExpense: nullableNumber,
  transactionCount: nullableNumber,
  suspiciousTransactions: z.array(z.string())
});

export const SalaryStatementFieldsSchema = z.object({
  employeeName: nullableString,
  employerName: nullableString,
  monthlySalary: nullableNumber,
  currency: nullableString,
  statementMonth: nullableString,
  socialInsurancePaid: nullableNumber,
  taxPaid: nullableNumber
});

export const CompanyCertificateFieldsSchema = z.object({
  companyName: nullableString,
  registrationNumber: nullableString,
  registerDate: nullableString,
  legalAddress: nullableString,
  directorName: nullableString,
  businessActivity: nullableString
});

export const CollateralDocumentFieldsSchema = z.object({
  ownerName: nullableString,
  assetType: nullableString,
  assetDescription: nullableString,
  estimatedValue: nullableNumber,
  currency: nullableString,
  certificateNumber: nullableString,
  registrationNumber: nullableString
});

export const IdentityDocumentFieldsSchema = z.object({
  fullName: nullableString,
  registerNumberMasked: nullableString,
  documentNumberMasked: nullableString,
  dateOfBirth: nullableString,
  nationality: nullableString,
  expiryDate: nullableString
});

export const InvoiceReceiptFieldsSchema = z.object({
  merchantName: nullableString,
  buyerName: nullableString,
  invoiceNumber: nullableString,
  invoiceDate: nullableString,
  totalAmount: nullableNumber,
  vatAmount: nullableNumber,
  currency: nullableString,
  lineItems: z.array(
    z.object({
      description: z.string(),
      quantity: z.number().nullable(),
      amount: z.number().nullable()
    })
  )
});

export const StructuredExtractionSchema = BaseExtractionSchema;

export type DocumentClassification = z.infer<typeof DocumentClassificationSchema>;
export type OcrPage = z.infer<typeof OcrPageSchema>;
export type OcrResult = z.infer<typeof OcrResultSchema>;
export type StructuredExtraction = z.infer<typeof StructuredExtractionSchema>;
