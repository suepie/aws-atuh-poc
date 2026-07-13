# PoC 計画書：JIT ユーザ削除 + SCIM 実装可能性検証（V1/V2/V3'）

> **作成日**: 2026-07-10
> **対象**: Phase 1 実装開始前ゲート 3 点の検証
> **背景**: [jit-scim §10.4.E 一次資料調査 14 件](../../doc/common/jit-scim-coexistence-keycloak.md) で判明した重大課題
> **ゲート項目**: [hearing-checklist B-SCIM-7/8/10](../../doc/requirements/hearing-checklist.md)

---

## ✅ 実行結果サマリ（2026-07-10 実機検証済み）

> 本 PoC を実機（Linux devcontainer / Docker Desktop WSL2）で **実際に起動・実行**した結果。
> 詳細は [docs/verification-log.md](docs/verification-log.md)、実行中に判明した不備・是正は [docs/additional-poc-findings.md](docs/additional-poc-findings.md)。

| 検証 | ゲート | 判定 | 要点 |
|---|---|:---:|---|
| **V1** SCIM カスタム属性 | B-SCIM-7 | ⚠ **PARTIAL** | native inbound SCIM は feature 有効でも `/scim/v2/*` が **404**。ただし User Profile で unmanaged 属性を有効化すれば **Admin API 経由で `scim_active`/`provisioned_by` は永続化可** → **代替 A** で実装可能 |
| **V2** Sync Mode Override | B-SCIM-8 | ✅ **PASS** | per-Mapper `syncMode=IMPORT` が作成・保存される（E-12 整合、Fallback 不要） |
| **V3'** Custom Authenticator SPI（P-4 ローカル PW） | B-SCIM-10 | ✅ **PASS** | 認可コードフロー経由ログインで **`last_login` 書込を実証** + **debounce 動作**確認 → **案 B 確定** |
| **V3''** フェデ JIT 経路（P-3 主用途） | B-SCIM-11 | ✅ **PASS** | 二段認可コードフローで **First Broker Login Flow（初回）+ Post Broker Login Flow（2 回目）** の SPI 書込を実証 → **3 系統 Flow 配置で確定**。詳細 [docs/verification-log-v3fed.md](docs/verification-log-v3fed.md) |

**総合判定：⚠ GO with Fallback**（V2/V3'/V3'' は Fallback 不要、V1 のみ代替 A を発動＝増分小）

### 実行中に判明した是正点（実機でしか分からなかった 8 件）

| # | 事象 | 是正 |
|---|---|---|
| F-1 | KC26.6 の feature 名変更：`scim-realm-api`→**`scim-api`**、`declarative-user-profile` は **GA 廃止**（旧名で起動失敗） | `docker-compose.yml` 修正済 |
| F-2 | devcontainer で **bind mount が空**（daemon=docker-desktop がパス不可視） | `Dockerfile.poc` + `docker-compose.exec.yml` で焼き込み |
| F-3 | realm import の `unmanagedAttributePolicy`(realm 属性) が無効 → **カスタム属性が黙って破棄** | `config/user-profile-poc.json` 追加（User Profile で設定） |
| F-4 | native inbound SCIM が 404（追加の realm 設定なしでは露出せず） | native に依存しない設計（代替 A） |
| F-5 | `v3-*.sh` の SPI 検出が **誤キー**でクラッシュ（`AuthenticatorFactory`→`Authenticator`） | スクリプト修正済 |
| F-6 | SPI を **top-level REQUIRED** に置くとログイン失敗（forms が無視される） | **forms サブフロー内**配置が必須 |
| F-7 | `setup-federation.sh` が IdP をフロー作成前に作り **500**（`No available authentication flow`） | フロー作成後に紐付ける **Step6** 追加（1 パス完走を検証済） |
| F-8 | `user-profile-poc.json` の `_comment` を UPConfig が拒否し **400** | JSON から `_comment` 除去 |

### Phase 1 実装への確定事項

- **SCIM 受信**：Keycloak native inbound SCIM に依存しない。外部/Admin 経由で受信し `scim_active`/`provisioned_by` を SPI/Admin でセット（代替 A）+ User Profile で対象属性を宣言。
- **last_login 記録**：**案 B（Custom Authenticator SPI）** 採用。ADR-055 の SPI 体制を流用。**SPI は 3 系統 Flow 配置**（Browser forms / First Broker Login / Post Broker Login）で P-4・P-3 両経路をカバー（F-6 / V3''）。
- **scim_active 保護**：per-Mapper `syncMode=IMPORT` で確定。

### 再現方法（この環境）

```bash
cd poc/jit-scim-verification-2026-07-10/
docker compose -f docker-compose.exec.yml build && docker compose -f docker-compose.exec.yml up -d
docker network connect poc-jit-scim-exec_default "$(hostname)"   # sibling container 間通信
export KC_URL=http://poc-keycloak-266:8080
./tests/v2-sync-mode-override.sh   # PASS
./tests/v1-metatavu-scim.sh        # native SCIM 404 → 代替 A
# V3' は docs/verification-log.md §4 の手順（User Profile 有効化 + forms 配置 + auth code flow）
```

---

## 0. PoC の目的

**Phase 1 リリース前ゲートの 3 検証を実施し、実装方式を確定する**:

1. **V1（B-SCIM-7 🚨）**：Metatavu keycloak-scim-server で `scim_active` / `provisioned_by` カスタム属性を user_attribute に書き込めるか
2. **V2（B-SCIM-8 🔴）**：Sync Mode = FORCE でも Mapper 単位 `syncMode=IMPORT` で `scim_active` を保護できるか
3. **V3'（B-SCIM-10 🚨）**：**Custom Authenticator SPI** で `last_login` を user_attribute に確実に書き込めるか（Event Listener SPI 版は Issue #14942 で動かない可能性）

**判定結果次第で Fallback**:
- V1 失敗 → **代替 A**（Custom Authenticator SPI で SCIM 受信時に自動セット）
- V2 失敗 → Realm 全体 IMPORT 化、SCIM Push 遅延受容
- V3' 失敗 → **案 A**（`enlistAfterCompletion`）or **案 C**（外部 DB 別管理）

---

## 1. PoC 環境

### 1.1 スタック

| コンポーネント | バージョン | 選定理由 |
|---|---|---|
| **Keycloak** | **26.6.x**（Latest stable）| Native SCIM Realm API + User Profile 対応 |
| **PostgreSQL** | 16 | Keycloak デフォルト DB、既存 PoC 互換 |
| **Metatavu keycloak-scim-server** | Latest（要 GitHub 確認）| [ADR-025 §I.2](../../doc/adr/025-scim-positioning-and-receive-stance.md) 選定済み |
| **JDK** | 17 | Keycloak 26 要件 |
| **Maven** | 3.9+ | SPI ビルド用 |
| **curl / jq** | any | テスト実行用 |

### 1.2 ディレクトリ構成

```
poc/jit-scim-verification-2026-07-10/
├── README.md                    # 本書
├── docker-compose.yml           # 環境定義
├── config/
│   ├── realm-poc.json           # PoC 用 Realm 設定
│   └── user-profile-config.json # User Profile schema
├── spi/
│   └── last-login-tracker/      # Custom Authenticator SPI
│       ├── pom.xml
│       ├── build.sh
│       └── src/main/
│           ├── java/com/example/keycloak/spi/
│           │   ├── LastLoginTrackerAuthenticator.java
│           │   └── LastLoginTrackerAuthenticatorFactory.java
│           └── resources/META-INF/services/
│               └── org.keycloak.authentication.AuthenticatorFactory
├── tests/
│   ├── v1-metatavu-scim.sh      # V1 テストスクリプト
│   ├── v2-sync-mode-override.sh # V2 テストスクリプト
│   ├── v3-custom-authenticator.sh # V3' テストスクリプト
│   └── common.sh                # 共通ヘルパー
└── docs/
    ├── execution-guide.md       # 実行手順書
    └── verification-log.md      # 検証結果ログ（実施後）
```

---

## 2. 検証項目詳細

### 2.1 V1: Metatavu SCIM Custom Attribute Mapping

**確認事項**：
- ✅ Metatavu keycloak-scim-server が Keycloak 26.6 で起動できるか（README 明記なし、[E-2](../../doc/common/jit-scim-coexistence-keycloak.md)）
- ✅ POST /Users で `scim_active=true` / `provisioned_by=scim` を user_attribute に書き込めるか
- ✅ PUT /Users {active: false} で `scim_active=false` に更新されるか
- ✅ DELETE /Users で `user_entity.enabled=false` + `scim_active=false` 更新されるか

**成功基準**：
- Keycloak Admin API で `user_attribute.scim_active` の値が期待通り更新されている
- SCIM API のレスポンスが RFC 7644 準拠

**失敗基準**：
- Metatavu が Keycloak 26.6 で起動しない
- カスタム属性が user_attribute に書き込まれない
- SCIM API がエラーを返す

**Fallback**：**代替 A**（[jit-scim §10.4.E.1 代替 A](../../doc/common/jit-scim-coexistence-keycloak.md)） — Keycloak 26 native SCIM + Custom Authenticator SPI で scim_active を自動セット

### 2.2 V2: Sync Mode Override

**確認事項**：
- ✅ Identity Provider を Sync Mode = FORCE で作成
- ✅ Attribute Mapper に `syncMode = IMPORT` を extra_config で設定
- ✅ SCIM で事前作成した user の `scim_active=true` が JIT ログイン後も保持される
- ✅ その他の属性（email 等）は FORCE で上書きされる

**成功基準**：
- SCIM 事前作成 → JIT ログイン → `scim_active` の値が変わらない
- 他属性は IdP アサーション値で上書きされる

**失敗基準**：
- Mapper 単位 syncMode が動作せず、`scim_active` が消失
- Realm デフォルト syncMode に override できない

**Fallback**：Realm 全体を IMPORT にする（SCIM Push 反映遅延受容）

### 2.3 V3': Custom Authenticator SPI

**確認事項**：
- ✅ Custom Authenticator SPI（Java）で `user.setSingleAttribute("last_login", ...)` が実際に user_attribute に書き込まれるか
- ✅ Browser Flow 末尾に組込 → ログイン試行 → user_attribute.last_login が反映
- ✅ debounce（1 日以内なら更新スキップ）が動作
- ✅ [Keycloak Issue #14942](https://github.com/keycloak/keycloak/issues/14942) の Event Listener SPI 版と挙動比較

**成功基準**：
- LoginFlow 経由の `setSingleAttribute` が確実に永続化
- 2 回目ログイン時に前回の last_login 値を取得可能

**失敗基準**：
- Authenticator 内でも `setSingleAttribute` が動かない
- Transaction エラー

**Fallback**：
- 案 A（`enlistAfterCompletion`）試行
- 案 C（EventBridge + Lambda + DynamoDB 外部 DB 別管理）

---

## 3. 実施タイムライン（3 日想定）

| Day | タスク | 成果物 |
|---|---|---|
| **Day 1（環境構築）**| Docker Compose 起動 + Keycloak 26.6 + PostgreSQL + Metatavu SCIM デプロイ + PoC Realm 作成 | ✅ 全コンポーネント起動 |
| **Day 2（V1 + V2 実施）**| V1 Metatavu SCIM 検証 + V2 Sync Mode override 検証 | ✅ V1/V2 判定 + Fallback 選定（必要時）|
| **Day 3（V3' 実施 + 結論確定）**| Custom Authenticator SPI プロトタイプビルド + 動作確認 + 全体判定 | ✅ V3' 判定 + Phase 1 実装計画確定 |

---

## 4. 成果物

| 種別 | 内容 | 保存先 |
|---|---|---|
| **検証結果ログ** | 各 V の実行ログ + curl 応答 + Admin API 応答 | [docs/verification-log.md](docs/verification-log.md) |
| **判定サマリ** | V1/V2/V3' の合否 + 選定 Fallback + Phase 1 実装計画への影響 | 同上（末尾）|
| **SPI JAR プロトタイプ** | Custom Authenticator SPI ビルド済み JAR | [spi/last-login-tracker/target/](spi/last-login-tracker/target/) |
| **既存ドキュメント反映** | 検証結果を jit-scim §10.4.E に追記 + B-SCIM-7/8/10 の ⏳ → 済み更新 | [jit-scim §10.4.F](../../doc/common/jit-scim-coexistence-keycloak.md) 新設予定 |

---

## 5. 一次資料エビデンス（本 PoC の前提）

[jit-scim §10.4.E.5](../../doc/common/jit-scim-coexistence-keycloak.md) の 14 件（E-1〜E-14）を全て前提とする。

特に重要:
- **E-8 Keycloak Issue #14942**：Event Listener SPI 内 setSingleAttribute 動かない（Closed as not planned）
- **E-9 Keycloak Issue #22902**：enlistAfterCompletion で ConcurrentModificationException（Open）
- **E-10 公式推奨 workaround**：`KeycloakTransactionManager.enlistAfterCompletion()`
- **E-11 Sync Mode 4 モード**：Legacy / Import / Force / Inherit
- **E-12 Per-Mapper syncMode Keycloak 10+**：extra_config で設定可能

---

## 6. 実行手順（Quick Start）

詳細は [docs/execution-guide.md](docs/execution-guide.md) 参照。概要:

```bash
# 1. 環境起動
cd poc/jit-scim-verification-2026-07-10/
docker compose up -d

# 2. Keycloak 起動確認（1-2 分待機）
curl http://localhost:8080/health/ready

# 3. V1 実行
./tests/v1-metatavu-scim.sh

# 4. V2 実行
./tests/v2-sync-mode-override.sh

# 5. V3' 実行（SPI ビルド → デプロイ → テスト）
cd spi/last-login-tracker && ./build.sh
docker compose restart keycloak
cd ../.. && ./tests/v3-custom-authenticator.sh

# 6. 結果確認
cat docs/verification-log.md
```

---

## 7. 関連ドキュメント

- **[jit-scim §10.4.E 一次資料調査](../../doc/common/jit-scim-coexistence-keycloak.md)** — 本 PoC の背景と 14 件エビデンス
- **[ADR-025 §I.2](../../doc/adr/025-scim-positioning-and-receive-stance.md)** — Metatavu keycloak-scim-server 選定
- **[ADR-060 §C.2.3](../../doc/adr/060-auth-protocol-attack-path-residual-tbd.md)** — Event Listener SPI に警告バナー付き
- **[hearing-checklist B-SCIM-7/8/9/10](../../doc/requirements/hearing-checklist.md)** — Phase 1 実装前ゲート項目
- **[ADR-055 HRD Authenticator SPI](../../doc/adr/055-hrd-implementation-method-selection.md)** — Custom Authenticator SPI 実装体制の前例
