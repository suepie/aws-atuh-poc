# §FR-API-4 利用者識別・課金按分（詳細）

> 元データ: [../hearing-checklist.md B-3 後半 + D-2](../hearing-checklist.md#b-3-流量制御課金fr-api-3-fr-api-4)
> 対象: アプリリード / 経理 / SecOps
> 関連章: [§FR-API-4](../proposal/fr/04-metering-billing.md)
>
> **注**: 計測標準（B-411〜B-432）は [03-throttling-quota.md](03-throttling-quota.md) に統合済み。本ファイルは **Phase D の確定判断**（D-401 〜 D-413）を扱う。

---

### 【必須タグの最終確定（CostCenter 粒度）】 (API-D-401, 🔥)

必須タグセット（[§FR-API-4 §4.3](../proposal/fr/04-metering-billing.md)）の最終リストと、特に `CostCenter` の粒度をご確定ください。

本標準の暫定提案：

| タグキー | 値の例 | 用途 |
|---|---|---|
| `CostCenter` | `dept-ec`, `dept-hr` | 内部部門 |
| `Project` | `proj-checkout-api` | プロジェクト |
| `Environment` | `prod`, `stg`, `dev` | 環境 |
| `Application` | `app-billing` | アプリ |
| `Exposure` | `public`, `internal`, `partner`, `private` | 公開境界 |
| `Tenant` | `tenant-xxxx` | テナント |
| `DataClassification` | `pii`, `internal`, `public` | データ分類 |

`CostCenter` の粒度は次のいずれかで運用が大きく変わります：
- 部門単位（10〜30 個程度）
- 課単位（数百個）
- プロジェクト単位（`Project` タグと統合）
**目的**: 必須タグは Service Catalog 製品にハードコードされ、Config Rule でも強制されるため、確定後の変更コストが大きくなります。

---

### 【按分の最小粒度】 (API-D-411, 🔥)

CUR + cost allocation tag による按分の **最小粒度**をご教示ください。
- **テナント単位**（B2B SaaS、テナントごとのコストを請求）
- **部門単位**（社内コストセンタ別）
- **アプリ単位**（プロジェクト・サービス別）
- 上記の組合せ（複数次元で並行集計）
**目的**: [§FR-API-4 §4.4](../proposal/fr/04-metering-billing.md) の集計パイプライン設計。粒度によって QuickSight ダッシュボードの構成が変わります。

---

### 【共有リソースの按分ルール】 (API-D-412, 🟡)

共有リソース（VPC・Transit Gateway・データ転送・NAT Gateway 等の **untaggable / マルチ利用** リソース）のコスト按分ルールをご教示ください。
選択肢：
- AWS **Split Charge Rule**（CUR 機能、定義済みルールで自動分割）
- **AWS Application Cost Profiler**（マネージドサービス、API リクエスト数等で配賦）
- 自前集計（Athena クエリ + ロジック）
- 案分しない（共通コストとして集計外）
**目的**: [§FR-API-4 §4.4 / §NFR-API-8](../proposal/nfr/08-cost.md) の按分完全性。

---

### 【内部請求のサイクルと確定タイミング】 (API-D-413, 🟡)

内部請求（部門間付替・テナント請求）のサイクルと、コスト確定のタイミングをご教示ください。
- 月次 / 四半期 / 半期 / 年次
- AWS の月次明細確定（翌月 5 営業日目頃）後の処理リードタイム
**目的**: [§FR-API-4 §4.4](../proposal/fr/04-metering-billing.md) のパイプライン運用要件。会計システム連携の前提となります。

---

## ヒアリング後の確定事項チェックリスト

- [ ] 必須タグセット + CostCenter 粒度（D-401）
- [ ] 按分の最小粒度（D-411）
- [ ] 共有リソース按分ルール（D-412）

これらが揃うと **§FR-API-4 課金按分** と **Service Catalog 製品の必須タグ仕様** を確定できます。
