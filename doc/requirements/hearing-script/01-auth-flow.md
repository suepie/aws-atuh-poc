# B-1: 認証フロー / Grant Type

> 元データ: [../hearing-checklist.md B-1](../hearing-checklist.md#b-1-認証フロー--grant-type-fr-auth-11--proposal-fr-11)  
> 対象: 開発チーム / テックリード  
> 関連: [proposal §FR-1.1](../proposal/fr/01-auth.md)

---

### 【SPA 採用システムの一覧】 (B-101, 🔥)

SPA（Single Page Application）として実装されているシステムをご教示ください。
システム名のリストでお答えいただけますと幸いです。
**目的**: Authorization Code Flow + PKCE 採用範囲の確定、SPA への JWT 配送方式（直接保持 or BFF 経由）の設計判断に必要な情報です。SPA の有無は本基盤の認証フロー設計の中核です。

---

### 【SSR Web Application の有無】 (B-102, 🔥)

Next.js / Spring MVC / Django / Rails 等の Server-Side Rendering Web アプリケーションをご利用、もしくは導入予定でしょうか。
有無 + 対象システム名でお答えいただけますと幸いです。
**目的**: Confidential Client での Authorization Code Flow 適用範囲、session storage の設計、Cookie ベース認証の必要性判断に必要な情報です。

---

### 【バックエンド API のエンドポイント形態（JWT 検証場所の決定軸）】 (B-102-2, 🟡)

> **重要**: 本問は **JWT 検証をどこでするか**（Lambda Authorizer / アプリ側ライブラリ / Service Mesh Sidecar / Cognito Authorizer）を決める軸です。**SSR / SPA / モバイルの選択とは独立した軸**であり、SSR を採用しても本問の答えで Lambda Authorizer の要否が変わります。

バックエンド API への通信経路についてご教示ください。複数該当する場合は **アプリ別のマッピング**（経費精算は ①、決済管理は ② 等）でお答えいただけますと幸いです。

**選択肢**:

- **① AWS API Gateway 経由**（**本基盤 PoC 標準・推奨**）
  - Bearer JWT → **Lambda Authorizer で検証**
  - 本基盤の**マルチイシュア対応**（Cognito + Keycloak 並列受理）が必要な場合は事実上必須
  - 採用シーン: Serverless 構成、複数 IdP / 複数 issuer の JWT を統一処理したい場合

- **② ALB + ECS / EC2 直結**（API Gateway なし）
  - **アプリ側ライブラリで JWT 検証**（Spring Security / Passport.js / python-jose 等）
  - Lambda Authorizer は不要
  - 採用シーン: モノリス的アーキテクチャ、API Gateway 利用コストを避けたい

- **③ Service Mesh**（EKS / ECS + Envoy / Istio Sidecar）
  - **Sidecar（Envoy 等）で JWT 検証**、Service Mesh の AuthorizationPolicy で認可
  - Lambda Authorizer は不要、Service Mesh が代替
  - 採用シーン: マイクロサービス内部通信、mTLS と組み合わせ

- **④ 完全内部完結**（SSR + 内部 API + DB が VPC 内で完結、外部 API 公開なし）
  - **SSR サーバー内で JWT 検証**、外部 API がないため Lambda Authorizer 不要
  - 採用シーン: 古典的 Web アプリ、Cookie + Session Store ベース

- **⑤ Cognito Authorizer**（API Gateway 標準機能、Lambda 不使用）
  - 単一 Cognito User Pool + シンプル検証のみ
  - 採用シーン: マルチイシュア不要、カスタム認可ロジック不要の場合

**目的**: 本基盤の**マルチイシュア要件**（Cognito + Keycloak 並列で JWT 発行）では **Lambda Authorizer が事実上必須** ですが、顧客アプリ側の構成次第で「アプリ側 JWT 検証」「Service Mesh」等の代替も可能です。本問により、JWT 検証実装の責務範囲（基盤側 vs アプリ側）、Cognito Authorizer で十分か Lambda Authorizer 必要かの判断、Service Mesh / Sidecar 採用時の認可設計などが決まります。**本基盤の責務はあくまで JWT 発行までで、検証手段は各アプリ側で選択可能**ですが、推奨は ① API Gateway + Lambda Authorizer です。

---

### 【M2M / バッチ処理の有無】 (B-103, 🔥)

バッチ処理 / 定期 API 連携処理 / システム間連携などの M2M（Machine-to-Machine）認証が必要なケースはございますか。
有無 + 想定件数（同時実行数 / 日次回数）でお答えいただけますと幸いです。
**目的**: Client Credentials Grant の必要性判断、Cognito の M2M トークン 150 RPS Hard Limit への適合性確認、Resource Server / Custom Scope 設計に必要な情報です。

---

### 【Token Exchange（マイクロサービス間ユーザー文脈伝播）】 (B-104, 🔥)

マイクロサービス間呼び出しにおいて、エンドユーザーの文脈（誰の操作か）を伝播する必要はございますか。
具体例: サービス A → サービス B 内部呼び出し時に、B 側でエンドユーザーを識別したい / B 側のログにユーザーを記録したい / サービス別に異なる権限チェックをしたい、等。
**目的**: Token Exchange（RFC 8693、On-Behalf-Of パターン）採用要否の判断。**Yes の場合は Token Exchange 必須となり、Cognito ネイティブ非対応のため Keycloak 必須化**となります。詳細判定フローは [§FR-6.3.4](../proposal/fr/06-authz.md) を参照。

---

### 【Device Code Flow（入力制約デバイス認証）】 (B-105, 🔥)

CLI ツール / IoT デバイス / Smart TV / AI Agent など、キーボード入力が制約されるデバイスの認証は必要でしょうか。
有無でお答えいただけますと幸いです。
**目的**: Device Authorization Grant（RFC 8628）採用要否の判断。**Yes の場合、Cognito ネイティブ非対応のため Lambda + DynamoDB の自前実装か Keycloak 採用が必要**となります。

---

### 【mTLS Client Authentication】 (B-106, 🔥)

FAPI（Financial-grade API）準拠が必要なシステム、もしくは高セキュリティ M2M で証明書ベースの相互認証を必要とするケースはございますか。
有無 + 対象システムでお答えいただけますと幸いです。
**目的**: mTLS Client Authentication（RFC 8705）採用要否の判断。**Yes の場合、Cognito は FAPI 不適合のため Keycloak（OSS or RHBK）必須化**となります。金融・決済系で必須となるケースが多い項目です。

---

### 【ネイティブモバイルアプリの有無】 (B-107, 🟡)

iOS / Android アプリを提供されている、もしくは予定はございますか。
有無 + アプリ件数でお答えいただけますと幸いです。
**目的**: モバイル向け Authorization Code Flow + PKCE 設計、Refresh Token の取り扱い（モバイル端末保存）、Custom URL Scheme 対応の判断に必要な情報です。

---

### 【SPA 認証方式（BFF vs PKCE 直接）】 (B-108, 🟡)

SPA の認証方式について、ご希望の設計をご教示ください。
- BFF（Backend-for-Frontend）パターン: トークンをサーバー側で保持、SPA は HttpOnly Cookie のみ
- PKCE 直接: SPA がトークンを直接保持
- 段階移行: 既存は PKCE、新規は BFF

業界動向として、IETF / Curity / Duende 等が 2025 年から **BFF を gold standard** として推奨しています。
**目的**: XSS リスクへの耐性、トークン保護レベル、実装工数の見積に必要な情報です。BFF 採用時は SPA 側のセッションハイジャック耐性が大幅に向上します（ただし顧客 IdP 側のセッションハイジャックには別軸の対策が必要）。

---

### 【DPoP（Sender-Constrained Tokens）の採用要否】 (B-109, 🟡)

mTLS の代替として **DPoP（RFC 9449）** の採用は必要でしょうか。
FAPI 2.0 準拠 / Open Banking / 高セキュリティ API でトークン盗難対策が必要な場合に該当します。
有無でお答えいただけますと幸いです。
**目的**: DPoP（Demonstration of Proof-of-Possession）採用要否の判断。**Yes の場合、Cognito 標準非対応のため Keycloak 必須化**となります。mTLS と比較して証明書管理が不要で実装容易なため、近年 FAPI 2.0 で採用が進んでいる方式です。
