import { useState } from 'react';
import type { User } from 'oidc-client-ts';
import styles from './ApiTester.module.css';

interface Props {
  user: User;
}

interface ApiResponse {
  status: number;
  statusText: string;
  headers: Record<string, string>;
  body: unknown;
  duration: number;
}

const API_ENDPOINT = import.meta.env.VITE_API_ENDPOINT || '';

export function ApiTester({ user }: Props) {
  const [response, setResponse] = useState<ApiResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const callApi = async (path: string, useToken: boolean) => {
    if (!API_ENDPOINT) {
      setError('VITE_API_ENDPOINT が設定されていません（.env を確認）');
      return;
    }

    setIsLoading(true);
    setError(null);
    setResponse(null);

    const url = `${API_ENDPOINT}${path}`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (useToken) {
      headers['Authorization'] = `Bearer ${user.access_token}`;
    }

    const start = performance.now();

    try {
      const res = await fetch(url, { headers });
      const duration = Math.round(performance.now() - start);

      const responseHeaders: Record<string, string> = {};
      res.headers.forEach((v, k) => { responseHeaders[k] = v; });

      let body: unknown;
      try {
        body = await res.json();
      } catch {
        body = await res.text();
      }

      setResponse({
        status: res.status,
        statusText: res.statusText,
        headers: responseHeaders,
        body,
        duration,
      });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <h2>API Tester</h2>

      <div className={styles.endpoint}>
        <span className={styles.label}>Endpoint:</span>
        <code className={styles.url}>{API_ENDPOINT || '未設定'}</code>
      </div>

      <div className={styles.actions}>
        <button
          className={styles.callBtn}
          onClick={() => callApi('/v1/test', true)}
          disabled={isLoading}
        >
          GET /v1/test（トークンあり）
        </button>
        <button
          className={styles.callBtnDanger}
          onClick={() => callApi('/v1/test', false)}
          disabled={isLoading}
        >
          GET /v1/test（トークンなし）
        </button>
      </div>

      {isLoading && <p className={styles.loading}>リクエスト中...</p>}
      {error && <p className={styles.error}>{error}</p>}

      {response && (
        <div className={styles.response}>
          <div className={styles.statusLine}>
            <span
              className={
                response.status >= 200 && response.status < 300
                  ? styles.statusOk
                  : styles.statusErr
              }
            >
              {response.status} {response.statusText}
            </span>
            <span className={styles.duration}>{response.duration}ms</span>
          </div>

          <div className={styles.section}>
            <h4>Response Body</h4>
            <pre className={styles.json}>
              {typeof response.body === 'object'
                ? JSON.stringify(response.body, null, 2)
                : String(response.body)}
            </pre>
          </div>

          <div className={styles.section}>
            <h4>Response Headers</h4>
            <pre className={styles.json}>
              {JSON.stringify(response.headers, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
