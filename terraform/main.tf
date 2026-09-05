terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
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
  source        = "./modules/iam"
  project_name  = var.project_name
  environment   = var.environment
  s3_bucket_arn = module.s3.bucket_arn
  tags          = local.tags
}

# ── OpenSearch Serverless Module ──────────────────────────────────────────────
module "opensearch" {
  source       = "./modules/opensearch"
  project_name = var.project_name
  environment  = var.environment
  kb_role_arn  = module.iam.knowledge_base_role_arn
  tags         = local.tags
}

# ── Bedrock Knowledge Base Module ─────────────────────────────────────────────
module "bedrock" {
  source         = "./modules/bedrock"
  project_name   = var.project_name
  environment    = var.environment
  kb_role_arn    = module.iam.knowledge_base_role_arn
  s3_bucket_arn  = module.s3.bucket_arn
  collection_arn = module.opensearch.collection_arn
  aws_region     = var.aws_region
  tags           = local.tags
}

# ── Bedrock Guardrail Module ──────────────────────────────────────────────────
module "guardrail" {
  source       = "./modules/guardrail"
  project_name = var.project_name
  environment  = var.environment
  tags         = local.tags
}

# ── EC2 Module ────────────────────────────────────────────────────────────────
module "ec2" {
  source           = "./modules/ec2"
  project_name     = var.project_name
  environment      = var.environment
  instance_type    = var.ec2_instance_type
  key_pair_name    = var.ec2_key_pair_name
  my_ip_cidr       = var.my_ip_cidr
  ec2_role_arn     = module.iam.ec2_role_arn
  ec2_profile_name = module.iam.ec2_instance_profile_name
  tags             = local.tags
}
