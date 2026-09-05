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
  default     = ""
}

variable "my_ip_cidr" {
  description = "Your IP address in CIDR notation for SSH security group rule"
  type        = string
  default     = "0.0.0.0/0"
}

variable "s3_bucket_suffix" {
  description = "Suffix to append to S3 bucket name (use account ID for uniqueness)"
  type        = string
}
