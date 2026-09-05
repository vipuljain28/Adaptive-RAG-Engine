# Enterprise Knowledge Assistant (Capstone Project)

An enterprise-grade Knowledge Assistant leveraging Amazon Bedrock, OpenSearch Serverless, Streamlit, and EKS. 

## Features
- **Dynamic Model Routing**: Routes complex queries to Amazon Bedrock (Anthropic Claude) and simpler/cost-sensitive queries to a self-hosted TinyLlama instance on EKS.
- **RAG Architecture**: Uses Amazon Titan Embeddings and OpenSearch Serverless for precise document retrieval.
- **Security**: Amazon Bedrock Guardrails for PII anonymization and content filtering.
- **One-Command Deployment**: Fully automated Infrastructure as Code using Terraform.

## Setup
1. Ensure AWS CLI, Terraform, and Python are installed.
2. Clone this repository.
3. Configure your AWS credentials.
4. Run `python scripts/deploy_all.py`.
5. Access the application on the provided EC2 public IP at port `8501`.

## Documentation
Please check the `docs` folder for architectural diagrams, run guides, and submission reports.
