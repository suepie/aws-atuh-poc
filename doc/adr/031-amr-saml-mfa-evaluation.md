# ADR-031: amr / SAML AuthnContext MFA 評価の統合方針

- **ステータス**: Proposed（要件定義フェーズで Accepted に昇格予定）
- **日付**: 2026-06-15
- **関連**:
  - [§FR-3.5 amr クレーム評価の信頼性根拠](../requirements/proposal/fr/03-mfa.md#fr-35-amr-クレーム評価の信頼性根拠)
  - [§FR-3.4 全顧客 MFA 必須化](../requirements/proposal/fr/03-mfa.md#fr-34-全顧客-mfa-必須化と基盤側保持データの最小化)
  - [common/jit-scim-coexistence-keycloak.md §10.8.5](../common/jit-scim-coexistence-keycloak.md)

---

## Context

§FR-3.4 案 3 で採用する「**amr クレーム評価**」が、なぜ盲信ではなく**業界標準的に安全か**の根拠整理が必要。あわせて **SAML 経由の MFA 評価**（amr 不在）の問題を解決する統合方針の確定が必要。

- OIDC 経由は `amr` クレーム（RFC 8176 標準値）で評価可能
- SAML 経由は `AuthnContextClassRef`（SAML 標準）+ `authnmethodsreferences`（Microsoft 拡張）が必要
- Microsoft Entra ID SAML は AuthnContextClassRef を MFA 用に変更しない特殊仕様

これら 3 種類の評価対象を**統一的に扱う実装方針**が必要。

---

## Decision

### amr 評価の業界標準採用

「**amr 不送出 = MFA していない**」とみなし、安全側で基盤側 MFA を補完する **fail-safe 設計**を採用（Microsoft Entra B2B / Auth0 / Okta 等の業界主流と同じ）。

### OIDC + SAML 統合評価：統一 User Attribute (`mfa_indicator`) への正規化

Identity Provider Mapper で 3 種類のクレーム/属性を **統一 User Attribute (`mfa_indicator`)** に正規化し、Conditional Authenticator は単一属性のみ評価する設計を採用。

```
OIDC IdP (amr)                         ─┐
SAML IdP (AuthnContextClassRef)         ├─→ Identity Provider Mapper
SAML IdP (authnmethodsreferences)      ─┘    で統一コピー
                                              ↓
                                       User Attribute: mfa_indicator
                                              ↓
                                       Conditional Authenticator
                                       (mfa_indicator に MFA 系値含むかチェック)
```

---

## A. amr クレームとは

**OIDC Core 1.0 §2 で定義**される標準クレーム:
- `amr` (Authentication Methods References) = ユーザーが認証時に使用した方法の配列
- 例: `["pwd", "otp"]` = パスワード + ワンタイムパスワード認証
- **RFC 8176** で標準値が定義

### amr クレームの形式

**JSON 文字列の配列**であり、認証時に使用した**全ての**認証方法を列挙:

```json
{
  "sub": "alice@acme.com",
  "iss": "https://login.microsoftonline.com/...",
  "amr": ["pwd", "mfa", "rsa"],     ← 配列、複数の認証方法
  "acr": "1"
}
```

### RFC 8176 標準値の分類

| 値 | 意味 | MFA 該当 | 本基盤の信頼 |
|---|---|:-:|:-:|
| `mfa` | 一般的な多要素認証（最も明示的）| ✅ | ✅ |
| `otp` | One-Time Password（TOTP / HOTP）| ✅ | ✅ |
| `hwk` | Hardware Key（FIDO2 / YubiKey）| ✅ | ✅ |
| `fpt` | 指紋認証 | ✅ | ✅ |
| `face` | 顔認証 | ✅ | ✅ |
| `iris` | 虹彩認証 | ✅ | ✅ |
| `mca` | Multi-Channel Authentication | ✅ | ✅ |
| `swk` | Software Key | ✅ | ✅ |
| `pwd` | パスワード | ❌ 単要素 | ❌ |
| `pin` | PIN | ❌ 単要素 | ❌ |
| `kba` | 知識ベース認証 | ❌ | ❌ |
| `sms` | SMS OTP | ⚠ NIST 非推奨 | ❌（本基盤不採用）|

---

## B. amr の有無による判定（4 パターン）

amr クレームは OIDC 仕様上 **OPTIONAL** であり、IdP によって送出しないこともある。

| パターン | 例 | 本基盤の判定 | 動作 |
|---|---|:-:|---|
| **A. amr 送出なし**（属性自体存在しない）| `{"sub": "...", ...}` | ⚠ 判定不可 | **安全側「未済」扱い → 基盤側 MFA 補完** |
| **B. amr が空配列** | `"amr": []` | ⚠ 判定不可 | 同上 |
| **C. amr に MFA 系値なし**（`pwd` のみ等）| `"amr": ["pwd"]` | ❌ MFA 未済 | 基盤側 MFA 補完 |
| **D. amr に MFA 系値あり** | `"amr": ["pwd", "mfa"]` | ✅ MFA 済 | 基盤側 MFA スキップ |

### 「amr がなければ必ず MFA していない」と言えるか?

- 厳密には情報がないだけで断定はできない
- ただし業界実装は「amr 不送出 = 未済扱い」が業界標準（**fail-safe**）
- **本基盤の判定: 「未済として扱う」→ 基盤側 MFA 補完**

→ Microsoft Entra B2B / Auth0 / Okta 等の業界主流と同じ。

---

## C. amr 評価が信頼できる根拠

| リスク | 対策 |
|---|---|
| 偽の amr を含む JWT 送信（中間者 / 悪意ある IdP）| ❌ **顧客 IdP の SAML/OIDC 署名検証**で防がれる |
| 顧客 IdP 側で MFA 設定変更（顧客都合）| 顧客責任、契約条項で明示 |
| amr 値の解釈差（IdP ごとに違う）| **信頼する `amr` 値をホワイトリスト化**（RFC 8176 標準値のみ採用）|
| HTTPS 中間者攻撃 | TLS + JWT 署名で防がれる |
| リプレイ攻撃 | JWT の `nonce` / `iat` / `exp` 検証で防がれる |

---

## D. 顧客 IdP 別の amr 送出実態

| 顧客 IdP | amr 送出 | 送出形式 | 設定要否 | 本基盤の動作 |
|---|:-:|---|---|---|
| **Microsoft Entra ID** | ✅ デフォルト | `["pwd", "mfa", "rsa"]` RFC 8176 準拠 | 設定不要 | amr 評価可能 |
| **Okta** | ✅ デフォルト | `["pwd", "mfa", "otp", "hwk"]` | 設定不要 | amr 評価可能 |
| **Google Workspace** | ✅ デフォルト | `["pwd", "mfa", "otp", "swk"]` | 設定不要 | amr 評価可能 |
| **ADFS** | ⚠ **デフォルト送出しない** | Claim Rule 設定時のみ | **顧客側で Claim Rule 設定が必要** | 設定なし = 未済扱い → 基盤側 MFA 補完 |
| **HENNGE One** | △ 個別確認必要 | カスタム実装次第 | 顧客実装次第 | 確認次第 |
| **独自 IdP** | △ 個別確認必要 | カスタム実装次第 | 顧客実装次第 | 確認次第 |

### ADFS の amr 送出設定例

```powershell
# ADFS PowerShell: amr クレームを発行する Claim Rule
$rule = @'
@RuleTemplate = "AuthenticationMethodsReferences"
@RuleName = "Issue AMR Claim"
c:[Type == "http://schemas.microsoft.com/claims/authnmethodsreferences"]
 => issue(claim = c);
'@

Add-AdfsRelyingPartyTrust -Name "Common-Auth-Platform" `
  -IssuanceTransformRules $rule
```

→ **顧客に Claim Rule 設定を強制する必要はなく**、未設定の場合は基盤側 MFA で MFA 必須化を確保。

---

## E. SAML 経由 IdP の MFA 評価（amr では不十分）

本基盤は **OIDC + SAML 両プロトコルの顧客 IdP を受信**するが、**SAML 経由では `amr` クレームが存在しない**。

### SAML 経由での MFA 検出方法（3 つのチェック対象）

| # | 検出対象 | 詳細 | 採用 IdP |
|:-:|---|---|---|
| **A** | `AuthnContextClassRef`（SAML 標準）| SAML Assertion の `<saml:AuthnContext>` 内 | Okta / Google Workspace / Shibboleth 等 |
| **B** | `authnmethodsreferences`（Microsoft 拡張）| URI: `http://schemas.microsoft.com/claims/authnmethodsreferences`、`mfa` / `multipleauthn` 等を含む | **Microsoft Entra ID (SAML)** / ADFS（設定時）|
| **C** | `multipleauthn`（Microsoft 拡張の特殊値）| Entra ID が MFA 完了時に送出、Salesforce が 2026-02-17 から対応 | **Microsoft Entra ID 専用** |

### AuthnContextClassRef の標準値（SAML）

| 値 | 意味 | MFA 該当 |
|---|---|:-:|
| `urn:oasis:names:tc:SAML:2.0:ac:classes:Password` | パスワードのみ | ❌ |
| `urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport` | HTTPS パスワード | ❌ |
| `urn:oasis:names:tc:SAML:2.0:ac:classes:MultiFactorContract` | **MFA** | ✅ |
| `urn:oasis:names:tc:SAML:2.0:ac:classes:Smartcard` | スマートカード | ✅ |
| `urn:oasis:names:tc:SAML:2.0:ac:classes:Kerberos` | Kerberos | △ |
| `https://refeds.org/profile/mfa` | **REFEDS MFA Profile**（学術界標準）| ✅ |

### 重要: Microsoft Entra ID SAML の特殊仕様

> **⚠ Microsoft Entra ID は AuthnContextClassRef を MFA 用に変更しない仕様**

| 観点 | Microsoft Entra ID の挙動 |
|---|---|
| MFA 実施時の AuthnContextClassRef | **変わらない**（`Password` 等のまま）|
| MFA 表現方法 | **`authnmethodsreferences` 属性で送出**（Microsoft 拡張）|
| 送出される値 | `mfa`、`multipleauthn`、`otp` 等 |

→ **Entra ID の SAML 接続で AuthnContextClassRef だけ見ても MFA 判定不可**。`authnmethodsreferences` を必ず評価する必要あり。

### 顧客 IdP × プロトコル別の評価対象マトリクス

| 顧客 IdP | OIDC 経由（amr）| SAML 経由（AuthnContextClassRef + authnmethodsreferences）|
|---|:-:|:-:|
| **Microsoft Entra ID** | ✅ amr 評価 | ⚠ **AuthnContextClassRef は無効、authnmethodsreferences を評価** |
| **Okta** | ✅ amr 評価 | ✅ AuthnContextClassRef 評価（REFEDS Profile 等）|
| **Google Workspace** | ✅ amr 評価 | ✅ AuthnContextClassRef 評価 |
| **ADFS** | △ Claim Rule 設定時のみ | △ Claim Rule 設定時のみ（authnmethodsreferences 推奨）|
| **HENNGE One** | △ 個別確認 | △ 個別確認 |
| **Shibboleth**（学術系）| - | ✅ AuthnContextClassRef = REFEDS Profile |
| **独自 IdP** | △ 個別確認 | △ 個別確認 |

### 業界事例：Salesforce の OIDC / SAML 別評価

Salesforce は OIDC IdP と SAML IdP で**評価方法を分けて**実装:

| 評価対象 | 評価値の列 |
|---|---|
| OIDC IdP | **AMR 受入値列**（`["mfa", "otp"]` 等）|
| SAML IdP | **ACR 受入値列**（`urn:...:MultiFactorContract` 等）|

2026-02-17 update で **Entra ID の `multipleauthn` 値もサポート追加**（authnmethodsreferences 属性内）し、「High Assurance」セッションとして扱うようになった。

---

## F. OIDC / SAML 統合評価の実装方針

### 推奨アプローチ: 統一 User Attribute (`mfa_indicator`) への正規化

複数のクレーム / 属性を Identity Provider Mapper で**統一 User Attribute (`mfa_indicator`)** に正規化し、Conditional Authenticator は単一属性のみ評価。

### Keycloak 実装（Terraform、3 IdP プロトコル別）

| IdP | Identity Provider Mapper の `claim_name` | コピー先 User Attribute |
|---|---|---|
| OIDC IdP | `amr` | `mfa_indicator` |
| SAML IdP（標準）| `Saml.AuthnContextClassRef` | `mfa_indicator` |
| SAML IdP（Microsoft Entra）| `http://schemas.microsoft.com/claims/authnmethodsreferences` | `mfa_indicator` |

→ **Conditional Authenticator は `mfa_indicator` 単一属性を見るだけで全プロトコル統合評価可能**。

詳細な Terraform 実装例は [common/jit-scim-coexistence-keycloak.md §10.8.5.C](../common/jit-scim-coexistence-keycloak.md) を参照。

### 統一評価の信頼値（OIDC + SAML 統合ホワイトリスト）

| 値 | プロトコル | MFA 該当 | 信頼 |
|---|:-:|:-:|:-:|
| `mfa` | OIDC amr / SAML 拡張 | ✅ | ✅ |
| `otp` / `hwk` / `fpt` / `face` / `iris` / `mca` / `swk` | OIDC amr | ✅ | ✅ |
| `urn:oasis:names:tc:SAML:2.0:ac:classes:MultiFactorContract` | SAML 標準 | ✅ | ✅ |
| `urn:oasis:names:tc:SAML:2.0:ac:classes:Smartcard` | SAML 標準 | ✅ | ✅ |
| `https://refeds.org/profile/mfa` | SAML (REFEDS) | ✅ | ✅ |
| `multipleauthn` | SAML (Microsoft 拡張) | ✅ | ✅ |
| `pwd` / `Password` / `PasswordProtectedTransport` | 両方 | ❌ 単要素 | ❌ |

### 評価フロー

| ステップ | 動作 |
|---|---|
| 1. 顧客 IdP から認証 Assertion を受信 | OIDC ID Token or SAML Assertion |
| 2. Identity Provider Mapper でクレーム/属性を正規化 | amr / AuthnContextClassRef / authnmethodsreferences → `mfa_indicator` |
| 3. Conditional Authenticator が評価 | `mfa_indicator` に **ホワイトリスト値が 1 つでも含まれるか**チェック |
| 4. 判定結果 | 含む → 基盤側 MFA スキップ / 含まない or 属性なし → 基盤側 MFA 補完 |

### 新規顧客 IdP 追加時の影響範囲

| 追加要素 | 設定変更箇所 |
|---|---|
| 新規 IdP（OIDC 経由）| Identity Provider Mapper で `amr` → `mfa_indicator` のみ |
| 新規 IdP（SAML 経由、標準）| Identity Provider Mapper で `Saml.AuthnContextClassRef` → `mfa_indicator` のみ |
| 新規 IdP（SAML 経由、Microsoft 系）| Identity Provider Mapper で `authnmethodsreferences` → `mfa_indicator` のみ |
| Conditional Authenticator | **変更不要**（`mfa_indicator` を見るだけ）|

→ **新規顧客 IdP 追加時の影響範囲が IdP 設定内に閉じる**、保守性が高い。

---

## G. 業界実装事例（amr 評価の業界標準性）

| プレイヤー | amr 評価の使い方 |
|---|---|
| **Microsoft Entra B2B Cross-Tenant Access** | Home IdP の amr を Resource Tenant 側で信頼 |
| **Auth0 Rules / Actions** | amr 評価で条件付き MFA 実装 |
| **Okta** | amr ベースの Authentication Policy |
| **Curity Identity Server** | amr 評価が標準機能 |
| **Salesforce** | OIDC / SAML 別評価、2026-02 から Entra `multipleauthn` も対応 |

→ amr 評価は業界標準パターン、本基盤の採用は実績豊富な手法。

---

## Consequences

### Positive

- OIDC + SAML 統合評価で全顧客 IdP に対応可能
- 統一 User Attribute (`mfa_indicator`) で実装シンプル化
- 新規 IdP 追加の影響範囲が IdP 設定内に閉じる
- fail-safe 設計（amr 不送出 = 未済扱い）で安全側に倒れる
- Microsoft Entra SAML の特殊仕様にも対応

### Negative

- ADFS / 独自 IdP は顧客側に Claim Rule 設定依頼が発生（or 基盤 MFA で補完）
- SAML 経由の評価対象が複数あり、初期設定がやや複雑
- 業界標準でない独自 amr 値を使う IdP はホワイトリスト調整が必要

---

## 参考資料

- [OIDC Core 1.0 §2](https://openid.net/specs/openid-connect-core-1_0.html#IDToken) — amr クレーム定義
- [RFC 8176 Authentication Method Reference Values](https://datatracker.ietf.org/doc/html/rfc8176)
- [SAML 2.0 AuthnContext Classes](http://docs.oasis-open.org/security/saml/v2.0/saml-authn-context-2.0-os.pdf)
- [REFEDS MFA Profile](https://refeds.org/profile/mfa)
- [Microsoft Entra SAML authnmethodsreferences](https://learn.microsoft.com/en-us/entra/identity/authentication/concept-authentication-methods)
- [Salesforce: Receive Multi-factor Authentication Indicator from External Identity Providers](https://help.salesforce.com/s/articleView?id=sf.security_external_idp_amr.htm)
- [common/jit-scim-coexistence-keycloak.md §10.8.5](../common/jit-scim-coexistence-keycloak.md) — 詳細な Keycloak 実装例
