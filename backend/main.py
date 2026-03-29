"""
main.py — FastAPI application entry point for Deflect AI backend.

Start with:
    uvicorn backend.main:app --reload --port 8000
"""

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI

from backend.mock_apis.stripe_mock import router as stripe_router
from backend.mock_apis.account_mock import router as account_router

app = FastAPI(title="Deflect AI Backend")

app.include_router(stripe_router)
app.include_router(account_router)


@app.get("/health")
def health():
    return {"status": "ok"}
