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

公開境界（§1）が決まると、**境界ごとに利用可能な認証方式が絞られる**。本章では各境界に対応する標準パターンを定める：

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
| §2.2 | API Key と mTLS（Partner 向け） | API Key 体系・Custom Domain mTLS |
| §2.3 | IAM auth（Internal/Private 向け） | SigV4・VPC Lattice Auth Policy |
| §2.4 | Authorizer 選定 | マネージド vs Lambda Authorizer の判断 |

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

## §2.2 API Key と mTLS（Partner 向け）

**このサブセクションで定めること**：B2B 接続で利用者識別と通信暗号化を強化する手段。
**主な判断軸**：API Key は識別目的、mTLS は対象クライアントの強固な認証目的。
**§2 全体との関係**：Partner 区分での標準。§3 流量制御・§4 課金とセットで運用。

### §2.2.1 ベースライン

- **API Key**：
  - 使う目的は **利用者識別 + Usage Plan による流量制御**（§3 / §4 と一体）
  - API Key 単独で認証扱いしない。**必ず Authorizer を併用**（IAM auth or JWT or 受領後の検証ロジック）
  - 発行は AWS Console / IaC（Terraform / CDK）。**配布は Secrets Manager または別経路の secure transfer**
  - ローテーション規定（標準：90 日 / 180 日 / 1 年）は §NFR-API-4 セキュリティで定義
- **mTLS**：
  - API Gateway REST + **Custom Domain で mTLS サポート**（HTTP API は限定対応）
  - Truststore は S3 にクライアント CA バンドル
  - クライアント識別は `$context.identity.clientCert.subjectDN` 等のクレームを Authorizer で評価
  - 証明書ローテーション・失効リスト（CRL）運用が必要

### §2.2.2 TBD / 要確認

- Q: **Partner 区分のデフォルトは API Key + WAF か、mTLS か**（mTLS は強固だが運用負荷高い）→ `API-B-211`
- Q: API Key の有効期限・ローテーションポリシー → `API-B-212`
- Q: mTLS の **証明書発行・配布元**（自社 PKI / AWS Private CA / Partner 側 CA）→ `API-B-213`

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

- [§FR-API-1 公開境界](01-exposure-boundary.md) — 境界別の認証方式マッピング
- [§FR-API-3 流量制御](03-throttling-quota.md) — API Key と Usage Plan の関係
- [§FR-API-4 課金](04-metering-billing.md) — 利用者識別子（API Key・JWT sub）の活用
- [§FR-API-6 §6.1.A モノリス vs マイクロサービス](06-container-standard.md) — モノリス採用時の認証設計
- [§C-API-3 共有認証基盤との接続点](../common/03-shared-auth-boundary.md) — 認証基盤側 SSOT との境界整理
