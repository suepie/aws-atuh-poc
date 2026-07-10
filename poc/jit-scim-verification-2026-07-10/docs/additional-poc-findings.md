# 追加 PoC 実機検証 — 発見事項と是正（2026-07-10）

> 本 PoC を実機（Linux devcontainer / Docker Desktop WSL2 backend）で実際に起動・実行した際に判明した
> 環境是正点・Keycloak 26.6 の仕様変更・スクリプト/設定の不備をまとめる。
> V1/V2/V3' の判定結果は [verification-log.md](verification-log.md) を参照。

---

## サマリ（6 件）

| # | 分類 | 事象 | 影響 | 是正 |
|---|---|---|---|---|
| **F-1** | KC26.6 仕様変更 | feature 名 `scim-realm-api` / `declarative-user-profile` が **存在せず起動失敗** | 環境が起動しない | `scim-api` に変更、`declarative-user-profile` は削除 |
| **F-2** | 実行環境 | devcontainer + Docker Desktop で **bind mount が空**（config/SPI が入らない） | realm import / SPI が効かない | `Dockerfile.poc` でイメージに焼き込み |
| **F-3** | KC26.6 仕様 / config | `unmanagedAttributePolicy` を **realm 属性で指定しても無効**、カスタム属性が黙って破棄 | V1 の核心。属性が保存されない | **User Profile API/config** で設定（+ `config/user-profile-poc.json` を追加） |
| **F-4** | KC26.6 仕様 | native **inbound SCIM server** が `/realms/{r}/scim/v2/*` で **404**（feature 有効でも） | V1 native SCIM 不可 | native inbound に依存しない設計（代替 A） |
| **F-5** | スクリプト不備 | `v3-custom-authenticator.sh` の SPI 検出が **serverinfo の誤キー**参照で crash | V3' が Test 1 で異常終了 | `AuthenticatorFactory` → `Authenticator` に修正 |
| **F-6** | Keycloak フロー設計 | SPI を **top-level REQUIRED** に置くと ALTERNATIVE(forms) が無視されログイン失敗 | V3' 実装制約 | **forms サブフロー内**（Username Password Form の後）に配置 |

---

## F-1: Keycloak 26.6 の feature 名変更

`docker-compose.yml` の `KC_FEATURES: scim-realm-api,declarative-user-profile,admin-fine-grained-authz` で起動すると:

```
'scim-realm-api' is an unrecognized feature, it should be one of [... scim-api ...]
'declarative-user-profile' is an unrecognized feature, it should be one of [...]
```

- `scim-realm-api` → **`scim-api`**（26.6 実機の feature 名。起動時 `Experimental features enabled: scim-api:v1`）
- `declarative-user-profile` → **廃止**（26 系で GA・デフォルト化。指定すると起動失敗）

> ⚠ QUICKSTART-OTHER-MACHINE.md §8.2 の「26.6 で正しい feature 名は scim-realm-api」は**誤り**。正しくは `scim-api`。

**是正**：`docker-compose.exec.yml` で `KC_FEATURES: scim-api,admin-fine-grained-authz`。

---

## F-2: devcontainer での bind mount 問題

Docker daemon が `docker-desktop`（WSL2 backend）で、devcontainer 内パス `/workspaces/...` を daemon が解決できない。
検証:

```
docker run --rm -v /workspaces/.../config:/test alpine ls -la /test
→ total 4  （空。ホスト側に該当パスが無く空ディレクトリがマウントされる）
```

このため元の `docker-compose.yml` の
`- ./config:/opt/keycloak/data/import` / `- ./spi/.../target:/opt/keycloak/providers`
は **両方とも空マウント**になり、realm import も SPI ロードも効かない。

**是正**：`Dockerfile.poc`（マルチステージ）で SPI を Maven ビルドし、config/JAR を **イメージに COPY で焼き込む**。
`docker build` のコンテキストは tar ストリームで daemon に送られるため、マウント問題を回避できる。
`docker-compose.exec.yml` はこのイメージを `build:` で使用。

> 元 Mac 環境（`/Users/suepie/...`）では bind mount が効くため、この是正は **devcontainer 実行時のみ必要**。

---

## F-3: カスタム属性が黙って破棄される（V1 の核心）

`config/realm-poc.json` は `"attributes": {"unmanagedAttributePolicy": "ADMIN_EDIT"}` を **realm 属性**として指定していたが、
Keycloak 26.6 ではこれは **User Profile の設定として認識されない**。結果:

```
GET /admin/.../users/profile .unmanagedAttributePolicy -> null   （= 無効）
PUT /admin/.../users/{id} {attributes:{scim_active:["true"]}} -> 204   （成功に見える）
GET /admin/.../users/{id} .attributes -> null                    （実は破棄されている）
```

`unmanagedAttributePolicy` を **User Profile API** で設定すると解決:

```
PUT /admin/realms/poc-jit-scim/users/profile {..., "unmanagedAttributePolicy":"ADMIN_EDIT"} -> 200
PUT /admin/.../users/{id} {attributes:{scim_active:["true"],provisioned_by:["scim"]}} -> 204
GET /admin/.../users/{id} .attributes -> {"provisioned_by":["scim"],"scim_active":["true"]}  ← 永続化 OK
```

> SPI（V3'）が auth flow 内で `setSingleAttribute` する場合は、より広い `ENABLED` が確実
> （`ADMIN_EDIT` は管理者コンテキスト限定）。本 PoC の V3' 検証では `ENABLED` を使用した。

**是正**：`config/user-profile-poc.json` を追加（unmanaged 属性を有効化 + `scim_active`/`provisioned_by`/`last_login` を宣言する例）。
Phase 1 実装では **User Profile に対象属性を明示宣言**するのが本筋（unmanaged に頼らない）。

---

## F-4: native inbound SCIM server が 404

`scim-api:v1` feature 有効・`realm-restapi-extension.providers.scim` も登録されているにもかかわらず、
inbound SCIM エンドポイントは全て 404:

```
/realms/poc-jit-scim/scim/v2/ServiceProviderConfig -> 404
/realms/poc-jit-scim/scim/v2/Users                 -> 404
serverinfo: providers.realm-restapi-extension.providers.scim.order = 0   ← 登録はされている
            providers.scimResourceType.providers.{Users,Groups,ServiceProviderConfig,Schemas,ResourceTypes}
```

追加の realm 単位設定（SCIM の有効化/プロビジョニング）が無いと当該パスが露出しない。
これは §10.4.E.1 の「native SCIM はカスタムスキーマ未成熟」という一次資料の結論と整合する。

**是正/方針**：Phase 1 では **native inbound SCIM に依存しない**。SCIM 受信は外部コンポーネント or Admin API で行い、
`scim_active`/`provisioned_by` は SPI/Admin でセット（**代替 A**）。

---

## F-5: v3 スクリプトの SPI 検出バグ

`tests/v3-custom-authenticator.sh` Test 1:

```bash
# 現状（誤）: このキーは serverinfo に存在せず null → jq が crash して異常終了
jq -r '.componentTypes."org.keycloak.authentication.AuthenticatorFactory"[] | select(.id == "last-login-tracker") | .id'
```

serverinfo の実際のキーは `org.keycloak.authentication.Authenticator`。正しくは:

```bash
jq -r '.componentTypes."org.keycloak.authentication.Authenticator"[]? | select(.id == "last-login-tracker") | .id'
```

（SPI 自体はロードされている。起動ログ `... implementing the internal SPI authenticator` で確認可能。）

**是正**：スクリプトのキーを修正（`?` を付けて null 安全に）。

---

## F-6: SPI のフロー配置（重要な実装制約）

SPI を `browser-with-last-login` の **最上位（level 0）に REQUIRED** で置くと:

```
WARN REQUIRED and ALTERNATIVE elements at same level!
     Those alternative executions will be ignored: [auth-cookie, identity-provider-redirector, ...]
WARN authenticator 'last-login-tracker' requires user to be set ... but user is not set yet
-> LOGIN_ERROR invalid_user_credentials   （ログイン自体が失敗）
```

Keycloak のフロー評価では、同一レベルに REQUIRED があると同レベルの ALTERNATIVE（Cookie / forms）が無視される。
その結果 **Username Password Form（forms サブフロー内）が実行されず**、user が未設定のまま SPI が走り例外になる。

**正しい配置**（本 PoC で PASS した構成）:

```
browser-with-last-login
  level0 Cookie (ALTERNATIVE)
  level0 Identity Provider Redirector (ALTERNATIVE)
  level0 forms (ALTERNATIVE)
    level1 Username Password Form (REQUIRED)
    level1 Last Login Tracker (REQUIRED)   ← forms サブフロー内・UPF の後に配置
```

**是正**：QUICKSTART の手動手順（§4.3）と Phase 1 実装で、SPI は **forms サブフロー内に配置**する旨を明記。

---

## 再現手順（この環境で再実行する場合）

```bash
cd poc/jit-scim-verification-2026-07-10/

# 1. イメージビルド（SPI Maven build + config/JAR 焼き込み）
docker compose -f docker-compose.exec.yml build

# 2. 起動
docker compose -f docker-compose.exec.yml up -d

# 3. devcontainer を PoC ネットワークに接続（sibling container 間通信のため）
docker network connect poc-jit-scim-exec_default "$(hostname)"

# 4. テスト実行（localhost:18080 の代わりに container 名で到達）
export KC_URL=http://poc-keycloak-266:8080
./tests/v2-sync-mode-override.sh          # PASS
./tests/v1-metatavu-scim.sh               # native SCIM 404 → 代替 A
# V3' は User Profile 有効化 + forms サブフロー配置 + auth code flow で検証（本ログ 4 章参照）

# 5. クリーンアップ
docker compose -f docker-compose.exec.yml down -v
```
