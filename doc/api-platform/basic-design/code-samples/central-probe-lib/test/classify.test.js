'use strict';

/**
 * classify（4×4 真偽値表）の単体テスト。README §2.5 準拠。
 * 実行: node --test
 */

const { test } = require('node:test');
const assert = require('node:assert');
const { classify } = require('../lib/classify');

// --- 正常系 ---------------------------------------------------------------
test('Neg=401 + Pos=200 → OK（認証が正しく機能）', () => {
  const r = classify(401, 200, 'api-gw-jwt');
  assert.strictEqual(r.severity, 'OK');
  assert.strictEqual(r.priority, null);
});

test('Neg=403 + Pos=204 → OK', () => {
  const r = classify(403, 204, 'api-gw-jwt');
  assert.strictEqual(r.severity, 'OK');
});

test('Neg=401 + Pos 未実施 → OK（Negative のみ）', () => {
  const r = classify(401, undefined, 'api-gw-jwt');
  assert.strictEqual(r.severity, 'OK');
});

test('Cookie モノリス Neg=302 + Pos 未実施 → OK', () => {
  const r = classify(302, undefined, 'alb-cookie-monolith');
  assert.strictEqual(r.severity, 'OK');
});

test('public skip（Neg=null）→ OK', () => {
  const r = classify(null, 200, 'api-gw-jwt');
  assert.strictEqual(r.severity, 'OK');
});

// --- CRITICAL（認証漏れ）---------------------------------------------------
test('Neg=200 + Pos=200 → CRITICAL/P1（認証 missing）', () => {
  const r = classify(200, 200, 'api-gw-jwt');
  assert.strictEqual(r.severity, 'CRITICAL');
  assert.strictEqual(r.priority, 'P1');
});

test('Neg=200 + Pos=401 → CRITICAL/P1（認証逆転）', () => {
  const r = classify(200, 401, 'api-gw-jwt');
  assert.strictEqual(r.severity, 'CRITICAL');
  assert.strictEqual(r.priority, 'P1');
});

test('Neg=204（2xx）+ Pos=200 → CRITICAL（2xx は全て通過扱い）', () => {
  const r = classify(204, 200, 'api-gw-jwt');
  assert.strictEqual(r.severity, 'CRITICAL');
});

// --- WARN（テスト構成 / token 失効）----------------------------------------
test('Neg=401 + Pos=401 → WARN/P2（token 失効）', () => {
  const r = classify(401, 401, 'api-gw-jwt');
  assert.strictEqual(r.severity, 'WARN');
  assert.strictEqual(r.priority, 'P2');
});

test('Neg=401 + Pos=404 → WARN/P2（endpoint 不在）', () => {
  const r = classify(401, 404, 'api-gw-jwt');
  assert.strictEqual(r.severity, 'WARN');
});

test('Neg=404 → WARN/P2（probe 構成ミス）', () => {
  const r = classify(404, undefined, 'api-gw-jwt');
  assert.strictEqual(r.severity, 'WARN');
});

test('想定外 Neg=500 → WARN', () => {
  const r = classify(500, undefined, 'api-gw-jwt');
  assert.strictEqual(r.severity, 'WARN');
});

// --- INFO（Backend バグ）--------------------------------------------------
test('Neg=401 + Pos=500 → INFO/P3（Backend バグ、認証は OK）', () => {
  const r = classify(401, 500, 'api-gw-jwt');
  assert.strictEqual(r.severity, 'INFO');
  assert.strictEqual(r.priority, 'P3');
});

test('Neg=403 + Pos=503 → INFO/P3', () => {
  const r = classify(403, 503, 'api-gw-jwt');
  assert.strictEqual(r.severity, 'INFO');
});

// --- authPattern 差（Cookie モノリスは 302 が認証拒否）----------------------
test('Cookie モノリス Neg=200 → CRITICAL（302 でないと漏れ）', () => {
  const r = classify(200, undefined, 'alb-cookie-monolith');
  assert.strictEqual(r.severity, 'CRITICAL');
});

test('JWT で Neg=302 は認証拒否とみなさない → WARN（想定外 status）', () => {
  const r = classify(302, undefined, 'api-gw-jwt');
  assert.strictEqual(r.severity, 'WARN');
});
