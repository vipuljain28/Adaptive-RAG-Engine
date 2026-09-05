variable "project_name"     { type = string }
variable "environment"      { type = string }
variable "instance_type"    { type = string }
variable "key_pair_name"    { type = string }
variable "my_ip_cidr"       { type = string }
variable "ec2_role_arn"     { type = string }
variable "ec2_profile_name" { type = string }
variable "tags"             { type = map(string) }
