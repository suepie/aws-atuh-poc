# ADR-052: マルチテナント Isolation + API Gateway Rate Limiting / Per-tenant Quota

- **ステータス**: Proposed（要件定義フェーズで Accepted に昇格予定）
- **日付**: 2026-06-23
- **関連**:
  - [ADR-017 マルチテナント L2 採用根拠](017-multitenant-l2-single-realm.md)
  - [ADR-038 ユーザ管理画面](038-tenant-admin-portal.md)
  - [ADR-039 中央集約 Network 専用アカウント](039-centralized-network-account-edge-layer.md)
  - [ADR-042 Bot Detection / CAPTCHA](042-bot-detection-captcha.md)
  - [ADR-049 Vendor Risk Management（Concentration Risk）](049-vendor-risk-management-tprm.md)
  - [§NFR-2 性能](../requirements/proposal/nfr/02-performance.md)
  - [§NFR-3 拡張性](../requirements/proposal/nfr/03-scalability.md)

---

## Context

### 背景

[ADR-017](017-multitenant-l2-single-realm.md) で「マルチテナント L2（単一 Pool/Realm + 複数 IdP）」を採用し、論理分離は確立した。しかし、**性能 / リクエスト量の隔離**（Noisy Neighbor 対策）と**Per-tenant Quota / Rate Limiting** の具体設計は未確定のままだった。

具体的に欠けていたもの:

1. **Noisy Neighbor 問題**：1 顧客の大量リクエストが他顧客の体感性能を悪化させる
2. **Per-tenant Rate Limiting**：テナント単位の RPS 上限設定
3. **Per-tenant Quota**：月間 API 呼出上限 / Storage / MAU 上限
4. **Throttling と Spike Arrest**：突発的トラフィックへの段階的対応
5. **Per-tenant Resource Tagging**：性能監視・コスト按分の前提
6. **Tier 別 SLA / 帯域保証**（Enterprise / Standard / Free 等）
7. **API Versioning**：Breaking change 時の旧 API 並走戦略
8. **Tenant-aware Caching**：CloudFront / DynamoDB DAX の Cache Key にテナント考慮

### 業界のベストプラクティス

- **AWS SaaS Lens（Well-Architected）**: Pool / Silo / Hybrid モデル
- **Stripe API Versioning**: 日付ベースバージョン、自動アップグレード
- **Auth0**: Tenant 単位 Rate Limit + Burst（バースト時のスパイク許容）
- **Twilio / GitHub**: X-RateLimit-* ヘッダ標準化
- **Cloudflare**: Workers ベース Rate Limiting

### 業界事案教訓

| 事案 | 教訓 |
|---|---|
| **AWS S3 Slowdown 多発**（継続）| Per-bucket / Per-prefix Rate Limit、リトライ戦略必須 |
| **GitHub API 障害**（多発）| Per-token / Per-IP Throttling 必須 |
| **Twitter API 制限変更**（2023）| API Versioning + 移行期間設定必須 |
| **Salesforce Org Limit**（継続）| Per-org Quota が業界標準 |

### 規制要件

| 規制 | 関連条項 |
|---|---|
| **SOC 2 CC7.1** | 容量計画 + 監視 |
| **PCI DSS §6.4.3** | レート制限（Bot 対策と整合）|
| **GDPR** | データアクセス分離 |
| **APPI 第 23 条** | 安全管理措置（隔離）|

### 業界用語の整理

| 用語 | 意味 |
|---|---|
| **Noisy Neighbor** | 1 テナントが他テナントの性能を阻害 |
| **Pool Model** | 全テナント共有リソース（コスト効率高、隔離低）|
| **Silo Model** | テナント別専用リソース（隔離高、コスト高）|
| **Hybrid / Bridge Model** | 重要テナントのみ Silo、他は Pool |
| **Rate Limit** | 単位時間あたりリクエスト数上限 |
| **Throttling** | 上限超過時の挙動（拒否 / 遅延 / Queue）|
| **Spike Arrest** | 短期スパイクを平準化 |
| **Quota** | 累積上限（月間 / 年間）|
| **Burst** | 短時間の上限超過許容 |
| **Token Bucket** | 一定速度で Token 補充、リクエストが Token 消費 |
| **Leaky Bucket** | 一定速度で処理、超過は Drop |
| **Tenant Tagging** | リソースにテナント識別子付与 |

---

## Decision

### 採用方針

**「Pool Model + Per-tenant Rate Limit + Tier 別 Quota」**を採用。Enterprise 顧客向けには Hybrid Silo オプション。Per-tenant Throttling は **API Gateway Usage Plan + Lambda Authorizer 連動**で実装。

| 項目 | 採用方針 |
|---|---|
| **マルチテナント モデル** | **Pool**（標準）+ **Hybrid Silo**（Enterprise オプション）|
| **Rate Limit 単位** | **Per-tenant + Per-client_id + Per-IP** の 3 軸 |
| **Rate Limit 実装** | **API Gateway Usage Plan + API Key + Lambda Authorizer**（Token Bucket）|
| **Quota 実装** | **DynamoDB + Lambda（月初リセット）+ ユーザ管理画面 表示** |
| **Tier 別 SLA** | Enterprise / Standard / Best Effort の 3 ティア |
| **API Versioning** | **日付ベース**（`/v2026-06-23/...`）、12 ヶ月並走 |
| **Tenant Tagging** | 全 AWS リソース + ログに `tenant_id` Tag 必須 |
| **Cache 戦略** | CloudFront Cache Key に `tenant_id` 含む、DAX 使用 |
| **Burst 許容** | 通常 RPS × 2 を 1 分間まで |
| **Throttling 挙動** | 429 Too Many Requests + Retry-After Header + X-RateLimit-* ヘッダ |
| **Noisy Neighbor 検知** | CloudWatch Metric + ITDR 統合（[ADR-035](035-identity-threat-detection-response.md)）|
| **Spike Arrest** | API Gateway の Burst Limit + EKS HPA 自動拡張 |

---

## A. マルチテナント モデル選定

### A.1 Pool vs Silo vs Hybrid 比較

| 項目 | Pool（本基盤標準）| Silo（Enterprise）| Hybrid |
|---|---|---|---|
| **共有レベル** | 全テナント共有 | テナント別専用 | 重要テナントのみ Silo |
| **隔離** | 論理（DB schema / row-level）| 物理（DB / EKS / Realm 別）| 混合 |
| **コスト** | 最小 | テナント数 × | 一部 Silo 分のみ追加 |
| **Noisy Neighbor 影響** | あり（Rate Limit で緩和）| なし | Silo テナントには影響なし |
| **規制対応** | 標準準拠 | 規制業種に強い | 規制業種のみ Silo |
| **運用負荷** | 低 | 高（テナント数 ×）| 中 |
| **採用** | **標準**（[ADR-017](017-multitenant-l2-single-realm.md)）| Enterprise オプション | 標準提供 |

### A.2 Silo 適用判断条件

| 条件 | Silo 推奨 |
|---|---|
| 規制業種顧客（金融 / 医療）| 顧客要求次第で Silo |
| MAU 500K 超 | Silo 候補 |
| 専用 API キー / 専用 SLA 契約 | Silo |
| データ Residency 厳格要件 | Silo（別 Region 含む）|
| 弊社 Network Acct 共有不可 | Silo（顧客 Acct 持込）|

### A.3 Hybrid アーキテクチャ

```mermaid
flowchart TB
    subgraph Pool["Pool Tenants(標準)"]
        T1[Tenant A<br/>Standard]
        T2[Tenant B<br/>Standard]
        T3[Tenant C<br/>Free]
        PoolKC[Broker KC + IdP-KC<br/>Pool]
        PoolDB[(Aurora Pool)]
    end

    subgraph Silo["Silo Tenants(Enterprise)"]
        T4[Tenant D Enterprise]
        T5[Tenant E Enterprise]
        SiloKC1[IdP-KC Silo<br/>(Tenant D)]
        SiloKC2[IdP-KC Silo<br/>(Tenant E)]
        SiloDB1[(Aurora Silo D)]
        SiloDB2[(Aurora Silo E)]
    end

    T1 --> PoolKC
    T2 --> PoolKC
    T3 --> PoolKC
    PoolKC --> PoolDB

    T4 --> SiloKC1
    SiloKC1 --> SiloDB1
    T5 --> SiloKC2
    SiloKC2 --> SiloDB2

    style Pool fill:#e3f2fd
    style Silo fill:#fff3e0
```

→ Broker KC は全テナント共通、IdP-KC のみ Silo 可能。

---

## B. Rate Limiting 設計

### B.1 3 軸 Rate Limit

| 軸 | 用途 | 制限例 |
|---|---|---|
| **Per-tenant**（最重要）| Noisy Neighbor 防止 | Standard 100 RPS / Enterprise 1000 RPS |
| **Per-client_id** | OAuth Client 単位 | Standard 50 RPS / client |
| **Per-IP** | 未認証エンドポイント / Bot 対策（[ADR-042](042-bot-detection-captcha.md)）| 2000 req / 5min / IP |

### B.2 Tier 別 Rate Limit

| Tier | 認証 API（/realms/.../auth）| Admin API（/admin/...）| Token API（/token）| Burst |
|---|---|---|---|---|
| **Enterprise** | 1000 RPS | 100 RPS | 500 RPS | ×2 / 1 min |
| **Standard** | 100 RPS | 20 RPS | 50 RPS | ×2 / 1 min |
| **Best Effort** | 10 RPS | 5 RPS | 10 RPS | なし |

### B.3 実装方式

```mermaid
flowchart LR
    Client[Client / Browser]
    CF[CloudFront]
    AGW[API Gateway<br/>Usage Plan + API Key]
    LA[Lambda Authorizer<br/>Per-tenant Token Bucket]
    DDB[DynamoDB<br/>tenant-rate-limit]
    KC[Keycloak / App]

    Client --> CF
    CF --> AGW
    AGW -->|Per-IP Throttle<br/>(Usage Plan)| LA
    LA -->|Token Bucket 確認| DDB
    DDB -->|残数| LA
    LA -->|OK| KC
    LA -->|超過| Throttle["429 Too Many Requests<br/>+ Retry-After + X-RateLimit-*"]
```

### B.4 Lambda Authorizer 実装例

```javascript
// Lambda Authorizer - Per-tenant Rate Limit (Token Bucket)
const AWS = require('aws-sdk');
const ddb = new AWS.DynamoDB.DocumentClient();

const TIER_LIMITS = {
  enterprise: { auth: 1000, admin: 100, token: 500, burst_multiplier: 2 },
  standard:   { auth: 100,  admin: 20,  token: 50,  burst_multiplier: 2 },
  best_effort:{ auth: 10,   admin: 5,   token: 10,  burst_multiplier: 1 },
};

exports.handler = async (event) => {
  const token = parseJWT(event.authorizationToken);
  const tenantId = token.tenant_id;
  const tier = await getTenantTier(tenantId);
  const endpoint = classifyEndpoint(event.methodArn);
  const limit = TIER_LIMITS[tier][endpoint];
  const burstLimit = limit * TIER_LIMITS[tier].burst_multiplier;

  // Token Bucket（DynamoDB Atomic Counter）
  const now = Date.now();
  const result = await ddb.update({
    TableName: 'tenant-rate-limit',
    Key: { tenant_id: tenantId, endpoint },
    UpdateExpression: `
      SET tokens = if_not_exists(tokens, :max) - :one,
          last_refill = :now
    `,
    ConditionExpression: 'tokens > :zero',
    ExpressionAttributeValues: {
      ':max': burstLimit, ':one': 1, ':zero': 0, ':now': now,
    },
    ReturnValues: 'ALL_NEW',
  }).promise().catch(err => {
    if (err.code === 'ConditionalCheckFailedException') {
      // Rate Limit 超過
      return { rate_limited: true };
    }
    throw err;
  });

  if (result.rate_limited) {
    return {
      principalId: tenantId,
      policyDocument: { Statement: [{ Effect: 'Deny', Resource: event.methodArn }] },
      context: {
        rate_limit_exceeded: 'true',
        retry_after: '60',
        limit: String(limit),
      },
    };
  }

  // 通常許可 + X-RateLimit-* 情報
  return {
    principalId: tenantId,
    policyDocument: { Statement: [{ Effect: 'Allow', Resource: event.methodArn }] },
    context: {
      tenant_id: tenantId,
      tier: tier,
      rate_limit: String(limit),
      rate_limit_remaining: String(result.Attributes.tokens),
    },
  };
};
```

### B.5 Token Refill（バックグラウンド Lambda）

```javascript
// EventBridge 1 秒毎に起動、各テナント / endpoint の Token を補充
exports.handler = async () => {
  const tenants = await listAllTenants();
  for (const tenant of tenants) {
    const tier = TIER_LIMITS[tenant.tier];
    for (const endpoint of ['auth', 'admin', 'token']) {
      const refillRate = tier[endpoint];  // RPS
      await ddb.update({
        TableName: 'tenant-rate-limit',
        Key: { tenant_id: tenant.id, endpoint },
        UpdateExpression: 'SET tokens = if_not_exists(tokens, :max) + :refill',
        ConditionExpression: 'tokens < :max',
        ExpressionAttributeValues: {
          ':refill': refillRate,
          ':max': refillRate * tier.burst_multiplier,
        },
      }).promise().catch(() => {});  // ConditionFail = 既に Max
    }
  }
};
```

---

## C. Per-tenant Quota

### C.1 Tier 別月次 Quota

| 項目 | Enterprise | Standard | Best Effort |
|---|---|---|---|
| 月間 MAU | 無制限 | 10 万 | 1,000 |
| 月間 API 呼出 | 1 億 | 1,000 万 | 10 万 |
| Storage（ユーザーデータ）| 100 GB | 10 GB | 100 MB |
| ユーザ管理画面 管理者数 | 無制限 | 10 名 | 2 名 |
| カスタム IdP 接続数 | 無制限 | 5 個 | 1 個 |
| Webhook 数 | 無制限 | 20 個 | 5 個 |
| 監査ログ保持期間 | 7 年 | 1 年 | 90 日 |

### C.2 Quota 超過時の挙動

| 種別 | 超過時 |
|---|---|
| MAU | **Soft Block**：超過分は Tenant Admin に警告通知、月末 95% で Slack / Email 通知、100% でアラート（強制 Block しない、Enterprise アップグレード勧奨）|
| API 呼出 | **Hard Block**：429 + Quota Exceeded、ユーザ管理画面 で増量申請可能 |
| Storage | **Read-Only**：書込不可、削除のみ可能 |
| Admin Portal 管理者数 | **新規追加不可**（既存はそのまま）|
| IdP 接続数 | **新規追加不可** |

### C.3 Quota 表示（ユーザ管理画面）

```
Dashboard / 利用状況
┌──────────────────────────────────────────────┐
│ Tier: Standard                                 │
├──────────────────────────────────────────────┤
│ MAU         87,234 / 100,000   [████████░░ 87%]│
│ API 呼出     6.2M / 10M        [██████░░░░ 62%]│
│ Storage     4.3 GB / 10 GB     [████░░░░░░ 43%]│
│ Admin 数    7 / 10             [███████░░░ 70%]│
│ IdP 接続数  3 / 5              [██████░░░░ 60%]│
└──────────────────────────────────────────────┘
[Upgrade to Enterprise] [Quota 増量申請]
```

### C.4 Quota 集計実装

```yaml
# DynamoDB Table: tenant-quota-usage
PartitionKey: tenant_id
SortKey: yyyy-mm-dd_metric_type  # 例: 2026-06_mau
Attributes:
  - tenant_id
  - month: 2026-06
  - metric_type: mau / api_calls / storage_bytes / ...
  - value: 87234
  - last_updated: 2026-06-23T10:00:00Z
  - tier: standard
  - quota_max: 100000
  - status: ok / warning_95 / exceeded
```

集計 Lambda（5 分毎）が各メトリクスを更新、95%/100% でアラート発火。

---

## D. API Versioning 戦略

### D.1 日付ベース URL Versioning

| 形式 | 例 |
|---|---|
| **本基盤採用** | `https://api.basis.example.com/v2026-06-23/...` |
| Stripe 同様 | （Stripe は Header だが、URL の方が顧客に分かりやすい）|

### D.2 Versioning ルール

| ルール | 内容 |
|---|---|
| **Major Version の頻度** | 半年に 1 回 |
| **古いバージョンの並走期間** | **12 ヶ月**（業界標準 6-12 ヶ月の上限）|
| **非互換変更** | Major Version のみ、Minor / Patch は後方互換維持 |
| **Deprecation 通知** | 6 ヶ月前 + 3 ヶ月前 + 1 ヶ月前 + 1 週間前（Email + ユーザ管理画面 + Trust Center）|
| **強制移行** | 12 ヶ月後、HTTP 410 Gone |

### D.3 Sunset Header（RFC 8594）

```http
HTTP/1.1 200 OK
Sunset: Sun, 23 Dec 2026 00:00:00 GMT
Deprecation: true
Link: </v2027-01-01/...>; rel="successor-version"
```

---

## E. Tenant Tagging（コスト按分 + 性能監視）

### E.1 必須 Tag

全 AWS リソース + ログ + メトリクスに以下 Tag 必須:

| Tag | 値 |
|---|---|
| `tenant_id` | テナント識別子（例: `acme`、Pool では `pool`）|
| `tier` | enterprise / standard / best_effort |
| `environment` | production / staging / dev |
| `cost_center` | コスト按分対象 |

### E.2 コスト按分（Cost Explorer）

```
AWS Cost Explorer:
- Tag: tenant_id
- グループ化: Tag tenant_id
- フィルタ: tier = enterprise
→ Enterprise 顧客別の月次コスト一覧
```

### E.3 性能監視（CloudWatch + ITDR 統合）

| メトリクス | 配列 |
|---|---|
| `tenant_id.api_rps` | 1 分毎 |
| `tenant_id.error_rate` | 1 分毎 |
| `tenant_id.latency_p99` | 1 分毎 |
| `tenant_id.rate_limit_hits` | 1 分毎 |

→ ITDR（[ADR-035](035-identity-threat-detection-response.md)）と統合し、Noisy Neighbor 兆候を検知。

---

## F. Caching 戦略

### F.1 CloudFront Cache Key with tenant_id

```hcl
resource "aws_cloudfront_cache_policy" "tenant_aware" {
  name = "tenant-aware-cache"
  parameters_in_cache_key_and_forwarded_to_origin {
    cookies_config { cookie_behavior = "none" }
    headers_config {
      header_behavior = "whitelist"
      headers { items = ["Host", "X-Tenant-ID"] }
    }
    query_strings_config { query_string_behavior = "all" }
  }
}
```

→ 異なるテナントの同 URL でも別 Cache Entry、テナント間漏洩防止。

### F.2 DynamoDB Accelerator (DAX)

- 読み取り性能が必要な ITDR / Adaptive Auth 履歴に DAX 採用
- Cache Key にも `tenant_id` 含む

### F.3 SPA / 静的コンテンツ

- ユーザ管理画面 SPA / アカウント設定画面 / サービス選択画面 / Sorry は**テナント間共通**（コードは同じ）
- ブランディング（[ADR-024](024-login-screen-architecture-branding.md)）はクライアント側 Runtime 切替（テナント別 Cache 不要）

---

## G. Spike Arrest（突発負荷対応）

### G.1 多層 Throttling

```
Layer 1: CloudFront（全体 100K RPS 上限）
  ↓
Layer 2: AWS WAF Rate Limit（Per-IP 2000 req/5min）
  ↓
Layer 3: API Gateway Usage Plan（Per-API Key）
  ↓
Layer 4: Lambda Authorizer Per-tenant Token Bucket（本 ADR）
  ↓
Layer 5: EKS HPA（CPU 70% で Pod 自動拡張）
  ↓
Layer 6: Aurora Auto-Scaling（Read Replica 自動追加）
```

### G.2 段階的劣化（Graceful Degradation）

| Load Level | 挙動 |
|---|---|
| 〜70% 容量 | 通常 |
| 70-85% | Rate Limit 警告、ユーザ管理画面 で表示 |
| 85-95% | Burst 許可停止、厳格 Limit 適用 |
| 95-100% | 非クリティカル API（管理画面）優先 Throttle、認証 API 優先 |
| 100%+ | 429 全面 + キュー（SQS）|

---

## H. ユーザ管理画面 統合（ADR-038 拡張）

| メニュー | 機能 |
|---|---|
| **利用状況ダッシュボード** | MAU / API 呼出 / Storage / Rate Limit Hit のグラフ |
| **Tier アップグレード** | Standard → Enterprise の申請 |
| **Quota 増量申請** | 一時的増量 / 恒久的増量 |
| **API キー管理** | OAuth Client 単位の Rate Limit 設定 |
| **Rate Limit 履歴** | 429 発生回数 / 時刻 / Top Endpoint |
| **API バージョン情報** | 現在使用バージョン + Deprecation 通知 |

---

## I. コスト試算

### I.1 月額追加（10M MAU）

| 項目 | 月額 |
|---|---|
| Lambda Authorizer（Per-tenant Rate Limit）| $200（Lambda Invocations）|
| DynamoDB（`tenant-rate-limit` + `tenant-quota-usage`）| $100 |
| Token Refill Lambda（1 秒毎）| $250（2.6M / 月実行）|
| CloudWatch Metrics（Per-tenant）| $200 |
| **合計** | **〜$750/月（年 〜$9K）** |

### I.2 比較

| 案 | 年額 |
|---|---|
| **本 ADR（自社実装 + AWS 標準）** | **〜$9K** |
| Kong Enterprise（Per-tenant Plugin） | $50K+ |
| Apigee | $40K+ |
| AWS WAF のみ（Per-IP のみ）| $5K（但し Per-tenant 不可、不十分）|

---

## J. 代替案検討

| 案 | 評価 | 採否 |
|---|---|---|
| **A. Rate Limit なし** | Noisy Neighbor / DDoS 影響大 | ❌ |
| **B. Per-IP のみ（WAF Rate Limit）** | テナント単位制御不可 | ❌ 不十分 |
| **C. Pool + 3 軸 Rate Limit + Tier Quota**（本 ADR）| 業界標準、コスト効率 | ✅ 採用 |
| **D. 全テナント Silo** | コスト膨大、運用負荷大 | ❌ |
| **E. Kong / Apigee 採用** | 年 $40-50K、本基盤の規模ではオーバースペック | △ Phase 2 |
| **F. Cloudflare Workers Rate Limit** | Cloudflare 依存度上昇 | ❌ |

---

## K. Consequences

### Positive

- **Noisy Neighbor 完全防止**（Per-tenant Rate Limit）
- **Tier 別 SLA**（Enterprise / Standard / Best Effort）で**収益モデル明確化**
- Quota 表示で**顧客自身が利用状況把握**、Upgrade 誘導
- Tenant Tagging で**コスト按分 + Per-tenant 監視**
- Spike Arrest で**突発負荷に段階的対応**、サービス全停止防止
- 自社実装で**商用 API Gateway 比 5-6 倍コスト削減**（年 $9K）

### Negative

- Lambda Authorizer の追加 Latency（〜10ms / リクエスト）
- DynamoDB の Atomic Counter コスト
- Hybrid Silo は運用負荷増（テナント別管理）
- API Versioning の並走期間（12 ヶ月）のコード保守負荷

### Neutral

- Silo は Enterprise 顧客のみ、Phase 1 は Pool のみ標準
- Hot Standby DR Region でも Lambda Authorizer + DynamoDB Global Tables で同様の Rate Limit 適用可能
- CloudFront Cache Hit 率は Per-tenant Cache Key で若干低下（Phase 2 で最適化検討）

### 我々のスタンス

| 基本方針の柱 | Multi-tenant Isolation での実現 |
|---|---|
| **絶対安全** | Per-tenant 隔離 + Noisy Neighbor 防止 |
| **どんなアプリでも** | Tier 別 SLA で多様な要件カバー |
| **効率よく認証** | Pool Model でコスト最小、Hybrid Silo は Enterprise のみ |
| **運用負荷・コスト最小** | 自社実装、商用 API Gateway 不要 |

---

## 参考資料

### AWS / 業界

- [AWS SaaS Lens — Well-Architected](https://docs.aws.amazon.com/wellarchitected/latest/saas-lens/saas-lens.html)
- [AWS API Gateway Usage Plans](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-api-usage-plans.html)
- [AWS DynamoDB Atomic Counters](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/WorkingWithItems.html#WorkingWithItems.AtomicCounters)
- [Cloudflare Rate Limiting Patterns](https://blog.cloudflare.com/counting-things-a-lot-of-different-things/)

### 業界事例

- [Stripe API Versioning](https://stripe.com/blog/api-versioning)
- [GitHub Rate Limiting](https://docs.github.com/en/rest/overview/resources-in-the-rest-api#rate-limiting)
- [Auth0 Rate Limits](https://auth0.com/docs/troubleshoot/customer-support/operational-policies/rate-limit-policy)
- [Twilio Rate Limits](https://www.twilio.com/docs/usage/api/rate-limits)

### 標準仕様

- [RFC 6585 — HTTP 429 Too Many Requests](https://datatracker.ietf.org/doc/html/rfc6585)
- [RFC 8594 — Sunset HTTP Header](https://datatracker.ietf.org/doc/html/rfc8594)
- [draft-ietf-httpapi-ratelimit-headers — IETF Rate Limit Header](https://datatracker.ietf.org/doc/draft-ietf-httpapi-ratelimit-headers/)

### Algorithms

- [Token Bucket Algorithm — Wikipedia](https://en.wikipedia.org/wiki/Token_bucket)
- [Leaky Bucket Algorithm — Wikipedia](https://en.wikipedia.org/wiki/Leaky_bucket)
