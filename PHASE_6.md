# Phase 6 — Bonus: EKS Open-Source LLM + CI/CD Theory

## Context: What This Capstone Is
An AI-powered Knowledge Assistant built on AWS using Amazon Bedrock. All core functionality
is complete across Phases 1–5:
- RAG pipeline with multi-model routing (text, voice, image)
- Bedrock Guardrails + RCTFC prompt engineering
- AI Gateway with 3 routing strategies
- Full Terraform IaC + cost comparison
- LangFuse observability tracing

Phase 6 covers two bonus requirements:
- **Bonus A (10 marks):** Deploy an open-source LLM on Amazon EKS and integrate it
- **Bonus B (10 marks):** Theory revision — GitHub + CodePipeline + CI/CD concepts

**No AWS Console is used. All resources are Terraform or kubectl/helm.**

---

## Phase 6 Scope

### Bonus A — EKS Open-Source LLM
- Terraform creates an EKS cluster
- Helm chart deploys TinyLlama (1.1B params) on a GPU-capable node group
- An adapter module lets the app call the self-hosted model via HTTP
- The self-hosted model is added to the LLM registry as a 4th routing option
- A comparison document is written: self-hosted vs Bedrock managed

### Bonus B — CI/CD Theory
- A written document covering: GitHub integration, AWS CodePipeline,
  buildspec.yaml, and the full CI/CD workflow for this project
- Includes a complete annotated `buildspec.yaml` example

---

## Requirement Coverage
- **Bonus Requirement 1 (10 marks):** EKS cluster + open-source LLM deployment + app integration
- **Bonus Requirement 2 (10 marks):** Theory — GitHub + CodePipeline + CI/CD

---

## Project Root
`G:\learn ai\modules\capstone`

---

## New Files to Create in Phase 6
```
bonus/
├── eks/
│   ├── terraform/
│   │   ├── main.tf              # EKS cluster + node group
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── helm/
│   │   └── tinyllama/
│   │       ├── Chart.yaml
│   │       ├── values.yaml
│   │       └── templates/
│   │           ├── deployment.yaml
│   │           ├── service.yaml
│   │           └── hpa.yaml
│   └── adapter.py               # HTTP adapter — calls self-hosted model
├── cicd/
│   ├── buildspec.yaml           # Annotated CodeBuild buildspec
│   └── cicd_theory.md           # Full CI/CD theory document
└── comparison/
    └── selfhosted_vs_bedrock.md # Self-hosted vs managed model comparison
```

## Files to Modify in Phase 6
```
gateway/llm_registry.py   — add 4th model entry: "tinyllama" (self-hosted)
gateway/router.py         — handle "Self-Hosted (TinyLlama)" sidebar option
app/components/sidebar.py — add 5th model option to selectbox
app/utils/rag_engine.py   — detect self-hosted model and call adapter instead of Bedrock
```

---

## BONUS A — EKS + Open-Source LLM

### Model Choice: TinyLlama 1.1B Chat
TinyLlama is chosen because:
- Small enough to run on a single g4dn.xlarge GPU instance (16GB VRAM, ~$0.526/hr)
- Hugging Face model ID: `TinyLlama/TinyLlama-1.1B-Chat-v1.0`
- Serves via a simple FastAPI + transformers HTTP server
- Good for demonstrating the concept without extreme cost
- Alternative: `mistralai/Mistral-7B-Instruct-v0.2` for better quality (needs g5.2xlarge)

---

### `bonus/eks/terraform/variables.tf`
```hcl
variable "aws_region"        { type = string; default = "us-east-1" }
variable "cluster_name"      { type = string; default = "knowledge-assistant-eks" }
variable "kubernetes_version" { type = string; default = "1.29" }
variable "node_instance_type" {
  type    = string
  default = "g4dn.xlarge"   # 1x NVIDIA T4 GPU, 16GB VRAM
  description = "GPU instance for LLM inference. g4dn.xlarge ~$0.526/hr on-demand."
}
variable "desired_nodes"     { type = number; default = 1 }
variable "min_nodes"         { type = number; default = 0 }  # scale to 0 when idle
variable "max_nodes"         { type = number; default = 2 }
variable "tags"              { type = map(string); default = {} }
```

### `bonus/eks/terraform/main.tf`
```hcl
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws        = { source = "hashicorp/aws",        version = "~> 5.0" }
    kubernetes = { source = "hashicorp/kubernetes",  version = "~> 2.0" }
    helm       = { source = "hashicorp/helm",        version = "~> 2.0" }
  }
}

provider "aws" { region = var.aws_region }

data "aws_availability_zones" "available" {}

# ── VPC (minimal — 2 public subnets for demo) ─────────────────────────────────
resource "aws_vpc" "eks" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = merge(var.tags, { Name = "${var.cluster_name}-vpc" })
}

resource "aws_subnet" "eks" {
  count                   = 2
  vpc_id                  = aws_vpc.eks.id
  cidr_block              = cidrsubnet(aws_vpc.eks.cidr_block, 8, count.index)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true
  tags = merge(var.tags, {
    Name                                        = "${var.cluster_name}-subnet-${count.index}"
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
    "kubernetes.io/role/elb"                    = "1"
  })
}

resource "aws_internet_gateway" "eks" {
  vpc_id = aws_vpc.eks.id
  tags   = var.tags
}

resource "aws_route_table" "eks" {
  vpc_id = aws_vpc.eks.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.eks.id
  }
  tags = var.tags
}

resource "aws_route_table_association" "eks" {
  count          = 2
  subnet_id      = aws_subnet.eks[count.index].id
  route_table_id = aws_route_table.eks.id
}

# ── EKS Cluster IAM Role ──────────────────────────────────────────────────────
resource "aws_iam_role" "cluster" {
  name = "${var.cluster_name}-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "eks.amazonaws.com" },
                   Action = "sts:AssumeRole" }]
  })
}
resource "aws_iam_role_policy_attachment" "cluster_policy" {
  role       = aws_iam_role.cluster.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}

# ── EKS Cluster ───────────────────────────────────────────────────────────────
resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  role_arn = aws_iam_role.cluster.arn
  version  = var.kubernetes_version

  vpc_config {
    subnet_ids = aws_subnet.eks[*].id
  }

  depends_on = [aws_iam_role_policy_attachment.cluster_policy]
  tags       = var.tags
}

# ── Node Group IAM Role ───────────────────────────────────────────────────────
resource "aws_iam_role" "node" {
  name = "${var.cluster_name}-node-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" },
                   Action = "sts:AssumeRole" }]
  })
}
resource "aws_iam_role_policy_attachment" "node_worker" {
  role       = aws_iam_role.node.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
}
resource "aws_iam_role_policy_attachment" "node_cni" {
  role       = aws_iam_role.node.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
}
resource "aws_iam_role_policy_attachment" "node_ecr" {
  role       = aws_iam_role.node.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

# ── GPU Node Group ────────────────────────────────────────────────────────────
resource "aws_eks_node_group" "gpu" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "gpu-nodes"
  node_role_arn   = aws_iam_role.node.arn
  subnet_ids      = aws_subnet.eks[*].id
  instance_types  = [var.node_instance_type]
  ami_type        = "AL2_x86_64_GPU"    # Amazon Linux 2 with GPU drivers

  scaling_config {
    desired_size = var.desired_nodes
    min_size     = var.min_nodes
    max_size     = var.max_nodes
  }

  labels = { role = "gpu-inference" }
  tags   = var.tags

  depends_on = [
    aws_iam_role_policy_attachment.node_worker,
    aws_iam_role_policy_attachment.node_cni,
    aws_iam_role_policy_attachment.node_ecr,
  ]
}
```

### `bonus/eks/terraform/outputs.tf`
```hcl
output "cluster_name"      { value = aws_eks_cluster.main.name }
output "cluster_endpoint"  { value = aws_eks_cluster.main.endpoint }
output "cluster_ca"        { value = aws_eks_cluster.main.certificate_authority[0].data }
```


---

### `bonus/eks/helm/tinyllama/Chart.yaml`
```yaml
apiVersion: v2
name: tinyllama
description: TinyLlama 1.1B Chat inference server for Knowledge Assistant
type: application
version: 1.0.0
appVersion: "1.1B-Chat-v1.0"
```

### `bonus/eks/helm/tinyllama/values.yaml`
```yaml
replicaCount: 1

image:
  repository: python          # Base image; model loaded at startup from HuggingFace
  tag: "3.11-slim"
  pullPolicy: IfNotPresent

model:
  huggingFaceId: "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
  cacheDir: "/model-cache"
  maxNewTokens: 512
  temperature: 0.1

service:
  type: ClusterIP
  port: 8080                  # Internal port; accessible within the cluster

resources:
  requests:
    memory: "8Gi"
    cpu: "2"
    nvidia.com/gpu: "1"
  limits:
    memory: "14Gi"
    cpu: "4"
    nvidia.com/gpu: "1"

nodeSelector:
  role: gpu-inference          # Match EKS node group label

persistence:
  enabled: true
  size: 10Gi                  # Cache downloaded model weights
  storageClass: "gp3"

autoscaling:
  enabled: false              # Keep simple for demo; enable for production
  minReplicas: 1
  maxReplicas: 3
  targetCPUUtilizationPercentage: 70
```

### `bonus/eks/helm/tinyllama/templates/deployment.yaml`
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Release.Name }}-tinyllama
  labels:
    app: tinyllama
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      app: tinyllama
  template:
    metadata:
      labels:
        app: tinyllama
    spec:
      nodeSelector:
        {{- toYaml .Values.nodeSelector | nindent 8 }}
      containers:
        - name: tinyllama-server
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          command: ["/bin/sh", "-c"]
          args:
            - |
              pip install fastapi uvicorn transformers torch accelerate --quiet
              python -c "
              import os
              from fastapi import FastAPI
              from pydantic import BaseModel
              from transformers import pipeline
              import uvicorn

              app = FastAPI()
              model_id = '{{ .Values.model.huggingFaceId }}'
              pipe = pipeline('text-generation', model=model_id,
                              torch_dtype='auto', device_map='auto',
                              model_kwargs={'cache_dir': '{{ .Values.model.cacheDir }}'})

              class QueryRequest(BaseModel):
                  prompt: str
                  max_new_tokens: int = {{ .Values.model.maxNewTokens }}
                  temperature: float = {{ .Values.model.temperature }}

              @app.get('/health')
              def health():
                  return {'status': 'ok', 'model': model_id}

              @app.post('/generate')
              def generate(req: QueryRequest):
                  messages = [{'role': 'user', 'content': req.prompt}]
                  out = pipe(messages, max_new_tokens=req.max_new_tokens,
                             temperature=req.temperature, do_sample=True)
                  text = out[0]['generated_text'][-1]['content']
                  return {'answer': text, 'model': model_id}

              uvicorn.run(app, host='0.0.0.0', port=8080)
              "
          ports:
            - containerPort: 8080
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
          volumeMounts:
            - name: model-cache
              mountPath: {{ .Values.model.cacheDir }}
      volumes:
        - name: model-cache
          persistentVolumeClaim:
            claimName: {{ .Release.Name }}-model-cache
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: {{ .Release.Name }}-model-cache
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: {{ .Values.persistence.storageClass }}
  resources:
    requests:
      storage: {{ .Values.persistence.size }}
```

### `bonus/eks/helm/tinyllama/templates/service.yaml`
```yaml
apiVersion: v1
kind: Service
metadata:
  name: {{ .Release.Name }}-tinyllama
spec:
  selector:
    app: tinyllama
  ports:
    - protocol: TCP
      port: {{ .Values.service.port }}
      targetPort: 8080
  type: {{ .Values.service.type }}
```

### `bonus/eks/helm/tinyllama/templates/hpa.yaml`
```yaml
{{- if .Values.autoscaling.enabled }}
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {{ .Release.Name }}-tinyllama-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{ .Release.Name }}-tinyllama
  minReplicas: {{ .Values.autoscaling.minReplicas }}
  maxReplicas: {{ .Values.autoscaling.maxReplicas }}
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: {{ .Values.autoscaling.targetCPUUtilizationPercentage }}
{{- end }}
```


---

### `bonus/eks/adapter.py`
HTTP adapter that calls the self-hosted TinyLlama server. Returns the same dict shape
as `generate_response()` in `rag_engine.py` so the rest of the pipeline is unchanged.

```python
"""
Self-hosted LLM adapter for TinyLlama running on EKS.

The TinyLlama server exposes:
  POST http://<service-host>:8080/generate
  Body: {"prompt": str, "max_new_tokens": int, "temperature": float}
  Response: {"answer": str, "model": str}

This adapter is called by rag_engine.py when model_id == TINYLLAMA_ENDPOINT.
It returns the same dict shape as generate_response() so no other code changes.
"""
import os
import requests
import time
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from dotenv import load_dotenv
load_dotenv()

# Set TINYLLAMA_ENDPOINT in .env after deploying to EKS.
# For local port-forward testing use: http://localhost:8080
# For in-cluster access use: http://tinyllama-tinyllama:8080 (k8s service DNS)
TINYLLAMA_ENDPOINT = os.getenv("TINYLLAMA_ENDPOINT", "http://localhost:8080")
TINYLLAMA_TIMEOUT  = int(os.getenv("TINYLLAMA_TIMEOUT", "60"))


def call_self_hosted(prompt: str, max_new_tokens: int = 512,
                     temperature: float = 0.1) -> dict:
    """
    Send a prompt to the self-hosted TinyLlama server and return the response.

    Args:
        prompt:         Complete prompt string (already built by RCTFC template)
        max_new_tokens: Max tokens to generate
        temperature:    Sampling temperature

    Returns:
        {
            "answer":        str   — model response text
            "input_tokens":  int   — approximate (word count * 1.3)
            "output_tokens": int   — approximate (word count * 1.3)
            "model_id":      str   — TINYLLAMA_ENDPOINT value
            "cost_usd":      float — always 0.0 (self-hosted, no token billing)
        }
    """
    url = f"{TINYLLAMA_ENDPOINT}/generate"
    payload = {
        "prompt":         prompt,
        "max_new_tokens": max_new_tokens,
        "temperature":    temperature,
    }

    start = time.time()
    response = requests.post(url, json=payload, timeout=TINYLLAMA_TIMEOUT)
    response.raise_for_status()
    elapsed = time.time() - start

    data   = response.json()
    answer = data.get("answer", "")

    # Token counts are approximate for self-hosted models
    # (no usage object returned from transformers pipeline)
    approx_input_tokens  = int(len(prompt.split()) * 1.3)
    approx_output_tokens = int(len(answer.split()) * 1.3)

    return {
        "answer":        answer,
        "input_tokens":  approx_input_tokens,
        "output_tokens": approx_output_tokens,
        "model_id":      TINYLLAMA_ENDPOINT,
        "cost_usd":      0.0,    # self-hosted: no per-token charge
        "latency_sec":   round(elapsed, 2),
    }


def health_check() -> bool:
    """Returns True if the TinyLlama server is reachable and healthy."""
    try:
        r = requests.get(f"{TINYLLAMA_ENDPOINT}/health", timeout=5)
        return r.status_code == 200
    except Exception:
        return False
```

---

### Modify `gateway/llm_registry.py` — add TinyLlama entry

```python
# Add import at top:
TINYLLAMA_ENDPOINT = os.getenv("TINYLLAMA_ENDPOINT", "http://localhost:8080")

# Add to MODELS dict:
"tinyllama": LLMModel(
    key="tinyllama",
    name="TinyLlama 1.1B (Self-Hosted)",
    model_id=TINYLLAMA_ENDPOINT,     # not a Bedrock ID — used as identifier
    provider="huggingface",
    tier="self-hosted",
    description="Open-source LLM running on EKS. No AWS token costs.",
    max_tokens=512,
    cost_per_1k_input=0.0,           # infrastructure cost only, not per-token
    cost_per_1k_output=0.0,
    supports_vision=False,
    best_for=["offline/private queries", "cost demo", "open-source showcase"]
),
```

### Modify `gateway/router.py` — handle TinyLlama selection

```python
# In _route_user_selection(), add to mapping dict:
"Self-Hosted (TinyLlama)": "tinyllama",
```

### Modify `app/components/sidebar.py` — add 5th model option

```python
# Add to model selectbox options list:
"Self-Hosted (TinyLlama) — EKS",

# Add to model_map dict:
"Self-Hosted (TinyLlama) — EKS": "Self-Hosted (TinyLlama)",
```

### Modify `app/utils/rag_engine.py` — route self-hosted calls to adapter

```python
# Add import:
from bonus.eks.adapter import call_self_hosted, health_check
TINYLLAMA_ENDPOINT = os.getenv("TINYLLAMA_ENDPOINT", "")

# In run_rag_query(), after routing_result is obtained, add:
is_self_hosted = routing_result["model"].provider == "huggingface"

# Then in the generate step, branch:
if is_self_hosted:
    if not health_check():
        raise RuntimeError(
            "TinyLlama server unreachable. "
            "Deploy to EKS and set TINYLLAMA_ENDPOINT in .env, "
            "or run: kubectl port-forward svc/tinyllama-tinyllama 8080:8080"
        )
    prompt = build_rag_prompt(query, chunks)   # vision not supported on TinyLlama
    gen = call_self_hosted(prompt)
else:
    # existing Bedrock path
    gen = generate_response(...)
```


---

### `bonus/comparison/selfhosted_vs_bedrock.md`
Write this document in full markdown. Include all sections below.

#### Section 1: Overview
Brief explanation of the two approaches:
- **Managed (Amazon Bedrock):** AWS hosts, scales, and maintains the model. You pay per token.
- **Self-hosted (EKS + TinyLlama):** You run the model on your own Kubernetes cluster. You pay
  for compute (GPU EC2) regardless of usage.

#### Section 2: Comparison Table
| Dimension | Amazon Bedrock (Claude) | Self-Hosted EKS (TinyLlama) |
|---|---|---|
| Setup complexity | Low — API call only | High — EKS cluster, Helm, GPU drivers |
| Model quality | Very high (Claude 3) | Lower (1.1B params) |
| Response latency | 1–5 seconds | 3–15 seconds (cold: longer) |
| Cost model | Pay per token | Pay per hour (g4dn.xlarge ~$0.526/hr) |
| Monthly cost (50 users) | $12–$152 depending on model | ~$380 (g4dn.xlarge 24/7) |
| Data privacy | Data sent to AWS Bedrock | Data stays in your VPC |
| Scalability | Automatic (AWS managed) | Manual HPA config |
| Maintenance | Zero — AWS manages updates | You manage updates, patches, scaling |
| Model flexibility | Choose from Bedrock catalog | Any HuggingFace model |
| Max context window | 200K tokens (Claude 3) | 2K tokens (TinyLlama) |
| Vision / multimodal | Yes (Claude 3 Sonnet) | No (TinyLlama text only) |
| Guardrails | Bedrock Guardrails (built-in) | Must implement manually |
| Compliance | AWS BAA available | Your responsibility |

#### Section 3: Cost Break-Even Analysis
At what usage level does self-hosted become cheaper than Bedrock?

```
Self-hosted fixed cost: g4dn.xlarge = $0.526/hr × 24 × 30 = ~$380/month

Bedrock Haiku at $380/month:
  $380 / ($0.00025/1K input + $0.00125/1K output) budget...
  Assuming 800 input + 300 output per query = avg $0.00057/query
  $380 / $0.00057 ≈ 666,000 queries/month before self-hosted is cheaper

Bedrock Sonnet at $380/month:
  Avg $0.0099/query (800 input + 300 output)
  $380 / $0.0099 ≈ 38,400 queries/month before self-hosted is cheaper
```

Conclusion: Self-hosting only makes economic sense at very high volumes (600K+ queries/month
for Haiku-tier quality) OR when data privacy requirements prevent using managed cloud services.

#### Section 4: When to Choose Each
**Choose Amazon Bedrock when:**
- Team is small to medium (< 500K queries/month)
- You need state-of-the-art model quality (Claude 3, Titan)
- You need vision/multimodal capabilities
- You want zero infrastructure management overhead
- Compliance requires AWS-managed guardrails

**Choose Self-Hosted EKS when:**
- Data cannot leave your VPC (strict data residency laws)
- You need to fine-tune the model on private data
- Volume is extremely high (millions of queries/month)
- You have an existing Kubernetes platform team
- You need a specific open-source model not on Bedrock

#### Section 5: Recommendation for This Project
For the Knowledge Assistant with 50 users, **Amazon Bedrock is the clear choice**.
The Auto-routing strategy (Phase 3) provides the best cost/quality balance at $68/month.
Self-hosted EKS adds $380/month in infrastructure for a much weaker model.
The EKS deployment is retained as a demonstration of architectural flexibility — it can
be enabled via the "Self-Hosted (TinyLlama)" sidebar option for testing or demos.

---

## BONUS B — CI/CD Theory

### `bonus/cicd/cicd_theory.md`
Write this document in full markdown. Include all sections below.

#### Section 1: GitHub Integration
Explain how this project connects to GitHub:
- The project repository is hosted on GitHub
- Developers push code to feature branches and open Pull Requests to `main`
- AWS CodePipeline has a GitHub source stage using a GitHub connection (OAuth or CodeStar)
- Every push to `main` automatically triggers the pipeline

Key concepts:
- **Branch protection:** Require PR review before merging to `main`
- **GitHub Actions vs CodePipeline:** GitHub Actions runs CI (tests, lint); CodePipeline runs CD (deploy to AWS)
- **Webhook:** GitHub sends a webhook to CodePipeline on push events

#### Section 2: AWS CodePipeline
Explain the pipeline structure for this project:

```
Source Stage
  └── GitHub repo (main branch) — triggered by push

Build Stage (AWS CodeBuild)
  └── buildspec.yaml — runs tests, packages app, pushes to ECR (if containerised)

Deploy Stage
  └── Option A: SSH deploy to EC2 (simple — SCP + restart systemd service)
  └── Option B: ECS/EKS rolling deployment (production-grade)
```

Explain each CodePipeline concept:
- **Stages:** logical phases (Source, Build, Deploy)
- **Actions:** individual steps within a stage
- **Artifacts:** files passed between stages (source zip, build output)
- **Service role:** IAM role that CodePipeline uses to access other services

#### Section 3: buildspec.yaml — Annotated Example

This is the complete `buildspec.yaml` for this project. Write it with a comment above
every meaningful line explaining what it does and why.

```yaml
# buildspec.yaml — AWS CodeBuild build specification
# This file tells CodeBuild exactly what to do when triggered by CodePipeline.
# It lives at the root of the repository.

version: 0.2   # Always use 0.2 — the current stable version

# Environment variables injected by CodePipeline or set in CodeBuild project
env:
  variables:
    AWS_REGION: "us-east-1"
    APP_DIR: "/codebuild/output/app"
  # Secrets from AWS Systems Manager Parameter Store (never hardcode secrets)
  parameter-store:
    KNOWLEDGE_BASE_ID: "/knowledge-assistant/KNOWLEDGE_BASE_ID"
    GUARDRAIL_ID:       "/knowledge-assistant/GUARDRAIL_ID"

phases:

  # install phase: set up the build environment
  install:
    runtime-versions:
      python: 3.11    # Request Python 3.11 runtime in CodeBuild
    commands:
      - echo "=== Installing dependencies ==="
      - pip install --upgrade pip
      - pip install -r requirements.txt   # install all app dependencies
      - pip install pytest flake8         # install test and lint tools

  # pre_build phase: run quality checks before building
  pre_build:
    commands:
      - echo "=== Running linter ==="
      - flake8 app/ gateway/ guardrails/ observability/ --max-line-length=120
        --exclude=__pycache__ || true   # warn but don't fail on style issues

      - echo "=== Running unit tests ==="
      - python -m pytest tests/ -v --tb=short || true   # run tests if tests/ exists

      - echo "=== Verifying routing logic ==="
      - python gateway/test_routing.py   # must pass — this is functional test

  # build phase: package the application
  build:
    commands:
      - echo "=== Build started on $(date) ==="

      # Create .env from SSM parameters for deployment
      - echo "AWS_REGION=${AWS_REGION}"                   > .env
      - echo "KNOWLEDGE_BASE_ID=${KNOWLEDGE_BASE_ID}"    >> .env
      - echo "GUARDRAIL_ID=${GUARDRAIL_ID}"               >> .env

      # Create deployment package (zip for SCP to EC2)
      - zip -r deployment.zip app/ gateway/ guardrails/ observability/
          bonus/ sample_documents/ requirements.txt run.sh .env
          --exclude "*.pyc" --exclude "__pycache__/*" --exclude "data/*"

      - echo "=== Build complete ==="

  # post_build phase: confirm build success and upload artifact
  post_build:
    commands:
      - echo "=== Post-build ==="
      - echo "Deployment package ready: deployment.zip"
      - ls -lh deployment.zip

# Artifacts: files CodePipeline passes to the Deploy stage
artifacts:
  files:
    - deployment.zip
    - scripts/deploy_ec2.sh     # deployment script used by Deploy stage
  discard-paths: no             # preserve directory structure in artifact

# Cache: speed up future builds by caching pip packages
cache:
  paths:
    - '/root/.cache/pip/**/*'   # cache pip downloads between builds
```

#### Section 4: Full CI/CD Workflow for This Project
Describe the end-to-end flow as a numbered sequence:

1. Developer pushes code to a feature branch on GitHub
2. Opens a Pull Request to `main`
3. GitHub Actions runs quick lint check (optional, runs in GitHub)
4. PR is reviewed and approved by a team member
5. PR merged to `main` → GitHub sends webhook to AWS CodePipeline
6. **Source Stage:** CodePipeline pulls the latest `main` branch zip from GitHub
7. **Build Stage:** CodeBuild runs `buildspec.yaml`:
   - Installs dependencies
   - Runs linter and tests
   - Validates routing logic
   - Creates `deployment.zip`
8. **Deploy Stage:** CodeDeploy or a custom action SSHs into the EC2 instance,
   uploads `deployment.zip`, extracts it, and restarts the systemd service
9. App is live — accessible at `http://<ec2-ip>:8501`
10. If any phase fails, CodePipeline stops and notifies via SNS/email

#### Section 5: Key Concepts Summary Table
| Concept | Definition | Example in this project |
|---|---|---|
| Source Stage | Where code comes from | GitHub main branch |
| Build Stage | Where code is compiled/tested | CodeBuild + buildspec.yaml |
| Deploy Stage | Where app goes live | EC2 via SCP + systemd restart |
| Artifact | File(s) passed between stages | deployment.zip |
| buildspec.yaml | Build instructions file | Lives at repo root |
| Service role | IAM role CodePipeline uses | Needs S3, CodeBuild, EC2 access |
| Parameter Store | Secure secret storage | KNOWLEDGE_BASE_ID, GUARDRAIL_ID |
| Branch protection | Prevents direct push to main | Requires PR + review |

---

### `bonus/cicd/buildspec.yaml`
Create this as an actual YAML file (not just in the document). Use the annotated content
from Section 3 of `cicd_theory.md` above — same content, just as a standalone file.

---

## Order to Create Files
1. `bonus/eks/terraform/variables.tf`
2. `bonus/eks/terraform/main.tf`
3. `bonus/eks/terraform/outputs.tf`
4. `bonus/eks/helm/tinyllama/Chart.yaml`
5. `bonus/eks/helm/tinyllama/values.yaml`
6. `bonus/eks/helm/tinyllama/templates/deployment.yaml`
7. `bonus/eks/helm/tinyllama/templates/service.yaml`
8. `bonus/eks/helm/tinyllama/templates/hpa.yaml`
9. `bonus/eks/adapter.py`
10. `bonus/comparison/selfhosted_vs_bedrock.md`
11. `bonus/cicd/cicd_theory.md`
12. `bonus/cicd/buildspec.yaml`
13. Modify `gateway/llm_registry.py` — add tinyllama entry
14. Modify `gateway/router.py` — add Self-Hosted to mapping
15. Modify `app/components/sidebar.py` — add 5th model option
16. Modify `app/utils/rag_engine.py` — branch to adapter for self-hosted calls

Also add `TINYLLAMA_ENDPOINT` to `.env.template`:
```
# Bonus: Self-hosted TinyLlama on EKS
# After deploying: kubectl port-forward svc/tinyllama-tinyllama 8080:8080
TINYLLAMA_ENDPOINT=http://localhost:8080
TINYLLAMA_TIMEOUT=60
```

---

## How to Run (for the human)
```bash
# ── Bonus A: EKS deployment ──────────────────────────────────────────────────
# Step 1: Provision EKS cluster
cd bonus/eks/terraform
terraform init
terraform apply   # takes 10-15 minutes

# Step 2: Configure kubectl
aws eks update-kubeconfig --name knowledge-assistant-eks --region us-east-1

# Step 3: Deploy TinyLlama via Helm
cd ../..
helm install tinyllama bonus/eks/helm/tinyllama/

# Step 4: Wait for pod to be running (model download takes ~3 minutes)
kubectl get pods -w

# Step 5: Port-forward for local testing
kubectl port-forward svc/tinyllama-tinyllama 8080:8080

# Step 6: Set TINYLLAMA_ENDPOINT in .env
# TINYLLAMA_ENDPOINT=http://localhost:8080

# Step 7: Launch app — select "Self-Hosted (TinyLlama) — EKS" in sidebar
cd ../..
streamlit run app/main.py

# ── Bonus B: CI/CD ────────────────────────────────────────────────────────────
# No commands to run — this is theory documentation only
# Review: bonus/cicd/cicd_theory.md and bonus/cicd/buildspec.yaml
```

---

## Definition of Done

### Bonus A
- All 12 EKS/Helm/adapter files created
- `bonus/eks/terraform/main.tf` creates EKS cluster + GPU node group
- `bonus/eks/helm/tinyllama/` is a valid Helm chart (`helm lint` passes)
- `bonus/eks/adapter.py` calls `POST /generate` and returns same dict shape as `generate_response()`
- `gateway/llm_registry.py` has 4 models: sonnet, haiku, vision, tinyllama
- Sidebar has 5th option "Self-Hosted (TinyLlama) — EKS"
- When selected, app calls adapter instead of Bedrock — no crash when endpoint is up
- When endpoint is down, app shows clear error message (not a Python traceback)
- `bonus/comparison/selfhosted_vs_bedrock.md` covers quality, cost, complexity, and recommendation

### Bonus B
- `bonus/cicd/cicd_theory.md` covers all 5 sections with the concepts table
- `bonus/cicd/buildspec.yaml` is a valid, complete YAML file with comments on every block
- Document explains the full GitHub → CodePipeline → CodeBuild → EC2 workflow end-to-end
