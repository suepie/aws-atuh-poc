# 認証基盤 drawio 詳細図

> **作成日**: 2026-06-25
> **最終更新**: 2026-06-25（overview を §C-7.3 全 29 セクション中間粒度反映に拡張、案 2）
> **対象**: 要件定義フェーズ確定済の本番想定構成（ADR-001〜056 反映、5 アカウント体系 v2 + 認可 C ハイブリッド案 + HRD Custom SPI Phase 1 採用）
> **元情報**: [§C-7 実装アーキテクチャ](../../requirements/proposal/common/07-implementation-architecture.md)

---

## 0. 本ディレクトリの目的

§C-7 architecture.md の Mermaid 図を **drawio (diagrams.net)** で開ける詳細図に変換、AWS Architecture Icons を用いた本番想定図を提供。

### 0.1 ファイル一覧

| ファイル | 内容 | レベル |
|---|---|---|
| `README.md`（本ファイル）| 作図仕様書 + ノード一覧 + 配置方針 + §C-7.3 反映マトリクス | — |
| `architecture-v2-overview.drawio` | **5 アカウント体系全体俯瞰**（5 Swim Lane + §C-7.3 全 29 セクション中間粒度反映、〜100 ノード）| 概要 |
| `architecture-v2-network-detail.drawio` | **ネットワーク監査 Acct 詳細**（アプリごと独立 CloudFront/WAF）| 詳細 |

### 0.2 §C-7.3 全 29 セクション 反映状況（2026-06-25 案 2 拡張）

凡例：✅ overview に反映済 / 📝 overview に注記のみ / 🔲 別図 or Mermaid のまま / — N/A

| § | セクション名 | overview 反映 | 反映先 Lane / ノード |
|---|---|:---:|---|
| C-7.3.1 | 外部アクター（P-1〜P-4 + I-1〜I-5 + M-1〜M-5）| ✅ | 外部アクター Lane（end_user / tenant_admin / op_user / mobile_user / i_actors / m_actors）|
| C-7.3.2 | AWS アカウント境界 5 体系 | ✅ | 全 5 Lane（auth_lane / net_lane / netaudit_lane / audit_lane / app_lane）|
| C-7.3.3 | Network 層（TGW / DX / VPN / VPC）| ✅ | ネットワーク Lane（tgw / dx / vpn + vpc_note）|
| C-7.3.4 | Broker Keycloak（Realm / Auth Flow / Custom SPI 群 / Mapper）| ✅ | Auth Lane broker_kc_box + spi_box（hrd_spi / risk_spi / event_listener_spi / user_storage_spi）|
| C-7.3.5 | IdP Keycloak（Tier 2、ローカルユーザー保管）| ✅ | Auth Lane idp_kc + aurora_idp |
| C-7.3.6 | 顧客 IdP フェデレーション | ✅ | customer_idp ノード + 接続線 e8 |
| C-7.3.7 | 外部 SP 連携（ServiceNow、ADR-023）| ✅ | sn_sp_box + external_sp + e15 |
| C-7.3.8 | UI レイヤー 5 種 SPA | ✅ | spa_box（spa_kc_theme / spa_account / spa_launchpad / spa_admin / spa_sorry）|
| C-7.3.9 | プロビジョニング（SCIM）| ✅ | admin_box の scim ノード + e9 |
| C-7.3.10 | セキュリティ・検知層（ITDR + Adaptive Auth）| ✅ | security_box（itdr / adaptive_auth / ddb_itdr / eventbridge）|
| C-7.3.11 | Sorry / エラー画面（Lambda@Edge）| ✅ | netaudit Lane le_auth + spa_sorry |
| C-7.3.12 | 監査基盤（Org Trail / S3 / SecHub / GuardDuty / OpenSearch / SIEM）| ✅ | 監査 Lane（org / cloudtrail / audit_s3 / opensearch / security_hub / guardduty / siem_export / iam_ic）|
| C-7.3.13 | ユーザ管理画面 Backend（認可 C ハイブリッド）| ✅ | admin_box（admin_apigw / admin_lambda / lambda_authorizer / ddb_admin）|
| C-7.3.14 | 移行層（User Storage SPI、旧 DB 並走）| ✅ | legacy_sys + user_storage_spi + e16 |
| C-7.3.15 | PAM（Out of Scope、ADR-040）| 📝 | audit_note 内に注記（"PAM Out of Scope"）|
| C-7.3.16 | Workload Identity（EKS Pod Identity + KC FedID）| ✅ | other_auth_box（pod_identity / kc_fedid）|
| C-7.3.17 | Bot Detection（WAF Bot Control + ATP）| ✅ | waf_auth ノードに注記 + turnstile_note（Phase 2 オプション）|
| C-7.3.18 | Accessibility（WCAG 2.2 AA、ADR-043）| 📝 | phase2_notes に集約注記 |
| C-7.3.19 | Tabletop Exercise（ADR-044）| 📝 | game_day + phase2_notes |
| C-7.3.20 | 鍵管理 3 階層（L1/L2/L3 KMS CMK + ES256）| ✅ | kms_box（kms_l1 / kms_l2 / kms_l3）|
| C-7.3.21 | Supply Chain Security（SBOM / Cosign / Renovate）| ✅ | other_auth_box の cicd_pipeline + ecr_quay |
| C-7.3.22 | PQC マイグレーション（ADR-047）| 📝 | phase2_notes に集約注記（2026-2035）|
| C-7.3.23 | DSAR Backend（Step Functions + Export 5 形式）| ✅ | dsar_box（dsar_apigw / dsar_lambda / step_func / dsar_export_lambda / dsar_ddb / dsar_s3）|
| C-7.3.24 | Vendor Risk Management（TPRM）| 📝 | phase2_notes に集約注記 |
| C-7.3.25 | モバイル認証（ADR-050、AppAuth + PKCE）| ✅ | netaudit Lane の cf_mobile / waf_mobile + mobile_user actor + mobile_note_audit |
| C-7.3.26 | Multi-Region DR（Active-Passive Warm Standby）| ✅ | dr_region_note + dr_note_audit |
| C-7.3.27 | Multi-tenant Isolation + Rate Limit | ✅ | rate_limit + rate_limit_note（縮小スコープ：認証 API のみ）|
| C-7.3.28 | Observability（OTel + AMP + AMG + X-Ray）| ✅ | other_auth_box（otel / amp / amg / xray）|
| C-7.3.29 | ID 統合構成（人事 DB SoT + マッピング DB）| ✅ | hr_db actor + admin_box の id_mapping_note + scim + e9 |

**反映率**: 29 セクション中 ✅ 24 + 📝 5 = **100% カバレッジ**（直接ノード or 注記）
**ノード数**: 約 80 ノード + 約 25 注記 / Lane / グループ（合計約 105 要素）
**意図的なシーケンス図化対象外**: §C-7.4 認証フロー（HRD / MFA / OBO / トークン交換）は Mermaid シーケンス図のまま維持（drawio は構成図に特化）

### 0.3 drawio で開く方法

| 方法 | URL |
|---|---|
| **オンライン版**（推奨）| https://app.diagrams.net/ |
| **VS Code 拡張** | [Draw.io Integration](https://marketplace.visualstudio.com/items?itemName=hediet.vscode-drawio) |
| **デスクトップ版** | https://github.com/jgraph/drawio-desktop/releases |

VS Code 拡張インストール後、`.drawio` ファイルをダブルクリックで GUI 編集可能。

---

## 1. 5 アカウント体系（v2、2026-06-24 確定）

| アカウント | アイコン色 | 担当 |
|---|:---:|---|
| 🔷 **ネットワーク Acct** | 青（`#cfe8ff`）| Network チーム |
| 🟣 **ネットワーク監査 Acct**（NEW）| オレンジ（`#fff3e0`）| Network 監査 / Security チーム |
| 🔵 **監査 Acct** | 薄青（`#e3f2fd`）| Compliance チーム |
| 🟠 **Auth Platform Acct** | ピンク（`#fce4ec`）| 認証基盤チーム |
| 🟢 **App Acct（複数）** | 緑（`#e8f5e9`）| 各アプリチーム |

---

## 2. 主要コンポーネント一覧（drawio AWS4 shape 指定）

### 2.1 ネットワーク Acct（🔷）

| ノード | drawio shape | 配置目安 |
|---|---|---|
| Transit Gateway | `shape=mxgraph.aws4.transit_gateway` | 中央 |
| VPC Peering | `shape=mxgraph.aws4.vpc` | 周辺 |
| Direct Connect | `shape=mxgraph.aws4.direct_connect` | 端 |
| Site-to-Site VPN | `shape=mxgraph.aws4.vpn_connection` | 端 |

### 2.2 ネットワーク監査 Acct（🟣）

| ノード | drawio shape | 数 | 配置目安 |
|---|---|---|---|
| CloudFront-Auth | `shape=mxgraph.aws4.cloudfront` | 1 | 上段 |
| WAF-Auth | `shape=mxgraph.aws4.waf` | 1 | CloudFront-Auth と並列 |
| Lambda@Edge-Auth | `shape=mxgraph.aws4.lambda` | 1 | CloudFront-Auth 付近 |
| CloudFront-Admin（ユーザ管理画面）| `shape=mxgraph.aws4.cloudfront` | 1 | 上段 |
| WAF-Admin | `shape=mxgraph.aws4.waf` | 1 | CloudFront-Admin と並列 |
| CloudFront-AppA, B, C, ... | `shape=mxgraph.aws4.cloudfront` | N | 下段（アプリ数分）|
| WAF-AppA, B, C, ... | `shape=mxgraph.aws4.waf` | N | 各 CloudFront と並列 |
| Lambda@Edge-AppA, B, C, ... | `shape=mxgraph.aws4.lambda` | N | 各 CloudFront 付近 |
| Network Firewall | `shape=mxgraph.aws4.network_firewall` | 1 | 別エリア |
| Shield Advanced | `shape=mxgraph.aws4.shield` | 1 | 全 CloudFront を囲む形 |
| ACM（CloudFront 用） | `shape=mxgraph.aws4.certificate_manager` | 1 | 上端 |

### 2.3 監査 Acct（🔵）

| ノード | drawio shape | 配置目安 |
|---|---|---|
| AWS Organizations | `shape=mxgraph.aws4.organizations` | 中央 |
| CloudTrail Organization Trail | `shape=mxgraph.aws4.cloudtrail` | 中央 |
| 監査ログ集約 S3（Object Lock 7 年） | `shape=mxgraph.aws4.s3` | 下段 |
| Security Hub | `shape=mxgraph.aws4.security_hub` | 周辺 |
| GuardDuty | `shape=mxgraph.aws4.guardduty` | 周辺 |
| OpenSearch（ADR-035 ITDR）| `shape=mxgraph.aws4.opensearch_service` | 下段 |

### 2.4 Auth Platform Acct（🟠、案 2 拡張版）

| ノード | drawio shape | 数 | 配置目安 | §C-7.3 |
|---|---|---|---|---|
| Broker Keycloak（EKS Pod）| `shape=mxgraph.aws4.elastic_kubernetes_service` | 1 | broker_kc_box 内 | C-7.3.4 |
| Single Realm + Organizations | `rounded=1` rectangle | 1 | broker_kc_box 内 | C-7.3.4.2 |
| Authentication Flow（HRD + MFA）| `rounded=1` rectangle | 1 | broker_kc_box 内 | C-7.3.4.3 |
| Protocol Mapper（JWT クレーム生成）| `rounded=1` rectangle | 1 | broker_kc_box 内 | C-7.3.4.5 |
| Identity Provider Mapper（amr/SAML 評価）| `rounded=1` rectangle | 1 | broker_kc_box 内 | C-7.3.4.6 |
| **HRD Authenticator Custom SPI（Java）** ★ ADR-055 Phase 1 採用 | `rounded=1` rectangle（fillColor=#fff3e0）| 1 | spi_box 内 | C-7.3.4.4 |
| Risk Engine Authenticator SPI | `rounded=1` rectangle | 1 | spi_box 内 | C-7.3.4.4 |
| Event Listener SPI（ITDR Webhook）| `rounded=1` rectangle | 1 | spi_box 内 | C-7.3.4.4 |
| User Storage SPI（旧 DB 並走）| `rounded=1` rectangle | 1 | spi_box 内 | C-7.3.14 |
| IdP Keycloak（EKS Pod）| `shape=mxgraph.aws4.elastic_kubernetes_service` | 1 | 上段 | C-7.3.5 |
| Public ALB（Broker KC 用、Internet-facing）| `shape=mxgraph.aws4.application_load_balancer` | 1 | 上端 | C-7.3.3 |
| Internal ALB（IdP KC + 管理用 + /admin 受付）| `shape=mxgraph.aws4.application_load_balancer` | 1 | 中央 | C-7.3.3 |
| Aurora Global Database（Broker DB + IdP-KC DB）| `shape=mxgraph.aws4.aurora` | 2 | 中段 | C-7.3.4/5 |
| KMS L1 共通 MRK | `rounded=1` rectangle（kms_box 内） | 1 | 中段 | C-7.3.20 |
| KMS L2 アカウント別（auth-aurora / dynamodb / KC JWT 署名 ES256）| `rounded=1` rectangle | 1 | 中段 | C-7.3.20 |
| KMS L3 テナント別（大規模顧客のみ Cryptographic Erasure）| `rounded=1` rectangle | 1 | 中段 | C-7.3.20 |
| S3 SPA Bundles 5 種（ログイン / アカウント設定 / サービス選択 / ユーザ管理 / エラー）| `rounded=1` rectangle 5 個 | 5 | spa_box 内 | C-7.3.8 |
| ユーザ管理画面 API GW + Backend Lambda + Authorizer + DDB | `shape=mxgraph.aws4.api_gateway` / `shape=mxgraph.aws4.lambda` / `shape=mxgraph.aws4.dynamodb` | 4 | admin_box 内 | C-7.3.13 |
| ITDR Lambda + DDB + EventBridge | `shape=mxgraph.aws4.lambda` / `shape=mxgraph.aws4.dynamodb` / `shape=mxgraph.aws4.eventbridge` | 3 | security_box 内 | C-7.3.10 |
| Adaptive Auth Risk Engine Lambda | `shape=mxgraph.aws4.lambda` | 1 | security_box 内 | C-7.3.10 |
| SCIM Server | `shape=mxgraph.aws4.elastic_kubernetes_service` | 1 | admin_box 内 | C-7.3.9 |
| マッピング DB 注記（Keycloak User Attribute）| `rounded=1` rectangle | 1 | admin_box 内 | C-7.3.29 |
| Route 53 Hosted Zone（`basis.example.com`）| `shape=mxgraph.aws4.route_53` | 1 | admin_box 内 | C-7.3.3 |
| SES（招待 / 通知メール）| `shape=mxgraph.aws4.simple_email_service` | 1 | admin_box 内 | C-7.3.9 |
| DSAR API GW + Workflow Lambda + Step Functions + Export Lambda + DDB + S3 | `shape=mxgraph.aws4.api_gateway` / `shape=mxgraph.aws4.lambda` / `shape=mxgraph.aws4.step_functions` / `shape=mxgraph.aws4.dynamodb` / `shape=mxgraph.aws4.s3` | 6 | dsar_box 内 | C-7.3.23 |
| EKS Pod Identity | `rounded=1` rectangle | 1 | other_auth_box 内 | C-7.3.16 |
| Keycloak FedID（K8s SA JWT → Token Exchange）| `rounded=1` rectangle | 1 | other_auth_box 内 | C-7.3.16 |
| OpenTelemetry Collector | `rounded=1` rectangle | 1 | other_auth_box 内 | C-7.3.28 |
| AMP（Managed Prometheus）| `shape=mxgraph.aws4.managed_service_for_prometheus` | 1 | other_auth_box 内 | C-7.3.28 |
| AMG（Managed Grafana）| `shape=mxgraph.aws4.managed_grafana` | 1 | other_auth_box 内 | C-7.3.28 |
| X-Ray（Distributed Tracing）| `shape=mxgraph.aws4.x_ray` | 1 | other_auth_box 内 | C-7.3.28 |
| CI/CD Pipeline 注記（GitHub Actions / Tekton + SBOM/Cosign/Trivy）| `rounded=1` rectangle | 1 | other_auth_box 内 | C-7.3.21 |
| ECR / Quay.io | `shape=mxgraph.aws4.elastic_container_registry` | 1 | other_auth_box 内 | C-7.3.21 |

### 2.5 App Acct（🟢、複数）

| ノード | drawio shape | 配置目安 |
|---|---|---|
| Internal ALB（VPC Origins 経由）| `shape=mxgraph.aws4.elastic_load_balancing_application_load_balancer` | 上段 |
| ECS / EKS / Lambda（アプリ実体）| `shape=mxgraph.aws4.ecs` / `shape=mxgraph.aws4.elastic_kubernetes_service` / `shape=mxgraph.aws4.lambda` | 中段 |
| アプリ DB（RDS / DynamoDB）| `shape=mxgraph.aws4.rds` / `shape=mxgraph.aws4.dynamodb` | 下段 |
| Route 53 Hosted Zone（`app-X.example.com`）| `shape=mxgraph.aws4.route_53` | 上端 |

### 2.6 外部アクター

| ノード | drawio shape | 配置 |
|---|---|---|
| エンドユーザー（P-3 / P-4）| `shape=mxgraph.aws4.users` | 左上 |
| 顧客テナント管理者（P-2）| `shape=mxgraph.aws4.user` | 左上 |
| 弊社運用者（P-1）| `shape=mxgraph.aws4.user` | 左上 |
| 顧客 IdP（Entra / Okta 等）| `shape=mxgraph.aws4.identity_and_access_management_iam_identity` | 左 |
| 人事 DB / HRIS（ADR-054）| `shape=mxgraph.aws4.database` | 右 |

---

## 3. 接続関係（線種別）

| 接続種別 | 線種 | 説明 |
|---|---|---|
| **HTTPS（公開）** | 実線 + ロックアイコン | エンドユーザー → CloudFront |
| **Cross-Account（VPC Origins）** | 実線（PrivateLink）| ネットワーク監査 Acct CloudFront → App Acct Internal ALB |
| **Cross-Account（Public ALB + secret header）** | 実線（secret header 注記）| ネットワーク監査 Acct CloudFront → Auth Acct Public ALB |
| **Cross-Account（OAC）** | 実線（OAC 注記）| ネットワーク監査 Acct CloudFront → Auth Acct S3 |
| **Transit Gateway 経由** | 太線 | VPC 間通信 |
| **VPN / 社内 NW** | 破線 | 弊社運用者の Internal アクセス |
| **/admin パス Deny** | 赤破線（×）| WAF で外部 IP 全 Deny |
| **DNS Alias** | 細点線 | Route 53 → CloudFront |
| **SCIM Push** | 矢印（SCIM 注記）| 人事 DB → SCIM Server → Keycloak |

---

## 4. 配置方針

### 4.1 全体俯瞰図（`architecture-v2-overview.drawio`）

- **5 Swim Lane**（垂直配置）
  - 上から：エンドユーザー（外部）→ ネットワーク監査 Acct → Auth Platform Acct → App Acct → 監査 Acct
  - 横：ネットワーク Acct を Transit GW 中心に配置
- **アプリごと独立 CloudFront/WAF** を 3-5 個並列表示（アプリ N 個の代表例）
- **/admin パス保護**を赤破線で強調

### 4.2 ネットワーク監査詳細図（`architecture-v2-network-detail.drawio`）

- **アプリごと独立 CloudFront + WAF + Lambda@Edge**のセットを Swim Lane で並列
- Cross-Account 接続（VPC Origins / OAC / Public ALB + secret header）を線種別で明示
- Network Firewall + Shield Advanced を全体を囲む形で配置

---

## 5. 作図の段階的進め方

| Step | 内容 | 工数目安 |
|---|---|---|
| **Step 1** | 本リポジトリの `.drawio` ファイルを VS Code 拡張で開く | 5 分 |
| **Step 2** | 5 アカウント Swim Lane の基本配置確認 + 主要コンポーネント表示確認 | 30 分 |
| **Step 3** | AWS Architecture Icons パレットを drawio 上で有効化（左ペイン →「Shape Categories」→「AWS19」）| 5 分 |
| **Step 4** | スケルトンに含まれない詳細コンポーネント（KMS 個別 / Lambda 群 / DynamoDB 群）を AWS パレットから追加 | 2-4 時間 |
| **Step 5** | 接続線を本書 §3 に従って整理 | 1-2 時間 |
| **Step 6** | 凡例 / タイトル / バージョン情報を追加 | 30 分 |
| **Step 7** | PNG / SVG エクスポートして顧客説明資料に貼付 | 10 分 |

---

## 6. 参考資料

### drawio AWS Architecture Icons

- [drawio AWS Architecture Icons 公式](https://www.drawio.com/blog/aws-templates)
- [AWS Architecture Icons (2023 update)](https://aws.amazon.com/architecture/icons/)
- [drawio Shape Reference - AWS4](https://www.drawio.com/doc/shape-reference#aws4-shapes)

### §C-7 architecture.md 元情報

- [§C-7.2.2 アーキテクチャ全体図](../../requirements/proposal/common/07-implementation-architecture.md#c-72-2-アーキテクチャ全体図)（Mermaid）
- [§C-7.2.3 AWS アカウント境界](../../requirements/proposal/common/07-implementation-architecture.md#c-72-3-aws-アカウント境界の整理)
- [§C-7.3.3 Network 層](../../requirements/proposal/common/07-implementation-architecture.md#c-73-3-network-層外部--内部の流れ)

### 関連 ADR

- [ADR-039 v2 ネットワーク監査アカウント設計](../../adr/039-centralized-network-account-edge-layer.md)
- [ADR-054 ID 統合戦略](../../adr/054-id-integration-strategy.md)
- [ADR-038 ユーザ管理画面 + 認可 C ハイブリッド案](../../adr/038-tenant-admin-portal.md)
