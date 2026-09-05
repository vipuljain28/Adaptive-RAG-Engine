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

output "guardrail_id" {
  description = "Bedrock Guardrail ID"
  value       = module.guardrail.guardrail_id
}

output "guardrail_version" {
  description = "Bedrock Guardrail Version"
  value       = module.guardrail.guardrail_version
}
