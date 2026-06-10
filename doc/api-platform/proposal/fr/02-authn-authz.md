# §FR-API-2 認証認可（共有認証基盤連携 / API Key / mTLS / IAM）

> 親 SSOT: [../00-index.md](../00-index.md) §FR-API-2
> ヒアリング: [../../hearing-script/02-authn-authz.md](../../hearing-script/02-authn-authz.md)

---

## §2.0 前提と背景

### §2.0.1 用語整理

| 用語 | 定義 |
|---|---|
| **認証（AuthN）** | 呼び出し元が誰かを確認する（共有認証基盤の JWT / IAM の SigV4 / mTLS のクライアント証明書 等） |
| **認可（AuthZ）** | その呼び出し元が当該操作を許可されているか判断する |
| **Authorizer** | API Gateway / ALB / Lambda 等で AuthN/AuthZ を担うコンポーネント |
| **API Key** | API Gateway の使用量計測・利用者識別用キー。**認証手段ではない**（AWS 公式明記） |

### §2.0.2 なぜここ（§2）で決めるか

公開範囲（§1）が決まると、**境界ごとに利用可能な認証方式が絞られる**。本章では各境界に対応する標準パターンを定める：

- Public → 共有認証基盤の JWT
- Internal → IAM auth または JWT
- Partner → API Key + WAF または mTLS
- Private → IAM auth

また、認証認可は **共有認証基盤（[../../requirements/](../../requirements/00-index.md)）の利用面**に当たるため、両ドメインの境界を本章で明示する。

### §2.0.3 §2.0.A 本標準のスタンス

| 基本方針 | 本章での具体化 |
|---|---|
| 絶対安全 | **未認証 API を原則禁止**（例外は監査ログイベント等のヘルスチェック相当のみ）。API Key 単独を認証扱いしない |
| どんなアプリでも | OIDC/JWT・IAM・mTLS・API Key の 4 方式を境界別に網羅 |
| 効率よく | JWT 検証は API Gateway / ALB の **マネージド Authorizer 機能を優先**（Lambda Authorizer はカスタムロジック必須時のみ）|
| 運用負荷・コスト最小 | JWKS は共有認証基盤の Discovery エンドポイントから取得、ローテーションは認証基盤側任せ |

### §2.0.4 本章で扱うサブセクション

| § | サブセクション | 主題 |
|---|---|---|
| §2.1 | 共有認証基盤との連携 | JWT 検証・JWKS 取得・クレーム利用 |
| **§2.2** | **Partner 認証（OAuth Client Credentials デフォルト / API Key / mTLS）** | **OAuth Client Credentials 標準、API Key legacy/trial 用、mTLS 規制対応** |
| ↳ §2.2.7 | **Partner 認証 詳細フロー（リファレンス実装）** | 併用フロー・シーケンス図・リクエスト具体例・SDK・監査ログ |
| §2.3 | IAM auth（Internal/Private 向け） | SigV4・VPC Lattice Auth Policy |
| §2.4 | Authorizer 選定 | マネージド vs Lambda Authorizer の判断 |
| §2.A | SSR モノリスでの留意点 | ALB + Cognito session、ALB Authentication |
| **§2.B** | **未認証エンドポイントの標準保護パターン** | **アプリ UI を持たないデフォルト、Hosted UI 委譲** |

---

## §2.1 共有認証基盤との連携

**このサブセクションで定めること**：Public/Internal で JWT を受け取って検証する標準パターン。
**主な判断軸**：マネージド Authorizer 優先、Lambda Authorizer は限定。
**§2 全体との関係**：本サブセクションが §2.4 Authorizer 選定の主要候補。

### §2.1.1 ベースライン

- 共有認証基盤が発行する **OIDC ID Token / Access Token** を Bearer ヘッダで受け取る
- 検証方式：
  - **HTTP API**: JWT Authorizer（マネージド、issuer + audience 検証、低レイテンシ）
  - **REST API**: Cognito User Pool Authorizer（共有認証基盤が Cognito の場合）または Lambda Authorizer
  - **ALB**: Authenticate-OIDC アクション（Web UI を持つアプリ向け）または ALB に Lambda Authorizer は付かないので **後段で検証**
  - **AppSync**: OIDC Authorizer
- **JWKS は共有認証基盤の Discovery エンドポイント**（`/.well-known/openid-configuration`）から取得、API Gateway/Lambda がキャッシュ
- クレーム利用：
  - `sub`: ユーザー識別子
  - `aud`: 自 API の audience（必須検証）
  - `iss`: 共有認証基盤の issuer（必須検証）
  - カスタムクレーム（`tenant_id`、`roles` 等）はアプリ側でテナント分離・認可に利用

### §2.1.2 TBD / 要確認

- Q: **Access Token vs ID Token のどちらを API 認証に使うか**（OAuth 2.0 推奨は Access Token） → 共有認証基盤側の方針に合わせる、`API-B-201`
- Q: クレームのうち **どれを「必ず検証する」か**（aud, iss, exp は必須、他は？）→ `API-B-202`
- Q: 共有認証基盤の **JWKS endpoint がプライベートか否か**（PoC では Private 化を検討中）の取扱い → `API-B-203`

---

## §2.2 Partner 認証（OAuth Client Credentials デフォルト / API Key / mTLS）

**このサブセクションで定めること**：B2B Partner との M2M（Machine-to-Machine）認証の標準。
**主な判断軸**：信頼レベル × 業界標準 × 運用負荷。**OAuth Client Credentials が業界主流**（Salesforce / Microsoft Graph / Stripe モダン版）。
**§2 全体との関係**：Partner 公開範囲での標準。§3 流量制御・§4 課金とセットで運用。

**本サブセクション内の構成**：

| § | 内容 | レベル |
|---|---|---|
| §2.2.0 | Partner B2B M2M スコープ確認（前提） | 要件 |
| §2.2.1〜§2.2.6 | 認証方式選定・Identity モデル・構成テンプレ・ライフサイクル・tier・TBD | 要件 / 方針 |
| **§2.2.7** | **Partner 認証 詳細フロー（リファレンス実装）** | **実装詳細**（Partner 開発者向け、Service Catalog 製品の元仕様） |

### §2.2.0 ⚠ 前提：Partner B2B M2M がスコープに含まれるかを先に確認

**本サブセクション（§2.2.1 以降）は Partner B2B API（外部企業システムからの M2M 呼び出し）が要件化された場合のみ適用**する。要件化されていない場合、本サブセクション全体は **対応なし** として扱う。

確認すべき項目：

| ID | 確認内容 | Phase |
|---|---|---|
| **API-A-112** | 現状で Partner B2B API（外部企業からの M2M 呼び出し）連携アプリの有無と Partner 数 | A |
| **API-A-113** | 将来 1〜3 年で M2M 連携要件が発生する可能性 | A |

#### 判定フロー

```mermaid
flowchart TD
    Q1{Partner B2B M2M<br/>連携の現状 or 想定<br/>あり?}
    Q1 -->|"No（両方なし）"| Skip["§2.2 全体スキップ<br/>Partner 公開範囲は §1.1 で定義のみ残す"]
    Q1 -->|"Yes（現状あり or 将来想定）"| Q2{要件規模は?}
    Q2 -->|"単発 / 小規模"| Lite["§2.2.1〜§2.2.5 軽量版<br/>API Key + Usage Plan で当面対応"]
    Q2 -->|"複数 Partner / 継続"| Full["§2.2.1〜§2.2.6 フル適用<br/>OAuth Client Credentials デフォルト"]

    style Skip fill:#f5f5f5,stroke:#9e9e9e
    style Lite fill:#fff3e0,stroke:#e65100
    style Full fill:#e3f2fd,stroke:#1565c0
```

→ ヒアリング A-112 / A-113 で要件確認後、本サブセクション §2.2.1 以降の適用範囲を確定する。

### §2.2.1 認証方式の選択肢

（以下 §2.2.1〜§2.2.6 は Partner B2B M2M がスコープに含まれる前提）

| # | 方式 | 信頼レベル | 業界実例 | 本標準での位置 |
|---|---|:---:|---|---|
| 1 | **OAuth 2.0 Client Credentials Grant**（[RFC 6749 §4.4](https://datatracker.ietf.org/doc/html/rfc6749#section-4.4)）| 中-高 | Salesforce, Microsoft Graph, Stripe（モダン版）| ⭐ **新規 Partner のデフォルト** |
| 2 | **API Key + Usage Plan** | 低 | Stripe（一部）、Twilio、SendGrid | **Legacy / Trial 用に退く** |
| 3 | **mTLS（Mutual TLS）**（[RFC 8705](https://datatracker.ietf.org/doc/html/rfc8705)）| 最高 | 金融 / 決済 / FAPI 2.0 | **規制対応の escalation** |
| 4 | OAuth JWT Bearer（[RFC 7523](https://datatracker.ietf.org/doc/html/rfc7523)）| 高 | GitHub Apps, Snowflake | 例外承認制 |
| 5 | API Key + IP Allowlist | 中 | 多数の B2B SaaS | 既存 Partner 互換性維持用 |

**重要な事実**：**API Key は「識別」であって「認証」ではない**（[AWS 公式明記](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-api-usage-plans.html)）→ 厳密には認証としての利用は推奨されない。本標準は業界トレンドに合わせ OAuth Client Credentials をデフォルト推奨。

### §2.2.2 Partner Identity モデル（識別単位）

**標準は Per-Partner-App × Per-Environment**（業界主流）：

| 単位 | 例 | 使い分け |
|---|---|---|
| Per-Partner Organization | Acme Corp 全体に 1 Credential | 小規模 / シンプル運用 |
| **Per-Partner-App × Per-Environment** ⭐ | Acme Mobile (prod), Acme Mobile (stg), Acme Web (prod) | **本標準のデフォルト**、scope 制御と事故防止に有利 |

**Partner Application 台帳の所在**：**共有認証基盤側で M2M Client（App Client）として管理**する（OAuth Client Credentials の発行元は認証基盤）。本標準（アプリ側）は **JWT を受け取って検証する側**。詳細は [§C-API-3 §C-3.1](../common/03-shared-auth-boundary.md)。

### §2.2.3 認証方式別の構成テンプレ

**A. OAuth Client Credentials（新規デフォルト）**

```
Partner → Custom Domain → CloudFront → WAF → REST API
  → JWT Authorizer（共有認証基盤の M2M App Client で発行された Access Token を検証）
  → Lambda / ECS
  + Per-client throttle（JWT クレーム `client_id` ベース）
  + Per-tenant 課金按分（JWT クレーム `tenant_id`）
```

**B. API Key + Usage Plan（Legacy / Trial 用）**

```
Partner → Custom Domain → CloudFront → WAF → REST API
  → API Key 検証 + Usage Plan
  → Lambda / ECS
  + Per-key throttle / quota（Usage Plan）
```
- 配布は Secrets Manager 経由、ローテーション 90 日 / 180 日 / 1 年
- **新規 Partner には推奨せず**、既存 Partner の互換性維持・Trial / 内部テスト用途のみ

**C. mTLS（規制対応 escalation）**

```
Partner → Custom Domain (mTLS Listener) → CloudFront 不可（mTLS なら直接 ALB / API GW）
  → API Gateway REST API + Truststore（クライアント CA バンドル）
  → JWT Authorizer（OAuth Client Credentials も併用、FAPI 2.0 準拠）
  → Lambda / ECS
```
- 適用：金融 / 決済 / 医療 等の規制業界、または FAPI 2.0 準拠要件
- 証明書発行：自社 PKI / AWS Private CA / Partner 側 CA のいずれか（要件次第）
- 失効リスト（CRL）運用、Overlap Period 24-72 時間

### §2.2.4 クレデンシャルライフサイクル（標準）

| フェーズ | 標準オペレーション | 業界標準値 |
|---|---|---|
| 発行 | 共有認証基盤の管理 API / Portal で発行 | - |
| 配布 | Secrets Manager / 暗号化メール / PrivateLink share | - |
| ローテーション | 期限ベース（90 日 / 180 日 / 1 年）+ Compromise 時即時 | - |
| 期限通知 | 30 日前 / 7 日前にダッシュボード + メール | - |
| Overlap Period | 旧新 Credential 併存 | **24-72 時間** |
| Revocation | Compromise 検知時の緊急停止 | 24h 以内 |
| 監査 | 利用ログ、最終利用時刻、ローテーション履歴 | コンプラ次第（7 年等）|

### §2.2.5 Partner-tier 別の構成パターン例（参考）

| Tier | デフォルト認証 | 適用 |
|---|---|---|
| **Bronze** | API Key + Usage Plan | Trial / 旧 Partner / 軽量 API |
| **Silver**（標準）| OAuth Client Credentials + JWT | 業界標準 B2B |
| **Gold** | OAuth Client Credentials + mTLS | 規制業界 / 重要パートナー / FAPI 2.0 |

### §2.2.6 TBD / 要確認

- Q: **Partner 新規デフォルトは OAuth Client Credentials で確定するか、API Key 互換性も標準に残すか** → `API-B-211`（**🔥 修正版**）
- Q: Partner identity 識別単位（Per-Org / Per-App / Per-Env）→ `API-B-214`
- Q: Partner Scope / Permission の細粒度（OAuth scope のみ / Verified Permissions 併用）→ `API-B-215`
- Q: Partner クレデンシャルのローテーション周期 + Overlap period → `API-B-216`
- Q: Partner オンボーディングフロー（自社ポータル / AWS Marketplace / 個別契約）→ `API-B-217`
- Q: Partner-tier の差別化（Bronze / Silver / Gold）を持つか → `API-B-218`
- Q: 既存 Partner の認証方式（互換性維持の要否）→ `API-B-219`
- Q: mTLS 採用時の証明書発行元（自社 PKI / AWS Private CA / Partner 側 CA）→ `API-B-220`（旧 API-B-213）
- Q: FAPI 2.0 など規制業界準拠の Partner 要件 → `API-D-241`

---

## §2.2.7 Partner 認証 詳細フロー（リファレンス実装）

> **位置付け**：§2.2.1〜§2.2.6 で決めた **「OAuth Client Credentials + API Key 併用」標準パターン** の **実装レベル詳細**。Partner 開発者向けのリファレンス、社内 Service Catalog 製品の元仕様、PowerPoint 補足資料として活用。
> **対象読者**：Partner 開発者、本標準の Service Catalog 製品設計者、認証基盤側との合議メンバー。

### §2.2.7.1 API Key と認証の役割分担

「**API Key だけ**」または「**Bearer Token だけ**」では Partner B2B として不十分。両者を併用する理由：

| 観点 | API Key | OAuth Bearer Token / mTLS |
|---|:---:|:---:|
| **利用者識別**（誰か）| ✅ Usage Plan / 課金按分 / ログ識別 | ✅ JWT クレーム or 証明書 Subject |
| **認証**（本当に本人か）| ❌ **暗号学的検証なし**、リプレイ可能 | ✅ 署名検証 / 期限あり |
| 流量制御の単位 | ✅ Usage Plan 直結 | △ JWT クレームで自前実装可 |
| 期限管理 | ❌ 手動ローテーションのみ | ✅ TTL 自動失効（OAuth: 1h 標準）|
| 漏洩リスク | ⚠ 文字列のみ、漏れたら即悪用可 | ✅ 短期 token なら被害限定 |

**AWS 公式明記**："Don't use API keys for authentication or authorization to control access to your APIs"（[Usage Plans and API Keys docs](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-api-usage-plans.html)）

→ **API Key = 識別用（Usage Plan / 課金）**、**OAuth Bearer Token または mTLS = 認証用（暗号学的検証）** の役割分担で組み合わせる。

### §2.2.7.2 4 つの併用パターン

| # | パターン | 適用 | API Gateway 種別 | 位置付け |
|---|---|---|:---:|---|
| **1** | API Key + OAuth Client Credentials ⭐ | 新規 Partner デフォルト | REST API | **本標準の推奨**（§2.2.3 A）|
| 2 | API Key + Lambda Authorizer（HMAC 等）| 特殊検証 | REST API | 例外承認制 |
| 3 | API Key + mTLS（+ OAuth）| 規制業界・最高信頼 | REST API | escalation（§2.2.3 C） |
| 4 | OAuth のみ（API Key なし）| HTTP API 採用時 | HTTP API | Usage Plan 不要なら |

### §2.2.7.3 標準パターン（OAuth Client Credentials）の詳細フロー

#### A. フェーズ A：一度限りのセットアップ

```mermaid
sequenceDiagram
    participant SecOps as SecOps/Platform
    participant Auth as 共有認証基盤<br/>(Cognito/Keycloak)
    participant APIGW as 各アプリ AWS<br/>API Gateway
    participant Partner as Partner システム
    participant SM as Secrets Manager

    SecOps->>Auth: Partner 申請承認後<br/>M2M App Client 作成<br/>(例: Acme Mobile prod)
    Auth-->>SecOps: client_id + client_secret 発行
    SecOps->>APIGW: API Key 発行 + Usage Plan 紐付け<br/>+ Scope 割当
    APIGW-->>SecOps: api_key 発行
    SecOps->>SM: client_secret + api_key を<br/>セキュアに格納
    SecOps->>Partner: client_id + client_secret + api_key を<br/>セキュアチャネル配布<br/>(暗号化メール/PrivateLink share)
    Partner->>Partner: 自社 Secrets 管理に格納
```

**発行されるもの 3 点**：

| アイテム | 性質 | 取り扱い |
|---|---|---|
| `client_id` | Partner App 識別子（公開可）| ログに出してよい |
| `client_secret` | 認証用シークレット | **絶対秘匿**、Secrets Manager 等で管理 |
| `api_key` | Usage Plan 識別子（識別 + 流量制御用）| Secrets Manager 管理推奨、リクエストヘッダで送信 |

#### B. フェーズ B：実行時フロー

```mermaid
sequenceDiagram
    participant P as Partner システム
    participant Cache as Token Cache<br/>(Partner 側)
    participant Auth as 共有認証基盤<br/>/oauth2/token
    participant CF as CloudFront
    participant WAF as AWS WAF
    participant APIGW as API Gateway
    participant Authz as JWT Authorizer
    participant Lambda as Lambda/ECS

    Note over P,Lambda: Step 1: Access Token 取得（初回 or 期限切れ時）
    P->>Cache: access_token がキャッシュにあるか?
    Cache-->>P: ない or 期限切れ
    P->>Auth: POST /oauth2/token<br/>Authorization: Basic base64(client_id:client_secret)<br/>grant_type=client_credentials<br/>scope=orders:read orders:write
    Auth-->>P: {access_token: "eyJ...", expires_in: 3600}
    P->>Cache: token を保存（TTL 3600s - margin 60s）

    Note over P,Lambda: Step 2: API 呼び出し（複数回、token 有効期間中）
    P->>CF: POST /api/v1/orders<br/>x-api-key: [api_key]<br/>Authorization: Bearer [access_token]
    CF->>WAF: WAF Managed Rules 評価
    WAF->>APIGW: 通過
    APIGW->>APIGW: API Key 検証<br/>(Usage Plan throttle/quota)
    APIGW->>Authz: JWT Authorizer 起動
    Authz->>Authz: JWT 署名検証 (JWKS)<br/>iss, aud, exp, scope 検証
    Authz-->>APIGW: Allow + client_id, scope を context に
    APIGW->>Lambda: invoke with context
    Lambda-->>P: 200 OK
```

#### C. フェーズ C：Token Refresh 戦略

Access Token は **1 時間 TTL が標準**。Partner システムは：

| 戦略 | タイミング | 適用 |
|---|---|---|
| **Lazy refresh** | API 呼出前に期限チェック、期限が近ければ /oauth2/token 再取得 | シンプル、低頻度呼出 |
| **Proactive refresh** | バックグラウンドジョブで期限 5 分前に refresh | 高頻度呼出、レイテンシ要件厳しい |
| **On 401** | API が 401 を返したら refresh + 1 回 retry | フォールバック / 例外処理 |

→ **本標準推奨**：**Lazy refresh + On 401 retry** の組合せ。SDK 利用なら自動実装される（§2.2.7.7）。

### §2.2.7.4 リクエスト・レスポンス具体例

#### A. Token 取得

**リクエスト**：
```http
POST /oauth2/token HTTP/1.1
Host: auth.example.com
Authorization: Basic YWNtZS1tb2JpbGUtcHJvZC1hYmMxMjM6c2VjcmV0LXJhbmRvbS0xMjg=
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials&scope=orders%3Aread%20orders%3Awrite
```

**レスポンス**：
```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: no-store

{
  "access_token": "eyJraWQiOiI3M...（JWT）",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "orders:read orders:write"
}
```

**JWT の中身**（decode した payload 例）：
```json
{
  "iss": "https://auth.example.com",
  "sub": "acme-mobile-prod-abc123",
  "aud": "https://api.example.com",
  "exp": 1717689600,
  "iat": 1717686000,
  "client_id": "acme-mobile-prod-abc123",
  "scope": "orders:read orders:write",
  "tenant_id": "acme-corp",
  "env": "prod"
}
```

#### B. API 呼び出し

**リクエスト**：
```http
POST /api/v1/orders HTTP/1.1
Host: api.example.com
x-api-key: 0123456789abcdef0123456789abcdef
Authorization: Bearer eyJraWQiOiI3M...
Content-Type: application/json

{"product_id": "prod-1", "quantity": 5}
```

**成功レスポンス**：
```http
HTTP/1.1 201 Created
Content-Type: application/json
X-Request-Id: 7f3e4a5b-...
X-RateLimit-Remaining: 999

{"order_id": "ord-12345", "status": "created"}
```

#### C. エラーケース一覧

| シナリオ | ステータス | 原因 | 対処（Partner 側）|
|---|:---:|---|---|
| API Key 不正・欠落 | `403 Forbidden`（API Gateway） | x-api-key 未送信 / 無効 | client_id を確認、Secrets 再確認 |
| Bearer 欠落 / 不正署名 | `401 Unauthorized`（Authorizer） | Authorization ヘッダ不正 | 認証フロー再実行（/oauth2/token） |
| token 期限切れ | `401 Unauthorized` | exp 過ぎ | refresh → retry |
| scope 不足 | `403 Forbidden`（Authorizer） | 必要な scope が token に含まれない | 必要な scope を申請、token 再取得 |
| Usage Plan quota 超過 | `429 Too Many Requests` | 月次 / 日次 quota 到達 | 翌期間まで待つ / quota 上限見直し |
| Throttle 超過（短期スパイク）| `429 Too Many Requests` | rate / burst 超過 | Exponential backoff |

### §2.2.7.5 API Gateway 側の設定

**REST API のリソース設定例**：

```
[Resource: /api/v1/orders]
├ Method: POST
│  ├ API Key Required: ✅ true                ← Usage Plan 識別
│  ├ Authorization: COGNITO_USER_POOLS         ← Cognito M2M Authorizer
│  │  or CUSTOM (Lambda Authorizer)
│  └ Authorization Scopes: orders:write        ← scope 検証

[Usage Plan: partner-silver]
├ Throttle: 1000 req/s burst 2000
├ Quota: 1,000,000 req/month
└ API Keys:
    ├ key_acme-mobile-prod (associated with Partner App)
    └ key_globex-web-prod
```

### §2.2.7.6 Token Cache 戦略の重要性

毎リクエストで /oauth2/token を叩くと：

- 認証基盤側に巨大な負荷（1 リクエストにつき 1 token 取得 = 倍のリクエスト）
- レイテンシ +200ms ペナルティ毎回
- /oauth2/token 自体の rate limit に引っかかる

**標準のキャッシュ戦略**（Partner システム実装ガイドライン）：

| 規模 | 推奨キャッシュ |
|---|---|
| 小規模（単一インスタンス）| **in-memory cache**（言語標準のオブジェクト保持）|
| 中規模（複数インスタンス）| **共有 cache**（Redis / DynamoDB）|
| TTL 設定 | `expires_in - 60秒`（マージン）|

### §2.2.7.7 推奨 SDK ライブラリ

業界では Auth Library が標準化されており、**token cache / 自動 refresh / 401 リトライ** を内蔵。本標準では以下を推奨：

| 言語 | 推奨ライブラリ |
|---|---|
| Java | [Spring Security OAuth2 Client](https://docs.spring.io/spring-security/reference/servlet/oauth2/client/index.html) |
| Node.js / TypeScript | [openid-client](https://github.com/panva/openid-client) |
| Python | [requests-oauthlib](https://github.com/requests/requests-oauthlib), [Authlib](https://docs.authlib.org/) |
| Go | [`golang.org/x/oauth2/clientcredentials`](https://pkg.go.dev/golang.org/x/oauth2/clientcredentials) |
| .NET | [Microsoft.Identity.Client (MSAL.NET)](https://learn.microsoft.com/en-us/entra/msal/dotnet/) |
| Ruby | [oauth2 gem](https://github.com/oauth-xx/oauth2) |

→ Partner 開発者向けドキュメントには「**これらの SDK を使うことを強く推奨**（手書き実装は token cache・refresh・401 リトライの抜けによる事故が多発）」と明記。

### §2.2.7.8 監査ログでの識別

各 API 呼び出しのアクセスログには以下フィールドを必須化：

| フィールド | 内容 | 用途 |
|---|---|---|
| `requestId` | リクエスト一意 ID | トレース |
| `apiKeyId` | API Key（マスク：先頭 4 + 末尾 4）| Usage Plan / 課金按分 |
| `clientId` | JWT クレーム `client_id` | Partner App 識別 |
| `tenantId` | JWT クレーム `tenant_id` | Partner 所属識別 |
| `scope` | 使用された scope | 認可監査 |
| `wafResponseCode` | WAF 評価結果 | セキュリティ監査 |
| `statusCode` | HTTP ステータス | 成功/エラー判定 |
| `latency` | レイテンシ | パフォーマンス |

**異常検知ルール例**：
- `apiKeyId` と `clientId` が **一致しない**呼び出し → anomaly alert（例：A 社の API Key で B 社の token が来る）
- 同一 `clientId` で **複数の IP / リージョン** → クレデンシャル漏洩疑い
- 期限直前 token の **大量取得**（DDoS や Stress test）

### §2.2.7.9 mTLS 併用パターン（規制業界向け）

mTLS は **TLS handshake で証明書検証** されるので、HTTP リクエストの Bearer Token とは別レイヤー：

```mermaid
flowchart LR
    P[Partner] -->|"① TLS handshake（client cert）"| TLS[TLS Layer]
    TLS -->|"② cert 検証（Truststore）"| HTTP[HTTP Layer]
    P -->|"③ x-api-key + Bearer token"| HTTP
    HTTP -->|"④ Lambda Authorizer"| Verify[3 重検証]
    Verify -->|"a) TLS Subject DN ↔ JWT client_id 一致"| Allow[Allow]
    Verify -->|"b) JWT 署名・exp・aud"| Allow
    Verify -->|"c) scope"| Allow
    Allow --> Lambda["Lambda / ECS"]
```

**3 重防御の意義**：
- a) TLS 証明書持参（**物理的に証明書を持っている**）
- b) JWT 署名（**client_secret を知っている**）
- c) Usage Plan API Key（**識別 + 流量制御**）

→ FAPI 2.0 等の規制業界要件で必要。証明書発行元・CRL 運用は §2.2.6 → `API-B-220` で確定。

### §2.2.7.10 アンチパターン / 注意点

| ❌ アンチパターン | ✅ 正しいパターン |
|---|---|
| API Key だけで認証扱い | API Key（識別）+ Bearer Token（認証）の併用 |
| 毎回 /oauth2/token を叩く | Token cache + Lazy refresh |
| `client_secret` をコード / Git に書く | Secrets Manager / Vault 等で管理 |
| `client_secret` をログ出力 | マスク（先頭 4 + 末尾 4）|
| Bearer Token を URL クエリパラメータで送信 | `Authorization: Bearer ...` ヘッダで送信 |
| API Key を URL クエリパラメータで送信 | `x-api-key` ヘッダで送信 |
| token を localStorage / Cookie に置く（M2M 用途） | サーバサイドメモリ / Secrets Manager |
| 同一 client_secret を prod / stg で使い回し | Per-Environment 単位で分離（§2.2.2）|
| Refresh Token も Client Credentials で取得しようとする | M2M に Refresh Token は不要（client_secret で再取得）|

### §2.2.7.11 関連項目への参照

- §2.2.0 Partner B2B M2M スコープ確認（前提）
- §2.2.1〜§2.2.6 認証方式選定・ライフサイクル・TBD
- §2.4 Authorizer 選定（JWT Authorizer vs Lambda Authorizer）
- [§C-API-3 §C-3.1 C 認証基盤側 Partner M2M Client 管理機能](../common/03-shared-auth-boundary.md)
- [escalation-to-auth.md §1.1](../../escalation-to-auth.md) — 認証側への申し送り
- §FR-API-3 流量制御 — Usage Plan 設定
- §FR-API-4 利用者識別 — `client_id` / `tenant_id` の課金按分活用
- §FR-API-8 観測性 — 監査ログ設計

---

## §2.3 IAM auth（Internal / Private 向け）

**このサブセクションで定めること**：AWS 内部から呼ぶ API の標準認証方式。
**主な判断軸**：マネージド・低レイテンシ・最小権限。
**§2 全体との関係**：Internal / Private 区分のデフォルト。

### §2.3.1 ベースライン

- **SigV4 署名**を呼び出し元（Lambda / ECS task role / EC2 instance profile）が付与
- API Gateway 側：`AWS_IAM` authorization、Resource Policy で `aws:PrincipalOrgID` や VPC Endpoint ID で絞る
- **VPC Lattice**: Service ごとに Auth Policy（IAM ポリシー記述）で許可 Principal を定義。Service Connect だけでは IAM 認可は提供されないので、Lattice 採用が標準
- **Lambda Function URL**: `AuthType=AWS_IAM` で IAM 認可を有効化

### §2.3.2 TBD / 要確認

- Q: **Internal 区分の標準は IAM auth か JWT か**（既存アプリが JWT 前提なら混在許容）→ `API-B-221`
- Q: VPC Lattice 採用範囲（前述 §1.2 と整合）→ `API-B-106`（再掲）
- Q: Cross-account の IAM 信頼関係セットアップを **Service Catalog で配布する**か、各アプリ自前か → `API-B-222`

---

## §2.4 Authorizer 選定

**このサブセクションで定めること**：マネージド Authorizer / Lambda Authorizer のいずれを採用するかの選定基準。
**主な判断軸**：レイテンシ・コスト・実装柔軟性。
**§2 全体との関係**：§2.1 / §2.2 / §2.3 の選択肢を集約した判断章。

### §2.4.1 ベースライン

| Authorizer 種別 | 採用基準 | 制約 |
|---|---|---|
| **JWT Authorizer (HTTP API)** | 標準 OIDC + audience 検証で十分なケース | カスタムクレーム判定はアプリ側 |
| **Cognito Authorizer (REST API)** | 共有認証基盤が Cognito 直結のケース | 他 IdP の JWT には使えない |
| **IAM auth** | AWS 内部呼び出し | IdP ユーザーの権限判定はできない |
| **Lambda Authorizer** | テナント分離・Verified Permissions / OPA 連携・Authorizer 内で外部 API 呼出 | レイテンシ +20-100ms、コスト増、キャッシュ設計必須 |

### §2.4.2 TBD / 要確認

- Q: **Lambda Authorizer の使用を例外承認制にするか**（コスト・レイテンシ影響大）→ `API-B-241`
- Q: Lambda Authorizer の **キャッシュ TTL の標準値**（Cognito 5 分、JWT は exp までが一般的）→ `API-B-242`
- Q: AWS Verified Permissions（Cedar）の採用範囲（細粒度認可の標準にするか）→ `API-B-243`

---

## §2.B 未認証エンドポイントの標準保護パターン

**このサブセクションで定めること**：パブリック（オープン）Profile（[§FR-API-1 §1.1](01-exposure-boundary.md)）のエンドポイントの設計指針と保護パターン。
**主な判断軸**：アプリ UI を持つか持たないか、業界主流の Hosted UI 委譲を採るか、認証フロー API は共有認証基盤に委ねるか。
**§2 全体との関係**：§2.1 共有認証基盤連携（認証必須エンドポイント）の対面として、認証不要エンドポイントの設計を扱う。

### §2.B.1 本標準のデフォルトスタンス：「アプリ UI を持たない」

業界主流（Salesforce、Workday、ServiceNow、Slack、Notion、Microsoft 365 等）は **サインイン・サインアップ UI をアプリで持たず、共有認証基盤の Hosted UI または IdP-Initiated SSO に委譲** している。本標準もこれをデフォルトとする。

| アプローチ | アプリ UI | サインイン UI 所在 | 業界実例 |
|---|---|---|---|
| **A. IdP-Initiated SSO**（完全委譲）| ❌ なし | 顧客 IdP の画面 | Salesforce、Workday、ServiceNow |
| **B. SP-Initiated（テナント別 URL）**| 「ログイン」リンクのみ | 顧客 IdP（URL に tenant 埋込）| Slack、Notion |
| **C. SP-Initiated + HRD** | メアド入力ページのみ | 顧客 IdP or Hosted UI | Microsoft 365、Auth0、Okta |
| **D. Hosted UI 委譲** | 「ログイン」リンクのみ | 認証基盤の Hosted UI | Cognito 採用アプリ |
| **E. アプリ完全実装**（例外）| ✅ あり | アプリ内フォーム | 強いカスタマイズ要件のみ |

**デフォルト**：A〜D いずれか（要件次第）。E は **例外承認制**。

### §2.B.2 サインアップの要否判断

| ケース | サインアップ UI | 理由 |
|---|:---:|---|
| **B2B + 顧客 IdP 連携** | ❌ 不要 | JIT プロビジョニング（初回ログインで自動作成）|
| **B2B + SCIM プロビジョニング** | ❌ 不要 | 顧客 IdP 側の管理者がユーザー追加 → 自動同期 |
| **B2B + 招待型（Invitation flow）**| △ 一部要 | 招待リンク → 承認画面のみ |
| **B2C（個人ユーザー）**| ✅ 必要 | 個人が自分で作成、認証基盤 Hosted UI に委譲 |
| **試用版・無料アカウント**| ✅ 必要 | セルフサービス前提、認証基盤 Hosted UI に委譲 |
| **IdP を持たない顧客向け（SMB 等）**| ✅ 必要 | アプリ独自 ID/Password、認証基盤 Hosted UI に委譲 |

→ サインアップが必要な場合も、**「サインアップ実行（DB 書き込み）は共有認証基盤側」**。アプリ側はリンクで認証基盤に Redirect。

### §2.B.3 アプリ UI を持たない場合の パブリック（オープン）エンドポイント

本標準スコープに残るのは主に：

| エンドポイント | 用途 | 保護 |
|---|---|---|
| ランディング・マーケティング（HTML / Web ページ）| 集客 / 製品紹介 | CloudFront 長 TTL + WAF Managed Rules + Per-IP rate（緩め）|
| 価格・公開カタログ（HTML / 公開 API）| 製品情報公開 | CloudFront 短 TTL + WAF Managed + Per-IP rate（中）|
| 公開データ API（`/api/v1/public/*`）| 公開データ提供 | 同上 |
| ヘルスチェック（外部公開する場合）| 監視 / 外形 | 別 path（`/_/healthz`）+ Per-IP rate |
| `robots.txt` / `sitemap.xml` | SEO | CloudFront キャッシュ |
| HRD ページ（パターン C 採用時）| メアド → IdP 判定 | CloudFront + WAF + Per-IP rate（厳しめ）|

### §2.B.4 アプリ UI を持つ場合（例外）の保護パターン

アプリで サインイン / サインアップ UI を実装する場合（パターン E）：

| エンドポイント | 保護 |
|---|---|
| Sign-in form | WAF Bot Control + AWS WAF ATP（[Account Takeover Prevention](https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-atp.html)）+ CAPTCHA + 厳しい rate |
| Sign-up form | WAF Bot Control + AWS WAF ACFP（[Account Creation Fraud Prevention](https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-acfp.html)）+ CAPTCHA + 厳しい rate |
| Password reset 要求 | WAF Bot Control + CAPTCHA + メール送信側の rate |
| 認証実行（サインイン処理）| **共有認証基盤 API に委譲**（ROPC / Cognito InitiateAuth 等）、本標準アプリでは認証ロジックを実装しない |

詳細な WAF 設定（ATP / ACFP 採用範囲、Bot Control コスト）は [§FR-API-7 §7.1](07-guardrails.md) で別途検討。

### §2.B.5 共有認証基盤との分担

| 役割 | 認証側（[../requirements/](../../../requirements/00-index.md)）| 本標準（API プラットフォーム）|
|---|:---:|:---:|
| `/.well-known/openid-configuration`, `/jwks`, `/authorize`, `/token`, `/logout` | ✅ | - |
| Hosted UI（Cognito Hosted UI / Keycloak login page）| ✅ | - |
| サインアップ実行（DB 書き込み）| ✅ | - |
| HRD ページ（メアド入力 → IdP 判定）| △ | △（パターン C の所在は認証側で確定）|
| **アプリ ランディング・マーケティング**| - | ✅ |
| **アプリ 公開データ API**| - | ✅ |
| アプリ サインイン / サインアップフォーム表示（例外時）| - | △（例外承認制）|

詳細は [§C-API-3 §C-3.1](../common/03-shared-auth-boundary.md) 認証基盤側が提供する契約。

### §2.B.6 TBD / 要確認

- Q: **未認証アクセスが必須のエンドポイント棚卸し**（マーケ・公開データ API のリスト）→ `API-B-103`
- Q: **サインイン / サインアップ UI をアプリで持つ標準アプリの有無**（🔥 認証側方針との連動）→ `API-B-107`
- Q: サインアップフローの所在（IdP 連携 JIT / 認証基盤 Hosted / アプリ実装）→ `API-B-108`
- Q: HRD ページの所在（認証基盤 / アプリ）→ `API-D-1402-α`

---

## §2.A SSR モノリスでの留意点

[§C-API-2 §C-2.1](../common/02-runtime-selection-criteria.md) のパターン C（SSR モノリス）では、認証方式の標準が API Gateway 系と異なる：

| 観点 | API Gateway 系（API） | SSR モノリス |
|---|---|---|
| **第一選択** | JWT Authorizer（HTTP API）/ Cognito Authorizer（REST API） | **ALB Authentication（Cognito / OIDC）** |
| トークン形式 | Bearer JWT in `Authorization` ヘッダ | **Session Cookie**（ALB が `AWSELBAuthSessionCookie`、または独自 cookie） |
| クレーム取得 | アプリ側で JWT decode | ALB が **`X-Amzn-Oidc-Data`** / **`X-Amzn-Oidc-Identity`** ヘッダに注入 |
| 認可ロジックの位置 | Lambda Authorizer / Verified Permissions | アプリ内 middleware（Next.js middleware、Rails before_action、Spring Security 等）|
| API Key | API GW Usage Plan | **使えない**（ALB に Usage Plan なし） — 必要なら自前検証 |
| mTLS | API GW Custom Domain | **ALB mTLS Listener**（2023〜） |
| IAM auth | API Gateway IAM auth | ALB は IAM auth 非対応 → **Cognito session または独自 IdP** |

**モノリス採用時の認証パス（推奨）**：
1. ブラウザ → CloudFront → ALB
2. ALB が未認証検知 → Cognito Hosted UI へリダイレクト
3. 認証成功 → ALB が **session cookie 発行 + `X-Amzn-Oidc-*` ヘッダ注入**
4. ECS の SSR モノリスがクレームを参照、アプリ内で認可判定
5. `/api/*` も同じ session cookie で認証（モバイル API 等の Bearer token 必要なら別 endpoint 切り出し検討）

**API 切り出し時の認証**：
- 将来モバイル / 外部 Partner 連携で `/api/*` を別サービスに切り出す場合、認証は **Bearer JWT** に切り替える必要あり（§C-API-2 §C-2.3 段階移行パス）

詳細は [§FR-API-6 §6.1.A モノリス vs マイクロサービス](06-container-standard.md) 参照。

---

## §2.x 関連ドキュメント

- [§FR-API-1 公開範囲](01-exposure-boundary.md) — 境界別の認証方式マッピング
- [§FR-API-3 流量制御](03-throttling-quota.md) — API Key と Usage Plan の関係
- [§FR-API-4 課金](04-metering-billing.md) — 利用者識別子（API Key・JWT sub）の活用
- [§FR-API-6 §6.1.A モノリス vs マイクロサービス](06-container-standard.md) — モノリス採用時の認証設計
- [§C-API-3 共有認証基盤との接続点](../common/03-shared-auth-boundary.md) — 認証基盤側 SSOT との境界整理
