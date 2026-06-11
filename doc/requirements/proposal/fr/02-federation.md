# §FR-2 フェデレーション / 外部 IdP 連携

> 上位 SSOT: [00-index.md](00-index.md)   
> 詳細: [../../functional-requirements.md §2 FR-FED](../../functional-requirements.md)、[../../../common/identity-broker-multi-idp.md](../../../common/identity-broker-multi-idp.md)   
> カバー範囲: FR-FED §2.1 IdP 接続種別 / §2.2 ユーザー処理（§2.2.1 JIT / §2.2.2 属性マッピング / §2.2.3 MFA 重複回避）/ §2.3 マルチテナント運用

---

## §FR-2.0 前提と背景

### 用語整理

| 用語 | 本基盤での意味 |
|---|---|
| **フェデレーション** | 自社外の IdP（顧客企業の IdP 等）に認証を委譲し、認証結果を受け取る仕組み |
| **外部 IdP** | Microsoft Entra ID / Okta / Google Workspace / HENNGE One / 自社 AD 等、顧客が既に使用している認証基盤 |
| **OIDC / SAML / LDAP** | 外部 IdP を接続するための標準プロトコル（前 2 つは主流、LDAP はレガシー領域で根強い） |
| **JIT プロビジョニング** | 初回ログイン時に外部 IdP の情報をもとに本基盤側にユーザーを自動登録 |
| **属性マッピング** | IdP ごとに異なる属性名（tid / group 等）を本基盤の標準クレームに正規化 |
| **マルチテナント** | 複数の顧客企業のユーザーを単一基盤で受け入れ、テナント境界で分離 |

### なぜここ（§FR-2）で決めるか

```mermaid
flowchart LR
    S1["§FR-1 認証<br/>(ローカル認証)"]
    S2["§FR-2 フェデレーション ← イマココ<br/>(外部 IdP 接続)"]
    S3["§FR-3 MFA"]
    S4["§FR-4 SSO"]
    C1["§C-1 Identity Broker<br/>アーキテクチャ"]

    S1 -.補完.- S2
    S2 --> S3
    S2 --> S4
    S2 --> C1

    style S2 fill:#fff3e0,stroke:#e65100
```

§FR-2 は **「どんな顧客 IdP でも受け入れられる基盤か」** を決める章。本基盤の **Identity Broker パターン**（[§C-1](../common/01-architecture.md)）の中核要件であり、ここの要件が確定すると Broker パターン採用は構造的に必然になる。
- **§FR-2.1 接続種別**: プロトコル / IdP 製品の対応範囲
- **§FR-2.2 ユーザー処理**: 受け入れたユーザーの内部表現（JIT / 属性マッピング / MFA 重複回避）
- **§FR-2.3 マルチテナント運用**: 複数 IdP の並行運用、顧客追加のオンボーディング

### §FR-2.0.A 本基盤のフェデレーションスタンス

> **OIDC / SAML 2.0 / LDAP の業界標準で接続可能な IdP は全て受け入れる。「どんな顧客 IdP でも繋ぎ込める」を capability として担保し、SAML IdP モード / LDAP 直結が必要な場合は Keycloak、それ以外は Cognito でも対応可能とする。マルチテナントは「単一 Pool/Realm + 複数 IdP」を採用し、顧客追加で各システム変更不要を実現する。**

### 共通認証基盤として「フェデレーション」を検討する意義

| 観点 | 個別アプリで実装した場合 | 共通認証基盤で実装した場合 |
|---|---|---|
| 顧客 IdP 接続 | 各アプリで個別連携（N アプリ × M IdP の組合せ爆発） | **基盤で 1 度設定 → 全アプリに波及** |
| 属性正規化 | アプリごとに別ロジック | **基盤側で OCSF/標準クレームに統一** |
| 顧客追加リードタイム | 全アプリ改修必要 | **基盤の IdP 設定追加のみ（< 1 営業日）** |
| プロトコル準拠 | アプリ実装ばらつき | **基盤側で OIDC/SAML 標準準拠** |
| MFA 重複回避 | アプリで判定不可 | **基盤側で `amr` クレーム検査** |

→ フェデレーションを共通基盤に集約することが、**Broker パターン採用の本質的価値**。顧客追加のフリクションレス化と統一クレーム形式が同時に実現する。

### §FR-2.0.B プロトコル組み合わせの全体像（受信側 × 発行側は独立）

> **混同しやすいポイント**: 「OIDC で認証 + OAuth でトークン発行」という表現は、実は **OIDC = OAuth 2.0 + ID Token** で同一系統。プロトコルは「**受信側（顧客 IdP → 本基盤）**」と「**発行側（本基盤 → アプリ）**」の **2 つの独立した軸**で考える。

#### 本基盤 = アイデンティティ仲介 Hub（Identity Broker）

> **注**: Identity Broker は「プロトコル変換」だけでなく、以下 5 つの機能を統合的に担う仲介装置:
> 1. **プロトコル変換**（SAML → OIDC 等）
> 2. **属性正規化**（IdP ごとに違う `tid` / `org_id` 等を統一 `tenant_id` に）
> 3. **Trust 集約**（各アプリは Broker 1 つだけを信頼）
> 4. **統一 JWT 発行**（受信側が何であれ同じフォーマット）
> 5. **オーケストレーション**（JIT / MFA 重複回避 / SSO セッション / ログアウト伝播）

```mermaid
flowchart LR
    subgraph Recv["受信側（多様、顧客次第）"]
        R1[顧客 A: OIDC<br/>Entra ID]
        R2[顧客 B: SAML 2.0<br/>HENNGE]
        R3[顧客 C: LDAP<br/>オンプレ AD]
    end

    Hub["本基盤<br/>Identity Broker<br/>(プロトコル変換 +<br/>属性正規化 +<br/>Trust 集約 +<br/>統一 JWT 発行 +<br/>オーケストレーション)"]

    subgraph Issue["発行側（基本統一）"]
        I1[アプリ全般<br/>OIDC + OAuth 2.0<br/>JWT]
        I2[レガシー SAML SP アプリ<br/>SAML 2.0 IdP モード<br/>※B-202 Yes 時のみ追加]
    end

    R1 --> Hub --> I1
    R2 --> Hub --> I1
    R3 --> Hub --> I1
    Hub -.オプション.-> I2

    style Hub fill:#fff3e0
    style I1 fill:#e8f5e9
    style I2 fill:#fff8e1
```

→ **受信側は顧客次第で多様、発行側は基本的に OIDC + OAuth で統一**。これにより**各アプリは「JWT 検証だけ」で完結**できる（Broker パターンの本質）。
→ **「プロトコル変換装置」は機能の 1 つを切り出した表現**。全体像は上記 5 機能を含む **アイデンティティ仲介 Hub**。

#### 組み合わせマトリクス

| 受信側プロトコル | 発行側プロトコル | 構成名 | 典型ケース | 本基盤の対応 |
|---|---|---|---|:---:|
| **OIDC** | **OIDC + OAuth 2.0** | 標準（現代的、推奨）| 新規構築、ほとんどの B2B SaaS | ✅ |
| **SAML 2.0 SP** | **OIDC + OAuth 2.0** | **SAML→JWT フェデブリッジ** | 顧客 IdP が HENNGE / ADFS、アプリは現代的 | ✅ |
| **LDAP** | **OIDC + OAuth 2.0** | AD→JWT 変換 | 顧客が AD 直結、アプリは JWT | ✅ Keycloak のみ |
| OIDC | **SAML 2.0 IdP** | レガシー SAML SP 連携 | 顧客 IdP は OIDC、既存アプリが SAML SP-only | ✅ Keycloak のみ |
| SAML 2.0 SP | **SAML 2.0 IdP** | フル SAML（古典 SSO）| 全体 SAML、稀 | ✅ Keycloak のみ |
| LDAP | **SAML 2.0 IdP** | AD→SAML 出力 | 稀、規制業界の特殊系 | ✅ Keycloak のみ |

#### OIDC と OAuth 2.0 の関係（よくある誤解）

| 用語 | 関係 |
|---|---|
| **OAuth 2.0** | **認可フレームワーク**（Token 発行プロトコル、RFC 6749）|
| **OIDC**（OpenID Connect 1.0）| **OAuth 2.0 + ID Token**（認証層を追加）|

→ 「**OIDC で認証 + OAuth で発行**」は技術的に同じ系統（OIDC が OAuth を内包）。**SAML だけが完全に別系統**。
→ **発行側は基本 OIDC + OAuth で統一**、**SAML IdP モードはオプション**（[B-202](../../hearing-script/02-idp-federation.md) Yes 時のみ追加）。
→ 受信側 / 発行側で **意味 A の認可（Token 発行制御）**は本基盤の責務。**意味 B の認可（業務判定）**はアプリ側（[§FR-6.0.A](06-authz.md)）。

### §FR-2.0.C 本基盤対応プロトコル一覧（早見表、12 プロトコル × 4 Tier）

> **「結局どんなプロトコルに対応する基盤か?」への 1 枚回答**。Tier 1 〜 4 で分類した全プロトコルと、各プラットフォームの対応状況を集約。顧客説明・新規参入者キャッチアップに利用可能。

#### Tier 1: 認証フェデレーション系（IdP 連携の中核 / 受信側）

| プロトコル | 種類 | 方向 | 用途 | Cognito | Keycloak | 関連 |
|---|---|---|---|:---:|:---:|---|
| **OIDC 1.0** | 認証 + ID | **受信** (顧客 IdP) | フェデログイン受け入れ | ✅ | ✅ | §FR-2.1 |
| **OIDC 1.0** | 認証 + ID | **発行** (アプリ向け) | 各アプリへ JWT 発行 | ✅ | ✅ | §FR-2.0.B |
| **SAML 2.0 SP** | 認証 | **受信** (顧客 IdP) | SAML 顧客 IdP（HENNGE 等）からの受信 | ✅ | ✅ | §FR-2.1 |
| **SAML 2.0 IdP** | 認証 | **発行** (アプリ向け) | 既存 SAML SP アプリへの発行 | ❌ **K-11** | ✅ | B-202 |
| **OAuth 2.0 Broker** ★NEW | 認可フロー | **受信** (OIDC 非対応 OAuth 2.0 IdP) | 純粋 OAuth 2.0 IdP からの受信（Keycloak 26.x で追加）| ❌ | ✅ | §FR-2.1 |
| **Social Login**（Google / Microsoft / Apple / Facebook / GitHub 等）★NEW | OIDC ベース | **受信** | B2C ユーザー（P-6）/ ゲスト（P-5）対応 | ✅ | ✅ | §FR-1.2 |
| **LDAP / LDAPS** | ディレクトリ認証 | **受信** (顧客 AD) | 顧客 AD への直接バインド | ❌ **K-12** | ✅ | §FR-2.1 |
| **Kerberos / SPNEGO** | チケット認証 | **受信** (顧客 AD) | Windows 統合認証（社内 PC SSO）| ❌ **K-13** | ✅ | §FR-2.1 |
| **WS-Federation** ★NEW | レガシー認証 | **受信** (古い ADFS) | 古い ADFS 環境（Microsoft も Entra ID 移行推奨）| ❌ | ⚠ extension | §FR-2.0.D |

#### Tier 2: OAuth 2.0/2.1 系（認可フロー / 発行側）

| プロトコル | 種類 | 方向 | 用途 | Cognito | Keycloak | 関連 |
|---|---|---|---|:---:|:---:|---|
| **Authorization Code + PKCE** | Grant Type | **発行** (SPA/SSR/Mobile) | ブラウザ経由ログイン | ✅ | ✅ | §FR-1.1 |
| **Client Credentials** | Grant Type | **発行** (M2M) | バッチ / マイクロサービス間 | ✅ | ✅ | §FR-1.1 |
| **Device Code (RFC 8628)** | Grant Type | **発行** (CLI/IoT) | CLI / IoT / Smart TV / AI Agent | ❌ **K-02** | ✅ | §FR-1.1 |
| **Token Exchange (RFC 8693)** | Grant Type | **発行** (OBO) | マイクロサービス間ユーザー文脈伝播 | ❌ **K-01** | ✅ | §FR-6.0.B |
| **mTLS Client Auth (RFC 8705)** | クライアント認証 | **受信** (M2M) | FAPI 準拠 / 高セキュリティ M2M | ❌ **K-03** | ✅ | §FR-1.1 |
| **DPoP (RFC 9449)** | トークン拘束 | **発行** (Sender-Constrained) | mTLS 代替 / Sender-Constrained Tokens | ❌ | ✅ | §FR-1.1 |

#### Tier 3: MFA 認証要素プロトコル

| プロトコル | 種類 | 方向 | 用途 | Cognito | Keycloak | 関連 |
|---|---|---|---|:---:|:---:|---|
| **WebAuthn / FIDO2 (Passkey)** | 認証要素 (Phishing-resistant) | 内部 | パスキー、ハードウェアキー | ✅ Essentials+ | ✅ | §FR-3.1 |
| **TOTP (RFC 6238)** | 認証要素 | 内部 | Google Authenticator 等 | ✅ | ✅ | §FR-3.1 |
| **SMS OTP** | 認証要素 (NIST 非推奨) | 内部 | レガシー互換 | ✅ | ✅ | §FR-3.1 |
| **Email OTP** | 認証要素 (NIST 非推奨) | 内部 | 本人確認補助 | ✅ Essentials+ | ✅ | §FR-3.1 |

#### Tier 4: 関連プロトコル（認証ではないが連携で必要）

| プロトコル | 種類 | 方向 | 用途 | Cognito | Keycloak | 関連 |
|---|---|---|---|:---:|:---:|---|
| **SCIM 2.0 (RFC 7644)** | プロビジョニング | **受信** (HR/IdP) | ユーザー同期、退職者 deprovisioning | ❌ ネイティブ（Lambda 自前）| ⚠ プラグイン | §FR-7.4 |
| **JWKS (RFC 7517)** | 鍵配布 | **発行** (アプリ向け) | 公開鍵の自動配布 | ✅ | ✅ | §FR-9.1 |
| **OIDC Discovery** | メタデータ配布 | **発行** (アプリ向け) | `.well-known/openid-configuration` | ✅ | ✅ | §FR-9.1 |
| **OIDC RP-Initiated Logout** | ログアウト | **発行** | ブラウザ経由ログアウト | ⚠ 独自実装 | ✅ | §FR-5.1 |
| **OIDC Back-Channel Logout 1.0** | ログアウト | **発行** | サーバー間直接ログアウト通知 | ❌ **K-07** | ✅ | §FR-5.1 |
| **Token Revocation (RFC 7009)** | トークン無効化 | **受信** | Access/Refresh Token 強制無効化 | ⚠ Refresh のみ | ✅ | §FR-5.3 |

#### Tier 別の必要度

| Tier | 必須度 | 採否判断 |
|---|---|---|
| **必須対応**（① OIDC 受信・発行 / OAuth Code+PKCE / Client Credentials / JWKS / Discovery）| 全顧客で使う | **Cognito / Keycloak どちらも対応** |
| **Should**（② SAML SP / Social Login / WebAuthn / TOTP / SCIM 受信）| 多くの顧客で必要（B2C 対応含む）| **Cognito / Keycloak どちらも対応** |
| **Conditional Must**（③ SAML IdP / LDAP / Device Code / Token Exchange / mTLS / DPoP / Back-Channel Logout / Kerberos / Access Token Revocation / OAuth 2.0 Broker）| 顧客要件次第で必須化 | **1 つでも該当すれば Keycloak 必須化** |
| **Could (extension)**（WS-Federation）| 古い ADFS 環境のみ、推奨は SAML/OIDC 移行 | extension 採用 or 顧客に IdP 変更依頼 |
| **オプション・非推奨**（④ SMS OTP / Email OTP）| レガシー互換のみ | NIST 非推奨、新規実装では Passkey 推奨 |

#### プラットフォーム別カバー率

| プラットフォーム | 必須対応 (①) | Should (②) | Conditional Must (③) | 合計 |
|---|:---:|:---:|:---:|---|
| **Cognito Lite** | ✅ | ⚠ Passkey 不可 | ❌ ほぼ全部不可 | 基本機能のみ |
| **Cognito Essentials** | ✅ | ✅ Passkey 可 | ❌ ③は不可 | 基本 + Passkey |
| **Cognito Plus** | ✅ | ✅ + 侵害検出 | ❌ ③は不可 | 基本 + 高度な MFA |
| **Keycloak OSS / RHBK** | ✅ | ✅ | ✅ **すべて対応** | **フルカバー** |

→ **「結局どれに対応するか」= 上記 22 プロトコル**（重複含む方向別カウント）。そのうち **必須・Should は両プラットフォーム共通**、**Conditional Must の領域は顧客要件次第で Keycloak 必須化** という構造。

→ Cognito 不可マーク（**K-XX**）の詳細は [reference/cognito-knockout-conditions.md](../../../reference/cognito-knockout-conditions.md) を参照。

### §FR-2.0.D 不採用プロトコルと判断根拠（ヒアリングで挙がっても採用しない）

> **本サブセクションで定めること**: §FR-2.0.C で採用対象外とした **業界既知だが本基盤で採用しないプロトコル** と、その判断根拠を明示。顧客ヒアリングで挙がった場合の即答資料 + 設計判断の整合性を確保。
> **主な判断軸**: 業界利用実態 / 後継プロトコル存在 / セキュリティ / Keycloak 対応状況
> **§FR-2.0 全体との関係**: §FR-2.0.C「採用するプロトコル」の対をなすセクション

#### 不採用プロトコル 6 種と判断根拠

| プロトコル | 状況 | 不採用理由 | 代替手段 |
|---|---|---|---|
| **WS-Trust** | Microsoft 系レガシー、Active Federation（API ベース）| ❌ ほぼ使われていない、業界トレンド = OIDC/SAML 移行 | SAML / OIDC へ移行依頼 |
| **OpenID 1.0 / 2.0** | OIDC の前身、廃止済 | ❌ **2014 年に OIDC が後継として標準化、既に廃止** | OIDC 採用 |
| **CAS** (Central Authentication Service) | 学術系 SSO プロトコル | ❌ 学術用途のみ、B2B SaaS では極めて稀 | SAML（Shibboleth）で代替 |
| **PKI / X.509 クライアント証明書** | 政府 / 金融 / 軍事の高セキュリティ用途 | ⚠ **別軸の認証**（フェデレーション ではない）、本基盤では mTLS（§FR-1.1）でカバー | mTLS Client Auth (RFC 8705) |
| **Smart Card** | 政府 / 軍事 | ⚠ **別軸の認証**、ユーザー直接認証手段 | 該当顧客なら mTLS + PKI |
| **HTTP Basic Auth / Digest Auth** | レガシー Web 認証 | ❌ **平文 / 弱ハッシュ、TLS 必須**、フェデレーションには不向き | OIDC / SAML へ移行 |

#### 顧客ヒアリングで挙がった場合の対応指針

| 顧客の発言 | 推奨回答 |
|---|---|
| 「**WS-Trust を使いたい**」 | 「WS-Trust はほぼ使われていないため対応していません。SAML / OIDC への移行をご検討ください」 |
| 「**OpenID 2.0 のままです**」 | 「OpenID 2.0 は廃止されており、OIDC への移行が業界標準です。Entra / Google Workspace への移行で対応可能」 |
| 「**CAS を使っています**」 | 「CAS は学術系の SSO プロトコルです。多くの IdP（Shibboleth / Keycloak 等）が SAML 2.0 も同時提供しているため、SAML 経由での接続をご提案します」 |
| 「**PKI / Smart Card で認証したい**」 | 「PKI / Smart Card は本基盤のフェデレーション層ではなく、**ユーザー直接認証層**で対応します（mTLS Client Auth, FR-1.1）」 |
| 「**WS-Federation のみの古い ADFS です**」 | 「ADFS 2019+ なら OIDC / SAML 対応可能ですので、ADFS のバージョンアップをご検討ください。やむを得ない場合は WS-Federation extension で対応可能（Keycloak 26.x）」 |

#### 採用プロトコルへの誘導戦略

| 現状の顧客 IdP | 推奨移行先 | 移行のメリット |
|---|---|---|
| WS-Federation（古い ADFS）| ADFS 2019+ で OIDC/SAML、または Entra ID 移行 | ✅ Microsoft 自身が推奨 / 新機能利用 |
| OpenID 2.0 | OIDC 採用 IdP（Auth0 / Okta / Google Workspace）| ✅ 業界標準 / 機能豊富 |
| CAS | Shibboleth SAML 2.0 | ✅ 学術界主流、本基盤対応 |
| HTTP Basic Auth | OIDC / SAML / SAML Sign-In | ✅ セキュリティ大幅向上 |

→ **本基盤の方針**: 「**OIDC + SAML 2.0 + Social Login + LDAP + Kerberos の組合せで業界 95%+ をカバー**」、不採用プロトコル要望には**代替手段を提案して顧客 IdP の近代化を支援**。

### 本章で扱うサブセクション

| サブセクション | 内容 | 関連 FR |
|---|---|---|
| §FR-2.1 IdP 接続種別 | 受け入れ可能なプロトコル / 主要 IdP 製品の接続実績 | FR-FED-001〜007 |
| §FR-2.2 ユーザー処理 | JIT プロビジョニング / 属性マッピング / MFA 重複回避 | FR-FED-008, 009, 012 |
| §FR-2.3 マルチテナント運用 | 複数 IdP 並行運用 / 顧客追加オンボーディング / Home Realm Discovery | FR-FED-010, 011, 013 |

---

## §FR-2.1 IdP 接続種別（→ FR-FED §2.1）

> **このサブセクションで定めること**: 本基盤が外部 IdP として**受け入れ可能なプロトコル**（OIDC / SAML 2.0 / LDAP）と、想定する**主要 IdP 製品**（Entra ID / Okta / HENNGE One 等）の接続実績。   
> **主な判断軸**: 御社・御社顧客の IdP 構成、SAML IdP 発行モード / LDAP 直接連携の要否（Keycloak 必須化に直結）   
> **§FR-2 全体との関係**: §FR-2.1 = 接続「できる範囲」、§FR-2.2 = 受け入れたユーザーの「処理」、§FR-2.3 = 「並行運用」

「**どんな顧客 IdP でも接続可能**」という capability を示す。具体接続先は §B 確認後に確定。

### 業界の現在地（2026 年時点の調査結果）

**グローバル**:
- **Microsoft Entra ID + Okta が 2 強**（合計でエンタープライズ需要の約 80% カバー）
- **Google Workspace** が残りの多くをカバー
- Ping / IBM / Oracle / Thales / Auth0 が次集団

**日本特有**:
- **HENNGE One** — 国内 IDaaS シェア No.1
- **GMO Trust Login** — 累計 1 万社以上の導入実績
- **Cloud Gate UNO、Extic** — 国産 IDaaS
- 共通点：いずれも **SAML 2.0 を主軸**（OIDC も対応進行中）

**プロトコル動向**:
- OIDC が新規システムの主流。SAML は依然エンタープライズ・SaaS で広く使用
- LDAP / Active Directory 直接連携はレガシー領域で根強い需要

### 我々のスタンス（基本方針に基づく）

| 基本方針の柱 | IdP 接続での実現 |
|---|---|
| **絶対安全** | 業界標準（OIDC 1.0 / SAML 2.0）準拠の IdP のみを受け入れる。独自プロトコルは受け入れない |
| **どんなアプリでも** | **OIDC または SAML が話せる IdP なら何でも接続可能**。Cognito / Keycloak 両方でグローバル主要 + 日本主要 IdP をカバー |
| **効率よく認証** | Broker パターンで顧客追加でも各システム変更不要（[§1](../common/01-architecture.md)）|
| **運用負荷・コスト最小** | OIDC は Discovery 自動化、SAML は Metadata XML 投入で完結。両方 Terraform 管理可能 |

### 対応能力マトリクス（裏どり）

**A. 接続方法（プロトコル別の対応）**

「**どんなプロトコルを話す IdP まで受けられるか**」の境界線：

| プロトコル | Cognito | Keycloak (OSS / RHBK) | 備考 |
|---|:---:|:---:|---|
| **OIDC IdP**（標準準拠なら何でも）| ✅ 標準対応 | ✅ 標準対応 | RFC 6749 / OIDC 1.0 |
| **SAML 2.0 SP モード**（外部 IdP からのアサーション受け入れ）| ✅ 標準対応 | ✅ 標準対応 | エンタープライズ / 日本 IDaaS が主に SAML |
| **SAML 2.0 IdP モード**（共通基盤が SAML を発行）| ❌ 不可 | ✅ 標準対応 | 共通基盤が他システムに対して SAML 発行 |
| **LDAP / Active Directory 直接連携** | ❌ 不可 | ✅ User Federation（標準機能）| ADFS 経由なし、AD 直結 |
| 独自プロトコル IdP | ❌ | ❌ | OIDC/SAML へのラッパー設計を要請 |

**B. 接続先（主要 IdP の対応実績）**

「**実際に名指しされる IdP を接続できるか**」の確認：

| IdP | プロトコル | Cognito | Keycloak (OSS / RHBK) | 備考 |
|---|---|:---:|:---:|---|
| Microsoft Entra ID（旧 Azure AD）| OIDC / SAML | ✅ | ✅ | グローバル No.1 |
| Okta | OIDC / SAML | ✅ | ✅ | グローバル 2 番手 |
| Google Workspace | OIDC / SAML | ✅ | ✅ | テック企業に多い |
| Auth0 | OIDC | ✅（PoC 実証済）| ✅（PoC 実証済）| Entra ID 代替として PoC 検証 |
| HENNGE One | SAML | ✅ | ✅ | 国内 IDaaS シェア No.1 |
| GMO Trust Login | SAML | ✅ | ✅ | 国内中堅、1 万社実績 |
| Cloud Gate UNO / Extic | SAML / OIDC | ✅ | ✅ | 国産 IDaaS |
| 顧客独自 SAML / OIDC IdP | SAML / OIDC | ✅ | ✅ | プロトコル準拠なら可 |
| ソーシャル（Google / Facebook / Apple / Amazon 等）| OIDC | ✅ ネイティブ統合 | ✅ ネイティブ統合 | コンシューマ向け |

### ベースライン

**1. プロトコル対応範囲**

| プロトコル | 対応 | 採用プラットフォーム |
|---|:---:|---|
| **OIDC 1.0**（外部 IdP として受け入れ） | ✅ Must | Cognito / Keycloak 両方 |
| **SAML 2.0 SP モード**（外部 IdP として受け入れ）| ✅ Must | Cognito / Keycloak 両方 |
| **SAML 2.0 IdP モード**（共通基盤が SAML を発行）| 要件次第 | **Keycloak のみ**（Cognito 不可）|
| **LDAP / AD 直接連携** | 要件次第 | **Keycloak のみ**（Cognito 不可）|
| 独自プロトコル IdP | ❌ Won't | OIDC/SAML へのラッパー設計を要請 |

**2. 主要 IdP の接続実績**（我々が裏どり済み）

| IdP | 種別 | 接続実績 | 想定優先度 |
|---|---|:---:|:---:|
| Microsoft Entra ID（旧 Azure AD）| OIDC / SAML | PoC で Auth0 を Entra ID 代替検証 | **Must 候補** |
| Auth0 | OIDC | ✅ PoC Phase 2, 7 で実証 | 検証完了 |
| Okta | OIDC / SAML | 公式手順あり | Should 候補 |
| Google Workspace | OIDC / SAML | 公式手順あり | Could 候補 |
| HENNGE One | SAML | 国内 No.1、SAML 経由で接続可能 | 国内顧客向け Must 候補 |
| GMO Trust Login | SAML | 国内 SAML 対応 | 国内中堅向け |
| 顧客独自 SAML / OIDC IdP | SAML / OIDC | プロトコル準拠なら接続可能 | 要件次第 |

**3. Custom Domain**

| 項目 | ベースライン |
|---|---|
| 認証エンドポイント URL | `auth.example.com` 等の顧客指定ドメイン |
| Cognito 実現方法 | Hosted UI Custom Domain + ACM 証明書 |
| Keycloak 実現方法 | Hostname 設定 + ACM/ALB 証明書 |
| 必要性 | フィッシング耐性 + ブランディング + DR 時の URL 統一に重要 |

### 接続対象 IdP の 2 つの分類（[§FR-1.2.0.0](01-auth.md#fr-1200-ローカルユーザーとは何か--利用者カテゴリ別の分析) 利用者カテゴリと連動）

本基盤が受け入れる IdP は、**利用者カテゴリ** によって 2 つに分類される:

| 分類 | 接続元 IdP | 認証する利用者 | 採用判断 |
|---|---|---|---|
| **(i) 顧客 IdP** | 顧客企業の IdP（Entra ID / Okta / HENNGE 等） | P-2 テナント管理者 / P-3 IdP あり顧客従業員 | **本章の主対象** |
| **(ii) 弊社内 IdP** | 弊社運用組織の社内 IdP（Entra ID 等） | P-1 基盤運用管理者 | **[§FR-1.2.0.0](01-auth.md#fr-1200-ローカルユーザーとは何か--利用者カテゴリ別の分析) γ シナリオ採用時に Must** |

→ (ii) 弊社内 IdP の接続は、γ シナリオ（管理者層のみローカル）採用時に「P-1 を弊社内 IdP 経由で認証 + Break Glass を最小ローカル管理」とするための前提。**Cognito / Keycloak 両方とも (i) と同じ仕組み（OIDC IdP 接続）で実現可能** で、構成上は単に「もう 1 つの IdP オブジェクト」を追加するだけ。

### IdP を持たない顧客への対応方針（γ / β シナリオの判定根拠）

[§FR-1.2.0.0](01-auth.md#fr-1200-ローカルユーザーとは何か--利用者カテゴリ別の分析) で議論したローカルユーザー範囲シナリオは、**顧客に IdP がない場合の対応方針**として §FR-2 でも具体化が必要:

| 顧客側状況 | γ シナリオ採用時の本基盤対応 | β シナリオ採用時の本基盤対応 |
|---|---|---|
| **顧客が IdP を持つ**（Entra / Okta / HENNGE 等）| フェデ受け入れ（標準） | フェデ受け入れ（標準） |
| **顧客が IdP を持たない（大手企業）** | **顧客に IdP 導入を依頼**（Microsoft 365 / Google Workspace のテナントを起点に Entra/Workspace を IdP 化等の支援案を提示） | 顧客判断（IdP 導入 or ローカルユーザー受け入れ） |
| **顧客が IdP を持たない（中小企業）** | **顧客取得を断念 or 営業所属判断**（γ の制約として明示） | **ローカルユーザー受け入れ** + [§FR-2.3.2 オンボーディング](#fr-232-顧客追加オンボーディング--fr-fed-011) の Quick Start プロセス |
| **顧客が独自プロトコル IdP のみ** | OIDC / SAML へのラッパー設計を依頼 | 同左 |

→ **シナリオ採用判断は本基盤のマーケットターゲット**を決める意思決定。営業観点での影響大。

### TBD / 要確認

**A. 御社・御社顧客の IdP 構成（影響最大）**

| 確認項目 | 回答例 |
|---|---|
| **基盤運用組織（弊社）の社内 IdP** | Entra ID / Okta / HENNGE One / オンプレ AD / なし（→ P-1 認証方式に直結、[§FR-1.2.0.0](01-auth.md#fr-1200-ローカルユーザーとは何か--利用者カテゴリ別の分析)）|
| エンドユーザー（顧客企業）の IdP | リスト + 各社の種別 |
| 想定する顧客企業数（1 年後 / 3 年後）| N 社 / M 社 |
| 顧客企業の IdP 種別の比率 | OIDC 系 X% / SAML 系 Y% / AD 直結 Z% |
| **顧客の IdP 普及率** | 90%+ → γ シナリオ採用可 / 50-90% → β / <50% → α 必要（[§FR-1.2.0.0](01-auth.md#fr-1200-ローカルユーザーとは何か--利用者カテゴリ別の分析)）|
| **IdP のない顧客への営業方針** | IdP 導入支援 / ローカルユーザー許容 / 顧客取得を断念 |

**B. プロトコル要件（プラットフォーム選定に直結）**

| 確認項目 | 影響 |
|---|---|
| SAML IdP モード（共通基盤が SAML 発行）が必要か | **Yes → Keycloak 必須**（Cognito 不可、FR-FED-006）|
| LDAP / AD 直接連携が必要か | **Yes → Keycloak 必須**（Cognito 不可、FR-FED-007）|
| 独自プロトコル IdP の有無 | ある場合は接続不可、ラッパー設計を要請 |

**B'. SCIM Provisioning（プロビジョニング層、[§FR-7.4.0](07-user.md#fr-740-scim-の位置づけと本基盤のスタンス) と連動）**

> 本基盤は SCIM 2.0 受信機能を実装する方針。顧客側の SCIM 対応状況を **顧客ごと**に確認する。

| 確認項目 | 回答例 |
|---|---|
| **Q1: 顧客 IdP の SCIM Provisioning 対応** | Entra ID Premium P1+ / Okta（全プラン）/ Google Cloud Identity Premium / HENNGE One（要確認）/ 自社製（通常未対応）/ なし / 不明 |
| **Q2: 顧客の SCIM 連携採用意思** | 採用希望 / 採用しない / 判断保留（顧客側で IdP 上位ライセンス + 連携設定が必要な旨を伝えた上で）|
| **Q3（詳細）**: 顧客 HR システムと IdP の連携状況、入退社フローの現状 | 顧客内部の現状（Workday / SAP / 国産 HR 系 / なし 等）|
| **Q4（Fallback）**: SCIM 不採用時、退職者 deprovisioning 責任を顧客側で持てるか | 顧客責任 / 弊社で定期バッチ運用希望 |

→ Q1 / Q2 の答えで [§FR-7.4](07-user.md) のプロビジョニング運用方式が決まり、退職者対応 SLA（[§NFR-6.5 D-3](../nfr/06-operations.md)）にも影響。

**C. Custom Domain**

| 確認項目 | 回答例 |
|---|---|
| カスタムドメインを使うか | 使う（推奨）/ 使わない |
| 想定ドメイン | `auth.example.com` 等 |
| TLS 証明書管理 | ACM / 既存証明書 |

### 参考資料（業界動向の裏どり）

- [ETR Research: Identity Security 2026](https://research.etr.ai/blog-observatory/identity-security-entra-and-okta-set-the-pace)
- [WorkOS: Best IAM Providers 2026](https://workos.com/blog/best-identity-access-management-providers-2026)
- [Cognito SAML IdP 公式](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-saml-idp.html)
- [Cognito OIDC IdP 公式](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-oidc-idp.html)
- [Keycloak Identity Brokering 公式](https://www.keycloak.org/docs/latest/server_admin/index.html)
- [HENNGE One IdP 解説](https://hennge.com/jp/service/one/glossary/what-is-idp/)
- [ITreview SSO 比較（日本）](https://www.itreview.jp/categories/sso)

---

## §FR-2.2 フェデレーションユーザー処理（→ FR-FED §2.2）

> **このサブセクションで定めること**: 外部 IdP で認証されたユーザーを本基盤がどう受け入れ・正規化するか（JIT プロビ・属性マッピング・MFA 重複回避）。Broker パターンの「**属性変換層**」の中核。   
> **主な判断軸**: SCIM 併用の必要性、属性命名規則、外部 IdP の MFA 主張をどこまで信頼するか   
> **§FR-2 全体との関係**: §FR-2.1 で「接続できる IdP」を決め、§FR-2.2 で「接続後の処理」を決め、§FR-2.3 で「並行運用」を扱う。

3 つの性質（プロビ / マッピング / MFA）に分けて記載。

### §FR-2.2.1 JIT プロビジョニング（→ FR-FED-008）

> **このサブ・サブセクションで定めること**: 外部 IdP 経由で初めてログインしたユーザーを基盤側で自動作成する方式（JIT）と、SCIM 2.0 との併用方針。   
> **主な判断軸**: 退職時の即時 deprovision 要件、SCIM 連携の必要性、デフォルト権限レベル   
> **§FR-2.2 内の位置付け**: 3 つのユーザー処理のうち「**初回作成**」を扱う。属性は §FR-2.2.2、MFA は §FR-2.2.3

#### 業界の現在地

| 方式 | 何をする | いつ使う |
|---|---|---|
| **JIT (Just-in-Time)** | SSO ログイン時に基盤側でユーザーレコードを自動作成 | 日常の新規ログイン受け入れ |
| **SCIM 2.0** | IdP 側からの API で事前プロビジョニング + ライフサイクル管理 | 大量投入・大量無効化・退職フロー |
| **推奨：ハイブリッド** | JIT で日常、SCIM で一括 | エンタープライズ |

業界ベストプラクティス（2026 年）:
- **デフォルト権限は最小**（後で属性マッピングでロール上書き）
- **JIT 生成イベントは必ず監査ログ記録**（誰がいつ自動生成されたか追跡可能に）

#### 我々のスタンス（基本方針に基づく）

| 基本方針の柱 | JIT 領域での実現 |
|---|---|
| **絶対安全** | デフォルト最小権限。JIT 生成は監査ログ必須 |
| **どんなアプリでも** | OIDC / SAML 標準準拠なら JIT 自動 |
| **効率よく** | 顧客企業の新規ユーザーは初回 SSO で即時利用可（事前プロビ不要） |
| **運用負荷・コスト最小** | JIT は自動、追加ライセンス不要。SCIM 併用は顧客要件に応じて |

#### 対応能力マトリクス

| 機能 | Cognito | Keycloak (OSS / RHBK) | 備考 |
|---|:---:|:---:|---|
| JIT プロビジョニング（OIDC）| ✅ 自動（初回ログイン時）| ✅ First Broker Login Flow | 両方標準 |
| JIT プロビジョニング（SAML）| ✅ 自動 | ✅ 自動 | 同上 |
| SCIM 2.0 プロビジョニング | ⚠ ネイティブ非対応（自前実装要） | ✅ プラグイン対応 | エンタープライズ要件次第 |
| デフォルト権限の指定 | ✅ App Client 設定 / Pre Token Lambda | ✅ Default Roles / First Login Flow | 両方標準 |
| JIT 生成監査ログ | ✅ CloudTrail | ⚠ Event Listener 自前実装 | Cognito が楽 |

#### ベースライン

| 項目 | ベースライン |
|---|---|
| 方式 | 初回 SSO ログイン時に基盤側でユーザーレコード自動作成 |
| デフォルト権限 | **最小権限**（業界ベストプラクティス）。後から属性マッピングでロール上書き |
| SCIM 併用 | 顧客が SCIM 対応 IdP の場合は併用（大量退職時の一括 deprovision 用）|
| 監査ログ | JIT 生成イベントを CloudWatch / Event Listener に出力 |

#### TBD / 要確認

| 確認項目 | 回答例 |
|---|---|
| JIT のみで十分か / SCIM 併用が必要か | 想定退職フローの規模次第 |
| デフォルト権限レベル | "最小権限" 標準で OK か、別レベルか |
| 既存ユーザーの初期投入方法 | バルクインポート / SCIM / JIT 任せ |
| JIT 生成イベントの通知先 | CloudWatch / SIEM / メール通知 |

---

### §FR-2.2.1.A 同一テナント内ユーザー重複の扱い

> **このサブ・サブセクションで定めること**: 同一テナント内で同一人物が複数 IdP / ローカル経由で別レコード化する重複問題と、その統合（アカウントリンク）または独立扱いの設計判断。   
> **主な判断軸**: 顧客が複数 IdP を持つか、IdP 切替計画があるか、ローカル + フェデ併存があるか、乗っ取りリスクを許容できるか   
> **§FR-2.2 内の位置付け**: §FR-2.2.1 JIT 時の「**既存ユーザー検出と統合判断**」を扱う。クロステナント重複は [§FR-2.3.A.1](#fr-23a1-何が分離共有されているか--論理分離の実態顧客が必ず聞く論点) で扱う

#### 問題の所在: 同一テナント内で重複が発生する 7 シナリオ

| # | シナリオ | 発生原因 |
|:---:|---|---|
| 1 | 顧客が複数 IdP を持つ（例: Acme = Entra ID + HENNGE 併用） | 各 IdP からの `sub` が別 |
| 2 | IdP 切り替え期間（例: Okta → Entra への移行中） | 旧 `sub` と新 `sub` が並存 |
| 3 | ローカル + フェデの併存 | 先にローカル登録、後から IdP 接続で別レコード作成 |
| 4 | SCIM プロビ + JIT 競合 | 事前 SCIM の `userName` ≠ JIT 時の `sub` |
| 5 | 退職 → 再入社 | IdP 上は新規アカウントだが基盤側に旧履歴あり |
| 6 | 複数役割の表現 | 1 人 = 複数組織コードで別レコード化 |
| 7 | 手動登録 + 自動流入 | 管理者の `AdminCreateUser` vs JIT 流入で別レコード |

#### 7 シナリオの図解（各々がどう「別レコード」を生むか）

> 重複が発生した状態は「同じテナント内に同一人物のユーザーレコードが複数存在し、本基盤の `sub` が別々」であることが核心。**`sub` が分かれると認可・履歴・退職処理・MFA 登録が分断**される。理想は「同一人物 = 1 プロファイル + 複数 IdP リンク（`identities` 配列）」（業界標準 = Microsoft Entra / Auth0 / Okta）。本節は「どうやってその理想状態に収束させるか」の前提となる重複発生メカニズムを図解で示す。

**重複が発生した状態のイメージ**:

```mermaid
flowchart LR
    subgraph Person["現実世界の 1 人（例: 田中 alice@acme.co.jp）"]
        P[Alice]
    end

    subgraph Hub["共通基盤 Acme テナント内のユーザー DB（重複した状態）"]
        U1["sub=abc111<br/>identities=[Entra]<br/>roles=[admin]"]
        U2["sub=def222<br/>identities=[HENNGE]<br/>roles=[]"]
        U3["sub=ghi333<br/>identities=[local PW]<br/>roles=[viewer]"]
    end

    P -->|Entra で SSO| U1
    P -->|HENNGE で SSO| U2
    P -->|ローカル PW で| U3

    style U1 fill:#ffebee,stroke:#c62828
    style U2 fill:#ffebee,stroke:#c62828
    style U3 fill:#ffebee,stroke:#c62828
```

##### シナリオ 1: 複数 IdP 併用（最頻出）

```mermaid
sequenceDiagram
    autonumber
    actor Alice
    participant Entra
    participant HENNGE
    participant Hub as 共通基盤

    Note over Alice: 月: 業務で Entra から
    Alice->>Entra: ログイン
    Entra->>Hub: assertion(sub=ENTRA-xyz, email=alice@acme.co.jp)
    Hub-->>Hub: JIT 作成（基盤 sub=abc111）

    Note over Alice: 翌週: 別アプリ用に HENNGE から
    Alice->>HENNGE: ログイン
    HENNGE->>Hub: assertion(sub=HEN-789, email=alice@acme.co.jp)
    Hub-->>Hub: ❌ 同一 email だが別 sub → 別レコード def222 作成
```

##### シナリオ 2: IdP 切替期間（Okta → Entra 移行中）

```mermaid
gantt
    title Acme 社の IdP 切替（例: 2026Q3-Q4）
    dateFormat YYYY-MM-DD
    section 旧 Okta
    全社員 Okta 利用     :done, 2025-01-01, 2026-09-30
    並走（一部 Okta 残）   :crit, 2026-09-01, 2026-12-31
    section 新 Entra
    並走（一部先行移行）   :active, 2026-09-01, 2026-12-31
    Entra 単独運用       :2026-12-01, 2027-06-30
```

→ 並走 4 ヶ月の間、**同じ社員が Okta と Entra の両方からログインしてくる** ため、`sub` が異なる 2 レコードが基盤に並存。

##### シナリオ 3: ローカル + フェデの併存

```mermaid
flowchart LR
    T1["2026-01<br/>Acme オンボード時<br/>IdP 未連携"] -->|管理者がローカル<br/>PW 登録| L["基盤レコード<br/>sub=ghi333<br/>local PW"]
    T2["2026-06<br/>Acme が Entra 連携開始"] -->|Alice が Entra でログイン| F["基盤レコード<br/>sub=abc111<br/>identities=Entra"]
    L -.同じ Alice.-> F
    style L fill:#fff3e0
    style F fill:#e3f2fd
```

##### シナリオ 4: SCIM プロビ + JIT 競合

```mermaid
sequenceDiagram
    autonumber
    participant HR as Acme HR
    participant SCIM as Acme IdP (SCIM Client)
    participant Hub as 共通基盤
    actor Alice

    Note over HR,SCIM: 入社処理（事前）
    HR->>SCIM: 新入社員 Alice 登録
    SCIM->>Hub: SCIM POST /Users (userName=alice, email=alice@acme.co.jp)
    Hub-->>Hub: レコード作成（sub=scim-001、IdP リンク無し）

    Note over Alice: 数日後: 初回ログイン
    Alice->>Hub: Entra 経由でログイン
    Hub-->>Hub: ❌ JIT が「SCIM 作成済み」を検知できず別レコード作成
```

##### シナリオ 5: 退職 → 再入社

```mermaid
flowchart LR
    A1["2024-04 入社<br/>sub=old-555<br/>roles=[admin]"] -->|2025-03 退職| A2["soft-delete<br/>or 物理削除"]
    A2 -->|2026-05 再入社| A3["新 sub=new-777<br/>roles=[viewer]<br/>※過去の admin 履歴ロスト"]
    style A1 fill:#e8f5e9
    style A2 fill:#eeeeee
    style A3 fill:#fff3e0
```

→ IdP 上は **新規アカウント扱い**（社員番号が再採番されるケースも多い）、基盤上は **旧 sub の履歴・監査ログが残る**。同一人物として復活させるか、別人扱いとするかの **運用判断（コンプライアンス論点）** が必要。

##### シナリオ 6: 複数役割の表現（1 人 = 複数組織コードで多重所属）

```mermaid
flowchart TB
    Alice["田中 Alice"]
    Alice -->|営業所長としての権限<br/>org_code=SALES01| R1["sub=role1-aaa<br/>roles=[sales_manager]"]
    Alice -->|PJ マネージャ権限<br/>org_code=PJ-X| R2["sub=role2-bbb<br/>roles=[pm]"]
    style R1 fill:#e3f2fd
    style R2 fill:#fff3e0
```

→ レアだが業務複雑な業種（建設・コンサル・SI 多重所属）で発生。アプリ側の文脈切替で対応すべき要件か、基盤で別レコードを許すかの判断。

##### シナリオ 7: 手動登録 + 自動流入の競合

```mermaid
sequenceDiagram
    autonumber
    participant Admin as テナント管理者
    participant Hub as 共通基盤
    actor Alice

    Admin->>Hub: AdminCreateUser(email=alice@acme.co.jp, role=admin)
    Hub-->>Hub: ローカル PW 仮レコード作成（sub=manual-100）

    Note over Alice: 翌日: 招待メールではなく Entra SSO で来てしまう
    Alice->>Hub: Entra 経由ログイン
    Hub-->>Hub: ❌ 既存ローカルと突合せず別レコード作成（sub=jit-200）
```

#### 業界の現在地

- 業界標準は「**同一人物 = 1 プロファイル + 複数 IdP リンク**」（Microsoft Entra / Auth0 / Okta などの実装）
- リンク時の最大リスクは「**他人 email アサーション流入による乗っ取り**」
- AWS Cognito 公式は `AdminLinkProviderForUser` を **"trusted IdPs only"** と警告
- Keycloak は First Broker Login Flow で **Confirm Link / Email OTP / Re-auth** を標準フロー化

#### 我々のスタンス（基本方針に基づく）

| 基本方針の柱 | 同一テナント重複扱いでの実現 |
|---|---|
| **絶対安全** | 自動リンクは原則しない。**Email OTP 確認** または **既存パスワード再認証** を経たリンクのみ。Trust Email は IdP 単位で明示判断 |
| **どんなアプリでも** | リンク後は単一 `sub` で見える（`identities` クレームで複数 IdP 可視化）|
| **効率よく** | SCIM 連携時は事前リンク（運用負荷で重複検出が起きない設計）|
| **運用負荷・コスト最小** | Keycloak は標準フロー、Cognito は Pre Sign-up Lambda + `AdminLinkProviderForUser` で実装 |

#### 設計の三択

| 案 | 設計方針 | メリット | デメリット | 採用例 |
|:---:|---|---|---|---|
| **A 統合（リンク）派** | 同一人物 → 1 プロファイル / 複数 IdP リンク | UX 一貫、データ重複なし、deprovision 一括 | リンクロジック誤動作で乗っ取りリスク | **Microsoft Entra / Auth0 / Okta（業界標準）** |
| **B 独立（許可）派** | IdP 経由 = 別ユーザー、重複を許容 | 攻撃面狭い、認証経路ごとに独立 | UX 悪化、データ重複、ロール管理混乱 | レガシー設計、移行期に一時採用 |
| **C ハイブリッド** | IdP 経由は独立、ローカルとは統合 | 規制業種で許容しやすい | 設計複雑、説明難 | 慎重派、規制業種 |

→ **推奨ベースライン: A 統合（リンク）派 + Trust Email を IdP 単位で慎重制御 + Email OTP / 再認証確認**

#### 対応能力マトリクス

| 機能 | Cognito | Keycloak (OSS / RHBK) | 備考・出典 |
|---|:---:|:---:|---|
| 同一プロファイルへの IdP リンク | ✅ `AdminLinkProviderForUser` API | ✅ First Broker Login Flow | 両方標準 |
| **リンク可能な IdP 数上限** | **5（Hard limit）**[^cognito-q08] | 制限なし | AWS 公式: "link up to five federated users to each user profile"[^aws-linking] |
| **リンク時の突合せ属性数上限** | **5（Hard limit）** | 制限なし | AWS 公式: "from up to five IdP attribute claims"[^aws-linking] |
| 既存ユーザー検出時の確認フロー | ⚠ Pre Sign-up Lambda 自前実装 | ✅ `Confirm Link Existing Account` / `Verify Existing Account By Email` / `Verify Existing Account By Re-authentication` の 3 認証器を選択 | Keycloak Identity Brokering Docs[^kc-fbl] |
| Detect Existing Broker User（同一 IdP の別ユーザー名検知）| ❌ 自前 | ✅ `Detect Existing Broker User` 認証器 | Keycloak Docs[^kc-fbl] |
| **既ログイン済 IdP の再リンク** | ⚠ **既存プロファイル削除が必要**（監査ログ分断）| ✅ `Detect Existing Broker User` で上書き確認 | AWS 公式: "you must first delete their existing profile"[^aws-linking] |
| 管理 UI からのリンク操作 | ❌ **API のみ**（Console 不可） | ✅ Admin Console + Account Console | AWS 公式: "can't link providers to user profiles in the AWS Management Console"[^aws-linking] |
| ユーザー自身による自己リンク | ❌ | ✅ Account Console 経由 | 同上 |
| Trust Email の IdP 単位制御 | ⚠ 暗黙的 | ✅ IdP 設定で明示 | Keycloak Identity Brokering 設定 |
| `identities` クレーム出力（複数 IdP 可視化）| ✅ ID Token | ✅ Federated Identities API | 両方標準 |
| 自動リンク（信頼 IdP 前提）| ⚠ Pre Sign-up Lambda で自前 | ✅ `Automatically Set Existing User` 認証器 | Keycloak Docs[^kc-fbl]、業界標準は **自動リンクは非推奨** |
| 退職 → 再入社時の旧履歴復活 | ⚠ プラットフォーム標準なし、soft-delete + 承認の運用設計マター | ⚠ 同左 | **両者ともシナリオ 5 はプラットフォーム選定で決まらない** |

[^cognito-q08]: [cognito-knockout-conditions.md Q-08](../../../reference/cognito-knockout-conditions.md) — Identities linked to a user は 5 Hard limit
[^aws-linking]: [AWS 公式 - Linking federated users to an existing user profile](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-identity-federation-consolidate-users.html)（"Things to know about linking federated users" セクション）
[^kc-fbl]: [Keycloak Server Admin Guide - First Login Flow](https://www.keycloak.org/docs/latest/server_admin/index.html#_default-first-login-flow) — `Confirm Link Existing Account` / `Verify Existing Account By Email` / `Verify Existing Account By Re-authentication` / `Detect Existing Broker User` / `Automatically Set Existing User` 認証器の組合せで重複検出を宣言的に構成

#### シナリオ別の実装可否（7 シナリオ × 2 プラットフォーム）

| # | シナリオ | Cognito での実現 | Keycloak での実現 |
|:---:|---|---|---|
| 1 | 複数 IdP 併用 | Pre Sign-up Lambda + `AdminLinkProviderForUser`（**自前 200〜500 行**）。**5 IdP までしかリンク不可** | First Broker Login Flow に `Confirm Link` + `Verify by Email` を組むだけ（**追加コード 0**）。IdP 数無制限 |
| 2 | IdP 切替期間 | 同上（移行用に Lambda 増強）| 同上（標準フローで自然に処理） |
| 3 | ローカル + フェデ併存 | Pre Sign-up Lambda + 既存ローカル検索 → Link | First Broker Login Flow で標準動作 |
| 4 | SCIM + JIT 競合 | **Pre Sign-up Lambda で SCIM 作成済みレコードを email/externalId で検索 → Link**（重い実装）| `Detect Existing Broker User` + email 突合（標準） |
| 5 | 退職 → 再入社 | **両プラットフォームとも標準機能なし** — soft-delete + 管理者承認のワークフロー自前運用 | 同左（**運用設計マター**、プラットフォーム選定で決まらない） |
| 6 | 複数役割（多重所属）| アプリ層で文脈切替 or Cognito Groups で属性多重化 | Realm Groups / Composite Roles で表現可。アプリ層対応も推奨 |
| 7 | 手動 + 自動流入 | Pre Sign-up Lambda で AdminCreateUser 済を検出 → Link | First Broker Login Flow で標準動作 |

#### Cognito の落とし穴 3 点（要件定義時に必ず顧客と握る）

公式ドキュメントから確認できた、**Cognito 採用時に契約前に顧客合意が必要な制約**:

| # | 制約 | 影響シナリオ |
|:---:|---|---|
| 1 | **1 ユーザーあたり IdP リンクは 5 個まで（Hard limit）**、突合せ属性も 5 個まで | グローバル製造業（多重子会社で各社が別 IdP）、IdP 切替を複数回経験する顧客で破綻 |
| 2 | **リンク操作の管理コンソール UI なし**（`AdminLinkProviderForUser` API のみ） | 運用者が CLI / カスタム自前 UI でしかリンク作業ができない。テナント管理者委譲（[B-404](../../hearing-checklist.md#b-4-ユーザー管理プロビジョニング-fr-user-6--proposal-fr-221-fr-7)）を顧客に提供する場合、専用 UI 開発が必須化 |
| 3 | **既ログイン済 IdP の再リンクには既存プロファイル削除が必要** | 監査ログ・履歴が分断、退職再入社シナリオ（シナリオ 5）で運用が複雑化 |

→ **B-406 で「あり」回答 + 経路に「複数 IdP」「IdP 切替」「SCIM + JIT 競合」のいずれかが含まれる場合、Cognito は実装工数・ハードリミット・運用 UI 不在で実質ノックアウト**になる可能性が高い。本基盤の **プラットフォーム選定上のキーファクター**（[§C-2.2](../common/02-platform.md) と整合）。

#### セキュリティ上の最大論点：アカウント乗っ取り対策

| 攻撃ベクター | 対策 |
|---|---|
| **悪意ある（or 設定ミス）IdP からの他人 email アサーション流入**（攻撃者が自分の IdP アカウントに被害者 email を設定 → 自動リンクで被害者アカウント乗っ取り） | **Trust Email を自動 true にしない**（IdP 単位で明示判断）+ Email OTP 確認 |
| **同名同 email の偶然衝突** | 突合せキーを email でなく **immutable な `sub` / `objectid` / 雇用 ID** にする |
| **退職者の再入社時のリンク誤動作** | 退職者プロファイルは soft-delete + 管理者承認後リンク |
| **JIT による自動レコード生成と既存ローカル衝突** | First Broker Login Flow / Pre Sign-up Lambda で確認フロー必須 |
| **管理者通知なしのサイレント乗っ取り** | リンクイベントは監査ログ + 管理者通知（[§FR-8.2](08-admin.md) 監査）|

#### ベースライン

| 項目 | ベースライン |
|---|---|
| 重複扱い方針 | **A 統合（リンク）派** |
| 自動リンクの条件 | **原則行わない**。Email OTP 確認 or 既存パスワード再認証を経た上でのみ |
| Trust Email | **IdP 単位で明示設定**。デフォルト false（顧客 IdP は性善説で扱わない）|
| 突合せキー | email（補助）+ **immutable な `sub` / 雇用 ID（プライマリ）** |
| 管理者通知 | リンクイベントは監査ログ + 管理者通知（運用必須） |
| IdP 切替時の連続性 | SCIM 同期で事前リンク、または管理者主導の手動マージ |
| Cognito 採用時の制約 | 1 ユーザーあたり **5 IdP リンクまで（Hard）** — 多 IdP 顧客は Keycloak へ移行検討 |

#### TBD / 要確認（[hearing-checklist.md](../../hearing-checklist.md) B-406〜B-410 と連動）

| 確認項目 | 回答例 |
|---|---|
| 同一テナント内で同一人物が複数経路でアクセスする想定はあるか | あり / なし |
| 想定経路 | 複数 IdP / ローカル + IdP / IdP 切替 / 退職再入社 / SCIM + JIT |
| 重複検出時の挙動 | 自動リンク / Email OTP 確認 / 既存パスワード再認証 / エラー停止 |
| 突合せキー | email / immutable sub / 雇用 ID / カスタム属性 |
| リンクのトリガー | 管理者主導 / ユーザー主導 / 自動 |
| IdP 切替計画の有無 | あり（時期）/ なし |

---

### §FR-2.2.2 属性マッピング / クレーム変換（→ FR-FED-009）

> **このサブ・サブセクションで定めること**: 各 IdP が返す多様な属性名・形式を本基盤の統一クレーム形式（`sub` / `tenant_id` / `roles` 等）に正規化する仕組み。   
> **主な判断軸**: 各システムが JWT に必要とする属性、IdP ごとのクレーム命名差異、Access Token への注入範囲   
> **§FR-2.2 内の位置付け**: 「**属性正規化**」を扱う。JIT は §FR-2.2.1、MFA は §FR-2.2.3。基盤発行クレーム全体像は [§FR-6.1](06-authz.md#71-認証基盤が発行する-jwt-クレーム--fr-authz-51) と整合

#### 業界の現在地

**Identity Broker の核心 = 「乱雑な入力を統一フォーマットに正規化する」属性変換層**

共通の落とし穴：
- IdP ごとの命名揺れ（`email` vs `User.Email` vs `NameID` vs `preferred_username`）
- SAML `NameID` ↔ OIDC `sub` の対応が曖昧
- `groups` クレームを盲信して別テナントのロールが混入
- 重複アカウント（同一ユーザーが複数 IdP 経由で別アカウントに）
- 属性更新タイミング（初回 JIT 時のみ vs 毎回上書き）

#### 我々のスタンス（基本方針に基づく）

| 基本方針の柱 | 属性マッピング領域での実現 |
|---|---|
| **絶対安全** | IdP 側クレームを Broker で「正規化」し統一形式 JWT を発行。各システムは Broker JWT のみ信頼 |
| **どんなアプリでも** | Entra `tid` / Okta `org_id` / HENNGE 属性 等の差異を吸収し、常に同じクレーム名で各システムに渡す |
| **効率よく** | マッピングは宣言的に記述（Terraform / Admin Console）、コード書かない |
| **運用負荷・コスト最小** | Cognito は `attribute_mapping`、Keycloak は IdP Mapper で完結。高度ロジックのみ Lambda / Custom Mapper |

#### 対応能力マトリクス

| 機能 | Cognito | Keycloak (OSS / RHBK) | 備考 |
|---|:---:|:---:|---|
| 属性マッピング（宣言的） | ✅ `attribute_mapping`（Terraform） | ✅ IdP Mapper（Admin Console / Terraform） | 両方標準 |
| クレーム変換（複雑ロジック）| ✅ Pre Token Lambda V2（Node.js / Python）| ✅ Protocol Mapper（宣言 + Java カスタム）| 言語の好み次第 |
| Access Token へのクレーム注入 | ⚠ Pre Token Lambda **V2** 必須（V1 は ID Token のみ）| ✅ Protocol Mapper（標準） | V2 はマイクロサービス認可で必須 |
| 属性更新タイミング制御 | ⚠ デフォルト JIT 時のみ、Pre Token Lambda で都度上書き可 | ✅ Sync Mode（Force / Import / Legacy）| Keycloak がフラグ 1 つ |
| 重複アカウント検出 | ⚠ 同じ email でユーザー競合の可能性 | ✅ "Trust Email" + アカウント自動リンク | Keycloak が手厚い |
| NameID / sub マッピング | ✅ `attribute_mapping` | ✅ IdP Mapper | 両方標準 |
| groups → roles 変換 | ✅ Pre Token Lambda | ✅ Protocol Mapper（宣言）| Keycloak が楽 |

#### ベースライン

| 項目 | ベースライン |
|---|---|
| 統一クレーム名 | `sub` / `email` / `name` / `tenant_id` / `roles` / `groups`（共通基盤の固定形式）|
| マッピング層 | Cognito: `attribute_mapping` + Pre Token Lambda V2 ／ Keycloak: IdP Mapper + Protocol Mapper |
| 命名揺れ吸収例 | Entra `tid` → `tenant_id` ／ Okta `org_id` → `tenant_id` ／ HENNGE 属性 → `tenant_id` |
| `groups` の扱い | IdP 側のグループ名を盲信せず、**マッピングテーブルで Broker 側ロールに変換** |
| Access Token への注入 | **Pre Token Lambda V2 必須**（Cognito）／ Protocol Mapper（Keycloak）|
| 属性更新タイミング | 毎回上書き（Sync Mode = Force 相当）を標準とし、特殊要件のみ JIT 時のみ |

#### TBD / 要確認

| 確認項目 | 回答例 |
|---|---|
| 各システムが JWT に必要とする属性 | 属性リスト |
| グループ / ロール / 部署 / テナント の定義 | データモデル |
| 属性更新の即時性要件 | 毎回上書き / JIT 時のみ / 別途トリガー |
| 顧客 IdP ごとの命名差異 | クレーム名対応表 |

---

### §FR-2.2.3 MFA 重複回避（→ FR-FED-012）

> **このサブ・サブセクションで定めること**: 外部 IdP で既に MFA 済みのユーザーに、本基盤側で MFA を**再要求しない**ためのポリシーと実装方式。   
> **主な判断軸**: 外部 IdP の MFA 主張（AuthnContext / `amr` クレーム）をどこまで信頼するか、ロール別の例外要件   
> **§FR-2.2 内の位置付け**: 「**MFA 整合**」を扱う。MFA 全般は [§FR-3 MFA](03-mfa.md)、本サブセクションは「フェデユーザーに対する MFA」のみ

#### 業界の現在地

- 外部 IdP で MFA 済みのユーザーに、Broker 側でも MFA を要求 = **UX 悪化 + 顧客クレーム原因**
- 解決方法は 2 通り：
  - **AuthnContext / `amr` クレーム尊重**: 外部 IdP の MFA 主張を信頼（SAML AuthnContext / OIDC `amr=mfa` 等）
  - **Conditional MFA**: Broker 側で「フェデレーションユーザーは MFA スキップ」のフロー設計
- **既知の問題**: Entra ID + 外部フェデの組み合わせで「ログインを 2 回求められる」事象あり（Microsoft 公式に文書化）

#### 我々のスタンス（基本方針に基づく）

| 基本方針の柱 | MFA 重複回避での実現 |
|---|---|
| **絶対安全** | 外部 IdP の MFA 主張（AuthnContext / `amr`）を検証して信頼。信頼しない外部 IdP は接続しない |
| **どんなアプリでも** | OIDC / SAML 標準の MFA assertion を尊重 |
| **効率よく** | フェデユーザーは MFA を再要求しない（[ADR-009](../../../adr/009-mfa-responsibility-by-idp.md)）|
| **運用負荷・コスト最小** | Keycloak は Conditional OTP（標準フロー）で完結、Cognito は Lambda で実装 |

#### 対応能力マトリクス

| 機能 | Cognito | Keycloak (OSS / RHBK) | 備考 |
|---|:---:|:---:|---|
| MFA 重複回避（AuthnContext 尊重）| ⚠ 個別実装（Pre Token Lambda + Conditional） | ✅ Conditional OTP（標準フロー）| **Keycloak が大幅に楽** |
| MFA `amr` クレーム検査 | ⚠ Lambda で自前検査 | ✅ Authentication Flow で標準対応 | 同上 |
| 高権限ロールへの追加 MFA | ⚠ Lambda + Custom Auth Challenge | ✅ Authentication Flow Conditional | 同上 |
| SAML AuthnContextClassRef 検査 | ⚠ Lambda | ✅ 標準対応 | 同上 |

#### ベースライン

| 項目 | ベースライン |
|---|---|
| 基本方針 | **外部 IdP で MFA 済みのユーザーには Broker 側で再要求しない**（[ADR-009](../../../adr/009-mfa-responsibility-by-idp.md)）|
| 実現方式（Cognito） | Pre Token Lambda + Conditional MFA で `amr` クレーム検査（個別実装）|
| 実現方式（Keycloak） | Conditional OTP（Authentication Flow 標準）|
| 信頼境界 | 外部 IdP の MFA 主張（AuthnContext / `amr`）を信頼。信頼しない外部 IdP は接続しない |
| 例外 | 管理者ロール等の高権限ユーザーには Broker 側でも MFA 強制（条件付き）|

#### TBD / 要確認

| 確認項目 | 回答例 |
|---|---|
| 外部 IdP の MFA を全面的に信頼するか | はい（推奨）/ 部分的（ロール別） |
| 信頼する `amr` 値 / AuthnContext クラス | `mfa` / `urn:oasis:names:tc:SAML:2.0:ac:classes:MultiFactorContract` 等 |
| 高権限ロールへの追加 MFA 強制 | する / しない |

---

### §FR-2.2.4 属性ライフサイクル設計の絡み合い（B-604 / B-605 / B-606 統合解説）

> **このサブ・サブセクションで定めること**: §FR-2.2.2（属性マッピング）/ §FR-2.3.1（複数 IdP）/ §FR-2.3.C（複数テナント所属）の **3 論点は単独で決められない**ことを明示し、絡み合いと連動の罠を整理する。   
> **主な判断軸**: 属性ライフサイクル（命名差異 → 更新 → 複数テナント所属）を一貫して扱えるか   
> **§FR-2.2 内の位置付け**: 3 論点を統合する「**設計の絡み合い章**」。個別の詳細は §FR-2.2.2 / §FR-2.3.1 / §FR-2.3.C を参照

#### 3 論点の関係

| # | 論点 | 主章 | ヒアリング ID |
|:---:|---|---|---|
| **1** | 顧客 IdP ごとの属性名差異 | [§FR-2.2.2](#fr-222-属性マッピング--クレーム変換--fr-fed-009) | B-604, B-604-2 |
| **2** | フェデユーザーの属性更新タイミング | [§FR-2.2.2](#fr-222-属性マッピング--クレーム変換--fr-fed-009) | B-605, B-605-2, B-605-3 |
| **3** | 1 ユーザー複数テナント所属 | [§FR-2.3.1](#fr-231-複数-idp-並行運用--fr-fed-010), [§FR-2.3.C](#fr-23c-マルチテナント環境での-sso-挙動) | B-606, B-606-2〜4, B-611 |

```mermaid
flowchart LR
    A["[1] 属性名差異<br/>各 IdP の命名"]
    B["[2] 属性更新<br/>タイミング"]
    C["[3] 複数テナント<br/>所属"]

    A -->|"何を変換するか"| B
    B -->|"いつ上書きするか"| C
    A -.->|"テナントごとに違う命名"| C

    ABC["3 軸全部:<br/>テナント × 属性 × タイミング<br/>= 設計爆発"]

    A --> ABC
    B --> ABC
    C --> ABC

    style ABC fill:#ffe0e0,stroke:#cc0000
```

→ **3 つは「属性のライフサイクル設計」の 3 軸**。1 つだけ決めても破綻する。

#### 論点 1: 顧客 IdP ごとの属性名差異

各 IdP は同じ概念に対して別の属性名を使う:

| 概念 | Entra ID | Okta | Google Workspace | HENNGE One | SAML 標準 | ADFS |
|---|---|---|---|---|---|---|
| ユーザー一意 ID | `oid` (objectId) | `sub` | `sub` | 独自 | `NameID` | `objectsid` |
| テナント ID | `tid` (tenant GUID) | `org_id` | `hd` | 独自 | （なし）| （なし） |
| メール | `email` / `preferred_username` | `email` | `email` | 独自 | `emailaddress` | `emailaddress` |
| グループ | `groups`（GUID） | `groups`（文字列） | （カスタム）| 独自 | AttributeStatement | `Group` |

**よくある罠**:
- Entra `tid` をそのまま `tenant_id` に → Entra のテナント GUID と本基盤の `tenant_id` 体系が齟齬
- Okta `groups` がデフォルト含まれない → カスタムスコープ要求が必要
- HENNGE / 国産 IdP の独自命名 → ドキュメント英語化なし、実物確認必須

**設計判断**:
- **A 案 顧客 IdP 個別に Broker 側でマッピング**（業界標準、本基盤推奨）
- B 案 顧客側に標準スキーマ準拠を契約条項で要求（大手のみ可）
- C 案 IdP-specific クレームを RP に露出（❌ Broker パターン崩壊）

#### 論点 2: 属性更新タイミング

JIT で作成後、IdP 側で属性が変わったらどうするか:

| Sync Mode | 異動反映 | 退職反映 | 基盤側カスタム温存 |
|:---:|:---:|:---:|:---:|
| **Force**（強制上書き、業界デフォルト）| ✅ 即時 | ✅ 即時 | ❌ 消える |
| **Import**（初回 JIT のみ）| ❌ 遅延 | ❌ **退職後も認可通る（重大）** | ✅ 温存 |
| **ハイブリッド**（属性ごと）| 属性次第 | 属性次第 | ✅ 一部温存 |
| **SCIM 駆動 + JIT 補完** | ✅ SCIM 即時 | ✅ SCIM 即時 | SCIM 経由のみ |

→ **トレードオフ**: 即時反映性（Force） vs 基盤側カスタマイズ温存（Import）。

**よくある罠**:
- 「Force」前提で基盤側にロール手動追加 → 次回ログインで消える
- 「Import」前提で退職者の groups が反映されない → **退職後も認可通る重大インシデント**
- SCIM + JIT 併用時の属性ソース競合（race condition）

**プラットフォーム差**:
- Cognito: デフォルト JIT 時のみ、Pre Token Lambda V2 で都度上書き実装
- Keycloak: **IdP 単位 + Mapper 単位で Sync Mode 指定可**（圧倒的に楽）

#### 論点 3: 1 ユーザー複数テナント所属

1 人が複数顧客企業に所属するケース:

| 実例 | 状況 |
|---|---|
| 業界横断コンサルタント | Acme と Globex 両社の IdP に登録 |
| MSP（マネージドサービスプロバイダ）| MSP 社員が顧客 A/B/C それぞれの IdP に所属 |
| 業務委託・フリーランス | 取引先 3 社にログイン |
| 親会社 + 子会社 | Acme Holdings + Acme Japan + Acme USA |
| M&A 後 / 兼務 | 旧 A 社員 + 新 B 社所属、営業 + 開発兼務 |

**「あり / なし」で設計の根本が変わる**:

| 要素 | あり前提 | なし前提 |
|---|---|---|
| `tenant_id` クレーム形式 | アクティブのみ JWT に注入 or 配列 | スカラー |
| ログイン UX | テナント選択 UI 必要 | HRD で直接 |
| プロファイル表現 | `memberships: [{tenant, groups, dept}, ...]` | フラット |
| 切替時 MFA | 再要求? | 1 回 |
| 監査ログ | テナント別分離 | 単純 |

**業界実例**:

| サービス | 設計 |
|---|---|
| **Slack** | Workspace ごとに切替（独立セッション） |
| **Notion** | Workspace ごとに切替 |
| **GitHub Organizations** | 1 ユーザー = 複数 Org、横断アクセス |
| **Box Enterprise** | 1 ユーザー = 1 Enterprise（基本）|
| **Auth0 Organizations** | 1 ユーザー = 複数 Organization 標準サポート |

→ **業界主流は「複数所属あり前提 + テナント切替 UI」**（Slack / Notion / Auth0 / Entra B2B）。

#### 3 論点の絡み合い：見落とすと破綻するシナリオ

| シナリオ | 起きること |
|---|---|
| **田中さんが Acme と Globex 両方に所属、両 IdP で groups の命名が違う** | テナント A の groups は `[営業]`、テナント B は `["Sales"]` → どちらをロールマッピングに使う?（1 × 3） |
| **田中さんが Acme で異動、Globex には反映なし** | Force で Acme ログイン → Globex ロールが消える?（2 × 3）|
| **Acme は SCIM 同期、Globex は JIT のみ** | 同一ユーザーで属性ソースが違う → どちらを優先?（2 × 3）|
| **Acme 退職、Globex は継続** | プロファイル削除? それともテナント別 deprovision?（3 × [§FR-5](05-logout-session.md)）|

#### 我々のスタンス（基本方針に基づく）

| 基本方針の柱 | 属性ライフサイクル設計での実現 |
|---|---|
| **絶対安全** | 退職反映は SLA 明示（即時推奨）。属性源は IdP / 基盤で明示分離 |
| **どんなアプリでも** | 統一クレーム形式は IdP 差異吸収後、変わらない |
| **効率よく** | Keycloak は Mapper 単位 Sync Mode、Cognito は Pre Token Lambda で対応 |
| **運用負荷・コスト最小** | 顧客 IdP 追加時、属性命名表をテンプレ化 |

#### 推奨ベースライン

| 軸 | ベースライン |
|---|---|
| **属性命名差異** | A 案: Broker 側マッピング（Cognito `attribute_mapping` / Keycloak IdP Mapper）|
| **属性更新** | **属性ごとに Source of Truth を分離**: `groups`/`department` は IdP 側 Force、`roles`（基盤管理ロール）は Import、表示名は Force |
| **退職反映 SLA** | 即時（< 数分）を目標。SCIM 推奨、JIT のみ運用時は明示警告 |
| **複数テナント所属** | **あり前提で設計**: `memberships: [{tenant, groups, dept}, ...]` + アクティブテナントのみ JWT 注入 + テナント切替 UI |
| **複数テナント時の MFA** | テナント切替時は再要求しない（同一セッション、ステップアップ MFA は別軸で）|
| **複数テナント時の属性ソース** | テナント所属コンテキスト単位で管理（テナント A 属性 ≠ テナント B 属性）|

#### TBD / 要確認（[hearing-checklist.md](../../hearing-checklist.md) と連動）

| 確認項目 | ヒアリング ID | 回答例 |
|---|---|---|
| 各顧客 IdP の実属性名サンプル取得手順 | **B-604-2** | メタデータ URL / Discovery URL / ID Token サンプル |
| 属性ごとの真実の源（Source of Truth） | **B-605-2** | groups は IdP、roles は基盤、表示名は IdP 等 |
| 退職反映 SLA | **B-605-3** | 即時 / 数時間 / 翌日 / SCIM 同期依存 |
| 複数テナント所属時の権限モデル | **B-606-2** | 横断（GitHub 型）/ 切替（Slack 型）/ 別ユーザー（独立）|
| テナント切替時の MFA 再要求 | **B-606-3** | 再要求する / しない / ロール別 |
| 複数所属時の属性ソース | **B-606-4** | テナント別管理 / 統合 |

---

### 参考資料（§FR-2.2 全体）

- [JIT Provisioning Best Practices - Security Boulevard](https://securityboulevard.com/2026/03/how-to-implement-just-in-time-jit-user-provisioning-with-sso-and-scim/)
- [OIDC and SAML Integration for Multi-Tenant - SSOJet](https://ssojet.com/enterprise-ready/oidc-and-saml-integration-multi-tenant-architectures)
- [SAML attributes to OIDC claims mapping - REFEDS](https://wiki.refeds.org/display/GROUPS/Mapping+SAML+attributes+to+OIDC+Claims)
- [Microsoft - Federated MFA assertion handling](https://learn.microsoft.com/en-us/entra/identity/authentication/how-to-mfa-expected-inbound-assertions)
- [Cognito attribute mapping 公式](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-specifying-attribute-mapping.html)
- [Cognito Pre Token Lambda 公式](https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-lambda-pre-token-generation.html)
- [Keycloak Protocol Mapper 解説](https://blog.elest.io/mapping-claims-and-assertions-in-keycloak/)

---

## §FR-2.3 マルチテナント運用（→ FR-FED §2.3）

> 本サブセクションは「**N 社の顧客 IdP を並行運用する全体運用設計**」を示すためのもの。§FR-2.1 / §FR-2.2 が "できる" の話なら、§FR-2.3 は "どう運用するか" の話。

### §FR-2.3.0 マルチテナント運用とは何か（前提と背景）

#### 用語整理

| 用語 | 本基盤での意味 |
|---|---|
| **テナント** | 共通認証基盤を利用する顧客企業（例：Acme 社、Globex 社）。それぞれ独自の社員・IdP・データを持つ |
| **マルチテナント運用** | 1 つの認証基盤で**複数のテナントを並行ホスト**する運用形態 |
| **テナント境界** | データ / 権限 / セッション の分離線。基盤が必ず守る不変条件 |

#### なぜここ（§FR-2.3）で決めるか

```mermaid
flowchart LR
    S31["§FR-2.1<br/>IdP 接続種別<br/>(できる)"]
    S32["§FR-2.2<br/>ユーザー処理<br/>(ミクロ視点)"]
    S33["§FR-2.3 ← イマココ<br/>マルチテナント運用<br/>(マクロ視点)"]
    S10["§FR-9<br/>Broker<br/>アーキテクチャ"]

    S31 --> S33
    S32 --> S33
    S33 --> S10

    style S33 fill:#fff3e0,stroke:#e65100
```

§FR-2.1 / §FR-2.2 は「**できる**」の話。§FR-2.3 は「**どう運用するか**」の話。スケール・運用フロー・UX を確定させる。

---

### §FR-2.3.A アーキテクチャ判断：単一 Pool/Realm + 複数 IdP を採用

#### 3 つの選択肢のトレードオフ

| アプローチ | テナント分離 | スケール上限 | 運用負荷 | Broker パターン整合 | 採用 |
|---|:---:|:---:|:---:|:---:|:---:|
| **A. 1 Pool/Realm + 複数 IdP** | 中（`tenant_id` クレームで分離）| 高（実用上 1000+ 顧客）| **低** | ✅ 完全整合 | **✅ 推奨** |
| B. Pool/Realm per テナント | 高（完全分離） | 中（Cognito Quota 1000 / Keycloak 100s で性能劣化） | 高（管理対象 N 倍）| ⚠ issuer が N 個に分散 | 例外時のみ |
| C. AWS Account per テナント | 最高（コスト分離も）| 低（運用工数爆発） | 最高 | ❌ Broker 崩壊 | ❌ |

#### A 案（採用）の根拠

**Broker パターンの本質は「集約点が 1 つ」**:
- 各バックエンドシステムが検証する issuer は 1 つだけ
- テナントごとに Pool/Realm を分けると issuer が分散 → 各システムが N 個の issuer を検証する羽目に
- B 案・C 案は **Broker パターンの恩恵を捨てる**ことになる（[§1](../common/01-architecture.md) と整合しない）

**スケールも十分**:
- Keycloak: 10K IdPs まで性能劣化なしの実証あり
- Cognito: 数百 IdP までは問題なし（千超は外部 Broker 検討）
- 通常の B2B SaaS（顧客 100〜1000 社）なら A 案で完全カバー

**テナント分離は別レイヤーで担保**:
- 認可層（[§FR-6](06-authz.md)）で `tenant_id` クレームベースのスコープ検証
- バックエンドが「JWT.tenant_id != path.tenantId なら 403」を必ず実行
- これで A 案でも完全分離を実現

#### B 案を例外的に採用するケース

| ケース | 理由 |
|---|---|
| 顧客契約で「データを物理的に分離」と明記 | データ所在地・暗号化キー分離が要件 |
| 規制上の理由（金融とそれ以外の混在禁止等）| コンプライアンス |
| 1 顧客が極めて大規模（10 万 MAU 超）| 性能・コスト個別最適化 |

→ いずれもレアケース。**デフォルトは A 案**。

---

### §FR-2.3.A.1 何が分離・共有されているか — 論理分離の実態（顧客が必ず聞く論点）

A 案（単一 Pool/Realm + 複数 IdP）を採用すると、**JIT で作成されるユーザーレコードが同一 Pool/Realm 内に同居**することになる。「**それでセキュリティは大丈夫なのか?**」という顧客からの懸念に答える。

#### 同居の様子（実態）

```mermaid
flowchart LR
    subgraph Acme["Acme 社の世界"]
        AcmeIdP["Acme Entra ID<br/>パスワード/MFA はここ"]
        AcmeAlice["alice@acme.com"]
    end
    subgraph Globex["Globex 社の世界"]
        GlobexIdP["Globex Okta<br/>パスワード/MFA はここ"]
        GlobexBob["bob@globex.com"]
    end
    subgraph Basis["共通認証基盤(単一 Pool/Realm)"]
        Pool["JIT ユーザーレコード<br/>alice / bob 同居<br/>※ 論理分離 (tenant_id)"]
    end

    AcmeAlice -.OIDC.-> Pool
    GlobexBob -.OIDC.-> Pool
    AcmeIdP -.- AcmeAlice
    GlobexIdP -.- GlobexBob

    style Pool fill:#fff8e1
```

#### 何が分離・共有されているか（詳細マトリクス）

| 要素 | 物理場所 | 分離方式 | テナント間で同居? |
|---|---|---|:---:|
| **パスワードハッシュ** | 各顧客 IdP（Entra/Okta）| 顧客 IdP 完全分離 | ❌ **同居しない（本基盤に来ない）**|
| **MFA 設定**（TOTP/Passkey 秘密）| 各顧客 IdP | 顧客 IdP 完全分離 | ❌ 同居しない |
| **認証アクション**（PW 検証 / MFA チャレンジ）| 各顧客 IdP で実行 | 顧客 IdP 完全分離 | ❌ 同居しない |
| **JIT ユーザーレコード** | 本基盤 Pool/Realm | 論理分離（`custom:tenant_id` 属性 / `identities` クレーム）| ⚠ **同居（論理分離）**|
| **メールアドレス / 表示名** | 本基盤側 | 論理分離 | ⚠ 同居 |
| **Group / Role 割り当て** | 本基盤側 | テナント別ロール | ⚠ 同居 |
| **発行する JWT** | 基盤発行 | `tenant_id` クレームで識別 | ✅ リクエストごとに分離 |
| **SSO セッション Cookie** | 本基盤 | Pool 内共有、ただし JWT は別 | ⚠ Cookie 同居、JWT 分離 |
| **業務データ** | 各アプリ DB | 共有 DB+`tenant_id` / DB 分離 / アカウント分離（[B-306](../../hearing-checklist.md)）| 設計次第 |
| **IdP 接続設定** | 本基盤の Identity Provider 設定 | テナント別エントリ | ⚠ 同居（管理上分離）|

#### 同居しているのは「公開可能な属性 + 論理分離タグ」のみ

| 同居しているもの | 機密度 |
|---|---|
| email（公開情報、JWT で配布）| 低 |
| 表示名 / 部署 / ロール | 低-中 |
| ユーザー内部 ID（`sub` / UUID）| 公開 |
| `tenant_id` / IdP リンク情報 | 低（識別タグ）|

→ **認証クレデンシャル（パスワード・秘密鍵）は本基盤に存在しない**。これが業界標準で**論理分離が安全とされる最大の根拠**。

#### 業界根拠（A 案論理分離の正当性）

| 出典 | 主張 |
|---|---|
| **OWASP Multi-Tenant Security Cheat Sheet** | 「テナント境界は **`tenant_id` を全リクエストで強制**することで論理的に実現可。物理分離は規制要件時のみ」 |
| **Microsoft Azure Architecture Center**（"Architectural Considerations for Identity in a Multitenant Solution"）| 「フェデレーション IdP 構成では、**ユーザーレコードの同居は標準。テナント境界は claim ベースで分離**」 |
| **WorkOS B2B SaaS Multi-tenant Guide** | 「Slack / Notion / Linear など主要 B2B SaaS が単一 Pool + 論理分離で運用」 |
| **Auth0 / Microsoft Entra External ID** | 単一 Tenant + Organization 機能で論理分離を標準採用 |
| **Gartner 予測** | 2026 年までに新規デジタル製品の 75% 以上がマルチテナント論理分離をデフォルト採用 |

#### A 案で残る攻撃面と対策

論理分離は**正しく実装されていれば**物理分離と同等のセキュリティを実現可能。OWASP 観点での対策：

| 攻撃ベクター | 対策 |
|---|---|
| **`tenant_id` クレーム改ざん** | 基盤側で**必ず注入**（Pre Token Lambda / Protocol Mapper、ユーザー自己申告 NG）+ JWT 署名検証 |
| **JIT ユーザー作成時の混同**（Acme IdP が間違って Globex の email でユーザー作成）| First Broker Login Flow で既存ユーザーとの突合せ拒否、Identity Provider 単位の namespace 分離 |
| **email 重複**（Acme と Globex で同じ email）| `tenant_id` + `email` 複合キーで識別、`Trust Email` 設定を慎重に |
| **Cross-tenant IDOR** | リソース ID → tenant_id 解決 + JWT.tenant_id 一致確認（アプリ側責務、[§FR-6.1](06-authz.md) / [§FR-6.3](06-authz.md)）|
| **Admin API での全ユーザー漏洩**（ListUsers）| Realm Admin / IAM Role でテナント別管理権限を分離 |
| **キャッシュ汚染** | キャッシュキーに `tenant_id` プレフィックス必須 |

詳細な実装方式は内部技術メモ [`identity-broker-multi-idp.md §10`](../../../common/identity-broker-multi-idp.md) 参照。

#### 顧客への説明（推奨フレーズ）

> 「**認証情報（パスワード・MFA）はお客様の IdP 側にあり、本基盤には決して送られません**。本基盤に保存されるのは、SSO 連携のために最小限必要な情報（メールアドレスとテナント所属タグ）のみで、これらは JWT に組み込んで各アプリに渡す前提の公開情報です。
>
> テナント間のアクセス分離は、JWT に必ず付与される `tenant_id` クレームを各アプリが検証することで実現します。これは Slack や Notion など主要 B2B SaaS で標準採用される設計で、OWASP・Microsoft Azure Architecture Center も推奨しています。
>
> 物理的にユーザーデータを完全分離したい場合（金融・医療など規制要件）は、お客様専用の Pool / Realm を別途用意することも可能です（B 案）。」

#### TBD / 要確認

| 確認項目 | 回答例 |
|---|---|
| 「ユーザーレコードが同居する」設計でセキュリティ要件を満たすか | はい（標準）/ いいえ（物理分離 = B 案）|
| 物理分離が必要な特殊顧客の有無 | あり（業種名）/ なし |
| Cross-tenant 攻撃対策の責務分担 | 基盤側で tenant_id 注入 / アプリ側で検証強制 |

---

### §FR-2.3.A.2 IdP なし顧客のローカルユーザー管理 — パスワードハッシュの同居問題

§FR-2.3.A.1 では「フェデユーザー」（顧客 IdP 経由）の同居問題を扱った。本サブセクションは**「IdP を持たない顧客」のユーザー管理**を扱う。

#### 問題の所在: パスワードハッシュも同居する

```mermaid
flowchart LR
    subgraph IdPAri["IdP あり顧客 (Acme / Globex)"]
        AcmeIdP["Acme Entra ID<br/>※ パスワードここ"]
        AcmeUsers["Acme 社員"]
    end
    subgraph IdPNashi["⚠ IdP なし顧客 (DeltaCo)"]
        DeltaUsers["DeltaCo 社員<br/>※ パスワードどこに?"]
    end
    subgraph Basis["共通認証基盤"]
        Pool_Local["⚠ User Pool<br/>(ローカルユーザー DB<br/>+ パスワードハッシュ)"]
    end

    AcmeUsers -.OIDC.-> Pool_Local
    AcmeIdP -.- AcmeUsers
    DeltaUsers ==>|"パスワード保存"| Pool_Local

    style Pool_Local fill:#fff8e1
```

→ **IdP なし顧客のユーザーをローカル管理すると、パスワードハッシュも本基盤側に保存される**。共通 Pool に集約すると、フェデユーザー以上に**強い「同居」状態**になる。

| 顧客タイプ | パスワード保存先 | 本基盤での同居 |
|---|---|---|
| IdP あり顧客（Acme, Globex）| 顧客 IdP（Entra / Okta）| ユーザーレコードのみ同居 |
| **IdP なし顧客**（DeltaCo）| **本基盤 User Pool**（PBKDF2/Argon2 ハッシュ）| **ユーザーレコード + パスワードハッシュ同居** |

#### 4 つの選択肢

```mermaid
flowchart TB
    Q["IdP なし顧客のユーザー管理"]
    Q --> A["A. 共通 Pool に集約<br/>(ローカル管理)"]
    Q --> B["B. 顧客別 Pool/Realm<br/>(物理分離)"]
    Q --> C["C. 顧客向け Mini IdP<br/>(別 Realm + フェデ)"]
    Q --> D["D. ハイブリッド<br/>(一般 A / 規制 B)"]

    A --> ARes["⚠ ハッシュ同居<br/>運用 ◎<br/>業界標準"]
    B --> BRes["✅ 物理分離<br/>運用 ❌ N 倍<br/>規制対応"]
    C --> CRes["✅ 実質物理分離<br/>運用 △<br/>メイン基盤シンプル"]
    D --> DRes["✅ 柔軟<br/>運用 ○<br/>**推奨**"]

    style A fill:#fff8e1
    style B fill:#e8f5e9
    style C fill:#e3f2fd
    style D fill:#fce4ec
```

#### 各選択肢の詳細

##### A. 共通 Pool に集約（ローカル管理、論理分離）

```mermaid
flowchart LR
    subgraph Pool["単一 User Pool"]
        FedUsers["フェデユーザー<br/>(alice, bob)<br/>パスなし"]
        LocalUsers["ローカルユーザー<br/>(DeltaCo の dave)<br/>**パスワードハッシュあり**"]
    end
    style Pool fill:#fff8e1
```

- **同居**: ユーザーレコード + **パスワードハッシュ**（DeltaCo 分）
- **保存形式**: PBKDF2-SHA512 / Argon2id（業界標準ハッシュ）
- **リスク**: Pool DB 全体漏洩時に全顧客のローカルユーザー分のハッシュ流出。**ただし強いハッシュ + salt で元パスワード復元困難**
- **業界スタンス**: B2B SaaS で論理分離 + 強いハッシュ + 侵害検知で十分とされる（OWASP / WorkOS / Microsoft 標準）

##### B. 顧客別 Pool / Realm（物理分離 = §FR-2.3.A の B 案）

```mermaid
flowchart LR
    subgraph PoolA["Pool A (Acme 専用)"]
        AcmeFed["Acme フェデユーザー"]
    end
    subgraph PoolD["Pool D (DeltaCo 専用)"]
        DeltaLocal["DeltaCo ローカルユーザー<br/>+ パスワードハッシュ"]
    end
    subgraph PoolG["Pool G (Globex 専用)"]
        GlobexFed["Globex フェデユーザー"]
    end
    style PoolD fill:#e8f5e9
```

- パスワードハッシュも**物理分離**（DeltaCo の Pool D のみに存在）
- 運用工数が顧客数 N に比例（100 社抱えると Pool 100 個）
- JWT issuer が分散 → 各アプリで複数 issuer 検証必要
- Broker パターンの本質が崩壊

##### C. 顧客専用 Mini IdP（別 Realm）+ メインからフェデ

```mermaid
flowchart LR
    subgraph DeltaMini["DeltaCo 専用 Mini Realm<br/>(または別 Pool)"]
        DeltaIdP["DeltaCo 用 IdP"]
        DeltaUsers["DeltaCo 社員<br/>+ パスワードハッシュ"]
    end
    subgraph Basis["メイン共通基盤"]
        MainPool["メイン Pool<br/>(フェデのみ同居)"]
    end

    DeltaIdP -.OIDC フェデ.-> MainPool
    DeltaUsers -.- DeltaIdP

    style DeltaMini fill:#e3f2fd
    style Basis fill:#fff3e0
```

- 「**IdP を自前で用意**」する案 = 顧客専用に Mini Realm/Pool を立て、メインからは外部 IdP として接続
- 物理分離の効果は B 案と同等（パスワードハッシュは Mini Realm のみ）
- メイン共通基盤側はシンプル（メインから見れば「フェデのみ」になる）
- 実装複雑度は B 案以上（2 段階の認証フロー）
- 採用例: Auth0 / Okta が「Premium Tenant」として顧客専用テラスを提供するパターン

##### D. ハイブリッド（一般 A + 規制 B / C）— **本基盤の推奨**

```mermaid
flowchart TB
    subgraph MainPool["メイン共通 Pool"]
        FedUsers["フェデユーザー<br/>(Acme, Globex 等)"]
        LocalGen["一般ローカルユーザー<br/>(DeltaCo 等の小規模)<br/>+ ハッシュ"]
    end
    subgraph FinPool["金融顧客専用 Pool"]
        FinLocal["金融顧客 ローカル<br/>+ ハッシュ"]
    end
    subgraph MedPool["医療顧客専用 Pool"]
        MedLocal["医療顧客 ローカル<br/>+ ハッシュ"]
    end

    style MainPool fill:#fff8e1
    style FinPool fill:#e8f5e9
    style MedPool fill:#e8f5e9
```

- **一般顧客（IdP なし含む）**: 共通 Pool で論理分離
- **規制顧客（金融 / 医療 / 政府）**: 専用 Pool で物理分離
- 柔軟で運用工数も最小化
- 業界実例: Auth0 / Microsoft Entra External ID 等が「**Standard Tenant + Premium Tenant**」パターン採用

#### 比較表

| 観点 | A. 共通 Pool | B. 顧客別 Pool | C. Mini IdP フェデ | D. ハイブリッド |
|---|:---:|:---:|:---:|:---:|
| パスワードハッシュの物理分離 | ❌ 同居 | ✅ 完全分離 | ✅ 完全分離 | ⚠ 部分分離 |
| 同居規模 | 全顧客 | 顧客 1 社 | 顧客 1 社 | 一般顧客のみ |
| 運用工数 | ◎ 1 つ | ❌ N 倍 | ❌ N 倍 + 階層 | ○ 数個 |
| JWT issuer | 1 つ | N 個 | N + 1 個 | 数個 |
| Broker パターン整合 | ✅ 完全 | ❌ 崩壊 | ⚠ 階層化 | ⚠ 部分崩壊 |
| 規制対応（金融 / 医療）| ⚠ 要交渉 | ✅ | ✅ | ✅ 特殊顧客のみ |
| **本基盤での採用判断** | ⚠ 一般顧客のみ | × 過剰 | △ 例外的 | ✅ **推奨** |

#### 「Pool を分けたら物理的に別れているのか?」の直接回答

**Yes、Pool/Realm を分けると物理的に別ストレージで分離されます**：

| 観点 | 単一 Pool | 別 Pool 分離 |
|---|---|---|
| データストレージ | 同じテーブル / DB | 別テーブル / 別 DB（Cognito 別 User Pool / Keycloak 別 Realm = 別テーブル群）|
| パスワードハッシュ | 同居 | 別物理保管 |
| 暗号化キー | 共通 | 別 KMS キー設定可 |
| 管理権限 | 共通 IAM Role / Realm Admin | Pool/Realm 別の Admin |
| 障害影響範囲 | 全テナント | 該当テナントのみ |
| GDPR Right to Erasure 等 | tenant_id レコード削除 | Pool 全体削除可、より厳密 |

→ 「**自前 IdP として別 Pool/Realm を立てる**」 = 「**Pool を分ける**」 = **物理分離**として等価。

#### 本基盤の推奨ベースライン

**D 案ハイブリッド**を採用：

| 顧客タイプ | 配置 | パスワード扱い |
|---|---|---|
| **IdP あり顧客**（Acme, Globex 等）| 共通 Pool | 顧客 IdP 側、本基盤に来ない |
| **IdP なし 一般顧客**（標準セキュリティ要件） | **共通 Pool でローカル管理** | PBKDF2/Argon2 ハッシュ + `tenant_id` タグ |
| **規制顧客**（金融 / 医療 / 政府）| **専用 Pool/Realm** | 物理分離 + 別 KMS キー |

#### 共通 Pool でローカル管理する場合の必須セキュリティ要件

A 案を採用する場合、以下を**標準実装**する：

| 要件 | 実装 | 参照 |
|---|---|---|
| **強いハッシュ** | PBKDF2-SHA512 / Argon2id | Cognito 自動 / Keycloak 標準 |
| **侵害クレデンシャル検出** | Cognito Plus（$0.02/MAU）or Keycloak + HIBP | [§FR-1.2 C-205-2](01-auth.md) |
| **強いパスワードポリシー** | NIST SP 800-63B Rev 4 準拠 | [§FR-1.2](01-auth.md) |
| **アカウントロック / ブルートフォース対策** | 連続失敗で一時ロック | [§FR-1.2 / C-205](01-auth.md) |
| **MFA Must**（IdP なしユーザー）| Passkey 推奨 + TOTP | [§FR-3](03-mfa.md) |
| **Pool DB 暗号化** | Cognito 自動 / Keycloak: Aurora storage_encrypted=true + KMS CMK | [§NFR-4](../nfr/04-security.md) |
| **管理 API 制限** | `ListUsers` 等は IAM Role で制限、`tenant_id` フィルター必須 | §10.0.5 OWASP |
| **監査ログ** | 全認証イベント（成功・失敗）を CloudTrail / Event Listener に永続化 | [§FR-8.2](08-admin.md) |

→ これらを実装すれば、**ハッシュ同居でも実用上のセキュリティリスクは小さい**（業界標準）。

#### 顧客への説明（推奨フレーズ）

> 「IdP をお持ちでない顧客のユーザーは、本基盤側で**ローカル管理**します。パスワードは PBKDF2-SHA512（または Argon2）でハッシュ化して保存され、salt 付きで元パスワード復元は困難です。
>
> ハッシュ自体は他の一般顧客のものと**同じデータベースに格納**されますが、これは Slack / Notion / Linear など主要 B2B SaaS の標準的な構成です（OWASP 推奨）。**侵害クレデンシャル検出 / 強いパスワードポリシー / MFA / DB 暗号化**で実用上のリスクは抑えられます。
>
> 金融・医療・政府系など、**規制・契約で物理分離が必須**な場合は、お客様専用の User Pool を別途用意することも可能です（B 案 = 物理分離、コスト・運用工数増）。」

#### TBD / 要確認

| 確認項目 | 回答例 |
|---|---|
| IdP なし顧客のユーザー管理方針 | A 共通 Pool / B 専用 Pool / C 専用 Mini IdP / D ハイブリッド |
| 規制顧客（金融 / 医療等）の有無 | あり（業種・顧客数）/ なし |
| パスワードハッシュ同居を許容するか | はい（一般顧客で OK）/ いいえ（全顧客分離要）|
| 専用 Pool/Realm を用意する顧客の判断基準 | 契約金額 / 規制要件 / セキュリティレベル |

→ 実装方式の詳細（Cognito 別 Pool vs Keycloak 別 Realm の比較、運用工数）は内部技術メモ [`identity-broker-multi-idp.md §10`](../../../common/identity-broker-multi-idp.md) 参照。

---

### §FR-2.3.B 我々のスタンス（基本方針に基づく）

| 基本方針の柱 | マルチテナント運用での実現 |
|---|---|
| **絶対安全** | テナント境界の厳格分離（`tenant_id` クレーム必須、cross-tenant データアクセス遮断） |
| **どんなアプリでも** | 顧客が何 IdP を持っていても並行運用可能。100〜1000 社規模を想定 |
| **効率よく認証**（中核）| **顧客追加で各システム変更不要**。基盤側で IdP 追加 → 統一 JWT 発行が完結（Broker パターンの本質） |
| **運用負荷・コスト最小** | IaC（Terraform）で自動化。手動 Console 設定は最小限 |

---

### §FR-2.3.C マルチテナント環境での SSO 挙動

「**SSO がテナントを跨ぐとどうなるか**」は顧客が必ず気にする論点。本セクションでは Cognito / Keycloak 共通の SSO **挙動シナリオ**を整理する。
（SSO 機能の Cognito vs Keycloak 比較は [§FR-4 SSO](04-sso.md) / [§FR-5 ログアウト・セッション管理](05-logout-session.md) で詳述。本表は **multi-tenant 文脈に絞った挙動の整理**。）

#### シナリオ A：同一テナント内 SSO（最も一般的）

```mermaid
sequenceDiagram
    participant U as Acme 社員 A
    participant X as Acme System X
    participant Y as Acme System Y
    participant B as 共通認証基盤
    participant I as Acme IdP

    U->>X: ① アクセス
    X->>B: ② 認証要求
    B->>I: ③ Acme IdP に委譲
    I->>U: ログイン画面
    U->>I: 認証情報
    I->>B: 認証成功
    B-->>X: ④ JWT(tenant_id=acme) 発行
    Note over U,B: Broker に SSO セッション確立

    U->>Y: ⑤ アクセス
    Y->>B: ⑥ 認証要求
    Note over B: SSO セッション有効
    B-->>Y: ⑦ JWT(tenant_id=acme) 即時発行（ログイン不要）
```

→ **Broker（Cognito Pool / Keycloak Realm）内の SSO セッションが共有**されるため、同一顧客内のシステム間はシームレス。A 案を採用する大きなメリット。

#### シナリオ B：クロステナント所属ユーザー

```mermaid
sequenceDiagram
    participant U as ユーザー A<br/>(Acme + Globex 所属)
    participant A as Acme System
    participant G as Globex System
    participant B as 共通認証基盤
    participant AI as Acme IdP
    participant GI as Globex IdP

    U->>A: Acme システムアクセス
    A->>B: 認証要求
    B->>AI: Acme IdP で認証
    AI->>B: 成功
    B-->>A: JWT(tenant_id=acme)

    U->>G: Globex システムアクセス
    G->>B: 認証要求
    Note over B: Acme の JWT は tenant_id 違いで使えない
    B->>GI: Globex IdP で再認証
    GI->>B: 成功
    B-->>G: JWT(tenant_id=globex)
```

→ **同一人物でもテナントが違えば別 JWT**。これは**仕様**であり、テナント境界を守るために必要な挙動。

#### シナリオ C：テナント切替 UI

複数テナント所属ユーザー向け：
- ログイン後に「どのテナントとして動くか」を選択する UI
- AWS Console の "Switch Role" と同様

**実装責務分担**（業界標準）:

| 責務 | 担当 |
|---|---|
| `memberships` クレーム発行（全所属配列）| **共通基盤**（[B-606-4](../../hearing-checklist.md)）|
| 切替時の新 JWT 発行（active_tenant 差替）| **共通基盤**（Refresh Token + クレーム差替 / Token Exchange） |
| **テナント選択 UI 描画**（ドロップダウン / 画面）| **アプリ側 SPA / BFF**（業界標準、[B-611](../../hearing-checklist.md)）|
| active_tenant のセッション保持 | アプリ側 BFF or SPA |

→ **基盤側で UI を持つのは業界実例なし**（Slack / Notion / GitHub / Atlassian Cloud / Linear すべてアプリ側実装）。本基盤の責務は **`memberships` クレーム + 切替時の JWT 再発行 API**、UI はアプリ層で構築。

→ 要件次第。多くの B2B SaaS では「1 アカウント = 1 テナント」で十分（[B-606](../../hearing-checklist.md) で確認）。

#### SSO 挙動の比較（multi-tenant 文脈）

「multi-tenant 運用に直接関わる SSO 挙動」だけに絞った Cognito vs Keycloak 比較。網羅的な機能比較は [§FR-4 SSO](04-sso.md) / [§FR-5 ログアウト・セッション管理](05-logout-session.md) を参照。

| SSO 挙動 | Cognito | Keycloak (OSS / RHBK) | 備考 |
|---|:---:|:---:|---|
| 同一 Pool/Realm 内 SSO セッション共有（同一テナント内）| ✅ User Pool 内 | ✅ Realm 内 | A 案採用時の標準挙動 |
| クロステナントで別 JWT 発行 | ✅ `tenant_id` クレームで識別 | ✅ `tenant_id` クレームで識別 | 設計で担保 |
| テナント切替 UI | ⚠ 自前 SPA 実装 | ⚠ 自前 SPA 実装 | プラットフォーム標準機能なし、SPA 側で実装 |
| 同一 Broker への複数 IdP 並行 SSO | ✅ Pool に複数 IdP | ✅ Realm に複数 IdP | A 案の前提 |
| Broker ログアウトで全テナントセッション破棄 | ✅ Global Sign-Out | ✅ Realm-level Logout | テナント境界で限定する場合は設計工夫が必要 |

詳細な SSO / ログアウト機能比較（Back-Channel Logout / Front-Channel Logout 等）は [§FR-5 ログアウト・セッション管理](05-logout-session.md) を参照。

---

### §FR-2.3.1 複数 IdP 並行運用（→ FR-FED-010）

> **このサブ・サブセクションで定めること**: 1 つの認証基盤に N 社の外部 IdP を同時登録して並行運用する技術構成（単一 Pool/Realm + 複数 IdP）と、テナント分離の方式。   
> **主な判断軸**: 想定顧客企業数、テナント分離の粒度（クレームベース vs 物理分離）、1 ユーザー複数テナント所属の可能性   
> **§FR-2.3 内の位置付け**: §FR-2.3.A アーキテクチャ判断（採用方針）を**具体実装**として確定。§FR-2.3.2 オンボーディング・§FR-2.3.3 UX と組合せて全体運用が完成

#### ベースライン

- **単一 Cognito User Pool / 単一 Keycloak Realm** に複数の外部 IdP を並行登録（A 案、3.3.A で根拠提示）
- 各ユーザーは `tenant_id` クレームで所属顧客企業を識別
- JWT には `tenant_id` / `roles` / `email` を統一形式で注入（[§FR-2.2.2](#322-属性マッピング--クレーム変換--fr-fed-009) と連動）
- バックエンド API は `tenant_id` でテナントスコープ検証（cross-tenant アクセス遮断）

#### 対応能力

| 項目 | Cognito | Keycloak |
|---|:---:|:---:|
| 単一 Pool/Realm への IdP 接続数 | 数十〜数百（実用上）| **10K** 実証済 |
| テナント分離 | `custom:tenant_id` クレーム | `tenant_id` クレーム |
| PoC 検証 | ✅ Phase 4, 5 | ✅ Phase 9 |

#### TBD / 要確認

| 確認項目 | 回答例 |
|---|---|
| 想定顧客企業数（1 年後 / 3 年後）| N 社 / M 社 |
| テナント分離の粒度 | データ完全分離 / 一部共有 |
| 1 ユーザーが複数テナントに所属する可能性 | あり / なし |
| 物理分離が必要な特殊顧客 | あり（B 案）/ なし |

---

### §FR-2.3.2 顧客追加オンボーディング（→ FR-FED-011）

> **このサブ・サブセクションで定めること**: 新規顧客企業の IdP を本基盤に接続する**運用フロー**（誰が・どんな手順で・どのくらいの時間で）と自動化方針。   
> **主な判断軸**: オンボーディング主体（弊社運用 / 顧客企業セルフサービス）、目標リードタイム、SCIM 連携の必要性、**顧客 IdP 側の作業 / エンドユーザー影響**   
> **§FR-2.3 内の位置付け**: §FR-2.3.1 の並行運用を**「持続的に拡張」**する運用面。IaC 自動化により [§FR-8.1 基盤設定管理](08-admin.md#91-基盤設定管理--fr-admin-71) と整合

#### §FR-2.3.2.A 全体像: 3 レイヤービュー（顧客 IdP 追加は 3 つの並行ワークストリーム）

> **論点**: 「IdP 追加」は単に基盤側で IdP 接続を 1 行足す話ではなく、**顧客 IdP 側の RP 登録 + エンドユーザーへの影響周知** が同時進行する複合プロセス。本基盤運用チームが見落としやすい Layer 1 / Layer 3 を明示する。

```mermaid
flowchart TB
    subgraph L1["Layer 1: 顧客 IdP 管理者の作業（IdP 種別で大きく違う）"]
        L1A["本基盤を SP/RP として IdP に登録<br/>Entity ID / ACS URL / Redirect URI / Cert"]
    end
    subgraph L2["Layer 2: 共通基盤運用チームの作業（後続「オンボーディングフロー」5 ステップ）"]
        L2A["Terraform PR で IdP 接続定義追加<br/>属性マッピング / SCIM 設定"]
    end
    subgraph L3["Layer 3: エンドユーザーの体験"]
        L3A["初回 First Broker Login / MFA 再登録 /<br/>パスワード再設定 / ブックマーク更新 等"]
    end

    L1 -.並行進行.-> L2
    L2 -.並行進行.-> L3

    style L1 fill:#e3f2fd,stroke:#1565c0
    style L2 fill:#e8f5e9,stroke:#2e7d32
    style L3 fill:#fff3e0,stroke:#e65100
```

##### Layer 1: 顧客 IdP 管理者の作業（IdP 別差異マトリクス）

顧客 IdP 管理者が本基盤を **新しい SP/RP として登録する作業**。IdP ごとに UI・工数が大きく異なる:

| IdP | プロトコル | 主要登録項目 | 作業 UI | 想定工数 | エンドユーザー個人側設定 |
|---|---|---|---|:---:|:---:|
| **Entra ID**（Premium P1+）| SAML / OIDC | Reply URL / Identifier (EntityID) / App roles / Token 署名 cert | Entra Admin Center（GUI） | 1〜2h | **不要** |
| **Okta** | SAML / OIDC | ACS URL / Single Logout URL / Attribute statements | Okta Admin Console（GUI） | 1〜2h | **不要** |
| **Google Workspace** | SAML（OIDC は限定的） | ACS URL / Entity ID / Name ID Format | Google Admin Console（GUI） | 30 分〜1h | **不要** |
| **HENNGE One** | SAML | SP-initiated SSO 設定（Entity ID / ACS URL） | HENNGE 管理画面（GUI） | 1〜2h | **不要**（HENNGE 経由は透過） |
| **AD FS**（オンプレ Microsoft） | SAML / WS-Fed | Relying Party Trust + Claim Rules | AD FS Management Console + PowerShell | **半日〜1 日** | **不要**（社内 AD 環境からのみアクセス可、VPN 経由等の制約は別軸） |
| **オンプレ AD（LDAP 直結、Keycloak のみ）** | LDAP/Kerberos | Keycloak 側で User Federation 設定（顧客 AD 側は通常変更不要） | Keycloak Admin Console + LDAP bind 設定 | 半日（接続テスト含む） | **不要** |

→ **共通点**: 顧客 IdP 側に基盤の **Entity ID / ACS URL / Redirect URI** を 1 セット登録するだけで、**エンドユーザー個人の IdP 設定変更は基本不要**（顧客はそのまま既存 IdP を使い続けるため）。

→ **AD FS のみ突出して工数大**。PowerShell 操作 + 証明書管理 + 社内ネット制約。Keycloak の LDAP 直結ならその工数自体が消える（[マスター表 B 列 Z](../../hearing-script/02-idp-federation.md) で確認）。

##### Layer 3: エンドユーザー体験（新規顧客追加 = Greenfield 想定）

新規顧客の従業員が初めて本基盤経由のアプリにアクセスした時の体験:

```mermaid
sequenceDiagram
    autonumber
    actor User as エンドユーザー
    participant App as アプリ
    participant Hub as 本基盤
    participant CustIdP as 顧客 IdP

    User->>App: 初回アクセス
    App->>Hub: 認証要求
    Hub->>CustIdP: SSO リダイレクト（Layer 1 で事前登録済み）
    CustIdP->>User: ログイン画面（顧客 IdP のドメイン）
    User->>CustIdP: 普段使いの社内 ID/PW + MFA
    CustIdP->>Hub: SAML/OIDC アサーション
    Hub-->>Hub: JIT 作成 + First Broker Login（[§FR-2.2.1.A](#fr-221a-同一テナント内ユーザー重複の扱い)）
    Hub->>App: JWT 発行
    App->>User: アプリ画面
```

→ **新規顧客のエンドユーザーに必要なアナウンス**: 「このサービスは社内 ID でログインできます」程度。慎重なアナウンス不要。**移行ケース（既存認証システムからの切替）は §FR-2.3.2.B 参照**。

---

#### §FR-2.3.2.B 既存システムからの移行時のエンドユーザー影響と周知チェックリスト

> **論点**: 新規顧客追加（Greenfield、§FR-2.3.2.A シナリオ S1）と異なり、**既存認証システムから本基盤への移行**（シナリオ S2）はエンドユーザー影響が大きい。事前周知・サポート体制の設計が必要。詳細な移行データ層は [§NFR-9 移行性](../nfr/09-migration.md) で扱い、本節ではエンドユーザー UX 観点で整理。

##### 「ドメインが変わらない」が指す対象は最低 3 つあり、影響範囲が異なる

```mermaid
flowchart LR
    subgraph Before["移行前"]
        B1[アプリ URL<br/>app.acme.com]
        B2[認証 URL<br/>old-auth.acme.com]
        B3[顧客 IdP<br/>login.acme.com<br/>※持ち越し]
    end
    subgraph After["移行後"]
        A1[アプリ URL<br/>app.acme.com<br/>※同じ]
        A2[認証 URL<br/>auth.acme.com<br/>※Custom Domain で持ち越し or 新規]
        A3[顧客 IdP<br/>login.acme.com<br/>※同じ]
    end

    B1 -. ① アプリ URL 変える? .-> A1
    B2 -. ② 認証基盤 URL 変える? .-> A2
    B3 -. ③ 顧客 IdP 変える? .-> A3

    style B1 fill:#e3f2fd
    style B2 fill:#fff3e0
    style B3 fill:#e8f5e9
```

> **重要な前提**: ドメインが変わるか変わらないかに関わらず、**新基盤導入そのもの** が顧客 IdP 側で SP/RP 識別情報の更新を必ず発生させます。これは「URL 文字列」と「SP/RP 識別子（Entity ID / 証明書 / 署名鍵）」が独立した項目だからです。
>
> | 項目 | 新基盤導入で変わるか | 顧客 IdP 側作業 |
> |---|:---:|---|
> | **Reply URL / ACS URL / Redirect URI** | Custom Domain 持ち越し時は変わらない | 流用可、変更不要 |
> | **Entity ID / Audience / Client ID** | **必ず新規発行** | **更新必須**（既存 RP の Entity ID 書き換え or 新規 RP 登録）|
> | **SAML 署名証明書 / OIDC JWKS** | **必ず新規発行** | **証明書差し替え必須**（Cognito は基盤管理で再ローテ不可、Keycloak は BYO 可だが現実的には新規発行）|
> | **属性マッピング** | 要件次第 | 新基盤が要求属性を追加した場合のみ更新 |
> | **エンドユーザー個人の IdP 設定** | 変わらない | **不要**（IdP は同じものを使い続けるため）|
>
> → 「顧客 IdP の設定不要」が成立するのは **エンドユーザー個人レベル** のみ。**顧客 IdP の管理者は新基盤導入の度に必ず作業発生**。ドメイン変更の有無は「その作業範囲」を左右するだけ。

ドメイン変更の影響範囲は次の通り:

| どのドメインが変わるか | 顧客 IdP 側 RP 設定変更の範囲 | エンドユーザー影響 | 慎重アナウンス必要度 |
|---|---|---|:---:|
| **アプリ URL** が変わる | Entity ID / 証明書差し替え（前提）+ Reply URL 更新は通常**不要**（IdP 直接のリダイレクト先はアプリでなく認証基盤のため）| ブックマーク変更、保存パスワード無効、社内 Wiki/メール URL 更新 | 🔥 **高** |
| **認証基盤 URL**（Custom Domain）が変わる | Entity ID / 証明書差し替え（前提）+ **Reply URL / ACS URL の更新も必要** | 通常見えない（リダイレクト先が変わるだけ）、ただし保存ブックマークがあれば無効 | 🟡 中 |
| **顧客 IdP** 自体を切替 | 別問題（[§FR-2.2.1.A シナリオ 2](#fr-221a-同一テナント内ユーザー重複の扱い)）| 通常変わらない（IdP の URL は基盤の外） | 🟡 中 |
| 何も変わらない（既存ドメイン全て持ち越し）| **Entity ID / 証明書差し替えは依然必要**、URL 項目は流用可 | 初回 First Broker Login の確認画面のみ | 🟢 低 |

##### エンドユーザー周知チェックリスト（移行時の 6 つの変化）

「ドメインが変わらなくても、以下が変わるとエンドユーザーへの周知が必要」。1 つでも該当すれば **事前 2〜4 週間の周知 + 当日サポート体制** が業界標準:

| # | 変化項目 | エンドユーザーに何が起きるか | 周知タイミング | 関連章 |
|:---:|---|---|---|---|
| 1 | **パスワードハッシュ持ち越し不可** | 全員パスワード再設定（メール送信 → 再設定リンク） | 切替 2-4 週間前 + 当日 | [§NFR-9.2](../nfr/09-migration.md) |
| 2 | **MFA 登録の持ち越し不可** | 全員 MFA 再登録（TOTP の QR コード再スキャン / Passkey 再登録） | 切替 2-4 週間前 + 当日 + サポート窓口拡充 | [§FR-3](03-mfa.md) |
| 3 | **First Broker Login 確認画面** | 初回 SSO 時に「同一 email の既存アカウントとリンクしますか?」画面が出る | 切替 1 週間前 | [§FR-2.2.1.A](#fr-221a-同一テナント内ユーザー重複の扱い) |
| 4 | **SSO セッション切れ** | 切替直後は再ログイン必須（既存セッションは旧基盤側で持っているため新基盤に引き継がれない） | 切替日時の事前共有 | [§FR-5](05-logout-session.md) |
| 5 | **ログイン画面のブランディング変更** | ログイン画面のロゴ / 色 / ボタン配置が変わる | 切替 1-2 週間前（フィッシング誤認回避） | [§FR-2.3.3](#fr-233-ログイン画面で-idp-選択-ux--home-realm-discovery--fr-fed-013) |
| 6 | **アプリ URL / 認証基盤 URL の変更** | ブックマーク無効、保存パスワード無効、社内 Wiki / メールの URL 更新 | 切替 4 週間前 + リダイレクトプロキシ運用（推奨） | §FR-2.3.2.B（本節）|

##### 周知体制のベースライン

| 周知チャネル | 推奨 | 適用シナリオ |
|---|---|---|
| **顧客 IT 担当者経由メール** | 必須 | 全 6 変化で共通 |
| **社内ポータル / 社内 Wiki 更新** | 推奨 | 変化 1, 2, 6 |
| **アプリ内バナー / モーダル**（切替 1-2 週間前）| 推奨 | 変化 5, 6 |
| **当日サポート窓口拡充**（ヘルプデスク 24h 対応）| 必須 | 変化 1, 2 |
| **SOC への事前共有** | 必須 | 変化 5（フィッシング誤認・誤通報の急増防止）|

---

#### ベースライン

**Terraform / IaC で自動化**を標準とする。

#### オンボーディングフロー（Layer 2 = 共通基盤運用チームの作業）

```mermaid
flowchart LR
    A["① 顧客から IdP 情報受領<br/>SAML Metadata URL<br/>or OIDC Discovery URL"] --> B
    B["② Terraform PR で<br/>IdP 接続定義追加<br/>(5〜30 分)"] --> C
    C["③ CI/CD でデプロイ<br/>(数分)"] --> D
    D["④ テストユーザーで<br/>疎通確認<br/>(10 分)"] --> E
    E["⑤ 顧客へ完了通知"]

    style A fill:#e3f2fd,stroke:#1565c0
    style E fill:#e8f5e9,stroke:#2e7d32
```

**目標リードタイム**：**< 1 営業日**（複雑な顧客でも 2〜3 営業日）

> **注**: 本フローは Layer 2（基盤側作業）のみ。Layer 1（顧客 IdP 側 RP 登録）は §FR-2.3.2.A の IdP 別工数表、Layer 3（エンドユーザー体験 / 移行時の周知）は §FR-2.3.2.B チェックリストを参照。

#### 対応能力

| 機能 | Cognito | Keycloak | 備考 |
|---|:---:|:---:|---|
| Terraform / IaC | ✅ `aws_cognito_identity_provider` | ✅ `keycloak_*_identity_provider` | 両方標準 |
| SAML Metadata 自動取り込み | ✅ URL / XML 指定 | ✅ URL Import | 両方 |
| OIDC Discovery 自動取り込み | ✅ `.well-known` URL | ✅ Discovery URL | 両方 |
| セルフサービスポータル | ❌ 自前 | ⚠ プラグイン（Phase Two 等）| 将来検討 |

#### TBD / 要確認

| 確認項目 | 回答例 |
|---|---|
| オンボーディング主体 | 弊社運用チーム / 顧客企業の管理者（セルフサービス）|
| 目標リードタイム | < 1 営業日 / N 日 |
| IdP 情報の受領形式 | SAML Metadata URL / XML / OIDC Discovery URL / 手動 |
| SCIM プロビジョニング | 必要 / 不要（JIT で OK）|
| **新基盤導入時のドメイン変更計画**（[B-612](../../hearing-checklist.md)）| アプリ URL 維持 / 認証基盤 URL Custom Domain 持ち越し / 全 URL 新規 |
| **エンドユーザー周知のリードタイム期待値**（[B-613](../../hearing-checklist.md)）| 切替 2-4 週間前 / それ以下 / 顧客判断委ね |
| **顧客 IdP 管理者向けオンボーディング手順書テンプレ提供**（[B-614](../../hearing-checklist.md)）| 必須提供 / IdP 別個別作成 / 不要（顧客知見あり）|

---

### §FR-2.3.3 ログイン画面で IdP 選択 UX / Home Realm Discovery（→ FR-FED-013）

> **このサブ・サブセクションで定めること**: ユーザーがログイン画面に来た時、**どの IdP に振り分けるか**の UX 設計（メールドメイン HRD / IdP セレクター / 組織固有 URL）。   
> **主な判断軸**: 推奨 UX パターン、メールドメイン → IdP 解決ルール、複数テナント所属時の選択 UI、ブランディング要件   
> **§FR-2.3 内の位置付け**: §FR-2.3.1 並行運用・§FR-2.3.2 オンボーディングを**エンドユーザー体験**として完成させる UX 層

#### 3 案併記（要件次第で選定、ハイブリッド併用も可）

| 案 | UX | 実装 | 採用例 |
|---|:---:|---|---|
| **A. メールドメインベース HRD**（推奨）| ◎ ユーザーは email だけ入れれば OK | 基盤側にドメイン → IdP マッピングテーブル | Auth0、Entra ID、Notion |
| B. IdP セレクター | ○ ボタン選択 | Keycloak 標準 / Cognito Hosted UI カスタム | Google、多くの SaaS |
| C. 組織固有ログイン URL | ◎ ブランディング両立 | Custom Domain（[§FR-2.1](#31-idp-接続種別-fr-fed-21)）+ ルーティング | Slack、Figma |
| **A + C ハイブリッド**（**複数顧客 × 複数サービス時の業界実用解**）| 基本 A、大口顧客のみ C | Single Realm + Front Proxy で URL → `kc_idp_hint` 自動付与 | Microsoft 365 + Enterprise オプション、Atlassian Cloud |

→ 上記 3 案は**相互排他ではない**。複数顧客 × 複数サービスのシナリオでは **A 基本 + 大口エンタープライズ顧客のみ C 併用** が実用解。Keycloak での具体構成は [§FR-2.3.3.C Keycloak でのハイブリッド構成リファレンス](#fr-233c-keycloak-でのハイブリッド構成リファレンス基本-a--大口顧客のみ-c)、採用方針確認は [B-618](../../hearing-checklist.md) を参照。

#### A 案（メールドメイン HRD）のフロー

```mermaid
sequenceDiagram
    participant U as ユーザー
    participant SPA as SPA / ログイン画面
    participant HRD as HRD 解決ロジック<br/>(基盤側)
    participant B as 共通認証基盤
    participant IdP as 顧客 IdP

    U->>SPA: メールアドレス入力
    SPA->>HRD: alice@acme.com を解決依頼
    HRD->>HRD: ドメイン → IdP マッピング検索
    HRD-->>SPA: Acme IdP に転送
    SPA->>B: 認証要求 (identity_provider=acme)
    B->>IdP: Acme IdP の認証画面
    IdP->>U: 顧客固有のログイン画面
    U->>IdP: 認証情報
    IdP->>B: 認証成功
    B-->>SPA: JWT(tenant_id=acme)
```

#### 対応能力

| パターン | Cognito | Keycloak |
|---|:---:|:---:|
| IdP セレクター（ボタン）| ⚠ Hosted UI カスタム | ✅ **自動表示** |
| メールドメイン HRD | ⚠ 自前実装（Lambda + Custom UI） | ⚠ プラグイン or カスタム |
| 組織固有 URL | ✅ Custom Domain | ✅ Hostname / Realm 別 |
| SPA 変更要否（顧客追加時）| ⚠ IdP ボタン追加要 | ✅ **不要** |

#### §FR-2.3.3.A 画面所在マトリクスとカスタマイズ 3 パターン

> **このサブ・サブセクションで定めること**: 「画面が認証基盤上 vs アプリ側のどちらに存在するか」で **カスタマイズ可能範囲と実装手段が決定的に変わる** ことを明示し、3 つの設計パターンから推奨を選ぶ。   
> **主な判断軸**: 顧客がブランディングを求める範囲（ログイン画面まで含むか、アプリ内のみか）、URL 肥大化制約（[§5.A.1](../../../common/platform-architecture-patterns.md) Cognito Branding Style 20 上限）   
> **§FR-2.3.3 内の位置付け**: UX パターン（HRD / セレクター / 組織固有 URL）の選択とは別軸の「**ブランディング層の責務分担**」を扱う

##### 画面の物理的所在で整理

```mermaid
flowchart LR
    User["👤 田中さん"]

    subgraph App["アプリ側ドメイン<br/>(app.example.com)"]
        Landing["ランディング"]
        Dashboard["ダッシュボード"]
        PostLogout["ログアウト後"]
    end

    subgraph Hub["認証基盤ドメイン<br/>(auth.example.com)"]
        Login["🔐 ログイン画面"]
        IdPSelect["IdP 選択"]
        MFA["MFA 入力"]
        PwReset["パスワードリセット"]
        ErrorPage["エラー画面"]
    end

    User -->|"❶ アクセス"| App
    Landing -->|"❷ 認証要求"| Hub
    Hub -->|"❸ ログイン完了"| App
    App -->|"❹ ログアウト要求"| Hub
    Hub -->|"❺ リダイレクト"| App

    style Hub fill:#fff3e0,stroke:#e65100
    style App fill:#e8f5e9,stroke:#2e7d32
```

| 画面 | 物理的所在 | アプリで `tenant_id` 解釈可能? | 認証基盤側設定 |
|---|---|:---:|:---:|
| ログイン画面（ID/PW 入力） | 認証基盤 | ❌ **不可能** | ✅ **必須** |
| IdP 選択画面（セレクター / HRD） | 認証基盤 | ❌ | ✅ **必須** |
| MFA 入力画面 | 認証基盤 | ❌ | ✅ **必須** |
| パスワードリセット画面 | 認証基盤 | ❌ | ✅ **必須** |
| 同意画面 / Consent | 認証基盤 | ❌ | ✅ **必須** |
| 認証エラー画面（一部） | 認証基盤 | △（リダイレクトで逃せる） | ⚠ 部分的に必要 |
| ログイン前ランディング | アプリ | ✅ **完全可能** | 不要 |
| ログイン後ダッシュボード | アプリ | ✅ **完全可能** | 不要 |
| ログアウト後ランディング | アプリ | ✅ **完全可能** | 不要 |

##### なぜアプリ側で完全カスタマイズできないか

ブラウザの URL バーが `auth.example.com` を指している間は、**ブラウザの Same-Origin Policy により、アプリの JS から認証基盤ドメインの DOM を触れない**（XSS / CSRF 対策の根幹）。回避は不可能。

→ **認証基盤上の画面のカスタマイズは、必ず認証基盤側の Theme / Branding 設定が必要**。

##### フェデユーザー / ローカルユーザーの画面遷移と責務分担

フェデユーザー（P-3）とローカルユーザー（P-2 / P-4 等）では、ログイン操作で経由する画面が異なります。**カスタマイズの責務もそれぞれ違う**ため、整理が必要です。

###### フェデユーザー（P-3）の画面遷移

```mermaid
sequenceDiagram
    participant User as 👤 田中さん<br/>(顧客 Acme 社員)
    participant App as 📱 アプリ
    participant Hub as 🏢 本基盤<br/>(auth.example.com)
    participant IdP as 🏢 Acme の Entra ID<br/>(login.microsoftonline.com)

    User->>App: アクセス
    App->>Hub: GET /authorize?client_id=expense-app

    rect rgb(255, 243, 224)
    Note over Hub: ❶ 本基盤の IdP セレクター画面<br/>(または HRD で自動振り分け)<br/>← A-11 / A-11-α の対象
    Hub->>User: ログイン画面表示
    User->>Hub: IdP 選択 or メール入力
    end

    Hub->>IdP: フェデーション要求 (OIDC/SAML)

    rect rgb(227, 242, 253)
    Note over IdP: ❷ 顧客 IdP のログイン画面<br/>(Entra/Okta 等のドメイン)<br/>← 本基盤管轄外、顧客 IT 部門が管理
    IdP->>User: ID/PW + MFA 入力画面
    User->>IdP: 認証情報入力
    IdP->>IdP: 認証成功 + assertion 生成
    end

    IdP->>Hub: assertion + リダイレクト

    rect rgb(255, 243, 224)
    Note over Hub: ❸ 必要なら補完画面<br/>(同意 / プロファイル補完 / アカウントリンク確認)<br/>← A-11 / A-11-α の対象
    Hub->>User: 補完画面 (必要時のみ)
    User->>Hub: 確認・入力
    end

    Hub->>App: 認証完了 (JWT 発行)
    App->>User: アプリ画面表示
```

###### ローカルユーザー（P-2 / P-4 等）の画面遷移

```mermaid
sequenceDiagram
    participant User as 👤 ユーザー
    participant App as 📱 アプリ
    participant Hub as 🏢 本基盤<br/>(auth.example.com)

    User->>App: アクセス
    App->>Hub: GET /authorize?client_id=expense-app

    rect rgb(255, 243, 224)
    Note over Hub: ❹ 本基盤の ID/PW 入力フォーム<br/>(+ 外部 IdP ボタンと統合された UI)<br/>← A-11 / A-11-α の対象
    Hub->>User: ログイン画面 (ID/PW フォーム + 外部 IdP ボタン)
    User->>Hub: ID/PW 入力 + MFA
    end

    Hub->>App: 認証完了 (JWT 発行)
```

###### 画面別の責務分担マトリクス

| 画面 | 物理的所在 | 誰が管理 | A-11 / A-11-α | 主な利用者カテゴリ |
|---|---|---|:---:|---|
| **❶ 本基盤の IdP セレクター画面** | 本基盤（`auth.example.com`）| 本基盤チーム | ✅ **対象** | P-3 フェデユーザー |
| **❷ 顧客 IdP のログイン画面** | **顧客 IdP**（`login.microsoftonline.com` 等） | **顧客 IT 部門**（Entra Admin Center 等） | ❌ **対象外** | P-3 フェデユーザー |
| **❸ 本基盤の補完画面**（同意 / プロファイル補完 / アカウントリンク確認） | 本基盤 | 本基盤チーム | ✅ 対象 | P-3 + 初回ログイン時 |
| **❹ 本基盤の ID/PW 入力フォーム**（外部 IdP ボタンと統合 UI） | 本基盤 | 本基盤チーム | ✅ 対象 | P-2 / P-4 / P-5 ローカルユーザー |

→ **❶❸❹ は本基盤側ドメインで表示** = A-11 / A-11-α でカスタマイズ可能。**❷ は顧客 IdP のドメイン** = 本基盤からは触れず、顧客 IT 部門の責務（Entra ID の場合 "Company Branding" 機能で設定）。

###### Managed Login / Theme の重要な特性：1 つの統合画面

Cognito Managed Login や Keycloak Theme の **ログイン画面は「フェデ専用」「ローカル専用」と分かれているわけではなく、両方が同じ画面上に統合される**:

```
┌──────────────────────────────────┐
│  本基盤のログイン画面（共通 UI）       │
│                                  │
│  ┌──────────────────────────┐    │
│  │  📧 メールアドレス           │    │  ← ローカル用フィールド
│  │  🔒 パスワード              │    │     (P-4/P-2 が利用)
│  │  [ ログイン ]               │    │
│  └──────────────────────────┘    │
│                                  │
│  ─────  または  ─────          │
│                                  │
│  [ Microsoft Entra でログイン ]   │  ← フェデ用ボタン
│  [ Okta でログイン ]              │     (P-3 が利用)
│  [ HENNGE でログイン ]            │
└──────────────────────────────────┘
```

→ **A-11 / A-11-α のカスタマイズは「統合 UI 全体」に適用される**。フェデ専用 / ローカル専用に分けて別 Branding を当てることは標準機能では不可（App Client 単位で分けるのは可能 = 後述）。

###### App Client 単位での「誰が見るか」の制御

App Client（= アプリ）ごとに **「ローカル ID/PW 入力欄を非表示にして外部 IdP ボタンだけ表示する」** という設定が可能:

| App Client | 設定 | 表示される UI | 採用シーン |
|---|---|---|---|
| 経費精算アプリ（**P-3 のみ受け入れ、フェデ強制**）| 外部 IdP のみ許可 | 外部 IdP ボタンのみ | γ シナリオ（顧客従業員は IdP 強制）|
| 管理画面アプリ（**P-1 / P-2 / P-5 用**）| ローカル Pool のみ許可 | ID/PW フォームのみ | 管理者専用（フェデ不要）|
| 汎用アプリ（**P-3 + P-4 両方**）| 両方許可 | 統合 UI（両方表示） | β シナリオ（IdP あり/なし混在）|

→ **A-5-2 / A-5-3 で利用者カテゴリ・採用シナリオが決まれば、App Client 単位の表示を自動的に最適化可能**。

##### フェデユーザーのログイン操作 UX（HRD / セレクター / 組織固有 URL）

フェデユーザーが「**❶ 本基盤の画面で IdP をどう選ぶか**」には 3 つの UX パターンがあります。これは B-601 で確認している論点ですが、本サブセクションで包括的に整理します。

###### 3 つの UX パターン

| パターン | ❶ の画面 | フロー | 業界実例 |
|---|---|---|---|
| **A. Home Realm Discovery (HRD)** | メール入力フィールドのみ表示 | ユーザーがメール入力 → 本基盤がドメインから IdP 自動判定 → 顧客 IdP にリダイレクト | Microsoft 365 / Slack |
| **B. IdP セレクター** | 各 IdP のボタンを並べる | ユーザーがボタン押下 → 顧客 IdP にリダイレクト | GitHub / GitLab |
| **C. 組織固有 URL** | URL 自体に組織が紐付く（`acme.app.example.com`） | URL アクセスで組織確定 → 顧客 IdP に直接リダイレクト | Slack（チーム別 URL）/ Notion |

###### パターン比較

```mermaid
flowchart TB
    subgraph A[A. HRD]
        A1["📧 メール入力"]
        A2["ドメインから IdP 自動判定"]
        A3["顧客 IdP へリダイレクト"]
        A1 --> A2 --> A3
    end

    subgraph B[B. セレクター]
        B1["IdP ボタン一覧表示"]
        B2["ユーザーが選択"]
        B3["顧客 IdP へリダイレクト"]
        B1 --> B2 --> B3
    end

    subgraph C[C. 組織固有 URL]
        C1["acme.app.example.com<br/>にアクセス"]
        C2["組織 = Acme と確定"]
        C3["顧客 IdP へ直接リダイレクト"]
        C1 --> C2 --> C3
    end

    style A fill:#e8f5e9
    style B fill:#fff3e0
    style C fill:#e3f2fd
```

###### 各パターンの長所・短所

| 観点 | A. HRD | B. セレクター | C. 組織固有 URL |
|---|:---:|:---:|:---:|
| **UX シンプルさ** | ◎ メール入力 1 回 | ○ ボタン選択 | ◎ URL でほぼ確定 |
| **顧客追加リードタイム** | △ ドメイン → IdP マッピング設定要 | ◎ 新 IdP ボタン追加のみ | ⚠ DNS / 証明書設定要 |
| **顧客間の混同リスク** | ❌ 他社の IdP ボタンも見える可能性 | ❌ 他社の IdP ボタンが見える | ✅ URL で組織完全分離 |
| **ブランディング** | △ 本基盤共通 | △ 本基盤共通 | ✅ 組織別カスタムページ可（パターン C / B 連動）|
| **マルチテナント所属時の UX** | ✅ 入力メールで自動判定 | ⚠ ユーザーが手動選択 | ⚠ 別 URL 訪問が必要 |
| **業界主流** | **Microsoft 365 / Slack** | GitHub / GitLab | Slack Workspace / Notion |

→ **業界推奨は A (HRD)**。本基盤の[§FR-2.3.3 ベースライン](#fr-233-ログイン画面で-idp-選択-ux--home-realm-discoveryfr-fed-013) でも HRD を推奨。

###### 採用シナリオ（A-5-3）との関係

| 採用シナリオ | フェデユーザー UX 推奨 | 理由 |
|---|---|---|
| **α 全カテゴリ受け入れ** | A. HRD + 統合 UI | ローカルもフェデも同居、メールで両方判定 |
| **β 管理者 + IdP なし顧客** | A. HRD + 統合 UI | フェデユーザー → HRD で IdP 自動判定、IdP なし顧客 → ローカル ID/PW 入力 |
| **γ 管理者層のみ（推奨）** | **A. HRD（フェデユーザー専用）** | 顧客従業員は全員フェデ、HRD で自動振り分け |
| **δ Break Glass のみ** | A. HRD or B. セレクター | フェデユーザーが大多数、ローカルは緊急用のみ |

→ **A-5-3 でシナリオが決まれば、フェデユーザーの UX パターン推奨が自動的に絞れる**。

###### 顧客 IdP 画面（❷）への影響

「フェデユーザーのログイン画面をカスタマイズしたい」という顧客要望に対する **責務分担の明示が重要**:

| 顧客要望 | 本基盤で対応可能? | 必要な対応 |
|---|:---:|---|
| 本基盤の IdP セレクター画面（❶）に自社ロゴ | ✅ | A-11-α = Yes 部分（パターン B、Cognito 20 顧客上限）|
| 「Acme でログイン」ボタン（❶）のスタイル | ✅ | A-11-α |
| 本基盤の補完画面（❸）の文言・配置 | ⚠ L4-L8 制約 | Cognito Managed Login は文言変更不可、Keycloak Theme なら可能 |
| **顧客 Entra ID のログイン画面（❷）のデザイン** | **❌ 本基盤管轄外** | **顧客 IT 部門に Entra Admin Center > Company Branding での設定を依頼** |
| 「顧客 IdP に飛ばす前にこちらで MFA も要求」 | ✅ | [§FR-3.3 ステップアップ MFA](03-mfa.md) + ACR 制御で実装可 |

→ **顧客が「Entra のログイン画面も変えたい」場合は、本基盤の責務外であることを契約・SOW 段階で明示**する必要があります。

##### 「2 回ログイン」の正体と対策（顧客の誤解への対応）

> **顧客からの典型質問**: 「フェデなのに 2 回ログインさせるのか?」「SSO じゃないのか?」  
> **回答の本質**: 多くのケースで **操作は 2 段階だが認証は 1 回**（業界標準）。ただし MFA 重複や信頼レベル設計次第で **本当に 2 回認証する**ケースもあり、これは設計で回避可能。

###### 「2 回ログイン」と見える 3 種類の現象

| 見え方 | 本当のところ | 評価 |
|---|---|:---:|
| **❶ メール入力 + ❷ IdP ログイン**（HRD パターン）| 実は **❶ は認証ではなく IdP 振り分け識別子の入力**。認証は ❷ の 1 回のみ | ✅ 業界標準・問題なし |
| **本基盤の IdP セレクター + IdP ログイン**（セレクターパターン）| ❶ はクリック 1 つで認証ではない | ✅ 業界標準・問題なし |
| **顧客 IdP で MFA + 本基盤で MFA**（MFA 重複）| **本当に 2 回認証している**。MFA 重複回避ができていない | ❌ **アンチパターン**、修正必要 |

→ **「2 回ログイン」に見える多くのケースは実は 1 回認証**で、業界標準の挙動。ただし「**MFA を 2 回求められる**」は本物の問題で、[§FR-2.2.3 MFA 重複回避](#fr-223-mfa-重複回避--fr-fed-012) で扱う領域。

###### 「ログイン」の定義の整理

OAuth/OIDC 業界で「ログイン」と呼ばれる操作には 2 レベル:

| 用語 | 意味 | 操作 |
|---|---|---|
| **狭義のログイン（認証）** | パスワード / MFA で本人確認 | ID/PW + MFA 入力 |
| **広義のログイン（認証フロー）** | 認証完了までの一連のステップ | IdP 選択 + 認証 + 同意 |

→ **「2 回ログイン」と顧客が言う場合、「狭義のログイン」を 2 回求められているか確認**することが重要。

###### フェデユーザーの「2 段階」の正体（HRD パターン）

```mermaid
sequenceDiagram
    participant User as 👤 田中さん
    participant Hub as 🏢 本基盤
    participant IdP as 🏢 顧客 Entra ID

    rect rgb(255, 250, 230)
    Note over User,Hub: ❶ IdP 振り分け（認証ではない）
    User->>Hub: メール入力<br/>(tanaka@acme.com)
    Hub->>Hub: ドメイン → IdP 自動判定<br/>("acme.com" → Acme Entra)
    end

    rect rgb(255, 230, 230)
    Note over User,IdP: ❷ 本物の認証（ID/PW + MFA）
    Hub->>IdP: フェデ要求
    IdP->>User: ID/PW 入力画面
    User->>IdP: パスワード + MFA
    IdP->>Hub: 認証成功 assertion
    end

    Hub->>User: アプリへリダイレクト
```

→ **操作 2 段階だが、狭義のログインは ❷ で 1 回のみ**。

###### SSO の本当の意味：「2 回目以降のログイン不要」

「Single Sign-On」の本質は **「初回の認証は必要、2 回目以降は再認証不要」** という性質:

```
[初回ログイン（フェデの場合）]
ユーザー → ❶ IdP 振り分け → ❷ 顧客 IdP で認証 → アプリ A 利用可
   ↓ ここで顧客 IdP と本基盤の両方にセッション Cookie 確立

[2 回目以降（同じブラウザ）]
ユーザー → アプリ B にアクセス
        → ❶ も ❷ もスキップ（既存セッションで認証成立）
        → アプリ B 即時利用可  ← これが SSO の効果
```

→ **SSO の効果は「2 回目以降の体験」で測る**。初回の段階数で評価するものではない。

###### 「本当に 2 回認証させる」アンチパターン 4 種

| パターン | 原因 | 対策 | 関連章 |
|---|---|---|---|
| **パターン 1: MFA 重複**（最多）| 顧客 IdP で MFA 済なのに本基盤側でも MFA 要求 | `amr` クレーム信頼設計 | [§FR-2.2.3](#fr-223-mfa-重複回避--fr-fed-012) |
| **パターン 2: 信頼レベル L4 不信任** | 本基盤側で `prompt=login` 強制 | L1〜L3 採用、L4 は規制業種のみ | [§FR-4.2](04-sso.md) |
| **パターン 3: 古い `auth_time` の `max_age` 制約** | 高セキュ操作時に再認証要求 | 重要操作のみで使用、`max_age` 値を慎重に | [§FR-4.2](04-sso.md) |
| **パターン 4: SCIM / JIT 競合の補完画面** | 初回ログイン時のアカウントリンク確認 | 認証ではないが操作が増える | [§FR-2.2.1.A](#fr-221a-同一テナント内ユーザー重複の扱い) |

###### 「2 回ログイン」整理表

| 状況 | ❶ 操作 | ❷ 操作 | 認証回数 | 問題? | 対策 |
|---|---|---|:---:|:---:|---|
| HRD 標準 | メール入力 | ID/PW + MFA | **1 回** | ❌ なし | 業界標準、説明だけ |
| セレクター標準 | IdP ボタンクリック | ID/PW + MFA | **1 回** | ❌ なし | 同上 |
| 組織固有 URL | (URL アクセスのみ) | ID/PW + MFA | **1 回** | ❌ なし | 最短 UX |
| MFA 重複 | ID/PW + MFA | ID/PW + MFA | **2 回** | ✅ 問題 | `amr` 信頼で重複回避 |
| L4 不信任 | ID/PW + MFA | ID/PW + MFA | **2 回** | ⚠ 意図的 | 規制業種で許容 |
| `max_age` 強制 | 過去ログイン | ID/PW + MFA | 2 回（時間差）| ⚠ 意図的 | 高セキュ操作のみで許容 |
| 同一基盤 SSO（2 回目）| (スキップ) | (スキップ) | **0 回** | ✅ SSO 効果 | これが SSO の真価 |

###### 業界実例（フェデ 2 段階は標準）

| サービス | 初回ログイン操作 | 認証回数 |
|---|---|:---:|
| **Microsoft 365** | メール入力 → Entra ID で ID/PW + MFA → サービス | 1 回（メール入力は識別子）|
| **Slack** | Workspace 名入力 → SSO ボタン → IdP → Slack | 1 回 |
| **Notion** | メール入力 → SSO 自動振り分け → IdP → Notion | 1 回 |
| **Salesforce** | My Domain URL → SSO ボタン → IdP → Salesforce | 1 回 |
| **GitHub Enterprise SSO** | IdP ボタン → IdP → GitHub | 1 回 |

→ **業界全体で「フェデの初回は 2 段階操作、認証は 1 回」が標準**。ユーザーも慣れている。

###### 顧客対話用の説明テンプレート

```
顧客「フェデなのに 2 回ログインさせるのか?」

回答テンプレート:
「実は『2 段階操作』に見えますが、認証（パスワード入力）自体は 1 回だけです。

  ❶ 本基盤の画面でメール入力（または IdP ボタン選択）
     → これは『認証』ではなく『どの会社の IdP に振り分けるか』を
       決めるための識別子入力です。パスワードは入れません。

  ❷ 御社の Entra ID で ID/パスワード + MFA 入力
     → これが本物の『認証』です。

これは Microsoft 365 / Slack / Notion / Salesforce 等、業界の標準的な
SaaS で全て採用されている挙動で、ユーザーも慣れている操作です。

なお、SSO の本当の効果は『2 回目以降のログイン操作が不要になる』点に
あります。初回認証後、同じブラウザで別アプリにアクセスすると、
Entra のセッションと本基盤のセッションが既に有効なため、
完全にスキップされて即時利用可能になります。

もし『❶❷ の両方でパスワード入力を求められている』状況であれば、
それは MFA 重複や信頼レベル設定の問題です。本基盤の §FR-2.2.3 / §FR-4.2 で
明示的に MFA 重複回避を実装し、業界標準の体験を保証します。」
```

###### 画面数を 1 つに減らす設計選択肢

「2 段階操作は業界標準だが、それでも 1 画面に減らしたい」というニーズへの対応策。**いずれもトレードオフあり**:

| 選択肢 | 効果 | トレードオフ | 採用例 |
|---|---|---|---|
| **A. 組織固有 URL**（パターン C 採用）| ❶ スキップ → **1 画面**（IdP ログインのみ）| 顧客ごとに URL を周知する必要 | Slack（`acme.slack.com`）/ Figma |
| **B. IdP-Initiated SSO**（顧客 IdP ポータル起点）| ❶ 完全スキップ + ❷ も既存セッションで省略可 → **0〜1 画面** | 顧客が IdP ポータル経由でアプリを開く運用動線が必要 | Office 365 ポータルから SaaS にジャンプ |
| **C. 顧客 IdP の SSO セッション持ち越し**（2 回目以降）| ❷ が無画面自動完了 → 業務時間中の 2 回目以降は **❶ メール入力 → 即アプリ** | 業務開始時の 1 回目は通常通り | Microsoft 365 内の他 SaaS 全般 |
| **D. HRD クッキー保存**（前回入力メアドの記憶）| ❶ をワンクリック自動進行 → 体感 **1 画面** | プライベートブラウジング / 別端末では効かない、プライバシー要件と緊張 | 一部の B2B SaaS |
| **E. IdP 1 社固定**（マルチテナント不要設計）| ❶ 不要 → **1 画面** | マルチテナント要件と相反、γ シナリオ端でのみ可能 | 内製業務システム / 単一顧客向け SaaS |

```mermaid
flowchart LR
    subgraph Std["標準（A=HRD or B=セレクター）"]
        S1["❶ メアド / IdP 選択"] --> S2["❷ IdP ログイン"] --> S3["アプリ"]
    end
    subgraph Org["A. 組織固有 URL（パターン C）"]
        O1["organization.app に直接アクセス<br/>(❶ スキップ)"] --> O2["❷ IdP ログイン"] --> O3["アプリ"]
    end
    subgraph IdPInit["B. IdP-Initiated SSO"]
        I1["顧客 IdP ポータル<br/>(Office 365 等) で<br/>アプリアイコンクリック"] --> I3["アプリ（既存 SSO セッションで認証完了）"]
    end

    style Std fill:#fff3e0
    style Org fill:#e8f5e9
    style IdPInit fill:#e8f5e9
```

→ **推奨**: 業界標準の 2 段階操作（A. HRD）+ SSO セッション持ち越し（C）で「初回 2 段階、2 回目以降 0〜1 段階」が現実的。1 画面強制が要件なら組織固有 URL（パターン C 採用）または IdP-Initiated SSO の運用動線を整備。

###### 既存ヒアリング項目との関係

| ヒアリング項目 | 関係 |
|---|---|
| [B-506 外部 IdP MFA 信頼度](../../hearing-checklist.md) | 「全面信頼」採用なら MFA 重複なし = 1 回のみ |
| [B-507 信頼する `amr` / AuthnContext 値](../../hearing-checklist.md) | どの値を信頼するか決定 |
| [B-801-1 信頼レベル（L1-L4）](../../hearing-checklist.md) | L1 完全信頼 = 業界標準、L4 不信任 = 意図的 2 回認証 |
| [B-802-2 `max_age` 制約](../../hearing-checklist.md) | 古い auth_time 強制再認証 = 意図的 2 回認証 |
| [B-601 IdP 選択 UX](../../hearing-checklist.md) | HRD / セレクター / 組織固有 URL の UX 差 |
| [C-216 ステップアップ MFA](../../hearing-checklist.md) | 重要操作時のみ追加 MFA = 意図的だが UX 配慮 |

→ **「2 回ログイン問題」は既存項目で十分カバー**。問題は「**業界標準の 2 段階操作**」と「**MFA 重複・不信任設計**」を顧客対話で混同しないこと。

##### 認証基盤側でテナント別ブランディングする方法と制約

**Cognito Managed Login Branding（Essentials+）**:

| 機能 | 内容 | 制約 |
|---|---|---|
| Branding Styles | ロゴ / 配色 / フォント | **20 / User Pool（Hard limit）**（[§5.A.1](../../../common/platform-architecture-patterns.md)）|
| App Client 別 Branding | App Client 単位で別 Style 適用可 | App Client 数の制約に縛られる |
| 動的差替（query パラメータ） | ❌ 標準非対応 | カスタム実装で代替 |

→ **顧客 20 社まで個別ブランディング可、それ以上は実質不可能**。

**Keycloak Themes**:

| 機能 | 内容 | 制約 |
|---|---|---|
| Realm Theme | Realm 単位で別 Theme | Realm 分離が必要（[§FR-2.3.A](#fr-23a-アーキテクチャ判断単一-poolrealm--複数-idp-を採用) 単一 Realm + 複数 IdP と矛盾）|
| Client Theme Override | Client 単位で一部上書き | 限定的（Login Theme は Realm 設定が支配的）|
| カスタム Theme（FreeMarker）| 動的にロゴ/色変更可（クエリ / Client 属性ベース）| 実装コスト高、Theme コードのメンテナンス必要 |

##### 2 軸 × Yes/No でパターンが自動判定される構造

ブランディングカスタマイズは **2 つの独立した軸** の組合せで考えると整理しやすい。両者は理論上独立しており、それぞれ Yes/No で答えればパターンが自動的に決まる。

| 軸 | 質問 | 対応するカスタマイズ単位 | ヒアリング ID |
|---|---|---|:---:|
| **軸 1: アプリ別カスタマイズ** | アプリごとに認証基盤側のログイン画面を変えるか?（経費精算 vs 決済管理 等）| 認証基盤側で `client_id` ベースの Branding | [A-11](../../hearing-checklist.md) |
| **軸 2: 顧客別カスタマイズ** | 顧客企業ごとに認証基盤側のログイン画面を変えるか?（Acme vs Globex 等）| 認証基盤側で `tenant_id` ベースの Branding | [A-11-α](../../hearing-checklist.md) |

###### 2 軸の組合せから自動判定されるパターン

| 軸 1（アプリ別）| 軸 2（顧客別）| 結果パターン | 採用シーン |
|:---:|:---:|:---:|---|
| ❌ No | ❌ No | **パターン A** | アプリ画面のみカスタマイズ（最シンプル、Slack/Notion 型）|
| ✅ Yes | ❌ No | **パターン A'** | 経費精算 vs 決済等でアプリ間差別化（Auth0/Entra/Okta 型、業界主流）|
| ❌ No | ✅ Yes 部分 | **パターン B** | 顧客別ブランディング（Cognito 20 上限、規制業種）|
| ✅ Yes | ✅ Yes | A' × B 複合 | アプリ × 顧客の組合せ（Cognito ほぼ不可、Keycloak 必須）|
| - | ✅ Yes 完全分離 | **パターン C** | Pool/Realm 分離、SSO 喪失リスクあり、Enterprise プラン |

→ **顧客は軸 1 と軸 2 の Yes/No を独立に判断するだけでよい**。組合せから本基盤側がパターンを自動マッピング。

###### ヒアリング推奨順序

1. **A-11**（軸 1: アプリ別）を Yes/No で確認
2. **A-11-α**（軸 2: 顧客別）を No / Yes 部分 / Yes 完全分離 のいずれかで確認
3. 上表で自動判定されたパターン（A / A' / B / C）を顧客に提示・合意取得
4. **A-11-2**（アプリ側実装責務）: 軸 1 = No または 軸 2 = No の場合に確認（アプリ側で顧客別差替する責務）
5. **A-11-3**（カスタマイズレベル L1-L8）: 軸 1 = Yes または 軸 2 = Yes の場合に確認（認証基盤側カスタマイズの深度）

→ 2 軸の合意取得により、**[B-612](../../hearing-checklist.md) / [B-703-3](../../hearing-checklist.md) / [B-208](../../hearing-checklist.md) / [B-703-1](../../hearing-checklist.md) の 4 項目が自動的に決まる**。

##### 現実的な 4 つの設計パターン（2 軸の組合せ詳細）

> 詳細な技術根拠・公式ソース引用は [branding-strategy-evidence.md](../../../common/branding-strategy-evidence.md) 参照。

**パターン A: 認証基盤は最小ブランディング、アプリ側で完全カスタマイズ**（**シンプル・業界標準**）

```
[認証基盤側]
- ロゴ: 本基盤の標準ロゴ / 「Powered by 本基盤」表記
- 配色: ニュートラル（ダーク / ライト切替程度）
- 文言: 多言語対応のみ

[アプリ側]
- ランディング / ログイン後 / ログアウト後: tenant_id を JWT or query で解釈、完全カスタマイズ
```

| 観点 | 評価 |
|---|---|
| Cognito で実装可能 | ✅ 1 Theme で完結 |
| Keycloak で実装可能 | ✅ 1 Realm + 標準 Theme |
| URL 肥大化 | なし（共通 URL）|
| 業界実例 | **Slack / Notion / Microsoft 365 標準** |

**パターン A': アプリ単位 Branding（認証基盤側） + テナント別差替（アプリ側）**（**新規・業界主流**）

```
[認証基盤側]
- アプリ単位（client_id ベース）に Branding Style を割当
  - 経費精算アプリ → 専用ロゴ・配色のログイン画面
  - 決済管理アプリ → 別の専用ロゴ・配色のログイン画面
- 認証画面で「どのアプリにログインするか」を視覚的に明示

[アプリ側]
- ランディング / ログイン後 / ログアウト後: tenant_id を JWT or query で解釈、完全カスタマイズ
- パターン A と同じ責務（顧客別差替はアプリ側）
```

**ポイント**: **「ログイン画面はアプリ単位」「アプリ画面は顧客単位」の二重軸**。認証前は JWT がまだないため、認証基盤側は **`client_id` パラメータ**でアプリを識別して Branding 切替。認証後はアプリ側で **JWT `tenant_id` クレーム**で顧客識別。

| 観点 | 評価 |
|---|---|
| Cognito で実装可能 | ✅ App Client 単位 Managed Login Branding（**20 Style 上限**）、Essentials+ ティア必須 |
| Keycloak で実装可能 | ✅ **Client 単位 Login Theme Override**（制限なし）、Theme Selector SPI で高度な動的選択も可 |
| 必要ティア | Cognito: **Essentials または Plus** / Keycloak: 制約なし |
| URL 肥大化 | なし（アプリ単位なので 5-10 / アプリで完結）|
| 対象アプリ規模 | Cognito: 20 アプリまで / Keycloak: 制限なし |
| 業界実例 | **Auth0 Universal Login / Microsoft Entra App Registration / Okta Brands / Cognito Managed Login Branding** |
| 採用シーン | アプリ間で全く異なるブランド体験を提供したい（経費精算 / 決済 / 人事 等）|

###### パターン A' のカスタマイズ範囲の限界（重要）

**「ロゴ・配色の差替」は両プラットフォームで可能**ですが、**配置・要素並び順・文言変更などの DOM 変更**には大きな制約があります。詳細は [branding-strategy-evidence.md §7.A カスタマイズレベル別マトリクス](../../../common/branding-strategy-evidence.md) を参照。

| Lv | 内容 | Cognito Managed Login | Keycloak Theme |
|:---:|---|:---:|:---:|
| L1-L3 | 見た目・スペーシング・基本配置（事前選択肢） | ✅ | ✅ |
| L4 | テキスト・文言変更 | **❌**（多言語のみ） | ✅ |
| L5 | 要素追加・削除 | **❌** | ✅ |
| L6 | 要素並び順変更 | **❌** | ✅ |
| L7-L8 | HTML 構造完全自由 / カスタム JS | **❌** | ✅ |

→ **L4-L8 が必要な場合の選択肢**:
1. **Keycloak 採用**（パターン A' のまま、Theme で完全自由、SSO 維持）
2. **Cognito Custom UI（SDK 経由）に切り替え**（自前ホスティング）
3. **そのアプリ単独でアプリ側カスタム UI に寄せる**（共通基盤の運用負荷回避、ただし SSO 喪失のトレードオフ。詳細は [branding-strategy-evidence.md §7.B](../../../common/branding-strategy-evidence.md)）

###### パターン A' の動作原理：URL 1 つで UI を振り分ける仕組み

「Callback URL もログイン URL も 1 つなのに、どうやってアプリごとに違う画面を出しているのか?」という疑問への解説。

**結論**: OAuth 標準の **`client_id` クエリパラメータで Client を識別**し、Client 設定から Branding / Theme を解決する仕組み。Cognito / Keycloak 共通の動作。

```mermaid
sequenceDiagram
    participant Browser as 👤 ブラウザ
    participant Hub as 🏢 共通認証基盤
    participant Config as Client 設定
    participant Theme as Theme/Branding<br/>リソース

    Note over Browser: アプリ A（経費精算）からの遷移
    Browser->>Hub: GET /auth?client_id=expense-app&...
    Hub->>Config: client_id "expense-app" の設定取得
    Config-->>Hub: Branding Style A / Theme A の参照
    Hub->>Theme: Branding A / Theme A 読込
    Theme-->>Hub: 経費精算用 UI リソース
    Hub-->>Browser: HTML レスポンス<br/>(経費精算ブランド画面)

    Note over Browser: アプリ B（決済管理）からの遷移
    Browser->>Hub: GET /auth?client_id=payment-app&...
    Hub->>Config: client_id "payment-app" の設定取得
    Config-->>Hub: Branding Style B / Theme B の参照
    Hub->>Theme: Branding B / Theme B 読込
    Theme-->>Hub: 決済管理用 UI リソース
    Hub-->>Browser: HTML レスポンス<br/>(決済管理ブランド画面)
```

**ポイント**:

| 観点 | 内容 |
|---|---|
| **URL** | 同じ（`/auth` 等の認証エンドポイント） |
| **Callback URL** | Client 設定の `redirectUris` で管理、複数アプリで共通 1 つでも OK |
| **識別キー** | `client_id` クエリパラメータ（OAuth 2.0 標準仕様） |
| **振り分けロジック** | 共通基盤が `client_id` から Client 設定を引き、紐づく Branding Style（Cognito）/ Theme（Keycloak）でレンダリング |

**Cognito vs Keycloak の本質的差**:

| 観点 | Cognito Managed Login | Keycloak Theme |
|---|---|---|
| **管理単位** | Branding Style（**JSON 設定**） | Theme（**ファイル群**） |
| **HTML 編集** | ❌ 不可（設定の組み合わせのみ） | ✅ 完全自由（`.ftl` テンプレート）|
| **継承機構** | ❌ なし | ✅ `parent` 指定で base / keycloak から継承可、差分のみ書く |
| **管理単位の上限** | 20 Style / Pool（Hard）| 制限なし |
| **デプロイ** | API 経由（`CreateManagedLoginBranding`）| ファイル配置（Git で管理可）|
| **動的選択** | App Client 単位の静的割当 | Theme Selector SPI で動的選択可 |

→ **「変更容易」の本質**: Keycloak は **ファイルベース + 階層継承** で、エンジニアが慣れた Git / PR フローで管理可能。Cognito Branding Editor の独自設定形式と異なり、HTML / CSS を直接編集できる。詳細は [branding-strategy-evidence.md §7.C](../../../common/branding-strategy-evidence.md) を参照。

**パターン B: テナント別ロゴのみ動的注入（認証基盤側で顧客識別）**

| 観点 | 評価 |
|---|---|
| Cognito | △ 20 **顧客**上限（Branding Style 20 を顧客に割当）|
| Keycloak | ✅ カスタム Theme + Theme Selector SPI で動的差替 |
| 採用シーン | ログイン画面にも**顧客**ブランドを出したい中規模顧客（規制業種等）|

**パターン C: 完全テナント別ブランディング**（コスト高、Enterprise プラン）

| 観点 | 評価 |
|---|---|
| Cognito | ❌ 21 社目から不可（Pool 分離が必要）|
| Keycloak | ⚠ Realm 分離が必須（[§C-1.4](../common/01-architecture.md#c-14-物理分離レベルと-broker-パターンの関係) L3 ハイブリッドへ移行）|
| 採用シーン | 大口顧客 / Enterprise プラン専用 |

##### 4 パターン比較表（決定版）

| 軸 | A | A' | B | C |
|---|:---:|:---:|:---:|:---:|
| **認証基盤側カスタマイズ単位** | ❌ 共通 | **✅ アプリ単位**（client_id）| ✅ テナント単位 | ✅ テナント単位（物理分離）|
| **アプリ側カスタマイズ** | ✅ テナント単位 | ✅ テナント単位 | ✅ | ✅ |
| **Cognito 制約** | なし | 20 Branding Style 上限 | 20 顧客上限 | Pool 分離（10,000 Pool 上限）|
| **Keycloak 制約** | なし | なし | Realm 分離 or Theme | Realm 分離（数千上限）|
| **必要ティア（Cognito）** | Lite OK | **Essentials+** | Essentials+ | Lite OK |
| **URL allowlist 数** | 5-10 / アプリ | 5-10 / アプリ | 顧客数 × アプリ数 | 顧客数 × アプリ数 |
| **対象スケール** | 制限なし | **アプリ 20 個まで** | 顧客 20 社まで | 大口顧客のみ |
| **業界実例** | Slack / Notion | **Auth0 / Entra / Okta** | 規制業種 | 金融 |

##### 業界実例（拡張版）

| サービス | 認証基盤側 | アプリ側 | パターン |
|---|---|---|---|
| Slack | 共通（Slack ロゴ） | Workspace 別ブランディング | **A** |
| Notion | 共通 | Workspace 別 | A |
| **Auth0 Universal Login** | **Application 単位 Branding Page** | 自由 | **A'** |
| **Microsoft Entra ID** | **App Registration 単位ロゴ** | 各 SaaS でカスタマイズ | **A'** |
| **Okta** | **Application 単位 + Brands** | 自由 | **A'** |
| **AWS Cognito Managed Login** | **App Client 単位 Branding Style** | アプリ側 | **A'**（公式機能） |
| Microsoft 365 | テナント別ロゴ表示可 | 各 SaaS でカスタマイズ | A + 一部 B |
| AWS Console | 共通（AWS ロゴ） | 一部 IAM Identity Center で組織別 | A |

→ **業界主流は A または A'**。「アプリ単位カスタマイズしたい」要望には A' で十分対応可能。

##### URL 肥大化問題との連動

「**共通 URL + 動的差替**」設計は、[§FR-5.1 ログアウト後リダイレクト](05-logout-session.md) と統合運用すべき:

| 用途 | URL 設計 |
|---|---|
| ログインコールバック | `https://app.example.com/callback`（全顧客共通）|
| ログアウト完了 | `https://app.example.com/post-logout?tenant=acme&reason=...` |
| エラー | `https://app.example.com/error?code=...&tenant=acme` |

→ **5〜10 URL/アプリで完結**。100 顧客でも Cognito 100 URL Hard limit 内に収まる。

##### ベースライン

| 項目 | 推奨 |
|---|---|
| **デフォルト** | **パターン A**（認証基盤は最小、アプリ側で完全カスタマイズ）|
| **アプリ間で異なるブランド体験を提供したい場合** | **パターン A'**（認証基盤側でアプリ単位 Branding + アプリ側でテナント別差替、業界主流）|
| 顧客から「ログイン画面に自社ロゴ」要望 | パターン B（Cognito は 20 顧客まで / Keycloak はカスタム Theme）|
| 大口顧客の「完全専用」要望 | パターン C（[§C-1.4 L3 ハイブリッド](../common/01-architecture.md#c-14-物理分離レベルと-broker-パターンの関係)、Enterprise プラン化）|
| `tenant_id` 改竄対策 | JWT クレームで検証（クエリパラメータは表示用のみ、authorize 判定には JWT を使う）|
| **認証前後の識別子の違い** | **認証前（ログイン画面）= `client_id` パラメータ**（OAuth 標準、A' で利用）/ **認証後（アプリ画面）= JWT クレーム `tenant_id`**（A / A' でアプリ側が利用）|
| **ヒアリング順序** | **[A-11 ブランディング基本方針](../../hearing-checklist.md)（🔥 最優先）で最初に合意取得**。パターン A / A' 合意により B-612 / B-703-3 / B-208 / B-703-1 の 4 項目が自動決定 |

##### 顧客との対話：要望の翻訳表

| 顧客要望の表現 | 真意の確認 | 対応 |
|---|---|---|
| 「テナントごとにブランディング」 | ログイン画面? アプリ内? 両方? | アプリ内のみなら **A** / ログイン画面まで含むなら **B** |
| 「会社のロゴを出したい」 | どの画面で? どの単位で? | ログイン画面で顧客ロゴ = **B** / アプリ内のみ = **A** / **アプリ単位のロゴ = A'** |
| **「経費精算と決済で違うブランド体験にしたい」** | アプリ単位の差別化要望 | **パターン A'**（業界主流、Auth0/Entra/Okta 採用）|
| 「完全に自社専用にしたい」 | 全画面? 目に触れる画面? | 全画面なら **C**（Enterprise プラン）|
| 「迷わないようにしたい」 | UX 問題（B-601）| **A** + HRD で十分 |
| 「アプリごとに異なるログイン画面のロゴ」 | システム識別子（client_id）ベースのカスタマイズ要望 | **パターン A'**（Cognito Branding Style / Keycloak Login Theme Override）|

#### §FR-2.3.3.B フローのカスタマイズ責務（3 領域の整理）

> **このサブ・サブセクションで定めること**: 「ログイン**フロー**を変えたい」要望に対する責務分担。§FR-2.3.3.A が**画面の所在**で整理したのに対し、本節は**フローの構成要素ごとの設定場所**で整理する。   
> **主な判断軸**: 変えたいフロー要素が「基盤の事前」「IdP 内部」「基盤の事後」のどこに属するか   
> **§FR-2.3.3 内の位置付け**: §FR-2.3.3.A 画面責務分担 と並列の「フロー責務分担」軸

##### フローは 3 領域に分かれる

```mermaid
flowchart LR
    subgraph PreIdP["❶ 基盤の事前フロー<br/>(本基盤管轄)"]
        F1A["IdP 選択 / HRD"]
        F1B["Step-up 要否判定<br/>(acr_values 要求)"]
    end
    subgraph IdPInternal["❷ IdP 内部フロー<br/>(顧客 IT 部門管轄)"]
        F2A["MFA ポリシー<br/>(必須 / 端末別)"]
        F2B["Conditional Access<br/>(場所・端末・リスクで分岐)"]
        F2C["AuthnContext の強度設定"]
    end
    subgraph PostIdP["❸ 基盤の事後フロー<br/>(本基盤管轄)"]
        F3A["First Broker Login<br/>(同一 email リンク確認)"]
        F3B["同意 / プロファイル補完"]
        F3C["基盤側 MFA 重複回避"]
    end

    PreIdP --> IdPInternal --> PostIdP

    style PreIdP fill:#fff3e0,stroke:#e65100
    style IdPInternal fill:#e3f2fd,stroke:#1565c0
    style PostIdP fill:#fff3e0,stroke:#e65100
```

##### 変えたいフロー要素 → 設定場所マッピング

| 変えたい項目 | 設定場所 | 具体的手段 | 関連章 |
|---|---|---|---|
| 「どの IdP に振り分けるか」のロジック | **❶ 本基盤** | HRD マッピング / IdP セレクター UI | [§FR-2.3.3](#fr-233-ログイン画面で-idp-選択-ux--home-realm-discoveryfr-fed-013) |
| 「MFA を必須化 / 端末ごとに分岐」 | **❷ 顧客 IdP** | Entra Conditional Access / Okta Sign-on Policy | 顧客 IdP 管理画面 |
| 「特定リスクで MFA を強化（Step-up）」 | **❶ + ❷ 連携** | 基盤側で `acr_values` 要求 → IdP 側で AuthnContext 対応 | [§FR-2.2.3 MFA 重複回避](#fr-223-mfa-重複回避--fr-fed-012) |
| 「初回ログイン時に同一 email 既存ユーザーへリンク確認」 | **❸ 本基盤** | Keycloak First Broker Login Flow / Cognito Pre Sign-up Lambda | [§FR-2.2.1.A](#fr-221a-同一テナント内ユーザー重複の扱い) |
| 「初回ログイン時に追加属性を入力させる」 | **❸ 本基盤** | Keycloak Required Actions / Cognito 自前画面 | [§FR-7.3 セルフサービス](07-user.md) |
| 「同意画面を出す」 | **❸ 本基盤** | Keycloak Consent / Cognito Hosted UI 設定 | [§FR-4.0 SSO 基本](04-sso.md) |
| 「IdP 認証成功後にカスタムロジック実行」 | **❸ 本基盤** | Cognito Post Authentication Lambda / Keycloak Event Listener | [§FR-9.3 Webhook](09-integration.md) |
| 「IdP 側の認証強度を上げる」 | **❷ 顧客 IdP** | 顧客 IdP のセキュリティポリシー（パスワード強度 / リスクベース等）| 顧客 IdP 管理画面 |

##### よくある顧客要望 → 対応場所の翻訳表

「ログインフローをこうしたい」と言われた時、責務領域を即時判別するための対応表:

| 顧客要望 | 真の領域 | 対応場所 | 顧客への説明ポイント |
|---|:---:|---|---|
| 「MFA を SMS で統一」 | ❷ | **顧客 IdP 側で MFA ポリシー設定** | フェデユーザーの MFA は顧客 IdP 管轄。基盤側で強制はできない（[§FR-2.2.3](#fr-223-mfa-重複回避--fr-fed-012)）|
| 「初回ログインで部署を入力」 | ❸ | **本基盤の Required Actions / 自前画面** | 基盤側で追加画面を挿入する設計。顧客 IdP では実現不可 |
| 「特定アプリだけ強い MFA」 | ❶ + ❷ | **基盤で `acr_values` を要求 + 顧客 IdP で AuthnContext 対応** | 基盤と IdP の双方で実装連携が必要 |
| 「ログイン後の同意画面を消す」 | ❸ | **本基盤の Consent 設定** | Keycloak は client-level 設定で off、Cognito は Hosted UI 設定 |
| 「IdP セレクター画面を出したくない」 | ❶ | **本基盤の HRD / 組織固有 URL 採用** | パターン C（[§FR-2.3.3.A 画面数を 1 つに減らす設計選択肢](#fr-233a-画面所在マトリクスとカスタマイズ-3-パターン)）|
| 「顧客 IdP のパスワード強度を強化」 | ❷ | **顧客 IT 部門に依頼** | 本基盤管轄外、SOW で明示 |
| 「初回 SSO で email 確認モーダルを出す」 | ❸ | **本基盤の First Broker Login Flow** | Keycloak は標準フロー、Cognito は Pre Sign-up Lambda で実装（[§FR-2.2.1.A](#fr-221a-同一テナント内ユーザー重複の扱い)）|

→ **要望ヒアリング時は「変えたいのは ❶❷❸ のどこか」を即座に判別**し、❷ なら顧客 IT 部門依頼、❶❸ なら本基盤で対応可、と明確化する。**画面責務分担（§FR-2.3.3.A）と並列で意識**することが重要。

#### §FR-2.3.3.C Keycloak でのハイブリッド構成リファレンス（基本 A + 大口顧客のみ C）

> **このサブ・サブセクションで定めること**: 複数顧客 × 複数サービスのシナリオで「全顧客 A 一律」「全顧客 C 一律」が両方非現実的な場合の **A + C ハイブリッド構成** を Keycloak で実装する標準パターンを提示。 [B-618 採用方針](../../hearing-checklist.md) で「採用」と回答された場合の参照リファレンス。   
> **主な判断軸**: 想定 C 経由顧客数、CloudFront Function 採用可否、DNS / ACM 管理体制   
> **§FR-2.3.3 内の位置付け**: §FR-2.3.3 の 3 案併記（A/B/C）が**相互排他ではない**ことを明示し、業界実用解としてのハイブリッド構成を具体化

##### なぜハイブリッドが必要か

**「全顧客 A 一律」では大口エンタープライズ顧客の「専用感」要求に応えられず、「全顧客 C 一律」では Cognito 4 顧客 Hard Limit / 運用負荷爆発の問題が生じる**。実用解は「基本 A、契約で大口のみ C」のハイブリッド:

| 顧客分類 | UX | 採用理由 |
|---|---|---|
| 一般顧客（中小規模 / 標準契約）| **A. HRD** | 1 URL 統一、運用負荷最小、マルチ所属対応容易 |
| 大口エンタープライズ顧客（契約で個別合意）| **C. 組織固有 URL** | フィッシング耐性 + 顧客別ブランディング + 「専用感」訴求 |

業界実例: Microsoft 365 / Notion / Atlassian Cloud（複数サービス系）は基本 A、Slack / Figma（単一サービス系）は基本 C。**本基盤と同型（複数サービス × 複数顧客）は A 基本 + 大口 C ハイブリッド** が現実的。

##### 推奨構成: Single Realm + Front Proxy で URL を IdP ヒント自動付与

```mermaid
flowchart TB
    subgraph Users["エンドユーザー"]
        UA[一般顧客<br/>従業員]
        UB[大口顧客<br/>従業員]
    end

    subgraph FrontProxy["Front Proxy 層 (AWS)"]
        CF[CloudFront / ALB]
        EF["CloudFront Function<br/>or Lambda@Edge<br/>URL → kc_idp_hint 変換"]
    end

    subgraph KC["Keycloak Single Realm"]
        Auth[Hostname Provider<br/>multi-hostname 許可]
        Flow["First Browser Flow<br/>Identity Provider Redirector<br/>+ HRD authenticator"]
        IdPList["Identity Providers<br/>(全顧客 IdP を 1 Realm に集約)"]
        DB[(User DB<br/>tenant_id で分離)]
    end

    subgraph Customers["顧客 IdP"]
        I1[Acme Entra ID]
        I2[Globex Okta]
        I3[HENNGE One]
    end

    UA -->|auth.example.com<br/>(共通 URL)| CF
    UB -->|acme.auth.example.com<br/>(大口専用 URL)| CF

    CF --> EF
    EF -->|kc_idp_hint=acme-entra<br/>を付与| Auth
    Auth --> Flow
    Flow --> IdPList
    Flow -.HRD ルート<br/>メアド入力.-> IdPList
    Flow -.組織 URL ルート<br/>kc_idp_hint 即時.-> IdPList
    IdPList --> I1
    IdPList --> I2
    IdPList --> I3
    Flow --> DB

    style FrontProxy fill:#fff3e0,stroke:#e65100
    style KC fill:#e8f5e9,stroke:#2e7d32
    style Customers fill:#e3f2fd,stroke:#1565c0
```

→ **同じ Single Realm を維持しつつ、エントリ URL の違いで A（HRD）/ C（組織固有 URL）の体験差を作る**。Realm を分けないので、ユーザー管理・SCIM・属性正規化・SSO セッションは統一。

##### 3 つの構成要素

###### ① Front Proxy 層（CloudFront Function 推奨）

複数の DNS 名（`auth.example.com` + 顧客別 `acme.auth.example.com` 等）をすべて Keycloak に向ける + **URL に応じて `kc_idp_hint` クエリパラメータを自動付与**:

| URL | Front Proxy の挙動 | 効果 |
|---|---|---|
| `auth.example.com/...` | パラメータ追加なし、そのまま通す | HRD 経路（A 案） |
| `acme.auth.example.com/...` | **`&kc_idp_hint=acme-entra` を追加** | Acme の IdP に即リダイレクト（C 案）|
| `globex.auth.example.com/...` | **`&kc_idp_hint=globex-okta` を追加** | Globex の IdP に即リダイレクト |

実装オプション比較:

| 方式 | 特徴 | 採用判断 |
|---|---|---|
| **CloudFront Function**（推奨）| Viewer Request で URL → ヒント変換、ms 単位、$0.10/1M req | 主流・シンプル |
| **Lambda@Edge** | 複雑ロジック可、ms-秒オーダー、$0.60/1M req | ヒント変換が複雑な場合 |
| **ALB Listener Rule** | host-header ベース、別 target group へ転送 | ALB のみ採用時 |

###### ② Keycloak Single Realm + Hostname 設定

Keycloak の Hostname Provider を**複数ホスト名許可モード**に設定:

```bash
KC_HOSTNAME_STRICT=false
KC_HOSTNAME_STRICT_BACKCHANNEL=false
KC_HOSTNAME_STRICT_HTTPS=true  # 必須（Open Redirect 対策）
```

→ `auth.example.com` / `acme.auth.example.com` / `globex.auth.example.com` のいずれからリクエストが来ても同じ Realm が応答。

###### ③ Identity Provider Redirector（標準 Authenticator）

First Browser Flow の `Identity Provider Redirector` 認証器が **`kc_idp_hint` パラメータを検知**して該当 IdP に即リダイレクト。**標準機能のため追加実装不要**:

```mermaid
flowchart LR
    Req["リクエスト到着"]
    Has["kc_idp_hint<br/>あり?"]
    DirectRedirect["指定 IdP に即リダイレクト<br/>(C 案フロー)"]
    HRD["HRD authenticator<br/>(メアド入力画面)"]
    Resolve["ドメインから IdP 自動判定"]
    IdPRedirect["判定 IdP にリダイレクト<br/>(A 案フロー)"]

    Req --> Has
    Has -->|Yes| DirectRedirect
    Has -->|No| HRD
    HRD --> Resolve
    Resolve --> IdPRedirect

    style DirectRedirect fill:#fff3e0
    style IdPRedirect fill:#e8f5e9
```

**HRD authenticator はメアド入力 HRD を行うため軽い拡張が必要**:
- 選択肢 1: コミュニティ拡張 [keycloak-home-idp-discovery](https://github.com/sventorben/keycloak-home-idp-discovery) を導入（広く採用、設定のみで動作）
- 選択肢 2: 自前 Custom Authenticator SPI で実装（Java、20-50 行）
- 選択肢 3: アプリ側でメアド入力 → `kc_idp_hint` を付けて Keycloak を呼ぶ（SPA 側設計、最もシンプル）

##### 顧客追加時の運用フロー

###### A 経由（一般顧客、HRD）の追加

```mermaid
flowchart LR
    A["① 顧客 IdP メタデータ受領"]
    B["② Terraform PR で<br/>Identity Provider 追加"]
    C["③ HRD マッピング追加<br/>(email_domain → provider_alias)"]
    D["④ CI/CD でデプロイ"]
    E["⑤ テスト + 顧客通知"]
    A --> B --> C --> D --> E
    style A fill:#e3f2fd
    style E fill:#e8f5e9
```

**作業量**: < 1 営業日（[§FR-2.3.2 標準フロー](#fr-232-顧客追加オンボーディング--fr-fed-011)）

###### C 経由（大口顧客、組織固有 URL）の追加

```mermaid
flowchart LR
    A["① IdP メタデータ +<br/>専用 URL 仕様合意"]
    B["② Terraform PR で<br/>3 つを同時追加"]
    B1["② -1 Identity Provider"]
    B2["② -2 ACM 証明書<br/>(Route 53 DNS 検証)"]
    B3["② -3 CloudFront Function 更新<br/>(hostname → kc_idp_hint)"]
    C["③ DNS レコード追加"]
    D["④ CI/CD + DNS 伝播待ち"]
    E["⑤ テスト + 顧客通知"]
    A --> B
    B --> B1
    B --> B2
    B --> B3
    B1 --> C
    B2 --> C
    B3 --> C
    C --> D --> E
    style A fill:#e3f2fd
    style E fill:#e8f5e9
```

**作業量**: 2-3 営業日（DNS 伝播 + ACM 検証で時間がかかる）→ **契約フェーズで「専用 URL 提供あり」をオプション化、リードタイムも長めに設定**。

##### B-607 物理分離との関係

**C 経由 ≠ 物理分離**。3 つの組合せパターン:

| 要件 | 採用パターン | ユーザー DB |
|---|---|:---:|
| 大口顧客が「専用 URL」要望のみ | **C ハイブリッド（本節）**| 共有（Single Realm 内、`tenant_id` 論理分離） |
| 大口顧客が「データ物理分離」要望 | **[B-607 = あり](../../hearing-checklist.md)（Multi-Realm）** | 専用（Realm 別） |
| 両方要望（規制金融等）| **C + B-607 両方採用** | 専用 + 専用 URL |

→ 通常は **C ハイブリッドだけで「専用感」演出は十分**。物理分離は規制・契約条項で明示された場合のみ追加。

##### 設計上のポイント・落とし穴

| ポイント | 詳細 |
|---|---|
| **`kc_idp_hint` のセキュリティ** | クライアントが任意の IdP を指定できないよう、Realm 設定で「許可 IdP」を絞る、または **Front Proxy 側で URL から導出した値で上書き** |
| **HRD マッピングの管理** | email_domain → provider_alias の対応表は **Realm Attribute or 外部 DynamoDB** で管理。Terraform で IaC 化推奨 |
| **マルチ所属ユーザー** ([B-606](../../hearing-checklist.md)) | C 経由でも Single Realm なら一人のユーザーレコードに複数 IdP リンク可。物理分離（Multi-Realm）採用時は注意 |
| **Custom Domain × CloudFront** | CloudFront は 1 ディストリビューションで複数 CNAME 可、ACM 証明書は SAN で複数 hostname 統合可（実用上の制約なし）|
| **Hostname strict モード OFF のリスク** | Open Redirect 等を防ぐため、`KC_HOSTNAME_STRICT_HTTPS=true` + 許可リスト管理を必須 |
| **DNS 伝播 SLA** | 大口 C 経由顧客の追加リードタイム（2-3 日）を契約に明示 |
| **ログ・監査** | 全顧客が同じ Realm のため、CloudTrail / Audit Log で `client_id` + `tenant_id` の組み合わせで分析する設計 |

##### 既存設計との整合性

| 既存設計 | 本ハイブリッドとの整合 |
|---|---|
| [§FR-2.3.A 単一 Pool/Realm + 複数 IdP](#fr-23a-アーキテクチャ判断単一-poolrealm--複数-idp-を採用) | ✅ **完全整合**（Single Realm 維持）|
| [§FR-2.3.A.1 論理分離（tenant_id）](#fr-23a1-何が分離共有されているか--論理分離の実態顧客が必ず聞く論点) | ✅ 維持（`tenant_id` クレームで分離）|
| [§FR-2.3.A.2 IdP なし顧客のローカル管理](#fr-23a2-idp-なし顧客のローカルユーザー管理--パスワードハッシュの同居問題) | ✅ 維持（同じ Realm 内でローカルユーザー併存）|
| [ADR-011 認証フロントネットワーク設計](../../../adr/011-auth-frontend-network-design.md) | 拡張: CloudFront / ALB の前段に Function 層追加 |
| [ADR-013 CloudFront WAF IP 制限](../../../adr/013-cloudfront-waf-ip-restriction.md) | ✅ そのまま適用可 |
| [§FR-7 ユーザー管理](07-user.md) | ✅ Single Realm 前提を維持 |

##### 推奨初期ロールアウト

| フェーズ | 内容 | 時期 |
|---|---|---|
| **Phase 1** | A（HRD）のみで全顧客対応 + Single Realm + 共通 1 Custom Domain | リリース時 |
| **Phase 2** | CloudFront Function を導入し、最初の大口顧客に C を適用 | 大口受注後 |
| **Phase 3** | C 採用顧客が 2-3 社に増えた段階で運用パターンを確立、テンプレート化 | 半年〜1 年後 |
| **Phase 4**（例外）| 物理分離（Multi-Realm = [B-607](../../hearing-checklist.md)）要求顧客が現れた場合のみ別 Realm を追加 | 必要時 |

→ **「A 全顧客対応 → C は契約後に追加」** が初期構築リスクを最小化する順序。最初から C 用インフラを構築する必要なし。

##### Cognito 採用時の制約（参考）

本リファレンスは Keycloak 想定。**Cognito 採用時**は以下の制約で実装難度が大幅に上がる:

| 制約 | 影響 |
|---|---|
| **Custom Domain 4 / Region（Hard Limit）**[^cognito-q12-fr233c] | 大口 C 顧客は最大 3 社まで（共通 1 + 大口 3）|
| **`kc_idp_hint` 相当の `identity_provider` パラメータ** | Cognito も対応するが、Pre Sign-up Lambda 等の前処理が複雑化 |
| **HRD authenticator 相当機能なし** | Lambda + Custom UI で自前実装、200-500 行のコード |
| **First Broker Login Flow なし** | Pre Sign-up Lambda で同等処理を自前実装（[§FR-2.2.1.A](#fr-221a-同一テナント内ユーザー重複の扱い)）|

→ **C ハイブリッド要件が想定される場合、Cognito 採用は実装工数とハードリミットで実質ノックアウト**。これは [§C-2.2 プラットフォーム選定](../common/02-platform.md) の判断要素として反映済み。

[^cognito-q12-fr233c]: [cognito-knockout-conditions.md Q-12](../../../reference/cognito-knockout-conditions.md)

#### §FR-2.3.3.D Keycloak HRD 実装方式選定（Universal Login + 4 オプション + 単一テナント複数 IdP 対応）

> **このサブ・サブセクションで定めること**: HRD（A 案）を採用する場合の **実装層の選定**。具体的には (1) アーキテクチャモデル（Universal Login vs アプリ主導）、(2) Keycloak での HRD 実装 4 オプションの選定、(3) 単一テナントが複数 IdP を持つ場合の対応パターン を要件として確定する。
> **主な判断軸**: RHBK 採用予定の有無、Elastic License v2 受容可否、v26 Organizations の採用方針、想定される単一テナント複数 IdP シナリオ
> **§FR-2.3.3 内の位置付け**: §FR-2.3.3 で「A 案 HRD 推奨」が決まった後の **実装層の設計判断**。§FR-2.3.3.C ハイブリッド構成の HRD 部分の実装方法。
> **詳細実装リファレンス**: [common/hrd-implementation-keycloak.md](../../../common/hrd-implementation-keycloak.md)（realm.json サンプル + Browser Flow 設定 + Stage B 検証推奨項目）

##### ベースライン: Universal Login（アプリ主導 HRD は採らない）

| 観点 | アプリ主導 HRD | **Universal Login（ベースライン）** | Identity-First Login（**UX 最適化として推奨**）|
|---|---|---|---|
| メアド入力フィールドの場所 | 各アプリの画面 | 認証基盤の `/auth` ページ | アプリ側 + 認証基盤両方 |
| マッピング知識の所在 | アプリに分散 | **認証基盤に集約** | 認証基盤に集約 |
| 顧客追加時の変更箇所 | 各アプリ | **認証基盤 1 箇所** | 認証基盤 1 箇所 |

→ **Identity Broker パターン採用以上、Universal Login が論理的帰結**。アプリ主導 HRD は「顧客追加で各システム変更不要」要件（§FR-2.3）と矛盾するため非採用。

**アプリ UX 最適化を求める場合**: Identity-First Login を選択。アプリのランディング画面にメアド入力フィールドだけ置き、OIDC `login_hint` パラメータで認証基盤にメアドを渡す。マッピング知識は基盤集約のまま、UX 体験はアプリ側で完結。

##### Keycloak での HRD 実装 4 オプション

| # | オプション | 工数 | ライセンス | RHBK サポート | 単一テナント複数 IdP | 本基盤推奨度 |
|---|---|---|---|:---:|:---:|:---:|
| ① | **Keycloak v26 Organizations（ネイティブ）** | ◎ 設定のみ | ✅ 公式 | ✅ 対象 | ✅ ネイティブ | ★★★★★ |
| ② | コミュニティプラグイン `keycloak-home-idp-discovery` | ◎ JAR 配置 | ⚠ Elastic License v2 | ❌ 対象外 | ⚠ 別途設定 | ★★★★ |
| ③ | 自前 Authenticator SPI（Java 実装）| ❌ 1-2 週間 | ✅ 自社所有 | ❌ 対象外 | ⚠ 実装次第 | ★★ |
| ④ | アプリ主導 + `kc_idp_hint` URL パラメータ | ◎ ゼロ | ✅ 標準 | ✅ 対象 | ❌ アプリで処理 | ★（ハイブリッド C 経路の裏で使用のみ）|

**ベースライン**: **① Keycloak v26 Organizations**。RHBK 採用予定の有無に関わらず第一推奨。理由:
- v25 Preview / v26 GA で Red Hat 公式ロードマップに乗る本命機能
- プラグイン不要、ライセンス問題なし、Red Hat サポート対象（RHBK 採用時）
- **単一テナント複数 IdP のケースでデフォルトで 2 段階セレクターに分岐するネイティブ動作**

**例外的に ② プラグインを採る場合**: Elastic License v2 が受容可能で、v25 以前への互換性が必要なケース。  
**例外的に ③ 自前 SPI を採る場合**: ヘルスケア・政府機関等で OSS plugin の採用が政策上不可なケース。

##### 単一テナントが複数 IdP を持つ場合（4 パターン）

| パターン | シナリオ | Keycloak Organizations での対応 |
|---|---|---|
| **A. ドメインサブ分割** | `@hq.acme.com` → Entra ID / `@sub.acme.com` → Okta | Organization の `domains` ↔ `identityProviders` マッピングで自動振り分け |
| **B. テナント確定後セレクター**（**本命**）| `@acme.com` の中に Entra ID 派 + Okta 派が混在（移行期 / 子会社統合等）| Organizations が複数 IdP を持つ Org で **デフォルトで 2 段階フロー（メアド → そのテナントの IdP セレクター）に自動分岐** |
| C. 既存ユーザーの前回 IdP 直行 | リピーターはセレクター省略 | Browser Flow に `Detect Existing Broker User` + 強制切替パラメータを組合せ |
| D. アプリ主導の明示指定 | 特権ユース（普段 Entra、特権操作で Okta）| アプリのリンク URL に `?kc_idp_hint=...` を埋め込み |

**ベースライン**: **A + B を主、C + D を補助** とする運用。Organizations 採用なら A も B も自動で動作する。

##### 既存設計との整合性

| 既存設計 | 本選定との整合 |
|---|---|
| [§FR-2.3.3 A 案 HRD 推奨](#fr-233-ログイン画面で-idp-選択-ux--home-realm-discoveryfr-fed-013)（メールドメインベース）| ✅ 本選定は A 案実装の選択肢を定義 |
| [§FR-2.3.3.C A+C ハイブリッド](#fr-233c-keycloak-でのハイブリッド構成リファレンス基本-a--大口顧客のみ-c) | ✅ A 経路の実装方式として Organizations を採用、C 経路は CloudFront Function で `kc_idp_hint` 付与 |
| [§FR-2.3.A 単一 Pool/Realm + 複数 IdP](#fr-23a-アーキテクチャ判断単一-poolrealm--複数-idp-を採用) | ✅ Single Realm 維持、Organizations は Realm 内のサブ単位として共存 |
| [§FR-2.3.A.1 論理分離（`tenant_id`）](#fr-23a1-何が分離共有されているか--論理分離の実態顧客が必ず聞く論点) | ✅ Organization 属性 → user attribute の Mapper で `tenant_id` クレームを自動注入可能 |
| [§FR-2.2.1.A 同一テナント内ユーザー重複](#fr-221a-同一テナント内ユーザー重複の扱い) | ✅ First Broker Login Flow と整合、パターン C（前回 IdP 記憶）と連動可 |
| [B-618 A+C ハイブリッド採用方針](../../hearing-checklist.md) | 本選定（実装方式）はその裏付け |

##### 推奨初期ロールアウト（[§FR-2.3.3.C](#fr-233c-keycloak-でのハイブリッド構成リファレンス基本-a--大口顧客のみ-c) と連動）

| フェーズ | 内容 | 時期 |
|---|---|---|
| **Phase 1** | Keycloak v26 + Organizations feature flag 有効化 + 1 Organization で fresh import 検証 | Stage B 期間 |
| **Phase 2** | 実顧客の Organization 追加（ドメインサブ分割 = パターン A） | リリース時 |
| **Phase 3** | 単一ドメイン内に複数 IdP のテナント（移行期顧客等）が発生 = パターン B | 顧客発生時 |
| **Phase 4** | 大口顧客向け組織固有 URL（[§FR-2.3.3.C](#fr-233c-keycloak-でのハイブリッド構成リファレンス基本-a--大口顧客のみ-c)）= A+C ハイブリッド完成 | 大口受注後 |

→ 詳細な Stage B 検証推奨項目（HRD-B1〜B7）は [hrd-implementation-keycloak.md §6](../../../common/hrd-implementation-keycloak.md) 参照。

#### TBD / 要確認

| 確認項目 | 回答例 |
|---|---|
| 推奨 UX パターン | メールドメイン HRD / IdP セレクター / 組織固有 URL |
| メールドメインから IdP への解決ルール | 1 ドメイン = 1 IdP / 1 顧客に複数ドメイン |
| 複数テナント所属時の選択 UI | ログイン後にテナント選択 / 別途 |
| ログイン画面のブランディング | 共通 UI / 顧客企業ごとカスタマイズ |
| **カスタマイズの所在**（§FR-2.3.3.A）| **認証基盤側のみ（A 推奨）/ 一部認証基盤（B）/ 全面（C）** |
| **A + C ハイブリッド構成採用方針**（[B-618](../../hearing-checklist.md) / §FR-2.3.3.C）| 採用（大口顧客のみ C） / 採用しない（全顧客 A 一律） / 検討中 |
| **HRD 実装方式**（§FR-2.3.3.D）| ① v26 Organizations（推奨） / ② sventorben プラグイン / ③ 自前 SPI / ④ kc_idp_hint（基盤 HRD 無し）|
| **単一テナント複数 IdP の想定**（§FR-2.3.3.D）| 想定あり（ドメイン分割可） / 想定あり（同一ドメイン内多 IdP）/ 想定なし |

---

### 参考資料（§FR-2.3 全体）

- [Keycloak Multi-Tenancy Options - Phase Two](https://phasetwo.io/blog/multi-tenancy-options-keycloak/)
- [Keycloak Scalability of IdPs - GitHub Issue](https://github.com/keycloak/keycloak/issues/30084)
- [Microsoft - Home Realm Discovery Policy](https://learn.microsoft.com/en-us/entra/identity/enterprise-apps/home-realm-discovery-policy)
- [Auth0 B2B Authentication](https://auth0.com/docs/get-started/architecture-scenarios/business-to-business/authentication)
- [Scalekit - B2B Universal vs Org-Specific Logins](https://www.scalekit.com/blog/designing-b2b-authentication-experiences-universal-vs-organization-specific-login)
- [WorkOS - Model B2B SaaS with Organizations](https://workos.com/blog/model-your-b2b-saas-with-organizations)
