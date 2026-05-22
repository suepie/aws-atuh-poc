# API プラットフォーム ドキュメント

各アプリの AWS アカウントで**標準として定めるべきルール**を整理する領域。
共有認証基盤（[../requirements/](../requirements/00-index.md)）とは独立した別ドメインの取り組み。

> 🌟 **まずここから**: [requirements-document-structure.md](requirements-document-structure.md) が API プラットフォーム標準 要件定義の **SSOT (Single Source of Truth)**。
> §0 ナラティブ（6 ステップ）／§1 ドキュメント体系／§8 依存関係と読み順／§9 ダッシュボード が全体把握の入口。
>
> 📣 **関係者向け要件提示**: [proposal/00-index.md](proposal/00-index.md)（フォルダ化済、章ごとにファイル分割、FR/NFR/common と 1:1 対応、サブセクション単位でベースライン提示 + TBD/要確認）

---

## §0.0 背景・なぜここで定めるか

このリポジトリの本筋は「共有認証基盤」の検証と要件定義だが、ドキュメント体系がそのまま雛形になるため、API プラットフォーム標準のドキュメントもここに間借りして作成する。

- **共有認証基盤**：共通アカウントに複数システムが接続する前提の横断サービス
- **API プラットフォーム標準（本領域）**：各アプリの AWS アカウント内で守るべき**アーキテクチャ標準・ガードレール**

両者は読者も性質も異なるため、`doc/requirements/`（認証）と本フォルダは独立して運用する。

---

## §0.1 スコープ（4 層モデル）

調査の結果、API プラットフォーム標準は **4 層 + 横串** で整理するのが AWS 流儀。

```
[公開境界層]      Who can reach the API?         Public / Internal / Partner / Private
[認証認可層]      Who is the caller?              共有認証基盤 / API Key / mTLS / IAM
[流量制御層]      How much can the caller use?    Throttle / Quota / 利用者識別 / 課金按分
[実装ランタイム層] How is the API served?         Serverless（API GW + Lambda）/ Container（ECS）
└横串：観測性（ログ・トレース・メトリクス）／コスト按分／ガードレール（監査アカウント FMS）
```

初期 6 テーマはこの 4 層に以下のようにマップされる：

| 要望テーマ | 4 層モデルでの位置 | 章 |
|---|---|---|
| 公開範囲ルール（Public / Internal） | 公開境界層 | [§FR-API-1](proposal/fr/01-exposure-boundary.md) |
| 流量制限・課金管理 | 流量制御層 | [§FR-API-3](proposal/fr/03-throttling-quota.md) / [§FR-API-4](proposal/fr/04-metering-billing.md) |
| 監査アカウント FMS | 横串：ガードレール | [§FR-API-7](proposal/fr/07-guardrails.md) |
| 標準アーキ（Serverless / ECS） | 実装ランタイム層 | [§FR-API-5](proposal/fr/05-serverless-standard.md) / [§FR-API-6](proposal/fr/06-container-standard.md) |
| セキュリティ死守事項 | 横串（NFR） | [§NFR-API-4](proposal/nfr/04-security.md) |
| ログのベストプラクティス | 横串：観測性 | [§FR-API-8](proposal/fr/08-observability.md) / [§NFR-API-6](proposal/nfr/06-operations.md) |

---

## §0.2 doc/requirements/（認証）との対比

| 観点 | doc/requirements/（認証基盤） | doc/api-platform/（本領域） |
|------|------------------------------|------------------------------|
| 対象 | 共有認証基盤の機能・非機能要件 | 各アプリの AWS アカウントで守る標準・ガードレール |
| 構成形態 | 中央集権（共通アカウントに集約） | 分散標準（各アカウントに同じルールを適用） |
| 主読者 | 共通基盤の運用者 + 接続アプリ開発者 | 各アプリの開発・運用担当者、プラットフォーム標準化推進者 |
| 中核ストーリー | プラットフォーム単一選定（Cognito vs Keycloak） | 2 系統並行カタログ（Serverless / Container）+ ガードレール配信 |
| 主成果物 | 要件定義書 + 顧客向け提示版 (proposal) | 要件定義書 + 提示版 (proposal) + 選定基準書 + 参考実装 |

---

## §0.3 ドキュメント構成（現状）

```
doc/api-platform/
├── 00-index.md                           ← 本ファイル
├── requirements-document-structure.md    ← SSOT（章立て・ナラティブ・進捗）🚧 ドラフト初版
│
├── proposal/                             ← 関係者向け要件定義 提示版 🚧 骨格初版
│   ├── 00-index.md                       ← proposal SSOT（基本方針・6 ステップ・章ナビ）
│   ├── fr/   (§FR-API-1 〜 §FR-API-8、8 章)
│   ├── nfr/  (§NFR-API-1 〜 §NFR-API-9、9 章 + IPA マッピング)
│   └── common/ (§C-API-1 〜 §C-API-5、5 章)
│
├── hearing-checklist.md                  ← ヒアリング項目 単一一覧（135 項目、Phase A-D）
└── hearing-script/                       ← 関係者送付用 敬体スクリプト
    ├── README.md
    ├── 00-common.md                      ← Phase A 共通前提
    └── 01〜10-*.md                       ← 章別スクリプト（FR / NFR / 最終判断）
```

詳細は [requirements-document-structure.md §1 ドキュメント体系の全体像](requirements-document-structure.md) を参照。

---

## §0.4 ドキュメント一覧

| ドキュメント | 内容 | 状態 |
|------------|------|:---:|
| **[requirements-document-structure.md](requirements-document-structure.md)** ⭐ | **要件定義 SSOT**：ナラティブ・6 ステップ・章構成・依存関係・状態ダッシュボード | 🚧 ドラフト初版 |
| **[proposal/](proposal/00-index.md)** 📣 | **関係者向け要件定義 提示版**：FR/NFR/common と 1:1 対応で要件ベースライン提示 | 🚧 骨格初版（全 22 章） |
| **[hearing-checklist.md](hearing-checklist.md)** | ヒアリング項目 単一一覧（135 項目、Phase A〜D、優先度・関連 FR/NFR 付き） | 🚧 初版 |
| **[hearing-script/](hearing-script/README.md)** | 関係者送付用 敬体スクリプト（章別 11 ファイル） | 🚧 初版 |

---

## §0.5 関連リンク

- [../00-index.md](../00-index.md) — doc/ 全体の入口
- [../requirements/00-index.md](../requirements/00-index.md) — 認証基盤の要件定義（ドキュメント体系のお手本）
- [../requirements/requirements-document-structure.md](../requirements/requirements-document-structure.md) — 認証側 SSOT（本書 SSOT の構造的雛形）
