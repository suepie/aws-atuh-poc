# ADR-065: 継続アクセス評価 = CAEP / Shared Signals（ゾンビ窓の標準解）

- **ステータス**: Proposed（2026-08-12 起票 → 2026-08-12 本設計化。Phase 1 スコープは確定、CAEP 本格導入の最終確定は G-SSF PoC + B-CAEP-1 回答後）
- **日付**: 2026-08-12 作成・本設計化
- **決定**: **AT 失効後の「ゾンビ窓」（[U5 §5.2.4](../basic-design/05-token-session-authz-design.md) Z-1〜Z-5、失効後 ≤30 分）の恒久解として OpenID SSF/CAEP を目標アーキテクチャに据え、3 フェーズで段階導入する。Phase 1 = 暫定ブリッジ（短命 AT + not-before push + 高価値リソースの Introspection + DPoP）+ ADR-064 outbox からの自作 SET エミッタ（transmitter 先行）。Phase 2 = Keycloak native SSF transmitter へ移行。Phase 3 = receiver（顧客 IdP からの inbound 信号）。**イベント語彙は CAEP/RISC 標準に合わせ、削除伝播（ADR-064）と統一する。**
- **関連**: [U5 §5.2.4 ゾンビ窓](../basic-design/05-token-session-authz-design.md) / [U5 §5.4 Revocation/ITDR L4](../basic-design/05-token-session-authz-design.md) / [U5 §5.5 ログアウト4層](../basic-design/05-token-session-authz-design.md) / [ADR-064 削除伝播 outbox](064-deprovisioning-propagation-outbox.md) / [ADR-060 §B DPoP](060-auth-protocol-attack-path-residual-tbd.md) / [ITDR U7 §7.4](../basic-design/07-security-compliance-design.md) / hearing **B-CAEP-1** / gate **G-SSF** / WBS **DU-U5-06**

---

## Context

- アプリ向け AT は **30 分の Stateless JWT**（RP がオフライン署名検証）ゆえ、失効操作後も**最大 30 分有効**（U5 §5.2.4 の構造的残余リスク）。現行緩和「短命化 + DPoP(P2) + Introspection(P3)」には**失効の near-real-time 伝播経路がない**。
- **2-tier ブローカー**は顧客 IdP と下流アプリの中間に位置 → **双方向**が論点。①下流（RP）へ失効を送る *transmitter* ②上流（顧客 IdP）の失効/リスクを受ける *receiver*。
- **業界動向**: OpenID **SSF 1.0 / CAEP 1.0 / RISC 1.0 が 2025-09-02 Final**（仕様リスクは解消）。ただし **Keycloak SSF は experimental・transmitter のみ・既定 off**（receiver 未完）、商用も `session-revoked`/`credential-change` 中心で risk/assurance 変化の相互運用は未成熟。
- **既存資産との親和**: ADR-064 の削除 outbox（`user.deprovisioned` を authz DB 1Tx → リレー → EventBridge）は、**SET（Security Event Token）配信の基盤としてそのまま流用できる**。

## Decision

### フェーズ計画

| Phase | transmitter（→RP） | receiver（←顧客 IdP） | ゾンビ窓 |
|---|---|---|---|
| **1（本設計スコープ）** | **暫定ブリッジ** + **自作 SET エミッタ**（outbox 起点） | なし（顧客 IdP 失効は SCIM/90 日バッチ = ADR-064 既存） | 高価値 API は数秒、標準 API は ≤30 分 |
| **2** | **Keycloak native SSF transmitter** へ移行（G-SSF 合格後） | なし | 全 API 数秒（受信 RP のみ） |
| **3** | 同上 | **CAEP receiver**（顧客 IdP の `session-revoked`/RISC を取込） | 上流失効も数秒伝播 |

### Phase 1 = 暫定ブリッジ + 自作 SET エミッタ（確定）

1. **暫定ブリッジ（全 RP）**: ① AT 30 分維持 ② ITDR L4 / 管理者強制ログアウト時の **not-before push**（U5 §5.4.3）③ **高価値リソース（管理系・決済・PII 更新）は RP が Introspection（RFC 7662）**でオンライン確認 ④ DPoP（Phase 2、盗難 AT の窓内再利用を無効化）。
2. **自作 SET エミッタ（transmitter 先行）**: ADR-064 の outbox/EventBridge に **CAEP イベントを相乗り**させ、CAEP receiver を実装した RP へ **SET（RFC 8417）を push（RFC 8935）or poll（RFC 8936）**で配信する。
   - **発火イベント**: `session-revoked`（管理者強制ログアウト・削除）/ `token-claims-change`（権限剥奪）/ RISC `account-disabled`・`account-purged`（ADR-064 の `user.deprovisioned` を写像）。
   - **配信先**: RP が登録した receiver エンドポイント（SSF Stream 管理）。**Phase 1 は opt-in の高価値 RP のみ**。
   - **語彙統一**: ADR-064 の `user.deprovisioned` = RISC `account-disabled`、shadow 無効化 = CAEP `session-revoked` に対応付け、**削除伝播と CAEP を単一イベントモデル**にする。

### 確定に必要（trigger のみ hearing/PoC 依存）

- **G-SSF PoC**: Keycloak experimental SSF transmitter の動作 + 自作エミッタとの機能差 + 性能（10M 規模の SET 配信）→ Phase 2 移行判定。
- **B-CAEP-1**: ①顧客 IdP の SSF 送信可否（→ Phase 3 receiver の要否）②RP への CAEP receiver SDK 配布範囲（→ Phase 1 opt-in の対象）。

## Consequences

- **Positive**: ゾンビ窓を高価値経路で「数秒」化 / 失効・リスクの標準伝播 / ADR-064 と単一イベントモデルで実装重複なし / RP 実装ガイド（U5 §5.6）に CAEP receiver 章を追加。
- **Negative / 受容**: Phase 1 は opt-in RP のみ（全 RP 即時ではない）/ Keycloak SSF 成熟待ち / RP 側 receiver SDK 配布の負担 / risk/assurance 変化の相互運用は業界的に未成熟ゆえ Phase 1 は基盤内評価に留める。

## Alternatives Considered

| 案 | 判定 |
|---|---|
| 暫定ブリッジのみ（CAEP 非採用） | 却下（標準非依存・数秒失効に届かない） |
| Keycloak native SSF を Phase 1 から必須 | 却下（experimental・receiver 未完でブロッカー化） |
| **暫定ブリッジ + outbox 自作 SET エミッタ（採用）** | **採用**（既存 outbox 流用で早期 transmitter、native は Phase 2 で置換） |

## Open Items

- SSF Stream 管理（RP 登録・鍵・再送）の実装は idm-api（Lambda）側か Broker 側か（ADR-062 と整合）。
- CAEP Interoperability Profile 準拠の要否（2-tier + 1000+ IdP）。
- ITDR risk-level 変化の CAEP `assurance-level-change` 送出は業界未相互運用 → Phase 3 以降の再評価。
