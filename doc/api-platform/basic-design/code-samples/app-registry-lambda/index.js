'use strict';

/**
 * app-registry-lambda / index.js
 *
 * Central Auth Check Canary (ADR-059, Pattern β) の App Registry CRUD。
 *
 * CloudFormation Custom Resource として各 App Acct の Service Catalog 製品から呼ばれ、
 * ネットワーク監査 Acct の DynamoDB(App Registry) に自アプリのメタデータを登録/更新/削除する。
 *
 * - Create / Update : PutItem（README §2.1 の全属性）
 * - Delete          : DeleteItem
 *
 * Cross-Acct: 本 Lambda が App Acct 側で動く場合は STS AssumeRole で
 *             ネットワーク監査 Acct のロールを引き受けてから DynamoDB を書く。
 *             （本 Lambda 自体をネットワーク監査 Acct に置き、App Acct から
 *              Lambda を invoke する構成なら CROSS_ACCT_ROLE_ARN 未設定でよい）
 *
 * AWS SDK は必ず v3。
 *   - @aws-sdk/client-dynamodb        : 低レベルクライアント
 *   - @aws-sdk/lib-dynamodb           : DocumentClient（marshalling 自動）
 *   - @aws-sdk/client-sts             : AssumeRole（Cross-Acct 時）
 *
 * ⚠ Custom Resource の鉄則:
 *   成功でも失敗でも必ず cfn-response を presigned S3 URL に PUT する。
 *   応答を返さないと CloudFormation はタイムアウト（既定最大 1h）まで stuck する。
 */

const https = require('https');
const url = require('url');

const { DynamoDBClient } = require('@aws-sdk/client-dynamodb');
const { DynamoDBDocumentClient, PutCommand, DeleteCommand } = require('@aws-sdk/lib-dynamodb');
const { STSClient, AssumeRoleCommand } = require('@aws-sdk/client-sts');

const TABLE_NAME = process.env.TABLE_NAME;                 // App Registry テーブル名（必須）
const CROSS_ACCT_ROLE_ARN = process.env.CROSS_ACCT_ROLE_ARN; // Cross-Acct 書込用ロール（任意）
const REGION = process.env.AWS_REGION || 'ap-northeast-1';

/**
 * DynamoDB DocumentClient を生成する。
 * CROSS_ACCT_ROLE_ARN が設定されていれば AssumeRole した一時クレデンシャルを使う。
 */
async function buildDocClient() {
  let credentials; // undefined の場合は Lambda 実行ロールの既定クレデンシャル

  if (CROSS_ACCT_ROLE_ARN) {
    const sts = new STSClient({ region: REGION });
    const assumed = await sts.send(
      new AssumeRoleCommand({
        RoleArn: CROSS_ACCT_ROLE_ARN,
        RoleSessionName: 'app-registry-write',
        DurationSeconds: 900,
      })
    );
    const c = assumed.Credentials;
    credentials = {
      accessKeyId: c.AccessKeyId,
      secretAccessKey: c.SecretAccessKey,
      sessionToken: c.SessionToken,
      expiration: c.Expiration,
    };
  }

  const ddb = new DynamoDBClient({ region: REGION, credentials });
  // 空文字列など undefined を除去したいので removeUndefinedValues を有効化
  return DynamoDBDocumentClient.from(ddb, {
    marshallOptions: { removeUndefinedValues: true, convertClassInstanceToMap: true },
  });
}

/**
 * ResourceProperties から App Registry レコード（README §2.1）を構築する。
 * CloudFormation は Properties の値をすべて文字列化して渡すため、
 * enabled のような Boolean は文字列→Boolean へ正規化する。
 */
function buildItem(props) {
  const appId = props.appId;
  const env = props.env;
  if (!appId || !env) {
    throw new Error('appId と env は必須です (PK/SK)');
  }

  // enabled: "true"/"false"(文字列) or Boolean を受け付ける
  const enabledRaw = props.enabled;
  const enabled =
    typeof enabledRaw === 'boolean' ? enabledRaw : String(enabledRaw).toLowerCase() === 'true';

  // alertRouting は Map。CFN 経由で {p1,p2,p3} が来る想定。
  const alertRouting = props.alertRouting || {};

  return {
    appId,                                   // PK (S)
    env,                                     // SK (S)
    baseUrl: props.baseUrl,                  // S
    authPattern: props.authPattern,          // S (enum)
    openApiS3Key: props.openApiS3Key,        // S
    testTokenSecret: props.testTokenSecret,  // S
    alertRouting,                            // M { p1, p2, p3 }
    enabled,                                 // BOOL
    registeredAt: props.registeredAt || new Date().toISOString(), // S ISO8601
  };
}

/**
 * PhysicalResourceId は「アプリ+環境」で安定させる。
 * これを Create/Update/Delete で一貫させることで、CFN が誤って replacement 扱いにしない。
 */
function physicalIdOf(props) {
  return `app-registry::${props.appId || 'unknown'}::${props.env || 'unknown'}`;
}

exports.handler = async (event, context) => {
  console.log('Received event:', JSON.stringify(event));

  const requestType = event.RequestType;
  const props = event.ResourceProperties || {};
  const physicalResourceId =
    event.PhysicalResourceId || physicalIdOf(props);

  try {
    if (!TABLE_NAME) {
      throw new Error('環境変数 TABLE_NAME が未設定です');
    }

    const doc = await buildDocClient();

    if (requestType === 'Create' || requestType === 'Update') {
      const item = buildItem(props);
      await doc.send(new PutCommand({ TableName: TABLE_NAME, Item: item }));
      console.log(`PutItem OK: ${item.appId}/${item.env}`);
      await sendResponse(event, context, 'SUCCESS', physicalIdOf(props), {
        appId: item.appId,
        env: item.env,
      });
    } else if (requestType === 'Delete') {
      // Delete: PK/SK が取れる時だけ削除。取れなければ「既に無い」とみなし SUCCESS。
      if (props.appId && props.env) {
        await doc.send(
          new DeleteCommand({
            TableName: TABLE_NAME,
            Key: { appId: props.appId, env: props.env },
          })
        );
        console.log(`DeleteItem OK: ${props.appId}/${props.env}`);
      } else {
        console.log('Delete: appId/env 不明のためスキップ（冪等扱い）');
      }
      await sendResponse(event, context, 'SUCCESS', physicalResourceId);
    } else {
      throw new Error(`未知の RequestType: ${requestType}`);
    }
  } catch (err) {
    // ⚠ 失敗しても必ず FAILED を返す。返さないと CFN が stuck する。
    console.error('Handler error:', err);
    await sendResponse(event, context, 'FAILED', physicalResourceId, {}, String(err && err.message ? err.message : err));
  }
};

/**
 * cfn-response 相当: presigned S3 URL(event.ResponseURL) へ HTTPS PUT で応答本文を送る。
 * （aws-cfn-response モジュールに依存せず自前実装。応答本文は 4096 bytes 以下）
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
        // presigned URL への PUT では Content-Type を空文字にするのが定石
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
      // ここで throw すると応答未送信のまま関数が終わり CFN が stuck するので、
      // ログのみ残して resolve する（CFN 側はタイムアウトで FAILED になる）。
      console.error('cfn-response send error:', e);
      resolve();
    });

    req.write(responseBody);
    req.end();
  });
}
