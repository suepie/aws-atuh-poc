# code-samples — 中央認証チェック 実装物

前提: [ADR-059 Central Auth Check Canary Architecture (Pattern β)](../../../adr/059-central-auth-check-canary-architecture.md) / [§C-API-6 §C-6.6.8](../../proposal/common/06-external-api-auth-architecture.md)
位置付け: 認証外形監視（Pattern β = ネットワーク監査アカウント集約）の**動く実装サンプル**。本ディレクトリは API プラットフォーム専用（認証基盤 `keycloak/` とは分離）。

> ⚠ **これは参照実装 / サンプルです**。本番採用時は Region / アカウント ID / ドメイン等を環境に合わせて置換し、PoC 検証（Phase 4）を経てください。

---

## 0. 全体像

```
[ネットワーク監査アカウント]                          [各 App アカウント]
  App Registry (DynamoDB) ◄──── クロスアカウント Put ──── Service Catalog 製品
  OpenAPI Registry (S3)   ◄──── クロスアカウント Put ──── (deploy 時に自動登録)
  中央認証チェック (Lambda, 共通 probe lib)
    │ M1 デプロイ差分（自動）/ M3 フル監査（手動）※18 章
    ├─ App Registry を Scan（M1 対象アプリ / M3 全アプリ取得）
    ├─ OpenAPI Registry から各アプリの openapi.yaml 取得
    ├─ 各 endpoint を Negative + Positive で probe（CloudFront 経由）──► 各アプリ CloudFront
    ├─ 4×4 真偽値表で分類 → CloudWatch Metrics (per-app)
    └─ 分類結果を Alert Router Lambda へ
  Alert Router Lambda → SNS (P1 Security / P2 Platform / P3 App)
```

## 1. コンポーネント一覧

| ディレクトリ | 役割 | Runtime |
|---|---|---|
| [central-probe-lib/](central-probe-lib/) | 中央認証チェック 本体（共通 probe lib：OpenAPI 動的発見、Hybrid 検証、4×4 分類）| Lambda（Node.js 22 / SDK v3）|
| [multi-checks-blueprint/](multi-checks-blueprint/) | **将来オプション**（Synthetics）: 小規模 Multi Checks JSON（≤10 checks、OAuth ネイティブ）| `syn-nodejs-5.1` |
| [app-registry-lambda/](app-registry-lambda/) | App Registry CRUD（Custom Resource から呼ばれる登録 API）| Node.js 22 / SDK v3 |
| [openapi-export-lambda/](openapi-export-lambda/) | OpenAPI Export Custom Resource（API GW get-export → S3 Put）| Node.js 22 / SDK v3 |
| [alert-router-lambda/](alert-router-lambda/) | 4×4 分類 → SNS routing | Node.js 22 / SDK v3 |
| [iac-guard-rules/](iac-guard-rules/) | cfn-guard / cdk-nag ルールセット（04 章）| — |
| [semgrep-rules/](semgrep-rules/) | Semgrep ルール（言語別、04 章）| — |

---

## 2. データ契約（全コンポーネント共通、必ず遵守）

### 2.1 App Registry（DynamoDB）スキーマ

各アプリが deploy 時に 1 レコード登録。中央認証チェックがこれを Scan する。

| 属性 | 型 | 説明 | 例 |
|---|---|---|---|
| `appId` (PK) | S | アプリ一意識別子 | `expense-api` |
| `env` (SK) | S | 環境 | `prod` / `stg` / `dev` |
| `baseUrl` | S | probe 先の CloudFront URL（Origin Protection 経由）| `https://expense.example.com` |
| `authPattern` | S | 認証パターン（下記 enum）| `api-gw-jwt` |
| `openApiS3Key` | S | OpenAPI Registry 内のキー | `111122223333/abc123/openapi.yaml` |
| `testTokenSecret` | S | Positive test 用 token の Secret 名（ネットワーク監査アカウント内）| `canary-central-readonly` |
| `alertRouting` | M | 通知先設定（下記）| `{ p1: "arn:...:security", p2: "arn:...:platform", p3: "arn:...:app-team-x" }` |
| `enabled` | BOOL | 監視有効フラグ | `true` |
| `registeredAt` | S | ISO8601 登録日時 | `2026-07-06T00:00:00Z` |

**`authPattern` enum**（中央認証チェックが assertion 方式を切替）:
| 値 | 意味 | Negative 期待 | Positive |
|---|---|---|---|
| `api-gw-jwt` | API GW + JWT Authorizer | 401/403 | Bearer で 200 |
| `api-gw-iam` | API GW + AWS_IAM | 403 | （SigV4、Phase 2）|
| `alb-code-jwt` | ALB + アプリコード JWT | 401/403 | Bearer で 200 |
| `alb-cookie-monolith` | ALB + Cookie SSR モノリス | 302 Redirect to /login | Puppeteer ログイン |
| `bff-cookie-session` | **BFF（ブラウザ↔BFF=Cookie セッション）** | 401 or 302（BFF 実装依存）| Puppeteer ログイン → Cookie |
| `lambda-url-iam` | Lambda Function URL + IAM | 403 | （SigV4、Phase 2）|

> `bff-cookie-session` は BFF アーキパターン（[§C-API-2 §C-2.1.1.A](../../proposal/common/02-runtime-selection-criteria.md)）の**ブラウザ↔BFF 入口**を監視する。BFF↔API 間（Bearer）は内部通信のため、BFF 入口の監視で実質カバー。API を独立監視する場合は別レコードで `api-gw-jwt` として登録。

### 2.2 OpenAPI Registry（S3）構造

- バケット: `<network-audit-acct>-openapi-registry`（Versioning 有効）
- キー: `{accountId}/{apiId}/openapi.yaml`
- 各アプリの deploy 時に openapi-export-lambda が Put

### 2.3 OpenAPI アノテーション（アプリチームが付与、中央認証チェックが解釈）

> **MON-1（必須・default-deny）**: 未記載 = 認証必須。**public endpoint は `x-synthetics-skip-auth-check: true` を必ず明示**。未明示の public は「認証漏れ（Neg=2xx）」として P1 になる（[13 章 §13.3.0](../13-openapi-registry-design.md)）。これがアプリ必須の唯一の監視アノテーション、他は任意。

| アノテーション | 意味 | デフォルト |
|---|---|---|
| `x-synthetics-skip-auth-check: true` | Negative probe 対象外（public endpoint）**※ public は必須明示（MON-1）** | false（= 認証必須）|
| `x-canary-positive-test: true \| false \| pre-prod-only` | Positive test 実施 | false |
| `x-canary-test-token-secret: <name>` | 使用 token の Secret 名 | app の `testTokenSecret` |
| `x-canary-path-params: { key: value }` | path parameter の dummy 値 | — |
| `x-canary-cleanup: { action, path, idFrom }` | probe 後の後処理（POST 等）| — |
| `x-canary-auth-mode: cookie-redirect` | モノリス Cookie フロー | — |
| `x-canary-expected-redirect: /login` | Cookie モノリスの期待リダイレクト先 | — |

### 2.4 CloudWatch Metrics（中央認証チェックが emit）

- Namespace: `APIPlatform/AuthCheck`
- Dimensions: `AppId`, `Env`, `AuthPattern`
- Metrics:
  | 名前 | 単位 | 意味 |
  |---|---|---|
  | `AuthCheckPassed` | Count | 正常（Neg=401/403 + Pos=200）|
  | `AuthCheckCritical` | Count | 🔥 認証漏れ（Neg=200）|
  | `AuthCheckWarn` | Count | ⚠ テスト構成 / token 失効 |
  | `AuthCheckInfo` | Count | Backend バグ（Pos=500）|
  | `EndpointsProbed` | Count | probe した endpoint 総数 |

### 2.5 4×4 真偽値表（分類ロジック、probe と alert-router で共有）

| Negative status | Positive status | 分類 | severity | 通知先 |
|:---:|:---:|---|---|---|
| 401/403 | 200/201/204 | OK | — | 通知なし |
| **200** | 200 | **CRITICAL**（認証 missing）| P1 | Security オンコール |
| **200** | 401/403 | **CRITICAL**（認証逆転）| P1 | Security オンコール |
| 401/403 | 401/403 | WARN（token 失効）| P2 | Platform |
| 401/403 | 404 | WARN（endpoint 不在 / 構成）| P2 | Platform |
| 401/403 | 500 | INFO（Backend バグ）| P3 | App team |
| 404 | any | WARN（構成ミス）| P2 | Platform |
| null(skip) | 200 | OK（public + health）| — | 通知なし |

### 2.6 Alert イベント形式（probe → alert-router）

```json
{
  "appId": "expense-api",
  "env": "prod",
  "authPattern": "api-gw-jwt",
  "path": "/api/users",
  "method": "GET",
  "negStatus": 200,
  "posStatus": 200,
  "severity": "CRITICAL",
  "reason": "Auth missing or bypassed",
  "timestamp": "2026-07-06T00:05:00Z"
}
```

---

## 3. Runtime / SDK バージョン（AWS 公式確認 2026-07）

現行の実行基盤は **Lambda（Node.js 22 / SDK v3）**。以下 Synthetics 系は **将来オプション**（M2 / ダッシュボード要件時、[18 章 §18.4.1](../18-scan-modes-and-scheduling.md)）で使う場合の確認値。

| 対象 | バージョン | 備考 |
|---|---|---|
| **認証チェック Lambda（現行）** | **Node.js 22 / AWS SDK v3** | probe lib を実行、synthetics 抽象は https 実装で注入 |
| Synthetics Puppeteer runtime（将来）| `syn-nodejs-puppeteer-16.1` | Lambda Node.js 22.x、旧 `-7.0` は Deprecated |
| Synthetics Node.js-only runtime（将来）| `syn-nodejs-5.1` | Multi Checks Blueprint 用 |
| Synthetics namespace（将来）| `@aws/synthetics-puppeteer` / `@aws/synthetics-logger` | v13.1+ で旧 `Synthetics` から変更 |

---

## 4. デプロイ順序

1. `app-registry-lambda` + `openapi-export-lambda` をネットワーク監査アカウントにデプロイ（クロスアカウント Role 設定）
2. `alert-router-lambda` + SNS トピック（P1/P2/P3）をデプロイ
3. `central-probe-lib` の probe lib を **認証チェック Lambda** としてデプロイ（M1=EventBridge 起動 / M3=手動 invoke、18 章）
4. 各 App アカウントの Service Catalog 製品に Custom Resource（App Registry 登録 + OpenAPI Export）を組込
5. Phase 4 PoC: 1 App アカウント相当で end-to-end 検証

---

## 5. 検証済み一次資料

| 事実 | URL |
|---|---|
| Synthetics runtime versions | https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_Library_nodejs_puppeteer.html |
| Multi Checks Blueprint 認証設定 | https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_Canaries_MultiCheck_Blueprint.html |
| executeHttpStep シグネチャ | https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_Canaries_Library_Nodejs.html |
| Synthetics VPC（Private API 用、Phase 2）| https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_Canaries_VPC.html |
