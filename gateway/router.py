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
            signals.append("complexity keyword matched")
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
      "Auto" | "Auto (Smart Routing)" | "Quality (Amazon Nova Pro)" | "Fast (Amazon Nova Lite)" | "Vision"
    """
    mapping = {
        "Quality (Amazon Nova Pro)":       "sonnet",
        "Quality (Claude Sonnet)":        "sonnet",
        "Fast (Amazon Nova Lite)":        "haiku",
        "Fast (Claude Haiku)":            "haiku",
        "Vision":                         "vision",
        "Self-Hosted (TinyLlama)":        "tinyllama",
        "Self-Hosted (TinyLlama) — EKS":  "tinyllama",
    }
    key    = mapping.get(selection, "sonnet")
    model  = get_model(key)
    reason = f"User selected: {model.name}"
    return model, "user_selection", reason


def _route_auto_complexity(query: str) -> tuple[LLMModel, str, str]:
    analysis = _score_complexity(query)
    if analysis["is_complex"]:
        model  = get_model("sonnet")
        reason = (f"Auto → Nova Pro: complex query "
                  f"(score {analysis['score']}, {', '.join(analysis['signals'])})")
    else:
        model  = get_model("haiku")
        reason = (f"Auto → Nova Lite: simple query "
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
    elif user_selection not in ("Auto", "Auto (Smart Routing)"):
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
