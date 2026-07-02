# ADR (Architecture Decision Records) 一覧

アーキテクチャ上の意思決定を記録する。

| ADR | タイトル | ステータス | 日付 |
|-----|---------|----------|------|
| [001](001-cognito-hybrid-for-poc.md) | PoC第1パターンとしてCognitoハイブリッド構成を採用 | Accepted | 2026-03-17 |
| [002](002-lambda-authorizer.md) | 認可方式としてLambda Authorizerを採用 | Accepted | 2026-03-17 |
| [003](003-oidc-client-ts.md) | 認証ライブラリとしてoidc-client-tsを採用 | Accepted | 2026-03-17 |
| [004](004-single-account-poc.md) | 1アカウント2 User Poolでマルチアカウント構成を擬似再現 | Accepted | 2026-03-17 |
| [005](005-user-pool-not-identity-pool.md) | 共通認証基盤にUser Poolを使用（Identity Poolではない） | Accepted | 2026-03-17 |
| [006](006-cognito-vs-keycloak-cost-breakeven.md) | Cognito vs Keycloak コスト損益分岐点の分析 | Proposed | 2026-03-17 |
| [007](007-osaka-auth0-idp-limitation.md) | 大阪リージョンでAuth0 OIDC IdP接続不可の記録 | Accepted | 2026-03-18 |
| [008](008-keycloak-start-dev-for-poc.md) | PoCでKeycloak start-devモードを使用 | Accepted | 2026-03-25 |
| [009](009-mfa-responsibility-by-idp.md) | MFA責任はパスワード管理側に帰属させる | Accepted | 2026-03-28 |
| [010](010-keycloak-private-subnet-vpc-endpoints.md) | Keycloak 環境を Private Subnet + VPC Endpoint 構成へ移行 | Accepted | 2026-04-21 |
| [011](011-auth-frontend-network-design.md) | 認証基盤前段ネットワーク設計（HTTPS / カスタムドメイン / WAF / CloudFront）の統合判断 | Proposed | 2026-04-21 |
| [012](012-vpc-lambda-authorizer-internal-jwks.md) | VPC Lambda Authorizer + Internal ALB による JWKS プライベート化 | Accepted | 2026-04-23 |
| [013](013-cloudfront-waf-ip-restriction.md) | CloudFront + WAF による IP 制限の置き換え戦略 | Proposed | 2026-04-24 |
| [014](014-auth-patterns-scope.md) | 共有認証基盤が対応する認証パターンの範囲 | Proposed | 2026-04-24 |
| [015](015-rhbk-validation-deferred.md) | PoC では RHBK 検証を実施せず本番設計フェーズへ先送り | Proposed | 2026-04-24 |
| [016](016-cognito-feature-tier-selection.md) | Cognito 機能ティア（Lite / Essentials / Plus）の機能マトリクスと選定基準 | Proposed | 2026-05-13 |
| [017](017-multitenant-l2-single-realm.md) | マルチテナント L2（単一 Pool/Realm + 複数 IdP）採用根拠 | Proposed | 2026-06-11 |
| [018](018-user-identifier-3layer-emailless.md) | ユーザー識別子 3 階層戦略（メール非保有 + 顧客独自 ID 対応） | Proposed | 2026-06-12 |
| [019](019-existing-system-migration.md) | 既存システムからの移行戦略（並走 + User Storage SPI キャッシュ移行） | Proposed | 2026-06-12 |
| [020](020-hrd-hint-keys-mixed-login.md) | HRD ヒントキー戦略 + フェデ/ローカル混在 Identifier-First | Proposed | 2026-06-12 |
| [021](021-post-login-landing-ux.md) | Post-login Landing UX（Pre/Post 設計判断 + サービス選択画面 + Sorry） | Proposed | 2026-06-12 |
| [022](022-aws-edge-sorry-control.md) | AWS edge での Sorry 制御パターン（ALB / CloudFront 統合） | Proposed | 2026-06-12 |
| [023](023-servicenow-sp-integration.md) | ServiceNow SP 連携設計（SSO + プロビジョニング方向の選択） | Proposed | 2026-06-15 |
| [024](024-login-screen-architecture-branding.md) | ログイン画面アーキテクチャとブランディング 4 パターン | Proposed | 2026-06-15 |
| [025](025-scim-positioning-and-receive-stance.md) | SCIM 2.0 の位置づけと本基盤の受信スタンス | Proposed | 2026-06-15 |
| [026](026-aal-mismatch-stepup-mfa.md) | AAL 不整合の具体例とステップアップ MFA 設計 | Proposed | 2026-06-15 |
| [027](027-tenant-user-duplication-handling.md) | 同一テナント内ユーザー重複の扱い（7 シナリオ + アカウントリンク戦略） | Proposed | 2026-06-15 |
| [028](028-idpless-customer-local-user-management.md) | IdP なし顧客のローカルユーザー管理 — 4 選択肢の比較 | Proposed | 2026-06-15 |
| [029](029-local-user-categories-and-scope-scenarios.md) | ローカルユーザーの定義 — 利用者カテゴリと範囲シナリオ | Proposed | 2026-06-15 |
| [030](030-minimal-jwt-claim-design.md) | 最小 JWT クレーム設計と接続元アプリ表現 | Proposed | 2026-06-15 |
| [031](031-amr-saml-mfa-evaluation.md) | amr / SAML AuthnContext MFA 評価の統合方針 | Proposed | 2026-06-15 |
| [032](032-ciam-platform-cost-comparison-10m-mau.md) | 10M MAU 規模における CIAM プラットフォーム選定 — Keycloak / Cognito / Entra External ID / Auth0/Okta コスト比較 | Proposed | 2026-06-12 |
| [033](033-keycloak-2tier-broker-idp-architecture.md) | Keycloak 2-tier アーキテクチャ（Broker Keycloak + IdP Keycloak） | Proposed | 2026-06-15 |
| [034](034-adaptive-authentication.md) | Adaptive Authentication（Risk-based 認証）の設計 | Proposed | 2026-06-18 |
| [035](035-identity-threat-detection-response.md) | Identity Threat Detection and Response (ITDR) 設計 | Proposed | 2026-06-18 |
| [036](036-customer-audit-support.md) | Customer Audit Support（縮小：監査ログ保管 + 都度メール対応のみ。Trust Center / Customer Portal はスコープアウト、2026-06-24）| **Scope Reduced** | 2026-06-18 |
| [037](037-shared-responsibility-and-lightweight-iga.md) | IdP Keycloak の Shared Responsibility Model と軽量 IGA 設計 | Proposed | 2026-06-18 |
| [038](038-tenant-admin-portal.md) | ユーザ管理画面（顧客テナント管理者向け Admin UI） | Proposed | 2026-06-18 |
| [039](039-centralized-network-account-edge-layer.md) | **ネットワーク監査アカウント設計（v2、アプリごと独立 CloudFront/WAF + 5 アカウント体系、2026-06-24 全面書き直し）** | Proposed | 2026-06-23 |
| [040](040-pam-jit-admin-privilege-management.md) | PAM / JIT 管理者権限管理 | **Out of Scope**（2026-06-24 — 本基盤対象外、運用体制側で別途検討。代わりに /admin パス保護方針を ADR-039/013 に追記）| 2026-06-23 |
| [041](041-workload-identity-spiffe.md) | Workload Identity 設計（SPIFFE/SPIRE + AWS IAM Roles for Service Accounts） | Proposed | 2026-06-23 |
| [042](042-bot-detection-captcha.md) | Bot Detection / CAPTCHA 設計（Credential Stuffing 対策の多層防御） | Proposed | 2026-06-23 |
| [043](043-accessibility-wcag-2-2-aa.md) | アクセシビリティ設計（WCAG 2.2 AA + JIS X 8341-3 準拠） | Proposed | 2026-06-23 |
| [044](044-tabletop-exercise-incident-drill.md) | Tabletop Exercise / セキュリティインシデント訓練設計 | Proposed | 2026-06-23 |
| [045](045-cryptographic-key-management-strategy.md) | 鍵管理戦略集約（KMS CMK 使い分け + 暗号化境界の統一） | Proposed | 2026-06-23 |
| [046](046-supply-chain-security.md) | ソフトウェアサプライチェーンセキュリティ（SBOM + SLSA + 依存スキャン + PCI DSS §6.4.3） | Proposed | 2026-06-23 |
| [047](047-post-quantum-cryptography-migration-plan.md) | Post-Quantum Cryptography（PQC）マイグレーション計画 | Proposed | 2026-06-23 |
| [048](048-data-portability-subject-rights.md) | データポータビリティ + データ主体権利対応（GDPR Art.15-20 / APPI 第 28-34 条） | Proposed | 2026-06-23 |
| [049](049-vendor-risk-management-tprm.md) | Vendor Risk Management / TPRM（Third-Party Risk Management） | Proposed | 2026-06-23 |
| [050](050-mobile-sdk-native-auth.md) | モバイルアプリ認証設計（AppAuth PKCE + WebAuthn Platform + Push 通知 MFA） | Proposed | 2026-06-23 |
| [051](051-multi-region-dr-failover.md) | Multi-Region DR / Failover 詳細設計（Aurora Global + KMS MRK + Keycloak Realm Replication） | Proposed | 2026-06-23 |
| [052](052-multi-tenant-isolation-rate-limiting.md) | 認証 API への Rate Limit（旧マルチテナント Isolation、2026-06-24 スコープ縮小：認証 API のみ、その他は API プラットフォーム側）| **Scope Reduced** | 2026-06-23 |
| [053](053-observability-strategy.md) | Observability Strategy（OpenTelemetry + SLO + Distributed Tracing + Dashboards） | Proposed | 2026-06-23 |
| [054](054-id-integration-strategy.md) | **ID 統合戦略（現状調査 + 人事 DB を SoT + マッピング DB + 3 段階移行プロセス + メアド不可対応）** | Proposed | 2026-06-24 |
| [055](055-hrd-implementation-method-selection.md) | **HRD 実装方式選定（Phase 1 採用確定 = 方式 A: Custom Authenticator SPI、Java、社内開発 / Phase 2 候補 = 方式 C: URL + CloudFront Function 併用 / §A.6 §A.7 で EKS vs ROSA Classic vs HCP の CI/CD・バージョン追従併記）** | **Accepted (Phase 1)** | 2026-06-25 |
| [056](056-rosa-adoption-decision.md) | **ROSA (Red Hat OpenShift Service on AWS) 採用判断**（Default 不採用 = Upstream OSS + ECS Fargate 維持、FIPS/HIPAA/10M MAU/Red Hat 統合サブスク条件付きで再評価。詳細 input は [rosa-detailed-analysis.md](../reference/rosa-detailed-analysis.md)） | Proposed | 2026-06-25 |
| [058](058-auth-platform-alternatives-comparison.md) | **認証プラットフォーム 代替アーキテクチャ 6 パターン比較検討**（Auth0/Entra External ID/Cognito Multi-Pool/Cognito Single-Pool/Keycloak Multi-Realm/FusionAuth・Ping-ForgeRock を体系的に評価、2 系統独立調査で現状 Keycloak Single Realm + Organizations 維持を再確認、FusionAuth を Phase 2 商用サポート代替候補として提案） | Accepted | 2026-07-02 |
