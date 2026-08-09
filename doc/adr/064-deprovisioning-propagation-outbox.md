# ADR-064: 削除／デプロビジョニング伝播 = outbox + 中央 shadow 制御（A 案）

- **ステータス**: Proposed（基本設計フェーズで Accepted 昇格予定）
- **日付**: 2026-08-08 作成
- **決定**: **ブランド(#2)での削除を、authz DB の outbox に 1 トランザクションで書き、outbox リレーが EventBridge へ必達送信 → 中央 shadow 制御 Lambda が冪等に Broker shadow を無効化する（A 案）。遮断チェックのみ数分リコンサイルを砦に置く。**
- **関連**:
  - [ADR-063 ブランドユニット](063-brand-unit-architecture.md)（ブランド主役・中央 shadow 制御。本 ADR はその削除伝播の具体化）
  - [ADR-062 idm-api = Lambda](062-idm-api-execution-form-lambda.md)（実行形態）
  - [U3 D3-17](../basic-design/03-identity-provisioning-design.md)（状態機械・削除フロー = 本 ADR の設計根拠 SSOT）/ [U9 D-U9-18](../basic-design/09-operations-observability-design.md)（Lambda パイプライン）
  - 検討材料: [research/control-plane-crud-authz-flows-notes.md フロー④](../basic-design/research/control-plane-crud-authz-flows-notes.md)、[jit-scim §10.4](../common/jit-scim-coexistence-keycloak.md)

---

## Context

- ブランド主役（[ADR-063](063-brand-unit-architecture.md)）で削除は **#2（ブランド側）が実行**するが、トークン発行のゲートは **Broker shadow（別アカウント）**。この 2 ストア（IdP-KC identity + Broker shadow）を確実に揃える分散問題。
- 要件（ユーザー確定）: **削除されたユーザは確実に遮断したい**。
- 制約: ブランド主役で中央 front door（旧 #1）は無く、`#1→#2` PrivateLink 委譲も撤回済み（ADR-063）。越境は EventBridge に寄せたい。

## Decision（A 案 = outbox）

1. **#2 が IdP-KC Soft Delete**（Keycloak: `enabled=false` + `deprovisioned_at`）。
2. **#2 が「projection deprovisioned + `user.deprovisioned` outbox 行」を authz DB の 1 トランザクションで書く** → *削除したら必ずイベントが残る（喪失なし）*。
3. **outbox リレー（Lambda）が EventBridge へ必達送信**（成功まで再送、IdP-KC→Broker）。
4. **中央 shadow 制御 Lambda が Broker shadow を `enabled=false` + `not_before` + session revoke（冪等）**（内部 NLB → Broker KC Admin API）。Keycloak は refresh 時に user.enabled を検査するため即 invalid_grant。
5. **遮断チェックのみ数分リコンサイル**（IdP-KC `deprovisioned_at` ↔ Broker shadow `enabled` の突合。取りこぼし・伝播窓の砦。他の整合突合は日次でよい）。

- **窓**: 通常 = 伝播 数秒 / worst = リコンサイル間隔（数分）。発行済み AT は ≤ 30 分有効（P-09、オフライン検証）。
- **federated（IdP-KC に identity 無）**: Phase 1 既定 = **SCIM deprovision**（SCIM Facade がイベント発行）。SCIM 非対応顧客は **90 日休眠バッチ**で shadow 無効化（U3 D3-09、S5/S6）。

## 決め手

- **outbox で「削除したのにイベントが飛ばない」を構造的に排除**（喪失なし）。同期の逆方向越境（S 案）を新設せずに確実性を担保できる。
- 主脅威（idm-api #2 の乗っ取り）は #2 が Admin API + authz DB の双方に正当アクセスするため伝播方式では防げない → #2 堅牢化（[U7 D-U7-19](../basic-design/07-security-compliance-design.md)）で守る。本 ADR は「確実な伝播」を担当。

## Consequences

- **Positive**: 削除の確実性（イベント喪失なし）+ 越境は EventBridge のみ（新規の同期逆経路 不要）+ shadow 制御は冪等（多重配信に安全）+ リコンサイルが二重の砦。
- **Negative / 受容**: 数分の伝播窓（worst = リコンサイル間隔）。発行済み AT は ≤ 30 分残る（既発行トークンの即死には Phase 3 Introspection or 短 AT が別途要）。
- **切替余地**: 即時ゼロ窓が契約要件になった場合は **S 案（削除だけ IdP-KC→Broker の同期呼びで shadow 無効化）**へ。逆方向同期チャネル（PrivateLink or cross-account）を新設する。

## Alternatives Considered

| 案 | 内容 | 判定 |
|---|---|---|
| **Broker-first 同期 2 コール（旧）** | ① Broker shadow 無効化 → ② IdP-KC Soft Delete（PrivateLink 委譲）の同期 | **却下**。ブランド主役で中央 #1 廃止・PrivateLink 委譲撤回（ADR-063） |
| **A 案 outbox（採用）** | 上記 Decision | **採用**。喪失なし + 越境 EventBridge のみ |
| **S 案 同期逆呼び** | 削除時に #2 → Broker shadow を同期呼び（IdP-KC→Broker） | 保留（即時ゼロ窓が契約要件なら採用。逆方向同期チャネル新設が要る） |
| **SCIM を内部伝播に使う** | IdP-KC→Broker を SCIM で | 却下（Keycloak SCIM outbound は core 未実装 = [keycloak#13484](https://github.com/keycloak/keycloak/issues/13484) / `scim_active` の意味崩壊 / shadow 除外印は既存 `jit_idp_alias=idpkc%` で足りる） |

## Open Items

- **ロックアウト SLA の明文化**: リコンサイル間隔を何分にするか + hosted の「即時ゼロ窓」要件の有無 → 契約 SLA と連動（要件なら S 案へ）。
- **越境イベント経路の S2S 認可の具体**（shadow 制御 Lambda、旧 ADR-062 O-12 の再定義、U5 §5.8）。
- Event Listener SPI 併用の要否（削除イベント発行の二重化）。
