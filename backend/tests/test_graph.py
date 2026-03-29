"""
test_graph.py — End-to-end tests for the Deflect AI LangGraph pipeline.

Run with:
    python backend/tests/test_graph.py

Requires:
  - Mock API server running: uvicorn backend.main:app --reload --port 8000
  - .env file at project root with ANTHROPIC_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY
  - human_queue table created in Supabase (run backend/schema_queue.sql first)
"""

import sys
import os
from pathlib import Path

# Ensure the project root (deflectai/) is on sys.path regardless of where the
# script is invoked from.
_project_root = Path(__file__).resolve().parents[2]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
from backend.mock_apis.mock_data import CUSTOMERS
from backend.graph.graph import run_graph


def _agents_fired(result: dict) -> list[str]:
    """Return list of specialist agents that populated outputs in the result."""
    fired = []
    if result.get("billing_output"):
        fired.append("billing")
    if result.get("technical_output"):
        fired.append("technical")
    if result.get("account_output"):
        fired.append("account")
    if not fired and result.get("triage_output", {}).get("escalate_immediately"):
        fired.append("(none — triage escalated immediately)")
    return fired or ["(none)"]


def run_scenario(num: int, customer_id: str, ticket: str, expected: str) -> bool:
    profile = CUSTOMERS[customer_id]
    print(f"\n{'='*60}")
    print(f"Scenario {num}: {expected}")
    print(f"Customer: {customer_id} ({profile['name']}, {profile['tier']} tier)")
    print(f"Ticket: {ticket[:100]}...")
    print("-" * 60)

    try:
        result = run_graph(
            ticket_text=ticket,
            customer_id=customer_id,
            customer_profile=profile,
        )
    except Exception as e:
        print(f"ERROR: {e}")
        return False

    resolution = result.get("resolution_type", "unknown")
    agents = _agents_fired(result)
    response = result.get("final_response", "")
    escalation = result.get("escalation_output")

    print(f"Resolution:  {resolution}")
    print(f"Agents fired: {', '.join(agents)}")
    print(f"Response (first 300 chars):\n  {response[:300]}")

    if escalation:
        ticket_id = escalation.get("ticket_id", "N/A")
        priority = escalation.get("priority", "N/A")
        print(f"Ticket ID written to human_queue: {ticket_id}")
        print(f"Priority: {priority}")

    return True


def main():
    scenarios = [
        (
            1,
            "cus_001",
            "I was charged $299 this month but I requested a downgrade to the starter plan last week. "
            "This is really frustrating — can you fix this?",
            "resolved — billing agent applies credit",
        ),
        (
            2,
            "cus_001",
            "My GitHub integration stopped syncing. None of my issues are showing up in the dashboard "
            "and it's been broken for two days.",
            "resolved — technical agent cites docs",
        ),
        (
            3,
            "cus_002",
            "I was charged twice this month — I see two identical $49 charges on my statement. "
            "I need a refund for the duplicate charge.",
            "resolved — billing agent applies refund",
        ),
        (
            4,
            "cus_001",
            "I want to cancel my subscription immediately. Please process the cancellation today.",
            "escalated — account agent flags cancellation",
        ),
        (
            5,
            "cus_005",
            "I need help with my account. We're having some issues with the platform.",
            "escalated — triage immediately escalates (enterprise)",
        ),
    ]

    passed = 0
    for scenario in scenarios:
        ok = run_scenario(*scenario)
        if ok:
            passed += 1

    print(f"\n{'='*60}")
    print(f"Completed: {passed}/{len(scenarios)} scenarios ran without errors")
    print("Check Supabase human_queue table for escalated ticket IDs (scenarios 4 and 5).")

    if passed < len(scenarios):
        sys.exit(1)


if __name__ == "__main__":
    main()
