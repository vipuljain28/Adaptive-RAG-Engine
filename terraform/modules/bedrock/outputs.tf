output "knowledge_base_id"  { value = aws_bedrockagent_knowledge_base.main.id }
output "knowledge_base_arn" { value = aws_bedrockagent_knowledge_base.main.arn }
output "data_source_id"     { value = aws_bedrockagent_data_source.s3.data_source_id }
