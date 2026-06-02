# §FR-API-6 標準アーキテクチャ：Container（ECS）

> 親 SSOT: [../00-index.md](../00-index.md) §FR-API-6
> ヒアリング: [../../hearing-script/06-container-standard.md](../../hearing-script/06-container-standard.md)

---

## §6.0 前提と背景

### §6.0.1 用語整理

| 用語 | 定義 |
|---|---|
| **ECS** | Amazon Elastic Container Service。AWS マネージドの Container Orchestrator |
| **Fargate** | ECS / EKS のサーバレスコンピュート。ノード管理不要、タスク単位課金 |
| **Service Connect** | ECS のサービス間通信機能（Envoy ベース）。クライアント側 LB / 自動 retry / 観測性 |
| **VPC Lattice** | クロス VPC / クロスアカウントの service-to-service 通信を SigV4 / IAM で実現 |
| **Task Role / Execution Role** | Task Role はアプリ自体の権限、Execution Role は ECS エージェント（ECR pull / Logs）の権限 |

### §6.0.2 なぜここ（§6）で決めるか

Serverless（§5）と並ぶもう 1 系統の標準。本章は Container 系の標準を定義する。

採用すべきユースケース：
- 長時間処理 / 常時稼働 / 既存資産の活用
- WebSocket・gRPC・特殊ライブラリ依存・Lambda タイムアウトを超える処理
- ECS 既経験チームのスムーズな立ち上げ

### §6.0.3 §6.0.A 本標準のスタンス

| 基本方針 | 本章での具体化 |
|---|---|
| 絶対安全 | Fargate 既定、Task Role 最小権限、Secrets Manager + KMS、private subnet |
| どんなアプリでも | API Gateway 経由・ALB 直・VPC Lattice 経由の 3 形態を提示 |
| 効率よく | ECS Service Connect / Lattice で内部通信標準化、ALB は共有 ALB で密度を上げる |
| 運用負荷・コスト最小 | Fargate デフォルト、EC2 は GPU / Spot / 専有要件のみ |

### §6.0.4 本章で扱うサブセクション

| § | サブセクション | 主題 |
|---|---|---|
| §6.1 | コンピュート（ECS Fargate / EC2） | 既定 Fargate、EC2 採用基準 |
| **§6.1.A** | **モノリス vs マイクロサービス** | **構成パターン選定、SSR モノリスは Container 一択** |
| §6.2 | 公開境界とロードバランサ | ALB / NLB / API Gateway VPC Link / 共有 ALB |
| §6.3 | サービス間通信 | Service Connect / VPC Lattice / Cloud Map |
| §6.4 | IAM・シークレット | Task Role / Execution Role / Secrets Manager 統合 |
| §6.5 | デプロイ | ECS Rolling / CodeDeploy Blue/Green |

---

## §6.1 コンピュート

**このサブセクションで定めること**：ECS Fargate / EC2 の使い分け。
**主な判断軸**：マネージド性・コスト・特殊要件。
**§6 全体との関係**：コンテナ実行環境の基盤。

### §6.1.1 ベースライン

| 観点 | Fargate（既定） | EC2 |
|---|---|---|
| **マネージド性** | ノード管理不要 | パッチ・OS 管理あり |
| **課金** | タスク単位（vCPU・GB・分） | EC2 単位 |
| **コスト最適化** | Savings Plan / Compute SP | RI / Spot / Savings Plan |
| **GPU / 専有** | ❌ | ✅ |
| **採用基準** | **新規はすべて Fargate**（明確な反証なき限り） | GPU / Spot / 専有 / ホストカスタマイズ要件のみ |

- **ARM (Graviton)** を推奨（同性能で 20% 安）
- **タスク CPU / メモリ**：プロファイリングで決定、過剰割当を避ける

### §6.1.2 TBD / 要確認

- Q: 既存 EC2 採用アプリの **Fargate 移行可否評価**スケジュール → `API-B-601`
- Q: Spot タスクの採用範囲（バッチのみ等）→ `API-B-602`

---

## §6.1.A モノリス vs マイクロサービス（構成パターン）

**このサブセクションで定めること**：Container 系の 2 つの構成パターン（モノリス / マイクロサービス）の選定基準と運用差分。
**主な判断軸**：[§C-API-2 §C-2.1](../common/02-runtime-selection-criteria.md) のアーキパターン選定結果、組織規模・スキル。
**§6 全体との関係**：§6.2〜§6.5 のデフォルト設定がどちらを選ぶかで異なる。

### §6.1.A.1 2 パターンの比較

| 観点 | **マイクロサービス** | **モノリス（SSR モノリス含む）** |
|---|---|---|
| **1 サービスの責務** | 1 機能 / 1 ドメインに限定 | フロント + バックエンドビジネスロジックが同居 |
| **代表例** | 個別 API、注文サービス、決済サービス | Next.js full-stack、Rails、Spring Boot + Thymeleaf |
| **アーキパターン §C-2.1 との対応** | A. SPA + 別 API / B. SSR + 別 API の **API 側** | **C. SSR モノリス** |
| **LB §6.2** | 共有 ALB + path/host routing で複数サービス | ALB 1 つで `/api/*` `/pages/*` を同一 ECS に振り分け |
| **サービス間通信 §6.3** | Service Connect / VPC Lattice が必須 | **基本的に不要**（同一プロセス内で完結） |
| **Task Role §6.4** | サービスごとに最小権限 | 1 タスクロールでアプリ全体の権限 |
| **デプロイ §6.5** | サービス単位で独立 | アプリ全体を 1 単位 |
| **スケール** | サービスごとに独立スケール | アプリ全体を一律スケール |
| **可観測性** | サービス境界でトレース、サービス間ホップが見える | アプリ内モジュール境界はアプリ自前計装 |
| **適性規模** | 中〜大規模、独立チーム複数 | 小〜中規模、単一チーム |

### §6.1.A.2 ベースライン（モノリスパターン採用時）

モノリスを採用する場合、以下を標準とする：

- **LB**: ALB 1 つで `/api/*` と `/pages/*` を path-based routing（§6.2 §6.2.1 の Public 行に該当）
- **サービス間通信**: 基本的に **不要**（同一プロセス内で関数呼び出し）
- **Service Connect / Lattice**: 採用しない（マイクロサービスでないため）
- **Task Role**: アプリ全体で 1 つ、ただし **アプリ内ロール分離**（IAM Identity Center / OPA / Verified Permissions 等）で機能別認可
- **デプロイ**: アプリ全体を 1 単位、Blue/Green 推奨（Critical Tier は必須）
- **スケール**: ECS Service Auto Scaling は **CPU / Memory + ALB request count** で設定
- **可観測性**: ADOT Collector サイドカー + OpenTelemetry SDK（Node/Ruby/Java/Python）、CloudWatch Logs 構造化

### §6.1.A.3 モノリス採用時の留意点

| 章 | モノリスでの注意 |
|---|---|
| §FR-API-1 公開境界 | 区分 (Public/Internal/Partner) は **path-based**（`/admin/*` は Internal 扱い等） |
| §FR-API-2 認証認可 | **ALB + Cognito session** を第一選択、JWT Authorizer は適用しにくい |
| §FR-API-3 流量制御 | **API Gateway Usage Plan が使えない** → ALB + WAF rate-based + アプリ内 throttling |
| §FR-API-4 課金按分 | per-tenant API Key 使えない → **session ID / JWT クレーム計測**、EMF カスタム次元で集計 |
| §FR-API-5 Serverless | **適用外**（モノリスは Container 一択） |
| §FR-API-7 ガードレール | 共通（WAF / 必須タグ / 暗号化 / SCP は完全に同じ） |
| §FR-API-8 観測性 | ADOT Lambda Layer 使えない → **ADOT Collector サイドカー + OTel SDK** |
| §C-API-2 §C-2.3 | **将来の API 切り出し**（モバイル要件等）が発生したら段階移行パスへ |

### §6.1.A.4 マイクロサービス採用時のチェック

新規マイクロサービス追加時に確認：

- [ ] サービス境界が **ビジネスドメイン**で明確に切られている
- [ ] サービス間通信は Service Connect / VPC Lattice で標準化
- [ ] Task Role は **当該サービス専用の最小権限**
- [ ] ログ / トレースで **サービス境界のホップ**が見える
- [ ] サービス削除・追加が他サービスに影響しないインターフェース

### §6.1.A.5 TBD / 要確認

- Q: モノリス採用アプリの **規模上限**（同時タスク数 / TPS）の目安 → `API-B-001-β`
- Q: モノリス →マイクロサービス **切り出しの支援範囲**（IaC テンプレ・移行サンプル）→ `API-D-1922`
- Q: モノリス標準テンプレ（Next.js / Rails / Spring Boot 等）を **Service Catalog に含めるか** → `API-D-2201-α`

---

## §6.2 公開境界とロードバランサ

**このサブセクションで定めること**：ECS 前段に置くロードバランサ・ゲートウェイの標準。
**主な判断軸**：公開境界（§1）と整合、共有 ALB でコスト密度を上げる。
**§6 全体との関係**：§FR-API-1 公開境界の Container 実装版。

### §6.2.1 ベースライン

| 公開境界 | LB 構成 | 補足 |
|---|---|---|
| **Public** | CloudFront → WAF → ALB → ECS | ALB 認証統合（Cognito / OIDC）も選択肢 |
| **Internal** | Internal ALB（同 VPC）/ VPC Lattice（クロス VPC/Account）| Lattice を新規推奨 |
| **Partner** | ALB（mTLS optional）+ WAF / API Gateway REST + VPC Link → NLB → ECS | Usage Plan 要件時は後者 |
| **Private** | Internal ALB + SG 制御 | |

- **共有 ALB の標準化**：複数 ECS サービスを host/path で振り分け、ALB 固定費を圧縮
- **NLB は TLS termination 要件・PrivateLink origin・超低レイテンシ時のみ**

### §6.2.2 TBD / 要確認

- Q: **共有 ALB の運用単位**（プロジェクト単位 / アカウント単位）→ `API-B-621`
- Q: ALB の **認証統合（Cognito / OIDC）を標準扱いするか**、APIGW + Lambda Authorizer に寄せるか → `API-B-622`

---

## §6.3 サービス間通信

**このサブセクションで定めること**：ECS サービス間 / 他コンピュートとの内部通信標準。
**主な判断軸**：同一 VPC か跨ぐか、IAM 認可の必要性。
**§6 全体との関係**：マイクロサービス間のデフォルトパス。

### §6.3.1 ベースライン

| 範囲 | 標準サービス | 補足 |
|---|---|---|
| **同一 VPC 内** | **ECS Service Connect**（Envoy ベース） | 新規推奨、クライアント側 LB / 自動 retry / メトリクス・ログ自動 |
| **クロス VPC / クロスアカウント** | **VPC Lattice** | Service Network を RAM で共有、Auth Policy で IAM 認可 |
| **DNS ベース discovery のみ** | AWS Cloud Map | 既存資産がこれのとき |
| **PrivateLink** | クロスアカウント特定 service の公開 | NLB エンドポイントサービス |

- **Service Connect サイドカー（Envoy）**：task definition のメモリ上限に織り込む（OOMKill 注意）
- **Service Connect は単一 VPC 内、Lattice はその外**

### §6.3.2 TBD / 要確認

- Q: 既存 Cloud Map / 自前 Consul 等からの **Service Connect / Lattice への移行ロードマップ** → `API-B-631`
- Q: Service Connect / Lattice の **mTLS 設定**を標準化するか → `API-B-632`

---

## §6.4 IAM・シークレット

**このサブセクションで定めること**：Task Role / Execution Role の分離と Secrets Manager 統合。
**主な判断軸**：最小権限、責任分離。
**§6 全体との関係**：セキュリティ最低ラインの実装。

### §6.4.1 ベースライン

- **Task Role**：アプリ自体が AWS API を呼ぶための権限。**サービスごとに専用ロール**、最小権限
- **Execution Role**：ECS エージェントが ECR pull / CloudWatch Logs 出力する権限。共通ロール許容
- **シークレット**：
  - Secrets Manager / SSM Parameter Store の **値を Task Definition の `secrets` フィールドで参照**（環境変数経由で渡る、ログに出ない）
  - KMS CMK で暗号化、ローテーション自動化（DB 認証情報など）
- **EBS / 一時ストレージ**：Fargate ephemeral storage は暗号化（KMS CMK）

### §6.4.2 TBD / 要確認

- Q: Task Role の **粒度**（サービス単位 / マイクロサービス単位）の標準化 → `API-B-641`
- Q: Execution Role の **共通テンプレ**を Service Catalog で配布するか → `API-B-642`

---

## §6.5 デプロイ

**このサブセクションで定めること**：ECS のデプロイ方式標準。
**主な判断軸**：本番リスク・ロールバック速度・ALB との整合。
**§6 全体との関係**：運用性（§NFR-6）と連動。

### §6.5.1 ベースライン

| 方式 | 採用条件 |
|---|---|
| **ECS Rolling**（既定） | 通常ケース、シンプル |
| **CodeDeploy Blue/Green** | ALB 切替 + テストリスナーで安全に検証したいケース、自動ロールバック |
| **External deployment**（ArgoCD / Spinnaker 等） | GitOps 既導入の場合のみ例外 |

- **2025.09 以降 ECS の AZ rebalancing がデフォルト有効化**。サービス設計時に AZ spread 戦略（`balanced`, `random`, `spread`）を明文化

### §6.5.2 TBD / 要確認

- Q: 本番は **Blue/Green を標準化するか**、Rolling でも可とするか → `API-B-651`
- Q: AZ spread strategy の **デフォルト値**（`spread` 推奨）→ `API-B-652`

---

## §6.x 関連ドキュメント

- [§FR-API-5 Serverless 標準](05-serverless-standard.md) — もう 1 系統の標準
- [§C-API-2 ランタイム選定基準](../common/02-runtime-selection-criteria.md) — 選定フロー
- [§NFR-API-1 可用性](../nfr/01-availability.md) — マルチ AZ / Spot 戦略
- [§NFR-API-6 運用](../nfr/06-operations.md) — デプロイ・パッチ
