/**
 * JWTトークンのデコードユーティリティ
 */

export interface DecodedToken {
  header: Record<string, unknown>;
  payload: Record<string, unknown>;
  signature: string;
}

export function decodeJwt(token: string): DecodedToken | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;

    const header = JSON.parse(atob(parts[0]));
    const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
    const signature = parts[2].substring(0, 20) + '...';

    return { header, payload, signature };
  } catch {
    return null;
  }
}

export function formatTimestamp(epoch: number): string {
  return new Date(epoch * 1000).toLocaleString('ja-JP');
}

export function getTokenExpiry(payload: Record<string, unknown>): {
  expiresAt: string;
  isExpired: boolean;
  remainingSeconds: number;
} {
  const exp = payload.exp as number;
  if (!exp) return { expiresAt: 'N/A', isExpired: true, remainingSeconds: 0 };

  const now = Math.floor(Date.now() / 1000);
  return {
    expiresAt: formatTimestamp(exp),
    isExpired: now >= exp,
    remainingSeconds: Math.max(0, exp - now),
  };
}
