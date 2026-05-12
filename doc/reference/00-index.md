# 参考情報・調査結果 一覧

検討過程で得た参考情報や学習メモ。

**最終更新**: 2026-05-08

## 認証基礎・SSO

| ドキュメント | 内容 |
|------------|------|
| [sso-implementation-types.md](sso-implementation-types.md) | 認証の基礎（トークン・JWT署名）、SSO 5方式の比較、フェデレーション方式の優位性 |
| [session-management-deep-dive.md](session-management-deep-dive.md) | セッション管理の基礎、中途半端なログアウト問題、Cognito/Keycloak比較 |
| [mfa-sso-comparison.md](mfa-sso-comparison.md) | MFA・SSO比較マトリクス（Cognito/Keycloak/Auth0の全組合せ） |

## Cognito

| ドキュメント | 内容 |
|------------|------|
| [cognito-app-client.md](cognito-app-client.md) | App Clientの概念と設計パターン（システム×アプリ種別の粒度） |
| [cognito-pricing-2024-revision.md](cognito-pricing-2024-revision.md) | 料金体系（2024年11月改定、Lite/Essentials/Plus 3ティア制） |
| [auth0-free-as-idp.md](auth0-free-as-idp.md) | Auth0 FreeをEntra ID代替として使う方法 |
| [cognito-knockout-conditions.md](cognito-knockout-conditions.md) | **Cognito のノックアウト条件網羅**（Hard / Soft / Quota / Regional / UX、公式 + PoC ベース、判定チェックリスト付き） |

## Keycloak

| ドキュメント | 内容 |
|------------|------|
| [keycloak-realm-and-db.md](keycloak-realm-and-db.md) | Realmの概念、realm-export.json解説、DB構造（ER図）、トークン比較 |
| [keycloak-configuration-guide.md](keycloak-configuration-guide.md) | 設定の3箇所分類（ビルド時/環境変数/DB）、SSL問題、変更困難な設定一覧 |
| [keycloak-dr-aurora-sync.md](keycloak-dr-aurora-sync.md) | Aurora Global DBのレプリケーション詳細、フェイルバック手順、Cognito DR比較 |
| [keycloak-upstream-vs-rhbk.md](keycloak-upstream-vs-rhbk.md) | Upstream（OSS版）vs Red Hat build of Keycloak の比較・切り替え難易度・本番判断フレーム |
| [rhbk-support-and-pricing.md](rhbk-support-and-pricing.md) | RHBK サポート対象範囲（OS/DB/JVM/コンテナ基盤）・サブスクリプション構造・価格レンジ・現 PoC との差分・Red Hat 確認事項リスト |

## 過去の検討ドキュメント

`doc/old/` に過去の検討成果物がある（読み取り専用）。主要なものは以下：

| ファイル | 内容 |
|---------|------|
| authentication-authorization-detail.md | 認証・認可の詳細設計（最も詳細なフロー定義） |
| authentication-authorization-responsibility.md | 認証・認可責任分離設計（IdPクレームベース権限管理） |
| cognito-keycloak-dr-comparison (8).md | Cognito vs Keycloak比較の最終版 |
| hybrid-cognito-architecture-analysis.md | ハイブリッド型Cognito TCO分析 |
| adr-api-platform-authentication.md | API基盤認証の6つのADR |
| requirements-summary.md | 要件整理表・75件のQA |
| design-summary.md | 16観点の設計方針サマリー |
