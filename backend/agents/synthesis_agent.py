"""
synthesis_agent.py — Synthesis agent for Deflect AI.

Receives the original ticket and response drafts from one or more specialist
agents, then merges them into a single coherent customer-facing reply.
"""

import json
import os

import anthropic
from dotenv import load_dotenv

load_dotenv()

from backend.models.schemas import SynthesisOutput

MODEL = "claude-sonnet-4-20250514"

_client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are a customer communications specialist for a SaaS company. Your job is to take draft responses from internal specialist teams and merge them into a single, polished customer-facing reply.

You will receive the original ticket and one or more specialist response drafts.

Your output MUST be ONLY valid JSON matching this exact schema — no markdown, no explanation:

{
  "final_response": "<the single merged customer-facing reply>",
  "agents_used": ["<agent1>", "<agent2>", ...],
  "resolution_type": "resolved"
}

## Rules:
1. Merge ALL specialist drafts into one coherent reply — address every issue raised.
2. Remove redundancy: don't repeat the same information twice.
3. NEVER reveal internal agent names, routing logic, or system architecture to the customer.
4. Use "agents_used" to list which specialists contributed (e.g. ["billing", "technical"]).
5. Maintain a professional, empathetic tone throughout.
6. Keep the response concise — resolve all issues in a single message.
7. Always set resolution_type to "resolved"."""


def run_synthesis_agent(
    ticket_text: str,
    agent_outputs: dict,
) -> SynthesisOutput:
    """
    Merge specialist response drafts into a single customer reply.

    Args:
        ticket_text: The original support ticket text.
        agent_outputs: Dict of specialist outputs keyed by agent name.
                       Each value should have a "response_draft" field.

    Returns:
        SynthesisOutput with the merged final_response, agents_used, and resolution_type.
    """
    # Collect response drafts
    drafts = {}
    for agent_name, output in agent_outputs.items():
        if output and isinstance(output, dict) and output.get("response_draft"):
            drafts[agent_name] = output["response_draft"]

    user_message = f"""Merge the following specialist drafts into a single customer reply.

Original ticket:
{ticket_text}

Specialist response drafts:
{json.dumps(drafts, indent=2)}

Output ONLY the JSON synthesis."""

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

    return SynthesisOutput.model_validate_json(raw)
