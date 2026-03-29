from typing import TypedDict, Optional


class GraphState(TypedDict):
    # Input
    ticket_text: str
    customer_id: str
    customer_profile: dict

    # Triage output
    triage_output: Optional[dict]

    # Specialist agent outputs
    billing_output: Optional[dict]
    technical_output: Optional[dict]
    account_output: Optional[dict]

    # Final outputs
    escalation_output: Optional[dict]
    synthesis_output: Optional[dict]

    final_response: str
    resolution_type: str
