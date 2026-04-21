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

# SPA用設定
output "spa_env_config" {
  description = "Environment variables for React SPA (.env)"
  value = {
    VITE_KEYCLOAK_AUTHORITY = "http://${aws_lb.keycloak.dns_name}/realms/auth-poc"
    VITE_KEYCLOAK_CLIENT_ID = "auth-poc-spa"
  }
}
