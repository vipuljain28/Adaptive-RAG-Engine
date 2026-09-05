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
        name="Amazon Nova Pro",
        model_id=PRIMARY_MODEL_ID,
        provider="amazon",
        tier="quality",
        description="Best quality & reasoning answers. Ideal for complex, multi-part questions.",
        max_tokens=4096,
        cost_per_1k_input=0.0008,
        cost_per_1k_output=0.0032,
        supports_vision=True,
        best_for=["complex questions", "policy interpretation",
                  "multi-part queries", "technical explanations"]
    ),
    "haiku": LLMModel(
        key="haiku",
        name="Amazon Nova Lite",
        model_id=SECONDARY_MODEL_ID,
        provider="amazon",
        tier="fast",
        description="Fast and ultra cost-efficient. Ideal for simple lookups.",
        max_tokens=4096,
        cost_per_1k_input=0.00006,
        cost_per_1k_output=0.00024,
        supports_vision=True,
        best_for=["simple lookups", "yes/no questions",
                  "short answers", "high-volume requests"]
    ),
    "vision": LLMModel(
        key="vision",
        name="Amazon Nova Pro (Vision)",
        model_id=VISION_MODEL_ID,
        provider="amazon",
        tier="vision",
        description="Vision-capable multimodal model. Required when an image is attached.",
        max_tokens=4096,
        cost_per_1k_input=0.0008,
        cost_per_1k_output=0.0032,
        supports_vision=True,
        best_for=["image analysis", "diagram questions",
                  "screenshot Q&A", "visual document queries"]
    ),
    "tinyllama": LLMModel(
        key="tinyllama",
        name="TinyLlama 1.1B (Self-Hosted)",
        model_id=os.getenv("TINYLLAMA_ENDPOINT", "http://localhost:8080"),
        provider="huggingface",
        tier="self-hosted",
        description="Open-source LLM running on EKS. No AWS token costs.",
        max_tokens=512,
        cost_per_1k_input=0.0,
        cost_per_1k_output=0.0,
        supports_vision=False,
        best_for=["offline/private queries", "cost demo", "open-source showcase"]
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
