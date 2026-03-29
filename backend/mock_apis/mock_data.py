"""
mock_data.py — Hardcoded customer/invoice/subscription data for mock APIs.

All data is module-level. CREDITS is an in-memory store that resets on restart.
"""

CUSTOMERS: dict[str, dict] = {
    "cus_001": {
        "customer_id": "cus_001",
        "name": "Sarah Chen",
        "email": "sarah@acme.com",
        "plan": "pro",
        "plan_price": 299,
        "account_age_months": 14,
        "tier": "standard",
        "seats": 5,
    },
    "cus_002": {
        "customer_id": "cus_002",
        "name": "James Park",
        "email": "james@startup.io",
        "plan": "starter",
        "plan_price": 49,
        "account_age_months": 3,
        "tier": "standard",
        "seats": 2,
    },
    "cus_003": {
        "customer_id": "cus_003",
        "name": "Maria Torres",
        "email": "maria@agency.co",
        "plan": "pro",
        "plan_price": 299,
        "account_age_months": 8,
        "tier": "high_value",
        "seats": 12,
    },
    "cus_004": {
        "customer_id": "cus_004",
        "name": "Tom Bradley",
        "email": "tom@personal.com",
        "plan": "free",
        "plan_price": 0,
        "account_age_months": 2,
        "tier": "standard",
        "seats": 1,
    },
    "cus_005": {
        "customer_id": "cus_005",
        "name": "Linda Wu",
        "email": "linda@bigcorp.com",
        "plan": "enterprise",
        "plan_price": 999,
        "account_age_months": 24,
        "tier": "enterprise",
        "seats": 50,
    },
}

INVOICES: dict[str, list[dict]] = {
    "cus_001": [
        {"id": "inv_001", "amount": 299, "date": "2026-03-19", "status": "paid", "description": "Pro plan - March"},
        {"id": "inv_002", "amount": 299, "date": "2026-02-19", "status": "paid", "description": "Pro plan - February"},
        {"id": "inv_003", "amount": 299, "date": "2026-01-19", "status": "paid", "description": "Pro plan - January"},
    ],
    "cus_002": [
        {"id": "inv_004", "amount": 49, "date": "2026-03-01", "status": "paid", "description": "Starter plan - March"},
        {"id": "inv_005", "amount": 49, "date": "2026-03-01", "status": "paid", "description": "Starter plan - March"},
    ],
    "cus_003": [
        {"id": "inv_006", "amount": 299, "date": "2026-03-15", "status": "paid", "description": "Pro plan - March"},
        {"id": "inv_007", "amount": 299, "date": "2026-02-15", "status": "paid", "description": "Pro plan - February"},
    ],
    "cus_004": [],
    "cus_005": [
        {"id": "inv_008", "amount": 999, "date": "2026-03-01", "status": "paid", "description": "Enterprise plan - March"},
    ],
}

SUBSCRIPTIONS: dict[str, dict] = {
    "cus_001": {
        "current_plan": "pro",
        "current_price": 299,
        "billing_cycle_start": "2026-03-19",
        "next_billing_date": "2026-04-19",
        "downgrade_requested": True,
        "downgrade_to": "starter",
        "downgrade_requested_date": "2026-03-20",
    },
    "cus_002": {
        "current_plan": "starter",
        "current_price": 49,
        "billing_cycle_start": "2026-03-01",
        "next_billing_date": "2026-04-01",
        "downgrade_requested": False,
        "downgrade_to": None,
        "downgrade_requested_date": None,
    },
    "cus_003": {
        "current_plan": "pro",
        "current_price": 299,
        "billing_cycle_start": "2026-03-15",
        "next_billing_date": "2026-04-15",
        "downgrade_requested": False,
        "downgrade_to": None,
        "downgrade_requested_date": None,
    },
    "cus_004": {
        "current_plan": "free",
        "current_price": 0,
        "billing_cycle_start": None,
        "next_billing_date": None,
        "downgrade_requested": False,
        "downgrade_to": None,
        "downgrade_requested_date": None,
    },
    "cus_005": {
        "current_plan": "enterprise",
        "current_price": 999,
        "billing_cycle_start": "2026-03-01",
        "next_billing_date": "2026-04-01",
        "downgrade_requested": False,
        "downgrade_to": None,
        "downgrade_requested_date": None,
    },
}

# In-memory credits store — resets on server restart
CREDITS: dict[str, float] = {}
