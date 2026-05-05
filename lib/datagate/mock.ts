import type { FullPipelineResponse } from "@/lib/datagate/types";

export const sampleDataGateResult: FullPipelineResponse = {
  parse_result: {
    document_id: "sample:financial-statement",
    document_type: "financial_statement",
    parser_version: "hybrid-v1",
    global_warnings: ["sample_mode: loaded frontend demo response."],
    pages: [
      {
        page_number: 1,
        strategy: "digital",
        confidence: 0.92,
        raw_text:
          "Financial statement 2025\nRevenue: 1,000,000 MNT\nNet profit: 120,000 MNT\nTotal assets: 900,000 MNT\nTotal liabilities: 320,000 MNT\nEquity: 580,000 MNT",
        tables: [{ source: "sample", rows: [] }],
        warnings: [],
        metrics: {
          text_char_count: 1560,
          word_count: 228,
          table_candidate_count: 1,
          image_area_ratio: 0.04,
          extraction_confidence: 0.92,
          selected_strategy: "digital"
        }
      }
    ]
  },
  financial_extraction: {
    document_type: "financial_statement",
    classification_confidence: 0.91,
    period: { start_date: null, end_date: null, fiscal_year: 2025 },
    currency: "MNT",
    income_statement: {
      revenue: 1000000,
      cost_of_goods_sold: null,
      gross_profit: 420000,
      operating_expenses: null,
      operating_profit: null,
      net_profit: 120000
    },
    balance_sheet: {
      total_assets: 900000,
      current_assets: 500000,
      cash: 220000,
      inventory: null,
      receivables: null,
      total_liabilities: 320000,
      short_term_debt: 180000,
      long_term_debt: null,
      equity: 580000
    },
    cash_flow: {
      operating_cash_flow: 130000,
      investing_cash_flow: null,
      financing_cash_flow: null,
      ending_cash: 220000
    },
    extraction_confidence: {
      revenue: 0.88,
      net_profit: 0.86,
      total_assets: 0.89,
      total_liabilities: 0.87,
      equity: 0.87
    },
    missing_fields: ["cost_of_goods_sold", "operating_expenses", "inventory", "receivables"],
    source_references: [
      { field: "revenue", page_number: 1, source: "table", raw_label: "Revenue", confidence: 0.88 },
      { field: "net_profit", page_number: 1, source: "table", raw_label: "Net profit", confidence: 0.86 }
    ]
  },
  parser_audit: {
    overall_accuracy_score: 0.87,
    field_scores: [
      { field: "revenue", value: 1000000, confidence: 0.91, evidence_found: true, page_number: 1, issues: [] },
      { field: "net_profit", value: 120000, confidence: 0.88, evidence_found: true, page_number: 1, issues: [] },
      { field: "cash", value: 220000, confidence: 0.76, evidence_found: true, page_number: 1, issues: [] }
    ],
    red_flags: ["missing_cash_flow_detail"],
    warnings: ["sample_warning: verify against bank statement before credit memo use."],
    recommended_manual_review_fields: ["cost_of_goods_sold", "operating_expenses"],
    lender_insight_readiness: {
      ready_for_credit_memo: true,
      minimum_required_fields_present: true,
      reason: "Minimum financial statement fields are present."
    }
  },
  lender_insights: {
    borrower_summary: {
      period: "2025",
      currency: "MNT",
      revenue: 1000000,
      net_profit: 120000,
      total_assets: 900000,
      total_liabilities: 320000,
      equity: 580000,
      audit_score: 0.87
    },
    key_metrics: {
      gross_margin: 0.42,
      net_margin: 0.12,
      debt_to_assets: 0.3556,
      debt_to_equity: 0.5517,
      current_ratio: 2.7778,
      return_on_assets: 0.1333,
      equity_ratio: 0.6444
    },
    risk_flags: ["missing_cash_flow_detail", "verify_revenue_with_bank_statements"],
    positive_signals: ["profitable", "positive_equity", "low_leverage", "current_ratio_above_1_5"],
    questions_for_borrower: [
      "Please provide bank statements to verify reported revenue.",
      "Please confirm whether the submitted statements are final audited figures."
    ],
    credit_memo_inputs: {
      recommended_next_steps: [
        "Verify revenue against bank statements and tax filings.",
        "Review missing operating expense detail."
      ]
    }
  },
  memo_markdown:
    "# Зээлийн шинжилгээний товч мемо\n\n## 1. Зээл хүсэгчийн товч мэдээлэл\n- Компанийн нэр: Altan Trade LLC\n- Тайлангийн хугацаа: 2025\n- Валют: MNT\n- Баримтын төрөл: Санхүүгийн тайлан\n- Өгөгдлийн чанарын үнэлгээ: Өндөр\n\n## 2. Санхүүгийн гол үзүүлэлтүүд\n| Үзүүлэлт | Дүн |\n| --- | ---: |\n| Борлуулалтын орлого | 1,000,000 MNT |\n| Цэвэр ашиг | 120,000 MNT |\n| Нийт хөрөнгө | 900,000 MNT |\n| Нийт өр төлбөр | 320,000 MNT |\n| Өөрийн хөрөнгө | 580,000 MNT |\n\n## 7. Урьдчилсан дүгнэлт\nЦаашид судлах боломжтой. Гэхдээ банкны хуулга, татварын тайлангаар орлогыг тулган баталгаажуулах шаардлагатай.",
  warnings: ["sample_mode: no backend call was made."]
};
