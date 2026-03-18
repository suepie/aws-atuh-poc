# ==============================================================================
# Phase 5: DR用 Cognito User Pool（大阪リージョン）
# 東京の集約Cognitoと同一構成。フェイルオーバー時に使用。
# ==============================================================================

resource "aws_cognito_user_pool" "dr" {
  name = "${var.project_name}-dr-osaka"

  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = false
    require_uppercase = true
  }

  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

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

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  tags = {
    Project = var.project_name
    Role    = "dr-cognito-osaka"
  }
}

resource "aws_cognito_user_pool_domain" "dr" {
  domain       = "${var.project_name}-dr-osaka"
  user_pool_id = aws_cognito_user_pool.dr.id
}

resource "aws_cognito_user_pool_client" "dr_spa" {
  name         = "${var.project_name}-dr-spa"
  user_pool_id = aws_cognito_user_pool.dr.id

  generate_secret = false

  allowed_oauth_flows                  = ["code"]
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_scopes                 = ["openid", "profile", "email"]
  supported_identity_providers         = ["COGNITO", aws_cognito_identity_provider.auth0_dr.provider_name]

  callback_urls = var.callback_urls
  logout_urls   = var.logout_urls

  id_token_validity      = 1
  access_token_validity  = 1
  refresh_token_validity = 30

  token_validity_units {
    id_token      = "hours"
    access_token  = "hours"
    refresh_token = "days"
  }

  read_attributes = [
    "email",
    "email_verified",
    "name",
    "custom:tenant_id",
    "custom:roles",
  ]

  write_attributes = [
    "email",
    "name",
    "custom:tenant_id",
    "custom:roles",
  ]

  enable_token_revocation = true

  explicit_auth_flows = [
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH",
  ]
}

# Auth0 IdP（手動エンドポイント指定）
# 大阪リージョンでは Cognito の .well-known 自動検出が Auth0 に対して失敗するため、
# コンソールの「Manual input」モードで作成し terraform import した。
# 以下の設定はコンソール作成時の内容と一致させている。
# See: ADR-007
resource "aws_cognito_identity_provider" "auth0_dr" {
  user_pool_id  = aws_cognito_user_pool.dr.id
  provider_name = "Auth0"
  provider_type = "OIDC"

  provider_details = {
    client_id                     = var.auth0_client_id
    client_secret                 = var.auth0_client_secret
    oidc_issuer                   = "https://${var.auth0_domain}"
    authorize_scopes              = "openid email profile"
    attributes_request_method     = "GET"
    # 手動エンドポイント指定（.well-known 自動検出のバイパス）
    authorize_url                 = "https://${var.auth0_domain}/authorize"
    token_url                     = "https://${var.auth0_domain}/oauth/token"
    attributes_url                = "https://${var.auth0_domain}/userinfo"
    jwks_uri                      = "https://${var.auth0_domain}/.well-known/jwks.json"
    attributes_url_add_attributes = "false"
  }

  attribute_mapping = {
    email    = "email"
    name     = "name"
    username = "sub"
  }

  lifecycle {
    # コンソールで作成→importした場合、provider_detailsの差分で再作成されないようにする
    ignore_changes = [provider_details]
  }
}

# テスト用グループ（東京と同じ）
resource "aws_cognito_user_group" "dr_expense_users" {
  name         = "expense-users"
  user_pool_id = aws_cognito_user_pool.dr.id
}

resource "aws_cognito_user_group" "dr_travel_users" {
  name         = "travel-users"
  user_pool_id = aws_cognito_user_pool.dr.id
}

resource "aws_cognito_user_group" "dr_admins" {
  name         = "admins"
  user_pool_id = aws_cognito_user_pool.dr.id
}
