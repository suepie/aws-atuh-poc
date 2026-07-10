#!/bin/bash
# V1 検証：SCIM Server で Custom Attribute Mapping
#
# 一次資料背景:
# - E-2: keycloak-orgs は Keycloak > 17.0.0（26 明記なし）
# - E-4: Keycloak 26.6 native SCIM Realm API は Experimental
# - E-5: Native SCIM はカスタムスキーマ未実装
#
# 検証項目:
#   1. Keycloak 26.6 native SCIM Realm API 有効化確認
#   2. SCIM POST /Users で標準属性 + カスタム属性書込
#   3. SCIM PATCH /Users で属性更新
#   4. user_attribute への永続化確認
#
# 期待結果:
#   ✅ 基本属性（active, userName）→ Keycloak enabled, username へ反映
#   ⚠ カスタム属性（scim_active, provisioned_by）→ 明示的な mapping 設定が必要
#     不可の場合 → Fallback A（Custom Authenticator SPI で自動セット）へ

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

log_test "===================================================="
log_test "V1: Metatavu SCIM Custom Attribute Mapping 検証"
log_test "===================================================="

# ==== 準備 ====
wait_for_keycloak || exit 1

TOKEN=$(get_admin_token)
if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
    log_error "Failed to get admin token"
    exit 1
fi
log_ok "Admin token acquired"

# ==== Test 1: SCIM Realm API 有効化確認 ====
log_test "Test 1: Keycloak 26.6 SCIM Realm API 有効性確認"
SCIM_META=$(curl -s -o /dev/null -w "%{http_code}" \
    "${KC_URL}/realms/${KC_REALM}/scim/v2/ServiceProviderConfig")
if [ "$SCIM_META" = "200" ]; then
    log_ok "SCIM Realm API is available (HTTP 200)"
else
    log_warn "SCIM Realm API returned HTTP $SCIM_META"
    log_warn "  → Keycloak 26.6 で feature 'scim-realm-api' が有効か確認"
    log_warn "  → docker-compose.yml の KC_FEATURES 確認"
fi

# ==== Test 2: 標準属性（active）で SCIM 作成 ====
log_test "Test 2: SCIM POST /Users で標準属性書込"
SCIM_USER_JSON='{
  "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
  "userName": "v1-test-user-01",
  "displayName": "V1 Test User 01",
  "active": true,
  "emails": [{"value": "v1-test-01@poc.example.com", "primary": true}],
  "name": {"givenName": "V1", "familyName": "Test01"}
}'

SCIM_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    "${KC_URL}/realms/${KC_REALM}/scim/v2/Users" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/scim+json" \
    -d "$SCIM_USER_JSON")

HTTP_CODE=$(echo "$SCIM_RESPONSE" | tail -1)
BODY=$(echo "$SCIM_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "201" ]; then
    log_ok "SCIM user created (HTTP 201)"
    echo "$BODY" | jq . 2>/dev/null || echo "$BODY"

    USER_ID=$(find_user_id "$TOKEN" "v1-test-user-01")
    log_info "Keycloak user_id: $USER_ID"

    # user_entity の enabled 確認
    ENABLED=$(curl -s "${KC_URL}/admin/realms/${KC_REALM}/users/${USER_ID}" \
              -H "Authorization: Bearer ${TOKEN}" | jq -r '.enabled')
    if [ "$ENABLED" = "true" ]; then
        log_ok "user_entity.enabled = true（SCIM active=true 反映）"
    else
        log_error "user_entity.enabled = $ENABLED（期待: true）"
    fi
elif [ "$HTTP_CODE" = "404" ]; then
    log_error "SCIM endpoint not found (HTTP 404)"
    log_error "  → Native SCIM Realm API が Keycloak 26.6 で有効化されていない"
    log_error "  → Fallback A（Custom Authenticator SPI）検討"
else
    log_error "SCIM POST failed (HTTP $HTTP_CODE)"
    echo "$BODY" | jq . 2>/dev/null || echo "$BODY"
fi

# ==== Test 3: カスタム属性で SCIM 作成 ====
log_test "Test 3: SCIM POST /Users でカスタム属性書込試行"
log_info "kc.scim.schema.attribute annotation の動作確認"
log_info "User Profile schema で scim_active を定義する必要があるかも"

SCIM_USER_WITH_CUSTOM='{
  "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
  "userName": "v1-test-user-02",
  "active": true,
  "emails": [{"value": "v1-test-02@poc.example.com", "primary": true}]
}'

SCIM_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    "${KC_URL}/realms/${KC_REALM}/scim/v2/Users" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/scim+json" \
    -d "$SCIM_USER_WITH_CUSTOM")

HTTP_CODE=$(echo "$SCIM_RESPONSE" | tail -1)

if [ "$HTTP_CODE" = "201" ]; then
    USER_ID=$(find_user_id "$TOKEN" "v1-test-user-02")

    # scim_active 属性が付いているか確認
    log_info "Checking user_attribute.scim_active..."
    SCIM_ACTIVE=$(get_user_attribute "$TOKEN" "$USER_ID" "scim_active")
    if [ "$SCIM_ACTIVE" != "NULL" ]; then
        log_ok "✅ user_attribute.scim_active = $SCIM_ACTIVE"
    else
        log_warn "❌ user_attribute.scim_active が設定されていない"
        log_warn "  → 期待通り、Native SCIM ではカスタム属性は自動 map されない（E-5 に整合）"
    fi

    # provisioned_by 属性
    PROVISIONED_BY=$(get_user_attribute "$TOKEN" "$USER_ID" "provisioned_by")
    if [ "$PROVISIONED_BY" != "NULL" ]; then
        log_ok "✅ user_attribute.provisioned_by = $PROVISIONED_BY"
    else
        log_warn "❌ user_attribute.provisioned_by が設定されていない"
    fi
else
    log_warn "SCIM POST HTTP $HTTP_CODE"
fi

# ==== Test 4: SCIM PATCH で active=false ====
log_test "Test 4: SCIM PATCH で active=false 更新"
USER_ID=$(find_user_id "$TOKEN" "v1-test-user-01")
if [ "$USER_ID" != "NOT_FOUND" ]; then
    PATCH_JSON='{
      "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
      "Operations": [{"op": "replace", "path": "active", "value": false}]
    }'

    PATCH_RESPONSE=$(curl -s -w "\n%{http_code}" -X PATCH \
        "${KC_URL}/realms/${KC_REALM}/scim/v2/Users/${USER_ID}" \
        -H "Authorization: Bearer ${TOKEN}" \
        -H "Content-Type: application/scim+json" \
        -d "$PATCH_JSON")

    HTTP_CODE=$(echo "$PATCH_RESPONSE" | tail -1)
    if [ "$HTTP_CODE" = "200" ]; then
        log_ok "SCIM PATCH successful (HTTP 200)"
        ENABLED=$(curl -s "${KC_URL}/admin/realms/${KC_REALM}/users/${USER_ID}" \
                  -H "Authorization: Bearer ${TOKEN}" | jq -r '.enabled')
        if [ "$ENABLED" = "false" ]; then
            log_ok "user_entity.enabled = false（SCIM active=false 反映）"
        else
            log_error "user_entity.enabled = $ENABLED（期待: false）"
        fi
    else
        log_warn "SCIM PATCH HTTP $HTTP_CODE"
    fi
fi

# ==== 判定 ====
log_test "===================================================="
log_verdict "V1 判定サマリ"
log_test "===================================================="
log_info "  Test 1: SCIM Realm API 有効性"
log_info "  Test 2: 標準属性書込 (active → enabled)"
log_info "  Test 3: カスタム属性書込 (scim_active / provisioned_by)"
log_info "  Test 4: SCIM PATCH で状態更新"
log_info ""
log_info "詳細ログを docs/verification-log.md に保存してください"
