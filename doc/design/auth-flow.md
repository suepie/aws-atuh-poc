# 認証フロー設計（PoC実装済み）

**最終更新**: 2026-03-18（Phase 5 完了時点）
**ベースドキュメント**: `doc/old/authentication-authorization-detail.md`

---

## 1. 認証パターン一覧

本PoCでは5種類の認証パターンを実装・検証済み。

| # | パターン | Cognito | 経路 | issuerType |
|---|---------|---------|------|------------|
| A | Hosted UI ログイン | 集約（東京） | SPA → 東京Hosted UI → SPA | central |
| B | Auth0 フェデレーション | 集約（東京） | SPA → 東京 → Auth0 → 東京 → SPA | central |
| C | ローカルCognito | ローカル（東京） | SPA → ローカルHosted UI → SPA | local |
| D | DR Hosted UI | DR（大阪） | SPA → 大阪Hosted UI → SPA | dr |
| E | DR Auth0 フェデレーション | DR（大阪） | SPA → 大阪 → Auth0 → 大阪 → SPA | dr |

---

## 2. パターンB: フェデレーション認証（Auth0 経由）

最も複雑で重要なフロー。本番の「Cognito ↔ Entra ID」に相当。

```mermaid
sequenceDiagram
    autonumber
    participant User as 👤 ユーザー
    participant SPA as 📱 React SPA
    participant Cognito as 🔴 集約 Cognito<br/>（東京 User Pool A）
    participant Auth0 as 🔵 Auth0<br/>（外部IdP）

    User->>SPA: 「ログイン（Auth0）」クリック
    SPA->>Cognito: /oauth2/authorize<br/>identity_provider=Auth0<br/>code_challenge=xxx (PKCE)

    Note over Cognito: Hosted UI スキップ<br/>identity_provider指定で<br/>直接Auth0にリダイレクト

    Cognito->>Auth0: OIDC認証リクエスト
    Auth0->>User: Auth0 ログイン画面
    User->>Auth0: email + パスワード
    Auth0->>Cognito: authorization_code
    Cognito->>Auth0: POST /oauth/token（code交換）
    Auth0->>Cognito: Auth0 ID Token + ユーザー属性

    Note over Cognito: JIT プロビジョニング<br/>初回: ユーザー自動作成<br/>2回目以降: 属性更新

    Cognito->>SPA: redirect_uri?code=xxx
    SPA->>Cognito: POST /oauth2/token<br/>code + code_verifier (PKCE)
    Cognito->>SPA: Cognito JWT<br/>（identitiesクレーム含む）
```

---

## 3. API 認可フロー（全パターン共通）

```mermaid
sequenceDiagram
    autonumber
    participant SPA as 📱 React SPA
    participant APIGW as 🟣 API Gateway
    participant Cache as 💾 Authorizer Cache<br/>（TTL 300秒）
    participant Lambda as 🟠 Lambda Authorizer
    participant JWKS as 🔑 JWKS Endpoint
    participant Backend as 🟢 Backend Lambda

    SPA->>APIGW: GET /v1/test<br/>Authorization: Bearer {JWT}
    APIGW->>Cache: キャッシュ確認

    alt キャッシュヒット
        Cache->>APIGW: キャッシュされた Policy
    else キャッシュミス
        APIGW->>Lambda: authorizationToken + methodArn

        Note over Lambda: ① JWTデコード → issuer取得

        Lambda->>Lambda: ② issuer判定<br/>ALLOWED_ISSUERS辞書

        alt central (東京集約)
            Lambda->>JWKS: JWKS取得（東京）
        else local (ローカル)
            Lambda->>JWKS: JWKS取得（ローカル）
        else dr (大阪DR)
            Lambda->>JWKS: JWKS取得（大阪）
        else 不明
            Lambda->>APIGW: Unauthorized
        end

        JWKS->>Lambda: 公開鍵
        Note over Lambda: ③ 署名検証<br/>④ client_id検証<br/>⑤ Context生成

        Lambda->>APIGW: IAM Policy + Context
        APIGW->>Cache: キャッシュ保存
    end

    alt Allow
        APIGW->>Backend: リクエスト + authorizer Context
        Backend->>SPA: 200 OK
    else Deny
        APIGW->>SPA: 403 Forbidden
    end
```

---

## 4. Lambda Authorizer マルチissuer判定

```mermaid
flowchart TB
    JWT["JWT トークン"] --> Decode["デコード（署名検証なし）"]
    Decode --> ExtractIss["issuer (iss) 抽出"]
    ExtractIss --> Check{ALLOWED_ISSUERS 辞書}

    Check -->|"東京集約 Cognito"| Central["type: central\nclient_id: 東京App Client"]
    Check -->|"ローカル Cognito"| Local["type: local\nclient_id: ローカルApp Client"]
    Check -->|"大阪DR Cognito"| DR["type: dr\nclient_id: 大阪App Client"]
    Check -->|"不明"| Deny["❌ Unauthorized"]

    Central --> Verify["JWKS取得 → 署名検証 → client_id検証"]
    Local --> Verify
    DR --> Verify
    Verify --> Policy["IAM Policy + Context 返却"]

    style Central fill:#fff0f0,stroke:#cc0000
    style Local fill:#f0fff0,stroke:#006600
    style DR fill:#f5f0ff,stroke:#6600cc
```

---

## 5. ログアウトフロー

### 5.1 ログアウト種別

| ボタン | 動作 | IdPセッション |
|--------|------|-------------|
| ログアウト | ログイン元Cognitoのセッション破棄 | 残る（SSO動作） |
| 完全ログアウト（SSO破棄） | Auth0 → Cognito の多段ログアウト | 破棄される |

### 5.2 ログアウト先の判定

```mermaid
flowchart TB
    Start["ログアウト開始"] --> GetType["JWTのissからユーザー種別判定"]
    GetType --> Type{getUserType()}

    Type -->|"central"| CentralLogout["集約Cognito /logout"]
    Type -->|"local"| LocalLogout["ローカルCognito /logout"]
    Type -->|"dr"| DRLogout["大阪DR Cognito /logout"]

    subgraph FullLogout["完全ログアウト（SSO破棄）の場合"]
        CentralLogout --> Auth0Central["Auth0 /v2/logout\n→ 集約Cognito /logout\n→ SPA"]
        DRLogout --> Auth0DR["Auth0 /v2/logout\n→ 大阪Cognito /logout\n→ SPA"]
    end

    LocalLogout --> SPALocal["→ SPA\n（Auth0セッションなし）"]
```

### 5.3 Auth0 Allowed Logout URLs 設定

完全ログアウトのreturnToに指定するURL。**URLエンコード済み**の完全一致で登録が必要：

```
https://auth-poc-central.auth.ap-northeast-1.amazoncognito.com/logout?client_id=<東京CLIENT_ID>&logout_uri=http%3A%2F%2Flocalhost%3A5173%2F
https://auth-poc-dr-osaka.auth.ap-northeast-3.amazoncognito.com/logout?client_id=<大阪CLIENT_ID>&logout_uri=http%3A%2F%2Flocalhost%3A5173%2F
```

---

## 6. DR フェイルオーバーの検証

### 6.1 フェイルオーバーシナリオ

```mermaid
sequenceDiagram
    participant User as 👤 ユーザー
    participant SPA as 📱 SPA
    participant Tokyo as 🔴 東京 Cognito
    participant Auth0 as 🔵 Auth0
    participant Osaka as 🟣 大阪 Cognito
    participant API as 🟣 API Gateway

    Note over User,API: 通常時: 東京で認証
    User->>SPA: Auth0でログイン
    SPA->>Tokyo: 東京 /oauth2/authorize
    Tokyo->>Auth0: OIDC
    Auth0->>Tokyo: 認証成功
    Tokyo->>SPA: 東京JWT (issuerType=central)
    SPA->>API: Bearer 東京JWT → 200 OK

    Note over User,API: 障害発生: 東京Cognito停止
    Note over Tokyo: ❌ 障害

    Note over User,API: フェイルオーバー: 大阪で認証
    User->>SPA: DR大阪+Auth0でログイン
    SPA->>Osaka: 大阪 /oauth2/authorize
    Osaka->>Auth0: OIDC
    Note over Auth0: SSOセッション有効<br/>→ パスワード不要
    Auth0->>Osaka: 認証成功
    Osaka->>SPA: 大阪JWT (issuerType=dr)
    SPA->>API: Bearer 大阪JWT → 200 OK

    Note over User,API: ポイント: Lambda Authorizerが<br/>東京・大阪両方のJWTを検証可能
```

### 6.2 DR検証での確認事項

| 項目 | 結果 |
|------|------|
| 大阪Cognito Hosted UIログイン | ✅ |
| 大阪Auth0フェデレーション | ✅（コンソール手動作成が必要） |
| 大阪JWTでAPI認可（issuerType=dr） | ✅ |
| Auth0 SSOでパスワード不要 | ✅（IdPセッション維持） |
| ログアウト（通常/完全） | ✅（getUserTypeで大阪判定） |

---

## 7. 技術的知見サマリー

| 知見 | 詳細 |
|------|------|
| Cognitoアクセストークンに`aud`がない | `client_id`クレームで代替検証 |
| JWKSは公開エンドポイント | クロスアカウント・クロスリージョンでもIAM不要 |
| SSOセッションはIdP側に残る | 完全ログアウトには多段リダイレクトが必要 |
| 大阪CognitoからAuth0の.well-known検出が失敗 | コンソール「Manual input」で回避（ADR-007） |
| マルチUserManagerのstateStore衝突 | プレフィックス分離が必須（oidc.central./oidc.local./oidc.dr.） |
| Auth0 Allowed Logout URLsはURLエンコード済み完全一致 | returnToパラメータと完全に一致する形で登録 |
