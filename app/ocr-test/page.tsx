import Link from "next/link";
import { OcrTestConsole } from "@/components/datagate/OcrTestConsole";

export default function OcrTestPage() {
  return (
    <main className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <header className="border-b border-slate-200 pb-6">
        <Link href="/" className="text-sm font-medium text-blue-700 hover:text-blue-900">
          DataGate
        </Link>
        <h1 className="mt-2 text-3xl font-semibold tracking-normal text-slate-950">OCR test console</h1>
        <p className="mt-2 max-w-2xl text-sm text-slate-500">
          Test a real document against PaddleOCR, mock OCR, or an advanced adapter and inspect the exact OCR response.
        </p>
      </header>
      <div className="mt-8">
        <OcrTestConsole />
      </div>
    </main>
  );
}
