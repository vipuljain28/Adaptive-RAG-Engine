"""
Demonstrates AI Gateway routing decisions across all three strategies.
No AWS calls — purely tests the routing logic.

Usage:
    python gateway/test_routing.py

Output: routing decision table for all test cases.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from gateway.router import route

# (label, query, user_selection, has_image, expected_strategy, expected_tier)
TEST_CASES = [
    (
        "Image attached -> forced Vision",
        "What does this diagram show?",
        "Auto", True,
        "image_forced", "vision"
    ),
    (
        "User picked Sonnet explicitly",
        "What is the leave policy?",
        "Quality (Claude Sonnet)", False,
        "user_selection", "quality"
    ),
    (
        "User picked Haiku explicitly",
        "List the DataSync Pro features.",
        "Fast (Claude Haiku)", False,
        "user_selection", "fast"
    ),
    (
        "Auto - short simple query -> Haiku",
        "What is the annual leave allowance?",
        "Auto", False,
        "auto_complexity", "fast"
    ),
    (
        "Auto - long complex query -> Sonnet",
        "Can you explain in detail the difference between the remote work policy and "
        "the office attendance policy, including what exceptions are allowed?",
        "Auto", False,
        "auto_complexity", "quality"
    ),
    (
        "Auto - why + step-by-step -> Sonnet",
        "Why does DataSync Pro show error E101 and what are the step-by-step "
        "troubleshooting procedures I should follow to resolve it?",
        "Auto", False,
        "auto_complexity", "quality"
    ),
    (
        "Auto - simple what-is -> Haiku",
        "What are the error codes?",
        "Auto", False,
        "auto_complexity", "fast"
    ),
    (
        "User picked Vision explicitly",
        "Analyse this screenshot.",
        "Vision", False,
        "user_selection", "vision"
    ),
]


def main():
    print("=" * 75)
    print("  AI GATEWAY — ROUTING DEMONSTRATION")
    print("=" * 75)

    passed = 0
    for label, query, selection, has_image, exp_strategy, exp_tier in TEST_CASES:
        result = route(query, selection, has_image)
        ok = (result["strategy"] == exp_strategy and
              result["model"].tier == exp_tier)
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1

        print(f"\n  {label}")
        print(f"  Query     : {query[:65]}")
        print(f"  Selection : {selection}  |  Image: {has_image}")
        print(f"  -> Model   : {result['model_name']}")
        print(f"  -> Strategy: {result['strategy']}")
        print(f"  -> Reason  : {result['reason']}")
        print(f"  -> Model ID: {result['model_id']}")
        print(f"  RESULT: {status}")

    print("\n" + "=" * 75)
    print(f"  Results: {passed}/{len(TEST_CASES)} passed")


if __name__ == "__main__":
    main()
