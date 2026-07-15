# PCI DSS v4.0.1 適用範囲・実装ガイド（認証基盤事業者向け）

> **目的**: 本基盤（Keycloak ベース B2B SaaS 認証基盤、CHD 非保持）における PCI DSS v4.0.1 適用範囲、5 従業員類型、Segmentation 3 パターン、責任分担、Trust Portal 設計、契約条項テンプレート、Phase 1-3 移行計画を集約する実装リファレンス。
> **対象読者**: プラットフォーム設計者 / セキュリティ担当 / コンプラ担当 / 法務 / 監査対応担当
> **位置付け**: [common/pci-dss-appi-compliance-gap.md](../common/pci-dss-appi-compliance-gap.md) の v4.0.1 準拠実装ガイド。既存 doc は v4.0.1 verbatim 引用と gap 分析、本 doc は**実装への具体マッピング**を担う。
> **関連**:
> - [common/pci-dss-appi-compliance-gap.md](../common/pci-dss-appi-compliance-gap.md) — v4.0.1 verbatim 引用 + APPI 対応
> - [ADR-032 CIAM プラットフォーム選定](../adr/032-ciam-platform-cost-comparison-10m-mau.md)
> - [ADR-033 Keycloak 2-tier アーキ](../adr/033-keycloak-2tier-broker-idp-architecture.md)
> - [ADR-034 Adaptive Authentication](../adr/034-adaptive-authentication.md)
> - [ADR-036 Customer Audit Support](../adr/036-customer-audit-support.md)
> - [ADR-039 中央集約 Network + 5 アカウント](../adr/039-centralized-network-account-edge-layer.md)
> - [ADR-044 Tabletop Exercise](../adr/044-tabletop-exercise-incident-drill.md)
> - [ADR-045 鍵管理戦略集約](../adr/045-cryptographic-key-management-strategy.md)
> - [ADR-046 Supply Chain Security](../adr/046-supply-chain-security.md)
> - [ADR-053 Observability Strategy](../adr/053-observability-strategy.md)

---

## 目次

1. [Executive Summary](#1-executive-summary)
2. [PCI DSS 適用判定（Cat 1 / 2a / 2b / 3 の 3 カテゴリ）](#2-pci-dss-適用判定cat-1--2a--2b--3-の-3-カテゴリ)
3. [本基盤の Cat 分類（5 アカウント体系マッピング）](#3-本基盤の-cat-分類5-アカウント体系マッピング)
4. [Service Provider ステータス（Level 1 vs Level 2 vs SAQ D-SP）](#4-service-provider-ステータスlevel-1-vs-level-2-vs-saq-d-sp)
5. [従業員範囲マップ（5 類型 verbatim）](#5-従業員範囲マップ5-類型-verbatim)
6. [認証基盤設計への要件マッピング（Req 3/6/7/8/10/11）](#6-認証基盤設計への要件マッピングreq-367810-11)
7. [Segmentation 3 パターン（A / B / C）](#7-segmentation-3-パターンa--b--c)
8. [TPSP 責任分担マトリクス](#8-tpsp-責任分担マトリクス)
9. [12.9.2 契約条項テンプレート](#9-1292-契約条項テンプレート)
10. [Trust Portal 設計指針](#10-trust-portal-設計指針)
11. [Phase 1-3 移行計画](#11-phase-1-3-移行計画)
12. [日本コンテキスト（割賦販売法・JCDSC・QSA）](#12-日本コンテキスト割賦販売法jcdsc-qsa)
13. [業界事例（Auth0 / Okta / Microsoft / AWS）](#13-業界事例auth0--okta--microsoft--aws)
14. [FAQ](#14-faq)
15. [参考文献](#15-参考文献)

---

## 1. Executive Summary

### 決定的な判定

| 論点 | 判定 | 根拠 |
|---|---|---|
| CHD 持たなくても PCI DSS 対象か | ✅ **対象**（Service Provider "could impact security" 節）| PCI SSC Glossary verbatim |
| 認証基盤は Service Provider か | ✅ **Yes**（"authentication server" 明示例）| PCI SSC 2016/2024 Scoping Info Supplement |
| Out-of-Scope 化可能か | ❌ **不可能**（4 条件のうち #3/#4 に該当）| SSC Guidance |
| Multi-tenant SP か | ✅ **Yes**（Appendix A.1 対象）| v4.0.1 §Appendix A.1 |
| Level 判定 | **Level 2 相当**（SAQ D-SP、300K 未満）| Visa/MC 300K 閾値 |
| 全社員が対象か | ❌ **5 類型で異なる** | v4.0.1 Std p.309-333 |
| CDE アクセス社員のみバックグラウンドチェック | ✅ **narrow scope** | v4.0.1 Req 12.7.1 |
| 全社員 Security Awareness 研修必須 | ✅ **"all personnel"** | v4.0.1 Req 12.6.1 |
| JWT 署名鍵は Req 3 対象か | ⚠️ **literal mandate 対象外の可能性**（要 QSA 確認）| Analyst interpretation |
| Segmentation PenTest 周期 | **SP は 6 ヶ月**（Merchant 12 ヶ月）| v4.0.1 Req 11.4.6 |
| Multi-tenant SP: 顧客 PenTest サポート | ✅ **必須** | v4.0.1 Req 11.4.7 |

### 30 秒サマリ

**本基盤は PCI DSS v4.0.1 Level 2 相当の Service Provider として SAQ D-SP + AoC を提供する必要がある**。顧客に CHD 扱う企業が居る限り Out-of-Scope 化は不可能。ただし Segmentation 3 パターンで適用範囲を最小化可能。**5 アカウント体系（ADR-039）+ 2-tier Keycloak（ADR-033）は Cat 分類と自然整合**しており、Auth Acct のみに PCI DSS を限定適用できる設計。**業界標準ポジションは "IDaaS = PCI DSS Level 1 SP"**（Auth0 / Okta）だが、Phase 1 は SAQ D-SP（Level 2）で開始が現実的。

### 2025-03-31 施行済要件（全て mandatory）

**7.x**: 7.2.4 / 7.2.5 / 7.2.5.1
**8.x**: 8.3.6（12 文字 PW）/ 8.3.10.1 / 8.4.2（全 CDE MFA）/ 8.5.1 / 8.6.1-3
**12.x**: 12.5.2.1（SP 限定 半期スコープ確認）/ 12.5.3（SP 限定）/ 12.6.2 / 12.6.3.1 / 12.6.3.2 / 12.10.4.1 / 12.10.5（payment-page bullet）/ 12.10.7

**2026-07 時点で全て mandatory**、"best practice" 猶予期間は終了済。

---

## 2. PCI DSS 適用判定（Cat 1 / 2a / 2b / 3 の 3 カテゴリ）

### 2.1 v4.0.1 のシステム分類（PCI SSC 2016/2024 Info Supplement）

| カテゴリ | 定義 | 例 | 適用要件 |
|---|---|---|---|
| **Cat 1 (CDE)** | CHD/SAD を直接 store/process/transmit | 決済 GW / カード情報 DB | **全要件、年次評価** |
| **Cat 2a (Connected-to)** | CDE に直接/間接接続可能 | Jump host / SIEM / Bastion | **全要件対象** |
| **Cat 2b (Security-Impacting)** | CDE の**セキュリティに影響**するサービス提供 | **認証サーバ（AD 相当）**/ DNS / 監査ログ / パッチ配布 | **全要件対象** |
| **Cat 3 (Out-of-Scope)** | CDE 通信経路なし、CHD 非保持、影響なし | 独立業務系 | 対象外 |

**PCI SSC 公式引用**（Info Supplement Guidance-PCI-DSS-Scoping-and-Segmentation_v1.pdf）:

> **「These systems may... provide security services to the CDE (such as an authentication server like Active Directory), support the requirements of the PCI DSS (like an audit log server), or provide the segmentation that separates the CDE from out-of-scope systems.」**

→ **「Authentication server」が明示的に Cat 2b 例として記載**。本基盤（Keycloak）は該当。

**重要原則**: 「証明されるまで全てスコープ内と仮定」— Segmentation で隔離を証明できて初めて Cat 3 と判定可。

### 2.2 判定フローチャート（本基盤向け）

```
Q1. 本基盤自体が CHD/SAD を store/process/transmit するか?
    ├─ Yes: Cat 1 該当（全要件、年次 RoC/AoC）
    └─ No → Q2 へ

Q2. 顧客テナントに CHD を扱う企業（Merchant）が居るか?
    ├─ No: PCI DSS 適用対象外（Cat 3、要要件定義段階で確定）
    └─ Yes → Q3 へ

Q3. その顧客 CDE への認証を本基盤が担っているか?
    ├─ No（別の認証系統）: 対象外
    └─ Yes → Q4 へ

Q4. 本基盤は Cat 2b (Security-Impacting) に該当するか?
    ★ 該当（Authentication server 明示例）★
    └─ Cat 2b として PCI DSS 全要件対象
       - Req 3.1-3.5（保存 PAN 保護）は非該当（PAN 持たない）
       - Req 3.6/3.7、6、7、8、10、11、12 は大部分適用
       - Service Provider 特有 11 要件も適用
```

### 2.3 Out-of-Scope 化の 4 条件（すべて満たす必要）

PCI SSC Info Supplement より:

1. ❌ CHD 処理しない → 満たす
2. ❌ CHD ネットワークと同一でない → 満たす
3. ❌ CDE に接続できない → **満たさない**（認証で接続する）
4. ❌ Connected-to/Security-Impacting 基準を満たさない → **満たさない**（Authentication Server 該当）

→ **本基盤は Out-of-Scope 化不可能**。#3 と #4 で確定的にスコープ内。

### 2.4 「PAN が本基盤を経由するか」の典型例

| ケース | 判定 |
|---|---|
| JWT に PAN 含める | ❌ 絶対禁止（Cat 1 化してしまう）|
| SAML アサーション属性に BIN+last4 | ⚠️ 議論あり、避けるべき |
| Redirect URL に PAN パラメータ | ❌ 絶対禁止 |
| 顧客 IdP からの userInfo に PAN | ❌ 属性 mapper で除外必須 |
| Session Cache に PAN | ❌ Infinispan に絶対載せない |
| ログに PAN | ❌ 監査ログのマスキング必須 |

**本基盤方針**: **PAN は本基盤経由禁止**を契約 + 技術的に強制（WAF + SDK 検証 + Attribute Mapper）。

---

## 3. 本基盤の Cat 分類（5 アカウント体系マッピング）

### 3.1 5 アカウント体系と Cat 分類

[ADR-039](../adr/039-centralized-network-account-edge-layer.md) の 5 アカウント体系が **PCI DSS Cat 分類と自然整合**:

| アカウント | Cat 分類 | 説明 |
|---|---|---|
| **Auth Acct** | **Cat 2b (Security-Impacting)** | 認証サーバ、Broker + IdP-KC、JWT 発行 |
| **App Acct**（顧客ごと N 個）| **Cat 1 (CDE)**（顧客が CHD 扱う場合）| 顧客側の判断、本基盤責任外 |
| **監査 Acct** | **Cat 2b** | ログ完全性保護、S3 Object Lock 7 年 |
| **Network Acct** | **Cat 2a** or **Cat 2b** | Transit GW / DX、経路上 |
| **ネットワーク監査 Acct** | **Cat 2b** | Shield / Network Firewall / WAF、境界防御 |

### 3.2 Segmentation 境界の設計

```
[外部]
  ↓ WAF / CloudFront
[ネットワーク監査 Acct]（Cat 2b）
  ↓ Shield Advanced / Network Firewall
[Network Acct]（Cat 2a）
  ↓ Transit GW
  ├──→ [Auth Acct]（Cat 2b）
  │      └── Broker Keycloak / IdP-KC / Aurora / KMS
  │
  └──→ [App Acct 1]（Cat 1、顧客 CDE）
       [App Acct 2]（Cat 1、顧客 CDE）
       [App Acct N]（Cat 1、顧客 CDE）

[監査 Acct]（Cat 2b、独立）
  ← CloudTrail Org Trail / 全 Acct のログ集約
```

### 3.3 スコープ縮小の設計原則

- **Auth Acct のみに PCI DSS 主対応**（Cat 2b）
- **App Acct は顧客側の Cat 1 責任**（本基盤の TPSP 責任は Auth Acct のみ）
- **監査 Acct はログ完全性の 12.10 対応**
- **ネットワーク監査 Acct は Segmentation 有効性の 11.4.6 検証対象**

→ **本基盤の PCI DSS 適用範囲は "Auth Acct + 監査 Acct" に限定**、これが SAQ D-SP のスコープ。

---

## 4. Service Provider ステータス（Level 1 vs Level 2 vs SAQ D-SP）

### 4.1 公式定義

**PCI SSC Glossary**:

> **「Business entity that is not a payment brand, directly involved in the processing, storage, or transmission of cardholder data (CHD) and/or sensitive authentication data (SAD) on behalf of another entity. This also includes companies that provide services that control or could impact the security of CHD and/or SAD.」**

後半節が **CHD 非保持でも SP 該当**の根拠。IDaaS / 認証基盤はここ。

### 4.2 Level 判定基準

| Level | 基準 | 検証形態 | 本基盤 |
|---|---|---|---|
| **Level 1** | Visa/MC 各 300K トランザクション/年 超（AMEX 250K）| **QSA 実地 RoC + AoC + 四半期 ASV** | 決済処理しないため通常該当せず |
| **Level 2** | 上記未満 | **SAQ D-SP（自己評価）+ AoC + 四半期 ASV** | **★ 本基盤該当** |

**認証基盤の特殊性**: トランザクション件数を持たないため、Level 判定は Payment Brand の指定に従う。"Impact on security" を根拠に **Level 1 相当が求められるケースあり**（Auth0/Okta 事例）。

### 4.3 SAQ の使い分け

- **RoC**: QSA 現地監査レポート、Level 1 SP 必須
- **SAQ D-SP**: 自己評価版、Level 2 SP 向け、**SP 用 SAQ は D のみ**
- **AoC**: 要約証明書、**顧客への提示物はこれ**

### 4.4 顧客との共有義務（Req 12.9.2）

TPSP は顧客からの PCI DSS 準拠情報要求に応じる義務（v4.x で明文化）。実務は:

- **AoC**（Attestation of Compliance）
- **Responsibility Matrix**（要件ごとに TPSP/顧客/共有 の担当明示）
- **SOC 2 と併せた Trust Portal 配布**

### 4.5 v4.0.1 §12.9.2 の重要な明確化（2025-03-31 施行済）

> **「AoC / website statement / policy / responsibility matrix 単独では written acknowledgment に該当しない。契約書内の明文が必要」**

→ **全 B2B 顧客 MSA/DPA に PCI DSS 12.9.2 準拠の written acknowledgment 条項を含める必要**。Trust portal の Responsibility Matrix だけでは不足。

---

## 5. 従業員範囲マップ（5 類型 verbatim）

### 5.1 5 類型（v4.0.1 Std p.309-333 verbatim ベース）

| 類型 | 該当例（本基盤）| 適用要件 |
|---|---|---|
| **A. CDE アクセス admin / SRE** | Keycloak realm admin / Aurora DBA（token/audit 保持）/ KMS custodian / IAM admin / SOC L2-L3 / CDE VPC engineer / CDE DevOps | **12.7.1**（雇用前バックグラウンドチェック）/ **12.6.1-3 + 12.6.3.1/2**（研修）/ **7.2.4**（半期レビュー）/ **8.x**（MFA + 個人責任）/ **12.10.3/4/4.1**（IR duty） |
| **B. Supporting IT（CDE 非該当）**| Corp IT ヘルプデスク / Endpoint admin / 非 CDE 開発者 / Corp NW admin | **12.6.1-3 + 12.6.3.1/2**（全社員研修）/ **7.2.4**（CDE 隣接アカウント持てば） |
| **C. 非 CDE 開発 / QA** | Segmented out アプリの product engineer | **12.6 研修のみ**、12.7 不適用 |
| **D. Executive / Legal / HR / Sales** | 役員 / HR / 調達 / 営業 / 財務 | **12.6 awareness** + **12.5.3**（重大変更時のスコープレビュー、Exec 報告）/ **12.8.3**（TPSP 選定） |
| **E. Third-party / TPSP スタッフ** | Contract DevOps / offshore SOC / MSSP / ServiceNow SI | **12.7.1**（CDE アクセスあれば必須）/ **12.8.1-5** / **12.9.1/2** / **12.8.5 責任分担マトリクス** / **A.1.x** |

### 5.2 重要な公式引用

**Req 12.6.1（"all personnel"）** — Std p.309:

> **「A formal security awareness program is implemented to make all personnel aware of the entity's information security policy and procedures, and their role in protecting the cardholder data.」**

→ CDE アクセスなくても**全社員が Security Awareness 対象**。営業 / HR / 経営陣も含む。

**Req 12.7.1（narrow scope）** — Std p.314:

> **「Potential personnel who will have access to the CDE are screened, within the constraints of local laws, prior to hire.」**

→ **バックグラウンドチェックは CDE アクセス社員のみ**。非 CDE 社員は不要。

**Req 12.10.3（24/7 On-call）** — Std p.329:

> **「Specific personnel are designated to be available on a 24/7 basis to respond to suspected or confirmed security incidents.」**

→ **24/7 IR On-call を specific personnel として designate 必須**。本基盤の SLA 想定次第で 24/7 or 平日運用の判断。

**Req 12.10.7（PAN 予期せぬ検出）** — Std p.333（2025-03-31 施行済）:

> **「Procedures upon detection of stored PAN anywhere it is not expected: retrieval / secure deletion / migration into CDE, root-cause, remediation.」**

→ **本基盤で PAN が予期せず検出された場合の SOP 整備必須**。認証基盤は PAN を持たない前提だが、SOP は用意しておく。

### 5.3 特権従業員の追加要件

- **8.3.10.1** (SP): パスワード方式のみで顧客リソースアクセスする SP 従業員は **90 日間隔変更**（phishing-resistant MFA 併用で緩和可）
- **8.4.3**: リモート特権アクセスに MFA 必須
- **8.5**: MFA の反自動化・反リプレイ

### 5.4 Phishing-Resistant Authentication による軽減

v4.0.1 明確化: **「Phishing-resistant Authentication Factor（FIDO2/WebAuthn）単独なら MFA 要件バイパス可能」**

→ 全社員に **YubiKey / Passkey** を配布して MFA 要件を効率的にカバー可能（ADR-050 Mobile SDK の WebAuthn Platform と整合）。

### 5.5 v4.0.1 で 12.5.4 は存在しない（訂正）

「12.5.4 strict access control」は v4.0.1 に**存在しない**（過去のドキュメントで参照している場合は訂正必要）。正しくは:

- **12.5.1**: システムコンポーネントインベントリ
- **12.5.2**: PCI DSS スコープ確認（Merchant 年 1 回、SP 12.5.2.1 で半期）
- **12.5.2.1** (SP 限定、2025-03-31 施行済): 半期 + 重大変更時のスコープ確認・文書化
- **12.5.3** (SP 限定、2025-03-31 施行済): 組織変更後のスコープレビュー、結果を Executive 報告

---

## 6. 認証基盤設計への要件マッピング（Req 3/6/7/8/10/11）

### 6.1 Req 8（認証）— 本基盤の中核

| 要件 | 内容 | 本基盤対応 |
|---|---|---|
| **8.3.6** (2025-03-31)| PW 最低 **12 文字** + 英数字 | Keycloak Password Policy 設定 |
| **8.4.2** (2025-03-31)| **全 CDE アクセスに MFA**（旧 admin のみから拡大）| Adaptive Auth（ADR-034）+ 顧客 IdP MFA 継承 |
| **8.5.1** (2025-03-31)| MFA 反射攻撃耐性 + バイパス不可 + ≥2 factor | WebAuthn/FIDO2 で完全対応、TOTP は要注意 |
| **8.6.1-3** (2025-03-31)| Service account 要件（interactive login 制限、ハードコード禁止、Rotation）| AWS Secrets Manager + Workload Identity（ADR-041）|
| **8.3.10.1** (SP)| SP 従業員 90 日 PW ローテ or 動的分析 | Adaptive Auth 動的分析実装 |

### 6.2 Req 10（ログ）

| 要件 | 内容 | 本基盤対応 |
|---|---|---|
| 10.5.1 | 12 ヶ月保持、3 ヶ月 hot | ✅ **7 年保持で余裕**（S3 Object Lock）|
| 10.4.1.1 (2025-03-31)| **自動 SIEM レビュー必須**（手動不可）| ADR-053 Observability + SIEM 連携 |
| 10.2.1 | 認証機構の使用/変更を記録 | Keycloak Event Listener + CloudWatch |

### 6.3 Req 11（テスト）— Service Provider 特有

| 要件 | 内容 | 本基盤対応 |
|---|---|---|
| **11.4.6** | **SP: Segmentation Control PenTest 6 ヶ月ごと**（Merchant 12 ヶ月より厳格）| 半期 PenTest 契約 |
| 11.4.3 | 外部 PenTest 年 1 回 | ADR-044 Tabletop と併用 |
| **11.4.7** | **Multi-tenant SP: 顧客の外部 PenTest サポート必須** | 顧客 PenTest 実施ウィンドウ提供 |
| 11.5.1.1 | SP: 隠れマルウェア通信検出 | IDS/IPS/DPI 導入（ネットワーク監査 Acct）|

### 6.4 Req 3（鍵管理）— **重要な解釈**

**Angle 2 の分析**:

> **「Requirement 3 is scoped to keys used to protect stored account data (PAN). JWT signing keys fall outside Req 3 unless JWT carries PAN.」**

→ **本基盤 ES256 JWT 署名鍵は Req 3.6/3.7 の literal mandate 対象外の可能性大**（JWT に PAN を含まないため）

- ES256 鍵は Req 8/6/2 の一般要件は適用
- 3 階層 KMS（ADR-045）はこれらをカバー
- **ただし "顧客 CDE のセキュリティに影響する鍵" として同等管理が実務上必要**
- **QSA 事前確認推奨**（analyst interpretation）

**追加必要**:
- JWT 署名鍵の **Cryptoperiod 明文化**（推奨 90 日）
- KMS CMK Retention Window 文書化
- **Key Custodian Agreement 書面**

### 6.5 Req 6（サプライチェーン）

| 要件 | 内容 | 本基盤対応 |
|---|---|---|
| **6.3.2** (2025-03-31)| SBOM 必須（第三者ライブラリ含む）| ✅ ADR-046 Supply Chain Security |
| **6.4.2** (2025-03-31)| WAF 必須（automated technical solution）| ✅ ADR-039 5 アカウント + WAF |
| 6.3.3 | 全ソフトウェア パッチ 30 日以内（critical）| Renovate + Ops SOP |

### 6.6 Req 7（アクセス制御）

| 要件 | 内容 | 本基盤対応 |
|---|---|---|
| **7.2.4** (2025-03-31)| **全アカウント + 権限を 6 ヶ月ごとレビュー**（第三者ベンダー含）| Tenant Admin Portal + 軽量 IGA（ADR-037）|
| 7.2.5-5.1 | Application/system accounts least privilege | Workload Identity（ADR-041）|

---

## 7. Segmentation 3 パターン（A / B / C）

### 7.1 パターン A: 完全分離

本基盤 → 顧客 CDE は **JWT/SAML アサーションのみ**、CDE 側は本基盤の公開鍵を "信頼するだけ" で片方向通信。

- **Cat 2a 非該当、Cat 2b のみで範囲限定**
- 5 アカウント体系の **Auth Acct と App Acct 分離**で自然充足
- **推奨**（現状本基盤設計と整合）

```
[Auth Acct (Cat 2b)]
     │
     │ JWT / SAML アサーション（片方向）
     ↓
[App Acct (Cat 1、顧客 CDE)]
```

### 7.2 パターン B: Zone-based Segmentation

Adaptive Auth Risk Engine の顧客連携部分を **別 VPC / 別 Namespace 隔離**。

- **11.4.6 Segmentation Pen Test 半期必須**（SP 頻度）
- **12.5.2.1 スコープ確認半期**

適用場面: 高機密顧客向けの追加隔離要件がある場合。

### 7.3 パターン C: Tokenization / 経由禁止（★ 強く推奨）

顧客 CDE の CHD が**本基盤を絶対通過しない**設計:

- **JWT Claims / SAML 属性に PAN および断片（BIN+last4）を含めない**
- **契約で「顧客が本基盤経由で CHD 送信を禁止」明記**
- **Redirect URL に PAN パラメータブロック**（WAF + SDK 検証）
- **Attribute Mapper で PAN 系属性を絶対除外**

**Auth0/Okta と同スタンス**、業界標準。

### 7.4 Segmentation 検証要件（v4.0.1）

- **11.4.5**: Segmentation Pen Test（Merchant 12 ヶ月）
- **11.4.6**: **SP は 6 ヶ月**（本基盤該当）
- **12.5.2**: 年 1 回スコープ確認
- **12.5.2.1** (SP): **半期スコープ確認**

### 7.5 本基盤の推奨組み合わせ

**パターン A + パターン C の併用**:
- パターン A: 5 アカウント体系による物理分離
- パターン C: PAN 経路の技術的・契約的遮断

→ **Auth Acct のみが Cat 2b、Cat 1 化を確実に回避**。

---

## 8. TPSP 責任分担マトリクス

### 8.1 三者関係

```
[Payment Brand (Visa/MC/AMEX/JCB)] ← Level 分類、AoC 受領
     ↑
[弊社 = TPSP (本認証基盤)]
     ↑ AoC + Responsibility Matrix 提供
[顧客企業 (Merchant)] ← CHD 保持者
     ↑
[Cardholder]

[AWS = Sub-TPSP (本基盤の下請け)]
     ↓ AWS AoC pass-through
[弊社]
```

### 8.2 Responsibility Matrix（本基盤向け完全版）

| Requirement | 弊社 (TPSP) | 顧客 (Merchant) | AWS (Sub-TPSP) | Shared |
|---|:-:|:-:|:-:|:-:|
| **1**（NW セキュリティ）| Auth NW | CDE 側 NW | Infra NW | |
| **2**（システム設定）| Keycloak/Aurora | CDE apps | EC2/RDS デフォルト | |
| **3.1-3.5**（保存 PAN）| N/A（PAN 持たない）| ★ 顧客のみ | N/A | |
| **3.6-3.7**（暗号鍵）| ● JWT/TLS 鍵 | ● CDE 内暗号鍵 | ● KMS infrastructure | |
| **4**（伝送 PAN）| JWT TLS 1.3 | Payment path | ALB/CloudFront TLS | |
| **5**（マルウェア対策）| Container scanning | CDE apps | Hypervisor | |
| **6**（セキュア開発）| Keycloak/SPI | CDE apps | AWS services | |
| **6.3.2 SBOM** | ● | ● | | |
| **6.4.2 WAF** | ● | | ● AWS WAF | |
| **7**（アクセス制御）| Keycloak roles | CDE apps user | IAM | |
| **7.2.4** 半期レビュー | ● | ● | | |
| **8**（認証）| ★ **主要責任** | 本基盤に委譲 | IAM (AWS 側) | ● 顧客 IdP フェデ時 |
| **8.3.6** 12 文字 PW | ● | | | |
| **8.4.2** 全 CDE MFA | ● | | | ● 顧客 IdP MFA と組合せ |
| **9**（物理）| N/A | N/A | ★ AWS | |
| **10**（ログ）| Auth events | CDE apps | Infra logs | |
| **10.4.1.1** SIEM 自動化 | ● | ● | | |
| **10.5.1** 12 ヶ月保持 | ● | ● | | |
| **11.4.3** 外部 PenTest | ● | ● | | |
| **11.4.6** Segmentation PenTest（SP 6 ヶ月）| ● | | | |
| **11.4.7** 顧客 PenTest サポート | ● | | | |
| **12.5.2.1** SP 半期スコープ | ● | | | |
| **12.5.3** 組織変更スコープ | ● | | | |
| **12.6.1-3** Awareness | ● | ● | | |
| **12.7.1** バックグラウンド | ● | ● | | |
| **12.8.5** 責任分担マトリクス | ● | ● | | |
| **12.9.2** written acknowledgment | ● | | | |
| **12.10.3** 24/7 On-call | ● | ● | | |
| **12.10.7** PAN 予期せぬ検出 SOP | ● | ● | | |
| **A.1** Multi-tenant SP | ● | | | |

### 8.3 顧客 IdP フェデ中心の特殊性

- **顧客 IdP 側 パスワード/MFA 実装** = 顧客責任
- **本基盤 Broker の Assertion Validation + Token 発行** = 本基盤責任
- **Keycloak の JIT Provisioning User 属性保護** = 本基盤責任
- **Post-login Landing UX** = 本基盤 Cat 2b

---

## 9. 12.9.2 契約条項テンプレート

### 9.1 契約に含めるべき必須条項

以下を全 B2B 顧客の MSA / DPA に含める:

```
[MSA/DPA 第 X 条: PCI DSS 対応]

第 X.1 条（TPSP としての位置付け）
甲（弊社）は、乙（顧客企業）の Cardholder Data Environment (CDE) の
セキュリティに影響する認証サービスを提供する Third-Party Service 
Provider (TPSP) として、PCI DSS v4.0.1 の該当要件を、責任分担
マトリクス（別紙 A）に定める範囲で維持する責任を有することを、
書面で確認する。

第 X.2 条（PCI DSS 準拠の証明）
甲は、Attestation of Compliance (AoC) を年 1 回更新し、乙および
乙の Qualified Security Assessor (QSA) からの要請に応じて速やかに
提供する。

第 X.3 条（責任分担マトリクスの維持）
甲は、PCI DSS 要件ごとに甲・乙・共有の責任範囲を明示した
Responsibility Matrix（別紙 A）を維持し、乙に提供する。
Matrix の変更時は乙に事前通知する。

第 X.4 条（重大変更・インシデント通知義務）
甲は以下の場合、乙に速やかに書面通知する:
  (1) 甲のシステム構成に PCI DSS 影響のある重大変更が発生した場合
  (2) 甲でセキュリティインシデントが発生した場合
  (3) 甲の PCI DSS 認証状態に変更があった場合
  (4) Sub-processor（AWS 等）の PCI DSS 認証状態に変更があった場合

第 X.5 条（監査協力）
甲は、乙またはその QSA からの正当な照会・監査要請に、Trust Portal
経由または個別対応にて協力する。オンサイト監査については、
別途費用および実施要領を協議する。

第 X.6 条（CHD 送信禁止）
乙は、Cardholder Data (CHD) および Sensitive Authentication Data
(SAD) を甲のシステム（JWT Claims、SAML 属性、Redirect URL、API
パラメータ等の一切）を経由して送信してはならない。甲は、
違反を検知した場合、当該データを速やかに削除し、乙に通知する。

第 X.7 条（Sub-Processor）
甲は、以下の Sub-processor を使用し、それぞれの AoC の pass-through
を乙に提供する:
  - Amazon Web Services (AWS) — Level 1 SP、Coalfire 評価
  - [その他の Sub-processor リスト、変更時は乙に通知]

[別紙 A: Responsibility Matrix]
(本 doc §8.2 参照)
```

### 9.2 v4.0.1 §12.9.2 の重要な明確化

> **「AoC / website statement / policy / responsibility matrix 単独では written acknowledgment に該当しない。契約書内の明文が必要」**

→ Trust Portal に Responsibility Matrix を掲載するだけでは不足、**契約書内の明文が必須**。

---

## 10. Trust Portal 設計指針

### 10.1 ADR-036 との整合性

**現状**: [ADR-036 Customer Audit Support](../adr/036-customer-audit-support.md) は **Scope Reduced**（2026-06-24）で「都度メール対応 + 監査ログ提供」に縮小、Trust Center / Customer Portal は削除された。

**PCI DSS 対応時の再検討要**: PCI DSS 対応が明確化された段階で **Trust Portal 復活を検討推奨**。Auth0/Okta の trust.[domain] パターン参考。

### 10.2 Trust Portal 構成（PCI DSS 対応時）

```
[trust.basis.example.com]（NDA + Portal ログイン後アクセス）

├── Compliance
│   ├── SOC 2 Type II 報告書（要約 + 詳細は NDA）
│   ├── ISO 27001 認証書
│   ├── PCI DSS AoC（SAQ D-SP 版、最新）
│   └── GDPR / APPI 対応体制
│
├── Documents
│   ├── Responsibility Matrix (PDF)
│   ├── Data Processing Addendum (DPA) テンプレート
│   ├── Sub-processor リスト
│   └── Security Whitepaper
│
├── Change Feed
│   ├── AoC 更新通知
│   ├── Sub-processor 変更通知
│   └── Security Incident Disclosure
│
└── Support
    ├── QSA 対応窓口（メール + Ticket）
    ├── FAQ
    └── Security Contact
```

### 10.3 業界事例

| 事業者 | Trust Portal URL |
|---|---|
| Auth0 | https://trust.auth0.com/ |
| Okta | https://security.okta.com/ |
| AWS | https://aws.amazon.com/artifact/ |
| Microsoft | https://servicetrust.microsoft.com/ |

### 10.4 Phase 1 の最小実装

Full Trust Portal を Phase 1 で構築するのは重い。**最小実装**:

1. **静的サイト**（S3 + CloudFront）で NDA 後の Portal 提供
2. **AoC PDF + Responsibility Matrix PDF 掲載**
3. **Change Feed は メール配信**（Phase 2 で自動化）
4. **QSA 対応窓口はメールベース**（Phase 2 で Ticket 化）

---

## 11. Phase 1-3 移行計画

### 11.1 Phase 1（半年〜1 年）: SAQ D-SP 基盤整備

| 対応内容 | 優先度 |
|---|:-:|
| SAQ D-SP 自己評価着手（Gap Analysis）| 🔴 |
| 全 B2B 契約に 12.9.2 written acknowledgment 条項追加 | 🔴 |
| 12.8.5 責任分担マトリクス作成 → Trust Portal（静的）公開 | 🔴 |
| Segmentation PenTest 半期契約締結 | 🔴 |
| Keycloak Password Policy 12 文字化 | 🔴 |
| Adaptive Auth 全 CDE アクセス MFA 強制 | 🔴 |
| 全社員 Security Awareness 年 1 回 + Phishing/Social 研修 | 🔴 |
| CDE アクセス社員のバックグラウンドチェック（雇用前）| 🔴 |
| 24/7 IR On-call designated personnel 明示 | 🔴 |
| 半期スコープ確認 SOP（12.5.2.1）| 🔴 |
| 組織変更時のスコープレビュー SOP（12.5.3）| 🔴 |
| 予期せぬ PAN 検出時 SOP（12.10.7）| 🔴 |
| 全アカウント半期レビュー（7.2.4）| 🔴 |
| Service account 要件（8.6.1-3）| 🔴 |
| 自動 SIEM レビュー（10.4.1.1）| 🔴 |
| Passkey / WebAuthn 全社員配布 | 🟡 |
| JWT 署名鍵 Req 3 スコープ QSA 事前確認 | 🟡 |
| IR Plan 整備 + 年 1 回テスト（ADR-044 統合）| 🟡 |

### 11.2 Phase 2（1-2 年目）: QSA Pre-assessment → 是正 → RoC/AoC

| 対応内容 |
|---|
| QSA 選定（NRI Secure / Deloitte / PwC / BSI / LRQA / ICMS 等）|
| Pre-assessment 実施 |
| Gap 是正（要件別）|
| Level 1 → RoC 目指す場合、Trust Portal 動的化 |
| Sub-processor（AWS）AoC pass-through 運用整備 |
| Bug Bounty / Responsible Disclosure Program 開始 |

### 11.3 Phase 3（3 年目以降）: 継続運用

| 対応内容 |
|---|
| 半期 Scope 確認 |
| 半期 Segmentation Pen Test |
| 年次 QSA 監査 |
| 年次 AoC 更新 |
| 年次 IR Plan テスト（Tabletop）|
| 年次社員 Awareness Training |
| Trust Portal Change Feed 継続更新 |
| Level 2 → Level 1 昇格判断 |

### 11.4 推定コスト

- **SAQ D-SP 準備**: 内部工数 2-3 ヶ月
- **半期 PenTest 契約**: 年 $50K-100K
- **QSA アドバイザリ**（Optional）: $20K-50K/年
- **QSA RoC**（Level 1 目指す場合、Phase 2）: $80K-150K/年
- **Trust Portal 構築**: 静的版 $10K、動的版 $50K-100K

---

## 12. 日本コンテキスト（割賦販売法・JCDSC・QSA）

### 12.1 割賦販売法（2018-06 施行）

**加盟店に "非保持化 or PCI DSS 準拠" を法的義務化**（EC は 2018-03、対面は 2020-03 期限）。

→ 顧客に決済系企業が居る場合、彼らはこの法的義務下にあり、認証委託先（本基盤）にも同等対応を求める。

### 12.2 クレジットカード・セキュリティガイドライン 6.1 版（2026-03-11 公表）

- 6.0 版（2025-03）から**実質変更なし**（普及促進フォーカス）
- **6.0 版 追加内容**: EC 脆弱性対策 / EMV 3-DS / 不正ログイン対策
- **2025-04 以降原則必須**

出典: [クレジット取引セキュリティ対策協議会](https://www.j-credit.or.jp/security/document/index.html)

### 12.3 JCDSC（日本カード情報セキュリティ協議会）

- PCI SSC 公認の日本組織
- PCI DSS 日本語版公開
- 日本市場での PCI DSS 普及の中核

出典: [https://www.jcdsc.org/](https://www.jcdsc.org/)

### 12.4 日本の主要 QSA 企業

| QSA | 特徴 |
|---|---|
| **NRI Secure Technologies** | 国内大手、Cognito 認識高 |
| **Deloitte Tohmatsu Cyber** | 監査法人系、金融業界実績 |
| **PwC Japan** | 監査法人系、規制業種実績 |
| **BSI Group Japan** | JCDSC パートナー、v4.0 セミナー実績 |
| **LRQA Japan** | 旧 Nettitude Japan |
| **ICMS**（国際マネジメントシステム認証機構）| 日本語対応 |
| **TIS / NEC Security / Infoscience** | JCDSC パートナー |

**最新一覧**: [PCI SSC 公式 QSA lookup](https://www.pcisecuritystandards.org/assessors_and_solutions/qualified_security_assessors/)（Japan フィルタ）

### 12.5 JCB Japan の特殊性

JCB は AMEX と同様の独自 SDP プログラムを持つが、実務的には Visa/MC の Level 分類に準拠することが多い。**JCB 加盟店の場合は個別確認**が必要。

---

## 13. 業界事例（Auth0 / Okta / Microsoft / AWS）

### 13.1 Auth0（Okta CIC）

- **2019 年 PCI DSS v3.2.1 Level 1 SP 認定**（IAM プロバイダ業界初、Schellman 評価）
- Trust Portal: [https://trust.auth0.com/](https://trust.auth0.com/)
- 現在 v4.0.1 の状態は要確認（Portal ログイン必須）

### 13.2 Okta

- **2018 年から IDaaS 向け SAQ D AoC 提供**
- 「Okta は顧客 CDE の SP」を明示公表
- Trust Portal: [https://security.okta.com/](https://security.okta.com/)

### 13.3 Microsoft Entra ID

- **Req 10 マッピングガイド公式公開**: [https://learn.microsoft.com/en-us/entra/standards/pci-requirement-10](https://learn.microsoft.com/en-us/entra/standards/pci-requirement-10)
- Azure 全体で PCI DSS Level 1 SP

### 13.4 AWS

- **Level 1 SP、Coalfire 評価**
- Artifact 経由 AoC 取得可能
- Shared Responsibility の infra 部分をカバー（~40% of Req 1/9/10）
- Sub-processor として本基盤が pass-through 利用

### 13.5 業界標準ポジション

**「IDaaS = PCI DSS Level 1 Service Provider」が業界標準ポジション**。本基盤も長期的には Level 1 を目指すのが妥当。Phase 1 は SAQ D-SP（Level 2）で開始。

---

## 14. FAQ

### Q1: 本基盤は CHD 持たないのに、なぜ PCI DSS 対象なのか?

**A**: PCI SSC Glossary の Service Provider 定義に **「services that control or could impact the security of CHD」** が含まれるため。認証サーバは Cat 2b (Security-Impacting) の明示例。

### Q2: 顧客に CHD 扱う企業が居なければ対象外か?

**A**: **Yes、対象外**。ただし将来的に受け入れる可能性を Phase 1 段階で判断が必要（後から SP 認定は工数大）。

### Q3: SAQ D-SP と Level 1 RoC のどちらを目指すべきか?

**A**: **Phase 1 は SAQ D-SP、Phase 2 で判断**。Auth0 は初期 Level 2 → 後に Level 1、Okta は SAQ D で継続。顧客要求次第。

### Q4: 全社員が Security Awareness 対象なのか?

**A**: **Yes、12.6.1 は "all personnel"**。ただし 12.7.1 のバックグラウンドチェックは CDE アクセス社員のみ。

### Q5: JWT 署名鍵は Req 3 対象か?

**A**: **literal mandate 対象外の可能性大**（PAN 含まないため）。ただし "顧客 CDE のセキュリティに影響する鍵" として同等管理が実務上必要。**QSA 事前確認推奨**。

### Q6: 5 アカウント体系で全て対象か?

**A**: **Auth Acct と 監査 Acct が Cat 2b で対象**、App Acct は顧客責任（Cat 1）。ネットワーク Acct と ネットワーク監査 Acct は Cat 2a/2b。

### Q7: Passkey / WebAuthn で MFA 要件を代替できるか?

**A**: **Yes、v4.0.1 で明確化された Phishing-resistant Authentication に該当**。全社員 Passkey 配布で MFA 要件を効率的にカバー可能。

### Q8: Trust Portal は必須か?

**A**: **契約書内の 12.9.2 written acknowledgment は必須**、Trust Portal は推奨（業界標準）。ADR-036 の「都度メール対応」から Trust Portal 復活を再検討。

### Q9: 12.5.4 は何か?

**A**: **v4.0.1 に 12.5.4 は存在しない**。12.5 は 12.5.1 / 12.5.2 / 12.5.2.1 / 12.5.3 のみ。過去ドキュメントで参照している場合は訂正必要。

### Q10: 半期 Pen Test の対象範囲は?

**A**: **Segmentation Control の有効性**（Cat 2b と Cat 1 の分離が実効的か）。全システム PenTest は年次 (11.4.3)。SP は半期の Segmentation 検証が追加要件。

---

## 15. 参考文献

### PCI SSC 公式

- [PCI SSC Homepage](https://www.pcisecuritystandards.org/)
- [PCI SSC Glossary](https://www.pcisecuritystandards.org/glossary/)
- [PCI DSS v4.0.1 (Middlebury mirror)](https://www.middlebury.edu/sites/default/files/2025-01/PCI-DSS-v4_0_1.pdf)
- [SAQ D for Service Providers v4.0](https://listings.pcisecuritystandards.org/documents/PCI-DSS-v4-0-SAQ-D-Service-Provider.pdf)
- [Guidance for PCI DSS Scoping and Network Segmentation](https://listings.pcisecuritystandards.org/documents/Guidance-PCI-DSS-Scoping-and-Segmentation_v1.pdf)
- [Third-Party Security Assurance Info Supplement (2016)](https://listings.pcisecuritystandards.org/documents/ThirdPartySecurityAssurance_March2016_FINAL.pdf)
- [PCI SSC QSA Directory](https://www.pcisecuritystandards.org/assessors_and_solutions/qualified_security_assessors/)
- [PCI SSC 日本語ミニサイト](https://www.pcisecuritystandards.org/minisite/ja-ja/)
- [PCI SSC Blog: Just Published PCI DSS v4.0.1](https://blog.pcisecuritystandards.org/just-published-pci-dss-v4-0-1)
- [PCI SSC Blog: Now is the Time to Adopt Future-Dated Requirements](https://blog.pcisecuritystandards.org/now-is-the-time-for-organizations-to-adopt-the-future-dated-requirements-of-pci-dss-v4-x)

### Card Brand

- [Visa CISP / AIS Small Business Security](https://usa.visa.com/support/small-business/security-compliance.html)
- [Visa Global Registry of Service Providers](https://usa.visa.com/splisting/splistinglearnmore.html)
- [Mastercard SDP — Service Providers Need to Know](https://www.mastercard.com/global/en/business/overview/safety-and-security/security-recommendations/site-data-protection-PCI/service-providers-need-to-know.html)
- [JCB Data Security Program](https://www.global.jcb/en/products/security/data-security-program/index.html)

### 業界解説

- [SecurityMetrics: Guide to New Requirements in PCI DSS 4.0.1](https://www.securitymetrics.com/blog/a-guide-to-new-requirements-in-pci-dss-4-0-1)
- [Schellman: New MFA Requirements in PCI DSS v4](https://www.schellman.com/blog/pci-compliance/new-mfa-requirements-in-pci-dss-v4)
- [Schellman: PCI DSS TPSP Requirements](https://www.schellman.com/blog/pci-compliance/pci-dss-tpsp-requirements)
- [Auditwerx: 12.8.5 Vendor Oversight in v4.0.1](https://auditwerx.com/pci-4-0-1-requirement-12-8-5-vendor-oversight-responsibility-matrices-and-scope-implications/)
- [PCI Policies: Req 12.9.2 written acknowledgment](https://pcipolicies.com/blogs/news/how-to-be-a-better-pci-third-party-service-provider-requirement-12-9)
- [PCI DSS Guide: SAQ D for Service Providers](https://pcidssguide.com/pci-saq-d/)
- [Elisity: PCI DSS 4.0 Segmentation](https://www.elisity.com/blog/pci-dss-4-0-network-segmentation-requirements)

### Cloud / IDaaS 事例

- [AWS PCI DSS Compliance FAQ](https://aws.amazon.com/compliance/pci-faqs/)
- [Auth0: PCI DSS Level 1 Validation (2019)](https://auth0.com/blog/auth0-completes-pci-dss-validation-for-iam/)
- [Auth0 Trust Center](https://trust.auth0.com/)
- [Okta: PCI DSS Compliance](https://support.okta.com/help/s/article/PCI-DSS-Compliance-With-Okta)
- [Okta Security Trust Center](https://security.okta.com/)
- [Microsoft Entra ID: PCI Req 10](https://learn.microsoft.com/en-us/entra/standards/pci-requirement-10)

### 日本

- [クレジット取引セキュリティ対策協議会](https://www.j-credit.or.jp/security/document/index.html)
- [JADMA 6.1 版通知](https://jadma.or.jp/news/j-credit61_0312)
- [METI 6.0 版プレスリリース](https://www.meti.go.jp/press/2024/03/20250305002/20250305002.html)
- [JCDSC](https://www.jcdsc.org/)
- [JCDSC v4.0.1 news](https://www.jcdsc.org/news/241029.php)
- [PwC Japan: 割賦販売法対応](https://www.pwc.com/jp/ja/services/digital-trust/cyber-security-consulting/pcidss.html)
- [NRI Secure: 割賦販売法対応](https://www.nri-secure.co.jp/blog/security-measures-for-revised-kappu-hanbaihou)

### 本プロジェクト内 関連 doc

- [common/pci-dss-appi-compliance-gap.md](../common/pci-dss-appi-compliance-gap.md) — v4.0.1 verbatim 引用 + APPI 対応
- [ADR-032 CIAM プラットフォーム選定](../adr/032-ciam-platform-cost-comparison-10m-mau.md)
- [ADR-033 Keycloak 2-tier アーキ](../adr/033-keycloak-2tier-broker-idp-architecture.md)
- [ADR-034 Adaptive Authentication](../adr/034-adaptive-authentication.md)
- [ADR-036 Customer Audit Support](../adr/036-customer-audit-support.md)
- [ADR-039 中央集約 Network + 5 アカウント](../adr/039-centralized-network-account-edge-layer.md)
- [ADR-044 Tabletop Exercise](../adr/044-tabletop-exercise-incident-drill.md)
- [ADR-045 鍵管理戦略集約](../adr/045-cryptographic-key-management-strategy.md)
- [ADR-046 Supply Chain Security](../adr/046-supply-chain-security.md)
- [ADR-053 Observability Strategy](../adr/053-observability-strategy.md)

---

## 改訂履歴

- 2026-07-15: 初版作成。5 Angle 独立調査 + 完全版レポートの統合結果を集約。PCI DSS v4.0.1 適用判定 3 カテゴリ / 本基盤 5 アカウント体系との Cat マッピング / SAQ D-SP + Level 判定 / 従業員 5 類型 verbatim / Segmentation 3 パターン (A/B/C) / TPSP Responsibility Matrix 完全版 / 12.9.2 契約条項テンプレート / Trust Portal 設計指針 / Phase 1-3 移行計画 / 日本コンテキスト (割賦販売法・JCDSC・QSA) / 業界事例 (Auth0/Okta/MS/AWS) / FAQ 10 項目を集約。既存 [pci-dss-appi-compliance-gap.md](../common/pci-dss-appi-compliance-gap.md) の実装ガイド版として補完位置付け
