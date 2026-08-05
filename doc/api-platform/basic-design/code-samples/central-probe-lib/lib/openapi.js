'use strict';

/**
 * OpenAPI Registry（S3）から openapi.yaml を取得・parse し、
 * probe 対象 endpoint 一覧に変換する。README §2.2 / §2.3 準拠。
 *
 * AWS SDK v3: S3Client + GetObjectCommand。
 * Body は Node.js 18+ で SdkStream（Readable）。transformToString() で文字列化。
 */

const { S3Client, GetObjectCommand } = require('@aws-sdk/client-s3');
const yaml = require('js-yaml');

const s3 = new S3Client({});

// probe 対象とする HTTP メソッド
const HTTP_METHODS = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options'];

/**
 * S3 から openapi.yaml を取得して parse する。
 * @param {string} bucket OpenAPI Registry バケット名
 * @param {string} key    openApiS3Key（例: 111122223333/abc123/openapi.yaml）
 * @returns {Promise<object>} parse 済み OpenAPI spec
 */
async function fetchSpec(bucket, key) {
  const res = await s3.send(new GetObjectCommand({ Bucket: bucket, Key: key }));
  // SDK v3: Body は IncomingMessage 互換の SdkStream。transformToString() は v3.188+ 提供。
  const text = await res.Body.transformToString('utf-8');
  return yaml.load(text);
}

/**
 * path template 内の {param} を x-canary-path-params の dummy 値で置換する。
 */
function resolvePath(pathTemplate, pathParams) {
  if (!pathParams) return pathTemplate;
  return pathTemplate.replace(/\{([^}]+)\}/g, (m, name) => {
    return pathParams[name] !== undefined ? encodeURIComponent(String(pathParams[name])) : m;
  });
}

/**
 * OpenAPI spec を probe 用 endpoint 記述子の配列に展開する。
 * アノテーション（README §2.3）を解釈する。
 *
 * @param {object} spec parse 済み OpenAPI
 * @returns {Array<{
 *   method, path, rawPath, skipAuthCheck, positiveTest,
 *   testTokenSecret, authMode, expectedRedirect, cleanup
 * }>}
 */
function extractEndpoints(spec) {
  const endpoints = [];
  const paths = (spec && spec.paths) || {};

  for (const [rawPath, pathItem] of Object.entries(paths)) {
    if (!pathItem || typeof pathItem !== 'object') continue;
    // path レベルの共通アノテーション
    const pathPathParams = pathItem['x-canary-path-params'];

    for (const method of HTTP_METHODS) {
      const op = pathItem[method];
      if (!op || typeof op !== 'object') continue;

      const pathParams = op['x-canary-path-params'] || pathPathParams;

      endpoints.push({
        method: method.toUpperCase(),
        path: resolvePath(rawPath, pathParams),
        rawPath,
        // x-synthetics-skip-auth-check: true → Negative probe 対象外（public）
        skipAuthCheck: op['x-synthetics-skip-auth-check'] === true,
        // x-canary-positive-test: true | false | 'pre-prod-only'
        positiveTest: op['x-canary-positive-test'] || false,
        // x-canary-test-token-secret: <name>（未指定なら app の testTokenSecret を使用）
        testTokenSecret: op['x-canary-test-token-secret'] || null,
        // x-canary-auth-mode: 'cookie-redirect'
        authMode: op['x-canary-auth-mode'] || null,
        // x-canary-expected-redirect: '/login'
        expectedRedirect: op['x-canary-expected-redirect'] || null,
        // x-canary-cleanup: { action, path, idFrom }
        cleanup: op['x-canary-cleanup'] || null,
      });
    }
  }

  return endpoints;
}

module.exports = { fetchSpec, extractEndpoints, resolvePath };
