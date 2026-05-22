# 非機能要件（NFR）— インデックス + IPA マッピング

> 上位 SSOT: [../00-index.md](../00-index.md)
> 詳細: [../../non-functional-requirements.md](../../non-functional-requirements.md)
> 関連: [IPA 非機能要求グレード 2018](https://www.ipa.go.jp/archive/digital/iot-en-ci/jyouryuu/hikinou/index.html)

---

## 0. はじめに

本フォルダ（nfr/）は、データプラットフォーム標準の **非機能要件**を 9 領域に分けて整理する。認証側 NFR と同じく **IPA 非機能要求グレード 2018**（大項目 6 / 中項目 35 / メトリクス 238）と対応付けて、業界標準に沿った要件定義を行う。

### IPA 非機能要求グレード 2018 の 6 大項目

1. **A. 可用性** — システムを止めない / 障害時の復旧
2. **B. 性能・拡張性** — 処理速度 / 規模変動への対応
3. **C. 運用・保守性** — 通常運用 / 障害時運用 / 保守
4. **D. 移行性** — 既存システムからの移行
5. **E. セキュリティ** — 不正アクセス防止 / 監査
6. **F. システム環境・エコロジー** — 物理環境 / グリーン IT

本標準の §NFR は IPA グレードを**基準フレーム**とし、データプラットフォーム固有の観点（データ保持・データ品質・データライフサイクル）を加える。

---

## 1. §NFR と IPA 非機能要求グレード のマッピング

| 本標準 §NFR | IPA 大項目 | IPA 主要中項目 | データ領域固有の補強 |
|---|---|---|---|
| [§NFR-1 可用性](01-availability.md) | **A. 可用性** | 継続性 / 耐障害性 | 保存先別 SLA（S3 / RDS / Redshift / OpenSearch）|
| [§NFR-2 性能](02-performance.md) | **B. 性能・拡張性** | 業務処理量 / 性能目標値 | クエリレイテンシ / スループット / バッチ処理時間 |
| [§NFR-3 拡張性](03-scalability.md) | **B. 性能・拡張性** | 拡張性 / 性能品質保証 | データ量増加 / 同時利用者数 |
| [§NFR-4 セキュリティ](04-security.md) | **E. セキュリティ** | 認証 / アクセス制限 / データ秘匿 / 不正追跡・監査 | 暗号化（at-rest / in-transit）/ Lake Formation |
| [§NFR-5 DR](05-dr.md) | **A. 可用性（災害対策）** | 復旧可能性 / バックアップ | クロスリージョン / Glacier 復旧 SLA |
| [§NFR-6 運用](06-operations.md) | **C. 運用・保守性** | 通常運用 / 障害時運用 | データ品質監視 / コスト監視 |
| [§NFR-7 コンプライアンス](07-compliance.md) | **E + C** | （IPA 直接対応なし、独立章） | 個人情報保護法 / 業界規制 / 監査ログ保管 |
| [§NFR-8 コスト](08-cost.md) | （IPA 範囲外） | 別途、本標準の重要要件 | 保存・転送・分析の各コスト統制 |
| [§NFR-9 データライフサイクル](09-lifecycle.md) | **D. 移行性** に準じる | 移行対象データ / 保管・廃棄 | 保管期間 / アーカイブ / 削除（GDPR 等の「忘れられる権利」対応） |

**注**: IPA F. システム環境・エコロジーは AWS マネージドサービス前提で透過化されるため、本標準では独立章としては扱わない（[§NFR-6 運用](06-operations.md) と [§NFR-8 コスト](08-cost.md) に内包）。

**§NFR-9 の位置付け**: 認証側 NFR では `§NFR-9 移行性` だったが、データプラットフォームでは「データの保管・アーカイブ・削除」が中核論点になるため、**「データライフサイクル」** に置き換えた。既存データの移行（既存 → 標準準拠）は §NFR-9 内のサブセクションとして扱う。

---

## 2. 章ナビゲーション

| 章 | ファイル | 内容 |
|---|---|---|
| §NFR-1 | [01-availability.md](01-availability.md) | 可用性（保存先別 SLA） |
| §NFR-2 | [02-performance.md](02-performance.md) | 性能（クエリレイテンシ / スループット） |
| §NFR-3 | [03-scalability.md](03-scalability.md) | 拡張性（データ量・利用者数の増加） |
| §NFR-4 | [04-security.md](04-security.md) | セキュリティ（暗号化・アクセス制御・監査） |
| §NFR-5 | [05-dr.md](05-dr.md) | DR（バックアップ・クロスリージョン） |
| §NFR-6 | [06-operations.md](06-operations.md) | 運用（監視・データ品質） |
| §NFR-7 | [07-compliance.md](07-compliance.md) | コンプライアンス（規制・認定） |
| §NFR-8 | [08-cost.md](08-cost.md) | コスト（保存・転送・分析） |
| §NFR-9 | [09-lifecycle.md](09-lifecycle.md) | データライフサイクル（保管・アーカイブ・削除） |

---

## 3. 関連ドキュメント

- [../../non-functional-requirements.md](../../non-functional-requirements.md) — NFR 詳細マトリクス
- [../../data-platform-document-structure.md](../../data-platform-document-structure.md) — 領域全体 SSOT
- [../../../requirements/proposal/nfr/00-index.md](../../../requirements/proposal/nfr/00-index.md) — 認証側 NFR（雛形元）
- [IPA 非機能要求グレード 2018 公式](https://www.ipa.go.jp/archive/digital/iot-en-ci/jyouryuu/hikinou/index.html)
