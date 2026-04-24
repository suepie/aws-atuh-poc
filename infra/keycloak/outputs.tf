output "keycloak_url" {
  description = "Keycloak URL (ALB)"
  value       = "http://${aws_lb.keycloak.dns_name}"
}

output "keycloak_admin_url" {
  description = "Keycloak Admin Console URL (Admin ALB - IP restricted)"
  value       = "http://${aws_lb.keycloak_admin.dns_name}/admin"
}

output "keycloak_public_url" {
  description = "Keycloak Public URL (OIDC endpoints)"
  value       = "http://${aws_lb.keycloak.dns_name}"
}

output "keycloak_oidc_issuer" {
  description = "Keycloak OIDC Issuer URL"
  value       = "http://${aws_lb.keycloak.dns_name}/realms/auth-poc"
}

output "keycloak_jwks_url" {
  description = "Keycloak JWKS URL"
  value       = "http://${aws_lb.keycloak.dns_name}/realms/auth-poc/protocol/openid-connect/certs"
}

output "ecr_repository_url" {
  description = "ECR Repository URL for docker push"
  value       = aws_ecr_repository.keycloak.repository_url
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = aws_db_instance.keycloak.endpoint
}

# 停止/起動コマンド
output "commands" {
  description = "Useful commands for cost management"
  value = {
    stop_ecs  = "aws ecs update-service --cluster ${aws_ecs_cluster.keycloak.name} --service ${aws_ecs_service.keycloak.name} --desired-count 0"
    start_ecs = "aws ecs update-service --cluster ${aws_ecs_cluster.keycloak.name} --service ${aws_ecs_service.keycloak.name} --desired-count 1"
    stop_rds  = "aws rds stop-db-instance --db-instance-identifier ${aws_db_instance.keycloak.identifier}"
    start_rds = "aws rds start-db-instance --db-instance-identifier ${aws_db_instance.keycloak.identifier}"
  }
}

# VPC Lambda Authorizer (ADR-012)
output "vpc_authorizer_function_name" {
  description = "VPC Lambda Authorizer function name (ADR-012)"
  value       = aws_lambda_function.vpc_authorizer.function_name
}

output "vpc_authorizer_function_arn" {
  description = "VPC Lambda Authorizer function ARN"
  value       = aws_lambda_function.vpc_authorizer.arn
}

output "vpc_authorizer_invoke_arn" {
  description = "VPC Lambda Authorizer invoke ARN (for API Gateway)"
  value       = aws_lambda_function.vpc_authorizer.invoke_arn
}

output "keycloak_internal_alb_dns" {
  description = "Internal ALB DNS name (VPC-only)"
  value       = aws_lb.keycloak_internal.dns_name
}

output "keycloak_internal_jwks_url" {
  description = "Internal ALB 経由の JWKS URL (VPC 内のみ到達可)"
  value       = "http://${aws_lb.keycloak_internal.dns_name}/realms/auth-poc/protocol/openid-connect/certs"
}

# SPA用設定
output "spa_env_config" {
  description = "Environment variables for React SPA (.env)"
  value = {
    VITE_KEYCLOAK_AUTHORITY = "http://${aws_lb.keycloak.dns_name}/realms/auth-poc"
    VITE_KEYCLOAK_CLIENT_ID = "auth-poc-spa"
  }
}
