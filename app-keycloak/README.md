# app-keycloak

**ステータス**: 参照用に維持（**新規開発は `app/` 統合版を使ってください**）

## 経緯

Phase 6 ～ Phase 9 で Keycloak 単体検証用に作成された SPA。
Phase 9 完了後（2026-04 以降）、`app/` に Keycloak サポートが統合されたため、
新規の検証は `app/` (port 5173) で行うのが推奨。

本 SPA は以下の理由で**削除せず残置**:

- Phase 6/7 当時の検証セットアップを再現したい場合の参照
- ミニマルな Keycloak-only SPA としての参考実装
- ドキュメントからの過去リンク維持

## 起動

```bash
make app-kc-dev   # http://localhost:5174
```

## 設定

`.env`（`.env.example` を参考に作成）:

```env
VITE_KEYCLOAK_AUTHORITY=http://<keycloak-alb>/realms/auth-poc
VITE_KEYCLOAK_CLIENT_ID=auth-poc-spa
VITE_REDIRECT_URI=http://localhost:5174/callback
VITE_POST_LOGOUT_URI=http://localhost:5174/

VITE_API_ENDPOINT=https://<api-gateway>/prod
```

## 関連

- `app/` — Cognito + Keycloak 統合版（推奨）
- `app-sso-peer/` — Keycloak の cross-client SSO 検証用ピア SPA（旧 app-keycloak-2）
