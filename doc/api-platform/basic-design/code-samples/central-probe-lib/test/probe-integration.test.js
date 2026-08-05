'use strict';

/**
 * P4-3 ローカル統合テスト（AWS 不要）。
 *
 * 実物の probe.js（authPattern 別の Negative probe 分岐）+ classify.js を、
 *   - synthetics スタブ（executeHttpStep を実 http リクエストで代替）
 *   - ローカル HTTP モックサーバ（path に応じて status を返す）
 * で end-to-end 実行し、4×4 分類まで通ることを検証する。
 *
 * Positive probe（Bearer 取得）は Secrets/OAuth を要するため本テストでは Negative 経路のみ。
 * 実行: node --test test/probe-integration.test.js
 */

const { test, before, after } = require('node:test');
const assert = require('node:assert');
const http = require('node:http');

const { probeEndpoint } = require('../lib/probe');
const { classify } = require('../lib/classify');

// --- synthetics スタブ ------------------------------------------------------
// executeHttpStep(stepName, requestOptions, callback, stepConfig) を実 http で代替。
const syntheticsStub = {
  async executeStep(_name, fn) { return fn(); },
  async executeHttpStep(_stepName, requestOptions, callback, _stepConfig) {
    return new Promise((resolve, reject) => {
      const req = http.request(
        {
          hostname: requestOptions.hostname,
          port: requestOptions.port,
          path: requestOptions.path,
          method: requestOptions.method,
          headers: requestOptions.headers,
        },
        async (res) => {
          try { await callback(res); resolve(); } catch (e) { reject(e); }
        }
      );
      req.on('error', reject);
      req.end();
    });
  },
};

// --- モック API サーバ ------------------------------------------------------
// 認証ヘッダの有無で status を出し分ける（実 API の認証挙動を模擬）。
//   /protected  : Authorization なし → 401、あり → 200
//   /leaky      : 常に 200（認証漏れを模擬）
//   /monolith   : Authorization なし → 302（/login へ）、あり → 200
let server;
let baseUrl;

before(async () => {
  server = http.createServer((req, res) => {
    const hasAuth = !!req.headers['authorization'];
    if (req.url === '/protected') {
      res.writeHead(hasAuth ? 200 : 401); res.end();
    } else if (req.url === '/leaky') {
      res.writeHead(200); res.end();
    } else if (req.url === '/monolith') {
      if (hasAuth) { res.writeHead(200); res.end(); }
      else { res.writeHead(302, { Location: '/login' }); res.end(); }
    } else {
      res.writeHead(404); res.end();
    }
  });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const { port } = server.address();
  baseUrl = `http://127.0.0.1:${port}`;
});

after(async () => { await new Promise((r) => server.close(r)); });

// --- テスト -----------------------------------------------------------------
test('api-gw-jwt: 認証ある endpoint → Neg=401 → classify OK', async () => {
  const app = { appId: 'mock', env: 'stg', baseUrl, authPattern: 'api-gw-jwt' };
  const ep = { method: 'GET', path: '/protected', rawPath: '/protected', skipAuthCheck: false, positiveTest: false };
  const { negStatus, posStatus } = await probeEndpoint(syntheticsStub, app, ep);
  assert.strictEqual(negStatus, 401);
  const v = classify(negStatus, posStatus, app.authPattern);
  assert.strictEqual(v.severity, 'OK');
});

test('api-gw-jwt: 認証漏れ endpoint → Neg=200 → classify CRITICAL/P1', async () => {
  const app = { appId: 'mock', env: 'stg', baseUrl, authPattern: 'api-gw-jwt' };
  const ep = { method: 'GET', path: '/leaky', rawPath: '/leaky', skipAuthCheck: false, positiveTest: false };
  const { negStatus, posStatus } = await probeEndpoint(syntheticsStub, app, ep);
  assert.strictEqual(negStatus, 200);
  const v = classify(negStatus, posStatus, app.authPattern);
  assert.strictEqual(v.severity, 'CRITICAL');
  assert.strictEqual(v.priority, 'P1');
});

test('alb-cookie-monolith: 未認証 → Neg=302 → classify OK', async () => {
  const app = { appId: 'mock', env: 'stg', baseUrl, authPattern: 'alb-cookie-monolith' };
  const ep = { method: 'GET', path: '/monolith', rawPath: '/monolith', skipAuthCheck: false, positiveTest: false };
  const { negStatus, posStatus } = await probeEndpoint(syntheticsStub, app, ep);
  assert.strictEqual(negStatus, 302);
  const v = classify(negStatus, posStatus, app.authPattern);
  assert.strictEqual(v.severity, 'OK');
});

test('skipAuthCheck=true（public）→ Neg=null → classify OK', async () => {
  const app = { appId: 'mock', env: 'stg', baseUrl, authPattern: 'api-gw-jwt' };
  const ep = { method: 'GET', path: '/protected', rawPath: '/protected', skipAuthCheck: true, positiveTest: false };
  const { negStatus } = await probeEndpoint(syntheticsStub, app, ep);
  assert.strictEqual(negStatus, null);
  const v = classify(negStatus, undefined, app.authPattern);
  assert.strictEqual(v.severity, 'OK');
});
