# Keycloak Realm 設定ファイル

このディレクトリは Keycloak `auth-poc` Realm の設定を Git 管理するための SSOT です。

## ファイル一覧

| ファイル | 役割 | Phase | 機密性 |
|---|---|---|---|
| [realm-export.json](realm-export.json) | Realm 全体定義（Clients / Users / Roles / Groups / Protocol Mappers / Scope Mappings） | Phase 6 + 8/9 | ⚠ サンプルパスワード含む |
| [realm-idp-auth0.json.example](realm-idp-auth0.json.example) | Phase 7 Auth0 Identity Brokering 設定テンプレート | Phase 7 | 🔥 実環境では secret を埋めて Git 管理外に |
| [export-realm.sh](export-realm.sh) | 稼働中 Keycloak から realm を export するヘルパー | - | - |
| [import-realm.sh](import-realm.sh) | realm-export.json を import するヘルパー | - | - |

## Phase 別カバー内容

### Phase 6（基本構成、realm-export.json 既存分）

- Realm: `auth-poc`
- Roles: `user` / `admin` / `expense-approver`
- Groups: `expense-users` / `expense-approvers` / `admins`
- Clients: `auth-poc-spa` (Public) / `auth-poc-backend` (Confidential M2M)
- Users: test@example.com / approver@example.com / admin@example.com

### Phase 8/9（クレームマッピング・認可、realm-export.json に統合済）

- **Unmanaged Attributes Enabled** (`attributes.userProfileEnabled = "true"`) — User Attribute 保存に必須
- **追加 Realm Roles**: `employee` / `manager`（Phase 8/9 で導入、`admin` は既存を流用）
- **Protocol Mappers** on `auth-poc-spa` client:
  - `tenant_id` (User Attribute → access/id token)
  - `roles` (Realm Role multivalued → access/id token)
  - `email` (User Property → access/id token + userinfo)
- **Full Scope Allowed = false** on both clients（`offline_access` 等の内部ロール除外）
- **Scope Mappings** `auth-poc-spa` → `[employee, manager, admin, user, expense-approver]`
- **Phase 8/9 テストユーザー**:
  - alice-kc / alice@acme.com / tenant_id=acme-corp / role=employee
  - bob-kc / bob@acme.com / tenant_id=acme-corp / role=manager
  - carol-kc / carol@acme.com / tenant_id=acme-corp / role=admin
  - dave-kc / dave@globex.com / tenant_id=globex-inc / role=manager

### Phase 7（MFA / SSO / Auth0、realm-idp-auth0.json.example に分離）

- **Identity Provider `auth0`** — 環境変数 `AUTH0_DOMAIN` / `AUTH0_CLIENT_ID` / `AUTH0_CLIENT_SECRET` で展開（secret を realm.json に commit しないため別ファイル）
- **TOTP MFA** — Keycloak v26 デフォルトの browser flow に「Browser - Conditional OTP」が組込み済み（追加設定不要）
  - ローカルユーザー: Credentials タブから OTP を登録すると次回ログインで OTP 要求
  - フェデユーザー: OTP credential 未設定 → Conditional OTP が自動スキップ（[mfa-sso-auth0-scenarios.md §7-6](../../doc/keycloak/mfa-sso-auth0-scenarios.md)）
- **Back-Channel Logout** — `auth-poc-spa` client の attributes に `backchannel.logout.session.required = true` を設定済み

## 適用フロー

### 新規環境への import（PoC 再構築）

```bash
# 1. Docker Compose で Keycloak 起動（compose 内で /opt/keycloak/data/import/ にマウント済）
cd keycloak/
docker compose up -d

# 2. realm-export.json が --import-realm で自動取込される
#    （ECS 環境では task definition の command に "--import-realm" を含めている）

# 3. Auth0 IdP は別途設定
cp config/realm-idp-auth0.json.example /tmp/realm-idp-auth0.json
# /tmp/realm-idp-auth0.json を編集して ${AUTH0_*} を実値に置換
docker exec keycloak-keycloak-1 /opt/keycloak/bin/kcadm.sh \
  config credentials --server http://localhost:8080 \
  --realm master --user admin --password "$KC_ADMIN_PASSWORD"
docker cp /tmp/realm-idp-auth0.json keycloak-keycloak-1:/tmp/
docker exec keycloak-keycloak-1 /opt/keycloak/bin/kcadm.sh \
  create identity-provider/instances -r auth-poc -f /tmp/realm-idp-auth0.json
```

### 稼働中 Keycloak からの export（変更を git に反映）

```bash
bash config/export-realm.sh
git diff config/realm-export.json
# 意図した変更のみコミット。secret や環境固有値が含まれていないか必ず確認
```

## Phase 7-9 を fresh import で再現する手順

[doc/keycloak/quick-rebuild-checklist.md](../../doc/keycloak/quick-rebuild-checklist.md) の手順は Admin Console UI で 10 分で再構築する方法だが、本ファイル群を使う方法では:

1. `make tf-apply-kc`（Terraform で ECS/RDS 起動）
2. ECS task は `command: ["start-dev", "--import-realm"]` で起動し、`/opt/keycloak/data/import/realm-export.json` を自動 import
3. Auth0 IdP のみ手動設定（上記「適用フロー」参照）
4. Phase 7-1 の TOTP 必須化が必要な場合のみ、Admin Console → Authentication → Required Actions → `Configure OTP` → Default Action ON

→ Phase 8/9 中核機能（tenant_id / roles クレーム注入、Full Scope OFF、テストユーザー）は **コード経由で完全再現可能**。Admin Console の手作業ゼロ。

## 注意事項

- **Secret 管理**: `realm-export.json` 内のパスワード（`TestPass1!` / `TestUser1!` 等）は PoC 用ダミー。本番では外部 Secrets Manager と連携する `--features=admin-fine-grained-authz` 等の機構へ移行
- **Client Secret**: `auth-poc-backend` client の `secret: "change-me-in-production"` は本番では Secrets Manager 経由で注入
- **`fullScopeAllowed: false`**: Phase 8/9 で導入。これがないと JWT の `realm_access.roles` に `offline_access` / `uma_authorization` 等の内部ロールが混入する
- **Unmanaged Attributes**: `attributes.userProfileEnabled = "true"` がないと User Attribute の `tenant_id` が保存できず、Mapper が空クレームを出す
