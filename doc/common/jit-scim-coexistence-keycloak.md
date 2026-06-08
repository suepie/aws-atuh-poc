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
| **未ログイン 90 日超ユーザー数** | PCI DSS 8.2.6 / 定期バッチ deprovisioning 対象 | kcadm.sh + 集計 |
| **論理削除（enabled=false）ユーザー数の推移** | DB 肥大化監視 | kcadm.sh + 集計 |

### 10.4 JIT 定期バッチ deprovisioning 実装（PCI DSS 8.2.6 / APPI 法 22 条対応）

> **背景**: JIT のみ顧客では「顧客 IdP 側で削除されても Keycloak は関知しない」（[proposal §FR-7.4.5 シーケンス 5](../requirements/proposal/fr/07-user.md)）→ ゴーストユーザー蓄積。**90 日未ログイン User の自動無効化** が必須（PCI DSS 8.2.6）。

#### バッチスクリプト実装例（kcadm.sh + jq）

```bash
#!/bin/bash
# inactive-user-disable.sh
# 90 日以上未ログインのユーザーを enabled=false に変更
# PCI DSS 8.2.6 適合、APPI 法 22 条 遅滞ない消去対応
# 実行頻度: 週次 (cron で毎週日曜 02:00)

set -euo pipefail

REALM="${1:-tenant-acme}"
INACTIVE_DAYS="${INACTIVE_DAYS:-90}"
DRY_RUN="${DRY_RUN:-false}"   # true = 実行せず一覧のみ
KC_URL="https://auth.example.com"
ADMIN_USER="admin"
ADMIN_PASS="$(vault kv get -field=password secret/keycloak/admin)"

# 閾値タイムスタンプ計算 (90 日前のミリ秒)
THRESHOLD_MS=$(($(date +%s%3N) - INACTIVE_DAYS * 86400 * 1000))

# kcadm.sh 認証
/opt/keycloak/bin/kcadm.sh config credentials \
  --server "$KC_URL" --realm master \
  --user "$ADMIN_USER" --password "$ADMIN_PASS"

# 全 User を取得（max=10000、必要に応じてページング）
USERS=$(kcadm.sh get users -r "$REALM" --max 10000 --fields id,username,enabled,createdTimestamp)

# 各 User の lastLogin を Event API から取得して判定
TARGETS=()
for USER_ID in $(echo "$USERS" | jq -r '.[] | select(.enabled==true) | .id'); do
  # 最終ログイン取得 (Event API、type=LOGIN)
  LAST_LOGIN=$(kcadm.sh get "events?client=auth-poc-spa&type=LOGIN&user=$USER_ID&max=1" -r "$REALM" | jq -r '.[0].time // 0')

  if [ "$LAST_LOGIN" -lt "$THRESHOLD_MS" ]; then
    USERNAME=$(echo "$USERS" | jq -r ".[] | select(.id==\"$USER_ID\") | .username")
    TARGETS+=("$USER_ID:$USERNAME:$LAST_LOGIN")
  fi
done

echo "Found ${#TARGETS[@]} inactive users (>${INACTIVE_DAYS} days)"

# 除外: サービスアカウント / 管理者ロール持ち
# 通常は事前にロールベースフィルタを別途実装

# 通知 (7 日前事前通知パターンは別バッチで実装、ここでは即時無効化)
for ENTRY in "${TARGETS[@]}"; do
  USER_ID=$(echo "$ENTRY" | cut -d: -f1)
  USERNAME=$(echo "$ENTRY" | cut -d: -f2)

  if [ "$DRY_RUN" = "true" ]; then
    echo "DRY_RUN: would disable $USERNAME ($USER_ID)"
  else
    # 論理削除（enabled=false）
    kcadm.sh update users/"$USER_ID" -r "$REALM" -s "enabled=false"

    # 全 Session Revoke (Token も含む)
    kcadm.sh post users/"$USER_ID"/logout -r "$REALM"

    # 監査ログ送出 (Custom Attribute で記録、Event Listener が拾う)
    kcadm.sh update users/"$USER_ID" -r "$REALM" \
      -s "attributes.deprovisioned_at=[\"$(date -Iseconds)\"]" \
      -s "attributes.deprovisioned_reason=[\"inactive_${INACTIVE_DAYS}d\"]"

    echo "DISABLED: $USERNAME ($USER_ID)"
  fi
done

# サマリレポート出力
echo "Deprovisioning summary: $(date -Iseconds)"
echo "  Realm: $REALM"
echo "  Inactive threshold: ${INACTIVE_DAYS} days"
echo "  Targets: ${#TARGETS[@]}"
echo "  Mode: $DRY_RUN"
```

#### CronJob (Kubernetes) 例

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: inactive-user-disable
  namespace: keycloak
spec:
  schedule: "0 2 * * 0"   # 毎週日曜 02:00
  successfulJobsHistoryLimit: 10
  failedJobsHistoryLimit: 5
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: keycloak-deprovision-sa
          restartPolicy: OnFailure
          containers:
          - name: deprovision
            image: ghcr.io/example/kc-deprovision:latest
            env:
            - name: REALM
              value: "tenant-acme"
            - name: INACTIVE_DAYS
              value: "90"
            - name: DRY_RUN
              value: "false"
            envFrom:
            - secretRef:
                name: keycloak-admin-credentials
            resources:
              limits:
                memory: 512Mi
                cpu: 500m
```

#### 通知 + ロールバック設計

```
T-7 日: 「7 日後に無効化」メール送信（誤無効化防止）
        attributes.deprovision_warning_at セット
T-0:    enabled=false に変更 + Token Revocation + 監査ログ
        attributes.deprovisioned_at セット
T+30 日: ロールバック可能期間（管理者が enabled=true 戻し可、Realm 設定）
T+30 日 〜 T+N 年: 法的保持期間中は論理削除のまま保持
T+N 年 (PCI DSS=1年 / 一般=7年): 物理削除 or 匿名化バッチ実行
```

### 10.5 Keycloak DB 保持・削除マトリクス（実装詳細）

| ケース | 影響テーブル | SQL/API 操作 |
|---|---|---|
| **JIT 顧客 IdP 削除** | なし（基盤に通知なし） | - |
| **JIT 定期バッチ無効化**（10.4 のスクリプト）| `user_entity.enabled` = false / `user_attribute` に deprovisioned_at | `UPDATE user_entity SET enabled=false WHERE id=?` |
| **SCIM DELETE 受信**（デフォルト）| `user_entity.enabled` = false / `user_attribute.scim_deleted` = true | Phase Two SCIM Plugin が自動処理 |
| **SCIM DELETE + Hard Delete 設定** | `user_entity` 物理削除 + 関連テーブル CASCADE | `DELETE FROM user_entity WHERE id=?`（FK CASCADE）|
| **管理者手動 Hard Delete** | 同上 | `DELETE /admin/realms/{realm}/users/{id}` |
| **GDPR Erasure** | 同上 + 監査ログ匿名化 | カスタムスクリプト（個別実装）|
| **法的保持期間後の自動削除** | 同上 + アーカイブ送信 | バッチ + S3 Glacier Deep Archive |

### 10.6 PCI DSS v4.0 / APPI 適合性チェックリスト

> 詳細な要件マッピングは [proposal §FR-7.4.8](../requirements/proposal/fr/07-user.md) 参照。本セクションは **Keycloak 実装側のチェック項目**。

#### PCI DSS v4.0 適合（CDE 範囲の認証経路がある顧客向け）

| Requirement | Keycloak 実装での対応 |
|---|---|
| **8.2.1** ユーザー識別子の一意性 | `user_entity.username` UNIQUE 制約（Realm 内）|
| **8.2.5** 退職時即時取消 | SCIM DELETE + Token Revocation（K8）+ Back-Channel Logout（K7）|
| **8.2.6** 90 日未使用無効化 | **§10.4 のバッチスクリプト** 必須 |
| **8.3.1** MFA 全アクセス | Realm Settings + Conditional Authentication Flow（[§3.2 / §4.6](../requirements/powerpoint-outline-and-references.md) と整合）|
| **8.5** アクセスレビュー（四半期）| SCIM 採用顧客 = SCIM API でユーザー一覧取得 + 自動レビュー / JIT のみ顧客 = §10.4 バッチで未使用検出 |
| **10.2** 監査ログ | Event Listener SPI + Phase Two `keycloak-events` で全イベント送出 |

#### APPI 適合（個人データを扱う全顧客向け）

| 法/GL | Keycloak 実装での対応 |
|---|---|
| **法 23 条**（安全管理措置）| MFA + SCIM 即時遮断 or §10.4 バッチ + 監査ログ |
| **法 22 条**（不要保持禁止 / 遅滞ない消去）| §10.4 バッチ + 法的保持期間後の物理削除（§10.5）|
| **法 25 条**（漏えい等報告）| Event Listener SPI で SIEM 連携 + インシデント対応手順 |
| **法 26 条**（委託先監督）| 監査ログ全保持 + SLA レポート + 認証取得（SOC2 / ISO27001）|
| **法 28-30 条**（開示・訂正・利用停止）| SCIM 採用 = 自動応答 API / JIT のみ = Admin API + 30 日以内手動応答 |

### 10.7 SCIM 非対応 IdP 顧客向け Compensating Controls 実装詳細

> **背景**: [proposal §FR-7.4.9](../requirements/proposal/fr/07-user.md) の案 A（短命 Token）+ 案 B（BCL）+ 案 C（認証ログ逆引きバッチ）の **Keycloak 実装目線** 詳細。SCIM 非対応 IdP 顧客でも PCI DSS / APPI 適合可能性を確保する。

#### 10.7.1 案 A: 短命 Access Token + Refresh Token Rotation の Keycloak 設定

**Realm Settings → Tokens タブ**:

```hcl
# Terraform 例
resource "keycloak_realm" "tenant_scim_none" {
  realm        = "tenant-acme"
  enabled      = true

  # 短命 Access Token
  access_token_lifespan                  = "15m"   # ★ 15 分
  access_token_lifespan_for_implicit_flow = "15m"

  # Refresh Token + Rotation
  sso_session_idle_timeout    = "24h"    # アイドル 24 時間
  sso_session_max_lifespan    = "30d"    # 絶対 30 日

  # Offline Token (任意、長期 Refresh)
  offline_session_idle_timeout = "30d"
  offline_session_max_lifespan_enabled = true
  offline_session_max_lifespan = "60d"

  # Refresh Token Rotation を有効化
  refresh_token_max_reuse = 0   # 0 = 1 回のみ使用可、Rotation 必須
  revoke_refresh_token    = true
}
```

#### 10.7.2 短命 Token 環境での Silent Refresh 実装パターン

##### SPA（oidc-client-ts）の Silent Refresh

```typescript
// authProvider.ts
import { UserManager, WebStorageStateStore } from "oidc-client-ts";

const userManager = new UserManager({
  authority: "https://auth.example.com/realms/tenant-acme",
  client_id: "auth-poc-spa",
  redirect_uri: window.location.origin + "/callback",
  silent_redirect_uri: window.location.origin + "/silent-callback",  // ★ Silent Refresh 専用
  scope: "openid profile email",
  response_type: "code",
  loadUserInfo: true,
  userStore: new WebStorageStateStore({ store: window.localStorage }),
  automaticSilentRenew: true,                  // ★ 自動 Silent Refresh
  silentRequestTimeoutInSeconds: 10,
  accessTokenExpiringNotificationTimeInSeconds: 60,   // ★ 期限 60 秒前に Refresh
});

// Silent Refresh 失敗時のハンドリング
userManager.events.addSilentRenewError((error) => {
  console.warn("Silent renew failed:", error);
  // ネットワーク断 → 自動リトライ（ライブラリが対応）
  // Refresh Token 失効 → 再ログインへ
  if (error.error === "invalid_grant") {
    userManager.signinRedirect();
  }
});

// Token 取得時のラッパ（期限切れチェック）
export async function getAccessToken(): Promise<string> {
  const user = await userManager.getUser();
  if (!user || user.expired) {
    await userManager.signinSilent();
    const refreshed = await userManager.getUser();
    return refreshed!.access_token;
  }
  return user.access_token;
}
```

##### Multi-Tab UX（BroadcastChannel API）

```typescript
// tab-sync.ts
const channel = new BroadcastChannel("auth_sync");

userManager.events.addUserLoaded((user) => {
  // 他タブへ Token 更新を通知
  channel.postMessage({ type: "TOKEN_REFRESHED", expires_at: user.expires_at });
});

channel.onmessage = (event) => {
  if (event.data.type === "TOKEN_REFRESHED") {
    // 他タブが Refresh した、自タブも User を再読込
    userManager.getUser();
  }
};
```

##### SSR (Next.js) の Silent Refresh

```typescript
// middleware.ts
import { jwtDecode } from "jwt-decode";

export async function middleware(request: NextRequest) {
  const accessToken = request.cookies.get("access_token")?.value;
  if (!accessToken) return NextResponse.redirect("/login");

  const payload = jwtDecode<{ exp: number }>(accessToken);
  const expiresIn = payload.exp * 1000 - Date.now();

  // 残り 60 秒で Refresh
  if (expiresIn < 60_000) {
    const refreshToken = request.cookies.get("refresh_token")?.value;
    const newTokens = await refreshAccessToken(refreshToken!);
    const response = NextResponse.next();
    response.cookies.set("access_token", newTokens.access_token, {
      httpOnly: true, secure: true, sameSite: "lax",
      maxAge: 15 * 60,
    });
    response.cookies.set("refresh_token", newTokens.refresh_token, {
      httpOnly: true, secure: true, sameSite: "lax",
      maxAge: 24 * 60 * 60,
    });
    return response;
  }
  return NextResponse.next();
}
```

#### 10.7.3 長時間タスクの設計（Token 期限切れ対策）

短命 Token 環境では **5-15 分以上かかるタスク** が Token 期限切れで失敗するリスクあり。

| タスク | 設計パターン |
|---|---|
| **ファイルアップロード**（数百 MB-GB）| **Multipart Upload + 各パート再認証**（S3 Presigned URL 等で Token 非依存化）|
| **レポート生成**（数分）| **Background Job 化**（API は Job ID 返却、ポーリング or WebSocket で結果取得）|
| **長時間 WebSocket 接続** | **Re-auth Frame で Token 更新**（クライアントから期限前に再接続）|
| **バッチ処理**（CSV 数千件）| **Chunk 分割 + 各 Chunk で Token Refresh** |

#### 10.7.4 案 B: 顧客 IdP からの Back-Channel Logout 受信実装

Keycloak の OIDC Identity Provider 設定で BCL 受信を有効化:

```hcl
resource "keycloak_oidc_identity_provider" "customer_idp" {
  realm        = keycloak_realm.tenant_a.id
  alias        = "customer-adfs-2019"
  display_name = "Customer ADFS 2019"

  authorization_url = var.customer_authorize_url
  token_url         = var.customer_token_url
  logout_url        = var.customer_logout_url
  client_id         = var.customer_client_id
  client_secret     = var.customer_client_secret

  # ★ Back-Channel Logout 受信を有効化
  backchannel_supported = true

  sync_mode         = "FORCE"
  trust_email       = true

  first_broker_login_flow_alias = "first broker login"
}
```

Realm の Client 側でも BCL 送出を有効化:

```hcl
resource "keycloak_openid_client" "spa" {
  # ...
  backchannel_logout_url             = "https://app.example.com/api/backchannel-logout"
  backchannel_logout_session_required = true
  backchannel_logout_revoke_offline_sessions = true
}
```

#### 10.7.5 案 C: 顧客 IdP 認証ログ逆引きバッチ実装

##### Microsoft Entra ID（Graph API）の例

```bash
#!/bin/bash
# entra-signin-log-reverse-lookup.sh
# Microsoft Graph API でサインインログ取得 → 7 日未認証ユーザーを Keycloak で無効化

set -euo pipefail

REALM="${1:-tenant-acme}"
INACTIVE_DAYS="${INACTIVE_DAYS:-7}"
ENTRA_TENANT_ID="${ENTRA_TENANT_ID}"
ENTRA_CLIENT_ID="${ENTRA_CLIENT_ID}"
ENTRA_CLIENT_SECRET="${ENTRA_CLIENT_SECRET}"

# Microsoft Graph アクセストークン取得
ENTRA_TOKEN=$(curl -sf -X POST \
  "https://login.microsoftonline.com/$ENTRA_TENANT_ID/oauth2/v2.0/token" \
  -d "grant_type=client_credentials" \
  -d "client_id=$ENTRA_CLIENT_ID" \
  -d "client_secret=$ENTRA_CLIENT_SECRET" \
  -d "scope=https://graph.microsoft.com/.default" \
  | jq -r '.access_token')

# 全ユーザー取得（Entra ID）
ENTRA_USERS=$(curl -sf -H "Authorization: Bearer $ENTRA_TOKEN" \
  "https://graph.microsoft.com/v1.0/users?\$select=id,userPrincipalName,signInActivity")

# 最終サインイン日時を取得 + N 日未認証ユーザーを抽出
THRESHOLD_DATE=$(date -u -d "$INACTIVE_DAYS days ago" -Iseconds 2>/dev/null || \
                 date -u -v-${INACTIVE_DAYS}d -Iseconds)

INACTIVE_USERS=$(echo "$ENTRA_USERS" | jq -r --arg threshold "$THRESHOLD_DATE" '
  .value[] | select(
    .signInActivity == null or
    .signInActivity.lastSignInDateTime < $threshold
  ) | .userPrincipalName')

# Keycloak で対応ユーザーを無効化
/opt/keycloak/bin/kcadm.sh config credentials --server "$KC_URL" \
  --realm master --user admin --password "$ADMIN_PASS"

for UPN in $INACTIVE_USERS; do
  # Keycloak の externalId or email で検索
  KC_USER=$(kcadm.sh get users -r "$REALM" -q email="$UPN" | jq -r '.[0]')
  KC_USER_ID=$(echo "$KC_USER" | jq -r '.id // empty')

  if [ -n "$KC_USER_ID" ]; then
    kcadm.sh update users/"$KC_USER_ID" -r "$REALM" -s "enabled=false"
    kcadm.sh post users/"$KC_USER_ID"/logout -r "$REALM"
    echo "DISABLED: $UPN ($KC_USER_ID)"
  fi
done
```

##### Okta（System Log API）の例

```bash
# Okta System Log API で 7 日内に成功ログインしていないユーザーを抽出
OKTA_LOGS=$(curl -sf -H "Authorization: SSWS $OKTA_API_TOKEN" \
  "https://$OKTA_DOMAIN/api/v1/logs?\
filter=eventType eq \"user.session.start\" and outcome.result eq \"SUCCESS\"&\
since=$(date -u -d "$INACTIVE_DAYS days ago" -Iseconds)")

# 直近ログインしたユーザーセット
ACTIVE_USERS=$(echo "$OKTA_LOGS" | jq -r '[.[].actor.alternateId] | unique | .[]')

# Okta 全ユーザーから未認証ユーザーを抽出
ALL_USERS=$(curl -sf -H "Authorization: SSWS $OKTA_API_TOKEN" \
  "https://$OKTA_DOMAIN/api/v1/users?limit=200" | jq -r '.[].profile.email')

INACTIVE=$(comm -23 <(echo "$ALL_USERS" | sort) <(echo "$ACTIVE_USERS" | sort))

# Keycloak で無効化（上記同様）
# ...
```

#### 10.7.6 UX チェックリスト（短命 Token 採用時）

短命 Token (15 分) 採用時の必須実装項目:

```
[クライアント側]
□ Silent Refresh の自動化（残り 60 秒前にトリガー）
□ Refresh 失敗時の透過的リトライ（指数バックオフ）
□ Refresh Token 失効時のみ再ログイン UI
□ Multi-Tab 同期（BroadcastChannel）
□ オフライン時の Service Worker キャッシュ
□ 長時間タスクの Background Job 化（Token 非依存）
□ ファイルアップロードの Presigned URL 化（Token 非依存）

[サーバー側]
□ Keycloak Token Endpoint の高可用性（Refresh トラフィック増加対応）
□ Refresh Token Rotation 有効化
□ Refresh 時に max_age=0 や prompt=login を強制しない（致命的 UX 悪化）
□ 監査ログで「Refresh ごと再認証強制」を計測（誤設定検知）

[運用]
□ Token 関連エラーレートのアラート（Refresh 失敗率 > 1% で警告）
□ 業務系アプリと管理系で別 Realm + 別 TTL（業務 = 8h、管理 = 15min 等）
□ 長時間バッチ処理は Service Account + Client Credentials で実行
```

#### 10.7.7 Compensating Controls Worksheet テンプレート（PCI DSS Appendix B）

QSA 申請用のテンプレート例:

| Element | 記載内容 |
|---|---|
| **1. 制限事項の文書化** | 顧客 IdP（[IdP 名]）が SCIM 2.0 Provisioning に非対応のため、PCI DSS 8.2.5 の即時取消の厳密適合（数秒〜数十秒）が不可 |
| **2. 代替手段の効果分析** | (a) Access Token TTL を 15 分に短縮、(b) 顧客 IdP 認証ログ API を毎日逆引きし 7 日未認証ユーザーを論理削除、(c) Refresh ごとに Keycloak DB の `enabled` チェック、(d) ITDR で異常ログイン検知 → 自動アラート + 自動無効化 |
| **3. 高レベルのリスク** | TTL 15 分間のアクセスリスク残存。推定 deprovisioning（7 日）の誤検知リスク（長期休暇等）。これらを ITDR の異常検知 + 監査ログ完全保持で補完 |
| **4. 維持手順** | 月次 QSA レポート + Refresh Token Rotation の動作確認 + 認証ログ逆引きバッチの実行ログ確認 + 退職者シナリオの四半期テスト |
| **5. 検証** | 四半期ペネトレーションテスト + 退職シナリオ模擬テスト + ITDR 検知率測定（false positive < 5%、false negative < 1%）|

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

### 11.4 コンプライアンス（PCI DSS / APPI）

- [PCI DSS v4.0.1（PCI Security Standards Council、2025）](https://www.pcisecuritystandards.org/document_library/)
- [PCI DSS v4.0 Requirement 8 解説（VistaInfoSec）](https://vistainfosec.com/blog/pci-dss-requirement-8-changes-from-v3-2-1-to-v4-0-explained/)
- [PCI DSS v4.0.1 Universal MFA 拡大（HYPR）](https://www.hypr.com/blog/pci-dss-4.0.1-what-changed-and-how-is-this-the-next-step-for-universal-mfa)
- [個人情報保護法ガイドライン（通則編）— 個人情報保護委員会](https://www.ppc.go.jp/personalinfo/legal/guidelines_tsusoku/)
- [個人情報保護委員会 行政指導動向 2025-03（JPAC）](https://blog.jpac-privacy.jp/administrativeguidancefromppc_202503/)
- [APPI 2025 三年見直し動向](https://datasign.jp/blog/appi-2025/)

### 11.5 内部関連ドキュメント

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
- 2026-06-08: **§10.4 JIT 定期バッチ deprovisioning 実装** + **§10.5 Keycloak DB 保持・削除マトリクス** + **§10.6 PCI DSS v4.0 / APPI 適合性チェックリスト** を追加。proposal §FR-7.4.6 末尾の保持・削除マトリクス + §FR-7.4.7 末尾の定期バッチ + §FR-7.4.8 PCI DSS/APPI 適合性整理の **実装目線詳細** として対応。kcadm.sh ベースのバッチスクリプト例 + Kubernetes CronJob 例 + PCI DSS Req 8 全要件のマッピング + APPI 法 22/23/25/26/28-30 条のマッピングを集約
- 2026-06-08: **§10.7 SCIM 非対応 IdP 顧客向け Compensating Controls 実装詳細** を追加（proposal §FR-7.4.9 の Keycloak 実装目線詳細）。短命 Access Token (15min) + Refresh Token Rotation の Keycloak 設定、SPA/SSR の Silent Refresh 実装パターン、Multi-Tab UX、長時間タスク設計、BCL 受信実装、Microsoft Entra Graph API / Okta System Log API 認証ログ逆引きバッチ、UX チェックリスト、Compensating Controls Worksheet テンプレートを集約。**RFC 9700 (2025) OAuth 2.0 Best Current Practice 整合**|
