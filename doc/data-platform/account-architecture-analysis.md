# データプラットフォーム アカウントアーキテクチャ検討（社内評価メモ）

> ステータス: 🚧 ドラフト（合意形成中）
> 対象読者: **社内のみ**。プラットフォーム標準化推進者 / アプリ運用責任者 / セキュリティ・ガバナンス担当
> 位置付け: 「データプラットフォームを独立アカウントとして立てるか、各アプリアカウントで分散するか」の検討記録
> 関連: [data-platform-document-structure.md](data-platform-document-structure.md) / [internal-evaluation.md](internal-evaluation.md) / [proposal/fr/02-storage.md](proposal/fr/02-storage.md)

---

## 0. 本資料の目的

API プラットフォーム標準が「**Federated（中央集約 + 分散）**」を採用した（[../api-platform/proposal/common/01-reference-architecture.md §C-1.5](../api-platform/proposal/common/01-reference-architecture.md)）。同じ問いをデータ標準にも適用する。

**問い**:
- データプラットフォームとして**独立した AWS アカウントを立てる**か
- 各アプリアカウントで**統一したガイドにする**か

**結論**: API と同じく **Federated 採用**。ただしデータ領域固有の理由により、**中央アカウントの責務に「データガバナンス層」が加わる**。

本資料は調査根拠と判断項目を整理し、合意形成後に [proposal/common/01-architecture.md](proposal/common/01-architecture.md) §C-DATA-1 として正式化する。

---

## 1. 結論サマリ

| 項目 | 結論 |
|---|---|
| アプローチ | **Federated**（AWS Producer / Central Governance / Consumer の 3 役割）|
| API 標準との関係 | **同型**（中央集約 + 各アプリ分散）。ただし中央のスコープが Catalog 分だけ広い |
| 既存アカウントへの影響 | **最低 +1 アカウント**（Data Governance / Catalog 専用）。Consumer は組織パターンにより +0〜+1 |
| バルクデータの集約 | **しない**（Producer の S3 に置いたまま、Catalog と権限のみ中央集約）|

> **追補（§5 参照）**: 親会社統制アカウントが CloudTrail / Security Hub / Macie 等の監査・セキュリティ集約を担う場合、データ標準で必要な中央責務は **「Catalog Account」**（Lake Formation + LF-Tags + (SMC Phase 2 候補) + KMS）に縮小される。この場合 **Catalog を Consumer に同居させる Option B（+2 アカウント）が実用解として有力**。
>
> **追補 2（§5.8 参照）**: 監査責務を担うのは **新規の「監査アカウント」**（データプラットフォーム標準のスコープ外、Transit Gateway 等と同様に別組織が運用）。本標準は監査アカウントに対して **「何を送るか / 何を期待するか / 何を依存するか」を定義する側**に立つ。運用メトリクスは各アプリに保持、監査・セキュリティ系のみ集約。

### 業界根拠（要約）

| 出典 | 結論 |
|---|---|
| [AWS Prescriptive Guidance: Strategy for Data Mesh](https://docs.aws.amazon.com/prescriptive-guidance/latest/strategy-data-mesh/aws-offerings-data-mesh.html) | Producer / Central Governance / Consumer の 3 役割が**規範**。「1 つの中央データレイクアカウント」は**アンチパターン** |
| [Lake Formation Cross-Account Permissions](https://docs.aws.amazon.com/lake-formation/latest/dg/cross-account-permissions.html) | バルクデータを動かさず Catalog + 権限のみで横断クエリを実現 |
| [Secure Data Mesh Guidance on AWS](https://aws.amazon.com/solutions/guidance/secure-data-mesh-with-distributed-data-asset-ownership-on-aws) | Distributed Data Asset Ownership + Central Governance パターン |
| [Well-Architected Data Analytics Lens](https://docs.aws.amazon.com/wellarchitected/latest/analytics-lens/analytics-lens.html) | 同上を Lens として体系化 |
| 業界事例 | Netflix UDA / Spotify / BBVA など主要事例も Federated（中央モノリス・完全分散の両極端は採らない）|

---

## 2. 既存アカウント体系とのマッピング（概念モデル）

> ⚠ **本章 §2-§4 は「概念モデル」を示す**: Producer / Central / Consumer の 3 役割を独立アカウントとして描いている。**実装上の推奨配置（Option B = Catalog 同居 Consumer、+2 アカウント）は §5 を参照**。本章は理解のために役割を分離した形で示すが、§5 で物理アカウント割当を最適化する。

### 2.1 マッピング表（役割と既存アカウントの対応）

| 既存 / 新規 | アカウント | 持つもの | データ標準での役割 |
|---|---|---|---|
| **既存** | **親会社統制**（SoC / NW Firewall + CloudTrail / Security Hub / Macie / GuardDuty 等の集約）| そのまま | データ標準では **Audit / Security 集約先**として活用（§5.2 参照）|
| **既存** | **共通基盤アカウント**（認証）| そのまま | データ標準には**直接関与しない**（後述 Catalog/Governance とは責務が違うので原則同居しない）|
| **既存** | **各アプリ アカウント**（複数）| アプリ + API GW + S3 + 運用 DB | ⭐ **Producer**（生産者）兼用 |
| **概念上** | **Central Governance / Catalog 役割** | Lake Formation Catalog + LF-Tags + (SMC は Phase 2 候補、[DP-ADR-001](adr/DP-ADR-001-sagemaker-catalog-adoption-deferred.md)) + 共通 KMS | ⭐ **Central**（中央統制）— 物理配置は §5 Option A/B/C で選択 |
| **概念上** | **Consumer 役割** | Athena / Redshift / QuickSight / SageMaker | ⭐ **Consumer**（消費者）— 物理配置は §4 Pattern α/β/γ で選択 |

> **物理アカウント追加数の整理**（仮案 = Option B + Pattern β + 共通ドメイン の場合）:
> - 中央 BI / Catalog アカウント（Consumer + Catalog 同居）: **+1**
> - 共通ドメインアカウント（顧客マスタ等）: **+1**
> - 合計: **+2 アカウント**

### 2.2 図解（概念モデル）

> ⚠ 下図は **3 役割の概念モデル**を独立アカウントとして示したもの。**実装上の推奨配置（Catalog を Consumer に同居させる Option B）は §5.3 の図を参照**。

```mermaid
flowchart TB
    subgraph Existing["既存（変更なし）"]
        direction LR
        Parent["親会社統制アカウント<br/>SoC / NW Firewall +<br/>CloudTrail / SH / Macie 集約"]
        Auth["共通基盤アカウント<br/>認証"]
    end

    subgraph New["概念上の Central 役割"]
        DG["Central / Catalog<br/>・Lake Formation Catalog<br/>・LF-Tags / 権限ポリシー<br/>・SMC は Phase 2 候補 (DP-ADR-001)<br/>・共通 KMS<br/>※物理配置は §5 で決定"]
    end

    subgraph Producers["各アプリ Producer 役割兼用（既存・変更最小）"]
        direction LR
        App1["App 1 アカウント<br/>+ S3 raw/curated/analytics<br/>+ 運用 DB"]
        App2["App 2 アカウント<br/>+ S3 / 運用 DB"]
        AppN["App N ..."]
    end

    subgraph Consumer["Consumer 役割（α/β/γ パターンで変動、§4 参照）"]
        Cons["Athena / Redshift /<br/>QuickSight / SageMaker"]
    end

    DG -.Catalog 提供 + 権限委任.-> App1
    DG -.同左.-> App2
    DG -.権限付与 (RAM).-> Cons
    Cons -.横断クエリ.-> App1
    Cons -.横断クエリ.-> App2
    Parent -.CloudTrail / Audit 集約 (既存活用).-> DG
    Parent -.CloudTrail / Audit 集約.-> App1
    Parent -.CloudTrail / Audit 集約.-> Cons

    style Existing fill:#f5f5f5
    style New fill:#fff3e0
    style Producers fill:#e8f5e9
    style Consumer fill:#e3f2fd
```

### 2.3 中央 Catalog/Governance 責務を共通基盤（認証）に同居させない理由

| 観点 | 同居（共通基盤 + Catalog/Governance）| 分離（別アカウント or Consumer 同居、推奨）|
|---|:---:|:---:|
| 責務分離 | ❌ 認証 + データ統制が混在 | ✅ |
| 障害影響 | ❌ 認証障害がデータ参照を巻き込む | ✅ |
| 権限境界 | ❌ 認証管理者 ≠ データ管理者だが同 IAM 内 | ✅ |
| AWS Well-Architected | ❌ 違反（責務単一原則）| ✅ |
| コスト・運用負荷 | ◎ 1 アカウント節約 | △ 別アカウント |

→ Catalog/Governance 責務は**軽量**（バルクデータなし）でランニングコストは限定的（Lake Formation 自体は無料、KMS / CloudTrail / 監査ログのみが課金対象）。**責務分離を優先**。共通基盤との同居は不採用。同じ責務分離原則で **Catalog を Consumer に同居させる Option B** は IAM Role 分離による緩和策が必要（§5.5 参照）。

---

## 3. Lake Formation + RAM の動き — 「参照のみ」の意味

> 本章は概念モデル（Producer / Catalog / Consumer の 3 役割）を前提にデータの動きを示す。Option B 採用時は **「Catalog」と「Consumer」が同一アカウント内**になるため、ステップ ③〜⑤ のクロスアカウント通信が**アカウント内の IAM Role 間通信**に置き換わる。それ以外の動きは同じ。

### 3.1 データの物理配置とクエリの動き

```mermaid
sequenceDiagram
    autonumber
    participant App1 as App 1 アカウント<br/>(Producer)
    participant LF as Catalog 役割<br/>(Lake Formation)<br/>※Option B 時は Consumer と同居
    participant Cons as Consumer 役割<br/>(Athena)

    Note over App1, LF: 事前設定（1 回のみ）
    App1->>LF: S3 バケット委任登録<br/>「Lake Formation に管理させる」
    LF->>Cons: AWS RAM で権限共有<br/>「Finance タグ付きテーブル SELECT 可」<br/>※Option B 時は同アカウント内 IAM Role 付与に置換

    Note over App1, Cons: ランタイム（クエリ実行時）
    Cons->>LF: SELECT * FROM sales<br/>権限確認
    LF-->>Cons: 認可 OK
    Cons->>App1: App 1 の S3 を直接読みに行く
    App1-->>Cons: データ返却<br/>※物理的に App 1 の S3 に残ったまま
```

| ステップ | 何が起きるか |
|---|---|
| ①②（事前設定）| App1（Producer）が Lake Formation に「この S3 バケットを管理させる」と委任登録。Catalog 役割の Lake Formation が App1 の S3 を「登録済みデータレイクロケーション」として扱える状態にする |
| ③（事前設定）| Catalog 役割が Consumer に **「Finance タグの付いたテーブル全部、SELECT のみ許可」** を **AWS RAM** 経由で共有（Option B 時は同アカウント内の `DataAnalystRole` への IAM 権限付与）|
| ④⑤（ランタイム）| Consumer の Athena が SQL を発行 → Lake Formation に「sales テーブルへの SELECT 権限あるか」を問い合わせ → 認可成功 |
| ⑥⑦（ランタイム）| Athena は App1 アカウントの S3 を**直接読みに行く**（バイトは Consumer のクエリエンジンを通って結果として返るだけ。データそのものは App1 の S3 から動かない）|

### 3.2 「参照のみ」の正確な定義

| 操作 | Consumer アカウントから可能か |
|---|:---:|
| App1 の S3 / Catalog テーブルを **SELECT**（読む）| ✅ |
| App1 の S3 にファイルを **書く / 削除する** | ❌ 権限分離で禁止 |
| Athena / Redshift で **クエリ結果を Consumer 自身の S3 に保存** | ✅ |
| Consumer アカウント内で **集計テーブル / ML 訓練データ作成** | ✅ Consumer の自前 S3 内 |
| App1 のソースデータを書き換える | ❌ Producer 側でだけ可能 |

→ **「ソースデータへの書込み権限はない、自分のアカウント内で派生データは作れる」** が「参照のみ」の正確な意味。

### 3.3 Lake Formation + RAM vs 単純 S3 IAM 共有

なぜ単純な S3 バケットポリシー + IAM の共有では不十分か。

| 観点 | 単純な S3 IAM 共有 | Lake Formation + RAM |
|---|:---:|:---:|
| 権限の粒度 | バケット / プレフィックス単位 | **テーブル / 列 / 行レベル** |
| 機密度別マスキング | 自前実装 | **LF データフィルタで宣言的に定義** |
| 監査 | S3 ログ単独で追跡困難 | Lake Formation 監査ログで「**誰が何のテーブルにアクセスしたか**」が記録 |
| Producer 側の関与 | バケットポリシー直接編集（変更が頻繁）| **委任モデル**（Producer は Lake Formation 管理を一度承諾するだけ）|
| 横断テーブルの定義 | 不可（バケットの寄せ集めにしかならない）| ✅ Central Catalog で論理テーブル定義可能 |
| 機密度 Restricted データ取り扱い | リスク高 | ✅ 業界推奨 |

---

## 4. Consumer アカウントは何個必要か — 3 パターン

> ⚠ **本章は「Consumer 役割の配置パターン（α/β/γ）」を扱う**。各図は **§5 Option B（Catalog 同居 Consumer）を反映した実構成**として描画している。
> - **α**: 中央 Consumer がないため Option B と組み合わせ不可。Catalog Account を独立で持つ（Option A/C 相当）
> - **β** ⭐（**仮案選定**）: Catalog を中央 BI Consumer アカウントに同居
> - **γ**: Catalog を中央 BI Consumer アカウントに同居（アプリは Producer + Consumer 兼任）
>
> 3 パターン × 3 オプション の組み合わせ整理は **§5.7 マトリクス**を参照。

### 4.1 Pattern α: 各アプリが Producer + Consumer 兼用（最小構成）

各アプリ AWS アカウントが自前の S3 を持ち（Producer）、同時に自前の Athena / QuickSight で他アプリのデータも引く（Consumer）。

> ⚠ **α は Option B と組み合わせ不可**: 中央 Consumer がないため Catalog の同居先が存在しない。Catalog は **独立した Catalog Account**（Option A or C 相当）として持つ必要がある。

```mermaid
flowchart TB
    subgraph Cat["🆕 Catalog Account（新規 +1）"]
        LFCat["Lake Formation Catalog<br/>+ LF-Tags + KMS"]
    end

    subgraph A1["App 1 アカウント = Producer + Consumer"]
        S1["S3 raw/curated/analytics"]
        DB1["運用 DB"]
        Q1["Athena / Notebook"]
    end

    subgraph A2["App 2 アカウント = Producer + Consumer"]
        S2["S3 raw/curated/analytics"]
        DB2["運用 DB"]
        Q2["Athena / Notebook"]
    end

    Cat -.権限.-> A1
    Cat -.権限.-> A2
    Q1 -.横断クエリ.-> S2
    Q2 -.横断クエリ.-> S1

    style Cat fill:#fff3e0
    style A1 fill:#e8f5e9
    style A2 fill:#e8f5e9
```

**特徴**:
- **追加アカウント = Catalog Account 1 つだけ**（**+1**）
- アプリ追加 ≠ Consumer アカウント追加
- 各アプリの開発者・分析者が自分のアカウントから他アプリのデータも引ける
- **想定環境**: 小〜中規模、アプリ間の横断分析が必要だが**専属の BI チームはない**

### 4.2 Pattern β: 専用 Consumer アカウント 1 つだけ ⭐（**仮案選定**）

各アプリは Producer のみ。横断分析・BI は専属アカウントで集約。**Option B により Catalog を Consumer に同居**することで、Governance アカウントが不要に。

```mermaid
flowchart TB
    subgraph A1["App 1 acct = Producer のみ"]
        S1["S3"]
    end

    subgraph A2["App 2 acct = Producer のみ"]
        S2["S3"]
    end

    subgraph BICat["🆕 中央 BI / Catalog 同居アカウント（新規 +1、Option B）"]
        Cat["Lake Formation Catalog<br/>+ LF-Tags + KMS<br/>(DataLakeAdminRole)"]
        QS["QuickSight Author<br/>+ Athena ワークグループ<br/>+ SageMaker<br/>(DataAnalystRole)"]
    end

    BICat -.権限管理 + Catalog.-> A1
    BICat -.同左.-> A2
    BICat -.横断クエリ.-> S1
    BICat -.横断クエリ.-> S2

    style A1 fill:#e8f5e9
    style A2 fill:#e8f5e9
    style BICat fill:#fff3e0
```

**特徴**:
- **追加アカウント = 中央 BI / Catalog 同居の 1 つだけ**（**+1**、Option B 効果）
- 共通ドメイン（顧客マスタ等）を別アカウントとする場合は **+2 合計**
- 専属の BI / データ分析チームがいる組織向け
- アプリ側は分析クエリを投げない（または最小限）
- 同居の責務分離は IAM Role（`DataLakeAdminRole` / `DataAnalystRole`）で実装（[§5.5 緩和策](#55-option-b-が成立する条件と緩和策) 参照）

#### 4.2.1 §4.2 図に登場する AWS リソースの詳細解説

§4.2 の図は要点だけを示しているが、実際の構成には複数の AWS サービスが連携している。**Producer 側 / カタログ層 / 利用者層 / IAM Role** の 4 グループに分けて各リソースの役割を解説する。

##### 4.2.1.1 リソース関係図（AWS アカウント境界 + アクター + サービス/機能階層）

> **図の読み方**:
> - **太枠の Account** = **AWS アカウント境界**（Producer × N / 中央 BI / Catalog 同居 の 2 種類）
> - **黄色丸**（👤）= **アクター**（人間の役割、IAM Role）
> - **オレンジ枠** = **AWS サービス**（Glue、Lake Formation、Athena 等）
> - **サービス枠内のアイテム** = そのサービスの **機能・コンポーネント**（LF-Tags は Lake Formation の機能、Glue Data Catalog は Glue の機能）
> - **Catalog 層 / 利用者層 / 共通参照データ層は同じアカウント内**（Option B + D-2、§4.2 + [DP-ADR-003](adr/DP-ADR-003-common-domain-account-placement.md) で決定）— アカウント追加を最小化、IAM Role で責務分離
> - **共通参照データ層**（顧客マスタ等）は中央 BI / Catalog アカウント内に同居（Phase 1）。Phase 2 以降で D-1 新設の再評価あり → [§4.2.1.X](#421x-共通参照データの配置--d-2中央同居採用)
> - **Producer 側（案件側）の ETL パイプライン**（データソース → 取込層 → S3 → オーケストレーション）も図に含めるが、**詳細実装は本標準のスコープ外**（[§4.2.2.8](#4228-案件側-etl-の詳細イメージデータプラットフォーム標準のスコープ外参考情報) 参照）

```mermaid
flowchart TB
    %% Actors at top
    Steward(["👤 データスチュワード<br/>役割 2<br/>DataStewardRole"])
    Owner(["👤 データ責任者<br/>役割 1<br/>DataProductOwnerRole"])
    Admin(["👤 カタログ管理者<br/>役割 3<br/>DataLakeAdminRole"])
    Analyst(["👤 中央 BI チーム<br/>役割 4<br/>DataAnalystRole"])
    Reader(["👤 業務利用者<br/>役割 6<br/>DataReaderRole"])
    MasterMgr(["👤 共通参照<br/>データ管理者<br/>役割 5"])

    %% Producer Account 1
    subgraph App1Account["🟢 AWS アカウント: App 1 (Producer、既存活用) ※ETL 詳細はスコープ外 §4.2.2.8"]
        direction TB

        subgraph App1Sources["💼 データソース（業務システム）"]
            direction LR
            App1Aurora[("Aurora / RDS<br/>業務 OLTP")]
            App1Dynamo[("DynamoDB<br/>サービスメタ")]
            App1AppLog["アプリログ<br/>ECS / Lambda"]
            App1ExtSaaS["外部 SaaS<br/>Salesforce 等"]
            App1ExtCust["顧客社内システム<br/>SFTP / Email"]
        end

        subgraph App1Ingest["📥 取込層 (Ingestion)"]
            direction LR
            App1DMS[AWS DMS<br/>CDC / Bulk]
            App1KFH[Kinesis<br/>Data Firehose]
            App1AppFlow[AWS AppFlow]
            App1Transfer[Transfer Family<br/>+ Lambda]
        end

        subgraph App1S3["Amazon S3"]
            direction LR
            App1S3raw[raw 層]
            App1S3cur[curated 層]
            App1S3ana[analytics 層]
        end

        subgraph App1Glue["AWS Glue"]
            direction LR
            App1GlueCat["Glue Data Catalog<br/>※App1 自身の S3 の<br/>テーブル定義"]
            App1Crawler[Glue Crawler]
            App1ETL[Glue ETL Flex<br/>+ Glue Data Quality]
        end

        subgraph App1Orch["🔁 オーケストレーション / 監視"]
            direction LR
            App1StepFn[Step Functions]
            App1EvBridge[EventBridge<br/>Scheduler]
            App1CW[CloudWatch<br/>Alarms + Logs]
        end
    end

    %% Producer Account N
    subgraph AppNAccount["🟢 AWS アカウント: App N (Producer、既存活用)"]
        direction TB
        AppNetc["...App 1 と同じ構造で N 個...<br/>(データソース / 取込層 / S3 / Glue / オーケストレーション)"]
    end

    %% Central BI / Catalog Account (Catalog + User + Common Reference Data layers in same account, Option B + D-2)
    subgraph CentralAccount["🟠 AWS アカウント: 中央 BI / Catalog 同居 (Option B + D-2、新規 +1 のみ)"]
        direction TB

        subgraph CatLayer["📚 カタログ層（管理: DataLakeAdminRole）"]
            direction LR
            subgraph LakeFormation["AWS Lake Formation"]
                LFTags[LF-Tags<br/>機能<br/>※domain=common 等]
                LFGrants[Cross-account Grants<br/>機能]
            end
            subgraph GlueCentral["AWS Glue"]
                GlueCatCentral["Glue Data Catalog<br/>※Lake Formation 利用基盤<br/>Producer Catalog を Federation 参照<br/>+ 'common_domain' DB を内包"]
            end
            subgraph KMSSvc["AWS KMS"]
                KMSCMK[CMK 共通暗号鍵]
            end
        end

        subgraph CommonRefLayer["🟡 共通参照データ層 (D-2 同居、管理: CommonReferenceDataManagerRole)"]
            direction LR
            subgraph CommonS3Svc["Amazon S3"]
                CommonS3["common-domain バケット<br/>顧客マスタ / 組織マスタ<br/>標準勘定科目 等"]
            end
        end

        subgraph UserLayer["📊 利用者層（管理: DataAnalystRole / DataReaderRole）"]
            direction LR
            subgraph AthenaSvc["Amazon Athena"]
                AthenaWG[Workgroups]
            end
            subgraph QSSvc["Amazon QuickSight Enterprise"]
                QSDash[ダッシュボード / SPICE]
            end
            subgraph SMSvc["Amazon SageMaker (Phase 2)"]
                SMStudio[Studio]
            end
            subgraph S3Result["Amazon S3"]
                S3Res[athena-results<br/>派生データ]
            end
        end
    end

    %% Producer side - Actor responsibilities
    Steward -.実装・運用.-> App1ETL
    Steward -.実装・運用.-> App1Crawler
    Steward -.実装・運用.-> App1Ingest
    Steward -.実装・運用.-> App1Orch
    Owner -.公開承認.-> App1GlueCat

    %% Producer side - Data source → Ingestion
    App1Aurora --> App1DMS
    App1Dynamo --> App1KFH
    App1AppLog --> App1KFH
    App1ExtSaaS --> App1AppFlow
    App1ExtCust --> App1Transfer

    %% Producer side - Ingestion → S3 raw
    App1DMS --> App1S3raw
    App1KFH --> App1S3raw
    App1AppFlow --> App1S3raw
    App1Transfer --> App1S3raw

    %% Producer side - S3 transformation flow
    App1S3raw -->|raw → curated| App1ETL
    App1ETL --> App1S3cur
    App1S3cur -->|curated → analytics| App1ETL
    App1ETL --> App1S3ana

    %% Producer side - Crawler
    App1Crawler -.スキャン.-> App1S3raw
    App1Crawler -.スキャン.-> App1S3cur
    App1Crawler -.スキャン.-> App1S3ana
    App1Crawler -->|テーブル定義更新| App1GlueCat

    %% Producer side - Orchestration controls
    App1EvBridge -.起動.-> App1StepFn
    App1StepFn -.制御.-> App1DMS
    App1StepFn -.制御.-> App1ETL
    App1StepFn -.制御.-> App1Crawler
    App1ETL -.ログ.-> App1CW
    App1DMS -.ログ.-> App1CW

    %% Central catalog
    Admin -.LF / Tag 管理.-> LakeFormation
    Admin -.鍵管理.-> KMSCMK
    LakeFormation -.認可レイヤー.-> GlueCatCentral

    %% Cross-account Federation (Producer → Central)
    App1GlueCat -.Cross-account<br/>Federation.-> GlueCatCentral
    AppNetc -.Federation.-> GlueCatCentral

    %% Encryption (KMS → Producer S3)
    KMSCMK -.暗号化.-> App1S3raw

    %% Consumer queries (利用者層 → Producer S3 を直接読込)
    Analyst -.クエリ作成.-> AthenaWG
    Analyst -.ダッシュ作成.-> QSDash
    Analyst -.ML 開発.-> SMStudio
    Reader -.閲覧.-> QSDash
    AthenaWG -.認可問合せ.-> LakeFormation
    AthenaWG -.メタデータ参照.-> GlueCatCentral
    AthenaWG -.データ直読.-> App1S3ana
    AthenaWG -.結果保存.-> S3Res
    QSDash -.SQL.-> AthenaWG
    SMStudio -.学習データ取得.-> App1S3ana

    %% Common Reference Data Layer (D-2 同居)
    MasterMgr -.管理.-> CommonS3
    MasterMgr -.スキーマ管理.-> GlueCatCentral
    KMSCMK -.暗号化.-> CommonS3
    AthenaWG -.横断クエリ.-> CommonS3

    %% Styling - Account boundaries with thick borders
    style App1Account fill:#e8f5e9,stroke:#388e3c,stroke-width:3px
    style AppNAccount fill:#e8f5e9,stroke:#388e3c,stroke-width:3px
    style CentralAccount fill:#fff3e0,stroke:#e65100,stroke-width:3px

    %% Layer backgrounds - Producer side (ETL pipeline = スコープ外、点線)
    style App1Sources fill:#f5f5f5,stroke:#999,stroke-dasharray: 3 3
    style App1Ingest fill:#fff3e0,stroke:#999,stroke-dasharray: 3 3
    style App1Orch fill:#e3f2fd,stroke:#999,stroke-dasharray: 3 3

    %% Layer backgrounds - Central side
    style CatLayer fill:#ffebee
    style CommonRefLayer fill:#fff8e1
    style UserLayer fill:#e3f2fd

    %% AWS Service boxes
    style LakeFormation fill:#ffcc99
    style GlueCentral fill:#ffd5cc
    style App1Glue fill:#ffd5cc
    style App1S3 fill:#ccffcc
    style S3Result fill:#ccddff
    style CommonS3Svc fill:#ccffcc
    style AthenaSvc fill:#ccddff
    style QSSvc fill:#ccddff
    style SMSvc fill:#ccddff
    style KMSSvc fill:#fff

    %% Actors
    style Steward fill:#fffacd
    style Owner fill:#fffacd
    style Admin fill:#fffacd
    style Analyst fill:#fffacd
    style Reader fill:#fffacd
    style MasterMgr fill:#fffacd
```

###### AWS アカウント境界の整理

| アカウント | 種類 | 数 | 役割 |
|---|---|:---:|---|
| 🟢 **App アカウント**（Producer）| 既存 | **N 個** | アプリ稼働 + Producer 役割兼任。S3 にデータを保管、Glue Catalog で自身のテーブル定義 |
| 🟠 **中央 BI / Catalog アカウント**（Option B + D-2 同居）| 新規 | **1 個** | **カタログ層 / 利用者層 / 共通参照データ層を同居**。3 層は IAM Role で責務分離: `DataLakeAdminRole`（カタログ）/ `CommonReferenceDataManagerRole`（共通参照データ）/ `DataAnalystRole`+`DataReaderRole`（利用者） |

→ **アカウント追加合計: +1 のみ**
→ 共通ドメインアカウントの **D-1 新設は Phase 2 以降の再評価候補**（[DP-ADR-003](adr/DP-ADR-003-common-domain-account-placement.md)）

###### Producer 側 ETL パイプラインの構成要素（**点線枠 = 本標準のスコープ外、参考**）

Producer アカウント内には ETL パイプラインに必要な以下のコンポーネントが存在する。**本標準ではインターフェース契約（S3 への着地データの規約）のみを定め、ETL の実装は案件側の自由**:

| # | 構成要素 | 主な役割 | 代表サービス | 詳細 |
|---|---|---|---|---|
| 💼 | **データソース** | 業務システムの原本データ | Aurora / RDS / DynamoDB / アプリログ / 外部 SaaS / SFTP | [§4.2.2.8.1](#42281-案件側-etl-の全体像典型パターン) |
| 📥 | **取込層 (Ingestion)** | データソース → S3 raw への運搬 | AWS DMS / Kinesis Firehose / AppFlow / Transfer Family + Lambda | [§4.2.2.8.3](#42283-取込層の選定マトリクス--詳細) |
| 🗄 | **S3 (Medallion)** | raw → curated → analytics の 3 層構造 | Amazon S3 + パーティション + Parquet | [§4.2.2.8.4](#42284-変換層の典型実装--詳細) |
| 🛠 | **Glue (変換 + メタデータ)** | クレンジング、PII マスキング、`tenant_id` 強制、Catalog 登録 | Glue ETL Flex / Glue Data Quality / Glue Crawler | [§4.2.2.8.4](#42284-変換層の典型実装--詳細) / [§4.2.3](#423-glue-crawler-の位置付けと運用) |
| 🔁 | **オーケストレーション / 監視** | ジョブ起動・依存関係・リトライ・通知 | Step Functions / EventBridge Scheduler / CloudWatch Alarms + Logs | [§4.2.2.8.6](#42286-オーケストレーションの典型実装--詳細) |

> ⚠ **スコープの境界**: 図中の **点線枠（💼 / 📥 / 🔁）は本標準のスコープ外**。案件側のデータエンジニアリングチームが選定・実装する。本標準は「**S3 への着地データの規約**」（バケット命名 / パーティション / 暗号化 / `tenant_id` / Catalog 登録）のみを課す。詳細は [§4.2.2.8.11 案件側に守ってもらうインターフェース契約](#422811-標準として案件側に守ってもらうことインターフェース契約)。

###### アクター（役割と IAM Role）の整理

| アクター | 役割 | IAM Role | 主な操作 |
|---|---|---|---|
| 👤 **データ責任者** | 役割 1 | `DataProductOwnerRole` | データ製品公開の承認、利用申請の承認 |
| 👤 **データスチュワード** | 役割 2 | `DataStewardRole` | Producer 側 ETL / Crawler の運用、スキーマ管理、データ品質責任 |
| 👤 **カタログ管理者** | 役割 3 | `DataLakeAdminRole` | Lake Formation 管理、LF-Tag 体系、KMS、クロスアカウント Grants |
| 👤 **中央 BI チーム** | 役割 4 | `DataAnalystRole` | Athena / QuickSight / SageMaker での分析・ダッシュ作成 |
| 👤 **共通参照データ管理者** | 役割 5 | （兼任、Phase 1）| 顧客マスタ等の整備・スキーマ管理 |
| 👤 **業務利用者** | 役割 6 | `DataReaderRole` | QuickSight ダッシュボード閲覧 |
| 👤 **監査担当者**（図には表示せず）| 役割 7 | （既存 Audit Role）| 監査アカウント（§5.8 参照）経由でログ確認 |

###### サービスと機能の階層理解（重要）

| AWS サービス | このサービスが含む機能 | 単独サービス / 他サービスとの関係 |
|---|---|---|
| **AWS Glue** | Glue Data Catalog（メタデータストア）/ Glue Crawler / Glue ETL Jobs / Glue Schema Registry / Glue Data Quality | 独立したサービス、上に他のサービス（Lake Formation / Athena）が乗る基盤 |
| **AWS Lake Formation** | LF-Tags（タグベース ABAC）/ Cross-account Grants / 監査ログ | **自身は Catalog を持たず、Glue Data Catalog を利用**して認可レイヤーを提供する |
| **Amazon Athena** | Workgroups / クエリエンジン（Trino ベース）/ Result Reuse | Glue Data Catalog からメタデータ取得、Lake Formation に認可問合せ、S3 を直接読込 |
| **Amazon QuickSight** | ダッシュボード / SPICE（インメモリ）/ Q（自然言語）| データソースとして Athena 等を利用 |
| **Amazon SageMaker** | Studio / Training / Inference / Model Registry | S3 / Glue Catalog を学習データ取得経路として利用 |
| **AWS KMS** | CMK / 鍵ポリシー / 鍵ローテーション | 独立、各サービスから暗号化用途で参照 |
| **Amazon S3** | バケット / Object Lock / ライフサイクル | 独立、データの実体保存先 |

→ **「LF-Tags は Lake Formation の機能」「Glue Data Catalog は Glue の機能」**を図でも明示的に表現（各 AWS サービスの subgraph 内に機能を配置）。

###### Producer 側の Glue Data Catalog の意味（明確化）

**Producer 側 Glue Data Catalog は「その App 自身の S3 データ」を記述します**:

| 機能 | 内容 |
|---|---|
| **何を記述するか** | App 自身の S3 raw / curated / analytics 各層のデータベース定義・テーブル定義・パーティション情報 |
| **誰が書込むか** | Glue Crawler（スキーマ自動検出時）/ Glue ETL Jobs（書込み時に明示登録）/ Athena DDL（CREATE TABLE）|
| **誰が読込むか** | Glue ETL（スキーマ参照）/ Athena（クエリ時のメタデータ）/ Lake Formation（Federation 経由で中央から参照）|
| **中央への共有** | Cross-account Glue Catalog Federation で **中央 Glue Catalog から透過的に参照**される |

**Central 側 Glue Data Catalog の意味**:

| 機能 | 内容 |
|---|---|
| **何を記述するか** | Federation で参照する Producer Catalog のテーブル + 共通ドメインのテーブル + Athena CTAS 等で作成した派生テーブル |
| **Lake Formation との関係** | **Lake Formation が認可レイヤーとしてこの Catalog を利用**（Lake Formation 自身は Catalog を持たない）|
| **LF-Tags はどこに付くか** | この **中央 Glue Catalog のテーブル / 列**に LF-Tags が付与される |
| **Athena は何を見るか** | クエリ時に **中央 Glue Catalog** からメタデータを取得、Lake Formation に認可問合せ、S3 を直接読込 |

→ **「Lake Formation は Glue Catalog の上に乗る認可レイヤー」**という関係を明示的に図に反映（点線「認可レイヤー」で表現）。

##### 4.2.1.X 共通参照データの配置 — D-2（中央同居）採用

> **意思決定**: **Phase 1 では D-2（中央 BI / Catalog アカウントに同居）を採用**。共通ドメインアカウント新設（D-1）は Phase 2 以降の再評価候補として保留。
> **判断記録**: [DP-ADR-003: 共通参照データの配置](adr/DP-ADR-003-common-domain-account-placement.md)
> **背景**: 過去の議論（strawman §1.3 / 当章 §5.5）で「共通ドメインアカウント新設」を提案していたが、Phase 1 規模では責務分離効果に対しアカウント運用コストが見合わないと判断し、D-2 に集約した。**判断経緯は本節 A〜F で記録し、ADR を正とする**。

###### A. 何のためのアカウントか

「**特定のアプリに所属しないが、複数アプリから参照される共通参照データ**」を保管・管理する独立 AWS アカウント。

**典型的に置く想定のデータ**:

| データ | 例 | なぜ「共通」か |
|---|---|---|
| **顧客マスタ** | 顧客企業 ID / 名称 / 業種 / 契約プラン / 解約日 | 経費精算 SaaS の利用状況と CRM の商談履歴を突合する際に、両者が同じ顧客 ID 体系を使う必要がある |
| **組織マスタ** | 顧客企業内の部署階層 / 従業員ロール | 多くの SaaS 製品が「同じ組織階層」を前提に動く |
| **標準勘定科目マスタ** | 経費精算 SaaS の費目 / 会計連携用コード | 個別アプリのコードと SaaS 提供側の標準コードのマッピング |
| **国・地域コード / 通貨マスタ** | ISO 3166 / ISO 4217 等 | アプリ非依存の汎用マスタ |
| **共通分析ディメンション** | 業種分類 / 企業規模区分 / 商圏定義 | クロスアプリ分析の軸 |

###### B. なぜ「特定アプリに寄せない」のか

```
❌ 経費精算 SaaS のアカウントに顧客マスタを置くと:
   - CRM / 営業支援 SaaS / ERP からも参照するため、依存方向が「経費精算 → 他」と逆転
   - 経費精算チームが顧客マスタの責任を負うのは責務範囲外
   - 経費精算アカウントの障害・変更が全 SaaS の分析を止める

✅ 共通ドメインアカウントに置くと:
   - どの SaaS アプリにも従属せず、横断データの「中立な所有者」になる
   - 共通参照データ管理者（役割 5）が責任を持つ
   - 個別アプリの稼働とは独立した寿命を持てる
```

###### C. 採用した場合の構成

| 要素 | 内容 |
|---|---|
| **アカウント** | AWS Organizations 配下の独立アカウント 1 個 |
| **保管先** | S3 + Glue Data Catalog（Producer と同じ構造）|
| **管理者** | 共通参照データ管理者（役割 5）。Phase 1 では中央 BI チームが兼任する想定 |
| **更新方法** | 顧客マスタ等は契約管理システム or Salesforce 等から日次連携 / 標準コードは手動 GitOps |
| **公開方法** | Cross-account Glue Catalog Federation で中央 Catalog から参照、Athena 横断クエリで利用 |
| **コスト** | S3 数 GB + Glue Catalog 無料枠内 + 連携ジョブ（Lambda or Glue ETL）程度。月 $10-50 規模 |

###### D. 代替案との比較

| 代替案 | 概要 | メリット | デメリット | 評価 |
|---|---|---|---|---|
| **D-1: 共通ドメインアカウント新設**（現提案）| 専用アカウント +1 | 責務明確、SaaS 非依存、独立した寿命 | アカウント +1、管理者ロール定義が必要 | ⭕ **本案** |
| **D-2: 中央 BI / Catalog アカウントに同居** | Catalog アカウント内に共通マスタ S3 を置く | アカウント追加なし | カタログ層と「共通参照データ」の責務が混在、Catalog 管理者と共通参照データ管理者の責任が曖昧化 | △ |
| **D-3: 既存の代表アプリに寄せる** | 例: 経費精算 SaaS アカウントに置く | 新規アカウント不要 | **依存方向の逆転 / 責務範囲外 / 障害影響伝播**（上記 B の問題） | ❌ |
| **D-4: マスタ専用 SaaS / MDM 製品導入** | Reltio / Informatica MDM 等 | 高機能（名寄せ、来歴管理）| SaaS 不採用方針に抵触、コスト高 | ❌ |
| **D-5: 採用しない（共通参照データは持たない）** | アプリごとに独自マスタで管理、突合は都度 | アカウント +0 | クロスアプリ分析が事実上不可能 / 顧客マスタ 1 件の不整合が全社で発生 | ❌（分析価値が大きく毀損）|

###### E. 採否を分ける質問（ヒアリング）

| 質問 | 「YES なら D-1 採用」 |
|---|---|
| 複数 SaaS 製品で同じ顧客企業を参照することがあるか | ✅ クロスアプリ分析がある |
| 顧客マスタ等を「どの SaaS にも所属しない中立データ」と扱いたいか | ✅ 責務分離を重視 |
| 共通マスタの責任者を BI/Catalog チームと分離したいか | ✅ 役割 3 と役割 5 を分ける |
| 将来 SaaS 製品を増やす計画があり、毎回マスタ依存を再設計したくないか | ✅ 拡張性を重視 |

→ **3 つ以上 YES なら D-1（共通ドメインアカウント新設）を採用**、それ以外なら D-2（中央同居）に縮退、または D-5（持たない）も選択肢。

###### F. Phase 1 採用方針と Phase 2 再評価条件

**Phase 1 採用方針**: **D-2（中央 BI / Catalog アカウント同居）** → 詳細は [DP-ADR-003](adr/DP-ADR-003-common-domain-account-placement.md)

| 観点 | Phase 1 採用内容 |
|---|---|
| **F-1**: 共通参照データの配置 | **中央 BI / Catalog アカウント内に同居**。独立 S3 バケット + Glue Catalog `common_domain` DB で識別 |
| F-2: 役割 5 の兼任 | Phase 1 は中央 BI チームが兼任、`CommonReferenceDataManagerRole` を別途定義し IAM で責務分離 |
| F-3: マスタソース | 契約管理 SaaS / Salesforce 等、顧客のシステム構成依存（ヒアリング項目）|
| F-4: 書込み権限 | `CommonReferenceDataManagerRole` のみ、Producer / Consumer は読込のみ |

**Phase 2 以降の D-1 移行トリガ**（[DP-ADR-003 §4.1](adr/DP-ADR-003-common-domain-account-placement.md) 参照）:

| カテゴリ | トリガ条件 |
|---|---|
| 規模 | 共通参照データの S3 サイズが 100 GB 超 / 月間アクセス頻度が中央 BI 層の 50% 超 |
| 組織 | 役割 5 が中央 BI チームから専任化 |
| SaaS ポートフォリオ | 共通参照データに依存する SaaS 製品が 5 つ以上 |
| マスタ管理機能 | 来歴管理・名寄せ等、Glue/Athena では不足する機能が要求 |
| 障害影響 | Catalog 層障害で共通参照データ参照が年 2 回以上停止 |
| 規制・監査 | アクセスログを物理分離する規制要件 |

**移行容易性**: D-2 → D-1 は 3-4 週間で移行可能（DDL エクスポート + S3 Replication + Federation 再設定）。クエリで使う DB 名 `common_domain` を最初から固定することで、Federation 経由でも同じ名前を維持できる設計とする。

##### 4.2.1.2 Producer 側（各アプリアカウント）のリソース

| リソース | 概要 | 本構成での役割 | 補足 |
|---|---|---|---|
| **S3 (Simple Storage Service)** | AWS のオブジェクトストレージ。無制限容量・11 nines 耐久性 | データレイクの中核。各アプリが「自分のデータ」を所有 | 暗号化（SSE-KMS）必須、ライフサイクルポリシーで Standard → IA → Glacier の自動移行 |
| **S3 raw 層** | 生データ層（Bronze）| アプリから直接取り込んだ生データ（JSON / CSV / Parquet 等）| 不変、Object Lock 検討、長期保管前提 |
| **S3 curated 層** | 整形済み層（Silver）| クレンジング・正規化・PII マスキング済（Parquet 推奨）| ETL ジョブで生成、データ品質チェック後 |
| **S3 analytics 層** | 分析用層（Gold）| 集計済み・分析に最適化されたテーブル（Parquet + パーティション）| BI / ML が直接クエリする層、`tenant_id` パーティション含む |
| **Glue Data Catalog（ローカル）** | 各アプリのテーブル定義・スキーマ・パーティション情報 | アプリ内のテクニカルメタデータストア | 中央 Lake Formation に Federate されて統合される |

##### 4.2.1.3 カタログ層（`DataLakeAdminRole` が管理）のリソース

| リソース | 概要 | 本構成での役割 | 補足 |
|---|---|---|---|
| **AWS Lake Formation** | AWS の中央データレイクガバナンスサービス | データレイクの「**ガバナンス層**」。表 / 列 / 行レベルのアクセス制御、クロスアカウント Catalog 提供、監査ログ | 各 Producer の S3 を「Federated Catalog」として束ねる |
| **Glue Data Catalog（中央）** | テーブル定義・スキーマ・パーティションのメタデータストア | Lake Formation の**下層**。Athena / Redshift Spectrum / EMR がメタデータを読む層 | Lake Formation = Glue Data Catalog + 権限管理層 |
| **LF-Tags (Lake Formation Tags)** | リソース（DB / テーブル / 列）に付与するキーバリュー型タグ | **タグベースアクセス制御（TBAC）** を実装。例: `機密度=Restricted` / `ドメイン=Finance` / `PII=Yes` | 個別テーブルへの権限付与より運用効率が高い。「Finance ドメインの PII=No なテーブル全て、SELECT 許可」のような宣言的設定 |
| **KMS CMK (Customer Managed Key)** | AWS の暗号鍵管理サービス、利用者が管理する鍵 | データレイク全体の暗号化に使用。鍵の生成・ローテーション・廃棄を管理 | アカウント間で鍵ポリシーを設定すれば、App 側からも CMK を使える（クロスアカウント暗号化） |

##### 4.2.1.4 利用者層（`DataAnalystRole` が管理）のリソース

| リソース | 概要 | 本構成での役割 | 補足 |
|---|---|---|---|
| **Athena** | AWS のサーバーレス SQL クエリエンジン（Trino ベース）| S3 上のデータを直接 SQL でクエリ。スキャンしたデータ量に応じた従量課金 | Lake Formation と統合され、認可は LF 経由 |
| **Athena ワークグループ** | クエリ実行の論理コンテナ | **用途別に分離**: 探索用 / BI 用 / 監査用 / アプリ問い合わせ用 など | 各 WG にクエリ結果保存先・スキャン量上限（コスト統制）・ログ出力先・暗号化設定 |
| **QuickSight Enterprise** | AWS の BI / ダッシュボードサービス | 経営層・CS・PM 等の業務利用者向けダッシュボード提供 | Enterprise Edition は **行レベルセキュリティ（RLS）対応** → テナント分離に重要 |
| **QuickSight Author** | ダッシュボード作成可能なユーザー権限 | 中央 BI チームのリーダーが該当 | ライセンス: ユーザーあたり月額（Reader より高い）|
| **QuickSight Reader** | ダッシュボード閲覧のみ可能なユーザー権限 | 業務利用者（経営層・CS・PM 等）が該当 | ライセンス: ユーザーあたり月額（Author より安い）、Author:Reader 比率は **1:10** 想定 |
| **QuickSight SPICE** | インメモリ計算エンジン | ダッシュボード応答時間を秒オーダーに高速化 | ピーク負荷のあるダッシュボードは SPICE 利用必須 |
| **SageMaker Studio** | AWS の機械学習プラットフォーム | 解約予兆検知 / 顧客健全性スコア / 業界別利用パターン分析 等の ML 開発 | Phase 2 から本格採用想定。Notebook / Training / Inference / Model Registry |
| **S3 athena-results** | Athena のクエリ結果保存用 S3 バケット | クエリ結果の中間ファイル保存、再利用・キャッシュにも使用 | ワークグループ単位で別バケット推奨（機密度別分離）|

##### 4.2.1.5 IAM Role 体系

[§5.5 緩和策](#55-option-b-が成立する条件と緩和策) で定めた 3 階層 Role の権限詳細:

| Role | 担当 | 主な権限 | 主な制約 |
|---|---|---|---|
| **`DataLakeAdminRole`** | 役割 3<br/>カタログ管理者（1-2 名）| ・Lake Formation 管理（Database / Table / Permission）<br/>・LF-Tags の作成・編集・付与<br/>・クロスアカウント Grant<br/>・KMS CMK 管理<br/>・データレイク全データへの読み権限（デバッグ用）| ・通常の業務 BI 操作はしない（QuickSight ダッシュボード作成等）<br/>・**Phase 1: 1-2 名のみ AssumeRole 可能**<br/>・常時ログインなし、必要時のみ一時利用 |
| **`DataAnalystRole`** | 役割 4<br/>中央 BI チーム（2 名）| ・Athena クエリ実行（許可された WG 内）<br/>・QuickSight ダッシュボード作成・編集・閲覧<br/>・自分の S3 結果バケットへの書込み<br/>・SageMaker での ML 開発（Phase 2）| ・**Lake Formation 管理操作は Permission Boundary で拒否**<br/>・他アプリの S3 への書込み不可<br/>・KMS 管理操作は不可<br/>・LF-Tags の変更不可 |
| **`DataReaderRole`** | 役割 6<br/>業務利用者（10 名）| ・QuickSight ダッシュボード閲覧のみ<br/>・許可された定形クエリのみ実行（Athena Saved Queries）| ・新規クエリ作成不可<br/>・データのダウンロード制限（QuickSight からの Export 制限）<br/>・LF-Tags / Lake Formation 管理は不可 |

##### 4.2.1.6 Permission Boundary と SCP（補強）

Role 間の境界を強制するためのガードレール:

| 制御 | 仕組み | 目的 |
|---|---|---|
| **Permission Boundary** | 各 IAM Role に付与する「上限ポリシー」 | `DataAnalystRole` から `lakeformation:*` の API 呼び出しを拒否 → 役割 4 が Catalog を操作できないことを保証 |
| **SCP (Service Control Policy)** | Organization レベルで設定するアカウント全体の制約 | 中央 BI / Catalog アカウント内で意図しない権限上昇（IAM Role 作成・PolicyVersion 変更等）を予防 |
| **AWS Config Rules** | 構成監視ルール | 「`DataLakeAdminRole` と `DataAnalystRole` を兼任するユーザー」を検出 → 役割 3 / 4 の人員重複を防止（Option B 成立前提） |

##### 4.2.1.7 図にはないが関連する重要リソース

§4.2 図は要点だけを示しているため、以下も実構成では存在する:

| リソース | 役割 | 配置 |
|---|---|---|
| **AWS RAM (Resource Access Manager)** | クロスアカウント Lake Formation 権限共有の裏で使用される AWS の基盤サービス | Lake Formation 内部で自動利用（明示的に意識不要）|
| **CloudTrail Data Events** | データプレーン操作（S3 オブジェクトアクセス、Lake Formation 操作、KMS 鍵使用）のログ | [§5.8 監査責務分離](#58-監査責務分離の具体設計option-b-採用時--新規監査アカウント前提) で監査アカウントへ送付 |
| **VPC エンドポイント** | プライベートネットワーク経由で S3 / Athena / Lake Formation にアクセス | 全アカウントで設定、データの公開ネットワーク経由を回避 |
| **Glue ETL** | データ変換ジョブ（raw → curated → analytics）| Producer 側（各アプリ）が運用 |
| **Glue Crawler** | スキーマ自動検出 + Glue Catalog 登録 | Producer 側で運用、新規データ発生時に実行 |

#### 4.2.2 ETL 的な処理の配置

##### 4.2.2.1 配置の原則: 「データを生む側が ETL する」

Data Mesh の **Domain Ownership** 原則に従う:
- **データの取り込み・整形・自前集計は Producer 側**（各アプリ）
- **横断集計・SaaS 提供側の派生データ生成は Central 側**（中央 BI / Catalog）
- **顧客企業ごとの分析（仮にスコープに含む場合）は Consumer 側**

##### 4.2.2.2 図解: ETL のデータフロー全体像

```mermaid
flowchart LR
    subgraph App["各アプリアカウント (Producer)"]
        direction TB
        DB["運用 DB<br/>Aurora/RDS/DynamoDB"]
        Stream["イベント/ストリーム<br/>(SaaS アプリの動作ログ等)"]
        Ext["外部システム<br/>(顧客の会計/HR システム)"]

        Ingest["**取り込み**<br/>DMS / Lambda /<br/>Kinesis / EventBridge"]

        S3R["S3 raw"]
        ETL1["**raw → curated**<br/>Glue ETL / Step Functions"]
        S3C["S3 curated"]
        ETL2["**curated → analytics**<br/>Glue ETL / Athena CTAS"]
        S3A["S3 analytics"]

        Quality["Glue Data Quality<br/>(品質チェック)"]
    end

    subgraph Central["中央 BI / Catalog (Option B)"]
        direction TB
        CTAS["**横断集計**<br/>Athena CTAS<br/>(派生テーブル生成)"]
        SMP["**ML 前処理**<br/>SageMaker Processing<br/>(Phase 2)"]
        S3Derived["S3 派生データ<br/>(横断集計・ML 訓練データ)"]
    end

    DB --> Ingest
    Stream --> Ingest
    Ext --> Ingest
    Ingest --> S3R
    S3R --> ETL1
    ETL1 --> S3C
    S3C --> ETL2
    ETL2 --> S3A
    ETL1 -.チェック.-> Quality
    ETL2 -.チェック.-> Quality

    S3A -.横断クエリ.-> CTAS
    CTAS --> S3Derived
    S3A -.特徴量.-> SMP
    SMP --> S3Derived

    style App fill:#e8f5e9
    style Central fill:#e3f2fd
```

##### 4.2.2.3 ETL の 3 種類と配置詳細

###### A. Producer 側 ETL（各アプリアカウント、主役）

最も多くの ETL がここに集中する。各アプリチームが**自データの所有者として実装責任**を持つ。

| 段階 | 内容 | 主な用途 |
|---|---|---|
| **データ取り込み（Ingestion）** | 運用 DB / 外部システム → S3 raw | リアルタイム性・整合性の確保 |
| **raw → curated** | クレンジング・正規化・PII マスキング・`tenant_id` 強制付与 | データ品質と機密度制御 |
| **curated → analytics** | 集計・パーティション化・Parquet 化・分析用最適化 | 分析クエリのパフォーマンス向上 |

###### B. Central 側 ETL（中央 BI / Catalog アカウント、横断分析用）

顧客企業横断・SaaS 提供側の集計が中心。中央 BI チームが実装責任を持つ。

| 内容 | 主な用途 |
|---|---|
| **横断テナント集計** | 顧客健全性スコア計算、業界別利用パターン分析 |
| **派生データ生成** | BI 用の事前集計テーブル、月次レポート用集計 |
| **ML 前処理** | 解約予兆検知モデルの訓練データ作成（Phase 2）|
| **データ統合** | 複数アプリのデータを Join した派生テーブル |

###### C. 外部連携系 ETL（Producer 側に組み込まれる）

顧客企業のシステムからデータを取り込む特殊な ETL。

| 内容 | 配置 |
|---|---|
| 顧客会計システム連携 | Producer 側（経費精算 SaaS 内）+ AWS Transfer Family / Glue Custom Connector |
| 法人カード明細 | 同上 + 外部 SaaS API 連携 |
| 人事システムからの組織マスタ取り込み | 中央 BI/Catalog アカウント内の共通参照データ層（D-2、[DP-ADR-003](adr/DP-ADR-003-common-domain-account-placement.md)）|

##### 4.2.2.4 ETL ツール選定マトリクス

| 用途 | 推奨ツール | 配置 | 補足 |
|---|---|---|---|
| **バッチ取り込み** | AWS Glue ETL, Step Functions | Producer | スケジュール実行、複数ジョブのオーケストレーション |
| **ストリーム取り込み** | Kinesis Data Firehose, MSK | Producer | リアルタイム性が必要な場合 |
| **CDC 取り込み** | DMS, Aurora Zero-ETL | Producer | 運用 DB → S3 のニアリアルタイム同期 |
| **小規模変換** | AWS Lambda | Producer | イベント駆動・軽量処理 |
| **大規模 Spark 変換** | AWS Glue ETL（Spark mode）, EMR Serverless | Producer | TB 級データの一括変換 |
| **横断集計（テナント横断）** | Athena CTAS（Create Table As Select）| Central | SQL ベースで完結、サーバーレス |
| **ML 前処理** | SageMaker Processing | Central | Phase 2 から、scikit-learn / Spark 等 |
| **データ品質チェック** | AWS Glue Data Quality | Producer 主体 | NULL 率・型違反・重複率の自動検出 |
| **パイプライン管理** | AWS Step Functions, EventBridge Scheduler | Producer | リトライ・分岐・並列実行 |
| **スキーマ自動検出** | AWS Glue Crawler | Producer | 新規データ発生時に Catalog 自動更新 |

##### 4.2.2.5 関連する非 ETL 処理（補足）

ETL とは別だが密接に関連する処理:

| 処理 | 配置 | ツール | 内容 |
|---|---|---|---|
| **データ品質監視**（NULL 率・鮮度・重複率）| Producer | Glue Data Quality | パイプライン実行後にチェック、閾値超えで通知 |
| **データリネージ追跡** | Central + Producer | Glue Lineage（将来）, OpenLineage | データの来歴可視化、SMC 採用時に強化 |
| **メタデータ更新** | Producer | Glue Crawler | スキーマ変更時の Catalog 自動同期 |
| **PII 検出・マスキング** | Producer の raw → curated 段階 | Macie（検出）+ Glue ETL（マスキング）| 個人情報を curated 層に持ち込まないための処理 |

##### 4.2.2.6 重要な設計原則

| # | 原則 | 説明 |
|---|---|---|
| 1 | **ELT を原則とする** | 生データはまず raw 層に着地、加工は下流（curated / analytics）で実施。例外は取り込み時点で PII マスキングが必須な場合のみ |
| 2 | **冪等性の徹底** | すべての ETL ジョブは冪等に設計、再実行で同じ結果を得られる |
| 3 | **テナント分離を ETL で強制** | raw → curated 変換時に `tenant_id` が確実に付与されるよう設計、欠落時はエラー |
| 4 | **個別アプリの集計は Producer で完結** | 「自分のデータの集計」はアプリ責任。Central は横断・SaaS 全体の集計のみ |
| 5 | **横断集計は SQL ファースト** | Central 側の派生データ生成は Athena CTAS が第一選択。Glue ETL は必要時のみ |
| 6 | **品質チェックを必須化** | Glue Data Quality でパイプライン後に検証、品質劣化時は自動停止 |

##### 4.2.2.7 残課題（ヒアリングで確認）

| # | 質問 | 影響 |
|---|---|---|
| 1 | 各アプリのデータエンジニアリングスキル | Producer 側 ETL の実装可否、研修必要性 |
| 2 | 既存の ETL 基盤（cron / Airflow / 自前バッチ）の取扱 | 移行戦略、並行運用期間 |
| 3 | リアルタイム性の要件（解約予兆検知の遅延許容）| ストリーム取り込みの採否 |
| 4 | 顧客企業マスタ・契約管理システムとの連携方式 | 共通参照データ層の ETL 設計（D-2 中央同居、[DP-ADR-003](adr/DP-ADR-003-common-domain-account-placement.md)）|

##### 4.2.2.8 案件側 ETL の詳細イメージ（**データプラットフォーム標準のスコープ外、参考情報**）

> ⚠ **位置付け**: 案件側（各アプリチーム）の ETL 実装は **本データプラットフォーム標準のスコープ外**。各アプリチームの責任で選定・実装する。本節は「**案件側がどのような構成になるか**」のイメージを掴むための参考資料であり、標準として強制するものではない。
>
> ただし、案件側が「データレイクに正しいフォーマットで raw データを着地させる」ためのインターフェース（S3 バケット命名・パーティション規約・暗号化要件等）は標準として定める（[../proposal/fr/03-pipeline.md](proposal/fr/03-pipeline.md)）。

###### 4.2.2.8.1 案件側 ETL の全体像（典型パターン）

```mermaid
flowchart TB
    subgraph Sources["データソース（業務システム）"]
        direction LR
        Aurora[("Aurora / RDS<br/>業務 OLTP")]
        Dynamo[("DynamoDB<br/>サービスメタ等")]
        AppLog["アプリログ<br/>(CloudWatch /<br/>ECS / Lambda)"]
        ExtSaaS["外部 SaaS<br/>(Salesforce 等)"]
        ExtCust["顧客社内システム<br/>(会計 / HR 等)"]
        SFTP["SFTP / Email 添付<br/>(顧客からの<br/>ファイル受領)"]
    end

    subgraph Step1["① 取込層 (Ingestion)"]
        direction LR
        DMS["AWS DMS<br/>(CDC / Bulk)"]
        ZeroETL["Aurora Zero-ETL<br/>(将来)"]
        KFH["Kinesis Data Firehose<br/>(ストリーム)"]
        DataPipe["AppFlow<br/>(SaaS 連携)"]
        Lambda1["Lambda<br/>(軽量 / API 取込)"]
        Transfer["Transfer Family<br/>(SFTP 受領)"]
    end

    subgraph App["案件側アカウント (Producer)"]
        direction TB
        S3Raw["S3 raw 層<br/>(原本保管、不変)"]

        subgraph Step2["② 変換層 (raw → curated)"]
            direction LR
            GlueETL1["Glue ETL Flex<br/>(Spark、PySpark)"]
            GlueDQ["Glue Data Quality<br/>(品質チェック)"]
            LambdaXform["Lambda<br/>(小規模変換)"]
        end

        S3Cur["S3 curated 層<br/>(Parquet、PII 除去、tenant_id 付与)"]

        subgraph Step3["③ 集計層 (curated → analytics)"]
            direction LR
            AthenaCTAS["Athena CTAS<br/>(SQL 集計)"]
            GlueETL2["Glue ETL Flex<br/>(複雑集計)"]
        end

        S3Ana["S3 analytics 層<br/>(集計済、パーティション最適化)"]

        subgraph Orchestration["④ オーケストレーション / 監視"]
            direction LR
            StepFn["Step Functions<br/>(ワークフロー)"]
            EvBridge["EventBridge<br/>Scheduler"]
            CWAlarm["CloudWatch Alarms<br/>(エラー検知)"]
            SNS["SNS / Chatbot<br/>(通知 → Slack/Teams)"]
        end

        subgraph CatalogProd["⑤ メタデータ管理"]
            Crawler["Glue Crawler<br/>(スキーマ自動検出)"]
            GlueCatProd["Glue Data Catalog<br/>(自アプリ分のテーブル定義)"]
        end
    end

    Aurora --> DMS
    Aurora -.将来.-> ZeroETL
    Dynamo --> Lambda1
    AppLog --> KFH
    ExtSaaS --> DataPipe
    ExtCust --> Lambda1
    SFTP --> Transfer

    DMS --> S3Raw
    ZeroETL --> S3Raw
    KFH --> S3Raw
    DataPipe --> S3Raw
    Lambda1 --> S3Raw
    Transfer --> S3Raw

    S3Raw --> GlueETL1
    S3Raw --> LambdaXform
    GlueETL1 --> S3Cur
    LambdaXform --> S3Cur
    GlueETL1 -.チェック.-> GlueDQ

    S3Cur --> AthenaCTAS
    S3Cur --> GlueETL2
    AthenaCTAS --> S3Ana
    GlueETL2 --> S3Ana

    StepFn -.制御.-> GlueETL1
    StepFn -.制御.-> GlueETL2
    StepFn -.制御.-> AthenaCTAS
    EvBridge -.起動.-> StepFn
    StepFn -.失敗.-> CWAlarm
    CWAlarm --> SNS

    Crawler -.スキャン.-> S3Raw
    Crawler -.スキャン.-> S3Cur
    Crawler -.スキャン.-> S3Ana
    Crawler -->|テーブル定義更新| GlueCatProd

    style Sources fill:#f5f5f5
    style App fill:#e8f5e9
    style Step1 fill:#fff3e0
    style Step2 fill:#fff3e0
    style Step3 fill:#fff3e0
    style Orchestration fill:#e3f2fd
    style CatalogProd fill:#ffebee
```

###### 4.2.2.8.2 5 つのコンポーネント詳細

| # | コンポーネント | 役割 | 代表選択肢 | 選定の考え方 |
|---|---|---|---|---|
| ① | **取込層 (Ingestion)** | 業務 DB / 外部システム → S3 raw への運搬 | **AWS DMS** (CDC/Bulk) / **Aurora Zero-ETL** / **Kinesis Data Firehose** / **AppFlow** / **Lambda** / **Transfer Family** | データソースの種類とリアルタイム性で選定（後述 4.2.2.8.3）|
| ② | **変換層 (raw → curated)** | クレンジング、PII マスキング、Parquet 化、tenant_id 強制 | **Glue ETL Flex** (Spark) / **Lambda** (軽量) / **Glue Data Quality** (品質) | データ量と複雑度で選定。標準は Glue ETL Flex |
| ③ | **集計層 (curated → analytics)** | パーティション化、集計、分析最適化 | **Athena CTAS** (SQL) / **Glue ETL Flex** (複雑) | SQL で済むなら Athena CTAS、Python ロジック必要なら Glue ETL |
| ④ | **オーケストレーション / 監視** | ジョブの起動・依存関係・リトライ・通知 | **Step Functions** (ワークフロー) / **EventBridge Scheduler** (起動) / **CloudWatch Alarms** (検知) / **SNS / Chatbot** (通知) | 標準は Step Functions + EventBridge |
| ⑤ | **メタデータ管理** | スキーマ自動検出、Catalog 登録 | **Glue Crawler** / **Glue Schema Registry** | 全 Producer 共通の標準 |

###### 4.2.2.8.3 取込層の選定マトリクス（① 詳細）

最も判断が割れるのが取込層。データソースとリアルタイム性で 6 パターンに分岐:

| データソース | リアルタイム性 | 推奨ツール | 理由 / 補足 |
|---|---|---|---|
| **Aurora MySQL / PostgreSQL** | バッチ（日次）| **DMS Full Load + Glue Job** | DMS で初回全件 → Glue で日次差分（タイムスタンプ列）|
| **Aurora MySQL / PostgreSQL** | ニアリアルタイム（分単位）| **DMS CDC** | バイナリログ / WAL から変更検知、S3 Sink |
| **Aurora MySQL（v3.06+）/ PostgreSQL** | ニアリアルタイム（秒単位）| **Aurora Zero-ETL to Redshift** | 将来選択肢（Phase 3+、Redshift 採用時のみ。[DP-ADR-002](adr/DP-ADR-002-redshift-emr-not-adopted.md)）|
| **DynamoDB** | ニアリアルタイム | **DynamoDB Streams + Kinesis Firehose** | Streams → Firehose → S3 raw、24 時間以内のデータのみ |
| **DynamoDB** | バッチ | **DynamoDB Export to S3** | テーブルスナップショット、無料（ただし PITR 課金）|
| **アプリログ（ECS / Lambda / EC2）** | ストリーム | **CloudWatch Logs → Kinesis Firehose → S3** | サブスクリプションフィルタで Firehose に流す |
| **外部 SaaS（Salesforce / HubSpot 等）** | 日次 | **AWS AppFlow** | OAuth 認証、200+ SaaS コネクタ標準 |
| **外部 SaaS（カスタム API）** | 日次 | **Lambda + EventBridge Scheduler** | AppFlow に対応がない場合の自作。`requests` で API 叩き S3 PUT |
| **顧客社内システム（DB 直接接続不可）** | 日次 | **Transfer Family (SFTP)** | 顧客が SFTP でファイル投函、S3 にランディング |
| **顧客社内システム（DB 直接接続不可）** | 日次 | **Email 受信 + SES + Lambda** | 顧客が CSV をメール添付、SES で受信 → Lambda で S3 配置 |
| **既存基盤（オンプレ Hadoop / Hive）** | バッチ | **DataSync** | NAS / HDFS / S3 互換ストレージ → S3 |

###### 4.2.2.8.4 変換層の典型実装（② 詳細）

**raw → curated の典型処理**（経費精算 SaaS の例）:

```python
# Glue ETL Flex Job (PySpark) の擬似コード例
# === Producer 側で実装、案件側のデータエンジニアが書く ===

import sys
from awsglue.transforms import *
from awsglue.context import GlueContext
from awsglue.dynamicframe import DynamicFrame
from pyspark.context import SparkContext
from pyspark.sql.functions import col, sha2, lit, when, current_timestamp

glueContext = GlueContext(SparkContext.getOrCreate())

# 1. raw 読込（DMS が出力した CDC 形式 JSON）
raw_df = glueContext.create_dynamic_frame.from_catalog(
    database="expense_app_raw",      # 自アプリの DB
    table_name="expenses_cdc"        # raw テーブル
).toDF()

# 2. tenant_id 強制付与（多くの場合 DB に既に列がある）
#    存在しなければエラー停止
if "tenant_id" not in raw_df.columns:
    raise ValueError("tenant_id is required for multi-tenant isolation")

# 3. PII マスキング（メールアドレスを SHA-256 ハッシュ化）
cleaned_df = raw_df \
    .withColumn("email_hash", sha2(col("submitter_email"), 256)) \
    .drop("submitter_email") \
    .withColumn("processed_at", current_timestamp())

# 4. データ品質: NULL チェック、型違反、金額の範囲チェック
quality_df = cleaned_df.filter(
    (col("tenant_id").isNotNull()) &
    (col("amount") > 0) &
    (col("amount") < 100000000)  # 1 億未満
)

# 5. Parquet で curated 層へ書込（パーティション = tenant_id + 日付）
quality_df.write \
    .mode("append") \
    .partitionBy("tenant_id", "submitted_date") \
    .parquet("s3://expense-app-curated/expenses/")
```

**変換層で典型的に行う処理**:

| 処理 | 必須 / 推奨 | 内容 |
|---|---|---|
| **`tenant_id` 強制付与** | **必須** | 多テナント分離の根幹。欠落時はジョブ失敗 |
| **PII マスキング** | **必須** | メール → SHA-256 / 個人名 → 仮名化 / 電話番号 → 末尾マスク |
| **Parquet 変換** | 推奨 | JSON / CSV → Parquet で Athena コスト 75% 削減 |
| **データ型統一** | 推奨 | 文字列の "true"/"True"/"1" → boolean に統一 |
| **パーティション設計** | **必須** | `tenant_id=XXX/year=YYYY/month=MM/day=DD/` 形式で Athena 最適化 |
| **重複排除** | 推奨 | CDC で同じレコードが複数回到着するため `row_number()` で最新のみ残す |
| **品質チェック** | 推奨 | Glue Data Quality でルール定義（NULL 率 5% 以下、外部キー整合性等）|

###### 4.2.2.8.5 集計層の典型実装（③ 詳細）

**curated → analytics は Athena CTAS が第一選択**:

```sql
-- Producer 側で Athena CTAS を実行、analytics 層に集計テーブル生成
-- 月次の経費精算サマリー（テナント別）

CREATE TABLE expense_app_analytics.monthly_summary
WITH (
    format = 'PARQUET',
    parquet_compression = 'SNAPPY',
    partitioned_by = ARRAY['tenant_id', 'year_month'],
    external_location = 's3://expense-app-analytics/monthly_summary/'
) AS
SELECT
    tenant_id,
    DATE_FORMAT(submitted_date, '%Y-%m') AS year_month,
    COUNT(*) AS submission_count,
    SUM(amount) AS total_amount,
    AVG(amount) AS avg_amount,
    COUNT(DISTINCT submitter_id) AS unique_submitters,
    SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) AS rejected_count
FROM expense_app_curated.expenses
WHERE submitted_date >= DATE '2026-01-01'
GROUP BY tenant_id, DATE_FORMAT(submitted_date, '%Y-%m');
```

**Athena CTAS vs Glue ETL の選び分け**:

| 観点 | Athena CTAS | Glue ETL |
|---|---|---|
| ロジック | SQL のみ | Python / Spark（任意ロジック）|
| 開発速度 | ⭕ 速い（SQL のみ）| △ Spark コード必要 |
| 実行コスト | スキャン量課金（$5/TB）| DPU 時間課金（Flex で $0.29）|
| 大量データ向き | ❌（30 分 / クエリ制限）| ⭕ |
| ML 前処理 / 複雑なロジック | ❌ | ⭕ |
| **推奨** | **集計が中心ならこれ** | 複雑な変換や ML 前処理に |

###### 4.2.2.8.6 オーケストレーションの典型実装（④ 詳細）

**Step Functions + EventBridge Scheduler の典型構成**:

```
EventBridge Scheduler (Cron: 毎日 02:00 JST)
    ↓ 起動
Step Functions ステートマシン
    ├── State 1: DMS タスク開始 (CDC リフレッシュ)
    │       ↓ 待機 (5 分)
    ├── State 2: Glue Crawler 実行 (raw のスキーマ更新)
    │       ↓ 完了待ち
    ├── State 3: Glue ETL Job (raw → curated)
    │       ↓ 完了待ち、失敗時リトライ 3 回
    ├── State 4: Glue Data Quality チェック
    │       ↓ 失敗時 → CloudWatch Alarm → SNS → Slack 通知
    ├── State 5: Athena CTAS (curated → analytics)
    │       ↓
    └── State 6: 完了通知 → SNS → Slack
```

**この構成のメリット**:
- ジョブ間の依存関係を State Machine で宣言的に管理
- 各 State のリトライ・タイムアウト・並列実行を細かく制御
- 視覚的にパイプラインの状態が分かる（Step Functions コンソール）
- IaC（CDK / Terraform）で全体を管理可能

###### 4.2.2.8.7 IaC / CI/CD の典型構成

**案件側の標準的な IaC / CI/CD 構成**:

| レイヤー | ツール | 内容 |
|---|---|---|
| **インフラ定義** | AWS CDK (TypeScript / Python) / Terraform / SAM | S3 / Glue / Lambda / Step Functions / DMS の宣言 |
| **ETL コード管理** | Git（GitHub / GitLab / CodeCommit）| Glue PySpark / Lambda コード / SQL クエリ |
| **CI** | GitHub Actions / CodeBuild | プルリク時に PyLint / Flake8 / SQL Lint / 単体テスト |
| **CD** | GitHub Actions / CodePipeline | dev → stg → prod のステージ別デプロイ、CDK Deploy 自動化 |
| **テスト** | pytest + LocalStack / Moto（モック）| Glue Job をローカルで実行（重い場合は dev 環境で実機テスト）|
| **シークレット** | Secrets Manager / Parameter Store | DB 接続情報、外部 SaaS API キー |

###### 4.2.2.8.8 案件側 ETL のコスト見積もり（経費精算 SaaS 中規模を想定）

**月次データ量の想定**: 1,000 顧客企業 × 平均 1,000 件 / 月 = **100 万件 / 月**、データサイズ約 **50 GB / 月**

| コンポーネント | 単価 | 月次利用量 | 月額 |
|---|---|---|---|
| **DMS（t3.medium インスタンス）** | $0.044/h | 24h × 30 = 720h | ~$32 |
| **DMS 通信料** | $0.09/GB（クロス AZ 不要なら $0）| 約 5 GB（差分のみ）| ~$0.5 |
| **S3 raw 保管**（GB × 月）| $0.023/GB | 50 GB × 3 ヶ月分（90 日 lifecycle）| ~$3.5 |
| **S3 curated / analytics**（Parquet 圧縮後）| $0.023/GB | 12.5 GB（75% 圧縮）| ~$0.3 |
| **Glue ETL Flex（raw → curated）** | $0.29/DPU 時間 | 2 DPU × 0.5 h × 30 日 = 30 DPU 時間 | ~$8.7 |
| **Athena CTAS（curated → analytics）** | $5/TB スキャン | 12.5 GB × 30 日 = 0.4 TB | ~$2 |
| **Glue Crawler** | $0.44/DPU 時間 | 0.5 DPU × 0.2 h × 30 日 = 3 DPU 時間 | ~$1.3 |
| **Step Functions** | $0.025/1,000 状態遷移 | 30 日 × ~50 遷移 = 1,500 遷移 | ~$0.04 |
| **EventBridge Scheduler** | 無料枠内（< 14M 起動）| 30 起動 / 月 | $0 |
| **CloudWatch Logs** | $0.50/GB 取込 | ~5 GB | ~$2.5 |
| **Lambda（軽量変換）** | $0.20/100 万リクエスト | 数千リクエスト | ~$0.1 |
| **合計** | | | **~$51 / 月** |

→ **中規模アプリ 1 つあたり月 ~$50 程度**。10 アプリで $500 / 月、20 アプリで $1,000 / 月。Glue / Athena / S3 の課金体系上、規模が増えても準線形に拡大する。

###### 4.2.2.8.9 案件側に必要な人材スキル

データプラットフォーム標準を活かすため、案件側に必要なスキル:

| スキル | レベル | 用途 |
|---|---|---|
| **SQL（標準クエリ + ウィンドウ関数）** | 中級 | Athena CTAS による集計、データ品質チェック |
| **Python（基礎 + Pandas / boto3）** | 中級 | Lambda、Glue ETL（PySpark）、外部 API 連携 |
| **PySpark（DynamicFrame / DataFrame）** | 初級〜中級 | Glue ETL の本体実装 |
| **AWS CDK / Terraform** | 初級〜中級 | インフラ IaC |
| **CloudWatch Logs / X-Ray** | 初級 | パイプライン障害調査 |
| **Parquet / 列指向ストレージの理解** | 初級 | パーティション設計、コスト最適化 |
| **CDC / イベントソーシング** | 初級 | DMS / DynamoDB Streams の運用 |
| **データモデリング（スター / 正規化）** | 中級 | curated / analytics 層の設計 |

→ **既存の Web アプリエンジニアから 2-3 名がデータエンジニアリングに転向**するイメージ。新規採用が難しい場合は、外部研修（AWS Data Engineering 学習パス、Udemy 等）で 3-6 ヶ月のオンボーディング想定。

###### 4.2.2.8.10 案件側 ETL の運用負荷の目安

**Phase 1 で 1 アプリあたり**:

| 工数項目 | 月次 |
|---|---|
| パイプライン障害対応 | 4-8 時間 |
| スキーマ変更追従（業務 DB に列追加等）| 2-4 時間 |
| データ品質ルール調整 | 1-2 時間 |
| コスト最適化（パーティション再設計等）| 月 0、四半期 8 時間 |
| **合計（定常運用）** | **8-15 時間 / 月** |

→ **案件側 0.1 人月（16 時間 / 月）程度**を初期想定。アプリチームの既存業務に組み込むことで、専任を新たに雇う必要は通常ない。ただし、新規パイプライン構築時は別途 2-4 週間の開発工数が必要。

###### 4.2.2.8.11 標準として案件側に守ってもらうこと（インターフェース契約）

データプラットフォーム標準のスコープ外ではあるが、**案件側 ETL の出力（S3 raw 着地データ）には標準が課す要件がある**:

| カテゴリ | 案件側に求める標準 | 詳細参照 |
|---|---|---|
| **S3 バケット命名規約** | `<prefix>-<app>-<layer>-<env>` 等の命名統一 | [proposal/fr/02-storage.md](proposal/fr/02-storage.md) §FR-2.1 |
| **パーティション規約** | `tenant_id=XXX/year=YYYY/month=MM/day=DD/` 形式 | [proposal/fr/02-storage.md](proposal/fr/02-storage.md) §FR-2.3 |
| **暗号化** | SSE-KMS 必須、中央 CMK 利用 | [proposal/fr/02-storage.md](proposal/fr/02-storage.md) §FR-2.4 |
| **Glue Catalog 登録** | curated / analytics 層は Glue Catalog 登録必須（Federation 元）| [proposal/fr/02-storage.md](proposal/fr/02-storage.md) §FR-2.5 |
| **データ品質メトリクス** | Glue Data Quality 結果を中央集約用 S3 に出力 | [proposal/fr/03-pipeline.md](proposal/fr/03-pipeline.md) §FR-3.4 |
| **`tenant_id` 必須付与** | curated 層以降、全テーブルに `tenant_id` 列が存在すること | [proposal/fr/05-governance.md](proposal/fr/05-governance.md) §FR-5.2 |
| **CloudTrail Data Events 有効化** | S3 raw / curated / analytics の全バケット | [proposal/fr/05-governance.md](proposal/fr/05-governance.md) §FR-5.4 |

→ 案件側は「**インターフェース契約を守れば、ETL の中身は自由に実装してよい**」というのが標準のスタンス（[../proposal/fr/03-pipeline.md §FR-3.0.A](proposal/fr/03-pipeline.md) 参照）。

#### 4.2.3 Glue Crawler の位置付けと運用

##### 4.2.3.1 Glue Crawler の役割

| 機能 | 内容 |
|---|---|
| **スキーマ自動検出** | S3 上のデータ（CSV / JSON / Parquet / ORC 等）からスキーマを推論 |
| **Glue Data Catalog 更新** | 検出したスキーマでテーブル定義を作成・更新 |
| **パーティション検出** | `s3://.../year=YYYY/month=MM/day=DD/` のような Hive 形式のパーティション認識 |
| **データフォーマット検出** | ファイル形式（Parquet vs JSON 等）の自動判定 |
| **スキーマ進化追跡** | 既存テーブルへの列追加・型変更を検出（ポリシーで挙動制御）|

##### 4.2.3.2 配置（Producer 側、各アプリアカウント内）

```mermaid
flowchart LR
    subgraph App["各アプリアカウント (Producer)"]
        Crawler["Glue Crawler"]
        S3R["S3 raw 層"]
        S3C["S3 curated 層"]
        S3A["S3 analytics 層"]
        GlueProd["Glue Data Catalog<br/>(ローカル)"]
    end

    subgraph Central["中央 BI / Catalog (Option B)"]
        LF["Lake Formation"]
        GlueCat["Glue Data Catalog<br/>(中央)"]
        LFTags["LF-Tags"]
    end

    Crawler -->|スキャン| S3R
    Crawler -->|スキャン| S3C
    Crawler -->|スキャン| S3A
    Crawler -->|テーブル定義更新| GlueProd
    GlueProd -.federate.-> GlueCat
    LF -.タグ付与.-> GlueCat
    LFTags -.参照.-> LF

    style App fill:#e8f5e9
    style Central fill:#e3f2fd
```

**配置の原則**: Crawler は **データに最も近い場所**（Producer 側）で動かす。ローカル Glue Data Catalog を更新し、その結果が **Cross-account Glue Catalog Federation** で中央 Lake Formation に反映される。

##### 4.2.3.3 各層での Crawler の必要性

| 層 | Crawler の必要性 | 理由 |
|---|:---:|---|
| **S3 raw 層** | ⭐⭐⭐ 高 | 取り込み元（顧客の会計システム等）からのデータ形式・スキーマが未知の可能性、外部 SaaS のスキーマ変更追従に必要 |
| **S3 curated 層** | ⭐⭐ 中 | ETL ジョブが明示的にスキーマ定義することが多いが、念のため Crawler で検証 |
| **S3 analytics 層** | ⭐ 低 | Athena CTAS / Glue ETL（Spark）が**自動的に Glue Catalog に登録**するため Crawler 不要 |

##### 4.2.3.4 実行タイミング

| トリガ | 使い分け |
|---|---|
| **スケジュール**（毎日 / 毎時）| 定期的なデータ取り込み・raw 層のスキーマドリフト検出に最適 |
| **EventBridge**（S3 ObjectCreated）| 不定期な大量データ取り込み時、リアルタイム性が必要な場合 |
| **ETL パイプライン終了時**（Step Functions から呼出）| 推奨。ETL → Crawler → 通知 の一連のフローで運用 |
| **手動実行** | 新規データソース追加時の検証 |

##### 4.2.3.5 Lake Formation との連携フロー

```mermaid
sequenceDiagram
    autonumber
    participant ETL as ETL ジョブ<br/>(Glue / Step Functions)
    participant S3 as S3 (App アカウント)
    participant Crawler as Glue Crawler
    participant GlueProd as Glue Catalog<br/>(App ローカル)
    participant LFCentral as Lake Formation<br/>(中央 BI/Catalog)
    participant Admin as DataLakeAdminRole

    ETL->>S3: データ書込み（raw → curated → analytics）
    Crawler->>S3: スキャン
    Crawler->>GlueProd: テーブル定義更新
    GlueProd-->>LFCentral: Catalog Federation で参照可能に
    LFCentral->>Admin: スキーマ変更通知
    Admin->>LFCentral: LF-Tags 付与・確認<br/>(機密度 / ドメイン / PII)
    LFCentral->>LFCentral: 既存の Grant が新カラムに自動継承<br/>(LF-Tag ベース)
```

**重要**: スキーマ変更時、**新カラムへの LF-Tags は自動継承されない**ケースがある（タグ設計次第）。DataLakeAdminRole の運用プロセスとして「Crawler 実行後の LF-Tags レビュー」を組み込む必要。

##### 4.2.3.6 ベストプラクティス（使う / 使わないの判断）

| 状況 | 推奨アプローチ | 理由 |
|---|---|---|
| **未知形式の raw データ取り込み**（外部システム連携）| ✅ Crawler 必須 | スキーマが事前に分からない |
| **ETL ジョブが明示的にスキーマ定義** | △ Crawler 不要 | ETL ジョブのスキーマが信頼できる |
| **Athena CTAS で派生テーブル生成** | ❌ Crawler 不要 | Athena が自動カタログ登録 |
| **大規模バケット**（数 TB 超 / 数百万ファイル）| ⚠ Crawler のスキャンコスト注意 | パーティションを限定したクロールを推奨 |
| **ストリーミングデータ**（Kinesis Firehose）| △ Glue Schema Registry を使用 | Crawler よりも Schema Registry のほうが適切 |
| **IaC 管理されたスキーマ** | ❌ Crawler 不要 | CDK / CloudFormation でスキーマを定義済み |

##### 4.2.3.7 代替手段（Crawler を使わない選択肢）

| 代替手段 | 用途 | 利点 |
|---|---|---|
| **AWS Glue Schema Registry** | ストリーミングデータ（Kinesis / MSK）のスキーマ管理 | スキーマ進化のバージョン管理、後方互換性チェック |
| **IaC（CDK / CloudFormation）でスキーマ定義** | 既知の安定したスキーマ | バージョン管理、レビュー可能、再現性 |
| **Lake Formation Resource Link** | クロスアカウント Catalog 参照 | Crawler 不要で他アカウントの Catalog を共有 |
| **ETL ジョブ内でのスキーマ宣言** | Spark / Pandas で明示定義 | 型変換・バリデーションを ETL と同時実行 |
| **Glue DataBrew** | データプロファイリング + スキーマ検出 | より高度な分析・品質チェック付き |

##### 4.2.3.8 コスト感

| 項目 | 単価 | 影響 |
|---|---|---|
| **クロール実行時間** | 1 DPU-hour あたり $0.44 | データ量・パーティション数次第で月数十 USD オーダー |
| **データスキャン** | 別途 S3 GET リクエスト課金 | 大規模バケットでは無視できない |
| **Glue Data Catalog ストレージ** | 月 100 万オブジェクトまで無料、超過後課金 | 数千テーブル程度なら無料枠内 |

**最適化のコツ**:
- **パーティション限定**: `s3://.../year=2026/month=06/` のように最新パーティションのみクロール
- **除外パターン**: `.tmp` ファイル等の不要ファイルを除外
- **更新検出モード**: 「Crawl new sub-folders only」で全スキャンを回避

##### 4.2.3.9 残課題（ヒアリングで確認）

| # | 質問 | 影響 |
|---|---|---|
| 1 | 各アプリのデータ取り込み形式の安定性 | Crawler を使うか IaC でスキーマ定義するか |
| 2 | スキーマ進化（既存カラムの型変更等）への対応ポリシー | Crawler の `SchemaChangePolicy` 設定 |
| 3 | Crawler 実行頻度の妥当性 | コスト・鮮度のバランス |
| 4 | LF-Tags 再付与プロセスの自動化要否 | スキーマ変更時の Catalog 管理者運用 |

#### 4.2.4 AWS RAM の役割と使用箇所

##### 4.2.4.1 AWS RAM とは

**AWS Resource Access Manager**: AWS リソースをアカウント間で共有するためのサービス。

| 機能 | 内容 |
|---|---|
| **リソース共有の宣言** | 「このリソースをこの相手に共有する」を Resource Share として作成 |
| **共有相手の指定** | (a) 個別 AWS アカウント ID / (b) Organization 内の OU / (c) Organization 全体 |
| **権限の付与** | Resource Share 内で何ができるか（読み専用 / 書き可 / etc.）を managed permission で指定 |
| **Auto-accept** | Organization 内なら **自動受諾** 可能（個別承認不要）|

##### 4.2.4.2 質問への回答: 子アカウント同士で共有できるか

**結論: YES、できる。Management アカウント経由は不要。**

```mermaid
flowchart TB
    Mgmt["Management アカウント<br/>(Organization Root)"]

    subgraph Children["子アカウント (Organizations Member)"]
        direction LR
        Audit["監査アカウント"]
        BICat["中央 BI / Catalog"]
        App1["App 1"]
        App2["App 2"]
        Common["共通ドメイン"]
    end

    Mgmt -.管理.-> Children

    BICat -.RAM 共有可.-> App1
    App1 -.RAM 共有可.-> BICat
    Audit -.RAM 共有可（技術的には）.-> App1
    App1 -.RAM 共有可.-> Common
    Common -.RAM 共有可.-> BICat

    style Mgmt fill:#f5f5f5
    style Children fill:#e8f5e9
```

**仕組み**:
1. 共有元アカウントが Resource Share を作成
2. Resource Share に「このリソースをこの相手に共有」と宣言
3. Organization 設定で **「AWS Organizations での共有を有効化」** をオンにしておくと、Org 内の共有は受信側で自動受諾される
4. 受信側は IAM 権限を別途付与すれば共有リソースを利用可能

**制約**:
- 共有元は **そのリソースの所有者** でなければならない（自分が持っていないリソースは共有できない）
- 受信側で利用するには **IAM 権限** が別途必要（RAM は「アクセスを許可する」だけ、IAM が「使うことを許可する」）
- リソース種別ごとに共有可否が決まっている（[RAM 対応リソース一覧](https://docs.aws.amazon.com/ram/latest/userguide/shareable.html)）

##### 4.2.4.3 本構成での RAM 使用箇所一覧

| 共有元 | 共有先 | リソース | 用途 | 仕組み |
|---|---|---|---|---|
| **中央 BI / Catalog** | App アカウント（Producer）| Lake Formation 権限 | Producer が自分のデータを Lake Formation に登録できるようにする | **Lake Formation Cross-Account v3 が RAM を透過利用** |
| **App アカウント**（Producer）| 中央 BI / Catalog | Glue Data Catalog テーブル | Producer の Catalog を中央 LF が参照（Federation）| Lake Formation 経由 |
| **共通ドメインアカウント** | 中央 BI / Catalog | Glue Data Catalog テーブル | 共通参照データ（顧客マスタ等）を中央から参照 | 同上 |
| **共通ドメインアカウント** | App アカウント | Glue Data Catalog テーブル | 各アプリが共通マスタを参照（例: 経費精算が顧客マスタを Join）| 同上 |
| **将来 γ パターン採用時**: 中央 BI / Catalog | 各 Consumer アカウント | Lake Formation 権限 | 各アプリ内 Consumer がデータをクエリできる | Lake Formation Cross-Account |
| **オプション**: 中央 BI / Catalog | App アカウント | KMS CMK | 暗号化鍵を App 側からも使えるように | **KMS 鍵ポリシー**（RAM ではなく Key Policy で制御）|
| **監査アカウント** | データ標準アカウント | （基本なし）| 詳細は §4.2.4.5 参照 | — |

##### 4.2.4.4 Lake Formation での RAM 透過利用

**重要**: Lake Formation **Cross-Account Permissions v3**（現行）は、RAM を **自動的に裏で作成・管理** する。利用者が明示的に RAM Resource Share を作る必要はない。

```mermaid
sequenceDiagram
    autonumber
    actor Admin as DataLakeAdminRole
    participant LF as Lake Formation<br/>(中央 BI / Catalog)
    participant RAM as AWS RAM
    participant App as App アカウント

    Admin->>LF: Grant SELECT ON sales TO App アカウント
    LF->>RAM: Resource Share 自動作成<br/>(指定なし、透過的)
    RAM->>App: 共有を自動受諾<br/>(Org 設定で auto-accept 有効)
    Note over App: アプリ側でデータ閲覧可能に
```

→ **DataLakeAdminRole は LF Grant のみ意識すればよい**。RAM の存在は知っていれば十分。

##### 4.2.4.5 監査アカウント → 案件アカウントの共有

**技術的可否**: 可能（Organizations 内の子アカウント間共有）

**ただし、本構成では基本的に不要**:
- 監査アカウントは通常 **ログを受け取る側**（受信専用）
- 監査アカウントから案件アカウントへの「リソース共有」は限定的なシナリオでのみ発生

**監査アカウント → 案件アカウントの共有が発生しうる典型シナリオ**:

| シナリオ | 内容 | 仕組み |
|---|---|---|
| **セキュリティ標準の AMI 配布** | 監査チームが標準化された AMI を全アカウントに共有 | RAM（AMI を Resource Share）|
| **共通 KMS 鍵の利用許可** | 監査チームが管理する暗号鍵を案件アカウントが使用 | KMS 鍵ポリシー（RAM ではない）|
| **Security Hub Insights / Custom Actions の共有** | カスタムフィルタを案件アカウントに展開 | Security Hub の Delegated Admin 機能 |
| **Config Conformance Pack のデプロイ** | コンプラチェックルールを案件側にデプロイ | Config の Multi-Account 機能 |
| **Network Firewall の共通ルール** | NW ファイアウォール設定を案件側に共有 | RAM（NW Firewall Rule Group を Resource Share）|

**監査アカウントが管理側のサービス使用例**:
- Security Hub Delegated Administrator
- GuardDuty Delegated Administrator
- Macie Delegated Administrator
- Config Aggregator

→ これらは **RAM ではなく各サービスの Delegated Admin / Aggregator 機能** で実現。RAM の直接利用は限定的。

##### 4.2.4.6 RAM 設定の流れ（例: Lake Formation 共有を手動で確認する場合）

```bash
# 1. Lake Formation Grant 実行
aws lakeformation grant-permissions \
    --principal DataLakePrincipalIdentifier=arn:aws:iam::APP_ACCOUNT_ID:root \
    --permissions SELECT \
    --resource Table='{DatabaseName=sales,Name=transactions}'

# 2. Lake Formation が裏で RAM Resource Share を作成
# 3. RAM 側で確認
aws ram list-resources \
    --resource-owner SELF

# 4. App アカウント側で受諾状態確認（auto-accept なら不要）
aws ram get-resource-share-invitations
```

##### 4.2.4.7 注意点と落とし穴

| # | 注意点 | 影響 |
|---|---|---|
| 1 | **Organization 設定の「RAM 共有有効化」が必須** | OFF の場合、子アカウント間共有が auto-accept にならず手動承認が必要 |
| 2 | **共有先での IAM 権限付与が別途必要** | RAM が「リソースを見える」ようにするだけ、利用には IAM 権限が必要 |
| 3 | **共有可能なリソースは限られる** | S3 バケットは RAM では共有できない（バケットポリシーで対応）|
| 4 | **Resource Share の上限**: アカウントあたり 5000 個まで | 大規模環境で要監視 |
| 5 | **Resource Link との違い**: Glue Catalog のクロスアカウント参照には **Resource Link** が必要（RAM 共有とは別）| Lake Formation 経由で自動生成される |
| 6 | **削除順序**: 共有元で削除 → 共有先で自動的に見えなくなる | データへの影響なし、メタデータのみ |
| 7 | **Auto-accept が効くのは Org 内のみ** | 別 Org への共有は手動受諾必要（本構成では発生しない）|

##### 4.2.4.8 残課題（ヒアリングで確認）

| # | 質問 | 影響 |
|---|---|---|
| 1 | Organizations の「**RAM 共有有効化**」設定状況 | 子アカウント間 auto-accept の可否 |
| 2 | 監査アカウントから案件アカウントへ配布したいリソースの有無 | RAM 使用範囲の確定 |
| 3 | KMS CMK のアカウント間利用の権限設計 | 鍵ポリシー設計（RAM ではなく Key Policy）|
| 4 | Resource Share の管理ガバナンス（誰が作成・削除できるか）| `DataLakeAdminRole` の権限範囲 |



各アプリは自分の分野の分析を自前で実施（Producer + Consumer）+ 中央 BI / 経営層向け横断分析は専用 Consumer。**Option B により Catalog を中央 BI Consumer に同居**。

```mermaid
flowchart TB
    subgraph A1["App 1 acct = Producer + Consumer"]
        S1["S3"]
        Q1["Athena<br/>(自部門の分析)"]
    end

    subgraph A2["App 2 acct = Producer + Consumer"]
        S2["S3"]
        Q2["Athena<br/>(自部門の分析)"]
    end

    subgraph BICat["🆕 中央 BI / Catalog 同居 acct（新規 +1、Option B）"]
        Cat["Lake Formation Catalog<br/>+ LF-Tags + KMS<br/>(DataLakeAdminRole)"]
        QS["QuickSight + Athena<br/>(横断 BI / 経営層向け)<br/>(DataAnalystRole)"]
    end

    BICat -.権限管理 + Catalog.-> A1
    BICat -.同左.-> A2
    Q1 -->|自分の S3| S1
    Q2 -->|自分の S3| S2
    BICat -.横断クエリ.-> S1
    BICat -.横断クエリ.-> S2

    style A1 fill:#e8f5e9
    style A2 fill:#e8f5e9
    style BICat fill:#fff3e0
```

**特徴**:
- **追加アカウント = 中央 BI / Catalog 同居の 1 つだけ**（**+1**、Option B 効果）
- 共通ドメインを別アカウントとする場合は **+2 合計**
- 各アプリは自前で自分の分析、中央 BI チームは横断分析
- **中規模以上の組織で最も一般的**
- 同居の責務分離は IAM Role で実装（[§5.5 緩和策](#55-option-b-が成立する条件と緩和策) 参照）

### 4.4 推奨マトリクス（Option B 適用後 + 共通ドメイン込み）

> 数値は **Option B（Catalog 同居 Consumer）適用後 + 共通ドメインアカウント (+1) 込み**の合計追加アカウント数。

| 組織条件 | 推奨パターン | 追加アカウント数 |
|---|:---:|:---:|
| 小規模、専属 BI / データ分析チームなし | **α** | **+2**（独立 Catalog +1、共通ドメイン +1。Option B 不適用）|
| 中央 BI / 経営 KPI ダッシュボードが重要、専属 BI チームあり、組織体制未整備で開始 | **β** ⭐（**仮案選定 = Phase 1**）| **+2**（中央 BI/Catalog 同居 +1、共通ドメイン +1）|
| 中央 BI 体制が整い、各アプリチームの自前分析も可能 | **γ**（業界標準推奨、仮案 Phase 2 移行先）| **+2**（中央 BI/Catalog 同居 +1、共通ドメイン +1）|
| 大規模、複数の分析チーム / ML チームが並行で動く | γ 拡張 | **+3 以上**（Catalog 単独 Option C、複数 Consumer）|
| アプリ側に分析機能を持たせたくない（権限統制重視）| **β** | **+2** |

> **仮案選定の根拠**: アプリチームに分析スキルなし（Q1）+ 専属 BI チームなし（Q4）→ Phase 1 では γ ではなく β、組織が整ったら Phase 2 で γ へ移行（Path C 段階移行、[strawman §4](strawman-proposal.md) 参照）。

---

## 5. Catalog vs Governance — 用語整理と配置 3 オプション

### 5.1 「Catalog Account」と「Governance Account」の用語

AWS 公式ドキュメント内で**両方の用語が使われており、スコープが違う**ものに付けられている:

| AWS ドキュメント | 使用用語 | スコープ |
|---|---|---|
| [Prescriptive Guidance: Data Mesh](https://docs.aws.amazon.com/prescriptive-guidance/latest/strategy-data-mesh/aws-offerings-data-mesh.html) | 「Central Account」「Governance Account」 | 広め（Catalog + permission + 監査）|
| [Lake Formation Cross-Account 公式](https://docs.aws.amazon.com/lake-formation/latest/dg/cross-account-permissions.html) | **「Central Catalog Account」** | 狭い（Catalog + permission のみ）|
| [DataZone Multi-Account](https://docs.aws.amazon.com/datazone/latest/userguide/working-with-accounts.html) | 「Domain Account」 | Catalog + Domain |
| [Secure Data Mesh Solutions](https://aws.amazon.com/solutions/guidance/secure-data-mesh-with-distributed-data-asset-ownership-on-aws) | 「Central Governance Account」 | 広め |
| [AWS Landing Zone Accelerator](https://aws.amazon.com/solutions/implementations/landing-zone-accelerator-on-aws/) | 「Audit Account」「Log Archive Account」 | 監査は別建て |

**用語の本質**: 「Governance Account」は複数責務を束ねた**包括用語**で、実装上は分解されることが多い。

```mermaid
flowchart LR
    Broad["Governance Account<br/>(広義の概念)"]
    Broad -->|分解| Cat["Catalog Account<br/>Lake Formation /<br/>LF-Tags / SMC (Phase 2 候補)"]
    Broad -->|分解| Sec["Security Account<br/>Macie / Security Hub /<br/>GuardDuty"]
    Broad -->|分解| Audit["Audit Account<br/>CloudTrail / Config 集約"]
    Broad -->|分解| Crypto["Crypto Account<br/>KMS CMK"]

    style Broad fill:#fff3e0
    style Cat fill:#e8f5e9
    style Sec fill:#fce4ec
    style Audit fill:#fff8e1
    style Crypto fill:#e0f7fa
```

### 5.2 既存アカウント体系を活かす責務再配置

ユーザー環境では**親会社統制アカウントが Audit / Security 集約を担う**ことを前提に、責務を再配置できる:

| 責務 | 元の置き場（§2 仮案）| 親会社統制を活かす場合 |
|---|---|---|
| CloudTrail Org Trail | Governance | **親会社統制（既存）** |
| Security Hub 集約 | Governance | **親会社統制（既存）** |
| GuardDuty 集約 | Governance | **親会社統制（既存）** |
| Macie 集約 | Governance | **親会社統制（要確認）** |
| Lake Formation Catalog | Governance | **Catalog Account（新規）** |
| LF-Tags | Governance | 同上 |
| DataZone / SageMaker Catalog（オプション）| Governance | 同上（**Phase 1 では不採用、[DP-ADR-001](adr/DP-ADR-001-sagemaker-catalog-adoption-deferred.md) で Phase 2 再評価**）|
| KMS CMK（データ専用）| Governance | Catalog Account or 既存 Crypto |
| 共通参照データ | 共通ドメイン | 共通ドメイン（変わらず）|

→ **「Governance Account」と呼ぶ必要が薄れ、実質「Catalog Account」だけで足りる可能性**。

> ⚠ **要ヒアリング確認（Q1）**: 親会社統制が Macie / Security Hub / GuardDuty / Config Aggregator の集約を実際に担当しているか。担当範囲次第で Catalog Account のスコープが変わる。

### 5.3 配置 3 オプションの比較

```mermaid
flowchart TB
    subgraph Common["全パターン共通"]
        P["親会社統制 (既存)<br/>+ Trail / Audit / Security"]
        A["共通基盤 (既存)<br/>+ 認証"]
        Apps["各アプリ N 個 (既存)<br/>= Producer"]
        CD["🆕 共通ドメイン (+1)<br/>顧客マスタ等"]
    end

    subgraph Opt1["Option A: 広義 Governance (+3)"]
        Gov1["🆕 Governance Account<br/>Catalog + LF-Tags +<br/>SMC (Phase 2 候補) + KMS + 重複監査"]
        BI1["🆕 中央 BI<br/>= Consumer"]
    end

    subgraph Opt2["Option B: Catalog 同居 Consumer (+2) ⭐"]
        BICat["🆕 中央 BI / Catalog<br/>= Consumer + Catalog<br/>+ LF-Tags + (SMC Phase 2 候補) + KMS"]
    end

    subgraph Opt3["Option C: Catalog 単独 (+3)"]
        Cat3["🆕 Catalog Account<br/>(軽量・専用)<br/>LF + LF-Tags + (SMC Phase 2 候補) + KMS"]
        BI3["🆕 中央 BI<br/>= Consumer"]
    end

    style Common fill:#f5f5f5
    style Opt1 fill:#fff8e1
    style Opt2 fill:#e8f5e9
    style Opt3 fill:#e3f2fd
```

### 5.4 3 オプションの観点別比較

| 観点 | A 広義 Governance (+3) | **B Catalog 同居 (+2)** ⭐ | C Catalog 単独 (+3) |
|---|:---:|:---:|:---:|
| 追加アカウント数 | +3 | **+2** | +3 |
| 責務分離（Catalog vs Consumer）| ◎ アカウント分離 | △ IAM Role 分離 | ◎ アカウント分離 |
| 責務分離（監査 vs 利用）| ◎（親会社統制 + Governance）| ◎（親会社統制で代替）| ◎ |
| Catalog 管理者特権の影響範囲 | 限定 | Consumer に集中 | 限定 |
| 運用負荷 | △ アカウント多い | ◎ 最少 | △ アカウント多い |
| 将来の分離容易性 | 既に分離済み | △ 移行コスト発生 | 既に分離済み |
| AWS 公式パターン整合 | ◎ Prescriptive Guidance 準拠 | ○ Lake Formation Central Catalog Account パターンとして整合 | ◎ |
| 規模拡大時の柔軟性 | ◎ | △ Consumer 増加で破綻 | ◎ |
| 業界実例の多さ | 大企業・規制業界 | **小〜中規模で多い** | 中規模 |

### 5.5 Option B が成立する条件と緩和策

**成立条件**:
- 親会社統制が Audit / Security 集約を担当している（§5.2 の責務再配置が成立）
- BI チーム規模が小〜中（〜5 名程度）
- Consumer アカウントが当面 1 つ

**緩和策**（Option B 採用時に必須）:

| # | 緩和策 | 効果 |
|---|---|---|
| 1 | **IAM Role の厳密な分離** — `DataLakeAdminRole`（Lake Formation 管理特権）と `DataAnalystRole`（クエリ・閲覧のみ）を完全に別ユーザー集合に割当 | Catalog 管理 ≠ 利用、Role 境界での責務分離 |
| 2 | **Permission Boundary** で `DataAnalystRole` から Lake Formation 管理操作を拒否 | 自己権限上昇の防止 |
| 3 | **SCP** で Consumer アカウントの権限上昇系操作を拒否 | 予防的制御 |
| 4 | **CloudTrail を親会社統制へ強制転送** | 自己監査リスク回避（前提として既に整備）|
| 5 | **AWS Config Rules** で「Catalog 管理権限と Consumer 権限の重複ユーザー」を検出 | 検知的制御 |
| 6 | **将来 Catalog 分離の手順書** を初日から準備 | 規模拡大時の移行リスク抑制 |

### 5.6 推奨

```mermaid
flowchart TB
    Q1{現状の規模 / 想定規模}

    Q1 -->|小〜中規模| OptB["⭐ Option B<br/>Catalog 同居 Consumer (+2)"]
    Q1 -->|中規模以上| OptC["Option C<br/>Catalog 単独 (+3)"]
    Q1 -->|大規模 or 規制業界| OptA["Option A<br/>広義 Governance (+3)"]

    OptB --> Future1{将来規模拡大?}
    Future1 -->|Yes、Phase 2 で分離検討| Migration["B → C への分離パスを Phase 計画に組込"]
    Future1 -->|No| Final["B 維持"]

    style OptB fill:#e8f5e9
```

**仮案の選定**: **Option B**（Catalog 同居 Consumer、**+2**）。将来規模拡大時に Option C へ分離可能な設計（§5.5 緩和策の #6）にしておく。

### 5.7 Pattern α/β/γ × Option A/B/C の組み合わせマトリクス

§4 の 3 パターン（Consumer 配置）と §5 の 3 オプション（Catalog 配置）は独立軸で、組み合わせ可能。**仮案は β + B + 共通ドメイン**。

| | Option A 広義 Governance（+ 別 Catalog） | **Option B Catalog 同居 Consumer** ⭐ | Option C Catalog 単独 |
|---|:---:|:---:|:---:|
| **Pattern α** 各アプリ Consumer 兼任 | +1（Governance）+ N アプリ内 Consumer | ⚠ 「Catalog 同居先」が無く成立しない<br/>※α なら Option A or C 必須 | +1（Catalog）+ N アプリ内 Consumer |
| **Pattern β** 1 中央 Consumer | +2（Governance + Consumer）| **+1（Consumer 兼 Catalog）** ⭐<br/>本仮案 = β + B + 共通ドメイン = **+2 合計** | +2（Catalog + Consumer）|
| **Pattern γ** ハイブリッド（アプリ + 中央 Consumer）| +2（Governance + 中央 Consumer）| +1（中央 Consumer 兼 Catalog） | +2（Catalog + 中央 Consumer）|

**重要な制約**: **α は Option B と組み合わせ不可**（中央 Consumer がないため Catalog の同居先が存在しない）。各アプリアカウントに分散して Catalog を持たせると Catalog の中央性が失われる。

**仮案の組み合わせ**: β + Option B + 共通ドメイン = **+2 アカウント**（中央 BI / Catalog + 共通ドメイン）

```mermaid
flowchart LR
    P["仮案"]
    P --> Pat["Pattern β<br/>(1 中央 Consumer)"]
    P --> Opt["Option B<br/>(Catalog 同居 Consumer)"]
    P --> Com["+ 共通ドメイン<br/>(別アカウント)"]

    Pat --> Result["合計 +2 アカウント<br/>中央 BI / Catalog +<br/>共通ドメイン"]
    Opt --> Result
    Com --> Result

    style Result fill:#e8f5e9
```

---

## 5.8 監査責務分離の具体設計（Option B 採用時 + 新規監査アカウント前提）

### 5.8.1 前提

**監査アカウントはデータプラットフォーム標準のスコープ外**で生成される。Transit Gateway / 共通 VPC エンドポイント / 共通 DNS 等の**共通インフラと同じ位置付け**で、「**他組織が運用するものを我々が利用させていただく**」という関係。

```mermaid
flowchart TB
    subgraph OutOfScope["スコープ外（他組織が運用）"]
        direction LR
        Parent["親会社統制アカウント<br/>SoC / NW Firewall"]
        AuditAcc["🔵 監査アカウント<br/>(別組織が生成・運用)<br/>・CloudTrail Org Trail<br/>・Security Hub / GuardDuty / Macie<br/>・Config Aggregator<br/>・監査ログ長期保管"]
        TGW["Transit Gateway<br/>共通 VPC エンドポイント等"]
    end

    subgraph InScope["データプラットフォーム標準のスコープ"]
        direction LR
        BICat["中央 BI / Catalog<br/>(Option B)"]
        Common["共通ドメイン"]
        Apps["各アプリ × N<br/>(Producer)"]
    end

    InScope -.ログ・監査イベント送付.-> AuditAcc
    InScope -.ネットワーク通信.-> TGW

    style OutOfScope fill:#f5f5f5
    style InScope fill:#e3f2fd
    style AuditAcc fill:#fce4ec
```

**本標準の役割**: 監査アカウントに対して **「何を送るか / 何を期待するか / 何を依存するか」** を定義する側に立つ。

### 5.8.2 アカウント体系（スコープ込み）

| カテゴリ | アカウント | 運用主体 | データプラットフォーム標準での位置付け |
|---|---|---|---|
| **スコープ外（既存・他組織）** | 親会社統制 | 親会社 SoC | データ標準には直接関与しない |
| **スコープ外（新規・他組織）** | **🔵 監査アカウント** | **別組織** | **ログ送付先・依存対象**として利用 |
| **スコープ外（既存・他組織）** | Transit Gateway / 共通ネットワーク | ネットワーク統括 | データ通信の経路として利用 |
| **スコープ内（既存）** | 共通基盤（認証）| 別チーム | 認証連携先として利用 |
| **スコープ内（既存）** | 各アプリ × N | アプリチーム | Producer 兼任、ガイド対象 |
| **スコープ内（新規 +1）** | 🆕 中央 BI / Catalog（Option B 同居）| データプラットフォームチーム | 本標準が設計・運用 |
| **スコープ内（新規 +1）** | 🆕 共通ドメイン | データプラットフォームチーム + 各データ責任者 | 本標準が設計・運用 |

### 5.8.3 監査アカウントへのログ送付経路

データプラットフォーム側から監査アカウントへ送付するログを **送信元 × 種別 × 仕組み** で整理。

| 送信元 | 種別 | 内容 | 送付の仕組み |
|---|---|---|---|
| **全アカウント** | コントロールプレーン監査 | CloudTrail Management Events | **Organization Trail**（監査アカウント側で設定済み前提）|
| 中央 BI / Catalog | データプレーン監査 | Lake Formation データアクセスイベント、KMS 鍵使用イベント | **CloudTrail Data Events**（Organization Trail に統合）|
| 中央 BI / Catalog | クエリ履歴 | Athena Workgroup クエリログ | **Athena Workgroup → S3 → クロスアカウント送付** |
| 中央 BI / Catalog | BI アクセス | QuickSight アクティビティログ | **QuickSight Activity Log → CloudTrail → 監査アカウント** |
| 各アプリ（Producer）| データアクセス | S3 サーバアクセスログ | **S3 Logging → 監査アカウントのログバケット**（クロスアカウント書込み）|
| 各アプリ（Producer）| アプリ操作 | アプリケーション操作監査ログ | **CloudWatch Logs Subscription → Kinesis Firehose → 監査アカウント S3** |
| 共通ドメイン | マスタ変更履歴 | 顧客マスタ更新ログ | 上記同様 |

### 5.8.4 メトリクスの扱い（運用は各アプリ保持）

**今回の方針確認**: 運用メトリクスは各アプリで保持（CloudWatch 標準）、監査・セキュリティ系のみ監査アカウントに集約。

| 種別 | 主用途 | 配置 | 理由 |
|---|---|---|---|
| **運用メトリクス** | 障害検知 / SLO 監視 / オートスケール判定 | **各アプリの CloudWatch**（30 日デフォルト保持）| アプリチームの責任、即時性が必要 |
| **セキュリティメトリクス** | GuardDuty Findings / Macie 検出 / Security Hub Findings | **監査アカウント集約** | 横断検知・SOC 連携 |
| **コスト系** | Cost Explorer / CUR | **親会社統制 or Organization Master** | 経理連携 |
| **長期保存メトリクス** | ML 用特徴量・容量計画 | **データプラットフォーム側で再集計**（必要に応じて）| 分析責務 |

### 5.8.5 データプラットフォーム側で実装する必須項目

監査アカウントが期待するログを「ちゃんと送る」ための実装責任:

| # | 実装項目 | 実装場所 |
|---|---|---|
| 1 | **CloudTrail Data Events 有効化**（S3 / Lake Formation / KMS）| 中央 BI / Catalog アカウント |
| 2 | **Lake Formation Audit Log 有効化** | 中央 BI / Catalog アカウント |
| 3 | **Athena Workgroup でクエリログ出力設定** | 中央 BI / Catalog アカウント |
| 4 | **QuickSight Activity Logging 有効化** | 中央 BI / Catalog アカウント |
| 5 | **S3 Server Access Logging のクロスアカウント設定** | 各アプリアカウント + 共通ドメインアカウント |
| 6 | **KMS CMK の使用イベント出力**（CloudTrail Data Events）| 中央 BI / Catalog アカウント |
| 7 | **VPC Flow Logs 出力設定** | 各アカウントの VPC（送信先は監査アカウント側の設計次第）|
| 8 | **アプリ操作ログの CloudWatch Logs Subscription 設定** | 各アプリアカウント |

### 5.8.6 監査アカウント側に期待する設定（依存事項）

データプラットフォーム標準が**監査アカウント運用主体に依頼する設定**:

| # | 期待する設定 | データプラットフォーム側への影響 |
|---|---|---|
| 1 | **CloudTrail Organization Trail** 設定（全アカウント対象）| 各アカウントで個別に CloudTrail を立てる必要なし |
| 2 | **Security Hub Delegated Admin** | 各アカウントの Security Hub 集約 |
| 3 | **GuardDuty Delegated Admin** | 同上 |
| 4 | **Macie Delegated Admin** | S3 PII スキャンの集約 |
| 5 | **Config Aggregator** | 全アカウントの構成監視 |
| 6 | **クロスアカウントログ受信用 S3 バケット**（Object Lock + 長期保管）| ログ送付先として利用 |
| 7 | **クロスアカウント書込み権限の付与**（バケットポリシー）| 各アプリ・中央 BI から書込みできる |
| 8 | **セキュリティ Findings 通知の管理プロセス** | データ標準で検出した PII 漏洩等の対応フロー |

### 5.8.7 セキュリティアラート連携の流れ

```mermaid
sequenceDiagram
    autonumber
    participant DP as データプラットフォーム<br/>(各アプリ / 中央 BI)
    participant Audit as 監査アカウント<br/>(別組織)
    participant SOC as 親会社 SoC

    Note over DP, SOC: 通常運用
    DP->>Audit: ログ送付（CloudTrail / S3 / etc.）
    Audit->>Audit: Security Hub / GuardDuty / Macie で分析

    Note over DP, SOC: インシデント検知時
    Audit->>SOC: Findings 通知
    SOC->>Audit: トリアージ
    SOC->>DP: 対応依頼（データ標準チームへ）
    DP->>DP: 該当アプリ / Catalog 側で対応
    DP->>SOC: 対応結果報告
    Audit->>Audit: Findings クローズ
```

### 5.8.8 残課題（監査アカウント別組織との合意事項）

| # | 確認事項 | 影響 |
|---|---|---|
| 1 | **監査アカウント運用主体との連絡窓口**（誰に何を聞くか）| 設計の進め方 |
| 2 | **ログ送付の権限設計**（クロスアカウント IAM Role / バケットポリシー）| 実装方法 |
| 3 | **監査アカウント側のログ保管期間** | データ標準側の §NFR-7 コンプラ要件と整合 |
| 4 | **Findings 通知の受け取りフロー**（SNS / EventBridge / メール / Slack 等）| インシデント対応設計 |
| 5 | **監査アカウント障害時のフォールバック**（自前で一時的に集約するか）| BCP / 5 nines 想定 |
| 6 | **コスト負担モデル**（監査アカウントの利用料はデータ標準側に按分されるか）| 予算計画 |
| 7 | **Athena クエリログ等のセンシティブ情報を含むログの扱い**（顧客企業データを参照したクエリ内容）| プライバシー設計 |
| 8 | **Transit Gateway 経由のクロスアカウント通信のログ取得範囲** | ネットワーク監査 |

### 5.8.9 図解: ログ送付の全体像

```mermaid
flowchart TB
    subgraph DataPlatform["データプラットフォーム標準（スコープ内）"]
        subgraph BICat["中央 BI / Catalog アカウント"]
            LF[Lake Formation]
            Athena
            QS[QuickSight]
            KMS[KMS CMK]
        end

        subgraph App1["App 1（Producer）"]
            S1[S3]
            DB1[運用 DB]
            App1Logs[CloudWatch Logs]
        end

        subgraph App2["App 2（Producer）"]
            S2[S3]
            DB2[運用 DB]
        end

        subgraph CommonD["共通ドメイン"]
            Master[顧客マスタ]
        end
    end

    subgraph Audit["監査アカウント（スコープ外）"]
        direction TB
        CT[CloudTrail Organization Trail]
        SH[Security Hub Delegated Admin]
        GD[GuardDuty Delegated Admin]
        Macie[Macie Delegated Admin]
        Cfg[Config Aggregator]
        LogBucket[(S3 長期保管バケット<br/>Object Lock)]
    end

    %% コントロールプレーン → CloudTrail
    LF -.管理イベント.-> CT
    Athena -.管理イベント.-> CT
    QS -.管理イベント.-> CT
    KMS -.管理イベント.-> CT
    App1 -.管理イベント.-> CT
    App2 -.管理イベント.-> CT
    CommonD -.管理イベント.-> CT

    %% データプレーン → CloudTrail Data Events
    LF -.データイベント.-> CT
    S1 -.S3 アクセスログ.-> LogBucket
    S2 -.S3 アクセスログ.-> LogBucket

    %% Athena クエリログ
    Athena -.クエリログ.-> LogBucket

    %% QuickSight アクティビティ
    QS -.アクティビティログ.-> CT

    %% アプリ操作ログ
    App1Logs -.subscription.-> LogBucket

    %% Macie が S3 をスキャン
    S1 -.PII スキャン対象.-> Macie
    S2 -.PII スキャン対象.-> Macie
    Master -.PII スキャン対象.-> Macie

    style DataPlatform fill:#e3f2fd
    style Audit fill:#fce4ec
```

---

## 6. 決定状況と残課題

### 6.1 仮案で決定済み（[strawman-proposal.md](strawman-proposal.md) に反映済）

| # | 決定事項 | 仮案での選定 | 根拠 / 参照 |
|---|---|---|---|
| 1 | **Consumer 役割のパターン**（α / β / γ）| **β**（中央 Consumer 集約）| Q1 アプリチームスキルなし / Q4 BI チームなし → α 不適合、γ は組織体制が未整備のため Phase 2 で検討。Path C 段階移行 |
| 2 | **Catalog Account / Governance Account の配置**（Option A / B / C）| **Option B**（Catalog 同居 Consumer、+2 アカウント）| §5.2 親会社統制が Audit / Security 集約を担う前提 / §5.4 Option 比較表 / 仮案規模に最適 |
| 3 | **Audit ログの最終集約先** | **親会社統制アカウント**（既存）| ユーザー環境の前提として確認済 |
| 4 | **共通参照データの扱い** | **共通ドメイン専用アカウント新設**（+1）| §3.3 案 2、業界標準（DAMA / Data Mesh）|
| 5 | **SageMaker Catalog（旧 DataZone）採否** | **Phase 1 不採用、Phase 2 再評価** | [DP-ADR-001](adr/DP-ADR-001-sagemaker-catalog-adoption-deferred.md)。Phase 1 規模では ROI 低い、+$1,360/年コスト・運用複雑度を抑制、Phase 2 で利用者拡大時に再評価 |

### 6.2 残課題（ヒアリングまたは追加検討が必要な事項）

| # | 決定事項 | 選択肢 | 影響範囲 | 確認方法 |
|---|---|---|---|---|
| 1 | **既存「共通基盤アカウント」のスコープ拡張** | 認証専用に閉じる / Service Catalog 配布元等も担わせる | API 側決定との整合 | API 標準化推進者との調整 |
| 2 | **環境分離**（prod / stg / dev）| 同一アカウントで Realm 分離 / 環境別にアカウント分離 | アカウント数の倍加、運用負荷 | ヒアリング G（インフラチーム）|
| 3 | **監査アカウントとの合意事項**（Option B 成立 + §5.8 監査責務分離の前提）| [§5.8.8 残課題 8 項目](#588-残課題監査アカウント別組織との合意事項)（連絡窓口 / 権限設計 / 保管期間 / Findings 通知 / 障害時 FB / コスト按分 / クエリログ機密性 / TGW 通信ログ）| 監査アカウント運用主体との合意で確定 | ヒアリング G-4 / 監査アカウント運用主体への問合せ |
| 4 | **役割 3（Catalog 管理者）と役割 4（BI チーム）の人員分離**（Option B 成立の前提）| 完全分離可能 / 部分重複 / 重複前提 | 責務分離の実質的な強度、Config Rules 検知設計 | ヒアリング G-5 で確認 |
| 5 | **将来 Option C 移行のトリガ条件**（規模拡大時）| 4 条件のうちどれを発動条件とするか | Phase 2 計画、運用設計 | Phase 1 運用開始後にレビュー、[strawman-proposal.md §4.3](strawman-proposal.md) 参照 |
| 6 | **DR / クロスリージョン設計** | リージョン障害時の Catalog / Consumer / 共通ドメイン の復旧戦略 | NFR-DR §NFR-5（未作成）の前提 | [proposal/nfr/05-dr.md](proposal/nfr/05-dr.md)（未作成）と連動 |

---

## 7. 反映先（合意後の後続作業）

ヒアリング Phase A 以降で前提が確認できれば、以下に反映する。**Option B（Catalog 同居 Consumer、+2 アカウント）** が確定したことを前提とする。

| # | 反映先 | 内容 |
|---|---|---|
| 1 | [proposal/00-index.md §0.2 比較表](proposal/00-index.md) | 「分散標準」記述を「**Federated（3 役割、Option B Catalog 同居 Consumer 推奨）**」に改訂 |
| 2 | [proposal/fr/02-storage.md](proposal/fr/02-storage.md) | 「Producer 役割」の明示、Central（Catalog）/ Consumer 役割の追記、**Option B 採用時の同居構造**、Lake Formation 共有モデルの図解、IAM Role 分離方針（`DataLakeAdminRole` / `DataAnalystRole` / `DataReaderRole`）|
| 3 | [proposal/fr/05-governance.md](proposal/fr/05-governance.md) | §FR-5.1 権限制御を Lake Formation Cross-Account + **同アカウント内 IAM Role 分離**前提に補強、Permission Boundary / SCP / Config Rules の必須化 |
| 4 | proposal/common/01-architecture.md（未作成）| 新規執筆。本資料 §1-§5 を §C-DATA-1.5「中央集約 vs 分散ガイド」フレームに展開、API §C-1.5 と並ぶ位置付け、**Option A/B/C 配置 + Pattern α/β/γ Consumer の組み合わせマトリクス**を §C-DATA-1.6 として明示 |
| 5 | proposal/common/03-ownership-raci.md（未作成）| **7 役割と RACI** の対応（[strawman-proposal.md §3](strawman-proposal.md) 参照）、特に役割 3（Catalog 管理者 = `DataLakeAdminRole`）と役割 4（BI チーム = `DataAnalystRole`）の人員分離原則を明示 |
| 6 | [internal-evaluation.md](internal-evaluation.md) | 抽出方針に「API と同型 Federated だが中央のスコープが Catalog 分だけ広く、親会社統制が監査・セキュリティ集約を担う場合は Catalog 同居 Consumer (Option B) で +2 アカウントに圧縮可能」根拠を追記 |
| 7 | [powerpoint-outline-and-references.md §1.3-1.4](powerpoint-outline-and-references.md) | 構成概要図を **Option B 版（+2 アカウント、中央 BI / Catalog 同居）**に差し替え、§1.4「アカウント体系」スライドで Option A/B/C の選定根拠を提示 |
| 8 | [strawman-proposal.md](strawman-proposal.md) | （反映済）Option B 仕様に改訂、§2 アカウント構成 +2、§3 役割 3 を `DataLakeAdminRole` として位置付け、§5 前提 8/9 追加、§6 ヒアリング G-4/5/6 追加 |
| 9 | proposal/fr/06-personas.md（既存）| §FR-6 ペルソナ別実装パターンに **IAM Role 別の利用パターン**（`DataLakeAdminRole` / `DataAnalystRole` / `DataReaderRole`）を反映 |
| 10 | [proposal/fr/05-governance.md](proposal/fr/05-governance.md) §FR-5.4 監査ログ | **§5.8 監査責務分離設計を反映**: 監査アカウントへのログ送付経路 7 種、データプラットフォーム側必須実装 8 項目、監査アカウント側に期待する 8 項目を明文化 |
| 11 | proposal/nfr/04-security.md（既存・要更新）| §NFR-4 セキュリティに **監査アカウントとの責務分離**、ログ送付経路、クロスアカウント送付の暗号化要件を追記 |
| 12 | proposal/nfr/06-operations.md（既存・要更新）| §NFR-6 運用に **メトリクスの責務分離**（運用は各アプリ / 監査・セキュリティは監査アカウント）を明示 |
| 13 | proposal/common/04-tbd-summary.md（未作成）| **監査アカウント運用主体との合意事項 8 項目**（§5.8.8 残課題）を要確認事項として記録 |
| 14 | [strawman-proposal.md §5 前提](strawman-proposal.md) | 前提 8 を **「監査アカウント運用主体との合意」** に書き換え（旧「親会社統制が CloudTrail / SH / Macie 等を集約」）|
| 15 | [hearing-slide-deck.md §4.2](hearing-slide-deck.md) | スライド §4.2 を **「監査アカウントとの責務分離 + 期待する設定」** に再構成（旧「親会社統制の責務範囲確認」）|

### 7.1 反映の依存順序

```mermaid
flowchart TB
    H["ヒアリング Phase A〜D<br/>(strawman 仮案検証)"]
    H --> Strawman["strawman-proposal.md 改訂<br/>(既改訂済、合意後さらに更新)"]

    Strawman --> P1["proposal/00-index.md<br/>(SSOT 改訂)"]
    Strawman --> P2["proposal/fr/02-storage.md<br/>(IAM Role 分離追記)"]
    Strawman --> P3["proposal/fr/05-governance.md<br/>(Cross-Account 補強)"]
    Strawman --> C1["proposal/common/01-architecture.md<br/>(新規執筆)"]
    Strawman --> C3["proposal/common/03-ownership-raci.md<br/>(新規執筆)"]

    P1 --> Internal["internal-evaluation.md<br/>(抽出方針追記)"]
    C1 --> PPT["powerpoint-outline-and-references.md<br/>(構成図差し替え)"]
    C3 --> PPT

    style Strawman fill:#fff3e0
    style C1 fill:#e8f5e9
    style C3 fill:#e8f5e9
```

---

## 8. 関連ドキュメント

### 本領域内

- [data-platform-document-structure.md](data-platform-document-structure.md) — 領域全体 SSOT
- [internal-evaluation.md](internal-evaluation.md) — 抽出方針の裏どり資料
- [proposal/fr/02-storage.md](proposal/fr/02-storage.md) — §FR-2 保存先標準

### 兄弟領域（API、雛形元）

- [../api-platform/proposal/common/01-reference-architecture.md](../api-platform/proposal/common/01-reference-architecture.md) — §C-1.5「中央集約 vs 分散ガイド」フレーム（本資料の元構造）

### AWS 公式

- [AWS Prescriptive Guidance: Strategy for Data Mesh](https://docs.aws.amazon.com/prescriptive-guidance/latest/strategy-data-mesh/aws-offerings-data-mesh.html)
- [Lake Formation Cross-Account Permissions](https://docs.aws.amazon.com/lake-formation/latest/dg/cross-account-permissions.html)
- [Secure Data Mesh Guidance on AWS](https://aws.amazon.com/solutions/guidance/secure-data-mesh-with-distributed-data-asset-ownership-on-aws)
- [Build enterprise data mesh with DataZone, CDK, CFN](https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/build-enterprise-data-mesh-amazon-data-zone.html)
- [AWS Well-Architected Data Analytics Lens](https://docs.aws.amazon.com/wellarchitected/latest/analytics-lens/analytics-lens.html)

### 業界・参考事例

- [Martin Fowler / Dehghani — Monolithic Data Lake to Data Mesh](https://martinfowler.com/articles/data-monolith-to-mesh.html)
- [Netflix UDA](https://netflixtechblog.com/uda-unified-data-architecture-6a6aee261d8d)
- [How Spotify Built Its Data Platform](https://blog.bytebytego.com/p/how-spotify-built-its-data-platform)
- [BBVA Global Data Platform](https://aws.amazon.com/blogs/industries/part-1-bbva-building-a-multi-region-multi-country-global-data-and-ml-platform-at-scale/)
