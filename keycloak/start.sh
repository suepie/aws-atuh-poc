#!/bin/bash
# Keycloak環境を起動する
# Usage: bash start.sh
set -e

AWS_REGION="ap-northeast-1"

echo "=== Starting RDS instance ==="
aws rds start-db-instance \
  --db-instance-identifier auth-poc-kc-db \
  --region "$AWS_REGION" 2>/dev/null || echo "RDS already running or starting"

echo "Waiting for RDS to become available (this may take 5-10 minutes)..."
aws rds wait db-instance-available \
  --db-instance-identifier auth-poc-kc-db \
  --region "$AWS_REGION"
echo "RDS is available."

echo "=== Starting ECS service (desired_count=1) ==="
aws ecs update-service \
  --cluster auth-poc-kc-cluster \
  --service auth-poc-kc-service \
  --desired-count 1 \
  --region "$AWS_REGION"

echo ""
echo "Keycloak environment starting."
echo "ECS task will take 1-2 minutes to become healthy."
echo ""
echo "Check status:"
echo "  aws ecs describe-services --cluster auth-poc-kc-cluster --services auth-poc-kc-service --query 'services[0].{running: runningCount, desired: desiredCount}'"
echo ""
cd "$(dirname "$0")/../infra/keycloak" && echo "Keycloak URL: $(terraform output -raw keycloak_url)"
