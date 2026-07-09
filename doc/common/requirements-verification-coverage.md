# 要件 × 検証カバレッジ マトリクス

> **作成日**: 2026-06-07
> **目的**: 要件定義（FR 59 項目 / NFR 48 項目）に対する PoC Phase 1-10 Stage A での検証状況を網羅的に俯瞰し、「**いま AWS 環境（Phase 10 Stage A 反映済）で何が画面 / API から確認できるか**」を一目で分かるようにする
> **読み方**: 行＝要件項目、列＝Cognito / Keycloak での検証実績と AWS 環境での再現方法
> **関連**:
> - [phase10-stage-a-screen-verification.md](phase10-stage-a-screen-verification.md) — 具体的な画面 / curl シナリオ
> - [doc/requirements/functional-requirements.md](../requirements/functional-requirements.md) — FR 一覧（要件 ID マトリクス）
> - [doc/requirements/non-functional-requirements.md](../requirements/non-functional-requirements.md) — NFR 一覧
> - [doc/requirements/poc-summary-evaluation.md](../requirements/poc-summary-evaluation.md) — Phase 1-9 総括
> - [phase10-stage-a-verification.md](phase10-stage-a-verification.md) — Stage A 検証レポート

---

## 0. サマリ統計

| 区分 | 要件数 | ✅ 検証済 | 🟡 部分検証/制約 | ❌ 未検証 | カバレッジ |
|---|---:|---:|---:|---:|---:|
| **FR（機能要件）** | 59 | 32 | 13 | 14 | 76% |
| **NFR（非機能要件）** | 48 | 12 | 17 | 19 | 60% |
| **合計** | 107 | 44 | 30 | 33 | 69% |

> **凡例**:
> - ✅ **検証済**: PoC で実機検証完了（Cognito または Keycloak または両方）
> - 🟡 **部分検証 / 制約あり**: 一部のみ検証、ティア依存、ローカル検証のみで AWS 未反映 など
> - ❌ **未検証**: PoC スコープ外、または本番設計フェーズで決定する項目
> - ➖ **対象外**: マネージドサービスの仕様で検証不要 / 適用外

---

## 1. FR-AUTH（認証 / パスワード管理）— 14 項目

| ID | 要件名 | Cognito | Keycloak | 検証 Phase | **AWS 環境で今すぐ可** | 検証手段 |
|---|---|:-:|:-:|:-:|:-:|---|
| FR-AUTH-001 | ID/PW 認証（ローカル） | ✅ | ✅ | 1, 6, 7 | ✅ | Public ALB の login 画面（要 IP 制限通過）|
| FR-AUTH-002 | Auth Code + PKCE（SPA） | ✅ | ✅ | 1, 6 | ✅ | `make app-kc-dev` + ブラウザ |
| FR-AUTH-003 | Auth Code + client_secret（SSR） | 🟡 | 🟡 | 10-A | 🟡 | `auth-poc-ssr` Client は realm 投入済、SSR 実装は別途必要 |
| FR-AUTH-004 | Client Credentials（M2M） | ❌ | ✅ | 10-A | ✅ | `auth-poc-backend` で curl token endpoint |
| FR-AUTH-005 | **Token Exchange（RFC 8693）** | ❌ | ✅ | 10-A | ✅ | scenario I：`auth-poc-backend → auth-poc-target-api` audience exchange |
| FR-AUTH-006 | Device Code Flow（RFC 8628） | ❌ | 🟡 | — | 🟡 | KC は対応可だが Client 未設定 |
| FR-AUTH-007 | mTLS Client 認証（RFC 8705） | ❌ | 🟡 | — | ❌ | 本番設計で証明書基盤と合わせて検証 |
| FR-AUTH-008 | ROPC（Password Grant） | ➖ | ➖ | — | ➖ | 採用しない方針 |
| FR-AUTH-009 | パスワードポリシー（長さ・複雑性） | ✅ | ✅ | 1, 6 | ✅ | Admin Console → Realm Settings → Authentication → Policies |
| FR-AUTH-010 | パスワード履歴 | 🟡 Plus | ✅ | — | 🟡 | KC は設定可、現 realm.json では未設定 |
| FR-AUTH-011 | アカウントロック | 🟡 Plus | ✅ | — | 🟡 | Realm Settings の Brute Force Detection（現 realm では OFF） |
| FR-AUTH-012 | パスワード有効期限 | ✅ | ✅ | — | ✅ | Realm Settings の Password Policy |
| FR-AUTH-013 | セルフサービスパスワードリセット | ✅ | ✅ | — | 🟡 | KC は Login Settings の Forgot password を有効化、SMTP 設定要 |
| FR-AUTH-014 | 初期パスワード強制変更 | ✅ | ✅ | — | ✅ | Required Actions → Update Password |

**ハイライト**: **Token Exchange v2** は Cognito 非対応 / Keycloak のみ。Stage A-3 で realm に焼き付け済、AWS 環境でも curl から動作確認可（[シナリオ I](phase10-stage-a-screen-verification.md#シナリオ-i-token-exchange-v2audience-切替)）。

---

## 2. FR-FED（フェデレーション / マルチテナント）— 14 項目

| ID | 要件名 | Cognito | Keycloak | 検証 Phase | **AWS 環境で今すぐ可** | 検証手段 |
|---|---|:-:|:-:|:-:|:-:|---|
| FR-FED-001 | Auth0 OIDC 連携 | ✅ | ✅ | 2, 7 | 🟡 | realm-idp-auth0.json.example を環境変数埋めて import |
| FR-FED-002 | Entra ID（Azure AD）OIDC | ❌ | ❌ | — | ❌ | 実 Entra テナント未準備 |
| FR-FED-003 | Okta OIDC | ❌ | ❌ | — | ❌ | 実 Okta テナント未準備 |
| FR-FED-004 | Google Workspace OIDC | ❌ | ❌ | — | ❌ | 実 GWS テナント未準備 |
| FR-FED-005 | SAML 2.0 IdP として受け入れ（SP） | ❌ | 🟡 | — | 🟡 | KC は対応可（既存 realm で test SP 未設定） |
| FR-FED-006 | SAML 2.0 IdP として発行（IdP） | ❌ | 🟡 | — | ❌ | KC は対応可だが realm に SP 登録なし |
| FR-FED-007 | LDAP / AD 直接連携 | ❌ | 🟡 | — | ❌ | KC は対応可、OpenLDAP コンテナで別途検証必要（Stage B-1）|
| FR-FED-008 | JIT プロビジョニング | ✅ | ✅ | 2, 7 | 🟡 | Auth0 IdP 設定後にブラウザ動作 |
| FR-FED-009 | 属性マッピング / クレーム変換 | ✅ | ✅ | 8, 9 | ✅ | Admin Console → Client → Client Scopes → Mappers |
| FR-FED-010 | 複数 IdP 並行運用 | ✅ | ✅ | 4 | 🟡 | KC は 1 realm 内 N IdP、Auth0 + 別 IdP 試験は Stage B-3 |
| FR-FED-011 | 顧客追加オンボーディングフロー | ❌ | 🟡 | — | ❌ | 運用設計（Terraform module 化）が未確立 |
| FR-FED-012 | フェデレーション MFA 二重回避 | 🟡 | ✅ | 7 | ✅ | KC の Conditional OTP Flow が realm に投入済 |
| FR-FED-013 | IdP 選択 UX | 🟡 param 要 | ✅ 自動 | 7 | 🟡 | IdP 1 つも未設定なので画面選択肢なし |
| FR-FED-014 | Custom Domain での federation | ❌ | ❌ | — | ❌ | Route 53 / ACM 公開証明書整備が必要 |

**ハイライト**: Auth0 IdP は **realm.json のテンプレート化済**（[realm-idp-auth0.json.example](../../keycloak/config/realm-idp-auth0.json.example)）。環境変数を埋めて import すれば Phase 7 と同じ挙動を AWS で再現可能。

---

## 3. FR-MFA（多要素認証）— 9 項目

| ID | 要件名 | Cognito | Keycloak | 検証 Phase | **AWS 環境で今すぐ可** | 検証手段 |
|---|---|:-:|:-:|:-:|:-:|---|
| FR-MFA-001 | TOTP | ✅ | ✅ | 1, 7 | ✅ | Account Console で alice-kc に TOTP 登録 |
| FR-MFA-002 | WebAuthn / FIDO2（Passkeys） | 🟡 Essentials+ | 🟡 | — | 🟡 | KC は対応可、WebAuthn Authenticator 設定要 |
| FR-MFA-003 | SMS OTP | ❌ | ❌ | — | ❌ | SMS gateway 未準備 |
| FR-MFA-004 | メール OTP | ❌ | 🟡 | — | 🟡 | KC は Email OTP Authenticator あり、SMTP 設定要 |
| FR-MFA-005 | バックアップコード | ❌ | 🟡 | — | 🟡 | KC は Recovery Codes Authenticator あり、Flow 設定要 |
| FR-MFA-006 | 条件付き MFA（IP / Risk） | 🟡 Plus | 🟡 | 7 | 🟡 | Conditional OTP（IP ベース）は realm で実装可 |
| FR-MFA-007 | MFA 強制 / 任意切替（ロール単位） | ✅ | ✅ | 7 | ✅ | Required Actions / Conditional OTP |
| FR-MFA-008 | 端末記憶（Trusted Device） | ✅ | 🟡 | — | ❌ | KC は Cookie ベースの remember-me、別設計要 |
| FR-MFA-009 | 管理者 MFA 強制 | ✅ | ✅ | — | ✅ | admin user に Required Actions を設定 |

---

## 4. FR-SSO（SSO / ログアウト / セッション）— 10 項目

| ID | 要件名 | Cognito | Keycloak | 検証 Phase | **AWS 環境で今すぐ可** | 検証手段 |
|---|---|:-:|:-:|:-:|:-:|---|
| FR-SSO-001 | 同一 IdP 内 複数 Client SSO | ✅ | ✅ | 1, 7 | ✅ | 同一ブラウザで複数 client にログインしてセッション継続確認 |
| FR-SSO-002 | クロス IdP SSO（Auth0 経由） | ✅ | ✅ | 7 | 🟡 | Auth0 IdP 設定後 |
| FR-SSO-003 | ローカルログアウト（Cookie 削除のみ） | ✅ | ✅ | — | ✅ | SPA の signoutSilent() |
| FR-SSO-004 | OIDC RP-Initiated Logout | ✅ | ✅ | 1, 6 | ✅ | `/realms/auth-poc/protocol/openid-connect/logout` |
| FR-SSO-005 | フェデレーション IdP 連動ログアウト | 🟡 | ✅ | 7 | 🟡 | Auth0 連動時に確認 |
| FR-SSO-006 | Front-Channel Logout | ✅ | ✅ | — | ✅ | OIDC logout iframe |
| FR-SSO-007 | **Back-Channel Logout (RFC 8606)** | ❌ | ✅ | 7 | ✅ | `auth-poc-spa` client の Backchannel Logout URL 設定で確認 |
| FR-SSO-008 | セッションタイムアウト | ✅ | ✅ | 6 | ✅ | Realm Settings → Sessions |
| FR-SSO-009 | Access Token Revocation | ✅ | ✅ | — | ✅ | `/protocol/openid-connect/revoke` |
| FR-SSO-010 | 強制全セッション破棄（管理者操作） | ✅ | ✅ | — | ✅ | Admin Console → User → Sessions → Logout |

---

## 5. FR-AUTHZ（認可）— 10 項目

| ID | 要件名 | Cognito | Keycloak | 検証 Phase | **AWS 環境で今すぐ可** | 検証手段 |
|---|---|:-:|:-:|:-:|:-:|---|
| FR-AUTHZ-001 | JWT クレームベース認可 | ✅ | ✅ | 8, 9 | ✅ | Lambda Authorizer + Backend Lambda |
| FR-AUTHZ-002 | tenant_id テナント分離 | ✅ | ✅ | 8, 9 | ✅ | alice-kc (acme-corp) vs dave-kc (globex-inc) |
| FR-AUTHZ-003 | roles クレーム認可 | ✅ | ✅ | 8, 9 | ✅ | employee/manager/admin の挙動差 |
| FR-AUTHZ-004 | ロール階層（継承） | ✅ | ✅ | 8, 9 | ✅ | Backend Lambda 認可ロジックで実装 |
| FR-AUTHZ-005 | scope ベース認可（M2M） | ✅ | ✅ | 10-A | ✅ | Client Credentials + scope 確認 |
| FR-AUTHZ-006 | カスタムクレーム注入 | ✅ | ✅ | 8, 9 | ✅ | Protocol Mapper（User Attribute / Realm Role） |
| FR-AUTHZ-007 | Lambda Authorizer 統合 | ✅ | ✅ | 3, 9 | ✅ | API Gateway → Lambda → /v2/expenses |
| FR-AUTHZ-008 | マルチイシュア対応 | ✅ | ✅ | 3, 4, 9 | ✅ | 同一 Authorizer で central/local/keycloak の検証 |
| FR-AUTHZ-009 | リソースレベル認可（UMA 2.0） | ❌ | 🟡 | — | 🟡 | KC は UMA 2.0 対応、Resource Server 未設定 |
| FR-AUTHZ-010 | 動的属性 ABAC | ❌ | 🟡 | — | 🟡 | KC Authorization Services で実現可能 |

**ハイライト**: テナント分離 + ロール階層は Phase 8/9 で実装済、Stage A 反映後の AWS 環境で **`/v2/expenses` エンドポイント（VPC Authorizer 経由）** から検証可能。

---

## 6. FR-USER（ユーザー管理）— 12 項目

| ID | 要件名 | Cognito | Keycloak | 検証 Phase | **AWS 環境で今すぐ可** | 検証手段 |
|---|---|:-:|:-:|:-:|:-:|---|
| FR-USER-001 | CRUD | ✅ | ✅ | — | ✅ | Admin Console / Admin REST API |
| FR-USER-002 | カスタム属性 | ✅ | ✅ | 8, 9 | ✅ | tenant_id 属性は実装済 |
| FR-USER-003 | SCIM 2.0 プロビジョニング | ❌ | 🟡 | — | ❌ | KC は SCIM extension 利用可能、PoC では未実装 |
| FR-USER-004 | セルフサービスプロフィール編集 | ✅ | ✅ | — | ✅ | Account Console (`/realms/auth-poc/account`) |
| FR-USER-005 | ユーザー検索・一覧 | ✅ | ✅ | — | ✅ | Admin Console |
| FR-USER-006 | 有効化 / 無効化 | ✅ | ✅ | — | ✅ | User → Enabled toggle |
| FR-USER-007 | グループ管理 | ✅ | ✅ | — | ✅ | Groups タブ |
| FR-USER-008 | ロール割り当て | ✅ | ✅ | 8, 9 | ✅ | User → Role mapping |
| FR-USER-009 | バルクインポート | 🟡 | ✅ | — | 🟡 | KC は import 機能あり、CSV→JSON 変換要 |
| FR-USER-010 | 強制パスワードリセット | ✅ | ✅ | — | ✅ | User → Credentials → Reset password |
| FR-USER-011 | 削除時の関連データ削除（GDPR） | ❌ | 🟡 | — | ❌ | アプリ側の連携設計が必要 |
| FR-USER-012 | 招待メール | ✅ | 🟡 | — | 🟡 | SMTP 設定要 |

---

## 7. FR-ADMIN（管理機能）— 12 項目

| ID | 要件名 | Cognito | Keycloak | 検証 Phase | **AWS 環境で今すぐ可** | 検証手段 |
|---|---|:-:|:-:|:-:|:-:|---|
| FR-ADMIN-001 | 管理コンソール UI | ✅ AWS Console | ✅ Admin Console | 6 | ✅ | Admin ALB |
| FR-ADMIN-002 | テナント追加・削除 | ✅ Pool 追加 | ✅ Realm 追加 | — | ✅ | Master realm から create realm |
| FR-ADMIN-003 | IdP 追加・削除・更新 | ✅ | ✅ | 7 | ✅ | Identity Providers タブ |
| FR-ADMIN-004 | Client 管理 | ✅ | ✅ | — | ✅ | Clients タブ |
| FR-ADMIN-005 | ロール定義管理 | ✅ | ✅ | 8, 9 | ✅ | Realm Roles タブ |
| FR-ADMIN-006 | パーミッション管理（細粒度） | 🟡 | ✅ | — | ✅ | Fine-grained Authz（A3 で焼き付け済） |
| FR-ADMIN-007 | 監査ログ閲覧 | ✅ CloudTrail | ✅ Events | — | 🟡 | Events タブ（Login/Admin Events を有効化要）|
| FR-ADMIN-008 | 設定変更履歴 | ✅ CloudTrail | ✅ Admin Events | — | 🟡 | 同上 |
| FR-ADMIN-009 | テナント別設定の分離 | ✅ | ✅ | — | ✅ | Realm 単位で完全分離 |
| FR-ADMIN-010 | 管理者ロール（RBAC） | ✅ | ✅ | — | ✅ | realm-management role |
| FR-ADMIN-011 | テナント管理者委譲 | 🟡 | ✅ | — | ✅ | Fine-grained Authz で realm-admin 部分委譲可 |
| FR-ADMIN-012 | カスタマイズログイン UI | 🟡 | ✅ | — | 🟡 | Custom Theme（PoC では default のまま） |

---

## 8. FR-INT（外部統合）— 10 項目

| ID | 要件名 | Cognito | Keycloak | 検証 Phase | **AWS 環境で今すぐ可** | 検証手段 |
|---|---|:-:|:-:|:-:|:-:|---|
| FR-INT-001 | OIDC 1.0 / OAuth 2.0 標準準拠 | ✅ | ✅ | 1-9 | ✅ | Discovery + JWKS + token endpoint |
| FR-INT-002 | OIDC Discovery | ✅ | ✅ | — | ✅ | `/realms/auth-poc/.well-known/openid-configuration` |
| FR-INT-003 | JWKS 公開 | ✅ | ✅ | 9 | ✅ | `/realms/auth-poc/protocol/openid-connect/certs` |
| FR-INT-004 | SAML 2.0 メタデータ | ❌ | ✅ | — | 🟡 | KC は `/realms/auth-poc/protocol/saml/descriptor` |
| FR-INT-005 | Webhook イベント通知 | 🟡 | 🟡 | — | ❌ | Cognito は Lambda Trigger、KC は extension 要 |
| FR-INT-006 | 管理 REST API | ✅ | ✅ | — | ✅ | `/admin/realms/auth-poc/...` |
| FR-INT-007 | API Gateway / Lambda Authorizer | ✅ | ✅ | 3, 9 | ✅ | 既存 API Gateway 経由 |
| FR-INT-008 | 監査ログ外部出力 | ✅ CloudWatch | 🟡 | — | 🟡 | KC は Event Listener SPI（PoC 未実装） |
| FR-INT-009 | SIEM 連携 | 🟡 | 🟡 | — | ❌ | Splunk/Datadog 連携は設計フェーズ |
| FR-INT-010 | Terraform / IaC | ✅ | 🟡 | 6-10 | ✅ | KC は realm.json まで含めて IaC 化済 |

---

## 9. NFR-AVL（可用性）— 6 項目

| ID | 要件名 | 検証状況 | **AWS 環境で今すぐ可** | 検証手段 |
|---|---|:-:|:-:|---|
| NFR-AVL-001 | サービス稼働率 SLA | ❌ 数値未確定 | 🟡 | CloudWatch メトリクス計測（要件 SLA 値が未定） |
| NFR-AVL-002 | 計画メンテナンス窓 | ❌ 未定義 | ❌ | 運用設計フェーズ |
| NFR-AVL-003 | Multi-AZ 配置 | ✅ Stage A | ✅ | ECS task が 1a + 1c 分散、RDS Multi-AZ=true |
| NFR-AVL-004 | 自動復旧（コンテナ障害） | ✅ Phase 6 | ✅ | ECS task stop → 自動再起動を観察（[シナリオ J](phase10-stage-a-screen-verification.md#シナリオ-j-ecs-task-stop-でフェイルオーバー)）|
| NFR-AVL-005 | 単一障害点排除 | 🟡 Stage A | 🟡 | ALB 3 本 / ECS 2 task / RDS Multi-AZ。だが Admin ALB は 1 本 |
| NFR-AVL-006 | デプロイ時ダウンタイム | 🟡 | 🟡 | ECS rolling deploy、kc-redeploy で観測可 |

**ハイライト**: Stage A 反映で **Multi-AZ + Infinispan セッション共有** が AWS で動作。実際にタスクを stop して可用性を体感可能。

---

## 10. NFR-PERF（性能）— 8 項目

| ID | 要件名 | 検証状況 | **AWS 環境で今すぐ可** | 検証手段 |
|---|---|:-:|:-:|---|
| NFR-PERF-001 | 認証応答時間（P50/P95/P99） | ❌ | 🟡 | ab / k6 等で計測、要件 SLA が未定 |
| NFR-PERF-002 | 同時認証 req/s | ❌ | 🟡 | 同上 |
| NFR-PERF-003 | Lambda Authorizer 応答時間 | ✅ Phase 3 | ✅ | CloudWatch Logs Duration |
| NFR-PERF-004 | JWT 検証スループット | 🟡 | 🟡 | 個別 ab 計測 |
| NFR-PERF-005 | JWKS キャッシュ TTL | ✅ Phase 3 | ✅ | Authorizer のキャッシュ設定（300s） |
| NFR-PERF-006 | API Gateway スロットリング | 🟡 | 🟡 | 既存 API GW 設定 |
| NFR-PERF-007 | ピーク時耐性 | ❌ | 🟡 | Auto Scaling + ab 負荷試験 |
| NFR-PERF-008 | DB 応答時間 | ❌ | 🟡 | RDS Performance Insights |

---

## 11. NFR-SCL（拡張性）— 7 項目

| ID | 要件名 | 検証状況 | **AWS 環境で今すぐ可** | 検証手段 |
|---|---|:-:|:-:|---|
| NFR-SCL-001 | MAU スケール上限 | ❌ | 🟡 | 要件 MAU が未確定（損益分岐 17.5万） |
| NFR-SCL-002 | ピーク時同時セッション数 | ❌ | 🟡 | 負荷試験で計測 |
| NFR-SCL-003 | 顧客テナント数（IdP 数）スケール | 🟡 | 🟡 | KC は 1 realm 内 N IdP / N realm 構成、設計次第 |
| NFR-SCL-004 | IdP 追加リードタイム | ❌ | ❌ | 運用フロー設計が未確立 |
| NFR-SCL-005 | 自動スケーリング | ✅ Stage A | ✅ | Auto Scaling target min=2, max=4 |
| NFR-SCL-006 | マルチリージョン対応 | 🟡 Phase 5 | ❌ | Cognito 大阪は完了、KC 大阪は未対応 |
| NFR-SCL-007 | DB スケール（Keycloak） | 🟡 | 🟡 | RDS read replica 設計が未確立 |

---

## 12. NFR-SEC（セキュリティ）— 20 項目

| ID | 要件名 | 検証状況 | **AWS 環境で今すぐ可** | 検証手段 |
|---|---|:-:|:-:|---|
| NFR-SEC-001 | TLS 1.2 以上 | ✅ Stage A | ✅ | ALB SSL Policy = TLS13-1-2-2021-06 |
| NFR-SEC-002 | データ暗号化 at-rest | ✅ | ✅ | RDS storage_encrypted=true |
| NFR-SEC-003 | トークン署名アルゴリズム | ✅ | ✅ | JWKS の alg=RS256 |
| NFR-SEC-004 | Access Token TTL | ✅ | ✅ | Realm Settings → Tokens（default 5min） |
| NFR-SEC-005 | Refresh Token TTL | ✅ | ✅ | 同上 |
| NFR-SEC-006 | ID Token TTL | ✅ | ✅ | Access Token と同じ |
| NFR-SEC-007 | Refresh Token Rotation | 🟡 | 🟡 | Realm Settings → Revoke Refresh Token |
| NFR-SEC-008 | トークン失効 | ✅ | ✅ | revoke endpoint |
| NFR-SEC-009 | パスワード保管アルゴリズム | ✅ | ✅ | PBKDF2-SHA256（KC default） |
| NFR-SEC-010 | ブルートフォース対策 | 🟡 | 🟡 | Brute Force Detection（要 Realm 設定） |
| NFR-SEC-010-2 | 侵害クレデンシャル検出 | ❌ | ❌ | HIBP 連携は extension 要 |
| NFR-SEC-011 | WAF 適用 | ❌ | ❌ | ALB の前段に WAF 未配置 |
| NFR-SEC-012 | DDoS 対策 | 🟡 | 🟡 | AWS Shield Standard のみ |
| NFR-SEC-013 | ペネトレーションテスト | ❌ | ❌ | 本番フェーズ |
| NFR-SEC-014 | 脆弱性スキャン | 🟡 | 🟡 | ECR Image Scan 設定済（KC image） |
| NFR-SEC-015 | シークレット管理 | 🟡 | 🟡 | terraform.tfvars が SSOT、Secrets Manager 未統合 |
| NFR-SEC-016 | Private Subnet 配置 | ✅ Phase 9 | ✅ | ECS / RDS が Private Subnet |
| NFR-SEC-017 | 管理画面アクセス制御 | ✅ Stage A | ✅ | Admin ALB の SG で IP 制限 |
| NFR-SEC-018 | JWKS エンドポイント保護 | 🟡 | 🟡 | Public ALB Listener Rule で全 IP 許可（WAF レート制限なし） |
| NFR-SEC-019 | 内部通信認証（Lambda → KC） | ✅ Phase 9 | ✅ | VPC Lambda + Internal ALB（インターネット非経由） |
| NFR-SEC-020 | セッション固定攻撃対策 | ✅ | ✅ | KC 標準動作 |

**ハイライト**: Stage A 反映で **HTTPS / Private Subnet / Admin IP 制限** が動作。Authorizer の VPC 化 + Internal ALB JWKS（Phase 9）も継続稼働。

---

## 13. NFR-DR（災害復旧）— 8 項目

| ID | 要件名 | 検証状況 | **AWS 環境で今すぐ可** | 検証手段 |
|---|---|:-:|:-:|---|
| NFR-DR-001 | RTO | ❌ | 🟡 | 要件 RTO 値が未確定 |
| NFR-DR-002 | RPO | ❌ | 🟡 | 同上 |
| NFR-DR-003 | フェイルオーバー方式 | 🟡 Phase 5 | 🟡 | Cognito は手動。KC 自動 FO は未検証 |
| NFR-DR-004 | バックアップ保存期間 | ✅ | ✅ | RDS backup_retention_period=7 days |
| NFR-DR-005 | PITR | ✅ | ✅ | RDS 自動 backup で対応 |
| NFR-DR-006 | クロスリージョンバックアップ | ❌ | ❌ | RDS snapshot のリージョン間コピー設計未 |
| NFR-DR-007 | DR 訓練 | ❌ | ❌ | 運用フェーズ |
| NFR-DR-008 | DR 切替時セッション維持 | 🟡 Phase 5 | ❌ | Cognito のみ部分確認、KC は未 |

**重要ギャップ**: 引き継ぎノートでも指摘の **DR Cognito Pre Token Lambda 未設定**（Phase 8/9 で追加した tenant_id/roles クレームが DR では効かない）が継続課題。

---

## 14. NFR-OPS（運用）— 11 項目

| ID | 要件名 | 検証状況 | **AWS 環境で今すぐ可** | 検証手段 |
|---|---|:-:|:-:|---|
| NFR-OPS-001 | 監視メトリクス | 🟡 | 🟡 | CloudWatch 基本メトリクス、ダッシュボード未整備 |
| NFR-OPS-002 | アラート通知 | ❌ | ❌ | CloudWatch Alarm 未設定 |
| NFR-OPS-003 | ログ保存期間 | 🟡 | 🟡 | デフォルト無期限、コスト管理上の制約あり |
| NFR-OPS-004 | ログ検索性 | ✅ | ✅ | CloudWatch Logs Insights |
| NFR-OPS-005 | バージョンアップ方針 | 🟡 | 🟡 | KC: Dockerfile 更新 + ECR push のフロー確立 |
| NFR-OPS-006 | パッチ適用（CVE） | 🟡 | 🟡 | 手動。CI/CD 自動化が未確立 |
| NFR-OPS-007 | 設定変更プロセス | ✅ | ✅ | Terraform + realm.json（Stage A で SSOT 化） |
| NFR-OPS-008 | インシデント対応体制 | ❌ | ❌ | 運用設計フェーズ |
| NFR-OPS-009 | 運用工数 | ❌ | ❌ | 試算済（$1,680/月）だが実測なし |
| NFR-OPS-010 | デプロイ自動化（CI/CD） | ❌ | ❌ | 現状は make コマンド手動 |
| NFR-OPS-011 | テナント追加 SLA | ❌ | ❌ | 運用設計フェーズ |

---

## 15. NFR-COMP（コンプライアンス）— 11 項目

| ID | 要件名 | 検証状況 |
|---|---|:-:|
| NFR-COMP-001〜011 | 個人情報保護法 / GDPR / SOC2 / ISO27001 / PCI DSS / FIPS 140-2 / 監査ログ保存（10 年）/ データ所在地 / 削除権 / アクセス監査 / 鍵ローテーション | **全 11 項目 ❌ 未検証** |

**理由**: コンプライアンス系は本番運用フェーズ + 法務レビューが必要で PoC スコープ外。proposal で要件確定後に対応。

---

## 16. NFR-COST（コスト）— 9 項目

| ID | 要件名 | 検証状況 | 備考 |
|---|---|:-:|---|
| NFR-COST-001〜009 | 初期構築費 / 月額固定 / MAU 単価 / Plus ティア追加 / DR 追加 / 運用人件費 / RHBK サブスク / 損益分岐 / 3 年 TCO | ✅ 試算済 | ADR-006 / poc-summary-evaluation.md §1.3.6 で算出済。Stage A 反映で実測フェーズへ |

---

## 17. NFR-MIG（移行）— 5 項目

| ID | 要件名 | 検証状況 |
|---|---|:-:|
| NFR-MIG-001 | ユーザー移行 | ❌ 未検証（Stage B-4 で予定） |
| NFR-MIG-002 | パスワードハッシュ移行 | ❌ 同上 |
| NFR-MIG-003 | ベンダーロックイン回避 | ✅ OIDC 標準準拠で達成 |
| NFR-MIG-004 | データエクスポート | 🟡 KC は realm-export.json で対応 |
| NFR-MIG-005 | 段階的移行（並行稼働） | 🟡 Identity Broker パターンで設計 |

---

## 18. 主要ギャップとリスク

### 🔥 優先度 高（Stage A 反映の AWS 環境では今すぐ着手可能）

| 項目 | 要件 ID | 着手方法 |
|---|---|---|
| Auth0 IdP を realm に投入 | FR-FED-001 / FR-MFA-006 / FR-FED-012 | `realm-idp-auth0.json.example` を埋めて Partial Import |
| Brute Force Detection 有効化 | FR-AUTH-011 / NFR-SEC-010 | Realm Settings → Authentication → failureFactor 設定 |
| 監査ログ有効化 | FR-ADMIN-007 / FR-ADMIN-008 | Realm Settings → Events → Save events |
| SMTP 設定 | FR-AUTH-013 / FR-USER-012 | SES 等の SMTP 設定 |
| Custom Theme 適用 | FR-ADMIN-012 | theme COPY を Dockerfile に追加 |

### 🔥 優先度 高（Stage B 以降での検証必要）

| 項目 | 要件 ID | Stage |
|---|---|---|
| **LDAP / AD 連携** | FR-FED-007 | Stage B-1（OpenLDAP コンテナで検証） |
| **HRD + CloudFront Lambda@Edge** | FR-FED-013 / FR-FED-014 | Stage B-2 |
| **First Broker Login 7 シナリオ** | FR-FED-008 / FR-FED-012 | Stage B-3 |
| **既存ユーザー移行 + ハッシュ互換** | NFR-MIG-001 / NFR-MIG-002 | Stage B-4 |
| **SAML 2.0 IdP / SP モード** | FR-FED-005 / FR-FED-006 | Stage B-4 |

### ⚠️ 既知の制約

| 項目 | 状況 | 対応 |
|---|---|---|
| **DR Cognito の Pre Token Lambda 未設定** | tenant_id/roles クレームが大阪では効かない | infra/dr-osaka/cognito.tf に lambda_config 追加が必要 |
| **Route 53 自動フェイルオーバー** | 未実装 | 本番 RTO/RPO 確定後に設計 |
| **WAF + DDoS** | ALB 前段に未配置 | 本番設計フェーズ |
| **CI/CD パイプライン** | make コマンド手動 | 本番運用前に GitHub Actions 等で整備 |
| **マルチアカウント分離** | 1 アカウントで全部運用 | 本番は OU 単位で分割 |

---

## 19. クイック実行マップ（Stage A 環境で今すぐ叩ける検証）

> 各シナリオは [phase10-stage-a-screen-verification.md](phase10-stage-a-screen-verification.md) に詳細手順あり

| 検証目的 | カバー要件 | シナリオ番号 |
|---|---|---|
| HTTPS / Issuer | NFR-SEC-001 / FR-INT-001 | A, E, F |
| Admin Console アクセス | FR-ADMIN-001 / NFR-SEC-017 | B |
| SPA からのログイン | FR-AUTH-002 / FR-SSO-001 | C |
| テナント / ロール検証 | FR-AUTHZ-002 / FR-AUTHZ-003 / FR-AUTHZ-004 | D |
| OIDC Discovery | FR-INT-002 | F |
| JWKS（Public + Internal） | FR-INT-003 / NFR-SEC-019 | G |
| Client Credentials | FR-AUTH-004 | H |
| **Token Exchange v2** | **FR-AUTH-005** | **I** |
| ECS HA フェイルオーバー | NFR-AVL-004 / NFR-AVL-003 | J |
| ECS service 全滅 → 復旧 | NFR-AVL-004 | K |
| RDS フェイルオーバー | NFR-DR-003 / NFR-AVL-003 | L |
| Infinispan セッション共有 | NFR-AVL-005 | M, N |
| Public ALB IP 制限 | NFR-SEC-017 | O |
| Lambda VPC Authorizer | FR-AUTHZ-007 / NFR-SEC-019 | P |
| CloudWatch 監視 | NFR-OPS-001 / NFR-OPS-004 | Q |
| Auto Scaling | NFR-SCL-005 | R |
| コスト確認 | NFR-COST-002 | S |

---

## 20. 「画面 / API から見える」マッピング表

| 何を見れば何が分かるか | エンドポイント / 画面 | 確認できる要件 |
|---|---|---|
| **OIDC Discovery JSON の issuer** | `https://.../realms/auth-poc/.well-known/openid-configuration` | HTTPS 化 / KC 26.2 起動 / token-exchange feature |
| **JWKS の `alg`** | `https://.../protocol/openid-connect/certs` | NFR-SEC-003 |
| **Access Token のクレーム（jwt.io）** | SPA でログイン後の token | FR-AUTHZ-002 / FR-AUTHZ-003 / FR-AUTHZ-006 |
| **Admin Console の Clients タブ** | `https://admin-alb/admin/master/console/` | FR-ADMIN-004 / FR-AUTH-005（Token Exchange Client） |
| **Admin Console の Users タブ** | 同上 | FR-USER-005 / FR-AUTHZ-002（tenant_id 属性表示） |
| **Realm Settings → Events** | 同上 | FR-ADMIN-007 / FR-ADMIN-008 |
| **ECS Task IP（AZ-1a/1c）** | `aws ecs list-tasks` + describe | NFR-AVL-003 |
| **ALB target health の HEALTHY 表示** | `make kc-status` | NFR-AVL-004 |
| **RDS の MultiAZ = true / SecondaryAZ** | `aws rds describe-db-instances` | NFR-AVL-003 / NFR-DR-003 |
| **CloudWatch Logs の `ISPN000094: cluster view (2)`** | `make kc-logs` | NFR-AVL-005 |
| **CloudWatch Logs の `JGroups Encryption enabled (mTLS)`** | 同上 | NFR-SEC-019 |
| **Auto Scaling target min=2 max=4** | application-autoscaling describe-scalable-targets | NFR-SCL-005 |

---

**次のアクション候補**

1. **Auth0 IdP を realm に投入** → FR-FED-001 / FR-MFA-006 / FR-FED-012 の検証を一気に進める
2. **Brute Force / 監査ログ / SMTP 有効化** → FR-AUTH-011, FR-ADMIN-007, FR-USER-012 のセットで PoC 完成度を上げる
3. **Stage B-1 LDAP 検証** → FR-FED-007 着手（OpenLDAP コンテナで）
4. **Route 53 + ACM カスタムドメイン** → FR-FED-014, NFR-DR-003 の本番準備
5. **WAF + CloudFront** → NFR-SEC-011, NFR-SEC-012 の対応
