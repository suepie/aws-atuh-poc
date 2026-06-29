# 認証基盤 drawio 詳細図

> **作成日**: 2026-06-25
> **対象**: 要件定義フェーズ確定済の本番想定構成（ADR-001〜054 反映、5 アカウント体系 v2 + 認可 C ハイブリッド案）
> **元情報**: [§C-7 実装アーキテクチャ](../../requirements/proposal/common/07-implementation-architecture.md)

---

## 0. 本ディレクトリの目的

§C-7 architecture.md の Mermaid 図を **drawio (diagrams.net)** で開ける詳細図に変換、AWS Architecture Icons を用いた本番想定図を提供。

### 0.1 ファイル一覧

| ファイル | 内容 | レベル |
|---|---|---|
| `README.md`（本ファイル）| 作図仕様書 + ノード一覧 + 配置方針 | — |
| `architecture-v2-overview.drawio` | **5 アカウント体系全体俯瞰**（5 Swim Lane + 主要コンポーネント）| 概要 |
| `architecture-v2-network-detail.drawio` | **ネットワーク監査 Acct 詳細**（アプリごと独立 CloudFront/WAF）| 詳細 |

### 0.2 drawio で開く方法

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

### 2.4 Auth Platform Acct（🟠）

| ノード | drawio shape | 数 | 配置目安 |
|---|---|---|---|
| Broker Keycloak（EKS Pod）| `shape=mxgraph.aws4.elastic_kubernetes_service` | 1 | 上段 |
| IdP Keycloak（EKS Pod）| `shape=mxgraph.aws4.elastic_kubernetes_service` | 1 | 上段 |
| Public ALB（Broker KC 用、Internet-facing）| `shape=mxgraph.aws4.elastic_load_balancing_application_load_balancer` | 1 | 上端 |
| Internal ALB（IdP KC + 管理用）| `shape=mxgraph.aws4.elastic_load_balancing_application_load_balancer` | 1 | 中央 |
| Aurora Global Database（Broker DB + IdP-KC DB）| `shape=mxgraph.aws4.aurora` | 2 | 中段 |
| KMS CMK（L1 + L2、Multi-Region）| `shape=mxgraph.aws4.key_management_service` | 〜10 | 周辺 |
| S3 SPA Bundles | `shape=mxgraph.aws4.s3` | 1 | 下段 |
| ユーザ管理画面 Backend Lambda | `shape=mxgraph.aws4.lambda` | 数 | 下段 |
| ITDR Lambda + DynamoDB + EventBridge | `shape=mxgraph.aws4.lambda` / `shape=mxgraph.aws4.dynamodb` / `shape=mxgraph.aws4.eventbridge` | 数 | 別エリア |
| Adaptive Auth Lambda | `shape=mxgraph.aws4.lambda` | 1 | ITDR 付近 |
| SCIM Server | `shape=mxgraph.aws4.elastic_kubernetes_service` | 1 | プロビ層 |
| Route 53 Hosted Zone（`basis.example.com`）| `shape=mxgraph.aws4.route_53` | 1 | 上端 |

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
