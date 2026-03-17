# Cognito App Client の概念と設計パターン

**作成日**: 2026-03-17

---

## App Client とは

App Client は「Cognito User Poolに接続するアプリケーションごとの接続設定」。
DBの接続ユーザーに相当する概念。

## App Clientに含まれる設定

| 設定項目 | 説明 | 例 |
|---------|------|-----|
| Client ID | アプリがCognitoに接続する際のID | `abc123xxxx` |
| Client Secret | サーバーサイドアプリ用の秘密鍵 | SPAでは不要 |
| 許可するOAuth Flow | Authorization Code, Implicit, Client Credentials | Auth Code + PKCE |
| 許可するスコープ | openid, profile, email, カスタム | `openid profile email` |
| コールバックURL | 認証後のリダイレクト先 | `https://app.example.com/callback` |
| サインアウトURL | ログアウト後のリダイレクト先 | `https://app.example.com/` |
| トークン有効期限 | ID/Access/Refreshの各有効期限 | ID: 1h, Refresh: 30d |
| 読み取り可能属性 | 取得できるユーザー属性 | email, name, custom:tenant_id |

## 設計パターン（粒度の選択）

### パターンA: システムごとに1つ
```
expense-app → SPA/モバイル/バックエンド全部で共有
```
- メリット: シンプル
- デメリット: フロー別のセキュリティ設定ができない

### パターンB: システム × アプリ種別（推奨）
```
expense-spa, expense-backend, expense-mobile
```
- メリット: フローごとに適切なセキュリティ設定
- デメリット: App Client数が増える

### パターンC: テナントごと
```
expense-spa-tenantA, expense-spa-tenantB
```
- 不要: テナント分離はトークンのクレーム（tenant_id）で行う

## アプリ種別ごとの設定

| アプリ種別 | OAuth Flow | Secret | PKCE |
|-----------|-----------|--------|------|
| SPA | Authorization Code | なし | 必須 |
| サーバーサイドWeb | Authorization Code | あり | 任意 |
| モバイル | Authorization Code | なし | 必須 |
| サーバー間通信 | Client Credentials | あり | 不要 |

## 運用上の注意

- App Client自体は無料（課金はMAU単位）
- コールバックURLはワイルドカード禁止、HTTPS必須（localhostは例外）
- Client Secretの漏洩 = そのApp Client経由の不正アクセスリスク
- App Clientごとにトークンのaudが異なる → Lambda Authorizerでaud検証に使用
