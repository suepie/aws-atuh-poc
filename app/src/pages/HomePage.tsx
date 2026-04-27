import { useAuth } from '../auth/AuthProvider';
import { AuthStatus } from '../components/AuthFlow/AuthStatus';
import { FlowDiagram } from '../components/AuthFlow/FlowDiagram';
import { TokenViewer } from '../components/TokenViewer/TokenViewer';
import { ApiTester } from '../components/ApiTester/ApiTester';
import { LogViewer } from '../components/LogViewer/LogViewer';
import styles from './HomePage.module.css';

export function HomePage() {
  const { user, logs } = useAuth();

  return (
    <div className={styles.page}>
      <header className={styles.header} data-app="multi">
        <span className={styles.appBadge} data-color="purple">app</span>
        <h1>🌐 Multi-IdP Auth PoC</h1>
        <span className={styles.phase}>:5173 / Cognito (集約・ローカル・DR) + Auth0 + Keycloak</span>
      </header>
      <p className={styles.description}>
        全 IdP を 1 つの SPA に統合した版。複数の「ログイン」ボタンから同じバックエンド (/v1, /v2) にアクセスして認可動作を比較できる。
      </p>

      <FlowDiagram user={user} logs={logs} />

      <div className={styles.grid}>
        <div className={styles.left}>
          <AuthStatus />
          {user && <ApiTester user={user} />}
          <LogViewer logs={logs} />
        </div>

        <div className={styles.right}>
          {user ? (
            <TokenViewer user={user} />
          ) : (
            <div className={styles.placeholder}>
              <p>ログインするとトークン情報とAPI Testerが表示されます</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
