# ADR-067: 認可判定ログ + アクセス再認証（IGA ガバナンス強化）

- **ステータス**: Proposed（**スタブ** — 2026-08-12 網羅性再監査で起票。方式確定は B-AUTHZLOG-1 / B-IGA-REC-1 回答 + U9 監査設計時）
- **日付**: 2026-08-12 作成
- **決定（方向性）**: **① 認可判定（Backend DB エンタイトルメント）の「なぜ許可/拒否したか」を判定ログとして記録し、② 3 層管理スコープ・テナント管理者・NHI に対する定期アクセス再認証（recertification）を軽量 IGA に組み込む。** 現行の 7 年不変監査（認証イベント中心）を「認可の説明可能性」と「権限棚卸しの実施記録」で補完する。
- **関連**: [ADR-037 軽量 IGA / Shared Responsibility](037-shared-responsibility-and-lightweight-iga.md) / [ADR-038 ユーザ管理画面 3 層スコープ](038-tenant-admin-portal.md) / [U7 §7.7.1 監査ログ 7 年 D-U7-13](../basic-design/07-security-compliance-design.md) / [U3 D3-14 粗粒度認可](../basic-design/03-identity-provisioning-design.md) / [U9 §9.3 ログ](../basic-design/09-operations-observability-design.md) / hearing **B-AUTHZLOG-1 / B-IGA-REC-1**

---

## Context

- 監査ログ（D-U7-13）は**認証イベント中心**。SOC 2 CC6.1 / ISO 27001 A.8/A.9 は**認可判定の証跡**（誰が・何に・なぜアクセスできたか、ポリシー版・入力）を求める傾向が強まっている。
- 認可は Backend DB エンタイトルメント（D3-14、粗粒度）で行うが、**判定の決定ログを出す仕組みが未設計** → 「最小権限を強制している」ことを監査で証明できない。
- **アクセス再認証（recertification）**: ADR-037 の軽量 IGA はあるが、**3 層管理スコープ・テナント管理者・NHI の定期棚卸し（誰が・いつ・判定を記録）が未定義**。ISO 27001 A.9.2.5 は一律年次でなくリスクベースの実施と**完了記録**を要求。

## Options

| 案 | 内容 | 評価 |
|---|---|---|
| **A. 現状（認証監査のみ）** | authZ 判定ログ・recert なし | 監査で最小権限/棚卸しを証明不能 |
| **B. 判定ログ + 軽量 recert（推奨方向）** | idm-api の認可判定に決定ログ（対象/スコープ/結果/理由/ポリシー版）を付与 + 3 層 × 四半期 or リスクベースの recert キャンペーン（reviewer/日付/判定を記録） | 自作コスト中・既存監査基盤に相乗り |
| **C. 商用 IGA/PDP 製品** | 外部 PDP + IGA スイート | Phase 1 予算外。将来（[ReBAC/Cedar/OPA 検討](../basic-design/03-identity-provisioning-design.md)）と連動 |

## Decision（TBD）

- **方向 = B**。判定ログは U9 ログ 3 層（Hot/Cold）に相乗り、recert は軽量 IGA（ADR-037）の運用に組み込む。
- **確定前に必要**: ① **B-AUTHZLOG-1**（顧客・監査人が要求する認可証跡の粒度・保持）② **B-IGA-REC-1**（各層の再認証頻度・実施主体 = 弊社運用者 / テナント管理者 / 監査、共有責任分界）③ 決定ログの PII 非搭載（U5 §5.1.4 チェックリストと整合）。

## Consequences（想定）

- **Positive**: 最小権限の証明 / 孤立権限・過剰権限の定期是正 / SOC2・ISO 監査対応。将来の externalized authorization（OpenFGA/Cedar/OPA）の決定ログ移行が容易。
- **Negative / 受容**: 判定ログの量（サンプリング/集約要）+ recert 運用の負荷（軽量 IGA の範囲で吸収）。

## Open Items

- 判定ログの量とサンプリング方針（全 authZ 判定 or 拒否 + 高権限のみ）。
- recert の対象に NHI（[ADR-066](066-non-human-identity-governance.md)）を含める範囲。
- 忘れられる権利 vs 監査保持（[hearing B-RTBF-1](../requirements/hearing-checklist.md)）との整合 — 判定ログ内の主体識別子の仮名化方針。
