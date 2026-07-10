# PoC 計画書：JIT ユーザ削除 + SCIM 実装可能性検証（V1/V2/V3'）

> **作成日**: 2026-07-10
> **対象**: Phase 1 実装開始前ゲート 3 点の検証
> **背景**: [jit-scim §10.4.E 一次資料調査 14 件](../../doc/common/jit-scim-coexistence-keycloak.md) で判明した重大課題
> **ゲート項目**: [hearing-checklist B-SCIM-7/8/10](../../doc/requirements/hearing-checklist.md)

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
