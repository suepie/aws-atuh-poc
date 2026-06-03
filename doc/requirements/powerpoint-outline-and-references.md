# PowerPoint 資料 構成案・参考資料マトリクス

> **目的**: 顧客提示用 PowerPoint 資料の **大項目構成 + 各項目の参考資料一覧**を整理した SSOT。
> **背景**: ヒアリングと並行して資料を準備するため、各章・項目で**どのドキュメントを参照すれば良いか**を一覧化。
> **対象読者**: PowerPoint 作成担当者 / 要件定義レビュー担当者 / 顧客提示担当者
> **更新基準**: 大項目構成の変更時、参考資料追加時

---

## 0. 構成サマリー

| 章 | 項目数 | 主題 | スライド枚数目安 | 時間配分目安 |
|:-:|:-:|---|:-:|:-:|
| 1 | 7 | 全体方針・前提 | 28 | 30 分 |
| 2 | 5 | 接続元・対象 | 20 | 30 分 |
| 3 | 4 | **認証**（Authentication）| 16 | 18 分 |
| 4 | 1 | **認可**（Authorization、★NEW 独立章）| 6 | 10 分 |
| 5 | 6 | SSO・セッション・ログアウト | 24 | 28 分 |
| 6 | 8 | ユーザー管理・プロビジョニング・セルフサービス | 32 | 30 分 |
| 7 | 9 | 非機能要件（★ITDR/Identity Security 追加）| 36 | 33 分 |
| 8 | 5 | 開発者体験・UX・プライバシー | 20 | 20 分 |
| **計** | **45** | - | **~182** | **~199 分（3.3 時間）** |

> **改訂履歴**: 初版 31 項目 → 2026-06-03 業界標準フレームワーク照合 **44 項目** → 2026-06-03 強制再認証/ステップアップ独立 **45 項目** → 2026-06-03 **認可を §3.4 から §4 独立章化 + ITDR を §3.5 から §7.4 セキュリティ群へ移動**（章数 7 → 8、業界 ITDR トレンドに整合）。詳細は §12 改訂履歴。

> ヒアリング 3 回会議計画（[hearing-checklist-excel-main.tsv ヒアリング回 M1/M2/M3](hearing-checklist-excel-main.tsv)）と照合：M1（章 1-2 中心）/ M2（章 3-5 中心）/ M3（章 6-7 + 最終意思決定）

### 🔑 PowerPoint と社内文書の narrative 差分（重要）

| 文書 | 主読者 | アーキテクチャの提示順序 | narrative |
|---|---|---|---|
| **PowerPoint（本文書）**| 顧客（経営層 / 情シス / アプリオーナー）| **集約 → 例外対応** | **「基本は集約、対応できない要件は別途対応可能」** |
| **§C-6 内部分析文書** | 弊社設計者 + 顧客技術担当 | ハイブリッド推奨 → 集約/分散比較 | 「6 懸念を踏まえてハイブリッド推奨」|

**両文書の関係**: **基盤構造は同じ**（コア 80% + エッジ 20%）。**見せ方の順序のみ違う**。PowerPoint は「**集約をデフォルトとして安心感を与えつつ、例外対応の柔軟性も示す**」narrative を採用。詳細は §1.3。

---

## 1. 全体方針・前提（7 項目）

### 1.1 要件定義の進め方・ヒアリング計画

**概要**: 4 ステージ要件定義プロセス、3 回ヒアリング計画、抽出方針（4 軸）、**本資料のスコープ宣言**（対象外領域: PAM / KYC / Access Review 等）。

| 種別 | 参考資料 |
|---|---|
| **内部** | [requirements-process-plan.md](requirements-process-plan.md) §1-7 |
| **内部** | [requirements-hearing-strategy.md](requirements-hearing-strategy.md) §1-3 |
| **内部** | [proposal/00-index.md §0.4 検討事項の抽出方針](proposal/00-index.md) |
| **内部** | [hearing-checklist-excel-readme.md ヒアリング回 M1/M2/M3](hearing-checklist-excel-readme.md) |
| **外部** | [IPA 非機能要求グレード 2018](https://www.ipa.go.jp/sec/softwareengineering/std/ent03-b.html) |

**スコープ明示すべき対象外領域**：
- PAM（Privileged Access Management、弊社運用者向け、§FR-8.3 で別途扱い）
- Identity Proofing / KYC（B2C 規制業界向け、本基盤対象外）
- Access Reviews / Recertification（IGA レイヤー、本基盤外）

### 1.2 認証基盤で認証するユーザ（P-1〜P-6 / α-δ シナリオ）

**概要**: 利用者カテゴリ 6 分類 + 採用シナリオ α/β/γ/δ + インフラ運用者 I-1〜I-5。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [00-common.md A-5-2, A-5-3, A-5-4](hearing-script/00-common.md) |
| **hearing-checklist** | §1.1 (A-5-2), §1.2 (A-5-3), §1.3 (A-5-4) |
| **proposal** | [§FR-1.2.0.0 利用者カテゴリ別の分析](proposal/fr/01-auth.md) |
| **内部** | [terms-and-codes-reference.md §2-4](terms-and-codes-reference.md) |
| **外部** | [NIST SP 800-63-3 Digital Identity Guidelines](https://pages.nist.gov/800-63-3/) |

### 1.3 アーキテクチャ方針（**基本は集約**、例外はハイブリッド / Token Exchange）

> **PowerPoint での narrative**: **「基本方針: 認証基盤への集約」**を前面に出し、**「対応できない要件には以下の手段で対応可能」**として例外対応方式（ハイブリッド / Token Exchange）を後置する構成。
>
> **社内向け §C-6 との関係**: §C-6 では「ハイブリッド推奨」として詳細分析しているが、PowerPoint では**集約をデフォルトとする narrative**で提示。**基盤構造は同じ**（80% コア統合 + 20% エッジ）だが、**見せ方を「集約 → 例外対応」順**にすることで顧客の納得度を高める。

**概要**: 認証基盤の集約を基本方針として提示。ただし以下の例外要件には**個別対応の選択肢**（ハイブリッド構成 / Token Exchange / アプリ独自実装）を提供。

#### スライド構成案（5 枚）

| # | スライド | 内容 |
|---|---|---|
| **1** | 基本方針 | **「認証基盤に集約します」**（Identity Broker パターン、業界標準）|
| **2** | 集約のメリット | SSO 自動 / 運用集約 / セキュリティ baseline 統一 / 顧客追加 < 1 営業日 / コスト効率 |
| **3** | 例外要件の認識 | 一部のアプリは集約だけでは対応困難:<br/>- FAPI 2.0（金融 / 決済）<br/>- AI Agent / IoT（Device Code）<br/>- レガシー SAML SP 連携 |
| **4** | 例外対応の選択肢 | **3 つの手段**:<br/>① **ハイブリッド構成**（エッジ層を独立）<br/>② **Token Exchange (RFC 8693)**（コア層 + 変換）<br/>③ **アプリ独自実装**（基盤外で完結）|
| **5** | アプリ別判定フロー | アプリは「コア統合（デフォルト）/ 例外 3 つのどれか」を選択 |

#### 重要メッセージング

| 言ってはいけない | 言うべき |
|---|---|
| ❌ 「ハイブリッド型を推奨します」（顧客に複雑性懸念を与える）| ✅ 「**基本は集約します**」（シンプル、安心）|
| ❌ 「最初から複数基盤を建てます」 | ✅ 「**ほとんどのアプリは 1 つの基盤で対応**」 |
| ❌ 「Federation 設計が複雑」 | ✅ 「**特殊要件のみ、必要に応じて追加対応**」 |

| 種別 | 参考資料 |
|---|---|
| **proposal** | [§C-1.0.A 本基盤のアーキテクチャスタンス](proposal/common/01-architecture.md)（Broker パターン採用根拠、**集約 narrative の核**）, [§C-1.0.B 代替アーキテクチャ参考図](proposal/common/01-architecture.md), [§C-6 ハイブリッド統合の根拠と設計](proposal/common/06-architecture-decision-hybrid.md)（**詳細分析、社内向け**）|
| **hearing-checklist** | D-6 |
| **外部** | [KuppingerCole Identity Fabrics](https://www.kuppingercole.com/blog/reinwarth/the-kuppingercole-identity-fabric-2025) / [Microsoft Federated Identity Pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/federated-identity) / [OIDC Federation 1.0](https://openid.net/specs/openid-federation-1_0.html) |

### 1.4 構成概要図（全体 + AWS 構成 + Federation 接続）

**概要**: 全体構成図 + 想定 AWS 構成図 + Federation 接続 + Bearer JWT/JWKS 動作。

> **§1.3 narrative との整合**: メインの構成図は **§C-1.0.A の集約版（1 Hub）**を提示。**例外対応として§C-1.0.B 図 2 ハイブリッド構成図**を「**こういう場合に追加可能**」として後置。順序が重要（集約 → 例外）。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [§C-1.2 全体アーキテクチャ](proposal/common/01-architecture.md), [§C-1.2.B 想定 AWS 構成図](proposal/common/01-architecture.md), [§C-1.2.D Bearer JWT / JWKS / 認可フロー 6 種](proposal/common/01-architecture.md), [§C-6 §6.1, §6.3.3, §6.4](proposal/common/06-architecture-decision-hybrid.md) |
| **内部** | [common/keycloak-network-architecture.md](../common/keycloak-network-architecture.md) |
| **外部** | [AWS Multi-Account Strategy](https://aws.amazon.com/controltower/) / [Keycloak Deployment Guide](https://www.keycloak.org/server/configuration-production) |

### 1.5 製品選定（Cognito vs Keycloak OSS vs RHBK + ティア選定）

**概要**: プラットフォーム選定軸、Cognito Hard Limit、ティア（Lite/Essentials/Plus）、Keycloak OSS vs RHBK、規模戦略。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [11-operations.md D-1](hearing-script/11-operations.md) |
| **hearing-checklist** | §2.8 (D-1), §3.2 (B-100 列 S K1-K8) |
| **proposal** | [§C-2 プラットフォーム選定軸](proposal/common/02-platform.md), [§C-2.4.A 規模軸](proposal/common/02-platform.md), [§C-1.5 規模スケーリング戦略](proposal/common/01-architecture.md) |
| **内部** | [ADR-016 Cognito ティア選定基準](../adr/016-cognito-feature-tier-selection.md), [ADR-017](../adr/017-keycloak-oss-vs-rhbk-selection.md), [poc-summary-evaluation.md](poc-summary-evaluation.md), [reference/cognito-knockout-conditions.md](../reference/cognito-knockout-conditions.md) |
| **外部** | [AWS Cognito Service Quotas](https://docs.aws.amazon.com/cognito/latest/developerguide/limits.html) / [Cognito Pricing](https://aws.amazon.com/cognito/pricing/) / [RHBK](https://access.redhat.com/products/red-hat-build-of-keycloak) |

### 1.6 移行方針・リリース計画

**概要**: 既存認証移行戦略 + パスワードハッシュ移行 + リリーススケジュール + ドメイン変更計画 + ユーザー周知 + **Vendor lock-in / Portability**。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [00-common.md A-5, A-10](hearing-script/00-common.md), [11-operations.md D-2, D-5](hearing-script/11-operations.md), [10-security-compliance.md C-204-4](hearing-script/10-security-compliance.md), [02-idp-federation.md B-615/616/617](hearing-script/02-idp-federation.md) |
| **hearing-checklist** | §2.7, §3.3 (C-204-4) |
| **proposal** | [§NFR-9 移行性](proposal/nfr/09-migration.md), [§C-4 スケジュール](proposal/common/04-schedule.md), [§FR-2.3.2.B 既存システムからの移行時のエンドユーザー影響](proposal/fr/02-federation.md) |

### 1.7 スコープ宣言（対象外領域）★NEW

**概要**: 本基盤のスコープと**明示的に対象外とする領域**を宣言。誤解を防ぎ、要件発散を抑制。

| 対象外領域 | 理由 / 代替手段 |
|---|---|
| **PAM**（Privileged Access Management）| 弊社運用者向けは §FR-8.3 で別途扱い、エンドユーザー向けは AWS IAM Identity Center 等 |
| **Identity Proofing / KYC** | B2C 規制業界向け、本基盤の認証フローとは別レイヤー |
| **Access Reviews / Recertification** | IGA 領域、SailPoint / Saviynt 等の別製品 |
| **データ統合 / ETL** | ID 同期は SCIM、それ以外のデータ統合は対象外 |
| **API ゲートウェイ機能の代替** | API Gateway は本基盤のクライアントとして連携、API 管理機能自体は AWS API Gateway / Kong 等 |

| 種別 | 参考資料 |
|---|---|
| **外部** | [SailPoint IGA](https://www.sailpoint.com/identity-library/identity-governance) / [CrowdStrike IGA](https://www.crowdstrike.com/en-us/cybersecurity-101/identity-protection/identity-governance-and-administration-iga/) |

---

## 2. 接続元・対象（5 項目）

### 2.1 規模・規制・コンプライアンス

**概要**: MAU 規模 + 顧客企業数（A-15）+ 業界規制（FIPS / SOC2 / PCI DSS / FFIEC / HIPAA / GDPR）+ データ所在地。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [00-common.md A-1〜A-4, A-7, A-12, A-15](hearing-script/00-common.md), [10-security-compliance.md C-201, C-202, C-209](hearing-script/10-security-compliance.md) |
| **hearing-checklist** | §2.1, §2.2 |
| **proposal** | [§NFR-3 拡張性](proposal/nfr/03-scalability.md), [§NFR-7 コンプライアンス](proposal/nfr/07-compliance.md), [§C-1.5 規模スケーリング戦略](proposal/common/01-architecture.md) |
| **内部** | [ADR-006 コスト損益分岐](../adr/006-cognito-vs-keycloak-cost-breakeven.md) |
| **外部** | [NIST SP 800-63B Rev 4](https://pages.nist.gov/800-63-4/sp800-63b.html) / [SOC 2 Trust Services Criteria](https://www.aicpa-cima.com/topic/audit-assurance/audit-and-assurance-greater-than-soc-2) / [FFIEC IT Handbook](https://ithandbook.ffiec.gov/) / [FISC 安全対策基準](https://www.fisc.or.jp/) |

### 2.2 顧客 IdP 一覧（マスター表 B）

**概要**: 事業者 IdP + 顧客企業 IdP の統合表。**LDAP 直結 = Keycloak 必須化**。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [02-idp-federation.md マスター表 B](hearing-script/02-idp-federation.md) |
| **hearing-checklist** | §3.1 (B-200, A-13, A-6, B-609, B-615-617) |
| **proposal** | [§FR-2.1 IdP 接続種別](proposal/fr/02-federation.md) |
| **内部** | [common/identity-broker-multi-idp.md](../common/identity-broker-multi-idp.md), [hearing-checklist-excel-master-b.tsv](hearing-checklist-excel-master-b.tsv) |
| **外部** | [Microsoft Entra ID](https://learn.microsoft.com/en-us/entra/) / [Okta Workforce](https://www.okta.com/products/) / [HENNGE One](https://hennge.com/jp/) / [AD FS Deployment Guide](https://learn.microsoft.com/en-us/windows-server/identity/ad-fs/) |

### 2.3 接続アプリ・システム一覧（マスター表 C）

**概要**: アプリ種別 + 認証方式 + JWT 検証場所 + **特殊要件フラグ K1〜K8（Cognito Knockout）** + 既存ローカル認証。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [01-auth-flow.md マスター表 C + 補足 1〜5](hearing-script/01-auth-flow.md) |
| **hearing-checklist** | §3.2 (B-100) |
| **proposal** | [§FR-1.1 認証フロー / Grant Type](proposal/fr/01-auth.md) |
| **内部** | [common/auth-patterns.md](../common/auth-patterns.md), [reference/cognito-knockout-conditions.md](../reference/cognito-knockout-conditions.md), [hearing-checklist-excel-master-c.tsv](hearing-checklist-excel-master-c.tsv) |
| **外部** | [OAuth 2.1](https://datatracker.ietf.org/doc/draft-ietf-oauth-v2-1/) / [FAPI 2.0](https://openid.net/specs/fapi-2_0-security-02.html) / RFC: [6749](https://datatracker.ietf.org/doc/html/rfc6749) / [7519](https://datatracker.ietf.org/doc/html/rfc7519) / [8628](https://datatracker.ietf.org/doc/html/rfc8628) / [8693](https://datatracker.ietf.org/doc/html/rfc8693) / [8705](https://datatracker.ietf.org/doc/html/rfc8705) / [9449](https://datatracker.ietf.org/doc/html/rfc9449) |

### 2.4 マルチテナント設計（分離粒度 + 規模戦略 + Organization 機能 + 特殊顧客）

**概要**: テナント分離粒度 L1/L2/L3 + 1500-3000 顧客の規模戦略 + Keycloak Organization + 物理分離特殊顧客。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [03-authz-jwt.md B-306](hearing-script/03-authz-jwt.md), [06-multitenancy.md B-602〜B-611](hearing-script/06-multitenancy.md) |
| **hearing-checklist** | §2.3 |
| **proposal** | [§FR-2.3 マルチテナント運用](proposal/fr/02-federation.md), [§C-1.4 物理分離レベル](proposal/common/01-architecture.md), [§C-1.5 規模スケーリング戦略](proposal/common/01-architecture.md) |
| **内部** | [ADR-014 認証パターン範囲](../adr/014-auth-patterns-scope.md) |
| **外部** | [Keycloak Organizations 26+](https://www.keycloak.org/docs/latest/server_admin/#_managing-organizations) / [AWS Cognito Multi-tenant patterns](https://docs.aws.amazon.com/cognito/latest/developerguide/multi-tenant-application-best-practices.html) / [Auth0 B2B Multi-tenancy](https://auth0.com/blog/demystifying-multi-tenancy-in-b2b-saas/) / [Wristband B2B Multi-tenant Auth](https://www.wristband.dev/blog/multi-tenant-b2b-authentication-explained-key-concepts-components) |

### 2.5 顧客別ブランディング（ログイン画面・URL）

**概要**: 軸 1 アプリ別 × 軸 2 顧客別の 4 パターン（A / A' / B / C）+ カスタマイズレベル + Custom Domain + 動的差替実装責務。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [00-common.md A-11, A-11-α, A-11-2, A-11-3](hearing-script/00-common.md), [02-idp-federation.md B-208](hearing-script/02-idp-federation.md), [06-multitenancy.md B-612](hearing-script/06-multitenancy.md), [07-logout-session.md B-703-1, B-703-3](hearing-script/07-logout-session.md) |
| **hearing-checklist** | §1.5, §3.4 |
| **proposal** | [§FR-2.3.3.A 画面所在マトリクス](proposal/fr/02-federation.md), [§FR-8.3 管理機能](proposal/fr/08-admin.md) |
| **内部** | [common/branding-strategy-evidence.md](../common/branding-strategy-evidence.md) |
| **外部** | [Auth0 Universal Login](https://auth0.com/docs/authenticate/login/auth0-universal-login) / [Cognito Managed Login Branding](https://docs.aws.amazon.com/cognito/latest/developerguide/managed-login-brandings.html) / [Microsoft Entra B2C Custom Branding](https://learn.microsoft.com/en-us/azure/active-directory-b2c/customize-ui-with-html) |

---

## 3. 認証 / Authentication（4 項目）

> **2026-06-03 構成変更**: 元の「§3.4 認可スタンス」を **§4 認可 (Authorization)** として独立章化、元の「§3.5 ITDR」を **§7.4 Identity Security** として §7 非機能要件群に移動。**§3 は「認証（Who you are）」の議論に純化**。

### 3.1 ログイン方式・画面設定

**概要**: IdP 選択 UX（HRD / セレクター / 組織固有 URL）+ Custom Domain + ログイン画面の所在。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [06-multitenancy.md B-601, B-610](hearing-script/06-multitenancy.md), [02-idp-federation.md B-208](hearing-script/02-idp-federation.md) |
| **hearing-checklist** | §4.4 (B-601), §3.4 (B-208), §3.5 (B-610) |
| **proposal** | [§FR-2.3.3 ログイン UX](proposal/fr/02-federation.md) |
| **外部** | [IETF / Curity BFF gold standard 2025](https://curity.io/resources/learn/the-bff-pattern/) / [Home Realm Discovery (Shibboleth)](https://shibboleth.atlassian.net/wiki/spaces/SP3/pages/2065335462/HomeRealmDiscovery) |

### 3.2 MFA 要件（初回認証）

**概要**: **初回ログイン時の MFA** に関する要件 — MFA 必須範囲 + MFA 方式（TOTP / WebAuthn / SMS / ハードウェアキー）+ AAL レベル + 条件付き MFA 判定軸 + 外部 IdP MFA 信頼度。

> **スコープ注記**: 本項目は「**初回認証時の MFA**」に純化。
> - **強制再認証**（システム駆動: 退職検知 / Risk / 管理者操作 / CAEP）→ [§4.6 強制再認証・ステップアップ認証](#46-強制再認証ステップアップ認証forced--step-up-re-authentication)
> - **ステップアップ認証**（アプリ駆動: 高権限操作 / 高額決済等で追加 MFA）→ [§4.6 強制再認証・ステップアップ認証](#46-強制再認証ステップアップ認証forced--step-up-re-authentication)
> - **「追加で認証を要求する」テーマは §4.6 に集約**（実装技術 = `prompt=login` / `max_age` / `acr_values` / Token Revocation で共通）

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [05-mfa.md B-501〜B-509](hearing-script/05-mfa.md), [10-security-compliance.md C-210〜C-215](hearing-script/10-security-compliance.md) |
| **hearing-checklist** | §2.6, §4.3 |
| **proposal** | [§FR-3 MFA](proposal/fr/03-mfa.md), [§FR-2.2.3 MFA 重複回避](proposal/fr/02-federation.md) |
| **内部** | [ADR-009 MFA 責任分担](../adr/009-mfa-responsibility-by-idp.md) |
| **外部** | [NIST SP 800-63B Rev 4 §5 MFA](https://pages.nist.gov/800-63-4/sp800-63b.html) / [FIDO Alliance Passkey](https://fidoalliance.org/passkeys/) / [WebAuthn Level 3](https://www.w3.org/TR/webauthn-3/) |

### 3.3 ローカルユーザー認証ポリシー（パスワード + アカウントロック + 侵害検出 + Bot 保護）★改名 + 拡張

**概要**: ローカルユーザー専用の認証ポリシー全体（パスワード強度 / 履歴 / 有効期限 / アカウントロック / 侵害クレデンシャル検出 / **Bot 保護・CAPTCHA**）。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [10-security-compliance.md C-204, C-204-2/3, C-205, C-205-2](hearing-script/10-security-compliance.md) |
| **hearing-checklist** | §4.5 |
| **proposal** | [§FR-1.2 パスワード・ローカルユーザー管理](proposal/fr/01-auth.md) |
| **内部** | [ADR-016 Cognito ティア選定](../adr/016-cognito-feature-tier-selection.md) |
| **外部** | [NIST SP 800-63B Rev 4 §5.1.1 Memorized Secrets](https://pages.nist.gov/800-63-4/sp800-63b.html) / [HaveIBeenPwned API](https://haveibeenpwned.com/API/v3) / [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html) / [AWS WAF Bot Control](https://docs.aws.amazon.com/waf/latest/developerguide/waf-bot-control.html) / [Cloudflare Turnstile](https://www.cloudflare.com/products/turnstile/) |

> **Q1 への対応**: 元「ローカル認証_パスワードポリシー」を本項目に統合（パスワード + ロック + 侵害検出 + Bot を 1 つに）。**セルフサービス機能（5.6）は別概念**として独立。

### 3.4 認可スタンス + JWT クレーム設計 + API 認可フロー

**概要**: 認可の 2 つの意味 + JWT クレーム + 認可粒度 + Bearer JWT / JWKS 標準動作 + Token Introspection 代替 + Token Exchange（K1）。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [03-authz-jwt.md B-301, B-302, B-305](hearing-script/03-authz-jwt.md), [01-auth-flow.md マスター表 C 補足 2 K1](hearing-script/01-auth-flow.md) |
| **hearing-checklist** | §4.2 |
| **proposal** | [§FR-6.0.A 認可スタンス](proposal/fr/06-authz.md), [§FR-6.1.A 最小クレーム設計](proposal/fr/06-authz.md), [§C-1.2.D Bearer JWT / JWKS / 認可フロー 6 種](proposal/common/01-architecture.md) |
| **内部** | [common/authz-architecture-design.md](../common/authz-architecture-design.md), [terms-and-codes-reference.md §16, §20, §21](terms-and-codes-reference.md) |
| **外部** | RFC: [6750 Bearer](https://datatracker.ietf.org/doc/html/rfc6750) / [7519 JWT](https://datatracker.ietf.org/doc/html/rfc7519) / [7517 JWKS](https://datatracker.ietf.org/doc/html/rfc7517) / [7662 Introspection](https://datatracker.ietf.org/doc/html/rfc7662) / [8693 Token Exchange](https://datatracker.ietf.org/doc/html/rfc8693) |

### 3.5 ITDR（Identity Threat Detection & Response）統合戦略 ★NEW

**概要**: 個別検知（侵害クレデンシャル C-205-2 / CAEP C-217）を**統合 ITDR 戦略**として整理。認証イベント異常検知 / リアルタイムリスク評価 / 自動レスポンス（強制ログアウト / MFA 要求）/ SOC 連携。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [10-security-compliance.md C-217](hearing-script/10-security-compliance.md) + 新規（C-217-2 ITDR 統合戦略）|
| **proposal** | [§FR-5.4 CAEP 将来発展](proposal/fr/05-logout-session.md) |
| **外部** | [Microsoft Defender for Identity](https://learn.microsoft.com/en-us/defender-for-identity/) / [AWS GuardDuty Identity Protection](https://docs.aws.amazon.com/guardduty/latest/ug/) / [Shared Signals Framework (OpenID)](https://openid.net/wg/sharedsignals/) / [Gartner ITDR Market Guide](https://www.gartner.com/en/documents/) |

### 3.6 認証フロー一覧（OAuth 2.0 / OIDC 標準）

**概要**: Authorization Code Flow + PKCE / Client Credentials / Device Code / mTLS / DPoP の使い分け、マスター表 C 列 P/S との対応。

> **🎯 内側プロトコル方針（D-7）**: 接続アプリへの**発行プロトコルは OIDC を推奨**。新規開発アプリは OIDC 一択、既存 SAML SP アプリは OIDC 化検討を優先、OIDC 化困難な既存資産のみ SAML IdP 発行 (K5) で当面接続。**外側（顧客 IdP からの受信）は SAML + OIDC 両対応を継続**（顧客側 IdP は仕様統制不可）。

**Broker の 4 役割マトリクス**（受信 × 発行）:

| | 外側=受信側（顧客 IdP）| 内側=発行側（接続アプリ）|
|---|---|---|
| **SAML 2.0** | ✅ SAML SP モード（両製品対応）| ⚠ SAML IdP モード（**K5**、Keycloak のみ）|
| **OIDC** | ✅ OIDC RP モード（両製品対応）| ✅ OIDC OP モード（**標準・推奨**）|

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [01-auth-flow.md マスター表 C 補足 1〜5](hearing-script/01-auth-flow.md) |
| **hearing-checklist** | [D-7 内側 OIDC 推奨合意](hearing-checklist.md), [B-100 マスター表 C](hearing-checklist.md) |
| **proposal** | [§FR-1.1 認証フロー / Grant Type](proposal/fr/01-auth.md), [§C-1 内側プロトコル方針](proposal/common/01-architecture.md) |
| **内部** | [terms-and-codes-reference.md §7 末尾 OIDC 推奨方針](terms-and-codes-reference.md) |
| **外部** | [OAuth 2.0 Best Current Practice (RFC 8252)](https://datatracker.ietf.org/doc/html/rfc8252) / [OIDC Core 1.0](https://openid.net/specs/openid-connect-core-1_0.html) |

---

## 4. SSO・セッション・ログアウト（6 項目）

### 4.1 SSO 方針 + セッション信頼レベル

**概要**: SSO 範囲 + クロス IdP SSO 信頼レベル L1〜L4 + 差別化 + max_age 制約 + SSO セッション TTL。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [05-mfa.md B-509](hearing-script/05-mfa.md), [08-sso-details.md B-801〜B-803](hearing-script/08-sso-details.md) |
| **hearing-checklist** | §2.5, §4.4 |
| **proposal** | [§FR-4 SSO](proposal/fr/04-sso.md), [§FR-5.2 セッション TTL](proposal/fr/05-logout-session.md) |
| **外部** | [OIDC Core 1.0 §3.2.2.10 max_age](https://openid.net/specs/openid-connect-core-1_0.html#AuthRequest) / [SAML 2.0 SSO Profile](https://docs.oasis-open.org/security/saml/v2.0/saml-profiles-2.0-os.pdf) |

### 4.2 ログアウト方針（4 レイヤー L1〜L4）

**概要**: デフォルトログアウトレイヤー + フェデ連動 + リダイレクト先 + 種類別飛び先 + 後処理 + 強制ログアウト時 + ユーザー自身のセッション管理 UI。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [07-logout-session.md B-701〜B-706, B-703-1〜5](hearing-script/07-logout-session.md) |
| **hearing-checklist** | §2.5, §3.4, §4.4 |
| **proposal** | [§FR-5.1 ログアウト 4 レイヤー](proposal/fr/05-logout-session.md), [§FR-5.3 強制ログアウト](proposal/fr/05-logout-session.md) |
| **外部** | [OIDC RP-Initiated Logout 1.0](https://openid.net/specs/openid-connect-rpinitiated-1_0.html) / [OIDC Front-Channel Logout 1.0](https://openid.net/specs/openid-connect-frontchannel-1_0.html) |

### 4.3 SLO + Back-Channel Logout + Token Revocation

**概要**: SLO 必須範囲 + Back-Channel Logout (RFC 8417, K7) + Access Token 即時 Revocation (K8) + トークン TTL + タイムアウト + CAEP。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [05-mfa.md B-504 → K7](hearing-script/05-mfa.md), [07-logout-session.md B-704 → K8](hearing-script/07-logout-session.md), [01-auth-flow.md 補足 2 K7/K8](hearing-script/01-auth-flow.md), [10-security-compliance.md C-206, C-206-2/3, C-217](hearing-script/10-security-compliance.md) |
| **hearing-checklist** | §3.2 (B-100 列 S K7/K8), §4.4, §5.3 |
| **proposal** | [§FR-5.1 SLO](proposal/fr/05-logout-session.md), [§FR-5.3 Revocation](proposal/fr/05-logout-session.md), [§FR-5.4 CAEP](proposal/fr/05-logout-session.md) |
| **外部** | [RFC 8417 Back-Channel Logout](https://datatracker.ietf.org/doc/html/rfc8417) / [OIDC Back-Channel Logout 1.0](https://openid.net/specs/openid-connect-backchannel-1_0.html) / [RFC 7009 Token Revocation](https://datatracker.ietf.org/doc/html/rfc7009) / [Shared Signals Framework](https://openid.net/wg/sharedsignals/) |

### 4.4 Federation 接続パターン（**例外対応の選択肢**: ハイブリッド構成での SSO 維持）

> **§1.3 narrative との整合**: 本項目は **§1.3 で示した「例外対応 3 つの選択肢」のうち、①ハイブリッド構成 + ②Token Exchange の技術詳細**。「基本は集約、例外時のみハイブリッド」という基本方針を前提に、**例外対応時の SSO 維持手段**として位置付ける。

**概要**: 例外的にハイブリッド構成（エッジ層）を採用する場合の **二重 Federation 動作** + **Token Exchange 代替** + Federation-Friendly 設計原則 + Edge アプリの SSO 維持。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [§C-6 §6.4 Federation 接続パターン](proposal/common/06-architecture-decision-hybrid.md), [§C-1.2.C.1 Federation Hub の 5 パターン](proposal/common/01-architecture.md), [§C-1.2.C.2 分散 + SSO + SPOF フリー 3 パターン](proposal/common/01-architecture.md) |
| **外部** | [RFC 8693 Token Exchange](https://datatracker.ietf.org/doc/html/rfc8693) / [OIDC Federation 1.0](https://openid.net/specs/openid-federation-1_0.html) / [eduGAIN Federation Doc](https://edugain.org/) / [Microsoft Entra B2B Cross-Tenant](https://learn.microsoft.com/en-us/entra/external-id/cross-tenant-access-settings-b2b-collaboration) / [Shibboleth Federation Operator Guide](https://shibboleth.atlassian.net/wiki/spaces/IDP30/overview) |

### 4.5 セッション TTL 設計（アイドル / 絶対 / トークン）

**概要**: Access Token TTL / Refresh Token TTL / ID Token TTL + アイドルタイムアウト + 絶対経過タイムアウト + AAL レベル別推奨値。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [10-security-compliance.md C-206, C-206-2, C-206-3](hearing-script/10-security-compliance.md) |
| **hearing-checklist** | §4.4 (C-206), §5.3 (C-206-2/3) |
| **proposal** | [§FR-5.2 セッション TTL](proposal/fr/05-logout-session.md) |
| **外部** | [NIST SP 800-63B Rev 4 §4.1.3 Reauthentication](https://pages.nist.gov/800-63-4/sp800-63b.html) |

### 4.6 強制再認証・ステップアップ認証（Forced & Step-up Re-authentication）★NEW

**概要**: **「追加で認証を要求する」要件のポリシー層**。トリガー一覧 + 切断深度（L1〜L4 + Token Revocation 要否）+ SLA + 実装方式の関連章への橋渡し。

> **位置付け**: §3.2 が「**初回認証時の MFA**」であるのに対し、本項目は「**初回認証後に、何らかの理由で追加認証を要求する**」要件の整理。**ポリシー定義**を本章で行い、実装技術は §4.3 / §4.5 / §3.5 に委譲する。

**含まれる 2 系統**:
| 系統 | トリガー | 典型例 |
|---|---|---|
| **A. 強制再認証**（システム駆動）| 退職検知 / 異動 / Risk Score 閾値超過 / 管理者操作 / セキュリティポリシー変更 / CAEP signals | 退職者の即時遮断、漏洩疑い時の全員強制ログアウト |
| **B. ステップアップ認証**（アプリ駆動、RFC 9470）| 業務イベント（高権限操作 / 高額決済 / 機微情報アクセス）| 管理画面の「テナント削除」操作時に追加 MFA |

**両系統の実装技術（共通）**:
1. `prompt=login` / `max_age=0` で次回認証時に再要求
2. `acr_values` 引き上げ要求（AAL レベル上昇）
3. Back-Channel Logout (RFC 8417) → §4.3 / K7
4. Access/Refresh Token Revocation (RFC 7009) → §4.3 / K8
5. `WWW-Authenticate: insufficient_user_authentication`（RFC 9470）
6. Continuous Access Evaluation (CAEP / Shared Signals) → §3.5

**ヒアリング 6 項目**:
| # | 質問 | 影響 |
|:-:|---|---|
| 1 | **強制再認証のトリガー**（退職 / 異動 / Risk / 管理者 / ポリシー変更 / CAEP）はどれが必要か | トリガー一覧確定 |
| 2 | 各トリガー別の**切断深度**（L1 IdP セッションのみ / L4 全 Token Revoke まで）| 実装方式 §4.3 連動 |
| 3 | **退職反映 SLA**（即時 / 5分 / 15分 / 翌日）| 製品選定（Cognito K7/K8 影響）|
| 4 | **ステップアップ認証**の必要性（高権限操作 / 高額決済等）| §3.2 と切り分け |
| 5 | **管理者の Force Logout 権限**（誰が誰のセッションを切れるか）| §5.7 委譲管理連動 |
| 6 | **CAEP / Shared Signals** 採否（顧客 IdP からの脅威シグナル受信）| §3.5 ITDR 連動 |

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [10-security-compliance.md C-216 ステップアップ（RFC 9470）, C-217 CAEP](hearing-script/10-security-compliance.md), [05-mfa.md B-504 BCL](hearing-script/05-mfa.md), [07-logout-session.md B-704 Token Revoke](hearing-script/07-logout-session.md), [06-multitenancy.md B-605-3 退職 SLA](hearing-script/06-multitenancy.md) |
| **hearing-checklist** | §3.2 (B-100 列 S K7/K8), §4.3, §4.4, §5.3 |
| **proposal** | [§FR-3.3 ステップアップ認証](proposal/fr/03-mfa.md), [§FR-5.3 Token Revocation](proposal/fr/05-logout-session.md), [§FR-5.4 CAEP](proposal/fr/05-logout-session.md) |
| **外部** | [RFC 9470 OAuth Step-up Authentication Challenge](https://datatracker.ietf.org/doc/html/rfc9470) / [RFC 8417 Security Event Token](https://datatracker.ietf.org/doc/html/rfc8417) / [Shared Signals Framework (CAEP)](https://openid.net/wg/sharedsignals/) / [Microsoft Entra Continuous Access Evaluation](https://learn.microsoft.com/en-us/entra/identity/conditional-access/concept-continuous-access-evaluation) / [NIST SP 800-63B Rev 4 §4.1.3 Reauthentication](https://pages.nist.gov/800-63-4/sp800-63b.html) |

---

## 5. ユーザー管理・プロビジョニング・セルフサービス（8 項目）

### 5.1 フェデユーザ同期（JIT / SCIM）

**概要**: JIT 採否 + SCIM 採否 + 既存ユーザー初期投入方法（バルク / SCIM / JIT 任せ）+ 規模感。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [04-user-management.md B-401, B-403](hearing-script/04-user-management.md) |
| **hearing-checklist** | §2.4 |
| **proposal** | [§FR-7.4 SCIM プロビジョニング](proposal/fr/07-user.md), [§FR-7.4.0 SCIM スタンス](proposal/fr/07-user.md), [§FR-2.2.1 JIT プロビジョニング](proposal/fr/02-federation.md) |
| **外部** | [SCIM 2.0 (RFC 7644)](https://datatracker.ietf.org/doc/html/rfc7644) / [Keycloak SCIM Plugin](https://github.com/Captain-P-Goldfish/scim-for-keycloak) / [AWS Cognito Bulk Import](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-using-import-tool.html) |

### 5.2 フェデユーザ権限（デフォルト権限）

**概要**: 新規作成時のデフォルト権限・ロール（JIT / SCIM / バルク共通）+ 業界推奨「最小権限」+ 顧客側で個別指定。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [04-user-management.md B-401-2](hearing-script/04-user-management.md) |
| **hearing-checklist** | §2.4 (B-401-2) |
| **proposal** | [§FR-2.2.1 新規作成時のデフォルト権限](proposal/fr/02-federation.md) |
| **外部** | [NIST Least Privilege Principle (SP 800-53)](https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final) |

### 5.3 フェデユーザ通知（Webhook）

**概要**: 共通基盤 → 外部アプリへの Webhook 通知（user.created/deleted/mfa.enrolled 等）+ 通知先 + 通知契機。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [04-user-management.md B-405, B-401-3](hearing-script/04-user-management.md) |
| **hearing-checklist** | §2.4 (B-405, B-401-3) |
| **proposal** | [§FR-9.3 Webhook](proposal/fr/09-integration.md), [§FR-9.3.0 Webhook の役割と SCIM/JIT との違い](proposal/fr/09-integration.md) |
| **外部** | [RFC 8417 Security Event Token](https://datatracker.ietf.org/doc/html/rfc8417) / [Webhook 業界標準（Stripe）](https://stripe.com/docs/webhooks) / [GitHub Webhooks API](https://docs.github.com/en/webhooks-and-events/webhooks) |

### 5.4 アカウント重複・リンク方針

**概要**: 同一テナント内ユーザー重複の想定 + 重複検出時の挙動 + 突合せキー + アカウントリンクトリガー + IdP 切替時のユーザー連続性。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [04-user-management.md B-406〜410](hearing-script/04-user-management.md) |
| **hearing-checklist** | §2.4, §3.5 (B-408) |
| **proposal** | [§FR-2.2.1.A 同一テナント内ユーザー重複](proposal/fr/02-federation.md) |
| **内部** | project_account_linking_investigation.md |
| **外部** | [OWASP Identity Linking](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html) / [Microsoft Account Linking Best Practices](https://learn.microsoft.com/en-us/entra/identity/users/users-restrict-guest-permissions) |

### 5.5 属性マッピング・更新

**概要**: 顧客 IdP 命名差異への対応 + 実属性名サンプル取得手順 + 属性更新タイミング + Source of Truth + HRD 解決ルール。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [06-multitenancy.md B-604, B-604-2, B-605, B-605-2, B-610](hearing-script/06-multitenancy.md) |
| **hearing-checklist** | §3.5 |
| **proposal** | [§FR-2.2.2 属性マッピング](proposal/fr/02-federation.md), [§FR-2.2.4 属性ライフサイクル設計](proposal/fr/02-federation.md) |
| **外部** | [SAML Attribute Mapping (Shibboleth)](https://shibboleth.atlassian.net/wiki/spaces/IDP30/pages/2065335462/AttributeMapping) / [OIDC Standard Claims](https://openid.net/specs/openid-connect-core-1_0.html#StandardClaims) / [Microsoft Entra B2B Claims Mapping](https://learn.microsoft.com/en-us/entra/identity-platform/saml-claims-customization) |

### 5.6 セルフサービス機能 ★NEW

**概要**: ユーザーが自身で操作できる機能の範囲（基盤標準提供 vs アプリ側実装）。**ローカルユーザー / フェデユーザの両方が対象**。

**含まれる機能**:
- **パスワードリセット**（メール経由、ローカルのみ）
- **プロフィール属性編集**（ローカル / フェデ両方）
- **MFA 要素の登録・解除**（ローカル / フェデ両方、基盤側 MFA を行う場合）
- **アクティブセッションの確認・破棄**（ローカル / フェデ両方）
- **連携 IdP の追加・削除**（複数 IdP リンク利用時）

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [04-user-management.md B-402](hearing-script/04-user-management.md) |
| **hearing-checklist** | §2.4 (B-402) |
| **proposal** | [§FR-7.3 セルフサービス](proposal/fr/07-user.md) |
| **外部** | [Auth0 Self-Service B2B Guide](https://auth0.com/blog/how-to-enable-self-service-identity-management-b2b-saas/) / [Keycloak Account Console](https://www.keycloak.org/docs/latest/server_admin/#con-account-console_server_administration_guide) / [Cognito Hosted UI Account Recovery](https://docs.aws.amazon.com/cognito/latest/developerguide/managed-login.html) |

### 5.7 委譲管理（Delegated Administration）★NEW

**概要**: 顧客企業のテナント管理者への管理委譲。**全権委譲を選んでも、委譲範囲の明確化 + 弊社側ガバナンス領域の定義が必要**。

**定義必要事項**（5 つ）:
1. **テナント管理者の認証方法**（顧客 IdP 経由）
2. **初期テナント管理者の任命方法**（弊社で初期付与 vs セルフサインアップ）
3. **テナント管理者の権限範囲**（全権 / ユーザー CRUD のみ / + ロール / + IdP 設定 / 監査ログ閲覧）
4. **管理者間の権限移譲**（他テナント管理者を任命できるか）
5. **弊社側に残るガバナンス領域**（コンプラ baseline / SLA 維持 / インシデント対応 / セキュリティ baseline）

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [04-user-management.md B-404](hearing-script/04-user-management.md), [06-multitenancy.md B-608](hearing-script/06-multitenancy.md) |
| **hearing-checklist** | §2.4 (B-404), §2.3 (B-608) |
| **proposal** | [§FR-8.3 管理機能 / 委譲管理](proposal/fr/08-admin.md) |
| **外部** | [Wristband B2B Admin Delegation](https://www.wristband.dev/blog/multi-tenant-b2b-authentication-explained-key-concepts-components) / [Auth0 Tenant Administration](https://auth0.com/docs/manage-users/user-administration) / [Microsoft Entra Delegated Administration](https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/) |

### 5.8 ユーザーライフサイクル管理（JML: Joiner/Mover/Leaver 統合視点）★NEW

**概要**: ユーザーライフサイクル全体（入社 / 異動 / 退職）を統合視点で整理。SCIM / JIT は Joiner だけだが、**Mover（異動）/ Leaver（退職、即時アクセス遮断）まで含めた一貫した設計が必要**。

**3 つのライフサイクルイベント**:
- **Joiner**（入社・新規）: JIT / SCIM / バルクで作成、デフォルト権限付与
- **Mover**（異動）: ロール変更、属性更新、Force/Import モード選択
- **Leaver**（退職）: **即時アクセス遮断 SLA**、Access Token Revocation、関連リソースクリーンアップ

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [04-user-management.md B-401, B-410](hearing-script/04-user-management.md), [06-multitenancy.md B-605-3 退職反映 SLA](hearing-script/06-multitenancy.md), [07-logout-session.md B-704 → K8](hearing-script/07-logout-session.md) |
| **hearing-checklist** | §2.4 (B-401, B-410), §3.5 (B-605-3) |
| **proposal** | [§FR-7.4 SCIM](proposal/fr/07-user.md), [§FR-2.2.1 JIT](proposal/fr/02-federation.md), [§FR-5.3 Token Revocation](proposal/fr/05-logout-session.md) |
| **外部** | [SailPoint IGA Lifecycle](https://www.sailpoint.com/identity-library/identity-governance) / [CrowdStrike IGA](https://www.crowdstrike.com/en-us/cybersecurity-101/identity-protection/identity-governance-and-administration-iga/) / [LoginRadius IAM Lifecycle](https://www.loginradius.com/blog/identity/identity-cloud-ciam-checklist) |

---

## 6. 非機能要件（8 項目）

### 6.1 可用性・SLA・DR

**概要**: SLA 目標 + RTO + RPO + フェイルオーバー方式 + 計画メンテナンス窓 + Multi-Region vs Multi-AZ。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [09-availability.md C-101〜C-104, C-107](hearing-script/09-availability.md) |
| **hearing-checklist** | §5.1 |
| **proposal** | [§NFR-1 可用性](proposal/nfr/01-availability.md), [§NFR-5 DR](proposal/nfr/05-dr.md), [§C-6 §6.2.4 SLA 別必要構成](proposal/common/06-architecture-decision-hybrid.md) |
| **外部** | [AWS Multi-Region Best Practices](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html) / [Keycloak HA Guide](https://www.keycloak.org/server/concepts-cluster) / [IPA 非機能要求グレード A. 可用性](https://www.ipa.go.jp/sec/softwareengineering/std/ent03-b.html) |

### 6.2 性能・スケール

**概要**: 認証応答時間目標 + ピーク時想定 + Cognito Hard Limit + Keycloak DB チューニング + 規模スケーリング戦略。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [09-availability.md C-105, C-106](hearing-script/09-availability.md) |
| **hearing-checklist** | §5.2 |
| **proposal** | [§NFR-2 性能](proposal/nfr/02-performance.md), [§NFR-3 拡張性](proposal/nfr/03-scalability.md), [§C-1.5 規模スケーリング戦略](proposal/common/01-architecture.md) |
| **内部** | [ADR-006 コスト損益分岐](../adr/006-cognito-vs-keycloak-cost-breakeven.md) |
| **外部** | [AWS Cognito Service Quotas](https://docs.aws.amazon.com/cognito/latest/developerguide/limits.html) / [Keycloak Performance Tuning](https://www.keycloak.org/server/configuration-production) |

### 6.3 セキュリティ NFR + 監査ログ詳細 + Key Management ★拡張

**概要**: 監査ログ詳細（SIEM 連携 / 改ざん防止 / レポート）+ セッションタイムアウト + ペネトレ + **JWT 署名鍵管理（KMS / HSM）** + 暗号化 + ゼロトラスト。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [10-security-compliance.md C-203, C-206-2/3, C-208](hearing-script/10-security-compliance.md) |
| **hearing-checklist** | §5.3 |
| **proposal** | [§NFR-4 セキュリティ](proposal/nfr/04-security.md), [§FR-5.2 セッション TTL](proposal/fr/05-logout-session.md) |
| **内部** | [common/jwks-public-exposure.md](../common/jwks-public-exposure.md) |
| **外部** | [OWASP Top 10 (2021)](https://owasp.org/Top10/) / [NIST SP 800-53 Rev 5](https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final) / [IPA 非機能要求グレード E. セキュリティ](https://www.ipa.go.jp/sec/softwareengineering/std/ent03-b.html) / [CIS Controls v8](https://www.cisecurity.org/controls) / [AWS KMS Best Practices](https://docs.aws.amazon.com/kms/latest/developerguide/best-practices.html) / [Keycloak Key Management](https://www.keycloak.org/server/keys) |

### 6.4 運用 + IaC + CI/CD ★拡張

**概要**: 監視ツール + バージョンアップ方針 + 変更管理プロセス（Git PR ベース）+ **IaC（Terraform / CloudFormation / Helm）** + **CI/CD パイプライン** + Runbook + 緊急対応 Fast Track。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [11-operations.md C-304, C-305, C-306](hearing-script/11-operations.md) |
| **hearing-checklist** | §5.4 |
| **proposal** | [§NFR-6 運用](proposal/nfr/06-operations.md), [§NFR-6.4 構成変更プロセス](proposal/nfr/06-operations.md) |
| **外部** | [AWS Well-Architected Framework - Operational Excellence](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/welcome.html) / [Terraform AWS Provider Cognito](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cognito_user_pool) / [Keycloak Helm Charts](https://github.com/keycloak/keycloak-helm) / [IPA 非機能要求グレード C. 運用・保守性](https://www.ipa.go.jp/sec/softwareengineering/std/ent03-b.html) |

### 6.5 運用体制（24/7 サポート・人員）

**概要**: サポート体制（24/7 / 営業時間）+ Red Hat 利用実績 + RHBK サブスク要否 + 専任 / 兼任 / 外部委託の選択。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [11-operations.md C-301, C-302, D-3](hearing-script/11-operations.md) |
| **hearing-checklist** | §5.4, §2.8 (D-3) |
| **proposal** | [§C-2.3 運用体制](proposal/common/02-platform.md), [§NFR-6 運用](proposal/nfr/06-operations.md) |
| **外部** | [Red Hat Build of Keycloak Subscription](https://access.redhat.com/products/red-hat-build-of-keycloak) / [AWS Enterprise Support](https://aws.amazon.com/premiumsupport/plans/enterprise/) |

### 6.6 コスト・予算

**概要**: 3 年 TCO + RHBK サブスク予算 + 年間予算枠 + ティア別コスト試算。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [11-operations.md C-303, D-4](hearing-script/11-operations.md) |
| **hearing-checklist** | §5.5, §2.8 (D-4) |
| **proposal** | [§NFR-8 コスト](proposal/nfr/08-cost.md), [§C-2.3 コスト比較・TCO](proposal/common/02-platform.md) |
| **内部** | [ADR-006 Cognito vs Keycloak コスト損益分岐 (175K MAU)](../adr/006-cognito-vs-keycloak-cost-breakeven.md) |
| **外部** | [AWS Cognito Pricing](https://aws.amazon.com/cognito/pricing/) / [Red Hat Build of Keycloak Subscription Pricing](https://access.redhat.com/products/red-hat-build-of-keycloak) |

### 6.7 監査ログ・コンプラレポート（独立項目化）

**概要**: 監査ログ保存期間 + ログフォーマット + SIEM 連携 + 改ざん防止 + コンプラ別レポート（SOC 2 / PCI DSS / HIPAA）。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [10-security-compliance.md C-203](hearing-script/10-security-compliance.md) |
| **hearing-checklist** | §5.3 (C-203) |
| **proposal** | [§FR-8.2 監査ログ](proposal/fr/08-admin.md), [§FR-9.2 ログ統合](proposal/fr/09-integration.md), [§NFR-7 コンプライアンス](proposal/nfr/07-compliance.md) |
| **外部** | [Splunk / Datadog SIEM integration patterns](https://www.datadoghq.com/blog/security-monitoring-for-aws-cognito/) / [AWS CloudTrail Best Practices](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/best-practices-security.html) / [Keycloak Event Listener SPI](https://www.keycloak.org/docs/latest/server_development/#_events) |

### 6.8 BCP・DR ランブック

**概要**: 災害復旧手順（Runbook）+ DR 訓練計画 + リハーサル頻度 + 連絡フロー + エスカレーション体制。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [11-operations.md C-306](hearing-script/11-operations.md) + 新規（C-306-2 BCP Runbook）|
| **proposal** | [§NFR-5 DR](proposal/nfr/05-dr.md), [§NFR-6 運用](proposal/nfr/06-operations.md) |
| **外部** | [AWS Disaster Recovery Strategies](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/) / [Keycloak Backup and Restore](https://www.keycloak.org/docs/latest/server_admin/) |

---

## 7. 開発者体験・UX・プライバシー（5 項目、★NEW 章）

> **本章の意義**: 「機能要件 / 非機能要件」の枠に収まらない、**開発者・エンドユーザー・規制対応**の横断観点を集約。CIAM 業界では「**Developer Experience + Privacy**」が独立評価軸として定着（[Kinde 2026 Top 10 Enterprise Auth Providers](https://www.kinde.com/comparisons/what-are-the-top-10-enterprise-authentication-providers-in-2026/)）。

### 7.1 開発者体験（SDK / API ドキュメント / サンプル）★NEW

**概要**: アプリチームの自律性 = ハイブリッド構成の前提。SDK / ドキュメント / サンプルコードの整備。

**提供すべきもの**:
- **フロント SDK**（React / Vue / iOS / Android / Flutter）
- **バックエンド SDK**（Node / Python / Java / Go / .NET）
- **OpenAPI 仕様公開**（管理 API / SCIM API）
- **サンプルコード・チュートリアル**（Quickstart / Common Patterns）
- **Postman Collection**

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | 新規（B-617 等）|
| **proposal** | [§FR-9.1 プロトコル準拠](proposal/fr/09-integration.md) |
| **外部** | [Kinde Top 10 Enterprise Auth Providers 2026](https://www.kinde.com/comparisons/what-are-the-top-10-enterprise-authentication-providers-in-2026/) / [Auth0 SDK Libraries](https://auth0.com/docs/libraries) / [Cognito SDK for JavaScript](https://github.com/aws-amplify/amplify-js) / [Keycloak Adapter Libraries](https://www.keycloak.org/securing-apps/overview) |

### 7.2 アクセシビリティ（WCAG 2.1 / JIS X 8341-3）★NEW

**概要**: ログイン画面のアクセシビリティ。WCAG 2.1 AA 準拠 / スクリーンリーダー対応 / キーボード操作 / カラーコントラスト。

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | 新規（A-11-4 アクセシビリティ要件）|
| **proposal** | [§FR-2.3.3.A ブランディング](proposal/fr/02-federation.md) |
| **外部** | [WCAG 2.1 (W3C)](https://www.w3.org/TR/WCAG21/) / [JIS X 8341-3 (総務省)](https://waic.jp/) / [Microsoft Accessibility for Enterprise](https://www.microsoft.com/en-us/accessibility/) / [Auth0 Accessibility Statement](https://auth0.com/docs/get-started/applications/accessibility) |

### 7.3 多言語対応（i18n / l10n）★NEW

**概要**: 顧客企業がグローバル展開（A-12 = Yes）の場合の必須要件。

**内容**:
- **対応言語**（日 / 英 / 中 / 仏 / 西 等）
- **Cognito Managed Login の言語設定**
- **Keycloak Theme 翻訳**
- **顧客テナント別の言語デフォルト**
- **RTL 言語**（アラビア語 / ヘブライ語）対応

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | 新規（A-12-3 多言語対応要件）|
| **外部** | [Cognito Managed Login Languages](https://docs.aws.amazon.com/cognito/latest/developerguide/managed-login-languages.html) / [Keycloak Internationalization](https://www.keycloak.org/docs/latest/server_admin/#_internationalization-config) |

### 7.4 プライバシー / Cookie Consent / GDPR DSR ★NEW

**概要**: GDPR / CCPA / APPI 対応。Cookie consent UI + プライバシーポリシー + Data Subject Rights（Access / Erasure / Portability）。

**内容**:
- **Cookie consent UI**（同意取得 / 区分 / 撤回）
- **プライバシーポリシー表示**
- **GDPR DSR**: Right to Access / Erasure / Portability / Rectification
- **Cookie 利用区分**: Essential / Analytics / Marketing
- **同意撤回が同意と同じくらい簡単**

| 種別 | 参考資料 |
|---|---|
| **hearing-script** | [10-security-compliance.md C-209](hearing-script/10-security-compliance.md) + 新規（A-12-2 GDPR 詳細、C-209-2 DSR 実装方針）|
| **hearing-checklist** | §2.2 (C-209、不足分は新規)|
| **proposal** | [§NFR-7 コンプライアンス](proposal/nfr/07-compliance.md) |
| **外部** | [GDPR Article 15-22 Data Subject Rights](https://gdpr-info.eu/chapter-3/) / [Secure Privacy Mobile Consent](https://secureprivacy.ai/blog/mobile-app-sdk-consent-management) / [Microsoft GDPR Compliance](https://learn.microsoft.com/en-us/compliance/regulatory/gdpr) / [個人情報保護法（APPI）](https://www.ppc.go.jp/) |

### 7.5 Vendor Lock-in 回避 / Portability ★NEW

**概要**: プラットフォーム選定後の出口戦略。Cognito → Keycloak 移行（または逆）の容易性。

**評価軸**:
- **ユーザー DB のエクスポート形式**（CSV / SCIM）
- **設定の IaC 化**（Terraform / CloudFormation で管理することで移行容易）
- **JWT 署名鍵の portability**
- **監査ログのアーカイブ形式**

| 種別 | 参考資料 |
|---|---|
| **proposal** | [§NFR-9 移行性](proposal/nfr/09-migration.md) |
| **外部** | [SCIM 2.0 (RFC 7644) data portability](https://datatracker.ietf.org/doc/html/rfc7644) / [AWS Cognito User Pool Import/Export](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-using-import-tool.html) / [Keycloak Realm Import/Export](https://www.keycloak.org/server/importExport) |

---

## 8. 元 28 項目 ↔ 新 44 項目のマッピング表

> **目的**: 当初提示された 28 項目が新構造のどこに配置されたか、**抜けがないかの確認**用。

| # | 元 28 項目（ご提示）| 新項目 | 状態 |
|:-:|---|---|:-:|
| 1 | MFA要件 | **3.2 MFA 要件（初回認証）** | ✅ そのまま（#7 から分離、初回 MFA に純化）|
| 2 | SSO方針・セッション信頼方針 | **4.1 SSO 方針 + セッション信頼レベル** | ✅ そのまま |
| 3 | アカウント重複・リンク方針 | **5.4 アカウント重複・リンク方針** | ✅ そのまま |
| 4 | アカウントロック_侵害検出 | **3.3 ローカルユーザー認証ポリシー**（統合）| ✅ パスワード + ロック + 侵害検出 + Bot を統合 |
| 5 | 移行方針・リリース計画 | **1.6 移行方針・リリース計画** | ✅ そのまま（+ Vendor Lock-in 追記） |
| 6 | 規模・規制・コンプライアンス | **2.1 規模・規制・コンプライアンス** | ✅ そのまま（+ A-15 顧客数追記） |
| 7 | 強制再認証・ステップアップ認証 | **4.6 強制再認証・ステップアップ認証（★NEW 独立章）** | ⚠ §3.2 から独立、ポリシー層として整理 |
| 8 | クレーム設計 | **3.4 認可スタンス + JWT クレーム設計 + API 認可フロー** | ⚠ #13 と統合 |
| 9 | 構成概要 | **1.4 構成概要図 / 1.3 アーキテクチャ方針** | ⚠ 細分化 |
| 10 | 顧客別ブランディング | **2.5 顧客別ブランディング** | ✅ そのまま |
| 11 | 製品選定 | **1.5 製品選定** | ✅ そのまま（+ ティア・規模軸明示） |
| 12 | 接続するサービスの情報 | **2.2 顧客 IdP 一覧 + 2.3 接続アプリ・システム一覧** | ⚠ 2 つに分離（IdP vs アプリ）|
| 13 | 認可設定（JWTクレーム）| **3.4 に統合** | ⚠ #8 と統合 |
| 14 | 認証基盤で認証するユーザ | **1.2 認証基盤で認証するユーザ** | ✅ そのまま（P-1〜P-6 + α-δ 拡充） |
| 15 | 非機能_運用 | **6.4 運用 + IaC + CI/CD** | ✅ 拡張（IaC 明示）|
| 16 | 非機能_可溶性・SLA・DR | **6.1 可用性・SLA・DR** | ✅ そのまま |
| 17 | フェデレーションユーザの権限 | **5.2 フェデユーザ権限（デフォルト権限）** | ✅ そのまま |
| 18 | フェデレーションユーザの通知 | **5.3 フェデユーザ通知（Webhook）** | ✅ そのまま |
| 19 | フェデレーションユーザの同期 | **5.1 フェデユーザ同期（JIT / SCIM）** | ✅ そのまま |
| 20 | マルチテナント設計 | **2.4 マルチテナント設計** | ✅ 拡張（分離粒度・規模戦略・Org 機能・特殊顧客 統合）|
| 21 | ローカル認証_パスワードポリシー | **3.3 ローカルユーザー認証ポリシー**（統合改名）| ⚠ #4 と統合（後述 Q1）|
| 22 | ログアウト方針 | **4.2 ログアウト方針 + 4.3 SLO** | ⚠ 細分化 |
| 23 | ログイン方式・画面設定 | **3.1 ログイン方式・画面設定** | ✅ そのまま |
| 24 | 属性マッピング・更新 | **5.5 属性マッピング・更新** | ✅ そのまま |
| 25 | 非機能_運用体制 | **6.5 運用体制** | ✅ そのまま（#15 とは別に保持）|
| 26 | 非機能_コスト・予算 | **6.6 コスト・予算** | ✅ そのまま |
| 27 | 非機能_性能・スケール | **6.2 性能・スケール** | ✅ そのまま |
| 28 | 非機能_セキュリティ | **6.3 セキュリティ NFR + 監査ログ詳細 + Key Management** | ✅ 拡張 |

### 新規追加項目（10 件）

| 新項目 | 不足理由 | 該当 §（既存資料での扱い）|
|---|---|---|
| **1.7 スコープ宣言** | 対象外領域の明示が抜け | §FR-8.3 PAM / 既存資料に散在 |
| **3.3 ローカル認証ポリシー（拡張）** | Bot 保護が抜け | C-205-3 想定 |
| **3.5 ITDR 統合戦略** | 個別検知はあるが統合視点なし | C-217 / 新規 |
| **3.6 認証フロー一覧** | 元の「構成概要」に含む想定だが詳細別出し推奨 | §FR-1.1 / マスター表 C 補足 |
| **4.5 セッション TTL 設計** | C-206 系を独立項目化 | C-206/206-2/206-3 |
| **4.6 強制再認証・ステップアップ認証** | 元 #7 を §3.2 から独立、システム駆動とアプリ駆動を「追加認証要求」ポリシー層として束ねる | C-216 / B-704 / B-605-3 / 新規 |
| **5.6 セルフサービス機能** | 元 28 項目に**なし**（B-402 既存）| §FR-7.3 |
| **5.7 委譲管理（Delegated Admin）** | 元 28 項目に**なし**（B-404 既存）| §FR-8.3 |
| **5.8 ユーザーライフサイクル管理（JML）** | 元 28 項目に**なし**（JML 統合視点）| §FR-7.4 + §FR-2.2.1 |
| **6.7 監査ログ・コンプラレポート** | C-203 のみで詳細浅い | §FR-8.2 / §FR-9.2 |
| **6.8 BCP・DR ランブック** | 6.1 DR とは別の運用視点 | §NFR-5 + §NFR-6 |
| **7.1〜7.5（章 7 全体）** | 元 28 項目に**なし**（業界標準で必須）| 新規 |

### 統合・改名・分離された項目（4 組）

| 元 | 新 | 理由 |
|---|---|---|
| #4 アカウントロック_侵害検出 + #21 ローカル認証_パスワードポリシー | **3.3 ローカルユーザー認証ポリシー** | ローカル認証関連を統合 |
| #8 クレーム設計 + #13 認可設定（JWTクレーム） | **3.4 認可スタンス + JWT クレーム設計 + API 認可フロー** | 重複統合 |
| **#7 強制再認証・ステップアップ認証**（元 #1 と統合予定だった）| **4.6 強制再認証・ステップアップ認証（独立）** | 「初回認証 (#1)」と「追加認証要求 (#7)」は性質が異なるため分離。#7 はシステム駆動 (強制) + アプリ駆動 (ステップアップ) を **追加認証要求ポリシー層** として独立化 |
| #9 構成概要 | **1.3 アーキテクチャ方針 + 1.4 構成概要図** | 細分化 |

---

## 9. PowerPoint スライド構成テンプレ

各大項目を以下の **基本テンプレ 3-5 スライド** で構成：

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
| **§の対応を明示** | 各スライド左下に「§FR-2.3」「B-306」等の対応 ID を小さく表示 |
| **Mermaid 図のスクショ** | proposal 内の Mermaid 図を PNG/SVG で書き出して貼る |
| **本基盤の推奨をハイライト** | ⭐ マークで「本基盤推奨」を明示 |
| **業界実例を 1-2 枚追加** | 「Slack / Auth0 / Microsoft はこの設計」と示すと顧客の納得度向上 |
| **比較表は最大 5 列まで** | スライドで読める列数は 4-5 が限界、それ以上は分割 |

---

## 10. ヒアリング会議への適用

### 3 回ヒアリング計画との対応

| 章 | ヒアリング回 | 含まれる項目 | スライド範囲 |
|---|---|---|---|
| **章 1 全体方針・前提（7）** | **M1** | 1.1〜1.7 全て | 約 28 枚 |
| **章 2 接続元・対象（5）** | **M1** | 2.1〜2.5 全て | 約 20 枚 |
| **章 3 認証方式（6）** | **M2** | 3.1〜3.6 | 約 24 枚 |
| **章 4 SSO・セッション（5）** | **M2 + M3** | M2: 4.1, 4.4 / M3: 4.2, 4.3, 4.5 | 約 20 枚 |
| **章 5 ユーザー管理（8）** | **M2 + M3** | M2: 5.1〜5.5 / M3: 5.6〜5.8 | 約 32 枚 |
| **章 6 非機能要件（8）** | **M3** | 6.1〜6.8 全て | 約 32 枚 |
| **章 7 開発者体験・UX・プライバシー（5）** | **M3** | 7.1〜7.5 全て | 約 20 枚 |

### 想定スケジュール（再計算）

| 回 | スライド範囲 | 時間 | 主な対象者 |
|---|---|---|---|
| **M1 第 1 回** | 章 1（28 枚）+ 章 2（20 枚）= **48 枚** | 2.5 時間 | PO / 事業企画 + テックリード + 情シス |
| **M2 第 2 回** | 章 3（24 枚）+ 章 4 前半（8 枚）+ 章 5 前半（20 枚）= **52 枚** | 2.5 時間 | 開発チーム / テックリード中心 |
| **M3 第 3 回** | 章 4 後半（16 枚、§4.6 含む）+ 章 5 後半（12 枚）+ 章 6（32 枚）+ 章 7（20 枚）= **80 枚** | 3 時間 | インフラ / SRE / セキュリティ + 意思決定者 |

→ **合計 8 時間**（3 回会議）で全 ~180 枚をカバー。M3 が重いため、章 7（開発者体験・UX）を**事前読み合わせ + Q&A 中心**にすれば短縮可能。

---

## 11. 関連ドキュメント

### 一次資料（本基盤の SSOT）

- [hearing-checklist.md](hearing-checklist.md) — 全 127 項目の SSOT
- [proposal/00-index.md](proposal/00-index.md) — 顧客提示版 SSOT
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

## 12. 改訂履歴

| 日付 | 内容 |
|---|---|
| 2026-05-27 | 初版作成。28 項目 → 31 項目（6 章）に再編成、参考資料マトリクス + スライド構成案 + 3 回ヒアリング対応 |
| 2026-06-03 | **業界標準フレームワーク 8 種照合の結果**、31 項目 → **44 項目（7 章）**に拡張。**章 7「開発者体験・UX・プライバシー」を新設**。元 28 項目とのマッピング表を §8 として追加。Q1（セルフサービス vs パスワードポリシー）/ Q2（全件委譲時の管理）への対応を §5.6 / §5.7 に反映 |
| 2026-06-03 | **§3.2 と #7 強制再認証・ステップアップ認証の分離**。元の解釈「#7 = ユーザー駆動のステップアップ」を「#7 = システム駆動 (強制再認証) + アプリ駆動 (ステップアップ)」に再定義。**§3.2 を「初回認証」に純化**し、**§4.6「強制再認証・ステップアップ認証」を新設**（44 項目 → 45 項目）。「追加で認証を要求する」テーマを **ポリシー層 (§4.6)** として束ね、実装技術は §4.3 / §4.5 / §3.5 に委譲する構成に再編 |
