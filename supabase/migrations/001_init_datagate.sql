create extension if not exists pgcrypto;

create table if not exists documents (
  id uuid primary key default gen_random_uuid(),
  original_filename text not null,
  file_type text,
  file_size bigint,
  storage_path text,
  document_type text,
  status text default 'pending',
  confidence numeric,
  raw_text text,
  ocr_markdown text,
  extracted_data jsonb,
  warnings jsonb,
  ocr_engine text,
  ocr_engine_version text,
  ocr_confidence numeric,
  layout_confidence numeric,
  table_count integer,
  stamp_detected boolean,
  processing_time_ms integer,
  fallback_used boolean default false,
  fallback_reason text,
  requires_human_review boolean default false,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists document_reviews (
  id uuid primary key default gen_random_uuid(),
  document_id uuid references documents(id) on delete cascade,
  reviewer_id uuid,
  review_status text,
  corrected_data jsonb,
  notes text,
  created_at timestamptz default now()
);

create table if not exists document_events (
  id uuid primary key default gen_random_uuid(),
  document_id uuid references documents(id) on delete cascade,
  event_type text,
  event_payload jsonb,
  created_at timestamptz default now()
);

create index if not exists documents_document_type_idx on documents(document_type);
create index if not exists documents_status_idx on documents(status);
create index if not exists documents_created_at_idx on documents(created_at);
create index if not exists document_events_document_id_idx on document_events(document_id);
create index if not exists document_reviews_document_id_idx on document_reviews(document_id);

alter table documents enable row level security;
alter table document_reviews enable row level security;
alter table document_events enable row level security;
