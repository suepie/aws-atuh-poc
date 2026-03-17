# アーキテクチャ検討経緯

## 認証基盤: Cognito vs Keycloak（未決定、PoC後に判断）

### Cognito推奨の根拠（ドキュメント検討結果）
- TCO: 3年で約$59,720（Keycloak: $149,340）
- DR: Route 53フェイルオーバーで対応可（Keycloakは公式非推奨）
- 運用: フルマネージド、SLA 99.9%
- コスト: 30万MAUで月額$1,535程度

### Keycloak検討すべきケース
- 100万MAU以上
- 高度なカスタマイズ必須
- 既存Keycloak運用チームがある
- データ主権要件

## 確定済み方針
- 認可方式: Lambda Authorizer（マルチIdP、カスタムロジック対応）
- API基盤: 三層構成（Internal/Partner/Public）
- 共通化範囲: WAF・認証・ログのみ共通、API GWは各システム管理
- OAuthフロー: Authorization Code Flow + PKCE（SPA）

## App Client設計
- 粒度: システム × アプリ種別（パターンB）
- PoCではまず1つ（SPA用）から開始

## 未決定事項
- Cognito vs Keycloak最終判断（PoC結果で決定）
- テナントのIdP保有状況
- MFA要件
- 可用性目標（99.9% or 99.95%）
