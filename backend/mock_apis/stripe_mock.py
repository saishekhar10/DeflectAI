"""
stripe_mock.py — Mock Stripe API router for local development and testing.

Endpoints:
    GET  /mock/stripe/customer/{customer_id}      → customer profile
    GET  /mock/stripe/invoices/{customer_id}      → invoice history
    GET  /mock/stripe/subscription/{customer_id}  → subscription status
    POST /mock/stripe/credit/{customer_id}        → apply a credit
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.mock_apis.mock_data import CUSTOMERS, INVOICES, SUBSCRIPTIONS, CREDITS

router = APIRouter(prefix="/mock/stripe")

_NOT_FOUND = JSONResponse(status_code=404, content={"error": "customer not found"})


class CreditRequest(BaseModel):
    amount: float


@router.get("/customer/{customer_id}")
def get_customer(customer_id: str):
    if customer_id not in CUSTOMERS:
        return _NOT_FOUND
    return CUSTOMERS[customer_id]


@router.get("/invoices/{customer_id}")
def get_invoices(customer_id: str):
    if customer_id not in INVOICES:
        return _NOT_FOUND
    return INVOICES[customer_id]


@router.get("/subscription/{customer_id}")
def get_subscription(customer_id: str):
    if customer_id not in SUBSCRIPTIONS:
        return _NOT_FOUND
    return SUBSCRIPTIONS[customer_id]


@router.post("/credit/{customer_id}")
def apply_credit(customer_id: str, body: CreditRequest):
    if customer_id not in CUSTOMERS:
        return _NOT_FOUND
    CREDITS[customer_id] = CREDITS.get(customer_id, 0.0) + body.amount
    return {
        "customer_id": customer_id,
        "credit_applied": body.amount,
        "total_credits": CREDITS[customer_id],
    }
