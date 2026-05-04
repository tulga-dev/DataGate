import {
  DocumentClassificationSchema,
  type DocumentClassification
} from "./schemas";
import type { DocumentType } from "./types";

const rules: Array<{
  documentType: DocumentType;
  keywords: string[];
}> = [
  {
    documentType: "loan_agreement",
    keywords: ["loan", "зээл", "зээлийн гэрээ", "borrower", "lender", "interest", "барьцаа"]
  },
  {
    documentType: "bank_statement",
    keywords: ["statement", "дансны хуулга", "transaction", "balance", "гүйлгээ", "үлдэгдэл"]
  },
  {
    documentType: "salary_statement",
    keywords: ["salary", "цалин", "employer", "employee", "нийгмийн даатгал", "татвар"]
  },
  {
    documentType: "company_certificate",
    keywords: ["company", "llc", "registration", "улсын бүртгэл", "регистр", "гэрчилгээ"]
  },
  {
    documentType: "collateral_document",
    keywords: ["collateral", "барьцаа", "хөрөнгө", "asset", "certificate", "өмчлөгч"]
  },
  {
    documentType: "identity_document",
    keywords: ["identity", "иргэний үнэмлэх", "register number", "регистрийн дугаар", "nationality"]
  },
  {
    documentType: "invoice_receipt",
    keywords: ["invoice", "receipt", "нэхэмжлэх", "баримт", "нөат", "vat", "total"]
  }
];

function detectLanguage(text: string) {
  const cyrillicMatches = text.match(/[А-Яа-яӨөҮүЁё]/g)?.length ?? 0;
  const latinMatches = text.match(/[A-Za-z]/g)?.length ?? 0;

  if (cyrillicMatches > latinMatches * 0.6) {
    return "mn-Cyrl";
  }

  return latinMatches > 0 ? "en" : "unknown";
}

export async function classifyDocument(text: string): Promise<DocumentClassification> {
  const normalized = text.toLowerCase();
  const scores = rules.map((rule) => {
    const hits = rule.keywords.filter((keyword) => normalized.includes(keyword.toLowerCase()));
    return {
      documentType: rule.documentType,
      hits,
      score: hits.length
    };
  });

  const best = scores.sort((a, b) => b.score - a.score)[0];
  const warnings: string[] = [];
  const reasons: string[] = [];

  if (!best || best.score === 0) {
    warnings.push("No strong document-type keywords were detected.");
    reasons.push("Classifier did not find a matching rule.");

    return DocumentClassificationSchema.parse({
      documentType: "unknown",
      confidence: 0.32,
      reasons,
      languageGuess: detectLanguage(text),
      warnings
    });
  }

  reasons.push(`Matched keywords: ${best.hits.join(", ")}`);
  const confidence = Math.min(0.92, 0.48 + best.score * 0.12);

  if (confidence < 0.7) {
    warnings.push("Document type should be verified by a reviewer.");
  }

  return DocumentClassificationSchema.parse({
    documentType: best.documentType,
    confidence,
    reasons,
    languageGuess: detectLanguage(text),
    warnings
  });
}
