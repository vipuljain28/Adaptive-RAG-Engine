# LLM Cost Comparison & Financial Recommendation

> **Note:** This project uses **Amazon Nova Pro** and **Amazon Nova Lite** via Amazon Bedrock.
> These are AWS-native foundation models, significantly more cost-efficient than Claude equivalents
> while delivering strong performance for enterprise Q&A use cases.

---

## 1. Models Being Compared

| Property | Amazon Nova Pro | Amazon Nova Lite |
|---|---|---|
| **Bedrock Model ID** | `amazon.nova-pro-v1:0` | `amazon.nova-lite-v1:0` |
| **Input Token Price** | $0.0008 / 1,000 tokens | $0.00006 / 1,000 tokens |
| **Output Token Price** | $0.0032 / 1,000 tokens | $0.00024 / 1,000 tokens |
| **Relative Quality** | High — superior reasoning, complex policy analysis, multimodal | Moderate — fast, ideal for simple factual Q&A |
| **Response Speed** | ~3–5 seconds | ~0.5–1.5 seconds |
| **Context Window** | 300K tokens | 300K tokens |
| **Vision / Multimodal** | Yes | No |
| **Best For** | Policy interpretation, multi-part questions, image Q&A | Quick lookups, FAQs, high-volume simple queries |

### Price Comparison vs Claude Models
| Model | Input / 1K | Output / 1K | vs Nova Pro |
|---|---|---|---|
| Amazon Nova Pro | $0.0008 | $0.0032 | baseline |
| Amazon Nova Lite | $0.00006 | $0.00024 | ~13× cheaper than Nova Pro |
| Claude 3 Sonnet | $0.003 | $0.015 | ~3.75× more expensive than Nova Pro |
| Claude 3 Haiku | $0.00025 | $0.00125 | ~4× more expensive than Nova Lite |

Amazon Nova models are the correct choice for this project — they are AWS-native,
cost-optimised, and available in the same us-east-1 region as all other resources.

---

## 2. Assumed Usage Pattern

To calculate realistic enterprise cost projections, we model a baseline scenario for a
mid-sized team of **50 active employees**:

| Parameter | Value |
|---|---|
| Active Users | 50 employees |
| Daily Queries per User | 20 queries / working day |
| Working Days per Month | 22 days |
| **Total Monthly Queries** | **50 × 20 × 22 = 22,000 queries/month** |
| Average Input Tokens per Query | 800 tokens (question + 5 retrieved KB chunks × ~150 tokens) |
| Average Output Tokens per Query | 300 tokens (structured answer with citations) |
| Auto-Routing Mix | 60% Nova Lite (simple lookups), 40% Nova Pro (complex analysis) |

---

## 3. Financial Cost Calculations

### Option A: Amazon Nova Pro Only (100% of volume)

```
Input tokens:  22,000 × 800 = 17,600,000 tokens = 17,600 K tokens
               17,600 × $0.0008   = $14.08

Output tokens: 22,000 × 300 = 6,600,000 tokens  = 6,600 K tokens
               6,600  × $0.0032   = $21.12

Total Nova Pro monthly cost:  $14.08 + $21.12  =  $35.20 / month
```

---

### Option B: Amazon Nova Lite Only (100% of volume)

```
Input tokens:  17,600 K tokens × $0.00006  = $1.056
Output tokens: 6,600  K tokens × $0.00024  = $1.584

Total Nova Lite monthly cost:  $1.056 + $1.584  =  $2.64 / month
```

---

### Option C: AI Gateway Auto-Routing Mix (60% Lite / 40% Pro)

```
Nova Lite share — 13,200 queries (60%)
  Input:  13,200 × 800 = 10,560 K tokens × $0.00006  = $0.634
  Output: 13,200 × 300 = 3,960  K tokens × $0.00024  = $0.950
  Nova Lite subtotal:   $1.58

Nova Pro share — 8,800 queries (40%)
  Input:  8,800 × 800 = 7,040 K tokens × $0.0008   = $5.632
  Output: 8,800 × 300 = 2,640 K tokens × $0.0032   = $8.448
  Nova Pro subtotal:    $14.08

Total Auto-Routing monthly cost:  $1.58 + $14.08  =  $15.66 / month
```

---

## 4. Summary Cost Matrix

| Strategy | Monthly LLM Cost | vs Nova Pro Only | Quality Profile |
|---|---|---|---|
| **Nova Pro Only** | **$35.20** | Baseline | Maximum reasoning & accuracy |
| **Auto-Routing (AI Gateway)** | **$15.66** | **−55% savings** | Balanced: Pro for complex, Lite for fast |
| **Nova Lite Only** | **$2.64** | **−92% savings** | High speed, acceptable for simple Q&A |

---

## 5. Detailed Cost Breakdown by Query Type

| Query Type | Example | Volume | Model Used | Cost per Query | Monthly Cost |
|---|---|---|---|---|---|
| Simple lookup | "What is the leave policy?" | 13,200 (60%) | Nova Lite | $0.000121 | $1.58 |
| Complex analysis | "Compare remote work and office policies, explain exceptions" | 8,800 (40%) | Nova Pro | $0.001600 | $14.08 |
| Vision query | "What does this diagram show?" + image | ~100 (est.) | Nova Pro | $0.001600 | $0.16 |
| **Total (Auto-Routing)** | | **22,000** | **Mixed** | **avg $0.000712** | **$15.74** |

---

## 6. Strategic Recommendation

### Recommended: AI Gateway Auto-Routing (Phase 3)

The Auto-Routing strategy delivers **55% cost savings** vs Nova Pro only while maintaining
top-tier reasoning quality on complex queries:

- **60% of queries** (simple lookups: "What is the leave allowance?") → **Nova Lite**
  at $0.000121/query — 13× cheaper than Nova Pro
- **40% of queries** (complex analysis: policy interpretation, step-by-step troubleshooting,
  multi-part comparisons) → **Nova Pro** for reliable, nuanced answers

### When to Use Nova Lite Only
For high-volume, low-complexity helpdesk deployments serving only FAQ-type queries,
Nova Lite reduces the monthly LLM cost from $35.20 to **$2.64** — a **92% reduction**.
This is suitable only when query complexity is reliably low.

### Cost Monitoring
Use the Analytics Dashboard (`app/pages/02_analytics.py`) and LangFuse telemetry to track
real token consumption. If costs exceed budget, lower the complexity threshold in
`gateway/router.py` (`_COMPLEX_SCORE_THRESHOLD`) to route more queries to Nova Lite.

---

## 7. Full Infrastructure Cost (Monthly)

| Component | AWS Service | Monthly Cost |
|---|---|---|
| LLM inference (Auto-Routing) | Amazon Bedrock — Nova Pro/Lite | ~$15.66 |
| Vector store | OpenSearch Serverless (~2 OCUs) | ~$350.00 |
| Application host | EC2 t3.small (on-demand) | ~$15.00 |
| Document storage | S3 (<1 GB) | ~$0.02 |
| Embedding (Titan v2) | Per-document (one-time ingestion) | <$0.01 |
| **Total Estimated** | **50 active users** | **~$381 / month** |

The dominant cost is **OpenSearch Serverless** at ~$350/month (minimum 2 OCUs regardless of
usage). LLM token costs are a small fraction of total infrastructure cost at this scale.

---

## 8. Break-Even: Self-Hosted vs Bedrock

When does deploying a self-hosted LLM on EKS become cheaper than Bedrock?

```
EKS fixed cost: g4dn.xlarge = $0.526/hr × 24 × 30 = ~$379/month

Break-even vs Nova Pro:
  Cost per query (Nova Pro)  = $0.001600
  $379 / $0.001600           = 236,875 queries/month before EKS is cheaper

Break-even vs Nova Lite:
  Cost per query (Nova Lite) = $0.000121
  $379 / $0.000121           = 3,132,231 queries/month before EKS is cheaper
```

**Conclusion:** For 22,000 queries/month across 50 users, Bedrock Nova is far more
cost-effective than self-hosting. EKS only makes financial sense above ~237K queries/month
(vs Nova Pro) OR when strict data residency requirements prevent using managed services.
