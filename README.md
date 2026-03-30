# Deflect AI

**Autonomous multi-agent customer support orchestration system built with LangGraph, FastAPI, and Next.js.**

Deflect AI classifies incoming SaaS support tickets via a triage agent, routes them to specialized agents (billing, technical, account) running in parallel where needed, and synthesizes a single coherent response. A RAG pipeline over scraped Linear docs powers the technical agent's knowledge base. Low-confidence tickets and high-value customer escalations route to a human queue with full context preserved. Every run is traced end-to-end via LangSmith.

<img width="1675" height="899" alt="Screenshot 2026-03-29 at 8 33 23 PM" src="https://github.com/user-attachments/assets/dfd57f99-dd9d-4f4a-be1c-21469516d39e" />

<img width="680" height="570" alt="deflect_ai_architecture1" src="https://github.com/user-attachments/assets/97482824-f2cc-44b3-b3ad-d8ae5a20d88b" />



---

## Architecture

```
[Incoming Ticket]
       ↓
[Triage Agent]  ← classifies intent, scores confidence, routes
       ↓
  ┌────┴──────────────────────────┐
  ↓                               ↓
[Billing Agent]              [Escalation Agent]
[Technical Agent]  (parallel)      ↓
[Account Agent]              [Human Queue Node]
  ↓                               ↓
  └────┬──────────────────────────┘
       ↓
[Synthesis Agent]  ← merges drafts into single customer reply
       ↓
  [Response]    OR    [Human Queue]
```

### Routing Rules

| Condition | Route |
|---|---|
| Single intent, confidence ≥ 0.6 | Direct to matching agent |
| Multi-intent, confidence ≥ 0.6 | Parallel execution via `Send()` |
| Any intent, confidence < 0.6 | Escalation Node |
| Agent returns `escalate: true` | Escalation Node |
| Customer tier = enterprise | Always escalate |
| Refund request > $100 | Escalation Node |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Orchestration | LangGraph |
| LLM | Anthropic Claude (`claude-sonnet-4-20250514`) |
| Embeddings | Voyage AI (`voyage-3`, 1024-dim) |
| Vector DB | Supabase pgvector |
| Backend | FastAPI |
| Frontend | Next.js 15 + Tailwind CSS v4 |
| Tracing | LangSmith |
| Deployment | Vercel (frontend), Railway (backend) |

---

## Agents

**Triage Agent** — Classifies incoming ticket intents (billing, technical, account), scores routing confidence (0–1), detects urgency, and routes to specialist agents. Enterprise customers and low-confidence tickets always escalate.

**Billing Agent** — Resolves billing disputes using mock Stripe tooling. Autonomously applies credits within a $100 threshold. Escalates larger refunds and ambiguous cases.

**Technical Agent** — RAG-powered over scraped Linear docs (441 chunks, pgvector). Diagnoses technical issues, matches against known bugs, and cites source documentation in responses.

**Account Agent** — Handles plan changes, seat management, and cancellation requests. Cancellations always route to a human.

**Escalation Agent** — Synthesizes a full-context summary for human handoff. Writes to the human queue visible in the frontend in real time.

**Synthesis Agent** — Merges multi-agent response drafts into a single coherent customer reply.

---

## RAG Pipeline

Linear's public docs are scraped, chunked (~500 tokens, 50-token overlap), embedded with `voyage-3`, and stored in Supabase pgvector. The Technical Agent queries this at runtime via cosine similarity search (threshold: 0.3).

```bash
# One-time ingestion
python -m backend.rag.ingest

# Re-run when Linear docs update
python -m backend.rag.ingest --limit 20  # test first
python -m backend.rag.ingest             # full run
```

---

## Frontend

Three-panel dashboard at `localhost:3000`:

- **Chat Panel** — Submit support tickets with a demo persona selector (customer tier + account context). Shows the AI response inline with resolution status and latency.
- **Agent Trace Panel** — Real-time view of which agents fired, in what order, and what each one did. Shows the full multi-agent workflow as it executes.
- **Human Queue Panel** — Escalated tickets appear here with priority badge, customer ID, context summary, and a Resolve button.

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
│   ├── graph/
│   │   ├── state.py
│   │   ├── nodes.py
│   │   └── graph.py
│   ├── mock_apis/
│   │   ├── stripe_mock.py
│   │   └── account_mock.py
│   ├── models/
│   │   └── schemas.py
│   ├── tests/
│   │   ├── routing_test_suite.json
│   │   ├── test_triage.py
│   │   ├── test_graph.py
│   │   ├── eval_dataset.json
│   │   └── run_evals.py
│   └── main.py
└── frontend/
    ├── app/
    │   ├── layout.tsx
    │   ├── page.tsx
    │   └── globals.css
    ├── components/
    │   ├── ChatPanel.tsx
    │   ├── AgentTracePanel.tsx
    │   ├── HumanQueuePanel.tsx
    │   └── Navbar.tsx
    └── lib/
        ├── api.ts
        └── types.ts
```

---

## Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- Supabase account (pgvector enabled)
- Anthropic API key
- Voyage AI API key
- LangSmith account (free tier)

### Backend

```bash
pip install -r backend/requirements.txt

# Paste schema.sql into Supabase SQL editor, then ingest Linear docs
python -m backend.rag.ingest

# Start backend (from project root)
PYTHONPATH=. uvicorn backend.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev  # runs on localhost:3000
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
# Routing test suite (30 tickets, target 90%+ accuracy)
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

| Metric | Target | Status |
|---|---|---|
| Routing accuracy | 90%+ | 93.3% (28/30) |
| Autonomous resolution rate | 75%+ | Tracked via LangSmith |
| RAG confidence | Results above 0.3 threshold | 6/8 queries validated |


