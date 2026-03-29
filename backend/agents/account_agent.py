"""
account_agent.py — Account specialist agent for Deflect AI.

Takes triage output (ticket text + customer ID) and produces an AccountOutput
with the action taken, a response draft, and an escalation flag.
"""

import json
import os

import anthropic
import httpx
from dotenv import load_dotenv

load_dotenv()

from backend.models.schemas import AccountOutput

MODEL = "claude-sonnet-4-20250514"
BASE_URL = os.getenv("MOCK_API_URL", "http://localhost:8000")

_client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are an account management specialist for a SaaS company. Your job is to help customers with account changes such as plan upgrades, downgrades, and cancellations.

RULES:
1. ALWAYS call get_account_info first to understand the customer's current account status.
2. For plan upgrades or downgrades that aren't cancellations, you may call update_plan autonomously.
3. NEVER auto-process cancellations. Always call flag_cancellation and set escalate=true. This is non-negotiable.
4. Write response_draft in a professional, empathetic tone — acknowledge the customer's request and set clear expectations.
5. When finished, output ONLY valid JSON matching this exact schema — no markdown, no explanation:

{
  "action_taken": "<what action you took, e.g. 'updated plan to starter' or 'flagged cancellation for review'>",
  "response_draft": "<the customer-facing reply>",
  "escalate": <true|false>,
  "escalation_reason": "<reason if escalate is true, else empty string>"
}"""

TOOLS = [
    {
        "name": "get_account_info",
        "description": "Retrieve the customer's current account information including plan, seats, and billing contact.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "The customer ID (e.g. cus_001)"}
            },
            "required": ["customer_id"],
        },
    },
    {
        "name": "update_plan",
        "description": "Update the customer's subscription plan. Use for plan upgrades or downgrades (not cancellations).",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "The customer ID"},
                "new_plan": {"type": "string", "description": "The new plan name (e.g. 'starter', 'pro', 'enterprise')"},
            },
            "required": ["customer_id", "new_plan"],
        },
    },
    {
        "name": "flag_cancellation",
        "description": "Flag the customer's account for cancellation review. Always use this for cancellation requests — never auto-process cancellations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "The customer ID"}
            },
            "required": ["customer_id"],
        },
    },
]


def _execute_tool(name: str, inputs: dict) -> str:
    if name == "get_account_info":
        resp = httpx.get(f"{BASE_URL}/mock/account/{inputs['customer_id']}")
        return json.dumps(resp.json())

    if name == "update_plan":
        resp = httpx.post(
            f"{BASE_URL}/mock/account/{inputs['customer_id']}/plan",
            json={"new_plan": inputs["new_plan"]},
        )
        return json.dumps(resp.json())

    if name == "flag_cancellation":
        resp = httpx.post(f"{BASE_URL}/mock/account/{inputs['customer_id']}/cancel")
        return json.dumps(resp.json())

    return json.dumps({"error": f"unknown tool: {name}"})


def run_account_agent(ticket_text: str, customer_id: str) -> AccountOutput:
    messages: list[dict] = [
        {
            "role": "user",
            "content": (
                f"Customer ID: {customer_id}\n\n"
                f"Support ticket:\n{ticket_text}\n\n"
                "Handle this account request. Output your final answer as JSON only."
            ),
        }
    ]

    while True:
        response = _client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            text = next(
                (block.text for block in response.content if hasattr(block, "text")),
                "",
            )
            text = text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return AccountOutput.model_validate_json(text.strip())

        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = _execute_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })
        messages.append({"role": "user", "content": tool_results})
