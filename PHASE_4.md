# Phase 4 — Cost Comparison & Infrastructure as Code (Terraform)

## Context: What This Capstone Is
An AI-powered Knowledge Assistant built on AWS using Amazon Bedrock, Knowledge Bases,
OpenSearch Serverless, S3, and EC2. Employees ask questions about internal documents.
The app supports text, voice, and image queries with multi-model routing.

## What Previous Phases Already Built — Do Not Recreate
```
app/                            — full Streamlit application (Phases 1-3)
gateway/                        — AI gateway with 3 routing strategies (Phase 3)
guardrails/                     — Bedrock Guardrail setup + test scripts (Phase 2)
scripts/setup_s3.py             — creates S3 bucket via boto3
scripts/upload_documents.py     — uploads docs to S3
scripts/setup_knowledge_base.py — creates KB + data source via boto3
```

**No AWS Console is used anywhere. All resources are created via Terraform or boto3 scripts.**

---

## Phase 4 Scope
Two deliverables:

**Deliverable A — Cost Comparison (Requirement 5)**
- Calculate approximate cost of Claude 3 Sonnet vs Claude 3 Haiku
- Based on a realistic assumed usage pattern
- Produce a recommendation: when to use which model

**Deliverable B — Terraform IaC (Requirement 6)**
- Provision all AWS infrastructure via Terraform
- Covers: S3, IAM roles, OpenSearch Serverless, EC2 (Streamlit host), Bedrock KB resource
- Demonstrates: resources, variables, outputs, modules, state

---

## Requirement Coverage
- **Requirement 5 (10 marks):** LLM cost comparison with recommendation
- **Requirement 6 (10 marks):** Terraform IaC — resources, variables, outputs, state

---

## Project Root
`G:\learn ai\modules\capstone`

---

## New Files to Create in Phase 4
```
docs/
└── cost_comparison.md               # Cost analysis document (Deliverable A)

terraform/
├── main.tf                          # Root module: calls all child modules
├── variables.tf                     # All input variables
├── outputs.tf                       # All outputs (IDs, ARNs, URLs)
├── terraform.tfvars                 # Actual values (gitignored)
├── terraform.tfvars.template        # Template showing required vars
└── modules/
    ├── s3/
    │   ├── main.tf
    │   ├── variables.tf
    │   └── outputs.tf
    ├── iam/
    │   ├── main.tf
    │   ├── variables.tf
    │   └── outputs.tf
    ├── opensearch/
    │   ├── main.tf
    │   ├── variables.tf
    │   └── outputs.tf
    ├── bedrock/
    │   ├── main.tf
    │   ├── variables.tf
    │   └── outputs.tf
    └── ec2/
        ├── main.tf
        ├── variables.tf
        ├── outputs.tf
        └── user_data.sh             # EC2 bootstrap script
```

---

## DELIVERABLE A — `docs/cost_comparison.md`

Write this document in full markdown. Include all sections below.

### Section 1: Models Being Compared
| Property | Claude 3 Sonnet | Claude 3 Haiku |
|---|---|---|
| Bedrock Model ID | anthropic.claude-3-sonnet-20240229-v1:0 | anthropic.claude-3-haiku-20240307-v1:0 |
| Input token price | $0.003 / 1K tokens | $0.00025 / 1K tokens |
| Output token price | $0.015 / 1K tokens | $0.00125 / 1K tokens |
| Relative quality | Higher — better reasoning | Lower — good for simple Q&A |
| Response speed | ~3-5 seconds | ~1-2 seconds |

### Section 2: Assumed Usage Pattern
Define a realistic monthly usage scenario for a team of 50 employees:
- 50 users × 20 queries/day × 22 working days = **22,000 queries/month**
- Average input tokens per query: 800 (question + 5 retrieved document chunks)
- Average output tokens per query: 300 (answer with citations)
- Mix assumption for Auto routing: 60% Haiku (simple queries), 40% Sonnet (complex)

### Section 3: Cost Calculation

#### Claude 3 Sonnet only (all 22,000 queries)
```
Input:  22,000 × 800 tokens = 17,600,000 tokens = 17,600 K tokens
        17,600 × $0.003     = $52.80

Output: 22,000 × 300 tokens = 6,600,000 tokens = 6,600 K tokens
        6,600  × $0.015     = $99.00

Total Sonnet-only: $52.80 + $99.00 = $151.80 / month
```

#### Claude 3 Haiku only (all 22,000 queries)
```
Input:  17,600 K tokens × $0.00025 = $4.40
Output: 6,600  K tokens × $0.00125 = $8.25

Total Haiku-only: $4.40 + $8.25 = $12.65 / month
```

#### Auto routing mix (60% Haiku, 40% Sonnet)
```
Haiku  queries: 13,200  →  Input $2.64  + Output $4.95  = $7.59
Sonnet queries:  8,800  →  Input $21.12 + Output $39.60  = $60.72

Total Auto-routing: $7.59 + $60.72 = $68.31 / month
```

#### Summary table
| Strategy | Monthly Cost | vs Sonnet-only | Quality |
|---|---|---|---|
| Sonnet only | $151.80 | baseline | Best |
| Auto routing | $68.31 | **-55% savings** | Good |
| Haiku only | $12.65 | **-92% savings** | Acceptable for simple Q&A |

### Section 4: Recommendation
Write 3-4 paragraphs covering:
- For high-volume teams where most queries are simple factual lookups → Haiku only saves
  significant cost with acceptable quality
- For enterprise use where accuracy on policy/compliance queries is critical → Sonnet
  ensures reliable answers but costs 12× more
- **Recommended approach: Auto routing** — balances cost and quality. Simple queries
  (60%) go to Haiku at low cost; complex queries (40%) go to Sonnet for quality.
  Saves 55% vs Sonnet-only while maintaining quality where it matters.
- Cost monitoring: Use the analytics dashboard (Phase 1) to track actual token usage
  and adjust the Auto routing threshold if costs drift above budget

### Section 5: Other Cost Factors (brief)
- OpenSearch Serverless: ~$0.24/OCU-hour, minimum 2 OCUs = ~$350/month base
- S3 storage: negligible for text documents (<1 GB = <$0.02/month)
- EC2 t3.small: ~$15/month (on-demand), $9/month (1-year reserved)
- Bedrock Knowledge Base: no additional charge beyond model and OpenSearch costs
- **Total estimated monthly infrastructure: ~$430–$450/month for 50 users**

---

## DELIVERABLE B — Terraform IaC

### Terraform Concepts Demonstrated
| Concept | Where Used |
|---|---|
| Resources | Every `resource` block in modules |
| Variables | `variables.tf` in root + each module |
| Outputs | `outputs.tf` in root + each module — IDs/ARNs fed to scripts |
| Modules | 5 child modules called from root `main.tf` |
| State | Local state by default; instructions to migrate to S3 backend |
| Data sources | `data "aws_caller_identity"` for account ID |

---

### `terraform/terraform.tfvars.template`
```hcl
# Copy to terraform.tfvars and fill in real values
# terraform.tfvars is gitignored — never commit it

aws_region     = "us-east-1"
aws_account_id = ""           # Your 12-digit account ID
project_name   = "knowledge-assistant"
environment    = "dev"

# EC2
ec2_instance_type = "t3.small"
ec2_key_pair_name = ""        # Name of existing EC2 key pair for SSH access
my_ip_cidr        = ""        # Your IP for SSH: "1.2.3.4/32"

# S3
s3_bucket_suffix = ""         # Appended to bucket name for uniqueness; use account ID
```

---

### `terraform/variables.tf`
Declare all root-level input variables with descriptions and defaults where safe.

```hcl
variable "aws_region" {
  description = "AWS region to deploy all resources"
  type        = string
  default     = "us-east-1"
}

variable "aws_account_id" {
  description = "Your 12-digit AWS account ID"
  type        = string
}

variable "project_name" {
  description = "Project name prefix for all resource names"
  type        = string
  default     = "knowledge-assistant"
}

variable "environment" {
  description = "Deployment environment: dev, staging, prod"
  type        = string
  default     = "dev"
}

variable "ec2_instance_type" {
  description = "EC2 instance type for the Streamlit application host"
  type        = string
  default     = "t3.small"
}

variable "ec2_key_pair_name" {
  description = "Name of the EC2 key pair for SSH access"
  type        = string
}

variable "my_ip_cidr" {
  description = "Your IP address in CIDR notation for SSH security group rule"
  type        = string
}

variable "s3_bucket_suffix" {
  description = "Suffix to append to S3 bucket name (use account ID for uniqueness)"
  type        = string
}
```

---

### `terraform/main.tf`
Root module. Configures provider, calls all child modules, wires outputs between modules.

```hcl
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  # To use remote S3 state (recommended for teams), uncomment:
  # backend "s3" {
  #   bucket = "your-terraform-state-bucket"
  #   key    = "knowledge-assistant/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}

locals {
  account_id = data.aws_caller_identity.current.account_id
  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# ── S3 Module ─────────────────────────────────────────────────────────────────
module "s3" {
  source        = "./modules/s3"
  project_name  = var.project_name
  environment   = var.environment
  bucket_suffix = var.s3_bucket_suffix
  tags          = local.tags
}

# ── IAM Module ────────────────────────────────────────────────────────────────
module "iam" {
  source       = "./modules/iam"
  project_name = var.project_name
  environment  = var.environment
  s3_bucket_arn = module.s3.bucket_arn
  tags         = local.tags
}

# ── OpenSearch Serverless Module ──────────────────────────────────────────────
module "opensearch" {
  source            = "./modules/opensearch"
  project_name      = var.project_name
  environment       = var.environment
  kb_role_arn       = module.iam.knowledge_base_role_arn
  tags              = local.tags
}

# ── Bedrock Knowledge Base Module ─────────────────────────────────────────────
module "bedrock" {
  source               = "./modules/bedrock"
  project_name         = var.project_name
  environment          = var.environment
  kb_role_arn          = module.iam.knowledge_base_role_arn
  s3_bucket_arn        = module.s3.bucket_arn
  collection_arn       = module.opensearch.collection_arn
  aws_region           = var.aws_region
  tags                 = local.tags
}

# ── EC2 Module ────────────────────────────────────────────────────────────────
module "ec2" {
  source            = "./modules/ec2"
  project_name      = var.project_name
  environment       = var.environment
  instance_type     = var.ec2_instance_type
  key_pair_name     = var.ec2_key_pair_name
  my_ip_cidr        = var.my_ip_cidr
  ec2_role_arn      = module.iam.ec2_role_arn
  ec2_profile_name  = module.iam.ec2_instance_profile_name
  tags              = local.tags
}
```

---

### `terraform/outputs.tf`
```hcl
output "s3_bucket_name" {
  description = "S3 bucket name — set as S3_BUCKET_NAME in .env"
  value       = module.s3.bucket_name
}

output "knowledge_base_id" {
  description = "Bedrock Knowledge Base ID — set as KNOWLEDGE_BASE_ID in .env"
  value       = module.bedrock.knowledge_base_id
}

output "opensearch_collection_arn" {
  description = "OpenSearch Serverless collection ARN"
  value       = module.opensearch.collection_arn
}

output "ec2_public_ip" {
  description = "EC2 public IP — access app at http://<ip>:8501"
  value       = module.ec2.public_ip
}

output "ec2_public_dns" {
  description = "EC2 public DNS hostname"
  value       = module.ec2.public_dns
}

output "knowledge_base_role_arn" {
  description = "IAM role ARN used by Bedrock Knowledge Base"
  value       = module.iam.knowledge_base_role_arn
}
```


---

### `terraform/modules/s3/variables.tf`
```hcl
variable "project_name"  { type = string }
variable "environment"   { type = string }
variable "bucket_suffix" { type = string }
variable "tags"          { type = map(string) }
```

### `terraform/modules/s3/main.tf`
```hcl
resource "aws_s3_bucket" "documents" {
  bucket = "${var.project_name}-docs-${var.bucket_suffix}"
  tags   = var.tags
}

resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_public_access_block" "documents" {
  bucket                  = aws_s3_bucket.documents.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
```

### `terraform/modules/s3/outputs.tf`
```hcl
output "bucket_name" { value = aws_s3_bucket.documents.id }
output "bucket_arn"  { value = aws_s3_bucket.documents.arn }
```

---

### `terraform/modules/iam/variables.tf`
```hcl
variable "project_name"  { type = string }
variable "environment"   { type = string }
variable "s3_bucket_arn" { type = string }
variable "tags"          { type = map(string) }
```

### `terraform/modules/iam/main.tf`
```hcl
# ── Bedrock Knowledge Base Role ───────────────────────────────────────────────
resource "aws_iam_role" "knowledge_base" {
  name = "${var.project_name}-kb-role-${var.environment}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "bedrock.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
  tags = var.tags
}

resource "aws_iam_role_policy" "kb_s3_access" {
  name = "s3-read-access"
  role = aws_iam_role.knowledge_base.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:GetObject", "s3:ListBucket"]
      Resource = [var.s3_bucket_arn, "${var.s3_bucket_arn}/*"]
    }]
  })
}

resource "aws_iam_role_policy_attachment" "kb_bedrock" {
  role       = aws_iam_role.knowledge_base.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonBedrockFullAccess"
}

# ── EC2 Instance Role ─────────────────────────────────────────────────────────
resource "aws_iam_role" "ec2" {
  name = "${var.project_name}-ec2-role-${var.environment}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "ec2_bedrock" {
  role       = aws_iam_role.ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonBedrockFullAccess"
}

resource "aws_iam_role_policy_attachment" "ec2_s3" {
  role       = aws_iam_role.ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
}

resource "aws_iam_instance_profile" "ec2" {
  name = "${var.project_name}-ec2-profile-${var.environment}"
  role = aws_iam_role.ec2.name
}
```

### `terraform/modules/iam/outputs.tf`
```hcl
output "knowledge_base_role_arn"      { value = aws_iam_role.knowledge_base.arn }
output "ec2_role_arn"                 { value = aws_iam_role.ec2.arn }
output "ec2_instance_profile_name"    { value = aws_iam_instance_profile.ec2.name }
```

---

### `terraform/modules/opensearch/variables.tf`
```hcl
variable "project_name" { type = string }
variable "environment"  { type = string }
variable "kb_role_arn"  { type = string }
variable "tags"         { type = map(string) }
```

### `terraform/modules/opensearch/main.tf`
```hcl
resource "aws_opensearchserverless_security_policy" "encryption" {
  name        = "${var.project_name}-enc-${var.environment}"
  type        = "encryption"
  description = "Encryption policy for Knowledge Assistant collection"
  policy = jsonencode({
    Rules = [{
      Resource     = ["collection/${var.project_name}-${var.environment}"]
      ResourceType = "collection"
    }]
    AWSOwnedKey = true
  })
}

resource "aws_opensearchserverless_security_policy" "network" {
  name        = "${var.project_name}-net-${var.environment}"
  type        = "network"
  description = "Network policy — public access for Bedrock KB"
  policy = jsonencode([{
    Rules = [
      { Resource = ["collection/${var.project_name}-${var.environment}"], ResourceType = "collection" },
      { Resource = ["collection/${var.project_name}-${var.environment}"], ResourceType = "dashboard"  }
    ]
    AllowFromPublic = true
  }])
}

resource "aws_opensearchserverless_access_policy" "kb_access" {
  name        = "${var.project_name}-access-${var.environment}"
  type        = "data"
  description = "Allow Bedrock KB role to manage indices and documents"
  policy = jsonencode([{
    Rules = [
      {
        Resource     = ["collection/${var.project_name}-${var.environment}"]
        Permission   = ["aoss:CreateCollectionItems","aoss:DeleteCollectionItems","aoss:UpdateCollectionItems","aoss:DescribeCollectionItems"]
        ResourceType = "collection"
      },
      {
        Resource     = ["index/${var.project_name}-${var.environment}/*"]
        Permission   = ["aoss:CreateIndex","aoss:DeleteIndex","aoss:UpdateIndex","aoss:DescribeIndex","aoss:ReadDocument","aoss:WriteDocument"]
        ResourceType = "index"
      }
    ]
    Principal = [var.kb_role_arn]
  }])
}

resource "aws_opensearchserverless_collection" "kb" {
  name        = "${var.project_name}-${var.environment}"
  type        = "VECTORSEARCH"
  description = "Vector store for Knowledge Assistant Knowledge Base"
  tags        = var.tags

  depends_on = [
    aws_opensearchserverless_security_policy.encryption,
    aws_opensearchserverless_security_policy.network,
    aws_opensearchserverless_access_policy.kb_access,
  ]
}
```

### `terraform/modules/opensearch/outputs.tf`
```hcl
output "collection_arn"      { value = aws_opensearchserverless_collection.kb.arn }
output "collection_endpoint" { value = aws_opensearchserverless_collection.kb.collection_endpoint }
```


---

### `terraform/modules/bedrock/variables.tf`
```hcl
variable "project_name"    { type = string }
variable "environment"     { type = string }
variable "kb_role_arn"     { type = string }
variable "s3_bucket_arn"   { type = string }
variable "collection_arn"  { type = string }
variable "aws_region"      { type = string }
variable "tags"            { type = map(string) }
```

### `terraform/modules/bedrock/main.tf`
```hcl
resource "aws_bedrockagent_knowledge_base" "main" {
  name        = "${var.project_name}-kb-${var.environment}"
  description = "Knowledge Base for company internal documents"
  role_arn    = var.kb_role_arn

  knowledge_base_configuration {
    type = "VECTOR"
    vector_knowledge_base_configuration {
      embedding_model_arn = "arn:aws:bedrock:${var.aws_region}::foundation-model/amazon.titan-embed-text-v2:0"
    }
  }

  storage_configuration {
    type = "OPENSEARCH_SERVERLESS"
    opensearch_serverless_configuration {
      collection_arn    = var.collection_arn
      vector_index_name = "knowledge-assistant-index"
      field_mapping {
        vector_field   = "embedding"
        text_field     = "text"
        metadata_field = "metadata"
      }
    }
  }

  tags = var.tags
}

resource "aws_bedrockagent_data_source" "s3" {
  knowledge_base_id = aws_bedrockagent_knowledge_base.main.id
  name              = "s3-company-documents"

  data_source_configuration {
    type = "S3"
    s3_configuration {
      bucket_arn          = var.s3_bucket_arn
      inclusion_prefixes  = ["documents/"]
    }
  }
}
```

### `terraform/modules/bedrock/outputs.tf`
```hcl
output "knowledge_base_id"  { value = aws_bedrockagent_knowledge_base.main.id }
output "knowledge_base_arn" { value = aws_bedrockagent_knowledge_base.main.arn }
output "data_source_id"     { value = aws_bedrockagent_data_source.s3.data_source_id }
```

---

### `terraform/modules/ec2/variables.tf`
```hcl
variable "project_name"     { type = string }
variable "environment"      { type = string }
variable "instance_type"    { type = string }
variable "key_pair_name"    { type = string }
variable "my_ip_cidr"       { type = string }
variable "ec2_role_arn"     { type = string }
variable "ec2_profile_name" { type = string }
variable "tags"             { type = map(string) }
```

### `terraform/modules/ec2/main.tf`
```hcl
data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_security_group" "app" {
  name        = "${var.project_name}-sg-${var.environment}"
  description = "Security group for Knowledge Assistant Streamlit app"

  # SSH — restricted to your IP only
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.my_ip_cidr]
    description = "SSH access"
  }

  # Streamlit — open to all (add CloudFront/ALB in production)
  ingress {
    from_port   = 8501
    to_port     = 8501
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Streamlit application"
  }

  # All outbound (needed for AWS API calls)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = var.tags
}

resource "aws_instance" "app" {
  ami                    = data.aws_ami.amazon_linux_2023.id
  instance_type          = var.instance_type
  key_name               = var.key_pair_name
  vpc_security_group_ids = [aws_security_group.app.id]
  iam_instance_profile   = var.ec2_profile_name

  user_data = file("${path.module}/user_data.sh")

  root_block_device {
    volume_size           = 20
    volume_type           = "gp3"
    delete_on_termination = true
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-app-${var.environment}"
  })
}
```

### `terraform/modules/ec2/outputs.tf`
```hcl
output "instance_id"  { value = aws_instance.app.id }
output "public_ip"    { value = aws_instance.app.public_ip }
output "public_dns"   { value = aws_instance.app.public_dns }
```

### `terraform/modules/ec2/user_data.sh`
EC2 bootstrap script. Runs on first launch. Installs Python, clones repo, sets up service.

```bash
#!/bin/bash
set -e

# Update system
dnf update -y
dnf install -y python3.11 python3.11-pip git

# Create app user
useradd -m -s /bin/bash appuser

# Clone repo — replace with your actual Git repo URL or use S3 to download
cd /home/appuser
git clone https://github.com/YOUR_USERNAME/capstone.git
chown -R appuser:appuser capstone

# Set up Python venv
cd capstone
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Create data directory for SQLite conversations
mkdir -p data

# Create systemd service so app restarts on reboot
cat > /etc/systemd/system/knowledge-assistant.service <<EOF
[Unit]
Description=Knowledge Assistant Streamlit App
After=network.target

[Service]
Type=simple
User=appuser
WorkingDirectory=/home/appuser/capstone
Environment="PATH=/home/appuser/capstone/venv/bin"
ExecStart=/home/appuser/capstone/venv/bin/streamlit run app/main.py \
  --server.port 8501 \
  --server.address 0.0.0.0 \
  --server.headless true
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable knowledge-assistant
systemctl start knowledge-assistant
```


---

## Order to Create Files
1. `docs/cost_comparison.md`
2. `terraform/terraform.tfvars.template`
3. `terraform/variables.tf`
4. `terraform/main.tf`
5. `terraform/outputs.tf`
6. `terraform/modules/s3/variables.tf`
7. `terraform/modules/s3/main.tf`
8. `terraform/modules/s3/outputs.tf`
9. `terraform/modules/iam/variables.tf`
10. `terraform/modules/iam/main.tf`
11. `terraform/modules/iam/outputs.tf`
12. `terraform/modules/opensearch/variables.tf`
13. `terraform/modules/opensearch/main.tf`
14. `terraform/modules/opensearch/outputs.tf`
15. `terraform/modules/bedrock/variables.tf`
16. `terraform/modules/bedrock/main.tf`
17. `terraform/modules/bedrock/outputs.tf`
18. `terraform/modules/ec2/variables.tf`
19. `terraform/modules/ec2/main.tf`
20. `terraform/modules/ec2/outputs.tf`
21. `terraform/modules/ec2/user_data.sh`

Also add `terraform.tfvars` and `.terraform/` to `.gitignore`.

---

## How to Run (for the human)
```bash
# 1. Copy the tfvars template and fill in values
cp terraform/terraform.tfvars.template terraform/terraform.tfvars
# Edit terraform/terraform.tfvars with your account ID, key pair name, IP

# 2. Initialise Terraform
cd terraform
terraform init

# 3. Preview what will be created
terraform plan

# 4. Apply (creates all AWS resources — takes ~5 minutes)
terraform apply

# 5. Copy outputs into your .env file
terraform output knowledge_base_id  # → KNOWLEDGE_BASE_ID
terraform output s3_bucket_name     # → S3_BUCKET_NAME
terraform output ec2_public_ip      # → access the app at http://<ip>:8501

# 6. Upload documents and start ingestion
cd ..
python scripts/upload_documents.py
python scripts/setup_knowledge_base.py   # starts ingestion job only (KB already exists)
```

---

## Definition of Done
- `docs/cost_comparison.md` exists with all 5 sections, complete cost tables, and recommendation
- All 21 Terraform files created with valid HCL syntax
- `terraform init` succeeds
- `terraform plan` shows expected resources with no errors
- `terraform apply` creates: S3 bucket, IAM roles, OpenSearch Serverless collection, Bedrock KB, EC2 instance
- `terraform output` prints: bucket name, KB ID, OpenSearch ARN, EC2 IP
- EC2 instance runs the Streamlit app automatically on port 8501 via systemd
- `.gitignore` excludes `terraform.tfvars` and `.terraform/`
