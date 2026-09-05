# Self-Hosted LLM (EKS) vs. AWS Bedrock Managed LLM

## 1. Overview & Architectural Context

This document evaluates the architectural, operational, and financial trade-offs between two distinct LLM deployment paradigms integrated into the Knowledge Assistant:

1. **Fully Managed LLMs (Amazon Bedrock)**:  
   AWS manages infrastructure, high availability, model weights, and scaling. Invocations are billed on a strict pay-per-token basis for Claude 3 Sonnet and Claude 3 Haiku.

2. **Self-Hosted Open-Source LLMs (Amazon EKS + TinyLlama 1.1B)**:  
   The application runs an open-source model (`TinyLlama/TinyLlama-1.1B-Chat-v1.0`) on a self-managed Amazon EKS cluster with GPU-accelerated worker nodes (`g4dn.xlarge`). Compute infrastructure is billed hourly regardless of query traffic.

---

## 2. Comprehensive Comparison Matrix

| Dimension | Amazon Bedrock (Managed) | Self-Hosted EKS (TinyLlama) |
|---|---|---|
| **Setup & Maintenance Overhead** | Low — serverless API calls | High — EKS cluster, Helm charts, GPU node scaling |
| **Model Reasoning Quality** | State-of-the-Art (Claude 3 Sonnet / Haiku) | Basic Q&A (1.1B parameter compact model) |
| **Response Latency** | ~1–4 seconds | ~3–15 seconds (subject to GPU load / cold starts) |
| **Cost Structure** | Pay-per-token ($0.00025–$0.003/1K input) | Fixed hourly compute ($0.526/hr for `g4dn.xlarge`) |
| **Monthly Cost (50 Users)** | **$12.65 – $151.80 / month** | **~$380.00 / month** (24/7 single GPU node) |
| **Data Privacy & Boundaries** | Sent to AWS Bedrock tenant API | Stays 100% inside private VPC boundaries |
| **Context Window Size** | Up to 200,000 tokens | 2,048 tokens |
| **Multimodal Capabilities** | Yes (Claude 3 Sonnet Vision) | No (Text-only) |
| **Safety Guardrails** | Integrated Bedrock Guardrails | Must be manually developed in application logic |
| **High Availability & SLA** | 99.9% AWS managed SLA | Requires multi-AZ Kubernetes replica management |

---

## 3. Financial Break-Even Analysis

### Compute Fixed Cost Baseline
Running a minimal 1-node `g4dn.xlarge` instance (1x NVIDIA T4 GPU, 16GB VRAM) for self-hosting costs:
$$\$0.526 \times 24 \text{ hours} \times 30 \text{ days} = \mathbf{\$378.72 / \text{month}}$$

### Volume Threshold Comparisons

1. **Vs. Claude 3 Haiku ($0.00057 / query avg)**:
   $$\frac{\$378.72}{\$0.00057} \approx \mathbf{664,400\text{ queries / month}}$$
   *Self-hosting is only cheaper than Haiku if volume exceeds ~665,000 queries per month.*

2. **Vs. Claude 3 Sonnet ($0.0099 / query avg)**:
   $$\frac{\$378.72}{\$0.0099} \approx \mathbf{38,250\text{ queries / month}}$$
   *Self-hosting becomes cheaper than Sonnet at ~38,000 queries per month, but yields significantly lower response quality.*

---

## 4. Decision Guidelines

### Choose Amazon Bedrock Managed LLMs When:
- Team size and monthly traffic is low-to-medium (< 500,000 queries/month).
- Complex policy reasoning, long context windows (up to 200K), or image analysis is required.
- Minimal DevOps infrastructure overhead is preferred.
- Built-in compliance guardrails and PII redaction are mandatory.

### Choose Self-Hosted EKS When:
- Regulatory compliance prohibits data from leaving private VPC boundaries.
- Fine-tuning open-source weights on domain-specific proprietary corpora is necessary.
- Monthly query volume is massive (millions of queries/month), making token costs prohibitive.
- Dedicated Kubernetes platform engineering capacity is available.

---

## 5. Capstone Recommendation

For this Knowledge Assistant deployment (50 active enterprise users):

**Amazon Bedrock with AI Gateway Auto-Routing (Phase 3) is the optimal choice**, delivering enterprise-grade quality at **$68.31 / month** (55% savings over Sonnet baseline). Self-hosting on EKS requires ~$380/month in fixed GPU infrastructure while delivering lower reasoning quality.

The EKS TinyLlama deployment module is retained in the codebase as a demonstration of hybrid architecture readiness, allowing users to toggle to `Self-Hosted (TinyLlama) — EKS` in the Streamlit sidebar for testing.
