# §FR-API-3 流量制御・クォータ

> 親 SSOT: [../00-index.md](../00-index.md) §FR-API-3
> ヒアリング: [../../hearing-script/03-throttling-quota.md](../../hearing-script/03-throttling-quota.md)

---

## §3.0 前提と背景

### §3.0.1 用語整理

| 用語 | 定義 |
|---|---|
| **Throttle（スロットル）** | 単位時間あたりの最大リクエスト数の制限 |
| **Burst** | 短時間に許容する瞬間最大値（rate を超える短期スパイク許容） |
| **Quota** | 期間（日 / 週 / 月）あたりの累積上限 |
| **Rate limit** | throttle の英語表現、本書では同義扱い |
| **Account-level throttling** | AWS アカウント全体での API Gateway の上限（既定 10,000 RPS / Burst 5,000） |
| **Usage Plan** | API Gateway REST API が提供する API Key 単位の throttle + quota の組み合わせ |

### §3.0.2 なぜここ（§3）で決めるか

流量制御は「**死守すべきセキュリティ**」と「**コスト管理**」の両面で必須：

- **セキュリティ**：DDoS 緩和・暴走クライアントの遮断・他テナント影響の隔離
- **コスト**：従量課金リソース（Lambda 実行・データ転送・DB クエリ）の暴騰防止

ただし AWS 公式は明確に「**Usage Plan の throttle/quota は best-effort であり、ハードリミットではない**」「**Usage Plan を予算管理に使うな**（→ AWS Budgets / AWS WAF を使え）」と明記している。本標準ではこの公式ガイダンスに沿う。

### §3.0.3 §3.0.A 本標準のスタンス

| 基本方針 | 本章での具体化 |
|---|---|
| 絶対安全 | **全公開 API に rate-based WAF rule を必須化**（IP 単位、5 分窓） |
| どんなアプリでも | REST API は Usage Plan、HTTP API は WAF + アプリ内制御の二本立てを許容 |
| 効率よく | Service Catalog で **API カテゴリ別の標準 throttle テンプレ**（Public / Internal / Partner）を配布 |
| 運用負荷・コスト最小 | 標準値で 80% カバー、個別調整は申請制 |

### §3.0.4 本章で扱うサブセクション

| § | サブセクション | 主題 |
|---|---|---|
| §3.1 | スロットル設計 | API・メソッド・利用者単位の throttle/burst |
| §3.2 | クォータ設計 | 日次・月次の累積上限 |
| §3.3 | 超過時挙動 | 429 応答・Retry-After・クライアント規約 |
| §3.4 | HTTP API での流量制御代替 | Usage Plan 非対応への対処 |

---

## §3.1 スロットル設計

**このサブセクションで定めること**：API・メソッド・利用者単位の throttle / burst の標準値。
**主な判断軸**：DDoS 緩和を優先、正規利用は阻害しない、アカウント上限から逆算。
**§3 全体との関係**：本サブセクションが流量制御の主要レイヤ。§3.2 quota は累積、§3.1 rate は瞬間。

### §3.1.1 ベースライン

- **階層構造**（API Gateway 公式の優先順）：
  1. クライアント/メソッド単位（Usage Plan）
  2. メソッド単位（Stage 設定）
  3. API 全体（Stage 設定）
  4. アカウントレベル（AWS 既定 / 申請上限）
  5. **AWS Regional 上限**（地域全体）
- **標準値（暫定）**：

| API カテゴリ | Rate（RPS） | Burst |
|---|---:|---:|
| Public B2C | 1,000 / API key | 2,000 |
| Internal microservice | 5,000 / service | 10,000 |
| Partner B2B | 100 / API key | 200 |
| Private | 個別 | 個別 |

- **WAF rate-based rule**（IP 単位、5 分窓）を **全 Public/Partner API に必須**：標準値 2,000 req / 5min（既定）

### §3.1.2 TBD / 要確認

- Q: **既定 throttle 値の妥当性**（アプリごとのトラフィック実績に基づいて再設定要）→ `API-B-301`
- Q: アカウントレベル throttle の **増枠申請を予防的に行うか**（10k RPS のままで足りるか）→ `API-B-302`
- Q: **メソッド単位**（POST は厳しく、GET は緩く 等）の標準化テンプレを用意するか → `API-B-303`

---

## §3.2 クォータ設計

**このサブセクションで定めること**：日次・月次の累積リクエスト上限。
**主な判断軸**：商用契約・無料枠・サブスクリプションプランへの対応。
**§3 全体との関係**：§3.1 の瞬間制御に対し本サブセクションは長期累積。

### §3.2.1 ベースライン

- **REST API + Usage Plan** で API Key ごとに `quota.limit` + `period`（DAY / WEEK / MONTH）を設定
- 標準プラン例（暫定）：

| プラン | 月次 quota | 想定用途 |
|---|---:|---|
| Free | 10,000 / month | 開発・評価 |
| Basic | 100,000 / month | 小規模商用 |
| Pro | 1,000,000 / month | 中規模商用 |
| Enterprise | 個別 | 大規模 / 専用契約 |

- **HTTP API は Usage Plan 非対応** → §3.4 で代替

### §3.2.2 TBD / 要確認

- Q: **商用 API に quota を全面適用するか、内部利用は無制限とするか** → `API-B-311`
- Q: **超過時の課金モデル**（追加課金 / ハードカット）→ `API-B-312`
- Q: 月初リセットの **タイムゾーン**（UTC か JST か）→ `API-B-313`

---

## §3.3 超過時挙動

**このサブセクションで定めること**：throttle / quota 超過時のレスポンス規約。
**主な判断軸**：クライアント側で正しくリトライできる、Observability で検出できる。
**§3 全体との関係**：§3.1 / §3.2 の挙動仕様。

### §3.3.1 ベースライン

- **HTTP ステータス**：429 Too Many Requests
- **必須ヘッダ**：
  - `Retry-After`（秒数 or 日時、推奨：秒数）
  - `X-RateLimit-Limit` / `X-RateLimit-Remaining` / `X-RateLimit-Reset`（任意だが推奨）
- **クライアント規約**：**Exponential backoff + jitter** での retry を義務化、最大 retry 回数・累積待機時間を SDK / 規約で標準化
- **観測**：429 を CloudWatch メトリクスに分離（`4XXError` から分離するため Logs Insights で集計）、SLO 違反通知

### §3.3.2 TBD / 要確認

- Q: 429 を **アラート化するしきい値**（1% / 5% / 10% を超えたら通知）→ `API-B-321`
- Q: **429 を SLO の対象外とするか含めるか** → `API-B-322`

---

## §3.4 HTTP API での流量制御代替

**このサブセクションで定めること**：HTTP API（Usage Plan 非対応）採用時の流量制御代替手段。
**主な判断軸**：マネージド優先、複雑性最小、検知可能性。
**§3 全体との関係**：§3.1 / §3.2 を HTTP API でも実現するための手段。

### §3.4.1 ベースライン

代替手段の積み重ね（複数を組み合わせる）：

1. **AWS WAF rate-based rule**（IP 単位、5 分窓）
2. **API Gateway stage throttling**（API 全体・メソッド単位の上限、Usage Plan のような per-key 制御は不可）
3. **Lambda Authorizer + DynamoDB アトミックカウンタ**でテナント単位の per-key 制御を自前実装（コスト・レイテンシ増）
4. **CloudFront function** でヘッダベース簡易制御
5. アプリ内（Lambda 内）でのトークンバケット実装

### §3.4.2 TBD / 要確認

- Q: **HTTP API でテナント単位 quota が必要なら REST API への変更を検討するか**、それとも自前実装を許容するか → `API-B-341`
- Q: 自前実装の DynamoDB スキーマ・コスト試算 → `API-B-342`

---

## §3.A SSR モノリスでの留意点

[§C-API-2 §C-2.1](../common/02-runtime-selection-criteria.md) のパターン C（SSR モノリス）では、流量制御の手段が大きく異なる：

| 観点 | API Gateway 系（API） | SSR モノリス（ALB + ECS）|
|---|---|---|
| **Usage Plan + API Key** | 利用可（REST API） | **利用不可**（ALB に Usage Plan なし）|
| Throttle | API GW stage / method throttle | **WAF rate-based rule のみ**（IP / 5min 窓）|
| Quota | Usage Plan で per-key | **自前実装**（DynamoDB アトミックカウンタ等）|
| 429 応答 | API GW 自動 | アプリ自前または ALB レベル（リクエスト容量超過時） |
| **代替手段** | （該当なし） | WAF rate-based + アプリ内 throttling（middleware）+ DynamoDB カウンタ |

**モノリス採用時の流量制御パス（推奨）**：
1. **第 1 層：CloudFront / WAF rate-based**（IP 単位、5min 窓、ボットや DDoS 対策）
2. **第 2 層：ALB**（target group の max connections / desired count スケール制御）
3. **第 3 層：アプリ内 middleware**（session ID / tenant_id 単位の throttling、必要時は DynamoDB）
4. **B2B 課金が要件化したら**：§C-API-2 §C-2.3 段階移行パスで `/api/*` を別サービスに切り出し、API Gateway + Usage Plan を導入

**留意点**：
- Usage Plan が使えないため、**per-tenant 課金が必須要件のアプリはモノリスを避ける**（パターン A / B を選ぶ）
- WAF rate-based の窓は固定 5min、より細かい制御は middleware で実装
- DynamoDB アトミックカウンタは **コスト感度が高い**ため、テナント数 × リクエスト頻度を要見積

詳細は [§FR-API-6 §6.1.A モノリス vs マイクロサービス](06-container-standard.md) 参照。

---

## §3.x 関連ドキュメント

- [§FR-API-4 課金](04-metering-billing.md) — 利用者識別子（API Key）の活用
- [§FR-API-6 §6.1.A モノリス vs マイクロサービス](06-container-standard.md) — モノリスでの流量制御
- [§FR-API-7 ガードレール](07-guardrails.md) — WAF rate-based rule の FMS 配信
- [§NFR-API-4 セキュリティ](../nfr/04-security.md) — DDoS 対策の死守事項
- [§NFR-API-8 コスト](../nfr/08-cost.md) — 流量制御で防ぐべきコスト暴騰シナリオ
