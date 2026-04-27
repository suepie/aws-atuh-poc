# Keycloak 構築手順書（Phase 6-7）

**最終更新**: 2026-03-30

---

## Step 1: Terraform apply（Keycloak）

```bash
cd infra/keycloak
cp terraform.tfvars.example terraform.tfvars
# terraform.tfvars を編集（db_password, keycloak_admin_password）

terraform init
terraform apply
```

作成されるリソース（全て `auth-poc-kc-*` プレフィックス）:
- ALB + Target Group + Listener
- ECS Cluster + Service + Task Definition（2 vCPU / 4 GB）
- RDS PostgreSQL 16.13（db.t4g.micro）
- ECR リポジトリ
- Security Groups（ALB/ECS/RDS）
- CloudWatch Log Group
- IAM Role（ECS Task Execution）

## Step 2: Keycloak Docker イメージ ビルド＆デプロイ

```bash
# Docker Desktop が起動していることを確認
cd keycloak
bash deploy.sh
```

ECSタスク起動まで2-3分待つ。以下で状態確認：
```bash
aws ecs describe-services --cluster auth-poc-kc-cluster --service auth-poc-kc-service --query 'services[0].{running: runningCount}' --output json
```

## Step 3: Keycloak DB の SSL設定修正

初回起動時、master realm の `sslRequired=EXTERNAL` で Admin Console にアクセスできない。
DB を直接更新する（RDSを一時的にpublic化）：

```bash
# infra/keycloak/rds.tf の publicly_accessible を一時的に true に変更
cd infra/keycloak && terraform apply

# DB更新
PGPASSWORD='<db_password>' PGSSLMODE=require psql \
  -h $(terraform output -raw rds_endpoint | cut -d: -f1) \
  -U keycloak -d keycloak \
  -c "UPDATE realm SET ssl_required='NONE' WHERE ssl_required != 'NONE';"

# publicly_accessible を false に戻す
# rds.tf を元に戻して terraform apply

# ECS再起動（キャッシュクリア）
aws ecs update-service --cluster auth-poc-kc-cluster --service auth-poc-kc-service --force-new-deployment
```

## Step 4: Keycloak Admin Console ログイン確認

```
URL: http://<ALB DNS>/admin/master/console/
User: admin
Password: terraform.tfvars の keycloak_admin_password
```

ALB DNSは `terraform output keycloak_url` で確認。

## Step 5: Keycloak Realm 設定

初回インポートが `already exists` でスキップされた場合、手動設定が必要：

1. `auth-poc` realm に切り替え
2. **Clients** → `auth-poc-spa` を確認（なければ作成）
   - Client ID: `auth-poc-spa`
   - Public Client: ON
   - Valid Redirect URIs: `http://localhost:5174/*`
   - Web Origins: `http://localhost:5174`
3. **Users** → テストユーザー作成
   - Username: `test@example.com`
   - Email verified: ON
   - Credentials: `TestUser1!`（Temporary: OFF）

## Step 6: Keycloak MFA 設定（Phase 7）

1. Authentication → Required Actions → `Configure OTP` を Default Action に
2. Users → test@example.com → Required Actions → `Configure OTP` 追加
3. SPAからログイン → TOTP登録

## Step 7: Auth0 Identity Brokering 設定（Phase 7）

#### Auth0 側
Allowed Callback URLs に追加:
```
http://<ALB DNS>/realms/auth-poc/broker/auth0/endpoint
```

Allowed Logout URLs に追加:
```
http://<ALB DNS>/realms/auth-poc/broker/auth0/endpoint/logout_response
```

#### Keycloak 側
1. Identity Providers → Add Provider → OpenID Connect v1.0
2. Alias: `auth0`, Display Name: `Login with Auth0`
3. Discovery Endpoint: `https://<auth0-domain>/.well-known/openid-configuration`
4. Client ID / Secret: Auth0の値
5. Default Scopes: `openid profile email`（Addボタンで追加）

## Step 8: フェデレーションユーザーのMFAスキップ設定

Auth0経由ユーザーに二重MFAを回避させるため：
1. Users → Auth0経由ユーザー → Credentials → OTPエントリを Delete
2. Required Actions → `Configure OTP` を削除

## Step 9: Keycloak SPA 設定

```bash
cd app-keycloak
cp .env.example .env
# .env を編集:
# VITE_KEYCLOAK_AUTHORITY=http://<ALB DNS>/realms/auth-poc
# VITE_KEYCLOAK_CLIENT_ID=auth-poc-spa
# VITE_REDIRECT_URI=http://localhost:5174/callback
# VITE_POST_LOGOUT_URI=http://localhost:5174/

npm install
npm run dev
```

## Step 10: SSO検証用 Client 2（任意）

```bash
# Admin Console で auth-poc-spa-2 を作成（redirect: localhost:5175）
cd app-sso-peer
cp .env.example .env
# VITE_KEYCLOAK_CLIENT_ID=auth-poc-spa-2, ポート5175

npm install
npm run dev
```

## コスト管理

```bash
# 停止（ECS + RDS → ALBの$0.80/日のみ）
bash keycloak/stop.sh

# 起動
bash keycloak/start.sh

# 完全削除
cd infra/keycloak && terraform destroy
```

## トラブルシューティング

| 症状 | 原因 | 対策 |
|------|------|------|
| `HTTPS required` | DB内sslRequired=EXTERNAL | `start-dev` モード or DB直接更新 |
| 502/503 頻発 | CPU 100%スパイク（start-dev起因） | 2 vCPU / 4 GB に増強。本番では start --optimized |
| ECSタスク起動しない | RDS停止中 | `aws rds start-db-instance` → 5-10分待つ |
| Admin Console セッション切れ | セッションCookie期限切れ | `/admin/master/console/` に直接アクセス |
| Auth0ボタンが表示されない | IdP設定の Enabled が OFF | Admin Console → Identity Providers → auth0 → Enabled ON |
| First Broker Login でemail空 | Default Scopes に `profile email` がない | IdP設定で Scopes 追加 |

---

