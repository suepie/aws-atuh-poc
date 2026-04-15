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

type HttpMethod = 'GET' | 'POST' | 'DELETE';

export function ApiTester({ user }: Props) {
  const [response, setResponse] = useState<ApiResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [method, setMethod] = useState<HttpMethod>('GET');
  const [path, setPath] = useState('/v1/expenses');
  const [body, setBody] = useState('');

  const callApi = async (
    p: string,
    useToken: boolean,
    m: HttpMethod = 'GET',
    reqBody: string = '',
  ) => {
    if (!API_ENDPOINT) {
      setError('VITE_API_ENDPOINT が設定されていません（.env を確認）');
      return;
    }

    setIsLoading(true);
    setError(null);
    setResponse(null);

    const url = `${API_ENDPOINT}${p}`;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (useToken) {
      headers['Authorization'] = `Bearer ${user.access_token}`;
    }

    const fetchInit: RequestInit = { method: m, headers };
    if (m !== 'GET' && reqBody.trim()) {
      fetchInit.body = reqBody;
    }

    const start = performance.now();

    try {
      const res = await fetch(url, fetchInit);
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

      <div className={styles.section}>
        <h4>カスタムリクエスト（認可テスト用）</h4>
        <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
          <select value={method} onChange={(e) => setMethod(e.target.value as HttpMethod)}>
            <option value="GET">GET</option>
            <option value="POST">POST</option>
            <option value="DELETE">DELETE</option>
          </select>
          <input
            type="text"
            value={path}
            onChange={(e) => setPath(e.target.value)}
            placeholder="/v1/expenses"
            style={{ flex: 1 }}
          />
          <button
            className={styles.callBtn}
            onClick={() => callApi(path, true, method, body)}
            disabled={isLoading}
          >
            送信
          </button>
        </div>
        {method !== 'GET' && (
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder='{"amount": 5000}'
            rows={4}
            style={{ width: '100%', fontFamily: 'monospace' }}
          />
        )}
        <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
          <strong>クイック:</strong>
          <button type="button" onClick={() => { setMethod('GET'); setPath('/v1/expenses'); setBody(''); }} style={{ marginLeft: 4 }}>一覧</button>
          <button type="button" onClick={() => { setMethod('POST'); setPath('/v1/expenses'); setBody('{"amount": 5000}'); }} style={{ marginLeft: 4 }}>作成</button>
          <button type="button" onClick={() => { setMethod('POST'); setPath('/v1/expenses/exp-002/approve'); setBody(''); }} style={{ marginLeft: 4 }}>承認</button>
          <button type="button" onClick={() => { setMethod('DELETE'); setPath('/v1/expenses/exp-001'); setBody(''); }} style={{ marginLeft: 4 }}>削除</button>
          <button type="button" onClick={() => { setMethod('GET'); setPath('/v1/tenants/globex-inc/expenses'); setBody(''); }} style={{ marginLeft: 4 }}>別テナント</button>
        </div>
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
