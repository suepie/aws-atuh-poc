'use strict';

/**
 * Positive probe 用の Bearer token を供給する。
 *
 * 2 経路をサポート:
 *   (A) Secrets Manager に格納済みの static test token を取得（既定）。
 *   (B) OAuth2 Client Credentials で token endpoint から Bearer を取得
 *       （Secret に { tokenUrl, clientId, clientSecret, scope } が入っている場合）。
 *
 * 取得した token は Secret 名単位でプロセス内キャッシュする（1 canary run 内で再利用）。
 *
 * AWS SDK v3: SecretsManagerClient + GetSecretValueCommand。
 * OAuth 呼び出しは synthetics.executeHttpStep（検証済みシグネチャ）を使用。
 */

const { SecretsManagerClient, GetSecretValueCommand } = require('@aws-sdk/client-secrets-manager');

const sm = new SecretsManagerClient({});

// Secret 名 → { token, expiresAt } のキャッシュ
const cache = new Map();

/**
 * Secrets Manager から Secret 文字列を取得し、JSON なら parse する。
 * @returns {object|string} JSON パースできれば object、できなければ生文字列
 */
async function getSecretValue(secretId) {
  const res = await sm.send(new GetSecretValueCommand({ SecretId: secretId }));
  const raw = res.SecretString;
  if (!raw) throw new Error(`Secret ${secretId} has no SecretString`);
  try {
    return JSON.parse(raw);
  } catch {
    return raw; // static token 文字列
  }
}

/**
 * OAuth2 Client Credentials で token endpoint を叩き Bearer を得る。
 * synthetics.executeHttpStep を使い、response body から access_token を回収する。
 *
 * @param {object} synthetics require('@aws/synthetics-puppeteer')
 * @param {object} cfg { tokenUrl, clientId, clientSecret, scope }
 * @returns {Promise<{token:string, expiresIn:number}>}
 */
async function fetchOAuthToken(synthetics, cfg) {
  const u = new URL(cfg.tokenUrl);
  const form = new URLSearchParams({
    grant_type: 'client_credentials',
    client_id: cfg.clientId,
    client_secret: cfg.clientSecret,
  });
  if (cfg.scope) form.set('scope', cfg.scope);
  const body = form.toString();

  const requestOptions = {
    hostname: u.hostname,
    port: u.port || (u.protocol === 'https:' ? 443 : 80),
    path: u.pathname + u.search,
    method: 'POST',
    protocol: u.protocol, // 'https:' 形式
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      'Content-Length': Buffer.byteLength(body),
    },
    body,
  };

  let result = null;
  // callback は http.IncomingMessage を受ける（検証済み）。status を検証し body を回収。
  const callback = async function (res) {
    return new Promise((resolve, reject) => {
      if (res.statusCode < 200 || res.statusCode > 299) {
        reject(new Error(`Token endpoint returned ${res.statusCode} ${res.statusMessage}`));
        return;
      }
      let responseBody = '';
      res.on('data', (d) => { responseBody += d; });
      res.on('end', () => {
        try {
          const parsed = JSON.parse(responseBody);
          if (!parsed.access_token) {
            reject(new Error('Token endpoint response missing access_token'));
            return;
          }
          result = { token: parsed.access_token, expiresIn: parsed.expires_in || 300 };
          resolve();
        } catch (e) {
          reject(e);
        }
      });
      res.on('error', reject);
    });
  };

  // stepConfig: Authorization を報告に載せない（既定で restricted だが明示）
  const stepConfig = {
    includeRequestHeaders: false,
    includeResponseBody: false,
    restrictedHeaders: ['Authorization', 'X-Amz-Security-Token'],
    continueOnHttpStepFailure: false, // token 取得失敗は即 fail
  };

  await synthetics.executeHttpStep('OAuth token exchange', requestOptions, callback, stepConfig);
  return result;
}

/**
 * Secret 名を解決し Bearer token を返す。キャッシュ有効。
 * @param {object} synthetics
 * @param {string} secretId Secret 名（app.testTokenSecret or endpoint 個別）
 * @returns {Promise<string>} Bearer token（"Bearer " prefix なしの生 token）
 */
async function getBearerToken(synthetics, secretId) {
  const now = Date.now();
  const cached = cache.get(secretId);
  if (cached && cached.expiresAt > now + 30_000) {
    return cached.token;
  }

  const secret = await getSecretValue(secretId);

  // 経路 A: static token（文字列 or { token: "..." }）
  if (typeof secret === 'string') {
    cache.set(secretId, { token: secret, expiresAt: now + 300_000 });
    return secret;
  }
  if (secret.token && !secret.tokenUrl) {
    cache.set(secretId, { token: secret.token, expiresAt: now + 300_000 });
    return secret.token;
  }

  // 経路 B: OAuth Client Credentials
  if (secret.tokenUrl && secret.clientId && secret.clientSecret) {
    const { token, expiresIn } = await fetchOAuthToken(synthetics, secret);
    cache.set(secretId, { token, expiresAt: now + expiresIn * 1000 });
    return token;
  }

  throw new Error(`Secret ${secretId} format unrecognized (expected token or OAuth config)`);
}

/** テスト / run 間キャッシュクリア用 */
function clearCache() {
  cache.clear();
}

module.exports = { getBearerToken, getSecretValue, fetchOAuthToken, clearCache };
