from pydantic import BaseModel
from typing import Literal


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
