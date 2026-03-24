# SSO実装方式の比較と本プロジェクトでの適用

**作成日**: 2026-03-19

---

## 0. そもそも「認証」とは何か

### 0.1 認証の本質

認証（Authentication）とは、**「あなたは本当にあなたですか？」を確認する仕組み**である。

Webシステムにおける認証は、以下の3ステップで成り立つ：

```mermaid
sequenceDiagram
    participant User as ユーザー
    participant App as アプリケーション
    participant Store as 認証情報ストア

    Note over User,Store: ① 資格情報の提示
    User->>App: ID + パスワード（知識情報）<br/>または生体認証（固有情報）<br/>またはデバイス（所持情報）

    Note over App,Store: ② 照合
    App->>Store: 提示された資格情報を照合
    Store->>App: 一致 / 不一致

    Note over User,App: ③ 認証状態の維持
    App->>User: 認証トークン発行<br/>（以降のリクエストで「誰か」を証明）
```

**重要なのは③**である。HTTP自体はステートレス（状態を持たない）なので、毎回パスワードを送るわけにはいかない。
そこで「一度認証に成功したら、その証明書（トークン）を持ち回る」仕組みが必要になる。

### 0.2 なぜ「安全」と言えるのか — トークンの信頼性

認証の安全性は、**「トークンが偽造・改ざんされていないことを、どうやって保証するか」** に集約される。

```mermaid
flowchart TB
    subgraph Danger["❌ 安全でない例"]
        D1["トークン: user=tanaka"]
        D2["→ 攻撃者が user=admin に書き換え"]
        D3["→ サーバーは区別できない"]
        D1 --> D2 --> D3
    end

    subgraph Safe["✅ 安全な仕組み"]
        S1["トークン: {user:tanaka} + 署名"]
        S2["→ 攻撃者が内容を書き換え"]
        S3["→ 署名が不一致 → 検出・拒否"]
        S1 --> S2 --> S3
    end

    style Danger fill:#fff0f0,stroke:#cc0000
    style Safe fill:#d3f9d8,stroke:#2b8a3e
```

各方式でのトークン保護の仕組み：

| 方式 | トークン形式 | 改ざん防止の仕組み | 安全性の根拠 |
|------|------------|-------------------|-------------|
| **サーバーセッション** | セッションID（ランダム文字列） | トークン自体に情報なし、サーバー側DBで照合 | IDが推測不能（十分な長さ + ランダム性） |
| **Cookie暗号化** | 暗号化Cookie | サーバーだけが持つ秘密鍵で暗号化 | 秘密鍵を知らなければ復号・改ざん不可 |
| **JWT（署名付き）** | JSON Web Token | **秘密鍵で電子署名**、公開鍵で検証 | 署名を再生成するには秘密鍵が必要 |

### 0.3 JWT署名の仕組み（フェデレーション方式の安全性の核心）

```mermaid
sequenceDiagram
    participant IdP as IdP（Cognito）<br/>秘密鍵を保持
    participant App as アプリケーション<br/>公開鍵で検証

    Note over IdP: JWT作成
    IdP->>IdP: ヘッダー = {"alg":"RS256"}<br/>ペイロード = {"sub":"tanaka","groups":["admin"]}<br/>署名 = RSA-SHA256(ヘッダー.ペイロード, 秘密鍵)

    IdP->>App: JWT = ヘッダー.ペイロード.署名

    Note over App: JWT検証
    App->>App: 1. 公開鍵で署名を検証<br/>   → 改ざんされていないか？
    App->>App: 2. exp（有効期限）を確認<br/>   → 期限切れでないか？
    App->>App: 3. iss（発行者）を確認<br/>   → 信頼するIdPが発行したか？
    App->>App: 4. aud（対象者）を確認<br/>   → 自分宛のトークンか？

    Note over App: 全て合格 → 認証成功
```

**ポイント**：
- **秘密鍵はIdPだけが持つ** → IdP以外はJWTを発行できない
- **公開鍵は誰でも取得可能**（JWKS endpoint） → どのサーバーでも検証できる
- **トークン内に「誰か」「何の権限か」が含まれる** → サーバー間でDBを共有する必要がない

これが、フェデレーション方式が**分散環境でスケール**する理由である。

### 0.4 認証の3要素と多要素認証（MFA）

| 要素 | 内容 | 例 |
|------|------|-----|
| **知識情報** | 本人だけが知っていること | パスワード、PIN、秘密の質問 |
| **所持情報** | 本人だけが持っていること | スマートフォン、ハードウェアキー、ICカード |
| **生体情報** | 本人自身の特徴 | 指紋、顔認証、虹彩 |

**MFA（多要素認証）** = 上記のうち**2つ以上を組み合わせる**。
パスワード（知識）+ SMS認証コード（所持）のように、1つが漏れても突破されない。

本PoCの構成では、MFAはIdP（Entra ID / Auth0）側で設定する。
Cognito自体もTOTPベースのMFAに対応している。

---

## 0.5 SSO方式別の安全性比較

上記を踏まえ、各SSO方式が「なぜ安全と言えるか/言えないか」を比較する。

| 観点 | エージェント方式 | リバースプロキシ方式 | フェデレーション方式 |
|------|----------------|---------------------|---------------------|
| **トークン形式** | 暗号化Cookie | HTTPヘッダー（平文） | **JWT（署名付き）** |
| **改ざん検知** | Cookie暗号鍵依存 | **検知不可**（ヘッダー信頼） | **署名で検知** |
| **トークン検証に必要なもの** | 共有秘密鍵 | なし（ヘッダー信頼） | **公開鍵のみ** |
| **中間者攻撃への耐性** | 中（Cookie暗号化） | **低**（プロキシバイパスで偽装可能） | **高**（署名で保証） |
| **秘密情報の管理** | 全サーバーで共有鍵 | プロキシのみ | **IdPのみに秘密鍵** |
| **検証の独立性** | 認証サーバーへの通信必要 | プロキシ経由必須 | **オフライン検証可能** |

### なぜフェデレーション方式が優れているのか

```mermaid
flowchart TB
    subgraph Agent["エージェント方式の課題"]
        A1["秘密鍵を全サーバーに配布"]
        A2["1台漏洩 → 全体が危険"]
        A1 --> A2
    end

    subgraph Proxy["リバースプロキシ方式の課題"]
        P1["ヘッダーはプロキシが注入"]
        P2["プロキシをバイパスされると\nヘッダー偽装が可能"]
        P3["全通信がプロキシ経由\n→ ボトルネック"]
        P1 --> P2
        P1 --> P3
    end

    subgraph Fed["フェデレーション方式の強み"]
        F1["秘密鍵はIdPだけが保持"]
        F2["公開鍵で誰でも検証可能"]
        F3["トークン自体が改ざん証明を持つ\n→ 経路に依存しない"]
        F4["分散検証可能\n→ SPOFなし"]
        F1 --> F2
        F2 --> F3
        F3 --> F4
    end

    style Agent fill:#fff0f0,stroke:#cc0000
    style Proxy fill:#fff0f0,stroke:#cc0000
    style Fed fill:#d3f9d8,stroke:#2b8a3e
```

**まとめ**：
- エージェント方式は「鍵の共有」が弱点（漏洩リスクがサーバー数に比例）
- リバースプロキシ方式は「経路の信頼」が弱点（バイパスされたら終わり）
- フェデレーション方式は「トークン自体が信頼を持つ」（経路に依存しない、分散検証可能）

**この「トークン自体に信頼性が内包されている」という性質が、クラウド・マイクロサービス時代にフェデレーション方式が標準となった最大の理由である。**

---

## 1. SSO実装方式の全体分類

SSOの実装方式は大きく5つに分類される。

```mermaid
flowchart TB
    SSO["SSO 実装方式"]

    SSO --> Agent["① エージェント方式\n各サーバーに認証モジュール組込み"]
    SSO --> Proxy["② リバースプロキシ方式\nプロキシ経由で通信集約"]
    SSO --> Federation["③ フェデレーション方式\nSAML/OIDCで標準連携"]
    SSO --> Delegate["④ 代理認証方式\nクライアントSWがID/PW代行入力"]
    SSO --> Transparent["⑤ 透過型方式\nネットワーク機器で通信監視"]

    Federation -->|"本PoCで採用"| Cognito["Cognito + OIDC"]

    style Federation fill:#d3f9d8,stroke:#2b8a3e
    style Cognito fill:#d3f9d8,stroke:#2b8a3e
```

---

## 2. 主要3方式のアーキテクチャ比較

### 2.1 エージェント方式

```mermaid
flowchart LR
    Browser["ブラウザ"] --> WebServer["Webサーバー\n+ エージェント"]
    WebServer <--> AuthServer["認証サーバー"]
    WebServer --> App["アプリケーション"]

    style WebServer fill:#fff0f0,stroke:#cc0000
```

- 各WebサーバーにエージェントSW（モジュール）を導入
- エージェントが認証サーバーと通信し、認証済みCookieを発行
- **代表製品**: CA SiteMinder（Webエージェント）、Oracle Access Manager

| メリット | デメリット |
|---------|-----------|
| ネットワーク構成の変更不要 | 全システムにエージェント導入が必要 |
| サーバー個別にアクセス制御可能 | 対応していないサーバーがある |
| | エージェントのバージョン管理が煩雑 |

### 2.2 リバースプロキシ方式

```mermaid
flowchart LR
    Browser["ブラウザ"] --> Proxy["リバースプロキシ\n（認証処理）"]
    Proxy <--> AuthServer["認証サーバー"]
    Proxy -->|"HTTPヘッダーに\nユーザー情報注入"| App1["Webアプリ A"]
    Proxy -->|"X-Remote-User\nX-User-Groups"| App2["Webアプリ B"]
    Proxy -->|"ヘッダーベース認証"| App3["レガシーアプリ C"]

    style Proxy fill:#f5f0ff,stroke:#6600cc
```

- 全アクセスをリバースプロキシ経由に集約
- プロキシが認証を処理し、バックエンドにはHTTPヘッダーでユーザー情報を渡す
- バックエンドアプリは**ヘッダーを読むだけ**（認証ロジック不要）
- **代表製品**: CA SiteMinder SPS、PingAccess（Gatewayモード）、IBM WebSEAL

| メリット | デメリット |
|---------|-----------|
| **バックエンドアプリの改修不要** | ネットワーク構成の変更が必要 |
| バックエンドを外部から隠蔽 | プロキシがSPOF/ボトルネック |
| 一元的なアクセス制御 | プロキシ直接バイパス対策が必要 |

### 2.3 フェデレーション方式（SAML/OIDC）

```mermaid
flowchart LR
    Browser["ブラウザ"] --> App["アプリケーション\n（OIDC RP / SAML SP）"]
    App <-->|"標準プロトコル\n（OIDC / SAML）"| IdP["IdP\n（Cognito / Entra ID）"]
    IdP -->|"JWT / SAMLアサーション"| App

    style App fill:#d3f9d8,stroke:#2b8a3e
    style IdP fill:#d3f9d8,stroke:#2b8a3e
```

- アプリ自身がSAML SP / OIDC RPとして機能
- 認証はIdP側で処理、トークン/アサーションで認証結果を返す
- **代表製品/サービス**: AWS Cognito、Entra ID、Okta、Keycloak、Auth0

| メリット | デメリット |
|---------|-----------|
| 業界標準プロトコル | アプリ側がSAML/OIDC対応必要 |
| クラウド/SaaS対応が容易 | レガシーアプリには適用困難 |
| スケーラブル（分散型） | |
| クロスドメイン対応 | |

---

## 3. 方式別 詳細比較表

| 観点 | エージェント方式 | リバースプロキシ方式 | フェデレーション方式 |
|------|----------------|---------------------|---------------------|
| **認証処理の場所** | 各サーバー上のエージェント | プロキシサーバー | IdP（認証サーバー） |
| **アプリ改修** | エージェント導入 | **不要** | OIDC/SAML対応必要 |
| **ネットワーク変更** | 不要 | **必要（全通信プロキシ経由）** | 不要 |
| **認証情報の受渡し** | Cookie + セッション | **HTTPヘッダー注入** | JWT / SAMLアサーション |
| **改ざん耐性** | Cookieの暗号化依存 | プロキシバイパス対策必要 | **JWT署名で保証** |
| **スケーラビリティ** | 中 | 低（プロキシがボトルネック） | **高（分散型）** |
| **クラウド/SaaS** | 困難 | 困難 | **標準対応** |
| **レガシー対応** | エージェント対応次第 | **最も容易** | 困難（アプリ改修必要） |
| **導入コスト** | 中 | 高（プロキシ基盤） | 低〜中 |
| **運用コスト** | 高（エージェント管理） | 高（プロキシ運用） | 低（IdPマネージド） |

---

## 4. 本プロジェクトでの適用

### 4.1 採用方式

**フェデレーション方式（OIDC + Cognito）を採用。**

理由：
- 新規開発のシステム（経費精算・出張予約等）→ 設計段階からOIDC対応可能
- API Gateway + Lambda Authorizer → JWT検証で認可
- クラウドネイティブ → SaaSとの連携も標準対応
- Cognito（マネージド）→ 運用コスト最小

### 4.2 リバースプロキシ方式の検討

**基本的に不要。ただし、統合対象にレガシーアプリが含まれる場合はハイブリッド構成を検討。**

```mermaid
flowchart TB
    subgraph Decision["判断フロー"]
        Q1{"統合対象システムは\nOIDC/SAML対応可能か？"}
        Q1 -->|"全て対応可能"| A1["フェデレーション方式のみ\n（本PoCの構成）"]
        Q1 -->|"一部レガシーあり"| A2["ハイブリッド構成\n（下記参照）"]
        Q1 -->|"大半がレガシー"| A3["リバースプロキシ方式\nまたは段階的移行"]
    end

    style A1 fill:#d3f9d8,stroke:#2b8a3e
```

### 4.3 レガシーアプリがある場合のハイブリッド構成（AWS）

AWSでは **ALB + Cognito認証** がリバースプロキシ型SSOの役割を果たす。

```mermaid
flowchart TB
    Browser["ブラウザ"]

    subgraph Modern["新規アプリ（OIDC対応）"]
        SPA["React SPA\n（OIDC RP）"]
        SPA <-->|"OIDC\nAuthorization Code + PKCE"| Cognito
    end

    subgraph Legacy["レガシーアプリ（OIDC非対応）"]
        ALB["ALB\n+ Cognito認証\n（実質リバースプロキシ）"]
        ALB <-->|"OIDC"| Cognito
        ALB -->|"HTTPヘッダー注入\nX-Amzn-Oidc-Identity\nX-Amzn-Oidc-Data\nX-Amzn-Oidc-Accesstoken"| LegacyApp["レガシーWebアプリ\n（改修不要）"]
    end

    Cognito["🔴 Cognito\n（共通IdP）"]

    Browser --> SPA
    Browser --> ALB

    style Modern fill:#d3f9d8,stroke:#2b8a3e
    style Legacy fill:#fff0f0,stroke:#cc0000
```

**ALB + Cognito認証の仕組み**:
1. ブラウザ → ALB にアクセス
2. ALB が Cognito の OIDC 認証フローを実行（ユーザーはCognito Hosted UIにリダイレクト）
3. 認証成功後、ALB がバックエンドに以下のHTTPヘッダーを注入:
   - `X-Amzn-Oidc-Identity`: ユーザーID（sub）
   - `X-Amzn-Oidc-Data`: JWT（ユーザー属性含む）
   - `X-Amzn-Oidc-Accesstoken`: アクセストークン
4. レガシーアプリはこのヘッダーを読むだけ（**アプリ改修不要**）

**メリット**:
- 共通IdP（Cognito）を新規アプリとレガシーアプリで共有
- レガシーアプリのOIDC対応改修が不要
- ALBのマネージドサービスでプロキシ運用不要

### 4.4 確認すべき事項（本番設計時）

| 確認項目 | 影響 |
|---------|------|
| 統合対象にOIDC/SAML非対応のWebアプリがあるか | ハイブリッド構成の要否判断 |
| 既存のSiteMinder等のWAM基盤があるか | 移行計画の策定が必要 |
| オンプレミスのWebアプリを統合するか | ALBでは対応不可、別途検討が必要 |

---

## 5. まとめ

| 結論 | 詳細 |
|------|------|
| 本PoCの方式 | フェデレーション方式（OIDC + Cognito）で正しい |
| リバースプロキシ方式の検討 | 新規システムのみなら不要 |
| レガシー対応が必要な場合 | ALB + Cognito認証でハイブリッド構成が可能 |
| 長期的方針 | レガシーアプリも段階的にOIDC対応に改修し、リバースプロキシ型は過渡的手段とする |

---

## 参考

- [SSOの認証方式の仕組みを解説（kamome-e.com）](https://solution.kamome-e.com/blog/archive/blog-sso-idm-20211125/)
- [Reverse-Proxy SSO vs. SAML/OIDC (SSOJet)](https://ssojet.com/blog/reverse-proxy-sso-vs-saml)
- [ALB + Amazon Cognito Authentication (AWS Docs)](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/listener-authenticate-users.html)
- [oauth2-proxy (GitHub)](https://github.com/oauth2-proxy/oauth2-proxy)
