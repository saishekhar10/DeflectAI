import json
import os

import anthropic
from dotenv import load_dotenv

from backend.models.schemas import TriageInput, TriageOutput

load_dotenv()

_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

_SYSTEM_PROMPT = """You are a support ticket triage system. Your job is to analyze incoming support tickets and classify them for routing.

You must output ONLY valid JSON — no prose, no markdown, no code blocks. The JSON must exactly match this schema:

{
  "intents": [...],
  "routing": [...],
  "confidence": 0.0,
  "urgency": "low" | "medium" | "high",
  "reasoning": "...",
  "escalate_immediately": true | false
}

## Intents
Extract ALL intents present in the ticket. Possible values (use only these):
- "billing" — charges, invoices, refunds, pricing, payment issues, plan costs
- "technical" — bugs, broken features, integrations not working, errors, export/import failures
- "account" — login issues, access problems, plan changes, cancellation, seat/user management
- "general" — unclear, generic questions, or anything that doesn't fit the above

## Routing
Map intents to routing targets. Use ALL that apply:
- "billing_agent" — for billing intent
- "technical_agent" — for technical intent
- "account_agent" — for account intent
- "escalation_agent" — for general intent, OR when confidence < 0.6, OR when customer tier is "enterprise"

## Critical routing rules
1. If the customer tier is "enterprise", route to ["escalation_agent"] ONLY and set escalate_immediately=true, regardless of intent.
2. If your confidence is below 0.6, route to ["escalation_agent"] ONLY and set escalate_immediately=true.
3. Multi-intent tickets should route to multiple agents (e.g., ["billing_agent", "technical_agent"]).
4. Otherwise set escalate_immediately=false.

## Urgency
Set urgency="high" if ANY of these are true:
- The ticket contains words like: urgent, broken, down, critical, losing data, not working, emergency, ASAP, immediately
- The customer tier is "enterprise"
Set urgency="medium" for clear issues without urgency signals.
Set urgency="low" for general questions or minor inconveniences.

## Confidence
Score 0.0–1.0 based on how clearly the ticket maps to a known intent:
- 0.9–1.0: Completely unambiguous (e.g., "I was double charged")
- 0.7–0.89: Clear intent with minor ambiguity
- 0.5–0.69: Somewhat unclear or vague — triggers escalation
- Below 0.5: Very unclear — triggers escalation

## Reasoning
Write a 1-2 sentence explanation of why you chose this routing."""


def triage(input: TriageInput) -> TriageOutput:
    profile = input.customer_profile
    user_message = f"""Support ticket:
{input.ticket_text}

Customer profile:
- Name: {profile.name}
- Email: {profile.email}
- Plan: {profile.plan}
- Tier: {profile.tier}
- Account age: {profile.account_age_months} months
- Open tickets: {profile.open_ticket_count}"""

    response = _client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=512,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw = response.content[0].text.strip()

    try:
        data = json.loads(raw)
        return TriageOutput(**data)
    except (json.JSONDecodeError, Exception) as e:
        raise ValueError(f"Failed to parse triage response as TriageOutput: {e}\nRaw response:\n{raw}")
