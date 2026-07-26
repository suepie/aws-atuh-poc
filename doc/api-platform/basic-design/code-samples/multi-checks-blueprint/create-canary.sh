#!/usr/bin/env bash
#
# create-canary.sh — CloudWatch Synthetics Multi Checks Blueprint canary 作成サンプル
#
# 前提:
#   - blueprint-config.json を ZIP 化して渡す（Multi Checks の唯一必須ファイル）。
#   - Code.BlueprintTypes=["multi-checks"] を指定し、Handler は指定しない
#     （両方指定すると ValidationException）。
#   - RuntimeVersion は syn-nodejs-3.0 以上。本サンプルは本プロジェクト規約の
#     syn-nodejs-5.1 を使用（README §3 Runtime バージョン参照）。
#   - ExecutionRoleArn には Secrets Manager 参照権限
#     （secretsmanager:GetSecretValue + secretsmanager:DescribeSecret、
#      顧客管理鍵なら kms:Decrypt）を付与しておくこと。
#
# 一次資料:
#   https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_Canaries_MultiCheck_Blueprint.html
#   https://docs.aws.amazon.com/AmazonSynthetics/latest/APIReference/API_CreateCanary.html
#
set -euo pipefail

# ---- 環境に合わせて置換 -------------------------------------------------------
REGION="ap-northeast-3"                       # 大阪リージョン想定
ACCOUNT_ID="111122223333"                     # ネットワーク監査 Acct
CANARY_NAME="auth-check-expense-api"          # 小文字/数字/ハイフン/アンダースコアのみ (^[0-9a-z_\-]+$)
RUNTIME="syn-nodejs-5.1"
EXEC_ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/synthetics-auth-check-exec-role"
ARTIFACT_BUCKET="s3://${ACCOUNT_ID}-synthetics-artifacts/auth-check/"
SCHEDULE_EXPR="rate(5 minutes)"               # ADR-059 = 5min 周期
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# -----------------------------------------------------------------------------

# 1) blueprint-config.json を ZIP 化。
#    synthetics.json は Multi Checks では任意。canary 名 / schedule / runtime /
#    role / 環境変数は本 CreateCanary API パラメータで与えるため同梱しない。
ZIP_PATH="$(mktemp -d)/multi-checks.zip"
( cd "${SCRIPT_DIR}" && zip -j "${ZIP_PATH}" blueprint-config.json )

# 2) canary 作成。
#    --code に BlueprintTypes="multi-checks" を渡し Handler は付けない。
aws synthetics create-canary \
  --region "${REGION}" \
  --name "${CANARY_NAME}" \
  --runtime-version "${RUNTIME}" \
  --execution-role-arn "${EXEC_ROLE_ARN}" \
  --artifact-s3-location "${ARTIFACT_BUCKET}" \
  --schedule "Expression=${SCHEDULE_EXPR},DurationInSeconds=0" \
  --run-config "TimeoutInSeconds=60,ActiveTracing=false,EnvironmentVariables={CW_SYNTHETICS_LOG_LEVEL=INFO}" \
  --code "ZipFile=fileb://${ZIP_PATH},BlueprintTypes=multi-checks" \
  --success-retention-period-in-days 31 \
  --failure-retention-period-in-days 31 \
  --tags "Project=api-platform,Component=central-auth-check,ADR=ADR-059"

echo "Created multi-checks canary: ${CANARY_NAME}"
echo "Debug tip: DEBUG ログは EnvironmentVariables に CW_SYNTHETICS_LOG_LEVEL=DEBUG を設定。"

# --- ExecutionRoleArn に必要な Secrets Manager インラインポリシー例 -----------
# {
#   "Version": "2012-10-17",
#   "Statement": [
#     {
#       "Effect": "Allow",
#       "Action": [
#         "secretsmanager:GetSecretValue",
#         "secretsmanager:DescribeSecret"
#       ],
#       "Resource": [
#         "arn:aws:secretsmanager:ap-northeast-3:111122223333:secret:canary-central-readonly-*",
#         "arn:aws:secretsmanager:ap-northeast-3:111122223333:secret:canary-central-apikey-*"
#       ]
#     }
#     // 顧客管理鍵で暗号化している場合は kms:Decrypt を対象鍵に追加
#   ]
# }
#
# ↑ に加え CreateCanary が要求する基本権限（s3:PutObject / s3:GetBucketLocation /
#   s3:ListAllMyBuckets / cloudwatch:PutMetricData / logs:CreateLogGroup /
#   logs:CreateLogStream / logs:PutLogEvents）と、信頼ポリシーに
#   lambda.amazonaws.com プリンシパルが必要。
