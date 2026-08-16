# ADR-066: 非人間ID（NHI）ガバナンス

- **ステータス**: **Accepted（縮小、2026-08-17）** — B-NHI-1 に回答が出た（「機械通信＝API から API の呼び出しであれば**アプリ側で管理**」）。**本 ADR の適用範囲を「本基盤自身が発行・保持する NHI」に限定**し、テナント業務アプリ間の M2M 資格情報はアプリ側責任として**対象外**とする。台帳スキーマ・命名規約・孤立検知は本基盤スコープ分のみ実装
- **日付**: 2026-08-12 作成・本設計化
- **決定**: **本基盤が生成・保持する非人間ID（NHI）を「軽量 NHI 台帳 + 命名規約 + 孤立検知バッチ + 失効伝播」で統制する（案 B、[ADR-037](037-shared-responsibility-and-lightweight-iga.md) 軽量 IGA の傘下）。台帳は authz 系 Aurora に同居し、失効は ADR-064 の outbox 機構で伝播する。** 商用 NHI/ISPM 製品は Phase 2 以降の選択肢。
- **関連**: [U7 §7.5 IRSA/Workload D-U7-09](../basic-design/07-security-compliance-design.md) / [ADR-041 Workload Identity](041-workload-identity-spiffe.md) / [ADR-037 軽量 IGA](037-shared-responsibility-and-lightweight-iga.md) / [ADR-064 失効伝播 outbox](064-deprovisioning-propagation-outbox.md) / [U5 §5.8 idm:* スコープ](../basic-design/05-token-session-authz-design.md) / [U9 §9.4 Runbook](../basic-design/09-operations-observability-design.md) / hearing **B-NHI-1** / WBS **DU-U7-10**

---

## Context

- 1000+ テナント × M2M アプリ（Client Credentials）+ IRSA/Pod Identity + SCIM Facade/JIT コネクタ + Webhook Dispatcher + outbox/shadow 制御 Lambda = **人間 ID の数十倍規模の NHI**。
- 現行は個別の技術決定（IRSA=D-U7-09、client_secret 90 日ローテ、private_key_jwt 昇格=D-U7-10b）を持つが、**NHI 全体の台帳・所有者・棚卸し・孤立検知のガバナンス層が不在**。
- 業界（2025-26）: NHI:人間 > 80:1・前年比 +44%、クラウドマシン ID の数%が既定管理者権限。NHI ガバナンス（CSA / ISPM）が最も見落とされる統制領域。

## Decision（案 B = 軽量 NHI 台帳）

### 1. NHI 台帳スキーマ（authz 系 Aurora 同居、ADR-063 ブランドローカル）

| 列 | 内容 |
|---|---|
| `nhi_id` | 一意 ID |
| `type` | `oidc-client`（M2M）/ `service-account` / `irsa-role` / `pod-identity` / `connector`（SCIM/JIT）/ `glue-lambda` |
| `owner` | 責任者（人間ユーザ or チーム。**必須・空は CI で拒否**） |
| `tenant_id` / `brand_id` | 帰属（横断は null） |
| `purpose` | 用途（自由記述 + 分類） |
| `scopes` | 付与スコープ（`idm:*` 等、最小権限の実体） |
| `secret_type` | `client_secret` / `private_key_jwt` / `irsa`（無秘密） |
| `rotation_period` / `last_rotated_at` | ローテ周期と最終ローテ |
| `last_used_at` | 最終使用（孤立検知の起点） |
| `status` | `active` / `disabled` / `retired` |

### 2. 命名規約

- OIDC クライアント: `nhi-<type>-<tenant|shared>-<purpose>`（例 `nhi-m2m-t042-expense`）。
- IRSA/SA: 既存 IRSA 規約（D-U7-09）に `nhi_id` タグを付与し台帳と突合。

### 3. 孤立検知バッチ（ROSA infra Pool CronJob、D3-08/D-U9-17 と同基盤）

- **`last_used_at` が閾値（既定 90 日）超**の `active` NHI を検出 → owner に通知 → 猶予後に `disabled`。
- **owner 不在（退職）**の NHI を検出 → 再アサイン要求。
- **ローテ期限超過**の secret を検出 → 強制ローテ or 失効。

### 4. 失効伝播（ADR-064 機構の再利用）

- NHI 失効（`disabled`/`retired`）は **outbox → EventBridge → 該当リソース無効化**（OIDC クライアント disable / IRSA ロール剥奪）。ADR-064 の `user.deprovisioned` と同じ必達 + 冪等 + リコンサイル。

### 5. 確定に必要（責任分界のみ hearing 依存）

- ~~**B-NHI-1**~~: ✅ **回答済み（2026-08-16）** — 「API から API の呼び出しであればアプリで管理の認識」。**テナント業務アプリ間の M2M は本基盤の管理対象外**。本基盤が管理するのは ① 基盤自身のサービスアカウント（idm-api / SCIM Facade / バッチの資格情報）② 基盤が発行するテナント向け管理 API クライアントに限定する。**アプリ間 M2M の棚卸し責任はアプリチーム**（責任分担表に明記すること）。

## Consequences

- **Positive**: 資格情報スプロールの可視化 / 最小権限・定期ローテの機械強制 / SOC2・ISO の NHI 証跡 / owner 必須で孤立を構造的に予防。
- **Negative / 受容**: 台帳維持と owner アサインの運用負荷（軽量 IGA 範囲で吸収）/ 既存 NHI の初期棚卸しに一時工数。

## Alternatives Considered

| 案 | 判定 |
|---|---|
| 個別決定のまま | 却下（台帳・孤立検知なしでスケール時に統制不能） |
| **軽量 NHI 台帳 + 規約（採用）** | **採用**（自作コスト小・既存 IGA/監視/outbox に相乗り） |
| 商用 NHI/ISPM 製品 | Phase 2 以降（Phase 1 予算外） |

## Open Items

- Client Credentials owner モデル（テナント × アプリ）と失効連鎖の粒度。
- IETF WIMSE（ワークロード ID Token、2024 WG）姿勢 — IRSA（AWS 限定）→ 将来ポータブル化の余地を台帳設計で殺さない。
- AI エージェント/エージェンティック ID（[hearing B-AGENT-1](../requirements/hearing-checklist.md)）は NHI の特殊系として本台帳の `type` 拡張で受ける。
