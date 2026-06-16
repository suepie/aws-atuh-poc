# PowerPoint 資料 構成案・参考資料マトリクス（データプラットフォーム標準）

> **目的**: 各アプリ向けデータプラットフォーム標準の **PowerPoint 資料の大項目構成 + 各項目の参考資料一覧**を整理した SSOT。
> **背景**: ヒアリングと並行して資料を準備するため、各章・項目で**どのドキュメントを参照すれば良いか**を一覧化。
> **対象読者**: PowerPoint 作成担当者 / 要件定義レビュー担当者 / 各アプリ提示担当者
> **更新基準**: 大項目構成の変更時、参考資料追加時
> **雛形元**: [../requirements/powerpoint-outline-and-references.md](../requirements/powerpoint-outline-and-references.md)（認証側）
>
> **関連 (スライド単位の内容)**: [hearing-slide-deck.md](hearing-slide-deck.md) — ヒアリング当日に提示するスライドの **タイトル / 内容 / 回答例** を 41 スライド分まとめた具体物。本資料が戦略マトリクスなのに対し、hearing-slide-deck.md は **実装スライド**。

---

## 0. 構成サマリー

| 章 | 項目数 | 主題 | スライド枚数目安 | 時間配分目安 |
|:-:|:-:|---|:-:|:-:|
| 1 | 6 | 全体方針・前提 | 24 | 30 分 |
| 2 | 3 | 対象データ・分類（§FR-1）| 12 | 20 分 |
| 3 | 5 | 保存先標準（§FR-2）| 20 | 25 分 |
| 4 | 4 | データ連携（§FR-3）| 16 | 20 分 |
| 5 | 4 | 閲覧・活用（§FR-4）| 16 | 20 分 |
| 6 | 4 | ガバナンス（§FR-5）| 16 | 25 分 |
| 7 | 4 | ペルソナ別実装（§FR-6）| 16 | 18 分 |
| 8 | 9 | 非機能要件（§NFR-1〜9）| 36 | 35 分 |
| **計** | **39** | - | **~156** | **~193 分（3.2 時間）** |

> **改訂履歴**: 初版作成。詳細は §13 改訂履歴。

> ヒアリング 3 回会議計画（M1/M2/M3、SSOT §2 Phase 2 で作成予定）と照合：M1（章 1-2 中心：対象データ確定）/ M2（章 3-7 中心：保存・連携・閲覧・ガバナンス・ペルソナ）/ M3（章 8 + 最終意思決定：非機能）

### 🔑 PowerPoint と社内文書の narrative 差分（重要）

| 文書 | 主読者 | アーキテクチャの提示順序 | narrative |
|---|---|---|---|
| **PowerPoint（本文書）**| 各アプリ開発・運用担当者 / プラットフォーム標準化推進者 / データオーナー候補 | **データレイク中心 → 用途別追加** | **「まずは S3 データレイクで集約、必要に応じて DWH/検索系を追加」** |
| **proposal/ + internal-evaluation.md** | 標準化推進側設計者 + アプリ側技術担当 | 4 種保存先を等価並列で提示 → 使い分けマトリクス | 「ポリグロット（用途別に最適サービス）、レイクが汎用デフォルト」|

**両文書の関係**: **標準構造は同じ**（4 種保存先 + ガバナンス横断）。**見せ方の順序のみ違う**。PowerPoint は「**S3 中心の安心感を与えつつ、必要に応じて DWH/検索系を追加できる柔軟性も示す**」narrative を採用。これにより「保存先 4 種類もあるのか」という認知負荷を抑える。

---

## 1. 全体方針・前提（6 項目）

### 1.1 標準化の進め方・ヒアリング計画

**概要**: ヒアリング 3 回計画、抽出方針（5 つの源泉）、**本標準のスコープ宣言**（対象外領域: BI ツール選定の詳細 / アプリ内部のメモリ DB 等）。

| 種別 | 参考資料 |
|---|---|
| **内部** | [data-platform-document-structure.md §0 ナラティブ](data-platform-document-structure.md) |
| **内部** | [internal-evaluation.md §2 抽出の 5 つの源泉](internal-evaluation.md) |
| **内部** | [proposal/00-index.md §0.4 §X.0 章冒頭規約](proposal/00-index.md) |
| **計画上** | hearing-strategy.md（SSOT §2 Phase 2、未作成）|
| **外部** | [IPA 非機能要求グレード 2018](https://www.ipa.go.jp/archive/digital/iot-en-ci/jyouryuu/hikinou/index.html) |
| **外部** | [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/) / [Data Analytics Lens](https://docs.aws.amazon.com/wellarchitected/latest/analytics-lens/analytics-lens.html) |

**スコープ明示すべき対象外領域**：
- BI ツール詳細選定（QuickSight 採用は決定済み、その上の利用詳細は対象外）
- アプリ内部の処理中データ（メモリ上の一時データ）
- 業務マスタデータの統合 MDM（別領域）
- データカタログ製品の SaaS 比較（Alation / Collibra 等は SaaS 不採用方針で対象外）

### 1.2 基本方針 4 軸とアーキテクチャスタンス

**概要**: 共有認証基盤の基本方針 4 軸（絶対安全 / どんなユースケースでも / 効率 / 運用負荷・コスト）のデータ領域翻案。**AWS ネイティブ優先・SaaS 原則不採用** の根拠。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/00-index.md §0.2 基本方針](proposal/00-index.md) |
| **proposal** | [proposal/fr/01-data-catalog.md §FR-1.0.A 本標準のスタンス](proposal/fr/01-data-catalog.md) |
| **proposal** | [proposal/fr/02-storage.md §FR-2.0.A 本標準のスタンス](proposal/fr/02-storage.md) |
| **内部** | [internal-evaluation.md §2.2 各源泉の詳細](internal-evaluation.md) |
| **計画上** | proposal/common/02-service-selection.md §C-2.3 SaaS 採用例外条件（未作成）|

### 1.3 アーキテクチャ方針（**S3 データレイク中心**、用途に応じて DWH / 検索系を追加）

> **PowerPoint での narrative**: **「基本方針: S3 データレイクで集約」**を前面に出し、**「必要に応じて DWH/検索系を追加可能」**として用途別保存先を後置する構成。
>
> **社内向け proposal との関係**: proposal/ では「用途別 4 種保存先を等価並列で提示 + 使い分けマトリクス」だが、PowerPoint では**レイク中心 narrative**で提示。**標準構造は同じ**（4 種保存先 + ガバナンス横断）だが、**見せ方を「レイク → 用途別追加」順**にすることで「保存先 4 種類もあるのか」という認知負荷を抑える。

**概要**: S3 データレイク（Medallion 3 層 = raw/curated/analytics）を基本方針として提示。ただし以下の用途には**個別の保存先**を提供。

#### スライド構成案（5 枚）

| # | スライド | 内容 |
|---|---|---|
| **1** | 基本方針 | **「S3 データレイクで集約します」**（Medallion 3 層、業界標準）|
| **2** | レイク集約のメリット | 単一データソース / 横断分析 / 安価 / 暗号化・アクセス制御の集約 / Glue Catalog でメタデータ集約 |
| **3** | レイクだけで足りない要件の認識 | 一部のユースケースは S3 + Athena だけでは対応困難:<br/>- 同時 BI 利用者多数（DWH）<br/>- 全文検索・ベクトル検索（検索系）<br/>- ミリ秒応答の OLTP（運用ストア）|
| **4** | 追加保存先の選択肢 | **3 つの選択肢**:<br/>① **Redshift**（高頻度 BI / 同時実行多数）<br/>② **OpenSearch Service**（全文検索 / ログ可視化 / ベクトル）<br/>③ **Aurora / DynamoDB**（OLTP、業務 TX）|
| **5** | データ × 用途 → 保存先判定フロー | データオーナーは「レイク（デフォルト）/ 追加保存先のどれか」を選択 |

#### 重要メッセージング

| 言ってはいけない | 言うべき |
|---|---|
| ❌ 「4 種類の保存先を使い分けます」（複雑性懸念を与える）| ✅ 「**まずはレイクに集約します**」（シンプル、安心）|
| ❌ 「最初から DWH・検索系・OLTP を建てます」 | ✅ 「**ほとんどのアプリは S3 で対応**」 |
| ❌ 「ポリグロット永続化」 | ✅ 「**用途次第で必要なだけ追加**」 |

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/02-storage.md §FR-2.5 用途別使い分けマトリクス](proposal/fr/02-storage.md)（**レイク中心 narrative の核**）|
| **計画上** | proposal/common/01-architecture.md §C-1 参照アーキテクチャ（未作成）|
| **外部** | [AWS Lake House Architecture](https://aws.amazon.com/big-data/datalakes-and-analytics/) / [Medallion Architecture（Databricks 由来）](https://www.databricks.com/glossary/medallion-architecture) / [AWS Well-Architected Data Analytics Lens](https://docs.aws.amazon.com/wellarchitected/latest/analytics-lens/analytics-lens.html) |

### 1.4 構成概要図（全体 + AWS 構成 + データフロー）

**概要**: 全体構成図 + 想定 AWS 構成図 + データフロー（運用ストア → CDC → レイク → 分析 → BI）+ アカウント分離想定。

> **§1.3 narrative との整合**: メインの構成図は **S3 レイク中心版**を提示。**追加保存先として DWH / 検索系の構成図**を「**こういう場合に追加可能**」として後置。順序が重要（レイク → 追加）。

| 種別 | 参考資料 |
|---|---|
| **計画上** | proposal/common/01-architecture.md §C-1.1 全体構成図 / §C-1.2 想定 AWS 構成図 / §C-1.3 データフロー（未作成）|
| **proposal** | [proposal/fr/02-storage.md §FR-2.5 使い分けマトリクス](proposal/fr/02-storage.md) |
| **外部** | [AWS Multi-Account Strategy](https://aws.amazon.com/controltower/) / [AWS Reference Architectures - Analytics](https://aws.amazon.com/architecture/analytics-big-data/) |

### 1.5 AWS サービス選定（Athena vs Redshift / Glue vs EMR / Kinesis vs MSK 等）

**概要**: 用途別の AWS サービス選定軸、選定マトリクス、SaaS 不採用の根拠と例外条件。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/02-storage.md §FR-2.1〜2.4](proposal/fr/02-storage.md) |
| **proposal** | [proposal/fr/03-pipeline.md §FR-3.1〜3.4](proposal/fr/03-pipeline.md) |
| **proposal** | [proposal/fr/04-consumption.md §FR-4.1〜4.4](proposal/fr/04-consumption.md) |
| **計画上** | proposal/common/02-service-selection.md §C-2 サービス選定軸（未作成）|
| **計画上** | service-selection-decision.md（SSOT §2 Phase 3、未作成）|
| **外部** | [Athena Pricing](https://aws.amazon.com/athena/pricing/) / [Redshift Pricing](https://aws.amazon.com/redshift/pricing/) / [Glue Pricing](https://aws.amazon.com/glue/pricing/) |

### 1.6 移行方針・標準展開計画

**概要**: 既存データプラットフォーム（自前構築 / SaaS / 散在 S3 等）からの移行戦略 + 標準展開スケジュール + データオーナー任命プロセス。

| 種別 | 参考資料 |
|---|---|
| **計画上** | proposal/nfr/09-lifecycle.md §NFR-9.4 既存データ移行（未作成）|
| **計画上** | proposal/common/05-schedule.md §C-5 スケジュール（未作成）|
| **proposal** | [proposal/fr/01-data-catalog.md §FR-1.3 データオーナー](proposal/fr/01-data-catalog.md) |
| **外部** | [AWS DMS](https://aws.amazon.com/dms/) / [AWS Migration Hub](https://aws.amazon.com/migration-hub/) |

---

## 2. 対象データ・分類（§FR-1）（3 項目）

### 2.1 データ区分（業務 TX / アプリログ / 監査ログ / メトリクス / 外部連携）

**概要**: 5 区分の定義・例・標準保存先マッピング。5 区分に収まらないデータの扱い（区分追加プロセス）。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/01-data-catalog.md §FR-1.1 データ区分](proposal/fr/01-data-catalog.md) |
| **proposal** | [proposal/fr/02-storage.md §FR-2.5 用途別使い分けマトリクス](proposal/fr/02-storage.md)（区分 → 保存先の橋渡し）|
| **計画上** | hearing-checklist.md（未作成、A 区分マッピング項目想定）|

### 2.2 機密度分類（4 階層 + PII 識別）

**概要**: Public / Internal / Confidential / Restricted の 4 階層 + PII フラグ必須化。ガバナンス（§FR-5）との連動。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/01-data-catalog.md §FR-1.2 機密度分類](proposal/fr/01-data-catalog.md) |
| **proposal** | [proposal/fr/05-governance.md §FR-5.3 PII 取り扱い](proposal/fr/05-governance.md) |
| **外部** | [個人情報保護法 (APPI)](https://www.ppc.go.jp/) / [Amazon Macie](https://aws.amazon.com/macie/) / [NIST SP 800-122 PII Guidelines](https://csrc.nist.gov/publications/detail/sp/800-122/final) |

### 2.3 データオーナー制度

**概要**: オーナー必須化、データスチュワード、オーナー不在データの取り扱い、組織配置（§C-3 RACI への連携）。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/01-data-catalog.md §FR-1.3 データオーナー](proposal/fr/01-data-catalog.md) |
| **計画上** | proposal/common/03-ownership-raci.md §C-3 RACI（未作成）|
| **外部** | [Data Mesh Principles](https://martinfowler.com/articles/data-mesh-principles.html) / [DAMA-DMBOK 2 Data Governance](https://www.dama.org/cpages/body-of-knowledge) |

---

## 3. 保存先標準（§FR-2）（5 項目）

### 3.1 データレイク（S3 + Glue Catalog + Medallion 3 層）

**概要**: バケット設計（raw / curated / analytics の 3 層）、Glue Data Catalog、パーティション戦略、ストレージクラス・ライフサイクル。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/02-storage.md §FR-2.1 データレイク](proposal/fr/02-storage.md) |
| **外部** | [AWS Lake House Architecture](https://aws.amazon.com/big-data/datalakes-and-analytics/) / [S3 Storage Classes](https://aws.amazon.com/s3/storage-classes/) / [Glue Data Catalog](https://docs.aws.amazon.com/glue/latest/dg/components-overview.html) |

### 3.2 DWH（Redshift プロビジョンド / Serverless）

**概要**: Redshift 採用判定基準、Serverless vs プロビジョンド、Redshift Spectrum によるレイク連携。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/02-storage.md §FR-2.2 DWH](proposal/fr/02-storage.md) |
| **外部** | [Redshift Serverless](https://aws.amazon.com/redshift/redshift-serverless/) / [Redshift Spectrum](https://docs.aws.amazon.com/redshift/latest/dg/c-using-spectrum.html) / [Zero-ETL Aurora to Redshift](https://aws.amazon.com/blogs/aws/new-aurora-zero-etl-integration-with-amazon-redshift/) |

### 3.3 運用ストア（Aurora / RDS / DynamoDB）

**概要**: OLTP 系ストアの使い分け、分析系（レイク・DWH）への連携前提。SaaS DB（Snowflake / MongoDB Atlas 等）の不採用根拠。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/02-storage.md §FR-2.3 運用ストア](proposal/fr/02-storage.md) |
| **外部** | [Aurora vs RDS](https://aws.amazon.com/rds/aurora/faqs/) / [DynamoDB Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html) |

### 3.4 検索系（OpenSearch Service）

**概要**: OpenSearch 採用判定基準、Serverless vs プロビジョンド、Tiered 構成（ホット/コールド）。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/02-storage.md §FR-2.4 検索系](proposal/fr/02-storage.md) |
| **外部** | [OpenSearch Serverless](https://aws.amazon.com/opensearch-service/features/serverless/) / [OpenSearch vs Elasticsearch](https://aws.amazon.com/opensearch-service/the-elk-stack/) |

### 3.5 用途別使い分けマトリクス（データ × 機密度 × アクセスパターン → 保存先）

**概要**: §FR-1.1 区分・§FR-1.2 機密度・アクセスパターンの 3 軸から保存先を決める標準マトリクス。例外パターン申請プロセス。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/02-storage.md §FR-2.5 用途別使い分けマトリクス](proposal/fr/02-storage.md) |
| **計画上** | functional-requirements.md FR-STORE-* 詳細マトリクス（未作成）|

---

## 4. データ連携（§FR-3）（4 項目）

### 4.1 バッチ連携（Glue / Step Functions / Lambda / EMR Serverless）

**概要**: バッチ連携サービスの使い分け、スケジュール（EventBridge Scheduler）、リトライ・冪等性・監視標準。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/03-pipeline.md §FR-3.1 バッチ連携](proposal/fr/03-pipeline.md) |
| **外部** | [AWS Glue](https://aws.amazon.com/glue/) / [Step Functions](https://aws.amazon.com/step-functions/) / [EMR Serverless](https://aws.amazon.com/emr/serverless/) |

### 4.2 ストリーム連携（Kinesis / MSK / EventBridge Pipes）

**概要**: ストリーミングサービスの使い分け、冪等性、Schema Registry、ラグ監視。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/03-pipeline.md §FR-3.2 ストリーム連携](proposal/fr/03-pipeline.md) |
| **外部** | [Kinesis Data Streams](https://aws.amazon.com/kinesis/data-streams/) / [Kinesis Firehose](https://aws.amazon.com/kinesis/data-firehose/) / [MSK](https://aws.amazon.com/msk/) / [Glue Schema Registry](https://docs.aws.amazon.com/glue/latest/dg/schema-registry.html) |

### 4.3 CDC（DMS / Zero-ETL / DynamoDB Streams）

**概要**: CDC 連携の選定基準、運用 DB への負荷影響、スキーマ変更伝播戦略。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/03-pipeline.md §FR-3.3 CDC](proposal/fr/03-pipeline.md) |
| **外部** | [AWS DMS](https://aws.amazon.com/dms/) / [Aurora Zero-ETL](https://aws.amazon.com/blogs/aws/new-aurora-zero-etl-integration-with-amazon-redshift/) / [DynamoDB Streams](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Streams.html) |

### 4.4 ETL/ELT 標準（ELT 推奨、冪等性、データ品質、メタデータ管理）

**概要**: ELT 原則、冪等性設計、データ品質チェック（Glue Data Quality）、メタデータ管理、Lineage 機能。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/03-pipeline.md §FR-3.4 ETL/ELT 標準](proposal/fr/03-pipeline.md) |
| **外部** | [Glue Data Quality](https://aws.amazon.com/glue/features/data-quality/) / [Medallion Architecture（ELT 推奨の根拠）](https://www.databricks.com/glossary/medallion-architecture) |

---

## 5. 閲覧・活用（§FR-4）（4 項目）

### 5.1 クエリ（Athena / Redshift）

**概要**: Athena ワークグループ、コスト統制（per-query スキャン上限）、Federated Query、Redshift WLM。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/04-consumption.md §FR-4.1 クエリ](proposal/fr/04-consumption.md) |
| **外部** | [Athena Workgroups](https://docs.aws.amazon.com/athena/latest/ug/workgroups.html) / [Athena Federated Query](https://docs.aws.amazon.com/athena/latest/ug/connect-to-a-data-source.html) |

### 5.2 BI（QuickSight）

**概要**: QuickSight Enterprise Edition 採用、SPICE、行/列レベルセキュリティ、SaaS BI（Tableau 等）不採用根拠。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/04-consumption.md §FR-4.2 BI](proposal/fr/04-consumption.md) |
| **外部** | [Amazon QuickSight](https://aws.amazon.com/quicksight/) / [QuickSight SPICE](https://docs.aws.amazon.com/quicksight/latest/user/spice.html) / [QuickSight Row-Level Security](https://docs.aws.amazon.com/quicksight/latest/user/restrict-access-to-a-data-set-using-row-level-security.html) |

### 5.3 アプリ参照（API Gateway + Lambda）

**概要**: API 経由データ提供の標準、認証（共有認証基盤 JWT）、レイテンシ要件、API プラットフォーム標準との分担境界。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/04-consumption.md §FR-4.3 アプリ参照](proposal/fr/04-consumption.md) |
| **隣接領域** | [../api-platform/00-index.md](../api-platform/00-index.md) — API プラットフォーム標準 |
| **隣接領域** | [../requirements/](../requirements/00-index.md) — 共有認証基盤 |

### 5.4 直接アクセス（例外的、最小化）

**概要**: 直接 S3 / DB アクセスの原則禁止、例外条件（オーナー承認 / 有限期間 / アクセスログ）、典型シナリオ（大量ダウンロード / バックアップ）。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/04-consumption.md §FR-4.4 直接アクセス](proposal/fr/04-consumption.md) |
| **proposal** | [proposal/fr/05-governance.md §FR-5.4 監査ログ](proposal/fr/05-governance.md)（直接アクセスログ取得）|

---

## 6. ガバナンス（§FR-5）（4 項目）

### 6.1 権限制御（Lake Formation / IAM、機密度別ポリシー）

**概要**: Lake Formation + IAM の標準制御、機密度 4 階層別ポリシー、Need-to-know 原則、クロスアカウント共有。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/05-governance.md §FR-5.1 権限制御](proposal/fr/05-governance.md) |
| **外部** | [AWS Lake Formation](https://aws.amazon.com/lake-formation/) / [Lake Formation Tag-Based Access Control](https://docs.aws.amazon.com/lake-formation/latest/dg/tag-based-access-control.html) |

### 6.2 暗号化（at-rest / in-transit、KMS CMK、鍵ローテーション）

**概要**: 機密度別の at-rest / in-transit 暗号化標準、KMS CMK 利用条件、自動ローテーション、Multi-Region キー。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/05-governance.md §FR-5.2 暗号化](proposal/fr/05-governance.md) |
| **外部** | [AWS KMS](https://aws.amazon.com/kms/) / [KMS Best Practices](https://docs.aws.amazon.com/kms/latest/developerguide/best-practices.html) / [Multi-Region Keys](https://docs.aws.amazon.com/kms/latest/developerguide/multi-region-keys-overview.html) |

### 6.3 PII 取り扱い（識別必須、Macie、マスキング・仮名化、棚卸し）

**概要**: PII フラグ必須化、Amazon Macie による自動検出、マスキング・仮名化の手法、四半期棚卸しプロセス。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/05-governance.md §FR-5.3 PII 取り扱い](proposal/fr/05-governance.md) |
| **外部** | [Amazon Macie](https://aws.amazon.com/macie/) / [Lake Formation Data Filters](https://docs.aws.amazon.com/lake-formation/latest/dg/data-filters-about.html) / [個人情報保護法 (APPI)](https://www.ppc.go.jp/) / [GDPR Article 4(5) Pseudonymisation](https://gdpr-info.eu/art-4-gdpr/) |

### 6.4 監査ログ（CloudTrail / Lake Formation / Athena ログ、改ざん不能保管）

**概要**: 監査対象（コントロールプレーン / データプレーン）、S3 Object Lock Compliance モード、監査アカウント集中管理、リアルタイムアラート。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/05-governance.md §FR-5.4 監査ログ](proposal/fr/05-governance.md) |
| **外部** | [AWS CloudTrail](https://aws.amazon.com/cloudtrail/) / [S3 Object Lock](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html) / [AWS Security Hub](https://aws.amazon.com/security-hub/) / [Amazon GuardDuty](https://aws.amazon.com/guardduty/) |

---

## 7. ペルソナ別実装（§FR-6）（4 項目）

### 7.1 業務利用者（BI 中心 / QuickSight Reader）

**概要**: 業務部門・経営層向け標準ルート。QuickSight + SPICE、SQL 不要、行/列レベルセキュリティ、想定ライセンス数。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/06-personas.md §FR-6.1 業務利用者](proposal/fr/06-personas.md) |
| **proposal** | [proposal/fr/04-consumption.md §FR-4.2 BI](proposal/fr/04-consumption.md) |

### 7.2 開発者（API 連携 / 運用ストア / IaC / CI/CD）

**概要**: アプリ開発者向け標準ルート。API Gateway + Lambda + Athena/Redshift、IaC（CDK/Terraform）必須、標準準拠の CI チェック。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/06-personas.md §FR-6.2 開発者](proposal/fr/06-personas.md) |
| **隣接領域** | [../api-platform/00-index.md](../api-platform/00-index.md) — API プラットフォーム標準（重複領域）|
| **外部** | [AWS CDK](https://aws.amazon.com/cdk/) / [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs) |

### 7.3 分析者（探索的クエリ / SageMaker / ML 前処理）

**概要**: データアナリスト・データサイエンティスト向け標準ルート。Athena 探索ワークグループ、SageMaker Studio、コスト統制、機密データ取り扱い。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/06-personas.md §FR-6.3 分析者](proposal/fr/06-personas.md) |
| **外部** | [Amazon SageMaker Studio](https://aws.amazon.com/sagemaker/studio/) / [Athena Notebooks](https://docs.aws.amazon.com/athena/latest/ug/notebooks-spark.html) |

### 7.4 監査者（アクセスログ閲覧 / PII 棚卸し / 権限レビュー）

**概要**: 内部監査・コンプラ向け標準ルート。CloudTrail Lake / Athena、Macie レポート、IAM Access Analyzer、第三者性の担保。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/06-personas.md §FR-6.4 監査者](proposal/fr/06-personas.md) |
| **外部** | [CloudTrail Lake](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-lake.html) / [IAM Access Analyzer](https://aws.amazon.com/iam/access-analyzer/) |

---

## 8. 非機能要件（§NFR-1〜9）（9 項目）

### 8.1 可用性（保存先別 SLA + 計画停止）

**概要**: 保存先別目標 SLA（S3 99.9% / Aurora 99.99% / Redshift 99.9% / OpenSearch 99.9% 等）、メンテ窓、ローリング適用。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/nfr/01-availability.md](proposal/nfr/01-availability.md) |
| **外部** | [S3 SLA](https://aws.amazon.com/s3/sla/) / [Aurora SLA](https://aws.amazon.com/rds/aurora/sla/) / [Redshift SLA](https://aws.amazon.com/redshift/sla/) |

### 8.2 性能（クエリレイテンシ + スループット）

**概要**: 利用形態別レイテンシ目標（BI 3 秒 / 探索 30 秒 / API 200 ms 等）、スループット目標、コールドスタート対策。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/nfr/02-performance.md](proposal/nfr/02-performance.md) |
| **外部** | [Athena Performance Tuning](https://docs.aws.amazon.com/athena/latest/ug/performance-tuning.html) / [QuickSight SPICE Performance](https://docs.aws.amazon.com/quicksight/latest/user/spice.html) |

### 8.3 拡張性（データ量・利用者数の増加対応）

**概要**: データ量増加（年率 X%）、同時利用者数、Auto Scaling 設計、リージョン拡張。

| 種別 | 参考資料 |
|---|---|
| **計画上** | proposal/nfr/03-scalability.md（未作成）|

### 8.4 セキュリティ（暗号化・アクセス制御・監査の NFR 側）

**概要**: §FR-5 ガバナンスの NFR 側補強。NIST CSF / CIS Controls 等の業界フレームへの対応。

| 種別 | 参考資料 |
|---|---|
| **計画上** | proposal/nfr/04-security.md（未作成）|
| **proposal** | [proposal/fr/05-governance.md](proposal/fr/05-governance.md)（FR 側）|
| **外部** | [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework) / [CIS Controls v8](https://www.cisecurity.org/controls) |

### 8.5 DR（バックアップ + クロスリージョン）

**概要**: RTO / RPO 目標、バックアップ戦略、クロスリージョンレプリケーション、Glacier 復旧 SLA。

| 種別 | 参考資料 |
|---|---|
| **計画上** | proposal/nfr/05-dr.md（未作成）|
| **外部** | [S3 Cross-Region Replication](https://docs.aws.amazon.com/AmazonS3/latest/userguide/replication.html) / [Aurora Global Database](https://aws.amazon.com/rds/aurora/global-database/) |

### 8.6 運用（監視 / データ品質 / 体制）

**概要**: CloudWatch 監視標準、データ品質監視、運用体制・SLA、コスト監視。

| 種別 | 参考資料 |
|---|---|
| **計画上** | proposal/nfr/06-operations.md（未作成）|
| **外部** | [CloudWatch Best Practices](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch-best-practices.html) / [Glue Data Quality](https://aws.amazon.com/glue/features/data-quality/) |

### 8.7 コンプライアンス（個人情報保護法 / 業界規制 / 監査）

**概要**: 適用法令・規制、業界認定（SOC 2 / ISO 27001 等）、監査ログ保管期間、GDPR 対応（忘れられる権利）。

| 種別 | 参考資料 |
|---|---|
| **計画上** | proposal/nfr/07-compliance.md（未作成）|
| **外部** | [個人情報保護法 (APPI)](https://www.ppc.go.jp/) / [GDPR](https://gdpr-info.eu/) / [SOC 2](https://www.aicpa-cima.com/topic/audit-assurance/audit-and-assurance-greater-than-soc-2) / [ISO/IEC 27001](https://www.iso.org/standard/27001) |

### 8.8 コスト（保存・転送・分析の各コスト統制）

**概要**: コスト統制の標準（Cost Explorer / Budgets / Athena per-query 上限）、ストレージクラス最適化、3 年 TCO 見積もり。

| 種別 | 参考資料 |
|---|---|
| **計画上** | proposal/nfr/08-cost.md（未作成）|
| **計画上** | cost-estimation.md（SSOT §2 Phase 4、未作成）|
| **外部** | [AWS Cost Explorer](https://aws.amazon.com/aws-cost-management/aws-cost-explorer/) / [AWS Budgets](https://aws.amazon.com/aws-cost-management/aws-budgets/) |

### 8.9 データライフサイクル（保管期間 / アーカイブ / 削除）

**概要**: データ区分別保管期間、Glacier アーカイブ戦略、GDPR 忘れられる権利対応、既存データ移行。

| 種別 | 参考資料 |
|---|---|
| **計画上** | proposal/nfr/09-lifecycle.md（未作成）|
| **外部** | [S3 Lifecycle](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html) / [S3 Glacier](https://aws.amazon.com/s3/storage-classes/glacier/) / [GDPR Article 17 Right to Erasure](https://gdpr-info.eu/art-17-gdpr/) |

---

## 9. 元 9 観点 ↔ 新構造のマッピング表

> **目的**: 当初依頼された 9 観点が新構造のどこに配置されたか、**抜けがないかの確認**用。

| # | 元 9 観点（依頼時）| 新項目（PowerPoint）| 新項目（proposal/）|
|:-:|---|---|---|
| 1 | データプラットフォームとは何か、何を実現するのか | §1.1〜1.3 全体方針・基本方針・アーキ方針 | proposal/00-index.md §0.1〜0.2、各 §X.0 |
| 2 | 対象のデータ | §2 対象データ・分類（3 項目）| [proposal/fr/01-data-catalog.md](proposal/fr/01-data-catalog.md) §FR-1 |
| 3 | データの保存場所 | §3 保存先標準（5 項目）| [proposal/fr/02-storage.md](proposal/fr/02-storage.md) §FR-2 |
| 4 | データ連携の方法 | §4 データ連携（4 項目）| [proposal/fr/03-pipeline.md](proposal/fr/03-pipeline.md) §FR-3 |
| 5 | データの閲覧方法 | §5 閲覧・活用（4 項目）| [proposal/fr/04-consumption.md](proposal/fr/04-consumption.md) §FR-4 |
| 6 | データのガバナンス | §6 ガバナンス（4 項目）| [proposal/fr/05-governance.md](proposal/fr/05-governance.md) §FR-5 |
| 7 | 構成例 | §1.4 構成概要図 | proposal/common/01-architecture.md §C-1（未作成）|
| 8 | 利用者とユースケースごとの実装例 | §7 ペルソナ別実装（4 項目）| [proposal/fr/06-personas.md](proposal/fr/06-personas.md) §FR-6 |
| 9 | 運用主体と責任分解 | §6.4 監査ログ + §8.6 運用（一部）| proposal/common/03-ownership-raci.md §C-3（未作成）|

### 新規追加項目（元 9 観点になかった要素）

| 新項目 | 不足理由 | 該当 § |
|---|---|---|
| **§1.5 AWS サービス選定** | サービス選定軸（Athena vs Redshift 等）の独立論点 | §C-2（未作成）|
| **§1.6 移行方針・標準展開計画** | 既存データ移行・標準展開のプロセス | §NFR-9.4 + §C-5（未作成）|
| **§8 非機能要件（9 項目全体）** | 元 9 観点には非機能が無いが、業界標準（IPA）に従い必須 | §NFR-1〜9（一部未作成）|
| **§1.2 基本方針 4 軸** | 認証側との一貫性、判断軸の明示 | proposal/00-index.md §0.2 |

---

## 10. PowerPoint スライド構成テンプレ

各大項目を以下の **基本テンプレ 3-5 スライド** で構成：

| スライド種別 | 内容 | 想定枚数 |
|---|---|---|
| **概要スライド** | 何を決めるか / なぜ重要か / 関連項目 | 1 枚 |
| **選択肢提示** | A/B/C 案の比較表（業界標準 + 本標準推奨）| 1-2 枚 |
| **業界標準・参考事例** | AWS Well-Architected / Medallion 等の引用 | 1 枚（必要時）|
| **本標準での推奨** | ベースライン + 理由 + 例外条件 | 1 枚 |
| **ヒアリング質問** | 各アプリ・データオーナーに確認する項目リスト | 1 枚 |

### スライド作成のコツ

| Tips | 内容 |
|---|---|
| **§の対応を明示** | 各スライド左下に「§FR-2.1」「§NFR-1.1」等の対応 ID を小さく表示 |
| **Mermaid 図のスクショ** | proposal 内の Mermaid 図を PNG/SVG で書き出して貼る |
| **本標準の推奨をハイライト** | ⭐ マークで「本標準推奨」を明示 |
| **AWS サービスロゴ活用** | S3 / Glue / Athena / Redshift 等のロゴで視覚的に分かりやすく |
| **比較表は最大 5 列まで** | スライドで読める列数は 4-5 が限界、それ以上は分割 |
| **マトリクスを多用** | データ × 機密度 × 用途等の 2-3 軸マトリクスは理解しやすい |

---

## 11. ヒアリング会議への適用

### 3 回ヒアリング計画との対応（想定）

> 注: ヒアリング計画は SSOT §2 Phase 2 で `hearing-strategy.md` として正式化予定。下表は想定値。

| 章 | ヒアリング回 | 含まれる項目 | スライド範囲 |
|---|---|---|---|
| **章 1 全体方針・前提（6）** | **M1** | 1.1〜1.6 全て | 約 24 枚 |
| **章 2 対象データ・分類（3）** | **M1** | 2.1〜2.3 全て | 約 12 枚 |
| **章 3 保存先標準（5）** | **M2** | 3.1〜3.5 全て | 約 20 枚 |
| **章 4 データ連携（4）** | **M2** | 4.1〜4.4 全て | 約 16 枚 |
| **章 5 閲覧・活用（4）** | **M2** | 5.1〜5.4 全て | 約 16 枚 |
| **章 6 ガバナンス（4）** | **M2 + M3** | M2: 6.1, 6.2 / M3: 6.3, 6.4 | 約 16 枚 |
| **章 7 ペルソナ別実装（4）** | **M3** | 7.1〜7.4 全て | 約 16 枚 |
| **章 8 非機能要件（9）** | **M3** | 8.1〜8.9 全て | 約 36 枚 |

### 想定スケジュール

| 回 | スライド範囲 | 時間 | 主な対象者 |
|---|---|---|---|
| **M1 第 1 回** | 章 1（24 枚）+ 章 2（12 枚）= **36 枚** | 2 時間 | プラットフォーム標準化推進者 + データオーナー候補 + アプリ PO |
| **M2 第 2 回** | 章 3（20 枚）+ 章 4（16 枚）+ 章 5（16 枚）+ 章 6 前半（8 枚）= **60 枚** | 3 時間 | アプリ開発・運用担当者 + データアーキテクト |
| **M3 第 3 回** | 章 6 後半（8 枚）+ 章 7（16 枚）+ 章 8（36 枚）= **60 枚** | 3 時間 | インフラ / SRE / セキュリティ / 監査 + 意思決定者 |

→ **合計 8 時間**（3 回会議）で全 ~156 枚をカバー。M2/M3 が重いため、章 8 非機能（特に 8.4〜8.9 未作成分）を**事前読み合わせ + Q&A 中心**にすれば短縮可能。

---

## 12. 関連ドキュメント

### 一次資料（本標準の SSOT）

- [data-platform-document-structure.md](data-platform-document-structure.md) — 領域全体 SSOT
- [proposal/00-index.md](proposal/00-index.md) — 標準ベースライン提示版 SSOT
- [internal-evaluation.md](internal-evaluation.md) — 抽出方針の裏どり資料

### proposal 章（既作成分）

- [proposal/fr/00-index.md](proposal/fr/00-index.md) — FR 章一覧
- [proposal/fr/01-data-catalog.md](proposal/fr/01-data-catalog.md) — §FR-1 対象データ
- [proposal/fr/02-storage.md](proposal/fr/02-storage.md) — §FR-2 保存先標準
- [proposal/fr/03-pipeline.md](proposal/fr/03-pipeline.md) — §FR-3 データ連携
- [proposal/fr/04-consumption.md](proposal/fr/04-consumption.md) — §FR-4 閲覧・活用
- [proposal/fr/05-governance.md](proposal/fr/05-governance.md) — §FR-5 ガバナンス
- [proposal/fr/06-personas.md](proposal/fr/06-personas.md) — §FR-6 ペルソナ別実装
- [proposal/nfr/00-index.md](proposal/nfr/00-index.md) — NFR 索引 + IPA マッピング
- [proposal/nfr/01-availability.md](proposal/nfr/01-availability.md) — §NFR-1 可用性
- [proposal/nfr/02-performance.md](proposal/nfr/02-performance.md) — §NFR-2 性能

### proposal 章（未作成、計画上）

- proposal/nfr/03-09 — §NFR-3〜9（拡張性 / セキュリティ / DR / 運用 / コンプラ / コスト / ライフサイクル）
- proposal/common/01-05 — §C-1〜5（参照アーキ / サービス選定 / RACI / TBD / スケジュール）

### ヒアリング関連（計画上）

- hearing-strategy.md（SSOT §2 Phase 2、未作成）
- hearing-checklist.md（未作成）
- hearing-phase-a/b/c/d.md（未作成）

### 標準仕様書関連（計画上）

- data-platform-spec.md（SSOT §2 Phase 3、未作成）
- functional-requirements.md（未作成）
- non-functional-requirements.md（未作成）
- service-selection-decision.md（未作成）

### 隣接領域

- [../requirements/](../requirements/00-index.md) — 共有認証基盤
- [../requirements/powerpoint-outline-and-references.md](../requirements/powerpoint-outline-and-references.md) — 認証側 PowerPoint 戦略シート（本ドキュメントの雛形元）
- [../api-platform/](../api-platform/00-index.md) — API プラットフォーム標準

---

## 13. 改訂履歴

| 日付 | 内容 |
|---|---|
| 2026-05-27 | 初版作成。元 9 観点 → 8 章 39 項目に再編成。参考資料マトリクス + スライド構成案 + 3 回ヒアリング対応（想定）+ ナラティブ差分整理。**雛形元**: 認証側 [powerpoint-outline-and-references.md](../requirements/powerpoint-outline-and-references.md)。未作成 proposal 章（NFR/common）は「計画上のリンク」として記載 |
