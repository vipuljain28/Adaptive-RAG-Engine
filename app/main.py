"""
main.py — Knowledge Assistant entry point and dashboard.

This is the first page Streamlit shows when the app starts.
It displays:
  - System status (KB, Guardrail, LangFuse)
  - Aggregate usage stats from the SQLite store
  - Feature guide cards
  - Navigation hints

Run with:
    streamlit run app/main.py
"""

import os
import sys
import warnings
import streamlit as st

warnings.filterwarnings("ignore", category=UserWarning, module="boto3")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import (
    APP_TITLE,
    APP_ICON,
    KNOWLEDGE_BASE_ID,
    GUARDRAIL_ID,
    LANGFUSE_PUBLIC_KEY,
    PRIMARY_MODEL_ID,
    SECONDARY_MODEL_ID,
    VISION_MODEL_ID,
)
from app.utils.conversation_store import init_db, get_all_stats

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialise DB on startup (creates tables if they don't exist)
init_db()

# ── Header ────────────────────────────────────────────────────────────────────
st.title(f"{APP_ICON} {APP_TITLE}")
st.markdown(
    "Your AI-powered guide to company knowledge.  "
    "Ask questions in text, upload images, or use your voice."
)
st.divider()

# ── System status row ─────────────────────────────────────────────────────────
st.subheader("System Status")
col_kb, col_gr, col_lf, col_vs = st.columns(4)

with col_kb:
    if KNOWLEDGE_BASE_ID:
        st.success("Knowledge Base", icon="✅")
        st.caption(f"ID: `{KNOWLEDGE_BASE_ID[:20]}…`")
    else:
        st.error("Knowledge Base", icon="❌")
        st.caption("Run: `python scripts/setup_knowledge_base.py`")

with col_gr:
    if GUARDRAIL_ID:
        st.success("Guardrails", icon="🛡️")
        st.caption(f"ID: `{GUARDRAIL_ID[:20]}…`")
    else:
        st.warning("Guardrails", icon="⚠️")
        st.caption("Run: `python guardrails/setup_guardrail.py`")

with col_lf:
    if LANGFUSE_PUBLIC_KEY:
        st.success("LangFuse Tracing", icon="📡")
        st.caption("cloud.langfuse.com")
    else:
        st.warning("LangFuse Tracing", icon="📡")
        st.caption("Set keys in `.env` (Phase 5)")

with col_vs:
    st.info("Vector Store", icon="🔍")
    st.caption("OpenSearch Serverless")

st.divider()

# ── Usage stats row ───────────────────────────────────────────────────────────
st.subheader("Usage Summary")
stats = get_all_stats()

s1, s2, s3, s4, s5 = st.columns(5)
s1.metric("Conversations",    stats["total_conversations"])
s2.metric("Messages",         stats["total_messages"])
s3.metric("Input Tokens",     f"{stats['total_input_tokens']:,}")
s4.metric("Output Tokens",    f"{stats['total_output_tokens']:,}")
s5.metric("Total Cost",       f"${stats['total_cost_usd']:.4f}")

st.divider()

# ── Model info row ────────────────────────────────────────────────────────────
st.subheader("Available Models")
m1, m2, m3 = st.columns(3)

with m1:
    st.markdown("### 🧠 Amazon Nova Pro")
    st.caption("Best quality & reasoning for complex questions")
    st.caption(f"`{PRIMARY_MODEL_ID}`")
    st.caption("$0.0008 / 1K input · $0.0032 / 1K output")

with m2:
    st.markdown("### ⚡ Amazon Nova Lite")
    st.caption("Fast & ultra cost-efficient for simple lookups")
    st.caption(f"`{SECONDARY_MODEL_ID}`")
    st.caption("$0.00006 / 1K input · $0.00024 / 1K output")

with m3:
    st.markdown("### 👁️ Amazon Nova Pro (Vision)")
    st.caption("Multimodal vision processing — auto-selected when image attached")
    st.caption(f"`{VISION_MODEL_ID}`")
    st.caption("$0.0008 / 1K input · $0.0032 / 1K output")

st.divider()

# ── Feature cards ─────────────────────────────────────────────────────────────
st.subheader("Features")
f1, f2, f3 = st.columns(3)
f1.markdown("### 💬 Chat\nAsk questions in text. Answers grounded in company documents with source citations.")
f2.markdown("### 🎙️ Voice Input\nSpeak your question — transcribed automatically via Google Speech Recognition.")
f3.markdown("### 📎 Image Q&A\nUpload a diagram, screenshot, or photo and ask questions about it.")

f4, f5, f6 = st.columns(3)
f4.markdown("### 🔀 Smart Routing\nAuto mode picks Nova Pro or Nova Lite based on query complexity — saves ~75% cost.")
f5.markdown("### 💾 Saved Conversations\nAll chats saved locally to SQLite. Resume any past conversation from the sidebar.")
f6.markdown("### 📊 Analytics\nTrack token usage and cost per message, per model, and over time.")

st.divider()
st.caption(
    "Navigate using the sidebar: **Chat** to start asking questions · "
    "**Analytics** to view usage stats"
)
