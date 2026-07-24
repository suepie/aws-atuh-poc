# U3: ID・プロビジョニング・ライフサイクル設計（Identity & Provisioning Design）

作成日: 2026-07-23
ステータス: **ドラフト（Wave 1）** — Phase 1 契約前ゲート 8 項目（§3.7）の回答で該当節のみ差し替える
前提: [01-architecture-baseline.md](01-architecture-baseline.md) **Baseline v1**（特に P-06 / P-07 / P-08 / P-12 / P-17）
上位文書: [00-basic-design-plan.md](00-basic-design-plan.md) §U3

## 3.0 背景・なぜここで決めるか / スコープ

本基盤は **IdP フェデレーション専用**（P-07 γ シナリオ：管理者層のみローカル、P-3 は原則フェデ強制）であり、ユーザーレコードは「アプリが登録する」のではなく「JIT / SCIM / LDAP / 管理者 / アプリ発 CRUD の 5 経路から流入する」。経路ごとに SoT（Source of Truth）が異なるため、**識別子のデータモデルとライフサイクル（作成 → 無効化 → 物理削除）を経路横断で 1 冊に固定しないと、90 日バッチの誤削除・SCIM 削除済みユーザーの誤復活・マッピング DB の FK 崩壊が実装フェーズで必ず起きる**。要件定義フェーズで [jit-scim-coexistence-keycloak.md §10.4](../common/jit-scim-coexistence-keycloak.md)（以下 jit-scim）に G〜L 節として蓄積された決定を、基本設計として再構成・確定するのが本書である。

### U2 / 他単元との境界

| 境界 | 本書（U3） | 相手側 |
|---|---|---|
| **U2 Keycloak 論理設計** | データモデル・属性規約・ライフサイクル仕様・判別/除外**条件**（What） | SPI の実装仕様・Flow 3 系統配置・Protocol Mapper・User Profile の realm.json 表現（How） |
| **U6 インフラ** | SCIM エンドポイントの論理設計・認証方式 | ALB/WAF 経路、Broker Acct ↔ IdP-KC Acct クロスアカウント経路、Aurora 配置 |
| **U10 周辺連携** | L1（顧客 IdP → 本基盤）のプロビジョニング | L2（本基盤 → ServiceNow 等 SP）のプロビジョニング詳細（[ADR-023 §L](../adr/023-servicenow-sp-integration.md) 前提）、ユーザ管理画面 API の OpenAPI 化 |
| **U7 セキュリティ** | 監査イベントの発行点定義 | ITDR 連携・ログ保管の実装 |

本書の決定は **D3-01〜D3-13** で採番する。

---

## 3.1 識別子データモデル

### D3-01: 3 階層識別子の格納先確定

[ADR-018](../adr/018-user-identifier-3layer-emailless.md) の 3 階層モデルを Keycloak の物理格納先に落とす。

| Layer | 内容 | 採番者 / 可変性 | **格納先（確定）** | 用途 |
|---|---|---|---|---|
| **A** `sub` | 基盤内部 UUID | 本基盤 / **絶対不変** | `user_entity.id`（Keycloak 採番）。JWT `sub` クレームとして発行 | 全 DB FK・監査ログ・アプリの主 ID（[jit-scim §10.5.3](../common/jit-scim-coexistence-keycloak.md) アプリ ID 設計標準） |
| **B** `external_id` | 顧客可視 ID（社員番号等） | 顧客 / 運用上可変 | `user_entity.username` = **`<tenant>-<userid>`**（基盤内一意化、[ADR-025 §I.3](../adr/025-scim-positioning-and-receive-stance.md)）+ `user_attribute.external_id`（顧客生値）+ `user_attribute.external_id_history`（改番履歴） | 顧客向け表示・検索・SCIM 照会 |
| **C** IdP 側 `sub` | 顧客 IdP の不変 ID | 顧客 IdP / IdP 内不変 | `federated_identity`（`identity_provider` alias + `federated_user_id` + `federated_username`） | フェデ突合・IdP リンク。IdP 切替（S8）時は新規リンク追加で対応 |

**根拠**: ADR-018 Failure Mode 表（B を FK にすると顧客 ID 改番で崩壊 / A と C を混同すると IdP 切替で sub が変わる）。username への tenant プレフィックスは P-06（L2 単一 Realm）下での基盤内一意性確保のため必須。

**User Profile 明示宣言（P-12 / PoC F-3 是正）**: 以下のカスタム属性は Phase 1 で **User Profile API による schema 宣言 + `unmanagedAttributePolicy` 設定が必須**（realm 属性では効かないことを実機確認済み、[jit-scim §10.4.F.4.4](../common/jit-scim-coexistence-keycloak.md)）。宣言一覧（U2 が realm.json 化する SSOT）:

| 属性 | 書込主体 | 意味 |
|---|---|---|
| `tenant_id` | IdP Mapper / SCIM Facade / API 層 | テナント識別（P-06 tenant_id クレーム原資） |
| `external_id` / `external_id_history` | 同上 | Layer B 生値と改番履歴 |
| `provisioned_by` | SPI / SCIM Facade / API 層（§3.2） | プロビ経路マーカー |
| `provisioned_app` | API 層のみ | アプリ発 CRUD 時の発行元 client_id（D3-04） |
| `scim_active` / `scim_external_id` / `scim_last_sync` | SCIM Facade のみ | SCIM 管理下フラグ（最強の削除禁止フラグ）と突合キー |
| `last_login` | Custom Authenticator SPI（案 B、U2 実装） | 90 日バッチ入力 |
| `jit_created_at` / `reactivated_at` | SPI | JIT 作成・再有効化の監査 |
| `deprovisioned_at` | 90 日バッチ / SCIM Facade / API 層 / 管理者操作 | **Phase 2 物理削除バッチの唯一の入力**（D3-09） |
| `deprovisioned_reason` | 90 日バッチ / 離脱処理 | Soft Delete 事由の監査記録（U2 §2.6 と同期、jit-scim §10.4.K.6） |

### D3-02: email は補助属性（突合キー・主識別子に使用禁止）

- JIT 突合キーの第一推奨は **`tenant_id` + persistent な IdP 不変 ID（OIDC `sub` / SAML persistent NameID / Entra `oid`）**。email は補助属性（ADR-018、Salesforce/Okta「email should never be used as the unique key」）。
- email 非保有ユーザー（B-IDM-1）が存在しても全フローが成立する設計とする。復旧手段は Recovery Codes / Admin Reset / Passkey 多重登録（ADR-018、NIST SP 800-63B-4）。
- **Broker 上の email 保持は「削除検知・突合に必要な場合のみ」の顧客別オプション**（[ADR-025 §I.3](../adr/025-scim-positioning-and-receive-stance.md) Minimum Storage）。S7（同一メール再作成）の Handle Existing Account 分岐は email に依存するため、**email 突合を使う顧客はデフォルト Confirm Link**（Auto-Link は Trusted IdP のみ、ゲート B-JIT-LC-1）。

### D3-03: マッピング DB（ADR-054）のスキーマ確定

[ADR-054 §C](../adr/054-id-integration-strategy.md) の「Keycloak User Attribute 主 + Aurora 補助」を 2-tier（P-17: Broker Acct / IdP-KC Acct 分離）で次のとおり確定する。

1. **per-user の少数マッピング**（`external_id` / `tenant_id` 等）→ Keycloak `user_attribute`（上表）。
2. **多システム ID マッピング**（経理 ID / ServiceNow user_name / 旧システム ID 等）→ **Aurora 補助スキーマ `idmap`**。**Broker の user_attribute には置かない**（[ADR-033](../adr/033-keycloak-2tier-broker-idp-architecture.md) Shallow Broker + ADR-025 §I.3 Minimum Storage）。JWT にも載せない（P-10: Stage 1 最小クレーム・PII 非搭載）。アプリは JWT `sub` を鍵に **ユーザ管理 API（D3-05 の専用 API 層）経由**で参照する（ADR-054 §C.3 のアクセスパターンを API 層経由に限定強化）。

**テーブル定義案**（Phase 1 DDL、配置は Broker Acct Aurora の独立 DB。物理配置・接続経路は U6）:

```sql
-- 統合 ID マッピング（Layer A を唯一の FK 起点とする）
CREATE TABLE idmap.id_mapping (
  mapping_id      BIGSERIAL PRIMARY KEY,
  sub             UUID         NOT NULL,             -- Layer A（user_entity.id、論理 FK）
  tenant_id       VARCHAR(64)  NOT NULL,
  system_code     VARCHAR(64)  NOT NULL,             -- 'hr' / 'accounting' / 'servicenow' / 'app_<id>' ...
  system_user_id  VARCHAR(255) NOT NULL,             -- 当該システム内 ID
  valid_from      TIMESTAMPTZ  NOT NULL DEFAULT now(),
  valid_to        TIMESTAMPTZ,                       -- NULL = 現行値（改番時に閉じて新行）
  created_by      VARCHAR(128) NOT NULL,             -- 'scim' / 'api:<client_id>' / 'admin:<user>' / 'migration'
  CONSTRAINT uq_current UNIQUE NULLS NOT DISTINCT (tenant_id, system_code, system_user_id, valid_to)
);
CREATE UNIQUE INDEX idx_current_per_system
  ON idmap.id_mapping (sub, system_code) WHERE valid_to IS NULL;
CREATE INDEX idx_reverse_lookup
  ON idmap.id_mapping (tenant_id, system_code, system_user_id) WHERE valid_to IS NULL;

-- Layer B 改番履歴（ADR-018 external_id_history の関係 DB 側の正）
CREATE TABLE idmap.external_id_history (
  history_id      BIGSERIAL PRIMARY KEY,
  sub             UUID         NOT NULL,
  tenant_id       VARCHAR(64)  NOT NULL,
  old_external_id VARCHAR(255) NOT NULL,
  new_external_id VARCHAR(255) NOT NULL,
  changed_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
  changed_by      VARCHAR(128) NOT NULL,
  reason          VARCHAR(255)
);
```

設計要点:
- **FK は Layer A（`sub`）のみ**。`system_user_id` に UNIQUE を張るのは「現行行のみ」（改番・再利用を履歴行で許容）。
- 履歴行方式（valid_from/valid_to）により、ADR-054 §D の並走期間中「旧 ID と新 ID の同時解決」を 1 テーブルで実現。
- SoT は人事 DB（ADR-054）。`idmap` は**写像であり SoT ではない**。更新経路は SCIM 受信（§3.5）・API 層（D3-05）・移行バッチの 3 つに限定。
- 物理削除は Phase 2 バッチ（D3-09）で `user_entity` 削除と同時に `id_mapping` を S3 アーカイブ後削除。

---

## 3.2 プロビジョニング経路の全体マトリクス

### D3-04: 5 経路と `provisioned_by` 値体系の確定

Keycloak でユーザーレコードが生まれる経路を次の 5 つに限定し、**経路マーカー `provisioned_by` を全経路で必ず刻む**（[jit-scim §10.4.B.1](../common/jit-scim-coexistence-keycloak.md) の 5 経路事実に P-17 の ⑤ を追加した設計）。

| # | 経路 | 対象 KC | SoT | `provisioned_by` | 書込者 | federated_identity | 90 日バッチ | Re-Activation |
|---|---|---|---|---|---|:---:|:---:|:---:|
| **①** | JIT（フェデ初回ログイン） | Broker | 顧客 IdP | `jit` | First Broker Login SPI（未設定時のみセット） | ✅ | **対象** | **対象** |
| **②** | SCIM 受信（顧客 IdP → Broker: D2 / 顧客 HRIS → IdP-KC: D1） | Broker / IdP-KC | 顧客 IdP / HRIS | `scim` + `scim_active=true` | SCIM Facade（§3.5） | ログイン後に追加 | 対象外（SoT 尊重） | **禁止** |
| **③** | LDAP User Federation | Broker | 顧客 AD/LDAP | `ldap`（+ `federation_link` 自動） | LDAP Provider 設定 | ❌（federation_link で判別） | 対象外（LDAP Sync が AD 側 Disable を反映、[ADR-025 §H.4.B](../adr/025-scim-positioning-and-receive-stance.md)） | 禁止（LDAP Sync 委譲） |
| **④** | 管理者ローカル作成 | Broker / IdP-KC | 本基盤運用 | `local-admin` | 管理者操作（Tenant Admin Portal / ADR-038） | ❌ | 対象外 | **禁止**（管理者操作待ち） |
| **⑤** | **アプリ発 CRUD（P-17 新規）** | **IdP-KC** | **同居アプリ** | **`app`** + `provisioned_app=<client_id>` | 専用 API 層（D3-05） | ❌ | 対象外（アプリが SoT、下記） | **禁止**（アプリ操作待ち） |
| — | Realm Import（移行時のみ） | 両方 | 旧システム | `realm_import` | 移行バッチ | JSON 次第 | 人間レビュー | 禁止 |

値体系の設計原則:
- **未知の値・null は常に安全側**（90 日バッチ = 人間レビュー行き / Re-Activation = 拒否）。[jit-scim §10.4.I.2](../common/jit-scim-coexistence-keycloak.md) の「上記以外 → USER_DISABLED」分岐がそのまま新値 `app` の安全網になる（SPI 改修前でも誤復活しない）。ただし監査可読性のため **U2 の Re-Activation SPI に `app` の明示分岐（拒否 + 専用ログ）を追加**する。
- `provisioned_by` と `scim_active` は **per-Mapper syncMode=IMPORT で JIT ログイン時の上書きから保護**（PoC V2 PASS、§3.3）。
- 導入時の既存ユーザーは [jit-scim §10.4.B.6](../common/jit-scim-coexistence-keycloak.md) バックフィル手順で一括付与。

### D3-05: 経路 ⑤ アプリ発 CRUD は「専用 API 層」経由に確定（推奨案）

P-17 により IdP-KC Acct にはアプリが同居し、当該アプリがユーザ CRUD を直接実施する。3 案を比較した:

| 観点 | 案 A: Keycloak Admin API 直叩き | 案 B: SCIM エンドポイント経由 | **案 C: 専用 API 層（採用）** |
|---|---|---|---|
| 属性規約の強制（`provisioned_by=app` / `deprovisioned_at` セット / User Profile 準拠） | ❌ N アプリが各自実装 → ドリフト必至 | △ Facade 実装次第 | ✅ API 層が不変条件として強制 |
| 物理削除ガードレール（[jit-scim §10.5.1](../common/jit-scim-coexistence-keycloak.md) Layer 1: `delete-users` 非付与） | ❌ アプリに広い admin 権限が必要で Layer 1 と正面衝突 | ✅ SCIM DELETE を Soft Delete に写像可 | ✅ DELETE 動詞を Soft Delete のみに限定 |
| ライフサイクル整合（S1-S10 / Re-Activation 除外） | ❌ アプリ責務に丸投げ | ❌ **`scim_active=true` が付き「顧客 IdP SoT」と誤認** → SCIM 保護・Health Check・テナント遷移（§10.4.L）と全面混線 | ✅ `app` 系列として独立管理 |
| 監査・イベント発行（EventBridge / Webhook） | △ Admin Event 頼み（粒度不足） | △ | ✅ API 層で USER_CREATED/DEPROVISIONED を一元発行 |
| テナント越境防止（P-06 単一 Realm） | ❌ fine-grained admin permissions の設計・維持が高難度 | △ トークン設計次第 | ✅ client_id → tenant スコープを API 層で強制 |
| 追加実装コスト | なし | 小（既存 Facade 拡張） | 中（ただし [ADR-038](../adr/038-tenant-admin-portal.md) Tenant Admin Portal Backend と同一 API 基盤を共用して圧縮） |
| Keycloak バージョン結合 | ❌ 全アプリが Admin API 仕様に結合 | ✅ | ✅ API 層のみが結合 |

**決定**: **案 C（専用 API 層）を採用**。実体は ADR-038 の管理画面 Backend（自作 SPA + 3 層スコープ）と同一のユーザ管理 API を IdP-KC Acct に配置し、アプリには OAuth2 Client Credentials（クライアントごとにテナント/操作スコープ限定）で開放する。案 B は「SCIM = 顧客 IdP/HRIS を SoT とするプロトコル」というセマンティクスを壊すため**明確に却下**。案 A は Phase 1 で API 層が間に合わない場合の**暫定運用としても不採用**（ガードレール Layer 1 崩壊のため）。API の OpenAPI 詳細は U10、認可スコープ設計は U2/U5 に引き渡す。

**S1-S10 / Re-Activation への影響**（D3-04 表の根拠）:
- `app` ユーザは **90 日バッチ対象外**。理由は SCIM と同型（SoT 尊重）: アプリが SoT であり、削除・休眠判定はアプリ責務。ただし PCI DSS 8.2.6 の「システムごと独立監査」原則（[jit-scim §10.4.H.3](../common/jit-scim-coexistence-keycloak.md)）により、**アプリは休眠検出時に API 層の deactivate（Soft Delete）を必ず呼ぶ義務**を開発標準・契約に明記する（未達アプリ向けに「90 日バッチへのテナント単位オプトイン」を Phase 1 設定項目として用意 — 未決 U3-OP-1、§3.7）。
- Re-Activation SPI は `app` を**拒否**（アプリ経由の reactivate API のみ許可）。SCIM 誤復活と同じ構図（[jit-scim §10.4.I.2](../common/jit-scim-coexistence-keycloak.md)）の再発を防ぐ。
- S7（再作成）: アプリ発ユーザは email 突合の Handle Existing Account を通らない（フェデログインしない前提）。フェデも行うユーザをアプリが作る場合は ②/① との混在となり、§3.3 Case 表の safe-side（`app` は scim_active を持たないため JIT 側が `provisioned_by` を上書きしない条件分岐で保護）に従う。

---

## 3.3 JIT/SCIM 共存設計

### D3-07: 判別ロジック 3 段階 + Case 1-5 の設計確定

[jit-scim §10.4.B.2 / §10.4.I.6](../common/jit-scim-coexistence-keycloak.md)（PoC V2/V3'' 実測済み）を Phase 1 の確定仕様とする。判定は必ずこの順序:

```
【判定 1: 削除禁止フラグ】 scim_active == "true"        → 削除・復活操作の対象外（最強フラグ）
【判定 2: 除外】 serviceAccountClientLink != null / provisioned_by ∈ {local-admin, app, ldap} / admin role
【判定 3: 経路判定】 provisioned_by == "jit" → 90 日バッチ・Re-Activation 対象
                     "scim" → SCIM DELETE 待ち / "ldap" → LDAP Sync 委譲
                     manual・realm_import・null → 人間レビュー（自動処理しない）
```

混在 Case 表（`app` 行を追加した拡張版）:

| Case | 状態 | provisioned_by | scim_active | 90 日バッチ | Re-Activation |
|---|---|---|:---:|:---:|:---:|
| 1 | SCIM 先登録 → 後日 JIT ログイン | `scim`（維持） | `true` | 対象外 | 対象外 |
| 2 | JIT 先登録 → 後日 SCIM Push | `jit`→`scim`（更新） | `true` | 対象外 | 対象外 |
| 3 | JIT のみ | `jit` | 未設定/`false` | **対象** | **対象** |
| 4 | SCIM のみ（未ログイン含む） | `scim` | `true` | 対象外 | 対象外 |
| 5 | 管理者ローカル | `local-admin` | 未設定 | 対象外 | 対象外 |
| **6（新設）** | アプリ発 CRUD | `app` | 未設定 | 対象外（D3-05） | 対象外 |

実装上の不変条件（U2 に引き渡す 3 点、いずれも PoC 実証済み）:
1. **First Broker Login SPI は `provisioned_by` 未設定時のみ `jit` をセット**（Case 1/6 の上書き防止、[jit-scim §10.4.G.3 S2](../common/jit-scim-coexistence-keycloak.md) の Java 条件分岐）。
2. **per-Mapper syncMode 制御 + ライフサイクル属性の Mapper 非対象化**（U2 §2.5.4: IdP 既定 IMPORT、`mfa_indicator` のみ FORCE override）で `scim_active` / `provisioned_by` を上書きから保護（PoC V2 PASS、P-12）。
3. SPI は **3 系統 Flow 配置**（Browser forms サブフロー / First Broker / Post Broker、PoC F-6/V3''）+ 初回ログインで First と Post が連続発火するため debounce は両 Flow 対応。

### D3-08: SoT ルール

| 経路 | SoT | 本基盤の立場 | 削除の一次トリガー |
|---|---|---|---|
| ① JIT | 顧客 IdP | 受動キャッシュ（Pull） | 本基盤 90 日バッチ（推定、唯一の砦） |
| ② SCIM | 顧客 IdP / HRIS | SCIM Consumer（RFC 7644、SoT の指示に従う受動的立場） | SCIM PATCH active=false / DELETE |
| ③ LDAP | 顧客 AD/LDAP | User Storage 参照 | LDAP Sync（msad-user-account-control-mapper） |
| ④ local-admin | 本基盤運用 | 自身が SoT | 管理者操作 |
| ⑤ app | 同居アプリ | API 提供者 | アプリの deactivate API 呼出 |

**混在時ポリシーは「SCIM 優先」**（B-SCIM-JIT-1 の Phase 1 推奨をそのまま採用）: `scim_active=true` は他のすべての判定に優先する削除禁止・復活禁止フラグ。SCIM ユーザーの Inactive Detection は**顧客 IdP 責任**として契約に明記（ADR-025 §H.4.B 2026-07-15 確定、Auth0/Okta/Ping/Entra いずれも CIAM 層で行わず IGA 層委譲が業界標準）。

---

## 3.4 ライフサイクル設計

### D3-09: S1-S10 状態遷移 + 3 段階削除モデル

**状態機械**（全経路共通の 4 状態）:

```
[未登録] --①〜⑤ 作成--> [有効 enabled=true]
[有効] --S5/S6/S10/管理者/アプリ deactivate--> [無効 enabled=false + deprovisioned_at=now + not_before + Session Revoke]
[無効] --Re-Activation（jit のみ）/ SCIM active=true / 管理者・アプリ reactivate--> [有効]（deprovisioned_at クリア）
[無効] --deprovisioned_at + retention_years 経過（Phase 2 バッチ）--> [物理削除済（S3 Glacier アーカイブ後 DELETE CASCADE）]
```

**S1-S10 遷移表**（[jit-scim §10.4.G.2](../common/jit-scim-coexistence-keycloak.md) を設計確定。JIT = Pull / SCIM = Push の非対称が全行の根）:

| # | イベント | JIT（①） | SCIM（②） |
|---|---|---|---|
| S1 | 顧客 IdP でユーザ追加 | 何も起きない（初回ログインまで不可視） | 即時 POST → user_entity 作成（未ログインでも登録済） |
| S2 | 初回ログイン | First Broker Login → user + federated_identity 作成、SPI が `provisioned_by=jit`（未設定時のみ） | 既存ユーザに federated_identity 追加、`scim` 維持 |
| S3 | 通常ログイン | Post Broker Login → 属性 Sync + last_login 更新（debounce 1 日） | 同左（SCIM は認証に無関与） |
| S4 | IdP 側属性変更 | 次回ログインまで未反映（syncMode 依存） | 即時 PATCH 反映 |
| S5 | IdP 側無効化 | 検知不能 🚨（対策 B: 短命 AT 30 分 + RT Rotation で実質 Lag 短縮、P-09 / [jit-scim §10.7](../common/jit-scim-coexistence-keycloak.md)） | 即時 PATCH active=false → Soft Delete + Session Revoke |
| S6 | IdP 側削除（退職） | 検知不能、90 日バッチで推定 Soft Delete（最大 90 日 Lag、契約明記） | 即時 DELETE → Soft Delete（`scim_active=false` + `deprovisioned_at`） |
| S7 | 同一メールで再作成 | Handle Existing Account 分岐 — **デフォルト Confirm Link、Trusted IdP のみ Auto-Link**（ゲート B-JIT-LC-1） | 新 externalId で POST、matchByEmail 設定時のみ旧ユーザへマージ |
| S8 | IdP 差し替え（Entra→Okta） | 全ユーザ federated_identity 再リンク（Bulk migration、Phase 1 スコープ判定はゲート B-JIT-LC-2） | SCIM Endpoint 差し替え + 移行期間併用 |
| S9 | IdP 一時停止 | 既発行トークンで継続（TTL 内）— P-09 で上限 30 分 | 同左 |
| S10 | 90 日未ログイン | **Soft Delete（バッチ）→ Re-Activation SPI で復帰時自動有効化**。結果のアプリ通知はゲート B-JIT-LC-3 | 対象外（scim_active 保護、顧客 IdP の Inactive Detection 責任） |

**3 段階削除モデル**（[jit-scim §10.4.K.1](../common/jit-scim-coexistence-keycloak.md)）:

| 段階 | 内容 | Phase | 備考 |
|---|---|:---:|---|
| 第 1 段階: 認証遮断 | 短命 AT + RT Rotation（対策 B） | Phase 1 | 退職後 数分〜4h で実質遮断。PCI DSS 8.2.5 側の主対策 |
| 第 2 段階: Soft Delete | `enabled=false` + `not_before` + Session Revoke + **`deprovisioned_at=now` 必須セット** | Phase 1 | PCI DSS 8.2.6 "removed **or disabled**"（PCI SSC Information Supplement: フラグ disable で十分。物理削除を求める QSA はほぼ無い）。**顧客 IdP 側 disabled でも本基盤内の明示 Soft Delete は必須**（監査のシステムごと独立性、[jit-scim §10.4.H.3](../common/jit-scim-coexistence-keycloak.md)） |
| 第 3 段階: 物理削除 | `deprovisioned_at + retention_years` 経過後、監査ログ S3 Glacier Deep Archive → DELETE CASCADE + `idmap` 掃除 | **Phase 2** | 起算は `last_login` ではなく **`deprovisioned_at`**（退職判定時点起算が法規制の標準解釈、[jit-scim §10.4.K.6.5](../common/jit-scim-coexistence-keycloak.md)） |

**Phase 1 準備必須事項**（[jit-scim §10.4.K.6.6](../common/jit-scim-coexistence-keycloak.md)）:
1. **全 Soft Delete 経路（90 日バッチ / SCIM Facade / API 層 / 管理者操作）で `deprovisioned_at` をセット** — 1 箇所でも漏れると Phase 2 バッチの対象から永久に外れる。
2. Realm 属性 `retention_years`（デフォルト 3、顧客 override 5/7/10 — ゲート B-JIT-DEL-2）を Terraform で設定可能に。
3. Phase 1 の物理削除は**原則禁止**。4 層ガードレール（admin role に `delete-users` 非付与 / API 層で DELETE 動詞封鎖 / SCIM DELETE → Soft Delete 写像 / Aurora PITR）を適用（[jit-scim §10.5.1](../common/jit-scim-coexistence-keycloak.md)）。

**テナントレベル遷移**（[jit-scim §10.4.L](../common/jit-scim-coexistence-keycloak.md)、Runbook は U9 に引き渡し）: Pattern A（JIT→SCIM: matchByEmail + bulk update、B-SCIM-JIT-2）/ Pattern B（SCIM→JIT: `scim_active=false` + `provisioned_by=jit` + `last_login=now` の切替スクリプト必須 — 漏れると Zombie 永続化、B-TENANT-SWITCH-1）/ Pattern C（離脱: Day 0-30 エクスポート → Day 30 Realm disable → Day 90 全 Soft Delete + アーカイブ → retention_years 後物理削除 + 完了証明書、B-TENANT-EXIT-1）。

### D3-10: 責任分界 L1-L3 の設計反映

[jit-scim §10.4.H](../common/jit-scim-coexistence-keycloak.md) の 3 層モデルを本基盤の機能・契約・通知に対応付けて確定:

| 層 | 責任主体 | 本設計での実装 | 契約 / SLA 明記（U10・契約書へ） |
|---|---|---|---|
| **L1 本基盤 Hygiene** | 本基盤 | 90 日バッチ + Soft Delete + Re-Activation + SCIM 受信 + Health Check | 「JIT 顧客の Deprovisioning は最大 90 日 Lag。即時性が必要なら SCIM 実装」 |
| **L2 認証（本当の遮断）** | **顧客 IdP** | 本基盤は顧客 IdP のユーザ状態を操作しない | 「退職処理・SCIM ユーザの Inactive Detection は顧客 IdP 責任」 |
| **L3 認可** | アプリ | USER_DISABLED / USER_REACTIVATED / USER_DEPROVISIONED を EventBridge → Webhook で通知（通知範囲はゲート B-JIT-LC-3 / B-JIT-RA-2） | 「アプリは `sub` 主 ID + 通知受信で Role 剥奪を実施」 |

### D3-12: Re-Activation の条件仕様（実装は U2）

- 発火点: **Post Broker Login Flow が主戦場**（3 系統配置のうち）。
- 分岐（本書が仕様の SSOT）: `enabled=false` で復帰ログイン時、`jit` → 自動 `enabled=true` + `reactivated_at` + `deprovisioned_at` クリア / `scim` or `scim_active=true` → **拒否**（SCIM deprovisioning の意味喪失防止、セキュリティ上重大） / `local-admin`・`app`・未知 → 拒否。
- 監査: `USER_REACTIVATED` イベント必須発行 + 大量発生の異常検知（ADR-035 ITDR、U7）。
- 自動 vs 手動の最終方針はゲート B-JIT-RA-1（Phase 1 推奨 = 自動 + 監査 + 異常検知。厳格ポリシー顧客はテナント単位で手動切替可能に設計）。

---

## 3.5 SCIM 受信エンドポイント設計

### D3-11: 自作 SCIM Facade（native / Metatavu 非依存）

**方式決定**: PoC 実機検証（2026-07-10/13、[ADR-025 §I.2 更新](../adr/025-scim-positioning-and-receive-stance.md)）により、
- Keycloak **native inbound SCIM は不採用**（feature `scim-api:v1` 有効でも `/realms/{r}/scim/v2/*` が 404、V1 実測）。
- **Metatavu keycloak-scim-server は Phase 1 選定不要**（native 非依存方針のため）。
- **Phase 1 は「SCIM Facade」= SCIM 2.0（RFC 7643/7644）を受けて Keycloak Admin API に写像する自前の外部コンポーネント**を採用する（代替 A の延長。属性書込は Admin API + User Profile `ADMIN_EDIT` で実測 PASS 済み）。

**Metatavu PoC 残 3 点の位置づけ**: 当初 G-SCIM ゲートの 3 点（① KC 26.6 対応度 / ② カスタム属性書込 / ③ SPI 統合パス）は、**「native 非依存 + 代替 A」への方針転換で Phase 1 の前提からは外れた**（①②③とも Facade + Admin API 経路で実測クリア）。Metatavu は **Facade の実装工数が超過した場合、または Phase 2 で運用コスト削減する場合の代替候補**として保持し、採用判断時に限り 3 点を再検証する。G-SCIM ゲート（Baseline §1.5）は「**Facade の SCIM 2.0 準拠検証（Entra / Okta の SCIM Validator 通過 + D1/D2 E2E）**」として再定義する（§3.7）。なお [scim-deletion-realtime-detection.md §2/§9](../reference/scim-deletion-realtime-detection.md) の Metatavu 前提の記述は本書が上書きする（同 doc は Endpoint 構造・Rate Limit・ゾンビセッション対策の参照として引き続き有効）。

**エンドポイント構造**（D1/D2 の 2 方向、[ADR-025 §I.1](../adr/025-scim-positioning-and-receive-stance.md)）:

| 方向 | 受信側 | ベース URL（案） | 送信元 |
|---|---|---|---|
| D2: 顧客 IdP → Broker | Broker Acct の Facade | `https://scim-broker.<domain>/t/{tenant_id}/scim/v2` | Entra / Okta / Google / Ping の SCIM Provisioning。Auth0 は Event Streams workaround |
| D1: 顧客 HRIS → IdP-KC | IdP-KC Acct の Facade | `https://scim-idp.<domain>/t/{tenant_id}/scim/v2` | Workday / SAP / SmartHR 等 |

- **パスにテナントを含める**（`/t/{tenant_id}/scim/v2/Users|Groups`）。P-06 の単一 Realm 構成では realm でテナントを分けられないため、URL + トークンの二重照合でテナント解決する。
- サポート操作（Phase 1）: `POST /Users` `GET /Users(?filter=externalId eq ...)` `PUT/PATCH /Users/{id}` `DELETE /Users/{id}`（→ **Soft Delete に写像**、物理削除しない）。Groups は Phase 2。
- 処理パイプライン: Facade → Admin API（user + `user_attribute` + `idmap`）→ EventBridge（USER_DELETED/DISABLED）→ Session Revoke Lambda（`not_before` + Refresh 失効）。ゾンビ残余は AT TTL 30 分以内（P-09。[scim-deletion §6](../reference/scim-deletion-realtime-detection.md) の 4 手段中 ①② を Phase 1 必須、Back-Channel Logout は Phase 2 / U5）。
- **D1 Facade（IdP-KC Acct）は `idmap` を直接書かない**。`idmap` 更新は EventBridge クロスアカウントイベント → Broker Acct 側ハンドラ経由（U6 D-U6-02 の許可経路に追加済み）。Layer A FK の一元性を Broker Acct 側で維持（案 i、2026-07-23 整合性レビュー）。

**認証（テナント別 Bearer）**:

| 項目 | 決定 |
|---|---|
| 方式 | テナント専用の不透明 Bearer トークン（顧客 IdP の SCIM 設定に登録） |
| 保管 | AWS Secrets Manager（テナント別シークレット、Vault 相当）。Facade はハッシュ照合のみ |
| 照合 | トークン → tenant_id 解決結果と URL の `{tenant_id}` の**不一致は 403**（トークン漏えい時の横移動防止） |
| ローテーション | 90 日を標準（顧客 IdP 側再設定を伴うため Runbook 化、U9） |
| 経路 | P-18 のインターネット境界（CF+WAF+ALB）経由。IP 制限等は他組織監査 Acct への要求仕様（U6） |
| Rate Limit | テナント単位（初期値: 10 req/s、Entra の再試行仕様と整合させる。実値は U6 サイジングと合わせ確定） |

**externalId 突合**（受信時のマッチング順序、email 非依存 — ADR-018 整合）:

1. `user_attribute.scim_external_id == externalId`（第一キー、Entra は `oid` / Okta は不変 ID を externalId として送出させる）
2. `username == <tenant_id>-<userName>`（Layer B 一致）
3. `email`（**verified のみ、テナント設定 `matchByEmail=true` の場合に限る**。Pattern A 移行時の既存 JIT ユーザ紐付け用）
4. 不一致 → 新規作成（`provisioned_by=scim` + `scim_active=true` + `scim_external_id` + `deprovisioned_at` なし）

**SCIM Health Check**（Inactive Detection とは別次元の「連携インフラ生存確認」、本基盤責任 — [jit-scim §10.4.K.4](../common/jit-scim-coexistence-keycloak.md)）: ① 直近受信 24h 超で警告 ② 操作頻度がベースライン比 50% 以下 ③ HTTP エラー率 5% 以上 ④ ユーザ数 1h で 10% 超変動。Grafana + Alertmanager（ADR-053 / U9 実装）。閾値カスタマイズはゲート B-SCIM-HC-1。

---

## 3.6 本書の決定一覧（D3 サマリ）

| # | 決定 | 主根拠 |
|---|---|---|
| D3-01 | 3 階層識別子の格納先（A=user_entity.id / B=username `<tenant>-<userid>`+external_id / C=federated_identity）+ User Profile 明示宣言 | ADR-018/054、ADR-025 §I.3、PoC F-3 |
| D3-02 | email は補助属性。突合第一キーは tenant_id + IdP 不変 ID。S7 デフォルト Confirm Link | ADR-018、B-JIT-LC-1 |
| D3-03 | マッピング DB = user_attribute 主 + Aurora `idmap` 補助（履歴行方式 DDL）。Broker 非保持・JWT 非搭載・API 層経由参照 | ADR-054 §C、ADR-033、P-10 |
| D3-04 | プロビ 5 経路 + `provisioned_by` 値体系（`app` + `provisioned_app` 新設、未知値は安全側） | jit-scim §10.4.B、P-17 |
| D3-05 | アプリ発 CRUD は専用 API 層（ADR-038 基盤共用）。Admin API 直・SCIM 経由は却下 | P-17、jit-scim §10.5.1 ガードレール |
| D3-06 | `app` ユーザは 90 日バッチ対象外 + Re-Activation 禁止 + アプリの deactivate 呼出義務 | jit-scim §10.4.H.3 監査独立性 |
| D3-07 | Case 1-6 判別 3 段階、scim_active 最強フラグ、per-Mapper syncMode=IMPORT、SPI 3 系統配置 | PoC V2/V3''、P-12 |
| D3-08 | SoT ルール表 + 混在時「SCIM 優先」 | ADR-025 §H.4.B、RFC 7644 |
| D3-09 | 4 状態機械 + S1-S10 + 3 段階削除 + `deprovisioned_at` 全経路必須 + `retention_years` Realm 属性 | jit-scim §10.4.G/K、PCI DSS 8.2.6 |
| D3-10 | 責任分界 L1-L3 の契約・通知への反映 | jit-scim §10.4.H |
| D3-11 | SCIM 受信 = 自作 Facade（native/Metatavu 非依存）、テナント別 URL+Bearer、externalId 突合順序 | ADR-025 §I.2（PoC 確定）、P-06 |
| D3-12 | Re-Activation 条件仕様（jit のみ許可、他は全拒否 + 監査） | jit-scim §10.4.I |
| D3-13 | ゲート追跡表を本書 §3.7 で一元管理（Wave ごとに更新） | 00-plan §5 |

---

## 3.7 未決事項 + Phase 1 前ゲート追跡表（D3-13）

### 3.7.1 Phase 1 契約前ゲート 8 項目（[hearing-checklist.md](../requirements/hearing-checklist.md) と同期）

| ゲート | 内容 | 本書の暫定値（未通過時のデフォルト） | 影響節 | 状態 |
|---|---|---|---|:---:|
| **B-JIT-LC-1** 🚨 | S7 Handle Existing Account ポリシー | Confirm Link デフォルト + Trusted IdP のみ Auto-Link | §3.4 S7 | ⬜ 未通過 |
| **B-JIT-RA-1** 🚨 | Re-Activation 自動 vs 手動 | 自動 + 監査ログ + ITDR 異常検知、テナント単位で手動切替可 | §3.4 D3-12 | ⬜ 未通過 |
| **B-SCIM-JIT-1** 🚨 | 混在時 Deprovisioning ポリシー | SCIM 優先（scim_active 最強フラグ） | §3.3 | ⬜ 未通過 |
| **B-SCIM-JIT-3** 🚨 | 顧客 IdP の Inactive Detection 機能有無 | 有り前提（無い顧客は PS 個別対応 or JIT 切替提案） | §3.3 / 契約 | ⬜ 未通過 |
| **B-JIT-DEL-1** 🚨 | 物理削除方針（Phase 1 なし）への顧客同意 | Soft Delete のみ + 4 層ガードレール | §3.4 D3-09 | ⬜ 未通過 |
| **B-JIT-DEL-2** 🚨 | `retention_years`（3/5/7/10） | デフォルト 3 年、Realm 属性 override | §3.4 D3-09 | ⬜ 未通過 |
| **B-SCIM-HC-1** 🟡 | Health Check 閾値カスタマイズ | デフォルト 4 閾値（24h/50%/5%/10%） | §3.5 | ⬜ 未通過 |
| **B-TENANT-SWITCH-1** / **B-TENANT-EXIT-1** 🚨 | JIT↔SCIM 切替 / 離脱時削除方針 | §10.4.L Pattern A/B/C Runbook 案 | §3.4 | ⬜ 未通過 |

### 3.7.2 技術検証ゲート（Baseline §1.5 の U3 担当分）

| ゲート | 内容 | 本書での再定義 | 状態 |
|---|---|---|:---:|
| **G-SCIM** | 旧: Metatavu 3 点検証 | **再定義: SCIM Facade の SCIM 2.0 準拠検証**（Entra/Okta SCIM Validator + D1/D2 E2E + Soft Delete 写像 + `deprovisioned_at` セット確認）。Metatavu 3 点は Metatavu 採用判断時のみ再検証（§3.5） | ⬜ |
| **G-LDAP**（= B-SCIM-13）🚨 最優先 | LDAP User Federation 経由の SPI 発火検証 | LDAP は Broker Flow を通らないため First/Post Broker 配置 SPI が**動かないリスク**。FAIL 時は経路 ③ の deprovisioning 設計（LDAP Sync 委譲、D3-04）が唯一の防御となるため、Browser forms 配置での発火可否 + 追加 Flow 要否を確定 | ⬜ |
| B-SCIM-12 ⚠ | SAML IdP 経由フェデ JIT の SPI 検証（V3'''） | First/Post Broker 共通のため PASS 見込みだが NameID handling 差を確認 | ⬜ |
| B-SCIM-14 ⚠ | 実 IdP（Entra/Okta trial）統合テスト | Phase 1 β 必須。Claims マッピング / `iss` 形式 / **SPI ①での** `provisioned_by=jit` セット確認 | ⬜ |

### 3.7.3 本書の未決事項（新規）

| # | 未決事項 | 暫定 | 決定期限 |
|---|---|---|---|
| U3-OP-1 | `app` ユーザの 90 日バッチ**オプトイン**（Inactive Detection 未実装アプリ向け）を Phase 1 設定に含めるか | 含める（テナント × クライアント単位フラグ） | U2 Flow 設計確定時 |
| U3-OP-2 | `idmap` 補助 DB の物理配置（Broker Acct Aurora 同居 vs 独立クラスタ）とアプリからの参照経路（クロスアカウント） | Broker Acct Aurora 別 DB + API 層経由のみ | U6 §6.8 に登録済み |
| U3-OP-3 | SCIM Facade の実装形態（ECS/ROSA 上のサービス vs Lambda + API GW）とレイテンシ要件 | ROSA 上の常駐サービス（KC と同一クラスタ運用） | U6 §6.8 に登録済み |
| U3-OP-4 | D1（HRIS → IdP-KC）利用顧客の HRIS が SCIM 非対応の場合のアダプター（ADR-054 §B.3 の Lambda アダプター）を Phase 1 に含めるか | Phase 2 | 契約時 |
| U3-OP-5 | B-IDM-4/5（顧客内 ID 衝突 / 顧客間衝突）の回答による `username` 生成規則の複合キー化 | `<tenant>-<userid>` で衝突しない前提 | ヒアリング回答時 |
| U3-OP-6 | B-MIG-12（旧 user_id の保持期間）— `idmap` 履歴行の valid_to 後の掃除ポリシー | 永続保持（retention_years 到達で物理削除に同調） | ヒアリング回答時 |

### 3.7.4 U2 への引き渡し事項（Wave 1 相互参照）

1. User Profile 宣言属性一覧（D3-01 表）→ realm.json 化
2. First Broker Login SPI の `provisioned_by` 条件分岐 + Re-Activation SPI の `app` 明示拒否分岐（D3-04/D3-12）
3. per-Mapper syncMode=IMPORT 対象属性（`scim_active` / `provisioned_by`）
4. 専用 API 層クライアントの Client Credentials スコープ設計（D3-05、U5 とも連携）
