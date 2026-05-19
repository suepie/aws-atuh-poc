# B-5: MFA 要素・適用ポリシー

> 元データ: [../hearing-checklist.md B-5](../hearing-checklist.md#b-5-mfa-要素適用ポリシー-fr-mfa-3--fr-fed-22--proposal-fr-223-fr-3)  
> 対象: 開発チーム / セキュリティチーム  
> 関連: [proposal §FR-2.2.3](../proposal/fr/02-federation.md), [§FR-3](../proposal/fr/03-mfa.md)

---

### 【MFA 必須範囲】 (B-501, 🟡)

MFA の適用範囲についてご希望をご教示ください。
- 全ユーザー必須
- 管理者のみ必須
- 条件付き（特定操作のみ / 特定ロールのみ / リスクベース）

**目的**: MFA 適用ポリシーの確定、Cognito の MFA 強制設定 / Keycloak の Authentication Flow 設計、ユーザー体験への影響評価に必要な情報です。

---

### 【許可する MFA 方式】 (B-502, 🟡)

ユーザーに許可する MFA 方式をご教示ください:
- TOTP（Google Authenticator / Authy 等のアプリ）
- WebAuthn / Passkey（生体認証 / プラットフォーム認証器）
- SMS OTP（近年は非推奨傾向）
- Email OTP（近年は非推奨傾向）
- ハードウェアキー（YubiKey 等）
- バックアップコード

複数選択可でお答えいただけますと幸いです。
**目的**: NIST SP 800-63B Rev 4 への適合性、業界 87% が Passkey デプロイ / パイロット中、Cognito Essentials+ の WebAuthn サポート（2024-11〜）の活用判断に必要な情報です。SMS OTP は世界的に禁止傾向のため、新規採用は非推奨を推奨しています。

---

### 【WebAuthn / FIDO2（Passkeys）の採用】 (B-503, 🟡)

Passkey（FIDO2 / WebAuthn）対応の必要性をご教示ください。
有無でお答えいただけますと幸いです。
業界動向として、2026 年時点で 87% の Enterprise が deploy / pilot 中（業界調査結果）です。
**目的**: Cognito 採用時は Essentials+ ティア必須（2024-11 〜サポート）、Keycloak は標準対応。AAL3 達成、Phishing-resistant MFA の実現に必須となります。

---

### 【Back-Channel Logout】 (B-504, 🟡)

全クライアント連動ログアウト（1 つのアプリでログアウトしたら、同 IdP の全 RP にも確実に伝播）の要件はございますか。
有無でお答えいただけますと幸いです。
**目的**: OIDC Back-Channel Logout（RFC 8417）採用要否の判断。**Yes の場合、Cognito はネイティブ非対応のため Keycloak 必須化**となります。Front-Channel Logout（ブラウザ依存）で代替する場合は信頼性が低下します。

---

### 【端末記憶（Trusted Device）】 (B-505, 🟢)

ユーザーが「この端末を信頼する」を選択することで、一定期間 MFA をスキップする機能は必要でしょうか。
有無でお答えいただけますと幸いです（詳細期間は C-215 で確認します）。
**目的**: Trusted Device 機能の採用判断、Cognito / Keycloak での実装方式選定、UX とセキュリティのバランス調整に必要な情報です。

---

### 【外部 IdP MFA 信頼度】 (B-506, 🟡)

外部 IdP（顧客 IdP）で既に MFA 済みのユーザーに対して、本基盤側でも MFA を再要求するかご教示ください。
- 全面信頼（IdP の `amr=mfa` を信頼、本基盤側 MFA はスキップ）
- 部分信頼（特定の IdP / 特定のロールのみ信頼）
- 全件再要求（信頼せず本基盤側で必ず MFA）

**目的**: MFA 重複回避設計（[§FR-2.2.3](../proposal/fr/02-federation.md)）、UX 悪化（ログイン 2 回要求）の回避、Conditional MFA フローの設計に必要な情報です。業界標準は「接続承認された IdP のみ信頼」です。

---

### 【信頼する `amr` / AuthnContext 値】 (B-507, 🟡)

B-506 で「全面信頼」または「部分信頼」を採用する場合、どの `amr` 値 / AuthnContextClassRef を MFA 済として信頼するかご教示ください。
代表例:
- OIDC: `amr=mfa`, `amr=hwk`（ハードウェアキー）, `amr=pwd+mfa`
- SAML: `urn:oasis:names:tc:SAML:2.0:ac:classes:MultiFactorContract`, `urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport`

**目的**: ACR-to-LoA Mapping の設計（[§FR-3.3.A](../proposal/fr/03-mfa.md)）、AAL レベル判定ロジックの確定、各 IdP の方言を統一 AAL に正規化するための情報です。

---

### 【高権限ロールへの追加 MFA 強制】 (B-508, 🟡)

管理者など高権限ユーザーには、外部 IdP MFA 信頼に関わらず本基盤側でも MFA を強制しますか。
- する（管理者は二重 MFA）
- しない
- ロール別に切替（admin は強制、staff は信頼）

**目的**: 高権限アカウント保護の強化、ステップアップ MFA（[§FR-3.3](../proposal/fr/03-mfa.md)）の要件確定、AAL レベルのロール別設定に必要な情報です。

---

### 【SSO で繋ぐシステム範囲】 (B-509, 🟡)

共通認証基盤の SSO で繋ぐシステムの範囲をご教示ください:
- 社内システムのみ（情シス系）
- 顧客向けシステムも含む（顧客 IdP 連携）
- 横断 SSO（社内 + 顧客 + 一部外部 SaaS まで）

**目的**: SSO スコープの確定、テナント境界設計、Cognito User Pool / Keycloak Realm の構成判断に必要な情報です。
