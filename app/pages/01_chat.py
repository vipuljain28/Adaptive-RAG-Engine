"""
01_chat.py — Main RAG chat interface.

Features:
  - Text input via st.chat_input
  - Voice input via microphone (SpeechRecognition)
  - Image upload with automatic Vision model selection
  - Multi-model selection via sidebar (Auto / Nova Pro / Nova Lite / Vision / TinyLlama)
  - Per-message token, cost, and model display
  - Persistent conversations stored in SQLite
  - Past conversations listed in sidebar — click to resume, delete button to remove
"""

import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import streamlit as st
from app.config import KNOWLEDGE_BASE_ID, MAX_HISTORY_TURNS
from app.utils.rag_engine import run_rag_query
from app.utils.conversation_store import (
    init_db,
    create_conversation,
    save_message,
    get_all_conversations,
    get_conversation_messages,
    delete_conversation,
)
from app.components.sidebar import render_sidebar
from app.components.chat_ui import (
    render_message,
    render_sources,
    render_token_usage,
    render_chat_history,
)
from app.components.voice_input import render_voice_input
from app.components.image_input import render_image_upload

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Chat — Knowledge Assistant",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Initialise DB and session state ───────────────────────────────────────────
init_db()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "current_conversation_id" not in st.session_state:
    st.session_state.current_conversation_id = None

# ── Sidebar settings ──────────────────────────────────────────────────────────
settings = render_sidebar()

# ── Past Conversations Panel (rendered inside sidebar after render_sidebar) ───
with st.sidebar:
    st.divider()
    st.subheader("📂 Past Conversations")

    all_convs = get_all_conversations()
    if not all_convs:
        st.caption("No saved conversations yet.")
    else:
        for conv in all_convs[:15]:          # show last 15
            col_title, col_del = st.columns([4, 1])

            # Clicking the title loads that conversation
            if col_title.button(
                conv["title"][:35],
                key=f"load_{conv['id']}",
                use_container_width=True,
            ):
                msgs = get_conversation_messages(conv["id"])
                st.session_state.chat_history = msgs
                st.session_state.current_conversation_id = conv["id"]
                st.rerun()

            # Delete button
            if col_del.button("🗑️", key=f"del_{conv['id']}"):
                delete_conversation(conv["id"])
                if st.session_state.current_conversation_id == conv["id"]:
                    st.session_state.chat_history = []
                    st.session_state.current_conversation_id = None
                st.rerun()

# ── Main chat area ─────────────────────────────────────────────────────────────
st.title("💬 Knowledge Assistant")

# Guard: KB must be configured before the chat is usable
if not KNOWLEDGE_BASE_ID:
    st.warning(
        "**Knowledge Base not configured.**  \n"
        "Run `python scripts/setup_knowledge_base.py` then set "
        "`KNOWLEDGE_BASE_ID` in your `.env` file.",
        icon="⚠️",
    )
    st.stop()

# Render conversation history
render_chat_history(st.session_state.chat_history)

# ── Input row ─────────────────────────────────────────────────────────────────
st.divider()

# Image uploader and voice button sit above the chat input
img_col, voice_col = st.columns([6, 1])

with img_col:
    image_b64, image_media_type = render_image_upload()

with voice_col:
    voice_text = render_voice_input()

# Pre-fill chat input from voice transcript via session state
if voice_text:
    st.session_state["_voice_prefill"] = voice_text

user_input = st.chat_input("Ask a question about company documents…")

# Resolve final query: typed input takes priority over voice prefill
query = user_input or st.session_state.pop("_voice_prefill", None)

# ── Process query ─────────────────────────────────────────────────────────────
if query:
    has_image    = image_b64 is not None
    model_choice = settings["model_choice"]

    # Vision model is always forced when an image is attached
    if has_image:
        model_choice = "Vision"

    # Create a new conversation if there isn't one active
    if st.session_state.current_conversation_id is None:
        conv_id = create_conversation(query[:60])
        st.session_state.current_conversation_id = conv_id
    else:
        conv_id = st.session_state.current_conversation_id

    # ── Display and persist user message ──────────────────────────────────────
    user_msg = {"role": "user", "content": query, "has_image": has_image}
    st.session_state.chat_history.append(user_msg)
    render_message("user", query, has_image)
    save_message(conv_id, "user", query, has_image=int(has_image))

    # ── Call RAG pipeline ─────────────────────────────────────────────────────
    with st.spinner("🔍 Searching knowledge base and generating answer…"):
        result = run_rag_query(
            query            = query,
            model_choice     = model_choice,
            use_guardrails   = settings["use_guardrails"],
            image_b64        = image_b64,
            image_media_type = image_media_type,
            max_results      = settings["max_results"],
            conversation_id  = conv_id,
        )

    # ── Display result ────────────────────────────────────────────────────────
    if result["error"]:
        st.error(result["error"], icon="❌")
    else:
        assistant_msg = {
            "role":           "assistant",
            "content":        result["answer"],
            "model_id":       result["model_id"],
            "model_name":     result["model_name"],
            "input_tokens":   result["input_tokens"],
            "output_tokens":  result["output_tokens"],
            "cost_usd":       result["cost_usd"],
            "routing_reason": result["routing_reason"],
            "sources":        result["sources"],
        }
        st.session_state.chat_history.append(assistant_msg)

        render_message("assistant", result["answer"])
        render_sources(result["sources"])
        render_token_usage(
            input_tokens   = result["input_tokens"],
            output_tokens  = result["output_tokens"],
            model_name     = result["model_name"],
            cost_usd       = result["cost_usd"],
            routing_reason = result["routing_reason"],
        )

        # Persist assistant message to SQLite
        save_message(
            conv_id,
            "assistant",
            result["answer"],
            model_id       = result["model_id"],
            model_name     = result["model_name"],
            input_tokens   = result["input_tokens"],
            output_tokens  = result["output_tokens"],
            cost_usd       = result["cost_usd"],
            routing_reason = result["routing_reason"],
            sources        = result["sources"],
        )

    # Trim in-memory history to prevent unbounded growth
    max_msgs = MAX_HISTORY_TURNS * 2
    if len(st.session_state.chat_history) > max_msgs:
        st.session_state.chat_history = st.session_state.chat_history[-max_msgs:]
