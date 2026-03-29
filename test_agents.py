import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()

from backend.agents.billing_agent import run_billing_agent
from backend.agents.technical_agent import run_technical_agent
from backend.agents.account_agent import run_account_agent

print("=== Billing Agent ===")
result = run_billing_agent(
    "I was charged $299 this month but I requested a downgrade last week",
    "cus_001"
)
print("Finding:", result.finding)
print("Action:", result.action_taken)
print("Escalate:", result.escalate)
print("Draft:", result.response_draft[:200])

print("\n=== Technical Agent ===")
result = run_technical_agent(
    "My GitHub integration stopped syncing with my issues",
    "cus_001"
)
print("Diagnosis:", result.diagnosis)
print("Sources:", result.source_docs)
print("Escalate:", result.escalate)
print("Draft:", result.response_draft[:200])

print("\n=== Account Agent ===")
result = run_account_agent(
    "I want to cancel my subscription",
    "cus_001"
)
print("Action:", result.action_taken)
print("Escalate:", result.escalate)
print("Draft:", result.response_draft[:200])
