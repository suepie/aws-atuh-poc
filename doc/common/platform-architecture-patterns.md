# プラットフォーム別アーキテクチャパターン（内部技術メモ）

> 最終更新: 2026-05-18
> 位置付け: **内部技術メモ**。顧客向け説明は [proposal/common/02-platform.md](../requirements/proposal/common/02-platform.md) に最小限のみ記載
> 関連: [bff-implementation-notes.md](bff-implementation-notes.md)、[architecture.md (PoC)](architecture.md)、[identity-broker-multi-idp.md](identity-broker-multi-idp.md)、[keycloak-network-architecture.md](keycloak-network-architecture.md)、[system-design-patterns.md](system-design-patterns.md)

---

## 1. はじめに

### 1.1 ドキュメントの目的

**Cognito / Keycloak OSS / Keycloak RHBK** の 3 つのプラットフォームについて、本番想定アーキテクチャを mermaid 構成図と共に整理する内部メモ。proposal §C-2 のプラットフォーム選定の**背景資料**として、また PoC から本番設計フェーズへの**移行設計の起点**として使う。

### 1.2 本ドキュメントと他の構成図ドキュメントの位置付け

| ドキュメント | 主題 | 視点 |
|---|---|---|
| **本書（platform-architecture-patterns.md）** | **3 プラットフォーム別の本番想定構成図** | **本番設計**（最新化対象）|
| [architecture.md](architecture.md) | PoC で実装した検証構成 | PoC 実装（Phase 1-9）|
| [identity-broker-multi-idp.md](identity-broker-multi-idp.md) | Broker パターンの抽象設計 / マルチ IdP | プロトコル・属性変換 |
| [keycloak-network-architecture.md](keycloak-network-architecture.md) | Keycloak ネットワーク詳細 | ネットワーク・IP 制限 |
| [system-design-patterns.md](system-design-patterns.md) | 8 つのシステム設計パターン（IdP × SPA/SSR × DR）| 抽象パターンカタログ |
| [bff-implementation-notes.md](bff-implementation-notes.md) | BFF パターン実装詳細 | 認証クライアント層 |

→ 本書は **「本番に持っていく構成」** にフォーカスし、上記他ドキュメントへの逆参照を持つ「俯瞰ハブ」として位置付ける。

### 1.3 共通の前提

すべての構成は以下を前提とする：

- **AWS マルチアカウント**（共通認証基盤アカウント + 各アプリアカウント）
- **Identity Broker パターン（Hub-and-Spoke）**採用（[§C-1](../requirements/proposal/common/01-architecture.md)）
- **マルチ AZ 必須**（[§NFR-1](../requirements/proposal/nfr/01-availability.md)）
- **TLS 1.2+ / KMS 暗号化 / Private Subnet 配置**（[§NFR-4](../requirements/proposal/nfr/04-security.md)）
- **CloudFront + WAF 前段**（高セキュ要件時、[ADR-013](../adr/013-cloudfront-waf-ip-restriction.md)）

---

## 2. Cognito 構成パターン

### 2.1 全体構成図（本番想定）

```mermaid
flowchart TB
    Internet["👥 エンドユーザー<br/>(ブラウザ / モバイル)"]

    subgraph CDN["コンテンツ配信 + 防御層"]
        CF["☁️ CloudFront"]
        WAF["🛡️ AWS WAF<br/>(レート制限 / Bot 対策)"]
        Shield["🛡️ Shield Standard"]
        CF --- WAF
        CF --- Shield
    end

    subgraph AuthAccount["共通認証基盤 AWS アカウント"]
        direction TB
        subgraph CogPool["Cognito User Pool 層"]
            UP_C["🔴 User Pool (central)<br/>+ Identity Providers<br/>(Entra ID / Okta / SAML)"]
            UP_L["🟢 User Pool (local)<br/>(IdP なし顧客向け)"]
            HUI["Hosted UI<br/>+ Managed Login UI<br/>(Essentials+)"]
        end
        subgraph Lambdas["Cognito Lambda Triggers"]
            PTL["⚡ Pre Token Lambda V2<br/>(クレーム注入)"]
            PreSU["⚡ Pre Sign-up Lambda<br/>(ユーザー名/パスワード検証)"]
            CAC["⚡ Custom Auth Challenge<br/>(ステップアップ MFA、Plus 機能の代替)"]
        end
        Secrets_C["🔐 Secrets Manager<br/>(BFF client_secret 等)"]
        CT["📝 CloudTrail<br/>(監査ログ)"]
    end

    subgraph DRAccount["DR リージョン (大阪) <br/>※同一アカウント別リージョン"]
        UP_DR["🟣 DR User Pool<br/>(パッシブ待機)"]
    end

    subgraph AppAccount["アプリ AWS アカウント (×N)"]
        direction TB
        SPA["⚛️ SPA / SSR / Mobile"]
        subgraph BFF["BFF レイヤー (オプション)"]
            BFFλ["⚡ BFF Lambda<br/>(OAuth Agent)"]
            DDB["🗄️ DynamoDB<br/>(session 暗号化)"]
        end
        subgraph BE["バックエンド API"]
            APIGW["🟣 API Gateway<br/>(/v1/*, /v2/*)"]
            Authλ["⚡ Lambda Authorizer<br/>(JWT 検証、マルチ issuer)"]
            BEλ["🟢 Backend Lambda / ECS"]
        end
    end

    R53["🌐 Route 53<br/>+ Health Check<br/>(フェイルオーバー)"]

    Internet --> CDN
    CDN --> SPA
    SPA <-->|"OIDC (Auth Code + PKCE)"| HUI
    SPA -->|"オプション"| BFFλ
    BFFλ <-->|"OAuth + client_secret"| HUI
    BFFλ <--> DDB
    BFFλ -.- Secrets_C
    HUI -.- UP_C
    HUI -.- UP_L
    UP_C -.- PTL
    UP_C -.- PreSU
    UP_C -.- CAC
    R53 -.通常.-> UP_C
    R53 -.障害時.-> UP_DR
    SPA -->|"Bearer JWT"| APIGW
    BFFλ -->|"Bearer 代理添付"| APIGW
    APIGW --> Authλ
    APIGW --> BEλ
    Authλ -.JWKS 取得.-> UP_C
    Authλ -.JWKS 取得.-> UP_DR
    UP_C --> CT

    style CogPool fill:#fff0f0,stroke:#cc0000
    style AuthAccount fill:#fff5f5,stroke:#cc0000
    style DRAccount fill:#f5f0ff,stroke:#6600cc
    style AppAccount fill:#e8f5e9,stroke:#2e7d32
    style BFF fill:#fff3e0,stroke:#e65100
```

### 2.2 主要構成要素

| レイヤー | 構成要素 | 役割 |
|---|---|---|
| **コンテンツ配信** | CloudFront + WAF + Shield | レート制限・Bot 対策・DDoS 防御 |
| **認可サーバー** | Cognito User Pool（central / local / DR）| OIDC OP、トークン発行 |
| **ログイン UI** | Hosted UI / Managed Login UI（Essentials+）| ユーザー認証画面 |
| **拡張 Lambda** | Pre Token Lambda V2 / Pre Sign-up Lambda / Custom Auth Challenge | クレーム注入 / バリデーション / ステップアップ MFA |
| **シークレット管理** | Secrets Manager | BFF / IdP の client_secret |
| **DR** | DR Cognito User Pool（大阪、パッシブ）+ Route 53 | フェイルオーバー |
| **アプリ側** | SPA / SSR / Mobile / BFF（オプション）/ API Gateway / Lambda Authorizer / Backend | 各アプリで自由構成 |

### 2.3 ティア選定（[ADR-016](../adr/016-cognito-feature-tier-selection.md)）

| 要件 | 必要ティア | 月額単価（フェデ利用）|
|---|:---:|---|
| 基本認証（Must）| Lite | $0.015/MAU（フェデ）+ Lite |
| WebAuthn / Passkeys / パスワード履歴 / Managed Login UI | **Essentials+** | $0.015/MAU（Lite と同額）|
| 侵害クレデンシャル検出 / 詳細ロック / リスクベース MFA | **Plus** | +$0.02/MAU 追加 |

### 2.4 マルチ AZ / 可用性

| 項目 | 状態 |
|---|---|
| Cognito User Pool | ✅ AWS 自動マルチ AZ（SLA 99.9%）|
| 認証エンドポイント | ✅ AWS 透過 |
| Lambda Triggers | ✅ AWS Lambda 自動マルチ AZ |
| 単一障害点 | ✅ 排除済 |

### 2.5 DR 構成

```mermaid
flowchart LR
    DNS["Route 53<br/>auth.example.com"]
    HC["Health Check<br/>(30秒間隔)"]
    Tokyo["🔴 東京 User Pool<br/>(Primary)"]
    Osaka["🟣 大阪 User Pool<br/>(Secondary、パッシブ)"]
    Auth0["🟣 Auth0 / Entra ID<br/>(外部 IdP)"]

    DNS --> HC
    HC --> Tokyo
    HC -.障害時.-> Osaka
    Tokyo <--> Auth0
    Osaka <--> Auth0

    style Tokyo fill:#fff0f0
    style Osaka fill:#f5f0ff
```

- **Route 53 ヘルスチェック**（東京 JWKS endpoint）+ フェイルオーバーレコード
- **追加コスト**: $0.50/月（ホステッドゾーン）+ 障害月のみ大阪 MAU
- **既知の制約**: Auth0 IdP は大阪で `.well-known` 自動検出失敗 → 手動 endpoint で workaround（[ADR-007](../adr/007-osaka-auth0-idp-limitation.md)）

### 2.6 月額コスト試算（10K MAU、フェデ利用）

| ティア | Cognito 月額 | + DR | 合計 |
|---|---|---|---|
| Lite | ~$150 | $0.50 | **~$150** |
| Essentials | ~$150（連携課金同額）| $0.50 | **~$150** |
| Plus | ~$350（+ $0.02/MAU）| $0.50 | **~$350** |

→ MAU に比例してスケール。インフラ固定費なし。

---

## 3. Keycloak OSS 構成パターン

### 3.1 全体構成図（本番想定、Option B 完成形）

```mermaid
flowchart TB
    Internet["👥 エンドユーザー"]

    subgraph CDN["コンテンツ配信 + 防御層"]
        CF_K["☁️ CloudFront + WAF<br/>+ ACM 証明書"]
    end

    subgraph AuthAccount["共通認証基盤 AWS アカウント"]
        direction TB
        subgraph KCVPC["カスタム VPC (10.0.0.0/16)、2 AZ"]
            subgraph PublicSubnet["Public Subnets (2 AZ)"]
                PALB["🌐 Public ALB<br/>HTTPS:443<br/>(L7 IP 制限)"]
                AALB["🔒 Admin ALB<br/>(管理者 IP 限定)"]
            end
            subgraph PrivateSubnet["Private Subnets (2 AZ)"]
                IALB["🔒 Internal ALB<br/>(VPC 内 JWKS)"]
                subgraph ECSCluster["ECS Fargate (Auto Scaling)"]
                    ECS1["🐳 Keycloak Task A"]
                    ECS2["🐳 Keycloak Task B"]
                end
                subgraph AuroraDB["Aurora PostgreSQL Multi-AZ"]
                    AuroraW["Writer"]
                    AuroraR["Reader"]
                    AuroraW --- AuroraR
                end
            end
            VPCe["📦 VPC Endpoints<br/>(ECR / S3 / Logs / Cognito-idp)"]
        end
        Secrets_K["🔐 Secrets Manager<br/>(DB password / Admin)"]
        KMS_K["🔑 KMS"]
        CW_K["📊 CloudWatch<br/>(メトリクス + ログ)"]
    end

    subgraph DRAccount["DR リージョン (大阪)"]
        direction TB
        DRVPC["カスタム VPC<br/>(同一構成)"]
        DRAurora["Aurora Global DB<br/>Secondary"]
    end

    subgraph AppAccount["アプリ AWS アカウント (×N)"]
        SPA_K["⚛️ SPA / SSR / Mobile / BFF"]
        APIGW_K["🟣 API Gateway"]
        Authλ_K["⚡ Lambda Authorizer<br/>(VPC 配置可)"]
    end

    R53_K["🌐 Route 53<br/>+ Health Check"]

    Internet --> CDN --> PALB
    SPA_K <-->|"OIDC"| PALB
    PALB --> ECS1
    PALB --> ECS2
    AALB --> ECS1
    AALB --> ECS2
    IALB --> ECS1
    IALB --> ECS2
    ECS1 --> AuroraW
    ECS2 --> AuroraW
    ECS1 --> VPCe
    ECS2 --> VPCe
    ECS1 -.- Secrets_K
    AuroraW <-..->|"Global Replication<br/>RPO ~1秒"| DRAurora
    R53_K -.通常.-> PALB
    R53_K -.障害時.-> DRVPC
    APIGW_K --> Authλ_K
    Authλ_K -.JWKS.-> IALB
    AuroraW --> KMS_K
    ECS1 --> CW_K

    style ECSCluster fill:#f5f0ff,stroke:#6600cc
    style AuroraDB fill:#f5f0ff,stroke:#6600cc
    style AuthAccount fill:#faf5ff,stroke:#6600cc
    style DRAccount fill:#fce4ec,stroke:#c2185b
    style AppAccount fill:#e8f5e9,stroke:#2e7d32
```

### 3.2 主要構成要素

| レイヤー | 構成要素 | 役割 |
|---|---|---|
| **コンテンツ配信** | CloudFront + WAF + ACM | HTTPS / IP 制限 / レート制限 |
| **3 系統 ALB** | Public / Admin / Internal | OIDC / 管理者 / VPC 内 JWKS（[ADR-012](../adr/012-vpc-lambda-authorizer-internal-jwks.md)）|
| **認可サーバー** | ECS Fargate（Keycloak 26.x、Auto Scaling 2-N）| OIDC OP、トークン発行 |
| **データベース** | Aurora PostgreSQL Multi-AZ | Realm 設定 / ユーザー / セッション保持 |
| **VPC Endpoints** | ECR / S3 / CloudWatch Logs / Cognito-idp | NAT Gateway 不要、Private Subnet 完結 |
| **シークレット管理** | Secrets Manager | DB password / Admin password |
| **暗号化** | KMS | Aurora encryption / Secrets 暗号化 |
| **DR** | Aurora Global DB（大阪 Secondary）+ Standby ECS + Route 53 | RPO ~1 秒 |

### 3.3 マルチ AZ / Auto Scaling

| 項目 | 構成 |
|---|---|
| ECS Fargate | Min 2 タスク（Multi-AZ）、CPU/Mem 閾値で自動スケール（〜 8 タスク程度）|
| Aurora | Multi-AZ（writer 1 + reader 1〜）、自動フェイルオーバー |
| ALB | Multi-AZ 自動（AWS 仕様）|
| Single Point of Failure | ✅ すべて冗長化済 |

### 3.4 DR 構成（Multi-Region）

```mermaid
flowchart LR
    DNS_K["Route 53"]
    HC_K["Health Check<br/>(Internal JWKS)"]
    TokyoVPC["🟪 東京 VPC<br/>(Primary)<br/>ECS + Aurora"]
    OsakaVPC["🟣 大阪 VPC<br/>(Standby)<br/>ECS + Aurora Global DB Reader"]

    DNS_K --> HC_K
    HC_K --> TokyoVPC
    HC_K -.障害時.-> OsakaVPC
    TokyoVPC <-.->|"Aurora Global DB<br/>RPO ~1 秒"| OsakaVPC

    style TokyoVPC fill:#faf5ff,stroke:#6600cc
    style OsakaVPC fill:#fce4ec,stroke:#c2185b
```

- **Aurora Global DB**: 東京 ↔ 大阪、RPO ~1 秒
- **Standby ECS**: 平常時は最小タスク（or オンデマンド起動）
- **追加月額コスト**: ~$890/月（大阪側 ECS + Aurora 常時稼働）+ Route 53
- **フェイルバック**: Aurora Global DB の writer 切替 + ECS 自動復旧

### 3.5 月額コスト試算（10K MAU 想定、本番 HA 構成）

| コンポーネント | 月額 |
|---|---|
| ECS Fargate（2 vCPU × 4GB × 2 タスク Multi-AZ）| ~$200 |
| Aurora PostgreSQL Multi-AZ（db.r6g.large × 2）| ~$300 |
| 3 系統 ALB（Public / Admin / Internal）| ~$80 |
| VPC Endpoints（ECR / S3 / Logs / Cognito-idp）| ~$30 |
| その他（CloudWatch / Secrets Manager / KMS）| ~$30 |
| **インフラ小計** | **~$640/月** |
| 運用人件費（月 21h × $80）| ~$1,680 |
| **合計（運用込）** | **~$2,320/月** |

→ **MAU に依存しない固定費**。MAU 増えてもコスト変動なし → 損益分岐 175,000 MAU（[ADR-006](../adr/006-cognito-vs-keycloak-cost-breakeven.md)）。

---

## 4. Keycloak RHBK 構成パターン

### 4.1 OSS との差分（基本構成は同じ）

RHBK は OSS と**同じインフラ構成**で動作するが、以下が追加される：

```mermaid
flowchart LR
    subgraph RH["Red Hat 側"]
        Reg["registry.redhat.io"]
        Support["Red Hat<br/>24/7 サポート"]
    end

    subgraph AWS_K["AWS 側 (OSS 構成と同じ)"]
        ECR["ECR<br/>(RHBK ミラーリング推奨)"]
        ECS_R["ECS Fargate<br/>(RHBK イメージ)"]
        FIPS["FIPS 140-2<br/>暗号モジュール<br/>(オプション)"]
    end

    Reg -->|"pull secret"| ECR
    ECR --> ECS_R
    ECS_R -.- FIPS
    ECS_R -.チケット.- Support

    style RH fill:#ffe4b5,stroke:#e65100
    style AWS_K fill:#faf5ff,stroke:#6600cc
```

### 4.2 デプロイメント選択肢（[ADR-015](../adr/015-rhbk-validation-deferred.md)）

| 構成 | Red Hat サポート対象 | 月額（OSS との差分）|
|---|:---:|---|
| **ECS Fargate + RHBK** | ⚠ **要確認**（[rhbk-vendor-inquiry.md Q1](../requirements/rhbk-vendor-inquiry.md)）| サブスクリプション $1,250〜2,500 |
| EKS Fargate + RHBK | ⚠ KB 7072950 要確認 | 同上 |
| **ROSA + RHBK** | ✅ 一級サポート | ROSA $400/月 + RHBK |
| EC2 RHEL 9 + RHBK | ✅ 一級サポート | EC2 + RHEL ライセンス |

### 4.3 月額コスト試算（10K MAU、ECS Fargate 想定）

| コンポーネント | 月額 |
|---|---|
| OSS インフラ（§3.5 参照）| ~$640 |
| RHBK サブスクリプション（2-core × 2 ノード、Standard）| ~$1,250 |
| RHBK サブスクリプション（Premium、24/7）| +$1,250（合計 ~$2,500）|
| 運用人件費（Red Hat サポート活用で半減想定）| ~$840 |
| **合計（Standard + 運用込）** | **~$2,730/月** |
| **合計（Premium + 運用込）** | **~$3,980/月** |

→ FIPS 140-2 必須 / 24/7 商用サポート必須なら有力候補。損益分岐は ~600K MAU（コスト的に大規模向け）。

---

## 5. 3 プラットフォーム比較表

[ADR-006](../adr/006-cognito-vs-keycloak-cost-breakeven.md) と [proposal §C-2](../requirements/proposal/common/02-platform.md) との整合表。

| 観点 | Cognito | Keycloak OSS | Keycloak RHBK |
|---|---|---|---|
| **タイプ** | フルマネージド SaaS | OSS 自己ホスト | OSS 商用版 + サポート |
| **インフラ月額（10K MAU）**| ~$150〜350（ティア）| ~$640 | ~$640 + RHBK |
| **運用人件費** | ~$0 | ~$1,680/月 | ~$840/月（半減想定）|
| **合計月額（10K MAU）**| ~$150〜350 | ~$2,320 | ~$2,730〜3,980 |
| **損益分岐 MAU**（vs Keycloak OSS）| 175K（連携）/ 75K（Plus）| — | ~600K |
| **マルチ AZ** | ✅ AWS 透過 | ⚠ 設計要 | ⚠ 同左 |
| **DR**（追加コスト）| $0.50/月 + 障害月 MAU | $890/月（常時）| $890 + RHBK |
| **FIPS 140-2** | ❌ | ❌ | ✅ |
| **24/7 商用サポート** | ✅ AWS Support | ❌ コミュニティ | ✅ Red Hat |
| **機能柔軟性** | 中（ティア依存）| 高 | 高 |
| **Token Exchange / SAML IdP 発行 / LDAP 直結 / DPoP / RFC 9470 step-up** | ❌ | ✅ | ✅ |
| **WebAuthn / Passkeys** | ✅（Essentials+）| ✅ | ✅ |
| **Identity Brokering**（外部 IdP）| ✅ | ✅ | ✅ |
| **IaC（Terraform）**| ✅ 完全管理可 | ⚠ Realm 部分は別管理 | 同左 |

---

## 5.A クォータ・スケール上限詳細

> 調査日: 2026-05-18 / 顧客向けサマリ: [§NFR-3.1.A クォータ・スケール上限の実数](../requirements/proposal/nfr/03-scalability.md#nfr-31a-クォータスケール上限の実数顧客向けサマリ)

「Broker パターン採用（[§C-1.1](../requirements/proposal/common/01-architecture.md#c-11-broker-パターン採用根拠)）」「物理分離レベル（[§C-1.4](../requirements/proposal/common/01-architecture.md#c-14-物理分離レベルと-broker-パターンの関係)）」を実装する際、**何が物理的に詰まるか**の一次資料。NFR 章への根拠データとしても流用。

### 5.A.1 Cognito User Pools クォータ

公式: [Quotas in Amazon Cognito](https://docs.aws.amazon.com/cognito/latest/developerguide/limits.html)（2026-05 時点）

#### リソース上限

| 項目 | 既定 | 緩和後最大 | Soft/Hard | Lite/Essentials/Plus 差 |
|---|---:|---:|:---:|:---:|
| **Users per user pool**（ローカル + フェデ JIT 含む） | **40,000,000** | "Contact your account team"（個別交渉） | Soft | 差なし |
| **User pools per Region** | **1,000** | **10,000** | Soft | 差なし |
| **Identity providers per user pool**（SAML + OIDC + Social 合算）| **300** | **1,000** | Soft | 差なし |
| **App clients per user pool** | **1,000** | **10,000** | Soft | 差なし |
| **Groups per user pool** | **10,000** | — | **Hard** | 差なし |
| Groups per user | 100 | — | Hard | 差なし |
| **Custom attributes per user pool** | **50** | — | **Hard** | 差なし |
| Characters per attribute | 2,048 bytes | — | Hard | — |
| Lambda triggers per user pool | 13 種別 × 各 1 個 | — | Hard | Pre Token Gen v2/v3 は Essentials+ 限定 |
| Identities linked to a user（外部 ID 連結数）| 5 | — | Hard | 差なし |
| Resource servers per user pool | 25 | 300 | Soft | 差なし |
| Callback / Logout URLs per app client | 100 / 100 | — | Hard | 差なし |
| Scopes per app client / resource server | 50 / 100 | — | Hard | 差なし |
| Passkey/WebAuthn authenticators per user | 20 | — | Hard | Essentials+ で利用可 |
| Managed Login branding styles per pool | 20 | — | Hard | Essentials+ 限定 |

#### API レート上限（カテゴリ別、リージョン × AWS アカウント単位）

| カテゴリ | 既定 RPS | Adjustable | 主な API |
|---|---:|:---:|---|
| **UserAuthentication** | **120** | **Yes** | `InitiateAuth`, `RespondToAuthChallenge`（`Admin*` 系は 3× 別枠 = 360）|
| UserCreation | 50 | Yes | `SignUp`, `AdminCreateUser` |
| **UserFederation** | **25** | Yes | OIDC/SAML IdP コールバック |
| **UserAccountRecovery** | **30** | **No (Hard)** | `ForgotPassword` 系 |
| UserRead | 120 | Yes | `GetUser` 等 |
| UserToken | 120 | Yes | トークン管理 |
| **UserUpdate** | **25** | **No (Hard)** | 属性・グループ変更 |
| **UserList** | **30** | **No (Hard)** | `ListUsers` 等 |
| UserResourceRead | 50 | Yes | デバイス・グループメンバー参照 |
| UserResourceUpdate | 25 | **No (Hard)** | デバイス・グループ更新 |
| UserPoolRead/Update | 15/15 | **No (Hard)** | プール設定（プール単位 5 RPS）|
| UserPoolResourceRead/Update | 20/15 | **No (Hard)** | グループ・リソースサーバ（プール単位 5 RPS）|
| UserPoolClientRead/Update | 15/15 | **No (Hard)** | App Client（プール単位 5 RPS）|
| **ClientAuthentication** | **150** | **No (Hard)** | M2M（`client_credentials` grant）|
| Read/Write user profile（per user）| **10 RPS / user** | Hard | `GetUser`, `UpdateUserAttributes` 等 |
| **JWKS（`jwks.json`）** | **50,000** | **No (Hard)** | リージョン × アカウント合算 |
| Managed Login ドメイン全体 | 500 | **No (Hard)** | ドメイン単位 |
| Managed Login per app client | 300 | **No (Hard)** | ドメイン × App Client |
| Managed Login per source IP | 300 | **No (Hard)** | 同一 IP → 同一ドメイン |

#### Cognito 公式の MAU ベース計算例

- **200 万 MAU 未満は既定クォータで運用可能**（公式 "Identify quota requirements" 明記）
- 100 万 MAU = 8 時間稼働で平均 35 RPS、トークン更新込み 70 RPS、ピーク 3× → **UserAuthentication 200 RPS** を購入推奨

#### ティア（Lite / Essentials / Plus）との関係

公式 docs 上、**クォータ値はティア依存しない**。Plus は機能を追加するのみ:

| 領域 | Lite | Essentials | Plus |
|---|:---:|:---:|:---:|
| Managed Login UI（ビジュアルエディタ）| × | ◯ | ◯ |
| Passkey / Email OTP / 選択型認証 | × | ◯ | ◯ |
| Pre Token Gen v2/v3、パスワード履歴 | × | ◯ | ◯ |
| Threat protection / 適応認証 / 漏洩パスワード検出 / 活動ログ | × | × | **◯（Plus 限定）** |

出典:
- https://docs.aws.amazon.com/cognito/latest/developerguide/limits.html
- https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-sign-in-feature-plans.html
- https://docs.aws.amazon.com/cognito/latest/developerguide/feature-plans-features-essentials.html
- https://docs.aws.amazon.com/cognito/latest/developerguide/feature-plans-features-plus.html

### 5.A.2 Keycloak 26.x スケール特性

公式数値が明示されない項目が多く、**ベンチマーク + GitHub Discussion / Issue + コミュニティ実証**を一次根拠とする。

#### リソース上限（公式 + コミュニティ実証）

| 項目 | 公式記述 | 実用上の知見 | 出典 |
|---|---|---|---|
| **Realm 数 / クラスタ** | ハード制限なし | **26.4 で 1,000+ 運用可能**（`realmCache` 50 entries/realm 推奨）／ 最適化適用時は **3,000 Realm でも線形挙動**（Admin Console 50 秒）／ 17.x 等の旧版は 100-200 で破綻 | [Discussion #11074](https://github.com/keycloak/keycloak/discussions/11074), [Benchmark 26.4](https://www.keycloak.org/2025/10/keycloak-benchmark) |
| **Users / Realm** | ハード制限なし | **数百万ユーザー実例あり**。ストレージ + DB スペックで決まる | [Discussion #15181](https://github.com/keycloak/keycloak/discussions/15181) |
| Clients / Realm | ハード制限なし | 動的クライアント登録も同じ | Discussion #15181 |
| Groups / Roles / IdPs / Realm | ハード制限なし | DB スケール依存 | — |
| Realm cache 推奨サイズ | — | **Realm あたり 50 entries** を目安（1 Realm の標準消費 ~20 entries） | Benchmark 26.4 |
| 26.x の Organization 機能 | — | 単一 Realm 内マルチテナント方式。Realm を増やさずに済む | Keycloak 26 リリースノート |

#### CPU / メモリ サイジング計算式（Keycloak 26.6 公式）

| 操作 | CPU 計算式 | 検証上限（単一ノード）|
|---|---|---:|
| パスワード ログイン | **1 vCPU で 15 logins/sec** | 300/sec |
| クライアント認証情報 | **1 vCPU で 120 grants/sec** | 2,000/sec |
| Refresh Token | **1 vCPU で 120 refresh/sec** | 435/sec |

メモリ:
- ベース 1,250 MB（10,000 キャッシュセッション含）
- ヒープ比率 70% / 非ヒープ 300 MB
- 計算式: `(必要メモリ - 300) ÷ 0.7`

#### 計算例（公式・単一クラスタ）

要件: ログイン 45/sec + Refresh 360/sec + Client Credentials 360/sec → **3 ポッド構成**

| 項目 | 値 |
|---|---|
| Pod あたり CPU request | 3 vCPU |
| Pod あたり CPU limit | 7.5 vCPU（150% スピーク余裕）|
| Pod あたり Memory | 1,250 MB（request） / 1,360 MB（limit）|
| DB | Aurora PostgreSQL `db.t4g.large` または `xlarge` |

#### スケーリングベンチマーク（公式 26.4, 2025-10）

- 最大検証: **2,000 logins/sec + 10,000 refresh/sec**
- 必要 CPU: 74 vCPU（3 ポッド構成）
- メモリ: 8 GB / ポッド
- ユーザー数: 100,000（テスト時）

#### 既知の劣化事例 / リグレッション

| Issue / Discussion | 内容 |
|---|---|
| [#46605](https://github.com/keycloak/keycloak/issues/46605) | **26.5.4 startup regression**: 多 Realm 環境でマスター Realm 管理ロール合成が O(N²) に劣化 |
| [#29978](https://github.com/keycloak/keycloak/issues/29978) | 600+ Realm で Admin UI ドロップダウンが約 6 分 |
| [#18328](https://github.com/keycloak/keycloak/issues/18328) | 300+ Realm で Admin Console ロード 20+ 秒 |
| [#20453](https://github.com/keycloak/keycloak/issues/20453) | 20.0.5 で Admin UI のテナント一覧が 1:47 かかる |
| [#19793](https://github.com/keycloak/keycloak/issues/19793) | 400 Realm 作成後、Admin Console でデータロード不能 |
| [Discussion #12332](https://github.com/keycloak/keycloak/discussions/12332) | 多 Realm 時の master Realm 上 client 評価コスト（root cause 議論）|

出典:
- https://www.keycloak.org/2025/10/keycloak-benchmark
- https://www.keycloak.org/high-availability/multi-cluster/concepts-memory-and-cpu-sizing
- https://github.com/keycloak/keycloak/discussions/11074
- https://github.com/keycloak/keycloak/discussions/15181

### 5.A.3 両者の「天井」対応関係

| 軸 | Cognito | Keycloak 26.x |
|---|---|---|
| **顧客 IdP 接続数の天井** | 300（既定）/ 1,000（最大）/ Pool 単位 — Soft | ハード制限なし。実例ベースで 10K IdPs 報告（[Issue #30084](https://github.com/keycloak/keycloak/issues/30084)）|
| **テナント分離パターン**：Pool/Realm 分離 | 1,000 Pool（既定）/ 10,000（最大）/ Region | 1,000-3,000 Realm（cache チューニング必須）|
| **テナント分離パターン**：単一 Pool/Realm + tenant_id | 4,000 万 user / Pool まで吸収可 | 数百万 user / Realm、DB 限界まで |
| **ユーザー総数の天井** | 4,000 万 / Pool（Soft, 個別緩和）| ハード制限なし。DB 性能次第 |
| **認証 TPS の上限** | 120 RPS（Soft, 増額可。Admin 系 3× = 360）| 単一ノード 300/sec、3 ポッドで 2,000/sec、リソース追加で線形 |
| **Refresh TPS の上限** | 120 RPS（Soft）| 単一ノード 435/sec、3 ポッドで 10,000/sec |
| **M2M（Client Credentials）TPS** | **150 RPS（Hard、緩和不可）** | 単一ノード 2,000/sec、リソース追加で拡張可 |
| **JWKS TPS** | 50,000 RPS（Hard、極めて高）| DB 非依存、ノードスケールで対応 |
| **緩和不可な Hard リミット** | UserAccountRecovery 30 / UserList 30 / UserUpdate 25 / ClientAuthentication 150 RPS など多数 | なし（リソース追加で線形拡張）|
| **DB / 永続化 SPOF** | なし（AWS 透過）| Aurora PostgreSQL がボトルネック |
| **管理 UI スケール** | AWS Console（影響なし）| Realm 数増で **劣化リスク**、26.x 系でも cache チューニング必須 |

### 5.A.4 NFR への示唆（要件定義に直結する 5 ポイント）

1. **「顧客数で天井に当たる項目」が両者で異なる**
   - **Cognito**: IdP 300（最大 1,000）が単一 Pool の "顧客 IdP 数" 天井 → **1,000 社級なら 1 Pool 設計は破綻**、Pool 分割（最大 10,000 / Region）に切り替え
   - **Keycloak**: Realm 分離方式で **1,000-3,000 顧客**まで単一クラスタ（cache 必須）。Organization 機能の単一 Realm 多テナントなら制限なし
   - **設計分岐点**: 100-300 顧客で Pool / Realm 分割を再検討すべき

2. **「ユーザー総数で天井に当たる項目」**
   - **Cognito**: 4,000 万 / Pool（Soft, 個別緩和）。**3,000 万を超えるなら Pool 分割設計を NFR に明記推奨**
   - **Keycloak**: 数百万事例あり、DB スペック次第

3. **Cognito の Hard リミットがボトルネック化**
   - **M2M 150 RPS（緩和不可）**: マイクロサービス間呼出が高頻度なら破綻 → **JWT キャッシュ前提**で設計
   - **UserList 30 RPS（緩和不可）**: 顧客一覧操作・バッチ運用に致命的 → **外部 DB / S3 エクスポート**前提
   - **UserUpdate 25 RPS（緩和不可）**: ユーザー属性更新の頻度上限

4. **Keycloak の "実用上の地雷"**
   - **多 Realm 時のキャッシュチューニング必須**（デフォルトでは劣化）
   - **Admin Console UI 性能は Realm 数の関数**で劣化（300 Realm で 20+ 秒事例）
   - **26.5.4 にリグレッションあり**（Issue #46605）→ **バージョン固定戦略**が必要
   - **DB（PostgreSQL）が SPOF**。Aurora 推奨

5. **§C-1.4 の物理分離レベルとの対応**
   - **L2（単一 Pool/Realm + tenant_id）**: Cognito 4,000 万 user / Keycloak 数百万 user → 圧倒的に余裕
   - **L3（規制顧客のみ別 Pool/Realm）**: Cognito 10,000 Pool / Keycloak 1,000-3,000 Realm → 十分
   - **L6（顧客ごと完全別基盤）**: 両者ともクォータ管理ではなく **AWS アカウント分離 / 別クラスタ**になり、本基盤の対象外（[§C-1.4](../requirements/proposal/common/01-architecture.md#c-14-物理分離レベルと-broker-パターンの関係)）

### 5.A.5 出典 URL（一次資料）

**Cognito**:
- [Quotas in Amazon Cognito](https://docs.aws.amazon.com/cognito/latest/developerguide/limits.html)
- [User pool feature plans](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-sign-in-feature-plans.html)
- [Essentials plan features](https://docs.aws.amazon.com/cognito/latest/developerguide/feature-plans-features-essentials.html)
- [Plus plan features](https://docs.aws.amazon.com/cognito/latest/developerguide/feature-plans-features-plus.html)
- [User pool Lambda triggers](https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-lambda-triggers.html)

**Keycloak**:
- [Keycloak Performance Benchmarks (26.4, 2025-10)](https://www.keycloak.org/2025/10/keycloak-benchmark)
- [Concepts for sizing CPU and memory resources (26.6)](https://www.keycloak.org/high-availability/multi-cluster/concepts-memory-and-cpu-sizing)
- [Improved scalability over number of realms (Discussion #11074)](https://github.com/keycloak/keycloak/discussions/11074)
- [Maximum user per realm? (Discussion #15181)](https://github.com/keycloak/keycloak/discussions/15181)
- [26.5.4 startup regression with many realms (Issue #46605)](https://github.com/keycloak/keycloak/issues/46605)
- [Admin UI slow performance loading 600+ realms (Issue #29978)](https://github.com/keycloak/keycloak/issues/29978)

---

## 6. プラットフォーム選定との対応

### 6.1 選定判定フロー（[proposal §C-2.4](../requirements/proposal/common/02-platform.md) と整合）

```mermaid
flowchart TB
    Start["要件確定"]
    Q1{"Token Exchange / SAML IdP 発行 /<br/>LDAP 直結 / DPoP /<br/>RFC 9470 step-up の<br/>いずれか Must?"}
    Q2{"FIPS 140-2 認定 必須?"}
    Q3{"24/7 商用サポート 必須?"}
    Q4{"MAU > 175,000<br/>(または Plus 要件あり<br/>+ MAU > 75,000)?"}
    Cog["**Cognito**<br/>(Lite/Essentials/Plus)"]
    OSS["**Keycloak OSS**<br/>(本書 §3)"]
    RHBK["**Keycloak RHBK**<br/>(本書 §4)"]

    Start --> Q1
    Q1 -->|Yes| Q2
    Q1 -->|No| Q4
    Q4 -->|Yes| Q2
    Q4 -->|No| Cog
    Q2 -->|Yes| RHBK
    Q2 -->|No| Q3
    Q3 -->|Yes| RHBK
    Q3 -->|No| OSS

    style Cog fill:#fff0f0,stroke:#cc0000
    style OSS fill:#faf5ff,stroke:#6600cc
    style RHBK fill:#ffe4b5,stroke:#e65100
```

### 6.2 典型シナリオごとの推奨構成

| シナリオ | 想定 | 推奨 |
|---|---|---|
| 国内 B2B SaaS、~50K MAU、特殊要件なし | 一般的なエンプラ SaaS | **Cognito Lite/Essentials**（§2）|
| 国内 B2B SaaS、~100K MAU、リスクベース MFA Must | 金融周辺 SaaS | **Cognito Plus**（§2、~$350）|
| 大規模 B2B、~500K MAU、フェデのみ | グローバル SaaS | **Keycloak OSS**（§3）|
| 金融 / FAPI / Token Exchange / SAML IdP 発行 | 金融 API | **Keycloak OSS or RHBK**（§3/§4）|
| FIPS 140-2 必須 / 政府系 | 政府・防衛・医療 | **Keycloak RHBK**（§4）|
| AI Agent 認証 / Device Code 必須 | CLI・IoT・AI Agent | **Keycloak OSS or RHBK**（§3/§4）|

---

## 7. 共通: マルチアカウント連携設計

### 7.1 共通基盤 ↔ アプリアカウントの接続

```mermaid
flowchart LR
    subgraph A["共通認証基盤アカウント"]
        Auth["認可サーバー<br/>(Cognito or Keycloak)"]
        JWKS["JWKS Endpoint<br/>(公開 or VPC 内)"]
    end

    subgraph B1["アプリ A アカウント"]
        SPA_A["SPA"]
        API_A["API + Authorizer"]
    end

    subgraph B2["アプリ B アカウント"]
        SPA_B["SPA"]
        API_B["API + Authorizer"]
    end

    subgraph C["管理アカウント"]
        CT["CloudTrail / Audit"]
        IAM["IAM Identity Center"]
    end

    SPA_A -.OIDC.-> Auth
    SPA_B -.OIDC.-> Auth
    API_A -.JWKS 取得.-> JWKS
    API_B -.JWKS 取得.-> JWKS
    Auth --> CT
    IAM --> A
    IAM --> B1
    IAM --> B2

    style A fill:#fff0f0
    style B1 fill:#e8f5e9
    style B2 fill:#e8f5e9
    style C fill:#f5f5f5
```

### 7.2 信頼境界

- **共通基盤 → アプリ**: JWT 発行（基盤の私有鍵で署名）
- **アプリ → 共通基盤**: JWKS 取得（公開鍵）+ Bearer JWT 添付
- **管理者 → 共通基盤**: IAM Identity Center 経由 / Realm Admin
- **テナント境界**: JWT の `tenant_id` クレームで分離（[§FR-2.3.C](../requirements/proposal/fr/02-federation.md)）

---

## 8. 最新化方針

本ドキュメントは以下のタイミングで更新する：

| トリガー | 反映先 |
|---|---|
| プラットフォーム選定（[ADR-017 / 018](../adr/) 確定）| §6 選定フローを最終化、§2/§3/§4 のうち選定外を簡略化 |
| Cognito 料金変更 / 機能追加 | §2.3 ティア表、§2.6 コスト試算 |
| Keycloak 新バージョンリリース | §3.1〜§3.5 |
| RHBK サポート条件確定（[rhbk-vendor-inquiry.md](../requirements/rhbk-vendor-inquiry.md)）| §4 |
| マルチアカウント戦略確定（ADR-018）| §7 |
| DR 自動フェイルオーバー方式確定（ADR-019）| §2.5 / §3.4 |

→ **本書を最新化のハブ**として、他の関連ドキュメント（PoC 構成 / Broker パターン / ネットワーク詳細）への参照を維持する。

---

## 9. 参考資料

### ADR（プラットフォーム関連）
- [ADR-006 Cognito vs Keycloak コスト損益分岐](../adr/006-cognito-vs-keycloak-cost-breakeven.md)
- [ADR-010 Keycloak Private Subnet + VPC Endpoints](../adr/010-keycloak-private-subnet-vpc-endpoints.md)
- [ADR-011 認証基盤前段ネットワーク設計](../adr/011-auth-frontend-network-design.md)
- [ADR-012 VPC Lambda Authorizer + Internal ALB JWKS](../adr/012-vpc-lambda-authorizer-internal-jwks.md)
- [ADR-013 CloudFront + WAF による IP 制限](../adr/013-cloudfront-waf-ip-restriction.md)
- [ADR-014 認証パターン対応範囲](../adr/014-auth-patterns-scope.md)
- [ADR-015 RHBK 検証先送り](../adr/015-rhbk-validation-deferred.md)
- [ADR-016 Cognito 機能ティア選定基準](../adr/016-cognito-feature-tier-selection.md)

### 関連内部ドキュメント
- [bff-implementation-notes.md](bff-implementation-notes.md) — BFF パターン実装
- [architecture.md](architecture.md) — PoC 実装構成
- [identity-broker-multi-idp.md](identity-broker-multi-idp.md) — Broker パターン抽象設計
- [keycloak-network-architecture.md](keycloak-network-architecture.md) — Keycloak ネットワーク詳細
- [system-design-patterns.md](system-design-patterns.md) — 8 つのシステム設計パターン
- [proposal/common/02-platform.md](../requirements/proposal/common/02-platform.md) — 顧客提示版プラットフォーム選定
- [rhbk-vendor-inquiry.md](../requirements/rhbk-vendor-inquiry.md) — Red Hat 問い合わせ
