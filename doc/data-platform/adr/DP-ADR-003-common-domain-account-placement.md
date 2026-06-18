# DP-ADR-003: 共通参照データの配置 — 共通ドメインアカウント新設 vs 中央同居

- **ステータス**: Accepted
- **日付**: 2026-06-18
- **関連**:
  - [../account-architecture-analysis.md §4.2.1.1](../account-architecture-analysis.md)（リソース関係図、AWS アカウント境界）
  - [../account-architecture-analysis.md §4.2.1.X](../account-architecture-analysis.md)（共通ドメインアカウントの検討経緯、A〜F 節）
  - [../account-architecture-analysis.md §5.5](../account-architecture-analysis.md)（β + Option B + 共通ドメインの組合せ）
  - [../strawman-proposal.md §1.3](../strawman-proposal.md)（採用パターン）
  - [../proposal/fr/01-data.md](../proposal/fr/01-data.md)（対象データ、共通マスタ位置付け）
  - [DP-ADR-002](DP-ADR-002-redshift-emr-not-adopted.md)（同様の Phase 別段階採用パターン）

---

## 1. Context

### 1.1 共通参照データとは何か

「**特定のアプリに所属しないが、複数アプリから参照される共通参照データ**」の存在を、本標準の検討の中で識別した。典型例:

| データ | 例 |
|---|---|
| **顧客マスタ** | 顧客企業 ID / 名称 / 業種 / 契約プラン / 解約日 |
| **組織マスタ** | 顧客企業内の部署階層 / 従業員ロール |
| **標準勘定科目マスタ** | 経費精算 SaaS の費目 / 会計連携用コード |
| **国・地域コード / 通貨マスタ** | ISO 3166 / ISO 4217 |
| **共通分析ディメンション** | 業種分類 / 企業規模区分 / 商圏定義 |

これらは「経費精算 SaaS / CRM / ERP / 営業支援 SaaS」のいずれにも所属しない横断データである。

### 1.2 配置の選択肢

[account-architecture-analysis.md §4.2.1.X D 節](../account-architecture-analysis.md) で 5 案を比較した:

| 代替案 | 概要 |
|---|---|
| **D-1: 共通ドメインアカウント新設** | 専用 AWS アカウント +1、共通参照データ管理者（役割 5）が責任 |
| **D-2: 中央 BI / Catalog アカウントに同居** | Catalog アカウント内に共通マスタ S3 を置く、IAM Role で責務分離 |
| **D-3: 既存の代表アプリに寄せる** | 例: 経費精算 SaaS アカウントに置く |
| **D-4: マスタ専用 SaaS / MDM 製品導入** | Reltio / Informatica MDM 等 |
| **D-5: 採用しない** | アプリごとに独自マスタ、突合は都度 |

### 1.3 本 ADR の目的

**Phase 1（最初 18 ヶ月）でどの配置を採用するか**を明確に意思決定し、将来の再評価条件と判断記録を残す。

特に、**Phase 1 で D-1 を採用すべきか、D-2 で十分か**を判断する。

---

## 2. Decision

### 2.1 決定内容

**Phase 1 では D-2（中央 BI / Catalog アカウント同居）を採用する**。

**Phase 2 以降は再評価**: 共通参照データの規模・所有者の組織化・SaaS 製品ポートフォリオ拡大などのトリガ条件が満たされた時点で D-1（共通ドメインアカウント新設）への移行を再検討する。

### 2.2 採用構成（Phase 1）

| 要素 | 内容 |
|---|---|
| **アカウント** | **中央 BI / Catalog アカウント内に同居**（追加アカウントなし）|
| **保管先** | 中央 BI / Catalog アカウントの S3 バケット（独立バケット、命名で識別: `<prefix>-common-domain-<env>`）|
| **メタデータ** | 中央 Glue Data Catalog 内に「`common_domain`」データベースを作成、その配下にテーブル定義 |
| **暗号化** | 中央 BI / Catalog アカウントの KMS CMK（他のデータと共通鍵）|
| **管理者** | 共通参照データ管理者（役割 5）= **Phase 1 では中央 BI チームが兼任**、IAM Role `CommonReferenceDataManagerRole` を別途定義 |
| **アクセス制御** | Lake Formation LF-Tag `domain=common` で識別、Producer / Consumer からは Federation 不要（同一アカウント内）|
| **公開方法** | Athena 横断クエリで Producer 側 analytics と JOIN 可能 |
| **書込み権限** | `CommonReferenceDataManagerRole` のみ。Producer / Consumer は読込専用 |

### 2.3 採用しない選択肢と理由

| 不採用案 | 主な理由 |
|---|---|
| D-1（共通ドメインアカウント新設）| Phase 1 規模では責務分離効果に対しアカウント運用コストが見合わない。**Phase 2 以降の再評価候補として残す** |
| D-3（既存アプリに寄せる）| 依存方向の逆転、責務範囲外、障害影響伝播 — 構造上の欠陥がある |
| D-4（MDM 製品）| SaaS 不採用方針（[../proposal/fr/04-consumption.md §FR-4.0.A](../proposal/fr/04-consumption.md)）に抵触、コスト過剰 |
| D-5（持たない）| 顧客マスタ 1 件の不整合が全 SaaS 製品で発生、クロスアプリ分析が事実上不可能 |

---

## 3. Rationale（D-2 採用の根拠）

### 3.1 Phase 1 では責務分離の必要性が小さい

**D-1 が解決する問題**:
- カタログ管理者（役割 3）と共通参照データ管理者（役割 5）の責務混在
- カタログ層と共通参照データ層の障害影響伝播

**Phase 1 の実態**:
- 役割 5 は **中央 BI チームが兼任**する想定（[../account-architecture-analysis.md §3](../account-architecture-analysis.md)）
- 兼任である以上、責務分離の効果が **組織上は限定的**
- 共通参照データの規模も顧客マスタ ~ 数 GB 程度、Catalog 層との障害伝播リスクは限定的

→ **Phase 1 では責務分離効果より運用シンプル化の優先度が高い**。

### 3.2 アカウント運用コストの観点

| 観点 | D-1（新設）| D-2（同居）|
|---|---|---|
| AWS アカウント数 | +1 | +0 |
| AWS Organizations 設定 | 追加 OU 検討必要 | 不要 |
| 横串の請求書 / コスト分析 | アカウント単位で分離可能 | タグベース集計が必要 |
| 監査ログ集約 | 別アカウント分の収集設定 | 既存設定に含まれる |
| クロスアカウント設定 | Catalog Federation / RAM 必要 | 不要（同一アカウント内）|
| IAM Role 設計 | 単純（アカウント単位）| **`CommonReferenceDataManagerRole` を Catalog 系 Role と分離する必要** |
| 障害切り分け | 容易 | やや煩雑 |

→ Phase 1 規模では **アカウント追加コスト > 責務分離メリット**。

### 3.3 移行容易性の観点

**D-2 → D-1 への移行は技術的に容易**:

| 移行作業 | 内容 | 工数感 |
|---|---|---|
| 新アカウント作成 | AWS Organizations 配下に追加 | 数日 |
| S3 データ移行 | バケット間 Replication 一回限り | 数日 |
| Glue Catalog 移行 | DDL エクスポート → 新アカウントで CREATE TABLE + Federation 設定 | 1-2 週間 |
| IAM Role 移行 | 既存 `CommonReferenceDataManagerRole` を新アカウントに作成、信頼関係更新 | 1 週間 |
| 関連クエリ書換え | Athena の参照先が `common_domain` DB → Federated Catalog 経由に変更（DB 名は維持可能）| 1 週間 |
| 合計 | | **3-4 週間** |

→ **D-2 で開始して問題があれば D-1 に移行可能**な構造を維持。逆方向（D-1 → D-2）も可能だが、D-1 で構築した責務分離を解くのは組織変更を伴うため逆方向の方が重い。**D-2 から始める方が後悔が少ない**。

### 3.4 [DP-ADR-002](DP-ADR-002-redshift-emr-not-adopted.md) と同じ段階採用パターン

DP-ADR-002 では Redshift / EMR を「Phase 1/2 不採用 / Phase 3+ 再評価」とした。本 ADR も同じパターン:

- **Phase 1**: 規模に見合った最小構成 → D-2 同居
- **Phase 2 以降**: トリガ条件で再評価 → D-1 新設の可能性

これは「規模が小さいうちはシンプルに、大きくなったら分割」という一貫した段階採用方針に沿う。

---

## 4. 再評価条件（Phase 2 以降）

### 4.1 D-1 移行を検討するトリガ

以下のいずれかが満たされたら D-1（共通ドメインアカウント新設）への移行を検討:

| カテゴリ | トリガ条件 |
|---|---|
| **規模** | 共通参照データの S3 サイズが 100 GB を超える / 月間アクセス頻度が中央 BI 層の 50% を超える |
| **組織** | 共通参照データ管理者（役割 5）が中央 BI チームから**専任化**される / 専任チームが組成される |
| **SaaS ポートフォリオ** | 共通参照データに依存する SaaS 製品が **5 つ以上**になる |
| **マスタ管理機能** | 来歴管理・名寄せ・バージョニング等、Glue/Athena では不足する機能が要求される |
| **障害影響** | Catalog 層の障害で共通参照データ参照が停止する事象が**年 2 回以上**発生 |
| **規制・監査** | 共通参照データへのアクセスログを Catalog アカウントから**物理分離**することが規制要件になる |

### 4.2 Phase 2 で D-4（MDM 製品）の再評価条件

| カテゴリ | トリガ条件 |
|---|---|
| **名寄せ要件** | 複数 SaaS 製品で同じ顧客企業が別 ID で登録される問題が頻発し、SQL ベースの名寄せでは不十分 |
| **マスタ品質** | データガバナンス組織が独立して立ち上がり、専用ツールへの投資余地がある |
| **規制対応** | 顧客マスタの来歴管理が監査・規制要件になる |

→ **本 ADR の射程はあくまで D-1 vs D-2**。D-4 は別 ADR で扱う想定。

### 4.3 再評価のタイミング

- **定期**: Phase 2 開始時（Phase 1 18 ヶ月後）に必ず再評価
- **随時**: 上記トリガが満たされた時点で随時再評価

---

## 5. Consequences

### 5.1 良い結果

- **Phase 1 のアカウント数を最小化**（中央 +1 のみ、共通ドメインは追加せず）
- **クロスアカウント設定の単純化**（共通参照データへのアクセスが同一アカウント内に閉じる）
- **運用負荷の低減**（監査・コスト・ID 管理が中央 BI / Catalog アカウントに集約）
- **D-1 移行は将来も可能**（3-4 週間の見積もり）

### 5.2 悪い結果 / 妥協点

- **責務混在のリスク**: `DataLakeAdminRole` と `CommonReferenceDataManagerRole` が同じアカウント内に存在するため、IAM 設計と命名規約が雑だと権限境界が曖昧化する → **対策**: IAM Role を厳密に分離し、Lake Formation LF-Tag `domain=common` で明示的に識別
- **障害影響の伝播**: Catalog 層の障害で共通参照データ参照も影響を受ける → **対策**: Phase 1 規模では許容、トリガ条件で再評価
- **将来 D-1 に移行した場合の手戻り**: クエリの参照先変更が必要 → **対策**: クエリで使う DB 名（`common_domain`）を最初から固定し、移行時に Federation 経由で同じ名前を維持する設計
- **顧客マスタへの**「中立性」**の説明**: 「Catalog アカウントに置く = Catalog チームが管理する」と誤解されるリスク → **対策**: IAM Role 名・ドキュメント・組織図で「共通参照データ管理者は別役割」を明示

### 5.3 受け入れる残存リスク

- 上記 5.2 の「責務混在の運用ミス」は IAM 設計次第。**Phase 1 では役割 5 が兼任で運用ミスの影響範囲が限定的**なので許容する
- Phase 2 で組織化されたタイミングで D-1 移行を行うことで、ミスのリスクと組織の成熟度を同期させる

---

## 6. 詳細分析（Phase 2 再評価時の参考資料）

### 6.1 D-1 採用時の構成詳細

将来 D-1 に移行する場合の構成を、判断材料として記録しておく。

#### 6.1.1 アカウント設計

```
AWS Organizations
├── 親会社統制 OU
├── アプリ OU
│   ├── App 1 (Producer)
│   ├── App 2 (Producer)
│   └── ... App N (Producer)
├── データ基盤 OU
│   ├── 中央 BI / Catalog アカウント (Option B)
│   └── 共通ドメインアカウント ← Phase 2 で新設
└── 監査 OU（既存）
```

#### 6.1.2 共通ドメインアカウント内構成

| 要素 | 内容 |
|---|---|
| **S3** | `<prefix>-common-domain-<env>` バケット、Producer と同じ Medallion 構造（raw / curated / analytics）|
| **Glue Data Catalog** | `common_domain` データベース、顧客マスタ・組織マスタ等のテーブル |
| **Glue Crawler / ETL** | 契約管理 SaaS / Salesforce 等からの取込ジョブ |
| **KMS CMK** | 独立 CMK（鍵ローテーション独立）|
| **IAM Role** | `CommonReferenceDataManagerRole`（このアカウントが信頼関係の起点）|
| **Cross-account 設定** | Glue Catalog Federation で中央 BI / Catalog アカウントから参照 |
| **AWS RAM** | S3 アクセス権限を中央 BI アカウントに共有 |

#### 6.1.3 コスト試算（Phase 2、D-1 採用時）

| 項目 | 月額 |
|---|---|
| S3（10-50 GB）| $0.50-2.50 |
| Glue Catalog（10 万オブジェクト以下 → 無料枠内）| $0 |
| Glue Crawler（日次 1 時間 × 30 日 × 0.5 DPU）| ~$6 |
| Glue ETL（連携ジョブ、日次 10 分 × 30 日 × 2 DPU Flex）| ~$3 |
| Lambda（一部の連携 / 通知）| ~$1 |
| KMS（鍵 + リクエスト）| ~$1 |
| **合計** | **~$12-13** |

→ コスト面のハードルは小さい。**判断はあくまで組織・規模・責務分離の要否**。

### 6.2 [account-architecture-analysis.md §4.2.1.X D 節](../account-architecture-analysis.md) の比較表（参照用）

D-1 / D-2 / D-3 / D-4 / D-5 の評価は §4.2.1.X D 節を参照。本 ADR は **D-1 vs D-2** の二択で Phase 1 判断を行った記録。

---

## 7. 関連リンク

- [../account-architecture-analysis.md §4.2.1.X](../account-architecture-analysis.md): 共通ドメインアカウント検討の全文
- [../proposal/fr/01-data.md](../proposal/fr/01-data.md): 対象データと共通マスタの位置付け
- [DP-ADR-001](DP-ADR-001-sagemaker-catalog-adoption-deferred.md): 同様の Phase 別判断（SageMaker Catalog）
- [DP-ADR-002](DP-ADR-002-redshift-emr-not-adopted.md): 同様の Phase 別判断（Redshift / EMR）
