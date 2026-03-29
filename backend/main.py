"""
main.py — FastAPI application entry point for Deflect AI backend.

Start with:
    uvicorn backend.main:app --reload --port 8000
"""

import os

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client

from backend.mock_apis.stripe_mock import router as stripe_router
from backend.mock_apis.account_mock import router as account_router
from backend.models.schemas import TicketRequest, TicketResponse, HumanQueueItem, StatusUpdate
from backend.graph.graph import run_graph
from backend.mock_apis.mock_data import CUSTOMERS

app = FastAPI(title="Deflect AI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stripe_router)
app.include_router(account_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ticket", response_model=TicketResponse)
def submit_ticket(request: TicketRequest):
    try:
        customer_profile = CUSTOMERS.get(request.customer_id)
        if not customer_profile:
            raise HTTPException(status_code=422, detail="Customer not found")
        result = run_graph(request.ticket_text, request.customer_id, customer_profile)
        ticket_id = ""
        if result.get("resolution_type") == "escalated":
            ticket_id = result.get("escalation_output", {}).get("ticket_id", "")
        return TicketResponse(
            final_response=result["final_response"],
            resolution_type=result["resolution_type"],
            agents_used=result["agents_used"],
            ticket_id=ticket_id,
            resolution_time_ms=result["resolution_time_ms"],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/queue", response_model=list[HumanQueueItem])
async def get_queue():
    supabase: Client = create_client(
        os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"]
    )
    response = (
        supabase.table("human_queue")
        .select("*")
        .neq("status", "resolved")
        .order("created_at", desc=True)
        .execute()
    )
    return response.data or []


@app.patch("/queue/{ticket_id}")
async def update_queue_item(ticket_id: str, update: StatusUpdate):
    supabase: Client = create_client(
        os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"]
    )
    response = (
        supabase.table("human_queue")
        .update({"status": update.status})
        .eq("ticket_id", ticket_id)
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {"success": True, "ticket_id": ticket_id, "status": update.status}


@app.get("/customers")
async def get_customers():
    return sorted(
        [
            {
                "customer_id": c["customer_id"],
                "name": c["name"],
                "plan": c["plan"],
                "tier": c["tier"],
            }
            for c in CUSTOMERS.values()
        ],
        key=lambda x: x["customer_id"],
    )
