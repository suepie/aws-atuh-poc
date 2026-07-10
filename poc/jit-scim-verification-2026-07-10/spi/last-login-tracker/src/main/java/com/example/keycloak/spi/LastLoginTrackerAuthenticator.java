package com.example.keycloak.spi;

import org.jboss.logging.Logger;
import org.keycloak.authentication.AuthenticationFlowContext;
import org.keycloak.authentication.Authenticator;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.RealmModel;
import org.keycloak.models.UserModel;

/**
 * V3' 検証：Custom Authenticator SPI 経由の user_attribute.last_login 書込
 *
 * 背景（一次資料）：
 * - E-8 Keycloak Issue #14942 (Closed as not planned):
 *   Event Listener SPI 内の setSingleAttribute() が動かない
 * - E-9 Keycloak Issue #22902 (Open):
 *   enlistAfterCompletion() でも Error イベント時に ConcurrentModificationException
 * - 本 SPI は Authentication Flow 内で動作するため、transaction 制御が明示的で
 *   確実に user_attribute への書込が保証される（案 B）
 *
 * 実装：Browser Flow の末尾に組込
 * debounce：1 日以内の再ログインは書込スキップ（性能配慮）
 */
public class LastLoginTrackerAuthenticator implements Authenticator {

    private static final Logger LOG = Logger.getLogger(LastLoginTrackerAuthenticator.class);

    // debounce 期間：1 日（epoch ms）
    private static final long DEBOUNCE_MS = 86_400_000L;

    // 書き込む user_attribute 名
    private static final String ATTR_LAST_LOGIN = "last_login";

    @Override
    public void authenticate(AuthenticationFlowContext context) {
        UserModel user = context.getUser();

        if (user == null) {
            LOG.warn("LastLoginTracker: user is null, skipping");
            context.attempted();
            return;
        }

        try {
            long nowMs = System.currentTimeMillis();
            String lastLoginStr = user.getFirstAttribute(ATTR_LAST_LOGIN);

            boolean shouldUpdate = false;

            if (lastLoginStr == null || lastLoginStr.isEmpty()) {
                // 初回書込
                shouldUpdate = true;
                LOG.infof("LastLoginTracker: initial write for user=%s, now=%d",
                          user.getUsername(), nowMs);
            } else {
                try {
                    long lastLoginMs = Long.parseLong(lastLoginStr);
                    long diffMs = nowMs - lastLoginMs;

                    if (diffMs > DEBOUNCE_MS) {
                        // 1 日以上経過 → 更新
                        shouldUpdate = true;
                        LOG.infof("LastLoginTracker: update for user=%s, last=%d, diff=%dms",
                                  user.getUsername(), lastLoginMs, diffMs);
                    } else {
                        // debounce 中 → スキップ
                        LOG.debugf("LastLoginTracker: debounce skip for user=%s, diff=%dms",
                                   user.getUsername(), diffMs);
                    }
                } catch (NumberFormatException e) {
                    // 不正な値 → 上書き
                    shouldUpdate = true;
                    LOG.warnf("LastLoginTracker: invalid last_login value '%s' for user=%s, overwriting",
                              lastLoginStr, user.getUsername());
                }
            }

            if (shouldUpdate) {
                user.setSingleAttribute(ATTR_LAST_LOGIN, String.valueOf(nowMs));
                LOG.infof("LastLoginTracker: wrote last_login=%d for user=%s",
                          nowMs, user.getUsername());
            }

        } catch (Exception e) {
            // 認証は絶対に通す（PoC では例外を logger に）
            LOG.error("LastLoginTracker: failed to update last_login", e);
        }

        // 次の Authenticator へ
        context.success();
    }

    @Override
    public void action(AuthenticationFlowContext context) {
        // このオーセンティケーターはユーザ操作を求めない
        context.success();
    }

    @Override
    public boolean requiresUser() {
        // 認証済み user が必要
        return true;
    }

    @Override
    public boolean configuredFor(KeycloakSession session, RealmModel realm, UserModel user) {
        // 常に有効
        return true;
    }

    @Override
    public void setRequiredActions(KeycloakSession session, RealmModel realm, UserModel user) {
        // 追加アクション不要
    }

    @Override
    public void close() {
        // クリーンアップ不要
    }
}
