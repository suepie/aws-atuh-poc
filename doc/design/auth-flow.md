# 認証フロー設計（PoC実装済み）

**最終更新**: 2026-03-17（Phase 4 完了時点）
**ベースドキュメント**: `doc/old/authentication-authorization-detail.md`

---

## 1. 認証パターン一覧

本PoCでは3種類の認証パターンを実装・検証済み。

| パターン | 経路 | issuerType | 用途（本番想定） |
|---------|------|------------|--------------|
| A. Hosted UI ログイン | SPA → 集約Cognito Hosted UI → SPA | central | 管理者・テストユーザー |
| B. フェデレーション（Auth0） | SPA → 集約Cognito → Auth0 → 集約Cognito → SPA | central | 顧客企業ユーザー（Entra ID/Okta） |
| C. ローカルCognito | SPA → ローカルCognito Hosted UI → SPA | local | パートナー企業ユーザー |

---

## 2. パターンA: Hosted UI ログイン（集約Cognito ローカルユーザー）

```mermaid
sequenceDiagram
    autonumber
    participant User as 👤 ユーザー
    participant SPA as 📱 React SPA
    participant Cognito as 🔴 集約 Cognito<br/>（User Pool A）

    User->>SPA: 「ログイン（Hosted UI）」クリック
    SPA->>Cognito: /oauth2/authorize<br/>response_type=code<br/>code_challenge=xxx (PKCE)
    Cognito->>User: Hosted UI 表示
    User->>Cognito: email + パスワード入力
    Cognito->>SPA: redirect_uri?code=xxx&state=xxx
    SPA->>Cognito: POST /oauth2/token<br/>code + code_verifier (PKCE)
    Cognito->>SPA: ID Token + Access Token + Refresh Token

    Note over SPA: トークンをsessionStorageに保存<br/>UserLoadedイベント発火<br/>認証済みUIに切替
```

**ポイント**:
- Authorization Code Flow + PKCE
- Client Secretなし（SPA用App Client）
- oidc-client-ts が PKCE を自動処理

---

## 3. パターンB: フェデレーション認証（Auth0 = 外部IdP）

```mermaid
sequenceDiagram
    autonumber
    participant User as 👤 ユーザー
    participant SPA as 📱 React SPA
    participant Cognito as 🔴 集約 Cognito<br/>（User Pool A）
    participant Auth0 as 🔵 Auth0 Free<br/>（外部IdP）

    User->>SPA: 「ログイン（Auth0）」クリック
    SPA->>Cognito: /oauth2/authorize<br/>identity_provider=Auth0<br/>code_challenge=xxx (PKCE)

    Note over Cognito: Hosted UI スキップ<br/>identity_provider指定により<br/>直接Auth0にリダイレクト

    Cognito->>Auth0: OIDC認証リクエスト<br/>/authorize
    Auth0->>User: Auth0 ログイン画面
    User->>Auth0: email + パスワード

    Auth0->>Cognito: authorization_code
    Cognito->>Auth0: POST /oauth2/token<br/>code交換
    Auth0->>Cognito: Auth0 ID Token + ユーザー属性

    Note over Cognito: JIT プロビジョニング<br/>初回: ユーザー自動作成<br/>2回目以降: 属性更新<br/>属性マッピング適用

    Cognito->>SPA: redirect_uri?code=xxx
    SPA->>Cognito: POST /oauth2/token<br/>code + code_verifier (PKCE)
    Cognito->>SPA: Cognito JWT<br/>（identitiesクレーム含む）

    Note over SPA: JWT発行元は Cognito<br/>Auth0のトークンではない
```

**ポイント**:
- `identity_provider=Auth0` パラメータでHosted UIをスキップ
- CognitoとAuth0間でOIDC Authorization Code Flowが実行される
- Cognitoが**自身のJWT**を発行（Auth0のトークンではない）
- `identities`クレームにフェデレーション元の情報が含まれる
- JITプロビジョニング: 初回ログイン時にCognito User Pool内にユーザーエントリが自動作成

---

## 4. パターンC: ローカルCognito ログイン

```mermaid
sequenceDiagram
    autonumber
    participant User as 👤 ユーザー
    participant SPA as 📱 React SPA
    participant LocalCognito as 🟢 ローカル Cognito<br/>（User Pool B）

    User->>SPA: 「ログイン（ローカルCognito）」クリック
    SPA->>LocalCognito: /oauth2/authorize<br/>response_type=code<br/>code_challenge=xxx (PKCE)
    LocalCognito->>User: Hosted UI 表示
    User->>LocalCognito: email + パスワード入力
    LocalCognito->>SPA: redirect_uri?code=xxx
    SPA->>LocalCognito: POST /oauth2/token<br/>code + code_verifier
    LocalCognito->>SPA: ID Token + Access Token + Refresh Token

    Note over SPA: issuer が集約Cognitoと異なる<br/>Lambda Authorizerが<br/>issuerで判別する
```

**ポイント**:
- フローはパターンAと同じだが、**issuer（User Pool ID）が異なる**
- Lambda Authorizerが issuer で集約/ローカルを判別

---

## 5. API 認可フロー（全パターン共通）

```mermaid
sequenceDiagram
    autonumber
    participant SPA as 📱 React SPA
    participant APIGW as 🟣 API Gateway
    participant Cache as 💾 Authorizer Cache<br/>（TTL 300秒）
    participant Lambda as 🟠 Lambda Authorizer
    participant JWKS as 🔑 JWKS Endpoint<br/>（Cognito）
    participant Backend as 🟢 Backend Lambda

    SPA->>APIGW: GET /v1/test<br/>Authorization: Bearer {JWT}
    APIGW->>Cache: キャッシュ確認

    alt キャッシュヒット
        Cache->>APIGW: キャッシュされた Policy
    else キャッシュミス
        APIGW->>Lambda: authorizationToken + methodArn

        Note over Lambda: ① Bearer プレフィックス除去
        Note over Lambda: ② JWT デコード（署名検証なし）<br/>issuer (iss) + kid 取得

        Lambda->>Lambda: ③ issuer 判定<br/>集約Cognito? ローカルCognito? 不明?

        alt issuer = 集約 Cognito
            Lambda->>JWKS: JWKS取得（集約）
        else issuer = ローカル Cognito
            Lambda->>JWKS: JWKS取得（ローカル）
        else issuer = 不明
            Lambda->>APIGW: Unauthorized 例外
        end

        JWKS->>Lambda: 公開鍵一覧

        Note over Lambda: ④ kid一致する公開鍵で署名検証
        Note over Lambda: ⑤ クレーム検証（iss, client_id, exp）
        Note over Lambda: ⑥ ユーザー情報抽出<br/>sub, email, groups, idpName
        Note over Lambda: ⑦ IAM Policy生成（Allow）<br/>+ Context情報

        Lambda->>APIGW: Policy + Context
        APIGW->>Cache: キャッシュに保存
    end

    alt Effect = Allow
        APIGW->>Backend: リクエスト転送<br/>+ requestContext.authorizer
        Note over Backend: Context からユーザー情報取得<br/>userId, email, groups,<br/>issuerType, idpName
        Backend->>SPA: 200 OK + レスポンス
    else Effect = Deny
        APIGW->>SPA: 403 Forbidden
    end
```

**ポイント**:
- Lambda Authorizerは**ALLOWED_ISSUERS辞書**でissuerを判定
- Cognitoアクセストークンは`aud`ではなく`client_id`クレームを使用（PyJWTの`verify_aud`をオフにして手動検証）
- JWKSはキャッシュ付き（TTL 1時間、Lambda内メモリ）
- API Gatewayもキャッシュ（TTL 5分、トークン値がキー）

---

## 6. Lambda Authorizer マルチissuer判定

```mermaid
flowchart TB
    JWT["JWT トークン"] --> Decode["デコード（署名検証なし）"]
    Decode --> ExtractIss["issuer (iss) 抽出"]

    ExtractIss --> Check{issuer の判定<br/>ALLOWED_ISSUERS 辞書}

    Check -->|"iss = 集約Cognito issuer"| Central["集約 Cognito パス"]
    Check -->|"iss = ローカルCognito issuer"| Local["ローカル Cognito パス"]
    Check -->|"iss = 不明"| Deny["❌ Unauthorized"]

    subgraph CentralFlow["集約 Cognito 検証"]
        Central --> CentralJWKS["JWKS取得\n集約Cognito endpoint"]
        CentralJWKS --> CentralVerify["署名検証 + クレーム検証\nclient_id = 集約App Client ID"]
    end

    subgraph LocalFlow["ローカル Cognito 検証"]
        Local --> LocalJWKS["JWKS取得\nローカルCognito endpoint"]
        LocalJWKS --> LocalVerify["署名検証 + クレーム検証\nclient_id = ローカルApp Client ID"]
    end

    CentralVerify --> Context["Context生成\nissuerType: central"]
    LocalVerify --> Context2["Context生成\nissuerType: local"]

    Context --> Policy["IAM Policy + Context 返却"]
    Context2 --> Policy

    style CentralFlow fill:#fff0f0,stroke:#cc0000
    style LocalFlow fill:#f0fff0,stroke:#006600
```

---

## 7. ログアウトフロー

### 7.1 通常ログアウト（Cognitoセッションのみ破棄）

```mermaid
sequenceDiagram
    participant SPA as 📱 React SPA
    participant Cognito as 🔴/🟢 Cognito

    SPA->>SPA: issuer判定<br/>（集約 or ローカル）
    SPA->>Cognito: /logout?client_id=xxx&logout_uri=xxx
    Cognito->>SPA: リダイレクト（logout_uri）

    Note over SPA: Cognitoセッション破棄<br/>Auth0セッションは残る（SSO動作）<br/>→ 再ログイン時パスワード不要
```

### 7.2 完全ログアウト（SSO破棄）

```mermaid
sequenceDiagram
    participant SPA as 📱 React SPA
    participant Auth0 as 🔵 Auth0
    participant Cognito as 🔴 集約 Cognito

    SPA->>SPA: sessionStorage クリア
    SPA->>Auth0: /v2/logout?returnTo=<Cognito logout URL>
    Auth0->>Auth0: Auth0セッション破棄
    Auth0->>Cognito: リダイレクト（/logout）
    Cognito->>Cognito: Cognitoセッション破棄
    Cognito->>SPA: リダイレクト（logout_uri）

    Note over SPA: 全セッション破棄完了<br/>→ 再ログイン時パスワード必要
```

---

## 8. 検証結果サマリー

### 確認済み項目

| 項目 | パターンA<br/>Hosted UI | パターンB<br/>Auth0連携 | パターンC<br/>ローカルCognito |
|------|:---:|:---:|:---:|
| ログイン | ✅ | ✅ | ✅ |
| JWT取得（3種） | ✅ | ✅ | ✅ |
| トークンデコード表示 | ✅ | ✅ | ✅ |
| identitiesクレーム | - | ✅ | - |
| JITプロビジョニング | - | ✅ | - |
| API呼び出し（トークンあり） | ✅ 200 | ✅ 200 | ✅ 200 |
| API呼び出し（トークンなし） | ✅ 401 | ✅ 401 | ✅ 401 |
| issuerType判定 | central | central | local |
| 通常ログアウト | ✅ | ✅（SSO残る） | ✅ |
| 完全ログアウト | ✅ | ✅（SSO破棄） | ✅ |

### 確認された技術的知見

| 知見 | 詳細 |
|------|------|
| Cognitoアクセストークンに`aud`がない | `client_id`クレームで代替。PyJWTの`verify_aud`をオフにして手動検証が必要 |
| JWKSは公開エンドポイント | クロスアカウントでもIAM設定不要。PoCと本番で動作差異なし |
| SSOセッションはIdP側に残る | Cognitoログアウトだけでは外部IdPのセッションは破棄されない。完全ログアウトには多段リダイレクトが必要 |
| Lambda依存ライブラリのビルド | macOSでビルドしたcryptographyはLambda(Linux)で動かない。`--platform manylinux2014_x86_64`が必要 |
| oidc-client-tsのUserManager共有 | CallbackPageで別インスタンスを作るとUserLoadedイベントが伝わらない。Contextで共有する必要がある |
