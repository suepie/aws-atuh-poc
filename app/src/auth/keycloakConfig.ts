import type { UserManagerSettings } from 'oidc-client-ts';
import { WebStorageStateStore } from 'oidc-client-ts';

const keycloakAuthority = import.meta.env.VITE_KEYCLOAK_AUTHORITY || '';
const keycloakClientId = import.meta.env.VITE_KEYCLOAK_CLIENT_ID || '';
const redirectUri = import.meta.env.VITE_REDIRECT_URI || 'http://localhost:5173/callback';
const postLogoutUri = import.meta.env.VITE_POST_LOGOUT_URI || 'http://localhost:5173/';

/**
 * Keycloak が設定されているか
 */
export const keycloakEnabled = !!(keycloakAuthority && keycloakClientId);

/**
 * Keycloak OIDC設定
 * Keycloak は OIDC Discovery が動くので metadata 指定は不要（oidc-client-ts が自動解決）。
 */
export const keycloakOidcConfig: UserManagerSettings | null = keycloakEnabled
  ? {
      authority: keycloakAuthority,
      client_id: keycloakClientId,
      redirect_uri: redirectUri,
      post_logout_redirect_uri: postLogoutUri,
      response_type: 'code',
      scope: 'openid profile email',
      userStore: new WebStorageStateStore({ store: window.sessionStorage, prefix: 'oidc.keycloak.' }),
      stateStore: new WebStorageStateStore({ store: window.sessionStorage, prefix: 'oidc.keycloak.' }),
    }
  : null;
