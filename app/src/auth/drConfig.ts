import type { UserManagerSettings } from 'oidc-client-ts';
import { WebStorageStateStore } from 'oidc-client-ts';

const drAuthority = import.meta.env.VITE_DR_COGNITO_AUTHORITY || '';
const drClientId = import.meta.env.VITE_DR_COGNITO_CLIENT_ID || '';
const drDomain = import.meta.env.VITE_DR_COGNITO_DOMAIN || '';
const redirectUri = import.meta.env.VITE_REDIRECT_URI || 'http://localhost:5173/callback';
const postLogoutUri = import.meta.env.VITE_POST_LOGOUT_URI || 'http://localhost:5173/';

/**
 * DR Cognito（大阪）が設定されているか
 */
export const drCognitoEnabled = !!(drAuthority && drClientId && drDomain);

/**
 * DR Cognito OIDC設定
 */
export const drOidcConfig: UserManagerSettings | null = drCognitoEnabled
  ? {
      authority: drAuthority,
      client_id: drClientId,
      redirect_uri: redirectUri,
      post_logout_redirect_uri: postLogoutUri,
      response_type: 'code',
      scope: 'openid profile email',
      userStore: new WebStorageStateStore({ store: window.sessionStorage, prefix: 'oidc.dr.' }),
      stateStore: new WebStorageStateStore({ store: window.sessionStorage, prefix: 'oidc.dr.' }),

      metadata: {
        issuer: drAuthority,
        authorization_endpoint: `${drDomain}/oauth2/authorize`,
        token_endpoint: `${drDomain}/oauth2/token`,
        userinfo_endpoint: `${drDomain}/oauth2/userInfo`,
        end_session_endpoint: `${drDomain}/logout?client_id=${drClientId}&logout_uri=${encodeURIComponent(postLogoutUri)}`,
        jwks_uri: `${drAuthority}/.well-known/jwks.json`,
      },
    }
  : null;

export const drIdpName = import.meta.env.VITE_AUTH0_IDP_NAME || '';
