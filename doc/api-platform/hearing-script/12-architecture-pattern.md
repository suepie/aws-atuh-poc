# §C-API-2 §C-2.1 アーキパターン選定（SPA+API / SSR+API / SSR モノリス）

> 元データ: [../hearing-checklist.md B-0](../hearing-checklist.md#b-0-アーキパターン選定c-api-2-c-21)
> 対象: アプリリード / アーキテクト / Platform / 経営層
> 関連章: [§C-API-2](../proposal/common/02-runtime-selection-criteria.md), [§FR-API-6 §6.1.A](../proposal/fr/06-container-standard.md)
> 想定時間: 60-90 分

---

## ヒアリングの前提

本標準は **「外部から HTTP(S) を受ける Workload」全般**を対象としており、API だけでなく **SSR モノリス**（フロント + バックエンドが 1 プロセス）も含みます。
3 つのアーキパターン（SPA+API / SSR+API / SSR モノリス）はそれぞれ得意領域が異なるため、本標準でどう扱うかを最初に確定する必要があります。

---

### 【3 パターンすべてサポート対象とするか】 (API-B-001, 🔥)

本標準は以下の 3 アーキパターンすべてをサポート対象とし、選定は各アプリに委ねる方針でよろしいかご確認ください。

| パターン | 構成 | 適性 |
|---|---|---|
| **A. SPA + 別 API** | フロント (S3+CloudFront) + バックエンド API | 大規模 / マルチクライアント / B2B SaaS |
| **B. SSR + 別 API** | SSR フロント (Lambda/ECS) + 別 API | SEO 重視 + 高機能 + モバイル併用 |
| **C. SSR モノリス** | フロント + ビジネスロジックが 1 プロセス（Next.js full-stack / Rails / Spring Boot 等） | 小〜中規模 / 単一クライアント / フルスタックチーム |

選択肢:
- **3 パターンすべてサポート、選定は各アプリ**（本標準推奨）
- **SPA + API を推奨、SSR モノリスは例外承認制**（アーキの一貫性重視）
- **要件別に推奨を有効化**（B2B SaaS なら分離、単一テナントならモノリス OK 等）

**目的**: [§C-API-2 §C-2.1](../proposal/common/02-runtime-selection-criteria.md) のスタンス確定。3 パターンサポートにすると Service Catalog の標準製品ラインナップが約 1.5 倍になります（モノリス用テンプレ追加）が、現実のアーキを包含できます。

---

### 【SSR モノリスの将来マイクロ化リスクへの扱い】 (API-B-001-α, 🟡)

SSR モノリスを採用したアプリで、**将来モバイルアプリ等で API 切り出し要件が生じた場合**の扱いをどうしますか。

選択肢:
- **段階移行を支援**（本標準が IaC テンプレ・移行サンプルを提供、§C-API-2 §C-2.3 段階移行パス）
- **採用時に「将来マイクロ化の可能性」をチェック**（高リスクなら SPA+API/SSR+API を推奨）
- **モノリスは「マイクロ化を想定しない」前提で採用**（リプラットが必要になったら例外プロジェクト扱い）

**目的**: [§C-API-2 §C-2.3](../proposal/common/02-runtime-selection-criteria.md) の移行戦略・[§NFR-API-9](../proposal/nfr/09-compatibility.md) の互換性方針確定。モノリスは初期スピードが高い反面、後の API 切り出しコストが大きい構造的特性があります。

---

### 【SSR モノリスの規模上限の目安】 (API-B-001-β, 🟡)

SSR モノリス採用の **規模上限**の目安をご教示ください。
本標準の暫定提案：
- 同時 ECS タスク数：**20 タスク以下**
- ピーク TPS：**1,000 RPS 以下**
- DB アクセスパターン：単一 RDB（Aurora）+ せいぜいキャッシュ追加

これを超える場合は、SPA+API or SSR+API への移行を推奨する想定です。妥当性をご評価ください。
**目的**: [§C-API-2 §C-2.1.4](../proposal/common/02-runtime-selection-criteria.md) のチェックリスト、[§NFR-API-3 §3.1](../proposal/nfr/03-scalability.md) のスケール設計の閾値確定。

---

### 【SSR モノリスでの認証は ALB + Cognito 標準化か】 (API-B-002, 🔥)

SSR モノリスでの認証の標準は **ALB Authentication（Cognito / OIDC）** とする方針でよろしいかご確認ください。

- ALB 認証統合：未認証検知 → Cognito Hosted UI へリダイレクト → session cookie 発行 → `X-Amzn-Oidc-*` ヘッダにクレーム注入
- アプリ内で session を解釈、`/api/*` も同じ session で認証

代替案：
- アプリ内 session 管理（Cognito SDK / Auth.js / Devise / Spring Security 等）— 自由度高だが標準化しにくい
- 共有認証基盤側で SSR 用エンドポイント発行

**目的**: [§FR-API-2 §2.A](../proposal/fr/02-authn-authz.md) のモノリス認証標準確定。本標準は ALB 認証統合を第一選択と整理していますが、既存資産との整合性も含めご見解をお願いします。

---

### 【SSR モノリスの流量制御は WAF rate-based + アプリ内 throttling か】 (API-B-003, 🟡)

SSR モノリスでは **API Gateway Usage Plan が使えない**ため、流量制御は以下の組合せを標準とする方針でよろしいかご確認ください。

1. **第 1 層：CloudFront / WAF rate-based**（IP 単位、5min 窓）
2. **第 2 層：ALB**（target group の max connections / desired count スケール制御）
3. **第 3 層：アプリ内 middleware**（session ID / tenant_id 単位の throttling、必要時は DynamoDB アトミックカウンタ）

**目的**: [§FR-API-3 §3.A](../proposal/fr/03-throttling-quota.md) のモノリス流量制御標準。per-tenant 課金が必須要件のアプリはモノリスを避ける方針につながります。

---

### 【SSR モノリスでの per-tenant 課金按分の要件】 (API-B-004, 🟡)

SSR モノリスでの **per-tenant 課金按分** をどう実現しますか。

- アプリ内 middleware で `tenant_id` を確定 → EMF カスタムメトリクス出力
- ECS Service / Task に `Tenant` タグ付与 → CUR + Athena で集計
- API Key + Usage Plan を諦め、session / JWT クレーム計測の精度に依存
- per-tenant 課金不要（社内利用 / 単一テナント）

**目的**: [§FR-API-4 §4.A](../proposal/fr/04-metering-billing.md) のモノリス課金按分標準。テナント数 × リクエスト頻度で CloudWatch コストが急増する可能性があるため、設計初期に方針確定が必要です。

---

### 【SSR モノリスの観測性スタックの標準化】 (API-B-005, 🟡)

SSR モノリスの観測性スタックを **OpenTelemetry SDK + ADOT Collector サイドカー** で標準化する方針でよろしいかご確認ください。

| レイヤ | 標準 |
|---|---|
| アプリ内 SDK | OpenTelemetry（Node.js / Python / Ruby / Java / Go） |
| Collector | ADOT Collector サイドカー（task definition 内） |
| ログ | Fluent Bit / Firelens サイドカー → CloudWatch Logs |
| メトリクス | EMF カスタムメトリクス（CloudWatch）|
| トレース | ADOT → X-Ray |

**目的**: [§FR-API-8 §8.A](../proposal/fr/08-observability.md) のモノリス観測性標準。Lambda 系の Powertools は使えないため、別スタックの統一が必要です。

---

### 【既存アプリの SSR モノリス分布】 (API-A-102-α, 🔥)

既存アプリのうち、**SSR モノリス構成**（Next.js full-stack / Rails / Spring Boot + Thymeleaf 等）の **割合と代表例**をご教示ください。
- 多数（主要アプリが SSR モノリス）
- 一部（一部アプリのみ、他は SPA+API）
- ほぼなし
- 未確認 → 改めて棚卸し予定

**目的**: 本標準のスコープ調整。SSR モノリスが多数なら、Service Catalog のモノリス用テンプレ整備を優先する必要があります。

---

### 【新規アプリのアーキパターン分布想定】 (API-A-111, 🔥)

これから新規開発するアプリでのアーキパターン分布の **想定**をご教示ください。
- SPA + API: ~%
- SSR + API: ~%
- SSR モノリス: ~%
- 未定 / 都度判断: ~%

**目的**: [§C-API-2 §C-2.1](../proposal/common/02-runtime-selection-criteria.md) のラインナップ優先度と、選定支援ツール（決定木）の重点ガイドの方向決定。

---

## ヒアリング後の確定事項チェックリスト

Phase B-0 完了時点で、以下が揃っていることを確認してください：

- [ ] 3 パターンすべてサポートの方針（B-001）
- [ ] SSR モノリスの将来マイクロ化リスクへの方針（B-001-α）
- [ ] SSR モノリス採用の規模上限（B-001-β）
- [ ] SSR モノリス採用時の認証 / 流量 / 課金 / 観測性の標準（B-002〜B-005）
- [ ] 既存 SSR モノリスの分布（A-102-α）
- [ ] 新規アプリのアーキパターン想定（A-111）

これらが揃うと **§C-API-2 §C-2.1 アーキパターン選定章** と **§FR-API-6 §6.1.A モノリスサブパターン** を確定でき、Service Catalog 製品ラインナップの設計に進めます。
