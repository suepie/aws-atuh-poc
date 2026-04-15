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

# Auth0 設定（東京と同じ値を使用）
variable "auth0_enabled" {
  type    = bool
  default = false
}

variable "auth0_domain" {
  type    = string
  default = ""
}

variable "auth0_client_id" {
  type    = string
  default = ""
}

variable "auth0_client_secret" {
  type      = string
  default   = ""
  sensitive = true
}
