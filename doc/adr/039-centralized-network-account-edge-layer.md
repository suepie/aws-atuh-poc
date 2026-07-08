# ADR-039: ネットワーク監査アカウント設計（アプリごと独立 CloudFront/WAF + 5 アカウント体系）

- **ステータス**: Proposed（要件定義フェーズで Accepted に昇格予定）
- **日付**: 2026-06-23 作成、**2026-06-24 全面書き直し（v2、設計方針大幅変更）**、**2026-07-08 §F.1.A LDAP Egress 経路追記**
- **関連**:
  - [ADR-011 認証基盤前段ネットワーク設計](011-auth-frontend-network-design.md)（更新あり）
  - [ADR-013 CloudFront + WAF による IP 制限の置き換え戦略](013-cloudfront-waf-ip-restriction.md)（更新あり）
  - [ADR-022 AWS edge での Sorry 制御パターン](022-aws-edge-sorry-control.md)（更新あり）
  - [ADR-036 Customer Audit Support](036-customer-audit-support.md)（**Scope Reduced**、監査ログ集約 Acct との関係）
  - [§C-7 実装アーキテクチャ](../requirements/proposal/common/07-implementation-architecture.md)（§C-7.2.2 全体図 / §C-7.2.3 アカウント境界 / §C-7.3.3 Network 層 / §C-7.3.11 Sorry 制御）
  - **[ADR-025 §H 顧客 IdP が LDAP(s) の場合](025-scim-positioning-and-receive-stance.md)** — §F.1.A LDAP Egress 経路追記の起点（L-6 論点、2026-07-08 追記）
  - **[ADR-060 §C.2.2 Golden LDAP 系検知](060-auth-protocol-attack-path-residual-tbd.md)** — §F.1.A.4 監査要件連動（2026-07-08 追記）

---

## v2 書き直しの背景（2026-06-24）

初版（2026-06-23、v1）では「Network 専用アカウント 1 つに CloudFront/WAF/Lambda@Edge を集約、アプリごとに Distribution を分散」というモデルだったが、ユーザー設計レビューで以下が確定:

1. **アプリごとに 1 CloudFront + 1 WAF（独立セット）**：Distribution 単位の分散ではなく、CloudFront/WAF 自体を**アプリごとに独立**させる
2. **5 アカウント体系**：「ネットワーク Acct」「ネットワーク監査 Acct」「監査 Acct」を明確に分離
3. **/admin パス保護方針**を追記（外部 IP Deny + Internal のみ）

v1 と v2 の差分:

| 項目 | v1（2026-06-23）| **v2（2026-06-24、本版）** |
|---|---|---|
| アカウント数 | 4（Network / Auth / App / Audit）| **5**（Network / **ネットワーク監査** / 監査 / Auth / App）|
| CloudFront / WAF 配置 | Network Acct 集約、アプリごと Distribution | **ネットワーク監査 Acct**、**アプリごと独立 CloudFront + 独立 WAF** |
| Route 53 配置 | Network Acct 集約 | **各 App Acct 別管理** |
| Network Firewall | 未定義 | **ネットワーク監査 Acct** |
| /admin パス保護 | 未定義 | **外部 IP 全 Deny + Internal（VPN/社内）のみ** |

---

## Context

### 背景

弊社内の組織方針として、**ネットワークレイヤとエッジ / 通信監査レイヤを明確に分離**する体制が確定。具体的には:

- **ネットワーク Acct**：Transit Gateway 等の純粋なネットワークインフラ
- **ネットワーク監査 Acct**：CloudFront / WAF / Network Firewall 等のエッジ・通信監視レイヤ
- **監査 Acct**：AWS Organizations / CloudTrail / 監査ログ集約

ネットワーク監査 Acct には**アプリごとに独立した CloudFront + WAF セット**を配置し、アプリ間の影響分離 + アプリ別 WAF ルールカスタマイズを可能にする。

### Why（5 アカウント体系の採用根拠）

| 理由 | 詳細 |
|---|---|
| **責任分担明確化** | Network チーム / Network 監査チーム / Compliance チーム / 認証基盤チーム / アプリチーム の責任範囲が AWS Acct で完全分離 |
| **アプリ間影響分離** | 1 アプリの WAF 設定変更や障害が他アプリに影響しない（独立 CloudFront + 独立 WAF）|
| **アプリ別 WAF ルールカスタマイズ** | アプリの脅威モデルや要件に応じて WAF ルールをチューニング可能 |
| **規制業種顧客への対応** | エッジ層も含めて監査対象を AWS Acct で明示分離 |
| **AWS Well-Architected 準拠** | Multi-account strategy + Centralized Network Services の組合せ |

### Why（アプリごと独立 CloudFront/WAF の採用根拠）

| 理由 | 詳細 |
|---|---|
| **Blast Radius 最小化** | 1 アプリの CloudFront / WAF 障害が他アプリに波及しない |
| **WAF ルールアプリ別カスタマイズ** | カード会員データ取扱アプリは厳格 WAF、社内ツールは緩い WAF など |
| **デプロイ独立性** | アプリチームごとに CloudFront / WAF の設定変更を独立リリース可能 |
| **顧客監査時のスコープ限定** | 「カード会員データ取扱アプリのみ」など監査範囲を CloudFront 単位で限定可 |

### 業界用語の整理

| 用語 | 意味 |
|---|---|
| **ネットワーク Acct** | AWS Multi-account 戦略における Transit / VPC / DX 等のインフラ集約 Acct |
| **ネットワーク監査 Acct** | エッジ（CloudFront/WAF/Lambda@Edge）+ 通信監視（Network Firewall）の集約 Acct（弊社独自命名）|
| **監査 Acct**（コンプラ監査）| AWS Organizations / CloudTrail / 監査ログ S3 の集約 Acct |
| **Network Firewall** | AWS マネージドステートフルファイアウォール、VPC 内部 / Transit GW 経由通信検査 |
| **Centralized Egress** | アウトバウンド通信を集約 Acct 経由に統一する設計パターン |
| **VPC Origins**（2024-12 GA）| CloudFront から内部 ALB へ Cross-Account PrivateLink 接続 |
| **OAC**（Origin Access Control）| S3 への CloudFront 限定アクセス制御 |
| **Per-app CloudFront** | アプリごとに独立した CloudFront Distribution + 独立 WAF Web ACL |

---

## Decision

### 採用方針

**「5 アカウント体系 + アプリごと独立 CloudFront/WAF」**を採用。CloudFront / WAF / Lambda@Edge / Network Firewall / Shield Advanced を**ネットワーク監査 Acct**に集約し、アプリごとに独立した CloudFront + WAF セットを配置。Route 53 は各 App Acct で別管理。

### 主要判断

| 判断ポイント | 採用 |
|---|---|
| **アカウント数** | **5（Network / ネットワーク監査 / 監査 / Auth Platform / App × N）** |
| **CloudFront/WAF 配置** | **ネットワーク監査 Acct**、**アプリごと独立 CloudFront + 独立 WAF**（1 アプリ = 1 CloudFront + 1 WAF）|
| **Route 53 配置** | **各 App Acct で別管理**（Hosted Zone はアプリチーム所有）|
| **Network Firewall** | **ネットワーク監査 Acct**（Centralized Egress + 通信検査）|
| **Transit Gateway** | **ネットワーク Acct**（純粋なネットワークインフラ）|
| **Shield Advanced** | **ネットワーク監査 Acct**で全社購入（$3K/月 × 1）|
| **CloudTrail Organization Trail** | **監査 Acct**（コンプラ統制）|
| **/admin パス保護** | **外部 IP 全 Deny + Internal（VPN/社内 → Transit GW → Internal ALB）のみ** |
| **Cross-Account 接続** | Public ALB + secret header / VPC Origins / OAC の 3 パターン |

---

## A. 5 アカウント体系の詳細

### A.1 アカウント別の役割

```mermaid
flowchart TB
    subgraph N["🔷 ネットワーク Acct"]
        TGW[Transit Gateway]
        VPCPeer[VPC Peering]
        DX[Direct Connect]
        VPN[Site-to-Site VPN]
    end

    subgraph NA["🟣 ネットワーク監査 Acct (NEW)"]
        CFA[CloudFront-A<br/>+ WAF-A<br/>auth.basis.example.com]
        CFB[CloudFront-B<br/>+ WAF-B<br/>app-a.example.com]
        CFC[CloudFront-C<br/>+ WAF-C<br/>app-b.example.com]
        LEA[Lambda@Edge-A]
        LEB[Lambda@Edge-B]
        NFW[Network Firewall]
        SA[Shield Advanced<br/>全社購入]
        ACM[ACM Certs<br/>(CloudFront 用)]
    end

    subgraph A["🔵 監査 Acct"]
        ORG[AWS Organizations]
        OT[CloudTrail<br/>Organization Trail]
        AUS3[監査ログ集約 S3<br/>Object Lock 7 年]
        SIEM[SIEM 連携]
    end

    subgraph AP["🟠 Auth Platform Acct"]
        BKC[Broker Keycloak<br/>+ Public ALB]
        IKC[IdP Keycloak<br/>+ Internal ALB]
        AURORA[Aurora]
        SPA[S3 SPA bundles]
        ADMIN[Admin Backend Lambda]
    end

    subgraph APP["🟢 App Acct A/B/C"]
        R53A[Route 53<br/>Hosted Zone]
        IALB[Internal ALB]
        ECS[ECS / Lambda / DB]
    end

    R53A -.|DNS A レコード| CFB
    R53A -.|DNS A レコード| CFC
    CFB -.|VPC Origins| IALB
    CFC -.|VPC Origins| IALB
    CFA -.|secret header| BKC
    CFA -.|OAC| SPA
    LEA --> CFA
    LEB --> CFB

    N -.|Transit GW Attachment| AP
    N -.|Transit GW Attachment| APP
    NFW -.|通信検査| N

    OT -.|集約| AUS3

    style N fill:#cfe8ff
    style NA fill:#fff3e0
    style A fill:#e3f2fd
    style AP fill:#fce4ec
    style APP fill:#e8f5e9
```

### A.2 アカウント別責務マトリクス

| アカウント | 担当チーム | 含むリソース | 責務 |
|---|---|---|---|
| 🔷 **ネットワーク Acct** | Network チーム | Transit Gateway / VPC ピアリング / Direct Connect / Site-to-Site VPN | 純粋なインフラネットワーク（L3 接続性）|
| 🟣 **ネットワーク監査 Acct** | Network 監査チーム | **アプリごとの独立 CloudFront + WAF**（n セット）/ Lambda@Edge / Network Firewall / Shield Advanced / ACM（CloudFront 用） | エッジ層 + 通信監視（L4-L7）、WAF ルール一元統制 |
| 🔵 **監査 Acct** | Compliance チーム | AWS Organizations / CloudTrail Organization Trail / 監査ログ集約 S3（Object Lock 7 年）/ Security Hub / GuardDuty 集約 | 組織統制 + コンプライアンス監査 |
| 🟠 **Auth Platform Acct** | 認証基盤チーム | Broker KC + IdP-KC EKS / Aurora / SPA S3 / ITDR / Admin Backend / ユーザ管理画面 Backend | 認証コア機能 |
| 🟢 **App Acct（複数）** | 各アプリチーム | Internal ALB / ECS / Lambda / DB / Route 53 Hosted Zone（アプリ別ドメイン） | 業務アプリ |

### A.3 ネットワーク Acct vs ネットワーク監査 Acct の境界

| 観点 | ネットワーク Acct | ネットワーク監査 Acct |
|---|---|---|
| **責任範囲** | L3 接続性（インフラネットワーク）| L4-L7 通信制御 + 監査 |
| **代表リソース** | Transit Gateway / VPC ピアリング / DX / VPN | CloudFront / WAF / Lambda@Edge / Network Firewall / Shield |
| **チーム** | Network エンジニア（インフラ寄り）| Network 監査 / Security エンジニア（セキュリティ寄り）|
| **変更頻度** | 低（インフラ変更は稀）| 中（WAF ルールは継続更新）|
| **監査頻度** | 年次 | 継続的（WAF Block ログレビュー等）|

---

## B. アプリごと独立 CloudFront/WAF 設計

### B.1 配置パターン

```mermaid
flowchart LR
    User[ユーザー]
    R53[各 App Acct<br/>Route 53]

    subgraph NA["🟣 ネットワーク監査 Acct"]
        CFA["CloudFront-Auth<br/>+ WAF-Auth<br/>(独立)"]
        CFA1["CloudFront-AppA<br/>+ WAF-AppA<br/>(独立)"]
        CFA2["CloudFront-AppB<br/>+ WAF-AppB<br/>(独立)"]
        CFA3["CloudFront-AppC<br/>+ WAF-AppC<br/>(独立)"]
        LEA[Lambda@Edge-Auth]
        LE1[Lambda@Edge-A]
    end

    subgraph AP["🟠 Auth Platform Acct"]
        BKC[Broker KC<br/>Public ALB]
        SPA[S3 SPA]
    end

    subgraph APPS["🟢 App Acct A/B/C"]
        IALB1[App A Internal ALB]
        IALB2[App B Internal ALB]
        IALB3[App C Internal ALB]
    end

    User --> R53
    R53 -->|auth.basis.example.com| CFA
    R53 -->|app-a.example.com| CFA1
    R53 -->|app-b.example.com| CFA2
    R53 -->|app-c.example.com| CFA3
    CFA --> BKC
    CFA --> SPA
    CFA --> LEA
    CFA1 --> IALB1
    CFA1 --> LE1
    CFA2 --> IALB2
    CFA3 --> IALB3

    style NA fill:#fff3e0
    style AP fill:#fce4ec
    style APPS fill:#e8f5e9
```

### B.2 CloudFront / WAF セット定義

| CloudFront 名 | ドメイン | 主 Origin | WAF ルール |
|---|---|---|---|
| **CloudFront-Auth**（認証基盤用）| `auth.basis.example.com` | Auth Acct Public ALB（Broker KC）+ S3（SPA）| Common + Targeted + ATP + 認証専用 Rate Limit |
| **CloudFront-Admin**（ユーザ管理画面）| `admin.basis.example.com` | Auth Acct Public ALB（Admin Backend）+ S3（Admin SPA）| Common + Targeted + 厳格 Rate Limit |
| **CloudFront-AppA**（業務アプリ A）| `app-a.example.com` | App Acct A Internal ALB（VPC Origins）| Common + アプリ A 独自ルール |
| **CloudFront-AppB**（業務アプリ B）| `app-b.example.com` | App Acct B Internal ALB | Common + アプリ B 独自ルール |
| ... | ... | ... | ... |

各 CloudFront + WAF は **完全独立**。1 つの設定変更が他に影響しない。

### B.3 アプリ別 WAF ルールカスタマイズ例

| アプリ種別 | WAF Web ACL ルール例 |
|---|---|
| **カード会員データ取扱アプリ**（PCI DSS 適用）| Common + Targeted + ATP + Bot Control + Geo-Match（国内のみ）+ 厳格 Rate Limit + IP Allowlist |
| **社内向けツール** | Common + IP Allowlist（社内 NW のみ）+ 緩い Rate Limit |
| **公開 API**（取引先連携）| Common + 取引先 IP Allowlist + API Token 検証 |
| **認証エンドポイント** | Common + Targeted + ATP（[ADR-042](042-bot-detection-captcha.md)）+ 認証専用 Rate Limit |

### B.4 アプリごと独立のメリット / デメリット

| 項目 | メリット | デメリット |
|---|---|---|
| Blast Radius | アプリ間影響完全分離 | 共通ルール変更は全 WAF に手動反映必要（IaC で緩和）|
| WAF カスタマイズ | アプリ別最適化可能 | ルール重複保守 |
| デプロイ独立性 | アプリチーム独立リリース | デプロイ調整は不要 |
| コスト | — | WAF Web ACL × アプリ数（$5/月 × 10 = $50/月）+ ルール費用 |
| 監査範囲限定 | 「カード扱いアプリのみ」等の限定監査が容易 | — |

---

## C. Cross-Account 接続パターン（3 種）

| パターン | 用途 | 実装 |
|---|---|---|
| **Public ALB + secret header** | Broker Keycloak（HTTPS、認証コア）| ALB 公開、CloudFront から `X-CloudFront-Secret` 付き転送、ALB Listener Rule で検証 |
| **VPC Origins**（推奨、2024-12 GA）| App Acct の Internal ALB | CloudFront → PrivateLink → Internal ALB（ALB 公開不要、最も安全）|
| **OAC**（Origin Access Control）| Auth Acct S3 SPA bundles | S3 バケットポリシーで `aws:SourceArn` を該当 CloudFront ARN に制限 |

### C.1 VPC Origins 採用判断

アプリ Acct の Internal ALB は **VPC Origins 強く推奨**:
- ALB を公開不要（最も安全）
- CloudFront ↔ ALB の通信は AWS バックボーン経由
- セキュリティグループは CloudFront プレフィックス許可不要

### C.2 認証基盤の Public ALB 採用理由

Broker KC は VPC Origins ではなく Public ALB + secret header:
- 顧客 IdP からの SAML AuthnRequest 等で**Public IPv4 アクセスが必要**（VPC 内 PrivateLink 不可）
- 代わりに**WAF + secret header + ALB SG 制限**の 3 層防御で保護

---

## D. Route 53 各 App Acct 別管理

### D.1 配置パターン

| ドメイン | Hosted Zone 配置 | 管理者 |
|---|---|---|
| `basis.example.com`（認証基盤ルート）| **Auth Platform Acct** | 認証基盤チーム |
| `auth.basis.example.com`（CloudFront-Auth）| Auth Platform Acct | 認証基盤チーム |
| `admin.basis.example.com`（CloudFront-Admin）| Auth Platform Acct | 認証基盤チーム |
| `app-a.example.com`（App A 用）| **App Acct A** | アプリ A チーム |
| `app-b.example.com`（App B 用）| **App Acct B** | アプリ B チーム |
| ... | ... | ... |

### D.2 Route 53 → CloudFront 連携

各 App Acct の Route 53 から、ネットワーク監査 Acct の CloudFront へ A レコード（Alias）で接続:

```hcl
# App Acct A の Route 53 設定例
resource "aws_route53_zone" "app_a" {
  name = "app-a.example.com"
}

resource "aws_route53_record" "app_a_alias" {
  zone_id = aws_route53_zone.app_a.zone_id
  name    = "app-a.example.com"
  type    = "A"

  alias {
    name                   = "d1xxxxx.cloudfront.net"  # ネットワーク監査 Acct CloudFront
    zone_id                = "Z2FDTNDATAQYW2"  # CloudFront 固定 Zone ID
    evaluate_target_health = false
  }
}
```

→ DNS は各アプリチームが自律的に管理、エッジは Network 監査チームが統制。

---

## E. /admin パス保護方針（追記）

### E.1 KC ネイティブ `/admin` パス（Keycloak Admin Console）の保護

弊社運用者のみがアクセスする KC ネイティブ Admin Console は **外部からアクセス不可** とする:

| 設定箇所 | 設定内容 |
|---|---|
| **CloudFront-Auth WAF（WAF-Auth）** | `/admin/*` パスに対して **全 IP Deny ルール**（最優先）|
| **Auth Platform Acct ALB Listener Rule** | `/admin/*` パスは Internal ALB Listener のみ受付、Public ALB Listener では返却 403 |
| **Internal アクセス経路** | VPN / 社内 Network → **Transit Gateway** → Auth Platform Acct Internal ALB → Keycloak `/admin` |

### E.2 アクセスフロー

```mermaid
flowchart LR
    Op[弊社運用者<br/>社内 PC]
    VPN[VPN / 社内 NW]
    TGW[Transit Gateway<br/>(Network Acct)]
    IALB[Auth Acct<br/>Internal ALB]
    KC[Keycloak<br/>/admin]

    Op --> VPN
    VPN --> TGW
    TGW --> IALB
    IALB --> KC

    Attacker[外部攻撃者]
    CF[CloudFront-Auth<br/>(ネットワーク監査 Acct)]
    WAF[WAF-Auth<br/>/admin Deny]

    Attacker -.|/admin リクエスト| CF
    CF --> WAF
    WAF -.|403 Forbidden| Attacker

    style Op fill:#e3f2fd
    style Attacker fill:#ffcdd2
    style WAF fill:#fff3e0
```

### E.3 ユーザ管理画面（`admin.basis.example.com`）との区別

| 種類 | URL | アクセス | 保護方針 |
|---|---|---|---|
| **KC ネイティブ `/admin`**（Keycloak Admin Console）| `auth.basis.example.com/admin` | **弊社運用者のみ**（社内 NW 経由）| **外部 IP 全 Deny + Internal のみ** |
| **ユーザ管理画面**（独自 SPA、[ADR-038](038-tenant-admin-portal.md)）| `admin.basis.example.com` | **顧客テナント管理者**（外部からアクセス可）| 通常の WAF + テナントスコープ強制 |

→ 2 つは別ドメイン / 別 CloudFront / 別 WAF で**完全分離**。

---

## F. Network Firewall + Shield Advanced

### F.1 Network Firewall

ネットワーク監査 Acct に Network Firewall を配置し、**Transit Gateway 経由の通信を検査**:

| 対象 | 内容 |
|---|---|
| **Egress 集約検査** | VPC → インターネットへの通信を Network Firewall で検査（C&C 通信 / DLP）|
| **East-West 検査** | Auth Acct ↔ App Acct ↔ Network Acct 間の通信を必要に応じて検査 |
| **ステートフル ルール** | Suricata 互換ルール、AWS Managed Rules + 独自ルール |
| **LDAP(s) 顧客 AD への egress**（2026-07-08 追加、[ADR-025 §H.6](025-scim-positioning-and-receive-stance.md) L-6 論点）| **Auth Acct EKS Pod → 顧客 AD (TCP 636)** を Network Firewall で許可 + 監査（詳細下記 §F.1.A）|

### F.1.A LDAP(s) 顧客 AD への Egress 経路（2026-07-08 追加、ADR-025 §H 波及）

顧客 IdP が LDAP(s) 直結の場合（[ADR-025 §H](025-scim-positioning-and-receive-stance.md)）、**Auth Acct の Keycloak Pod から顧客 AD への outbound 通信**が必要になる。本節でその経路と監査を明示する。

#### F.1.A.1 経路 3 パターン（ヒアリング [B-LDAP-7](../requirements/hearing-checklist.md) 選択）

| 経路 | 用途 | 帯域 / 遅延 | 冗長化 | 適用顧客 |
|---|---|---|---|---|
| **① Direct Connect**（推奨、金融/大企業）| 顧客オンプレ AD への専用線 | 大帯域 / 低遅延（<10 ms）| DX 2 本 + BGP | 金融 / 製造 / 官公庁 |
| **② Site-to-Site VPN** | 中小顧客 or Phase 1 開始時 | 中帯域 / 中遅延（20-50 ms）| VPN 2 本 + BGP | 中小 / 開発 / Staging |
| **③ VPC Peering / TGW**（顧客 AD が AWS 内）| 顧客が自社 AWS Acct で Managed AD 運用 | AWS 内部 / 極低遅延（<5 ms）| AWS SLA | AWS ネイティブ顧客 |
| ❌ Public LDAPS | **原則禁止**（要例外承認）| — | — | 要例外承認 |

#### F.1.A.2 通信フロー（例：Direct Connect 経路）

```
[Auth Acct]                                    [顧客オンプレ]
Keycloak Pod (EKS)
    │
    ▼
Auth Acct VPC (Private Subnet)
    │
    ▼
Transit Gateway Attachment (Auth Acct)
    │
    ▼
【Transit Gateway】(ネットワーク Acct)
    │
    ▼
【Network Firewall】(ネットワーク監査 Acct)
    │ ┌── ルール: allow tcp:636 dest=customer-ad-cidr src=keycloak-pod-cidr
    │ ├── 監査: VPC Flow Log + Network Firewall Alert Log
    │ └── DPI: TLS ハンドシェイクのみ検査（LDAPS 内容は暗号化されており DPI 不可）
    │
    ▼
Direct Connect Gateway
    │
    ▼
Direct Connect (専用線)
    │
    ▼
顧客オンプレ Router
    │
    ▼
顧客 AD (TCP 636 LDAPS)
```

#### F.1.A.3 Network Firewall ルール例（Suricata 互換）

```
# Auth Acct EKS Keycloak Pod → 顧客 AD LDAPS
pass tcp $KEYCLOAK_POD_CIDR any -> $CUSTOMER_AD_CIDR 636 \
    (msg:"LDAP(S) egress to customer AD (permitted)"; \
     flow:established,to_server; \
     sid:1000101; rev:1;)

# 顧客 AD 以外への LDAP 636 は拒否 + アラート
drop tcp any any -> any 636 \
    (msg:"LDAP(S) egress to unknown destination (Golden LDAP suspicion)"; \
     sid:1000102; rev:1;)

# Plain LDAP 389 は全拒否
drop tcp any any -> any 389 \
    (msg:"Plain LDAP 389 attempt (policy violation, LDAPS required)"; \
     sid:1000103; rev:1;)
```

#### F.1.A.4 監査要件（[ADR-060 §C.2.2 L-GD](060-auth-protocol-attack-path-residual-tbd.md) 連動）

| 監査項目 | 実装 | 用途 |
|---|---|---|
| **VPC Flow Log**（Auth Acct + ネットワーク監査 Acct）| S3 → OpenSearch | 通常時の bind パターン統計、L-GD-4 IP 異常検知 |
| **Network Firewall Alert Log**| CloudWatch Logs → EventBridge → ITDR | L-GD-2 Off-hours / L-GD-4 IP 異常 の即時検知 |
| **DNS 解決ログ**（Route 53 Resolver Query Log）| S3 → OpenSearch | 顧客 AD ホスト名解決の追跡、DNS スプーフィング検知 |
| **Keycloak LDAP bind イベント**（Event Listener SPI）| EventBridge → Risk Engine | L-GD-1〜L-GD-3 / L-GD-5 の検知パイプライン ([ADR-060 §C](060-auth-protocol-attack-path-residual-tbd.md))|

#### F.1.A.5 セキュリティ考慮事項

- **LDAPS は E2E 暗号化**（Network Firewall での DPI 不可）→ **メタデータ検知（IP / 時間帯 / 頻度）が主軸**
- **Bind Service Account 資格情報は Auth Acct KMS L2 CMK で暗号化管理**（[ADR-045 §L2](045-cryptographic-key-management-strategy.md) 準拠）
- **証明書検証必須**：顧客 AD の CA 証明書を Keycloak Truststore に登録、期限監視
- **障害時フォールバック**：DX or VPN 障害時の LDAP 断は本基盤側でユーザーへ通知（[ADR-022 Sorry パターン](022-aws-edge-sorry-control.md)）

#### F.1.A.6 Phase 1 実装 TODO

- [ ] 顧客ごとの LDAP CIDR / エンドポイントの Terraform モジュール化
- [ ] Network Firewall ルールの IaC 化（Suricata ルール）
- [ ] Route 53 Resolver Forwarding rule（顧客 AD DNS 参照）
- [ ] VPC Flow Log → OpenSearch → Grafana ダッシュボード
- [ ] LDAP 断障害の Sorry 画面ルーティング（[ADR-022](022-aws-edge-sorry-control.md) 連動）

### F.2 Shield Advanced

- **配置**：ネットワーク監査 Acct（全社購入、$3K/月 × 1）
- **保護対象**：ネットワーク監査 Acct 内の全 CloudFront Distribution（アプリごと独立分すべて）
- **メリット**：DDoS 検知 + DDoS Response Team サポート + 透過的に Multi-account 保護

---

## G. コスト試算

### G.1 月額（10 アプリ想定、認証基盤 + 業務アプリ 9）

| 項目 | 月額 |
|---|---|
| CloudFront 10 個（リクエスト課金）| $500（10 アプリ合計、リクエスト量次第）|
| **WAF Web ACL 10 個**（$5 × 10）| $50 |
| **WAF Managed Rules**（Common Bot Control × 10 = $310 × 10）| **$3,100** |
| WAF ATP（認証エンドポイントのみ × 1）| $110 |
| Lambda@Edge 10 個（リクエスト課金）| $200 |
| Network Firewall（時間 $0.395 + GB $0.065）| 〜$600 |
| Shield Advanced（全社購入 × 1）| $3,000 |
| ACM（無料）| $0 |
| **合計** | **〜$7,560/月（〜$91K/年）** |

### G.2 v1（集約モデル）vs v2（アプリごと独立）コスト比較

| 項目 | v1 | v2 | 差分 |
|---|---|---|---|
| WAF Web ACL | $5 × 1 = $5 | $5 × 10 = $50 | +$45 |
| WAF Managed Rules | $310 × 1 = $310 | $310 × 10 = $3,100 | **+$2,790** |
| その他（CloudFront / Lambda@Edge 等）| 集約で割引 | 個別配置で重複 | +$200 程度 |
| **合計差分（月額）** | | | **+$3,000 / 月（+$36K/年）** |

→ **v2 のアプリ間影響分離 + WAF ルールカスタマイズのメリット**と**$3K/月 のコスト増**のトレードオフを許容。

---

## H. 移行計画

| Phase | 内容 | 期間 |
|---|---|---|
| **Phase 1** | ネットワーク監査 Acct 新規作成、ACM 証明書取得、ネットワーク Acct と分離 | 2-4 週 |
| **Phase 2** | **認証基盤用 CloudFront-Auth + WAF-Auth** をネットワーク監査 Acct で新設、テストドメインで疎通検証 | 2 週 |
| **Phase 3** | 認証基盤 DNS 切替（auth.basis.example.com → 新 CloudFront）| 1 週 |
| **Phase 4** | **/admin パス保護方針実装**（WAF 全 IP Deny + Internal 経路確立）| 2 週 |
| **Phase 5** | **ユーザ管理画面用 CloudFront-Admin + WAF-Admin** 新設 | 2 週 |
| **Phase 6** | アプリごとに順次 CloudFront/WAF セット作成 + 切替（1 アプリあたり 1-2 週、並行可）| 半年〜1 年 |
| **Phase 7** | 全アプリ切替完了 → 旧 CloudFront 削除 | 1 週 |

---

## I. 代替案検討

| 案 | 評価 | 採否 |
|---|---|---|
| **A. v1 集約モデル**（1 CloudFront + 共通 WAF、Distribution でアプリ分離）| アプリ間影響あり、WAF ルール統一限定 | ❌ v2 で書き直し |
| **B. v2 アプリごと独立 CloudFront/WAF**（本 ADR） | アプリ間影響分離 + アプリ別 WAF カスタマイズ | ✅ 採用 |
| **C. 各 App Acct で CloudFront/WAF 配置** | 統制困難、Network 監査チームの一元管理不可 | ❌ |
| **D. CloudFront/WAF を Auth Acct に配置**（旧 ADR-013 想定）| 認証基盤チームの責任過大、ネットワーク部門のガバナンス効かない | ❌ |
| **E. 4 アカウント体系**（ネットワーク + 監査統合）| ネットワーク Acct と監査 Acct の責任混在 | ❌ v2 で 5 アカウントに |

---

## Consequences

### Positive

- **5 アカウント体系**で責任分担 + 監査範囲が AWS Acct で完全明確化
- **アプリごと独立 CloudFront/WAF**で Blast Radius 最小化 + アプリ別 WAF カスタマイズ可能
- **Network チーム / Network 監査チーム / Compliance チーム / 認証基盤チーム / アプリチーム** の 5 チームの責任が完全分離
- **/admin パス保護**（外部 IP 全 Deny + Internal のみ）で KC Admin Console を堅牢化
- **VPC Origins 採用**で App Acct Internal ALB を公開不要に
- AWS Well-Architected Centralized Ingress / Multi-account 準拠

### Negative

- **WAF コスト +$3K/月**（v1 集約モデル比、アプリ 10 個想定）
- **アプリごとの CloudFront/WAF 設定の重複保守**（IaC で緩和）
- **アカウント数増**（4 → 5）で Cross-Account 設計の複雑性増
- Route 53 各 App Acct 管理で**DNS 設定の権限管理**が複雑化

### Neutral

- ネットワーク Acct（Transit GW）とネットワーク監査 Acct（CloudFront/WAF）の境界線は組織のチーム編成に依存
- Shield Advanced は全社購入で全 CloudFront を保護、追加コストなし

### 我々のスタンス

| 基本方針の柱 | 5 アカウント体系での実現 |
|---|---|
| **絶対安全** | Network Firewall + アプリごと独立 WAF + /admin 保護 + Shield Advanced |
| **どんなアプリでも** | アプリ別 WAF ルールカスタマイズで多様な要件対応 |
| **効率よく** | Network 監査チームによる WAF 一元統制 + IaC で重複保守緩和 |
| **運用負荷・コスト最小** | アプリ別独立で Blast Radius 最小化、+$3K/月 のコストは許容範囲 |

---

## J. ADR-011 / 013 / 022 への影響

| ADR | 影響 | 対応 |
|---|---|---|
| [ADR-011](011-auth-frontend-network-design.md) 認証基盤前段ネットワーク設計 | N5 カスタムドメイン / N10 WAF / Pattern C CloudFront は**ネットワーク監査 Acct での実装**に変更 | 冒頭注記を v2 方針に更新 |
| [ADR-013](013-cloudfront-waf-ip-restriction.md) CloudFront + WAF IP 制限置き換え | CloudFront / WAF は**ネットワーク監査 Acct での実装**、**/admin パス保護方針も本 ADR に統合追記** | 冒頭注記を v2 方針に更新 + /admin 追記 |
| [ADR-022](022-aws-edge-sorry-control.md) AWS edge Sorry 制御 | Lambda@Edge は CloudFront と同一 Acct 必須 = **ネットワーク監査 Acct での実装**（アプリごと独立）| 冒頭注記を v2 方針に更新 |

---

## 参考資料

- [AWS Multi-Account Strategy](https://docs.aws.amazon.com/whitepapers/latest/organizing-your-aws-environment/organizing-your-aws-environment.html)
- [AWS Centralized Ingress with CloudFront](https://aws.amazon.com/blogs/networking-and-content-delivery/centralized-ingress-with-aws-global-accelerator-and-aws-network-firewall/)
- [AWS Network Firewall Centralized Architecture](https://docs.aws.amazon.com/network-firewall/latest/developerguide/architectures.html)
- [VPC Origins for CloudFront (2024-12 GA)](https://aws.amazon.com/blogs/networking-and-content-delivery/introducing-vpc-origins-for-amazon-cloudfront/)
- [AWS Shield Advanced — Multi-account Protection](https://aws.amazon.com/shield/)
- [AWS WAF Web ACL Pricing](https://aws.amazon.com/waf/pricing/)
- [AWS Organizations + CloudTrail Organization Trail](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/creating-trail-organization.html)
