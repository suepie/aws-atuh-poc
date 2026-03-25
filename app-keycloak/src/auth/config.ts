import type { UserManagerSettings } from 'oidc-client-ts';
import { WebStorageStateStore } from 'oidc-client-ts';

const authority = import.meta.env.VITE_KEYCLOAK_AUTHORITY;
const clientId = import.meta.env.VITE_KEYCLOAK_CLIENT_ID || 'auth-poc-spa';
const redirectUri = import.meta.env.VITE_REDIRECT_URI || 'http://localhost:5174/callback';
const postLogoutUri = import.meta.env.VITE_POST_LOGOUT_URI || 'http://localhost:5174/';

/**
 * Keycloak OIDC設定
 * Keycloakは標準OIDC Discovery対応のため、metadataの手動指定不要
 * (Cognitoと異なり end_session_endpoint も Discovery で自動取得される)
 */
export const oidcConfig: UserManagerSettings = {
  authority,
  client_id: clientId,
  redirect_uri: redirectUri,
  post_logout_redirect_uri: postLogoutUri,
  response_type: 'code',
  scope: 'openid profile email',
  userStore: new WebStorageStateStore({ store: window.sessionStorage, prefix: 'oidc.kc.' }),
  stateStore: new WebStorageStateStore({ store: window.sessionStorage, prefix: 'oidc.kc.' }),
  // Keycloakは標準OIDC Discoveryを完全サポートしているため
  // metadata手動指定は不要（Cognitoとの大きな違い）
};
