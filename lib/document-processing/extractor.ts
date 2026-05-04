import {
  BankStatementFieldsSchema,
  CollateralDocumentFieldsSchema,
  CompanyCertificateFieldsSchema,
  IdentityDocumentFieldsSchema,
  InvoiceReceiptFieldsSchema,
  LoanAgreementFieldsSchema,
  SalaryStatementFieldsSchema,
  StructuredExtractionSchema,
  type DocumentClassification,
  type StructuredExtraction
} from "./schemas";
import type { DocumentType, ProcessingMetadata } from "./types";

function firstMatch(text: string, pattern: RegExp) {
  return text.match(pattern)?.[1]?.trim() ?? null;
}

function amountFrom(value: string | null) {
  if (!value) {
    return null;
  }

  const normalized = value.replace(/[,\s]/g, "");
  const amount = Number(normalized);

  return Number.isFinite(amount) ? amount : null;
}

function firstAmountAfter(text: string, labels: string[]) {
  for (const label of labels) {
    const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const value = firstMatch(text, new RegExp(`${escaped}[^\\d]*(\\d[\\d,\\s]*)\\s*(?:MNT|₮)?`, "i"));
    const amount = amountFrom(value);

    if (amount !== null) {
      return amount;
    }
  }

  return null;
}

function firstDateAfter(text: string, labels: string[]) {
  for (const label of labels) {
    const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const value = firstMatch(text, new RegExp(`${escaped}[^\\d]*(\\d{4}-\\d{2}(?:-\\d{2})?)`, "i"));

    if (value) {
      return value;
    }
  }

  return null;
}

function detectCurrency(text: string) {
  return /\bMNT\b|₮|төгрөг/i.test(text) ? "MNT" : null;
}

function getCriticalWarnings(documentType: DocumentType, fields: Record<string, unknown>) {
  const criticalByType: Partial<Record<DocumentType, string[]>> = {
    loan_agreement: ["borrowerName", "lenderName", "loanAmount", "interestRate"],
    bank_statement: ["accountHolderName", "bankName", "closingBalance"],
    salary_statement: ["employeeName", "employerName", "monthlySalary"],
    company_certificate: ["companyName", "registrationNumber"],
    collateral_document: ["ownerName", "assetType", "estimatedValue"],
    identity_document: ["fullName", "registerNumberMasked"],
    invoice_receipt: ["merchantName", "invoiceNumber", "totalAmount"]
  };

  return (criticalByType[documentType] ?? [])
    .filter((key) => fields[key] === null || fields[key] === undefined || fields[key] === "")
    .map((key) => `Missing critical field: ${key}`);
}

function buildFields(text: string, documentType: DocumentType) {
  const borrower = firstMatch(text, /Borrower[^:]*:\s*([^\n/]+(?:\/\s*[^\n]+)?)/i);
  const batErdene = /Бат-Эрдэнэ Болд|Bat-Erdene Bold/i.test(text) ? "Бат-Эрдэнэ Болд / Bat-Erdene Bold" : borrower;
  const altanTrade = /Altan Trade LLC/i.test(text) ? "Altan Trade LLC" : null;
  const khanBank = /Khan Bank/i.test(text) ? "Khan Bank" : null;
  const currency = detectCurrency(text);

  switch (documentType) {
    case "loan_agreement":
      return LoanAgreementFieldsSchema.parse({
        borrowerName: batErdene,
        lenderName: khanBank ?? firstMatch(text, /Lender[^:]*:\s*([^\n]+)/i),
        loanAmount: firstAmountAfter(text, ["Loan amount", "Зээлийн дүн"]),
        currency,
        interestRate: firstMatch(text, /(?:Interest rate|Хүү)[^:]*:\s*([^\n]+)/i),
        termMonths: amountFrom(firstMatch(text, /(?:Term|Хугацаа)[^:]*:\s*(\d+)/i)),
        startDate: firstDateAfter(text, ["Start date"]),
        maturityDate: firstDateAfter(text, ["Maturity date"]),
        collateralDescription: firstMatch(text, /(?:Collateral|Барьцаа)[^:]*:\s*([^\n]+)/i),
        repaymentSchedule: firstMatch(text, /Repayment schedule:\s*([^\n]+)/i),
        signaturesDetected: /signatures detected:\s*yes/i.test(text)
      });
    case "bank_statement":
      return BankStatementFieldsSchema.parse({
        accountHolderName: firstMatch(text, /Account holder:\s*([^\n]+)/i) ?? batErdene,
        bankName: firstMatch(text, /Bank name:\s*([^\n]+)/i) ?? khanBank,
        accountNumberMasked: firstMatch(text, /Account number:\s*([*\d\s]+)/i),
        statementPeriodStart: firstDateAfter(text, ["Statement period"]),
        statementPeriodEnd: firstMatch(text, /Statement period:\s*\d{4}-\d{2}-\d{2}\s*to\s*(\d{4}-\d{2}-\d{2})/i),
        openingBalance: firstAmountAfter(text, ["Opening balance"]),
        closingBalance: firstAmountAfter(text, ["Closing balance"]),
        totalIncome: firstAmountAfter(text, ["Total income"]),
        totalExpense: firstAmountAfter(text, ["Total expense"]),
        transactionCount: amountFrom(firstMatch(text, /Transaction count:\s*(\d+)/i)),
        suspiciousTransactions: []
      });
    case "salary_statement":
      return SalaryStatementFieldsSchema.parse({
        employeeName: firstMatch(text, /Employee:\s*([^\n]+)/i) ?? batErdene,
        employerName: firstMatch(text, /Employer:\s*([^\n]+)/i) ?? altanTrade,
        monthlySalary: firstAmountAfter(text, ["Monthly salary"]),
        currency,
        statementMonth: firstDateAfter(text, ["Statement month"]),
        socialInsurancePaid: firstAmountAfter(text, ["Social insurance paid"]),
        taxPaid: firstAmountAfter(text, ["Tax paid"])
      });
    case "company_certificate":
      return CompanyCertificateFieldsSchema.parse({
        companyName: altanTrade,
        registrationNumber: firstMatch(text, /(?:registration|регистр)[^:\n]*:\s*([A-Z0-9-]+)/i),
        registerDate: firstDateAfter(text, ["Register date", "registration date"]),
        legalAddress: firstMatch(text, /Legal address:\s*([^\n]+)/i),
        directorName: firstMatch(text, /Director:\s*([^\n]+)/i),
        businessActivity: firstMatch(text, /Business activity:\s*([^\n]+)/i)
      });
    case "collateral_document":
      return CollateralDocumentFieldsSchema.parse({
        ownerName: batErdene,
        assetType: /Toyota|apartment/i.test(text) ? "Vehicle / apartment" : null,
        assetDescription: firstMatch(text, /(?:Collateral|Барьцаа)[^:]*:\s*([^\n]+)/i),
        estimatedValue: firstAmountAfter(text, ["Estimated value", "Value"]),
        currency,
        certificateNumber: firstMatch(text, /(UB-\d{4}-\d+)/i),
        registrationNumber: firstMatch(text, /registration number:\s*([A-Z0-9-]+)/i)
      });
    case "identity_document":
      return IdentityDocumentFieldsSchema.parse({
        fullName: batErdene,
        registerNumberMasked: firstMatch(text, /register number:\s*([A-ZА-ЯӨҮЁ0-9*]+)/i),
        documentNumberMasked: firstMatch(text, /document number:\s*([A-Z0-9*]+)/i),
        dateOfBirth: firstDateAfter(text, ["Date of birth"]),
        nationality: firstMatch(text, /Nationality:\s*([^\n]+)/i) ?? "Mongolian",
        expiryDate: firstDateAfter(text, ["Expiry date"])
      });
    case "invoice_receipt":
      return InvoiceReceiptFieldsSchema.parse({
        merchantName: firstMatch(text, /Merchant:\s*([^\n]+)/i) ?? altanTrade,
        buyerName: firstMatch(text, /Buyer:\s*([^\n]+)/i) ?? batErdene,
        invoiceNumber: firstMatch(text, /Invoice number:\s*([A-Z0-9-]+)/i),
        invoiceDate: firstDateAfter(text, ["Invoice date"]),
        totalAmount: firstAmountAfter(text, ["Invoice total", "total"]),
        vatAmount: firstAmountAfter(text, ["VAT", "НӨАТ"]),
        currency,
        lineItems: [
          {
            description: "Mock financial service invoice line",
            quantity: 1,
            amount: firstAmountAfter(text, ["Invoice total"])
          }
        ]
      });
    default:
      return {};
  }
}

export async function extractStructuredFields(
  text: string,
  classification: DocumentClassification,
  metadata: ProcessingMetadata
): Promise<StructuredExtraction> {
  const fields = buildFields(text, classification.documentType);
  const warnings = [
    ...classification.warnings,
    ...getCriticalWarnings(classification.documentType, fields)
  ];
  const confidencePenalty = warnings.length > 0 ? 0.08 : 0;

  return StructuredExtractionSchema.parse({
    documentType: classification.documentType,
    originalFilename: metadata.originalFilename,
    detectedLanguage: classification.languageGuess,
    rawText: text,
    markdown: metadata.markdown,
    confidence: Math.max(0.1, Math.min(classification.confidence, metadata.confidence) - confidencePenalty),
    extractedAt: new Date().toISOString(),
    fields,
    warnings
  });
}
