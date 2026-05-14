# 非機能要件（NFR）— インデックス + IPA マッピング

> 上位 SSOT: [../00-index.md](../00-index.md)
> 詳細: [../../non-functional-requirements.md](../../non-functional-requirements.md)
> 関連: [IPA 非機能要求グレード 2018](https://www.ipa.go.jp/archive/digital/iot-en-ci/jyouryuu/hikinou/index.html)

---

## 0. はじめに

本フォルダ（nfr/）は、共有認証基盤の **非機能要件**を 9 領域に分けて整理する。各領域は **IPA 非機能要求グレード 2018**（大項目 6 / 中項目 35 / メトリクス 238）と対応付けて、業界標準に沿った要件定義を行う。

### IPA 非機能要求グレード 2018 の 6 大項目

1. **A. 可用性** — システムを止めない / 障害時の復旧
2. **B. 性能・拡張性** — 処理速度 / 規模変動への対応
3. **C. 運用・保守性** — 通常運用 / 障害時運用 / 保守
4. **D. 移行性** — 既存システムからの移行
5. **E. セキュリティ** — 不正アクセス防止 / 監査
6. **F. システム環境・エコロジー** — 物理環境 / グリーン IT

本基盤の §NFR は IPA グレードを**基準フレーム**とし、認証基盤として固有な観点を加える。

---

## 1. §NFR と IPA 非機能要求グレード のマッピング

| 本基盤 §NFR | IPA 大項目 | IPA 主要中項目 |
|---|---|---|
| [§NFR-1 可用性](01-availability.md) | **A. 可用性** | 継続性 / 耐障害性 / 災害対策（一部）|
| [§NFR-2 性能](02-performance.md) | **B. 性能・拡張性** | 業務処理量 / 性能目標値 |
| [§NFR-3 拡張性](03-scalability.md) | **B. 性能・拡張性** | 拡張性 / 性能品質保証 |
| [§NFR-4 セキュリティ](04-security.md) | **E. セキュリティ** | 認証 / アクセス制限 / データ秘匿 / 不正追跡・監査 / マルウェア対策 / Web 対策 |
| [§NFR-5 DR](05-dr.md) | **A. 可用性** | 災害対策 / 復旧可能性 |
| [§NFR-6 運用](06-operations.md) | **C. 運用・保守性** | 通常運用 / 保守運用 / 障害時運用 / 運用環境 / サポート体制 |
| [§NFR-7 コンプライアンス](07-compliance.md) | **E + C** | （IPA 直接対応なし、業界規制対応として独立） |
| [§NFR-8 コスト](08-cost.md) | （IPA 範囲外）| 別途、本基盤独自の重要要件 |
| [§NFR-9 移行性](09-migration.md) | **D. 移行性** | 移行時期 / 移行方式 / 移行対象データ / 移行計画 |

**注**: IPA F. システム環境・エコロジーは AWS マネージドサービス前提で透過化されるため、本基盤では独立章としては扱わない（[§NFR-6 運用](06-operations.md) と [§NFR-8 コスト](08-cost.md) に内包）。

---

## 2. 章ナビゲーション

| 章 | ファイル | 内容 |
|---|---|---|
| §NFR-1 | [01-availability.md](01-availability.md) | 可用性（SLA / Multi-AZ / 自動復旧 / メンテ窓） |
| §NFR-2 | [02-performance.md](02-performance.md) | 性能（応答時間 / スループット / レイテンシ）|
| §NFR-3 | [03-scalability.md](03-scalability.md) | 拡張性（MAU スケール / IdP 拡張 / マルチリージョン）|
| §NFR-4 | [04-security.md](04-security.md) | セキュリティ（暗号化 / トークン / 攻撃対策 / ネットワーク）|
| §NFR-5 | [05-dr.md](05-dr.md) | DR（RTO / RPO / フェイルオーバー）|
| §NFR-6 | [06-operations.md](06-operations.md) | 運用（監視 / デプロイ / 体制）|
| §NFR-7 | [07-compliance.md](07-compliance.md) | コンプラ（規制 / 業界認定 / データガバナンス）|
| §NFR-8 | [08-cost.md](08-cost.md) | コスト（直接 / 間接 / 3 年 TCO）|
| §NFR-9 | [09-migration.md](09-migration.md) | 移行性（既存からの移行 / ハッシュ持ち越し）|

---

## 3. 関連ドキュメント

- [../../non-functional-requirements.md](../../non-functional-requirements.md) — 内部 NFR 一覧
- [../../requirements-document-structure.md](../../requirements-document-structure.md) — 要件定義 SSOT
- [IPA 非機能要求グレード 2018 公式](https://www.ipa.go.jp/archive/digital/iot-en-ci/jyouryuu/hikinou/index.html)
- [非機能要求グレードの歩き方 - Zenn](https://zenn.dev/nttdata_tech/articles/c16414c86883cb)
