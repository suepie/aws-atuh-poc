# ADR-058: 認証プラットフォーム 代替アーキテクチャ 6 パターン比較検討（現状構成の再確認）

- **ステータス**: **Accepted**（現状構成 = Keycloak Single Realm + Organizations 維持を再確認）
- **日付**: 2026-07-02
- **関連**:
  - [ADR-006 Cognito vs Keycloak コスト損益分岐](006-cognito-vs-keycloak-cost-breakeven.md)
  - [ADR-017 Realm 数の性能限界](017-realm-scalability-limit.md)（該当があれば）
  - [ADR-032 10M MAU CIAM プラットフォーム選定](032-ciam-cost-comparison-10m-mau.md)
  - [ADR-033 Keycloak 2-tier アーキテクチャ](033-keycloak-2tier-broker-idp-architecture.md)
  - [ADR-038 ユーザ管理画面（Tenant Admin Portal）](038-tenant-admin-portal.md)
  - [ADR-039 中央集約 Network + 5 アカウント体系 v2](039-centralized-network-account-edge-layer.md)
  - [ADR-051 Multi-Region DR / Failover](051-multi-region-dr-failover.md)
  - [ADR-054 ID 統合戦略](054-id-integration-strategy.md)
  - [ADR-055 HRD 実装方式選定](055-hrd-implementation-method-selection.md)
  - [ADR-056 ROSA 採用判断](056-rosa-adoption-decision.md)

---

## Context

### 背景

要件定義フェーズ後半（2026-06 末〜 2026-07 初）、53+ の ADR / SSOT（§C-7）で認証基盤全体構成の設計が進み、Phase 1 実装着手前の**判断妥当性の再検証**が必要となった。「現状構成が最適解か」「代替の可能性を体系的に確認したか」を、独立した検証プロセスで裏どりする。

### Why 本 ADR が必要

個別 ADR（ADR-032 プラットフォーム / ADR-033 2-tier / ADR-055 HRD 等）は**特定軸ごとの判断**を記録しているが、以下の観点で横断的な再検証が未実施だった:

1. **全 12 軸を横断した代替 6 パターンとの比較**が単一 doc に集約されていない
2. **業界の 2026 年時点のアップデート**（Keycloak v26 Organizations GA、Cognito 2024 リブランド、Auth0 Actions Node.js 化、Entra External ID GA、Ping/ForgeRock 統合後の SKU 整理）が個別 ADR に部分反映されているのみ
3. Phase 1 着手前の**戦略判断の最終ゲート**として、経営層 / 監査人向けの「代替を検討した証跡」が明示的に必要

本 ADR はプラットフォーム変更を決定する ADR ではなく、**「6 代替と比較検討した上で現状構成を維持する」という判断を明示的に記録する**ことが目的。

### 現状構成のサマリ（比較ベースライン）

以下 12 軸で現状の決定を要約:

| # | 軸 | 現状の決定 | 根拠 ADR |
|---|---|---|---|
| 1 | プラットフォーム | Keycloak OSS（RHBK は条件付き再評価）| ADR-032 |
| 2 | 実行基盤 | EKS Fargate + Aurora Serverless v2（ROSA は Phase 2 再評価）| ADR-056 |
| 3 | マルチテナント | **Single Realm + Organizations**（L2 論理分離、2-tier: Broker KC + IdP KC）| ADR-033 |
| 4 | HRD / 識別子 | **`<tenant>-<userid>` + 薄い SPI（~50-100 行 Java）+ Keycloak Organizations 内データ** | ADR-055, ADR-054 |
| 5 | フェデ / IdP 対応 | OIDC / SAML / LDAP、**Deep Broker**（Keycloak Broker + First Broker Login + User Storage SPI）| ADR-032 |
| 6 | Tenant Admin Portal | 別 SPA + 3 層認可（L1 本基盤 / L2 各アプリ）| ADR-038 |
| 7 | AWS アカウント | **5 アカウント体系 v2**（Network / ネットワーク監査 / 監査 / Auth / App × N）| ADR-039 |
| 8 | データプレーン | Aurora Multi-AZ + Infinispan、Multi-Region DR（Active-Passive Warm Standby）| ADR-051 |
| 9 | セキュリティ | Adaptive Auth + ITDR + Bot + PQC + Supply Chain + DSAR | ADR-034〜048 |
| 10 | ID 統合 / 移行 | 人事 DB SoT + User Storage SPI + 5 Phase 移行 | ADR-054 |
| 11 | 主要 SPI | HRD / Risk / Event Listener / User Storage / Authorization | ADR-055, ADR-034, ADR-037 |
| 12 | 規模・コスト | 10M MAU、**$122K/年**（平日）/ $182K/年（24/7）| ADR-032 |

---

## Decision

**現状構成（Keycloak OSS Single Realm + Organizations + 5 アカウント体系 + Deep Broker + `<tenant>-<userid>` + 薄い SPI）を維持する**。

**根拠**: 2 つの独立した調査エージェント（内部ドキュメント分析 + 外部業界調査）が全 12 軸で代替 6 パターンを評価した結果、以下 4 軸すべてで現状構成が優位であることが再確認された:

1. **コスト**: 現状 $122K/年 vs 代替 $1M-$10M/年 = **10-100 倍差**
2. **Java SPI 深度**: ADR-055 HRD SPI は Keycloak Organizations API と密結合、他プラットフォームで JS Lambda に書き直しコスト発生
3. **データ主権 (PCI DSS / APPI)**: SaaS 代替は etcd 相当データが外部ベンダに流入、5 アカウント体系との両立不可
4. **拡張性 (Deep Broker + 3 階層識別子)**: 顧客独自 ID / メール非保有 / 3 階層識別子を Broker 側で吸収する要件は Keycloak Custom SPI 以外で満たせない

---

## Consequences

### Positive（現状構成維持の利点）

- **判断の確信度向上**: 独立した 2 系統の調査で同結論、Phase 1 着手の説得材料が強化
- **経営層 / 監査人向け証跡**: 「代替 6 パターンを体系的に検討した記録」が本 ADR + 参照 reference doc に集約
- **将来の再評価トリガーが明確化**: SaaS CIAM の値下がり / 規制要件変化 / 顧客側 IdP 標準化 の 3 条件で本 ADR を再評価可能

### Negative（本比較検討自体のリスク）

- **リサーチ日時点情報の陳腐化**: 2026-07-02 時点の公式価格 / 機能状況に依存、SaaS ベンダの改定で数値が古くなる可能性
- **Ping/ForgeRock 統合後 SKU の流動性**: 2023 統合後のブランド整理が継続中、本 ADR 記載の SKU 構造が数四半期で変わる可能性
- **10M MAU 想定コストの見積精度**: Enterprise 契約は非公開が多く、業界事例ベースの推定値であることに留意

### Neutral

- **本 ADR は Alternatives Considered セクションが本体**（Decision は現状維持の再確認のみ）
- 個別 ADR（ADR-032/033/055 等）の変更は不要、本 ADR は横断的補強として機能
- Follow-up の FusionAuth Phase 2 候補追記は個別に判断（本 ADR では方向性のみ提示）

---

## Alternatives Considered（本 ADR の本体）

### 6 パターン適合度スコアマトリクス

各パターン、5 軸で ★1-5 評価:

| パターン | B2B SaaS | 認証集約 | 顧客 IdP フェデ | Custom SPI | PCI/APPI | 10M MAU 年額 | 総合 |
|---|:-:|:-:|:-:|:-:|:-:|---|:-:|
| **現状: Keycloak Single Realm + Organizations** | ★★★★★ | ★★★★★ | ★★★★ | ★★★★★ | ★★★★ | **$122K** | **★★★★★** |
| Auth0 B2B Organizations | ★★★★★ | ★★★★ | ★★★★★ | ★★ | ★★★ | $1M–$3M | ★★★ |
| Entra External ID | ★★★ | ★★★ | ★★★ | ★★ | ★★★★ | $1.5M–$3.6M | ★★★ |
| Cognito Multi-User-Pool | ★★★★ | ★★ | ★★★★ | ★★ | ★★★★★ | $1.8M–$2.4M | ★★½ |
| Cognito Single-Pool + Groups | ★★★ | ★★★★★ | ★★ | ★★ | ★★★ | $1.8M–$2.4M | ★★½ |
| Keycloak Multi-Realm | ★★ | ★★★★ | ★★★ | ★★★★★ | ★★★★ | ~$122K | ★★½ |
| FusionAuth | ★★★★ | ★★★★ | ★★★★ | ★★★ | ★★★ | $10-36K + 運用 | ★★★★ |
| Ping/ForgeRock | ★★★ | ★★★★★ | ★★★★★ | ★★★★★ | ★★★★★ | $1M–$10M+ | ★★★ |

### Alt 1: SaaS Auth0（Okta CIC）B2B Organizations パターン

- **概要**: Auth0 の Organizations 機能（1 Auth0 Tenant 内に複数 Organization、認証は Pool、ブランディング/接続は Silo = "Pool-with-Bridge"）
- **強み**: Self-Service Enterprise Configuration wizard は業界最高峰、SOC 2/PCI DSS/HIPAA/ISO 27001 認証済み SaaS、開発者体験（DX）が優秀、事例（Siemens/Mazda/Pfizer/AMD/IKEA/UPS/P&G/Vanguard）
- **決定的な弱点**:
  - 10M MAU で **$1M-$3M/年**（Keycloak の 10-30 倍）
  - Enterprise SSO Connection は MAU とは別課金で $5K-$34K/年/バンドル、100 顧客規模で **$200K-$400K/年別枠発生**
  - Auth0 Actions は Node.js のみ = ADR-055 HRD Custom Authenticator SPI（Java）を書き直し必要
  - Actions 制約: 100 KB/action、10 日ログ保持、外部 HTTP でレイテンシ +
  - Public Cloud データ主権が弱い、Japan 対応は Enterprise SKU
  - Rules/Hooks は 2026-11-18 廃止
- **不採用理由**: コスト過剰 + SPI 深度不足 + PCI DSS/APPI データ主権弱化

### Alt 2: Microsoft Entra External ID（2024 統合版）

- **概要**: Azure AD B2C + Azure AD B2B の統合版（2024 GA）、workforce tenant と external tenant を分離。CIAM successor to Azure AD B2C（B2C は 2025-05 新規停止、2026-03 Premium P2 退役）
- **強み**: Microsoft エコシステム親和性、Compliance depth（FedRAMP High/ISO 27001/SOC 2/PCI DSS）、Japan Go-Local（APPI 対応）、事例（NSK 等）
- **決定的な弱点**:
  - 10M MAU で **$0.03/MAU 基本 = $3.6M/年 list**、EA 交渉で $1.5-$2.5M/年
  - Premium add-on（Adaptive/Governance）は $0.75/MAU/月で更に上乗せ
  - **Custom Auth Extensions は 2 秒 REST timeout** = 重い HRD/リスクロジック不可
  - OIDC `domain_hint` が external tenant で機能しないバグ
  - B2C Custom Policies（IEF）は移行不可、再アーキ必要
  - SaaS-only、etcd 相当データ主権制御不可
- **不採用理由**: コスト + 拡張制約 + データ主権

### Alt 3: AWS Cognito Multi-User-Pool パターン（テナントごとに独立 Pool）

- **概要**: 1 テナント = 1 User Pool、完全 Silo。デフォルト 1,000 Pool/region 上限（Support Ticket で拡張可）
- **強み**: 完全なテナント blast-radius 隔離、per tenant ポリシー / MFA / IdP、AWS ネイティブ統合、PCI DSS/APPI 監査容易
- **決定的な弱点**:
  - **1,000 Pool/region ハードキャップ**（1,000 顧客超規模で詰む）
  - 運用スプロール: N pool = N Lambda / N IaC / N ダッシュボード、tenant onboarding 自動化が重い
  - 10M MAU で **$1.8M/年（Essentials）/ $2.4M/年（Plus）**
  - Lambda triggers のみ = ADR-055 Custom Authenticator SPI 相当不可
  - Organizations 概念なし、テナント階層自前実装
  - Cognito はデータモデルが user-centric、tenant-centric ではない（WorkOS Blog 明言）
- **不採用理由**: Pool 上限 + 運用工数爆発 + SPI 深度不足

### Alt 4: AWS Cognito Single Pool + Groups パターン（1 Pool 全テナント収容）

- **概要**: 1 Pool + custom:tenant_id 属性 + Group（10,000 group/pool 上限）で論理分離。App Client per tenant で IdP 切り分け
- **強み**: 単一 hosted UI / Lambda / dashboard、40M user/pool、Cognito 2024 next-gen infra（high-throughput / customer-managed KMS / multi-region replication preview）
- **決定的な弱点**:
  - **1,000 SAML/OIDC IdP/pool ハードキャップ**（大規模フェデ顧客対応不可）
  - **email 一意性制約**: 同一 email が別テナントで登録不可 → 合成 email や UUID で回避必須（本基盤の `<tenant>-<userid>` と同じ設計課題）
  - per tenant セキュリティポリシー分離不可（MFA 強度 / パスワード長を per tenant 化不可）→ 大口顧客の「うちだけ強化」要件対応不能
  - 10M MAU で **$1.8-$2.4M/年**（Multi-Pool と同一）
  - Noisy-neighbor: UserAuthentication 120 RPS quota が pool 全体
  - Custom Attributes 50 個 / 2048 bytes 上限
  - Lambda triggers のみ
- **不採用理由**: IdP 上限 + per tenant ポリシー分離不可 + 認可 claim-based のみ

### Alt 5: セルフホスト Keycloak Multi-Realm（Single Realm 選択の代替）

- **概要**: 1 テナント = 1 Realm。各 Realm は独立 issuer / 独自 IdP / 独自ユーザストア。ADR-033 選択の代替案として体系的に評価
- **強み**: ハード隔離（監査人に説明しやすい）、SPI 100% ポータブル（ADR-055 method A 動作）、Realm 単位ポリシー完全独立
- **決定的な弱点**:
  - **100-200 realm 超で指数的性能劣化**（GitHub #11074, forum: 3000 realms = 50-110s login latency）
  - Keycloak 26.4 で 1K+ realms までは改善（realms cache 増加必須）だが、10K+ 顧客は範囲外
  - 根本原因: N+1 composite-role 展開、JPA persistence-context bloat、admin-realm client-role explosion
  - **Keycloak プロジェクト自体が Organizations を投入した理由が "realm-per-tenant は 50/100/500 tenant でスケールしない"**（phasetwo, skycloak, Medium Keycloak blog）→ 公式が Organizations を B2B デフォルトに位置付け
  - HRD は DIY（Realm 間ネイティブサポートなし）
  - Ops 負荷がテナント数に線形、cross-realm policy 一括更新の bulk API なし
  - Admin console UX が 200 realm 超で degrade
  - Upgrade 複雑度: 5K realm × migration script = 長い downtime
- **不採用理由**: スケール限界 + Keycloak 公式が非推奨方向 + 運用負荷 → **本基盤の Single Realm + Organizations（ADR-033）が公式推奨と一致していることを再確認**

### Alt 6-A: セルフホスト FusionAuth（Enterprise 商用オルタナ）

- **概要**: FusionAuth Inc.（Colorado）、self-host または SaaS、PostgreSQL + Elasticsearch/OpenSearch backend
- **強み**:
  - **フラットレート料金**（MAU 無制限）: Enterprise $850-$2,970/mo = **$10-$36K/年 + セルフホストインフラ**
  - 大規模時のコスト予測容易
  - Tenants + Applications ネイティブ、multi-tenant primitive しっかり
  - JS Lambda 拡張（JWT populate / SAML v2 populate/reconcile / UserInfo / SCIM 等）が広範
  - SCIM Essentials+
- **決定的な弱点**:
  - **JS Lambdas のみ、Java SPI 不在** → ADR-055 HRD SPI（Java）を JS 書き直しコスト発生
  - コミュニティ / エコシステムが Keycloak より薄い
  - Advanced adaptive / risk 機能が Ping/ForgeRock より弱い
  - Orchestration DSL（journey/tree）なし、code+config
  - IGA 内蔵なし
  - PCI DSS Level 1 / APPI 実運用ケーススタディが Keycloak 比で少ない
  - B2B Starter プラン 100 entity 上限（本格 B2B は Enterprise 必須）
- **判定**: **次点候補として ADR-032 に追記価値あり**（RHBK 統合サブスクが割高になった場合の Phase 2 商用サポート代替候補）

### Alt 6-B: Ping Identity / ForgeRock（Enterprise 全部盛り）

- **概要**: Ping Identity（ForgeRock を 2023 吸収、ブランド統合）。PingOne / PingOne AIC / PingFederate / PingAM
- **強み**:
  - **技術適合度 5/5** across all dimensions
  - Auth Trees / Scripted Decision Nodes（JS/Groovy）+ Java plugin SDK
  - PingFederate は市場リーディングのフェデハブ
  - DaVinci low-code orchestration（100+ connector）
  - PingOne Protect（Adaptive/Risk/Fraud）
  - 規制産業実績（金融/通信/官公庁）豊富、KuppingerCole/Gartner Leader
- **決定的な弱点**:
  - **10M MAU で $1M-$10M+/年**（Keycloak の 50-500 倍）= 「低運用負荷・コスト」基本方針を毀損
  - PingFederate オンプレは $25-$40/authenticated user/年 → 10M で年 $250M+（CIAM 用途では PingOne 系一択）
  - 統合後 SKU 混乱（PingDirectory vs PingDS convergence）
  - Java skillset 重い、deploy 遅い
  - mid-market B2B SaaS には overkill
- **不採用理由**: コスト過剰、規制産業実績が必要な特殊要件がなければ選択理由なし

---

## 大きく違う構成の軸別比較

### 1. Regional 戦略

| 選択肢 | 内容 | 本基盤採用 |
|---|---|---|
| Single-Region + AWS Backup のみ | RTO 4-8h、コスト -50% | ❌ 弱すぎる |
| **Single-Region Active-Passive Warm Standby** | Aurora Global + KMS MRK + S3 CRR、Tier1 RTO 30min / RPO 1min | **✅ 採用（ADR-051）** |
| Multi-Region Active-Active | Global Accelerator + Aurora Global Write Forward、コスト +100% | ❌ Identity 領域では PII データ主権制約（GDPR/APPI）が阻害要因 |

**業界標準**: Identity 領域では Active-Passive が業界標準。SaaS CIAM（Auth0/Entra）でも Multi-Region は Enterprise 契約制約多。

### 2. アカウント境界

| 選択肢 | 内容 | 本基盤採用 |
|---|---|---|
| Single AWS Account | PoC / 開発初期のみ | ❌ Blast radius 過大、SoD 不成立 |
| 3 Account（Auth / App / Audit） | 業界最小構成 | ❌ ネットワーク監査分離弱 |
| **5 Account 体系 v2** | Network / ネットワーク監査 / 監査 / Auth / App × N、年 +$36K | **✅ 採用（ADR-039 v2）** |
| 7-10 Account 細分化 | DMZ / IdP / Broker / Data 更に分離 | ❌ 運用複雑化 |
| SaaS 委譲 | Cognito / Auth0 側で完結 | ❌ etcd 相当データ主権失う |

### 3. Broker 深度

| 選択肢 | 内容 | 本基盤採用 |
|---|---|---|
| No Broker | 全 SaaS 化、アプリが直接顧客 IdP と OIDC/SAML | ❌ 認証集約放棄 |
| Shallow Broker | メタデータのみ pass-through | ❌ 属性正規化不可 |
| **Deep Broker** | Keycloak Broker + First Broker Login Flow + User Storage SPI、独自 issuer 再署名 | **✅ 採用**（ADR-055 の HRD SPI は Deep Broker 前提だから成立） |

**業界事例**: Auth0 も Deep Broker（`provider\|external_id` 形式で自動発行）、Ping DaVinci Trees も同系。本基盤は Deep Broker が必然。

### 4. 識別子戦略

| 選択肢 | 内容 | 本基盤採用 |
|---|---|---|
| 合成 Email（`u001234@acme.basis.example.com`）| Cognito Single Pool email 一意制約回避で頻用 | ❌ Q5 メアド UX 二重化リスク |
| **ハイフン区切り `<tenant>-<userid>`** | 人間可読、Organization alias と 1 対 1、Keycloak Custom SPI で吸収 | **✅ 採用（ADR-055 Phase 1 確定）** |
| UUID + Alias | sub=UUID + preferred_username=Alias、Cognito 推奨 | △ 現状 Layer A で採用（sub=UUID）だが Layer B（外部露出）にハイフン区切り採用 |
| URL 分離（`acme.basis.example.com`）| 大口顧客専用、Slack/Figma パターン | △ Phase 2 候補（大口ブランディング向け） |

---

## Follow-up

### 短期（Phase 1 開始前）

なし。本 ADR は現状構成の維持を再確認するもので、実装への影響なし。

### 中期（Phase 1 完了時 / Phase 2 検討時）

1. **FusionAuth を ADR-032 Alternatives Considered に追記**（Phase 2 の商用サポート代替候補として）
   - フラットレート料金の予測性と Keycloak OSS + RHBK の TCO 比較を年 1 回レビュー
   - RHBK 統合サブスクが割高になった場合の代替として文書化

2. **Auth0 Self-Service Enterprise Config パターンを ADR-038 Phase 2 で参考実装検討**
   - Tenant Admin Portal Phase 2 に「顧客 IT 管理者のセルフサービス SSO 設定 wizard」機能追加を評価

3. **Entra External ID の 2 秒 REST timeout を教訓化**
   - 本基盤 Custom SPI に「同期実行のパフォーマンス予算」を SLA として明文化（Adaptive Auth 遅延監視）

### 長期（本 ADR の再評価トリガー）

以下 3 条件のいずれか発生時に本 ADR を再評価:

| 再評価トリガー | 具体的な条件 |
|---|---|
| **SaaS CIAM の値下がり** | Auth0 / Entra External ID / Cognito のいずれかが 10M MAU で $500K/年以下に |
| **規制要件変化** | FIPS 140-2 / HIPAA / FedRAMP / ISMAP-Hi が顧客要件として発生（ADR-056 ROSA 再評価と連動） |
| **顧客側 IdP 標準化** | 顧客企業側で OIDC 標準化が進み、Deep Broker の必要性が薄れた場合 |

### 記録の更新頻度

- **年 1 回定期レビュー**（本 ADR の 6 代替パターン価格 / 機能アップデートを反映）
- **重大事象発生時**（プラットフォームベンダの M&A / SKU 変更 / 大規模事例発表）

---

## Notes

### 本 ADR と関連 ADR の整理

| ADR | 焦点 |
|---|---|
| ADR-006 | Cognito vs Keycloak コスト損益分岐（17.5 万 MAU） |
| ADR-032 | 10M MAU CIAM プラットフォーム選定（Keycloak OSS 確定）|
| ADR-033 | Keycloak 2-tier アーキテクチャ（Broker + IdP 物理分離）|
| ADR-055 | HRD 実装方式選定（薄い SPI + Organizations）|
| ADR-056 | ROSA 採用判断（Default 不採用）|
| **本 ADR-058** | **上記個別 ADR を統合した横断的比較検討 + 現状構成再確認** |

### 調査方法（本 ADR の裏どり）

本 ADR の結論は、以下 2 系統の独立した調査プロセスで裏どり:

1. **内部ドキュメント分析**（Agent 1）: §C-7 実装アーキテクチャ + 53+ ADR + MEMORY.md を横断読解し、現状構成の 12 軸サマリを生成
2. **外部業界調査**（Agent 2 + サブエージェント）: WebSearch/WebFetch で 6 代替パターンの公式ドキュメント / 業界事例 / 価格公開情報を収集、独立して適合度スコアリング

両調査は独立実行し、結論一致を確認済。

### 主要引用ソース

- [Keycloak Discussion #11074 - Realm scalability](https://github.com/keycloak/keycloak/discussions/11074)
- [phasetwo.io - Multi-tenancy Options in Keycloak](https://phasetwo.io/blog/multi-tenancy-options-keycloak/)
- [Skycloak - Multitenancy in Keycloak Using the Organizations Feature](https://skycloak.io/blog/multitenancy-in-keycloak-using-the-organizations-feature/)
- [Medium Keycloak Blog - Exploring Keycloak 26 Organizations](https://medium.com/keycloak/exploring-keycloak-26-introducing-the-organization-feature-for-multi-tenancy-fb5ebaaf8fe4)
- [AWS Cognito Pricing](https://aws.amazon.com/cognito/pricing/)
- [AWS Cognito Multi-tenancy Best Practices](https://docs.aws.amazon.com/cognito/latest/developerguide/bp_user-pool-based-multi-tenancy.html)
- [Beyond the 1,000 User Pool Limit in Cognito](https://dev.to/ameer-pk/architecting-multi-tenant-saas-beyond-the-1000-user-pool-limit-in-amazon-cognito-2le3)
- [Auth0 B2B SaaS Landing](https://auth0.com/b2b-saas)
- [Auth0 Organizations Overview](https://auth0.com/docs/manage-users/organizations/organizations-overview)
- [Auth0 Actions Limitations](https://auth0.com/docs/customize/actions/limitations)
- [SSOJet - Auth0 Growth Penalty](https://ssojet.com/blog/auth0-pricing-growth-penalty)
- [Microsoft Entra External ID Pricing](https://learn.microsoft.com/en-us/entra/external-id/external-identities-pricing)
- [Entra Custom Auth Extensions](https://learn.microsoft.com/en-us/entra/external-id/customers/concept-custom-extensions)
- [Entra Direct Federation Domain Hint](https://learn.microsoft.com/en-us/entra/external-id/direct-federation)
- [FusionAuth Pricing](https://fusionauth.io/pricing)
- [FusionAuth Lambdas Docs](https://fusionauth.io/docs/extend/code/lambdas/)
- [Ping Identity Pricing (CheckThat.ai)](https://checkthat.ai/brands/ping-identity/pricing)
- [Ping/ForgeRock Vendor Benchmark](https://vendorbenchmark.com/vendors/ping-identity-pricing)
- [PingOne DaVinci](https://www.pingidentity.com/en/product/pingone-davinci.html)
- [WorkOS - 5 Best Cognito Alternatives for B2B SaaS](https://workos.com/blog/aws-cognito-alternatives)
- [Scalekit - AWS Cognito for B2B SaaS](https://www.scalekit.com/blog/aws-cognito-b2b-saas)
- [AWS Well-Architected SaaS Lens: Silo/Pool/Bridge](https://docs.aws.amazon.com/wellarchitected/latest/saas-lens/silo-pool-and-bridge-models.html)

---

## 改訂履歴

- 2026-07-02: 初版作成。要件定義フェーズ後半、Phase 1 着手前の判断妥当性再検証として、6 代替パターン（Auth0 / Entra External ID / Cognito Multi-Pool / Cognito Single-Pool / Keycloak Multi-Realm / FusionAuth・Ping/ForgeRock）を体系的に比較。2 系統の独立調査（内部 doc + 外部業界）で現状構成（Keycloak Single Realm + Organizations）の維持を再確認。Follow-up として FusionAuth を Phase 2 商用サポート代替候補として ADR-032 に追記提案。
