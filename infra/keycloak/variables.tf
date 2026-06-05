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

variable "vpc_cidr" {
  description = "CIDR block for the Keycloak VPC"
  type        = string
  default     = "10.0.0.0/16"
}

# ==============================================================================
# VPC Lambda Authorizer 用: Cognito 情報
# Tokyo stack の terraform output から手動で取得して tfvars に設定する
# ==============================================================================

variable "central_cognito_user_pool_id" {
  description = "Central Cognito User Pool ID (Tokyo stack output)"
  type        = string
  default     = ""
}

variable "central_cognito_client_id" {
  description = "Central Cognito App Client ID"
  type        = string
  default     = ""
}

variable "local_cognito_user_pool_id" {
  description = "Local Cognito User Pool ID"
  type        = string
  default     = ""
}

variable "local_cognito_client_id" {
  description = "Local Cognito App Client ID"
  type        = string
  default     = ""
}

# ==============================================================================
# RDS Restore from Snapshot (VPC 移行時のデータ保全用)
# ==============================================================================

variable "rds_snapshot_identifier" {
  description = "RDS を既存スナップショットから復元する場合のスナップショット ID。空文字列なら新規作成。"
  type        = string
  default     = ""
}

# ==============================================================================
# Stage A-2: HA / Multi-AZ 設定
# ==============================================================================

variable "keycloak_desired_count" {
  description = "ECS Service の desired_count 初期値。HA 検証は 2 以上。停止時は 0 を CLI で指定（lifecycle.ignore_changes で Terraform からの変更は無視される）"
  type        = number
  default     = 2
}

variable "keycloak_autoscale_min" {
  description = "ECS Service Auto Scaling 最小タスク数"
  type        = number
  default     = 2
}

variable "keycloak_autoscale_max" {
  description = "ECS Service Auto Scaling 最大タスク数"
  type        = number
  default     = 4
}

variable "keycloak_db_pool_max_size" {
  description = "Keycloak HikariCP の max pool size。RDS max_connections と (タスク数 × プールサイズ) のバランスを取る。db.t4g.micro (max~105) で 2 task なら 30 が安全側"
  type        = number
  default     = 30
}

variable "rds_multi_az" {
  description = "RDS Multi-AZ 配置（自動フェイルオーバー）。月額 ~$14 → ~$28 に増加"
  type        = bool
  default     = true
}
