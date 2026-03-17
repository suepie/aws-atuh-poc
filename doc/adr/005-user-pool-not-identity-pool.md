# ADR-005: 共通認証基盤にCognito User Poolを使用（Identity Poolではない）

**ステータス**: Accepted
**日付**: 2026-03-17

## コンテキスト

共通認証基盤としてCognitoを使う際、User PoolとIdentity Pool（Federated Identities）のどちらを使うべきか、混同が生じていた。

## 決定

共通認証基盤には **Cognito User Pool** を使用する。Identity Poolは使用しない。

## 理由

### User Pool と Identity Pool の根本的な違い

| | User Pool | Identity Pool |
|--|-----------|---------------|
| 役割 | 認証 + JWT発行 | AWS一時認証情報（STS）の発行 |
| 出力 | JWT（ID/Access/Refresh Token） | AWS Access Key / Secret Key / Session Token |
| 外部IdP連携 | OIDC/SAMLで直接連携しJWT発行 | 認証済みトークンをAWS認証情報に変換 |
| API Gateway連携 | Cognito Authorizer / Lambda Authorizer | IAM認証のみ |

### 本アーキテクチャに必要な機能

以下はすべて **User Poolの機能** であり、Identity Poolでは提供されない：

- OIDC/SAMLフェデレーション → JWT発行
- クレームマッピング（IdP属性→カスタム属性）
- Pre Token Lambda（テナント識別グループ付与）
- `cognito:groups`, `custom:idp_groups` 等のJWTクレーム
- Hosted UI（ログイン画面）
- API Gateway + Lambda AuthorizerでのJWT検証

### Identity Pool が必要になるケース（本設計では該当しない）

- SPAからS3に直接ファイルアップロード
- SPAからAppSyncにIAM認証で直接接続
- モバイルアプリからDynamoDBに直接アクセス

本設計ではすべてのAPI呼び出しが `SPA → API Gateway → Lambda Authorizer → Backend Lambda` の経路を通るため、Identity Poolは不要。

## 参考

- [AWS re:Post: Understand Amazon Cognito user pools and identity pools](https://repost.aws/knowledge-center/cognito-user-pools-identity-pools)
- [AWS Documentation: Amazon Cognito identity pools](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-identity.html)
