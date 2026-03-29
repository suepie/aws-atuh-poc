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
