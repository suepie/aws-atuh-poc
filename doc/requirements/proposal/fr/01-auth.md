# §FR-1 認証

> 上位 SSOT: [00-index.md](00-index.md)
> 詳細: [../../functional-requirements.md §1](../../functional-requirements.md)
> カバー範囲: FR-AUTH §1.1 認証フロー / §1.2 パスワード・ローカルユーザー管理

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
- **mTLS Client Authentication（RFC 8705）**: FAPI 準拠、金融、高セキュリティ M2M

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
    Q1{XSS リスク<br/>(third-party JS / WYSIWYG 等)}
    Q2{扱うデータ機密性}
    Q3{BFF 運用体制<br/>(Lambda/ECS 運用可)}
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
| B2B SaaS（一般業務） | **BFF 推奨**（北極星「絶対安全」と整合）|
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

→ 「採用するか / しないか」の方向性合意のみ本資料で扱い、**実装詳細・構成図・移行プランは内部技術メモ [`bff-implementation-notes.md`](../../../common/bff-implementation-notes.md) に分離**。

**C. オプションフローの要否（影響：プラットフォーム選定に直結）**

| 要件 ID | フロー | 要否確認の問い | 影響 |
|---|---|---|---|
| FR-AUTH-005 | Token Exchange | マイクロサービス間でユーザー文脈を伝播させたい呼び出しがあるか | **Yes → Keycloak 必須**（Cognito 非対応）|
| FR-AUTH-006 | Device Code | CLI / IoT / Smart TV / AI Agent クライアントを認証する予定があるか | **Yes → Keycloak 必須** |
| FR-AUTH-007 | mTLS | FAPI 準拠 / 金融取引 / 高セキュリティ M2M の要件があるか | **Yes → Keycloak 必須** |

これらが 1 つでも Yes なら、Cognito 単独では実現できないため、**Keycloak（または併用）が必須**になります。

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

> **このサブセクションで定めること**: フェデユーザー以外（パスワード等で認証する「ローカルユーザー」）を、**共通基盤側で認証するか、各アプリ側で認証するか**という認証主体の選択。
> **主な判断軸**: 北極星整合（特に「絶対安全」「効率よく」「運用負荷低」）、既存システムの認証実装の有無、移行戦略
> **§FR-1 全体との関係**: §FR-1.2.0 が**前提のスタンス**、§FR-1.2 以降が**具体ポリシー**。スタンスが決まらないと §FR-1.2 の議論は意味を持たない

### 業界の現在地

OIDC / OAuth 2.0 の **Identity Broker パターン**を採用する組織では、**ローカルユーザーも基盤側に集約する**のが業界標準。各アプリで独自認証を持つと、Broker パターンの本質（集約点 1 つ、各アプリは JWT を信頼するだけ）が崩れ、SSO・コンプライアンス対応・運用面で大きな問題が発生する。

### 我々のスタンス（北極星に基づく）

> **本基盤の前提：**
> - **ローカルユーザーは共通基盤（Cognito User Pool / Keycloak Realm）に集約する**（A 案）
> - **各アプリで独自にローカル認証は持たない**（B 案不採用）
> - **既存システムの移行期間は例外的にハイブリッド許容**（C 案、移行完了で A 案に統一）

### 3 つの選択肢

| 選択肢 | 概要 | 採用判断 |
|---|---|---|
| **A. 共通基盤集約** | 全ローカルユーザーを共通基盤の User DB に集約。各アプリは基盤発行 JWT を信頼するだけ | ✅ **Must** |
| **B. 各アプリ独自認証** | 各アプリが独自 Login UI + ユーザー DB + パスワード管理を持ち、共通基盤は OAuth/OIDC で連携する外部 IdP として動作 | ❌ **Won't** |
| **C. ハイブリッド** | レガシーアプリは独自認証を維持、新規は共通基盤を使う移行期間限定運用 | △ **移行期限定で許容** |

### 評価マトリクス

| 観点 | A. 共通基盤集約 | B. 各アプリ独自 | C. ハイブリッド |
|---|:---:|:---:|:---:|
| **SSO** | ✅ 全アプリで自動 | ❌ 不可能（別 DB） | ⚠ 共通基盤側のみ |
| **パスワードポリシー統一** | ✅ 一元管理 | ❌ 各アプリで別 | ⚠ 部分的 |
| **退職時 deprovision** | ✅ 基盤で 1 回 → 全アプリ反映 | ❌ 各アプリで手動 | ⚠ 混在対応必要 |
| **侵害クレデンシャル検出** | ✅ 基盤 1 箇所で実装 | ❌ 各アプリで個別 | ⚠ 一部のみ |
| **MFA 一元化** | ✅ 基盤で統一 | ❌ 各アプリで個別 | ⚠ 一部のみ |
| **GDPR 削除権対応** | ✅ 基盤で 1 回 | ❌ 各アプリで個別 | ⚠ 混在 |
| **監査ログ集約** | ✅ 一元 | ❌ 各アプリで個別 | ⚠ 混在 |
| **漏洩時の影響範囲** | ⚠ 基盤 1 箇所大 | ⚠ 各アプリで脆弱性管理必要 | ⚠ 混在 |
| **実装複雑度** | ✅ 単純 | ❌ 各アプリで認証実装 | ❌ 最も複雑（2 系統管理）|
| **運用負荷** | ✅ 基盤チームのみ | ❌ 各アプリチームで個別 | ❌ 混在 |
| **Broker パターン整合性**（[§1](../common/01-architecture.md)）| ✅ 完全整合 | ❌ パターン崩壊 | ⚠ 部分整合 |
| **北極星「絶対安全」** | ✅ NIST 統一適用可 | ❌ 各アプリで品質差 | ⚠ 一部のみ |
| **北極星「効率よく」** | ✅ 顧客追加で各アプリ変更不要 | ❌ 顧客追加で全アプリ改修 | ⚠ 段階対応 |

### B 案（各アプリ独自認証）を採用しない理由

| 理由 | 内容 |
|---|---|
| **Broker パターンの崩壊** | 各アプリで独自認証 → §1 の Hub-and-Spoke パターンの恩恵が消失。issuer が分散し、各アプリで複数 issuer 検証が必要 |
| **SSO 不可能** | 同じユーザーがアプリ A と B にログインしても別認証セッション。「一度のログインで全システム使える」UX が成立しない |
| **セキュリティの品質差** | 各アプリでパスワードハッシュ・レート制限・侵害検出・MFA を個別実装 → 品質が揃わず、最も弱いアプリが全体のセキュリティ天井になる |
| **コンプライアンス対応の重複** | GDPR 削除権、SOC 2 ユーザー監査、ISO 27001 等を**全アプリで個別対応**必要 |
| **退職時 deprovision の漏れリスク** | 基盤で 1 回 → 全アプリ反映、にならず、各アプリで個別対応必要 |
| **コスト** | 各アプリで認証 UI / DB / バックエンド実装 → 開発・運用コスト N 倍 |

### C 案（ハイブリッド）の許容範囲

C 案は**移行期限定**で許容（将来は A 案に統一する前提）：

| 状況 | 扱い |
|---|---|
| 既存システムが独自認証を持つ | **段階移行**を計画（一括移行 / 並行稼働 / 即時切替を選択）|
| 移行困難な特殊レガシー | **共通基盤と並行稼働**（既存ユーザーは既存認証、新規は基盤）、長期サポートはしない |
| 法規制で物理分離が必要 | テナント単位の Pool/Realm 分離（[§FR-2.3.A](02-federation.md#33a-アーキテクチャ判断単一-poolrealm--複数-idp-を採用) の B 案）で対応、独自認証は不要 |

→ **新規アプリは A 案を採用**。

### TBD / 要確認

| 確認項目 | 回答例 |
|---|---|
| 既存システムで独自ローカル認証を持つアプリの有無 | あり（システム名 + ユーザー数）/ なし |
| 既存独自認証システムの扱い方針 | 段階移行 / 並行稼働 / 即時切替 / 維持（C 案）|
| 移行期間中のユーザー情報同期方針 | 同期する / しない（移行完了後に基盤に統一）|
| 既存パスワードハッシュの持ち越し（[§FR-1.2 B](#tbd--要確認-2) と連動）| 持ち越す（bcrypt 等）/ 全員再設定 |

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

### 我々のスタンス（北極星に基づく）

| 北極星の柱 | パスワード領域での実現 |
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
| ユーザー名/メール禁止 | ❌ | ❌ | ❌ | ✅ | ✅ |
| カスタム正規表現 | ❌ | ❌ | ❌ | ✅ | ✅ |
| 履歴（N 個再利用禁止） | ❌ | ✅ (1-24) | ✅ | ✅ | ✅ |
| 定期ローテーション | ✅ | ✅ | ✅ | ✅ | ✅ |
| **侵害クレデンシャル検出** | ❌ | ❌ | ✅ **ネイティブ** | ⚠ HIBP プラグイン | ⚠ HIBP プラグイン（**Red Hat サポート対象外**）|
| ブラックリスト | ❌ | ❌ | △ 侵害検出に内包 | ✅ | ✅ |
| ハッシュアルゴリズム選択 | 透過 | 透過 | 透過 | ✅ (PBKDF2-SHA1/256/512) | ✅ |
| グループ別ポリシー | ❌ | ❌ | ❌ | ⚠ プラグイン要 | ⚠ プラグイン要 |
| **商用サポート（24/7）** | ✅ AWS Support | ✅ AWS Support | ✅ AWS Support | ❌ ベストエフォート（コミュニティ）| ✅ **Red Hat 24/7** |
| **SaaS / マネージド** | ✅ フルマネージド | ✅ フルマネージド | ✅ フルマネージド | ❌ 自己ホスト | ❌ 自己ホスト + 商用サポート |
| 価格モデル | 従量課金 / 安価 | 中 | +$0.02/MAU | OSS 無料 + AWS インフラ | $5,000〜30,000/年/ノード + AWS |

→ Cognito Plus、Keycloak OSS+HIBP、Keycloak RHBK のいずれかで **NIST SP 800-63B Rev 4 完全準拠**が可能。

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
- カスタム正規表現 / Not Username / 高度ブラックリスト → **Keycloak（OSS or RHBK）**
- 24/7 商用サポート必須 → **Cognito 全ティア**、または **Keycloak RHBK**
- 上記なし、最安希望 → **Cognito Lite**

### 参考資料（業界動向の裏どり）

- [NIST SP 800-63B Rev 4 公式](https://pages.nist.gov/800-63-4/sp800-63b.html)
- [NIST 800-63B Rev 4 解説 - Enzoic](https://www.enzoic.com/blog/nist-sp-800-63b-rev4/)
- [Cognito Essentials/Plus 発表 - AWS What's New](https://aws.amazon.com/about-aws/whats-new/2024/11/new-feature-tiers-essentials-plus-amazon-cognito/)
- [Cognito Compromised Credentials Detection 公式](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pool-settings-compromised-credentials.html)
- [Keycloak Password Policies 公式](https://www.keycloak.org/docs/latest/server_admin/index.html)
- [Keycloak HIBP プラグイン (community)](https://github.com/alexashley/keycloak-password-policy-have-i-been-pwned)
- [Red Hat build of Keycloak 公式](https://docs.redhat.com/en/documentation/red_hat_build_of_keycloak)
