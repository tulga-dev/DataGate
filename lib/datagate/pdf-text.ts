export type ClientPdfTextPage = {
  page_number: number;
  raw_text: string;
};

export type ClientPdfTextPayload = {
  filename: string;
  pages: ClientPdfTextPage[];
};

export async function extractPdfTextInBrowser(file: File): Promise<ClientPdfTextPayload> {
  const pdfjs = (await import("pdfjs-dist/legacy/build/pdf.mjs")) as {
    getDocument: (options: { data: Uint8Array; disableWorker?: boolean }) => { promise: Promise<unknown> };
  };

  const bytes = new Uint8Array(await file.arrayBuffer());
  const loadingTask = pdfjs.getDocument({ data: bytes, disableWorker: true });
  const pdf = (await loadingTask.promise) as {
    numPages: number;
    getPage: (pageNumber: number) => Promise<{
      getTextContent: () => Promise<{ items: Array<{ str?: string; transform?: number[] }> }>;
    }>;
  };

  const pages: ClientPdfTextPage[] = [];
  for (let pageNumber = 1; pageNumber <= pdf.numPages; pageNumber += 1) {
    const page = await pdf.getPage(pageNumber);
    const textContent = await page.getTextContent();
    const lines = new Map<number, string[]>();
    for (const item of textContent.items) {
      const text = (item.str ?? "").trim();
      if (!text) continue;
      const y = Math.round(item.transform?.[5] ?? 0);
      const existingKey = Array.from(lines.keys()).find((key) => Math.abs(key - y) <= 3) ?? y;
      const values = lines.get(existingKey) ?? [];
      values.push(text);
      lines.set(existingKey, values);
    }
    const rawText = Array.from(lines.entries())
      .sort((left, right) => right[0] - left[0])
      .map(([, values]) => values.join(" ").replace(/\s+/g, " ").trim())
      .filter(Boolean)
      .join("\n");
    pages.push({ page_number: pageNumber, raw_text: rawText });
  }

  return {
    filename: file.name || "document.pdf",
    pages
  };
}

export function hasReadableClientPdfText(payload: ClientPdfTextPayload): boolean {
  return payload.pages.some((page) => page.raw_text.trim().length >= 80);
}
