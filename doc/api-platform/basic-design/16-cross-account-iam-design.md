# 16. クロスアカウント IAM / 配布設計

前提: [00-basic-design-plan.md](00-basic-design-plan.md) / [10-external-monitoring-overview.md](10-external-monitoring-overview.md) / [17-deployment-integration-and-registration.md](17-deployment-integration-and-registration.md)
根拠: [ADR-039](../../adr/039-centralized-network-account-edge-layer.md) / [ADR-059](../../adr/059-central-auth-check-canary-architecture.md) / [ADR-061](../../adr/061-deploy-detection-pull-model.md)

---

## §16.0 前提と背景

**この章で定めること**: 共通基盤アカウント（中央）と App アカウント（各アプリ）の間で必要な IAM 権限と、その配布方法。
**方式の前提**: デプロイ検知は pull 型中央巡回 × **S3 監視資材**（[ADR-061 追記 2026-08-21](../../adr/061-deploy-detection-pull-model.md)、17 章）。クロスアカウント権限は **「中央 → App アカウントの資材読み取り」1 種類だけ**（旧 push 型の「App → 中央の書き込み」経路は廃止のまま。**資材オンリー原則**により codecommit / apigateway の読み取りも廃止）。外部ベンダー CI からのアップロードは **App アカウント内の専用ロール**（§16.2.2）に閉じる。権限を**最小限**に閉じ込める。

---

## §16.1 クロスアカウント要件の全体像

| # | 経路 | 方向 | 手段 | 権限 |
|---|---|---|---|---|
| 1 | **巡回発見（監視資材の読み取り）** | **中央 → App アカウント（読み取り）** | 発見 Lambda が `DiscoveryReadRole` に AssumeRole → **資材バケット**を読む（17 章 §17.2）| 下記 §16.2（s3 read-only）|
| 2 | **資材アップロード** | **外部ベンダー CI → App アカウント（書き込み）** | パイプライン最終段で `ArtifactUploadRole-{appId}` を Assume → 資材バケットの自アプリ prefix に Put（17 §17.3。CI からの接続方式はアプリごとの既存方式で可）| 下記 §16.2.2（`{appId}/` 限定 PutObject。**デプロイロールと分離**）|
| — | probe → アプリ | 中央 → App アカウント | **Public CloudFront URL（権限不要）** | — |
| — | probe → OAuth /token | 中央 → 認証基盤 | **Public URL（権限不要）** | — |
| — | ~~App Registry 登録 / OpenAPI Export~~ | ~~App → 中央（書き込み）~~ | **廃止**（[ADR-061](../../adr/061-deploy-detection-pull-model.md)。台帳への書き込みは中央アカウント内のみ、12 章 §12.3）| — |

→ **probe 自体はクロスアカウント権限を要さない**（実ユーザーと同じ Public 経路）。権限が要るのは**巡回の読み取りだけ**。書き込みのクロスアカウント開放が消えたことで、攻撃面・設定ミス面が push 型より小さい。

> 旧 push 型時代の「App → 中央 書き込み経路 5 案比較（中央 Lambda Invoke / AssumeRole / EventBridge Bus / DDB Resource Policy / 中央 S3）」は [ADR-061 付録](../../adr/061-deploy-detection-pull-model.md)に記録。

---

## §16.2 読み取りロール（`DiscoveryReadRole`）の設計

各 App アカウントに **読み取り専用ロールを 1 つ**配布し、中央の発見 Lambda だけが引き受けられるようにする。

```json
// 権限（App アカウント側、read-only 最小。資材バケット限定）
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket", "s3:ListBucketVersions"],
      "Resource": "arn:aws:s3:::auth-monitoring-artifacts-<accountId>"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:GetObjectVersion"],
      "Resource": "arn:aws:s3:::auth-monitoring-artifacts-<accountId>/*"
    }
  ]
}
```

> 2026-08-21 更新: 旧権限（codecommit 5 アクション + apigateway:GET）は外部 git 化と**資材オンリー原則**により全廃（[ADR-061 追記](../../adr/061-deploy-detection-pull-model.md)）。読み取り対象は資材バケットのみで、git・API GW 構成には触れない。

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
- **read-only（資材バケットの s3 読み取り）のみ**。漏洩時の影響は**監視資材（monitoring.yaml / openapi.yaml）の閲覧**（変更・削除・実行は不可。ソースコード・AWS 構成は見えない — 旧 codecommit 権限より機微性が大幅に低下）
- 信頼先を**発見 Lambda のロール 1 本に限定** + ExternalId（confused deputy 防止）
- 全 App アカウントで**同一ロール名**（`DiscoveryReadRole`）・**同一バケット命名規約**（`auth-monitoring-artifacts-{accountId}`、M-Q-17-8）にし、発見 Lambda は ARN を機械的に組み立てて AssumeRole

### §16.2.2 アップロードロール（`ArtifactUploadRole-{appId}`）の設計

外部ベンダーの CI が資材を Put するための**アプリ単位の専用ロール**。**デプロイロールとは分離**する（2026-08-21 ユーザー確定、D-M-17-7）。

```json
// 権限（App アカウント側、自アプリ prefix 限定の書き込みのみ）
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "s3:PutObject",
    "Resource": "arn:aws:s3:::auth-monitoring-artifacts-<accountId>/<appId>/*"
  }]
}
```

- **削除・読み取り権限なし**（Put のみ。旧版は Versioning が保全し、取り消しは中央/アカウント管理者の操作）
- 信頼ポリシーはベンダー CI の接続方式（IAM ロール / OIDC federation 等）に合わせてアプリごとに設定（**接続方式はアプリごとの既存方式で可** — 2026-08-21 確定）。ExternalId または OIDC の sub/aud 条件で引受け元を限定
- **1 ベンダー複数アプリでもロールはアプリ単位**（他アプリの prefix には書けない）。バケットポリシー側でも `{appId}/` 外への Put を Deny し二重化

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
| `DiscoveryReadRole` | 中央の発見 Lambda（AssumeRole）| 資材バケットの `s3:ListBucket / ListBucketVersions / GetObject / GetObjectVersion`（read-only、§16.2）|
| `ArtifactUploadRole-{appId}` | 各アプリのベンダー CI（アプリごとの接続方式で Assume）| 資材バケットの `{appId}/*` への `s3:PutObject` のみ（§16.2.2）|
| 資材バケット | —（S3。Versioning 有効 + バケットポリシーで prefix 外 Put を Deny）| — |

→ App アカウント側に置くのは**資材バケット + 読み取りロール 1 本 + アプリ単位のアップロードロール**。旧 push 型で必要だった中央への Invoke / 書き込み AssumeRole / Custom Resource 実行権限は不要のまま（中央への書き込み開放はしない）。

---

## §16.4 配布（StackSets）

| 配布物 | 手段 | 内容 |
|---|---|---|
| `DiscoveryReadRole` + **資材バケット** | **CloudFormation StackSets**（Organizations 連携・自動デプロイ）| 新規アカウント作成時も自動で配布 → 巡回が即座に読める。バケットは Versioning・暗号化・ライフサイクル込みのテンプレ（M-Q-17-8）|
| `ArtifactUploadRole-{appId}` | StackSets のテンプレ + アプリ登録時のパラメータ（appId・CI 信頼先）| アプリ追加時に払い出し。信頼先はアプリごとの CI 接続方式に合わせる（§16.2.2）|
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
| D-M-16-6 | 読み取り対象は**資材バケットのみ**（codecommit / apigateway 権限は 2026-08-21 全廃）| 資材オンリー原則（[ADR-061 追記](../../adr/061-deploy-detection-pull-model.md)）。ベンダーへの権限説明が単純・漏洩時影響も資材閲覧のみに縮小 |
| D-M-16-7 | アップロードは `ArtifactUploadRole-{appId}`（Put のみ・prefix 限定・デプロイロール分離）+ バケットポリシーで二重 Deny | 最小権限・アプリ間分離・書込経路の監査容易性（§16.2.2）|
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
