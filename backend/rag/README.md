# Deflect AI — RAG Ingestion Pipeline

This module scrapes the [Linear docs](https://linear.app/docs), chunks the content, generates embeddings with VoyageAI, and stores everything in Supabase for semantic search at runtime.

---

## 1. Supabase Setup

### a) Create a project
1. Go to [supabase.com](https://supabase.com) and create a new project.
2. Note your **Project URL** and **Service Role Key** (Project Settings → API).

### b) Enable pgvector and run the schema
1. In your Supabase dashboard, open **SQL Editor**.
2. Paste the contents of `backend/schema.sql` and click **Run**.

This creates:
- `documents` table with a `vector(1024)` column for VoyageAI embeddings
- An **HNSW** index for fast cosine-similarity search
- A `match_documents` RPC function used by `search.py` at runtime

---

## 2. Environment Setup

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` and fill in:

| Variable | Where to get it |
|---|---|
| `VOYAGE_API_KEY` | [dash.voyageai.com/api-keys](https://dash.voyageai.com/api-keys) |
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com/) |
| `SUPABASE_URL` | Supabase → Project Settings → API |
| `SUPABASE_SERVICE_KEY` | Supabase → Project Settings → API → service_role |

---

## 3. Running the Ingestion Script

Install dependencies first:

```bash
pip install -r backend/requirements.txt
```

### Quick test (dry run, 5 pages)

Runs the full pipeline — scrape, chunk, embed — but **skips** the Supabase write:

```bash
python -m backend.rag.ingest --dry-run --limit 5
```

### Full ingestion

Scrapes all Linear docs and writes to Supabase:

```bash
python -m backend.rag.ingest
```

### Flags

| Flag | Description |
|---|---|
| `--dry-run` | Skip Supabase upsert; print a preview of the first 3 chunks |
| `--limit N` | Scrape at most N pages (e.g. `--limit 10` for quick testing) |

---

## 4. Testing `rag_search()` Manually

Open a Python shell from the project root:

```python
from backend.rag.search import rag_search, confidence_check

results = rag_search("how do I create an issue in Linear", top_k=5)

for r in results:
    print(f"[{r['similarity']:.3f}] {r['page_title']}")
    print(f"  {r['source_url']}")
    print(f"  {r['content'][:120]}\n")

print("High confidence?", confidence_check(results))
```

---

## 5. Re-running Ingestion When Linear Docs Update

The `documents` table uses **upsert**, so re-running ingestion is safe — existing rows are updated in place.

To refresh all docs:

```bash
python -m backend.rag.ingest
```

To update a subset (e.g. spot-check after a docs release):

```bash
python -m backend.rag.ingest --limit 20
```

For a scheduled refresh (e.g. weekly cron):

```cron
0 3 * * 1 cd /path/to/deflectai && python -m backend.rag.ingest >> logs/ingest.log 2>&1
```
