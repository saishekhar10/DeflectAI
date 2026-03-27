-- schema.sql — Supabase schema for Deflect AI RAG pipeline
--
-- Run this in your Supabase project's SQL editor:
--   1. Go to https://supabase.com/dashboard → your project → SQL Editor
--   2. Paste this file and click "Run"
--
-- Prerequisites: pgvector extension must be available (enabled by default
-- on Supabase projects; this script enables it if not already active).

-- ── Extensions ────────────────────────────────────────────────────────────────

create extension if not exists vector;

-- ── Documents table ───────────────────────────────────────────────────────────

create table if not exists documents (
    id           uuid        primary key default gen_random_uuid(),
    content      text        not null,
    -- voyage-3 produces 1024-dimensional vectors
    embedding    vector(1024),
    source_url   text,
    page_title   text,
    chunk_index  integer,
    created_at   timestamp with time zone default now()
);

-- ── HNSW index for fast cosine-similarity search ──────────────────────────────

-- HNSW (Hierarchical Navigable Small World) is faster than IVFFlat for
-- small-to-medium datasets and doesn't require a training step.
create index if not exists documents_embedding_idx
    on documents
    using hnsw (embedding vector_cosine_ops);

-- ── match_documents RPC ───────────────────────────────────────────────────────

-- Called by search.py at runtime.  Returns the top `match_count` chunks
-- whose cosine similarity to `query_embedding` exceeds `similarity_threshold`.
create or replace function match_documents (
    query_embedding    vector(1024),
    match_count        int     default 5,
    similarity_threshold float  default 0.75
)
returns table (
    id           uuid,
    content      text,
    source_url   text,
    page_title   text,
    similarity   float
)
language sql stable
as $$
    select
        id,
        content,
        source_url,
        page_title,
        -- cosine similarity = 1 − cosine distance
        1 - (embedding <=> query_embedding) as similarity
    from documents
    where 1 - (embedding <=> query_embedding) > similarity_threshold
    order by embedding <=> query_embedding
    limit match_count;
$$;
