# データプラットフォーム ヒアリング項目一覧（統合チェックリスト）

> **位置付け**: 検討過程で散在している「残課題 / ヒアリング項目」を統合し、**対象者別 / トピック別 / 優先度別**に整理した実務チェックリスト。
> **対応 SSOT**:
> - [account-architecture-analysis.md](account-architecture-analysis.md)（§4.2.1.X / §4.5.5 の残課題）
> - [strawman-proposal.md](strawman-proposal.md) §6.1（組織別ヒアリング項目、原本）
> - [architecture-alternatives-comparison.md](architecture-alternatives-comparison.md) §2.1.8（Pattern B 採用条件）
> - [hearing-slide-deck.md](hearing-slide-deck.md)（当日提示用スライド、45 枚）
> **作成日**: 2026-07-02
> **項目総数**: 73 項目（P0: 22 / P1: 31 / P2: 20）

---

## §0 使い方

### 0.1 目的

Phase 1 の設計確定に必要な意思決定情報を、**もれなく・重複なく・優先度付きで**取得する。

### 0.2 4 つの索引

| 索引 | 用途 |
|---|---|
| [§2 優先度別クイックリファレンス](#2-優先度別クイックリファレンスp0-p1-p2) | 「今日の会議で必ず聞くべき」項目を秒で選ぶ |
| [§3 対象者別項目リスト](#3-対象者別ヒアリング項目) | 個別ヒアリング前に、その相手に聞くべき項目を確認 |
| [§4 トピック別マスタリスト](#4-トピック別マスタリスト) | 「セキュリティ観点で確認すべきことは何か」等の網羅チェック |
| [§5 統合マスタ表（ID 付き）](#5-統合マスタ表id-付き) | 全項目を ID・状態・回答を管理する Single Source of Truth |

### 0.3 ID 体系

```
DP-{カテゴリ}-{連番}

カテゴリ:
  ORG   組織・チーム構成
  SCOPE スコープ・対象データ
  ARCH  アーキテクチャ選択
  COST  コスト・規模
  SEC   セキュリティ・コンプライアンス
  UX    UX・ダッシュボード
  NFR   非機能・SLA・運用
```

### 0.4 優先度定義

| 優先度 | 定義 | Phase |
|---|---|---|
| **P0** | Phase 1 設計決定に**必須**。回答なしで進めるとやり直しリスク | Phase 1 開始前 |
| **P1** | Phase 1 詳細設計・実装に必要 | Phase 1 中盤まで |
| **P2** | Phase 2 判断・将来評価のため確認 | Phase 1 末〜Phase 2 |

### 0.5 状態管理

| 状態 | 意味 |
|---|---|
| 🔴 未回答 | ヒアリング未実施 |
| 🟡 部分回答 | 一部回答済、詳細追加ヒアリング必要 |
| 🟢 回答済 | 回答内容が仮案に反映済 |
| 🔵 確定 | 意思決定完了、ADR 化済 |
| ⚪ 保留 | Phase 2 以降で再確認、現段階は不要 |

---

## §1 ヒアリング全体設計

### 1.1 対象者（7 種）

| # | 対象者 | 想定人数 | 主な関心 |
|---|---|---|---|
| A | 経営層（CXO / 事業責任者）| 1-3 名 | 事業戦略・KPI・投資判断 |
| B | 中央 BI チーム（新設想定、役割 3+4）| 2 名 | 実装可能性・スキル・工数 |
| C | 各アプリ部署（データオーナー候補、役割 1）| 案件数 | ETL 実装工数・スキル |
| D | 業務利用者（役割 6、CS / PM / マーケ / 経営層閲覧）| 10-50 名 | ダッシュ要件・UX |
| E | 監査担当者（役割 7、既存 Audit 部門）| 1-3 名 | 監査ログ要件・PII 参照権限 |
| F | 親会社統制チーム / 情シス | 数名 | 監査アカウント連携・ネットワーク |
| G | データエンジニアリング組織（横断）| 1-3 名 | ETL パターン統一・スキル基盤 |
| H | セキュリティ / コンプラ担当 | 2-3 名 | PII 保護・削除要件・監査 |

### 1.2 Phase 別優先度

| Phase | ヒアリング内容 | 完了時期 |
|---|---|---|
| **Phase A: 事前確認** | 組織・スコープ・既存の状況の把握 | Phase 1 開始 -1 ヶ月 |
| **Phase B: 設計合意** | アーキテクチャ選択・コスト・SLA の確定 | Phase 1 開始 |
| **Phase C: 実装詳細** | UX・データセット設計・運用ルール | Phase 1 前半 |
| **Phase D: 将来判断** | Phase 2 移行トリガ・拡張要件 | Phase 1 末 |

### 1.3 推奨ヒアリング順序

```
Week 1-2: A 経営層 → 事業目的・投資規模の合意
Week 2-3: F/G 親会社統制/データエンジ → 前提条件（監査アカウント、Producer スキル）
Week 3-4: B 中央 BI チーム → 実装可能性の検証
Week 4-5: C 各アプリ部署 → 個別要件（案件数 × 数日）
Week 5-6: D 業務利用者 → ダッシュ要件
Week 6-7: E/H 監査・セキュリティ → コンプラ要件
Week 7-8: 統合レビュー → ADR 更新・意思決定
```

---

## §2 優先度別クイックリファレンス（P0 / P1 / P2）

### 2.1 P0: 22 項目（Phase 1 決定に必須）

| ID | 対象 | 項目 | 出所 |
|---|---|---|---|
| DP-ORG-01 | B | 中央 BI チームの Phase 1 人員規模（2 名 / 5 名 / 10 名）| §2.1.8 |
| DP-ORG-02 | C | Producer チームのデータエンジニアリング経験度合い | §2.1.8 / §4.2.2.7 |
| DP-ORG-03 | F | 新規「監査アカウント」の生成予定・運用主体 | §5.8 前提 8 |
| DP-ORG-04 | A | Producer 案件数の見通し（Phase 1: 5 / 10 / 20）| §4.5.5 |
| DP-SCOPE-01 | A | 経営層は「1 画面で全 KPI」か「業務領域別に見る」か | §4.2.1.12 |
| DP-SCOPE-02 | D | QuickSight Reader の最終想定数（50 / 100 / 300 名）| §4.5.5 |
| DP-SCOPE-03 | D | 業務利用者の既存 BI（Excel / Tableau 等）と移行方針 | strawman §6.1 |
| DP-ARCH-01 | A/B | Pattern A（Federated）継続 or Pattern B（中央集約）検討 | §2.1.8 |
| DP-ARCH-02 | H | 共通ドメインアカウントを **D-1 新設 / D-2 中央同居 / D-5 持たない** | §4.2.1.X F |
| DP-ARCH-03 | E/H | テナント分離は Lake Formation Data Filter 必須か、アプリ側 WHERE 強制か | §4.2.1.9 |
| DP-COST-01 | A | Phase 1 データプラットフォーム予算枠（月額目安）| §4.5.5 |
| DP-COST-02 | C | SFTP 受領が必要な顧客の数（Transfer Family 採否）| §4.5.5 |
| DP-COST-03 | A | AWS Pricing Calculator での正式試算実施者・タイミング | §4.5.5 |
| DP-SEC-01 | E | 監査担当者は全テナント参照可能とする運用ポリシーが成立するか | §4.2.1.9 |
| DP-SEC-02 | H | PII マスキングは LF セル単位か、ETL 段階の恒久マスキングか | §4.2.1.9 |
| DP-SEC-03 | E/H | 監査ログの保持年数（1 年 / 3 年 / 7 年）| §4.5.5 |
| DP-SEC-04 | H | 顧客テナントデータ削除要件（GDPR/APPI）の期限 | §4.2.1.14 |
| DP-UX-01 | D | 経営層向け「単一 KPI ダッシュ」or「業務領域別ダッシュ」の希望 | §4.2.1.12 |
| DP-UX-02 | E | 監査担当者の特権モード（PII 含む全列表示）を組織として許容できるか | §4.2.1.11 |
| DP-NFR-01 | D | 各ダッシュボードの鮮度 SLA（リアルタイム / 時間次 / 日次）| §4.2.1.13 |
| DP-NFR-02 | C | データのリアルタイム性要件（解約予兆検知の遅延許容）| §4.2.2.7 |
| DP-NFR-03 | F | 前提 6: アカウント追加 +1 が AWS Organizations 運用上許容可能か | strawman §6.1 G-3 |

### 2.2 P1: 31 項目（Phase 1 詳細設計）

| ID | 対象 | 項目 | 出所 |
|---|---|---|---|
| DP-ORG-04 | G | Producer 全体のデータエンジニアリング組織の有無・成熟度 | §4.2.2.7 / §2.1.8 |
| DP-ORG-05 | C | 各アプリの既存 ETL 基盤（cron / Airflow / 自前バッチ）| §4.2.2.7 |
| DP-ORG-06 | E | 既存マスタ（顧客・組織・商品）の所管部署・移管交渉可否 | strawman §6.1 C-3 / D-2 |
| DP-ORG-07 | B | Phase 2 で共通参照データ管理者（役割 5）専任化の見込み | §4.2.1.X |
| DP-SCOPE-04 | A | 全社統合 KPI の変更頻度（月次 / 四半期 / 年次）| §2.1.8 / 新規 |
| DP-SCOPE-05 | H | 顧客テナントの規模想定（1,000 / 2,000 / 3,000）| §4.5.5 |
| DP-SCOPE-06 | C | 顧客企業マスタ / 契約管理システムとの連携方式 | §4.2.2.7 |
| DP-SCOPE-07 | D | ダッシュボード閲覧履歴の監査要件（誰が何を見たか）| §4.2.1.11 |
| DP-ARCH-04 | H | Lake Formation 監査ログのリテンション期間 | §4.2.1.9 |
| DP-ARCH-05 | H | LF キャッシュ 15 分の権限即時反映非対応を運用で許容できるか | §4.2.1.9 |
| DP-ARCH-06 | B | 認証基盤から QuickSight への属性受渡しは SAML / OIDC のどちらか | §4.2.1.11 |
| DP-ARCH-07 | B | SPICE Dataset Owner は Service Role 化するか個人 Account か | §4.2.1.13 |
| DP-ARCH-08 | B | 顧客企業の業務利用者（Phase 2+）の自社ダッシュ提供方式 | §4.2.1.11 |
| DP-COST-04 | A | Phase 2 の SageMaker 利用規模（Inference 常時稼働 yes/no）| §4.5.5 |
| DP-COST-05 | F | インターネット egress の量（Embedded ダッシュ等）| §4.5.5 |
| DP-COST-06 | B | Reserved / Savings Plans の発注タイミング（Phase 1 で確約可能か）| §4.5.5 |
| DP-COST-07 | B | Reader Capacity Pricing に切替えるべき Reader 数の閾値判断 | §4.5.5 |
| DP-SEC-05 | H | クエリ結果の保管期間（業界・コンプラ要件）| §4.2.1.14 |
| DP-SEC-06 | E | 利用者間で「自分の結果のみ参照可」の徹底度合い | §4.2.1.14 |
| DP-SEC-07 | H | クエリ結果からの再エクスポート（ダウンロード）の禁止要件 | §4.2.1.14 |
| DP-SEC-08 | H | Result Reuse Cache の利用可否（PII 含むクエリで再利用される懸念）| §4.2.1.14 |
| DP-SEC-09 | H | 権限変更の反映 SLA（退職・異動時の即時反映必要性）| §4.2.1.11 |
| DP-UX-03 | D | ドリルダウン操作（クリックで詳細遷移）の慣れ度合い | §4.2.1.12 |
| DP-UX-04 | D | 新規ユーザーオンボーディング時間の目安 | §4.2.1.12 |
| DP-UX-05 | D | ダッシュボード棚卸し（未使用の整理）の周期 | §4.2.1.12 |
| DP-UX-06 | D | 既存の BI / ダッシュボードの数とテーマ（棚卸し）| §4.2.1.12 |
| DP-NFR-04 | B | Refresh 失敗時の通知ルート（Slack / Teams / メール）| §4.2.1.13 |
| DP-NFR-05 | E | 監査担当者のダッシュボードは Direct Query で応答時間が許容できるか | §4.2.1.13 |
| DP-NFR-06 | F | 中央 BI アカウントでの災害復旧要件（RTO / RPO）| 新規 |
| DP-NFR-07 | B | Producer 側 PII マスキング等のガバナンス実装意思 | §2.1.8 |
| DP-NFR-08 | H | 前提 9: Catalog 管理者と BI 分析者の人員が重ならない運用が可能か | strawman §6.1 G-5 |

### 2.3 P2: 20 項目（Phase 2 判断・継続監視）

| ID | 対象 | 項目 | 出所 |
|---|---|---|---|
| DP-ORG-08 | B | Phase 2 で中央 BI チーム 5+ 名に増員する見通し | §2.1.8 |
| DP-ORG-09 | B | Phase 2 で共通参照データ管理者（役割 5）専任化 | §4.2.1.X |
| DP-SCOPE-08 | A | Phase 2 の共通参照データに依存する SaaS 製品数（5+ で D-1 再評価）| DP-ADR-003 |
| DP-SCOPE-09 | A | Phase 2 の SPICE 容量見積もり（テナント数増加 + ML 特徴量）| §4.2.1.13 |
| DP-SCOPE-10 | A | Phase 2 で Reader 数が 150 名を超えるか | §4.5.5 |
| DP-ARCH-09 | B | Pattern C（Iceberg / S3 Tables）Phase 2 移行検討トリガ | §2.5 |
| DP-ARCH-10 | B | Pattern B-1/B-2 への切替えトリガ（中央 BI 5+ 名 等）| §2.1.8 |
| DP-ARCH-11 | B | Phase 3+ で Redshift / EMR / Athena Provisioned Capacity 再評価 | DP-ADR-002 |
| DP-ARCH-12 | B | Phase 2 で SageMaker Catalog（SMC）再評価 | DP-ADR-001 |
| DP-ARCH-13 | B | Phase 2 で Athena Result Reuse Cache 導入判断 | §4.2.1.14 |
| DP-COST-08 | A | Phase 2 でのコスト増加（SageMaker + Reader 増）を許容できるか | §4.5.3 |
| DP-SEC-10 | H | Phase 2+ で Trust Center 開設判断（顧客への監査情報開示）| ADR-036 参照 |
| DP-UX-07 | D | Phase 2 で顧客テナント向けダッシュ（QuickSight Embedded）| §4.2.1.11 |
| DP-UX-08 | A | Paginated Reports の必要性（月次レポート $100/月）| §4.5.2 |
| DP-NFR-09 | H | Phase 2 の監査要件変化（PCI DSS / SOC 2 対応）| ADR 参照 |
| DP-NFR-10 | B | Phase 2 で災害復旧 Multi-Region 対応（ADR-051 参照）| §NFR |
| DP-NFR-11 | H | 監査ログ物理分離規制（アクセスログを別アカウントへ）| DP-ADR-003 |
| DP-NFR-12 | B | 中央 Catalog 障害の年 2 回以上停止（D-1 移行トリガ）| DP-ADR-003 |
| DP-NFR-13 | C | Producer 側スキーマ変更で中央 ETL 影響が年 5 件以上（Pattern B 切替検討）| §2.1.7 |
| DP-NFR-14 | B | Phase 3+ で 100+ アプリ規模時の Central Catalog 分離判断 | §4.3 |

---

## §3 対象者別ヒアリング項目

### 3.1 経営層（対象 A）

**主な確認事項**: 事業目的・投資規模・KPI・Phase 計画

| ID | 項目 | 想定回答から次に動くもの |
|---|---|---|
| DP-SCOPE-01 | 「1 画面で全 KPI」か「業務領域別に見る」か | ダッシュ設計（P4 ハブ+詳細 vs P1 巨大単一）|
| DP-SCOPE-04 | 全社統合 KPI の変更頻度 | Pattern B 切替評価 |
| DP-SCOPE-05 | 顧客テナントの規模想定 | データ量試算・SPICE 容量 |
| DP-SCOPE-08〜10 | Phase 2 の増加見通し（共通データ / SPICE / Reader）| Phase 2 予算 |
| DP-COST-01 | Phase 1 予算枠 | 必須/任意判断、レベル 1〜3 最適化選択 |
| DP-COST-03 | Pricing Calculator 実施者・タイミング | 正式試算の workflow |
| DP-COST-08 | Phase 2 コスト増加の許容度 | Phase 計画 |
| DP-ORG-04 | Producer 案件数の見通し | 全体コストの主要変数 |
| DP-UX-08 | Paginated Reports の必要性 | +$100/月の判断 |

### 3.2 中央 BI チーム（対象 B、新設想定）

**主な確認事項**: 実装可能性・スキル・工数・運用ルール

| ID | 項目 | 想定回答から次に動くもの |
|---|---|---|
| DP-ORG-01 | Phase 1 人員規模（2 / 5 / 10 名）| Pattern A 継続の可否（B-1 は 5+ 必要）|
| DP-ORG-07/08 | Phase 2 で共通参照データ管理者専任化 | D-1 移行トリガ |
| DP-ARCH-01 | Pattern A 継続 or B 検討 | 全体アーキ確定 |
| DP-ARCH-06 | SAML / OIDC 属性受渡し | QuickSight Session Tag 設計 |
| DP-ARCH-07 | SPICE Dataset Owner の Role 化 | セキュリティ設計 |
| DP-ARCH-08 | 顧客テナント向けダッシュ提供方式 | QuickSight Embedded vs Anonymous |
| DP-ARCH-09〜13 | Phase 2 の技術評価トリガ（Iceberg / Provisioned 等）| 継続監視項目 |
| DP-COST-06 | Reserved / Savings Plans 発注タイミング | -30%削減 |
| DP-COST-07 | Reader Capacity Pricing 切替閾値 | Named vs Capacity |
| DP-NFR-04 | Refresh 失敗の通知ルート | 運用設計 |
| DP-NFR-06 | 中央 BI アカウントの災害復旧 | Multi-Region 検討 |
| DP-NFR-07 | Producer 側 PII マスキングガバナンス | Pattern B 切替評価 |

### 3.3 各アプリ部署（対象 C、Producer / データオーナー候補）

**主な確認事項**: ETL 実装可能性・既存資産・案件別要件

| ID | 項目 | 想定回答から次に動くもの |
|---|---|---|
| DP-ORG-02 | Producer チームのデータエンジ経験 | Pattern B 検討トリガ |
| DP-ORG-05 | 既存 ETL 基盤（cron / Airflow）| 移行戦略 |
| DP-SCOPE-06 | 顧客企業マスタ / 契約管理システム連携 | 共通ドメイン設計 |
| DP-COST-02 | SFTP 受領必要な顧客数（アプリ別）| Transfer Family 採否 |
| DP-NFR-02 | リアルタイム性要件（解約予兆等）| ストリーム取込採否 |
| DP-NFR-13 | Producer スキーマ変更頻度 | Pattern B 影響評価 |

### 3.4 業務利用者（対象 D、CS / PM / マーケ / 経営層閲覧）

**主な確認事項**: ダッシュ要件・UX・利用パターン

| ID | 項目 | 想定回答から次に動くもの |
|---|---|---|
| DP-SCOPE-02 | Reader 想定数 | ライセンス方式・SPICE 容量 |
| DP-SCOPE-03 | 既存 BI（Excel / Tableau）移行方針 | 移行戦略 |
| DP-SCOPE-07 | 閲覧履歴の監査要件 | CloudTrail Data Events 設定 |
| DP-UX-01 | 経営層向けダッシュ形式 | ダッシュボード粒度設計 |
| DP-UX-03 | ドリルダウン操作の慣れ | P4 ハブ+詳細パターン採否 |
| DP-UX-04 | 新規ユーザーオンボーディング時間 | ダッシュ数の上限判断 |
| DP-UX-05 | 棚卸し周期 | 細分化リスク許容度 |
| DP-UX-06 | 既存 BI / ダッシュの棚卸し | 移行時のダッシュ統合 |
| DP-UX-07 | 顧客テナント向けダッシュ（Phase 2）| Embedded 検討 |
| DP-NFR-01 | 鮮度 SLA（リアルタイム / 時間次 / 日次）| Refresh スケジュール設計 |

### 3.5 監査担当者（対象 E）

**主な確認事項**: 監査ログ要件・PII 参照権限・アクセス範囲

| ID | 項目 | 想定回答から次に動くもの |
|---|---|---|
| DP-ORG-06 | 既存マスタの所管部署・移管交渉 | 共通ドメイン設計 |
| DP-ARCH-03 | テナント分離: LF Data Filter vs アプリ側 WHERE | LF 運用設計 |
| DP-SEC-01 | 監査担当の全テナント参照可能ポリシー | Grant 設計 |
| DP-SEC-03 | 監査ログの保持年数 | CloudTrail Lake / Object Lock |
| DP-SEC-06 | 「自分の結果のみ」の徹底度 | IAM / バケットポリシー設計 |
| DP-UX-02 | 監査担当の特権モード許容 | CLS 設計 |
| DP-NFR-05 | 監査 Direct Query の応答時間許容 | SPICE 採否 |

### 3.6 親会社統制チーム / 情シス（対象 F）

**主な確認事項**: 監査アカウント連携・ネットワーク・Organizations 前提

| ID | 項目 | 想定回答から次に動くもの |
|---|---|---|
| DP-ORG-03 | 新規監査アカウントの計画 | Option B 成立可否（決定的）|
| DP-NFR-03 | アカウント追加 +1 の許容可否 | 全体アーキ確定 |
| DP-COST-05 | インターネット egress の量 | 中央 BI コスト試算 |
| DP-NFR-06 | 災害復旧要件（RTO / RPO）| Multi-Region 検討 |

### 3.7 データエンジニアリング組織（対象 G、横断）

**主な確認事項**: ETL パターン統一・スキル基盤・技術判断

| ID | 項目 | 想定回答から次に動くもの |
|---|---|---|
| DP-ORG-04 | Producer 全体のデータエンジ組織成熟度 | Pattern A vs B 選択 |
| DP-ARCH-09/10 | Iceberg / Pattern B 移行トリガ | Phase 2 判断 |

### 3.8 セキュリティ / コンプラ担当（対象 H）

**主な確認事項**: PII 保護・削除要件・監査ログ・規制対応

| ID | 項目 | 想定回答から次に動くもの |
|---|---|---|
| DP-ARCH-02 | 共通ドメインアカウント D-1/D-2/D-5 | DP-ADR-003 確定 |
| DP-ARCH-03 | テナント分離方式 | LF 運用設計 |
| DP-ARCH-04 | LF 監査ログのリテンション | 監査アカウント設計 |
| DP-ARCH-05 | LF キャッシュ 15 分の許容 | 権限剥奪 SLA |
| DP-SEC-02 | PII マスキング方式（LF セル / ETL 恒久）| データ設計 |
| DP-SEC-03 | 監査ログ保持年数 | Object Lock 設定 |
| DP-SEC-04 | GDPR/APPI 削除要件の期限 | Cryptographic Erasure 検討 |
| DP-SEC-05 | クエリ結果の保管期間 | Lifecycle 設計 |
| DP-SEC-07 | 再エクスポート禁止要件 | DLP 対応 |
| DP-SEC-08 | Result Reuse Cache 利用可否 | Cache 設定 |
| DP-SEC-09 | 権限変更反映 SLA | Permissions Dataset 更新頻度 |
| DP-SEC-10 | Trust Center 開設判断（Phase 2+）| ADR-036 参照 |
| DP-NFR-08 | Catalog 管理者と BI 分析者の人員分離 | Option B 成立条件 |
| DP-NFR-09 | Phase 2 監査要件変化（PCI DSS / SOC 2）| コンプラ計画 |
| DP-NFR-11 | 監査ログ物理分離規制 | D-1 移行トリガ |

---

## §4 トピック別マスタリスト

### 4.1 組織・チーム構成（DP-ORG-01〜09）

| # | 項目 | P |
|---|---|---|
| ORG-01 | 中央 BI チーム Phase 1 人員規模 | P0 |
| ORG-02 | Producer チームのデータエンジ経験 | P0 |
| ORG-03 | 新規監査アカウントの計画 | P0 |
| ORG-04 | Producer 案件数の見通し | P0 |
| ORG-05 | Producer 全体のデータエンジ組織成熟度 | P1 |
| ORG-06 | 既存 ETL 基盤（cron / Airflow）| P1 |
| ORG-07 | 既存マスタの所管部署・移管交渉 | P1 |
| ORG-08 | Phase 2 で共通参照データ管理者専任化 | P2 |
| ORG-09 | Phase 2 で中央 BI チーム 5+ 名 | P2 |

### 4.2 スコープ・データ範囲（DP-SCOPE-01〜10）

| # | 項目 | P |
|---|---|---|
| SCOPE-01 | 経営層のダッシュ形式（単一 vs 業務領域別）| P0 |
| SCOPE-02 | QuickSight Reader 最終想定数 | P0 |
| SCOPE-03 | 既存 BI 移行方針 | P0 |
| SCOPE-04 | 全社統合 KPI の変更頻度 | P1 |
| SCOPE-05 | 顧客テナントの規模想定 | P1 |
| SCOPE-06 | 顧客企業マスタ / 契約管理システム連携 | P1 |
| SCOPE-07 | 閲覧履歴の監査要件 | P1 |
| SCOPE-08 | Phase 2 共通参照データ依存 SaaS 数 | P2 |
| SCOPE-09 | Phase 2 SPICE 容量見積もり | P2 |
| SCOPE-10 | Phase 2 Reader 150 名超か | P2 |

### 4.3 アーキテクチャ選択（DP-ARCH-01〜13）

| # | 項目 | P |
|---|---|---|
| ARCH-01 | Pattern A 継続 or Pattern B 検討 | P0 |
| ARCH-02 | 共通ドメイン D-1/D-2/D-5 | P0 |
| ARCH-03 | テナント分離: LF Data Filter vs アプリ側 WHERE | P0 |
| ARCH-04 | LF 監査ログのリテンション | P1 |
| ARCH-05 | LF キャッシュ 15 分の許容 | P1 |
| ARCH-06 | SAML / OIDC 属性受渡し | P1 |
| ARCH-07 | SPICE Dataset Owner の Role 化 | P1 |
| ARCH-08 | 顧客テナント向けダッシュ提供方式 | P1 |
| ARCH-09 | Pattern C（Iceberg）Phase 2 移行トリガ | P2 |
| ARCH-10 | Pattern B 切替トリガ | P2 |
| ARCH-11 | Redshift / EMR / Athena Provisioned Phase 3+ | P2 |
| ARCH-12 | SageMaker Catalog（SMC）Phase 2 再評価 | P2 |
| ARCH-13 | Athena Result Reuse Cache 導入判断 | P2 |

### 4.4 コスト・規模（DP-COST-01〜08）

| # | 項目 | P |
|---|---|---|
| COST-01 | Phase 1 予算枠 | P0 |
| COST-02 | SFTP 受領必要な顧客数 | P0 |
| COST-03 | Pricing Calculator 実施者 | P0 |
| COST-04 | Phase 2 SageMaker 利用規模 | P1 |
| COST-05 | インターネット egress の量 | P1 |
| COST-06 | Reserved / Savings Plans 発注 | P1 |
| COST-07 | Reader Capacity Pricing 切替閾値 | P1 |
| COST-08 | Phase 2 コスト増加許容 | P2 |

### 4.5 セキュリティ・コンプライアンス（DP-SEC-01〜10）

| # | 項目 | P |
|---|---|---|
| SEC-01 | 監査担当の全テナント参照ポリシー | P0 |
| SEC-02 | PII マスキング方式（LF セル / ETL 恒久）| P0 |
| SEC-03 | 監査ログ保持年数 | P0 |
| SEC-04 | GDPR/APPI 削除要件の期限 | P0 |
| SEC-05 | クエリ結果の保管期間 | P1 |
| SEC-06 | 「自分の結果のみ」徹底度 | P1 |
| SEC-07 | 再エクスポート禁止要件 | P1 |
| SEC-08 | Result Reuse Cache 利用可否 | P1 |
| SEC-09 | 権限変更反映 SLA | P1 |
| SEC-10 | Trust Center 開設判断（Phase 2+）| P2 |

### 4.6 UX・ダッシュボード（DP-UX-01〜08）

| # | 項目 | P |
|---|---|---|
| UX-01 | 経営層向けダッシュ形式 | P0 |
| UX-02 | 監査担当の特権モード許容 | P0 |
| UX-03 | ドリルダウン操作の慣れ | P1 |
| UX-04 | 新規ユーザーオンボーディング時間 | P1 |
| UX-05 | 棚卸し周期 | P1 |
| UX-06 | 既存 BI / ダッシュの棚卸し | P1 |
| UX-07 | 顧客テナント向けダッシュ（Phase 2）| P2 |
| UX-08 | Paginated Reports の必要性 | P2 |

### 4.7 非機能・SLA・運用（DP-NFR-01〜14）

| # | 項目 | P |
|---|---|---|
| NFR-01 | ダッシュボードの鮮度 SLA | P0 |
| NFR-02 | データのリアルタイム性要件 | P0 |
| NFR-03 | アカウント追加 +1 の許容 | P0 |
| NFR-04 | Refresh 失敗の通知ルート | P1 |
| NFR-05 | 監査 Direct Query の応答時間許容 | P1 |
| NFR-06 | 中央 BI アカウントの災害復旧 | P1 |
| NFR-07 | Producer 側 PII マスキング実装意思 | P1 |
| NFR-08 | Catalog 管理者と BI 分析者の人員分離 | P1 |
| NFR-09 | Phase 2 監査要件変化（PCI DSS / SOC 2）| P2 |
| NFR-10 | Phase 2 災害復旧 Multi-Region 対応 | P2 |
| NFR-11 | 監査ログ物理分離規制 | P2 |
| NFR-12 | 中央 Catalog 障害の年 2 回以上停止 | P2 |
| NFR-13 | Producer スキーマ変更で中央 ETL 影響年 5+ 件 | P2 |
| NFR-14 | Phase 3+ 100+ アプリ規模時の Central Catalog 分離 | P2 |

---

## §5 統合マスタ表（ID 付き）

Excel / Notion / スプレッドシート等で管理する用の完全リスト。

### 5.1 マスタ表フォーマット

| ID | カテゴリ | 優先度 | 対象者 | 項目（質問文）| 想定回答例 | 状態 | 回答内容 | 決定事項 | 出所 | 更新日 |
|---|---|---|---|---|---|---|---|---|---|---|

### 5.2 マスタ表本体（抜粋、Excel 化推奨）

以下は §2〜§4 で列挙した項目の代表例。全 73 項目は本ドキュメントの §2 と §4 を参照。

| ID | 優先度 | 対象 | 項目 | 状態 |
|---|---|---|---|---|
| DP-ORG-01 | P0 | B | 中央 BI チーム Phase 1 人員規模 | 🔴 |
| DP-ORG-02 | P0 | C | Producer チームのデータエンジ経験 | 🔴 |
| DP-ORG-03 | P0 | F | 新規監査アカウントの計画 | 🔴 |
| DP-ORG-04 | P0 | A | Producer 案件数の見通し | 🔴 |
| DP-SCOPE-01 | P0 | A | 経営層のダッシュ形式 | 🔴 |
| DP-SCOPE-02 | P0 | D | QuickSight Reader 想定数 | 🔴 |
| DP-SCOPE-03 | P0 | D | 既存 BI 移行方針 | 🔴 |
| DP-ARCH-01 | P0 | A/B | Pattern A 継続 or B 検討 | 🔴 |
| DP-ARCH-02 | P0 | H | 共通ドメイン D-1/D-2/D-5 | 🟢 D-2 採用（DP-ADR-003）|
| DP-ARCH-03 | P0 | E/H | テナント分離方式 | 🔴 |
| DP-COST-01 | P0 | A | Phase 1 予算枠 | 🔴 |
| DP-COST-02 | P0 | C | SFTP 受領必要な顧客数 | 🔴 |
| DP-COST-03 | P0 | A | Pricing Calculator 実施者 | 🔴 |
| DP-SEC-01 | P0 | E | 監査担当の全テナント参照ポリシー | 🔴 |
| DP-SEC-02 | P0 | H | PII マスキング方式 | 🔴 |
| DP-SEC-03 | P0 | E/H | 監査ログ保持年数 | 🔴 |
| DP-SEC-04 | P0 | H | GDPR/APPI 削除要件 | 🔴 |
| DP-UX-01 | P0 | D | 経営層向けダッシュ形式 | 🔴 |
| DP-UX-02 | P0 | E | 監査担当の特権モード | 🔴 |
| DP-NFR-01 | P0 | D | ダッシュボードの鮮度 SLA | 🔴 |
| DP-NFR-02 | P0 | C | データのリアルタイム性要件 | 🔴 |
| DP-NFR-03 | P0 | F | アカウント追加 +1 の許容 | 🔴 |

（P1: 31 項目、P2: 20 項目は §2.2 / §2.3 参照）

---

## §6 ヒアリング準備リスト

### 6.1 実施前チェック

- [ ] 対象者ごとに §3 の項目を抜粋し、質問シート化
- [ ] [hearing-slide-deck.md](hearing-slide-deck.md) の該当スライドを用意
- [ ] 事前資料（strawman-proposal.md）を対象者に共有
- [ ] 具体例（経費精算 SaaS）で説明する準備

### 6.2 実施時のポイント

- **P0 項目は必ず全問聞き切る**
- P1 は 8 割目標、残りは追加ヒアリング
- P2 は「聞けたら聞く」、Phase 1 末尾で再訪問
- **回答例（strawman §6.1 の暫定回答）を提示**して収束を早める
- 想定外の回答があれば **ADR に反映すべきかその場で判断**

### 6.3 実施後

- [ ] 統合マスタ表（§5）に回答を記録
- [ ] 決定事項は該当 ADR に反映（DP-ADR-004 等を新設）
- [ ] 仮案（strawman-proposal.md）を更新
- [ ] 未回答項目を再ヒアリング候補に

---

## §7 参照ドキュメント

| ドキュメント | 参照理由 |
|---|---|
| [strawman-proposal.md §6.1](strawman-proposal.md) | 原本の組織別ヒアリング項目（A-H）|
| [hearing-slide-deck.md](hearing-slide-deck.md) | 当日提示用スライド 45 枚 |
| [account-architecture-analysis.md](account-architecture-analysis.md) | 各 §4.2.1.X / §4.5.5 の残課題の出所 |
| [architecture-alternatives-comparison.md](architecture-alternatives-comparison.md) | §2.1.8 Pattern B 採用条件 |
| [adr/DP-ADR-001〜003](adr/) | 既存の意思決定記録 |

---

## §8 改訂履歴

| 日付 | 改訂内容 |
|---|---|
| 2026-07-02 | 初版作成。散在していた 73 項目を統合、対象者別 / トピック別 / 優先度別に 4 索引化 |
