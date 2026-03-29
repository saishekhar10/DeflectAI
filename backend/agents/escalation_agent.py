"""
escalation_agent.py — Escalation specialist agent for Deflect AI.

Receives the original ticket, customer profile, and outputs from any specialist
agents that have already run. Produces a structured EscalationOutput for the
human review queue.
"""

import json
import os
import uuid

import anthropic
from dotenv import load_dotenv

load_dotenv()

from backend.models.schemas import EscalationOutput

MODEL = "claude-sonnet-4-20250514"

_client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are an escalation coordinator for a SaaS customer support team. Your job is to prepare a clear, structured escalation ticket for a human support agent.

You will receive:
- The original support ticket text
- The customer's profile (tier, plan, etc.)
- Outputs from any specialist agents that already ran (billing, technical, account)
- A pre-generated ticket_id UUID

Your output MUST be ONLY valid JSON matching this exact schema — no markdown, no explanation:

{
  "summary": "<1-3 sentence human-readable summary of the customer's issue>",
  "what_was_tried": "<what specialist agents found or attempted — if none ran, say 'No automated resolution attempted'>",
  "priority": "<low|medium|high>",
  "customer_tier": "<the customer's tier from the profile>",
  "ticket_id": "<the exact UUID provided to you — do not modify it>",
  "original_ticket": "<the verbatim original ticket text>"
}

## Priority assignment rules (apply in order, first match wins):
1. "high" — if customer tier is "enterprise" OR urgency is "high" in triage output
2. "medium" — if the ticket contains frustrated or negative language (e.g. "unacceptable", "terrible", "demand", "immediately", "still broken", "this is ridiculous")
3. "low" — all other cases"""


def run_escalation_agent(
    ticket_text: str,
    customer_profile: dict,
    agent_outputs: dict,
) -> EscalationOutput:
    """
    Produce a structured escalation ticket for human review.

    Args:
        ticket_text: The original support ticket text.
        customer_profile: Customer profile dict (tier, plan, name, etc.).
        agent_outputs: Dict of specialist outputs keyed by agent name
                       (e.g. {"billing": {...}, "account": {...}}).

    Returns:
        EscalationOutput with summary, priority, ticket_id, etc.
    """
    ticket_id = str(uuid.uuid4())

    user_message = f"""Prepare an escalation ticket for human review.

Ticket ID (use this exactly): {ticket_id}

Original ticket:
{ticket_text}

Customer profile:
{json.dumps(customer_profile, indent=2)}

Specialist agent outputs (may be empty if none ran):
{json.dumps(agent_outputs, indent=2)}

Output ONLY the JSON escalation ticket."""

    response = _client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    return EscalationOutput.model_validate_json(raw)
