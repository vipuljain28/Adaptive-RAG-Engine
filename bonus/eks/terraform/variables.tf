variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "cluster_name" {
  type    = string
  default = "knowledge-assistant-eks"
}

variable "kubernetes_version" {
  type    = string
  default = "1.34"
}

variable "node_instance_type" {
  type        = string
  default     = "t3.xlarge"
  description = "Instance type for LLM inference."
}

variable "desired_nodes" {
  type    = number
  default = 1
}

variable "min_nodes" {
  type    = number
  default = 0
}

variable "max_nodes" {
  type    = number
  default = 2
}

variable "tags" {
  type    = map(string)
  default = {}
}
