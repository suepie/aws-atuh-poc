'use strict';

/**
 * 中央認証チェック — handler（README §0 / §2 準拠）。
 *
 * ネットワーク監査アカウントに配置し、M1 デプロイ差分（自動）/ M3 フル監査（手動）で全アプリの認証を外形監視する（18 章）。
 *   1. App Registry（DynamoDB）を Scan して enabled なアプリ一覧を取得
 *   2. 各アプリの OpenAPI Registry(S3) から openapi.yaml を取得 → endpoint 展開
 *   3. 各 endpoint を Negative + Positive で probe（CloudFront 経由 = Origin Protection 準拠）
 *   4. 4×4 真偽値表で分類 → CloudWatch Metrics（per-app）
 *   5. severity が OK 以外は Alert Router Lambda へ非同期 Invoke
 *
 * Runtime: syn-nodejs-puppeteer-16.1（namespace @aws/synthetics-puppeteer, AWS SDK v3）
 *
 * 環境変数:
 *   REGISTRY_TABLE     App Registry テーブル名（必須）
 *   OPENAPI_BUCKET     OpenAPI Registry バケット名（必須）
 *   ALERT_ROUTER_FN    Alert Router Lambda 名/ARN（必須）
 *   ENV_FILTER         監視対象環境の絞込（任意、例 "prod"。未指定なら全 env）
 */

const synthetics = require('@aws/synthetics-puppeteer');
const log = require('@aws/synthetics-logger');

const { scanEnabledApps } = require('./lib/registry');
const { fetchSpec, extractEndpoints } = require('./lib/openapi');
const { probeEndpoint } = require('./lib/probe');
const { classify } = require('./lib/classify');
const { putMetrics, invokeAlertRouter } = require('./lib/emit');

function nowIso() {
  // Synthetics runtime は Date を許容（Lambda 実行環境）
  return new Date().toISOString();
}

/**
 * 1 アプリを probe する。endpoint ごとに分類し、CRITICAL/WARN/INFO は Alert Router へ送る。
 * @returns {object} counts { OK, CRITICAL, WARN, INFO, probed }
 */
async function checkApp(app, alertRouterFn) {
  const counts = { OK: 0, CRITICAL: 0, WARN: 0, INFO: 0, probed: 0 };

  // OpenAPI 取得
  let spec;
  try {
    spec = await fetchSpec(process.env.OPENAPI_BUCKET, app.openApiS3Key);
  } catch (e) {
    log.error(`[${app.appId}] OpenAPI 取得失敗: ${e.message}`);
    // OpenAPI が引けない = 構成問題。WARN として 1 件計上し Platform に通知。
    counts.WARN += 1;
    await invokeAlertRouter(alertRouterFn, {
      appId: app.appId, env: app.env, authPattern: app.authPattern,
      path: '(openapi)', method: '-', negStatus: null, posStatus: null,
      severity: 'WARN', reason: `OpenAPI fetch failed: ${e.message}`, timestamp: nowIso(),
    });
    return counts;
  }

  const endpoints = extractEndpoints(spec);
  log.info(`[${app.appId}/${app.env}] ${endpoints.length} endpoints`);

  for (const ep of endpoints) {
    counts.probed += 1;
    let negStatus;
    let posStatus;
    try {
      ({ negStatus, posStatus } = await probeEndpoint(synthetics, app, ep));
    } catch (e) {
      // probe 自体が例外 = 到達不能等。WARN 扱い。
      log.warn(`[${app.appId}] probe error ${ep.method} ${ep.rawPath}: ${e.message}`);
      counts.WARN += 1;
      continue;
    }

    const verdict = classify(negStatus, posStatus, app.authPattern);
    counts[verdict.severity] = (counts[verdict.severity] || 0) + 1;

    if (verdict.severity !== 'OK') {
      // OK 以外は Alert Router へ（4×4 分類は README §2.5、送信形式は §2.6）
      await invokeAlertRouter(alertRouterFn, {
        appId: app.appId,
        env: app.env,
        authPattern: app.authPattern,
        path: ep.rawPath,
        method: ep.method,
        negStatus: negStatus === undefined ? null : negStatus,
        posStatus: posStatus === undefined ? null : posStatus,
        severity: verdict.severity,
        reason: verdict.reason,
        timestamp: nowIso(),
      });
    }
  }

  return counts;
}

const authCheckCanary = async function () {
  const table = process.env.REGISTRY_TABLE;
  const alertRouterFn = process.env.ALERT_ROUTER_FN;
  const envFilter = process.env.ENV_FILTER || null;

  if (!table || !process.env.OPENAPI_BUCKET || !alertRouterFn) {
    throw new Error('REGISTRY_TABLE / OPENAPI_BUCKET / ALERT_ROUTER_FN は必須');
  }

  let apps = await scanEnabledApps(table);
  if (envFilter) apps = apps.filter((a) => a.env === envFilter);
  log.info(`監視対象アプリ: ${apps.length} 件${envFilter ? `（env=${envFilter}）` : ''}`);

  let totalCritical = 0;
  const summary = [];

  for (const app of apps) {
    // アプリ単位を executeStep で括る（Synthetics のステップ計測に載せる）
    const counts = await synthetics.executeStep(`app:${app.appId}:${app.env}`, async function () {
      return checkApp(app, alertRouterFn);
    });
    await putMetrics(app, counts);
    totalCritical += counts.CRITICAL || 0;
    summary.push({ appId: app.appId, env: app.env, ...counts });
  }

  log.info(`集計: ${JSON.stringify(summary)}`);

  // CRITICAL（認証漏れ）が 1 件でもあれば canary 自体を FAIL させ、
  // Synthetics のアラーム（SuccessPercent < 100）を発火させる。
  if (totalCritical > 0) {
    throw new Error(`CRITICAL auth findings: ${totalCritical} 件（詳細は Alert Router / CloudWatch Metrics）`);
  }
};

exports.handler = async function () {
  return await authCheckCanary();
};
