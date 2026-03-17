# AWS統合認証基盤PoC

## 目的
AWSを使った統合認証基盤の設計・検証。Cognito vs Keycloakを実際に構築して比較する。

## PoCの構成
- **第1パターン**: Cognitoハイブリッド構成（集約Cognito + ローカルCognito）
- **第2パターン**: Keycloak構成（後日）

## 制約
- AWSアカウントは1つのみ（User Pool 2つで擬似マルチアカウント）
- 外部IdP（Entra ID）なし → Phase 2でAuth0 Freeを外部IdP代替として使用

## 技術スタック
- IaC: Terraform
- Frontend: React + TypeScript + Vite（SPA）
- 認証ライブラリ: oidc-client-ts（Keycloak検証時にも流用可能）
- 将来デプロイ: S3 + CloudFront or Amplify Hosting

## 段階的検証プラン
- Phase 1: 集約Cognito + Hosted UI + React SPA（基本認証フロー）
- Phase 2: Auth0 Free を外部IdPとして追加（フェデレーション検証）
- Phase 3: Lambda Authorizer + API Gateway（JWT検証・認可）
- Phase 4: ローカルCognito追加（ハイブリッド・マルチissuer）
- Phase 5: DR検証（マルチリージョン）
