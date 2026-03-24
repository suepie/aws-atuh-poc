# 構築手順書

**最終更新**: 2026-03-24（Phase 5 完了時点）

---

## 前提条件

| ツール | バージョン |
|--------|----------|
| Node.js | 18以上 |
| Python | 3.10以上（venv用） |
| Terraform | 1.5以上 |
| AWS CLI | 2.x（認証済み） |
| Auth0 | Freeアカウント |

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

## 環境削除

```bash
# 大阪
cd infra/dr-osaka && terraform destroy

# 東京
cd infra && terraform destroy
```
