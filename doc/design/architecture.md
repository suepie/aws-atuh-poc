# 全体アーキテクチャ（PoC構成）

**最終更新**: 2026-03-17

---

## 本番想定構成 vs PoC構成

### 本番想定（doc/old/ の設計）

```
AWS Organizations
├── 共通認証基盤アカウント (111111111111)
│   └── 集約 Cognito User Pool
│       ├── IdP: Entra ID TenantA (OIDC)
│       ├── IdP: Entra ID TenantB (OIDC)
│       ├── IdP: Okta TenantC (OIDC)
│       └── App Clients: 各システム用
│
├── 経費精算アカウント (222222222222)
│   ├── API Gateway
│   ├── Lambda Authorizer → 集約Cognito JWKS参照
│   ├── ローカル Cognito（パートナー用）
│   └── Backend
│
└── 出張予約アカウント (333333333333)
    ├── API Gateway
    ├── Lambda Authorizer → 集約Cognito JWKS参照
    └── Backend
```

### PoC構成（1アカウントで擬似再現）

```
単一AWSアカウント
├── User Pool A（集約Cognito役）
│   ├── IdP: Auth0 Free (OIDC) ← Entra IDの代替
│   ├── Hosted UI（ローカルユーザー用）
│   └── App Client: poc-spa
│
├── User Pool B（ローカルCognito役）※Phase 4〜
│   ├── ローカルユーザーのみ
│   └── App Client: poc-local-spa
│
├── API Gateway ※Phase 3〜
│   └── Lambda Authorizer
│       ├── User Pool A の JWKS 検証
│       └── User Pool B の JWKS 検証（Phase 4〜）
│
├── Backend Lambda ※Phase 3〜
│
└── React SPA（ローカル開発 → S3+CloudFront）
    ├── 認証フロー可視化
    ├── トークンデコード表示
    └── ログ・イベント表示
```

## なぜ1アカウントで再現可能か

- JWKS取得はHTTPS公開エンドポイント → IAM設定不要、アカウント関係なし
- Lambda Authorizerはissuer（User Pool ID）で判定 → 同一アカウント内でもissuerが異なる
- 本番移行時は環境変数（User Pool ID、Client ID）を変更するだけ

## 認証フローの対応関係

| フロー上の要素 | 本番 | PoC |
|--------------|------|-----|
| 外部IdP | Entra ID / Okta | Auth0 Free |
| 集約Cognito | 共通認証基盤アカウント | User Pool A |
| ローカルCognito | 各サービスアカウント | User Pool B |
| JWKS取得 | クロスアカウントHTTPS | 同一アカウントHTTPS |
| Lambda Authorizer | 各サービスアカウント | 同一アカウント |
| クライアント | 各種アプリ | React SPA |
