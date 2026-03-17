# PoC 検証結果サマリー（Phase 1〜4）

**最終更新**: 2026-03-17

---

## 1. 検証目的と達成状況

| 目的 | 達成 | 備考 |
|------|:---:|------|
| Cognito ハイブリッド構成の実現性検証 | ✅ | 集約 + ローカルの2 User Pool構成で動作確認 |
| OIDC フェデレーション認証の動作確認 | ✅ | Auth0をEntra ID代替として連携 |
| Lambda Authorizer による JWT検証 | ✅ | JWKS取得、署名検証、マルチissuer対応 |
| マルチissuer対応の動作確認 | ✅ | 集約/ローカル両方のトークンを検証可能 |
| 認証フローの可視化 | ✅ | React SPAでフロー図・トークン・ログを表示 |

---

## 2. 構築した構成

### AWS リソース

| リソース | 名前 | 役割 |
|---------|------|------|
| Cognito User Pool | auth-poc-central | 集約認証基盤（共通アカウント相当） |
| Cognito User Pool | auth-poc-local | ローカル認証（サービスアカウント相当） |
| Cognito IdP | Auth0 (OIDC) | 外部IdP（Entra ID代替） |
| API Gateway | auth-poc-api | REST API エンドポイント |
| Lambda | auth-poc-authorizer | JWT検証 + 認可判定 |
| Lambda | auth-poc-backend | サンプルAPI（Context返却） |

### ローカル

| 要素 | 技術 |
|------|------|
| IaC | Terraform |
| Frontend | React + TypeScript + Vite |
| 認証ライブラリ | oidc-client-ts |
| Lambda | Python 3.11 + PyJWT |

---

## 3. 検証シナリオと結果

### シナリオ1: ローカルユーザー認証（Hosted UI）

```
ユーザー → Hosted UI（集約Cognito） → パスワード認証 → JWT発行 → API呼び出し → 200 OK
```

| 項目 | 結果 |
|------|------|
| ログイン | ✅ Authorization Code + PKCE で正常動作 |
| JWT内容 | sub, email, cognito:groups を含む |
| API認可 | ✅ issuerType=central として認可成功 |
| ログアウト | ✅ Cognitoセッション破棄 |

### シナリオ2: フェデレーション認証（Auth0 経由）

```
ユーザー → Cognito → Auth0 → 認証 → Cognito（JIT + JWT発行） → API呼び出し → 200 OK
```

| 項目 | 結果 |
|------|------|
| ログイン | ✅ identity_provider パラメータでHosted UIスキップ |
| JITプロビジョニング | ✅ 初回ログイン時にCognitoにユーザー自動作成 |
| identitiesクレーム | ✅ providerName=Auth0, providerType=OIDC |
| API認可 | ✅ issuerType=central として認可成功 |
| SSOセッション | ✅ Auth0セッションが維持され、再ログイン時パスワード不要 |
| 完全ログアウト | ✅ Auth0 → Cognito の多段ログアウトでSSO破棄 |

### シナリオ3: ローカルCognito認証（パートナーユーザー）

```
ユーザー → Hosted UI（ローカルCognito） → パスワード認証 → JWT発行 → API呼び出し → 200 OK
```

| 項目 | 結果 |
|------|------|
| ログイン | ✅ ローカルCognitoのHosted UIで認証 |
| JWT内容 | issuer がローカルCognito（集約と異なる） |
| API認可 | ✅ issuerType=local として認可成功 |
| マルチissuer判定 | ✅ Lambda Authorizerが正しくissuerを識別 |

### シナリオ4: 認可失敗

```
ユーザー → API呼び出し（トークンなし） → 401 Unauthorized
```

| 項目 | 結果 |
|------|------|
| トークンなし | ✅ 401 Unauthorized |
| 期限切れトークン | ✅ 401 Unauthorized（PyJWT ExpiredSignatureError） |
| 不明なissuer | ✅ 401 Unauthorized（ALLOWED_ISSUERS不一致） |

---

## 4. 判明した技術的事項

### 4.1 Cognito固有の注意点

| 事項 | 詳細 | 対応 |
|------|------|------|
| アクセストークンに`aud`クレームがない | Cognito固有。`client_id`クレームが代わり | PyJWTの`verify_aud`をオフ、手動で`client_id`検証 |
| フェデレーションユーザーはUser Pool内に作成される | JITプロビジョニング。パスワードはIdP側 | MAU課金の対象になる（$0.015/MAU） |
| Hosted UI のログアウトは外部IdPセッションを破棄しない | SSO動作の仕様 | 完全ログアウトは多段リダイレクトで実装 |

### 4.2 Lambda実装の注意点

| 事項 | 詳細 | 対応 |
|------|------|------|
| cryptographyライブラリのバイナリ互換性 | macOSビルドはLambda(Linux)で動かない | `pip install --platform manylinux2014_x86_64` |
| JWKSキャッシュ | Lambda実行環境間で共有されない | 実行環境ごとにキャッシュ。TTL 1時間で十分 |

### 4.3 SPA実装の注意点

| 事項 | 詳細 | 対応 |
|------|------|------|
| UserManagerインスタンスの共有 | CallbackPageで別インスタンスを作るとイベントが伝わらない | React Context経由で共有 |
| マルチUserManager | 集約/ローカルで別々のUserManagerが必要 | AuthProviderで両方を管理、Callbackで順番に試行 |
| ログアウト先の分岐 | ログイン元のCognitoに合わせてログアウトURLを切替 | JWTのissから判定 |

---

## 5. 本番適用に向けた残課題

| カテゴリ | 課題 | 優先度 |
|---------|------|--------|
| **認証** | Entra ID / Okta での実地検証 | 高 |
| **認証** | Pre Token Lambda（テナント識別グループ付与） | 高 |
| **認証** | クレームマッピング（IdP属性→カスタム属性） | 高 |
| **認可** | グループベース認可ルール実装 | 高 |
| **認可** | テナントスコープ検証 | 中 |
| **DR** | マルチリージョン（東京+大阪）構成 | 中 |
| **DR** | Route 53フェイルオーバー | 中 |
| **比較** | Keycloak構成の構築・比較 | 中 |
| **運用** | トークンリフレッシュの挙動詳細検証 | 低 |
| **運用** | Cognito User Pool のバックアップ・復旧 | 低 |
| **セキュリティ** | WAFとの連携 | 低 |

---

## 6. 次のPhase

| Phase | 内容 | 目的 |
|-------|------|------|
| 5 | DR検証（マルチリージョン） | Route 53フェイルオーバーの実現性確認 |
| 6 | Keycloak構成（第2パターン） | Cognitoとの運用負荷・コスト比較 |
