import { classifyDocument } from "./classifier";
import { extractStructuredFields } from "./extractor";
import { extractTextFromDocument } from "./ocr";
import type { DocumentClassification, OcrResult, StructuredExtraction } from "./schemas";
import type { DocumentType, OcrOptions } from "./types";

export type ProcessedDocumentPayload = {
  ocr: OcrResult;
  classification: DocumentClassification;
  extraction: StructuredExtraction;
};

export async function processDocumentFile(
  file: File,
  options: OcrOptions & { requestedDocumentType?: DocumentType | "auto" } = {}
): Promise<ProcessedDocumentPayload> {
  const ocr = await extractTextFromDocument(file, options);
  const inferredClassification = await classifyDocument(ocr.rawText);
  const classification =
    options.requestedDocumentType && options.requestedDocumentType !== "auto"
      ? {
          ...inferredClassification,
          documentType: options.requestedDocumentType,
          reasons: [
            `User selected document type: ${options.requestedDocumentType}`,
            ...inferredClassification.reasons
          ],
          warnings:
            inferredClassification.documentType !== options.requestedDocumentType
              ? [
                  `Auto-detected ${inferredClassification.documentType}, but user selected ${options.requestedDocumentType}.`,
                  ...inferredClassification.warnings
                ]
              : inferredClassification.warnings
        }
      : inferredClassification;
  const extraction = await extractStructuredFields(ocr.rawText, classification, {
    originalFilename: file.name,
    ocrEngine: ocr.engine,
    ocrEngineVersion: ocr.engineVersion,
    markdown: ocr.markdown,
    confidence: ocr.confidence
  });

  return {
    ocr,
    classification,
    extraction
  };
}
