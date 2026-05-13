# 機能要件一覧（functional-requirements.md）

> 最終更新: 2026-05-13（Cognito 2024-11 仕様変更反映 / Phase 9 反映 / 実装実態と整合）
> 対象: 共有認証基盤（Cognito / Keycloak 比較）
> 関連: [auth-patterns.md](../common/auth-patterns.md)、[ADR-014](../adr/014-auth-patterns-scope.md)

---

## 凡例

### 優先度（**共通認証基盤としての位置付け**）

本基盤は複数顧客が利用する共有プラットフォームのため、以下は **基盤として備えるべき capability** の優先度。「全顧客が必ず使う」ではなく「**基盤側で対応できているか**」を意味する:

- **Must**: 基盤として **常時提供必須**（標準装備、個別顧客の要否に関わらず搭載）
- **Should**: 基盤として **オプション提供**（顧客ごとに on/off できる、有効化されればすぐ使える）
- **Could**: **顧客固有要件**として個別対応（要望時に拡張する）
- **Won't**: 採用しない
- **TBD**: 要件定義で確定（顧客ヒアリング結果次第で Must/Should/Could に分類）

### 状態
- ✅ **確定**: PoC 検証済 or 業界標準で迷いなし
- 🟡 **デフォルト**: 推奨値あり、ヒアリングで承認が必要
- 🔴 **TBD**: ヒアリングで顧客から確認必須

### Cognito / Keycloak 列の表記
- ✅ ネイティブ対応
- ⚠ 制約あり / 追加実装必要
- ❌ 非対応

---

## 1. FR-AUTH（認証方式）

FR-AUTH は性質の異なる 2 つの観点を含む。

- **§1.1 認証フロー / Grant Type**（FR-AUTH-001〜008）— OIDC / OAuth 2.0 標準フロー群。**Broker（Cognito / Keycloak）が OIDC 標準実装である**ことから自動的に提供される機能（ROPC を除く 001〜007 は Broker パターンとしてカバー対象）。クライアント種別（SPA / SSR / Mobile / M2M）に応じて使い分ける。
- **§1.2 パスワード・ローカルユーザー管理**（FR-AUTH-009〜014）— Broker が**ローカル IdP モード**で動作するときの認証情報管理ポリシー。フェデレーションユーザーには適用されず、外部 IdP（Entra ID / Okta 等）側の責務となる（[ADR-009](../adr/009-mfa-responsibility-by-idp.md)）。

### 1.1 認証フロー / Grant Type

| ID | 要件 | 優先度 | Cognito | Keycloak | PoC | 状態 |
|----|------|:----:|:------:|:------:|:---:|:---:|
| FR-AUTH-001 | ID/PW 認証（ローカルユーザー） | Must | ✅ Hosted UI | ✅ Realm Login Page | ✅ | ✅ |
| FR-AUTH-002 | Authorization Code + PKCE（SPA / モバイル） | Must | ✅ App Client（Public） | ✅ Public Client | ✅ Phase 1,4,5,6,7 | ✅ |
| FR-AUTH-003 | Authorization Code + client_secret（SSR） | Must | ✅ App Client（Confidential） | ✅ Confidential Client | ❌ 未検証 | 🟡 |
| FR-AUTH-004 | Client Credentials（M2M） | Must | ⚠ Resource Server + custom scope 必要 | ✅ Service Account | ❌ 未検証 | 🟡 |
| FR-AUTH-005 | Token Exchange（RFC 8693） | TBD | ❌ 非対応 | ✅ ネイティブ対応 | ❌ | 🔴 |
| FR-AUTH-006 | Device Code Flow | TBD | ❌ 非対応 | ✅ ネイティブ対応 | ❌ | 🔴 |
| FR-AUTH-007 | mTLS Client Authentication（RFC 8705） | Could | ❌ 非対応 | ✅ FAPI Profile | ❌ | 🔴 |
| FR-AUTH-008 | ROPC（Password Grant） | Won't | ✅（非推奨） | ✅（非推奨） | — | ✅ 不採用 |

**Broker パターンとの関係**: 001〜003（Must）はいずれも OIDC/OAuth 標準フロー（RFC 6749 / 7636）であり、Broker が OIDC OP として実装されている限り構造的に提供可能。004 は実装上の設定差はあるが Broker パターンとして対応可能。005〜007 は実装依存（Cognito 非対応・Keycloak 対応）であり、要否次第でプラットフォーム選定に直結する（§9.1 参照）。

**詳細**: [auth-patterns.md §2.1〜2.9](../common/auth-patterns.md)

### 1.2 パスワード・ローカルユーザー管理

ローカル IdP モード（Broker 自体にユーザー DB を持つ運用）でのみ適用。フェデレーションユーザーは外部 IdP のポリシーに従う。

> **Cognito ティア依存の機能**: FR-AUTH-010 / FR-AUTH-011 は Cognito のティア選定（Lite / Essentials / Plus）に依存する。詳細マトリクスは [ADR-016](../adr/016-cognito-feature-tier-selection.md) 参照。
> なお Cognito Essentials ティアはフェデレーション課金が Lite と同額（$0.015/MAU）のため、FR-AUTH-010 / FR-MFA-002 を採用しても**フェデレーション利用なら追加コストは発生しない**。

| ID | 要件 | 優先度 | Cognito | Keycloak | PoC | 状態 |
|----|------|:----:|:------:|:------:|:---:|:---:|
| FR-AUTH-009 | パスワードポリシー（最小長・複雑性） | Must | ✅ User Pool 設定 | ✅ Realm Policy | ✅ Cognito 明示設定済（min 8 + 大小数字必須） | ✅ |
| FR-AUTH-010 | パスワード履歴（N 個と一致禁止）| Should | ⚠ **Essentials+ ティア必要**（`PasswordHistorySize` 0〜24、Terraform 未対応 [#39016](https://github.com/hashicorp/terraform-provider-aws/issues/39016)）| ✅ N 履歴設定可 | ❌ | 🔴 |
| FR-AUTH-011 | アカウントロック（連続失敗） | Must | **2 段階**: ⚠ 全ティア標準ブルートフォース保護（パラメータ調整不可）/ ✅ **Plus ティア**で詳細設定可（リスクベース適応認証）| ✅ Realm 設定（`failureFactor` 等細かく制御可） | ✅ Phase 7（realm-export.json `bruteForceProtected: true, failureFactor: 5`） | 🟡 |
| FR-AUTH-012 | パスワード有効期限 | Should | ✅ 設定可 | ✅ 設定可 | ❌ | 🟡 |
| FR-AUTH-013 | セルフサービスパスワードリセット | Must | ✅ Forgot Password | ✅ Forgot Password | ❌ | 🟡 |
| FR-AUTH-014 | 初期パスワード強制変更 | Should | ✅ Required Action | ✅ Required Action | ❌ | 🟡 |

**ID 体系について**: 性質はフローと異なるが、ADR-006 / poc-summary-evaluation.md / hearing-checklist.md / non-functional-requirements.md から既に番号参照されているため、ID は `FR-AUTH-NNN` のまま維持する（サブセクション分けのみ）。

---

## 2. FR-FED（フェデレーション / 外部 IdP 連携）

FR-FED は性質の異なる 3 つの観点を含む。

- **§2.1 IdP 接続種別**（FR-FED-001〜007, 014）— どのプロトコル・どの製品の IdP を受け入れられるか
- **§2.2 フェデレーションユーザー処理**（FR-FED-008, 009, 012）— 外部 IdP から渡されたユーザー情報を基盤側でどう扱うか
- **§2.3 マルチテナント運用**（FR-FED-010, 011, 013）— 複数顧客 IdP を並行運用するための機能

### 2.1 IdP 接続種別

Broker パターンの「Spoke 側」。受け入れ可能な外部 IdP プロトコル / 製品の範囲を規定する。

| ID | 要件 | 優先度 | Cognito | Keycloak | PoC | 状態 |
|----|------|:----:|:------:|:------:|:---:|:---:|
| FR-FED-001 | Auth0 OIDC IdP 連携 | — | ✅ | ✅ | ✅ Phase 2,7 | ✅ |
| FR-FED-002 | Entra ID（Azure AD）OIDC 連携 | Must | ✅ | ✅ | ❌ Auth0 で代替 | 🔴 |
| FR-FED-003 | Okta OIDC 連携 | Should | ✅ | ✅ | ❌ | 🔴 |
| FR-FED-004 | Google Workspace OIDC 連携 | Could | ✅ | ✅ | ❌ | 🔴 |
| FR-FED-005 | SAML 2.0 IdP として受け入れ（SP モード） | Should | ✅ | ✅ | ❌ | 🔴 |
| FR-FED-006 | SAML 2.0 IdP として発行（IdP モード） | TBD | ❌ 非対応 | ✅ | ❌ | 🔴 |
| FR-FED-007 | LDAP / AD 直接連携 | TBD | ❌ 非対応 | ✅ User Federation | ❌ | 🔴 |
| FR-FED-014 | Custom Domain での federation | Should | ✅ Hosted UI Custom Domain | ✅ Hostname 設定 | ❌ | 🟡 |

### 2.2 フェデレーションユーザー処理

外部 IdP から認証を受けたユーザーを基盤側で取り扱うときの処理。Broker パターンの「属性変換層」の中核。

| ID | 要件 | 優先度 | Cognito | Keycloak | PoC | 状態 |
|----|------|:----:|:------:|:------:|:---:|:---:|
| FR-FED-008 | JIT プロビジョニング | Must | ✅ 自動 | ✅ First Login Flow | ✅ Phase 2 | ✅ |
| FR-FED-009 | 属性マッピング / クレーム変換 | Must | ✅ attribute_mapping | ✅ IdP Mapper | ✅ Phase 8 | ✅ |
| FR-FED-012 | フェデレーション時の MFA 重複回避 | Must | ⚠ 個別実装 | ✅ Conditional OTP | ✅ Phase 7（Keycloak のみ） | 🟡 |

> **クロスリファレンス**: FR-FED-012 は MFA ポリシーの一種でもある（§3.2 関連）。フェデユーザーの MFA 責務は外部 IdP 側に寄せる方針（[ADR-009](../adr/009-mfa-responsibility-by-idp.md)）。

### 2.3 マルチテナント運用

複数顧客 IdP の並行運用・追加・選択 UX。Broker パターンが本来狙う「顧客追加で各システム変更不要」を支える機能群。

| ID | 要件 | 優先度 | Cognito | Keycloak | PoC | 状態 |
|----|------|:----:|:------:|:------:|:---:|:---:|
| FR-FED-010 | 複数 IdP 並行運用（マルチテナント） | Must | ✅ User Pool に複数登録 | ✅ Realm に複数登録 | ✅ Phase 4,5 | ✅ |
| FR-FED-011 | 顧客追加時のオンボーディングフロー | Must | ✅ 設計可（手動 / IaC） | ✅ 設計可（手動 / IaC） | ⚠ 概念設計のみ | 🟡 |
| FR-FED-013 | ログイン画面で IdP 選択 UX | Should | ⚠ `identity_provider` パラメータ必須 | ✅ ボタン自動表示 | ✅ Phase 7 | 🟡 |

**詳細**: [auth-patterns.md §2.0](../common/auth-patterns.md)、[identity-broker-multi-idp.md](../common/identity-broker-multi-idp.md)

---

## 3. FR-MFA（多要素認証）

FR-MFA は性質の異なる 2 つの観点を含む。

- **§3.1 MFA 要素**（FR-MFA-001〜005）— どんな認証手段（TOTP / WebAuthn / SMS / Email / バックアップ）を提供できるか
- **§3.2 MFA 適用ポリシー**（FR-MFA-006〜009）— いつ・誰に・どんな条件で MFA を強制するか

### 3.1 MFA 要素

| ID | 要件 | 優先度 | Cognito | Keycloak | PoC | 状態 |
|----|------|:----:|:------:|:------:|:---:|:---:|
| FR-MFA-001 | TOTP（Google Authenticator 等） | Must | ✅ | ✅ | ✅ Phase 1,7 | ✅ |
| FR-MFA-002 | WebAuthn / FIDO2（Passkeys） | Should | ✅ ネイティブ対応（**Essentials+ ティア**、2024-11〜）— フェデレーション利用なら Lite と単価同額のため追加コストなし | ✅ | ❌ 未検証 | 🟡 |
| FR-MFA-003 | SMS OTP | Could | ✅（追加課金） | ⚠ プラグイン | ❌ | 🔴 |
| FR-MFA-004 | メール OTP | Could | ✅ | ✅ | ❌ | 🔴 |
| FR-MFA-005 | バックアップコード | Should | ❌ | ✅ | ❌ | 🟡 |

### 3.2 MFA 適用ポリシー

| ID | 要件 | 優先度 | Cognito | Keycloak | PoC | 状態 |
|----|------|:----:|:------:|:------:|:---:|:---:|
| FR-MFA-006 | 条件付き MFA（IP / リスクベース） | Should | ⚠ Plus ティア（$0.02/MAU 追加）必要（リスクベース適応認証） | ✅ Conditional Flow | ✅ Phase 7（Keycloak） | 🟡 |
| FR-MFA-007 | MFA 強制 / 任意の切替（ロール単位） | Must | ⚠ User 単位のみ | ✅ Flow 単位制御可 | ✅ Phase 7 | 🟡 |
| FR-MFA-008 | 端末記憶（Trusted Device） | Could | ✅ Remember Device | ⚠ 設定要 | ❌ | 🔴 |
| FR-MFA-009 | 管理者の MFA 強制 | Must | ✅ | ✅ | ❌ | 🟡 |

> **クロスリファレンス**: フェデレーションユーザーへの MFA 適用は外部 IdP 側責務（[ADR-009](../adr/009-mfa-responsibility-by-idp.md)）。FR-FED-012（MFA 重複回避）と一緒に検討する。

**詳細**: [auth-patterns.md §2.0.2](../common/auth-patterns.md)、[ADR-009](../adr/009-mfa-responsibility-by-idp.md)

---

## 4. FR-SSO / FR-LOGOUT（シングルサインオン・ログアウト）

FR-SSO は性質の異なる 3 つの観点を含む。

- **§4.1 SSO**（FR-SSO-001, 002）— サインオン側。一度認証したら別 Client・別 IdP でもログイン不要にする
- **§4.2 ログアウト**（FR-SSO-003〜007）— サインアウト側。どのレベル（アプリ / IdP / フェデ連動 / Channel Logout）まで破棄するか
- **§4.3 セッション管理**（FR-SSO-008〜010）— セッション・トークンの有効期間と強制無効化

### 4.1 SSO

| ID | 要件 | 優先度 | Cognito | Keycloak | PoC | 状態 |
|----|------|:----:|:------:|:------:|:---:|:---:|
| FR-SSO-001 | 同一 IdP 内の複数 Client 間 SSO | Must | ✅ User Pool 内 | ✅ Realm 内 | ✅ Phase 1,7 | ✅ |
| FR-SSO-002 | Auth0/Entra 経由のクロス IdP SSO | Must | ✅ | ✅ | ✅ Phase 2,7 | ✅ |

### 4.2 ログアウト

ログアウトは「どこまで破棄するか」のレイヤーが複数ある。基盤として全レイヤーへの対応有無を明示する。

| ID | 要件 | 優先度 | Cognito | Keycloak | PoC | 状態 |
|----|------|:----:|:------:|:------:|:---:|:---:|
| FR-SSO-003 | ローカルログアウト（アプリ Cookie 削除のみ） | Must | ✅ | ✅ | ✅ | ✅ |
| FR-SSO-004 | IdP セッション破棄（OIDC RP-Initiated Logout） | Must | ✅ `/logout` | ✅ `/logout?id_token_hint=...` | ✅ | ✅ |
| FR-SSO-005 | フェデレーション IdP セッション破棄（連動ログアウト） | Should | ⚠ URL エンコード制約あり | ✅ | ✅ Phase 2,5 | 🟡 |
| FR-SSO-006 | Front-Channel Logout | Should | ✅ | ✅ | ❌ | 🟡 |
| FR-SSO-007 | Back-Channel Logout（RFC 8606） | Should | ❌ 非対応 | ✅ ネイティブ対応 | ✅ Phase 7（Keycloak） | 🟡 |

### 4.3 セッション管理

| ID | 要件 | 優先度 | Cognito | Keycloak | PoC | 状態 |
|----|------|:----:|:------:|:------:|:---:|:---:|
| FR-SSO-008 | セッションタイムアウト設定 | Must | ✅ | ✅ | ⚠ デフォルトのみ | 🟡 |
| FR-SSO-009 | アクセストークン強制無効化（Revocation） | Should | ⚠ Refresh Token のみ revoke 可 | ✅ Token Revocation | ❌ | 🔴 |
| FR-SSO-010 | 強制全セッション破棄（管理者操作） | Must | ✅ AdminUserGlobalSignOut | ✅ Admin Console | ❌ | 🟡 |

**詳細**: [auth-patterns.md §2.1, §2.2](../common/auth-patterns.md)、[reference/session-management-deep-dive.md](../reference/session-management-deep-dive.md)

---

## 5. FR-AUTHZ（認可）

FR-AUTHZ は性質の異なる 2 つの観点を含む。

- **§5.1 クレームベース基本認可**（FR-AUTHZ-001〜008）— JWT クレームを用いた RBAC・テナント分離・scope 認可。本基盤の中核
- **§5.2 細粒度認可**（FR-AUTHZ-009, 010）— リソースレベル / 動的属性ベース。要件次第で適用

### 5.1 クレームベース基本認可

| ID | 要件 | 優先度 | Cognito | Keycloak | PoC | 状態 |
|----|------|:----:|:------:|:------:|:---:|:---:|
| FR-AUTHZ-001 | JWT クレームベース認可 | Must | ✅ | ✅ | ✅ Phase 3,8,9 | ✅ |
| FR-AUTHZ-002 | tenant_id によるテナント分離 | Must | ✅ Pre Token Lambda | ✅ Protocol Mapper | ✅ Phase 8（Cognito）/ Phase 9（Keycloak）※DR Cognito は Pre Token Lambda 未設定 | ✅ |
| FR-AUTHZ-003 | roles クレームによるロール認可 | Must | ✅ Pre Token Lambda | ✅ Protocol Mapper（Realm Role） | ✅ Phase 8（Cognito）/ Phase 9（Keycloak） | ✅ |
| FR-AUTHZ-004 | ロール階層（継承） | Should | ⚠ アプリ側実装 | ✅ Composite Role | ✅ Phase 8（アプリ側） | 🟡 |
| FR-AUTHZ-005 | scope ベース認可（M2M） | Must | ✅ Resource Server scope | ✅ Client Scope | ❌ | 🟡 |
| FR-AUTHZ-006 | カスタムクレーム注入（任意属性） | Must | ✅ Pre Token Generation Lambda V2 | ✅ Protocol Mapper（宣言的） | ✅ Phase 8（Cognito）/ Phase 9（Keycloak） | ✅ |
| FR-AUTHZ-007 | API Gateway 認可統合（Lambda Authorizer） | Must | ✅ | ✅ | ✅ Phase 3 / VPC 版 Phase 9 | ✅ |
| FR-AUTHZ-008 | マルチイシュア対応（複数 User Pool / Realm） | Must | ✅ | ✅ | ✅ Phase 4,5,9（4 イシュア: central/local/dr/keycloak） | ✅ |

### 5.2 細粒度認可

| ID | 要件 | 優先度 | Cognito | Keycloak | PoC | 状態 |
|----|------|:----:|:------:|:------:|:---:|:---:|
| FR-AUTHZ-009 | リソースレベル認可（UMA 2.0 / Fine-grained） | Could | ❌ 非対応 | ✅ Authorization Services | ❌ | 🔴 |
| FR-AUTHZ-010 | 動的属性ベース認可（ABAC） | Could | ⚠ Lambda 側実装 | ✅ Policy Enforcer | ❌ | 🔴 |

**詳細**: [authz-architecture-design.md](../common/authz-architecture-design.md)、[claim-mapping-authz-scenario.md](../common/claim-mapping-authz-scenario.md)

---

## 6. FR-USER（ユーザー管理）

FR-USER は性質の異なる 4 つの観点を含む。

- **§6.1 ユーザー CRUD**（FR-USER-001, 005, 006, 011）— 基盤がユーザー DB を持つ場合の基本操作
- **§6.2 属性・ロール**（FR-USER-002, 007, 008）— ユーザーに紐づく属性・グループ・ロール
- **§6.3 セルフサービス**（FR-USER-004, 012）— ユーザー自身による操作
- **§6.4 プロビジョニング**（FR-USER-003, 009, 010）— 管理者・外部システムからの大量・自動投入

### 6.1 ユーザー CRUD

| ID | 要件 | 優先度 | Cognito | Keycloak | PoC | 状態 |
|----|------|:----:|:------:|:------:|:---:|:---:|
| FR-USER-001 | ユーザー作成 / 更新 / 削除（CRUD） | Must | ✅ Admin API | ✅ Admin REST API | ✅ | ✅ |
| FR-USER-005 | ユーザー検索・一覧 | Must | ✅ ListUsers API | ✅ Search API | ✅ | ✅ |
| FR-USER-006 | ユーザー有効化 / 無効化（suspend） | Must | ✅ AdminDisableUser | ✅ Enable/Disable | ✅ | ✅ |
| FR-USER-011 | ユーザー削除時の関連データ削除（GDPR 等） | Should | ✅ AdminDeleteUser | ✅ Cascade Delete | ❌ | 🟡 |

### 6.2 属性・ロール

| ID | 要件 | 優先度 | Cognito | Keycloak | PoC | 状態 |
|----|------|:----:|:------:|:------:|:---:|:---:|
| FR-USER-002 | カスタム属性（任意フィールド） | Must | ✅ Custom Attributes | ✅ User Attributes（無制限） | ✅ Phase 8 | ✅ |
| FR-USER-007 | ユーザーグループ管理 | Should | ✅ Cognito Groups | ✅ Realm Groups | ⚠ 概念のみ | 🟡 |
| FR-USER-008 | ロール割り当て | Must | ⚠ Custom Attribute or Group | ✅ Realm Role Assignment | ✅ Phase 8 | 🟡 |

> **クロスリファレンス**: ロールは [§5 FR-AUTHZ](#5-fr-authz認可) の認可ロジックで参照される。

### 6.3 セルフサービス

| ID | 要件 | 優先度 | Cognito | Keycloak | PoC | 状態 |
|----|------|:----:|:------:|:------:|:---:|:---:|
| FR-USER-004 | セルフサービスプロフィール編集 | Must | ⚠ アプリ側実装 | ✅ Account Console | ❌ | 🟡 |
| FR-USER-012 | ユーザー作成時の招待メール | Should | ✅ AdminCreateUser invitation | ✅ Email Verification | ⚠ デフォルト | 🟡 |

> **クロスリファレンス**: パスワード関連のセルフサービス（FR-AUTH-013 セルフサービスパスワードリセット）は [§1.2](#12-パスワードローカルユーザー管理) を参照。

### 6.4 プロビジョニング

| ID | 要件 | 優先度 | Cognito | Keycloak | PoC | 状態 |
|----|------|:----:|:------:|:------:|:---:|:---:|
| FR-USER-003 | SCIM 2.0 プロビジョニング | TBD | ⚠ 非ネイティブ（自前実装要） | ✅ プラグイン対応 | ❌ | 🔴 |
| FR-USER-009 | バルクインポート（CSV / JSON） | Should | ✅ ImportUsers | ✅ Realm Import | ❌ | 🟡 |
| FR-USER-010 | ユーザーパスワード強制リセット | Must | ✅ AdminSetUserPassword | ✅ Admin Console | ✅ | ✅ |

---

## 7. FR-ADMIN（管理機能）

FR-ADMIN は性質の異なる 3 つの観点を含む。

- **§7.1 基盤設定管理**（FR-ADMIN-001〜005, 009）— 基盤管理者が基盤そのものを設定する
- **§7.2 監査・可視性**（FR-ADMIN-007, 008）— 何が起きたかを追跡
- **§7.3 権限委譲・カスタマイズ**（FR-ADMIN-006, 010, 011, 012）— 管理者権限の細分化・顧客への委譲・見た目のカスタマイズ

### 7.1 基盤設定管理

| ID | 要件 | 優先度 | Cognito | Keycloak | PoC | 状態 |
|----|------|:----:|:------:|:------:|:---:|:---:|
| FR-ADMIN-001 | 管理コンソール UI | Must | ✅ AWS Console | ✅ Keycloak Admin Console | ✅ Phase 6 | ✅ |
| FR-ADMIN-002 | テナント追加・削除 | Must | ✅ User Pool 単位 / Group | ✅ Realm 単位 / IdP 単位 | ⚠ 設計のみ | 🟡 |
| FR-ADMIN-003 | IdP 追加・削除・更新 | Must | ✅ Console / Terraform | ✅ Console / Terraform | ✅ Phase 2,5,7 | ✅ |
| FR-ADMIN-004 | クライアント（App）管理 | Must | ✅ App Client | ✅ Client | ✅ | ✅ |
| FR-ADMIN-005 | ロール定義管理 | Must | ⚠ Custom Attr / Group | ✅ Realm Role / Client Role | ✅ Phase 8 | 🟡 |
| FR-ADMIN-009 | テナント別設定の分離 | Must | ✅ User Pool 分離 | ✅ Realm 分離 | ✅ Phase 4,5 | ✅ |

### 7.2 監査・可視性

| ID | 要件 | 優先度 | Cognito | Keycloak | PoC | 状態 |
|----|------|:----:|:------:|:------:|:---:|:---:|
| FR-ADMIN-007 | 監査ログ閲覧 | Must | ✅ CloudTrail | ✅ Event Listener | ⚠ 設定要 | 🟡 |
| FR-ADMIN-008 | 設定変更履歴 | Should | ✅ CloudTrail | ✅ Admin Events | ❌ | 🟡 |

> **クロスリファレンス**: 監査ログの外部出力・SIEM 連携・保存期間は [§8.2](#82-ログ監視) および NFR-OPS-003 / NFR-COMP-007 を参照。

### 7.3 権限委譲・カスタマイズ

| ID | 要件 | 優先度 | Cognito | Keycloak | PoC | 状態 |
|----|------|:----:|:------:|:------:|:---:|:---:|
| FR-ADMIN-006 | パーミッション管理（細粒度） | Could | ⚠ アプリ側 | ✅ Authorization Services | ❌ | 🔴 |
| FR-ADMIN-010 | 管理者ロール（RBAC for Admin） | Must | ✅ IAM | ✅ Realm Admin Roles | ⚠ デフォルト | 🟡 |
| FR-ADMIN-011 | テナント管理者の委譲（顧客の自社運用） | Should | ⚠ AWS IAM 必要 | ✅ Realm-level Admin | ❌ | 🔴 |
| FR-ADMIN-012 | カスタマイズ可能なログイン UI | Should | ⚠ CSS / ロゴのみ | ✅ Theme（フルカスタム） | ❌ | 🟡 |

---

## 8. FR-INT（外部システム統合）

FR-INT は性質の異なる 3 つの観点を含む。

- **§8.1 プロトコル準拠**（FR-INT-001〜004, 007）— 標準 OIDC/OAuth/SAML/JWKS による連携可能性
- **§8.2 ログ・監視**（FR-INT-008, 009）— 監査ログを外部システムへ流す
- **§8.3 API・IaC・Webhook**（FR-INT-005, 006, 010）— 基盤の構成・運用を自動化する手段

### 8.1 プロトコル準拠

| ID | 要件 | 優先度 | Cognito | Keycloak | PoC | 状態 |
|----|------|:----:|:------:|:------:|:---:|:---:|
| FR-INT-001 | OIDC 1.0 / OAuth 2.0 標準準拠 | Must | ✅ | ✅ | ✅ | ✅ |
| FR-INT-002 | OIDC Discovery（`.well-known`） | Must | ✅ | ✅ | ✅ | ✅ |
| FR-INT-003 | JWKS 公開エンドポイント | Must | ✅ AWS 公開 | ✅ ALB 経由 | ✅ Phase 3 | ✅ |
| FR-INT-004 | SAML 2.0 メタデータ | Should | ✅ | ✅ | ❌ | 🟡 |
| FR-INT-007 | API Gateway / Lambda Authorizer 統合 | Must | ✅ | ✅ | ✅ Phase 3 | ✅ |

### 8.2 ログ・監視

| ID | 要件 | 優先度 | Cognito | Keycloak | PoC | 状態 |
|----|------|:----:|:------:|:------:|:---:|:---:|
| FR-INT-008 | 監査ログ外部出力（CloudWatch / S3 / Kinesis） | Must | ✅ CloudTrail / CloudWatch | ⚠ Event Listener 自前実装 | ⚠ デフォルト | 🟡 |
| FR-INT-009 | 監査ログ SIEM 連携（Splunk / Datadog） | Could | ✅ | ⚠ ログ転送設計要 | ❌ | 🔴 |

> **クロスリファレンス**: ログ保存期間・コンプライアンス要件は NFR-OPS-003 / NFR-COMP-007 を参照。

### 8.3 API・IaC・Webhook

| ID | 要件 | 優先度 | Cognito | Keycloak | PoC | 状態 |
|----|------|:----:|:------:|:------:|:---:|:---:|
| FR-INT-005 | Webhook イベント通知（user.created 等） | Should | ⚠ Pre Token / Post Conf Lambda | ✅ Event Listener | ❌ | 🔴 |
| FR-INT-006 | 管理 REST API | Must | ✅ AWS SDK | ✅ Admin REST API | ⚠ | 🟡 |
| FR-INT-010 | Terraform / IaC 管理 | Must | ✅ | ⚠ Realm 部分は別管理 | ✅ | ✅ |

---

## 9. 必須要件サマリー（要件定義での優先確認）

### 9.1 「Cognito 不可・Keycloak 必須」要因

以下の要件のいずれかが Must 確定すると **Keycloak 必須** となる（[ADR-014](../adr/014-auth-patterns-scope.md)）:

| 要件 ID | 内容 |
|--------|------|
| FR-AUTH-005 | Token Exchange（RFC 8693） |
| FR-AUTH-006 | Device Code Flow |
| FR-AUTH-007 | mTLS（RFC 8705） |
| FR-FED-006 | SAML IdP として発行 |
| FR-FED-007 | LDAP 直接連携 |
| FR-AUTHZ-009 | UMA 2.0 / Fine-grained |
| FR-SSO-007 | Back-Channel Logout |

※ **FR-MFA-002 WebAuthn / FIDO2 は Cognito も対応**（2024-11〜、Essentials+ ティア）。「Keycloak 必須要因」ではない。

### 9.2 Cognito ティア選定への影響要因

以下の要件が Must になると Cognito のティア選定に影響する（[ADR-016](../adr/016-cognito-feature-tier-selection.md) 参照）:

| 要件 ID | 内容 | 必要ティア |
|--------|------|----------|
| FR-AUTH-010 | パスワード履歴 | **Essentials+**（フェデレーション利用なら追加コストなし）|
| FR-MFA-002 | WebAuthn / Passkeys | **Essentials+**（同上）|
| FR-AUTH-011 | 設定可能なアカウントロック（連続失敗閾値・ロック時間）| **Plus**（+$0.02/MAU）|
| FR-MFA-006 | リスクベース MFA（適応認証）| **Plus**（同上）|
| NFR-SEC-011 | 侵害クレデンシャル検出 | **Plus**（同上）|

→ Plus ティア採用時は損益分岐 MAU が **175,000 → 75,000** に変動（[ADR-006](../adr/006-cognito-vs-keycloak-cost-breakeven.md)）。

### 9.2 ヒアリングで早期確定すべき項目（🔴 TBD）

優先順位が高い順:

1. **FR-FED-002**: Entra ID 実接続（PoC は Auth0 代替）
2. **FR-AUTH-005 / 006 / FR-FED-006 / 007**: 上記「Keycloak 必須要因」群
3. **FR-USER-003**: SCIM 必要性
4. **FR-AUTHZ-009 / 010**: 細粒度認可の必要性
5. **FR-MFA-002**: WebAuthn 採用方針
6. **FR-INT-005**: Webhook 通知の必要性

### 9.3 デフォルト値で進める項目（🟡）

ヒアリングで承認だけ取れば確定するもの。デフォルト値の妥当性を提示する形で進める。

---

## 10. 関連ドキュメント

- [auth-patterns.md](../common/auth-patterns.md): 認証パターン詳細（Cognito vs Keycloak 比較）
- [authz-architecture-design.md](../common/authz-architecture-design.md): 認可アーキテクチャ
- [identity-broker-multi-idp.md](../common/identity-broker-multi-idp.md): マルチ IdP 設計
- [keycloak-network-architecture.md](../common/keycloak-network-architecture.md): ネットワーク要件
- [non-functional-requirements.md](non-functional-requirements.md): 非機能要件
- ADR-006、010〜015
