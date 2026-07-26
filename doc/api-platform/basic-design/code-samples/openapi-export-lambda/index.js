'use strict';

/**
 * openapi-export-lambda / index.js
 *
 * Central Auth Check Canary (ADR-059, Pattern β) の OpenAPI Export。
 *
 * CloudFormation Custom Resource として各 App Acct の Service Catalog 製品から呼ばれ、
 * 自アプリの API Gateway 定義を OpenAPI(oas30 / YAML) で get-export し、
 * ネットワーク監査 Acct の OpenAPI Registry(S3) に Put する。
 *
 * - Create / Update : API GW get-export → S3 PutObject（キー {accountId}/{apiId}/openapi.yaml）
 * - Delete          : S3 上の openapi.yaml を DeleteObject（任意・冪等）
 *
 * Cross-Acct: 本 Lambda は App Acct 側で動く（API GW を export する）ため、
 *             S3 Put は STS AssumeRole でネットワーク監査 Acct のロールを引き受けて行う。
 *
 * AWS SDK は必ず v3。
 *   - @aws-sdk/client-api-gateway : GetExportCommand（OpenAPI 取得）
 *   - @aws-sdk/client-s3          : PutObjectCommand / DeleteObjectCommand
 *   - @aws-sdk/client-sts         : AssumeRoleCommand（Cross-Acct）
 *
 * ⚠ Custom Resource の鉄則:
 *   成功でも失敗でも必ず cfn-response を presigned S3 URL に PUT する。
 *   応答を返さないと CloudFormation はタイムアウトまで stuck する。
 */

const https = require('https');
const url = require('url');

const { APIGatewayClient, GetExportCommand } = require('@aws-sdk/client-api-gateway');
const { S3Client, PutObjectCommand, DeleteObjectCommand } = require('@aws-sdk/client-s3');
const { STSClient, AssumeRoleCommand } = require('@aws-sdk/client-sts');

const REGION = process.env.AWS_REGION || 'ap-northeast-1';
const REGISTRY_BUCKET = process.env.REGISTRY_BUCKET;         // OpenAPI Registry バケット（必須）
const CROSS_ACCT_ROLE_ARN = process.env.CROSS_ACCT_ROLE_ARN; // S3 書込用ロール（Cross-Acct 時必須）

/**
 * AssumeRole して一時クレデンシャルを得る（未設定なら undefined = 既定クレデンシャル）。
 */
async function assumeCredentials() {
  if (!CROSS_ACCT_ROLE_ARN) return undefined;

  const sts = new STSClient({ region: REGION });
  const assumed = await sts.send(
    new AssumeRoleCommand({
      RoleArn: CROSS_ACCT_ROLE_ARN,
      RoleSessionName: 'openapi-export-write',
      DurationSeconds: 900,
    })
  );
  const c = assumed.Credentials;
  return {
    accessKeyId: c.AccessKeyId,
    secretAccessKey: c.SecretAccessKey,
    sessionToken: c.SessionToken,
    expiration: c.Expiration,
  };
}

/**
 * API Gateway REST API を OpenAPI 3.0(YAML) で export する。
 * GetExportCommand の出力 body は Uint8Array なので TextDecoder で文字列化する。
 */
async function exportOpenApi(restApiId, stageName) {
  // export は API GW 本体（= App Acct 内）に対して行うので既定クレデンシャルでよい
  const apigw = new APIGatewayClient({ region: REGION });
  const res = await apigw.send(
    new GetExportCommand({
      restApiId,
      stageName,
      exportType: 'oas30',            // OpenAPI 3.0
      accepts: 'application/yaml',    // YAML で受け取る
      // parameters: { extensions: 'integrations' }, // 必要なら統合情報も含められる
    })
  );
  // res.body は Uint8Array
  return new TextDecoder('utf-8').decode(res.body);
}

/**
 * S3 キー: {accountId}/{apiId}/openapi.yaml（README §2.2）
 */
function s3KeyOf(accountId, apiId) {
  return `${accountId}/${apiId}/openapi.yaml`;
}

function physicalIdOf(props) {
  const accountId = props.accountId || 'unknown';
  const apiId = props.apiId || 'unknown';
  return `openapi-export::${accountId}::${apiId}`;
}

exports.handler = async (event, context) => {
  console.log('Received event:', JSON.stringify(event));

  const requestType = event.RequestType;
  const props = event.ResourceProperties || {};
  const physicalResourceId = event.PhysicalResourceId || physicalIdOf(props);

  try {
    if (!REGISTRY_BUCKET) {
      throw new Error('環境変数 REGISTRY_BUCKET が未設定です');
    }

    const accountId = props.accountId;   // App Acct の 12 桁アカウント ID
    const apiId = props.apiId;            // API Gateway restApiId
    const stageName = props.stageName;    // export 対象ステージ（prod 等）

    if (!accountId || !apiId) {
      throw new Error('accountId と apiId は必須です（S3 キー生成に使用）');
    }

    const key = s3KeyOf(accountId, apiId);
    const credentials = await assumeCredentials();
    const s3 = new S3Client({ region: REGION, credentials });

    if (requestType === 'Create' || requestType === 'Update') {
      if (!stageName) {
        throw new Error('stageName は Create/Update で必須です（get-export 対象）');
      }
      const yaml = await exportOpenApi(apiId, stageName);
      await s3.send(
        new PutObjectCommand({
          Bucket: REGISTRY_BUCKET,
          Key: key,
          Body: yaml,
          ContentType: 'application/yaml',
        })
      );
      console.log(`PutObject OK: s3://${REGISTRY_BUCKET}/${key} (${Buffer.byteLength(yaml)} bytes)`);
      await sendResponse(event, context, 'SUCCESS', physicalIdOf(props), {
        s3Key: key,
        bucket: REGISTRY_BUCKET,
      });
    } else if (requestType === 'Delete') {
      // stack 削除時に openapi.yaml を掃除（無くても冪等に SUCCESS）
      try {
        await s3.send(new DeleteObjectCommand({ Bucket: REGISTRY_BUCKET, Key: key }));
        console.log(`DeleteObject OK: s3://${REGISTRY_BUCKET}/${key}`);
      } catch (delErr) {
        // 既に無い等は致命ではない。ログのみ。
        console.warn('DeleteObject warning (無視):', delErr && delErr.message);
      }
      await sendResponse(event, context, 'SUCCESS', physicalResourceId);
    } else {
      throw new Error(`未知の RequestType: ${requestType}`);
    }
  } catch (err) {
    // ⚠ 失敗しても必ず FAILED を返す。返さないと CFN が stuck する。
    console.error('Handler error:', err);
    await sendResponse(
      event,
      context,
      'FAILED',
      physicalResourceId,
      {},
      String(err && err.message ? err.message : err)
    );
  }
};

/**
 * cfn-response 相当: presigned S3 URL(event.ResponseURL) へ HTTPS PUT で応答本文を送る。
 * 応答本文は 4096 bytes 以下（OpenAPI 本体は S3 に置くので応答にはキーのみ含める）。
 */
function sendResponse(event, context, status, physicalResourceId, data, reason) {
  return new Promise((resolve) => {
    const responseBody = JSON.stringify({
      Status: status,
      Reason:
        reason ||
        (status === 'FAILED'
          ? 'See CloudWatch Logs: ' + (context && context.logStreamName)
          : 'OK'),
      PhysicalResourceId: physicalResourceId || (context && context.logStreamName),
      StackId: event.StackId,
      RequestId: event.RequestId,
      LogicalResourceId: event.LogicalResourceId,
      NoEcho: false,
      Data: data || {},
    });

    console.log('Response body:', responseBody);

    const parsed = url.parse(event.ResponseURL);
    const options = {
      hostname: parsed.hostname,
      port: 443,
      path: parsed.path,
      method: 'PUT',
      headers: {
        'content-type': '',
        'content-length': Buffer.byteLength(responseBody),
      },
    };

    const req = https.request(options, (res) => {
      console.log(`cfn-response status: ${res.statusCode}`);
      res.on('data', () => {});
      res.on('end', () => resolve());
    });

    req.on('error', (e) => {
      console.error('cfn-response send error:', e);
      resolve();
    });

    req.write(responseBody);
    req.end();
  });
}
