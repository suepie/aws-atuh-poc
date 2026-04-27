import { useEffect, useState } from 'react';
import { User } from 'oidc-client-ts';
import { decodeJwt, getTokenExpiry, type DecodedToken } from '../../auth/tokenUtils';
import styles from './TokenViewer.module.css';

interface Props {
  user: User;
}

type TabType = 'id_token' | 'access_token' | 'refresh_token' | 'profile';

export function TokenViewer({ user }: Props) {
  const [activeTab, setActiveTab] = useState<TabType>('id_token');
  const [decodedId, setDecodedId] = useState<DecodedToken | null>(null);
  const [decodedAccess, setDecodedAccess] = useState<DecodedToken | null>(null);

  useEffect(() => {
    if (user.id_token) setDecodedId(decodeJwt(user.id_token));
    if (user.access_token) setDecodedAccess(decodeJwt(user.access_token));
  }, [user]);

  const tabs: { key: TabType; label: string }[] = [
    { key: 'id_token', label: 'ID Token' },
    { key: 'access_token', label: 'Access Token' },
    { key: 'refresh_token', label: 'Refresh Token' },
    { key: 'profile', label: 'Profile' },
  ];

  return (
    <div className={styles.container}>
      <h2>Token Viewer</h2>

      <div className={styles.tabs}>
        {tabs.map((tab) => (
          <button
            key={tab.key}
            className={`${styles.tab} ${activeTab === tab.key ? styles.active : ''}`}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className={styles.content}>
        {activeTab === 'id_token' && decodedId && (
          <TokenDetail label="ID Token" decoded={decodedId} raw={user.id_token} />
        )}
        {activeTab === 'access_token' && decodedAccess && (
          <TokenDetail label="Access Token" decoded={decodedAccess} raw={user.access_token} />
        )}
        {activeTab === 'refresh_token' && (
          <div>
            <h3>Refresh Token</h3>
            <p className={styles.note}>
              Refresh Token は暗号化されており、デコードできません。
              Cognito内部で使用されます。
            </p>
            <pre className={styles.raw}>
              {user.refresh_token
                ? user.refresh_token.substring(0, 50) + '...'
                : 'なし'}
            </pre>
          </div>
        )}
        {activeTab === 'profile' && (
          <div>
            <h3>User Profile (OIDC)</h3>
            <pre className={styles.json}>
              {JSON.stringify(user.profile, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}

function TokenDetail({
  label,
  decoded,
  raw,
}: {
  label: string;
  decoded: DecodedToken;
  raw?: string;
}) {
  const [showRaw, setShowRaw] = useState(false);
  const expiry = getTokenExpiry(decoded.payload);

  return (
    <div>
      <h3>{label}</h3>

      <div className={styles.expiry}>
        <span className={expiry.isExpired ? styles.expired : styles.valid}>
          {expiry.isExpired ? 'EXPIRED' : 'VALID'}
        </span>
        <span>
          有効期限: {expiry.expiresAt}
          {!expiry.isExpired && ` (残り ${expiry.remainingSeconds}秒)`}
        </span>
      </div>

      <div className={styles.section}>
        <h4>Header</h4>
        <pre className={styles.json}>
          {JSON.stringify(decoded.header, null, 2)}
        </pre>
      </div>

      <div className={styles.section}>
        <h4>Payload (Claims)</h4>
        <ClaimsTable claims={decoded.payload} />
      </div>

      <div className={styles.section}>
        <h4>Signature</h4>
        <code className={styles.signature}>{decoded.signature}</code>
      </div>

      <button
        className={styles.toggleRaw}
        onClick={() => setShowRaw(!showRaw)}
      >
        {showRaw ? 'Raw JWT を隠す' : 'Raw JWT を表示'}
      </button>
      {showRaw && raw && (
        <pre className={styles.raw}>{raw}</pre>
      )}
    </div>
  );
}

function ClaimsTable({ claims }: { claims: Record<string, unknown> }) {
  return (
    <table className={styles.claimsTable}>
      <thead>
        <tr>
          <th>Claim</th>
          <th>Value</th>
        </tr>
      </thead>
      <tbody>
        {Object.entries(claims).map(([key, value]) => (
          <tr key={key}>
            <td className={styles.claimKey}>{key}</td>
            <td>
              <pre className={styles.claimValue}>
                {typeof value === 'object'
                  ? JSON.stringify(value, null, 2)
                  : String(value)}
              </pre>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
