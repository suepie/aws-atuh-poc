# ADR-063: ブランドユニット・アーキテクチャ（共有 Broker + ブランド別 backend、authz/idmap をブランド配置）

- **ステータス**: Proposed（基本設計フェーズで Accepted 昇格予定）
- **日付**: 2026-08-06 作成
- **決定**: **Broker は共有（1 つ）。ブランドを将来の隔離/複製単位とし、authz / idmap / projection / CRUD / アプリをブランドユニット（IdP-KC 側）に置く。Broker は authz を持たない。** Phase 1 スコープ = 1 ブランド。物理 per-brand 分割は将来（本 ADR では論理境界のみ確定）。
- **関連**:
  - [ADR-062 idm-api 実行形態 = Lambda](062-idm-api-execution-form-lambda.md)（実行形態。本 ADR の authz 配置と直交、両立）
  - [ADR-017 マルチテナント L2](017-multitenant-single-realm.md) / [ADR-033 2-tier](033-keycloak-2tier-architecture.md)（Broker/IdP-KC の 2 層）
  - [U1 §1.2 アカウント体系 E 判断](../basic-design/01-architecture-baseline.md)（本 ADR で改訂：authz DB = Broker → ブランドユニット）
  - 検討材料: [research/control-plane-crud-authz-flows-notes.md](../basic-design/research/control-plane-crud-authz-flows-notes.md) / [research/me-context-projection-comparison-notes.md](../basic-design/research/me-context-projection-comparison-notes.md)

---

## Context

### スコープと前提（ユーザー確定 2026-08-06）

- **Phase 1 は 1 ブランドのみ**。マルチブランドの要件は現時点で無いが、**将来のための設計**として境界を決める。
- **Broker は 1 つ（複数 Broker は作らない）**。複数システムの認証を横断し、ログイン画面をブランド別テーマで描画する（Keycloak Organizations + per-client/org テーマ + HRD で 1 Broker で実現可能）。
- **ブランドごとに分かれるもの = ログイン画面（テーマ）・そのブランドのユーザー編集（CRUD）・権限・idmap・アプリ**。
- **ユーザーは 1 ブランドに閉じる**（ブランドが違えば体系ごと別。将来 SSO する可能性はあるが体系は変わる）。
- **各ブランドのアプリはそのブランド側で動く**（ただし顧客 IdP とフェデレーションするユーザーはいる）。
- **idmap はブランドで閉じる**。
- **物理隔離（ブランド別アカウント/クラスタ）は将来検討**（Phase 1 では 1 ブランド = 現行 IdP-KC アカウント 1 つ）。

### 論点

前 ADR 検討で「認可 DB = Broker」と一旦記録した（[U1 §1.2](../basic-design/01-architecture-baseline.md)）が、これは**ブランドモデルが判明する前**の判断。ブランドモデルでは:
- **将来 per-brand になるもの（authz/idmap/CRUD）を "共有 Broker" に載せると、将来剥がす移行が必要**になる。
- authz DB は Keycloak でなく Backend DB で **キー = `sub`**。federated ユーザーも `sub`（+ `brand_id`）で保持でき、**IdP-KC の identity レコードが無くても authz 行は持てる**（前 ADR の「federated だから Broker 必須」は撤回）。

## Decision

**案 b を採用：authz / idmap / projection をブランドユニット（IdP-KC 側）に置く。Broker は authz を持たない。**

### 層の分担

| 層 | 共有 or ブランド別 | 中身 |
|---|---|---|
| **Broker（共有・1）** | 共有 | 横断認証/SSO・**ログイン画面描画（ブランド別テーマ）**・`sub` 発行・ブランドルーティング・**Broker shadow（遮断キルスイッチ）**。**authz 非保持** |
| **ブランドユニット（将来 N、Phase 1 は 1）** | ブランド別 | IdP-KC（hosted identity）+ **authz + idmap + projection（`sub` + `brand_id` キー）** + CRUD + アプリ。**すべてブランド内でローカル完結** |

### 今ロックする不変条件（将来の物理分割を綺麗にする）

1. **`sub` はグローバルで安定な UUID**（Broker 発番。ブランドローカルにしない）→ 将来 SSO でも通用。
2. **authz / idmap / ユーザー各レコードに `brand_id` を一級キーとして持つ**。
3. **cross-brand の join / クエリを設計に作らない**（ブランドは独立サイロ）。
4. **Broker は共有関心のみ**。per-brand データは brand スコープで、将来そのまま per-brand へ切り出せる形にする。

## Consequences

### Positive

- **将来ブランドを増やす時、ブランドユニットを複製するだけ**（authz を共有 Broker から剥がす移行が不要）。
- **`/api/me/context` はブランドローカル read**（ブランドのアプリ → ブランド authz/projection、**越境ゼロ**）。→ [射影比較ノート](../basic-design/research/me-context-projection-comparison-notes.md) の「中央射影 vs 越境都度 read」の悩みが per-brand では実質消える。
- **ホットパスの越境ゼロ**。越境は「初回 sub 通知（write）」「shadow 遮断」に縮小。

### Negative / 留意

- **federated ユーザーの authz 行生成**：初回ログイン時に **Broker → ブランドへ `sub` 通知（EventBridge、write 時のみ越境）** → ブランドが authz スタブ行作成。順序/整合（at-least-once + 冪等）が要る。
- **idm-api トポロジが変わる**：#2（ブランド側）が **CRUD + 権限 + projection** を担い厚くなる。#1（Broker）は **共有 front door（brand ルーティング）+ shadow 遮断** に縮小。front door を #1 集約とするか #2 直とするかは実装で確定。
- **Phase 1（1 ブランド）ではやや冗長**に見えるが、将来移行回避のため受容。

### 改訂・影響

- **U1 §1.2 E 判断**：「認可 DB = Broker」→ **「authz/idmap/projection = ブランドユニット（IdP-KC 側）、Broker は authz 非保持」** + 不変条件 1〜4。
- **control-plane ノート**：構成図・フロー③を per-brand に更新。
- **射影比較ノート**：per-brand ではブランドローカル read で越境問題が消える旨。
- **ADR-062（Lambda）**：影響なし（実行形態と直交）。#2 が authz も担う点だけ注記。

## Alternatives Considered

| 案 | 内容 | 判定 |
|---|---|---|
| **(a) authz = Broker（現状維持 + brand_id）** | Phase 1 シンプル | 将来 per-brand 化で **Broker→per-brand の移行が必要**。不採用（将来設計が目的のため） |
| **(b) authz = ブランドユニット（IdP-KC 側）** | 将来移行不要・brand 形状 | **採用** |
| 複数 Broker | ブランドごとに Broker | 不採用（ユーザー確定：Broker は 1 つ。ログインテーマは 1 Broker で per-brand 可能） |

## Open Items

- **物理 per-brand 分割の時期・方式**（アカウント/クラスタをブランド別に）→ マルチブランド要件が出た時。
- **front door トポロジ**：管理操作の入口を #1（Broker 集約 → #2 ルーティング）にするか、ブランド admin → #2 直にするか。
- **federated `sub` 通知**の具体（EventBridge Broker→ブランド、整合設計）。
- **cross-brand 横断管理ビュー**を将来作る場合の越境 read 設計（作らなければ不要）。
- ブランドの Realm/Organization モデリング（1 Realm + Organizations でブランドをどう表すか）→ U2。
