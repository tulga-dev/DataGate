"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Brain,
  ClipboardCheck,
  FileCode2,
  FileText,
  Gauge,
  Layers3,
  Loader2,
  Play,
  ShieldCheck,
  Sparkles
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { analyzeFinancials, generateCreditMemo, getDataGateApiBaseUrl, parseDocument, runFullPipeline } from "@/lib/datagate/api";
import { sampleDataGateResult } from "@/lib/datagate/mock";
import type {
  FinancialExtraction,
  FullPipelineResponse,
  LenderInsights,
  NormalizedConsoleResult,
  ParseResult,
  ParserAudit,
  ParserPage,
  PipelineStep,
  StepStatus
} from "@/lib/datagate/types";
import { cn, formatBytes, formatPercent } from "@/lib/utils/format";
import { ConfidenceBadge } from "@/components/datagate/ConfidenceBadge";
import { FileDropzone } from "@/components/datagate/FileDropzone";
import { JsonViewer } from "@/components/datagate/JsonViewer";
import { MarkdownMemoViewer } from "@/components/datagate/MarkdownMemoViewer";
import { MetricCard } from "@/components/datagate/MetricCard";
import { PipelineStatus } from "@/components/datagate/PipelineStatus";
import { RiskFlagList } from "@/components/datagate/RiskFlagList";
import { SummaryCard } from "@/components/datagate/SummaryCard";

type ActionKey = "parse" | "analyze" | "memo" | "full";
type TabKey = "overview" | "pages" | "financial" | "audit" | "insights" | "memo" | "raw";
type BackendStatus = "checking" | "online" | "offline";

const emptyStatuses: Record<PipelineStep, StepStatus> = {
  upload: "pending",
  parse: "pending",
  extract: "pending",
  audit: "pending",
  insights: "pending",
  memo: "pending"
};

const tabs: Array<{ key: TabKey; label: string; icon: LucideIcon }> = [
  { key: "overview", label: "Overview", icon: Gauge },
  { key: "pages", label: "Parsed Pages", icon: Layers3 },
  { key: "financial", label: "Financial JSON", icon: FileCode2 },
  { key: "audit", label: "Audit", icon: ClipboardCheck },
  { key: "insights", label: "Insights", icon: Brain },
  { key: "memo", label: "Credit Memo", icon: FileText },
  { key: "raw", label: "Raw API", icon: BarChart3 }
];

const sidebarItems = [
  "Upload & Test",
  "Parse Result",
  "Financial Extraction",
  "Audit",
  "Lender Insights",
  "Credit Memo"
];

function normalizeResponse(response: FullPipelineResponse): NormalizedConsoleResult {
  const parseResult =
    response.parse_result ??
    response.parserResult ??
    (response.pages
      ? {
          document_type: response.document_type ?? response.documentType,
          pages: response.pages,
          global_warnings: response.global_warnings ?? response.warnings
        }
      : undefined);

  const dataQualityAudit: ParserAudit | undefined = response.data_quality
    ? {
        overall_accuracy_score:
          typeof response.data_quality.overall_accuracy_score === "number"
            ? response.data_quality.overall_accuracy_score
            : undefined,
        recommended_manual_review_fields: Array.isArray(response.data_quality.recommended_manual_review_fields)
          ? (response.data_quality.recommended_manual_review_fields as string[])
          : [],
        lender_insight_readiness:
          typeof response.data_quality.lender_insight_readiness === "object" && response.data_quality.lender_insight_readiness
            ? (response.data_quality.lender_insight_readiness as ParserAudit["lender_insight_readiness"])
            : undefined
      }
    : undefined;

  const financialExtraction = response.financial_extraction ?? response.financialExtraction;
  const parserAudit = response.parser_audit ?? response.parserAudit ?? dataQualityAudit;
  const lenderInsights = response.lender_insights ?? response.lenderInsights;
  const memoMarkdown = response.memo_markdown ?? response.creditMemoMarkdown;
  const warnings = collectWarnings(response, parseResult, parserAudit);

  return {
    parseResult,
    financialExtraction,
    parserAudit,
    lenderInsights,
    memoMarkdown,
    rawResponse: response,
    warnings
  };
}

function collectWarnings(response: FullPipelineResponse, parseResult?: ParseResult, parserAudit?: ParserAudit) {
  return Array.from(
    new Set([
      ...(response.warnings ?? []),
      ...(response.global_warnings ?? []),
      ...(parseResult?.warnings ?? []),
      ...(parseResult?.global_warnings ?? []),
      ...(parserAudit?.warnings ?? []),
      ...(parserAudit?.red_flags ?? [])
    ])
  );
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "number") return Number.isInteger(value) ? value.toLocaleString("en-US") : value.toFixed(4);
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}

function formatMoney(value: unknown, currency?: string) {
  if (typeof value !== "number") return "—";
  return `${value.toLocaleString("en-US")} ${currency && currency !== "unknown" ? currency : ""}`.trim();
}

function pageNumber(page: ParserPage, index: number) {
  return page.page_number ?? page.pageNumber ?? index + 1;
}

function pageText(page: ParserPage) {
  return page.raw_text ?? page.text ?? "";
}

function pageMetrics(page: ParserPage) {
  return page.metrics ?? page.metadata ?? {};
}

function firstParserStrategy(parseResult?: ParseResult) {
  const strategies = (parseResult?.pages ?? []).map((page) => page.strategy).filter(Boolean);
  return strategies[0] ?? "—";
}

function statusAfter(action: ActionKey, hasWarnings: boolean): Record<PipelineStep, StepStatus> {
  const ok: StepStatus = hasWarnings ? "warning" : "success";
  if (action === "parse") return { ...emptyStatuses, upload: "success", parse: ok };
  if (action === "analyze") return { upload: "success", parse: ok, extract: ok, audit: ok, insights: ok, memo: "pending" };
  if (action === "memo") return { ...emptyStatuses, upload: "success", memo: ok };
  return { upload: "success", parse: ok, extract: ok, audit: ok, insights: ok, memo: ok };
}

function statusRunning(action: ActionKey): Record<PipelineStep, StepStatus> {
  if (action === "parse") return { ...emptyStatuses, upload: "success", parse: "running" };
  if (action === "analyze") return { upload: "success", parse: "running", extract: "running", audit: "running", insights: "running", memo: "pending" };
  if (action === "memo") return { ...emptyStatuses, upload: "success", memo: "running" };
  return { upload: "success", parse: "running", extract: "running", audit: "running", insights: "running", memo: "running" };
}

function statusFailed(action: ActionKey): Record<PipelineStep, StepStatus> {
  const running = statusRunning(action);
  return Object.fromEntries(
    Object.entries(running).map(([step, status]) => [step, status === "running" ? "failed" : status])
  ) as Record<PipelineStep, StepStatus>;
}

export function DataGateConsole() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<NormalizedConsoleResult | null>(null);
  const [activeTab, setActiveTab] = useState<TabKey>("overview");
  const [statuses, setStatuses] = useState<Record<PipelineStep, StepStatus>>(emptyStatuses);
  const [loadingAction, setLoadingAction] = useState<ActionKey | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [backendStatus, setBackendStatus] = useState<BackendStatus>("checking");

  const apiBaseUrl = getDataGateApiBaseUrl();

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${apiBaseUrl}/health`, { signal: controller.signal })
      .then((response) => setBackendStatus(response.ok ? "online" : "offline"))
      .catch(() => setBackendStatus("offline"));
    return () => controller.abort();
  }, [apiBaseUrl]);

  const parseResult = result?.parseResult;
  const financialExtraction = result?.financialExtraction;
  const parserAudit = result?.parserAudit;
  const lenderInsights = result?.lenderInsights;
  const memoMarkdown = result?.memoMarkdown;
  const pages = parseResult?.pages ?? [];
  const missingFields = financialExtraction?.missing_fields ?? [];
  const riskFlags = lenderInsights?.risk_flags ?? parserAudit?.red_flags ?? [];
  const readyForMemo = parserAudit?.lender_insight_readiness?.ready_for_credit_memo;

  const actionButtons: Array<{ key: ActionKey; label: string; icon: LucideIcon }> = [
    { key: "parse", label: "Run Parse Only", icon: Layers3 },
    { key: "analyze", label: "Analyze Financials", icon: BarChart3 },
    { key: "memo", label: "Generate Credit Memo", icon: FileText },
    { key: "full", label: "Run Full Pipeline", icon: Sparkles }
  ];

  const backendTone = backendStatus === "online" ? "bg-emerald-400" : backendStatus === "checking" ? "bg-amber-300" : "bg-rose-400";
  const backendLabel = backendStatus === "online" ? "Backend online" : backendStatus === "checking" ? "Checking backend" : "Backend offline";

  async function runAction(action: ActionKey) {
    if (!file) {
      setError("Upload a PDF or image before running the pipeline.");
      setStatuses({ ...emptyStatuses, upload: "failed" });
      return;
    }

    setLoadingAction(action);
    setError(null);
    setStatuses(statusRunning(action));

    try {
      let response: FullPipelineResponse;
      if (action === "parse") response = await parseDocument(file);
      else if (action === "analyze") response = await analyzeFinancials(file);
      else if (action === "memo") response = await generateCreditMemo(file);
      else response = await runFullPipeline(file);

      const normalized = normalizeResponse(response);
      setResult(normalized);
      setStatuses(statusAfter(action, normalized.warnings.length > 0));
      setActiveTab(action === "memo" ? "memo" : action === "parse" ? "pages" : "overview");
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "DataGate backend request failed.");
      setStatuses(statusFailed(action));
    } finally {
      setLoadingAction(null);
    }
  }

  function loadSample() {
    const normalized = normalizeResponse(sampleDataGateResult);
    setResult(normalized);
    setStatuses(statusAfter("full", normalized.warnings.length > 0));
    setError(null);
    setActiveTab("overview");
  }

  return (
    <main className="min-h-screen bg-[#050812] text-slate-100">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_18%_0%,rgba(59,130,246,0.24),transparent_28%),radial-gradient(circle_at_88%_8%,rgba(34,211,238,0.16),transparent_25%),linear-gradient(180deg,#050812_0%,#0a1020_45%,#050812_100%)]" />
      <div className="pointer-events-none fixed inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cyan-200/60 to-transparent" />
      <div className="relative grid min-h-screen lg:grid-cols-[280px_minmax(0,1fr)]">
        <aside className="border-b border-white/10 bg-white/[0.035] p-5 backdrop-blur-xl lg:border-b-0 lg:border-r">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-cyan-300/20 bg-cyan-300/10 text-cyan-100">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <p className="text-lg font-semibold tracking-normal text-white">DataGate</p>
              <p className="text-xs text-slate-400">Lender intelligence layer</p>
            </div>
          </div>

          <nav className="mt-8 space-y-1">
            {sidebarItems.map((item, index) => (
              <button
                key={item}
                type="button"
                onClick={() => setActiveTab(tabs[Math.min(index, tabs.length - 2)].key)}
                className="flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-left text-sm text-slate-300 transition hover:bg-white/[0.06] hover:text-white"
              >
                {item}
                <span className="h-1.5 w-1.5 rounded-full bg-cyan-300/60" />
              </button>
            ))}
          </nav>

          <div className="mt-8 rounded-2xl border border-white/10 bg-black/20 p-4">
            <div className="flex items-center gap-2 text-sm font-medium text-white">
              <span className={cn("h-2.5 w-2.5 rounded-full", backendTone)} />
              {backendLabel}
            </div>
            <p className="mt-2 break-all text-xs leading-5 text-slate-400">{apiBaseUrl}</p>
          </div>
        </aside>

        <section className="min-w-0 px-4 py-6 sm:px-6 lg:px-8">
          <header className="overflow-hidden rounded-3xl border border-white/10 bg-white/[0.055] p-6 shadow-2xl shadow-black/30 backdrop-blur-xl xl:p-7">
            <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.28em] text-cyan-200/80">Internal testing dashboard</p>
                <h1 className="mt-3 max-w-4xl text-4xl font-semibold tracking-normal text-white sm:text-5xl">
                  DataGate Intelligence Console
                </h1>
                <p className="mt-4 max-w-3xl text-sm leading-6 text-slate-300">
                  Upload a lender document, run the parser stack, inspect field-level confidence, and generate deterministic Mongolian memo output.
                </p>
              </div>
              <button
                type="button"
                onClick={loadSample}
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-cyan-300/25 bg-cyan-300/10 px-4 py-2.5 text-sm font-semibold text-cyan-100 transition hover:bg-cyan-300/15"
              >
                <Sparkles className="h-4 w-4" />
                Load Sample Result
              </button>
            </div>

            <div className="mt-7 grid gap-3 md:grid-cols-3">
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Console mode</p>
                <p className="mt-2 text-lg font-semibold text-white">No-auth internal test</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Primary workflow</p>
                <p className="mt-2 text-lg font-semibold text-white">PDF to memo</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Fallback</p>
                <p className="mt-2 text-lg font-semibold text-white">Sample result ready</p>
              </div>
            </div>
          </header>

          <div className="mt-6 grid gap-6 xl:grid-cols-[420px_minmax(0,1fr)]">
            <section className="rounded-3xl border border-white/10 bg-white/[0.055] p-5 shadow-2xl shadow-black/30 backdrop-blur-xl">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-base font-semibold text-white">Upload & Test</h2>
                  <p className="mt-1 text-xs text-slate-400">No login or database required.</p>
                </div>
                {file ? <span className="rounded-full border border-white/10 px-2 py-1 text-xs text-slate-300">{formatBytes(file.size)}</span> : null}
              </div>

              <div className="mt-5">
                <FileDropzone
                  file={file}
                  onFileChange={(nextFile) => {
                    setFile(nextFile);
                    setError(null);
                    setStatuses(nextFile ? { ...emptyStatuses, upload: "success" } : emptyStatuses);
                  }}
                />
              </div>

              <div className="mt-5 grid gap-2">
                {actionButtons.map(({ key, label, icon: Icon }) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => void runAction(key)}
                    disabled={!file || loadingAction !== null}
                    className={cn(
                      "inline-flex items-center justify-center gap-2 rounded-xl border px-4 py-3 text-sm font-semibold transition",
                      key === "full"
                        ? "border-cyan-300/30 bg-cyan-300/15 text-cyan-50 hover:bg-cyan-300/20"
                        : "border-white/10 bg-white/[0.055] text-slate-200 hover:bg-white/[0.08]",
                      "disabled:cursor-not-allowed disabled:opacity-45"
                    )}
                  >
                    {loadingAction === key ? <Loader2 className="h-4 w-4 animate-spin" /> : <Icon className="h-4 w-4" />}
                    {loadingAction === key ? "Running..." : label}
                  </button>
                ))}
              </div>

              {file ? (
                <div className="mt-4 rounded-2xl border border-white/10 bg-black/20 p-3 text-xs text-slate-400">
                  <p className="font-medium text-slate-200">{file.name}</p>
                  <p className="mt-1">{formatBytes(file.size)} ready for upload</p>
                </div>
              ) : null}

              <div className="mt-4 rounded-2xl border border-white/10 bg-black/20 p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">This console validates</p>
                <div className="mt-3 grid gap-2 text-sm text-slate-300">
                  <span>Parser routing and page strategy</span>
                  <span>Financial field extraction</span>
                  <span>Audit confidence and memo readiness</span>
                </div>
              </div>

              {error ? (
                <div className="mt-4 rounded-2xl border border-rose-300/30 bg-rose-400/10 p-4 text-sm leading-6 text-rose-100">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                    <span>{error}</span>
                  </div>
                </div>
              ) : null}
            </section>

            <section className="min-w-0 space-y-6">
              <PipelineStatus statuses={statuses} />

              <div className="rounded-3xl border border-white/10 bg-white/[0.045] p-3 shadow-2xl shadow-black/30 backdrop-blur-xl">
                <div className="flex gap-2 overflow-x-auto border-b border-white/10 pb-3">
                  {tabs.map(({ key, label, icon: Icon }) => (
                    <button
                      key={key}
                      type="button"
                      onClick={() => setActiveTab(key)}
                      className={cn(
                        "inline-flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold transition",
                        activeTab === key ? "bg-cyan-300/15 text-cyan-50" : "text-slate-400 hover:bg-white/[0.06] hover:text-white"
                      )}
                    >
                      <Icon className="h-4 w-4" />
                      {label}
                    </button>
                  ))}
                </div>

                <div className="p-2 sm:p-4">
                  {loadingAction ? (
                    <LoadingState action={loadingAction} />
                  ) : !result ? (
                    <EmptyState />
                  ) : activeTab === "overview" ? (
                    <OverviewTab
                      parseResult={parseResult}
                      financialExtraction={financialExtraction}
                      parserAudit={parserAudit}
                      lenderInsights={lenderInsights}
                      warnings={result.warnings}
                    />
                  ) : activeTab === "pages" ? (
                    <ParsedPagesTab pages={pages} />
                  ) : activeTab === "financial" ? (
                    <FinancialTab extraction={financialExtraction} />
                  ) : activeTab === "audit" ? (
                    <AuditTab audit={parserAudit} />
                  ) : activeTab === "insights" ? (
                    <InsightsTab insights={lenderInsights} />
                  ) : activeTab === "memo" ? (
                    <MarkdownMemoViewer markdown={memoMarkdown} />
                  ) : (
                    <JsonViewer value={result.rawResponse} />
                  )}
                </div>
              </div>
            </section>
          </div>
        </section>
      </div>
    </main>
  );
}

function EmptyState() {
  return (
    <div className="flex min-h-[460px] items-center justify-center rounded-2xl border border-dashed border-white/10 bg-black/15 p-8 text-center">
      <div>
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.06] text-cyan-100">
          <Activity className="h-6 w-6" />
        </div>
        <h2 className="mt-4 text-lg font-semibold text-white">No pipeline result yet</h2>
        <p className="mt-2 max-w-md text-sm leading-6 text-slate-400">
          Upload a document or load the sample response to inspect parser decisions, extracted fields, risk flags, and memo output.
        </p>
      </div>
    </div>
  );
}

function LoadingState({ action }: { action: ActionKey }) {
  const label =
    action === "parse"
      ? "Parsing document pages"
      : action === "analyze"
        ? "Extracting and auditing financials"
        : action === "memo"
          ? "Generating deterministic memo"
          : "Running full intelligence pipeline";

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-cyan-300/20 bg-cyan-400/10 p-4">
        <div className="flex items-center gap-3 text-cyan-50">
          <Loader2 className="h-5 w-5 animate-spin" />
          <div>
            <p className="text-sm font-semibold">{label}</p>
            <p className="mt-1 text-xs text-cyan-100/70">Waiting for backend response and normalizing the result for the console.</p>
          </div>
        </div>
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        {[0, 1, 2].map((item) => (
          <div key={item} className="h-28 animate-pulse rounded-2xl border border-white/10 bg-white/[0.055]" />
        ))}
      </div>
      <div className="space-y-3">
        {[0, 1, 2, 3].map((item) => (
          <div key={item} className="h-14 animate-pulse rounded-2xl border border-white/10 bg-white/[0.04]" />
        ))}
      </div>
    </div>
  );
}

function OverviewTab({
  parseResult,
  financialExtraction,
  parserAudit,
  lenderInsights,
  warnings
}: {
  parseResult?: ParseResult;
  financialExtraction?: FinancialExtraction;
  parserAudit?: ParserAudit;
  lenderInsights?: LenderInsights;
  warnings: string[];
}) {
  const ready = parserAudit?.lender_insight_readiness?.ready_for_credit_memo;
  const riskFlags = lenderInsights?.risk_flags ?? parserAudit?.red_flags ?? [];
  const missingFields = financialExtraction?.missing_fields ?? [];

  return (
    <div className="space-y-5">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        <SummaryCard label="Document type" value={financialExtraction?.document_type ?? parseResult?.document_type ?? "—"} />
        <SummaryCard label="Parser strategy" value={firstParserStrategy(parseResult)} detail={`${parseResult?.pages?.length ?? 0} page(s)`} />
        <SummaryCard label="Accuracy score" value={formatPercent(parserAudit?.overall_accuracy_score)} tone={(parserAudit?.overall_accuracy_score ?? 0) >= 0.8 ? "good" : "warning"} />
        <SummaryCard label="Ready for memo" value={ready === undefined ? "—" : ready ? "Yes" : "No"} tone={ready ? "good" : ready === false ? "risk" : "default"} />
        <SummaryCard label="Missing fields" value={missingFields.length} tone={missingFields.length ? "warning" : "good"} />
        <SummaryCard label="Risk flags" value={riskFlags.length} tone={riskFlags.length ? "risk" : "good"} />
      </div>

      <div className="rounded-2xl border border-white/10 bg-white/[0.045] p-4">
        <h3 className="text-sm font-semibold text-white">Processing warnings</h3>
        {warnings.length ? (
          <div className="mt-3 flex flex-wrap gap-2">
            {warnings.map((warning) => (
              <span key={warning} className="rounded-full border border-amber-300/25 bg-amber-400/10 px-3 py-1 text-xs text-amber-100">
                {warning}
              </span>
            ))}
          </div>
        ) : (
          <p className="mt-2 text-sm text-slate-400">No warnings returned.</p>
        )}
      </div>
    </div>
  );
}

function ParsedPagesTab({ pages }: { pages: ParserPage[] }) {
  if (!pages.length) return <EmptyPanel title="No parsed pages yet" label="Run Parse Only or Full Pipeline to inspect page strategy, raw text, and page-level warnings." />;

  return (
    <div className="space-y-3">
      {pages.map((page, index) => {
        const metrics = pageMetrics(page);
        return (
          <details key={`${pageNumber(page, index)}-${index}`} className="group rounded-2xl border border-white/10 bg-white/[0.045] p-4">
            <summary className="flex cursor-pointer flex-wrap items-center gap-3 rounded-xl transition group-open:mb-1">
              <span className="text-sm font-semibold text-white">Page {pageNumber(page, index)}</span>
              <span className="rounded-full border border-cyan-300/25 bg-cyan-400/10 px-2 py-1 text-xs text-cyan-100">
                {page.strategy ?? "unknown"}
              </span>
              <ConfidenceBadge value={page.confidence ?? metrics.extraction_confidence} dark />
              <span className="text-xs text-slate-400">{formatValue(metrics.text_char_count ?? pageText(page).length)} chars</span>
              <span className="text-xs text-slate-400">{(page.tables ?? []).length} table(s)</span>
            </summary>
            {(page.warnings ?? []).length ? (
              <div className="mt-4 flex flex-wrap gap-2">
                {(page.warnings ?? []).map((warning) => (
                  <span key={warning} className="rounded-full border border-amber-300/25 bg-amber-400/10 px-2 py-1 text-xs text-amber-100">
                    {warning}
                  </span>
                ))}
              </div>
            ) : null}
            <pre className="mt-4 max-h-80 overflow-auto whitespace-pre-wrap rounded-xl bg-black/30 p-4 text-xs leading-6 text-slate-300">
              {pageText(page) || "No raw text returned for this page."}
            </pre>
          </details>
        );
      })}
    </div>
  );
}

function FinancialTab({ extraction }: { extraction?: FinancialExtraction }) {
  const [showJson, setShowJson] = useState(false);
  if (!extraction) return <EmptyPanel title="No financial extraction yet" label="Run Analyze Financials or Full Pipeline to populate income statement, balance sheet, cash flow, and missing fields." />;

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button
          type="button"
          onClick={() => setShowJson((value) => !value)}
          className="rounded-xl border border-white/10 bg-white/[0.06] px-3 py-2 text-xs font-semibold text-slate-200 hover:bg-white/10"
        >
          {showJson ? "Show cards" : "Show JSON"}
        </button>
      </div>
      {showJson ? (
        <JsonViewer value={extraction} />
      ) : (
        <>
          <div className="grid gap-3 md:grid-cols-3">
            <SummaryCard label="Period" value={extraction.period?.fiscal_year ?? extraction.period?.end_date ?? "—"} />
            <SummaryCard label="Currency" value={extraction.currency ?? "—"} />
            <SummaryCard label="Missing fields" value={extraction.missing_fields?.length ?? 0} tone={(extraction.missing_fields?.length ?? 0) ? "warning" : "good"} />
          </div>
          <FinancialGroupCard title="Income Statement" group={extraction.income_statement} currency={extraction.currency} />
          <FinancialGroupCard title="Balance Sheet" group={extraction.balance_sheet} currency={extraction.currency} />
          <FinancialGroupCard title="Cash Flow" group={extraction.cash_flow} currency={extraction.currency} />
          <div className="rounded-2xl border border-white/10 bg-white/[0.045] p-4">
            <h3 className="text-sm font-semibold text-white">Missing Fields</h3>
            <div className="mt-3 flex flex-wrap gap-2">
              {(extraction.missing_fields ?? []).map((field) => (
                <span key={field} className="rounded-full border border-amber-300/25 bg-amber-400/10 px-3 py-1 text-xs text-amber-100">
                  {field}
                </span>
              ))}
              {(extraction.missing_fields ?? []).length === 0 ? <span className="text-sm text-slate-400">No missing fields reported.</span> : null}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function FinancialGroupCard({ title, group, currency }: { title: string; group?: Record<string, unknown>; currency?: string }) {
  const entries = Object.entries(group ?? {});
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.045] p-4">
      <h3 className="text-sm font-semibold text-white">{title}</h3>
      <div className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
        {entries.map(([key, value]) => (
          <div key={key} className="rounded-xl border border-white/10 bg-black/20 p-3">
            <p className="text-xs uppercase tracking-[0.12em] text-slate-500">{key.replaceAll("_", " ")}</p>
            <p className="mt-2 text-sm font-semibold text-slate-100">{typeof value === "number" ? formatMoney(value, currency) : formatValue(value)}</p>
          </div>
        ))}
        {!entries.length ? <p className="text-sm text-slate-400">No fields returned.</p> : null}
      </div>
    </div>
  );
}

function AuditTab({ audit }: { audit?: ParserAudit }) {
  if (!audit) return <EmptyPanel title="No audit yet" label="Run Analyze Financials or Full Pipeline to see field confidence, red flags, and memo readiness." />;

  return (
    <div className="space-y-5">
      <div className="grid gap-3 lg:grid-cols-[280px_minmax(0,1fr)]">
        <SummaryCard
          label="Overall accuracy"
          value={formatPercent(audit.overall_accuracy_score)}
          detail={audit.lender_insight_readiness?.reason}
          tone={(audit.overall_accuracy_score ?? 0) >= 0.8 ? "good" : (audit.overall_accuracy_score ?? 0) >= 0.6 ? "warning" : "risk"}
        />
        <div className="rounded-2xl border border-white/10 bg-white/[0.045] p-4">
          <h3 className="text-sm font-semibold text-white">Memo readiness</h3>
          <p className={cn("mt-3 text-2xl font-semibold", audit.lender_insight_readiness?.ready_for_credit_memo ? "text-emerald-100" : "text-rose-100")}>
            {audit.lender_insight_readiness?.ready_for_credit_memo ? "Ready" : "Needs review"}
          </p>
          <p className="mt-2 text-sm leading-6 text-slate-400">{audit.lender_insight_readiness?.reason ?? "—"}</p>
        </div>
      </div>

      <div className="overflow-hidden rounded-2xl border border-white/10">
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead className="bg-white/[0.06] text-xs uppercase tracking-[0.12em] text-slate-400">
            <tr>
              <th className="px-4 py-3">Field</th>
              <th className="px-4 py-3">Value</th>
              <th className="px-4 py-3">Confidence</th>
              <th className="px-4 py-3">Evidence</th>
              <th className="px-4 py-3">Issues</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/10">
            {(audit.field_scores ?? []).map((score) => {
              const confidence = score.confidence ?? 0;
              const rowTone = confidence >= 0.85 ? "bg-emerald-400/[0.035]" : confidence >= 0.65 ? "bg-amber-400/[0.035]" : "bg-rose-400/[0.045]";
              return (
                <tr key={score.field} className={rowTone}>
                  <td className="px-4 py-3 font-medium text-white">{score.field}</td>
                  <td className="px-4 py-3 text-slate-300">{formatValue(score.value)}</td>
                  <td className="px-4 py-3"><ConfidenceBadge value={score.confidence} dark /></td>
                  <td className="px-4 py-3 text-slate-300">{score.evidence_found ? `Page ${score.page_number ?? "—"}` : "Missing"}</td>
                  <td className="px-4 py-3 text-slate-400">{(score.issues ?? []).join(", ") || "—"}</td>
                </tr>
              );
            })}
            {(audit.field_scores ?? []).length === 0 ? (
              <tr className="bg-white/[0.025]">
                <td className="px-4 py-6 text-center text-slate-400" colSpan={5}>
                  No field-level scores returned.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <RiskFlagList items={audit.red_flags} emptyLabel="No red flags returned." />
        <RiskFlagList items={audit.recommended_manual_review_fields} emptyLabel="No manual review fields returned." tone="warning" />
      </div>
    </div>
  );
}

function InsightsTab({ insights }: { insights?: LenderInsights }) {
  if (!insights) return <EmptyPanel title="No lender insights yet" label="Run Analyze Financials or Full Pipeline to generate ratios, risk flags, positive signals, and borrower questions." />;

  const metrics = insights.key_metrics ?? {};
  const nextSteps = insights.credit_memo_inputs?.recommended_next_steps ?? [];

  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {Object.entries(metrics).map(([key, value]) => (
          <MetricCard key={key} label={key} value={value} />
        ))}
        {Object.entries(metrics).length === 0 ? (
          <div className="rounded-2xl border border-dashed border-white/10 bg-black/15 p-6 text-sm text-slate-400">
            No key metrics returned.
          </div>
        ) : null}
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <div>
          <h3 className="mb-3 text-sm font-semibold text-white">Positive signals</h3>
          <RiskFlagList items={insights.positive_signals} emptyLabel="No positive signals returned." tone="good" />
        </div>
        <div>
          <h3 className="mb-3 text-sm font-semibold text-white">Risk flags</h3>
          <RiskFlagList items={insights.risk_flags} emptyLabel="No risk flags returned." />
        </div>
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <TextList title="Borrower questions" items={insights.questions_for_borrower ?? []} />
        <TextList title="Recommended next steps" items={nextSteps} />
      </div>
    </div>
  );
}

function TextList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.045] p-4">
      <h3 className="text-sm font-semibold text-white">{title}</h3>
      <div className="mt-3 space-y-2">
        {items.length ? items.map((item) => <p key={item} className="rounded-xl bg-black/20 px-3 py-2 text-sm text-slate-300">{item}</p>) : <p className="text-sm text-slate-400">—</p>}
      </div>
    </div>
  );
}

function EmptyPanel({ title, label }: { title: string; label: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-white/10 bg-black/15 p-8 text-center">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.05] text-slate-300">
        <FileText className="h-5 w-5" />
      </div>
      <h3 className="mt-4 text-base font-semibold text-white">{title}</h3>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-400">{label}</p>
    </div>
  );
}
