'use strict';

/**
 * CloudWatch Metrics emit（README §2.4）と Alert Router Lambda Invoke（§2.6）。
 *
 * AWS SDK v3:
 *   CloudWatchClient + PutMetricDataCommand
 *   LambdaClient + InvokeCommand（Event 非同期呼び出し）
 */

const { CloudWatchClient, PutMetricDataCommand } = require('@aws-sdk/client-cloudwatch');
const { LambdaClient, InvokeCommand } = require('@aws-sdk/client-lambda');

const cw = new CloudWatchClient({});
const lambda = new LambdaClient({});

const NAMESPACE = 'APIPlatform/AuthCheck';

// severity → metric 名（README §2.4）
const SEVERITY_METRIC = {
  OK: 'AuthCheckPassed',
  CRITICAL: 'AuthCheckCritical',
  WARN: 'AuthCheckWarn',
  INFO: 'AuthCheckInfo',
};

/**
 * per-app の集計結果を CloudWatch に PutMetricData する。
 * PutMetricData は 1 回 20 MetricDatum まで。app 単位で呼ぶ想定なので余裕あり。
 *
 * @param {object} app   { appId, env, authPattern }
 * @param {object} counts { OK, CRITICAL, WARN, INFO, probed }
 */
async function putMetrics(app, counts) {
  const dimensions = [
    { Name: 'AppId', Value: app.appId },
    { Name: 'Env', Value: app.env },
    { Name: 'AuthPattern', Value: app.authPattern },
  ];
  const now = new Date();

  const metricData = [];
  for (const [sev, metricName] of Object.entries(SEVERITY_METRIC)) {
    metricData.push({
      MetricName: metricName,
      Dimensions: dimensions,
      Timestamp: now,
      Value: counts[sev] || 0,
      Unit: 'Count',
    });
  }
  metricData.push({
    MetricName: 'EndpointsProbed',
    Dimensions: dimensions,
    Timestamp: now,
    Value: counts.probed || 0,
    Unit: 'Count',
  });

  await cw.send(new PutMetricDataCommand({
    Namespace: NAMESPACE,
    MetricData: metricData,
  }));
}

/**
 * Alert Router Lambda へ 1 件のアラートイベントを非同期 Invoke する（README §2.6 形式）。
 * @param {string} functionName alert-router Lambda 名/ARN
 * @param {object} event { appId, env, authPattern, path, method, negStatus, posStatus, severity, reason, timestamp }
 */
async function invokeAlertRouter(functionName, event) {
  await lambda.send(new InvokeCommand({
    FunctionName: functionName,
    InvocationType: 'Event', // 非同期（fire-and-forget）
    Payload: Buffer.from(JSON.stringify(event)),
  }));
}

module.exports = { putMetrics, invokeAlertRouter, NAMESPACE, SEVERITY_METRIC };
