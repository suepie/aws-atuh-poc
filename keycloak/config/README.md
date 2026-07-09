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

## ⚠️ 既存 realm が存在する環境での `--import-realm` の挙動（重要）

**`--import-realm` は既存 realm が DB に存在すると import を skip するデフォルト動作**。新しい realm-export.json を image に焼き付けても、初回構築後の realm 変更は反映されない。

### 典型的な踏み方（Phase 10 Stage A で実機ヒット、2026-06-07）

- Phase 6 で `auth-poc` realm が RDS に作成・永続化
- Phase 10 Stage A で realm-export.json に Token Exchange v2 設定を追加
  - `auth-poc-target-api` client（新規）
  - `auth-poc-backend` の `standard.token.exchange.enabled = true` 属性
  - `auth-poc-ssr` client（新規）
- 新 image (KC 26.2 + features 焼き付け) を ECR push → ECS で新 task 起動
- → 既存 realm があるため `--import-realm` skip → 新設定が realm に反映されない
- → Token Exchange v2 curl が `invalid_client: Audience not found` で失敗
- Admin REST API で realm を確認すると **`auth-poc-target-api` クライアント自体が存在しない**

### 対処法（3 つ）

| 方針 | 用途 | 影響 | 手順 |
|---|---|---|---|
| **A. Partial Import**（既存温存、差分追加） | 本番運用での realm 変更 | 既存ユーザー / セッション保持 | Admin Console → Realm Settings → Partial Import / REST `/admin/realms/{realm}/partialImport` |
| **B. realm delete → 再起動**（fresh import） | PoC の「初期状態再現」テスト | **既存ユーザー / セッション全消失** | DELETE `/admin/realms/auth-poc` → `make kc-redeploy`（ECS force-new-deployment） → 新タスク起動時に realm-export.json が import される |
| **C. Admin Console 手動変更** | 緊急 / 1 回限り | 設定が realm.json から drift | Admin Console で 1 つずつ変更 → 後で `export-realm.sh` で realm.json に書き戻し |

### 本番運用想定の運用フロー

「**realm.json を git の SSOT**」と「**Admin Console での直接変更**」の二系統管理は **drift の温床**になる。本番では:

1. **Admin Console での直接変更は禁止**（読み取り専用運用）
2. **realm 変更は PR ベースで realm.json を編集**
3. **CI/CD で Partial Import を自動実行**（Keycloak Operator や Terraform Keycloak Provider）
4. 既存ユーザー・セッションは温存（fresh import は禁止）

### 確認用コマンド

```bash
# 現 AWS realm に特定 client が存在するか確認
ALB=$(cd infra/keycloak && terraform output -raw keycloak_url | sed 's|http://||;s|https://||')
ADMIN_PW=$(grep keycloak_admin_password infra/keycloak/terraform.tfvars | sed -E 's/.*= *"([^"]+)".*/\1/')
ADMIN_TOKEN=$(curl -ks -X POST "https://$ALB/realms/master/protocol/openid-connect/token" \
  -d "client_id=admin-cli&grant_type=password&username=admin&password=$ADMIN_PW" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
curl -ks -H "Authorization: Bearer $ADMIN_TOKEN" \
  "https://$ALB/admin/realms/auth-poc/clients?clientId=auth-poc-target-api" | python3 -m json.tool
# → [] なら未反映、{...} なら反映済
```

---

## 注意事項

- **Secret 管理**: `realm-export.json` 内のパスワード（`TestPass1!` / `TestUser1!` 等）は PoC 用ダミー。本番では外部 Secrets Manager と連携する `--features=admin-fine-grained-authz` 等の機構へ移行
- **Client Secret**: `auth-poc-backend` client の `secret: "change-me-in-production"` は本番では Secrets Manager 経由で注入
- **`fullScopeAllowed: false`**: Phase 8/9 で導入。これがないと JWT の `realm_access.roles` に `offline_access` / `uma_authorization` 等の内部ロールが混入する
- **Unmanaged Attributes**: `attributes.userProfileEnabled = "true"` がないと User Attribute の `tenant_id` が保存できず、Mapper が空クレームを出す
