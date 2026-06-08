-- =============================================================================
-- 001_create_memos.sql
-- Memos table — stores AI-generated investment research memos.
-- =============================================================================

-- Enable UUID extension (already present in Supabase projects by default)
create extension if not exists "uuid-ossp";


-- =============================================================================
-- Table
-- =============================================================================

create table if not exists public.memos (
    id               uuid        primary key default uuid_generate_v4(),
    ticker           text        not null,
    memo             text        not null,
    date             text        not null,           -- ISO date string, e.g. "2025-06-05"

    -- Individual agent outputs (stored for debugging / future fine-tuning)
    sec_analysis     text        not null default '',
    earnings_analysis text       not null default '',
    analyst_analysis text        not null default '',
    news_analysis    text        not null default '',
    tech_analysis    text        not null default '',

    -- Nullable — anonymous users can generate memos, authenticated ones are tracked
    generated_by     uuid        references auth.users(id) on delete set null,

    created_at       timestamptz not null default now()
);

-- Index for the most common query: latest memo for a ticker
create index if not exists memos_ticker_created_at_idx
    on public.memos (ticker, created_at desc);

-- Index for user history
create index if not exists memos_generated_by_idx
    on public.memos (generated_by)
    where generated_by is not null;


-- =============================================================================
-- Row Level Security
-- =============================================================================

alter table public.memos enable row level security;

-- Anyone (including anonymous) can read memos
create policy "Memos are publicly readable"
    on public.memos
    for select
    using (true);

-- Only the service role (backend) can insert/update/delete
-- (RLS is bypassed when using the service_role key, so this just prevents
--  accidental writes via the anon key from the browser)
create policy "Only service role can write memos"
    on public.memos
    for insert
    with check (false);   -- blocks anon/authenticated direct inserts; service role bypasses RLS


-- =============================================================================
-- Helper view: latest memo per ticker
-- =============================================================================

create or replace view public.latest_memos as
select distinct on (ticker)
    id,
    ticker,
    memo,
    date,
    generated_by,
    created_at
from public.memos
order by ticker, created_at desc;
