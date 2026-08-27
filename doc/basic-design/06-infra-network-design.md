# U6: インフラ・ネットワーク設計

作成日: 2026-07-23
ステータス: Draft v1（Wave 1）
前提: [01-architecture-baseline.md](01-architecture-baseline.md) **Baseline v1（P-01〜P-20）**
> **[P-19 ブランドユニット](01-architecture-baseline.md)**: ブランドユニット = IdP-KC アカウント側。**業務アプリは同居させない**（パスワードハッシュのブラスト半径隔離、E 判断）
> **[P-20 管理コントロールプレーンの実行形態](01-architecture-baseline.md)**: **idm-api + 非同期の糊 = Lambda**（Pod ネットワーク外）。ゆえに Keycloak Admin API へは**内部 NLB 経由**（`scheme=internal`・SG を Lambda SG 限定・server-TLS・アプリ層認証）。本書 §6.6.1 の設計はこの前提に立つ
上位文書: [00-basic-design-plan.md](00-basic-design-plan.md) U6

---

## 6.0 背景・なぜここで決めるか・スコープ

### 6.0.1 背景

U1 で実行基盤（P-01 ROSA HCP + RHBK Operator）、リージョン（P-15 東京 + 大阪）、クラスタトポロジ（P-17 IdP-KC 別 AWS アカウント・ROSA HCP × 2）、インターネット境界の管理主体（P-18 他組織管理の NW 監査 Acct）が凍結された。本書はこれらを物理構成（アカウント / VPC / クラスタ / DB / 経路 / サイジング）に落とす。

### 6.0.2 本書の最重要構造 — 2 部構成（P-18 由来）

P-18 により、インターネットの Inbound（CloudFront + WAF + ALB or NLB + Network Firewall）と Outbound（Network Firewall ドメインフィルタ）は**他組織管理**であり、我々は設定を実装できない（[ADR-039 v3 注記](../adr/039-centralized-network-account-edge-layer.md)）。したがって本書は次の 2 部で構成し、**混在させない**:

| 部 | 内容 | 我々の統制 |
|---|---|---|
| **A 部（§6.1〜§6.6）** | **自管理アカウント内設計** — Broker Acct / IdP-KC Acct / 監査 Acct の中身。我々が実装・保証する | 完全 |
| **B 部（§6.7）** | **他組織への要求仕様** — NW 監査 Acct / NW Acct に対して「要求として出す」項目（REQ-IN-* / REQ-OUT-*）。我々は要求と受入確認のみ可能で、実装は保証できない | 要求のみ |

この分離の帰結として、**セキュリティの生命線は「B 部が満たされなくても A 部単独で破られない」こと**（例: /admin 保護は WAF Deny〔B 部要求〕が外れても自管理側 Listener Rule 403〔A 部〕で成立、§6.6）。

### 6.0.3 スコープ / 非スコープ

- スコープ: 6 アカウント体系・クロスアカウント IAM / ROSA HCP クラスタ設計 × 2 / Broker ↔ IdP-KC クロスアカウント経路 / Aurora 設計 / サイジング（CPU・キャッシュ）/ /admin 保護 / 他組織要求仕様（Inbound・Outbound）
- 非スコープ: Keycloak 論理設計（Realm/Flow/SPI → U2）、DR フェイルオーバー手順詳細（→ U8、本書は物理配置のみ）、監視実装・IaC 分割（→ U9）、KMS Key Policy 詳細（→ U7）
- 本書確定後、[§C-7.2](../requirements/proposal/common/07-implementation-architecture.md)（旧 EKS / 5 アカウント / Auth Platform Acct 単一表記の SSOT）を本書の内容で一括改訂する（U1 §1.4 の残タスク）

---

# A 部: 自管理アカウント内設計

## 6.1 アカウント体系とクロスアカウント IAM

### 6.1.1 決定 D-U6-01: 6 アカウント体系の確定

ADR-039 の 5 アカウント体系を P-17（Broker / IdP-KC 分割）+ P-18（NW 監査 = 他組織）で読み替え、以下の **6 アカウント体系**で確定する（U1 §1.2 の図面化）:

```mermaid
flowchart TB
    subgraph EXT["🌐 インターネット / 顧客 IdP"]
        User[利用者ブラウザ]
        CIdP[顧客 IdP 1000+<br/>Entra/Okta/AD 等]
    end

    subgraph OTHER["═══ 他組織管理（B 部: 要求仕様の対象）═══"]
        subgraph NA["🟣 ネットワーク監査 Acct"]
            CF[CloudFront + WAF<br/>auth 用 / idp 用 / admin-SPA 用]
            EDGE[ALB or NLB（要確認）]
            NFWI[Network Firewall<br/>Inbound 検査]
            NFWO[Network Firewall<br/>Outbound ドメインフィルタ]
        end
        subgraph NW["🔷 ネットワーク Acct（他組織想定・要確認）"]
            TGW[Transit Gateway / DX / VPN]
        end
    end

    subgraph OURS["═══ 弊社管理（A 部: 本書で設計）═══"]
        subgraph AUD["🔵 監査 Acct"]
            OT[Org Trail / 監査ログ集約 S3<br/>Object Lock 7 年]
        end
        subgraph BRK["🟠 Broker Acct"]
            BALB[Internal ALB<br/>secret header 検証 + /admin 403]
            BKC[ROSA HCP #1<br/>Broker KC]
            BAUR[(Aurora Broker DB)]
            ITDR[ITDR / shadow 制御 Lambda]
        end
        subgraph IKC["🟡 IdP-KC Acct"]
            IALB[Internal ALB]
            IKCC[ROSA HCP #2<br/>IdP-KC]
            IAUR[(Aurora IdP-KC DB)]
            APPCRUD[同居アプリ<br/>ユーザ CRUD（U3）]
            IAPI[ユーザ管理 API 層<br/>ADR-038 Backend 同基盤]
        end
    end

    subgraph APPS["🟢 App Acct × N（各アプリチーム）"]
        AALB[Internal ALB + アプリ本体]
    end

    User --> CF --> EDGE --> NFWI --> TGW
    TGW --> BALB --> BKC
    TGW --> IALB --> IKCC
    BKC -.->|Back-channel<br/>PrivateLink（§6.3）| IALB
    BKC -->|token/JWKS Egress| NFWO --> CIdP
    BKC --> BAUR
    IKCC --> IAUR
    APPCRUD --> IAPI --> IKCC
    BKC -.->|イベントログ| OT
    IKCC -.->|イベントログ| OT
    AALB -.->|OIDC| BALB

    style OTHER fill:#f3e5f5,stroke:#7b1fa2,stroke-dasharray: 5 5
    style OURS fill:#fff8e1,stroke:#ff8f00
    style BRK fill:#fce4ec
    style IKC fill:#fffde7
    style AUD fill:#e3f2fd
    style APPS fill:#e8f5e9
```

> ⚠ 図の簡略化注意(2026-07-24): 上図の ALB 箱「secret header 検証 + /admin 403」は簡略表記であり、**主防御は /admin 403 + SG エッジ送信元限定、secret header は追加層**(REQ-IN-06 の重み付け参照)。**詳細版(全フロー ID 付き全体図 + ROSA 内部図)は [06a-network-flow-diagrams.md](06a-network-flow-diagrams.md) を参照**(2026-07-24 新設。同書 §A.3 で本書未記載のフロー 8 系統〔idm-api 公開入口 / Webhook Egress / HIBP / SES / ITDR 経路 6 / LDAPS / Canary / DNS 3 役割〕を追加検出 — SES 送信設計と Pod/Service CIDR 分離は §A.4 未決)。

| # | アカウント | 管理主体 | 主な内容 | 根拠 |
|---|-----------|---------|---------|------|
| 1 | 🟣 ネットワーク監査 Acct | **他組織（管理外）** | Inbound: CloudFront + WAF + ALB or NLB + Network Firewall / Outbound: Network Firewall ドメインフィルタ | P-18、ADR-039 v3 |
| 2 | 🔷 ネットワーク Acct | 他組織想定（**要確認**） | Transit GW / DX / Site-to-Site VPN | P-18、ADR-039 §A.3 |
| 3 | 🔵 監査 Acct | 弊社 | Org Trail / 監査ログ集約 S3（Object Lock 7 年）/ Security Hub / GuardDuty 集約 | ADR-039 §A.2 |
| 4 | 🟠 Broker Acct | 弊社 | ROSA HCP #1（Broker KC）+ Aurora + ITDR + shadow 制御 Lambda + Route 53 PHZ | P-17、ADR-033 |
| 5 | 🟡 IdP-KC Acct = ブランドユニット | 弊社 | ROSA HCP #2（IdP-KC）+ identity Aurora + authz系 Aurora + **idm-api（ブランド管理 API = Lambda: CRUD/権限/authz/projection）**。業務アプリは**非同居**（App Acct へ、PW ハッシュのブラスト半径隔離） | P-17、[ADR-033](../adr/033-keycloak-2tier-architecture.md)/[ADR-063](../adr/063-brand-unit-architecture.md)/[ADR-062](../adr/062-idm-api-execution-form-lambda.md) |
| 6 | 🟢 App Acct × N | 各アプリチーム | Internal ALB + アプリ本体（JWT 検証は VPC 内 JWKS 経路、ADR-012 パターン踏襲） | ADR-039 §A.2 |

補足:
- 旧「Auth Platform Acct」（§C-7.2.3）は Broker Acct / IdP-KC Acct に**分割済み**。§C-7 改訂は本書確定後（§6.0.3）。
- ADR-039 v2 の「アプリごと独立 CloudFront + WAF」の思想は維持するが、実装主体が他組織になったため **B 部の要求仕様として提示**する（§6.7.1）。

### 6.1.2 決定 D-U6-02: クロスアカウント IAM 原則

| # | 原則 | 内容 | 根拠 |
|---|------|------|------|
| 1 | **Broker ↔ IdP-KC 間に IAM クロスアカウント Role を作らない** | 両 Acct 間は §6.3 のネットワーク経路（OIDC federation HTTPS）のみ。IAM AssumeRole の相互許可は設けず、片方の侵害が他方の AWS 制御面に波及しない構造とする（P-17 の分離目的 = 権限分界・障害隔離を IAM 面でも貫徹） | P-17、ADR-033 |
| 2 | Pod → AWS リソースは **ROSA pod identity webhook + IRSA 方式** | クラスタ OIDC プロバイダを信頼する IAM Role + SA アノテーション。SA Token（短命・自動ローテーション）→ STS の**一時クレデンシャルは最長 1h で失効**（2026-07-24 表現修正） | ADR-041（2026-07-23 更新）、[research](research/rosa-hcp-adoption-research.md) #5 |
| 3 | クロスアカウントは「監査 Acct への書込」「CI/CD」「idmap 更新イベント」「ITDR イベント集約」「**削除 shadow 制御**」「**初回 sub 通知**」のみ | 下表の **8 経路**に限定（2026-08-06 制御プレーン 2 追加、ADR-063）。ワイルドカード Principal 禁止、`sts:ExternalId` or OIDC `sub` 条件必須 | ADR-041 §C.3（2 段階 STS チェーン維持） |
| 4 | 他組織 Acct との IAM 関係は**持たない** | NW 監査 Acct / NW Acct とは TGW Attachment / PrivateLink 等のネットワーク受渡しのみ。IAM 信頼は要求仕様にも含めない | P-18 |

**許可するクロスアカウント経路（8 経路。2026-08-06 制御プレーン 2 経路追加）**:

| 経路 | 方式 | 用途 |
|------|------|------|
| Broker Acct → 監査 Acct S3 | IRSA Role + バケットポリシー（`aws:SourceAccount` 限定、書込のみ・削除不可） | KC イベント / ALB ログ / Flow Log 集約 |
| IdP-KC Acct → 監査 Acct S3 | 同上 | 同上 |
| CI/CD（GitHub OIDC）→ Broker / IdP-KC 各 Acct | GitHub OIDC Federation → 各 Acct の Terraform Role（`sub` = リポジトリ/ブランチ条件） | IaC デプロイ（state は Acct ごと分離、U9） |
| App Acct → Broker Acct | **IAM 経路なし**（OIDC/JWKS は HTTPS のみ）。Token Exchange 等もアプリ層プロトコルで完結 | ADR-041 の境界 2b/2c |
| IdP-KC → Broker | **EventBridge クロスアカウントイベント**（イベントバスへの PutEvents のみ許可） | `idmap` 更新（D1 SCIM Facade 発、案 i — U3 D3-11。Layer A FK の一元性を Broker Acct 側で維持） |
| IdP-KC → Broker | **EventBridge PutEvents（itdr-bus への PutEvents のみ許可）** | **ITDR イベント集約**（U7 D-U7-04。IdP-KC 側ローカル PW ログインイベントを Broker Acct の Risk Engine へ送出。経路 5〔idmap〕と同一方式のため増分リスク小） |
| **IdP-KC(ブランド) → Broker** | **EventBridge PutEvents（削除 shadow bus）** | **削除伝播**（2026-08-06、[ADR-063](../adr/063-brand-unit-architecture.md) / U3 D3-17）: `user.deprovisioned {sub, brand_id}`（idm-api の **outbox リレー**発 → Broker shadow 制御 Lambda が Broker shadow 無効化）。**経路 5/6 と同一方式**（IdP-KC→Broker PutEvents） |
| **Broker → ブランド(IdP-KC)** | **EventBridge PutEvents（初回 sub 通知 bus）** | **authz スタブ生成**（2026-08-06、[ADR-063](../adr/063-brand-unit-architecture.md) / U3 D3-16）: 初回ログイン時に Broker が `sub` をブランドへ通知（federated の authz 行生成用）。**EventBridge の新方向 = Broker→IdP-KC**（フェデ backchannel PrivateLink〔D-U6-06〕とは別レイヤ） |

---

## 6.2 ROSA HCP クラスタ設計 × 2

### 6.2.1 決定 D-U6-03: クラスタ構成

| 項目 | Broker クラスタ（#1、Broker Acct） | IdP-KC クラスタ（#2、IdP-KC Acct） | 根拠 |
|------|------|------|------|
| 形態 | ROSA HCP（Classic 不採用: 新規作成期限公式化） | 同左 | P-01、[research](research/rosa-hcp-adoption-research.md) #1 |
| SLA | 99.95%（P-04 の 99.9% を上回る） | 同左 | research #1 |
| リージョン | 東京 ap-northeast-1（+ 大阪は**コールド DR** = 平時 ROSA なし・Aurora Global Secondary のみ、§6.2.4、2026-07-30 D-18） | 同左 | P-15 |
| Multi-AZ | **3 AZ**。HCP の Machine Pool は AZ 単位のため **AZ ごとに 1 Machine Pool × 3** を作成 | 同左 | P-04/P-05 |
| KC 配布 | RHBK Operator（OperatorHub、追加サブスク不要） | 同左 | research #3 |
| Control Plane | **Red Hat サービスアカウント内**（API server × 2 + etcd × 3、3 AZ 冗長）。顧客 VPC には出ない。Worker → CP は顧客 VPC 内の **PrivateLink Endpoint** 経由。CP のサイジングは Worker 数に応じ **Red Hat が自動管理**（顧客関与なし） | 同左 | 2026-07-23 ユーザー検討（[research note](research/rosa-hcp-machine-pool-egress-notes.md)） |
| Ingress | デフォルト IngressController を **Private / NLB** で作成（HCP 新規は CLB でなく **NLB が既定**）。**「platform 用 Private NLB」と「アプリ選択公開用」は追加 IngressController で分離**（OpenShift 4.14+ で HCP もサポート、Red Hat Cloud Experts〔MOBB〕推奨パターン。**ただし追加 IC の LB は Red Hat 管理外の顧客管理リソース扱い** — HCP サービス定義は default IC の LB のみ RH 管理、2026-07-24 検証追記）。前段に自管理 Internal ALB を置き L7 制御（§6.6 の 403 ルール、secret header 検証）を ALB 側で実施 | 同左 | research #1、ユーザー検討、ADR-010 の Private 原則 |
| ネットワーク | 各 Acct に専用 VPC（Private Subnet × 3 AZ + VPC Endpoint 群: S3 / ECR / Logs / KMS / Secrets / STS）。**CIDR は Broker / IdP-KC / 社内 NW / 顧客 AD 系と重複しないよう採番**（§6.3 PrivateLink 採用により必須ではないが、TGW 転換余地を残す） | 同左 | ADR-010 |
| **サブネット 4 層設計（2026-07-24 追記、2026-08-17 /23 具体化、**2026-08-27: 本行は [VPC-K（認証製品側）](#625-決定-d-u6-19-2-ネットワーク分離構成2026-08-27-本文化--c-9)の記述**）** | AZ ごとに用途別 4 層で採番: **① TGW Attachment 用 /28** ② **ALB 専用 /27**（Internal ALB は専用サブネットに分離 — スケール時の ENI 枯渇防止）③ **Node 用 /26（内部 NLB＋Worker＋Infra）**（**OVN-Kubernetes のため Pod 数でなくノード数ベースで採番**。Failover 後の東京同等スケール〔KC Pool max 9/**29**〔2026-08-27 是正〕+ infra〕を収容。**/26=59 usable に対し IdP-KC 側は 29÷3AZ ≈ 10 ノード/AZ + infra 1 + 内部 NLB の ENI 3 + Lambda ENI 6 ≈ 20 → 約 3 倍ヘッドルーム**（旧「8 倍」は max 18 前提）。**フェデ比率がさらにローカル寄りへ振れると /26 が効き始める**ため、ローカル 100%（58 ノード = 20/AZ）を想定する場合は Node 層を /25 へ拡張すること）④ **Aurora 用 /28**。→ **AZ あたり /25、3 AZ で VPC = /23（+/25 予備）に収まる**（[research 2026-08-17](research/rosa-vpc-ip-conservation-2026-08-17.md)）。**CIDR はクラスタ install 後に変更不可のため事前確定必須**（大阪側も同サイズで確保、§6.2.4）。~~**（2026-08-06 追記）層③は idm-api + shadow 制御 + 非同期の糊 Lambda の VPC ENI アタッチ先も兼ねる**~~ → **2026-08-27 無効化（C-9）: 2 ネットワーク分離の採用により、これらは [VPC-M の関数用サブネット](#625-決定-d-u6-19-2-ネットワーク分離構成2026-08-27-本文化--c-9)へ移動**（[ADR-062](../adr/062-idm-api-execution-form-lambda.md) Decision 2）。層③に残るのは worker と内部 NLB 2 本のみ | 同左 | 2026-07-24 ユーザー検討（[research note](research/rosa-hcp-machine-pool-egress-notes.md)）、2026-08-06 ADR-062、2026-08-17 /23 具体化 |
| **Egress 形態（要決定 O-10）** | 通常構成では **AZ ごとに Public Subnet + NAT Gateway が必須**（Worker の registry.redhat.io / quay / OLM / STS 等への outbound）。**案 A**: NAT GW → 他組織 NFW ドメインフィルタ（P-18 接続）/ **案 B**: `zero_egress:true`（ECR ミラー化）+ **TGW で他組織 Outbound 専用経路へ** — **NAT 不要となり P-18（自 Acct に NAT を置かず他組織アウトバウンド経由）と製品仕様が噛み合うため積極検討**。§6.7.3 参照。**（2026-08-17 追記）本決定は VPC IP 節約策とも連動**: CGNAT 退避／PrivateLink で「ノード CIDR を Transit から隠す」場合、集中 egress（NFW = L3 到達要）と完全隠蔽は **案 B（zero_egress + VPC 内 Interface/Gateway Endpoint）でこそ両立**する（[research 2026-08-17](research/rosa-vpc-ip-conservation-2026-08-17.md)） | 同左 | 2026-07-23 ユーザー検討、2026-08-17 IP 節約連動 |

- **⚠ HCP には専用 Infra Node が存在しない**（Classic の 3 Infra Node は廃止）: ingress **router pod** / in-cluster monitoring(Prometheus) / image registry（デフォルト配備）は **Worker Node に同居**する。**（2026-07-24 公式検証で訂正）OLM 本体（olm/catalog-operator・カタログ Pod）と Ingress Operator・ネットワーク系 Operator は Red Hat 側 Hosted Control Plane 内で稼働**し、Worker 上に載るのは **OperatorHub からインストールした Operator（RHBK Operator 等）とそのワークロード**。KC と infra 系の食い合いを防ぐため、§6.2.2 で **Machine Pool を役割分離**する（2026-07-23 ユーザー検討による設計変更）。
- **接続 3 系統の分離**: ①ユーザ（フロントチャネル）= 他組織エッジ → 自管理 Internal ALB → IngressController NLB → KC Pod / ②Red Hat SRE = **backplane 経由の JIT アクセス（短命トークン・MFA・全操作監査、PrivateLink 経由で CP 管理。昇格は 2h 限定・承認制の Red Hat 側手続。顧客の /admin とは完全別経路。※「break-glass credential」は HCP では顧客側機能の名称のため SRE アクセスの呼称に使わない — 2026-07-24 用語修正）**/ ③顧客側メンテ = SSM ポートフォワード（D-U6-12）。
- **SCIM Facade の配置**: **2026-08-06 更新 — O-9（管理コントロールプレーン実行形態）は Lambda で確定（[ADR-062](../adr/062-idm-api-execution-form-lambda.md)）**。SCIM Facade も idm-api（ブランド）・shadow 制御・非同期の糊と同じ Lambda substrate（層③）へ寄せる（旧「default（infra）Pool 常駐」から変更、§6.8.1 O-9）。受信経路は §6.7.1 REQ-IN-09（scim-broker / scim-idp、API GW → Lambda）。レイテンシ/読取 p99 は G-SCIM で実測。

- **単一 VPC 集約の受容条件と分離トリガー（2026-08-18、[research](research/single-vpc-consolidation-risk-2026-08-18.md)）**: 現行は idm-api Lambda ENI をクラスタ VPC の層③に同居させる**単一 VPC（A 案）**だが、**AWS SEC05-BP01 は「全リソースを単一 VPC に作る」を High リスクのアンチパターン**とする（機微度で境界を サブネット→VPC→アカウント へ格上げせよ）。8 リスク（横展開/ブラスト半径・PrivateLink 単方向喪失・機微データ comingling・監査境界肥大・ROSA/SRE 隣接・DR 結合・IP 結合・VPC 障害ドメイン）を出典付きで評価。**A 案受容の必須要件**: ① east-west 最小権限（**identity Aurora SG＝KC Pod のみ / idm-api は Admin API 経由のみ**）② Flow Log+GuardDuty で東西横展開検知 ③ data perimeter（RCP/SCP）④ 層順の CI 機械検査。**分離トリガー**（規制ブランド/高保証/SRE 隔離強化/構造的ブラスト半径縮小）が立てば **2 VPC 分離（Keycloak/identity VPC ＋ 管理/authz VPC、idm-api は 1 本のまま管理 VPC・Admin API へ PrivateLink 単方向）→ さらに authz 別アカウント（[ADR-063 オプション B](../adr/063-brand-unit-architecture.md)）** へ格上げ。**決定（2026-08-18）= 2 VPC 分離（B 案）採用**（SEC05-BP01 アンチパターン回避＋ブラスト半径を構造で縮小）。**→ 構成としての本文は [§6.2.5 D-U6-19](#625-決定-d-u6-19-2-ネットワーク分離構成2026-08-27-本文化--c-9)（2026-08-27 本文化）**。**VPC-K（Keycloak/identity＋identity Aurora〔PW ハッシュ〕＋Admin/OIDC 内部 NLB）** と **VPC-M（idm-api Lambda〔1 本〕＋authz Aurora＋IF Endpoint、TGW 非 attach・CGNAT 可）** に分割。**idm-api → authz Aurora＝同一 VPC 直結／→ Keycloak Admin API＝PrivateLink 単方向（EPS-Admin）／identity Aurora は VPC-K で KC Pod のみ到達（idm-api はルートも SG も持たない）**。サブネット×リソース×接続×SG×PrivateLink の**構成図用 詳細は [research 2026-08-18](research/brand-unit-2vpc-topology-2026-08-18.md)**。※現行 D-U6-11 の「idm-api 侵害時 Admin API 到達は in-cluster と引き分け」評価は **Admin API 経路限定**で、identity/authz Aurora・クラスタ網への横展開全体は評価外だった点に注意（B 案でこの残リスクを構造的に解消）。
- **VPC IP 節約と CIDR 隠蔽（2026-08-17、[research](research/rosa-vpc-ip-conservation-2026-08-17.md)）**: 「ROSA が大きな CIDR を食う」は EKS VPC CNI の話で **ROSA は OVN オーバーレイ＝ Pod は VPC IP を消費しない**（routable を食うのはノードのみ、マルチ AZ 最小 /24）。**Transit-routable に本当に晒す必要があるのは「インバウンド ALB ＋ TGW attachment」だけ**（Node/Aurora/Interface Endpoint はクラスタ内〔VPC 内〕で完結し TGW 到達不要）。**構成: Broker 1 VPC・IdP-KC 1 VPC・編集系〔idm-api＋管理 SPA〕別 VPC**、各 /23（上表 4 層×3AZ）。**routable の縮小策 2 段**: **(既定) そのまま**（Broker/IdP = /22 相当を Transit へ、現行 P-18 経路）/ **(節約案 B) ノード・Aurora・Endpoint を secondary CGNAT CIDR（`100.64.0.0/16`〔OVN 予約〕は回避）へ退避し Transit へは ALB の極小 CIDR のみ広告**（1 VPC のまま・追加コストほぼゼロ、2 クラスタ＋別 VPC＋将来ブランドが単一 /24 に収まる余地）。**PrivateLink 分割（front/ROSA 2 VPC）** は ② を完全隔離アイランドにしたい場合の上位オプション（[D-U6-06](06-infra-network-design.md) と同方式、TGW から見えるのは公開 NLB のみ＝クラスタ網スキャン不可）。**編集系別 VPC → IdP-KC Admin API（内部 NLB）は PrivateLink 到達**。いずれも **egress を zero_egress（O-10 案 B）で固めるのが前提**（PrivateLink 単方向ゆえノード外向きは別経路、集中 egress と完全隠蔽は zero_egress で両立）。**未確認**: ROSA のノードサブネット CGNAT 公式サポート／ノード実 ENI 数（要 Red Hat 確認・PoC）。

### 6.2.2 決定 D-U6-04: Machine Pool・インスタンスタイプ案（2026-07-23 改訂: 役割分離 2 Pool 構成）

Tier ごとに CPU プロファイルが 10-30 倍異なる（Broker = JWT/SAML 署名系、IdP-KC = Password Hashing 支配、[sizing-guide §5](../reference/keycloak-cpu-bottleneck-sizing-guide.md)）ことに加え、**HCP には Infra Node が無く infra 系が Worker に同居する**（§6.2.1）ため、**クラスタごとに「KC 専用 Pool」と「default（infra）Pool」の 2 系統 Machine Pool** を設計する。

**Pool 役割分離（両クラスタ共通）**:

| Pool | テイント | 載せるもの | スケール特性 |
|------|---------|-----------|-------------|
| **default（infra）Pool** | なし（**ROSA はテイントなし Pool〔レプリカ 2 以上〕が最低 1 つ必須** — 公式制約。rosa CLI 1.2.26+ なら default pool 自体へのテイントも可、KB 7032223） | ingress router pod / in-cluster monitoring（Prometheus。**UWM は新規クラスタで既定無効 → KC メトリクス scrape には Day-2 有効化必須**、2026Q1 仕様変更）/ image registry / **OperatorHub 導入 Operator（RHBK Operator 等。OLM 本体は RH 側 CP）** / **SCIM Facade** / **Fluent Bit Aggregator**（マスキング Filter 集中、U7 §7.3.1） | **準静的**: 負荷でなくクラスタ規模・監視量（1000+ IdP の時系列カーディナリティ）で手動 or 緩い Autoscale。Prometheus メモリを先に見積もり固定気味に確保 |
| **keycloak 専用 Pool** | `dedicated=keycloak:NoSchedule` + nodeSelector/toleration | KC Pod のみ | **動的**: HPA（CPU/予兆）→ Pending → Cluster Autoscaler が本 Pool にのみノード追加。**KC のバーストが infra を巻き込まない** |

- 分離しない場合のリスク: KC の HPA バーストが同居 infra と CPU/メモリを食い合い、**監視が飛ぶ・ingress が詰まる**（router は既定 replica 固定、monitoring は Pod 数で自動増しない）。10M MAU + 1000+ IdP では顕在化必至。
- スケールの 3 主体は独立: **CP = Red Hat 自動 / Worker = Machine Pool 単位（手動 or Autoscaler） / Pod = HPA**。連鎖（HPA → Pending → Autoscaler）はするが制御は別。

| 項目 | Broker クラスタ | IdP-KC クラスタ |
|------|------|------|
| Machine Pool 構成 | `kc-az1/2/3`（テイント付き）+ `default-az1/2/3`（infra） | 同左 |
| KC Pool インスタンス（第一候補） | **c7g.xlarge（4 vCPU/8 GB）** — Phase 1 ベースライン | **c7g.xlarge（4 vCPU/8 GB）** — Phase 1 ベースライン |
| KC Pool スケール上限タイプ | c7g.2xlarge — **サイズ変更 = EC2 作り直しのため、ピーク帯用 c7g.2xlarge Pool を事前に別 Machine Pool として定義**しておき必要時に台数を増やす（Blue/Green、稼働中の作り直し回避） | 同左 |
| KC Pool ノード数（東京） | min 3（AZ × 1）/ **max 9** | min 3 / **max 29**（2026-08-27 是正: 旧 18。フェデ比率 50:50 への改訂で必要 vCPU が 135 → 225 に増加、§6.5.3） |
| **default（infra）Pool** | **c7g.large × 2〜3/クラスタ**（monitoring 規模で増減、準静的） | 同左 |
| 代替（Graviton 非対応時） | c7i.xlarge | m7i.xlarge（Argon2id メモリ余裕） |
| KC Pod リソース | **少数大型 Pod モデル = 1 ノード 1 KC Pod**（下記 6.2.2a）。requests はノード割当可能量のほぼ全量（c7g.xlarge 期 = 3 vCPU / 6 GB、c7g.2xlarge 期 = 6.5 vCPU / 13 GB）、`MaxRAMPercentage=60-70`、G1GC | 同左 + Argon2id メモリ余裕（§6.5.4） |

- 根拠: インスタンス候補と 3y RI 単価は [sizing-guide §8](../reference/keycloak-cpu-bottleneck-sizing-guide.md)。c7g（Graviton3）は Broker/IdP-KC とも第一候補。**（2026-07-24 検証済み）ROSA HCP の Graviton/arm64 Machine Pool は 2024-07-24 以降作成クラスタで公式対応済み** — 残る確認は **RHBK Operator の arm64 イメージ提供**と**東京/大阪の c7g 在庫**のみ（未対応なら c7i/m7i 系へ差替、コスト +15-20%）→ §6.8 未決事項。
- ワーカー最小数: HCP はクラスタあたり最小 2 ノードだが、Multi-AZ 要件（P-04）により **KC Pool 最小 3（AZ × 1）を下限**とする。§6.5 のノード数試算（Broker max 9 / **IdP-KC max 29**〔2026-08-27 是正、フェデ 50:50〕）は **KC Pool の数値**であり、infra Pool は別建てで加算（§6.2.3）。
- ノードのスケールアウト/イン・バージョンアップは**ノード完全置換のローリング**（**既定 maxSurge=1 / maxUnavailable=0** — 1 台余分に立ててから抜く。pool ごとに変更可、2026-07-24 公式検証で既定値訂正）+ drain で実施。**PDB が尊重されるのは pool の `node-drain-grace-period`（最大 30 分等の設定値）の範囲内で、超過時は drain が強行される** — KC Pod の PDB + レプリカ配置 + 猶予時間の 3 点が揃って無停止が成立する。
- **Machine Pool 名の実体（2026-07-24 注記）**: HCP はクラスタ作成時にサブネットごとの pool（`workers` / `workers-2`…）を自動作成する。本書の `default-az1/2/3` / `kc-az1/2/3` は論理名であり、IaC 上は「自動作成 pool（infra 役）+ 追加作成 pool（KC 役）」に対応付ける。
- **アップグレード順序制約（U9 引き渡し）**: CP と Machine Pool は独立アップグレードで **CP を先行**、pool は CP から 2 マイナー版以内に維持（U9 §9.6 の KC 昇格ゲートと合わせて Runbook 化）。将来オプション: **AutoNode（Karpenter v1.9 ベース、2026Q2 に HCP 対応）**は Pool 事前定義不要の動的プロビジョニング — 本設計の準静的 infra + 動的 KC には従来型 Autoscaler が適合するため Phase 1 不採用、Phase 2 で再評価。

#### 6.2.2a 決定 D-U6-18: 少数大型 Pod モデル（2026-08-27 新設 — Pod 数定義の不整合是正）

**背景（是正の経緯）**: 本書には Pod 数の記述が 3 箇所あり、定義が揃っていなかった。§6.2.2 は **ノード数**（max 9 / 18）、[§6.4.2](#642-決定-d-u6-08-jdbc-ping-前提のコネクション設計) は **「最大 Pod 数 27（Broker 9 + IdP-KC 18）」= ノード数の合算を Pod 数として流用**、[§6.5](#65-サイジングmau-10m-上限--フェデ比率-5050--argon2id) は **vCPU 数**（51 / 135）で記述していた。「27」という値自体は **1 ノード 1 Pod を暗黙に仮定すれば正しい**が、同じ §6.2.2 の「KC Pod リソース requests 2 vCPU」は **1 ノードに複数 Pod が載る前提**であり、両者が矛盾していた。**モデルを明文化して解消する。**

**採用: 1 ノードに KC Pod を 1 個だけ載せる（少数大型 Pod モデル）**

| 観点 | 少数大型（採用） | 多数小型（不採用） |
|---|---|---|
| **クラスタ内の状態共有コスト** | メンバー数が少なく、状態複製の相手が減る | **メンバー数の増加に対して複製の組合せが急増**し、キャッシュ同期が支配的になる |
| **DB 接続数** | Pod 数 × プール 30 で線形 → **ピークでも 1,140 本**（下表） | 同じ vCPU 総量でも Pod 数が 3 倍 → **3,400 本超で Writer 上限に接触** |
| **JVM の固定費** | ヒープ・メタスペース・JIT の固定オーバーヘッドが Pod 数分だけで済む | Pod ごとに固定費が乗り、実効効率が落ちる |
| **暖機** | 台数が少なく、スケールアウト時の暖機対象が限定的 | 暖機待ちの Pod が増え、スケールアウトの応答が鈍る |
| **AZ 分散** | ノード = Pod なので **AZ 分散がノード配置と一致し単純** | Pod の AZ 偏りを別途 topologySpreadConstraints で制御する必要 |

- **requests の決め方**: ノード全 vCPU から DaemonSet・kubelet・OS 分（約 1 vCPU / 2 GB）を控除した残り全量を KC Pod の requests とする。c7g.xlarge 期は **3 vCPU / 6 GB**、ピーク帯の c7g.2xlarge 期は **6.5 vCPU / 13 GB**。
- **`dedicated=keycloak:NoSchedule` テイント（§6.2.2）と併用**することで「1 ノード 1 Pod」が構造的に保証される（infra 系が同じノードに入らない）。
- **HPA は Pod 数ではなくノード数を動かす**: HPA が Pod を増やしても収容ノードが無ければ Pending → Cluster Autoscaler がノードを追加、という連鎖で **Pod 数とノード数が 1:1 で追従**する。よって §6.5 の「必要 vCPU → ノード数」の試算が **そのまま Pod 数**になる。

**Pod 数と DB 接続数の確定表（本書内でこの値を正とする）**

| 時点 | Broker Pod（= ノード） | IdP-KC Pod（= ノード） | 合計 Pod | Broker 接続 | IdP-KC 接続 |
|---|---:|---:|---:|---:|---:|
| **Phase 1 ベースライン**（c7g.xlarge × 3、初回 100 万 MAU 下限） | 3 | 3 | **6** | 90 | 90 |
| **初回リリース上限**（500 万 MAU 上限、§6.5） | 4 | 15 | **19** | 120 | 450 |
| **10M ピーク上限**（フェデ 50:50） | 9 | **29** | **38** | 270 | **870** |

> ⚠ **旧記述「最大 Pod 数 27」は 10M ピークの値としては過小**だった（フェデ比率 70/30 前提の IdP-KC 18 ノードに基づく）。**50:50 への改訂（[§6.5.1](#651-前提と暫定値の明示)）で IdP-KC は 29 ノード = 29 Pod** となる。§6.4.2 の接続見積もこれに合わせて改訂済み。

---

#### 6.2.2b 決定 D-U6-17: ノードの時刻同期（2026-08-24 新設）

**背景**: 本設計 10 冊に**時刻同期の要件が一箇所も無かった**（[U5 §5.2.1](05-token-session-authz-design.md) の「RP 検証側 clock skew ≤ 60 秒」はアプリへの要求であって基盤の同期要件ではない）。暗黙の前提のまま置くと、**時刻ずれが「全ログイン失敗」として突然顕在化する**にもかかわらず、誰の責任範囲かも許容値も定義されていない状態になる。

**採用**: 両クラスタ（Broker / IdP-KC）の全ノード・Aurora・Lambda・監査基盤の時刻同期を **Amazon Time Sync Service**（リンクローカル `169.254.169.123` / PTP 対応インスタンスでは `169.254.169.253`）に統一し、**許容ずれを ±1 秒以内**とする。

| 対象 | 同期方式 | 責任 |
|---|---|---|
| ROSA worker ノード（EC2 / RHCOS） | chrony → Amazon Time Sync Service | **Red Hat SRE 管理領域**（ノード OS 設定）。**既定でこの構成であることの確認が必要**（→ 未決） |
| ROSA Control Plane | 同上（HCP = Red Hat 管理） | Red Hat |
| Aurora / Lambda / API GW | AWS マネージド（利用者設定不可） | AWS |
| Break-Glass 用踏み台 | chrony → Amazon Time Sync Service | 弊社（IaC で明示） |

**時刻ずれが効く範囲と効かない範囲（誤解の多い点）**:

| 影響 | 効くか | 理由 |
|---|---|---|
| **SSO セッション TTL**（Idle 1h / Max 24h、P-09） | ❌ **効かない** | 各サーバが**自分の時計だけで完結して**計算し、相手の時刻を参照しないため。Broker と IdP-KC がずれていても各々の中では正しい |
| ID Token の `exp` / `iat` 検証（2-tier 間・顧客 IdP 間） | ✅ 効く | 許容は IdP 設定の Allowed clock skew（[U2 §2.2.2](02-keycloak-logical-design.md) = 30 秒） |
| アプリの JWT 検証 | ✅ 効く | RP 側 ≤ 60 秒（U5 §5.2.1） |
| **`auth_time` / `max_age`** | ✅ **強く効く** | AAL3 の `max_age=300` は**5 分幅しかない**。1 分ずれれば余裕の 20% を失う |
| **TOTP** | ✅ **最も敏感** | **30 秒刻み**。IdP-KC 収容ユーザの MFA に直結 |
| 監査ログの相関 | ✅ 効く | Broker / IdP-KC / SSM のイベントを時系列突合できなくなる。**インシデント調査で効く** |
| Kerberos（LDAP 連携時） | ✅ 効く（5 分以内必須） | Phase 1 スコープ外（[keycloak-ldap-configuration-notes §Clock Skew](../common/keycloak-ldap-configuration-notes.md)） |

- **DR 整合**: 東京・大阪とも同一の Amazon Time Sync Service に同期するため、**リージョン切替で時刻基準が変わらない**（U8 §8.5 の再認証設計に影響しない）。
- **監視**: 時刻ずれは**「沈黙」型**（ずれ始めても全て正常に動き続け、閾値を超えた瞬間に全ログインが失敗し、症状は「原因不明のトークン検証エラー」としか出ない）。よって存在確認型の監視を [U9 §9.1.2 #15](09-operations-observability-design.md) に設置する。
- **未決（O-12）**: **ROSA worker の chrony 設定が Amazon Time Sync Service を向いていることの確認**、および**ずれた場合の是正が Red Hat SRE / 弊社どちらの作業か**の責任分界。ノード OS は Red Hat 管理領域のため**弊社が直接設定できない可能性がある** → [Red Hat 照会 RH-C 群](../requirements/redhat-inquiry/00-plan.md)に追加。

---

### 6.2.3 決定 D-U6-05: コスト表（HCP cluster fee 前提、東京 2 + **大阪は平時 ROSA なし = コールド DR**）

> **2026-07-30 D-18 転換**: DR をコールド化（U8 D-U8-14）。**大阪の常時 ROSA クラスタ（旧パイロットライト 2 × $301 = $602/月）を廃止**し、大阪の平時コストは Aurora Global Secondary ストレージ + バックアップ/クロスリージョンスナップショット + ECR ミラーのみ（データ層のみ常時、コンピュートは被災時にオンデマンド再構築）。下表の大阪パイロットライト 2 行は旧・参考。

前提: HCP cluster fee $0.25/h ≈ $182.5/月/クラスタ、Worker ROSA fee $0.171/4vCPU/h（3y 契約 55% 引はパートナーチーム経由・**見積未取得**）、EC2 は 3y RI 単価（[sizing-guide §8](../reference/keycloak-cpu-bottleneck-sizing-guide.md)）。**概算 ±30%、Phase 1 ベースライン（c7g.xlarge × 3/クラスタ）時点**。

| クラスタ | HCP fee | EC2（3y RI） | ROSA Worker fee（3y 55% 引仮定） | 小計/月 |
|---------|--------:|------------:|-------------------------------:|--------:|
| 東京 Broker（KC Pool c7g.xlarge × 3） | $182.5 | $186 | $169 | **$538** |
| 東京 Broker infra Pool（c7g.large × 3） | — | $93 | $84 | **$177** |
| 東京 IdP-KC（KC Pool c7g.xlarge × 3） | $182.5 | $186 | $169 | **$538** |
| 東京 IdP-KC infra Pool（c7g.large × 3） | — | $93 | $84 | **$177** |
| ~~大阪 Broker パイロットライト~~ **廃止（2026-07-30 D-18、平時 ROSA なし）→ 常時 $0**（被災時オンデマンド再構築） | ~~$182.5~~ | — | — | **$0** |
| ~~大阪 IdP-KC パイロットライト~~ **廃止（2026-07-30 D-18）→ 常時 $0** | ~~$182.5~~ | — | — | **$0** |
| **ROSA 合計（4 クラスタ）** | $730 | $682 | $618 | **≈ $2,032/月** |

- **2026-07-23 改訂**: HCP に Infra Node が無い帰結として infra Pool（東京 × 2 クラスタ分 ≈ +$354/月）を別建て加算（旧試算 $1,678 → **$2,032**）。大阪パイロットライトは最小 2 ノード(テイントなし)が infra を兼ねるため増分なし。
- **2026-07-24 修正（大阪 KC Pool の不整合解消）**: KC Pod は `dedicated=keycloak` toleration + nodeSelector を持つ（§6.2.2）ため、**テイントなし infra ノードだけの大阪では Failover 時に KC Pod がスケジュール不能**になる。よって大阪にも **KC 専用 Machine Pool（labeled/tainted、min 0・平時ノード 0 台 = コスト増なし）を事前定義**し、Failover 時に 0 → 3+ へスケールする。U8 §8.5 の「replicas 0→3」「min 0 スケールアップ用プール」はこの KC 専用 Pool を指す。
- クラスタ 1 本の固定増分 ≒ +$500〜680/月という research #7 の見立てと整合。**P-17（別 Acct 2 クラスタ + DR 側 2）の増分コストはユーザー凍結済みの許容範囲**。
- 大阪はパイロットライト（Warm Standby 最小、ADR-051）: 平時 2 ノード + Failover 時に Machine Pool を東京同等へスケールアップ（RB-DR-03 相当、U8）。
- 10M MAU ピーク帯までスケールした場合のワーカー増分は §6.5 の vCPU 試算から別途線形加算（Broker +$350〜1,000/月、IdP-KC +$500〜2,500/月程度。B-BROK-1 確定後に再計算）。
- Aurora / ALB / VPC Endpoint 等は §6.4 と ADR-051 §G を参照（DR 込み Aurora ≈ $2,280/月 × 2 DB 系統ベース）。

#### 6.2.3a 時点別コスト再計算（2026-08-27 新設 — C-1.3、フェデ 50:50 × MAU 時点分離）

上表は **c7g.xlarge × 3 のベースライン固定**での試算であり、[§6.5](#65-サイジングmau-10m-上限--フェデ比率-5050--argon2id) の改訂で**ベースラインが成立する範囲が「100 万 MAU かつ TPS 下限」に限られる**ことが判明したため、時点別に再計算する。

**単価**（上表から逆算）: c7g.xlarge ≈ **$118/ノード/月**（EC2 3y RI $62 + ROSA Worker fee $56）、c7g.2xlarge ≈ **$237/ノード/月**。HCP cluster fee $182.5/クラスタ/月、infra Pool 2 クラスタ計 $354/月。

| 時点 | Broker ノード | IdP-KC ノード | KC Pool 費 | HCP fee | infra Pool | **ROSA 計/月** |
|---|---|---|---:|---:|---:|---:|
| **ベースライン**（100 万 MAU・TPS 下限） | c7g.xlarge × 3 | c7g.xlarge × 3 | $708 | $365 | $354 | **≈ $1,427** |
| **初回 100 万 MAU・上限** | c7g.xlarge × 3 | c7g.2xlarge × 3 | $1,065 | $365 | $354 | **≈ $1,784** |
| **初回 500 万 MAU・下限** | c7g.xlarge × 3 | c7g.2xlarge × 5 | $1,539 | $365 | $354 | **≈ $2,258** |
| **初回 500 万 MAU・上限** | c7g.2xlarge × 4 | c7g.2xlarge × 15 | $4,503 | $365 | $354 | **≈ $5,222** |
| **10M ピーク上限** | c7g.2xlarge × 9 | **c7g.2xlarge × 29** | $9,006 | $365 | $354 | **≈ $9,725** |

- **初回リリース時点だけで $1,427 〜 $5,222 の 3.7 倍幅**がある。**幅を決めるのは MAU 見込みと TPS 見込みとフェデ比率の 3 点**（いずれも B-BROK-1 と P-02 の確定待ち）。**調達判断はこの 3 点が揃うまで確定できない**。
- 旧試算 **$2,032/月**は「両クラスタ c7g.xlarge × 3」前提であり、**上表のベースライン $1,427 と一致しない**（旧試算は大阪パイロットライト廃止前の infra 計上差）。**本表を正**とする。
- 10M ピークは**常時ではなくピーク帯のみ**の値。Machine Pool の Autoscaler により平時は下位段へ縮退するため、**月額はピーク滞留時間で按分**される（実測は [PT-01/PT-02](research/wbs-test-refinement-2026-08-26.md)）。
- Aurora はインスタンスクラス据置き（接続予算の使用率が最大 28%、[§6.4.2a](#642a-接続予算表2026-08-27-新設--c-12)）のため**本改訂による増分なし**。

### 6.2.4 大阪（DR）側の扱い

> **2026-07-30 D-18 転換（コールド DR）**: 大阪は**平時 ROSA クラスタを持たない**。被災時に IaC で**オンデマンド再構築**（RTO ≈ 14 日、U8 D-U8-14）。以下の「大阪パイロットライト（平時 2 ノード + Aurora Global Secondary）」記述のうち **ROSA 常時ノード分は廃止**。**Aurora Global Secondary（データ層）は維持**（U8 D-U8-14 推奨 A、RPO < 1 分・ストレージのみ）。**CIDR/サブネットは再構築先として事前確保**（install 後不変制約のため、平時クラスタが無くても IP レンジは予約）。

- 東京 + 大阪の **ROSA HCP 対称構成が成立**（AWS 公式リージョン表で確認済み、ADR-051 2026-07-23 更新。**平時は東京のみ稼働、大阪はオンデマンド再構築先**）。
- 残: **G-OSAKA** — 大阪側の該当インスタンスタイプ在庫 + vCPU クォータの実確認（U1 §1.5 ゲート、§6.8）。
- **大阪の Machine Pool 構成（2026-07-24 明確化）**: infra Pool（c7g.large × 2、テイントなし）+ **KC 専用 Pool（labeled/tainted、min 0、東京と同一のテイント/ラベル定義で事前作成）**。CIDR・サブネットも Failover 後の東京同等スケール（**KC Pool max 9/29**、2026-08-27 是正）を収容できるサイズで事前確保する（§6.2.1 サブネット設計参照）。
- DR の Failover 手順・RTO/RPO 設計は U8（本書は「Broker/IdP-KC それぞれ大阪にパイロットライト・クラスタと Aurora Global Secondary を持つ」という物理配置のみ確定）。

---

### 6.2.5 決定 D-U6-19: 2 ネットワーク分離構成（2026-08-27 本文化 — C-9）

> **本節の位置づけ**: 2026-08-18 に「単一ネットワーク集約（A 案）→ **2 ネットワーク分離（B 案）採用**」を決定したが、[§6.2.1](#621-決定-d-u6-03-クラスタ構成) の箇条書き（決定の記録）に留まり、**本文の構成記述が単一ネットワーク前提のまま**だった。本節で構成として書き下す。**詳細（サブネット × リソース × 接続 × SG × 通信シーケンス）は [トポロジ note](research/brand-unit-2vpc-topology-2026-08-18.md) を正**とし、本節はその要約と設計上の不変条件を担う。
>
> ⚠ **CIDR の実値は P-17（[D-19](00a-remaining-tasks-and-effort.md)）の確定待ち**のため、本節では変数で記述する（`$CIDR_K` / `$CIDR_M`）。**クラスタ作成後に CIDR は変更できない**ため、確定前に構築へ進んではならない。

#### 6.2.5.1 分離の単位と理由

| ネットワーク | 収容するもの | 機微度 | ROSA 管理下 | TGW 接続 | CIDR |
|---|---|---|---|---|---|
| **VPC-K（認証製品・利用者情報）** | ROSA クラスタ（認証製品 Pod）／**利用者情報 DB（パスワードのハッシュを保持）**／ログイン用と管理用の内部 NLB 2 本 | **最高** | ○ | **必要**（ログインの入口が経由するため） | `$CIDR_K`（Transit へ広告する） |
| **VPC-M（管理・権限）** | **管理 API（idm-api）**／非同期処理群／**権限 DB**／各種エンドポイント | 中 | × | **不要** | `$CIDR_M`（**Transit へ広告しない = 隠蔽できる**） |

**なぜ 2 つに分けるか**: [AWS の設計原則 SEC05-BP01](research/single-vpc-consolidation-risk-2026-08-18.md) は「**全リソースを 1 つのネットワークに置く**」を **High リスクのアンチパターン**として明示し、機微度が異なるものは境界を「サブネット → ネットワーク → アカウント」の順に格上げせよとする。単一ネットワークでは **管理 API が侵害されたときにパスワードのハッシュを保持する DB まで到達しうる**が、分離すれば**経路そのものが存在しない**状態を作れる。

**VPC-M が TGW に繋がなくてよい理由**: 管理 API への入口は「配信 → API ゲートウェイ → 関数の直接呼び出し」であり、**ネットワーク経路を通らない**。関数側のネットワーク接続は**出ていく方向専用**（権限 DB・管理 API・AWS サービス）。よって **Transit から見えない孤立した島**にでき、[CGNAT 帯](research/rosa-vpc-ip-conservation-2026-08-17.md)を使って Transit の IP を一切消費しない構成が取れる。

#### 6.2.5.2 サブネット構成（AZ ごと × 3）

**VPC-K** — [§6.2.1](#621-決定-d-u6-03-クラスタ構成) の「サブネット 4 層設計」は**本ネットワークの記述**である（VPC-M には適用されない）:

| 層 | サイズ/AZ | 収容 |
|---|---|---|
| TGW 接続用 | /28 | Transit の接続点。ログインの入口 |
| ロードバランサ用 | /27 | 内部 ALB（L7 制御・`/admin` 遮断） |
| ノード用 | /26 | ROSA worker（認証製品 Pod）／**ログイン用 内部 NLB**／**管理用 内部 NLB** |
| DB 用 | /28 | **利用者情報 DB**（認証製品 Pod のみ到達可） |
| エンドポイント用 | /27 | 外向き通信を閉域化するための各種エンドポイント |

**VPC-M**（3 層のみ・小規模）:

| 層 | サイズ/AZ | 収容 |
|---|---|---|
| 関数用 | /27 | 管理 API の実行環境／非同期処理群の実行環境 |
| エンドポイント用 | /27 | **管理 API 到達用エンドポイント**／AWS サービス用エンドポイント |
| DB 用 | /28 | **権限 DB**（管理 API のみ到達可） |

#### 6.2.5.3 ネットワークをまたぐ経路は 2 本だけ

| 経路 | 呼ぶ側 → 呼ばれる側 | 用途 | 方向 |
|---|---|---|---|
| **① 認証の裏経路** | 外部連携を受ける側（別アカウント） → VPC-K のログイン用 NLB | 利用者を直接収容する側へ認証を委譲する際の、トークン取得・鍵取得・属性取得 | **一方向**（逆向きに接続できない） |
| **② 管理 API 経路** | VPC-M の管理 API → VPC-K の管理用 NLB | 利用者・接続先の作成／更新／削除 | **一方向** |

- **接続を受ける側の NLB を 2 本に分ける**ことで、**管理用の口をログインの面から隔離**する（ログイン経路から管理 API へ横に移動できない）。
- 名前解決は**呼ぶ側のネットワーク内に閉じた DNS** で行い、外部からは解決できない。

#### 6.2.5.4 守るべき不変条件（設計・実装・レビューの合格基準）

| # | 不変条件 | 破れたときに起きること |
|---|---|---|
| **1** | **管理 API は利用者情報 DB への経路も接続許可も持たない** | パスワードのハッシュが管理面の侵害で流出する |
| **2** | **利用者情報 DB に接続できるのは認証製品 Pod のみ** | 同上 |
| **3** | **権限 DB に接続できるのは管理 API と非同期処理群のみ** | 権限情報の直接改ざん |
| **4** | **ネットワーク間の接続は「呼ぶ側 → 呼ばれる側」の一方向で、逆向きの接続を張れない** | VPC-K 側が侵害された場合に管理面へ横展開される |
| **5** | **管理用 NLB に到達できるのは VPC-M の当該エンドポイントのみ** | 管理 API が広く公開される |
| **6** | **VPC-M は Transit に接続しない** | 社内網から権限 DB へ到達しうる |

> **管理 API が全侵害された場合の到達範囲**: 権限 DB と、管理 API 経由でできる操作のみ。**パスワードのハッシュには到達できず**、**クラスタ網の探索もできない**。これが単一ネットワーク構成との決定的な差である。

#### 6.2.5.5 単一ネットワーク構成からの差分

| 観点 | 旧（A 案・単一） | **新（B 案・2 分離）** |
|---|---|---|
| ネットワーク数 | 1 | **2** |
| 管理 API の実行環境の置き場所 | クラスタと同じネットワークのノード層 | **VPC-M の専用層** |
| 管理 API → 認証製品 | 同一ネットワーク内で直接到達 | **一方向の閉域接続のみ** |
| 利用者情報 DB への到達可能性 | 同一ネットワークのため**経路が存在した** | **経路が存在しない** |
| Transit が消費する IP | 全リソース分 | **VPC-K のみ**（VPC-M は隠蔽可） |
| 設定の複雑さ | 低 | **中**（エンドポイント 2 系統・DNS 2 系統の増） |

- **増える運用**: 閉域接続の受け口 2 本の作成・承認、名前解決の設定、接続の疎通監視。→ [U9](09-operations-observability-design.md) へ引き渡し、[IT-08 疎通試験](research/wbs-test-refinement-2026-08-26.md)で検証する。
- **アカウントまで分ける案**（権限側を別アカウントへ）は [ADR-063 オプション B](../adr/063-brand-unit-architecture.md) として保留。Phase 1 は 2 ネットワーク分離まで。

---

## 6.3 Broker ↔ IdP-KC クロスアカウント経路

### 6.3.1 前提: フロントチャネルとバックチャネルの分離

2-tier フェデレーション（ADR-033 §C シナリオ 2）では、IdP なし顧客のログイン時にユーザーの**ブラウザが IdP-KC のログイン画面へリダイレクト**される。したがって:

| チャネル | 通信 | 経路 |
|---------|------|------|
| **フロントチャネル**（authorize / ログイン画面） | ブラウザ → IdP-KC | **他組織 Inbound エッジ経由**（`idp.basis.example.com` 用の CloudFront + WAF セットを B 部で要求、REQ-IN-02） |
| **バックチャネル**（token / JWKS / userinfo） | Broker KC Pod → IdP-KC Internal ALB | **本節のクロスアカウント私設経路**（インターネット非経由） |

バックチャネルの名前解決は Split-horizon DNS（ADR-012 Follow-up / [keycloak-network-architecture.md §6.5](../common/keycloak-network-architecture.md)）: Broker Acct の Route 53 Private Hosted Zone で `idp.basis.example.com` を私設経路のエンドポイントに解決させ、`iss` の一致を保ったまま VPC 内完結させる。

### 6.3.2 決定 D-U6-06: バックチャネル経路は PrivateLink を推奨

| 観点 | ① TGW | ② VPC Peering | ③ **PrivateLink（推奨）** |
|------|-------|---------------|--------------------------|
| 方向性 | 双方向（ルーティング次第） | 双方向 | **単方向**（Broker → IdP-KC のみ。逆流不能） |
| 到達範囲 | 経路設定した CIDR 全体 | 相手 VPC 全体 | **公開した NLB/サービスのみ**（最小到達） |
| CIDR 重複 | 不可 | 不可 | **無関係** |
| 管理主体 | **NW Acct = 他組織想定（P-18）**。我々単独で完結しない | 弊社 2 Acct 間で完結 | 弊社 2 Acct 間で完結 |
| コスト | Attachment $0.07/h × 2 + 処理料 | 同 AZ 内転送無料 | Endpoint ~$7/月 + $0.01/GB |
| 帯域・遅延 | 十分 | 十分 | 十分（トークン交換は低トラフィック: 初回ログインのみ、SSO 中は Broker 完結 = ADR-033 §C シナリオ 3） |

**判断**: **③ PrivateLink** を推奨・採用する。
- 根拠 1: P-17 の分離目的（権限分界・障害隔離）と方向一致 — IdP-KC 側から Broker VPC へ**構造的に到達できない**単方向経路は、IdP-KC（PW ハッシュ保有側、ADR-033 §D-1）侵害時の横展開を経路レベルで遮断する。
- 根拠 2: TGW は NW Acct（他組織想定）依存となり、弊社 2 Acct 間の内部経路まで他組織の変更管理に載る。P-18 の教訓（管理外依存の最小化）から回避。
- 根拠 3: HCP worker は自アカウント VPC 内にあり（research #8）、IdP-KC 側 Private Ingress の NLB を Endpoint Service 化する構成は AWS 標準パターン。
- 実装: IdP-KC Acct の Ingress NLB → VPC Endpoint Service（`acceptance_required = true`、許可 Principal = Broker Acct のみ）→ Broker Acct に Interface Endpoint → PHZ `idp.basis.example.com` を Endpoint に Alias。TLS は IdP-KC 側 Ingress で終端（証明書は IdP-KC Acct ACM/cert-manager）。
- 補足: 将来 IdP-KC シャーディング（P-16 超過時の拡張パス、ADR-033 更新注記）でも Endpoint Service を追加するだけで Broker 側設計は不変。
- **アプリ → IdP-KC のユーザ CRUD 経路（P-17）は IdP-KC Acct 内で完結**（同居アプリ → **専用 API 層（ADR-038 Backend 同基盤、IdP-KC Acct 内配置）** → IdP-KC Admin API。U3 D3-05 確定。Admin API 直・SCIM 経由は不採用）。本書はネットワーク面で「**アプリ発 CRUD については** IdP-KC Acct の VPC 内経路のみ・クロスアカウント CRUD 経路は設けない」ことを確定する（2026-07-24 文言精密化 — 下記の管理画面経路と区別）。
- **CRUD / 権限編集はブランド側（idm-api）でローカル完結（2026-08-06 [ADR-063 ブランドユニット](../adr/063-brand-unit-architecture.md) 改訂 — 旧「Broker Acct の中央 front door が PrivateLink 単方向でブランド idm-api を委譲呼び」は廃止）**: idm-api（ブランド管理 API、Lambda）が **CRUD + 権限 + authz + projection の実体**。入口は idm-api、ルーティングはエッジ（CloudFront/API GW がブランド → idm-api）で、Admin API 書込は IdP-KC クラスタ内・内部 NLB で完結（Admin API を外部露出しない方針は維持、D-U6-11 / 06a §A.2.1b）。**越境は EventBridge の 2 本のみ**: ① `idm-api → Broker`（削除イベント `user.deprovisioned {sub, brand_id}` → 中央 shadow 制御 Lambda が Broker shadow を `enabled=false` + `not_before` + session revoke、内部 NLB）② `Broker → ブランド`（初回ログイン時の `sub` 通知 = ブランド authz スタブ行生成用）。ホットパス（アプリの `/api/me/context`）はブランドローカル read で**越境ゼロ**。**旧 O-12（PrivateLink 内部ルート / 中央 front door → ブランド idm-api S2S 委譲）は不要化** → 越境イベント経路の S2S 認可（shadow 制御 Lambda、U5 §5.8）に再定義。
- **2-tier クライアント認証**: PrivateLink 閉域経路が成立するため Phase 1 は `client_secret_post` を許容。`private_key_jwt` / mTLS への昇格は U7 の Secrets ローテーション設計と同時に判断（Phase 2 開始まで）— U2 未決 #4 への回答。

---

## 6.4 Aurora PostgreSQL 設計

### 6.4.1 決定 D-U6-07: 基本構成

| 項目 | 決定 | 根拠 |
|------|------|------|
| エンジン | Aurora PostgreSQL 16（RHBK 26.4 HA Guide が 15/16/17 を multi-site HA サポート DB に明記） | research #8、ADR-051 更新注記 |
| クラスタ | Broker DB / IdP-KC DB の **2 系統**（各 Acct 内、共有しない） | ADR-033 §E-1 |
| 東京構成 | Writer + Reader × 2（Multi-AZ）、I/O-Optimized（Write IOPS 14,000-42,000 見込み） | ADR-033 §A |
| インスタンス | Broker: db.r7g.xlarge × 3 / IdP-KC: db.r7g.xlarge × 2（Phase 1。10M ピーク帯で Broker db.r7g.2xlarge 化を再評価） | ADR-033 §G、ADR-051 §B.1 |
| DR | Aurora Global Database（大阪 Secondary Reader × 1、RPO < 1 min）。**2026-07-30 D-18: コンピュート（ROSA）はコールド化するが Aurora Global〔データ層〕は維持**（D-U8-14 推奨 A、O-U8-10 で最終確定）+ イミュータブルスナップショット併用。Failover 手順は U8 | ADR-051 §B.1、P-05 |
| 暗号化 | KMS MRK（CMK は Acct ごと。IdP-KC DB は PW ハッシュ保有のためバックアップ暗号化必須） | ADR-045、ADR-033 §H |
| 接続 | **KC Pod SG → Aurora SG の直接続**（HCP でも worker は自 Acct VPC 内のため PrivateLink 不要 — 旧調査の「PrivateLink 経由」は CP↔worker 間の話） | research #8 |
| `authz` / `idmap` / `projection` | **2026-08-07 [ADR-063](../adr/063-brand-unit-architecture.md): ブランド(IdP-KC)アカウントローカルに配置**（旧「Broker Acct Aurora 別 DB」= O-8 は上書き）。**Option C: Keycloak identity Aurora とは別 Aurora・別 CMK・別 IAM ロール・別 SG**（[U7 D-U7-19](07-security-compliance-design.md)）。federated の authz 行は初回 sub 通知(EventBridge Broker→ブランド、§6.1.2)で生成 | U3 D3-03/D3-11/D3-16、U7 D-U7-19 |

### 6.4.2 決定 D-U6-08: jdbc-ping 前提のコネクション設計（禁則 [K-2](09-operations-observability-design.md) の根拠）

KC 26.1 以降 **jdbc-ping がデフォルト**（ノードディスカバリを KC DB の `JGROUPSPING` テーブル経由で実施、multicast 不要。PoC 前提と完全整合 — research #8）。これを前提に:

| 項目 | 設計値（初期） | 理由 |
|------|---------------|------|
| 接続先エンドポイント | **Cluster（Writer）エンドポイントのみ**。Reader エンドポイントを KC に渡さない | jdbc-ping のハートビート書込 + KC のトランザクション整合。読取分散は KC では行わない |
| Pod あたり接続プール | **`db-pool-initial-size` = `db-pool-min-size` = `db-pool-max-size` = 30 の等値**を明示設定（2026-07-23 改訂: 旧 10/30 → Keycloak 公式推奨の等値化。Agroal デフォルト max 100/pod は放置厳禁） | 等値化で接続チャーン回避 + PostgreSQL server-side prepared statement（5 回実行で有効化）が効き **p99 に有利**。トレードオフ: scale-out 時に新 Pod が即 30 本確保するが、下記の Writer 余裕内に収まる |
| 総接続数見積 | **2026-08-27 是正**（[D-U6-18 少数大型 Pod モデル](#622a-決定-d-u6-18-少数大型-pod-モデル2026-08-27-新設--pod-数定義の不整合是正)確定 + フェデ 50:50 改訂）: **10M ピークで Broker 9 Pod × 30 = 270 / IdP-KC 29 Pod × 30 = 870**（旧記述「27 Pod × 30 = 810」は 70/30 前提のため過小）。Writer 上限は r7g.xlarge で **max_connections ≈ 3,300**（`LEAST(DBInstanceClassMemory/9531392, 5000)`、32GB）。**2 系統 DB に分かれるため、1 系統あたりの評価は下記「接続予算」表で行う** | **Pod 数とノード数が 1:1 のため、Machine Pool の max を上げると接続数も比例して増える** — max 変更時は必ず本表を再評価すること（禁則 [K-2](09-operations-observability-design.md)） |
| **接続予算（2026-08-27 新設 — C-1.2）** | **1 つの Aurora Writer に接続しうる全主体を列挙し、上限 3,300 を配分する規約**。下記「接続予算表」を DB 系統ごとに維持し、**新たな接続主体を追加する変更は必ず本表への行追加を伴う**（表に無い主体が接続してはならない） | 従来は KC の分だけを見て「大幅な余裕」と評価しており、**Lambda 群・バッチ・監視の枠が明示されていなかった**。[ADR-062](../adr/062-idm-api-execution-form-lambda.md) で管理 API が Lambda 化されたことで、**同時実行数 × 接続数で膨らむ主体**が加わったため規約化する |
| jdbc-ping 留意 | Failover（Writer 交代 / Global DB Promote）中はディスカバリ書込が一時失敗する。**クラスタ全 Pod の同時再起動を伴う操作は Writer 安定後に実施**する運用制約を U8/U9 Runbook に引き渡す | KC 26.1 リリースノート、ADR-051 |
| タイムアウト | JDBC socket/login timeout を ALB/Route 53 Failover TTL（30s）より短く設定し、Failover 検知を DB 側で先行させる | ADR-051 §D.2 |

#### 6.4.2a 接続予算表（2026-08-27 新設 — C-1.2）

**規約 3 点**:

1. **表に無い主体は接続してはならない**。接続主体を増やす変更は、本表への行追加とレビューを必須とする。
2. **Lambda は接続プールを持てない**（実行環境が同時実行数だけ独立に立ち上がるため）。したがって **予約同時実行数をそのまま最大接続数として計上**する。予約同時実行数を設定しない Lambda を Aurora に接続させてはならない（**アカウント既定の同時実行上限まで接続が膨らみ、Writer を枯渇させる**）。
3. **使用率が上限の 60% を超えたら**、[§6.4.3](#643-決定-d-u6-09-rds-proxy-は暫定不採用) の RDS Proxy 不採用判断とインスタンスクラスを再評価する。

**① Broker Keycloak DB（Broker Aurora）— 上限 ≈ 3,300**

| 接続主体 | 算定根拠 | 本数 |
|---|---|---:|
| KC Pod（10M ピーク） | 9 Pod × プール 30（等値固定） | 270 |
| superuser 予約 | PostgreSQL 既定 | 3 |
| Aurora 内部（autovacuum / レプリケーション等） | 実測で補正 | ~20 |
| メトリクス収集 | postgres_exporter | 2 |
| 移行バッチ | 移行期間のみ・短命 | 10 |
| 退職者遮断バッチ（[U9 D-U9-17](09-operations-observability-design.md)） | 排他ロック用・少数短命 | 5 |
| **合計 / 使用率** | | **≈ 310 / 9%** |

> **Keycloak 以外のアプリケーションが本 DB に接続することを禁止**する（製品所有スキーマのため。管理操作は Admin API 経由に限る — [ADR-062](../adr/062-idm-api-execution-form-lambda.md)）。

**② IdP-KC Keycloak DB（identity Aurora）— 上限 ≈ 3,300**

| 接続主体 | 算定根拠 | 本数 |
|---|---|---:|
| KC Pod（10M ピーク・フェデ 50:50） | **29 Pod** × プール 30 | **870** |
| superuser / Aurora 内部 / メトリクス | 上に同じ | ~25 |
| 移行バッチ / 遮断バッチ | 上に同じ | 15 |
| **合計 / 使用率** | | **≈ 910 / 28%** |

> **フェデ比率が 50:50 より低ローカル側へ振れると Pod 数が増え、本表が最初に効く**。ローカル 100%（フォールバック β）では IdP-KC ≈ 58 Pod × 30 = **1,740 本（53%）** となり、60% 閾値に接近する。

**③ authz 系 Aurora（VPC-M）— 上限 ≈ 3,300**

| 接続主体 | 算定根拠 | Writer | Reader |
|---|---|---:|---:|
| 管理 API（idm-api） | 予約同時実行 100 = 100 接続 | 100 | — |
| 受け取り窓口（SCIM Facade） | 予約同時実行 100 | 100 | — |
| 権限情報の一括取得（`/api/me/context`） | 予約同時実行 200、**参照専用のため Reader へ振る** | — | 200 |
| 参照用データの更新（射影フィード） | 予約同時実行 50 | 50 | — |
| 送信予定イベントの中継（outbox リレー） | 予約同時実行 20 | 20 | — |
| 対応づけハンドラ / Webhook 系 | 予約同時実行 30 | 30 | — |
| 定期バッチ（保持・消去・整合確認） | 逐次実行・少数 | 20 | — |
| superuser / Aurora 内部 / メトリクス | | ~25 | ~5 |
| **合計 / 使用率** | | **≈ 345 / 10%** | **≈ 205 / 6%** |

> **Keycloak 用 DB と異なり Reader エンドポイントを併用**する（KC は整合上 Writer 固定だが、authz 系の参照 API は遅延許容のため Reader へ逃がせる）。**読み取りが増えたら Reader を増設**することで Writer 予算を守る。

---

### 6.4.3 決定 D-U6-09: RDS Proxy は暫定不採用

| 観点 | 評価 |
|------|------|
| 恩恵 | RDS Proxy の主用途は「大量短命接続（サーバーレス）」の多重化と Failover 短縮。KC は **Quarkus/Agroal の長命プール**で接続数が設計上固定（§6.4.2）のため多重化恩恵がほぼない |
| リスク | セッション状態（prepared statement / advisory lock 系）による**ピン留め**で多重化が無効化 + レイテンシ加算。jdbc-ping のハートビート経路に中間層が挟まる構成は RHBK 26.4 HA Guide / keycloak-benchmark の「ROSA + Aurora 直結」手順（research #8）から外れ、サポート切り分けが不利 |
| コスト | vCPU 課金が Aurora 2 系統 × 東西で加算 |

**判断**: **Phase 1 は不採用（Aurora SG 直接続）**。ただし U8 の DR 検証で「Writer Failover 時の KC 再接続時間」が RTO 内訳を圧迫する場合に限り再評価する（§6.8 未決事項に登録）。
- 一般則の裏付け（2026-07-23 追記、**2026-08-27 数値是正**）: 外部 pooler が必要になるのは「1 pod あたり接続 < 5 × pod 数百」の形態。本設計は **pod 少数（10M ピークで Broker 9 / IdP-KC 29、[D-U6-18](#622a-決定-d-u6-18-少数大型-pod-モデル2026-08-27-新設--pod-数定義の不整合是正)）× 中規模プール（30）の長命プール直結**が最適解。将来 P-16 超過で IdP-KC を数百 pod 規模へシャーディングする段階で初めて **PgBouncer transaction mode** を拡張パスとして検討する。
- **再評価トリガー（2026-08-27 新設）**: [§6.4.2a 接続予算表](#642a-接続予算表2026-08-27-新設--c-12)の**いずれかの系統で使用率が 60% を超えた時点**で本判断を再開する（現状の最大は identity Aurora の 28%、ローカル 100% 振れで 53%）。

---

## 6.5 サイジング（MAU 10M 上限 / フェデ比率 50:50 暫定 / Argon2id）

### 6.5.1 前提と暫定値の明示

> **2026-08-27 改訂（C-1.3）**: ① フェデ比率を **70/30 → 50:50**（B-BROK-1 の暫定値、2026-08-16 決定）へ差し替え ② **MAU を「初回リリース時点」と「上限」に分離**（P-02）し、初回リリースのサイジングを独立して算定 ③ Pod 数は [D-U6-18 少数大型 Pod モデル](#622a-決定-d-u6-18-少数大型-pod-モデル2026-08-27-新設--pod-数定義の不整合是正)（1 ノード 1 Pod）に統一。

| パラメータ | 値 | 位置づけ |
|-----------|-----|---------|
| MAU（**時点分離**） | **初回リリース = 100 万〜500 万** ／ **上限 = 10M** | P-02（凍結）。**設備は初回リリース値で調達し、上限値はスケール余地として設計にのみ反映**する |
| ピーク Login TPS | **10M で 1,000〜3,000**。MAU に線形按分（100 万 = 100〜300 / 500 万 = 500〜1,500） | ADR-033 §A（10M MAU 試算） |
| フェデ比率 | **50% フェデ / 50% ローカル — 暫定**（2026-08-16、B-BROK-1 の暫定回答）。**旧 70/30 から改訂**。P-07 γ シナリオ（管理者層のみローカル）が確定すればローカル比率は 5% 未満まで縮小し得るため、**本節の IdP-KC 側は上限保守値** | [sizing-guide §7](../reference/keycloak-cpu-bottleneck-sizing-guide.md)、P-07 |
| PW ハッシュ | **Argon2id**（KC 25+ デフォルト、P-03 FIPS 不要のため維持）。スループット 8-12 TPS/vCPU（t=1/m=64MB 帯の保守値。KC デフォルトパラメータ m=7MiB/t=5 での実測は PoC で補正） | sizing-guide §3/§6 |
| Safety Margin | 1.5x | sizing-guide §6 |

### 6.5.2 Broker クラスタ CPU 試算

公式（sizing-guide §6）: `Broker vCPU ≈ (L × 0.003 + R × 0.002 + 1) × M`、R（Refresh TPS）= L × 4 と仮置き。

| シナリオ | L | R | 必要 vCPU | ノード構成（= **Pod 数**、[D-U6-18](#622a-決定-d-u6-18-少数大型-pod-モデル2026-08-27-新設--pod-数定義の不整合是正)） |
|---------|---:|---:|----------:|--------------------------------|
| **初回 100 万 MAU・下限** | 100 | 400 | ≈ 3 | **c7g.xlarge × 3**（AZ 冗長の下限が支配、ベースライン） |
| **初回 100 万 MAU・上限** | 300 | 1,200 | ≈ 6 | c7g.xlarge × 3（12 vCPU で充足） |
| **初回 500 万 MAU・下限** | 500 | 2,000 | ≈ 10 | c7g.xlarge × 3（12 vCPU、ほぼ限界） |
| **初回 500 万 MAU・上限** | 1,500 | 6,000 | **≈ 26** | **c7g.2xlarge × 4**（32 vCPU）— ここでベースラインを超える |
| 10M MAU ピーク下限 | 1,000 | 4,000 | ≈ 18 | c7g.2xlarge × 3（24 vCPU） |
| 10M MAU ピーク上限 | 3,000 | 12,000 | **≈ 51** | **c7g.2xlarge × 7**（56 vCPU）→ Machine Pool **max 9** |

- Broker は Password Hashing ~0%（sizing-guide §5）のため CPU 需要は署名/検証系で線形。**フェデ比率の影響を受けない**（フェデもローカルも Broker を通るため）ので、50:50 への改訂で Broker 側の数値は変わらない。SAML 顧客 IdP 比率が高い場合 DSig 検証分の上振れに注意（監視で補正、U9）。

### 6.5.3 IdP-KC クラスタ CPU 試算（フェデ比率感度）

公式: `IdP-KC vCPU ≈ (L × (1 - F) / T_login) × M`、T_login = 10 TPS/vCPU（Argon2id 中央値）。

**① フェデ比率の感度（10M ピーク時）**

| フェデ比率 F | ローカル TPS（L=1,000 / 3,000） | 必要 vCPU | ノード構成（= Pod 数） |
|-------------|-------------------------------:|----------:|-------------|
| **50:50 ★暫定（2026-08-16 改訂）** | 500 / 1,500 | **75 / 225** | c7g.2xlarge × 10 〜 **× 29**。**最大ケースが Machine Pool max=29 の根拠（§6.2.2）** |
| 70/30（**旧暫定・参考**） | 300 / 900 | 45 / 135 | c7g.2xlarge × 6 〜 × 17 |
| 90/10 | 100 / 300 | 15 / 45 | c7g.2xlarge × 2 〜 × 6 |
| γ シナリオ確定時（≈97/3） | 30 / 90 | 5 / 14 | **c7g.xlarge × 3 で収まる** |

> ⚠ **50:50 への改訂の影響**: 10M ピーク上限の必要 vCPU が **135 → 225（+67%）**、ノード = Pod 数が **18 → 29** に増える。これに伴い ① **Machine Pool max を 18 → 29 へ引き上げ**（§6.2.2）② **DB 接続予算を 540 → 870 本へ改訂**（[§6.4.2a](#642a-接続予算表2026-08-27-新設--c-12)）③ **ピーク時コストが上振れ**（§6.2.3）。**フェデ比率は本設計で最も感度の高いパラメータ**であり、B-BROK-1 の確定回答は最優先で取得する。

**② 初回リリース時点（100 万〜500 万 MAU、フェデ 50:50）**

| MAU | L（下限 / 上限） | 必要 vCPU | ノード構成（= Pod 数） |
|---|---:|---:|---|
| **100 万** | 100 / 300 | **8 / 23** | c7g.xlarge × 3（12 vCPU）で下限は充足、**上限は c7g.2xlarge × 3 が必要** |
| **500 万** | 500 / 1,500 | **38 / 113** | **c7g.2xlarge × 5 〜 × 15** — **ベースライン c7g.xlarge × 3 では下限すら賄えない** |

> ⚠ **重要な発見（2026-08-27）**: 従来 §6.2.2 が「Phase 1 ベースライン = c7g.xlarge × 3」としてきたが、**50:50 では初回 500 万 MAU の時点で IdP-KC は c7g.2xlarge × 5 以上が必要**であり、**ベースラインが成立するのは「100 万 MAU かつ TPS 下限」の場合に限られる**。初回リリースの MAU 見込みと TPS 見込みの確定（B-BROK-1 とセット）が、**調達する設備量を 3 台〜15 台の 5 倍幅で左右する**。

- **B-BROK-1 の回答が IdP-KC のノード数（= コスト）を 3〜29 台の幅で直接決める**。回答受領時は本節のみ差し替えれば §6.2.3 コスト表まで機械的に再計算できる構造とした。
- ローカル 100% への振れ（フォールバック β）では 10M ピークで **≈ 450 vCPU = c7g.2xlarge × 58**（接続 1,740 本 = 予算の 53%、[§6.4.2a](#642a-接続予算表2026-08-27-新設--c-12)）。線形に吸収可能（sizing-guide §7）でアーキテクチャ変更は不要だが、**接続予算の 60% 閾値に接近する**ため RDS Proxy 判断（§6.4.3）の再開点となる。

### 6.5.4 メモリ・Argon2id 留意

- Argon2id はメモリハード（sizing-guide §4）。KC デフォルト（m=7MiB）なら同時ハッシュ **1,500 並列**（フェデ 50:50・L=3,000 時）でも **+10.5 GB/クラスタ**程度で、**29 Pod × 13 GB = 377 GB** の枠に対し十分吸収可能。**m=64MB 系へ強化する場合は m7g 系へ変更**（セキュリティパラメータ選定は U7）。
- IdP-KC はスケールアウト時の JVM warmup + Infinispan 参加が遅いため、**Scale-Out 予兆トリガ（`login_success_password_rate` > 8 TPS/node 3 分）を CPU 閾値より優先**（sizing-guide §9）→ U9 に引き渡し。

### 6.5.5 決定 D-U6-10: IdP 1000+ 時の Infinispan キャッシュ初期値

P-16（1000+ IdP、条件付き成立）の必須対策 6「キャッシュサイジング明示設計」（[research](research/keycloak-1000idp-scalability-research.md)）を以下の初期値で確定し、**PoC P-4（キャッシュメモリ実測）で補正**する:

| キャッシュ | 初期値 | 根拠 |
|-----------|-------|------|
| realms 系（IdP 専用キャッシュ含む、KC 26.0 `IdentityProviderStorageProvider` 経由） | **max-count 200,000 entries** | 26.4 公式ベンチ: 10k → 200k entries で Aurora CPU 77.8% → 63.8%（research 必須対策 6）。IdP 2,000 ×（IdP 1 + Mapper 6 + org 紐付け）≈ 16,000 entries に対し 10 倍超の余裕 |
| users | 100,000（アクティブ作業集合ベース。ヒット率 < 90% で増量） | sizing-guide §9 `infinispan_cache_hit_ratio` 監視と連動 |
| sessions 系 | KC 26 の Persistent user sessions（DB 永続）デフォルトを維持し、メモリ側は既定上限。Off-heap 化は負荷試験後（sizing-guide §10 Level 5） | ADR-051 §C.4（Session は Region 間非同期・失効許容） |
| ヒープ影響 | 上記で +1.5〜2 GB/Pod を見込む。**[D-U6-18 少数大型 Pod モデル](#622a-決定-d-u6-18-少数大型-pod-モデル2026-08-27-新設--pod-数定義の不整合是正)により Pod メモリは c7g.xlarge 期 6 GB / c7g.2xlarge 期 13 GB** を確保済みのため、**キャッシュ増分は既存枠内で吸収できる**（旧記述「3 GB → 4 GB へ引上げ」は多数小型 Pod 前提のため無効） | §6.2.2 |

- 併せて P-16 必須対策 4「realm 全体 export/import 運用禁止」をインフラ運用禁則として U9 Runbook に引き渡す。

---

## 6.6 /admin 保護（自管理側実装）

### 6.6.1 決定 D-U6-11: 3 層防御 + `hostname-admin` 分離を採用

P-18 により WAF の「/admin 全 IP Deny」は**他組織への要求（保証不能）**に変わった（ADR-039 v3 注記 2）。よって自管理側で完結する防御線を 2 層持ち、WAF は追加層と位置づける:

| 層 | 実装 | 管理主体 | 位置づけ |
|----|------|---------|---------|
| L1（要求） | CloudFront WAF で `/admin/*` 全 IP Deny（REQ-IN-04） | 他組織 | あれば良い追加層。**保証しない** |
| L2（**生命線**） | Broker/IdP-KC Acct の Internal ALB（外部流入側 Listener）で `/admin/*` → **固定 403** ルール（最優先評価）。PoC 実証済みパターン（[keycloak-network-architecture.md §3.1](../common/keycloak-network-architecture.md) Rule Default 403、ADR-039 §E.1） | 弊社 | 我々が保証する第一防御線 |
| L3（構造防御） | **Keycloak `hostname-admin` 分離を採用**（下記） | 弊社 | 設定ミス時の最終防御 |

**`hostname-admin` の採否判断（推奨案）**: **採用する**。
- 設定: `hostname=https://auth.basis.example.com`（公開系）/ `hostname-admin=https://kc-admin.broker.internal`（Admin Console 専用）。`kc-admin.broker.internal` は **Broker Acct の Route 53 PHZ にのみ登録**し、パブリック DNS に存在させない（IdP-KC 側も同様に `kc-admin.idpkc.internal`）。
- 効果: Admin Console の URL 生成・リダイレクトが内部ホスト名に固定され、公開ホスト名側から管理 UI が「開けない」構造になる。**注意: `hostname-admin` 単体はアクセスブロック機構ではない**（パス自体は残る）ため、必ず L2 の 403 ルールと併用する — 3 層で初めて成立する設計であることを明記する。
- 影響: Terraform（keycloak provider）/ ユーザ管理画面 Backend（ADR-038）等の Admin REST API クライアントは**内部ホスト名 + 内部経路経由**に統一する（U2/U9 へ引き渡し）。
- 却下した代替: 「L2 のみ（hostname-admin なし）」— 追加コストほぼゼロの構造防御を捨てる理由がない。「Admin 専用の別公開 ALB」— PoC の Admin ALB パターン（ADR-010 Cons で本番非推奨と整理済み）はインターネット露出が残るため不採用。

**Admin API への到達 — 禁則 [K-10](09-operations-observability-design.md) の実体（2026-08-06、[ADR-062](../adr/062-idm-api-execution-form-lambda.md) 反映 — O-9 = idm-api 実行形態 Lambda 確定に伴う D-U6-11 の一部見直し）**: idm-api が Lambda（Pod ネットワーク外）になったため、Keycloak Admin API へは **各クラスタの内部 NLB（`scheme=internal` + SG を idm-api Lambda の SG に限定 + 最低 server-TLS + Admin API のアプリ層認証〔管理クライアント資格情報〕）** で到達する（経路 = `idm-api Lambda（層③）→ 内部 NLB → IngressController → Admin API`）。**ClusterIP 単独方針は "Lambda からの管理 API 到達" 本用途に限り "内部 NLB + 厳格 SG" へ見直す**（エンドユーザー認証経路の L2 `/admin` 403 は不変）。**到達主体は 2 つ**（[ADR-063](../adr/063-brand-unit-architecture.md)）: (a) **ブランド側 idm-api → IdP-KC Admin API**（CRUD、内部 NLB）(b) **中央 shadow 制御 Lambda → Broker Admin API**（shadow 無効化、IdP-KC 削除イベントで発火）。**内部 NLB は `scheme=internal` = インターネット非露出**（公開面は in-cluster でも Lambda でも `api.basis` で同じ）。in-cluster（ClusterIP）との差は **VPC 内の到達経路が 1 本増える（東西）** ことで、**送信元 SG を Lambda の SG に限定 + server-TLS + アプリ層認証**で緩和する。※idm-api 自体が侵害された場合の Admin API 到達は in-cluster と同じ（引き分け）で、残る差は「VPC 層経路が増える・正しく保つ設定対象が増える」程度。**idm-api（IdP-KC = credential アカウント）側はこの東西経路を特に厳格に絞る**（SG 限定・監査必須・可能なら mTLS 優先検討 — ADR-062 Open Items「idm-api Admin API 堅牢化」。ここでの「厳格」は "インターネット露出" の意味ではなく内部到達の厳格化）。


#### 6.2.2a 決定 D-U6-16: ノードのディスク種別と容量（2026-08-18 新設）

**背景**: `D-U6-04` は Machine Pool のインスタンス種別（c7g.xlarge / c7g.large）を定めているが、**ディスクの種別・容量に一切言及が無かった**。コスト見積りには「EBS（ノード用ブロックストレージ）1 台 100GB」と数量だけが入っており、**設計上の根拠が無い状態**だった。

| 項目 | 決定 | 根拠 |
|---|---|---|
| **種別** | **gp3**（0.096 USD/GB-月） | io2 は不要。ROSA ワーカーのディスクは**コンテナイメージ・ログバッファ・一時領域**が主で、IOPS 要求は Aurora 側に寄っている |
| **容量（KC Pool）** | **120 GB/台** | 内訳: OS + OpenShift 基盤 約 40GB / RHBK イメージ + Custom SPI（3 JAR）約 20GB / **コンテナログのローテーション前バッファ 30GB** / 空き 30GB |
| **容量（infra Pool）** | **100 GB/台** | monitoring スタックのローカル保持分を含む |
| **IOPS / スループット** | **gp3 既定（3,000 IOPS / 125 MB/s）** | 追加購入はしない。**不足が実測で判明した場合のみ引き上げ**（gp3 は無停止で変更可） |
| **暗号化** | **KMS CMK（アカウント別）** | D-U7-01 の鍵体系に従う |

**監視**: **使用率 80% 警告 / 90% 重大**（[D-U9-21](09-operations-observability-design.md) #14、観点「飽和」）。**ログ滞留とイメージ蓄積が枯渇の 2 大要因**であり、どちらも徐々に進行するため閾値監視が有効。

**コスト影響**: 従来の見積り（100GB × ノード数）に対し **KC Pool を 120GB へ引き上げる**ため、1000 万人規模で月額 +約 30 USD。**誤差の範囲**。

---

#### 6.6.1a 決定 D-U6-15: 内部 TLS の PKI と、ゼロ egress のためのエンドポイント（2026-08-18 新設）

**背景**: `DU-U6-11`（内部 NLB server-TLS PKI + NetworkPolicy）は網羅監査（2026-08-12）で新設された DU だが、**U6 本文に対応する設計記述が無かった**。加えて、コスト見積り 35 項目との突合で **DynamoDB / Secrets Manager 向けの VPC エンドポイントが本文に無い**ことが判明した（ゼロ egress 構成の穴）。

**採用 ①: 内部 TLS の認証局**

| 項目 | 決定 |
|---|---|
| 発行元 | **ACM Private CA**（アカウントごとに 1 台。Broker Acct / IdP-KC Acct） |
| 用途 | **内部 NLB の server-TLS 証明書**（idm-api Lambda → Keycloak Admin API、D-U6-11） |
| モード | **短期証明書モード（月 50 USD）を第一候補**。汎用モードは月 400 USD で、内部通信用途には過剰。**要検証**（短期モードの有効期間 7 日が自動更新運用に耐えるか） |
| 信頼の配布 | Lambda 側は環境変数 or Secrets 経由で CA 証明書を保持。**IaC で配布し手動配置を禁止** |
| **DR** | **リージョン資源で複製不可**。案①② は被災時に新規 CA を作成 → **新しい信頼チェーンの再配布が復旧手順に必要**（[U8 D-U8-15](08-availability-dr-design.md)） |
| 監視 | **残存有効期間を監視**（30 日前警告 / 7 日前重大、[U9 D-U9-21](09-operations-observability-design.md)）。**切れると管理操作が全断する** |

**採用 ②: VPC エンドポイントの追加**

ゼロ egress（NAT 経由のインターネット出口を持たない）を維持するため、以下を追加する。**本文に無かったもの**:

| サービス | 種別 | 用途 |
|---|---|---|
| **DynamoDB** | **Gateway 型**（無料） | ITDR / Adaptive / テナント監査 / DSAR（U7・U8 で使用が確定していたが U6 に記載が無かった） |
| **Secrets Manager** | Interface 型 | idm-api Lambda / Pod からの資格情報取得。**DR ではレプリカ側にも必要**（U8 D-U8-15） |
| **AWS Backup** | Interface 型 | バックアップ操作を VPC 内から実行する場合 |
| **ACM PCA** | Interface 型 | 証明書の自動更新を VPC 内から実行 |

**注**: Gateway 型（DynamoDB / S3）は**無料**、Interface 型は**エンドポイント時間 0.014 USD + データ処理料**が発生する。コスト見積りの「接続点群（VPCエンドポイント）」の数量 10 個はこの追加分を織り込んで再確認すること。

### 6.6.2 決定 D-U6-12: Internal 運用経路

| 経路 | 方式 | 用途 |
|------|------|------|
| **標準** | **SSM Session Manager ポートフォワード**（各 Acct の踏み台レス。IAM + SSM ログで監査、監査 Acct へ集約） | 日常の Admin Console / DB メンテ（ADR-010 Follow-up の方針を踏襲） |
| 併用 | 社内 NW / Client VPN →（NW Acct TGW 経由 — **他組織依存のため可用性を保証しない**）→ Internal ALB | チーム常用アクセス。TGW 断時は SSM 経路に退避 |
| 禁止 | インターネットからの /admin 到達経路の新設 | ADR-039 §E |

- SSM 経路は他組織（NW Acct）に依存しない点が P-18 環境での可用性上の利点。**運用経路の二重化（SSM 標準 + VPN 併用）を必須**とする。

---

# B 部: 他組織への要求仕様

### 6.6.3 決定 D-U6-14: テナント隔離契約 + 認証フローのテナント別公平性

**採用**: 単一 Realm + Organizations は**論理**マルチテナンシーであり自動的な資源/障害隔離を伴わないため、隔離を「契約」として明文化する。**①テナント別公平性（noisy-neighbor 対策）**: ログイン/token フローに**テナント別レート制限・クォータ**を設ける（SCIM/管理 API は 10 req/s 済 = D3-11。認証フローは 1 テナントのバーストで共有 DB 接続プール/Infinispan を枯渇させ得るため、CloudFront/WAF or ALB 層 + KC 側で per-tenant スロットルを実装）。**②隔離の強制点**: `tenant_id` を DB 行（IDOR 防御 U5 §5.6.3）・ログ・キュー・射影・下流 API で一貫強制（Organization クレームは識別であり隔離ではない）。**③realm 分離の脱出条件**: realm 全体変更/障害/キャッシュが全テナントに波及するため、**大口/規制テナントは別 realm へ分離できる基準**（U2 §2.7.8 拡張パスと連動）を持つ。既定値・分離基準は hearing **B-TENANT-ISO-1** + U6 サイジングで確定。

## 6.7 ネットワーク監査 Acct / ネットワーク Acct への要求仕様

本節は先方（NW 監査 Acct / NW Acct 管理組織）への**要求として出す形式**で記述する。各項目に REQ 番号を付与し、合意結果（可否・SLA）を本書に追記して管理する。前提となる責任分界は ADR-039 v3 注記。

### 6.7.1 Inbound 要求（REQ-IN）

| # | 要求 | 内容 | 根拠 |
|---|------|------|------|
| REQ-IN-01 | 認証基盤専用 CloudFront + WAF セット | `auth.basis.example.com` 用に**独立した** CloudFront + WAF（他アプリと共有しない）。WAF ルール: Common + Targeted + ATP + 認証専用 Rate Limit | ADR-039 §B.2（独立セット思想の要求化） |
| REQ-IN-02 | IdP-KC フロントチャネル用セット | `idp.basis.example.com` 用の CloudFront + WAF セット（2-tier のログイン画面公開に必須、§6.3.1） | ADR-033 §C |
| REQ-IN-03 | 管理画面 SPA 用セット | `admin.basis.example.com`（顧客テナント管理者向け、外部公開・KC /admin とは別物） | ADR-039 §E.3 |
| REQ-IN-04 | **/admin 全 IP Deny ルール** | REQ-IN-01/02 の WAF に `/admin/*` 全 IP Deny を最優先で設定。**未設定でも弊社側 L2/L3 で防御は成立する（§6.6）が、多層防御として要求** | ADR-039 §E |
| REQ-IN-05 | ビューア IP ヘッダの透過 | CloudFront で `X-Forwarded-For` / `CloudFront-Viewer-Address` を改変せずオリジンへ転送（Rate Limit / ITDR / 監査のクライアント IP 特定に必須） | ADR-035、§6.7.2 |
| REQ-IN-06 | オリジン検証ヘッダ（**追加層**） | CloudFront → オリジン経路に秘密ヘッダ（`X-CloudFront-Secret`）を付与。値は弊社発行・年 2 回ローテーション。弊社 Internal ALB で検証する。**2026-07-24 重み付け修正: 本ヘッダの本来目的（CloudFront 迂回の直アクセス防止）は Internal ALB トポロジで既に達成されているため、主防御 = /admin 403（D-U6-11 L2）+ SG でエッジ送信元限定、secret header = 多層防御の追加層（他組織の設定・ローテーション運用に依存するため主防御に位置づけない）** | ADR-039 §C |
| REQ-IN-07a | Sorry 制御連携（**障害時 Maintenance/Sorry**） | 503・オリジン断時の Sorry ルーティング（Lambda@Edge or CF エラーページ）の設定余地（**U8 主管**、DR/劣化可視化） | ADR-022、U8 |
| REQ-IN-07b | Sorry 制御連携（**認可 Sorry**） | `403` + `X-Sorry-Reason` ヘッダあり → `302 /sorry?app=&reason=` の集約（**U4 別紙**が要求仕様を確定。受諾されても RP 側 redirect 規約は廃止しない — U5 §5.6.6） | ADR-022、U4 §4.5.1 |
| REQ-IN-09 | SCIM 受信用 CloudFront + WAF セット × 2 | `scim-broker.<domain>` / `scim-idp.<domain>` 用（D2: 顧客 IdP → Broker / D1: 顧客 HRIS → IdP-KC）。送信元 IdP/HRIS の IP 許可リスト + テナント別 Rate Limit（初期値 10 req/s、U3 D3-11） | U3 D3-11、ADR-025 §I.1 |
| REQ-IN-10 | CloudFront ログの scrubbing 連携 | 認証系ディストリビューションのログ設定で query string 記録を最小化（`code`/`state` 等が残らない設定）+ ログを弊社監査 Acct へ配信する場合は弊社側マスク経路を通すこと | U7 §7.3 |
| REQ-IN-11 | launchpad SPA 配信用 CloudFront + WAF セット | `launchpad.<domain>`（launchpad/Sorry SPA 配信、S3 オリジン + OAC。**U4 §4.7.4 の追加提案に対する予約採番** — 詳細要求は U4 確定後に追補） | U4 §4.7.4（予約） |
| REQ-IN-12 | **api.basis（idm-api Lambda）inbound = CloudFront → API GW → Lambda（元設計どおり）で確定**（2026-08-06。**組織方針 = 全 inbound NFW 通過必須、ただし静的 SPA と API GW は例外**。API GW はこの例外ゆえ NFW 経路外で準拠） | `他組織 CloudFront(api.basis)+WAF → API GW（JWT authorizer L1 + throttle）→ Lambda ネイティブ invoke`。**API GW が NFW 通過必須の例外**（組織確定）なので **Option 2（ALB→Lambda ターゲットで NFW 経路）/ Option 3（Private API GW）は不要**。他組織は **api. 専用 CloudFront+WAF** を構築（origin = 自 Acct の API GW）。JWT L1 = API GW authorizer、throttle = API GW/WAF | 他組織（api. 専用 CloudFront+WAF）、[U10 §10.2](10-integration-migration-design.md)、[ADR-062](../adr/062-idm-api-execution-form-lambda.md) |
| REQ-IN-13 | **CloudFront → エッジ LB の到達方式 + NFW ingress ルート設計**（2026-07-29 追加、[06a §A.1.1](06a-network-flow-diagrams.md) / O-APP-1 連動） | `auth.`/`idp.`/`admin.` 等の**全 inbound が Network Firewall を必ず通過する**よう、① CloudFront → エッジ LB の到達方式〔(a) パブリック custom origin か (b) VPC origins プライベート LB か〕と ② その通信を firewall endpoint に通す **VPC ルートテーブル設計** を明示すること。**「NFW を通す」ことは自動成立せず経路設計が必須**が本要求の核心。(a) 採用時: エッジ LB の SG を CloudFront マネージドプレフィックスリスト（`com.amazonaws.global.cloudfront.origin-facing`）に限定 + ingress routing で NFW へ。(b) 採用時: **VPC origins は NACL 非評価 / TLS リスナー付き NLB 不可**の制約に留意（In-B の TCP パススルー NLB は TCP リスナーのため相性は要検証、§6.7.2） | ADR-039 §F、06a §A.1.1 |

### 6.7.2 ALB 経路か NLB 経路かの場合分け（REQ-IN-08、**先方確認事項**）

P-18 で Inbound が「ALB **または** NLB + Network Firewall」とされているため、両パターンの要求を場合分けして提示し、**先方にどちらかを確認する**（§6.8 未決事項）:

| 観点 | パターン In-A: 先方 ALB 経路 | パターン In-B: 先方 NLB 経路（**弊社推奨**） |
|------|------------------------------|---------------------------------------------|
| TLS 終端 | 先方 ALB で終端（`auth.basis.example.com` の証明書を**先方が保有・更新**） | NLB は TCP:443 パススルー → **TLS 終端は弊社 Internal ALB**（証明書・秘密鍵が自管理に留まる） |
| WAF 適用範囲 | CloudFront（L7）+ 先方 ALB（Regional WAF 可） | **CloudFront のみ**（NLB に WAF 不可）。→ REQ-IN-01 の CloudFront WAF が唯一の WAF となるため**必須条件に格上げ** |
| クライアント IP | CF + 先方 ALB が XFF に追記 → 弊社側は先方 ALB を信頼プロキシに追加 | CF が付与した XFF がそのまま到達（NLB は L4 透過）→ 信頼プロキシは弊社 ALB のみ |
| KC proxy headers 整合 | `proxy-headers=xforwarded` + 信頼チェーンに**先方 ALB を含める**（先方構成変更が弊社 KC 設定に波及） | `proxy-headers=xforwarded` + 信頼チェーンは**弊社 ALB のみで閉じる** |
| 証明書運用 | 先方 ACM。更新失敗 = 全ログイン停止のため**更新 SLA の合意必須** | 弊社 ACM。他組織依存なし |
| 弊社評価 | 依存が増える | **推奨** — TLS 終端・証明書・プロキシ信頼チェーンが自管理で完結し、P-18 の管理外依存を最小化 |

- **In-B 推奨の根拠補足（2026-07-24 追記）**: TLS 終端は 2 箇所で不可避に発生する — ①**CloudFront は WAF（L7 検査）のため終端が不可避**（これはどちらのパターンでも同じ）。②2 段目の終端を先方 ALB に置く（In-A）と**平文 HTTP が他組織 VPC 内に出現**するが、In-B（NLB パススルー）なら**平文の出現位置を自管理 VPC（弊社 Internal ALB 以降）に閉じられる**。P-18 の管理外領域に平文を置かないことが In-B 推奨の本質的理由。

> **⚠ In-A/In-B とは別軸の未確定事項（2026-07-29、REQ-IN-13）**: 本表は「TLS 終端位置（ALB/NLB）」を場合分けするが、**「CloudFront がそのエッジ LB にどう到達するか」= (a) パブリック custom origin / (b) VPC origins（プライベート LB）は別軸で未確定**。P-18 の露出最小化志向だと (b) VPC origins（プライベート LB・パブリック IP なし）が整合的で、その場合 **[06a §A.1.1](06a-network-flow-diagrams.md) の「VPC origins × NFW 共存」注意（CloudFront 管理 ENI 経由通信・NACL 非評価）が認証パスにこそ本命で効く**。かつ VPC origins は「TLS リスナー付き NLB 不可」だが In-B は TCP:443 パススルー（TCP リスナー = TLS リスナーではない）のため許容されうる — **実装時に到達方式 × NFW ルート設計 × In-B の相性を要検証**（REQ-IN-13 として先方へ要求）。

**要求文**: 「NLB（TCP:443 パススルー）経路を推奨する。ALB 経路とする場合は、①証明書更新 SLA、②XFF 付与仕様（追記位置・偽装除去）、③ヘルスチェックパス（`/health/ready`）、④アイドルタイムアウト ≥ 65s、の 4 点の合意を条件とする。」

### 6.7.3 Outbound 要求（REQ-OUT）— フェデレーション Egress

Broker KC は顧客 IdP の authorization/token/JWKS/userinfo エンドポイントへ HTTPS Egress する。IdP 1000+（P-16）ではドメイン数も 1000+ に達し、Outbound の Network Firewall ドメインフィルタ（他組織管理）と正面衝突する（ADR-039 v3 注記 3 の新リスク）。

**zero-egress との関係（2026-07-23 追記）**: §6.2.1 O-10 の **案 B（`zero_egress:true`）を採用する場合、Worker の運用系 outbound（registry 等）は ECR ミラー化で VPC 内完結し、自 Acct に NAT GW を置かずに TGW で他組織 Outbound 専用経路へ接続できる** — P-18 の「アウトバウンドは他組織アカウント経由」と ROSA の**サポート済み標準構成が噛み合う**。この場合も顧客 IdP 1000+ FQDN のフェデレーション Egress は先方 NFW ドメインフィルタを通過するため、本節の REQ-OUT 要求(特に D-U6-13 の委任方式)は**案 A/B いずれでも必要**(zero-egress は REQ-OUT の代替ではなく、NAT と運用系 Egress 統制の代替)。

**選択肢比較**:

| 案 | 方式 | IdP 追加リードタイム < 1 営業日（§NFR-3）との整合 | 統制 | 評価 |
|----|------|----------------------------------------------|------|------|
| ① 都度申請 | IdP 追加ごとに先方へドメイン許可申請 | **申請 SLA 次第で破綻**（先方の変更管理が週次なら SLA 違反が常態化） | 先方フル統制 | ❌ 単独では不成立 |
| ② 認証基盤向け一括ポリシー | 「Broker KC の Egress 専用ルールグループ」を事前合意で設置。宛先 FQDN リストを弊社が管理し、先方は**枠（送信元 = Broker クラスタの Worker サブネット CIDR〔3AZ 分〕、ポート = 443 のみ、プロトコル = TLS）を統制** | ✅ 追加はリスト更新のみ | 枠 = 先方 / 中身 = 弊社（委任） | ◎ 推奨の主軸 |
| ③ FQDN 許可の自動化 API | 弊社の IdP オンボーディングパイプラインから先方 Firewall のルール更新 API（もしくは先方提供の申請 API）を呼び、自動反映 + 監査ログ | ✅ 分単位 | ②の委任を API 化 | ◎ ② の実装形態として要求 |

**決定 D-U6-13（要求案）**: **② + ③ のハイブリッドを第一要求**とする。
- 要求文: 「認証基盤（Broker）専用の Egress ルールグループ（Suricata 互換、**送信元 = Broker クラスタの Worker サブネット CIDR〔3AZ 分、具体値は別紙〕** / TCP:443 / TLS SNI ベース FQDN 許可）を設置し、FQDN リストの更新権限を弊社オンボーディングパイプラインに委任（API または CI 連携）いただきたい。全更新は双方の監査ログに記録し、四半期レビューで先方が棚卸しする。」
- **フォールバック条件（G-EGRESS ゲートの合否基準）**: ② / ③ が受け入れられない場合、①都度申請の**申請 SLA ≤ 4 営業時間**を合意できなければ、§NFR-3 の「IdP 追加リードタイム < 1 営業日」は成立しない → NFR 側改訂（リードタイム緩和）を U9 経由でエスカレーションする。**「SLA 未合意のまま Phase 1 契約」を禁止する**のが本ゲートの趣旨（U1 §1.5 G-EGRESS）。
- 付帯要求: LDAPS 顧客 AD への Egress（TCP:636、ADR-039 §F.1.A の 3 ルール: 許可 CIDR 限定 / 未知宛先 636 drop+alert / 平文 389 全 drop）も同ルールグループ内で**要求仕様として提示**する（実装主体は先方に変更、監査ログ連携 REQ-OUT-03 で受領）。

#### 送信元の粒度についての注記（2026-08-24 是正）

**要求文の「送信元」は Pod 単位ではなく Worker サブネット単位でしか表現できない。**

ROSA（OVN-Kubernetes）では **Pod IP はオーバーレイ（`10.128.0.0/14`）で VPC の外に出ず、クラスタ外向きの通信はノードの VPC IP に変換される**（[06a §A.2.1](06a-network-flow-diagrams.md)）。よって Network Firewall / SG から観測できる送信元は**ノードが載る Worker サブネット**であり、**Pod や Machine Pool を区別できない**。

さらに [06a §A.5.3](06a-network-flow-diagrams.md) のサブネット割付では **KC Pool / infra Pool / 2xlarge Pool のノードが同一 Worker サブネットに同居**する。したがって、**従来記載の「送信元 = Broker KC Pod CIDR」は実現できない**（実態は Worker サブネット全体の許可であり、infra Pool 上のコンポーネント〔Fluent Bit Aggregator / SCIM Facade 等〕も同じ送信元に見える）。

- **決め**: **要求文を実態に合わせて「Worker サブネット CIDR」と正確に記載する**（本節で是正済み）。**先方へ「KC Pod だけに絞っている」と説明しない** — 受入試験（§6.7.4）で齟齬が出る。
- **残余リスクの評価**: 当該サブネットに載るのは全て自社管理コンポーネントであり、外部からの侵入経路が別途無い限り実害は限定的。**許可先が「顧客 IdP の FQDN のみ」に絞られている**こと（REQ-OUT-01 の SNI ベース許可 + REQ-OUT-02 デフォルト Deny）が実質的な統制。
- **採らなかった案**: ① **KC Pool を専用サブネットへ分離** — HCP の Machine Pool はサブネット単位で作成できるため技術的には可能だが、**サブネットは install 後変更不可**のため構築前に確定する必要があり、分離で得られる統制の増分が小さいため不採用（採るなら Phase 1 構築前が唯一の機会）。② **EgressIP による namespace 単位の送信元 IP 割当** — OpenShift の機能としては存在するが、**ROSA HCP + zero-egress 構成での成立性が未確認**のため Phase 1 では採らない。

**その他 Outbound 要求**:

| # | 要求 | 内容 |
|---|------|------|
| REQ-OUT-01 | Egress ルールグループ設置 + 更新委任（上記 D-U6-13 本文） | — |
| REQ-OUT-02 | デフォルト Deny の維持 | Broker/IdP-KC の **Worker サブネット CIDR** からの許可外 Egress は drop + alert（C2 通信検知。弊社側も SG Egress 最小化で二重化、ADR-010） |
| REQ-OUT-03 | Firewall Alert/Flow ログの共有 | Network Firewall Alert Log と該当 Flow Log を弊社監査 Acct へ配信（S3 レプリケーション or 購読）。ITDR（L-GD 系検知、ADR-060 §C.2.2）の入力に必要 |
| REQ-OUT-04 | DNS 解決の整合 | 顧客 IdP FQDN の名前解決経路（Route 53 Resolver）と Firewall の FQDN 評価が同一解決系であること（DNS 分裂による誤 drop 防止） |

### 6.7.4 要求仕様の運用

- 本節を抜粋した「要求仕様書 v1」を別紙として先方へ提示し、**回答（可否・SLA・実装時期）を REQ 番号単位で本書に追記**する。
- 受入確認: REQ-IN 系は疎通試験（弊社テストドメインで 403/秘密ヘッダ/XFF の実挙動確認）、REQ-OUT 系はテスト IdP ドメインの追加所要時間実測（G-EGRESS の実測値）で行う。

---

## 6.8 未決事項と他単元への引き渡し

### 6.8.1 未決事項（オープン項目）

| # | 項目 | 内容 | 期限/ゲート |
|---|------|------|------------|
| O-1 | **G-OSAKA** | 大阪 ap-northeast-3 の c7g/c7i 系在庫 + vCPU クォータ実確認（+ ROSA HCP arm64 Machine Pool / RHBK Operator arm64 対応確認、§6.2.2） | Phase 1 前 PoC ゲート（U1 §1.5） |
| O-2 | **G-EGRESS** | Egress 許可方式（②+③ vs ① SLA ≤ 4 営業時間）の先方合意。未合意なら §NFR-3 リードタイム改訂へエスカレーション | Phase 1 契約前（§6.7.3） |
| O-3 | **RDS Proxy 再評価** | U8 DR 検証で Writer Failover 時の KC 再接続時間が RTO 内訳を圧迫した場合のみ再評価（現決定: 不採用 D-U6-09） | U8 検証後 |
| O-4 | **Inbound ALB or NLB の先方確認** | パターン In-A / In-B のどちらか（弊社推奨 = In-B NLB パススルー）。回答により KC proxy 設定・証明書運用が分岐（§6.7.2） | 要求仕様書 v1 回答時 |
| O-5 | B-BROK-1（フェデ比率） | 回答受領で §6.5.3 → §6.2.3 を再計算（IdP-KC 3〜17 ノードの幅が確定） | ヒアリング |
| O-6 | ROSA 3y 契約見積 | Worker fee 55% 引 + cluster fee 割引有無（aws-redhat-partnerteam 経由）。§6.2.3 は 55% 仮定 | 発注前 |
| O-7 | NW Acct の管理主体確認 | 「他組織想定（要確認）」の確定。弊社管理なら §6.6.2 VPN 経路の位置づけが「保証可能」に昇格 | 要求仕様書 v1 回答時 |
| ~~O-8~~ | ~~U3-OP-2: `idmap` DB 配置~~ | ✅ **2026-08-07 確定（[ADR-063](../adr/063-brand-unit-architecture.md)）: idmap/authz/projection はブランド(IdP-KC)アカウントローカル + Option C で Keycloak identity Aurora と別 Aurora/CMK/IAM/SG（U7 D-U7-19）**。旧「Broker Acct 別 DB」は上書き | クローズ |
| O-9 | **管理コントロールプレーン実行形態（idm-api〔ブランド主役〕+ shadow 制御 + SCIM Facade + 非同期の糊）** | ✅ **Lambda で確定（[ADR-062](../adr/062-idm-api-execution-form-lambda.md)、2026-08-06）**。トポロジは [ADR-063](../adr/063-brand-unit-architecture.md) で brand 主役（idm-api が CRUD+authz、中央は shadow 制御のみ）。残る実装論点は cold start 緩和・内部 NLB 堅牢化・**越境イベント経路の S2S 認可（旧 O-12 再定義）**、レイテンシ/読取 p99 は G-SCIM 実測 | 確定（ADR-062/063）。実装論点は越境イベント S2S / G-SCIM |
| O-10 | **Egress 形態: 案 A（NAT GW）vs 案 B（egress zero + TGW）** | 案 B は NAT 不要 + P-18/PCI DSS 志向と整合し**積極検討**（§6.2.1/§6.7.3、U7 D-U7-16 でセキュリティ推奨済み）。**（2026-07-24 公式検証）機能名 = "egress zero"、2025Q1 GA、`--properties zero_egress:true`。ミラーは Red Hat が用意する in-region ECR（顧客自前構築ではない、VPC Endpoint 経由）。制約: ① Lightspeed/Telemetry 系機能不可 ② OperatorHub は Red Hat 製 Operator の default チャネルのみミラー → **RHBK Operator の利用チャネルが default であることの確認が採用条件** ③ ROSA CLI v1.2.45+ ④ zero_egress はプラットフォーム egress の排除であり、アプリの外向き（フェデ/HIBP/Webhook）は別管理（REQ-OUT 系）**。先方 TGW 接続可否と併せて決定 | 要求仕様書 v1 回答時（先方経路確認と同時） |
| O-11 | **infra Pool サイジング実測** | c7g.large × 2〜3 暫定（§6.2.2）。1000+ IdP 時の Prometheus 時系列カーディナリティ + **Fluent Bit Aggregator のマスキング処理量**の実測（G-IdP-Scale P-4 と併せて）で確定。**⚠ c7g.large(4GB) は 1000+ IdP・10M MAU の Prometheus には不足懸念 — 比較対象に c7g.xlarge(8GB) とメモリ最適化系(r7g.large 16GB / m7g.large 8GB)を併記して実測**（台数でなくサイズで吸収する方針、2026-07-24 追記） | G-IdP-Scale 実施時 |
| **O-12** | **ノード時刻同期の実装確認と責任分界（D-U6-17）** | ROSA worker の chrony が Amazon Time Sync Service を向いているか / ずれた場合の是正は Red Hat SRE と弊社のどちらの作業か。**ノード OS は Red Hat 管理領域のため弊社が直接設定できない可能性**（§6.2.2b）。**時刻ずれは `auth_time`/`max_age`・TOTP・ID Token 検証を同時に壊す**が、責任範囲が未定義 | **Red Hat 照会（RH-C 群）+ Phase 1 実装前** |
| O-APP-1 | **アプリ inbound を NFW に通す経路設計（サーバーレス App 用）** | 2026-07-28、[06a §A.1.1](06a-network-flow-diagrams.md)。①静的 SPA(S3) = CloudFront+WAF+**OAC 直結で NFW 経路外**（LB 経由不要が公式推奨。**2026-08-06: 静的 SPA と API GW は NFW 通過必須の例外〔組織確定、REQ-IN-12〕ゆえ OAC 直結で準拠**。launchpad./admin. の SPA も同様）②API = CloudFront **VPC origins → 監査 ALB → NFW → Private API GW(Interface Endpoint)**。要検証: VPC origins の CloudFront→オリジン通信をどの**ルートテーブルで firewall endpoint に通すか**（VPC origins は NACL 非評価・TLS リスナー付き NLB 不可）+ Private API GW の execute-api ENI IP の**動的追従**（Lambda カスタムリソース）+ 監査 Acct LB→案件 Acct への **VPC ピアリング/TGW 要求（REQ-IN 追加）** | サーバーレス App 採用時（他組織エッジ設計と合同） |

### 6.8.2 U8（可用性・DR）への引き渡し

- 物理配置確定分: 大阪パイロットライト 2 クラスタ（§6.2.3/6.2.4）、Aurora Global 2 系統（§6.4.1）、PrivateLink は大阪側にも同構成で複製（Endpoint/Service とも Region 内リソースのため**大阪で別途作成が必要** — Failover 時の Broker→IdP-KC 経路断を防ぐ）。
- 検証依頼: ①Writer Failover 時の jdbc-ping 挙動と KC 再接続時間（O-3 の判定材料）、②大阪 Machine Pool スケールアップ所要時間（RTO 内訳）、③他組織 Inbound エッジの DR 切替（Route 53 Failover は誰の管理か — P-18 の DR 版として要求仕様に追補が必要か判定）。

### 6.8.3 U9（運用・監視・IaC）への引き渡し

- 監視: IdP 系 Admin API p99 / ログイン p99 を **IdP 数の関数として継続計測**（P-16 必須対策 7）、`infinispan_cache_hit_ratio` ≥ 90%（§6.5.5）、IdP-KC Scale-Out 予兆トリガ（§6.5.4）、PrivateLink Endpoint の疎通監視。
- Runbook / 禁則: realm 全体 export/import 禁止（§6.5.5）、クラスタ全 Pod 同時再起動は Writer 安定後（§6.4.2）、SSM/VPN 二重経路の切替手順（§6.6.2）。
- IaC: Terraform state は Acct ごと分離（§6.1.2）+ 1000+ IdP の state 分割 or オンボーディング API 化（P-16 必須対策 5）。IdP オンボーディングパイプラインに **REQ-OUT-01 の FQDN 更新ステップを組み込む**（G-EGRESS 合意形態に依存）。
- ADR-055 CI/CD 併記（EKS vs ROSA）は ROSA HCP 側で確定させる。

### 6.8.4 決定一覧（サマリ）

| # | 決定 | 節 |
|---|------|-----|
| D-U6-01 | 6 アカウント体系確定（Broker / IdP-KC 分割、NW 監査 = 他組織） | §6.1.1 |
| D-U6-02 | クロスアカウント IAM 8 経路限定（EventBridge idmap 更新 + ITDR PutEvents + **削除 shadow / 初回 sub 通知**〔2026-08-06 制御プレーン 2 追加、ADR-063〕）、Broker↔IdP-KC 間 IAM Role なし | §6.1.2 |
| D-U6-03 | ROSA HCP × 2、3 AZ × Machine Pool、Private NLB Ingress + 自管理 Internal ALB。**CP = Red Hat 管理、Infra Node なし、Egress 形態は O-10（NAT vs zero-egress）** | §6.2.1 |
| D-U6-04 | **役割分離 2 Pool 構成（KC 専用 taint Pool + default/infra Pool c7g.large×2-3）**。KC = c7g.xlarge、2xlarge は事前定義の別 Pool（Blue/Green）、arm64 要確認 | §6.2.2 |
| D-U6-05 | コスト概算 ROSA 4 クラスタ ≈ **$2,032/月**（infra Pool 別建て +$354、3y 55% 仮定） | §6.2.3 |
| D-U6-06 | Broker→IdP-KC バックチャネル = PrivateLink（フロントチャネルはエッジ経由） | §6.3.2 |
| D-U6-07 | Aurora PG16（Broker / IdP-KC 各系統）、SG 直接続、Global DB。**2026-08-07: ブランド(IdP-KC)アカウントは Keycloak identity Aurora に加え authz 系 Aurora（authz/idmap/projection）を別建て（Option C 内部分離、ADR-063 / U7 D-U7-19）** | §6.4.1 |
| D-U6-08 | Writer エンドポイントのみ + **プール initial=min=max=30 等値**（KC 公式推奨、チャーン回避）、予約枠控除評価、jdbc-ping 運用制約 | §6.4.2 |
| D-U6-09 | RDS Proxy 暫定不採用 | §6.4.3 |
| D-U6-10 | Infinispan realms 系キャッシュ初期値 200k entries 他 | §6.5.5 |
| D-U6-11 | /admin 3 層防御 + `hostname-admin` 分離採用（L2 Listener 403 が生命線） | §6.6.1 |
| D-U6-12 | Internal 経路 = SSM 標準 + VPN 併用の二重化 | §6.6.2 |
| D-U6-13 | Egress 要求 = 専用ルールグループ + 更新委任（②+③）、フォールバック SLA ≤ 4 営業時間 | §6.7.3 |
| **D-U6-17** | **ノード時刻同期 = Amazon Time Sync Service に統一、許容ずれ ±1 秒。セッション TTL には影響せず、`auth_time`/`max_age`・TOTP・ID Token 検証・監査相関に効く** | **§6.2.2b** |

---

## 改訂履歴

- 2026-08-25: **§6.7.3 の REQ-OUT-01 送信元表記を是正** — 「送信元 = Broker KC Pod CIDR」は**実現できない**（ROSA/OVN では Pod IP が VPC に出ず、クラスタ外向きはノード IP に変換される。かつ KC Pool と infra Pool が同一 Worker サブネットに同居）。**「Broker クラスタの Worker サブネット CIDR〔3AZ 分〕」へ正確化**し、粒度の限界・残余リスク評価・不採用案（KC Pool 専用サブネット分離 / EgressIP）を注記として追加。**先方へ「KC Pod だけに絞っている」と説明しない**（受入試験で齟齬）。REQ-OUT-02 も同様に是正。経路の全体像は [06a §A.1.3](06a-network-flow-diagrams.md)。
- 2026-08-24: **§6.2.2b 決定 D-U6-17 新設（ノードの時刻同期）** — 設計 10 冊に時刻同期の要件が一箇所も無かったため新設。Amazon Time Sync Service 統一・許容 ±1 秒。**セッション TTL には影響しない**（各サーバ自己完結）が、`auth_time`/`max_age`・TOTP・ID Token 検証・監査相関に効くことを表で明示。**未決 O-12**（ROSA worker の chrony 設定確認と是正の責任分界 → [RH-C-07](../requirements/redhat-inquiry/00-plan.md)）。
- 2026-08-12: **D-U6-14 新設（§6.6.3）** — テナント隔離契約 + 認証フローのテナント別公平性（noisy-neighbor 対策 + `tenant_id` 一貫強制 + realm 分離脱出条件、B-TENANT-ISO-1）。

- 2026-07-23: 初版（Wave 1 起草）。Baseline v1（P-01〜P-18）準拠。A 部（自管理設計）/ B 部（他組織要求仕様）の 2 部構成で確定。B-BROK-1 / G-OSAKA / G-EGRESS / In-A/In-B 先方確認は未決事項として §6.8 で追跡。
- 2026-08-07: **認可データ配置粒度 = A+C を反映（[ADR-063](../adr/063-brand-unit-architecture.md) / U7 D-U7-19）** — idmap/authz/projection はブランド(IdP-KC)アカウントローカル（O-8 クローズ）、Keycloak identity Aurora とは別 Aurora/CMK/IAM/SG に内部分離（D-U6-07 に authz 系 Aurora 別建てを明記）。
- 2026-08-06: **REQ-IN-12 訂正 = API GW 例外で元設計維持**（組織方針の正確化: 全 inbound NFW 必須だが**静的 SPA と API GW は例外**。よって api. = CloudFront→API GW→Lambda のまま準拠、Option 2 不要、ADR-062 の撤回も取消）。O-APP-1 / 06a の "静的 S3 非準拠" flag も撤回（静的 SPA は例外ゆえ OAC 直結で準拠）。
- 2026-08-06: **REQ-IN-12（api. = idm-api Lambda inbound の NFW 通過要否 + 到達方式）を実体化**（予約採番 → 表に追加）。Q1(a)。3 案〔(1) exception / (2) ALB→Lambda ターゲットで NFW 経路〔弊社推奨〕/ (3) Private API GW〕を提示し先方回答事項に。REQ-IN-13 に api.(Option 2) を追記。
- 2026-08-06: **D-U6-11 の Admin API 内部 NLB 表現を正確化** — 「最厳格/露出」→「`scheme=internal` でインターネット非露出、in-cluster との差は VPC 内到達経路が 1 本増える分（SG を Lambda SG 限定 + server-TLS + アプリ層認証で緩和）、idm-api 侵害時の Admin API 到達は in-cluster と同等」。過大表現の是正。
- 2026-08-06: **削除の A 案（outbox）に伴う EventBridge 経路追加** — D-U6-02 を 6→8 経路に（制御プレーン 2 = ①削除 `user.deprovisioned`〔IdP-KC→Broker、outbox 発〕②初回 sub 通知〔Broker→IdP-KC、EventBridge の新方向〕、ADR-063 / U3 D3-16/D3-17）。
- 2026-08-06: **[ADR-062](../adr/062-idm-api-execution-form-lambda.md)（O-9 Lambda）+ [ADR-063 ブランドユニット](../adr/063-brand-unit-architecture.md)を反映** — D-U6-11 に「Admin API へは内部 NLB（scheme=internal + SG を Lambda SG 限定 + server-TLS + アプリ層認証）で到達、到達主体 = ブランド idm-api→IdP-KC / 中央 shadow 制御→Broker」を追記（ClusterIP 単独を本用途に限り見直し、/admin 403 は不変）、サブネット層③ を Lambda ENI アタッチ先と明記、O-9 を Lambda 確定に更新。**§6.3.2 の越境を再整理: 旧「中央 front door → ブランド idm-api の PrivateLink 委譲」廃止 → 越境は EventBridge 2 本（idm-api→Broker 削除 / Broker→ブランド 初回 sub 通知）のみ、旧 O-12 は越境イベント S2S 認可に再定義**（ADR-063 = idm-api ブランド主役 / 中央 shadow 制御のみ）。
- 2026-07-23 (v1.1): 整合性レビュー修正（D-U6-02 5 経路化 / REQ-IN-09 / O-8/O-9 / 専用 API 層図示 / §6.3.2 クライアント認証追記）。
- 2026-07-23 (v1.2): **ユーザー検討（[research note](research/rosa-hcp-machine-pool-egress-notes.md)）反映** — ① HCP に Infra Node なし → **役割分離 2 Machine Pool 構成**（D-U6-04 改訂、infra Pool 別建てでコスト $1,678 → $2,032/月）② CP = Red Hat 管理 + 接続 3 系統整理 + Ingress NLB 既定 ③ **Egress 形態 O-10 新設**（NAT GW 必須の明記 + zero-egress 案 B が P-18 と整合するため積極検討）④ **DB プール initial=min=max=30 等値化**（KC 公式推奨）+ max_connections 予約枠控除 + idmap 別プール独立計上 ⑤ PgBouncer はシャーディング段階の拡張パスと明記。
- 2026-07-24 (v1.4): **ユーザー検討 第 2 弾反映** — ① **大阪 KC 専用 Pool（min 0、labeled/tainted）の事前定義**（テイントなし infra のみでは Failover 時に KC Pod がスケジュール不能になる不整合を解消、§6.2.3/§6.2.4 + U8 §8.5 同期）② O-11 に infra Pool サイズ候補併記（c7g.large 4GB では Prometheus 不足懸念 → c7g.xlarge / r7g / m7g を比較対象に）③ **サブネット 4 層設計**（TGW /28・ALB 専用 /26-27・Worker /24+〔OVN のためノード数採番〕・Aurora /27-28、CIDR は install 後不変ゆえ事前確定）④ **secret header の重み付け格下げ**（主防御 = /admin 403 + SG エッジ限定、REQ-IN-06 は追加層）⑤ In-B 推奨の TLS 終端根拠補足（平文出現位置を自管理 VPC に閉じる）⑥ §6.1.1 図の簡略化注意書き。
- 2026-07-24 (v1.5): **ROSA HCP 公式ドキュメント・ファクトチェック反映**（16 項目、検証エージェント。❌1: **OLM 本体は RH 側 CP で稼働** — Worker に載るのは導入 Operator のみ / ⚠5: テイントなし Pool は「レプリカ 2 以上」条件付き〔KB 7032223: CLI 1.2.26+ は default pool テイント可〕・SA Token 表現修正〔1h は STS クレデンシャル側〕・追加 IngressController は 4.14+ HCP 可だが **LB は顧客管理扱い**・ローリング既定は **maxSurge=1/maxUnavailable=0** + PDB 保護は drain 猶予内のみ・**UWM 新規クラスタ既定無効 → Day-2 有効化必須**〔2026Q1 変更〕）。追加反映: **Graviton は HCP 2024-07 対応済み**（残確認は RHBK arm64 + 在庫のみ）/ egress zero 正式情報（2025Q1 GA、Red Hat 管理 in-region ECR、**RHBK Operator の default チャネル確認が採用条件**、Lightspeed/Telemetry 不可）/ pool 名の実体注記（workers 自動作成）/ CP→pool アップグレード順序制約（U9 引き渡し）/ AutoNode 2026Q2 は Phase 2 再評価。主要出典: AWS ROSA architecture / RH Managing machine pools / CIDR range definitions / Egress zero install / KB 7032223 / MOBB Ingress ガイド / RH Developer 2026-02-27（いずれも 2026-07-24 取得、詳細は 06a §A.2.1b）。
- 2026-07-23 (v1.3): Wave 2 整合性レビュー反映 — D-U6-02 **6 経路化**（第 6 経路: IdP-KC → Broker ITDR EventBridge PutEvents、U7 D-U7-04 / M-9）、REQ-IN-07 を **REQ-IN-07a（障害時、U8 主管）/ REQ-IN-07b（認可 Sorry、U4 別紙）に分割** + **REQ-IN-10（CF ログ scrubbing、U7 §7.3）/ REQ-IN-11（launchpad SPA 配信、U4 §4.7.4 予約）追加**（M-9）、infra Pool 積載に Fluent Bit Aggregator 追加 + O-11 見積り対象へ包含（L-2）。
