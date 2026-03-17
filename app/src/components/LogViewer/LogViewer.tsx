import type { AuthLogEntry } from '../../auth/AuthProvider';
import styles from './LogViewer.module.css';

interface Props {
  logs: AuthLogEntry[];
}

const eventColors: Record<string, string> = {
  Init: '#89b4fa',
  LoginStart: '#f9e2af',
  UserLoaded: '#a6e3a1',
  SessionRestored: '#a6e3a1',
  NoSession: '#a6adc8',
  LogoutStart: '#fab387',
  UserUnloaded: '#fab387',
  AccessTokenExpiring: '#f9e2af',
  AccessTokenExpired: '#f38ba8',
  SilentRenewStart: '#89b4fa',
  SilentRenewSuccess: '#a6e3a1',
  SilentRenewError: '#f38ba8',
  LoginError: '#f38ba8',
  LogoutError: '#f38ba8',
  InitError: '#f38ba8',
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
