# Phase 1 — Project Scaffold & Core RAG Application

## Context: What This Capstone Is
An AI-powered Knowledge Assistant for a company. Employees ask questions about internal
documents (product manuals, HR policies, technical guides). The app retrieves relevant
document chunks and uses an LLM to generate grounded answers. This is RAG —
Retrieval-Augmented Generation.

**No AWS Console is used anywhere. All AWS resources are created via Terraform (Phase 4)
or Python boto3 scripts inside this project.**

---

## Phase 1 Scope
Build the complete working application code including:
- Project structure and configuration
- Core RAG engine (retrieve from Bedrock Knowledge Base → generate with Claude)
- Streamlit UI with:
  - Multi-model selection (text models + vision model)
  - Voice input (speak your question)
  - Image upload (ask questions about images using vision model)
  - Auto-routing mode (app decides which model to call)
  - Per-message token and cost display
  - Token/cost charts across the session
  - Persistent conversation storage (save, load, resume past conversations)
- Sample documents
- Scripts to create S3 bucket, upload documents, create Knowledge Base — all via boto3

---

## Technology Stack
| Tool | Purpose |
|---|---|
| Amazon Bedrock bedrock-runtime | Invoke Claude LLMs for text and vision |
| Amazon Bedrock Agent Runtime | Query Knowledge Base for retrieval |
| Amazon Bedrock Knowledge Bases | Managed RAG retrieval service |
| Amazon OpenSearch Serverless | Vector store (created by setup script) |
| Amazon Titan Embeddings v2 | Embedding model |
| Amazon S3 | Source document storage |
| Streamlit 1.35+ | Python web UI |
| boto3 | AWS Python SDK |
| python-dotenv | Load .env config |
| SpeechRecognition | Convert microphone audio to text |
| Pillow | Image loading and base64 encoding for vision |
| plotly | Interactive token/cost charts |
| pandas | Conversation history dataframes |
| sqlite3 (stdlib) | Persistent conversation storage (no extra install) |


---

## Project Root
`G:\learn ai\modules\capstone`

---

## Complete Folder Structure for Phase 1
```
capstone/
├── app/
│   ├── __init__.py
│   ├── config.py                      # All config from .env
│   ├── main.py                        # Streamlit entry point / dashboard
│   ├── pages/
│   │   ├── __init__.py
│   │   ├── 01_chat.py                 # Main chat interface
│   │   └── 02_analytics.py           # Token/cost charts page
│   ├── components/
│   │   ├── __init__.py
│   │   ├── sidebar.py                 # Sidebar: model selector, settings
│   │   ├── chat_ui.py                 # Chat message renderers
│   │   ├── voice_input.py             # Microphone → text
│   │   └── image_input.py             # Image upload + preview
│   └── utils/
│       ├── __init__.py
│       ├── bedrock_client.py          # boto3 client factory
│       ├── rag_engine.py              # Retrieve + generate pipeline
│       └── conversation_store.py     # SQLite persistent conversation store
├── sample_documents/
│   ├── product_manual.txt
│   ├── hr_policy.txt
│   └── technical_guide.txt
├── scripts/
│   ├── setup_s3.py                    # Create S3 bucket via boto3
│   ├── upload_documents.py            # Upload docs to S3
│   └── setup_knowledge_base.py       # Create KB + data source via boto3
├── data/
│   └── conversations.db              # SQLite DB (auto-created at runtime)
├── .env.template
├── requirements.txt
└── run.sh
```

---

## `.env.template`
```
# Copy this to .env and fill in your values

AWS_REGION=us-east-1
AWS_ACCOUNT_ID=           # Your 12-digit AWS account ID

# Bedrock Models
PRIMARY_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
SECONDARY_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0
VISION_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0

# S3 — must be globally unique
S3_BUCKET_NAME=knowledge-assistant-docs-REPLACE_WITH_ACCOUNT_ID

# Knowledge Base — filled by scripts/setup_knowledge_base.py
KNOWLEDGE_BASE_ID=
KNOWLEDGE_BASE_ARN=

# Guardrail — filled by guardrails/setup_guardrail.py in Phase 2
GUARDRAIL_ID=
GUARDRAIL_VERSION=DRAFT

# LangFuse — filled in Phase 5
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=https://cloud.langfuse.com
```

---

## `requirements.txt`
```
streamlit==1.35.0
boto3==1.34.144
python-dotenv==1.0.1
langfuse==2.36.1
plotly==5.22.0
pandas==2.2.2
SpeechRecognition==3.10.4
Pillow==10.3.0
pyaudio==0.2.14
```


---

## File Specifications

### `app/config.py`
Load all config from `.env` using `python-dotenv`. Call `load_dotenv()` at top.
Export named constants — every other module imports from here only.

```python
from dotenv import load_dotenv
import os
load_dotenv()

AWS_REGION           = os.getenv("AWS_REGION", "us-east-1")
AWS_ACCOUNT_ID       = os.getenv("AWS_ACCOUNT_ID", "")
PRIMARY_MODEL_ID     = os.getenv("PRIMARY_MODEL_ID",    "anthropic.claude-3-sonnet-20240229-v1:0")
SECONDARY_MODEL_ID   = os.getenv("SECONDARY_MODEL_ID",  "anthropic.claude-3-haiku-20240307-v1:0")
VISION_MODEL_ID      = os.getenv("VISION_MODEL_ID",     "anthropic.claude-3-sonnet-20240229-v1:0")
EMBEDDING_MODEL_ID   = os.getenv("EMBEDDING_MODEL_ID",  "amazon.titan-embed-text-v2:0")
KNOWLEDGE_BASE_ID    = os.getenv("KNOWLEDGE_BASE_ID",   "")
KB_MAX_RESULTS       = int(os.getenv("KB_MAX_RESULTS",  "5"))
GUARDRAIL_ID         = os.getenv("GUARDRAIL_ID",        "")
GUARDRAIL_VERSION    = os.getenv("GUARDRAIL_VERSION",   "DRAFT")
S3_BUCKET_NAME       = os.getenv("S3_BUCKET_NAME",      "")
LANGFUSE_PUBLIC_KEY  = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY  = os.getenv("LANGFUSE_SECRET_KEY", "")
LANGFUSE_HOST        = os.getenv("LANGFUSE_HOST",       "https://cloud.langfuse.com")

# Hardcoded app constants
APP_TITLE            = "Knowledge Assistant"
APP_ICON             = "🧠"
MAX_HISTORY_TURNS    = 20
DEFAULT_MAX_TOKENS   = 1024
DEFAULT_TEMPERATURE  = 0.1

# Model cost table (USD per 1000 tokens) — used by analytics page
MODEL_COSTS = {
    PRIMARY_MODEL_ID:   {"input": 0.003,   "output": 0.015,   "name": "Claude 3 Sonnet"},
    SECONDARY_MODEL_ID: {"input": 0.00025, "output": 0.00125, "name": "Claude 3 Haiku"},
    VISION_MODEL_ID:    {"input": 0.003,   "output": 0.015,   "name": "Claude 3 Sonnet (Vision)"},
}

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "conversations.db")
```

---

### `app/utils/bedrock_client.py`
Cached boto3 client factory. Use `functools.lru_cache(maxsize=1)` on every function.

```python
import boto3
from functools import lru_cache
from app.config import AWS_REGION

@lru_cache(maxsize=1)
def get_bedrock_runtime():
    return boto3.client("bedrock-runtime", region_name=AWS_REGION)

@lru_cache(maxsize=1)
def get_bedrock_agent_runtime():
    return boto3.client("bedrock-agent-runtime", region_name=AWS_REGION)

@lru_cache(maxsize=1)
def get_bedrock_client():
    return boto3.client("bedrock", region_name=AWS_REGION)

@lru_cache(maxsize=1)
def get_s3_client():
    return boto3.client("s3", region_name=AWS_REGION)

@lru_cache(maxsize=1)
def get_iam_client():
    return boto3.client("iam", region_name=AWS_REGION)
```


---

### `app/utils/rag_engine.py`
Core RAG pipeline. Supports text queries and image+text queries (vision).

#### Function: `retrieve_from_knowledge_base(query, kb_id, max_results) -> list[dict]`
```python
# Calls bedrock_agent_runtime.retrieve()
# Returns list of dicts:
# [{"content": str, "source": str (S3 URI), "score": float}]

client = get_bedrock_agent_runtime()
response = client.retrieve(
    knowledgeBaseId=kb_id,
    retrievalQuery={"text": query},
    retrievalConfiguration={
        "vectorSearchConfiguration": {"numberOfResults": max_results}
    }
)
chunks = []
for r in response.get("retrievalResults", []):
    chunks.append({
        "content": r["content"]["text"],
        "source":  r["location"]["s3Location"]["uri"],
        "score":   r.get("score", 0.0)
    })
return chunks
```

#### Function: `generate_response(query, context_chunks, model_id, image_b64=None, image_media_type=None, guardrail_id="", guardrail_version="DRAFT") -> dict`
Builds a Claude API call. If `image_b64` is provided, builds a vision (multimodal) message.

Text-only message body:
```python
messages = [{"role": "user", "content": prompt_string}]
```

Vision message body (when image_b64 is provided):
```python
messages = [{
    "role": "user",
    "content": [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": image_media_type,   # e.g. "image/jpeg"
                "data": image_b64
            }
        },
        {"type": "text", "text": prompt_string}
    ]
}]
```

Invoke call:
```python
import json
body = json.dumps({
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": DEFAULT_MAX_TOKENS,
    "temperature": DEFAULT_TEMPERATURE,
    "messages": messages
})
kwargs = {"modelId": model_id, "body": body}
if guardrail_id:
    kwargs["guardrailIdentifier"] = guardrail_id
    kwargs["guardrailVersion"]    = guardrail_version

response = get_bedrock_runtime().invoke_model(**kwargs)
result   = json.loads(response["body"].read())

return {
    "answer":        result["content"][0]["text"],
    "input_tokens":  result["usage"]["input_tokens"],
    "output_tokens": result["usage"]["output_tokens"],
    "model_id":      model_id
}
```

#### Function: `run_rag_query(query, model_choice="Auto", use_guardrails=True, image_b64=None, image_media_type=None, max_results=5) -> dict`
Orchestrates retrieve → generate. Returns:
```python
{
    "answer":         str,
    "sources":        list[dict],
    "input_tokens":   int,
    "output_tokens":  int,
    "model_id":       str,
    "model_name":     str,
    "routing_reason": str,
    "cost_usd":       float,   # calculated from MODEL_COSTS
    "error":          str | None
}
```

Rules:
- If `KNOWLEDGE_BASE_ID` is empty, return error: `"Knowledge Base not configured. Run scripts/setup_knowledge_base.py first."`
- If image is provided, force model to `VISION_MODEL_ID` regardless of `model_choice`
- If `model_choice` is `"Auto"`, use complexity heuristic (Phase 3 adds full router; in Phase 1 default to `PRIMARY_MODEL_ID`)
- Calculate `cost_usd` = `(input_tokens/1000 * cost_input) + (output_tokens/1000 * cost_output)` using `MODEL_COSTS` from config
- Wrap everything in try/except; put exception string in `error` field


---

### `app/utils/conversation_store.py`
Persistent conversation storage using SQLite (no extra dependency — sqlite3 is Python stdlib).

#### Schema
```sql
CREATE TABLE IF NOT EXISTS conversations (
    id          TEXT PRIMARY KEY,      -- UUID
    title       TEXT NOT NULL,         -- First 60 chars of first user message
    created_at  TEXT NOT NULL,         -- ISO timestamp
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id              TEXT PRIMARY KEY,  -- UUID
    conversation_id TEXT NOT NULL,
    role            TEXT NOT NULL,     -- "user" | "assistant"
    content         TEXT NOT NULL,     -- message text
    model_id        TEXT,
    model_name      TEXT,
    input_tokens    INTEGER DEFAULT 0,
    output_tokens   INTEGER DEFAULT 0,
    cost_usd        REAL    DEFAULT 0.0,
    routing_reason  TEXT,
    has_image       INTEGER DEFAULT 0, -- 1 if message had image
    sources         TEXT,              -- JSON string of sources list
    created_at      TEXT NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);
```

#### Functions to implement
```python
def init_db():
    # Create data/ dir if missing, create tables if not exist

def create_conversation(title: str) -> str:
    # Insert new conversation row, return conversation id (UUID)

def save_message(conversation_id: str, role: str, content: str, **kwargs) -> str:
    # Insert message row with all metadata fields, return message id

def get_all_conversations() -> list[dict]:
    # Return all conversations ordered by updated_at DESC
    # Each dict: {id, title, created_at, updated_at, message_count}

def get_conversation_messages(conversation_id: str) -> list[dict]:
    # Return all messages for a conversation ordered by created_at ASC
    # Parse sources field from JSON string back to list

def delete_conversation(conversation_id: str):
    # Delete messages first, then conversation row

def get_conversation_stats(conversation_id: str) -> dict:
    # Return: {total_messages, total_input_tokens, total_output_tokens,
    #          total_cost_usd, models_used: list[str]}

def get_all_stats() -> dict:
    # Return aggregate stats across ALL conversations for analytics page
    # Return: {total_conversations, total_messages, total_input_tokens,
    #          total_output_tokens, total_cost_usd,
    #          messages_by_model: dict[model_name -> count],
    #          daily_costs: list[{date, cost_usd, message_count}]}
```


---

### `app/components/voice_input.py`
Captures microphone input and returns transcribed text.

```python
import streamlit as st
import speech_recognition as sr

def render_voice_input() -> str | None:
    """
    Renders a 'Record Voice' button in Streamlit.
    When clicked, opens the microphone, listens for speech, transcribes it,
    and returns the transcribed text string.
    Returns None if no recording was made or if an error occurred.

    Implementation:
    - Show st.button("🎙️ Record Voice", key="voice_btn")
    - If button clicked:
        - Show st.spinner("Listening... speak now")
        - r = sr.Recognizer()
        - with sr.Microphone() as source:
            - r.adjust_for_ambient_noise(source, duration=0.5)
            - audio = r.listen(source, timeout=10, phrase_time_limit=30)
        - text = r.recognize_google(audio)   # uses Google free speech API
        - st.success(f"Transcribed: {text}")
        - return text
    - On sr.UnknownValueError: st.warning("Could not understand audio. Try again.")
    - On sr.RequestError: st.error("Speech recognition service unavailable.")
    - On Exception: st.error(f"Microphone error: {e}")
    - Return None on any error
    
    Note: pyaudio must be installed for Microphone() to work.
    On EC2 Linux without audio hardware, voice input will show a warning and return None.
    """
```

---

### `app/components/image_input.py`
Handles image upload and converts to base64 for Claude vision API.

```python
import streamlit as st
from PIL import Image
import base64
import io

def render_image_upload() -> tuple[str | None, str | None]:
    """
    Renders a file uploader for images.
    Returns (base64_string, media_type) or (None, None) if no image uploaded.

    Implementation:
    - uploaded = st.file_uploader(
          "📎 Attach Image", 
          type=["jpg", "jpeg", "png", "gif", "webp"],
          help="Upload an image to ask questions about it (uses vision model)"
      )
    - If uploaded is not None:
        - Open with PIL: img = Image.open(uploaded)
        - Resize if larger than 1568px on any dimension (Claude vision limit):
            max_dim = 1568
            if img.width > max_dim or img.height > max_dim:
                img.thumbnail((max_dim, max_dim), Image.LANCZOS)
        - Show preview: st.image(img, caption="Attached image", width=200)
        - Convert to bytes: buffer = io.BytesIO(); img.save(buffer, format="JPEG")
        - Encode: b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        - Return (b64, "image/jpeg")
    - Return (None, None) if nothing uploaded
    """

def clear_image_upload():
    """Call st.session_state pop on the uploader key to reset it."""
```


---

### `app/components/sidebar.py`
Full sidebar with all controls. Returns a settings dict used by chat page.

```python
def render_sidebar() -> dict:
    with st.sidebar:
        st.title("⚙️ Settings")
        st.divider()

        # ── Model Selection ──────────────────────────────────────────────────
        st.subheader("🤖 Model")
        model_choice = st.selectbox(
            "Select Model",
            options=[
                "Auto (Smart Routing)",
                "Claude 3 Sonnet  — Quality",
                "Claude 3 Haiku   — Fast & Cheap",
                "Claude 3 Sonnet  — Vision (Image Q&A)",
            ],
            index=0,
            help="Auto: app picks based on your query. Vision: required for image questions."
        )

        # Show routing explanation for Auto
        if model_choice == "Auto (Smart Routing)":
            with st.expander("How Auto routing works"):
                st.markdown("""
                - **Short / simple queries** → Haiku (fast, cheap)
                - **Long / complex queries** → Sonnet (quality)
                - **Image attached** → Sonnet Vision (forced)
                - Complexity scored by word count + keywords
                """)

        st.divider()

        # ── Safety ──────────────────────────────────────────────────────────
        st.subheader("🛡️ Safety")
        use_guardrails = st.checkbox(
            "Enable Guardrails", value=True,
            help="Blocks PII leakage and prompt injection attempts"
        )
        from app.config import GUARDRAIL_ID
        if GUARDRAIL_ID:
            st.success("Guardrail active", icon="✅")
        else:
            st.warning("Run guardrails/setup_guardrail.py", icon="⚠️")

        st.divider()

        # ── Retrieval ────────────────────────────────────────────────────────
        st.subheader("📚 Knowledge Base")
        max_results = st.slider("Sources to retrieve", 1, 10, 5)

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
            """)

    # Map display label to internal key used by rag_engine
    model_map = {
        "Auto (Smart Routing)":              "Auto",
        "Claude 3 Sonnet  — Quality":        "Quality (Claude Sonnet)",
        "Claude 3 Haiku   — Fast & Cheap":   "Fast (Claude Haiku)",
        "Claude 3 Sonnet  — Vision (Image Q&A)": "Vision",
    }

    return {
        "model_choice":  model_map[model_choice],
        "use_guardrails": use_guardrails,
        "max_results":    max_results,
    }
```


---

### `app/components/chat_ui.py`
Reusable chat rendering helpers.

```python
import streamlit as st

def render_message(role: str, content: str, has_image: bool = False):
    """Render a single chat bubble using st.chat_message(role)."""
    with st.chat_message(role):
        if has_image and role == "user":
            st.caption("📎 Image attached")
        st.markdown(content)

def render_sources(sources: list[dict]):
    """Render source documents in a collapsible expander."""
    if not sources:
        return
    with st.expander(f"📄 View Sources ({len(sources)})"):
        for i, s in enumerate(sources, 1):
            filename = s["source"].split("/")[-1]
            st.markdown(f"**{i}. {filename}**")
            st.caption(f"Relevance: {s['score']:.2f} · `{s['source']}`")
            st.divider()

def render_token_usage(input_tokens: int, output_tokens: int,
                       model_name: str, cost_usd: float, routing_reason: str = ""):
    """
    Render a compact metrics row below each assistant message.
    Show: input tokens, output tokens, cost in USD, model name, routing reason.
    """
    cols = st.columns(4)
    cols[0].metric("Input tokens",  input_tokens)
    cols[1].metric("Output tokens", output_tokens)
    cols[2].metric("Cost",          f"${cost_usd:.5f}")
    cols[3].metric("Model",         model_name)
    if routing_reason:
        st.caption(f"🔀 {routing_reason}")

def render_chat_history(history: list[dict]):
    """Render all messages in history list."""
    for item in history:
        render_message(item["role"], item["content"], item.get("has_image", False))
```

---

### `app/pages/01_chat.py`
Main chat page. Full implementation logic:

```python
"""
01_chat.py — Main RAG chat interface.
Features: text input, voice input, image upload, model selection,
          per-message token/cost display, persistent conversations.
"""
import streamlit as st
import uuid
from datetime import datetime

from app.config import KNOWLEDGE_BASE_ID, MAX_HISTORY_TURNS, VISION_MODEL_ID
from app.utils.rag_engine import run_rag_query
from app.utils.conversation_store import (
    init_db, create_conversation, save_message,
    get_all_conversations, get_conversation_messages, delete_conversation
)
from app.components.sidebar import render_sidebar
from app.components.chat_ui import render_message, render_sources, render_token_usage, render_chat_history
from app.components.voice_input import render_voice_input
from app.components.image_input import render_image_upload

st.set_page_config(page_title="Chat", page_icon="💬", layout="wide")

# ── Init ─────────────────────────────────────────────────────────────────────
init_db()
settings = render_sidebar()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "current_conversation_id" not in st.session_state:
    st.session_state.current_conversation_id = None

# ── Past Conversations Panel ──────────────────────────────────────────────────
with st.sidebar:
    st.subheader("📂 Past Conversations")
    all_convs = get_all_conversations()
    for conv in all_convs[:15]:   # show last 15
        col1, col2 = st.columns([4, 1])
        if col1.button(conv["title"][:35], key=f"conv_{conv['id']}"):
            # Load this conversation
            msgs = get_conversation_messages(conv["id"])
            st.session_state.chat_history = msgs
            st.session_state.current_conversation_id = conv["id"]
            st.rerun()
        if col2.button("🗑️", key=f"del_{conv['id']}"):
            delete_conversation(conv["id"])
            if st.session_state.current_conversation_id == conv["id"]:
                st.session_state.chat_history = []
                st.session_state.current_conversation_id = None
            st.rerun()

# ── Main Area ─────────────────────────────────────────────────────────────────
st.title("💬 Knowledge Assistant")

if not KNOWLEDGE_BASE_ID:
    st.warning("Knowledge Base not configured. Run `scripts/setup_knowledge_base.py` first.")
    st.stop()

# Render existing history
render_chat_history(st.session_state.chat_history)

# ── Input Area ────────────────────────────────────────────────────────────────
st.divider()
input_col, voice_col = st.columns([5, 1])

with voice_col:
    voice_text = render_voice_input()   # returns transcribed text or None

with input_col:
    image_b64, image_media_type = render_image_upload()

# Voice input populates the chat input via session state
if voice_text and "voice_prefill" not in st.session_state:
    st.session_state["voice_prefill"] = voice_text

user_input = st.chat_input("Ask a question about company documents...")

# Use voice transcript if chat_input is empty
query = user_input or st.session_state.pop("voice_prefill", None)

# ── Process Query ─────────────────────────────────────────────────────────────
if query:
    has_image = image_b64 is not None

    # Force vision model if image is attached
    model_choice = settings["model_choice"]
    if has_image:
        model_choice = "Vision"

    # Create new conversation if needed
    if st.session_state.current_conversation_id is None:
        title = query[:60]
        conv_id = create_conversation(title)
        st.session_state.current_conversation_id = conv_id
    else:
        conv_id = st.session_state.current_conversation_id

    # Add user message to display and DB
    user_msg = {"role": "user", "content": query, "has_image": has_image}
    st.session_state.chat_history.append(user_msg)
    render_message("user", query, has_image)
    save_message(conv_id, "user", query, has_image=int(has_image))

    # Generate response
    with st.spinner("🔍 Searching knowledge base and generating answer..."):
        result = run_rag_query(
            query=query,
            model_choice=model_choice,
            use_guardrails=settings["use_guardrails"],
            image_b64=image_b64,
            image_media_type=image_media_type,
            max_results=settings["max_results"]
        )

    if result["error"]:
        st.error(result["error"])
    else:
        # Add assistant message to display and DB
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
            result["input_tokens"],
            result["output_tokens"],
            result["model_name"],
            result["cost_usd"],
            result["routing_reason"]
        )

        save_message(
            conv_id, "assistant", result["answer"],
            model_id=result["model_id"],
            model_name=result["model_name"],
            input_tokens=result["input_tokens"],
            output_tokens=result["output_tokens"],
            cost_usd=result["cost_usd"],
            routing_reason=result["routing_reason"],
            sources=result["sources"]
        )

    # Trim in-memory history to MAX_HISTORY_TURNS
    if len(st.session_state.chat_history) > MAX_HISTORY_TURNS * 2:
        st.session_state.chat_history = st.session_state.chat_history[-(MAX_HISTORY_TURNS * 2):]
```


---

### `app/pages/02_analytics.py`
Token usage and cost analytics page with interactive charts.

```python
"""
02_analytics.py — Token usage and cost analytics dashboard.
Shows per-message costs, per-model breakdown, daily trends.
All data comes from the SQLite conversation store.
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from app.utils.conversation_store import init_db, get_all_stats, get_all_conversations, get_conversation_messages

st.set_page_config(page_title="Analytics", page_icon="📊", layout="wide")
st.title("📊 Token Usage & Cost Analytics")

init_db()
stats = get_all_stats()

# ── Summary Metrics Row ──────────────────────────────────────────────────────
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Conversations", stats["total_conversations"])
col2.metric("Total Messages",      stats["total_messages"])
col3.metric("Total Input Tokens",  f"{stats['total_input_tokens']:,}")
col4.metric("Total Output Tokens", f"{stats['total_output_tokens']:,}")
col5.metric("Total Cost (USD)",    f"${stats['total_cost_usd']:.4f}")

st.divider()

# ── Chart 1: Cost per Message (last 50 messages) ────────────────────────────
st.subheader("💰 Cost per Message")
# Build a dataframe from all conversations' messages
# Columns: message_index, model_name, cost_usd, created_at, short_content
# Show as bar chart with colour by model_name using plotly express

# ── Chart 2: Token usage per message ────────────────────────────────────────
st.subheader("🔢 Token Usage per Message")
# Stacked bar: input_tokens (blue) and output_tokens (orange) per message

# ── Chart 3: Model usage breakdown (pie) ────────────────────────────────────
st.subheader("🤖 Model Usage Breakdown")
# Pie chart: how many messages used each model
# Data: stats["messages_by_model"] — dict {model_name: count}

# ── Chart 4: Daily cost trend (line) ────────────────────────────────────────
st.subheader("📈 Daily Cost Trend")
# Line chart: x=date, y=cost_usd
# Data: stats["daily_costs"] — list of {date, cost_usd, message_count}

# ── Chart 5: Conversation-level cost table ──────────────────────────────────
st.subheader("📋 Cost by Conversation")
# Table: conversation title | messages | input tokens | output tokens | cost USD
# Allow sorting by cost_usd desc
# Add a "Load" button per row that sets st.session_state to navigate to that conversation
```

All charts must be built with `plotly.express` or `plotly.graph_objects` and rendered with
`st.plotly_chart(fig, use_container_width=True)`.

---

### `app/main.py`
Entry point / dashboard shown when app first loads.

```python
import streamlit as st
from app.config import APP_TITLE, APP_ICON, KNOWLEDGE_BASE_ID, GUARDRAIL_ID
from app.utils.conversation_store import init_db, get_all_stats

st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON, layout="wide")
init_db()

st.title(f"{APP_ICON} {APP_TITLE}")
st.markdown("Your AI-powered guide to company knowledge. Ask questions, upload images, use your voice.")
st.divider()

# Status indicators
col1, col2, col3 = st.columns(3)
with col1:
    if KNOWLEDGE_BASE_ID:
        st.success(f"Knowledge Base connected", icon="✅")
        st.caption(f"ID: `{KNOWLEDGE_BASE_ID}`")
    else:
        st.error("Knowledge Base not configured", icon="❌")
        st.caption("Run: `python scripts/setup_knowledge_base.py`")
with col2:
    if GUARDRAIL_ID:
        st.success("Guardrails active", icon="🛡️")
    else:
        st.warning("Guardrails not configured", icon="⚠️")
        st.caption("Run: `python guardrails/setup_guardrail.py`")
with col3:
    st.info("Vector Store: OpenSearch Serverless", icon="🔍")

st.divider()

# Quick stats from conversation store
stats = get_all_stats()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Conversations", stats["total_conversations"])
c2.metric("Messages",      stats["total_messages"])
c3.metric("Total Tokens",  f"{stats['total_input_tokens'] + stats['total_output_tokens']:,}")
c4.metric("Total Cost",    f"${stats['total_cost_usd']:.4f}")

st.divider()

# Feature guide
st.subheader("Features")
cols = st.columns(3)
cols[0].markdown("### 💬 Chat\nAsk questions in text. Answers grounded in your documents.")
cols[1].markdown("### 🎙️ Voice Input\nSpeak your question — it's transcribed automatically.")
cols[2].markdown("### 📎 Image Q&A\nUpload an image and ask questions about it (Vision model).")
cols2 = st.columns(3)
cols2[0].markdown("### 🔀 Smart Routing\nAuto mode picks the right model based on query complexity.")
cols2[1].markdown("### 💾 Saved Conversations\nAll chats saved locally. Resume any past conversation.")
cols2[2].markdown("### 📊 Analytics\nTrack token usage and costs per message and over time.")

st.markdown("---")
st.caption("Navigate using the sidebar → Chat to start | Analytics to view usage stats")
```


---

### `sample_documents/product_manual.txt`
~300 word realistic internal document for **DataSync Pro v3.2**.
Sections: Overview, System Requirements (Windows 10+/macOS 12+, 8GB RAM, 50GB disk),
Features (real-time sync, conflict resolution, AES-256 encryption at rest),
Installation Steps (4 steps), Troubleshooting:
- E101: Connection timeout — check firewall port 8443
- E202: Authentication failure — re-enter credentials or contact IT
- E303: Disk full — free space and retry
Support contact: datasync-support@company.com

### `sample_documents/hr_policy.txt`
~300 word realistic HR policy. Sections:
- Annual Leave: 20 days/year, accrued monthly, max 5 days rollover
- Sick Leave: 10 days/year, doctor's note required after 3 consecutive days
- Remote Work: up to 3 days/week, mandatory office days Tuesday and Thursday
- Performance Reviews: June and December, conducted by line manager
- Code of Conduct: professional communication, zero tolerance for harassment,
  violations reported to hr@company.com

### `sample_documents/technical_guide.txt`
~300 word internal API guide for **InternalAuthAPI v2**. Sections:
- Base URL: https://auth.internal.company.com/v2
- Authentication: OAuth 2.0 client credentials flow
- Endpoints: POST /token, POST /token/refresh, DELETE /token (logout)
- Headers required: Content-Type: application/json, X-Client-ID: your_client_id
- Rate limits: 100 requests/minute per client
- Error codes: 401 invalid credentials, 429 rate limit exceeded, 503 service unavailable
- Contact: api-support@company.com

---

### `scripts/setup_s3.py`
```python
# Load .env
# Get S3_BUCKET_NAME, AWS_REGION
# boto3 s3 client
# Create bucket (handle us-east-1 LocationConstraint special case)
# Enable versioning
# Block all public access via put_public_access_block
# Print bucket name and ARN
```

### `scripts/upload_documents.py`
```python
# Load .env
# Get S3_BUCKET_NAME
# boto3 s3 client
# Walk sample_documents/ folder
# Upload each .txt / .pdf to S3 under prefix "documents/"
# Print upload count and completion message
```

### `scripts/setup_knowledge_base.py`
```python
# Load .env
# Step 1: Create IAM role for Bedrock Knowledge Base
#   Trust policy: bedrock.amazonaws.com principal
#   Attach: AmazonBedrockFullAccess + AmazonS3ReadOnlyAccess
# Step 2: Create Bedrock Knowledge Base via bedrock-agent client
#   type: VECTOR, embeddingModelArn: Titan v2
#   storageConfiguration type: OPENSEARCH_SERVERLESS
#   collectionArn: from OPENSEARCH_COLLECTION_ARN env var (set by Terraform in Phase 4)
#   vectorIndexName: "knowledge-assistant-index"
# Step 3: Create data source pointing to S3 bucket
# Step 4: Start ingestion job
# Step 5: Write KNOWLEDGE_BASE_ID to .env file using regex replace
# Print all created resource IDs
```

### `run.sh`
```bash
#!/bin/bash
set -e
cd /home/ec2-user/capstone
source venv/bin/activate
echo "Starting Knowledge Assistant on port 8501..."
streamlit run app/main.py \
  --server.port 8501 \
  --server.address 0.0.0.0 \
  --server.headless true
```

---

## All `__init__.py` files
Create empty `__init__.py` in:
`app/`, `app/pages/`, `app/components/`, `app/utils/`

---

## Order to Create Files
1. `.env.template`
2. `requirements.txt`
3. `run.sh`
4. `app/__init__.py`
5. `app/config.py`
6. `app/utils/__init__.py`
7. `app/utils/bedrock_client.py`
8. `app/utils/conversation_store.py`
9. `app/utils/rag_engine.py`
10. `app/components/__init__.py`
11. `app/components/voice_input.py`
12. `app/components/image_input.py`
13. `app/components/sidebar.py`
14. `app/components/chat_ui.py`
15. `app/pages/__init__.py`
16. `app/pages/01_chat.py`
17. `app/pages/02_analytics.py`
18. `app/main.py`
19. `sample_documents/product_manual.txt`
20. `sample_documents/hr_policy.txt`
21. `sample_documents/technical_guide.txt`
22. `scripts/setup_s3.py`
23. `scripts/upload_documents.py`
24. `scripts/setup_knowledge_base.py`

---

## Definition of Done
- All 24 files created with complete working Python code
- `streamlit run app/main.py` starts without import errors
- Chat page loads with sidebar model selector (4 options), voice button, image uploader
- If `KNOWLEDGE_BASE_ID` empty → warning shown, app does not crash
- If image attached → VISION_MODEL_ID is used automatically
- Voice button opens microphone and transcribes speech into the text input
- Every assistant response shows input tokens, output tokens, cost, model name
- Analytics page shows 5 charts: cost per message, token usage, model breakdown, daily trend, conversation table
- All conversations saved to `data/conversations.db` (SQLite)
- Past conversations listed in sidebar; clicking one loads all messages
- Delete button removes conversation from DB and sidebar
