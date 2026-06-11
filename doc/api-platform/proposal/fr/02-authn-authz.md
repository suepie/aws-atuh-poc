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
| **§2.2** | **Partner 認証（Tier 別：Bronze OAuth / Silver Token Exchange / Gold mTLS）** | **Path C 確定：Token Exchange を Silver 主流、§FR-6 と整合** |
| ↳ §2.2.7 | Partner 認証 詳細フロー：OAuth Client Credentials（**Bronze fallback**）| Partner が IdP 持たない場合の OAuth + API Key 併用 |
| ↳ §2.2.8 | **Partner 認証 詳細フロー：Token Exchange RFC 8693（Silver 主流）⭐** | **§FR-6 K-01 と整合、Partner IdP token を /token で exchange** |
| ↳ §2.2.9 | **Federation B：Multi-Issuer at API（長期 ADR placeholder）** | 認証側設計変更を要する究極形、長期ロードマップ |
| ↳ §2.2.10 | **Defense-in-depth 4 層防御** | Dedicated /token + WAF + Pool 分離 + API IP allowlist |
| §2.3 | **IAM auth（AWS ネイティブ Internal / Private 向け）** | SigV4・VPC Lattice Auth Policy |
| **§2.3.A** | **非 AWS Internal の認証（GitHub Actions / mTLS / Vendor SaaS 等）** | **OIDC Federation / IRSA / mTLS / OAuth M2M / External ID / API Key legacy の 6 カテゴリ** |
| §2.4 | Authorizer 選定 | マネージド vs Lambda Authorizer の判断 |
| **§2.5** | **アプリ側認可モデル & ユーザオンボーディング** ⭐ | **Hybrid モデル（C）、JIT / SCIM / Invitation / Self-Service、Pattern 1/2/3、role→permission マッピング** |
| **§2.6** | **Permission ストレージの標準パターン** | **DynamoDB / Aurora スキーマ例、Cedar / Verified Permissions** |
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

#### Tier 戦略（2026-06-10 確定、Path C 採用）

`/oauth2/token` 露出リスクと Partner 規模・IdP 保有状況を踏まえ、tier 別の主流方式：

| Tier | 主流方式 | リファレンス章 | `/token` 露出 | 共有認証基盤との関係 |
|---|---|---|:---:|---|
| **Bronze**（Trial / SMB / 旧 Partner）| OAuth Client Credentials + API Key | **§2.2.7**（fallback リファレンス）| ✅ あり | 共有基盤で M2M Client 発行 |
| **Silver**（標準 B2B、Partner 自社 IdP 保有）⭐ | **Token Exchange (RFC 8693)** | **§2.2.8**（新規主流） | ✅ あり（subject_token を /token に送る）| 共有基盤を **信頼台帳 + token exchange ハブ**として |
| **Gold**（規制業界）| Silver + mTLS or PrivateLink | §2.2.3 C | ✅ あり（mTLS で輸送層保護）| 同上 |
| **将来 ADR**（長期）| **Federation B**（Multi-Issuer at API、Partner IdP token 直接受容）| **§2.2.9**（ADR placeholder） | ❌ なし | **認証側設計変更要**（[escalation-to-auth.md](../../escalation-to-auth.md)）|

**重要**：
- `/token` 露出は **Silver / Bronze では避けられない**（認証側 Identity Broker 単一 issuer 集約モデル前提）
- 代わりに **§2.2.10 Defense-in-depth 4 層** で多層防御
- 長期的に Federation B を認証側に提起することで露出ゼロを目指す

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

## §2.2.7 Partner 認証 詳細フロー：OAuth Client Credentials（Bronze fallback リファレンス）

> **位置付け（2026-06-10 改訂）**：**Bronze tier（Trial / SMB / Partner が自社 IdP 持たない場合）の fallback リファレンス実装**。Silver tier の主流は [§2.2.8 Token Exchange](#228-partner-認証-詳細フローtoken-exchange-rfc-8693silver-主流リファレンス) に移行。
> **適用シーン**：
> - Partner が OIDC IdP を持たない（SMB / Trial）
> - 既存 Partner で OAuth Client Credentials を採用済（互換性維持）
> - 単発 / 小規模 Partner 連携
> **対象読者**：Partner 開発者（Bronze tier）、本標準の Service Catalog 製品設計者、認証基盤側との合議メンバー。

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

## §2.2.8 Partner 認証 詳細フロー：Token Exchange (RFC 8693)（Silver 主流リファレンス）

> **位置付け（新規 2026-06-10）**：**Silver tier の主流リファレンス実装**。Partner が自社 OIDC IdP（Entra ID / Okta / Auth0 等）を保有する前提で、Partner IdP 発行 token を共有認証基盤の `/oauth2/token` で **Token Exchange (RFC 8693)** することで、本基盤発行 token を取得し API を呼ぶ。
> **認証側との整合**：認証側 [§FR-6.0.B / §FR-6.3 Knockout K-01](../../../requirements/proposal/fr/06-authz.md) で **Token Exchange は要件化済（Keycloak 必須化要因）**。本パターンは完全整合。
> **対象読者**：Partner 開発者（Silver tier）、本標準の Service Catalog 製品設計者、認証基盤側との合議メンバー。

### §2.2.8.1 なぜ Silver 主流が Token Exchange か

| 観点 | OAuth Client Credentials（§2.2.7）| Token Exchange（§2.2.8）|
|---|---|---|
| Partner 側のクレデンシャル管理 | **我々が Partner 用 secret を発行・配布** | **Partner が自社 IdP で完結**、我々は信頼台帳のみ |
| クレデンシャル漏洩時の対応 | 我々が secret 再発行 + Partner へ再配布 | Partner が自社 IdP で再発行、我々は介在しない |
| ローテーション運用負荷 | 我々が Partner に通知・配布 | **Partner 自社運用** |
| 認証側 §FR-6 との整合 | プロトコル要件のみ | **K-01 要件と完全整合**（Token Exchange は Keycloak 必須化要因）|
| 業界実例 | Salesforce Connected Apps | OIDC Federation, Auth0 multi-org, Curity |

→ **Partner が IdP 保有なら Token Exchange が運用負荷・セキュリティ責任分界・§FR-6 整合の 3 観点で有利**。

### §2.2.8.2 詳細フロー

```mermaid
sequenceDiagram
    participant P as Partner システム
    participant PIdP as Partner 社内 IdP<br/>(Entra/Okta/Auth0等)
    participant OurAuth as 共有認証基盤<br/>/oauth2/token
    participant Trust as 共有認証基盤<br/>信頼台帳
    participant CF as CloudFront + WAF
    participant API as 各アプリ API Gateway<br/>(IP allowlist あり)
    participant Authz as JWT Authorizer

    Note over P,PIdP: Step 1: Partner 内部で完結（我々の露出ゼロ）
    P->>PIdP: Client Credentials Grant<br/>(Partner 内部の client_id_partner)
    PIdP-->>P: access_token_partner<br/>(iss=partner-idp.com)

    Note over P,OurAuth: Step 2: Token Exchange（共有認証基盤 /token を呼ぶ）
    P->>CF: POST /oauth2/token<br/>grant_type=urn:ietf:params:oauth:grant-type:token-exchange<br/>subject_token=access_token_partner<br/>subject_token_type=urn:ietf:params:oauth:token-type:access_token
    CF->>OurAuth: WAF 通過後
    OurAuth->>Trust: iss=partner-idp.com は信頼台帳にある?
    Trust-->>OurAuth: YES + JWKS URL
    OurAuth->>PIdP: JWKS 取得（キャッシュ）
    OurAuth->>OurAuth: access_token_partner の<br/>署名・iss・aud・exp 検証
    OurAuth-->>P: access_token_ours<br/>(iss=our-auth.example.com, sub=partner-acme-mobile-prod)

    Note over P,API: Step 3: API 呼び出し（単一 issuer モデル維持）
    P->>API: Bearer access_token_ours
    API->>API: IP 制限 check (Partner egress IP?)
    API->>Authz: JWT Authorizer 起動
    Authz->>Authz: iss=our-auth.example.com のみ検証<br/>aud, exp, scope 検証
    Authz-->>API: Allow
    API-->>P: 200 OK
```

### §2.2.8.3 リクエスト・レスポンス具体例

#### A. Step 2: Token Exchange リクエスト

```http
POST /oauth2/token HTTP/1.1
Host: auth.example.com
Content-Type: application/x-www-form-urlencoded

grant_type=urn:ietf:params:oauth:grant-type:token-exchange
&subject_token=eyJraWQiOiI3M...（Partner IdP 発行 JWT）
&subject_token_type=urn:ietf:params:oauth:token-type:access_token
&audience=https://api.example.com
&scope=orders:read orders:write
```

#### B. Step 2: レスポンス

```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: no-store

{
  "access_token": "eyJraWQiOiJvdXItYXV0aC...（OUR auth 発行 JWT）",
  "issued_token_type": "urn:ietf:params:oauth:token-type:access_token",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "orders:read orders:write"
}
```

#### C. Our auth が発行する access_token_ours の JWT payload

```json
{
  "iss": "https://auth.example.com",
  "sub": "partner-acme-mobile-prod",
  "aud": "https://api.example.com",
  "exp": 1717689600,
  "iat": 1717686000,
  "scope": "orders:read orders:write",
  "tenant_id": "partner:acme-corp",
  "partner_idp": "partner-idp.com",
  "original_subject": "acme-mobile-prod@partner-idp.com"
}
```

→ **`partner_idp` クレームで「どの Partner IdP から来たか」を保持**、監査・課金按分に活用。

### §2.2.8.4 Partner IdP の登録（オンボーディング時）

Partner オンボーディング時、共有認証基盤の信頼台帳に以下を登録：

| 項目 | 説明 | 例 |
|---|---|---|
| `iss` | Partner IdP の issuer URL | `https://partner-idp.acme.com` |
| **JWKS URL** | Partner IdP の JWKS endpoint | `https://partner-idp.acme.com/.well-known/jwks.json` |
| 許可 audience | Partner IdP token の許可 `aud` | `acme-mobile-prod` |
| 許可 scope | exchange 後に付与する scope | `orders:read orders:write` |
| Partner Org ID | tenant_id にマップ | `partner:acme-corp` |
| 有効期限 | 信頼関係の有効期限 | 1 年（更新時に再確認）|

### §2.2.8.5 Partner IdP の要件（Partner 側責任）

Partner が以下を満たす必要がある：

- **OIDC 標準 IdP**（Entra ID / Okta / Auth0 / 自社運用 Keycloak など）
- **JWKS endpoint 公開**（HTTPS、定期キャッシュ可能）
- **`/oauth2/token` で Client Credentials Grant** をサポート
- **JWT 標準準拠**（RS256 / ES256 等の署名アルゴリズム）
- **`iss` / `aud` / `exp` / `iat` クレーム** を必ず含める
- **鍵ローテーション** を独自に運用（JWKS の `kid` ベース）

### §2.2.8.6 アンチパターン / 注意点

| ❌ アンチパターン | ✅ 正しいパターン |
|---|---|
| Partner IdP token を直接 API に投げる | **Step 2 の Token Exchange を必ず経由**（単一 issuer モデル維持）|
| `subject_token` の `iss` を信頼台帳でチェックしない | **信頼台帳ルックアップを必須**（任意 IdP の token を受容しない）|
| Partner IdP JWKS を毎回取得 | **キャッシュ（5-15 分）+ Cache-Control respect** |
| Partner IdP の鍵ローテーションを我々が管理 | **Partner 責任**、我々は JWKS キャッシュ削除で追従 |
| Token Exchange の `audience` パラメータを省略 | **必ず指定**（aud の意図しない混入を防ぐ）|
| 失効通知なし | **Partner IdP からの信頼撤回**（停止・契約終了）を信頼台帳から削除する API |

### §2.2.8.7 アクセスログでの識別

`access_token_ours` の JWT に **`partner_idp` クレーム**を含めることで、監査・課金按分で「どの Partner IdP 経由か」を識別：

| フィールド | 由来 |
|---|---|
| `clientId` | `sub` クレーム（partner-acme-mobile-prod）|
| `tenantId` | `tenant_id` クレーム（partner:acme-corp）|
| `partnerIdp` | `partner_idp` クレーム（partner-idp.com）|
| `originalSubject` | `original_subject` クレーム（acme-mobile-prod@partner-idp.com）|

### §2.2.8.8 §2.2.7 OAuth Client Credentials との使い分け

| シナリオ | 推奨方式 | 章 |
|---|---|---|
| Partner が OIDC IdP 保有（大企業 / Auth0 / Entra ID 等） | **Token Exchange** | §2.2.8 |
| Partner が IdP 持たない（SMB / Trial / 個人開発者）| OAuth Client Credentials | §2.2.7 |
| 既存 Partner で OAuth Client Credentials 採用済 | 互換性維持で OAuth | §2.2.7 |
| 規制業界（金融・医療）| Silver + mTLS 追加 | §2.2.3 C + §2.2.8 |

### §2.2.8.9 認証側との分担

| 役割 | 認証側（共有認証基盤）| 本標準（各アプリ）|
|---|:---:|:---:|
| Partner IdP 信頼台帳管理 | ✅ | – |
| Token Exchange エンドポイント提供 | ✅ §FR-6 既要件化 | – |
| Partner IdP JWKS 取得・キャッシュ | ✅ | – |
| `access_token_ours` 発行 | ✅ | – |
| `access_token_ours` 検証（API GW Authorizer） | – | ✅ |
| Partner egress IP allowlist | – | ✅ |

→ **本標準アプリは認証側の Token Exchange エンドポイントを利用する立場**、認証側に信頼台帳管理機能の正式要件化を申し送り（[escalation-to-auth.md §1.5](../../escalation-to-auth.md) 予定）。

---

## §2.2.9 Federation B：Multi-Issuer at API（長期 ADR placeholder）

> **位置付け（新規 2026-06-10）**：**長期戦略 ADR**。`/oauth2/token` 露出を完全に排除する究極形だが、**認証側現設計（Identity Broker 単一 issuer 集約モデル）と根本的に対立** するため、本標準では即時実装しない。
> **状態**：📋 ADR placeholder（[escalation-to-auth.md §1.7](../../escalation-to-auth.md) 予定）

### §2.2.9.1 Federation B の理想形

```
Partner システム → Partner 社内 IdP /token（内部完結）
                ↓ access_token_partner（iss=partner-idp.com）
                ↓
                CloudFront + WAF + API IP allowlist
                ↓
                API Gateway（Multi-Issuer Authorizer）
                ↓ iss=partner-idp.com の信頼台帳照合
                ↓ Partner IdP JWKS で署名検証
                Lambda / ECS
```

→ **共有認証基盤の `/oauth2/token` を経由しない**。Multi-Issuer at API 層が前提。

### §2.2.9.2 認証側設計との対立点

| 観点 | 認証側現状（§FR-2.1）| Federation B 要件 |
|---|---|---|
| 各アプリの JWT 検証 issuer 数 | **単一**（共有認証基盤の Broker）| **複数**（共有認証基盤 + 各 Partner IdP）|
| 信頼台帳の管理機能 | Implicit（Broker 内部に IdP 登録）| **明示的な API 提供必要**（Partner IdP の追加・削除・更新）|
| API Gateway / Lambda Authorizer | 単一 JWKS URL から JWKS 取得 | **複数 JWKS URL を `iss` に応じて切替**（Authorizer の大幅変更）|
| Identity Broker パターン | コア設計 | **崩壊する**（B2B 連携を Broker 経由しないため）|

→ 認証側の **ADR レベルの設計変更**が必要。本標準では長期 ADR として残し、認証側で議論を継続。

### §2.2.9.3 Federation B 実現に必要な認証側拡張

1. **Multi-Issuer Lambda Authorizer テンプレート**：`iss` ベースで JWKS routing
2. **Partner IdP 信頼台帳 API**：CRUD endpoint
3. **JWKS キャッシュ戦略の拡張**：複数 issuer URL を並列キャッシュ
4. **監査ログでの issuer 識別**：`iss=partner-idp.com` を audit field に
5. **失効通知メカニズム**：Partner IdP 撤回・契約終了時の信頼台帳更新

### §2.2.9.4 移行ロードマップ案（推進する場合）

| Phase | 内容 | スケジュール想定 |
|---|---|---|
| Phase 1（現在）| Token Exchange（§2.2.8）で Silver tier 標準化、API IP 制限で Defense-in-depth | 2026〜2027 |
| Phase 2 | 認証側 ADR 提起、Multi-Issuer Authorizer 実装の PoC | 2027〜2028 |
| Phase 3 | Federation B を Gold tier の選択肢として開放 | 2028〜 |
| Phase 4 | Federation B を Silver tier 主流化、Token Exchange は併存 | 2029〜 |

→ 認証側の意思決定次第。本標準では **Phase 1 を確実に運用**しながら Phase 2 以降を ADR として準備する。

### §2.2.9.5 関連項目への参照

- §2.2.8 Token Exchange（現実的な Silver 主流）
- §2.2.10 Defense-in-depth 4 層（Phase 1 の補強策）
- [escalation-to-auth.md §1.7（予定）](../../escalation-to-auth.md) — Federation B ADR 案
- 認証側 §FR-2.1 顧客 IdP 連携（拡張対象）
- 認証側 §FR-6.0.B Token Exchange（既要件化）

---

## §2.2.10 Defense-in-depth：4 層防御

> **位置付け（新規 2026-06-10）**：§2.2.7 / §2.2.8 のいずれを採用しても `/oauth2/token` 露出は避けられない。**Federation B 移行までの間（Phase 1）の現実的な多層防御戦略**を明示する。

### §2.2.10.1 リスク分類

| リスク | 内容 | 影響範囲 |
|---|---|---|
| **リスク 1** | クレデンシャル漏洩 → token 取得 → API 呼出 | 個別 Partner |
| **リスク 2** | `/oauth2/token` への DDoS | **共有基盤全体**（他テナント波及）|
| **リスク 3** | 共有基盤の他テナント（B2C / Internal）への cross 影響 | **共有基盤全体** |
| **リスク 4** | 認証基盤の 0-day 脆弱性 exploit | **共有基盤全体** |
| **リスク 5** | Partner 内部の悪意（insider threat）| 個別 Partner |

### §2.2.10.2 4 層防御マトリクス

| 層 | 防御策 | リスク 1 | リスク 2 | リスク 3 | リスク 4 | リスク 5 | 実装場所 |
|---|---|:---:|:---:|:---:|:---:|:---:|---|
| **層 1** | Dedicated Partner `/oauth2/token` + WAF + Rate-based + ATP equivalent | ✅ | ✅ | 部分 | 攻撃面縮小 | ❌ | 認証基盤側 |
| **層 2** | 認証基盤の Pool/Realm 分離（Partner 専用）| – | – | ✅ | – | – | 認証基盤側 |
| **層 3** | API Gateway IP allowlist（Partner egress IP のみ）| ✅ | – | – | – | ❌ | 本標準（各アプリ）|
| **層 4** | 監視・異常検知（cross-IP token use, replay, anomaly）| 検知 | 検知 | 検知 | 検知 | 検知 | 本標準 + 認証側 |

### §2.2.10.3 各層の具体実装

#### 層 1：Dedicated Partner `/oauth2/token` + WAF（認証基盤側）

```
[Internet]
   ↓
[CloudFront]              ← global WAF, edge cache
   ↓
[WAF v2]                  ← Managed Rules, Rate-based 100 req/5min/IP
   ↓                         + AWS WAF ATP (Account Takeover Prevention)
[Custom Domain]           ← partner-auth.example.com（内部 user 用と分離）
   ↓
[Internal ALB]            ← VPC 内のみ、internet 非公開
   ↓
[共有認証基盤 backend]
```

→ Partner 用 `/token` と Internal user 用 `/token` を **ホスト分離**。Internal user 用は VPC 内のみで完全保護。

→ 認証側に申し送り（[escalation-to-auth.md §1.6](../../escalation-to-auth.md)）。

#### 層 2：Pool / Realm 分離（認証基盤側）

| プラットフォーム | 分離手段 |
|---|---|
| **Cognito** | **Partner 専用 User Pool**（B2C/Internal とは別 Pool）|
| **Keycloak** | **Partner 専用 Realm**（B2C/Internal とは別 Realm）|

→ DB / Cache / Compute pool の物理分離まではしないが、論理境界を明確化。

→ 認証側に申し送り（[escalation-to-auth.md §1.6](../../escalation-to-auth.md)）。

#### 層 3：API Gateway IP allowlist（本標準）

```
[API Gateway / ALB]
   ↓
[WAF v2 + IPSet]
   ├─ Allow: Partner egress IPs（Acme: 1.2.3.0/24, Globex: 5.6.7.0/24, …）
   ├─ Allow: 内部監視 IP
   └─ Block: all others
   ↓
[Lambda / ECS]
```

→ Partner オンボーディング時に egress IP リスト取得・更新。

→ **これが層 1〜2 の補完防御として最重要**。漏洩クレデンシャルが Partner 外部から使われても API レベルで遮断。

#### 層 4：監視・異常検知

| 異常パターン | 検知方法 |
|---|---|
| Cross-IP token use（同一 token が複数 IP から）| CloudWatch Insights + アラート |
| /token への異常な request rate | CloudWatch metrics + WAF 連動 |
| Partner IdP 信頼台帳に登録されていない `iss` の token | Lambda Authorizer ログ |
| Token replay（同一 jti 複数回）| Lambda Authorizer + DynamoDB cache |

### §2.2.10.4 採用判断マトリクス

| Tier | 層 1 | 層 2 | 層 3 | 層 4 |
|---|:---:|:---:|:---:|:---:|
| **Bronze** | 必須 | 推奨 | 必須 | 必須 |
| **Silver** | 必須 | 必須 | 必須 | 必須 |
| **Gold** | 必須 | 必須 | 必須 + mTLS | 必須（強化）|

### §2.2.10.5 認証側に申し送る要件

- **層 1**：Dedicated Partner `/oauth2/token` + WAF + ATP 配置 → [escalation-to-auth.md §1.6](../../escalation-to-auth.md)
- **層 2**：Partner 専用 Pool/Realm 分離 → 同上
- **長期（Phase 2〜）**：Federation B Multi-Issuer 対応 ADR → [escalation-to-auth.md §1.7](../../escalation-to-auth.md)

---

## §2.3 IAM auth（AWS ネイティブ Internal / Private 向け）

**このサブセクションで定めること**：**AWS ネイティブ**な内部呼び出し元（Lambda / ECS / EC2 等の AWS リソース）の標準認証方式。
**主な判断軸**：マネージド・低レイテンシ・最小権限。
**§2 全体との関係**：社内 / 社内限定 Profile のデフォルト（AWS Principal を持つ呼び出し元）。**非 AWS Internal は [§2.3.A](#23a-非-aws-internal-の認証github-actions--mtls--vendor-saas-等)** で扱う。

### §2.3.1 ベースライン

- **SigV4 署名**を呼び出し元（Lambda / ECS task role / EC2 instance profile）が付与
- API Gateway 側：`AWS_IAM` authorization、Resource Policy で `aws:PrincipalOrgID` や VPC Endpoint ID で絞る
- **VPC Lattice**: Service ごとに Auth Policy（IAM ポリシー記述）で許可 Principal を定義。Service Connect だけでは IAM 認可は提供されないので、Lattice 採用が標準
- **Lambda Function URL**: `AuthType=AWS_IAM` で IAM 認可を有効化

### §2.3.2 TBD / 要確認

- Q: **社内 Profile の標準は IAM auth か JWT か**（既存アプリが JWT 前提なら混在許容）→ `API-B-221`
- Q: VPC Lattice 採用範囲（前述 §1.2 と整合）→ `API-B-106`（再掲）
- Q: Cross-account の IAM 信頼関係セットアップを **Service Catalog で配布する**か、各アプリ自前か → `API-B-222`

---

## §2.3.A 非 AWS Internal の認証（GitHub Actions / mTLS / Vendor SaaS 等）

**このサブセクションで定めること**：**AWS Principal を持たない**内部呼び出し元（CI/CD、on-prem、Vendor SaaS 等）の標準認証方式。
**主な判断軸**：呼び出し元の特性 × セキュリティ × 運用負荷。
**§2 全体との関係**：§2.3 の対面。社内 Profile の中で「AWS ネイティブでない」ケースを扱う。

### §2.3.A.1 「Internal 呼び出し元」の実態は 2 カテゴリ

| カテゴリ | 例 | AWS IAM 適用可？ |
|---|---|:---:|
| **A. AWS ネイティブ Internal**（§2.3 が対象）| Lambda / ECS / EC2 / EventBridge / S3 | ✅ SigV4 / Resource Policy / VPC Lattice |
| **B. 非 AWS Internal**（**本サブセクションが対象**）| GitHub Actions、社内 on-prem、Vendor SaaS、Kubernetes（社内 EKS 以外） | ❌ AWS Principal を持たない |

### §2.3.A.2 非 AWS Internal 呼び出し元別の推奨認証

| 呼び出し元 | 推奨認証方式 | 業界実例 / リファレンス |
|---|---|---|
| **GitHub Actions / GitLab CI / Bitbucket Pipelines** | **AWS OIDC Federation → STS AssumeRoleWithWebIdentity** ⭐ | [AWS 公式推奨 2022〜](https://aws.amazon.com/blogs/security/use-iam-roles-to-connect-github-actions-to-actions-in-aws/) |
| **Kubernetes / EKS pod** | **IRSA**（IAM Roles for Service Accounts） | [AWS マネージド標準](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html) |
| **on-prem サーバ（PKI あり）** | **mTLS**（社内 CA 発行証明書）| エンタープライズ標準 |
| **on-prem サーバ（PKI なし）** | **OAuth Client Credentials**（共有認証基盤、`internal:*` scope）| Partner Bronze（§2.2.7）と同じ仕組み |
| **Vendor SaaS（Datadog / Splunk / New Relic 等）** | **AWS Integration Role + External ID** | [AWS 公式：confused deputy 防止](https://docs.aws.amazon.com/IAM/latest/UserGuide/confused-deputy.html) |
| **レガシー on-prem（モダン認証非対応）** | **API Key + IP allowlist + WAF** | 移行期間限定（標準外、要例外承認）|

### §2.3.A.3 GitHub Actions OIDC Federation の詳細フロー

最も典型的な「非 AWS Internal」ケースとして CI/CD パイプラインの例：

```mermaid
sequenceDiagram
    participant GHA as GitHub Actions Workflow
    participant GH as GitHub OIDC Provider<br/>(token.actions.githubusercontent.com)
    participant STS as AWS STS
    participant IAM as AWS IAM Role<br/>(trust policy で GitHub OIDC を信頼)
    participant API as API Gateway / S3 / etc.

    GHA->>GH: OIDC token request<br/>(workflow context: repo/branch/job)
    GH-->>GHA: id_token（GitHub 発行 JWT）
    GHA->>STS: AssumeRoleWithWebIdentity<br/>+ id_token + role-arn
    STS->>STS: id_token 署名検証<br/>(GitHub JWKS)<br/>+ Trust Policy 評価<br/>(sub=repo:org/repo:ref:refs/heads/main 等)
    STS-->>GHA: 一時 AWS credentials<br/>(15 分〜1h TTL)
    GHA->>API: SigV4 署名でリクエスト
```

**特徴**：
- **永続シークレットなし**（AWS Access Key を GitHub Secrets に置かない）
- **自動ローテーション**（15 分〜1h で expire）
- **fine-grained 制御**（Workflow / repo / branch / environment ごとに role 別）
- **業界標準**（[AWS 公式推奨](https://aws.amazon.com/blogs/security/use-iam-roles-to-connect-github-actions-to-actions-in-aws/)、HashiCorp Vault も同パターン）

### §2.3.A.4 Vendor SaaS Integration の詳細（External ID）

```mermaid
flowchart LR
    Vendor[Datadog SaaS] -->|"AssumeRole API"| STS[AWS STS]
    STS -->|"Trust Policy 評価"| Check{External ID<br/>一致?}
    Check -->|"Yes"| Role[IAM Role for Vendor]
    Check -->|"No"| Reject[拒否]
    Role -->|"許可されたサービス"| API[CloudWatch / S3 etc.]
```

**External ID の意義**：
- Vendor 側で発行されるランダム文字列を Trust Policy に埋め込む
- **confused deputy 攻撃**を防ぐ（他顧客の Trust Policy を流用されない）
- Vendor 標準パターン（Datadog、Splunk、New Relic、Snyk 等）

### §2.3.A.5 on-prem PKI なしの場合：OAuth Client Credentials

PKI 持たない on-prem サーバ → AWS API：
- Partner Bronze（§2.2.7）と同じ仕組み
- 違いは：
  - scope が `internal:*`（Partner は `partner:*`）
  - audience が internal-api（Partner は partner-api）
  - 監視ダッシュボードが internal 系
  - 共有認証基盤の Pool/Realm 分離は **Partner 用とは別、内部用**

### §2.3.A.6 ベースライン採用方針

| 区分 | デフォルト推奨 |
|---|---|
| 新規 CI/CD パイプライン | **GitHub Actions OIDC（必須化）**、Access Key 直接埋め込み禁止 |
| 新規 Kubernetes（社内 EKS 以外） | **IRSA または OIDC Federation** |
| 既存 PKI ある on-prem | **mTLS が第一推奨**（既存資産活用）|
| 新規 on-prem（PKI なし）| **OAuth Client Credentials**（共有認証基盤利用） |
| Vendor SaaS 連携 | **External ID 必須化**（Trust Policy 標準テンプレで配布）|
| レガシー API Key 認証 | **移行期限 N ヶ月で削除**（標準外、要例外承認）|

### §2.3.A.7 TBD / 要確認

- Q: 非 AWS Internal 呼び出し元の **現状棚卸し**（GitHub Actions / SaaS / on-prem / レガシーの内訳）→ `API-A-115` ⭐
- Q: GitHub Actions / GitLab CI で **OIDC Federation 必須化**するか → `API-B-225`
- Q: on-prem 認証は **mTLS / OAuth どちらをデフォルト**にするか → `API-B-226`
- Q: Vendor SaaS の **External ID 必須化** スコープ → `API-B-227`
- Q: **レガシー API Key 認証**の許容範囲・移行期限 → `API-B-228`

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

## §2.5 アプリ側認可モデル & ユーザオンボーディング

**このサブセクションで定めること**：認証基盤から受け取った JWT クレームを、アプリ側で **「誰が・何をできるか」** の認可判定にどう繋げるか、および初回ユーザのアプリ DB 反映フロー。
**主な判断軸**：認証基盤の最小限クレーム設計（§FR-6.1.A Stage 1）と整合、業界主流の Hybrid モデル、JIT vs SCIM。
**§2 全体との関係**：§2.1 共有認証基盤連携で受け取る JWT を、実際に業務認可で活用する側のガイド。

### §2.5.1 認可情報の所在モデル（業界 3 パターン）

| Model | 認可情報の所在 | 採用される場面 |
|---|---|---|
| A. 中央集権 | 認証基盤 100% | 小規模 SaaS、シンプルアプリ |
| B. 分散 | アプリ DB 100% | レガシー、独立性重視 |
| **C. Hybrid** ⭐ | **粗粒度 role = 認証基盤、細粒度 permission = アプリ DB** | 業界主流（Auth0 / Cognito / Keycloak / Azure AD / Salesforce）|

### §2.5.2 本標準のデフォルト：Hybrid モデル（C）

**認証側の現状設計（[§FR-6.0.A 認可スタンス](../../../requirements/proposal/fr/06-authz.md)）と完全整合**：
> 「本基盤は最小限のクレーム発行、認可判定は各アプリ」

#### 役割分担

| 情報 | 所有者 | 流通方法 |
|---|---|---|
| `sub` / `iss` / `aud` / `exp` | 認証基盤 | JWT クレーム（必須） |
| `tenant_id` | 認証基盤 | JWT クレーム（B2B SaaS では必須）|
| `roles` / `groups`（粗粒度ロール） | 認証基盤 | JWT クレーム（オプション、要件次第） |
| `email` | 認証基盤 | JWT クレーム or userinfo endpoint（PII 配慮） |
| **アプリ固有 permission**（resource-level、action-level） | **アプリ DB** | アプリ自前管理 |
| **アプリ固有設定**（preference / onboarding 状態） | **アプリ DB** | アプリ自前管理 |
| 業務ログ | アプリ | アプリ自前 |

→ **「認証基盤は事実を渡す、アプリが解釈する」**（[認証側 authz-architecture-design.md §3](../../../common/authz-architecture-design.md)）

### §2.5.3 認可実装の 3 パターン

JWT クレームをアプリでどう使うか、規模・複雑度別に：

| Pattern | 仕組み | 適用 |
|---|---|---|
| **Pattern 1：JWT クレーム単独** | `if 'orders:write' in jwt.scope: ...` | 軽量、低レイテンシ、scope のみで完結 |
| **Pattern 2：JWT + アプリ DB** ⭐ | 粗粒度は JWT、細粒度は DB lookup | **業界主流**、Hybrid の標準実装 |
| **Pattern 3：Policy Engine**（Cedar / OPA）| Verified Permissions / OPA に判定委譲 | 大規模、policy-as-code、変更頻繁時 |

→ デフォルト：**Pattern 2**、escalation：Pattern 3（AWS Verified Permissions / Cedar）。

### §2.5.4 初回ログイン時のオンボーディングフロー（JIT パターン）

```mermaid
sequenceDiagram
    participant U as ユーザ
    participant IdP as 顧客 IdP
    participant Auth as 共有認証基盤
    participant APIGW as API Gateway
    participant Authz as JWT Authorizer
    participant App as アプリ
    participant DB as アプリ DB

    Note over U,IdP: SSO 認証
    U->>IdP: 認証
    IdP->>Auth: SAML / OIDC federation
    Auth->>Auth: 顧客 IdP claims → tenant_id / roles マッピング<br/>(認証側 §FR-2.3 / §FR-2.2)
    Auth-->>U: JWT (sub, tenant_id, roles)

    Note over U,App: アプリ API 呼び出し
    U->>APIGW: Bearer JWT
    APIGW->>Authz: 検証
    Authz-->>APIGW: Allow + claims を context に
    APIGW->>App: invoke + claims

    Note over App,DB: ★ オンボーディング判定
    App->>App: 必須検証：JWT iss/aud/exp + tenant_id 突合
    App->>DB: SELECT user WHERE user_id = sub

    alt 初回（レコードなし）
        App->>App: JIT user 作成
        App->>DB: INSERT users (sub, tenant_id, auth_roles)
        App->>DB: INSERT user_permissions<br/>(role→permission マッピングテーブル参照)
        Note over App: 任意：プロフィール完成画面
        App-->>U: 200（初回フラグ）
    else 既存
        App->>DB: SELECT permissions
        App->>App: permission check
        App-->>U: 200 / 403
    end
```

### §2.5.5 アプリ側で必須となる処理

認証側が「最小限」のため、**以下はアプリで補完必須**（[認証側 §FR-6 / authz-architecture-design.md §6](../../../common/authz-architecture-design.md)）：

| # | 処理 | 説明 | 実装位置 |
|---|---|---|---|
| 1 | **JWT 署名検証 + iss/aud/exp 検証** | JWKS で署名検証、iss が信頼する認証基盤か、aud が自アプリか、未期限切れか | API Gateway Authorizer（マネージド or Lambda）|
| 2 | **テナント境界チェック** | リクエスト path/body の `tenant_id` と JWT.tenant_id 突合、異なれば 403（IDOR 防止） | アプリの認可関数 |
| 3 | **role → permission マッピング** | アプリ独自テーブル（GROUP_TO_ROLE 等）で groups → app permission に変換 | アプリ middleware |
| 4 | **細粒度 permission 判定** | resource-level / action-level の認可、アプリ DB の user_permissions と request の突合 | アプリ業務ロジック |
| 5 | **JIT ユーザ作成**（初回ログイン時） | sub が DB にない → 自動作成 + デフォルト permission 付与 | アプリ |
| 6 | **監査ログ** | 誰が何にアクセスしたか（業務イベント） | アプリ |

### §2.5.6 ユーザプロビジョニングの 4 パターン

| Pattern | 仕組み | 適用 |
|---|---|---|
| **A. JIT（Just-In-Time）**⭐ | 初回ログイン時に自動作成 | **業界主流、本標準デフォルト** |
| B. SCIM 同期 | 顧客 IdP → 認証基盤 → アプリ Webhook | 大規模 / 退職即時削除要件 |
| C. Invitation Flow | 管理者が事前にユーザ追加 + 招待リンク | B2B SaaS、細粒度初期権限 |
| D. Self-Service Sign-up | ユーザが自分でサインアップ | B2C、Trial |

→ **本標準デフォルト：JIT**、SCIM は退職追従が法令要件なら escalation。

### §2.5.7 SCIM 採用判断

| シナリオ | SCIM 要否 |
|---|:---:|
| 退職者を **即座に全アプリから削除**（SOC 2 / 金融コンプラ）| ✅ 必須 |
| 顧客 IdP 側だけでユーザ管理完結したい | ✅ 必須 |
| 大規模顧客（数万ユーザ）の **バルク同期** | ✅ 推奨 |
| 退職追従は **次回ログイン時に無効化で OK**（JWT TTL 短い）| ❌ 不要 |
| ユーザ規模が小〜中（数百〜数千）| ❌ JIT で十分 |

#### SCIM 採用時のフロー

```mermaid
sequenceDiagram
    participant CIdP as 顧客 IdP
    participant Auth as 共有認証基盤
    participant Hook as SCIM Webhook
    participant App as アプリ

    CIdP->>Auth: SCIM PUSH<br/>(/Users CRUD)
    Auth->>Auth: 内部 user 台帳更新
    Auth->>Hook: User lifecycle event
    Hook->>App: Webhook (POST /webhooks/scim)
    App->>App: アプリ DB の user 更新<br/>(削除 → user_permissions も無効化)
```

**実装場所**：
- **認証側**：顧客 IdP からの SCIM 受信（§FR-7 / §FR-2.3）
- **本標準アプリ**：認証基盤からの Webhook 受信エンドポイント

### §2.5.8 デフォルト permission マッピング規約（推奨）

認証基盤 role → アプリ permission の初期マッピング標準：

| Auth Role | デフォルト App Permission |
|---|---|
| `admin` | 全アクション許可 |
| `manager` | 配下 user の管理 + 業務 read/write |
| `user` | 自己リソースの read/write、業務 read |
| `viewer` | read-only |
| 未指定 | viewer 相当 |

→ アプリは初期化時にこのマッピングを使う、その後**アプリ DB で個別調整**（cluster の admin に対して特定 permission を剥奪する等）。

### §2.5.9 TBD / 要確認

- Q: アプリ側認可は **JWT クレーム単独 / JWT + アプリ DB / Policy Engine** のどれをデフォルトとするか → `API-B-244` 🔥
- Q: ユーザプロビジョニング標準（JIT / SCIM / Invitation / Self-Service）の **使い分け基準** → `API-B-245` 🔥
- Q: **退職者の即時削除要件**（SCIM 必須化 vs 次回ログイン無効化で OK）→ `API-B-246`
- Q: 認証基盤 roles → アプリ permissions の **マッピング規約**（標準テンプレ提供か、アプリ判断か）→ `API-B-247`
- Q: 初回ログイン時の **プロフィール完成 UX 必須化**スコープ → `API-B-248`
- Q: **AWS Verified Permissions / Cedar** を本標準のデフォルトに含めるか（escalation 扱い）→ `API-D-245`

---

## §2.6 Permission ストレージの標準パターン

**このサブセクションで定めること**：§2.5 で扱う「アプリ DB に持つ permission」の具体的なデータモデル標準。
**主な判断軸**：実装ランタイム（Lambda / ECS）、DB 選定（DynamoDB / Aurora）、規模、変更頻度。
**§2 全体との関係**：§2.5 の実装詳細レベル。

### §2.6.1 標準スキーマ（DynamoDB パターン）⭐

**Lambda + DynamoDB の場合の推奨スキーマ**：

```
Table: users
  PK: user_id (= JWT sub)
  Attrs:
    - tenant_id           (= JWT tenant_id)
    - auth_roles          (= JWT roles snapshot)
    - app_permissions     (List<String>)  ← アプリ固有 permission
    - preferences         (Map)
    - onboarding_completed (Bool)
    - created_at, last_login_at
    - status: active|suspended|deleted

Table: user_permissions（GSI で role-based 検索）
  PK: user_id
  SK: permission_key (例: "order:write", "report:read")
  Attrs:
    - granted_at
    - granted_by         (admin user_id)
    - expires_at         (optional, time-limited)
    - source             (jit_default | manual | scim_sync)

  GSI: by_tenant
    PK: tenant_id
    SK: permission_key  ← テナント全体の permission サマリ
```

### §2.6.2 標準スキーマ（Aurora パターン）

**ECS + Aurora の場合の推奨 RDB スキーマ**：

```sql
CREATE TABLE users (
  user_id VARCHAR(64) PRIMARY KEY,        -- JWT sub
  tenant_id VARCHAR(64) NOT NULL,         -- JWT tenant_id
  auth_roles JSONB,                       -- JWT roles snapshot
  email VARCHAR(255),                     -- optional, PII 配慮
  status VARCHAR(20) DEFAULT 'active',    -- active|suspended|deleted
  onboarding_completed BOOLEAN DEFAULT FALSE,
  preferences JSONB,
  created_at TIMESTAMP DEFAULT NOW(),
  last_login_at TIMESTAMP,
  INDEX idx_tenant (tenant_id)
);

CREATE TABLE user_permissions (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(64) REFERENCES users(user_id),
  permission_key VARCHAR(128) NOT NULL,
  granted_at TIMESTAMP DEFAULT NOW(),
  granted_by VARCHAR(64),
  expires_at TIMESTAMP,                   -- optional time-limited
  source VARCHAR(20) DEFAULT 'manual',    -- jit_default|manual|scim_sync
  UNIQUE (user_id, permission_key)
);

CREATE TABLE role_permission_mappings (
  role_name VARCHAR(64) NOT NULL,
  permission_key VARCHAR(128) NOT NULL,
  tenant_id VARCHAR(64),                   -- NULL = global, otherwise tenant-specific
  PRIMARY KEY (role_name, permission_key, tenant_id)
);
```

### §2.6.3 アクセスパターン例

#### 認可判定（高頻度）
```sql
-- アプリ middleware で呼ぶ
SELECT permission_key FROM user_permissions
WHERE user_id = $jwt_sub
  AND (expires_at IS NULL OR expires_at > NOW());
```

→ **キャッシュ推奨**（5-15 分、認可変更を即反映したいなら 1 分）

#### JIT 初回ユーザ作成
```sql
BEGIN;
INSERT INTO users (user_id, tenant_id, auth_roles)
  VALUES ($jwt_sub, $jwt_tenant_id, $jwt_roles);
INSERT INTO user_permissions (user_id, permission_key, source)
  SELECT $jwt_sub, permission_key, 'jit_default'
  FROM role_permission_mappings
  WHERE role_name = ANY($jwt_roles)
    AND (tenant_id IS NULL OR tenant_id = $jwt_tenant_id);
COMMIT;
```

#### SCIM 削除
```sql
UPDATE users SET status = 'deleted', deleted_at = NOW()
  WHERE user_id = $scim_user_id;
DELETE FROM user_permissions WHERE user_id = $scim_user_id;
```

### §2.6.4 Cedar / Verified Permissions パターン（Pattern 3 採用時）

```
AWS Verified Permissions:
  Policy Store: per-tenant or shared
  Schema:
    - Principal: User { user_id, tenant_id, roles }
    - Resource: Order { order_id, owner_id, tenant_id }
    - Action: ViewOrder, EditOrder, DeleteOrder

  Sample Policy:
    permit (principal, action == EditOrder, resource)
    when {
      principal.tenant_id == resource.tenant_id
      && (principal in [Role::"admin"]
          || principal == resource.owner)
    };
```

→ Cedar を採用すると、アプリは policy-as-code で宣言的に認可記述可。学習コストはあるが大規模で有効。

### §2.6.5 TBD / 要確認

- Q: 標準 DB（DynamoDB / Aurora）の **デフォルト選定** → `API-B-521`（既存）と整合
- Q: Permission のキャッシュ戦略 → `API-B-242` Lambda Authorizer cache と一体化
- Q: Cedar / Verified Permissions の **採用判断基準**（規模、複雑度）→ `API-D-245`

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
