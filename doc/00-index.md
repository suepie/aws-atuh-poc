# ドキュメント一覧

**最終更新**: 2026-03-30（Phase 7 完了、全環境削除済み）

---

## 構成

```
doc/
├── common/          # 全体共通（構成図・比較・スコープ・削除手順）
├── cognito/         # Cognito固有（認証フロー・構築手順）
├── keycloak/        # Keycloak固有（認証フロー・構築手順・検証シナリオ）
├── adr/             # Architecture Decision Records（001-009）
├── reference/       # 参考情報（認証基礎 / Cognito / Keycloak）
└── old/             # 過去の検討ドキュメント（読み取り専用）
```

## 共通（[common/](common/00-index.md)）

| ドキュメント | 内容 |
|------------|------|
| [architecture.md](common/architecture.md) | 全体アーキテクチャ（Cognito + Keycloak構成図） |
| [poc-scope.md](common/poc-scope.md) | PoC範囲・制約・技術スタック |
| [poc-results.md](common/poc-results.md) | 検証結果サマリー（Phase 1-7）・Cognito vs Keycloak比較 |
| [destroy-guide.md](common/destroy-guide.md) | 環境削除・残存リソース確認手順 |

## Cognito（[cognito/](cognito/00-index.md)）

| ドキュメント | 内容 |
|------------|------|
| [auth-flow.md](cognito/auth-flow.md) | 認証フロー（5パターン + API認可 + DR + ログアウト） |
| [setup-guide.md](cognito/setup-guide.md) | 構築手順書（Phase 1-5） |

## Keycloak（[keycloak/](keycloak/00-index.md)）

| ドキュメント | 内容 |
|------------|------|
| [auth-flow.md](keycloak/auth-flow.md) | 認証フロー（ローカル+MFA / Auth0 Brokering / SSO） |
| [setup-guide.md](keycloak/setup-guide.md) | 構築手順書（Phase 6-7） |
| [test-scenarios.md](keycloak/test-scenarios.md) | 検証シナリオ（基本動作・障害・DR）+ Cognito対比 |
| [mfa-sso-auth0-scenarios.md](keycloak/mfa-sso-auth0-scenarios.md) | MFA・SSO・Auth0連携検証 + ノウハウ集 |

## ADR（[adr/](adr/00-index.md)）

| ADR | タイトル |
|-----|---------|
| 001-007 | Cognito構成・Lambda Authorizer・oidc-client-ts・DR等 |
| 008 | PoCでKeycloak start-devモードを使用 |
| 009 | MFA責任はパスワード管理側に帰属させる |

## 参考情報（[reference/](reference/00-index.md)）

| カテゴリ | ドキュメント数 |
|---------|:------------:|
| 認証基礎・SSO | 3 |
| Cognito | 3 |
| Keycloak | 3 |

## 過去の検討（[old/](old/)）

`doc/old/` に過去の検討成果物がある（読み取り専用）。
