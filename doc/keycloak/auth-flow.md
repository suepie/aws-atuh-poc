# Keycloak 認証フロー設計（Phase 6-7）

**最終更新**: 2026-03-30

---

## 1. ローカルユーザー（Authorization Code + PKCE + MFA）

```mermaid
sequenceDiagram
    participant User as ユーザー
    participant SPA as SPA (localhost:5174)
    participant KC as Keycloak (ECS)
    participant DB as PostgreSQL (RDS)

    User->>SPA: ログインボタン
    SPA->>KC: /realms/auth-poc/protocol/openid-connect/auth<br/>response_type=code, code_challenge(S256)
    KC->>User: ログイン画面
    User->>KC: ID + パスワード
    KC->>DB: credential テーブルで照合
    KC->>User: TOTP入力画面
    User->>KC: TOTPコード
    KC->>DB: SSOセッション作成（user_session テーブル）
    KC->>SPA: code + state
    SPA->>KC: code → token交換（/token endpoint）
    KC->>SPA: ID Token + Access Token + Refresh Token
    Note over SPA: realm_access.roles でロール確認
```

**Cognitoとの違い**:
- OIDC Discovery が完全動作（metadata手動指定不要）
- `aud` クレームがアクセストークンに含まれる（Cognitoにはない）
- ログアウトは `signoutRedirect()` のみで完結（多段リダイレクト不要）
- MFAはKeycloakの認証フローで制御（Conditional OTP）

## 2. Auth0 Identity Brokering

```mermaid
sequenceDiagram
    participant User as ユーザー
    participant SPA as SPA
    participant KC as Keycloak
    participant Auth0 as Auth0
    participant DB as PostgreSQL

    User->>SPA: ログインボタン
    SPA->>KC: /authorize
    KC->>User: ログイン画面<br/>「Login with Auth0」ボタン表示
    User->>KC: Auth0ボタンクリック
    KC->>Auth0: OIDC /authorize
    Auth0->>User: Auth0ログイン画面 + MFA（Auth0側）
    User->>Auth0: 認証成功
    Auth0->>KC: code
    KC->>Auth0: code → token交換
    Auth0->>KC: Auth0 JWT（ユーザー情報）

    Note over KC,DB: 初回: JITプロビジョニング
    KC->>DB: user_entity 作成
    KC->>DB: federated_identity 作成（Auth0ユーザーID紐付け）

    KC->>DB: SSOセッション作成
    KC->>SPA: Keycloakトークン発行（issuer=Keycloak）
    Note over SPA: MFAはAuth0側で完了<br/>KeycloakのMFAはスキップ（Conditional OTP）
```

**Cognito + Auth0との違い**:
- Keycloakログイン画面にIdPボタンが**自動表示**される（SPA側の変更不要）
- Cognito: `identity_provider` パラメータを明示的に渡す必要があった
- トークン発行元はどちらもローカル（Cognito/Keycloak）で、Auth0ではない

## 3. SSO（同一Realm内 複数Client）

```mermaid
sequenceDiagram
    participant User as ユーザー
    participant A as Client A (5174)
    participant KC as Keycloak
    participant B as Client B (5175)

    User->>A: ログインボタン
    A->>KC: /authorize (client_id=auth-poc-spa)
    KC->>User: ログイン画面（PW + TOTP）
    User->>KC: 認証成功
    Note over KC: SSOセッション作成<br/>+ KEYCLOAK_SESSION Cookie
    KC->>A: トークン（Client A用）

    Note over User,B: 別のアプリにアクセス

    User->>B: ログインボタン
    B->>KC: /authorize (client_id=auth-poc-spa-2)
    Note over KC: KEYCLOAK_SESSION Cookie確認<br/>→ SSOセッション有効<br/>★ PW/MFA不要、外部通信なし
    KC->>B: トークン（Client B用、即座）
```

**Cognito + Auth0 SSOとの違い**:
- Cognito: SSOはAuth0セッション経由（Auth0にリダイレクトが走る）
- Keycloak: **Realm内で完結**（外部通信なし、高速）
- Keycloak: **Back-Channel Logout対応**（Client Aログアウト → Client Bも無効化）
