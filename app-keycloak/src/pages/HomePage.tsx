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
      <header className={styles.header} data-app="keycloak">
        <span className={styles.appBadge} data-color="blue">app-keycloak</span>
        <h1>🔵 Keycloak 単体 SPA（参照用）</h1>
        <span className={styles.phase}>:5174 / Keycloak のみ (auth-poc-spa)</span>
      </header>
      <p className={styles.description}>
        Phase 6/7 当時の Keycloak 単体検証用 SPA。新規検証は <code>app/</code> 統合版（:5173）の利用を推奨。
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
