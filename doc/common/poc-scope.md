# PoC 範囲・制約・技術スタック

**最終更新**: 2026-04-24（Phase 9 追記）

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
| IaC | Terraform（3つの独立state） | 既存ドキュメントがTerraform前提。Cognito/DR/Keycloak独立管理 |
| Frontend | React + TypeScript + Vite | SPA前提、シンプルな構成 |
| 認証ライブラリ | oidc-client-ts | OIDC標準準拠、Cognito/Keycloak両方で使用 |
| Backend（Phase 3） | Lambda (Python 3.11) + PyJWT | JWT検証用Lambda Authorizer |
| Keycloak（Phase 6-7） | Keycloak 26.0.8 on ECS Fargate + RDS PostgreSQL 16.13 | Cognito比較用の第2パターン |
| 外部IdP | Auth0 Free | Entra ID代替（Cognito/Keycloak両方で使用） |

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

### Phase 5: DR検証 ✅ 完了
- 大阪リージョンにDR Cognito User Pool作成
- Auth0 IdPはコンソール手動作成→terraform import（.well-known自動検出失敗のため、ADR-007）
- Lambda Authorizerにdr issuer追加（3 issuer対応: central/local/dr）
- React SPAにDRログインボタン追加（Hosted UI / Auth0フェデレーション）
- ログアウトのgetUserType()でdr判定対応
- **確認**: 大阪Cognitoでの認証・認可・ログアウト動作、Auth0 SSO維持
- **知見**: stateStoreプレフィックス分離が必須、Auth0 Logout URLsはURLエンコード完全一致

### Phase 6: Keycloak構成 ✅ 完了
- Keycloak 26.0.8 on ECS Fargate + RDS PostgreSQL + ALB
- 基本認証フロー（ログイン/ログアウト）、設定変更の即時反映
- 障害検証（ECS停止、RDS停止）
- Cognito vs Keycloak 総合対比
- **確認**: 運用・可用性ではCognito優位、機能・柔軟性ではKeycloak優位
- **知見**: start-devモードのCPU問題、SSL設定でのロックアウトリスク、設定3箇所分散の複雑さ

### Phase 7: MFA・SSO・Auth0連携 ✅ 完了
- Keycloak TOTP MFA 有効化・障害耐性確認（ECS/RDS再起動後もMFAデータ維持）
- 同一Realm内 ネイティブSSO（複数Client間、外部通信不要）
- Auth0 Identity Brokering（Keycloakの外部IdPとしてAuth0を設定）
- フェデレーションユーザーのMFAスキップ（二重MFA回避）
- **確認**: MFAデータはDB保存で障害に強い、SSOはRealm内ネイティブ、Back-Channel Logout対応
- **知見**: Conditional OTPでユーザー種別別MFA制御、First Broker Loginフロー、Default Scopesの設定漏れ

### Phase 8: クレームマッピング・認可の具体化（Cognito） ✅ 完了
- マルチテナント経費精算 API シナリオで認可を具体化
- Auth0 `app_metadata`（tenant_id / role）→ Post Login Action で IDトークン注入
- Cognito `attribute_mapping` で custom 属性に反映
- Pre Token Generation Lambda **V2** で Access Token にも tenant_id / roles / email 注入
- Lambda Authorizer → Backend Lambda へ tenantId / roles を Context 伝播
- Backend でロール階層（employee<manager<admin）とテナントスコープ検証
- **確認**: フェデレーションユーザー・ローカルユーザーの両方で同じ JWT 形・同じ認可判定
- **知見**: Pre Token V1 は Access Token 非対応→V2 必須、Access Token に email は既定で入らない、フェデ自動付与グループの除外が必要

### Phase 9: Keycloak 対応 + VPC Lambda による JWKS 完全プライベート化 ✅ 完了
- Phase 8 の認可シナリオを **Keycloak 発行 JWT でも同一動作**することを確認
- Keycloak の Protocol Mapper（User Attribute / User Realm Role / User Property）で同じクレーム名（tenant_id / roles / email）を出力
- Full scope allowed OFF で `offline_access` 等の内部ロール除外
- **VPC Lambda Authorizer**（Internal ALB + VPC Endpoint 経由）を新規追加、`/v2/*` エンドポイントで並列稼働
- Keycloak ネットワークを **Option B 本番理想形**に移行: カスタム VPC + Private Subnet + VPC Endpoints + NAT 不使用
- 3 系統の ALB（Public / Admin / Internal）で役割分離
- RDS スナップショット + `snapshot_identifier` で VPC 移行時のデータ保持
- CloudFront + WAF + Split-horizon DNS を**本番理想形としてドキュメント化**（実装は将来フェーズ）
- **確認**: 同一 JWT で `/v1`（非 VPC）と `/v2`（VPC）両経路が動作、Authorizer は差し替え可能・Backend 共通
- **知見**: internet-facing ALB は VPC 内でも public IP 解決（要 NAT または Internal ALB）、JWT `iss` と JWKS URL の不整合は env override で回避、S3 Gateway Endpoint 経由アクセスには SG の prefix list 指定必須

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
