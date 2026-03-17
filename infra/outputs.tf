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
  }
}
