export type StepStatus = "pending" | "running" | "success" | "warning" | "failed";

export type PipelineStep = "upload" | "parse" | "extract" | "audit" | "insights" | "memo";

export type ParserStrategy = "digital" | "ocr" | "hybrid" | "failed" | string;

export type ParserPage = {
  page_number?: number;
  pageNumber?: number;
  strategy?: ParserStrategy;
  text_blocks?: unknown[];
  blocks?: unknown[];
  tables?: unknown[];
  raw_text?: string;
  text?: string;
  confidence?: number | null;
  warnings?: string[];
  metrics?: {
    text_char_count?: number;
    word_count?: number;
    table_candidate_count?: number;
    image_area_ratio?: number;
    extraction_confidence?: number;
    selected_strategy?: string;
  };
  metadata?: {
    text_char_count?: number;
    word_count?: number;
    table_candidate_count?: number;
    image_area_ratio?: number;
    extraction_confidence?: number;
    selected_strategy?: string;
  };
};

export type ParseResult = {
  document_id?: string;
  document_type?: string;
  pages?: ParserPage[];
  global_warnings?: string[];
  warnings?: string[];
  parser_version?: string;
};

export type FinancialGroup = Record<string, number | string | boolean | null | undefined>;

export type FinancialExtraction = {
  document_type?: string;
  classification_confidence?: number;
  classification_reasons?: string[];
  period?: {
    start_date?: string | null;
    end_date?: string | null;
    fiscal_year?: number | string | null;
  };
  currency?: string;
  income_statement?: FinancialGroup;
  balance_sheet?: FinancialGroup;
  cash_flow?: FinancialGroup;
  extraction_confidence?: Record<string, number>;
  missing_fields?: string[];
  source_references?: Array<Record<string, unknown>>;
};

export type FieldScore = {
  field?: string;
  value?: unknown;
  confidence?: number;
  evidence_found?: boolean;
  page_number?: number | null;
  issues?: string[];
};

export type ParserAudit = {
  overall_accuracy_score?: number;
  field_scores?: FieldScore[];
  red_flags?: string[];
  warnings?: string[];
  recommended_manual_review_fields?: string[];
  lender_insight_readiness?: {
    ready_for_credit_memo?: boolean;
    reason?: string;
    minimum_required_fields_present?: boolean;
  };
};

export type LenderInsights = {
  borrower_summary?: Record<string, unknown>;
  key_metrics?: Record<string, number | null | undefined>;
  risk_flags?: string[];
  positive_signals?: string[];
  questions_for_borrower?: string[];
  credit_memo_inputs?: {
    financial_snapshot?: Record<string, unknown>;
    risk_assessment?: Record<string, unknown>;
    data_quality?: Record<string, unknown>;
    recommended_next_steps?: string[];
  };
};

export type FullPipelineResponse = {
  parse_result?: ParseResult;
  parserResult?: ParseResult;
  financial_extraction?: FinancialExtraction;
  financialExtraction?: FinancialExtraction;
  parser_audit?: ParserAudit;
  parserAudit?: ParserAudit;
  lender_insights?: LenderInsights;
  lenderInsights?: LenderInsights;
  memo_markdown?: string;
  creditMemoMarkdown?: string;
  data_quality?: Record<string, unknown>;
  warnings?: string[];
  global_warnings?: string[];
  pages?: ParserPage[];
  document_type?: string;
  documentType?: string;
  rawText?: string;
};

export type NormalizedConsoleResult = {
  parseResult?: ParseResult;
  financialExtraction?: FinancialExtraction;
  parserAudit?: ParserAudit;
  lenderInsights?: LenderInsights;
  memoMarkdown?: string;
  rawResponse?: unknown;
  warnings: string[];
};
