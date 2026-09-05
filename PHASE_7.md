# Phase 7 — Project Summary, Documentation, Tests & Flow Diagrams
# (Includes: EKS LLM App Integration + CI/CD Theory Revision)

## Context: What This Capstone Is
An AI-powered Knowledge Assistant built on AWS. All 6 phases are complete:
- Phase 1: RAG app — text, voice, image, multi-model, persistent conversations, analytics
- Phase 2: Guardrails (PII + injection) + RCTFC prompt engineering
- Phase 3: AI Gateway — 3 routing strategies (image_forced, user_selection, auto_complexity)
- Phase 4: Cost comparison + Terraform IaC (5 modules)
- Phase 5: LangFuse observability tracing
- Phase 6: EKS TinyLlama deployment + CI/CD theory (files created but app not wired)

## What Phase 7 Adds
1. **EKS LLM wired into the live app** as a selectable 5th model option
2. **Project summary document** — one-page overview of the whole system
3. **Full technical documentation** — architecture, components, data flow
4. **Test suite** — unit tests + integration test stubs for every major module
5. **Flow diagrams** (text-based ASCII + description) — system flow, RAG pipeline,
   routing decision tree, CI/CD pipeline, conversation persistence flow
6. **CI/CD theory document** — GitHub, CodePipeline, buildspec.yaml, workflow

---

## Project Root
`G:\learn ai\modules\capstone`

---

## New Files to Create in Phase 7
```
docs/
├── PROJECT_SUMMARY.md        # One-page project overview for submission
├── ARCHITECTURE.md           # Full technical architecture document
├── FLOW_DIAGRAMS.md          # All flow diagrams in ASCII + description
└── TESTING.md                # Test plan and test run instructions

tests/
├── __init__.py
├── test_rag_engine.py        # Unit tests for RAG pipeline
├── test_router.py            # Unit tests for gateway routing logic
├── test_conversation_store.py # Unit tests for SQLite store
├── test_prompt_templates.py  # Unit tests for RCTFC prompt builders
├── test_guardrail_config.py  # Unit tests for guardrail constants
└── integration/
    ├── __init__.py
    └── test_integration_stubs.py  # Integration test stubs (documented, not live)

bonus/cicd/
├── cicd_theory.md            # Full CI/CD theory (GitHub + CodePipeline + buildspec)
└── buildspec.yaml            # Annotated buildspec file
```

## Files to Modify in Phase 7
```
gateway/llm_registry.py       — confirm tinyllama entry exists (added in Phase 6)
gateway/router.py             — confirm Self-Hosted routing works
app/components/sidebar.py     — confirm 5th option "Self-Hosted (TinyLlama) — EKS" exists
app/utils/rag_engine.py       — confirm adapter branch is wired
.env.template                 — confirm TINYLLAMA_ENDPOINT is present
.gitignore                    — create if missing
```

---

## SECTION 1 — EKS LLM App Integration (Confirm & Complete)

Phase 6 specified these changes. Phase 7 ensures they are fully implemented.
If they were not done in Phase 6, implement them now.

### Changes required across 4 files:

#### `gateway/llm_registry.py` — 4th model entry
```python
# Ensure this entry exists in the MODELS dict:
"tinyllama": LLMModel(
    key="tinyllama",
    name="TinyLlama 1.1B (Self-Hosted EKS)",
    model_id=os.getenv("TINYLLAMA_ENDPOINT", "http://localhost:8080"),
    provider="huggingface",
    tier="self-hosted",
    description="Open-source LLM on EKS. No Bedrock token cost. Requires EKS deployment.",
    max_tokens=512,
    cost_per_1k_input=0.0,
    cost_per_1k_output=0.0,
    supports_vision=False,
    best_for=["offline demo", "cost comparison", "open-source showcase"]
),
```

#### `gateway/router.py` — user selection mapping
```python
# In _route_user_selection(), mapping dict must include:
"Self-Hosted (TinyLlama)": "tinyllama",
```

#### `app/components/sidebar.py` — 5th model option
```python
# The selectbox options list must be exactly:
options=[
    "Auto (Smart Routing)",
    "Claude 3 Sonnet  — Quality",
    "Claude 3 Haiku   — Fast & Cheap",
    "Claude 3 Sonnet  — Vision (Image Q&A)",
    "Self-Hosted TinyLlama  — EKS",        # NEW 5th option
]

# The model_map dict must include:
"Self-Hosted TinyLlama  — EKS": "Self-Hosted (TinyLlama)",
```

Show a status indicator for TinyLlama in the sidebar:
```python
from bonus.eks.adapter import health_check
if model_choice == "Self-Hosted (TinyLlama)":
    if health_check():
        st.success("EKS TinyLlama server reachable", icon="🤖")
    else:
        st.warning(
            "TinyLlama server not reachable. "
            "Deploy to EKS or run: "
            "`kubectl port-forward svc/tinyllama-tinyllama 8080:8080`",
            icon="⚠️"
        )
```

#### `app/utils/rag_engine.py` — branch to self-hosted adapter
```python
# Add imports at top:
from bonus.eks.adapter import call_self_hosted, health_check as tinyllama_health

# In run_rag_query(), after routing_result is determined:
is_self_hosted = (routing_result["model"].provider == "huggingface")

# Replace the generate_response() call with a branch:
if is_self_hosted:
    # Self-hosted path — call EKS TinyLlama adapter
    if not tinyllama_health():
        raise RuntimeError(
            "TinyLlama server unreachable. "
            "Set TINYLLAMA_ENDPOINT in .env and ensure the server is running."
        )
    prompt = build_rag_prompt(query, chunks)   # vision not supported on TinyLlama
    gen = call_self_hosted(prompt)
    gen["model_id"]   = model_id
    gen["model_name"] = model_name
else:
    # Managed Bedrock path (existing code)
    if has_image:
        prompt = build_vision_prompt(query, chunks)
    else:
        prompt = build_rag_prompt(query, chunks)
    gen = generate_response(
        query=query,
        context_chunks=chunks,
        model_id=model_id,
        image_b64=image_b64,
        image_media_type=image_media_type,
        guardrail_id=GUARDRAIL_ID if use_guardrails else "",
        guardrail_version=GUARDRAIL_VERSION,
    )
```

#### `.env.template` — add TinyLlama vars
```
# Bonus: Self-hosted TinyLlama on Amazon EKS
# After deploying: kubectl port-forward svc/tinyllama-tinyllama 8080:8080
TINYLLAMA_ENDPOINT=http://localhost:8080
TINYLLAMA_TIMEOUT=60
```

---

## SECTION 2 — `docs/PROJECT_SUMMARY.md`

Write this as a clean, professional one-page summary. Include all sections below.

### Project Title
**Knowledge Assistant — Production-Ready RAG Application on AWS**

### Business Problem
Company employees spend significant time searching through internal documents (product
manuals, HR policies, technical guides) to find answers. This project delivers an
AI-powered assistant that answers questions instantly using those documents.

### Solution Overview
A RAG (Retrieval-Augmented Generation) application built on AWS that:
- Retrieves relevant document chunks from a vector database
- Generates grounded answers using large language models
- Supports text, voice, and image queries
- Routes queries to the optimal model automatically

### Architecture Summary (one paragraph)
Documents are stored in Amazon S3 and indexed into an OpenSearch Serverless vector store
via Amazon Bedrock Knowledge Bases using Titan Embeddings v2. User queries are processed
through a 3-strategy AI Gateway that routes to Claude 3 Sonnet, Claude 3 Haiku, or a
self-hosted TinyLlama on EKS. Bedrock Guardrails protect against PII leakage and prompt
injection. All queries are traced end-to-end in LangFuse. The Streamlit UI is hosted on
EC2, provisioned fully via Terraform.

### Requirements Completion Table
| # | Requirement | Marks | Status | Phase |
|---|---|---|---|---|
| 1 | RAG Application on AWS | 20 | ✅ Complete | Phase 1 |
| 2 | Bedrock Guardrails (PII + injection) | 10 | ✅ Complete | Phase 2 |
| 3 | RCTFC Prompt Engineering | 10 | ✅ Complete | Phase 2 |
| 4 | AI Gateway / LLM Routing | 10 | ✅ Complete | Phase 3 |
| 5 | LLM Cost Comparison | 10 | ✅ Complete | Phase 4 |
| 6 | Terraform IaC | 10 | ✅ Complete | Phase 4 |
| 7 | LangFuse Observability | 10 | ✅ Complete | Phase 5 |
| ★ | EKS Open-Source LLM | 10 | ✅ Complete | Phase 6+7 |
| ★ | CI/CD Theory | 10 | ✅ Complete | Phase 7 |
| **Total** | | **100** | | |

### Key Technical Decisions
- **SQLite for conversation persistence** — zero infrastructure, works on EC2, sufficient for 50 users
- **Auto routing default** — saves 55% cost vs Sonnet-only while maintaining quality
- **RCTFC prompts** — reduces hallucinations by anchoring model to retrieved context only
- **Graceful degradation** — every optional component (guardrails, LangFuse, TinyLlama)
  fails safely with a warning; the core RAG pipeline always works

### How to Run the Complete Project
```bash
# 1. Provision infrastructure
cd terraform && terraform apply

# 2. Upload documents
python scripts/upload_documents.py

# 3. Create guardrail
python guardrails/setup_guardrail.py

# 4. Set .env values (KB ID, guardrail ID from terraform outputs + guardrail script)

# 5. Launch app
streamlit run app/main.py

# Optional: test routing, guardrails, observability
python gateway/test_routing.py
python guardrails/test_guardrail.py
```


---

## SECTION 3 — `docs/ARCHITECTURE.md`

Write this as a detailed technical architecture document. Include all sections:

### 1. System Components
List every component with its AWS service, purpose, and which phase built it:

| Component | AWS Service | Purpose | Phase |
|---|---|---|---|
| Document Store | Amazon S3 | Stores raw documents (txt, pdf) | 1 |
| Vector Store | OpenSearch Serverless | Stores document embeddings for similarity search | 1 |
| Embedding Model | Amazon Titan Embeddings v2 | Converts text to vectors | 1 |
| Knowledge Base | Amazon Bedrock Knowledge Bases | Managed retrieval — query → top-K chunks | 1 |
| Primary LLM | Claude 3 Sonnet (Bedrock) | Quality answer generation | 1 |
| Fast LLM | Claude 3 Haiku (Bedrock) | Low-cost answer generation | 1 |
| Vision LLM | Claude 3 Sonnet Vision (Bedrock) | Image + text answer generation | 1 |
| Self-Hosted LLM | TinyLlama 1.1B on EKS | Open-source inference, no token cost | 6 |
| Guardrail | Amazon Bedrock Guardrails | PII redaction, prompt injection blocking | 2 |
| AI Gateway | Custom Python module | Routes queries to optimal model | 3 |
| Conversation Store | SQLite (on EC2) | Persistent chat history | 1 |
| Observability | LangFuse (SaaS) | Trace every pipeline step | 5 |
| App Host | Amazon EC2 (t3.small) | Runs Streamlit application | 1+4 |
| IaC | Terraform | Provisions all AWS resources | 4 |

### 2. Component Interaction Diagram (ASCII)
```
User (Browser)
     │
     ▼
┌─────────────────────────────────────────────────────┐
│              Streamlit App (EC2 :8501)               │
│                                                       │
│  ┌──────────┐  ┌─────────────┐  ┌────────────────┐  │
│  │ Voice    │  │ Image       │  │ Text Input     │  │
│  │ Input    │  │ Upload      │  │ (chat_input)   │  │
│  └────┬─────┘  └──────┬──────┘  └───────┬────────┘  │
│       └───────────────┴─────────────────┘            │
│                        │                              │
│               ┌────────▼────────┐                    │
│               │   AI Gateway    │                    │
│               │   router.py     │                    │
│               │ ┌─────────────┐ │                    │
│               │ │ image_forced│ │                    │
│               │ │ user_select │ │                    │
│               │ │ auto_complex│ │                    │
│               └────────┬────────┘                    │
│                        │                              │
│          ┌─────────────┼──────────────┬────────────┐ │
│          ▼             ▼              ▼            ▼ │
│    ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────┐  │
│    │ Claude 3 │ │ Claude 3 │ │ Claude 3 │ │Tiny  │  │
│    │ Sonnet   │ │ Haiku    │ │ Sonnet   │ │Llama │  │
│    │(Bedrock) │ │(Bedrock) │ │(Vision)  │ │(EKS) │  │
│    └──────────┘ └──────────┘ └──────────┘ └──────┘  │
└─────────────────────────────────────────────────────┘
     │                                     │
     ▼                                     ▼
Amazon Bedrock                      LangFuse SaaS
Knowledge Base ──► OpenSearch       (Traces & Spans)
     │             Serverless
     ▼
  Amazon S3
(Documents)
```

### 3. RAG Pipeline Data Flow
Describe each step:
1. User submits a query (text / voice transcript / text + image)
2. Gateway scores the query → selects model
3. `retrieve_from_knowledge_base()` calls Bedrock Agent Runtime `retrieve()` API
4. OpenSearch Serverless finds top-K most similar document chunks by vector similarity
5. Chunks returned with S3 source URIs and relevance scores
6. `build_rag_prompt()` or `build_vision_prompt()` assembles RCTFC prompt with chunks
7. `generate_response()` calls Bedrock Runtime `invoke_model()` with prompt (+ image if vision)
8. Guardrail evaluates both the input prompt and output response
9. Answer returned with token counts, cost, model info
10. Response saved to SQLite conversation store
11. LangFuse trace flushed with all span data

### 4. Security Architecture
- **IAM roles** — EC2 uses instance profile with least-privilege Bedrock + S3 access
- **S3** — bucket blocks all public access, AES-256 server-side encryption, versioning enabled
- **OpenSearch Serverless** — access controlled by IAM data access policy (KB role only)
- **Guardrails** — all user inputs and model outputs pass through Bedrock Guardrails
- **Secrets** — stored in `.env` (never committed); production should use AWS SSM Parameter Store
- **EC2 SSH** — security group restricts SSH to specific IP (`my_ip_cidr` variable)
- **Streamlit** — runs on port 8501; production should add ALB + HTTPS

### 5. File Dependency Map
Show which files import from which — so any developer understands the dependency order:
```
app/config.py
  ← app/utils/bedrock_client.py
  ← app/utils/conversation_store.py
  ← gateway/llm_registry.py
      ← gateway/router.py
          ← app/utils/rag_engine.py
              ← app/utils/prompt_templates.py
              ← observability/langfuse_tracer.py
              ← bonus/eks/adapter.py
              ← app/components/sidebar.py
              ← app/pages/01_chat.py
                  ← app/components/chat_ui.py
                  ← app/components/voice_input.py
                  ← app/components/image_input.py
app/pages/02_analytics.py
  ← app/utils/conversation_store.py
app/main.py
  ← app/utils/conversation_store.py
  ← observability/langfuse_tracer.py
```

---

## SECTION 4 — `docs/FLOW_DIAGRAMS.md`

Write each diagram in ASCII art with a plain-English description below it.

### Diagram 1: User Query Flow (End-to-End)
```
User submits query
       │
       ▼
  Has image? ──Yes──► Force Vision Model
       │
      No
       ▼
  User picked model? ──Yes──► Use that model
       │
      No (Auto mode)
       ▼
  Complexity Score < 3? ──Yes──► Haiku (fast)
       │
      No
       ▼
  Sonnet (quality)
       │
       ▼
  Retrieve from Knowledge Base
  (top-K chunks by vector similarity)
       │
       ▼
  Build RCTFC Prompt
  (Role + Context chunks + Task + Format + Constraints)
       │
       ▼
  Apply Guardrail on INPUT
  (block PII, injection, off-topic)
       │
       ▼
  Invoke LLM
  (Bedrock or TinyLlama EKS)
       │
       ▼
  Apply Guardrail on OUTPUT
  (block PII in response)
       │
       ▼
  Return answer + sources + tokens + cost
       │
       ▼
  Save to SQLite + Trace to LangFuse
       │
       ▼
  Display in Streamlit UI
```

### Diagram 2: Auto Routing Decision Tree
```
                    New Query
                        │
                   Has image?
                  /          \
                Yes            No
                │               │
        Force Vision        User selection?
        Model               /           \
        (Sonnet)          Yes             No (Auto)
                          │                │
                    Use selected      Score query:
                    model             word count +
                                      keywords
                                          │
                                  Score ≥ 3?
                                 /          \
                               Yes            No
                               │              │
                           Sonnet          Haiku
                         (Quality)        (Fast)
```

### Diagram 3: RAG Retrieval Pipeline
```
Query Text
    │
    ▼
Titan Embeddings v2
(text → 1536-dim vector)
    │
    ▼
OpenSearch Serverless
(cosine similarity search)
    │
    ▼
Top-K chunks returned
[chunk_1: content + S3 URI + score]
[chunk_2: content + S3 URI + score]
[chunk_3: content + S3 URI + score]
    │
    ▼
RCTFC Prompt Builder
(chunks inserted into ## CONTEXT section)
    │
    ▼
LLM Generation
(answer grounded in chunk content only)
    │
    ▼
Answer + source citations
```

### Diagram 4: Conversation Persistence Flow
```
User sends message
    │
    ▼
conversation_id in session_state?
   /                     \
  No                     Yes
  │                       │
Create new            Use existing
conversation           conversation
(SQLite INSERT)            │
  │                        │
  └──────────┬─────────────┘
             │
             ▼
    save_message() to SQLite
    (role, content, model, tokens, cost)
             │
             ▼
    LangFuse trace: session_id = conversation_id
             │
             ▼
    Sidebar: Past Conversations list
    (get_all_conversations() → ordered by updated_at)
             │
             ▼
    User clicks past conversation
             │
             ▼
    get_conversation_messages(id)
    → load into st.session_state.chat_history
             │
             ▼
    Full chat history re-rendered in UI
```

### Diagram 5: LangFuse Trace Structure
```
Trace: "rag-query"
├── name:       "rag-query"
├── session_id: "<conversation UUID>"
├── input:      {query, has_image}
├── metadata:   {routing_strategy, routing_reason}
│
├── Span: "kb-retrieval"
│   ├── input:   {query, kb_id, max_results}
│   ├── output:  {chunks_returned, sources, top_score}
│   └── duration: <retrieval latency ms>
│
└── Generation: "llm-generation"
    ├── model:   "<bedrock model ID>"
    ├── input:   "<full RCTFC prompt>"
    ├── output:  "<answer text>"
    ├── usage:   {input_tokens, output_tokens, totalCost}
    └── duration: <generation latency ms>
```

### Diagram 6: Terraform Infrastructure Layout
```
AWS Account
└── Region: us-east-1
    │
    ├── S3 Bucket (module: s3)
    │   └── documents/ prefix
    │       ├── product_manual.txt
    │       ├── hr_policy.txt
    │       └── technical_guide.txt
    │
    ├── IAM Roles (module: iam)
    │   ├── knowledge-assistant-kb-role
    │   │   └── Policies: BedrockFull + S3ReadOnly
    │   └── knowledge-assistant-ec2-role
    │       └── Policies: BedrockFull + S3ReadOnly
    │
    ├── OpenSearch Serverless (module: opensearch)
    │   ├── Encryption policy
    │   ├── Network policy (public)
    │   ├── Data access policy (KB role)
    │   └── Collection: knowledge-assistant-dev (VECTORSEARCH)
    │
    ├── Bedrock Knowledge Base (module: bedrock)
    │   ├── KB: knowledge-assistant-kb-dev
    │   │   └── Embedding: Titan v2
    │   │   └── Storage: OpenSearch collection above
    │   └── Data Source: S3 bucket documents/ prefix
    │
    └── EC2 Instance (module: ec2)
        ├── AMI: Amazon Linux 2023
        ├── Type: t3.small
        ├── IAM Profile: knowledge-assistant-ec2-role
        ├── Security Group: SSH (your IP) + 8501 (open)
        └── user_data.sh: installs Python, clones repo, starts systemd service
```

### Diagram 7: CI/CD Pipeline Flow
```
Developer
    │
    ▼
git push → feature branch
    │
    ▼
Open Pull Request (GitHub)
    │
    ▼
Team review + approve PR
    │
    ▼
Merge to main branch
    │
    ▼
GitHub webhook fires
    │
    ▼
AWS CodePipeline triggered
    │
    ├── Stage 1: SOURCE
    │   └── Pull source zip from GitHub (main branch)
    │
    ├── Stage 2: BUILD (CodeBuild + buildspec.yaml)
    │   ├── Install: pip install requirements.txt
    │   ├── Pre-build: flake8 lint + pytest + routing test
    │   ├── Build: create deployment.zip
    │   └── Post-build: confirm artifact ready
    │
    └── Stage 3: DEPLOY
        ├── Upload deployment.zip to EC2 via SCP
        ├── Extract to /home/appuser/capstone/
        └── systemctl restart knowledge-assistant
            │
            ▼
        App live at http://<ec2-ip>:8501
```


---

## SECTION 5 — Test Suite

### `tests/test_rag_engine.py`
Unit tests for the RAG pipeline. Uses `unittest.mock` to patch AWS calls — no real AWS needed.

```python
"""
Unit tests for app/utils/rag_engine.py
Tests routing, cost calculation, error handling, and return dict shape.
Run: pytest tests/test_rag_engine.py -v
"""
import pytest
from unittest.mock import patch, MagicMock
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestRunRagQuery:
    """Tests for run_rag_query() — main pipeline orchestrator."""

    def test_returns_error_when_kb_not_configured(self):
        """If KNOWLEDGE_BASE_ID is empty, return error dict immediately."""
        with patch("app.utils.rag_engine.KNOWLEDGE_BASE_ID", ""):
            from app.utils.rag_engine import run_rag_query
            result = run_rag_query("test query")
        assert result["error"] is not None
        assert "Knowledge Base not configured" in result["error"]
        assert result["answer"] == ""

    def test_return_dict_has_required_keys(self):
        """Return dict must always have all required keys."""
        required_keys = [
            "answer", "sources", "input_tokens", "output_tokens",
            "model_id", "model_name", "routing_reason", "cost_usd", "error"
        ]
        with patch("app.utils.rag_engine.KNOWLEDGE_BASE_ID", ""):
            from app.utils.rag_engine import run_rag_query
            result = run_rag_query("test")
        for key in required_keys:
            assert key in result, f"Missing key: {key}"

    def test_cost_calculation_sonnet(self):
        """Cost should be correctly calculated from token counts and MODEL_COSTS."""
        from app.config import PRIMARY_MODEL_ID, MODEL_COSTS
        cost_config = MODEL_COSTS[PRIMARY_MODEL_ID]
        input_tokens  = 800
        output_tokens = 300
        expected_cost = (input_tokens / 1000 * cost_config["input"]) + \
                        (output_tokens / 1000 * cost_config["output"])
        # 800/1000 * 0.003 + 300/1000 * 0.015 = 0.0024 + 0.0045 = 0.0069
        assert abs(expected_cost - 0.0069) < 0.0001

    def test_cost_calculation_haiku(self):
        """Haiku should be ~12x cheaper than Sonnet per query."""
        from app.config import PRIMARY_MODEL_ID, SECONDARY_MODEL_ID, MODEL_COSTS
        sonnet = MODEL_COSTS[PRIMARY_MODEL_ID]
        haiku  = MODEL_COSTS[SECONDARY_MODEL_ID]
        sonnet_cost = (800/1000 * sonnet["input"]) + (300/1000 * sonnet["output"])
        haiku_cost  = (800/1000 * haiku["input"])  + (300/1000 * haiku["output"])
        ratio = sonnet_cost / haiku_cost
        assert ratio > 10, f"Expected Sonnet to be 10x+ more expensive, got ratio={ratio:.1f}"


class TestRetrieveFromKnowledgeBase:
    """Tests for retrieve_from_knowledge_base()."""

    def test_returns_list_of_dicts(self):
        """Must return a list of dicts with content, source, score keys."""
        mock_response = {
            "retrievalResults": [
                {
                    "content": {"text": "Test content"},
                    "location": {"s3Location": {"uri": "s3://bucket/doc.txt"}},
                    "score": 0.85
                }
            ]
        }
        mock_client = MagicMock()
        mock_client.retrieve.return_value = mock_response

        with patch("app.utils.rag_engine.get_bedrock_agent_runtime",
                   return_value=mock_client):
            from app.utils.rag_engine import retrieve_from_knowledge_base
            chunks = retrieve_from_knowledge_base("query", "kb-123", 5)

        assert len(chunks) == 1
        assert chunks[0]["content"] == "Test content"
        assert chunks[0]["source"] == "s3://bucket/doc.txt"
        assert chunks[0]["score"] == 0.85

    def test_returns_empty_list_on_no_results(self):
        """Empty retrievalResults must return empty list, not crash."""
        mock_client = MagicMock()
        mock_client.retrieve.return_value = {"retrievalResults": []}
        with patch("app.utils.rag_engine.get_bedrock_agent_runtime",
                   return_value=mock_client):
            from app.utils.rag_engine import retrieve_from_knowledge_base
            chunks = retrieve_from_knowledge_base("query", "kb-123", 5)
        assert chunks == []
```

---

### `tests/test_router.py`
Unit tests for gateway routing logic. No AWS calls needed.

```python
"""
Unit tests for gateway/router.py
Tests all three routing strategies and edge cases.
Run: pytest tests/test_router.py -v
"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from gateway.router import route, _score_complexity


class TestScoreComplexity:
    """Tests for the internal complexity scoring function."""

    def test_short_query_is_simple(self):
        result = _score_complexity("What is the leave policy?")
        assert result["is_complex"] is False
        assert result["score"] < 3

    def test_long_query_is_complex(self):
        query = ("Can you explain in detail the difference between the remote work policy "
                 "and the office attendance policy, and describe what exceptions are allowed?")
        result = _score_complexity(query)
        assert result["is_complex"] is True
        assert result["score"] >= 3

    def test_explain_keyword_increases_score(self):
        simple  = _score_complexity("What is the policy?")
        complex_ = _score_complexity("Explain the policy in detail please.")
        assert complex_["score"] > simple["score"]

    def test_compare_keyword_increases_score(self):
        result = _score_complexity("Compare Sonnet and Haiku models.")
        assert result["score"] >= 2

    def test_word_count_tracked(self):
        result = _score_complexity("What is the policy?")
        assert result["word_count"] == 5


class TestRoute:
    """Tests for the main route() function."""

    def test_image_always_forces_vision(self):
        result = route("Any query", "Auto", has_image=True)
        assert result["strategy"] == "image_forced"
        assert result["model"].tier == "vision"

    def test_image_overrides_user_selection(self):
        """Even if user picks Haiku, image forces Vision."""
        result = route("Any query", "Fast (Claude Haiku)", has_image=True)
        assert result["strategy"] == "image_forced"
        assert result["model"].tier == "vision"

    def test_user_selection_sonnet(self):
        result = route("Any query", "Quality (Claude Sonnet)", has_image=False)
        assert result["strategy"] == "user_selection"
        assert result["model"].key == "sonnet"

    def test_user_selection_haiku(self):
        result = route("Any query", "Fast (Claude Haiku)", has_image=False)
        assert result["strategy"] == "user_selection"
        assert result["model"].key == "haiku"

    def test_user_selection_tinyllama(self):
        result = route("Any query", "Self-Hosted (TinyLlama)", has_image=False)
        assert result["strategy"] == "user_selection"
        assert result["model"].key == "tinyllama"

    def test_auto_simple_routes_to_haiku(self):
        result = route("What is the leave allowance?", "Auto", has_image=False)
        assert result["strategy"] == "auto_complexity"
        assert result["model"].key == "haiku"

    def test_auto_complex_routes_to_sonnet(self):
        query = ("Can you explain the detailed difference between remote work policy "
                 "and office attendance requirements including all exceptions?")
        result = route(query, "Auto", has_image=False)
        assert result["strategy"] == "auto_complexity"
        assert result["model"].key == "sonnet"

    def test_return_dict_has_all_keys(self):
        result = route("test query", "Auto", has_image=False)
        for key in ["model", "model_id", "model_name", "strategy", "reason"]:
            assert key in result, f"Missing key: {key}"

    def test_reason_is_non_empty_string(self):
        result = route("test query", "Auto", has_image=False)
        assert isinstance(result["reason"], str)
        assert len(result["reason"]) > 0
```

---

### `tests/test_conversation_store.py`
Unit tests for SQLite conversation persistence.

```python
"""
Unit tests for app/utils/conversation_store.py
Uses a temporary in-memory DB to avoid touching the real conversations.db
Run: pytest tests/test_conversation_store.py -v
"""
import pytest
import os
import sys
import tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(autouse=True)
def temp_db(monkeypatch, tmp_path):
    """Redirect DB_PATH to a temp file for each test."""
    db_file = str(tmp_path / "test_conversations.db")
    monkeypatch.setattr("app.utils.conversation_store.DB_PATH", db_file)
    monkeypatch.setattr("app.config.DB_PATH", db_file)
    from app.utils.conversation_store import init_db
    init_db()
    return db_file


class TestConversationStore:

    def test_create_conversation_returns_id(self):
        from app.utils.conversation_store import create_conversation
        conv_id = create_conversation("Test conversation title")
        assert isinstance(conv_id, str)
        assert len(conv_id) > 0

    def test_get_all_conversations_empty_initially(self):
        from app.utils.conversation_store import get_all_conversations
        convs = get_all_conversations()
        assert convs == []

    def test_create_and_retrieve_conversation(self):
        from app.utils.conversation_store import (
            create_conversation, get_all_conversations
        )
        create_conversation("My first conversation")
        convs = get_all_conversations()
        assert len(convs) == 1
        assert convs[0]["title"] == "My first conversation"

    def test_save_and_retrieve_messages(self):
        from app.utils.conversation_store import (
            create_conversation, save_message, get_conversation_messages
        )
        conv_id = create_conversation("Test")
        save_message(conv_id, "user", "Hello")
        save_message(conv_id, "assistant", "Hi there",
                     model_name="Claude 3 Haiku",
                     input_tokens=10, output_tokens=5, cost_usd=0.0001)
        msgs = get_conversation_messages(conv_id)
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[0]["content"] == "Hello"
        assert msgs[1]["role"] == "assistant"
        assert msgs[1]["model_name"] == "Claude 3 Haiku"

    def test_delete_conversation(self):
        from app.utils.conversation_store import (
            create_conversation, delete_conversation, get_all_conversations
        )
        conv_id = create_conversation("To be deleted")
        assert len(get_all_conversations()) == 1
        delete_conversation(conv_id)
        assert len(get_all_conversations()) == 0

    def test_get_stats_returns_correct_totals(self):
        from app.utils.conversation_store import (
            create_conversation, save_message, get_all_stats
        )
        conv_id = create_conversation("Stats test")
        save_message(conv_id, "user", "q1")
        save_message(conv_id, "assistant", "a1",
                     input_tokens=100, output_tokens=50, cost_usd=0.005)
        save_message(conv_id, "user", "q2")
        save_message(conv_id, "assistant", "a2",
                     input_tokens=200, output_tokens=80, cost_usd=0.01)
        stats = get_all_stats()
        assert stats["total_conversations"] == 1
        assert stats["total_messages"] == 4
        assert stats["total_input_tokens"] == 300
        assert stats["total_output_tokens"] == 130
        assert abs(stats["total_cost_usd"] - 0.015) < 0.0001
```


---

### `tests/test_prompt_templates.py`
Unit tests for RCTFC prompt builders.

```python
"""
Unit tests for app/utils/prompt_templates.py
Verifies RCTFC sections are present in generated prompts.
Run: pytest tests/test_prompt_templates.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.utils.prompt_templates import build_rag_prompt, build_vision_prompt


SAMPLE_CHUNKS = [
    {"content": "Annual leave is 20 days per year.",
     "source": "s3://bucket/documents/hr_policy.txt", "score": 0.9},
    {"content": "Remote work is allowed 3 days per week.",
     "source": "s3://bucket/documents/hr_policy.txt", "score": 0.8},
]


class TestBuildRagPrompt:

    def test_contains_all_rctfc_sections(self):
        prompt = build_rag_prompt("What is the leave policy?", SAMPLE_CHUNKS)
        for section in ["## ROLE", "## CONTEXT", "## TASK", "## FORMAT", "## CONSTRAINTS"]:
            assert section in prompt, f"Missing RCTFC section: {section}"

    def test_query_appears_in_prompt(self):
        query = "What is the leave policy?"
        prompt = build_rag_prompt(query, SAMPLE_CHUNKS)
        assert query in prompt

    def test_chunk_content_appears_in_context(self):
        prompt = build_rag_prompt("query", SAMPLE_CHUNKS)
        assert "Annual leave is 20 days per year." in prompt

    def test_source_filename_appears_in_context(self):
        prompt = build_rag_prompt("query", SAMPLE_CHUNKS)
        assert "hr_policy.txt" in prompt

    def test_empty_chunks_does_not_crash(self):
        prompt = build_rag_prompt("query", [])
        assert "## ROLE" in prompt
        assert "## CONSTRAINTS" in prompt

    def test_prompt_ends_with_answer_marker(self):
        prompt = build_rag_prompt("query", SAMPLE_CHUNKS)
        assert prompt.strip().endswith("Answer:")


class TestBuildVisionPrompt:

    def test_contains_all_rctfc_sections(self):
        prompt = build_vision_prompt("What is in this image?", SAMPLE_CHUNKS)
        for section in ["## ROLE", "## CONTEXT", "## TASK", "## FORMAT", "## CONSTRAINTS"]:
            assert section in prompt

    def test_vision_prompt_mentions_image(self):
        prompt = build_vision_prompt("What does this show?", SAMPLE_CHUNKS)
        assert "image" in prompt.lower()

    def test_vision_prompt_different_from_text_prompt(self):
        text_prompt   = build_rag_prompt("query", SAMPLE_CHUNKS)
        vision_prompt = build_vision_prompt("query", SAMPLE_CHUNKS)
        assert text_prompt != vision_prompt
```

---

### `tests/test_guardrail_config.py`
Unit tests verifying guardrail config constants are correctly structured.

```python
"""
Unit tests for guardrails/guardrail_config.py
Verifies constants have the correct structure expected by the Bedrock API.
Run: pytest tests/test_guardrail_config.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from guardrails.guardrail_config import (
    GUARDRAIL_NAME, PII_ENTITIES, DENIED_TOPICS, CONTENT_FILTERS,
    BLOCKED_INPUT_MESSAGE, BLOCKED_OUTPUT_MESSAGE
)


class TestGuardrailConfig:

    def test_guardrail_name_not_empty(self):
        assert isinstance(GUARDRAIL_NAME, str)
        assert len(GUARDRAIL_NAME) > 0

    def test_pii_entities_have_required_keys(self):
        for entity in PII_ENTITIES:
            assert "type" in entity,   f"Missing 'type' in {entity}"
            assert "action" in entity, f"Missing 'action' in {entity}"
            assert entity["action"] in ("ANONYMIZE", "BLOCK"), \
                f"Invalid action: {entity['action']}"

    def test_pii_entities_covers_email_and_phone(self):
        types = [e["type"] for e in PII_ENTITIES]
        assert "EMAIL" in types
        assert "PHONE" in types

    def test_denied_topics_have_required_keys(self):
        for topic in DENIED_TOPICS:
            assert "name" in topic
            assert "definition" in topic
            assert "examples" in topic
            assert "type" in topic
            assert isinstance(topic["examples"], list)
            assert len(topic["examples"]) > 0
            assert topic["type"] == "DENY"

    def test_prompt_injection_topic_exists(self):
        names = [t["name"] for t in DENIED_TOPICS]
        assert "PromptInjection" in names

    def test_content_filters_have_required_keys(self):
        for f in CONTENT_FILTERS:
            assert "type" in f
            assert "inputStrength" in f
            assert "outputStrength" in f
            assert f["inputStrength"]  in ("NONE","LOW","MEDIUM","HIGH")
            assert f["outputStrength"] in ("NONE","LOW","MEDIUM","HIGH")

    def test_blocked_messages_not_empty(self):
        assert len(BLOCKED_INPUT_MESSAGE)  > 10
        assert len(BLOCKED_OUTPUT_MESSAGE) > 10
```

---

### `tests/integration/test_integration_stubs.py`
Integration test stubs. These document what would be tested against real AWS.
They are marked with `pytest.mark.skip` so they don't run in CI without credentials.

```python
"""
Integration test stubs for the Knowledge Assistant.
These require real AWS credentials and a configured .env.

To run a specific test (with real AWS):
    pytest tests/integration/test_integration_stubs.py::TestKnowledgeBase -v -s

All tests are skipped by default in CI.
"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


@pytest.mark.skip(reason="Requires real AWS credentials and KNOWLEDGE_BASE_ID in .env")
class TestKnowledgeBase:

    def test_retrieval_returns_chunks(self):
        """Real KB retrieval should return at least 1 chunk for a known query."""
        from dotenv import load_dotenv
        load_dotenv()
        from app.config import KNOWLEDGE_BASE_ID
        from app.utils.rag_engine import retrieve_from_knowledge_base
        chunks = retrieve_from_knowledge_base("annual leave policy", KNOWLEDGE_BASE_ID, 3)
        assert len(chunks) >= 1
        assert all("content" in c for c in chunks)

    def test_retrieval_scores_between_0_and_1(self):
        """All relevance scores must be between 0.0 and 1.0."""
        from dotenv import load_dotenv; load_dotenv()
        from app.config import KNOWLEDGE_BASE_ID
        from app.utils.rag_engine import retrieve_from_knowledge_base
        chunks = retrieve_from_knowledge_base("leave policy", KNOWLEDGE_BASE_ID, 5)
        for chunk in chunks:
            assert 0.0 <= chunk["score"] <= 1.0


@pytest.mark.skip(reason="Requires real AWS credentials and valid model access")
class TestBedrockGeneration:

    def test_full_rag_query_returns_answer(self):
        """Full RAG pipeline should return a non-empty answer."""
        from dotenv import load_dotenv; load_dotenv()
        from app.utils.rag_engine import run_rag_query
        result = run_rag_query("What is the annual leave allowance?", "Auto")
        assert result["error"] is None
        assert len(result["answer"]) > 0
        assert result["input_tokens"] > 0
        assert result["cost_usd"] > 0

    def test_rag_query_returns_sources(self):
        """Full RAG pipeline should return source citations."""
        from dotenv import load_dotenv; load_dotenv()
        from app.utils.rag_engine import run_rag_query
        result = run_rag_query("What is the sick leave policy?", "Auto")
        assert result["error"] is None
        assert len(result["sources"]) >= 1


@pytest.mark.skip(reason="Requires real GUARDRAIL_ID in .env")
class TestGuardrail:

    def test_pii_query_is_processed(self):
        """Query with email should not crash — guardrail anonymizes it."""
        from dotenv import load_dotenv; load_dotenv()
        from app.utils.rag_engine import run_rag_query
        result = run_rag_query(
            "Send leave policy to test@example.com", "Auto", use_guardrails=True
        )
        # Should not error — guardrail anonymizes, doesn't crash
        assert result is not None


@pytest.mark.skip(reason="Requires TINYLLAMA_ENDPOINT running")
class TestTinyLlama:

    def test_health_check_returns_true(self):
        """Health endpoint should return 200 when server is running."""
        from bonus.eks.adapter import health_check
        assert health_check() is True

    def test_generate_returns_answer(self):
        """Self-hosted model should return a non-empty answer."""
        from bonus.eks.adapter import call_self_hosted
        result = call_self_hosted("What is 2 + 2? Answer in one word.")
        assert "answer" in result
        assert len(result["answer"]) > 0
        assert result["cost_usd"] == 0.0
```

---

### `docs/TESTING.md`
Write a clean markdown document covering:

#### Section 1: Test Strategy
| Test Type | Coverage | Tools | Real AWS? |
|---|---|---|---|
| Unit tests | Routing logic, prompt templates, guardrail config, conversation store | pytest + unittest.mock | No |
| Integration tests | Full RAG pipeline, KB retrieval, guardrail, TinyLlama | pytest (skip markers) | Yes |
| Manual demo tests | Routing demo, guardrail demo | Python scripts | Yes |

#### Section 2: How to Run Tests
```bash
# Install test dependencies
pip install pytest

# Run all unit tests (no AWS needed)
pytest tests/ -v --ignore=tests/integration/

# Run with coverage report
pytest tests/ --ignore=tests/integration/ --cov=app --cov=gateway --cov=guardrails

# Run a specific test file
pytest tests/test_router.py -v

# Run manual demo scripts (requires AWS credentials)
python gateway/test_routing.py      # routing decisions (no AWS)
python guardrails/test_guardrail.py # PII + injection demo (requires AWS)
```

#### Section 3: Test File Map
Table mapping each test file to the module it tests and what it verifies.

#### Section 4: What is NOT tested (and why)
- Streamlit UI components — require a browser; use manual screenshot testing
- Real Bedrock API calls — covered by integration stubs; requires AWS credentials and costs money
- LangFuse tracing — verified by viewing traces in cloud.langfuse.com dashboard
- Terraform — verified by `terraform plan` and `terraform apply`


---

## SECTION 6 — CI/CD Theory (Bonus B — Full Document)

### `bonus/cicd/cicd_theory.md`
Write this in full markdown with all 6 sections below.

---

#### Section 1: GitHub Integration

**What it is:**
GitHub hosts the project source code. It is the single source of truth for all application
code, Terraform, tests, and documentation.

**How this project uses GitHub:**
- The repository contains all code under version control
- Developers work on feature branches (e.g. `feature/add-voice-input`)
- Changes go through Pull Requests to the `main` branch
- `main` is protected — direct pushes are blocked; a PR review is required
- When a PR is merged to `main`, GitHub fires a webhook that triggers AWS CodePipeline

**Key concepts:**
| Concept | Definition |
|---|---|
| Repository | The codebase hosted on GitHub |
| Branch | An isolated line of development |
| Pull Request | A request to merge a feature branch into main |
| Branch protection | Rule that requires review before merge |
| Webhook | HTTP call GitHub sends to AWS when an event occurs |
| GitHub Actions | Optional: CI (lint/test) that runs inside GitHub on PR events |
| CodeStar Connection | AWS service that authorises CodePipeline to read your GitHub repo |

---

#### Section 2: AWS CodePipeline

**What it is:**
AWS CodePipeline is a fully managed CI/CD service. It orchestrates the stages that take
code from source to deployed application automatically.

**Pipeline structure for this project:**
```
┌─────────────────────────────────────────────────┐
│             AWS CodePipeline                     │
│                                                  │
│  Stage 1: SOURCE                                 │
│  ├── Provider: GitHub (via CodeStar Connection)  │
│  ├── Branch: main                                │
│  └── Trigger: webhook on push                    │
│                                                  │
│  Stage 2: BUILD                                  │
│  ├── Provider: AWS CodeBuild                     │
│  ├── Build spec: buildspec.yaml (repo root)      │
│  └── Outputs: deployment.zip artifact            │
│                                                  │
│  Stage 3: DEPLOY                                 │
│  ├── Provider: AWS CodeDeploy or custom action   │
│  ├── Target: EC2 instance                        │
│  └── Action: extract zip + restart systemd       │
└─────────────────────────────────────────────────┘
```

**Key concepts:**
| Concept | Definition |
|---|---|
| Stage | A logical phase in the pipeline (Source, Build, Deploy) |
| Action | A step within a stage |
| Artifact | Files passed between stages (source zip, deployment zip) |
| Artifact store | S3 bucket CodePipeline uses to store artifacts |
| Service role | IAM role CodePipeline assumes to access other services |
| Approval action | Optional manual gate between stages |

---

#### Section 3: buildspec.yaml — Complete Annotated File

```yaml
# buildspec.yaml — AWS CodeBuild build specification file
# Location: project root (same level as requirements.txt)
# Tells CodeBuild exactly what to run at each phase of the build.

version: 0.2    # Always 0.2 — the current and only stable version

# Environment variables available during the build
env:
  variables:
    # Non-sensitive config — safe to hardcode
    AWS_REGION: "us-east-1"
    APP_DIR: "."

  # Sensitive values pulled from AWS SSM Parameter Store at build time
  # Never put real secrets in buildspec.yaml or environment variables directly
  parameter-store:
    KNOWLEDGE_BASE_ID: "/knowledge-assistant/prod/KNOWLEDGE_BASE_ID"
    GUARDRAIL_ID:       "/knowledge-assistant/prod/GUARDRAIL_ID"
    S3_BUCKET_NAME:     "/knowledge-assistant/prod/S3_BUCKET_NAME"

phases:

  # ── install phase ─────────────────────────────────────────────────────────
  # Runs first. Set up the build environment.
  # Changes here do NOT persist to later phases (use artifacts for that).
  install:
    runtime-versions:
      python: 3.11          # Request specific Python version from CodeBuild image
    commands:
      - echo "Installing Python dependencies..."
      - pip install --upgrade pip
      - pip install -r requirements.txt     # install app packages
      - pip install pytest flake8           # install test + lint tools

  # ── pre_build phase ────────────────────────────────────────────────────────
  # Quality gate. If any command fails, the build stops here.
  pre_build:
    commands:
      - echo "=== Linting ==="
      # Check code style — || true means lint warnings don't fail the build
      - flake8 app/ gateway/ guardrails/ observability/ \
          --max-line-length=120 \
          --exclude=__pycache__,venv \
          || true

      - echo "=== Unit Tests ==="
      # Run unit tests — skip integration tests (need real AWS)
      - pytest tests/ -v --ignore=tests/integration/ --tb=short

      - echo "=== Routing Demo (functional test) ==="
      # This must pass — it validates core routing logic with no AWS calls
      - python gateway/test_routing.py

  # ── build phase ────────────────────────────────────────────────────────────
  # Main build step. Creates the deployment artifact.
  build:
    commands:
      - echo "Build started: $(date)"

      # Write .env file using values from SSM Parameter Store
      # (injected as env vars by the parameter-store section above)
      - |
        cat > .env <<EOF
        AWS_REGION=${AWS_REGION}
        KNOWLEDGE_BASE_ID=${KNOWLEDGE_BASE_ID}
        GUARDRAIL_ID=${GUARDRAIL_ID}
        S3_BUCKET_NAME=${S3_BUCKET_NAME}
        EOF

      # Create deployment zip — exclude unnecessary files
      - zip -r deployment.zip . \
          --exclude "*.pyc" \
          --exclude "__pycache__/*" \
          --exclude ".terraform/*" \
          --exclude "data/*" \
          --exclude ".git/*" \
          --exclude "tests/*" \
          --exclude "*.tfstate*"

      - echo "Build complete: $(date)"
      - ls -lh deployment.zip

  # ── post_build phase ───────────────────────────────────────────────────────
  # Runs regardless of build success or failure.
  # Use for notifications, cleanup, or final logging.
  post_build:
    commands:
      - echo "Post-build phase"
      - |
        if [ "$CODEBUILD_BUILD_SUCCEEDING" = "1" ]; then
          echo "BUILD SUCCEEDED"
        else
          echo "BUILD FAILED — check logs above"
        fi

# Artifacts: what CodePipeline passes to the Deploy stage
artifacts:
  files:
    - deployment.zip          # main app package
  discard-paths: no           # keep directory structure inside the zip

# Cache: reuse pip download cache between builds (speeds up installs)
cache:
  paths:
    - "/root/.cache/pip/**/*"
```

---

#### Section 4: Full CI/CD Workflow — Step by Step

1. **Developer creates a feature branch**
   ```bash
   git checkout -b feature/add-voice-input
   # make changes
   git add app/components/voice_input.py
   git commit -m "Add voice input component"
   git push origin feature/add-voice-input
   ```

2. **Pull Request opened on GitHub**
   - PR description explains the change
   - Team member reviews the code
   - (Optional) GitHub Actions runs a quick lint check automatically

3. **PR approved and merged to `main`**
   - GitHub fires a webhook to AWS CodePipeline

4. **Stage 1 — SOURCE**
   - CodePipeline pulls the latest `main` branch as a zip
   - Stores the zip in the artifact S3 bucket

5. **Stage 2 — BUILD (CodeBuild)**
   - CodeBuild starts a fresh container with Python 3.11
   - Runs `buildspec.yaml` phases in order:
     - install → pre_build (tests) → build (zip) → post_build
   - If any test fails → pipeline stops, team is notified
   - On success → `deployment.zip` uploaded to artifact bucket

6. **Stage 3 — DEPLOY**
   - CodeDeploy (or a CodeBuild deploy action) SSHs into the EC2 instance
   - Uploads `deployment.zip`
   - Extracts to `/home/appuser/capstone/`
   - Restarts the systemd service:
     ```bash
     systemctl restart knowledge-assistant
     ```

7. **Verification**
   - Access `http://<ec2-ip>:8501` to confirm the app is live
   - Check LangFuse dashboard to confirm traces are arriving

8. **If deployment fails**
   - CodePipeline stops at the failed stage
   - SNS notification sent to the team email
   - Developer checks CodeBuild logs in CloudWatch
   - Fix, push, and the pipeline retriggers automatically

---

#### Section 5: Key Benefits for This Project
| Benefit | How it applies |
|---|---|
| Automated testing | Routing logic, unit tests verified on every push |
| Consistent deployments | Same steps every time — no manual SSH and copy |
| Audit trail | Every deployment logged in CodePipeline console |
| Rollback | Re-run a previous pipeline execution to redeploy older code |
| Team collaboration | PR review gates prevent untested code reaching production |
| Secret management | SSM Parameter Store keeps KB ID, guardrail ID out of code |

---

#### Section 6: Concepts Summary Table
| Concept | What it is | Role in this project |
|---|---|---|
| GitHub | Code hosting platform | Source of truth for all code |
| Pull Request | Code review mechanism | Gate before merge to main |
| Branch protection | GitHub rule: require review | Prevents direct pushes to main |
| CodePipeline | CI/CD orchestrator | Automates Source → Build → Deploy |
| CodeBuild | Managed build server | Runs buildspec.yaml, creates artifact |
| buildspec.yaml | Build instructions file | Defines install, test, package steps |
| Artifact | File passed between stages | deployment.zip |
| CodeStar Connection | GitHub-AWS auth | Lets CodePipeline read GitHub |
| SSM Parameter Store | Secure secret storage | Holds KB ID, guardrail ID |
| systemd service | Linux service manager | Keeps Streamlit running, auto-restarts |

---

## SECTION 7 — `.gitignore`

Create this file at the project root to prevent secrets and build artifacts being committed.

```gitignore
# Environment and secrets — NEVER commit
.env
*.env

# Terraform state and local files
terraform/.terraform/
terraform/*.tfstate
terraform/*.tfstate.backup
terraform/terraform.tfvars

# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
venv/
.venv/
env/
*.egg-info/
dist/
build/

# SQLite conversation database
data/conversations.db
data/*.db

# Streamlit cache
.streamlit/

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db

# Test artifacts
.pytest_cache/
.coverage
htmlcov/

# Deployment artifacts
deployment.zip
*.zip
```

---

## Order to Create Files
1. `tests/__init__.py` (empty)
2. `tests/integration/__init__.py` (empty)
3. `tests/test_rag_engine.py`
4. `tests/test_router.py`
5. `tests/test_conversation_store.py`
6. `tests/test_prompt_templates.py`
7. `tests/test_guardrail_config.py`
8. `tests/integration/test_integration_stubs.py`
9. `docs/PROJECT_SUMMARY.md`
10. `docs/ARCHITECTURE.md`
11. `docs/FLOW_DIAGRAMS.md`
12. `docs/TESTING.md`
13. `bonus/cicd/cicd_theory.md`
14. `bonus/cicd/buildspec.yaml`
15. `.gitignore`
16. Confirm/add tinyllama to `gateway/llm_registry.py`
17. Confirm/add "Self-Hosted (TinyLlama)" to `gateway/router.py`
18. Confirm/add 5th option + health indicator to `app/components/sidebar.py`
19. Confirm/add adapter branch to `app/utils/rag_engine.py`
20. Add `TINYLLAMA_ENDPOINT` to `.env.template`

---

## How to Run Tests (for the human)
```bash
# Run all unit tests — no AWS credentials needed
pytest tests/ -v --ignore=tests/integration/

# Expected output: all tests PASS
# tests/test_router.py::TestRoute::test_image_always_forces_vision PASSED
# tests/test_router.py::TestRoute::test_auto_simple_routes_to_haiku PASSED
# ... (30+ tests total)

# Run with coverage
pip install pytest-cov
pytest tests/ --ignore=tests/integration/ --cov=app --cov=gateway --cov=guardrails --cov-report=term-missing
```

---

## Definition of Done

### EKS Integration
- Sidebar has exactly 5 model options including "Self-Hosted TinyLlama — EKS"
- Selecting TinyLlama shows health check status in sidebar
- When TinyLlama server is running, queries are answered via `bonus/eks/adapter.py`
- When TinyLlama server is down, a clear error message shown (no Python traceback)
- `cost_usd` is 0.0 for TinyLlama queries in the analytics dashboard

### Tests
- All 5 unit test files created and pass with `pytest tests/ --ignore=tests/integration/`
- Integration stubs exist and are correctly skipped with `@pytest.mark.skip`
- `docs/TESTING.md` explains how to run each test type

### Documentation
- `docs/PROJECT_SUMMARY.md` — requirements completion table shows all 9 items ✅
- `docs/ARCHITECTURE.md` — all 5 sections complete including ASCII component diagram
- `docs/FLOW_DIAGRAMS.md` — all 7 flow diagrams with ASCII art and descriptions
- `.gitignore` exists and includes `.env`, `*.tfstate`, `data/conversations.db`

### CI/CD Theory
- `bonus/cicd/cicd_theory.md` — all 6 sections complete
- `bonus/cicd/buildspec.yaml` — valid YAML with a comment on every meaningful line
- Document covers: GitHub integration, CodePipeline stages, buildspec phases, full workflow
