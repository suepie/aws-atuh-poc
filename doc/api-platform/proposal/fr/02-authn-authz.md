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
**§2 全体との関係**：Partner 区分での標準。§3 流量制御・§4 課金とセットで運用。

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
    Q1{Partner B2B M2M\n連携の現状 or 想定\nあり?}
    Q1 -->|No (両方なし)| Skip[§2.2 全体スキップ\nPartner 区分は §1.1 で定義のみ残す]
    Q1 -->|Yes (現状あり or 将来想定)| Q2{要件規模は?}
    Q2 -->|単発 / 小規模| Lite[§2.2.1〜§2.2.5 軽量版\nAPI Key + Usage Plan で当面対応]
    Q2 -->|複数 Partner / 継続| Full[§2.2.1〜§2.2.6 フル適用\nOAuth Client Credentials デフォルト]

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
