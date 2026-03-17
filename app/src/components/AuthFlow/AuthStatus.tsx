import { useAuth } from '../../auth/AuthProvider';
import { externalIdpName } from '../../auth/config';
import styles from './AuthStatus.module.css';

export function AuthStatus() {
  const { user, isLoading, error, login, loginWithIdp, loginLocal, loginDr, loginDrWithIdp, logout, logoutFull, silentRenew, localEnabled, drEnabled } = useAuth();

  if (isLoading) {
    return (
      <div className={styles.container}>
        <p>認証状態を確認中...</p>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <h2>認証ステータス</h2>

      <div className={styles.statusRow}>
        <span className={styles.label}>状態:</span>
        <span className={user ? styles.authenticated : styles.unauthenticated}>
          {user ? '認証済み' : '未認証'}
        </span>
      </div>

      {user && (
        <>
          <div className={styles.statusRow}>
            <span className={styles.label}>ユーザー:</span>
            <span>{user.profile.email || user.profile.sub}</span>
          </div>
          <div className={styles.statusRow}>
            <span className={styles.label}>Subject (sub):</span>
            <code className={styles.code}>{user.profile.sub}</code>
          </div>
          <div className={styles.statusRow}>
            <span className={styles.label}>認証方式:</span>
            <span>
              {user.profile.identities
                ? `フェデレーション（${(user.profile.identities as Array<{ providerName: string }>)[0]?.providerName || '不明'}）`
                : 'ローカル（Hosted UI）'}
            </span>
          </div>
          {user.profile['cognito:groups'] && (
            <div className={styles.statusRow}>
              <span className={styles.label}>Groups:</span>
              <span>
                {(user.profile['cognito:groups'] as string[]).join(', ')}
              </span>
            </div>
          )}
          <div className={styles.statusRow}>
            <span className={styles.label}>トークン期限:</span>
            <span>
              {user.expires_at
                ? new Date(user.expires_at * 1000).toLocaleString('ja-JP')
                : 'N/A'}
            </span>
          </div>
        </>
      )}

      {error && <p className={styles.error}>{error}</p>}

      <div className={styles.actions}>
        {!user ? (
          <>
            <button className={styles.loginBtn} onClick={login}>
              ログイン（Hosted UI）
            </button>
            {externalIdpName && (
              <button
                className={styles.federationBtn}
                onClick={() => loginWithIdp(externalIdpName)}
              >
                ログイン（{externalIdpName}）
              </button>
            )}
            {localEnabled && (
              <button className={styles.localBtn} onClick={loginLocal}>
                ログイン（ローカルCognito）
              </button>
            )}
            {drEnabled && (
              <>
                <button className={styles.drBtn} onClick={loginDr}>
                  ログイン（DR 大阪）
                </button>
                {externalIdpName && (
                  <button className={styles.drBtn} onClick={loginDrWithIdp}>
                    ログイン（DR 大阪 + {externalIdpName}）
                  </button>
                )}
              </>
            )}
          </>
        ) : (
          <>
            <button className={styles.renewBtn} onClick={silentRenew}>
              トークン更新
            </button>
            <button className={styles.logoutBtn} onClick={logout}>
              ログアウト
            </button>
            <button className={styles.logoutFullBtn} onClick={logoutFull}>
              完全ログアウト（SSO破棄）
            </button>
          </>
        )}
      </div>
    </div>
  );
}
