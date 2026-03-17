import { useEffect, useRef, useState } from 'react';
import { UserManager } from 'oidc-client-ts';
import { useNavigate } from 'react-router-dom';
import { oidcConfig } from './config';

/**
 * OAuth コールバックページ
 * Cognito Hosted UI からリダイレクトされた後、authorization code を処理する
 */
export function CallbackPage() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const processed = useRef(false);

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;

    const mgr = new UserManager(oidcConfig);
    mgr
      .signinRedirectCallback()
      .then(() => {
        navigate('/', { replace: true });
      })
      .catch((err) => {
        console.error('Callback error:', err);
        setError((err as Error).message);
      });
  }, [navigate]);

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
