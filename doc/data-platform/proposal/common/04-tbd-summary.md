# §C-4 TBD / 要確認 事項サマリー

> 上位 SSOT: [../00-index.md](../00-index.md) / [00-index.md](00-index.md)
> 一次ソース: 各章 §FR-X / §NFR-X / §C-X の「TBD / 要確認」セクション

---

## §C-4.0 前提と背景

### なぜここ（§C-4）で決めるか

各章に分散している「TBD / 要確認」を 1 つのリストに集約し、**ヒアリング項目の単一情報源**として機能させる章。本サマリーは [../../hearing-checklist.md](../../hearing-checklist.md)（未着手）の起点になる。

### §C-4.0.A 本標準のスタンス

> **proposal/ 各章の TBD を機械的に集約するだけでなく、優先度（Critical / High / Medium / Low）と確定タイミング（合意取り段階 / ヒアリング Phase A〜D）を付与する。これにより、何を先に決めるべきかが一目で分かるようにする。**

### 本章で扱うサブセクション

| サブセクション | 内容 |
|---|---|
| §C-4.1 優先度別サマリー | Critical / High / Medium / Low |
| §C-4.2 章別 TBD 一覧 | 各章のリストへのリンク + 件数 |
| §C-4.3 確定タイミング表 | Phase A〜D に対する割り振り |

---

## §C-4.1 優先度別サマリー

> **このサブセクションで定めること**: TBD の優先度別集計と、それぞれの代表項目。
> **主な判断軸**: 後続論点への影響度 / 確定の難度
> **§C-4 全体との関係**: 一覧の俯瞰ビュー

### 凡例

| 優先度 | 意味 | 例 |
|---|---|---|
| **Critical** | これが決まらないと proposal/ の合意が進まない | 機密度区分の社内規定整合 |
| **High** | 標準の骨格に影響する | 既存データの規模・保管要件 |
| **Medium** | 詳細パラメータの確定 | アラート閾値 / コスト上限 |
| **Low** | 運用開始後でも調整可 | 棚卸しテンプレ詳細 |

### ベースライン（初期）

> 各章の TBD を本リストに集約するのは proposal 各章の中身が固まった次のフェーズ。本サブセクションは構造のみ提示し、初版では未集計。

| 優先度 | 件数 | 主な内容 |
|---|---:|---|
| Critical | TBD | （proposal/ 各章レビュー後に集計） |
| High | TBD | （同上） |
| Medium | TBD | （同上） |
| Low | TBD | （同上） |

---

## §C-4.2 章別 TBD 一覧

> **このサブセクションで定めること**: 各章の TBD リストへのリンクと件数。
> **§C-4 全体との関係**: 章別ナビゲーション

### ベースライン

| 章 | TBD セクション | 件数 |
|---|---|---:|
| §FR-1 対象データ | [fr/01-data-catalog.md](../fr/01-data-catalog.md) 各 TBD | 集計 TBD |
| §FR-2 保存先 | [fr/02-storage.md](../fr/02-storage.md) 各 TBD | 集計 TBD |
| §FR-3 連携 | [fr/03-pipeline.md](../fr/03-pipeline.md) 各 TBD | 集計 TBD |
| §FR-4 閲覧・活用 | [fr/04-consumption.md](../fr/04-consumption.md) 各 TBD | 集計 TBD |
| §FR-5 ガバナンス | [fr/05-governance.md](../fr/05-governance.md) 各 TBD | 集計 TBD |
| §FR-6 ペルソナ | [fr/06-personas.md](../fr/06-personas.md) 各 TBD | 集計 TBD |
| §NFR-1〜9 | [../nfr/](../nfr/) 各章 TBD | 集計 TBD |
| §C-1 参照アーキ | [01-architecture.md](01-architecture.md) 各 TBD | 集計 TBD |
| §C-2 サービス選定 | [02-service-selection.md](02-service-selection.md) 各 TBD | 集計 TBD |
| §C-3 RACI | [03-ownership-raci.md](03-ownership-raci.md) 各 TBD | 集計 TBD |

---

## §C-4.3 確定タイミング表

> **このサブセクションで定めること**: 各 TBD をどのヒアリング Phase で確定させるかの計画。
> **主な判断軸**: 依存関係 / ステークホルダー / 確定までの SLA
> **§C-4 全体との関係**: §C-5 スケジュールとの接続点

### ベースライン

| Phase | 確定するもの | 関連章 |
|---|---|---|
| Phase A: スコープ・対象データ | データ区分 / 機密度区分 / オーナー任命方針 | §FR-1 |
| Phase B: 技術要件 | 保存先選定 / 連携方式 / 閲覧手段 | §FR-2 / §FR-3 / §FR-4 / §C-1 / §C-2 |
| Phase C: ガバナンス・運用 | 権限・暗号化・PII / 監視・データ品質 | §FR-5 / §NFR-4 / §NFR-6 / §NFR-7 |
| Phase D: 推進体制・スケジュール | RACI / 移行計画 / 改訂サイクル | §C-3 / §NFR-9 / §C-5 |

### TBD / 要確認

- Phase の区切り方
- 各 Phase の参加者・期間

---

## §C-4.X 関連リンク

- [00-index.md](00-index.md): Common インデックス
- 各章の TBD セクション（[../fr/](../fr/) / [../nfr/](../nfr/) / 他 §C 章）
- [../../hearing-checklist.md](../../hearing-checklist.md): ヒアリング項目一覧（未着手）
