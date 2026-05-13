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
| FR-AUTH-009 | パスワードポリシー（最小長・複雑性） | Must | ✅ User Pool 設定 | ✅ Realm Policy | ✅ Cognito 明示設定済（min 8 + 大小数字必須） | ✅ |
| FR-AUTH-010 | パスワード履歴 | Should | ❌ 非対応（`passwordHistoryLength` 相当なし） | ✅ N 履歴設定可 | ❌ | 🔴 |
| FR-AUTH-011 | アカウントロック（連続失敗） | Must | ⚠ Plus ティア（$0.02/MAU 追加）必要 | ✅ Realm 設定 | ✅ Phase 7（realm-export.json `bruteForceProtected: true, failureFactor: 5`） | 🟡 |
| FR-AUTH-012 | パスワード有効期限 | Should | ✅ 設定可 | ✅ 設定可 | ❌ | 🟡 |
| FR-AUTH-013 | セルフサービスパスワードリセット | Must | ✅ Forgot Password | ✅ Forgot Password | ❌ | 🟡 |
| FR-AUTH-014 | 初期パスワード強制変更 | Should | ✅ Required Action | ✅ Required Action | ❌ | 🟡 |

**詳細**: [auth-patterns.md §2.1〜2.9](../common/auth-patterns.md)

---

## 2. FR-FED（フェデレーション / 外部 IdP 連携）

| ID | 要件 | 優先度 | Cognito | Keycloak | PoC | 状態 |
|----|------|:----:|:------:|:------:|:---:|:---:|
| FR-FED-001 | Auth0 OIDC IdP 連携 | — | ✅ | ✅ | ✅ Phase 2,7 | ✅ |
| FR-FED-002 | Entra ID（Azure AD）OIDC 連携 | Must | ✅ | ✅ | ❌ Auth0 で代替 | 🔴 |
| FR-FED-003 | Okta OIDC 連携 | Should | ✅ | ✅ | ❌ | 🔴 |
| FR-FED-004 | Google Workspace OIDC 連携 | Could | ✅ | ✅ | ❌ | 🔴 |
| FR-FED-005 | SAML 2.0 IdP として受け入れ（SP モード） | Should | ✅ | ✅ | ❌ | 🔴 |
| FR-FED-006 | SAML 2.0 IdP として発行（IdP モード） | TBD | ❌ 非対応 | ✅ | ❌ | 🔴 |
| FR-FED-007 | LDAP / AD 直接連携 | TBD | ❌ 非対応 | ✅ User Federation | ❌ | 🔴 |
| FR-FED-008 | JIT プロビジョニング | Must | ✅ 自動 | ✅ First Login Flow | ✅ Phase 2 | ✅ |
| FR-FED-009 | 属性マッピング / クレーム変換 | Must | ✅ attribute_mapping | ✅ IdP Mapper | ✅ Phase 8 | ✅ |
| FR-FED-010 | 複数 IdP 並行運用（マルチテナント） | Must | ✅ User Pool に複数登録 | ✅ Realm に複数登録 | ✅ Phase 4,5 | ✅ |
| FR-FED-011 | 顧客追加時のオンボーディングフロー | Must | ✅ 設計可（手動 / IaC） | ✅ 設計可（手動 / IaC） | ⚠ 概念設計のみ | 🟡 |
| FR-FED-012 | フェデレーション時の MFA 重複回避 | Must | ⚠ 個別実装 | ✅ Conditional OTP | ✅ Phase 7（Keycloak のみ） | 🟡 |
| FR-FED-013 | ログイン画面で IdP 選択 UX | Should | ⚠ `identity_provider` パラメータ必須 | ✅ ボタン自動表示 | ✅ Phase 7 | 🟡 |
| FR-FED-014 | Custom Domain での federation | Should | ✅ Hosted UI Custom Domain | ✅ Hostname 設定 | ❌ | 🟡 |

**詳細**: [auth-patterns.md §2.0](../common/auth-patterns.md)、[identity-broker-multi-idp.md](../common/identity-broker-multi-idp.md)

---

## 3. FR-MFA（多要素認証）

| ID | 要件 | 優先度 | Cognito | Keycloak | PoC | 状態 |
|----|------|:----:|:------:|:------:|:---:|:---:|
| FR-MFA-001 | TOTP（Google Authenticator 等） | Must | ✅ | ✅ | ✅ Phase 1,7 | ✅ |
| FR-MFA-002 | WebAuthn / FIDO2（Passkeys） | Should | ✅ ネイティブ対応（Essentials+ ティア、2024-11〜） | ✅ | ❌ 未検証 | 🟡 |
| FR-MFA-003 | SMS OTP | Could | ✅（追加課金） | ⚠ プラグイン | ❌ | 🔴 |
| FR-MFA-004 | メール OTP | Could | ✅ | ✅ | ❌ | 🔴 |
| FR-MFA-005 | バックアップコード | Should | ❌ | ✅ | ❌ | 🟡 |
| FR-MFA-006 | 条件付き MFA（IP / リスクベース） | Should | ⚠ Plus ティア（$0.02/MAU 追加）必要（リスクベース適応認証） | ✅ Conditional Flow | ✅ Phase 7（Keycloak） | 🟡 |
| FR-MFA-007 | MFA 強制 / 任意の切替（ロール単位） | Must | ⚠ User 単位のみ | ✅ Flow 単位制御可 | ✅ Phase 7 | 🟡 |
| FR-MFA-008 | 端末記憶（Trusted Device） | Could | ✅ Remember Device | ⚠ 設定要 | ❌ | 🔴 |
| FR-MFA-009 | 管理者の MFA 強制 | Must | ✅ | ✅ | ❌ | 🟡 |

**詳細**: [auth-patterns.md §2.0.2](../common/auth-patterns.md)、[ADR-009](../adr/009-mfa-responsibility-by-idp.md)

---

## 4. FR-SSO / FR-LOGOUT（シングルサインオン・ログアウト）

| ID | 要件 | 優先度 | Cognito | Keycloak | PoC | 状態 |
|----|------|:----:|:------:|:------:|:---:|:---:|
| FR-SSO-001 | 同一 IdP 内の複数 Client 間 SSO | Must | ✅ User Pool 内 | ✅ Realm 内 | ✅ Phase 1,7 | ✅ |
| FR-SSO-002 | Auth0/Entra 経由のクロス IdP SSO | Must | ✅ | ✅ | ✅ Phase 2,7 | ✅ |
| FR-SSO-003 | ローカルログアウト（アプリ Cookie 削除のみ） | Must | ✅ | ✅ | ✅ | ✅ |
| FR-SSO-004 | IdP セッション破棄（OIDC RP-Initiated Logout） | Must | ✅ `/logout` | ✅ `/logout?id_token_hint=...` | ✅ | ✅ |
| FR-SSO-005 | フェデレーション IdP セッション破棄（連動ログアウト） | Should | ⚠ URL エンコード制約あり | ✅ | ✅ Phase 2,5 | 🟡 |
| FR-SSO-006 | Front-Channel Logout | Should | ✅ | ✅ | ❌ | 🟡 |
| FR-SSO-007 | Back-Channel Logout（RFC 8606） | Should | ❌ 非対応 | ✅ ネイティブ対応 | ✅ Phase 7（Keycloak） | 🟡 |
| FR-SSO-008 | セッションタイムアウト設定 | Must | ✅ | ✅ | ⚠ デフォルトのみ | 🟡 |
| FR-SSO-009 | アクセストークン強制無効化（Revocation） | Should | ⚠ Refresh Token のみ revoke 可 | ✅ Token Revocation | ❌ | 🔴 |
| FR-SSO-010 | 強制全セッション破棄（管理者操作） | Must | ✅ AdminUserGlobalSignOut | ✅ Admin Console | ❌ | 🟡 |

**詳細**: [auth-patterns.md §2.1, §2.2](../common/auth-patterns.md)、[reference/session-management-deep-dive.md](../reference/session-management-deep-dive.md)

---

## 5. FR-AUTHZ（認可）

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
| FR-AUTHZ-009 | リソースレベル認可（UMA 2.0 / Fine-grained） | Could | ❌ 非対応 | ✅ Authorization Services | ❌ | 🔴 |
| FR-AUTHZ-010 | 動的属性ベース認可（ABAC） | Could | ⚠ Lambda 側実装 | ✅ Policy Enforcer | ❌ | 🔴 |

**詳細**: [authz-architecture-design.md](../common/authz-architecture-design.md)、[claim-mapping-authz-scenario.md](../common/claim-mapping-authz-scenario.md)

---

## 6. FR-USER（ユーザー管理）

| ID | 要件 | 優先度 | Cognito | Keycloak | PoC | 状態 |
|----|------|:----:|:------:|:------:|:---:|:---:|
| FR-USER-001 | ユーザー作成 / 更新 / 削除（CRUD） | Must | ✅ Admin API | ✅ Admin REST API | ✅ | ✅ |
| FR-USER-002 | カスタム属性（任意フィールド） | Must | ✅ Custom Attributes | ✅ User Attributes（無制限） | ✅ Phase 8 | ✅ |
| FR-USER-003 | SCIM 2.0 プロビジョニング | TBD | ⚠ 非ネイティブ（自前実装要） | ✅ プラグイン対応 | ❌ | 🔴 |
| FR-USER-004 | セルフサービスプロフィール編集 | Must | ⚠ アプリ側実装 | ✅ Account Console | ❌ | 🟡 |
| FR-USER-005 | ユーザー検索・一覧 | Must | ✅ ListUsers API | ✅ Search API | ✅ | ✅ |
| FR-USER-006 | ユーザー有効化 / 無効化（suspend） | Must | ✅ AdminDisableUser | ✅ Enable/Disable | ✅ | ✅ |
| FR-USER-007 | ユーザーグループ管理 | Should | ✅ Cognito Groups | ✅ Realm Groups | ⚠ 概念のみ | 🟡 |
| FR-USER-008 | ロール割り当て | Must | ⚠ Custom Attribute or Group | ✅ Realm Role Assignment | ✅ Phase 8 | 🟡 |
| FR-USER-009 | バルクインポート（CSV / JSON） | Should | ✅ ImportUsers | ✅ Realm Import | ❌ | 🟡 |
| FR-USER-010 | ユーザーパスワード強制リセット | Must | ✅ AdminSetUserPassword | ✅ Admin Console | ✅ | ✅ |
| FR-USER-011 | ユーザー削除時の関連データ削除（GDPR 等） | Should | ✅ AdminDeleteUser | ✅ Cascade Delete | ❌ | 🟡 |
| FR-USER-012 | ユーザー作成時の招待メール | Should | ✅ AdminCreateUser invitation | ✅ Email Verification | ⚠ デフォルト | 🟡 |

---

## 7. FR-ADMIN（管理機能）

| ID | 要件 | 優先度 | Cognito | Keycloak | PoC | 状態 |
|----|------|:----:|:------:|:------:|:---:|:---:|
| FR-ADMIN-001 | 管理コンソール UI | Must | ✅ AWS Console | ✅ Keycloak Admin Console | ✅ Phase 6 | ✅ |
| FR-ADMIN-002 | テナント追加・削除 | Must | ✅ User Pool 単位 / Group | ✅ Realm 単位 / IdP 単位 | ⚠ 設計のみ | 🟡 |
| FR-ADMIN-003 | IdP 追加・削除・更新 | Must | ✅ Console / Terraform | ✅ Console / Terraform | ✅ Phase 2,5,7 | ✅ |
| FR-ADMIN-004 | クライアント（App）管理 | Must | ✅ App Client | ✅ Client | ✅ | ✅ |
| FR-ADMIN-005 | ロール定義管理 | Must | ⚠ Custom Attr / Group | ✅ Realm Role / Client Role | ✅ Phase 8 | 🟡 |
| FR-ADMIN-006 | パーミッション管理（細粒度） | Could | ⚠ アプリ側 | ✅ Authorization Services | ❌ | 🔴 |
| FR-ADMIN-007 | 監査ログ閲覧 | Must | ✅ CloudTrail | ✅ Event Listener | ⚠ 設定要 | 🟡 |
| FR-ADMIN-008 | 設定変更履歴 | Should | ✅ CloudTrail | ✅ Admin Events | ❌ | 🟡 |
| FR-ADMIN-009 | テナント別設定の分離 | Must | ✅ User Pool 分離 | ✅ Realm 分離 | ✅ Phase 4,5 | ✅ |
| FR-ADMIN-010 | 管理者ロール（RBAC for Admin） | Must | ✅ IAM | ✅ Realm Admin Roles | ⚠ デフォルト | 🟡 |
| FR-ADMIN-011 | テナント管理者の委譲（顧客の自社運用） | Should | ⚠ AWS IAM 必要 | ✅ Realm-level Admin | ❌ | 🔴 |
| FR-ADMIN-012 | カスタマイズ可能なログイン UI | Should | ⚠ CSS / ロゴのみ | ✅ Theme（フルカスタム） | ❌ | 🟡 |

---

## 8. FR-INT（外部システム統合）

| ID | 要件 | 優先度 | Cognito | Keycloak | PoC | 状態 |
|----|------|:----:|:------:|:------:|:---:|:---:|
| FR-INT-001 | OIDC 1.0 / OAuth 2.0 標準準拠 | Must | ✅ | ✅ | ✅ | ✅ |
| FR-INT-002 | OIDC Discovery（`.well-known`） | Must | ✅ | ✅ | ✅ | ✅ |
| FR-INT-003 | JWKS 公開エンドポイント | Must | ✅ AWS 公開 | ✅ ALB 経由 | ✅ Phase 3 | ✅ |
| FR-INT-004 | SAML 2.0 メタデータ | Should | ✅ | ✅ | ❌ | 🟡 |
| FR-INT-005 | Webhook イベント通知（user.created 等） | Should | ⚠ Pre Token / Post Conf Lambda | ✅ Event Listener | ❌ | 🔴 |
| FR-INT-006 | 管理 REST API | Must | ✅ AWS SDK | ✅ Admin REST API | ⚠ | 🟡 |
| FR-INT-007 | API Gateway / Lambda Authorizer 統合 | Must | ✅ | ✅ | ✅ Phase 3 | ✅ |
| FR-INT-008 | 監査ログ外部出力（CloudWatch / S3 / Kinesis） | Must | ✅ CloudTrail / CloudWatch | ⚠ Event Listener 自前実装 | ⚠ デフォルト | 🟡 |
| FR-INT-009 | 監査ログ SIEM 連携（Splunk / Datadog） | Could | ✅ | ⚠ ログ転送設計要 | ❌ | 🔴 |
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
