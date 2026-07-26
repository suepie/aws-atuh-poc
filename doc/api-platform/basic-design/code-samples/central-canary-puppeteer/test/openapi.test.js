'use strict';

/**
 * openapi.js の extractEndpoints（アノテーション解釈、README §2.3）単体テスト。
 * S3 取得は伴わない純ロジック。実行: node --test test/openapi.test.js
 */

const { test } = require('node:test');
const assert = require('node:assert');
const yaml = require('js-yaml');
const { extractEndpoints, resolvePath } = require('../lib/openapi');

const SPEC = yaml.load(`
openapi: 3.0.0
paths:
  /api/users:
    get:
      x-canary-positive-test: true
      x-canary-test-token-secret: canary-central-readonly
  /api/users/{userId}:
    get:
      x-canary-path-params:
        userId: canary-probe-user-001
  /api/orders:
    post:
      x-canary-positive-test: pre-prod-only
      x-canary-cleanup:
        action: DELETE
        path: /api/orders/{orderId}
        idFrom: response.body.orderId
  /_/health:
    get:
      x-synthetics-skip-auth-check: true
      x-canary-positive-test: true
  /dashboard:
    get:
      x-canary-auth-mode: cookie-redirect
      x-canary-expected-redirect: /login
`);

test('全 GET/POST の endpoint を抽出', () => {
  const eps = extractEndpoints(SPEC);
  // 5 path × 各 1 method = 5
  assert.strictEqual(eps.length, 5);
});

test('x-synthetics-skip-auth-check → skipAuthCheck=true', () => {
  const eps = extractEndpoints(SPEC);
  const health = eps.find((e) => e.rawPath === '/_/health');
  assert.strictEqual(health.skipAuthCheck, true);
});

test('x-canary-positive-test の値を保持（true / pre-prod-only）', () => {
  const eps = extractEndpoints(SPEC);
  assert.strictEqual(eps.find((e) => e.rawPath === '/api/users').positiveTest, true);
  assert.strictEqual(eps.find((e) => e.rawPath === '/api/orders').positiveTest, 'pre-prod-only');
});

test('x-canary-path-params で path template を dummy 置換', () => {
  const eps = extractEndpoints(SPEC);
  const u = eps.find((e) => e.rawPath === '/api/users/{userId}');
  assert.strictEqual(u.path, '/api/users/canary-probe-user-001');
  assert.strictEqual(u.rawPath, '/api/users/{userId}'); // rawPath は元のまま
});

test('cookie-redirect アノテーションを保持', () => {
  const eps = extractEndpoints(SPEC);
  const d = eps.find((e) => e.rawPath === '/dashboard');
  assert.strictEqual(d.authMode, 'cookie-redirect');
  assert.strictEqual(d.expectedRedirect, '/login');
});

test('x-canary-cleanup を保持', () => {
  const eps = extractEndpoints(SPEC);
  const o = eps.find((e) => e.rawPath === '/api/orders');
  assert.strictEqual(o.cleanup.action, 'DELETE');
});

test('resolvePath: params なしはそのまま', () => {
  assert.strictEqual(resolvePath('/a/{id}', null), '/a/{id}');
  assert.strictEqual(resolvePath('/a/{id}', { id: 'x' }), '/a/x');
});
