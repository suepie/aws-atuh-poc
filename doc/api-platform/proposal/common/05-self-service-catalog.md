# §C-API-5 標準提供物（Service Catalog / IaC モジュール）

> 親 SSOT: [../00-index.md](../00-index.md) §C-API-5
> ヒアリング: [../../hearing-script/07-guardrails.md](../../hearing-script/07-guardrails.md)

---

## §C-5.0 前提と背景

### §C-5.0.1 用語整理

| 用語 | 定義 |
|---|---|
| **Service Catalog** | AWS Service Catalog。組織内で承認済み AWS 製品（IaC スタック）を配布するサービス |
| **製品（Product）** | Service Catalog で配布される 1 つのテンプレート（CloudFormation / Terraform） |
| **IaC モジュール** | 再利用可能な Infrastructure-as-Code 部品（CDK Construct / Terraform Module） |
| **開発者ポータル** | アプリ開発者向けの API カタログ・ドキュメント・サンプル提示 UI |

### §C-5.0.2 なぜここ（§C-5）で決めるか

要望テーマの「**効率よく**」の中核。本標準を **「ドキュメント」だけで提供すると形骸化する**。Service Catalog / IaC モジュールという **配布可能な形** に落とすことで、開発者が標準に従うのが自然な選択肢になる。

```mermaid
flowchart LR
    Doc[本標準ドキュメント] -->|変換| IaC[IaC モジュール<br/>CDK / Terraform]
    IaC --> Catalog[Service Catalog 製品]
    Catalog -->|配布| Apps[各アプリアカウント]
    Apps -->|self-service launch| Stack[標準準拠スタック]
```

### §C-5.0.3 §C-5.0.A 本標準のスタンス

| 基本方針 | 本章での具体化 |
|---|---|
| 絶対安全 | 製品起動時点で **セキュリティ死守事項**（暗号化・タグ・ログ）が自動充足 |
| どんなアプリでも | カテゴリ別の製品ラインナップ（公開範囲 × ランタイム の組合せ） |
| 効率よく | アプリ開発者が **数クリック / IaC 一行** で標準準拠スタック起動 |
| 運用負荷・コスト最小 | 製品の更新・バージョン管理は Platform チーム集約 |

### §C-5.0.4 本章で扱うサブセクション

| § | サブセクション |
|---|---|
| §C-5.1 | 製品ラインナップ |
| §C-5.2 | IaC モジュール体系 |
| §C-5.3 | バージョン管理・更新通知 |
| §C-5.4 | 開発者ポータル |

---

## §C-5.1 製品ラインナップ

**このサブセクションで定めること**：Service Catalog Portfolio で提供する標準製品。
**主な判断軸**：公開範囲 × ランタイムの代表的な組合せ、過剰な細分化を避ける。
**§C-5 全体との関係**：§FR-API-1〜6 の出口。

### §C-5.1.1 ベースライン

| 製品名（暫定） | 構成 | 想定アプリ |
|---|---|---|
| `api-gateway-http-public-lambda-dynamodb` | CloudFront + WAF + HTTP API + JWT Authorizer + Lambda + DynamoDB | B2C 公開 API |
| `api-gateway-rest-partner-lambda` | REST API + Custom Domain + Usage Plan + WAF + Lambda | B2B 課金 API |
| `api-gateway-private-internal-lambda` | Private API + Lambda + Resource Policy | 社内マイクロサービス |
| `lambda-function-url-internal` | Function URL + IAM auth | Webhook / 内部 |
| `ecs-fargate-public-alb` | CloudFront + WAF + ALB + ECS Fargate | B2C コンテナ |
| `ecs-fargate-internal-lattice` | VPC Lattice + ECS Fargate + Service Connect | クロスアカウント内部 API |
| `ecs-fargate-partner-alb-mtls` | ALB + mTLS + WAF + ECS Fargate | B2B mTLS |
| `appsync-graphql-public` | AppSync + Cognito Authorizer + DynamoDB | GraphQL / モバイル |

各製品には必須要素を組み込み済：
- 必須タグセット（§FR-API-4 §4.3）
- CloudWatch Log Group + Retention + CMK
- ADOT / X-Ray 有効化
- アラート（標準セット）
- IAM 最小権限ロール
- ⭐ **Authorizer 必須化**（[§FR-API-2 §2.8 Fail-closed 原則](../fr/02-authn-authz.md)）：
  - 全 API Gateway 製品テンプレで **Authorizer フィールド必須**（IAM / JWT / Lambda / Cognito、`AuthType=NONE` 不可）
  - ALB ベースの製品テンプレで **認証統合 or アプリ middleware 認証タグ必須**
  - Lambda Function URL 採用製品は `AuthType=AWS_IAM` 必須
  - IaC validation hook（cfn-guard / CDK Aspect 等）で deploy 前に強制

→ **アプリ開発者が「認証なし API」を Service Catalog 経由で作れない構造**を製品テンプレレベルで担保。例外は別途申請制（[§FR-API-2 §2.8.3](../fr/02-authn-authz.md)）。

### §C-5.1.2 TBD / 要確認

- Q: **初期ラインナップ**を上記 8 種類で確定するか → `API-D-2201`
- Q: 各製品の **対応リージョン**（東京 / 大阪両対応か） → `API-D-2202`
- Q: Authorizer 強制の IaC validation hook 実装（cfn-guard / CDK Aspect / OPA）→ `API-B-251`（§FR-API-2 §2.8 と同じ）

---

## §C-5.2 IaC モジュール体系

**このサブセクションで定めること**：Service Catalog 製品の元となる IaC モジュールの体系。
**主な判断軸**：再利用性、テスト可能性、CDK / Terraform の選定。
**§C-5 全体との関係**：§C-5.1 の実装基盤。

### §C-5.2.1 ベースライン

- **IaC 言語**：CDK（TypeScript / Python）を第一推奨、Terraform は既存資産との整合性次第
- **モジュール階層**：
  - Level 1: AWS リソース直接（CDK L1）
  - Level 2: 共通パターン（CDK L2、AWS 標準）
  - Level 3: 本標準の独自 Construct（必須タグ・ログ・モニタリングセット）
  - Level 4: 製品テンプレ（§C-5.1 の製品をまとめたもの）
- **配布**：内部 npm / PyPI / GitHub Packages
- **テスト**：CDK assertions / Terraform plan diff、CI で自動実行

### §C-5.2.2 TBD / 要確認

- Q: **CDK vs Terraform の社内推奨**確定 → `API-C-2211`
- Q: 既存資産が **CloudFormation のみ**のアプリへの対応 → `API-C-2212`

---

## §C-5.3 バージョン管理・更新通知

**このサブセクションで定めること**：製品・モジュールのバージョン管理ルール。
**主な判断軸**：Semantic Versioning、Breaking change の通知期間。
**§C-5 全体との関係**：§NFR-API-9 互換性と相似。

### §C-5.3.1 ベースライン

- **SemVer 採用**（major.minor.patch）
- **Breaking change（major）**：30 日前通知、旧バージョン製品も併存
- **新機能（minor）**：通知のみ
- **バグ修正（patch）**：自動更新（Critical のみ）
- **製品の Lifecycle**：Active / Deprecated / Sunset
- **通知**：changelog + Slack + メール

### §C-5.3.2 TBD / 要確認

- Q: 旧バージョン製品の **併存期間**（6 ヶ月 / 12 ヶ月）→ `API-C-2221`
- Q: アプリ側の **アップデート義務**（minor / major で異なる）→ `API-C-2222`

---

## §C-5.4 開発者ポータル

**このサブセクションで定めること**：アプリ開発者向けの API カタログ・サンプル・ドキュメント提示。
**主な判断軸**：self-service の実効性、検索性。
**§C-5 全体との関係**：本標準の出口の UX。

### §C-5.4.1 ベースライン

- **API カタログ**：OpenAPI 仕様書を公開（社内向け / Partner 向け別）
- **製品カタログ**：Service Catalog UI（標準）または社内開発者ポータル
- **サンプルコード**：GitHub 内 リファレンス実装リポジトリ
- **ドキュメント**：本標準（doc/api-platform/）+ Confluence / Notion / mkdocs

### §C-5.4.2 TBD / 要確認

- Q: 開発者ポータルの **構築範囲**（Service Catalog UI のみで足りるか、Backstage 等の追加プラットフォーム要件か）→ `API-D-2241`
- Q: OpenAPI 公開の **必須化範囲** → `API-C-1702`（§NFR-API-9 と同じ）

---

## §C-5.x 関連ドキュメント

- [§FR-API-7 ガードレール](../fr/07-guardrails.md) — Service Catalog 配信
- [§C-API-1 全体参照アーキ](01-reference-architecture.md) — 製品が実装する構成
- [reference-implementations.md（付録）](../../) — 参考実装スニペット（TBD）
