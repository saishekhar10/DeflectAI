"""
account_mock.py — Mock Account DB router for local development and testing.

Endpoints:
    GET  /mock/account/{customer_id}              → account info
    POST /mock/account/{customer_id}/plan         → update plan
    POST /mock/account/{customer_id}/cancel       → flag cancellation
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.mock_apis.mock_data import CUSTOMERS

router = APIRouter(prefix="/mock/account")

_NOT_FOUND = JSONResponse(status_code=404, content={"error": "customer not found"})


class PlanUpdateRequest(BaseModel):
    new_plan: str


@router.get("/{customer_id}")
def get_account(customer_id: str):
    if customer_id not in CUSTOMERS:
        return _NOT_FOUND
    c = CUSTOMERS[customer_id]
    return {
        "customer_id": customer_id,
        "name": c["name"],
        "email": c["email"],
        "plan": c["plan"],
        "plan_price": c["plan_price"],
        "seats": c["seats"],
        "tier": c["tier"],
        "account_age_months": c["account_age_months"],
        "billing_contact": c["email"],
    }


@router.post("/{customer_id}/plan")
def update_plan(customer_id: str, body: PlanUpdateRequest):
    if customer_id not in CUSTOMERS:
        return _NOT_FOUND
    old_plan = CUSTOMERS[customer_id]["plan"]
    CUSTOMERS[customer_id]["plan"] = body.new_plan
    return {
        "customer_id": customer_id,
        "old_plan": old_plan,
        "new_plan": body.new_plan,
        "status": "updated",
    }


@router.post("/{customer_id}/cancel")
def flag_cancellation(customer_id: str):
    if customer_id not in CUSTOMERS:
        return _NOT_FOUND
    return {"status": "flagged_for_review"}
