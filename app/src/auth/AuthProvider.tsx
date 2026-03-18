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
import { drOidcConfig, drCognitoEnabled, drIdpName } from './drConfig';

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
  drUserManager: UserManager | null;
  login: () => Promise<void>;
  loginWithIdp: (idpName: string) => Promise<void>;
  loginLocal: () => Promise<void>;
  loginDr: () => Promise<void>;
  loginDrWithIdp: () => Promise<void>;
  logout: () => Promise<void>;
  logoutFull: () => Promise<void>;
  silentRenew: () => Promise<void>;
  localEnabled: boolean;
  drEnabled: boolean;
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
  const drUserManagerRef = useRef<UserManager | null>(null);

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

    // DR Cognito（大阪）UserManager 初期化
    if (drCognitoEnabled && drOidcConfig) {
      const drMgr = new UserManager(drOidcConfig);
      drUserManagerRef.current = drMgr;

      drMgr.events.addUserLoaded((u) => {
        setUser(u);
        addLog('DrUserLoaded', 'DR Cognito（大阪）のトークンが取得されました', {
          sub: u.profile.sub,
          issuer: 'dr',
        });
      });

      addLog('Init', 'DR Cognito（大阪）UserManager を初期化しました');
    }

    // 既存セッション確認（集約 → ローカル → DRの順に確認）
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
          const localUser = await localUserManagerRef.current.getUser();
          if (localUser && !localUser.expired) {
            setUser(localUser);
            addLog('SessionRestored', '既存セッションを復元しました（ローカルCognito）', {
              sub: localUser.profile.sub,
              expires_at: localUser.expires_at,
            });
            return;
          }
          // DR Cognito も確認
          if (drUserManagerRef.current) {
            const drUser = await drUserManagerRef.current.getUser();
            if (drUser && !drUser.expired) {
              setUser(drUser);
              addLog('SessionRestored', '既存セッションを復元しました（DR Cognito 大阪）', {
                sub: drUser.profile.sub,
                expires_at: drUser.expires_at,
              });
              return;
            }
          }
          addLog('NoSession', '有効なセッションがありません');
        } else if (drUserManagerRef.current) {
          const drUser = await drUserManagerRef.current.getUser();
          if (drUser && !drUser.expired) {
            setUser(drUser);
            addLog('SessionRestored', '既存セッションを復元しました（DR Cognito 大阪）', {
              sub: drUser.profile.sub,
              expires_at: drUser.expires_at,
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

  const loginDr = useCallback(async () => {
    if (!drUserManagerRef.current) return;
    try {
      addLog('DrLoginStart', 'DR Cognito（大阪）ログインを開始します');
      await drUserManagerRef.current.signinRedirect();
    } catch (err) {
      const message = (err as Error).message;
      setError(message);
      addLog('LoginError', `DRログイン開始に失敗: ${message}`);
    }
  }, [addLog]);

  const loginDrWithIdp = useCallback(async () => {
    if (!drUserManagerRef.current) return;
    try {
      addLog('DrFederationLoginStart', 'DR Cognito（大阪）フェデレーションログインを開始します');
      await drUserManagerRef.current.signinRedirect({
        extraQueryParams: { identity_provider: drIdpName },
      });
    } catch (err) {
      const message = (err as Error).message;
      setError(message);
      addLog('LoginError', `DRフェデレーションログイン開始に失敗: ${message}`);
    }
  }, [addLog]);

  const getUserType = useCallback((): 'central' | 'local' | 'dr' => {
    if (!user) return 'central';
    const iss = user.profile.iss || '';
    const localAuthority = import.meta.env.VITE_LOCAL_COGNITO_AUTHORITY || '';
    const drAuthority = import.meta.env.VITE_DR_COGNITO_AUTHORITY || '';
    if (localAuthority && iss === localAuthority) return 'local';
    if (drAuthority && iss === drAuthority) return 'dr';
    return 'central';
  }, [user]);

  const logout = useCallback(async () => {
    const type = getUserType();
    const postLogoutUri = import.meta.env.VITE_POST_LOGOUT_URI || 'http://localhost:5173/';

    try {
      if (type === 'local' && localUserManagerRef.current) {
        addLog('LogoutStart', 'ログアウトを開始します（ローカルCognito）');
        await localUserManagerRef.current.removeUser();
        setUser(null);
        const domain = import.meta.env.VITE_LOCAL_COGNITO_DOMAIN;
        const clientId = import.meta.env.VITE_LOCAL_COGNITO_CLIENT_ID;
        window.location.href = `${domain}/logout?client_id=${clientId}&logout_uri=${encodeURIComponent(postLogoutUri)}`;
      } else if (type === 'dr' && drUserManagerRef.current) {
        addLog('LogoutStart', 'ログアウトを開始します（DR Cognito 大阪）');
        await drUserManagerRef.current.removeUser();
        setUser(null);
        const domain = import.meta.env.VITE_DR_COGNITO_DOMAIN;
        const clientId = import.meta.env.VITE_DR_COGNITO_CLIENT_ID;
        window.location.href = `${domain}/logout?client_id=${clientId}&logout_uri=${encodeURIComponent(postLogoutUri)}`;
      } else if (userManagerRef.current) {
        addLog('LogoutStart', 'ログアウトを開始します（集約Cognito）');
        await userManagerRef.current.signoutRedirect();
      }
    } catch (err) {
      const message = (err as Error).message;
      setError(message);
      addLog('LogoutError', `ログアウトに失敗: ${message}`);
    }
  }, [addLog, getUserType]);

  const logoutFull = useCallback(async () => {
    const type = getUserType();

    try {
      addLog('FullLogoutStart', '完全ログアウトを開始します（全セッション破棄）');

      // 全UserManagerのセッションをクリア
      if (userManagerRef.current) await userManagerRef.current.removeUser();
      if (localUserManagerRef.current) await localUserManagerRef.current.removeUser();
      if (drUserManagerRef.current) await drUserManagerRef.current.removeUser();
      setUser(null);

      const postLogoutUri = import.meta.env.VITE_POST_LOGOUT_URI || 'http://localhost:5173/';
      const auth0Domain = import.meta.env.VITE_AUTH0_DOMAIN;

      if (type === 'local') {
        const domain = import.meta.env.VITE_LOCAL_COGNITO_DOMAIN;
        const clientId = import.meta.env.VITE_LOCAL_COGNITO_CLIENT_ID;
        window.location.href = `${domain}/logout?client_id=${clientId}&logout_uri=${encodeURIComponent(postLogoutUri)}`;
      } else if (type === 'dr') {
        // DR Cognito + Auth0 の完全ログアウト
        const domain = import.meta.env.VITE_DR_COGNITO_DOMAIN;
        const clientId = import.meta.env.VITE_DR_COGNITO_CLIENT_ID;
        if (auth0Domain) {
          const cognitoLogoutUrl = `${domain}/logout?client_id=${clientId}&logout_uri=${encodeURIComponent(postLogoutUri)}`;
          const auth0LogoutUrl = `https://${auth0Domain}/v2/logout?client_id=${import.meta.env.VITE_AUTH0_CLIENT_ID || ''}&returnTo=${encodeURIComponent(cognitoLogoutUrl)}`;
          window.location.href = auth0LogoutUrl;
        } else {
          window.location.href = `${domain}/logout?client_id=${clientId}&logout_uri=${encodeURIComponent(postLogoutUri)}`;
        }
      } else {
        // 集約Cognito + Auth0 の完全ログアウト
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
  }, [addLog, getUserType]);

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
      value={{ user, isLoading, error, logs, userManager: userManagerRef.current, localUserManager: localUserManagerRef.current, drUserManager: drUserManagerRef.current, login, loginWithIdp, loginLocal, loginDr, loginDrWithIdp, logout, logoutFull, silentRenew, localEnabled: localCognitoEnabled, drEnabled: drCognitoEnabled }}
    >
      {children}
    </AuthContext.Provider>
  );
}
