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
  login: () => Promise<void>;
  loginWithIdp: (idpName: string) => Promise<void>;
  logout: () => Promise<void>;
  logoutFull: () => Promise<void>;
  silentRenew: () => Promise<void>;
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

    // 既存セッション確認
    addLog('Init', 'OIDC UserManager を初期化中...');
    mgr
      .getUser()
      .then((existingUser) => {
        if (existingUser && !existingUser.expired) {
          setUser(existingUser);
          addLog('SessionRestored', '既存セッションを復元しました', {
            sub: existingUser.profile.sub,
            expires_at: existingUser.expires_at,
          });
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

  const logout = useCallback(async () => {
    if (!userManagerRef.current) return;
    try {
      addLog('LogoutStart', 'ログアウトを開始します');
      await userManagerRef.current.signoutRedirect();
    } catch (err) {
      const message = (err as Error).message;
      setError(message);
      addLog('LogoutError', `ログアウトに失敗: ${message}`);
    }
  }, [addLog]);

  const logoutFull = useCallback(async () => {
    if (!userManagerRef.current) return;
    try {
      addLog('FullLogoutStart', '完全ログアウトを開始します（Cognito + IdPセッション破棄）');

      // Cognitoのセッションをクリア
      await userManagerRef.current.removeUser();
      setUser(null);

      // Auth0のセッションも破棄してからCognitoのログアウトへ
      const auth0Domain = import.meta.env.VITE_AUTH0_DOMAIN;
      const cognitoDomain = import.meta.env.VITE_COGNITO_DOMAIN;
      const clientId = import.meta.env.VITE_COGNITO_CLIENT_ID;
      const postLogoutUri = import.meta.env.VITE_POST_LOGOUT_URI || 'http://localhost:5173/';

      if (auth0Domain) {
        // Auth0 ログアウト → Cognito ログアウト → SPA に戻る
        const cognitoLogoutUrl = `${cognitoDomain}/logout?client_id=${clientId}&logout_uri=${encodeURIComponent(postLogoutUri)}`;
        const auth0LogoutUrl = `https://${auth0Domain}/v2/logout?client_id=${import.meta.env.VITE_AUTH0_CLIENT_ID || ''}&returnTo=${encodeURIComponent(cognitoLogoutUrl)}`;
        window.location.href = auth0LogoutUrl;
      } else {
        // Auth0なしの場合はCognitoのみログアウト
        const cognitoLogoutUrl = `${cognitoDomain}/logout?client_id=${clientId}&logout_uri=${encodeURIComponent(postLogoutUri)}`;
        window.location.href = cognitoLogoutUrl;
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
      value={{ user, isLoading, error, logs, userManager: userManagerRef.current, login, loginWithIdp, logout, logoutFull, silentRenew }}
    >
      {children}
    </AuthContext.Provider>
  );
}
