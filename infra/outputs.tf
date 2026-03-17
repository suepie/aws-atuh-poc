output "cognito_user_pool_id" {
  description = "Central Cognito User Pool ID"
  value       = aws_cognito_user_pool.central.id
}

output "cognito_user_pool_endpoint" {
  description = "Central Cognito User Pool endpoint"
  value       = aws_cognito_user_pool.central.endpoint
}

output "cognito_client_id" {
  description = "SPA App Client ID"
  value       = aws_cognito_user_pool_client.spa.id
}

output "cognito_domain" {
  description = "Cognito Hosted UI domain"
  value       = "https://${aws_cognito_user_pool_domain.central.domain}.auth.${var.aws_region}.amazoncognito.com"
}

output "cognito_issuer" {
  description = "OIDC Issuer URL"
  value       = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.central.id}"
}

output "jwks_url" {
  description = "JWKS URL for token verification"
  value       = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.central.id}/.well-known/jwks.json"
}

# React SPA 用の設定（.env ファイル生成に使用）
output "spa_env_config" {
  description = "Environment variables for React SPA"
  value = {
    VITE_COGNITO_AUTHORITY = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.central.id}"
    VITE_COGNITO_CLIENT_ID = aws_cognito_user_pool_client.spa.id
    VITE_COGNITO_DOMAIN    = "https://${aws_cognito_user_pool_domain.central.domain}.auth.${var.aws_region}.amazoncognito.com"
    VITE_REDIRECT_URI      = "http://localhost:5173/callback"
    VITE_POST_LOGOUT_URI   = "http://localhost:5173/"
    VITE_AUTH0_IDP_NAME    = var.auth0_enabled ? "Auth0" : ""
    VITE_API_ENDPOINT      = aws_api_gateway_stage.prod.invoke_url
  }
}

# Phase 4: ローカル Cognito
output "local_cognito_user_pool_id" {
  description = "Local Cognito User Pool ID"
  value       = aws_cognito_user_pool.local.id
}

output "local_cognito_client_id" {
  description = "Local SPA App Client ID"
  value       = aws_cognito_user_pool_client.local_spa.id
}

output "local_cognito_domain" {
  description = "Local Cognito Hosted UI domain"
  value       = "https://${aws_cognito_user_pool_domain.local.domain}.auth.${var.aws_region}.amazoncognito.com"
}

output "local_cognito_issuer" {
  description = "Local OIDC Issuer URL"
  value       = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.local.id}"
}

output "api_gateway_url" {
  description = "API Gateway endpoint URL"
  value       = aws_api_gateway_stage.prod.invoke_url
}

output "auth0_callback_url" {
  description = "Auth0 に設定する Allowed Callback URL"
  value       = var.auth0_enabled ? "https://${aws_cognito_user_pool_domain.central.domain}.auth.${var.aws_region}.amazoncognito.com/oauth2/idpresponse" : "N/A (Auth0 disabled)"
}
