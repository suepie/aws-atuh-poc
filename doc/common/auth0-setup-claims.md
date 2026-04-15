# Auth0 設定ガイド: カスタムクレーム（tenant_id / role）の注入

**目的**: Auth0 経由でログインしたユーザーのIDトークンに `tenant_id` と `role`
クレームを載せ、Cognito の attribute_mapping 経由で Cognito カスタム属性
（`custom:tenant_id` / `custom:roles`）に反映させる。

---

## 全体の流れ

```
[Auth0 User]
   ├─ app_metadata.tenant_id = "acme-corp"
   └─ app_metadata.role      = "manager"
                │
                ▼  ログイン時に Post Login Action が実行される
[Auth0 Action]
   api.idToken.setCustomClaim("tenant_id", ...)
   api.idToken.setCustomClaim("role", ...)
                │
                ▼  Auth0 IDトークンにカスタムクレームが載る
[Cognito OIDC Federation]
   attribute_mapping:
     custom:tenant_id  ← tenant_id
     custom:roles      ← role
                │
                ▼  Cognito User Pool のカスタム属性に書き込まれる
[Cognito Pre Token Lambda]
   トップレベルクレーム tenant_id / roles を注入
                │
                ▼
[Cognito IDトークン]
   {
     "sub": "...",
     "email": "...",
     "tenant_id": "acme-corp",
     "roles": "manager",
     "cognito:groups": ["manager"]
   }
```

---

## 1. Auth0 ユーザー作成

### 1.1 管理画面の場所
Auth0 Dashboard → **User Management** → **Users** → **+ Create User**

### 1.2 パラメータ
| 項目 | 値 |
|------|-----|
| Email | `alice@acme.com` 等（架空メールOK） |
| Password | `TestPass1!` 等任意 |
| Connection | `Username-Password-Authentication` |

### 1.3 作成後の設定
ユーザーをクリックして詳細画面へ：

- **Details タブ** → `Email Verified` を **true** に変更（Save）
- **Raw JSON / Metadata タブ** → `app_metadata` を設定（次章）

---

## 2. app_metadata の設定

ユーザー詳細画面の **Metadata** タブで `app_metadata` 欄に以下を入力：

### alice@acme.com
```json
{
  "tenant_id": "acme-corp",
  "role": "employee"
}
```

### bob@acme.com
```json
{
  "tenant_id": "acme-corp",
  "role": "manager"
}
```

### carol@acme.com
```json
{
  "tenant_id": "acme-corp",
  "role": "admin"
}
```

### dave@globex.com
```json
{
  "tenant_id": "globex-inc",
  "role": "manager"
}
```

**重要**: `user_metadata` ではなく `app_metadata` に入れる。
- `user_metadata`: ユーザー自身が編集可（プロフィール類）
- `app_metadata`: アプリ側のみ編集可（ロール等の権限に関する情報）

---

## 3. Action（Post Login）の作成

`app_metadata` の値を **IDトークンのカスタムクレーム** として発行するには、
Post Login Action が必要。Auth0 はデフォルトでは app_metadata をトークンに
出力しない。

### 3.1 Action を作成

Auth0 Dashboard → **Actions** → **Library** → **Create Action** → **Build Custom**

| 項目 | 値 |
|------|-----|
| Name | `Add tenant and role claims` |
| Trigger | **Login / Post Login** |
| Runtime | Node 22 |

### 3.2 コード

```javascript
/**
 * Auth0 Post Login Action
 * app_metadata.tenant_id / app_metadata.role を IDトークンに
 * カスタムクレームとして注入する。
 *
 * Cognito OIDC フェデレーションの attribute_mapping で
 *   custom:tenant_id ← tenant_id
 *   custom:roles     ← role
 * にマッピングされる。
 */
exports.onExecutePostLogin = async (event, api) => {
  const md = event.user.app_metadata || {};

  if (md.tenant_id) {
    api.idToken.setCustomClaim('tenant_id', md.tenant_id);
  }
  if (md.role) {
    api.idToken.setCustomClaim('role', md.role);
  }
};
```

右上の **Deploy** ボタンで保存＋デプロイ。

---

## 4. Action を Login フローに紐付ける

Deploy しただけでは実行されない。**Login Flow** に配置する必要がある。

### 4.1 Flow の場所（UI バージョンによって異なる）

**現行UI（2024〜）**:
- 左サイドバー **Actions** → **Triggers** → **post-login** を選択

**旧UI**:
- 左サイドバー **Actions** → **Flows** → **Login**

### 4.2 配置手順

1. Trigger `post-login` を開く
2. 右側の **Custom** タブに先ほど作成した `Add tenant and role claims` がある
3. Action を真ん中のフロー図（Start → End の間）にドラッグ&ドロップ
4. **Apply** ボタンで保存

---

## 5. 動作確認（Auth0単体）

### 5.1 Auth0 Universal Login をテスト

Auth0 Dashboard → **Applications** → 対象アプリ → **Test** タブ
- Try Login で alice@acme.com にログイン
- 成功したら IDトークンを Decode（jwt.io等）
- `tenant_id` / `role` クレームが載っていることを確認

### 5.2 Cognito 経由のクレーム確認

PoC SPA（http://localhost:5173）で Auth0 ログイン → トークンビューアで確認。
期待値:

```json
{
  "sub": "...",
  "email": "alice@acme.com",
  "tenant_id": "acme-corp",
  "roles": "employee",
  "cognito:groups": ["employee"],
  "identities": [{ "providerName": "Auth0", ... }]
}
```

---

## 6. トラブルシュート

### クレームが空/undefined になる
- `app_metadata` ではなく `user_metadata` に書いていないか
- Action が Login Flow に接続されていない（Deploy だけでは不十分）
- Action 内で `event.user.app_metadata` ではなく別のパスを参照している

### Cognito 側にカスタム属性が書き込まれない
- Terraform の `attribute_mapping` 側のキーと Auth0 クレーム名が一致しているか
  - 期待: Cognito `custom:tenant_id` ← Auth0 クレーム `tenant_id`
  - `infra/cognito.tf` の `aws_cognito_identity_provider.auth0` で確認
- 初回ログインで JIT プロビジョニングされた後、属性は固定される（変更は
  Cognito 側から手動更新必要）

### Lambda Authorizer で tenant_id が取れない
- Cognito User Pool 側の custom 属性に値は入っているか（AWS Console で
  Users → 対象ユーザー → Attributes）
- Pre Token Generation Lambda が呼ばれているか（CloudWatch Logs
  `/aws/lambda/auth-poc-pre-token`）
- attribute_mapping の更新後、既存ユーザーは再ログインしても属性が
  上書きされないことがある。AWS Console から手動で属性を入れるか
  ユーザーを削除して再JITさせる。

---

## 参考

- [Auth0 Post Login Actions docs](https://auth0.com/docs/customize/actions/triggers/post-login)
- [Auth0 Custom Claims](https://auth0.com/docs/secure/tokens/json-web-tokens/create-custom-claims)
- [Cognito OIDC Federation Attribute Mapping](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-oidc-flow.html)
