import json
import sys
import time
from pathlib import Path

from backend.agents.triage_agent import triage
from backend.models.schemas import CustomerProfile, TriageInput

SUITE_PATH = Path(__file__).parent / "routing_test_suite.json"


def run_tests():
    with open(SUITE_PATH) as f:
        suite = json.load(f)

    total = len(suite)
    passed = 0
    failures = []

    for i, case in enumerate(suite, start=1):
        profile = CustomerProfile(**case["customer_profile"])
        input_ = TriageInput(ticket_text=case["ticket_text"], customer_profile=profile)
        expected_routing = set(case["expected_routing"])

        try:
            output = triage(input_)
            actual_routing = set(output.routing)
            ok = expected_routing.issubset(actual_routing)
        except Exception as e:
            ok = False
            actual_routing = set()
            output = None
            print(f"  [ERROR] #{i:02d}: {e}")

        time.sleep(0.5)

        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failures.append({
                "index": i,
                "ticket_text": case["ticket_text"][:80] + ("..." if len(case["ticket_text"]) > 80 else ""),
                "expected": sorted(expected_routing),
                "actual": sorted(actual_routing),
            })

        confidence_str = f"  confidence={output.confidence:.2f}" if output else ""
        print(f"[{status}] #{i:02d}{confidence_str}")
        print(f"       expected={sorted(expected_routing)}")
        print(f"       actual  ={sorted(actual_routing)}")
        if not ok:
            print(f"       text    ={case['ticket_text'][:80]}...")
        print()

    accuracy = passed / total * 100
    print("=" * 60)
    print(f"Total:    {passed}/{total} passed")
    print(f"Accuracy: {accuracy:.1f}%")

    if failures:
        print(f"\nFailed tickets ({len(failures)}):")
        for f in failures:
            print(f"  #{f['index']:02d} | expected={f['expected']} | actual={f['actual']}")
            print(f"       {f['ticket_text']}")

    print("=" * 60)

    if accuracy < 90.0:
        print("\nACCURACY BELOW 90% — FAILING")
        sys.exit(1)
    else:
        print("\nAll checks passed.")


if __name__ == "__main__":
    run_tests()
