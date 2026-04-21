# Keycloak クレームマッピング設定ガイド

**目的**: Keycloak 発行の Access Token に Cognito 側と同じクレーム
（`tenant_id` / `roles` / `email`）を載せ、**同じ Lambda Authorizer + Backend** で
認可判定できるようにする。

**前提**: Admin Console にアクセス可能。`auth-poc` Realm, `auth-poc-spa` Client 作成済み。

---

## 全体像

```
[Keycloak User]
  attributes.tenant_id = "acme-corp"
  realm roles = ["manager"]
  email = "bob@acme.com"
          │
          ▼  Protocol Mapper 3つで Access Token に注入
[Access Token]
  {
    "sub": "...",
    "email": "bob@acme.com",
    "tenant_id": "acme-corp",
    "roles": "manager",
    "iss": "http://...elb.../realms/auth-poc",
    "aud": "account"
  }
          │
          ▼
[Lambda Authorizer] - ALLOWED_ISSUERS に Keycloak issuer を追加済
          │
          ▼
[Backend Lambda] - 同じ認可ロジックが動く
```

---

## 1. Realm 属性スキーマに tenant_id を追加（任意）

ユーザー属性は Keycloak 26 ではデフォルトで制限があるため、Unmanaged 属性を許可するか
事前に宣言する。今回は手軽さ優先で Unmanaged 属性を ENABLED にする。

### 手順

1. Admin Console → 左メニュー **Realm settings**
2. **General** タブ → **Unmanaged Attributes** を **Enabled** に変更
3. **Save**

---

## 2. ロール（Realm Role）を作成

### 手順

1. Admin Console → 左メニュー **Realm roles**
2. **Create role**
3. 以下3つを作成:
   - `employee`
   - `manager`
   - `admin`

---

## 3. Protocol Mapper を auth-poc-spa Client に追加

Access Token にトップレベルクレーム `tenant_id` / `roles` / `email` を載せる。

### 3.1 tenant_id マッパー（User Attribute → claim）

1. Admin Console → **Clients** → `auth-poc-spa` → **Client scopes** タブ
2. `auth-poc-spa-dedicated` をクリック（専用スコープ）
3. **Add mapper** → **By configuration** → **User Attribute**
4. 以下を入力:
   | 項目 | 値 |
   |------|-----|
   | Name | `tenant_id` |
   | User Attribute | `tenant_id` |
   | Token Claim Name | `tenant_id` |
   | Claim JSON Type | `String` |
   | Add to ID token | **ON** |
   | Add to access token | **ON** |
   | Add to userinfo | OFF |
   | Multivalued | OFF |
5. **Save**

### 3.2 roles マッパー（Realm Role → claim, カンマ区切り）

Cognito と同じ `roles` カンマ区切り文字列を作るため **Script Mapper** を使う。
ただし Keycloak 26 の start-dev ではデフォルトで Script Mapper が無効のため、
代わりに **User Realm Role** マッパーで配列として出力し、Authorizer 側で配列対応する。

（Authorizer 側はこの後の修正で `roles` が配列でも文字列でも扱えるようにする）

1. 同じ **Mappers** 画面 → **Add mapper** → **By configuration** → **User Realm Role**
2. 以下を入力:
   | 項目 | 値 |
   |------|-----|
   | Name | `roles` |
   | Realm Role prefix | (空欄) |
   | Multivalued | **ON** |
   | Token Claim Name | `roles` |
   | Claim JSON Type | `String` |
   | Add to ID token | **ON** |
   | Add to access token | **ON** |
   | Add to userinfo | OFF |
3. **Save**

### 3.3 email マッパー

Keycloak は標準で `email` を含むが、Access Token に明示的に載せておく。

1. 通常は `email` Client Scope が自動で付く。確認のみで OK。
2. 無ければ **Add mapper** → **By configuration** → **User Property**
   | 項目 | 値 |
   |------|-----|
   | Name | `email` |
   | Property | `email` |
   | Token Claim Name | `email` |
   | Add to access token | **ON** |
3. **Save**

---

## 4. テストユーザーを作成

### ユーザー一覧（Phase 8 と同じ）

| Username | Email           | tenant_id  | Role     |
| -------- | --------------- | ---------- | -------- |
| alice-kc | alice@acme.com  | acme-corp  | employee |
| bob-kc   | bob@acme.com    | acme-corp  | manager  |
| carol-kc | carol@acme.com  | acme-corp  | admin    |
| dave-kc  | dave@globex.com | globex-inc | manager  |

※ Cognito ユーザー（alice@acme.com 等）とメールが被っても Keycloak 上は別ユーザーとして扱われる。
区別のため username に `-kc` サフィックスを付けておくと便利。

### 作成手順（各ユーザー共通）

1. Admin Console → **Users** → **Add user**
2. Username / Email を入力、**Email verified** を **ON**、**Create**
3. 作成後のユーザー画面 → **Credentials** タブ → **Set password**
   - Password: `TestPass1!`
   - Temporary: **OFF**
   - **Save password** ここまで
4. **Attributes** タブ → key: `tenant_id`、value: `acme-corp` 等 → **Save**
5. **Role mapping** タブ → **Assign role** → Realm role から `manager` 等を選択 → **Assign**

---

## 5. 動作確認（JWT を見る）

### 5.1 Keycloak Admin Console で Token を試す方法

- **Clients** → `auth-poc-spa` → **Client scopes** → **Evaluate** タブ
- User: `bob-kc` を選択 → **Generated access token** を確認
- 以下があれば成功:
  ```json
  {
    "email": "bob@acme.com",
    "tenant_id": "acme-corp",
    "roles": ["manager"]
  }
  ```

### 5.2 SPA (app-keycloak) 経由の確認

`.env` に Keycloak の authority / client_id / API エンドポイント（Cognito と同じ Backend）
を設定して起動 → ログイン → API Tester で Phase 8 と同じクイックボタンを実行。

---

## 6. トラブルシュート

### tenant_id クレームが載らない

- Realm settings → Unmanaged Attributes が Disabled のままだとユーザー属性が保存できない
- Mapper 設定の `Add to access token` が OFF になっていないか
- User Attribute 名と Token Claim Name が一致しているか

### roles クレームが空

- User Realm Role マッパーで Multivalued が ON になっているか
- ユーザーに Role が割り当てられているか（Role mapping タブ）

### Authorizer で Unknown issuer エラー

- Lambda Authorizer の環境変数 `KEYCLOAK_ISSUER` を設定済か
- realm URL が HTTPS になっていないか確認（PoC は HTTP）
