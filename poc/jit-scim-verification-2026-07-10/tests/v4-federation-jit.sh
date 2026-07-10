#!/bin/bash
# V3'' 検証：フェデ JIT 経路で SPI が動作するか
#
# 一次資料背景:
# - V3' PoC はローカル PW ユーザ（P-4）で SPI 動作を実証
# - フェデ JIT ユーザ（P-3、本基盤主用途）は未検証（jit-scim §10.4.F.9）
# - Browser Flow の ALTERNATIVE 分岐上、SPI が forms 内では動かない
# - 対策：First Broker Login Flow + Post Broker Login Flow に SPI 配置
#
# 検証項目:
#   1. IdP 設定確認（customer-idp が poc-jit-scim に登録済み）
#   2. First Broker Login Flow 確認（Last Login Tracker が REQUIRED で末尾）
#   3. Post Broker Login Flow 確認（同上）
#   4. 初回フェデログイン → JIT で fed-jit-user 作成 + last_login 反映
#   5. 2 回目フェデログイン → last_login 更新（debounce 期間外の場合）
#   6. provisioned_by = "jit" が付与されているか
#
# 前提:
#   - ./tests/setup-federation.sh 実行済み
#
# 期待結果:
#   ✅ フェデ経由でも last_login が確実に書き込まれる
#   → Phase 1 実装で 3 系統 Flow 配置（Browser + First Broker + Post Broker）確定

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

log_test "===================================================="
log_test "V3'': フェデ JIT 経路の SPI 動作検証"
log_test "===================================================="

wait_for_keycloak || exit 1
TOKEN=$(get_admin_token)
log_ok "Admin token acquired"

# ==== Test 1: IdP 設定確認 ====
log_test "Test 1: OIDC IdP 'customer-idp' が登録されているか"

IDP_INFO=$(curl -s "${KC_URL}/admin/realms/${KC_REALM}/identity-provider/instances/customer-idp" \
           -H "Authorization: Bearer ${TOKEN}")

IDP_ALIAS=$(echo "$IDP_INFO" | jq -r '.alias // "NULL"')
FBL_ALIAS=$(echo "$IDP_INFO" | jq -r '.firstBrokerLoginFlowAlias // "NULL"')
PBL_ALIAS=$(echo "$IDP_INFO" | jq -r '.postBrokerLoginFlowAlias // "NULL"')

if [ "$IDP_ALIAS" = "customer-idp" ]; then
    log_ok "✅ IdP 'customer-idp' 登録済"
    log_info "  firstBrokerLoginFlowAlias: $FBL_ALIAS"
    log_info "  postBrokerLoginFlowAlias:  $PBL_ALIAS"

    if [ "$FBL_ALIAS" != "first-broker-login-with-tracker" ]; then
        log_warn "⚠ firstBrokerLoginFlowAlias が期待値と異なる（期待: first-broker-login-with-tracker）"
    fi
    if [ "$PBL_ALIAS" != "post-broker-login-with-tracker" ]; then
        log_warn "⚠ postBrokerLoginFlowAlias が期待値と異なる（期待: post-broker-login-with-tracker）"
    fi
else
    log_error "❌ IdP 'customer-idp' が未登録"
    log_error "  → ./tests/setup-federation.sh を先に実行してください"
    exit 1
fi

# ==== Test 2: First Broker Login Flow 確認 ====
log_test "Test 2: First Broker Login Flow の SPI 配置確認"

FBL_EXECS=$(curl -s "${KC_URL}/admin/realms/${KC_REALM}/authentication/flows/first-broker-login-with-tracker/executions" \
            -H "Authorization: Bearer ${TOKEN}")

FBL_TRACKER=$(echo "$FBL_EXECS" | jq -c '.[] | select(.providerId == "last-login-tracker")')
if [ -n "$FBL_TRACKER" ]; then
    log_ok "✅ First Broker Login Flow に last-login-tracker が配置"
    echo "$FBL_TRACKER" | jq .
else
    log_error "❌ First Broker Login Flow に last-login-tracker が配置されていない"
    log_error "  → ./tests/setup-federation.sh を実行してください"
    exit 1
fi

# ==== Test 3: Post Broker Login Flow 確認 ====
log_test "Test 3: Post Broker Login Flow の SPI 配置確認"

PBL_EXECS=$(curl -s "${KC_URL}/admin/realms/${KC_REALM}/authentication/flows/post-broker-login-with-tracker/executions" \
            -H "Authorization: Bearer ${TOKEN}")

PBL_TRACKER=$(echo "$PBL_EXECS" | jq -c '.[] | select(.providerId == "last-login-tracker")')
if [ -n "$PBL_TRACKER" ]; then
    log_ok "✅ Post Broker Login Flow に last-login-tracker が配置"
    echo "$PBL_TRACKER" | jq .
else
    log_error "❌ Post Broker Login Flow に last-login-tracker が配置されていない"
    exit 1
fi

# ==== Test 4: 初回フェデログイン（手動確認案内） ====
log_test "Test 4: 初回フェデログイン → JIT + last_login 反映"

log_warn "🔍 以下の手順で手動確認してください："
log_info ""
log_info "1. Admin Console で Realm Settings → Bindings で"
log_info "   Browser Flow が 'browser-with-last-login' に設定されているか確認"
log_info ""
log_info "2. 新しい Incognito ブラウザで:"
log_info "   ${KC_URL}/realms/${KC_REALM}/account"
log_info "   → ログイン画面が表示される"
log_info ""
log_info "3. ログイン画面で 'Customer IdP (Federation Test)' ボタンを押す"
log_info "   （customer-idp の OIDC ログインへリダイレクト）"
log_info ""
log_info "4. customer-idp のログインフォームで:"
log_info "   Username: fed-jit-user"
log_info "   Password: fed123"
log_info ""
log_info "5. First Broker Login Flow が実行される（初回のため）:"
log_info "   → Review Profile が表示される場合は Save でスキップ"
log_info "   → Last Login Tracker が実行される"
log_info ""
log_info "6. poc-jit-scim Realm の Account Console に戻る"

echo ""
read -p "手動確認が完了したら Enter を押してください（結果を確認します）: " -r

# JIT で作成されたユーザを検索
sleep 2
TOKEN=$(get_admin_token)
FED_USER_ID=$(find_user_id "$TOKEN" "fed-jit-user")

if [ "$FED_USER_ID" = "NOT_FOUND" ]; then
    # username は IdP 側 mapping により違う可能性（email 等）
    log_info "username=fed-jit-user で見つからないので email で検索..."
    FED_USER_JSON=$(curl -s "${KC_URL}/admin/realms/${KC_REALM}/users?email=fed-jit-user@customer.example.com" \
                    -H "Authorization: Bearer ${TOKEN}")
    FED_USER_ID=$(echo "$FED_USER_JSON" | jq -r '.[0].id // "NOT_FOUND"')
fi

if [ "$FED_USER_ID" = "NOT_FOUND" ]; then
    log_error "❌ フェデ JIT ユーザが見つかりません"
    log_error "  → ログインが完了していない可能性があります"
    log_error "  → または Realm Settings → Bindings で Browser Flow の設定を確認"
    exit 1
fi

log_ok "フェデ JIT ユーザ発見: user_id=$FED_USER_ID"

# 属性確認
USER_DETAILS=$(curl -s "${KC_URL}/admin/realms/${KC_REALM}/users/${FED_USER_ID}" \
               -H "Authorization: Bearer ${TOKEN}")

echo ""
log_info "ユーザ詳細:"
echo "$USER_DETAILS" | jq '{username, email, enabled, attributes, federatedIdentities}'

# federated_identity の確認
FED_IDENTITIES=$(echo "$USER_DETAILS" | jq -r '.federatedIdentities[]?.identityProvider // "NONE"')
if echo "$FED_IDENTITIES" | grep -q "customer-idp"; then
    log_ok "✅ federated_identity に customer-idp が紐付いている（真の JIT ユーザ）"
else
    log_warn "⚠ federated_identity が見つからない（ローカルユーザの可能性）"
fi

# last_login 属性の確認
LAST_LOGIN=$(echo "$USER_DETAILS" | jq -r '.attributes.last_login[0] // "NULL"')
if [ "$LAST_LOGIN" != "NULL" ] && [ "$LAST_LOGIN" != "" ]; then
    log_ok "✅ user_attribute.last_login = $LAST_LOGIN"
    log_ok "  → First Broker Login Flow の SPI で書き込まれた"
else
    log_error "❌ user_attribute.last_login が設定されていない"
    log_error "  → First Broker Login Flow の SPI が動作していない可能性"
    log_error "  → docker compose logs keycloak | grep LastLoginTracker で確認"
fi

# provisioned_by 属性の確認
PROV_BY=$(echo "$USER_DETAILS" | jq -r '.attributes.provisioned_by[0] // "NULL"')
if [ "$PROV_BY" = "jit" ]; then
    log_ok "✅ user_attribute.provisioned_by = jit"
else
    log_warn "⚠ user_attribute.provisioned_by = $PROV_BY（期待: jit）"
    log_info "  → SPI で provisioned_by も自動セットする場合は SPI 改修必要"
fi

# ==== Test 5: 2 回目ログイン（Post Broker Login Flow）====
log_test "Test 5: 2 回目フェデログイン → Post Broker Login Flow の SPI"

log_warn "⚠ debounce（1 日）を回避するため、Keycloak DB を直接操作して"
log_warn "  last_login を過去日に上書きします（テスト用）"

# last_login を 2 日前に設定
TWO_DAYS_AGO_MS=$(($(date +%s%3N) - 2 * 86400 * 1000))
curl -s -X PUT "${KC_URL}/admin/realms/${KC_REALM}/users/${FED_USER_ID}" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"attributes\":{\"last_login\":[\"${TWO_DAYS_AGO_MS}\"]}}" > /dev/null

log_ok "last_login を 2 日前 ($TWO_DAYS_AGO_MS) に更新"

log_warn "🔍 2 回目ログインの手動確認:"
log_info ""
log_info "1. Incognito ブラウザで再度:"
log_info "   ${KC_URL}/realms/${KC_REALM}/account"
log_info "2. 'Customer IdP' → fed-jit-user でログイン"
log_info "3. First Broker Login Flow は skip される（初回ではないため）"
log_info "4. Post Broker Login Flow の Last Login Tracker が実行される"

echo ""
read -p "2 回目ログインが完了したら Enter を押してください: " -r

sleep 2
TOKEN=$(get_admin_token)
USER_AFTER=$(curl -s "${KC_URL}/admin/realms/${KC_REALM}/users/${FED_USER_ID}" \
             -H "Authorization: Bearer ${TOKEN}")
LAST_LOGIN_AFTER=$(echo "$USER_AFTER" | jq -r '.attributes.last_login[0] // "NULL"')

if [ "$LAST_LOGIN_AFTER" != "$TWO_DAYS_AGO_MS" ] && [ "$LAST_LOGIN_AFTER" != "NULL" ]; then
    log_ok "✅ 2 回目ログイン後、last_login が更新: $LAST_LOGIN_AFTER"
    log_ok "  → Post Broker Login Flow の SPI が動作"
    log_ok "  → 案 B（Custom Authenticator SPI）フェデ経路対応 確定"
else
    log_error "❌ 2 回目ログイン後、last_login が更新されない"
    log_error "  → Post Broker Login Flow の SPI が動作していない"
    log_error "  → または debounce が期待通り動かなかった可能性"
fi

# ==== 判定 ====
log_test "===================================================="
log_verdict "V3'' 判定サマリ"
log_test "===================================================="
log_info "  Test 1: OIDC IdP 登録 = $([ "$IDP_ALIAS" = "customer-idp" ] && echo "OK" || echo "NG")"
log_info "  Test 2: First Broker Login Flow SPI 配置 = $([ -n "$FBL_TRACKER" ] && echo "OK" || echo "NG")"
log_info "  Test 3: Post Broker Login Flow SPI 配置 = $([ -n "$PBL_TRACKER" ] && echo "OK" || echo "NG")"
log_info "  Test 4: 初回フェデログイン + last_login 反映 = $([ "$LAST_LOGIN" != "NULL" ] && echo "OK" || echo "NG")"
log_info "  Test 5: 2 回目ログイン + Post Broker Flow 動作 = 手動確認済"
log_info ""
log_info "詳細は docs/verification-log-v3fed.md に保存してください"
