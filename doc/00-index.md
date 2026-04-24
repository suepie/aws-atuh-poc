# ドキュメント一覧

**最終更新**: 2026-04-21（Phase 8 完了、要件定義フェーズ開始）

---

## 構成

```
doc/
├── common/          # 全体共通（構成図・比較・スコープ・削除手順）
├── cognito/         # Cognito固有（認証フロー・構築手順）
├── keycloak/        # Keycloak固有（認証フロー・構築手順・検証シナリオ）
├── adr/             # Architecture Decision Records（001-009）
├── reference/       # 参考情報（認証基礎 / Cognito / Keycloak）
├── requirements/    # 要件定義（PoC総括・ヒアリング・要件定義書）
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
| 010 | Keycloak を Private Subnet + VPC Endpoint 構成へ移行 |
| 011 | 認証基盤前段ネットワーク設計（HTTPS / カスタムドメイン / WAF / CloudFront）統合判断（Proposed） |
| 012 | VPC Lambda Authorizer + Internal ALB による JWKS プライベート化（Accepted） |
| 013 | CloudFront + WAF による IP 制限の置き換え戦略（Proposed） |
| 014 | 共有認証基盤が対応する認証パターンの範囲（Proposed） |

## 参考情報（[reference/](reference/00-index.md)）

| カテゴリ | ドキュメント数 |
|---------|:------------:|
| 認証基礎・SSO | 3 |
| Cognito | 3 |
| Keycloak | 3 |

## 要件定義（[requirements/](requirements/00-index.md)）

| ドキュメント | 内容 |
|------------|------|
| [poc-summary-evaluation.md](requirements/poc-summary-evaluation.md) | PoC総括評価：成果・ドキュメント評価・不足箇所分析 |
| [requirements-hearing-strategy.md](requirements/requirements-hearing-strategy.md) | ヒアリング戦略：確認事項・ステークホルダー・スケジュール |
| [requirements-document-structure.md](requirements/requirements-document-structure.md) | 要件定義資料の構成案・作成順序 |

## 過去の検討（[old/](old/)）

`doc/old/` に過去の検討成果物がある（読み取り専用）。
