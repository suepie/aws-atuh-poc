# JIT + SCIM 併用環境の Keycloak 実装ノート

> **位置付け**: 顧客 IdP の **SCIM 対応状況がバラバラ**（タイプ A=SCIM 採用 / タイプ B=JIT のみ / タイプ C=移行期混在）な環境を Keycloak 26 で実装するための **技術設計ノート**。proposal §FR-7.4.5/6/7 の設計判断を **Keycloak の Identity Provider Mapper / First Broker Login Flow / Sync Mode / SCIM Plugin** の具体設定に落とし込む。
> **対象読者**: Keycloak 設計・実装担当者 / SRE / Realm 設定運用者
> **関連**:
> - [§FR-7.4.5 混在環境シーケンス](../requirements/proposal/fr/07-user.md#fr-745-混在環境の認証プロビジョニング-フロー顧客-idp-別の-scim-対応差) — 設計判断（必読、まず読む）
> - [§FR-7.4.6 同期競合の解決ルール](../requirements/proposal/fr/07-user.md#fr-746-同期競合の解決ルールscim-vs-jitsource-of-truth-ポリシー)
> - [§FR-7.4.7 段階移行運用](../requirements/proposal/fr/07-user.md#fr-747-段階移行運用jit--scim-追加既存ユーザーマージ)
> - [hook-architecture-keycloak.md §3.6 SCIM 受信プラグイン](hook-architecture-keycloak.md#36-scim-受信プラグイン別軸参考整理) — プラグイン選択
> - [auth-patterns.md](auth-patterns.md) / [authz-architecture-design.md](authz-architecture-design.md) / [identity-broker-multi-idp.md](identity-broker-multi-idp.md)

---

## 目次

1. [前提と全体像](#1-前提と全体像)
2. [Keycloak の主要コンポーネント整理](#2-keycloak-の主要コンポーネント整理)
3. [タイプ A（SCIM 採用顧客）の実装](#3-タイプ-ascim-採用顧客の実装)
4. [タイプ B（JIT のみ顧客）の実装](#4-タイプ-bjit-のみ顧客の実装)
5. [タイプ C（移行期混在）の実装](#5-タイプ-c移行期混在の実装)
6. [externalId 突合実装の詳細](#6-externalid-突合実装の詳細)
7. [テナント別設定の場所（Realm/IdP/Client/User）](#7-テナント別設定の場所realmidpclientuser)
8. [Sync Mode 詳細と設定例](#8-sync-mode-詳細と設定例)
9. [First Broker Login Flow との連動](#9-first-broker-login-flow-との連動)
10. [運用手順と落とし穴](#10-運用手順と落とし穴)
11. [リファレンス](#11-リファレンス)

---

## 1. 前提と全体像

### 1.1 本ドキュメントが解決する技術的問い

| 問い | 本ドキュメントでの回答 |
|---|---|
| 顧客 IdP の SCIM 対応バラツキにどう対応するか? | **Realm 単位で SCIM Plugin を有効化、IdP 単位で Sync Mode 切替**（§7）|
| SCIM で事前作成された Alice が JIT ログイン時に重複作成されないか? | **First Broker Login Flow で externalId 突合**、既存ユーザーリンク（§6, §9）|
| 属性食い違いはどう解決するか? | **Sync Mode = FORCE（SCIM 採用）/ IMPORT（JIT のみ）の Per-IdP 設定**（§8）|
| JIT → SCIM 移行時の既存ユーザーマージは? | **kcadm.sh + SCIM API バッチで externalId 後付け**（§5, §10）|
| Keycloak ネイティブ SCIM Realm API（26.6 Experimental）を使うべきか? | **Phase Two SCIM が本番候補、Keycloak ネイティブは将来移行先**（§2）|

### 1.2 全体像（混在テナント収容）

```mermaid
flowchart LR
    subgraph TenantA["タイプ A: SCIM 採用 Realm"]
        TAIdP["IdP A1<br/>(Entra ID)<br/>SyncMode=FORCE"]
        TAHR[顧客 HR]
        TAHR -->|SCIM Push| TAEnd
        TAEnd[Phase Two SCIM<br/>Endpoint A]
        TAIdP -.→ SAML/OIDC -.→ KC_A
        TAEnd --> KC_A
    end

    subgraph TenantB["タイプ B: JIT のみ Realm"]
        TBIdP["IdP B1<br/>(ADFS)<br/>SyncMode=IMPORT"]
        TBIdP --> KC_B
    end

    subgraph TenantC["タイプ C: 移行期 Realm"]
        TCIdP1["IdP C1 (Okta) - SCIM 段階導入<br/>SyncMode=IMPORT→FORCE 切替期"]
        TCEnd[Phase Two SCIM<br/>Endpoint C]
        TCIdP1 --> KC_C
        TCEnd -.→ 段階的に開通 .-> KC_C
    end

    subgraph Core["Keycloak Cluster"]
        KC_A[Realm: tenant-a]
        KC_B[Realm: tenant-b]
        KC_C[Realm: tenant-c]
        DB[(統合 DB<br/>externalId で<br/>SCIM/JIT 起点を区別)]
        KC_A --> DB
        KC_B --> DB
        KC_C --> DB
    end

    style TenantA fill:#e8f5e9
    style TenantB fill:#fff8e1
    style TenantC fill:#fff3e0
    style Core fill:#e3f2fd
```

→ **同一 Keycloak Cluster で 3 タイプを同時収容**、テナント別 Realm + IdP 単位の Sync Mode で切り替え。

---

## 2. Keycloak の主要コンポーネント整理

| コンポーネント | 役割 | 本件での用途 |
|---|---|---|
| **Realm** | テナント単位のセキュリティ境界 | 顧客ごとに 1 Realm（マルチテナント L3）|
| **Identity Provider (IdP) 設定** | 外部 IdP（SAML/OIDC）との連携設定 | 顧客 IdP 接続情報、**Sync Mode 設定の中核**|
| **Identity Provider Mapper SPI** | 外部 IdP の属性 → Keycloak 属性マッピング | `externalId` 設定、属性引き当て |
| **First Broker Login Flow** | 外部 IdP 初回ログイン時のフロー（突合/作成/リンク）| **JIT + SCIM 突合の心臓部**（§9）|
| **User Attribute** | Keycloak User オブジェクトのカスタム属性 | `externalId`、`tenant_id`、`scim_source` 等 |
| **Phase Two SCIM Plugin** | SCIM 2.0 Server エンドポイント実装 | 顧客 IdP からの SCIM Push 受信（[§3.6](hook-architecture-keycloak.md#36-scim-受信プラグイン別軸参考整理)）|
| **Keycloak 26.6 ネイティブ SCIM Realm API** | Experimental の SCIM Server 機能 | 将来移行先、現時点は Phase Two が安定 |
| **Event Listener SPI** | 認証・管理イベントの受信 | Webhook 送出基盤（Phase Two `keycloak-events`）|
| **kcadm.sh** | CLI 管理ツール | バッチ操作、移行スクリプト |
| **Terraform Provider keycloak/keycloak** | IaC 化 | Realm/IdP/Mapper 設定の差分管理 |

### 2.1 SCIM Plugin 選択方針（再掲）

| 選択肢 | 状況 | 本件採用 |
|---|---|:-:|
| **Keycloak 26.6 ネイティブ Experimental** | Microsoft Entra ID 互換最優先、API 安定化待ち | △ 将来移行 |
| **Phase Two SCIM** | Per-org SCIM endpoints、Production 採用実績、Webhook と統合 | ⭐ **採用** |
| Captain-P-Goldfish OSS | kc-21 で EOL | ❌ 不採用 |

→ **Phase Two SCIM Plugin を Realm 単位で有効化** + Per-org endpoint で顧客別 SCIM URL を提供。

---

## 3. タイプ A（SCIM 採用顧客）の実装

### 3.1 Realm 設定

```hcl
# Terraform 例
resource "keycloak_realm" "tenant_a" {
  realm                  = "tenant-acme"
  display_name           = "Acme Corp"
  enabled                = true
  registration_allowed   = false   # セルフサインアップ禁止
  email_verified_default = false   # 検証必須化
}
```

### 3.2 顧客 IdP（Entra ID）設定

```hcl
resource "keycloak_oidc_identity_provider" "entra_id" {
  realm             = keycloak_realm.tenant_a.id
  alias             = "acme-entra"
  display_name      = "Acme Corp Entra ID"
  enabled           = true

  authorization_url = "https://login.microsoftonline.com/${var.tenant_id}/oauth2/v2.0/authorize"
  token_url         = "https://login.microsoftonline.com/${var.tenant_id}/oauth2/v2.0/token"
  client_id         = var.entra_client_id
  client_secret     = var.entra_client_secret

  default_scopes    = "openid profile email"
  trust_email       = true       # IdP の email_verified を信頼
  store_token       = false

  # ★Sync Mode = FORCE（SCIM 採用顧客は IdP が SoT）
  sync_mode         = "FORCE"

  # First Broker Login Flow を指定（既存ユーザーリンク優先）
  first_broker_login_flow_alias = "first broker login"

  # Post Broker Login Flow（任意、ログイン後処理）
  post_broker_login_flow_alias  = ""
}
```

### 3.3 Identity Provider Mapper（externalId の中核）

```hcl
# Entra ID の "oid" (objectId, 不変 ID) を externalId として保存
resource "keycloak_attribute_importer_identity_provider_mapper" "external_id" {
  realm                   = keycloak_realm.tenant_a.id
  name                    = "external-id-mapper"
  identity_provider_alias = keycloak_oidc_identity_provider.entra_id.alias

  claim_name              = "oid"            # Entra Assertion の Object ID
  user_attribute          = "externalId"     # Keycloak User Attribute

  extra_config = {
    # FORCE モード時は毎回上書き
    syncMode = "FORCE"
  }
}

# テナント識別子 (tenant_id)
resource "keycloak_attribute_importer_identity_provider_mapper" "tenant_id" {
  realm                   = keycloak_realm.tenant_a.id
  name                    = "tenant-id-mapper"
  identity_provider_alias = keycloak_oidc_identity_provider.entra_id.alias
  claim_name              = "tid"
  user_attribute          = "tenant_id"
  extra_config = {
    syncMode = "FORCE"
  }
}

# email
resource "keycloak_attribute_importer_identity_provider_mapper" "email" {
  realm                   = keycloak_realm.tenant_a.id
  name                    = "email-mapper"
  identity_provider_alias = keycloak_oidc_identity_provider.entra_id.alias
  claim_name              = "email"
  user_attribute          = "email"
  extra_config = {
    syncMode = "FORCE"
  }
}
```

### 3.4 Phase Two SCIM Plugin の Realm 有効化

```bash
# Realm 別に SCIM Endpoint URL が払い出される
# Per-org endpoint: https://auth.example.com/realms/tenant-acme/scim/v2/

# Phase Two の Admin Console > SCIM タブで:
# - Enabled: ON
# - Bearer Token: 顧客向けに発行 (Vault 保管)
# - externalId Source: User Attribute "externalId"
# - Default Sync Mode: FORCE
```

顧客 IdP（Entra ID）側で SCIM Provisioning を設定（Enterprise App として）:
- Tenant URL: `https://auth.example.com/realms/tenant-acme/scim/v2/`
- Secret Token: Phase Two で発行した Bearer Token
- Provision User attributes: email / displayName / department / externalId(objectId)

---

## 4. タイプ B（JIT のみ顧客）の実装

### 4.1 IdP 設定（Sync Mode = IMPORT）

```hcl
resource "keycloak_saml_identity_provider" "adfs" {
  realm             = keycloak_realm.tenant_b.id
  alias             = "globex-adfs"
  display_name      = "Globex ADFS"
  enabled           = true

  entity_id                  = "https://auth.example.com/realms/tenant-globex"
  single_sign_on_service_url = var.adfs_sso_url
  signing_certificate        = var.adfs_cert

  # ★Sync Mode = IMPORT（JIT 初回のみ、以降は基盤側でセルフサービス）
  sync_mode = "IMPORT"

  trust_email = false           # ADFS は email_verified を出さないので false
  first_broker_login_flow_alias = "first broker login"
}
```

### 4.2 Attribute Mapper（externalId は null のまま）

```hcl
# SAML NameID を externalId にする（IdP 不変 ID として）
resource "keycloak_saml_user_attribute_protocol_mapper" "external_id" {
  realm                      = keycloak_realm.tenant_b.id
  name                       = "external-id-mapper"
  identity_provider_alias    = keycloak_saml_identity_provider.adfs.alias
  user_attribute             = "externalId"
  attribute_name             = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/upn"

  extra_config = {
    syncMode = "IMPORT"   # JIT 初回のみ反映、後の手動編集を許可
  }
}
```

### 4.3 SCIM Endpoint は無効

タイプ B では Phase Two SCIM の Realm 設定で Enabled = OFF。SCIM Endpoint URL は払い出されない。

---

## 5. タイプ C（移行期混在）の実装

### 5.1 Phase 別の設定変更

| Phase | Sync Mode | SCIM Endpoint | 既存ユーザー扱い |
|---|---|---|---|
| **Phase 0**（JIT のみ）| IMPORT | 無効 | externalId=null |
| **Phase 1**（SCIM 事前テスト）| IMPORT（変更なし）| **有効化 + ダミーユーザーで検証**| 影響なし |
| **Phase 2**（既存ユーザーマージ）| IMPORT（変更なし）| **本番 SCIM Push 開始** | **externalId 後付け（バッチ）**|
| **Phase 3**（FORCE 切替）| **FORCE に変更**| 継続 | 完全 SCIM 主導に切替 |

### 5.2 マージスクリプト例（Phase 2、kcadm.sh + jq）

```bash
#!/bin/bash
# scim-merge.sh: 既存 JIT ユーザーに externalId を後付け
# 入力: 顧客 IdP からの SCIM ダンプ (CSV: email, externalId)
# 動作: email 突合 (verified=true のみ) → externalId 上書き

REALM="tenant-okta"
CSV_FILE="users.csv"

# kcadm.sh ログイン
/opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 --realm master \
  --user admin --password "$ADMIN_PASS"

while IFS=, read -r email external_id; do
  # 既存ユーザー検索
  USER=$(kcadm.sh get users -r $REALM -q email=$email -q exact=true | jq -r '.[0]')
  USER_ID=$(echo "$USER" | jq -r '.id')
  EMAIL_VERIFIED=$(echo "$USER" | jq -r '.emailVerified')

  if [ -z "$USER_ID" ] || [ "$USER_ID" = "null" ]; then
    echo "SKIP: $email (not found, will be SCIM-created)"
    continue
  fi

  if [ "$EMAIL_VERIFIED" != "true" ]; then
    echo "CONFLICT: $email (email_verified=false, manual review needed)"
    echo "$email,$external_id,CONFLICT" >> conflicts.csv
    continue
  fi

  # externalId 後付け
  kcadm.sh update users/$USER_ID -r $REALM \
    -s "attributes.externalId=[\"$external_id\"]"
  echo "MERGED: $email -> externalId=$external_id"
done < "$CSV_FILE"

echo "Done. Conflicts: $(wc -l < conflicts.csv) (review conflicts.csv)"
```

### 5.3 Phase 3 切替時のロールバック準備

```bash
# 切替前に Sync Mode を IMPORT のままで externalId を全 User に保存済 = 元に戻せる
# 万が一 FORCE 切替で問題発生したら IMPORT に戻すだけ

kcadm.sh update identity-provider/instances/okta -r $REALM \
  -s "config.syncMode=IMPORT"

# externalId を全削除して JIT のみ状態へ完全戻し
# (通常は不要、緊急時のみ)
for USER_ID in $(kcadm.sh get users -r $REALM --fields id -F | jq -r '.[].id'); do
  kcadm.sh update users/$USER_ID -r $REALM \
    -s 'attributes={"externalId":[]}'
done
```

---

## 6. externalId 突合実装の詳細

### 6.1 突合キーの優先順位（First Broker Login Flow 内）

```
SAML/OIDC Assertion 受信
  ↓
[Custom Authenticator: Find User By External ID]   ← Step 1（最優先）
  ↓ externalId 突合
  ├─ Found → 既存ユーザー使用、JIT 新規作成スキップ
  └─ Not Found
       ↓
[Standard Authenticator: Review Profile]            ← Step 2
  ↓
[Standard Authenticator: Create User If Unique]     ← Step 3（email 突合）
  ↓
  ├─ Found by email (email_verified=true) → リンク確認 UI
  ├─ Found by email (email_verified=false) → ❌ エラー、管理者通知
  └─ Not Found → 新規 JIT 作成
```

### 6.2 Custom Authenticator SPI（externalId 突合）の実装スケルトン

```java
public class FindUserByExternalIdAuthenticator implements Authenticator {

    @Override
    public void authenticate(AuthenticationFlowContext context) {
        SerializedBrokeredIdentityContext brokerContext = (SerializedBrokeredIdentityContext)
            context.getAuthenticationSession().getAuthNote(BROKERED_CONTEXT_NOTE);

        BrokeredIdentityContext bic = brokerContext.deserialize(context.getSession(), context.getAuthenticationSession());

        // IdP Assertion から externalId 候補を取り出す
        String externalId = bic.getUserAttribute("externalId");
        if (externalId == null) {
            context.attempted();    // 次の Authenticator へ
            return;
        }

        // Keycloak User DB を externalId 属性で検索
        RealmModel realm = context.getRealm();
        List<UserModel> users = context.getSession().users()
            .searchForUserByUserAttributeStream(realm, "externalId", externalId)
            .collect(Collectors.toList());

        if (users.isEmpty()) {
            context.attempted();    // 既存ユーザーなし、次の Authenticator へ
            return;
        }

        if (users.size() > 1) {
            // データ不整合、エラー
            context.failure(AuthenticationFlowError.INVALID_USER);
            return;
        }

        // 既存ユーザー発見、リンク成功
        UserModel existingUser = users.get(0);
        context.setUser(existingUser);
        context.success();
    }

    // ... 残りのインターフェース実装
}
```

`META-INF/services/org.keycloak.authentication.AuthenticatorFactory` に Factory 登録 + Phase Two SCIM 対応版でも同等の Authenticator 実装あり。

### 6.3 突合キーの代替（既存実装で対応可能なケース）

Custom Authenticator を書かない簡易解:

| 突合キー | Keycloak 標準対応 | 採用シーン |
|---|:-:|---|
| **username == externalId** | ✅ 標準 username 検索で代用可 | 簡易（ただし username 衝突リスク）|
| **email == 一意性** | ✅ Realm 設定で email-unique=true | 標準パターン、ただし email_verified 必須 |
| **NameID == 不変 ID** | ⚠ Standard Token Mapper では限定的 | SAML 限定、Custom Authenticator 推奨 |

→ **本格運用は Custom Authenticator (Phase Two 既存 or 自作)** が安全。

---

## 7. テナント別設定の場所（Realm/IdP/Client/User）

| 設定対象 | 設定場所 | 適用範囲 |
|---|---|---|
| **SCIM Plugin 有効化** | Realm Settings（Phase Two SCIM タブ）| Realm 全体 |
| **SCIM Bearer Token** | Realm Attribute / Client Credentials | Realm 全体 |
| **Sync Mode** | Identity Provider 設定（`config.syncMode`）| IdP 単位（同一 Realm 内に複数 IdP 可）|
| **Attribute Mapping** | Identity Provider Mapper | IdP 単位 |
| **First Broker Login Flow** | Identity Provider 設定（`firstBrokerLoginFlowAlias`）| IdP 単位 |
| **email_verified 信頼** | Identity Provider 設定（`trustEmail`）| IdP 単位 |
| **email 一意制約** | Realm Settings（`duplicateEmailsAllowed=false`）| Realm 全体 |
| **externalId 属性** | User Attribute | User 単位 |
| **scim_source 属性**（任意）| User Attribute | User 単位（SCIM 起点 / JIT 起点を識別）|

### 7.1 同一 Realm 内に複数 IdP がある場合

タイプ A 顧客が「Entra ID + 緊急時 ADFS」のように **複数 IdP を持つ** ケース:

```
Realm: tenant-acme
├─ Identity Provider: acme-entra (SCIM 採用、Sync Mode=FORCE)
└─ Identity Provider: acme-adfs (JIT のみ、Sync Mode=IMPORT、Break Glass 用)
```

→ **IdP 単位で Sync Mode 設定可能**、同一 Realm 内で混在運用が標準。

### 7.2 マルチテナント L3（Realm 分離）vs L2（Realm 共有）

| 分離レベル | Realm 構成 | SCIM Endpoint | JIT 設定 |
|---|---|---|---|
| **L3 物理分離** | 顧客ごとに 1 Realm | Realm 別 URL | Realm 別 IdP |
| **L2 論理分離** | 全顧客で 1 Realm | Realm 共通 URL（顧客別 Bearer Token で分離）| 1 Realm に多数 IdP |

本基盤は **L3 推奨**（[§FR-2.4](../requirements/proposal/fr/02-federation.md) 連動）、Realm = テナント単位。

---

## 8. Sync Mode 詳細と設定例

### 8.1 Sync Mode 一覧

| Mode | 動作 | First Login | Subsequent Logins | SCIM Push |
|---|---|---|---|---|
| **IMPORT** | 初回ログイン時のみ属性反映、以降は変更しない | 反映 | スキップ | スキップ |
| **LEGACY**（非推奨）| 都度上書き、基盤側編集禁止 | 反映 | 反映（上書き）| 反映 |
| **FORCE** | 毎回 IdP 値で強制上書き | 反映 | 反映（強制）| 反映 |

### 8.2 Per-Mapper Sync Mode（属性別の細粒度設定）

Identity Provider Mapper ごとに `syncMode` を上書き可能:

| 属性 | 推奨 syncMode | 理由 |
|---|---|---|
| `externalId` | **FORCE** | IdP の不変 ID、変更検知必要 |
| `email` | **FORCE** | IdP がマスター |
| `firstName`, `lastName` | FORCE | IdP がマスター |
| `tenant_id` | **FORCE**（カスタム）| テナント識別、変更を即時反映 |
| `display_name` | IMPORT | 基盤側でセルフサービス上書き可能にしたい場合 |
| `phone_number` | IMPORT | ユーザー自身で更新を許可する場合 |

```hcl
resource "keycloak_attribute_importer_identity_provider_mapper" "display_name" {
  # ...
  extra_config = {
    syncMode = "IMPORT"   # この属性のみ IMPORT（基盤側編集を許可）
  }
}
```

### 8.3 IdP 全体 Sync Mode との優先順位

```
Per-Mapper syncMode が設定されている → Per-Mapper を優先
Per-Mapper が未設定 → IdP 全体の syncMode を使用
```

→ **デフォルトは IdP 全体で FORCE、特定属性のみ IMPORT に緩める** パターンが運用しやすい。

---

## 9. First Broker Login Flow との連動

### 9.1 標準 First Broker Login Flow（Keycloak デフォルト）

```
Identity Provider Redirector
  ↓
Cookie                                            ← SSO セッション確認
  ↓
Identity Provider Authentication                  ← IdP リダイレクト
  ↓
First Broker Login Flow                           ← ★ここに介入★
  ├─ Review Profile                               ← 属性確認 UI
  ├─ Create User If Unique                        ← 既存ユーザー検索（email）
  │   ├─ Found → Confirm Link Existing Account   ← リンク確認 UI
  │   │           ↓ ユーザー同意
  │   │           Verify Existing Account         ← 既存 IdP で再認証
  │   └─ Not Found → 新規 JIT 作成
  ↓
完了
```

### 9.2 本基盤の拡張 First Broker Login Flow（externalId 突合追加）

```
Identity Provider Redirector
  ↓
Identity Provider Authentication
  ↓
[Custom: Find User By External ID]   ← ★新規追加★
  ├─ Found → 既存ユーザー使用、以降スキップ
  └─ Not Found → 次へ
  ↓
Review Profile
  ↓
Create User If Unique (by email)
  ├─ Found (email_verified=true) → Confirm Link Existing Account
  ├─ Found (email_verified=false) → ❌ エラー、管理者通知
  └─ Not Found → 新規 JIT 作成
```

### 9.3 Realm Settings での Flow 設定

```hcl
# Custom Flow 定義（簡略例）
resource "keycloak_authentication_flow" "fbl_with_external_id" {
  realm_id = keycloak_realm.tenant_a.id
  alias    = "first broker login with externalId"
  description = "Find by externalId first, fallback to standard FBL"
}

# IdP に紐付け
resource "keycloak_oidc_identity_provider" "entra_id" {
  # ...
  first_broker_login_flow_alias = keycloak_authentication_flow.fbl_with_external_id.alias
}
```

詳細実装は [Phase Two の First Broker Login 拡張サンプル](https://github.com/p2-inc/keycloak-events) や [Keycloak Authentication SPI ドキュメント](https://www.keycloak.org/docs/latest/server_development/index.html#_auth_spi) を参照。

---

## 10. 運用手順と落とし穴

### 10.1 落とし穴 7 つ

| # | 落とし穴 | 対策 |
|:-:|---|---|
| 1 | `trustEmail=false` で email_verified=false のまま JIT、後から SCIM Push で `email 一致 + verified=false` 検出エラー | 移行前にメール検証キャンペーン実施 |
| 2 | Sync Mode = LEGACY で運用すると、IdP 側 email 変更時に基盤側 email がブロックして失敗 | LEGACY は非推奨、FORCE か IMPORT |
| 3 | `externalId` を user_attribute ではなく username に保存 → username 衝突（特に複数 IdP 持つ Realm）| **必ず User Attribute `externalId` を使用** |
| 4 | Custom Authenticator のテストが困難 | Testcontainers で Keycloak コンテナ起動 + 統合テスト |
| 5 | SCIM Push のリトライ無効化（Phase Two デフォルトは有効、自作なら要実装）| Phase Two 標準利用、自作避ける |
| 6 | Realm 削除 = 全 User 消失（Bearer Token 含む）| Realm 削除前に backup、SCIM Bearer Token は Vault 管理 |
| 7 | Multi-instance Keycloak で Identity Provider Mapper が同期されない（古い Infinispan 設定）| Stage A の jdbc-ping クラスタ設定で対応済（[phase10-stage-a-verification.md](phase10-stage-a-verification.md) 参照）|

### 10.2 検証チェックリスト（混在環境 E2E テスト）

```
[タイプ A 検証]
□ Entra Enterprise App で SCIM Provisioning 設定
□ ダミーユーザー Push → Keycloak User 作成確認 (externalId 含む)
□ ダミーユーザーで SAML ログイン → 既存ユーザー使用、JIT 新規作成スキップ確認
□ Entra 側で属性変更 → SCIM PATCH → Keycloak 反映確認
□ Entra 側で削除 → SCIM DELETE → Keycloak 無効化 + Token Revocation 確認
□ Back-Channel Logout で全 RP に通知される確認

[タイプ B 検証]
□ ADFS から SAML ログイン → JIT 新規ユーザー作成 (externalId=null)
□ 属性更新は基盤側セルフサービスで可能（Sync Mode=IMPORT）
□ ADFS 側削除 → Keycloak セッション継続（既存 Token TTL 中）
□ 次回ログインで認証失敗 → Keycloak 側ユーザー無効化は手動 or 定期バッチ

[タイプ C 検証]
□ Phase 0 (JIT のみ) で 100 ユーザー作成 (externalId=null)
□ Phase 1 (SCIM 有効化) でダミーユーザー Push 検証
□ Phase 2 (マージスクリプト実行) で既存 100 ユーザーに externalId 後付け
  □ 成功: 90 件 (externalId 追加)
  □ Conflict: 10 件 (email_verified=false) → 個別解決
□ Phase 3 (Sync Mode=FORCE) で本番切替、退職反映即時化確認
```

### 10.3 監視・運用メトリクス

| メトリクス | 目的 | 計測場所 |
|---|---|---|
| SCIM Endpoint レスポンス時間 | 顧客 IdP の SCIM Push 性能 | Phase Two メトリクス / CloudWatch |
| SCIM 受信エラー率 | 顧客側設定問題検知 | Phase Two ログ |
| JIT 新規作成数 / 日 | タイプ B 顧客の活動量 | Keycloak Event Listener |
| externalId 後付け成功率 | 移行マージの品質 | マージスクリプトサマリ |
| Sync Mode 別ユーザー分布 | テナント別の構成把握 | kcadm.sh + 集計 |

---

## 11. リファレンス

### 11.1 Keycloak 公式

- [Identity Brokering Overview](https://www.keycloak.org/docs/latest/server_admin/#_identity_broker)
- [First Login Flow](https://www.keycloak.org/docs/latest/server_admin/#_identity_broker_first_login)
- [Identity Provider Mappers](https://www.keycloak.org/docs/latest/server_admin/#_mappers)
- [Sync Mode](https://www.keycloak.org/docs/latest/server_admin/#general-identity-provider-configuration)
- [Authentication SPI](https://www.keycloak.org/docs/latest/server_development/index.html#_auth_spi)
- [Keycloak 26.6 SCIM Realm API Experimental](https://www.keycloak.org/2026/04/scim-as-experimental-feature)

### 11.2 Phase Two

- [Phase Two `keycloak-events`](https://github.com/p2-inc/keycloak-events) — Webhook（OUTBOUND）
- [Phase Two SCIM](https://phasetwo.io/) — Per-org SCIM endpoints
- [Phase Two Webhooks docs](https://phasetwo.io/docs/audit-logs/webhooks/)

### 11.3 SCIM 仕様

- [RFC 7644 SCIM 2.0 Protocol](https://datatracker.ietf.org/doc/html/rfc7644)
- [RFC 7643 SCIM 2.0 Core Schema](https://datatracker.ietf.org/doc/html/rfc7643)
- [Microsoft Entra SCIM Provisioning](https://learn.microsoft.com/en-us/entra/identity/app-provisioning/use-scim-to-provision-users-and-groups)
- [Okta SCIM Connector Guide](https://developer.okta.com/docs/concepts/scim/)

### 11.4 内部関連ドキュメント

- [§FR-7.4 プロビジョニング（proposal）](../requirements/proposal/fr/07-user.md)
- [§FR-2.2.1 JIT プロビジョニング（proposal）](../requirements/proposal/fr/02-federation.md)
- [§FR-2.2.1.A 同一テナント内ユーザー重複（proposal）](../requirements/proposal/fr/02-federation.md)
- [hook-architecture-keycloak.md](hook-architecture-keycloak.md) — INBOUND/OUTBOUND Hook + SCIM Plugin
- [auth-patterns.md](auth-patterns.md) — 認証パターン総覧
- [authz-architecture-design.md](authz-architecture-design.md) — 認可アーキテクチャ
- [identity-broker-multi-idp.md](identity-broker-multi-idp.md) — Identity Broker パターン
- [subdomain-architecture-notes.md](subdomain-architecture-notes.md) — サブドメイン構成
- [token-exchange-spec-and-patterns.md](token-exchange-spec-and-patterns.md) — Token Exchange

---

## 改訂履歴

- 2026-06-08: 初版作成。proposal §FR-7.4.5/6/7 の設計判断を Keycloak 26 + Phase Two SCIM 実装目線で詳細化。混在 3 タイプ（A=SCIM 採用 / B=JIT のみ / C=移行期）の Realm/IdP/Mapper 設定 + externalId 突合 Custom Authenticator + Sync Mode 詳細 + First Broker Login Flow 拡張 + マージスクリプト + 落とし穴 7 つを集約
