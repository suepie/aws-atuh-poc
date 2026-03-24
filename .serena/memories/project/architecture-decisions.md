# アーキテクチャ検討経緯（2026-03-24時点）

## 確定済み方針
- 認証基盤: Cognito User Pool（Identity Poolではない）- ADR-005
- 構成: ハイブリッド（集約Cognito + ローカルCognito）- ADR-001
- 認可: Lambda Authorizer（マルチissuer: central/local/dr）- ADR-002
- 認証ライブラリ: oidc-client-ts（Keycloak時にも流用可能）- ADR-003
- PoC構成: 1アカウント3 User Pool - ADR-004
- DR: 大阪リージョンにDR Cognito（Auth0はManual input）- ADR-007

## 未決定事項
- Cognito vs Keycloak最終判断 → 損益分岐点17.5万MAU（ADR-006）、MAU規模を顧客に確認必要
- Phase 6 Keycloak構成はまだ未実施

## コスト分析
- フェデレーション: $0.015/MAU（一律、ボリューム割引なし）
- 損益分岐点: 約175,000 MAU
- 17.5万MAU未満 → Cognito推奨、以上 → 要検討

## SSO方式
- フェデレーション方式（OIDC + Cognito）を採用
- リバースプロキシ方式は基本不要（レガシーアプリがある場合はALB+Cognito認証で対応可能）
- 詳細: doc/reference/sso-implementation-types.md

## DR検証で判明した課題
- 東京→大阪フェイルオーバーは未実装（Route 53 + カスタムドメインが必要）
- フェイルバック時にトークンリフレッシュ失敗→再ログイン必要（Auth0 SSOで自動認証されるためPW不要）
- DRコストは月額$2-5追加（Cognito User Pool維持費のみ）
- 同一ブラウザで東京・大阪両方にログインした場合、完全ログアウト時に片方のJWTが残る（PoCの制限事項）
