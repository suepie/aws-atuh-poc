# Auth0 Free を外部IdP（Entra ID代替）として使う

**作成日**: 2026-03-17

---

## 目的

Entra IDが利用できないため、Auth0 Freeを外部IdPとしてCognitoにOIDC連携する。
これにより本番想定の「Cognito ↔ 外部IdP」フェデレーション認証フローを検証する。

## Auth0 Free の制限

| 項目 | 制限 |
|------|------|
| MAU | 25,000（PoCには十分） |
| Social Connections | 2つまで |
| Organizations | 5つまで |
| カスタムドメイン | 不可 |
| MFA | 対応 |

## セットアップ手順

### Step 1: Auth0 アカウント作成

1. https://auth0.com にアクセス
2. 「Sign Up」からFreeプランでアカウント作成
3. テナント作成（例: `auth-poc`）

### Step 2: Auth0 で Application 作成

1. Auth0 Dashboard → Applications → Create Application
2. 名前: `cognito-federation`
3. タイプ: **Regular Web Application**（CognitoがバックチャネルでAuth0と通信するため）
4. Settings で以下を確認・設定:

| 設定項目 | 値 |
|---------|-----|
| Domain | `auth-poc.auth0.com`（自動生成） |
| Client ID | （自動生成、メモする） |
| Client Secret | （自動生成、メモする） |
| Allowed Callback URLs | `https://<cognito-domain>.auth.<region>.amazoncognito.com/oauth2/idpresponse` |

**Callback URL の形式:**
```
https://auth-poc-central.auth.ap-northeast-1.amazoncognito.com/oauth2/idpresponse
```
※ Cognito のドメイン名に合わせる

### Step 3: Auth0 でテストユーザー作成

1. User Management → Users → Create User
2. Email: `testuser@example.com`
3. Password: 任意
4. Connection: Username-Password-Authentication

### Step 4: Auth0 の OIDC エンドポイント確認

```
Issuer URL: https://auth-poc.auth0.com/
Discovery: https://auth-poc.auth0.com/.well-known/openid-configuration
```

### Step 5: Cognito に Auth0 を IdP として追加（Terraform）

`infra/cognito.tf` に IdP 設定を追加。詳細は Terraform ファイルを参照。

### Step 6: 動作確認

1. React SPA で「Auth0でログイン」ボタンをクリック
2. Cognito → Auth0 にリダイレクト
3. Auth0 でID/PW認証
4. Auth0 → Cognito にリダイレクト（authorization code）
5. Cognito がトークン交換 → JWT発行
6. SPA にトークンが返される

## CognitoのJWTに含まれるクレーム（フェデレーション時）

```json
{
  "sub": "cognito-user-id-xxx",
  "cognito:username": "Auth0_auth0|abc123",
  "email": "testuser@example.com",
  "identities": [
    {
      "userId": "auth0|abc123",
      "providerName": "Auth0",
      "providerType": "OIDC",
      "primary": true
    }
  ],
  "iss": "https://cognito-idp.ap-northeast-1.amazonaws.com/ap-northeast-1_XXX",
  "aud": "client-id-xxx"
}
```

## Entra ID との対応

| 観点 | Entra ID（本番） | Auth0 Free（PoC） |
|------|-----------------|-------------------|
| プロトコル | OIDC | OIDC |
| Cognito側の設定 | aws_cognito_identity_provider | 同じ |
| クレームマッピング | attribute_mapping | 同じ |
| JITプロビジョニング | あり | あり |
| identitiesクレーム | providerName: "EntraID-TenantA" | providerName: "Auth0" |
