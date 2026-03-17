# ADR-002: 認可方式としてLambda Authorizerを採用

**ステータス**: Accepted
**日付**: 2026-03-17

## コンテキスト

API Gatewayでの認可方式として、JWT Authorizer、Lambda Authorizer、IAM認証の3つがある。

## 決定

**Lambda Authorizer（TOKEN型）** を採用する。

## 理由

1. **マルチIdP対応**: 集約Cognito + ローカルCognitoの複数issuerを処理できる
2. **カスタムロジック**: グループベース認可、テナント分離が実装可能
3. **Context伝播**: userId, tenantId, groups等をBackendに渡せる
4. **REST API対応**: JWT AuthorizerはHTTP APIのみ

## 代替案

| 代替案 | 不採用理由 |
|-------|-----------|
| JWT Authorizer | HTTP APIのみ、単一issuer、カスタムロジック不可 |
| Cognito Authorizer | グループベース認可不可、マルチissuer対応が制限的 |
| IAM認証 | 外部ユーザー向けではない |
| Amazon Verified Permissions | 現時点ではグループベースRBACで十分、将来移行を検討 |

## トレードオフ

- レイテンシ: +15-60ms（キャッシュで軽減、TTL 300秒）
- コスト: 1億リクエスト/月で約$12（キャッシュ80%時）
- コールドスタート: Provisioned Concurrencyで対策可能
