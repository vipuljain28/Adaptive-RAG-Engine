"""
Test suite for LangFuse observability integration.
Verifies graceful fallback when keys are missing and tracer functionality when keys are set.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from observability.langfuse_tracer import RagTracer, is_enabled

def test_tracer():
    print("Testing LangFuse Tracer...")
    print(f"Tracing enabled status: {is_enabled()}")

    # Initialize tracer
    tracer = RagTracer(
        conversation_id="test-conv-123",
        query="What is the remote work policy?",
        user_id="test-user-1",
        has_image=False,
        routing_strategy="auto_complexity",
        routing_reason="Auto -> Haiku: simple query",
    )

    # Test retrieval span
    tracer.start_retrieval(query="What is the remote work policy?", kb_id="TEST_KB", max_results=5)
    tracer.end_retrieval(chunks=[{"source": "hr_policy.txt", "score": 0.88}])

    # Test generation span
    tracer.start_generation(
        model_id="anthropic.claude-3-haiku-20240307-v1:0",
        prompt="Role: Assistant\nContext: ...\nQuery: ...",
        model_name="Claude 3 Haiku",
    )
    tracer.end_generation(
        answer="Employees may work remotely up to 2 days per week.",
        input_tokens=450,
        output_tokens=85,
        cost_usd=0.0002,
    )

    # Test trace finalization
    tracer.end_trace(success=True, answer="Employees may work remotely up to 2 days per week.")
    tracer.flush()

    print("PASS: RagTracer executed without exceptions!")

if __name__ == "__main__":
    test_tracer()
