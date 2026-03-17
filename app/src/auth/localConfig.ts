import type { UserManagerSettings } from 'oidc-client-ts';
import { WebStorageStateStore } from 'oidc-client-ts';

const localAuthority = import.meta.env.VITE_LOCAL_COGNITO_AUTHORITY || '';
const localClientId = import.meta.env.VITE_LOCAL_COGNITO_CLIENT_ID || '';
const localDomain = import.meta.env.VITE_LOCAL_COGNITO_DOMAIN || '';
const redirectUri = import.meta.env.VITE_REDIRECT_URI || 'http://localhost:5173/callback';
const postLogoutUri = import.meta.env.VITE_POST_LOGOUT_URI || 'http://localhost:5173/';

/**
 * ローカル Cognito が設定されているか
 */
export const localCognitoEnabled = !!(localAuthority && localClientId && localDomain);

/**
 * ローカル Cognito OIDC設定
 */
export const localOidcConfig: UserManagerSettings | null = localCognitoEnabled
  ? {
      authority: localAuthority,
      client_id: localClientId,
      redirect_uri: redirectUri,
      post_logout_redirect_uri: postLogoutUri,
      response_type: 'code',
      scope: 'openid profile email',
      // ローカル用は別の storage key を使い、集約Cognitoのセッションと分離
      userStore: new WebStorageStateStore({ store: window.sessionStorage }),
      stateStore: new WebStorageStateStore({ store: window.sessionStorage }),

      metadata: {
        issuer: localAuthority,
        authorization_endpoint: `${localDomain}/oauth2/authorize`,
        token_endpoint: `${localDomain}/oauth2/token`,
        userinfo_endpoint: `${localDomain}/oauth2/userInfo`,
        end_session_endpoint: `${localDomain}/logout?client_id=${localClientId}&logout_uri=${encodeURIComponent(postLogoutUri)}`,
        jwks_uri: `${localAuthority}/.well-known/jwks.json`,
      },
    }
  : null;
