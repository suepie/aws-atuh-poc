# central-canary-puppeteer — Central Auth Check Canary（本体）

前提: [../README.md](../README.md)（データ契約）/ [ADR-059](../../../../adr/059-central-auth-check-canary-architecture.md) / [§C-6.6.8](../../../proposal/common/06-external-api-auth-architecture.md)
Runtime: **`syn-nodejs-puppeteer-16.1`**（Lambda Node.js 22.x、namespace `@aws/synthetics-puppeteer`、AWS SDK v3）

> ⚠ 参照実装。Region / アカウント ID / ドメインは環境に合わせ、Phase 4 PoC で検証すること。

## 役割

ネットワーク監査 Acct に配置する **Central Canary**。5min 周期で全アプリの認証を外形監視する（Pattern β）。各アプリに canary を配らず、App Registry への登録で自動追随する。

## 処理フロー

```
handler (index.js)
  ├ scanEnabledApps(REGISTRY_TABLE)         … App Registry を Scan（lib/registry.js）
  └ 各アプリについて executeStep:
      ├ fetchSpec(OPENAPI_BUCKET, key)      … OpenAPI 取得（lib/openapi.js）
      ├ extractEndpoints(spec)              … アノテーション解釈で endpoint 展開
      ├ 各 endpoint: probeEndpoint()        … Negative + Positive probe（lib/probe.js）
      │     └ getBearerToken()              … OAuth Client Credentials（lib/token.js）
      ├ classify(neg, pos, authPattern)     … 4×4 真偽値表（lib/classify.js）
      ├ putMetrics(app, counts)             … CloudWatch Metrics（lib/emit.js）
      └ severity!=OK → invokeAlertRouter()  … Alert Router Lambda へ
  └ CRITICAL があれば canary を throw で FAIL（SuccessPercent アラーム発火）
```

## ファイル構成

| ファイル | 役割 |
|---|---|
| `index.js` | handler。全アプリ横断の probe オーケストレーション |
| `lib/registry.js` | App Registry（DynamoDB）Scan |
| `lib/openapi.js` | OpenAPI（S3）取得 + アノテーション解釈で endpoint 展開 |
| `lib/token.js` | test token 取得 + OAuth Client Credentials で Bearer 取得 + cache |
| `lib/probe.js` | 1 endpoint の Negative + Positive probe（authPattern 別 assertion）|
| `lib/classify.js` | 4×4 真偽値表の分類（alert-router と SSOT 共有）|
| `lib/emit.js` | CloudWatch PutMetricData + Alert Router Invoke |
| `test/classify.test.js` | classify 単体テスト（16 ケース、`node --test`）|

## 環境変数

| 変数 | 必須 | 説明 |
|---|:---:|---|
| `REGISTRY_TABLE` | ✅ | App Registry テーブル名 |
| `OPENAPI_BUCKET` | ✅ | OpenAPI Registry バケット名 |
| `ALERT_ROUTER_FN` | ✅ | Alert Router Lambda 名/ARN |
| `ENV_FILTER` | — | 監視対象環境の絞込（例 `prod`）|

## Canary 実行ロールに必要な権限

- `dynamodb:Scan`（App Registry）
- `s3:GetObject`（OpenAPI Registry）
- `secretsmanager:GetSecretValue` / `secretsmanager:DescribeSecret`（test token、CMK なら `kms:Decrypt`）
- `cloudwatch:PutMetricData`（Namespace `APIPlatform/AuthCheck`）
- `lambda:InvokeFunction`（Alert Router）
- CloudWatch Logs / S3 artifact（Synthetics 標準）

## デプロイ（CLI 例）

```bash
# lib/ を含めて zip 化（node_modules は同梱 or Lambda Layer）
zip -r canary.zip index.js lib/ node_modules/
aws synthetics create-canary \
  --name central-auth-check \
  --runtime-version syn-nodejs-puppeteer-16.1 \
  --execution-role-arn arn:aws:iam::<network-audit-acct>:role/CentralCanaryRole \
  --schedule Expression="rate(5 minutes)" \
  --artifact-s3-location s3://<artifact-bucket>/central-auth-check/ \
  --code Handler=index.handler,S3Bucket=<code-bucket>,S3Key=canary.zip \
  --run-config EnvironmentVariables="{REGISTRY_TABLE=app-registry,OPENAPI_BUCKET=openapi-registry,ALERT_ROUTER_FN=alert-router}"
```

## テスト

```bash
node --test          # classify 16 ケース
```

## 制約・要 PoC 検証（Phase 4）

| 項目 | 状態 |
|---|---|
| `api-gw-jwt` / `alb-code-jwt` の Negative + Positive | 実装済み（要実機検証）|
| `alb-cookie-monolith` の Negative（302 観測）| 実装済み。**Positive（Puppeteer ログインフロー）は index.js での分岐が未実装**（`lib/probe.js` に TODO）|
| `api-gw-iam` / `lambda-url-iam` の Positive（SigV4 署名）| **未実装**（`@aws-sdk/signature-v4` で手動署名が必要、Phase 2）|
| `x-canary-cleanup`（POST 後の DELETE）| 記述子は展開するが実行は未実装（Phase 2）|
| Multilocation（DR region 併走）| Phase 2 |
| Private API（VPC + TGW）| Phase 2（VPC config 追加）|

## 検証済み事実（一次資料）

| 事実 | URL |
|---|---|
| Synthetics runtime `syn-nodejs-puppeteer-16.1` / namespace `@aws/synthetics-*` | https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_Library_nodejs_puppeteer.html |
| `executeHttpStep(stepName, requestOptions, callback, stepConfig)` / `executeStep` | https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_Canaries_Library_Nodejs.html |
| AWS SDK v3 DynamoDB Scan / S3 GetObject / SecretsManager / CloudWatch / Lambda | https://docs.aws.amazon.com/AWSJavaScriptSDK/v3/latest/ |
