'use strict';

/**
 * Alert Router Lambda（ADR-059 中央認証チェック / Pattern β）
 *
 * canary（central-probe-lib）から Alert イベント（README §2.6）を受け、
 * severity（CRITICAL/WARN/INFO）に基づき P1/P2/P3 の SNS トピックへ Publish する。
 *
 * 通知先 SNS ARN の解決:
 *   - Alert イベント自体には ARN が含まれない（§2.6）。
 *   - App Registry（DynamoDB, §2.1）の該当レコードの `alertRouting` M
 *     ( { p1, p2, p3 } ) から appId/env で引く。
 *   - App Registry に該当が無い / alertRouting 欠落時は、環境変数の
 *     デフォルト SNS ARN（DEFAULT_P1/P2/P3_TOPIC_ARN）に fallback する。
 *
 * 分類は canary 側 lib/classify.js が実施済み（severity を受領するだけ）。
 * severity → priority(P1/P2/P3) の対応は lib/format.js（§2.5 の SSOT）と一致。
 *
 * 環境変数:
 *   APP_REGISTRY_TABLE       App Registry DynamoDB テーブル名（任意。未設定なら DDB 参照せずデフォルト ARN）
 *   DEFAULT_P1_TOPIC_ARN     P1(Security) デフォルト SNS ARN（fallback）
 *   DEFAULT_P2_TOPIC_ARN     P2(Platform) デフォルト SNS ARN（fallback）
 *   DEFAULT_P3_TOPIC_ARN     P3(App)      デフォルト SNS ARN（fallback）
 *   AWS_REGION               Lambda ランタイムが自動設定
 */

const { SNSClient, PublishCommand } = require('@aws-sdk/client-sns');
const { DynamoDBClient, GetItemCommand } = require('@aws-sdk/client-dynamodb');
const { metaFor, formatSubject, formatBody } = require('./lib/format');

const snsClient = new SNSClient({});
const ddbClient = new DynamoDBClient({});

const APP_REGISTRY_TABLE = process.env.APP_REGISTRY_TABLE;

// 環境変数のデフォルト ARN（routingKey → env var）
const DEFAULT_ARNS = {
  p1: process.env.DEFAULT_P1_TOPIC_ARN,
  p2: process.env.DEFAULT_P2_TOPIC_ARN,
  p3: process.env.DEFAULT_P3_TOPIC_ARN,
};

/**
 * App Registry（DynamoDB）から alertRouting を取得。
 * テーブル未設定 / 取得失敗時は null（呼び出し側でデフォルトに fallback）。
 */
async function fetchAlertRouting(appId, env) {
  if (!APP_REGISTRY_TABLE) return null;
  try {
    const res = await ddbClient.send(
      new GetItemCommand({
        TableName: APP_REGISTRY_TABLE,
        Key: {
          appId: { S: appId },
          env: { S: env },
        },
        ProjectionExpression: 'alertRouting',
      }),
    );
    const m = res.Item && res.Item.alertRouting && res.Item.alertRouting.M;
    if (!m) return null;
    // DynamoDB M {p1:{S:arn},...} → {p1: arn, ...}
    const routing = {};
    for (const key of ['p1', 'p2', 'p3']) {
      if (m[key] && typeof m[key].S === 'string') routing[key] = m[key].S;
    }
    return routing;
  } catch (err) {
    console.error(`[alert-router] App Registry 取得失敗 appId=${appId} env=${env}:`, err);
    return null;
  }
}

/**
 * severity + alertRouting から Publish 先 SNS ARN を解決。
 * 優先: App Registry の alertRouting[routingKey] → デフォルト ARN。
 */
function resolveTopicArn(severity, routing) {
  const meta = metaFor(severity); // { routingKey: 'p1'|'p2'|'p3', ... }
  const key = meta.routingKey;
  const fromRegistry = routing && routing[key];
  const arn = fromRegistry || DEFAULT_ARNS[key];
  return { arn, routingKey: key, priority: meta.priority };
}

/**
 * Alert イベントの最小バリデーション。
 */
function validateEvent(event) {
  if (!event || typeof event !== 'object') return 'event が object でない';
  for (const f of ['appId', 'env', 'severity']) {
    if (!event[f]) return `必須フィールド ${f} が欠落`;
  }
  return null;
}

/**
 * 1 件の Alert イベントを処理して SNS へ Publish。
 */
async function routeOne(event) {
  const validationError = validateEvent(event);
  if (validationError) {
    throw new Error(`Alert イベント不正: ${validationError}`);
  }

  // OK（通知不要）は通常 canary が送ってこないが、来た場合は skip
  if (event.severity === 'OK') {
    console.log(`[alert-router] severity=OK のため通知 skip appId=${event.appId}`);
    return { published: false, reason: 'severity OK' };
  }

  const routing = await fetchAlertRouting(event.appId, event.env);
  const { arn, routingKey, priority } = resolveTopicArn(event.severity, routing);

  if (!arn) {
    // ARN 未解決 = 設定不備。エラーを投げて可視化（DLQ / retry へ）。
    throw new Error(
      `SNS ARN 未解決 severity=${event.severity} routingKey=${routingKey} ` +
        `(App Registry alertRouting も DEFAULT_${routingKey.toUpperCase()}_TOPIC_ARN も未設定)`,
    );
  }

  const publishInput = {
    TopicArn: arn,
    Subject: formatSubject(event),
    Message: formatBody(event),
    MessageAttributes: {
      severity: { DataType: 'String', StringValue: event.severity },
      priority: { DataType: 'String', StringValue: priority },
      appId: { DataType: 'String', StringValue: event.appId },
      env: { DataType: 'String', StringValue: event.env },
    },
  };

  const res = await snsClient.send(new PublishCommand(publishInput));
  console.log(
    `[alert-router] published ${priority} appId=${event.appId} env=${event.env} ` +
      `path=${event.path} messageId=${res.MessageId} arn=${arn}`,
  );
  return { published: true, priority, topicArn: arn, messageId: res.MessageId };
}

/**
 * Lambda ハンドラ。
 * canary からの直接 Invoke は単一の Alert イベント（§2.6）を想定。
 * 配列で複数件渡された場合も処理する（バッチ耐性）。
 */
exports.handler = async (event) => {
  const events = Array.isArray(event) ? event : [event];
  const results = [];
  const errors = [];

  for (const e of events) {
    try {
      results.push(await routeOne(e));
    } catch (err) {
      console.error('[alert-router] routing error:', err);
      errors.push({ appId: e && e.appId, error: err.message });
    }
  }

  // 1 件でも失敗したら throw して Lambda を失敗扱いに（retry / DLQ 発火）
  if (errors.length > 0) {
    const err = new Error(`alert routing に ${errors.length} 件失敗: ${JSON.stringify(errors)}`);
    err.results = results;
    throw err;
  }

  return { routed: results.length, results };
};

// テスト用に内部関数を公開
exports._internal = { resolveTopicArn, validateEvent, fetchAlertRouting, routeOne };
