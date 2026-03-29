"""
billing_agent.py — Billing specialist agent for Deflect AI.

Takes triage output (ticket text + customer ID) and produces a BillingOutput
with a response draft, any action taken, and an escalation flag.
"""

import json
import os

import anthropic
import httpx
from dotenv import load_dotenv

load_dotenv()

from backend.models.schemas import BillingOutput

MODEL = "claude-sonnet-4-20250514"
BASE_URL = os.getenv("MOCK_API_URL", "http://localhost:8000")

_client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are a billing support specialist for a SaaS company. Your job is to investigate customer billing issues and resolve them where possible.

RULES:
1. Always start by calling get_customer_profile, get_invoice_history, and get_subscription_status to gather full context.
2. If the customer tier is "enterprise", you MUST call flag_for_escalation — enterprise accounts always require human review.
3. You may apply credits autonomously ONLY if the amount is $100 or less. For amounts over $100, call flag_for_escalation instead.
4. If a downgrade was requested but the customer was still charged the higher amount this cycle, apply a courtesy credit for the price difference (if <= $100).
5. Write response_draft in a professional, empathetic tone — acknowledge the issue, explain what you did, and set expectations.
6. When you have finished all tool calls and are ready to respond, output ONLY valid JSON matching this exact schema — no markdown, no explanation:

{
  "finding": "<what you discovered about the billing situation>",
  "action_taken": "<what action you took, e.g. 'applied $50 credit' or 'no action taken' or 'escalated'>",
  "response_draft": "<the customer-facing reply>",
  "escalate": <true|false>,
  "escalation_reason": "<reason if escalate is true, else empty string>"
}"""

TOOLS = [
    {
        "name": "get_customer_profile",
        "description": "Retrieve the customer's profile including their tier, plan, and contact info.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "The customer ID (e.g. cus_001)"}
            },
            "required": ["customer_id"],
        },
    },
    {
        "name": "get_invoice_history",
        "description": "Retrieve the customer's invoice history.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "The customer ID"}
            },
            "required": ["customer_id"],
        },
    },
    {
        "name": "get_subscription_status",
        "description": "Retrieve the customer's current subscription status, including any pending downgrades.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "The customer ID"}
            },
            "required": ["customer_id"],
        },
    },
    {
        "name": "apply_credit",
        "description": "Apply a credit to the customer's account. Only use for amounts <= $100.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "The customer ID"},
                "amount": {"type": "number", "description": "Credit amount in dollars"},
            },
            "required": ["customer_id", "amount"],
        },
    },
    {
        "name": "flag_for_escalation",
        "description": "Flag this ticket for human review. Use when amount > $100, customer is enterprise tier, or the issue requires manual intervention.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "Why this ticket needs human review"}
            },
            "required": ["reason"],
        },
    },
]


def _execute_tool(name: str, inputs: dict) -> str:
    if name == "get_customer_profile":
        resp = httpx.get(f"{BASE_URL}/mock/stripe/customer/{inputs['customer_id']}")
        return json.dumps(resp.json())

    if name == "get_invoice_history":
        resp = httpx.get(f"{BASE_URL}/mock/stripe/invoices/{inputs['customer_id']}")
        return json.dumps(resp.json())

    if name == "get_subscription_status":
        resp = httpx.get(f"{BASE_URL}/mock/stripe/subscription/{inputs['customer_id']}")
        return json.dumps(resp.json())

    if name == "apply_credit":
        amount = inputs["amount"]
        if amount > 100:
            return json.dumps({"error": "amount exceeds auto-credit limit of $100 — escalate instead"})
        resp = httpx.post(
            f"{BASE_URL}/mock/stripe/credit/{inputs['customer_id']}",
            json={"amount": amount},
        )
        return json.dumps(resp.json())

    if name == "flag_for_escalation":
        return json.dumps({"status": "flagged", "reason": inputs["reason"]})

    return json.dumps({"error": f"unknown tool: {name}"})


def run_billing_agent(ticket_text: str, customer_id: str) -> BillingOutput:
    messages: list[dict] = [
        {
            "role": "user",
            "content": (
                f"Customer ID: {customer_id}\n\n"
                f"Support ticket:\n{ticket_text}\n\n"
                "Investigate this billing issue and resolve it where possible. "
                "Output your final answer as JSON only."
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
            # Extract JSON from the final text block
            text = next(
                (block.text for block in response.content if hasattr(block, "text")),
                "",
            )
            # Strip markdown code fences if present
            text = text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return BillingOutput.model_validate_json(text.strip())

        # Process tool calls
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
