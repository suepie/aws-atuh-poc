# 機能要件（§FR-API-1 〜 §FR-API-8）

> 提示版 fr/ サブフォルダの索引。各章は §X.0「前提と背景」+ サブセクション + ベースライン + TBD の構造で記述。
> 親 SSOT: [../00-index.md](../00-index.md)

---

## 章一覧

| § | 章 | 主題 | 状態 |
|---|---|---|:---:|
| [§FR-API-1](01-exposure-boundary.md) | 公開境界 | Public / Internal / Partner / Private の区分と判定 | 🚧 |
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
| 公開境界 | `FR-API-EXP-*` |
| 認証認可 | `FR-API-AUTH-*` |
| 流量制御 | `FR-API-RATE-*` |
| 利用者識別・課金 | `FR-API-MTR-*` |
| Serverless 標準 | `FR-API-SLS-*` |
| Container 標準 | `FR-API-CNT-*` |
| ガードレール | `FR-API-GRD-*` |
| 観測性 | `FR-API-OBS-*` |
