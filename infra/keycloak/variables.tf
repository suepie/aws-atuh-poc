variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-northeast-1"
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

variable "app_callback_urls" {
  description = "Allowed callback URLs for SPA"
  type        = list(string)
  default     = ["http://localhost:5173/callback"]
}
