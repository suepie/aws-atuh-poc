# Phase A: 既存アプリ現状・前提（共通）

> 元データ: [../hearing-checklist.md Phase A](../hearing-checklist.md#phase-a-既存アプリ現状前提)
> 対象: アプリリード / Platform / 既存運用担当
> 想定時間: 60-90 分

---

### 【標準化対象アプリの一覧】 (API-A-101, 🔥)

本標準（API プラットフォーム標準）の適用対象に含めるアプリの AWS アカウント一覧と数をご教示ください。
アカウント名・主な API の用途（例：経費精算 / 顧客向け Web / 内部マイクロサービス 等）も併せていただけますと幸いです。
**目的**: 標準化のスコープ確定、Service Catalog 配布対象の決定、移行計画（[§NFR-API-9 移行性](../proposal/nfr/09-compatibility.md)）の規模見積に必要な情報です。

---

### 【既存アプリの実装分布】 (API-A-102, 🔥)

各アプリの現状実装が **Serverless（API Gateway + Lambda 等）/ Container（ECS / EKS 等）/ 混在 / その他** のどれに該当するか、概況をご教示ください。
アプリ別の内訳（例: A サービス Lambda 中心 / B サービス ECS Fargate 中心）でお答えいただけますと幸いです。
**目的**: 本標準は **「Serverless / Container 2 系統並行カタログ」** を中心に設計しているため（[§C-API-2 ランタイム選定基準](../proposal/common/02-runtime-selection-criteria.md)）、既存実装が片寄っているなら **カタログラインナップの優先度**や移行コストに影響します。

---

### 【既存 SSR モノリス構成の割合】 (API-A-102-α, 🔥)

既存アプリのうち、**SSR モノリス構成**（Next.js full-stack / Nuxt / Rails / Spring Boot + Thymeleaf / Laravel + Blade 等、フロントとバックエンドが 1 プロセスに同居する構成）の **割合と代表例**をご教示ください。
選択肢:
- 多数（主要アプリが SSR モノリス）
- 一部（一部アプリのみ、他は SPA + 別 API）
- ほぼなし（SPA + 別 API が主流）
- 未確認 → 改めて棚卸し予定
**目的**: [§C-API-2 §C-2.1](../proposal/common/02-runtime-selection-criteria.md) のスコープ確定、[§FR-API-6 §6.1.A](../proposal/fr/06-container-standard.md) のモノリスサブパターンの整備優先度判断。SSR モノリスが多数なら Service Catalog のモノリス用テンプレ整備を優先します。

---

### 【公開範囲区分の現状】 (API-A-103, 🟡)

既存 API の公開範囲区分（Public / Internal / Partner / Private）は、現状で明確に分類されていますか。それとも実態として曖昧（インターネット公開なのか社内のみなのか不明確）な API がありますか。
曖昧な API について **再評価を実施する余地**があるかも併せて教えてください。
**目的**: [§FR-API-1 公開範囲](../proposal/fr/01-exposure-boundary.md) の判定フローを既存に適用する際、まず区分の棚卸しが必要かを判断します。

---

### 【トラフィック実測の有無】 (API-A-104, 🟡)

既存 API の月間リクエスト数・ピーク TPS の実測データはございますか。
取得済みであれば概数（例：1 億 req/月、ピーク 5,000 RPS）、未取得であれば取得可否をご教示ください。
**目的**: [§NFR-API-2 性能](../proposal/nfr/02-performance.md) / [§NFR-API-3 拡張性](../proposal/nfr/03-scalability.md) の Tier 割当と、流量制御の標準値設定（[§FR-API-3](../proposal/fr/03-throttling-quota.md)）に必要な情報です。

---

### 【AWS アカウント数と OU 構成】 (API-A-105, 🟡)

御社の AWS アカウント数と Organizations OU 構成（管理 / 監査 / Platform / Workload 等）の概況をご教示ください。
**目的**: [§C-API-1 §C-1.4 アカウント体系](../proposal/common/01-reference-architecture.md) の前提整理。本標準の **監査アカウント** / **共有認証基盤アカウント** が想定通り存在するか、または新設要否を判断します。

---

### 【Landing Zone 状況】 (API-A-106, 🟡)

AWS Control Tower / Landing Zone Accelerator (LZA) の導入状況をご教示ください。
**導入済み** / **検討中** / **未導入** + 導入済みなら採用範囲を併せて教えてください。
**目的**: 本標準は LZA / Control Tower のガードレール（SCP / Config Rules）と相補的に動作するため、既存導入の有無で **本標準で追加配信すべきルールセットの範囲**が変わります（[§FR-API-7 §7.2](../proposal/fr/07-guardrails.md)）。

---

### 【共有認証基盤の利用状況】 (API-A-107, 🔥)

共有認証基盤（本リポジトリ doc/requirements/ で要件定義中）の利用状況・利用予定（フェーズ）をご教示ください。
- 既に利用中（採用済プラットフォーム名）
- 利用予定（開始時期）
- 未利用 / 検討中
**目的**: 本標準は共有認証基盤の **利用側**として位置づけられるため（[§C-API-3](../proposal/common/03-shared-auth-boundary.md)）、認証基盤の存在を前提に組むか、独立も視野に入れるかが章立てに影響します。

---

### 【IaC 化率】 (API-A-108, 🟡)

既存アプリの IaC 化状況をご教示ください。
- 全面 IaC（CDK / Terraform / CloudFormation）
- 部分 IaC（一部リソースのみ手作業）
- 手作業中心
言語別の内訳（CDK / Terraform / CFn）も併せて教えてください。
**目的**: 本標準は Service Catalog / IaC モジュール（[§C-API-5](../proposal/common/05-self-service-catalog.md)）として配布する想定のため、提供する **IaC 言語選定**と既存アプリの **モジュール適用容易性**に影響します。

---

### 【チームの技術スキル分布】 (API-A-109, 🟡)

各アプリチームの主な技術スキル分布（Lambda 経験 / Container 経験 / 両方 / どちらも限定的）をご教示ください。
**目的**: [§C-API-2 ランタイム選定基準](../proposal/common/02-runtime-selection-criteria.md) の決定木で **チームスキル軸**が重い要素として組まれているため、社内分布が選定の妥当性に影響します。また Service Catalog 製品の優先度や教育投資計画にも影響します。

---

### 【本標準の対象範囲】 (API-A-110, 🔥)

本標準の適用対象範囲をどう想定されていますか。
- **全アプリに適用**（新規・既存問わず）
- **新規アプリのみ**（既存は段階移行）
- **Critical アプリのみ**（段階拡大）
- その他
移行コストの上限・期限の方針があれば併せていただけますと幸いです。
**目的**: [§NFR-API-9 §9.3 既存アプリの本標準への移行](../proposal/nfr/09-compatibility.md) の **移行 Tier** と期限の決定。本標準の中核ストーリーが「全面適用」か「漸進適用」かで章立ての強調点が変わります。

---

### 【新規アプリのアーキパターン分布想定】 (API-A-111, 🔥)

これから新規開発するアプリでのアーキパターン分布の **想定**をご教示ください。
- A. SPA + 別 API: 約 N %
- B. SSR + 別 API: 約 N %
- C. SSR モノリス: 約 N %
- 未定 / 都度判断: 約 N %

業界や事業の特性（B2B SaaS / 社内利用中心 / コンシューマー向け Web 等）に応じた偏りがあるならその背景もご教示ください。
**目的**: [§C-API-2 §C-2.1](../proposal/common/02-runtime-selection-criteria.md) のラインナップ優先度確定、選定支援ツール（決定木）の重点ガイドの方向決定、[§C-API-5](../proposal/common/05-self-service-catalog.md) Service Catalog 製品の整備優先度。

---

### 【Partner B2B API 連携の現状】 (API-A-112, 🔥)

**現状**で、外部企業（Partner）のシステムから本標準のアプリ API を呼び出す **M2M（Machine-to-Machine）連携** はございますか。
- **あり**（該当アプリ数、Partner 数、認証方式：API Key / OAuth / mTLS 等）
- **なし**（B2C / 社内利用中心、外部企業との API 連携なし）
- **一部あり**（特定アプリのみ、Partner 数も限定的）

具体例があればアプリ名と Partner 例（業界一般名でも可）をご教示ください。
**目的**: [§FR-API-2 §2.2.0](../proposal/fr/02-authn-authz.md) の Partner B2B M2M スコープ確認。「なし」の場合、本標準の §FR-API-2 §2.2 全体を対応範囲外として扱えます。「あり」の場合は OAuth Client Credentials デフォルト・認証基盤側の Partner Client 管理機能要件などの詳細を進めます。

---

### 【Partner B2B API の新規想定】 (API-A-113, 🔥)

**将来 1〜3 年**で、Partner B2B API（外部企業からの M2M 呼び出し）連携の **新規要件が発生する可能性**をご教示ください。
- **高い**（ロードマップに明示、Partner 連携が事業戦略に組み込み）
- **中程度**（顧客から要望あり、検討中）
- **低い**（B2C / 社内利用中心、Partner 連携の事業計画なし）
- **不明**（事業企画と要相談）

「あり」の場合は想定 Partner 数、業界、対象 API（読み取り / 書き込み / Webhook 等）をご教示ください。
**目的**: A-112 と合わせて Partner B2B M2M のスコープ確認。「将来あり」なら、本標準の Service Catalog 製品ラインナップに Partner 向け構成（OAuth Client Credentials + 認証基盤 M2M Client 連携）を含めるか判断します。認証基盤側（共有認証基盤）の Partner Client 管理機能要件の早期化にも影響します。

---

### 【非 AWS Internal 呼び出し元の現状棚卸し】 (API-A-115, 🔥)

「**社内 / Internal**」呼び出し元のうち、**AWS Principal を持たない**もの（GitHub Actions / Vendor SaaS / on-prem サーバ / 社外 Kubernetes 等）の現状をご教示ください。

選択肢（複数選択可）:
- **GitHub Actions / GitLab CI / Bitbucket Pipelines**（CI/CD パイプラインから AWS API 呼び出し）
- **Vendor SaaS**（Datadog / Splunk / New Relic / Snyk 等）
- **on-prem サーバ**（社内データセンター・オフィス内サーバ）
- **社外 Kubernetes**（IRSA を使わない、または EKS 以外の Kubernetes）
- **レガシーシステム**（API Key 直接埋め込み等のモダン認証非対応）
- 該当なし

該当ある場合、呼び出し頻度・データ機密度・現在の認証方式（IAM User の Access Key / API Key / 等）も併せてお教えください。
**目的**: [§FR-API-2 §2.3.A 非 AWS Internal の認証](../proposal/fr/02-authn-authz.md) のスコープ確定。現状で IAM User の Access Key を CI/CD に埋め込んでいる等のアンチパターンがあれば、**OIDC Federation 移行**を優先項目化します。

---

## ヒアリング後の確定事項チェックリスト

Phase A 完了時点で、以下が **仮回答以上の精度で**揃っていることを確認してください：

- [ ] 標準化対象アプリの一覧（A-101）
- [ ] 既存実装の分布（A-102）
- [ ] 既存 SSR モノリス構成の割合（A-102-α）
- [ ] 共有認証基盤の利用予定（A-107）
- [ ] 本標準の対象範囲（A-110）
- [ ] 新規アプリのアーキパターン分布想定（A-111）

これらが揃うと、Phase B-0（アーキパターン選定）と Phase B-1〜5（技術要件）の議論が **現実的な制約に基づいて**進められます。
