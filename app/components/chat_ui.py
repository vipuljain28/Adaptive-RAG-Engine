"""
Reusable chat rendering helpers for the Knowledge Assistant.

All functions take plain Python values (strings, dicts, lists) and render
them into the Streamlit UI.  They have no side effects beyond rendering.
"""

import streamlit as st


def render_message(role: str, content: str, has_image: bool = False) -> None:
    """
    Render a single chat bubble.

    Args:
        role:      "user" or "assistant"
        content:   Message text (markdown supported)
        has_image: If True and role=="user", shows an image-attached caption.
    """
    with st.chat_message(role):
        if has_image and role == "user":
            st.caption("📎 Image attached to this message")
        st.markdown(content)


def render_sources(sources: list[dict]) -> None:
    """
    Render retrieved source documents in a collapsible expander.

    Args:
        sources: List of dicts with keys: source (S3 URI), score (float), content (str)
    """
    if not sources:
        return

    with st.expander(f"📄 View Sources ({len(sources)})", expanded=False):
        for i, s in enumerate(sources, 1):
            filename   = s.get("source", "").split("/")[-1] or "unknown"
            score      = s.get("score", 0.0)
            content    = s.get("content", "")

            st.markdown(f"**{i}. {filename}**")
            cols = st.columns([1, 3])
            cols[0].caption(f"Relevance: **{score:.2f}**")
            cols[1].caption(f"`{s.get('source', '')}`")

            if content:
                with st.expander("Show excerpt", expanded=False):
                    st.text(content[:400] + ("…" if len(content) > 400 else ""))

            if i < len(sources):
                st.divider()


def render_token_usage(
    input_tokens:   int,
    output_tokens:  int,
    model_name:     str,
    cost_usd:       float,
    routing_reason: str = "",
) -> None:
    """
    Render a compact 4-column metrics row below each assistant message.

    Args:
        input_tokens:   Tokens sent to the model
        output_tokens:  Tokens returned by the model
        model_name:     Human-readable model name
        cost_usd:       Calculated cost in USD
        routing_reason: Why this model was chosen (shown as caption)
    """
    cols = st.columns(4)
    cols[0].metric("Input tokens",  f"{input_tokens:,}")
    cols[1].metric("Output tokens", f"{output_tokens:,}")
    cols[2].metric("Cost",          f"${cost_usd:.5f}")
    cols[3].metric("Model",         model_name)

    if routing_reason:
        st.caption(f"🔀 {routing_reason}")


def render_chat_history(history: list[dict]) -> None:
    """
    Render all messages in the chat history list.

    Args:
        history: List of message dicts. Each dict must have:
                   role    (str)  — "user" or "assistant"
                   content (str)  — message text
                 Optional keys for assistant messages:
                   has_image      (bool)
                   sources        (list[dict])
                   input_tokens   (int)
                   output_tokens  (int)
                   model_name     (str)
                   cost_usd       (float)
                   routing_reason (str)
    """
    for item in history:
        role      = item.get("role", "user")
        content   = item.get("content", "")
        has_image = bool(item.get("has_image", False))

        render_message(role, content, has_image)

        # For assistant messages, show sources and token metrics inline
        if role == "assistant":
            sources = item.get("sources", [])
            if sources:
                render_sources(sources)

            if item.get("input_tokens") or item.get("output_tokens"):
                render_token_usage(
                    input_tokens   = item.get("input_tokens",   0),
                    output_tokens  = item.get("output_tokens",  0),
                    model_name     = item.get("model_name",     ""),
                    cost_usd       = item.get("cost_usd",       0.0),
                    routing_reason = item.get("routing_reason", ""),
                )
