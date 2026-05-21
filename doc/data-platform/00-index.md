# データプラットフォーム ドキュメント

各アプリの AWS アカウントで**標準として定めるべきルール**を整理する領域。
共有認証基盤（[../requirements/](../requirements/00-index.md)）とは独立した別ドメインの取り組みで、[../api-platform/](../api-platform/00-index.md) と並ぶ「各アプリのアーキテクチャ標準化」の一部。

---

## §0.0 背景・なぜここで定めるか

このリポジトリの本筋は「共有認証基盤」の検証と要件定義だが、ドキュメント体系がそのまま雛形になるため、データプラットフォーム標準のドキュメントもここに間借りして作成する。

- **共有認証基盤**：共通アカウントに複数システムが接続する前提の横断サービス
- **API プラットフォーム標準**（[../api-platform/](../api-platform/00-index.md)）：各アプリの AWS アカウント内で守るべき API 周りの標準・ガードレール
- **データプラットフォーム標準（本領域）**：各アプリの AWS アカウント内で守るべき**データの蓄積・連携・閲覧・統制に関する標準**

読者も性質も異なるため、`doc/requirements/`（認証）・`doc/api-platform/`（API）・本フォルダはそれぞれ独立して運用する。

### 前提方針

- **AWS ネイティブサービスを優先**。SaaS は原則利用しない（よほどメリットがある場合を除き、選定時には ADR で意思決定経緯を残す）。
- 各アプリは自アカウント内でこの標準に沿って構築する。共有アカウントに集約するのではなく、**分散標準** として運用する。

---

## §0.1 スコープ（初期）

データプラットフォーム標準として扱う対象。詳細は今後 SSOT 文書で整理する。

| # | テーマ | 内容（初期メモ） |
|---|--------|----------------|
| 1 | データプラットフォームの定義 | 「データプラットフォームとは何か / 何を実現するのか」のミッションと境界 |
| 2 | 対象データ | 業務トランザクション / アプリログ / 監査ログ / メトリクス / 外部連携データ など、扱うデータ区分 |
| 3 | データの保存場所 | S3（データレイク） / RDS / DynamoDB / Glue Catalog 等、用途別の標準保存先 |
| 4 | データ連携の方法 | バッチ（Glue / Step Functions）/ ストリーム（Kinesis / MSK）/ CDC（DMS）等の使い分け |
| 5 | データの閲覧方法 | Athena / QuickSight / Redshift / 直接 S3 等、利用者属性ごとの標準 |
| 6 | データのガバナンス | 権限制御（Lake Formation / IAM）、暗号化、削除・保管ポリシー、PII 取り扱い |
| 7 | 構成例 | サーバレス系（S3 + Glue + Athena）、DWH 系（Redshift）等の参照アーキテクチャ |
| 8 | 利用者×ユースケース別実装例 | 業務利用者 / 開発者 / 分析者 / 監査者 など、ペルソナごとの実装パターン |
| 9 | 運用主体と責任分解 | データオーナー / プラットフォーム標準化推進者 / 各アプリ運用者の RACI |

> 上記は要望段階の見出しであり、章立て・粒度・依存関係は今後 SSOT 文書（後続作成予定）で整理する。

---

## §0.2 doc/requirements/（認証）・doc/api-platform/ との対比

| 観点 | doc/requirements/（認証基盤） | doc/api-platform/（API 標準） | doc/data-platform/（本領域） |
|------|------------------------------|------------------------------|------------------------------|
| 対象 | 共有認証基盤の機能・非機能要件 | 各アプリの AWS アカウントで守る API 周りの標準・ガードレール | 各アプリの AWS アカウントで守るデータ蓄積・連携・閲覧・統制の標準 |
| 構成形態 | 中央集権（共通アカウントに集約） | 分散標準（各アカウントに同じルールを適用） | 分散標準（各アカウントに同じルールを適用） |
| 主読者 | 共通基盤の運用者 + 接続アプリ開発者 | 各アプリの開発・運用担当者、プラットフォーム標準化推進者 | 各アプリの開発・運用担当者、データ利活用者、プラットフォーム標準化推進者 |
| 主成果物 | 要件定義書 + 顧客向け提示版 (proposal) | （TBD：要件定義書 + 各アプリ向けの標準ガイド） | （TBD：要件定義書 + 各アプリ向けの標準ガイド） |
| SaaS 方針 | 認証 SaaS（Auth0 等）は選定対象として比較 | AWS ネイティブ優先 | AWS ネイティブ優先（SaaS は原則不採用） |

---

## §0.3 ドキュメント構成

SSOT（[data-platform-document-structure.md](data-platform-document-structure.md)）に**ナラティブ（5 ステップ）・章構成・作成順序・依存関係・ダッシュボード・ID 体系**を集約。本ファイルは入口の役割のみ持つ。

```
doc/data-platform/
├── 00-index.md                              ← このファイル（暫定、入口）
└── data-platform-document-structure.md      ← SSOT（構成・ナラティブ・状態の単一情報源）
```

予定（SSOT §1 参照、決まったものから随時追加）：

- proposal/（fr/ §FR-1〜§FR-6 / nfr/ §NFR-1〜§NFR-9 / common/ §C-1〜§C-5）
- hearing-strategy / hearing-checklist / hearing-phase-a〜d
- data-platform-spec.md（標準仕様書本体）
- functional-requirements.md / non-functional-requirements.md
- service-selection-decision.md（AWS サービス選定判断書）
- reference-architectures/（S3 レイク / Redshift DWH / Streaming / 運用ストア の 4 本）
- governance-guide.md / cost-estimation.md

---

## §0.4 関連リンク

- [data-platform-document-structure.md](data-platform-document-structure.md) — 本領域の SSOT（まずここから）
- [../00-index.md](../00-index.md) — doc/ 全体の入口
- [../requirements/00-index.md](../requirements/00-index.md) — 認証基盤の要件定義（ドキュメント体系のお手本）
- [../requirements/requirements-document-structure.md](../requirements/requirements-document-structure.md) — 認証側 SSOT（本 SSOT の雛形元）
- [../api-platform/00-index.md](../api-platform/00-index.md) — API プラットフォーム標準（兄弟領域）
