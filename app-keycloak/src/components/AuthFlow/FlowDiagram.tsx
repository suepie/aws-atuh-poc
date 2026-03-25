import type { User } from 'oidc-client-ts';
import type { AuthLogEntry } from '../../auth/AuthProvider';
import styles from './FlowDiagram.module.css';

interface Props {
  user: User | null;
  logs: AuthLogEntry[];
}

type StepStatus = 'done' | 'active' | 'pending' | 'error';

interface FlowStep {
  id: string;
  label: string;
  icon: string;
  description: string;
}

/**
 * Keycloak認証フロー（Authorization Code + PKCE）
 * Cognitoと異なり、Keycloakは標準OIDCを完全サポートしているため
 * metadata手動指定やlogoutの多段リダイレクトが不要
 */
const KEYCLOAK_STEPS: FlowStep[] = [
  { id: 'start', label: 'SPA', icon: '📱', description: 'ログインボタン押下' },
  { id: 'redirect', label: 'Keycloak', icon: '🔑', description: '/protocol/openid-connect/auth' },
  { id: 'auth', label: 'ログイン画面', icon: '🔐', description: 'ID/PW認証' },
  { id: 'callback', label: 'Callback', icon: '↩️', description: 'code → token交換' },
  { id: 'tokens', label: 'JWT取得', icon: '🎫', description: 'realm_access含む' },
];

function deriveStepStatuses(
  steps: FlowStep[],
  user: User | null,
  logs: AuthLogEntry[],
): Record<string, StepStatus> {
  const statuses: Record<string, StepStatus> = {};
  const eventNames = logs.map((l) => l.event);

  const hasError = eventNames.some((e) => e.includes('Error'));
  const loginStarted = eventNames.includes('LoginStart');
  const userLoaded = eventNames.includes('UserLoaded') || eventNames.includes('SessionRestored');

  if (user && !user.expired) {
    for (const step of steps) statuses[step.id] = 'done';
  } else if (hasError) {
    for (const step of steps) statuses[step.id] = 'pending';
    statuses[steps[0].id] = 'done';
    statuses[steps[1].id] = 'done';
    statuses[steps[2].id] = 'error';
  } else if (userLoaded) {
    for (const step of steps) statuses[step.id] = 'done';
  } else if (loginStarted) {
    for (const step of steps) statuses[step.id] = 'pending';
    statuses[steps[0].id] = 'done';
    statuses[steps[1].id] = 'active';
  } else {
    for (const step of steps) statuses[step.id] = 'pending';
    statuses[steps[0].id] = 'active';
  }

  return statuses;
}

export function FlowDiagram({ user, logs }: Props) {
  const steps = KEYCLOAK_STEPS;
  const statuses = deriveStepStatuses(steps, user, logs);

  return (
    <div className={styles.container}>
      <h2>認証フロー (Keycloak: Authorization Code + PKCE)</h2>
      <div className={styles.flow}>
        {steps.map((step, i) => (
          <div key={step.id} className={styles.stepWrapper}>
            <div
              className={`${styles.step} ${styles[statuses[step.id] || 'pending']}`}
            >
              <span className={styles.icon}>{step.icon}</span>
              <span className={styles.label}>{step.label}</span>
              <span className={styles.desc}>{step.description}</span>
            </div>
            {i < steps.length - 1 && (
              <div
                className={`${styles.arrow} ${
                  statuses[steps[i + 1].id] === 'done' ||
                  statuses[steps[i + 1].id] === 'active'
                    ? styles.arrowActive
                    : ''
                }`}
              >
                →
              </div>
            )}
          </div>
        ))}
      </div>
      <div className={styles.legend}>
        <span className={styles.legendItem}>
          <span className={`${styles.dot} ${styles.done}`} /> 完了
        </span>
        <span className={styles.legendItem}>
          <span className={`${styles.dot} ${styles.active}`} /> 進行中
        </span>
        <span className={styles.legendItem}>
          <span className={`${styles.dot} ${styles.pending}`} /> 待機
        </span>
        <span className={styles.legendItem}>
          <span className={`${styles.dot} ${styles.error}`} /> エラー
        </span>
      </div>
    </div>
  );
}
