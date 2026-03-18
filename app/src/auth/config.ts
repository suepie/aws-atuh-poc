import type { UserManagerSettings } from 'oidc-client-ts';
import { WebStorageStateStore } from 'oidc-client-ts';

const cognitoDomain = import.meta.env.VITE_COGNITO_DOMAIN;
const clientId = import.meta.env.VITE_COGNITO_CLIENT_ID;
const authority = import.meta.env.VITE_COGNITO_AUTHORITY;
const redirectUri = import.meta.env.VITE_REDIRECT_URI || 'http://localhost:5173/callback';
const postLogoutUri = import.meta.env.VITE_POST_LOGOUT_URI || 'http://localhost:5173/';

/**
 * Cognito OIDC設定
 * 環境変数から取得（Terraform outputの値を.envに設定）
 */
export const oidcConfig: UserManagerSettings = {
  authority,
  client_id: clientId,
  redirect_uri: redirectUri,
  post_logout_redirect_uri: postLogoutUri,
  response_type: 'code',
  scope: 'openid profile email',
  userStore: new WebStorageStateStore({ store: window.sessionStorage, prefix: 'oidc.central.' }),
  stateStore: new WebStorageStateStore({ store: window.sessionStorage, prefix: 'oidc.central.' }),

  // Cognito固有: Hosted UIのlogoutエンドポイント
  metadata: {
    issuer: authority,
    authorization_endpoint: `${cognitoDomain}/oauth2/authorize`,
    token_endpoint: `${cognitoDomain}/oauth2/token`,
    userinfo_endpoint: `${cognitoDomain}/oauth2/userInfo`,
    end_session_endpoint: `${cognitoDomain}/logout?client_id=${clientId}&logout_uri=${encodeURIComponent(postLogoutUri)}`,
    jwks_uri: `${authority}/.well-known/jwks.json`,
  },
};

/**
 * 外部IdP名（Auth0等）。設定されていればフェデレーションログインが有効。
 */
export const externalIdpName = import.meta.env.VITE_AUTH0_IDP_NAME || '';

/**
 * 外部IdP経由のログインURL を構築する。
 * Cognito の /oauth2/authorize に identity_provider パラメータを付与して
 * Hosted UI をスキップし、直接外部IdPにリダイレクトさせる。
 */
export function buildIdpLoginUrl(idpName: string, state: string, codeChallenge: string, nonce: string): string {
  const params = new URLSearchParams({
    response_type: 'code',
    client_id: clientId,
    redirect_uri: redirectUri,
    scope: 'openid profile email',
    identity_provider: idpName,
    state,
    code_challenge: codeChallenge,
    code_challenge_method: 'S256',
    nonce,
  });
  return `${cognitoDomain}/oauth2/authorize?${params.toString()}`;
}
