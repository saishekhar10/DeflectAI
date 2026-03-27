"""
search.py — Runtime RAG search interface for the Technical Agent.

The Technical Agent imports and calls `rag_search()` to retrieve relevant
Linear docs context before generating a response.

Requires environment variables:
    VOYAGE_API_KEY       — for query embedding
    SUPABASE_URL         — Supabase project URL
    SUPABASE_SERVICE_KEY — Supabase service-role key
"""

import os

from dotenv import load_dotenv
from supabase import create_client, Client

from backend.rag.embedder import embed_query

# Load backend/.env relative to this file's location
_env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
load_dotenv(_env_path)

# Module-level Supabase client (initialised lazily on first call)
_supabase_client: Client | None = None


def _get_client() -> Client:
    """Return a cached Supabase client, creating it on first use."""
    global _supabase_client
    if _supabase_client is None:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY")
        if not url or not key:
            raise EnvironmentError(
                "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set. "
                "Copy backend/.env.example to backend/.env and fill in your keys."
            )
        _supabase_client = create_client(url, key)
    return _supabase_client


def rag_search(
    query: str,
    top_k: int = 5,
    similarity_threshold: float = 0.3,
) -> list[dict]:
    """
    Search the Supabase documents table for chunks semantically similar
    to `query`.

    Args:
        query:               The user's question or search string.
        top_k:               Maximum number of results to return.
        similarity_threshold: Minimum cosine similarity (0–1) for a result
                              to be included.  Lower = more permissive.

    Returns:
        List of dicts (sorted by descending similarity):
            {
                "content":    str,   # chunk text
                "source_url": str,   # original Linear docs URL
                "page_title": str,   # page title
                "similarity": float, # cosine similarity score
            }
        Returns an empty list if no results exceed the threshold.
    """
    # Embed the query with VoyageAI (input_type="query" is handled inside embed_query)
    query_embedding: list[float] = embed_query(query)

    # Call the match_documents Postgres function via Supabase RPC
    response = (
        _get_client()
        .rpc(
            "match_documents",
            {
                "query_embedding": query_embedding,
                "match_count": top_k,
                "similarity_threshold": similarity_threshold,
            },
        )
        .execute()
    )

    if not response.data:
        return []

    return [
        {
            "content": row["content"],
            "source_url": row["source_url"],
            "page_title": row["page_title"],
            "similarity": row["similarity"],
        }
        for row in response.data
    ]


def confidence_check(results: list[dict]) -> bool:
    """
    Return True if at least one result has similarity >= 0.35.

    Use this to decide whether the RAG context is reliable enough to
    answer the user's question, or whether to fall back to a generic reply.
    Threshold is calibrated to voyage-3's cosine similarity scoring range.

    Args:
        results: Output from rag_search().

    Returns:
        True if any result meets the confidence bar, False otherwise.
    """
    HIGH_CONFIDENCE_THRESHOLD = 0.35
    return any(r["similarity"] >= HIGH_CONFIDENCE_THRESHOLD for r in results)
