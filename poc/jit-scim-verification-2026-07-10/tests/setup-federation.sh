#!/bin/bash
# フェデ JIT 検証（V3''）用の環境セットアップ
#
# 動作:
#   1. customer-idp Realm を作成（Keycloak Native import 済 or Admin API で作成）
#   2. poc-jit-scim Realm に OIDC Identity Provider "customer-idp" を追加
#   3. First Broker Login Flow を複製 → Last Login Tracker を末尾に配置
#   4. Post Broker Login Flow を新規作成 → Last Login Tracker を配置
#   5. Identity Provider に First/Post Broker Login Flow を紐付け
#   6. User Profile に provisioned_by/last_login/scim_active を宣言
#
# 前提:
#   - docker compose up 済み（Keycloak 26.6 起動中）
#   - SPI JAR デプロイ済み（last-login-tracker が Authenticator にロード済み）
#   - poc-jit-scim Realm インポート済み
#
# 一次資料:
#   - jit-scim §10.4.F.9 検証ギャップ
#   - ADR-060 §C.2.3 F-9 フェデ経路制約

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

log_test "===================================================="
log_test "セットアップ：フェデ JIT 検証環境（V3''）"
log_test "===================================================="

wait_for_keycloak || exit 1
TOKEN=$(get_admin_token)
log_ok "Admin token acquired"

# ==== Step 1: customer-idp Realm の作成 ====
log_test "Step 1: customer-idp Realm を作成"

# 既存確認
EXISTS=$(curl -s -o /dev/null -w "%{http_code}" \
    "${KC_URL}/admin/realms/customer-idp" \
    -H "Authorization: Bearer ${TOKEN}")

if [ "$EXISTS" = "200" ]; then
    log_warn "customer-idp Realm は既に存在します。スキップ"
else
    # config/customer-idp-realm.json から作成
    IDP_REALM_JSON="${SCRIPT_DIR}/../config/customer-idp-realm.json"
    if [ ! -f "$IDP_REALM_JSON" ]; then
        log_error "config/customer-idp-realm.json が見つかりません"
        exit 1
    fi

    CREATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
        "${KC_URL}/admin/realms" \
        -H "Authorization: Bearer ${TOKEN}" \
        -H "Content-Type: application/json" \
        -d @"$IDP_REALM_JSON")

    HTTP_CODE=$(echo "$CREATE_RESPONSE" | tail -1)
    if [ "$HTTP_CODE" = "201" ]; then
        log_ok "customer-idp Realm を作成しました"
    else
        log_error "customer-idp Realm 作成失敗 (HTTP $HTTP_CODE)"
        echo "$CREATE_RESPONSE"
        exit 1
    fi
fi

# ==== Step 2: User Profile に対象属性を宣言 ====
log_test "Step 2: poc-jit-scim Realm の User Profile 設定"

USER_PROFILE_JSON="${SCRIPT_DIR}/../config/user-profile-poc.json"
if [ -f "$USER_PROFILE_JSON" ]; then
    UP_RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT \
        "${KC_URL}/admin/realms/${KC_REALM}/users/profile" \
        -H "Authorization: Bearer ${TOKEN}" \
        -H "Content-Type: application/json" \
        -d @"$USER_PROFILE_JSON")

    HTTP_CODE=$(echo "$UP_RESPONSE" | tail -1)
    if [ "$HTTP_CODE" = "200" ]; then
        log_ok "User Profile 設定完了（provisioned_by/last_login/scim_active 宣言）"
    else
        log_warn "User Profile 設定 HTTP $HTTP_CODE"
    fi
else
    log_warn "config/user-profile-poc.json が見つかりません。unmanaged 属性有効化のみ実施"
    UP_MIN='{"unmanagedAttributePolicy":"ENABLED"}'
    curl -s -X PUT "${KC_URL}/admin/realms/${KC_REALM}/users/profile" \
        -H "Authorization: Bearer ${TOKEN}" \
        -H "Content-Type: application/json" \
        -d "$UP_MIN" > /dev/null
    log_ok "unmanagedAttributePolicy=ENABLED を設定"
fi

# ==== Step 3: OIDC Identity Provider "customer-idp" を追加 ====
# 注意（F-7）: IdP は First/Post Broker Login Flow を参照するが、それらは Step 4-5 で作成する。
#             先に flow alias を指定すると "No available authentication flow" で 500 になるため、
#             ここでは flow alias を付けず IdP を作成し、Step 6 でフロー作成後に紐付ける。
log_test "Step 3: poc-jit-scim Realm に OIDC IdP を追加（flow alias は Step 6 で紐付け）"

# 既存 IdP チェック
IDP_EXISTS=$(curl -s -o /dev/null -w "%{http_code}" \
    "${KC_URL}/admin/realms/${KC_REALM}/identity-provider/instances/customer-idp" \
    -H "Authorization: Bearer ${TOKEN}")

if [ "$IDP_EXISTS" = "200" ]; then
    log_warn "IdP 'customer-idp' は既に存在します。削除して再作成します"
    curl -s -X DELETE \
        "${KC_URL}/admin/realms/${KC_REALM}/identity-provider/instances/customer-idp" \
        -H "Authorization: Bearer ${TOKEN}" > /dev/null
fi

# Keycloak 自身の Discovery URL を取得（同一 Docker network 内なので container 名で解決）
# ※ ローカル ↔ container 相互アクセスに応じて調整
INTERNAL_KC_URL="${INTERNAL_KC_URL:-http://poc-keycloak-266:8080}"
DISCOVERY_URL="${INTERNAL_KC_URL}/realms/customer-idp/.well-known/openid-configuration"

IDP_CONFIG=$(cat <<EOF
{
  "alias": "customer-idp",
  "displayName": "Customer IdP (Federation Test)",
  "providerId": "oidc",
  "enabled": true,
  "trustEmail": true,
  "storeToken": false,
  "linkOnly": false,
  "config": {
    "syncMode": "IMPORT",
    "clientId": "broker-poc",
    "clientSecret": "broker-poc-secret-2026",
    "authorizationUrl": "${INTERNAL_KC_URL}/realms/customer-idp/protocol/openid-connect/auth",
    "tokenUrl": "${INTERNAL_KC_URL}/realms/customer-idp/protocol/openid-connect/token",
    "userInfoUrl": "${INTERNAL_KC_URL}/realms/customer-idp/protocol/openid-connect/userinfo",
    "logoutUrl": "${INTERNAL_KC_URL}/realms/customer-idp/protocol/openid-connect/logout",
    "issuer": "${INTERNAL_KC_URL}/realms/customer-idp",
    "jwksUrl": "${INTERNAL_KC_URL}/realms/customer-idp/protocol/openid-connect/certs",
    "useJwksUrl": "true",
    "validateSignature": "true",
    "clientAuthMethod": "client_secret_post",
    "defaultScope": "openid profile email"
  }
}
EOF
)

CREATE_IDP=$(curl -s -w "\n%{http_code}" -X POST \
    "${KC_URL}/admin/realms/${KC_REALM}/identity-provider/instances" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d "$IDP_CONFIG")

HTTP_CODE=$(echo "$CREATE_IDP" | tail -1)
if [ "$HTTP_CODE" = "201" ]; then
    log_ok "OIDC IdP 'customer-idp' を作成"
else
    log_warn "IdP 作成 HTTP $HTTP_CODE"
    echo "$CREATE_IDP"
fi

# ==== Step 4: First Broker Login Flow を複製 + Last Login Tracker 追加 ====
log_test "Step 4: First Broker Login Flow に SPI を追加"

# 既存の 'first broker login' を複製
COPY_FBL=$(curl -s -w "\n%{http_code}" -X POST \
    "${KC_URL}/admin/realms/${KC_REALM}/authentication/flows/first%20broker%20login/copy" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{"newName":"first-broker-login-with-tracker"}')

HTTP_CODE=$(echo "$COPY_FBL" | tail -1)
if [ "$HTTP_CODE" = "201" ] || [ "$HTTP_CODE" = "409" ]; then
    log_ok "first-broker-login-with-tracker フロー準備完了"
else
    log_warn "First Broker Login Flow 複製 HTTP $HTTP_CODE"
fi

# Last Login Tracker を追加（フロー末尾）
ADD_EXEC=$(curl -s -w "\n%{http_code}" -X POST \
    "${KC_URL}/admin/realms/${KC_REALM}/authentication/flows/first-broker-login-with-tracker/executions/execution" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{"provider":"last-login-tracker"}')

HTTP_CODE=$(echo "$ADD_EXEC" | tail -1)
if [ "$HTTP_CODE" = "201" ]; then
    log_ok "First Broker Login Flow に Last Login Tracker を追加"
else
    log_warn "SPI 追加 HTTP $HTTP_CODE"
fi

# 追加した execution を REQUIRED に設定
sleep 1
EXECUTIONS=$(curl -s "${KC_URL}/admin/realms/${KC_REALM}/authentication/flows/first-broker-login-with-tracker/executions" \
             -H "Authorization: Bearer ${TOKEN}")
TRACKER_EXEC_ID=$(echo "$EXECUTIONS" | jq -r '.[] | select(.providerId == "last-login-tracker") | .id')
if [ -n "$TRACKER_EXEC_ID" ] && [ "$TRACKER_EXEC_ID" != "null" ]; then
    # requirement を REQUIRED に更新
    UPDATED_EXEC=$(echo "$EXECUTIONS" | jq --arg id "$TRACKER_EXEC_ID" \
        '.[] | select(.id == $id) | .requirement = "REQUIRED"')
    curl -s -X PUT \
        "${KC_URL}/admin/realms/${KC_REALM}/authentication/flows/first-broker-login-with-tracker/executions" \
        -H "Authorization: Bearer ${TOKEN}" \
        -H "Content-Type: application/json" \
        -d "$UPDATED_EXEC" > /dev/null || true
    log_ok "First Broker Login Flow の Last Login Tracker を REQUIRED に設定"
fi

# ==== Step 5: Post Broker Login Flow を新規作成 + SPI 追加 ====
log_test "Step 5: Post Broker Login Flow を作成 + SPI 追加"

# 新規トップレベルフロー作成
CREATE_PBL=$(curl -s -w "\n%{http_code}" -X POST \
    "${KC_URL}/admin/realms/${KC_REALM}/authentication/flows" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{"alias":"post-broker-login-with-tracker","description":"Post Broker Login with Last Login Tracker","providerId":"basic-flow","topLevel":true,"builtIn":false}')

HTTP_CODE=$(echo "$CREATE_PBL" | tail -1)
if [ "$HTTP_CODE" = "201" ] || [ "$HTTP_CODE" = "409" ]; then
    log_ok "post-broker-login-with-tracker フロー準備完了"
else
    log_warn "Post Broker Login Flow 作成 HTTP $HTTP_CODE"
fi

# Last Login Tracker を追加
ADD_EXEC_PBL=$(curl -s -w "\n%{http_code}" -X POST \
    "${KC_URL}/admin/realms/${KC_REALM}/authentication/flows/post-broker-login-with-tracker/executions/execution" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{"provider":"last-login-tracker"}')

HTTP_CODE=$(echo "$ADD_EXEC_PBL" | tail -1)
if [ "$HTTP_CODE" = "201" ]; then
    log_ok "Post Broker Login Flow に Last Login Tracker を追加"
else
    log_warn "SPI 追加 HTTP $HTTP_CODE"
fi

# REQUIRED に設定
sleep 1
PBL_EXECS=$(curl -s "${KC_URL}/admin/realms/${KC_REALM}/authentication/flows/post-broker-login-with-tracker/executions" \
             -H "Authorization: Bearer ${TOKEN}")
PBL_TRACKER_ID=$(echo "$PBL_EXECS" | jq -r '.[] | select(.providerId == "last-login-tracker") | .id')
if [ -n "$PBL_TRACKER_ID" ] && [ "$PBL_TRACKER_ID" != "null" ]; then
    UPDATED_PBL=$(echo "$PBL_EXECS" | jq --arg id "$PBL_TRACKER_ID" \
        '.[] | select(.id == $id) | .requirement = "REQUIRED"')
    curl -s -X PUT \
        "${KC_URL}/admin/realms/${KC_REALM}/authentication/flows/post-broker-login-with-tracker/executions" \
        -H "Authorization: Bearer ${TOKEN}" \
        -H "Content-Type: application/json" \
        -d "$UPDATED_PBL" > /dev/null || true
    log_ok "Post Broker Login Flow の Last Login Tracker を REQUIRED に設定"
fi

# ==== Step 6: IdP に First/Post Broker Login Flow を紐付け（F-7 対応：フロー作成後に実施） ====
log_test "Step 6: IdP に First/Post Broker Login Flow を紐付け"

IDP_CURRENT=$(curl -s "${KC_URL}/admin/realms/${KC_REALM}/identity-provider/instances/customer-idp" \
    -H "Authorization: Bearer ${TOKEN}")
IDP_BOUND=$(echo "$IDP_CURRENT" | jq \
    '.firstBrokerLoginFlowAlias = "first-broker-login-with-tracker"
     | .postBrokerLoginFlowAlias = "post-broker-login-with-tracker"')

BIND_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X PUT \
    "${KC_URL}/admin/realms/${KC_REALM}/identity-provider/instances/customer-idp" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d "$IDP_BOUND")

if [ "$BIND_CODE" = "204" ] || [ "$BIND_CODE" = "200" ]; then
    log_ok "IdP に first/post broker login flow を紐付け（HTTP $BIND_CODE）"
else
    log_error "IdP への flow 紐付け失敗 (HTTP $BIND_CODE)"
fi

# ==== 完了 ====
log_test "===================================================="
log_ok "セットアップ完了"
log_test "===================================================="
log_info "次のステップ："
log_info "  ./tests/v4-federation-jit.sh を実行してフェデ JIT テストを実施"
log_info ""
log_info "作成された構成："
log_info "  1. customer-idp Realm（fed-jit-user / fed-jit-user-2 保有）"
log_info "  2. poc-jit-scim Realm の OIDC IdP 'customer-idp'"
log_info "  3. first-broker-login-with-tracker フロー（Last Login Tracker REQUIRED）"
log_info "  4. post-broker-login-with-tracker フロー（Last Login Tracker REQUIRED）"
log_info "  5. IdP に First/Post Broker Login Flow 紐付け"
