# §C-1 アーキテクチャ — Identity Broker パターン

> 上位 SSOT: [00-index.md](00-index.md)   
> 詳細: [../../../common/identity-broker-multi-idp.md](../../../common/identity-broker-multi-idp.md)
>
> **⚠ 重要 — アーキテクチャ方針の再検討（2026-05-26）**:
> 本章は「完全統合（Identity Broker 一択）」を前提とした分析だが、設計レビュー段階で 6 つの懸念（SPOF / 過剰品質 / アプリ最適化放棄 / 個別変更困難 / 想定外対応 / 等）が提起された。これを踏まえた **ハイブリッド統合（コア統合 + エッジ自律）への方針転換提案**を [§C-6 アーキテクチャ判断: ハイブリッド統合の根拠と設計](06-architecture-decision-hybrid.md) で詳述。
>
> **読み方**:
> - 本章 §C-1 の Broker パターン分析は **ハイブリッドのコア層に適用**される（コア層内は引き続き Broker パターンで設計）
> - 全体アーキテクチャの最終判断は §C-6 を参照
> - D-6 ヒアリングは §C-6 §12 の拡張項目で確認

---

## §C-1.0 前提と背景

### 用語整理

| 用語 | 本基盤での意味 |
|---|---|
| **Identity Broker** | 複数の外部 IdP と各システムの間に立ち、認証を仲介するアーキテクチャパターン |
| **Hub-and-Spoke** | 中央集約型の通信トポロジー。本基盤の物理表現 |
| **IdP**(Identity Provider) | 顧客企業の認証情報を持つ外部システム(Entra ID / Okta / HENNGE 等) |
| **RP**(Relying Party) | 本基盤の JWT を受け取って認可判定するアプリ |
| **Federation Hub** | Identity Broker の別称(Microsoft / KuppingerCole 用語) |
| **Identity Fabric** | KuppingerCole 提唱の新世代 IAM 統合概念。Broker を内包したより広い枠組み |

### なぜここ(§C-1)で決めるか

```mermaid
flowchart LR
    S3["§FR-2 フェデレーション<br/>(IdP接続・処理・運用)"]
    S5["§FR-4 SSO"]
    S6["§FR-5 ログアウト"]
    S7["§FR-6 認可"]
    S10["§FR-9 外部統合"]
    S11["§C-1 アーキテクチャ<br/>全体構造の確定"]
    S12["§C-2 プラットフォーム<br/>(Cognito / Keycloak 選定)"]

    S3 --> S11
    S5 --> S11
    S6 --> S11
    S7 --> S11
    S10 --> S11
    S11 --> S12

    style S11 fill:#fff3e0,stroke:#e65100
```

§FR-1-§FR-9 で「**個別の機能・運用方針**」を確定してきた。§C-1 は **それらを束ねた "アーキテクチャ全体像"** を確定する。
§C-1 の方向性が決まれば、§C-2 「**どのプラットフォームで実装するか**」が判断可能になる。

### §C-1.0.A 本基盤のアーキテクチャスタンス

> **Identity Broker パターン(Hub-and-Spoke 型)を採用する。これは選択というより、§FR-2 で示した要件から構造的に導かれる必然である。**

```mermaid
flowchart TB
    subgraph CustomerIdP["顧客企業の IdP 群(Spoke - 一般従業員 P-3/P-4 用)"]
        C1["Acme<br/>Entra ID"]
        C2["Globex<br/>Okta"]
        C3["HENNGE<br/>顧客"]
        C4["AD 直結<br/>顧客"]
    end

    subgraph InternalIdP["弊社内 IdP (基盤運用管理者 P-1 用)"]
        I1["弊社<br/>Entra ID 等"]
    end

    Hub["共通認証基盤<br/>(Hub = Identity Broker)<br/>属性正規化 + 統一 JWT 発行<br/>+ Break Glass 用<br/>最小ローカル管理者"]

    subgraph Apps["各バックエンドシステム(RP)"]
        A1["経費精算"]
        A2["勤怠管理"]
        A3["人事システム"]
        A4["..."]
    end

    C1 -->|OIDC| Hub
    C2 -->|OIDC| Hub
    C3 -->|SAML| Hub
    C4 -->|LDAP| Hub
    I1 -->|"OIDC<br/>(基盤運用者用)"| Hub
    Hub -->|統一 JWT| A1
    Hub -->|統一 JWT| A2
    Hub -->|統一 JWT| A3
    Hub -->|統一 JWT| A4

    style Hub fill:#fff3e0,stroke:#e65100
    style InternalIdP fill:#f3e5f5,stroke:#7b1fa2
```

> **利用者カテゴリの位置付け**（[§FR-1.2.0.0](../fr/01-auth.md#fr-1200-ローカルユーザーとは何か--利用者カテゴリ別の分析) と整合）:
> - **顧客 IdP 群（Spoke）**: 顧客の一般従業員（P-3）+ テナント管理者（P-2、顧客 IdP あり時）の認証
> - **弊社内 IdP**: 基盤運用管理者（P-1）の認証。**γ シナリオ採用時に Must**
> - **共通基盤内最小ローカル**: Break Glass 用ローカル管理者（数名）+ IdP なし顧客分（シナリオ β / α 時の P-2/P-4）

#### このスタンスの業界根拠

| 出典 | 主張 |
|---|---|
| **Microsoft Azure Architecture Center** | "**Federated Identity Pattern**" として公式パターン化。"a federated identity provider acts as a broker, integrating IdPs via authentication protocols" |
| **KuppingerCole Leadership Compass: Identity Fabrics** | Identity Fabric の foundational layer に Broker パターンを位置付け。「**Orchestration, signal-driven decisions, seamless integration**」が新世代 IAM の核 |
| **Hub-and-Spoke Architectural Pattern** | "Hub component includes **identity and access control**, spokes inherit policies"。エンタープライズ統合の定石パターン |
| **AWS Cognito 公式 / Keycloak Identity Brokering** | 両プラットフォームが Broker パターンをネイティブ実装 |
| **WJAETS-2025 学術論文** | Broker パターンで「**統合点 18→6 に削減**」の定量効果を示す実証研究 |

### 共通認証基盤として「アーキテクチャ全体像」を確定する意義

| 観点 | 個別アプリで実装 | Broker パターン採用 |
|---|---|---|
| 顧客 IdP 追加 | 全アプリで個別対応 | **Broker に 1 度設定するだけ** |
| 各システムが検証する issuer | 顧客数 × プロトコル数 | **1 つだけ** |
| クレーム差異の吸収 | 各システムで対応 | **Broker で一元正規化** |
| テスト・セキュリティレビュー | 全組合せ | **Broker のみ** |
| 顧客追加リードタイム | 全システム改修 | **基盤の IdP 設定追加のみ(< 1 営業日)** |
| 管理運用コスト(業界調査) | 高 | **最大 60% 削減**(WJAETS-2025) |

→ Broker パターン採用は「**基本方針 4 軸すべての実現**」の中核装置。

### 本章で扱うサブセクション

| サブセクション | 内容 |
|---|---|
| §C-1.1 Broker パターン採用根拠 | なぜ Broker か、要件からの構造的導出、業界根拠 |
| §C-1.2 全体アーキテクチャ | 構成要素・データフロー・各章との対応 |
| §C-1.3 採用しない代替パターン | Point-to-Point / Mesh / Identity Fabric / BYOI の位置付け |
| §C-1.4 物理分離レベルと Broker パターンの関係 | 6 段階分離レベル(L1〜L6)と Broker 採用境界、業界実例 |

---

## §C-1.1 Broker パターン採用根拠

> **このサブセクションで定めること**: なぜ Identity Broker パターンを採用するかの **論理的導出**(§FR-2 で確定した要件から自動的に決まる)と業界根拠。   
> **主な判断軸**: §FR-2 の要件確定状況(マルチ IdP 要否 / 統一クレーム要否 / 顧客追加で各システム変更不要要否)   
> **§C-1 全体との関係**: §C-1.0.A のスタンスを「**要件 → 帰結**」のロジックで裏付ける

### §FR-2 の要件から Broker パターンが自動導出される

```mermaid
flowchart LR
    R1["§FR-2.1<br/>複数 IdP 受け入れ"] --> D1["集約点が必要"]
    R2["§FR-2.2<br/>属性の統一形式 JWT"] --> D2["属性変換層が必要"]
    R3["§FR-2.3.1<br/>顧客追加で<br/>各システム変更不要"] --> D3["issuer 集約が必要"]

    D1 --> Conclusion["Identity Broker<br/>(Hub-and-Spoke)<br/>パターン"]
    D2 --> Conclusion
    D3 --> Conclusion

    style Conclusion fill:#fff3e0,stroke:#e65100
```

### 要件と帰結の対応表

| §FR-2 の要件 | 帰結 |
|---|---|
| §FR-2.1 FR-FED-001〜007 が Must(複数 IdP 受け入れ) | **集約点が必要** = Hub |
| §FR-2.2.2 FR-FED-009 が Must(属性正規化) | **変換層が必要** = Hub 内属性マッピング |
| §FR-2.3.1 FR-FED-010 が Must(複数 IdP 並行運用) | **単一 issuer で発行** = Hub が JWT 発行 |
| §FR-2.3.2 FR-FED-011 が Must(顧客追加で各システム変更不要) | **アプリの依存先は Hub のみ** = Hub-and-Spoke 不可避 |

→ §FR-2 の Must 要件が決まれば、Broker パターン採用は **構造的に必然**(選択肢ではない)。

### 業界の現在地(業界根拠)

- **Microsoft Azure Architecture Center "Federated Identity Pattern"**: 公式クラウドデザインパターンカタログに登録(成熟したパターン)
- **KuppingerCole Identity Fabrics**: Broker を新世代 IAM の "Foundation" と位置付け、Leadership Compass で評価対象化
- **Keycloak / Cognito**: 両プラットフォームが Identity Brokering を**ネイティブ機能**として提供
- **学術定量効果**(WJAETS-2025): 統合点 18→6 削減、管理運用コスト 60% 削減

### 我々のスタンス(基本方針に基づく)

| 基本方針の柱 | Broker パターンでの実現 |
|---|---|
| **絶対安全** | 信頼境界が明確(Hub のみが発行する JWT を信頼)、各システムは Broker JWT のみ検証 |
| **どんなアプリでも** | 統一クレーム形式により**どんなバックエンドでも同じ方法で検証可能** |
| **効率よく** | 顧客追加で各システム変更不要、IdP 接続 < 1 営業日([§FR-2.3.2](../fr/02-federation.md#332-顧客追加オンボーディング--fr-fed-011)) |
| **運用負荷・コスト最小** | 統合点 60% 削減(業界調査)、テスト範囲は Broker のみ |

### ベースライン

| 項目 | ベースライン |
|---|---|
| アーキテクチャパターン | **Identity Broker(Hub-and-Spoke)採用** — Must |
| Hub の物理実装 | Cognito User Pool または Keycloak Realm([§C-2](02-platform.md) で選定) |
| マルチテナント方式 | **単一 Pool/Realm + 複数 IdP**([§FR-2.3.A](../fr/02-federation.md#33a-アーキテクチャ判断単一-poolrealm--複数-idp-を採用) で根拠) |
| 業界整合性 | Microsoft / KuppingerCole / AWS / OSS いずれの設計指針とも整合 |

### TBD / 要確認

| 確認項目 | 回答例 |
|---|---|
| Broker パターン採用に異論ないか | はい(推奨) / 反対意見あり |
| Hub の物理境界(単一基盤 / 用途別分離) | 単一 / 用途別(金融とそれ以外で分離等) |
| 既存 IdP(既存認証基盤含む)からの移行制約 | 段階移行 / 一括移行 / なし |

---

## §C-1.2 全体アーキテクチャ

> **このサブセクションで定めること**: Broker パターンを採用した本基盤の **全体構成図・データフロー・構成要素**の整理。各章で個別に扱った内容を 1 つの絵に統合。   
> **主な判断軸**: 構成要素の網羅性、データフローの正確性、運用主体の明示   
> **§C-1 全体との関係**: §C-1.1 の採用根拠を**実装イメージ**として可視化。§C-2 プラットフォーム選定の前提となる絵

### 全体構成図

```mermaid
flowchart TB
    subgraph CustomerIdP["顧客企業 IdP(Spoke)"]
        direction LR
        IdP1["Acme<br/>Entra ID"]
        IdP2["Globex<br/>Okta"]
        IdP3["HENNGE One<br/>(SAML)"]
        IdP4["AD<br/>(LDAP)"]
    end

    subgraph Basis["共通認証基盤(Hub)"]
        direction TB
        subgraph Auth["認証層"]
            AS["Authorization Server<br/>(Cognito or Keycloak)"]
            UD["User DB<br/>(ローカル + JIT)"]
            AS --- UD
        end
        subgraph Federation["フェデレーション層"]
            FED["IdP 接続マネージャ"]
            MAP["属性マッピング"]
            FED --- MAP
        end
        subgraph Token["トークン層"]
            JWT["JWT 発行<br/>(統一クレーム)"]
            JWKS["JWKS 公開"]
            JWT --- JWKS
        end
        subgraph Mgmt["管理層"]
            ADMIN["管理コンソール"]
            API["Admin REST API"]
            LOG["監査ログ"]
            ADMIN --- API --- LOG
        end
    end

    subgraph Apps["バックエンドシステム(RP)"]
        direction LR
        APP1["経費精算"]
        APP2["勤怠管理"]
        APP3["人事システム"]
        APP4["..."]
    end

    CustomerIdP --> Federation
    Federation --> Auth
    Auth --> Token
    Token --> Apps

    style Basis fill:#fff3e0,stroke:#e65100
    style CustomerIdP fill:#e3f2fd,stroke:#1565c0
    style Apps fill:#e8f5e9,stroke:#2e7d32
```

### データフロー(典型ログインケース)

```mermaid
sequenceDiagram
    participant U as ユーザー
    participant S as SPA(Acme システム)
    participant H as 共通認証基盤<br/>(Hub)
    participant I as Acme IdP<br/>(Entra ID)
    participant A as バックエンド API

    U->>S: アクセス
    S->>H: 認証要求(OIDC)
    H->>I: フェデレーション(OIDC)
    I->>U: ログイン画面
    U->>I: 認証情報 + MFA
    I->>H: 認証成功 + アサーション
    Note over H: §FR-2.2.2 属性マッピング<br/>tid → tenant_id<br/>group → roles
    H->>S: 統一 JWT 発行<br/>(sub, tenant_id, email)
    S->>A: Bearer JWT
    A->>H: JWKS で公開鍵取得(キャッシュ)
    A->>A: JWT 署名検証 + tenant_id 検証
    A->>S: レスポンス
```

### 構成要素マッピング(各章との対応)

| 構成要素 | 関連章 |
|---|---|
| 認証層(Authorization Server) | [§FR-1 認証](../fr/01-auth.md), [§FR-3 MFA](../fr/03-mfa.md), [§FR-4 SSO](../fr/04-sso.md), [§FR-5 ログアウト](../fr/05-logout-session.md) |
| フェデレーション層 | [§FR-2 フェデレーション](../fr/02-federation.md) |
| トークン層(JWT / JWKS) | [§FR-6 認可](../fr/06-authz.md), [§FR-9.1 プロトコル](../fr/09-integration.md#101-プロトコル準拠--fr-int-81) |
| 管理層 | [§FR-7 ユーザー管理](../fr/07-user.md), [§FR-8 管理機能](../fr/08-admin.md), [§FR-9.3 API・IaC](../fr/09-integration.md#103-apiiacwebhook--fr-int-83) |
| 監査層 | [§FR-8.2 監査](../fr/08-admin.md#92-監査可視性--fr-admin-72), [§FR-9.2 ログ・SIEM](../fr/09-integration.md#102-ログ監視--fr-int-82) |

### システム間接続パターンの一覧（静的な接続関係）

「**どこからどこへ、どんな目的で接続するか**」の俯瞰。動的なシーケンス図は次の「§C-1.2.A フロー図のインデックス」を参照。

| # | 接続元 | 接続先 | プロトコル | 認証方式 | 用途 |
|:---:|---|---|---|---|---|
| 1 | エンドユーザー（ブラウザ）| アプリ SPA / SSR | HTTPS | Cookie / Bearer | 業務操作 |
| 2 | アプリ SPA / SSR | 共通認証基盤（Hub）| **OIDC / OAuth 2.0**（Authorization Code + PKCE）| client_id（+ client_secret）| **ログイン / トークン取得** |
| 3 | 共通認証基盤（Hub）| 外部 IdP（Entra ID / Okta / HENNGE 等）| **OIDC / SAML 2.0 / LDAP** | client_secret / 証明書 | **フェデレーション（Spoke 側）** |
| 4 | 共通認証基盤（Hub）| アプリ SPA / SSR | HTTPS リダイレクト | — | **Authorization Code / Token 返却** |
| 5 | アプリ SPA / SSR | バックエンド API | HTTPS | **Bearer JWT**（共通基盤発行）| 業務 API 呼び出し |
| 6 | バックエンド API | 共通認証基盤（Hub）| HTTPS | — | **JWKS 取得**（公開鍵キャッシュ）|
| 7 | 共通認証基盤（Hub）| 各アプリ Back-Channel エンドポイント | HTTPS POST | client_secret | **Back-Channel Logout 通知**（[§FR-5.1](../fr/05-logout-session.md)）|
| 8 | 管理者（基盤運用）| 共通認証基盤の管理 API | HTTPS | IAM / Realm Admin | **テナント / IdP / Client 管理**（[§FR-8](../fr/08-admin.md)）|
| 9 | 監視 / 監査基盤 | 共通認証基盤の監査ログ | HTTPS / Kinesis | IAM | **CloudTrail / Event Listener**（[§FR-9.2](../fr/09-integration.md)）|
| 10 | （オプション）SPA | **BFF サーバー** | HTTPS | **HttpOnly Cookie**（セッション ID）| トークンを SPA に持たせない（[§FR-1.1 B](../fr/01-auth.md)）|
| 11 | （オプション）**BFF サーバー** | 共通認証基盤（Hub）| OIDC | client_secret（Confidential）| BFF が代理でトークン取得 |
| 12 | （オプション）**BFF サーバー** | バックエンド API | HTTPS | Bearer JWT 代理添付 | SPA からの API リクエストを BFF が中継 |

### §C-1.2.A 認証フロー・接続フロー図のインデックス

本資料群では、ユースケース別の**動的フロー（シーケンス図）を各章に分散配置**している。本セクションは逆引きインデックス。

| フロー / シナリオ | 場所 | 内容 |
|---|---|---|
| **フェデユーザーのログイン（典型 OIDC）** | §C-1.2 上記「データフロー」 | フェデレーション + JIT + 統一 JWT 発行 |
| **ローカルユーザーのログイン** | [§FR-1.1](../fr/01-auth.md#fr-11-認証フロー--grant-type-fr-auth-11) | ID/PW + MFA → JWT（Authorization Code + PKCE） |
| **SPA → BFF → 認可サーバー → API**（BFF パターン全体）| [bff-implementation-notes.md §6](../../../common/bff-implementation-notes.md) | ログイン / API 呼び出し / Refresh / ログアウトの 4 シーケンス |
| **API 呼び出し（JWT 検証）** | §C-1.2 上記「データフロー」末尾 + [authz-architecture-design.md](../../../common/authz-architecture-design.md) | Bearer JWT → JWKS → 検証 → tenant_id 検証 |
| **ステップアップ MFA**（RFC 9470）| [§FR-3.3](../fr/03-mfa.md) | AAL2 → AAL3 昇格、`acr_values` 要求 |
| **MFA 重複回避**（フェデユーザー、`amr` 信頼）| [§FR-2.2.3](../fr/02-federation.md) | 外部 IdP の MFA 主張を信頼してスキップ |
| **マルチテナント SSO 挙動**（3 シナリオ） | [§FR-2.3.C](../fr/02-federation.md#33c-マルチテナント環境での-sso-挙動) | 同一テナント内 / クロステナント / テナント切替 UI |
| **顧客 IdP 追加オンボーディング** | [§FR-2.3.2](../fr/02-federation.md) | IdP 情報受領 → Terraform PR → デプロイ → 疎通確認 |
| **4 レイヤーログアウト**（L1〜L4）| [§FR-5.1](../fr/05-logout-session.md) | ローカル / IdP セッション破棄 / フェデ連動 / Back-Channel |
| **Refresh Token Rotation（自動更新）** | [§FR-5.2](../fr/05-logout-session.md) + [bff-implementation-notes.md §6.3](../../../common/bff-implementation-notes.md) | Refresh 検出 → 新 Token 発行 → 旧 Refresh 破棄 |
| **継続的アクセス評価（CAEP、将来発展形）** | [§FR-5.4](../fr/05-logout-session.md) | リアルタイム deprovision / イベント駆動セッション無効化 |
| **PoC 実装の実構成図（参考）** | [doc/common/architecture.md](../../../common/architecture.md) | Phase 1-9 で実装した検証構成（Cognito / Keycloak 並列）|
| **Identity Broker パターンの詳細図群** | [doc/common/identity-broker-multi-idp.md](../../../common/identity-broker-multi-idp.md) | 抽象設計 / マルチ IdP 認証 / 属性変換 / スケール / セキュリティ |
| **8 つのシステム設計パターン**（IdP × SPA/SSR × DR）| [doc/common/system-design-patterns.md](../../../common/system-design-patterns.md) | 構成図 + 通信フロー + プロトコル詳細 |
| **プラットフォーム別本番想定構成**（Cognito / Keycloak OSS / RHBK）| [doc/common/platform-architecture-patterns.md](../../../common/platform-architecture-patterns.md) | **3 プラットフォームそれぞれの本番アーキテクチャ図** + Multi-AZ / Auto Scaling / DR / 月額コスト + 選定フロー |

→ **proposal §C-1.2 の全体構成図は「論理アーキテクチャの俯瞰」、各ユースケースの詳細フローは「該当章 + 内部技術メモ」に委譲**する設計。

---

### §C-1.2.B 想定 AWS 構成図（要件定義用、統合 + マーカー版）

> **このサブセクションで定めること**: 要件定義フェーズで顧客に提示する **「想定する AWS 構成」の叩き台**。プラットフォーム選定前提のため、Cognito / Keycloak 両採用パターンを **1 枚に統合 + マーカーで差分明示**。論理図（§C-1.2）の AWS リソースレベル表現。   
> **主な判断軸**: 顧客 IT 担当が理解しやすい抽象度、未確定箇所のマーカー、本番想定構成（[platform-architecture-patterns.md](../../../common/platform-architecture-patterns.md)）への詳細委譲   
> **§C-1 全体との関係**: §C-1.2 の論理図を「AWS リソース視点」に翻訳。**顧客ヒアリングの叩き台**として使い、Phase D で確定図へ進化させる前提

#### 全体構成図（3 アカウント前提、Cognito / Keycloak 統合表現）

```mermaid
flowchart TB
    User["👥 エンドユーザー<br/>(ブラウザ / モバイル)"]

    subgraph CustomerEnv["顧客環境 / 顧客指定 IdP（顧客ごとに異なる）"]
        CustIdP["顧客 IdP<br/>Entra ID / Okta / HENNGE /<br/>Google / Auth0 / Keycloak /<br/>オンプレ AD 等<br/>※ B-200 マスター表 B で確定"]
    end

    subgraph CDN["コンテンツ配信 + 防御層（共通基盤側）"]
        CF["☁️ CloudFront<br/>+ ACM 証明書"]
        WAF["🛡️ AWS WAF<br/>(レート制限 / Bot 対策)"]
    end

    subgraph AuthAccount["共通認証基盤 AWS アカウント【弊社運用】"]
        direction TB
        subgraph AuthServer["認可サーバー ★プラットフォーム選定対象（§C-2）"]
            Cog["🔴 Cognito User Pool<br/>※ Cognito 採用時のみ<br/>(Managed Login / Hosted UI)"]
            KC["🟦 Keycloak<br/>(ECS Fargate + Aurora)<br/>※ Keycloak 採用時のみ<br/>(カスタム VPC / 2 AZ)"]
        end
        AdminAPI["📡 Admin REST API<br/>(委譲管理者 / SCIM 受信)"]
        CT["📝 CloudTrail /<br/>Audit Log<br/>(全認証イベント)"]
        Secrets_A["🔐 Secrets Manager<br/>(Client Secret /<br/>SCIM Token)"]
    end

    subgraph AppAccount["アプリ AWS アカウント【× N、顧客 or 用途別】"]
        direction TB
        SPA["⚛️ SPA / SSR / Mobile"]
        subgraph BFFLayer["BFF レイヤー（オプション、§FR-1.1 B 要件次第）"]
            BFFλ["⚡ BFF Lambda<br/>(OAuth Confidential Client)"]
            DDB["🗄️ Session ストア<br/>DynamoDB + KMS"]
        end
        subgraph BE["バックエンド API"]
            APIGW["🟣 API Gateway"]
            Authλ["⚡ Lambda Authorizer<br/>(JWT 検証 + JWKS キャッシュ)"]
            BEλ["🟢 Backend Lambda / ECS"]
        end
        Secrets_App["🔐 Secrets Manager<br/>(BFF Token 保管 /<br/>SCIM クライアント認証)"]
    end

    User --> CF
    CF --> WAF
    WAF --> SPA

    SPA -->|"OIDC PKCE 直接"| AuthServer
    SPA -.オプション.-> BFFλ
    BFFλ -->|"OIDC + client_secret"| AuthServer
    BFFλ <--> DDB
    BFFλ -.- Secrets_App

    AuthServer ==>|"OIDC / SAML / LDAP<br/>(顧客 IdP 種別次第、B-200 表 列 Y)"| CustIdP
    CustIdP -.SCIM Push<br/>(顧客 IdP 対応時).-> AdminAPI

    SPA -->|"Bearer JWT"| APIGW
    BFFλ -->|"Bearer JWT 代理添付"| APIGW
    APIGW --> Authλ
    APIGW --> BEλ
    Authλ -.JWKS 取得 (1h キャッシュ).-> AuthServer

    AuthServer --> CT
    AuthServer -.- Secrets_A

    style AuthAccount fill:#fff5f5,stroke:#cc0000
    style AppAccount fill:#e8f5e9,stroke:#2e7d32
    style CustomerEnv fill:#e3f2fd,stroke:#1565c0
    style BFFLayer fill:#fff3e0,stroke:#e65100
    style AuthServer fill:#fff0f0,stroke:#cc0000
    style Cog fill:#ffe0e0
    style KC fill:#e0e8ff
```

#### マーカー凡例

| マーカー | 意味 |
|---|---|
| **※ Cognito 採用時のみ** / **※ Keycloak 採用時のみ** | [§C-2 プラットフォーム選定](02-platform.md) 後に **どちらか一方** が確定 |
| **※ B-200 マスター表 B で確定** | [hearing-script B-2](../../hearing-script/02-idp-federation.md) の顧客 IdP リスト次第 |
| **※ §FR-1.1 B 要件次第** | [§FR-1.1](../fr/01-auth.md) の SPA 認証方式（BFF or PKCE 直接）次第。**オプション層**として点線で表現 |
| **※ 顧客 IdP 対応時** | 顧客 IdP の SCIM Provisioning 対応有無次第（[B-401](../../hearing-script/04-user-management.md)）|

#### 構成要素の役割（顧客 IT 担当向け 1-2 行解説）

| アカウント / 層 | 構成要素 | 役割 |
|---|---|---|
| **顧客環境** | 顧客 IdP | 顧客企業の認証基盤。本基盤と OIDC / SAML / LDAP でフェデレーション。顧客ごとに異なる |
| **共通基盤** | CloudFront + WAF | コンテンツ配信 + DDoS / Bot 防御。全顧客共通の入口 |
| 共通基盤 | **Cognito User Pool** / **Keycloak** | 認可サーバー。**選定対象**（[§C-2](02-platform.md)）。フェデ受信 + JWT 発行を担当 |
| 共通基盤 | Admin REST API | 委譲管理者 / SCIM 受信エンドポイント。顧客アプリ運用がユーザー CRUD に使用 |
| 共通基盤 | CloudTrail / Audit Log | 全認証イベントの監査ログ。法定保存期間に応じて S3 へ転送 |
| 共通基盤 | Secrets Manager | OAuth Client Secret / SCIM Token 等の機密情報を KMS で暗号化保管 |
| **アプリアカウント** | SPA / SSR / Mobile | エンドユーザーが操作するフロントエンド。各アプリ独自に実装 |
| アプリアカウント | **BFF Lambda（オプション）** | SPA の代わりに OAuth トークンを保管。XSS リスク低減（金融 / 医療等で推奨）|
| アプリアカウント | Session ストア（DynamoDB）| BFF 採用時の session_id ↔ token マッピング保管 |
| アプリアカウント | API Gateway | バックエンド API のエントリポイント。Lambda Authorizer で JWT 検証 |
| アプリアカウント | Lambda Authorizer | JWT 署名検証 + 認可コンテキスト構築。JWKS を 1 時間キャッシュ |
| アプリアカウント | Backend Lambda / ECS | 業務ロジック実装。認可判定（[§FR-6.0.A](../fr/06-authz.md) 意味 B）はここで行う |
| アプリアカウント | Secrets Manager（アプリ側）| BFF 用 Token / SCIM クライアント認証情報の保管 |

#### 議論用マーカー（顧客との詰めポイント）

```mermaid
flowchart LR
    A["✅ 確定済<br/>(本基盤の標準提供)"]
    B["⚙️ 顧客要件次第<br/>(BFF 採否 / SCIM 採否 /<br/>テナント分離方式 等)"]
    C["🔵 プラットフォーム選定後に確定<br/>(Cognito or Keycloak)"]
    D["🟡 顧客 IdP 構成次第<br/>(B-200 マスター表 B で確定)"]
```

| 確定度 | 該当箇所 | 確定タイミング |
|---|---|---|
| ✅ **確定済**（本基盤標準提供）| CloudFront / WAF / Admin REST API / CloudTrail / Lambda Authorizer / JWT 検証経路 | 既定 |
| 🔵 **プラットフォーム選定後に確定** | Cognito User Pool or Keycloak（ECS + Aurora）| [§C-2](02-platform.md) 確定後（Phase D）|
| 🟡 **顧客 IdP 構成次第** | フェデ経路（OIDC / SAML / LDAP）、Identity Brokering の設定 | [B-200](../../hearing-script/02-idp-federation.md) マスター表 B 完成後 |
| ⚙️ **顧客要件次第（採否選択）** | BFF レイヤー / SCIM 受信 / DR 構成 / マルチリージョン | Phase B-C ヒアリング後 |

#### 詳細版へのリンク（プラットフォーム選定後）

本図はあくまで **要件定義フェーズの叩き台**。プラットフォーム選定後は以下の **本番想定構成図**に進化:

| 採用プラットフォーム | 詳細構成図 | 補足 |
|---|---|---|
| **Cognito** | [platform-architecture-patterns.md §2.1 Cognito 全体構成図](../../../common/platform-architecture-patterns.md) | Lambda Triggers / DR Account / 月額試算込み |
| **Keycloak OSS** | [platform-architecture-patterns.md §3.1 Keycloak OSS 全体構成図](../../../common/platform-architecture-patterns.md) | VPC / 2 AZ / Aurora / Internal ALB（Option B 完成形）|
| **Keycloak RHBK** | [platform-architecture-patterns.md §4.1 RHBK 構成パターン](../../../common/platform-architecture-patterns.md) | OSS との差分 + Red Hat サポート前提 |

#### ヒアリング時の使い方

```mermaid
flowchart LR
    S1["1. 本図を見せる<br/>(俯瞰共有)"]
    S2["2. マーカーで論点を整理<br/>(確定 / 未確定の明示)"]
    S3["3. 未確定箇所を質問<br/>(BFF? SCIM? IdP 構成?)"]
    S4["4. 回答を元に図を更新<br/>(マーカー → 確定要素へ)"]
    S5["5. Phase D で本番構成図へ"]

    S1 --> S2 --> S3 --> S4 --> S5

    style S5 fill:#fff3e0,stroke:#e65100
```

→ **要件定義 → 本番構成**へ滑らかに進化する叩き台として使用。

---

## §C-1.3 採用しない代替パターン

> **このサブセクションで定めること**: 検討した代替パターン(Point-to-Point / Mesh / Identity Fabric / BYOI)と、**なぜ採用しないか**の整理。   
> **主な判断軸**: 各代替パターンの本プロジェクト要件への適合度   
> **§C-1 全体との関係**: §C-1.1 の Broker 採用判断を、**代替案を排除した結果**として補強

### 代替パターン 5 つの位置付け

| パターン | 位置付け | 採用判断 |
|---|---|:---:|
| **① Point-to-Point**(個別連携) | 各システム ↔ 各 IdP を直接連携 | ❌ **却下**(顧客追加で全システム改修必要、N×M 接続) |
| **② Federation Mesh** | 複数 Broker が相互信頼するメッシュ | △ **将来オプション**(大学連合 GakuNin / 政府間連邦の規模が必要) |
| **③ Identity Fabric**(KuppingerCole) | Broker + IGA / PAM / AM を統合した上位概念 | △ **将来発展形**(本基盤の Broker 採用後、段階的拡張可能) |
| **④ BYOI**(Bring Your Own Identity) | B2B SaaS で顧客が自社 IdP を持ち込む要件呼称 | ✅ **本基盤で実現**(Broker パターンが BYOI の実装手段) |
| **⑤ 各アプリ独自ローカル認証** | 各アプリが独自 Login UI + ユーザー DB + パスワード管理を持つ。共通基盤は OAuth/OIDC で連携する外部 IdP としてのみ動作 | ❌ **却下**(Broker パターン崩壊、SSO 不可、品質差、コンプライアンス重複。詳細: [§FR-1.2.0](../fr/01-auth.md#220-ローカルユーザー認証の主体--11-アーキテクチャと連動)) |

### 各代替パターンとの関係

```mermaid
flowchart TB
    subgraph Today["本基盤(現在)"]
        Broker["Broker パターン<br/>(採用)"]
    end

    subgraph Rejected["却下"]
        P2P["Point-to-Point<br/>N×M 接続地獄"]
    end

    subgraph FutureScope["将来の発展形(必要時に拡張)"]
        Fabric["Identity Fabric<br/>(IGA+PAM+AM 統合)"]
        Mesh["Federation Mesh<br/>(複数 Broker 連邦)"]
    end

    subgraph CustomerView["顧客視点の呼称"]
        BYOI["BYOI<br/>(Broker パターンの実現)"]
    end

    Broker -.将来拡張.-> Fabric
    Broker -.大規模時.-> Mesh
    Broker --実現手段--> BYOI

    style Broker fill:#fff3e0,stroke:#e65100
    style P2P fill:#fff0f0,stroke:#cc0000
```

### 各代替パターンを採用しない理由

**① Point-to-Point(却下)**
- N×M(顧客数 × システム数)の接続が爆発
- 顧客追加で全システム改修が必要
- テスト範囲が膨大
- 基本方針「効率よく」「運用負荷低」と真逆

**② Federation Mesh(将来検討、現状は不要)**
- 複数 Broker が相互信頼する大規模連邦
- 採用ケース:大学連合(学術認証 GakuNin / eduGAIN)、政府間連邦
- 本プロジェクトの想定規模(顧客 100〜1000 社)では過剰
- 将来基盤が複数拠点・複数組織に拡張する場合に検討

**③ Identity Fabric(将来発展形)**
- KuppingerCole 提唱の新世代 IAM 統合概念
- Broker(本基盤) + IGA(Identity Governance) + PAM(Privileged Access) + AM(Access Management)の統合
- 本基盤は Identity Fabric の **Foundation** に位置付けられる
- 将来 IGA / PAM を追加導入する場合の自然な発展経路

**④ BYOI(実は採用)**
- 「顧客が自社 IdP を持ち込める」という**要件側の呼称**
- 実装手段としての Broker パターンとイコール
- 本基盤は BYOI の標準実装と言える

**⑤ 各アプリ独自ローカル認証(却下)**
- 各アプリが独自 Login UI + ユーザー DB + パスワード管理を持つ
- 共通基盤は外部 IdP として OAuth/OIDC で連携のみ
- 却下理由:
  - **Broker パターンの本質崩壊**: 集約点が消え、issuer が各アプリに分散
  - **SSO 不可能**: 同じユーザーがアプリ A と B で別認証セッション
  - **セキュリティの品質差**: パスワードハッシュ・MFA・侵害検出が各アプリで個別実装 → 最弱アプリが全体の天井
  - **コンプライアンス対応重複**: GDPR / SOC 2 / ISO 27001 を全アプリで個別対応必要
  - **退職時 deprovision 漏れリスク**: 基盤 1 回 → 全アプリ反映、にならない
  - **コスト**: 認証 UI / DB / バックエンドを N アプリ分実装
- 詳細評価と却下理由: [§FR-1.2.0 ローカルユーザー認証の主体](../fr/01-auth.md#220-ローカルユーザー認証の主体--11-アーキテクチャと連動)
- ただし **既存システム移行期間中の暫定運用（C 案ハイブリッド）は例外的に許容**（§FR-1.2.0 参照）

---

## §C-1.4 物理分離レベルと Broker パターンの関係

> **このサブセクションで定めること**: 「テナント分離をどこまで物理的に行うか」という顧客との議論において、**物理分離を強めるほど Broker パターンが成立しなくなる**という構造的トレードオフを明示。   
> **主な判断軸**: 顧客が要求する分離レベル（論理 / 物理ハイブリッド / 完全物理）  
> **§C-1 全体との関係**: §C-1.1 で採用した Broker パターンが、**どこまでの分離要求と両立するか**の境界線を示す。§FR-2.3.A.2（IdP なし顧客の選択肢）と §C-1.3（採用しない代替）と地続きの議論。

### §C-1.4.0 用語前提: Realm（Keycloak）≈ User Pool（Cognito）= 認証境界

物理分離の議論の前に、**Keycloak Realm と Cognito User Pool は同列に語れる概念**であることを明確化する。両者ともユーザー / 外部 IdP / クライアントを内包する独立した認証単位（tenancy boundary）。

| 概念 | Keycloak | Cognito | 説明 |
|---|---|---|---|
| **認証境界** | **Realm** | **User Pool** | 独立した認証単位、境界をまたぐ SSO は自動成立しない |
| **アプリ登録単位** | Client | App Client | 個別アプリ（expense-app / payment-app 等）の設定 |
| **SSO 範囲** | Realm 内のクライアント間で自動成立 | Pool 内の App Client 間で自動成立 | この境界が「分離の単位」になる |
| **外部 IdP 接続** | Realm 内 IdP | Pool 内 IdP | 顧客 IdP を Federation 接続する |

#### 階層構造の例

```
Keycloak Realm "shared"                Cognito User Pool "shared-pool"
├── Users（ローカルユーザー）           ├── Users
├── Identity Providers                ├── Identity Providers
│   ├── acme-entra-id                 │   ├── acme-entra-id
│   └── globex-okta                   │   └── globex-okta
├── Clients                           ├── App Clients
│   ├── expense-app                   │   ├── expense-app
│   ├── payment-app                   │   ├── payment-app
│   └── hr-app                        │   └── hr-app
└── Sessions                          └── Hosted UI
```

→ 以下 L1〜L6 の「分離」とは、**この Realm/Pool（認証境界）の単位をどう設けるか**の選択を指す。

#### よくある誤解への即答

| 誤解 | 訂正 |
|---|---|
| **「Realm をアプリ単位で分けるべき?」** | ❌ 非推奨。アプリ間 SSO が完全に失われる = SSO 基盤の意味なし。アプリは **Client（同一 Realm 内）** として登録するのが正しい単位 |
| **「Realm を顧客（IdP）単位で分けることはできないのでは?」** | ✅ 可能。それが **L3 物理分離**。同一 Realm 内のアプリ間で SSO は成立するため、「顧客 acme のユーザーが acme の全アプリで SSO」は実現できる |
| **「全顧客 L3 にすれば最も安全」** | ⚠ Identity Broker パターン崩壊、N×M Client 登録、Cognito Custom Domain 4 個 Hard Limit、設定ドリフト等の重大デメリット |

### 「全部物理分離 = Broker パターン採用不可」の理解は概ね正しい

顧客から **「テナントごとに完全に物理的に分離してほしい」** という要求が出た場合、これは構造的に Broker パターンを放棄することと等価。理由は明確で:

- **Broker = 単一 Hub で issuer / 属性正規化 / JWT 発行を集約する**ことが本質
- すべて物理分離するということは **Hub が顧客数ぶん必要** = もはや Hub ではなく N 個の独立基盤
- 各システム（RP）が検証する issuer も顧客数ぶんになり、§FR-2.3.2「顧客追加で各システム変更不要」が崩壊
- → **Broker パターン採用の構造的必然性（§C-1.1）が消失** = 共通認証基盤を構築する意味そのものがなくなる

### 物理分離の 6 段階グラデーション

実際には「論理 ↔ 物理」は二者択一ではなく、**6 段階のグラデーション**で考えるべき。

```mermaid
flowchart LR
    L1["L1<br/>完全集約<br/>(単一 Pool+IdP)"]
    L2["L2<br/>論理分離<br/>(単一 Pool+<br/>複数 IdP)"]
    L3["L3<br/>ハイブリッド<br/>(規制顧客のみ<br/>別 Pool/Realm)"]
    L4["L4<br/>階層 Broker<br/>(子 Broker を<br/>顧客側に)"]
    L5["L5<br/>Federation Mesh<br/>(複数 Broker<br/>相互信頼)"]
    L6["L6<br/>完全分散<br/>(顧客ごと独立基盤)"]

    L1 --> L2 --> L3 --> L4 --> L5 --> L6

    style L2 fill:#fff3e0,stroke:#e65100
    style L3 fill:#fff3e0,stroke:#e65100
    style L1 fill:#ffe0e0,stroke:#cc0000
    style L6 fill:#ffe0e0,stroke:#cc0000
```

### 各レベルの特性比較

| Lv | 名称 | 物理分離の範囲 | Broker パターン互換性 | 実装難度 | 採用事例 |
|:---:|---|---|:---:|:---:|---|
| L1 | 完全集約 | 顧客ごと IdP も持たない（基盤内ローカルユーザーのみ）| ◎ Broker が最大価値 | 低 | 単一テナント SaaS |
| **L2** | **論理分離（標準）** | 単一 Pool/Realm + 複数 IdP + `tenant_id` クレーム | ◎ **Broker の標準形** | 中 | **Slack / Notion / Linear / Box** |
| **L3** | **ハイブリッド** | 規制業種顧客のみ別 Pool/Realm（金融・医療等）+ 一般顧客は L2 | ○ **Broker を顧客カテゴリ別に複数化** | 中〜高 | **Auth0 Private Cloud / Microsoft Entra GCC / Okta Custom Cell** |
| L4 | 階層 Broker | Hub Broker の下に顧客側 Broker を配置 | △ Broker 多段化 | 高 | 大企業内グループ会社統合 |
| L5 | Federation Mesh | 完全独立した複数 Broker が相互信頼 | △ Broker の連邦化（§C-1.3） | 極めて高 | GakuNin（学術認証）/ eduGAIN / 政府間連邦 |
| L6 | 完全分散 | 顧客ごとに完全独立した認証基盤 | ✗ **Broker 不成立** | 不要（基盤要らず）| **オンプレ個別構築 / 顧客自前運用** |

→ **L1 と L6 は Broker パターンの否定**（前者は「集約しすぎて顧客 IdP なし」、後者は「分散しすぎて Hub なし」）。**L2-L3 が現実解**。

### 業界の実例で見る分離レベル

| 企業 / サービス | 採用レベル | 内容 |
|---|:---:|---|
| **Slack** | **L2** | 単一 Pool + Workspace ごとの IdP 接続 + ワークスペース ID で分離 |
| **Notion** | **L2** | 単一 Pool + Workspace SSO + workspace_id で分離 |
| **Linear** | **L2** | 単一 Pool + SAML / SCIM 接続 + organization_id |
| **Box** | **L2** | 単一基盤 + Enterprise SSO + enterprise_id |
| **Auth0 Private Cloud** | **L3** | 標準は共有テナント / 規制業種は専用 Private Cloud（別 Pool）|
| **Microsoft Entra GCC / GCC-High / DoD** | **L3** | 一般顧客は共有 Entra ID / 米政府機関は GCC（別物理クラスタ）|
| **Okta Custom Cell** | **L3** | 標準は Shared Cell / 高セキュリティ顧客は Dedicated Cell |
| **AWS GovCloud** | **L3** に近い | リージョン物理分離（同じ Cognito だが別エンドポイント）|
| **GakuNin（学術認証）** | **L5** | 各大学が独立した Broker を持ち、相互信頼でメッシュ化 |

→ **業界のメインストリームは L2 標準 + L3 オプション**。L1（完全集約のみ）も L6（完全分散のみ）も実用ベンダーには見当たらない。

### 顧客が「全部物理分離」と言うときの本当のニーズ

顧客の「物理分離してほしい」要求は、多くの場合は以下のいずれか（または組み合わせ）で、**L6 の完全分離を求めているわけではない**ことが多い。

| 顧客の表現 | 真のニーズ | 対応レベル |
|---|---|:---:|
| 「他社とパスワードが同じ DB にあるのは嫌」 | パスワードハッシュの DB 同居回避 | **§FR-2.3.A.2 D 案ハイブリッド**（IdP 化）で L2 のまま解決可 |
| 「監査時に他社データに触れない構成にしたい」 | 監査スコープ限定 | **L3 ハイブリッド**（規制顧客のみ別 Pool / Realm）|
| 「データ主権上、別国・別リージョンに置きたい」 | リージョン分離 | **L3 ハイブリッド**（リージョン別 Pool）|
| 「マルチテナント脆弱性（CVE）の影響を分離したい」 | Blast radius 限定 | **L3 ハイブリッド** + テナントごと暗号鍵分離 |
| 「他社と同じソフトを使うのが信用上 NG」 | 専有環境の見え方 | **L3 ハイブリッド** or **Dedicated Cell 提案** |

→ **本当に L6 を要求しているケースはほぼない**。L3 のハイブリッドで多くの分離ニーズは満たせる。

### 「全部物理分離」を要求された場合の本基盤の立場

| 本基盤の立場 | 内容 |
|---|---|
| **基本: L2 を標準提供** | 単一 Pool/Realm + 複数 IdP（[§FR-2.3.A](../fr/02-federation.md#33a-アーキテクチャ判断単一-poolrealm--複数-idp-を採用)） |
| **オプション: L3 を選択肢に** | 規制業種顧客 / 大口顧客のみ別 Pool / Realm を提供（追加料金）|
| **顧客が L6 を強硬に求める場合** | **本基盤の対象外**。顧客自前運用 or 個別 SI 案件として扱う（Broker 価値が消えるため）|
| **L4 / L5 への発展** | 将来 M&A / 子会社統合 / 業界連合の規模になった場合に検討（[§C-1.3](#§c-13-採用しない代替パターン)）|

### 結論

> **「全部物理分離」= Broker パターン放棄 = 本基盤の存在価値消失**、という構造的事実は顧客に明示すべき。  
> 実務上は **L2（論理分離）を標準**とし、**L3（規制顧客のみハイブリッド物理分離）をオプション**として提供する形が業界標準であり、本基盤の方針。  
> 顧客の「物理分離」要望は、**真のニーズを掘って [§FR-2.3.A.2](../fr/02-federation.md#33a2-idp-なし顧客のユーザー管理) の 4 オプション（A〜D）や L3 で満たせるか**を最初に検討する。

### TBD / 要確認

| 確認項目 | 回答例 |
|---|---|
| 標準提供レベルは L2 で合意できるか | 合意 / 別案 |
| L3（規制顧客向け別 Pool）の提供範囲 | 全顧客対応 / 一定規模以上のみ / 提供しない |
| L6 を求める顧客の扱い | 対象外 / 個別 SI / 顧客自前運用支援 |
| 「物理分離」要求顧客への真のニーズヒアリング手順 | ヒアリングテンプレ化 / 営業判断 |

---

## §C-1.5 規模スケーリング戦略（1500-3000 顧客企業）

> **このサブセクションで定めること**: 顧客企業数（テナント数）が **1500-3000 規模** になった場合の、L2 論理分離の維持可否と Hard Limit 抵触対策。**A-15（顧客企業数）** との連動章。
> **主な判断軸**: Cognito Hard Limit（IdP per Pool、Custom Domain）の抵触判定、Keycloak 単一 Realm の運用限界。

### §C-1.5.0 規模を聞く理由

**MAU（A-1/A-2）とは別軸**で、**顧客企業数（テナント数 = IdP 接続数）** が **Cognito Hard Limit に直接抵触**する。MAU が小さくても顧客企業が 1500 社あれば Cognito 単一 Pool は不可。事業計画に応じた **5 年後想定** まで把握することで、初期設計段階で **スケール戦略** を組み込む。

### §C-1.5.1 Cognito Hard Limit と顧客企業数の関係

#### 主要な Hard Limit（2026 時点）

| リソース | デフォルト上限 | 引き上げ可否 | 1500-3000 顧客時の影響 |
|---|---:|---|---|
| **Identity Providers per User Pool** | 1,000 | ⚠ 引き上げ要相談（実質ハード）| 単一 Pool では **不足**（1500 で抵触）|
| **SAML IdPs per User Pool**（実質）| 約 50-100 | 個別案件 | **HENNGE / ADFS / 国内 IDaaS が 100 社超で抵触** |
| **User Pools per AWS account per Region** | 1,000 | ✅ 引き上げ可 | 3000 顧客分けても OK（10-30 Pool で済む）|
| **Custom Domain per Region** | **4** | ❌ **完全ハード** | Pool ごとに別 Domain にすると 4 Pool で詰む |
| **App Clients per User Pool** | 10,000 | ✅ 引き上げ可 | 余裕あり |
| **AdminCreateUser API** | 50 RPS | ✅ 引き上げ可 | バルクインポート時注意 |
| **M2M Token endpoint** | 150 RPS | ✅ 引き上げ可 | 大規模バッチ時注意 |

→ **問題は IdP 上限（特に SAML）と Custom Domain 4 個 Hard Limit**。

#### Cognito 採用時の Pool 分割戦略（変形 L2）

**Pool あたり 100-200 顧客が現実解**：

```
本基盤 Cognito（事業者 AWS アカウント）
├── User Pool "shared-cohort-01"（顧客 1-100、SAML 80 + OIDC 20）
│   ├── 100 IdP
│   └── App Clients: expense / payment / hr ...
├── User Pool "shared-cohort-02"（顧客 101-200）
│   └── 100 IdP
├── ...（15-30 Pool）
└── 共通 Custom Domain: auth.example.com（Path で Pool ルーティング、Lambda@Edge）
```

**運用上の課題**：
- **Custom Domain 4 個 Hard Limit**: Pool ごとに別 Domain にすると 4 Pool 目で詰む
  - 対策 1: **共通 Domain + Path で Pool ルーティング**（Lambda@Edge / API Gateway で Pool ID 判定）
  - 対策 2: **複数リージョンに分散**（4 Pool × 4 リージョン = 16 Pool まで、さらに複雑）
- **アプリ側**: 30 Pool それぞれに App Client 登録 = **30 個の issuer 検証**ロジック（Lambda Authorizer で multi-issuer 対応必須）
- **顧客振り分けロジック**: HRD（メールドメイン → どの Pool か）の実装が必要
- **Pool 間 SSO**: ❌ 不成立（顧客またぎの SSO は B2B では不要）

→ **これは「変形 L2」**。論理分離の思想は維持しつつ、Cognito 制約で物理的に複数 Pool に分かれる。

### §C-1.5.2 Keycloak の Limit と顧客企業数の関係

| リソース | 上限 | 1500-3000 顧客時の評価 |
|---|---|---|
| **Realm 数** | 実質無制限（PostgreSQL DB 性能依存）| 単一 Realm で対応推奨 |
| **Identity Providers per Realm** | 実質無制限（数千 OK）| ✅ 1500-3000 IdP 可能 |
| **Clients per Realm** | 実質無制限（万 OK）| ✅ 余裕 |
| **Users per Realm** | 数千万（適切な DB 設計）| 全顧客総ユーザー数次第 |
| **Organizations per Realm**（26+）| 実質無制限 | ✅ 1500-3000 Organization OK |

#### Keycloak 採用時の構成（Organization 機能活用）

```
Realm "shared"（1 つだけ）
├── Organizations: 1500-3000（顧客企業ごとに 1 Organization）
├── Identity Providers: 1500-3000
├── Clients: 10〜30 程度（全アプリ）
└── 単一 Custom Domain: auth.example.com（顧客数によらず 1 つで OK）
```

**メリット**：
- **Custom Domain は 1 つで完結**（Cognito の Hard Limit 問題なし）
- **Identity Broker パターン完全成立**（各アプリは Realm 1 つだけを Trust）
- **アプリ追加は 1 回**（全顧客で利用可能）
- **顧客追加は IdP + Organization 登録 1 回**

**留意点**：
- **Admin Console** で 3000 IdP 一覧表示は重い → **Organization 単位での管理**で UX 向上
- **DB チューニング**: PostgreSQL の indexing、Realm cache size 設定が必要
- **JWKS endpoint キャッシュ**: アプリ側で適切にキャッシュ（5 分等）すれば認証レイテンシ問題なし

### §C-1.5.3 プラットフォーム比較（1500-3000 顧客規模）

| 観点 | **Cognito**（複数 Pool 分割必須）| **Keycloak**（単一 Realm + Organization）|
|---|---|---|
| **Pool/Realm 数** | **15-30 Pool**（cohort 別、100-200 顧客/Pool）| **1 Realm**（Organization 機能で論理分割）|
| **Custom Domain** | 4 Pool しか持てない → Path ルーティング or 複数リージョン | **共通 1 つ**で全 3000 顧客カバー |
| **アプリ追加コスト** | 各 Pool に App Client 登録（**15-30 回**）| **1 回**で完結 |
| **顧客追加コスト** | どの Pool に入れるか判定 + 登録 | **Organization + IdP 登録 1 回** |
| **Identity Broker パターン** | ⚠ 部分崩壊（multi-issuer Lambda Authorizer で吸収）| **✅ 完全成立** |
| **運用画面操作性** | Pool ごとに Console 切替 | Organization 単位で集約管理（26+）|
| **DB 設計負荷** | AWS マネージドで不要 | PostgreSQL チューニング必要 |
| **リスク** | **SAML IdP Hard Limit に確実に抵触** | DB / Cache チューニング失敗時の性能劣化 |
| **本基盤での評価** | **規模が大きいほど不利**（運用複雑化）| **規模が大きいほど有利**（単一 Realm で対応）|

→ **1500-3000 顧客規模では Keycloak が圧倒的に有利**（Cognito 採用時は Pool 分割の運用負荷が顕著に重い）。

### §C-1.5.4 認証性能（per-request 性能）

総顧客数とは別に、**1 回の認証リクエストあたりの性能**：

| 観点 | 影響 | 顧客数依存 |
|---|---|---|
| **JWT 発行レイテンシ** | 100-300ms（標準）| ❌ 顧客数に依存しない |
| **JWKS 検証**（アプリ側）| キャッシュで 1ms 以下 | ❌ 依存しない |
| **HRD 解決**（メールドメイン → IdP）| 1-10ms（DB ルックアップ）| ⚠ 顧客数に弱依存（インデックスで対応）|
| **Token Exchange / Lambda Authorizer** | 100-500ms | ❌ 依存しない |
| **Cognito レート制限**（M2M 150 RPS / Pool）| - | ⚠ Pool 分割により 1 Pool あたりは緩和 |
| **Keycloak DB クエリ** | 1-50ms | ⚠ インデックス・キャッシュチューニング次第 |

→ **3000 顧客でも認証レイテンシは劣化しない**（適切な設計なら）。問題になるのは **管理画面操作・初期化時間・バッチ処理レート**。

### §C-1.5.5 5 年見据えた拡張シナリオ

#### Keycloak 採用シナリオ

| Year | 顧客数 | 構成 | 運用ポイント |
|:---:|---:|---|---|
| 0 | 1,500 | 単一 Realm + Organization | DB は PostgreSQL r6i.2xlarge クラス、JWKS キャッシュ 5 分 |
| 3 | 2,500 | 単一 Realm + 性能監視強化 | Realm 起動時間 / 認可レイテンシ監視 |
| 5 | 3,000 | 単一 Realm or 2-3 分割 | L3 物理分離顧客（数社）は別 Realm |
| 8 | 5,000+ | 複数 Realm 分割 | 地域別 / 業種別 Realm |

#### Cognito 採用シナリオ（参考）

| Year | 顧客数 | 必要 Pool 数 | 課題 |
|:---:|---:|---:|---|
| 0 | 1,500 | **15** | Pool 分割設計が初期から必要 |
| 3 | 2,500 | **25** | Pool 間でのアプリ Client 同期運用 |
| 5 | 3,000 | **30** | **運用負荷が線形に増加**、人員 増員必須 |

→ Cognito 採用は **規模拡大に伴い運用負荷が爆発**するため、1500-3000 顧客規模では Keycloak を強推奨。

### §C-1.5.6 規模別の本基盤対応マトリクス

| 顧客企業数 | 推奨プラットフォーム | 構成 | 運用負荷 |
|---:|---|---|---|
| 〜100 社 | Cognito / Keycloak 両方可 | 単一 Pool/Realm | 低 |
| 〜500 社 | **Keycloak 推奨** | 単一 Realm + Organization | 中 |
| **1500-3000 社** | **Keycloak 強推奨** | 単一 Realm + Organization + DB チューニング | 中〜高 |
| 〜10000 社 | Keycloak（複数 Realm 分割）| Realm 分割 + 専任 SRE | 高 |

### TBD / 要確認

| 確認項目 | 回答例 |
|---|---|
| 想定顧客企業数（現状 / 3 年 / 5 年）| 1500 / 2500 / 3000 等 |
| 規模軸での Cognito vs Keycloak 選定合意 | Keycloak 強推奨に合意 / Cognito Pool 分割で進める |
| Pool 分割戦略採用時の Custom Domain 構成 | 共通 1 Domain + Path ルーティング / 複数リージョン |
| Keycloak DB 性能基準 | 認可レイテンシ P95 〇〇 ms 以下 等 |

---

## §C-1.6 TBD / 要確認

| 確認項目 | 回答例 |
|---|---|
| Broker パターン採用に異論ないか | 異論なし(推奨) / 他案を検討したい |
| 物理境界(用途別分離の必要性) | 単一基盤 / 用途別分離 |
| 既存システム認証基盤からの移行戦略 | 段階移行 / 一括移行 / 並行稼働 |
| 将来の Identity Fabric への発展可能性 | あり(IGA / PAM 統合検討) / Broker で完結予定 |
| Federation Mesh への発展可能性 | あり(複数拠点・複数組織想定) / 単一 Broker で完結 |

---

### 参考資料(§C-1 全体)

#### Broker パターン業界根拠

- [Microsoft Azure Architecture Center - Federated Identity Pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/federated-identity)
- [KuppingerCole Leadership Compass: Identity Fabrics](https://www.kuppingercole.com/research/lc81426/identity-fabrics)
- [KuppingerCole Identity Fabric 2025 / 2026](https://www.kuppingercole.com/blog/reinwarth/the-kuppingercole-identity-fabric-2025)
- [Keycloak Identity Brokering 公式](https://www.keycloak.org/docs/latest/server_admin/index.html)
- [AWS Cognito - User pool sign-in with third party IdPs](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-identity-federation.html)
- [WJAETS-2025 Federated identity management](https://journalwjaets.com/sites/default/files/fulltext_pdf/WJAETS-2025-0919.pdf)

#### Hub-and-Spoke パターン

- [Enterprise Integration Patterns - Hub and Spoke](https://www.enterpriseintegrationpatterns.com/ramblings/03_hubandspoke.html)
- [Hub-and-Spoke Architecture 2026 Guide - CloudOpsNow](https://www.cloudopsnow.in/hub-and-spoke/)

#### 内部ドキュメント

- [identity-broker-multi-idp.md](../../../common/identity-broker-multi-idp.md): Broker パターン詳細
- [§FR-2.3.A アーキテクチャ判断](../fr/02-federation.md#33a-アーキテクチャ判断単一-poolrealm--複数-idp-を採用): 単一 Pool/Realm + 複数 IdP の根拠
