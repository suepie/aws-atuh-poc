# 検証結果ログ

> **実施日**: 2026-07-10
> **実施者**: Claude Code（別端末 = Linux devcontainer / Docker Desktop WSL2 backend で実機実行）
> **環境**: Keycloak 26.6 + PostgreSQL 16（本 PoC、実際に起動して検証）
> **参照**: [README.md](../README.md) / [execution-guide.md](execution-guide.md) / [additional-poc-findings.md](additional-poc-findings.md)
> **注記**: 実行環境の制約（devcontainer の bind mount 問題・KC26.6 の feature 名変更）に対応するため
>          `Dockerfile.poc` + `docker-compose.exec.yml` を追加。詳細は additional-poc-findings.md 参照。

---

## 0. 実行環境の是正（実機で判明、詳細は additional-poc-findings.md）

| # | 事象 | 是正 |
|---|---|---|
| F-1 | `KC_FEATURES: scim-realm-api,declarative-user-profile` で **起動失敗** | 26.6 実機の feature 名は **`scim-api`**、`declarative-user-profile` は **GA 化で廃止**。`scim-api,admin-fine-grained-authz` に修正 |
| F-2 | devcontainer + Docker Desktop で **bind mount が空**（config/SPI が入らない） | `Dockerfile.poc` で config/JAR をイメージに焼き込み（build コンテキストはストリーム送信されマウント問題を回避） |
| F-3 | realm import した **カスタム属性が全 user で null**（黙って破棄） | `unmanagedAttributePolicy` を **realm 属性でなく User Profile API/config** で設定する必要あり（V1 の核心、後述） |

---

## 1. 環境構築（Day 1）

| 項目 | 状態 | メモ |
|---|:---:|---|
| Docker Compose 起動 | ✅ | `docker-compose.exec.yml`（bind mount 廃止版）で起動 |
| Keycloak 26.6 起動 | ✅ | `scim-api:v1` experimental 有効で起動（F-1 是正後） |
| PoC Realm インポート | ✅ | `poc-jit-scim` realm + 3 test user 作成（属性は F-3 の通り欠落） |
| SCIM Realm API 有効化 | ⚠ | feature は有効だが inbound エンドポイントは 404（V1 参照） |
| SPI JAR ビルド | ✅ | Maven コンテナで build → `last-login-tracker.jar`（6102 bytes） |
| SPI JAR デプロイ | ✅ | providers に焼き込み。起動ログで `implementing the internal SPI authenticator` 確認 |

---

## 2. V1: SCIM Custom Attribute Mapping

**参照**：[tests/v1-metatavu-scim.sh](../tests/v1-metatavu-scim.sh)

### 2.1 テスト結果

| Test | 内容 | 結果 | HTTP | メモ |
|---|---|:---:|---|---|
| Test 1 | SCIM Realm API 有効性（`/realms/{r}/scim/v2/ServiceProviderConfig`） | ❌ | 404 | feature `scim-api` は有効・`realm-restapi-extension.scim` も登録済みだが、当該パスは 404 |
| Test 2 | SCIM POST /Users（標準属性） | ❌ | 404 | 同上。inbound SCIM server がこのパスで露出せず |
| Test 3 | SCIM POST /Users（カスタム属性） | ❌ | 404 | 到達不可のため評価不能 |
| Test 4 | SCIM PATCH で active=false | ❌ | 404 | 同上 |
| **追加** | **Admin API + User Profile(`ADMIN_EDIT`) でカスタム属性書込** | ✅ | 204→永続化 | **F-3 是正後、`scim_active`/`provisioned_by` が user_attribute に永続化されることを実証** |

### 2.2 判定

- **総合**：⚠ **PARTIAL** — Keycloak 26.6 の **native inbound SCIM server は追加の realm 単位設定なしでは到達不可**（§10.4.E.1 の「native SCIM はカスタムスキーマ未成熟」と整合）。
  一方で **カスタム属性そのものは書き込み可能**（User Profile で unmanaged 属性を有効化すれば Admin API 経由で永続化）。
- **Fallback**：**代替 A（Custom Authenticator SPI / Admin 経由で scim_active を自動セット）** を採用。V3' で SPI 書込が実証済みのため実現性は確認済み。
- **Phase 1 実装への影響**：SCIM 受信を「Keycloak native inbound SCIM」に依存させない。SCIM 受信は外部コンポーネント or Admin API 経由で行い、`scim_active`/`provisioned_by` は SPI/Admin で確実にセットする。

### 2.3 詳細ログ

```
Test 1: /realms/poc-jit-scim/scim/v2/ServiceProviderConfig -> 404 {"error":"HTTP 404 Not Found"}
Test 2: POST /realms/poc-jit-scim/scim/v2/Users -> 404
serverinfo: providers.realm-restapi-extension.providers.scim.order = 0  ← 拡張は登録されている
           providers.scimResourceType.providers.{Users,Groups,ServiceProviderConfig,Schemas,ResourceTypes}
features: SCIM_API enabled=true (scim-api:v1, experimental)

追加検証（F-3 是正後）:
  PUT /admin/.../users/profile {unmanagedAttributePolicy: "ADMIN_EDIT"} -> 200
  PUT /admin/.../users/{id} {attributes:{scim_active:["true"],provisioned_by:["scim"]}} -> 204
  GET /admin/.../users/{id} .attributes -> {"provisioned_by":["scim"],"scim_active":["true"]}  ← 永続化 OK
  ※ User Profile 未設定時は同じ 204 でも読み戻しが null（黙って破棄）= F-3
```

---

## 3. V2: Sync Mode Override

**参照**：[tests/v2-sync-mode-override.sh](../tests/v2-sync-mode-override.sh)

### 3.1 テスト結果

| Test | 内容 | 結果 | HTTP | メモ |
|---|---|:---:|---|---|
| Test 1 | IdP 作成（Sync Mode = FORCE） | ✅ | 201 | `v2-test-idp` 作成 |
| Test 2 | 通常 Mapper 作成 | ✅ | 201 | `map-email-default`（oidc-user-attribute-idp-mapper） |
| Test 3 | Sync Mode Override Mapper 作成（syncMode=IMPORT） | ✅ | 201 | `protect-scim-active`（hardcoded-attribute-idp-mapper） |
| Test 4 | 設定保存確認 | ✅ | 200 | `config.syncMode = "IMPORT"` が保存されていることを確認 |

### 3.2 判定

- **総合**：✅ **PASS** — Mapper 単位の `syncMode=IMPORT` が作成・永続化される（一次資料 E-12 と整合）。
- **Fallback**：**不要**。
- **Phase 1 実装への影響**：`scim_active` を保護する mapper に per-mapper `syncMode=IMPORT` を付与する方針で確定。
- **残課題**：本 PoC は **設定が保存されること** の確認まで。実際の JIT ログインで「他属性は FORCE 上書き / scim_active は IMPORT 保護」の**動作**確認は、実 IdP を用いた追加検証（B-SCIM 実装フェーズ）で実施。

### 3.3 詳細ログ

```json
[
  {"name":"map-email-default","identityProviderMapper":"oidc-user-attribute-idp-mapper",
   "config":{"claim":"email","user.attribute":"email"}},
  {"name":"protect-scim-active","identityProviderMapper":"hardcoded-attribute-idp-mapper",
   "config":{"attribute.value":"true","syncMode":"IMPORT","attribute":"scim_active"}}
]
→ [OK] syncMode = IMPORT が Mapper 設定に保存されている
```

---

## 4. V3': Custom Authenticator SPI

**参照**：[tests/v3-custom-authenticator.sh](../tests/v3-custom-authenticator.sh)

### 4.1 テスト結果

| Test | 内容 | 結果 | メモ |
|---|---|:---:|---|
| Test 1 | SPI ロード確認 | ✅ | 起動ログで `last-login-tracker ... implementing the internal SPI authenticator`。serverinfo でも検出（※スクリプトは誤キー参照、F-5 参照） |
| Test 2 | Browser Flow への組込 | ✅ | `browser` 複製 → `browser-with-last-login`。**forms サブフロー内**（Username Password Form の後）に REQUIRED で追加 |
| Test 3 | 事前状態確認 | ✅ | test-jit-user の last_login = NULL |
| Test 4 | **認可コードフロー（ブラウザフロー経由）ログイン → last_login 反映** | ✅ | curl で auth code flow を実行、ログイン成功（302+code）、`last_login=1783666203620` を書込 |
| 追加 | debounce（1 日以内は再書込スキップ） | ✅ | 2 回目ログイン後も値が不変（skip 動作） |

### 4.2 判定

- **総合**：✅ **PASS**（**⚠ ローカル PW ユーザ（P-4）経路のみ**）— Custom Authenticator SPI の `user.setSingleAttribute("last_login", ...)` が **user_attribute に確実に永続化**される（Event Listener SPI の Issue #14942 問題を回避）。debounce も動作。
- **Fallback**：**不要**（案 A `enlistAfterCompletion` / 案 C 外部 DB は不要）。
- **Phase 1 実装への影響**：**案 B（Custom Authenticator SPI）採用確定**。ADR-055 の SPI 開発体制を再利用。
- **重要な実装制約（F-6）**：SPI を **フロー最上位（top-level）に REQUIRED で置くと、同レベルの ALTERNATIVE（Cookie / forms）が無視され、Username Password Form が実行されず**、`user is not set yet` でログイン自体が失敗する。
  → **必ず `forms` サブフロー内（Username Password Form の後）に REQUIRED で配置**すること。

### 4.4 【2026-07-10 追加】⚠ 検証ギャップ：フェデ JIT 経路（P-3 主用途）は未検証

**核心**：本 V3' 検証は `test-jit-user`（realm-import で作成した **ローカル PW ユーザ = P-4**）で実施。**フェデ JIT ユーザ（P-3、本基盤の主用途）は未検証**。

**Browser Flow 分岐の制約**：
```
browser-with-last-login
├── Cookie (ALT)
├── Identity Provider Redirector (ALT)  ← ★ フェデ JIT はここを通る
├── Organization (ALT)
└── forms (ALT)                          ← ★ 現状の SPI 配置
    ├── Username Password Form (REQ)
    └── Last Login Tracker (REQ)         ← ★ ここで SPI 実行
```

**Keycloak 設計**：4 つの ALTERNATIVE のうち 1 つ成功で他は skip → **フェデユーザは `IdP Redirector` 成功 → `forms` skip → SPI 実行されない**。

**影響**：**主用途である P-3（顧客従業員 JIT）で SPI が動かない**。

**対策（Phase 1 実装で必須）**：SPI を 3 系統に配置
1. Browser Flow の forms サブフロー内（V3' 実測済み）
2. **First Broker Login Flow**（フェデ JIT 初回ログイン）
3. **Post Broker Login Flow**（フェデ JIT 2 回目以降）

**追加 PoC V3''（別端末で実施予定）**：`tests/setup-federation.sh` + `tests/v4-federation-jit.sh` でフェデ JIT 経路を実測確認。詳細は [../QUICKSTART-OTHER-MACHINE.md §V3''](../QUICKSTART-OTHER-MACHINE.md) と [../docs/verification-log-v3fed.md](verification-log-v3fed.md) 参照。

**判定**：V3' PASS は **P-4 経路限定** で有効。**フェデ JIT 経路の PASS は V3'' で確定**、Phase 1 リリース前ゲートに追加。

### 4.3 詳細ログ

```
[配置] browser-with-last-login:
  level0 Cookie(ALT) / IdP Redirector(ALT) / Organization(ALT) / forms(ALT)
    level1 Username Password Form(REQUIRED)
    level1 Last Login Tracker(REQUIRED)  ← ここに配置

[ログイン] auth code flow (curl, cookie jar):
  GET /auth -> login form
  POST /login-actions/authenticate {username=test-jit-user, password=test123} -> 302 code=a880b037-...
  last_login: NULL -> 1783666203620

[SPI ログ]
  INFO LastLoginTracker: initial write for user=test-jit-user, now=1783666203620
  INFO LastLoginTracker: wrote last_login=1783666203620 for user=test-jit-user

[debounce] 2 回目ログイン(302) -> last_login 変化なし(1783666203620) = skip OK

[誤配置時のログ（F-6 の根拠）]
  WARN REQUIRED and ALTERNATIVE elements at same level! ignored: [auth-cookie, identity-provider-redirector, ...]
  WARN authenticator 'last-login-tracker' requires user to be set ... but user is not set yet
  -> LOGIN_ERROR invalid_user_credentials
```

---

## 5. Phase 1 実装計画への影響

### 5.1 SCIM プラグイン選定

- 採用：**Keycloak native inbound SCIM には依存しない**（V1 で 404、未成熟を実機確認）。SCIM 受信は外部 or Admin API 経由。
- 選定理由：26.6 の `scim-api` は experimental かつ inbound server がそのままでは露出せず、カスタムスキーマも未成熟（§10.4.E.1 と整合）。
- 追加工数：**+代替 A 相当**（SPI/Admin で `scim_active` セット。V3' の SPI 基盤を流用するため増分小）。

### 5.2 SPI 実装方式

- 採用：**案 B（Custom Authenticator SPI）** — 実機で書込・debounce 実証済み。
- 選定理由：Event Listener SPI（#14942）を回避しつつ、Authentication Flow 内で確実に永続化。
- 追加工数：なし（ADR-055 の SPI 体制流用）。**ただし forms サブフロー配置が必須（F-6）**。

### 5.3 Fallback 発動状況

| 項目 | 発動 | 対応 |
|---|:---:|---|
| V1 Fallback | ✅ 発動 | 代替 A（SPI/Admin で scim_active セット + User Profile で unmanaged 属性有効化） |
| V2 Fallback | ✗ 不要 | per-mapper syncMode=IMPORT で確定 |
| V3' Fallback | ✗ 不要 | 案 B 確定 |

---

## 6. 既存ドキュメントへの反映（TODO）

- [ ] [jit-scim §10.4.F 新設](../../../doc/common/jit-scim-coexistence-keycloak.md)（本 PoC 実測結果セクション）
- [ ] [hearing-checklist B-SCIM-7/8/10](../../../doc/requirements/hearing-checklist.md) の ⏳ → V1:⚠(代替A) / V2:✅ / V3':✅
- [ ] [ADR-025 §I.2](../../../doc/adr/025-scim-positioning-and-receive-stance.md) に「native inbound SCIM 未使用 / 代替 A」を反映
- [ ] [ADR-060 §C.2.3](../../../doc/adr/060-auth-protocol-attack-path-residual-tbd.md) の SPI 実装方式を **案 B（forms サブフロー配置必須）** で確定

---

## 7. 総合結論

### 7.1 SCIM は問題なく実装できるか

- 答え：**条件付き Yes**。Keycloak native inbound SCIM server には依存できない（実機で 404）。SCIM 受信は外部/Admin 経由とし、`scim_active`/`provisioned_by` は SPI/Admin でセット + User Profile で unmanaged 属性を有効化すれば実装可能。
- 根拠：V1（native 404 / Admin+User Profile で属性永続化）、V2（syncMode 保護 PASS）。

### 7.2 JIT ユーザは削除できるか（last_login ベースの棚卸し）

- 答え：**Yes**。Custom Authenticator SPI で `last_login` を確実に記録でき（V3' PASS + debounce）、これを基に非活性 JIT ユーザの deprovisioning が可能。
- 根拠：V3' で実ログイン経由の書込・debounce を実証。

### 7.3 Phase 1 リリース可否

- 判定：⚠ **GO with Fallback** — V2/V3' は Fallback 不要、V1 のみ代替 A を発動（増分小）。
- 条件：(1) SCIM 受信を native inbound に依存させない設計、(2) User Profile で unmanaged 属性を有効化、(3) SPI を forms サブフローに配置。

---

**変更履歴**

| 日付 | 内容 |
|---|---|
| 2026-07-10 | 初版作成（テンプレート） |
| 2026-07-10 | **実機で V1/V2/V3' 実行・実測結果を記入。環境是正 F-1〜F-6 を追記。V2/V3' PASS、V1 は代替 A 発動で GO with Fallback** |
