'use strict';

/**
 * severity → 通知先(P1/P2/P3 SNS)の振り分けテスト（node:test）。
 * README §2.5 の 4x4 真偽値表 / §2.6 Alert 形式に準拠。
 * canary 側 lib/classify.js が出力する severity と一致することを確認する。
 */

const { test } = require('node:test');
const assert = require('node:assert');

// デフォルト ARN を環境変数で設定（DDB を使わない fallback 経路を検証）
process.env.DEFAULT_P1_TOPIC_ARN = 'arn:aws:sns:ap-northeast-1:111122223333:auth-p1-security';
process.env.DEFAULT_P2_TOPIC_ARN = 'arn:aws:sns:ap-northeast-1:111122223333:auth-p2-platform';
process.env.DEFAULT_P3_TOPIC_ARN = 'arn:aws:sns:ap-northeast-1:111122223333:auth-p3-app';
// APP_REGISTRY_TABLE 未設定 → DDB 参照せずデフォルト ARN を使う

const { metaFor, formatSubject, formatBody, SEVERITY_META } = require('../lib/format');
const { _internal } = require('../index');
const { resolveTopicArn, validateEvent } = _internal;

// --- severity → priority / routingKey の対応（§2.5）-----------------------
test('CRITICAL → P1 / p1', () => {
  const meta = metaFor('CRITICAL');
  assert.strictEqual(meta.priority, 'P1');
  assert.strictEqual(meta.routingKey, 'p1');
});

test('WARN → P2 / p2', () => {
  const meta = metaFor('WARN');
  assert.strictEqual(meta.priority, 'P2');
  assert.strictEqual(meta.routingKey, 'p2');
});

test('INFO → P3 / p3', () => {
  const meta = metaFor('INFO');
  assert.strictEqual(meta.priority, 'P3');
  assert.strictEqual(meta.routingKey, 'p3');
});

test('未知 severity は WARN(P2) に fallback', () => {
  const meta = metaFor('MYSTERY');
  assert.strictEqual(meta.priority, 'P2');
});

// --- resolveTopicArn: alertRouting 優先 / デフォルト fallback ---------------
test('resolveTopicArn: alertRouting の p1 を優先', () => {
  const routing = {
    p1: 'arn:aws:sns:ap-northeast-1:111122223333:custom-security',
    p2: 'arn:aws:sns:ap-northeast-1:111122223333:custom-platform',
    p3: 'arn:aws:sns:ap-northeast-1:111122223333:custom-app',
  };
  const r = resolveTopicArn('CRITICAL', routing);
  assert.strictEqual(r.arn, routing.p1);
  assert.strictEqual(r.priority, 'P1');
});

test('resolveTopicArn: routing 無ければデフォルト ARN に fallback', () => {
  const r = resolveTopicArn('WARN', null);
  assert.strictEqual(r.arn, process.env.DEFAULT_P2_TOPIC_ARN);
  assert.strictEqual(r.priority, 'P2');
});

test('resolveTopicArn: INFO は p3(App) デフォルトへ', () => {
  const r = resolveTopicArn('INFO', {});
  assert.strictEqual(r.arn, process.env.DEFAULT_P3_TOPIC_ARN);
  assert.strictEqual(r.priority, 'P3');
});

// --- 4x4 真偽値表の代表ケース → 通知先（severity 経由）---------------------
// canary classify.js の出力 severity を alert-router がどこへ振るか
const cases = [
  { name: 'Neg200/Pos200 認証漏れ', severity: 'CRITICAL', expectArn: process.env.DEFAULT_P1_TOPIC_ARN },
  { name: 'Neg200/Pos401 認証逆転', severity: 'CRITICAL', expectArn: process.env.DEFAULT_P1_TOPIC_ARN },
  { name: 'Neg401/Pos401 token 失効', severity: 'WARN', expectArn: process.env.DEFAULT_P2_TOPIC_ARN },
  { name: 'Neg401/Pos404 構成', severity: 'WARN', expectArn: process.env.DEFAULT_P2_TOPIC_ARN },
  { name: 'Neg404 構成ミス', severity: 'WARN', expectArn: process.env.DEFAULT_P2_TOPIC_ARN },
  { name: 'Neg401/Pos500 Backend バグ', severity: 'INFO', expectArn: process.env.DEFAULT_P3_TOPIC_ARN },
];

for (const c of cases) {
  test(`振り分け: ${c.name} (${c.severity})`, () => {
    const r = resolveTopicArn(c.severity, null);
    assert.strictEqual(r.arn, c.expectArn);
  });
}

// --- validateEvent -------------------------------------------------------
test('validateEvent: 正常イベントは null', () => {
  assert.strictEqual(validateEvent({ appId: 'x', env: 'prod', severity: 'WARN' }), null);
});

test('validateEvent: severity 欠落を検出', () => {
  assert.match(validateEvent({ appId: 'x', env: 'prod' }), /severity/);
});

// --- format: 本文に endpoint / SLA / severity 情報が含まれる ----------------
test('formatBody: appId/endpoint/SLA が含まれる', () => {
  const event = {
    appId: 'expense-api',
    env: 'prod',
    authPattern: 'api-gw-jwt',
    path: '/api/users',
    method: 'GET',
    negStatus: 200,
    posStatus: 200,
    severity: 'CRITICAL',
    reason: 'Auth missing or bypassed',
    timestamp: '2026-07-06T00:05:00Z',
  };
  const body = formatBody(event);
  assert.match(body, /expense-api/);
  assert.match(body, /GET \/api\/users/);
  assert.match(body, /即時対応/); // P1 SLA
  assert.match(body, /初動/); // CRITICAL の初動セクション
});

test('formatSubject: priority と appId を含み 100 文字以内', () => {
  const event = { appId: 'expense-api', env: 'prod', method: 'GET', path: '/api/users', severity: 'WARN' };
  const subject = formatSubject(event);
  assert.match(subject, /\[P2\]/);
  assert.match(subject, /expense-api/);
  assert.ok(subject.length <= 100);
});

test('formatBody: null(skip) status は human readable 表記', () => {
  const event = { appId: 'a', env: 'prod', authPattern: 'api-gw-jwt', path: '/health', method: 'GET', negStatus: null, posStatus: 200, severity: 'INFO', reason: 'r', timestamp: 't' };
  const body = formatBody(event);
  assert.match(body, /null \(skip/);
});

// --- SEVERITY_META の網羅性（§2.5 の 3 severity 全て定義）------------------
test('SEVERITY_META は CRITICAL/WARN/INFO を全て持つ', () => {
  for (const s of ['CRITICAL', 'WARN', 'INFO']) {
    assert.ok(SEVERITY_META[s], `${s} が未定義`);
    assert.ok(SEVERITY_META[s].sla, `${s} の SLA が未定義`);
  }
});
