# 共通ドキュメント

Cognito / Keycloak 横断の全体設計・比較・管理。

| ドキュメント | 内容 |
|------------|------|
| [architecture.md](architecture.md) | 全体アーキテクチャ（Cognito + Keycloak構成図・ディレクトリ） |
| [poc-scope.md](poc-scope.md) | PoC範囲・制約・技術スタック・Phase 1-9 |
| [poc-results.md](poc-results.md) | 検証結果サマリー・Cognito vs Keycloak比較 |
| [claim-mapping-authz-scenario.md](claim-mapping-authz-scenario.md) | Phase 8: クレームマッピング・認可シナリオ（経費精算SaaS） |
| [auth0-setup-claims.md](auth0-setup-claims.md) | Auth0 カスタムクレーム設定ガイド（Action / app_metadata） |
| [authz-architecture-design.md](authz-architecture-design.md) | 認可アーキテクチャ設計：バックエンド非依存・トークンキャッシュ・ベスト���ラクティス |
| [identity-broker-multi-idp.md](identity-broker-multi-idp.md) | Identity Broker パターン：マルチ顧客IdP対応設計 |
| [jwks-public-exposure.md](jwks-public-exposure.md) | JWKSエンドポイント公開の設計判断：なぜ公開が必要で安全なのか |
| [keycloak-network-architecture.md](keycloak-network-architecture.md) | Keycloak ネットワーク構成（実装実態）：IP 制限マトリクス・本番移行要件・CloudFront+WAF 完全形 |
| [auth-patterns.md](auth-patterns.md) | 認証パターン総覧（SPA / SSR / M2M / Token Exchange / SAML 等）と Cognito vs Keycloak 対応詳細 |
| [destroy-guide.md](destroy-guide.md) | 環境削除・残存リソース確認手順 |
| [devcontainer-corporate-cert-setup.md](devcontainer-corporate-cert-setup.md) | Dev Container に企業プロキシ(Netskope等)のルートCA証明書を組み込む手順（日英併記） |
| [claude-code-communication-flow.md](claude-code-communication-flow.md) | Claude Code (Dev Container) の通信フロー・OAuth 認証・Netskope 対策の関係（日英併記） |
