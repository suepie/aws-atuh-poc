# §FR-1 認証

> 上位 SSOT: [00-index.md](00-index.md)   
> 詳細: [../../functional-requirements.md §1](../../functional-requirements.md)   
> カバー範囲: FR-AUTH §1.1 認証フロー / §1.2 パスワード・ローカルユーザー管理

---

## §FR-1.0 前提と背景

### 用語整理

| 用語 | 本基盤での意味 |
|---|---|
| **認証**（Authentication） | 「誰であるか」を確認する行為。認可（Authorization、「何ができるか」）とは別物 |
| **Grant Type** | OAuth 2.0 が定める認証フローの種類（Authorization Code / Client Credentials / Device Code 等） |
| **PKCE**（Proof Key for Code Exchange、RFC 7636） | Authorization Code Grant の盗難対策。OAuth 2.1 で必須化 |
| **ローカルユーザー** | フェデレーション IdP を経由せず、本基盤の User DB に直接登録されているユーザー。**ただし誰をローカルユーザーとして扱うかは [§FR-1.2.0.0](#fr-1200-ローカルユーザーとは何か--利用者カテゴリ別の分析) で利用者カテゴリ別に検討する** |
| **利用者カテゴリ** | 本基盤の利用者を性格別に分けた区分（P-1 基盤運用管理者 / P-2 テナント管理者 / P-3 現行で IdP があった従業員 / P-4 現行で IdP がなかった従業員 ※旧 P-5 ゲスト/外部協力者 統合）。**B2C は本基盤対象外**。詳細は [§FR-1.2.0.0](#fr-1200-ローカルユーザーとは何か--利用者カテゴリ別の分析) |
| **Break Glass account** | IdP 障害時の最終防衛線として残す最小限のローカル管理者。大手 IaaS/SaaS の管理層で標準採用 |
| **BFF**（Backend For Frontend） | SPA のトークンをブラウザに置かず、サーバー側で保管するパターン |
| **NIST SP 800-63B Rev 4** | パスワード・MFA に関する米国政府ガイドライン（2024）。業界標準 |

### なぜここ（§FR-1）で決めるか

```mermaid
flowchart LR
    S1["§FR-1 認証 ← イマココ<br/>(認証フロー / パスワード)"]
    S2["§FR-2 フェデレーション<br/>(外部 IdP)"]
    S3["§FR-3 MFA"]
    S4["§FR-4 SSO"]
    S6["§FR-6 認可<br/>(JWT)"]

    S1 --> S2
    S1 --> S3
    S1 --> S4
    S1 --> S6

    style S1 fill:#fff3e0,stroke:#e65100
```

§FR-1 は **「どんな認証フローを受け入れる基盤か」** と **「ローカルユーザーをどう管理するか」** の 2 つを決める章。
- **§FR-1.1 認証フロー**: 外部から本基盤を呼び出すときの OAuth/OIDC 仕様 → §FR-2 以降の前提
- **§FR-1.2 パスワード**: ローカルユーザーのパスワードポリシー → §FR-3 MFA と組み合わせて「絶対安全」を実現

### §FR-1.0.A 本基盤の認証スタンス

> **OAuth 2.1 / OIDC 1.0 業界標準に徹底準拠する。Implicit / ROPC は採用しない。SPA は BFF パターンを推奨、PKCE 直接も併記。パスワードは NIST SP 800-63B Rev 4 準拠で「どんな顧客要件にも対応可」を担保する。**

### 共通認証基盤として「認証」を検討する意義

| 観点 | 個別アプリで実装した場合 | 共通認証基盤で実装した場合 |
|---|---|---|
| OAuth/OIDC 実装 | アプリごとに実装ばらつき | **基盤側で標準準拠、アプリは JWT を信じるだけ** |
| パスワードポリシー | アプリごとに別ルール → UX/セキュリティ品質バラバラ | **基盤側で一元定義、全顧客に共通適用** |
| 業界標準追従（OAuth 2.1 等） | 全アプリ追従が必要 | **基盤側 1 回でアプリ全体に反映** |
| AAL2 / AAL3 適合 | アプリごとに対応 → 弱い箇所が天井 | **基盤側で集約、全システムで同レベル保証** |

→ 認証を共通基盤に集約することで、**個別アプリでは到達不可能な統一レベルのセキュリティ・UX**を全アプリに提供。

### 本章で扱うサブセクション

| サブセクション | 内容 | 関連 FR |
|---|---|---|
| §FR-1.1 認証フロー / Grant Type | OAuth 2.0 / OIDC のフロー範囲、クライアント種別ごとの推奨、SPA の BFF 採否 | FR-AUTH-001〜008 |
| §FR-1.1.A BFF と DPoP の補完関係 | B-108（BFF）と B-109（DPoP）は別軸の対策、両者の脅威モデル比較、業界推奨、併用パターン | FR-AUTH-002 / FR-AUTH-015 想定 |
| §FR-1.2.0 ローカルユーザー認証の主体 | **§FR-1.2.0.0 ローカルユーザーの定義**（利用者カテゴリ P-1〜P-4 / 範囲シナリオ α〜δ）+ 共通基盤集約 / 各アプリ独自 / ハイブリッドの選択 + §FR-1.2.0.B クロスアカウント運用モデル | — |
| §FR-1.2 パスワード・ローカルユーザー管理 | パスワードポリシー、リセット、ロックアウト等 | FR-AUTH-009〜014 |

---

## §FR-1.1 認証フロー / Grant Type（→ FR-AUTH §1.1）

> **このサブセクションで定めること**: 本基盤がサポートする OAuth 2.0 / OIDC の認証フロー（Grant Type）の範囲、クライアント種別ごとに採用するフローのマッピング。   
> **主な判断軸**: 御社のクライアント種別（SPA / SSR / Mobile / M2M）、SPA で BFF 採用可否、Token Exchange / Device Code / mTLS のオプション要否   
> **§FR-1 全体との関係**: §FR-1 のうち「**認証プロトコル層**」を確定する。パスワード管理ポリシー（§FR-1.2）とは独立に判定可能

### ベースライン

**クライアント種別ごとの推奨フロー**:

| クライアント種別 | 推奨フロー | 標準 | 補足 |
|---|---|---|---|
| ローカルユーザー直接 | ID/PW（Hosted UI） | — | Broker のログイン画面で受付 |
| **SPA（ブラウザ）** | **2 案併記**：(a) BFF パターン / (b) Authorization Code + PKCE 直接 | RFC 6749 + RFC 7636 | BFF が業界推奨。トークンをブラウザに置かない |
| SSR Web | Authorization Code + **PKCE** + client_secret | RFC 6749 + RFC 7636 | OAuth 2.1 で confidential client でも PKCE 必須 |
| ネイティブモバイル | Authorization Code + PKCE（AppAuth 等） | RFC 6749 + RFC 7636 + RFC 8252 | OS 標準ブラウザ経由 |
| M2M（バッチ / サービス間） | Client Credentials | RFC 6749 §FR-3.4 | Resource Server + scope 設計が必要 |

**採用しないフロー**:
- **ROPC（Password Grant）**: OAuth 2.1 で正式削除。本基盤では Won't
- **Implicit Flow**: OAuth 2.1 で正式削除。本基盤では非対応

**オプション（要件次第で採用判定）**:
- **Device Code Flow（RFC 8628）**: CLI / IoT / Smart TV / **AI Agent** など入力制約デバイス向け
- **Token Exchange（RFC 8693）**: マイクロサービス間のユーザー文脈伝播（On-Behalf-Of）、API Gateway でのトークン変換
- **mTLS Client Authentication（RFC 8705）**: FAPI 準拠、金融、高セキュリティ M2M。PKI / TLS 終端制御が必要
- **DPoP（RFC 9449、Demonstrating Proof-of-Possession）**: Access Token の盗難対策（sender-constrained tokens）。**mTLS の代替として 2026 年から enterprise 採用が急増**（Auth0 2026-03 GA、Spring Security 6.5、Keycloak 26.4 対応）。FAPI 2.0 で mTLS と同等の選択肢。**TLS 終端制御不要、PKI 不要**で SPA / Mobile からも利用可能 → mTLS よりも実装ハードルが低い

**業界標準との整合**:

| 動向 | 状態 | 本ベースラインへの反映 |
|---|---|---|
| OAuth 2.1（draft-ietf-oauth-v2-1-15） | IETF Internet Draft。Spring Security 等は既に準拠実装 | 全 confidential client でも PKCE 必須化 |
| Implicit Flow / ROPC 削除 | OAuth 2.1 で正式削除 | Won't として明示 |
| SPA = BFF パターン推奨 | Curity / Duende / Auth0 / WorkOS 等が推奨 | SPA で 2 案併記 |
| Device Code = AI Agent 認証 | 入力制約デバイスの典型 + AI Agent でも採用増加 | オプションに位置付け |

### TBD / 要確認

**A. クライアント種別の特定（影響：基盤の Must 機能範囲）**

| 確認項目 | 回答形式 |
|---|---|
| 御社の SPA システムは？（React / Vue / Angular 等） | システム名と件数 |
| SSR Web は？（Next.js / Spring MVC / Django / Rails 等） | 同上 |
| ネイティブモバイル（iOS / Android）は？ | 有無 + 件数 |
| バッチ・サービス間 API 呼び出しは？ | 有無 + 件数 |

**B. SPA の認証方式選定（影響：アーキテクチャ複雑性 vs セキュリティ強度）**

##### B-1. BFF パターン vs 従来の PKCE 直接 比較表

| 観点 | 従来（PKCE 直接） | BFF パターン |
|---|---|---|
| **Access / Refresh Token 保管** | ブラウザ（メモリ / Storage）| BFF サーバー側（DB 暗号化）|
| **ブラウザが持つもの** | Token そのもの | セッション ID（HttpOnly Cookie）|
| **XSS による Token 漏洩** | ⚠ リスクあり（localStorage / メモリ盗難）| ✅ 防御（Cookie は JS 不可触）|
| **Refresh Token 盗難リスク** | ⚠ 長期間なりすまし可能 | ✅ Refresh Token はサーバー側のみ |
| **CSRF 攻撃** | ✅ Bearer ヘッダー方式で耐性 | ⚠ Cookie 認証で要対策（SameSite=Strict + CSRF トークン）|
| **NIST AAL2 / AAL3 適合** | △ 条件付き | ✅ 整合 |
| **業界推奨度（2026 IETF）** | △ レガシー扱い、低リスクのみ | ✅ **gold standard** |
| **アーキテクチャ複雑度** | ✅ 単純（SPA + 認可サーバー）| ⚠ BFF サーバー + セッションストア追加 |
| **必要なインフラ** | SPA ホスティングのみ | + Lambda or ECS + DynamoDB + KMS |
| **月額コスト目安（10K MAU）** | $0〜数ドル | $20〜50（小規模 Lambda 構成）|
| **実装言語の自由度** | SPA フレームワーク次第 | サーバー側で自由（Node/Python/Java 等）|
| **既存 SPA からの移行コスト** | — | 中（認証部分のみ書き換え、段階移行可）|
| **OAuth 2.1 整合（Confidential Client + PKCE）** | △ Public Client | ✅ Confidential Client |
| **Cookie ドメイン制約** | なし（Bearer ヘッダー）| 同一サイト前提（推奨）|
| **デバッグ性** | ブラウザツールで Token 直接確認可 | サーバー側ログ参照必要 |

##### B-2. 採用判断のガイドライン

```mermaid
flowchart TB
    Start["対象システムの<br/>セキュリティ要件評価"]
    Q1{"XSS リスク<br/>(third-party JS / WYSIWYG 等)"}
    Q2{扱うデータ機密性}
    Q3{"BFF 運用体制<br/>(Lambda/ECS 運用可)"}
    BFF["BFF 採用"]
    PKCE["PKCE 直接<br/>+ XSS 対策強化<br/>(CSP / SRI / Sanitizer)"]
    HYB["ハイブリッド<br/>(高機密パスのみ BFF)"]

    Start --> Q1
    Q1 -->|高 or 不明| BFF
    Q1 -->|低| Q2
    Q2 -->|金融 / 医療 / 個人情報多用| BFF
    Q2 -->|社内ツール限定| Q3
    Q2 -->|システム間で混在| HYB
    Q3 -->|あり| BFF
    Q3 -->|なし| PKCE

    style BFF fill:#fff3e0
    style HYB fill:#fff8e1
    style PKCE fill:#e8f5e9
```

##### B-3. 本基盤としての方針案

| 顧客 / システム種別 | 推奨方式 |
|---|---|
| 金融 / 医療 / 行政 / 個人情報多用 SaaS | **BFF 採用必須** |
| B2B SaaS（一般業務） | **BFF 推奨**（基本方針「絶対安全」と整合）|
| 社内ツール / 機密性低 | PKCE 直接でも可（XSS 対策強化前提）|
| AI Agent / CLI / Mobile | PKCE 直接（Device Code 含む、BFF 不要）|

##### B-4. 段階移行・ハイブリッド運用について

既存 SPA がある場合は **PKCE → BFF への段階移行が可能**。
また、**システムごとに方式を選択（ハイブリッド運用）**も技術的に可能：

- 共通認証基盤（Cognito User Pool / Keycloak Realm）に **SPA Client（Public）と BFF Client（Confidential）を両方登録**しておけば、システムごとにどちらを使うか自由選択
- 例：「経費精算は PKCE 直接、人事システムは BFF」のような混在運用
- SSO は両方で機能（同一 IdP 内 SSO セッションを共有）

実装詳細・制約・運用上の注意点は内部技術メモ [`bff-implementation-notes.md`](../../../common/bff-implementation-notes.md) 参照。

---

→ 金融・医療・行政系なら BFF、社内ツール系なら PKCE 直接で十分というのが現場感覚。**システム種別ごとに方式を分けるハイブリッド運用も可能**。

##### B 補足: BFF パターンの実装可否（参考）

BFF パターンを採用する場合の補足情報:

- **両プラットフォームで実装可能**: Cognito / Keycloak のどちらも**認可サーバー側に Confidential Client を 1 つ追加するだけ**で対応可能（PoC からの差分は小）
- **本基盤での標準実装**: AWS Lambda + API Gateway + DynamoDB（既存 PoC の Lambda Authorizer 構成と統一）。ECS Fargate / Lambda Function URL も選択肢
- **既存リソースへの影響なし**: 既存の Lambda Authorizer / Backend Lambda は変更不要、BFF は「フロントとバックエンド API の間に挟む」追加レイヤー
- **段階移行**: 既存 PKCE 直接 SPA と BFF 構成を並列稼働 → 段階的に移行可能

##### B 補足-2: BFF の AWS アカウント配置と Lambda Authorizer との違い

> **よくある誤解**: 「**BFF は Lambda Authorizer のようなもの**」と捉えがちだが、**両者は別レイヤー**で組み合わせて使うのが標準。

**配置先 AWS アカウント**:

| コンポーネント | 配置先 AWS アカウント | 理由 |
|---|---|---|
| 認可サーバー（Cognito / Keycloak）| **共通基盤アカウント** | 全アプリ共通の認証 SaaS 的存在 |
| JWKS Endpoint | **共通基盤アカウント** | 公開鍵配布、複数アプリから参照 |
| **BFF**（Lambda / ECS）| **アプリ AWS アカウント** | アプリの SPA 専用セッション管理、アプリ実装の一部 |
| **セッションストア**（DynamoDB / Redis）| **アプリ AWS アカウント** | session_id ↔ token のマッピング保管（KMS 暗号化）|
| Lambda Authorizer | **アプリ AWS アカウント** | API Gateway の JWT 検証ゲート |
| Backend Lambda / ECS | **アプリ AWS アカウント** | 業務ロジック |

→ **BFF とセッションストアと Lambda Authorizer はすべてアプリ側 AWS アカウント**に配置。共通基盤アカウントは認可サーバー + JWKS のみ。

**BFF と Lambda Authorizer の責務の違い**:

| 観点 | BFF | Lambda Authorizer |
|---|---|---|
| **主機能** | OAuth フロー実行 + トークン保管 + **セッション Cookie 発行** | API Gateway 受付時の **JWT 署名検証 + 認可判定** |
| **入力** | ブラウザからの HTTP リクエスト + **セッション Cookie** | API Gateway からの **JWT (Authorization ヘッダー)** |
| **出力** | バックエンド API へのプロキシ + ブラウザへの応答 | API Gateway への **allow / deny ポリシー** |
| **状態保持** | あり（**セッションストア / トークンキャッシュ**）| なし（リクエストごとに JWT 検証）|
| **使用プロトコル** | OAuth 2.0 Client (Confidential) | JWT 検証（RFC 7519）|
| **役割の例え** | **ブラウザ用フロントドア** | **API のセキュリティガード** |

→ **BFF は Lambda Authorizer の代替ではなく追加レイヤー**。両方をアプリ側に置く構成が標準。

**全体フロー（BFF + Lambda Authorizer の組み合わせ、クロスアカウント表現）**:

```mermaid
sequenceDiagram
    participant User as エンドユーザー
    participant SPA as SPA<br/>(ブラウザ)
    participant BFF as BFF<br/>(アプリAWS)
    participant Store as セッション<br/>ストア<br/>(アプリAWS)
    participant Auth as 認可サーバー<br/>(共通基盤AWS)
    participant APIGW as API Gateway<br/>(アプリAWS)
    participant Authz as Lambda Authorizer<br/>(アプリAWS)
    participant Backend as Backend Lambda<br/>(アプリAWS)

    Note over User,Backend: ① ログインフロー
    User->>SPA: アクセス
    SPA->>BFF: /login
    BFF->>Auth: Authorization Code + PKCE 認可リクエスト
    Auth->>User: ログイン画面
    User->>Auth: 認証情報 + MFA
    Auth->>BFF: Authorization Code
    BFF->>Auth: Code + PKCE verifier
    Auth->>BFF: Access Token + Refresh Token + ID Token
    BFF->>Store: トークンを KMS 暗号化保管
    BFF->>SPA: HttpOnly Cookie (session_id)

    Note over User,Backend: ② API 呼び出しフロー
    User->>SPA: 業務操作
    SPA->>BFF: /api/foo + session cookie
    BFF->>Store: session_id → トークン取得
    BFF->>APIGW: GET /foo + Authorization Bearer JWT
    APIGW->>Authz: JWT 検証要求
    Authz->>Auth: JWKS 取得 (キャッシュ済)
    Authz->>APIGW: allow + 認可コンテキスト
    APIGW->>Backend: GET /foo + コンテキスト
    Backend->>APIGW: レスポンス
    APIGW->>BFF: レスポンス
    BFF->>SPA: レスポンス
```

→ **二重防御**: ブラウザは JWT に一切触れず（BFF が隠蔽）、API Gateway は JWT で守られる（Lambda Authorizer が検証）。**XSS 経由のトークン盗難リスクをほぼゼロ化**できる。

→ 「採用するか / しないか」の方向性合意のみ本資料で扱い、**実装詳細・構成図・移行プランは内部技術メモ [`bff-implementation-notes.md`](../../../common/bff-implementation-notes.md) に分離**。

**C. オプションフローの要否（影響：プラットフォーム選定に直結）**

| 要件 ID | フロー | 要否確認の問い | 影響 |
|---|---|---|---|
| FR-AUTH-005 | Token Exchange | マイクロサービス間でユーザー文脈を伝播させたい呼び出しがあるか（詳細な業務質問・判定フローは **[§FR-6.3 マイクロサービス間トークンリレー](06-authz.md#fr-63-マイクロサービス間トークンリレー--ユーザー文脈伝播--fr-authz--fr-auth-005)** 参照）| **Yes → Keycloak 必須**（Cognito 非対応）|
| FR-AUTH-006 | Device Code | CLI / IoT / Smart TV / AI Agent クライアントを認証する予定があるか | **Yes → Keycloak 必須** |
| FR-AUTH-007 | mTLS | FAPI 準拠 / 金融取引 / 高セキュリティ M2M の要件があるか | **Yes → Keycloak 必須** |
| FR-AUTH-015（新規想定）| **DPoP（RFC 9449）** | sender-constrained tokens / FAPI 2.0 準拠 / 高セキュリティ API があるか（mTLS の代替として）| **Yes → Keycloak 必須**（Keycloak 26.4 ネイティブ対応、Cognito は標準非対応）|

これらが 1 つでも Yes なら、Cognito 単独では実現できないため、**Keycloak（または併用）が必須**になります。

### §FR-1.1.A BFF と DPoP の補完関係

> **このサブ・サブセクションで定めること**: BFF パターン（[B-108](../../hearing-checklist.md) で問う SPA 認証方式）と DPoP（[B-109](../../hearing-checklist.md) で問う Sender-Constrained Token）は **別軸の対策で補完関係**にあることを明示し、両者の対象範囲・推奨パターン・併用ケースを整理。   
> **主な判断軸**: ブラウザ層 XSS 対策（BFF が強い）vs トークン使用全体の防御（DPoP が強い）、M2M / モバイル統合の要否、FAPI 2.0 準拠要否   
> **§FR-1.1 内の位置付け**: B-108 と B-109 を**別軸として両方確認**するための背景整理

#### よくある誤解：「BFF があれば DPoP は不要」

```
❌ 誤: BFF を採用すれば SPA のトークン盗難リスクは解消するので、DPoP は不要
✅ 正: BFF と DPoP は守る対象が異なる。重なる部分もあるが、それぞれ独自の領域を持つ
```

#### 脅威モデル比較

| 攻撃 | BFF | DPoP |
|---|:---:|:---:|
| **XSS で LocalStorage / メモリからトークン盗難** | ✅ 完全に防ぐ（ブラウザにトークン無し） | ⚠ 鍵保管次第（後述）|
| **盗まれたトークンを別端末で使う**（Sender-Constrained）| △ 既に盗めないので問題化しない | ✅ **強力に防御** |
| **異なる API エンドポイントへのリプレイ** | × 該当しない | ✅ `htm` / `htu` で防御 |
| **M2M（サーバー間）のトークン盗難** | × **BFF はエンドユーザー向け、M2M は対象外** | ✅ M2M でも統一適用可 |
| **モバイル端末紛失時の流用** | × 該当しない | ✅ Keystore / Secure Enclave で防御 |
| **DPoP の秘密鍵自体が盗まれる**（XSS 経由）| × 該当しない | ⚠ WebCrypto non-extractable でも JS から `signMessage` 呼び出し可能 |
| **BFF サーバー自体の侵害** | ⚠ 防御不可（インフラ層）| × 該当しない |
| **IdP 側 SSO セッション乗っ取り**（外部 IdP Cookie 漏洩）| ❌ 防げない | ❌ 防げない |

→ **BFF はブラウザ層の攻撃に強い、DPoP はトークン使用全体に強い**。

#### DPoP の「隠れた弱点」：ブラウザでの鍵保管問題

DPoP の秘密鍵をブラウザでどう保管するかで XSS 耐性が大きく変わる:

| 保管方法 | XSS 耐性 | 備考 |
|---|:---:|---|
| `localStorage` / `sessionStorage` | ❌ 弱 | XSS で簡単に抜き取り可能 |
| `IndexedDB` | ❌ 弱 | 同上 |
| **WebCrypto API の non-extractable key**（推奨）| ⚠ **限定的に強い** | 鍵は取り出せないが、**XSS 攻撃者は JS から `signMessage()` を呼んで proof 作成可能** |
| Service Worker 内に隔離 | △ 中 | ブラウザ実装依存 |

→ **DPoP は「別端末への持ち出し」は完全防御するが、「当該ブラウザ上での悪用」は限定的**（[InfoQ: The DPoP Storage Paradox](https://www.infoq.com/articles/dpop-key-storage-unsolved-problem/)）。BFF の XSS 耐性は "根本的"、DPoP の XSS 耐性は "Sender-Constrained 領域に限定的"。

#### 業界の見解（2026 時点）

| 推奨元 | 立場 |
|---|---|
| **IETF OAuth Security BCP** | 両方推奨。**BFF を優先**、技術的に使えない場合 DPoP |
| **IETF / Curity / Duende**（2025〜）| **BFF を gold standard** |
| Auth0 / Okta / Microsoft | DPoP は「BFF の補完 / BFF 不可時の代替」 |
| **FAPI 2.0**（金融グレード API）| **DPoP 必須**（または mTLS） |

#### 推奨される使い分け

| シナリオ | 推奨 | 理由 |
|---|:---:|---|
| **SPA 単独の B2B SaaS**（業務系一般）| **BFF** | 業界 gold standard、XSS 完全防御 |
| **モバイル + SPA の混在** | **DPoP** | BFF は SPA 用、モバイル統一には DPoP |
| **M2M（サーバー間連携）が中心** | **DPoP** または **mTLS** | BFF は M2M に該当しない |
| **FAPI 2.0 準拠が必須**（金融）| **DPoP**（または mTLS）| 仕様で必須 |
| **規制業種・最高セキュリティ** | **BFF + DPoP 併用** | 多層防御（BFF が SPA 隠蔽、BFF → API で DPoP）|
| 一般業務系 + Sender-Constrained 不要 | **Bearer + 短 TTL** | 業界一般、コスト最適 |

#### B-108 と B-109 の使い分け

ヒアリング項目として:

| ID | 何を聞いているか | 関係 |
|---|---|---|
| **B-108 SPA 認証方式（BFF vs PKCE 直接）** | XSS 耐性。SPA に絞った話 | 主にブラウザ層 |
| **B-109 DPoP 採用要否** | Sender-Constrained Token 全般（M2M / モバイル含む）| トークン使用全体 |

→ **両者は別軸で、両方確認すべき**。「BFF を採用するから DPoP は不要」とは限らない（M2M がある場合 / FAPI 2.0 必要な場合）。

#### 実装負荷の比較

| 観点 | BFF | DPoP |
|---|---|---|
| SPA / モバイル クライアント実装 | **軽**（Cookie + 通常 HTTP）| **中〜重**（鍵生成 + Proof 署名 + jti 管理）|
| 認可サーバー設定 | 通常 OIDC（**軽**）| Keycloak: 軽（Admin Console 1 スイッチ）/ **Cognito: 不可** |
| リソースサーバー検証 | JWT 検証のみ（**軽**）| JWT + Proof 検証 + jti キャッシュ（**中**）|
| サーバーインフラ追加 | **BFF サーバー必須**（重） | **不要**（軽）|
| ライブラリ成熟度 | **◎ 非常に成熟**（`oauth2-proxy` / `next-auth` 等）| △ 発展中（[oauth4webapi](https://github.com/panva/oauth4webapi) 等）|
| 全体重心 | **サーバー側に重心** | **クライアント側に重心** |

→ **総コストは同等程度**、ただし重心が違う。BFF はサーバーインフラ追加、DPoP はクライアント実装の複雑化。

#### 本基盤での推奨方針

| 段階 | 推奨 |
|---|---|
| **デフォルト** | SPA → BFF（[B-108](../../hearing-checklist.md)）、M2M / モバイル無しなら DPoP 不要 |
| **モバイル / M2M / FAPI 2.0 が必要になった場合** | DPoP を追加検討（Keycloak 必須化） |
| **金融・規制業種** | BFF + DPoP 併用（多層防御）|

詳細実装パターンは [bff-implementation-notes.md §11.3](../../../common/bff-implementation-notes.md) 参照。

### 参考資料（業界動向の裏どり）

- [OAuth 2.1 (oauth.net)](https://oauth.net/2.1/)
- [OAuth 2.1 vs 2.0 - Stytch](https://stytch.com/blog/oauth-2-1-vs-2-0/)
- [OAuth 2.1: What's new - WorkOS](https://workos.com/blog/oauth-2-1-whats-new)
- [SPA Best Practices - Curity](https://curity.io/resources/learn/spa-best-practices/)
- [Web App Security Best Practices 2025 - Duende](https://duendesoftware.com/blog/20250805-best-practices-of-web-application-security-in-2025)
- [Device Authorization Grant - WorkOS](https://workos.com/blog/oauth-device-authorization-grant)
- [Token Exchange Why and How - Curity](https://curity.medium.com/token-exchange-in-oauth-why-and-how-to-implement-it-a7407367cb55)

---

## §FR-1.2.0 ローカルユーザー認証の主体（→ §1 アーキテクチャと連動）

> **このサブセクションで定めること**: 「ローカルユーザー」が**そもそも何を指すか**を定義したうえで、**どのカテゴリのユーザーをローカルとして基盤側に持つか**、および **その認証を共通基盤側で行うか各アプリ側で行うか**という認証主体の選択。   
> **主な判断軸**: ローカルユーザー範囲の定義、基本方針整合（特に「絶対安全」「効率よく」「運用負荷低」）、既存システムの認証実装の有無、移行戦略   
> **§FR-1 全体との関係**: §FR-1.2.0 が**前提のスタンス**、§FR-1.2 以降が**具体ポリシー**。**ローカルユーザーの定義と範囲が決まらないと §FR-1.2 のポリシー議論は意味を持たない**

### §FR-1.2.0.0 ローカルユーザーとは何か — 利用者カテゴリ別の分析

> **詳細は [ADR-029 ローカルユーザーの定義 — 利用者カテゴリと範囲シナリオ](../../../adr/029-local-user-categories-and-scope-scenarios.md) を参照**

> **このサブ・サブセクションで定めること**: 「ローカルユーザー」を素朴に扱う前に、**利用者カテゴリ P-1〜P-4（人間ユーザー）+ I-1〜I-5（インフラ運用）+ M-1〜M-5（M2M）+ T-1〜T-2（脅威）** を整理してから「どこまでをローカルにするか」のシナリオ（α/β/γ/δ）を選ぶ。あわせて「アプリ集約 3 選択肢（A 共通基盤集約 / B 各アプリ独自 / C ハイブリッド）」も確定する。
> **主な判断軸**: ターゲット顧客層（中小 vs エンタープライズ）、IdP 普及率、業界規制
> **§FR-1.2.0 内の位置付け**: §FR-1.2.0 の前提となる「誰がローカルユーザーで、どう集約するか」の根本判断

#### 結論サマリ

| 項目 | 採用方針 |
|---|---|
| **ローカルユーザー範囲** | **シナリオ γ（管理者層のみローカル）を第一推奨**、現実的フォールバックは β |
| **不採用** | α（全カテゴリローカル）/ δ（Break Glass のみ）|
| **管理者層 P-1** | 弊社内 IdP + Break Glass 用 2-3 名のローカル管理者 |
| **管理者層 P-2** | 顧客 IdP 推奨、IdP なし顧客はローカル許容 |
| **アプリ集約** | **A. 共通基盤集約（Must）**。B 各アプリ独自は不採用（Won't）、C ハイブリッドは移行期限定 |

#### 利用者カテゴリ全体マップ

| カテゴリ | 想定数 | 自然な認証方式 |
|---|---|---|
| **P-1. 基盤運用管理者** | 弊社運用チーム数〜数十名 | 弊社内 IdP（Entra ID 等）連携 / Break Glass 用ローカル |
| **P-2. テナント管理者** | 顧客数 × 1-数名 | 顧客 IdP（推奨）/ ローカル（妥協）|
| **P-3. 現行で IdP があった従業員** | 顧客数 × 数百〜数千（**最大ボリューム**）| **顧客 IdP（フェデ）** |
| **P-4. 現行で IdP がなかった従業員**（※旧 P-5 ゲスト/外部協力者 統合）| 一部顧客 × 数十〜数百 | ローカル / 顧客に IdP を持ってもらう |

> **対象外**: 旧 P-6 B2C エンドユーザーは**本基盤対象外**（B2B SaaS 専用、2026-06-24 確定）。

#### 4 カテゴリ責務分担サマリ（詳細は ADR-029）

| カテゴリ | 認証提供主体 | 関連 |
|:---:|---|---|
| **A. 人間ユーザー（P-1〜P-4）** | 本基盤（Cognito / Keycloak）| §FR-1.2.0 / §FR-2 |
| **B. インフラ運用者（I-1〜I-5）** | AWS IAM / IAM Identity Center / K8s RBAC | [§NFR-6.4](../nfr/06-operations.md) |
| **C. M2M（M-1〜M-5）** | 本基盤（Client Credentials / Token Exchange / SCIM / Device Code）| §FR-1.1, §FR-6.3 |
| **D. 脅威モデル（T-1, T-2）** | （対象外、防御対象）| [§NFR-4](../nfr/04-security.md) |

→ **Category B のインフラ運用者は本基盤の認証を使わない**ため、Cognito / Keycloak の設計には影響しないが、運用設計と監査ログ要件に直接関わる。

#### ローカルユーザー範囲の 4 シナリオ

| シナリオ | 範囲 | 採用判断 |
|---|---|---|
| α 全カテゴリ | P-1〜P-4 全員ローカル可 | ❌ 不採用（要件混在で最適化困難）|
| β 管理者+IdPなし顧客 | P-1, P-2, P-4 ローカル可、P-3 はフェデ強制 | △ フォールバック |
| **γ 管理者のみ**（推奨）| P-1, P-2 のみローカル、P-3〜P-4 は IdP 経由 | ✅ **第一推奨** |
| δ Break Glass のみ | P-1 Break Glass 用最小ローカルのみ | ❌ B2B 顧客獲得幅狭すぎる |

#### アプリ集約 3 選択肢

| 案 | 概要 | 採用 |
|:---:|---|:---:|
| **A. 共通基盤集約** | 全ローカルユーザーを共通基盤に集約 | ✅ **Must** |
| B. 各アプリ独自 | 各アプリが独自 Login UI + ユーザー DB | ❌ **Won't** |
| C. ハイブリッド | レガシーは独自、新規は共通基盤 | △ 移行期限定で許容 |

#### B 案を採用しない理由（要点）

- **Broker パターン崩壊**（issuer 分散）
- **SSO 不可能**（別認証セッション）
- **セキュリティ品質差**（最も弱いアプリが天井）
- **コンプライアンス重複**（GDPR / SOC 2 / ISO 27001 を全アプリで）
- **退職時 deprovision 漏れ**
- **コスト N 倍**

詳細な「4 カテゴリ全体表」「シナリオ別 12 観点比較」「業界事例（Notion Enterprise / Stripe 等）」「B 案不採用の 6 理由詳細」は ADR-029 参照。

#### カテゴリ別の認証主体と委譲モデル

| カテゴリ | 推奨認証 | 管理主体 | [§FR-1.2.0.B](#fr-120b-aws-アカウント境界による運用摩擦への対応) Layer |
|---|---|---|---|
| P-1 基盤運用管理者 | 弊社内 IdP + Break Glass ローカル | 共通基盤運用チーム | AWS IAM Identity Center |
| P-2 テナント管理者（IdP あり）| 顧客 IdP 経由 | 顧客 IdP 側 | フェデユーザー |
| P-2 テナント管理者（IdP なし）| ローカル + MFA Must | 共通基盤運用がプロビジョン | Layer 3 委譲管理者 |
| P-3 顧客従業員（IdP あり）| 顧客 IdP 経由 | 顧客 IdP 側 | フェデユーザー |
| P-4 顧客従業員（IdP なし）+ ゲスト/外部協力者（旧 P-5 統合）| ローカル + MFA 強推奨、ゲスト系は招待 URL も可 | 顧客がテナント管理者として CRUD | Layer 3 + Layer 1 + 招待リンク |

→ シナリオ γ / β 採用により、ローカルユーザー数を**顧客一般従業員規模 → 管理者層規模に圧縮**できる。

### §FR-1.2.0.B AWS アカウント境界による運用摩擦への対応

> **論点**: A 案（共通基盤集約）を採ると、**共通基盤は専用 AWS アカウント**（アプリのアカウントとは別）に配置される。素朴に運用すると、ローカルユーザーの CRUD のたびに「共通基盤アカウントへの IAM 権限付与」や「アプリ運用チームから共通基盤運用チームへの作業申請」が発生し、業務スピードが落ちる懸念がある。
>
> **結論先出し**: この懸念は **「ユーザー CRUD を AWS IAM ベースで行う」前提を捨てれば解消する**。業界標準は **アプリケーション層の認証（Service Credentials / 委譲管理者 / SCIM / セルフサービス）** で CRUD を行い、AWS アカウント境界とは無関係に動かす設計。これにより A 案の集約メリットを保ったまま、現場運用は分散化できる。

#### 懸念事項の整理

| 操作 | 頻度 | 素朴な実装での摩擦 | 解消可能か |
|---|---|---|:---:|
| **ユーザー作成・削除・更新** | 高（日次）| アプリチームが共通基盤アカウントの IAM 権限申請 → 待ち時間発生 | ✅ **解消可能** |
| **パスワードリセット** | 高（日次）| 同上 | ✅ **解消可能**（セルフサービスも有効）|
| **MFA リセット・ロック解除** | 中（週次）| 同上 | ✅ **解消可能** |
| **ユーザー属性・ロール変更** | 中（週次）| 同上 | ✅ **解消可能** |
| **新規 IdP 接続追加** | 低（顧客追加時）| 共通基盤側の構成変更が必要 | △ **頻度低・申請許容** |
| **新規 App Client 追加** | 低（新アプリ立ち上げ時）| 同上 | △ **頻度低・申請許容** |
| **Realm / User Pool 設定変更** | 極低（半期 / 年）| 同上 | △ **頻度極低・申請許容** |

→ **高頻度操作（ユーザー CRUD）の摩擦は解消可能**。低頻度操作（構成変更）は AWS 側の作業申請を許容しても運用負荷は限定的。

#### 解決アプローチ（4 つのレイヤー）

```mermaid
flowchart TB
    subgraph Layer1["Layer 1: セルフサービス（ユーザー本人）"]
        S1["パスワードリセット<br/>MFA 自己設定<br/>プロフィール更新"]
    end

    subgraph Layer2["Layer 2: SCIM 自動プロビジョニング"]
        S2["アプリ側 HR / 人事システム<br/>↓ SCIM 2.0<br/>共通基盤（自動）"]
    end

    subgraph Layer3["Layer 3: テナント管理者委譲"]
        S3["アプリ運用チーム<br/>↓ Admin REST API<br/>（テナント Scope の OAuth Token）<br/>共通基盤"]
    end

    subgraph Layer4["Layer 4: Service Credentials"]
        S4["アプリ CI/CD / バックエンド<br/>↓ Client Credentials Grant<br/>共通基盤 Admin API"]
    end

    style Layer1 fill:#e8f5e9
    style Layer2 fill:#e8f5e9
    style Layer3 fill:#fff3e0
    style Layer4 fill:#fff3e0
```

**各レイヤーの詳細**:

| レイヤー | 解決する摩擦 | 実装 | 業界根拠 |
|---|---|---|---|
| **Layer 1: セルフサービス** | パスワードリセット / MFA 設定の人手作業をゼロ化 | Cognito Hosted UI / Keycloak アカウント設定画面（標準機能） | NIST SP 800-63B / OWASP 推奨。Auth0 / Okta もデフォルト機能 |
| **Layer 2: SCIM 2.0** | アプリ側の人事/HR 変更を共通基盤に自動同期。手動 CRUD 自体を不要化 | Keycloak SCIM プラグイン / Cognito は Lambda 経由実装 | RFC 7644。Microsoft Entra / Okta / Google Workspace が業界標準採用 |
| **Layer 3: 委譲管理者** | テナント（顧客 / アプリ）ごとに専用の管理者ユーザーを作り、その管理者は **Admin REST API** を使って自分のテナント内のユーザー CRUD ができる。AWS IAM は使わない | Cognito Plus ティアの delegated admin / Keycloak Realm Admin Role | KuppingerCole の Multi-Tenant IAM ベストプラクティス。Auth0 Organizations 同等機能 |
| **Layer 4: Service Credentials** | アプリの CI/CD やバックエンドが Client Credentials Grant で取得したアクセストークンで Admin API を呼ぶ | OAuth 2.0 Client Credentials Grant（RFC 6749 §4.4）+ 限定スコープ Client | OAuth 標準。Stripe / GitHub / Twilio 等の SaaS が同一モデル |

**重要**: いずれも **AWS IAM とは別の認証チャネル**（アプリケーション層の OAuth）で動く。共通基盤の AWS アカウントに対する IAM 権限申請は **不要**。

**Layer 3 の実装層 UI**: 委譲管理者（顧客テナント管理者）が実際に使うのは **[ADR-038 ユーザ管理画面](../../../adr/038-tenant-admin-portal.md)**（`admin.basis.example.com`）。Keycloak Admin Console を顧客に直接開放するのは不可（マルチテナント未対応 / UI 複雑度 / ブランディング不可、業界実例なし）。詳細は [§FR-8.5](08-admin.md#fr-85-tenant-admin-portal顧客テナント管理者向け-admin-ui) 参照。

**Layer 3 の Shared Responsibility 位置付け**: Layer 3 委譲管理者が管理する **IdP-KC 移行ユーザーは「顧客所有・弊社ホスト」モデル**（[ADR-037 Shared Responsibility Model](../../../adr/037-shared-responsibility-and-lightweight-iga.md)）。弊社はインフラ / データ保護 / ITDR 検知を、顧客はユーザーマスタ管理を実施する責務分担。詳細は [§FR-8.4](08-admin.md#fr-84-shared-responsibility-model-と軽量-iga) 参照。

#### 推奨運用モデル

```mermaid
flowchart LR
    subgraph App["アプリアカウント"]
        Dev["アプリ運用<br/>チーム"]
        HR["人事/HR<br/>システム"]
        User["エンド<br/>ユーザー"]
        CI["CI/CD"]
    end

    subgraph Auth["共通基盤アカウント（別 AWS アカウント）"]
        IDP["Cognito User Pool<br/>or Keycloak Realm"]
        AdminAPI["Admin REST API<br/>（OAuth で保護）"]
        SelfUI["Hosted UI /<br/>アカウント設定画面"]
    end

    HR -->|SCIM 自動同期| AdminAPI
    Dev -->|"テナント管理者 Token<br/>(Admin REST API)"| AdminAPI
    CI -->|"Client Credentials Token<br/>(Admin REST API)"| AdminAPI
    User -->|セルフサービス| SelfUI
    AdminAPI --> IDP
    SelfUI --> IDP

    style Auth fill:#fff3e0,stroke:#e65100
    style App fill:#e3f2fd,stroke:#1565c0
```

→ アプリチームは **自アカウント内に閉じた認証情報（OAuth Token）** で共通基盤を操作。AWS IAM 経由のクロスアカウント申請は発生しない。

#### 残る摩擦と対処

| 残る摩擦 | 対処 |
|---|---|
| 新規アプリ立ち上げ時の App Client 登録 | **Terraform IaC** で `proposal/common/01-architecture.md` の構成に従い PR ベース。AWS IAM 申請ではなく **Git PR 申請** |
| 新規顧客 IdP 登録 | 同上（Terraform で IdP オブジェクトを定義）|
| Realm / User Pool レベルの設定変更 | 同上（半期に 1 回程度の頻度） |
| 構成変更のレビュー責任 | **共通基盤運用チームが PR レビューを担当**。アプリチームは PR 提出のみ。実行は CI/CD |

→ **構成変更は AWS IAM ではなく Git PR ベース**にすることで、共通基盤運用チームの「ゲートキーパー」役割を維持しつつ、申請プロセスの軽量化（メール / チケット → PR レビュー）が可能。

#### 補足: B 案を再考する場合の条件

「アプリチームが完全な独立性を求める」場合のみ B 案を検討するが、次の **2 つすべてを満たす** ことが前提:

1. アプリが **物理的に SSO 不要**（独立した認証境界として扱われることが業務要件で確定）
2. アプリ独自のセキュリティ要件（PCI DSS の例で言う「カード処理アプリは完全分離」等）が**法的に強制**される

→ 上記 2 条件を満たさない限り、**Layer 1-4 の運用モデルで A 案を維持した方が運用負荷・セキュリティ品質ともに優位**。

### C 案（ハイブリッド）の許容範囲

C 案は**移行期限定**で許容（将来は A 案に統一する前提）：

| 状況 | 扱い |
|---|---|
| 既存システムが独自認証を持つ | **段階移行**を計画（一括移行 / 並行稼働 / 即時切替を選択）|
| 移行困難な特殊レガシー | **共通基盤と並行稼働**（既存ユーザーは既存認証、新規は基盤）、長期サポートはしない |
| 法規制で物理分離が必要 | テナント単位の Pool/Realm 分離（[§FR-2.3.A](02-federation.md#33a-アーキテクチャ判断単一-poolrealm--複数-idp-を採用) の B 案）で対応、独自認証は不要 |

→ **新規アプリは A 案 + Layer 1-4 の運用モデルを採用**。

### TBD / 要確認

**A. 利用者カテゴリと範囲（[§FR-1.2.0.0](#fr-1200-ローカルユーザーとは何か--利用者カテゴリ別の分析) と連動）**

| 確認項目 | 回答例 |
|---|---|
| **対象とする利用者カテゴリ**（P-1〜P-4） | P-1〜P-4（B2B 想定）/ P-1〜P-4（B2C 含む）/ その他 |
| **ローカルユーザー範囲シナリオ** | α 全カテゴリ / β 管理者+IdP なし顧客 / **γ 管理者のみ（推奨）** / δ Break Glass のみ |
| **想定顧客の IdP 普及率** | 90%+（大手中心、γ 採用可）/ 50-90%（β 採用）/ <50%（α 必要）|
| **IdP なし顧客への対応方針** | 顧客に IdP 準備を依頼 / 共通基盤側でローカル受け入れ / 顧客取らない |
| **P-1 基盤運用管理者の認証方式** | 弊社内 IdP（Entra ID 等）連携 / 完全ローカル / IdP + Break Glass 用ローカル |
| **P-2 テナント管理者の認証方式** | 顧客 IdP 経由 / ローカル / 顧客選択 |
| **ゲスト/外部協力者の扱い** | 確定（P-4 統合）/ 別途検討 | B2C は本基盤対象外で確定 |

**B. 既存システムからの移行**

| 確認項目 | 回答例 |
|---|---|
| 既存システムで独自ローカル認証を持つアプリの有無 | あり（システム名 + ユーザー数）/ なし |
| 既存独自認証システムの扱い方針 | 段階移行 / 並行稼働 / 即時切替 / 維持（C 案）|
| 移行期間中のユーザー情報同期方針 | 同期する / しない（移行完了後に基盤に統一）|
| 既存パスワードハッシュの持ち越し（[§FR-1.2 B](#tbd--要確認-2) と連動）| 持ち越す（bcrypt 等）/ 全員再設定 |

**C. クロスアカウント運用モデル（[§FR-1.2.0.B](#fr-120b-aws-アカウント境界による運用摩擦への対応) と連動）**

| 確認項目 | 回答例 |
|---|---|
| **ユーザー CRUD 運用モデル** | Layer 1 セルフ / Layer 2 SCIM / Layer 3 委譲管理者 / Layer 4 Service Credentials のどれをどこまで採用するか |
| **アプリチームに委譲する操作範囲** | 自テナントユーザー CRUD のみ / + ロール変更 / + IdP 設定変更まで |
| **SCIM ソース（自動プロビジョニング元）** | 人事システム / Active Directory / なし（手動 + セルフサービスのみ）|
| **新規 App Client / IdP 追加の申請プロセス** | Git PR / 共通基盤チームへのチケット / 即時許可 |

---

### §FR-1.2.0.D ユーザー識別子戦略 — メール非保有・顧客独自 ID への対応

> **詳細は [ADR-018 ユーザー識別子 3 階層戦略](../../../adr/018-user-identifier-3layer-emailless.md) を参照**
> **🆕 2026-06-24 追加: ID 統合の実装プロセス（現状調査 + SoT 決定 + マッピング DB 設計 + 段階的移行）は [ADR-054 ID 統合戦略](../../../adr/054-id-integration-strategy.md) を参照**
> **🆕 2026-06-29 追加: HRD ルーティング用ログイン ID 形式は `<tenant>-<userid>`（最初のハイフン前が Keycloak Organization alias）。詳細は [ADR-055 HRD 実装方式選定](../../../adr/055-hrd-implementation-method-selection.md) を参照**

> **このサブセクションで定めること**: メールアドレスを持たないユーザー、および顧客が独自に決めた ID 体系を受け入れる場合の**識別子設計（3 階層モデル）**と、JIT 突合・アカウント復旧・通知の代替手段。
> **主な判断軸**: email 非保有ユーザーの存在有無、顧客独自 ID の命名規則・不変性、アカウント復旧手段の物理制約、プラットフォーム（Cognito vs Keycloak）の制約耐性
> **§FR-1 全体との関係**: §FR-1.2.0.0 が「誰をローカルにするか」、§FR-1.2.0.B が「運用モデル」、§FR-1.2.0.D が「**識別子設計**」+ **ID 統合実装プロセス（ADR-054）**。本サブセクションは [§FR-2.2.1.A](02-federation.md#fr-2.2.1.a-同一テナント内ユーザー重複の扱い)（テナント内ユーザー重複の突合キー）と [§FR-7.1](07-user.md#fr-7.1-ユーザー-crud--fr-user-6.1)（ユーザー CRUD のキー設計）の**前提**を確定させる

#### 結論サマリ

業界標準の **3 階層識別子モデル**を採用:

| Layer | 値の例 | 採番者 | 可変性 | 用途 |
|---|---|---|---|---|
| **A** `sub` | UUID `a1b2c3d4-...` | 本基盤 | **不変** | 内部参照、JWT `sub` クレーム、全 DB FK |
| **B** `external_id` / `preferred_username`（=**ログイン ID**）| `acme-EMP-0042`（tenant prefix + 顧客内部 ID、**最初のハイフン前 = Keycloak Organization alias**）| 顧客 + 本基盤 | 可（運用上）| 顧客向け表示、検索、**ログイン入力**（ADR-055 SPI が parse）|
| **C** `identities[].userId` | IdP の `sub` | 顧客 IdP | **不変** | フェデ突合、IdP リンク |

> **2026-06-29 確定**: Layer B は **`<tenant>-<userid>` 形式**（最初のハイフン区切り、`<tenant>` 部分 = Keycloak Organization alias）。これにより外部 DB なしで HRD ルーティング可能（[ADR-055 §Decision Phase 1 採用確定](../../../adr/055-hrd-implementation-method-selection.md) 参照）。
> - 例: `acme-EMP-0042` → tenant=`acme`, userid=`EMP-0042`
> - 例: `beta-yamada.t` → tenant=`beta`, userid=`yamada.t`

**JIT 突合キー第一推奨**: `tenant_id + persistent NameID`、email は補助属性。Salesforce / Okta / ThousandEyes 公式が「email should never be used as the unique key」。

#### プラットフォーム影響

email 非保有 + 顧客独自 ID 対応では **Keycloak が運用摩擦小**:
- Cognito: username 不変・必須属性変更不可・preferred_username alias の制約により Pool 設計修正不可
- Keycloak: 随時変更可、Identity Provider Mapper で柔軟、Recovery Codes 公式機能（2025-10）

→ [[project-platform-direction-keycloak]] の Keycloak 確定方向を補強。

#### 復旧手段（NIST SP 800-63B-4 適合）

| 推奨手段 | 適用 |
|---|---|
| Recovery Codes（紙配布）| 全員、Keycloak 26.x 公式機能 |
| WebAuthn / Passkey 多重登録 | NIST 推奨、2 物理デバイス |
| Admin Reset | 工場・病院など対面で配布可 |
| Push Notification | スマホ持参の現場ワーカー |
| SMS OTP | Restricted（リスク承認必要）|

#### TBD / 要確認（B-IDM 系ヒアリング項目）

[hearing-checklist.md B-IDM-1〜12](../../hearing-checklist.md) を参照。主要項目:
- **B-IDM-1** 🔴 email 非保有ユーザーの存在
- **B-IDM-2** 🔴 顧客独自 ID の体系（命名規則・桁数）
- **B-IDM-6** 🔴 アカウント復旧手段の物理制約
- **B-IDM-9** 顧客 IdP の NameID Format 受け入れ
- **B-IDM-10** 顧客 IdP の email 送出率

---

### §FR-1.2.0.E 既存システムからの混在モデル移行戦略（ローカル + フェデ併存からの集約）

> **詳細は [ADR-019 既存システム移行戦略](../../../adr/019-existing-system-migration.md) を参照**

> **このサブセクションで定めること**: 現行システムが**ローカルユーザー管理 + フェデレーション併存**から本基盤（Keycloak ベース）へ移行する戦略。(1) 移行アプローチ、(2) PW ハッシュ移行手段、(3) サインアップ機能の引継ぎ、(4) 並走期運用、(5) 混在顧客対応。
> **§FR-1 全体との関係**: §FR-1.2.0.D で識別子戦略を定めた後、本サブセクションは**現行から新基盤への遷移パス**を確定。[§FR-7.4.7](07-user.md#fr-747-段階移行運用jit--scim-追加既存ユーザーマージ) JIT→SCIM 段階移行とは別軸

#### 結論サマリ

| 項目 | 採用方針 |
|---|---|
| 移行アプローチ | **B. 並走（Parallel Run）** — アプリ単位順次切替 |
| ローカル PW ハッシュ | **② User Storage SPI（キャッシュ移行）** — 初回ログイン時自動移行 |
| サインアップ機能 | **β. 共通基盤集約**（Keycloak Hosted UI + Custom Approval Authenticator）|
| 並走期間 | **3〜6 ヶ月** |
| 切替単位 | **アプリ単位**（DNS/config 切替で 1 時間以内ロールバック可）|
| 識別子マッピング | 旧 user_id を Layer B `external_id` として保持 + JWT `legacy_user_id` クレーム |
| 混在顧客対応 | Keycloak Organizations + Organization メンバー（IdP 紐付け有 / 無）|

#### 主要な裏どり（詳細は ADR-019）

- **Keycloak ネイティブ対応 PW ハッシュ**: PBKDF2 + Argon2（25+ デフォルト）。**bcrypt は plugin / Custom SPI 必要**
- **業界推奨 User Storage SPI**: 「Both authentication systems will have to be deployed at the same time until every user has logged in at least once」（codesoapbox.dev / Inteca）
- **Keymate 実証**: Keycloak へ **12 million records/hour** で大量移行成功
- **混在顧客は業界標準**（Microsoft Azure Architecture Center 2026）：「federation for employees + local for contractors」

#### TBD / 要確認（B-MIG 系ヒアリング項目）

[hearing-checklist.md B-MIG-1〜12](../../hearing-checklist.md) を参照。主要項目:
- **B-MIG-1** 🔴 現行 PW ハッシュアルゴリズム
- **B-MIG-2** 🔴 サインアップ機能の所在と承認フロー
- **B-MIG-3** 🔴 移行アプローチ希望（A Big Bang / **B 並走** / C 永続共存）
- **B-MIG-5** 🔴 顧客側混在状況（社員フェデ + 委託ローカル）

---

## §FR-1.2 パスワード・ローカルユーザー管理（→ FR-AUTH §1.2）

> **このサブセクションで定めること**: 本基盤の**ローカルユーザー**（フェデユーザーではなくパスワードで認証するユーザー）に対するパスワード管理ポリシー（長さ・複雑性・履歴・ローテーション・侵害検出等）。   
> **前提**: 認証主体は [§FR-1.2.0](#220-ローカルユーザー認証の主体--11-アーキテクチャと連動) で **A 案（共通基盤集約）採用**を前提とする。   
> **主な判断軸**: 適用される規制（PCI DSS / FFIEC / 業界独自）、NIST SP 800-63B Rev 4 準拠の意思、侵害クレデンシャル検出の要否   
> **§FR-1 全体との関係**: §FR-1.1 はフェデユーザー含む全認証フロー、§FR-1.2 はローカルユーザー固有のポリシー。フェデユーザーは [§FR-2 フェデレーション](02-federation.md) で扱う

「**どんな顧客パスワード要件にも対応可能**」という capability を示す。具体ポリシー値は §B 確認後に確定。

### 業界の現在地（2026 年時点の調査結果）

**NIST SP 800-63B Rev 4（2024 公開）が新ゴールドスタンダード**:

| 旧来の常識（〜2017） | NIST Rev 4 の指示 |
|---|---|
| 複雑性要件（大小・数字・記号）必須 | **"shall not" — 課してはならない** |
| 90 日ローテーション | **侵害証拠ない限り禁止** |
| 8 文字最低 | 8 文字（15 文字推奨、64 文字までサポート） |
| ペースト禁止 | **ペースト許可必須** |
| ブラックリストは任意 | **侵害クレデンシャル検出必須化** |

主要規制との関係:
- **PCI DSS v4.0** → NIST 準拠を許容（Compensating Control 不要）
- **ISO 27001 / SOC 2** → NIST 系業界標準に追随
- **個人情報保護法 / GDPR** → 具体パスワード要件指定なし、適切な技術的措置と表現
- **FFIEC（金融）** → 多要素重視、パスワード単独は不可

### 我々のスタンス（基本方針に基づく）

| 基本方針の柱 | パスワード領域での実現 |
|---|---|
| **絶対安全** | NIST SP 800-63B Rev 4 準拠をデフォルト推奨。侵害クレデンシャル検出を Must とする選択肢を提示 |
| **どんなアプリでも** | 下記マトリクスの通り、Cognito 3 ティア × Keycloak OSS × Keycloak RHBK の組み合わせで業界全要件をカバー |
| **効率よく** | AWS マルチアカウント前提で、顧客 / 用途ごとに最適なプラットフォーム・ティアを選択可能 |
| **運用負荷・コスト最小** | Cognito Lite で十分なら Lite（最安・運用ゼロ）。要件次第で Plus / Keycloak / RHBK へ段階的にせり上げる |

### 対応能力マトリクス（裏どり）

「どんな要件にも対応可能」を裏付ける全体像:

| 要件タイプ | Cognito Lite | Cognito Essentials | Cognito Plus | Keycloak OSS | Keycloak RHBK |
|---|:---:|:---:|:---:|:---:|:---:|
| 最小長 | ✅ (6-99) | ✅ | ✅ | ✅ | ✅ |
| 最大長 | ✅ (256 内部上限) | ✅ | ✅ | ✅ 明示設定可 | ✅ |
| 文字種（複雑性） | ✅ | ✅ | ✅ | ✅ | ✅ |
| ユーザー名/メール禁止 | ⚠ Pre Sign-up Lambda で実装可（※1）| ⚠ 同左 | ⚠ 同左 | ✅ `notUsername()` / `notEmail()` ポリシー標準 | ✅ 同左 |
| カスタム正規表現 | ⚠ Pre Sign-up Lambda で実装可（※1）| ⚠ 同左 | ⚠ 同左 | ✅ `regexPattern()` ポリシー標準 | ✅ 同左 |
| 履歴（N 個再利用禁止） | ❌ | ✅ (1-24) | ✅ | ✅ | ✅ |
| 定期ローテーション | ✅ | ✅ | ✅ | ✅ | ✅ |
| **侵害クレデンシャル検出** | ❌ | ❌ | ✅ **ネイティブ** | ⚠ HIBP プラグイン | ⚠ HIBP プラグイン（**Red Hat サポート対象外**）|
| ブラックリスト | ❌ | ❌ | △ 侵害検出に内包 | ✅ | ✅ |
| ハッシュアルゴリズム選択 | 透過 | 透過 | 透過 | ✅ (PBKDF2-SHA1/256/512) | ✅ |
| グループ別ポリシー | ❌ | ❌ | ❌ | ⚠ プラグイン要 | ⚠ プラグイン要 |
| **商用サポート（24/7）** | ✅ AWS Support | ✅ AWS Support | ✅ AWS Support | ❌ ベストエフォート（コミュニティ）| ✅ **Red Hat 24/7** |
| **SaaS / マネージド** | ✅ フルマネージド | ✅ フルマネージド | ✅ フルマネージド | ❌ 自己ホスト | ❌ 自己ホスト + 商用サポート |
| 価格モデル | 従量課金 / 安価 | 中 | +$0.02/MAU | OSS 無料 + AWS インフラ | $5,000〜30,000/年/ノード + AWS |

**※1**: Cognito にはネイティブなパスワード内容検証ポリシー（ユーザー名/メール禁止・カスタム正規表現）の**設定オプションは存在しない**が、**Pre Sign-up Lambda Trigger** で同等の実装が可能（AWS 公式 News Blog で "Safely Validating Usernames with Amazon Cognito" として紹介、`event.userAttributes.email` / `event.userName` を取得して新パスワードに含まれていれば拒否する Lambda を書く）。Keycloak のような宣言的設定との差はあるが、要件として実現できないわけではない。

→ Cognito Plus、Keycloak OSS+HIBP、Keycloak RHBK のいずれかで **NIST SP 800-63B Rev 4 完全準拠**が可能。Pre Sign-up Lambda を使えば Cognito 全ティアでも「ユーザー名/メール禁止・カスタム正規表現」要件に対応できる。

### ベースライン（推奨デフォルト + 設定範囲）

我々が現時点で推奨するデフォルト値（NIST Rev 4 ベース）:

| ポリシー | 推奨デフォルト | 設定可能範囲 | NIST Rev 4 整合 |
|---|---|---|:---:|
| 最小長 | **12 文字** | 8〜64+ | ✅ |
| 文字種要件 | **なし**（NIST 非推奨） | 任意組み合わせも可 | ✅ |
| 履歴 | 過去 5 個と一致禁止 | 0〜24 | — |
| 定期ローテーション | **なし**（侵害証拠時のみ強制変更） | 任意 | ✅ |
| 侵害クレデンシャル検出 | **有効**（Cognito Plus or Keycloak+HIBP） | ON/OFF | ✅ |
| アカウントロック | 5 回失敗で 30 分 | 任意 | — |
| セルフサービスリセット | 有効 | ON/OFF | — |
| 初期パスワード強制変更 | 有効 | ON/OFF | — |

→ 顧客が「PCI DSS 準拠で 12 文字 + 文字種要件 + 90 日ローテーション」を要求しても、「ISO 27001 ベースで複雑性不要」を要求しても、「金融系で侵害検出 Must」と要求しても、**いずれも対応可能**。

### TBD / 要確認

**A. 御社のパスワード要件**

| 確認項目 | 回答形式 |
|---|---|
| 適用される業界規制 | PCI DSS / FFIEC / 業界独自 / 規制なし |
| 既存パスワードポリシー | 文字長・複雑性・履歴・ローテーション |
| NIST SP 800-63B Rev 4 準拠を目指すか | はい / いいえ / 部分採用 |
| 侵害クレデンシャル検出（HIBP 等）の要否 | はい / いいえ |

**B. 既存システムからの移行**

| 確認項目 | 回答形式 |
|---|---|
| 既存ユーザーのパスワードハッシュ | 形式（bcrypt / PBKDF2 / 独自）+ 件数 |
| ハッシュ持ち越しの希望 | 持ち越す / 全員再設定で OK |

**C. サポート・運用形態の希望**（プラットフォーム選定に直結）

| 希望 | 推奨プラットフォーム |
|---|---|
| フルマネージド（SaaS 同等、サーバー管理不要） | **Cognito**（Lite / Essentials / Plus）|
| 自己ホストだが 24/7 商用サポート必須 | **Keycloak RHBK**（Red Hat サポート + $5K〜30K/年/ノード）|
| 自己ホスト + 自前運用 OK（OSS で十分） | **Keycloak OSS**（最小コスト、コミュニティサポート）|

**D. プラットフォーム選定への影響まとめ**

- 侵害検出ネイティブ Must + マネージド希望 → **Cognito Plus**（+$0.02/MAU）
- カスタム正規表現 / Not Username / 高度ブラックリストを**宣言的設定で運用したい** → **Keycloak（OSS or RHBK）**
- カスタム正規表現 / Not Username が要件にあるが、**Lambda 実装許容** → **Cognito 全ティア**でも対応可（※1）
- 24/7 商用サポート必須 → **Cognito 全ティア**、または **Keycloak RHBK**
- 上記なし、最安希望 → **Cognito Lite**

---

## §FR-1.3 モバイルアプリ認証（Native Mobile）

> **詳細は [ADR-050 モバイルアプリ認証設計](../../../adr/050-mobile-sdk-native-auth.md) を参照**

> **このサブセクションで定めること**: 顧客アプリ（業務アプリ）がモバイル対応する場合の標準的なネイティブ認証フローと推奨 SDK / 認証パターン。
> **主な判断軸**: OAuth 2.1 / RFC 8252 / WebAuthn Platform / DPoP / MFA Fatigue Attack 対策 / 商用 Mobile SDK（Auth0 / Okta）のコスト
> **§FR-1 全体との関係**: §FR-1.1 ブラウザベース認証の**ネイティブモバイル版**、§FR-3 MFA と統合

### 結論サマリ

| 項目 | 採用方針 |
|---|---|
| **OAuth フロー** | **OAuth 2.1 (PKCE 必須)** + Authorization Code + System Browser |
| **推奨 SDK** | **AppAuth iOS / Android**（OpenID Foundation 公式）+ 弊社薄ラッパー |
| **ブラウザ** | **iOS: ASWebAuthenticationSession** / **Android: Chrome Custom Tabs** |
| **WebView** | **全面禁止**（RFC 8252、Phishing 対策）|
| **MFA** | **WebAuthn Platform**（Face ID / Touch ID / Android Biometric）+ Phase 2 で Push 通知 MFA（Number Matching + Context）|
| **Refresh Token** | **App-bound + Device Binding（DPoP RFC 9449）** |
| **Deep Link** | **Universal Links（iOS）+ App Links（Android）**、Custom Scheme 非推奨 |
| **Token 保管** | iOS Keychain（Secure Enclave）/ Android Keystore（Hardware-backed）+ Biometric ロック |
| **デバイス検証**（Phase 2）| App Attest（iOS）+ Play Integrity（Android）|
| **MDM / MAM / MTD 統合**（Phase 3）| 顧客側ツールと連携、Conditional Access パターン |

### Phase 別ロードマップ

| Phase | 内容 | 期間 |
|---|---|---|
| Phase 1 | AppAuth SDK + 弊社ラッパー + Keycloak 設定 + リファレンス実装 | 3 ヶ月 |
| Phase 2 | Push 通知 MFA + App Attest / Play Integrity + DPoP | 4 ヶ月 |
| Phase 3 | MDM / MAM / MTD 統合 + Conditional Access + FAPI 2.0 | 顧客要件次第 |

### MFA Fatigue Attack 対策（重要）

- **Number Matching**：画面表示 2 桁数字をモバイル入力
- **Context 表示**：ログイン元 IP / 地域 / アプリ / 時刻を承認画面に明示
- **Push 試行回数制限**：5 分間に 3 回まで
- **Adaptive Auth 連動**：高 Risk Score 時は Push 送信せず Step-up

### コスト

- Phase 1 初期 1,500 万円 + 月次運用 50 万円
- Phase 2 追加 1,000 万円 + SNS Push $750/月（10M MAU）
- 商用 Auth0 / Okta Mobile SDK 年 $40-50K 比 5-10 倍削減

### TBD / 要確認

| 確認項目 | ヒアリング ID | 回答例 |
|---|---|---|
| **モバイルアプリ採用予定** | **B-MOB-1** | あり（Phase 1）/ Phase 2 / なし |
| 対応プラットフォーム | **B-MOB-2** | iOS のみ / Android のみ / 両方 / React Native / Flutter |
| 想定 MAU 規模 | **B-MOB-3** | 〜10K / 100K / 1M / 10M |
| WebAuthn Biometric 採用 | **B-MOB-4** | 必須（推奨）/ オプション / 不要 |
| Push 通知 MFA 採用 | **B-MOB-5** | Phase 1 から / Phase 2 / 不要 |
| FAPI 2.0 適用顧客（金融）| **B-MOB-6** | あり / なし |
| MDM / MAM 統合 | **B-MOB-7** | Intune / Workspace ONE / Jamf / 不要 |

---

### 参考資料（業界動向の裏どり）

- [NIST SP 800-63B Rev 4 公式](https://pages.nist.gov/800-63-4/sp800-63b.html)
- [NIST 800-63B Rev 4 解説 - Enzoic](https://www.enzoic.com/blog/nist-sp-800-63b-rev4/)
- [Cognito Essentials/Plus 発表 - AWS What's New](https://aws.amazon.com/about-aws/whats-new/2024/11/new-feature-tiers-essentials-plus-amazon-cognito/)
- [Cognito Compromised Credentials Detection 公式](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pool-settings-compromised-credentials.html)
- [Keycloak Password Policies 公式](https://www.keycloak.org/docs/latest/server_admin/index.html)
- [Keycloak HIBP プラグイン (community)](https://github.com/alexashley/keycloak-password-policy-have-i-been-pwned)
- [Red Hat build of Keycloak 公式](https://docs.redhat.com/en/documentation/red_hat_build_of_keycloak)
