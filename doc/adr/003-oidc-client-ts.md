# ADR-003: 認証ライブラリとしてoidc-client-tsを採用

**ステータス**: Accepted
**日付**: 2026-03-17

## コンテキスト

React SPAからCognitoに接続するための認証ライブラリを選定する。

## 決定

**oidc-client-ts** を採用する。

## 理由

1. **OIDC標準準拠**: Cognito固有のAPIに依存しない
2. **Keycloak互換**: Phase 6のKeycloak検証時にそのまま流用可能（issuer URLを変えるだけ）
3. **軽量**: 認証に特化、不要な依存がない
4. **学習価値**: OIDC/OAuth 2.0の仕組みを直接理解できる

## 代替案

| 代替案 | 不採用理由 |
|-------|-----------|
| @aws-amplify/auth (Amplify v6) | Cognito専用、Keycloak検証時に使えない |
| amazon-cognito-identity-js | 低レベルすぎる、OIDC標準フローに沿わない |
| next-auth / Auth.js | Next.js前提、Vite SPAでは不適 |

## トレードオフ

- Amplifyより初期設定がやや複雑（OIDC設定を自前で書く）
- Cognito固有機能（Custom Auth Flow等）は直接使えない → PoCでは不要
- Keycloak切り替え時の差し替えコストがほぼゼロ（最大のメリット）
