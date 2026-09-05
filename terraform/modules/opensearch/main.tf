data "aws_caller_identity" "current" {}

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
  name        = "${var.project_name}-acc-${var.environment}"
  type        = "data"
  description = "Allow Bedrock KB role and caller to manage indices and documents"
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
    Principal = [var.kb_role_arn, data.aws_caller_identity.current.arn]
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

resource "null_resource" "create_index" {
  depends_on = [aws_opensearchserverless_collection.kb]

  provisioner "local-exec" {
    command = "python ${path.module}/../../../scripts/create_os_index.py ${aws_opensearchserverless_collection.kb.id} us-east-1"
  }
}

