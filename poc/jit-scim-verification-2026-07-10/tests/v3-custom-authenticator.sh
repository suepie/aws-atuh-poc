#!/bin/bash
# V3' 検証：Custom Authenticator SPI で user_attribute.last_login 書込
#
# 一次資料背景:
# - E-8: Event Listener SPI 内 setSingleAttribute 動かない（Issue #14942、Closed as not planned）
# - E-9: enlistAfterCompletion で ConcurrentModificationException（Issue #22902、Open）
# - E-10: 公式推奨 workaround = enlistAfterCompletion
#
# 検証項目:
#   1. Custom Authenticator SPI が Keycloak にロードされている
#   2. Browser Flow に SPI を組込
#   3. ログイン試行 → user_attribute.last_login 反映
#   4. 2 回目ログイン → debounce（1 日以内はスキップ）動作
#
# 期待結果:
#   ✅ 案 B Custom Authenticator SPI で setSingleAttribute が確実に動作
#   → Phase 1 実装で本方式を採用

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

log_test "===================================================="
log_test "V3': Custom Authenticator SPI 検証"
log_test "===================================================="

wait_for_keycloak || exit 1
TOKEN=$(get_admin_token)
log_ok "Admin token acquired"

# ==== Test 1: SPI ロード確認 ====
log_test "Test 1: SPI が Keycloak にロードされているか確認"

# Server info API から Authenticator 一覧を取得
SERVER_INFO=$(curl -s "${KC_URL}/admin/serverinfo" \
              -H "Authorization: Bearer ${TOKEN}")

# 注意: serverinfo の componentTypes キーは "...authentication.Authenticator"
#       （"...AuthenticatorFactory" ではない）。誤キーだと jq が null で crash する。
#       詳細: docs/additional-poc-findings.md F-5
AUTH_LOADED=$(echo "$SERVER_INFO" | jq -r '.componentTypes."org.keycloak.authentication.Authenticator"[]? | select(.id == "last-login-tracker") | .id')

if [ "$AUTH_LOADED" = "last-login-tracker" ]; then
    log_ok "✅ 'last-login-tracker' Authenticator SPI がロードされている"
else
    log_error "❌ SPI が Keycloak にロードされていない"
    log_error "  → SPI JAR を build.sh でビルド後、Keycloak restart 必要"
    log_error "  → docker compose logs keycloak | grep -i 'last-login-tracker'"
    exit 1
fi

# ==== Test 2: Browser Flow に SPI 組込 ====
log_test "Test 2: Browser Flow の複製 + last-login-tracker 組込"

# 既定 'browser' フローを複製
COPY_FLOW_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    "${KC_URL}/admin/realms/${KC_REALM}/authentication/flows/browser/copy" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{"newName":"browser-with-last-login"}')

HTTP_CODE=$(echo "$COPY_FLOW_RESPONSE" | tail -1)
if [ "$HTTP_CODE" = "201" ] || [ "$HTTP_CODE" = "409" ]; then
    log_ok "Browser flow copied (or already exists)"
else
    log_warn "Flow copy HTTP $HTTP_CODE"
fi

# フローの Executions を確認
EXECUTIONS=$(curl -s "${KC_URL}/admin/realms/${KC_REALM}/authentication/flows/browser-with-last-login/executions" \
             -H "Authorization: Bearer ${TOKEN}")
log_info "Current executions:"
echo "$EXECUTIONS" | jq '.[] | {index: .index, requirement: .requirement, displayName: .displayName, providerId: .providerId}'

# last-login-tracker を末尾に追加
log_test "Adding last-login-tracker to browser-with-last-login flow"
ADD_EXEC_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    "${KC_URL}/admin/realms/${KC_REALM}/authentication/flows/browser-with-last-login/executions/execution" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{"provider":"last-login-tracker"}')

HTTP_CODE=$(echo "$ADD_EXEC_RESPONSE" | tail -1)
if [ "$HTTP_CODE" = "201" ]; then
    log_ok "✅ 'last-login-tracker' を browser flow に追加"
else
    log_warn "Execution add HTTP $HTTP_CODE"
    echo "$ADD_EXEC_RESPONSE"
fi

# ==== Test 3: 事前状態確認（test-jit-user の last_login） ====
log_test "Test 3: 事前状態確認"
USER_ID=$(find_user_id "$TOKEN" "test-jit-user")
LAST_LOGIN_BEFORE=$(get_user_attribute "$TOKEN" "$USER_ID" "last_login")
log_info "Before login: user=test-jit-user, last_login=$LAST_LOGIN_BEFORE"

# ==== Test 4: 実際のログイン試行（Direct Access Grant） ====
log_test "Test 4: 実際のログイン試行（Direct Access Grant）"
log_warn "注意：Direct Access Grant は Browser Flow を通らないため、"
log_warn "  完全な V3' 検証にはブラウザ経由のログインが必要"
log_warn "  ここでは SPI のロード確認のみ実施"

LOGIN_RESPONSE=$(curl -s -X POST \
    "${KC_URL}/realms/${KC_REALM}/protocol/openid-connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "grant_type=password" \
    -d "client_id=poc-test-client" \
    -d "username=test-jit-user" \
    -d "password=test123")

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token // "NULL"')
if [ "$ACCESS_TOKEN" != "NULL" ]; then
    log_ok "Direct Access Grant ログイン成功"
else
    log_warn "Direct Access Grant ログイン失敗（Browser flow のみで動く可能性）"
fi

# 少し待って user_attribute を再確認
sleep 2

# 管理者トークン再取得（前のトークンが期限切れの可能性）
TOKEN=$(get_admin_token)
LAST_LOGIN_AFTER=$(get_user_attribute "$TOKEN" "$USER_ID" "last_login")
log_info "After login: user=test-jit-user, last_login=$LAST_LOGIN_AFTER"

if [ "$LAST_LOGIN_BEFORE" != "$LAST_LOGIN_AFTER" ] && [ "$LAST_LOGIN_AFTER" != "NULL" ]; then
    log_ok "✅ user_attribute.last_login が更新された"
    log_ok "  → Custom Authenticator SPI で setSingleAttribute が動作"
    log_ok "  → 案 B（Custom Authenticator SPI）採用確定"
else
    log_warn "❌ user_attribute.last_login が更新されなかった"
    log_warn "  → Direct Access Grant は Browser Flow を通らないため想定内"
    log_warn "  → 完全な検証には ブラウザ経由のログインで再テスト必要"
    log_warn "  → 手順："
    log_warn "     1. Realm Settings → Bindings → Browser Flow を"
    log_warn "        'browser-with-last-login' に変更"
    log_warn "     2. Account Console (${KC_URL}/realms/${KC_REALM}/account) にブラウザでアクセス"
    log_warn "     3. test-jit-user でログイン"
    log_warn "     4. 再度本スクリプトの Test 3 チェックを実行"
fi

# ==== 判定 ====
log_test "===================================================="
log_verdict "V3' 判定サマリ"
log_test "===================================================="
log_info "  Test 1: SPI ロード確認"
log_info "  Test 2: Browser Flow への組込"
log_info "  Test 3: 事前状態確認"
log_info "  Test 4: ログイン試行後の user_attribute 反映"
log_info ""
log_info "🔍 完全検証には手動でのブラウザログインが必要"
log_info "詳細ログを docs/verification-log.md に保存してください"
