"""
02_analytics.py — Token Usage & Cost Analytics Dashboard.

Shows per-message and aggregate metrics pulled from the SQLite conversation store.
All charts are built with Plotly and rendered via st.plotly_chart.

Charts:
  1. Cost per message       (bar, coloured by model)
  2. Token usage per message (stacked bar: input + output)
  3. Model usage breakdown   (pie)
  4. Daily cost trend        (line)
  5. Cost by conversation    (sortable table)
"""

import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from app.utils.conversation_store import (
    init_db,
    get_all_stats,
    get_all_conversations,
    get_conversation_stats,
    get_all_messages_flat,
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Analytics — Knowledge Assistant",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_db()
st.title("📊 Token Usage & Cost Analytics")

# ── Load data ─────────────────────────────────────────────────────────────────
stats    = get_all_stats()
messages = get_all_messages_flat(limit=200)
convs    = get_all_conversations()

# ── Summary metrics row ───────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Conversations",    stats["total_conversations"])
c2.metric("Total Messages",   stats["total_messages"])
c3.metric("Input Tokens",     f"{stats['total_input_tokens']:,}")
c4.metric("Output Tokens",    f"{stats['total_output_tokens']:,}")
c5.metric("Total Cost (USD)", f"${stats['total_cost_usd']:.4f}")

st.divider()

# ── Guard: nothing to show yet ────────────────────────────────────────────────
if not messages:
    st.info(
        "No messages yet. Start chatting to see analytics here.",
        icon="💡",
    )
    st.stop()

# ── Build dataframe from messages ─────────────────────────────────────────────
df = pd.DataFrame(messages)
df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
df["msg_index"]  = range(1, len(df) + 1)
df["model_name"] = df["model_name"].fillna("Unknown")
df["content_short"] = df["content"].str[:40] + "…"

# ── Chart 1: Cost per Message ─────────────────────────────────────────────────
st.subheader("💰 Cost per Message")
fig1 = px.bar(
    df,
    x="msg_index",
    y="cost_usd",
    color="model_name",
    labels={
        "msg_index": "Message #",
        "cost_usd":  "Cost (USD)",
        "model_name": "Model",
    },
    hover_data={"content_short": True, "cost_usd": ":.6f"},
    title="Cost (USD) per assistant message",
    color_discrete_sequence=px.colors.qualitative.Set2,
)
fig1.update_layout(
    xaxis_title="Message #",
    yaxis_title="Cost (USD)",
    legend_title="Model",
    hovermode="x unified",
)
st.plotly_chart(fig1, use_container_width=True)

# ── Chart 2: Token usage per message ─────────────────────────────────────────
st.subheader("🔢 Token Usage per Message")
fig2 = go.Figure()
fig2.add_trace(go.Bar(
    x=df["msg_index"],
    y=df["input_tokens"],
    name="Input tokens",
    marker_color="#4C78A8",
    hovertemplate="Msg #%{x}<br>Input: %{y:,}<extra></extra>",
))
fig2.add_trace(go.Bar(
    x=df["msg_index"],
    y=df["output_tokens"],
    name="Output tokens",
    marker_color="#F58518",
    hovertemplate="Msg #%{x}<br>Output: %{y:,}<extra></extra>",
))
fig2.update_layout(
    barmode="stack",
    xaxis_title="Message #",
    yaxis_title="Tokens",
    legend_title="Token type",
    title="Input + Output tokens per message",
    hovermode="x unified",
)
st.plotly_chart(fig2, use_container_width=True)

# ── Chart 3: Model usage breakdown ───────────────────────────────────────────
st.subheader("🤖 Model Usage Breakdown")
model_counts = stats.get("messages_by_model", {})

if model_counts:
    fig3 = px.pie(
        names=list(model_counts.keys()),
        values=list(model_counts.values()),
        title="Messages by model",
        color_discrete_sequence=px.colors.qualitative.Set2,
        hole=0.35,
    )
    fig3.update_traces(textposition="inside", textinfo="percent+label")
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("No model usage data yet.")

# ── Chart 4: Daily cost trend ─────────────────────────────────────────────────
st.subheader("📈 Daily Cost Trend")
daily = stats.get("daily_costs", [])

if daily:
    daily_df = pd.DataFrame(daily)
    fig4 = px.line(
        daily_df,
        x="date",
        y="cost_usd",
        markers=True,
        labels={"date": "Date", "cost_usd": "Cost (USD)"},
        title="Daily spend (USD)",
        hover_data={"message_count": True},
        color_discrete_sequence=["#54A24B"],
    )
    fig4.update_layout(
        xaxis_title="Date",
        yaxis_title="Cost (USD)",
        hovermode="x unified",
    )
    st.plotly_chart(fig4, use_container_width=True)
else:
    st.info("Not enough data for a daily trend yet.")

# ── Chart 5: Cost by conversation (table) ─────────────────────────────────────
st.subheader("📋 Cost by Conversation")

if convs:
    rows = []
    for conv in convs:
        cstats = get_conversation_stats(conv["id"])
        rows.append({
            "ID":              conv["id"][:8] + "…",
            "Title":           conv["title"][:50],
            "Messages":        cstats["total_messages"],
            "Input Tokens":    cstats["total_input_tokens"],
            "Output Tokens":   cstats["total_output_tokens"],
            "Cost (USD)":      round(cstats["total_cost_usd"], 5),
            "Models Used":     ", ".join(cstats["models_used"]) or "—",
            "Last Updated":    conv["updated_at"][:16].replace("T", " "),
        })

    conv_df = pd.DataFrame(rows).sort_values("Cost (USD)", ascending=False)
    st.dataframe(
        conv_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Cost (USD)": st.column_config.NumberColumn(format="$%.5f"),
        },
    )
else:
    st.info("No conversations yet.")

st.divider()
st.caption("Data refreshes when you reload this page. All data is stored locally in `data/conversations.db`.")
