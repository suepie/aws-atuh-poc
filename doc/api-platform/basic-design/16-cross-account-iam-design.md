# 16. クロスアカウント IAM / 配布設計

前提: [00-basic-design-plan.md](00-basic-design-plan.md) / [10-external-monitoring-overview.md](10-external-monitoring-overview.md) / [17-deployment-integration-and-registration.md](17-deployment-integration-and-registration.md)
根拠: [ADR-039](../../adr/039-centralized-network-account-edge-layer.md) / [ADR-059](../../adr/059-central-auth-check-canary-architecture.md) / [ADR-061](../../adr/061-deploy-detection-pull-model.md)

---

## §16.0 前提と背景

**この章で定めること**: 共通基盤アカウント（中央）と App アカウント（各アプリ）の間で必要な IAM 権限と、その配布方法。
**方式の前提**: デプロイ検知は pull 型中央巡回（[ADR-061](../../adr/061-deploy-detection-pull-model.md)）。これにより、クロスアカウント権限は **「中央 → App アカウントの読み取り」1 種類だけ**になった（旧 push 型の「App → 中央の書き込み」経路は廃止）。権限を**最小限**に閉じ込める。

---

## §16.1 クロスアカウント要件の全体像

| # | 経路 | 方向 | 手段 | 権限 |
|---|---|---|---|---|
| 1 | **巡回発見（リポジトリ読み取り）** | **中央 → App アカウント（読み取り）** | 発見 Lambda が `DiscoveryReadRole` に AssumeRole → **CodeCommit** を読む（17 章 §17.2）| 下記 §16.2（codecommit read-only）|
| — | probe → アプリ | 中央 → App アカウント | **Public CloudFront URL（権限不要）** | — |
| — | probe → OAuth /token | 中央 → 認証基盤 | **Public URL（権限不要）** | — |
| — | ~~App Registry 登録 / OpenAPI Export~~ | ~~App → 中央（書き込み）~~ | **廃止**（[ADR-061](../../adr/061-deploy-detection-pull-model.md)。台帳への書き込みは中央アカウント内のみ、12 章 §12.3）| — |

→ **probe 自体はクロスアカウント権限を要さない**（実ユーザーと同じ Public 経路）。権限が要るのは**巡回の読み取りだけ**。書き込みのクロスアカウント開放が消えたことで、攻撃面・設定ミス面が push 型より小さい。

> 旧 push 型時代の「App → 中央 書き込み経路 5 案比較（中央 Lambda Invoke / AssumeRole / EventBridge Bus / DDB Resource Policy / 中央 S3）」は [ADR-061 付録](../../adr/061-deploy-detection-pull-model.md)に記録。

---

## §16.2 読み取りロール（`DiscoveryReadRole`）の設計

各 App アカウントに **読み取り専用ロールを 1 つ**配布し、中央の発見 Lambda だけが引き受けられるようにする。

```json
// 権限（App アカウント側、read-only 最小）
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "codecommit:ListRepositories",
      "codecommit:GetBranch",        // 先端コミット ID
      "codecommit:GetCommit",
      "codecommit:GetDifferences",   // 変更パス（モノレポのアプリ特定）
      "codecommit:GetFile",          // monitoring.yaml / openapi.yaml 取得
      "apigateway:GET"               // stage deploymentId 併読（手動変更のデプロイ反映検知。ADR-061 追記 2026-08-19）
    ],
    "Resource": "*"
  }]
}
```

```json
// 信頼ポリシー（引受け元を発見 Lambda ロールに限定 + ExternalId）
{
  "Effect": "Allow",
  "Principal": { "AWS": "arn:aws:iam::<common-platform-acct>:role/DiscoveryLambdaRole" },
  "Action": "sts:AssumeRole",
  "Condition": { "StringEquals": { "sts:ExternalId": "auth-impl-discovery" } }
}
```

**設計のポイント**:
- **read-only（codecommit 読み取り + apigateway:GET）のみ**。漏洩時の影響は**ソースコードと API GW 構成（Authorizer 設定等）の閲覧**（変更・削除・実行は不可）。いずれも閲覧自体が機微なため、信頼先限定・ExternalId・CloudTrail での AssumeRole 監査を必須とする
- 信頼先を**発見 Lambda のロール 1 本に限定** + ExternalId（confused deputy 防止）
- 全 App アカウントで**同一ロール名**（`DiscoveryReadRole`）にし、発見 Lambda は `arn:aws:iam::{accountId}:role/DiscoveryReadRole` を機械的に組み立てて AssumeRole
- 対象リポジトリを絞りたい場合は `Resource` を命名規約（例 `arn:aws:codecommit:*:*:*-api`）で限定可能（M-Q-16-3）

---

## §16.3 必要な IAM 一覧

**共通基盤アカウント側**

| ロール | 使い手 | 権限 |
|---|---|---|
| `DiscoveryLambdaRole` | 発見 Lambda | アカウント列挙（⚠ `organizations:ListAccounts` は管理アカウント限定のため、方式は M-Q-17-2 で確定: 案 a なら管理アカウントの列挙用ロールへの `sts:AssumeRole` / 案 b なら `ssm:GetParameter`）/ `sts:AssumeRole`（各 App の DiscoveryReadRole）/ `s3:PutObject・GetObject・ListBucket`（Monitoring Registry の `registry/*` + `openapi/*`）/ `lambda:InvokeFunction`（認証実装チェック Lambda）|
| `CentralProbeRole` | 認証実装チェック Lambda | `s3:GetObject・ListBucket`（Monitoring Registry：台帳 + spec）/ `secretsmanager:GetSecretValue` / `cloudwatch:PutMetricData` / `lambda:InvokeFunction`（Alert Router）|
| `alert-router-lambda-role` | Alert Router | `s3:GetObject`（`registry/*`、alertRouting 解決）/ `sns:Publish` |

**各 App アカウント側（StackSets で配布）**

| ロール | 使い手 | 権限 |
|---|---|---|
| `DiscoveryReadRole` | 中央の発見 Lambda（AssumeRole）| `codecommit:ListRepositories / GetBranch / GetCommit / GetDifferences / GetFile` + `apigateway:GET`（deploymentId 併読）（いずれも read-only、§16.2）|

→ App アカウント側に置くのは**読み取りロール 1 つだけ**。旧 push 型で必要だった Invoke ロール / 書き込み AssumeRole / Custom Resource 実行権限はすべて不要になった。

---

## §16.4 配布（StackSets）

| 配布物 | 手段 | 内容 |
|---|---|---|
| `DiscoveryReadRole` | **CloudFormation StackSets**（Organizations 連携・自動デプロイ）| 新規アカウント作成時も自動で配布 → 巡回が即座に読める |
| Service Catalog 製品 | Portfolio 共有（Organizations / RAM）| 認証必須 / Origin Protection / タグの「守られた API の型」（17 章 §17.1。登録系 Custom Resource は含まない）|

---

## §16.5 ⚠ ROSA 側前提との責任分界（BD-Q-01）

アカウント配置は **2 つに分離**している：**インターネット境界（CloudFront/WAF、ADR-039）＝ネットワーク監査アカウント**（ROSA 側 P-18 で他組織管理になる可能性）と、**認証実装確認処理のリソース群（App Registry / OpenAPI Registry / 認証実装チェック Lambda / Alert Router / Secrets）＝共通基盤アカウント（自社管理）**。

| 影響 | 対応 |
|---|---|
| CloudFront / Origin Protection の管理主体（ネットワーク監査アカウント）| 他組織なら、probe 先 URL / Origin Protection secret の運用を他組織と調整 |
| 認証実装確認処理の配置 | **共通基盤アカウント（自社管理）に置くため、境界が他組織管理になっても再設計は不要**。影響は上記の probe 先経路調整のみ |

→ P-18 確定時に probe 先経路（境界越え）を差分改訂する（BD-Q-01）。確認処理リソース自体の配置は影響を受けない。巡回の読み取り経路（中央 → App）も境界を通らないため影響なし。

---

## §16.6 設計判断

| ID | 判断 | 根拠 |
|---|---|---|
| D-M-16-1 | クロスアカウントは**中央 → App の読み取り AssumeRole 1 種のみ**（書き込み経路は廃止）| pull 型統一（[ADR-061](../../adr/061-deploy-detection-pull-model.md)）。攻撃面・設定ミス面の最小化 |
| D-M-16-2 | probe は Public URL 経由でクロスアカウント権限不要 | 実 UX 同一 + 権限を巡回読み取りだけに限定 |
| D-M-16-3 | `DiscoveryReadRole` は read-only + 信頼先 1 本 + ExternalId + 全アカウント同一名 | 漏洩時影響の最小化・confused deputy 防止・機械的な AssumeRole |
| D-M-16-4 | 配布は StackSets（Organizations 自動デプロイ）| 新規アカウントにも自動追随 → 巡回の空白を作らない |
| D-M-16-5 | ROSA 側 P-18 確定まで自管理前提で記述、差分改訂 | 前提変更に追随（BD-Q-01）|

---

## §16.7 未決事項

| ID | 内容 |
|---|---|
| BD-Q-01 | ROSA 側 P-18（監査アカウント他組織管理）確定時の probe 先経路改訂 |
| M-Q-16-1 | `DiscoveryReadRole` の配布対象範囲（Organizations 全体 / OU 単位、17 章 M-Q-17-3 と連動）|
| M-Q-16-2 | 発見 Lambda の並列度・スロットリング（アカウント数増加時の API コール制御）|

---

## §16.x 関連ドキュメント

- [ADR-061](../../adr/061-deploy-detection-pull-model.md) — pull 型統一の決定 + 旧 push 型書き込み 5 案比較（付録）
- [17-deployment-integration-and-registration.md](17-deployment-integration-and-registration.md) — 巡回フロー（このロールの使い手）
- [12-app-registry-design.md](12-app-registry-design.md) — 台帳の書き込み権限（中央のみ）
