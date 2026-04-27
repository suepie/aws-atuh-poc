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
      <header className={styles.header} data-app="sso-peer">
        <span className={styles.appBadge} data-color="orange">app-sso-peer</span>
        <h1>🟠 SSO 検証用ピア SPA</h1>
        <span className={styles.phase}>:5175 / Keycloak Realm 内の別 Client (auth-poc-spa-2)</span>
      </header>
      <p className={styles.description}>
        cross-client SSO 検証用。app または app-keycloak でログイン後にこの画面を開くと、パスワード入力なしでログイン状態になれば SSO 成功。
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
