import Link from "next/link";
import { DocumentUpload } from "@/components/datagate/DocumentUpload";

export default function UploadPage() {
  return (
    <main className="mx-auto w-full max-w-3xl px-4 py-8 sm:px-6 lg:px-8">
      <header className="border-b border-slate-200 pb-6">
        <Link href="/" className="text-sm font-medium text-blue-700 hover:text-blue-900">
          DataGate
        </Link>
        <h1 className="mt-2 text-3xl font-semibold tracking-normal text-slate-950">Upload document</h1>
        <p className="mt-2 text-sm text-slate-500">Run OCR, classify the document, and extract structured fields.</p>
      </header>
      <div className="mt-8">
        <DocumentUpload />
      </div>
    </main>
  );
}
