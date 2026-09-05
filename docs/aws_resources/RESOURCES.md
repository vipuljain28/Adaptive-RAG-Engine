# AWS Resources — Knowledge Assistant Capstone Project

**Account ID:** `674959318309`  
**Primary Region:** `us-east-1`  
**Deployed by:** Vipul Jain  
**Last Updated:** 2026-08-21

---

## Resource Inventory

### 1. EC2 Instance — Application Server

| Field | Value |
|-------|-------|
| **Instance ID** | `i-02d6f4514eb18b127` |
| **Name** | `knowledge-assistant-app-dev` |
| **Type** | `t3.small` |
| **State** | `running` |
| **Public IP** | `100.24.105.149` |
| **Security Group** | `sg-012e4a535cabeca66` (`knowledge-assistant-sg-dev`) |
| **Key Pair** | `ec2-key-ml` |

**Purpose:** Hosts the Streamlit-based multi-modal Knowledge Assistant web application.  
**App Port:** `8501`  
**App URL:** `http://100.24.105.149:8501`  
**Service:** Managed as a `systemd` service (`knowledge-assistant.service`)

**Pages Live:**
- `http://100.24.105.149:8501` — Home
- `http://100.24.105.149:8501/chat` — AI Chat Interface
- `http://100.24.105.149:8501/upload` — Document Upload
- `http://100.24.105.149:8501/history` — Query History
- `http://100.24.105.149:8501/models` — Model Registry
- `http://100.24.105.149:8501/settings` — Settings

---

### 2. S3 Bucket — Document Storage & Deployment

| Field | Value |
|-------|-------|
| **Bucket Name** | `knowledge-assistant-docs-674959318309` |
| **Region** | `us-east-1` |
| **ARN** | `arn:aws:s3:::knowledge-assistant-docs-674959318309` |

**Purpose:** Stores source documents for RAG indexing and the deployment code bundle.

**Key S3 Paths:**

| Path | Description |
|------|-------------|
| `documents/` | Source documents ingested into Bedrock KB |
| `deploy/app_deploy.zip` | Latest app deployment bundle |

**Sample Documents ingested:**
- `hr_policy.txt`
- `product_manual.txt`
- `technical_guide.txt`

---

### 3. Amazon Bedrock — Knowledge Base

| Field | Value |
|-------|-------|
| **Knowledge Base ID** | `IY7GSOCYCH` |
| **Name** | `vipul-knowledge-base-quick-start-5cyu0` |
| **ARN** | `arn:aws:bedrock:us-east-1:674959318309:knowledge-base/IY7GSOCYCH` |
| **Status** | `ACTIVE` |
| **Embedding Model** | `amazon.titan-embed-text-v2:0` |
| **Data Source ID** | `3BTPQGVBWX` |

**Purpose:** RAG knowledge base that retrieves relevant document chunks and passes them to the LLM for grounded responses.

---

### 4. Amazon Bedrock — Foundation Models (API-only, no dedicated servers)

| Alias | Model ID | Use Case | Cost per 1K tokens (In/Out) |
|-------|----------|----------|----------------------------|
| Primary | `amazon.nova-pro-v1:0` | Main chat + vision | $0.0008 / $0.0032 |
| Secondary | `amazon.nova-lite-v1:0` | Fast / low-cost queries | $0.00006 / $0.00024 |
| Embedding | `amazon.titan-embed-text-v2:0` | Document embedding | Serverless |

---

### 5. Amazon Bedrock — Guardrail

| Field | Value |
|-------|-------|
| **Guardrail ID** | `epexi952sjix` |
| **Name** | `knowledge-assistant-guardrail` |
| **Status** | `READY` |
| **Version** | `1` |

**Policies configured:**

| Policy Type | Rules |
|-------------|-------|
| PII Detection | EMAIL, PHONE, NAME, CREDENTIALS, US_SSN → ANONYMIZED |
| Content Filters | PROMPT_ATTACK, HATE, VIOLENCE, SEXUAL, HARASSMENT → HIGH blocked |
| Topic Filters | competitor_info, financial_advice → BLOCKED |
| Grounding | Contextual grounding & relevance filtering enabled |

---

### 6. Amazon OpenSearch Serverless — Vector Store

| Field | Value |
|-------|-------|
| **Collection ID** | `zrhy9hl9a0vtsgj4f0h` |
| **Name** | `knowledge-assistant` |
| **ARN** | `arn:aws:aoss:us-east-1:674959318309:collection/zrhy9hl9a0vtsgj4f0h` |
| **Status** | `ACTIVE` |
| **Type** | VECTORSEARCH |

**Purpose:** Stores document embeddings for semantic similarity search (vector DB backend for Bedrock KB).

Additional collections (pre-existing/test):
- `0v2f2sst526rf1o6hspl` — `knowledge-assistant-dev` (ACTIVE)
- `try37poxropo2v51c1s5` — `bedrock-knowledge-base-hxnhid` (ACTIVE)

---

### 7. VPC — Custom Network

| Field | Value |
|-------|-------|
| **VPC ID** | `vpc-031c0bbf0770403f6` |
| **CIDR** | `10.0.0.0/16` |
| **Name** | `knowledge-assistant-eks-vpc` |

**Purpose:** Isolated VPC created during EKS/Terraform setup for the bonus TinyLlama deployment.

---

### 8. IAM Roles

| Role Name | Purpose |
|-----------|---------|
| `AmazonBedrockExecutionRoleForKnowledgeBase_5cyu0` | Allows Bedrock to access S3/OpenSearch for KB |
| `AmazonBedrockExecutionRoleForKnowledgeBase_sva4q` | Bedrock KB execution role (secondary) |
| `AmazonBedrockExecutionRoleForKnowledgeBase_w8675` | Bedrock KB execution role (tertiary) |

---

### 9. Observability — LangFuse (SaaS)

| Field | Value |
|-------|-------|
| **Platform** | LangFuse (us.cloud.langfuse.com) |
| **Public Key** | `pk-lf-d525d366-11dc-4507-9e3b-cfcc938cdc80` |

**Purpose:** Traces every LLM call — input tokens, output tokens, latency, cost per query.

---

## Application Architecture

```
User (Browser)
    |
    v
EC2 t3.small (100.24.105.149:8501)
    | Streamlit App (systemd)
    |
    |----> Bedrock Guardrail (epexi952sjix)
    |         PII Redaction + Content Filtering
    |
    |----> Bedrock Knowledge Base (IY7GSOCYCH)
    |         Retrieve relevant document chunks
    |         |
    |         +----> OpenSearch Serverless (zrhy9hl9a0vtsgj4f0h)
    |                   Vector similarity search
    |
    |----> Bedrock Model API
    |         amazon.nova-pro-v1:0 (primary)
    |         amazon.nova-lite-v1:0 (secondary)
    |
    +----> S3 (knowledge-assistant-docs-674959318309)
              Document storage + Deploy bundle

Tracing: LangFuse (us.cloud.langfuse.com)
```

---

## Monthly Cost Estimate

| Service | Estimated Cost | Notes |
|---------|---------------|-------|
| EC2 t3.small | ~$15.33/month | On-demand, us-east-1 |
| OpenSearch Serverless | ~$20–50/month | 3 active collections (OCU billing) |
| Bedrock Knowledge Base | ~$0.001–0.05/query | Per-token + retrieval fees |
| S3 Storage | ~$0.02/GB/month | < 1 GB total |
| Bedrock Guardrail | ~$0.0015/query | Per-request processing |

---

## Verified & Working Features

| Feature | Status |
|---------|--------|
| Home Page (`/`) | HTTP 200 OK |
| Chat Page (`/chat`) | HTTP 200 OK — Amazon Nova Pro responding |
| Upload Page (`/upload`) | HTTP 200 OK |
| History Page (`/history`) | HTTP 200 OK |
| Models Page (`/models`) | HTTP 200 OK |
| Settings Page (`/settings`) | HTTP 200 OK |
| RAG Pipeline | LIVE — 5 chunks retrieved, grounded responses |
| Guardrails | ACTIVE (epexi952sjix v1) |
| Unit Tests (8/8) | PASSING |
| Observability | LangFuse tracing active |
| boto3 Deprecation Warnings | Suppressed via warnings.filterwarnings |
