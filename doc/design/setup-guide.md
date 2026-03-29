# 構築手順書

**最終更新**: 2026-03-28（Phase 7 完了時点）

---

## 前提条件

| ツール | バージョン | 用途 |
|--------|----------|------|
| Node.js | 18以上 | React SPA |
| Python | 3.10以上 | Lambda Authorizer ビルド（venv） |
| Terraform | 1.5以上 | IaC |
| AWS CLI | 2.x（認証済み） | AWSリソース操作 |
| Docker Desktop | 最新 | Keycloak イメージビルド（Phase 6） |
| Auth0 | Freeアカウント | 外部IdP代替 |

---

## Phase 1-3: 東京リージョン（集約Cognito + API Gateway）

### Step 1: Auth0 アカウント作成・設定

1. https://auth0.com でFreeアカウント作成
2. **Applications → Create Application → Regular Web Application**
3. Settings で以下をメモ：
   - Domain（例: `dev-xxx.us.auth0.com`）
   - Client ID
   - Client Secret
4. **Allowed Callback URLs** に以下を設定（後で大阪分も追加）:
   ```
   https://auth-poc-central.auth.ap-northeast-1.amazoncognito.com/oauth2/idpresponse
   ```
5. **Allowed Logout URLs** に以下を設定（URLエンコード済み）:
   ```
   https://auth-poc-central.auth.ap-northeast-1.amazoncognito.com/logout?client_id=<CLIENT_ID>&logout_uri=http%3A%2F%2Flocalhost%3A5173%2F
   ```
   ※ `<CLIENT_ID>` は Step 3 の `terraform output cognito_client_id` で取得した値
6. **User Management → Users → Create User** でテストユーザー作成

### Step 2: Terraform 変数ファイル作成（東京）

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars
```

`terraform.tfvars` を編集:
```hcl
auth0_enabled       = true
auth0_domain        = "dev-xxx.us.auth0.com"
auth0_client_id     = "xxxxxxxx"
auth0_client_secret = "xxxxxxxx"
```

### Step 3: Terraform apply（東京）

```bash
cd infra
terraform init
terraform apply
```

作成されるリソース:
- Cognito User Pool（集約: auth-poc-central）
- Cognito User Pool（ローカル: auth-poc-local）
- Auth0 OIDC IdP
- API Gateway + Lambda Authorizer + Backend Lambda

### Step 4: Lambda パッケージビルド

```bash
# Authorizer（venv + Linux向けバイナリ）
bash lambda/authorizer/build.sh

# Backend
cd lambda/backend && zip -j package.zip index.py
```

### Step 5: Lambda デプロイ

```bash
cd infra
terraform apply  # source_code_hash変更を検知して自動更新
```

### Step 6: テストユーザー作成

```bash
# 集約Cognito ローカルユーザー
USER_POOL_ID=$(cd infra && terraform output -raw cognito_user_pool_id)
aws cognito-idp admin-create-user \
  --user-pool-id $USER_POOL_ID \
  --username test@example.com \
  --user-attributes Name=email,Value=test@example.com Name=email_verified,Value=true \
  --temporary-password 'TempPass1!' \
  --message-action SUPPRESS
aws cognito-idp admin-set-user-password \
  --user-pool-id $USER_POOL_ID \
  --username test@example.com \
  --password 'TestUser1!' \
  --permanent

# ローカルCognito パートナーユーザー
LOCAL_POOL_ID=$(cd infra && terraform output -raw local_cognito_user_pool_id)
aws cognito-idp admin-create-user \
  --user-pool-id $LOCAL_POOL_ID \
  --username partner@example.com \
  --user-attributes Name=email,Value=partner@example.com Name=email_verified,Value=true \
  --temporary-password 'TempPass1!' \
  --message-action SUPPRESS
aws cognito-idp admin-set-user-password \
  --user-pool-id $LOCAL_POOL_ID \
  --username partner@example.com \
  --password 'Partner1!' \
  --permanent
```

### Step 7: React SPA 設定

```bash
cd app
npm install
cp .env.example .env
```

`.env` を Terraform output の値で更新:

```bash
# 以下で値を確認
cd ../infra
terraform output spa_env_config
terraform output local_cognito_user_pool_id
terraform output local_cognito_client_id
terraform output local_cognito_domain
```

`.env` の内容:
```
VITE_COGNITO_AUTHORITY=https://cognito-idp.ap-northeast-1.amazonaws.com/<POOL_ID>
VITE_COGNITO_CLIENT_ID=<CLIENT_ID>
VITE_COGNITO_DOMAIN=https://auth-poc-central.auth.ap-northeast-1.amazoncognito.com
VITE_REDIRECT_URI=http://localhost:5173/callback
VITE_POST_LOGOUT_URI=http://localhost:5173/
VITE_AUTH0_IDP_NAME=Auth0
VITE_AUTH0_DOMAIN=dev-xxx.us.auth0.com
VITE_AUTH0_CLIENT_ID=<AUTH0_CLIENT_ID>
VITE_API_ENDPOINT=https://xxxxxxxxxx.execute-api.ap-northeast-1.amazonaws.com/prod
VITE_LOCAL_COGNITO_AUTHORITY=https://cognito-idp.ap-northeast-1.amazonaws.com/<LOCAL_POOL_ID>
VITE_LOCAL_COGNITO_CLIENT_ID=<LOCAL_CLIENT_ID>
VITE_LOCAL_COGNITO_DOMAIN=https://auth-poc-local.auth.ap-northeast-1.amazoncognito.com
```

### Step 8: 起動・動作確認

```bash
cd app
npm run dev
```

http://localhost:5173 にアクセスし、以下を確認:
- ログイン（Hosted UI）→ 認証成功
- ログイン（Auth0）→ Auth0画面 → 認証成功
- ログイン（ローカルCognito）→ 認証成功
- API Tester（トークンあり）→ 200 OK
- API Tester（トークンなし）→ 401 Unauthorized
- ログアウト / 完全ログアウト → 正常動作

---

## Phase 5: 大阪リージョン（DR Cognito）

### Step 9: Terraform apply（大阪）- Auth0 なしで先に作成

```bash
cd infra/dr-osaka
cp terraform.tfvars.example terraform.tfvars
```

`terraform.tfvars` を編集:
```hcl
auth0_enabled = false
```

```bash
terraform init
terraform apply
```

### Step 10: Auth0 IdP をコンソールで手動追加

大阪リージョンではTerraformの`.well-known`自動検出が失敗するため、コンソールで手動作成する。

1. AWSコンソール → **リージョンを大阪（ap-northeast-3）に変更**
2. Cognito → User Pools → `auth-poc-dr-osaka`
3. **Sign-in experience → Add identity provider → OpenID Connect**
4. **Setup method: Manual input** を選択
5. 以下を入力:

| 項目 | 値 |
|------|-----|
| Provider name | `Auth0` |
| Client ID | （東京と同じAuth0 Client ID） |
| Client Secret | （東京と同じAuth0 Client Secret） |
| Authorized scopes | `openid email profile` |
| Issuer URL | `https://dev-xxx.us.auth0.com` |
| Authorization endpoint | `https://dev-xxx.us.auth0.com/authorize` |
| Token endpoint | `https://dev-xxx.us.auth0.com/oauth/token` |
| Userinfo endpoint | `https://dev-xxx.us.auth0.com/userinfo` |
| Jwks uri | `https://dev-xxx.us.auth0.com/.well-known/jwks.json` |

6. Attribute mapping: email→email, name→name, username→sub
7. 保存
8. App Client `auth-poc-dr-spa` → Login pages → Identity providers で `Auth0` を追加

### Step 11: Terraform import

```bash
cd infra/dr-osaka
# terraform.tfvars で auth0_enabled = true に変更
terraform import "aws_cognito_identity_provider.auth0_dr" "ap-northeast-3_XXXXXXXX:Auth0"
terraform plan  # 差分確認
terraform apply  # App Client の supported_identity_providers 更新
```

### Step 12: Auth0 に大阪のURLを追加

Auth0 Dashboard:

**Allowed Callback URLs** に追加（カンマ区切り）:
```
https://auth-poc-dr-osaka.auth.ap-northeast-3.amazoncognito.com/oauth2/idpresponse
```

**Allowed Logout URLs** に追加（カンマ区切り）:
```
https://auth-poc-dr-osaka.auth.ap-northeast-3.amazoncognito.com/logout?client_id=<大阪CLIENT_ID>&logout_uri=http%3A%2F%2Flocalhost%3A5173%2F
```

### Step 13: 東京 Terraform に DR 情報追加

東京の `terraform.tfvars` に追加:
```hcl
dr_cognito_user_pool_id = "ap-northeast-3_XXXXXXXX"
dr_cognito_client_id    = "xxxxxxxxxx"
```

```bash
# Lambda リビルド
bash lambda/authorizer/build.sh

# 東京 Terraform apply（Lambda環境変数にDR issuer追加）
cd infra
terraform apply
```

### Step 14: React SPA に DR 設定追加

`.env` に追加:
```
VITE_DR_COGNITO_AUTHORITY=https://cognito-idp.ap-northeast-3.amazonaws.com/<DR_POOL_ID>
VITE_DR_COGNITO_CLIENT_ID=<DR_CLIENT_ID>
VITE_DR_COGNITO_DOMAIN=https://auth-poc-dr-osaka.auth.ap-northeast-3.amazoncognito.com
```

### Step 15: DR 動作確認

```bash
cd app
npm run dev
```

http://localhost:5173 で以下を確認:
- ログイン（DR 大阪）→ 大阪Hosted UI → 認証成功
- ログイン（DR 大阪 + Auth0）→ Auth0フェデレーション → 認証成功
- API Tester → issuerType=dr で 200 OK
- ログアウト / 完全ログアウト → 正常動作

---

## トラブルシューティング

| 症状 | 原因 | 対策 |
|------|------|------|
| Lambda Authorizer 500エラー | cryptographyバイナリがmacOS用 | `build.sh` でLinux向けビルド（`--platform manylinux2014_x86_64`） |
| `Token is missing the "aud" claim` | Cognitoアクセストークンにaudがない | `verify_aud=False` + `client_id`手動検証 |
| Callback後に認証状態にならない | UserManagerインスタンスが別 | AuthProviderの共有インスタンスを使用 |
| DR Callbackが全て失敗 | stateStore衝突 | プレフィックス分離（oidc.central./oidc.local./oidc.dr.） |
| 大阪で Auth0 IdP作成失敗 | `.well-known`自動検出失敗 | コンソール「Manual input」で作成 → terraform import |
| Auth0ログアウトエラー | Allowed Logout URLsの不一致 | URLエンコード済み完全一致で登録 |
| ログアウトが効かない | ログイン元Cognito判定ミス | `getUserType()`でiss判定（central/local/dr） |

---

## Phase 6-7: Keycloak（ECS Fargate + RDS）

### Step 16: Terraform apply（Keycloak）

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

### Step 17: Keycloak Docker イメージ ビルド＆デプロイ

```bash
# Docker Desktop が起動していることを確認
cd keycloak
bash deploy.sh
```

ECSタスク起動まで2-3分待つ。以下で状態確認：
```bash
aws ecs describe-services --cluster auth-poc-kc-cluster --service auth-poc-kc-service --query 'services[0].{running: runningCount}' --output json
```

### Step 18: Keycloak DB の SSL設定修正

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

### Step 19: Keycloak Admin Console ログイン確認

```
URL: http://<ALB DNS>/admin/master/console/
User: admin
Password: terraform.tfvars の keycloak_admin_password
```

ALB DNSは `terraform output keycloak_url` で確認。

### Step 20: Keycloak Realm 設定

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

### Step 21: Keycloak MFA 設定（Phase 7）

1. Authentication → Required Actions → `Configure OTP` を Default Action に
2. Users → test@example.com → Required Actions → `Configure OTP` 追加
3. SPAからログイン → TOTP登録

### Step 22: Auth0 Identity Brokering 設定（Phase 7）

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

### Step 23: フェデレーションユーザーのMFAスキップ設定

Auth0経由ユーザーに二重MFAを回避させるため：
1. Users → Auth0経由ユーザー → Credentials → OTPエントリを Delete
2. Required Actions → `Configure OTP` を削除

### Step 24: Keycloak SPA 設定

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

### Step 25: SSO検証用 Client 2（任意）

```bash
# Admin Console で auth-poc-spa-2 を作成（redirect: localhost:5175）
cd app-keycloak-2
cp .env.example .env
# VITE_KEYCLOAK_CLIENT_ID=auth-poc-spa-2, ポート5175

npm install
npm run dev
```

### Keycloak コスト管理

```bash
# 停止（ECS + RDS → ALBの$0.80/日のみ）
bash keycloak/stop.sh

# 起動
bash keycloak/start.sh

# 完全削除
cd infra/keycloak && terraform destroy
```

### Keycloak トラブルシューティング

| 症状 | 原因 | 対策 |
|------|------|------|
| `HTTPS required` | DB内sslRequired=EXTERNAL | `start-dev` モード or DB直接更新 |
| 502/503 頻発 | CPU 100%スパイク（start-dev起因） | 2 vCPU / 4 GB に増強。本番では start --optimized |
| ECSタスク起動しない | RDS停止中 | `aws rds start-db-instance` → 5-10分待つ |
| Admin Console セッション切れ | セッションCookie期限切れ | `/admin/master/console/` に直接アクセス |
| Auth0ボタンが表示されない | IdP設定の Enabled が OFF | Admin Console → Identity Providers → auth0 → Enabled ON |
| First Broker Login でemail空 | Default Scopes に `profile email` がない | IdP設定で Scopes 追加 |

---

## 環境削除

### 削除手順（依存関係順）

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
