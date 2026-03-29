from __future__ import annotations

import operator
from typing import Annotated, TypedDict, Optional


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

    # Accumulated list of agents that ran — uses operator.add reducer so parallel
    # specialist nodes (billing + technical) can both append without overwriting.
    agents_used: Annotated[list[str], operator.add]
