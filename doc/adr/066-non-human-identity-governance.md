# ADR-066: 非人間ID（NHI）ガバナンス

- **ステータス**: Proposed（**スタブ** — 2026-08-12 網羅性再監査で起票。方式確定は B-NHI-1 回答 + IGA 設計時）
- **日付**: 2026-08-12 作成
- **決定（方向性）**: **本基盤が生成・保持する非人間ID（M2M クライアント資格情報・サービスアカウント・IRSA/Pod Identity ワークロード・SCIM/JIT コネクタ）を、棚卸し・所有者・目的・最小権限・ローテーション・失効の観点で統制する「NHI ガバナンス」を Phase 1 の運用設計に組み込む。**
- **関連**: [U7 §7.5 IRSA/Workload D-U7-09](../basic-design/07-security-compliance-design.md) / [ADR-041 Workload Identity](041-workload-identity-spiffe.md) / [ADR-037 Shared Responsibility / 軽量 IGA](037-shared-responsibility-and-lightweight-iga.md) / [U5 §5.8 idm:* スコープ](../basic-design/05-token-session-authz-design.md) / hearing **B-NHI-1**

---

## Context

- 1000+ テナント × M2M アプリ（Client Credentials）+ IRSA/Pod Identity + SCIM Facade/JIT コネクタ + Webhook Dispatcher = **人間IDの数十倍規模の非人間ID**が発生する。
- 現行設計は個別の技術決定（IRSA=D-U7-09、client_secret 90 日ローテ、private_key_jwt 昇格=D-U7-10b）を持つが、**NHI 全体の「台帳・所有者・棚卸し・孤立検知」というガバナンス層が不在**。
- 業界動向（2025-26）: NHI:人間 > 80:1・前年比 +44%、クラウドのマシンIDの数%が既定で管理者権限。NHI ガバナンス（CSA / ISPM）が最も見落とされる統制領域。

## Options

| 案 | 内容 | 評価 |
|---|---|---|
| **A. 個別決定のまま（現状）** | 各 NHI を個別に設定・ローテ | 台帳・所有者・孤立検知が無く、スケール時に統制不能 |
| **B. 軽量 NHI 台帳 + 規約（推奨方向）** | ADR-037 軽量 IGA の一部として NHI 台帳（種別・所有者・目的・スコープ・ローテ周期・最終使用）+ 命名規約 + 孤立検知バッチ | 自作コスト小・既存 IGA/監視に相乗り |
| **C. 商用 NHI/ISPM 製品** | 専用ガバナンス製品導入 | Phase 1 予算外。Phase 2 以降の選択肢 |

## Decision（TBD）

- **方向 = B**（軽量 NHI 台帳 + 規約、ADR-037 の傘下）。
- **確定前に必要**: ① **B-NHI-1**（顧客側 M2M クライアントの所有者・棚卸し責任分界、共有責任のどちら側か）② NHI 台帳の SSOT（idmap 系 authz DB 同居 or 別）③ 孤立検知（最終使用が閾値超のクライアント/SA の失効フロー）と ADR-064 削除伝播の整合。

## Consequences（想定）

- **Positive**: 資格情報スプロールの可視化 / 最小権限と定期ローテの機械強制 / 監査（SOC2/ISO）での NHI 証跡。
- **Negative / 受容**: 台帳の維持運用 + 所有者アサインの運用負荷（軽量 IGA の範囲で吸収）。

## Open Items

- Client Credentials の所有者モデル（テナント × アプリ）と失効時の連鎖（[ADR-064](064-deprovisioning-propagation-outbox.md) と同機構で伝播できるか）。
- IETF WIMSE（ワークロードID Token、2024 WG）の姿勢 — IRSA（AWS 限定）→ 将来ポータブル化の余地を台帳設計で殺さない。
- AI エージェント/エージェンティックID（[hearing B-AGENT-1](../requirements/hearing-checklist.md)）は NHI の特殊系として本 ADR の枠組みで受ける。
