import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from './AuthProvider';

/**
 * OAuth コールバックページ（Keycloak版）
 * Keycloakは単一のUserManagerのみなのでシンプル
 */
export function CallbackPage() {
  const navigate = useNavigate();
  const { userManager } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const processed = useRef(false);

  useEffect(() => {
    if (processed.current || !userManager) return;
    processed.current = true;

    userManager
      .signinRedirectCallback()
      .then(() => {
        navigate('/', { replace: true });
      })
      .catch((err) => {
        console.error('Callback error:', err);
        setError((err as Error).message);
      });
  }, [navigate, userManager]);

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
