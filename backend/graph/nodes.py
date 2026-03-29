"""
nodes.py — LangGraph node functions for Deflect AI.

Each node reads from GraphState, calls the appropriate agent, and returns
a partial state dict with updated fields.
"""

import os

from dotenv import load_dotenv
from langsmith import traceable
from supabase import create_client

load_dotenv()

from backend.agents.triage_agent import triage
from backend.agents.billing_agent import run_billing_agent
from backend.agents.technical_agent import run_technical_agent
from backend.agents.account_agent import run_account_agent
from backend.agents.escalation_agent import run_escalation_agent
from backend.agents.synthesis_agent import run_synthesis_agent
from backend.models.schemas import CustomerProfile, EscalationOutput
from backend.graph.state import GraphState

# Supabase client — created once at module load
_supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_KEY"],
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _profile_from_dict(d: dict) -> CustomerProfile:
    """Build a CustomerProfile from a raw dict, ignoring unknown fields."""
    return CustomerProfile(
        customer_id=d["customer_id"],
        name=d["name"],
        email=d["email"],
        plan=d["plan"],
        account_age_months=d["account_age_months"],
        tier=d["tier"],
        open_ticket_count=d.get("open_ticket_count", 0),
    )


def _collect_agent_outputs(state: GraphState) -> dict:
    """Return a dict of non-None specialist outputs keyed by agent name."""
    outputs = {}
    if state.get("billing_output"):
        outputs["billing"] = state["billing_output"]
    if state.get("technical_output"):
        outputs["technical"] = state["technical_output"]
    if state.get("account_output"):
        outputs["account"] = state["account_output"]
    if state.get("triage_output"):
        outputs["triage"] = state["triage_output"]
    return outputs


# ---------------------------------------------------------------------------
# Supabase write helper
# ---------------------------------------------------------------------------

def write_to_human_queue(escalation_output: EscalationOutput, customer_id: str) -> str:
    """
    Write an escalation ticket to the Supabase human_queue table.

    Returns the ticket_id on success.
    """
    row = {
        "ticket_id": escalation_output.ticket_id,
        "customer_id": customer_id,
        "customer_tier": escalation_output.customer_tier,
        "priority": escalation_output.priority,
        "summary": escalation_output.summary,
        "what_was_tried": escalation_output.what_was_tried,
        "original_ticket": escalation_output.original_ticket,
        "status": "pending",
    }
    _supabase.table("human_queue").insert(row).execute()
    return escalation_output.ticket_id


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------

@traceable(name="triage-node", tags=["node"])
def triage_node(state: GraphState) -> dict:
    from backend.models.schemas import TriageInput

    profile = _profile_from_dict(state["customer_profile"])
    result = triage(TriageInput(ticket_text=state["ticket_text"], customer_profile=profile))
    return {"triage_output": result.model_dump(), "agents_used": ["triage_agent"]}


@traceable(name="billing-node", tags=["node"])
def billing_node(state: GraphState) -> dict:
    result = run_billing_agent(
        ticket_text=state["ticket_text"],
        customer_id=state["customer_id"],
    )
    return {"billing_output": result.model_dump(), "agents_used": ["billing_agent"]}


@traceable(name="technical-node", tags=["node"])
def technical_node(state: GraphState) -> dict:
    result = run_technical_agent(
        ticket_text=state["ticket_text"],
        customer_id=state["customer_id"],
    )
    return {"technical_output": result.model_dump(), "agents_used": ["technical_agent"]}


@traceable(name="account-node", tags=["node"])
def account_node(state: GraphState) -> dict:
    result = run_account_agent(
        ticket_text=state["ticket_text"],
        customer_id=state["customer_id"],
    )
    return {"account_output": result.model_dump(), "agents_used": ["account_agent"]}


@traceable(name="escalation-node", tags=["node"])
def escalation_node(state: GraphState) -> dict:
    agent_outputs = _collect_agent_outputs(state)
    result = run_escalation_agent(
        ticket_text=state["ticket_text"],
        customer_profile=state["customer_profile"],
        agent_outputs=agent_outputs,
    )
    return {"escalation_output": result.model_dump(), "agents_used": ["escalation_agent"]}


@traceable(name="synthesis-node", tags=["node"])
def synthesis_node(state: GraphState) -> dict:
    agent_outputs = _collect_agent_outputs(state)
    # Remove triage from synthesis inputs — only specialist drafts needed
    agent_outputs.pop("triage", None)
    result = run_synthesis_agent(
        ticket_text=state["ticket_text"],
        agent_outputs=agent_outputs,
    )
    return {
        "synthesis_output": result.model_dump(),
        "final_response": result.final_response,
        "resolution_type": result.resolution_type,
        "agents_used": ["synthesis_agent"],
    }


@traceable(name="human-queue-node", tags=["node"])
def human_queue_node(state: GraphState) -> dict:
    escalation_data = state["escalation_output"]
    escalation = EscalationOutput(**escalation_data)
    ticket_id = write_to_human_queue(escalation, customer_id=state["customer_id"])
    return {
        "final_response": (
            f"Thank you for reaching out. Your issue has been escalated to our support team "
            f"for priority review. Your ticket ID is {ticket_id}. "
            f"A team member will contact you shortly."
        ),
        "resolution_type": "escalated",
    }


def post_specialist_node(state: GraphState) -> dict:
    """No-op fan-in node — waits for all parallel specialist branches to complete."""
    return {}
