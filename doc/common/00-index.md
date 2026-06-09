# 共通ドキュメント

Cognito / Keycloak 横断の全体設計・比較・管理。

| ドキュメント | 内容 |
|------------|------|
| [architecture.md](architecture.md) | 全体アーキテクチャ（Cognito + Keycloak構成図・ディレクトリ） |
| [poc-scope.md](poc-scope.md) | PoC範囲・制約・技術スタック・Phase 1-9 |
| [poc-results.md](poc-results.md) | 検証結果サマリー・Cognito vs Keycloak比較 |
| [claim-mapping-authz-scenario.md](claim-mapping-authz-scenario.md) | Phase 8: クレームマッピング・認可シナリオ（経費精算SaaS） |
| [auth0-setup-claims.md](auth0-setup-claims.md) | Auth0 カスタムクレーム設定ガイド（Action / app_metadata） |
| [authz-architecture-design.md](authz-architecture-design.md) | 認可アーキテクチャ設計：バックエンド非依存・トークンキャッシュ・ベスト���ラクティス |
| [identity-broker-multi-idp.md](identity-broker-multi-idp.md) | Identity Broker パターン：マルチ顧客IdP対応設計 |
| [realm-separation-citations.md](realm-separation-citations.md) | **Multi-Realm 物理分離が「システム側ゼロ作業」と両立しない理由 — 一次資料引用集**：OIDC Core §3.1.3.7 / RFC 9068 / Keycloak 公式 / AWS API Gateway JWT Authorizer の verbatim quote 付き、顧客説明・反論対応テンプレ |
| [jwks-public-exposure.md](jwks-public-exposure.md) | JWKSエンドポイント公開の設計判断：なぜ公開が必要で安全なのか |
| [keycloak-network-architecture.md](keycloak-network-architecture.md) | Keycloak ネットワーク構成（実装実態）：IP 制限マトリクス・本番移行要件・CloudFront+WAF 完全形 |
| [auth-patterns.md](auth-patterns.md) | 認証パターン総覧（SPA / SSR / M2M / Token Exchange / SAML 等）と Cognito vs Keycloak 対応詳細 |
| [token-exchange-spec-and-patterns.md](token-exchange-spec-and-patterns.md) | **OAuth 2.0 Token Exchange (RFC 8693) 詳細技術仕様**：リクエスト/レスポンス全パラメータ + 7 設計パターン + Delegation vs Impersonation (`act` claim) + 実装例 4 言語 + 製品対応 (Cognito K1 / Keycloak / Auth0 / Entra OBO / Okta) + セキュリティ考慮 + 本プロジェクト設計判断 |
| [subdomain-architecture-notes.md](subdomain-architecture-notes.md) | **サブドメイン構成での認証基盤設計ノート**：接続アプリが同一親ドメインのサブドメイン（`app1.example.com` 等）で展開される場合の本方式適合性 + Cookie/SameSite/CORS 設計原則 + 現代ブラウザ規制（ITP/3rd-party Cookie 廃止）対応 + 設計注意点 10 項目 + ヒアリング 5 項目 |
| [hook-architecture-keycloak.md](hook-architecture-keycloak.md) | **Keycloak Hook アーキテクチャ — 初期実装 + 運用作業 詳細メモ**：INBOUND Hook（Keycloak SPI 8 種類）vs OUTBOUND Webhook（Phase Two `keycloak-events` デファクト）vs **SCIM 受信プラグイン**（別軸、2026-04 Keycloak 26.6 ネイティブ Experimental 追加 / Phase Two SCIM Per-org / Captain-P-Goldfish kc-21 EOL）の **3 軸整理** + 採用パターン 4 マトリクス + SSF/CAEP 未対応現状 + 初期実装 4 Phase + シナリオ別運用作業 + 性能/セキュリティ/テスト落とし穴 + **Elastic License v2 適合性評価** + 本プロジェクト設計指針（パターン B = Phase Two Webhook のみ から開始、SCIM 必要時にパターン D へ拡張） |
| [jit-scim-coexistence-keycloak.md](jit-scim-coexistence-keycloak.md) | **JIT + SCIM 併用環境の Keycloak 実装ノート**：顧客 IdP の SCIM 対応バラツキ（タイプ A=SCIM 採用 / B=JIT のみ / C=移行期混在）に対応する Keycloak 26 + Phase Two SCIM 実装。混在 3 タイプの Realm/IdP/Mapper 設定 + **externalId 突合 Custom Authenticator** + Sync Mode 詳細 (IMPORT/FORCE) + First Broker Login Flow 拡張 + JIT→SCIM 段階移行マージスクリプト + 落とし穴 7 つ。proposal §FR-7.4.5/6/7 の実装目線詳細 |
| [bff-implementation-notes.md](bff-implementation-notes.md) | **BFF パターン実装ノート（内部技術メモ）**：Cognito/Keycloak での Confidential Client 設定、Lambda BFF 構成、認証フロー詳細、コスト試算、段階移行プラン |
| [platform-architecture-patterns.md](platform-architecture-patterns.md) | **プラットフォーム別アーキテクチャパターン（内部技術メモ）**：Cognito / Keycloak OSS / Keycloak RHBK の本番想定構成図（mermaid）、Multi-AZ / Auto Scaling / DR、月額コスト試算、選定判定フロー。最新化対象のハブ |
| [system-design-patterns.md](system-design-patterns.md) | システム設計パターン 8 種（IdP × SPA/SSR × DR）：構成図・通信フロー・プロトコル・選定ガイド |
| [user-types-and-auth.md](user-types-and-auth.md) | ユーザー種別 5 カテゴリ（Platform Admin / Tenant Admin / End User Fed / End User Local / External）と認証方式・JWT クレーム・5 経路集約構成図 |
| [self-service-responsibility.md](self-service-responsibility.md) | **セルフサービスの責任配置 — 浅いブローカー設計での割切り**：パスワード変更・MFA 登録・プロフィール編集等 9 機能 × 5 ユーザー種別の所在マトリクス + broker 側に残る 3 例外（ローカルユーザー / セッション管理 / GDPR）+ アンチパターン + Keycloak 実装上の打ち手 + PowerPoint 構成案 |
| [broker-data-model.md](broker-data-model.md) | **浅いブローカーが保持するデータモデル — 何を持ち、何を持たないか**：Keycloak DB スキーマ実態に基づく 7 カテゴリ（federated_identity / user_entity / user_attribute / 役割 / セッション / 監査 / 同意）+ 持たないもの対比（password hash / MFA secret 等）+ JWT クレームへの反映 + 5 ユーザー種別差分 + ER 図 + GDPR/APPI/PCI DSS 含意 |
| [pci-dss-appi-compliance-gap.md](pci-dss-appi-compliance-gap.md) | **PCI DSS v4.0.1 + APPI 準拠ギャップ分析 — 一次資料引用集 + 必須対応リスト**：PCI DSS v4.0.1 PDF (`doc/old/`、gitignore 済) と PPC ガイドライン 通則編 PDF を pdftotext で実取得・原文照合した verbatim quote 集。Req 8 (認証) / 10.5.1 (ログ 12ヶ月) / 11.4 (ペネトレ)、APPI 法 22-28 + 33-35 + 規則 7・8 条。現状 Stage A × 規制マッピング + 必須対応 Top 12 + 要件定義 10 ゲーティング論点 |
| [destroy-guide.md](destroy-guide.md) | 環境削除・残存リソース確認手順 |
| [devcontainer-corporate-cert-setup.md](devcontainer-corporate-cert-setup.md) | Dev Container に企業プロキシ(Netskope等)のルートCA証明書を組み込む手順（日英併記） |
| [claude-code-communication-flow.md](claude-code-communication-flow.md) | Claude Code (Dev Container) の通信フロー・OAuth 認証・Netskope 対策の関係（日英併記） |
