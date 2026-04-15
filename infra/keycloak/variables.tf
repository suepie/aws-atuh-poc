variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-northeast-1"
}

variable "project_name" {
  description = "Project name prefix"
  type        = string
  default     = "auth-poc"
}

variable "environment" {
  description = "Environment name (poc, dev, stg, prod)"
  type        = string
  default     = "poc"
}

variable "owner" {
  description = "Owner of the resources"
  type        = string
  default     = "auth-poc"
}

variable "db_password" {
  description = "RDS PostgreSQL password for Keycloak"
  type        = string
  sensitive   = true
}

variable "keycloak_admin_password" {
  description = "Keycloak admin console password"
  type        = string
  sensitive   = true
}

variable "keycloak_image_tag" {
  description = "Keycloak Docker image tag"
  type        = string
  default     = "latest"
}

variable "allowed_cidr_blocks" {
  description = "ALB へのアクセスを追加で許可するCIDRブロック（例: [\"203.0.113.10/32\"]）。実行者のIPは自動追加される。"
  type        = list(string)
  default     = []
}

variable "app_callback_urls" {
  description = "Allowed callback URLs for SPA"
  type        = list(string)
  default     = ["http://localhost:5173/callback"]
}
