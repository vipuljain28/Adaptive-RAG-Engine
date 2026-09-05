# Phase 5 — Monitoring & Observability with LangFuse

## Context: What This Capstone Is
An AI-powered Knowledge Assistant built on AWS using Amazon Bedrock. Employees ask questions
about internal company documents. The app supports text queries, voice input, and image
uploads with multi-model routing and persistent conversation storage.

## What Previous Phases Already Built — Do Not Recreate
```
app/config.py                      — LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST
app/utils/bedrock_client.py        — boto3 client factory
app/utils/rag_engine.py            — run_rag_query() returns answer, tokens, cost, model info
app/utils/conversation_store.py   — SQLite persistent conversations
app/utils/prompt_templates.py      — RCTFC prompts
app/components/sidebar.py          — 4-option model selector
app/components/chat_ui.py          — token/cost display per message
app/pages/01_chat.py               — full chat page
app/pages/02_analytics.py          — local token/cost charts from SQLite
app/main.py                        — dashboard
gateway/router.py                  — 3-strategy LLM routing
guardrails/                        — Bedrock Guardrail
terraform/                         — full IaC
```

**No AWS Console is used anywhere. All resources are created via boto3 scripts or Terraform.**
**LangFuse is an external SaaS observability platform — account created at cloud.langfuse.com**

---

## Phase 5 Scope
Integrate LangFuse tracing into the RAG pipeline so every query is fully observable:

| What is captured | Where it appears in LangFuse |
|---|---|
| User query text | Span input |
| Retrieved document chunks | Retrieval span output |
| Prompt sent to LLM | Generation span input |
| LLM response text | Generation span output |
| Model ID used | Span metadata |
| Routing strategy + reason | Span metadata |
| Input tokens | LangFuse usage.input |
| Output tokens | LangFuse usage.output |
| Total cost USD | LangFuse usage.totalCost |
| End-to-end latency | Trace duration (automatic) |
| Errors | Span status = ERROR |
| Has image | Span metadata flag |
| Conversation ID | Trace session_id |

---

## Requirement Coverage
- **Requirement 7 (10 marks):** Monitoring & Observability — LangFuse traces covering
  queries, retrievals, LLM calls, latency, token usage, and errors

---

## Technology Used
| Tool | Purpose |
|---|---|
| LangFuse Python SDK (langfuse==2.36.1) | Tracing, spans, token usage, cost tracking |
| cloud.langfuse.com | Free-tier hosted dashboard |

LangFuse key concepts used in this phase:
- **Trace** — one complete user request end-to-end
- **Span** — a step within a trace (retrieval, generation)
- **Generation** — a special span type for LLM calls with token + cost support
- **session_id** — groups traces by conversation
- **user_id** — identifies the user (we use a session-level UUID)

---

## Project Root
`G:\learn ai\modules\capstone`

---

## New Files to Create in Phase 5
```
observability/
├── __init__.py
├── langfuse_tracer.py       # LangFuse client + trace/span helpers
└── README.md                # Setup guide: create account, get keys, view dashboard
```

## Files to Modify in Phase 5
```
app/utils/rag_engine.py      — wrap retrieve + generate steps in LangFuse spans
app/pages/01_chat.py         — pass conversation_id as session_id to tracer
app/main.py                  — show LangFuse connection status on dashboard
```

---

## LangFuse Account Setup (human does this once)
1. Go to https://cloud.langfuse.com and create a free account
2. Create a new project called "knowledge-assistant"
3. Go to Settings → API Keys → Create new key pair
4. Copy Public Key and Secret Key into `.env`:
   ```
   LANGFUSE_PUBLIC_KEY=pk-lf-...
   LANGFUSE_SECRET_KEY=sk-lf-...
   LANGFUSE_HOST=https://cloud.langfuse.com
   ```
5. The tracer code checks if keys are set — if empty, tracing is silently skipped

---

## File Specifications

### `observability/langfuse_tracer.py`
LangFuse client wrapper. Provides a clean API that `rag_engine.py` calls.
If LangFuse keys are not configured, every function is a no-op so the app still works.

```python
"""
LangFuse observability wrapper for the Knowledge Assistant RAG pipeline.

Traces every query end-to-end:
  Trace
    └── Span: retrieval       (KB query → chunks returned)
    └── Generation: llm_call  (prompt → answer, tokens, cost)

If LANGFUSE_PUBLIC_KEY is empty, all functions are no-ops — app works without tracing.

Usage in rag_engine.py:
    tracer = RagTracer(conversation_id, user_query)
    tracer.start_retrieval(query)
    tracer.end_retrieval(chunks)
    tracer.start_generation(model_id, prompt)
    tracer.end_generation(answer, input_tokens, output_tokens, cost_usd)
    tracer.end_trace(success=True)
    tracer.flush()
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import (
    LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST
)

# Only import langfuse if keys are configured
_langfuse_enabled = bool(LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY)

if _langfuse_enabled:
    from langfuse import Langfuse
    _client = Langfuse(
        public_key=LANGFUSE_PUBLIC_KEY,
        secret_key=LANGFUSE_SECRET_KEY,
        host=LANGFUSE_HOST,
    )
else:
    _client = None


class RagTracer:
    """
    Context manager-style tracer for one complete RAG query.

    Create one RagTracer per query in run_rag_query().
    Call methods in order: start → end for each step → end_trace → flush.
    """

    def __init__(
        self,
        conversation_id: str,
        query: str,
        user_id: str = "anonymous",
        has_image: bool = False,
        routing_strategy: str = "",
        routing_reason: str = "",
    ):
        self._enabled = _langfuse_enabled
        self._trace = None
        self._retrieval_span = None
        self._generation_span = None

        if not self._enabled:
            return

        self._trace = _client.trace(
            name="rag-query",
            input={"query": query, "has_image": has_image},
            session_id=conversation_id,
            user_id=user_id,
            metadata={
                "routing_strategy": routing_strategy,
                "routing_reason":   routing_reason,
                "has_image":        has_image,
            },
        )

    # ── Retrieval span ─────────────────────────────────────────────────────────

    def start_retrieval(self, query: str, kb_id: str, max_results: int):
        """Call immediately before the Knowledge Base retrieve() API call."""
        if not self._enabled or not self._trace:
            return
        self._retrieval_span = self._trace.span(
            name="kb-retrieval",
            input={
                "query":       query,
                "kb_id":       kb_id,
                "max_results": max_results,
            },
        )

    def end_retrieval(self, chunks: list[dict]):
        """Call immediately after retrieve() returns chunks."""
        if not self._enabled or not self._retrieval_span:
            return
        self._retrieval_span.end(
            output={
                "chunks_returned": len(chunks),
                "sources": [c["source"] for c in chunks],
                "top_score": chunks[0]["score"] if chunks else 0.0,
            }
        )

    # ── Generation span ────────────────────────────────────────────────────────

    def start_generation(self, model_id: str, prompt: str, model_name: str = ""):
        """Call immediately before the Bedrock invoke_model() call."""
        if not self._enabled or not self._trace:
            return
        self._generation_span = self._trace.generation(
            name="llm-generation",
            model=model_id,
            input=prompt,
            metadata={"model_name": model_name},
        )

    def end_generation(
        self,
        answer: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
    ):
        """Call immediately after invoke_model() returns with the answer."""
        if not self._enabled or not self._generation_span:
            return
        self._generation_span.end(
            output=answer,
            usage={
                "input":      input_tokens,
                "output":     output_tokens,
                "totalCost":  cost_usd,
            },
        )

    # ── Error recording ────────────────────────────────────────────────────────

    def record_error(self, error_message: str, step: str = "unknown"):
        """Call in the except block of any step that fails."""
        if not self._enabled or not self._trace:
            return
        self._trace.span(
            name=f"error-{step}",
            input={"error": error_message},
            level="ERROR",
        ).end()

    # ── Finalise trace ─────────────────────────────────────────────────────────

    def end_trace(self, success: bool, answer: str = "", error: str = ""):
        """Call after the full pipeline completes."""
        if not self._enabled or not self._trace:
            return
        if success:
            self._trace.update(output={"answer": answer[:500]})
        else:
            self._trace.update(
                output={"error": error},
                metadata={"status": "error"},
            )

    def flush(self):
        """Flush all pending events to LangFuse. Call at end of run_rag_query()."""
        if not self._enabled:
            return
        _client.flush()


def is_enabled() -> bool:
    """Returns True if LangFuse tracing is configured and active."""
    return _langfuse_enabled
```


---

### Modify `app/utils/rag_engine.py` — integrate RagTracer

Add tracing calls at each step of the pipeline. The full modified `run_rag_query` function:

```python
# Add import at top of rag_engine.py:
from observability.langfuse_tracer import RagTracer

# Replace run_rag_query with this implementation:

def run_rag_query(
    query: str,
    model_choice: str = "Auto",
    use_guardrails: bool = True,
    image_b64: str = None,
    image_media_type: str = None,
    max_results: int = 5,
    conversation_id: str = "default",   # NEW PARAMETER — pass from 01_chat.py
) -> dict:
    """
    Full RAG pipeline with LangFuse tracing.
    Steps: gateway route → KB retrieve → RCTFC prompt build → LLM generate
    """
    from app.config import (
        KNOWLEDGE_BASE_ID, GUARDRAIL_ID, GUARDRAIL_VERSION,
        MODEL_COSTS, KB_MAX_RESULTS
    )

    # Guard: KB must be configured
    if not KNOWLEDGE_BASE_ID:
        return {
            "answer": "", "sources": [], "input_tokens": 0, "output_tokens": 0,
            "model_id": "", "model_name": "", "routing_reason": "",
            "cost_usd": 0.0,
            "error": "Knowledge Base not configured. Run scripts/setup_knowledge_base.py first."
        }

    # ── Gateway routing ────────────────────────────────────────────────────────
    has_image      = image_b64 is not None
    routing_result = gateway_route(query, user_selection=model_choice, has_image=has_image)
    model_id       = routing_result["model_id"]
    model_name     = routing_result["model_name"]
    routing_reason = routing_result["reason"]
    strategy       = routing_result["strategy"]

    # ── Initialise tracer ──────────────────────────────────────────────────────
    tracer = RagTracer(
        conversation_id=conversation_id,
        query=query,
        has_image=has_image,
        routing_strategy=strategy,
        routing_reason=routing_reason,
    )

    try:
        # ── Step 1: Retrieve ───────────────────────────────────────────────────
        tracer.start_retrieval(query, KNOWLEDGE_BASE_ID, max_results)
        chunks = retrieve_from_knowledge_base(query, KNOWLEDGE_BASE_ID, max_results)
        tracer.end_retrieval(chunks)

        # ── Step 2: Build RCTFC prompt ─────────────────────────────────────────
        if has_image:
            prompt = build_vision_prompt(query, chunks)
        else:
            prompt = build_rag_prompt(query, chunks)

        # ── Step 3: Generate ───────────────────────────────────────────────────
        tracer.start_generation(model_id, prompt, model_name)
        gen = generate_response(
            query=query,
            context_chunks=chunks,
            model_id=model_id,
            image_b64=image_b64,
            image_media_type=image_media_type,
            guardrail_id=GUARDRAIL_ID if use_guardrails else "",
            guardrail_version=GUARDRAIL_VERSION,
        )
        tracer.end_generation(
            answer=gen["answer"],
            input_tokens=gen["input_tokens"],
            output_tokens=gen["output_tokens"],
            cost_usd=gen["cost_usd"],
        )

        tracer.end_trace(success=True, answer=gen["answer"])
        tracer.flush()

        return {
            "answer":         gen["answer"],
            "sources":        chunks,
            "input_tokens":   gen["input_tokens"],
            "output_tokens":  gen["output_tokens"],
            "model_id":       model_id,
            "model_name":     model_name,
            "routing_reason": routing_reason,
            "cost_usd":       gen["cost_usd"],
            "error":          None,
        }

    except Exception as e:
        error_msg = str(e)
        tracer.record_error(error_msg, step="pipeline")
        tracer.end_trace(success=False, error=error_msg)
        tracer.flush()
        return {
            "answer": "", "sources": [], "input_tokens": 0, "output_tokens": 0,
            "model_id": model_id, "model_name": model_name,
            "routing_reason": routing_reason, "cost_usd": 0.0,
            "error": f"Pipeline error: {error_msg}"
        }
```

---

### Modify `app/pages/01_chat.py` — pass conversation_id to rag_engine

The conversation ID already exists in `st.session_state.current_conversation_id`.
Pass it to `run_rag_query`:

```python
# Change this call:
result = run_rag_query(
    query=query,
    model_choice=model_choice,
    use_guardrails=settings["use_guardrails"],
    image_b64=image_b64,
    image_media_type=image_media_type,
    max_results=settings["max_results"]
)

# To this (add conversation_id parameter):
result = run_rag_query(
    query=query,
    model_choice=model_choice,
    use_guardrails=settings["use_guardrails"],
    image_b64=image_b64,
    image_media_type=image_media_type,
    max_results=settings["max_results"],
    conversation_id=st.session_state.get("current_conversation_id", "default")
)
```

---

### Modify `app/main.py` — show LangFuse status on dashboard

```python
# Add import:
from observability.langfuse_tracer import is_enabled as langfuse_enabled

# Add to the status indicators section (alongside KB and Guardrail status):
with col_langfuse:   # add a 4th column or add to existing layout
    if langfuse_enabled():
        st.success("LangFuse tracing active", icon="📡")
        st.caption(f"Dashboard: cloud.langfuse.com")
    else:
        st.warning("LangFuse not configured", icon="📡")
        st.caption("Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY in .env")
```

---

### `observability/README.md`
Write this document in full markdown. Include all sections below.

#### Section 1: What is LangFuse?
LangFuse is an open-source observability platform for LLM applications. It captures every
step of the AI pipeline as structured traces visible in a web dashboard. Key features:
traces, spans, generations, token usage tracking, latency, cost tracking, error monitoring.

#### Section 2: Setup Steps
```
1. Create free account at https://cloud.langfuse.com
2. Click "New Project" → name it "knowledge-assistant"
3. Go to Settings → API Keys → Create new key pair
4. Copy keys into .env:
     LANGFUSE_PUBLIC_KEY=pk-lf-...
     LANGFUSE_SECRET_KEY=sk-lf-...
     LANGFUSE_HOST=https://cloud.langfuse.com
5. Restart the Streamlit app
6. Send a test query in the chat
7. Open cloud.langfuse.com → Traces — you should see the trace appear within seconds
```

#### Section 3: What Each Trace Shows
Explain the trace structure with a diagram in text:
```
Trace: "rag-query"
├── metadata: routing_strategy, routing_reason, has_image
├── session_id: conversation UUID (groups all messages in one chat)
├── Span: "kb-retrieval"
│     input:  query text, kb_id, max_results
│     output: chunks_returned count, source filenames, top relevance score
│     duration: retrieval latency in ms
└── Generation: "llm-generation"
      model:  bedrock model ID
      input:  full RCTFC prompt text
      output: answer text
      usage:  input_tokens, output_tokens, totalCost (USD)
      duration: generation latency in ms
```

#### Section 4: What to Monitor
Table of key metrics to check in the LangFuse dashboard:

| Metric | Where to Find | What to Look For |
|---|---|---|
| End-to-end latency | Trace duration | > 10s may indicate KB issues |
| Retrieval latency | kb-retrieval span duration | > 3s is slow for OpenSearch |
| Generation latency | llm-generation span duration | Haiku should be < 2s |
| Input tokens | Generation usage.input | Spikes may mean large retrieved chunks |
| Output tokens | Generation usage.output | Very short = possible guardrail block |
| Cost per query | Generation usage.totalCost | Compare Sonnet vs Haiku in dashboard |
| Error rate | Trace status = ERROR | Any errors need investigation |
| Model distribution | Filter by model metadata | Verify Auto routing balance |

#### Section 5: Viewing Traces by Conversation
Each trace has `session_id` = the conversation UUID from SQLite. In LangFuse:
- Go to Sessions tab
- Click a session ID to see all traces in that conversation in order
- Compare token usage across messages in the same conversation

#### Section 6: Screenshots to Take for Submission
List of 5 screenshots that demonstrate observability:
1. LangFuse Traces list — showing multiple rag-query traces
2. Single trace detail — expanded to show kb-retrieval + llm-generation spans
3. Generation span detail — showing prompt input and token usage
4. Sessions view — showing one conversation's traces grouped together
5. Overview dashboard — showing total tokens/costs aggregated

---

## Order to Create / Modify Files
1. `observability/__init__.py` (empty)
2. `observability/langfuse_tracer.py`
3. `observability/README.md`
4. Modify `app/utils/rag_engine.py` — add RagTracer calls + conversation_id param
5. Modify `app/pages/01_chat.py` — pass conversation_id to run_rag_query
6. Modify `app/main.py` — add LangFuse status indicator

---

## How to Run (for the human)
```bash
# 1. Set LangFuse keys in .env (get from cloud.langfuse.com)
# 2. Launch the app
streamlit run app/main.py

# 3. Send a few queries in the chat
# 4. Open cloud.langfuse.com → your project → Traces
# 5. Each query appears as a trace with full span breakdown
```

---

## Definition of Done
- `observability/langfuse_tracer.py` exists with RagTracer class and is_enabled()
- If LangFuse keys are empty in .env, app still runs without errors (graceful no-op)
- If LangFuse keys are set, every run_rag_query() call creates a LangFuse trace
- Each trace has: retrieval span + generation span with token/cost data
- Trace session_id matches the conversation UUID in SQLite
- Errors during retrieval or generation are recorded in LangFuse with level=ERROR
- app/main.py dashboard shows LangFuse connection status
- observability/README.md explains setup, trace structure, and screenshot guide
