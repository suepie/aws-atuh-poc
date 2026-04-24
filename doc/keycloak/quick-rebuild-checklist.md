# Keycloak 再構築チェックリスト（最短10分）

**目的**: VPC 移行（Option B）で Keycloak を destroy → apply した際に、
Admin Console で必要な設定を短時間で復元するための手順書。

**前提**:
- `make tf-destroy-kc` 後に `make tf-apply-kc` を実施済み
- Keycloak ECS が起動 healthy であること
- `make kc-admin-url` で管理画面 URL が表示できる
- `make kc-push` 済み（Docker イメージが ECR にある）

---

## タイムライン（10分目安）

| 時間 | 手順 |
|:----:|------|
| 0:00 | Admin Console ログイン |
| 0:30 | §1 Realm settings（Unmanaged Attributes Enabled） |
| 1:00 | §2 Realm Roles 作成（employee / manager / admin） |
| 3:00 | §3 Protocol Mappers（tenant_id / roles / email） |
| 5:00 | §4 Full scope allowed OFF + 3 Roles Assign |
| 7:00 | §5 Users 作成（alice-kc / bob-kc / carol-kc / dave-kc） |
| 9:00 | §6 Evaluate で JWT 確認 |
| 10:00 | 完了 → SPA で動作確認 |

---

## 0. Admin Console アクセス

```bash
make kc-admin-url      # URL 取得
# 例: http://auth-poc-kc-admin-alb-xxx.elb.amazonaws.com/admin

# ユーザー / パスワード
# admin / Jsol2524   ← infra/keycloak/terraform.tfvars の keycloak_admin_password
```

Realm ドロップダウンが `master` の場合は **`auth-poc` に切り替え**（左上）。

---

## 1. Realm Settings

**Admin Console → Realm settings**

| 場所 | 設定 |
|------|------|
| **General** タブ | **Unmanaged Attributes** → **Enabled** |
| **Save** |

> これを忘れると後で User Attribute に `tenant_id` を保存できない。

---

## 2. Realm Roles 作成

**Admin Console → Realm roles → Create role**

3つ作成（すべてデフォルト設定で OK）:
- `employee`
- `manager`
- （`admin` は **既存**なのでスキップ）

---

## 3. Protocol Mappers（3個）

**Admin Console → Clients → `auth-poc-spa` → Client scopes タブ → `auth-poc-spa-dedicated` をクリック → Mappers タブ**

### 3.1 tenant_id

**Add mapper → By configuration → User Attribute** を選択。

| 項目 | 値 |
|------|-----|
| Name | `tenant_id` |
| User Attribute | `tenant_id` |
| Token Claim Name | `tenant_id` |
| Claim JSON Type | `String` |
| Add to ID token | **ON** |
| Add to access token | **ON** |
| Add to userinfo | OFF |
| Add to token introspection | ON（デフォルトのまま）|
| Multivalued | OFF |

**Save**。

### 3.2 roles

**Add mapper → By configuration → User Realm Role**。

| 項目 | 値 |
|------|-----|
| Name | `roles` |
| Realm Role prefix | （空欄）|
| Multivalued | **ON** |
| Token Claim Name | `roles` |
| Claim JSON Type | `String` |
| Add to ID token | **ON** |
| Add to access token | **ON** |
| Add to userinfo | OFF |

**Save**。

### 3.3 email

標準で存在する可能性あり。無ければ:

**Add mapper → By configuration → User Property**。

| 項目 | 値 |
|------|-----|
| Name | `email` |
| Property | `email` |
| Token Claim Name | `email` |
| Add to ID token | **ON** |
| Add to access token | **ON** |

**Save**。

---

## 4. Full scope allowed OFF + 必要 Roles のみ Assign

**Clients → `auth-poc-spa` → `auth-poc-spa-dedicated`**

### 4.1 Full scope allowed OFF

- Client scopes → `auth-poc-spa-dedicated` 画面の上部（または **Scope** タブ）に
  **Full scope allowed** トグル
- **OFF** に変更 → **Save**

### 4.2 Roles を明示 Assign

**Scope** タブ → **Assign role** ボタン

- フィルタを **Filter by realm roles** に切り替え
- 以下の 3つを選択:
  - `employee`
  - `manager`
  - `admin`
- **Assign**

> これで JWT の `roles` クレームに `offline_access` などが混入せず、`["manager"]` のようにクリーンになる。

---

## 5. Users 作成（4人）

**Users → Add user**

各ユーザーで以下を実施:

### 共通パラメータ

| 項目 | 値 |
|------|-----|
| Password | `TestPass1!`（全員共通） |
| Temporary | **OFF**（Set password 時）|
| Email verified | **ON**（Details タブ）|

### ユーザー一覧

| Username | Email | tenant_id (Attributes) | Role (Role mapping) |
|---------|-------|------------------------|--------------------|
| `alice-kc` | `alice@acme.com` | `acme-corp` | `employee` |
| `bob-kc` | `bob@acme.com` | `acme-corp` | `manager` |
| `carol-kc` | `carol@acme.com` | `acme-corp` | `admin` |
| `dave-kc` | `dave@globex.com` | `globex-inc` | `manager` |

### 1ユーザーあたりの手順（約40秒）

1. **Users → Add user**
2. Username / Email 入力 → **Email verified ON** → **Create**
3. **Credentials タブ → Set password**
   - Password: `TestPass1!`
   - Temporary: **OFF**
   - **Save password**
4. **Attributes タブ**
   - Add: key = `tenant_id`, value = （上表参照）
   - **Save**
5. **Role mapping タブ → Assign role**
   - Filter: **Realm roles**
   - 選択: （上表の Role）
   - **Assign**

---

## 6. Evaluate で JWT 確認（5分）

**Clients → `auth-poc-spa` → Client scopes タブ → Evaluate タブ**

- User: `bob-kc` を選択
- **Generated access token** を確認
- 以下が含まれていれば成功:

```json
{
  "email": "bob@acme.com",
  "tenant_id": "acme-corp",
  "roles": ["manager"]
}
```

- `roles` に `offline_access` などが混入していないこと
- `tenant_id` がトップレベルクレームにあること

---

## 7. SPA からの動作確認

### 7.1 `.env` 再生成

```bash
# Keycloak の新 URL を確認
make kc-public-url

# app-keycloak/.env の VITE_KEYCLOAK_AUTHORITY を新 ALB DNS に更新
# (ALB DNS は再作成で変わるため)
```

### 7.2 SPA 起動 + ログイン

```bash
make app-kc-dev   # http://localhost:5174
```

ブラウザで `bob-kc / TestPass1!` でログイン → API Tester で `/v1/expenses` を実行 → 200 OK。

---

## 8. トラブルシュート

### Protocol Mapper 画面が見つからない
Keycloak のバージョンにより UI が異なる。以下を順に確認:
- Clients → `auth-poc-spa` → **Client scopes タブ** → `auth-poc-spa-dedicated` をクリック
- 専用 Client scope の画面内にある **Mappers** タブ

### Full scope allowed が見つからない (KC 26)
- `auth-poc-spa-dedicated` の画面内（Mappers 隣の **Scope** タブ）
- なければ Clients → `auth-poc-spa` 内の **Settings** タブ下部を探す

### ログイン画面で「Invalid parameter: redirect_uri」
**Clients → `auth-poc-spa` → Settings**
- **Valid redirect URIs**: `http://localhost:5174/*`
- **Web origins**: `http://localhost:5174`

### Admin Console アクセス時に「HTTPS required」
master realm の `sslRequired` が DB に書き込まれている。ECS Exec で:

```bash
make kc-exec   # sh で入れる
/opt/keycloak/bin/kcadm.sh config credentials --server http://localhost:8080 --realm master --user admin --password Jsol2524
/opt/keycloak/bin/kcadm.sh update realms/master -s sslRequired=NONE
```

---

## 9. 参考

- 本手順書は [claim-mapping-setup.md](claim-mapping-setup.md) の内容を再構築時用にダイジェスト化したもの
- 詳細設定の意図は [claim-mapping-setup.md](claim-mapping-setup.md) と [../common/claim-mapping-authz-scenario.md](../common/claim-mapping-authz-scenario.md) を参照
