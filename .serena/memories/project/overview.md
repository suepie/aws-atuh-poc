# AWS統合認証基盤PoC

## 目的
AWSを使った統合認証基盤の設計・検証。Cognito vs Keycloakを実際に構築して比較する。

## 完了した Phase（2026-03-17時点）
- Phase 1: 集約Cognito + Hosted UI + React SPA ✅
- Phase 2: Auth0 Free を外部IdPとしてフェデレーション認証 ✅
- Phase 3: Lambda Authorizer + API Gateway（JWT検証・認可・Context伝播）✅
- Phase 4: ローカルCognito追加、マルチissuer対応 ✅

## 残り Phase
- Phase 5: DR検証（マルチリージョン）
- Phase 6: Keycloak構成（第2パターン）

## 技術スタック
- IaC: Terraform
- Frontend: React + TypeScript + Vite + oidc-client-ts
- Backend: Python 3.11 (Lambda) + PyJWT
- AWS: Cognito User Pool x2, API Gateway, Lambda x2

## 主要な技術的知見
- Cognitoアクセストークンは`aud`ではなく`client_id`クレームを使用
- JWKSは公開エンドポイント → クロスアカウントでもIAM不要
- SSOセッションはIdP側に残る → 完全ログアウトには多段リダイレクト必要
- LambdaのPythonライブラリはLinux向けビルドが必要
