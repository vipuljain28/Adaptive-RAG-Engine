# Knowledge Assistant - Run Guide

Welcome to the Knowledge Assistant project! This infrastructure runs on AWS (EC2, EKS, OpenSearch Serverless, Bedrock Knowledge Bases) and is fully automated via Terraform and Python orchestration.

## Prerequisites
1. **AWS CLI** installed and configured (`aws configure`) with Admin credentials.
2. **Terraform** (>= 1.5.0) installed.
3. **Python 3.9+** with `boto3`, `python-dotenv`, `requests`, `opensearch-py`, `requests-aws4auth` installed (`pip install -r requirements.txt`).
4. **Helm** and **kubectl** installed (for EKS / TinyLlama deployment).

## Setup
1. Copy `.env.template` to `.env` (optional, as the script will automatically populate the necessary variables).
2. Ensure you have your `documents/` ready for ingestion in the root directory (optional).

## Single-Command Deployment

To deploy the entire stack from scratch, run the master deployment script. This script orchestrates:
1. Terraform creation for Main infrastructure (EC2, Bedrock, OpenSearch, S3).
2. Terraform creation for EKS (TinyLlama).
3. Automatic Bedrock Knowledge Base vector index creation.
4. Document upload & synchronization.
5. Pushing app code to the EC2 instance and restarting the Streamlit service.

### On Windows (PowerShell)
```powershell
.\deploy_all.ps1
```

### On macOS / Linux
```bash
./deploy_all.sh
```

At the end of the script, it will print out the final **Web UI URL** (e.g. `http://<EC2-IP>:8501`).

## Single-Command Teardown

To clean up all AWS resources and prevent runaway billing, run the master destroy script. This script gracefully removes blocking Kubernetes load balancers and empties S3 buckets before executing `terraform destroy`.

### On Windows (PowerShell)
```powershell
.\destroy_all.ps1
```

### On macOS / Linux
```bash
./destroy_all.sh
```

## Troubleshooting
- **Terraform `ValidationException` (Bedrock KB)**: OpenSearch index creation can sometimes lag. If the deploy script fails here, just re-run `.\deploy_all.ps1` - it is idempotent!
- **EC2 Instance Not Updating**: If you make changes to the app code and want to push them to the running EC2 instance without doing a full tear-down, simply run:
  ```bash
  python scripts/deploy_to_s3.py
  python scripts/fix_ec2.py
  ```
