# app-sso-peer (旧 app-keycloak-2)

**用途**: SSO 検証用の「ピア SPA」。`app` または `app-keycloak` とは**別のポート・別のClient ID**で起動し、**同一 IdP Realm 内のクライアント間 SSO** を確認する。

## 検証シナリオ

1. ブラウザで `app` (5173) または `app-keycloak` (5174) にアクセスし Keycloak にログイン
2. 同じブラウザで `app-sso-peer` (5175) を開く
3. **パスワード入力なしでログイン状態になれば** SSO 成功（Keycloak Realm 内のセッション共有）

## 起動

```bash
make app-sso-dev   # http://localhost:5175
```

## 設定

`.env`（`.env.example` を参考に作成）:

```env
# 既存の app-keycloak と同じ Realm を指定するが、
# Client ID は別のものを使う（例: auth-poc-spa-2）
VITE_KEYCLOAK_AUTHORITY=http://<keycloak-alb>/realms/auth-poc
VITE_KEYCLOAK_CLIENT_ID=auth-poc-spa-2
VITE_REDIRECT_URI=http://localhost:5175/callback
VITE_POST_LOGOUT_URI=http://localhost:5175/

VITE_API_ENDPOINT=https://<api-gateway>/prod
```

## 関連ドキュメント

- [doc/keycloak/mfa-sso-auth0-scenarios.md](../doc/keycloak/mfa-sso-auth0-scenarios.md) — Phase 7 で実施した SSO 検証手順
- [doc/common/poc-results.md](../doc/common/poc-results.md) — Phase 7 結果

## なぜ別の SPA が必要か

**Client 間 SSO** を検証するには物理的に別の SPA インスタンスが必要：

- **同じ SPA だけ**でリロード → 同一 Client・同一セッション → SSO の証明にならない
- **別ポートで別 Client の SPA** → Keycloak 側でクライアント間セッション共有が機能しているか確認できる

将来的には `.env` で IdP（Cognito or Keycloak）を切り替えて Cognito の cross-client SSO 検証にも転用可能な設計。

## 将来統合の検討

将来 Cognito の cross-client SSO 検証も対応する場合：

- `VITE_IDP_TYPE=cognito|keycloak` 環境変数で切替
- Cognito Central User Pool に 2 つ目の App Client を作成
- 同 SPA で Cognito SSO テストも可能になる
