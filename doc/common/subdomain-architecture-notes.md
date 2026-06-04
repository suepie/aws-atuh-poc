# サブドメイン構成での認証基盤設計ノート

> **位置付け**: 接続アプリが「**同一親ドメインのサブドメイン**」（例: `app1.example.com` / `app2.example.com` / `auth.example.com`）で展開される場合の、本プロジェクトの認証基盤方式（Identity Broker + Cognito/Keycloak + Bearer JWT + OIDC SSO）との **適合性 + 設計指針 + 注意点** を一元化した技術メモ。
> **対象読者**: 認証基盤設計者 / アプリ実装者 / セキュリティレビュー担当者 / ヒアリング担当者
> **関連**:
> - [auth-patterns.md](auth-patterns.md) — 認証パターン総覧
> - [authz-architecture-design.md](authz-architecture-design.md) — 認可アーキテクチャ
> - [bff-implementation-notes.md](bff-implementation-notes.md) — BFF パターン実装
> - [§C-1 アーキテクチャ (proposal)](../requirements/proposal/common/01-architecture.md) — Identity Broker パターン
> - [hearing-checklist.md マスター表 C](../requirements/hearing-checklist.md) — B-100 アプリ構成

---

## 目次

1. [結論サマリー](#1-結論サマリー)
2. [想定されるドメイン構成パターン](#2-想定されるドメイン構成パターン)
3. [技術観点別の適合性評価](#3-技術観点別の適合性評価)
4. [Cookie / セッション設計の核心原則](#4-cookie--セッション設計の核心原則)
5. [SameSite / CORS / 現代ブラウザ規制への対応](#5-samesite--cors--現代ブラウザ規制への対応)
6. [本プロジェクト構成要素ごとの適合性](#6-本プロジェクト構成要素ごとの適合性)
7. [業界実例](#7-業界実例)
8. [設計上の注意点（必須チェックリスト）](#8-設計上の注意点必須チェックリスト)
9. [ヒアリング項目（5 項目）](#9-ヒアリング項目5-項目)
10. [リファレンス](#10-リファレンス)

---

## 1. 結論サマリー

| 観点 | 評価 |
|---|---|
| **本プロジェクト方式は成り立つか** | ✅ **成り立つ**（業界推奨パターン）|
| **完全別ドメイン構成との比較** | サブドメインの方が **Cookie / SameSite / iframe / TLS 管理 / BFF / Cognito Custom Domain 全てで有利** |
| **設計上の最重要原則** | **Cookie は各サブドメインに限定**（親ドメインで共有しない）+ **SSO は Hub セッション経由**（Cookie 共有不要）|
| **本プロジェクトへの影響** | **全構成要素で問題なし、複数で有利** |
| **現代ブラウザ規制（ITP / 3rd-party Cookie 廃止）の影響** | サブドメイン構成は影響小（Same-Site 扱い）|

---

## 2. 想定されるドメイン構成パターン

| パターン | 例 | 採用度 |
|---|---|:-:|
| **A. サブドメイン構成（同一親ドメイン）** | `app1.example.com` / `app2.example.com` / `auth.example.com` | ⭐ **業界主流** |
| B. 完全別ドメイン | `app1.com` / `app2.com` / `auth-platform.com` | △ 買収統合等の歴史的事情がある場合 |
| C. パスベース分離 | `example.com/app1` / `example.com/app2` | △ レガシー、現代では非推奨 |
| D. 混在 | 一部サブドメイン + 一部別ドメイン | △ 規模拡大過程で混在化 |

本ドキュメントは **パターン A サブドメイン構成** を主題とし、パターン B/D との比較を整理する。

---

## 3. 技術観点別の適合性評価

### 3.1 OIDC / SAML 認証フロー
| 観点 | サブドメイン構成 | 完全別ドメイン |
|---|:-:|:-:|
| Authorization Code Flow + PKCE | ✅ そのまま動作 | ✅ そのまま動作 |
| SAML SP / IdP | ✅ そのまま動作 | ✅ そのまま動作 |
| Token Exchange (RFC 8693) | ✅ 非依存 | ✅ 非依存 |
| Device Code Flow | ✅ 非依存 | ✅ 非依存 |
| Bearer JWT (HTTP Header) | ✅ 非依存 | ✅ 非依存 |

→ **プロトコル仕様レベルではドメイン構成に完全非依存**。

### 3.2 Cookie / セッション設計（最も影響大）
詳細は [§4 Cookie / セッション設計の核心原則](#4-cookie--セッション設計の核心原則) を参照。

### 3.3 SameSite / CORS（サブドメイン構成の優位点）
詳細は [§5 SameSite / CORS / 現代ブラウザ規制への対応](#5-samesite--cors--現代ブラウザ規制への対応) を参照。

### 3.4 BFF パターンとの相性

| 構成 | 推奨度 |
|---|:-:|
| `app1.example.com` で SPA + `app1.example.com/api` で BFF | ◎ 最適 |
| `app1.example.com` で SPA + `bff.example.com` で BFF（サブドメイン分離）| ◯ 要 CORS |
| `app1.com` SPA + `bff.app2.com` BFF（完全別ドメイン）| △ Cross-Site で複雑 |

→ サブドメイン構成は **BFF パターン構築が容易**（[Curity BFF gold standard 2025](https://curity.io/resources/learn/the-bff-pattern/) も同一親ドメイン構成を推奨）。

### 3.5 認証基盤の Custom Domain

| 製品 | Custom Domain 制限 | サブドメイン構成への影響 |
|---|---|---|
| **Cognito** | **1 Region あたり 4 Custom Domain**（ハードリミット）| 認証基盤を `auth.example.com` の **1 つだけ**にすれば全アプリ対応可能（**問題なし**）|
| **Keycloak / RHBK** | 制限なし | 任意 |

→ **アプリ別** のサブドメイン構成では Cognito の Custom Domain 制約は問題にならない。
→ **顧客企業ごと**に別 Custom Domain が必要な場合（§2.5 ブランディング）のみ 4 顧客制約が効く（別軸の議論）。

### 3.6 TLS 証明書管理

| 構成 | 証明書管理 |
|---|---|
| サブドメイン（`*.example.com`）| **ワイルドカード証明書 1 枚で全アプリ対応**（運用負荷小）|
| 完全別ドメイン | アプリごとに個別証明書（ACM 等で自動化可だが管理対象多）|

→ サブドメインのほうが運用シンプル。

### 3.7 Front-Channel Logout / iframe Silent Auth

| 観点 | サブドメイン | 完全別ドメイン |
|---|:-:|:-:|
| Front-Channel Logout (`<iframe>` で各 RP に GET) | ✅ Same-Site で安定 | ⚠ 3rd-party Cookie ブロック影響 |
| Silent Auth (`<iframe>` で IdP に prompt=none) | ✅ Same-Site で動作 | ⚠ 主要ブラウザでブロック増 |

→ 2024-2026 のブラウザ規制で **完全別ドメインの iframe ベース SSO は厳しくなっている**。サブドメイン構成は**現代の業界推奨**。

---

## 4. Cookie / セッション設計の核心原則

### 4.1 SSO 実現の本質

**SSO とは「認証基盤 (Hub) のセッション Cookie を再利用して各アプリにログインする仕組み」**。

各アプリの Cookie 共有は **不要かつ非推奨**。SSO は OIDC リダイレクトで Hub セッションを参照することで実現される。

### 4.2 Cookie の役割分担

| Cookie 種別 | 設定対象 | 用途 |
|---|---|---|
| **Hub の SSO セッション Cookie** | `auth.example.com` | 認証基盤側のログインセッション保持 |
| **各アプリのセッション Cookie** | `app1.example.com` 等（独立）| アプリごとのセッション保持（BFF Cookie 等）|
| **アプリ間 Cookie 共有**（親ドメイン `.example.com`）| **使わない** | アプリ間 Cookie 漏洩リスクのため非推奨 |

### 4.3 推奨 Cookie 設定

```http
# Hub の SSO セッション Cookie (auth.example.com)
Set-Cookie: AUTH_SESSION_ID=abc123;
  Domain=auth.example.com;     ← 親ドメイン共有しない、Hub 専用
  Path=/;
  HttpOnly;
  Secure;
  SameSite=Lax

# アプリの BFF セッション Cookie (app1.example.com)
Set-Cookie: APP_SESSION_ID=xyz789;
  Domain=app1.example.com;     ← または Domain 未指定（Host-only Cookie 推奨）
  Path=/;
  HttpOnly;
  Secure;
  SameSite=Lax
```

### 4.4 SSO シーケンス（サブドメイン構成）

```
1. User → app1.example.com にアクセス
2. app1 → セッションなし、auth.example.com へリダイレクト
3. auth → SSO セッション Cookie あり → ログイン済み判定
4. auth → app1 に Authorization Code リダイレクト
5. app1 → Code を Token に交換、独自セッション Cookie 発行
6. User → app2.example.com にアクセス
7. app2 → セッションなし、auth.example.com へリダイレクト
8. auth → SSO セッション Cookie あり（同一ブラウザ）→ ログイン済み判定
9. auth → app2 に Authorization Code リダイレクト（再認証なし）
10. app2 → Code を Token に交換、独自セッション Cookie 発行
```

→ **アプリ間 Cookie 共有は不要**、Hub の SSO セッション Cookie 1 つだけで SSO 成立。

### 4.5 アンチパターン: 親ドメイン Cookie 共有

```http
# ❌ アンチパターン
Set-Cookie: APP_SESSION_ID=xyz789;
  Domain=.example.com;         ← 全サブドメインで共有可能 = 危険
  ...
```

**リスク**:
- XSS が 1 アプリで発生 → 全アプリのセッション漏洩
- Subdomain Takeover 攻撃で全アプリのセッション取得可能
- マルチテナント時に他テナントへの Cookie 漏洩

→ **必ず各サブドメインに限定**（Host-only Cookie 推奨）。

---

## 5. SameSite / CORS / 現代ブラウザ規制への対応

### 5.1 SameSite Cookie 動作の違い

| 構成 | SameSite 必要設定 | 説明 |
|---|---|---|
| サブドメイン（同一親）| `Lax` で十分（多くの場合）| Same-Site 扱い、現代ブラウザ規制の影響小 |
| 完全別ドメイン | **`None` + `Secure` 必須** | Cross-Site 扱い、3rd-party Cookie 規制の影響大 |

### 5.2 現代ブラウザ規制（2024-2026）

| 規制 | サブドメイン影響 | 完全別ドメイン影響 |
|---|:-:|:-:|
| **Safari ITP (Intelligent Tracking Prevention)** | 影響なし（Same-Site）| 3rd-party Cookie ブロック対象 |
| **Chrome 3rd-party Cookie 廃止** (Privacy Sandbox) | 影響なし | 大きな影響、対策必要 |
| **Firefox Total Cookie Protection** | 影響軽微 | 影響大 |
| **Brave / Tor** | 軽微 | 大きな影響 |

→ **完全別ドメイン + Cookie ベース SSO は持続不可能**になりつつある。サブドメイン構成は **将来安泰**。

### 5.3 CORS 設定例（サブドメイン構成）

```http
# auth.example.com のレスポンス（CORS 設定）
Access-Control-Allow-Origin: https://app1.example.com
Access-Control-Allow-Credentials: true
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
```

各アプリの Origin を Whitelist で明示。`*.example.com` のワイルドカード許可は **CORS 仕様では不可**（Origin は完全一致必要）、各アプリ別個に登録する。

---

## 6. 本プロジェクト構成要素ごとの適合性

| 構成要素 | サブドメイン構成での影響 |
|---|---|
| **Identity Broker パターン (§C-1)** | ✅ 影響なし |
| **OIDC SSO** | ✅ **むしろ有利**（iframe ベース動作が安定）|
| **OIDC RP / OP モード（§3.4）** | ✅ 非依存 |
| **SAML SP / IdP モード（§3.4 / K5）** | ✅ 非依存 |
| **Bearer JWT (§4.1)** | ✅ HTTP ヘッダーなので非依存 |
| **JWKS (§4.1)** | ✅ 非依存 |
| **MFA (§3.2)** | ✅ 非依存 |
| **強制再認証・ステップアップ (§5.6)** | ✅ 非依存 |
| **Back-Channel Logout (K7) / Token Revocation (K8) (§5.3)** | ✅ 非依存（サーバー間通信）|
| **Front-Channel Logout (§5.2)** | ✅ Same-Site で安定動作 |
| **Cognito Custom Domain** | ✅ アプリ別なら 1 つ (`auth.example.com`) で対応 |
| **Cookie Consent / GDPR (§8.4)** | ✅ 同意管理 UI もサブドメイン構成で OK |
| **BFF パターン** | ✅ **サブドメイン構成と相性最良** |
| **マルチテナント設計 (§2.4)** | ✅ アプリ別サブドメインとテナント別 URL は独立軸（混在も可能）|
| **顧客別ブランディング (§2.5)** | △ 顧客別 Custom Domain が必要な場合は別途検討（アプリ別サブドメインとは別軸）|
| **ハイブリッド構成 (§1.3)** | ✅ コア = `auth.example.com`、エッジ = `edge1.example.com` で配置可能 |

→ **全要素で問題なし、複数要素で有利**。

---

## 7. 業界実例

| サービス | ドメイン構成 | 補足 |
|---|---|---|
| **Google Workspace** | `mail.google.com` / `drive.google.com` / `calendar.google.com` | アプリ別サブドメイン、`accounts.google.com` で SSO |
| **AWS Console** | `console.aws.amazon.com` + `*.amazonaws.com` | サービス別サブドメイン、AWS SSO 連携 |
| **Microsoft 365** | `outlook.office.com` / `teams.microsoft.com` / `*.office.com` | アプリ別サブドメイン + 一部別ドメイン、`login.microsoftonline.com` で SSO |
| **Atlassian** | `<workspace>.atlassian.net` 内のパス分離 + 一部別サブドメイン | Workspace 別サブドメイン構成 |
| **Slack** | `<workspace>.slack.com` | 顧客（Workspace）別サブドメイン |
| **GitHub** | `github.com` + `api.github.com` | 機能別サブドメイン分離 |
| **Salesforce** | `<instance>.salesforce.com` / `<org>.lightning.force.com` | 顧客別サブドメイン |

→ **大手 SaaS の主流はサブドメイン構成**、完全別ドメインは買収統合等の歴史的事情がある場合のみ。

---

## 8. 設計上の注意点（必須チェックリスト）

| # | 注意点 | 対策 | 優先度 |
|:-:|---|---|:-:|
| 1 | **Cookie Domain を親ドメインに設定しない** | 各アプリの Cookie は `Domain` 未指定 or サブドメイン限定 | 🔥 |
| 2 | **XSS の影響範囲** — サブドメイン間で Cookie 漏洩リスク | CSP / SameSite / HttpOnly / Secure を全アプリで徹底 | 🔥 |
| 3 | **CSP の `default-src` 設計** | サブドメイン許可リストを明示（`*.example.com` ではなく具体的に）| ◯ |
| 4 | **Subdomain Takeover 攻撃** | 未使用サブドメインの DNS レコード残置を防ぐ、定期監査 | 🔥 |
| 5 | **Public Suffix List (PSL) チェック** | 親ドメインが PSL 外であることを確認（`co.jp` のような PSL ドメイン直下は Cookie 共有不可だが、本件では問題なし）| ◯ |
| 6 | **OIDC `redirect_uri` Whitelist** | 各アプリのサブドメインを全て Cognito/Keycloak に登録 | 🔥 |
| 7 | **Cognito callback URL 上限** | Cognito は 1 App Client 100 callback URL、アプリ数が多い場合は App Client 分離 | ◯ |
| 8 | **TLS 証明書の自動更新** | ワイルドカード証明書（ACM）の自動更新を確実に運用 | ◯ |
| 9 | **CORS 設定の Whitelist 化** | `*.example.com` のワイルドカードは CORS 仕様では不可、各 Origin を明示 | 🔥 |
| 10 | **第三者ドメインからの iframe 埋め込み** | `X-Frame-Options: DENY` または CSP `frame-ancestors` で制限 | ◯ |

---

## 9. ヒアリング項目（5 項目）

マスター表 C（[B-100](../requirements/hearing-checklist.md)）の補足として、以下を確認:

| # | 確認事項 | 想定回答 | 影響 |
|:-:|---|---|---|
| 1 | **アプリのドメイン構成方針** | (A) 全アプリ同一親ドメインのサブドメイン / (B) アプリ別の独立ドメイン / (C) 混在 | Cookie / CORS / TLS 設計 |
| 2 | **共通親ドメイン** | `example.com` 等（A or C 採用時）| 認証基盤の配置 URL |
| 3 | **認証基盤の配置 URL** | `auth.example.com` / `idp.example.com` 等 | Cognito Custom Domain |
| 4 | **Cookie 共有方針** | (A) 各サブドメイン独立（**推奨**）/ (B) 親ドメイン共有 | セキュリティ設計 |
| 5 | **SSO 実現方式** | OIDC リダイレクトで Hub セッション参照（**推奨、標準**）/ Cookie 共有 | 全体方針 |

→ これにより:
- Cookie Domain 設計を明確化
- SameSite / CORS 設定の事前合意
- Cognito Custom Domain 必要数の見積もり
- CSP / Subdomain Takeover 対策の Phase 化

---

## 10. リファレンス

### 10.1 仕様 / 標準

- [RFC 6265 HTTP State Management (Cookie)](https://datatracker.ietf.org/doc/html/rfc6265)
- [RFC 6265bis (draft) Cookie 仕様改訂](https://datatracker.ietf.org/doc/draft-ietf-httpbis-rfc6265bis/)
- [SameSite Cookie (MDN)](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie/SameSite)
- [Public Suffix List](https://publicsuffix.org/)
- [OIDC Core 1.0](https://openid.net/specs/openid-connect-core-1_0.html)
- [OIDC Session Management 1.0](https://openid.net/specs/openid-connect-session-1_0.html)
- [OIDC Front-Channel Logout 1.0](https://openid.net/specs/openid-connect-frontchannel-1_0.html)
- [OIDC Back-Channel Logout 1.0](https://openid.net/specs/openid-connect-backchannel-1_0.html)

### 10.2 業界ベストプラクティス

- [Curity BFF Gold Standard 2025](https://curity.io/resources/learn/the-bff-pattern/) — サブドメイン構成 BFF の推奨パターン
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html) — XSS / CSP / Cookie セキュリティ
- [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html) — Cookie 設計
- [Subdomain Takeover (HackerOne / OWASP)](https://owasp.org/www-community/attacks/Subdomain_Takeover) — 攻撃手法と対策
- [Chrome 3rd-party Cookie Phaseout (Privacy Sandbox)](https://developers.google.com/privacy-sandbox/3pcd) — 廃止スケジュール
- [Safari ITP](https://webkit.org/blog/category/privacy/) — ブラウザ規制動向

### 10.3 製品ドキュメント

- [AWS Cognito Custom Domains](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-add-custom-domain.html)
- [AWS Cognito Limits](https://docs.aws.amazon.com/cognito/latest/developerguide/limits.html) — Custom Domain 4/region 制限
- [Keycloak Hostname Configuration](https://www.keycloak.org/server/hostname)

### 10.4 関連内部ドキュメント

- [auth-patterns.md](auth-patterns.md) — 認証パターン総覧
- [authz-architecture-design.md](authz-architecture-design.md) — 認可アーキテクチャ
- [bff-implementation-notes.md](bff-implementation-notes.md) — BFF パターン実装
- [token-exchange-spec-and-patterns.md](token-exchange-spec-and-patterns.md) — Token Exchange 仕様
- [keycloak-network-architecture.md](keycloak-network-architecture.md) — Keycloak ネットワーク構成
- [§C-1 アーキテクチャ (proposal)](../requirements/proposal/common/01-architecture.md) — Identity Broker パターン
- [hearing-checklist.md マスター表 C](../requirements/hearing-checklist.md) — B-100 アプリ構成
- [terms-and-codes-reference.md](../requirements/terms-and-codes-reference.md) — コード体系

---

## 改訂履歴

- 2026-06-04: 初版作成。サブドメイン構成での認証基盤方式適合性 + 設計指針 + ヒアリング項目 5 項目を網羅
