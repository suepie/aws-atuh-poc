# openapi-export-lambda

Central Auth Check Canary（[ADR-059](../../../../adr/059-central-auth-check-canary-architecture.md), Pattern β）の **OpenAPI Export**。
各 App Acct の deploy 時に、自アプリの API Gateway 定義を OpenAPI(oas30/YAML) で export し、
ネットワーク監査 Acct の **OpenAPI Registry(S3)** に Put する CloudFormation **Custom Resource** ハンドラ。

Central Canary はこの Registry から各アプリの `openapi.yaml` を取得し、endpoint を動的発見して probe する（[../README.md](../README.md) §0）。

## 役割

| RequestType | 動作 |
|---|---|
| `Create` / `Update` | API GW **get-export**（`oas30` / `application/yaml`）→ S3 **PutObject** |
| `Delete` | S3 上の `openapi.yaml` を **DeleteObject**（無くても冪等に SUCCESS）|

- S3 キー: `{accountId}/{apiId}/openapi.yaml`（[../README.md](../README.md) §2.2）
- バケット: `<network-audit-acct>-openapi-registry`（Versioning 有効）
- いずれの結果でも **cfn-response** で `SUCCESS`/`FAILED` を返す（失敗時も必ず `FAILED`、CFN stuck 防止）。

## 環境変数

| 変数 | 必須 | 説明 |
|---|---|---|
| `REGISTRY_BUCKET` | ✅ | OpenAPI Registry の S3 バケット名（ネットワーク監査 Acct）|
| `CROSS_ACCT_ROLE_ARN` | Cross-Acct 時 ✅ | ネットワーク監査 Acct 側の S3 書込ロール ARN。設定時は STS `AssumeRole` してから S3 に Put/Delete。未設定なら Lambda 実行ロールの既定クレデンシャル |
| `AWS_REGION` | 自動 | Lambda が自動注入（既定 `ap-northeast-1`）|

> 本 Lambda は **App Acct 側で動く**のが基本（自 Acct の API GW を export するため）。
> したがって S3 Put は通常 `CROSS_ACCT_ROLE_ARN` 経由の Cross-Acct 書込になる。
> `GetExportCommand` は同一 Acct 内の API GW に対して既定クレデンシャルで実行する。

## Service Catalog 製品からの呼ばれ方

```yaml
Resources:
  OpenApiExport:
    Type: Custom::OpenApiExport
    Properties:
      ServiceToken: !GetAtt OpenApiExportFunction.Arn
      accountId: !Ref AWS::AccountId    # S3 キーの {accountId}
      apiId: !Ref MyRestApi             # API Gateway restApiId = S3 キーの {apiId}
      stageName: prod                   # get-export 対象ステージ
```

- Create/Update で毎回 export し直すため、API 定義変更が deploy のたびに Registry へ反映される。
- `PhysicalResourceId` は `openapi-export::{accountId}::{apiId}` で安定化（Update が replacement 扱いにならないよう）。

## 検証済み事実（AWS 公式、2026-07）

- **AWS SDK v3**（`aws-sdk` v2 禁止）:
  - `@aws-sdk/client-api-gateway` の **`GetExportCommand`**。入力は `restApiId` / `stageName` / `exportType: 'oas30'`（OpenAPI 3.0。`'swagger'` は 2.0）/ `accepts: 'application/yaml'`（or `application/json`）/ 任意 `parameters`。
  - **出力 `body` は `Uint8Array`** → `new TextDecoder('utf-8').decode(res.body)` で文字列化。
  - S3 は `@aws-sdk/client-s3` の `PutObjectCommand`/`DeleteObjectCommand`。Cross-Acct は `@aws-sdk/client-sts` の `AssumeRoleCommand`。
- **CFN Custom Resource 応答**（[crpg-ref](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/crpg-ref-responses.html)）: presigned S3 URL(`ResponseURL`) へ **HTTPS PUT**。必須 `Status`(SUCCESS/FAILED)/`RequestId`/`StackId`/`LogicalResourceId`/`PhysicalResourceId`、FAILED 時 `Reason` 必須、`Data`/`NoEcho` は Create/Update のみ、**本文 4096 bytes 以下**。→ OpenAPI 本体は S3 に置き、応答にはキーのみ含める。
- **応答未送信 = CFN タイムアウト**（既定最大 1h）まで stuck。成功でも失敗でも必ず送る。PUT の `content-type` は空文字が定石。
