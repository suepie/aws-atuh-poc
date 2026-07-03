# 【補足資料】Glue と運用の具体作業・必要スキル

> **位置付け**: データプラットフォーム構築時に、**Glue を中心とした具体的な作業内容**と、**運用全般で必要なスキルセット**を整理した資料。ヒアリング（[hearing-slides-organization.md](hearing-slides-organization.md) スライド 8, 9）で「中央分析チーム / 各アプリチームの必要人員・スキル」を判断する際の裏付け資料。
> **対象読者**: 中央分析チーム候補 / 各アプリ側データエンジニア / 採用・育成計画立案者 / 経営層
> **前提構成**: A案 分散型（Federated Data Mesh、Producer 側で ETL）を想定。B案（中央集約）の場合は §5 参照。
> **作成日**: 2026-07-03

---

## §0 全体像

### 0.1 データプラットフォーム運用の 8 大カテゴリー

データプラットフォーム運用は大きく **8 つのカテゴリー**に分かれます:

| # | カテゴリー | 主な内容 | 主担当（A案想定）|
|---|---|---|---|
| ① | **Glue Data Catalog 管理** | テーブル定義・スキーマ・パーティション管理 | Producer + 中央 |
| ② | **Glue ETL 開発・運用** | データ変換ジョブの実装・監視 | **Producer**（A案）/ 中央（B案）|
| ③ | **Lake Formation 認可管理** | LF-Tag、Data Filter、Cross-account Grants | 中央 |
| ④ | **Athena / QuickSight 運用** | クエリ、ダッシュボード、SPICE 管理 | 中央 BI チーム |
| ⑤ | **パイプライン Orchestration** | Step Functions、EventBridge、依存関係管理 | Producer + 中央 |
| ⑥ | **監視・アラート** | CloudWatch、失敗検知、パフォーマンス | Producer + 中央 |
| ⑦ | **コスト管理** | Budget、Cost Explorer、リソース最適化 | 中央 |
| ⑧ | **セキュリティ・ガバナンス** | IAM、KMS、CloudTrail、削除対応 | 中央 |

### 0.2 頻度別 作業マップ

| 頻度 | 主な作業 |
|---|---|
| **日次** | ETL 失敗検知・再実行、ダッシュボード鮮度確認、コスト監視 |
| **週次** | ダッシュボード改善、新規リクエスト対応、失敗傾向分析 |
| **月次** | コスト最適化、Refresh スケジュール見直し、権限棚卸し |
| **四半期** | Dataset サイズ最適化、Reader Capacity 見直し、SLA レビュー |
| **年次** | 全体アーキテクチャレビュー、Phase 移行判断、スキル戦略見直し |

### 0.3 想定人月工数（A案 分散型 = Producer で ETL、10 アプリ規模、Phase 1）

| 役割 | Phase 1 人員 | 主な工数配分 |
|---|:---:|---|
| **各 Producer のデータスチュワード**（役割 2）| **1 名/アプリ × 10 = 10 名工数**（1 名は 0.3-0.5 人月/月）| ETL 開発 30% / 運用 30% / スキーマ管理 20% / 対応 20% |
| **カタログ管理者**（役割 3）| **1-2 名**（0.5-1 人月/月）| Lake Formation 30% / IAM 25% / KMS 20% / 障害対応 25% |
| **中央 BI Author**（役割 4）| **2 名**（1-1.5 人月/月）| ダッシュ開発 40% / SPICE 運用 25% / クエリ最適化 20% / データ品質 15% |

### 0.4 【重要】アプリと中央の連携モデル（Data Contract パターン）

**よくある誤解**: 「中央がアプリに『こういうデータを出して』と要件を出すのか、それともアプリがとりあえずデータを出して中央でよしなに加工するのか、どちらか」

→ **どちらの極端も適切ではありません**。実際は **「Data Contract」ベースのハイブリッドモデル**が推奨です。

#### 0.4.1 3 パターンの比較

| パターン | 内容 | 課題 |
|---|---|---|
| ① **App-driven**（アプリが中央の要望通り ETL）| 中央が要件を出す → アプリが専用テーブルを作る | アプリが**「中央のためのデータ雑用」化**、Domain Ownership 崩壊 |
| ② **Central-driven**（中央が全て加工）| アプリは Catalog に生データを出すだけ → 中央が全加工 | 中央が **10 アプリ分の業務ドメイン知識**を要求される、中央ボトルネック化 |
| ③ **Hybrid（Data Contract）**⭐ 推奨 | **アプリが「業務単位の整形済みデータ」提供** → **中央がその上で横断集計** | 業界標準（Data Mesh の Data Product 概念）|

#### 0.4.2 責務分担（Hybrid モデル）

**アプリ側の責務**（Producer）: 「Data Product」を提供 - **用途に依存しない業務単位の整形済みデータ**を作って公開

| 作業 | 内容 | 用途依存性 |
|---|---|:---:|
| raw → curated 変換 | 生データを整える | ❌ 依存しない |
| PII マスキング（社員番号ハッシュ化等）| 個人情報保護 | ❌ どんな用途でも必要 |
| `tenant_id` 強制付与 | マルチテナント分離 | ❌ どんな用途でも必要 |
| 重複排除 | データ品質担保 | ❌ どんな用途でも必要 |
| Parquet + パーティション | 標準フォーマット | ❌ どんな用途でも必要 |
| **業務単位のスキーマ提供**（例: `expenses` テーブル）| ドメインの本質を保持 | ❌ 業務そのもの |
| Data Quality チェック | 品質保証 | ❌ どんな用途でも必要 |
| **Glue Catalog にテーブル公開**（Contract 明示）| 中央から発見可能に | ❌ 公開が責任 |

**中央側の責務**（Consumer）: 「横断分析・ダッシュボード」を作る - **アプリの curated テーブルを as-is で使い**、その上で用途駆動の集計を組む

| 作業 | 内容 | 用途依存性 |
|---|---|:---:|
| **横断 CTAS 集計**（例: 全 SaaS 合算売上）| 複数アプリの curated を JOIN して集計 | ⭕ 用途駆動 |
| ダッシュボード用の事前集計 | 特定ダッシュ用の派生テーブル | ⭕ 用途駆動 |
| KPI 定義の実装 | 全社 KPI ロジックを反映 | ⭕ 用途駆動 |
| ML 特徴量生成 | ML 用の特徴量テーブル | ⭕ 用途駆動 |
| アプリ側 curated の直接読み込み（Federation 経由）| データを動かさず横断参照 | ❌ 変換なし |

#### 0.4.3 具体例で見る Hybrid モデル

**例 1: 中央が「顧客テナント別 月次売上」を見たい**

```
[アプリ側 curated] expenses テーブル
├─ 列: tenant_id, expense_id, amount, submitted_at, status, ...
└─ アプリが日次で更新、業務ロジック（承認済のみ集計等）を反映済

[中央側 analytics] 中央が CTAS で構築
CREATE TABLE central_analytics.monthly_tenant_revenue AS
SELECT
    tenant_id,
    DATE_TRUNC('month', submitted_at) AS month,
    SUM(amount) AS total_revenue,
    COUNT(*) AS transaction_count
FROM expense_app_curated.expenses
WHERE status = '承認済'
GROUP BY tenant_id, DATE_TRUNC('month', submitted_at);
```

→ アプリは curated を提供、**中央が用途特化の集計を組む**（アプリは何もしない）

**例 2: 中央が「全 SaaS 合算の顧客活性度スコア」を見たい**（横断集計）

```
[アプリ側 curated] 各アプリが提供
├─ expense_app_curated.expenses（経費精算）
├─ attendance_app_curated.time_records（勤怠）
└─ crm_app_curated.customer_activities（CRM）

[中央側 analytics] 中央が横断集計
CREATE TABLE central_analytics.customer_health_score AS
SELECT
    e.tenant_id,
    COUNT(DISTINCT e.submitter_id) AS expense_active_users,
    COUNT(DISTINCT t.employee_id) AS attendance_active_users,
    COUNT(DISTINCT c.contact_id) AS crm_active_users,
    (COUNT(DISTINCT e.submitter_id) + COUNT(DISTINCT t.employee_id) + COUNT(DISTINCT c.contact_id)) / 3 AS avg_activity
FROM expense_app_curated.expenses e
FULL OUTER JOIN attendance_app_curated.time_records t ON e.tenant_id = t.tenant_id
FULL OUTER JOIN crm_app_curated.customer_activities c ON e.tenant_id = c.tenant_id
GROUP BY e.tenant_id;
```

→ **横断は中央でしかできない**、各アプリは自分の curated を提供するのみ

**例 3: 業務ロジックがアプリでないとわからない場合（Data Contract の実践）**

```
中央: 「経費精算の 月次 平均処理時間 を見たい」
    ↓
アプリ側と会話:
- 中央: 「submitted_at と approved_at の差の平均が欲しい」
- アプリ: 「実は差戻し（rejected）があると再申請されて時間が伸びるので、
        『初回申請から最終承認まで』の定義が業務的には正しい」
- 中央: 「なるほど、その定義でいきましょう」
    ↓
Data Contract 合意:
- テーブル名: expense_app_curated.monthly_processing_time
- 定義: 初回申請から最終承認までの平均時間
- 粒度: tenant_id x month
- 更新: 日次
    ↓
アプリが実装、中央が消費
```

→ **業務定義が絡む集計は Data Contract で合意してからアプリが提供**

#### 0.4.4 責務分担の判断フロー

新しい集計テーブルが必要になった時、以下のフローで判断:

```
中央が新しい集計テーブルを欲しい時
    │
    ├─ 業務ロジックの深い理解が必要?
    │   ├─ YES → アプリ側で作る（Data Contract で合意）
    │   └─ NO  → 中央側で作る
    │
    ├─ 複数アプリの JOIN が必要?
    │   ├─ YES → 中央側で作る（横断は中央の役割）
    │   └─ NO  → どちらでも可（下記で判断）
    │
    ├─ 他の中央分析でも使う共通指標?
    │   ├─ YES → アプリ側 or 中央の共通集計層で作る（再利用性）
    │   └─ NO  → 中央側で用途特化で作る
    │
    └─ 業務データの構造そのもの?（例: expenses テーブル）
        └─ YES → アプリ側で作る（アプリの curated の本体）
```

#### 0.4.5 Data Contract の要素（アプリ ⇔ 中央の合意事項）

Data Contract で合意すべき 7 項目:

| # | 項目 | 例 |
|---|---|---|
| 1 | **テーブル名 / 場所** | `expense_app_curated.expenses` / `s3://acme-expense-curated-prd/expenses/` |
| 2 | **スキーマ**（列名・型）| `expense_id STRING, tenant_id STRING, amount BIGINT, ...` |
| 3 | **業務定義**（各列の意味） | `amount: 承認済み経費申請の金額（税込、円）` |
| 4 | **粒度**（1 行が何を表すか）| 「1 行 = 1 経費申請」 |
| 5 | **更新頻度・鮮度 SLA** | 日次更新、遅延最大 6 時間 |
| 6 | **データ品質**（完全性、正確性、一貫性）| NULL 率 < 1%、tenant_id 必須 |
| 7 | **変更管理プロセス** | Breaking change は 2 週間前予告、Slack で通知 |

**運用のコツ**:
- Data Contract は **Confluence / GitLab / GitHub** 等で明文化
- 変更は **Pull Request** で管理し、中央側の Review 必須
- **半期に 1 度の棚卸し**（未使用テーブルの削除、変更の反映）

#### 0.4.6 アンチパターン（避けるべき運用）

| # | アンチパターン | 何が起きるか | 回避策 |
|---|---|---|---|
| ① | アプリが raw だけ提供、curated も中央でやる | 中央が全アプリの業務理解を要求される、中央崩壊 | **アプリが curated まで責任持つ** |
| ② | 中央が業務定義を勝手に決めて集計 | 業務定義違反で誤った KPI が経営に出る | **業務ロジック絡みは Data Contract で合意** |
| ③ | アプリが「中央の欲しい形」で毎回 ETL を書き直す | アプリチームが「中央の下請け化」、Domain Ownership 崩壊 | **中央の要望は curated への基本責務外は Contract 経由に限定** |
| ④ | 中央がアプリの curated を書き換える | データ整合性崩壊、誰の責任か曖昧 | **中央は curated を Read-only で扱う、派生は自分の analytics に** |
| ⑤ | Contract なしで場当たり的に集計 | 定義乱立、集計ミス、後で辻褄が合わない | **定期的な Data Contract 棚卸し** |

#### 0.4.7 実運用でよくあるやりとりのパターン

**日常的な状況別、期待される会話**:

| 状況 | 中央側の言動 | アプリ側の言動 |
|---|---|---|
| 中央が新しいダッシュを作りたい（curated で足りる）| 「◯◯テーブルを CTAS で集計して analytics に置きます」| 特に関与不要（curated が使われる） |
| 中央が新しい KPI を定義したい（業務ロジック絡み）| 「◯◯という KPI を計算したい、定義は X で合っていますか?」| 「業務定義は Y が正しい、これで合意すれば curated に追加します」|
| アプリでスキーマ変更した | 「Slack で 2 週間前に予告します、影響ダッシュを教えて」| 「◯◯ダッシュに影響あり、変更に合わせて修正します」|
| アプリで新しいテーブルを追加した | 「Catalog を見て発見、活用します」| 「Slack で新テーブル追加を告知」|
| 中央のダッシュで誤った数字が出た | 「原因調査、Contract 違反か curated バグか切り分け」| バグなら修正、そうでなければ Contract 確認 |
| アプリが業務変更で列削除したい | 「使ってるダッシュがあるか確認したい」| 「Deprecation 予告→半年後削除の流れで進める」|

→ **「気軽に相談・合意する文化」が重要**。厳格な承認プロセスより、**日常的な軽い会話**の積み重ねが Hybrid モデルを機能させます。

---

## §1 Glue Data Catalog 管理（カテゴリー ①）

### 1.1 具体的な作業内容

| 作業 | 頻度 | 1 回あたり工数 | 主担当 |
|---|---|---|---|
| **テーブル定義の新規登録**（DDL 作成、Partition Projection 設定）| 新規テーブル追加時（月 2-5 回）| 30 分-2 時間/テーブル | Producer |
| **スキーマ変更対応**（列追加、型変更、名前変更）| 月 1-3 回 | 30 分-4 時間/変更 | Producer |
| **パーティション管理**（Manual vs Partition Projection、追加、削除）| 週次 or 月次 | 15 分-1 時間 | Producer |
| **LF-Tag 付与**（domain, classification, pii, tenant_isolation）| 新規テーブル時 + 定期棚卸し | 5-15 分/テーブル | Producer + カタログ管理者 |
| **カタログ検索性の確保**（説明文、カラム コメント、ドキュメント）| 継続的 | 15-30 分/テーブル | Producer |
| **Catalog の棚卸し**（未使用テーブル・DB の削除）| 四半期 | 半日-1 日 | カタログ管理者 |
| **Federation 設定**（Producer → 中央 Catalog）| 新規 Producer 追加時 | 2-4 時間 | カタログ管理者 |
| **KMS 鍵ローテーション**（Catalog 暗号化）| 年次 | 半日 | カタログ管理者 |

### 1.2 具体作業のイメージ（サンプル）

**新規テーブル登録の DDL 例**（Producer で実施）:

```sql
-- 経費精算 SaaS の analytics 層に新テーブル追加
CREATE EXTERNAL TABLE expense_app_analytics.reimbursement_summary (
    tenant_id STRING,
    period_year INT,
    period_month INT,
    total_amount BIGINT,
    submission_count INT,
    approval_rate DOUBLE
)
PARTITIONED BY (year INT, month INT)
STORED AS PARQUET
LOCATION 's3://acme-expense-analytics-prd/reimbursement_summary/'
TBLPROPERTIES (
    'projection.enabled' = 'true',
    'projection.year.type' = 'integer',
    'projection.year.range' = '2026,2030',
    'projection.month.type' = 'integer',
    'projection.month.range' = '1,12',
    'storage.location.template' = 's3://acme-expense-analytics-prd/reimbursement_summary/year=${year}/month=${month}/'
);

-- LF-Tag 付与
-- (Lake Formation UI or aws lakeformation add-lf-tags-to-resource で実施)
```

### 1.3 必要スキル

| スキル | レベル | 用途 |
|---|:---:|---|
| **SQL DDL** | 中級 | CREATE EXTERNAL TABLE、ALTER 等 |
| **AWS Glue Data Catalog** | 中級 | Catalog 構造、API 理解 |
| **Partition Projection** | 中級 | パーティション設計、TBLPROPERTIES |
| **Lake Formation** | 中級 | LF-Tag、Data Filter |
| **Data Modeling** | 中級-上級 | スキーマ設計、正規化・非正規化判断 |
| **業務ドメイン知識** | 上級 | 各テーブルの業務意味理解 |

---

## §2 Glue ETL 開発・運用（カテゴリー ②）

### 2.1 具体的な作業内容

| 作業 | 頻度 | 1 回あたり工数 | 主担当 |
|---|---|---|---|
| **新規 ETL ジョブの設計・実装**（raw → curated 変換等）| 新規テーブル追加時 | **1-5 日/ジョブ** | Producer |
| **既存 ETL ジョブの修正**（スキーマ変更、業務変更対応）| 月 5-10 回 | 2 時間-1 日/修正 | Producer |
| **PySpark スクリプト作成**（Spark SQL、DataFrame API 等）| 新規 ETL 開発時 | 1-3 日/ジョブ | Producer |
| **Job Config 設計**（DPU、タイムアウト、リトライ、Bookmark 等）| 新規ジョブ設計時 | 1-2 時間/ジョブ | Producer |
| **依存関係の設計**（Glue Workflow、Step Functions）| 月 2-3 回 | 半日-1 日 | Producer |
| **失敗時の再実行**（冪等性の確認、影響範囲判断）| 週 1-3 回 | 30 分-2 時間 | Producer |
| **パフォーマンスチューニング**（Skew 対応、Shuffle 最適化、DPU 数調整）| 月次 or 遅い時 | 半日-2 日 | Producer + 中央 |
| **コスト最適化**（Flex vs Standard、DPU 削減、ジョブ統合）| 四半期 | 1-2 日 | Producer + 中央 |
| **Glue Data Quality ルール定義**（NULL 率、Uniqueness、Freshness）| 新規テーブル + 追加 | 半日-1 日/ルール | Producer |

### 2.2 具体作業のイメージ（サンプル）

**Glue ETL ジョブのサンプル**（Producer 側で作成、raw → curated 変換）:

```python
# Glue ETL Job (PySpark) - サンプル
# 経費精算 SaaS: raw → curated 変換
# - PII マスキング（社員番号のハッシュ化）
# - tenant_id 強制付与
# - 重複排除

import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import sha2, col, current_timestamp

args = getResolvedOptions(sys.argv, ['JOB_NAME'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# raw 層から読込
raw_df = glueContext.create_dynamic_frame.from_catalog(
    database="expense_app_raw",
    table_name="expenses"
).toDF()

# クレンジング処理
curated_df = (raw_df
    # PII マスキング（社員番号を SHA-256 でハッシュ化）
    .withColumn("submitter_id_hash", sha2(col("submitter_id"), 256))
    .drop("submitter_id")
    # tenant_id 必須チェック（NULL は除外）
    .filter(col("tenant_id").isNotNull())
    # 重複排除（expense_id で dedup）
    .dropDuplicates(["expense_id"])
    # メタデータ追加
    .withColumn("processed_at", current_timestamp())
)

# curated 層に書出（Parquet + Snappy、tenant_id/日付でパーティション）
curated_df.write \
    .mode("overwrite") \
    .partitionBy("tenant_id", "year", "month", "day") \
    .format("parquet") \
    .option("compression", "snappy") \
    .save("s3://acme-expense-curated-prd/expenses/")

job.commit()
```

### 2.3 想定されるトラブルとその対応

| トラブル | 対応 | 必要スキル |
|---|---|---|
| ジョブが OOM で失敗 | DPU 増、Skew 対応、パーティション調整 | Spark tuning |
| ジョブが遅い | Predicate Pushdown、Broadcast Join、Cache | Spark performance |
| ジョブが冪等でない（重複データ）| Bookmark 活用、Idempotency 設計 | Data Engineering |
| スキーマ変更で失敗 | Schema Evolution 対応、上流通知 | Data Contract |
| コストが高い | Flex 化、実行頻度削減、SQL 最適化 | Cost Engineering |

### 2.4 必要スキル

| スキル | レベル | 用途 |
|---|:---:|---|
| **Python** | 中級 | Glue ETL Job のスクリプト |
| **PySpark**（Spark SQL、DataFrame API）| 中級-上級 | 大規模データ変換 |
| **Spark 内部構造理解**（Executor、Shuffle、Partition）| 上級 | パフォーマンス チューニング |
| **AWS Glue**（Job、Bookmark、Workflow、Flex）| 中級-上級 | Glue 特有機能の理解 |
| **SQL**（複雑クエリ、CTAS、Window 関数）| 中級-上級 | データ変換ロジック |
| **Data Engineering Patterns**（Medallion、SCD、CDC 等）| 上級 | 業務データパイプライン設計 |
| **業務ドメイン知識** | 上級 | どういう変換が業務的に妥当か判断 |
| **Git、CI/CD** | 中級 | Job コード管理、デプロイ |

---

## §3 Lake Formation 認可管理（カテゴリー ③）

### 3.1 具体的な作業内容

| 作業 | 頻度 | 1 回あたり工数 | 主担当 |
|---|---|---|---|
| **LF-Tag 体系の設計**（domain、classification、pii 等）| Phase 0 一回 + 定期見直し | 数日 | カタログ管理者 |
| **LF-Tag の付与**（Database、Table、Column に）| 新規テーブル時 | 5-15 分 | Producer + カタログ管理者 |
| **LF-TBAC ポリシー設定**（Principal x LF-Tag Expression）| 新規 Principal 時 | 30 分-2 時間 | カタログ管理者 |
| **Data Filter 定義**（行レベル、列レベル、セルレベル）| 新規テーブル or 要件変更時 | 1 時間-半日 | カタログ管理者 |
| **Cross-account Grants**（Producer → 中央 Consumer）| 新規 Producer 追加時 | 半日-1 日 | カタログ管理者 |
| **権限の棚卸し**（Grant 一覧確認、未使用削除）| 四半期 | 半日-1 日 | カタログ管理者 |
| **監査ログレビュー**（LF Access Log）| 月次 | 1-2 時間 | カタログ管理者 + 監査 |
| **Federation 設定**（Producer Catalog を中央から参照）| 新規 Producer 時 | 半日 | カタログ管理者 |

### 3.2 必要スキル

| スキル | レベル | 用途 |
|---|:---:|---|
| **Lake Formation**（LF-Tag、TBAC、Data Filter）| 上級 | 認可設計・実装 |
| **AWS IAM**（Role、Policy、Trust、Boundary）| 中級-上級 | Principal 管理 |
| **AWS Organizations**（Cross-account）| 中級 | Multi-account 認可 |
| **セキュリティ思考**（Least Privilege、SoD）| 上級 | ガバナンス設計 |
| **監査対応**（GDPR、APPI、PCI DSS）| 中級-上級 | コンプライアンス |

---

## §4 Athena / QuickSight 運用（カテゴリー ④）

### 4.1 具体的な作業内容

| 作業 | 頻度 | 1 回あたり工数 | 主担当 |
|---|---|---|---|
| **Athena Workgroup 設計**（用途別、コスト上限、Result location）| Phase 0 + 追加時 | 半日 | 中央 BI |
| **Athena クエリ開発**（新規分析、CTAS 集計）| 週次 3-10 件 | 30 分-数時間 | 中央 BI |
| **クエリコスト最適化**（Parquet、パーティション、Result Reuse）| 月次 or 高コストクエリ発見時 | 半日-1 日 | 中央 BI |
| **QuickSight Dataset 作成**（Athena 接続、SPICE Import）| 新規ダッシュ時 | 半日-1 日 | 中央 BI |
| **QuickSight Dashboard 開発**（Visual 配置、Filter 設計、RLS）| 新規ダッシュ時 | 2-5 日 | 中央 BI |
| **SPICE Refresh 設計・監視**（Full/Incremental、スケジュール）| 新規 Dataset 時 + 継続 | 半日/Dataset | 中央 BI |
| **SPICE 失敗時対応**（原因調査、再実行）| 週 1-3 回 | 30 分-2 時間 | 中央 BI |
| **Dataset サイズ最適化**（列削減、期間限定、Incremental 化）| 四半期 | 半日-1 日/Dataset | 中央 BI |
| **QuickSight ユーザー・グループ管理** | 入退社時 | 15-30 分/回 | 中央 BI |
| **RLS/CLS Permissions Dataset 更新**（属性連動）| 権限変更時 | 30 分-2 時間 | 中央 BI |

### 4.2 必要スキル

| スキル | レベル | 用途 |
|---|:---:|---|
| **SQL**（複雑クエリ、Window、CTE、CTAS）| 上級 | Athena での分析 |
| **Athena** の詳細（Workgroup、Provisioned、Result Reuse、Federated Query）| 中級-上級 | Athena 運用 |
| **Data Modeling**（Star Schema、Dimensional Modeling）| 中級-上級 | Dataset 設計 |
| **QuickSight**（Dataset、Analysis、Dashboard、SPICE、RLS/CLS）| 中級-上級 | BI 開発 |
| **可視化設計**（Chart 選択、ダッシュボード UX）| 中級 | ダッシュ品質 |
| **業務ドメイン知識**（KPI 定義、業務プロセス）| 上級 | ビジネス価値創出 |

---

## §5 パイプライン Orchestration（カテゴリー ⑤）

### 5.1 具体的な作業内容

| 作業 | 頻度 | 1 回あたり工数 | 主担当 |
|---|---|---|---|
| **Step Functions ワークフロー設計** | 新規パイプライン時 | 1-3 日 | Producer |
| **EventBridge Scheduler 設定**（Cron、Rate、Fixed Window）| 新規ジョブ時 | 30 分-1 時間 | Producer |
| **依存関係管理**（Job A → Job B → Job C）| 新規 or 変更時 | 半日 | Producer |
| **リトライ戦略設計**（Backoff、Max Attempts、Failure Action）| 新規ジョブ時 | 30 分-1 時間 | Producer |
| **タイムアウト設計** | 新規ジョブ時 | 30 分/ジョブ | Producer |
| **依存の可視化**（DAG、ドキュメント）| 継続 | 継続 | Producer |

### 5.2 必要スキル

| スキル | レベル | 用途 |
|---|:---:|---|
| **AWS Step Functions**（ASL、Distributed Map、Callback）| 中級 | Orchestration |
| **EventBridge**（Rules、Scheduler、Bus、Target）| 中級 | Event-driven パイプライン |
| **Idempotency 設計** | 中級-上級 | 冪等性の担保 |
| **Failure Domain 設計** | 中級-上級 | 障害隔離 |
| **CDK / Terraform** | 中級 | IaC |

---

## §6 監視・アラート（カテゴリー ⑥）

### 6.1 具体的な作業内容

| 作業 | 頻度 | 1 回あたり工数 | 主担当 |
|---|---|---|---|
| **CloudWatch Dashboard 作成**（ジョブ実行時間、失敗率、コスト）| 初期 + 継続改善 | 数日-1 週間（初期）| Producer + 中央 |
| **アラーム設定**（ジョブ失敗、遅延、コスト超過）| 新規ジョブ時 | 30 分-1 時間 | Producer + 中央 |
| **通知先設定**（SNS → Slack/Teams/PagerDuty）| Phase 0 + 変更時 | 半日 | 中央 |
| **CloudWatch Logs Insights クエリ**（障害調査、傾向分析）| 週次 or 障害時 | 30 分-数時間 | Producer + 中央 |
| **ログ保管設計**（Retention、S3 Export、Athena 分析）| 初期 + 変更時 | 半日 | 中央 |
| **失敗の一次対応**（ログ確認、再実行、エスカレーション）| 週次 3-5 件 | 30 分-2 時間/件 | Producer + 中央 |
| **Post-mortem**（重大障害の振り返り）| 障害発生時 | 半日-1 日/件 | 中央 |
| **Runbook 整備**（頻出障害の手順書）| 継続 | 継続 | 中央 |

### 6.2 必要スキル

| スキル | レベル | 用途 |
|---|:---:|---|
| **CloudWatch**（Metrics、Alarms、Logs、Insights、Dashboards）| 中級 | 監視 |
| **障害分析**（ログ調査、根本原因究明）| 中級-上級 | トラブル対応 |
| **SRE / DevOps 思考**（SLO、Error Budget、Runbook）| 中級-上級 | 継続改善 |
| **Slack / Teams API** | 初級-中級 | 通知連携 |

---

## §7 コスト管理（カテゴリー ⑦）

### 7.1 具体的な作業内容

| 作業 | 頻度 | 1 回あたり工数 | 主担当 |
|---|---|---|---|
| **Cost Explorer での月次分析**（サービス別、タグ別）| 月次 | 半日 | 中央 |
| **Budget アラート設定** | Phase 0 + 変更時 | 半日 | 中央 |
| **Reserved Capacity / Savings Plans 検討**（DMS、SageMaker）| 年 1-2 回 | 数日 | 中央 |
| **リソース最適化**（未使用削除、DPU 削減、Lifecycle 調整）| 四半期 | 数日 | 中央 |
| **Cost Allocation Tag 管理**（タグ付与、レポート）| 継続 | 継続 | 中央 |
| **AWS Pricing Calculator 更新**（見積り再計算）| 半期 | 半日 | 中央 |

### 7.2 必要スキル

| スキル | レベル | 用途 |
|---|:---:|---|
| **AWS 料金体系の理解** | 中級-上級 | コスト分析 |
| **FinOps 思考**（Efficiency、Optimization、Governance）| 中級 | コスト戦略 |
| **AWS Cost Explorer / Budget** | 中級 | ツール活用 |
| **業務との対応付け**（アプリ別・チーム別コスト按分）| 中級 | Chargeback |

---

## §8 セキュリティ・ガバナンス（カテゴリー ⑧）

### 8.1 具体的な作業内容

| 作業 | 頻度 | 1 回あたり工数 | 主担当 |
|---|---|---|---|
| **IAM Role 設計・実装**（`DataLakeAdminRole` 等）| Phase 0 + 追加時 | 数日-1 週間 | カタログ管理者 |
| **Permission Boundary 設定** | Phase 0 + 見直し | 半日-1 日 | カタログ管理者 |
| **SCP 設計**（Organizations レベル）| Phase 0 | 数日 | 中央 |
| **KMS CMK 管理**（作成、ローテーション、鍵ポリシー）| 継続 + 年次ローテーション | 半日/年 | カタログ管理者 |
| **CloudTrail Data Events レビュー**（監査ログ確認）| 月次 | 半日 | カタログ管理者 + 監査 |
| **Config Rules 監視**（違反対応）| 週次 | 1-2 時間 | 中央 |
| **GDPR / APPI 削除リクエスト対応**（テナントデータ削除）| 発生時 | 半日-1 日/件 | Producer + カタログ管理者 |
| **PII 検出（Macie）レビュー** | 月次 | 半日 | カタログ管理者 |
| **セキュリティ監査対応**（社内、外部）| 年 1-2 回 | 数日-1 週間 | カタログ管理者 |

### 8.2 必要スキル

| スキル | レベル | 用途 |
|---|:---:|---|
| **AWS IAM**（詳細）| 上級 | 認可設計 |
| **AWS KMS**（Envelope Encryption、鍵ポリシー、ローテーション）| 中級-上級 | 暗号化 |
| **AWS Organizations、SCP** | 中級 | Multi-account ガバナンス |
| **CloudTrail、Config、Macie** | 中級 | 監査・検出 |
| **セキュリティ規制**（GDPR、APPI、PCI DSS）| 中級-上級 | コンプライアンス |
| **リスクマネジメント思考** | 上級 | ガバナンス設計 |

---

## §9 総合スキルセット

### 9.1 スキルレベル別まとめ

| レベル | 主な内容 | 主な取得先 |
|---|---|---|
| **基礎** | SQL、Python 基礎、Linux/Shell、AWS 基礎（S3、IAM、VPC）| AWS Cloud Practitioner、SAA、初級 SQL 本 |
| **中級** | AWS Glue、Athena、Lake Formation、CloudWatch、CDK/Terraform 基礎 | AWS SAP、Data Engineer Specialty、実務経験 |
| **上級** | Spark tuning、Data Modeling、Cost Engineering、SRE、Security Engineering | 実務経験、AWS Security Specialty、大規模プロジェクト経験 |
| **専門** | 業務ドメイン、ML Ops、Data Governance、Regulation 対応 | 業界経験、専門書、認定資格 |

### 9.2 役割別 必要スキルの深さ（推奨レベル）

| スキル / 役割 | Producer データスチュワード（役割 2）| カタログ管理者（役割 3）| 中央 BI Author（役割 4）|
|---|:---:|:---:|:---:|
| SQL | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| Python / PySpark | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| AWS Glue | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| Athena | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| Lake Formation | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| AWS IAM / KMS | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| CloudWatch | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| Step Functions | ⭐⭐⭐ | ⭐⭐ | ⭐ |
| QuickSight | ⭐ | ⭐ | ⭐⭐⭐⭐⭐ |
| Data Modeling | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| セキュリティ規制 | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| 業務ドメイン | ⭐⭐⭐⭐（自分のアプリ）| ⭐⭐ | ⭐⭐⭐⭐（全社横断）|
| コスト管理 | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| SRE / 障害対応 | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |

（⭐ = 1: 基礎知識、⭐⭐⭐⭐⭐ = 5: 専門家レベル）

### 9.3 A案 vs B案 での必要スキル対比

**A案（分散型）採用時**:
- Producer 側に **中級以上のスキル人材が各アプリで 1-2 名**必要
- 中央は **2-3 名**（カタログ管理者 + BI Author）で成立
- 各アプリチームが自律的に動く前提

**B案（中央集約型）採用時**:
- 中央に **5+ 名の強力なチーム**が必要（データエンジニア + BI Author）
- 各アプリ側は **データ供給の担当**のみ（データエンジニアリング スキル不要）
- 全アプリのドメイン知識を中央が引き取る必要（→ 業務把握が大変）

---

## §10 Phase 別の人員・スキル計画

### 10.1 Phase 1 開始時（0-6 ヶ月）

**必要人員**:

| 役割 | 人数 | 主な業務 |
|---|:---:|---|
| Producer データスチュワード（各アプリ）| 1-2 名/アプリ | ETL 開発、Catalog 登録、パーティション設計 |
| カタログ管理者（中央）| 1-2 名 | Lake Formation 初期構築、KMS 設計、IAM 設計 |
| 中央 BI Author | 2 名 | 初期ダッシュボード開発、SPICE 運用開始 |

**Phase 1 前半で確保すべきスキル**:
- SQL、Python 基礎
- Glue Data Catalog、Glue ETL Flex
- Lake Formation 基礎（LF-Tag、Grant）
- QuickSight 基礎
- AWS IAM、KMS 基礎
- CloudWatch 監視基礎

### 10.2 Phase 1 後半（6-18 ヶ月）

**追加で必要な知識・経験**:
- Spark tuning（大規模 Job 最適化）
- Athena Result Reuse、Provisioned Capacity 検討
- Cost 最適化（Flex、Reserved 等）
- Data Quality 運用
- 障害対応 Runbook 整備

### 10.3 Phase 2（1.5-3 年）

**追加で必要なスキル**:
- SageMaker（ML Ops）
- 大規模 Data Modeling
- Multi-Region 対応（DR）
- 高度な Data Governance（GDPR、APPI 詳細対応）
- 育成体制（社内 Data Engineer コミュニティ運営）

---

## §11 スキル獲得の推奨方法

### 11.1 AWS 公式リソース

| リソース | 用途 |
|---|---|
| AWS Skill Builder | 無料のオンライントレーニング、ハンズオン |
| AWS 認定資格 | Cloud Practitioner → SAA → Data Engineer Specialty → Security Specialty |
| AWS Workshops（workshops.aws）| ハンズオン形式の実習 |
| AWS Prescriptive Guidance | Data Mesh、Lake House 等のリファレンス |
| AWS Well-Architected Data Analytics Lens | 設計原則 |

### 11.2 実務経験の推奨手順

1. **Phase 0（1-2 ヶ月）**: AWS Skill Builder で基礎学習、簡単な Glue Job を書いてみる
2. **Phase 1 前半（3-6 ヶ月）**: 1 アプリの Producer 化を担当、Catalog + ETL 実装を経験
3. **Phase 1 後半（6-18 ヶ月）**: 障害対応、コスト最適化、パフォーマンス チューニングを経験
4. **Phase 2 以降**: 他アプリの Producer 化支援、社内育成担当、大規模設計判断に参画

### 11.3 参考書籍・リソース

**Data Engineering 全般**:
- 『Fundamentals of Data Engineering』（Joe Reis, Matt Housley）
- 『Designing Data-Intensive Applications』（Martin Kleppmann）

**AWS 特化**:
- 『AWS Big Data Architect Handbook』
- 『データ指向アプリケーション設計』（O'Reilly）

**Data Governance**:
- 『Data Management Body of Knowledge (DMBOK 2)』
- 『Data Mesh』（Zhamak Dehghani）

---

## §12 参考: ヒアリング時の確認項目との対応

このドキュメントの内容は、[hearing-slides-organization.md](hearing-slides-organization.md) スライド 8, 9 で確認する**体制ヒアリング**の裏付けになります。

**スライド 8: 中央分析チーム人員規模** で確認する項目:
- カタログ管理者 → §3, §8 のスキルを持つ人
- 中央 BI Author → §4 のスキルを持つ人

**スライド 9: 各アプリ側の加工能力** で確認する項目:
- Producer データスチュワード → §1, §2, §5, §6 のスキルを持つ人

**判断基準**:
- ⭕ 各アプリで §1, §2 が可能な人が 1-2 名 → A案 分散型 で成立
- ❌ 各アプリで難しい + 中央に §2, §4 の強力な人材 5+ 名 → B案 中央集約型
- ❌ どちらも難しい → **育成計画の別途検討** or **Phase 1 縮小**

---

## §13 関連ドキュメント

| ドキュメント | 参照理由 |
|---|---|
| [hearing-slides-organization.md](hearing-slides-organization.md) スライド 8, 9 | 体制ヒアリング（本資料が裏付け）|
| [account-architecture-analysis.md](account-architecture-analysis.md) §3 | 7 役割定義 |
| [account-architecture-analysis.md](account-architecture-analysis.md) §4.2 | Producer 側 ETL 詳細 |
| [architecture-alternatives-comparison.md](architecture-alternatives-comparison.md) §2.1.4 | Pattern A vs B の責務分担詳細 |
| [data-collection-standards-for-future-aggregation.md](data-collection-standards-for-future-aggregation.md) | C案 採用時に守るべき標準 |

---

## §14 改訂履歴

| 日付 | 改訂内容 |
|---|---|
| 2026-07-03 | 初版作成。Glue + 運用の 8 カテゴリー、役割別 スキル、Phase 別 人員計画 を整理 |
| 2026-07-03 | §0.4 **アプリと中央の連携モデル（Data Contract パターン）**を追加。3 パターン比較（App-driven / Central-driven / Hybrid）、責務分担、判断フロー、Data Contract の 7 要素、アンチパターン 5 種、日常運用のやりとり例 |
