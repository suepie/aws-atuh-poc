# 外部 API 認証 配置方針 — 顧客向け検討資料

> **位置付け**: 「Partner / Private API の認証を**共通基盤に置くか / 各アプリに置くか**」を顧客と合意するための検討資料兼ヒアリング準備資料。
> **対象読者**: 顧客の情報システム部門 / API オーナー / アーキテクト / セキュリティ責任者
> **使い方**: §1 でヒアリング項目を埋める → §2-3 で配置方針を顧客と合議 → §4 のアクションに移行
> **関連標準**: [§C-API-6 外部 API 認証アーキテクチャ](../proposal/common/06-external-api-auth-architecture.md) （標準側 SSOT、本資料の根拠）
> **改訂**: 2026-06-19 初版

---

## 目次

1. [前提（ヒアリングで埋める）](#1-前提ヒアリングで埋める)
2. [Partner について](#2-partner-について)
3. [Private について](#3-private-について)
4. [次のアクション](#4-次のアクション)
5. [ヒアリング項目総括（チェックリスト）](#5-ヒアリング項目総括チェックリスト)

---

## 1. 前提（ヒアリングで埋める）

### 1.1 現状の API 3 カテゴリ

本標準は外部から呼ばれる API を **3 カテゴリ** に分類して認証方式を整理する：

| カテゴリ | 呼出元 | 業務例 |
|---|---|---|
| **Public** | エンドユーザー（ブラウザ / モバイル）+ 認証なし公開（公開ドキュメント等）| B2C / B2B 顧客の Web UI、ヘルスチェック、JWKS |
| **Partner** | 外部企業の Backend（M2M）、外部 SaaS Webhook 等 | 受発注、在庫同期、決済通知、API 統合 |
| **Private** | 社内 / AWS-to-AWS / 非 AWS 内部 | マイクロサービス間、GitHub Actions、on-prem |

### 1.2 各カテゴリの現状認証方式（要ヒアリング埋め）

| カテゴリ | 現状の認証方式 | 認証種別（大分類）| 該当 7 パターン（§2.1）| 共通基盤の関与 | ヒアリング ID |
|---|---|---|---|---|:---:|
| **Public** | <span style="color:gray">TBD: 共有認証基盤（Keycloak / Cognito）が JWT 発行、各アプリ API GW が JWT 検証</span> | **OAuth トークン** | P-1 / P-2 / P-3 のいずれか相当 | ✅（既定）| `H-CTX-1` |
| **Partner** | <span style="color:gray">TBD: 現在連携 Partner なし / 既存連携あり（方式：____）</span> | <span style="color:gray">TBD: OAuth トークン / 証明書 (mTLS) / 共有秘密キー (API Key・HMAC) / AWS IAM / その他</span> | <span style="color:gray">TBD: P-1〜P-7 のうち該当</span> | <span style="color:gray">TBD</span> | `H-CTX-2` |
| **Private** | <span style="color:gray">TBD: AWS IAM SigV4 / VPC Lattice / mTLS / その他</span> | <span style="color:gray">TBD: AWS IAM / 証明書 (mTLS) / その他</span> | <span style="color:gray">TBD: P-4 (mTLS) / P-7 (AWS IAM) 相当</span> | <span style="color:gray">TBD</span> | `H-CTX-3` |

#### 認証種別（大分類）の定義

| 大分類 | 内容 | 該当 7 パターン |
|---|---|---|
| **OAuth トークン** | IdP で credential 認証 → Bearer JWT 取得 → API 呼出に提示 | **P-1**（Client Credentials）/ **P-2**（Token Exchange）/ **P-3**（JWT Bearer）|
| **証明書 (mTLS)** | クライアント証明書を TLS handshake で検証 | **P-4** mTLS |
| **共有秘密キー** | 事前共有 secret を提示（静的）または署名計算（動的）| **P-5** API Key / **P-6** HMAC Signature |
| **AWS IAM 署名** | AWS SDK が SigV4 で各リクエスト署名 | **P-7** AWS IAM Cross-account |
| **その他** | 上記いずれにも該当しない独自方式 | 個別検討 |

> ✏️ **ヒアリング埋め**：上記の TBD 部分は顧客の現状認証方式 / Partner 数 / Private 連携方式を確認して埋める。
> 📎 **「大分類」と「7 パターン」の使い分け**：顧客との初期会話では「大分類」（OAuth / 証明書 / キー / IAM）で把握、技術詳細議論は「7 パターン」（P-1〜P-7）で精密化、というレイヤーで使い分ける。

### 1.3 §1.2「現状認証方式」と §2.1「7 パターン」の関係（Tier 廃止の補足）

| 観点 | §1.2 現状認証方式 | §2.1 7 パターン カタログ |
|---|---|---|
| **目的** | 顧客の **現在の認証実装状況**を捉える | **設計判断のための分類フレーム** |
| **粒度** | カテゴリ単位（Public / Partner / Private 3 区分）| 接続先単位（個別 Partner / SaaS 単位、5-15 件想定）|
| **使い方** | ヒアリングで現状把握 | 接続先ごとに「どのパターンか」を判定 |
| **連携** | §1.2 で把握した現状 →  §2.1 のどのパターンに該当するかをマッピング | §2.2 接続先マッピング表で統合 |

#### 旧 Tier 表現の廃止について

これまで議論で使っていた **Bronze / Silver / Gold tier 表現は本標準では使わない**。理由：

| 観点 | Tier フレーム | §2.1 7 パターン フレーム |
|---|---|---|
| **抽象度** | 抽象的（Bronze って具体的に何？が残る）| 具体的（P-2 = RFC 8693 と直接ひもづく）|
| **網羅性** | Bronze/Silver/Gold の 3 段（HMAC / IAM が漏れる）| 7 パターンで網羅 |
| **顧客説明** | 「Silver tier」と言われても意味不明 | 「OAuth Token Exchange」と言えば技術者に伝わる |
| **プラットフォーム選定への寄与** | 関連不明 | §2.1 表で直接 Keycloak/Cognito 対応可否が見える |

→ **ユーザ指摘通り、§2.1 の「認証方式直接分類」の方が分かりやすい**。Tier 表現は廃止し、本資料以降は **「P-1〜P-7 のどれか」で議論する**。

### 1.4 本資料の検討範囲

| カテゴリ | 本資料での検討 |
|---|---|
| **Public** | 共通基盤（共有認証基盤）採用で確定。本資料の検討対象外 |
| **Partner** | ⭐ **アプリ側 vs 共通基盤** の配置を検討（§2）|
| **Private** | ⭐ **IAM 単独で十分か、共通基盤も検討対象か**（§3）|

### 1.5 検討の動機

- **アプリチームの自律性**：リリースサイクルや SaaS 選定をアプリチームが自己完結したい
- **責任境界の明確化**：認証基盤チームとアプリチームの役割分担
- **業務適合性**：Partner / SaaS との運用関係は業務に深く紐づく、アプリチームが詳しい
- **ガバナンス担保**：自律化しても認証実装漏れが発生しないか確認したい

### 1.6 Origin Protection と DDoS 対策（前提共有）

本標準では **CloudFront + WAF を中央 Network Account に集約、API Gateway / ALB は各アプリ Account に配置** する 4 アカウント体制（[ADR-039](../../adr/039-centralized-network-account-edge-layer.md)）を採用する。「Partner / Private API の認証配置」議論の前提として、**「API GW を public 化しつつ、CloudFront 経由以外の直接アクセスを遮断する仕組み」**を確認しておく。

#### 1.6.1 構成図

```mermaid
flowchart LR
    Internet[Internet] -->|HTTPS| CF

    subgraph NetAcc["🟣 Network Account（中央集約）"]
        CF[CloudFront Distribution]
        WAF[AWS WAF<br/>Managed Rules + Rate]
        SM_Net[Secrets Manager<br/>X-Origin-Verify secret]
        L@E[Lambda@Edge<br/>Custom Header 注入]
        CF --> WAF --> L@E
        L@E -.fetch.-> SM_Net
    end

    subgraph AppA["🟢 App A Account"]
        APIGW[API GW REST<br/>REGIONAL]
        RP[Resource Policy<br/>① IP allowlist<br/>② Header 検証]
        Lambda
        APIGW --> RP --> Lambda
    end

    subgraph AppB["🟢 App B Account"]
        ALB[Public ALB]
        SG[Security Group + Listener Rule<br/>① CloudFront PL<br/>② Header 検証]
        ECS[ECS Fargate]
        ALB --> SG --> ECS
    end

    Direct[Direct Origin Attack] -.X.- APIGW
    Direct -.X.- ALB

    L@E -->|X-Origin-Verify: secret| APIGW
    L@E -->|X-Origin-Verify: secret| ALB

    style NetAcc fill:#e3f2fd
    style AppA fill:#e8f5e9
    style AppB fill:#e8f5e9
    style Direct fill:#ffcdd2
```

#### 1.6.2 ポイント

| 観点 | 内容 |
|---|---|
| **API GW の DNS は public** | `xxxxx.execute-api.ap-northeast-1.amazonaws.com` で公開、ただし **Resource Policy で実質非公開** |
| **Resource Policy で 2 層検証** | ① CloudFront 管理 IP プレフィックスリスト ② Custom Header `X-Origin-Verify` の Secret 一致 |
| **直接 curl での攻撃** | すべて 403、CloudFront 経由しない限り Origin に届かない |
| **Secret Rotation** | 30 日周期で自動ローテ、Overlap Period 24-72h（旧新両方受容） |
| **クロスアカウント運用** | Network Acct の Rotation Lambda が App Acct の Resource Policy / Listener Rule を Cross-account AssumeRole で更新 |

#### 1.6.3 DDoS 4 層防御

| 層 | 防御策 | 効果 |
|---|---|---|
| L1 | CloudFront Edge + Shield Standard 自動 | 99%+ の L3/L4 攻撃を Edge で吸収 |
| L2 | WAF Managed Rules + Rate-based + Bot Control | L7 攻撃、SQLi/XSS、量的攻撃遮断 |
| **L3 ⭐ Origin Protection** | **CloudFront IP allowlist + Custom Header** | **CloudFront 経由しない直接攻撃を完全遮断** |
| L4 | API GW Throttling + Backend Auto Scaling | 万一通過した負荷も Backend で吸収 |

→ 「Partner / Private の認証方式」と「Origin Protection」は **直交した関心事**。本資料 §2 / §3 で議論する認証方式は、上記 Origin Protection の **上に重ねる** 形で実装される。

### 1.7 認証実装漏れの自動検知（アプリチーム作り込みゼロ）

「アプリチームに認証を実装させる」決定の **継続検証**として、本標準では Synthetics canary が **5 分周期で全 API endpoint に対して未認証リクエストを送信、401/403 が返らなければアラート** という仕組みを Service Catalog 製品に同梱する。

#### 1.7.1 アプリチームと Platform チームの責務分担

| 主体 | やること | 工数 |
|---|---|---|
| **アプリチーム** | API 開発の通常業務として **OpenAPI を書く** + public endpoint に `x-synthetics-skip-auth-check: true` アノテーション + S3 アップ + Service Catalog 起動 | 数分 |
| **Platform チーム（初回のみ）** | 共通 canary Lambda 実装 + Service Catalog 製品テンプレ作成 + OpenAPI Registry 配備 | 1-2 週間 |
| **Platform チーム（運用）** | canary バージョン更新時の S3 zip 差し替え（既存 canary 自動追従）| 必要時のみ |

→ **canary の作り込み・Alarm 設定・OpenAPI Registry 運用はすべて Platform 集約**。アプリ数 N に対して 1 つの実装で済む。

#### 1.7.2 仕組み（OpenAPI ドリブン）

```mermaid
flowchart LR
    subgraph App["アプリチーム（作業最小）"]
        OAS[openapi.yaml]
        OAS_S3[S3 アップ]
        SC_Launch[Service Catalog 起動]
        OAS --> OAS_S3 --> SC_Launch
    end

    subgraph Platform["Platform チーム（初回のみ整備）"]
        Canary_Code[共通 canary Lambda<br/>auth-check-v1.zip]
        SC_Product[Service Catalog 製品テンプレ]
        Registry[OpenAPI Registry<br/>Shared S3]
        Export_Lambda[OpenAPI Export<br/>Custom Resource Lambda]
    end

    subgraph Auto["自動構築・実行"]
        APIGW[API Gateway]
        Canary[Synthetics canary]
        Probe[5 分周期 probe]
        Alarm[Slack 通知]
    end

    SC_Launch --> SC_Product
    SC_Product --> APIGW
    SC_Product --> Canary
    SC_Product --> Export_Lambda
    Canary_Code -.読込.-> Canary
    Export_Lambda -.deploy 後 export.-> Registry
    Registry -.読込.-> Canary
    Canary --> Probe
    Probe -.fail.-> Alarm

    style App fill:#c8e6c9
    style Platform fill:#e3f2fd
    style Auto fill:#fff9c4
```

#### 1.7.3 顧客説明用ポイント

| 観点 | メッセージ |
|---|---|
| **アプリチームの負担** | OpenAPI は API 開発の通常業務、追加負担は数分（S3 アップ + Service Catalog 起動）|
| **新規 endpoint の自動追従** | OpenAPI 更新 → 次回 deploy で canary が自動的に新 endpoint を probe 対象化 |
| **public endpoint の制御** | OpenAPI に `x-synthetics-skip-auth-check: true` を 1 行付けるだけ |
| **canary コード保守** | Platform チームが集約、全アプリで共通の 1 本のみ |
| **検証頻度** | 5 分周期（運用コスト次第で 15min も可能）|
| **コスト感** | アプリ 10 個 × endpoint 10 で月 $100 程度、95-99% の検知率達成 |
| **OpenAPI を持たないレガシー API** | 別製品 `api-gateway-legacy-public`（自動発見方式）で対応可 |

#### 1.7.4 検知できるパターン

| 漏れパターン | 検知 |
|---|:---:|
| Authorizer 設定忘れ（AuthorizationType=NONE）| ✅ |
| Authorizer が常に Allow を返すバグ | ✅（無効 token probe で）|
| JWT 検証バグ（`alg=none` 受容等）| ✅（alg=none probe で）|
| 特定 path の bypass | ✅（全 endpoint enum で）|
| ALB アプリコード内認証の素通り | ✅ |
| tenant 越境 | ✅（追加 probe で）|

#### 1.7.5 Negative + Positive 両方の検証（重要）

「認証なしリクエストで 401 が返るか」（Negative test）だけでは、**「認証が無いから 401」と「テスト構成ミスで失敗」を区別できない**。本標準では **valid token を使った正常系（Positive test）も併用**し、両方の組合せで判定する。

##### なぜ両方必要か

| Negative の結果 | Positive の結果 | 解釈 | 通知先 |
|:---:|:---:|---|---|
| **401 / 403** | **200** | ✅ 認証が機能 + API 稼働 | 通知なし |
| **200** | **200** | ❌❌ **認証が完全 missing**（最重大）| 🔥 Security オンコール（P1）|
| 401 / 403 | 401 / 403 | ⚠ テスト token が無効 | Platform チーム（P2）|
| 401 / 403 | 404 | ⚠ endpoint 不在 / テスト構成ミス | Platform チーム（P2）|
| 401 / 403 | 500 | ⚠ Backend バグ（認証は OK）| アプリチーム（P3）|

→ Negative だけでは「Negative=401/403 で OK」と判定してしまい、**実は endpoint そのものが存在せず 404 が 401 に偽装される**等のエッジケースを見落とす。Positive を併用することで「**認証が正しく機能 + API が稼働している**」を初めて断言できる。

##### Production と Pre-prod での運用差

| 環境 | Negative（全 endpoint）| Positive (GET)（read-only）| Positive (POST/PUT/DELETE)（副作用あり）|
|---|:---:|:---:|:---:|
| **Production** | ✅ 実施 | ✅ 実施（安全）| ❌ skip（副作用回避）|
| **Staging / Dev** | ✅ 実施 | ✅ 実施 | ✅ 実施（cleanup 付き）|

→ production で POST 等の副作用を起こさないため、OpenAPI に `x-canary-positive-test: pre-prod-only` を付けることで自動制御。アプリチームの追加負担はアノテーション 1 行のみ。

##### Failure 分類でアラートを正しく振り分け

```mermaid
flowchart LR
    Fail[canary 失敗]
    Sec[🔥 Security オンコール<br/>認証実装漏れ]
    Plat[🟡 Platform チーム<br/>テスト基盤 / 構成]
    App[🟢 アプリチーム<br/>Backend バグ]
    Fail --> Sec
    Fail --> Plat
    Fail --> App

    style Sec fill:#ffcdd2
    style Plat fill:#fff9c4
    style App fill:#c8e6c9
```

→ 「**全部 Security オンコールに飛ばす**」のではなく、**4×4 真偽値表に基づく自動分類**で適切な担当に振り分け、運用負担を最小化。

##### テスト用 token の運用（Platform 集約）

Positive test には **valid token** が必要だが、これも Platform 集約で運用：

- 共有認証基盤に `canary-readonly-client` / `canary-write-client` を最小権限で作成
- Secrets Manager に保管 + 30 日自動ローテ
- multi-tenant の場合は `canary-probe-tenant` を分離（production テナント影響ゼロ）
- アプリチームは OpenAPI に `x-canary-test-token-secret: canary-readonly-token` と書くだけ

→ 詳細は標準側 [§C-API-6 §C-6.6.8](../proposal/common/06-external-api-auth-architecture.md) 参照。

---

## 2. Partner について

### 2.1 Partner 認証 7 パターン（顧客自己分類用）

> ⚠️ **本表の適用範囲（重要）**：本表は **Inbound（外部 Partner / SaaS → 自社 API）** の認証パターンを整理したもの。**Outbound（自社 → 外部 SaaS）** は接続先 SaaS が認証 protocol を決めるため、自由に選べる設計判断ではない（§2.1.A 参照）。
> 🗑️ **Tier 表現（Bronze/Silver/Gold）は廃止**：本標準では「7 パターン」を正規モデルとし、抽象的な Tier 表現は使わない。「どのパターンに該当するか」で接続先ごとに直接判定する。

外部企業 / SaaS と本システムを Inbound 連携する場合、認証方式は **7 つの基本パターン**に分類される。顧客は接続先ごとにどのパターンが該当するかを判断する。

#### 7 パターン早見表（Inbound）

| # | パターン | **大分類**（§1.2 連携）| セキュリティ強度 | Partner 側に必要な機能 | 業界実例 | **Keycloak 対応** | **Cognito 対応** |
|:---:|---|:---:|:---:|---|---|:---:|:---:|
| **P-1** | **OAuth 2.0 Client Credentials Grant** | **OAuth トークン** | 中-高 | client_id / client_secret を保管できる | Salesforce, Microsoft Graph, Stripe (モダン版) | ✅ ネイティブ | ✅ Plus tier (2024-11 GA) |
| **P-2** | **OAuth 2.0 Token Exchange (RFC 8693)** | **OAuth トークン** | 高 | 自社 OIDC IdP（Entra ID / Okta / Auth0 等）を保有 | OIDC Federation, Auth0 multi-org, Curity | ✅ ネイティブ（v22+ で v2 GA）| ❌ **未対応** |
| **P-3** | **OAuth 2.0 JWT Bearer Grant (RFC 7523)** | **OAuth トークン** | 高 | 自社 PKI で JWT 署名できる | GitHub Apps, Snowflake | ✅ ネイティブ | ❌ 未対応 |
| **P-4** | **mTLS（Mutual TLS, RFC 8705）** | **証明書 (mTLS)** | 最高 | クライアント証明書発行運用ができる | 金融 / 決済 / FAPI 2.0 / 医療 | ✅ ネイティブ（X.509 Authenticator）| △ Cognito 単体不可、API GW Custom Domain mTLS で別レイヤー実装 |
| **P-5** | **API Key + Usage Plan** | **共有秘密キー** | 低 | 文字列を保管できる | Stripe（一部）, Twilio, SendGrid | – 認証基盤対象外（API GW Usage Plan）| – 認証基盤対象外 |
| **P-6** | **HMAC Signature（Webhook 受信）** | **共有秘密キー** | 中 | shared secret + 署名計算 | Stripe → 決済通知, GitHub → push event | – 認証基盤対象外（Lambda Authorizer 実装）| – 認証基盤対象外 |
| **P-7** | **AWS IAM Cross-account (SigV4)** | **AWS IAM 署名** | 高 | AWS アカウント保有 + IAM Role 設定 | AWS-to-AWS Partner（VPC Peering / Lattice）| – 認証基盤対象外（AWS IAM）| – 認証基盤対象外 |

#### Keycloak / Cognito 対応観点でのプラットフォーム選定示唆

| 採用 protocol | 推奨プラットフォーム | 根拠 |
|---|---|---|
| **P-1 のみ** | Cognito Plus tier or Keycloak | どちらでも可、コスト・運用負荷で選定 |
| **P-2 Token Exchange を採用** | **Keycloak 必須**（Cognito 未対応）| RFC 8693 サポートは Keycloak のみ |
| **P-3 JWT Bearer Grant を採用** | **Keycloak 必須** | Cognito 未対応 |
| **P-4 mTLS を採用** | Keycloak が望ましい | Cognito は API GW 別レイヤー実装必要 |
| **P-5/P-6/P-7** | 認証基盤に依存しない（API GW / IAM）| プラットフォーム選定への影響なし |

→ **本標準で Keycloak を採用する根拠の中核は P-2 / P-3 / P-4**。これらを使わない前提なら Cognito Plus も選択肢。

#### Tier 表現との対応（廃止）

旧 Tier 表現を廃止し、7 パターンに統一する：

| 旧 Tier 表現 | 新 7 パターン表現 | 利点 |
|---|---|---|
| Bronze tier | P-1 OAuth Client Credentials または P-5 API Key | 「何の protocol か」が明確 |
| Silver tier | **P-2 Token Exchange** | RFC 8693 という具体仕様 |
| Gold tier | **P-4 mTLS** + P-1/P-2 のいずれか（併用）| 「mTLS + OAuth」と組合せ明示可 |
| Tier 該当なし | P-3 / P-6 / P-7 | 旧フレームでは表現できなかった protocol を網羅 |

→ **「Bronze/Silver/Gold で語る」習慣を捨て、「P-1〜P-7 のどれか」で議論する**。

#### 大分類別フロー（初期設定時 / 認証時）

大分類 4 種（OAuth トークン / 証明書 / 共有秘密キー / AWS IAM 署名）について、**初期設定時のオンボーディング手順**と**実行時の認証フロー**を整理する。

---

##### 大分類 1: OAuth トークン（P-1 / P-2 / P-3）

**特徴**：IdP で credential 認証 → Bearer JWT を取得 → API GW に提示。Token TTL（1h 標準）で被害限定。

**初期設定時のフロー**

```mermaid
sequenceDiagram
    participant App as アプリチーム
    participant Partner
    participant Portal as Self-Service<br/>Developer Portal
    participant IdP as 共有認証基盤
    participant SM as Partner 側<br/>Secrets Manager

    App->>Partner: ① 契約・交渉（scope 設計）
    App->>Portal: ② Partner Client 申請
    Portal->>IdP: ③ Admin API で M2M Client 作成
    IdP-->>Portal: ④ client_id, client_secret 発行
    Portal-->>App: ⑤ credential 受領
    App->>Partner: ⑥ 暗号化メール / 1Password 等で配布
    Partner->>SM: ⑦ Secrets 保管
```

**認証時のフロー**

```mermaid
sequenceDiagram
    participant Partner
    participant Cache as Partner 側<br/>Token Cache
    participant IdP as 共有認証基盤<br/>/oauth2/token
    participant APIGW
    participant Authz as JWT Authorizer
    participant Lambda

    Partner->>Cache: ① Token があるか確認
    alt Token なし / 期限切れ
        Partner->>IdP: ② /oauth2/token<br/>(client_id + secret)
        IdP->>IdP: ③ credential 検証
        IdP-->>Partner: ④ Bearer JWT (TTL 1h)
        Partner->>Cache: ⑤ Cache に保存（TTL - 60s）
    end
    Partner->>APIGW: ⑥ Authorization: Bearer JWT
    APIGW->>Authz: ⑦ JWT Authorizer 起動
    Authz->>Authz: ⑧ 署名・iss・aud・exp・scope 検証
    Authz-->>APIGW: ⑨ Allow + context
    APIGW->>Lambda: ⑩ 認可済リクエスト
    Lambda-->>Partner: ⑪ 200 OK
```

**要点**：
- API GW 側設定は P-1/P-2/P-3 で **すべて同じ JWT Authorizer**
- 差は IdP 側の Token 発行手順のみ（client cred / token-exchange / jwt-bearer）
- Token Cache が運用上の鍵（毎回 /token を叩くと IdP 負荷増 + レイテンシ +200ms）

---

##### 大分類 2: 証明書 (mTLS) — P-4

**特徴**：クライアント証明書を TLS handshake で検証、TLS 層で完結。CloudFront 経由不可（ALB / API GW Custom Domain 直接）。

**初期設定時のフロー**

```mermaid
sequenceDiagram
    participant App as アプリチーム
    participant Sec as Security<br/>(CA 運用)
    participant Partner
    participant CA as 自社 Private CA<br/>(AWS Private CA等)
    participant APIGW as API GW<br/>Custom Domain
    participant Trust as Truststore

    App->>Partner: ① 契約・交渉（規制要件確認）
    Partner->>Partner: ② Partner が CSR 生成
    Partner->>Sec: ③ CSR 送付
    Sec->>CA: ④ CSR 署名要求
    CA-->>Sec: ⑤ Client Cert 発行
    Sec-->>Partner: ⑥ Client Cert + 中間 CA 配布
    Partner->>Partner: ⑦ 秘密鍵 + 証明書 を保管
    Sec->>Trust: ⑧ Partner CA bundle 登録
    Sec->>APIGW: ⑨ mTLS Listener 設定 + CRL/OCSP 設定
```

**認証時のフロー**

```mermaid
sequenceDiagram
    participant Partner
    participant TLS as API GW<br/>Custom Domain<br/>(mTLS Listener)
    participant Trust as Truststore
    participant CRL as CRL/OCSP
    participant APIGW
    participant Lambda

    Partner->>TLS: ① TLS Handshake 開始
    TLS->>Partner: ② Server Cert 提示
    Partner->>TLS: ③ Client Cert 提示
    TLS->>Trust: ④ 証明書 chain 検証
    Trust-->>TLS: ⑤ Valid
    TLS->>CRL: ⑥ 失効確認 (CRL/OCSP)
    CRL-->>TLS: ⑦ Not revoked
    TLS->>TLS: ⑧ TLS 確立
    Partner->>APIGW: ⑨ HTTPS リクエスト<br/>(cert binding 含む)
    APIGW->>Lambda: ⑩ cert 情報 (Subject DN) を context に
    Lambda-->>Partner: ⑪ 200 OK
```

**要点**：
- 認証ステップは **TLS handshake 内で完結**、Bearer Token 不要（ただし FAPI 2.0 では併用推奨）
- 証明書発行・配布・失効管理（CRL/OCSP）の運用負荷が高い
- Overlap Period（旧新証明書併存 24-72h）必須

---

##### 大分類 3: 共有秘密キー（P-5 API Key + P-6 HMAC）

**特徴**：事前共有された secret を提示（静的：API Key）または毎回署名計算（動的：HMAC）。AWS 公式：API Key は認証ではなく識別。

###### P-5 API Key 初期設定時のフロー

```mermaid
sequenceDiagram
    participant App as アプリチーム
    participant Partner
    participant APIGW
    participant UP as Usage Plan

    App->>Partner: ① 契約・交渉（プラン選定）
    App->>APIGW: ② Usage Plan 作成<br/>(Throttle / Quota)
    App->>APIGW: ③ API Key 発行
    APIGW-->>App: ④ API Key 受領
    App->>UP: ⑤ Usage Plan に API Key 紐付け
    App->>Partner: ⑥ 暗号化メール等で配布
    Partner->>Partner: ⑦ Secrets 保管
```

###### P-5 API Key 認証時のフロー

```mermaid
sequenceDiagram
    participant Partner
    participant APIGW
    participant UP as Usage Plan
    participant Lambda

    Partner->>APIGW: ① x-api-key: <key>
    APIGW->>UP: ② API Key 検証<br/>+ Throttle/Quota チェック
    UP-->>APIGW: ③ 通過
    APIGW->>Lambda: ④ リクエスト転送
    Lambda-->>Partner: ⑤ 200 OK
```

###### P-6 HMAC 初期設定時のフロー

```mermaid
sequenceDiagram
    participant App as アプリチーム
    participant SaaS as 外部 SaaS<br/>(Stripe等)
    participant SM as Secrets Manager
    participant APIGW
    participant Authz as Lambda Authorizer

    App->>SaaS: ① SaaS 側 Console で<br/>Webhook 設定 (URL 指定)
    SaaS-->>App: ② Webhook Secret 発行
    App->>SM: ③ Secret を保管 (CMK)
    App->>APIGW: ④ Webhook endpoint 作成
    App->>Authz: ⑤ Lambda Authorizer 設定<br/>(Secret 読込み)
```

###### P-6 HMAC 認証時のフロー

```mermaid
sequenceDiagram
    participant SaaS as 外部 SaaS
    participant APIGW
    participant Authz as Lambda Authorizer
    participant SM as Secrets Manager
    participant DDB as Idempotency Store<br/>(DynamoDB)
    participant Lambda

    SaaS->>APIGW: ① POST + X-Signature: HMAC<br/>+ X-Timestamp + body
    APIGW->>Authz: ② Lambda Authorizer 起動
    Authz->>SM: ③ Webhook Secret 取得
    Authz->>Authz: ④ HMAC 計算 → 提示値と比較
    Authz->>Authz: ⑤ Timestamp ±5min check<br/>(Replay 対策)
    Authz->>DDB: ⑥ Idempotency-Key 重複確認
    Authz-->>APIGW: ⑦ Allow
    APIGW->>Lambda: ⑧ リクエスト転送
    Lambda-->>SaaS: ⑨ 200 OK (即返却、処理は async)
```

**要点**：
- P-5 API Key は **「認証ではなく識別」**（AWS 公式明記）、単独で使うのは非推奨
- P-6 HMAC は **送信側が SaaS で OAuth が使えない**特殊ケース、Replay 対策 + Idempotency 必須
- 両方とも secret ローテーション運用が必要

---

##### 大分類 4: AWS IAM 署名（P-7）

**特徴**：AWS SDK が SigV4 で毎リクエスト署名。AWS マネージドで完結、credential 不要（STS 動的発行）、最小権限細粒度。

**初期設定時のフロー**

```mermaid
sequenceDiagram
    participant App as アプリチーム
    participant Partner as Partner<br/>(AWS account 保有)
    participant IAM as 自社 IAM
    participant APIGW

    App->>Partner: ① 契約・交渉<br/>(AWS account ID 取得)
    App->>IAM: ② Cross-account IAM Role 作成<br/>(Trust Policy: Partner account)
    IAM-->>App: ③ Role ARN 取得
    App->>APIGW: ④ AuthorizationType=AWS_IAM 設定
    App->>APIGW: ⑤ Resource Policy 設定<br/>(Partner ARN を Principal)
    App->>Partner: ⑥ Role ARN + API GW URL 共有
    Partner->>Partner: ⑦ Partner 側 IAM Role 設定<br/>(AssumeRole 権限)
```

**認証時のフロー**

```mermaid
sequenceDiagram
    participant Partner as Partner<br/>(AWS Lambda / EC2 等)
    participant STS as AWS STS
    participant SDK as AWS SDK
    participant APIGW
    participant IAM as AWS IAM
    participant Lambda

    Partner->>STS: ① AssumeRole<br/>(Cross-account)
    STS-->>Partner: ② 一時的 credential<br/>(AccessKey + SecretKey + SessionToken)
    Partner->>SDK: ③ AWS SDK でリクエスト構築
    SDK->>SDK: ④ SigV4 で署名
    SDK->>APIGW: ⑤ SigV4 署名付きリクエスト
    APIGW->>IAM: ⑥ AWS が SigV4 検証 + Policy 評価
    IAM-->>APIGW: ⑦ Allow
    APIGW->>Lambda: ⑧ リクエスト転送
    Lambda-->>Partner: ⑨ 200 OK
```

**要点**：
- credential は **STS で動的発行**（永続 secret なし、漏洩リスク最小）
- 毎リクエストで SigV4 署名 → token 取得ステップ不要
- Partner も AWS account 保有が前提（AWS 外 Partner には適用不可）

---

##### 大分類別フロー まとめ

| 大分類 | 該当 P | 認証時の主要ステップ | 初期設定時の主要ステップ | API GW 側設定 |
|---|---|---|---|---|
| **OAuth トークン** | P-1/2/3 | IdP で Token 取得 → Bearer 提示 → JWT Authorizer 検証 | Self-Service Portal で M2M Client 作成 → secret 配布 | **JWT Authorizer** |
| **証明書 (mTLS)** | P-4 | TLS Handshake で cert 検証 → 各リクエストへ context 注入 | Partner CSR 受領 → 自社 CA 署名 → Truststore 登録 | **mTLS Custom Domain** |
| **共有秘密キー (API Key)** | P-5 | x-api-key 送信 → Usage Plan 検証 | API Key 発行 → Usage Plan 紐付け → 配布 | **API Key Required + Usage Plan** |
| **共有秘密キー (HMAC)** | P-6 | HMAC 署名検証 + Timestamp + Idempotency | SaaS 側で Webhook 設定 → Secret 取得 → Secrets Manager 保管 | **Lambda Authorizer** |
| **AWS IAM 署名** | P-7 | STS AssumeRole → SigV4 署名 → IAM 検証 | Cross-account Role 作成 → Trust Policy 設定 → ARN 共有 | **AuthorizationType=AWS_IAM** |

→ **Type A（OAuth）= 「事前 Token 取得 → 使う」、Type B（mTLS / IAM）= 「リクエスト毎に署名」、Type C（API Key / HMAC）= 「静的 secret 提示」**の 3 類型に集約。

#### ⚠️ Outbound（自社 → 外部 SaaS）の扱い

Outbound は **接続先 SaaS が認証 protocol を決める**ため、Inbound のような「設計判断としての 7 パターン選定」は発生しない。我々がやることは **「SaaS の規定に従ってクライアント実装する + credential を Secrets Manager で安全保管する」**のみ。

##### 代表 SaaS 別 Outbound 認証

| SaaS | SaaS が要求する protocol | 我々の実装 |
|---|---|---|
| **Stripe** | API Key（Secret Key）または OAuth Connect | `Authorization: Bearer <key>` 送信 |
| **SendGrid** | API Key | `Authorization: Bearer <key>` 送信 |
| **OpenAI** | API Key | `Authorization: Bearer <key>` 送信 |
| **Slack** | OAuth 2.0 Auth Code Flow | OAuth Flow 実装 + token 保管 + Refresh 運用 |
| **GitHub API（個人 PAT）** | API Key 相当（PAT）| Header 送信 |
| **GitHub App** | JWT Bearer + Installation Token | JWT 署名実装 + Token 取得 |
| **Microsoft Graph** | OAuth Client Credentials | P-1 と同等の Outbound 版 |
| **AWS Services** | AWS SDK SigV4 | SDK 自動署名（追加実装ゼロ）|

→ Outbound 設計判断は「**どの SaaS を採用するか**」と「**credential をどう保管・ローテするか**」の 2 点のみ。protocol は SaaS 側依存。

##### Outbound で 7 パターンを「逆向き」に見ると

技術的にプロトコルは双方向で使えるが、Outbound での典型出現頻度：

| パターン | Inbound 典型度 | Outbound 典型度 | Outbound 採用 SaaS 例 |
|---|:---:|:---:|---|
| P-1 OAuth Client Credentials | ✅ 主流 | ⚠ 一部 | Microsoft Graph, Salesforce |
| P-2 Token Exchange | ✅ 主流 | ❌ ほぼなし | – |
| P-3 JWT Bearer Grant | ✅ 主流 | ⚠ 限定 | GitHub App |
| P-4 mTLS | ✅ 主流 | ⚠ 限定 | 金融機関 API 連携時 |
| P-5 API Key | ⚠ | ✅ **主流** | **Stripe / SendGrid / OpenAI** |
| P-6 HMAC | ✅（受信）| ⚠（送信）| 自社が Webhook 送信する時 |
| P-7 AWS IAM | ✅ | ✅（AWS-to-AWS）| AWS Service / Marketplace Partner |

→ **Outbound の主流は P-5 API Key**（業界の SaaS 主流が API Key のため）。本資料の §2.4 配置比較も「API Key 中心の Outbound」を前提に整理している。

#### Outbound 大分類別フロー（初期設定時 / 認証時）

Outbound（自社 → 外部 SaaS）における大分類別の「初期設定時のオンボーディング手順」と「実行時の認証フロー」を整理する。Inbound と対称構造（Engine 提供者が外部 SaaS、自社は client として実装）。

---

##### Outbound 大分類 1: OAuth トークン（例: Microsoft Graph / Salesforce）

**初期設定時のフロー**

```mermaid
sequenceDiagram
    participant App as アプリチーム
    participant SaaS as 外部 SaaS Console
    participant SM as 自社 Secrets Manager
    participant Lambda

    App->>SaaS: ① SaaS 申込 / Console で<br/>Application 登録 + scope 申請
    SaaS-->>App: ② client_id, client_secret 発行
    App->>SM: ③ Secret を保管 (CMK + 自動ローテ)
    App->>Lambda: ④ Lambda IAM Role に<br/>Secret 取得権限付与
```

**認証時のフロー**

```mermaid
sequenceDiagram
    participant Lambda
    participant SM as Secrets Manager
    participant Cache as Token Cache
    participant SToken as SaaS /oauth2/token
    participant SAPI as SaaS API

    Lambda->>Cache: ① Token あるか
    alt なし / 期限切れ
        Lambda->>SM: ② Secret 取得
        Lambda->>SToken: ③ client_id + secret で /token
        SToken-->>Lambda: ④ Bearer JWT
        Lambda->>Cache: ⑤ Cache 保存（TTL - 60s）
    end
    Lambda->>SAPI: ⑥ Authorization: Bearer JWT
    SAPI-->>Lambda: ⑦ 200 OK
```

---

##### Outbound 大分類 2: 証明書 (mTLS)（例: 金融機関 API 連携）

**初期設定時のフロー**

```mermaid
sequenceDiagram
    participant App as アプリチーム
    participant SaaS as 外部 SaaS / 金融機関
    participant CA as 自社 CA or<br/>SaaS 指定 CA
    participant SM as Secrets Manager

    App->>SaaS: ① 契約・規制要件確認<br/>(CA 指定の有無)
    App->>CA: ② CSR 生成 + 署名要求
    CA-->>App: ③ Client Cert + 秘密鍵
    App->>SM: ④ Cert + 秘密鍵を保管 (CMK)
    App->>SaaS: ⑤ 公開鍵 / Cert を SaaS に登録
```

**認証時のフロー**

```mermaid
sequenceDiagram
    participant Lambda
    participant SM as Secrets Manager
    participant SaaS as 外部 SaaS

    Lambda->>SM: ① Cert + 秘密鍵 取得
    Lambda->>SaaS: ② TLS Handshake +<br/>Client Cert 提示
    SaaS->>SaaS: ③ Truststore で検証
    SaaS-->>Lambda: ④ TLS 確立
    Lambda->>SaaS: ⑤ HTTPS リクエスト
    SaaS-->>Lambda: ⑥ 200 OK
```

---

##### Outbound 大分類 3-a: API Key（例: Stripe / SendGrid / OpenAI）⭐ Outbound 主流

**初期設定時のフロー**

```mermaid
sequenceDiagram
    participant App as アプリチーム
    participant SaaS as 外部 SaaS Console
    participant SM as Secrets Manager
    participant Lambda

    App->>SaaS: ① SaaS 申込 / アカウント開設
    SaaS-->>App: ② Console で API Key 発行
    App->>SM: ③ API Key を保管 (CMK)
    App->>Lambda: ④ Lambda IAM Role に<br/>Secret 取得権限付与
    App->>App: ⑤ (可能なら) 自動ローテーション設定
```

**認証時のフロー**

```mermaid
sequenceDiagram
    participant Lambda
    participant SM as Secrets Manager
    participant SaaS as 外部 SaaS API

    Lambda->>SM: ① API Key 取得 (or Cache)
    Lambda->>SaaS: ② Authorization: Bearer <key><br/>or x-api-key: <key>
    SaaS->>SaaS: ③ Key 検証
    SaaS-->>Lambda: ④ 200 OK
```

---

##### Outbound 大分類 3-b: HMAC（自社が Webhook 送信側）

**初期設定時のフロー**

```mermaid
sequenceDiagram
    participant App as アプリチーム
    participant Partner as Partner (受信側)
    participant SM as Secrets Manager

    App->>Partner: ① Webhook 連携契約
    App->>App: ② shared secret 生成
    App->>Partner: ③ 暗号化チャネルで配布
    App->>SM: ④ secret を保管 (CMK)
    Partner->>Partner: ⑤ 受信 endpoint 設定 + secret 保管
```

**認証時のフロー**

```mermaid
sequenceDiagram
    participant Lambda
    participant SM as Secrets Manager
    participant Partner as Partner endpoint

    Lambda->>SM: ① shared secret 取得
    Lambda->>Lambda: ② payload + HMAC 計算<br/>+ Timestamp 付与
    Lambda->>Partner: ③ POST + X-Signature<br/>+ X-Timestamp + body
    Partner->>Partner: ④ HMAC 検証 + Replay チェック
    Partner-->>Lambda: ⑤ 200 OK
```

---

##### Outbound 大分類 4: AWS IAM 署名（例: AWS Service / AWS Marketplace Partner）

**初期設定時のフロー**

```mermaid
sequenceDiagram
    participant App as アプリチーム
    participant Partner as Partner (AWS account)
    participant PIAM as Partner IAM
    participant Lambda

    App->>Partner: ① AWS account ID 共有
    Partner->>PIAM: ② Cross-account Role 作成<br/>(Trust Policy: 自社 account)
    Partner-->>App: ③ Role ARN 受領
    App->>Lambda: ④ Lambda Execution Role に<br/>AssumeRole 権限付与
```

**認証時のフロー**

```mermaid
sequenceDiagram
    participant Lambda
    participant STS as AWS STS
    participant SDK as AWS SDK
    participant Partner as Partner AWS Service

    Lambda->>STS: ① AssumeRole (Cross-account)
    STS-->>Lambda: ② 一時 credential
    Lambda->>SDK: ③ AWS SDK で<br/>リクエスト構築 + SigV4 署名
    SDK->>Partner: ④ SigV4 署名付きリクエスト
    Partner->>Partner: ⑤ IAM 検証
    Partner-->>Lambda: ⑥ 200 OK
```

---

##### Outbound 大分類別フロー まとめ

| 大分類 | 設定主体 | Engine 提供 | 自社の主要作業 |
|---|---|---|---|
| OAuth トークン | 外部 SaaS の Application 機能 | 外部 SaaS | client_id/secret 受領 + Secrets Manager 保管 + Token Cache |
| 証明書 (mTLS) | 自社 CA or SaaS 指定 CA | 外部 SaaS の Truststore | CSR 生成 + Cert 保管 + mTLS Client 実装 |
| API Key | 外部 SaaS Console | 外部 SaaS | Key 受領 + Secrets Manager 保管 |
| HMAC | 自社（Webhook 送信側）| 自社 + Partner | secret 生成 + 配布 + HMAC 計算実装 |
| AWS IAM | Partner AWS account | AWS IAM + STS | Lambda Execution Role に AssumeRole 権限 |

→ Outbound では **「Engine は外部 SaaS（一部は自社）」「自社は client として実装 + credential を Secrets Manager で安全保管」**が共通構造。

#### 各パターンの特徴詳細

##### P-1: OAuth 2.0 Client Credentials Grant

| 項目 | 内容 |
|---|---|
| **概要** | Partner が `client_id + client_secret` を共有認証基盤の `/oauth2/token` に送って Bearer JWT を取得、API 呼出時に Bearer ヘッダで提示 |
| **メリット** | OAuth 2.0 業界標準、SDK 豊富、Token TTL で被害限定 |
| **デメリット** | client_secret 漏洩リスク、ローテ運用必要 |
| **典型ユースケース** | Partner が自社 IdP を持たない SMB / Trial、一般的な B2B SaaS 連携 |
| **セキュリティ要件適合** | 機密度：中、規制：通常 B2B、頻度：高頻度 OK |

##### P-2: OAuth 2.0 Token Exchange (RFC 8693)

| 項目 | 内容 |
|---|---|
| **概要** | Partner が自社 IdP で発行した token を `/oauth2/token` で exchange、本基盤発行 token に変換して API 呼出 |
| **メリット** | Partner 側で credential 管理完結、ローテ Partner 自社運用、我々が secret 配布不要 |
| **デメリット** | Partner 側 IdP 保有が前提、信頼台帳の運用必要 |
| **典型ユースケース** | Partner が大企業で Entra ID / Okta / Auth0 保有、Federation 重視 |
| **セキュリティ要件適合** | 機密度：中-高、規制：通常 B2B + 監査強化、頻度：高頻度 OK |

##### P-3: OAuth 2.0 JWT Bearer Grant (RFC 7523)

| 項目 | 内容 |
|---|---|
| **概要** | Partner が自社秘密鍵で署名した JWT を `assertion` として送信、認証基盤が公開鍵で検証 |
| **メリット** | shared secret 不要、暗号学的検証、漏洩リスク低 |
| **デメリット** | Partner 側で鍵管理 + JWT 署名実装必要、運用負荷高 |
| **典型ユースケース** | GitHub Apps、データ分析 SaaS、エンタープライズ自社開発システム |
| **セキュリティ要件適合** | 機密度：高、規制：強化、頻度：高頻度 OK |

##### P-4: mTLS（Mutual TLS, RFC 8705）

| 項目 | 内容 |
|---|---|
| **概要** | TLS handshake 時に Partner のクライアント証明書を検証、API GW Custom Domain で mTLS 終端 |
| **メリット** | TLS 層で認証完結、最高セキュリティ、Certificate-bound Token も可（cnf claim） |
| **デメリット** | 証明書発行・配布・失効運用（CRL）が必要、CloudFront 経由不可 |
| **典型ユースケース** | 金融 / 決済 / オープンバンキング / FAPI 2.0 / 医療 / 政府連携 |
| **セキュリティ要件適合** | 機密度：最高、規制：金融 / HIPAA / FedRAMP、頻度：中-高頻度 |

##### P-5: API Key + Usage Plan

| 項目 | 内容 |
|---|---|
| **概要** | API Gateway 発行の API Key を `x-api-key` ヘッダで送信、Usage Plan で識別 + クォータ管理 |
| **メリット** | 最もシンプル、開発工数最小、即時オンボーディング |
| **デメリット** | **AWS 公式：認証用途は非推奨**（識別のみ）、漏洩リスク高、暗号学的検証なし |
| **典型ユースケース** | 公開 API のトライアル、識別 + 課金専用、低リスク連携 |
| **セキュリティ要件適合** | 機密度：低、規制：なし、頻度：低-中 |

##### P-6: HMAC Signature（Webhook 受信）

| 項目 | 内容 |
|---|---|
| **概要** | 外部 SaaS（Stripe / GitHub 等）が本システムに push する際、shared secret で HMAC 署名、本システムが検証 |
| **メリット** | Webhook 専用、SaaS 業界標準、Replay 対策と組合せ可 |
| **デメリット** | OAuth は使えない（送信側が SaaS のため）、shared secret ローテ必要 |
| **典型ユースケース** | Stripe → 決済通知、GitHub → push event、Auth0 → user event |
| **セキュリティ要件適合** | 機密度：中、規制：SaaS 側準拠、頻度：イベント駆動 |

##### P-7: AWS IAM Cross-account (SigV4)

| 項目 | 内容 |
|---|---|
| **概要** | Partner も AWS アカウント保有、IAM Role を Cross-account Assume、SigV4 で API 呼出 |
| **メリット** | AWS マネージドで完結、credential 不要（STS 動的発行）、最小権限細粒度 |
| **デメリット** | Partner も AWS 利用が前提、AWS 外 Partner には適用不可 |
| **典型ユースケース** | AWS Marketplace SaaS、AWS パートナー企業との B2B、VPC Lattice cross-account |
| **セキュリティ要件適合** | 機密度：高、規制：AWS 環境内、頻度：高頻度 OK |

#### セキュリティ要件 → パターン推奨フロー

接続先ごとの **セキュリティ要件**から推奨パターンを判定：

```mermaid
flowchart TD
    Start([Partner 接続要件])
    Q1{方向は?}

    Start --> Q1
    Q1 -->|"自社→Partner / 双方向"| Q2{Partner は AWS 利用か?}
    Q1 -->|"Partner→自社 のみ（push通知）"| P6["P-6 HMAC<br/>Signature"]

    Q2 -->|Yes 同 AWS Org| P7["P-7 AWS IAM<br/>Cross-account"]
    Q2 -->|No / 別組織| Q3{規制業界か<br/>FAPI 2.0?}

    Q3 -->|Yes 金融/医療/政府| P4["P-4 mTLS<br/>必須"]
    Q3 -->|No| Q4{Partner が自社 IdP<br/>保有?}

    Q4 -->|Yes 大企業 Entra/Okta/Auth0| Q5{鍵管理運用<br/>許容?}
    Q4 -->|No SMB / Trial| Q6{セキュリティ強度<br/>高/中?}

    Q5 -->|Yes 鍵運用OK| P3["P-3 JWT Bearer<br/>Grant"]
    Q5 -->|No 楽な方| P2["P-2 Token<br/>Exchange"]

    Q6 -->|高| P1["P-1 OAuth Client<br/>Credentials"]
    Q6 -->|中（低リスク識別のみ）| P5["P-5 API Key<br/>+ Usage Plan"]

    style P4 fill:#f3e5f5
    style P3 fill:#c8e6c9
    style P2 fill:#c8e6c9
    style P1 fill:#bbdefb
    style P7 fill:#bbdefb
    style P6 fill:#ffe0b2
    style P5 fill:#fce4ec
```

### 2.2 想定接続先 × パターン マッピング表（ヒアリング埋め）

顧客が想定する Partner / SaaS の接続先と適用パターンを整理：

| # | 接続先（想定）| 方向 | パターン | セキュリティ要件 | ヒアリング ID |
|:---:|---|:---:|:---:|---|:---:|
| 1 | <span style="color:gray">TBD: 例 Stripe（決済）</span> | Inbound | P-6 HMAC | 機密度高、PCI 関連 | `H-CON-1` |
| 2 | <span style="color:gray">TBD: 例 自社モバイルアプリ Partner</span> | Inbound | P-1 OAuth | 機密度中 | `H-CON-2` |
| 3 | <span style="color:gray">TBD: 例 大企業 Salesforce 連携</span> | Inbound | P-2 Token Exchange | 機密度中-高 | `H-CON-3` |
| 4 | <span style="color:gray">TBD: 例 銀行 API 連携</span> | Inbound | P-4 mTLS | 規制金融 | `H-CON-4` |
| 5 | <span style="color:gray">TBD: 例 SendGrid（メール送信）</span> | **Outbound** | API Key + IP allowlist | 機密度低 | `H-CON-5` |
| 6 | <span style="color:gray">TBD: 例 OpenAI API</span> | **Outbound** | API Key | 機密度中 | `H-CON-6` |
| 7 | <span style="color:gray">TBD: 例 Slack 通知</span> | **Outbound** | OAuth + Webhook | 機密度中 | `H-CON-7` |
| 8 | <span style="color:gray">TBD: 例 AWS Marketplace Partner</span> | 双方向 | P-7 AWS IAM | 機密度高 | `H-CON-8` |

> ✏️ **ヒアリング埋め**：顧客の想定接続先 5-15 件をリストアップ、各々の方向 / パターン / セキュリティ要件を確認。

### 2.3 Inbound / Outbound サマリ

外部 API 連携には **方向が 2 種類**あり、認証の構造が異なる：

| 観点 | Inbound（外部 → 自社）| Outbound（自社 → 外部）|
|---|---|---|
| **代表ユースケース** | Partner B2B システムが自社 API を呼ぶ / SaaS Webhook 受信 | 自社 Lambda が Stripe / SendGrid / OpenAI を呼ぶ |
| **credential 発行者** | **自社認証基盤**（Engine） | **外部 SaaS**（Engine）|
| **credential 保管場所** | Partner 側で保管 | 自社 Secrets Manager |
| **検証実施場所** | 自社 API GW で検証 | 外部 SaaS で検証 |
| **方向別の認証パターン** | P-1〜P-4, P-6, P-7 | API Key / OAuth / Bearer（外部 SaaS 規格に従う）|
| **対抗先との運用関係** | 自社アプリチーム ↔ Partner | 自社アプリチーム ↔ SaaS Vendor |
| **「アプリに寄せる」議論対象** | ⭐ Yes（§2.4-2.5 参照）| ⭐ Yes（§2.4-2.5 参照）|

→ **方向に関わらず、対抗先との運用関係（契約・credential 配布・ローテ調整）はアプリチームに集中する**。これが「アプリ自律性」の正当化根拠。

### 2.4 Outbound（自社 → SaaS）配置比較

自社アプリが外部 SaaS を呼ぶ際の credential 管理を **どこで実装するか**：

#### A. 各アプリで実装（分散モデル）

```
[App A account]
  Lambda → 自 account の Secrets Manager（Stripe credential）→ Stripe

[App B account]
  Lambda → 自 account の Secrets Manager（SendGrid credential）→ SendGrid
```

| 観点 | メリット | デメリット |
|---|---|---|
| **自律性** | ✅ アプリチームが SaaS 選定・契約・credential 取得を完結 | – |
| **リリース連動** | ✅ 新規 SaaS 採用がアプリリリースと同時 | – |
| **責任境界** | ✅ 障害・トラブル対応は自アプリ完結 | – |
| **コスト按分** | ✅ 各 account 課金でクリア | – |
| **ガバナンス** | – | ⚠ Approved SaaS Allowlist を中央で管理する仕組みが必要 |
| **secret 散在** | – | ⚠ N アプリ × N SaaS で credential が分散、棚卸し困難 |
| **ローテ運用** | – | ⚠ アプリチームの実装品質次第、ローテ漏れリスク |
| **DPA / 法務確認** | – | ⚠ 各アプリで個別確認すると重複・漏れ |

#### B. 共通基盤で実装（中央モデル）

```
[共通基盤 account]
  Secrets Manager Vault → SaaS credential 中央管理
    ↑ API
[App A account] Lambda → 共通基盤 API で credential 取得 → Stripe
[App B account] Lambda → 共通基盤 API で credential 取得 → SendGrid
```

| 観点 | メリット | デメリット |
|---|---|---|
| **ガバナンス** | ✅ Approved SaaS / DPA 確認が中央 1 箇所 | – |
| **棚卸し** | ✅ 全社の SaaS 利用一覧化が容易 | – |
| **ローテ運用** | ✅ 中央で標準化 | – |
| **secret 集中管理** | ✅ Vault パターン | – |
| **自律性** | – | ❌ 新規 SaaS 採用は中央承認待ち、リードタイム長 |
| **リリース連動性** | – | ❌ アプリリリースと SaaS credential 設定が別動線 |
| **複雑性** | – | ⚠ 中央 API 経由 = 追加 hop / 追加障害点 |
| **業務適合性** | – | ❌ アプリ固有の SaaS 選定理由を中央が判断するのは困難 |

#### 推奨：A（各アプリ実装）+ 中央ガバナンス補強

| 中央が担保すべきガバナンス | 仕組み |
|---|---|
| **Approved SaaS Allowlist** | Security / Legal レビュー後にカタログ化、Service Catalog テンプレで強制 |
| **Secret 保管標準** | Secrets Manager + CMK + 自動ローテ、Config Rule で強制 |
| **DPA / 法務確認** | 法務台帳 + タグで紐付け、年次棚卸し |
| **コスト可視化** | FinOps タグ + Cost Explorer |
| **検知** | 環境変数 credential を持つ Lambda の deploy 拒否（cfn-guard / Service Catalog）|

→ **「各アプリ実装 + 中央 5 項目ガバナンス」**で自律性とガバナンスを両立。

### 2.5 Inbound（SaaS → 自社）配置比較

外部 Partner が自社 API を呼ぶ際の Engine（OAuth / JWT 発行・検証基盤）を **どこに置くか**：

#### A. 各アプリで実装（分散モデル）

```
[App A account]
  Cognito User Pool A → Partner X 用 M2M client 発行
  API GW → 自 account Cognito Authorizer で検証

[App B account]
  Cognito User Pool B → Partner Y 用 M2M client 発行
  API GW → 自 account Cognito Authorizer で検証
```

| 観点 | メリット | デメリット |
|---|---|---|
| **自律性** | ✅ アプリチームが Pool を所有、運用完全自律 | – |
| **Blast radius** | ✅ 別 account / 別 Pool で完全独立 | – |
| **コスト按分** | ✅ 各 account 課金 | – |
| **AWS native** | ✅ Cognito Authorizer ネイティブ統合 | – |
| **責任境界** | ✅ Pool SLA / 障害対応はアプリチーム責任 | – |
| **Partner UX**（複数アプリ連携時）| – | ❌ Partner が N 個 credential を管理、N 個 token endpoint |
| **P-2 Token Exchange 対応** | – | ❌ Cognito M2M は RFC 8693 未対応 |
| **P-4 mTLS（FAPI 2.0）対応** | – | ❌ Cognito M2M は mTLS at /token 未対応 |
| **Federation**（Partner IdP 信頼台帳）| – | ❌ Cognito 未対応 |
| **追加コスト** | – | ⚠ Cognito M2M Active Client 課金（~¥1,000/月/client）|
| **メモリ整合（既存 Keycloak 確定方向）**| – | ⚠ P-2 / P-3 / P-4 不可になりプラットフォーム選定根拠と矛盾 |

#### B. 共通基盤で実装（中央モデル）

```
[共通基盤 account]
  Keycloak Public Realm  → End User
  Keycloak Partner Realm → 全 Partner（P-1〜P-4 全パターン対応）
    ↓ JWT 発行
[App A account] API GW → JWT 検証
[App B account] API GW → JWT 検証
```

| 観点 | メリット | デメリット |
|---|---|---|
| **Partner UX** | ✅ 1 credential で複数アプリ呼出可（業界標準）| – |
| **P-2 Token Exchange** | ✅ Keycloak ネイティブ対応 | – |
| **P-4 mTLS（FAPI 2.0）**| ✅ Keycloak + mTLS Custom Domain で対応 | – |
| **Federation** | ✅ Partner IdP 信頼台帳一元 | – |
| **ガバナンス** | ✅ 命名規約 / scope policy / 監査 中央 | – |
| **業界標準** | ✅ Auth0 Organizations / Okta CIC と同パターン | – |
| **自律性**（運用関係） | ✅ Self-Service Developer Portal でアプリチーム自律可能 | – |
| **Engine 中央依存** | – | ⚠ Public 障害が Partner に波及（Realm 分離で軽減）|
| **追加コスト** | – | ✅ なし（既存 Keycloak で吸収）|

#### 推奨：B（共通基盤）+ Self-Service Developer Portal

**Engine 機能（OAuth / JWT / Token Exchange / mTLS）は中央、Relationship 運用（契約・credential 配布・ローテ調整）はアプリチーム**という分担で、自律性とガバナンスを両立。

| 役割 | 担当 |
|---|---|
| Engine 提供（共有認証基盤 Partner Realm）| 認証基盤チーム（中央）|
| Self-Service Developer Portal 提供 | 認証基盤チーム（中央）|
| Partner Client 作成（Portal 経由）| **アプリチーム自律** |
| Partner Secret 配布・ローテ | **アプリチーム自律** |
| Partner SLA 管理・契約 | **アプリチーム自律** |

#### 例外：P-1 / P-5 のみで完結する場合の判断

P-2 / P-3 / P-4 が **将来も不要**と判断できる場合のみ、A（各アプリ Cognito）も選択肢になる：

| 判断条件 | Yes なら | No なら |
|---|---|---|
| Token Exchange（RFC 8693）必要か | B 中央 | A 検討可 |
| mTLS / FAPI 2.0 必要か | B 中央 | A 検討可 |
| Partner クロスアプリ連携あるか | B 中央 | A 検討可 |
| 追加コスト ¥100-200 万/年許容か | A 検討可 | B 中央 |

→ **現状要件のヒアリング次第**（`H-PAT-1` 〜 `H-PAT-4`）。

### 2.6 Inbound 配置 4 象限比較（横断ビュー）

| 配置 \ 方向 | Inbound（外部 → 自社）| Outbound（自社 → 外部）|
|---|---|---|
| **各アプリ実装** | ⚠ P-2/P-3/P-4 不可、Partner UX 悪化 | ✅ **推奨**（自律性活用）|
| **共通基盤実装** | ✅ **推奨**（Engine 中央 + Portal で自律担保）| ⚠ 過剰中央化、業務適合性低下 |

→ **Inbound = 共通基盤、Outbound = 各アプリ**の Cross 配置が業界標準。両方とも対抗先運用はアプリチームが所有。

---

## 3. Private について

### 3.1 Private 認証は IAM 単独か？

Private（社内 / 内部）API 認証は **AWS IAM SigV4 が主流だが、他にも選択肢あり**：

| # | 方式 | 対象 | 業界実例 |
|:---:|---|---|---|
| **PR-1** | **AWS IAM SigV4** | AWS-to-AWS（Lambda / ECS / EC2）| AWS native、最一般 |
| **PR-2** | **VPC Lattice Auth Policy** | AWS-to-AWS（クロス VPC / cross-account）| AWS 2023 GA、Service Mesh 代替 |
| **PR-3** | **ECS Service Connect / App Mesh** | ECS 間 mTLS 自動 | Service Mesh パターン |
| **PR-4** | **Resource-based Policy**（S3 / Lambda 等）| AWS 内 Service-to-Service | パッシブ Policy |
| **PR-5** | **OIDC Federation → STS AssumeRole** | 非 AWS Internal（GitHub Actions / on-prem）| IRSA, GitHub OIDC, EKS Pod Identity |
| **PR-6** | **mTLS（Custom Domain）** | 非 AWS Internal（on-prem システム）| Hybrid Cloud, ハイブリッド構成 |
| **PR-7** | **VPN / Direct Connect + IP allowlist** | NW 層認証（補助） | ハイブリッド、Zero Trust 違反のため単独不可 |

→ **Private = IAM 単独ではなく、対象システムの種類で 7 選択肢から選ぶ**。

### 3.2 Private 認証 配置比較

#### A. 各システムで実装（分散モデル）

```
App A → IAM SigV4 で App B の API GW を呼出
App B → IAM SigV4 で App C の API GW を呼出
（各 API GW で AuthorizationType=AWS_IAM）
```

| 観点 | メリット | デメリット |
|---|---|---|
| **AWS native** | ✅ 追加運用ゼロ、AWS SDK 自動署名 | – |
| **レイテンシ** | ✅ 最小（追加 hop なし）| – |
| **コスト** | ✅ 追加コスト基本なし | – |
| **設計シンプル** | ✅ IAM Role の最小権限設計のみ | – |
| **マネージド** | ✅ AWS が証明書ローテ等を運用 | – |
| **Cross-cutting policy** | – | ⚠ retry / circuit breaker / mTLS auto は別途実装 |
| **可観測性** | – | ⚠ Service Mesh 標準メトリクスなし |

#### B. 共通基盤（Service Mesh）で実装（中央モデル）

```
App A → Sidecar Envoy → mTLS auto → App B Sidecar → App B
        ↑ 中央 Control Plane が policy 配布
```

| 観点 | メリット | デメリット |
|---|---|---|
| **Cross-cutting policy** | ✅ retry / timeout / mTLS auto / circuit breaker 一元 | – |
| **可観測性** | ✅ メトリクス / トレース自動 | – |
| **mTLS 自動化** | ✅ 証明書ローテ Mesh が管理 | – |
| **言語非依存** | ✅ アプリコードは認証ロジック不要 | – |
| **運用負荷** | – | ❌ Control Plane / Sidecar の運用負荷大 |
| **レイテンシ** | – | ⚠ Sidecar 経由 +5-20ms |
| **コスト** | – | ❌ Sidecar リソース + Control Plane インフラ |
| **学習曲線** | – | ❌ Istio / App Mesh / Linkerd の専門知識 |

#### C. AWS マネージド（VPC Lattice）— 中間アプローチ

```
App A → VPC Lattice Service → App B
        ↑ Auth Policy（IAM 統合）+ Network 統合
```

| 観点 | メリット | デメリット |
|---|---|---|
| **AWS マネージド** | ✅ Sidecar 不要、Control Plane 不要 | – |
| **IAM 統合** | ✅ Auth Policy で IAM Principal ベース | – |
| **Service Discovery** | ✅ 統合 DNS | – |
| **Cross-VPC / Cross-account** | ✅ 自然対応 | – |
| **mTLS 自動化** | – | ⚠ VPC Lattice は TLS 終端、mTLS は未対応（2026 時点）|
| **業界実績** | – | ⚠ 2023 GA で実績まだ少ない |

#### 配置別 評価まとめ

| 配置 | レイテンシ | 運用負荷 | Cross-cutting Policy | 推奨用途 |
|---|:---:|:---:|:---:|---|
| **A. 各アプリ IAM SigV4** | ✅ 最小 | ✅ 最小 | – | デフォルト推奨 |
| **B. Service Mesh** | ⚠ +5-20ms | ❌ 大 | ✅ 強 | 大規模 mesh / 複雑 routing 要件 |
| **C. VPC Lattice** | ⚠ +少 | ⚠ 中 | ⚠ 中 | Cross-account / Cross-VPC 多 |

#### 推奨：A（各アプリ IAM）+ C（VPC Lattice）のハイブリッド

| シナリオ | 推奨配置 |
|---|---|
| 同一 account 内 Service-to-Service | **A: IAM SigV4** |
| Cross-account / Cross-VPC | **C: VPC Lattice + IAM Auth Policy** |
| 非 AWS Internal（GitHub Actions）| **PR-5: OIDC Federation → STS** |
| 非 AWS Internal（on-prem）| **PR-6: mTLS Custom Domain** |
| 大規模 mesh / Istio 既存資産 | **B: Service Mesh** |

→ **基本は A + C のハイブリッド、Mesh は組織的に既に運用していなければ採用しない**。

### 3.3 Private 配置 ヒアリング項目

| 項目 | 内容 | ID |
|---|---|:---:|
| 想定される Private 連携の対象システム | <span style="color:gray">TBD: AWS-to-AWS / 非 AWS Internal / on-prem</span> | `H-PRV-1` |
| 連携頻度・レイテンシ要件 | <span style="color:gray">TBD: 高頻度 / 低頻度 / リアルタイム</span> | `H-PRV-2` |
| Cross-account / Cross-VPC の有無 | <span style="color:gray">TBD: あり / なし</span> | `H-PRV-3` |
| Service Mesh 既存採用状況 | <span style="color:gray">TBD: あり / なし / 検討中</span> | `H-PRV-4` |
| mTLS 必須要件の有無 | <span style="color:gray">TBD: あり / なし</span> | `H-PRV-5` |

---

## 4. 次のアクション

### 4.1 ヒアリング → 配置確定までのフロー

```mermaid
flowchart TD
    H[ヒアリング実施] --> Fill[§1.2 §2.2 §3.3 の TBD を埋める]
    Fill --> Decide{接続先 × パターンが<br/>確定したか}
    Decide -->|No| MoreH[追加ヒアリング]
    MoreH --> Fill
    Decide -->|Yes| Plan[配置方針 確定]
    Plan --> PoC[PoC 計画策定]
    PoC --> Build[Service Catalog 製品実装]

    style H fill:#fff9c4
    style Plan fill:#c8e6c9
```

### 4.2 配置確定後の PoC 候補

| Phase | 内容 |
|---|---|
| PoC-1 | P-1 OAuth Client Credentials の Inbound 動作検証 |
| PoC-2 | P-2 Token Exchange の Inbound 動作検証（該当する場合）|
| PoC-3 | P-4 mTLS の Inbound 動作検証（該当する場合）|
| PoC-4 | Outbound SaaS（Stripe / SendGrid / OpenAI 等）の credential 管理パターン検証 |
| PoC-5 | Private（IAM SigV4 / VPC Lattice）の Cross-account 動作検証 |

---

## 5. ヒアリング項目総括（チェックリスト）

### 5.1 現状把握（H-CTX）

| ID | 質問 | 確認内容 |
|:---:|---|---|
| `H-CTX-1` | 現状の Public API 認証方式 | 共有認証基盤の有無 / IdP の種類 / JWT 検証実装場所 |
| `H-CTX-2` | 現状の Partner API 認証方式 | 連携 Partner の有無 / 既存方式（API Key / OAuth / mTLS）|
| `H-CTX-3` | 現状の Private API 認証方式 | AWS IAM / VPC Lattice / Service Mesh / その他 |

### 5.2 Partner 想定接続先（H-CON）

| ID | 質問 | 確認内容 |
|:---:|---|---|
| `H-CON-1〜N` | 想定接続先リスト | 5-15 件、方向（In/Out）、業界、規模、機密度 |
| `H-CON-X1` | Partner 数の現状と将来想定 | 現状 / 1 年 / 3 年後の想定 |
| `H-CON-X2` | クロスアプリ Partner の有無 | 1 Partner が複数アプリと連携するか |

### 5.3 Partner 認証方式選定（H-PAT）

| ID | 質問 | 確認内容 |
|:---:|---|---|
| `H-PAT-1` | Token Exchange（RFC 8693）必要性 | Partner が大企業 IdP 保有か、Federation 重視か |
| `H-PAT-2` | mTLS / FAPI 2.0 必要性 | 金融 / 医療 / 政府連携の有無 |
| `H-PAT-3` | Webhook 受信パターン（HMAC）| 外部 SaaS からの push 通知の有無（Stripe / GitHub 等）|
| `H-PAT-4` | AWS IAM Cross-account パターン | Partner が AWS Marketplace 等か |
| `H-PAT-5` | 追加コスト許容範囲 | Cognito M2M ¥100-200 万/年 vs Keycloak 既存吸収 |

### 5.4 Outbound（自社 → SaaS）（H-OUT）

| ID | 質問 | 確認内容 |
|:---:|---|---|
| `H-OUT-1` | 想定 SaaS リスト | 5-15 件、用途、機密度 |
| `H-OUT-2` | DPA / 法務確認状況 | 既に締結済 / 未確認の区分 |
| `H-OUT-3` | Approved SaaS Allowlist 承認プロセス | Security / Legal の関与 |
| `H-OUT-4` | アプリチームの credential 管理運用 | Secrets Manager 既利用 / 環境変数利用 |

### 5.5 Private（H-PRV）

| ID | 質問 | 確認内容 |
|:---:|---|---|
| `H-PRV-1` | 想定 Private 連携対象 | AWS-to-AWS / 非 AWS Internal / on-prem |
| `H-PRV-2` | 連携頻度・レイテンシ要件 | 高頻度 / 低頻度 / リアルタイム |
| `H-PRV-3` | Cross-account / Cross-VPC | 有無 / 規模 |
| `H-PRV-4` | Service Mesh 既存採用 | あり / なし / 検討中 |
| `H-PRV-5` | mTLS 必須要件 | あり / なし |

### 5.6 自律性 vs ガバナンス（H-GOV）

| ID | 質問 | 確認内容 |
|:---:|---|---|
| `H-GOV-1` | アプリチームと認証基盤チームの分離度 | 別組織 / 同組織 / マトリクス |
| `H-GOV-2` | リリース自律性の重要度 | 月次 / 週次 / 任意のタイミング |
| `H-GOV-3` | ガバナンス要件（監査・コンプラ）| PCI / APPI / GDPR / SOC2 |
| `H-GOV-4` | Self-Service Developer Portal 採用可否 | 採用 / 検討 / 不採用 |
| `H-GOV-5` | Two-Track 承認モデル受容 | 日常自律 + 増分リスク承認 OK か |

---

## 改訂履歴

- **2026-06-19 初版**：3 カテゴリ前提 + Partner 7 パターン × ユースケース + 接続先マッピング + Inbound/Outbound 4 象限比較 + Private 7 選択肢比較 + ヒアリング項目総括 30+ 項目を統合。顧客説明可能な水準でドキュメント化、TBD はヒアリング後に埋める前提。

---

## 関連ドキュメント

- [§C-API-6 外部 API 認証アーキテクチャ](../proposal/common/06-external-api-auth-architecture.md) — 本資料の根拠となる標準側 SSOT
- [§FR-API-0 外部 API 実行 6 タイプ](../proposal/fr/00-external-api-consumption-overview.md) — Inbound 詳細
- [§FR-API-2 認証認可詳細](../proposal/fr/02-authn-authz.md) — Engine 機能仕様
- [hearing-checklist.md](../hearing-checklist.md) — 既存ヒアリング項目との統合候補
