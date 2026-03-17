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

variable "callback_urls" {
  description = "OAuth callback URLs"
  type        = list(string)
  default     = ["http://localhost:5173/callback"]
}

variable "logout_urls" {
  description = "OAuth logout URLs"
  type        = list(string)
  default     = ["http://localhost:5173/"]
}

# ==============================================================================
# Phase 2: Auth0 外部IdP設定
# ==============================================================================

variable "auth0_enabled" {
  description = "Auth0 IdP連携を有効にするか"
  type        = bool
  default     = false
}

variable "auth0_domain" {
  description = "Auth0 tenant domain (例: auth-poc.auth0.com)"
  type        = string
  default     = ""
}

variable "auth0_client_id" {
  description = "Auth0 Application の Client ID"
  type        = string
  default     = ""
}

variable "auth0_client_secret" {
  description = "Auth0 Application の Client Secret"
  type        = string
  default     = ""
  sensitive   = true
}

# ==============================================================================
# Phase 5: DR Cognito（大阪）設定
# dr-osaka の terraform output から取得して設定する
# ==============================================================================

variable "dr_cognito_user_pool_id" {
  description = "DR Cognito User Pool ID (大阪、dr-osaka terraform output から取得)"
  type        = string
  default     = ""
}

variable "dr_cognito_client_id" {
  description = "DR Cognito App Client ID (大阪、dr-osaka terraform output から取得)"
  type        = string
  default     = ""
}
