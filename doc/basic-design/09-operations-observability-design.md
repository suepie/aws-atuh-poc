# U9: 運用・監視・IaC 設計（Operations / Observability / IaC）

作成日: 2026-07-24
ステータス: Draft v1.1（Wave 3）
前提: [01-architecture-baseline.md](01-architecture-baseline.md) **Baseline v1（P-01〜P-18）**
上位文書: [00-basic-design-plan.md](00-basic-design-plan.md) §2 U9
主インプット: [ADR-053](../adr/053-observability-strategy.md) / [ADR-059](../adr/059-central-auth-check-canary-architecture.md) / [ADR-046](../adr/046-supply-chain-security.md) / [ADR-055 §A.6-A.7](../adr/055-hrd-implementation-method-selection.md) / [§NFR-6](../requirements/proposal/nfr/06-operations.md) / [research/keycloak-1000idp-scalability-research.md](research/keycloak-1000idp-scalability-research.md) / Wave 1-2 各書の U9 引き渡し節（U2 §2.8 / U3 §3.7 / U4 §4.7.4 / U5 §5.9 / U6 §6.8.3 / U7 §7.9.3 / U8 §8.9.2）

---

## 9.0 背景・なぜここで決めるか

Wave 1/2 の 7 単元（U2/U3/U4/U5/U6/U7/U8）は、設計決定と同時に**運用・監視・IaC への引き渡し事項**を大量に発行した（Runbook 化 20 件超 / 監視メトリクス 30 件超 / 禁則 6 件 / IaC モジュール化・CI lint 要求）。これらは個々の設計書内では「U9 で実装」とだけ記されており、**体系（採番・優先度・実装先）を与えないと Phase 1 実装時に漏れる**。本書は Wave 1/2 の全引き渡しを唯一の運用設計体系に統合し、決定を D-U9-xx で採番する。

**スコープ（責任分界）**: 本書は**自管理側**（Broker Acct / IdP-KC Acct / 弊社監査 Acct、P-17）の運用設計のみを扱う。インターネット境界（P-18: CloudFront + WAF + Network Firewall）は**他組織管理**であり、先方への依頼は U6 §6.7 の要求仕様（REQ-IN / REQ-OUT / REQ-DR 番号体系）への参照に留める。本書が要求仕様に**依存**する箇所（Egress FQDN 更新 §9.7、エッジ DR 切替 §9.4、WAF ログ共有 §9.3）は依存先 REQ 番号を明記する。

**本書の 9 領域**: ①可観測性実装（§9.1）②SLO 定義書（§9.2）③ログパイプライン統合（§9.3）④Runbook 体系 + 禁則集（§9.4）⑤IaC 設計（§9.5）⑥CI/CD（§9.6）⑦IdP オンボーディングパイプライン（§9.7）⑧Central Canary（§9.8）⑨決定・未決・引き渡し（§9.9）。

---

## 9.1 可観測性実装（ADR-053 の ROSA HCP / 6 Acct 体系への確定写像）

### 9.1.1 決定 D-U9-01: スタック確定と OTel Collector 配置

**採用**: ADR-053 の「OpenTelemetry + AWS Managed（AMP / AMG / X-Ray）、商用 APM 不採用」を維持し、実行基盤 = ROSA HCP（P-01/P-15）へ次の配置で確定する:

| コンポーネント | 配置 | 備考 |
|---|---|---|
| OTel Collector（ADOT） | **両クラスタの default（infra）Pool に Deployment**（U6 D-U6-04 の役割分離原則: KC Pool の CPU を食わせない）+ 全ノード DaemonSet（node/Pod メトリクス収集。**KC Pool taint `dedicated=keycloak:NoSchedule` への toleration 必須** — Fluent Bit と同じ落とし穴、U7 v1.1 L-2） | ADR-053 §A.2 の「Cross-Acct Collector（ECS Fargate）」は ROSA 内 infra Pool 配置に置換（追加 Fargate 費不要） |
| メトリクス Backend | **AMP**（弊社監査 Acct に 1 Workspace 集約。Broker / IdP-KC 両 Acct から remote_write、クロスアカウントは IRSA + AMP 書込 Role） | 東西比較・IdP 数関数分析（§9.1.2）を 1 箇所で行うため集約 |
| トレース Backend | **X-Ray**（OTLP 経由）。Sampling は §9.1.3 | ADR-053 §C.3 |
| ダッシュボード / アラート | **AMG**（Grafana Alerting → SNS → PagerDuty / Slack）。SCIM Health Check（U3 §3.5）も AMG Alert で実装 | ADR-053 §D/§E |
| Lambda（Risk Engine / マスキング / Facade 補助） | ADOT Lambda Layer | ADR-053 §A.2 |
| 大阪（DR）側 | **平時から同構成を縮退配備**（外形監視・Collector 常時稼働 — 「DR 側の監視が死んでいた」防止、U8 §8.6 引き渡し） | U8 §8.9.2 |

- **根拠**: ADR-053 Decision（年 ~$32K、商用 APM 比 5-8 倍削減）、U6 D-U6-04（infra Pool 別建て）、U8 §8.9.2。
- **代替**: OpenShift 同梱 Cluster Monitoring（Prometheus）単独 — クラスタ内メトリクスは取れるが、6 Acct 横断（Lambda / Aurora / DynamoDB / Canary）と長期保管・東西統合が弱い。ROSA 同梱 Prometheus は**ノード/プラットフォーム監視の一次ソース**として残し、AMP へ federate する（二重管理はしない）。
- **未決**: infra Pool サイジング実測（U6 O-11: 1000+ IdP 時の時系列カーディナリティ + マスキング処理量、G-IdP-Scale P-4 と併せ実測）。

### 9.1.2 決定 D-U9-02: Keycloak 計装ポイントと「IdP 数の関数」監視（P-16 必須対策 7）

**採用**: KC 26 の組込みメトリクス（`metrics-enabled=true`、management port）+ Custom SPI 内計測 + イベント由来メトリクスの 3 系統で計装し、**主要系列は IdP 数・Org 数を注記した時系列として継続計測**する（U2 §2.7.7 の実装確定）:

| # | メトリクス / 計装ポイント | 供給元 | 閾値・用途 |
|---|---|---|---|
| 1 | ログインフロー p99（`first-broker-login` 含む、系統②） | KC HTTP メトリクス + X-Ray | **「10 IdP 時点ベースライン比 +10%」で警戒**（PoC P-2 合否基準の運用転用、U2 §2.7.7） |
| 2 | HRD 解決時間（`getByAlias` レイテンシ） | **HRD SPI ② 内の手動計装**（Micrometer Timer） | 同上。IdP 追加バッチ（+100 社）前後比較 |
| 3 | IdP 系 Admin API（作成/更新/一覧）p99 | KC HTTP メトリクス | 同上 |
| 4 | `infinispan_cache_hit_ratio`（realms 系 / users） | KC Infinispan メトリクス | **≥ 90% 維持**（U6 §6.5.5 / D-U6-10。下回れば cache max-count 増 → U6 と再サイジング） |
| 5 | IdP キャッシュエントリ数 / Aurora CPU | 同上 + RDS メトリクス | エントリ数は IdP 数に線形か（P-4 検証と同軸） |
| 6 | `login_success_password_rate`（TPS/node） | KC イベント由来 | **> 8 TPS/node 3 分で IdP-KC Scale-Out 予兆トリガ**（CPU 閾値より優先、U6 §6.5.4 / U8 D-U8-02） |
| 7 | SAML DSig 検証比率 / CPU | KC メトリクス | SAML 顧客比率上昇時の Broker CPU 上振れ補正（U6 §6.5.3） |
| 8 | Aurora Global lag | RDS メトリクス | **> 10s warning / > 30s critical**（U8 §8.5.2。`rds.global_db_rpo` は設定しない決定の代替担保） |
| 9 | PrivateLink Endpoint 疎通（Broker→IdP-KC バックチャネル） | 内部 synthetic（infra Pool CronJob） | 断 = フェデ経路全断の先行指標（U6 §6.8.3） |
| 10 | `log_scrubbing_leak_count` / マスク処理件数 | Fluent Bit / Lambda メトリクス | 漏れ目標 0。**マスク件数の突然のゼロはパイプライン故障アラート**（U7 §7.3.1） |
| 11 | SCIM Facade: 受信レート / エラー率 / 突合結果分布 | Facade 手動計装 | SCIM Health Check 4 閾値（24h 無受信 / ベースライン比 50% / エラー率 5% / ユーザ数 1h 10% 変動、U3 §3.5。カスタマイズは B-SCIM-HC-1） |
| 12 | HIBP 照会失敗率（fail-open 発生数） | ITDR Lambda | fail-open 多発 = 侵害 PW 検知の穴（U7 §7.2.2） |
| 13 | 東西 ECR digest 一致 / 大阪外形監視 | 日次 CI + Synthetic | U8 §8.9.2 |
| 14 | KMS 監視（CMK 無効化・Key Policy 変更・Decrypt 失敗急増） | CloudTrail → EventBridge | U7 §7.1.2 引き渡し |

AMG に「**IdP スケールダッシュボード**」を常設し、#1〜5 を IdP 数注記付きで表示、IdP 追加バッチ前後のスナップショット比較をオンボーディングパイプライン（§9.7）の完了条件に組み込む。

- **根拠**: P-16（条件付き成立の条件 7「IdP 数の関数として継続計測」）、research 必須対策 7、U2 §2.7.7 / U6 §6.8.3。
- **未決**: SPI 内 Micrometer 計装の RHBK 互換（G-SPI-Compat に検証項目として追加依頼 → U2）。

### 9.1.3 決定 D-U9-03: Cardinality 規約・Per-tenant メトリクス・Trace Sampling

**採用**: ADR-053 §G/§C.4 をそのまま規約化する:

| 項目 | 決定 |
|---|---|
| ラベル採用 | `tenant_id`（= Org alias）/ `endpoint` / `method` / `status_code` / `client_id` を採用。`user_id` / `session_id` / `request_id` / `ip_address` は**メトリクス禁止**（ログ / Trace で追跡） |
| Per-tenant | ログイン成功率・SCIM 受信・エラー率をテナント単位で常設（Noisy Neighbor 検知）。1000+ テナント × endpoint の系列数は AMP 課金に直結するため、**テナント別系列は「ログイン系 + SCIM 系のみ」に限定**し、他は集約系列 + ログで代替 |
| Trace Sampling | **正常 1% / Error(5xx)・Slow(p99 超過)100% / 顧客サポート時の特定テナント一時 100% / ITDR アラート関連 100%**（ADR-053 §C.4） |
| Trace 伝播 | エッジ（他組織 CloudFront）は透過を期待できないため、**Trace 起点は Internal ALB / KC** とする（X-Amzn-Trace-Id は自管理層で採番） |

- **根拠**: ADR-053 §G（Cardinality 爆発防止）、P-16（1000+ テナント前提でのコスト統制）。

---

## 9.2 SLO 定義書（NFR-6 標準値の正式採用 + Burn Rate 運用）

### 9.2.1 決定 D-U9-04: サービス別 SLO と Burn Rate Alert

**採用**: §NFR-6.1 の SLO 標準値を Phase 1 正式値として凍結する（顧客契約 SLA は 99.9% = P-04。下表はそれを支える**内部 SLO**）:

| サービス（SLI 計測点） | 可用性 SLO | レイテンシ p99 | 月間エラーバジェット |
|---|---|---|---|
| Authentication API（`/realms/*/auth`、SAML 含む） | **99.9%** | < 500ms | 43.8 分（U8 D-U8-01 と同値） |
| Token API（`/token`） | **99.95%** | < 200ms | 21.9 分 |
| Admin API（`/admin/*`、専用 API 層含む） | **99.5%** | < 1s | 3.6 時間 |
| JWKS（`/.well-known/*` / `/certs`） | **99.99%** | < 100ms | 4.4 分 |
| ユーザ管理画面 / SCIM Facade | 99.5% | — | 3.6 時間 |

計測・除外規定は U8 D-U8-01 に従う: 計画メンテ窓（月 1・深夜 2-4 時・7 日前通知）/ 顧客起因 / **顧客 IdP 起因のフェデ失敗は除外**（責任分界 L1 側）。他組織エッジには可用性 99.95% を要求済み（REQ-DR-04）であり、**エッジ起因の停止は SLA 協議事項として区分計上**する（Synthetic の CloudFront 経由 / Internal 直の 2 系統計測で切り分け、§9.8 と共用）。

**Burn Rate Alert**（Google SRE 流 Multi-window Multi-burn-rate、ADR-053 §B.3）:

| 区分 | Burn Rate | ウィンドウ | Routing |
|---|---|---|---|
| **Fast Burn** | 14.4× | 5m + 1h の AND | Critical → PagerDuty（応答 15 分） |
| **Slow Burn** | 6× | 30m + 6h の AND | High → Slack #incident（1h） |
| 予兆 | 3× | 2h + 24h の AND | Medium → Slack #ops（4h） |

実装は AMP Recording Rules（`sli:*` 系列を 30s 間隔で事前計算）+ AMG Alerting。4 サービス × 2 種（可用性 / レイテンシ）を Phase 1 で全て設定する（ADR-053 ロードマップの Phase 2 項目を前倒し — SLA 契約が Phase 1 から始まるため）。

**エラーバジェット運用**: ①残バジェットは SRE On-Call ダッシュボード常設（ADR-053 §D.2）②バジェット 50% 消費で変更凍結の要否を週次レビュー ③**バジェット枯渇時は機能変更（SPI 更新・バージョン昇格）を凍結し信頼性作業のみ許可**（例外は SRE Lead + Security Lead 承認）④月次で消費内訳（自管理 / エッジ / 顧客 IdP 起因）を分類し、エッジ起因分は他組織との定例で提示（REQ-DR-04 の実効性検証）。

- **根拠**: §NFR-6.1 SLO 標準値、ADR-053 §B、U8 D-U8-01（直列可用性 99.87〜99.92%、律速 = 他組織エッジ）。
- **未決**: B-OBS-4/5（SLO 公開範囲・顧客 SLA 連動）、Admin API SLO にユーザ管理画面 API を含める境界の最終確定（U10 と合同）。

---

## 9.3 ログパイプライン統合（U7 §7.3 実装の運用確定）

### 9.3.1 決定 D-U9-05: 3 層保管の最終形（ADR-053 §F を U7 D-U7-13 で上書き）

**採用**: ログ経路と保管を次で統合する。ADR-053 §F の「Hot 3 ヶ月 / Warm 1 年 / Cold 6 年（Glacier）」は、U7 D-U7-13（PCI DSS 10.5.1 即時 3 ヶ月 + 7 年 WORM）で確定した実装に**置き換える**:

```
KC Container stdout（両クラスタ）
  → Fluent Bit DaemonSet（全ノード、KC Pool toleration 付き）
  → Fluent Bit Aggregator（infra Pool Deployment、マスキング辞書 M-1〜14 を集中適用 = scrubbing、U7 §7.3.1）
  → ① CloudWatch Logs（Hot 90 日 — PCI「直近 3 ヶ月即時参照」充足）
  → ② Kinesis Firehose → 監査 Acct S3【Object Lock Compliance 7 年】+ Athena（Cold / WORM）
  → ③ OpenSearch（Warm — 検索・週次監査スキャン・SIEM 相関用）
ALB access log / CloudWatch Logs（Lambda・Facade・API 層）
  → マスキング Lambda 経由で同 3 層へ（U7 §7.3.1 の表の通り）
```

| 項目 | 決定 |
|---|---|
| Hot | CloudWatch Logs **90 日**（両 Acct。retention は IaC 固定、変更は PR のみ） |
| Cold | 監査 Acct S3 **Object Lock Compliance mode 7 年**（削除不可。`*-audit-logs` CMK、U7 D-U7-01/13） |
| Warm | OpenSearch（弊社監査 Acct）。保持は **1 年 + UltraWarm 移行**を初期値とし、サイジングはログ量実測後確定（U7 未決の継承） |
| 順序保証 | **全ソース scrubbing 通過後に保存**（平文がいずれの層にも入らない、U7 D-U7-13）。大阪側にも Aggregator・マスキング経路を平時配備（U8 §8.6） |
| 監査スキャン | OpenSearch 週 1 定期クエリ（`Bearer eyJ` / `SAMLResponse=` / `code=` / `logout_token=`）を **AMG Dashboard 化 + 検出時 SOP は RB-SEC-04 系に接続**（U7 §7.3.1 の U9 引き受け分） |
| CloudFront ログ | 他組織管理。REQ-IN-10（query string 記録最小化 + 配信時マスク）の回答待ち。**未対応でも自管理 2 層で Bearer/token 系は遮蔽される**が認可 code 残余リスクは残る（U7 §7.3.1） |

- **根拠**: U7 D-U7-07/13（配置・辞書・WORM は U7 で確定済み。本書は保持値・スキャン Dashboard・ジョブ実装を確定）、ADR-053 §F（改訂対象 — §9.9.3）。
- **代替**: OpenShift Cluster Logging（Vector）— U7 §7.3.1 の再評価条件を維持（Phase 1 は Fluent Bit 資産流用）。

### 9.3.2 決定 D-U9-06: SIEM 取込イベントセット（OpenSearch 相関 + ITDR 連携）

**採用**: Keycloak Event Listener SPI（emit 専任、U7 D-U7-04）の対象イベントを SIEM（OpenSearch + Risk Engine）への必須取込セットとして確定する:

| 分類 | イベント | 由来 |
|---|---|---|
| 認証 | `LOGIN` / `LOGIN_ERROR` / `CLIENT_LOGIN` / `CODE_TO_TOKEN` / `REFRESH_TOKEN` | Golden 検知 G-2/G-3/G-6 の入力（U7 §7.4.1） |
| トークン | `TOKEN_EXCHANGE`（subject / requester client / audience / scope 付き） | U5 §5.3.3 監査必須 |
| **revoke / logout 系** | **`REVOKE_GRANT` / `LOGOUT` / `LOGOUT_ERROR`**（+ not-before push の Admin Event） | **U5 §5.9.2 依頼 → U7 v1.1 L-1 で emit セット確定済み**。本書で SIEM 取込側も確定 |
| ライフサイクル | `USER_REACTIVATED`（Re-Activation SPI 監査、U3 D3-12）/ USER_DELETED・USER_DISABLED（SCIM Facade → EventBridge 経由） | jit-scim §10.4.I / U3 §3.5 |
| 管理操作 | Admin Events 全量（IdP/Org/Client/Flow の作成・変更・削除 — ドリフト検知 §9.5.3 の照合ソースを兼ねる） | U8 §8.3.2 #3 |
| 基盤 | CloudTrail（6 Acct、Org Trail → 監査 Acct）/ kubernetes audit log / Break-Glass 使用イベント | U7 §7.6.2（監査 Acct 一元、WORM 7 年） |

顧客 SIEM への提供（OCSF 形式、ADR-035 経由）は Phase 2。B-OBS-2（ダッシュボード共有範囲）の回答で優先度を再評価。

- **根拠**: U5 §5.9.2 + U7 §7.4.1（イベントセットの発行側は確定済み — 本決定は取込・保管・相関側の確定）。

---

## 9.4 Runbook 体系と禁則集

### 9.4.1 決定 D-U9-07: Phase 1 Runbook 一覧（NFR-6 ユースケース A〜G の実装写像）

**採用**: §NFR-6.5 のユースケース A〜G を次の採番体系で Phase 1 Runbook に落とす。**太字は Phase 1 リリース前に文書 + 訓練必須**（それ以外はリリース後 3 ヶ月以内）:

| RB 番号 | 内容 | 仕様元 |
|---|---|---|
| **RB-TEN-01** | 顧客追加（IdP オンボーディング、§9.7 パイプラインの手動介入点含む）。**付属: 顧客オンボーディングガイド**（IdP 側ブランディング・A11y 推奨・HRD ドメイン周知、U4 §4.7.4） | NFR-6.5 A-1、§FR-2.3.2、U4 §4.7.4 |
| RB-TEN-02 | 顧客 IdP 設定変更（証明書ローテ / 属性追加。顧客名変更・M&A 時は **alias 不変 + 表示名変更**で吸収 — U2 §2.2 未決の運用ルール化） | NFR-6.5 A-2、U2 §2.8 |
| **RB-TEN-03** | 顧客離脱（Pattern C: Day 0-30 エクスポート → Day 30 Realm disable → Day 90 全 Soft Delete → retention_years 後物理削除 + 完了証明書） | NFR-6.5 A-3、U3 §3.4 / jit-scim §10.4.L |
| RB-TEN-04 | JIT↔SCIM 切替（Pattern A: matchByEmail + bulk update / Pattern B: **scim_active=false + provisioned_by=jit + last_login=now 切替スクリプト必須 — 漏れると Zombie 永続化**） | U3 §3.4（B-TENANT-SWITCH-1） |
| RB-TEN-05 | SCIM Bearer トークンローテ（90 日標準。顧客 IdP 側再設定を伴うため顧客連絡テンプレート同梱） | U3 §3.5 |
| RB-TEN-06 | ServiceNow オンボーディング（並走 M0〜M3 + 提供 6 点セット + 受入テスト T-1〜T-5 + 削除連鎖確認 T-3） | U10 §10.1 |
| RB-TEN-07 | Webhook 購読登録（テナント × endpoint × イベント種の登録・変更。**顧客アプリ endpoint FQDN の Egress 申請込み** — §9.7 ステップ 3 と同プロセス） | U10 §10.3 |
| RB-APP-01〜03 | アプリ追加 / 認可要件追加 / 廃止（廃止時 RT 強制失効含む） | NFR-6.5 B-1〜B-3 |
| RB-USR-01〜04 | 個別 CRUD / PW リセット / MFA リセット / ロック解除（**γ シナリオ P-07 により対象は管理者層のみ・週次〜月次頻度**。P-3 フェデユーザは顧客 IdP 責任）。**RB-USR-03（MFA リセット）は Recovery Codes 管理者リセットを含む**（U4 §4.3.3。本人確認手順込み） | NFR-6.5 C-1〜C-4、U4 §4.3.3 |
| RB-USR-05 | 一括インポート / 一括 deprovision（テナント一括 logout ジョブ含む — U5 引き渡し） | NFR-6.5 D-1〜D-3、U5 §5.9.2 |
| **RB-SEC-01** | クレデンシャル侵害対応 = ITDR L4 発動手順（手動承認 → not-before push + 全セッション削除 + Back-Channel Logout 一斉送信 + **AT ゾンビ窓 ≤30 分の追加監視**〔対象 sub/azp の API アクセス監視〕） | U5 §5.4.3 / U7 D-U7-05、NFR-6.5 E-1 |
| **RB-SEC-02** | 強制ログアウト・Revocation 3 粒度（個別 / Client / 全体）・not-before push 単体手順 | U5 §5.4、NFR-6.5 E-2 |
| RB-SEC-03 | 緊急 IP 制限（自管理 = Internal ALB / SG。エッジ WAF は他組織への Fast Track 依頼 — REQ-IN-01 の連絡手順） | NFR-6.5 E-3、U7 §7.8.1 |
| **RB-SEC-04** | 漏えい等報告 SOP（APPI 速報 3-5 日 / 確報 30・60 日、7 ステップ + 4 類型判定表） | U7 D-U7-15 |
| **RB-SEC-05** | 緊急鍵ローテ SOP（Golden 検知 Critical: 並走なし旧鍵即時無効化 + not-before push + RP へ JWKS 再取得注意喚起。承認体制は B-GD-3） | U7 §7.1.3 / §7.4 |
| **RB-SEC-06** | Break-Glass 手順（使用 = インシデント扱い、事後 Git 反映必須） | U7 §7.6 |
| RB-SEC-07 | SN Break Glass 定期テスト（四半期ログインテスト + 使用時 SIEM 通知・PW ローテ確認。本基盤の Break-Glass〔RB-SEC-06〕とは独立の SN ローカル経路） | U10 §10.1.5 |
| RB-PLT-01 | CVE 緊急パッチ（Trivy/Inspector 検知 → SLA: Critical 24h / High 7 日〔ADR-046 §C.3〕→ §9.6 パイプラインで昇格。**zero-egress 採用時（U6 O-10 案 B）は Critical CVE の緊急イメージミラー同期手順を含む** — U7 D-U7-16） | NFR-6.5 F-1、ADR-046 |
| RB-PLT-02 | 定例バージョンアップ（§9.6.3 の昇格プロセス手順書） | NFR-6.5 F-2、U2 §2.7.1 |
| RB-PLT-03 | 計画メンテナンス窓運用（月 1・深夜 2-4 時、7 日前通知、SLO 除外登録） | NFR-6.5 F-3、U8 §8.1.4 |
| RB-PLT-04 | 定例鍵ローテ（Realm Key 90 日 Cryptoperiod・30 日並走。CronJob `broker-irsa-ops-key-rotation` の監視と失敗時手動手順）。**SN 用 SAML RSA 証明書ローテ（U10-OP-1: 年 1 回 + 2 世代並走 + SN 側再登録手順）を本 Runbook に統合** | U7 §7.1.3、U10-OP-1 |
| RB-PLT-05 | スケール対応（IdP-KC 予兆トリガ発火時の Machine Pool 増設 / Blue-Green 2xlarge Pool 切替） | NFR-6.5 G-2、U6 D-U6-04 |
| RB-MIG-01 | 既存システム移行実行（**PW ハッシュ調査票**〔algo / パラメータ / salt 形式 / 抽出可否 / 件数 / 最終ログイン分布〕を付録化 + 移行バッチ + ロールバック手順） | U10 §10.4 |
| RB-DSAR-01 | DSAR 対応（JSON / SCIM 2.0 エクスポートスクリプト + Soft Delete + 仮名化 + SLA 手動追跡〔GDPR 30 日 / APPI 14 日目標〕） | U10 §10.5 |
| **RB-DR-00〜05** | DR 系 6 冊（本書は U8 §8.7.2 仕様の**文書実体化のみ**を担う）: 00 判定チェックリスト（**ITDR 抑制/強化フラグ切替を含む**: G-2/G-3 通知のみ降格 + Brute Force 感度引上げ、U7 §7.2.3）/ 01 Aurora Promote × 2 系統 / 02 DNS・エッジ切替（REQ-DR-02 連絡手順）/ 03 大阪スケールアップ + KC 起動 + 検証 / 04' PITR + 差分 IaC 再生 / 05 フェイルバック（**冒頭に禁止 3 操作**） | U8 §8.7.2 / §8.9.2 |

付属物: 顧客向け Failover 告知文テンプレート（「再認証が必要」「発行済みパスワードリセットリンクは無効化」を明記、U8 §8.5.3）/ エスカレーション図（on-call → セキュリティ → 法務 → 顧客、NFR-6.5 ベースライン）/ 全 Runbook に AMG ダッシュボード URL と対応アラート名を必須記載（ADR-053 §E.2「Runbook URL 必須」の逆リンク）。維持: 年次見直し + Game Day / Tabletop（ADR-044、U8 D-U8-13）で完走率 100% を KPI とする。

### 9.4.2 決定 D-U9-08: 運用禁則集（違反 = 設計逸脱として CI / レビューで機械強制）

**採用**: Wave 1/2 で確定した禁則を 1 枚に集約し、可能なものは CI lint / パイプライン reject で機械強制する:

| # | 禁則 | 由来 | 強制手段 |
|---|---|---|---|
| K-1 | **realm 全体 export / import / partial-export を一切使用しない**（バックアップ・監査含む全用途。構成読取は IdP/Org/Client 単位 Admin API のみ） | U2 §2.7.4 / U8 D-U8-06（P-16 必須対策 4） | Runbook 全冊に明記 + Admin Events で export 操作を検知しアラート |
| K-2 | **クラスタ全 Pod の同時再起動を伴う操作は Aurora Writer 安定後に実施**（jdbc-ping ディスカバリ書込失敗のため） | U6 §6.4.2 / U8 §8.1.3 | RB-PLT-02/05・RB-DR-03 のチェック項目 |
| K-3 | **ITDR 抑制/強化フラグは RB-DR-00 でのみ操作**（Game Day / DR ウィンドウ宣言〜完了 + 2h に限定。恒常的な検知降格を禁止） | U7 §7.2.3 / U8 §8.9.2 | フラグ変更を監査ログ必須 + ウィンドウ外の変更をアラート |
| K-4 | **フェイルバック禁止 3 操作**: 東京旧 Aurora 独立再起動 / Global Cluster 削除 / 同期完了前の東京 Primary 復帰 | U8 §8.7.1 | RB-DR-05 冒頭明記 |
| K-5 | **Admin Console 直接変更禁止**（変更経路は基盤層 Terraform / テナント層パイプラインのみ。緊急時 Break-Glass のみ + 事後 Git 反映必須） | U8 §8.3.2 #1 | 日次ドリフト検知（§9.5.3）+ Break-Glass 監査 |
| K-6 | **`requiresUser()=true` の Custom SPI を top-level REQUIRED に置かない**（forms サブフロー内 / Broker Flow 末尾のみ） | U2 §2.3（PoC F-6） | **IaC レビューチェックリスト必須項目 + Flow 定義 lint**（realm.json / Terraform の構造検査） |
| K-7 | **secret / SCIM Bearer の IaC 直書き禁止**（Secrets Manager 参照のみ、PCI 8.6.2） | U7 §7.5.3 | CI lint（gitleaks + カスタムルール）で PR ブロック |
| K-8 | **`hideOnLoginPage=true` 必須 / Org 非紐付け IdP の新規作成禁止** | U2 §2.7.2/2.7.3（P-16 対策 2/3） | オンボーディングパイプラインの reject 条件 + 日次ドリフト検知の検査項目 |
| K-9 | **単一 Terraform state に 1000 IdP 級のテナント層リソースを置かない** | U2 §2.7.5（設計として不成立） | §9.5.1 の 2 層分離で構造的に排除 |
| K-10 | **Admin REST API クライアント（Terraform / 管理画面 Backend / パイプライン）は内部ホスト名 + 内部経路経由に統一**（公開 `/admin` 経路は 3 層防御で遮断済み） | U6 §6.6.1 / D-U6-11 | provider 設定を IaC テンプレート固定 |
| K-11 | OLM 自動更新禁止（Explicit Strategy。パッチも Staging 1000 IdP 回帰通過が必須） | U2 §2.7.1 / U8 §8.1.4 | Subscription CR を IaC 固定 + ドリフト検知 |

- **根拠**: 各行の由来欄。禁則を「知識」でなく「機械強制 + チェックリスト」に落とすことが本決定の趣旨（運用者の記憶に依存しない）。

---

## 9.5 IaC 設計（Terraform 2 層 + state 分離 + ドリフト検知）

### 9.5.1 決定 D-U9-09: モジュール分割と state 分離マトリクス

**採用**: state は「**AWS アカウント × 層**」で分離する（U6 §6.1.2 の Acct ごと分離 + U2 §2.7.5 の基盤層/テナント層分離を合成）:

| state | 対象 | 主モジュール |
|---|---|---|
| `broker-infra`（Broker Acct） | VPC / ROSA HCP / Machine Pool / Aurora / PrivateLink / IRSA Role 群 / KMS Key Policy / Secrets / EventBridge / ITDR（Risk Engine Lambda・DynamoDB・閾値）/ ログパイプライン（Fluent Bit 設定・Firehose・マスキング辞書） | `modules/rosa-cluster` `modules/aurora-global` `modules/kms-cmk`（U7 Key Policy 3 ロールテンプレート） `modules/logging-pipeline` `modules/itdr` |
| `idpkc-infra`（IdP-KC Acct） | 同上の IdP-KC 版 + 専用 API 層 / SCIM Facade（D1） | 同上再利用 |
| `audit-infra`（弊社監査 Acct） | Org Trail 集約 S3（Object Lock）/ OpenSearch / AMP / AMG / Central Canary（§9.8）/ Athena | `modules/observability` `modules/canary` |
| `broker-kc-realm` / `idpkc-kc-realm`（**基盤層 KC**） | Realm 設定 / Authentication Flow 5 系統 / Custom SPI 配備参照 / 共通 Client Scope / アプリ Client テンプレート / User Profile 宣言 / TTL 体系（U5 確定値） | terraform-provider-keycloak（**内部ホスト名経由**、K-10） |
| **テナント層（state を持たない）** | Organization / 顧客 IdP / IdP Mapper / Org-IdP リンク | **オンボーディングパイプライン（§9.5.2）— Terraform 管理外** |
| `dr-osaka-*`（大阪 overlay） | 東京の各 state の大阪版（Machine Pool min 0 / パイロットライト） | **日次 plan 検証**（U8 §8.9.2）+ Machine Pool スケールアップ定義 |

運用規約: リソース数が IdP 数に依存する定義を基盤層 state に置かない（K-9）/ 環境（dev / staging / prod）は別 AWS アカウント + 別 state（NFR-6.4 ベースライン）/ apply は CI のみ（GitHub OIDC → 各 Acct の Terraform Role、U6 §6.1.2。ローカル apply 禁止）。

- **根拠**: U2 §2.7.5（単一 state 5,000〜8,000 リソースは plan 分〜十分オーダーで不成立）、U6 §6.8.3、research §Terraform。分割閾値の実測は PoC P-6。

### 9.5.2 決定 D-U9-10: テナント層エンジン = 自作オンボーディング API（keycloak-config-cli 不採用）

**採用**: テナント層の宣言と適用は次で確定する:

- **宣言**: テナント単位の宣言ファイル（`tenants/<tenant_id>/idp.yaml` — Org 定義 / IdP 接続 / Mapper セット / HRD ヒントキーを 1 ファイルに集約）を Git 管理。テンプレートは IdP 種別ごと（`-entra01` / `-okta01` / `-saml01` 等、U2 の alias 規約）。
- **適用エンジン**: **自作オンボーディング API（パイプライン Worker）が Keycloak Admin API を IdP / Org / Mapper 単位で呼ぶ**。**keycloak-config-cli は不採用** — 同ツールは realm representation ベースの import を中核とするため、**制約 K-1（realm representation を扱う運用の禁止、U2 §2.7.4）と原理的に衝突**し、1000+ IdP では realm JSON 肥大の再輸入になる。U2 §2.7.5 の「Admin API or keycloak-config-cli」の選択は本決定で前者に確定する。
- **冪等性**: 宣言ファイル → 期待状態の差分適用（GET → 差分 → PUT/POST）。適用結果 / 差分 / 実行者を監査 Acct へ記録。
- **検証**: 適用エンジン自体を G-IdP-Scale P-1（一括投入スクリプト）の恒久資産として実装し、PoC と本番投入で同一コードパスを使う（U2 §2.7.1 の合成データセット投入にも流用）。

- **根拠**: U2 §2.7.4/2.7.5、U8 D-U8-06 経路 2（テナント単位再生はこの宣言ファイルが SSOT）、research 対策 5。
- **代替**: Terraform テナント単位 state 分割（50-100 社バッチ）— 1000 state の管理・plan 時間・provider の Admin API 負荷から次善。パイプライン障害時の**手動フォールバック手段**として手順のみ RB-TEN-01 に残す。

### 9.5.3 決定 D-U9-11: ドリフト検知（日次 CI、U8 経路 2 の成立前提）

**採用**: U8 §8.3.2 の仕様を次で実装する:

| # | 検知 | 実装 |
|---|---|---|
| 1 | 基盤層 | 日次 CI で全 state `terraform plan -detailed-exitcode` 差分ゼロ確認（`-refresh=false` は日次検知では使わない — 検知が目的のため refresh あり。ただし KC realm 系 state は Admin API 負荷を考慮し夜間実行） |
| 2 | テナント層 | **Admin API 読取（IdP / Org / Mapper 単位の GET、ページング走査）と宣言ファイルの突合スクリプト**。realm 全体 export は使わない（K-1）。検査項目に K-8（hideOnLoginPage / Org 紐付け）を含む |
| 3 | ドリフト時対応 | 差分検知 → Admin Events / CloudTrail 照合 → **正当（Break-Glass 等）なら Git へ逆反映 PR / 不正なら経路 2（PITR + 差分 IaC 再生）発動判断 + ITDR 連携**（RB 化: RB-SEC 系に「ドリフト = 不正変更疑い」フローを追加） |
| 4 | 大阪 | 大阪 overlay の日次 plan + Game Day で「大阪昇格後構成 = Git」突合（U8 §8.3.2 #4） |

- **根拠**: U8 D-U8-07（経路 1 の成立条件 =「Aurora の中身 = Git」の常時担保）、U8 §8.9.2。

---

## 9.6 CI/CD（ROSA HCP + RHBK Operator 前提）

### 9.6.1 決定 D-U9-12: パイプライン構成（CI = GitHub Actions / CD = OpenShift GitOps / Registry = ECR）

**採用**: ADR-055 §A.6 の ROSA HCP 列を基礎に、ツールを次で確定する:

| 段 | 採用 | 根拠・補足 |
|---|---|---|
| CI | **GitHub Actions + OIDC Federation**（long-lived key なし、各 Acct Role へ AssumeRole） | ADR-046 §E.2 の確定済み方式 + U6 §6.1.2 の GitHub OIDC 経路と整合。**Tekton（OpenShift Pipelines）は不採用** — ADR-046 の SLSA / Cosign / SBOM 資産が GitHub Actions 前提で構築済みであり二重投資を避ける |
| Container Registry | **ECR**（Quay.io 不採用） | U8 §8.2.2（ECR クロスリージョンレプリケーション = DR 前提）+ U6 O-10 zero-egress 案 B（ECR ミラー = サプライチェーン単一検証点、U7 D-U7-16）と整合。RHBK ベースイメージは Red Hat レジストリから **ECR へミラー**して利用（pull 経路を ECR に一元化） |
| CD（クラスタ内） | **OpenShift GitOps（ArgoCD、ROSA 同梱）**: Keycloak CR / ConfigMap / SPI イメージ参照 / Fluent Bit・OTel 設定を Git → クラスタ同期 | ADR-055 §A.6（同梱・追加費不要）。Image 更新は Git 上の digest 書き換え（ImageStream Trigger は使わず GitOps に一本化） |
| KC デプロイ | **RHBK Operator（Keycloak CR の `image:` にカスタムイメージ digest 指定）**。ローリングは U8 D-U8-04 の区分（パッチ = Auto ローリング / マイナー = メンテ窓） | ADR-055 §A.6 / U8 §8.1.4 |
| Terraform 実行 | GitHub Actions（plan を PR コメント → 2 名レビュー〔NFR-6.4〕→ merge 後 apply、本番は手動承認ゲート） | NFR-6.4 推奨フロー |
| Secret | AWS Secrets Manager + External Secrets Operator（クラスタへは ESO 経由でのみ供給） | ADR-055 §A.6 EKS 列の方式を ROSA でも採用（Secrets の SSOT を AWS 側に維持、U7 ローテ系統と直結） |
| Theme / A11y 検査（CI 段） | **Theme lint（CSRF hidden field 保持・IdP 一覧非描画・messages 集約チェック）+ axe-core CI（Keycloak テストコンテナで実画面を起動して検査、WCAG 2.2 AA 違反で PR ブロック）** | U4 §4.6.3 / D-U4-08 / §4.7.4（Theme PR チェックリストの機械強制。K-6 Flow lint と同じ CI 段） |
| PII クレーム検査（CI 段） | **PII クレーム検査 CI（realm 設定 lint + 実トークンデコード検査、C-1〜C-7）** | U5 §5.1.4（PII 非搭載原則 P-10 の機械強制） |

環境昇格: dev → staging → production の 3 段階（別 Acct）。本番 apply / イメージ昇格は手動承認。Fast Track（緊急）は on-call 単独承認 + Skip staging 可、事後レビュー必須（NFR-6.4）。

### 9.6.2 決定 D-U9-13: Custom SPI のビルド・検証・カナリアデプロイ

**採用**: SPI 3 JAR・4 機能（JIT 制御〔Re-Activation 統合〕/ HRD / Event Listener / mfa_indicator Mapper — U2 §2.4 と整合）のサプライチェーンを ADR-046 の 6 層に沿って確定する:

1. **ビルド**: Maven（`cyclonedx-maven-plugin` で SBOM 生成）→ KC ベースイメージ（ECR ミラー済み RHBK）へ SPI JAR を焼き込み、**単一のカスタムイメージ**として出荷（JAR 単体配布はしない — イメージ digest = 検証単位）。
2. **検証**: Trivy スキャン（SLA: Critical 24h / High 7 日、ADR-046 §C.3）→ **Cosign 署名 + SLSA Provenance 生成**（Phase 1 = SLSA L2、12 ヶ月以内 L3 — ADR-046 §E.1）→ クラスタ側は admission policy で **Cosign verify 必須**（未署名イメージの Pod 起動を拒否）。
3. **機能検証**: Staging で ①SPI 3 系統 Flow 配置の回帰（Browser forms / First Broker / Post Broker — PoC F-6 / K-6 lint 含む）②**1000 IdP 合成データセット回帰（ログイン p99 / Admin API p99、ベースライン比 +10% 以内）**③G-SPI-Compat 項目（RHBK × upstream SPI 互換）。
4. **カナリアデプロイ**: 本番は RHBK Operator ローリング（PDB maxUnavailable=1）を利用し、**1 Pod 目更新後に bake time 15 分**を置く。bake 中は §9.8 の synthetic ログインチェック（認証成功 + 該当 SPI パスの発火メトリクス）を毎分実行し、失敗で自動ロールバック（Git revert → ArgoCD 同期）。ユーザ影響ゼロ（Persistent user sessions が DB 保存のため、U8 D-U8-04）。

- **根拠**: ADR-046（L2〜L5）、U2 §2.4/2.8、U8 D-U8-04、PoC V3''（SPI 3 系統配置）。
- **未決**: Renovate の RHBK イメージ追従ルール（ADR-046 §C.4 の `keycloak` パッケージルールを RHBK タグ体系に合わせ調整）。

### 9.6.3 決定 D-U9-14: Keycloak バージョン固定 + 昇格前検証（P-16 対策 1 の CI 化）

**採用**: U2 §2.7.1 の制約を CI プロセスとして固定する:

| 項目 | 決定 |
|---|---|
| 版数固定 | RHBK 26.x 系固定（P-01）。イメージは**タグでなく digest 指定**（東西 ECR digest 一致を日次検証、U8） |
| OLM | Subscription = **Explicit Strategy（手動承認）**、IaC 固定（K-11） |
| 昇格ゲート | **パッチ含む全昇格**が Staging 1000 IdP 合成データセット回帰（PoC P-1 投入スクリプト = §9.5.2 適用エンジンの恒久資産）を通過してから本番へ。26.5.4 O(N²) リグレッション #46605 前例のためパッチも例外にしない |
| 追従カレンダー | RHBK 年 1-2 回リリースの動作確認をカレンダー化（ADR-055 §A.7 Phase 3）。SPI 互換確認 → 必要修正 → §9.6.2 の順で流す |
| リグレッション検知手順 | PoC P-7（26.x → 26.x+1 を 1000 IdP データセットで実施）で確立した手順を RB-PLT-02 に収録 |

- **根拠**: U2 §2.7.1（P-16 必須対策 1）、ADR-055 §A.7、U8 D-U8-04。

---

## 9.7 IdP オンボーディングパイプライン（3 レイヤー方式の実装形）

### 9.7.1 決定 D-U9-15: パイプライン 6 ステップとリードタイム内訳

**採用**: §FR-2.3.2 の 3 レイヤー（L1 顧客 IdP 側作業 / L2 基盤側作業 / L3 エンドユーザー体験）のうち、**L2 を次の 6 ステップの半自動パイプラインとして実装**する。実行主体はオンボーディング API（§9.5.2）+ 承認 UI（ユーザ管理画面 Backend と基盤共用、ADR-038 / U10）:

| # | ステップ | 内容 | 自動化 | 所要（目標） |
|---|---|---|---|---|
| 1 | 申請 | テナント宣言ファイル（`tenants/<id>/idp.yaml`）の PR。顧客 Metadata（SAML XML / OIDC discovery URL）・ドメイン・HRD ヒントキーを含む | テンプレート生成 | — （顧客準備に依存） |
| 2 | 検証 | 機械検査: Metadata 妥当性 / alias 規約 / **K-8（hideOnLoginPage・Org 紐付け）** / K-7（secret 直書き）/ ドメイン重複（HRD 衝突）。+ 基盤運用 1 名レビュー（NFR-6.4 B 種別） | lint 全自動 + 人 1 名 | 〜2h |
| 3 | **Egress FQDN 更新（REQ-OUT-01）** | 顧客 IdP の token / JWKS / userinfo エンドポイント FQDN を他組織 Network Firewall の許可リストへ反映。**形態は G-EGRESS 合意に依存**: ②専用ルールグループ + ③更新委任なら**パイプラインから自動反映（分オーダー）** / ①都度申請フォールバックなら**先方 SLA ≤ 4 営業時間**（U6 D-U6-13）。**Webhook 配信先（顧客アプリ endpoint）の FQDN も同プロセスで扱う**（U10 §10.3、RB-TEN-07） | ②③なら自動 | ②③: 〜10 分 / ①: ≤ 4 営業時間 |
| 4 | IdP + Org 作成 | 適用エンジンが Admin API で Org 作成 → IdP 作成（テンプレート Mapper 5-6 個、per-Mapper syncMode=IMPORT〔mfa_indicator のみ FORCE override、U2 §2.5.4〕）→ Org-IdP リンク → HRD ヒント登録 | 全自動 | 〜10 分 |
| 5 | 疎通確認 | ①メタデータ解決・JWKS 取得（ステップ 3 の実効確認 = G-EGRESS 受入試験と同型、U6 §6.7.4）②テストログイン（顧客テスト ID での first-broker-login、L1 完了が前提）③JIT 属性書込確認 | ① 自動 / ②③ 顧客と合同 | ①〜5 分 / ②③ 顧客都合 |
| 6 | 監視登録 | Per-tenant メトリクス系列の有効化 / SCIM Health Check 閾値登録（SCIM 顧客のみ）/ **IdP スケールダッシュボードのバッチ前後スナップショット確認（§9.1.2）** / RB-TEN-01 クローズ | 自動 | 〜5 分 |

**リードタイム < 1 営業日（§NFR-3 / NFR-6.5 A-1）の成立条件**: 基盤側純作業は ②③ 形態なら**合計 2-3 時間**で余裕をもって成立。①形態でも 4 営業時間 SLA が守られれば 1 営業日内に収まるが、余裕はない。**G-EGRESS が①のまま SLA ≥ 1 営業日となった場合は成立しない** — その場合は §NFR-3 のリードタイム改訂（緩和）を U1 経由でエスカレーションする（U6 §6.7.3 のフォールバック条件を本書が運用面から確認。「SLA 未合意のまま Phase 1 契約禁止」= G-EGRESS ゲートの趣旨）。

- **補足 1**: リードタイムの計測起点は「ステップ 1 PR 受付」、終点は「ステップ 5① 完了」（②③ は顧客都合のため SLA 外と契約で明記 — L1/L3 レイヤーは顧客側作業）。
- **補足 2**: 大量一括（+100 社バッチ）の場合はステップ 3 を事前一括申請し、ステップ 4 をバッチ実行 + P-5（他テナント波及なし）の監視確認を挟む。
- **根拠**: §FR-2.3.2.A、U2 §2.7.5（パイプライン = P-1 投入スクリプトの恒久資産）、U6 §6.7.3 / D-U6-13、U2 §2.8.2（G-EGRESS 行）。

---

## 9.8 Central Canary（ADR-059 の Phase 1 実装範囲）

### 9.8.1 決定 D-U9-16: 配置変更（P-18 対応）と Phase 1 スコープ

**採用**: ADR-059 は Central Canary / App Registry を「ネットワーク監査 Acct」（ADR-039 v2 = 自管理前提）に置くが、**P-18 により同 Acct は他組織管理となったため成立しない**。Phase 1 は次で配置・範囲を確定する:

| 項目 | 決定 |
|---|---|
| 配置 | **弊社監査 Acct**（§9.5.1 `audit-infra` state。App Registry DynamoDB / OpenAPI Registry S3 / Canary / Alert Router / Secrets Manager `canary/central/*` を同居）。ADR-059 の Cross-Acct 要件 2 種（Registry / OpenAPI 書込）は宛先 Acct を読み替えるのみで方式不変 |
| 運用主体 | ADR-059 の「Network 監査チーム」は他組織となったため**弊社基盤運用（SRE）へ変更** |
| App Registry スキーマ | ADR-059 §B.1 を踏襲: `appId` / `baseUrl` / `authPattern` / `openApiS3Key` / `testTokenSecret` / `networkClass` / `alertRouting`（critical=security-oncall / warn=platform / info=app-team）/ `vpcConfig`。authPattern 7 値（`api-gw-jwt` 〜 `internal-alb-jwt`、§B.2）も踏襲。登録は Service Catalog 起動時の Custom Resource 自動登録（§B.3） |
| Phase 1 検知範囲 | **認証実装漏れ検知の Hybrid 検証**: Positive（`canary-central-readonly` Client の正当トークンで 200）+ Negative（**無トークン / 改ざんトークンで 401/403 が返ること** = 認証チェック欠落の直接検知）。対象 = App Registry 登録済み全アプリの代表エンドポイント（OpenAPI Registry から自動抽出）。Monolith（`alb-cookie-monolith`）と Private API（Canary VPC + TGW、ADR-059 §D/§E）は**対応アプリが Phase 1 に現れた時点で有効化** |
| 兼用 | ①§9.2 SLO の外形計測（CloudFront 経由 / Internal 直の 2 系統で切り分け）②§9.6.2 カナリアデプロイの bake 判定 ③大阪側外形監視（U8） — synthetic 送信元は ITDR allowlist へ登録（U7 §7.2.3、IaC 管理 + 四半期棚卸し） |
| Runtime / Region | `syn-nodejs-puppeteer` 系最新（ADR-059 §H 準拠で実装時に最新版へ更新）。Phase 1 = ap-northeast-1 単一、**Phase 2 で大阪 replica**（Multilocation、ADR-059 §I） |
| Alert Router | 4×4 真偽値表分類（ADR-059 §K）に基づき SNS → PagerDuty / Slack 振り分け。§9.2 の Severity 体系と統合 |

- **根拠**: ADR-059 Decision（Pattern β の構成要素は維持、配置のみ P-18 で変更）、Baseline §1.2（弊社監査 Acct の存在）。
- **帰結**: **ADR-059 の改訂が必要**（配置 Acct・運用主体。§9.9.3 で改訂案として引き渡し）。
- **未決**: `canary-central-readonly` Client のスコープ設計（読取専用 audience の付与規約 — U5 §5.8 のスコープ規約に従い U10 実装時に確定）。

---

## 9.9 決定一覧・未決事項・他単元への引き渡し

### 9.9.1 決定一覧（サマリ）

| # | 決定 | 節 |
|---|---|---|
| D-U9-01 | OTel + AMP/AMG/X-Ray 確定、Collector = infra Pool（KC Pool toleration 付き DaemonSet 併用）、AMP は弊社監査 Acct 集約、大阪平時配備 | §9.1.1 |
| D-U9-02 | KC 計装 14 点 + **IdP 数の関数としての p99 監視**（ベースライン比 +10% 警戒）+ IdP スケールダッシュボード常設 | §9.1.2 |
| D-U9-03 | Cardinality 規約（user_id 等禁止）、Per-tenant 系列はログイン + SCIM 系に限定、Trace Sampling 正常 1% / エラー・Slow 100% | §9.1.3 |
| D-U9-04 | SLO 4 サービス（99.9/99.95/99.5/99.99）+ Burn Rate Alert（Fast 14.4× / Slow 6×）Phase 1 全設定 + エラーバジェット枯渇時の変更凍結ルール | §9.2.1 |
| D-U9-05 | ログ 3 層 = CW Hot 90 日 / OpenSearch Warm / S3 Object Lock 7 年（ADR-053 §F を U7 D-U7-13 で上書き）、全ソース scrubbing 通過後保存、週次監査スキャン Dashboard | §9.3.1 |
| D-U9-06 | SIEM 取込イベントセット確定（LOGIN 系 / TOKEN_EXCHANGE / **REVOKE_GRANT・LOGOUT 系** / USER_REACTIVATED / Admin Events 全量 / CloudTrail 6 Acct） | §9.3.2 |
| D-U9-07 | Runbook 体系 RB-TEN/APP/USR/SEC/PLT/DR/MIG/DSAR **全 35 冊**（TEN 7 / APP 3 / USR 5 / SEC 7 / PLT 5 / DR 6 / MIG 1 / DSAR 1）+ **Phase 1 前必須 13 冊**（TEN-01/03、SEC-01/02/04/05/06、DR-00〜05）の指定 | §9.4.1 |
| D-U9-08 | 禁則集 K-1〜K-11（realm export 禁止 / 全 Pod 同時再起動は Writer 安定後 / ITDR フラグは RB-DR-00 のみ 等）を CI lint・パイプライン reject で機械強制 | §9.4.2 |
| D-U9-09 | Terraform state = Acct × 層で 6+ 分割、テナント層は state を持たない、apply は CI（GitHub OIDC）のみ | §9.5.1 |
| D-U9-10 | テナント層エンジン = 自作オンボーディング API（Admin API 差分適用）、**keycloak-config-cli 不採用**（K-1 と原理衝突） | §9.5.2 |
| D-U9-11 | 日次ドリフト検知 CI（基盤層 plan + テナント層 Admin API 突合、K-8 検査含む）+ ドリフト時の正当/不正分岐フロー | §9.5.3 |
| D-U9-12 | CI = GitHub Actions + OIDC / CD = OpenShift GitOps（ArgoCD）/ Registry = **ECR**（Quay・Tekton 不採用）/ Secret = ESO | §9.6.1 |
| D-U9-13 | SPI = 単一カスタムイメージ出荷、Trivy + Cosign + SBOM + SLSA L2→L3、カナリア = 1 Pod bake 15 分 + synthetic 判定 + 自動ロールバック | §9.6.2 |
| D-U9-14 | KC 昇格 = digest 固定 + OLM Explicit + **パッチ含め Staging 1000 IdP 回帰必須**（P-16 対策 1 の CI 化） | §9.6.3 |
| D-U9-15 | IdP オンボーディング 6 ステップ（検証 → **REQ-OUT-01 FQDN 更新** → 作成 → 疎通 → 監視登録）、リードタイム < 1 営業日は G-EGRESS ②③ 形態で成立（① SLA ≥ 1 営業日なら NFR 改訂エスカレーション） | §9.7.1 |
| D-U9-16 | Central Canary は**弊社監査 Acct へ配置変更**（P-18 帰結、ADR-059 要改訂）、Phase 1 = Hybrid 検証（Positive + Negative 401/403）+ SLO 外形・デプロイ bake 兼用 | §9.8.1 |

### 9.9.2 未決事項（オープン項目）

| # | 項目 | 内容 | 期限 / ゲート |
|---|---|---|---|
| O-U9-1 | **G-EGRESS 合意形態** | ②③（委任）vs ①（都度申請 SLA ≤ 4 営業時間）。§9.7 のステップ 3 実装と NFR-3 リードタイムの成立性が分岐 | Phase 1 契約前（U6 O-2 と同一） |
| O-U9-2 | infra Pool サイジング | Prometheus カーディナリティ + Aggregator マスキング量の実測（U6 O-11 合同） | G-IdP-Scale 実施時 |
| O-U9-3 | OpenSearch サイジング / Warm 保持最終値 | ログ量実測後（U7 未決の継承）+ B-OBS-1（保存期間ヒアリング） | Phase 1 実装時 |
| O-U9-4 | SCIM Facade 実行形態 | ROSA 常駐 vs Lambda + API GW（U6 O-9 / U3-OP-3、三者合同） | Phase 1 実装前 |
| O-U9-5 | SPI 内 Micrometer 計装の RHBK 互換 | G-SPI-Compat への検証項目追加（U2 へ依頼） | G-SPI-Compat |
| O-U9-6 | アラート Routing 実体 | PagerDuty 契約 / オンコールローテーション体制（NFR-6.3 の 24/7 要否ヒアリング連動） | Phase 1 実装前 |
| O-U9-7 | B-OBS-2/3/4/5 | ダッシュボード共有範囲 / APM 最終確認 / SLO 公開 / SLA 連動 | ヒアリング |
| O-U9-8 | テナント一括 logout ジョブ / 90 日 enabled=false バッチの実行基盤 | CronJob（infra Pool）実装詳細（U3 D3-09 / U5 §5.9.2 の実行面） | Phase 1 実装時 |
| O-U9-9 | 文書整合更新の残タスク | ADR-040 OOS 残存注記（§FR-8.6 / §NFR-4.7）の参照整理（U7 §7.9.3 から引き受け。**ADR-040/036 は別スレッド改訂中のため本書からは書込まず、完了後に実施**） | 別スレッド完了後 |

### 9.9.3 他単元・ADR への引き渡し

**U2 へ**: SPI 内 Micrometer 計装（§9.1.2 #2）と Flow 定義 lint（K-6）の仕様化。G-SPI-Compat への検証項目追加（O-U9-5）。

**U10 へ**: オンボーディング承認 UI（ADR-038 Backend 共用、§9.7 ステップ 2）/ `canary-central-readonly` Client のスコープ設計（§9.8 未決）/ アプリ向け Runbook 公開範囲（RB-APP 系）/ Webhook 通知（IdP 追加完了・メンテ通知）の要否。

**U1（Baseline）へ**: G-EGRESS ゲートの合否基準に「① 形態の場合 SLA ≤ 4 営業時間、未達なら §NFR-3 リードタイム改訂」を明記 — **U1 §1.5 G-EGRESS 行へ更新済み**（本書 §9.7 が運用面の裏付け）。

**ADR への反映（本書確定後、メイン統合レビューで実施）**:
- **ADR-053 改訂**: §A.2 Collector 配置（ECS Fargate → ROSA infra Pool）/ §F ログ階層（Hot 3 ヶ月 → CW 90 日、Cold 6 年 Glacier → S3 Object Lock Compliance 7 年、U7 D-U7-13 整合）/ §B SLO 表に本書 §9.2 参照追記 / Proposed → Accepted 昇格可。
- **ADR-059 改訂**: 配置 Acct（ネットワーク監査 Acct → 弊社監査 Acct、P-18 帰結）/ 運用主体（Network 監査チーム → 基盤 SRE）/ Runtime 版数の最新化（§H）。
- ADR-055 §A.6: 「Tekton / Quay」推奨行に対し本書 D-U9-12（GitHub Actions / ECR 確定）の参照注記。
- **ADR-051 改訂**: :15 / :94 / :305 の keycloak-config-cli 文言を「自作オンボーディング API による Admin API 差分適用」へ一本化（D-U9-10 帰結）。
- **ADR-060 改訂**: :341 実装ガイドの keycloak-config-cli 記述を除去（D-U9-10 帰結）。
- U8 §8.3.1: 経路 2 のテナント層再生を Admin API 差分適用へ一本化（**適用済み**、2026-07-24）。
- U2 §2.7.5: 「Admin API or keycloak-config-cli」の併記を Admin API に確定（**適用済み**、2026-07-24）。
- ※ ADR-040 / 036 は別スレッド改訂中のため**本書からの参照のみ**とし、両ファイルへの書き込みは行わない（U7 §7.9.3 と同運用）。

---

## 改訂履歴

- 2026-07-24: 初版（Wave 3 起草）。Baseline v1（P-01/P-04/P-15/P-16/P-17/P-18）準拠。可観測性（OTel/AMP/AMG/X-Ray + IdP 数関数監視、D-U9-01〜03）、SLO 定義書 + Burn Rate（D-U9-04）、ログ 3 層 + SIEM 取込セット（D-U9-05〜06）、Runbook 27 冊 + 禁則 K-1〜11（D-U9-07〜08）、IaC 2 層 + keycloak-config-cli 不採用 + ドリフト検知（D-U9-09〜11）、CI/CD（GitHub Actions/ArgoCD/ECR + SPI サプライチェーン + KC 昇格ゲート、D-U9-12〜14）、IdP オンボーディング 6 ステップ（D-U9-15）、Central Canary 弊社監査 Acct 配置変更（D-U9-16）を決定。
- 2026-07-24 (v1.1): Wave 3 最終レビュー反映 — **H-1**: D-U9-10（keycloak-config-cli 不採用）の波及 4 件を §9.9.3 に追加（ADR-051 :15/:94/:305 / ADR-060 :341 / U8 §8.3.1・U2 §2.7.5 は適用済み）。**H-2**: 主インプットに U4 §4.7.4 追加、§9.6.1 に Theme lint + axe-core CI 段追加、RB-TEN-01 に顧客オンボーディングガイド付属・RB-USR-03 に Recovery Codes 管理者リセットを明記。**H-3**: RB-TEN-06（SN オンボーディング）/ RB-TEN-07（Webhook 購読登録）/ RB-MIG-01 / RB-DSAR-01 / RB-SEC-07 の 5 冊追加 + RB-PLT-04 に SAML RSA 証明書ローテ（U10-OP-1）統合注記 + §9.7 ステップ 3 に Webhook 配信先 FQDN 同プロセス注記。**M-1**: D-U9-07 の冊数を実列挙から再計上（全 35 冊 / 必須 13 冊）。**M-2**: D-U9-13 の SPI 表記を「3 JAR・4 機能」へ修正（U2 §2.4 整合）。**M-9**: §9.6.1 に PII クレーム検査 CI（U5 §5.1.4 C-1〜C-7）追加。**M-11**: U1 向け G-EGRESS 記述を「更新済み」へ。**L-1**: U8 §8.2.3 → §8.5.2。**L-6**: §9.7 ステップ 4 に mfa_indicator FORCE override 注記（U2 §2.5.4）。
