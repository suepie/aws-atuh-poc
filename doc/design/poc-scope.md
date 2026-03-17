# PoC 範囲・制約・技術スタック

**最終更新**: 2026-03-17

---

## 目的

AWSを使った統合認証基盤について、Cognito と Keycloak をそれぞれ構築し比較検証する。
認証フローの動作確認、可視化、DR検証を段階的に実施する。

## PoC の制約

| 制約 | 内容 | 影響 |
|------|------|------|
| AWSアカウント | 1つのみ | User Pool 2つで擬似マルチアカウント構成 |
| 外部IdP | Entra ID なし | Phase 2 で Auth0 Free を代替使用 |
| 環境 | 検証用のみ | 本番運用は想定しない |

## 技術スタック

| 要素 | 選定 | 理由 |
|------|------|------|
| IaC | Terraform | 既存ドキュメントがTerraform前提、IaCの学習も兼ねる |
| Frontend | React + TypeScript + Vite | SPA前提、シンプルな構成 |
| 認証ライブラリ | oidc-client-ts | OIDC標準準拠、Keycloak検証時にも流用可能 |
| デプロイ（将来） | S3 + CloudFront or Amplify Hosting | SPA配信 |
| Backend（Phase 3〜） | Lambda (Python) | ドキュメントの実装例がPython |

## 段階的検証プラン

### Phase 1: 基本認証フロー ✅ 完了
- 集約Cognito User Pool作成（Terraform）
- Hosted UI でのログイン
- React SPA: ログイン/ログアウト、トークン取得・デコード表示
- **確認**: Authorization Code Flow + PKCE の動作理解

### Phase 2: フェデレーション認証 ✅ 完了
- Auth0 Free を外部IdPとしてCognitoに登録
- OIDC フェデレーション認証フロー
- JIT プロビジョニング、identitiesクレーム確認
- SSOセッション動作確認、完全ログアウト実装
- **確認**: `doc/old/authentication-authorization-detail.md` のフロー再現

### Phase 3: 認可（Lambda Authorizer）✅ 完了
- API Gateway + Lambda Authorizer 構築
- JWT署名検証（JWKS）、クレーム検証（client_id）
- IAM Policy生成、Context伝播（userId, email, groups, issuerType, idpName）
- Backend Lambda でのContext利用
- **確認**: 認可の4フェーズ（認証→検証→実行→ビジネスロジック）
- **知見**: Cognitoアクセストークンは`aud`ではなく`client_id`を使用

### Phase 4: ハイブリッド構成 ✅ 完了
- ローカルCognito User Pool追加
- Lambda Authorizerのマルチissuer対応（ALLOWED_ISSUERS辞書）
- issuer判定（集約=central / ローカル=local）
- ログアウト先の動的切替（issuerベース）
- **確認**: ハイブリッド構成の動作、3パターンのログイン

### Phase 5: DR検証（未実施）
- マルチリージョン構成（東京+大阪）
- Route 53 フェイルオーバー
- **確認**: フェイルオーバー時の認証継続性

### Phase 6: Keycloak構成（第2パターン）
- Keycloak on ECS Fargate
- Cognito と同等のフローを Keycloak で再現
- **確認**: Cognito との比較（運用負荷、柔軟性、DR対応）

## 検証用React SPAの要件

### 必須機能
- ログイン/ログアウト
- トークン（ID/Access/Refresh）のデコード表示
- 認証フローのログ・イベント表示
- 現在の認証状態の可視化

### 将来機能
- 認証フローのシーケンス図動的表示
- 複数App Client切り替え（SPA/サーバー/モバイル模擬）
- DR切り替えのシミュレーション
- Cognito vs Keycloak の並列比較画面

## アプリ種別の検証（将来）

認証基盤はクライアント種別に依存しない設計。App Clientを追加することで以下を検証可能：

| アプリ種別 | OAuth Flow | Phase |
|-----------|-----------|-------|
| SPA (React) | Authorization Code + PKCE | Phase 1 |
| サーバーサイドWeb | Authorization Code | 将来 |
| モバイル | Authorization Code + PKCE | 将来 |
| サーバー間通信 | Client Credentials | 将来 |
