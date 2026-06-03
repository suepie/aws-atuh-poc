# OAuth 2.0 Token Exchange — 技術仕様と設計パターン

> **位置付け**: RFC 8693 OAuth 2.0 Token Exchange の **詳細技術仕様 + 7 設計パターン + 実装例 + 製品対応 + セキュリティ考慮** を一元化した技術メモ。
> **対象読者**: 認証基盤設計者 / アプリ実装者 / セキュリティレビュー担当者
> **関連**:
> - [auth-patterns.md §2.5 Token Exchange / OBO](auth-patterns.md#25-token-exchange--obo--rfc-8693) — 概要
> - [§C-1.2.C / K1 (Cognito Knockout)](../requirements/proposal/common/01-architecture.md) — 集約判定での扱い
> - [hearing-checklist.md §3.2 K1 列](../requirements/hearing-checklist.md) — ヒアリング項目 B-104 / B-304

---

## 目次

1. [RFC 8693 仕様の全体像](#1-rfc-8693-仕様の全体像)
2. [リクエスト / レスポンス仕様](#2-リクエスト--レスポンス仕様)
3. [7 つの設計パターン](#3-7-つの設計パターン)
4. [Delegation vs Impersonation — `act` claim](#4-delegation-vs-impersonation--act-claim)
5. [実装例](#5-実装例)
6. [製品別対応状況と設定](#6-製品別対応状況と設定)
7. [セキュリティ考慮 + アンチパターン](#7-セキュリティ考慮--アンチパターン)
8. [本プロジェクトでの設計判断](#8-本プロジェクトでの設計判断)
9. [リファレンス](#9-リファレンス)

---

## 1. RFC 8693 仕様の全体像

### 1.1 位置付け

OAuth 2.0 (RFC 6749) を拡張する **Token Endpoint の新しい grant_type 仕様**。2020 年 1 月に IETF 標準化 (Proposed Standard)。

```
grant_type=urn:ietf:params:oauth:grant-type:token-exchange
```

### 1.2 基本概念

「**既存トークン (subject_token) を、別のトークンと交換する**」 — その「別のトークン」が:
- **別の Audience** 向け (downstream service へ)
- **別の Scope** (権限縮小)
- **別の Type** (SAML → JWT 等)
- **別の Subject** (Impersonation)
- **別の Subject + 代理者記録** (Delegation, `act` claim)

であるかは、リクエストパラメータと交換ポリシーで決まる。

### 1.3 関与する主要アクター

```mermaid
flowchart LR
    Client[Client<br/>= 要求者]
    STS["Security Token Service<br/>= 認証基盤<br/>(/token endpoint)"]
    Subject[Subject<br/>= 元 Token の主体]
    Actor[Actor<br/>= 代理して動く者<br/>(Delegation 時)]
    Resource[Resource Server<br/>= 新 Token の audience]

    Client -->|Token A + 任意で Actor Token| STS
    STS -->|Token B 発行| Client
    Client -->|Token B| Resource

    Subject -.元 Token の sub.-> STS
    Actor -.act claim に記録.-> STS

    style STS fill:#e8f5e9,stroke:#2e7d32,stroke-width:3px
```

| アクター | 役割 |
|---|---|
| **Client** | Token Exchange を **要求する側**（API Gateway / Service A / Mobile App 等）|
| **STS (Security Token Service)** | 認証基盤の `/token` エンドポイント、新トークン発行 |
| **Subject** | 元 Token (`subject_token`) の主体 (`sub` claim) |
| **Actor** | Delegation 時、代理して動く者 (`actor_token` で証明)|
| **Resource Server** | 新 Token を受け取る側（API、別サービス）|

---

## 2. リクエスト / レスポンス仕様

### 2.1 リクエスト（RFC 8693 §2.1）

`POST /token` で `application/x-www-form-urlencoded`:

| パラメータ | 必須 | 内容 |
|---|:-:|---|
| `grant_type` | ✅ | `urn:ietf:params:oauth:grant-type:token-exchange` |
| `subject_token` | ✅ | **交換対象トークン**（誰のための交換か）|
| `subject_token_type` | ✅ | subject_token のタイプ URI（下表）|
| `actor_token` | △ | **代理者トークン**（Delegation 用）|
| `actor_token_type` | △ | actor_token のタイプ URI |
| `requested_token_type` | - | 欲しいトークンタイプ（省略時は実装依存）|
| `audience` | - | 新トークンの送り先（複数可）|
| `resource` | - | 新トークンの対象リソース URL（複数可）|
| `scope` | - | 新トークンに含めたい scope（縮小可、拡張不可）|
| **クライアント認証** | ✅ | Basic / `client_id`+`client_secret` / mTLS / Private Key JWT 等 |

### 2.2 トークンタイプ URI（IANA 登録）

| URI | 意味 |
|---|---|
| `urn:ietf:params:oauth:token-type:access_token` | OAuth 2.0 Access Token |
| `urn:ietf:params:oauth:token-type:refresh_token` | OAuth 2.0 Refresh Token |
| `urn:ietf:params:oauth:token-type:id_token` | OIDC ID Token |
| `urn:ietf:params:oauth:token-type:jwt` | 汎用 JWT (RFC 7519) |
| `urn:ietf:params:oauth:token-type:saml1` | SAML 1.1 Assertion |
| `urn:ietf:params:oauth:token-type:saml2` | SAML 2.0 Assertion |

### 2.3 リクエスト例 (HTTP)

```http
POST /realms/myrealm/protocol/openid-connect/token HTTP/1.1
Host: auth.example.com
Content-Type: application/x-www-form-urlencoded
Authorization: Basic c2VydmljZS1hOnNlY3JldA==

grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Atoken-exchange
&subject_token=eyJhbGciOiJSUzI1NiIs...
&subject_token_type=urn%3Aietf%3Aparams%3Aoauth%3Atoken-type%3Aaccess_token
&requested_token_type=urn%3Aietf%3Aparams%3Aoauth%3Atoken-type%3Ajwt
&audience=service-b
&scope=read
```

### 2.4 レスポンス（RFC 8693 §2.2）

成功時 `200 OK`、`application/json`:

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIs...",
  "issued_token_type": "urn:ietf:params:oauth:token-type:access_token",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "read",
  "refresh_token": "8xLOxBtZp8..."
}
```

| フィールド | 内容 |
|---|---|
| `access_token` | **新発行トークン**（フィールド名は token_type 関係なく "access_token"）|
| `issued_token_type` | 発行されたトークンのタイプ URI |
| `token_type` | `Bearer` / `N_A`（mutual TLS 等）|
| `expires_in` | 有効期限（秒）|
| `scope` | 実際に付与された scope |
| `refresh_token` | 任意、refresh 不可な場合は含めない |

### 2.5 エラーレスポンス

OAuth 2.0 標準（RFC 6749 §5.2）に準拠:

```json
{
  "error": "invalid_request",
  "error_description": "audience is required"
}
```

主要エラー:
- `invalid_request` — パラメータ不足/不正
- `invalid_client` — クライアント認証失敗
- `invalid_grant` — subject_token / actor_token が無効
- `unauthorized_client` — クライアントに交換権限なし
- `invalid_target` — 指定 audience/resource が無効

---

## 3. 7 つの設計パターン

RFC 8693 自体は仕組み（仕様）。その**使い方**には複数の設計パターンが存在する:

### Pattern 1: **トークンタイプ変換** (Token Type Translation)

**用途**: 既存のレガシー Token（SAML / Opaque）を JWT に変換、または逆。

```mermaid
sequenceDiagram
    autonumber
    participant Legacy as レガシー SP<br/>(SAML Assertion 受信)
    participant STS as 共通基盤<br/>(STS)
    participant Modern as モダン API<br/>(JWT 想定)

    Legacy->>STS: subject_token=SAML Assertion<br/>subject_token_type=...token-type:saml2<br/>requested_token_type=...token-type:jwt<br/>audience=modern-api
    STS-->>Legacy: access_token=JWT
    Legacy->>Modern: Authorization: Bearer JWT
```

**典型シナリオ**: SAML 連携の社内システムから、JWT ベースのモダン API へのアクセス橋渡し。

---

### Pattern 2: **Audience 縮小 / Downstream Token**

**用途**: マイクロサービス間で「特定サービスにしか使えない」Token に絞る（**最小権限**）。

```mermaid
sequenceDiagram
    autonumber
    participant User as User
    participant API as API Gateway
    participant STS as STS
    participant ServiceA as Service A
    participant ServiceB as Service B

    User->>API: Bearer T1<br/>(aud=api-gateway, scope=full)
    API->>STS: subject_token=T1<br/>audience=service-a<br/>scope=read
    STS-->>API: T2 (aud=service-a, scope=read)
    API->>ServiceA: Bearer T2
    Note over ServiceA: T2 は Service A 専用<br/>盗まれても他サービスには使えない
    ServiceA->>STS: subject_token=T2<br/>audience=service-b<br/>scope=read
    STS-->>ServiceA: T3 (aud=service-b)
    ServiceA->>ServiceB: Bearer T3
```

**メリット**: **Token 盗難時の被害最小化**（盗まれた Token は当該サービスにしか使えない）。

---

### Pattern 3: **Scope 縮小 / Refresh Token Exchange**

**用途**: 一時的に権限を絞った Token を取得（縮小は可、拡張は不可）。

```http
POST /token
grant_type=...:token-exchange
subject_token=<Access Token with scope: read write admin>
subject_token_type=...:access_token
scope=read    ← admin / write を削った read のみの Token を要求
```

**典型シナリオ**: バッチ処理が「読み取りのみ」で動く時、フル権限 Token から「read のみ」Token を発行。

---

### Pattern 4: **Impersonation**（なりすまし）

**用途**: A が B として動く、新 Token は完全に **B のもの**（A の痕跡なし）。

```mermaid
sequenceDiagram
    autonumber
    participant Admin as 管理者 A
    participant STS as STS
    participant API as API

    Admin->>STS: subject_token=<B のトークン or B 特定情報><br/>requested_token_type=...:access_token
    Note over STS: A に「Impersonation 権限」があるか検証<br/>(限定的に許可)
    STS-->>Admin: B のトークン<br/>(sub=B, act 無し)
    Admin->>API: Bearer B のトークン
    Note over API: 「B 本人が操作した」とログに記録
```

**JWT ペイロード**:
```json
{
  "sub": "B",
  "aud": "...",
  "iss": "https://sts.example.com"
}
```

**⚠ アンチパターン傾向**: 監査追跡が困難（A の操作が B 名義で記録される）。**Delegation の方が業界推奨**。

---

### Pattern 5: **Delegation**（委譲）— `act` claim

**用途**: A が B のために動く、新 Token は **B のもの** だが **`act` claim で A も記録**。

```mermaid
sequenceDiagram
    autonumber
    participant Support as サポート担当 A
    participant STS as STS
    participant API as API
    participant Audit as 監査ログ

    Support->>STS: subject_token=B のトークン<br/>actor_token=A のトークン<br/>actor_token_type=...:access_token
    Note over STS: 1. A の actor_token 検証<br/>2. A に委譲権限あるか確認<br/>3. B のための Token + act claim 発行
    STS-->>Support: Token (sub=B, act={sub:A})
    Support->>API: Bearer Token
    API->>Audit: 操作実行<br/>sub=B (代理 by A)
```

**JWT ペイロード**:
```json
{
  "sub": "B",
  "aud": "...",
  "iss": "https://sts.example.com",
  "act": {
    "sub": "A",
    "iss": "https://sts.example.com"
  }
}
```

### `act` 連鎖（Multi-hop Delegation）

委譲は連鎖可能。古い `act` を入れ子に:
```json
{
  "sub": "B",
  "act": {
    "sub": "A2",
    "act": {
      "sub": "A1"
    }
  }
}
```
→ 「A1 が A2 に委譲、A2 が B のために動く」

**業界推奨**: 監査要件（SOC2/ISO27001/FISC）がある場合は **Delegation 一択**。

---

### Pattern 6: **クロスドメイン / クロステナント橋渡し**

**用途**: 外部 IdP の Token を自基盤の Token に変換（**Federation の代替・補完**）。

```mermaid
sequenceDiagram
    autonumber
    participant App as アプリ
    participant ExtIdP as 外部 IdP<br/>(顧客企業 A)
    participant Core as 共通認証基盤<br/>(STS)
    participant API as 自基盤の API

    App->>ExtIdP: ログイン
    ExtIdP-->>App: 外部 IdP Token T_ext
    App->>Core: subject_token=T_ext<br/>subject_token_type=...:access_token<br/>audience=internal-api
    Note over Core: 1. T_ext を IdP の JWKS で検証<br/>2. テナント解決 (iss → tenant_id)<br/>3. 属性マッピング<br/>4. 内部 Token T_int 発行
    Core-->>App: T_int (iss=core, aud=internal-api)
    App->>API: Bearer T_int
```

**Federation との違い**:
- Federation: ブラウザベース、ユーザー UI 介在
- Token Exchange: **サーバー間**、Token 持参型、UI 介在なし

→ **API-to-API のフェデレーション** に近い。

---

### Pattern 7: **ハイブリッド構成での橋渡し**（本プロジェクト文脈）

**用途**: コア認証基盤（集約）↔ エッジ自治アプリ（分散）間の Token 連携。

```mermaid
sequenceDiagram
    autonumber
    participant User as User
    participant Core as コア認証基盤<br/>(Keycloak)
    participant Edge as エッジ自治アプリ<br/>(独自 IdP 持ち)
    participant EdgeAPI as エッジ API

    User->>Core: ログイン
    Core-->>User: コア Token T_core

    User->>Edge: T_core 持参でアクセス
    Edge->>Core: subject_token=T_core<br/>audience=edge-api<br/>scope=read
    Note over Core: Edge アプリに対する<br/>Token 交換ポリシー判定
    Core-->>Edge: T_edge (aud=edge-api)
    Edge->>EdgeAPI: Bearer T_edge
```

**用途**: 「**基本は集約 (Core)、特定アプリはエッジ自治** だが SSO 体験を維持」。エッジは自分の IdP で Token を発行するのではなく、コアから受領した Token を **自分のドメインの Token に交換**して使う。

---

## 4. Delegation vs Impersonation — `act` claim

両者の根本的違いは「**A の存在が記録に残るか**」。

| 観点 | Impersonation | Delegation |
|---|---|---|
| **新 Token の `sub`** | B | B |
| **新 Token の `act`** | なし | `{ sub: A }` |
| **監査追跡** | ❌ A の関与不可視 | ✅ A が誰かを記録 |
| **業界推奨度** | × 限定的 | ◎ 標準 |
| **典型ユースケース** | 完全な権限委譲（テストアカウント等）| サポート代行、管理者代行、Multi-hop |
| **法的責任** | B が実行したことになる | A が B の代行で実行（責任分界明確）|

### `act` claim 構造（RFC 8693 §4.1）

```json
{
  "iss": "https://sts.example.com",
  "sub": "B",                          // 元の主体
  "aud": "https://api.example.com",
  "iat": 1700000000,
  "exp": 1700003600,
  "act": {                             // 代理者
    "sub": "A",
    "iss": "https://sts.example.com"   // A の発行元
  }
}
```

### 委譲が連鎖した場合

`A1 → A2 → B のために動く`:

```json
{
  "sub": "B",
  "act": {
    "sub": "A2",
    "act": {
      "sub": "A1"
    }
  }
}
```

→ **最も内側が最初の代理者、最も外側 (`sub`) が最終的に「ふりをしている」相手**。

### 監査ログでの書き方

```
2026-06-03T12:34:56Z
  event: tenant.user.delete
  acted_user: user-B (sub)
  actor_chain: [user-A2, user-A1]
  reason: "support_request_TKT-12345"
```

→ Delegation の `act` 連鎖を **そのまま監査ログに展開**できるのが標準的な実装。

---

## 5. 実装例

### 5.1 cURL

#### 基本パターン（Audience 縮小）

```bash
curl -X POST https://auth.example.com/realms/myrealm/protocol/openid-connect/token \
  -u "service-a:secret" \
  -d "grant_type=urn:ietf:params:oauth:grant-type:token-exchange" \
  -d "subject_token=${USER_TOKEN}" \
  -d "subject_token_type=urn:ietf:params:oauth:token-type:access_token" \
  -d "audience=service-b" \
  -d "scope=read"
```

#### Delegation パターン

```bash
curl -X POST https://auth.example.com/realms/myrealm/protocol/openid-connect/token \
  -u "support-portal:secret" \
  -d "grant_type=urn:ietf:params:oauth:grant-type:token-exchange" \
  -d "subject_token=${TARGET_USER_TOKEN}" \
  -d "subject_token_type=urn:ietf:params:oauth:token-type:access_token" \
  -d "actor_token=${SUPPORT_AGENT_TOKEN}" \
  -d "actor_token_type=urn:ietf:params:oauth:token-type:access_token" \
  -d "audience=customer-api"
```

### 5.2 Node.js (axios)

```javascript
import axios from "axios";
import qs from "querystring";

async function exchangeToken({
  userToken,
  audience,
  scope,
  actorToken = null
}) {
  const params = {
    grant_type: "urn:ietf:params:oauth:grant-type:token-exchange",
    subject_token: userToken,
    subject_token_type: "urn:ietf:params:oauth:token-type:access_token",
    audience,
    scope,
  };
  if (actorToken) {
    params.actor_token = actorToken;
    params.actor_token_type =
      "urn:ietf:params:oauth:token-type:access_token";
  }

  const response = await axios.post(
    `${IDP_URL}/protocol/openid-connect/token`,
    qs.stringify(params),
    {
      auth: {
        username: process.env.CLIENT_ID,
        password: process.env.CLIENT_SECRET,
      },
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    }
  );
  return response.data.access_token;
}
```

### 5.3 Python (requests)

```python
import requests
from requests.auth import HTTPBasicAuth

def exchange_token(user_token, audience, scope, actor_token=None):
    data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "subject_token": user_token,
        "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
        "audience": audience,
        "scope": scope,
    }
    if actor_token:
        data["actor_token"] = actor_token
        data["actor_token_type"] = "urn:ietf:params:oauth:token-type:access_token"

    r = requests.post(
        f"{IDP_URL}/protocol/openid-connect/token",
        data=data,
        auth=HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET),
    )
    r.raise_for_status()
    return r.json()["access_token"]
```

### 5.4 Java (Spring)

```java
public String exchangeToken(String userToken, String audience, String scope) {
    MultiValueMap<String, String> body = new LinkedMultiValueMap<>();
    body.add("grant_type", "urn:ietf:params:oauth:grant-type:token-exchange");
    body.add("subject_token", userToken);
    body.add("subject_token_type", "urn:ietf:params:oauth:token-type:access_token");
    body.add("audience", audience);
    body.add("scope", scope);

    HttpHeaders headers = new HttpHeaders();
    headers.setBasicAuth(clientId, clientSecret);
    headers.setContentType(MediaType.APPLICATION_FORM_URLENCODED);

    ResponseEntity<TokenResponse> response = restTemplate.postForEntity(
        tokenEndpoint,
        new HttpEntity<>(body, headers),
        TokenResponse.class
    );
    return response.getBody().getAccessToken();
}
```

---

## 6. 製品別対応状況と設定

### 6.1 対応一覧

| 製品 | RFC 8693 | Delegation (`act`) | Impersonation | クロスドメイン | コメント |
|---|:-:|:-:|:-:|:-:|---|
| **AWS Cognito** | ❌ | ❌ | ❌ | ❌ | **K1 ノックアウト**。Lambda + 独自 endpoint で代替自作 |
| **Keycloak (Standard)** | ✅ Token Exchange v1/v2 (24+ で GA) | ✅ | ✅ | ✅ External-to-Internal / Internal-to-Internal | **Preview Feature の有効化必要** (24 以前)|
| **RHBK** | ✅ | ✅ | ✅ | ✅ | Keycloak Standard と同等 |
| **Auth0** | ✅ Custom Token Exchange | ✅ | ✅ | ✅ | Action / Hooks 経由実装 |
| **Microsoft Entra ID** | ✅ On-Behalf-Of Flow | ✅ | ⚠ 制限あり | ✅ | RFC 8693 を踏襲した独自フロー名称 |
| **Okta** | ✅ | ✅ | ✅ | ✅ | OAuth 2.0 Token Exchange (CIC) |
| **Ping Identity** | ✅ | ✅ | ✅ | ✅ | PingFederate / PingOne |

### 6.2 Keycloak 設定例

#### 1. Token Exchange の有効化（24 以前は Preview）

```bash
# 起動時オプション
bin/kc.sh start --features=token-exchange
```

24 以降は標準機能だが、**Client ごとの設定で許可** が必要。

#### 2. クライアント設定（Admin Console）

**Realm Settings → Clients → service-a**:
- **Client Authentication**: ON（Confidential Client）
- **Capability config**:
  - Standard flow: OFF（不要）
  - Service accounts roles: ON
  - **OAuth 2.0 Token Exchange**: ON

#### 3. 交換ポリシー（誰が誰の Token を交換可能か）

**Permissions タブ** で:
- `token-exchange.users.permission`: 「service-a が user の Token を交換できる」
- `token-exchange.client-to-client.permission`: 「service-a が service-b に交換できる」

**Policy 例**: Client Policy で「service-a のみ」を許可。

#### 4. External IdP からの交換

External-to-Internal の場合、IdP の `Stored Tokens` を ON にし、`Exchange Tokens Permission` を設定。

### 6.3 Cognito での代替実装（K1 回避）

Cognito では RFC 8693 をサポートしていないため、**Lambda + API Gateway で独自エンドポイントを実装**:

```
POST /custom-token-exchange
  Headers: Authorization: Bearer <subject_token>
  Body: { audience: "...", scope: "..." }

→ Lambda:
  1. subject_token を Cognito JWKS で検証
  2. 交換ポリシー判定
  3. 新 JWT を独自署名鍵で発行（または Cognito のカスタム JWT 機能利用）
  4. 監査ログ出力
```

**問題点**:
- ❌ 標準仕様準拠ではないため、相互運用性なし
- ❌ Cognito の signing key とは別の鍵管理が必要
- ❌ Refresh Token Revocation との連動なし
- ❌ Delegation `act` claim を独自実装する必要

→ **マイクロサービス間ユーザー文脈伝播が必要なら Keycloak/RHBK 採用が無難**。

### 6.4 Microsoft Entra On-Behalf-Of (OBO) Flow

Microsoft の独自名称だが、内部的には RFC 8693 ベース:

```http
POST https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token
  grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer
  client_id={midtier-app-id}
  client_secret={...}
  assertion={user-token}
  scope=https://downstream-api/.default
  requested_token_use=on_behalf_of
```

※ `grant_type` が `jwt-bearer` で RFC 8693 そのものではないが、概念は同じ。

---

## 7. セキュリティ考慮 + アンチパターン

### 7.1 必須セキュリティ対策

| # | 対策 | 理由 |
|:-:|---|---|
| 1 | **Client 認証必須** | 誰でも交換できる状態は致命的 (mTLS / Private Key JWT 推奨)|
| 2 | **`audience` 必須化** | 「無制限 Token」発行を防ぐ |
| 3 | **scope 縮小のみ許可、拡張禁止** | 権限昇格防止 |
| 4 | **交換ポリシーの最小権限** | 「Client A は Client B にのみ交換可」等の細粒度制御 |
| 5 | **Delegation 優先、Impersonation 制限** | 監査追跡可能性 |
| 6 | **新 Token の TTL 短縮** | 交換 Token は通常より短命 (5-15min)|
| 7 | **`act` claim の連鎖検証** | 古い `act` を改ざんで上書きされないよう |
| 8 | **監査ログ完全記録** | who / what / why / when すべて |
| 9 | **Rate Limit** | Token 乱発防止 |
| 10 | **subject_token 失効伝播** | 元 Token Revoke 時に交換 Token も Revoke |

### 7.2 主要アンチパターン

#### ❌ A. 「全 Client から全 Subject の Token を Exchange 可能」設定

```
Risk: 任意の Client が任意ユーザーの Token を取得可能
Impact: 完全な権限昇格、データ漏洩
対策: 交換ポリシーで Client × Subject × Audience を限定
```

#### ❌ B. Impersonation を無制限に許可

```
Risk: 監査追跡不能、誰が誰のふりをしたか分からない
Impact: 内部不正の温床
対策: Impersonation は限定 (テストアカウント等)、業務には Delegation
```

#### ❌ C. 交換 Token に長い TTL

```
Risk: 漏洩時の影響時間長期化
Impact: 攻撃面の拡大
対策: 通常 Token より短い TTL (5-15min)、Refresh 不可
```

#### ❌ D. audience を指定しない交換

```
Risk: 任意のリソースサーバーで使える「マスター Token」を発行
Impact: 一つの Token 漏洩で全システム侵害
対策: audience 必須化、サービスごとに別 Token
```

#### ❌ E. Subject Token の Issuer 検証なし

```
Risk: 偽 IdP の Token を受け入れ、なりすまし
Impact: 認証突破
対策: subject_token の iss を Whitelist 化、JWKS で署名検証
```

#### ❌ F. 監査ログ欠落

```
Risk: 不正交換の検出・追跡不能
Impact: インシデント対応不能
対策: 全交換イベントを SIEM 連携、act 連鎖も記録
```

---

## 8. 本プロジェクトでの設計判断

### 8.1 §C-1.2.C / K1 における位置付け

Cognito Knockout 条件 **K1** として、Token Exchange は「**集約しない例外パターンで必要になる主要技術**」と整理されている。

| ヒアリング項目 | 内容 | K1 該当性 |
|---|---|:-:|
| **B-104** | コアの Token を別エッジへの利用許可 | ✅ K1 |
| **B-304** | 業務シナリオで認証情報を別システムへリレー (Delegation) | ✅ K1 |

### 8.2 採用シナリオ（本プロジェクト）

| シナリオ | 用途 | パターン |
|---|---|:-:|
| **シナリオ A**: ハイブリッド構成のエッジ橋渡し | コア Token → エッジ API Token | Pattern 7 |
| **シナリオ B**: マイクロサービス間 Audience 縮小 | API Gateway → Service A → Service B の段階的 Token | Pattern 2 |
| **シナリオ C**: 業務代行（サポートが顧客代行）| サポート担当 A が顧客 B として操作 | Pattern 5 Delegation |
| **シナリオ D**: バッチ処理の権限縮小 | フル権限ユーザー Token → 「読み取りのみ」Token | Pattern 3 |
| **シナリオ E**: SAML 連携の橋渡し | レガシー SAML SP → モダン JWT API | Pattern 1 |
| **シナリオ F**: 外部 IdP からの直接 API アクセス | 顧客 IdP Token → 自基盤 API Token | Pattern 6 |

### 8.3 製品選定への影響

```
Token Exchange 要件 (B-104 / B-304) 必要?
├─ Yes (1 つでも該当)
│   ├─ Pattern 5 Delegation / Pattern 6 クロスドメイン 必要?
│   │   ├─ Yes → Keycloak / RHBK 必須 (Cognito K1 不可)
│   │   └─ No  → Cognito + Lambda 実装 で代替可能
│   └─ Pattern 2/3 のみ → Cognito + Lambda 実装 OK (簡易)
└─ No → Cognito で OK
```

### 8.4 ヒアリング項目との連動

| 項目 | 質問 | 影響 |
|---|---|---|
| **B-104** | コアの Token を別エッジへの利用許可は必要か？ | K1 / 製品選定 |
| **B-304** | 業務シナリオで認証情報を別システムへリレー必要か？ | K1 / Delegation 採否 |
| 新規 | Token Exchange の用途は Pattern 1-7 のどれか？ | 設計詳細 |
| 新規 | Delegation 用 `act` 連鎖は最大何段必要か？ | 監査要件 |
| 新規 | 監査ログでの代理操作記録要件は？ | SOC2/ISO27001 対応 |

### 8.5 アーキテクチャ設計指針

- ✅ **デフォルトは Delegation 採用**（監査追跡可能性のため）
- ✅ **Impersonation は限定**（テストアカウント、緊急時のみ）
- ✅ **`audience` 必須**、交換ごとに分離
- ✅ **交換 Token TTL = 15min 以下**（通常 Token より短く）
- ✅ **Client は Confidential 必須**、Public Client は禁止
- ✅ **交換ポリシーは Client × Subject × Audience の Whitelist**
- ✅ **監査ログに subject / actor / audience / scope / reason を完全記録**

---

## 9. リファレンス

### 9.1 RFC / 仕様

- [RFC 8693 OAuth 2.0 Token Exchange](https://datatracker.ietf.org/doc/html/rfc8693) — 本仕様
- [RFC 6749 OAuth 2.0](https://datatracker.ietf.org/doc/html/rfc6749) — ベース仕様
- [RFC 7519 JWT](https://datatracker.ietf.org/doc/html/rfc7519) — JWT 仕様
- [RFC 7521 Assertion Framework](https://datatracker.ietf.org/doc/html/rfc7521) — Assertion ベース grant
- [RFC 7523 JWT Profile for OAuth 2.0 Client Authentication and Authorization Grants](https://datatracker.ietf.org/doc/html/rfc7523)

### 9.2 製品ドキュメント

- [Keycloak Token Exchange](https://www.keycloak.org/securing-apps/token-exchange)
- [AWS Cognito Limits / 代替実装](https://docs.aws.amazon.com/cognito/latest/developerguide/limits.html)
- [Microsoft Entra On-Behalf-Of Flow](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-on-behalf-of-flow)
- [Auth0 Custom Token Exchange](https://auth0.com/docs/authenticate/custom-token-exchange)
- [Okta Token Exchange](https://developer.okta.com/docs/guides/set-up-token-exchange/)

### 9.3 関連内部ドキュメント

- [auth-patterns.md §2.5 Token Exchange / OBO](auth-patterns.md) — 概要
- [platform-architecture-patterns.md](platform-architecture-patterns.md) — K1 を含む製品選定判定
- [§C-1.2.C / K1 Cognito Knockout (proposal/common/01-architecture.md)](../requirements/proposal/common/01-architecture.md)
- [§FR-6 認可設計 (proposal/fr/06-authz.md)](../requirements/proposal/fr/06-authz.md)
- [hearing-checklist.md §3.2 K1 列](../requirements/hearing-checklist.md)
- [hearing-script/03-authz-jwt.md](../requirements/hearing-script/03-authz-jwt.md) — B-104 ヒアリングスクリプト
- [hearing-script/01-auth-flow.md マスター表 C 補足 2 K1](../requirements/hearing-script/01-auth-flow.md)
- [powerpoint-slides/3.4-authz-jwt-api-flow-slides.md](../requirements/powerpoint-slides/3.4-authz-jwt-api-flow-slides.md) — 認可スライド
- [powerpoint-slides/1.3-architecture-strategy-slides.md](../requirements/powerpoint-slides/1.3-architecture-strategy-slides.md) — 集約 vs 例外対応

### 9.4 業界記事 / ベストプラクティス

- [Curity: OAuth 2.0 Token Exchange in detail](https://curity.io/resources/learn/oauth-token-exchange/)
- [Auth0: Token Exchange explained](https://auth0.com/blog/introducing-custom-token-exchange/)
- [OWASP Cheat Sheet: OAuth Token Exchange security](https://cheatsheetseries.owasp.org/cheatsheets/OAuth_Cheat_Sheet.html)

---

## 改訂履歴

- 2026-06-03: 初版作成。RFC 8693 全網羅 + 7 設計パターン + 実装例 4 言語 + 製品対応 + セキュリティ + 本プロジェクト設計判断
