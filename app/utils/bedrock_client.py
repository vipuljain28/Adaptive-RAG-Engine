"""
Cached boto3 client factory.

Each function uses functools.lru_cache(maxsize=1) so the client is created
once per process and reused on every subsequent call.  This avoids the overhead
of re-authenticating on every request.
"""

import boto3
from functools import lru_cache
from app.config import AWS_REGION


@lru_cache(maxsize=1)
def get_bedrock_runtime() -> boto3.client:
    """
    bedrock-runtime — used for LLM invocations (invoke_model).
    Supports: Claude text, Claude vision, Titan embeddings.
    """
    return boto3.client("bedrock-runtime", region_name=AWS_REGION)


@lru_cache(maxsize=1)
def get_bedrock_agent_runtime() -> boto3.client:
    """
    bedrock-agent-runtime — used for Knowledge Base retrieval (retrieve).
    This is the RAG retrieval client.
    """
    return boto3.client("bedrock-agent-runtime", region_name=AWS_REGION)


@lru_cache(maxsize=1)
def get_bedrock_client() -> boto3.client:
    """
    bedrock (control plane) — used for creating guardrails, listing models.
    """
    return boto3.client("bedrock", region_name=AWS_REGION)


@lru_cache(maxsize=1)
def get_s3_client() -> boto3.client:
    """S3 — used for document upload and bucket management."""
    return boto3.client("s3", region_name=AWS_REGION)


@lru_cache(maxsize=1)
def get_iam_client() -> boto3.client:
    """IAM — used by setup scripts to create roles for Knowledge Base."""
    return boto3.client("iam", region_name=AWS_REGION)


@lru_cache(maxsize=1)
def get_bedrock_agent_client() -> boto3.client:
    """
    bedrock-agent (control plane) — used to create/manage Knowledge Bases
    and data sources.  Different from bedrock-agent-runtime which does retrieval.
    """
    return boto3.client("bedrock-agent", region_name=AWS_REGION)
