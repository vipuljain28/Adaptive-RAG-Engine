variable "project_name"    { type = string }
variable "environment"     { type = string }
variable "kb_role_arn"     { type = string }
variable "s3_bucket_arn"   { type = string }
variable "collection_arn"  { type = string }
variable "aws_region"      { type = string }
variable "tags"            { type = map(string) }
