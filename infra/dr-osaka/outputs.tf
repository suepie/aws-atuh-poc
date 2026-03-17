output "dr_cognito_user_pool_id" {
  description = "DR Cognito User Pool ID (Osaka)"
  value       = aws_cognito_user_pool.dr.id
}

output "dr_cognito_client_id" {
  description = "DR SPA App Client ID (Osaka)"
  value       = aws_cognito_user_pool_client.dr_spa.id
}

output "dr_cognito_domain" {
  description = "DR Cognito Hosted UI domain (Osaka)"
  value       = "https://${aws_cognito_user_pool_domain.dr.domain}.auth.ap-northeast-3.amazoncognito.com"
}

output "dr_cognito_issuer" {
  description = "DR OIDC Issuer URL (Osaka)"
  value       = "https://cognito-idp.ap-northeast-3.amazonaws.com/${aws_cognito_user_pool.dr.id}"
}

output "dr_jwks_url" {
  description = "DR JWKS URL (Osaka)"
  value       = "https://cognito-idp.ap-northeast-3.amazonaws.com/${aws_cognito_user_pool.dr.id}/.well-known/jwks.json"
}

output "auth0_callback_url_osaka" {
  description = "Auth0 に追加設定する Allowed Callback URL (大阪)"
  value       = var.auth0_enabled ? "https://${aws_cognito_user_pool_domain.dr.domain}.auth.ap-northeast-3.amazoncognito.com/oauth2/idpresponse" : "N/A"
}
