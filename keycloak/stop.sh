#!/bin/bash
# Keycloak環境を停止してコスト削減する
# Usage: bash stop.sh
set -e

AWS_REGION="ap-northeast-1"

echo "=== Stopping ECS service (desired_count=0) ==="
aws ecs update-service \
  --cluster auth-poc-kc-cluster \
  --service auth-poc-kc-service \
  --desired-count 0 \
  --region "$AWS_REGION"

echo "=== Stopping RDS instance ==="
aws rds stop-db-instance \
  --db-instance-identifier auth-poc-kc-db \
  --region "$AWS_REGION" 2>/dev/null || echo "RDS already stopped or stopping"

echo ""
echo "Keycloak environment stopped."
echo "  ECS: $0 (即時停止)"
echo "  RDS: 数分で停止完了（7日後に自動起動されるので注意）"
echo "  ALB: 常時課金（~$0.80/日）。完全削除は terraform destroy"
echo ""
echo "再開するには: bash start.sh"
