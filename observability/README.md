# LangFuse Monitoring & Observability Integration

## 1. What is LangFuse?
LangFuse is an open-source SaaS observability platform for LLM applications. It captures every step of the RAG pipeline as structured traces visible in a real-time web dashboard.

Key capabilities integrated in this capstone:
- **End-to-End Traces**: Track user queries from input to response.
- **Spans & Steps**: Isolate vector retrieval (`kb-retrieval`) latency vs LLM generation (`llm-generation`) latency.
- **Token & Cost Tracking**: Log exact input tokens, output tokens, and calculated USD expenditure.
- **Session Grouping**: Group traces by conversation ID to analyze full user chat histories.
- **Error Observability**: Record exceptions and guardrail blocks with `ERROR` status tags.

---

## 2. Setup Guide

1. Create a free account at [https://cloud.langfuse.com](https://cloud.langfuse.com).
2. Click **New Project** -> name it `knowledge-assistant`.
3. Navigate to **Settings** -> **API Keys** -> **Create new key pair**.
4. Add keys to your local `.env` file:
   ```env
   LANGFUSE_PUBLIC_KEY=pk-lf-...
   LANGFUSE_SECRET_KEY=sk-lf-...
   LANGFUSE_HOST=https://cloud.langfuse.com
   ```
5. Restart the Streamlit app.
6. Submit queries via the Chat page (`app/pages/01_chat.py`).
7. Open `https://cloud.langfuse.com` -> **Traces** to view incoming real-time telemetry.

*Note: If `LANGFUSE_PUBLIC_KEY` is not set, tracing operates as a silent, graceful no-op.*

---

## 3. Trace Hierarchy & Structure

```text
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

---

## 4. Key Metrics to Monitor

| Metric | Dashboard Location | Diagnostic Purpose |
|---|---|---|
| **End-to-End Latency** | Trace duration | > 10s indicates potential OpenSearch or network bottlenecks |
| **Retrieval Latency** | `kb-retrieval` span duration | > 3s indicates vector search slowdowns |
| **Generation Latency** | `llm-generation` span duration | Haiku should respond in < 2s; Sonnet in < 5s |
| **Token Expenditure** | Generation `usage.input`/`output` | Spikes indicate excessive context chunking |
| **Cost Per Query** | Generation `usage.totalCost` | Compares cost footprint between Sonnet and Haiku |
| **Session Traces** | Sessions tab | Groups all traces for a single user chat session |
| **Error Events** | Trace status = `ERROR` | Immediately flags pipeline or API exceptions |

---

## 5. Submission Artifact Screenshots Guide

To document Phase 5 compliance for evaluation:
1. **Traces List**: Overview showing multiple `rag-query` traces.
2. **Single Trace Detail**: Expanded tree showing `kb-retrieval` and `llm-generation` spans.
3. **Generation Detail**: Deep dive into LLM prompt input and token count usage.
4. **Session Overview**: Grouped view of traces sharing a `session_id`.
5. **Dashboard Analytics**: Aggregated token expenditure and cost summary charts.
