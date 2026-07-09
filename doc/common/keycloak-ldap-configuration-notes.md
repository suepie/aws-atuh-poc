# Keycloak LDAP 設定ノート — 実装時に意識すべきポイント集約

> **作成日**: 2026-07-08、**最終更新**: 2026-07-09（§12 に Transient Password Exposure 対策追記 + §13.7 実装チェックリストに 5 層防御項目追加）
> **対象**: Keycloak LDAP User Federation Provider の設定担当者・レビュー担当者・顧客説明担当者
> **元情報**: [ADR-025 §H](../adr/025-scim-positioning-and-receive-stance.md) / [§C-7.3.4.4.B](../requirements/proposal/common/07-implementation-architecture.md) / [§C-7.4.7](../requirements/proposal/common/07-implementation-architecture.md#c-747-ldap-顧客の-sso-ログインbind-pull-モデルimport-users--on2026-07-08-追加) / Keycloak 26 公式 Server Administration Guide

---

## 0. 本ドキュメントの位置づけ

Keycloak の LDAP User Federation Provider は **Keycloak 標準機能**（Custom SPI 開発不要）だが、**「デフォルト設定のままだと事故る箇所」が多い**。本ドキュメントは:

- 実装時に **設定漏れ・誤設定で発生する典型的な事故** を先に潰す
- **顧客ごとに異なる要件**（AD/OpenLDAP/AD LDS、Nested Groups、金融規制業界の Sync 頻度等）に対応する判断軸を提供
- **本基盤の運用ハマりどころ Top 10** を集約

**位置づけ**：ADR-025 §H が "戦略"（何を採用するか）、§C-7.3.4.4.B が "コンポーネント配置"、本ドキュメントが "設定リファレンス + 実装チェックリスト"。

**関連する主要 ADR**：
- [ADR-025 §H 顧客 IdP が LDAP(s) の場合の JIT/SCIM 扱い](../adr/025-scim-positioning-and-receive-stance.md)
- [ADR-009 MFA 責任はパスワード管理側](../adr/009-mfa-responsibility-by-idp.md)（§7 補完 MFA の根拠）
- [ADR-014 認証パターン範囲 K-12](../adr/014-auth-patterns-scope.md)（LDAP → Keycloak 必須化）
- [ADR-039 v2 §F.1.A LDAP Egress 経路](../adr/039-centralized-network-account-edge-layer.md)（Network Firewall 設定）
- [ADR-045 鍵管理戦略](../adr/045-cryptographic-key-management-strategy.md)（Bind Credential の KMS 保管）
- [ADR-055 HRD 実装方式](../adr/055-hrd-implementation-method-selection.md)（Organization スコープ + Custom SPI との連携）
- [ADR-057 CSRF 対策の責任分界](../adr/057-csrf-protection-responsibility-boundary.md)（LDAP の場合の CSRF 影響）
- [ADR-060 §C.2.2 Golden LDAP 検知](../adr/060-auth-protocol-attack-path-residual-tbd.md)（L-GD-1〜L-GD-5 シグナル）

**関連するヒアリング項目**：[B-LDAP-1〜7](../requirements/hearing-checklist.md)

---

## 1. 接続設定（Connection）

### 1.1 Connection URL

```
❌ ldap://ad.customer:389            # Plain LDAP、禁止（[ADR-025 §H.6](../adr/025-scim-positioning-and-receive-stance.md)）
❌ ldap://ad.customer:389 + StartTLS # 中間、非推奨
✅ ldaps://ad.customer:636           # LDAPS、必須
✅ ldaps://ad1:636 ldaps://ad2:636   # HA、スペース区切りで複数エンドポイント
```

- **Suricata ルール**（[ADR-039 §F.1.A.3](../adr/039-centralized-network-account-edge-layer.md)）で **Plain LDAP 389 は全拒否**、LDAPS 636 のみ許可

### 1.2 Connection Pooling / Timeout

| 項目 | デフォルト | 推奨値 | 事故例 |
|---|---|---|---|
| **Connection Pooling** | OFF | **ON** | OFF だとリクエスト毎に TCP 接続 → 性能悪化 |
| **Connection Timeout** | **無限**（設定なし）| **5-10 秒**（明示設定必須）| デフォルトのままだと AD 障害時に Keycloak Pod ハング → EKS Liveness 失敗 → Pod 再起動ループ |
| **Read Timeout** | **無限**（設定なし）| **10-30 秒**（明示設定必須）| 大規模検索時のハング |

**Keycloak 26 設定例**（Admin Console → User Federation → LDAP → Connection Settings）:

```
Connection URL       = ldaps://ad1.acme.com:636 ldaps://ad2.acme.com:636
Connection Pooling   = ON
Connection Timeout   = 5000   # ms
Read Timeout         = 10000  # ms
```

### 1.3 Bind 認証

```
Bind Type            = simple   # or GSSAPI (Kerberos 時のみ)
Bind DN              = CN=svc-keycloak-bind,OU=ServiceAccounts,DC=acme,DC=com
Bind Credential      = <KMS L2 CMK 経由取得、Vault Reference>
```

- **Bind DN の権限**：**Read-only + Users OU + Groups OU に限定**（[B-LDAP-6](../requirements/hearing-checklist.md)）
- **Bind Credential 管理**：**KMS L2 CMK 暗号化**（[ADR-045](../adr/045-cryptographic-key-management-strategy.md)）、Kubernetes Secret 平文禁止
  - 実装：ExternalSecrets Operator + AWS Secrets Manager
- **Bind Credential ローテ**：**半年〜1 年に 1 回**（[運用ハマりどころ #2](#12-本基盤運用ハマりどころ-top-10)）

---

## 2. Truststore（LDAPS 証明書検証）— ハマりどころ

Keycloak 26 では **Realm Truststore Provider** or **JVM Truststore** の 2 系統。

### 2.1 起動時の Truststore 設定（推奨: 明示）

```bash
kc.sh start \
  --spi-truststore-file-file=/opt/keycloak/conf/truststore.jks \
  --spi-truststore-file-password=<KMS 経由取得> \
  --spi-truststore-file-hostname-verification-policy=STRICT
```

### 2.2 hostname-verification-policy

| 値 | 挙動 | 用途 |
|---|---|---|
| **STRICT** | 証明書 CN / SAN と接続ホスト厳密一致 | **推奨** |
| WILDCARD | `*.customer.com` 許容 | Wildcard 証明書使う顧客のみ |
| ANY | 証明書検証スキップ | **禁止**（MITM 攻撃を招く）|

### 2.3 顧客 AD の CA 証明書登録

```bash
# 顧客 AD の CA 証明書を Truststore に追加
keytool -importcert -alias acme-ad-ca \
  -file customer-ad-ca.crt \
  -keystore /opt/keycloak/conf/truststore.jks \
  -storepass <password>
```

**顧客ごとに異なる CA を管理する必要**があるため、複数顧客対応時は **Truststore を顧客別 or 統合管理** の運用設計が必要（[§10 マルチテナント考慮](#10-マルチテナント考慮本基盤特化)）。

### 2.4 証明書期限監視 — 事故率 No.1

- **期限切れで全 LDAP 接続が一斉断**
- **監視必須**：
  - CloudWatch Alarm で **90 日前 / 30 日前 / 7 日前** 通知
  - 顧客ごとの CA 証明書期限を Grafana ダッシュボード可視化
  - 期限リストを [customer-doc/security.md](customer-doc/security.md) に反映

---

## 3. Edit Mode + Sync 動作 ★最重要設定

### 3.1 Edit Mode

| 値 | 動作 | 用途 |
|---|---|---|
| **READ_ONLY** ✅ | LDAP 変更不可、Keycloak UI で編集不可 | **本基盤の Phase 1 デフォルト** |
| WRITABLE | Keycloak → LDAP 書込む | 高度な運用、責任分担明確化が必要 |
| UNSYNCED | Keycloak DB のみ変更、LDAP に反映しない | **混乱の元、非推奨** |

### 3.2 Import Users

```
Import Users = ON   ★推奨
```

- **ON**：初回ログイン時 LDAP → Keycloak DB キャッシュ、2 回目以降キャッシュ利用（JIT 相当、性能◎）
- **OFF**：毎回 LDAP に問い合わせ（機微データ保管回避、性能△）
- **選択判断**：[ADR-025 §H.3](../adr/025-scim-positioning-and-receive-stance.md) を参照、原則 ON

### 3.3 Sync Registrations

```
Sync Registrations = OFF  ★必須（Read-Only 運用の徹底）
```

**ONに設定すると、ユーザ管理画面から作成したユーザが AD に書き込まれる → 事故**。特にマルチテナントで異なる顧客 AD への意図せぬ書込が発生しうる。

### 3.4 Sync Period 設定

```
Full Sync Period          = 3600  # 1 h 標準
                          = 300   # 5 min 金融/規制業界（B-LDAP-2 確定後）
                          = -1    # 無効

Changed Users Sync Period = 300   # 5 min（差分同期、性能◎）
                          = -1    # 無効
```

**注意**：`Changed Users Sync` は AD の `whenChanged` 属性利用前提。**削除ユーザーは Full Sync でしか検出できない**ケースあり（Tombstone 設定次第）→ [運用ハマりどころ #7](#12-本基盤運用ハマりどころ-top-10)。

### 3.5 Sync 実行時間帯の設計 — L-GD 誤検知回避

- 業務時間中の Full Sync は **AD 側負荷 + Golden LDAP 検知 L-GD-2 誤発火** を招く
- 推奨：業務時間外（深夜 or 週末）に Full Sync 実行
- Changed Users Sync は 5 min 継続で問題なし

---

## 4. LDAP Search 設定（AD の落とし穴集中）

| 項目 | AD 推奨値 | 落とし穴 |
|---|---|---|
| **Users DN** | `OU=Users,DC=customer,DC=com` | 全体 `DC=customer,DC=com` 指定は Domain Controller の Computer Object も検索対象、性能悪化 + 権限膨張 |
| **Username LDAP attribute** | **`sAMAccountName`**（AD 標準）| `userPrincipalName` を選ぶと `@` 含みで [ADR-055 HRD Custom SPI](../adr/055-hrd-implementation-method-selection.md) の識別子先行判定に影響 |
| **RDN LDAP attribute** | **`cn`**（AD）/ `uid`（OpenLDAP）| プロトコル間で異なる |
| **UUID LDAP attribute** | **`objectGUID`**（AD 必須）| デフォルトは `entryUUID`（OpenLDAP 用）→ **AD で未変更だと Sync 毎に全員別ユーザー扱い、大事故**（[落とし穴 #1](#11-ad-特有の落とし穴-top-5)）|
| **Object Classes** | `person, organizationalPerson, user` | `user` 忘れると AD のユーザー取得不可 |
| **Search Scope** | **SUBTREE**（推奨）| ONE_LEVEL だと Sub-OU 内ユーザーが取れない |
| **Pagination Enabled** | **ON**（1000 件超で必須）| OFF だと AD の SizeLimit（デフォルト 1000）で切られる |
| **Batch Size** | 1000 | メモリ使用量とレスポンス時間のバランス |
| **LDAP Filter** | `(&(objectClass=user)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))` | Disabled ユーザー除外の AD bit 演算特殊構文 |

### 4.1 LDAP Filter の使い方（AD の "bitmask 特殊構文"）

`userAccountControl` は bit フィールド:
- `0x2 = 2` → ACCOUNTDISABLE
- `0x10 = 16` → LOCKOUT
- `0x200 = 512` → NORMAL_ACCOUNT

**Disabled ユーザーを除外する Filter**:
```
(&(objectClass=user)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))
```

- `1.2.840.113556.1.4.803` は AD の **LDAP_MATCHING_RULE_BIT_AND** OID
- 直感的でないが、AD で「特定 bit が立ってるかどうか」を判定する唯一の方法

---

## 5. Attribute Mapper — msad-user-account-control が最重要

### 5.1 主要マッパー一覧

| マッパー | 用途 | AD 必須度 |
|---|---|:---:|
| **msad-user-account-control-mapper** | AD の `userAccountControl` bit 検査 → Keycloak `enabled` に反映（**退職者検知の根幹**）| **必須** |
| msad-lds-user-account-control-mapper | AD LDS 用（Standalone AD、稀）| AD LDS 時のみ |
| user-attribute-ldap-mapper | mail / firstName / lastName / phoneNumber 等 | 必須 |
| full-name-ldap-mapper | `cn` → firstName + lastName 分解 | 好み |
| certificate-ldap-mapper | X.509 相互認証 | オプション |
| hardcoded-ldap-attribute-mapper | 固定値付与 | 稀 |

### 5.2 msad-user-account-control-mapper の重要性

**このマッパーが無効だと、AD で無効化された退職ユーザーが Keycloak では有効のまま**。[§C-7.4.8 退職 Deprovision フロー](../requirements/proposal/common/07-implementation-architecture.md#c-748-ldap-顧客の退職時-deprovisionfull-syncscim-代替2026-07-08-追加) が機能しない。

```
Force Password Change = ON  # AD 側で pwdLastSet=0 の時に強制変更要求
```

**Keycloak Admin Console**：User Federation → LDAP → Mappers → Add mapper → **msad-user-account-control-mapper**

### 5.3 標準的な user-attribute-ldap-mapper 例

| Keycloak Attribute | LDAP Attribute (AD) | LDAP Attribute (OpenLDAP) |
|---|---|---|
| email | mail | mail |
| firstName | givenName | givenName |
| lastName | sn | sn |
| phoneNumber | telephoneNumber | telephoneNumber |
| tenant_id（[ADR-018](../adr/018-user-identifier-3layer-emailless.md)）| ハードコード or department | ハードコード |

---

## 6. Group/Role Mapper — Nested Groups の落とし穴

### 6.1 group-ldap-mapper 設定

| 項目 | AD 推奨値 | 落とし穴 |
|---|---|---|
| **Groups DN** | `OU=Groups,DC=customer,DC=com` | 全体指定はビルトイン Group（Domain Admins 等）まで取り込み |
| **Group Name LDAP Attribute** | `cn` | — |
| **Group Object Classes** | `group`（AD）/ `groupOfNames`（OpenLDAP）| プロトコル差異 |
| **Membership LDAP Attribute** | **`member`**（AD 推奨、Reverse Lookup で高速）| `memberOf` + Attribute Type = UID にすると Nested 展開されない |
| **Membership Attribute Type** | **DN**（AD 推奨）| UID にすると LDAP 参照不整合 |
| **User Roles Retrieve Strategy** | **`LOAD_GROUPS_BY_MEMBER_ATTRIBUTE_RECURSIVELY`**（Nested Groups 対応）| デフォルトの `LOAD_GROUPS_BY_MEMBER_ATTRIBUTE` は 1 階層のみ、AD の Nested Groups で失敗 |
| **Preserve Group Inheritance** | **ON**（推奨、階層保持）| OFF だと親子関係喪失 |
| **Mode** | **READ_ONLY** | WRITABLE は運用複雑化 |

### 6.2 Nested Groups の罠

AD の実務では **Group of Groups**（Nested）が多用される:

```
domain-users (親グループ)
  └── department-eng (子)
       └── team-security (孫)
            └── tanaka@customer.com  ← このユーザーは domain-users のメンバー？
```

**`memberOf` は AD の Computed Attribute** で `LDAP_MATCHING_RULE_IN_CHAIN`（1.2.840.113556.1.4.1941）を使わないと **直接メンバーシップしか見えない**。

**Keycloak 26 対策**：`Retrieve Strategy = LOAD_GROUPS_BY_MEMBER_ATTRIBUTE_RECURSIVELY` で **RECURSIVELY モード** 有効化。

### 6.3 Keycloak Role へのマッピング

Group → Realm Role マッピングは以下 2 方式:

1. **Group Mapper で Group 取得** → Keycloak Realm Role Group Mapping で Realm Role 付与
2. **role-ldap-mapper で直接 Role 取得**（LDAP 側に Role 概念がある場合、稀）

**推奨**：方式 1（Group ベースで Role 付与）。理由：Group のほうが AD で管理しやすい。

---

## 7. Password Policy の SoT 決定 — L-4 論点

**[ADR-025 §H.9 L-4](../adr/025-scim-positioning-and-receive-stance.md)** の TBD:

| 選択 | SoT | Keycloak 側 | 判断 |
|---|---|---|:---:|
| **AD 側 SoT**（推奨）| AD Fine-Grained Password Policy | **Keycloak Realm Password Policy は無効化** | ✅ B-LDAP-4 デフォルト |
| Keycloak 側 SoT | Keycloak | Sync Registrations = ON + WRITABLE mode（複雑化）| — |
| 混在 | 両方 | 二重チェック矛盾で混乱 | ❌ 非推奨 |

### 7.1 AD 側 SoT 採用時の Keycloak 設定

- Realm Settings → Password Policy → **すべて空**（Length / Digits / Special Characters 等）
- 認証は AD の `ldap_bind` に完全委譲
- Keycloak 側でのパスワード変更 UI は**無効化**（ユーザーは AD 側 UI で変更）

### 7.2 顧客への説明

> **「本基盤の Password Policy は AD 側 Group Policy に完全委譲します。パスワード変更・強度チェック・履歴管理はすべて AD 側で運用してください。」**

---

## 8. Cache Policy — LDAP 障害時挙動

### 8.1 Cache Policy 選択

```
Cache Policy = DEFAULT / EVICT_DAILY / EVICT_WEEKLY / MAX_LIFESPAN / NO_CACHE
```

| 値 | 挙動 | 用途 |
|---|---|---|
| **DEFAULT** ✅ | Infinispan cache（Keycloak 内部管理）| **推奨、性能◎** |
| EVICT_DAILY | 毎日 cache 失効 | 退職者反映を確実にしたい業界 |
| EVICT_WEEKLY | 毎週 cache 失効 | 変更頻度低い環境 |
| MAX_LIFESPAN | 明示 TTL | 特定要件時 |
| NO_CACHE | LDAP に毎回問い合わせ | **デバッグ用のみ**（性能悪影響甚大）|

### 8.2 LDAP 障害時挙動 — セキュリティ vs 可用性

- **キャッシュ有効期間中**：LDAP 障害でも認証可能（Business Continuity◎）
- **キャッシュ失効後**：認証断（Availability × 低下）

**トレードオフ**：
- 短命キャッシュ（1 h）= **退職者反映早い + LDAP 障害耐性弱**
- 長命キャッシュ（1 日）= **退職者反映遅い + LDAP 障害耐性強**

### 8.3 本基盤の推奨

**`EVICT_DAILY` + Full Sync 5 min（金融）/ 1 h（標準）** の組合わせで両立:

- 日次キャッシュ失効で長期滞留を防ぐ
- Sync 間隔で退職反映を担保
- [ADR-022 Sorry パターン](../adr/022-aws-edge-sorry-control.md) で LDAP 断障害時のユーザー通知

---

## 9. Kerberos SPNEGO 統合（Phase 2 候補）

**[§C-7.3.4.4.C](../requirements/proposal/common/07-implementation-architecture.md)** で Phase 2 候補確定済。Phase 1 では不採用。

### 9.1 Kerberos 設定（Phase 2 実装時のリファレンス）

```
Allow Kerberos authentication = ON
Kerberos Realm                = CUSTOMER.COM
Server Principal              = HTTP/keycloak.basis.example.com@CUSTOMER.COM
KeyTab                        = /opt/keycloak/conf/keytab
Debug                         = OFF   # トラブル時のみ ON
Use Kerberos For Password Authentication = OFF   # LDAP bind と併用時
```

### 9.2 Phase 2 前倒しトリガー

- 大口顧客の必須要件（B-LDAP-5）
- セキュリティ規制で SPNEGO 必須の業界
- Windows ドメイン参加 PC からの seamless SSO 強い要望

### 9.3 実装時の主要依存性

- **KDC への到達性**：Direct Connect / VPN 経由必須（LDAP と同じ経路、[ADR-039 §F.1.A](../adr/039-centralized-network-account-edge-layer.md)）
- **Keytab 発行**：顧客 AD 管理者に SPN 登録依頼が必要
- **Clock Skew**：本基盤 NTP と顧客 AD が **5 分以内同期必須**（Kerberos の制約）

---

## 10. マルチテナント考慮（本基盤特化）

### 10.1 顧客ごとに別の User Federation Provider

```
Realm: main
├── UF Provider #1: ldap-acme
│   ├── Connection URL: ldaps://ad.acme.com:636
│   ├── Priority: 10
│   └── Organization: acme       # [ADR-017](../adr/017-multitenant-l2-single-realm.md) Organizations 紐付け
├── UF Provider #2: ldap-delta
│   ├── Connection URL: ldaps://ad.delta.com:636
│   ├── Priority: 20
│   └── Organization: delta
└── UF Provider #3: entra-beta   # 別顧客は OIDC
    └── Organization: beta
```

### 10.2 Priority 設定 — 検索順序の落とし穴

- **Priority が低いほど先に検索**
- **同一 username が複数 LDAP に存在**すると衝突 → **必ず Organization スコープで絞る**（[ADR-017](../adr/017-multitenant-l2-single-realm.md)）
- **HRD Custom SPI**（[ADR-055](../adr/055-hrd-implementation-method-selection.md)）で先に Organization 特定 → 該当 UF Provider のみ照会するフロー

### 10.3 顧客追加時の運用

- **Terraform / Keycloak Config CLI で IaC 化**必須（GUI 手動運用は N 顧客規模で破綻）
- **秘匿情報（Bind Credential）は Secrets Manager or KMS 経由**、Terraform state に平文禁止
- **Truststore 管理**：顧客追加時に CA 証明書追加、期限監視も自動化

### 10.4 顧客別 UF Provider の IaC 例（keycloak-config-cli）

```yaml
realm: main
userFederationProviders:
  - name: ldap-acme
    providerName: ldap
    priority: 10
    config:
      connectionUrl: [ "ldaps://ad.acme.com:636" ]
      bindDn: [ "CN=svc-keycloak,OU=ServiceAccounts,DC=acme,DC=com" ]
      bindCredential: [ "$(env:LDAP_ACME_BIND_CREDENTIAL)" ]
      usersDn: [ "OU=Users,DC=acme,DC=com" ]
      usernameLDAPAttribute: [ "sAMAccountName" ]
      uuidLDAPAttribute: [ "objectGUID" ]
      editMode: [ "READ_ONLY" ]
      importEnabled: [ "true" ]
      syncRegistrations: [ "false" ]
      fullSyncPeriod: [ "3600" ]
      changedSyncPeriod: [ "300" ]
      cachePolicy: [ "EVICT_DAILY" ]
      connectionTimeout: [ "5000" ]
      readTimeout: [ "10000" ]
      connectionPooling: [ "true" ]
      trustEmail: [ "true" ]
    userFederationMappers:
      - name: msad-user-account-control-mapper
        federationMapperType: msad-user-account-control-mapper
      - name: group-mapper
        federationMapperType: group-ldap-mapper
        config:
          groups.dn: [ "OU=Groups,DC=acme,DC=com" ]
          membership.attribute.type: [ "DN" ]
          membership.ldap.attribute: [ "member" ]
          user.roles.retrieve.strategy: [ "LOAD_GROUPS_BY_MEMBER_ATTRIBUTE_RECURSIVELY" ]
          preserve.group.inheritance: [ "true" ]
```

---

## 11. AD 特有の落とし穴 Top 5

| # | 落とし穴 | 影響 | 対策 |
|---|---|---|---|
| **1** | **UUID LDAP attribute = entryUUID のまま** | Sync 毎に全員別ユーザー扱い、大事故 | **`objectGUID` に変更必須** |
| **2** | **msad-user-account-control-mapper 未設定** | 退職者が Keycloak で有効のまま | マッパー追加必須 |
| **3** | **Membership Attribute = memberOf + UID** | Nested Groups 展開失敗 | **`member` + DN + RECURSIVELY** |
| **4** | **Domain Admin 権限で Bind** | Golden LDAP 攻撃時の被害甚大 | **Read-only + 限定 OU 権限**（[B-LDAP-6](../requirements/hearing-checklist.md)）|
| **5** | **Search Scope が OU 限定なのに Sub-OU が有効** | Sub-OU 内ユーザー Sync 漏れ | **SUBTREE + Users DN を親 OU に** |

---

## 12. 本基盤運用ハマりどころ Top 10

| # | 論点 | チェック内容 | 関連 ADR |
|---|---|---|---|
| **1** | LDAPS 証明書期限管理 | 期限監視 CloudWatch Alarm、90/30/7 日前通知 | [ADR-045](../adr/045-cryptographic-key-management-strategy.md) |
| **2** | Bind Credential のローテ | 半年〜1 年に 1 回、KMS L2 CMK 経由 | [ADR-045](../adr/045-cryptographic-key-management-strategy.md) |
| **3** | Sync 時間帯 | 業務時間中の Full Sync 避ける（LDAP 負荷 + [L-GD-2](../adr/060-auth-protocol-attack-path-residual-tbd.md) 誤検知）| [ADR-060 §C.2.2](../adr/060-auth-protocol-attack-path-residual-tbd.md) |
| **4** | Connection Timeout | 明示 5-10 秒設定、無限ハング防止 | [§1.2](#12-connection-pooling--timeout) |
| **5** | AD 側の SizeLimit（1000 件）超過 | Pagination = ON、Batch Size = 1000 | [§4](#4-ldap-search-設定ad-の落とし穴集中) |
| **6** | Nested Groups の再帰展開 | `LOAD_GROUPS_BY_MEMBER_ATTRIBUTE_RECURSIVELY` | [§6.2](#62-nested-groups-の罠) |
| **7** | 削除ユーザーの Tombstone | Changed Users Sync で検出できない → Full Sync 必須 | [§3.4](#34-sync-period-設定) |
| **8** | 顧客 AD 側の Password Policy 変更 | 変更検知 → Force Password Change のトリガー | [§7](#7-password-policy-の-sot-決定--l-4-論点) |
| **9** | Bind Service Account 権限のドリフト | 定期棚卸（半期）+ [L-GD-3](../adr/060-auth-protocol-attack-path-residual-tbd.md) 検知 | [ADR-060 §C.2.2](../adr/060-auth-protocol-attack-path-residual-tbd.md) |
| **10** | Keycloak バージョンアップ時の LDAP 動作確認 | [ADR-055 §A.7](../adr/055-hrd-implementation-method-selection.md) バージョン追従プロセスに LDAP 動作確認を含める | [ADR-055 §A.7](../adr/055-hrd-implementation-method-selection.md) |
| **11** | **Transient Password Exposure 対策**（2026-07-09 追加）| ヒープダンプ無効化 / kubectl exec 禁止 / Swap 無効化 / APM request body capture 禁止 / debug flag OFF の 5 層防御 | **[ADR-025 §H.6.3](../adr/025-scim-positioning-and-receive-stance.md)** |

---

## 13. 実装チェックリスト（一括参照用）

顧客の LDAP User Federation Provider を新規追加する時の**必須チェック項目**:

### 13.1 事前準備（顧客との協議 / ヒアリング）

- [ ] B-LDAP-1〜7 ヒアリング完了（[hearing-checklist.md](../requirements/hearing-checklist.md)）
- [ ] 顧客 AD ベンダー確認（Microsoft AD / Red Hat DS / OpenLDAP / AD LDS）
- [ ] Bind Service Account の権限確認（Read-only + 限定 OU）
- [ ] ネットワーク経路確定（DX / VPN / VPC Peering）
- [ ] LDAPS 証明書入手（CA 証明書 + 期限）
- [ ] Sync 頻度要件確認（1 h / 5 min / リアルタイム）
- [ ] AD 側 MFA 状況確認（本基盤側追加 MFA 要否）
- [ ] Kerberos SPNEGO 要否確認（Phase 2 判断）

### 13.2 Keycloak 設定

- [ ] Connection URL: `ldaps://` 636 のみ
- [ ] Connection Pooling: ON
- [ ] Connection Timeout: 5000 ms
- [ ] Read Timeout: 10000 ms
- [ ] Bind Type: simple
- [ ] Bind DN + Bind Credential（KMS 経由）
- [ ] Users DN: 限定 OU
- [ ] Username LDAP attribute: sAMAccountName
- [ ] **UUID LDAP attribute: objectGUID** ★
- [ ] Search Scope: SUBTREE
- [ ] Pagination Enabled: ON
- [ ] Edit Mode: READ_ONLY
- [ ] Import Users: ON
- [ ] **Sync Registrations: OFF** ★
- [ ] Full Sync Period: 3600 or 300
- [ ] Changed Users Sync Period: 300
- [ ] Cache Policy: EVICT_DAILY
- [ ] Trust Email: true

### 13.3 Mapper 設定

- [ ] **msad-user-account-control-mapper** 追加 ★
- [ ] user-attribute-ldap-mapper: mail, firstName, lastName, phoneNumber
- [ ] **group-ldap-mapper** 設定 ★
  - [ ] Groups DN: 限定 OU
  - [ ] Membership Attribute Type: DN
  - [ ] Membership LDAP Attribute: member
  - [ ] **Retrieve Strategy: LOAD_GROUPS_BY_MEMBER_ATTRIBUTE_RECURSIVELY** ★
  - [ ] Preserve Group Inheritance: ON

### 13.4 Truststore

- [ ] 顧客 AD の CA 証明書を Truststore に登録
- [ ] hostname-verification-policy: STRICT（or WILDCARD）
- [ ] 証明書期限を CloudWatch Alarm に登録（90/30/7 日前）

### 13.5 Organization 紐付け（マルチテナント）

- [ ] Organization を Realm に作成（`acme` 等）
- [ ] LDAP UF Provider に Organization 紐付け
- [ ] HRD Custom SPI で識別子 → Organization 判定確認

### 13.6 Network Firewall

- [ ] Suricata ルール追加（allow tcp:636 to customer-ad-cidr）
- [ ] VPC Flow Log 有効化
- [ ] DNS Resolver Forwarding rule 追加

### 13.7 セキュリティ・監査

- [ ] Log scrubbing 設定（Password / Bind Credential マスク、[ADR-060 §A](../adr/060-auth-protocol-attack-path-residual-tbd.md)）
- [ ] Golden LDAP 検知シグナル L-GD-1〜L-GD-5 有効化（[ADR-060 §C.2.2](../adr/060-auth-protocol-attack-path-residual-tbd.md)）
- [ ] 本基盤側 MFA 有効化（AD 側 MFA 検証不可のため、[ADR-009](../adr/009-mfa-responsibility-by-idp.md)）
- [ ] **Transient Password Exposure 対策 5 層防御**（**[ADR-025 §H.6.3](../adr/025-scim-positioning-and-receive-stance.md)**、2026-07-09 追加）：
  - [ ] ヒープダンプ無効化（JVM `-XX:-HeapDumpOnOutOfMemoryError`）
  - [ ] kubectl exec 禁止（Pod Security Standard `restricted` + RBAC）
  - [ ] Kubernetes ノード Swap 無効化（`--fail-swap-on=true`）
  - [ ] APM Agent の request body capture 禁止（Datadog / New Relic / Dynatrace マスキング）
  - [ ] 本番 Debug flag OFF（`KC_LOG_LEVEL=INFO`）

### 13.8 動作確認

- [ ] 初回ログイン（JIT でユーザー作成）
- [ ] 2 回目以降ログイン（キャッシュ利用）
- [ ] Full Sync 実行（手動トリガー）
- [ ] 退職者 deprovisioning（AD 側 Disabled → Sync → Keycloak 反映）
- [ ] Nested Groups の再帰展開
- [ ] LDAP 障害シミュレーション（Cache 有効時の挙動）

---

## 14. 参考資料

### Keycloak 公式

- [Keycloak Server Administration Guide - LDAP and Active Directory](https://www.keycloak.org/docs/latest/server_admin/#_ldap)
- [Keycloak Server Administration Guide - User Storage Federation](https://www.keycloak.org/docs/latest/server_admin/#_user-storage-federation)
- [Keycloak Truststore 設定](https://www.keycloak.org/server/keycloak-truststore)
- [keycloak-config-cli（IaC）](https://github.com/adorsys/keycloak-config-cli)

### プロトコル標準

- [RFC 4511 LDAPv3](https://datatracker.ietf.org/doc/html/rfc4511)
- [RFC 4513 LDAPv3 Authentication Methods](https://datatracker.ietf.org/doc/html/rfc4513)
- [RFC 4515 LDAP Search Filters](https://datatracker.ietf.org/doc/html/rfc4515)

### Microsoft AD

- [Microsoft AD LDAPS 設定ガイド](https://learn.microsoft.com/en-us/troubleshoot/windows-server/certificates-and-public-key-infrastructure-pki/enable-ldap-over-ssl-3rd-certification-authority)
- [AD userAccountControl bit フィールド](https://learn.microsoft.com/en-us/troubleshoot/windows-server/active-directory/useraccountcontrol-manipulate-account-properties)
- [LDAP_MATCHING_RULE_BIT_AND (1.2.840.113556.1.4.803)](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-adts/6f81dfaa-4b7a-4f61-8b09-e4ff3a29ec24)
- [LDAP_MATCHING_RULE_IN_CHAIN (1.2.840.113556.1.4.1941)](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-adts/6f81dfaa-4b7a-4f61-8b09-e4ff3a29ec24)（Nested Groups）

### 本プロジェクト内リファレンス

- [ADR-025 §H 顧客 IdP が LDAP(s) の場合の JIT/SCIM 扱い](../adr/025-scim-positioning-and-receive-stance.md)
- [§C-7.3.4.4.B LDAP User Federation Provider 詳細](../requirements/proposal/common/07-implementation-architecture.md)
- [§C-7.4.7 LDAP 顧客の SSO ログイン シーケンス図](../requirements/proposal/common/07-implementation-architecture.md#c-747-ldap-顧客の-sso-ログインbind-pull-モデルimport-users--on2026-07-08-追加)
- [§C-7.4.8 LDAP 顧客の退職時 Deprovision シーケンス図](../requirements/proposal/common/07-implementation-architecture.md#c-748-ldap-顧客の退職時-deprovisionfull-syncscim-代替2026-07-08-追加)
- [ADR-039 v2 §F.1.A LDAP Egress 経路](../adr/039-centralized-network-account-edge-layer.md)
- [ADR-060 §C.2.2 Golden LDAP 検知 L-GD-1〜L-GD-5](../adr/060-auth-protocol-attack-path-residual-tbd.md)
- [hearing-checklist.md B-LDAP-1〜7](../requirements/hearing-checklist.md)

---

**変更履歴**

| 日付 | 内容 |
|---|---|
| 2026-07-08 | 初版作成（[ADR-025 §H](../adr/025-scim-positioning-and-receive-stance.md) 派生、実装時チェックリスト + AD 落とし穴 Top 5 + 運用ハマりどころ Top 10 集約）|
| 2026-07-09 | §12 に Transient Password Exposure 対策（項番 11、5 層防御）追加 + §13.7 実装チェックリストに 5 層防御項目追加（[ADR-025 §H.6.3](../adr/025-scim-positioning-and-receive-stance.md) 波及）|
