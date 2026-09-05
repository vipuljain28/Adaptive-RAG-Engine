# 1-Command Install & 1-Command Destroy Guide

This repository provides single-command lifecycle management for the entire **Knowledge Assistant** platform across **Terraform**, **AWS Bedrock**, **OpenSearch Serverless**, **Amazon EKS (Kubernetes 1.34)**, and **Amazon EC2**.

---

## ⚡ 1-Command Install (Full Deployment)

To provision all infrastructure via Terraform, populate `.env` with resource IDs, ingest documents into Bedrock KB, deploy EKS (k8s 1.34) + EC2, and launch the application:

```bash
python deploy_all.py
```

*Or on Windows (PowerShell):*
```powershell
.\deploy_all.ps1
```

*Or on Linux / macOS (Bash):*
```bash
./deploy_all.sh
```

---

## 🧹 1-Command Destroy (Full Teardown)

To disassociate Kubernetes LoadBalancers, empty S3 objects, run `terraform destroy` across all modules, and stop AWS billing:

```bash
python destroy_all.py
```

*Or on Windows (PowerShell):*
```powershell
.\destroy_all.ps1
```

*Or on Linux / macOS (Bash):*
```bash
./destroy_all.sh
```

---

## 🔄 What Happens Under the Hood

### 1-Command Install (`deploy_all.py`):
1. **Terraform Main Infrastructure**: Provisions S3 storage, IAM roles, OpenSearch Serverless collection & index, Bedrock Knowledge Base & Data Source, Bedrock Guardrail, and EC2 application host.
2. **Environment Auto-Binding**: Extracts Terraform JSON outputs (`terraform output -json`) and populates `.env`.
3. **Document Ingestion**: Uploads PDFs & web documents to S3 and runs Bedrock KB sync job.
4. **Terraform EKS Cluster**: Provisions EKS cluster (k8s 1.34) and AL2023 nodes, deploys TinyLlama Helm chart with LoadBalancer service, and sets ELB timeout to 300s.
5. **EC2 App Deployment**: Bundles code into `app_deploy.zip`, uploads to S3, deploys to EC2 host via SSM, and restarts `knowledge-assistant.service`.

### 1-Command Destroy (`destroy_all.py`):
1. **Pre-Cleanup**: Automatically uninstalls Helm releases, deletes Kubernetes LoadBalancer services (`kubectl delete svc`), and disassociates orphan AWS Classic LoadBalancers attached to EKS subnets.
2. **S3 Object Emptying**: Deletes all object keys, version markers, and delete markers from S3 buckets so Terraform S3 deletion succeeds without `BucketNotEmpty` errors.
3. **Terraform EKS Destroy**: Executes `terraform destroy -auto-approve` in `bonus/eks/terraform`.
4. **Terraform Main Destroy**: Executes `terraform destroy -auto-approve` in `terraform/`.

---

## 🌐 Application Access Endpoints

After running `python deploy_all.py`:
- **Chat Web UI**: `http://<EC2_PUBLIC_IP>:8501/chat`
- **Analytics Dashboard**: `http://<EC2_PUBLIC_IP>:8501/analytics`
- **EKS TinyLlama Health**: `http://<LOADBALANCER_DNS>:8080/health`
