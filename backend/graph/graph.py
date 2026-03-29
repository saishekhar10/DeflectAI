"""
graph.py — LangGraph graph construction for Deflect AI.

Exposes:
  deflect_graph — the compiled StateGraph (for LangSmith tracing)
  run_graph()   — main entry point for processing support tickets
"""

from langgraph.graph import StateGraph, END
from langgraph.types import Send

from backend.graph.state import GraphState
from backend.graph.nodes import (
    triage_node,
    billing_node,
    technical_node,
    account_node,
    escalation_node,
    synthesis_node,
    human_queue_node,
    post_specialist_node,
)


# ---------------------------------------------------------------------------
# Routing functions
# ---------------------------------------------------------------------------

_SPECIALIST_NODES = {"billing", "technical", "account"}


def route_after_triage(state: GraphState):
    """
    After triage, decide which specialist node(s) to run.

    Returns a single node name, or a list of Send() for parallel execution.
    """
    triage = state["triage_output"]

    if triage.get("escalate_immediately"):
        return "escalation_node"

    intents = [i for i in triage.get("intents", []) if i in _SPECIALIST_NODES]

    if not intents:
        # "general" only or empty — escalate
        return "escalation_node"

    if len(intents) == 1:
        return f"{intents[0]}_node"

    # Multiple intents — fan out in parallel
    return [Send(f"{i}_node", state) for i in intents]


def route_after_specialist(state: GraphState) -> str:
    """
    After specialist node(s) complete, decide whether to escalate or synthesize.
    """
    outputs = [
        state.get("billing_output"),
        state.get("technical_output"),
        state.get("account_output"),
    ]
    if any(o and o.get("escalate") for o in outputs):
        return "escalation_node"
    return "synthesis_node"


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

_builder = StateGraph(GraphState)

_builder.add_node("triage_node", triage_node)
_builder.add_node("billing_node", billing_node)
_builder.add_node("technical_node", technical_node)
_builder.add_node("account_node", account_node)
_builder.add_node("post_specialist", post_specialist_node)
_builder.add_node("escalation_node", escalation_node)
_builder.add_node("synthesis_node", synthesis_node)
_builder.add_node("human_queue_node", human_queue_node)

_builder.set_entry_point("triage_node")

# After triage: route to specialist(s) or directly to escalation
_builder.add_conditional_edges(
    "triage_node",
    route_after_triage,
    {
        "escalation_node": "escalation_node",
        "billing_node": "billing_node",
        "technical_node": "technical_node",
        "account_node": "account_node",
    },
)

# All specialist nodes fan-in to post_specialist (no-op join)
_builder.add_edge("billing_node", "post_specialist")
_builder.add_edge("technical_node", "post_specialist")
_builder.add_edge("account_node", "post_specialist")

# After fan-in: escalate or synthesize
_builder.add_conditional_edges(
    "post_specialist",
    route_after_specialist,
    {
        "escalation_node": "escalation_node",
        "synthesis_node": "synthesis_node",
    },
)

# Escalation path
_builder.add_edge("escalation_node", "human_queue_node")
_builder.add_edge("human_queue_node", END)

# Resolution path
_builder.add_edge("synthesis_node", END)

# Compiled graph — expose for LangSmith tracing
deflect_graph = _builder.compile()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_graph(ticket_text: str, customer_id: str, customer_profile: dict) -> dict:
    """
    Main entry point for processing a support ticket through the Deflect AI graph.

    Args:
        ticket_text: The raw support ticket text from the customer.
        customer_id: The customer's ID (e.g. "cus_001").
        customer_profile: Customer profile dict with keys: customer_id, name, email,
                          plan, tier, account_age_months, etc.

    Returns:
        The final graph state as a dict, including:
          - final_response: customer-facing reply
          - resolution_type: "resolved" or "escalated"
          - escalation_output: set if ticket was escalated (contains ticket_id)
          - billing_output / technical_output / account_output: set if those agents ran
    """
    initial_state: GraphState = {
        "ticket_text": ticket_text,
        "customer_id": customer_id,
        "customer_profile": customer_profile,
        "triage_output": None,
        "billing_output": None,
        "technical_output": None,
        "account_output": None,
        "escalation_output": None,
        "synthesis_output": None,
        "final_response": "",
        "resolution_type": "",
    }
    result = deflect_graph.invoke(initial_state)
    return dict(result)
