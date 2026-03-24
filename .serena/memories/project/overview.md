# AWS統合認証基盤PoC

## 目的
AWSを使った統合認証基盤の設計・検証。Cognito vs Keycloakを実際に構築して比較する。

## 完了した Phase（2026-03-24時点）
- Phase 1: 集約Cognito + Hosted UI + React SPA ✅
- Phase 2: Auth0 Free を外部IdPとしてフェデレーション認証 ✅
- Phase 3: Lambda Authorizer + API Gateway（JWT検証・認可・Context伝播）✅
- Phase 4: ローカルCognito追加、マルチissuer対応 ✅
- Phase 5: DR検証（大阪リージョン、マルチリージョンCognito）✅

## 残り Phase
- Phase 6: Keycloak構成（第2パターン）

## 技術スタック
- IaC: Terraform（東京 + 大阪）
- Frontend: React + TypeScript + Vite + oidc-client-ts
- Backend: Python 3.11 (Lambda) + PyJWT
- AWS: Cognito User Pool x3（東京集約・東京ローカル・大阪DR）, API Gateway, Lambda x2

## AWSリソース構成
- 東京: 集約Cognito + ローカルCognito + API Gateway + Lambda Authorizer + Backend Lambda
- 大阪: DR Cognito（Auth0 IdPはコンソール手動作成→terraform import）

## 主要な技術的知見
- Cognitoアクセストークンは`aud`ではなく`client_id`クレーム
- JWKSは公開エンドポイント → クロスアカウント・クロスリージョンでもIAM不要
- SSOセッションはIdP側に残る → 完全ログアウトには多段リダイレクト
- LambdaのPythonライブラリはLinux向けビルドが必要（venv + --platform manylinux2014_x86_64）
- マルチUserManagerのstateStoreはプレフィックス分離が必須
- 大阪CognitoからAuth0の.well-known自動検出が失敗（コンソールManual inputで回避）
- Auth0 Allowed Logout URLsはURLエンコード済み完全一致で登録

## ドキュメント構成
- doc/design/ - 最新設計（architecture, auth-flow, poc-scope, poc-results, setup-guide）
- doc/adr/ - ADR 001-007
- doc/reference/ - 参考情報（App Client, 料金, Auth0設定, SSO実装方式比較）
- doc/old/ - 過去の検討ドキュメント（読み取り専用）
