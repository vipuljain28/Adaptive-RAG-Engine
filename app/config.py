"""
Central configuration for the Knowledge Assistant.
All settings are loaded from the .env file via python-dotenv.
Every other module imports constants from here — never from os.getenv directly.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── AWS ───────────────────────────────────────────────────────────────────────
AWS_REGION          = os.getenv("AWS_REGION",       "us-east-1")
AWS_ACCOUNT_ID      = os.getenv("AWS_ACCOUNT_ID",   "")

# ── Bedrock Models ─────────────────────────────────────────────────────────────
PRIMARY_MODEL_ID    = os.getenv("PRIMARY_MODEL_ID",   "amazon.nova-pro-v1:0")
SECONDARY_MODEL_ID  = os.getenv("SECONDARY_MODEL_ID", "amazon.nova-lite-v1:0")
VISION_MODEL_ID     = os.getenv("VISION_MODEL_ID",    "amazon.nova-pro-v1:0")
EMBEDDING_MODEL_ID  = os.getenv("EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")

# ── Knowledge Base ─────────────────────────────────────────────────────────────
KNOWLEDGE_BASE_ID   = os.getenv("KNOWLEDGE_BASE_ID",  "")
KNOWLEDGE_BASE_ARN  = os.getenv("KNOWLEDGE_BASE_ARN", "")
KB_MAX_RESULTS      = int(os.getenv("KB_MAX_RESULTS", "5"))

# ── Guardrail ──────────────────────────────────────────────────────────────────
GUARDRAIL_ID        = os.getenv("GUARDRAIL_ID",      "")
GUARDRAIL_VERSION   = os.getenv("GUARDRAIL_VERSION", "DRAFT")

# ── S3 ────────────────────────────────────────────────────────────────────────
S3_BUCKET_NAME      = os.getenv("S3_BUCKET_NAME",    "")

# ── LangFuse ───────────────────────────────────────────────────────────────────
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
LANGFUSE_HOST       = os.getenv("LANGFUSE_HOST",       "https://cloud.langfuse.com")

# ── Self-hosted LLM (Phase 6/7) ────────────────────────────────────────────────
TINYLLAMA_ENDPOINT  = os.getenv("TINYLLAMA_ENDPOINT", "http://localhost:8080")
TINYLLAMA_TIMEOUT   = int(os.getenv("TINYLLAMA_TIMEOUT", "60"))

# ── App constants (never change these via .env) ────────────────────────────────
APP_TITLE           = "Knowledge Assistant"
APP_ICON            = "🧠"
MAX_HISTORY_TURNS   = 20
DEFAULT_MAX_TOKENS  = 1024
DEFAULT_TEMPERATURE = 0.1

# ── Model cost table — USD per 1,000 tokens ────────────────────────────────────
# Source: AWS Bedrock pricing page (us-east-1), September 2026
# Keys are the Bedrock model ID strings.
MODEL_COSTS = {
    # ── Amazon Nova family (active models for this project) ──────────────────
    "amazon.nova-pro-v1:0": {
        "input":  0.0008,
        "output": 0.0032,
        "name":   "Amazon Nova Pro",
    },
    "amazon.nova-lite-v1:0": {
        "input":  0.00006,
        "output": 0.00024,
        "name":   "Amazon Nova Lite",
    },
    "amazon.nova-micro-v1:0": {
        "input":  0.000035,
        "output": 0.00014,
        "name":   "Amazon Nova Micro",
    },
    # ── Anthropic Claude (kept for reference / phase doc compatibility) ───────
    "anthropic.claude-3-sonnet-20240229-v1:0": {
        "input":  0.003,
        "output": 0.015,
        "name":   "Claude 3 Sonnet",
    },
    "anthropic.claude-3-haiku-20240307-v1:0": {
        "input":  0.00025,
        "output": 0.00125,
        "name":   "Claude 3 Haiku",
    },
}
# Vision model uses the same pricing as Nova Pro (same model ID)
MODEL_COSTS["amazon.nova-pro-v1:0 (vision)"] = {
    "input":  0.0008,
    "output": 0.0032,
    "name":   "Amazon Nova Pro (Vision)",
}
# Ensure VISION_MODEL_ID key always resolves correctly even if same as PRIMARY
if VISION_MODEL_ID not in MODEL_COSTS:
    MODEL_COSTS[VISION_MODEL_ID] = {
        "input":  0.0008,
        "output": 0.0032,
        "name":   "Amazon Nova Pro (Vision)",
    }

# ── SQLite DB path ─────────────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "conversations.db")
