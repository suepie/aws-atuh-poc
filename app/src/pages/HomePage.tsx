import { useAuth } from '../auth/AuthProvider';
import { AuthStatus } from '../components/AuthFlow/AuthStatus';
import { FlowDiagram } from '../components/AuthFlow/FlowDiagram';
import { TokenViewer } from '../components/TokenViewer/TokenViewer';
import { LogViewer } from '../components/LogViewer/LogViewer';
import styles from './HomePage.module.css';

export function HomePage() {
  const { user, logs } = useAuth();

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>AWS Auth PoC</h1>
        <span className={styles.phase}>Phase 1: Cognito + Hosted UI</span>
      </header>

      <FlowDiagram user={user} logs={logs} />

      <div className={styles.grid}>
        <div className={styles.left}>
          <AuthStatus />
          <LogViewer logs={logs} />
        </div>

        <div className={styles.right}>
          {user ? (
            <TokenViewer user={user} />
          ) : (
            <div className={styles.placeholder}>
              <p>ログインするとトークン情報が表示されます</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
