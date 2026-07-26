# Phase 4 環境セットアップ手順（P4-4 / P4-5 へ進むため）

作成: 2026-07-25
前提（確認済み）: macOS arm64 / Homebrew 5.1.15 / Docker Desktop 導入済（デーモン停止中）/ AWS CLI 2.34 + default プロファイルあり / Node 22 / cfn-guard 3.2.0 / Semgrep 1.171.0（venv）

## 0. 役割分担（重要）

| 区分 | 内容 | 実施者 |
|---|---|---|
| **U（ユーザーのみ可）** | Docker Desktop 起動 / AWS 認証情報・アカウント準備 / 課金の承認 | **あなた** |
| **C（私が代行可）** | ツール導入コマンド実行 / SAM テンプレ・スクリプト作成 / LocalStack リソース作成 / テスト実行・検証 | Claude |

→ **あなたが手を動かすのは主に 3 点**（Docker 起動 / AWS 準備 / 課金判断）。それ以外は私が Bash で実行できます。

---

## Step 1: canary を SAM local で動かす（P4-3 full、ローカル・ほぼ無料）

### U（あなた）がやること
1. **Docker Desktop を起動**（GUI アプリ、デーモンが要る）
   ```bash
   open -a Docker      # 起動後 30-60 秒待つ
   docker ps           # エラーが出なければ OK
   ```
2. **artifact 用 S3 バケット**（canary が HAR/スクリーンショットを置く。実 AWS に 1 個、月数円）
   ```bash
   aws sts get-caller-identity          # プロファイル有効性を確認（実 AWS 問い合わせ）
   aws s3 mb s3://cw-syn-$(aws sts get-caller-identity --query Account --output text)-ap-northeast-1
   ```
   - ※完全オフラインにしたい場合は artifact を無効化する payload も可能（私が設定）

### C（私）が代行できること
3. SAM CLI 導入: `brew install aws-sam-cli`
4. [aws-samples/synthetics-canary-local-debugging-sample](https://github.com/aws-samples/synthetics-canary-local-debugging-sample) の `template.yml` / `cw-synthetics.js` shim を流用し、CodeUri を `central-canary-puppeteer/` に向けた **SAM テンプレ + event.json を作成**
5. `sam build && sam local invoke -e event.json` を実行・結果検証

→ **あなたは「Docker 起動 + S3 バケット 1 個」だけ**。残りは私がやります。

---

## Step 2: Lambda / canary の呼び先を LocalStack で用意（P4-2 full、ローカル・無料）

canary/Lambda が読む App Registry(DynamoDB) / OpenAPI Registry(S3) / SNS / Secrets を LocalStack でエミュレートする。

### U（あなた）がやること
1. **Docker Desktop 起動**（Step 1 と同じ、LocalStack は Docker で動く）

### C（私）が代行できること
2. LocalStack 導入: `brew install localstack/tap/localstack-cli`（or `pip install localstack`）
3. 起動: `localstack start -d` → `localstack status services`
4. `awslocal`（or `aws --endpoint-url=http://localhost:4566`）で **App Registry テーブル / OpenAPI バケット / SNS トピック / Secret を作成するスクリプト**を用意・実行
5. Lambda handler（app-registry / openapi-export / alert-router）を LocalStack エンドポイント向けに実行し、DynamoDB Put / Custom Resource 応答 / SNS Publish の実挙動を検証

> ⚠ **LocalStack は CloudWatch Synthetics 非対応**。canary 本体は Step 1（SAM local）で動かし、その probe 先・データ源として LocalStack を併用する構成になります。

---

## Step 3: 実 AWS サンドボックス 1 アカウント（P4-4、少額課金）

ローカルで検証しきれない部分（実 Synthetics canary の定期実行 / 実 CloudWatch Metrics / Alarm）を単一アカウントで確認。

### U（あなた）がやること
1. **本番と分離したサンドボックス AWS アカウント**（or 専用リージョン）と、デプロイ権限のあるプロファイル
2. **課金の承認**（DynamoDB/S3/SNS/Synthetics canary 実行で**月 $5-15 程度**）
3. `aws cloudformation deploy`（or `cdk deploy`）の **実行承認**

### C（私）が代行できること
4. 一式の CloudFormation/CDK テンプレ（App Registry テーブル / OpenAPI バケット / canary / Alert Router / SNS / IAM ロール）を作成
5. デプロイ後の疎通確認スクリプト（App 登録 → canary 実行 → Metrics → Alert）

---

## Step 4: マルチアカウント E2E（P4-5、本番相当課金）

### U（あなた）がやること
1. **AWS Organizations で 2 アカウント**（ネットワーク監査 Acct + App Acct）
2. CloudFront + WAF + Origin Protection の配置（ADR-039、他組織管理の可能性は BD-Q-01）
3. Cross-Acct Role の信頼関係承認
4. 本番相当課金の承認

### C（私）が代行できること
5. Cross-Acct Role / StackSets / Origin Protection 込みの IaC 作成（章 16 の設計に基づく）
6. E2E 疎通（CloudFront 経由 probe → 4×4 分類 → Alert）の検証シナリオ

---

## 推奨する最短ルート

| 目的 | 最小手順（あなた）| 得られる確証 |
|---|---|---|
| **canary を実際に動かしたい** | Docker 起動 + S3 バケット 1 個 → 私が SAM 一式実行 | Synthetics ランタイムでの実動作 |
| **Lambda SDK 実挙動を見たい** | Docker 起動のみ → 私が LocalStack 一式実行 | DynamoDB/SNS/Custom Resource の実挙動 |
| **本番同等を確認したい** | サンドボックスアカウント + 課金承認 | 実 Metrics / Alarm / canary スケジュール |

→ **まず「Docker Desktop 起動」だけしてもらえれば、Step 1（SAM local canary）+ Step 2（LocalStack）の大半を私が実行**できます。実 AWS 課金は Step 3 以降で初めて必要。

## 費用の目安

| 環境 | 課金 |
|---|---|
| Step 1-2（ローカル SAM + LocalStack）| ほぼ無料（artifact S3 のみ数円）|
| Step 3（サンドボックス単一）| 月 $5-15 |
| Step 4（マルチアカウント E2E）| 構成次第（Shield Advanced 使わなければ月 $数十）|

## 注意点

- **LocalStack は Synthetics 非対応** → canary 本体は SAM local か実 AWS
- Docker Desktop のリソース割当（メモリ 4GB+ 推奨、SAM の Lambda コンテナ + LocalStack）
- サンドボックスは**本番と必ず分離**（誤爆防止）
- `aws sts get-caller-identity` 等は実 AWS を叩くため、どのアカウントに繋がるか確認してから
