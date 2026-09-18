# 16. クロスアカウント IAM / 配布設計

前提: [00-basic-design-plan.md](00-basic-design-plan.md) / [10-external-monitoring-overview.md](10-external-monitoring-overview.md) / [17-deployment-integration-and-registration.md](17-deployment-integration-and-registration.md)
根拠: [ADR-039](../../adr/039-centralized-network-account-edge-layer.md) / [ADR-059](../../adr/059-central-auth-check-canary-architecture.md) / [ADR-061](../../adr/061-deploy-detection-pull-model.md)

---

## §16.0 前提と背景

**この章で定めること**: 共通基盤アカウント（中央）と App アカウント（各アプリ）の間で必要な IAM 権限と、その**作成主体・オンボーディング手順**。
**方式の前提**: デプロイ検知は pull 型中央巡回 × **認証構成情報（S3）の VersionId 比較**（[ADR-061 追記 2026-08-21](../../adr/061-deploy-detection-pull-model.md)、17 章）。クロスアカウント権限は **「中央 → App アカウントの認証構成情報読み取り」1 種類だけ**（旧 push 型の「App → 中央の書き込み」経路は廃止のまま。**認証構成情報オンリー原則**により codecommit / apigateway の読み取りも廃止）。外部ベンダー CI からのアップロードは **App アカウント内の専用ロール**（§16.2.2）に閉じる。権限を**最小限**に閉じ込める。

**作成主体（2026-09-16 ユーザー確定）**: 認証構成情報連携バケットと各ロールは、**中央が StackSets で全アカウントへ自動配布するのではなく、中央が提供するテンプレートと手順にもとづいて案件側（アプリ／ベンダー）が自アカウントに作成する**。これに伴い、巡回の対象アカウントは **SSM Parameter Store の登録リスト（申請ベース）**で管理する（§16.4 / §16.4.1）。組織全体を列挙しても「どのアカウントが監視対象か」は判別できなくなるためである（判別のために全アカウントへ AssumeRole を試すと、対象外アカウントで必ず失敗して `DiscoveryAccountErrors`（MM-3）が常時発報し、本物の障害が埋もれる）。

---

## §16.1 クロスアカウント要件の全体像

| # | 経路 | 方向 | 手段 | 権限 | 作成主体 |
|---|---|---|---|---|---|
| 0 | **巡回対象アカウントの取得** | **中央アカウント内（クロスアカウントではない）** | 対象検索 Lambda が **SSM Parameter Store の登録リスト**（`/auth-monitoring/target-accounts`）を読む（§16.4.1、17 §17.2.1 ①）| `ssm:GetParameter`（対象パラメータ 1 本に限定）| 中央（登録の申請は案件側）|
| 1 | **巡回発見（認証構成情報の読み取り）** | **中央 → App アカウント（読み取り）** | 対象検索 Lambda（旧称: 発見 Lambda）が `DiscoveryReadRole` に AssumeRole → **認証構成情報連携バケット**を読む（17 章 §17.2）| 下記 §16.2（s3 read-only）| **案件側**（中央提供テンプレート、§16.4）|
| 2 | **認証構成情報アップロード** | **外部ベンダー CI → App アカウント（書き込み）** | パイプライン最終段で `ArtifactUploadRole-{appId}` を Assume → 認証構成情報連携バケットの自アプリ prefix に Put（17 §17.3。CI からの接続方式はアプリごとの既存方式で可）| 下記 §16.2.2（`{appId}/` 限定 PutObject。**デプロイロールと分離**）| **案件側**（中央提供テンプレート、§16.4）|
| — | probe → アプリ | 中央 → App アカウント | **Public CloudFront URL（権限不要）** | — | — |
| — | probe → OAuth /token | 中央 → 認証基盤 | **Public URL（権限不要）** | — | — |
| — | ~~App Registry 登録 / OpenAPI Export~~ | ~~App → 中央（書き込み）~~ | **廃止**（[ADR-061](../../adr/061-deploy-detection-pull-model.md)。台帳への書き込みは中央アカウント内のみ、12 章 §12.3）| — | — |

→ **probe 自体はクロスアカウント権限を要さない**（実ユーザーと同じ Public 経路）。権限が要るのは**巡回の読み取りだけ**。書き込みのクロスアカウント開放が消えたことで、攻撃面・設定ミス面が push 型より小さい。

> 旧 push 型時代の「App → 中央 書き込み経路 5 案比較（中央 Lambda Invoke / AssumeRole / EventBridge Bus / DDB Resource Policy / 中央 S3）」は [ADR-061 付録](../../adr/061-deploy-detection-pull-model.md)に記録。

---

## §16.2 読み取りロール（`DiscoveryReadRole`）の設計

各 App アカウントに **読み取り専用ロールを 1 つ**置き、中央の対象検索 Lambda だけが引き受けられるようにする。**作成するのは案件側**（中央提供のテンプレートを使用、§16.4）。ロール名・バケット名・信頼ポリシーは**規約どおりに作られていること**が前提で、逸脱すると中央からの AssumeRole が失敗する（MM-3 で検知、§16.4.2）。

```json
// 権限（App アカウント側、read-only 最小。認証構成情報連携バケット限定）
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

> 2026-08-21 更新: 旧権限（codecommit 5 アクション + apigateway:GET）は外部 git 化と**認証構成情報オンリー原則**により全廃（[ADR-061 追記](../../adr/061-deploy-detection-pull-model.md)）。読み取り対象は認証構成情報連携バケットのみで、git・API GW 構成には触れない。

```json
// 信頼ポリシー（引受け元を対象検索 Lambda ロールに限定 + ExternalId）
{
  "Effect": "Allow",
  "Principal": { "AWS": "arn:aws:iam::<common-platform-acct>:role/DiscoveryLambdaRole" },
  "Action": "sts:AssumeRole",
  "Condition": { "StringEquals": { "sts:ExternalId": "auth-impl-discovery" } }
}
```

**設計のポイント**:
- **read-only（認証構成情報連携バケットの s3 読み取り）のみ**。漏洩時の影響は**認証構成情報（monitoring.yaml / openapi.yaml）の閲覧**（変更・削除・実行は不可。ソースコード・AWS 構成は見えない — 旧 codecommit 権限より機微性が大幅に低下）
- 信頼先を**対象検索 Lambda のロール 1 本に限定** + ExternalId（confused deputy 防止）。**信頼先 ARN（`DiscoveryLambdaRole` の ARN）と ExternalId は中央が案件側へ伝える**（§16.4.1）
- 全 App アカウントで**同一ロール名**（`DiscoveryReadRole`）・**同一バケット命名規約**（`auth-monitoring-artifacts-{accountId}`、M-Q-17-8）にし、対象検索 Lambda は ARN を機械的に組み立てて AssumeRole。案件側作成であっても**この命名規約は変更不可**（テンプレートで固定する）

### §16.2.2 アップロードロール（`ArtifactUploadRole-{appId}`）の設計

外部ベンダーの CI が認証構成情報を Put するための**アプリ単位の専用ロール**。**デプロイロールとは分離**する（2026-08-21 ユーザー確定、D-M-17-7）。**作成するのは案件側**（中央提供のテンプレートを使用、§16.4）。

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
| `DiscoveryLambdaRole` | 対象検索 Lambda | **`ssm:GetParameter`（`/auth-monitoring/target-accounts` の 1 本に限定。巡回対象アカウントの登録リスト取得、§16.4.1。2026-09-16 確定により Organizations 系権限は不要）** / `sts:AssumeRole`（各 App の DiscoveryReadRole）/ `s3:PutObject・GetObject・ListBucket`（認証構成情報配置バケット の `registry/*` + `openapi/*`。**`GetObject` は If-Match 条件付き書き込みにも必須**、12 §12.1.2）/ `lambda:InvokeFunction`（認証実装チェック Lambda）/ **`sns:Publish`（P2 Platform トピックに限定）**（対象検索-12 構成情報不備通知 / 対象検索-13 棚卸しアラート）/ **`cloudwatch:PutMetricData`**（対象検索-14 巡回結果メトリクス `DiscoveryLastSuccess` / `DiscoveryAccountErrors`）|
| `CentralProbeRole` | 認証実装チェック Lambda | `s3:GetObject・ListBucket`（認証構成情報配置バケット：台帳 + spec）/ `secretsmanager:GetSecretValue` / `cloudwatch:PutMetricData` / `lambda:InvokeFunction`（**アラート検知 Lambda ※旧称: Alert Router + 自関数 ARN**。全量検査（モード2）の親が**自分自身をアプリ単位に fan-out invoke する**ため、自関数 ARN も Resource に含める。全量-04）|
| `alert-router-lambda-role` | アラート検知 Lambda | `s3:GetObject`（`registry/*`、alertRouting 解決）/ `sns:Publish` |

**各 App アカウント側（中央提供テンプレートで案件側が作成、§16.4）**

| ロール | 使い手 | 権限 |
|---|---|---|
| `DiscoveryReadRole` | 中央の対象検索 Lambda（AssumeRole）| 認証構成情報連携バケットの `s3:ListBucket / ListBucketVersions / GetObject / GetObjectVersion`（read-only、§16.2）|
| `ArtifactUploadRole-{appId}` | 各アプリのベンダー CI（アプリごとの接続方式で Assume）| 認証構成情報連携バケットの `{appId}/*` への `s3:PutObject` のみ（§16.2.2）|
| 認証構成情報連携バケット | —（S3。Versioning 有効 + バケットポリシーで prefix 外 Put を Deny）| — |

→ App アカウント側に置くのは**認証構成情報連携バケット + 読み取りロール 1 本 + アプリ単位のアップロードロール**。旧 push 型で必要だった中央への Invoke / 書き込み AssumeRole / Custom Resource 実行権限は不要のまま（中央への書き込み開放はしない）。

**中央アカウント側の設定物（ロール以外）**

| 設定物 | 内容 |
|---|---|
| SSM Parameter `/auth-monitoring/target-accounts` | 巡回対象アカウントの登録リスト。**中央管理**（アプリ側が書き換えられる場所に置かない）。形式は §16.4.1 |

---

## §16.4 テンプレート提供とオンボーディング（2026-09-16 確定）

**方針**: 中央は**作成用テンプレートと手順を提供する**。実際に自アカウントへ作成するのは**案件側（アプリ／ベンダー）**である。中央から全アカウントへ StackSets で自動配布する旧方式は採らない。

| 提供物 | 提供者 | 作成者 | 内容 |
|---|---|---|---|
| 認証構成情報連携バケットのテンプレート | 中央 | **案件側** | `auth-monitoring-artifacts-{accountId}`。**Versioning 有効**・暗号化・旧版ライフサイクル・バケットポリシー（`{appId}/` 外への Put を Deny）込み（M-Q-17-8）|
| `DiscoveryReadRole` のテンプレート | 中央 | **案件側** | 中央の対象検索 Lambda だけが引き受けられる読み取り専用ロール（§16.2）。信頼先 ARN と ExternalId は中央が伝える値を埋める |
| `ArtifactUploadRole-{appId}` のテンプレート | 中央 | **案件側** | `{appId}/*` 限定 PutObject（§16.2.2）。信頼先はアプリごとの CI 接続方式に合わせて案件側が設定 |
| 作成手順書・チェックリスト | 中央 | — | テンプレートの適用方法、埋める値、作成後の確認手順 |
| Service Catalog 製品 | 中央 | — | Portfolio 共有（Organizations / RAM）。認証必須 / Origin Protection / タグの「守られた API の型」（17 章 §17.1。登録系 Custom Resource は含まない）|

### §16.4.1 オンボーディングの流れ

| # | 実施者 | 作業 | 成果物・伝達事項 |
|---|---|---|---|
| 0 | 中央 | 案件側へ**テンプレート・手順書**と、埋めるべき値（**`DiscoveryLambdaRole` の ARN** = `arn:aws:iam::<common-platform-acct>:role/DiscoveryLambdaRole`、**ExternalId** = `auth-impl-discovery`）を伝える | テンプレート一式 + パラメータ表 |
| 1 | **案件側** | **認証構成情報連携バケット**を作成（`auth-monitoring-artifacts-{accountId}`、Versioning 有効）| バケット |
| 2 | **案件側** | **`DiscoveryReadRole`** を作成（信頼先 = 上記 ARN、Condition = 上記 ExternalId、権限 = 当該バケットの read-only）| ロール |
| 3 | **案件側** | **`ArtifactUploadRole-{appId}`** を作成（`{appId}/*` 限定 PutObject、信頼先は自社 CI の接続方式）| ロール |
| 4 | **案件側** | 中央へ**アカウント ID の登録を依頼**（申請）。アプリ責任者・連絡先を添える | 登録申請 |
| 5 | **中央** | SSM Parameter Store の**登録リストへ追加**（`/auth-monitoring/target-accounts`）| 次回巡回から対象化 |
| 6 | 中央 | 初回巡回で AssumeRole とバケット読み取りが成功することを確認（失敗は §16.4.2）| 巡回成功 |

> **【注意】信頼先 ARN と ExternalId は中央が案件側へ伝える必要がある**。案件側はこの 2 値を知らないと `DiscoveryReadRole` を正しく作れないため、手順 0 で必ず伝達する（値は秘匿情報ではないが、誤記すると中央からの AssumeRole が全件失敗する）。

**登録リストの仕様**:

| 項目 | 内容 |
|---|---|
| 置き場所 | 中央アカウントの SSM Parameter Store。例: `/auth-monitoring/target-accounts` |
| 管理主体 | **中央**（アプリ側が書き換えられる場所に置かない。監視対象を勝手に外せない）|
| 形式 | `[{ "accountId": "…", "appOwner": "…", "registeredAt": "…" }]` の JSON 配列 |
| 読み取り権限 | `DiscoveryLambdaRole` の `ssm:GetParameter`（**このパラメータ 1 本に限定**、§16.3）|

### §16.4.2 オンボーディング未完了の検知

**登録リストに載っているのに、バケット／ロールが無い（または信頼ポリシーが誤っている）= オンボーディング未完了**である。この状態は巡回時の AssumeRole 失敗またはバケット読み取り失敗として現れ、**`DiscoveryAccountErrors`（MM-3）で気づく**（対象検索-03 / 04 / 14）。中央は当該アカウントを巡回対象から一時除外しつつ、**案件側へ作成完了を督促する**。

> 旧方式（StackSets 自動配布）ではこの状態が発生しなかったため、MM-3 は純粋な障害シグナルだった。本方式では **MM-3 が「障害」と「オンボーディング未完了」の両方を運ぶ**ため、Runbook で切り分け（登録日からの経過・初回巡回か否か）を定める。

### §16.4.3 「登録漏れが構造的にゼロ」の範囲（重要）

本方式の変更により、**「登録漏れが構造的に起きない」と言える範囲が狭まる**。

| 単位 | 仕組み | 登録漏れ |
|---|---|---|
| **アプリ単位** | 連携バケットに `{appId}/monitoring.yaml` を置けば**自動発見・自動登録**（17 §17.2.1）| **構造的にゼロ（従来どおり維持）**。中央が発見する側であり、アプリ側の登録処理に依存しない |
| **アカウント単位** | **申請ベース**（案件側が作成 → 中央へ依頼 → 登録リストへ追加）| **起きうる**。申請されなければ、そのアカウントのアプリは一切巡回されない。**月次棚卸し（M-Q-17-3）で補完する** |

→ アカウント単位の登録漏れは**巡回では検知できない**（巡回しないアカウントはエラーも出さない）。API 提供契約リスト・タグ・Service Catalog launch 実績との突合（M-Q-17-3）が**唯一の検出手段**になる。

---

## §16.5 【注意】ROSA 側前提との責任分界（BD-Q-01）

アカウント配置は **2 つに分離**している：**インターネット境界（CloudFront/WAF、ADR-039）＝ネットワーク監査アカウント**（ROSA 側 P-18 で他組織管理になる可能性）と、**認証実装確認処理のリソース群（App Registry / OpenAPI Registry / 認証実装チェック Lambda / アラート検知 Lambda / Secrets）＝共通基盤アカウント（自社管理）**。

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
| D-M-16-6 | 読み取り対象は**認証構成情報連携バケットのみ**（codecommit / apigateway 権限は 2026-08-21 全廃）| 認証構成情報オンリー原則（[ADR-061 追記](../../adr/061-deploy-detection-pull-model.md)）。ベンダーへの権限説明が単純・漏洩時影響も認証構成情報閲覧のみに縮小 |
| D-M-16-7 | アップロードは `ArtifactUploadRole-{appId}`（Put のみ・prefix 限定・デプロイロール分離）+ バケットポリシーで二重 Deny | 最小権限・アプリ間分離・書込経路の監査容易性（§16.2.2）|
| D-M-16-4 | ~~配布は StackSets（Organizations 自動デプロイ）~~ → **バケット・ロールは中央提供テンプレートで案件側が作成**（2026-09-16 ユーザー確定、§16.4）| 中央が全アカウントへ書き込む前提を置かない。代償として**アカウント単位の登録漏れが起きうる**ため、登録は申請ベース + 月次棚卸しで補完（§16.4.3、M-Q-17-3）|
| D-M-16-8 | 巡回対象アカウントは **SSM Parameter Store の登録リスト**（中央管理・申請ベース）。**Organizations 委任ポリシーによる `ListAccounts` は不採用**（2026-09-16 ユーザー確定）| 案件側作成方式では組織全体を列挙しても監視対象を判別できない。判別のため全アカウントへ AssumeRole を試すと、対象外アカウントで必ず失敗し `DiscoveryAccountErrors`（MM-3）が常時発報して**本物の障害が埋もれる**（17 §17.7 M-Q-17-2 解決）|
| D-M-16-9 | 「**登録漏れが構造的にゼロ**」は**アプリ単位に限定**（アカウント単位は申請ベースのため漏れうる）| 範囲を正確に記述しないと棚卸し（M-Q-17-3）の必要性を見誤る（§16.4.3）|
| D-M-16-5 | ROSA 側 P-18 確定まで自管理前提で記述、差分改訂 | 前提変更に追随（BD-Q-01）|

---

## §16.7 未決事項

| ID | 内容 |
|---|---|
| BD-Q-01 | ROSA 側 P-18（監査アカウント他組織管理）確定時の probe 先経路改訂 |
| M-Q-16-1 | ~~`DiscoveryReadRole` の配布対象範囲（Organizations 全体 / OU 単位）~~ → **2026-09-16 に方式変更**（案件側作成 + SSM 登録リスト、§16.4）により「配布範囲」の論点は消滅。残る論点は**登録申請フロー（申請窓口・承認者・SLA）と棚卸し運用**（17 章 M-Q-17-3 と連動）|
| M-Q-16-3 | 案件側が作成したバケット・ロールが**規約どおりか**の検証手段（初回巡回時の自己診断のみで足りるか、テンプレート適用の証跡を求めるか）|
| M-Q-16-2 | 対象検索 Lambda の並列度・スロットリング（アカウント数増加時の API コール制御）|

---

## §16.x 関連ドキュメント

- [ADR-061](../../adr/061-deploy-detection-pull-model.md) — pull 型統一の決定 + 旧 push 型書き込み 5 案比較（付録）
- [17-deployment-integration-and-registration.md](17-deployment-integration-and-registration.md) — 巡回フロー（このロールの使い手）
- [12-app-registry-design.md](12-app-registry-design.md) — 台帳の書き込み権限（中央のみ）
