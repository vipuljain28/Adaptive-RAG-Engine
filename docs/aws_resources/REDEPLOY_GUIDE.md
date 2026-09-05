# Re-Deploy Guide — Knowledge Assistant

This guide explains how to re-deploy the entire Knowledge Assistant application from scratch after running `scripts/cleanup_aws.py`.

---

## 🚀 Recommended: Single-Command Automated Deployment

You can deploy the complete infrastructure (S3, OpenSearch, Bedrock Knowledge Base, Guardrails, EKS k8s 1.34, TinyLlama, EC2 host, and Streamlit app) with **a single command**:

```bash
# Direct Python
python deploy_all.py

# Or PowerShell (Windows)
.\deploy_all.ps1

# Or Bash (Linux/Mac)
./deploy_all.sh
```

### What `deploy_all.py` does automatically:
1. **S3 Bucket**: Creates `knowledge-assistant-docs-<account_id>` and updates `.env`.
2. **OpenSearch Serverless**: Creates collection `knowledge-assistant-vector` + vector index `knowledge-assistant-index` and updates `OPENSEARCH_COLLECTION_ARN`.
3. **Bedrock Knowledge Base**: Creates KB `knowledge-assistant-kb` + IAM roles and updates `KNOWLEDGE_BASE_ID` and `DATA_SOURCE_ID`.
4. **Document Ingestion**: Uploads all sample PDFs & web text files and triggers the Bedrock KB sync job (`start_ingestion_job`).
5. **Bedrock Guardrail**: Provisions `knowledge-assistant-guardrail` with PII/content filters and updates `GUARDRAIL_ID` & `GUARDRAIL_VERSION`.
6. **EKS Cluster (k8s 1.34)**: Runs Terraform apply for `knowledge-assistant-eks`, installs TinyLlama Helm chart with `LoadBalancer` service, configures ELB timeout to 300s, and updates `TINYLLAMA_ENDPOINT`.
7. **EC2 App Host**: Packages `app_deploy.zip`, uploads to S3, deploys via SSM to EC2 host, and starts `knowledge-assistant.service`.
8. **Verification**: Performs automated health checks and prints the live UI URLs.

---

## 🛠️ Manual Step-by-Step Deployment (Alternative)

If you prefer running individual scripts manually step-by-step:

### Step 1 — Provision S3 Storage
```bash
python scripts/setup_s3.py
```

### Step 2 — Provision OpenSearch Serverless Vector Index
```bash
python scripts/setup_opensearch.py
```

### Step 3 — Provision Bedrock Knowledge Base
```bash
python scripts/setup_knowledge_base.py
```

### Step 4 — Upload Documents & Ingest
```bash
python scripts/upload_documents.py
```

### Step 5 — Provision Bedrock Guardrails
```bash
python guardrails/setup_guardrail.py
```

### Step 6 — Deploy EKS (k8s 1.34) & TinyLlama Helm Chart
```bash
cd bonus/eks/terraform
terraform apply -auto-approve
aws eks update-kubeconfig --region us-east-1 --name knowledge-assistant-eks
helm upgrade --install tinyllama ../helm/tinyllama --namespace default
```

### Step 7 — Deploy Code Bundle & Launch EC2 App
```bash
python scripts/deploy_to_s3.py
python scripts/setup_ec2_service.py
```

---

## 🧹 Cleanup / Teardown Command

To tear down all resources and stop AWS charges when finished:

```bash
python scripts/cleanup_aws.py
```
