import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatPercent(value?: number | null) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "N/A";
  }

  return `${Math.round(value * 100)}%`;
}

export function formatDateTime(value?: string | Date | null) {
  if (!value) {
    return "N/A";
  }

  return new Intl.DateTimeFormat("en", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}

export function formatBytes(bytes?: number | null) {
  if (!bytes) {
    return "0 B";
  }

  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** index;

  return `${value.toFixed(value >= 10 || index === 0 ? 0 : 1)} ${units[index]}`;
}

export function formatDocumentType(value?: string | null) {
  const labels: Record<string, string> = {
    loan_agreement: "Loan agreement",
    bank_statement: "Bank statement",
    salary_statement: "Salary statement",
    company_certificate: "Company certificate",
    collateral_document: "Collateral document",
    identity_document: "Identity document",
    invoice_receipt: "Invoice / receipt",
    unknown: "Unknown"
  };

  return labels[value ?? ""] ?? "Unknown";
}

export function formatStatus(value?: string | null) {
  const labels: Record<string, string> = {
    pending: "Pending",
    auto_processed: "Auto processed",
    needs_review: "Needs review",
    approved: "Approved",
    rejected: "Rejected"
  };

  return labels[value ?? ""] ?? "Pending";
}
