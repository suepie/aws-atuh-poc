# API プラットフォーム標準 ヒアリングスクリプト

> 目的: [../hearing-checklist.md](../hearing-checklist.md) の全項目を **関係者にそのまま送付できる敬体形式**で出力したもの。各質問の「目的・必要な理由」を併記。
> SSOT: [../hearing-checklist.md](../hearing-checklist.md)（ID / 優先度 / 関連 FR/NFR / 章番号は本ファイル側を正とする）

---

## 構成

| ファイル | 内容 | 対応元 |
|---|---|---|
| [00-common.md](00-common.md) | Phase A 既存アプリ現状・前提（12 項目） | A-101〜A-111 |
| [12-architecture-pattern.md](12-architecture-pattern.md) ⭐ | **Phase B-0 アーキパターン選定**（SPA+API / SSR+API / SSR モノリス、9 項目） | B-001〜B-005, A-102-α, A-111 |
| [01-exposure-boundary.md](01-exposure-boundary.md) | §FR-API-1 公開境界（5 項目） | B-101〜B-106 |
| [02-authn-authz.md](02-authn-authz.md) | §FR-API-2 認証認可（11 項目） | B-201〜B-243 |
| [03-throttling-quota.md](03-throttling-quota.md) | §FR-API-3/4 流量制御・課金（16 項目） | B-301〜B-432 |
| [04-metering-billing.md](04-metering-billing.md) | §FR-API-4 詳細（按分・タグ） | B-401〜B-432 + D-4 系 |
| [05-serverless-standard.md](05-serverless-standard.md) | §FR-API-5 Serverless（11 項目） | B-501〜B-552 |
| [06-container-standard.md](06-container-standard.md) | §FR-API-6 Container（10 項目） | B-601〜B-652 |
| [07-guardrails.md](07-guardrails.md) | §FR-API-7 ガードレール（10 項目） | D-7 系 |
| [08-observability.md](08-observability.md) | §FR-API-8 観測性（9 項目） | C-811〜C-833 |
| [09-nfr.md](09-nfr.md) | §NFR-API-1〜9 非機能（28 項目） | C-9 / C-10 / C-12 / D-5 / D-6 / D-8 / D-9 / D-10 系 |
| [10-final-decisions.md](10-final-decisions.md) | Phase D 最終判断（21 項目） | D-1 / D-11 / D-12 / D-13 系 |

---

## 凡例

各項目は以下の形式で記載しています:

```markdown
---
### 【項目タイトル】 (ID, 優先度)

質問本文（敬体）。
追加で確認したい詳細。
**目的**: 本標準側の意図と、この情報が必要な理由。
---
```

- **優先度**: 🔥 最優先（本標準の中核判断）/ 🟡 重要 / 🟢 通常
- **ID**: API-A-XXX / API-B-XXX / API-C-XXXX / API-D-XXXX
- **目的**: なぜこの質問をするか、どの設計判断に必要か

---

## ヒアリング推奨順序

1. **Phase A**（既存現状）→ 標準化対象範囲、既存アプリ実装の分布、既存スキル等、後続選定の前提
2. **Phase B-0**（アーキパターン選定）⭐ → SPA+API / SSR+API / SSR モノリスの 3 パターンに対する本標準のスタンス
3. **Phase B-1〜5**（技術要件）→ 公開境界 / 認証 / 流量 / Serverless / Container 等、機能標準の中核
4. **Phase C**（運用・セキュリティ）→ 観測性 / 死守事項 / コンプラ / 運用体制
5. **Phase D**（最終判断）→ ガードレール承認 / 移行計画 / 体制・予算

→ A → B-0 → B-1〜5 → C → D の順で進めると、後段の判断に必要な情報が手戻りなく揃います。Phase B-0 を早期に確定すると、Service Catalog 製品ラインナップの設計に着手できます。

---

## 補足

- 全 135 項目の網羅版です。プロジェクト初期に **🔥 最優先 25 項目を Stage 1 として先行確認** することで、本標準の中核判断（公開境界判定 / Serverless-Container 選定方針 / 監査アカウント役割 / ガードレール範囲）を早期確定できます。
- 「**Bot Control 採用範囲**」「**死守事項マトリクス**」「**Service Catalog 初期ラインナップ**」が Stage 1 で確定すると、Service Catalog 製品の設計に着手できます。
- 元データの標準パターン・対応マトリクスは [../proposal/](../proposal/00-index.md) 配下の各章を参照してください。
