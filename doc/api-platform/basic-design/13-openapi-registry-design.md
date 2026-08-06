# 13. OpenAPI Registry 設計（S3）

前提: [00-basic-design-plan.md](00-basic-design-plan.md) / [10-external-monitoring-overview.md](10-external-monitoring-overview.md)
実装: 発見 Lambda が pull 取得（M-Q-17-4、[openapi-export-lambda/](code-samples/openapi-export-lambda/) の GetExport ロジックを流用）/ データ契約: [code-samples/README.md §2.2/§2.3](code-samples/README.md)

---

## §13.0 前提と背景

**この章で定めること**: 認証実装確認処理が「各アプリの endpoint 一覧と probe 制御情報」を得るための OpenAPI 置き場（S3）と、deploy 後の正本を自動 export する仕組み、アプリチームが付けるアノテーション。
**なぜ要るか**: 認証実装確認処理は endpoint を**動的に**知る必要がある（アプリごとに違い、増減する）。OpenAPI を正本にすれば新規 endpoint も次回 deploy で自動追随する。

---

## §13.1 S3 バケット構造

共通基盤アカウントに 1 バケット。

| 項目 | 値 |
|---|---|
| バケット | `<common-platform-acct>-openapi-registry` |
| キー | `{accountId}/{apiId}/openapi.yaml` |
| Versioning | 有効（正本の履歴を保持）|

認証実装確認処理は App Registry の `openApiS3Key` でこのキーを引き、`lib/openapi.js` の `fetchSpec` で取得・parse する。

> ⚠ **実装注意（Phase 4 検証で判明）**: LocalStack でのローカルテストは S3 の **virtual-host addressing** で失敗する（`forcePathStyle` 要）。これは LocalStack 固有で**実 AWS では発生しない**。full-run は SAM local か実 AWS で（[research](research/phase4-local-verification-results.md)）。

---

## §13.2 取得フロー（中央が pull で export）

deploy 後の**実際の API GW 定義**を正本として S3 に置く。リポジトリの OpenAPI とずれても production と一致させるため、**発見 Lambda の巡回（[17 章 §17.2](17-deployment-integration-and-registration.md) / [ADR-061](../../adr/061-deploy-detection-pull-model.md)）が変化を検知した API について、中央が AssumeRole + GetExport で取得**する。アプリ側の Export 処理は存在しない。

```mermaid
sequenceDiagram
    participant DISC as 発見 Lambda / 共通基盤アカウント
    participant AGW as API GW / App アカウント（読み取り AssumeRole）
    participant S3 as OpenAPI Registry / 共通基盤アカウント

    Note over DISC: 巡回で deploymentId の変化を検知（17 章）
    DISC->>AGW: GetExport（exportType=oas30, accepts=application/yaml）
    AGW-->>DISC: OpenAPI（body = Uint8Array）
    DISC->>S3: PutObject（同一アカウント、{accountId}/{apiId}/openapi.yaml）
```

> **公式確認（Phase 3）**: `GetExportCommand({ restApiId, stageName, exportType:'oas30', accepts:'application/yaml' })`、**body は `Uint8Array`** → `TextDecoder` で文字列化して Put。GetExport 呼び出しは App アカウント側の API に対して行うため読み取りロールで AssumeRole する（16 章）。
> 旧 push 型の Custom Resource 実装（[`openapi-export-lambda/`](code-samples/openapi-export-lambda/)）は参考保管。GetExport → S3 Put のロジックは発見 Lambda に流用できる。

---

## §13.3 OpenAPI アノテーション（アプリチームが付与）

probe 挙動を OpenAPI 上で制御する。アプリチームは通常の API 設計に加えてこれらを書くだけ。

### §13.3.0 公開明示は必須（default-deny）⭐

> **死守事項 MON-1**: すべての endpoint は **デフォルトで「認証必須」** とみなす。**認証不要（public）な endpoint は `x-synthetics-skip-auth-check: true` を必ず明示する**。明示のない endpoint は認証必須として Negative probe で検査し、未認証で 2xx が返れば CRITICAL/P1（認証漏れ）とする。

- **アノテーション未記載 = 認証必須**。「うっかり公開」を検知する側に倒すための default-deny 設計。
- public を意図する endpoint に**明示を付け忘れると、正しく公開していても "認証漏れ" として P1 アラートが出る** → アプリチームは明示せざるを得ない（＝必須が自然に強制される）。
- 公開明示は**唯一アプリが必ず書くべき監視用アノテーション**（他は任意）。これが「アプリは OpenAPI に公開印を付けるだけ」という責任境界の中核。
- 公開明示された endpoint も、それが**本当に公開してよいか**は別途セキュリティレビュー対象（無制限に skip を濫用させない。棚卸しは中央、[05 §5.2.3 AC-3](05-security.md) の例外申請と連動）。

| アノテーション | 意味 | デフォルト |
|---|---|---|
| `x-synthetics-skip-auth-check: true` | Negative probe 対象外（public endpoint）**※ public は必須明示（MON-1）** | false（認証必須）|
| `x-canary-positive-test: true \| false \| pre-prod-only` | Positive test 実施 | false |
| `x-canary-test-token-secret: <name>` | 使用 token の Secret 名 | app の `testTokenSecret` |
| `x-canary-path-params: {key: value}` | path parameter の dummy 値 | — |
| `x-canary-cleanup: {action, path, idFrom}` | probe 後の後処理（POST 等）| — |
| `x-canary-auth-mode: cookie-redirect` | モノリス Cookie フロー | — |
| `x-canary-expected-redirect: /login` | Cookie モノリスの期待リダイレクト先 | — |

解釈は `lib/openapi.js` の `extractEndpoints`（[検証済み: openapi test 7 PASS](research/phase4-local-verification-results.md)）。

### §13.3.1 記述例

```yaml
paths:
  /api/users:
    get:
      x-canary-positive-test: true
      x-canary-test-token-secret: canary-central-readonly
  /api/orders:
    post:
      x-canary-positive-test: pre-prod-only     # 本番は Negative のみ（副作用回避）
      x-canary-cleanup: { action: DELETE, path: /api/orders/{orderId}, idFrom: response.body.orderId }
  /_/health:
    get:
      x-synthetics-skip-auth-check: true        # public
  /dashboard:
    get:
      x-canary-auth-mode: cookie-redirect        # SSR モノリス
      x-canary-expected-redirect: /login
```

---

## §13.4 新規 endpoint の自動追随

1. アプリチームが endpoint を追加（OpenAPI 更新）→ deploy
2. **次回巡回（最大 1h）で発見 Lambda が変化を検知し、新版を GetExport → S3 に上書き**（§13.2）
3. 同じ巡回で M1 probe が起動し、新 endpoint も対象化

→ **probe のコード変更は不要**。OpenAPI を正本にすることで「監視対象の維持」が自動化される。

## §13.5 M1 との関係と S3 Versioning

**M1 のトリガは発見 Lambda の巡回差分（deploymentId 比較、[17 章 §17.2](17-deployment-integration-and-registration.md)）であり、S3 イベントではない**（[ADR-061](../../adr/061-deploy-detection-pull-model.md)）。OpenAPI Registry は「probe が読む正本」+「Versioning による履歴」を担う。

- ⚠ **差分粒度はアプリ単位**（18 章 §18.2.1）: 巡回は deploymentId の変化で「デプロイされた」ことだけ判定し、**endpoint 単位に絞らず「そのアプリの全 endpoint」を probe** する。理由は、認証コードだけ変えて OpenAPI が不変なケース（middleware 削除等）を見逃さないため。
- S3 Versioning の新旧 diff は「何が変わったか」の**参考情報**（アラート本文への付記）に使い、probe 範囲の絞り込みには使わない。

> **なぜ endpoint 単位に絞らないか**は 18 章 §18.2.1 の設計判断 D-M-18-2 参照。

---

## §13.5 設計判断

| ID | 判断 | 根拠 |
|---|---|---|
| D-M-13-1 | 正本は deploy 後の API GW から export（リポジトリの OpenAPI でなく）| production と一致保証、drift 防止 |
| D-M-13-2 | probe 制御は OpenAPI アノテーションで表現 | アプリチームの追加作業を最小化、endpoint と同じ場所で管理 |
| D-M-13-3 | Versioning 有効 | 正本の時点管理（監査・巻き戻し）|
| D-M-13-4 | 新規 endpoint は OpenAPI 更新で自動追随（probe 無改修）| 監視維持の自動化 |

---

## §13.6 未決事項

| ID | 内容 |
|---|---|
| M-Q-13-1 | OpenAPI を持たないレガシー API の扱い（App Registry に固定 endpoint リストを持たせる代替、14 章 §14.4）|
| M-Q-13-2 | S3 Object Lock（改ざん防止）の要否 |
| M-Q-13-3 | probe の S3Client に forcePathStyle 相当のテスト用オプションを持たせるか（本番不要）|
