# 機能要件（§FR-API-1 〜 §FR-API-8）

> 提示版 fr/ サブフォルダの索引。各章は §X.0「前提と背景」+ サブセクション + ベースライン + TBD の構造で記述。
> 親 SSOT: [../00-index.md](../00-index.md)

---

## 章一覧

| § | 章 | 主題 | 状態 |
|---|---|---|:---:|
| **[§FR-API-0](00-external-api-consumption-overview.md)** | **外部サービスからの API 実行 — 章プロローグ** | **6 タイプ（Partner B2B / 顧客 S2S / 顧客 Browser / Webhook / Open Public / 金融グレード）× 10 観点責任配置マトリクス + 推奨パターン + 決定フローチャート + 実装テンプレ。§FR-API-1〜8 + §C-API-* の Aggregator SSOT** | 🆕 |
| [§FR-API-1](01-exposure-boundary.md) | 公開範囲（信頼プロファイル）| 5 Profile（パブリック認証有/オープン、社内、パートナー、社内限定）— ネットワーク × 認証 × 既定 WAF を統合 | 🚧 |
| [§FR-API-2](02-authn-authz.md) | 認証認可 | 共有認証基盤連携 / API Key / mTLS / IAM auth / Authorizer 選定 | 🚧 |
| [§FR-API-3](03-throttling-quota.md) | 流量制御 | throttle / burst / quota / 超過時挙動 | 🚧 |
| [§FR-API-4](04-metering-billing.md) | 利用者識別・課金 | 識別子体系 / 計測 / cost allocation / 按分 | 🚧 |
| [§FR-API-5](05-serverless-standard.md) | Serverless 標準 | API GW + Lambda / Function URL / イベント駆動 / DB アクセス | 🚧 |
| [§FR-API-6](06-container-standard.md) | Container 標準 | ECS Fargate / ALB-NLB / Service Connect / Lattice | 🚧 |
| [§FR-API-7](07-guardrails.md) | ガードレール | FMS 配信 / SCP / Config Rules / Service Catalog | 🚧 |
| [§FR-API-8](08-observability.md) | 観測性 | 構造化ログ / トレース（ADOT）/ メトリクス / 監査ログ | 🚧 |

---

## ID 体系

各要件は `FR-API-{CAT}-NNN` 形式で機能要件カタログ（functional-requirements.md、TBD）に登録される。

| カテゴリ | 接頭辞 |
|---|---|
| 公開範囲（信頼プロファイル） | `FR-API-EXP-*` |
| 認証認可 | `FR-API-AUTH-*` |
| 流量制御 | `FR-API-RATE-*` |
| 利用者識別・課金 | `FR-API-MTR-*` |
| Serverless 標準 | `FR-API-SLS-*` |
| Container 標準 | `FR-API-CNT-*` |
| ガードレール | `FR-API-GRD-*` |
| 観測性 | `FR-API-OBS-*` |
