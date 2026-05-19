# B-2: IdP 接続種別

> 元データ: [../hearing-checklist.md B-2](../hearing-checklist.md#b-2-idp-接続種別-fr-fed-21--proposal-fr-21)  
> 対象: 開発チーム / テックリード  
> 関連: [proposal §FR-2.1](../proposal/fr/02-federation.md)

---

### 【Microsoft Entra ID への実接続】 (B-201, 🔥)

顧客企業の中で Microsoft Entra ID への接続が必要なケースはございますか。
有無 + 想定顧客名（差し支えない範囲で）でお答えいただけますと幸いです。
（本基盤の PoC では Auth0 で代替検証を実施済みです）
**目的**: 主要 IdP として最も多い Entra ID への対応優先度、OIDC / SAML どちらでの接続を想定するかの判断、属性マッピング（`tid` / `oid` 等）の設計準備に必要な情報です。

---

### 【SAML IdP として発行する必要性】 (B-202, 🔥)

既存の SAML SP（業務システム）と連携し、本基盤を **SAML IdP（発行側）** として動作させる必要はございますか。
有無 + 対象システムでお答えいただけますと幸いです。
**目的**: SAML IdP モード対応の判断。**Yes の場合、Cognito はネイティブ非対応のため Keycloak 必須化**となります。レガシー SaaS や既存オンプレシステムが SAML SP として動作している場合に必要となります。

---

### 【LDAP / AD 直接連携の必要性】 (B-203, 🔥)

ADFS や Entra ID を経由せず、**オンプレ Active Directory / LDAP に直接接続**する必要のある顧客はございますか。
有無 + 対象顧客でお答えいただけますと幸いです。
**目的**: LDAP / AD 直接連携対応の判断。**Yes の場合、Cognito はネイティブ非対応のため Keycloak の User Federation 機能必須**となります。Cognito では AD Connector + ADFS + SAML の 3 段階経由が必要となり、構成が複雑化します。

---

### 【Okta への接続】 (B-204, 🟡)

Okta を IdP とする顧客との接続は必要でしょうか。
有無でお答えいただけますと幸いです。
**目的**: Okta 接続実績の確認、OIDC / SAML どちらでの接続か（Okta はどちらもサポート）、属性マッピング（`org_id` 等）の準備に必要な情報です。

---

### 【Google Workspace への接続】 (B-205, 🟡)

Google Workspace を IdP とする顧客との接続は必要でしょうか。
有無でお答えいただけますと幸いです。
**目的**: Google Workspace（OpenID Connect 標準）接続の必要性判断、`hd`（hosted domain）クレームによるテナント識別の準備に必要な情報です。

---

### 【SAML SP として受け入れる必要性】 (B-206, 🟡)

顧客 IdP が SAML 専用（ADFS / HENNGE One / 自社 SAML 等）の場合、本基盤を **SAML SP（受信側）** として動作させる必要はございますか。
有無 + 対象 IdP 名でお答えいただけますと幸いです。
**目的**: SAML 2.0 SP モード対応の必要性判断（Cognito / Keycloak 両者対応）、NameID フォーマット（emailAddress / persistent / transient）の確認、属性マッピング設計の準備に必要な情報です。

---

### 【独自プロトコル IdP の有無】 (B-207, 🟡)

OIDC / SAML 以外の独自プロトコルを使う IdP との接続が必要なケースはございますか。
有無 + プロトコル詳細でお答えいただけますと幸いです。
**目的**: 標準プロトコル外の IdP との接続可否判断。独自プロトコルは本基盤との直接接続不可となるため、**接続不可とするか、顧客側でラッパー（OIDC/SAML 化）を用意していただくか**の方針確定が必要です。

---

### 【Custom Domain 利用】 (B-208, 🟡)

認証エンドポイントの URL に、顧客指定のドメイン（`auth.example.com` 等）を利用されますか。
利用する場合は想定ドメイン、利用しない場合（プラットフォーム標準ドメイン）はその旨でお答えいただけますと幸いです。
**目的**: Cognito Custom Domain 機能（ACM 証明書 + Route 53）、Keycloak の Hostname 設定の利用判断、CloudFront 統合の必要性確認に必要な情報です。
