# §FR-API-6 標準アーキテクチャ：Container（ECS）

> 元データ: [../hearing-checklist.md B-5](../hearing-checklist.md#b-5-containerecs-標準fr-api-6)
> 対象: アプリリード / アーキテクト
> 関連章: [§FR-API-6](../proposal/fr/06-container-standard.md)

---

### 【既存 EC2 アプリの Fargate 移行可否】 (API-B-601, 🟡)

既存の EC2 ベース ECS アプリ（または素の EC2 アプリ）の **Fargate 移行可否評価**を実施する方針はありますか。
- 全件評価（標準化前提として必須）
- 段階的に評価（次回リプラット時等）
- 評価しない（EC2 継続を許容）
GPU / Spot / 専有要件のあるアプリは Fargate 対象外として整理することが想定されます。
**目的**: [§FR-API-6 §6.1 / §NFR-API-9](../proposal/nfr/09-compatibility.md) の移行スコープ。Fargate を新規デフォルトにすることが本標準のスタンスです。

---

### 【Spot タスクの採用範囲】 (API-B-602, 🟢)

Fargate Spot タスクの採用範囲をご教示ください。
- バッチ・stateless ECS のみ
- 開発・ステージング環境のみ
- 採用しない（中断リスクを受容しない）
Spot は最大 70% 安価ですが、2 分前通知で中断される可能性があります。
**目的**: [§FR-API-6 §6.1 / §NFR-API-8](../proposal/nfr/08-cost.md) のコスト最適化と可用性のバランス。

---

### 【共有 ALB の運用単位】 (API-B-621, 🟡)

ALB の共有運用単位をご教示ください。
- **プロジェクト単位**で 1 ALB を共有（複数 ECS service を host/path 振り分け）
- **アカウント単位**で大規模共有
- **サービス単位**で個別 ALB（共有しない）
ALB は固定費（時間課金 + LCU）がかかるため、複数 service を 1 つの ALB で振り分けるとコスト密度が大きく向上します。
**目的**: [§FR-API-6 §6.2 / §NFR-API-8](../proposal/nfr/08-cost.md) のコスト最適化と運用境界。

---

### 【ALB の認証統合】 (API-B-622, 🟡)

ALB の認証統合（Cognito / OIDC を ALB レベルで実装、`X-Amzn-Oidc-*` ヘッダにクレーム注入）を本標準の **標準扱い**にするか、APIGW + Lambda Authorizer に寄せるか、ご見解をお願いします。
- ALB 認証統合：Web UI 系で簡単、SSO 体験が良い
- APIGW Lambda Authorizer：細粒度ロジック可能
- 用途別（Web UI は ALB、API は APIGW）
**目的**: [§FR-API-6 §6.2 / §FR-API-2](../proposal/fr/02-authn-authz.md) の認証配置選定。

---

### 【ECS バックエンドの前段 LB デフォルト】 (API-B-623, 🔥)

ECS バックエンド（フロントエンドが SPA や別 SSR で分離されている構成、[§C-API-2 §C-2.1 パターン A / B](../proposal/common/02-runtime-selection-criteria.md)）の **前段ロードバランサ**として、本標準のデフォルトをどちらにする方針が望ましいかご教示ください。

選択肢:
- **Pattern X：ALB only**（CloudFront + WAF + ALB + ECS）
  - 低コスト（特に >100M req/月）、レイテンシ低、Streaming / WebSocket / 大容量レスポンス対応
  - Usage Plan / API Key 機能なし
- **Pattern Y：API Gateway + ALB**（CloudFront + WAF + API GW + VPC Link + ALB + ECS）
  - Usage Plan / API Key / Stage 管理 / Canary deployments 機能あり
  - per-request 課金、29 秒タイムアウト、10 MB ペイロード上限、Streaming / WebSocket 制約
- 用途別判断（Partner B2B あれば API GW、それ以外は ALB 等）

**目的**: [§FR-API-6 §6.2.A](../proposal/fr/06-container-standard.md) の前段選定基準確定。本標準の Service Catalog 製品ラインナップが決まります。一般的には **「ALB only がデフォルト、Partner B2B / マルチテナント throttle 等の要件で API GW + ALB に escalation」** が業界主流です（[§6.2.A 選定マトリクス](../proposal/fr/06-container-standard.md) 参照）。

---

### 【Partner B2B 対応 ECS バックエンドの API GW 必須化】 (API-B-624, 🟡)

Partner B2B 連携（OAuth Client Credentials + Usage Plan / API Key）が要件化された ECS バックエンドアプリの場合、**API Gateway REST API + Usage Plan の利用を必須化**する方針でよろしいかご確認ください。

選択肢:
- 必須化（Partner B2B 要件なら自動的に API GW REST 採用）
- 任意（ALB + Lambda Authorizer + 自前 throttle で対応可）
- アプリ判断

**目的**: [§FR-API-6 §6.2.A / §FR-API-2 §2.2](../proposal/fr/02-authn-authz.md) の Partner 認証と前段選定の整合。Usage Plan の代替自前実装は運用負荷が高いため、Partner B2B あれば API GW REST 必須化が自然です。

---

### 【サービス間通信の移行ロードマップ】 (API-B-631, 🟡)

既存の Cloud Map / 自前 Consul / 自前 sidecar service mesh から、本標準の **ECS Service Connect / VPC Lattice** への移行ロードマップ方針をご教示ください。
- 新規は Service Connect / Lattice 必須、既存は次回更新時に移行
- 段階的に全件移行（半期 / 1 年単位の計画）
- 既存維持、新規のみ標準適用
**目的**: [§FR-API-6 §6.3 / §NFR-API-9](../proposal/nfr/09-compatibility.md) の移行計画。

---

### 【Service Connect / Lattice の mTLS】 (API-B-632, 🟢)

ECS Service Connect / VPC Lattice の **内部 mTLS** を本標準で必須化するか、選択肢とするか、ご見解をお願いします。
**目的**: [§FR-API-6 §6.3 / §NFR-API-4 §4.1](../proposal/nfr/04-security.md) の内部通信暗号化方針。

---

### 【Task Role の粒度】 (API-B-641, 🟡)

ECS Task Role の標準粒度をご教示ください。
- **サービス単位**（同一サービス内の全 task が同じロール）
- **マイクロサービス単位**（細分化、最小権限徹底）
- **環境単位**（prod / stg 等で 1 つ、大粒度）
**目的**: [§FR-API-6 §6.4 / §NFR-API-4](../proposal/nfr/04-security.md) の最小権限の徹底度。

---

### 【Execution Role の共通テンプレ配布】 (API-B-642, 🟢)

ECS Task **Execution Role**（ECR pull / CloudWatch Logs 出力等の共通 ECS エージェント権限）を、Service Catalog で共通テンプレとして配布する方針はありますか。
Execution Role は権限内容が定型的なため、共通テンプレ提供は妥当ですが、責任分界の明確化が必要です。
**目的**: [§FR-API-6 §6.4 / §C-API-5](../proposal/common/05-self-service-catalog.md) の標準提供物。

---

### 【本番デプロイは Blue/Green 標準化か】 (API-B-651, 🟡)

本番 ECS デプロイの方式を、**CodeDeploy Blue/Green を標準化する**か、**ECS Rolling でも可**とするか、ご見解をお願いします。
- Blue/Green：ALB 切替、テストリスナーで安全検証、自動ロールバック
- Rolling：シンプル、ALB ターゲットを段階的に置換
- Critical Tier のみ Blue/Green 必須
**目的**: [§FR-API-6 §6.5 / §NFR-API-6](../proposal/nfr/06-operations.md) のデプロイ標準。本番リスクと運用工数のバランス。

---

### 【ECS AZ spread strategy】 (API-B-652, 🟢)

ECS Service の AZ spread strategy（`spread` / `random` / `balanced`）の **デフォルト値**をご教示ください。
本標準の暫定推奨は `spread`（3 AZ 均等配置、可用性最優先）です。
**目的**: [§FR-API-6 §6.5 / §NFR-API-1](../proposal/nfr/01-availability.md) の可用性設計。2025.09 以降 ECS AZ rebalancing がデフォルト有効化されている前提です。

---

## ヒアリング後の確定事項チェックリスト

- [ ] 既存 EC2 アプリの Fargate 移行方針（B-601）
- [ ] 共有 ALB の運用単位（B-621）
- [ ] ALB 認証統合の扱い（B-622）
- [ ] 本番デプロイ方式（B-651）

これらが揃うと **§FR-API-6 Container 標準** と **Service Catalog の Container 製品ラインナップ** を確定できます。
