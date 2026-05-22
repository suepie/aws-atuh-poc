# §FR-API-5 標準アーキテクチャ：Serverless（API GW + Lambda）

> 親 SSOT: [../00-index.md](../00-index.md) §FR-API-5
> ヒアリング: [../../hearing-script/05-serverless-standard.md](../../hearing-script/05-serverless-standard.md)

---

## §5.0 前提と背景

### §5.0.1 用語整理

| 用語 | 定義 |
|---|---|
| **Serverless（本書での定義）** | 実行時間課金・自動スケールのマネージド実行環境を指す。中核は **API Gateway + Lambda** |
| **Cold start** | Lambda 等で関数インスタンスが新規起動する際の遅延 |
| **Function URL** | Lambda に HTTPS endpoint を API Gateway 無しで直接付ける機能 |
| **AppSync** | GraphQL（クエリ・mutation・subscription）のマネージドサーバ |

### §5.0.2 なぜここ（§5）で決めるか

本標準は **「Serverless / Container の 2 系統並行カタログ」** を採用する。本章は Serverless 側の標準を定義する：

- どんな API は Serverless にすべきか（→ §C-API-2 選定基準）
- 採用したら何をどう組むか（本章）
- 落とし穴と回避策

Container 側は §FR-API-6 で別建てとし、選択肢として共存する。

### §5.0.3 §5.0.A 本標準のスタンス

| 基本方針 | 本章での具体化 |
|---|---|
| 絶対安全 | VPC アクセスは ENI in private subnet、IAM 最小権限、Secrets Manager で資格情報 |
| どんなアプリでも | API Gateway + Lambda を基本形、Function URL は限定用途（Webhook / 内部）、AppSync は GraphQL/Subscription 要件時 |
| 効率よく | **AWS Lambda Powertools** をデファクト、SAM/CDK の IaC テンプレ提供 |
| 運用負荷・コスト最小 | Provisioned Concurrency は明確な要件があるときのみ。固定費を抑える |

### §5.0.4 本章で扱うサブセクション

| § | サブセクション | 主題 |
|---|---|---|
| §5.1 | API Gateway の標準設定 | HTTP API / REST API の使い分け、共通設定 |
| §5.2 | Lambda の標準設定 | ランタイム / メモリ / 同時実行 / VPC / Powertools |
| §5.3 | データアクセス | DynamoDB / Aurora Serverless v2 / RDS Proxy |
| §5.4 | イベント駆動・非同期 | SQS / SNS / EventBridge / Step Functions |
| §5.5 | Function URL / AppSync の位置づけ | 補完的な選択肢 |

---

## §5.1 API Gateway の標準設定

**このサブセクションで定めること**：API Gateway の HTTP/REST 使い分けと共通設定。
**主な判断軸**：コスト・機能要件（Usage Plan/API Key）・公開境界（Private endpoint 要否）。
**§5 全体との関係**：本サブセクションが Serverless の入口の標準。

### §5.1.1 ベースライン

| 観点 | HTTP API | REST API |
|---|---|---|
| **コスト** | 約 71% 安価（マネージド料金が低い） | 高 |
| **レイテンシ** | 低 | 中 |
| **Usage Plan / API Key** | ❌ 非対応 | ✅ |
| **Private endpoint** | ⚠ VPC Link 経由のみ | ✅ ネイティブ |
| **mTLS** | ⚠ 一部 | ✅ |
| **JWT Authorizer** | ✅ ネイティブ | ⚠ Cognito or Lambda |
| **WAF** | ✅（2025 サポート開始） | ✅ |
| **デフォルト推奨** | **B2C / 内部 API のデフォルト** | **B2B / 課金 / Private endpoint 要件時** |

- **共通必須**：
  - カスタムドメイン + ACM 証明書（`*.execute-api.*` 直叩きは本番禁止）
  - access log（JSON 形式）有効化、CloudWatch Logs に CMK 暗号化
  - X-Ray Tracing（or ADOT）有効化
  - CORS は明示設定（`*` 禁止）

### §5.1.2 TBD / 要確認

- Q: **デフォルト選定の基準**：原則 HTTP API、Usage Plan 必要時のみ REST API、で固定するか → `API-B-501`
- Q: **Edge-optimized エンドポイント**は標準で使うか（CloudFront を別途置く方式が推奨されているため、本標準では Regional + CloudFront 前段を既定にするか）→ `API-B-502`

---

## §5.2 Lambda の標準設定

**このサブセクションで定めること**：Lambda 関数の標準ランタイム・メモリ・タイムアウト・VPC 設定。
**主な判断軸**：コスト・コールドスタート・運用統一性。
**§5 全体との関係**：本サブセクションが Serverless のコア。

### §5.2.1 ベースライン

| 項目 | 標準 / 既定 | 補足 |
|---|---|---|
| **ランタイム** | Python 3.13 / Node.js 22 / Go 1.x / Java 21 | LTS / 非 Deprecation 必須 |
| **メモリ** | 512 MB（CPU は メモリと比例） | プロファイリングで調整 |
| **タイムアウト** | 30 秒（API GW 同期上限と整合）<br/>非同期は 15 分まで | |
| **同時実行** | 既定（Reserved Concurrency 任意） | テナント分離が要件なら Reserved を分ける |
| **Provisioned Concurrency** | 既定 0 | コールドスタート要件時のみ、固定費明示 |
| **VPC** | 必要時のみ（DB アクセス等） | ENI 起動オーバヘッドは 2019 改善以降軽微 |
| **Powertools** | **全関数で必須**（Logger / Tracer / Metrics） | サイレント `print` 禁止 |
| **環境変数** | 通常設定のみ。シークレットは Secrets Manager / SSM Parameter Store | KMS 暗号化 |
| **アーキテクチャ** | **arm64 (Graviton2) を推奨**（20% コスト減） | 互換性確認の上 |
| **SnapStart** | Java / .NET / Python は要件時に有効化（2024 拡張） | |

### §5.2.2 TBD / 要確認

- Q: **ランタイムの社内推奨優先順位**（Python / Node.js / Go / Java いずれが第一推奨か）→ `API-B-511`
- Q: **arm64 を新規 default 化するか**（既存資産との混在許容）→ `API-B-512`
- Q: Lambda extension（OTel Collector / Secrets Manager extension 等）の **標準セット**を Service Catalog で提供するか → `API-B-513`

---

## §5.3 データアクセス

**このサブセクションで定めること**：Lambda から DB へのアクセスパターン標準。
**主な判断軸**：コネクション数制約・コスト・既存資産。
**§5 全体との関係**：API バックエンドの非選択的要素。

### §5.3.1 ベースライン

| DB | 推奨アクセス方式 | 補足 |
|---|---|---|
| **DynamoDB** | SDK 直接 | サーバレス親和性最高。アクセスパターン先決め |
| **Aurora Serverless v2** | RDS Proxy or 直接 | **min ACU = 0**（MySQL 3.08+、2025） |
| **Aurora プロビジョン / RDS** | **RDS Proxy 経由必須** | Lambda の short-lived connection 対策 |
| **OpenSearch** | SDK / RestHighLevelClient | VPC アクセス時は ENI 必要 |

- **Aurora Serverless v2 + RDS Proxy** は **コスト二重化に注意**（min ACU=0 効果を Proxy 固定費が相殺するケース多発）
- **シークレット**：Secrets Manager + 自動ローテーション

### §5.3.2 TBD / 要確認

- Q: **新規アプリのデフォルト DB**（DynamoDB / Aurora Serverless v2）の社内推奨 → `API-B-521`
- Q: RDS Proxy 採用基準（Aurora Serverless v2 と組まない場合のみ標準採用、等）→ `API-B-522`

---

## §5.4 イベント駆動・非同期

**このサブセクションで定めること**：非同期処理・キュー・ワークフローの標準。
**主な判断軸**：用途（fanout / 順序保証 / オーケストレーション）に応じた使い分け。
**§5 全体との関係**：同期 API の補完。

### §5.4.1 ベースライン

| 用途 | 標準サービス | 補足 |
|---|---|---|
| **キュー（at-least-once、最大 15 分遅延）** | SQS（DLQ 必須） | |
| **fanout（複数 subscriber）** | SNS | SQS との組み合わせ標準 |
| **イベントルーティング** | **EventBridge** | スキーマレジストリ・パートナーイベント・標準のイベントバス |
| **ワークフロー** | Step Functions（Express vs Standard を要件別に） | Express は低コスト、Standard はステートフル長期 |

### §5.4.2 TBD / 要確認

- Q: **クロスアカウントのイベント配信**（EventBridge custom event bus + リソースポリシー）の標準化 → `API-B-541`
- Q: メッセージスキーマの **バージョニング方針**（EventBridge Schema Registry を活用するか）→ `API-B-542`

---

## §5.5 Function URL / AppSync の位置づけ

**このサブセクションで定めること**：補完的な選択肢の採用基準。
**主な判断軸**：用途のはまり度。
**§5 全体との関係**：API Gateway + Lambda 標準への例外オプション。

### §5.5.1 ベースライン

- **Lambda Function URL**：
  - 適：単発 Webhook、内部 service 間（`AWS_IAM` auth）、最大 15 分実行が要るバッチ系
  - 不適：throttle / API Key / multi-route 要件
- **AppSync**：
  - 適：GraphQL（query / mutation / subscription）、複数バックエンド集約、モバイル
  - 不適：単純 CRUD・REST 慣れチームへの強制適用

### §5.5.2 TBD / 要確認

- Q: AppSync を「**選択肢に入れる**」か「**例外承認制**」にするか → `API-B-551`
- Q: Function URL の使用範囲を **Webhook と内部用途に明確に限定**するか → `API-B-552`

---

## §5.x 関連ドキュメント

- [§FR-API-6 Container 標準](06-container-standard.md) — もう 1 系統の標準
- [§C-API-2 ランタイム選定基準](../common/02-runtime-selection-criteria.md) — Serverless / Container の選定フロー
- [§FR-API-8 観測性](08-observability.md) — Powertools / ADOT の詳細
- [§NFR-API-2 性能](../nfr/02-performance.md) — Cold start 要件
