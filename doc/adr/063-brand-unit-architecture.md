# ADR-063: ブランドユニット・アーキテクチャ（共有 Broker + ブランド別 backend、authz/idmap をブランド配置）

- **ステータス**: Proposed（基本設計フェーズで Accepted 昇格予定）
- **日付**: 2026-08-06 作成、2026-08-07 更新（§認可データ配置粒度 = A+C 追記、U7 D-U7-19 連動）、**2026-08-15 更新（ブランド Realm モデリング = brand=Realm 確定、不変条件⑤ issuer per brand 追加、参照切れ §3.8.0 解消）**
- **決定**: **Broker は共有（1 つ）。ブランドを将来の隔離/複製単位とし、authz / idmap / projection / CRUD / アプリをブランドユニット（IdP-KC 側）に置く。Broker は authz を持たない。** Phase 1 スコープ = 1 ブランド。物理 per-brand 分割は将来（本 ADR では論理境界のみ確定）。
- **対応する前提**: **[P-19 ブランドユニット](../basic-design/01-architecture-baseline.md)**（2026-08-17 正式採番。それまで P 表に不在で、Excel 側が仮採番 `P-BRAND-1` で追跡していた）
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
5. **issuer はブランド毎に単一**（2026-08-15 追加、下記「ブランド Realm モデリング」）。アプリ/RP は issuer をハードコードせず**ブランド設定から解決**する。プラットフォーム全体は将来 N issuer（ブランド毎）だが、各アプリは自ブランドの単一 issuer のみを見る。

## Consequences

### Positive

- **将来ブランドを増やす時、ブランドユニットを複製するだけ**（authz を共有 Broker から剥がす移行が不要）。
- **`/api/me/context` はブランドローカル read**（ブランドのアプリ → ブランド authz/projection、**越境ゼロ**）。→ [射影比較ノート](../basic-design/research/me-context-projection-comparison-notes.md) の「中央射影 vs 越境都度 read」の悩みが per-brand では実質消える。
- **ホットパスの越境ゼロ**。越境は「初回 sub 通知（write）」「shadow 遮断」に縮小。

### Negative / 留意

- **federated ユーザーの authz 行生成**：初回ログイン時に **Broker → ブランドへ `sub` 通知（EventBridge、write 時のみ越境）** → ブランドが authz スタブ行作成。順序/整合（at-least-once + 冪等）が要る。
- **idm-api トポロジが変わる**：#2（ブランド側）が **CRUD + 権限 + projection** を担う（主役）。**中央 front door（旧 #1）は置かず、ルーティングはエッジ（CloudFront/API GW）、中央に残るのは shadow 制御 Lambda のみ**（front door トポロジは Open Items で確定）。
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
| **認可データ配置粒度 A+C** | ブランド内は単一アカウント + identity(Keycloak)/authz 系(authz/idmap/projection) を別 Aurora・別 CMK・別 IAM ロール・別 SG に内部分離 | **採用**（2026-08-07。下記「認可データ配置粒度」。B=2 アカウント分割は規制ブランド向け将来オプション、D=authz を Broker へ は却下） |

## 認可データ配置粒度（A+C 採用、2026-08-07）

ブランドユニット内で **credential（IdP-KC Keycloak の PW ハッシュ）と authz 系（authz/idmap/projection）をどう分離するか**。

**脅威分解**: アカウント分離が効くのは「アカウントレベル侵害（IAM 権限昇格・アカウント乗っ取り）」のみ。**主脅威の idm-api #2 乗っ取りは、#2 が CRUD のため Admin API（credential）と authz DB の双方に正当アクセスするので、データを別アカウントにしても防げない**。DB 単体侵害は identity/authz が元々別 Aurora・別資格情報ゆえ一方から他方は取れない。

**決定 = A + C**:
- **A（単一アカウント）** の単純さ + ブランドローカル完結を維持。
- **C（内部強分離）**: identity(Keycloak) Aurora と authz 系 Aurora を **別 Aurora・別 KMS CMK・別 IAM ロール・別 SG** に分け、**両方に届く単一ロールを作らない**（最小権限 + SCP）→ [U7 D-U7-19](../basic-design/07-security-compliance-design.md)。
- 主脅威（#2 乗っ取り）は #2 の堅牢化（最小権限実行ロール・依存最小・監査）で守る。

**却下/保留**:
- **B（ブランドを credential/データの 2 アカウントに分割）**: アカウントレベル侵害には強いが #2 乗っ取りには無効 + ブランドあたり 2 アカウント + ブランド内クロスアカウント経路増。**規制ブランド（アカウントレベル分離が契約/監査要件）向けの将来オプションとして予約**。不変条件（sub グローバル / brand_id 一級キー）により、データアカウントの切り出しはクリーン移行可。
- **D（authz を共有 Broker へ戻す）**: 却下。将来 per-brand 移行が必要 + 共有 Broker に cross-brand データ集中 = 不変条件 ③④ 違反。

## ブランド Realm/Organization モデリング（brand=Realm 確定、2026-08-15）

> 旧 DU-U2-09 が参照していた「§3.8.0」は本節。**先行判断「単一 broker Realm vs ブランド=Realm」をここで確定する**（[00b DU-U2-09](../basic-design/00b-design-unit-breakdown.md) / [01 §1.5 G-SRE… 隣接](../basic-design/01-architecture-baseline.md)）。

### 論点の本質 = 2 軸の取り違え

「Realm をいくつにするか」で **テナント軸**と**ブランド軸**という別粒度を衝突扱いしていたのが混乱の原因。両者は両立する。

| 軸 | 基数 | モデリング | 根拠 |
|---|---|---|---|
| **テナント（顧客）** | 数千 | **Realm 内の Organizations**（1 顧客 = 1 Org） | [ADR-017](017-multitenant-l2-single-realm.md)：マルチ Realm は 100–400 で運用劣化 → テナントに Realm を割らない。[02 §2.1.1](../basic-design/02-keycloak-logical-design.md) |
| **ブランド** | 少数（Phase 1 = 1、将来も数個） | **Realm（brand = Realm）**。将来は別クラスタ/アカウントへ | 本 ADR：ブランド = 将来の隔離/複製単位 |

**ADR-017 の「マルチ Realm 禁止」はテナント軸の話**であり、ブランドは数個なのでブランド=Realm にしてもスケール劣化に当たらない（マルチ Realm の劣化はテナント数千を Realm 化した場合の話）。→ **非衝突**。

### 決定 = brand = Realm

- **1 Broker = N Realm（ブランド毎）**。Phase 1 = 1 ブランド = **現行の単一 Realm `broker` / `idp` のまま（今の設定は不変）**。
- ブランド追加 = **Realm を IaC テンプレートから機械派生**（per-realm ログインテーマ / per-realm issuer / per-brand IdP-KC Realm 対応）。将来ブランドを別クラスタ/アカウントへ出す時も、Realm が単位なので**クラスタ分割が自然に別 Realm=別 issuer になり、Realm を割る移行が発生しない**。
- テナント（Organizations）は**各ブランドの Realm 内**にそのまま入る（テナント軸の単一 Realm + Organizations 設計〔[02 §2.1.1](../basic-design/02-keycloak-logical-design.md)〕はブランド Realm 内で不変）。
- **issuer 規律を Phase 1 からロック**（不変条件 ⑤）：[U5 の単一 issuer 前提](../basic-design/05-token-session-authz-design.md)を**「ブランド毎に単一 issuer」**と読み替え。アプリ/RP は issuer をハードコードせずブランド設定から解決する（各アプリは 1 ブランドに閉じるため、見る issuer は常に 1 つ）。→ 将来ブランド追加時にアプリ再計装が不要。

### 却下：brand = 単一 Realm 内の Organizations グループ

全ブランドで 1 Realm を共有し、ブランドを Organizations のグループ/属性で表す案。単一 issuer を維持できるが、**(1) Keycloak に「Organization のグループ」概念がなく不自然**、**(2) 将来ブランドを別クラスタに出す時に Realm 分割の移行が必要**（本 ADR の「将来移行回避」目的に反する）。不採用。

### Phase 1 実装への影響

- **設定変更なし**（1 ブランド = 現行単一 Realm）。確定するのは "方式" と不変条件⑤のみ。
- Phase 1 の実作業 = ① Realm を IaC モジュール化しブランドをパラメータ化（1 Realm のみ instantiate）② issuer をブランド設定から解決する RP 実装ガイド規律 + トークン検証設計。
- **将来分（Phase 2+）**: N Realm 機械派生の完成 + per-realm テーマ自動化 + per-brand IdP-KC Realm 対応表の運用。→ DU-U2-09 の残工数。

## Open Items

- **物理 per-brand 分割の時期・方式**（アカウント/クラスタをブランド別に）→ マルチブランド要件が出た時。
- **front door / shadow 制御トポロジ = 確定済み**：**ブランド主役**＝ #2 が CRUD + authz + projection の実体、中央は **shadow 制御 Lambda のみ**、ルーティングはエッジ。**削除伝播（shadow 無効化）は [ADR-064](064-deprovisioning-propagation-outbox.md) で確定**（A 案 outbox: 1Tx outbox + リレー必達 + 数分リコンサイル。旧「案 i 直接発行 / 日次リコンサイル」から更新）。残論点 = ロックアウト SLA（ADR-064 Open Items）。
- **federated `sub` 通知**（authz 行生成用）の具体（EventBridge Broker→ブランド、整合設計）。
- **cross-brand 横断管理ビュー**を将来作る場合の越境 read 設計（作らなければ不要）。
- ~~ブランドの Realm/Organization モデリング~~ → **確定（2026-08-15、上記「ブランド Realm/Organization モデリング」節）= brand=Realm**。残 = N Realm 機械派生の IaC 完成（将来、DU-U2-09）。
