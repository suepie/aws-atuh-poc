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

const STEPS: FlowStep[] = [
  {
    id: 'start',
    label: 'SPA',
    icon: '📱',
    description: 'ログインボタン押下',
  },
  {
    id: 'redirect',
    label: 'Cognito',
    icon: '🔐',
    description: '/oauth2/authorize',
  },
  {
    id: 'auth',
    label: 'Hosted UI',
    icon: '🔑',
    description: 'ID/PW認証',
  },
  {
    id: 'callback',
    label: 'Callback',
    icon: '↩️',
    description: 'code → token交換',
  },
  {
    id: 'tokens',
    label: 'JWT取得',
    icon: '🎫',
    description: 'ID / Access / Refresh',
  },
];

function deriveStepStatuses(
  user: User | null,
  logs: AuthLogEntry[],
): Record<string, StepStatus> {
  const statuses: Record<string, StepStatus> = {};
  const eventNames = logs.map((l) => l.event);

  const hasError = eventNames.some((e) => e.includes('Error'));
  const loginStarted = eventNames.includes('LoginStart');
  const userLoaded = eventNames.includes('UserLoaded') || eventNames.includes('SessionRestored');

  if (user && !user.expired) {
    // 認証完了
    for (const step of STEPS) statuses[step.id] = 'done';
  } else if (hasError) {
    statuses['start'] = 'done';
    statuses['redirect'] = 'done';
    statuses['auth'] = 'error';
    statuses['callback'] = 'pending';
    statuses['tokens'] = 'pending';
  } else if (userLoaded) {
    for (const step of STEPS) statuses[step.id] = 'done';
  } else if (loginStarted) {
    statuses['start'] = 'done';
    statuses['redirect'] = 'active';
    statuses['auth'] = 'pending';
    statuses['callback'] = 'pending';
    statuses['tokens'] = 'pending';
  } else {
    statuses['start'] = 'active';
    statuses['redirect'] = 'pending';
    statuses['auth'] = 'pending';
    statuses['callback'] = 'pending';
    statuses['tokens'] = 'pending';
  }

  return statuses;
}

export function FlowDiagram({ user, logs }: Props) {
  const statuses = deriveStepStatuses(user, logs);

  return (
    <div className={styles.container}>
      <h2>認証フロー (Authorization Code + PKCE)</h2>
      <div className={styles.flow}>
        {STEPS.map((step, i) => (
          <div key={step.id} className={styles.stepWrapper}>
            <div
              className={`${styles.step} ${styles[statuses[step.id] || 'pending']}`}
            >
              <span className={styles.icon}>{step.icon}</span>
              <span className={styles.label}>{step.label}</span>
              <span className={styles.desc}>{step.description}</span>
            </div>
            {i < STEPS.length - 1 && (
              <div
                className={`${styles.arrow} ${
                  statuses[STEPS[i + 1].id] === 'done' ||
                  statuses[STEPS[i + 1].id] === 'active'
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
