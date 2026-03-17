import type { AuthLogEntry } from '../../auth/AuthProvider';
import styles from './LogViewer.module.css';

interface Props {
  logs: AuthLogEntry[];
}

const eventColors: Record<string, string> = {
  Init: '#4c6ef5',
  LoginStart: '#e67700',
  UserLoaded: '#2f9e44',
  SessionRestored: '#2f9e44',
  NoSession: '#868e96',
  LogoutStart: '#e67700',
  UserUnloaded: '#e67700',
  AccessTokenExpiring: '#e67700',
  AccessTokenExpired: '#e03131',
  SilentRenewStart: '#4c6ef5',
  SilentRenewSuccess: '#2f9e44',
  SilentRenewError: '#e03131',
  LoginError: '#e03131',
  LogoutError: '#e03131',
  InitError: '#e03131',
};

export function LogViewer({ logs }: Props) {
  return (
    <div className={styles.container}>
      <h2>Auth Event Log</h2>
      <div className={styles.logList}>
        {logs.length === 0 && (
          <p className={styles.empty}>イベントはまだありません</p>
        )}
        {logs.map((log, i) => (
          <div key={i} className={styles.logEntry}>
            <span className={styles.time}>
              {log.timestamp.toLocaleTimeString('ja-JP', {
                hour12: false,
                fractionalSecondDigits: 3,
              })}
            </span>
            <span
              className={styles.event}
              style={{ color: eventColors[log.event] || '#cdd6f4' }}
            >
              [{log.event}]
            </span>
            <span className={styles.detail}>{log.detail}</span>
            {log.data != null && (
              <pre className={styles.data}>
                {JSON.stringify(log.data, null, 2)}
              </pre>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
