# 認証フロー設計

**最終更新**: 2026-03-17
**ベースドキュメント**: `doc/old/authentication-authorization-detail.md`

---

## Phase 1: 基本認証フロー（Hosted UI）

```mermaid
sequenceDiagram
    autonumber
    participant User as ユーザー
    participant SPA as React SPA
    participant Cognito as Cognito (User Pool A)<br/>集約Cognito役

    User->>SPA: ログインボタンクリック
    SPA->>Cognito: /oauth2/authorize?<br/>response_type=code&<br/>client_id=xxx&<br/>redirect_uri=http://localhost:5173/callback&<br/>scope=openid profile email&<br/>code_challenge=xxx (PKCE)
    Cognito->>User: Hosted UI 表示
    User->>Cognito: ID/PW 入力
    Cognito->>SPA: redirect_uri?code=xxx
    SPA->>Cognito: POST /oauth2/token<br/>(code + code_verifier)
    Cognito->>SPA: ID Token + Access Token + Refresh Token
    SPA->>SPA: トークンデコード・表示
```

**検証ポイント:**
- Authorization Code Flow + PKCE の完全な動作
- 3種類のトークンの取得と内容確認
- トークンの有効期限、リフレッシュ動作

---

## Phase 2: フェデレーション認証（Auth0 = 外部IdP）

```mermaid
sequenceDiagram
    autonumber
    participant User as ユーザー
    participant SPA as React SPA
    participant Cognito as Cognito (User Pool A)
    participant Auth0 as Auth0 Free<br/>(外部IdP役)

    User->>SPA: ログインボタンクリック
    SPA->>Cognito: /oauth2/authorize?<br/>identity_provider=Auth0
    Cognito->>Auth0: OIDC認証リクエスト
    User->>Auth0: ID/PW + MFA
    Auth0->>Cognito: authorization_code
    Cognito->>Auth0: POST /token (code交換)
    Auth0->>Cognito: ID Token + ユーザー属性

    Note over Cognito: JITプロビジョニング<br/>ユーザー作成/更新<br/>属性マッピング

    Cognito->>SPA: Cognito JWT<br/>(ID Token + Access Token + Refresh Token)
    SPA->>SPA: トークンデコード・表示<br/>identitiesクレーム確認
```

**検証ポイント:**
- CognitoとAuth0間のOIDCフェデレーション
- JITプロビジョニング（初回ログイン時のユーザー自動作成）
- 属性マッピング（Auth0の属性→Cognitoカスタム属性）
- `identities`クレームの内容確認

---

## Phase 3: 認可（Lambda Authorizer）

```mermaid
sequenceDiagram
    autonumber
    participant SPA as React SPA
    participant APIGW as API Gateway
    participant Lambda as Lambda Authorizer
    participant JWKS as JWKS エンドポイント<br/>(Cognito)
    participant Backend as Backend Lambda

    SPA->>APIGW: GET /v1/expenses<br/>Authorization: Bearer {JWT}
    APIGW->>Lambda: トークン検証リクエスト

    Note over Lambda: 1. JWTデコード（署名検証なし）<br/>2. issuer判定<br/>3. JWKS URL構築

    alt JWKSキャッシュあり
        Lambda->>Lambda: キャッシュから公開鍵取得
    else キャッシュなし
        Lambda->>JWKS: GET /.well-known/jwks.json
        JWKS->>Lambda: 公開鍵一覧
    end

    Note over Lambda: 4. 署名検証<br/>5. クレーム検証(exp, iss, aud)<br/>6. グループ抽出<br/>7. IAM Policy生成

    Lambda->>APIGW: IAM Policy + Context

    alt Allow
        APIGW->>Backend: リクエスト + requestContext.authorizer
        Note over Backend: tenantId, userId, groups<br/>でデータフィルタリング
        Backend->>SPA: レスポンス
    else Deny
        APIGW->>SPA: 403 Forbidden
    end
```

**検証ポイント:**
- Lambda AuthorizerのJWT検証全ステップ
- IAM Policy生成とAPI GatewayのPolicy評価
- Context伝播（authorizer→Backend）
- キャッシュ動作（TTL 300秒）

---

## Phase 4: ハイブリッド構成（マルチissuer）

```mermaid
sequenceDiagram
    autonumber
    participant SPA as React SPA
    participant Lambda as Lambda Authorizer

    Note over SPA,Lambda: パターンA: 集約Cognitoトークン
    SPA->>Lambda: Bearer {JWT from User Pool A}
    Note over Lambda: iss = User Pool A<br/>→ 集約Cognitoパス<br/>→ JWKS A で検証

    Note over SPA,Lambda: パターンB: ローカルCognitoトークン
    SPA->>Lambda: Bearer {JWT from User Pool B}
    Note over Lambda: iss = User Pool B<br/>→ ローカルCognitoパス<br/>→ JWKS B で検証

    Note over SPA,Lambda: パターンC: 不明なissuer
    SPA->>Lambda: Bearer {JWT from unknown}
    Note over Lambda: iss = 不明<br/>→ 401 Unauthorized
```

**検証ポイント:**
- マルチissuer対応の動作確認
- issuer判定ロジック（ALLOWED_ISSUERS）
- 集約/ローカルで異なるクレーム内容の確認

---

## 詳細リファレンス

認証フローの網羅的な詳細は `doc/old/authentication-authorization-detail.md` を参照。
本ドキュメントはPoC実装に必要な部分を抽出・整理したもの。
