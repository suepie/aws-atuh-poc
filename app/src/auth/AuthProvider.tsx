import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { User, UserManager } from 'oidc-client-ts';
import { oidcConfig } from './config';
import { localOidcConfig, localCognitoEnabled } from './localConfig';

// ログエントリの型
export interface AuthLogEntry {
  timestamp: Date;
  event: string;
  detail: string;
  data?: unknown;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  error: string | null;
  logs: AuthLogEntry[];
  userManager: UserManager | null;
  localUserManager: UserManager | null;
  login: () => Promise<void>;
  loginWithIdp: (idpName: string) => Promise<void>;
  loginLocal: () => Promise<void>;
  logout: () => Promise<void>;
  logoutFull: () => Promise<void>;
  silentRenew: () => Promise<void>;
  localEnabled: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [logs, setLogs] = useState<AuthLogEntry[]>([]);
  const userManagerRef = useRef<UserManager | null>(null);
  const localUserManagerRef = useRef<UserManager | null>(null);

  const addLog = useCallback((event: string, detail: string, data?: unknown) => {
    setLogs((prev) => [
      ...prev,
      { timestamp: new Date(), event, detail, data },
    ]);
  }, []);

  // UserManager初期化
  useEffect(() => {
    const mgr = new UserManager(oidcConfig);
    userManagerRef.current = mgr;

    // イベントリスナー登録
    mgr.events.addUserLoaded((u) => {
      setUser(u);
      addLog('UserLoaded', 'トークンが取得/更新されました', {
        sub: u.profile.sub,
        expires_at: u.expires_at,
      });
    });

    mgr.events.addUserUnloaded(() => {
      setUser(null);
      addLog('UserUnloaded', 'ユーザー情報がクリアされました');
    });

    mgr.events.addAccessTokenExpiring(() => {
      addLog('AccessTokenExpiring', 'アクセストークンがまもなく期限切れです');
    });

    mgr.events.addAccessTokenExpired(() => {
      addLog('AccessTokenExpired', 'アクセストークンが期限切れになりました');
    });

    mgr.events.addSilentRenewError((err) => {
      addLog('SilentRenewError', 'サイレントリニューアルに失敗しました', {
        message: err.message,
      });
    });

    // ローカル Cognito UserManager 初期化
    if (localCognitoEnabled && localOidcConfig) {
      const localMgr = new UserManager(localOidcConfig);
      localUserManagerRef.current = localMgr;

      localMgr.events.addUserLoaded((u) => {
        setUser(u);
        addLog('LocalUserLoaded', 'ローカルCognitoのトークンが取得されました', {
          sub: u.profile.sub,
          issuer: 'local',
        });
      });

      addLog('Init', 'ローカル Cognito UserManager を初期化しました');
    }

    // 既存セッション確認（集約 → ローカルの順に確認）
    addLog('Init', 'OIDC UserManager を初期化中...');
    mgr
      .getUser()
      .then(async (existingUser) => {
        if (existingUser && !existingUser.expired) {
          setUser(existingUser);
          addLog('SessionRestored', '既存セッションを復元しました（集約Cognito）', {
            sub: existingUser.profile.sub,
            expires_at: existingUser.expires_at,
          });
        } else if (localUserManagerRef.current) {
          // ローカル Cognito のセッションも確認
          const localUser = await localUserManagerRef.current.getUser();
          if (localUser && !localUser.expired) {
            setUser(localUser);
            addLog('SessionRestored', '既存セッションを復元しました（ローカルCognito）', {
              sub: localUser.profile.sub,
              expires_at: localUser.expires_at,
            });
          } else {
            addLog('NoSession', '有効なセッションがありません');
          }
        } else {
          addLog('NoSession', '有効なセッションがありません');
        }
      })
      .catch((err) => {
        addLog('InitError', 'セッション確認でエラーが発生しました', {
          message: (err as Error).message,
        });
      })
      .finally(() => setIsLoading(false));

    return () => {
      mgr.events.removeUserLoaded(() => {});
      mgr.events.removeUserUnloaded(() => {});
    };
  }, [addLog]);

  const login = useCallback(async () => {
    if (!userManagerRef.current) return;
    try {
      addLog('LoginStart', 'ログインフローを開始します（Hosted UI へリダイレクト）');
      await userManagerRef.current.signinRedirect();
    } catch (err) {
      const message = (err as Error).message;
      setError(message);
      addLog('LoginError', `ログイン開始に失敗: ${message}`);
    }
  }, [addLog]);

  const loginLocal = useCallback(async () => {
    if (!localUserManagerRef.current) return;
    try {
      addLog('LocalLoginStart', 'ローカルCognitoログインを開始します（Hosted UI へリダイレクト）');
      await localUserManagerRef.current.signinRedirect();
    } catch (err) {
      const message = (err as Error).message;
      setError(message);
      addLog('LoginError', `ローカルログイン開始に失敗: ${message}`);
    }
  }, [addLog]);

  const isLocalUser = useCallback(() => {
    if (!user) return false;
    const localAuthority = import.meta.env.VITE_LOCAL_COGNITO_AUTHORITY || '';
    return localAuthority && user.profile.iss === localAuthority;
  }, [user]);

  const logout = useCallback(async () => {
    try {
      if (isLocalUser() && localUserManagerRef.current) {
        addLog('LogoutStart', 'ログアウトを開始します（ローカルCognito）');
        await localUserManagerRef.current.removeUser();
        setUser(null);
        const localDomain = import.meta.env.VITE_LOCAL_COGNITO_DOMAIN;
        const localClientId = import.meta.env.VITE_LOCAL_COGNITO_CLIENT_ID;
        const postLogoutUri = import.meta.env.VITE_POST_LOGOUT_URI || 'http://localhost:5173/';
        window.location.href = `${localDomain}/logout?client_id=${localClientId}&logout_uri=${encodeURIComponent(postLogoutUri)}`;
      } else if (userManagerRef.current) {
        addLog('LogoutStart', 'ログアウトを開始します（集約Cognito）');
        await userManagerRef.current.signoutRedirect();
      }
    } catch (err) {
      const message = (err as Error).message;
      setError(message);
      addLog('LogoutError', `ログアウトに失敗: ${message}`);
    }
  }, [addLog, isLocalUser]);

  const logoutFull = useCallback(async () => {
    try {
      addLog('FullLogoutStart', '完全ログアウトを開始します（全セッション破棄）');

      // 両方のUserManagerのセッションをクリア
      if (userManagerRef.current) await userManagerRef.current.removeUser();
      if (localUserManagerRef.current) await localUserManagerRef.current.removeUser();
      setUser(null);

      const postLogoutUri = import.meta.env.VITE_POST_LOGOUT_URI || 'http://localhost:5173/';

      if (isLocalUser()) {
        // ローカルCognitoのログアウト
        const localDomain = import.meta.env.VITE_LOCAL_COGNITO_DOMAIN;
        const localClientId = import.meta.env.VITE_LOCAL_COGNITO_CLIENT_ID;
        window.location.href = `${localDomain}/logout?client_id=${localClientId}&logout_uri=${encodeURIComponent(postLogoutUri)}`;
      } else {
        // 集約Cognito + Auth0 の完全ログアウト
        const auth0Domain = import.meta.env.VITE_AUTH0_DOMAIN;
        const cognitoDomain = import.meta.env.VITE_COGNITO_DOMAIN;
        const clientId = import.meta.env.VITE_COGNITO_CLIENT_ID;

        if (auth0Domain) {
          const cognitoLogoutUrl = `${cognitoDomain}/logout?client_id=${clientId}&logout_uri=${encodeURIComponent(postLogoutUri)}`;
          const auth0LogoutUrl = `https://${auth0Domain}/v2/logout?client_id=${import.meta.env.VITE_AUTH0_CLIENT_ID || ''}&returnTo=${encodeURIComponent(cognitoLogoutUrl)}`;
          window.location.href = auth0LogoutUrl;
        } else {
          window.location.href = `${cognitoDomain}/logout?client_id=${clientId}&logout_uri=${encodeURIComponent(postLogoutUri)}`;
        }
      }
    } catch (err) {
      const message = (err as Error).message;
      setError(message);
      addLog('FullLogoutError', `完全ログアウトに失敗: ${message}`);
    }
  }, [addLog]);

  const loginWithIdp = useCallback(async (idpName: string) => {
    if (!userManagerRef.current) return;
    try {
      addLog('FederationLoginStart', `フェデレーションログインを開始します（IdP: ${idpName}）`);
      await userManagerRef.current.signinRedirect({
        extraQueryParams: { identity_provider: idpName },
      });
    } catch (err) {
      const message = (err as Error).message;
      setError(message);
      addLog('LoginError', `フェデレーションログイン開始に失敗: ${message}`);
    }
  }, [addLog]);

  const silentRenew = useCallback(async () => {
    if (!userManagerRef.current) return;
    try {
      addLog('SilentRenewStart', 'サイレントリニューアルを開始します');
      const renewed = await userManagerRef.current.signinSilent();
      if (renewed) {
        setUser(renewed);
        addLog('SilentRenewSuccess', 'トークンが更新されました');
      }
    } catch (err) {
      const message = (err as Error).message;
      setError(message);
      addLog('SilentRenewError', `サイレントリニューアルに失敗: ${message}`);
    }
  }, [addLog]);

  return (
    <AuthContext.Provider
      value={{ user, isLoading, error, logs, userManager: userManagerRef.current, localUserManager: localUserManagerRef.current, login, loginWithIdp, loginLocal, logout, logoutFull, silentRenew, localEnabled: localCognitoEnabled }}
    >
      {children}
    </AuthContext.Provider>
  );
}
