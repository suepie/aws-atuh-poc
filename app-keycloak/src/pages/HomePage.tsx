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
      <header className={styles.header}>
        <h1>Keycloak Auth PoC</h1>
        <span className={styles.phase}>Phase 6: Keycloak (OIDC)</span>
      </header>

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
