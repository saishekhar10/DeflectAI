"""
technical_agent.py — Technical specialist agent for Deflect AI.

Takes triage output (ticket text + customer ID) and produces a TechnicalOutput
with a diagnosis, relevant source docs, a response draft, and an escalation flag.
"""

import json
import os

import anthropic
from dotenv import load_dotenv

load_dotenv()

from backend.models.schemas import TechnicalOutput
from backend.rag.search import rag_search as _rag_search

MODEL = "claude-sonnet-4-20250514"

_client = anthropic.Anthropic()

KNOWN_ISSUES = [
    {
        "id": "KI-001",
        "title": "CSV export fails for >10k rows",
        "keyword": "csv",
        "status": "in_progress",
        "eta": "2026-04-10",
    },
    {
        "id": "KI-002",
        "title": "Slack integration disconnects after OAuth refresh",
        "keyword": "slack",
        "status": "investigating",
        "eta": "TBD",
    },
    {
        "id": "KI-003",
        "title": "Webhook delivery delayed under high load",
        "keyword": "webhook",
        "status": "resolved",
        "eta": "deployed 2026-03-15",
    },
]

SYSTEM_PROMPT = """You are a technical support specialist for a SaaS company. Your job is to diagnose technical issues using the knowledge base and known bug tracker.

RULES:
1. ALWAYS call rag_search first with the most relevant query from the ticket. Extract source_urls from the results to populate source_docs.
2. Also call check_known_issues with relevant keywords (e.g. "csv", "slack", "webhook", "github", "integration").
3. If ALL similarity scores from rag_search are below 0.35, set escalate=true — the knowledge base doesn't have enough relevant information to answer confidently.
4. Cite source_urls in the response_draft where relevant (e.g. "For more details, see: <url>").
5. If a known issue matches, include the issue status and ETA in your response.
6. Write response_draft in a professional, empathetic tone.
7. When finished, output ONLY valid JSON matching this exact schema — no markdown, no explanation:

{
  "diagnosis": "<what you believe is causing the issue>",
  "source_docs": ["<source_url_1>", "<source_url_2>", ...],
  "response_draft": "<the customer-facing reply>",
  "escalate": <true|false>,
  "escalation_reason": "<reason if escalate is true, else empty string>"
}"""

TOOLS = [
    {
        "name": "rag_search",
        "description": "Search the product knowledge base for documentation relevant to the customer's issue. Returns chunks with similarity scores.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query based on the customer's issue"}
            },
            "required": ["query"],
        },
    },
    {
        "name": "check_known_issues",
        "description": "Check the known bug tracker for issues matching a keyword. Use keywords like 'csv', 'slack', 'webhook', 'github', 'integration', etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "Keyword to search for in known issues"}
            },
            "required": ["keyword"],
        },
    },
]


def _execute_tool(name: str, inputs: dict) -> str:
    if name == "rag_search":
        results = _rag_search(query=inputs["query"], top_k=5)
        return json.dumps(results)

    if name == "check_known_issues":
        keyword = inputs["keyword"].lower()
        matches = [
            issue for issue in KNOWN_ISSUES
            if keyword in issue["keyword"].lower() or issue["keyword"].lower() in keyword
        ]
        if not matches:
            return json.dumps({"matches": [], "message": "No known issues found for this keyword."})
        return json.dumps({"matches": matches})

    return json.dumps({"error": f"unknown tool: {name}"})


def run_technical_agent(ticket_text: str, customer_id: str) -> TechnicalOutput:
    messages: list[dict] = [
        {
            "role": "user",
            "content": (
                f"Customer ID: {customer_id}\n\n"
                f"Support ticket:\n{ticket_text}\n\n"
                "Diagnose this technical issue using the knowledge base and known bug tracker. "
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
            text = next(
                (block.text for block in response.content if hasattr(block, "text")),
                "",
            )
            text = text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return TechnicalOutput.model_validate_json(text.strip())

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
