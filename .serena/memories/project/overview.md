# AWS統合認証基盤PoC

## 目的
AWSを使った統合認証基盤の設計・検証。Cognito vs Keycloakを実際に構築して比較する。

## 完了した Phase（2026-03-25時点）
- Phase 1: 集約Cognito + Hosted UI + React SPA ✅
- Phase 2: Auth0 Free を外部IdPとしてフェデレーション認証 ✅
- Phase 3: Lambda Authorizer + API Gateway（JWT検証・認可・Context伝播）✅
- Phase 4: ローカルCognito追加、マルチissuer対応 ✅
- Phase 5: DR検証（大阪リージョン、マルチリージョンCognito）✅
- Phase 6: Keycloak構成（基本動作確認: ログイン・ログアウト）✅ ← 進行中

## Phase 7 完了（2026-03-28）
- MFA（TOTP）有効化 + ECS/RDS障害耐性確認
- SSO（複数Client、同一Realm内ネイティブ）
- Auth0 Identity Brokering
- Auth0 MFAスキップ（二重MFA回避）

## 技術スタック
- IaC: Terraform（東京Cognito + 大阪DR + 東京Keycloak）★3つの独立state
- Frontend: React + TypeScript + Vite + oidc-client-ts
  - app/ (Cognito版, port:5173)
  - app-keycloak/ (Keycloak版, port:5174) ★Phase 6追加
- Backend: Python 3.11 (Lambda) + PyJWT
- AWS Cognito: User Pool x3（東京集約・東京ローカル・大阪DR）
- AWS Keycloak: ECS Fargate + RDS PostgreSQL 16.13 + ALB ★Phase 6追加
  - Keycloak 26.0.8 (start-dev モード)
  - Realm: auth-poc

## AWSリソース構成
- 東京: 集約Cognito + ローカルCognito + API Gateway + Lambda x2
- 東京: ECS(Keycloak) + RDS(PostgreSQL) + ALB + ECR ★Phase 6
- 大阪: DR Cognito（Auth0 IdPはコンソール手動作成→terraform import）

## 主要な技術的知見
### Cognito
- Cognitoアクセストークンは`aud`ではなく`client_id`クレーム
- SSOセッションはIdP側に残る → 完全ログアウトには多段リダイレクト
- 大阪CognitoからAuth0の.well-known自動検出が失敗（Manual inputで回避）

### Keycloak
- 設定は3箇所（ビルド時/環境変数/DB）に分散 → 運用複雑性の主因
- start-devとstart --optimizedの違い（ビルド時設定の扱い）
- DB内のsslRequired設定でAdmin Consoleロックアウトのリスク
- ヘルスチェックはManagement Interface(port:9000)で提供
- ECSメモリ1GBでは不足 → 2GBに拡張
- KeycloakのログアウトはsignoutRedirect()のみで完結（Cognitoより簡単）
- realm_access.rolesでロール管理（Cognitoはcognito:groups）

## ドキュメント構成
- doc/design/ - 最新設計（architecture, auth-flow, poc-scope, poc-results, setup-guide, keycloak-test-scenarios）
- doc/adr/ - ADR 001-007
- doc/reference/ - 参考情報（SSO方式, KC DR/Aurora, KC設定ガイド, KC Realm/DB構造）
- doc/old/ - 過去の検討ドキュメント（読み取り専用）
