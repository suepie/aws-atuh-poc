# §C-API-6 外部 API 認証アーキテクチャ — Engine / Relationship モデルと技術的担保

> 親 SSOT: [../00-index.md](../00-index.md) §C-API-6
> 位置付け: 「**認証基盤 vs アプリ**」「**中央集約 vs アプリ自律**」「**Inbound vs Outbound**」の責務分担を統合的に整理する横断ドキュメント。顧客説明・調達 DDQ 対応・社内合意形成に共用。
> 関連: [§FR-API-0 (Inbound 6 タイプ)](../fr/00-external-api-consumption-overview.md) / [§FR-API-2 (認証認可詳細)](../fr/02-authn-authz.md) / [§FR-API-7 (ガードレール)](../fr/07-guardrails.md) / [§C-API-3 (共有認証境界)](03-shared-auth-boundary.md) / [§C-API-5 (Service Catalog)](05-self-service-catalog.md)
> 改訂: 2026-06-19 初版

---

## §C-6.0 前提と背景

### §C-6.0.1 エグゼクティブサマリ（顧客説明用 60 秒）

**本標準の認証アーキテクチャは「Engine 中央 + Relationship 分散」モデルを採用する**：

1. **End-User 認証**（B2C / B2B 顧客のエンドユーザー）は **共有認証基盤（Keycloak / Cognito）が中央で実施**。CIAM 専門組織が運用し、全アプリで JWT 検証として利用。
2. **Partner B2B 認証**（外部企業 Backend からの M2M 呼出）は **認証基盤の Engine 機能（Token 発行・検証）を利用しつつ、Partner との Relationship 運用（契約・credential 配布・ローテ調整）は各アプリチームが Self-Service で実施**。
3. **Outbound SaaS 連携**（自アプリが Stripe / SendGrid 等の外部 SaaS を呼ぶ）は **各アプリチームが完全自律**。中央は Approved SaaS Allowlist と Service Catalog テンプレでガバナンスを担保。
4. **Private（社内 / AWS native）認証**は AWS IAM SigV4 / VPC Lattice Auth Policy で各アプリが自律。
5. **「アプリに寄せる」決定の技術的前提**として、5 検知レイヤー（IaC / Config / Static Code / Runtime Log / Behavioral）の組合せで **認証実装漏れを 95-99% 担保**する仕組みを Service Catalog / Config Rules / Semgrep / CloudWatch Synthetics で構築する。

→ **End-User の CIAM 価値（規模・専門性）を中央で享受**しつつ、**Partner / Outbound では各アプリチームのリリース自律性**を確保し、**技術的なガバナンス担保で安全性を担保**する 3 立てモデル。

### §C-6.0.2 用語整理

| 用語 | 定義 |
|---|---|
| **Engine（認証エンジン）** | OAuth 2.0 / OIDC / JWT の技術機能群。Token 発行 / 署名 / 検証 / 鍵ローテ / JWKS 公開 / Token Exchange / 信頼台帳 |
| **Relationship（対抗先運用）** | 外部主体（Partner / SaaS）との契約・scope 設計・credential 配布・ローテ調整・トラブル対応・廃止処理 |
| **Inbound API** | 外部 → 自アプリへの呼出（例：Partner Backend が自アプリ API を叩く）|
| **Outbound API** | 自アプリ → 外部 SaaS への呼出（例：自アプリが Stripe API を叩く）|
| **Self-Service Developer Portal** | アプリチームが認証基盤の Engine 機能を呼び出して Partner Client を作成・管理する UI / ワークフロー |
| **共有認証基盤** | Keycloak / Cognito 等の OIDC IdP。End-User CIAM の中央コンポーネント |
| **Approved SaaS Allowlist** | アプリが Outbound で接続して良い外部 SaaS のリスト（DPA / 法務確認済）|
| **Two-Track 承認** | 日常運用は自律、増分リスクのある操作（新規 scope / PII 関連 / 新規 IdP 登録等）は中央承認 |
| **検知 5 Layer** | IaC pre-deploy / Config post-deploy / Static Code / Runtime Log / Behavioral probe の 5 段の認証実装漏れ検知 |

### §C-6.0.3 なぜここ（§C-6）で決めるか

「外部 API 認証」を取り巻く 3 つの議論が、これまで各章に分散していた：

1. **§FR-API-0**：Inbound 6 タイプの分類
2. **§FR-API-2**：認証認可の技術選択肢（共有認証基盤 / IAM / mTLS / API Key）
3. **§C-API-3**：共有認証基盤との接続点

しかし、以下の 4 つの横断的論点は **どの章でも単独では決められない**：

- 「**認証基盤チームとアプリチームの責任分担**」（組織論）
- 「**Inbound と Outbound の対応関係**」（業務領域論）
- 「**中央集約 vs アプリ自律**の判断軸」（アーキ論）
- 「**技術的にガバナンスを担保できるか**」（実装論）

本章はこの 4 つを統合的に提示し、各章（§FR-API-0/2/7、§C-API-3/5）の **設計判断の根拠を一元的に説明可能にする**横断章として位置付ける。

```mermaid
flowchart LR
    C6["§C-API-6<br/>外部 API 認証<br/>アーキテクチャ<br/>(本章)"]
    FR0["§FR-API-0<br/>Inbound 6 タイプ"]
    FR2["§FR-API-2<br/>認証認可詳細"]
    FR7["§FR-API-7<br/>ガードレール"]
    C3["§C-API-3<br/>共有認証境界"]
    C5["§C-API-5<br/>Service Catalog"]

    C6 -.根拠を提供.-> FR0
    C6 -.根拠を提供.-> FR2
    C6 -.根拠を提供.-> FR7
    C6 -.根拠を提供.-> C3
    C6 -.根拠を提供.-> C5

    style C6 fill:#fff9c4,stroke:#f57f17
```

### §C-6.0.4 §C-6.0.A 本標準のスタンス

| 基本方針 | 本章での具体化 |
|---|---|
| **絶対安全** | 検知 5 Layer による認証実装漏れ防止（95-99% 担保）、Fail-closed Authorizer 必須、Service Catalog による「認証なし API」deploy 不可化 |
| **どんなアプリでも** | Self-Service Developer Portal でアプリチームが認証基盤 Engine を呼び出し可能、IaC / Config / Static Code / Runtime / Behavioral の 5 層検知でどんな実装でも担保 |
| **効率よく** | Engine（OAuth 機能群）は中央 1 箇所、Relationship 運用は Self-Service、開発者は Service Catalog から数クリックで標準準拠 |
| **運用負荷・コスト最小** | 認証基盤チーム = CIAM コア + Engine 運用のみ、各アプリチーム = Partner / SaaS Relationship 運用のみ、責任境界が明確で過剰連携不要 |

### §C-6.0.5 本章で扱うサブセクション

| § | サブセクション | 主題 |
|---|---|---|
| §C-6.1 | 認証作業の 2 軸分解（Engine vs Relationship）| 「認証基盤チーム」と「アプリチーム」の責任境界を技術機能と運用関係で再定義 |
| §C-6.2 | Inbound / Outbound 対称性 | Inbound（外部→当社）と Outbound（当社→外部）で同じ責務分担構造が成立 |
| §C-6.2.5 | **Inbound 認証パターン詳細（7 パターン × 5 大分類）** ⭐ | **OAuth/証明書/共有秘密キー/AWS IAM の 5 大分類 + P-1〜P-7 の詳細、Keycloak/Cognito 対応、フロー サマリ、Tier 廃止** |
| §C-6.2.6 | **Outbound 認証パターン詳細（5 大分類）** ⭐ | **SaaS 別 protocol、大分類別フロー サマリ、中央ガバナンス 7 項目** |
| §C-6.3 | 4 領域 × 担当 最終モデル | Public / Inbound Partner / Outbound SaaS / Private の 4 領域別の責務 |
| §C-6.4 | Self-Service Developer Portal | アプリチーム自律と認証基盤 Engine の橋渡し UI |
| §C-6.5 | ガバナンス Two-Track 設計 | 日常自律 + 増分リスク中央承認 のバランス |
| §C-6.6 | 認証実装漏れの 6 パターン × 5 検知レイヤー | 「アプリに寄せる」の技術的前提となる検知の体系 |
| §C-6.6.4〜.9 | **5 検知レイヤー詳細実装サンプル + 統合パイプライン** ⭐ | **cfn-guard / Config Rule / Semgrep / Athena / Synthetics の具体ルール・クエリ・コードサンプル、コスト試算** |
| §C-6.7 | AWS リソース別 検知可能性マトリクス | API GW / Lambda URL / ALB / AppSync / VPC Lattice 等で何が検知できるか |
| §C-6.8 | ALB / app-code 認証のグレーゾーン | アプリ実装認証の特殊事情と対策 |
| §C-6.9 | 推奨検知ツールスタック | cfn-guard / Config Rules / Semgrep / Athena / Synthetics 等の組合せ |
| §C-6.10 | 分散化への OK 条件（C1〜C10）| 「アプリに寄せる」を解禁するためのチェックリスト |
| §C-6.11 | 留保事項とリスク | 5 Layer でも防げないリスクの率直な開示 |
| §C-6.12 | ロードマップと PoC 計画 | 検知機構の段階実装計画（DET-1〜DET-6）|

---

## §C-6.1 認証作業の 2 軸分解（Engine vs Relationship）

**このサブセクションで定めること**：認証作業を「技術機能（Engine）」と「対抗先運用（Relationship）」の 2 軸で再分解し、認証基盤チームとアプリチームの責任境界を明確化する。
**主な判断軸**：「技術機能の中央集約による品質確保」と「運用関係のアプリ自律による効率」の両立。
**§C-6 全体との関係**：以降のすべてのサブセクションが本軸を前提とする。

### §C-6.1.1 ベースライン：2 軸の定義

「認証基盤チームが何をやり、アプリチームが何をやるか」を、技術機能（Engine）と運用関係（Relationship）の 2 軸で分解する：

| 軸 | 内容 | 担当 |
|---|---|---|
| **Engine（技術機能）** | OAuth 2.0 / OIDC / JWT の機能群：Token 発行 / 署名 / 検証 / 鍵ローテ / JWKS 公開 / 信頼台帳 / Token Exchange（RFC 8693）/ DPoP（RFC 9449）等 | **認証基盤チーム**（中央）|
| **Relationship（対抗先運用）** | 外部主体との運用関係：Partner との契約交渉 / scope 設計 / Client 作成 / Secret 配布 / ローテ調整 / トラブル対応 / Partner 固有カスタム / 廃止処理 | **アプリチーム**（分散）|

### §C-6.1.2 なぜこの分解が業界標準か

「認証 = 認証基盤」「アプリ = 認証は使うだけ」と単純化すると、**Partner との運用関係は誰がやるか宙に浮く**。実態は：

- 認証基盤チームは CIAM 専門組織で、業務アプリ固有の Partner 関係には立ち入らない
- アプリチームが Partner 営業 / 契約 / インテグレーション支援を一貫して担当
- 認証基盤チームは **Engine 提供者**として Self-Service Admin API / UI を整備

業界主要 IdP プラットフォームでも同じ構造：

| プラットフォーム | Engine 中央 | Relationship 委譲 |
|---|---|---|
| **Auth0 Organizations** | Auth0 SaaS 全機能 | Organization 内 Application / Connection を Org Admin に委譲 |
| **Okta Customer Identity Cloud** | Okta SaaS | Workforce / Customer Admin 分離 |
| **Keycloak Realm 委譲** | Keycloak Cluster | Realm-level / Client-level Admin を IAM で委譲 |
| **AWS Cognito** | Cognito | App Client 管理を IAM Policy で App Owner に委譲 |
| **AWS IAM Identity Center** | IAM Identity Center | 各 AWS account 管理者が SSO Application 設定 |

→ **Engine 中央 + Admin 委譲** は業界共通パターン。本標準もこれに準拠する。

### §C-6.1.3 8 工程での分担（Partner Client Lifecycle）

Partner Client の Lifecycle を 8 工程に分解し、Engine と Relationship を可視化：

| 工程 | 内容 | Engine 担当 | Relationship 担当 |
|---|---|:---:|:---:|
| ① 契約・交渉 | Partner との SLA / DPA / scope 範囲合意 | – | **アプリチーム** |
| ② scope / 権限決定 | 当該 Partner にどの API を開放するか | – | **アプリチーム** |
| ③ Credential 生成 | client_id / client_secret 生成 | **認証基盤**（Admin API）| – |
| ④ Credential 受領 | アプリチームが Admin API / Portal から受け取る | 提供 | **アプリチーム** |
| ⑤ Credential 配布 / 保管 | Partner へ安全配布（暗号化メール / 1Password / Secrets Manager share）| – | **アプリチーム** |
| ⑥ ローテ運用 | 90 / 180 / 365 日周期で Partner と調整 | Engine 機能提供 | **アプリチーム** |
| ⑦ トラブル対応 | Token failure / scope 不足 / Partner 問い合わせ対応 | – | **アプリチーム** |
| ⑧ 廃止・契約終了 | Client 無効化 / 監査ログ封印 / データ削除 | Engine 機能提供 | **アプリチーム** |

→ **8 工程中 7 工程はアプリチーム責務**。Engine は ③ 生成と ⑥ / ⑧ の機能提供のみ。

### §C-6.1.4 TBD / 要確認

- Q: Keycloak Realm-level Admin / Client-level Admin の **委譲粒度** → `API-B-261`
- Q: Cognito 採用時の **App Client 管理委譲方式**（IAM Policy / Custom Lambda）→ `API-B-262`
- Q: Engine 機能の **SLA 目標**（99.9% / 99.95% / 99.99%）→ `API-B-263`

---

## §C-6.2 Inbound / Outbound 対称性

**このサブセクションで定めること**：Inbound（外部→当社）と Outbound（当社→外部）が同じ「Engine vs Relationship」構造で説明できることを示し、両方向で一貫した責務モデルを定義する。
**主な判断軸**：方向に関わらず、credential のやり取りは対抗先との運用関係であり、アプリチームに集約される。
**§C-6 全体との関係**：§C-6.3 4 領域モデルの基礎。

### §C-6.2.1 ベースライン：対称構造

8 工程を Inbound / Outbound で対比すると、**Engine 提供者が「自社認証基盤」か「外部 SaaS」かが入れ替わるだけで、それ以外は完全に同じ構造**：

| 工程 | Inbound（Partner → 自アプリ）| Outbound（自アプリ → SaaS）|
|---|---|---|
| **① 契約・交渉** | アプリチーム ↔ Partner | アプリチーム ↔ SaaS（営業 / 申込）|
| **② scope / 権限決定** | アプリチームが Partner へ開放範囲決定 | アプリチームが SaaS の利用範囲決定 |
| **③ Credential 生成** | **自社認証基盤 Engine** | **外部 SaaS Engine** |
| **④ Credential 受領** | アプリチーム → Admin API / Portal から | アプリチーム → SaaS Console から |
| **⑤ Credential 配布 / 保管** | アプリチーム → Partner へ安全配布 | アプリチーム → 自社 Secrets Manager に保管 |
| **⑥ ローテ運用** | アプリチーム ↔ Partner | アプリチーム ↔ SaaS |
| **⑦ トラブル対応** | アプリチーム ↔ Partner | アプリチーム ↔ SaaS |
| **⑧ 廃止・契約終了** | アプリチーム ↔ Partner | アプリチーム ↔ SaaS |

→ **方向が違うだけで責務構造は同型**。「自律性」要求は Inbound でも Outbound でも同じ理由（アプリチームのリリースサイクルと一致）で正当化される。

### §C-6.2.2 対称性の可視化

```mermaid
flowchart LR
    subgraph Inbound["Inbound（外部 → 自アプリ）"]
        Partner[Partner B2B]
        AppIn[自アプリ API GW]
        AUTH1[自社認証基盤<br/>Engine]
        AppIn_team[アプリチーム]

        AppIn_team -.①②⑦⑧ Relationship.-> Partner
        AppIn_team -.④受領.-> AUTH1
        AppIn_team -.⑤配布.-> Partner
        AUTH1 -.JWT.-> AppIn
        Partner -.Bearer JWT.-> AppIn
    end

    subgraph Outbound["Outbound（自アプリ → 外部）"]
        AppOut[自アプリ Lambda]
        SaaS[外部 SaaS]
        AUTH2[SaaS Engine]
        AppOut_team[アプリチーム]
        SM[Secrets Manager]

        AppOut_team -.①②⑦⑧ Relationship.-> SaaS
        AppOut_team -.④受領.-> AUTH2
        AppOut_team -.⑤保管.-> SM
        SM -.credential.-> AppOut
        AppOut -.API Key/Bearer.-> SaaS
    end

    style Inbound fill:#e3f2fd
    style Outbound fill:#fff3e0
```

### §C-6.2.3 顧客説明用：本構造のメリット

| 観点 | 顧客に提示するメッセージ |
|---|---|
| **CIAM 専門性の享受** | エンドユーザー認証は CIAM 専門組織（認証基盤チーム）が中央で運用、スケールメリットと専門性を業界 SaaS 同等に活用 |
| **アプリチームの自律性** | Partner / SaaS との運用関係はアプリチームに完結、リリースサイクルと整合、過剰な部門間連携なし |
| **業界標準モデル** | Auth0 / Okta / Keycloak と同じ Engine 中央 + Admin 委譲パターンで、顧客 IdP 連携時の互換性確保 |
| **ガバナンス保証** | 後述（§C-6.6）の 5 Layer 検知で「アプリ自律でも実装漏れ防止」を技術的に担保 |

### §C-6.2.4 TBD / 要確認

- Q: Outbound で利用予定の **既存 SaaS リスト** 棚卸し → `API-A-264`（Phase A）
- Q: Outbound と Inbound の **責務分担明示の合意プロセス**（誰がサインオフするか）→ `API-B-265`

### §C-6.2.5 Inbound 認証パターン詳細（7 パターン × 5 大分類）

**このサブセクションで定めること**：Inbound 認証の 7 パターンとそれを束ねる 5 大分類のフレーム、および Keycloak/Cognito 対応状況。
**主な判断軸**：顧客との初期会話は「大分類」、技術詳細議論は「7 パターン」のレイヤー使い分け。Tier 表現（Bronze/Silver/Gold）は廃止。
**§C-6 全体との関係**：§C-6.3 4 領域モデルの「② Inbound Partner Auth」の具体的選択肢。

#### §C-6.2.5.1 7 パターン早見表

| # | パターン | 大分類 | セキュリティ強度 | Keycloak | Cognito |
|:---:|---|:---:|:---:|:---:|:---:|
| **P-1** | OAuth 2.0 Client Credentials Grant | OAuth トークン | 中-高 | ✅ ネイティブ | ✅ Plus tier (2024-11 GA) |
| **P-2** | OAuth 2.0 Token Exchange (RFC 8693) | OAuth トークン | 高 | ✅ ネイティブ（v22+）| ❌ **未対応** |
| **P-3** | OAuth 2.0 JWT Bearer Grant (RFC 7523) | OAuth トークン | 高 | ✅ ネイティブ | ❌ 未対応 |
| **P-4** | mTLS (Mutual TLS, RFC 8705) | 証明書 (mTLS) | 最高 | ✅ ネイティブ | △ API GW 別レイヤー |
| **P-5** | API Key + Usage Plan | 共有秘密キー | 低 | – | – |
| **P-6** | HMAC Signature（Webhook 受信）| 共有秘密キー | 中 | – | – |
| **P-7** | AWS IAM Cross-account (SigV4) | AWS IAM 署名 | 高 | – | – |

#### §C-6.2.5.2 5 大分類定義

| 大分類 | 内容 | 該当パターン |
|---|---|---|
| **OAuth トークン** | IdP で credential 認証 → Bearer JWT 取得 → API 呼出に提示 | P-1 / P-2 / P-3 |
| **証明書 (mTLS)** | クライアント証明書を TLS handshake で検証 | P-4 |
| **共有秘密キー** | 事前共有 secret を提示（静的）または署名計算（動的）| P-5 / P-6 |
| **AWS IAM 署名** | AWS SDK が SigV4 で各リクエスト署名 | P-7 |
| **その他** | 上記いずれにも該当しない独自方式 | 個別検討 |

#### §C-6.2.5.3 プラットフォーム選定示唆

| 採用 protocol | 推奨プラットフォーム | 根拠 |
|---|---|---|
| P-1 のみ | Cognito Plus tier or Keycloak | どちらでも可、コスト・運用負荷で選定 |
| **P-2 Token Exchange を採用** | **Keycloak 必須**（Cognito 未対応）| RFC 8693 サポートは Keycloak のみ |
| **P-3 JWT Bearer Grant を採用** | **Keycloak 必須** | Cognito 未対応 |
| **P-4 mTLS を採用** | Keycloak が望ましい | Cognito は API GW 別レイヤー必要 |
| P-5/P-6/P-7 | 認証基盤に依存しない | プラットフォーム選定への影響なし |

→ **Keycloak 採用根拠の中核は P-2 / P-3 / P-4**（[`project_platform_direction_keycloak`](memory) と整合）。

#### §C-6.2.5.4 大分類別フロー（Inbound）

各大分類について「初期設定時のオンボーディング手順」と「実行時の認証フロー」を整理。詳細 mermaid フロー図は **[customer-doc/01-external-api-auth-decision-guide.md §2.1「大分類別フロー」](../../customer-doc/01-external-api-auth-decision-guide.md)** に完備。本標準側ではサマリ表を掲載。

##### Inbound 大分類別 認証時フロー サマリ

| 大分類 | Step 1 | Step 2 | Step 3 | API GW 側設定 |
|---|---|---|---|---|
| OAuth トークン | IdP /oauth2/token で credential 認証 | Bearer JWT 取得 + Cache | API GW へ Bearer 提示 → JWT Authorizer 検証 | **JWT Authorizer** |
| 証明書 (mTLS) | TLS Handshake で Client Cert 提示 | Truststore で chain 検証 + CRL/OCSP | cert binding を context に注入 → Lambda へ | **mTLS Custom Domain** |
| 共有秘密キー (API Key) | x-api-key ヘッダで送信 | API GW Usage Plan で throttle/quota 検証 | リクエスト転送 | **API Key Required + Usage Plan** |
| 共有秘密キー (HMAC) | POST + X-Signature + X-Timestamp + body | Lambda Authorizer で HMAC + Timestamp + Idempotency 検証 | リクエスト転送 | **Lambda Authorizer** |
| AWS IAM 署名 | Partner: STS AssumeRole + SigV4 署名 | API GW: AWS IAM が SigV4 検証 + Policy 評価 | リクエスト転送 | **AuthorizationType=AWS_IAM** |

##### Inbound 大分類別 初期設定時フロー サマリ

| 大分類 | 主要工程 |
|---|---|
| OAuth トークン | ① 契約 → ② Self-Service Portal で M2M Client 作成 → ③ client_id/secret 発行 → ④ Partner へ secret 安全配布 → ⑤ Partner Secrets 保管 |
| 証明書 (mTLS) | ① 契約 → ② Partner CSR 生成 → ③ 自社 CA 署名 → ④ Cert 配布 → ⑤ Truststore に Partner CA 登録 → ⑥ mTLS Listener 設定 |
| 共有秘密キー (API Key) | ① 契約 → ② Usage Plan 作成 → ③ API Key 発行 → ④ Plan に紐付け → ⑤ Partner へ Key 配布 |
| 共有秘密キー (HMAC) | ① SaaS Console で Webhook 設定 → ② Secret 発行 → ③ Secrets Manager 保管 → ④ Lambda Authorizer 設定 |
| AWS IAM 署名 | ① 契約 + Partner account ID 取得 → ② Cross-account Role 作成 → ③ Trust Policy 設定 → ④ Role ARN 共有 → ⑤ Partner 側 AssumeRole 権限設定 |

#### §C-6.2.5.5 Tier 表現の廃止

旧設計で使用していた Bronze / Silver / Gold tier 表現は **本標準では廃止**：

| 旧 Tier | 新 P-x 表現 | 廃止根拠 |
|---|---|---|
| Bronze | P-1 OAuth Client Credentials または P-5 API Key | 「Bronze って何？」が解消、具体 protocol で議論 |
| Silver | P-2 Token Exchange | RFC 8693 という具体仕様 |
| Gold | P-4 mTLS + P-1/P-2 併用 | mTLS + OAuth の組合せ明示可 |
| 該当なし | P-3 / P-6 / P-7 | Tier フレームが網羅できなかった protocol を追加 |

→ **本標準以降は「P-1〜P-7 のどれか」で議論**、Tier 表現は使わない。

#### §C-6.2.5.6 TBD / 要確認

- Q: P-2 Token Exchange の **採用想定**有無（Keycloak 採用必須性と直結）→ `API-A-2651`（Phase A）
- Q: P-4 mTLS の **採用想定**有無（規制業界連携）→ `API-A-2652`（Phase A）
- Q: P-3 JWT Bearer Grant の採用想定有無 → `API-B-2653`
- Q: P-6 HMAC Webhook 受信の想定（Stripe / GitHub / Auth0 等）→ `API-A-2654`（Phase A）
- Q: P-7 AWS IAM Cross-account の採用想定（AWS Marketplace 連携等）→ `API-B-2655`

### §C-6.2.6 Outbound 認証パターン詳細（5 大分類）

**このサブセクションで定めること**：Outbound 認証は外部 SaaS が protocol を決めるため、自由な設計判断ではなく「SaaS の規定に従ったクライアント実装 + Secrets Manager 保管」の運用設計。
**主な判断軸**：自社で Engine を持たない、credential の安全保管 + ローテーション運用が中核。
**§C-6 全体との関係**：§C-6.3 4 領域モデルの「③ Outbound SaaS Auth」の具体実装パターン。

#### §C-6.2.6.1 Outbound の特性

| 観点 | Inbound（§C-6.2.5）| Outbound（本セクション）|
|---|---|---|
| **誰がプロトコルを決めるか** | 自社が決める（Partner に従わせる）| **外部 SaaS が決める**（自社は従う）|
| **設計判断** | Active な選択（7 パターンからの選定）| Passive な対応（SaaS の規定実装）|
| **Engine 所在** | 自社認証基盤（Keycloak Partner Realm 等）| **外部 SaaS** |
| **自社の責務** | Engine 運用 + Realm 管理 + Authorizer | **client 実装 + credential 安全保管 + ローテ運用** |

#### §C-6.2.6.2 代表 SaaS 別 Outbound 認証

| SaaS | 要求 protocol | 大分類 | 自社の実装 |
|---|---|:---:|---|
| **Stripe** | API Key | 共有秘密キー | Authorization: Bearer <key> |
| **SendGrid** | API Key | 共有秘密キー | Authorization: Bearer <key> |
| **OpenAI** | API Key | 共有秘密キー | Authorization: Bearer <key> |
| **Slack** | OAuth Auth Code | OAuth トークン | OAuth Flow + Token Refresh |
| **GitHub PAT** | API Key 相当 | 共有秘密キー | Header 送信 |
| **GitHub App** | JWT Bearer + Installation Token | OAuth トークン | JWT 署名 + Token 取得 |
| **Microsoft Graph** | OAuth Client Credentials | OAuth トークン | P-1 と同等の Outbound 版 |
| **AWS Services** | AWS SDK SigV4 | AWS IAM 署名 | SDK 自動署名 |
| **金融機関 API（一部）** | mTLS | 証明書 (mTLS) | mTLS Client 実装 |

→ **Outbound 主流は「API Key」**（業界の SaaS 主流が API Key のため）。

#### §C-6.2.6.3 大分類別フロー サマリ（Outbound）

##### Outbound 大分類別 認証時フロー サマリ

| 大分類 | Step 1 | Step 2 | Step 3 |
|---|---|---|---|
| OAuth トークン | Secrets Manager から secret 取得 | SaaS /token で Bearer 取得（Cache 活用）| SaaS API へ Bearer で呼出 |
| 証明書 (mTLS) | Secrets Manager から cert + 秘密鍵 取得 | mTLS Handshake で SaaS へ接続 | HTTPS リクエスト送信 |
| 共有秘密キー (API Key) | Secrets Manager から API Key 取得 | Authorization: Bearer or x-api-key ヘッダ | SaaS API 呼出 |
| 共有秘密キー (HMAC) | Secrets Manager から shared secret 取得 | payload + HMAC 計算 + Timestamp | Partner endpoint へ POST |
| AWS IAM 署名 | STS AssumeRole で一時 credential 取得 | AWS SDK で SigV4 署名 | Partner AWS Service へリクエスト |

##### Outbound 大分類別 初期設定時フロー サマリ

| 大分類 | 主要工程 |
|---|---|
| OAuth トークン | ① SaaS Console で Application 登録 → ② client_id/secret 受領 → ③ Secrets Manager 保管 → ④ Lambda IAM Role に Secret 取得権限 |
| 証明書 (mTLS) | ① 契約 → ② CSR 生成 → ③ 自社 or SaaS 指定 CA で署名 → ④ Cert + 秘密鍵 を Secrets Manager 保管 → ⑤ SaaS に公開鍵 登録 |
| 共有秘密キー (API Key) | ① SaaS 申込 → ② Console で API Key 発行 → ③ Secrets Manager 保管 → ④ Lambda IAM 権限付与 → ⑤ 自動ローテ設定 |
| 共有秘密キー (HMAC) | ① Partner と Webhook 連携契約 → ② 自社で shared secret 生成 → ③ Partner へ暗号化配布 → ④ Secrets Manager 保管 |
| AWS IAM 署名 | ① Partner と契約 → ② AWS account ID 共有 → ③ Partner 側で Cross-account Role 作成（Trust Policy: 自社）→ ④ 自社 Lambda Execution Role に AssumeRole 権限 |

→ 詳細 mermaid フロー図は **[customer-doc/01-external-api-auth-decision-guide.md §2.1「Outbound 大分類別フロー」](../../customer-doc/01-external-api-auth-decision-guide.md)** に完備。

#### §C-6.2.6.4 Outbound のガバナンス（中央管理項目）

「Outbound は各アプリ自律」原則のもと、中央が担保すべきガバナンス：

| 項目 | 中央の責務 | 仕組み |
|---|---|---|
| **Approved SaaS Allowlist** | 接続可能 SaaS を Security/Legal レビュー後にカタログ化 | Service Catalog テンプレ + Config Rule 強制 |
| **Secrets Manager 必須化** | 環境変数 / コード埋め込みを禁止 | Config Rule `secretsmanager-secret-stored` |
| **自動ローテーション** | 90/180/365 日周期で自動ローテ強制 | Config Rule `secretsmanager-rotation-enabled` |
| **CMK 暗号化** | KMS カスタマーマネージドキー必須 | Service Catalog で `KmsKeyId` 必須化 |
| **DPA / 法務確認** | APPI 28 条越境移転 / GDPR 28 条 Data Processor 契約 | 法務台帳 + タグ紐付け + 年次棚卸し |
| **Egress filtering** | 接続先 SaaS の allowlist | VPC Endpoint + Network Firewall |
| **コスト按分** | 外部 SaaS との通信量・課金 monitor | FinOps タグ + Cost Explorer |

#### §C-6.2.6.5 TBD / 要確認

- Q: 既存利用 SaaS の **棚卸しリスト**作成 → `API-A-266`（Phase A、§C-6.2.4 と統合）
- Q: Approved SaaS Allowlist の **決裁プロセス**（誰が承認 / 棚卸し頻度）→ `API-B-2661`
- Q: Outbound credential の **自動ローテ採用範囲**（全 SaaS / 重要 SaaS のみ）→ `API-C-2662`

---

## §C-6.3 4 領域 × 担当 最終モデル

**このサブセクションで定めること**：外部 API 認証を 4 領域に分類し、各領域での Engine / Relationship / ガバナンスの責任配置を確定する。
**主な判断軸**：End-User の中央化メリット最大化 + Partner/Outbound のアプリ自律性 + Private の AWS native 活用。
**§C-6 全体との関係**：本章の中核モデル。§FR-API-2 / §C-API-3 の責務分担表の根拠。

### §C-6.3.1 ベースライン：4 領域モデル

| 領域 | Engine（中央 提供）| Relationship 運用（分散 = アプリチーム）| 中央ガバナンス |
|---|---|---|---|
| **① Public End-User Auth** | **共有認証基盤 Engine**（Public Realm）<br/>OAuth Auth Code + PKCE / BFF | – （アプリチームは検証のみ）| CIAM 標準 / IPA 認証 |
| **② Inbound Partner Auth** | **共有認証基盤 Engine**（Partner Realm 分離）<br/>OAuth Client Credentials / Token Exchange / mTLS<br/>+ **Self-Service Developer Portal** | **アプリチーム**：<br/>Partner と契約 / scope 設計 / Client 作成（Portal 経由）/ Secret 配布 / ローテ調整 | 命名規約 / scope policy / 承認フロー / 監査 |
| **③ Outbound SaaS Auth** | **外部 SaaS Engine**（弊社外）| **アプリチーム**：<br/>SaaS 契約 / credential 取得 / Secrets Manager 保管 / ローテ調整 | Approved SaaS Allowlist / DPA / Service Catalog テンプレ / FinOps 按分 |
| **④ Private（AWS native）** | **AWS IAM Engine** | アプリチーム：IAM Role 設計 / VPC Lattice Auth Policy | SCP / Permissions Boundary |

→ **Engine 提供は中央、Relationship 運用は分散** という構造で 4 領域すべて一貫。

### §C-6.3.2 全体像（アーキテクチャ図）

```mermaid
flowchart TB
    subgraph Central["中央（認証基盤チーム + Platform + Security/Legal）"]
        AUTH["共有認証基盤 Engine<br/>(Keycloak)<br/>- Public Realm<br/>- Partner Realm<br/>- Token Exchange<br/>- 信頼台帳"]
        PORTAL["Self-Service Developer Portal<br/>- Partner Client 作成 UI<br/>- scope 申請ワークフロー<br/>- 承認フロー<br/>- Secret 配布チャネル"]
        SC["Service Catalog<br/>- API GW templates<br/>- ⭐ Outbound SaaS templates"]
        GOV["Governance<br/>- Approved SaaS Allowlist<br/>- 命名規約 / scope policy<br/>- 承認プロセス"]
        FMS["FMS WAF / Config Rules<br/>- 認証強制 6 ルール"]
        DET["Detection 5 Layer<br/>- IaC / Config / Static<br/>- Runtime Log / Behavioral"]
    end

    subgraph AppA["App A チーム（自律運用）"]
        AppA_team["アプリ開発者"]
        AGWA["API GW (Inbound)"]
        AppA_Lambda["Lambda / ECS"]
        SMA["Secrets Manager<br/>(Outbound credentials)"]
    end

    subgraph External["対抗先"]
        EU["End User"]
        Partner["Inbound Partner"]
        SaaS["Outbound SaaS"]
    end

    AppA_team -.Inbound 申請.-> PORTAL
    PORTAL -.Engine 呼出.-> AUTH
    AppA_team -.Outbound 申請.-> GOV
    GOV -.allowlist 強制.-> SMA

    SC -.deploy templates.-> AGWA
    SC -.deploy templates.-> SMA
    FMS -.rules.-> AGWA
    DET -.全 Layer 監視.-> AGWA

    AUTH -.JWT.-> EU
    AUTH -.JWT.-> Partner
    EU -->|Bearer JWT| AGWA
    Partner -->|Bearer JWT| AGWA
    AGWA --> AppA_Lambda
    SMA -.credential.-> AppA_Lambda
    AppA_Lambda -->|"API Key / Bearer"| SaaS

    style Central fill:#e3f2fd
    style AppA fill:#e8f5e9
    style External fill:#fff3e0
    style PORTAL fill:#fff9c4
    style DET fill:#ffcdd2
```

### §C-6.3.3 顧客説明用：本モデルの選定根拠

| 顧客が問う論点 | 本モデルの答え |
|---|---|
| **「なぜ End-User と Partner を分けるのか」** | エンドユーザーは CIAM 専門性 + スケール（10M MAU 想定）が必要、Partner は M2M で性質が異なる。同じ Engine だが Realm 分離で SLA / 障害境界を独立化 |
| **「なぜ Outbound は中央化しないのか」** | アプリ固有の SaaS 選定はリリース判断と一体、中央化すると新規 SaaS 採用のリードタイムが過剰。Approved Allowlist + Service Catalog で安全担保 |
| **「Private はなぜ別か」** | AWS-to-AWS は IAM SigV4 で最低レイテンシ・最高セキュリティが達成可能、認証基盤を介在させる価値なし |
| **「アプリ自律で本当に安全か」** | 後述 §C-6.6 の 5 Layer 検知で 95-99% 担保、§C-6.10 の C1-C10 条件を全部満たした上で解禁 |

### §C-6.3.4 TBD / 要確認

- Q: **Partner Realm の SLA 目標**（Public Realm と独立目標を持つか）→ `API-B-266`
- Q: **Approved SaaS Allowlist の承認プロセス**（誰が決裁 / 棚卸し頻度）→ `API-B-267`
- Q: VPC Lattice **採用範囲**（Private 全域 / 重要 service のみ）→ `API-B-268`

---

## §C-6.4 Self-Service Developer Portal

**このサブセクションで定めること**：アプリチームが認証基盤 Engine を Self-Service で利用できる UI / API / ワークフローの標準。
**主な判断軸**：自律性 + ガバナンス + 監査の両立、業界標準（Auth0 / Okta / Backstage）との整合。
**§C-6 全体との関係**：§C-6.3 4 領域モデルの「② Inbound Partner Auth」を実現するキー機構。

### §C-6.4.1 ベースライン：機能要件

Developer Portal が提供すべき 6 機能：

| # | 機能 | 内容 |
|---|---|---|
| **F1** | **Partner Client 作成 UI** | アプリチームが Partner ごとに M2M Client を作成 |
| **F2** | **scope 申請ワークフロー** | 既定 scope は自動承認、新規 scope / PII / 決済関連はセキュリティレビュー |
| **F3** | **Credential 受領チャネル** | client_id / client_secret を安全に受け取る（暗号化メール / Secrets Manager cross-account share / 1Password Business）|
| **F4** | **ローテーション管理** | 期限通知 / 旧新併存運用 / 緊急ローテ |
| **F5** | **監査ログ** | 誰がいつどの Partner Client を作成・変更・削除したか |
| **F6** | **棚卸し** | 各アプリの Partner Client 一覧 / 利用状況 / 死蔵検出 |

### §C-6.4.2 実装オプション

| オプション | 概要 | 評価 |
|---|---|---|
| **A. Keycloak Admin Console 直接利用 + IAM 委譲** | Keycloak 標準 UI を Realm-level Admin として利用 | ✅ 最速立ち上げ、業界標準、Self-Service Portal なし |
| **B. Backstage（CNCF）+ Keycloak Plugin** | 開発者ポータル業界デファクト、Plugin で Keycloak 統合 | ⚠ 学習コスト、運用負荷大、Catalog 統合価値あり |
| **C. 自作 SPA + Keycloak Admin API** | 自社要件に合わせて構築 | ⚠ 開発コスト高、独自運用、機能拡張柔軟 |
| **D. AWS Marketplace SaaS（CloudEntity 等）** | 商用 Partner Management Platform | ⚠ コスト、vendor lock-in |

→ **推奨：A を初期、B/C を中期検討**。A で Self-Service の本質（中央 Engine + 委譲 Admin）は達成可能、UI 体験向上は後段。

### §C-6.4.3 ワークフロー例（Partner 新規オンボーディング）

```mermaid
sequenceDiagram
    participant App as アプリチーム
    participant Portal as Developer Portal
    participant Sec as Security レビュー
    participant Engine as 認証基盤 Engine
    participant Partner as Partner

    App->>Partner: ① 営業 / 契約
    App->>Portal: ② Partner Client 申請<br/>(Partner 情報, 必要 scope)
    Portal->>Portal: ③ 既定 scope か判定
    alt 既定 scope のみ
        Portal->>Engine: ④ Admin API で Client 作成
        Engine-->>Portal: client_id, client_secret
    else 新規 scope / PII / 決済関連
        Portal->>Sec: ④' レビュー依頼
        Sec->>Portal: ⑤' 承認
        Portal->>Engine: ⑥' Admin API で Client 作成
        Engine-->>Portal: client_id, client_secret
    end
    Portal->>App: ⑦ 配布チャネル経由で credential 受領
    App->>Partner: ⑧ Partner へ安全配布
    Partner->>Engine: ⑨ /oauth2/token で token 取得
    Partner->>App: ⑩ Bearer JWT で API 呼出
```

### §C-6.4.4 TBD / 要確認

- Q: 実装オプション **A / B / C / D の選定**（初期版はどれで開始するか）→ `API-D-269`
- Q: Credential 配布チャネルの **標準化**（暗号化メール許容範囲 / Secrets Manager cross-account share）→ `API-B-270`
- Q: 棚卸し頻度（**月次 / 四半期**）→ `API-C-271`

---

## §C-6.5 ガバナンス Two-Track 設計

**このサブセクションで定めること**：日常運用は自律、増分リスク操作は中央承認という Two-Track でガバナンスを担保する設計。
**主な判断軸**：自律性を損なわず、不可逆 / 高影響操作のみ中央承認に倒す。
**§C-6 全体との関係**：§C-6.3 のアプリ自律性と §C-6.6 の技術的担保の中間に立つ「組織的ガバナンス」。

### §C-6.5.1 ベースライン：Two-Track 境界線

| 操作 | アプリチーム自律 | 中央承認必要 | 承認者 |
|---|:---:|:---:|---|
| 新規 Partner Client 作成（既定 scope のみ）| ✅ | – | – |
| 既定 scope での発行 | ✅ | – | – |
| Secret rotation 実行 | ✅ | – | – |
| Client 削除（自分のアプリの分）| ✅ | – | – |
| **新規 scope 定義** | – | ✅ | Security |
| **PII / 決済 / 医療関連 scope の付与** | – | ✅ | Security + Legal |
| **新規 Partner IdP の信頼台帳登録（Silver tier）** | – | ✅ | Security |
| **新規 SaaS の Approved Allowlist 追加** | – | ✅ | Security + Legal |
| **mTLS Truststore への新規 CA 追加（Gold tier）** | – | ✅ | Security |
| Token TTL 上限変更（max 1h を超える）| – | ✅ | Security |

### §C-6.5.2 自動化されたガードレール

承認プロセスを経ない日常操作にも、以下の自動ガードレールを適用：

| 機構 | 対象 |
|---|---|
| **命名規約自動検証** | client 名 / scope 名 が規約パターンに沿っているか |
| **scope カタログ強制** | カタログ外の scope 自由作成を禁止 |
| **Token TTL 上限強制**（既定 1h）| 長期 token 発行禁止 |
| **secret 強度強制** | 自動生成 + 32 文字以上 + 必要なエントロピー |
| **作成・変更ログ Audit** | CloudTrail / Keycloak Admin Events 必須 |
| **Outbound: Service Catalog 経由強制** | 環境変数 credential を持つ Lambda の deploy 拒否 |
| **rotation 期限切れ検知** | Config Rule で自動アラート |

### §C-6.5.3 顧客説明用：本設計の意義

| 観点 | メッセージ |
|---|---|
| **自律性とガバナンスの両立** | 「ガバナンス強化 = 自律性低下」というトレードオフを Two-Track 設計で回避 |
| **増分リスクへの精密対応** | リスクの高い操作だけに承認を集中させ、リスク低い操作は妨げない |
| **業界標準性** | PCI DSS Req 8 / APPI 法 23 の「最小権限 + 重要操作の承認」要求と整合 |

### §C-6.5.4 TBD / 要確認

- Q: 承認 SLA（例：**24h 以内に承認 / 却下**）→ `API-B-272`
- Q: 既定 scope カタログの **初期定義範囲**（read / write / admin の 3 段階か業務分類か）→ `API-B-273`
- Q: 承認ワークフローの **実装手段**（Slack / ServiceNow / Jira / 自作）→ `API-C-274`

---

## §C-6.6 認証実装漏れの 6 パターン × 5 検知レイヤー

**このサブセクションで定めること**：「アプリに認証を寄せる」決定の技術的前提となる、認証実装漏れの分類と検知レイヤーの体系。
**主な判断軸**：技術的にガバナンス担保可能であれば自律性を解禁、不可能であれば中央集約に倒す。
**§C-6 全体との関係**：§C-6.3 4 領域モデルの「アプリ自律」部分の安全性根拠。

### §C-6.6.1 ベースライン：6 漏れパターン

「認証が実装されていない」と言っても、実態は 6 種類のパターンがある：

| # | 漏れパターン | 例 | 影響 |
|---|---|---|---|
| **P1** | **AuthorizationType=NONE で deploy** | API GW Method を Authorizer なしで deploy | ⭐ 最重大 |
| **P2** | **Authorizer 設定済だが無効化されている** | Authorizer はあるが Lambda が常に Allow を返す | 重大 |
| **P3** | **Authorizer 通過後にアプリ内 2 段検証なし** | scope / tenant_id 検証がアプリコードに欠如 | 中（テナント漏洩等）|
| **P4** | **特定 path / method の bypass** | `/health` だけ open のつもりが `/api/admin` も open | 重大 |
| **P5** | **JWT 検証ロジックのバグ** | signature 検証スキップ / iss/aud 未検証 / `none` alg 受容 | 重大 |
| **P6** | **ALB / Function URL で IAM/OIDC 設定なし、かつアプリコード検証も不在** | ALB → 直接 Lambda、コード内も素通り | 重大 |

### §C-6.6.2 5 検知レイヤー

これら 6 パターンを検知する 5 段のレイヤー：

| Layer | タイミング | 手段 | 代表ツール |
|---|---|---|---|
| **L1: IaC** | Pre-deploy | CloudFormation / CDK / Terraform 構文解析 | cfn-guard / cdk-nag / Checkov / OPA |
| **L2: Config** | Post-deploy（リソース構成）| AWS Config Rules / describe-* API | AWS Config Rules / Resource Explorer |
| **L3: Static Code** | Pre-deploy（コード）| AST 解析 / pattern match | Semgrep / ast-grep / CodeQL |
| **L4: Runtime Log** | 運用中（実トラフィック）| CloudWatch / CloudTrail / Athena | Athena query / CloudWatch Insights |
| **L5: Behavioral** | 運用中（能動探査）| 合成監視 / 未認証 probe | CloudWatch Synthetics / OWASP ZAP |

### §C-6.6.3 検知マトリクス（6 パターン × 5 Layer）

各漏れパターンをどの Layer で検知できるか：

| パターン | L1 IaC | L2 Config | L3 Static Code | L4 Runtime Log | L5 Behavioral |
|---|:---:|:---:|:---:|:---:|:---:|
| **P1** AuthorizationType=NONE | ✅ 確実 | ✅ 確実 | – | ✅ 検出可 | ✅ 確実 |
| **P2** Authorizer 無効化 | ❌ 不可 | ❌ 不可 | ⚠ パターン依存 | ✅ 検出可 | ✅ 確実 |
| **P3** アプリ 2 段検証なし | ❌ 不可 | ❌ 不可 | ⚠ パターン依存 | ⚠ 観測内容依存 | ⚠ tenant 越境 probe |
| **P4** path bypass | ⚠ 一部 | ⚠ Method 単位 | ⚠ パターン依存 | ✅ 全 path enum | ✅ 確実 |
| **P5** JWT 検証バグ | ❌ 不可 | ❌ 不可 | ✅ Semgrep ルール | ⚠ 異常 token 限定 | ✅ 既知バグ probe |
| **P6** ALB + コード素通り | ⚠ 部分 | ⚠ ALB 検知困難 | ✅ ハンドラ検証 | ⚠ 観測のみ不足 | ✅ 確実 |

→ **L1+L2 だけだと P2 / P3 / P5 / P6 が漏れる**。L3 + L5 併用で多くを担保。

### §C-6.6.4 L1: IaC Pre-Deploy 詳細

**主要ツール**：

| ツール | 種別 | コスト | AWS 対応 |
|---|---|:---:|:---:|
| **AWS CloudFormation Guard (cfn-guard)** | OSS / AWS 公式 | 無料 | ✅ CFN ネイティブ |
| **cdk-nag** | OSS / CDK 用 Aspect | 無料 | ✅ CDK ネイティブ |
| **Checkov** | OSS / マルチ IaC | 無料 | ✅ CFN / TF / K8s |
| **OPA Conftest** | OSS / 言語非依存 | 無料 | ✅ |

**設置場所**：

```
[Developer Local] → pre-commit hook (cfn-guard / cdk-nag)
        ↓
[GitHub Actions / GitLab CI] → cfn-guard validate / cdk synth + cdk-nag
        ↓ Pass
[Service Catalog Provisioning] → 強制テンプレ
```

**cfn-guard ルールサンプル**：

```hcl
# api-gw-authorizer-required.guard

let api_gw_methods = Resources.*[ Type == 'AWS::ApiGateway::Method' ]

rule api_gw_must_have_authorizer when %api_gw_methods !empty {
    %api_gw_methods.Properties {
        AuthorizationType != "NONE"
        <<API GW Method must have non-NONE AuthorizationType>>
    }
}

let lambda_urls = Resources.*[ Type == 'AWS::Lambda::Url' ]

rule lambda_url_must_have_iam_auth when %lambda_urls !empty {
    %lambda_urls.Properties {
        AuthType == "AWS_IAM"
        <<Lambda Function URL must use AWS_IAM auth, not NONE>>
    }
}

let alb_listeners = Resources.*[ Type == 'AWS::ElasticLoadBalancingV2::Listener' ]

rule alb_must_have_auth_action when %alb_listeners !empty {
    %alb_listeners.Properties.DefaultActions[*] {
        Type IN ["authenticate-oidc", "authenticate-cognito"]
        <<ALB Listener must have authenticate-oidc or authenticate-cognito action>>
    }
}
```

**cdk-nag サンプル**：

```typescript
import { AwsSolutionsChecks } from 'cdk-nag';
import { App, Aspects } from 'aws-cdk-lib';

const app = new App();
const stack = new MyApiStack(app, 'MyApiStack');

Aspects.of(stack).add(new AwsSolutionsChecks({ verbose: true }));
// cdk-nag は以下を自動検出:
//  - APIG4: API GW Method の Authorization 設定
//  - LMB5: Lambda Function URL の AuthType=NONE
//  - ELB7: ALB の Access logging
```

**CI 統合（GitHub Actions）**：

```yaml
# .github/workflows/iac-validate.yml
- name: cfn-guard validate
  run: cfn-guard validate -r rules/auth-required.guard -d cloudformation/
- name: Block PR on violation
  if: failure()
  run: exit 1
```

**検知可能漏れパターン**：

| パターン | 検知可能性 |
|---|:---:|
| P1 AuthorizationType=NONE | ✅ 確実 |
| P2 Authorizer 無効化（コード）| ❌ 不可 |
| P3 アプリ 2 段検証なし | ❌ 不可 |
| P4 path bypass | ⚠ Method 単位なら部分 |
| P5 JWT 検証バグ | ❌ 不可 |
| P6 ALB 認証 action なし | ✅ alb_must_have_auth_action で |

**運用注意**：

- **False positive 対策**：`/health` 等の例外は guard 注釈で個別承認
- **段階導入**：既存 stack は warn、新規は error
- **共通リポ配布**：rules/ を別リポで集中管理、各アプリは consumer
- **コスト**：OSS、CI 計算時間のみ（無視できるレベル）

### §C-6.6.5 L2: Config Rules（Deploy 後・継続監査）詳細

**主要ツール**：

| ツール | 種別 |
|---|---|
| **AWS Config Managed Rules** | AWS 公式（80+ rule）|
| **AWS Config Custom Rules** | Lambda で自前判定 |
| **Config Aggregator** | Org 全 account 集約 |
| **Auto-remediation (SSM)** | 違反時の自動修復 |

**設置場所**：

```
[Resource 作成 / 変更]
        ↓ CloudTrail event
[AWS Config] → ルール評価
        ↓ NON_COMPLIANT
[EventBridge] → Lambda → Slack / Jira
        ↓ (オプション)
[SSM Run Document] → 自動修復
```

**マネージドルール一覧（認証関連）**：

| ルール名 | 検知内容 |
|---|---|
| `api-gw-method-authorizer-required` | API GW Method の AuthorizationType≠NONE |
| `api-gwv2-authorization-type-configured` | HTTP API の Authorizer 設定 |
| `lambda-function-url-auth` | Lambda Function URL の AuthType=AWS_IAM |
| `appsync-authorization-check` | AppSync の AuthenticationType 設定 |
| `alb-http-to-https-redirection-check` | HTTPS リダイレクト強制 |
| `api-gw-execution-logging-enabled` | API GW の execution log 有効化 |

**Custom Rule サンプル（ALB 認証 action）**：

```python
# config-rule-alb-auth-action.py
import boto3
import json

def lambda_handler(event, context):
    invoking_event = json.loads(event['invokingEvent'])
    config_item = invoking_event['configurationItem']
    compliance = 'NOT_APPLICABLE'

    if config_item['resourceType'] == 'AWS::ElasticLoadBalancingV2::Listener':
        config = config_item.get('configuration', {})
        default_actions = config.get('defaultActions', [])

        has_auth = any(
            action.get('type') in ['authenticate-oidc', 'authenticate-cognito']
            for action in default_actions
        )

        compliance = 'COMPLIANT' if has_auth else 'NON_COMPLIANT'

    config_client = boto3.client('config')
    config_client.put_evaluations(
        Evaluations=[{
            'ComplianceResourceType': config_item['resourceType'],
            'ComplianceResourceId': config_item['resourceId'],
            'ComplianceType': compliance,
            'OrderingTimestamp': config_item['configurationItemCaptureTime'],
        }],
        ResultToken=event['resultToken']
    )
```

**自動修復例（SSM Automation）**：

```yaml
schemaVersion: '0.3'
description: 'Auto-disable API GW Method with AuthorizationType=NONE'
parameters:
  RestApiId: { type: String }
  ResourceId: { type: String }
  HttpMethod: { type: String }
mainSteps:
  - name: DisableMethod
    action: aws:executeAwsApi
    inputs:
      Service: apigateway
      Api: UpdateMethod
      restApiId: '{{ RestApiId }}'
      resourceId: '{{ ResourceId }}'
      httpMethod: '{{ HttpMethod }}'
      patchOperations:
        - op: replace
          path: /authorizationType
          value: 'AWS_IAM'
```

**検知可能漏れパターン**：

| パターン | 検知可能性 |
|---|:---:|
| P1 AuthorizationType=NONE | ✅ 確実 |
| P2 Authorizer 無効化 | ❌ Config は設定のみ |
| P3 アプリ 2 段検証なし | ❌ 不可 |
| P4 path bypass | ⚠ Method 単位なら |
| P5 JWT 検証バグ | ❌ 不可 |
| P6 ALB 認証 action なし | ✅ Custom Rule で |

**運用注意**：

- **コスト**：$0.001 / evaluation、Org 全体で月 $50-200
- **遅延**：drift 発生から検知まで数分〜数十分
- **Auto-remediation の慎重採用**：production trafic 中断リスクあり、まず通知から
- **Aggregator 設定**：Org 全 account を 1 つに集約、ダッシュボード化
- **例外管理**：承認済例外 API を別タグで識別、Rule から除外

### §C-6.6.6 L3: Static Code（コード AST 解析）詳細

**主要ツール**：

| ツール | 種別 | 特徴 |
|---|---|---|
| **Semgrep** | OSS / 多言語 | YAML でルール記述、CI 統合容易 |
| **ast-grep** | OSS / 多言語 | TreeSitter ベース、高速 |
| **CodeQL** | GitHub Advanced Security | 強力だが学習曲線、SaaS 課金 |
| **Snyk Code** | 商用 | 既知脆弱パターン中心 |

**設置場所**：

```
[Developer Local] → pre-commit hook (semgrep --config auto)
        ↓
[CI Pipeline] → semgrep ci
        ↓ Pass
[Deploy]
```

**Semgrep ルール: FastAPI 認証 middleware 必須**：

```yaml
rules:
  - id: fastapi-missing-auth-middleware
    pattern: |
      $APP = FastAPI(...)
    pattern-not-inside: |
      $APP = FastAPI(...)
      ...
      $APP.add_middleware($MIDDLEWARE, ...)
    message: "FastAPI app is missing auth middleware. Use app.add_middleware(AuthMiddleware, ...)"
    languages: [python]
    severity: ERROR
    metadata:
      cwe: CWE-306
      category: security
```

**Semgrep ルール: Spring Boot @PreAuthorize 必須**：

```yaml
rules:
  - id: spring-controller-missing-preauthorize
    patterns:
      - pattern-either:
        - pattern: |
            @RestController
            class $CLS {
              ...
              @GetMapping(...)
              public $RT $METHOD(...) { ... }
            }
        - pattern: |
            @RestController
            class $CLS {
              ...
              @PostMapping(...)
              public $RT $METHOD(...) { ... }
            }
      - pattern-not-inside: |
          @PreAuthorize(...)
          public $RT $METHOD(...) { ... }
      - pattern-not-inside: |
          @Secured(...)
          public $RT $METHOD(...) { ... }
    message: "Controller method missing @PreAuthorize or @Secured"
    languages: [java]
    severity: WARNING
```

**Semgrep ルール: JWT 検証バグ検出（P-5 漏れ対策）**：

```yaml
rules:
  - id: jwt-decode-without-verify
    pattern-either:
      - pattern: jwt.decode($TOKEN, ..., verify=False, ...)
      - pattern: jwt.decode($TOKEN, ..., algorithms=["none"], ...)
      - patterns:
        - pattern: jwt.decode($TOKEN, ...)
        - pattern-not: jwt.decode($TOKEN, ..., key=$K, ...)
        - pattern-not: jwt.decode($TOKEN, $K, ...)
    message: "JWT decoded without proper signature verification (P-5)"
    languages: [python]
    severity: ERROR
```

**Semgrep ルール: tenant 越境チェック検出**：

```yaml
rules:
  - id: missing-tenant-validation
    patterns:
      - pattern: |
          def handler(event, context):
            ...
            tenant_id = event['pathParameters'].get('tenant_id')
            ...
      - pattern-not-inside: |
          def handler(event, context):
            ...
            jwt_tenant = event['requestContext']['authorizer']['tenant_id']
            ...
            if $REQ_TENANT != $JWT_TENANT:
              ...
    message: "Handler uses tenant_id from path but doesn't validate against JWT claim (P-3)"
    languages: [python]
    severity: ERROR
```

**Semgrep ルール: Express.js 認証ミドルウェア欠落**：

```yaml
rules:
  - id: express-route-missing-auth
    pattern-either:
      - pattern: |
          $APP.get('/api/$PATH', $HANDLER)
      - pattern: |
          $APP.post('/api/$PATH', $HANDLER)
    pattern-not:
      - pattern: |
          $APP.get('/api/$PATH', authMiddleware, $HANDLER)
      - pattern: |
          $APP.post('/api/$PATH', authMiddleware, $HANDLER)
    message: "Express route under /api/ missing authMiddleware"
    languages: [javascript, typescript]
    severity: ERROR
```

**検知可能漏れパターン**：

| パターン | 検知可能性 |
|---|:---:|
| P1 AuthorizationType=NONE | – |
| P2 Authorizer 無効化（コード）| ⚠ パターン依存 |
| P3 アプリ 2 段検証なし | ✅ tenant validation ルールで |
| P4 path bypass | ⚠ ハンドラ列挙ルールで部分 |
| P5 JWT 検証バグ | ✅ 確実 |
| P6 ALB + コード素通り | ✅ 認証 middleware ルールで |

**運用注意**：

- **言語別整備の負荷**：Python / Node / Go / Java で別ルールセット必要
- **False positive 多発リスク**：段階導入で warn → error
- **公開レジストリ活用**：`p/owasp-top-ten` / `p/security-audit` プリセット
- **CI 統合**：`returntocorp/semgrep-action` で簡単
- **コスト**：OSS 無料、Pro 版は $20-40 / dev / 月

### §C-6.6.7 L4: Runtime Log（実トラフィック分析）詳細

**主要ツール**：

| ツール | 種別 | 用途 |
|---|---|---|
| **Athena on CloudTrail** | AWS マネージド | API 呼出履歴の長期分析 |
| **Athena on API GW access log** | AWS マネージド | 認証ヘッダ・status の分析 |
| **CloudWatch Logs Insights** | リアルタイム検索 | 直近のクエリ |
| **QuickSight ダッシュボード** | BI | 経営報告 |

**設置場所**：

```
[実トラフィック] → CloudTrail / API GW access log → S3
        ↓
[Athena scheduled query] → 違反検出
        ↓
[EventBridge / SNS] → Slack / Jira
        ↓ (定期)
[QuickSight] → ダッシュボード
```

**Athena クエリ Q1: 未認証通過の検出**：

```sql
SELECT
  request_id,
  request_time,
  http_method,
  resource_path,
  ip_address,
  status,
  authorization_header_present,
  api_key_id
FROM apigw_access_logs
WHERE date_added >= current_date - INTERVAL '1' DAY
  AND resource_path LIKE '/api/%'
  AND (authorization_header_present = false OR authorization_header_present IS NULL)
  AND api_key_id IS NULL
  AND status BETWEEN 200 AND 299
ORDER BY request_time DESC
LIMIT 100;
```

**Athena クエリ Q2: 認証成功率の異常監視**：

```sql
SELECT
  date_trunc('hour', request_time) AS hour,
  api_id,
  resource_path,
  COUNT(*) AS total_requests,
  COUNT(CASE WHEN status IN (401, 403) THEN 1 END) AS auth_failures,
  ROUND(
    CAST(COUNT(CASE WHEN status IN (401, 403) THEN 1 END) AS DOUBLE)
    / COUNT(*) * 100, 2
  ) AS failure_rate_pct
FROM apigw_access_logs
WHERE request_time >= current_timestamp - INTERVAL '24' HOUR
GROUP BY 1, 2, 3
HAVING COUNT(*) > 100
   AND CAST(COUNT(CASE WHEN status IN (401, 403) THEN 1 END) AS DOUBLE) / COUNT(*) > 0.1
ORDER BY failure_rate_pct DESC;
```

**Athena クエリ Q3: tenant 越境疑い検出**：

```sql
SELECT
  request_id,
  request_time,
  jwt_tenant_id,
  requested_tenant_id,
  client_id,
  status,
  ip_address
FROM apigw_access_logs
WHERE date_added >= current_date - INTERVAL '7' DAY
  AND jwt_tenant_id IS NOT NULL
  AND requested_tenant_id IS NOT NULL
  AND jwt_tenant_id != requested_tenant_id
  AND status = 200
ORDER BY request_time DESC;
```

**Athena クエリ Q4: 同一 token の cross-IP 利用検出（漏洩疑い）**：

```sql
SELECT
  client_id,
  COUNT(DISTINCT ip_address) AS distinct_ips,
  array_agg(DISTINCT ip_address) AS ip_list,
  MIN(request_time) AS first_seen,
  MAX(request_time) AS last_seen
FROM apigw_access_logs
WHERE request_time >= current_timestamp - INTERVAL '24' HOUR
  AND client_id IS NOT NULL
GROUP BY client_id
HAVING COUNT(DISTINCT ip_address) > 5
ORDER BY distinct_ips DESC;
```

**必須メタデータフィールド（access log）**：

```json
{
  "requestId": "$context.requestId",
  "userArn": "$context.identity.userArn",
  "apiKeyId": "$context.identity.apiKeyId",
  "client_id": "$context.authorizer.client_id",
  "tenant_id": "$context.authorizer.tenant_id",
  "scope": "$context.authorizer.scope",
  "profile": "partner-silver",
  "authMethod": "P-2 Token Exchange"
}
```

**検知可能漏れパターン**：

| パターン | 検知可能性 |
|---|:---:|
| P1 AuthorizationType=NONE | ✅ Q1 で |
| P2 Authorizer 無効化 | ✅ Q2 で（401 が 0 件 = 異常）|
| P3 tenant 越境 | ✅ Q3 で |
| P4 path bypass | ✅ path 別集計 |
| P5 JWT 検証バグ | ⚠ 異常 token 来訪時のみ |
| P6 ALB | ⚠ 観測のみでは不足 |

**運用注意**：

- **コスト**：Athena $5/TB scan、Partition により絞込必要（date / api_id）
- **スケジュール実行**：AWS Step Functions or EventBridge Scheduler で日次/時次
- **アラート閾値調整**：false positive を減らすため初期は warning のみ
- **長期保存**：90 日 → S3 Glacier、コスト最適化
- **PII マスキング**：CloudWatch Logs Data Protection Policy で IP / email マスク

### §C-6.6.8 L5: Behavioral（能動探査）詳細

**主要ツール**：

| ツール | 種別 | 用途 |
|---|---|---|
| **CloudWatch Synthetics canary** | AWS マネージド | 定期合成監視、軽量 |
| **OWASP ZAP** | OSS | 深掘り pen test |
| **Burp Suite Enterprise** | 商用 | 高度 pen test |
| **Postman / Newman scheduled** | 開発者親和性高 | 定期 API テスト |

**設置場所**：

```
[CloudWatch Synthetics] → 5min interval → 各 endpoint へ probe
        ↓ failure
[EventBridge] → SNS → Slack / PagerDuty
        ↓ 月次
[OWASP ZAP automation] → 深掘り → レポート
```

**Synthetics canary サンプル（Node.js）**：

```javascript
// synthetics-canary-auth-check.js
const synthetics = require('Synthetics');
const log = require('SyntheticsLogger');

const protectedEndpoints = [
  { url: 'https://api.example.com/api/users', expected: [401, 403] },
  { url: 'https://api.example.com/api/orders', expected: [401, 403] },
  { url: 'https://api.example.com/api/admin', expected: [401, 403] },
];

const authCheckCanary = async function () {
  const failures = [];

  for (const endpoint of protectedEndpoints) {
    // Probe 1: 認証ヘッダなし → 401/403 期待
    const noAuthRes = await makeRequest(endpoint.url, {});
    if (!endpoint.expected.includes(noAuthRes.statusCode)) {
      failures.push({
        endpoint: endpoint.url,
        probe: 'no-auth',
        expected: endpoint.expected,
        actual: noAuthRes.statusCode,
        severity: 'CRITICAL'
      });
    }

    // Probe 2: 無効トークン → 401 期待
    const invalidTokenRes = await makeRequest(endpoint.url, {
      'Authorization': 'Bearer eyJhbGciOiJub25lIn0.eyJzdWIiOiJoYWNrZXIifQ.'
    });
    if (invalidTokenRes.statusCode !== 401) {
      failures.push({
        endpoint: endpoint.url,
        probe: 'invalid-token',
        expected: 401,
        actual: invalidTokenRes.statusCode,
        severity: 'CRITICAL'
      });
    }

    // Probe 3: alg=none token → 401 期待（P-5 検証バグ検出）
    const noneAlgRes = await makeRequest(endpoint.url, {
      'Authorization': 'Bearer ' + craftNoneAlgToken()
    });
    if (noneAlgRes.statusCode !== 401) {
      failures.push({
        endpoint: endpoint.url,
        probe: 'none-alg-token',
        expected: 401,
        actual: noneAlgRes.statusCode,
        severity: 'CRITICAL - JWT verification bug suspected'
      });
    }
  }

  if (failures.length > 0) {
    log.error('Auth check failures:', JSON.stringify(failures, null, 2));
    throw new Error(`${failures.length} authentication checks failed`);
  }
  log.info('All authentication checks passed');
};

exports.handler = async () => {
  return await synthetics.executeStep('authCheck', authCheckCanary);
};
```

**tenant 越境 probe サンプル**：

```javascript
async function tenantIsolationProbe() {
  const tenantATokenVar = await synthetics.getSecret('test-tenant-a-token');
  const tenantBResource = '/api/tenants/tenant-b/orders';

  const res = await makeRequest(
    `https://api.example.com${tenantBResource}`,
    { 'Authorization': `Bearer ${tenantATokenVar}` }
  );

  if (res.statusCode === 200) {
    log.error('TENANT BOUNDARY VIOLATION: Tenant A token accessed Tenant B');
    throw new Error('Cross-tenant access allowed - critical violation');
  }
  if (res.statusCode !== 403) {
    log.warn(`Unexpected status ${res.statusCode} for cross-tenant probe`);
  }
}
```

**Direct Origin Attack probe サンプル**（[ADR-039 §C-4](../../../adr/039-centralized-network-account-edge-layer.md) Origin Protection 検証）：

```javascript
// CloudFront を経由しない直接 Origin アクセスが遮断されているかを定期検証
async function directOriginAttackProbe() {
  // CloudFront を経由しない直接 Origin DNS（API GW / Public ALB）
  const directOriginEndpoints = [
    'https://abc123.execute-api.ap-northeast-1.amazonaws.com/prod/api/users',  // API GW direct
    'https://app-b-alb-xxx.ap-northeast-1.elb.amazonaws.com/api/orders',       // Public ALB direct
  ];

  for (const endpoint of directOriginEndpoints) {
    // Probe 1: CloudFront を経由せず直接 curl → 403 期待
    const res = await makeRequest(endpoint, {});
    if (res.statusCode !== 403) {
      log.error(`ORIGIN PROTECTION FAILURE: ${endpoint} returned ${res.statusCode} on direct access`);
      throw new Error(`Direct origin access allowed - critical security violation (ADR-039 violation)`);
    }
  }

  // Probe 2: 古い Secret で X-Origin-Verify 偽装 → 403 期待
  const oldSecret = await synthetics.getSecret('test-old-origin-verify-secret');
  for (const endpoint of directOriginEndpoints) {
    const res = await makeRequest(endpoint, {
      'X-Origin-Verify': oldSecret
    });
    if (res.statusCode !== 403) {
      log.error(`SECRET ROTATION FAILURE: ${endpoint} accepted stale secret`);
      throw new Error(`Stale Origin Protection secret accepted - rotation may have failed`);
    }
  }

  log.info('All Origin Protection probes passed');
}
```

**Probe シナリオまとめ**：

| Probe | 期待 status | 検知パターン |
|---|:---:|---|
| `directOriginAttackProbe` 1: 直接 curl | 403 | Origin Protection 失効 / Resource Policy 削除 |
| `directOriginAttackProbe` 2: 古い Secret | 403 | Secret rotation 失敗 / Overlap 過剰 |
| `authCheckCanary` 1: no-auth | 401/403 | P1 Authorizer 不在 |
| `authCheckCanary` 2: invalid-token | 401 | P2 Authorizer 無効化 |
| `authCheckCanary` 3: alg=none | 401 | P5 JWT 検証バグ |
| `tenantIsolationProbe`: cross-tenant | 403 | P3 tenant 越境 |

#### canary 自動化 Pattern A〜D（API 数増加への対応）

API 数が増えた場合の自動化レベル別 4 Pattern：

| Pattern | アプリチーム作業量 | 新規 API 自動追従 | OpenAPI 要 | 採用シーン |
|---|---|:---:|:---:|---|
| **A. 手書き canary 個別作成** | 大（API ごとに canary）| ❌ 手動更新 | – | 数本の API のみ |
| **B. 設定駆動 canary**（JSON / SSM 設定）| 中（設定ファイル更新）| ❌ 手動更新 | – | 10-50 API |
| **C. OpenAPI ドリブン canary** ⭐ 推奨 | **ほぼゼロ** | ✅ 自動追従 | ✅ 必要 | 全 API、本標準推奨 |
| **D. Resource Explorer 自動発見** | **ゼロ** | ✅ 自動追従 | – | OpenAPI なしレガシー / Org 横断 |

→ **本標準推奨は Pattern C（OpenAPI ドリブン）**。Service Catalog 製品テンプレに同梱し、アプリチームの作り込みゼロを実現（詳細は [§C-API-5 §C-5.1.1](05-self-service-catalog.md) ）。

#### Pattern C: OpenAPI ドリブン canary 詳細

**設計原則**：
- API GW を OpenAPI から構築（Service Catalog 製品テンプレが `AWS::ApiGateway::RestApi.Body` に OpenAPI を展開）
- deploy 後の正本 OpenAPI を Custom Resource Lambda が Shared S3 Registry に export
- 共通 canary Lambda コード（Platform チーム配布）が Registry から OpenAPI を取得して全 endpoint を probe
- アプリチームの作業：OpenAPI を書く + `x-synthetics-skip-auth-check: true` アノテーションのみ

**OpenAPI アノテーション**：

```yaml
paths:
  /api/users:
    get:
      security: [{ bearerAuth: [] }]
      responses: { ... }                  # 認証必須として probe 対象
  /api/orders/{orderId}:
    get:
      security: [{ bearerAuth: [] }]
      parameters:
        - name: orderId
          in: path
          required: true
          schema: { type: string }
      responses: { ... }
  /_/health:
    get:
      x-synthetics-skip-auth-check: true  # ⭐ public endpoint、probe 対象外
      responses: { '200': { ... } }
  /api/discovery:
    get:
      x-synthetics-skip-auth-check: true
      responses: { '200': { ... } }
```

**Service Catalog 製品テンプレ抜粋（CloudFormation）**：

```yaml
Parameters:
  OpenAPIS3Url: { Type: String, Description: "s3://bucket/path/openapi.yaml" }
  AppName: { Type: String }
  Environment: { Type: String, AllowedValues: [dev, stg, prod] }

Resources:
  # (1) API Gateway を OpenAPI から構築
  ApiGateway:
    Type: AWS::ApiGateway::RestApi
    Properties:
      Name: !Sub "${AppName}-${Environment}"
      Body:
        Fn::Transform:
          Name: AWS::Include
          Parameters: { Location: !Ref OpenAPIS3Url }

  # (2) deploy 後 OpenAPI を Shared Registry に export
  OpenApiExporter:
    Type: Custom::OpenApiExport
    Properties:
      ServiceToken: !ImportValue SharedOpenApiExportFunction
      RestApiId: !Ref ApiGateway
      StageName: !Ref Environment
      TargetS3Bucket: !ImportValue SharedOpenApiRegistryBucket
      TargetS3Key: !Sub "${AWS::AccountId}/${ApiGateway}/openapi.yaml"

  # (3) Synthetics canary（共通 Lambda コード参照、5min 周期）
  AuthCheckCanary:
    Type: AWS::Synthetics::Canary
    DependsOn: OpenApiExporter
    Properties:
      Name: !Sub "${AppName}-auth-check"
      ExecutionRoleArn: !GetAtt CanaryRole.Arn
      RuntimeVersion: syn-nodejs-puppeteer-7.0
      Schedule: { Expression: rate(5 minutes) }
      Code:
        Handler: index.handler
        S3Bucket: !ImportValue SharedCanaryBucket
        S3Key: "canary-code/auth-check-v1.zip"  # ⭐ 共通実装
      RunConfig:
        EnvironmentVariables:
          API_BASE_URL: !Sub "https://${ApiGateway}.execute-api.${AWS::Region}.amazonaws.com/${Environment}"
          OPENAPI_S3_URL: !Sub
            - "s3://${Bucket}/${Key}"
            - Bucket: !ImportValue SharedOpenApiRegistryBucket
              Key: !Sub "${AWS::AccountId}/${ApiGateway}/openapi.yaml"

  # (4) Alarm（違反時 Slack 通知）
  AuthCheckAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      Namespace: CloudWatchSynthetics
      MetricName: SuccessPercent
      Dimensions: [{ Name: CanaryName, Value: !Ref AuthCheckCanary }]
      Statistic: Average
      Period: 300
      Threshold: 100
      ComparisonOperator: LessThanThreshold
      AlarmActions: [!ImportValue SharedSecuritySlackTopicArn]
```

**共通 canary Lambda 実装（Platform 配布）**：

```javascript
// canary-code/auth-check-v1.zip 内 index.js
const synthetics = require('Synthetics');
const log = require('SyntheticsLogger');
const yaml = require('js-yaml');
const AWS = require('aws-sdk');
const s3 = new AWS.S3();

const authCheckCanary = async () => {
  const apiBaseUrl = process.env.API_BASE_URL;
  const openapiUrl = process.env.OPENAPI_S3_URL;

  // OpenAPI Registry から取得
  const [_, bucket, ...keyParts] = openapiUrl.replace('s3://', '').split('/');
  const key = keyParts.join('/');
  const obj = await s3.getObject({ Bucket: bucket, Key: key }).promise();
  const spec = yaml.load(obj.Body.toString());

  const failures = [];
  let totalProbes = 0;

  for (const [path, methods] of Object.entries(spec.paths)) {
    for (const [method, operation] of Object.entries(methods)) {
      if (operation['x-synthetics-skip-auth-check']) continue;
      if (['options', 'parameters'].includes(method)) continue;

      // path parameter を dummy 値で置換
      const probeUrl = apiBaseUrl + path.replace(/{[^}]+}/g, 'probe-test-id');
      totalProbes++;

      const res = await synthetics.executeHttpStep(`${method}-${path}`, {
        url: probeUrl,
        method: method.toUpperCase(),
        headers: { 'Content-Type': 'application/json' },
        body: method === 'get' ? null : '{}'
      });

      if (![401, 403].includes(res.statusCode)) {
        failures.push({ path, method, expected: '401 or 403', actual: res.statusCode });
      }
    }
  }

  if (failures.length > 0) {
    log.error(`AUTH CHECK FAILURES (${failures.length}/${totalProbes}):`,
              JSON.stringify(failures, null, 2));
    throw new Error(`${failures.length} unauthenticated endpoints accept requests`);
  }
  log.info(`All ${totalProbes} endpoints properly require auth`);
};

exports.handler = async () => {
  return await synthetics.executeStep('authCheck', authCheckCanary);
};
```

**Pattern C 採用時の責務分担**：

| 主体 | やること | 工数 |
|---|---|:---:|
| **アプリチーム** | OpenAPI を書く（API 開発の通常業務）+ public endpoint にアノテーション + S3 アップ + Service Catalog 起動 | 数分 |
| **Platform チーム（初回のみ）** | 共通 canary Lambda 実装 + Shared S3 配布 + Service Catalog 製品テンプレ作成 + OpenAPI Export Custom Resource 実装 | 1-2 週間 |
| **Platform チーム（運用）** | canary バージョン更新時 → Shared S3 の zip 差し替え（既存 canary 自動追従）| 必要時 |

→ **canary コード保守は完全に Platform チーム集約**、アプリ数 N に対して 1 つの実装で済む。アプリ追加時のスケーラビリティ確保。

**OpenAPI を持たないレガシー API への対応（Pattern D 補完）**：

別製品 `api-gateway-legacy-public` で Resource Explorer / API GW `getResources` API を使った自動発見を実装。OpenAPI なしでも Account 単位で全 endpoint を probe 対象化可能。

**Probe 対象の制御性比較**：

| 観点 | Pattern A 手書き | Pattern B 設定駆動 | Pattern C OpenAPI | Pattern D 自動発見 |
|---|:---:|:---:|:---:|:---:|
| 新規 endpoint の追加忘れ | ⚠ 起きる | ⚠ 起きる | ✅ 起きない | ✅ 起きない |
| public endpoint の除外 | 直接コード編集 | 設定編集 | ✅ アノテーション | ⚠ tag / 別 list |
| 偽 probe（負荷大）の防止 | ✅ 完全制御 | ✅ 制御 | ⚠ アノテーション依存 | ⚠ 自動発見の精度依存 |
| アプリ独立性 | ✅ | ✅ | ✅ | ⚠ 共有発見プロセスに依存 |

#### Hybrid 検証（Negative + Positive 併用）⭐

**問題提起**：Negative test だけだと「認証が無いから 401」と「テスト構成ミス（path 誤り等で 404 / token 失効で 401）」を区別できない。**Positive test を併用し、4×4 真偽値表で failure を分類する**ことで初めて検知の正確性が担保される。

##### 4×4 真偽値表（Negative × Positive status 組合せ判定）

| Negative status | Positive status | 解釈 | 緊急度 |
|:---:|:---:|---|:---:|
| **401/403** | **200/201/204** | ✅ **正常**：認証が機能、API も稼働 | – |
| 401/403 | 401/403 | ⚠ **テスト token が無効 or 失効** | 中（テスト構成）|
| 401/403 | 404 | ⚠ **endpoint 不在 or path 誤り** | 中（テスト構成）|
| 401/403 | 500 | ⚠ **Backend バグ**、認証は OK | 中（別問題）|
| **200** | **200** | ❌❌ **認証が完全 missing** | 🔥 P1 即時 |
| **200** | 401/403 | ❌ **認証ロジックが逆 / 誤動作** | 🔥 P1 |
| 404 | 404 | ⚠ **endpoint 不在** or canary 構成ミス | 中（見直し）|
| 404 | 200 | ⚠ **path parameter 解決ミス** | 中（見直し）|
| 500 | 500 | ⚠ **API or Authorizer 常時エラー** | 中 |
| 401/403 | 403 | ⚠ **token scope 不足**（認証 OK 認可 NG）| 中（見直し）|

→ **「Negative=401/403 + Positive=200」のペアが揃って初めて「認証が正しく実装されている」と断言できる**。

##### Hybrid canary 実装（Failure 分類ロジック含む）

```javascript
// hybrid-auth-canary.zip 内 index.js
const synthetics = require('Synthetics');
const log = require('SyntheticsLogger');
const yaml = require('js-yaml');
const AWS = require('aws-sdk');
const s3 = new AWS.S3();
const sm = new AWS.SecretsManager();

const hybridCanary = async () => {
  const apiBaseUrl = process.env.API_BASE_URL;
  const openapiUrl = process.env.OPENAPI_S3_URL;
  const env = process.env.ENVIRONMENT;  // prod / stg / dev

  // ── ① Smoke test：canary 基盤健全性確認 ──
  await smokeTest();

  const spec = await fetchOpenApi(openapiUrl);
  const tokenCache = {};
  const results = { passed: [], failed: [], skipped: [] };

  for (const [path, methods] of Object.entries(spec.paths)) {
    for (const [method, op] of Object.entries(methods)) {
      if (['parameters', 'options'].includes(method)) continue;

      const probeUrl = apiBaseUrl + resolvePath(path, op['x-canary-path-params']);

      // ── ② Negative test ──
      let negStatus = null;
      if (!op['x-synthetics-skip-auth-check']) {
        const negRes = await sendRequest(probeUrl, method, {}, null);
        negStatus = negRes.statusCode;
      }

      // ── ③ Positive test ──
      let posStatus = null;
      const posMode = op['x-canary-positive-test'];
      const runPositive = posMode === true ||
                          (posMode === 'pre-prod-only' && env !== 'prod');

      if (runPositive) {
        const tokenSecret = op['x-canary-test-token-secret'] || 'canary-default-token';
        if (!tokenCache[tokenSecret]) {
          tokenCache[tokenSecret] = await fetchToken(tokenSecret);
        }
        const headers = { 'Authorization': `Bearer ${tokenCache[tokenSecret]}` };
        const body = op.requestBody?.content?.['application/json']?.example;
        const posRes = await sendRequest(probeUrl, method, headers,
                                          body ? JSON.stringify(body) : null);
        posStatus = posRes.statusCode;

        // cleanup（副作用ある method）
        if (op['x-canary-cleanup'] && posStatus < 300) {
          await runCleanup(op['x-canary-cleanup'], posRes, headers);
        }
      }

      // ── ④ 4×4 真偽値表に基づく判定 ──
      const verdict = classifyResult(negStatus, posStatus, op);
      if (verdict.severity === 'OK') {
        results.passed.push({ path, method });
      } else {
        results.failed.push({
          path, method, negStatus, posStatus,
          ...verdict
        });
      }
    }
  }

  if (results.failed.filter(f => f.severity === 'CRITICAL').length > 0) {
    log.error('CRITICAL FAILURES:', JSON.stringify(results.failed));
    throw new Error(`${results.failed.length} probe failures (CRITICAL present)`);
  }
  log.info(`Passed: ${results.passed.length}, Failed: ${results.failed.length}`);
};

// 4×4 真偽値表ロジック
function classifyResult(neg, pos, op) {
  // Negative=200 → 認証完全 missing（最重大）
  if (neg === 200) {
    return { severity: 'CRITICAL', reason: 'Auth missing or bypassed', alertTo: 'security-oncall' };
  }
  // Positive 未実行：negative のみ判定
  if (pos === null) {
    if ([401, 403].includes(neg)) return { severity: 'OK' };
    return { severity: 'WARN', reason: `Unexpected negative status ${neg}`, alertTo: 'app-team' };
  }
  // 両方判定
  if ([401, 403].includes(neg) && [200, 201, 204].includes(pos)) return { severity: 'OK' };
  if ([401, 403].includes(neg) && [401, 403].includes(pos))
    return { severity: 'WARN', reason: 'Test token invalid or expired', alertTo: 'platform-team' };
  if ([401, 403].includes(neg) && pos === 404)
    return { severity: 'WARN', reason: 'Endpoint not found, canary config issue', alertTo: 'platform-team' };
  if ([401, 403].includes(neg) && pos >= 500)
    return { severity: 'INFO', reason: 'Backend issue (auth OK)', alertTo: 'app-team' };
  if (neg === pos && [404, 500].includes(neg))
    return { severity: 'WARN', reason: 'Same error in both (config issue?)', alertTo: 'platform-team' };
  return { severity: 'INVESTIGATE', reason: `Unusual ${neg}/${pos} combination`, alertTo: 'security-oncall' };
}

exports.handler = async () => {
  return await synthetics.executeStep('hybridAuth', hybridCanary);
};
```

##### Smoke test（canary 基盤健全性確認）

canary の冒頭で **既知の挙動**を確認し、テスト基盤自体の健全性を担保：

```javascript
async function smokeTest() {
  // 1. 既知の health endpoint に valid token で呼出 → 200 必須
  const healthRes = await fetchWithDefaultToken('/health-with-auth');
  if (healthRes.statusCode !== 200) {
    throw new Error(`SMOKE FAIL: cannot reach health endpoint or token broken (status ${healthRes.statusCode})`);
  }

  // 2. 既知の admin-only endpoint に readonly token で呼出 → 403 必須
  const deniedRes = await fetchWithDefaultToken('/admin/canary-test-denied');
  if (deniedRes.statusCode !== 403) {
    throw new Error(`SMOKE FAIL: token may have unexpected scope (status ${deniedRes.statusCode})`);
  }

  log.info('Smoke test passed - canary infrastructure healthy');
}
```

→ Smoke test 失敗時は **「認証実装漏れ」ではなく「テスト基盤問題」と分離してアラート**、誤った P1 通知を防止。

##### 副作用ある method（POST/PUT/DELETE）の戦略

| 戦略 | 内容 | production で使えるか |
|---|---|:---:|
| **A. Read-only positive（GET のみ）**| production canary は GET のみ positive、POST 等は negative のみ | ✅ 安全 |
| **B. 環境分離**：pre-prod で full positive | staging / dev で full coverage、production は read-only | ✅ |
| **C. Probe + Cleanup**：POST 後すぐ DELETE | tag で identification、後処理で削除 | ⚠ 慎重に |
| **D. Idempotency-key + dummy tenant** | `canary-probe` 専用テナント、全データ probe-only | ✅ おすすめ |

**推奨：A + D の組合せ**。OpenAPI に `x-canary-positive-test: pre-prod-only` を付けることで production 環境では positive をスキップ、pre-prod でフル検証。

##### テスト用 token 管理

| 要素 | 内容 |
|---|---|
| **Test client 作成**（共有認証基盤）| `canary-readonly-client` / `canary-write-client` 等を最小権限で発行 |
| **Test tenant 準備**（multi-tenant 時）| `canary-probe-tenant`、production テナントと完全分離 |
| **Token Secrets Manager 保管** | CMK 暗号化、Lambda が取得 |
| **Token 自動ローテ** | Secrets Manager Rotation Lambda、共有認証基盤の M2M Client を 30 日周期で更新 |
| **Token scope 設計** | endpoint 別に必要 scope を最小化、smoke test で過剰 scope を検出 |
| **Token 監査ログ** | canary 発の token 利用を別 client_id で識別、production リクエストと区別 |

##### Failure 分類別 アラート振り分け

```mermaid
flowchart TD
    Fail[canary failure]
    Fail --> Class{4×4 真偽値表<br/>分類}

    Class -->|CRITICAL<br/>Auth missing| Sec[Security オンコール<br/>+ アプリチーム<br/>P1 即時]
    Class -->|CRITICAL<br/>Auth reversed| Sec
    Class -->|WARN<br/>Token issue| Platform[Platform チーム<br/>P2 24h]
    Class -->|WARN<br/>Endpoint config| Platform
    Class -->|INFO<br/>Backend issue| App[アプリチーム<br/>P3 通常]
    Class -->|INVESTIGATE| Sec

    style Sec fill:#ffcdd2
    style Platform fill:#fff9c4
    style App fill:#c8e6c9
```

→ **「認証漏れ」「テスト構成ミス」「Backend バグ」を分離発火**することで、誤った P1 通知を防ぎ運用負担を軽減。

##### 環境別 probe 動作まとめ

| 環境 | Negative | Positive (GET) | Positive (POST/PUT/DELETE) | Smoke test |
|---|:---:|:---:|:---:|:---:|
| **Production** | ✅ 全 endpoint | ✅ 全 GET | ❌ skip | ✅ 冒頭 |
| **Staging / Dev** | ✅ 全 endpoint | ✅ 全 GET | ✅ probe + cleanup | ✅ 冒頭 |

**OWASP ZAP 自動化サンプル**：

```yaml
env:
  contexts:
    - name: api-test
      urls:
        - https://api-test.example.com/api/
      includePaths:
        - https://api-test.example.com/api/.*
      authentication:
        method: oauth2
        parameters:
          tokenEndpoint: https://auth.example.com/oauth2/token
          clientId: ${ZAP_CLIENT_ID}
          clientSecret: ${ZAP_CLIENT_SECRET}
jobs:
  - type: spider
    parameters:
      maxDuration: 5
  - type: activeScan
    parameters:
      maxDuration: 30
  - type: report
    parameters:
      template: traditional-html
      reportFile: zap-report.html
```

**検知可能漏れパターン**：

| パターン | 検知可能性 |
|---|:---:|
| P1 AuthorizationType=NONE | ✅ 確実（probe で 200 返る）|
| P2 Authorizer 無効化 | ✅ 確実（無効 token で 200 返る）|
| P3 tenant 越境 | ✅ 専用 probe で |
| P4 path bypass | ✅ 全 endpoint enum で |
| P5 JWT 検証バグ | ✅ alg=none / 期限切れ probe で |
| P6 ALB + コード素通り | ✅ 確実 |

**運用注意**：

- **コスト**：Synthetics $0.0012/run × 5min interval × 30 days ≈ $10/月/canary
- **production 直接探査の影響**：read-only probe に限定、write は test env で
- **endpoint enumeration**：OpenAPI spec から自動生成 or Resource Explorer
- **alert 頻度**：critical のみ即時、warning はバッチ
- **stage 別実行**：production / staging で probe 内容を変える

### §C-6.6.9 統合パイプラインと総合コスト

**統合パイプライン**：

```mermaid
flowchart TB
    subgraph Pre["Pre-Deploy 段階"]
        Git[Git push]
        Pre1[L1 cfn-guard]
        Pre3[L3 Semgrep]
        Git --> Pre1
        Git --> Pre3
    end

    subgraph Deploy["Deploy 段階"]
        SC[Service Catalog<br/>強制テンプレ]
        Pre1 -->|Pass| SC
        Pre3 -->|Pass| SC
    end

    subgraph Post["Post-Deploy 継続"]
        L2[L2 Config Rules<br/>常時]
        L4[L4 Athena<br/>日次バッチ]
        L5[L5 Synthetics<br/>5min 周期]
        SC --> L2
        SC --> L4
        SC --> L5
    end

    subgraph Alert["アラート"]
        EB[EventBridge]
        Slack
        Jira
        L2 -->|NON_COMPLIANT| EB
        L4 -->|anomaly| EB
        L5 -->|test fail| EB
        EB --> Slack
        EB --> Jira
    end

    style Pre fill:#e8f5e9
    style Deploy fill:#fff9c4
    style Post fill:#fff3e0
    style Alert fill:#ffcdd2
```

**総合コスト想定（10 アプリ規模）**：

| Layer | 月額コスト目安 |
|---|---|
| L1 cfn-guard / cdk-nag | $0（OSS）|
| L2 Config Rules | $50-200 |
| L3 Semgrep OSS | $0 / Pro $20-40/dev |
| L4 Athena | $100-500（log volume 次第）|
| L5 Synthetics canary | $50-200 |
| **合計** | **$200-1000 / 月** |

→ アプリ 10 個規模なら **月 $500（約 ¥75,000）程度**。担保率 95-99% を考えれば妥当な投資。

### §C-6.6.10 担保率の率直評価

各 Layer 構成での総合担保率：

| 構成 | 総合担保率 | 評価 |
|---|:---:|---|
| L1 IaC のみ | ~40% | ❌ 不足 |
| L1 + L2 Config | ~50% | ❌ 不足 |
| L1+L2+L3 Static | ~85% | ⚠ ALB の P2 残る |
| L1+L2+L3+L4 Log | ~90% | ⚠ P3 未経験 path 残る |
| **L1+L2+L3+L5 Behavioral** | **~95%** | **✅ 実用的に十分** |
| **5 Layer 全部** | **~99%** | **✅ ほぼ完全** |

→ **L1+L2+L3+L5（4 層）で 95%+**、5 Layer 全部で **99%**。

### §C-6.6.11 顧客説明用：本設計の意義

| 観点 | メッセージ |
|---|---|
| **多層防御の体系化** | 「認証ありますか」「検知してます」だけでなく、漏れの種類を 6 パターンに分類し、検知を 5 Layer で体系化 |
| **実証可能なガバナンス** | 各 Layer の検知実績は監査人に提示可能（CloudTrail / Athena / Config / Synthetics ログ）|
| **業界標準性** | OWASP API Security Top 10 / CIS Benchmark / PCI DSS Req 6 / 11 と整合 |
| **率直なリスク開示** | 「100% にはならない」を明示、残り 1-5% のリスクを顧客に正しく提示 |

### §C-6.6.12 TBD / 要確認

- Q: 6 パターンの **追加 / 統廃合**（業務固有の漏れパターンあれば）→ `API-D-275`
- Q: 担保率の **目標値設定**（95% / 99% / 99.5%）→ `API-D-276`
- Q: L3 Semgrep ルールセットの **言語別整備優先順位** → `API-D-2761`
- Q: L5 Synthetics canary の **探査頻度**（5min / 15min / 1h）→ `API-C-2762`
- Q: L2 Config Rule **自動修復採用範囲**（通知のみ / 自動修復）→ `API-D-2763`
- Q: 外部 pen test（年 1 回） **ベンダー選定**と予算 → `API-D-2764`

---

## §C-6.7 AWS リソース別 検知可能性マトリクス

**このサブセクションで定めること**：各 AWS リソース種別で認証実装漏れがどこまで検知可能かを精密化する。
**主な判断軸**：IaC / Config レベルで 100% 検知可能なものは Service Catalog 強制、不可能なものは Static Code / Behavioral で補完。
**§C-6 全体との関係**：§C-6.6 検知マトリクスの AWS リソース別細分化。

### §C-6.7.1 ベースライン：リソース別検知可能性

| リソース | "認証あり" 判定基準 | L1 IaC 検知 | L2 Config Rule | 確度 |
|---|---|---|---|:---:|
| **API GW REST Method** | `AuthorizationType != NONE` | cfn-guard 明確 | `api-gw-method-authorizer-required` ✅ AWS マネージド | ✅ 100% |
| **API GW HTTP Route** | Authorizer 紐付け | cfn-guard 明確 | `api-gwv2-authorization-type-configured` ✅ | ✅ 100% |
| **Lambda Function URL** | `AuthType=AWS_IAM` | cfn-guard 明確 | `lambda-function-url-auth` ✅ | ✅ 100% |
| **AppSync** | `AuthenticationType` 設定 | cfn-guard | `appsync-authorization-check` ✅ | ✅ 100% |
| **ALB Listener** | `authenticate-oidc` / `authenticate-cognito` action 存在 | cfn-guard | カスタム Config Rule 必要 | ⚠ 80%（app code 認証は L2 不可）|
| **VPC Lattice Service** | Auth Policy attached | cfn-guard | カスタム Config Rule | ✅ 95% |
| **CloudFront** | OAC / OAI / signed cookie / signed URL | cfn-guard | カスタム Config Rule | ⚠ 70%（オリジン側判定）|
| **NLB → ECS** | 認証は app 内のみ | – | – | ❌ L1/L2 不可 |
| **EC2 直接公開** | アプリ内のみ | – | – | ❌ L1/L2 不可 |

### §C-6.7.2 判定：4 カテゴリへの分類

リソース種別ごとに、検知の容易さで 4 カテゴリに分類：

| カテゴリ | リソース | 戦略 |
|---|---|---|
| **Cat-A: L1/L2 で 100% 検知可** | API GW REST / HTTP, Lambda URL, AppSync, VPC Lattice | Service Catalog テンプレで Authorizer 必須化、Config Rule で継続監査 |
| **Cat-B: L1/L2 で部分検知可** | ALB（OIDC action）, CloudFront | カスタム Config Rule 整備、+ L3/L5 で補完 |
| **Cat-C: L1/L2 不可、L3/L5 で補完** | ALB（app code 認証）, NLB → ECS | Semgrep ルール + Synthetics canary 必須 |
| **Cat-D: 原則 deploy 禁止** | EC2 直接公開 | SCP / Service Catalog で禁止、例外承認制 |

### §C-6.7.3 顧客説明用：本マトリクスの活用

| 質問 | 回答 |
|---|---|
| **「API Gateway 利用前提か」** | Cat-A 100% 検知可能リソースを優先採用、ALB/ECS 利用時は Cat-B/C で補完 |
| **「ALB はどう守るか」** | authenticate-oidc 必須化（Cat-B）、無理なら Semgrep + Synthetics（Cat-C）の二段構え |
| **「全アプリで同じガバナンスが効くか」** | リソース選択時にカテゴリが決まり、Service Catalog 製品ラインナップで自動誘導 |

### §C-6.7.4 TBD / 要確認

- Q: **Cat-D（EC2 直接公開）の禁止化** を SCP で実装するか → `API-D-277`
- Q: ALB のカスタム Config Rule **実装範囲**（authenticate-oidc 必須化のみ / アプリタグ確認まで）→ `API-B-278`

---

## §C-6.8 ALB / app-code 認証のグレーゾーン対策

**このサブセクションで定めること**：ALB + アプリ内 JWT 検証パターンの認証漏れリスクとその対策。
**主な判断軸**：IaC / Config では検知できないアプリコード認証を、3 アプローチで実効的に担保する。
**§C-6 全体との関係**：§C-6.7 Cat-B/C への詳細対策。

### §C-6.8.1 ベースライン：3 アプローチ

| アプローチ | 内容 | 効果 | 限界 |
|---|---|---|---|
| **A. 認証 middleware 必須化（Static Code）** | Semgrep で middleware 未適用ハンドラを検出 | ✅ Pre-deploy 強制 | アプリ言語 / フレームワーク別ルール整備が必要、bypass 構文検出困難 |
| **B. ALB 認証 action 必須化（Config）** | ALB authenticate-oidc を必須化、アプリコード認証廃止 | ✅ L1+L2 で 100% 担保、業界標準 | カスタム token 検証不可（Cognito 限定）、既存 ECS は改修必要 |
| **C. Behavioral 監視（Synthetics）** | 定期的に未認証 probe を全 endpoint に送信 | ✅ 実装方式非依存、実証 | Pre-deploy 不可、production 直接探査、全 path enum 必要 |

### §C-6.8.2 推奨組合せ

| 構成パターン | 推奨アプローチ |
|---|---|
| **新規アプリ（Service Catalog 経由）** | **B**（ALB authenticate-oidc 必須化）+ Service Catalog 強制 |
| **既存 ECS / ALB アプリ** | **A**（Semgrep middleware 必須化）+ **C**（Synthetics 監視）の併用 |
| **全公開エンドポイント共通** | **C**（Synthetics）を運用フェーズで継続実施 |

→ B が採れる場合は L1+L2 で 100%、無理な場合は A + C で **95%+**。

### §C-6.8.3 Semgrep ルール例（FastAPI 想定）

```yaml
# pseudo Semgrep rule
rules:
  - id: missing-auth-middleware
    pattern: |
      app = FastAPI(...)
      ...
    pattern-not: |
      app.add_middleware(AuthMiddleware, ...)
    message: "FastAPI app missing AuthMiddleware"
    severity: ERROR
```

言語 / フレームワーク別に同等のルールを整備：

| 言語 / FW | パターン |
|---|---|
| Python / FastAPI | `app.add_middleware(AuthMiddleware, ...)` 必須 |
| Python / Flask | `@auth_required` デコレータ必須 |
| Node.js / Express | `app.use(authMiddleware)` 必須 |
| Java / Spring | `@PreAuthorize` / `SecurityConfig` 必須 |
| Go | `auth.Middleware()` 必須 |

### §C-6.8.4 Synthetics canary 設計

```
[CloudWatch Synthetics canary - 5 分毎]
  → 各 endpoint enumerate（OpenAPI spec / Discovery）
  → 未認証 / 不正 token / 期限切れ token / scope 不足 token の 4 パターン送信
  → 期待 status：401 / 403
  → 期待外（200 / 5xx）→ アラート → 自動 Slack 通知 + Jira issue 作成
```

### §C-6.8.5 TBD / 要確認

- Q: **ALB authenticate-oidc 必須化** の例外承認プロセス（カスタム token 検証ケース）→ `API-B-279`
- Q: Semgrep ルールの **言語別整備優先順位** → `API-D-280`
- Q: Synthetics 探査頻度（**5 分 / 15 分 / 1 時間**）とコスト → `API-C-281`

---

## §C-6.9 推奨検知ツールスタック

**このサブセクションで定めること**：5 Layer 検知を実現する具体的なツール選定と組合せ。
**主な判断軸**：AWS native 優先、業界標準、OSS / 商用混在許容。
**§C-6 全体との関係**：§C-6.6 / §C-6.7 / §C-6.8 の実装手段。

### §C-6.9.1 ベースライン：標準スタック

| Layer | 第一推奨ツール | 採用理由 | コスト感 |
|---|---|---|---|
| **L1 IaC** | **cfn-guard**（AWS native）+ **cdk-nag**（CDK 採用時）| AWS 公式 + 標準対応 | 無料（OSS）|
| **L2 Config** | **AWS Config Rules + Custom Lambda Rules** | §FR-API-7 §7.2.2 で既標準化 | Config 評価コスト |
| **L3 Static Code** | **Semgrep**（OSS + Pro 両方）| 多言語対応、CI 統合容易 | 無料（OSS）/ Pro 有償 |
| **L4 Runtime Log** | **Athena on CloudTrail + access log** | §FR-API-8 §8.1.2 で既標準化 | Athena scan コスト |
| **L5 Behavioral** | **CloudWatch Synthetics canary**（軽量）+ **OWASP ZAP**（深掘り）| AWS native + 業界標準 | Synthetics 実行コスト |

### §C-6.9.2 補完ツール（オプション）

| 用途 | ツール |
|---|---|
| マルチクラウド IaC | Checkov / Terrascan / KICS |
| CodeQL 深掘り | GitHub Advanced Security |
| API 仕様検証 | Spectral（OpenAPI lint）|
| Pen test 自動化 | Burp Suite Enterprise / Detectify |
| 商用 Posture | Wiz / Orca / Prisma Cloud |

### §C-6.9.3 統合パイプライン

```mermaid
flowchart LR
    subgraph PreDeploy["Pre-Deploy"]
        Git[Git push]
        CI[CI/CD pipeline]
        L1["L1: cfn-guard / cdk-nag"]
        L3["L3: Semgrep"]
        Git --> CI --> L1
        CI --> L3
    end

    subgraph Deploy["Deploy"]
        SC["Service Catalog<br/>強制テンプレ"]
        L1 -->|"OK"| SC
        L3 -->|"OK"| SC
    end

    subgraph PostDeploy["Post-Deploy（運用）"]
        L2["L2: Config Rules"]
        L4["L4: Athena"]
        L5["L5: Synthetics"]
        Alert["EventBridge → Slack / Jira"]

        SC -->|"deploy"| L2
        SC -->|"deploy"| L4
        SC -->|"deploy"| L5
        L2 -->|"violation"| Alert
        L4 -->|"anomaly"| Alert
        L5 -->|"401/403 missing"| Alert
    end

    style PreDeploy fill:#e8f5e9
    style Deploy fill:#fff9c4
    style PostDeploy fill:#fff3e0
```

### §C-6.9.4 顧客説明用：本スタックの根拠

| 質問 | 回答 |
|---|---|
| **「AWS native か」** | L1 / L2 / L4 / L5 はすべて AWS native、L3 のみ OSS Semgrep |
| **「商用ツール必須か」** | 基本不要、規模拡大時に Wiz / Burp Enterprise 追加検討 |
| **「監査人に提示可能か」** | 全 Layer のログ・違反履歴を CloudTrail / Athena に集約、PCI DSS / APPI 監査対応可能 |

### §C-6.9.5 TBD / 要確認

- Q: Semgrep **Pro / Enterprise 採用可否**（OSS 版で十分か）→ `API-C-282`
- Q: 商用 Posture ツール（Wiz / Orca）採用検討の **規模閾値** → `API-D-283`

---

## §C-6.10 分散化への OK 条件（C1〜C10）

**このサブセクションで定めること**：「アプリに認証を寄せる」を技術的に解禁するためのチェックリスト。
**主な判断軸**：5 Layer 検知 + 運用プロセスの双方を満たした時点で分散化解禁。
**§C-6 全体との関係**：本章全体の運用ゲート。

### §C-6.10.1 ベースライン：10 条件

| # | 条件 | 必須/推奨 |
|---|---|:---:|
| **C1** | L1 IaC 検知（cfn-guard / cdk-nag）が CI で強制 | 必須 |
| **C2** | L2 Config Rule が全 account / region で有効化 | 必須 |
| **C3** | L3 Semgrep ルールセットが整備され CI 統合 | 必須 |
| **C4** | L4 Athena クエリが定期実行 + ダッシュボード | 推奨 |
| **C5** | L5 Synthetics canary が全 endpoint で稼働 | 必須 |
| **C6** | ALB を採用する場合、authenticate-oidc を Service Catalog で強制 or 例外承認制 | 必須 |
| **C7** | 違反検知時の自動アラート + Slack 通知 | 必須 |
| **C8** | 違反検知時の対応 SLA（24h 以内に修正 or 一時的 deny）| 必須 |
| **C9** | Service Catalog 外の deploy を SCP / Permissions Boundary で禁止 | 推奨 |
| **C10** | 違反検知 PoC（DET-1〜DET-6）の実証完了 | 必須（着手前）|

### §C-6.10.2 判定プロセス

```mermaid
flowchart TD
    Start([アプリ自律化の意思決定])
    Check{C1-C10 全部 満たすか}
    Start --> Check
    Check -->|Yes| Distribute["✅ アプリ自律化 解禁<br/>4 領域モデル運用開始"]
    Check -->|No| Central["⚠ 中央集約継続<br/>条件未充足の領域を集中化"]
    Central -->|"条件整備"| Check

    style Distribute fill:#c8e6c9
    style Central fill:#ffe0b2
```

### §C-6.10.3 顧客説明用：本条件の意義

| 観点 | メッセージ |
|---|---|
| **意思決定の透明性** | 「いつ分散化するか」「何を満たせば良いか」を明示、説明責任を果たす |
| **段階的解禁** | C1-C10 を満たさない領域は中央集約を継続、技術整備に応じて段階解禁 |
| **継続評価** | 解禁後も C1-C10 の維持を継続評価、満たさなくなれば再集約 |

### §C-6.10.4 TBD / 要確認

- Q: 各条件の **達成判定基準**（pass rate / 検知率 / カバレッジ）→ `API-D-284`
- Q: 条件未充足時の **既定動作**（中央集約継続 / 部分解禁）→ `API-B-285`

---

## §C-6.11 留保事項とリスク

**このサブセクションで定めること**：5 Layer 検知でも残るリスクを率直に開示。
**主な判断軸**：楽観評価を避け、顧客 / 監査人に正確な情報を提示。
**§C-6 全体との関係**：本章全体の前提条件としての残余リスク明示。

### §C-6.11.1 残余リスク 5 項

| 留保 | 内容 | 対処 |
|---|---|---|
| **R1** | 5 Layer 検知も適切運用が前提。canary 放置 / アラート無視 / SLA 不遵守は担保率を急落させる | 運用 KPI 設定（アラート対応率 / SLA 遵守率）|
| **R2** | Semgrep ルールは「想定済の漏れ」だけ検知、未知の bypass / 新フレームワーク / 設計バグは検出不能 | ルール継続更新 + 外部 pen test 年 1 回 |
| **R3** | 検知から修正までの時間差（post-deploy 検知は数時間〜数日 production 脆弱）| SLA 24h 以内 + 自動 deny / rollback 機構 |
| **R4** | 偽陰性のコスト：「5 Layer 通過 = 安全」と過信すると隙間が攻撃面化 | 多層防御 + Defense-in-depth の継続教育 |
| **R5** | 中央集約モデルの「漏れの起こりにくさ」は捨てられない（既定 ON の安全性）| 重要 endpoint は中央モデル併用検討 |

### §C-6.11.2 「100% は技術だけでは到達不可能」の明示

```
中央集約モデル：構造的に 99-100%（既定 ON、漏れが起きない）
分散モデル+5 Layer：運用次第で 95-99%（運用品質が担保率に直結）
分散モデルのみ：~60-80%（人的ミスが漏れる）
```

→ **分散の自律性メリットと中央の安全マージンのトレードオフ**。本標準は「**自律性メリット > 安全マージン差**」と判断するが、これは経営判断であり継続再評価対象。

### §C-6.11.3 顧客説明用：率直な開示

| 質問 | 回答 |
|---|---|
| **「100% 安全と言えるか」** | 「技術的に 99% まで担保、運用 KPI 継続評価、外部 pen test 年 1 回。100% を主張するベンダーは信用してはいけない」 |
| **「中央集約より安全か」** | 「集約は構造的安全性、分散は自律性。本標準は自律性メリットを優先、検知 5 Layer で集約との差を 1-5% まで縮小」 |
| **「インシデント時の対応は」** | 「24h 以内に修正 or 一時的 deny、root cause 分析、再発防止策反映を SLA 化」 |

### §C-6.11.4 TBD / 要確認

- Q: 残余リスクの **顧客 SLA への明記方法** → `API-D-286`
- Q: 外部 pen test の **頻度 / 範囲 / ベンダー選定** → `API-B-287`

---

## §C-6.12 ロードマップと PoC 計画

**このサブセクションで定めること**：本章のモデルを段階実装する PoC 計画。
**主な判断軸**：早期検証 + 段階的解禁。
**§C-6 全体との関係**：本章の実装着地点。

### §C-6.12.1 PoC フェーズ（DET-1〜DET-6）

| Phase | Layer | 検証内容 | 工数 |
|---|---|---|---|
| **PoC-DET-1** | L1 | cfn-guard ルール 5 本書く + 違反 deploy 弾く実証 | 2-3 日 |
| **PoC-DET-2** | L2 | Config Rule 5 本（既標準）+ EventBridge 通知 + 自動修復 1 本 | 1 週間 |
| **PoC-DET-3** | L3 | Semgrep ルール 10 本書く（Python / Node.js / Go）+ CI 統合 | 1 週間 |
| **PoC-DET-4** | L4 | Athena 標準クエリ 3 本（既標準）+ ダッシュボード | 3 日 |
| **PoC-DET-5** | L5 | Synthetics canary で各 endpoint 未認証 probe + アラート | 1 週間 |
| **PoC-DET-6** | 統合 | 5 Layer 違反シナリオ 6 種を deploy → 5 Layer 全部で検知できることを実証 | 1 週間 |

→ **全 6 PoC で約 4-5 週間**。

### §C-6.12.2 段階解禁ロードマップ

```mermaid
gantt
    title 認証アーキテクチャ実装ロードマップ
    dateFormat YYYY-MM-DD
    section Phase 1：基盤整備
    PoC-DET-1〜2（L1+L2）    :p1, 2026-07-01, 14d
    PoC-DET-3（L3 Semgrep）  :p2, after p1, 7d
    PoC-DET-4（L4 Athena）   :p3, after p2, 3d
    PoC-DET-5（L5 Synthetics）:p4, after p3, 7d
    PoC-DET-6（統合検証）    :p5, after p4, 7d
    section Phase 2：自律化解禁
    C1-C10 条件達成判定      :c1, after p5, 14d
    Inbound Partner 解禁     :c2, after c1, 7d
    Outbound SaaS 解禁       :c3, after c2, 7d
    section Phase 3：継続運用
    運用 KPI 評価            :ops, after c3, 90d
    外部 pen test            :pen, after c3, 30d
```

### §C-6.12.3 関連 PoC との接続

| 既存 PoC | 本章との接続 |
|---|---|
| **PoC-EXT-1〜6**（Partner 模擬環境）| 本章の Inbound 検証で利用、Detection PoC と並行可 |
| **Phase 10 Stage A** | Token Exchange 検証済、本章 §C-6.3 ② の根拠 |
| **Phase 9** | OAuth Client Credentials 検証済、§C-6.3 ② の Bronze tier |

### §C-6.12.4 TBD / 要確認

- Q: PoC 着手の **タイミング / 優先度** → `API-D-288`
- Q: 解禁判定の **正式承認者** → `API-D-289`

---

## §C-6.x 関連ドキュメント

### 機能要件側

- [§FR-API-0 外部からの API 実行 6 タイプ](../fr/00-external-api-consumption-overview.md) — Inbound 詳細
- [§FR-API-2 認証認可詳細](../fr/02-authn-authz.md) — Engine 機能の詳細仕様
- [§FR-API-7 ガードレール](../fr/07-guardrails.md) — Config Rules 実装
- [§FR-API-8 観測性](../fr/08-observability.md) — Athena クエリ標準

### 非機能要件側

- [§NFR-API-4 セキュリティ（死守事項）](../nfr/04-security.md) — Zero Trust 原則
- [§NFR-API-7 コンプライアンス](../nfr/07-compliance.md) — PCI DSS / APPI 対応

### 横断章

- [§C-API-1 全体参照アーキテクチャ](01-reference-architecture.md)
- [§C-API-3 共有認証基盤との接続点](03-shared-auth-boundary.md)
- [§C-API-4 監査アカウントとのガバナンス境界](04-audit-governance.md)
- [§C-API-5 標準提供物（Service Catalog）](05-self-service-catalog.md)

### 認証基盤側（input source）

- [認証基盤 §FR-2 顧客 IdP 連携](../../../requirements/proposal/fr/02-federation.md)
- [認証基盤 §FR-6 認可モデル](../../../requirements/proposal/fr/06-authz.md)
- [ADR-014 認証パターン Must/Should/Could/Won't](../../../adr/014-auth-patterns-scope.md)

### 業界参考

- [Auth0 Organizations](https://auth0.com/docs/manage-users/organizations) — Engine 中央 + Admin 委譲の業界実例
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/) — 認証実装漏れの業界分類
- [AWS Well-Architected Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html) — AWS native 検知ツールの根拠

---

## 改訂履歴

- **2026-06-19 初版**：6 セッションにわたる議論（Engine vs Relationship モデル / Inbound-Outbound 対称性 / 4 領域責務 / Self-Service Portal / Two-Track ガバナンス / 6 漏れパターン × 5 検知レイヤー / AWS リソース別検知可能性 / ALB グレーゾーン / 推奨ツールスタック / 分散化 OK 条件 C1-C10 / 残余リスク / PoC ロードマップ）を統合し、顧客説明可能な水準でドキュメント化。
