#!/bin/bash
# 共通ヘルパー関数

# ==== 設定 ====
export KC_URL="${KC_URL:-http://localhost:18080}"
export KC_ADMIN_USER="${KC_ADMIN_USER:-admin}"
export KC_ADMIN_PASS="${KC_ADMIN_PASS:-admin_poc_2026}"
export KC_REALM="${KC_REALM:-poc-jit-scim}"

# ==== ログ関数 ====
log_info()  { echo -e "\033[0;36m[INFO]\033[0m  $*"; }
log_ok()    { echo -e "\033[0;32m[OK]\033[0m    $*"; }
log_warn()  { echo -e "\033[0;33m[WARN]\033[0m  $*"; }
log_error() { echo -e "\033[0;31m[ERROR]\033[0m $*"; }
log_test()  { echo -e "\033[1;34m[TEST]\033[0m  $*"; }
log_verdict() { echo -e "\033[1;35m[VERDICT]\033[0m $*"; }

# ==== Admin Token 取得 ====
get_admin_token() {
    curl -s -X POST "${KC_URL}/realms/master/protocol/openid-connect/token" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "grant_type=password" \
        -d "client_id=admin-cli" \
        -d "username=${KC_ADMIN_USER}" \
        -d "password=${KC_ADMIN_PASS}" \
        | jq -r '.access_token'
}

# ==== ユーザ属性取得 ====
get_user_attribute() {
    local token="$1"
    local user_id="$2"
    local attr_name="$3"

    curl -s -X GET "${KC_URL}/admin/realms/${KC_REALM}/users/${user_id}" \
        -H "Authorization: Bearer ${token}" \
        | jq -r ".attributes.${attr_name}[0] // \"NULL\""
}

# ==== ユーザ検索（username で） ====
find_user_id() {
    local token="$1"
    local username="$2"

    curl -s -X GET "${KC_URL}/admin/realms/${KC_REALM}/users?username=${username}&exact=true" \
        -H "Authorization: Bearer ${token}" \
        | jq -r '.[0].id // "NOT_FOUND"'
}

# ==== Keycloak 起動確認 ====
wait_for_keycloak() {
    log_info "Waiting for Keycloak to be ready..."
    local max_retries=60
    local i=0
    while [ $i -lt $max_retries ]; do
        if curl -s -o /dev/null -w "%{http_code}" "${KC_URL}/realms/master" | grep -q "200"; then
            log_ok "Keycloak is ready"
            return 0
        fi
        i=$((i + 1))
        sleep 2
    done
    log_error "Keycloak did not become ready in $((max_retries * 2)) seconds"
    return 1
}
