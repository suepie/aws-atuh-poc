# 環境削除・確認手順

**最終更新**: 2026-03-30

---

## 削除手順（依存関係順）

```bash
# 1. Keycloak（独立state、他に依存なし）
cd infra/keycloak
terraform destroy

# 2. 大阪DR（東京に依存なし）
cd ../dr-osaka
terraform destroy

# 3. 東京（Cognito + API Gateway + Lambda）
cd ..
terraform destroy
```

### 削除確認コマンド

全てのコマンドで結果が空であれば完全削除：

```bash
# Cognito User Pool（東京）
aws cognito-idp list-user-pools --max-results 20 \
  --query 'UserPools[?starts_with(Name,`auth-poc`)].{Name:Name,Id:Id}' --output table

# Cognito User Pool（大阪）
aws cognito-idp list-user-pools --max-results 20 --region ap-northeast-3 \
  --query 'UserPools[?starts_with(Name,`auth-poc`)].{Name:Name,Id:Id}' --output table

# RDS
aws rds describe-db-instances \
  --query 'DBInstances[?starts_with(DBInstanceIdentifier,`auth-poc`)].{Id:DBInstanceIdentifier,Status:DBInstanceStatus}' --output table

# ECS
aws ecs list-clusters --query 'clusterArns[?contains(@,`auth-poc`)]' --output text

# ALB
aws elbv2 describe-load-balancers \
  --query 'LoadBalancers[?starts_with(LoadBalancerName,`auth-poc`)].{Name:LoadBalancerName}' --output table

# ECR
aws ecr describe-repositories \
  --query 'repositories[?starts_with(repositoryName,`auth-poc`)].repositoryName' --output text

# Security Groups
aws ec2 describe-security-groups --filters "Name=group-name,Values=auth-poc-*" \
  --query 'SecurityGroups[].{Name:GroupName,Id:GroupId}' --output table

# CloudWatch Logs
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/auth-poc" \
  --query 'logGroups[].logGroupName' --output text
aws logs describe-log-groups --log-group-name-prefix "/ecs/auth-poc" \
  --query 'logGroups[].logGroupName' --output text

# Lambda
aws lambda list-functions \
  --query 'Functions[?starts_with(FunctionName,`auth-poc`)].FunctionName' --output text

# API Gateway
aws apigateway get-rest-apis \
  --query 'items[?starts_with(name,`auth-poc`)].{Name:name,Id:id}' --output table
```

### 残存リソースの手動削除

Terraform管理外のリソースが残っている場合：

```bash
# CloudWatch Logs（Terraformで削除されない場合がある）
aws logs delete-log-group --log-group-name /aws/lambda/auth-poc-authorizer
aws logs delete-log-group --log-group-name /aws/lambda/auth-poc-backend
aws logs delete-log-group --log-group-name /ecs/auth-poc-kc
```
