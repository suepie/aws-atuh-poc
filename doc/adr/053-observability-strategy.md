# ADR-053: Observability Strategy（OpenTelemetry + SLO + Distributed Tracing + Dashboards）

- **ステータス**: Proposed（要件定義フェーズで Accepted に昇格予定）
- **日付**: 2026-06-23
- **関連**:
  - [ADR-033 Keycloak 2-tier アーキテクチャ](033-keycloak-2tier-broker-idp-architecture.md)
  - [ADR-035 ITDR](035-identity-threat-detection-response.md)
  - [ADR-039 中央集約 Network 専用アカウント](039-centralized-network-account-edge-layer.md)
  - [ADR-044 Tabletop Exercise](044-tabletop-exercise-incident-drill.md)
  - [ADR-049 Vendor Risk（Continuous Monitoring）](049-vendor-risk-management-tprm.md)
  - [ADR-051 Multi-Region DR / Failover](051-multi-region-dr-failover.md)
  - [ADR-052 Multi-tenant Isolation + Rate Limiting](052-multi-tenant-isolation-rate-limiting.md)
  - [§NFR-6 運用](../requirements/proposal/nfr/06-operations.md)

---

## Context

### 背景

[§NFR-6.1](../requirements/proposal/nfr/06-operations.md) で「監視・ロギング」のベースラインは定めたが、**現代的な Observability 戦略**（OpenTelemetry / SLO / Distributed Tracing / Dashboards 体系）が未定義のままだった。各 ADR で CloudWatch / EventBridge / OpenSearch への言及は散在していたが、以下が不明確:

1. **OpenTelemetry 採用判断**（業界デファクトだが運用負荷もあり）
2. **SLO 設計**（Auth API / Token API / Admin API 別の目標値）
3. **Distributed Tracing**（Cross-Service / Cross-Region トレーシング）
4. **メトリクス階層**（基盤共通 / Per-tenant / Per-endpoint）
5. **Dashboards 体系**（CISO / SRE / 開発者 / Tenant Admin 別）
6. **Alerting 階層**（Critical / High / Medium / Low + Routing）
7. **ログ保管階層**（Hot / Warm / Cold + 規制要件）
8. **CloudWatch vs OpenSearch vs Grafana 選定**
9. **Cost 最適化**（Sampling / Aggregation / 保管期間）

### 業界の現在地

| 項目 | 業界標準（2026） |
|---|---|
| **計装** | OpenTelemetry（CNCF Graduated 2024）|
| **メトリクス** | Prometheus / Amazon Managed Prometheus (AMP)|
| **トレース** | Jaeger / Tempo / AWS X-Ray |
| **ログ** | Loki / OpenSearch / CloudWatch Logs |
| **ダッシュボード** | Grafana / Amazon Managed Grafana (AMG)|
| **SLO 管理** | Nobl9 / SLOTH / Prometheus Recording Rules |
| **AIOps** | Datadog / New Relic / Dynatrace（商用）|

### 業界事案教訓

| 事案 | 教訓 |
|---|---|
| **Cloudflare 2020/7 BGP 障害** | Distributed Tracing で原因 30 分で特定 |
| **GitHub 2018 24h 障害** | Observability 不足で復旧長期化 |
| **Facebook 2021/10 6h 障害** | DNS BGP 内部観測欠落 |
| **AWS us-east-1 障害（多発）** | Multi-Region Observability の必要性 |

### 規制要件

| 規制 | 関連条項 |
|---|---|
| **SOC 2 CC7.1 / CC7.2** | システム監視 + 異常検知 |
| **PCI DSS §10** | 監査ログ 1 年 + Hot 3 ヶ月 |
| **PCI DSS §10.4** | ログ レビュー（日次）|
| **ISO 27001 A.5.36 / A.8.15** | ログ監視 |
| **APPI 第 23 条** | 安全管理措置（不正アクセス監視）|
| **DORA**（金融顧客）| Continuous Monitoring + Reporting |

### 業界用語の整理

| 用語 | 意味 |
|---|---|
| **Observability**（O11y）| 内部状態を外部出力から推測可能な性質 |
| **3 Pillars** | Metrics / Logs / Traces |
| **4th Pillar** | Profiles（パフォーマンス Profiling）|
| **OpenTelemetry**（OTel）| ベンダー中立な計装フレームワーク |
| **OTLP**（OpenTelemetry Protocol）| OTel 標準 wire protocol |
| **SLI**（Service Level Indicator）| 性能指標（latency / error rate 等）|
| **SLO**（Service Level Objective）| 目標値（例: 99.9% 可用性）|
| **SLA**（Service Level Agreement）| 契約上の保証 |
| **Error Budget** | SLO 達成の余裕（100% - SLO%）|
| **RED Method** | Rate / Errors / Duration |
| **USE Method** | Utilization / Saturation / Errors |
| **Cardinality** | メトリクスの組合せ数（高 = コスト増）|
| **Span / Trace** | 1 単位処理 / 複数 Span の関連付け |
| **Context Propagation** | Span ID を Cross-Service 伝播 |
| **Sampling** | 全 Trace の一部のみ保存（コスト削減）|

---

## Decision

### 採用方針

**「OpenTelemetry + AWS Managed（AMP/AMG/X-Ray）+ SLO with Error Budget」**を採用。商用 APM（Datadog / New Relic）は不採用、AWS Managed Services 中心で年 $30K 範囲に収める。

| 項目 | 採用方針 |
|---|---|
| **計装フレームワーク** | **OpenTelemetry**（OTLP）|
| **メトリクス Backend** | **Amazon Managed Prometheus (AMP)** |
| **トレース Backend** | **AWS X-Ray**（OTLP 経由）|
| **ログ Backend** | **CloudWatch Logs**（Hot 3 ヶ月）+ **OpenSearch**（Warm 1 年）+ **S3 Glacier**（Cold 6 年）|
| **ダッシュボード** | **Amazon Managed Grafana (AMG)** |
| **SLO 管理** | **Prometheus Recording Rules + Grafana Burn Rate Alert** |
| **APM** | **不採用**（OpenTelemetry + X-Ray で代替、Datadog 等は $40K+/年）|
| **AIOps / 異常検知** | **CloudWatch Anomaly Detection + ITDR EventBridge**（[ADR-035](035-identity-threat-detection-response.md)）|
| **計装範囲** | EKS Pod / Lambda / API Gateway / Aurora / DynamoDB / CloudFront / Step Functions 全て |
| **Sampling** | Trace 1%（通常）+ 100%（Error / Slow）|
| **メトリクス Cardinality** | Per-tenant_id + Per-endpoint + Per-status_code（その他は集約）|

---

## A. OpenTelemetry アーキテクチャ

### A.1 全体図

```mermaid
flowchart TB
    subgraph Apps["アプリケーション(全 Acct)"]
        EKS[EKS Pod<br/>OTel Collector Sidecar]
        Lambda[Lambda<br/>OTel Lambda Layer]
        APIGW[API Gateway<br/>Native Metrics]
        Aurora[Aurora<br/>Performance Insights]
        DDB[DynamoDB<br/>Contributor Insights]
    end

    subgraph Collector["OTel Collector Layer"]
        OCS[OTel Collector<br/>EKS DaemonSet]
        OCM[Cross-Acct OTel Collector<br/>(Observability Acct)]
        OCS --> OCM
        Lambda --> OCM
    end

    subgraph Backend["Backend(Audit Acct or 専用 Acct)"]
        AMP[Amazon Managed<br/>Prometheus]
        XRay[AWS X-Ray]
        CWL[CloudWatch Logs]
        OS[OpenSearch]
    end

    subgraph Visual["可視化"]
        AMG[Amazon Managed<br/>Grafana]
        CWDash[CloudWatch Dashboard]
    end

    subgraph Alert["アラート"]
        SNS[SNS]
        PD[PagerDuty]
        Slack
        ITDR[ITDR EventBridge<br/>(ADR-035)]
    end

    EKS --> OCS
    Lambda --> OCM
    APIGW --> CWL
    Aurora --> CWL
    DDB --> CWL
    OCM --> AMP
    OCM --> XRay
    OCM --> CWL
    CWL --> OS

    AMP --> AMG
    XRay --> AMG
    OS --> AMG
    AMP --> CWDash

    AMG --> SNS
    AMP --> SNS
    SNS --> PD
    SNS --> Slack
    AMP --> ITDR

    style Apps fill:#e3f2fd
    style Collector fill:#fff3e0
    style Backend fill:#e8f5e9
    style Visual fill:#fce4ec
    style Alert fill:#ffcdd2
```

### A.2 OpenTelemetry Collector 配置

| 場所 | 役割 | コスト |
|---|---|---|
| **EKS Cluster（DaemonSet）** | Pod レベルメトリクス + Trace 受信 → 集約 | EKS Node に含む |
| **Lambda Layer**（AWS Distro for OpenTelemetry, ADOT）| Lambda 自動計装 | Cold Start 〜100ms |
| **Cross-Acct Collector**（🔵 Audit Acct or 専用 Observability Acct）| 全 Acct 集約 + Backend 送信 | ECS Fargate、$200/月 |

### A.3 自動計装 vs 手動計装

| 項目 | 採用 |
|---|---|
| HTTP リクエスト / レスポンス | **自動**（OpenTelemetry SDK） |
| Database クエリ | **自動**（OpenTelemetry SDK） |
| AWS SDK 呼出 | **自動**（X-Ray SDK 互換） |
| ビジネスロジック Span | **手動**（重要箇所のみ） |
| カスタムメトリクス（テナント別等）| **手動** |

---

## B. SLO 設計

### B.1 サービス別 SLO

| サービス | SLI | SLO（月次）| Error Budget |
|---|---|---|---|
| **Authentication API**（/realms/.../auth）| 可用性（HTTP 200 率）| **99.9%**（年 43.2 分停止）| 43.2 分 / 月 |
| Authentication API | レイテンシ p99 | **< 500ms** | — |
| **Token API**（/token）| 可用性 | **99.95%**（年 21.6 分）| 21.6 分 / 月 |
| Token API | レイテンシ p99 | **< 200ms** | — |
| **Admin API**（/admin/...）| 可用性 | **99.5%**（年 3.6 時間）| 3.6 時間 / 月 |
| Admin API | レイテンシ p99 | **< 1s** | — |
| **JWKS Endpoint**（/.well-known/jwks）| 可用性 | **99.99%**（年 4.3 分）| 4.3 分 / 月 |
| JWKS Endpoint | レイテンシ p99 | **< 100ms** | — |
| **ユーザ管理画面** | 可用性 | **99.5%** | 3.6 時間 / 月 |
| **Trust Center** | 可用性 | **99.5%** | 3.6 時間 / 月 |
| **DSAR Backend** | 完了率（SLA 内）| **99%** | — |

### B.2 SLO 計算（Prometheus Recording Rule 例）

```yaml
# SLI 計算
groups:
  - name: sli
    interval: 30s
    rules:
      # Auth API SLI
      - record: sli:auth_api:availability_5m
        expr: |
          sum(rate(http_requests_total{service="keycloak", endpoint=~"/realms/.*/auth", status_code!~"5.."}[5m]))
          /
          sum(rate(http_requests_total{service="keycloak", endpoint=~"/realms/.*/auth"}[5m]))

      - record: sli:auth_api:latency_p99_5m
        expr: |
          histogram_quantile(0.99,
            sum(rate(http_request_duration_seconds_bucket{service="keycloak", endpoint=~"/realms/.*/auth"}[5m])) by (le))
```

### B.3 Error Budget Burn Rate Alert

| Burn Rate | 期間 | 意味 | アラート |
|---|---|---|---|
| 14.4× | 1h | 1 時間で 1 ヶ月分の Error Budget を 5% 消費 | **Critical PagerDuty** |
| 6× | 6h | 6 時間で 5% 消費 | **High Slack #incident** |
| 3× | 24h | 24h で 5% 消費 | Medium Slack #ops |
| 1× | 通常 | SLO ペース通り | Dashboard のみ |

```yaml
# Alert Rule（Multi-window Multi-burn-rate）
- alert: AuthAPISLOFastBurn
  expr: |
    (1 - sli:auth_api:availability_5m) > 14.4 * (1 - 0.999)
    and
    (1 - sli:auth_api:availability_1h) > 14.4 * (1 - 0.999)
  labels:
    severity: critical
    pager: pagerduty
  annotations:
    summary: "Auth API SLO burning at 14.4x rate (fast burn)"
    runbook: "https://runbook.example.com/slo/auth-api-burn"
```

---

## C. 3 Pillars 詳細

### C.1 Metrics

| カテゴリ | メトリクス例 | Cardinality |
|---|---|---|
| **インフラ**（USE）| CPU / Memory / Disk / Network Saturation | Per-node |
| **サービス**（RED）| Rate / Errors / Duration | Per-service + Per-endpoint |
| **ビジネス** | Login 成功率 / MFA Challenge 数 / SCIM Provisioning 数 | Per-tenant + Per-realm |
| **セキュリティ** | Failed Login / Adaptive Auth Score 分布 / WAF Block 数 | Per-tenant |
| **コスト** | Per-tenant AWS Cost（[ADR-052 §E](052-multi-tenant-isolation-rate-limiting.md)）| Per-tenant |

### C.2 Logs

| ログソース | 形式 | 保管階層 |
|---|---|---|
| **アプリケーションログ**（EKS / Lambda）| JSON 構造化 | CloudWatch Logs（3 ヶ月）→ OpenSearch（1 年）→ S3 Glacier（6 年）|
| **Keycloak Events**（Admin / User）| Keycloak 形式 | 同上、ADR-035 ITDR 連動 |
| **CloudTrail**（AWS API）| JSON | CloudTrail Organization Trail → 🔵 Audit Acct S3（7 年）|
| **WAF Logs**（[ADR-039](039-centralized-network-account-edge-layer.md)）| JSON | Kinesis Firehose → S3 → OpenSearch |
| **ALB / CloudFront Access Logs** | W3C / JSON | S3 → Athena Query 可能 |
| **VPC Flow Logs** | JSON | CloudWatch Logs / S3 |

### C.3 Traces

| 範囲 | 採用 |
|---|---|
| **End-to-End**（CloudFront → Keycloak → DB）| ✅ X-Ray Service Map |
| **Cross-Acct**（Network Acct → Auth Acct）| ✅ X-Ray Trace ID 伝播 |
| **Cross-Region**（DR Failover 時）| ✅ X-Ray |
| **DB クエリレベル** | ✅ Aurora Performance Insights |

### C.4 サンプリング戦略

| トレース種別 | サンプリング率 | 理由 |
|---|---|---|
| 正常リクエスト | **1%** | コスト最小化 |
| Error（5xx）| **100%** | 全て保存 |
| Slow（p99 超過）| **100%** | 全て保存 |
| 特定テナント（顧客サポート時）| **100%**（一時的）| デバッグ |
| Security イベント（ITDR Alert）| **100%** | 監査 |

---

## D. Dashboards 体系

### D.1 ロール別ダッシュボード

| ダッシュボード | 対象 | 主な指標 |
|---|---|---|
| **CISO Executive** | CISO + 経営 | 月次 SLO 達成率 / セキュリティインシデント数 / コスト |
| **SRE On-Call** | SRE / IR | 全 SLO 現状 / Error Budget 残 / Active Alert |
| **Service Owner**（Auth / Admin / DSAR 等）| 各 Lead | サービス別 RED + ビジネス指標 |
| **ユーザ管理画面**（顧客向け）| Tenant Admin | テナント自身の利用状況 / Quota（[ADR-052](052-multi-tenant-isolation-rate-limiting.md)）|
| **Cost Optimization** | FinOps | Per-tenant コスト / Wasted Resources |
| **Security Operations** | SOC | ITDR Alert / Adaptive Auth Score 分布 / WAF Block |
| **DR / Resilience** | SRE Lead | Multi-Region Lag / Backup 成功率 / DR 訓練結果 |

### D.2 Dashboard 例（SRE On-Call）

```
┌──────────────────────────────────────────────┐
│ SRE On-Call Dashboard                          │
├──────────────────────────────────────────────┤
│ Active Alerts: 0 Critical / 2 High / 5 Medium │
│                                                │
│ SLO Status (Last 30d):                        │
│ ┌─────────────────┬────────┬──────────────┐ │
│ │ Service         │ SLO    │ Error Budget │ │
│ ├─────────────────┼────────┼──────────────┤ │
│ │ Auth API        │ 99.95% │ 79% 残       │ │
│ │ Token API       │ 99.97% │ 92% 残       │ │
│ │ Admin API       │ 99.71% │ 42% 残 ⚠     │ │
│ │ JWKS            │ 100.0% │ 100% 残      │ │
│ └─────────────────┴────────┴──────────────┘ │
│                                                │
│ Top Latency (p99, last 1h):                   │
│ ┌─────────────────┬────────┐                  │
│ │ /admin/users    │ 850ms  │                  │
│ │ /token          │ 180ms  │                  │
│ └─────────────────┴────────┘                  │
└──────────────────────────────────────────────┘
```

---

## E. Alerting 階層

### E.1 4 段階優先度

| Severity | 例 | Routing | 応答時間 |
|---|---|---|---|
| **Critical** | SLO Fast Burn / Region 障害 / Aurora Down | PagerDuty（24/7）| **15 分** |
| **High** | SLO Slow Burn / 1 AZ 障害 / Pod Crashloop | Slack #incident + Email | 1 時間 |
| **Medium** | High CPU / High Latency / Disk Full 警告 | Slack #ops | 4 時間 |
| **Low** | Metric Anomaly / Cost Spike | Slack #ops | 営業日中 |

### E.2 Alert Fatigue 対策

- **Alert 集約**（同種 5 分以内は 1 通）
- **Maintenance Window** 中はサプレス
- **Runbook URL 必須**
- **オンコール ローテーション**（疲労防止）
- **月次 Alert レビュー**（Noise 多いものは閾値調整 or 廃止）

### E.3 PagerDuty Escalation Policy

```
On-Call SRE → 15 min 無応答 → Backup SRE
            → 30 min 無応答 → SRE Lead
            → 45 min 無応答 → CTO
```

---

## F. ログ保管階層

### F.1 3 階層 + 規制対応

| 階層 | 期間 | 保管先 | コスト | 検索性 |
|---|---|---|---|---|
| **Hot** | 0-3 ヶ月 | CloudWatch Logs / OpenSearch（Live）| 高 | 高 |
| **Warm** | 3 ヶ月-1 年 | OpenSearch UltraWarm | 中 | 中 |
| **Cold** | 1-7 年（規制対応）| S3 Glacier Deep Archive | 最小 | 低（Athena Query 可）|

### F.2 規制要件対応

| 規制 | 対象ログ | 保管期間 |
|---|---|---|
| PCI DSS §10.7 | 全監査ログ | **1 年（Hot/Warm 容易検索）+ 1 年（最小要件）= 2 年合計** |
| SOC 2 | 監査ログ | **1 年（推奨 7 年）** |
| APPI 第 23 条 | アクセス記録 | **指針に従い適切な期間** |
| 規制業種顧客（金融）| 全監査ログ | **7 年** |
| 規制業種顧客（医療）| 個人情報アクセス | **5 年以上** |

→ **本基盤は規制業種顧客対応で 7 年保管をデフォルト**（[ADR-040 / ADR-045](045-cryptographic-key-management-strategy.md) §D.1 と整合）。

---

## G. メトリクス Cardinality 戦略

### G.1 高 Cardinality 問題

高 Cardinality（Per-user / Per-request_id）はメトリクスストレージ爆発を招く。本基盤は以下に制限:

| ラベル | 採用 / 不採用 |
|---|---|
| `tenant_id` | ✅ 採用（Per-tenant 監視必須）|
| `endpoint` | ✅ 採用 |
| `method` | ✅ 採用 |
| `status_code` | ✅ 採用 |
| `realm` | ✅ 採用（テナント = realm）|
| `client_id` | ✅ 採用（OAuth Client 単位）|
| `user_id` | ❌ 不採用（Cardinality 爆発、ログで対応）|
| `session_id` | ❌ 不採用（同上）|
| `request_id` | ❌ メトリクス不採用、Trace で対応 |
| `ip_address` | ❌ 不採用（プライバシー + Cardinality）|

### G.2 集約

```promql
# 例: Per-tenant + Per-endpoint の RPS
sum(rate(http_requests_total[5m])) by (tenant_id, endpoint, status_code)
```

---

## H. コスト試算

### H.1 月額（10M MAU、月 30 億リクエスト）

| サービス | 月額 |
|---|---|
| Amazon Managed Prometheus（AMP）| $200（Active Series + Ingestion）|
| AWS X-Ray（Trace、1% Sampling = 3000 万 Trace/月）| $150 |
| CloudWatch Logs（Hot 3 ヶ月、月 100 GB）| $50 |
| OpenSearch（Warm 1 年、月 1 TB）| $1,500 |
| S3 Glacier Deep Archive（Cold 6 年、月 10 TB 累積）| $400 |
| Amazon Managed Grafana（AMG）| $50 |
| OTel Collector（ECS Fargate）| $200 |
| Lambda（SLO Recording Rules + Alert）| $50 |
| SNS / PagerDuty Connector | $50 |
| **合計** | **〜$2,650/月（年 〜$32K）** |

### H.2 比較

| 案 | 年額 |
|---|---|
| **本 ADR（AWS Managed + OTel）** | **〜$32K** |
| Datadog（Per-Host + APM + Logs）| $200K+ |
| New Relic | $150K+ |
| Dynatrace | $250K+ |
| Splunk Observability Cloud | $180K+ |
| Self-hosted（Prometheus + Grafana + Loki + Jaeger on EKS）| $50K（運用負荷大）|

→ **商用 APM 比 5-8 倍コスト削減**。

---

## I. 段階的導入ロードマップ

| Phase | 期間 | 内容 |
|---|---|---|
| **Phase 1**（Phase 1 着手と同時、3 ヶ月）| OTel 計装 + AMP + AMG + 基本 Dashboard 5 個 + Critical Alert | 必須 |
| **Phase 2**（3-6 ヶ月）| SLO 全サービス設定 + Error Budget Burn Rate Alert + Distributed Tracing | 必須 |
| **Phase 3**（6-12 ヶ月）| Per-tenant Dashboard + Cost Optimization + AIOps（CloudWatch Anomaly Detection）| 強化 |
| **Phase 4**（12+ ヶ月）| Multi-Region Distributed Tracing + DR 自動検知 + 演習自動化 | 完成 |

---

## J. 代替案検討

| 案 | 評価 | 採否 |
|---|---|---|
| **A. CloudWatch のみ** | Distributed Tracing 弱い、SLO 管理困難 | ❌ |
| **B. Datadog 全面採用** | 年 $200K+、過剰 | ❌ |
| **C. OTel + AWS Managed**（本 ADR）| 業界標準、コスト最適 | ✅ 採用 |
| **D. Self-hosted Prometheus + Grafana + Loki + Jaeger** | 運用負荷大、SRE 工数 +1 FTE | △ Phase 2 検討 |
| **E. New Relic / Dynatrace** | 高機能だが Lock-in + コスト | ❌ |
| **F. AWS X-Ray + CloudWatch のみ**（Vendor Lock-in） | OTel Open Standards に劣後 | ❌ |

---

## K. Consequences

### Positive

- **SOC 2 CC7.1 / CC7.2 / PCI DSS §10 / DORA Continuous Monitoring を 1 つの設計で同時充足**
- **OpenTelemetry Open Standards** 採用で**ベンダー Lock-in 回避**
- **SLO + Error Budget** で**サービス品質を数値管理**
- **Distributed Tracing** で Cross-Service / Cross-Region デバッグ効率化
- **Per-tenant 監視**で Noisy Neighbor 検知（[ADR-052](052-multi-tenant-isolation-rate-limiting.md) 連動）
- **商用 APM 不要、年 $32K**（Datadog 等 $200K+ 比 5-8 倍削減）
- 段階的導入で Phase 1 から運用可能

### Negative

- **OTel 計装の開発負荷**（既存サービス改修必要）
- **メトリクス Cardinality 制限**で個別 User 追跡はログ / Trace 経由
- **Sampling 1%** で正常リクエストの大半は Trace 残らない（Error 100% で実用上問題なし）
- OpenSearch 月 $1,500 がコストの過半（Cold 階層への migration で削減可能）

### Neutral

- AIOps（自動異常検知）は Phase 3 で CloudWatch Anomaly Detection 採用、Datadog Watchdog 等は不採用
- 顧客 SIEM 連携は [ADR-035](035-identity-threat-detection-response.md) ITDR 経由（OCSF 形式）で別途対応
- Cost Optimization Dashboard は FinOps 専任配置後（Phase 2-3）

### 我々のスタンス

| 基本方針の柱 | Observability での実現 |
|---|---|
| **絶対安全** | SLO + Error Budget + Critical Alert PagerDuty 15 分応答 |
| **どんなアプリでも** | OpenTelemetry Open Standards、全 AWS Acct 統一計装 |
| **効率よく認証** | Per-tenant 監視 + Distributed Tracing で問題解決時間短縮 |
| **運用負荷・コスト最小** | AWS Managed Services 中心、商用 APM 不要、年 $32K |

---

## 参考資料

### 標準 / 業界

- [OpenTelemetry 公式](https://opentelemetry.io/)
- [CNCF OpenTelemetry Graduated（2024）](https://www.cncf.io/projects/opentelemetry/)
- [Google SRE Book — SLO](https://sre.google/sre-book/service-level-objectives/)
- [Google SRE Workbook — Implementing SLOs](https://sre.google/workbook/implementing-slos/)
- [Implementing Service Level Objectives — Alex Hidalgo](https://www.oreilly.com/library/view/implementing-service-level/9781492076803/)
- [Brendan Gregg — USE Method](http://www.brendangregg.com/usemethod.html)
- [Tom Wilkie — RED Method](https://thenewstack.io/monitoring-microservices-red-method/)

### AWS

- [AWS Distro for OpenTelemetry (ADOT)](https://aws.amazon.com/otel/)
- [Amazon Managed Service for Prometheus (AMP)](https://aws.amazon.com/prometheus/)
- [Amazon Managed Grafana (AMG)](https://aws.amazon.com/grafana/)
- [AWS X-Ray](https://aws.amazon.com/xray/)
- [CloudWatch Anomaly Detection](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Anomaly_Detection.html)

### Multi-burn-rate Alerting

- [Multi-Window, Multi-Burn-Rate Alerts — Google SRE Workbook](https://sre.google/workbook/alerting-on-slos/)
- [SLOTH — Easy SLO Generator](https://github.com/slok/sloth)

### 規制

- [PCI DSS v4.0 §10 公式](https://www.pcisecuritystandards.org/document_library/)
- [SOC 2 Trust Services Criteria CC7.1-7.2](https://www.aicpa-cima.com/)
- [DORA Continuous Monitoring](https://www.eiopa.europa.eu/digital-operational-resilience-act-dora_en)
