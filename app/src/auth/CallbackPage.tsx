import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from './AuthProvider';

/**
 * OAuth コールバックページ
 * 集約 / ローカル / DR Cognito のコールバックを処理する。
 * AuthProvider の共有 UserManager を使用することで、認証状態が即座に反映される。
 * oidc-client-ts は state パラメータで自分が発行したリクエストかを判別する。
 */
export function CallbackPage() {
  const navigate = useNavigate();
  const { userManager, localUserManager, drUserManager } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const processed = useRef(false);

  useEffect(() => {
    if (processed.current || !userManager) return;
    processed.current = true;

    const tryManagers = async () => {
      // 集約 Cognito
      try {
        await userManager.signinRedirectCallback();
        navigate('/', { replace: true });
        return;
      } catch { /* 集約ではない */ }

      // ローカル Cognito
      if (localUserManager) {
        try {
          await localUserManager.signinRedirectCallback();
          navigate('/', { replace: true });
          return;
        } catch { /* ローカルでもない */ }
      }

      // DR Cognito（大阪）
      if (drUserManager) {
        try {
          await drUserManager.signinRedirectCallback();
          navigate('/', { replace: true });
          return;
        } catch { /* DRでもない */ }
      }

      throw new Error('認証コールバックの処理に失敗しました');
    };

    tryManagers().catch((err) => {
      console.error('Callback error:', err);
      setError((err as Error).message);
    });
  }, [navigate, userManager, localUserManager, drUserManager]);

  if (error) {
    return (
      <div style={{ padding: '2rem' }}>
        <h2>認証エラー</h2>
        <p style={{ color: '#e74c3c' }}>{error}</p>
        <button onClick={() => navigate('/', { replace: true })}>
          トップに戻る
        </button>
      </div>
    );
  }

  return (
    <div style={{ padding: '2rem', textAlign: 'center' }}>
      <p>認証処理中...</p>
    </div>
  );
}
