# Keycloak ドキュメント（Phase 6-7）

Keycloak を使った認証基盤の設計・フロー・構築手順・検証結果。

## 設計・フロー

| ドキュメント | 内容 |
|------------|------|
| [auth-flow.md](auth-flow.md) | 認証フロー設計（ローカル+MFA / Auth0 Brokering / SSO） |
| [setup-guide.md](setup-guide.md) | 構築手順書（ECS + RDS + Realm + MFA + Auth0） |

## 検証シナリオ

| ドキュメント | 内容 |
|------------|------|
| [test-scenarios.md](test-scenarios.md) | 基本動作・障害・DR検証 + Cognito対比マトリクス |
| [mfa-sso-auth0-scenarios.md](mfa-sso-auth0-scenarios.md) | MFA・SSO・Auth0連携検証 + ノウハウ集 |
