#!/bin/bash
# Keycloak Docker イメージをビルドしてECRにpushする
# Usage: bash deploy.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INFRA_DIR="$SCRIPT_DIR/../infra/keycloak"
AWS_REGION="ap-northeast-1"

# ECR Repository URLを取得
ECR_URL=$(cd "$INFRA_DIR" && terraform output -raw ecr_repository_url)
AWS_ACCOUNT_ID=$(echo "$ECR_URL" | cut -d. -f1)

echo "=== Building Keycloak image ==="
cd "$SCRIPT_DIR"
docker build --platform linux/amd64 -t auth-poc-kc .

echo "=== Logging in to ECR ==="
aws ecr get-login-password --region "$AWS_REGION" | \
  docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

echo "=== Tagging and pushing ==="
docker tag auth-poc-kc:latest "$ECR_URL:latest"
docker push "$ECR_URL:latest"

echo "=== Updating ECS service ==="
aws ecs update-service \
  --cluster auth-poc-kc-cluster \
  --service auth-poc-kc-service \
  --force-new-deployment \
  --region "$AWS_REGION"

echo ""
echo "Deploy complete. Keycloak will be available at:"
cd "$INFRA_DIR" && terraform output keycloak_url
echo ""
echo "ECS service is updating. Check status with:"
echo "  aws ecs describe-services --cluster auth-poc-kc-cluster --services auth-poc-kc-service --query 'services[0].deployments'"
