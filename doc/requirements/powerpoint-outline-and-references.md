# PowerPoint 資料 構成案・参考資料マトリクス

> **目的**: 顧客提示用 PowerPoint 資料の **大項目構成 + 各項目の参考資料一覧**を整理した SSOT。
> **背景**: ヒアリングと並行して資料を準備するため、各章・項目で**どのドキュメントを参照すれば良いか**を一覧化。
> **対象読者**: PowerPoint 作成担当者 / 要件定義レビュー担当者 / 顧客提示担当者
> **更新基準**: 大項目構成の変更時、参考資料追加時

---

## 0. 構成サマリー

| 章 | 項目数 | 主題 | スライド枚数目安 | 時間配分目安 |
|:-:|:-:|---|:-:|:-:|
| 1 | 6 | 全体方針・前提 | 24 | 30 分 |
| 2 | 5 | 接続元・対象 | 20 | 30 分 |
| 3 | 5 | 認証方式 | 20 | 20 分 |
| 4 | 4 | SSO・セッション・ログアウト | 16 | 20 分 |
| 5 | 5 | ユーザー管理・プロビジョニング | 20 | 20 分 |
| 6 | 6 | 非機能要件 | 24 | 30 分 |
| **計** | **31** | - | **~124** | **~150 分（2.5 時間）** |

> ヒアリング 3 回会議計画（[hearing-checklist-excel-main.tsv ヒアリング回 M1/M2/M3](hearing-checklist-excel-main.tsv)）と照合：M1（章 1-2 中心）/ M2（章 3-5 中心）/ M3（章 6 + 最終意思決定）

---

## 1. 全体方針・前提（6 項目）

### 1.1 要件定義の進め方・ヒアリング計画

**概要**: 4 ステージ要件定義プロセス（ヒアリング → 実装可能性評価 → 実装方針定義 → 要件定義書化）、3 回ヒアリング計画、抽出方針（4 軸）。

| 種別 | 参考資料 |
|---|---|
| **内部** | [requirements-process-plan.md](requirements-process-plan.md) §1-7 |
| **内部** | [requirements-hearing-strategy.md](requirements-hearing-strategy.md) §1-3 |
| **内部** | [proposal/00-index.md §0.4 検討事項の抽出方針](proposal/00-index.md) |
| **内部** | [hearing-checklist-excel-readme.md ヒアリング回 M1/M2/M3](hearing-checklist-excel-readme.md) |
| **外部** | [IPA 非機能要求グレード 2018](https://www.ipa.go.jp/sec/softwareengineering/std/ent03-b.html) |

### 1.2 認証基盤で認証するユーザ（P-1〜P-6 / α-δ シナリオ）

**概要**: 利用者カテゴリ 6 分類（基盤運用管理者 / 顧客テナント管理者 / フェデユーザ / ローカル / Break Glass / B2C）+ 採用シナリオ α/β/γ/δ + インフラ運用者 I-1〜I-5。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [00-common.md A-5-2, A-5-3, A-5-4](hearing-script/00-common.md) |
| **hearing-checklist** | §1.1 (A-5-2), §1.2 (A-5-3), §1.3 (A-5-4) |
| **proposal** | [§FR-1.2.0.0 利用者カテゴリ別の分析](proposal/fr/01-auth.md) |
| **内部** | [terms-and-codes-reference.md §2 P-1〜P-6, §3 I-1〜I-5, §4 α-δ シナリオ](terms-and-codes-reference.md) |
| **外部** | [NIST SP 800-63-3 Digital Identity Guidelines](https://pages.nist.gov/800-63-3/) — IAL/AAL/FAL 定義 |

### 1.3 アーキテクチャ方針（完全統合 / ハイブリッド / 完全分散）★再検討の結果

**概要**: 6 つの懸念（SPOF / 過剰品質 / 個別変更困難 等）を踏まえた 4 選択肢比較、業界実例、御社規模での評価、**ハイブリッド推奨**の根拠。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [§C-1.0.B 代替アーキテクチャスタンスの参考図](proposal/common/01-architecture.md) — 3 図並列比較 |
| **proposal** | [§C-1.2.C 代替アーキテクチャの比較](proposal/common/01-architecture.md) — 4 図 + Federation Hub 5 パターン + SSO 動作 |
| **proposal** | [§C-1.2.C.1 Federation Hub の 5 パターンと SPOF 評価](proposal/common/01-architecture.md) |
| **proposal** | [§C-1.2.C.2 「分散 + SSO + SPOF フリー」3 パターン](proposal/common/01-architecture.md) |
| **proposal** | [§C-6 アーキテクチャ判断: ハイブリッド統合の根拠と設計](proposal/common/06-architecture-decision-hybrid.md) |
| **hearing-checklist** | D-6 Identity Broker パターン採用前提合意 |
| **外部** | [KuppingerCole Identity Fabrics 2025](https://www.kuppingercole.com/blog/reinwarth/the-kuppingercole-identity-fabric-2025) |
| **外部** | [Microsoft Federated Identity Pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/federated-identity) |
| **外部** | [OIDC Federation 1.0 (IETF Draft)](https://openid.net/specs/openid-federation-1_0.html) |
| **外部** | [Auth0 Private Cloud Architecture](https://auth0.com/docs/customize/deploy-monitor/private-cloud) |
| **外部** | [Okta Cell-based Architecture](https://www.okta.com/blog/) |

### 1.4 構成概要図（全体 + AWS 構成 + Federation 接続）

**概要**: 全体構成図（§C-1.2）+ 想定 AWS 構成図（§C-1.2.B）+ Federation 接続パターン（コア↔エッジ）+ Bearer JWT/JWKS 動作（§C-1.2.D）。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [§C-1.2 全体アーキテクチャ + 構成図](proposal/common/01-architecture.md) |
| **proposal** | [§C-1.2.A 認証フロー・接続フロー図のインデックス](proposal/common/01-architecture.md) |
| **proposal** | [§C-1.2.B 想定 AWS 構成図（統合 + マーカー版）](proposal/common/01-architecture.md) |
| **proposal** | [§C-1.2.D Bearer JWT / JWKS / 認可フロー種別 6 種](proposal/common/01-architecture.md) |
| **proposal** | [§C-6 §6.1 全体構造 / §6.3.3 AWS アカウント配置 3 オプション / §6.4 Federation 接続](proposal/common/06-architecture-decision-hybrid.md) |
| **内部** | [common/keycloak-network-architecture.md](../common/keycloak-network-architecture.md) |
| **外部** | [AWS Multi-Account Strategy (Control Tower)](https://aws.amazon.com/controltower/) |
| **外部** | [Keycloak Deployment Guide](https://www.keycloak.org/server/configuration-production) |

### 1.5 製品選定（Cognito vs Keycloak OSS vs RHBK + ティア選定）

**概要**: プラットフォーム選定軸（規模 / 機能 / 規制）、Cognito Hard Limit、Cognito ティア（Lite/Essentials/Plus）、Keycloak OSS vs RHBK、規模戦略。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [11-operations.md D-1 プラットフォーム選定](hearing-script/11-operations.md) |
| **hearing-checklist** | §2.8 (D-1), §3.2 (B-100 列 S K1-K8 = Knockout 条件) |
| **proposal** | [§C-2 プラットフォーム選定軸](proposal/common/02-platform.md) |
| **proposal** | [§C-2.4.A 規模軸（A-15 顧客数連動）](proposal/common/02-platform.md) |
| **proposal** | [§C-1.5 規模スケーリング戦略（1500-3000 顧客企業）](proposal/common/01-architecture.md) |
| **内部** | [ADR-016 Cognito ティア選定基準](../adr/016-cognito-feature-tier-selection.md) |
| **内部** | [ADR-017 Keycloak OSS vs RHBK](../adr/017-keycloak-oss-vs-rhbk-selection.md) |
| **内部** | [poc-summary-evaluation.md PoC 結果](poc-summary-evaluation.md) |
| **内部** | [reference/cognito-knockout-conditions.md](../reference/cognito-knockout-conditions.md) |
| **外部** | [AWS Cognito Service Quotas](https://docs.aws.amazon.com/cognito/latest/developerguide/limits.html) |
| **外部** | [Cognito Pricing](https://aws.amazon.com/cognito/pricing/) |
| **外部** | [Red Hat Build of Keycloak](https://access.redhat.com/products/red-hat-build-of-keycloak) |

### 1.6 移行方針・リリース計画

**概要**: 既存認証からの移行戦略（段階移行 / 並行稼働 / 即時切替 / 維持）+ パスワードハッシュ移行 + リリーススケジュール + ドメイン変更計画 + ユーザー周知。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [00-common.md A-5, A-10](hearing-script/00-common.md), [11-operations.md D-2, D-5](hearing-script/11-operations.md), [10-security-compliance.md C-204-4](hearing-script/10-security-compliance.md), [02-idp-federation.md B-615/616/617](hearing-script/02-idp-federation.md) |
| **hearing-checklist** | §2.7 (A-5, A-10, D-2, D-5), §3.3 (C-204-4) |
| **proposal** | [§NFR-9 移行性](proposal/nfr/09-migration.md), [§C-4 スケジュール](proposal/common/04-schedule.md), [§FR-2.3.2.B 既存システムからの移行時のエンドユーザー影響](proposal/fr/02-federation.md) |
| **内部** | migration-strategy.md（予定）|

---

## 2. 接続元・対象（5 項目）

### 2.1 規模・規制・コンプライアンス

**概要**: MAU 規模 + 顧客企業数（A-15）+ 業界規制（FIPS / SOC2 / PCI DSS / FFIEC / HIPAA / GDPR）+ データ所在地。**Cognito vs Keycloak / OSS vs RHBK 選定への直接インパクト**。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [00-common.md A-1〜A-4, A-7, A-12, A-15](hearing-script/00-common.md), [10-security-compliance.md C-201, C-202, C-209](hearing-script/10-security-compliance.md) |
| **hearing-checklist** | §2.1 (A-1/2/3/4/7/12/15), §2.2 (A-8/9, C-201/202/209) |
| **proposal** | [§NFR-3 拡張性](proposal/nfr/03-scalability.md), [§NFR-7 コンプライアンス](proposal/nfr/07-compliance.md), [§C-1.5 規模スケーリング戦略](proposal/common/01-architecture.md) |
| **内部** | [ADR-006 Cognito vs Keycloak コスト損益分岐](../adr/006-cognito-vs-keycloak-cost-breakeven.md) |
| **外部** | [NIST SP 800-63B Rev 4](https://pages.nist.gov/800-63-4/sp800-63b.html) |
| **外部** | [SOC 2 Trust Services Criteria](https://www.aicpa-cima.com/topic/audit-assurance/audit-and-assurance-greater-than-soc-2) |
| **外部** | [FFIEC IT Handbook - Authentication](https://ithandbook.ffiec.gov/) |
| **外部** | [FISC 安全対策基準](https://www.fisc.or.jp/) |

### 2.2 顧客 IdP 一覧（マスター表 B）

**概要**: 事業者 IdP + 顧客企業 IdP の統合表。製品（Entra/Okta/Auth0/HENNGE/AD 等）/ プロトコル（OIDC/SAML/LDAP）/ SCIM 対応 / テナント分離希望。**LDAP 直結 = Keycloak 必須化**。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [02-idp-federation.md マスター表 B](hearing-script/02-idp-federation.md), B-200, B-609, B-615/616/617 |
| **hearing-checklist** | §3.1 (B-200), A-13, A-6 |
| **proposal** | [§FR-2.1 IdP 接続種別](proposal/fr/02-federation.md), [§C-1.0.A 本基盤のアーキテクチャスタンス](proposal/common/01-architecture.md) |
| **内部** | [common/identity-broker-multi-idp.md](../common/identity-broker-multi-idp.md) |
| **内部** | [hearing-checklist-excel-master-b.tsv テンプレ](hearing-checklist-excel-master-b.tsv) |
| **外部** | [Microsoft Entra ID Documentation](https://learn.microsoft.com/en-us/entra/) |
| **外部** | [Okta Identity Cloud](https://www.okta.com/products/) |
| **外部** | [HENNGE One](https://hennge.com/jp/) |
| **外部** | [AD FS Deployment Guide](https://learn.microsoft.com/en-us/windows-server/identity/ad-fs/) |

### 2.3 接続アプリ・システム一覧（マスター表 C）

**概要**: アプリ・システムの種別（SPA/SSR/モバイル/M2M/CLI/Backend/SAML SP）+ 認証方式 + JWT 検証場所 + 特殊要件フラグ K1〜K8（Cognito Knockout 条件）+ 既存ローカル認証。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [01-auth-flow.md マスター表 C + 補足 1〜5](hearing-script/01-auth-flow.md), B-100, K1〜K8 |
| **hearing-checklist** | §3.2 (B-100) |
| **proposal** | [§FR-1.1 認証フロー / Grant Type](proposal/fr/01-auth.md) |
| **内部** | [common/auth-patterns.md](../common/auth-patterns.md), [common/system-design-patterns.md](../common/system-design-patterns.md) |
| **内部** | [reference/cognito-knockout-conditions.md K1〜K11](../reference/cognito-knockout-conditions.md) |
| **内部** | [hearing-checklist-excel-master-c.tsv テンプレ](hearing-checklist-excel-master-c.tsv) |
| **外部** | [OAuth 2.1 Draft](https://datatracker.ietf.org/doc/draft-ietf-oauth-v2-1/) |
| **外部** | [FAPI 2.0 Security Profile](https://openid.net/specs/fapi-2_0-security-02.html) |
| **外部** | RFC: [6749 OAuth 2.0](https://datatracker.ietf.org/doc/html/rfc6749) / [7519 JWT](https://datatracker.ietf.org/doc/html/rfc7519) / [8628 Device Code](https://datatracker.ietf.org/doc/html/rfc8628) / [8693 Token Exchange](https://datatracker.ietf.org/doc/html/rfc8693) / [8705 mTLS](https://datatracker.ietf.org/doc/html/rfc8705) / [9449 DPoP](https://datatracker.ietf.org/doc/html/rfc9449) |
| **外部** | [Curity / Duende BFF gold standard 2025](https://curity.io/resources/learn/the-bff-pattern/) |

### 2.4 マルチテナント設計（分離粒度 + 規模戦略 + Organization 機能 + 特殊顧客）

**概要**: テナント分離粒度 L1/L2/L3（共有 DB+tenant_id / 論理分離 / 物理分離）+ 1500-3000 顧客の規模戦略 + Keycloak Organization（26+）+ 物理分離が必要な特殊顧客。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [03-authz-jwt.md B-306](hearing-script/03-authz-jwt.md), [06-multitenancy.md B-602, B-606, B-607, B-608, B-611, B-606-2/3/4](hearing-script/06-multitenancy.md) |
| **hearing-checklist** | §2.3 (B-306, B-602, B-603, B-606 系, B-607, B-608, B-611) |
| **proposal** | [§FR-2.3 マルチテナント運用](proposal/fr/02-federation.md), [§FR-2.3.A アーキテクチャ判断](proposal/fr/02-federation.md), [§C-1.4 物理分離レベル 6 段階](proposal/common/01-architecture.md), [§C-1.5 規模スケーリング戦略](proposal/common/01-architecture.md) |
| **内部** | [ADR-014 認証パターン範囲](../adr/014-auth-patterns-scope.md) |
| **外部** | [Keycloak Organizations 26+](https://www.keycloak.org/docs/latest/server_admin/#_managing-organizations) |
| **外部** | [AWS Cognito Multi-tenant patterns](https://docs.aws.amazon.com/cognito/latest/developerguide/multi-tenant-application-best-practices.html) |
| **外部** | [Slack Enterprise Grid Architecture](https://api.slack.com/enterprise/grid) |

### 2.5 顧客別ブランディング（ログイン画面・URL）

**概要**: 軸 1 アプリ別 × 軸 2 顧客別の 4 パターン（A / A' / B / C）+ カスタマイズレベル L1-L3 vs L4-L8 + Custom Domain + 動的差替実装責務。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [00-common.md A-11, A-11-α, A-11-2, A-11-3](hearing-script/00-common.md), [02-idp-federation.md B-208](hearing-script/02-idp-federation.md), [06-multitenancy.md B-612](hearing-script/06-multitenancy.md), [07-logout-session.md B-703-1, B-703-3](hearing-script/07-logout-session.md) |
| **hearing-checklist** | §1.5 (A-11/A-11-α), §3.4 (A-11-2/3, B-208, B-612, B-703-1/3) |
| **proposal** | [§FR-2.3.3.A 画面所在マトリクスとカスタマイズ 3 パターン](proposal/fr/02-federation.md), [§FR-8.3 管理機能](proposal/fr/08-admin.md) |
| **内部** | [common/branding-strategy-evidence.md](../common/branding-strategy-evidence.md) |
| **外部** | [Auth0 Universal Login](https://auth0.com/docs/authenticate/login/auth0-universal-login) |
| **外部** | [Cognito Managed Login Branding](https://docs.aws.amazon.com/cognito/latest/developerguide/managed-login-brandings.html) |
| **外部** | [Microsoft Entra B2C Custom Branding](https://learn.microsoft.com/en-us/azure/active-directory-b2c/customize-ui-with-html) |

---

## 3. 認証方式（5 項目）

### 3.1 ログイン方式・画面設定

**概要**: IdP 選択 UX（HRD / セレクター / 組織固有 URL）+ Custom Domain + ログイン画面の所在（アプリ側 vs 認証基盤側）。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [06-multitenancy.md B-601, B-610](hearing-script/06-multitenancy.md), [02-idp-federation.md B-208](hearing-script/02-idp-federation.md) |
| **hearing-checklist** | §4.4 (B-601), §3.4 (B-208), §3.5 (B-610) |
| **proposal** | [§FR-2.3.3 ログイン UX](proposal/fr/02-federation.md), [§FR-2.3.3.C Keycloak ハイブリッド HRD + 組織固有 URL](proposal/fr/02-federation.md) |
| **外部** | [IETF / Curity BFF gold standard 2025](https://curity.io/resources/learn/the-bff-pattern/) |
| **外部** | [Home Realm Discovery (Shibboleth)](https://shibboleth.atlassian.net/wiki/spaces/SP3/pages/2065335462/HomeRealmDiscovery) |

### 3.2 MFA 要件 + ステップアップ認証

**概要**: MFA 必須範囲（全員 / 管理者のみ / 条件付き）+ MFA 方式（TOTP / WebAuthn / SMS / Email / ハードウェアキー）+ AAL レベル + 条件付き MFA 判定軸 + ステップアップ認証（RFC 9470）+ 外部 IdP MFA 信頼度。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [05-mfa.md B-501〜B-509](hearing-script/05-mfa.md), [10-security-compliance.md C-210〜C-216](hearing-script/10-security-compliance.md) |
| **hearing-checklist** | §2.6 (B-501, B-506, B-508, C-210), §4.3 (B-502, B-503, B-505, B-507, C-211〜C-216) |
| **proposal** | [§FR-3 MFA](proposal/fr/03-mfa.md), [§FR-3.3 ステップアップ認証](proposal/fr/03-mfa.md), [§FR-2.2.3 MFA 重複回避](proposal/fr/02-federation.md) |
| **内部** | [ADR-009 MFA 責任分担 IdP 別](../adr/009-mfa-responsibility-by-idp.md) |
| **外部** | [NIST SP 800-63B Rev 4 §5 MFA](https://pages.nist.gov/800-63-4/sp800-63b.html) |
| **外部** | [RFC 9470 OAuth 2.0 Step-up Authentication Challenge Protocol](https://datatracker.ietf.org/doc/html/rfc9470) |
| **外部** | [FIDO Alliance Passkey Specification](https://fidoalliance.org/passkeys/) |
| **外部** | [WebAuthn Level 3 (W3C)](https://www.w3.org/TR/webauthn-3/) |
| **外部** | 業界調査「Enterprise Passkey Adoption 2024」(87% deploy/pilot) |

### 3.3 ローカル認証パスワードポリシー

**概要**: パスワードポリシー（最小長 / 複雑性 / 履歴 / 有効期限）+ NIST SP 800-63B Rev 4 準拠方針 + 既存パスワードハッシュ移行。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [10-security-compliance.md C-204, C-204-2, C-204-3, C-204-4](hearing-script/10-security-compliance.md) |
| **hearing-checklist** | §4.5 (C-204, C-204-2/3), §3.3 (C-204-4) |
| **proposal** | [§FR-1.2 パスワード・ローカルユーザー管理](proposal/fr/01-auth.md) |
| **外部** | [NIST SP 800-63B Rev 4 §5.1.1 Memorized Secrets](https://pages.nist.gov/800-63-4/sp800-63b.html#sec5.1) |
| **外部** | [HaveIBeenPwned API（侵害クレデンシャル DB）](https://haveibeenpwned.com/API/v3) |
| **外部** | [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html) |

### 3.4 アカウントロック・侵害検出

**概要**: アカウントロック詳細設定（連続失敗回数 / ロック時間）+ 侵害クレデンシャル検出（HaveIBeenPwned / Cognito Compromised Credentials）+ Cognito Plus ティア要否。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [10-security-compliance.md C-205, C-205-2](hearing-script/10-security-compliance.md) |
| **hearing-checklist** | §4.5 (C-205, C-205-2) |
| **proposal** | [§FR-1.2 パスワード・ローカルユーザー管理](proposal/fr/01-auth.md) |
| **内部** | [ADR-016 Cognito ティア選定（Plus 機能要否）](../adr/016-cognito-feature-tier-selection.md) |
| **外部** | [NIST SP 800-63B Rev 4 §5.2.2 Rate Limiting](https://pages.nist.gov/800-63-4/sp800-63b.html) |
| **外部** | [OWASP Brute Force Attack Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html#protect-against-automated-attacks) |

### 3.5 認可スタンス + JWT クレーム設計 + API 認可フロー

**概要**: 認可の 2 つの意味（意味 A vs 意味 B）+ JWT 必須クレーム + 認可粒度 + Bearer JWT / JWKS の標準動作 + Token Introspection 代替案 + Token Exchange（K1）。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [03-authz-jwt.md B-301, B-302, B-305](hearing-script/03-authz-jwt.md), [01-auth-flow.md マスター表 C 補足 2 K1 Token Exchange](hearing-script/01-auth-flow.md) |
| **hearing-checklist** | §4.2 (B-301, B-302, B-305) |
| **proposal** | [§FR-6.0.A 認可スタンス](proposal/fr/06-authz.md), [§FR-6.1.A 最小クレーム設計](proposal/fr/06-authz.md), [§C-1.2.D Bearer JWT / JWKS / 認可フロー 6 種](proposal/common/01-architecture.md) |
| **内部** | [common/authz-architecture-design.md](../common/authz-architecture-design.md) |
| **内部** | [terms-and-codes-reference.md §16 認可の 2 つの意味, §20 認可フロー 6 種, §21 Bearer JWT/JWKS](terms-and-codes-reference.md) |
| **外部** | RFC: [6750 Bearer Token](https://datatracker.ietf.org/doc/html/rfc6750) / [7519 JWT](https://datatracker.ietf.org/doc/html/rfc7519) / [7517 JWKS](https://datatracker.ietf.org/doc/html/rfc7517) / [7515 JWS](https://datatracker.ietf.org/doc/html/rfc7515) / [7662 Token Introspection](https://datatracker.ietf.org/doc/html/rfc7662) / [8693 Token Exchange](https://datatracker.ietf.org/doc/html/rfc8693) |
| **外部** | [OAuth 2.0 Threat Model (RFC 6819)](https://datatracker.ietf.org/doc/html/rfc6819) |

---

## 4. SSO・セッション・ログアウト（4 項目）

### 4.1 SSO 方針 + セッション信頼レベル

**概要**: SSO で繋ぐシステム範囲 + クロス IdP SSO 信頼レベル L1〜L4 + 顧客 / IdP / アプリ別差別化 + 規制業種向け L3 オプション + max_age 制約 + 外部 IdP SSO セッション TTL 尊重。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [05-mfa.md B-509](hearing-script/05-mfa.md), [08-sso-details.md B-801, B-801-1/2/3, B-802, B-802-2, B-803](hearing-script/08-sso-details.md) |
| **hearing-checklist** | §2.5 (B-509, B-801, B-801-1/2/3, B-803), §4.4 (B-802, B-802-2) |
| **proposal** | [§FR-4 SSO](proposal/fr/04-sso.md), [§FR-4.2 クロス IdP SSO](proposal/fr/04-sso.md), [§FR-5.2 セッション TTL](proposal/fr/05-logout-session.md) |
| **外部** | [OIDC Core 1.0 §3.2.2.10 max_age](https://openid.net/specs/openid-connect-core-1_0.html#AuthRequest) |
| **外部** | [SAML 2.0 SSO Profile](https://docs.oasis-open.org/security/saml/v2.0/saml-profiles-2.0-os.pdf) |

### 4.2 ログアウト方針（4 レイヤー L1〜L4）

**概要**: デフォルトのログアウトレイヤー L1〜L4 + フェデ連動ログアウト要否 + ログアウト後リダイレクト先（全体方針 / 種類別飛び先 / 後処理 / 強制ログアウト時 / テナント別カスタムランディング）+ ユーザー自身のセッション管理 UI。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [07-logout-session.md B-701, B-702, B-703, B-703-2/4/5, B-705, B-706](hearing-script/07-logout-session.md) |
| **hearing-checklist** | §2.5 (B-701, B-702, B-703), §3.4 (B-703-1/3), §4.4 (B-703-2/4/5, B-705, B-706) |
| **proposal** | [§FR-5.1 ログアウト 4 レイヤー](proposal/fr/05-logout-session.md), [§FR-5.3 強制ログアウト](proposal/fr/05-logout-session.md) |
| **外部** | [OIDC RP-Initiated Logout 1.0](https://openid.net/specs/openid-connect-rpinitiated-1_0.html) |
| **外部** | [OIDC Front-Channel Logout 1.0](https://openid.net/specs/openid-connect-frontchannel-1_0.html) |

### 4.3 SLO + Back-Channel Logout + Token Revocation

**概要**: Single Logout 必須範囲 + Back-Channel Logout（RFC 8417、K7）+ Access Token 即時 Revocation（K8）+ トークン TTL + アイドルタイムアウト + 絶対経過タイムアウト + CAEP（将来）。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [05-mfa.md B-504 → K7](hearing-script/05-mfa.md), [07-logout-session.md B-704 → K8](hearing-script/07-logout-session.md), [01-auth-flow.md マスター表 C 補足 2 K7/K8](hearing-script/01-auth-flow.md), [10-security-compliance.md C-206, C-206-2/3, C-217](hearing-script/10-security-compliance.md) |
| **hearing-checklist** | §3.2 (B-100 列 S K7/K8), §4.4 (C-206, C-217), §5.3 (C-206-2/3) |
| **proposal** | [§FR-5.1 SLO](proposal/fr/05-logout-session.md), [§FR-5.3 Revocation](proposal/fr/05-logout-session.md), [§FR-5.4 CAEP 将来](proposal/fr/05-logout-session.md) |
| **外部** | [RFC 8417 Security Event Token / Back-Channel Logout](https://datatracker.ietf.org/doc/html/rfc8417) |
| **外部** | [OIDC Back-Channel Logout 1.0](https://openid.net/specs/openid-connect-backchannel-1_0.html) |
| **外部** | [RFC 7009 OAuth 2.0 Token Revocation](https://datatracker.ietf.org/doc/html/rfc7009) |
| **外部** | [Shared Signals Framework / CAEP (OpenID)](https://openid.net/wg/sharedsignals/) |

### 4.4 Federation 接続パターン（コア↔エッジ）

**概要**: 二重 Federation（Customer IdP → Core → Edge）の動作 + Token Exchange 代替案 + Federation-Friendly 設計原則 + Edge アプリの SSO 維持メカニズム。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [§C-6 §6.4 Federation 接続パターン](proposal/common/06-architecture-decision-hybrid.md), [§C-1.2.C.1 Federation Hub の 5 パターン](proposal/common/01-architecture.md), [§C-1.2.C.2 「分散 + SSO + SPOF フリー」3 パターン](proposal/common/01-architecture.md) |
| **外部** | [RFC 8693 Token Exchange](https://datatracker.ietf.org/doc/html/rfc8693) |
| **外部** | [OIDC Federation 1.0 (IETF)](https://openid.net/specs/openid-federation-1_0.html) |
| **外部** | [eduGAIN Federation Documentation](https://edugain.org/) |
| **外部** | [Microsoft Entra B2B Cross-Tenant](https://learn.microsoft.com/en-us/entra/external-id/cross-tenant-access-settings-b2b-collaboration) |
| **外部** | [Shibboleth Federation Operator Guide](https://shibboleth.atlassian.net/wiki/spaces/IDP30/overview) |

---

## 5. ユーザー管理・プロビジョニング（5 項目）

### 5.1 フェデユーザ同期（JIT / SCIM / Webhook）

**概要**: JIT プロビジョニング採否 + SCIM 採否（顧客選択制 / 必須）+ 既存ユーザー初期投入方法（バルク / SCIM / JIT 任せ）+ 退職反映 SLA。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [04-user-management.md B-401, B-403](hearing-script/04-user-management.md), [06-multitenancy.md B-605-3 退職反映 SLA](hearing-script/06-multitenancy.md) |
| **hearing-checklist** | §2.4 (B-401, B-403), §3.5 (B-605-3) |
| **proposal** | [§FR-7.4 SCIM プロビジョニング](proposal/fr/07-user.md), [§FR-7.4.0 SCIM の位置づけと本基盤のスタンス](proposal/fr/07-user.md), [§FR-2.2.1 JIT プロビジョニング](proposal/fr/02-federation.md), [§FR-2.2.1.A 同一テナント内ユーザー重複](proposal/fr/02-federation.md) |
| **外部** | [SCIM 2.0 (RFC 7644)](https://datatracker.ietf.org/doc/html/rfc7644) |
| **外部** | [Keycloak SCIM Plugin](https://github.com/Captain-P-Goldfish/scim-for-keycloak) |
| **外部** | [AWS Cognito Bulk Import](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-using-import-tool.html) |

### 5.2 フェデユーザ権限（デフォルト権限）

**概要**: 新規作成時のデフォルト権限・ロール（JIT / SCIM / バルク共通）+ 業界推奨「最小権限」+ 顧客側で個別指定の許容。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [04-user-management.md B-401-2](hearing-script/04-user-management.md) |
| **hearing-checklist** | §2.4 (B-401-2) |
| **proposal** | [§FR-2.2.1 新規作成時のデフォルト権限](proposal/fr/02-federation.md) |
| **外部** | [NIST Least Privilege Principle (NIST SP 800-53)](https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final) |

### 5.3 フェデユーザ通知（Webhook）

**概要**: 共通基盤 → 外部アプリへの Webhook 通知（user.created / deleted / mfa.enrolled 等）+ 通知先（CloudWatch / SIEM / Slack / メール）+ ユーザー作成イベントの通知契機。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [04-user-management.md B-405, B-401-3](hearing-script/04-user-management.md) |
| **hearing-checklist** | §2.4 (B-405, B-401-3) |
| **proposal** | [§FR-9.3 Webhook](proposal/fr/09-integration.md), [§FR-9.3.0 Webhook の役割と SCIM/JIT との違い](proposal/fr/09-integration.md) |
| **外部** | [RFC 8417 Security Event Token](https://datatracker.ietf.org/doc/html/rfc8417) |
| **外部** | [Webhook 業界標準（Stripe）](https://stripe.com/docs/webhooks) |
| **外部** | [GitHub Webhooks API](https://docs.github.com/en/webhooks-and-events/webhooks) |

### 5.4 アカウント重複・リンク方針

**概要**: 同一テナント内ユーザー重複の想定 + 重複検出時の挙動（自動リンク / Email OTP / 既存パスワード再認証 / エラー停止）+ 突合せキー（email / immutable sub / 雇用 ID）+ アカウントリンクトリガー + IdP 切替時のユーザー連続性。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [04-user-management.md B-406, B-407, B-408, B-409, B-410](hearing-script/04-user-management.md) |
| **hearing-checklist** | §2.4 (B-406/407/409/410), §3.5 (B-408) |
| **proposal** | [§FR-2.2.1.A 同一テナント内ユーザー重複](proposal/fr/02-federation.md) |
| **内部** | project_account_linking_investigation.md（Cognito 3 落とし穴 / Keycloak FBL 認証器）|
| **外部** | [OWASP Identity Linking](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html) |
| **外部** | [Microsoft Account Linking Best Practices](https://learn.microsoft.com/en-us/entra/identity/users/users-restrict-guest-permissions) |

### 5.5 属性マッピング・更新

**概要**: 顧客 IdP 命名差異への対応 + 実属性名サンプル取得手順 + 属性更新タイミング（Force / 初回 JIT のみ / 別途トリガー）+ 属性ごとの Source of Truth + HRD 解決ルール。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [06-multitenancy.md B-604, B-604-2, B-605, B-605-2, B-610](hearing-script/06-multitenancy.md) |
| **hearing-checklist** | §3.5 (B-604, B-604-2, B-605, B-605-2, B-610) |
| **proposal** | [§FR-2.2.2 属性マッピング](proposal/fr/02-federation.md), [§FR-2.2.4 属性ライフサイクル設計](proposal/fr/02-federation.md) |
| **外部** | [SAML Attribute Mapping (Shibboleth)](https://shibboleth.atlassian.net/wiki/spaces/IDP30/pages/2065335462/AttributeMapping) |
| **外部** | [OIDC Standard Claims](https://openid.net/specs/openid-connect-core-1_0.html#StandardClaims) |
| **外部** | [Microsoft Entra B2B Claims Mapping](https://learn.microsoft.com/en-us/entra/identity-platform/saml-claims-customization) |

---

## 6. 非機能要件（6 項目）

### 6.1 可用性・SLA・DR

**概要**: SLA 目標（99.9% / 99.95% / 99.99%）+ RTO + RPO + フェイルオーバー方式 + 計画メンテナンス窓 + Multi-Region Active-Active vs Multi-AZ。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [09-availability.md C-101〜C-104, C-107](hearing-script/09-availability.md) |
| **hearing-checklist** | §5.1 (C-101〜104, C-107) |
| **proposal** | [§NFR-1 可用性](proposal/nfr/01-availability.md), [§NFR-5 DR](proposal/nfr/05-dr.md), [§C-6 §6.2.4 SLA 別必要構成](proposal/common/06-architecture-decision-hybrid.md) |
| **内部** | DR コスト比較表 |
| **外部** | [AWS Multi-Region Best Practices](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html) |
| **外部** | [Keycloak High Availability Guide](https://www.keycloak.org/server/concepts-cluster) |
| **外部** | [IPA 非機能要求グレード A. 可用性](https://www.ipa.go.jp/sec/softwareengineering/std/ent03-b.html) |

### 6.2 性能・スケール

**概要**: 認証応答時間目標（P95 / P99）+ ピーク時想定 + Cognito Hard Limit + Keycloak DB チューニング + 規模スケーリング戦略（1500-3000 顧客）。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [09-availability.md C-105, C-106](hearing-script/09-availability.md) |
| **hearing-checklist** | §5.2 (C-105, C-106) |
| **proposal** | [§NFR-2 性能](proposal/nfr/02-performance.md), [§NFR-3 拡張性](proposal/nfr/03-scalability.md), [§C-1.5 規模スケーリング戦略](proposal/common/01-architecture.md) |
| **内部** | [ADR-006 コスト損益分岐](../adr/006-cognito-vs-keycloak-cost-breakeven.md) |
| **外部** | [AWS Cognito Service Quotas (Hard Limits)](https://docs.aws.amazon.com/cognito/latest/developerguide/limits.html) |
| **外部** | [Keycloak Performance Tuning](https://www.keycloak.org/server/configuration-production) |

### 6.3 セキュリティ NFR

**概要**: 監査ログ保存期間（SOC 2 / PCI DSS / HIPAA / FFIEC / GDPR）+ セッションタイムアウト（アイドル / 絶対経過）+ ペネトレーションテスト + 暗号化 + ゼロトラスト。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [10-security-compliance.md C-203, C-206-2, C-206-3, C-208](hearing-script/10-security-compliance.md) |
| **hearing-checklist** | §5.3 (C-203, C-206-2/3, C-208) |
| **proposal** | [§NFR-4 セキュリティ](proposal/nfr/04-security.md), [§FR-5.2 セッション TTL](proposal/fr/05-logout-session.md) |
| **内部** | [common/jwks-public-exposure.md](../common/jwks-public-exposure.md) |
| **外部** | [OWASP Top 10 (2021)](https://owasp.org/Top10/) |
| **外部** | [NIST SP 800-53 Rev 5](https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final) |
| **外部** | [IPA 非機能要求グレード E. セキュリティ](https://www.ipa.go.jp/sec/softwareengineering/std/ent03-b.html) |
| **外部** | [CIS Controls v8](https://www.cisecurity.org/controls) |

### 6.4 運用（監視・変更管理）

**概要**: 監視ツール（CloudWatch / Datadog / Grafana / Splunk）+ バージョンアップ方針（LTS / 最新追従）+ 変更管理プロセス（Git PR ベース）+ 緊急対応 Fast Track ルート。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [11-operations.md C-304, C-305, C-306](hearing-script/11-operations.md) |
| **hearing-checklist** | §5.4 (C-304, C-305, C-306) |
| **proposal** | [§NFR-6 運用](proposal/nfr/06-operations.md), [§NFR-6.4 構成変更プロセス](proposal/nfr/06-operations.md) |
| **外部** | [AWS Well-Architected Framework - Operational Excellence](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/welcome.html) |
| **外部** | [IPA 非機能要求グレード C. 運用・保守性](https://www.ipa.go.jp/sec/softwareengineering/std/ent03-b.html) |

### 6.5 運用体制（24/7 サポート・人員）

**概要**: サポート体制（24/7 / 営業時間 / 不要）+ Red Hat 利用実績 + RHBK サブスクリプション要否 + 専任 / 兼任 / 外部委託の選択。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [11-operations.md C-301, C-302, D-3](hearing-script/11-operations.md) |
| **hearing-checklist** | §5.4 (C-301, C-302), §2.8 (D-3) |
| **proposal** | [§C-2.3 運用体制](proposal/common/02-platform.md), [§NFR-6 運用](proposal/nfr/06-operations.md) |
| **外部** | [Red Hat Build of Keycloak Subscription](https://access.redhat.com/products/red-hat-build-of-keycloak) |
| **外部** | [AWS Enterprise Support](https://aws.amazon.com/premiumsupport/plans/enterprise/) |

### 6.6 コスト・予算

**概要**: 3 年 TCO（Cognito MAU 課金 vs Keycloak 自前運用）+ RHBK サブスク予算（$15K〜90K/年）+ 年間予算枠 + ティア別コスト試算。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [11-operations.md C-303, D-4](hearing-script/11-operations.md) |
| **hearing-checklist** | §5.5 (C-303), §2.8 (D-4) |
| **proposal** | [§NFR-8 コスト](proposal/nfr/08-cost.md), [§C-2.3 コスト比較・TCO](proposal/common/02-platform.md) |
| **内部** | [ADR-006 Cognito vs Keycloak コスト損益分岐 (175K MAU)](../adr/006-cognito-vs-keycloak-cost-breakeven.md) |
| **内部** | cost-estimation.md（予定）|
| **外部** | [AWS Cognito Pricing](https://aws.amazon.com/cognito/pricing/) |
| **外部** | [Red Hat Build of Keycloak Subscription Pricing](https://access.redhat.com/products/red-hat-build-of-keycloak) |

---

## 7. PowerPoint スライド構成テンプレ

各大項目を以下の **基本テンプレ 3-5 スライド** で構成すると密度がバランスする：

| スライド種別 | 内容 | 想定枚数 |
|---|---|---|
| **概要スライド** | 何を決めるか / なぜ重要か / 関連項目 | 1 枚 |
| **選択肢提示** | A/B/C 案の比較表（業界標準 + 本基盤推奨）| 1-2 枚 |
| **業界標準・参考事例** | KuppingerCole / Microsoft / Auth0 等の引用 | 1 枚（必要時）|
| **本基盤での推奨** | ベースライン + 理由 + 例外条件 | 1 枚 |
| **ヒアリング質問** | 顧客に確認する項目リスト | 1 枚 |

### スライド作成のコツ

| Tips | 内容 |
|---|---|
| **§の対応を明示** | 各スライド左下に「§FR-2.3」「B-306」等の対応 ID を小さく表示、参照しやすくする |
| **Mermaid 図のスクショ** | proposal 内の Mermaid 図を PNG/SVG で書き出して貼る（編集可能な PowerPoint Shape は手動）|
| **本基盤の推奨をハイライト** | ⭐ マークで「本基盤推奨」を明示、議論時の合意ポイントが分かりやすい |
| **業界実例を 1-2 枚追加** | 「Slack / Auth0 / Microsoft はこの設計」と示すと顧客の納得度向上 |
| **比較表は最大 5 列まで** | スライドで読める列数は 4-5 が限界、それ以上は分割 |

---

## 8. ヒアリング会議への適用

### 3 回ヒアリング計画との対応

| 章 | ヒアリング回 | 含まれる質問数（hearing-checklist 基準） |
|---|---|---:|
| 章 1 全体方針・前提（うち §1.1〜§1.6）| **M1**（前提合意 + 規模・規制）| 約 18 件 |
| 章 2 接続元・対象 | **M1**（マスター表 + 規制範囲）| 約 25 件 |
| 章 3 認証方式 | **M2**（機能要件詳細）| 約 22 件 |
| 章 4 SSO・セッション・ログアウト | **M2 + M3**（M2 = 方針、M3 = 技術仕様）| 約 20 件 |
| 章 5 ユーザー管理・プロビジョニング | **M2**（機能要件詳細）| 約 18 件 |
| 章 6 非機能要件 | **M3**（NFR + 運用 + 意思決定）| 約 18 件 |

### 想定スケジュール

| 回 | スライド範囲 | 時間 | 主な対象者 |
|---|---|---|---|
| **M1 第 1 回** | 章 1（全 24 枚）+ 章 2（前半 12 枚）= 約 36 枚 | 2 時間 | PO / 事業企画 + テックリード + 情シス |
| **M2 第 2 回** | 章 2（後半 8 枚）+ 章 3（20 枚）+ 章 4（前半 8 枚）+ 章 5（20 枚）= 約 56 枚 | 2 時間 | 開発チーム / テックリード中心 |
| **M3 第 3 回** | 章 4（後半 8 枚）+ 章 6（24 枚）= 約 32 枚 | 2 時間 | インフラ / SRE / セキュリティ + 意思決定者 |

---

## 9. 関連ドキュメント

### 一次資料（本基盤の SSOT）

- [hearing-checklist.md](hearing-checklist.md) — 全 127 項目の SSOT（§0〜§5 構造）
- [proposal/00-index.md](proposal/00-index.md) — 顧客提示版 SSOT（§FR / §NFR / §C）
- [proposal/common/01-architecture.md](proposal/common/01-architecture.md) — §C-1 アーキテクチャ全章
- [proposal/common/06-architecture-decision-hybrid.md](proposal/common/06-architecture-decision-hybrid.md) — §C-6 ハイブリッド決定文書
- [requirements-document-structure.md](requirements-document-structure.md) — 要件定義資料構成 SSOT

### 用語・コード参照

- [terms-and-codes-reference.md](terms-and-codes-reference.md) — 21 章のコード体系リファレンス
- [hearing-checklist-excel-terms.tsv](hearing-checklist-excel-terms.tsv) — Excel 転記用 用語シート

### マスター表

- [hearing-checklist-excel-master-b.tsv](hearing-checklist-excel-master-b.tsv) — マスター表 B（事業者・顧客 IdP 統合表）
- [hearing-checklist-excel-master-c.tsv](hearing-checklist-excel-master-c.tsv) — マスター表 C（アプリ・システム構成）

### プロセス・戦略

- [requirements-process-plan.md](requirements-process-plan.md) — 進め方
- [requirements-hearing-strategy.md](requirements-hearing-strategy.md) — ヒアリング戦略

### Excel 転記用

- [hearing-checklist-excel-main.tsv](hearing-checklist-excel-main.tsv) — メインシート（127 項目 + M1/M2/M3 タグ）
- [hearing-checklist-excel-readme.md](hearing-checklist-excel-readme.md) — Excel 使い方ガイド

---

## 10. 改訂履歴

| 日付 | 内容 |
|---|---|
| 2026-05-27 | 初版作成。28 項目 → 31 項目（6 章）に再編成、参考資料マトリクス + スライド構成案 + 3 回ヒアリング対応 |
