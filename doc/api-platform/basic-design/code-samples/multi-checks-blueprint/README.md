# multi-checks-blueprint — 小規模用 認証外形監視（Multi Checks Blueprint）

前提: [ADR-059 Central Auth Check Canary](../../../../adr/059-central-auth-check-canary-architecture.md) / 親 [code-samples/README.md](../README.md) §2 データ契約

CloudWatch Synthetics の **Multi Checks Blueprint** を使い、ヘッドレスブラウザ（Puppeteer）なしで
最大 10 個の HTTP/DNS/SSL/TCP チェックを 1 つの canary にまとめて実行する認証外形監視サンプル。
OAuth Client Credentials / API Key / Basic / SigV4 がネイティブ対応で、Secrets Manager 参照も組込。

> ⚠ これは参照実装 / サンプルです。Region・アカウント ID・ドメイン・Secret 名は環境に合わせて置換してください。

---

## 1. central-canary-puppeteer との使い分け

| 観点 | multi-checks-blueprint（本ディレクトリ）| central-canary-puppeteer |
|---|---|---|
| Runtime | `syn-nodejs-5.1`（Node.js のみ、ブラウザなし）| `syn-nodejs-puppeteer-16.1`（ヘッドレス Chrome）|
| endpoint 数 | **≤ 10 チェック / canary**（上限あり）| 制限なし（OpenAPI から動的発見）|
| endpoint 定義 | JSON で静的に列挙（`blueprint-config.json`）| OpenAPI Registry から動的発見 + アノテーション解釈 |
| 認証 | OAuth / API Key / Basic / SigV4 が**ネイティブ**（宣言のみ）| コードで自前実装 |
| Cookie モノリス（302 redirect ログイン）| 不可（HTTP チェックのみ）| 可（Puppeteer でログインフロー）|
| 適合ケース | **≤10 endpoint の静的な少数アプリ**、OAuth をコード無しで手早く | **大規模 / 動的 / 4×4 分類 / Cookie SSR モノリス** |

判断基準:
- **≤10 endpoint かつ静的**、OAuth ネイティブで十分 → **Multi Checks**（本ディレクトリ）。運用が軽い。
- **endpoint 数が多い / OpenAPI から動的に増減 / 4×4 真偽値表分類 / Cookie リダイレクトのモノリス** → **Puppeteer**。

親 README のデータ契約（Negative → 401/403 期待、Positive → 200 期待）は本サンプルでも同じ思想で表現している。
ただし 4×4 分類・CloudWatch Metrics emit・Alert Router 連携は Puppeteer 版が担う。Multi Checks は
assertion PASS/FAIL の可用性メトリクスをステップ単位で自動生成する（自前 emit 不要）点が異なる。

---

## 2. ファイル構成

| ファイル | 役割 |
|---|---|
| `blueprint-config.json` | **必須**。checks の実体。ZIP 化して CreateCanary に渡す |
| `synthetics.json` | 任意。Multi Checks では省略可。canary 設定は CreateCanary API 側で付与する方針 |
| `create-canary.sh` | `aws synthetics create-canary` の CLI サンプル |

### blueprint-config.json の中身（本サンプル）

1 アプリ（`expense-api`）に対し、親 README の Negative/Positive 思想を実装:
- **step 1 / 4**: 認証なし（`type: NONE`）→ `STATUS_CODE IN_RANGE 401..403` を期待（Negative）
- **step 2**: `OAUTH_CLIENT_CREDENTIALS` + `${AWS_SECRET:...}` → `STATUS_CODE EQUALS 200`（Positive）
- **step 3**: public health → 200（親 README §2.5 の `null(skip) → 200 = OK`）
- **step 5**: `API_KEY` の Positive 例

---

## 3. 検証済み事実（AWS 公式一次資料、2026-07 確認）

| 事実 | 値 / 内容 | URL |
|---|---|---|
| ルート構造 | `globalSettings` / `variables` / `steps`（**`steps` は "1"〜"10" をキーに持つオブジェクト**。配列ではない）| [Writing a JSON config for Multi Checks](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_WritingCanary_Multichecks.html) |
| 各 step | `stepName`（必須）/ `checkerType`（HTTP/DNS/SSL/TCP、必須）/ `url` / `httpMethod` / `headers` / `body` / `authentication` / `assertions` / `extractors` | 同上 |
| step 数上限 | **1〜10 step** | 同上 |
| 変数上限 | 最大 10 変数、`${変数名}` 参照 | 同上 |
| 認証タイプ | `NONE` / `BASIC` / `API_KEY` / `OAUTH_CLIENT_CREDENTIALS` / `SIGV4` | [Multi Checks Blueprint（親）](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_Canaries_MultiCheck_Blueprint.html) |
| OAuth フィールド | `tokenUrl` `clientId` `clientSecret`（必須）/ `scope` `audience` `resource` `tokenApiAuth` `tokenCacheTtl`（任意）| 同上 |
| API_KEY フィールド | `apiKey`（必須）/ `headerName`（任意、既定 `X-API-Key`）| 同上 |
| SIGV4 フィールド | `service` `region` `roleArn`（すべて必須）| 同上 |
| **Secret 参照構文** | 値全体: **`${AWS_SECRET:<secret_name>}`** / 特定キー: **`${AWS_SECRET:<secret_name>:<secret_key>}`** | 同上 |
| STATUS_CODE assertion | `operator`: `EQUALS` / `NOT_EQUALS` / `GREATER_THAN` / `LESS_THAN` / `IN_RANGE`、`value`（100-599）または `rangeMin`/`rangeMax` | [Writing a JSON config](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_WritingCanary_Multichecks.html) |
| BODY assertion | `target`（JSON/TEXT）/ `path`（JSONPath）/ `operator`（CONTAINS 等）/ `value` | 同上 |
| HEADER assertion | `headerName` / `operator`（EQUALS/CONTAINS/EXIST 等）/ `value` | 同上 |
| HTTP レスポンス上限 | **1 MB** | [Multi Checks Blueprint（親）](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_Canaries_MultiCheck_Blueprint.html) |
| CreateCanary | `Code.BlueprintTypes=["multi-checks"]` を指定し `Handler` は付けない（両方指定で `ValidationException`）。runtime は **`syn-nodejs-3.0` 以上**（本サンプルは規約の `syn-nodejs-5.1`）| [Multi Checks（親）](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_Canaries_MultiCheck_Blueprint.html) / [CreateCanary API](https://docs.aws.amazon.com/AmazonSynthetics/latest/APIReference/API_CreateCanary.html) |
| Secrets 権限 | ExecutionRoleArn に `secretsmanager:GetSecretValue` + `secretsmanager:DescribeSecret`（顧客管理鍵なら `kms:Decrypt`）。SigV4 は対象 `roleArn` を assume できる信頼ポリシー | 同上 |
| canary 名パターン | `^[0-9a-z_\-]+$`（小文字・数字・ハイフン・アンダースコアのみ、最大 255）| [CreateCanary API](https://docs.aws.amazon.com/AmazonSynthetics/latest/APIReference/API_CreateCanary.html) |
| OAuth トークン更新 | 401/407 応答時に自動リフレッシュ | [Multi Checks（親）](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_Canaries_MultiCheck_Blueprint.html) |
| DEBUG ログ | 環境変数 `CW_SYNTHETICS_LOG_LEVEL: "DEBUG"` | 同上 |

---

## 4. 制約・注意

- **checks は「配列」ではなく `steps` オブジェクト**（キー "1".."10"）。§C-6.6.8 の記述と食い違う場合は本スキーマが正。
- HTTP チェックのみ。**Cookie SSR モノリスの 302 リダイレクトログインは表現できない** → Puppeteer 版へ。
- OAuth の `clientId`/`clientSecret` を **`${AWS_SECRET:name:key}` でキー単位参照**する場合、Secret は JSON 形式で該当キーを持つこと。
- ENUM 値を持つフィールド（`type`/`operator` 等）には変数 / Secret 置換が効かない（公式明記）。
- 同一 JSON 内でフィールド重複時は**最後の値のみ有効**。
- レスポンス 1 MB 超は失敗する。大きい応答を返す endpoint は本方式に不向き。
