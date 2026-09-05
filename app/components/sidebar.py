"""
Sidebar component for the Knowledge Assistant.

Renders all controls in the Streamlit sidebar and returns a settings dict
that the chat page uses to configure each query.
"""

import streamlit as st
from app.config import GUARDRAIL_ID, KNOWLEDGE_BASE_ID


# Maps the display label shown in the selectbox to the internal key
# used by rag_engine._resolve_model() and (Phase 3) gateway/router.py
_MODEL_MAP: dict[str, str] = {
    "Auto (Smart Routing)":                  "Auto",
    "Amazon Nova Pro  — Quality":            "Quality (Amazon Nova Pro)",
    "Amazon Nova Lite — Fast & Cheap":       "Fast (Amazon Nova Lite)",
    "Amazon Nova Pro  — Vision (Image Q&A)": "Vision",
    "Self-Hosted TinyLlama  — EKS":          "Self-Hosted (TinyLlama)",
}


def render_sidebar() -> dict:
    """
    Render the full sidebar and return a settings dict with keys:
        model_choice    (str)  — internal routing key
        use_guardrails  (bool) — whether to apply Bedrock Guardrail
        max_results     (int)  — number of KB chunks to retrieve
    """
    with st.sidebar:
        st.title("⚙️ Settings")
        st.divider()

        # ── Model Selection ──────────────────────────────────────────────────
        st.subheader("🤖 Model")
        display_choice = st.selectbox(
            "Select Model",
            options=list(_MODEL_MAP.keys()),
            index=0,
            help=(
                "Auto: app picks based on query complexity. "
                "Vision: required for image questions. "
                "TinyLlama: self-hosted on EKS (Phase 6)."
            ),
        )
        model_choice = _MODEL_MAP[display_choice]

        # Routing explanation (only for Auto)
        if model_choice == "Auto":
            with st.expander("🔀 How Auto routing works", expanded=False):
                st.markdown("""
                | Signal | Score |
                |---|---|
                | Word count > 20 | +3 |
                | Word count 12–20 | +1 |
                | Keywords: compare, explain, policy, why | +2 |
                | Simple pattern (what is, list) | −1 |

                **Score ≥ 3** → Amazon Nova Pro (quality)  
                **Score < 3** → Amazon Nova Lite (fast & cheap)  
                **Image attached** → Vision model (always forced)
                """)

        # TinyLlama health check (Phase 6/7)
        if model_choice == "Self-Hosted (TinyLlama)":
            _show_tinyllama_status()

        st.divider()

        # ── Safety ──────────────────────────────────────────────────────────
        st.subheader("🛡️ Safety")
        use_guardrails = st.checkbox(
            "Enable Guardrails",
            value=True,
            help="Blocks PII leakage and prompt injection attempts via Bedrock Guardrails.",
        )
        if GUARDRAIL_ID:
            st.success("Guardrail active", icon="✅")
        else:
            st.warning("Run `guardrails/setup_guardrail.py`", icon="⚠️")

        st.divider()

        # ── Knowledge Base ────────────────────────────────────────────────────
        st.subheader("📚 Knowledge Base")
        if KNOWLEDGE_BASE_ID:
            st.success("KB connected", icon="✅")
            st.caption(f"`{KNOWLEDGE_BASE_ID[:20]}…`")
        else:
            st.error("KB not configured", icon="❌")
        max_results = st.slider("Sources to retrieve", min_value=1, max_value=10, value=5)

        st.divider()

        # ── Conversation Management ──────────────────────────────────────────
        st.subheader("💬 Conversations")
        if st.button("➕ New Conversation", use_container_width=True):
            st.session_state.current_conversation_id = None
            st.session_state.chat_history = []
            st.rerun()

        if st.button("🗑️ Clear Current Chat", use_container_width=True):
            st.session_state.chat_history = []
            st.session_state.current_conversation_id = None
            st.rerun()

        st.divider()

        # ── About ────────────────────────────────────────────────────────────
        with st.expander("ℹ️ About"):
            st.markdown("""
            **Knowledge Assistant** v1.0  
            Built on Amazon Bedrock + RAG  
            Documents indexed via Bedrock Knowledge Bases  
            Vector store: OpenSearch Serverless  
            """)

    return {
        "model_choice":   model_choice,
        "use_guardrails": use_guardrails,
        "max_results":    max_results,
    }


def _show_tinyllama_status():
    """Show TinyLlama server health status in the sidebar."""
    try:
        from bonus.eks.adapter import health_check
        if health_check():
            st.success("EKS TinyLlama reachable", icon="🤖")
        else:
            st.warning(
                "TinyLlama server not reachable.  \n"
                "Deploy to EKS or run:  \n"
                "`kubectl port-forward svc/tinyllama-tinyllama 8080:8080`",
                icon="⚠️",
            )
    except ImportError:
        st.info("TinyLlama adapter not yet installed (Phase 6).", icon="ℹ️")
    except Exception:
        st.warning("TinyLlama server unreachable.", icon="⚠️")
