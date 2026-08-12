# ADR-065: 継続アクセス評価 = CAEP / Shared Signals（ゾンビ窓の標準解）

- **ステータス**: Proposed（**スタブ** — 2026-08-12 網羅性再監査で起票。方式確定は G-SSF PoC + B-CAEP-1 回答後）
- **日付**: 2026-08-12 作成
- **決定（方向性）**: **AT 失効後の「ゾンビ窓」（[U5 §5.2.4](../basic-design/05-token-session-authz-design.md) Z-1〜Z-5、失効後 ≤30 分）の恒久解として、OpenID Shared Signals Framework（SSF）+ CAEP を目標アーキテクチャに据える。** Phase 1 は暫定ブリッジ（短命 AT + not-before push + 高価値リソースの Introspection + DPoP Phase 2）で凌ぎ、CAEP は PoC ゲート **G-SSF** 通過後に段階導入する。
- **関連**: [U5 §5.2.4 ゾンビ窓](../basic-design/05-token-session-authz-design.md) / [U5 §5.5 ログアウト4層](../basic-design/05-token-session-authz-design.md) / [ADR-060 §B Token Binding/DPoP](060-auth-protocol-attack-path-residual-tbd.md) / [ADR-064 削除伝播 outbox](064-deprovisioning-propagation-outbox.md) / [ITDR U7 §7.4](../basic-design/07-security-compliance-design.md) / hearing **B-CAEP-1** / gate **G-SSF**

---

## Context

- 本基盤のアプリ向け AT は **30 分の Stateless JWT**（RP がオフライン署名検証）ゆえ、失効操作（退職 SCIM 削除・管理者強制ログアウト・ITDR L4）後も**最大 30 分は有効**（U5 §5.2.4 で受容済みの構造的残余リスク）。
- 現行の緩和は「短命化 + DPoP(Phase 2) + Introspection(Phase 3)」に留まり、**失効の near-real-time 伝播**（数秒での RP 側セッション/トークン失効）を担う標準経路がない。
- **2-tier ブローカー**は顧客 IdP と下流アプリの間に位置するため、**双方向**が論点: ①上流（顧客 IdP）の失効/リスク信号を受信して伝播 ②下流（RP）へ失効イベントを送信。
- 業界動向: **OpenID SSF 1.0 / CAEP 1.0 / RISC 1.0 が 2025-09-02 Final**。ただし **Keycloak の SSF は experimental・transmitter のみ・既定 off**（receiver 未完）で、商用（Okta 等）も `session-revoked`/`credential-change` 中心で risk/assurance 変化の相互運用は未成熟。

## Options

| 案 | 内容 | 評価 |
|---|---|---|
| **A. 暫定ブリッジのみ（現行維持）** | 短命 AT + not-before push + 高価値 API は Introspection | ゾンビ窓は縮むが「数秒失効」には届かない。標準非依存で相互運用性なし |
| **B. CAEP 目標 + 暫定ブリッジ（推奨方向）** | 目標を SSF/CAEP に置き、Phase 1 は A、G-SSF 通過後に transmitter（→RP）先行、receiver（←顧客 IdP）は成熟待ち | 標準準拠・段階導入。Keycloak SSF 成熟度が律速 |
| **C. 独自 SET エミッタ自作** | CAEP イベント（`session-revoked` 等）を outbox/EventBridge から自作配信 | ADR-064 の outbox と親和。Keycloak native を待たず前倒し可能だが自作保守負担 |

## Decision（TBD）

- **方向 = B**（CAEP を目標、Phase 1 は暫定ブリッジ）。**C（outbox からの自作 SET エミッタ）を transmitter 早期実装の有力手段**として G-SSF で評価。
- **確定前に必要**: ① **G-SSF PoC**（Keycloak experimental SSF の transmitter 動作 + receiver 要否 + 自作エミッタ比較）② **B-CAEP-1**（顧客 IdP 側の SSF 送受信可否・RP 側の受信 SDK 提供範囲）③ RISC（アカウント侵害/無効化）と ADR-064 削除伝播のイベント語彙整合。

## Consequences（想定）

- **Positive**: ゾンビ窓を「数秒」オーダーへ短縮 / 失効・リスクの標準伝播 / RP 実装ガイド（U5 §5.6）に CAEP receiver 章を追加できる。
- **Negative / 受容**: Keycloak SSF 成熟待ち・RP 側 SDK 配布の負担 / 相互運用は業界的に未成熟なため Phase 1 は暫定ブリッジ必須。

## Open Items

- G-SSF の合格基準定義（transmitter/receiver/自作エミッタの 3 択と性能）。
- CAEP Interoperability Profile 準拠の要否（2-tier + 1000+ IdP + RP fleet での相互運用）。
- ITDR Risk Engine の risk-level 変化を CAEP `assurance-level-change` 等で RP へ出すか（業界的に未相互運用 = 当面は基盤内評価に留める）。
