# ServiceNow SSO 既存ユーザーリンク手順ガイド

> **目的**: 既存 ServiceNow ローカルユーザーを SSO 移行する際に、**過去履歴を壊さずに認証だけ SSO 化する**ための具体的な手順・設定・テスト観点を集約する reference doc。
> **対象読者**: プラットフォーム設計者 / ServiceNow 管理者 / 移行実施担当者
> **位置付け**: [ADR-023 ServiceNow SP 連携設計](../adr/023-servicenow-sp-integration.md) の **実装手順の裏どり**。[§FR-2.4 外部 SP（SaaS）連携](../requirements/proposal/fr/02-federation.md) からの参照先
> **関連**:
> - [ADR-023 ServiceNow SP 連携設計](../adr/023-servicenow-sp-integration.md)
> - [ADR-019 既存システムからの移行戦略](../adr/019-existing-system-migration.md)
> - [ADR-054 ID 統合戦略](../adr/054-id-integration-strategy.md)
> - [ADR-055 HRD 実装方式選定](../adr/055-hrd-implementation-method-selection.md)（`<tenant>-<userid>` 形式）
> - [§FR-2.4](../requirements/proposal/fr/02-federation.md) / [§FR-7.4.10](../requirements/proposal/fr/07-user.md)

---

## 目次

1. [ServiceNow のデータモデルと sys_id](#1-servicenow-のデータモデルと-sys_id)
2. [絶対に避けるべきアンチパターン](#2-絶対に避けるべきアンチパターン)
3. [推奨アプローチ: Matching Field でリンク](#3-推奨アプローチ-matching-field-でリンク)
4. [Matching Field の選定](#4-matching-field-の選定)
5. [ServiceNow SSO 設定手順](#5-servicenow-sso-設定手順)
6. [並走期間の運用](#6-並走期間の運用)
7. [重複 sys_user の統合作業](#7-重複-sys_user-の統合作業)
8. [属性の継続同期（SCIM）](#8-属性の継続同期scim)
9. [Break Glass 管理者の設定](#9-break-glass-管理者の設定)
10. [退職者データの取扱い（APPI / GDPR）](#10-退職者データの取扱いappi--gdpr)
11. [テスト手順](#11-テスト手順)
12. [参考文献](#12-参考文献)

---

## 1. ServiceNow のデータモデルと sys_id

### sys_user と sys_id の関係

ServiceNow のすべてのユーザーは `sys_user` テーブルに 1 レコード = 1 UUID (`sys_id`) で管理される:

```
sys_user (ユーザマスタ)
├── sys_id: "abc-123-xyz"  ★不変の UUID、主キー
├── user_name: "yamada.t"   Login 用 (慣例的にユニーク)
├── email: "yamada@company.com"
├── employee_number: "EMP-001234"
├── first_name / last_name / active / etc.
└── sso_source: "SAML2Update1"  ← per-user SSO 経路制御用
```

### sys_id を参照する主要テーブル (履歴系)

ServiceNow のあらゆる業務レコードが `sys_user.sys_id` を外部キーとして持ちます:

| 参照元テーブル | フィールド | 意味 |
|---|---|---|
| `incident` | `caller_id` / `assigned_to` / `opened_by` / `resolved_by` / `closed_by` | インシデント関係者 |
| `problem` | `assigned_to` / `opened_by` / etc. | 問題管理関係者 |
| `change_request` | `requested_by` / `assigned_to` / `assignment_group` | 変更管理 |
| `sc_request` / `sc_req_item` | `requested_for` / `opened_by` | サービスリクエスト |
| `task` | `assigned_to` / `opened_by` | タスク全般 |
| `sysapproval_approver` | `approver` / `source_table` | 承認ワークフロー |
| `sys_journal_field` | `sys_created_by` | Journal (履歴コメント) |
| `sys_audit` | `user` | 監査ログ |
| `sys_user_grmember` | `user` | グループ所属 |
| `sys_user_delegate` | `delegate` / `user` | 代理承認設定 |
| `cmn_notif_message` | `user` | 通知配信ログ |

→ **sys_id が消える = 上記全テーブルの参照が「不明ユーザ」化 = 業務不能**

### なぜ SSO が sys_id を壊さないか

ServiceNow の SSO 動作:

1. SAML/OIDC アサーションが到着
2. 設定された **matching field** で `sys_user` を検索
3. **既存 sys_user が見つかったらそのまま利用**（sys_id 不変）
4. 見つからなければ設定次第で JIT 作成 or 拒否

→ **既存ユーザーを削除せず、matching field で紐付けるだけ**で SSO 移行が完了する仕組み。

---

## 2. 絶対に避けるべきアンチパターン

### アンチパターン 1: 既存ユーザーを削除して JIT で作り直す

```
[Before]
sys_user{sys_id="abc-123", user_name="yamada.t"}
incident{caller_id="abc-123"} ← 過去 3 年分のインシデント

[アンチパターン実行後]
sys_user 削除 → JIT で新規作成
sys_user{sys_id="def-456-new", user_name="yamada.t"}  ★sys_id が変わる
incident{caller_id="abc-123"} ← 参照先消失、「Unknown Caller」表示
```

**影響範囲**:
- インシデント / タスク / 承認履歴すべてで「不明ユーザ」表示
- 監査ログ (`sys_audit`) の caller / operator が破綻
- 承認ワークフロー中の履歴が読めなくなる
- BI / レポート (Performance Analytics) が壊れる
- SLA / OLA 履歴の集計対象から消える
- 部下 - 上司関係 (`manager` フィールド) が切断

### アンチパターン 2: matching field を後から変更

```
Day 1: matching field = user_name で運用開始
       → 既存全ユーザにリンク成功
Day N: 「employee_number に変更しよう」
       → user_name != employee_number のユーザで sys_user が新規作成される
       → 実質上のアンチパターン 1 と同等
```

**教訓**: **matching field は移行前に確定し、以後変更しない**（変更する場合は sys_user 統合が必要）。

### アンチパターン 3: 認証データ（PW ハッシュ）は消したが sys_user は残した状態で SSO 未設定

```
Day 1: 「移行準備」で sys_user.password を NULL 化
Day 2: SSO 設定完了前にユーザがログイン試行
       → password 認証失敗、SSO 未有効、ログイン不能
```

**教訓**: **PW 無効化と SSO 有効化は同一メンテウィンドウで実施**、隙間を作らない。

---

## 3. 推奨アプローチ: Matching Field でリンク

### 全体フロー

```
[本基盤 Keycloak (IdP)]                    [ServiceNow (SP)]
                                              │
     Login 開始                                │
        ↓                                     │
   Keycloak が SAML Assertion 生成             │
        ↓                                     │
   NameID = "acme-EMP-001234"                 │
   attribute:                                  │
      employee_number = "EMP-001234"          │
      email = "yamada@company.com"            │
      first_name = "Taro"                     │
      last_name = "Yamada"                    │
        ↓                                     ▼
   POST /navpage.do (SAML Response) ────────► SSO Plugin
                                              │
                                              │ matching field = employee_number
                                              │
                                              │ SELECT * FROM sys_user
                                              │  WHERE employee_number = 'EMP-001234'
                                              │        AND active = true
                                              │
                                              │ Result: sys_id="abc-123-xyz"
                                              │        (既存ユーザ！)
                                              │
                                              │ ★ sys_id 不変でセッション作成
                                              ▼
                                          過去履歴すべて閲覧可能
```

### 前提条件

- ServiceNow の **Multi-Provider SSO Plugin** 有効化（`com.snc.integration.sso.multi`）
- Keycloak (Broker Realm) が SAML Assertion に matching field を含めて送出可能
- 既存 sys_user の matching field 値が **一意 + 空欄なし**

---

## 4. Matching Field の選定

### 4 候補の比較

| 候補 | 安定性 | 一意性 | 埋込率 | 変更頻度 | 推奨度 |
|---|---|---|---|---|---|
| **`employee_number`** | ★★★★★（社員番号は不変）| ★★★★★（HR 側で厳格に一意）| △（未入力の顧客あり）| ★★★★★（変わらない）| **★★★★★ 第一推奨** |
| `user_name` | ★★★★（変更されうる）| ★★★★（慣例的に unique）| ★★★★★（必須項目）| ★★★（結婚 / 部署異動で変更事例）| ★★★★ |
| `email` | ★★★（変更されうる）| ★★★（本来一意だが例外あり）| ★★★★（メアド不可対応で空欄あり）| ★★（婚姻 / 部署異動 / ドメイン変更）| ★★ |
| **カスタム属性** (`u_keycloak_sub`)| ★★★★★（内部管理）| ★★★★★（Keycloak 側 `sub` = UUID）| SSO 移行時に投入 | ★★★★★ | ★★★★（新規設計向け）|

### 判断フロー

```
Q1: employee_number は全ユーザに埋め込まれているか?
    ├── Yes → employee_number 採用
    └── No → Q2 へ

Q2: user_name は「顧客独自 ID / 社員番号」形式で埋まっているか?
    ├── Yes → user_name 採用（B-SN-5 で確認済み）
    └── No → Q3 へ

Q3: 新規カスタム属性を追加してよいか?
    ├── Yes → u_keycloak_sub カスタム属性を新設、移行時に一括埋め込み
    └── No → email 採用（変更発生時に運用対応）
```

### 本基盤の推奨

本基盤の識別子形式は `<tenant>-<userid>`（ADR-055）。**userid 部分 = 社員番号相当**なので、**matching field = `employee_number`** が第一推奨:

```
Keycloak 側 SAML Assertion:
  NameID: "acme-EMP-001234"（全体、そのまま送出）
  attribute employee_number: "EMP-001234"（userid 部分のみ抽出）

ServiceNow 側:
  matching field = "employee_number"
  → sys_user{employee_number="EMP-001234"} を検索・リンク
```

---

## 5. ServiceNow SSO 設定手順

### Step 1: Multi-Provider SSO Plugin 有効化

```
System Definition > Plugins
検索: "Multi-Provider SSO Plugin (com.snc.integration.sso.multi)"
Activate/Install
```

システムプロパティ:
```
glide.authenticate.multisso.enabled = true
glide.authenticate.sso.redirect.idp = <IdP sys_id>
```

### Step 2: SAML 2 Update1 IdP 登録

```
Multi-Provider SSO > Identity Providers > New > SAML
```

主要フィールド:

| フィールド | 値 |
|---|---|
| Name | `Keycloak Broker` |
| Identity Provider URL | `https://auth.basis.example.com/realms/broker` |
| Identity Provider's AuthnRequest | `https://auth.basis.example.com/realms/broker/protocol/saml` |
| Identity Provider's SingleLogoutRequest | `https://auth.basis.example.com/realms/broker/protocol/saml` |
| ServiceNow Homepage | `https://<instance>.service-now.com/navpage.do` |
| Entity ID / Issuer | `https://<instance>.service-now.com` |
| NameID Policy | `urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified` |
| **User Field** | **`employee_number`**（matching field、★重要）|
| **Auto Provisioning User** | **`true`**（JIT 作成、SN-only の新規は JIT）|
| Create AuthnRequests Signed | `true`（署名検証）|
| Sign LogoutRequest | `true` |
| Sign LogoutResponse | `true` |
| Signing/Encryption Key Alias | `keycloak-broker-cert` |

### Step 3: 属性マッピング

Keycloak SAML Assertion → sys_user カラム対応:

| SAML Attribute | sys_user カラム | 用途 |
|---|---|---|
| `employee_number` | `employee_number` | **matching field（PK）** |
| `email` | `email` | 通知配信 |
| `first_name` | `first_name` | 表示名 |
| `last_name` | `last_name` | 表示名 |
| `department` | `department` | 部署（Reference Field）|
| `manager` | `manager` | 上長（Reference Field）|
| `role` | `roles`（Groups 経由）| ロール反映 |

ServiceNow 側:
```
Multi-Provider SSO > Identity Providers > <IdP> > SAML2 Update1 Properties
> Attribute Mapping Panel
```

### Step 4: per-user sso_source 設定

既存ユーザに一括で SSO 経路指定:

```sql
UPDATE sys_user 
SET sso_source = '<IdP sys_id>' 
WHERE active = true 
  AND employee_number IS NOT NULL
  -- Break Glass 管理者は除外
  AND user_name NOT IN ('sn.breakglass.1', 'sn.breakglass.2');
```

または Background Script:
```javascript
var gr = new GlideRecord('sys_user');
gr.addQuery('active', true);
gr.addNotNullQuery('employee_number');
gr.addQuery('user_name', 'NOT IN', 'sn.breakglass.1,sn.breakglass.2');
gr.query();
while (gr.next()) {
    gr.sso_source = '<IdP sys_id>';
    gr.update();
}
```

### Step 5: SSO 有効化前の Dry Run

**必ず並走モードでスタート**（PW auth も残したまま SSO 有効化）:

```
glide.authenticate.sso.mandatory = false  ★重要（強制 SSO はしない）
```

一部の Pilot ユーザで動作確認後、段階的にロールアウト。

---

## 6. 並走期間の運用

### 段階的移行フロー

```
[Phase 6-A: Pilot 期間 (2-4 週間)]
  - Pilot 10-20 名にのみ sso_source 設定
  - SSO 動作確認、履歴表示確認、権限確認
  - 問題発見 → 巻き戻し可能

[Phase 6-B: 全社 SSO 有効化 (1-2 ヶ月)]
  - 全ユーザに sso_source 設定
  - password auth も継続（フェイルオーバー用）
  - ユーザは主に SSO でログイン
  - 未 SSO ログインユーザ (login_history でトラッキング) にフォローアップ

[Phase 6-C: password auth 段階無効化 (1 ヶ月)]
  - login_history で全ユーザが SSO ログイン成功したか確認
  - 全員 SSO ログイン確認後、一般ユーザの password_needs_reset = true
  - Break Glass 管理者のみ password auth 継続

[Phase 6-D: Password Login Page 無効化 (完了)]
  - glide.authenticate.sso.mandatory = true
  - ローカル PW 認証を完全停止（Break Glass は URL パラメータで例外的にアクセス）
```

### 未 SSO ログイン検出

Login 履歴で SSO 未経由ユーザを特定:

```javascript
// Business Rule: sys_user_session on before-insert
var gr = new GlideRecord('sys_user');
gr.get(current.user);
if (current.login_type != 'sso') {
    gs.info('Non-SSO login: ' + gr.user_name);
}
```

集計:
```
Reports > Sessions where login_type != 'sso' 
         AND active = true 
         AND user.sso_source IS NOT NULL
```

---

## 7. 重複 sys_user の統合作業

### 発生パターン

- 部署異動時に別 sys_user を作成
- ContractOr / Employee の切替時に新規作成
- 誤操作で複数登録
- Import 時のマッチング失敗

### 検出方法

```sql
-- 同じ employee_number で複数存在
SELECT employee_number, COUNT(*) 
FROM sys_user 
WHERE employee_number IS NOT NULL
GROUP BY employee_number 
HAVING COUNT(*) > 1;

-- 同じ email で複数存在
SELECT email, COUNT(*) 
FROM sys_user 
WHERE email IS NOT NULL
GROUP BY email 
HAVING COUNT(*) > 1;
```

### 統合手順

**優先順位付け**:
1. Retain（残す）: 履歴が多い方 / active な方 / employee_number 埋込済み
2. Merge（統合先）: 履歴が少ない方 / inactive な方

**統合スクリプト例**:

```javascript
// oldSysId のすべての参照を newSysId に付け替え
var oldSysId = 'abc-old-uuid';
var newSysId = 'def-new-uuid';

var affectedTables = [
    'incident', 'problem', 'change_request', 
    'sc_request', 'sc_req_item', 'task',
    'sysapproval_approver', 'sys_journal_field', 
    'sys_audit', 'sys_user_grmember'
];

affectedTables.forEach(function(tableName) {
    ['caller_id', 'assigned_to', 'opened_by', 'requested_for', 'approver', 'user'].forEach(function(field) {
        var gr = new GlideRecord(tableName);
        if (gr.isValidField(field)) {
            gr.addQuery(field, oldSysId);
            gr.query();
            while (gr.next()) {
                gr[field] = newSysId;
                gr.update();
            }
        }
    });
});

// 旧 sys_user を inactive 化（削除ではなく）
var oldUser = new GlideRecord('sys_user');
oldUser.get(oldSysId);
oldUser.active = false;
oldUser.first_name = '(Merged into ' + newSysId + ')';
oldUser.update();
```

**注意**: 標準機能の `sys_user.merge` は稼働中は非推奨。上記のようなカスタムスクリプトで慎重に実施。

---

## 8. 属性の継続同期（SCIM）

### なぜ SCIM が必要か

SSO だけでは **認証時のみ**属性更新 = 部署異動 / 上長変更 / 権限変更 の反映が遅延。SCIM Push で継続同期:

```
[Keycloak (IdP)]                     [ServiceNow]
  Realm Event Listener                  │
   User 更新 (department, manager 等)    │
       ↓                                │
   SCIM Client SPI                      │
   PATCH /scim/v2/Users/{externalId}    │
       ─────────────────────────────►   sys_user 属性更新
```

### ServiceNow 側の SCIM Endpoint

```
POST   /scim/v2/Users     ユーザ作成
GET    /scim/v2/Users/{id} 参照
PATCH  /scim/v2/Users/{id} 属性更新
PUT    /scim/v2/Users/{id} 完全置換
DELETE /scim/v2/Users/{id} 論理削除 (active=false)
```

Plugin: `sn_scim_provisioning`

### 制約事項（重要）

- **⚠ 2025-11 KB2599716**: Microsoft Entra 経由の SCIM Provisioning は ServiceNow が非サポート公表
- Keycloak → ServiceNow SCIM Push は Custom SPI で自前実装（[ADR-023 パターン C の SI 保証外前提を継承](../adr/023-servicenow-sp-integration.md)）

### 推奨採用シーン

| シーン | 採用 |
|---|---|
| Phase 1（PoC / 初期）| ❌ 実装せず、JIT のみ |
| Phase 2（属性変更頻度高）| ✅ Custom SPI で SCIM Push 実装 |
| Phase 2（変更頻度低）| △ Custom Event Listener + REST 呼出でも代替可能 |

---

## 9. Break Glass 管理者の設定

### 目的

- SSO 障害時の緊急ログイン経路
- Keycloak / IdP メンテ時の運用継続
- 監査対応の証跡確保

### 業界標準構成

| 項目 | 推奨 |
|---|---|
| **人数** | 2-3 名 |
| **要件** | ローカル PW + Hardware MFA (YubiKey) |
| **sso_source** | 空欄（SSO 経由不可）|
| **アクセス制限** | 特定 IP のみ (Company Network) |
| **監査ログ** | 全操作を SIEM 転送 + 別チーム監視 |
| **PW ローテ** | 90 日 or アクセス発生時 |
| **命名規則** | `sn.breakglass.1`, `sn.breakglass.2`, ... |

### 設定手順

```javascript
// Break Glass ユーザ作成
var bg = new GlideRecord('sys_user');
bg.initialize();
bg.user_name = 'sn.breakglass.1';
bg.first_name = 'Break Glass';
bg.last_name = 'Admin 1';
bg.email = 'breakglass@company.com';
bg.active = true;
bg.locked_out = false;
// sso_source は空欄のまま = SSO 経由不可
bg.roles = 'admin,security_admin';
bg.insert();
```

システムプロパティ:
```
# Break Glass アクセス URL
glide.login.local_login_url = /login_locate.do?local_login=true

# IP 制限（Access Control で設定）
glide.security.ip_range.breakglass = 10.0.0.0/24, 192.168.1.0/24
```

### 運用ルール

- 使用時は Change Request 起票必須
- 使用後 24h 以内に PW ローテ
- 全操作を Post-mortem レビュー対象化

---

## 10. 退職者データの取扱い（APPI / GDPR）

### 3 つの選択肢

| 選択肢 | 内容 | 履歴影響 | 適用場面 |
|---|---|---|---|
| **A. 残置 + inactive 化** | `sys_user.active = false`、レコード保持 | ✅ 履歴保持 | **業界標準・第一推奨** |
| **B. 一部匿名化** | 個人特定情報のみ削除、履歴は残す | ✅ 履歴保持 | APPI Article 30 / GDPR RTBF 発動時 |
| **C. 完全削除** | sys_user 削除 → sys_id 参照が Orphan 化 | ❌ 履歴壊れる | ❌ 通常は非推奨 |

### 選択肢 B: 匿名化スクリプト例

```javascript
// APPI Article 30 / GDPR RTBF (Right to be Forgotten) 対応
var sysId = 'target-user-sys-id';

var gr = new GlideRecord('sys_user');
gr.get(sysId);
if (gr.isValidRecord()) {
    var anonPrefix = '[Anonymized-' + sysId.substring(0, 6) + ']';
    gr.first_name = anonPrefix;
    gr.last_name = '';
    gr.email = '';
    gr.phone = '';
    gr.mobile_phone = '';
    gr.employee_number = '';
    gr.title = '';
    gr.location = '';
    gr.department = '';
    gr.manager = '';
    // Note: user_name / sys_id は残す（履歴の外部キー参照維持のため）
    gr.active = false;
    gr.locked_out = true;
    gr.notes = 'Anonymized per APPI Article 30 request on ' + new GlideDateTime();
    gr.update();
}
```

**重要**:
- **sys_id は残す**（インシデント等の履歴参照維持）
- 表示名は `[Anonymized-xxxxxx]` 等の非可逆識別子
- 完全削除は原則行わない（履歴壊れる）

### 対応フロー

```
1. データ主体権利申請 (Data Subject Rights) 受付
   → ADR-048 Data Portability / Right to Erasure と連動
2. 法務・コンプラ承認
3. 対象 sys_user 特定
4. 匿名化スクリプト実行
5. 実施記録を Audit Log に保存
6. 申請者に完了通知
```

詳細は [ADR-048 Data Portability + Cryptographic Erasure](../adr/048-data-portability-cryptographic-erasure.md) 参照。

---

## 11. テスト手順

### Test 1: 既存ユーザーの SSO リンク確認

```
[準備]
1. テストユーザー選定: existing_user_1 (employee_number = "EMP-9999")
2. 過去履歴確認: incident.caller_id = existing_user_1.sys_id が 10件以上
3. sso_source を IdP に設定

[実行]
4. Keycloak にログイン (acme-EMP-9999)
5. ServiceNow へリダイレクト
6. SAML Assertion 送出、SSO 経由でセッション成立

[検証]
7. My Profile 画面で sys_id 確認 → 変わっていないこと
8. My Incidents 画面で過去 10 件が表示されること
9. Approval 履歴が引き継がれていること
10. Group Membership が保持されていること
```

### Test 2: 属性更新の反映確認

```
1. Keycloak 側で department を "Engineering" → "Sales" に変更
2. SCIM Push が発火（Event Listener SPI）
3. ServiceNow sys_user.department が更新される
4. 未更新の場合は SCIM Log で診断
```

### Test 3: Break Glass ログイン確認

```
1. SSO を意図的に無効化（Test IdP を Disable）
2. sn.breakglass.1 でローカルログイン試行
3. Hardware MFA 突破
4. Admin 権限で操作可能
5. 監査ログに Break Glass 使用記録
6. SIEM に通知が届く
```

### Test 4: 重複 sys_user 統合の Regression Test

```
1. 統合前: user_A (sys_id="abc", incidents=15件)
          user_B (sys_id="def", incidents=5件、こちらを Merge 対象)
2. 統合スクリプト実行
3. 検証:
   - user_A.sys_id 変わらないこと
   - user_A の incidents カウント = 20件
   - user_B は inactive、first_name に "Merged into abc" 表示
   - Reports で user_B が集計外に
```

### Test 5: 履歴の非破壊確認（Regression）

- 過去 3 年分のインシデント一覧表示 → ユーザ表示すべて正常
- Performance Analytics ダッシュボード → SLA 集計正常
- 通知 (email) 配信 → 対象ユーザーに届く
- Delegation (代理承認) → 代理関係維持

---

## 12. 参考文献

### ServiceNow 公式

- [Multi-Provider SSO Plugin](https://docs.servicenow.com/bundle/washingtondc-platform-security/page/administer/security/concept/c_MultipleProviderSSO.html)
- [SAML 2 Single Sign-On](https://docs.servicenow.com/bundle/washingtondc-platform-security/page/integrate/saml/concept/c_SAML20WebBrowserSSO.html)
- [User Provisioning](https://docs.servicenow.com/bundle/washingtondc-platform-security/page/administer/security/concept/c_UserProvisioning.html)
- [SCIM Provisioning Plugin](https://docs.servicenow.com/bundle/washingtondc-platform-administration/page/administer/scim/concept/scim-landing-page.html)
- KB2599716: Microsoft Entra 経由 SCIM 非サポート表明

### 本プロジェクト内 関連 doc

- [ADR-023 ServiceNow SP 連携設計](../adr/023-servicenow-sp-integration.md) — 4 パターン比較 + SSO ローカル残置 (④) 選択肢
- [ADR-019 既存システムからの移行戦略](../adr/019-existing-system-migration.md) — User Storage SPI キャッシュ移行
- [ADR-054 ID 統合戦略](../adr/054-id-integration-strategy.md) — 人事 DB SoT + 3 階層識別子モデル
- [ADR-055 HRD 実装方式選定](../adr/055-hrd-implementation-method-selection.md) — `<tenant>-<userid>` 形式（本手順の matching field 前提）
- [ADR-048 Data Portability / Cryptographic Erasure](../adr/048-data-portability-cryptographic-erasure.md) — 退職者データ匿名化フロー
- [§FR-2.4 外部 SP 連携](../requirements/proposal/fr/02-federation.md) — 要件定義本体
- [§FR-7.4.10 ServiceNow ユーザプロビジョニング](../requirements/proposal/fr/07-user.md)

### 業界事例 / 記事

- [Okta - ServiceNow SAML Integration Guide](https://help.okta.com/en-us/content/topics/apps/apps_add_servicenow_saml.htm)
- [Auth0 - ServiceNow Integration](https://auth0.com/docs/customize/integrations/marketplace/servicenow-social-connection)
- [ServiceNow Community - Handling User Migration to SSO](https://community.servicenow.com/community?id=community_question&sys_id=SSO_migration_best_practices)

---

## 改訂履歴

- 2026-07-03: 初版作成。ServiceNow SSO 既存ユーザリンクの具体的手順を集約。sys_id 保全の重要性 + 3 アンチパターン + Matching Field 選定フロー + 5 Step 設定手順 + 並走期間 4 Phase + 重複統合スクリプト + SCIM 属性同期 + Break Glass 設定 + APPI/GDPR 対応 (匿名化) + 5 Test シナリオ を体系化。ADR-023 の実装手順裏どりとして機能
