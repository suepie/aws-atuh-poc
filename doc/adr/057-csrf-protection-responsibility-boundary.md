# ADR-057: CSRF 対策の責任分界と実装パターン

- **ステータス**: Proposed（要件定義フェーズで Accepted 昇格予定）
- **日付**: 2026-07-06
- **関連**:
  - [ADR-030 最小 JWT クレーム設計](030-minimal-jwt-claim-design.md)（Bearer JWT + SPA を前提とする実装との整合）
  - [ADR-038 ユーザ管理画面](038-tenant-admin-portal.md)（本基盤直下の主要 SPA / Backend、認可 C ハイブリッド）
  - [ADR-020 HRD ヒントキー戦略](020-hrd-hint-keys-mixed-login.md)（OAuth `state` 併記）
  - [ADR-024 ログイン画面アーキテクチャとブランディング](024-login-screen-architecture-branding.md)（Keycloak Theme の CSRF）
  - [ADR-050 モバイルアプリ認証設計](050-mobile-sdk-native-auth.md)（AppAuth + PKCE と CSRF）
  - [ADR-023 ServiceNow SP 連携](023-servicenow-sp-integration.md)（SAML の RelayState / IdP-initiated リスク）
  - [§NFR-4.3 攻撃対策](../requirements/proposal/nfr/04-security.md#nfr-43-攻撃対策)
  - [§C-7.3.30 CSRF 対策の責任分界](../requirements/proposal/common/07-implementation-architecture.md#c-7-3-30-csrf-対策の責任分界adr-057-2026-07-06-新規)

---

## Context

### 背景

顧客レビューで「**CSRF トークンは認証基盤で発行すべきか、各 API で発行すべきか**」という設計質問が出た。従来 CSRF 対策は Web フレームワーク（Rails / Django / Spring Security）に暗黙的に埋め込まれてきたが、本基盤のような **B2B SaaS 共通認証基盤 + SPA + Bearer JWT + マイクロサービス化** の構成では、責任分界を明示しないと以下 3 つの誤設計が発生する:

1. **認証基盤（Keycloak）に CSRF トークン API を作らせる**（Keycloak は API GW ではないため役割違い、拡張コスト高）
2. **各 API が独自方式で CSRF 実装**（バラつきによる漏れ・ブランク発生）
3. **Bearer JWT でも CSRF トークンを二重発行**（過剰実装、UX 摩擦）

### 業界用語の整理

| 用語 | 意味 |
|---|---|
| **CSRF**（Cross-Site Request Forgery）| 認証済みユーザーのブラウザに攻撃者が用意したリクエストを送信させる攻撃 |
| **Synchronizer Token Pattern** | サーバがランダム値をセッション + フォーム / ヘッダに埋め込み、送信時に一致確認（OWASP 標準）|
| **Double Submit Cookie** | ランダム値を Cookie + ヘッダ両方に載せる。サーバ側セッション状態不要（Stateless）|
| **SameSite Cookie** | Cookie 属性で `Lax` / `Strict` / `None` を指定。Lax がモダンブラウザのデフォルト |
| **Origin / Referer 検証** | HTTP ヘッダで送信元 origin を検証（軽量、フォールバック用）|
| **OAuth `state`** | 認可要求時のランダム値。認可コード横流し（CSRF）と混同型 CSRF の両方を防ぐ |
| **PKCE**（RFC 7636）| Public Client の認可コード横流し対策（S256 code_challenge）|

### なぜ本 ADR が必要か

- CSRF の教科書的説明は「セッション Cookie を使う画面」に閉じているが、本基盤は **SPA + Bearer JWT + Keycloak UI（Cookie）+ モバイル（Bearer）+ SAML/OAuth 認可フロー** の 4 系統が混在
- 4 系統それぞれで **CSRF が成立する条件・対策・責任主体** が異なる
- **「認証基盤の責任範囲」を明確化しないと、顧客から「共通認証基盤なのに CSRF まで面倒見てくれないのか」と誤解される**（実際は API 側で対応する方が原則安全）

---

## Decision

### 採用方針

**「攻撃対象（＝状態変更が起きる箇所）で防御する」**という OWASP 原則を採用し、以下 3 責任層に明示分界する:

| 責任層 | 対象 UI / API | CSRF 対策 | 主体 |
|---|---|---|---|
| **L1: 認証基盤内 UI** | Keycloak ログイン画面 / アカウント設定画面 / Admin Console / password-reset フォーム | **Keycloak 標準の CSRF トークン**（KC 内部で自動発行、Session Cookie 内 `KC_RESTART` / hidden `_csrf` form field）| **本基盤（Keycloak 標準機能で完結、追加実装なし）** |
| **L2: OAuth / OIDC / SAML 認可フロー** | authorize エンドポイント / SAML AuthnRequest | **`state` パラメータ（必須化）+ PKCE（Public Client 必須）+ SameSite=Lax Cookie**、SAML は `RelayState` + IdP-initiated 拒否 | **本基盤（RP 実装ガイドで顧客 SPA / SP に強制）** |
| **L3: アプリ API（状態変更）** | ユーザ管理画面 API / 各業務アプリ API / モバイル BFF | **Bearer JWT + CORS + Origin/Referer 検証で原則 CSRF 免疫**。Cookie セッション採用時のみ Double Submit Cookie or Synchronizer Token | **各アプリ / API プラットフォーム（本基盤は原則・パターン提示のみ）** |

### 本基盤の Phase 1 採用（2026-07-06 確定）

- **L1**：Keycloak 標準機能 → **追加開発ゼロ**
- **L2**：OIDC/OAuth 認可要求に `state` + PKCE を **RP 実装ガイド（[hrd-implementation-keycloak.md](../common/hrd-implementation-keycloak.md)）と接続顧客ドキュメントで必須化**、SAML は **IdP-initiated SSO 原則不許可**（SP-initiated + `InResponseTo` 検証を推奨）
- **L3**：**Bearer JWT + `Authorization: Bearer <token>` 前提**、Cookie セッションを使うアプリは各アプリ側で対応（本基盤は「§C-7.3.30 参照パターン」を提供）

---

## A. CSRF 攻撃モデルの再整理（本基盤の 4 系統別）

### A.1 4 系統マトリクス

| 系統 | 認証情報の運び方 | CSRF 成立条件 | 本基盤での該当 |
|---|---|:---:|---|
| **Cookie セッション（同一 origin）** | サーバ Session Cookie（自動送信）| ✅ 成立 | Keycloak UI（L1）|
| **Bearer JWT（Authorization ヘッダ）** | JS が明示付与、ブラウザは自動送信しない | ❌ 原則不成立 | ユーザ管理画面 SPA → 管理 API（L3）/ 各アプリ SPA → API |
| **BFF + HttpOnly Cookie（SPA でも）** | サーバ Session Cookie（自動送信）| ✅ 成立 | Cookie セッション採用アプリ（L3 の一部）|
| **モバイル（Bearer JWT、System Browser）** | AppAuth ライブラリが明示付与 | ❌ 原則不成立 | ADR-050 モバイル BFF |

**キーポイント**：**「ブラウザが自動送信するか」が CSRF 成立の分岐点**。Bearer 方式は自動送信されないため CSRF 免疫。

### A.2 見落としがちな 5 パターン

| 攻撃パターン | 説明 | 対策 | 責任 |
|---|---|---|---|
| **A. Login CSRF** | 攻撃者の資格情報でログインさせ、被害者の入力を攻撃者アカウントに残す | **`state` 必須化 + PKCE + Keycloak 標準 CSRF**（L1 + L2 で完結）| 本基盤 |
| **B. Logout CSRF** | 攻撃サイトから強制ログアウトさせて業務中断 | Keycloak `logout` は POST 必須化（`POST_LOGOUT_REDIRECT_URI` + `id_token_hint`）| 本基盤 |
| **C. IdP-initiated SAML CSRF** | 攻撃者の IdP からの Response を被害者ブラウザに投げ込む | **SP-initiated 必須化 + `InResponseTo` 検証**（ADR-023 §J に追記）| 本基盤 + SP 側実装 |
| **D. OAuth state 未検証** | Callback で state を検証しない SPA が Authz Code 横流し攻撃を受ける | **`state` 検証必須（RP 実装ガイド + 顧客ドキュメント）** | 顧客 RP（本基盤はガイド提供）|
| **E. Refresh Token CSRF** | httpOnly Refresh Token Cookie が使われ、攻撃サイトが `refresh` を叩ける | Refresh Token を Cookie 保管する場合は **SameSite=Strict + Custom Header 検証** | 顧客 RP / API プラットフォーム |

---

## B. なぜ「認証基盤で全部やる」ではダメか

### B.1 責務違反（Concerns violation）

- **認証基盤（Keycloak）は「認証」と「発行」が主責務**、認可の状態変更ポイントは知らない
- **CSRF トークンは「状態変更する箇所で検証」が OWASP 原則**（[CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)）
- 認証基盤が CSRF トークン発行 API を持つと **各 API が「認証基盤に問い合わせて検証」する必要** → 認証基盤が SPOF・レイテンシボトルネックに

### B.2 セッションモデル依存性

- CSRF トークンの実装（Synchronizer / Double Submit）は **API 側のセッション実装**に依存
  - Cookie セッション → Synchronizer Token（サーバ側 state 必要）
  - Stateless → Double Submit Cookie
- 認証基盤は API のセッション実装を知らない・知るべきでない（**責務分離原則**）

### B.3 Bearer JWT 前提での過剰実装

- 本基盤の主要フローは **SPA + `Authorization: Bearer <token>`**（ADR-030）
- Bearer は **ブラウザが自動送信しないため CSRF 免疫**
- ここに CSRF トークンを追加すると **開発コスト増 × UX 摩擦 × 実装バグ増** の 3 重負担

---

## C. Bearer JWT が「CSRF 免疫」である 3 つの前提条件

Bearer JWT で CSRF 免疫を成立させるには **以下 3 条件すべて** の充足が必要。1 つでも欠けると条件付きで CSRF が復活する。

| 条件 | 説明 | 検証方法 |
|---|---|---|
| **C-1: Cookie 保管禁止** | JWT を Cookie に保存しない（localStorage / sessionStorage / Memory）| ブラウザ DevTools → Application → Cookies で JWT がないこと |
| **C-2: 明示付与のみ** | `Authorization: Bearer <token>` を JS が明示的にセット、ブラウザ自動送信させない | fetch/axios interceptor 経路のみで送信 |
| **C-3: CORS 適切設定** | `Access-Control-Allow-Origin` を **具体的な RP origin** に限定、`*` 不可、`Access-Control-Allow-Credentials: false` | API GW / ALB の CORS 設定確認 |

**注意点**：**localStorage 保管は XSS リスク**があるため、**XSS 対策（CSP / DOMPurify / React 標準 escape）とセット**が前提。CSRF 免疫と XSS 脆弱性はトレードオフではない（両方対策する）。

---

## D. 実装パターン集（責任層別・詳細）

### D.1 L1: Keycloak UI（本基盤担当、追加実装ゼロ）

Keycloak は **既定で CSRF 対策済** の以下 UI を提供:

| UI | CSRF 対策方式 | 実装状態 |
|---|---|:---:|
| ログイン画面（`/realms/{r}/login-actions/authenticate`）| POST + hidden `session_code` + `execution` トークン | ✅ 標準 |
| アカウント設定画面（`/realms/{r}/account/`）| Bearer JWT + Origin 検証 | ✅ 標準 |
| Admin Console（`/admin/`）| Bearer JWT + Origin 検証 | ✅ 標準 |
| password-reset フォーム | 使い捨てトークン（メール送付）| ✅ 標準 |
| Consent 画面 | POST + `session_code` | ✅ 標準 |
| `logout` エンドポイント | POST 化（`id_token_hint` + `POST_LOGOUT_REDIRECT_URI`）| ⚠ **RP 実装ガイド必要**（GET 化しないこと）|

**本基盤の作業**: Keycloak Custom Theme 側で `<form>` の hidden field を消さないこと（Theme 実装ガイド §5 に明記）

### D.2 L2: OAuth / OIDC / SAML 認可フロー（本基盤担当、RP ガイド化）

#### D.2.1 OIDC / OAuth 2.0（新規実装アプリ）

```
GET /realms/basis/protocol/openid-connect/auth?
  response_type=code&
  client_id=expense-spa&
  redirect_uri=https://expense.example.com/callback&
  scope=openid&
  state={random-256bit}&          ← 必須（CSRF 対策）
  nonce={random-256bit}&          ← 必須（ID Token 再生攻撃対策）
  code_challenge={S256-hash}&     ← Public Client は必須（PKCE）
  code_challenge_method=S256
```

- **`state` 未検証は最も頻発する脆弱性**（[OWASP OAuth 2.0 Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/OAuth2_Cheat_Sheet.html)）
- Callback 側で **`state` を必ずセッション保存値と照合**、不一致は 400 で拒否
- 実装ガイドを [hrd-implementation-keycloak.md §5](../common/hrd-implementation-keycloak.md) と接続顧客ドキュメント（Basis Integration Guide）で提供

#### D.2.2 SAML 2.0（ServiceNow SP 等既存 SaaS 連携）

- **SP-initiated（推奨）**: SAML AuthnRequest 時に `RelayState` にランダム値を入れ、Response の `InResponseTo` と照合
- **IdP-initiated（原則不許可）**: `InResponseTo` が使えないため CSRF 対策困難。**やむを得ず使う場合は「短命 nonce Cookie + IdP-initiated allowed URI ホワイトリスト」で緩和**（ADR-023 §J に追記）

#### D.2.3 State / Nonce の実装要件（RP 側）

| 項目 | 要件 |
|---|---|
| エントロピー | 128 bit 以上（`crypto.getRandomValues(new Uint8Array(32))` 相当）|
| 保存先 | HttpOnly Cookie or sessionStorage（BFF 有：Server Session）|
| TTL | 10 分（認可コード交換タイムアウトと同期）|
| 使い捨て | 1 回検証したら即削除（Reuse Detection）|

### D.3 L3: アプリ API（各アプリ担当、本基盤はパターン提示のみ）

#### D.3.1 Bearer JWT（推奨、本基盤直下 §C-7.3.13 ユーザ管理画面 も本方式）

**CSRF 対策不要**（前提 C-1〜C-3 充足時）。代わりに以下を実装:

| 対策 | 実装 |
|---|---|
| **JWT 保管** | Memory / sessionStorage（**Cookie 保管禁止**）|
| **CORS** | Origin ホワイトリスト明示 + `Access-Control-Allow-Credentials: false` |
| **Origin/Referer 検証**（軽量フォールバック）| API GW / ALB Level で `Origin` ヘッダ検証（optional）|
| **XSS 対策** | CSP `default-src 'self'; script-src 'self'` + React 標準 escape + DOMPurify |

#### D.3.2 Cookie セッション（BFF パターン、Cookie に JWT 隠蔽）

**CSRF トークン必要**。以下 2 パターンから選択:

##### パターン D.3.2.a Double Submit Cookie（推奨、Stateless）

```
1. サーバは初回 GET で以下を発行:
   Set-Cookie: XSRF-TOKEN={random-256bit}; SameSite=Lax; Path=/
   （HttpOnly なし = JS 読取可）
2. SPA は Cookie を読み取り、ヘッダに詰めて送信:
   X-XSRF-TOKEN: {random-256bit}
3. サーバは Cookie 値と Header 値の一致を確認、不一致で 403
```

- **Angular / axios 標準対応**（`XSRF-TOKEN` / `X-XSRF-TOKEN` は業界慣例）
- **SameSite=Lax で兼用防御**（モダンブラウザは Cookie 側で自動遮断）

##### パターン D.3.2.b Synchronizer Token Pattern（Stateful）

```
1. サーバ Session に csrf_token を保存
2. 各 form / API 呼び出しに hidden field or Header で送信
3. サーバは Session 値と一致確認
```

- **Rails / Django / Spring Security 標準**
- サーバ側 Session が必要（Redis / DDB / Sticky Session）

#### D.3.3 SameSite Cookie の防御効果と限界

| SameSite 値 | GET | POST（form）| POST（fetch/XHR）| CSRF 防御 |
|---|:---:|:---:|:---:|---|
| **Strict** | ❌ 送信されない | ❌ | ❌ | ✅ 完全 |
| **Lax（ブラウザ既定）** | ✅ | ❌ | ❌ | ✅ 実用充分 |
| **None（Secure 必須）** | ✅ | ✅ | ✅ | ❌ 防御なし |

- **Lax がモダンブラウザの既定**、これだけで **9 割の CSRF は自動遮断**
- 残り 1 割（GET で状態変更する API、iframe 埋め込み、非モダンブラウザ）は **CSRF トークン併用で完全防御**

---

## E. モバイル / SAML / 特殊系の扱い（ADR-050 / ADR-023 連動）

### E.1 モバイル（AppAuth + System Browser、ADR-050）

- **AppAuth ライブラリが System Browser 経由で認可コード取得** → Bearer JWT 発行
- **ブラウザ自動送信 Cookie は使わない** → **CSRF 免疫**
- **PKCE 必須**（Public Client）

### E.2 ServiceNow SP（SAML JIT、ADR-023）

- **SP-initiated 推奨**（`RelayState` + `InResponseTo`）
- IdP-initiated 許容時は **§C.2 短命 nonce Cookie 方式**
- ADR-023 §J に本 ADR の判断を追記

### E.3 M2M / API-to-API（OAuth Client Credentials）

- **CSRF 対象外**（ブラウザを経由しないため）
- Client Credentials Grant + **相互 mTLS or DPoP**（別 ADR 候補）

---

## F. Consequences

### F.1 Positive（本方針採用の効用）

- **開発コスト削減**：本基盤側で CSRF トークン発行 API を作らない（数百万円級の削減）
- **業界標準準拠**：Auth0 / Okta / Microsoft Entra ID 同パターン（それぞれ「CSRF は API 側の責任」を明示）
- **顧客説明容易**：「Bearer JWT + CORS + SameSite Lax で CSRF 免疫、Cookie 使うなら各アプリ責任」で完結
- **Keycloak バージョン追従負担ゼロ**（標準機能に依存、独自拡張なし）

### F.2 Negative / トレードオフ

- **顧客 RP 側の実装負担**：`state` + PKCE + Callback 検証が必須（**RP 実装ガイド + 顧客ドキュメントで明示**）
- **Cookie セッション採用アプリ側の実装負担**：API プラットフォーム側で標準化しないと各アプリで独自実装のばらつき
- **教育コスト**：顧客の伝統的 Rails / Java 開発者に「Bearer JWT で CSRF 不要」を説明する労力

### F.3 リスク軽減

- **顧客 RP 側の実装ミス**（`state` 未検証、Cookie 保管 JWT）→ **[Basis Integration Guide] チェックリスト提供 + PR テンプレ + サンプル SDK 公開**
- **Cookie セッション採用アプリの CSRF 漏れ** → **API プラットフォーム側で Double Submit Cookie 参照実装提供**（`doc/api-platform/` 側で別 ADR）
- **Keycloak バージョンアップで CSRF 挙動変更** → **Release Note レビュー + Regression テスト**（[ADR-055 §A.7 バージョン追従プロセス] 内でカバー）

---

## G. 業界事例・裏どり

| ベンダー / 標準 | 本 ADR との整合 |
|---|---|
| **Auth0** [Mitigate CSRF Attacks](https://auth0.com/docs/secure/attack-protection/state-parameters) | ✅ 「Auth0 は `state` 発行、CSRF トークンは各 API 責任」明記 |
| **Okta** [Preventing OAuth 2.0 CSRF](https://developer.okta.com/docs/guides/implement-grant-type/authcodepkce/main/#request-an-authorization-code) | ✅ `state` + PKCE を必須要件化 |
| **Microsoft Entra ID** [Anti-CSRF cookies](https://learn.microsoft.com/en-us/entra/msal/dotnet/advanced/anti-csrf-cookies) | ✅ Cookie ベースは MSAL 内蔵、Bearer は各 API 責任 |
| **OWASP CSRF Prevention Cheat Sheet** | ✅ 「Bearer JWT + CORS + SameSite Lax = CSRF 免疫」明記 |
| **OWASP OAuth 2.0 Cheat Sheet** | ✅ `state` + PKCE + Redirect URI 完全一致 = OAuth CSRF 対策の 3 点セット |
| **RFC 6749 §10.12 OAuth 2.0 CSRF** | ✅ `state` パラメータ必須化の根拠 |
| **RFC 7636 PKCE** | ✅ Public Client の必須要件 |
| **Keycloak Server Admin Guide** | ✅ Keycloak UI は標準で CSRF トークン発行、外部 API には関与しないと明記 |

---

## H. 反映先

### H.1 ドキュメント反映（本 ADR 作成時に同期反映）

- [doc/adr/00-index.md](00-index.md)：ADR-057 追加
- [§C-7.3.30](../requirements/proposal/common/07-implementation-architecture.md#c-7-3-30-csrf-対策の責任分界adr-057-2026-07-06-新規)：新規セクション「CSRF 対策の責任分界」追加
- [§NFR-4.3 攻撃対策](../requirements/proposal/nfr/04-security.md#nfr-43-攻撃対策)：ベースライン表に「CSRF 対策」行 + ADR-057 リンク追加

### H.2 顧客 / RP ガイド（Phase 1 スコープ、Phase 2 以降拡充）

- **[Basis Integration Guide]（未作成、Phase 2 予定）** ：`state` + PKCE + Callback 検証チェックリスト
- **[hrd-implementation-keycloak.md §5]**：認可要求サンプルコード（`state` 生成含む）
- **[doc/api-platform/]** 側：Double Submit Cookie 参照実装 ADR 起票（別途 API プラットフォーム側で）

### H.3 ヒアリング項目追加候補（本 ADR 起票時点で TBD）

| 項目 | 記号 | 対象 | 内容 |
|---|---|---|---|
| Bearer JWT 保管方針 | B-CSRF-1 | 顧客 SPA | localStorage / Memory / Cookie / BFF |
| Cookie セッション採用アプリ | B-CSRF-2 | 顧客業務アプリ | 存在の有無、CSRF 対策の現状 |
| IdP-initiated SAML 要件 | B-CSRF-3 | 大口 SaaS 顧客 | 必須 / SP-initiated 移行可否 |
| Refresh Token 保管方針 | B-CSRF-4 | 顧客 SPA / モバイル | localStorage / HttpOnly Cookie / Secure Enclave |

---

## I. TBD / 要検討

- **Phase 2 での判断**：DPoP（[RFC 9449](https://datatracker.ietf.org/doc/html/rfc9449)）採用可否 → Bearer から DPoP-bound Access Token へ移行時に CSRF 免疫がどう変化するか
- **BFF パターン標準化**：Cookie セッションを使うアプリ用の参照実装（Double Submit Cookie）を **本基盤側で「参照アプリ」として公開**するか、それとも `doc/api-platform/` に閉じるか
- **Trust Center 記載**：ADR-036 縮小により Trust Center は削除されたため、顧客監査時の CSRF 対策説明資料の格納先を [customer-doc/security.md](../common/customer-doc/security.md) 想定として明記

---

## J. 関連 ADR / メモリ

- [ADR-030 最小 JWT クレーム設計](030-minimal-jwt-claim-design.md) — Bearer JWT 前提の根拠
- [ADR-020 HRD ヒントキー戦略](020-hrd-hint-keys-mixed-login.md) — `state` の使い所
- [ADR-023 ServiceNow SP 連携](023-servicenow-sp-integration.md) — §J に本 ADR §E.2 の判断を追記
- [ADR-024 ログイン画面アーキテクチャ](024-login-screen-architecture-branding.md) — Custom Theme での CSRF hidden field 保持義務
- [ADR-038 ユーザ管理画面](038-tenant-admin-portal.md) — L3 実装例（Bearer JWT + Lambda Authorizer）
- [ADR-050 モバイルアプリ認証](050-mobile-sdk-native-auth.md) — E.1 モバイル CSRF 免疫の根拠

---

**変更履歴**

| 日付 | 内容 |
|---|---|
| 2026-07-06 | 初版作成（顧客レビューでの CSRF トークン担務質問を起点、責任分界 L1/L2/L3 モデル確立）|
