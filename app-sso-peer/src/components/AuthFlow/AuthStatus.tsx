import { useAuth } from '../../auth/AuthProvider';
import styles from './AuthStatus.module.css';

export function AuthStatus() {
  const { user, isLoading, error, login, logout, silentRenew } = useAuth();

  if (isLoading) {
    return (
      <div className={styles.container}>
        <p>認証状態を確認中...</p>
      </div>
    );
  }

  // Keycloak の realm_access からロールを取得
  const realmAccess = (user?.profile as Record<string, unknown>)?.realm_access as
    | { roles?: string[] }
    | undefined;
  const roles = realmAccess?.roles?.filter((r) => !r.startsWith('default-roles-')) || [];

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
            <span>{user.profile.email || user.profile.preferred_username || user.profile.sub}</span>
          </div>
          <div className={styles.statusRow}>
            <span className={styles.label}>Subject (sub):</span>
            <code className={styles.code}>{user.profile.sub}</code>
          </div>
          <div className={styles.statusRow}>
            <span className={styles.label}>Issuer:</span>
            <code className={styles.code}>{user.profile.iss}</code>
          </div>
          {roles.length > 0 && (
            <div className={styles.statusRow}>
              <span className={styles.label}>Roles:</span>
              <span>{roles.join(', ')}</span>
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
          <button className={styles.loginBtn} onClick={login}>
            ログイン（Keycloak）
          </button>
        ) : (
          <>
            <button className={styles.renewBtn} onClick={silentRenew}>
              トークン更新
            </button>
            <button className={styles.logoutBtn} onClick={logout}>
              ログアウト
            </button>
          </>
        )}
      </div>
    </div>
  );
}
