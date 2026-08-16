# ADR-067: 認可判定ログ + アクセス再認証（IGA ガバナンス強化）

- **ステータス**: Proposed（2026-08-12 起票 → 2026-08-12 本設計化。ログスキーマ・サンプリング・recert 枠組みは確定、粒度と実施主体の最終確定は B-AUTHZLOG-1 / B-IGA-REC-1 回答後）
- **日付**: 2026-08-12 作成・本設計化
- **決定**: **① idm-api の認可判定に「決定ログ」（対象/スコープ/結果/理由/ポリシー版、PII 非搭載）を出し U9 ログ 3 層に相乗りさせる。既定サンプリング = 拒否 + 高権限操作は全件、read 許可は集約。② 3 層管理スコープ・テナント管理者・NHI のアクセス再認証（recertification）を軽量 IGA（[ADR-037](037-shared-responsibility-and-lightweight-iga.md)）に組込み、リスクベース頻度 + 完了記録（reviewer/日付/判定）を残す。**
- **関連**: [ADR-037 軽量 IGA](037-shared-responsibility-and-lightweight-iga.md) / [ADR-038 3 層スコープ](038-tenant-admin-portal.md) / [ADR-066 NHI 台帳](066-non-human-identity-governance.md) / [U7 §7.7.1 監査ログ D-U7-13](../basic-design/07-security-compliance-design.md) / [U3 D3-14 粗粒度認可](../basic-design/03-identity-provisioning-design.md) / [U9 §9.3 ログ](../basic-design/09-operations-observability-design.md) / hearing **B-AUTHZLOG-1 / B-IGA-REC-1** / WBS **DU-U9O-06**

---

## Context

- 監査ログ（D-U7-13）は**認証イベント中心**。SOC 2 CC6.1 / ISO 27001 A.8/A.9 は**認可判定の証跡**（誰が・何に・なぜ・ポリシー版）を求める傾向。認可は Backend DB エンタイトルメント（D3-14 粗粒度）で行うが**決定ログ機構が未設計** → 最小権限の強制を監査で証明できない。
- **アクセス再認証**: ADR-037 軽量 IGA はあるが**3 層管理スコープ・テナント管理者・NHI の定期棚卸し（誰が・いつ・判定を記録）が未定義**。ISO 27001 A.9.2.5 = リスクベース + 完了記録。

## Decision

### 1. 認可判定ログ（decision log）

**出力元 = idm-api（認可判定を行う Backend）**。判定ごとに構造化ログを出す:

| フィールド | 内容 |
|---|---|
| `ts` / `request_id` | 時刻 / 相関 ID |
| `subject` | 判定対象（`sub` — **PII 非搭載**、U5 §5.1.4 と整合） |
| `actor` | 操作主体（管理者/テナント管理者/CC クライアント） |
| `resource` / `action` | 対象リソース × 操作 |
| `decision` | `allow` / `deny` |
| `reason` | 根拠（付与エンタイトルメント / スコープ不足 / テナント不一致 等） |
| `policy_version` | 適用したエンタイトルメント定義の版 |

- **サンプリング（既定）**: `deny` は全件 / 高権限操作（`idm:*:write`・削除・権限変更）の `allow` は全件 / 一般 read の `allow` は集約（件数メトリクス + 逸脱時のみ詳細）。**量の律速を避けつつ「なぜ許可したか」を高リスク面で担保**。
- **保管**: U9 ログ 3 層に相乗り（Hot 90 日 / Cold WORM。D-U9-05）。scrubbing 通過後保存（D-U7-07）。
- **将来**: externalized authorization（OpenFGA/Cedar/OPA、U3 将来検討）へ移行しても decision log の形は不変 → PDP 決定ログへ素直に接続。

### 2. アクセス再認証（recertification）キャンペーン

| 対象 | 実施主体（既定） | 頻度（既定・リスクベース） |
|---|---|---|
| L1 基盤運用者スコープ（P-1） | 弊社 Security Lead | 四半期 |
| L2 テナント管理者権限 | テナント管理者（自テナント）+ 弊社サンプリング監査 | 半期 |
| L3 アプリ/機能ロール | アプリオーナー | 年次 or 変更時 |
| NHI（[ADR-066](066-non-human-identity-governance.md)） | NHI owner | 四半期（孤立検知と連動） |

- **完了記録**: reviewer / 日付 / 対象 / 判定（継続 or 剥奪）を監査ログに残す（ISO A.9.2.5）。剥奪は ADR-064/066 の失効機構で伝播。
- **実装**: ユーザ管理画面（ADR-038）に recert ビューを追加、または軽量バッチ + レビュー記録テーブル。

### 3. 確定に必要（粒度・主体のみ hearing 依存）

- **B-AUTHZLOG-1**: 顧客/監査人が要求する認可証跡の粒度・保持期間。
- ~~**B-IGA-REC-1**~~: ✅ **範囲確定（2026-08-16）** — 「**Keycloak のユーザの話であれば必要。アプリの話であればアプリで検討**」。**定期棚卸し（recertification）の対象を本基盤が保持する ID・権限（Keycloak ユーザ / 3 層管理スコープ / 基盤側 NHI）に限定**し、**アプリ内部の権限の棚卸しはアプリ側責任**とする（責任分担表に明記）。残る未決は**頻度と実施主体**のみ（年 1 回 / 半期、弊社主導 or テナント主導）。

## Consequences

- **Positive**: 最小権限の証明 / 過剰・孤立権限の定期是正 / SOC2・ISO 対応 / PDP 移行への布石。
- **Negative / 受容**: 判定ログの量（サンプリングで抑制）+ recert 運用の負荷（軽量 IGA 範囲）。

## Alternatives Considered

| 案 | 判定 |
|---|---|
| 認証監査のみ（現状） | 却下（最小権限/棚卸しを証明不能） |
| **判定ログ + 軽量 recert（採用）** | **採用**（既存監査基盤・ADR-037 に相乗り） |
| 商用 IGA/PDP 製品 | Phase 2 以降（予算外・将来の externalized authz と連動） |

## Open Items

- 判定ログのサンプリング率の実測調整（10M 規模の量）。
- recert 対象への NHI 包含範囲（ADR-066 と合同）。
- decision log 内 `sub` の仮名化と RTBF（[hearing B-RTBF-1](../requirements/hearing-checklist.md)）の整合。
