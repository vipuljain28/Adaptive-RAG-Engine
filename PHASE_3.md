# Phase 3 — AI Gateway & LLM Routing

## Context: What This Capstone Is
An AI-powered Knowledge Assistant built on AWS using Amazon Bedrock. Employees ask questions
about internal company documents. The app supports text queries, voice input, and image
uploads. All answers are grounded in documents stored in a Bedrock Knowledge Base.

## What Previous Phases Already Built — Do Not Recreate
```
app/config.py                      — config from .env, MODEL_COSTS table, VISION_MODEL_ID
app/utils/bedrock_client.py        — boto3 client factory (cached)
app/utils/rag_engine.py            — retrieve + generate pipeline with image support
app/utils/prompt_templates.py      — RCTFC prompts: build_rag_prompt, build_vision_prompt
app/utils/conversation_store.py   — SQLite persistent conversation storage
app/components/sidebar.py          — 4-option model selector, guardrail status
app/components/chat_ui.py          — chat renderers with token/cost metrics row
app/components/voice_input.py      — microphone transcription
app/components/image_input.py      — image upload + base64 encode
app/pages/01_chat.py               — main chat page (text + voice + image)
app/pages/02_analytics.py          — token/cost analytics charts
app/main.py                        — dashboard entry point
guardrails/setup_guardrail.py      — creates Bedrock Guardrail via boto3
guardrails/test_guardrail.py       — 7-case PII + injection demo
```

**No AWS Console is used anywhere. All resources are created via boto3 scripts or Terraform.**

---

## Phase 3 Scope
Build a complete AI Gateway that:
1. Routes text queries to the right LLM based on user selection or auto-complexity analysis
2. Forces the Vision model when an image is attached
3. Provides a central model registry so new models can be added in one place
4. Exposes routing decisions in the UI (which model, which strategy, why)
5. Includes a standalone demo script for the capstone submission screenshots

---

## Requirement Coverage
- **Requirement 4 (10 marks):** AI Gateway / LLM Routing — routes to at least 2 LLMs with a meaningful strategy

---

## Routing Strategies
| Strategy | Trigger | Model Selected |
|---|---|---|
| image_forced | Image attached | VISION_MODEL_ID (Claude 3 Sonnet) |
| user_selection | User picks explicit model | That model |
| auto_complexity | User picks "Auto" + no image | Complexity score decides |

### Auto Complexity Scoring
| Condition | Score Added |
|---|---|
| Query word count > 20 | +3 |
| Query word count 12–20 | +1 |
| Keywords: compare, explain, difference, why, how does, step-by-step | +2 |
| Keywords: policy, regulation, compliance, procedure | +2 |
| Starts with: what is, list, how many | -1 |
| Score ≥ 3 | → Sonnet (quality) |
| Score < 3 | → Haiku (fast) |

---

## Models in Registry
| Key | Model ID | Tier | Cost Input/1k | Cost Output/1k |
|---|---|---|---|---|
| sonnet | anthropic.claude-3-sonnet-20240229-v1:0 | quality | $0.003 | $0.015 |
| haiku | anthropic.claude-3-haiku-20240307-v1:0 | fast | $0.00025 | $0.00125 |
| vision | anthropic.claude-3-sonnet-20240229-v1:0 | vision | $0.003 | $0.015 |

---

## Project Root
`G:\learn ai\modules\capstone`

---

## New Files to Create in Phase 3
```
gateway/
├── __init__.py
├── llm_registry.py      # Central model catalog — dataclass + dict
├── router.py            # All routing logic (3 strategies)
└── test_routing.py      # Standalone demo showing routing decisions
```

## Files to Modify in Phase 3
```
app/utils/rag_engine.py       — replace direct model_id logic with gateway router call
app/components/sidebar.py     — add routing explanation expander (already has model selector)
app/pages/01_chat.py          — pass model_choice string to rag_engine; display routing badge
```

---

## File Specifications

### `gateway/llm_registry.py`
Central catalog of every available model. Adding a new model only requires a new entry here.

```python
"""
LLM Registry — single source of truth for all available models.
All other modules import model metadata from here.
"""
from dataclasses import dataclass, field
from typing import Optional
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.config import PRIMARY_MODEL_ID, SECONDARY_MODEL_ID, VISION_MODEL_ID


@dataclass
class LLMModel:
    key: str                       # Registry key: "sonnet", "haiku", "vision"
    name: str                      # Human-readable: "Claude 3 Sonnet"
    model_id: str                  # Bedrock model ID string
    provider: str                  # "anthropic"
    tier: str                      # "quality" | "fast" | "vision"
    description: str               # One-line description for UI tooltip
    max_tokens: int                # Max output tokens
    cost_per_1k_input: float       # USD per 1000 input tokens
    cost_per_1k_output: float      # USD per 1000 output tokens
    supports_vision: bool = False  # True if model accepts image input
    best_for: list = field(default_factory=list)


# ── Registry dict ─────────────────────────────────────────────────────────────
MODELS: dict[str, LLMModel] = {
    "sonnet": LLMModel(
        key="sonnet",
        name="Claude 3 Sonnet",
        model_id=PRIMARY_MODEL_ID,
        provider="anthropic",
        tier="quality",
        description="Best quality answers. Ideal for complex, multi-part questions.",
        max_tokens=4096,
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.015,
        supports_vision=False,
        best_for=["complex questions", "policy interpretation",
                  "multi-part queries", "technical explanations"]
    ),
    "haiku": LLMModel(
        key="haiku",
        name="Claude 3 Haiku",
        model_id=SECONDARY_MODEL_ID,
        provider="anthropic",
        tier="fast",
        description="Fast and cost-efficient. Ideal for simple lookups.",
        max_tokens=4096,
        cost_per_1k_input=0.00025,
        cost_per_1k_output=0.00125,
        supports_vision=False,
        best_for=["simple lookups", "yes/no questions",
                  "short answers", "high-volume requests"]
    ),
    "vision": LLMModel(
        key="vision",
        name="Claude 3 Sonnet (Vision)",
        model_id=VISION_MODEL_ID,
        provider="anthropic",
        tier="vision",
        description="Vision-capable model. Required when an image is attached.",
        max_tokens=4096,
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.015,
        supports_vision=True,
        best_for=["image analysis", "diagram questions",
                  "screenshot Q&A", "visual document queries"]
    ),
}


def get_model(key: str) -> LLMModel:
    """Return model by registry key. Raises KeyError if not found."""
    if key not in MODELS:
        raise KeyError(f"Model key '{key}' not in registry. Available: {list(MODELS.keys())}")
    return MODELS[key]


def list_models() -> list[LLMModel]:
    """Return all models as a list."""
    return list(MODELS.values())


def get_model_by_id(model_id: str) -> Optional[LLMModel]:
    """Reverse-lookup a model by its Bedrock model ID string."""
    for m in MODELS.values():
        if m.model_id == model_id:
            return m
    return None


def get_vision_models() -> list[LLMModel]:
    """Return all models that support image input."""
    return [m for m in MODELS.values() if m.supports_vision]
```

---

### `gateway/router.py`
All routing logic. Three strategies in one file with a single public entry point `route()`.

```python
"""
AI Gateway Router

Three routing strategies:
  1. image_forced     — image attached → always Vision model
  2. user_selection   — user picked an explicit model in the UI
  3. auto_complexity  — user chose "Auto" → complexity score decides

Public API:
  result = route(query, user_selection, has_image)
  result["model_id"]       # Bedrock model ID
  result["model_name"]     # Human-readable name
  result["strategy"]       # which strategy was used
  result["reason"]         # human-readable explanation for UI display
"""
import re
from gateway.llm_registry import get_model, LLMModel


# ── Complexity scoring constants ───────────────────────────────────────────────
_COMPLEX_PATTERNS = [
    r"(compare|comparison|difference between|vs\.?|versus)",
    r"(explain|describe|elaborate|in detail|detailed)",
    r"(why|how does|what causes|what happens when|what is the impact)",
    r"(step[- ]by[- ]step|procedure|process for|walk me through)",
    r"(policy|regulation|compliance|legal|requirement|obligation)",
    r"\band\b.{5,40}\band\b",             # "X and Y and Z" style multi-part
]
_SIMPLE_PATTERNS = [
    r"^(what is|what are|who is|where is|when is)\b",
    r"^(how many|how much)\b",
    r"^(list|give me|show me|tell me)\b.{0,25}$",
]
_COMPLEX_SCORE_THRESHOLD = 3


def _score_complexity(query: str) -> dict:
    """
    Score a query for complexity.
    Returns {"score": int, "is_complex": bool, "word_count": int, "signals": list[str]}
    """
    q     = query.lower().strip()
    words = q.split()
    score = 0
    signals = []

    # Word count contribution
    if len(words) > 20:
        score += 3
        signals.append(f"long query ({len(words)} words)")
    elif len(words) > 12:
        score += 1
        signals.append(f"medium query ({len(words)} words)")

    # Complex pattern matches
    for pattern in _COMPLEX_PATTERNS:
        if re.search(pattern, q):
            score += 2
            signals.append(f"complexity keyword matched")
            break   # count once per query

    # Simple pattern reduces score
    for pattern in _SIMPLE_PATTERNS:
        if re.search(pattern, q):
            score -= 1
            signals.append("simple question pattern")
            break

    return {
        "score":      max(0, score),
        "is_complex": score >= _COMPLEX_SCORE_THRESHOLD,
        "word_count": len(words),
        "signals":    signals,
    }


# ── Strategy implementations ───────────────────────────────────────────────────

def _route_image_forced() -> tuple[LLMModel, str, str]:
    model  = get_model("vision")
    reason = "Vision model selected automatically — image attached to query"
    return model, "image_forced", reason


def _route_user_selection(selection: str) -> tuple[LLMModel, str, str]:
    """
    Maps the sidebar dropdown string to a registry key.
    sidebar.py returns one of these exact strings:
      "Auto"  |  "Quality (Claude Sonnet)"  |  "Fast (Claude Haiku)"  |  "Vision"
    """
    mapping = {
        "Quality (Claude Sonnet)": "sonnet",
        "Fast (Claude Haiku)":     "haiku",
        "Vision":                  "vision",
    }
    key    = mapping.get(selection, "sonnet")
    model  = get_model(key)
    reason = f"User selected: {model.name}"
    return model, "user_selection", reason


def _route_auto_complexity(query: str) -> tuple[LLMModel, str, str]:
    analysis = _score_complexity(query)
    if analysis["is_complex"]:
        model  = get_model("sonnet")
        reason = (f"Auto → Sonnet: complex query "
                  f"(score {analysis['score']}, {', '.join(analysis['signals'])})")
    else:
        model  = get_model("haiku")
        reason = (f"Auto → Haiku: simple query "
                  f"(score {analysis['score']}, {analysis['word_count']} words)")
    return model, "auto_complexity", reason


# ── Public entry point ─────────────────────────────────────────────────────────

def route(query: str, user_selection: str = "Auto", has_image: bool = False) -> dict:
    """
    Route a query to the appropriate model.

    Args:
        query:          The user's question text
        user_selection: Value from sidebar dropdown.
                        One of: "Auto" | "Quality (Claude Sonnet)" |
                                "Fast (Claude Haiku)" | "Vision"
        has_image:      True if the user attached an image to this query

    Returns dict:
        {
            "model":      LLMModel dataclass instance
            "model_id":   str  — pass to Bedrock invoke_model
            "model_name": str  — display in UI
            "strategy":   str  — "image_forced" | "user_selection" | "auto_complexity"
            "reason":     str  — human-readable explanation for UI display
        }
    """
    # Strategy 1: image always overrides everything
    if has_image:
        model, strategy, reason = _route_image_forced()

    # Strategy 2: explicit user choice
    elif user_selection != "Auto":
        model, strategy, reason = _route_user_selection(user_selection)

    # Strategy 3: auto routing by complexity
    else:
        model, strategy, reason = _route_auto_complexity(query)

    return {
        "model":      model,
        "model_id":   model.model_id,
        "model_name": model.name,
        "strategy":   strategy,
        "reason":     reason,
    }
```


---

### `gateway/test_routing.py`
Standalone demo script. No AWS calls. Run to produce routing decision screenshots.

```python
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
        "Image attached → forced Vision",
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
        "Auto — short simple query → Haiku",
        "What is the annual leave allowance?",
        "Auto", False,
        "auto_complexity", "fast"
    ),
    (
        "Auto — long complex query → Sonnet",
        "Can you explain in detail the difference between the remote work policy and "
        "the office attendance policy, including what exceptions are allowed?",
        "Auto", False,
        "auto_complexity", "quality"
    ),
    (
        "Auto — why + step-by-step → Sonnet",
        "Why does DataSync Pro show error E101 and what are the step-by-step "
        "troubleshooting procedures I should follow to resolve it?",
        "Auto", False,
        "auto_complexity", "quality"
    ),
    (
        "Auto — simple what-is → Haiku",
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
        status = "✅ PASS" if ok else "❌ FAIL"
        if ok:
            passed += 1

        print(f"\n  {label}")
        print(f"  Query     : {query[:65]}")
        print(f"  Selection : {selection}  |  Image: {has_image}")
        print(f"  → Model   : {result['model_name']}")
        print(f"  → Strategy: {result['strategy']}")
        print(f"  → Reason  : {result['reason']}")
        print(f"  → Model ID: {result['model_id']}")
        print(f"  {status}")

    print("\n" + "=" * 75)
    print(f"  Results: {passed}/{len(TEST_CASES)} passed")
    print("  Take a screenshot of this output for your submission.")

if __name__ == "__main__":
    main()
```

---

### Modify `app/utils/rag_engine.py` — integrate gateway router

Replace the placeholder model resolution logic added in Phase 1 with the real gateway router.

Changes required:

```python
# 1. Add import at top of rag_engine.py (after existing imports):
from gateway.router import route as gateway_route

# 2. Update run_rag_query signature:
# OLD: def run_rag_query(query, model_choice="Auto", use_guardrails=True,
#                        image_b64=None, image_media_type=None, max_results=5)
# NEW: same signature — no change needed

# 3. Inside run_rag_query, replace the model_id resolution block with:
has_image      = image_b64 is not None
routing_result = gateway_route(
    query=query,
    user_selection=model_choice,
    has_image=has_image
)
model_id       = routing_result["model_id"]
model_name     = routing_result["model_name"]
routing_reason = routing_result["reason"]

# 4. Ensure the return dict includes:
return {
    "answer":         ...,
    "sources":        ...,
    "input_tokens":   ...,
    "output_tokens":  ...,
    "model_id":       model_id,
    "model_name":     model_name,        # from routing_result
    "routing_reason": routing_reason,    # from routing_result
    "cost_usd":       ...,               # already calculated from MODEL_COSTS
    "error":          None
}
```

---

### Modify `app/components/sidebar.py` — add routing info expander

Inside `render_sidebar()`, after the model selectbox, add this block:

```python
# Routing strategy explanation (only shown in Auto mode)
if model_choice == "Auto (Smart Routing)":
    with st.expander("🔀 How Auto routing works", expanded=False):
        st.markdown("""
        The gateway scores each query for complexity:

        | Signal | Score |
        |---|---|
        | Word count > 20 | +3 |
        | Word count 12–20 | +1 |
        | Keywords: compare, explain, why, policy | +2 |
        | Simple pattern (what is, list) | -1 |

        **Score ≥ 3** → Claude 3 Sonnet (quality)  
        **Score < 3** → Claude 3 Haiku (fast & cheap)  
        **Image attached** → Vision model (always forced)
        """)
```

No other changes to sidebar.py needed.

---

### Modify `app/pages/01_chat.py` — show routing badge

After `render_sources()`, the routing reason is already displayed via `render_token_usage()`.
Confirm the call passes `routing_reason` from `result`:

```python
render_token_usage(
    result["input_tokens"],
    result["output_tokens"],
    result["model_name"],
    result["cost_usd"],
    result["routing_reason"]   # ← ensure this is passed
)
```

No other changes needed in 01_chat.py.

---

## Order to Create / Modify Files
1. `gateway/__init__.py` (empty)
2. `gateway/llm_registry.py`
3. `gateway/router.py`
4. `gateway/test_routing.py`
5. Modify `app/utils/rag_engine.py` — replace model resolution with `gateway_route()`
6. Modify `app/components/sidebar.py` — add routing explanation expander
7. Confirm `app/pages/01_chat.py` passes `routing_reason` to `render_token_usage()`

---

## How to Run (for the human)
```bash
# Test routing logic — no AWS credentials needed
python gateway/test_routing.py

# Then launch app and test with the UI
streamlit run app/main.py
```

---

## Definition of Done
- `gateway/test_routing.py` runs and all 8 test cases show ✅ PASS
- Image attached → Vision model always selected regardless of sidebar setting
- "Auto" + short query → Haiku selected, routing reason shown in UI
- "Auto" + long/complex query → Sonnet selected, routing reason shown in UI
- Explicit model picks → that model used, routing reason says "User selected"
- Routing reason visible below every assistant response in the chat UI
- No hardcoded model IDs anywhere except `app/config.py` and `gateway/llm_registry.py`
