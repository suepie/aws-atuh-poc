# ADR (Architecture Decision Records) 一覧

アーキテクチャ上の意思決定を記録する。

| ADR | タイトル | ステータス | 日付 |
|-----|---------|----------|------|
| [001](001-cognito-hybrid-for-poc.md) | PoC第1パターンとしてCognitoハイブリッド構成を採用 | Accepted | 2026-03-17 |
| [002](002-lambda-authorizer.md) | 認可方式としてLambda Authorizerを採用 | Accepted | 2026-03-17 |
| [003](003-oidc-client-ts.md) | 認証ライブラリとしてoidc-client-tsを採用 | Accepted | 2026-03-17 |
| [004](004-single-account-poc.md) | 1アカウント2 User Poolでマルチアカウント構成を擬似再現 | Accepted | 2026-03-17 |
| [005](005-user-pool-not-identity-pool.md) | 共通認証基盤にUser Poolを使用（Identity Poolではない） | Accepted | 2026-03-17 |
| [006](006-cognito-vs-keycloak-cost-breakeven.md) | Cognito vs Keycloak コスト損益分岐点の分析 | Proposed | 2026-03-17 |
| [007](007-osaka-auth0-idp-limitation.md) | 大阪リージョンでAuth0 OIDC IdP接続不可の記録 | Accepted | 2026-03-18 |
| [008](008-keycloak-start-dev-for-poc.md) | PoCでKeycloak start-devモードを使用 | Accepted | 2026-03-25 |
| [009](009-mfa-responsibility-by-idp.md) | MFA責任はパスワード管理側に帰属させる | Accepted | 2026-03-28 |
| [010](010-keycloak-private-subnet-vpc-endpoints.md) | Keycloak 環境を Private Subnet + VPC Endpoint 構成へ移行 | Accepted | 2026-04-21 |
| [011](011-auth-frontend-network-design.md) | 認証基盤前段ネットワーク設計（HTTPS / カスタムドメイン / WAF / CloudFront）の統合判断 | Proposed | 2026-04-21 |
| [012](012-vpc-lambda-authorizer-internal-jwks.md) | VPC Lambda Authorizer + Internal ALB による JWKS プライベート化 | Accepted | 2026-04-23 |
| [013](013-cloudfront-waf-ip-restriction.md) | CloudFront + WAF による IP 制限の置き換え戦略 | Proposed | 2026-04-24 |
| [014](014-auth-patterns-scope.md) | 共有認証基盤が対応する認証パターンの範囲 | Proposed | 2026-04-24 |
| [015](015-rhbk-validation-deferred.md) | PoC では RHBK 検証を実施せず本番設計フェーズへ先送り | Proposed | 2026-04-24 |
