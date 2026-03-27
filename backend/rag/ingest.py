"""
ingest.py — Orchestrates the full RAG ingestion pipeline.

Pipeline:
    scraper.scrape_docs()
        → chunker.chunk_documents()
        → embedder.embed_chunks()
        → Supabase upsert (batches of 50)

Usage:
    # Full run
    python -m backend.rag.ingest

    # Dry run (no Supabase writes)
    python -m backend.rag.ingest --dry-run

    # Limit pages for quick testing
    python -m backend.rag.ingest --limit 10 --dry-run

Required environment variables (set in backend/.env):
    SUPABASE_URL
    SUPABASE_SERVICE_KEY
    VOYAGE_API_KEY
"""

import argparse
import os
import sys
import time

from dotenv import load_dotenv
from supabase import create_client, Client

from backend.rag.scraper import scrape_docs
from backend.rag.chunker import chunk_documents
from backend.rag.embedder import embed_chunks

# Load backend/.env (relative to this file's location)
_env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
load_dotenv(_env_path)

UPSERT_BATCH_SIZE = 50


def _get_supabase_client() -> Client:
    """Initialise a Supabase client using service-role credentials."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")

    if not url or not key:
        print(
            "ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in your .env file.",
            file=sys.stderr,
        )
        sys.exit(1)

    return create_client(url, key)


def _get_ingested_urls(client: Client) -> set[str]:
    """
    Return the set of source_urls already present in the documents table.
    Used to skip re-ingestion of pages that haven't changed.
    """
    response = client.table("documents").select("source_url").execute()
    return {row["source_url"] for row in response.data if row["source_url"]}


def _upsert_to_supabase(
    client: Client, embedded_chunks: list[dict]
) -> int:
    """
    Upsert embedded chunks into the Supabase `documents` table in batches.

    Returns the total number of rows upserted.
    """
    total = len(embedded_chunks)
    num_batches = (total + UPSERT_BATCH_SIZE - 1) // UPSERT_BATCH_SIZE
    inserted = 0

    for batch_num in range(num_batches):
        start = batch_num * UPSERT_BATCH_SIZE
        end = min(start + UPSERT_BATCH_SIZE, total)
        batch = embedded_chunks[start:end]

        rows = [
            {
                "content": item["content"],
                "embedding": item["embedding"],
                "source_url": item["metadata"]["source_url"],
                "page_title": item["metadata"]["page_title"],
                "chunk_index": item["metadata"]["chunk_index"],
            }
            for item in batch
        ]

        print(
            f"Upserting batch {batch_num + 1}/{num_batches} "
            f"({len(rows)} rows)..."
        )
        # Retry up to 3 times on transient network errors (SSL drops, etc.)
        for attempt in range(3):
            try:
                client.table("documents").upsert(rows).execute()
                break
            except Exception as exc:
                if attempt == 2:
                    raise
                wait = 5 * (2 ** attempt)
                print(f"  Upsert error (attempt {attempt + 1}/3), retrying in {wait}s: {exc}")
                time.sleep(wait)
        inserted += len(rows)

    return inserted


def run(dry_run: bool = False, limit: int | None = None) -> None:
    """
    Execute the full ingestion pipeline.

    Args:
        dry_run: If True, skip the Supabase upsert step.
        limit:   If set, scrape at most this many pages.
    """
    print("=" * 60)
    print("Deflect AI — RAG Ingestion Pipeline")
    print("=" * 60)

    # ── Step 1: Scrape ────────────────────────────────────────────
    print("\n[1/4] Scraping Linear docs...\n")
    docs = scrape_docs(limit=limit)

    if not docs:
        print("No documents scraped. Exiting.")
        return

    # ── Step 2: Chunk ─────────────────────────────────────────────
    print(f"\n[2/4] Chunking {len(docs)} pages...\n")
    chunks = chunk_documents(docs)
    print(f"Produced {len(chunks)} chunks.")

    if not chunks:
        print("No chunks produced. Exiting.")
        return

    # Filter out oversized chunks — likely scraper artifacts from JS-heavy pages
    # that defeat the chunker and cause the embedder to hang on token limits.
    MAX_CHUNK_CHARS = 6000
    oversized = [c for c in chunks if len(c["content"]) > MAX_CHUNK_CHARS]
    if oversized:
        print(f"  WARNING: dropping {len(oversized)} chunks exceeding "
              f"{MAX_CHUNK_CHARS} chars (scraper artifacts):")
        for c in oversized:
            print(f"    {c['metadata']['source_url']}  chunk {c['metadata']['chunk_index']} "
                  f"({len(c['content'])} chars)")
        chunks = [c for c in chunks if len(c["content"]) <= MAX_CHUNK_CHARS]
        print(f"  {len(chunks)} chunks remaining after filter.")

    # ── Step 3: Deduplicate ───────────────────────────────────────
    # Skip chunks whose source_url already exists in Supabase so that
    # re-runs don't re-embed and re-insert unchanged pages.
    if not dry_run:
        print("\n[3/4] Checking Supabase for already-ingested URLs...")
        supabase = _get_supabase_client()
        ingested_urls = _get_ingested_urls(supabase)
        before = len(chunks)
        chunks = [c for c in chunks if c["metadata"]["source_url"] not in ingested_urls]
        skipped = before - len(chunks)
        if skipped:
            print(f"  Skipping {skipped} chunks from {len(ingested_urls)} already-ingested URLs.")
        print(f"  {len(chunks)} new chunks to embed and upsert.")

        if not chunks:
            print("\nAll pages already ingested. Nothing to do.")
            return
    else:
        supabase = None  # not needed for dry run

    # ── Step 4: Embed ─────────────────────────────────────────────
    step = "4/4" if not dry_run else "3/3"
    print(f"\n[{step}] Embedding {len(chunks)} chunks...\n")
    embedded = embed_chunks(chunks)

    # ── Step 5: Upsert (or dry-run preview) ───────────────────────
    if dry_run:
        print("\n[DRY RUN] Skipping Supabase upsert.")
        print("First 3 chunks preview:\n")
        for i, item in enumerate(embedded[:3]):
            print(f"  Chunk {i}:")
            print(f"    source_url  : {item['metadata']['source_url']}")
            print(f"    page_title  : {item['metadata']['page_title']}")
            print(f"    chunk_index : {item['metadata']['chunk_index']}")
            print(f"    content[:80]: {item['content'][:80]!r}")
            print(f"    embedding   : [{item['embedding'][0]:.6f}, ...] "
                  f"(dim={len(item['embedding'])})\n")
    else:
        print(f"\n[5/5] Upserting {len(embedded)} chunks to Supabase...\n")
        total_inserted = _upsert_to_supabase(supabase, embedded)
        print(f"\nIngestion complete. Total chunks inserted: {total_inserted}")

    print("\nDone.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the Deflect AI RAG ingestion pipeline."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run the full pipeline but skip the Supabase upsert step.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Scrape at most N pages (useful for quick testing).",
    )
    args = parser.parse_args()
    run(dry_run=args.dry_run, limit=args.limit)


if __name__ == "__main__":
    main()
