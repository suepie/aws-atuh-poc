# app-registry-lambda

Central Auth Check Canary（[ADR-059](../../../../adr/059-central-auth-check-canary-architecture.md), Pattern β）の **App Registry CRUD**。
各 App アカウントの deploy 時に、自アプリのメタデータを共通基盤アカウントの DynamoDB(App Registry) に登録する CloudFormation **Custom Resource** ハンドラ。

Central Canary はこの App Registry を 5min 周期で Scan して監視対象を動的発見する（[../README.md](../README.md) §0）。

## 役割

| RequestType | 動作 |
|---|---|
| `Create` / `Update` | App Registry(DynamoDB) に **PutItem**（[../README.md](../README.md) §2.1 の全属性）|
| `Delete` | 該当レコードを **DeleteItem**（`appId`/`env` 不明時は冪等スキップ）|

いずれの結果でも **cfn-response**（`event.ResponseURL` へ HTTPS PUT）で `SUCCESS`/`FAILED` を返す。
失敗時も必ず `FAILED` を返すため、CloudFormation が stuck しない。

## 環境変数

| 変数 | 必須 | 説明 |
|---|---|---|
| `TABLE_NAME` | ✅ | App Registry DynamoDB テーブル名（PK=`appId`, SK=`env`）|
| `CROSS_ACCT_ROLE_ARN` | 任意 | 共通基盤アカウント側の書込ロール ARN。設定時は STS `AssumeRole` してから DynamoDB を書く。未設定なら Lambda 実行ロールの既定クレデンシャルを使用（= 本 Lambda を共通基盤アカウントに置く構成）|
| `AWS_REGION` | 自動 | Lambda が自動注入（既定 `ap-northeast-1`）|

## Service Catalog 製品からの呼ばれ方

各 App アカウントの Service Catalog 製品（CFN テンプレート）内で `Custom::AppRegistryEntry` として宣言し、
`ServiceToken` に本 Lambda の ARN を指定、`Properties` に §2.1 の属性を渡す。

```yaml
Resources:
  AppRegistryEntry:
    Type: Custom::AppRegistryEntry
    Properties:
      ServiceToken: !Sub arn:aws:lambda:${AWS::Region}:<common-platform-acct>:function:app-registry-lambda
      appId: expense-api
      env: prod
      baseUrl: https://expense.example.com
      authPattern: api-gw-jwt          # §2.1 enum
      openApiS3Key: 111122223333/abc123/openapi.yaml
      testTokenSecret: canary-central-readonly
      alertRouting:
        p1: arn:aws:sns:...:security
        p2: arn:aws:sns:...:platform
        p3: arn:aws:sns:...:app-team-x
      enabled: "true"                  # CFN は文字列化して渡す → コード側で Boolean 正規化
      # registeredAt 省略時は Lambda 側で ISO8601 を自動付与
```

- `PhysicalResourceId` は `app-registry::{appId}::{env}` で安定化させ、Update が誤って replacement 扱いにならないようにしている。
- Delete は stack 削除・製品終了時に発火し、該当アプリを Registry から外す（= 監視対象から外れる）。

## 構成パターンと クロスアカウント

```
[本 Lambda を共通基盤アカウントに配置]（推奨・シンプル）
  App アカウントの Service Catalog → ServiceToken(クロスアカウント Lambda invoke)
  → Lambda は同一 アカウント内の DynamoDB を書く（CROSS_ACCT_ROLE_ARN 不要）

[本 Lambda を App アカウントに配置]
  → CROSS_ACCT_ROLE_ARN に共通基盤アカウントのロールを設定
  → STS AssumeRole 後に DynamoDB へ PutItem/DeleteItem
```

## 検証済み事実（AWS 公式、2026-07）

- **AWS SDK v3**（`aws-sdk` v2 禁止）: DynamoDB は `@aws-sdk/client-dynamodb` + `@aws-sdk/lib-dynamodb` の `DynamoDBDocumentClient`（`PutCommand`/`DeleteCommand`）。クロスアカウントは `@aws-sdk/client-sts` の `AssumeRoleCommand`。
- **CFN Custom Resource 応答**（[crpg-ref](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/crpg-ref-responses.html)）: presigned S3 URL(`ResponseURL`) へ **HTTPS PUT**。本文の必須フィールドは `Status`(SUCCESS/FAILED), `RequestId`, `StackId`, `LogicalResourceId`, `PhysicalResourceId`。`Reason` は FAILED 時必須。`Data`/`NoEcho` は Create/Update のみ。**本文 4096 bytes 以下**。
- **応答未送信 = CFN タイムアウト**（既定最大 1h）まで stuck。だから成功でも失敗でも必ず送る。PUT の `content-type` は空文字が定石。
- `PhysicalResourceId` は同一リソースの全応答で一致させる。変わると CFN は replacement（旧リソースへ Delete）と解釈する。
