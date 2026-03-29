# 設計ドキュメント一覧

最新の設計ドキュメントを管理する。PoCの進行に合わせて更新する。

**最終更新**: 2026-03-29（Phase 7 完了、全環境削除済み）

## 設計

| ドキュメント | 内容 | ステータス |
|------------|------|----------|
| [architecture.md](architecture.md) | 全体アーキテクチャ（Cognito + Keycloak構成図） | Phase 6 反映済 |
| [auth-flow.md](auth-flow.md) | 認証フロー設計（Cognito 5パターン + Keycloak 3パターン） | Phase 7 反映済 |
| [poc-scope.md](poc-scope.md) | PoC範囲・制約・技術スタック・段階的検証プラン | Phase 7 反映済 |
| [poc-results.md](poc-results.md) | 検証結果サマリー（Phase 1〜7） | Phase 7 反映済 |

## 手順

| ドキュメント | 内容 | ステータス |
|------------|------|----------|
| [setup-guide.md](setup-guide.md) | 構築・削除・確認手順（Phase 1〜7 全手順） | Phase 7 反映済 |

## 検証シナリオ

| ドキュメント | 内容 | ステータス |
|------------|------|----------|
| [keycloak-test-scenarios.md](keycloak-test-scenarios.md) | Phase 6: Keycloak基本動作・障害・DR・Cognito対比 | 検証完了 |
| [phase7-mfa-sso-auth0-scenarios.md](phase7-mfa-sso-auth0-scenarios.md) | Phase 7: MFA・SSO・Auth0連携・ノウハウ集 | 検証完了 |
