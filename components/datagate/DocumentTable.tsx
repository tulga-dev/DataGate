import Link from "next/link";
import type { DocumentRecord } from "@/lib/document-processing/types";
import { formatDateTime, formatDocumentType } from "@/lib/utils/format";
import { ConfidenceBadge } from "./ConfidenceBadge";
import { StatusBadge } from "./StatusBadge";

export function DocumentTable({ documents }: { documents: DocumentRecord[] }) {
  if (documents.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">
        No documents processed yet.
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-md border border-slate-200 bg-white shadow-soft">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50">
            <tr className="text-left text-xs font-semibold uppercase tracking-normal text-slate-500">
              <th className="px-4 py-3">Document</th>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Confidence</th>
              <th className="px-4 py-3">Created</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {documents.map((document) => (
              <tr key={document.id} className="hover:bg-slate-50">
                <td className="px-4 py-3">
                  <Link href={`/documents/${document.id}`} className="font-medium text-slate-950 hover:text-blue-700">
                    {document.originalFilename}
                  </Link>
                </td>
                <td className="px-4 py-3 text-slate-600">{formatDocumentType(document.documentType)}</td>
                <td className="px-4 py-3">
                  <StatusBadge status={document.status} />
                </td>
                <td className="px-4 py-3">
                  <ConfidenceBadge value={document.confidence} />
                </td>
                <td className="px-4 py-3 text-slate-500">{formatDateTime(document.createdAt)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
