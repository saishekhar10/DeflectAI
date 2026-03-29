"""
run_evals.py — Eval runner for Deflect AI Phase 5.

Runs 10 representative tickets through the full LangGraph pipeline, grades
pass/fail per ticket, prints a summary with autonomous resolution rate, and
logs all results to a LangSmith dataset named "deflect-ai-evals".

Run with:
    PYTHONPATH=. python backend/tests/run_evals.py

Requirements:
  - .env at project root with ANTHROPIC_API_KEY, LANGSMITH_API_KEY, etc.
  - Supabase human_queue table created (escalated tickets write to it)
  - pip install langsmith
"""

import sys
import json
import os
from pathlib import Path

# Bootstrap sys.path so imports resolve from the project root
_project_root = Path(__file__).resolve().parents[2]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from dotenv import load_dotenv

load_dotenv()

from langsmith import Client
from backend.graph.graph import run_graph
from backend.mock_apis.mock_data import CUSTOMERS

# ---------------------------------------------------------------------------
# Load eval dataset
# ---------------------------------------------------------------------------

_dataset_path = Path(__file__).parent / "eval_dataset.json"
with open(_dataset_path) as f:
    eval_cases = json.load(f)

# ---------------------------------------------------------------------------
# LangSmith dataset setup
# ---------------------------------------------------------------------------

_ls_client = Client()
DATASET_NAME = "deflect-ai-evals"


def _get_or_create_dataset():
    existing = list(_ls_client.list_datasets(dataset_name=DATASET_NAME))
    if existing:
        return existing[0]
    return _ls_client.create_dataset(
        dataset_name=DATASET_NAME,
        description="Deflect AI eval suite — 10 representative support tickets",
    )


dataset = _get_or_create_dataset()

# ---------------------------------------------------------------------------
# Eval loop
# ---------------------------------------------------------------------------

results = []

print(f"Running {len(eval_cases)} eval cases...\n")

for case in eval_cases:
    case_id = case["id"]
    customer_id = case["customer_id"]
    ticket_text = case["ticket_text"]
    expected_resolution = case["expected_resolution_type"]
    expected_agents = set(case["expected_agents_used"])

    profile = CUSTOMERS[customer_id]
    tier = profile.get("tier", "standard")

    try:
        result = run_graph(
            ticket_text=ticket_text,
            customer_id=customer_id,
            customer_profile=profile,
            langsmith_extra={
                "metadata": {
                    "customer_id": customer_id,
                    "customer_tier": tier,
                    "eval_case_id": case_id,
                }
            },
        )
        actual_resolution = result.get("resolution_type", "unknown")
        actual_agents = set(result.get("agents_used") or [])
        resolution_time_ms = result.get("resolution_time_ms", 0)

        resolution_pass = actual_resolution == expected_resolution
        agents_pass = expected_agents.issubset(actual_agents)
        passed = resolution_pass and agents_pass

    except Exception as exc:
        actual_resolution = "error"
        actual_agents = set()
        resolution_time_ms = 0
        resolution_pass = False
        agents_pass = False
        passed = False
        print(f"  Case {case_id:2d}: ERROR — {exc}")

    status = "PASS" if passed else "FAIL"
    results.append(
        {
            "id": case_id,
            "passed": passed,
            "actual_resolution": actual_resolution,
            "expected_resolution": expected_resolution,
            "actual_agents": sorted(actual_agents),
            "expected_agents": sorted(expected_agents),
            "resolution_time_ms": resolution_time_ms,
        }
    )

    print(f"Case {case_id:2d}: {status}  ({resolution_time_ms}ms)")
    if not passed:
        if not resolution_pass:
            print(
                f"         resolution : expected={expected_resolution!r}, "
                f"got={actual_resolution!r}"
            )
        if not agents_pass:
            missing = expected_agents - actual_agents
            print(f"         agents missing: {sorted(missing)}")

    # Log result to LangSmith dataset
    _ls_client.create_example(
        inputs={
            "ticket_text": ticket_text,
            "customer_id": customer_id,
        },
        outputs={
            "resolution_type": actual_resolution,
            "agents_used": sorted(actual_agents),
            "passed": passed,
            "resolution_time_ms": resolution_time_ms,
        },
        dataset_id=dataset.id,
    )

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

total_passed = sum(1 for r in results if r["passed"])
resolved_count = sum(1 for r in results if r["actual_resolution"] == "resolved")
autonomous_rate = resolved_count / len(results) * 100

print()
print("=" * 50)
print(f"Total: {total_passed}/{len(results)} passed")
print(f"Autonomous Resolution Rate: {autonomous_rate:.0f}%  (Target: 75%+)")
if autonomous_rate >= 75:
    print("TARGET MET")
else:
    print("BELOW TARGET")
print("=" * 50)
print(f"\nResults logged to LangSmith dataset: {DATASET_NAME!r}")
