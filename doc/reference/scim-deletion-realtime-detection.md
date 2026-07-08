# SCIM 削除リアルタイム検知 + PII 最小化ガイド（2-tier Keycloak）

> **目的**: 顧客 IdP / IdP-KC のユーザ削除をリアルタイムで検知し、下流アプリへ即時反映するための設計と、Broker Keycloak の PII 保有を最小化する実装方針を集約する reference doc。
> **対象読者**: プラットフォーム設計者 / SCIM 実装担当 / セキュリティ / コンプラ担当
> **位置付け**: [ADR-025 SCIM 2.0 の位置づけと受信スタンス](../adr/025-scim-positioning-and-receive-stance.md) §I の実装裏どり / [ADR-033 Keycloak 2-tier アーキ](../adr/033-keycloak-2tier-broker-idp-architecture.md) の Shallow Broker 原則の具体化
> **関連**:
> - [ADR-023 ServiceNow SP 連携設計](../adr/023-servicenow-sp-integration.md)
> - [ADR-025 SCIM 2.0 の位置づけと受信スタンス](../adr/025-scim-positioning-and-receive-stance.md)
> - [ADR-033 Keycloak 2-tier アーキ](../adr/033-keycloak-2tier-broker-idp-architecture.md)
> - [ADR-048 Data Portability / Cryptographic Erasure](../adr/048-data-portability-subject-rights.md)
> - [common/scim-operations.md](../common/scim-operations.md)
> - [common/jit-scim-coexistence-keycloak.md](../common/jit-scim-coexistence-keycloak.md)
> - [common/hook-architecture-keycloak.md](../common/hook-architecture-keycloak.md)
> - [common/broker-data-model.md](../common/broker-data-model.md)
> - [reference/servicenow-sso-user-linking-guide.md](servicenow-sso-user-linking-guide.md)

---

## 目次

1. [要件整理と適用範囲](#1-要件整理と適用範囲)
2. [全体アーキ（2 SCIM Server + EventBridge 統合）](#2-全体アーキ2-scim-server--eventbridge-統合)
3. [削除検知の 3 経路](#3-削除検知の-3-経路)
4. [Broker の PII 最小化方針（Minimum Storage）](#4-broker-の-pii-最小化方針minimum-storage)
5. [APPI 観点の解釈と実装原則](#5-appi-観点の解釈と実装原則)
6. [ゾンビセッション対策（4 手段）](#6-ゾンビセッション対策4-手段)
7. [顧客 IdP 別の SCIM 対応状況](#7-顧客-idp-別の-scim-対応状況)
8. [SLA と遅延見積](#8-sla-と遅延見積)
9. [Metatavu keycloak-scim-server 実装ガイド](#9-metatavu-keycloak-scim-server-実装ガイド)
10. [外部 SaaS への SCIM 送信（Broker → SP）](#10-外部-saas-への-scim-送信broker--sp)
11. [Rate Limit の正確な値](#11-rate-limit-の正確な値)
12. [Phase 別実装計画](#12-phase-別実装計画)
13. [テスト観点](#13-テスト観点)
14. [参考文献](#14-参考文献)
15. [改訂履歴](#15-改訂履歴)

---

## 1. 要件整理と適用範囲

### 要件

| 項目 | 内容 |
|---|---|
| **主目的** | ユーザ削除のリアルタイム検知（deprovisioning trigger）|
| **対象データソース** | ① 顧客 IdP（Entra ID / Okta 等）② IdP-KC のローカルユーザ |
| **前提** | 顧客 IdP は SCIM 対応済み（JIT-only 顧客は別途検討）|
| **削除 SLA** | 業種標準: 60 秒以内、規制業種: 数秒以内 |
| **下流連携** | Session revoke / SaaS SCIM Push / 監査ログ |

### スコープ外（別 doc / 別 Phase）

- 顧客 IdP が JIT-only の場合の削除検知（Phase 2 で別途）
- SCIM CREATE / UPDATE の詳細フロー（既存 [scim-operations.md](../common/scim-operations.md) 参照）
- 属性の継続同期（別途 SCIM UPDATE 経由）
- SAML/OIDC の認証プロトコル詳細

---

## 2. 全体アーキ（2 SCIM Server + EventBridge 統合）

```
┌─ 顧客 IdP（SCIM 対応）──┐         ┌─ 顧客 HRIS ──┐
│ Entra ID / Okta         │         │ (SCIM 対応時) │
│ Google Cloud Identity   │         │ Workday / SAP │
└──────────┬──────────────┘         └───────┬──────┘
           │                                │
           │ SCIM DELETE Push               │ SCIM DELETE Push
           │ (CREATE/UPDATE も並行)         │
           ▼                                ▼
    ┌─────────────────────┐         ┌─────────────────────┐
    │ Broker Keycloak     │         │ IdP Keycloak         │
    │ SCIM Server:        │         │ SCIM Server:         │
    │  Metatavu (Apache2) │         │  Metatavu (Apache2)  │
    │ Event Listener SPI: │         │ Event Listener SPI:  │
    │  USER_DELETE 検知    │         │  USER_DELETE 検知     │
    │ Minimum Storage 方針 │         │ Full User 保持       │
    └──────────┬──────────┘         └──────────┬──────────┘
               │                                │
               │ Deletion Event                 │ Deletion Event
               │ (SQS enqueue、非同期)          │ (SQS enqueue、非同期)
               ▼                                ▼
       ┌──────────────────────────────────────────────┐
       │  AWS EventBridge (削除イベントバス)          │
       └──────────────────────┬───────────────────────┘
                              │
              ┌───────────────┼──────────────────┐
              ▼               ▼                  ▼
        ┌──────────┐    ┌─────────────┐    ┌───────────┐
        │ Session  │    │ SaaS SCIM   │    │ 監査ログ    │
        │ Revoke   │    │ Push Lambda │    │  記録      │
        │ Lambda   │    │ (SN/SF等)   │    │           │
        └──────────┘    └─────────────┘    └───────────┘
```

### 主要コンポーネント

| コンポーネント | 実装 | 用途 |
|---|---|---|
| **Broker SCIM Server** | Metatavu keycloak-scim-server (Apache 2.0) | 顧客 IdP からの CREATE/UPDATE/DELETE 受信 |
| **IdP-KC SCIM Server** | Metatavu keycloak-scim-server (Apache 2.0) | 顧客 HRIS からの CREATE/UPDATE/DELETE 受信 |
| **Broker Event Listener SPI** | Custom Java SPI | USER_DELETE / USER_DISABLE → SQS enqueue |
| **IdP-KC Event Listener SPI** | 同一実装、Realm 別デプロイ | 同上 |
| **削除イベントバス** | AWS EventBridge | Broker + IdP-KC の削除イベント集約 |
| **Session Revoke Lambda** | Node.js/Python | 削除 → `not_before` セット + 全 Refresh Token revoke |
| **SaaS SCIM Push Lambda** | Node.js/Python | 削除 → ServiceNow/Salesforce/Slack へ SCIM DELETE |
| **監査ログ** | CloudWatch + S3（Object Lock, 7 年）| 削除イベントの証跡 |

---

## 3. 削除検知の 3 経路

### 経路 1: 顧客 IdP → Broker（フェデユーザ削除）

```
顧客 Entra ID / Okta
    ↓ SCIM DELETE Push
Broker (Metatavu SCIM Server)
    ↓ enabled=false + not_before=NOW
Broker Event Listener SPI (USER_DELETE)
    ↓ SQS enqueue
EventBridge → Downstream 処理
```

- **代表顧客タイプ**: 自社 IdP を持つ大手顧客（Federation 顧客）
- **SCIM Push 元**: 顧客 IdP の SCIM Provisioning app
- **本基盤の受信 Endpoint**: `https://scim-broker.basis.example.com/realms/{realm}/scim/v2/Users/{id}`

### 経路 2: 顧客 HRIS → IdP-KC（ローカルユーザ削除）

```
顧客 HRIS (Workday / SAP / SmartHR)
    ↓ SCIM DELETE Push
IdP-KC (Metatavu SCIM Server)
    ↓ enabled=false + not_before=NOW
IdP-KC Event Listener SPI (USER_DELETE)
    ↓ SQS enqueue
EventBridge → Downstream 処理
```

- **代表顧客タイプ**: 自社 IdP を持たない中小顧客、HRIS が SCIM Push を実行
- **本基盤の受信 Endpoint**: `https://scim-idp.basis.example.com/realms/{realm}/scim/v2/Users/{id}`

### 経路 3: Tenant Admin Portal 手動削除（IdP-KC 内で完結）

```
Tenant 管理者 → Tenant Admin Portal UI
    ↓ Keycloak Admin API DELETE
IdP-KC (User 削除実行)
    ↓ Event 発火
IdP-KC Event Listener SPI (USER_DELETE)
    ↓ SQS enqueue
EventBridge → Downstream 処理
```

- **代表顧客タイプ**: HRIS 連携なしで手動運用する顧客
- Event Listener SPI は経路 1/2 と共通、SCIM 経由でも UI 経由でも同じイベント発火

---

## 4. Broker の PII 最小化方針（Minimum Storage）

### 方針の背景

- 標準の Keycloak Broker Federation では、フェデユーザに対して `user_entity` + `user_attribute` + `federated_identity` が完全に保存される
- ADR-033 の「Shallow Broker」は **PW ハッシュ非保持**の意味（credential テーブル空）だが、**PII 属性は普通に保存される**
- 事故時の影響範囲を限定し、APPI の安全管理措置対象データ量を減らすため、**設計判断として PII 保有を最小化**する

### Broker が保有する情報 3 レベル

| レベル | Broker DB 保有内容 | 実装 | 実装コスト |
|---|---|---|---|
| **L1: フル保有**（Metatavu 標準）| user_entity + 全 attribute + federated_identity + role/group + session | Metatavu SCIM Server + IdP Mapper 標準 | 低 |
| **★ L2: Minimum Storage** ★採用推奨 | user_entity (id + username) + federated_identity + session のみ | Metatavu + IdP Mapper 属性フィルタ | 低〜中 |
| L3: ほぼゼロ保有 | user_entity (id) + session のみ、PII は外部 DB | Custom User Storage SPI + 外部 SCIM Gateway | **高**（2-4 週間）|

### Minimum Storage (L2) の具体実装

#### IdP Mapper Sync Mode の設定

顧客 IdP のフェデ設定で、以下の Sync Mode を採用:

- **SYNC_MODE = FORCE**: 毎回ログイン時に属性を上書き（陳腐化防止）
- **ただし Import する属性を制限**: `username` / `email` / `tenant_id` のみ Import
- **Role / Group は Claim ベースで都度算出**: user_role_mapping に永続化しない

Keycloak Admin Console 設定例:

```
Identity Providers > acme-entra-saml > Mappers
├── Username Mapper (SAML NameID → username)      [Import]
├── Tenant ID Mapper (SAML tenant_id → tenant_id) [Import]
├── Email Mapper (SAML email → email)             [Import]
└── (他の属性は Import せず、都度 Claim から取得)
```

#### 保存されないもの（意図的）

- `department`, `manager_email`, `cost_center`, `office_location`, `job_title` 等の詳細属性
- 顧客 IdP 側で管理、本基盤は都度 Claim 経由で参照
- Access Token 発行時に必要な属性は Claim Mapper で JWT に埋め込む（DB 保存不要）

#### 保存される最小データ

```
user_entity:
  id:                   UUID (Keycloak 生成、不可逆)
  username:             "acme-EMP-001234"（ハイフン区切り、ADR-055）
  email:                (optional、削除検知用に持つ場合のみ)
  enabled:              true / false
  realm_id:             broker

federated_identity:
  identity_provider:    "acme-entra-saml"
  federated_user_id:    顧客 IdP の sub
  federated_username:   顧客 IdP の userName

credential:             （空、PW hash なし）

user_attribute:         （空 or tenant_id のみ）

user_role_mapping:      （空、都度算出）

user_group_membership:  （空、都度算出）
```

#### データサイズ試算（1.05M フェデユーザ）

| テーブル | L1 フル | L2 Minimum |
|---|---|---|
| user_entity | ~1 GB | ~500 MB（属性減）|
| user_attribute | ~2 GB | ~50 MB（tenant_id のみ）|
| federated_identity | ~500 MB | ~500 MB |
| user_role_mapping | ~200 MB | ~0（Claim ベース）|
| user_group_membership | ~200 MB | ~0（Claim ベース）|
| **合計** | **~4 GB** | **~1 GB（-75%）** |

### L2 採用時の SCIM 受信の挙動

- SCIM CREATE 受信時: user_entity + federated_identity のみ作成、詳細属性は無視
- SCIM UPDATE 受信時: username / email 更新のみ、詳細属性は無視
- SCIM DELETE 受信時: enabled=false（従来通り、変更なし）

**注意**: 顧客 IdP から SCIM で送られる属性の一部を意図的に廃棄することになる。「保有しない」という選択は顧客との DPA で明示すべき。

---

## 5. APPI 観点の解釈と実装原則

### 重要な認識

**APPI に "データ最小化" の明示規定は存在しない**（GDPR Article 5(1)(c) とは違う）。関連条文:

- 法第 17 条（利用目的の特定）
- 法第 18 条（利用目的による制限）
- 法第 22 条（**利用する必要がなくなったときは遅滞なく消去、努力義務**）
- 法第 23 条（必要かつ適切な安全管理措置）

### Minimum Storage (L2) の APPI 上の位置付け

| 論点 | 回答 |
|---|---|
| L2 は APPI 違反か? | ❌ 違反ではない |
| L2 は APPI 準拠か? | ✅ 適切な安全管理措置があれば準拠 |
| L2 で APPI 適用範囲が縮小するか? | ❌ 縮小しない（保有事業者としての義務は同じ）|
| L2 のメリット | 事故時の影響範囲限定、削除権対応コスト削減、監査対応容易化 |

### 「保有していない」と主張できるか

APPI 上「保有」の判定は**事業者内で他情報と容易照合可能か**による（法第 2 条、PPC 通則編 2-1）:

- Broker が UUID + username のみ保有
- 同一事業者内の他システム（IdP-KC / 外部 DB）に PII あり
- UUID / username で紐付け可能
- → **事業者全体では「保有」に該当**

**結論**: 「Broker で保有量を最小化」しても「事業者として保有しない」ことにはならない。APPI 適用範囲は変わらない。

### 実装原則

1. **法第 22 条の努力義務を満たす**: SCIM DELETE 受信時に速やかに `enabled=false` + `not_before` セット
2. **法第 23 条の安全管理措置**: Aurora + KMS CMK で暗号化 + アクセス制御 + 監査
3. **法第 25 条の委託先監督**: 顧客との DPA に「弊社が保有する PII の範囲」明示
4. **法第 30 条の削除権対応**: SCIM DELETE または匿名化スクリプト（ADR-048 連動）で対応

### 顧客説明で使える表現（誤解を避ける）

| ❌ 誤解を招く | ✅ 正確 |
|---|---|
| PII を持たないので APPI 対象外 | PII を最小限に絞り、APPI の要件を満たします |
| 最小化により APPI 対応不要 | APPI に最小化義務はないが、事故時のリスク低減目的で最小化 |
| GDPR の最小化原則に従い | 実装ベストプラクティスとして最小化（APPI 明示規定なし）|

---

## 6. ゾンビセッション対策（4 手段）

### 問題: JWT の Stateless 特性

- Access Token は JWT（自己完結型）
- Broker で `enabled=false` にしても、既発行 Access Token は TTL 内で有効
- App が JWT を検証するだけなら、削除ユーザが最大 Access Token TTL 分アクセス可能

### 対策手段の比較

| 手段 | ゾンビ期間 | 実装コスト | 適用 |
|---|---|---|---|
| **① Access Token TTL 短縮** | TTL 分（例: 5 分）| ゼロ | ★ 全 Phase 必須 |
| **② `not_before` + Session revoke** | Refresh 時に即時ブロック | 低（SCIM Event Listener 内で実行）| ★ 全 Phase 必須 |
| **③ Backchannel Logout** | 数秒（RP 実装依存）| 中（各 RP に Endpoint 実装要）| Phase 1 or 2 |
| **④ API Gateway Token Introspection** | リアルタイム（1 API 呼出以内）| 中〜高（レイテンシ +20-50ms）| Phase 2、高機密 API のみ |

### 手段 1: Access Token TTL 短縮

Realm Settings > Tokens で以下:

```
Access Token Lifespan:            5 分
Refresh Token Lifespan:           30 分
SSO Session Idle:                 30 分
SSO Session Max:                  8 時間
```

- ゾンビ期間: 最大 5 分
- パフォーマンス: 5 分ごとの Refresh 要、負荷 3-5%増（許容範囲）

### 手段 2: `not_before` + Session revoke

Metatavu SCIM Server + Custom Event Listener SPI で実装:

```java
// SCIM DELETE 受信時、Event Listener SPI で実行
@Override
public void onEvent(Event event) {
    if (event.getType() == EventType.DELETE_ACCOUNT
        || event.getType() == EventType.USER_DISABLED) {
        
        // 1. not_before を現在時刻に設定
        UserModel user = session.users().getUserById(realm, event.getUserId());
        user.setNotBefore((int)(System.currentTimeMillis() / 1000));
        
        // 2. 全 Session revoke
        session.sessions().removeUserSessions(realm, user);
        
        // 3. Offline session も削除
        session.sessions().getOfflineUserSessionsStream(realm, user)
            .forEach(s -> session.sessions().removeOfflineUserSession(realm, s));
        
        // 4. EventBridge へ enqueue
        sqsClient.sendMessage("deletion-events", buildEvent(user));
    }
}
```

- 効果: Broker が受ける refresh 要求は即時ブロック
- 限界: JWT を検証するだけの RP は素通し（Access Token TTL 依存）

### 手段 3: Backchannel Logout（OIDC 標準）

各アプリ（RP）が `backchannel_logout_uri` を実装:

```
[Broker] SCIM DELETE 受信
    │
    │ 各 App の backchannel_logout_uri へ POST
    │
    ├──→ POST https://app1.example.com/backchannel-logout
    │        Body: logout_token (JWT)
    ├──→ POST https://app2.example.com/backchannel-logout
    └──→ POST https://app3.example.com/backchannel-logout
```

Keycloak 設定:

```
Clients > my-app > Settings
├── Frontchannel Logout: false
├── Backchannel Logout URL: https://my-app.example.com/backchannel-logout
├── Backchannel Logout Session Required: true
```

- 効果: App 側で即時 Session 削除
- 前提: 各 RP が Backchannel Logout Endpoint を実装

### 手段 4: API Gateway Token Introspection

高機密 API（決済、個人情報アクセス、管理操作）は API Gateway でリアルタイム検証:

```
[App] ─── API 呼出 ───→ [API Gateway]
                            │
                            │ POST /realms/{realm}/protocol/openid-connect/token/introspect
                            │  (client_credentials で認証、token を送る)
                            ▼
                        [Broker]
                            │ user.enabled + not_before + revoked check
                            ▼
                        active: true / false
```

- 効果: 完全リアルタイム（削除後 <1 秒で無効化）
- コスト: 全 API 呼出で Broker 経由、レイテンシ +20-50ms
- 適用: 高機密 API のみ（キャッシュ 30 秒等で緩和可能）

### 本基盤の推奨実装

**Phase 1**:
- 手段 1 + 手段 2 の組合せ
- ゾンビ期間: 最大 5 分
- PCI DSS §8.2.5「即時無効化」→ 5 分は SLA 60 秒超過だが、業界標準の Access Token TTL 5-15 分と整合

**Phase 2**:
- 手段 3 の Backchannel Logout を主要 App に実装
- ゾンビ期間: 数秒〜5 分

**Phase 3+**（規制業種顧客向け）:
- 手段 4 の Introspection を高機密 API のみに適用
- ゾンビ期間: リアルタイム（<1 秒）

---

## 7. 顧客 IdP 別の SCIM 対応状況

### SCIM Outbound Push 対応（顧客 IdP から本基盤 Broker への送信）

| 顧客 IdP | SCIM Push 対応 | 詳細 |
|---|:-:|---|
| **Microsoft Entra ID** | ✅ | Enterprise Application SCIM Provisioning、5-40 分周期、Real-time は Preview |
| **Okta** | ✅ | SCIM Provisioning App（OIN or Private App）、5-30 分周期 |
| **Google Cloud Identity** | ✅ | SCIM 対応 |
| **Ping Identity / ForgeRock** | ✅ | Provisioning Service 標準機能 |
| **HENNGE One** | 要確認 | 個別ヒアリング必要 |
| **Auth0** | ❌ **Native 非対応** | Outbound SCIM は 2026-07 時点でネイティブ機能なし。Event Streams + Custom Actions で workaround |
| **SAML JIT-only** | ❌ | SCIM 未対応、Phase 2 で別途検討 |

### Auth0 顧客の workaround

Auth0 は Inbound SCIM は対応するが、**Outbound SCIM は非対応**。以下で回避:

1. **Event Streams** で User Deleted イベントを購読
2. **Custom Actions** で本基盤の SCIM Endpoint に PATCH（active=false）or DELETE を Push
3. または **AWS Lambda 経由**で Bridge 実装

このため、Auth0 顧客は **B-SCIM-N** ヒアリング項目で個別対応要件を確認。

---

## 8. SLA と遅延見積

### エンド to エンド の遅延内訳

| ステップ | 想定遅延 |
|---|---|
| 顧客 IdP DELETE 発生 → 本基盤受信 | 5-30 秒（顧客 IdP の SCIM Push サイクル依存）|
| 本基盤受信 → SCIM Server 処理 | <100 ms |
| SCIM Server → Event Listener SPI 発火 | <50 ms |
| Event Listener SPI → SQS enqueue | <100 ms |
| SQS → EventBridge Rule → Lambda 起動 | <1 秒 |
| Session Revoke Lambda → Keycloak Admin API 完了 | <500 ms |
| **合計: 顧客 IdP DELETE → Session 無効化** | **6-32 秒** |
| Access Token TTL (5 分) 経過による JWT 失効 | +5 分 |
| **完全遮断（Access Token 含む）** | **最大 5 分 32 秒** |

### 規制対応

| 規制 | SLA 要件 | 本設計での対応 |
|---|---|---|
| PCI DSS §8.2.5 | 即時無効化 | ✅ Session revoke は即時、Access Token は TTL 依存（5 分）|
| APPI 法第 22 条 | 遅滞なく消去 | ✅ SCIM DELETE で速やかに enabled=false |
| ISO 27001 A.9.2.6 | Access rights removal | ✅ 上記同等 |
| SOC 2 CC6.2 | Access management | ✅ 監査ログで証跡 |

---

## 9. Metatavu keycloak-scim-server 実装ガイド

### なぜ Metatavu を選定

| 項目 | Metatavu | Phase Two | Native 26.6 |
|---|---|---|---|
| ライセンス | **Apache 2.0** ★ | Elastic License v2 | Apache 2.0 |
| Status | Production Ready | Production Ready | **Experimental** |
| Keycloak 対応 | 26.3.5+ | 26.x | 26.6+ (要 `--features=scim-api`) |
| Organization-scoped | ✅ | ✅ | ✅ |
| SaaS 販売可否 | ✅ 制約なし | ⚠️ 販売 NG | ✅ |
| Bulk API | ❌ | 部分対応 | ❌ |
| コミュニティ | 中 | 大 | 公式 |

**選定理由**:
- **Apache 2.0** で SaaS 販売の商用利用可能（Phase Two ELv2 制約回避）
- Production Ready（Native 26.6 の Experimental より安全）
- Native 26.6 が Stable 昇格したら Phase 2 で移行検討

### インストール手順

```bash
# 1. Metatavu keycloak-scim-server JAR を取得
wget https://github.com/Metatavu/keycloak-scim-server/releases/download/v1.6.0/keycloak-scim-server.jar

# 2. Keycloak providers ディレクトリに配置
cp keycloak-scim-server.jar $KC_HOME/providers/

# 3. Optimized build 再実行
kc.sh build

# 4. Realm 単位で SCIM Provider 有効化
# Realm Settings > Themes > SCIM Provider Configuration
```

### Endpoint 構造

```
Realm 単位:
  https://scim-{tier}.basis.example.com/realms/{realm}/scim/v2/{Users,Groups}

Organization 単位（v26 Organizations 連携）:
  https://scim-{tier}.basis.example.com/realms/{realm}/scim/v2/organizations/{orgId}/{Users,Groups}
```

### 2-tier での URL 分離

```
Broker Keycloak:
  https://scim-broker.basis.example.com/realms/broker/scim/v2/organizations/{tenant}/Users

IdP Keycloak:
  https://scim-idp.basis.example.com/realms/idp/scim/v2/organizations/{tenant}/Users
```

- 顧客 IdP / HRIS は自身が Push すべき先を判別（Broker vs IdP-KC）
- CloudFront + WAF で URL パスベースで振り分け（[ADR-039](../adr/039-centralized-network-account-edge-layer.md) 5 アカウント体系連動）

### 認証設定

SCIM Client は OAuth 2.0 Client Credentials で認証:

```
Keycloak Client 設定:
  Name:                    scim-client-{customer}
  Access Type:             confidential
  Service Account Enabled: true
  Client Roles:            manage-users, view-users, query-users, query-groups, view-realm
```

顧客 IdP は取得した Bearer Token を SCIM Endpoint に提示:

```http
POST /realms/broker/scim/v2/organizations/acme/Users HTTP/1.1
Host: scim-broker.basis.example.com
Authorization: Bearer <access_token>
Content-Type: application/scim+json

{
  "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
  "userName": "acme-EMP-001234",
  ...
}
```

### IdP Mapper 設定（Minimum Storage 実現）

L2 Minimum Storage を実現するための IdP Mapper 設定:

```json
[
  {
    "name": "username-mapper",
    "identityProviderMapper": "saml-username-idp-mapper",
    "config": {
      "syncMode": "FORCE",
      "userAttribute": "username"
    }
  },
  {
    "name": "tenant-id-mapper",
    "identityProviderMapper": "saml-user-attribute-idp-mapper",
    "config": {
      "syncMode": "FORCE",
      "userAttribute": "tenant_id",
      "attribute.name": "tenant_id"
    }
  }
  // 他の属性 mapper は追加しない（Import しない）
]
```

Role Claim は都度 Claim Mapper で JWT に埋め込む（DB 保存不要）:

```json
{
  "name": "role-claim-mapper",
  "protocolMapper": "oidc-usermodel-realm-role-mapper",
  "config": {
    "claim.name": "roles",
    "id.token.claim": "true",
    "access.token.claim": "true"
  }
}
```

---

## 10. 外部 SaaS への SCIM 送信（Broker → SP）

### アーキ

Broker が SCIM Client として ServiceNow / Salesforce / Slack へ削除を Push:

```
Broker Event Listener SPI (USER_DELETE)
    ↓ SQS enqueue（非同期化必須、EL SPI は同期実行のため）
    ↓
[EventBridge Rule で Fan-out]
    ├─→ ServiceNow SCIM Push Lambda
    ├─→ Salesforce SCIM Push Lambda
    └─→ Slack SCIM Push Lambda
```

### なぜ Event Listener SPI で直接 SCIM Push しないか

- **Event Listener SPI は同期実行**が公式仕様
- 直接 SCIM Push すると認証レイテンシに直撃（外部 SaaS 応答遅延で数秒）
- **必ず SQS enqueue + 非同期 Lambda で Push** の 2 段構え

### Transaction Commit 前の Event 発火問題

Keycloak Event Listener には Transaction Commit 前に発火するケースがあり、race condition の元凶:

**対策**: Custom Event Listener で `EventListenerTransaction` を使い、**Post-Commit 発火に統一**:

```java
public class PostCommitScimEventListener implements EventListenerProvider {
    
    @Override
    public void onEvent(Event event) {
        // 同期発火時は enqueue のみ、Push は行わない
        session.getTransactionManager().enlistAfterCompletion(new AfterCompletion() {
            @Override
            public void afterCompletion(int status) {
                if (status == Status.STATUS_COMMITTED) {
                    // Post-Commit で SQS enqueue
                    sqsClient.sendMessage("scim-outbound-queue", buildEvent(event));
                }
            }
        });
    }
}
```

### Retry と DLQ 設計

- **Exponential Backoff**: 1 分 → 5 分 → 15 分 → 60 分（最大 4 回リトライ）
- **DLQ**: 全リトライ失敗時に Dead Letter Queue へ、監査ログ + アラート
- **冪等性**: SCIM DELETE は同じユーザに複数回実行しても 404 or no-op（安全）

---

## 11. Rate Limit の正確な値（過去の誤り訂正）

### ServiceNow

- **公式に固定値なし**（誤情報訂正）
- インスタンス単位で「Rate Limit Rules」を管理者が設定（通常 per-hour）
- **実装前に顧客インスタンスの Rate Limit Rule 設定確認が必須**（B-SN-N ヒアリング項目）

### Salesforce

- **公式に per-second 値なし**（誤情報訂正）
- プラットフォーム API 全体で 24 時間あたりの上限（Enterprise Edition 10 万〜、Editions 依存）
- **実運用は 15 req/sec 以下推奨**（業界ベストプラクティス）
- Bulk API は別枠

### Slack

- **正しい値**（Slack 公式 SCIM Rate Limits Doc）:
  - **Write (POST/PUT/PATCH/DELETE): 合計 600 req/min, burst 180**
  - **Read (GET): 合計 1000 req/min, burst 1000**
  - **Endpoint 単位**:
    - Create/Update/Delete User: 180 req/min, burst 20
    - Get User: 300 req/min, burst 300
- 「Tier 2 = 20 req/min per Method」は **Slack Web API と混同**した誤情報

### Workday

- **Strategic Sourcing SCIM: 5 req/sec**（唯一明確に公表されている値）
- Workday HCM 全体の SCIM は Enterprise pricing、SSO 必須

---

## 12. Phase 別実装計画

### Phase 1（MVP、SCIM 削除リアルタイム検知）

- [x] Broker Keycloak に Metatavu SCIM Server 導入
- [x] IdP-KC に Metatavu SCIM Server 導入
- [x] Custom Event Listener SPI 実装（USER_DELETE → SQS enqueue）
- [x] EventBridge Rule で Session Revoke Lambda を fan-out
- [x] Session Revoke Lambda 実装（`not_before` + Session removal）
- [x] Broker 側 IdP Mapper 設定で Minimum Storage 実現
- [x] Access Token TTL = 5 分に設定
- [x] SCIM 監査ログを CloudWatch → S3（Object Lock 7 年）
- [x] Auth0 顧客の workaround（Event Streams + Custom Actions）ドキュメント化

### Phase 2（拡張）

- [ ] Backchannel Logout を主要 App に実装
- [ ] ServiceNow / Salesforce / Slack への SCIM Push Lambda 実装
- [ ] SCIM Push Retry / DLQ 設計
- [ ] 全件 Reconciliation（週次 Bulk 検証）
- [ ] 顧客 IdP が JIT-only の場合の別途検討（別 ADR）

### Phase 3+（規制業種顧客向け）

- [ ] API Gateway Token Introspection（高機密 API のみ）
- [ ] Keycloak Native SCIM 26.6+ Stable 昇格後、Metatavu からの移行検討
- [ ] SCIM Bulk API 対応（Phase 2 で Metatavu 経由 or Native Stable 版）

---

## 13. テスト観点

### 機能テスト

- 顧客 IdP から Broker への SCIM DELETE 受信 → Session 無効化確認
- 顧客 HRIS から IdP-KC への SCIM DELETE 受信 → Session 無効化確認
- Tenant Admin Portal 手動削除 → Event Listener 発火確認
- Access Token 期限内アクセス（ゾンビ期間の実測）
- Refresh Token での更新試行 → 即時ブロック確認
- Auth0 workaround の Event Streams 経由 Push 動作確認

### 非機能テスト

- 削除イベント TPS 想定: 100 events/sec（規模別）
- SCIM Push レイテンシ: <1 秒（Broker 受信 → Session 無効化）
- ゾンビ期間: Access Token TTL 5 分以内で無効化されること
- Transaction Commit 前の Event 発火 race condition の再現確認

### コンプラテスト

- APPI 法第 22 条: 削除の遅滞なき実行（5 分以内）
- PCI DSS §8.2.5: 即時無効化の証跡（監査ログで確認）
- 削除イベントの監査ログ完全性（S3 Object Lock で改ざん検証）

### 障害テスト

- SCIM Server 障害時の DLQ 挙動
- EventBridge 遅延時の下流影響
- Backchannel Logout 失敗時のリトライ挙動
- Aurora 書込み遅延時の Broker 動作

---

## 14. 参考文献

### Keycloak 公式

- [Keycloak 26.6.0 Release Notes](https://www.keycloak.org/2026/04/keycloak-2660-released)
- [Keycloak SCIM as Experimental Feature](https://www.keycloak.org/2026/04/scim-as-experimental-feature)
- [Keycloak Server Developer Guide - User Storage SPI](https://www.keycloak.org/docs/latest/server_development/#_user-storage-spi)
- [Keycloak Server Administration - Backchannel Logout](https://www.keycloak.org/docs/latest/server_admin/#backchannel-logout)

### Metatavu keycloak-scim-server

- [GitHub: Metatavu/keycloak-scim-server](https://github.com/Metatavu/keycloak-scim-server)
- Apache 2.0 License

### SCIM 2.0 RFC

- [RFC 7643 - SCIM Core Schema](https://datatracker.ietf.org/doc/html/rfc7643)
- [RFC 7644 - SCIM Protocol](https://datatracker.ietf.org/doc/html/rfc7644)

### 顧客 IdP SCIM

- [Microsoft Entra ID - Use SCIM to provision users](https://learn.microsoft.com/en-us/entra/identity/app-provisioning/use-scim-to-provision-users-and-groups)
- [Okta SCIM Provisioning Integration](https://developer.okta.com/docs/guides/scim-provisioning-integration-overview/main/)
- [Auth0 Community - Outbound SCIM Provisioning (Not Supported)](https://community.auth0.com/t/enable-outbound-scim-provisioning-to-sync-users-and-roles-from-auth0-to-a-third-party-application/182503)
- [Auth0 Blog - Event Streams + Actions for SCIM workaround](https://auth0.com/blog/driving-business-outcomes-auth0-inbound-scim-event-streams/)

### 外部 SaaS SCIM

- [Slack SCIM Rate Limits](https://docs.slack.dev/reference/scim-api/rate-limits/)
- [ServiceNow SCIM API](https://www.servicenow.com/docs/bundle/yokohama-api-reference/page/integrate/inbound-rest/concept/scim-api.html)
- [ServiceNow REST API Rate Limits](https://www.servicenow.com/community/developer-articles/understanding-servicenow-rest-api-rate-limits-key-concepts-amp/ta-p/3407367)
- [Workday Strategic Sourcing SCIM (5 req/sec)](https://apidocs.workdayspend.com/services/scim/v2.html)

### APPI / 規制

- [個人情報の保護に関する法律（e-Gov 法令検索）](https://elaws.e-gov.go.jp/document?lawid=415AC0000000057)
- [PPC 通則編ガイドライン](https://www.ppc.go.jp/personalinfo/legal/guidelines_tsusoku/)
- [PCI DSS v4.0.1](https://www.pcisecuritystandards.org/)

### 本プロジェクト内 関連 doc

- [ADR-023 ServiceNow SP 連携設計](../adr/023-servicenow-sp-integration.md)
- [ADR-025 SCIM 2.0 の位置づけ](../adr/025-scim-positioning-and-receive-stance.md)
- [ADR-033 Keycloak 2-tier アーキ](../adr/033-keycloak-2tier-broker-idp-architecture.md)
- [ADR-048 Data Portability / Cryptographic Erasure](../adr/048-data-portability-subject-rights.md)
- [common/scim-operations.md](../common/scim-operations.md)
- [common/jit-scim-coexistence-keycloak.md](../common/jit-scim-coexistence-keycloak.md)
- [common/hook-architecture-keycloak.md](../common/hook-architecture-keycloak.md)
- [common/broker-data-model.md](../common/broker-data-model.md)
- [reference/servicenow-sso-user-linking-guide.md](servicenow-sso-user-linking-guide.md)

---

## 15. 改訂履歴

- 2026-07-08: 初版作成。SCIM 削除リアルタイム検知の全体アーキ（2 SCIM Server + EventBridge 統合）、Broker の PII 最小化方針（Minimum Storage L2 採用）、APPI 観点の解釈（最小化はベストプラクティスであり義務ではない、適用範囲は縮小しない）、ゾンビセッション対策 4 手段（Access Token TTL 短縮 / `not_before` + Session revoke / Backchannel Logout / API Gateway Introspection）、顧客 IdP 別 SCIM 対応（Auth0 例外の workaround 含む）、Metatavu keycloak-scim-server 実装ガイド、外部 SaaS SCIM 送信の Event Listener SPI 非同期化パターン、Rate Limit の正確な値（ServiceNow / Salesforce / Slack / Workday の誤情報訂正）、Phase 別実装計画、テスト観点、参考文献を集約。ADR-025 §I / ADR-033 §G.3（今後追記）の実装裏どりとして機能
