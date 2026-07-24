# ROSA (Red Hat OpenShift Service on AWS) — 詳細調査リファレンス

> **目的**: ROSA (Red Hat OpenShift Service on AWS) の概要・アーキテクチャ・価格・SLA・本基盤での採用検討材料を網羅した reference doc。RHBK 採用判断・プラットフォーム選定で参照される技術的事実集約。
> **対象読者**: プラットフォーム選定者 / インフラ設計者 / コスト試算担当 / 営業
> **位置付け**: [ADR-056 ROSA 採用判断](../adr/056-rosa-adoption-decision.md) の input source（ADR は判断記録、本 doc は事実整理）
> **関連**:
> - [ADR-056 ROSA 採用判断](../adr/056-rosa-adoption-decision.md)（本 doc を input として最終判断）
> - [rhbk-support-and-pricing.md](rhbk-support-and-pricing.md) — RHBK サポート対象（ROSA 含む）
> - [rhbk-vendor-inquiry.md](../requirements/rhbk-vendor-inquiry.md) — Red Hat / リセラへの照会メール文面
> - [keycloak-upstream-vs-rhbk.md](keycloak-upstream-vs-rhbk.md) — RHBK 採用判断フレーム
> - [ADR-015 RHBK validation deferred](../adr/015-rhbk-validation-deferred.md)
> - [ADR-006 Cognito vs Keycloak コスト損益分岐](../adr/006-cognito-vs-keycloak-cost-breakeven.md)

---

## 目次

1. [ROSA とは — 30 秒サマリ](#1-rosa-とは--30-秒サマリ)
2. [ROSA Classic vs ROSA HCP（Hosted Control Plane）](#2-rosa-classic-vs-rosa-hcphosted-control-plane)
3. [価格モデル詳細](#3-価格モデル詳細)
4. [コスト試算 — 本基盤の Keycloak HA 想定](#4-コスト試算--本基盤の-keycloak-ha-想定)
5. [SLA と運用責任](#5-sla-と運用責任)
6. [リージョン展開](#6-リージョン展開)
7. [AWS サービス統合](#7-aws-サービス統合)
8. [RHBK 採用との関係](#8-rhbk-採用との関係)
9. [本 PoC からの移行考慮](#9-本-poc-からの移行考慮)
10. [採用判断フレーム](#10-採用判断フレーム)
11. [コントロールプレーンに入る情報とコンプライアンス影響（PCI DSS / APPI）](#11-コントロールプレーンに入る情報とコンプライアンス影響pci-dss--appi)
12. [参考文献](#12-参考文献)

---

## 1. ROSA とは — 30 秒サマリ

> **ROSA (Red Hat OpenShift Service on AWS)** は AWS と Red Hat が **共同設計・共同サポート**するマネージド OpenShift サービス。OpenShift クラスタの構築・運用・パッチ・アップグレードを Red Hat SRE チームが担当し、顧客は OpenShift ワークロードに集中できる。**99.95% SLA** 保証、AWS Marketplace 経由で購買可能、AWS サービス（RDS / S3 / IAM 等）とネイティブ統合。

### 公式の位置付け

| 出典 | 表現 |
|---|---|
| Red Hat 公式 | "Managed OpenShift integration in the cloud" |
| AWS 公式 | "production-ready OpenShift integration" + "self-service provisioning, automatic security enforcement" |
| サポート体制 | "joint Red Hat and AWS support" + "global Site Reliability Engineering (SRE) team" |
| 購買経路 | AWS Marketplace（AWS 請求書に統合可能）|

### 主な利用シーン（Red Hat 公式）

1. **AI/ML** — Red Hat OpenShift AI でのモデル構築・デプロイ
2. **Virtualization** — コンテナと VM の混在運用 + 移行ツール
3. **Hybrid Cloud** — オンプレ / クラウド / エッジでの一貫した運用

→ **本基盤の認証基盤用途**は上記の primary use case には含まれていない（OpenShift ミドルウェアの 1 つとして RHBK が動く位置付け）。

---

## 2. ROSA Classic vs ROSA HCP（Hosted Control Plane）

ROSA には **2 つの形態** があり、Control plane の所在で課金・コスト・運用が大きく変わる。

### アーキテクチャの違い

```
┌─ ROSA Classic ────────────────────────┐  ┌─ ROSA HCP (2024 GA、新規推奨) ───────┐
│                                       │  │                                      │
│ 顧客の AWS アカウント                  │  │ 顧客の AWS アカウント                │
│ ┌─────────────────────────────────┐  │  │ ┌────────────────────────────────┐  │
│ │ Control Plane (3x m5.2xlarge)    │  │  │ │ Worker Nodes (3x m5.xlarge)    │  │
│ │ Infrastructure Nodes (3x r5.xl)  │  │  │ │ + Infrastructure (statically)  │  │
│ │ Worker Nodes (3x m5.xlarge)     │  │  │ └────────────────────────────────┘  │
│ │ 計 9 ノード                      │  │  │                                      │
│ └─────────────────────────────────┘  │  │ ─────────────────────────────────── │
│                                       │  │                                      │
│ ★ 全てが顧客の AWS 課金              │  │ Red Hat の AWS アカウント            │
└───────────────────────────────────────┘  │ ┌────────────────────────────────┐  │
                                            │ │ Control Plane (Hosted by RH)   │  │
                                            │ │ ★ Red Hat 運用、顧客は         │  │
                                            │ │   cluster fee $0.25/hr 払う    │  │
                                            │ └────────────────────────────────┘  │
                                            └──────────────────────────────────────┘
```

### 比較表

| 観点 | ROSA Classic | ROSA HCP |
|---|---|---|
| **Control Plane の所在** | 顧客 AWS アカウント内（3 ノード）| **Red Hat 所有の AWS アカウント** |
| **Infrastructure ノード** | 顧客 AWS（3 ノード必要）| 顧客 AWS（埋込み or 削減）|
| **Worker ノード** | 顧客 AWS（3+ ノード）| 顧客 AWS（3+ ノード）|
| **最小ノード数** | 9 ノード | **3 ノード**（worker のみ）|
| **Control Plane の課金** | EC2 instance 課金（m5.2xlarge × 3 ≒ $830/月）| **$0.25/hr cluster fee（一律）** |
| **クラスタ起動時間** | 約 40 分 | **約 10 分**（Red Hat 側が事前準備）|
| **アップグレード時間** | 数時間 | **約 1 時間**（Red Hat 側で並列処理）|
| **クラスタ削除・再作成コスト** | 高 | **低**（dev/stg 用にも適） |
| **AWS PrivateLink 経由 API** | 設定可能 | **HCP 標準対応** |
| **コスト効率** | 9 ノード分インフラ常時稼働 | **6 ノード削減 + cluster fee** |
| **採用推奨** | レガシー / オンプレ意識強い場合 | **新規採用は HCP 推奨** |

> Red Hat 公式 ([www.redhat.com](https://www.redhat.com/en/technologies/cloud-computing/openshift/aws)) の HCP 紹介:
> "the control plane is hosted in a Red Hat-owned AWS account, providing cost savings and improved efficiency and reliability."

### どちらを選ぶべきか

| 状況 | 推奨 |
|---|---|
| **新規導入 / クラスタを動的に作りたい** | **ROSA HCP** |
| **既存 ROSA Classic ユーザー / カスタム control plane 構成** | Classic を維持 |
| **規制要件で control plane も自社アカウント内必須** | Classic（HCP は Red Hat アカウントなので NG）|
| **コスト最適化が最重要** | **HCP**（Classic より 30-50% 安い）|
| **本基盤** | **HCP**（コスト・運用負荷両面で有利）|

→ 2024 年に HCP が一般提供開始されて以降、**新規は HCP が業界推奨**。

---

## 3. 価格モデル詳細

### 課金の 3 階層構造

```
ROSA の総コスト = ① ROSA Service Fee + ② AWS Infrastructure Fee + ③ HCP のみ: Cluster Fee
                                                    │
                              Worker Node EC2 + Storage (EBS) + Network 等
```

### ① ROSA Service Fee（worker node の per-vCPU 課金）

| 契約形態 | 4 vCPU/年額 | 1 vCPU/時間換算 | 4 vCPU/時間換算 |
|---|---|---|---|
| **On-Demand** | $1,500 | $0.043 | **$0.171** |
| **1 年契約** (33% off) | $1,000 | $0.029 | $0.114 |
| **3 年契約** (55% off) | $667 | $0.019 | $0.076 |

- 課金対象: **worker node の vCPU のみ** (control plane / infrastructure は別)
- 4 vCPU 単位の課金 (3 vCPU 利用でも 4 vCPU 課金)
- 出典: [AWS ROSA Pricing](https://aws.amazon.com/rosa/pricing/)

### ② AWS Infrastructure Fee（worker node の EC2 等）

通常の AWS EC2 / EBS / Data Transfer 課金:

| 構成要素 | コスト目安 |
|---|---|
| m5.xlarge (4 vCPU, 16 GB) | $0.192/hr (on-demand) / $0.114 (1y RI) / $0.077 (3y RI) |
| m5.2xlarge (8 vCPU, 32 GB) | $0.384/hr / $0.228 / $0.155 |
| EBS gp3 (storage) | $0.08/GB/月 |
| AZ 間データ転送 | $0.01/GB |
| NAT Gateway | $0.045/hr + $0.045/GB |

### ③ HCP Cluster Fee（HCP のみ）

- **$0.25/hr** = **約 $180/月** = **約 $2,160/年**
- 24/7 起動なら必ず課金
- クラスタ削除時のみ停止

### Classic の Control Plane 課金（参考）

- m5.2xlarge × 3 ノード = 8 vCPU × 3 = 24 vCPU
- $0.384/hr × 3 × 24 × 30 = **約 $830/月**（On-Demand）
- 1y RI: 約 $493/月、3y RI: 約 $335/月

→ HCP の $180/月 vs Classic の $830/月 で **HCP は月額 $650 安い**（コントロールプレーン分だけで）。

---

## 4. コスト試算 — 本基盤の Keycloak HA 想定

### 前提条件

- Keycloak HA: worker node 3 個（Multi-AZ）
- 各 worker: m5.xlarge (4 vCPU, 16 GB) = Keycloak Pod 2-3 個動かせる
- 計 12 vCPU = 3 units of 4 vCPU billing
- Aurora PostgreSQL Multi-AZ は別途（ROSA 外）

### ROSA HCP 月額試算

| 項目 | On-Demand | 1y RI | 3y RI |
|---|---|---|---|
| ROSA Service Fee (12 vCPU = 3 units) | $375 | $250 | $167 |
| HCP Cluster Fee ($0.25/hr × 730h) | $182 | $182 | $182 |
| Worker EC2 (m5.xlarge × 3) | $415 | $246 | $167 |
| EBS gp3 (3 × 100GB) | $24 | $24 | $24 |
| NAT GW + Data Transfer | $50 | $50 | $50 |
| **計** | **~$1,046/月** | **~$752/月** | **~$590/月** |

### ROSA Classic 月額試算

| 項目 | On-Demand | 1y RI | 3y RI |
|---|---|---|---|
| ROSA Service Fee | $375 | $250 | $167 |
| Control Plane EC2 (m5.2xlarge × 3) | $830 | $493 | $335 |
| Infrastructure EC2 (r5.xlarge × 3) | $546 | $324 | $220 |
| Worker EC2 (m5.xlarge × 3) | $415 | $246 | $167 |
| EBS + NAT + Transfer | $100 | $100 | $100 |
| **計** | **~$2,266/月** | **~$1,413/月** | **~$989/月** |

→ **HCP は Classic より約 50% 安い**。新規採用は HCP 一択。

### 現 PoC (ECS Fargate) との比較

| 構成 | 月額（停止運用） | 月額（常時） |
|---|---|---|
| 現 PoC: ECS Fargate + RDS Multi-AZ | ~$90 | ~$190 |
| EC2 RHEL + RHBK + RDS Multi-AZ | ~$200-300 | ~$400-600 |
| **ROSA HCP 3y RI + Aurora** | – | **~$640-690** |
| **ROSA Classic 3y RI + Aurora** | – | **~$1,040-1,090** |

→ **ROSA HCP 採用は ECS 比で 3-5 倍のコスト増**。EC2 RHEL + RHBK と比べても少し高い。

### ROSA + RHBK サブスクリプション

> **2026-07-23 訂正（確定）**: [KB 7044244](https://access.redhat.com/articles/7044244) により **RHBK エンタイトルメントは OCP サブスクリプションに含まれ、ROSA/ARO/OSD ユーザーにも有効 = ROSA 採用時に RHBK 別途サブスクは不要**と確定（[basic-design/research/rosa-hcp-adoption-research.md](../basic-design/research/rosa-hcp-adoption-research.md)）。ROSA では RHBK は「customer installed software」扱い（Red Hat がサポート、運用は顧客）。旧記述「別途必要 / 可能性が高い」は履歴として下に残す。

<details><summary>旧記述（2024 調査時点、2026-07-23 訂正済み）</summary>

ROSA 上で RHBK を動かす場合、**RHBK サブスクリプション**が **別途必要**:
- 本リポの [rhbk-support-and-pricing.md §5](rhbk-support-and-pricing.md) 参照
- Red Hat Runtimes Standard 4 vCPU 1y 契約: 要見積もり（リセラ表示あり）
- ただし [KB 7044244](https://access.redhat.com/articles/7044244) に「**RHBK 使用コアは OCP サブスクの総コアにカウント可能**」とあり、**ROSA を採用すれば RHBK 別途サブスク不要 or 大幅減**になる可能性が高い
- → リセラに照会が必須（[rhbk-vendor-inquiry.md Q8](../requirements/rhbk-vendor-inquiry.md) で確認項目あり）

</details>

### 3 年 TCO 比較（参考）

| 構成 | 3 年 TCO（Aurora 含む）|
|---|---|
| 現 PoC: ECS Fargate + RDS | 約 $6,800 |
| EC2 RHEL + RHBK サブスク + Aurora | 約 $20,000 - $30,000（サブスク含む）|
| **ROSA HCP 3y RI + Aurora** | **約 $25,000**（RHBK サブスク内包 — 2026-07-23 確定）|
| ~~ROSA HCP 3y RI + Aurora + RHBK 別途~~ | ~~約 $30,000 - $45,000~~（**2026-07-23 訂正: 本行は不要。RHBK は ROSA 内包のため「サブスク別途」のケースは存在しない**）|

→ ~~ROSA + RHBK 統合サブスクが認められれば~~ **（2026-07-23 確定）** ROSA HCP の 3y TCO は EC2 + RHBK と同等圏（約 $25,000）で、フルマネージド + SLA 99.95% が付く。

---

## 5. SLA と運用責任

### SLA

- **99.95% uptime SLA** ([Red Hat 公式](https://www.redhat.com/en/technologies/cloud-computing/openshift/aws))
- = 月あたり **約 22 分**のダウンタイム許容
- Red Hat の **global SRE team** が運用
- 違反時のクレジット詳細は [ROSA Service Agreement](https://www.redhat.com/en/about/agreements) で確認

参考: 認証基盤に 99.99% SLA を求める場合 (月 4 分許容)、ROSA HCP に **Multi-Region**（PrivateLink ベース DR）を組み合わせる必要あり。

### Shared Responsibility Model

ROSA の責任分界（Red Hat / AWS / 顧客）:

| レイヤ | Red Hat | AWS | 顧客 |
|---|:-:|:-:|:-:|
| OpenShift Control Plane（HCP）| ✅ | – | – |
| OpenShift Control Plane（Classic）| ✅ 運用 | EC2 提供 | EC2 課金 |
| OpenShift Worker Node OS / kubelet | ✅ パッチ・更新 | EC2 提供 | EC2 課金 |
| Cluster Autoscaling / Operator | ✅ | – | 設定 |
| ワークロード（Pod / Deployment）| – | – | **✅ 顧客責任** |
| アプリケーションコード | – | – | **✅ 顧客責任** |
| AWS インフラ（EC2 / VPC 等）| – | ✅ 物理・ハイパーバイザ | ネットワーク設定 |
| データ（PV / RDS 等）| – | ✅ ストレージ層 | **✅ アプリデータ** |
| 監視・アラート設定 | 基本提供 | CloudWatch 提供 | カスタム設定 |
| バックアップ・DR | – | EBS Snapshot 等提供 | **✅ ポリシー** |

→ **Red Hat が「OpenShift 自体の運用」を担い、顧客は「ワークロード・データ」に集中**。RHBK Pod は顧客責任の領域。

---

## 6. リージョン展開

[AWS Regional Services List](https://aws.amazon.com/about-aws/global-infrastructure/regional-product-services/) で正確なリスト確認必要だが、一般的に:

| リージョン | ROSA Classic | ROSA HCP |
|---|:-:|:-:|
| us-east-1 (Virginia) | ✅ | ✅ |
| us-west-2 (Oregon) | ✅ | ✅ |
| eu-west-1 (Ireland) | ✅ | ✅ |
| **ap-northeast-1 (東京)** | ✅ | ✅（2024 GA 後対応）|
| **ap-northeast-3 (大阪)** | ✅（**2026-07-23 確認済み**、[AWS 公式表](https://docs.aws.amazon.com/general/latest/gr/rosa.html)） | ✅（同左） |
| ap-southeast-1/2 (Singapore/Sydney) | ✅ | ✅ |

→ **本基盤の東京・大阪とも対応（2026-07-23 解消）**。東京 + 大阪の ROSA HCP 対称 DR 構成が成立。残: 大阪側の採用予定インスタンスタイプ在庫 + vCPU クォータの実確認のみ。

### Multi-AZ 構成

- ROSA は **Multi-AZ がデフォルト推奨**（SLA 99.95% を満たすため）
- HCP では worker node を 3 AZ に均等配置
- Classic では control plane / infra / worker すべて Multi-AZ で 3 AZ × 3 ノード = 9 ノード最小

---

## 7. AWS サービス統合

ROSA は AWS マネージドサービスとネイティブ統合:

| AWS サービス | ROSA との連携 |
|---|---|
| **RDS / Aurora** | 認証情報を OpenShift Secret で管理。**接続は SG 直接続（2026-07-23 訂正: HCP でも worker は顧客 VPC 内で稼働するため PrivateLink は不要。PrivateLink は control plane ↔ worker 間の話）** |
| **S3** | OpenShift Storage 経由 / アプリ直接アクセス |
| **EFS** | OpenShift Storage Class として利用可 |
| **IAM** | STS-based ROSA Roles（クラスタごとに別 IAM Role）|
| **ALB / NLB** | OpenShift Ingress / Service として直接統合 |
| **CloudWatch / Cost Explorer** | コスト・メトリクス可視化 |
| **Secrets Manager** | OpenShift Secret に投入 |
| **AWS PrivateLink** | HCP では control plane アクセスを PrivateLink 経由可 |
| **KMS** | EBS / RDS / S3 暗号化キー |
| **Route 53** | OpenShift Ingress の DNS 統合 |

→ 本基盤の **Aurora PostgreSQL / ALB / CloudWatch** との統合は問題なし。

---

## 8. RHBK 採用との関係

本基盤を **ROSA + RHBK** で動かす場合の構図:

```
┌─ ROSA Cluster ─────────────────────────────┐
│                                             │
│  ┌─ RHBK Pods (3+ replica, Multi-AZ) ──┐  │
│  │  registry.redhat.io/rhbk/keycloak-   │  │
│  │  rhel9:26.x                          │  │
│  └────────────────────────────────────────┘ │
│                                             │
│  Infinispan (Embedded / OpenShift Cache)    │
│  ↕ JGroups (Pod 間)                          │
│                                             │
└──────────────────────────────────────────────┘
        ↓                                     ↓
   ┌─Aurora PostgreSQL──┐         ┌─ ALB / NLB ──┐
   │ Multi-AZ           │         │              │
   └────────────────────┘         └──────────────┘
```

### ROSA + RHBK の利点

| 利点 | 内容 |
|---|---|
| **第一級サポート** | RHBK 公式サポート対象 ([KB 7033107](https://access.redhat.com/articles/7033107) で OpenShift 4.12+ + ROSA が一級扱い) |
| **HA 標準** | OpenShift StatefulSet / Operator で Multi-AZ HA が標準 |
| **アップグレード自動化** | Red Hat SRE が ROSA クラスタを管理、RHBK バージョン更新も Operator で対応可 |
| **規制対応** | FIPS 140-2 mode で動作可、HIPAA BAA も AWS で締結可 |
| **Multi-Site HA Operator** | RHBK 26.4+ の Multi-Site HA は OpenShift 単一クラスタ複数 AZ 構成で extended support |
| **コスト統合** | AWS Marketplace で AWS 請求書に統合、ROSA サブスクで RHBK ライセンスもカバー可（要照会）|

### ROSA + RHBK の欠点・考慮

| 欠点 | 内容 |
|---|---|
| **コスト増** | ECS Fargate の 3-5 倍（HCP 3y RI でも $590-690/月）|
| **OpenShift 知識習得** | Terraform / Helm 中心のチームには学習コスト |
| **オペレーション統合** | 既存 AWS-native 運用 (CloudWatch / SSM) と OpenShift 運用 (oc / OperatorHub) の二重化 |
| **マイグレーション工数** | ECS Fargate → ROSA は Terraform / Dockerfile / Manifest の全面書き換え |
| **AWS マルチアカウント戦略との整合性** | ROSA は単一クラスタ前提、複数アカウント分散には不向き |

### ROSA + RHBK の Operator 動作

Red Hat の RHBK Operator が OpenShift 上で以下を自動管理:

| 機能 | 内容 |
|---|---|
| **インストール** | OperatorHub から 1 クリック |
| **CR ベース管理** | `Keycloak` カスタムリソースで宣言的に realm/client/role 管理 |
| **アップグレード** | Operator が自動 rolling update |
| **HA 構成** | StatefulSet で Multi-AZ 配置、Infinispan/JGroups 自動構成 |
| **バックアップ** | Operator + AWS Backup 統合可 |
| **Multi-Site HA** | RHBK 26.4+ で OpenShift マルチ AZ 構成サポート |

→ Operator 採用で運用工数は ECS Fargate より小さい可能性。ただし学習コストは大。

---

## 9. 本 PoC からの移行考慮

現 ECS Fargate ベースの PoC を ROSA に移行する場合:

### Phase 別の作業

| Phase | 内容 | 工数 |
|---|---|---|
| 1. ROSA クラスタ作成 | Terraform で ROSA HCP 構築 + Aurora PostgreSQL Multi-AZ | 1-2 週間 |
| 2. RHBK Operator 導入 | OperatorHub から RHBK Operator install + Keycloak CR 定義 | 1 週間 |
| 3. realm-export.json import | 既存 [keycloak/config/realm-export.json](../../keycloak/config/realm-export.json) を ConfigMap or PV 経由で投入 | 1 日 |
| 4. Multi-AZ HA 動作確認 | JGroups Pod 間通信、Pod kill 時 failover 検証 | 1 週間 |
| 5. CloudFront + ALB 統合 | Ingress を ALB Controller で公開、CloudFront 前段配置 | 1 週間 |
| 6. CI/CD パイプライン整備 | GitHub Actions / GitLab CI で OpenShift Manifest デプロイ | 1 週間 |
| 7. 既存 Lambda Authorizer 維持 | ROSA 外の Lambda は変更なし、JWKS は ROSA 公開エンドポイントから取得 | 0.5 日 |
| **合計** | – | **6-8 週間** |

### Stage A Terraform との関係

[infra/keycloak/](../../infra/keycloak/) の現 Terraform 群:
- ECS / RDS / ALB / VPC Endpoint → **ROSA 移行時はすべて廃棄**（ROSA 自体が同等機能を提供）
- Aurora PostgreSQL Multi-AZ は維持・ROSA から接続
- Lambda VPC Authorizer（[ADR-012](../adr/012-vpc-lambda-authorizer-internal-jwks.md)）は ROSA 外の Lambda として継続可

→ **Stage A の Terraform 投資は ROSA 移行時に大半が破棄される**。ROSA 採用決定は **Stage A AWS apply 前** が望ましい。

### 既存 Phase 1-9 / Stage A 成果物の流用可能性

| 成果物 | ROSA 移行時の扱い |
|---|---|
| [realm-export.json](../../keycloak/config/realm-export.json) | ✅ そのまま流用（ConfigMap / PV 経由）|
| [Dockerfile](../../keycloak/Dockerfile) | ⚠ RHBK 公式イメージに置換（`registry.redhat.io/rhbk/keycloak-rhel9:26.x`）|
| Token Exchange / SSR Client 設定 | ✅ realm-export.json と一緒に流用 |
| Lambda Authorizer ([ADR-012](../adr/012-vpc-lambda-authorizer-internal-jwks.md)) | ✅ ROSA 外の Lambda として継続 |
| ECS / RDS Terraform | ❌ 廃棄、ROSA 用 Terraform を新規作成 |
| ALB Listener / Target Group | ⚠ OpenShift Route / Ingress に置換 |
| Phase 8/9 検証結果 | ✅ 動作確認済の構成として ROSA でも再現可能 |

---

## 10. 採用判断フレーム

### ROSA 採用が **推奨される** 状況

| 条件 | 当てはまり度（本基盤）| 備考 |
|---|:-:|---|
| RHBK 商用サポート必須 (FIPS / HIPAA / 24/7 SLA 等) | ❓ 要件次第 | 顧客に金融・医療・政府機関を含む場合 |
| 10M+ MAU の大規模認証基盤 | 🟡 想定次第 | 大規模なら ROSA HCP のスケール優位 |
| 既存 OpenShift エンジニアがチームにいる | ❓ | 学習コスト軽減 |
| マルチアプリ前提（認証基盤 + 他のミドルウェア・アプリも OpenShift で統合）| ❓ | ROSA の規模効率を発揮 |
| 規制業界（金融 / 医療 / 政府）| ❓ | FIPS / HIPAA / BAA 要件 |
| AWS GovCloud / 厳格分離要件 | ❌ 想定なし | 本基盤は通常リージョン |

### ROSA 採用が **推奨されない** 状況

| 条件 | 当てはまり度（本基盤）| 備考 |
|---|:-:|---|
| 認証基盤単独 + 小〜中規模（〜10K MAU）| ⚠ 当てはまる | コストオーバーヘッドが顕著 |
| コスト最重要（$200-500/月レンジ）| ⚠ 当てはまる | ROSA HCP $590-/月は予算超過 |
| ECS / Fargate での運用に慣れている | ✅ 当てはまる | 既存ノウハウ活用可 |
| Upstream Keycloak OSS でサポート要件満たせる | ✅ 想定 | RHBK 商用サポート不要 |
| マルチ AWS アカウント戦略との整合性 | ⚠ ROSA は単一クラスタ前提 | 横断分散には不向き |

→ **本基盤は ROSA 採用の必然性が薄い**。**Upstream Keycloak OSS + ECS Fargate** または **EC2 RHEL + RHBK サブスク**が現実的な選択肢。

### 推奨される次のアクション（状況別）

| 状況 | アクション |
|---|---|
| **ROSA 採用検討中** | リセラ ([rhbk-vendor-inquiry.md §3](../requirements/rhbk-vendor-inquiry.md)) に「ROSA + RHBK 構成での見積」を Q7 として追加照会 |
| **コスト試算が必要** | [AWS Pricing Calculator](https://calculator.aws/) で本試算 + Aurora PostgreSQL 追加 |
| **既存 PoC と比較したい** | ECS Fargate 月額 $190 vs ROSA HCP 月額 $590 の差分を本番要件と照合 |
| **採用しない判断** | [ADR-015 RHBK validation deferred](../adr/015-rhbk-validation-deferred.md) の延長として **Upstream Keycloak OSS + EC2 RHEL + RHBK サブスク**を代替案として検討 |
| **採用する場合** | Stage A AWS apply 前に方針確定（Terraform 全面書き換え）|

---

## 11. コントロールプレーンに入る情報とコンプライアンス影響（PCI DSS / APPI）

> **HCP モデル特有の論点**: コントロールプレーンが **Red Hat 所有 AWS アカウント内** で動くため、そこに乗る情報を具体的に把握し、PCI DSS / APPI 等の規制要件への影響を評価する必要がある。本セクションは [ADR-056](../adr/056-rosa-adoption-decision.md) の採用判断時に「コンプライアンス観点で何を追加要件とするか」を決める input source。

### 11.1 HCP コントロールプレーンに入る情報

**Red Hat 所有 AWS アカウント内**で稼働 / 永続化されるもの:

| コンポーネント | 中身 | 認証基盤として影響 |
|---|---|---|
| **etcd**（暗号化済永続ストレージ）| 全 K8s リソース | ★最重要 |
| └ Kubernetes Secrets | DB 接続文字列 / TLS 秘密鍵 / **Keycloak JWT 署名鍵** / Keycloak admin password / IdP Client Secret | ★ |
| └ ConfigMaps | Keycloak realm.json 参照 / env 値 | △ |
| └ ServiceAccount tokens | Pod → API server 認証 | △ |
| └ Pod / Deployment specs | イメージ参照 / env 名 | △ |
| └ Audit log buffer | 一時的（通常は CloudWatch へ flush）| △ |
| **kube-apiserver** | API リクエスト処理（in-memory）| △ |
| **OpenShift OAuth server** | クラスタ管理者 SSO（Keycloak 本体とは別）| △ |
| **kube-controller-manager / scheduler** | 制御ループ（状態のみ）| △ |

**顧客 VPC（データプレーン）側に残り、コントロールプレーンには入らない**もの:

| データ | 場所 |
|---|---|
| **Keycloak users テーブル**（パスワードハッシュ / MFA seed / PII）| Aurora PostgreSQL（顧客 VPC）|
| **セッションデータ**（Infinispan）| Worker Node メモリ（顧客 VPC）|
| **アプリケーション DB**（カード会員データ等）| 顧客 VPC |
| **監査ログ**（flush 後）| CloudWatch / S3（顧客アカウント）|

**判定**:

- **個人データ・CHD（Cardholder Data）本体は etcd には入らない**（適切な設計を維持する限り）
- ただし **JWT 署名鍵 / DB 接続クレデンシャル / IdP Client Secret は etcd に入る** → 「個人データを保護するための鍵」として間接的に規制対象
- **設計原則として「K8s Secret に個人データを直接保存しない（鍵のみ）/ 個人データはアプリ DB（顧客 VPC 内）」を必須化** する必要

### 11.2 PCI DSS v4.0.1 の兼ね合い

| 条項 | 要件 | ROSA HCP での扱い |
|---|---|---|
| **§3.6 / §3.7** | 暗号鍵の管理 / SoD（Separation of Duties）| etcd 内 K8s Secret に Keycloak JWT 署名鍵が乗る場合、Red Hat 側 KMS 暗号化 + BYOK (Bring Your Own Key) 可否確認が必要 |
| **§7 / §8** | 最小権限 / 強認証 | Red Hat SRE の JIT (Just-In-Time) アクセス管理（OpenShift OAuth + Cluster Logging）|
| **§10.2** | 監査証跡 | API server audit log を顧客 CloudWatch に強制 flush。SRE 操作も含む |
| **§11** | ペネトレーションテスト | ROSA インフラ層は Red Hat が実施。顧客は worker node 上ワークロードのみ |
| **§12.8** | TPSP (Third-Party Service Provider) リスト管理 | Red Hat を委託先として登録 / 監督記録 |
| **§12.9** | TPSP 責任分担マトリクス | Red Hat AOC (Attestation of Compliance) + Shared Responsibility Matrix 取得 |
| **§6.4.3** | サプライチェーン整合性 | OpenShift コンテナイメージ署名 (Cosign / sigstore) 適用 |

**Red Hat / AWS の attestation 入手経路**:

- ROSA は **PCI DSS Level 1 Service Provider** として AWS Artifact から AOC 取得可能（要確認: 2024 年版 + リージョン別カバレッジ）
- Red Hat 側補完統制 (compensating controls) を顧客監査人 (QSA) に提示可能

**判断**:

- **CHD 本体を etcd に乗せない設計を維持できれば** ROSA HCP は PCI DSS スコープ内クラスタとして許容される
- 前提: カード番号自体は決済代行 (Stripe / Adyen / GMO) でトークン化し、認証基盤に流さない
- 運用要件: Red Hat AOC を**毎年取得** + §12.8 / §12.9 文書化を継続

### 11.3 APPI（個人情報の保護に関する法律）の兼ね合い

| 条文 | 要件 | ROSA HCP での扱い |
|---|---|---|
| **法第25条**（委託先の監督）| 委託先の安全管理措置監督義務 | Red Hat = 委託先（マネージドサービスは原則「委託」）。DPA (Data Processing Addendum) + 監査権規定必要 |
| **法第27条**（第三者提供の制限）| 第三者提供は同意 or 例外 | 委託扱いなら 27 条非該当 |
| **法第28条**（外国第三者提供） | 越境提供は「相当措置」必要 | ★最大の論点（後述）|
| **規則第7条**（安全管理措置）| 組織的 / 人的 / 物理的 / 技術的措置 | 委託監督に含む |

**法第28条の論点**:

> **用語の明確化**: 本セクションで「SRE 越境」と呼ぶのは **Red Hat 社員のクラスタ運用チーム（Red Hat ROSA SRE）の所在**を指す。**弊社オペレーター（認証基盤運用チーム）は国内想定**であり、APPI 28 条評価対象外。RHEL サブスクのサポートとは異なり、ROSA は「**Red Hat が顧客クラスタを管理する**」モデルのため、Red Hat SRE のアクセス所在地が論点となる。

| 観点 | 状況 |
|---|---|
| **データ物理保存地** | ROSA HCP コントロールプレーンは **ap-northeast-1（東京）に配置可能** → 物理保存は国内 |
| **Red Hat SRE の所在**（**Red Hat 社員**、弊社運用者ではない） | Red Hat の "follow-the-sun" モデルで **米国 (Raleigh NC, Westford MA) + EMEA (Brno チェコ, Dublin) + APAC (Pune インド、Brisbane 豪、Tokyo)** の各拠点から 24/7 対応。**地理的制限を契約で保証することは難しい**（ROSA 標準 SLA に地理限定規定なし） |
| **Red Hat SRE のアクセス形態** | JIT (Just-In-Time) アクセス、インシデント対応時のみ顧客クラスタへ到達 → 「**外国にある第三者への提供**」に該当する可能性 |
| **個人データ本体の所在** | etcd には入らない（適切な設計時、§11.4 参照）→ 28 条主たる懸念は限定的 |
| **間接的処理** | K8s Secret 経由で「個人データを処理するための鍵」を扱う → 委託監督義務 (法第 25 条) |

**APPI 28 条への対応オプション**:

1. **本人同意**: 越境前に明示同意取得（実務的に困難、SaaS では非現実的）
2. **相当措置**: 委託先国が「個人情報保護委員会が指定する国」 (EU + 英国) → 米国は対象外（Red Hat 本社 = 米国）
3. **基準適合体制**: 委託先が「基準に適合する体制」を整備 → **DPA + GDPR SCC (Standard Contractual Clauses) 相当条項で対応可能**（実務上の主流）

**判断**:

ROSA HCP は APPI 上採用可能だが、以下を整備する必要あり:

- **Red Hat との DPA に APPI 28 条「相当措置」相当の規定**（GDPR SCC 統合可否を Red Hat 営業に確認）
- **Red Hat SRE 越境アクセスログ**を顧客側で取得できる契約条項
- **設計原則**: 「ROSA は K8s 管理データのみ、個人データはアプリ DB（顧客 VPC 内）に閉じ込める」を維持
- **個人情報保護方針 / プライバシーポリシー**に Red Hat / AWS の役割明示（委託先公表）

### 11.4 「個人データ・CHD を etcd に入れない」の具体化と限界

> **用語の厳密化**: 「etcd 非流入」と一括りに言うと誤解を招くため、以下に **何が達成可能で何が達成不可か**を明示する。

#### Keycloak のデフォルト設計 — 個人データは元々 etcd に入らない

| データ | デフォルト保存場所 | etcd に入るか |
|---|---|---|
| Keycloak users テーブル（パスハッシュ / MFA seed / PII）| Aurora PostgreSQL（顧客 VPC）| **入らない** |
| セッション（Infinispan）| Worker Node メモリ | **入らない** |
| Realm 設定（永続）| Aurora PostgreSQL | **入らない** |
| アプリケーション DB（CHD があれば）| 各アプリ DB（決済代行トークン化前提）| **入らない** |
| **JWT 署名鍵 / TLS 秘密鍵 / DB 接続文字列 / IdP Client Secret** | K8s Secret | **入る（避けられない）** |
| 環境変数 / Realm 名 / Pod 数 | ConfigMap / Deployment spec | **入る** |

→ Keycloak は **Stateless Pod + DB 分離アーキテクチャ**のため、**個人データ本体・CHD 本体は意図的に設計しない限り etcd に入らない**。「必須化」とは「現状の設計を意図的に維持し、誤って入れないようガードレールを敷く」運用。

#### 「必須化」のガードレール 5 階層

| レベル | 内容 | 工数目安 |
|---|---|---|
| **L1. 設計レベル** | K8s manifest レビュー時に「Secret / ConfigMap に PII / CHD が入っていないか」チェック | 設計段階のみ |
| **L2. CI/CD ゲート** | OPA Gatekeeper / Kyverno で「Secret 名前パターン・サイズ閾値超過」検出 | 初期構築 1 週間 |
| **L3. 静的解析** | Kubescape / Polaris で manifest スキャン | CI 統合 3 日 |
| **L4. 運用監査** | CronJob で定期 (週次 / 月次) に `kubectl get secrets -A` の中身を監査 + アラート | 初期構築 1 週間 |
| **L5. バックアップ制御** | Velero 等 K8s backup ツールが etcd snapshot を **国外 S3 に送らない**設定。Red Hat 側の cluster backup の保管先確認 | 設計時 + 監査運用 |

#### 達成可能 / 達成不可の区別

| 達成可能 ✅ | 達成不可 ❌ |
|---|---|
| ✅ 個人データ本体（users テーブル等）の etcd 非流入 | ❌ 鍵類（JWT 署名鍵等）の etcd 非流入 |
| ✅ CHD 本体の etcd 非流入（決済代行トークン化前提）| ❌ DB 接続文字列・TLS 秘密鍵の etcd 非流入 |
| ✅ ConfigMap への PII 直書き防止 | ❌ Deployment spec の環境変数名（PII カラム名想起可）の完全隠蔽 |

→ **「完全な etcd 非流入」は K8s アーキテクチャ上不可能**。現実的なラインは:

> **「個人データ本体・CHD 本体の非流入を維持し、不可避な鍵類は etcd KMS 暗号化 (Red Hat 管理) + BYOK (顧客 CMK) で保護」**

これは PCI DSS §3.6 / §3.7 + APPI 規則第 7 条「技術的安全管理措置」の範疇で評価される。

#### コンプライアンス影響による採用条件追加（まとめ）

| 規制 | ROSA HCP 採用時の追加要件 |
|---|---|
| **PCI DSS v4.0.1** | Red Hat AOC 年次取得 + §12.8 / §12.9 文書化 + **CHD 本体の etcd 非流入** + 鍵類への BYOK 適用 + ガードレール L1-L5 整備 |
| **APPI** | DPA に 28 条相当措置規定 + Red Hat SRE 越境アクセスログ取得 + **個人データ本体の etcd 非流入** + 委託先公表 + ガードレール L1-L5 整備 |
| **共通設計原則** | K8s Secret には鍵類のみ（個人データ本体は禁止）/ 個人データはアプリ DB（顧客 VPC 内）/ Aurora KMS は CMK (BYOK) / バックアップ保管先制御 |

→ これらの追加要件は **ROSA Classic では「Control plane も顧客 AWS アカウント内」** のため評価範囲が縮小される（Red Hat SRE 越境アクセスのみが残論点）が、**コスト差が解消されるほどではない**（Classic は HCP の 1.7 倍）。

### 11.5 ADR-056 の Decision への影響

本セクションの分析より、[ADR-056](../adr/056-rosa-adoption-decision.md) の **Default 不採用方針** は維持されるが、**採用時の追加要件**として以下を必須化する:

1. Red Hat との **DPA + Shared Responsibility Matrix** 締結
2. AWS Artifact から **Red Hat AOC 取得 + 年次更新運用**
3. **個人データ本体・CHD 本体の etcd 非流入を維持する設計レビュー + ガードレール L1-L5（OPA / Kubescape / 監査 CronJob / Velero 保管先制御）整備**
4. **Red Hat SRE（Red Hat 社員）の越境アクセスログ**の可視化要件確認 + 弊社オペレーター（国内）とは別評価
5. **規制要件発生時の再評価条件**に「コンプライアンス追加要件の整備コスト」を含める

→ ADR-056 の「採用再評価条件」と「Follow-up」セクションに反映。

---

## 12. 参考文献

### 公式ソース

| 資料 | URL |
|---|---|
| AWS ROSA トップ | https://aws.amazon.com/rosa/ |
| AWS ROSA Pricing | https://aws.amazon.com/rosa/pricing/ |
| AWS ROSA FAQs | https://aws.amazon.com/rosa/faqs/ |
| Red Hat ROSA 製品ページ | https://www.redhat.com/en/technologies/cloud-computing/openshift/aws |
| ROSA 公式 Documentation | https://docs.redhat.com/en/documentation/red_hat_openshift_service_on_aws/4 |
| ROSA Service Agreement | https://www.redhat.com/en/about/agreements |
| Red Hat KB 7033107 - RHBK Supported Configurations | https://access.redhat.com/articles/7033107 |
| Red Hat KB 7044244 - RHBK Subscriptions or Entitlements | https://access.redhat.com/articles/7044244 |
| Red Hat KB 7072950 - RHBK on 3rd-party Kubernetes | https://access.redhat.com/ja/solutions/7072950 |

### 本プロジェクト内 関連 doc

| 資料 | 用途 |
|---|---|
| [ADR-056 ROSA 採用判断](../adr/056-rosa-adoption-decision.md) | 本 doc を input として最終判断 |
| [rhbk-support-and-pricing.md](rhbk-support-and-pricing.md) | RHBK サポート対象（ROSA 含む）|
| [rhbk-vendor-inquiry.md](../requirements/rhbk-vendor-inquiry.md) | Red Hat / リセラ照会メール文面 |
| [keycloak-upstream-vs-rhbk.md](keycloak-upstream-vs-rhbk.md) | RHBK 採用判断フレーム |
| [ADR-015 RHBK validation deferred](../adr/015-rhbk-validation-deferred.md) | PoC で RHBK 検証先送り判断 |
| [ADR-006 Cognito vs Keycloak コスト損益分岐](../adr/006-cognito-vs-keycloak-cost-breakeven.md) | プラットフォーム選定コスト面 |
| [§C-2 プラットフォーム選定軸](../requirements/proposal/common/02-platform.md) | 選定軸全体 |

---

## 改訂履歴

- 2026-06-25: 初版作成。Red Hat / AWS 公式から ROSA Classic vs HCP / 価格モデル / SLA 99.95% / リージョン展開 / AWS サービス統合 / RHBK との関係 / 本 PoC からの移行考慮 / 採用判断フレームを統合。[ADR-056 ROSA 採用判断](../adr/056-rosa-adoption-decision.md) の input source として機能
- 2026-06-29: §11「コントロールプレーンに入る情報とコンプライアンス影響（PCI DSS / APPI）」追加。HCP モデルで Red Hat 所有 AWS アカウント内 etcd に乗る情報範囲（K8s Secrets / ConfigMaps）と乗らないもの（個人データ・CHD 本体）を区別し、PCI DSS v4.0.1 §3.6/§3.7/§7/§8/§10.2/§11/§12.8/§12.9/§6.4.3 + APPI 法第 25/27/28 条 + 規則第 7 条への影響を分析。採用時の追加要件 4 項目を整理し ADR-056 への反映ポイントを明示
- 2026-06-29 補足修正: §11.3 で「SRE 越境」を **Red Hat 社員（Red Hat ROSA SRE）の所在**であり弊社オペレーター（国内）は対象外と明示。Red Hat の "follow-the-sun" モデル（米国 + EMEA + APAC）の具体的所在を追記。§11.4 を「個人データ・CHD を etcd に入れない」の具体化と限界へ再構成 — Keycloak デフォルト設計で個人データは元々 etcd に入らないこと、ガードレール 5 階層 (L1 設計 / L2 OPA Gatekeeper / L3 Kubescape / L4 監査 CronJob / L5 Velero 保管先制御)、達成可能 (個人データ本体・CHD 本体非流入) と達成不可 (鍵類非流入) の区別を追加
