# Deflect AI

**Autonomous multi-agent customer support orchestration system built with LangGraph, FastAPI, and Next.js.**

Deflect AI routes incoming SaaS support tickets to specialized AI agents — billing, technical, and account — running in parallel where needed, and synthesizes a single coherent response. Low-confidence tickets and high-value customer escalations are routed to a human queue with full context preserved.

---

## Architecture

```
[Incoming Ticket]
       ↓
[Triage Agent]  ← classifies intent, scores confidence, routes
       ↓
  ┌────┴─────────────┐
  ↓                  ↓
[Billing Agent]  [Technical Agent]  ← run in parallel for multi-intent tickets
[Account Agent]
  ↓                  ↓
  └────┬─────────────┘
       ↓
[Synthesis Agent]  ← merges drafts into single customer reply
       ↓
  [Response]    OR    [Human Queue]  ← escalation path
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Orchestration | LangGraph |
| LLM | Anthropic Claude (claude-sonnet-4-20250514) |
| Embeddings | Voyage AI (voyage-3, 1024-dim) |
| Vector DB | Supabase pgvector |
| Backend | FastAPI |
| Frontend | Next.js 15 |
| Tracing | LangSmith |
| Deployment | Vercel (frontend), Railway (backend) |

---

## Agents

**Triage Agent** — Classifies incoming ticket intents (billing, technical, account), scores routing confidence (0–1), detects urgency, and routes to specialist agents. Enterprise customers and low-confidence tickets always escalate.

**Billing Agent** — Resolves billing disputes using mock Stripe tooling. Autonomously applies credits within a $100 threshold. Escalates larger refunds and ambiguous cases.

**Technical Agent** — RAG-powered over scraped Linear docs (441 chunks, pgvector). Diagnoses technical issues, matches against known bugs, and cites source documentation in responses.

**Account Agent** — Handles plan changes, seat management, and cancellation requests. Cancellations always route to a human.

**Escalation Agent** — Synthesizes a full-context summary for human handoff. Writes to a human queue visible in the frontend in real time.

**Synthesis Agent** — Merges multi-agent response drafts into a single coherent customer reply with no seams.

---

## RAG Pipeline

Linear's public docs are scraped, chunked (~500 tokens, 50-token overlap), embedded with `voyage-3`, and stored in Supabase pgvector. The Technical Agent queries this at runtime via cosine similarity search.

```bash
# One-time ingestion
python -m backend.rag.ingest

# Re-run when Linear docs update
python -m backend.rag.ingest --limit 20  # test first
python -m backend.rag.ingest             # full run
```

---

## Project Structure

```
deflect-ai/
├── backend/
│   ├── agents/
│   │   ├── triage_agent.py
│   │   ├── billing_agent.py
│   │   ├── technical_agent.py
│   │   ├── account_agent.py
│   │   ├── escalation_agent.py
│   │   └── synthesis_agent.py
│   ├── rag/
│   │   ├── scraper.py
│   │   ├── chunker.py
│   │   ├── embedder.py
│   │   ├── ingest.py
│   │   └── search.py
│   ├── models/
│   │   └── schemas.py
│   ├── mock_apis/
│   │   ├── stripe_mock.py
│   │   └── account_mock.py
│   ├── tests/
│   │   ├── routing_test_suite.json
│   │   └── test_triage.py
│   ├── graph.py
│   ├── main.py
│   └── requirements.txt
└── frontend/
    └── (Next.js app)
```

---

## Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- Supabase account (free tier)
- Anthropic API key
- Voyage AI API key
- LangSmith account (free tier)

### Backend

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Copy and fill in environment variables
cp backend/.env.example backend/.env

# Run Supabase schema (paste schema.sql into Supabase SQL editor)
# Then ingest Linear docs
python -m backend.rag.ingest

# Start backend
uvicorn backend.main:app --reload
```

### Environment Variables

```
ANTHROPIC_API_KEY=sk-ant-...
VOYAGE_API_KEY=pa-...
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
LANGSMITH_API_KEY=ls__...
LANGSMITH_PROJECT=deflect-ai
```

---

## Testing

```bash
# Run routing test suite (30 tickets, target 90%+ accuracy)
python -m backend.tests.test_triage

# Test RAG search
python3 -c "
import sys; sys.path.insert(0, '.')
from backend.rag.search import rag_search
results = rag_search('github integration not syncing')
for r in results:
    print(f'{r[\"similarity\"]:.3f} — {r[\"page_title\"]}')
"
```

---

## Key Metrics

- **Autonomous resolution rate** — % of tickets resolved without hitting the escalation agent. Target: 75%+
- **Routing accuracy** — % of tickets routed to the correct specialist agents. Target: 90%+
- **RAG confidence** — % of technical queries returning results above similarity threshold

All metrics tracked via LangSmith.

---

## Demo

The frontend includes:
- **Chat UI** — submit support tickets and see responses in real time
- **Agent trace panel** — shows which agents fired, in what order, with reasoning
- **Human queue panel** — escalated tickets appear here with full context summary
- **Demo persona toggle** — switch between SaaS, e-commerce, and IT helpdesk

---

## License

MIT
