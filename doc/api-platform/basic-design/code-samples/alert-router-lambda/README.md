# alert-router-lambda — 4×4 分類 → SNS routing

Central Auth Check Canary（[ADR-059](../../../../adr/059-central-auth-check-canary-architecture.md) / Pattern β）の **Alert Router**。
canary（[central-canary-puppeteer](../central-canary-puppeteer/)）が 4×4 真偽値表で分類した結果（Alert イベント）を受け、
`severity` に応じて **P1 / P2 / P3** の SNS トピックへ振り分ける。

> ⚠ 参照実装。Region / アカウント ID / SNS ARN は環境に合わせて置換すること。

---

## 1. 役割

```
central-canary-puppeteer
  └─ lib/classify.js で 4×4 分類 → { severity, reason, priority }
       │  Alert イベント（README §2.6）を Lambda.invoke
       ▼
alert-router-lambda (このコンポーネント)
  ├─ severity → priority(P1/P2/P3) を判定（lib/format.js = §2.5 SSOT）
  ├─ App Registry(DynamoDB §2.1) の alertRouting {p1,p2,p3} を appId/env で引く
  │    └─ 無ければ環境変数 DEFAULT_Px_TOPIC_ARN に fallback
  ├─ 人間可読メッセージ整形（endpoint / SLA / 初動）
  └─ SNS PublishCommand（@aws-sdk/client-sns v3）
       ▼
SNS: P1 Security / P2 Platform / P3 App
```

分類そのものは **canary 側で完了済み**。本 Lambda は「振り分け + 整形 + Publish」に専念し、
severity → priority の対応表のみを canary と共有する（`lib/format.js` の `SEVERITY_META`）。

---

## 2. severity → 通知先 対応表（README §2.5 準拠）

| canary 分類（Neg / Pos）| severity | priority | routingKey | SNS トピック | 対応 SLA |
|---|---|---|---|---|---|
| Neg=200 / Pos=200（認証漏れ）| **CRITICAL** | **P1** | `p1` | Security オンコール | 即時（page / 15 分）|
| Neg=200 / Pos=401/403（認証逆転）| **CRITICAL** | **P1** | `p1` | Security オンコール | 即時（page / 15 分）|
| Neg=401/403 / Pos=401/403（token 失効）| WARN | P2 | `p2` | Platform | 24h 以内 |
| Neg=401/403 / Pos=404（構成）| WARN | P2 | `p2` | Platform | 24h 以内 |
| Neg=404 / any（構成ミス）| WARN | P2 | `p2` | Platform | 24h 以内 |
| Neg=401/403 / Pos=500（Backend バグ）| INFO | P3 | `p3` | App team | 通常（次営業日）|
| Neg=401/403 / Pos=200（正常）| OK | — | — | 通知なし | — |
| Neg=null(skip) / Pos=200（public）| OK | — | — | 通知なし | — |

`OK` が届いた場合は Publish せず skip（通常 canary は OK を送らない）。
未知 severity は安全側で **WARN(P2)** に fallback。

---

## 3. 環境変数

| 変数 | 必須 | 説明 |
|---|---|---|
| `APP_REGISTRY_TABLE` | 任意 | App Registry DynamoDB テーブル名。設定時は appId/env で `alertRouting` を lookup。未設定なら DDB を参照せずデフォルト ARN のみ使用 |
| `DEFAULT_P1_TOPIC_ARN` | 推奨 | P1(Security) デフォルト SNS ARN（alertRouting.p1 欠落時の fallback）|
| `DEFAULT_P2_TOPIC_ARN` | 推奨 | P2(Platform) デフォルト SNS ARN |
| `DEFAULT_P3_TOPIC_ARN` | 推奨 | P3(App) デフォルト SNS ARN |
| `AWS_REGION` | 自動 | Lambda ランタイムが設定 |

ARN が App Registry / デフォルトの双方で未解決の場合は **エラーを throw**（DLQ / retry で可視化）。

### 必要 IAM 権限
- `sns:Publish`（P1/P2/P3 各トピック）
- `dynamodb:GetItem`（`APP_REGISTRY_TABLE` を使う場合）

---

## 4. canary からの Invoke 方法

canary は分類結果を §2.6 の Alert イベントとして `@aws-sdk/client-lambda` の
`InvokeCommand`（`InvocationType: 'Event'` = 非同期）で本 Lambda に渡す。

Alert イベント（README §2.6）:

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

- 単一イベント / イベント配列の両方を受け付ける（バッチ耐性）。
- 1 件でも Publish 失敗すると Lambda は失敗（`throw`）→ retry / DLQ 発火。

---

## 5. SNS トピック構成

| トピック | priority | 購読者 | 用途 |
|---|---|---|---|
| P1 Security | P1 | Security オンコール（PagerDuty 等）| 🔥 認証漏れ / 認証逆転。即時 page |
| P2 Platform | P2 | Platform チーム | ⚠ token 失効 / 構成 drift。24h |
| P3 App | P3 | 各 App チーム | ℹ Backend バグ（5xx）。通常 |

App ごとに宛先を変える場合は App Registry レコードの `alertRouting`（§2.1）に
`{ p1, p2, p3 }` で個別 ARN を設定する（例: p3 をアプリ専用トピックに）。

---

## 6. ローカルテスト

```bash
npm install          # @aws-sdk/client-sns, @aws-sdk/client-dynamodb
npm test             # node --test （test/routing.test.js）
```

`test/routing.test.js` は SNS/DDB を呼ばず、純粋な振り分けロジック
（`resolveTopicArn` / `metaFor` / `formatBody` / `formatSubject` / `validateEvent`）を検証する。

---

## 7. 検証済み事実

| 事実 | 根拠 |
|---|---|
| AWS SDK v3 SNS Publish import は `const { SNSClient, PublishCommand } = require('@aws-sdk/client-sns')` | AWS SDK for JavaScript v3 公式（@aws-sdk/client-sns）|
| DynamoDB GetItem は `const { DynamoDBClient, GetItemCommand } = require('@aws-sdk/client-dynamodb')` | AWS SDK for JavaScript v3 公式 |
| Lambda Node.js 18+ は SDK v2 非バンドル → v3 を `dependencies` に含める | README §3 / AWS 公式 |
| severity → P1/P2/P3 対応は canary `lib/classify.js` の `priority` 出力と一致 | 本 README §2 = §2.5 4×4 真偽値表 |
| node:test 19 ケース全 PASS（2026-07-25 実行）| `npm test` |

---

## 8. canary 側 classify との整合

`central-canary-puppeteer/lib/classify.js` が返す `severity` と本 Lambda の `SEVERITY_META`
（`lib/format.js`）は §2.5 の 4×4 真偽値表を SSOT として一致している:

| classify.js の severity | classify.js の priority | 本 Lambda の routingKey / priority |
|---|---|---|
| `CRITICAL` | `P1` | `p1` / P1 |
| `WARN` | `P2` | `p2` / P2 |
| `INFO` | `P3` | `p3` / P3 |
| `OK` | `null` | Publish skip |

classify.js は分類（severity 判定）を、alert-router は振り分け（SNS 選択）を担う分業。
どちらも §2.5 を唯一の真実源とするため、真偽値表を変更する際は両者を同時に更新すること。
