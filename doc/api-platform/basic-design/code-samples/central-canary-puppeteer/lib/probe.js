'use strict';

/**
 * 1 endpoint に対する Negative + Positive probe。
 *
 * authPattern 別に assertion 方式を切替（README §2.1 enum）:
 *   - api-gw-jwt / alb-code-jwt : Negative 期待 401/403、Positive は Bearer で 2xx
 *   - alb-cookie-monolith       : Negative 期待 302 Redirect to /login
 *   - api-gw-iam / lambda-url-iam: SigV4 が必要（Phase 2、Positive 未実装）
 *
 * probe は synthetics.executeHttpStep で行う。ここでは status を fail させず
 * 「観測した status を回収する」方針にする（分類は classify.js が担う）。
 * そのため stepConfig.continueOnHttpStepFailure=true とし、callback は
 * status を resolve するだけで throw しない（canary 自体は index.js で必要時に fail）。
 */

const { getBearerToken } = require('./token');

/**
 * executeHttpStep を「status 観測モード」で実行する。
 * どんな status でも throw せず statusCode を返す。
 *
 * @returns {Promise<number>} 観測した HTTP status code
 */
async function observeStatus(synthetics, stepName, baseUrl, path, method, headers) {
  const u = new URL(baseUrl);
  const fullPath = (u.pathname === '/' ? '' : u.pathname) + path;

  const requestOptions = {
    hostname: u.hostname,
    port: u.port || (u.protocol === 'https:' ? 443 : 80),
    path: fullPath,
    method,
    protocol: u.protocol,
    headers: headers || {},
  };

  let observed = 0;
  const callback = async function (res) {
    return new Promise((resolve) => {
      observed = res.statusCode;
      // body を drain（メモリリーク防止）。中身は使わない。
      res.on('data', () => {});
      res.on('end', () => resolve());
      res.on('error', () => resolve());
    });
  };

  const stepConfig = {
    includeRequestHeaders: false,
    includeResponseHeaders: true,
    includeResponseBody: false,
    restrictedHeaders: ['Authorization', 'X-Amz-Security-Token'],
    // status に関わらず step 失敗で run を止めない（観測を続ける）
    continueOnHttpStepFailure: true,
  };

  await synthetics.executeHttpStep(stepName, requestOptions, callback, stepConfig);
  return observed;
}

/**
 * 1 endpoint を probe する。
 *
 * @param {object} synthetics
 * @param {object} app     App Registry レコード（baseUrl, authPattern, testTokenSecret）
 * @param {object} ep      endpoint 記述子（openapi.extractEndpoints の 1 要素）
 * @returns {Promise<{negStatus, posStatus}>}
 */
async function probeEndpoint(synthetics, app, ep) {
  const { baseUrl, authPattern } = app;
  const stepBase = `${app.appId}:${ep.method} ${ep.rawPath}`;

  let negStatus = null;
  let posStatus = undefined;

  // ---- Negative probe（skip 指定でなければ実施）--------------------------
  if (!ep.skipAuthCheck) {
    if (authPattern === 'alb-cookie-monolith') {
      // Cookie モノリス: 未認証で /login への 302 を期待。
      // リダイレクトを自動追従させない（302 そのものを観測したい）ため
      // executeHttpStep は redirect を追わない前提で status を回収する。
      negStatus = await observeStatus(
        synthetics, `${stepBase} [neg-cookie]`, baseUrl, ep.path, ep.method, {}
      );
    } else {
      // JWT / IAM 系: 認証ヘッダなしで 401/403 を期待
      negStatus = await observeStatus(
        synthetics, `${stepBase} [neg]`, baseUrl, ep.path, ep.method, {}
      );
    }
  }

  // ---- Positive probe（positiveTest が有効な場合のみ）-------------------
  const doPositive = ep.positiveTest === true
    || (ep.positiveTest === 'pre-prod-only' && app.env !== 'prod');

  if (doPositive) {
    if (authPattern === 'api-gw-jwt' || authPattern === 'alb-code-jwt') {
      // Bearer token で 2xx を期待
      const secretId = ep.testTokenSecret || app.testTokenSecret;
      if (!secretId) {
        // token 未設定は WARN 相当。posStatus を残さず Negative のみで分類させる。
        posStatus = undefined;
      } else {
        const token = await getBearerToken(synthetics, secretId);
        posStatus = await observeStatus(
          synthetics, `${stepBase} [pos]`, baseUrl, ep.path, ep.method,
          { Authorization: `Bearer ${token}` }
        );
      }
    } else if (authPattern === 'api-gw-iam' || authPattern === 'lambda-url-iam') {
      // ⚠ 要 PoC 検証: SigV4 署名が必要（Phase 2）。
      // executeHttpStep は SigV4 を自動付与しないため、@aws-sdk/signature-v4 で
      // 手動署名 → headers に載せる実装が必要。現状は Positive をスキップ。
      posStatus = undefined;
    } else if (authPattern === 'alb-cookie-monolith') {
      // ⚠ 要 PoC 検証: Cookie モノリスの Positive は Puppeteer でログインフロー
      //   （page.goto → form 入力 → Cookie 取得）を回す必要がある。
      //   executeHttpStep だけでは完結しないため index.js 側で分岐が必要。
      posStatus = undefined;
    }
  }

  return { negStatus, posStatus };
}

module.exports = { probeEndpoint, observeStatus };
