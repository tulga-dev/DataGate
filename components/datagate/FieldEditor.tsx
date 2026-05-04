"use client";

import { Save } from "lucide-react";
import { useMemo, useState } from "react";

type FieldValue = string | number | boolean | null | Array<unknown> | Record<string, unknown>;

function stringifyValue(value: FieldValue) {
  if (value === null || value === undefined) {
    return "";
  }

  if (typeof value === "object") {
    return JSON.stringify(value, null, 2);
  }

  return String(value);
}

function parseValue(original: FieldValue, value: string) {
  if (value.trim() === "") {
    return null;
  }

  if (typeof original === "number") {
    const number = Number(value.replace(/,/g, ""));
    return Number.isFinite(number) ? number : original;
  }

  if (typeof original === "boolean") {
    return value.toLowerCase() === "true" || value.toLowerCase() === "yes";
  }

  if (Array.isArray(original) || (original && typeof original === "object")) {
    try {
      return JSON.parse(value);
    } catch {
      return original;
    }
  }

  return value;
}

export function FieldEditor({
  fields,
  onSave
}: {
  fields: Record<string, FieldValue>;
  onSave: (fields: Record<string, unknown>) => Promise<void>;
}) {
  const initial = useMemo(
    () => Object.fromEntries(Object.entries(fields).map(([key, value]) => [key, stringifyValue(value)])),
    [fields]
  );
  const [values, setValues] = useState<Record<string, string>>(initial);
  const [saving, setSaving] = useState(false);

  async function handleSave() {
    setSaving(true);
    const nextFields = Object.fromEntries(
      Object.entries(values).map(([key, value]) => [key, parseValue(fields[key], value)])
    );

    await onSave(nextFields);
    setSaving(false);
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2">
        {Object.entries(values).map(([key, value]) => (
          <label key={key} className="space-y-2">
            <span className="block text-xs font-semibold uppercase tracking-normal text-slate-500">{key}</span>
            <textarea
              value={value}
              onChange={(event) => setValues((current) => ({ ...current, [key]: event.target.value }))}
              rows={value.includes("\n") || value.length > 70 ? 4 : 1}
              className="w-full resize-y rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-950 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
            />
          </label>
        ))}
      </div>
      <button
        type="button"
        onClick={handleSave}
        disabled={saving}
        className="inline-flex items-center gap-2 rounded-md bg-slate-950 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        <Save className="h-4 w-4" />
        {saving ? "Saving" : "Save corrections"}
      </button>
    </div>
  );
}
