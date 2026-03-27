"""
chunker.py — Splits scraped document text into overlapping chunks.

Uses a recursive character splitter (no external dependencies):
  - Primary split: paragraphs (\n\n)
  - Fallback splits: lines (\n), sentences (". "), words (" ")
  - Chunk size: ~2000 chars (~500 tokens at 4 chars/token)
  - Overlap:    ~200 chars (~50 tokens)
"""

CHUNK_SIZE = 2000   # characters
CHUNK_OVERLAP = 200  # characters
# Ordered from coarsest to finest granularity
SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


def _split_text(text: str, separators: list[str], chunk_size: int) -> list[str]:
    """
    Recursively split `text` using the first separator that produces pieces
    small enough to fit in `chunk_size`.  Falls back to the next separator
    if a piece is still too large, down to character-level splitting.
    """
    if not separators:
        # Hard character-level split as a last resort
        return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]

    separator = separators[0]
    remaining_seps = separators[1:]
    parts = text.split(separator) if separator else list(text)

    chunks: list[str] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if len(part) <= chunk_size:
            chunks.append(part)
        else:
            # This piece is still too large — recurse with finer separators
            chunks.extend(_split_text(part, remaining_seps, chunk_size))

    return chunks


def _merge_with_overlap(
    pieces: list[str], chunk_size: int, overlap: int
) -> list[str]:
    """
    Greedily merge small `pieces` into chunks of up to `chunk_size` chars,
    then carry the tail of each chunk forward as an overlap prefix for the next.
    """
    chunks: list[str] = []
    current = ""

    for piece in pieces:
        candidate = (current + "\n\n" + piece).strip() if current else piece

        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                chunks.append(current)
            # Start new chunk with overlap from the end of the previous chunk
            overlap_text = current[-overlap:] if len(current) > overlap else current
            current = (overlap_text + "\n\n" + piece).strip() if overlap_text else piece

    if current:
        chunks.append(current)

    return chunks


def chunk_documents(docs: list[dict]) -> list[dict]:
    """
    Split each scraped document into overlapping text chunks.

    Args:
        docs: Output from scraper.scrape_docs() —
              list of {"url": str, "title": str, "content": str}

    Returns:
        List of dicts:
            {
                "content": str,
                "metadata": {
                    "source_url": str,
                    "page_title": str,
                    "chunk_index": int,
                }
            }
    """
    all_chunks: list[dict] = []

    for doc in docs:
        url: str = doc["url"]
        title: str = doc["title"]
        content: str = doc["content"]

        if not content.strip():
            continue

        # Step 1: recursively split into atomic pieces
        pieces = _split_text(content, SEPARATORS, CHUNK_SIZE)

        # Step 2: merge pieces into overlapping chunks
        merged = _merge_with_overlap(pieces, CHUNK_SIZE, CHUNK_OVERLAP)

        for idx, chunk_text in enumerate(merged):
            if not chunk_text.strip():
                continue
            all_chunks.append(
                {
                    "content": chunk_text,
                    "metadata": {
                        "source_url": url,
                        "page_title": title,
                        "chunk_index": idx,
                    },
                }
            )

    return all_chunks
