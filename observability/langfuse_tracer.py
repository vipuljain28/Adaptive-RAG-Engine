"""
LangFuse observability wrapper for the Knowledge Assistant RAG pipeline.

Traces every query end-to-end:
  Trace
    └── Span: retrieval       (KB query -> chunks returned)
    └── Generation: llm_call  (prompt -> answer, tokens, cost)

If LANGFUSE_PUBLIC_KEY is empty, all functions are no-ops — app works without tracing.
"""

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import (
    LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST
)

# Only import langfuse if keys are configured
_langfuse_enabled = bool(LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY)
if _langfuse_enabled:
    try:
        from langfuse import Langfuse
        _langfuse_client = Langfuse(
            public_key=LANGFUSE_PUBLIC_KEY,
            secret_key=LANGFUSE_SECRET_KEY,
            host=LANGFUSE_HOST,
        )
    except Exception as e:
        print(f"[Observability] Warning: Failed to init LangFuse client: {e}")
        _langfuse_enabled = False
        _langfuse_client = None
else:
    _langfuse_client = None


class RagTracer:
    """
    Manages a single RAG trace across retrieval and generation steps.
    """

    def __init__(self, conversation_id: str = "default", user_query: str = None, query: str = None, **kwargs):
        self.enabled = _langfuse_enabled
        self.trace_id = None
        self.retrieval_span = None
        self.generation_span = None
        self.start_time = time.time()
        q = user_query or query or ""

        if not self.enabled or not _langfuse_client:
            return

        try:
            user_id = kwargs.get("user_id", "anonymous")
            if hasattr(_langfuse_client, "trace") and callable(getattr(_langfuse_client, "trace")):
                self.trace = _langfuse_client.trace(
                    name="rag_query",
                    session_id=conversation_id,
                    user_id=user_id,
                    input={"query": q, "has_image": kwargs.get("has_image", False)},
                    metadata={
                        "environment": os.getenv("ENVIRONMENT", "production"),
                        "routing_strategy": kwargs.get("routing_strategy", ""),
                        "routing_reason": kwargs.get("routing_reason", ""),
                    }
                )
            elif hasattr(_langfuse_client, "span") and callable(getattr(_langfuse_client, "span")):
                self.trace = _langfuse_client.span(
                    name="rag_query",
                    input={"query": q, "has_image": kwargs.get("has_image", False)}
                )
            else:
                self.enabled = False
            self.trace_id = getattr(self.trace, "id", None) if hasattr(self, "trace") and self.trace else None
        except Exception as e:
            print(f"[Observability] Error starting trace: {e}")
            self.enabled = False

    def start_retrieval(self, *args, **kwargs):
        if not self.enabled or not getattr(self, "trace", None):
            return
        try:
            query = args[0] if args else kwargs.get("query", "")
            kb_id = args[1] if len(args) > 1 else kwargs.get("kb_id", "")
            top_k = args[2] if len(args) > 2 else kwargs.get("top_k", 5)
            if hasattr(self.trace, "span"):
                self.retrieval_span = self.trace.span(
                    name="knowledge_base_retrieval",
                    input={"query": query, "kb_id": kb_id, "top_k": top_k}
                )
        except Exception as e:
            print(f"[Observability] Error starting retrieval span: {e}")

    def end_retrieval(self, chunks: list = None, *args, **kwargs):
        if not self.enabled or not self.retrieval_span:
            return
        try:
            c_list = chunks if chunks is not None else (args[0] if args else [])
            if hasattr(self.retrieval_span, "end"):
                self.retrieval_span.end(
                    output={
                        "num_chunks_retrieved": len(c_list),
                        "top_chunk_score": c_list[0]["score"] if c_list and isinstance(c_list[0], dict) and "score" in c_list[0] else 0.0,
                        "sources": [c.get("source") for c in c_list if isinstance(c, dict)]
                    }
                )
        except Exception as e:
            print(f"[Observability] Error ending retrieval span: {e}")

    def start_generation(self, model_id: str = None, prompt: str = None, *args, **kwargs):
        if not self.enabled or not getattr(self, "trace", None):
            return
        try:
            m_id = model_id or (args[0] if args else "")
            p_text = prompt or (args[1] if len(args) > 1 else "")
            if hasattr(self.trace, "generation"):
                self.generation_span = self.trace.generation(
                    name="llm_generation",
                    model=m_id,
                    input=p_text,
                )
        except Exception as e:
            print(f"[Observability] Error starting generation span: {e}")

    def end_generation(self, answer: str = None, input_tokens: int = 0, output_tokens: int = 0, cost_usd: float = 0.0, *args, **kwargs):
        if not self.enabled or not self.generation_span:
            return
        try:
            ans = answer if answer is not None else (args[0] if args else "")
            in_tok = input_tokens or (args[1] if len(args) > 1 else 0)
            out_tok = output_tokens or (args[2] if len(args) > 2 else 0)
            cost = cost_usd or (args[3] if len(args) > 3 else 0.0)
            if hasattr(self.generation_span, "end"):
                self.generation_span.end(
                    output=ans,
                    usage={
                        "input": in_tok,
                        "output": out_tok,
                        "total": in_tok + out_tok,
                        "unit": "TOKENS",
                    },
                    metadata={"cost_usd": cost}
                )
        except Exception as e:
            print(f"[Observability] Error ending generation span: {e}")

    def record_error(self, error_msg: str, step: str = "pipeline"):
        if not self.enabled or not getattr(self, "trace", None):
            return
        try:
            if hasattr(self.trace, "update"):
                self.trace.update(output={"error": error_msg, "step": step}, level="ERROR")
        except Exception as e:
            print(f"[Observability] Error recording trace error: {e}")

    def end_trace(self, success: bool = True, error_msg: str = None, *args, **kwargs):
        if not self.enabled or not getattr(self, "trace", None):
            return
        try:
            if hasattr(self.trace, "update"):
                self.trace.update(
                    output={"success": success, "error": error_msg},
                    metadata={"total_duration_sec": time.time() - self.start_time}
                )
        except Exception as e:
            print(f"[Observability] Error ending trace: {e}")

    def flush(self):
        if self.enabled and _langfuse_client and hasattr(_langfuse_client, "flush"):
            try:
                _langfuse_client.flush()
            except Exception as e:
                print(f"[Observability] Error flushing LangFuse: {e}")
