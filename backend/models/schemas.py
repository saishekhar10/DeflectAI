from pydantic import BaseModel
from typing import Literal, Optional


class CustomerProfile(BaseModel):
    customer_id: str
    name: str
    email: str
    plan: Literal["free", "starter", "pro", "enterprise"]
    account_age_months: int
    tier: Literal["standard", "high_value", "enterprise"]
    open_ticket_count: int = 0


class TriageInput(BaseModel):
    ticket_text: str
    customer_profile: CustomerProfile


class TriageOutput(BaseModel):
    intents: list[Literal["billing", "technical", "account", "general"]]
    routing: list[Literal["billing_agent", "technical_agent", "account_agent", "escalation_agent"]]
    confidence: float  # 0.0 to 1.0
    urgency: Literal["low", "medium", "high"]
    reasoning: str  # brief explanation of routing decision
    escalate_immediately: bool  # True if enterprise tier or confidence < 0.6


class BillingOutput(BaseModel):
    finding: str
    action_taken: str  # e.g. "applied $50 credit" or "no action taken" or "escalated"
    response_draft: str
    escalate: bool
    escalation_reason: str = ""


class TechnicalOutput(BaseModel):
    diagnosis: str
    source_docs: list[str]  # list of source_urls returned by RAG
    response_draft: str
    escalate: bool
    escalation_reason: str = ""


class AccountOutput(BaseModel):
    action_taken: str
    response_draft: str
    escalate: bool
    escalation_reason: str = ""


class EscalationOutput(BaseModel):
    summary: str
    what_was_tried: str
    priority: Literal["low", "medium", "high"]
    customer_tier: str
    ticket_id: str
    original_ticket: str


class SynthesisOutput(BaseModel):
    final_response: str
    agents_used: list[str]
    resolution_type: Literal["resolved", "escalated"]
