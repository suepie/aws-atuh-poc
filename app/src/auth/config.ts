import type { UserManagerSettings } from 'oidc-client-ts';
import { WebStorageStateStore } from 'oidc-client-ts';

/**
 * Cognito OIDC設定
 * 環境変数から取得（Terraform outputの値を.envに設定）
 */
export const oidcConfig: UserManagerSettings = {
  authority: import.meta.env.VITE_COGNITO_AUTHORITY,
  client_id: import.meta.env.VITE_COGNITO_CLIENT_ID,
  redirect_uri: import.meta.env.VITE_REDIRECT_URI || 'http://localhost:5173/callback',
  post_logout_redirect_uri: import.meta.env.VITE_POST_LOGOUT_URI || 'http://localhost:5173/',
  response_type: 'code',
  scope: 'openid profile email',
  userStore: new WebStorageStateStore({ store: window.sessionStorage }),

  // Cognito固有: Hosted UIのlogoutエンドポイント
  metadata: {
    issuer: import.meta.env.VITE_COGNITO_AUTHORITY,
    authorization_endpoint: `${import.meta.env.VITE_COGNITO_DOMAIN}/oauth2/authorize`,
    token_endpoint: `${import.meta.env.VITE_COGNITO_DOMAIN}/oauth2/token`,
    userinfo_endpoint: `${import.meta.env.VITE_COGNITO_DOMAIN}/oauth2/userInfo`,
    end_session_endpoint: `${import.meta.env.VITE_COGNITO_DOMAIN}/logout?client_id=${import.meta.env.VITE_COGNITO_CLIENT_ID}&logout_uri=${encodeURIComponent(import.meta.env.VITE_POST_LOGOUT_URI || 'http://localhost:5173/')}`,
    jwks_uri: `${import.meta.env.VITE_COGNITO_AUTHORITY}/.well-known/jwks.json`,
  },
};
