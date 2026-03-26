# MFA・SSO 比較マトリクス（Cognito / Keycloak / Auth0）

**作成日**: 2026-03-26

---

## 1. MFA（多要素認証）

### 1.1 MFA対応方式の比較

| MFA方式 | Cognito | Keycloak | Auth0 Free |
|---------|:-------:|:--------:|:----------:|
| **TOTP（Google Authenticator等）** | ✅ | ✅ | ✅ |
| **SMS** | ✅（SNS経由） | ✅（SPI拡張） | ✅ |
| **Email OTP** | ✅（Essentials以上） | ✅ | ✅ |
| **WebAuthn / FIDO2（指紋・顔・YubiKey）** | **✅（2024年11月追加、Essentials以上）** | ✅ | ✅（有料プラン） |
| **Push通知** | ❌ | △（SPI拡張） | ✅（有料プラン） |
| **リカバリーコード** | ❌ | ✅ | ✅ |

> **2024年11月更新**: CognitoにWebAuthn/パスキーサポートが追加された（Essentials以上のプラン）。最大20パスキー/ユーザー登録可能。ただし選択ベース認証フローでのみ利用可能。

### 1.2 MFAの設定・管理の比較

| 観点 | Cognito | Keycloak | Auth0 |
|------|---------|----------|-------|
| **MFA設定場所** | User Pool設定（Terraform） | Realm → Authentication Flow | Auth0 Dashboard |
| **ユーザーごとのMFA強制** | グループ単位 or 全ユーザー | **認証フローで条件分岐可能**（ロール・グループ・IdP別） | ルール/アクションで条件分岐 |
| **MFAデータ保存先** | AWS内部（不可視） | **`credential` テーブル（PostgreSQL）** | Auth0内部（不可視） |
| **MFAの可視性** | ユーザー単位で確認可能（API） | **Admin Console で確認・削除可能** | Dashboard で確認可能 |
| **MFAリセット（管理者）** | `admin-set-user-mfa-preference` | Admin Console → ユーザー → Credentials → 削除 | Dashboard → ユーザー → MFA |

### 1.3 ユーザー種別ごとのMFA責任

```mermaid
flowchart TB
    subgraph Cognito_Arch["Cognito構成"]
        CU_Local["ローカルユーザー\n→ CognitoがMFA提供"]
        CU_Fed["フェデレーションユーザー\n→ Auth0/Entra IDがMFA提供\n→ CognitoはMFA不要"]
    end

    subgraph KC_Arch["Keycloak構成"]
        KU_Local["ローカルユーザー\n→ KeycloakがMFA提供"]
        KU_Fed["フェデレーションユーザー\n→ Auth0/Entra IDがMFA提供\n→ KeycloakはMFAスキップ"]
    end

    style Cognito_Arch fill:#fff0f0,stroke:#cc0000
    style KC_Arch fill:#f5f0ff,stroke:#6600cc
```

| ユーザー種別 | Cognito構成でのMFA | Keycloak構成でのMFA |
|-------------|-------------------|-------------------|
| **ローカルユーザー**（ID/PW直接管理） | Cognito MFA（TOTP/SMS） | **Keycloak MFA（TOTP/WebAuthn）** |
| **フェデレーション（Auth0経由）** | Auth0がMFA | Auth0がMFA（Keycloakスキップ） |
| **フェデレーション（Entra ID経由）** | Entra IDがMFA | Entra IDがMFA（Keycloakスキップ） |

**原則**: MFAは**ユーザーのパスワードを管理している側**が提供する。

### 1.4 MFAデータの障害耐性

| 障害シナリオ | Cognito | Keycloak |
|-------------|---------|----------|
| **認証サーバー再起動** | 影響なし（マネージド） | **影響なし**（DBに保存） |
| **DB障害 → 復旧** | 影響なし（マネージド） | **影響なし**（DB復旧で復元） |
| **DR切替（クロスリージョン）** | 別User Pool → **MFAは同期されない → ユーザーが再登録必要** | Aurora Global DB → **MFAは同期される（<1秒遅れ）** |

```mermaid
flowchart TB
    subgraph Cognito_DR["Cognito DR"]
        C_Tokyo["東京 User Pool\nMFA: TOTP登録済み"]
        C_Osaka["大阪 User Pool\nMFA: ★未登録（別Pool）"]
        C_Tokyo -.->|"同期されない"| C_Osaka
    end

    subgraph KC_DR["Keycloak DR (Aurora Global DB)"]
        K_Tokyo["東京 RDS\ncredential テーブル\nMFA: TOTP登録済み"]
        K_Osaka["大阪 Aurora Secondary\ncredential テーブル\nMFA: ★同期済み（<1秒遅れ）"]
        K_Tokyo -->|"非同期レプリケーション"| K_Osaka
    end

    style Cognito_DR fill:#fff0f0,stroke:#cc0000
    style KC_DR fill:#d3f9d8,stroke:#2b8a3e
```

**重要な発見**: **DRにおけるMFA維持はKeycloakが優位**。Cognitoでは別User Poolにユーザーがいないため、DR切替後にMFAを含めて再登録が必要。Keycloakではcredentialテーブルがレプリケーションされるため、MFA設定も引き継がれる。

---

## 2. SSO（シングルサインオン）

### 2.1 SSO方式の比較

| 観点 | Cognito + Auth0 | Keycloak単体 | Keycloak + Auth0 |
|------|----------------|-------------|-----------------|
| **SSOの仕組み** | Auth0のセッションCookie | Keycloakのセッション Cookie（`KEYCLOAK_SESSION`） | Keycloakのセッション + Auth0セッション（二層） |
| **SSO範囲** | 同一Auth0テナント配下の全User Pool | **同一Realm内の全Client** | 同一Realm内の全Client |
| **SSOの設定** | 不要（Auth0セッションで自動） | **不要（同一Realm内は自動）** | 不要 |
| **SSOセッション制御** | Auth0のタイムアウト設定 | **SSO Session Idle / Max（Realm設定）** | Keycloak側で制御 |

### 2.2 SSOが効くケースと効かないケース

```mermaid
flowchart TB
    subgraph Works["✅ SSOが効く"]
        W1["Cognito: User Pool A(Auth0) → User Pool B(Auth0)\n同じAuth0テナント → Auth0セッションで自動ログイン"]
        W2["Keycloak: Client A → Client B\n同じRealm → Keycloakセッションで自動ログイン"]
        W3["Keycloak+Auth0: Client A(Auth0経由) → Client B\n同じRealm → Keycloakセッションで自動ログイン\n（Auth0に再問い合わせしない）"]
    end

    subgraph NotWork["❌ SSOが効かない"]
        N1["Cognito: User Pool A → User Pool B\nAuth0を使わずローカルユーザーのみ\n→ 別Poolなので独立"]
        N2["Keycloak: Realm A → Realm B\n異なるRealm → セッション共有なし"]
    end

    style Works fill:#d3f9d8,stroke:#2b8a3e
    style NotWork fill:#fff0f0,stroke:#cc0000
```

### 2.3 SSOフロー詳細比較

#### パターン1: Cognito + Auth0

```mermaid
sequenceDiagram
    participant User as ユーザー
    participant AppA as 経費精算SPA<br/>(User Pool A)
    participant CogA as Cognito A
    participant Auth0 as Auth0
    participant AppB as 出張予約SPA<br/>(User Pool B)
    participant CogB as Cognito B

    User->>AppA: アクセス
    AppA->>CogA: /authorize (identity_provider=Auth0)
    CogA->>Auth0: OIDC /authorize
    Auth0->>User: ログイン画面 + MFA
    User->>Auth0: 認証成功
    Note over Auth0: ★ Auth0セッション Cookie 作成
    Auth0->>CogA: code
    CogA->>AppA: Cognitoトークン

    Note over User,AppB: 出張予約にアクセス

    User->>AppB: アクセス
    AppB->>CogB: /authorize (identity_provider=Auth0)
    CogB->>Auth0: OIDC /authorize
    Note over Auth0: ★ Auth0セッション有効<br/>→ PW/MFA不要
    Auth0->>CogB: code（即座）
    CogB->>AppB: Cognitoトークン
```

**SSOの主体**: Auth0（Auth0セッションCookieが鍵）

#### パターン2: Keycloak単体（ローカルユーザー）

```mermaid
sequenceDiagram
    participant User as ユーザー
    participant AppA as 経費精算SPA<br/>(Client A)
    participant KC as Keycloak
    participant AppB as 出張予約SPA<br/>(Client B)

    User->>AppA: アクセス
    AppA->>KC: /authorize (client_id=expense-spa)
    KC->>User: ログイン画面 + MFA
    User->>KC: 認証成功
    Note over KC: ★ SSOセッション作成<br/>+ KEYCLOAK_SESSION Cookie
    KC->>AppA: トークン（Client A用）

    Note over User,AppB: 出張予約にアクセス

    User->>AppB: アクセス
    AppB->>KC: /authorize (client_id=travel-spa)
    Note over KC: ★ KEYCLOAK_SESSION 有効<br/>→ PW/MFA不要<br/>→ 外部通信なし
    KC->>AppB: トークン（Client B用、即座）
```

**SSOの主体**: Keycloak（Keycloakセッションが鍵。外部通信不要でレスポンスが速い）

#### パターン3: Keycloak + Auth0（フェデレーション）

```mermaid
sequenceDiagram
    participant User as ユーザー
    participant AppA as 経費精算SPA<br/>(Client A)
    participant KC as Keycloak
    participant Auth0 as Auth0
    participant AppB as 出張予約SPA<br/>(Client B)

    User->>AppA: アクセス
    AppA->>KC: /authorize
    KC->>User: 「Login with Auth0」ボタン
    User->>KC: Auth0ボタンクリック
    KC->>Auth0: OIDC /authorize
    Auth0->>User: ログイン画面 + MFA
    User->>Auth0: 認証成功
    Auth0->>KC: code
    KC->>KC: JIT + SSOセッション作成
    KC->>AppA: トークン

    Note over User,AppB: 出張予約にアクセス

    User->>AppB: アクセス
    AppB->>KC: /authorize
    Note over KC: ★ Keycloak SSOセッション有効<br/>→ Auth0に問い合わせない<br/>→ PW/MFA不要
    KC->>AppB: トークン（即座）
```

**SSOの主体**: Keycloak（初回のみAuth0に問い合わせ。2回目以降はKeycloakセッションで完結）

### 2.4 SSOの制御比較

| 制御項目 | Cognito + Auth0 | Keycloak |
|---------|----------------|----------|
| **SSOセッション有効期限** | Auth0設定に依存 | **Realm設定で制御**（Idle: 30分, Max: 10時間等） |
| **アプリ別のSSO除外** | 不可 | **認証フローで条件分岐可能**（特定Clientだけ再認証要求等） |
| **SSOセッション一覧** | 不可（Auth0 Dashboardで限定的） | **Admin Console → Sessions で全セッション可視** |
| **強制ログアウト（全アプリ）** | Auth0 logout + 各Cognitoログアウト（多段） | **Keycloak 1箇所でログアウト + Back-Channel Logout** |
| **Back-Channel Logout** | 非対応 | **対応**（ログアウト時に全Clientに通知） |

### 2.5 ログアウトとSSOの関係

| 操作 | Cognito + Auth0 | Keycloak |
|------|----------------|----------|
| **アプリAからログアウト** | CognitoAのセッション削除。Auth0セッション残存 → **アプリBはまだSSOで入れる** | Keycloak SSOセッション削除 → **アプリBのセッションも無効化（Back-Channel Logout）** |
| **完全ログアウト** | Auth0 logout → Cognito logout → SPA（多段リダイレクト、Phase 2で実装） | **signoutRedirect()のみ**（Keycloak SSOセッション削除で全Client無効化） |
| **ログアウト後の再ログイン** | Auth0セッション破棄済み → **PW必要** | Keycloakセッション破棄済み → **PW必要** |

---

## 3. MFA + SSO の組み合わせ

### 3.1 「MFAは初回だけ、SSOで2つ目以降はスキップ」

| 構成 | 動作 |
|------|------|
| **Cognito + Auth0** | Auth0で初回ログイン時にMFA → Auth0セッション有効 → 2つ目のUser PoolではPW/MFA不要 |
| **Keycloak（ローカル）** | 初回ログイン時にMFA → Keycloak SSOセッション有効 → 2つ目のClientではPW/MFA不要 |
| **Keycloak + Auth0** | Auth0で初回ログイン時にMFA → Keycloak SSOセッション有効 → 2つ目のClientではAuth0にも問い合わせずPW/MFA不要 |

**全構成で「MFAは初回だけ」が実現可能。**

### 3.2 「特定アプリだけMFAを再要求」

例: 経費精算はSSO、承認画面だけMFA再要求

| 構成 | 実現可能？ | 方法 |
|------|:---------:|------|
| Cognito + Auth0 | △ | Auth0 Actions でclient_id判定 → step-up MFA（複雑） |
| **Keycloak** | **✅** | **認証フローで条件分岐**（Client別にMFA要否を設定可能） |

```mermaid
flowchart TB
    subgraph KC_Flow["Keycloak 認証フロー"]
        Start["ログイン要求"]
        Start --> Check["SSOセッション確認"]
        Check -->|"有効"| ClientCheck{"どのClient？"}
        ClientCheck -->|"expense-spa\n(通常)"| Skip["MFAスキップ\n→ トークン発行"]
        ClientCheck -->|"approval-spa\n(承認画面)"| Require["MFA再要求\n→ TOTP入力\n→ トークン発行"]
        Check -->|"無効"| Login["PW + MFA\n→ SSOセッション作成"]
    end

    style Skip fill:#d3f9d8,stroke:#2b8a3e
    style Require fill:#fff0f0,stroke:#cc0000
```

これはKeycloakの**Step-up Authentication**機能で、Cognito単体では実現が難しい。

---

## 4. 総合マトリクス

| 観点 | Cognito | Cognito + Auth0 | Keycloak | Keycloak + Auth0 | 優位 |
|------|:-------:|:--------------:|:--------:|:----------------:|:---:|
| **TOTP MFA** | ✅ | Auth0側 | ✅ | Auth0側 | 同等 |
| **WebAuthn MFA** | **✅（Essentials以上）** | Auth0(有料) | ✅ | Auth0(有料) | **同等**（※1） |
| **MFA条件分岐（Client別）** | △（カスタム実装必要） | △ | **✅（認証フローで設定）** | **✅** | **KC** |
| **MFA DR時の維持** | **❌（別Pool、再登録必要）** | ❌ | **✅（DB同期）** | **✅** | **KC** |
| **同一Pool/Realm内SSO** | ✅ | ✅ | ✅ | ✅ | 同等 |
| **異なるPool/Realm間SSO** | ❌ | ✅（Auth0経由） | ❌ | ✅（Auth0経由） | 同等 |
| **SSOセッション制御** | △ | △（Auth0依存） | **✅（細粒度）** | **✅** | **KC** |
| **Back-Channel Logout** | **❌（2026年時点で未対応）** | ❌ | **✅** | **✅** | **KC** |
| **ログアウトのシンプルさ** | △（多段リダイレクト） | △ | **✅** | ✅ | **KC** |
| **Step-up Authentication** | **△（カスタム実装: APIGW+Lambda+DynamoDB）** | △ | **✅（認証フロー設定のみ）** | **✅** | **KC** |
| **運用負荷** | **✅（マネージド）** | ✅ | △（自前運用） | △ | **Cognito** |
| **可用性** | **✅ SLA 99.9%** | ✅ | △ | △ | **Cognito** |

> ※1: CognitoのWebAuthnは2024年11月に追加。Essentials以上のプランが必要（追加コスト）。Keycloakは標準で対応。

### 結論

| カテゴリ | 優位 | 理由 |
|---------|------|------|
| **MFA機能の豊富さ** | **ほぼ同等** | CognitoもWebAuthn対応済み（2024年11月）。ただし条件分岐・Step-upはKeycloak優位 |
| **MFA DR時の維持** | **Keycloak** | DB同期でMFA設定も引き継がれる。**Cognitoは別User PoolのためMFA再登録が必要** |
| **SSO制御の柔軟性** | **Keycloak** | セッション制御、Back-Channel Logout（Cognito未対応）、条件付きMFA |
| **SSO基本動作** | 同等 | どちらも初回MFA → 以降スキップが可能 |
| **運用負荷・可用性** | **Cognito** | マネージド、SLA保証 |

### Cognito Essentials/Plus プランの考慮

2024年11月以降、CognitoはWebAuthn・Email OTP等の高度なMFA機能を追加したが、**Essentials以上のプランが必要**。

| Cognito プラン | 料金 | MFA |
|---------------|------|-----|
| Lite | $0.015/MAU（フェデレーション） | TOTP, SMS のみ |
| **Essentials** | $0.0150/MAU + 追加 | TOTP, SMS, **Email OTP, WebAuthn** |
| **Plus** | さらに追加 | 上記 + **適応型認証（リスクベースMFA）** |

→ WebAuthn/Step-up等の高度な要件がある場合、Cognitoのプラン・コストも再検討が必要。

---

## 参考

- [Keycloak OTP Authentication](https://www.keycloak.org/docs/latest/server_admin/index.html#otp-policies)
- [Keycloak WebAuthn](https://www.keycloak.org/docs/latest/server_admin/index.html#_webauthn)
- [Keycloak Identity Brokering](https://www.keycloak.org/docs/latest/server_admin/index.html#_identity_broker)
- [Keycloak Step-up Authentication](https://www.keycloak.org/docs/latest/server_admin/index.html#_step-up-flow)
- [Cognito MFA Configuration](https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-settings-mfa.html)
- [Auth0 MFA](https://auth0.com/docs/secure/multi-factor-authentication)
