# PCI DSS v4.0.1 + APPI 準拠ギャップ分析 — 一次資料引用集 + 必須対応リスト

> **作成日**: 2026-06-08
> **最終更新**: **2026-07-08 §2.A / §3.2.0 追記**（Consumer / Cashier アカウント除外の判定 + Req 8 Applicability Notes verbatim 引用 + 3 シナリオ比較 + 業界事例）
> **対象**: AWS 認証基盤 PoC（Keycloak v26.2、Stage A 完了状態）
> **規制バージョン**: PCI DSS v4.0.1（2024-06 発行、2025-03-31 future-dated 要件完全強制）+ APPI 令和 4 年改正（PPC ガイドライン 通則編 令和 8 年 4 月一部改正版）
> **一次資料**:
> - PCI DSS v4.0.1 PDF（`doc/old/PCI-DSS-v4_0_1.pdf`、gitignore 済、PCI SSC 配布物）
> - PPC ガイドライン 通則編 PDF（[公開 URL](https://www.ppc.go.jp/files/pdf/260401_guidelines01.pdf)）
>
> **関連**:
> - [§FR-7.4.8 PCI DSS / APPI 適合性整理](../requirements/proposal/fr/07-user.md) — JIT/SCIM 選定への影響
> - [§NFR-4 セキュリティ](../requirements/proposal/nfr/04-security.md) — セキュリティベースライン
> - [§NFR-7 コンプライアンス](../requirements/proposal/nfr/07-compliance.md) — 規制対応方針
> - [phase10-stage-a-verification.md](phase10-stage-a-verification.md) — Stage A 現状

---

## 目次

1. [エグゼクティブサマリー](#1-エグゼクティブサマリー)
2. [PCI DSS スコープ判定（最重要ゲーティング論点）](#2-pci-dss-スコープ判定最重要ゲーティング論点)
2.A. [Consumer（カード会員）アカウント除外の判定（2026-07-08 追加）](#2a-consumerカード会員アカウント除外の判定2026-07-08-追加)
3. [PCI DSS v4.0.1 一次資料 verbatim 引用](#3-pci-dss-v401-一次資料-verbatim-引用)
4. [APPI 一次資料 verbatim 引用](#4-appi-一次資料-verbatim-引用)
5. [現状 × PCI DSS 要件マッピング](#5-現状--pci-dss-要件マッピング)
6. [現状 × APPI 要件マッピング](#6-現状--appi-要件マッピング)
7. [必須対応 Top 12（優先度・工数・対応場所）](#7-必須対応-top-12優先度工数対応場所)
8. [要件定義で確定すべき 10 ゲーティング論点](#8-要件定義で確定すべき-10-ゲーティング論点)
9. [Stage B / C への追加スコープ](#9-stage-b--c-への追加スコープ)
10. [参考文献](#10-参考文献)

---

## 1. エグゼクティブサマリー

### 30 秒で言える結論

> 本基盤は **APPI は適用必至** (PII を取扱う以上自動適用)。**PCI DSS は『本基盤を経由する HTTP リクエスト/レスポンスに PAN が含まれるか』で In-Scope/Out-of-Scope が決まる**。In-Scope なら Req 1〜12 全適用で工数 2-3 ヶ月、Out-of-Scope なら Req 8 (認証) / Req 10 (ログ) の一部が「CDE 連携基盤」として参考適用。
>
> 現状 (Stage A 完了) の **最大ギャップは 3 つ**: ① 監査ログ 12 ヶ月保存 (PCI Req 10.5.1)、② Phishing-resistant MFA (PCI Req 8.4 + NIST SP 800-63B Rev 4)、③ 漏えい等報告 SOP (APPI 法 26 + 規則 7・8 条)。これらは In-Scope/Out-of-Scope どちらでも対応必須。
>
> APPI の **漏えい報告閾値は「5 件以上」ではなく、不正アクセス起因なら 1 件でも報告対象**（規則第 7 条第 3 号）。件数閾値が効くのは規則第 7 条第 4 号「千人を超える」場合のみ。
>
> **PCI DSS Consumer 除外は本基盤に適用されない**（2026-07-08 追加、[§2.A](#2a-consumerカード会員アカウント除外の判定2026-07-08-追加) 参照）：Req 8 の Consumer / ショッパー アカウント除外は E コマース サイト向け。本基盤は B2B SaaS 従業員認証専用のため、**社員が個人カードで出張予約 SaaS を使う場合でも Employee アカウント扱い**で Req 8 全面適用（判定はアカウント種別で決まり、カードの持ち主では決まらない）。

### 最大ギャップ Top 5

| # | カテゴリ | ギャップ | 規制根拠 | 工数 |
|---|---|---|---|---|
| 1 | **監査ログ長期保存** | CloudWatch 7d retention → 12ヶ月＋3ヶ月即時アクセス要 | PCI Req 10.5.1 + APPI 法 23 安全管理措置 | 2-3w |
| 2 | **Phishing-resistant MFA** | TOTP のみ → WebAuthn/Passkeys 必要 | PCI Req 8.4 + NIST SP 800-63B Rev 4 | 2-3w |
| 3 | **漏えい等報告 SOP** | 検知・速報（3-5 日）・確報（30 日 / 不正アクセス 60 日）の Runbook 未構築 | APPI 法 26 + 規則 7・8 条 | 2-3w |
| 4 | **委託先監督契約** | AWS / Auth0 / Entra ID の DPA / BAA 未整理 | APPI 法 25 + 28（外国提供）| 2-3w |
| 5 | **KMS Customer-Managed Key** | AWS 管理鍵のみ、本番は CMK + ローテーション要 | PCI Req 3.5 + 3.6 | 2-3d |

---

## 2. PCI DSS スコープ判定（最重要ゲーティング論点）

### 判定フロー

```
┌─ 顧客がカード会員データを処理するか? ─┐
│                                       │
└──────────────┬────────────────────────┘
               │
           Yes │   No
               │   └─→ PCI DSS 不適用（終了）
               │
       ┌───────▼────────────────────┐
       │ PAN が本基盤を経由するか?  │
       └───────┬────────────────────┘
               │
           Yes │   No
               │   │
               │   └─→ Out-of-Scope（認証 / ロール情報のみ）
               │       ※ ただし「CDE 連携基盤」として Req 8 / 10 一部適用
               │
       ┌───────▼─────────────────────┐
       │ In-Scope: PCI DSS 完全準拠 │
       │ Req 1-12 全適用             │
       │ - 年 1 回ペネトレ           │
       │ - 年 1 回 SAQ 提出          │
       │ - QSA 監査 (Level 1 の場合) │
       └─────────────────────────────┘
```

### 「PAN が本基盤を経由するか」の典型例

| パターン | PAN 経由 | 判定 |
|---|---|---|
| 認証 token のクレームに PAN が含まれる | ✅ 経由 | **In-Scope** |
| API リクエストヘッダに PAN | ✅ 経由 | **In-Scope** |
| 認証画面で PAN を入力するフロー | ✅ 経由 | **In-Scope** |
| 認証は OIDC で完結、PAN は別パスでアプリ → 決済代行へ直送 | ❌ 不経由 | Out-of-Scope |
| Auth0 Action / Keycloak Mapper で PAN を加工 | ✅ 経由 | **In-Scope** |

**本基盤の現状想定 (Phase 8/9 SaaS シナリオ)**: 経費精算 SaaS の認証なので PAN を直接扱わない設計 → **Out-of-Scope の前提**。ただし将来「決済機能を持つ顧客アプリで本基盤を使う」場合は In-Scope 化する。

---

## 2.A Consumer（カード会員）アカウント除外の判定（2026-07-08 追加）

> **背景**：PCI DSS v4.0.1 の Requirement 8 には **Consumer（カード会員 / ショッパー）アカウント除外条項** がある。本基盤への適用可否を明確化する。

### 2.A.1 除外条項の存在（結論）

PCI DSS v4.0.1 Requirement 8 の **Applicability Notes / Overview** に、以下 2 種類の除外条項が明記されている:

- **Consumer 除外**：E コマース サイトのショッパー アカウント（マーチャントの Web サイトで消費者が使うアカウント）
- **Cashier 除外**：POS 決済アプリの単一トランザクション用アカウント（1 度に 1 カード番号のみアクセス可能）

一次資料 verbatim は §3.2.0 参照。

### 2.A.2 判定原則：アカウント種別 ≠ カード種別

Consumer 除外の判定は **「そのアカウントが何のためのアカウントか」** で決まる。**「誰のカードで払うか」ではない**。

| 判定軸 | Consumer 除外に効くか |
|---|:---:|
| **アカウント種別**（consumer / employee / admin）| ✅ **効く** |
| ~~カード種別~~（personal / corporate）| ❌ 効かない |
| ~~決済の目的~~（業務 / プライベート）| ❌ 効かない |
| ~~支払者~~（本人 / 会社 / 立替）| ❌ 効かない |

**設計思想**：PCI DSS の目的は「カードデータの保護」であり「消費者の権利保護」ではない。Consumer 除外の理由は**認証セキュリティを consumer に強制すると非現実的**（数千万〜数億のアカウントに MFA 強制不可能）だから。「Consumer だからカードを保護しなくていい」ではない。

### 2.A.3 典型 3 シナリオ比較（旅行予約サイトを例に）

| シナリオ | 例 | 認証経路 | アカウント種別 | Consumer 除外 | 本基盤の関与 |
|---|---|---|---|:---:|:---:|
| **A. B2B 出張予約 SaaS**| SAP Concur / Navan / TravelPerk / Egencia | 本基盤 SSO 経由 | **Employee アカウント** | ❌ 適用不可 | ✅ Connected-to CDE |
| **B. B2C 一般旅行サイト**| Expedia / じゃらん / 楽天トラベル | サイト独自ログイン | **Consumer アカウント** | ✅ 適用可能 | ❌ 無関係 |
| **C. ハイブリッド（福利厚生）**| 会社契約の旅行 SaaS を業務 + プライベート両方に使える | 本基盤 SSO 経由 | **Employee アカウント**（利用目的が混在でも）| ❌ 適用不可 | ✅ Connected-to CDE |

**含意**：**「社員が個人カードで払う」場合でも、本基盤 SSO 経由で認証している以上 Employee アカウント扱い**（シナリオ A / C）。Consumer 除外は適用されず、PCI DSS Req 8 が全面適用。

**業界事例**：
- **SAP Concur**：PCI DSS Level 1 準拠、Consumer 除外は使わず全 Req 8 適用（[Concur Compliance](https://www.concur.com/security)）
- **Navan (TripActions)**：同様
- **Amazon.com Consumer accounts**：Req 8 除外、ただし内部 Employee アカウントは厳格適用
- **Netflix / Booking.com**：Consumer accounts のみ除外適用

### 2.A.4 本基盤の各アカウントカテゴリでの適用性

| 本基盤ユーザー | Consumer 該当性 | Consumer 除外 | Req 8 適用 |
|---|:---:|:---:|:---:|
| **P-1 弊社運用者**| ❌ Not consumer | ❌ 適用不可 | ✅ **strictest** |
| **P-2 テナント管理者**| ❌ Not consumer（顧客社員）| ❌ 適用不可 | ✅ 全面適用 |
| **P-3 現行 IdP あり従業員**| ❌ Not consumer（顧客社員）| ❌ 適用不可 | ✅ 全面適用 |
| **P-4 現行 IdP なし従業員**（外部協力者）| ❌ Not consumer（B2B 外部委託先）| ❌ 適用不可 | ✅ 全面適用 |
| ~~B2C エンドユーザー~~ | ~~✅ Consumer~~ | ~~✅ 除外可能~~ | ~~⚠ 除外対象~~ |

**本基盤は B2B SaaS 専用と確定済み**（[project_scope_redesign_phase1](../../../.claude/projects/-Users-suepie-Develop-10-project-aws-atuh-poc/memory/project_scope_redesign_phase1.md)、Phase 1 確定）→ **Consumer 除外条項は本基盤の全ユーザーに適用されない**。

### 2.A.5 「個人カード情報」の扱いは別議題

Consumer 除外とは別に、**社員個人カード情報の扱い**は APPI / GDPR / 労務管理側の別議題:

| 規制 | 個人カード情報 が関わる論点 | 本基盤への直接影響 |
|---|---|:---:|
| **APPI**（日本）| 社員個人カード情報 = 個人情報。会社が経費精算等で "見る" と 委託関係 or 第三者提供の議論（第 25 / 27 条）| ❌ 保管しないため無し |
| **GDPR**（EU）| Personal financial data、purpose limitation（Art. 5(1)(b)）で厳格運用が必要 | ❌ 保管しないため無し |
| **労務管理**（日本）| 会社が個人カード情報を扱う際の社員同意 + 利用範囲明示（労働契約法・就業規則）| ❌ 認証のみのため無し |

**本基盤は個人カード情報を一切保管しない**ため、これらの追加規制負担は発生しない（PAN を扱う顧客アプリ側の責任）。

### 2.A.6 判定フローの追記

§2 の判定フローに **Consumer 除外分岐** を追加すると:

```
┌─ 顧客がカード会員データを処理するか? ─┐
│                                       │
└──────────────┬────────────────────────┘
               │
           Yes │   No → PCI DSS 不適用（終了）
               │
       ┌───────▼────────────────────┐
       │ PAN が本基盤を経由するか?  │
       └───────┬────────────────────┘
               │
           No  │   Yes → In-Scope
               │
       ┌───────▼─────────────────────────────┐
       │ 本基盤の利用者は Consumer か?      │
       │ （E コマース ショッパー等）        │
       └───────┬─────────────────────────────┘
               │
           Yes │   No
               │   │
               │   └─→ **Connected-to CDE**
               │       Req 8 全面適用（本基盤の位置）
               │
               ▼
     ✅ **Req 8 Consumer 除外適用可**
       （B2C E コマース の場合のみ）
       ※ 本基盤は B2B SaaS 専用のため到達せず
```

→ **本基盤は "B2B SaaS 専用 + PAN 不経由" のため、Consumer 除外分岐に到達せず Connected-to CDE として Req 8 全面適用**。

---

## 3. PCI DSS v4.0.1 一次資料 verbatim 引用

> **出典**: Payment Card Industry Data Security Standard: Requirements and Testing Procedures, **Version 4.0.1, June 2024**, PCI Security Standards Council
> **PDF**: `doc/old/PCI-DSS-v4_0_1.pdf` (gitignore 済、PCI SSC 配布物のため社内利用のみ)

### 3.1 future-dated requirements の完全強制日

PCI DSS v4.0.1 文中の typical phrasing（複数 sub-req で同一文言）:

> "This requirement is a best practice until **31 March 2025**, after which it will be required and must be fully considered during a PCI DSS assessment."

→ **2025-03-31 まで「best practice」（推奨）、それ以降「required」（必須）**。本基盤の本番稼働が 2025-04 以降なら future-dated 要件は完全強制対象。

### 3.2 Requirement 8: 認証

#### Req 8 章タイトル

> "Requirement 8: **Identify Users and Authenticate Access to System Components**"

#### 3.2.0 Req 8 Applicability Notes（2026-07-08 追加、Consumer / Cashier 除外の一次資料）

**Consumer（カード会員）アカウント除外**：

> **"Requirement 8 does not apply to consumer accounts, which are accounts used by consumers to perform e-commerce transactions on a merchant's website (customer or shopper accounts)."**

**日本語意訳**：Requirement 8 は、**マーチャントのウェブサイトで E コマース取引を行うために消費者が使用するアカウント**（カスタマー・アカウント / ショッパー・アカウント）には適用されない。

**Cashier（レジ担当）アカウント除外**：

> **"Requirement 8 is not intended to apply to user accounts within a point-of-sale (POS) payment application that only have access to one card number at a time in order to facilitate a single transaction (such as cashier accounts)."**

**日本語意訳**：POS 決済アプリ内の、単一トランザクションを処理するために **1 度に 1 つのカード番号にしかアクセスできないユーザーアカウント**（レジ担当アカウント等）には Requirement 8 を適用することを意図していない。

**判定原則**（キーワード分析）:

| キーワード | 意味 | 判定への効果 |
|---|---|---|
| **"used by consumers"** | 消費者が使う | ✅ 用途主体で判定 |
| **"e-commerce transactions"** | E コマース取引 | ✅ 取引種別 |
| **"merchant's website"** | マーチャント（販売者）のウェブサイト | ✅ サイト種別 |
| **"customer or shopper accounts"** | カスタマー・アカウント / ショッパー・アカウント | ✅ アカウント種別 |
| ~~カードの持ち主~~ | 個人 vs 法人カード | ❌ **文言上、一切言及なし** |

→ **本基盤は B2B SaaS 従業員認証専用のため、いずれの除外も適用対象外**（[§2.A](#2a-consumerカード会員アカウント除外の判定2026-07-08-追加) 参照）。

**追加参照**（PCI SSC 公式 FAQ）：
- [PCI SSC FAQ Search](https://www.pcisecuritystandards.org/faqs/)：`consumer accounts` で検索、"Are consumer accounts subject to PCI DSS Requirement 8?" 等の関連 FAQ 多数
- [PCI SSC Blog - Common Questions on PCI DSS Applicability](https://blog.pcisecuritystandards.org/)

#### Req 8.1〜8.6 トップレベル要件

> 8.1 Processes and mechanisms for identifying users and authenticating access to system components are defined and understood.
> 8.2 User identification and related accounts for users and administrators are strictly managed throughout an account's lifecycle.
> 8.3 Strong authentication for users and administrators is established and managed.
> 8.4 Multi-factor authentication (MFA) is implemented to secure access into the CDE.
> 8.5 Multi-factor authentication (MFA) systems are configured to prevent misuse.
> 8.6 Use of application and system accounts and associated authentication factors is strictly managed.

#### Req 8.2.5 退職ユーザーアクセスの即時無効化

> "8.2.5 **Access for terminated users is immediately revoked.**"

Testing Procedure:
> "8.2.5.a Examine information sources for terminated users and review current user access lists—for both local and remote access—to verify that terminated user IDs have been deactivated or removed from the access lists."

Purpose:
> "If an employee or third party/vendor has left the company and still has access to the network via their user account, unnecessary or malicious access to cardholder data could occur..."

→ **本基盤への意味**: JIT のみ顧客では即時無効化が顧客 IdP に依存 → SCIM 推奨。JIT のみなら定期バッチ + 契約で deprovision 責任明示。

#### Req 8.2.6 90 日未使用ユーザーの無効化

> "8.2.6 **Inactive user accounts are removed or disabled within 90 days of inactivity.**"

Testing Procedure:
> "8.2.6 Examine user accounts and last logon information, and interview personnel to verify that any inactive user accounts are removed or disabled within 90 days of inactivity."

→ **本基盤への意味**: **[jit-scim-coexistence-keycloak.md §10.4.A](jit-scim-coexistence-keycloak.md)** の Event Listener SPI + `user_attribute.last_login` + kcadm.sh バッチで対応（**⚠ 2026-07-09 訂正**：旧 §10.4 は `event_entity` 依存で 10M MAU では 9 億行 DB 肥大化 + `user_session` は 10h で消滅のため破綻。[ADR-060 §C.2.2](../adr/060-auth-protocol-attack-path-residual-tbd.md) SPI 拡張と統合）。**JIT/SCIM 判別ロジックは [§10.4.B](jit-scim-coexistence-keycloak.md)** 参照（scim_active=true が最強の削除禁止フラグ）。

#### Req 8.3.1 認証要素 (3 種類のいずれか必須)

> "8.3.1 All user access to system components for users and administrators is authenticated via at least one of the following authentication factors:
> • Something you know, such as a password or passphrase.
> • Something you have, such as a token device or smart card.
> • Something you are, such as a biometric element."

#### Req 8.3.6 パスワード長・複雑性

> "8.3.6 If passwords/passphrases are used as authentication factors to meet Requirement 8.3.1, they meet the following minimum level of complexity:
> • **A minimum length of 12 characters** (or IF the system does not support 12 characters, a minimum length of eight characters).
> • Contain both numeric and alphabetic characters."

→ **本基盤への意味**: Keycloak Realm Password Policy で `length(12)` + `digits(1)` + `notUsername(undefined)` 等を設定。

#### Req 8.3.9 パスワード単独 (single-factor) 利用時の制約

> "8.3.9 If passwords/passphrases are used as the only authentication factor for user access (i.e., in any single-factor authentication implementation) then either:
> • **Passwords/passphrases are changed at least once every 90 days,** OR
> • The security posture of accounts is dynamically analyzed, and real-time access to resources is automatically determined accordingly."

→ **本基盤への意味**: MFA を全アクセスに必須化（= MFA 強制）すれば 8.3.9 は適用外。SaaS 認証基盤として MFA 必須化が現実的。

#### Req 8.3.10 / 8.3.10.1 Service Provider の追加要件

> "8.3.10 / 8.3.10.1 Additional requirement for service providers only: If passwords/passphrases are used as the only authentication factor for customer user access..."

→ **本基盤への意味**: 本基盤が Service Provider 扱いなら、顧客側ユーザーに対しても上記制約適用。

#### Req 8.4.1 CDE への管理者アクセスの MFA

> "8.4.1 **MFA is implemented for all non-console access into the CDE for personnel with administrative access.**"

#### Req 8.4.2 CDE への全 non-console アクセスの MFA

> "8.4.2 **MFA is implemented for all non-console access into the CDE.**"

#### Req 8.4.3 リモートアクセス全般の MFA

> "8.4.3 **MFA is implemented for all remote access originating from outside the entity's network that could access or impact the CDE.**"

#### Req 8.5.1 MFA システム構成

> "8.5.1 MFA systems are implemented as follows:
> • **The MFA system is not susceptible to replay attacks.**
> • MFA systems cannot be bypassed by any users, including administrative users unless specifically documented, and authorized by management on an exception basis, for a limited time period.
> • At least two different types of authentication factors are used."

→ **本基盤への意味**: TOTP は replay 耐性が時刻ベース ±30s の窓内で脆弱。**WebAuthn/Passkeys (FIDO2)** は public-key 署名で完全 replay 耐性 → Phishing-resistant MFA として推奨。

#### Req 8.6.1 System/Application accounts の interactive login 制限

> "8.6.1 If accounts used by systems or applications can be used for interactive login, they are managed as follows:
> • Interactive use is prevented unless needed for an exceptional circumstance.
> • Interactive use is limited to the time needed for the exceptional circumstance."

#### Req 8.6.2 ハードコード credential 禁止

> "8.6.2 Passwords/passphrases for any application and system accounts that can be used for interactive login are **not hard coded in scripts, configuration/property files, or bespoke and custom source code.**"

→ **本基盤への意味**: M2M client_secret (`auth-poc-backend` の `secret`) を realm.json に書かないこと、Secrets Manager / KMS で動的注入。現状 realm.json に `"secret": "change-me-in-production"` 直書きしているが、本番は外部化必須。

#### Req 8.6.3 System/Application account credentials の保護

> "8.6.3 Passwords/passphrases for any application and system accounts are protected against misuse as follows:
> • **Passwords/passphrases are changed periodically (at the frequency defined in the entity's targeted risk analysis, which is performed according to all elements specified in Requirement 12.3.1)** and upon suspicion or confirmation of compromise.
> • Passwords/passphrases are constructed with sufficient complexity appropriate for how frequently the entity changes the passwords/passphrases."

→ **本基盤への意味**: M2M client_secret の rotation を顧客リスク評価で決定。3-6 ヶ月 rotation が業界標準。

### 3.3 Requirement 10: ログと監視

#### Req 10 章タイトル

> "Requirement 10: **Log and Monitor All Access to System Components and Cardholder Data**"

#### Req 10.5.1 監査ログ保存期間 (★Critical Critical)

> "10.5.1 **Retain audit log history for at least 12 months, with at least the most recent three months immediately available for analysis.**"

Testing Procedure:
> "10.5.1.a Examine documentation to verify that the following is defined:
> • Audit log retention policies.
> • Procedures for retaining audit log history for at least 12 months, with at least the most recent three months immediately available online."

Purpose:
> "Retaining historical audit logs for at least 12 months is necessary because compromises often go unnoticed for significant lengths of time. Having centrally stored log history allows investigators to better determine the length of time a potential breach was occurring..."

→ **本基盤への意味**: CloudWatch 7d retention は完全不適合。**S3 + Athena + Intelligent-Tiering 構成必須**（最近 3 ヶ月は Standard、それ以降 Glacier 等で 12 ヶ月）。

### 3.4 Requirement 11: テスト

#### Req 11 章タイトル

> "Requirement 11: **Test Security of Systems and Networks Regularly**"

#### Req 11.4.1 ペネトレーション テスト方法論

> "11.4.1 A penetration testing methodology is defined, documented, and implemented by the entity, and includes:
> • Industry-accepted penetration testing approaches.
> • Coverage for the entire CDE perimeter and critical systems.
> • Testing from both inside and outside the network."

#### Req 11.4.2 内部ペネトレーション テスト

> "11.4.2 Internal penetration testing is performed:
> • Per the entity's defined methodology,
> • **At least once every 12 months**
> • After any significant infrastructure or application upgrade or change
> • By a qualified internal resource or qualified external third-party."

#### Req 11.4.3 外部ペネトレーション テスト

> "11.4.3 External penetration testing is performed:
> • Per the entity's defined methodology
> • **At least once every 12 months**
> • After any significant infrastructure or application upgrade or change."

→ **本基盤への意味**: 本番稼働前 + 年 1 回 + 重要変更後にペネトレ必須。In-Scope なら外部 QSA / ASV 経由、Out-of-Scope なら自社/委託で実施。

---

## 4. APPI 一次資料 verbatim 引用

> **出典**: 個人情報の保護に関する法律についてのガイドライン（通則編）、平成 28 年 11 月（**令和 8 年 4 月一部改正**）、個人情報保護委員会
> **PDF**: https://www.ppc.go.jp/files/pdf/260401_guidelines01.pdf（公開、`/tmp/appi-tsusoku.txt` に pdftotext 抽出済）

### 4.1 法第 22 条: 個人データの正確性確保・遅滞ない消去

> "個人情報取扱事業者は、利用目的の達成に必要な範囲内において、個人データを正確かつ最新の内容に保つとともに、利用する必要がなくなったときは、当該個人データを遅滞なく消去するよう**努めなければならない**。"

→ **本基盤への意味**: 退職者のゴーストユーザー削除（**[jit-scim-coexistence-keycloak.md §10.4.A Event Listener SPI 版](jit-scim-coexistence-keycloak.md)** の 90 日定期バッチ deprovisioning で対応、**⚠ 2026-07-09 訂正**：旧 §10.4 は 10M MAU で破綻）。**努力義務**だが、運用上は安全管理措置（法 23）と一体で実装。

### 4.2 法第 23 条: 安全管理措置（★Critical）

> "個人情報取扱事業者は、その取り扱う個人データの漏えい、滅失又は毀損の防止その他の個人データの安全管理のために必要かつ適切な措置を講じなければならない。"

PPC ガイドライン 通則編 §3-4-2 解説:
> "個人情報取扱事業者は、その取り扱う個人データの漏えい、滅失又は毀損（以下「漏えい等」という。）の防止その他の個人データの安全管理のため、必要かつ適切な措置を講じなければならないが、当該措置は、**個人データが漏えい等をした場合に本人が被る権利利益の侵害の大きさを考慮し、事業の規模及び性質、個人データの取扱状況**（取り扱う個人データの性質及び量を含む。）**、個人データを記録した媒体の性質等に起因するリスクに応じて、必要かつ適切な内容としなければならない**。"

PPC ガイドライン §10 別添: **講ずべき安全管理措置の内容**:
- **10-3** 組織的安全管理措置
- **10-4** 人的安全管理措置
- **10-5** 物理的安全管理措置
- **10-6** 技術的安全管理措置
- **10-7** 外的環境の把握

→ **本基盤への意味**: 4 区分（組織的・人的・物理的・技術的）を網羅する必要。AWS は物理的安全管理を担保。本基盤は技術的（暗号化・アクセス制御）と組織的（運用 SOP）を実装。人的（従業者教育）は法 24 と一体。

### 4.3 法第 24 条: 従業者の監督

> "個人情報取扱事業者は、その従業者に個人データを取り扱わせるに当たっては、当該個人データの安全管理が図られるよう、当該従業者に対する必要かつ適切な監督を行わなければならない。"

> 「**従業者**」とは...雇用関係にある従業員（正社員、契約社員、嘱託社員、パート社員、アルバイト社員等）のみならず、取締役、執行役、理事、監査役、監事、**派遣社員等も含まれる**。

→ **本基盤への意味**: 基盤運用チーム（Platform Admin）の教育・誓約・監督 SOP が必要。SOC 2 / ISO 27001 の人的管理策と統合できる。

### 4.4 法第 25 条: 委託先の監督

> "個人情報取扱事業者は、個人データの取扱いの全部又は一部を委託する場合は、その取扱いを委託された個人データの安全管理が図られるよう、委託を受けた者に対する必要かつ適切な監督を行わなければならない。"

PPC ガイドライン §3-4-4:
> "個人情報取扱事業者は、個人データの取扱いの全部又は一部を委託する場合は、委託を受けた者（以下「委託先」という。）において当該個人データについて安全管理措置が適切に講じられるよう、委託先に対し必要かつ適切な監督をしなければならない。具体的には、個人情報取扱事業者は、**法第 23 条に基づき自らが講ずべき安全管理措置と同等の措置が講じられるよう、監督を行うものとする**。"

→ **本基盤への意味**: 本基盤は「顧客から委託を受ける処理者」の立場 → 委託元（顧客）から監督される対象。同時に本基盤が AWS / Auth0 / Entra ID を利用する場合、それらは本基盤側の委託先。**SOC 2 Type II / ISO 27001 / PCI DSS Level 1 等の第三者監査証跡** を委託先選定の基準とするのが業界標準。

### 4.5 法第 26 条: 漏えい等の報告（★Critical）

> "個人情報取扱事業者は、その取り扱う個人データの漏えい、滅失、毀損その他の個人データの安全の確保に係る事態であって個人の権利利益を害するおそれが大きいものとして個人情報保護委員会規則で定めるものが生じたときは、個人情報保護委員会規則で定めるところにより、当該事態が生じた旨を個人情報保護委員会に報告しなければならない。"

#### 規則第 7 条: 報告対象事態（★4 カテゴリ）

> "法第 26 条第 1 項本文の個人の権利利益を害するおそれが大きいものとして個人情報保護委員会規則で定めるものは、次の各号のいずれかに該当するものとする。
> (1) 要配慮個人情報が含まれる個人データ...の漏えい、滅失若しくは毀損（以下この条及び次条第 1 項において「漏えい等」という。）が発生し、又は発生したおそれがある事態
> (2) 不正に利用されることにより**財産的被害**が生じるおそれがある個人データの漏えい等が発生し、又は発生したおそれがある事態
> (3) 不正の目的をもって行われたおそれがある当該個人情報取扱事業者に対する行為による個人データの漏えい等が発生し、又は発生したおそれがある事態
> (4) 個人データに係る本人の数が**千人を超える**漏えい等が発生し、又は発生したおそれがある事態"

通則編 §3-5-3-1 の事例（本基盤に関連する代表例）:

**規則第 7 条 (2) 事例**:
> "事例 2）**送金や決済機能のあるウェブサービスのログイン ID とパスワードの組み合わせを含む個人データが漏えいした場合**"

→ federated identity の email + 認証情報の組合せが流出した場合、件数閾値なしで報告対象。

**規則第 7 条 (3) 事例**:
> "事例 1）**不正アクセスにより個人データが漏えいした場合**
> 事例 2）ランサムウェア等により個人データが暗号化され、復元できなくなった場合
> 事例 4）従業者が顧客の個人データを不正に持ち出して第三者に提供した場合"

→ **不正アクセス起因なら 1 件でも報告対象**。本基盤での brute-force 突破、SQLi、内部犯行はすべてこのカテゴリ。

#### 規則第 8 条第 1 項: 速報（3〜5 日以内）

> "個人情報取扱事業者は、法第 26 条第 1 項本文の規定による報告をする場合には、前条各号に定める事態を知った後、速やかに、当該事態に関する次に掲げる事項（報告をしようとする時点において把握しているものに限る。次条において同じ。）を報告しなければならない。
> (1) 概要
> (2) 漏えい等が発生し、又は発生したおそれがある個人データ...の項目
> (3) 漏えい等が発生し、又は発生したおそれがある個人データに係る本人の数
> (4) 原因
> (5) 二次被害又はそのおそれの有無及びその内容
> (6) 本人への対応の実施状況
> (7) 公表の実施状況
> (8) 再発防止のための措置
> (9) その他参考となる事項"

> 「『速やか』の日数の目安については、個別の事案によるものの、個人情報取扱事業者が当該事態を知った時点から**概ね 3〜5 日以内**である。」

#### 規則第 8 条第 2 項: 確報（30 日以内 / 不正アクセス 60 日以内）

> "前項の場合において、個人情報取扱事業者は、**当該事態を知った日から 30 日以内**（当該事態が前条第 3 号に定めるものである場合にあっては、**60 日以内**）に、当該事態に関する前項各号に定める事項を報告しなければならない。"

通則編 §3-5-3-4 補足:
> "30 日以内又は 60 日以内は報告期限であり、可能である場合には、より早期に報告することが望ましい。"

→ **本基盤への意味**: 漏えい検知 → 速報（3-5 日）→ 確報（30 日 / 不正アクセス起因 60 日）の Runbook 必須。**SOC2 / CSIRT 連携体制** + **個人情報保護委員会の報告フォーム** 提出フロー。

### 4.6 法第 28 条: 外国にある第三者への提供

> "個人情報取扱事業者は、外国（本邦の域外にある国又は地域をいう。以下この条及び第 31 条第 1 項第 2 号において同じ。）（個人の権利利益を保護する上で我が国と同等の水準にあると認められる個人情報の保護に関する制度を有している外国として個人情報保護委員会規則で定めるものを除く。以下この条及び同号において同じ。）にある第三者（個人データの取扱いについてこの節の規定により個人情報取扱事業者が講ずべきこととされている措置に相当する措置（第 3 項において「相当措置」という。）を継続的に講ずるために必要なものとして個人情報保護委員会規則で定める基準に適合する体制を整備している者を除く。以下この項及び次項並びに同号において同じ。）に個人データを提供する場合には、前条第 1 項各号に掲げる場合を除くほか、あらかじめ外国にある第三者への提供を認める旨の本人の同意を得なければならない。"

→ **本基盤への意味**: Auth0 (米 Okta)、Entra ID (米 Microsoft) は外国の第三者。**「同等水準の保護制度を有する国」** には EU 加盟国・英国（GDPR 適合決定相当）が指定。**米国は指定外** → 同意取得 or 相当措置（標準契約条項等）が必須。

### 4.7 法第 33-35 条: 本人による開示等請求

#### 法第 33 条: 保有個人データの開示

> "本人は、個人情報取扱事業者に対し、当該本人が識別される保有個人データの電磁的記録の提供による方法、書面の交付による方法その他の個人情報保護委員会規則で定める方法のうち当該本人が請求した方法（当該方法による開示に多額の費用を要する場合その他の当該方法による開示が困難である場合にあっては、書面の交付による方法）による開示を請求することができる。"

#### 法第 34 条: 保有個人データの訂正等

> "本人は、個人情報取扱事業者に対し、当該本人が識別される保有個人データの内容が事実でないときは、当該保有個人データの内容の訂正、追加又は削除（以下この節において「訂正等」という。）を請求することができる。"

#### 法第 35 条: 保有個人データの利用停止等

> "本人は、個人情報取扱事業者に対し、当該本人が識別される保有個人データを当該個人情報取扱事業者が...違反して取り扱っているという理由...により、当該保有個人データの利用の停止又は消去（以下この条において「利用停止等」という。）を請求することができる。"

→ **本基盤への意味**: 本人からの開示・訂正・利用停止請求に「**遅滞なく**」応答する SOP 必須。Keycloak Admin API + アカウント設定画面 + 運用フローで対応。

---

## 5. 現状 × PCI DSS 要件マッピング

| Req | 内容 | 現状 (Stage A 後) | ギャップ | 優先度 |
|---|---|---|---|---|
| **8.2.5** | 退職者の即時アクセス無効化 | 🟡 SCIM 採用顧客は対応可、JIT のみは顧客 IdP 依存 | 顧客 IdP との Token Revocation 連動 | High |
| **8.2.6** | 90 日未使用無効化 | 🟡 **[jit-scim §10.4.A Event Listener SPI 版](jit-scim-coexistence-keycloak.md)** 実装ガイド済、本番実装未（**⚠ 旧 §10.4 は 10M MAU で破綻、2026-07-09 訂正**）| Event Listener SPI 開発 + user_attribute.last_login 書込 + JIT/SCIM 判別 + CronJob 化 | High |
| **8.3.1** | 認証要素 | ✅ TOTP MFA (Phase 7-9 で検証) | — | — |
| **8.3.6** | パスワード長 12 文字 | 🟡 Keycloak Realm Policy で設定可、現実値未確定 | realm.json でポリシー固定 | Medium |
| **8.3.9** | 90 日 PW 変更 or 動的分析 | 🟡 MFA 強制で適用外化可 | MFA 全アクセス必須化を決定 | High |
| **8.4.1** | CDE 管理者の MFA | ✅ Platform Admin に MFA 強制設定可 | 強制設定の Realm 反映 | Medium |
| **8.4.2** | CDE 全アクセス MFA | ⚠ In-Scope なら全 end user に MFA 必須 | Phishing-resistant MFA 検討 | **Critical** |
| **8.4.3** | リモートアクセス MFA | ✅ 全 OIDC フローで MFA 適用可 | — | — |
| **8.5.1** | MFA replay 耐性 | ❌ **TOTP は窓内 replay 可、WebAuthn 必要** | WebAuthn/Passkeys 実装 | **Critical** |
| **8.6.1** | System account interactive 制限 | ✅ auth-poc-backend は serviceAccountsEnabled のみ | — | — |
| **8.6.2** | ハードコード credential 禁止 | ❌ realm.json に `"secret":"change-me"` 直書き | AWS Secrets Manager + ECS env 注入 | **Critical** |
| **8.6.3** | System account credential rotation | ❌ rotation 未実装 | client_secret rotation cron | High |
| **10.5.1** | ログ 12 ヶ月保存 (3ヶ月即時) | ❌ **CloudWatch 7d retention** | S3 + Athena + Intelligent-Tiering | **Critical** |
| **11.4.2** | 内部ペネトレ 年 1 回 | ❌ 未実施 | 本番稼働前 + 年次計画 | High |
| **11.4.3** | 外部ペネトレ 年 1 回 | ❌ 未実施 | 外部認定企業選定 | High |

---

## 6. 現状 × APPI 要件マッピング

| 法条 | 内容 | 現状 (Stage A 後) | ギャップ | 優先度 |
|---|---|---|---|---|
| **法 22** | 個人データ正確性確保・遅滞ない消去（努力義務）| 🟡 90 日 deprovisioning 実装ガイド済 | 本番実装 | Medium |
| **法 23** | 安全管理措置（4 区分）| 🟡 技術的 ✅、組織的・人的 部分的、物理的 = AWS 委託 | 組織的 SOP + 人的教育プログラム | **Critical** |
| **法 24** | 従業者の監督 | 🟡 部分的 | 教育・誓約・監督 SOP | High |
| **法 25** | 委託先の監督 | ❌ AWS / Auth0 / Entra ID の DPA 未整理 | 第三者監査証跡確認 + 契約レビュー | **Critical** |
| **法 26 + 規則 7・8** | 漏えい等の報告 | ❌ Runbook 未構築 | 検知 → 速報 (3-5d) → 確報 (30d/60d) フロー | **Critical** |
| **法 27** | 第三者提供の制限 | ✅ 「本人からの直接取得」論理で federation は非該当 | — | — |
| **法 28** | 外国にある第三者への提供 | ❌ Auth0/Entra ID 利用時の同意取得 UI 未実装 | SPA 同意画面 + 相当措置確認 | High |
| **法 33** | 開示請求 | ✅ Keycloak Admin API + アカウント設定画面 で対応可 | 運用 SOP 文書化 | Low |
| **法 34** | 訂正等 | ✅ 同上 | 同上 | Low |
| **法 35** | 利用停止等 | ✅ realm.json で `enabled=false` 可 | 同上 | Low |

---

## 7. 必須対応 Top 12（優先度・工数・対応場所）

| # | 対応項目 | 規制根拠 | 優先度 | 工数 | 対応場所 | 依存 |
|---|---|---|:-:|---|---|---|
| 1 | **監査ログ S3 + Athena 長期保存 (12ヶ月)** | PCI 10.5.1 + APPI 法 23 | **Critical** | 2-3w | Terraform: CW Subscription → Kinesis Firehose → S3、Athena テーブル定義 | Stage B 計画 |
| 2 | **漏えい等報告 SOP / Runbook 策定** | APPI 法 26 + 規則 7・8 | **Critical** | 2-3w | 法務 + セキュリティ協議、PPC 報告フォーム連携、CSIRT 体制 | 法務 |
| 3 | **委託先監督契約整備 (AWS BAA + Auth0/Entra ID DPA)** | APPI 法 25 + 28 | **Critical** | 2-3w | 法務、AWS Enterprise Support / Auth0 Enterprise plan / Entra Enterprise | 契約 |
| 4 | **Phishing-resistant MFA (WebAuthn/Passkeys)** | PCI 8.4 + 8.5.1 + NIST SP 800-63B Rev 4 | **Critical** | 2-3w | Keycloak WebAuthn mapper + realm.json | Phase 10 検証 |
| 5 | **ハードコード credential 廃止 (Secrets Manager 統合)** | PCI 8.6.2 | **Critical** | 1w | ECS task def env → Secrets Manager、realm.json の secret を `${SECRETS:KEY}` 形式に | KMS 統合 |
| 6 | **KMS Customer-Managed Key + Rotation** | PCI 3.5 + 3.6 + APPI 法 23 | High | 2-3d | RDS encryption key + Keycloak DB + S3 audit log の CMK + ローテーションスケジュール | IAM 設計 |
| 7 | **外国提供同意取得 UI (APPI 法 28)** | APPI 法 28 | High | 2w | SPA 同意画面 + Keycloak Conditional Flow（IdP 選択時に同意確認）| 法務文言確認 |
| 8 | **ペネトレーション テスト計画 + 実施** | PCI 11.4.2 + 11.4.3 | High | 1m + 予算 | 認定企業 RFP → 実施 → 是正 | 本番移行前 |
| 9 | **退職時即時無効化フロー (SCIM + Token Revocation)** | PCI 8.2.5 | High | 1-2w | SCIM 受信実装（[hook-architecture-keycloak.md パターン D](hook-architecture-keycloak.md)）+ Universal Logout | Phase Two plugin |
| 10 | **90 日定期バッチ deprovisioning 本番実装** | PCI 8.2.6 + APPI 法 22 | High | **1-2w**（Event Listener SPI 開発込）| **[jit-scim §10.4.A](jit-scim-coexistence-keycloak.md)** Event Listener SPI 版の本番デプロイ + [ADR-060 §C.2.2](../adr/060-auth-protocol-attack-path-residual-tbd.md) SPI 統合 | EKS Scheduled Task + Keycloak SPI JAR |
| 11 | **公開 ACM 証明書 + カスタムドメイン** | PCI 4.2（推奨）| Medium | 3d | Route 53 ドメイン取得 + ACM 公開証明書 + ALB | ドメイン取得 |
| 12 | **WAF + CloudFront 統合 (ADR-013)** | PCI 6.4 (OWASP Top 10 対策) | Medium | 1-2w | CloudFront distribution + AWS WAFv2 ルールセット | Phase 10 |

---

## 8. 要件定義で確定すべき 10 ゲーティング論点

| # | 論点 | 質問 | 影響 |
|:-:|---|---|---|
| Q1 | **PCI DSS スコープ** | 顧客システムから本基盤経由で PAN が流れるか? | In-Scope/Out-of-Scope 判定 = 工数 2-3 ヶ月 vs 1-2 週間 |
| Q2 | **顧客 IdP の所在国** | Auth0/Entra ID 等の米国企業 IdP を使うか? 国内 IdP のみか? | APPI 法 28 「外国提供」フローの要否 |
| Q3 | **想定漏えいユーザー規模** | 顧客 1 社あたり数 100/数 1000/数万ユーザー? | 規則第 7 条 (4) 「千人超」閾値の頻度 |
| Q4 | **MFA 採用範囲** | 全 end user MFA 強制 / オプション? | PCI 8.3.9 (PW only の 90 日変更) 適用回避 |
| Q5 | **MFA 種別** | TOTP のみ / WebAuthn 必須 / 両方選択可? | Phishing-resistant 要件 (PCI 8.5.1) |
| Q6 | **委託先選定** | AWS Enterprise Support 必須? Auth0 Enterprise plan? | 監査証跡入手可否 (法 25) |
| Q7 | **退職時 SLA** | 即時 (1 分以内) / 24 時間以内? | SCIM 必須化 vs 定期バッチ |
| Q8 | **監査ログ保存方式** | S3 Intelligent-Tiering / Splunk / Security Lake? | コストと検索性能のバランス |
| Q9 | **ペネトレ実施主体** | 内部 / 外部 (PCI ASV 認定) / どちらも? | 予算 $20-50k / 年 |
| Q10 | **インシデント対応体制** | 24/7 SOC / 営業時間のみ + オンコール? | 速報 3-5 日達成可否 |

---

## 9. Stage B / C への追加スコープ

### Stage B（コンプラ検証）

| Task | 内容 | 工数 | 規制 |
|---|---|---|---|
| B-CM1 | KMS Customer-Managed Key 統合検証 | 2-3d | PCI 3.5/3.6 + APPI 法 23 |
| B-CM2 | CloudWatch Logs → S3 + Athena 12ヶ月保存 PoC | 1w | PCI 10.5.1 + APPI 法 23 |
| B-CM3 | Secrets Manager + ECS env 経由 credential 注入 | 1w | PCI 8.6.2 |
| B-CM4 | WebAuthn / Passkeys realm.json 設定 + ブラウザテスト | 1-2w | PCI 8.5.1 |
| B-CM5 | 漏えい等報告 SOP / Runbook ドラフト作成 | 2-3w | APPI 法 26 |
| B-CM6 | AWS / Auth0 / Entra ID 委託契約レビュー (法務協業) | 2-3w | APPI 法 25 + 28 |

### Stage C（本番移行前）

| Task | 内容 | 工数 | 規制 |
|---|---|---|---|
| C-CM1 | ペネトレーション テスト実施・是正 | 1-2m + 予算 | PCI 11.4.2/3 |
| C-CM2 | 12 ヶ月保存 E2E 検証 | 2d | PCI 10.5.1 |
| C-CM3 | 削除応答 SLA 検証 (法 35 利用停止フロー) | 2d | APPI 法 33-35 |
| C-CM4 | 外部監査 (SOC 2 Type II 等) | 6-8w | 顧客要件次第 |
| C-CM5 | 顧客向けコンプラ説明書 | 2-3w | 提案資料 |
| C-CM6 | DR 検証 (Multi-Region failover) | 1-2w | PCI 12.10 + APPI 法 23 |

---

## 10. 参考文献

### 一次資料

| 資料 | 出典 | 入手方法 |
|---|---|---|
| **PCI DSS v4.0.1** (June 2024) | PCI Security Standards Council | [PCI SSC Document Library](https://www.pcisecuritystandards.org/document_library/) 無料登録後 DL（本リポジトリでは `doc/old/PCI-DSS-v4_0_1.pdf` に保存、gitignore 済）|
| **個人情報の保護に関する法律** | e-Gov 法令検索 | [415AC0000000057](https://laws.e-gov.go.jp/document?lawid=415AC0000000057) 無料 |
| **PPC ガイドライン 通則編** (令和 8 年 4 月一部改正) | 個人情報保護委員会 | [PDF](https://www.ppc.go.jp/files/pdf/260401_guidelines01.pdf) 無料 |
| **PPC 外国にある第三者への提供編** | 同上 | [PDF](https://www.ppc.go.jp/files/pdf/251212_guidelines02.pdf) 無料 |
| **PPC 漏えい等の対応** | 同上 | [Web ページ](https://www.ppc.go.jp/personalinfo/legal/leakAction/) 無料 |

### 業界標準・推奨資料

- [NIST SP 800-63B Rev 4](https://pages.nist.gov/800-63-4/sp800-63b.html) — Digital Identity Guidelines, Authentication and Lifecycle Management
- [OWASP Application Security Verification Standard (ASVS) v5.0](https://github.com/OWASP/ASVS) — V2 Authentication, V8 Authorization
- [AWS PCI DSS Compliance](https://aws.amazon.com/compliance/pci-dss-level-1-faqs/) — AWS の PCI DSS 認定情報
- [Keycloak Admin Guide v26.2](https://www.keycloak.org/docs/latest/server_admin/) — 認証ポリシー / Event Listener / Token Revocation

### プロジェクト内 関連ドキュメント

- [§FR-7.4.8 PCI DSS / APPI 適合性整理](../requirements/proposal/fr/07-user.md) — JIT/SCIM 選定への影響整理
- [§NFR-4 セキュリティ](../requirements/proposal/nfr/04-security.md) — セキュリティベースライン
- [§NFR-7 コンプライアンス](../requirements/proposal/nfr/07-compliance.md) — 規制対応方針
- [jit-scim-coexistence-keycloak.md §10.4.A](jit-scim-coexistence-keycloak.md) — **90 日定期バッチ deprovisioning 実装ガイド（Event Listener SPI + user_attribute.last_login 版、2026-07-09 更新）**。旧 §10.4 は 10M MAU で破綻するため PoC / 小規模顧客リファレンスとして保持
- [jit-scim-coexistence-keycloak.md §10.4.B](jit-scim-coexistence-keycloak.md) — **JIT vs SCIM ユーザー判別ロジック**（scim_active=true 削除禁止フラグ + provisioned_by 属性 + 3 段階戦略）
- [identity-broker-multi-idp.md §10](identity-broker-multi-idp.md) — テナント分離・セキュリティ考慮
- [keycloak-network-architecture.md](keycloak-network-architecture.md) — 本基盤のネットワーク構成
- [phase10-stage-a-verification.md](phase10-stage-a-verification.md) — Stage A 完了状態

---

## 改訂履歴

- 2026-06-08: 初版作成。PCI DSS v4.0.1 PDF (`doc/old/PCI-DSS-v4_0_1.pdf`) と PPC ガイドライン 通則編 PDF を pdftotext で実取得・原文照合し、Req 8 (認証)・10.5.1 (ログ保存)・11.4 (ペネトレ) と APPI 法 22-28 + 33-35 + 規則 7・8 条の verbatim quote を本ドキュメントに統合。現状 (Stage A 後) とのギャップマッピング + 必須対応 Top 12 + 要件定義 10 ゲーティング論点を整理
