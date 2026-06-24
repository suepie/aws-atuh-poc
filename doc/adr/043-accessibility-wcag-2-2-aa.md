# ADR-043: アクセシビリティ設計（WCAG 2.2 AA + JIS X 8341-3 準拠）

- **ステータス**: Proposed（要件定義フェーズで Accepted に昇格予定）
- **日付**: 2026-06-23
- **関連**:
  - [ADR-024 ログイン画面アーキテクチャとブランディング 4 パターン](024-login-screen-architecture-branding.md)
  - [ADR-038 ユーザ管理画面](038-tenant-admin-portal.md)
  - [ADR-021 Post-login Landing UX](021-post-login-landing-ux.md)
  - [ADR-042 Bot Detection / CAPTCHA](042-bot-detection-captcha.md)
  - [§NFR-7 コンプライアンス](../requirements/proposal/nfr/07-compliance.md)

---

## Context

### 背景

本基盤の **UI 接点**（ログイン画面 / アカウント設定画面 / サービス選択画面 / Sorry / ユーザ管理画面）は、**規制業種顧客**（自治体 / 公的機関 / 大企業）にとって**アクセシビリティ準拠**が必須要件となる。今まで個別 UI ごとに暗黙的に「Keycloak Theme は標準で AA 相当」と仮定していたが、**統一的な準拠基準と検証プロセス**が未定義だった。

### 国内法 / ガイドラインの現在地

| 規制 | 状況 |
|---|---|
| **障害者差別解消法**（2024/4 民間事業者にも合理的配慮が義務化）| Web アクセシビリティは合理的配慮の重要要素 |
| **JIS X 8341-3:2016** | 国内 Web アクセシビリティ JIS、WCAG 2.0 と整合 |
| **総務省 みんなの公共サイト運用ガイドライン**（2024 改訂版）| 公的機関は AA 必須、民間は AA 推奨 |
| **WCAG 2.2**（2023/10 W3C 勧告）| 最新版、2.1 の 9 達成基準を追加 |
| **EAA**（European Accessibility Act、2025/6 施行）| EU 市場アクセス時、AA 必須 |
| **米国 Section 508 / ADA**（2024 DOJ 規則）| 政府 / 公共サービス AA 必須 |

### 認証基盤としてアクセシビリティが特に重要な理由

| 理由 | 詳細 |
|---|---|
| **入り口** | ログイン画面は全アプリの入口、ここで詰まると全機能利用不可 |
| **代替手段なし** | 「電話で代行」が通用しない（パスワードを口頭で伝えられない）|
| **MFA 工程** | TOTP / WebAuthn は視覚 / 操作性に依存、配慮必要 |
| **CAPTCHA**（[ADR-042](042-bot-detection-captcha.md)）| 視覚 / 聴覚障害者への配慮必須 |
| **エラーメッセージ** | スクリーンリーダーで読み上げ可能であるべき |
| **タイムアウト** | 操作に時間がかかる利用者向け延長機構が必須 |

### 業界用語の整理

| 用語 | 意味 |
|---|---|
| **WCAG 2.2**（Web Content Accessibility Guidelines）| W3C 標準、4 原則（知覚 / 操作 / 理解 / 堅牢）× 13 ガイドライン × 86 達成基準 |
| **適合レベル A / AA / AAA** | A = 最低限、AA = 業界標準、AAA = 最高（実現困難）|
| **JIS X 8341-3:2016** | 国内 JIS、WCAG 2.0 と等価、最新化は審議中 |
| **VPAT**（Voluntary Product Accessibility Template）| ベンダー側の適合性報告書、Section 508 / EN 301 549 用 |
| **ACR**（Accessibility Conformance Report）| VPAT の具体的アウトプット文書 |
| **ATAG**（Authoring Tool Accessibility Guidelines）| オーサリングツール向け、ユーザ管理画面 が該当 |
| **WAI-ARIA** | リッチ Web アプリのアクセシビリティ強化属性 |
| **スクリーンリーダー** | NVDA / JAWS / VoiceOver / TalkBack |

---

## Decision

### 採用方針

**WCAG 2.2 Level AA + JIS X 8341-3:2016 AA 準拠**を全 UI 接点で必須。ユーザ管理画面 は ATAG 2.0 も追加準拠。VPAT 2.5 形式の ACR を Trust Center で公開（[ADR-036](036-customer-audit-support.md) 連動）。

| UI | 準拠目標 | 検証方式 | ACR 公開 |
|---|---|---|---|
| **Keycloak ログイン画面**（Theme カスタム）| WCAG 2.2 AA + JIS X 8341-3:2016 AA | axe-core + 手動 + 当事者テスト | ✅ |
| **アカウント設定画面** | 同上 | 同上 | ✅ |
| **サービス選択画面 SPA**（ADR-021）| 同上 | 同上 | ✅ |
| **エラー / 案内画面 SPA** | 同上 | 同上 | ✅ |
| **ユーザ管理画面**（ADR-038）| WCAG 2.2 AA + **ATAG 2.0 AA** | 同上 + ATAG 専用テスト | ✅ |
| **Trust Center / Customer Portal**（ADR-036）| WCAG 2.2 AA | axe-core + 手動 | ✅ |
| **エラーページ / Maintenance** | WCAG 2.2 AA | axe-core | △ |

### 主要判断

| 判断ポイント | 採用 | 理由 |
|---|---|---|
| **適合レベル** | **AA**（AAA は非現実的）| 業界標準、JIS X 8341-3 / Section 508 / EAA 全準拠 |
| **検証ツール** | **axe-core**（自動）+ **NVDA / VoiceOver**（手動）+ **当事者テスト** | 自動のみでは 30-40% しか検出できない |
| **CI/CD 統合** | **PR 時 axe-core 自動チェック**、AA 違反は merge ブロック | 退行防止 |
| **当事者テスト頻度** | **年 1 回**、Major UI 改修時は追加 | コスト vs 品質バランス |
| **ACR 公開** | **VPAT 2.5 形式**で半年ごと更新 | Section 508 / EN 301 549 監査対応 |
| **CAPTCHA 配慮** | Cloudflare Turnstile（ADR-042）の **Accessibility 機能を必ず有効化**、Audio CAPTCHA 提供 | 視覚障害者対応 |

---

## A. WCAG 2.2 AA 達成基準（86 基準のうち AA 関連 50 基準）

### A.1 4 原則のスタンス

| 原則 | 内容 | 本基盤での重要度 |
|---|---|---|
| **1. 知覚可能（Perceivable）** | テキスト代替 / 字幕 / 適切なコントラスト | ★★★ |
| **2. 操作可能（Operable）** | キーボード操作 / 十分な時間 / 発作回避 / ナビゲーション | ★★★ |
| **3. 理解可能（Understandable）** | 読みやすさ / 予測可能性 / 入力支援 | ★★★ |
| **4. 堅牢（Robust）** | 支援技術との互換性、WAI-ARIA 適切な使用 | ★★ |

### A.2 認証 UI で特に重要な達成基準

| 基準 | レベル | 本基盤での実装 |
|---|---|---|
| **1.1.1 非テキストコンテンツ** | A | ロゴ / アイコンに alt 属性、装飾画像は `alt=""` |
| **1.3.1 情報及び関係性** | A | フォームラベルと input の関連付け（`for`/`id`）、エラーメッセージの `aria-describedby` |
| **1.3.5 入力目的の特定**（WCAG 2.1 新規）| AA | `autocomplete="username"` / `autocomplete="current-password"` |
| **1.4.3 コントラスト（最低限）** | AA | 通常テキスト 4.5:1、大きいテキスト 3:1 |
| **1.4.11 非テキストのコントラスト**（WCAG 2.1）| AA | UI コンポーネント 3:1 以上 |
| **1.4.13 ホバー時 / フォーカス時のコンテンツ**（WCAG 2.1）| AA | Tooltip 等は dismissible / hoverable / persistent |
| **2.1.1 キーボード** | A | 全機能キーボード操作可能、Tab フォーカス順序明確 |
| **2.1.4 文字キーショートカット**（WCAG 2.1）| A | 単一文字ショートカットは無効化 or カスタマイズ可能 |
| **2.2.1 タイミング調整可能** | A | セッションタイムアウト前に警告 + 延長ボタン |
| **2.2.2 一時停止、停止、非表示** | A | 自動更新コンテンツ（Sorry 自動 redirect 等）に停止機構 |
| **2.4.3 フォーカス順序** | A | Tab 順序 = 視覚的順序 |
| **2.4.7 フォーカスの可視化** | AA | フォーカスリング常時表示、3:1 コントラスト |
| **2.4.11 フォーカスの最低限の到達**（WCAG 2.2 新規）| AA | フォーカス対象が他要素で完全に隠れない |
| **2.4.12 フォーカスの遮蔽なし**（WCAG 2.2 AAA、推奨対応） | AAA | 推奨のみ |
| **2.5.7 ドラッグ操作**（WCAG 2.2 新規）| AA | ドラッグの代替操作（クリック / タップ）提供 |
| **2.5.8 ターゲットのサイズ**（WCAG 2.2 新規）| AA | クリック領域 24×24 CSS pixel 以上 |
| **3.1.1 ページの言語** | A | `<html lang="ja">` 必須 |
| **3.2.4 一貫した識別性** | AA | 同機能ボタンは全画面で同一ラベル |
| **3.3.1 エラーの特定** | A | エラー箇所をテキスト + 視覚 + スクリーンリーダーで通知 |
| **3.3.7 冗長な入力**（WCAG 2.2 新規）| A | 同セッション内で同情報を再入力させない |
| **3.3.8 アクセシブルな認証（最低限）**（WCAG 2.2 新規）| AA | パスワード以外の認知タスクを必須化しない（CAPTCHA 例外あり）|
| **4.1.2 名前（name）、役割（role）、値（value）** | A | カスタムコンポーネントに WAI-ARIA |
| **4.1.3 ステータスメッセージ**（WCAG 2.1）| AA | `aria-live` で動的メッセージを支援技術に通知 |

### A.3 WCAG 2.2 新規 9 基準の対応

WCAG 2.2 で追加された 9 基準のうち本基盤に影響するもの:

| 基準 | レベル | 本基盤での対応 |
|---|---|---|
| **2.4.11 フォーカスの最低限の到達** | AA | フォーカスリング確認、固定ヘッダの z-index 配慮 |
| **2.4.12 フォーカスの遮蔽なし** | AAA | 推奨対応 |
| **2.4.13 フォーカスの外観** | AAA | 推奨対応（フォーカスリング 3:1） |
| **2.5.7 ドラッグ操作** | AA | スライダー等は + / - ボタンも提供 |
| **2.5.8 ターゲットのサイズ（最小）** | AA | ボタン 24×24px 以上、間隔考慮 |
| **3.2.6 一貫したヘルプ** | A | ヘルプリンクは全画面同位置 |
| **3.3.7 冗長な入力** | A | 「前画面の値を保持」「再入力不要」|
| **3.3.8 アクセシブルな認証（最低限）** | AA | CAPTCHA 以外で認知タスクを課さない |
| **3.3.9 アクセシブルな認証（強化）** | AAA | 推奨対応 |

---

## B. Keycloak Theme アクセシビリティ実装

### B.1 Theme 構成

```
themes/custom-accessible/
├── login/
│   ├── login.ftl              ← WCAG AA 準拠ログイン画面
│   ├── login-reset-password.ftl
│   ├── login-update-password.ftl
│   ├── login-otp.ftl          ← OTP 入力、autocomplete="one-time-code"
│   ├── webauthn-authenticate.ftl
│   ├── resources/
│   │   ├── css/accessible.css ← コントラスト / フォーカススタイル
│   │   ├── js/a11y-helpers.js ← aria-live announcer
│   │   └── img/               ← alt 属性必須
│   └── messages/
│       ├── messages_ja.properties
│       └── messages_en.properties
└── account/
    └── ...（アカウント設定画面、PatternFly 4 ベース）
```

### B.2 ログイン画面 FTL 例（抜粋）

```html
<!DOCTYPE html>
<html lang="${locale.currentLanguageTag}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${msg("loginTitle", realm.displayName!realm.name)}</title>
  <!-- WCAG 1.4.3 コントラスト確保された CSS -->
  <link rel="stylesheet" href="${url.resourcesPath}/css/accessible.css">
</head>
<body>
  <!-- WCAG 2.4.1 スキップリンク -->
  <a href="#main" class="skip-link">${msg("skipToMain")}</a>

  <main id="main" role="main">
    <h1>${msg("loginTitle", realm.displayName!realm.name)}</h1>

    <!-- WCAG 3.3.1 エラー領域、aria-live で動的通知 -->
    <div id="error-message" role="alert" aria-live="assertive" aria-atomic="true">
      <#if message?has_content>
        <p class="error">${kcSanitize(message.summary)?no_esc}</p>
      </#if>
    </div>

    <form id="kc-form-login" action="${url.loginAction}" method="post"
          aria-labelledby="kc-form-login-heading">
      <h2 id="kc-form-login-heading" class="sr-only">${msg("loginAccountTitle")}</h2>

      <!-- WCAG 1.3.5 autocomplete + 1.3.1 関連付け -->
      <div class="form-group">
        <label for="username">${msg("username")}</label>
        <input id="username" name="username" type="text"
               autocomplete="username"
               aria-required="true"
               aria-invalid="${(messagesPerField.existsError('username'))?string('true','false')}"
               aria-describedby="username-error"
               required>
        <span id="username-error" class="error-text" role="alert">
          <#if messagesPerField.existsError('username')>
            ${kcSanitize(messagesPerField.get('username'))?no_esc}
          </#if>
        </span>
      </div>

      <div class="form-group">
        <label for="password">${msg("password")}</label>
        <input id="password" name="password" type="password"
               autocomplete="current-password"
               aria-required="true"
               aria-describedby="password-error"
               required>
        <span id="password-error" class="error-text" role="alert">
          <#if messagesPerField.existsError('password')>
            ${kcSanitize(messagesPerField.get('password'))?no_esc}
          </#if>
        </span>
      </div>

      <!-- WCAG 2.5.8 ターゲットサイズ 24×24px 以上、min-height: 44px が推奨 -->
      <button type="submit" class="btn-primary"
              style="min-height:44px;min-width:44px;">
        ${msg("doLogIn")}
      </button>

      <!-- WCAG 3.2.6 一貫したヘルプ -->
      <a href="${url.loginResetCredentialsUrl}" class="help-link">
        ${msg("doForgotPassword")}
      </a>
    </form>
  </main>

  <!-- Cloudflare Turnstile：Accessibility 対応必須 -->
  <div class="cf-turnstile"
       data-sitekey="${properties.turnstileSiteKey}"
       data-size="invisible"
       data-tabindex="0"
       data-language="ja">
  </div>
</body>
</html>
```

### B.3 CSS：コントラスト / フォーカススタイル

```css
/* WCAG 1.4.3 コントラスト 4.5:1 以上 */
body {
  color: #1a1a1a;            /* 背景 #fff に対し 19.6:1 */
  background: #ffffff;
}
.error-text {
  color: #b00020;            /* 背景 #fff に対し 6.55:1 */
}

/* WCAG 2.4.7 フォーカス可視化、2.4.11 最低限の到達 */
*:focus-visible {
  outline: 3px solid #0066cc; /* 背景 #fff に対し 4.55:1 */
  outline-offset: 2px;
}

/* WCAG 2.5.8 ターゲットサイズ */
button, a.help-link, input[type="checkbox"] {
  min-height: 44px;
  min-width: 44px;
}

/* スキップリンク */
.skip-link {
  position: absolute;
  left: -9999px;
  z-index: 999;
}
.skip-link:focus {
  left: 8px;
  top: 8px;
  background: #fff;
  padding: 8px;
}

/* スクリーンリーダー専用 */
.sr-only {
  position: absolute;
  width: 1px; height: 1px;
  padding: 0; margin: -1px;
  overflow: hidden;
  clip: rect(0,0,0,0);
  border: 0;
}
```

---

## C. 検証プロセス

### C.1 3 層検証

| 層 | ツール / 手法 | 頻度 | 検出率 |
|---|---|---|---|
| **L1 自動**（CI/CD）| **axe-core**（Playwright 統合）+ **Lighthouse**（Chrome）| PR ごと | 30-40% |
| **L2 手動**（社内）| **NVDA**（Windows）+ **VoiceOver**（macOS / iOS）+ **TalkBack**（Android）| 月 1 + Major 改修時 | +30% |
| **L3 当事者テスト** | アクセシビリティ専門会社 + 視覚 / 上肢障害 / 認知障害の当事者 | 年 1 + Major 改修時 | +30%、合計 90-95% |

### C.2 CI/CD 統合例（GitHub Actions）

```yaml
# .github/workflows/a11y.yml
name: Accessibility
on: [pull_request]

jobs:
  axe-core:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: npm ci
      - name: Build SPA
        run: npm run build
      - name: Run axe-core via Playwright
        run: npx playwright test tests/a11y/
        # WCAG 2.2 AA violation で exit 1（merge ブロック）
      - name: Upload axe-core report
        uses: actions/upload-artifact@v4
        with:
          name: a11y-report
          path: a11y-report/
```

### C.3 当事者テストの実施

| 項目 | 内容 |
|---|---|
| **委託先** | アクセシビリティ専門会社（インフォアクシア / ミツエーリンクス等）|
| **対象 UI** | ログイン / アカウント設定画面 / サービス選択画面 / Sorry / ユーザ管理画面 |
| **当事者** | 視覚障害（スクリーンリーダー利用 / ロービジョン）/ 上肢障害（キーボードのみ）/ 認知障害 |
| **タスク** | 各 UI の代表的なユースケース 5-10 個 |
| **アウトプット** | レポート + 動画記録 + 改善提案 |
| **費用** | 〜200 万円 / 年 |

---

## D. ACR（Accessibility Conformance Report）

### D.1 VPAT 2.5 形式での ACR 作成

VPAT 2.5（W3C / ITI 提供）には以下 4 タブ:

| Tab | 規格 | 採用 |
|---|---|---|
| WCAG | WCAG 2.2 | ✅ |
| Revised Section 508 | 米国連邦調達基準 | △（米国顧客時のみ）|
| EN 301 549 | 欧州 EAA 基準 | ✅（EAA 対応）|
| Combined | 全規格統合 | ✅ |

### D.2 ACR 公開

[ADR-036 Customer Audit Support](036-customer-audit-support.md) Trust Center に以下を公開:

| ドキュメント | 形式 | 更新頻度 |
|---|---|---|
| ACR（VPAT 2.5）| PDF + Web | 半年ごと |
| 当事者テストレポートサマリ | PDF | 年 1 回 |
| Accessibility Statement | HTML | 半年ごと |
| 既知の問題 / 改善ロードマップ | HTML | 四半期 |

---

## E. 規制対応マッピング

| 規制 / ガイドライン | 本 ADR での対応 |
|---|---|
| **障害者差別解消法（合理的配慮義務）** | WCAG 2.2 AA + 申出時の代替手段提供（電話サポート等）|
| **JIS X 8341-3:2016 AA** | WCAG 2.2 AA はこれを完全に包含 |
| **総務省 みんなの公共サイト運用ガイドライン** | 公的機関顧客は AA、ACR を Trust Center で公開 |
| **EAA（EU Accessibility Act 2025）** | EN 301 549 ACR で対応 |
| **米国 ADA / Section 508**（DOJ 2024）| VPAT 2.5 で対応 |
| **EAA / WCAG 連動の SOC 2 監査** | ACR を Trust Center 経由で監査人に開示 |

---

## F. CAPTCHA / Bot Defense との整合（ADR-042 連動）

[ADR-042 Bot Detection / CAPTCHA](042-bot-detection-captcha.md) の Cloudflare Turnstile は以下のアクセシビリティ機能を**必ず有効化**:

| 機能 | 設定 | WCAG 対応 |
|---|---|---|
| Audio CAPTCHA フォールバック | Turnstile 標準 | 1.1.1 / 1.4.2 |
| キーボード操作 | 自動 | 2.1.1 |
| `aria-label` | 自動 | 4.1.2 |
| 多言語 | `data-language="ja"` | 3.1.1 |
| 高コントラスト対応 | Turnstile 自動 | 1.4.3 |

→ WCAG 3.3.8 「アクセシブルな認証」基準準拠。

---

## G. コスト試算

### G.1 初期 + 年次

| 項目 | コスト |
|---|---|
| **Phase 0 初期**（Theme 開発 + axe-core CI 統合）| 〜500 万円（3 ヶ月）|
| **当事者テスト**（年 1 + Major 改修時）| 〜200 万円 / 年 |
| **ACR 作成 / 半年更新** | 〜100 万円 / 年 |
| **axe-core / Playwright ツール** | OSS、無料 |
| **アクセシビリティ専任エンジニア**（0.2 FTE）| 〜200 万円 / 年 |
| **年次合計** | **〜500 万円 / 年** |

### G.2 ROI（規制業種顧客対応）

- 自治体 / 公的機関契約：ACR 提示で受注可能性大幅向上
- 障害者差別解消法 違反訴訟リスク回避：1 件あたり 数千万円〜
- EAA 違反罰金回避（EU 顧客時）：年商の 2-4%

---

## H. 代替案検討

| 案 | 評価 | 採否 |
|---|---|---|
| **A. WCAG 2.0 A のみ準拠** | 旧基準、業界標準未達 | ❌ |
| **B. WCAG 2.2 AA + JIS 8341-3 + ACR 公開**（本 ADR）| 業界標準 + 規制対応 | ✅ 採用 |
| **C. WCAG 2.2 AAA 全準拠** | 非現実的（一部基準は技術的に困難）| ❌ |
| **D. 自動ツールのみで検証** | 30-40% しか検出できない | ❌ |
| **E. 当事者テストを実施しない** | 認知障害 / 視覚障害の本物の課題を見逃す | ❌ |
| **F. アクセシビリティ専門会社に丸投げ** | 内製ノウハウが蓄積しない | △ |

---

## Consequences

### Positive

- **規制業種顧客（自治体 / 公的機関 / 大企業）の受注機会拡大**
- **障害者差別解消法 合理的配慮義務**を技術的に充足
- **EAA / Section 508**（海外展開時）対応
- **ACR 公開**で顧客監査・契約交渉が円滑化
- 認証エンドポイントは「入り口」、ここの優しさは全アプリ体験を底上げ

### Negative

- **初期 500 万円 + 年 500 万円のコスト**
- Keycloak Theme カスタム開発の維持負荷
- WCAG 2.2 新基準への追従コスト（基準アップデートごとに改修）
- 当事者テスト調整の運用負荷

### Neutral

- AAA は推奨に留め、必須としない
- Mobile アプリ（ネイティブ）の Accessibility は別 ADR

### 我々のスタンス

| 基本方針の柱 | Accessibility での実現 |
|---|---|
| **絶対安全** | 認証アクセスを誰も排除しない（全員が安全に認証できる）|
| **どんなアプリでも** | Keycloak Theme 統一で全アプリの入り口が一貫 AA |
| **効率よく認証** | WCAG 3.3.7 / 3.3.8 で冗長入力排除、認証摩擦最小化 |
| **運用負荷・コスト最小** | OSS ツール（axe-core / Playwright）中心、商用ツール不要 |

---

## 参考資料

- [WCAG 2.2 W3C 勧告（2023/10）](https://www.w3.org/TR/WCAG22/)
- [JIS X 8341-3:2016 公式](https://www.jisc.go.jp/)
- [総務省 みんなの公共サイト運用ガイドライン 2024](https://www.soumu.go.jp/main_sosiki/joho_tsusin/b_free/guideline.html)
- [WAIC（ウェブアクセシビリティ基盤委員会）](https://waic.jp/)
- [VPAT 2.5 公式テンプレート](https://www.itic.org/policy/accessibility/vpat)
- [axe-core](https://github.com/dequelabs/axe-core)
- [Keycloak Themes — Customization](https://www.keycloak.org/docs/latest/server_development/#_themes)
- [EAA（European Accessibility Act）](https://ec.europa.eu/social/main.jsp?catId=1202)
- [WebAIM Survey 2024](https://webaim.org/projects/screenreadersurvey10/) — スクリーンリーダー利用実態
- [障害者差別解消法 2024 改正対応 内閣府](https://www8.cao.go.jp/shougai/suishin/sabekai.html)
