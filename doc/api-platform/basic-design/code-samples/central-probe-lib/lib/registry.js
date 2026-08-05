'use strict';

/**
 * App Registry（DynamoDB）を Scan して enabled なアプリ一覧を取得する。
 * README §2.1 スキーマ準拠。
 *
 * AWS SDK v3: DynamoDBClient + ScanCommand + unmarshall。
 */

const { DynamoDBClient, ScanCommand } = require('@aws-sdk/client-dynamodb');
const { unmarshall } = require('@aws-sdk/util-dynamodb');

const client = new DynamoDBClient({});

/**
 * enabled=true のアプリを全件取得（ページネーション対応）。
 * @param {string} tableName App Registry テーブル名
 * @returns {Promise<Array>} アプリレコード配列（unmarshall 済み plain object）
 */
async function scanEnabledApps(tableName) {
  const apps = [];
  let exclusiveStartKey;

  do {
    const cmd = new ScanCommand({
      TableName: tableName,
      // enabled = true のみ抽出（フィルタ）
      FilterExpression: '#enabled = :true',
      ExpressionAttributeNames: { '#enabled': 'enabled' },
      ExpressionAttributeValues: { ':true': { BOOL: true } },
      ExclusiveStartKey: exclusiveStartKey,
    });

    const res = await client.send(cmd);
    for (const item of res.Items || []) {
      apps.push(unmarshall(item));
    }
    exclusiveStartKey = res.LastEvaluatedKey;
  } while (exclusiveStartKey);

  return apps;
}

module.exports = { scanEnabledApps };
