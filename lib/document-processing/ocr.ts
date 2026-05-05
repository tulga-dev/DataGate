import { OcrResultSchema, type OcrResult } from "./schemas";
import type { DocumentType, OcrEngine, OcrOptions } from "./types";

const mockRawText = `DATA GATE MOCK OCR
ЗЭЭЛИЙН ГЭРЭЭ / Loan Agreement
Borrower / Зээлдэгч: Бат-Эрдэнэ Болд / Bat-Erdene Bold
Lender / Зээлдүүлэгч: Khan Bank
Company: Altan Trade LLC
Loan amount / Зээлийн дүн: 50,000,000 MNT
Interest rate / Хүү: 2.2% monthly
Term / Хугацаа: 24 months
Start date: 2026-01-15
Maturity date: 2028-01-15
Collateral / Барьцаа: Toyota Land Cruiser 2021, apartment certificate UB-2024-1188
Repayment schedule: monthly equal payments
Signatures detected: yes

ДАНСНЫ ХУУЛГА / Bank Statement
Account holder: Bat-Erdene Bold
Bank name: Khan Bank
Account number: **** **** 1290
Statement period: 2026-01-01 to 2026-01-31
Opening balance: 2,150,000 MNT
Closing balance: 4,375,000 MNT
Total income: 6,800,000 MNT
Total expense: 4,575,000 MNT
Transaction count: 38

ЦАЛИНГИЙН ТОДОРХОЙЛОЛТ / Salary Statement
Employee: Bat-Erdene Bold
Employer: Altan Trade LLC
Monthly salary: 3,500,000 MNT
Statement month: 2026-01
Social insurance paid: 420,000 MNT
Tax paid: 350,000 MNT

НЭХЭМЖЛЭХ / Invoice
Merchant: Altan Trade LLC
Buyer: Bat-Erdene Bold
Invoice number: INV-2026-0042
Invoice date: 2026-01-20
Invoice total: 1,250,000 MNT
VAT / НӨАТ: 125,000 MNT`;

export function createMockOcrResult(
  engine: OcrEngine = "mock",
  fallbackUsed = false,
  fallbackReason?: string
): OcrResult {
  const markdown = `# Mock Mongolian Financial Document\n\n${mockRawText}`;

  return OcrResultSchema.parse({
    engine,
    engineVersion: engine === "mock" ? "mock-0.1.0" : "placeholder",
    rawText: mockRawText,
    markdown,
    pages: [
      {
        pageNumber: 1,
        text: mockRawText,
        markdown,
        blocks: [],
        tables: [],
        confidence: 0.91
      }
    ],
    languageGuess: "mn-Cyrl",
    confidence: 0.91,
    warnings: fallbackReason ? [fallbackReason] : [],
    processingTimeMs: 180,
    fallbackUsed,
    fallbackReason
  });
}

function normalizeEngine(value?: string | null): OcrEngine {
  if (value === "glm_ocr" || value === "paddleocr" || value === "surya" || value === "mock") {
    return value;
  }

  return "mock";
}

export async function extractTextFromDocument(
  file: File,
  options: OcrOptions & { requestedDocumentType?: DocumentType | "auto" } = {}
): Promise<OcrResult> {
  const serviceUrl = process.env.OCR_SERVICE_URL;
  const preferredEngine = options.forceMock ? "mock" : options.preferredEngine ?? (serviceUrl ? "paddleocr" : "mock");
  const fallbackEngine = options.fallbackEngine ?? "mock";

  if (!serviceUrl || options.forceMock || preferredEngine === "mock") {
    const fallbackReason =
      preferredEngine !== "mock" && !serviceUrl ? "OCR_SERVICE_URL is not configured; using mock OCR." : undefined;
    return createMockOcrResult("mock", Boolean(fallbackReason), fallbackReason);
  }

  try {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("engine", preferredEngine);
    formData.append("fallback_engine", fallbackEngine);
    formData.append("document_type", options.requestedDocumentType && options.requestedDocumentType !== "auto" ? options.requestedDocumentType : "unknown");

    const response = await fetch(`${serviceUrl.replace(/\/$/, "")}/ocr/extract`, {
      method: "POST",
      body: formData
    });

    if (!response.ok) {
      throw new Error(`OCR service returned ${response.status}`);
    }

    const parsed = OcrResultSchema.parse(await response.json());
    return parsed;
  } catch (error) {
    const reason = error instanceof Error ? error.message : "OCR service failed.";
    return createMockOcrResult(normalizeEngine(fallbackEngine), true, `OCR service failed: ${reason}. Used mock-compatible fallback.`);
  }
}
