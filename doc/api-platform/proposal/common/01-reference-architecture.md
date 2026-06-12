# §C-API-1 全体参照アーキテクチャ

> 親 SSOT: [../00-index.md](../00-index.md) §C-API-1
> ヒアリング: [../../hearing-script/00-common.md](../../hearing-script/00-common.md)

---

## §C-1.0 前提と背景

### §C-1.0.1 用語整理

| 用語 | 定義 |
|---|---|
| **4 層モデル** | 公開範囲 / 認証認可 / 流量制御 / 実装ランタイム の層構造。**AWS が公式に命名したフレームワークではなく**、API Gateway Developer Guide / Well-Architected Serverless Lens / Prescriptive Guidance / 業界標準の API Gateway パターン等に共通する論述順を抽出した本標準の合成（根拠は [SSOT 付録 A.0](../../requirements-document-structure.md)） |
| **Landing Zone** | AWS Organizations + Control Tower + 標準アカウント体系の総称 |
| **共有認証基盤アカウント** | OIDC/OAuth 認可サーバを提供する集中アカウント |
| **監査アカウント** | FMS Delegated Admin、CloudTrail / Config 集約先 |

### §C-1.0.2 なぜここ（§C-1）で決めるか

§FR-API-1 〜 §FR-API-8 / §NFR-API-1 〜 §NFR-API-9 の各章は **「ある層・ある側面」の標準** を定義する。本章は **全体図** を 1 つに統合し、横串で見たときの整合性を保証する。

### §C-1.0.3 §C-1.0.A 本標準のスタンス

| 基本方針 | 本章での具体化 |
|---|---|
| 絶対安全 | 全体図で監査アカウントからの配信経路（FMS / CloudTrail）を明示 |
| どんなアプリでも | Serverless / Container を並列で図示、いずれの選択でも整合性を保つ |
| 効率よく | Service Catalog で配布される「製品」と各層の対応を見える化 |
| 運用負荷・コスト最小 | マネージドサービスを最大限活用する構成 |

### §C-1.0.4 本章で扱うサブセクション

| § | サブセクション |
|---|---|
| §C-1.1 | 4 層モデル全体図 |
| §C-1.2 | Serverless パターン参照アーキ |
| §C-1.3 | Container（ECS）パターン参照アーキ — **マイクロサービス / モノリス 両方** |
| §C-1.4 | アカウント体系（Landing Zone との関係） |
| **§C-1.5** | **Federated Platform Standard：中央集約 vs 分散ガイドの判断** ⭐ — 本標準が分散ガイドを採用する根拠と業界事例 |

---

## §C-1.1 4 層モデル全体図

**このサブセクションで定めること**：本標準の中核となる 4 層構造を 1 つの図で示す。
**主な判断軸**：層ごとの責務分離、横串（観測性・コスト・ガードレール）の整理。
**§C-1 全体との関係**：他のサブセクションがこの図の特殊化。

### §C-1.1.1 ベースライン

```mermaid
flowchart TB
    subgraph Client[クライアント]
        Web[Web/SPA]
        Mobile[Mobile]
        Partner[Partner B2B]
        Internal[Internal Service]
    end

    subgraph App[各アプリ AWS アカウント]
        subgraph L1[公開範囲層 §FR-API-1<br/>信頼プロファイル]
            CF[CloudFront + WAF]
            APIGW[API Gateway]
            ALB[ALB]
        end

        subgraph L2[認証認可層 §FR-API-2]
            JWT[JWT Authorizer]
            IAMauth[IAM Auth]
            APIKey[API Key + Usage Plan]
            mTLS[mTLS]
        end

        subgraph L3[流量制御層 §FR-API-3/4]
            Throttle[Throttle]
            Quota[Quota]
            Meter[Metering / Cost tag]
        end

        subgraph L4[実装ランタイム層 §FR-API-5/6]
            Lambda[Lambda]
            ECS[ECS Fargate]
            AppSync[AppSync]
        end

        subgraph Cross[横串]
            Obs[観測性 §FR-API-8]
            Cost[コスト §NFR-API-8]
            Tag[必須タグ §FR-API-4]
        end
    end

    subgraph Auth[共有認証基盤アカウント §C-API-3]
        IdP[Identity Broker<br/>Cognito or Keycloak]
    end

    subgraph Audit[監査アカウント §C-API-4]
        FMS[FMS<br/>WAF/SG/NetFW 配信]
        CT[CloudTrail Org Trail]
        Catalog[Service Catalog]
    end

    Client --> L1 --> L2 --> L3 --> L4
    L2 -.JWT 検証.-> IdP
    FMS -.WAF/SG 配信.-> L1
    FMS -.SG 配信.-> L4
    Catalog -.スタック配布.-> App
    App -.集約.-> CT
    L4 --> Obs
    L4 --> Cost
    L4 --> Tag
```

### §C-1.1.2 図の読み方

- **縦方向の流れ**：クライアント → L1 → L2 → L3 → L4
- **横方向の連携**：L2 が共有認証基盤と JWT 検証で連携、横串で観測・コスト・タグ
- **監査アカウントからの配信**：FMS / SCP / Service Catalog はトップダウンで各アプリへ
- **集約**：CloudTrail / Config の証跡は各アプリから監査アカウントへ

---

## §C-1.2 Serverless パターン参照アーキ

**このサブセクションで定めること**：Serverless 標準（§FR-API-5）の完成形参照アーキ。
**主な判断軸**：マネージド優先、低コスト。
**§C-1 全体との関係**：§C-1.1 を Serverless で具現化したもの。

### §C-1.2.1 公開範囲別 Serverless 構成

```mermaid
flowchart LR
    Internet --> CF[CloudFront] --> WAF[AWS WAF<br/>Managed Rules]
    WAF --> APIGW[Regional<br/>HTTP API]
    APIGW --> JWTAuth[JWT Authorizer]
    JWTAuth --> Lambda[Lambda<br/>arm64 / Powertools]
    Lambda --> DDB[DynamoDB<br/>or Aurora Serverless v2]
    Lambda --> EB[EventBridge]
    EB --> SQS[SQS] --> LambdaAsync[Async Lambda]

    Lambda -.metrics/trace.-> CW[CloudWatch + ADOT]
    APIGW -.access log.-> CWL[CloudWatch Logs<br/>CMK + Data Protection]
```

### §C-1.2.2 標準要素

- **CloudFront**：Public は前段必須（WAF / 直叩き防止）
- **AWS WAF**：FMS 配信 Managed Rules + rate-based + アプリ独自
- **API Gateway**：HTTP API 既定、REST は Usage Plan/API Key 必要時
- **Lambda**：Powertools 必須、ADOT で OpenTelemetry tracing
- **DB**：DynamoDB on-demand を新規既定
- **イベント**：EventBridge + SQS で非同期化

### §C-1.2.3 TBD / 要確認

- Q: 全 Serverless API で CloudFront を必須化するか → `API-B-105`（§FR-API-1 と同じ）
- Q: ADOT / X-Ray の選定（新規 ADOT 必須化）→ `API-C-821`（§FR-API-8 と同じ）

---

## §C-1.3 Container（ECS）パターン参照アーキ

**このサブセクションで定めること**：Container 標準（§FR-API-6）の完成形参照アーキ。
**主な判断軸**：Fargate 既定、Service Connect / Lattice。
**§C-1 全体との関係**：§C-1.1 を Container で具現化したもの。

### §C-1.3.1 公開範囲別 Container 構成

```mermaid
flowchart LR
    Internet --> CF[CloudFront] --> WAF[AWS WAF]
    WAF --> ALB[ALB<br/>Cognito/OIDC auth optional]
    ALB --> ECS[ECS Fargate Service<br/>arm64]
    ECS --> SC[Service Connect<br/>Envoy sidecar]
    SC --> OtherECS[Other ECS Service]
    ECS --> Lattice[VPC Lattice<br/>cross-account]
    ECS --> Aurora[Aurora Serverless v2]

    ECS -.metrics/log.-> CW[CloudWatch + ADOT]
    ECS -.firelens.-> CWL[CloudWatch Logs]
```

### §C-1.3.2 標準要素

- **CloudFront / WAF**：Public は同じく前段必須
- **ALB**：共有 ALB で複数 ECS service を host/path 振り分け
- **ECS Fargate**：arm64、`spread` AZ strategy、Service Connect で内部通信
- **VPC Lattice**：クロスアカウント / クロス VPC 時に採用
- **DB**：Aurora Serverless v2 / RDS Proxy（要件次第）
- **観測**：ADOT Collector サイドカー、Fluent Bit でログルーティング

### §C-1.3.3 SSR モノリスパターン参照アーキ

[§C-API-2 §C-2.1](02-runtime-selection-criteria.md) のパターン C（SSR モノリス）を採用する場合の参照アーキ：

```mermaid
flowchart LR
    Internet --> CF[CloudFront] --> WAF[AWS WAF]
    WAF --> ALB[ALB<br/>+ Cognito session auth]
    ALB -.path: /api/*.-> ECS[ECS Fargate Service<br/>Next.js / Rails / Spring Boot<br/>full-stack monolith]
    ALB -.path: /pages/*.-> ECS
    ALB -.path: /assets/*.-> ECS
    ECS --> RDS[RDS / Aurora]

    ECS -.ADOT sidecar.-> CW[CloudWatch + ADOT]
    ECS -.firelens.-> CWL[CloudWatch Logs]
```

#### モノリスパターンの標準要素

- **CloudFront / WAF**：Public は前段必須（マイクロサービスと同じ）
- **ALB**：path-based routing で 1 ECS Service に集約。**ALB 認証（Cognito）が第一選択**
- **ECS Fargate**：1 Service / 1 Task Definition、フルスタックエンジニアの構成
- **Service Connect / VPC Lattice**：**不要**（同一プロセス内で完結）
- **DB**：RDS / Aurora 主流（リレーショナル中心のフレームワークが多い）
- **観測**：ADOT Collector サイドカー + OTel SDK（言語別）、Fluent Bit でログルーティング

→ 詳細は [§FR-API-6 §6.1.A モノリス vs マイクロサービス](../fr/06-container-standard.md) 参照。

### §C-1.3.4 ECS バックエンド + API Gateway パターン参照アーキ

[§C-API-2 §C-2.1.5](02-runtime-selection-criteria.md) のサブパターン **A-3（SPA + ECS バックエンド + API GW + ALB）** を採用する場合の参照アーキ：

```mermaid
flowchart LR
    Internet --> CF[CloudFront]
    CF --> WAF[AWS WAF]
    WAF --> APIGW[API Gateway<br/>REST or HTTP]

    APIGW -.JWT Authorizer.-> Auth[共有認証基盤]
    APIGW -.Usage Plan + API Key.-> Usage[Partner B2B]
    APIGW --> VPCLink[VPC Link v2]
    VPCLink --> ALB[Internal ALB]
    ALB --> ECS[ECS Fargate Service<br/>Backend API only<br/>Spring Boot / Express / FastAPI 等]
    ECS --> DB[RDS / Aurora / DynamoDB]

    ECS -.ADOT sidecar.-> CW[CloudWatch + ADOT]
    ECS -.firelens.-> CWL[CloudWatch Logs]
```

#### ECS バックエンド + API GW パターンの標準要素

- **CloudFront / WAF**：Public は前段必須
- **API Gateway**：REST（Usage Plan / API Key 必要時）or HTTP（マネージド JWT Authorizer）
- **VPC Link v2**：ALB 統合（2020 GA）、HTTP API は直接 ALB 統合可
- **Internal ALB**：path / host based routing、VPC 内部のみ
- **ECS Fargate**：純粋 JSON バックエンド API（HTML 配信なし）
- **DB**：要件次第（DynamoDB / Aurora 等）

#### A-2（ALB only）vs A-3（API GW + ALB）の選定

- Partner B2B Usage Plan 必要 → **A-3 必須**
- マルチテナント per-tenant throttle 必要 → **A-3 必須**
- AWS Marketplace SaaS 公開 → **A-3 必須**
- 純粋 B2C / 内部 + トラフィック大 → **A-2 推奨**（コスト優位）
- WebSocket / Streaming / 大容量 → **A-2 必須**

→ 詳細は [§FR-API-6 §6.2.A ALB only vs API Gateway + ALB の選定基準](../fr/06-container-standard.md) 参照。

### §C-1.3.5 TBD / 要確認

- Q: Service Connect vs VPC Lattice の **デフォルト境界**確定 → `API-B-106`（§FR-API-1 と同じ）
- Q: モノリスパターン用 **Service Catalog 製品**の整備優先度 → `API-D-2201-α`

---

## §C-1.4 アカウント体系（Landing Zone との関係）

**このサブセクションで定めること**：本標準が想定する AWS アカウント体系。
**主な判断軸**：Control Tower / LZA 既定との整合、責務分離。
**§C-1 全体との関係**：監査アカウント（§C-4）・共有認証基盤（§C-3）の位置づけ。

### §C-1.4.1 ベースライン

```mermaid
flowchart TB
    Mgmt[Management Account<br/>Org root]

    subgraph Security[Security OU]
        Audit[Audit / Security Tooling<br/>FMS Delegated Admin<br/>CloudTrail / Config 集約]
        LogArc[Log Archive]
    end

    subgraph Platform[Platform OU]
        AuthAcc[共有認証基盤アカウント]
        Catalog[Service Catalog 配布元]
    end

    subgraph Workload[Workload OU]
        App1[App 1 (prod)]
        App2[App 2 (prod)]
        App3[App 3 (stg)]
    end

    Mgmt --> Security
    Mgmt --> Platform
    Mgmt --> Workload
    Audit -.WAF/SG 配信.-> App1
    Audit -.WAF/SG 配信.-> App2
    Audit -.WAF/SG 配信.-> App3
    AuthAcc -.JWT.-> App1
    AuthAcc -.JWT.-> App2
```

### §C-1.4.2 アカウント区分

| OU / アカウント | 役割 |
|---|---|
| **Management** | Org root、SCP 設定 |
| **Audit / Security Tooling** | FMS Delegated Admin、Security Hub、GuardDuty 集約 |
| **Log Archive** | CloudTrail / Config / S3 access log の集約先 |
| **共有認証基盤** | Identity Broker（[../../requirements/](../../requirements/00-index.md)）|
| **Workload (prod/stg/dev)** | 各アプリ。**本標準が適用される対象** |

### §C-1.4.3 TBD / 要確認

- Q: 既存アカウント体系の **再編要否**（Landing Zone Accelerator 未導入なら導入計画要）→ `API-D-1801`
- Q: Workload OU の **環境分離**（prod / stg / dev でアカウント分離 vs 同一アカウント内）→ `API-D-1802`

---

## §C-1.5 Federated Platform Standard：中央集約 vs 分散ガイドの判断

**このサブセクションで定めること**：**「API 基盤を共通化する」か「ガイドで分散する」か** の根本論拠と、本標準のスタンス。
**主な判断軸**：システムの独立性、API の重複度、障害分離要件、業界トレンド（Platform Engineering）。
**§C-1 全体との関係**：本サブセクションが §C-1.1〜§C-1.4 の全体アーキ設計の **根本的な前提**。

### §C-1.5.1 2 つのアプローチの定義

| アプローチ | 仕組み | 例 |
|---|---|---|
| **A. 中央集約**（共通 API 基盤）| 1 つの中央 API アカウントで全システムの API を受ける。共通の WAF・認証・流量制御・監視。中央チームが運用 | ESB / SOA / 旧来の API Gateway 一元化 |
| **B. 分散ガイド**（本標準）⭐ | 各システムが自アカウントで API 基盤を自前構築。標準（ガイド）と Service Catalog 製品で支援。中央は監査・ガードレール配信のみ | Netflix Paved Road / Spotify Golden Path / Amazon Two-Pizza |

### §C-1.5.2 観点別比較

| # | 観点 | A. 中央集約 | B. 分散ガイド（本標準）|
|---|---|:---:|:---:|
| 1 | 重複コスト | ◎ 削減 | △ 重複あり（IaC で軽減） |
| 2 | 障害分離 | ❌ **単一障害点** | ◎ 完全分離 |
| 3 | 各システムの自由度 | △ 制約あり | ◎ 高い |
| 4 | スケール上限 | △ 中央上限 | ◎ 独立 |
| 5 | ガバナンス | ◎ 一箇所 | ◎ FMS / Config で実現可 |
| 6 | セキュリティ更新の伝播 | ◎ 即時全反映 | △ 各システムで反映 |
| 7 | 統一性 | ◎ 強制可 | △ 規律依存 |
| 8 | リリースサイクル独立性 | △ 中央調整 | ◎ システム別 |
| 9 | 中央チームのボトルネック | ❌ あり | ◎ なし |
| 10 | スキル要件 | ◎ 中央集約 | △ 分散 |
| 11 | 監視・トレース | ◎ 一元 | △ 横断視点別構築 |
| 12 | **API 重複時の効果** | ◎ 大 | – |
| 13 | **API 重複なし時の効果** | △ メリット減 | ◎ そのまま機能 |
| 14 | 業界トレンド | △ 旧来型 | ◎ Modern（Platform Engineering）|

### §C-1.5.3 本標準が B を採用する根拠

本標準が想定する条件：

| 条件 | 状況 |
|---|---|
| 対象システムは独立している | ✅ |
| 同じ API を複数システムが叩く（共通参照系）| ❌ ほぼなし |
| 横断的トランザクション管理が必要 | ❌ |
| API 数が爆発的で統合管理が困難 | ❌ |
| 全社で API ライフサイクル統一が必要 | ❌ |
| 障害分離が重要 | ✅ |
| 各システムの要件最適化が重要 | ✅ |

→ **A（中央集約）の主要メリット（重複削減・再利用・横断管理）がほぼ無効化**、**B（分散ガイド）の主要メリット（障害分離・独立性・最適化）がフル活用**される条件。

### §C-1.5.4 ただし「完全分散」ではなく Federated（連邦型）

「完全に分散」だとガバナンスが効かない。**「共通すべきものは中央集約、独立すべきものは分散」**のハイブリッド = **Federated アーキ** が業界主流。

| 要素 | 集約 / 分散 | 根拠 |
|---|:---:|---|
| **認証基盤**（OIDC / OAuth） | **中央** | 共通の identity provider、SSO 統一（[../requirements/](../../../requirements/00-index.md)）|
| **監査アカウント FMS**（WAF / SG ポリシー配信）| **中央** | ガードレール統一、コンプラ要件 |
| **Service Catalog**（標準テンプレ配布）| **中央** | 標準の機械的強制 |
| **Security Hub / CloudTrail 集約**| **中央** | 横断監視 |
| **SCP / Org policy** | **中央** | 予防的制御 |
| **コスト按分・タグ**（CUR + Athena）| **中央** | 横断コスト可視化 |
| **API Gateway** | **分散** | 各システムの要件に最適化 |
| **WAF Web ACL**（カスタムルール）| **分散**（FMS 配信は中央）| アプリ独自ルール |
| **Lambda / ECS / DB** | **分散** | 完全独立 |
| **流量制御の閾値** | **分散** | システム要件依存 |
| **アプリ DB の permission**| **分散** | アプリ固有 |

→ **本標準は既にこの Federated アプローチを採用済み**（§C-1.4 アカウント体系 + §C-API-4 監査ガバナンス境界 + §C-API-3 共有認証基盤）。

```mermaid
flowchart TB
    subgraph Central["🏛 中央集約（共通要素）"]
        Auth["共有認証基盤<br/>(OIDC/OAuth)"]
        Audit["監査アカウント<br/>(FMS / CloudTrail / Config)"]
        Catalog["Service Catalog<br/>(標準テンプレ配布)"]
        Org["Organization SCP<br/>(予防的制御)"]
    end

    subgraph App1["📦 App 1 アカウント（分散・独立）"]
        API1[API Gateway]
        WAF1[WAF]
        Lambda1[Lambda/ECS]
        DB1[DB]
    end

    subgraph App2["📦 App 2 アカウント（分散・独立）"]
        API2[API Gateway]
        WAF2[WAF]
        Lambda2[Lambda/ECS]
        DB2[DB]
    end

    subgraph App3["📦 App 3 アカウント（分散・独立）"]
        API3[API Gateway]
        WAF3[WAF]
        Lambda3[Lambda/ECS]
        DB3[DB]
    end

    Auth -.JWT.-> API1
    Auth -.JWT.-> API2
    Auth -.JWT.-> API3
    Audit -.FMS 配信.-> WAF1
    Audit -.FMS 配信.-> WAF2
    Audit -.FMS 配信.-> WAF3
    Catalog -.テンプレ配布.-> App1
    Catalog -.テンプレ配布.-> App2
    Catalog -.テンプレ配布.-> App3
    Org -.SCP.-> App1
    Org -.SCP.-> App2
    Org -.SCP.-> App3
```

### §C-1.5.5 業界事例

| 企業 / モデル | アプローチ | 教訓 |
|---|---|---|
| **Netflix Paved Road** | 分散 + 中央が「使うと楽になる」テンプレ提供 | 強制せず、自然に従いたくなる設計 |
| **Spotify Golden Path** | 分散 + Backstage 内部ポータルで標準化支援 | self-service が鍵 |
| **Amazon Two-Pizza Team** | 完全分散、各チームが独立 API オーナー | 規律と自由のバランス |
| **Google SRE** | 分散 + 横断 SRE による品質保証 | 横断視点の重要性 |
| **大手 SaaS** | 製品独立 + 共通 Identity / Billing のみ集約 | Federated パターン |

→ 業界トレンドは明確に **「分散ガイド + 共通要素のみ中央化」**。

### §C-1.5.6 メッセージング（関係者向け）

| 誤解されやすい | 正しい説明 |
|---|---|
| ❌ 「中央 API 基盤を作って全システムで使う」| ✅ **「各システムが自前で API 基盤を持ち、標準とガイドで支援する」** |
| ❌ 「分散だとガバナンスが効かない」| ✅ **「中央集約すべき要素（認証・監査・ガードレール）は集約済、それ以外を分散」** |
| ❌ 「重複が無駄」| ✅ **「障害分離・要件最適化のメリットが、API 重複なし条件で重複コストを上回る」** |
| ❌ 「分散は旧来型」| ✅ **「分散ガイド = Platform Engineering 業界主流（Netflix / Spotify / Amazon）」** |

### §C-1.5.7 TBD / 要確認

- Q: Federated アプローチの **共通集約要素の追加候補**（例：API カタログサーバ、Backstage 等の開発者ポータル）→ `API-D-1810`
- Q: 各システムでの WAF ルール **重複コストの試算**（Service Catalog 配布で軽減される範囲）→ `API-B-625`

---

## §C-1.x 関連ドキュメント

- [§C-API-2 ランタイム選定基準](02-runtime-selection-criteria.md) — 図のうちどちらを選ぶか
- [§C-API-3 共有認証基盤との接続点](03-shared-auth-boundary.md) — 認証基盤アカウントとの境界
- [§C-API-4 監査ガバナンス](04-audit-governance.md) — 監査アカウントとの境界
- [§C-API-5 Service Catalog](05-self-service-catalog.md) — 標準提供物
