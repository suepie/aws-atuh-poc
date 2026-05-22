# 非機能要件（§NFR-API-1 〜 §NFR-API-9）

> 提示版 nfr/ サブフォルダの索引。IPA 非機能要求グレード 2018 の 6 大項目とマッピング。
> 親 SSOT: [../00-index.md](../00-index.md)

---

## 章一覧（IPA グレード対応）

| § | 章 | IPA 大項目 | 状態 |
|---|---|---|:---:|
| [§NFR-API-1](01-availability.md) | 可用性 | **A. 可用性** | 🚧 |
| [§NFR-API-2](02-performance.md) | 性能 | **B. 性能・拡張性**（応答時間） | 🚧 |
| [§NFR-API-3](03-scalability.md) | 拡張性 | **B. 性能・拡張性**（スケール） | 🚧 |
| [§NFR-API-4](04-security.md) | セキュリティ（死守事項） | **E. セキュリティ** | 🚧 |
| [§NFR-API-5](05-dr.md) | DR / BCP | **A. 可用性**（災害対策） | 🚧 |
| [§NFR-API-6](06-operations.md) | 運用 | **C. 運用・保守性** | 🚧 |
| [§NFR-API-7](07-compliance.md) | コンプライアンス | **E + C**（独立章） | 🚧 |
| [§NFR-API-8](08-cost.md) | コスト・課金可視化 | （IPA 範囲外）| 🚧 |
| [§NFR-API-9](09-compatibility.md) | 互換性・移行性 | **D. 移行性** | 🚧 |

IPA グレードの **F. システム環境・エコロジー** はクラウド前提で独自要件にならないため省略。

---

## ID 体系

各要件は `NFR-API-{CAT}-NNN` 形式で非機能要件カタログ（non-functional-requirements.md、TBD）に登録される。

| カテゴリ | 接頭辞 |
|---|---|
| 可用性 | `NFR-API-AVL-*` |
| 性能 | `NFR-API-PERF-*` |
| 拡張性 | `NFR-API-SCL-*` |
| セキュリティ | `NFR-API-SEC-*` |
| DR / BCP | `NFR-API-DR-*` |
| 運用 | `NFR-API-OPS-*` |
| コンプライアンス | `NFR-API-COMP-*` |
| コスト | `NFR-API-COST-*` |
| 互換性・移行性 | `NFR-API-COMPAT-*` |
