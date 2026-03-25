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
  logout: () => Promise<void>;
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

  useEffect(() => {
    const mgr = new UserManager(oidcConfig);
    userManagerRef.current = mgr;

    mgr.events.addUserLoaded((u) => {
      setUser(u);
      addLog('UserLoaded', 'トークンが取得/更新されました', {
        sub: u.profile.sub,
        expires_at: u.expires_at,
        realm_access: (u.profile as Record<string, unknown>).realm_access,
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

    addLog('Init', 'Keycloak OIDC UserManager を初期化中...');
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
      addLog('LoginStart', 'ログインフローを開始します（Keycloak へリダイレクト）');
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
      addLog('LogoutStart', 'ログアウトを開始します（Keycloakセッションも破棄）');
      // Keycloakは標準の end_session_endpoint をサポートしているため
      // signoutRedirect() だけで IdP セッションも破棄される（Cognitoとの違い）
      await userManagerRef.current.signoutRedirect();
    } catch (err) {
      const message = (err as Error).message;
      setError(message);
      addLog('LogoutError', `ログアウトに失敗: ${message}`);
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
      value={{ user, isLoading, error, logs, userManager: userManagerRef.current, login, logout, silentRenew }}
    >
      {children}
    </AuthContext.Provider>
  );
}
