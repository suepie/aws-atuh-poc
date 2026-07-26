# Phase 4 ローカル検証結果（P4-1〜P4-3）

実施日: 2026-07-25
範囲: 課金ゼロでローカル実行可能な P4-1（静的解析）/ P4-2（Lambda 単体）/ P4-3（canary probe→classify 統合）
方針: **実際にツールを走らせて検証**（嘘なし）。発見した不具合はその場で修正。

## 0. 使用した検証環境

| ツール | バージョン | 導入方法 |
|---|---|---|
| Node.js | v22.14.0 | 既存 |
| cfn-guard | **3.2.0** | `cargo install cfn-guard --locked` |
| Semgrep | **1.171.0** | 隔離 venv に pip install |
| AWS CLI | 2.34.0 | 既存 |
| Docker | 24.0.6（デーモン停止中）| P4-3 full には要起動 |
| SAM CLI | 未導入 | P4-3 full に必要 |

## 1. P4-1 静的解析（実行済み、実バグ 2 件発見・修正、guard 3 ファイル全検証）

> **2026-07-26 追記**: 残っていた `origin-protection-required.guard` / `required-tags.guard` の専用フィクスチャを作成し検証。両者とも **compliant PASS / noncompliant FAIL で正しく動作**（今回バグなし）。`required-tags` は PascalCase キー・app- 前缀なし・env 列挙外を検知、`origin-protection` は Policy 欠落・SG 0.0.0.0/0 を検知。**cfn-guard 3 ファイル + Semgrep 3 言語すべてフィクスチャ検証済み**。

### 1.1 Semgrep（Python ルール）

フィクスチャ: `semgrep-rules/test-fixtures/vulnerable.py`（脆弱）/ `clean.py`（健全）

| 対象 | 期待 | 実測（修正前）| 実測（修正後）|
|---|---|---|---|
| vulnerable.py | 全ルール検知 | **5 検知**（P6×1 / P5×3 / P3×1）✅ | 5 検知 ✅ |
| clean.py | 検知ゼロ | **1 検知（FP）** ⚠ | **0 検知** ✅ |

**🐛 実バグ発見・修正**: `fastapi-missing-auth-middleware` が middleware のある健全コードでも誤発火（false positive）していた。
- **原因**: (1) `pattern:` / `pattern-not-inside:` のトップレベル併記形式では期待通り動かず、(2) `pattern-not-inside` の末尾に `...` が無いとモジュールトップレベルの `FastAPI()` 代入が範囲「内側」と判定されない。
- **修正**: `patterns:` リスト形式に変更 + `pattern-not-inside` 末尾に `...` を追加（`python-auth.yaml` に反映済み、コメントで理由明記）。
- **教訓**: Semgrep の `pattern-not-inside` はマッチ対象が範囲の先頭ノードだと「内側」と見なされない。トレーリング `...` で範囲を延ばす必要がある。**実行しないと分からない類の不具合**。

### 1.2 cfn-guard（認証必須ルール）

フィクスチャ: `iac-guard-rules/test-fixtures/noncompliant.yaml` / `compliant.yaml`

| 対象 | 期待 | 実測（修正前）| 実測（修正後）|
|---|---|---|---|
| noncompliant.yaml | 3 ルール FAIL | Status=FAIL、3/3 FAIL ✅ | 3/3 FAIL ✅ |
| compliant.yaml | 全 PASS | **Status=FAIL（1 ルール誤 FAIL）** ⚠ | **Status=PASS、3/3 PASS** ✅ |

**🐛 実バグ発見・修正**: `alb_must_have_auth_action` が「**全** DefaultAction が認証型」を要求し、標準的な `[authenticate-oidc, forward]` の 2 段構成（認証 → 転送）で `forward` に対し誤 FAIL していた。
- **原因**: `%...DefaultActions[*] { Type IN [...] }` は全要素に条件を課す（ALL 意味論）。
- **修正**: `some %...DefaultActions[*].Type IN [...]` に変更し「**少なくとも 1 つ**が認証 action」の意味論に（`api-gw-authorizer-required.guard` に反映済み、コメントで理由明記）。
- **教訓**: cfn-guard の配列アクセス `[*]` は ALL 意味論。「いずれか」は `some` 演算子が必要。**実行しないと分からない**。

### 1.3 P4-1 結論
- **ツールチェーン（cfn-guard 3.2.0 / Semgrep 1.171.0）は実コードで正しく動作**することを実証。
- **走らせたことで実バグ 2 件を発見・修正**。これがローカル検証の価値。
- 残: `origin-protection-required.guard` / `required-tags.guard` は専用フィクスチャ未作成（対象リソースが本フィクスチャに無く未評価）。P4-4 で追加。

## 2. P4-2 Lambda 単体（実行済み）

### 2.1 ユニット（純関数）

| コンポーネント | 検証 | 結果 |
|---|---|---|
| **alert-router-lambda** | `test/routing.test.js`（4×4 分類 → SNS 振り分け）| **19/19 PASS** ✅ |

### 2.2 SDK 実挙動（LocalStack、2026-07-25 追加実施）

ユーザーが Docker Desktop を起動 → **LocalStack 3.8.1（community、auth 不要）** をコンテナ起動し、実 AWS サービスエミュレーションで handler を実行。SDK v3 は `AWS_ENDPOINT_URL=http://localhost:4566` で LocalStack へルーティング。

> ⚠ LocalStack の `latest`(2026.7.0) は auth token 必須に変わっていたため、**community は `3.8.1` にピン留め**が必要（本検証で判明）。

| コンポーネント | 検証内容 | 結果 |
|---|---|---|
| **app-registry-lambda** | Custom Resource Create イベントで実行 → LocalStack DynamoDB に PutItem | ✅ scan で item 確認（`enabled:"true"`→Boolean `true` 正規化も動作、cfn-response の mock URL 失敗も graceful に resolve = stuck しない）|
| **alert-router-lambda** | 本番フロー: canary イベント(ARN なし) → App Registry(DDB) GetItem で alertRouting 解決 → SNS Publish | ✅ **P1 topic に publish、実 MessageId 取得**（`published:true, priority:P1`）|

**実証できたこと**:
- SDK v3 の DynamoDB DocumentClient PutCommand / GetItemCommand、SNS PublishCommand が実際に動く
- app-registry の Boolean 正規化・Custom Resource エラーハンドリングが設計通り
- alert-router の「イベントに ARN 無し → DDB から解決 → publish」という**本番ルーティング経路が end-to-end で成立**

**未実施（要 API GW or 実 AWS）**: openapi-export の get-export（LocalStack community の API GW REST + GetExport 対応が限定的なため P4-4/実 AWS で）。

## 3. P4-3 canary probe→classify 統合（実行済み）

`central-canary-puppeteer/test/probe-integration.test.js`:
- **synthetics スタブ**（executeHttpStep を実 http リクエストで代替）+ **ローカル HTTP モックサーバ**（認証ヘッダ有無で status 出し分け）で、**実物の probe.js（authPattern 分岐）+ classify.js** を end-to-end 実行。

| ケース | probe 実測 | classify 実測 | 結果 |
|---|---|---|---|
| api-gw-jwt 認証あり endpoint | Neg=401 | OK | ✅ |
| api-gw-jwt 認証漏れ endpoint | Neg=200 | **CRITICAL/P1** | ✅ |
| alb-cookie-monolith 未認証 | Neg=302 | OK | ✅ |
| skipAuthCheck=true（public）| Neg=null | OK | ✅ |

**4/4 PASS**。canary の中核（authPattern 別 Negative probe + 4×4 分類）が **実 HTTP ラウンドトリップ**で正しく動くことを実証。特に「認証漏れ endpoint（常時 200）→ CRITICAL/P1」を実際に検知できた。

### 3.1 canary logic 全ユニット/統合（2026-07-26 追加）

`central-canary-puppeteer` の `node --test` 全体: **27 PASS**（classify 16 + probe-integration 4 + openapi extractEndpoints 7）。
- `test/openapi.test.js` 新規: `extractEndpoints` のアノテーション解釈（skip-auth-check / positive-test / path-params dummy 置換 / cookie-redirect / cleanup）を検証。

### 3.2 full オーケストレーション（LocalStack、部分成立）

synthetics スタブ（`@aws/synthetics-*` を node_modules に配置）+ LocalStack + モック probe 先で `index.handler` を実行:
- ✅ **registry.js の `scanEnabledApps` が LocalStack DynamoDB からアプリを取得**（Scan 実挙動 OK）
- ⚠ **openapi.js の S3 取得が LocalStack の virtual-host addressing で失敗**（"bucket does not exist"）。これは **canary のバグではなく LocalStack 固有**（S3 は `forcePathStyle: true` が必要。実 AWS では発生しない）。テストハーネスで path-style を強制するか、SAM local / 実 AWS で実行すれば解消。
- ⚠ CloudWatch `ListMetrics` は LocalStack community で 500（サポート限定）。

→ **full オーケストレーションの完全実行は SAM local か実 AWS が必要**（LocalStack だけでは S3 addressing / CloudWatch / Lambda deploy の壁がある）。canary の**ロジック自体は構成テスト（probe/classify/extractEndpoints/registry Scan）で網羅的に検証済み**。

- 未検証（full 実行に SAM+Docker or 実 AWS 必要）: `@aws/synthetics-puppeteer` の実ランタイム挙動 / Positive probe（Secrets + OAuth Bearer）/ SigV4 Positive / Cookie モノリス Positive（Puppeteer ログイン）/ CloudWatch metrics 着地 / Lambda invoke。

## 4. P4-4 以降（実 AWS が必要、未実施）

full 実行の手順（環境が整い次第）:

```bash
# --- P4-3 full: canary を SAM local で実行 ---
brew install aws-sam-cli        # or 公式インストーラ
# Docker Desktop を起動（デーモン）
git clone https://github.com/aws-samples/synthetics-canary-local-debugging-sample.git
# 同 sample の template.yml / cw-synthetics.js を流用し、CodeUri を
#   central-canary-puppeteer に向ける。event.json に canaryName / artifactS3Location を設定
sam build && sam local invoke -e event.json

# --- P4-2 full: Lambda を LocalStack で ---
localstack start            # DynamoDB/S3/SNS/SecretsManager/API GW をエミュレート
# ※ CloudWatch Synthetics は LocalStack 非対応 → canary は SAM local or 実 AWS

# --- P4-4/P4-5: 実 AWS サンドボックス〜マルチアカウント E2E ---
# App Registry / OpenAPI Registry / canary / Alert Router を実デプロイ
```

## 5. 修正したファイル（本検証で変更）

| ファイル | 変更 |
|---|---|
| `semgrep-rules/python-auth.yaml` | fastapi ルールを `patterns:` リスト形式 + 末尾 `...` に修正（FP 解消）|
| `iac-guard-rules/api-gw-authorizer-required.guard` | ALB ルールを `some` 演算子に修正（誤 FAIL 解消）|
| `semgrep-rules/test-fixtures/{vulnerable,clean}.py` | 新規（検証フィクスチャ）|
| `iac-guard-rules/test-fixtures/{noncompliant,compliant}.yaml` | 新規（検証フィクスチャ）|
| `central-canary-puppeteer/test/probe-integration.test.js` | 新規（P4-3 統合テスト）|

## 6. 総括

| Phase | 実行 | 結果 |
|---|:---:|---|
| P4-1 静的解析（guard 3 + semgrep 3）| ✅ 実行 | 全フィクスチャ検証 + **実バグ 2 件修正**（Semgrep FP / cfn-guard ALB）|
| P4-2 Lambda ユニット | ✅ 実行 | alert-router 19 PASS |
| P4-2 Lambda SDK 実挙動 | ✅ 実行（LocalStack 3.8.1）| **app-registry PutItem / alert-router SNS Publish（DDB 経由）end-to-end** |
| P4-3 canary logic | ✅ 実行 | **27 PASS**（classify 16 + probe統合 4 + extractEndpoints 7、実 HTTP で漏れ検知）|
| P4-3 full orchestration | ◐ 部分 | registry Scan は LocalStack で成立、S3 は LocalStack addressing の壁 → SAM/実 AWS 要 |
| P4-3 canary full（SAM）| ⏳ | SAM CLI + Docker 要（synthetics ランタイム再現）|
| P4-4 openapi-export get-export | ⏳ | API GW（LocalStack 限定 or 実 AWS）要 |
| P4-5 E2E | ⏳ | 実マルチアカウント要 |

**課金ゼロで検証できる範囲はすべて実行。静的解析で実バグ 2 件を発見・修正し、Lambda の SDK 実挙動（DynamoDB/SNS）を LocalStack で end-to-end 実証した。**

## 7. LocalStack 環境メモ（再現用）

```bash
# community 版は 3.8.1 にピン留め（latest=2026.7.0 は auth token 必須）
docker run -d --name localstack-p4 -p 4566:4566 localstack/localstack:3.8.1
# SDK を向ける
export AWS_ENDPOINT_URL=http://localhost:4566 AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test AWS_REGION=ap-northeast-1
# 停止・削除
docker rm -f localstack-p4
```
