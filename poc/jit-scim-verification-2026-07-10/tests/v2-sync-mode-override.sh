#!/bin/bash
# V2 検証：Sync Mode Override（Mapper 単位 syncMode = IMPORT）
#
# 一次資料背景:
# - E-11: Sync Mode 4 モード（Legacy / Import / Force / Inherit）
# - E-12: Per-Mapper syncMode は Keycloak 10+ で対応済（extra_config）
#
# 検証項目:
#   1. IdP 作成（Sync Mode = FORCE）
#   2. Attribute Mapper 作成（Mapper 単位 syncMode = IMPORT）
#   3. Realm 設定確認：Mapper 単位の syncMode が実際に override されるか
#
# 期待結果:
#   ✅ 一次資料上、技術的に可能（E-12）
#   ✅ Terraform provider でも extra_config でサポート済み
#   PoC ではプログラム的に IdP + Mapper 作成し、設定が保存されるか確認

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

log_test "===================================================="
log_test "V2: Sync Mode Override 検証"
log_test "===================================================="

wait_for_keycloak || exit 1
TOKEN=$(get_admin_token)
log_ok "Admin token acquired"

# ==== Test 1: Test IdP 作成（Sync Mode = FORCE） ====
log_test "Test 1: Test OIDC IdP 作成（Sync Mode = FORCE）"

IDP_JSON='{
  "alias": "v2-test-idp",
  "displayName": "V2 Test IdP",
  "providerId": "oidc",
  "enabled": true,
  "config": {
    "syncMode": "FORCE",
    "authorizationUrl": "https://example.com/auth",
    "tokenUrl": "https://example.com/token",
    "clientId": "test",
    "clientSecret": "test-secret"
  }
}'

IDP_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    "${KC_URL}/admin/realms/${KC_REALM}/identity-provider/instances" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d "$IDP_JSON")

HTTP_CODE=$(echo "$IDP_RESPONSE" | tail -1)
if [ "$HTTP_CODE" = "201" ]; then
    log_ok "IdP 'v2-test-idp' created with Sync Mode = FORCE"
elif [ "$HTTP_CODE" = "409" ]; then
    log_warn "IdP already exists (previous run), reusing"
else
    log_error "IdP creation failed (HTTP $HTTP_CODE)"
    echo "$IDP_RESPONSE"
    exit 1
fi

# ==== Test 2: 通常の Attribute Mapper（syncMode 未指定、Realm デフォルト = FORCE を継承） ====
log_test "Test 2: 通常 Mapper 作成（syncMode 未指定、Inherit）"

MAPPER_DEFAULT_JSON='{
  "name": "map-email-default",
  "identityProviderAlias": "v2-test-idp",
  "identityProviderMapper": "oidc-user-attribute-idp-mapper",
  "config": {
    "claim": "email",
    "user.attribute": "email"
  }
}'

MAPPER_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    "${KC_URL}/admin/realms/${KC_REALM}/identity-provider/instances/v2-test-idp/mappers" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d "$MAPPER_DEFAULT_JSON")

HTTP_CODE=$(echo "$MAPPER_RESPONSE" | tail -1)
if [ "$HTTP_CODE" = "201" ]; then
    log_ok "Default mapper created"
elif [ "$HTTP_CODE" = "409" ]; then
    log_warn "Mapper already exists"
fi

# ==== Test 3: Sync Mode Override Mapper（extra_config で syncMode = IMPORT） ====
log_test "Test 3: Sync Mode Override Mapper 作成（syncMode = IMPORT）"

MAPPER_OVERRIDE_JSON='{
  "name": "protect-scim-active",
  "identityProviderAlias": "v2-test-idp",
  "identityProviderMapper": "hardcoded-attribute-idp-mapper",
  "config": {
    "syncMode": "IMPORT",
    "attribute": "scim_active",
    "attribute.value": "true"
  }
}'

MAPPER_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
    "${KC_URL}/admin/realms/${KC_REALM}/identity-provider/instances/v2-test-idp/mappers" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d "$MAPPER_OVERRIDE_JSON")

HTTP_CODE=$(echo "$MAPPER_RESPONSE" | tail -1)
if [ "$HTTP_CODE" = "201" ]; then
    log_ok "✅ Sync Mode Override Mapper created successfully"
    log_ok "  → E-12（Per-Mapper syncMode Keycloak 10+）と整合"
elif [ "$HTTP_CODE" = "409" ]; then
    log_warn "Override mapper already exists"
else
    log_error "❌ Sync Mode Override Mapper creation failed (HTTP $HTTP_CODE)"
    echo "$MAPPER_RESPONSE"
fi

# ==== Test 4: Mapper 設定確認（syncMode 値が実際に保存されているか） ====
log_test "Test 4: Mapper 設定確認"
MAPPERS=$(curl -s "${KC_URL}/admin/realms/${KC_REALM}/identity-provider/instances/v2-test-idp/mappers" \
          -H "Authorization: Bearer ${TOKEN}")

echo "$MAPPERS" | jq '.'

OVERRIDE_MAPPER=$(echo "$MAPPERS" | jq '.[] | select(.name == "protect-scim-active")')
if [ -n "$OVERRIDE_MAPPER" ]; then
    SYNC_MODE=$(echo "$OVERRIDE_MAPPER" | jq -r '.config.syncMode // "NOT_SET"')
    if [ "$SYNC_MODE" = "IMPORT" ]; then
        log_ok "✅ syncMode = IMPORT が Mapper 設定に保存されている"
        log_ok "  → V2 判定：技術的に override 可能（一次資料 E-12 と整合）"
    else
        log_error "❌ syncMode = $SYNC_MODE（期待: IMPORT）"
    fi
else
    log_error "Override mapper not found in list"
fi

# ==== 判定 ====
log_test "===================================================="
log_verdict "V2 判定サマリ"
log_test "===================================================="
log_info "  Test 1: IdP 作成（Sync Mode = FORCE）"
log_info "  Test 2: 通常 Mapper 作成"
log_info "  Test 3: Sync Mode Override Mapper 作成"
log_info "  Test 4: 設定保存確認"
log_info ""
log_info "実動作の完全確認には実 JIT ログインが必要（本 PoC では設定検証のみ）"
log_info "詳細ログを docs/verification-log.md に保存してください"
