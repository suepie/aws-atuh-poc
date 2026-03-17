# ==============================================================================
# 集約 Cognito User Pool（共通認証基盤アカウント相当）
# ==============================================================================

resource "aws_cognito_user_pool" "central" {
  name = "${var.project_name}-central"

  # パスワードポリシー
  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = false
    require_uppercase = true
  }

  # ユーザー名の設定（emailでログイン可能）
  username_attributes = ["email"]

  # 自動検証属性
  auto_verified_attributes = ["email"]

  # スキーマ（カスタム属性）
  schema {
    name                = "tenant_id"
    attribute_data_type = "String"
    mutable             = true

    string_attribute_constraints {
      min_length = 1
      max_length = 64
    }
  }

  schema {
    name                = "roles"
    attribute_data_type = "String"
    mutable             = true

    string_attribute_constraints {
      min_length = 0
      max_length = 256
    }
  }

  # アカウントリカバリ
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  tags = {
    Project = var.project_name
    Role    = "central-cognito"
  }
}

# ==============================================================================
# Cognito Domain（Hosted UI 用）
# ==============================================================================

resource "aws_cognito_user_pool_domain" "central" {
  domain       = "${var.project_name}-central"
  user_pool_id = aws_cognito_user_pool.central.id
}

# ==============================================================================
# App Client（SPA用 - PKCE、シークレットなし）
# ==============================================================================

resource "aws_cognito_user_pool_client" "spa" {
  name         = "${var.project_name}-spa"
  user_pool_id = aws_cognito_user_pool.central.id

  # SPA なのでシークレットなし
  generate_secret = false

  # OAuth 設定
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_scopes                 = ["openid", "profile", "email"]
  supported_identity_providers         = var.auth0_enabled ? ["COGNITO", aws_cognito_identity_provider.auth0[0].provider_name] : ["COGNITO"]

  # コールバック URL
  callback_urls = var.callback_urls
  logout_urls   = var.logout_urls

  # トークン有効期限
  id_token_validity      = 1  # 1時間
  access_token_validity  = 1  # 1時間
  refresh_token_validity = 30 # 30日

  token_validity_units {
    id_token      = "hours"
    access_token  = "hours"
    refresh_token = "days"
  }

  # 読み取り可能属性
  read_attributes = [
    "email",
    "email_verified",
    "name",
    "custom:tenant_id",
    "custom:roles",
  ]

  # 書き込み可能属性
  write_attributes = [
    "email",
    "name",
    "custom:tenant_id",
    "custom:roles",
  ]

  # トークン取消を有効化
  enable_token_revocation = true

  # PKCE を強制するため明示的なフロー設定は不要
  # oidc-client-ts がクライアント側で PKCE を自動的に使用
  explicit_auth_flows = [
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH",
  ]
}

# ==============================================================================
# Phase 2: Auth0 外部IdP（Entra ID 代替）
# ==============================================================================

resource "aws_cognito_identity_provider" "auth0" {
  count = var.auth0_enabled ? 1 : 0

  user_pool_id  = aws_cognito_user_pool.central.id
  provider_name = "Auth0"
  provider_type = "OIDC"

  provider_details = {
    client_id                = var.auth0_client_id
    client_secret            = var.auth0_client_secret
    oidc_issuer              = "https://${var.auth0_domain}/"
    attributes_request_method = "GET"
    authorize_scopes         = "openid email profile"
  }

  # クレームマッピング（Auth0 → Cognito カスタム属性）
  # 本番では Entra ID のクレーム名に合わせてマッピングする
  attribute_mapping = {
    email    = "email"
    name     = "name"
    username = "sub"
  }
}

# ==============================================================================
# テスト用ユーザーグループ
# ==============================================================================

resource "aws_cognito_user_group" "expense_users" {
  name         = "expense-users"
  user_pool_id = aws_cognito_user_pool.central.id
  description  = "経費精算システムのユーザー"
}

resource "aws_cognito_user_group" "travel_users" {
  name         = "travel-users"
  user_pool_id = aws_cognito_user_pool.central.id
  description  = "出張予約システムのユーザー"
}

resource "aws_cognito_user_group" "admins" {
  name         = "admins"
  user_pool_id = aws_cognito_user_pool.central.id
  description  = "管理者"
}
