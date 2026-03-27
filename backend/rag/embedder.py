"""
embedder.py — Generates embeddings for text chunks using VoyageAI.

Model: voyage-3 (1024-dimensional vectors)
Batch size: 5 chunks per API call (conservative to avoid token limits on large pages).
Each embed call is wrapped in a 30-second ThreadPoolExecutor timeout so a
hung request raises TimeoutError instead of blocking forever.
Requires VOYAGE_API_KEY in environment.
"""

import os
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

import voyageai
from dotenv import load_dotenv

_env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
load_dotenv(_env_path)

EMBED_MODEL = "voyage-3"
# Small batch size to avoid token-limit hangs on large pages.
# Paid accounts with higher TPM can increase this safely.
BATCH_SIZE = 5
# Seconds between batches — keeps free-tier requests under 3 RPM.
INTER_BATCH_DELAY = 21
# Seconds before a single embed() call is considered hung.
EMBED_TIMEOUT = 30


def _get_client() -> voyageai.Client:
    """Initialise and return a VoyageAI client."""
    api_key = os.environ.get("VOYAGE_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "VOYAGE_API_KEY is not set. "
            "Copy backend/.env.example to backend/.env and fill in your key."
        )
    return voyageai.Client(api_key=api_key)


def _embed_with_timeout(
    client: voyageai.Client, texts: list[str], timeout: int = EMBED_TIMEOUT
):
    """
    Call client.embed() in a background thread and raise TimeoutError if it
    doesn't return within `timeout` seconds.
    """
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(
            client.embed, texts, model=EMBED_MODEL, input_type="document"
        )
        return future.result(timeout=timeout)


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """
    Generate embeddings for a list of text chunks.

    Args:
        chunks: Output from chunker.chunk_documents() —
                list of {"content": str, "metadata": dict}

    Returns:
        List of dicts:
            {
                "content": str,
                "embedding": list[float],   # 1024-dimensional
                "metadata": dict,
            }
    """
    client = _get_client()
    total = len(chunks)
    num_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE

    embedded: list[dict] = []

    for batch_num in range(num_batches):
        start = batch_num * BATCH_SIZE
        end = min(start + BATCH_SIZE, total)
        batch = chunks[start:end]

        print(f"Embedding batch {batch_num + 1}/{num_batches} ({len(batch)} chunks)...")

        texts = [chunk["content"] for chunk in batch]

        # Retry up to 3 times on rate-limit errors or timeouts.
        result = None
        for attempt in range(3):
            try:
                result = _embed_with_timeout(client, texts)
                break
            except FuturesTimeoutError:
                if attempt == 2:
                    raise TimeoutError(
                        f"Batch {batch_num + 1} timed out after {EMBED_TIMEOUT}s "
                        f"on all 3 attempts."
                    )
                wait = INTER_BATCH_DELAY * (2 ** attempt)
                print(f"  Timeout — retrying in {wait}s (attempt {attempt + 1}/3)...")
                time.sleep(wait)
            except voyageai.error.RateLimitError as exc:
                if attempt == 2:
                    raise
                wait = INTER_BATCH_DELAY * (2 ** attempt)
                print(f"  Rate limit hit — retrying in {wait}s... ({exc})")
                time.sleep(wait)

        for chunk, vector in zip(batch, result.embeddings):
            embedded.append(
                {
                    "content": chunk["content"],
                    "embedding": vector,
                    "metadata": chunk["metadata"],
                }
            )

        # Polite inter-batch delay to stay within RPM limits.
        if batch_num < num_batches - 1:
            time.sleep(INTER_BATCH_DELAY)

    print(f"\nEmbedding complete. {len(embedded)} chunks embedded.")
    return embedded


def embed_query(query: str) -> list[float]:
    """
    Embed a single query string for similarity search.

    Args:
        query: The user's search query.

    Returns:
        1024-dimensional embedding vector as a list of floats.
    """
    client = _get_client()
    result = client.embed([query], model=EMBED_MODEL, input_type="query")
    return result.embeddings[0]
