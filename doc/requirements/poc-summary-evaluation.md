# PoC 総括評価

> 最終更新: 2026-04-21
> 対象: 共有認証基盤 PoC（Cognito / Keycloak 比較検証）

---

## 1. PoC の目的と達成状況

### 1.1 目的（poc-scope.md より）

「複数システムが利用する共有認証基盤として、AWS Cognito と Keycloak のどちらが適切かを技術的に検証する」

### 1.2 フェーズ別達成状況

| Phase | テーマ | 状態 | 成果物 |
|-------|--------|------|--------|
| 1 | Cognito 基本認証 | ✅ 完了 | Hosted UI + PKCE フロー確立 |
| 2 | Auth0 フェデレーション | ✅ 完了 | OIDC IdP 連携、JIT プロビジョニング |
| 3 | API 認可（Lambda Authorizer） | ✅ 完了 | マルチイシュア JWT 検証、グループベース RBAC |
| 4 | ハイブリッド（ローカル Cognito） | ✅ 完了 | 2 イシュア並行運用、動的ログアウトルーティング |
| 5 | DR（大阪リージョン） | ⚠ 一部未完 | 3 イシュア対応済、Route 53 自動フェイルオーバー未検証 |
| 6 | Keycloak デプロイ | ✅ 完了 | ECS + RDS + ALB、障害注入テスト |
| 7 | MFA + SSO + Auth0 Broker | ✅ 完了 | TOTP MFA、Back-Channel Logout、条件付き OTP |
| 8 | クレームマッピング・認可 | ✅ 完了 | Pre Token Lambda V2、ロール階層、テナントスコーピング |

**総合達成率: 8/8 Phase 完了（Phase 5 の Route 53 自動フェイルオーバーのみ未検証）**

---

## 1.3 検証内容サマリー

### 1.3.1 認証パターンの検証（計 8 パターン）

**Cognito 系（5 パターン）**:

| # | パターン | 概要 | IdP | 検証 Phase |
|---|---------|------|-----|-----------|
| A | Hosted UI（ローカルユーザー） | Cognito 標準ログイン画面でID/PW認証 | Cognito (central) | Phase 1 |
| B | Auth0 フェデレーション | Auth0（Entra ID 代替）経由の OIDC 連携 + JIT | Auth0 → Cognito (central) | Phase 2 |
| C | ローカル Cognito | 顧客専用の別 User Pool | Cognito (local) | Phase 4 |
| D | DR（大阪）ローカル | DR リージョンでのローカルユーザー認証 | Cognito (dr) | Phase 5 |
| E | DR（大阪）+ Auth0 | DR リージョンでの Auth0 フェデレーション | Auth0 → Cognito (dr) | Phase 5 |

**Keycloak 系（3 パターン）**:

| # | パターン | 概要 | IdP | 検証 Phase |
|---|---------|------|-----|-----------|
| F | Keycloak ローカルユーザー | Realm 内ローカルユーザー + TOTP MFA | Keycloak | Phase 6, 7 |
| G | Keycloak + Auth0 Brokering | Auth0 経由の IdP Brokering + 条件付き MFA スキップ | Auth0 → Keycloak | Phase 7 |
| H | Keycloak SSO | 同一 Realm 内の複数 Client でのシングルサインオン | Keycloak | Phase 7 |

### 1.3.2 機能別の検証項目

| カテゴリ | 検証項目 | 結果 | 検証場所 |
|---------|---------|------|---------|
| **認証** | PKCE + Authorization Code フロー | ✅ | Phase 1, 6 |
| | OIDC Identity Provider フェデレーション | ✅ | Phase 2, 7 |
| | JIT プロビジョニング | ✅ | Phase 2, 7 |
| | 複数 IdP 同時運用（central + local + dr） | ✅ | Phase 4, 5 |
| **API 認可** | Lambda Authorizer マルチイシュア JWT 検証 | ✅ | Phase 3, 4, 5 |
| | JWKS 取得・署名検証 | ✅ | Phase 3 |
| | Authorizer キャッシュ（300 秒 TTL） | ✅ | Phase 3 |
| | Context 伝播（tenantId, roles, issuerType） | ✅ | Phase 3, 8 |
| **MFA** | Cognito TOTP | ✅ | Phase 1 |
| | Keycloak TOTP | ✅ | Phase 7 |
| | 条件付き MFA（フェデレーションユーザーはスキップ） | ✅ | Phase 7 |
| | MFA 設定の永続化（ECS 再起動後） | ✅ | Phase 7 |
| | MFA 設定の永続化（RDS 障害後） | ✅ | Phase 7 |
| **SSO** | Cognito 同一 User Pool 内 SSO | ✅ | Phase 1 |
| | Keycloak Realm 内マルチ Client SSO | ✅ | Phase 7 |
| | Back-Channel Logout（Keycloak） | ✅ | Phase 7 |
| | Auth0 経由のクロス IdP SSO | ✅ | Phase 2, 7 |
| **ログアウト** | ローカルログアウト | ✅ | Phase 1, 6 |
| | Cognito Hosted UI ログアウト | ✅ | Phase 1 |
| | Auth0 セッション破棄（完全ログアウト） | ✅ | Phase 2 |
| | Keycloak Back-Channel Logout | ✅ | Phase 7 |
| | ハイブリッド環境での動的ログアウトルーティング | ✅ | Phase 4 |
| **DR** | 3 イシュア対応（central / local / dr） | ✅ | Phase 5 |
| | Auth0 SSO 維持でのリージョン切替 | ✅ | Phase 5（手動） |
| | Route 53 ヘルスチェック + 自動フェイルオーバー | ❌ | Phase 5 未実施 |
| | Cognito リージョン間バックアップ | ⚠ | Phase 5（仕組み設計のみ） |
| **クレーム / 認可** | Pre Token Generation Lambda V2 | ✅ | Phase 8 |
| | tenant_id 属性のトークン注入 | ✅ | Phase 8 |
| | roles 属性のトークン注入 | ✅ | Phase 8 |
| | ロール階層（employee < manager < admin） | ✅ | Phase 8 |
| | テナント分離（cross-tenant 拒否） | ✅ | Phase 8 |
| | Keycloak Protocol Mapper でのクレーム変換 | ❌ | Phase 9（未着手） |
| **障害・復旧** | Keycloak ECS タスク停止 → 自動再起動 | ✅ | Phase 6 |
| | RDS 停止 → 復旧 | ✅ | Phase 6 |
| | Keycloak バージョンアップ（設定ファイル変更） | ✅ | Phase 6 |
| | Client リダイレクト URI 変更 | ✅ | Phase 6 |
| **コスト** | Cognito / Keycloak 3 年 TCO 試算 | ✅ | ADR-006 |
| | 損益分岐 MAU の算出（175,000 MAU） | ✅ | ADR-006 |
| | DR 構成のコスト比較 | ✅ | poc-results.md |

### 1.3.3 障害注入テストの内容

| 障害シナリオ | 対象 | 検証目的 | 結果 |
|------------|------|---------|------|
| ECS タスク強制停止 | Keycloak コンテナ | 自動復旧・セッション影響の確認 | ✅ 自動復旧、既存セッションは一時 503 → 復旧 |
| RDS インスタンス停止 | Keycloak DB | Keycloak の挙動・復旧手順 | ✅ 停止中は認証不可、復旧後は MFA 設定も保持 |
| リージョン障害想定 | 東京リージョン | DR への切替手順 | ⚠ 手動切替のみ確認（自動化未検証） |
| Auth0 接続不可 | Auth0 Tenant | フォールバック挙動 | ✅ ローカルユーザーは影響なし |
| Lambda Authorizer エラー | API Gateway | エラーレスポンス形式 | ✅ 401 正常返却 |

### 1.3.4 観点 × プラットフォーム検証マトリクス

「どの観点で、Cognito / Keycloak それぞれに何ができたか」を横並びで比較。

凡例: ✅ 検証済み / ⚠ 一部検証・制約あり / ❌ 未検証 / ➖ 対象外

#### (A) 認証方式

| 観点 | Cognito | Keycloak | 備考 |
|------|:-------:|:--------:|------|
| ID/PW 認証（ローカルユーザー） | ✅ Phase 1 | ✅ Phase 6 | 両者とも Hosted UI / Admin Console 経由 |
| Authorization Code + PKCE フロー | ✅ Phase 1 | ✅ Phase 6 | oidc-client-ts で統一実装 |
| Hosted UI のカスタマイズ | ⚠ 制約あり | ✅ 自由 | Cognito は CSS / ロゴのみ、Keycloak はテーマ全面カスタム可 |
| パスワードポリシー設定 | ✅ | ✅ | Cognito デフォルト / Keycloak は Realm 単位で細かく制御可 |
| ソーシャルログイン | ❌ 未検証 | ❌ 未検証 | Google/Facebook 等、本 PoC では対象外 |

#### (B) フェデレーション（外部 IdP 連携）

| 観点 | Cognito | Keycloak | 備考 |
|------|:-------:|:--------:|------|
| Auth0 (OIDC) フェデレーション | ✅ Phase 2 | ✅ Phase 7 | 両者とも Authorization Code フロー |
| JIT プロビジョニング | ✅ Phase 2 | ✅ Phase 7 | 初回ログイン時に自動ユーザー作成 |
| 属性マッピング | ✅ attribute_mapping | ✅ IdP Mapper | Cognito は宣言的、Keycloak は Mapper 単位で柔軟 |
| ログイン画面での IdP 自動表示 | ⚠ `identity_provider` パラメータ必要 | ✅ 自動表示 | **Keycloak が UX 優位** |
| 大阪リージョンからの Auth0 接続 | ❌ 失敗（ADR-007） | ➖ | `.well-known` 到達不可 |
| SAML IdP 対応 | ❌ 未検証 | ❌ 未検証 | 両者とも対応可だが本 PoC では未検証 |
| LDAP IdP 対応 | ❌ **非対応** | ❌ 未検証（対応可） | **Cognito は仕様として非対応**、Keycloak は User Federation |

#### (C) MFA

| 観点 | Cognito | Keycloak | 備考 |
|------|:-------:|:--------:|------|
| TOTP MFA | ✅ Phase 1 | ✅ Phase 7 | — |
| SMS MFA | ❌ 未検証 | ❌ 未検証 | Cognito は対応済、Keycloak は外部連携必要 |
| WebAuthn / FIDO2 | ❌ 未検証 | ❌ 未検証（対応可） | Keycloak は標準対応、Cognito は未対応 |
| フェデレーションユーザーの MFA スキップ | ⚠ 個別実装 | ✅ 条件付き OTP | **Keycloak が柔軟** |
| MFA 設定の永続化（ECS 再起動後） | ➖ マネージド | ✅ Phase 7 | Keycloak は RDS 保持を確認済 |
| MFA 設定の永続化（RDS 障害後） | ➖ マネージド | ✅ Phase 7 | 復旧後も設定保持 |
| MFA 強制 / 任意の切替 | ✅ | ✅ | Realm / Pool 単位で設定可 |

#### (D) SSO / ログアウト

| 観点 | Cognito | Keycloak | 備考 |
|------|:-------:|:--------:|------|
| 同一 User Pool / Realm 内 SSO | ✅ Phase 1 | ✅ Phase 7 | — |
| 複数 Client 間の SSO | ✅ | ✅ Phase 7 | マルチシステム連携の基本 |
| ローカルログアウト | ✅ | ✅ | トークン破棄のみ |
| Hosted UI / Keycloak UI ログアウト | ✅ | ✅ | IdP セッション破棄 |
| Auth0 セッション破棄（完全ログアウト） | ⚠ URL エンコード要注意 | ✅ | Cognito は federated sign-out 実装に落とし穴あり |
| Back-Channel Logout | ❌ **非対応** | ✅ Phase 7 | **Keycloak のみ対応** |
| Front-Channel Logout | ✅ | ✅ | — |
| ハイブリッド環境での動的ログアウト | ✅ Phase 4 | ➖ | Cognito central/local/dr 3 イシュア対応 |

#### (E) マルチテナント / IdP Broker

| 観点 | Cognito | Keycloak | 備考 |
|------|:-------:|:--------:|------|
| 複数 IdP 並行運用 | ✅ | ✅ | 両者対応 |
| テナントごとの属性マッピング | ✅ attribute_mapping | ✅ IdP Mapper | — |
| テナント追加時の既存システム影響 | ✅ 影響なし | ✅ 影響なし | Broker パターン（identity-broker-multi-idp.md）|
| 顧客 IdP 数のスケーラビリティ | ✅ | ✅ | JWT 検証性能は IdP 数に依存しない |
| ログイン画面での IdP 選択 UX | ⚠ パラメータ指定必要 | ✅ ボタン自動生成 | **Keycloak 優位** |

#### (F) 認可（JWT / クレーム）

| 観点 | Cognito | Keycloak | 備考 |
|------|:-------:|:--------:|------|
| JWT 発行（Access / ID / Refresh） | ✅ | ✅ | 標準 OIDC 準拠 |
| JWT にカスタムクレーム注入 | ✅ Pre Token Lambda V2 | ❌ **未検証（Phase 9 で実施予定）** | **Keycloak は Protocol Mapper で対応可** |
| tenant_id クレーム | ✅ Phase 8 | ❌ 未検証 | — |
| roles クレーム（配列） | ✅ Phase 8 | ❌ 未検証 | — |
| ロール階層（継承） | ✅ Phase 8（アプリ側実装） | ➖ | Keycloak は Realm Role の Composite で対応可 |
| テナント分離（cross-tenant 拒否） | ✅ Phase 8 | ❌ 未検証 | Lambda Authorizer で実装済 |
| Pre Token Lambda V1 の制約 | ⚠ Access Token 変更不可 | ➖ | V2 移行で解決 |
| Federation ユーザーへのカスタムクレーム | ✅ Phase 8 | ❌ 未検証 | 内部グループ名の除外処理要 |

#### (G) API 認可（Lambda Authorizer）

| 観点 | Cognito | Keycloak | 備考 |
|------|:-------:|:--------:|------|
| JWT 署名検証（JWKS） | ✅ Phase 3 | ✅ Phase 8 | 同一 Lambda で両対応 |
| マルチイシュア対応 | ✅ 3 イシュア（central/local/dr） | ✅ 1 イシュア追加済 | Authorizer コードは同一 |
| Authorizer キャッシュ | ✅ 300 秒 TTL | ✅ 同様 | — |
| Context 伝播（tenantId, roles 等） | ✅ Phase 3, 8 | ✅ | バックエンドへ情報引き継ぎ |
| マルチアカウント想定の JWKS 公開 | ✅ HTTPS 公開 | ✅ HTTPS 公開 | ADR-004、jwks-public-exposure.md |

#### (H) DR / 可用性

| 観点 | Cognito | Keycloak | 備考 |
|------|:-------:|:--------:|------|
| マルチリージョン構成 | ✅ Phase 5（東京 + 大阪） | ❌ 未検証 | — |
| DR リージョン IdP 連携 | ⚠ Auth0 は大阪不可 | ➖ | ADR-007 |
| 手動フェイルオーバー | ✅ Phase 5 | ❌ 未検証 | — |
| 自動フェイルオーバー（Route 53） | ❌ **未検証** | ❌ **未検証** | Phase 5 残課題 |
| バックアップ・リストア | ⚠ 概念設計のみ | ⚠ RDS スナップショットのみ | — |
| マネージド SLA | ✅ 99.9% | ❌ 自前設計 | AWS 保証 vs 自前 HA |
| DR 時のセッション維持（Auth0 SSO） | ✅ Phase 5 | ❌ 未検証 | Auth0 側でセッション維持 |

#### (I) 運用

| 観点 | Cognito | Keycloak | 備考 |
|------|:-------:|:--------:|------|
| 管理コンソール | ✅ AWS Console | ✅ Keycloak Admin Console | Keycloak の方が機能豊富 |
| Terraform 管理 | ✅ | ⚠ インフラのみ / Realm は別管理 | Keycloak Realm は realm-export.json |
| バージョンアップ | ➖ 自動 | ⚠ 手動 Docker image 更新 | **Cognito 優位** |
| パッチ適用 | ➖ 自動 | ⚠ 手動 | **Cognito 優位** |
| 障害検知・自動復旧（ECS） | ➖ マネージド | ✅ Phase 6 | ECS 自動再起動確認済 |
| 設定変更のリードタイム | ⚠ 一部再作成必要 | ✅ 即時反映 | Keycloak は多くを即時反映 |
| ログ・監査 | ✅ CloudWatch + CloudTrail | ⚠ Keycloak Event + CloudWatch | Keycloak はイベント設定要 |

#### (J) コスト

| 観点 | Cognito | Keycloak | 備考 |
|------|:-------:|:--------:|------|
| 初期コスト（インフラ） | ✅ $0 | ❌ $940/月〜 | Keycloak は常時稼働必要 |
| 従量課金（MAU） | ❌ $0.015/MAU（連携） | ➖ なし | — |
| 損益分岐 MAU | ➖ | ➖ | **175,000 MAU**（ADR-006） |
| DR コスト | ✅ $0.50/月 + MAU | ❌ $890/月 | **Cognito 圧倒的優位** |
| 運用人件費 | ✅ ほぼ不要 | ❌ 月 $1,680 想定 | Keycloak は運用工数必要 |

#### (K) 障害・復旧テスト

| 観点 | Cognito | Keycloak | 備考 |
|------|:-------:|:--------:|------|
| ECS タスク停止 → 復旧 | ➖ | ✅ Phase 6 | 自動再起動確認 |
| RDS 停止 → 復旧 | ➖ | ✅ Phase 6 | MFA 設定も永続 |
| Auth0 接続不可時の挙動 | ✅ ローカルユーザー影響なし | ❌ 未検証 | — |
| Lambda Authorizer エラー | ✅ 401 返却確認 | ✅ 同 Lambda 使用 | — |
| リリース・設定変更（クライアントURI 等） | ✅ | ✅ Phase 6 | 両者とも即時反映 |

### 1.3.5 観点別サマリー（どちらが優位か）

| 観点カテゴリ | Cognito 優位 | Keycloak 優位 | 備考 |
|------------|:-----------:|:------------:|------|
| 認証方式 | — | ◯（柔軟性） | UI カスタマイズ |
| フェデレーション | — | ◯（UX + LDAP） | IdP 自動表示、LDAP 対応 |
| MFA | — | ◯（柔軟性） | WebAuthn、条件付き OTP |
| SSO / ログアウト | — | ◯（Back-Channel） | ログアウト完全性 |
| マルチテナント | △ 同等 | △ 同等 | UX で Keycloak やや優位 |
| 認可・クレーム | ◯（検証進捗） | — | PoC では Cognito が先行、本番は同等 |
| API 認可 | △ 同等 | △ 同等 | 同一 Lambda で対応 |
| DR | ◯（コスト・SLA） | — | マネージドの強み |
| 運用 | ◯（無運用） | — | 運用工数圧倒的差 |
| コスト（小規模） | ◯ | — | 〜175K MAU |
| コスト（大規模） | — | ◯ | 175K MAU〜 |
| 障害復旧 | ◯（マネージド） | △ 要設計 | — |

**総合傾向**: Cognito は**運用・コスト・可用性**で優位、Keycloak は**柔軟性・UX・大規模時コスト**で優位。選定は MAU 規模 + カスタマイズ要件が決定要因。

---

### 1.3.6 コスト検証の結果

| シナリオ | Cognito | Keycloak | 備考 |
|---------|---------|----------|------|
| 初期コスト（100 MAU） | $0〜 | $940/月〜 | Keycloak は ECS/RDS 常時稼働 |
| 50,000 MAU | $750/月 | $940/月 | Cognito 優位 |
| **175,000 MAU（損益分岐）** | **$2,625/月** | **$2,625/月** | ADR-006 参照 |
| 500,000 MAU | $7,500/月 | $2,625/月 | Keycloak 優位 |
| DR 追加コスト | $0.50/月 + MAU 按分 | $890/月 | Keycloak DR は常時稼働必須 |

---

## 1.4 ADR（Architecture Decision Records）サマリー

意思決定の記録が 9 件残っている。本番設計でも参照すべき重要な判断根拠。

### 1.4.1 ADR 一覧と概要

| ADR | タイトル | 状態 | 日付 | 一言サマリー |
|-----|---------|------|------|------------|
| [001](../adr/001-cognito-hybrid-for-poc.md) | PoC 第1パターンとして Cognito ハイブリッド構成を採用 | Accepted | 2026-03-17 | 中央 + ローカル + DR の 3 User Pool 構成で検証開始 |
| [002](../adr/002-lambda-authorizer.md) | 認可方式として Lambda Authorizer を採用 | Accepted | 2026-03-17 | マルチイシュア対応・カスタムロジックが必要なため |
| [003](../adr/003-oidc-client-ts.md) | 認証ライブラリとして oidc-client-ts を採用 | Accepted | 2026-03-17 | OIDC 標準準拠で Cognito/Keycloak 両対応 |
| [004](../adr/004-single-account-poc.md) | 1 アカウント 2 User Pool でマルチアカウント構成を擬似再現 | Accepted | 2026-03-17 | JWKS は HTTPS 公開、アカウント分離は本番で再検証 |
| [005](../adr/005-user-pool-not-identity-pool.md) | 共通認証基盤に User Pool を使用（Identity Pool ではない） | Accepted | 2026-03-17 | JWT 発行が目的で AWS STS クレデンシャル不要 |
| [006](../adr/006-cognito-vs-keycloak-cost-breakeven.md) | Cognito vs Keycloak コスト損益分岐点の分析 | **Proposed** | 2026-03-17 | 損益分岐 175,000 MAU、MAU 規模次第で選定 |
| [007](../adr/007-osaka-auth0-idp-limitation.md) | 大阪リージョンで Auth0 OIDC IdP 接続不可の記録 | Accepted | 2026-03-18 | ap-northeast-3 から Auth0 `.well-known` 到達不可、本番は Entra ID で要再検証 |
| [008](../adr/008-keycloak-start-dev-for-poc.md) | PoC で Keycloak start-dev モードを使用 | Accepted | 2026-03-25 | HTTP 許可（ACM 不要）、本番は `start --optimized` 必須 |
| [009](../adr/009-mfa-responsibility-by-idp.md) | MFA 責任はパスワード管理側に帰属させる | Accepted | 2026-03-28 | 二重 MFA 回避、フェデレーションユーザーは IdP 側で MFA |

### 1.4.2 ADR の重要度・本番への影響度

| ADR | 重要度 | 本番での再検討 | 理由 |
|-----|--------|--------------|------|
| 001 | 中 | **要** | PoC 用構成。本番はアカウント分離等で再設計 |
| 002 | **高** | 基本維持 | マルチイシュア対応はそのまま継続可能 |
| 003 | 中 | 基本維持 | フロントエンド再開発時も同ライブラリ採用推奨 |
| 004 | **高** | **要** | 本番はマルチアカウント構成の実装が必要 |
| 005 | 中 | 維持 | User Pool で十分、Identity Pool は別目的 |
| 006 | **最高** | **要最終確定** | MAU 規模確定後に Proposed → Accepted に昇格すべき最重要 ADR |
| 007 | **高** | **要再検証** | 本番の Entra ID / Okta では事象が異なる可能性 |
| 008 | **高** | **要** | 本番は `start --optimized` + HTTPS 必須 |
| 009 | 中 | 維持 | MFA 設計の基本方針は継続可能 |

### 1.4.3 ADR で決定済みの主要設計

- **認証ライブラリ**: oidc-client-ts（OIDC 標準準拠、Cognito/Keycloak 両対応）
- **認可方式**: Lambda Authorizer（キャッシュ 300 秒、マルチイシュア対応）
- **User Pool 構成**: 中央 + ローカル + DR の 3 分割（本番は顧客単位に拡張）
- **Keycloak 運用モード**: 本番は start --optimized + ACM（PoC は start-dev）
- **MFA 方針**: パスワード管理側に責任集約、二重 MFA を回避
- **JWKS 公開方針**: パブリック公開が正解（暗号理論・OIDC 仕様・他社慣行）

### 1.4.4 本番移行時に追加が必要な ADR（想定）

要件定義・本番設計で以下の ADR を追加する想定：

| 想定 ADR | テーマ | 判断タイミング |
|---------|-------|-------------|
| ADR-010 | Keycloak Private Subnet + VPC Endpoint 構成（発番済・Accepted） | ✅ 2026-04-21 |
| ADR-011 | 認証基盤前段ネットワーク設計（HTTPS / カスタムドメイン / WAF / CloudFront）統合判断（発番済・Proposed） | ⏳ 要件定義 Phase C で Accepted 化 |
| ADR-012 | VPC Lambda Authorizer + Internal ALB による JWKS プライベート化（発番済・Accepted） | ✅ 2026-04-23 |
| ADR-013 | CloudFront + WAF による IP 制限置き換え（発番済・Proposed） | ⏳ 要件定義で確定後 Accepted 化 |
| ADR-014 | 共有認証基盤が対応する認証パターンの範囲（発番済・Proposed） | ⏳ 要件定義 Phase A/B で確定 |
| ADR-015 | PoC では RHBK 検証を実施せず本番設計フェーズへ先送り（発番済・Proposed） | ⏳ 本番設計時に Accepted 化 or 撤回 |
| ADR-016 | Upstream Keycloak vs RHBK 最終選定 | 本番設計フェーズ（FIPS / サポート / 予算 確定後） |
| ADR-017 | Cognito vs Keycloak 最終選定 | Week 4 最終判断会議（ADR-014 確定後） |
| ADR-018 | 本番マルチアカウント戦略 | 設計フェーズ |
| ADR-019 | DR 自動フェイルオーバー方式（Route 53 等） | 設計フェーズ |
| ADR-020 | バックエンド実装言語・フレームワーク | 設計フェーズ |
| ADR-021 | 監視・アラート設計 | 運用設計 |
| ADR-022 | 監査ログの保存・検索基盤 | 運用設計 |

---

## 2. 既存ドキュメント評価

### 2.1 ドキュメント品質マトリクス

| カテゴリ | ドキュメント | 完成度 | 正確性 | 実用性 | 評価 |
|---------|------------|--------|--------|--------|------|
| **共通** | architecture.md | ◎ | ◎ | ◎ | 構成図・コンポーネント一覧が正確。実装と一致 |
| | poc-scope.md | ◎ | ◎ | ◎ | Phase 定義・制約事項が明確。技術選定理由あり |
| | poc-results.md | ◎ | ◎ | ○ | 66KB と大きいが網羅的。Phase 別の結果が明確 |
| | authz-architecture-design.md | ◎ | ◎ | ◎ | 認可パターン 3 案比較、本番設計指針として十分 |
| | identity-broker-multi-idp.md | ◎ | ◎ | ◎ | マルチ IdP スケーリング問題を的確に解決 |
| | jwks-public-exposure.md | ◎ | ◎ | ◎ | 暗号理論に基づく安全性根拠。RFC 引用あり |
| | claim-mapping-authz-scenario.md | ○ | ◎ | ◎ | 具体シナリオで理解しやすい。Keycloak 実装は未完 |
| | auth0-setup-claims.md | ◎ | ◎ | ◎ | ハンズオン形式で再現性が高い |
| | destroy-guide.md | ○ | ◎ | ○ | 基本的だが必要十分 |
| **ADR** | ADR-001〜009 | ◎ | ◎ | ◎ | 意思決定の背景が明確。代替案との比較あり |
| **Cognito** | auth-flow.md | ◎ | ◎ | ◎ | 5 パターンのシーケンス図。DR フローまで網羅 |
| | setup-guide.md | ○ | ◎ | ◎ | 58KB と大きいが手順は正確。分割推奨 |
| **Keycloak** | auth-flow.md | ○ | ◎ | ◎ | Cognito との差分が明確 |
| | setup-guide.md | ○ | ◎ | ◎ | SSL ワークアラウンドが有用 |
| | test-scenarios.md | ◎ | ◎ | ◎ | 障害注入テストが実践的 |
| | mfa-sso-auth0-scenarios.md | ◎ | ◎ | ◎ | MFA 永続性・SSO・二重 MFA 回避を検証 |
| **参考** | 9 ドキュメント | ◎ | ◎ | ○ | 教育的価値が高い。直接の成果物ではないが判断材料として有用 |

凡例: ◎ 優秀 / ○ 良好 / △ 改善要 / × 不足

### 2.2 ドキュメント全体の強み

1. **網羅性**: 40+ ドキュメント、アーキテクチャ・ADR・手順書・テストシナリオを完備
2. **判断根拠の明示**: ADR 9 件で技術選定の「なぜ」が記録されている
3. **視覚的説明**: Mermaid 図を多用、フロー理解が容易
4. **実践的検証**: 障害注入テスト、コスト試算、運用シナリオまで網羅
5. **再現性**: setup-guide のコマンドがコピペ可能

### 2.3 ドキュメントの改善点

1. **大容量ファイル**: poc-results.md (66KB)、setup-guide.md (58KB) は分割が望ましい
2. **インデックスの更新漏れ**: doc/common/00-index.md に Phase 8 追加ドキュメントが反映途上
3. **old/ フォルダ**: アーカイブ基準が不明確

### 2.4 ドキュメント最新化対応（2026-04-21 実施）

Keycloak ネットワーク構成の実装実態とドキュメントに差分があったため、以下を対応済:

| 対応 | 対象 | 内容 |
|-----|------|------|
| ✅ 新規作成 | [keycloak-network-architecture.md](../common/keycloak-network-architecture.md) | 実装実態に基づくネットワーク構成・IP 制限マトリクス・本番移行要件 |
| ✅ 更新 | [architecture.md](../common/architecture.md) | Admin ALB の追記、Public ALB の L7 制限を注記 |
| ✅ 更新 | [jwks-public-exposure.md](../common/jwks-public-exposure.md) | Public ALB の L7 パスベース制限を追記（従来は L4 SG のみの記載） |

**検出された主な差分**:
- Admin ALB が `architecture.md` に未反映だった
- `jwks-public-exposure.md` が Public ALB の L7 Listener Rule（JWKS 以外のパスは IP 制限）を記載していなかった
- RDS の「メンテナンス用自分の IP 許可」がどのドキュメントにも記載されていなかった

### 2.5 Option B 移行対応（2026-04-21 実施）

本番理想形（Private Subnet + VPC Endpoint 方式）へ Keycloak インフラを移行した。これにより、不足箇所の多くが解消された。

| 対応 | 対象 | 内容 |
|-----|------|------|
| ✅ 新規 Terraform | [infra/keycloak/network.tf](../../infra/keycloak/network.tf) | カスタム VPC + Public/Private サブネット × 2 AZ |
| ✅ 新規 Terraform | [infra/keycloak/vpc-endpoints.tf](../../infra/keycloak/vpc-endpoints.tf) | ECR API / ECR DKR / S3 Gateway / CloudWatch Logs Endpoint |
| ✅ 更新 Terraform | [security-groups.tf](../../infra/keycloak/security-groups.tf) | ECS Egress を VPC 内 :443/:5432/:53 に限定、RDS の my_ip 許可削除 |
| ✅ 更新 Terraform | [ecs.tf](../../infra/keycloak/ecs.tf) / [rds.tf](../../infra/keycloak/rds.tf) / [alb.tf](../../infra/keycloak/alb.tf) | Private Subnet 配置、`assign_public_ip=false` |
| ✅ 新規 ADR | [ADR-010](../adr/010-keycloak-private-subnet-vpc-endpoints.md) | 意思決定の記録 |
| ✅ 更新 | [keycloak-network-architecture.md](../common/keycloak-network-architecture.md) | 新構成の反映（N3/N4 を解消済としてマーク） |

**解消されたリスク**:
- ECS タスクのパブリック IP 付与 → 除去
- ECS SG Egress 全開（0.0.0.0/0） → VPC 内必要ポートのみに限定
- RDS SG にメンテ用 my_ip 許可 → 削除
- デフォルト VPC 使用 → カスタム VPC + サブネット分離

**残る本番課題**（[keycloak-network-architecture.md §6](../common/keycloak-network-architecture.md) 参照）:
- **Critical**: N1 HTTPS 化 / N2 Admin ALB internal 化 / N5 正式ドメイン
- **High（設計判断）**: N10 WAF 適用 / N11 DB メンテ経路 / **N16 CloudFront 配置**（→ ADR-013 で詳細化）/ **N17 認証パターン対応範囲**（→ ADR-014）
- **Medium**: N12 VPC Flow Logs / N13 ALB アクセスログ / N14 VPC Endpoint 監視 / N15 不正 IP ブロック

### 2.6 認証パターン拡張ドキュメントの追加（2026-04-24 実施）

PoC で検証した認証パターンが SPA のみだったため、共有基盤として想定される全パターンを整理:

| 対応 | 対象 | 内容 |
|-----|------|------|
| ✅ 新規作成 | [auth-patterns.md](../common/auth-patterns.md) | 9 パターンの総覧（SPA / SSR / モバイル / M2M / Token Exchange / Device Code / SAML / mTLS / ROPC）+ Cognito vs Keycloak 対応詳細 |
| ✅ 新規 ADR | [ADR-013](../adr/013-cloudfront-waf-ip-restriction.md) | CloudFront + WAF による IP 制限置き換え（ADR-011 Pattern C の詳細化） |
| ✅ 新規 ADR | [ADR-014](../adr/014-auth-patterns-scope.md) | 認証パターン対応範囲の判断（ADR-015 プラットフォーム選定の前提条件） |
| ✅ 更新 | [keycloak-network-architecture.md](../common/keycloak-network-architecture.md) | §6.5 に CloudFront + SPA + SSR + 外部 RS を含む完全形を反映、N17 を追加 |

**重要な発見**: Cognito では実現できない 4 パターン（**Token Exchange / Device Code / SAML IdP 発行 / mTLS**）のいずれかが要件にあれば、**Keycloak 必須**となる。要件定義の Phase A/B でこれらの要否を確認することが、Cognito vs Keycloak 選定の決め手。

---

## 3. 不足箇所の分析（重要度順）

### 3.1 要件定義に進む上で不足している事項

#### 【Critical】本番環境との差分が未整理

| 項目 | PoC での状態 | 本番で必要なこと | 影響度 |
|------|-------------|-----------------|--------|
| IdP | Auth0 Free（Entra ID 代替） | 実際の Entra ID / Okta 接続 | **高** — フェデレーション挙動が異なる可能性 |
| HTTPS | Keycloak HTTP:80 | ACM 証明書 + HTTPS 必須 | **高** — start --optimized 必須化 |
| マルチアカウント | 1 アカウント 2 User Pool | 本番は組織単位の AWS アカウント分離 | **高** — IAM・ネットワーク設計が異なる |
| DR 自動フェイルオーバー | 手動切替のみ検証 | Route 53 ヘルスチェック + 自動切替 | **高** — RTO/RPO の確定が必要 |
| HA 構成 | ECS タスク 1 台 | ECS Auto Scaling + Multi-AZ | **中** — 可用性要件次第 |
| カスタムドメイン | localhost / ALB DNS | 認証ドメイン（auth.example.com） | **中** — Cookie・CORS・証明書に影響 |
| **WAF** | **未導入**（IP 制限のみ） | **ALB regional WAF / CloudFront global WAF 必須** | **高** — 攻撃検知・レート制限・ボット対策。N10 |
| **CloudFront** | **未導入**（ALB 直接） | **導入有無を要件定義で判断**（HTTPS/WAF/Shield 一元化の器） | **中** — ドメイン戦略と統合判断。N16 |
| 監視・ログ | CloudWatch 基本のみ | 統合監視・アラート・監査ログ | **中** — 運用要件次第 |
| データ暗号化 | RDS 暗号化なし（PoC） | KMS 暗号化必須（コンプライアンス） | **中** |
| バックアップ | 手動スナップショット | 自動バックアップ・PITR | **中** |
| Cognito 料金プラン | 未選択（Lite/Essentials/Plus） | MAU 見積もりに基づく選択 | **低** — 後から変更可能 |

#### 【High】技術的に未検証の領域

| 項目 | 現状 | 要件定義での確認ポイント |
|------|------|------------------------|
| Entra ID 実接続 | Auth0 で代替検証 | 実際の OIDC メタデータ・クレーム構造の違い |
| Okta 接続 | 未検証 | 2 社目の IdP 追加パターン確認 |
| LDAP 連携 | Keycloak のみ対応（ADR なし） | 顧客に LDAP のみの IdP がある場合の対応 |
| トークン失効（Revocation） | 検証なし | リフレッシュトークンの即時無効化要件 |
| **SSR バックエンド認証**（Confidential Client） | 未検証 | Next.js / Spring MVC 等の SSR 連携。詳細: [auth-patterns.md §2.2](../common/auth-patterns.md) |
| **M2M（Client Credentials）** | 未検証 | バッチ・連携処理の必須要件。Cognito では Resource Server + 課金あり |
| **Token Exchange（RFC 8693）** | 未検証 | マイクロサービス間ユーザー文脈伝播。**Cognito 非対応 → Keycloak 必須要因** |
| **Device Code Flow** | 未検証 | CLI / IoT 連携。**Cognito 非対応 → Keycloak 必須要因** |
| **SAML IdP 発行** | 未検証 | レガシー業務システム向け。**Cognito 非対応 → Keycloak 必須要因** |
| **mTLS Client Auth** | 未検証 | FAPI 準拠。**Cognito 非対応 → Keycloak 必須要因** |
| セッション管理 | 参考資料レベル | セッションタイムアウト・強制ログアウトの仕様 |
| パスワードポリシー | Cognito デフォルト | 顧客ごとのパスワード要件の違い |
| アカウントロック | 未検証 | ブルートフォース対策の要件 |
| SCIM プロビジョニング | 未検証 | ユーザー同期の自動化要件 |
| API スロットリング | 未検証 | Cognito API の Rate Limit（40 req/s） |

#### 【Medium】運用・組織面の未整理事項

| 項目 | 現状 | 確認が必要なこと |
|------|------|-----------------|
| 共有基盤の運用体制 | 未定義 | 誰が IdP を管理するか（専任 / 兼任） |
| SLA 定義 | 未定義 | 認証基盤の可用性目標（99.9%? 99.99%?） |
| インシデント対応 | 未定義 | 認証障害時の連絡体制・復旧手順 |
| 変更管理 | 未定義 | IdP 追加・クレーム変更のリードタイム |
| テナントオンボーディング | 概念設計のみ | 顧客追加の具体的フロー・承認プロセス |
| コスト配賦 | 未定義 | 利用システムへのコスト配分方法 |
| セキュリティ監査 | 未定義 | 監査ログの保存期間・アクセス制御 |
| コンプライアンス | 未定義 | 個人情報保護法・GDPR・SOC2 対応範囲 |

#### 【Low】ドキュメント整備の改善

| 項目 | 対応内容 |
|------|---------|
| Cognito vs Keycloak 判断マトリクス | PoC 結果を基にした最終判断材料の整理 |
| Phase 9（Keycloak Protocol Mapper） | Keycloak 側のクレームマッピング未実装 |
| パフォーマンステスト計画 | 負荷試験のシナリオ・ツール選定 |
| 移行計画（既存認証 → 新基盤） | 既存システムからの移行戦略 |

---

## 4. PoC から得られた主要知見

### 4.1 Cognito vs Keycloak 比較サマリー

| 評価軸 | Cognito | Keycloak | PoC での確認事項 |
|--------|---------|----------|-----------------|
| **初期コスト** | ◎ $0 | △ $940/月〜 | インフラ常時稼働コスト |
| **スケールコスト** | △ MAU 課金（連携 $0.015/人） | ◎ 固定費のみ | 損益分岐: 175,000 MAU |
| **DR コスト** | ◎ $0.50/月 + MAU | × $890/月〜 | Keycloak DR は常時稼働必要 |
| **運用負荷** | ◎ フルマネージド | × 自前運用（ECS/RDS/バージョン管理） | パッチ適用・スケーリング |
| **カスタマイズ性** | △ 制約あり（Pre Token Lambda） | ◎ 自由度高い（Protocol Mapper） | クレーム変換の柔軟性 |
| **マルチ IdP** | △ 手動 IdP 指定必要 | ◎ ログイン画面に IdP 自動表示 | UX の違い |
| **MFA** | ○ TOTP/SMS | ◎ TOTP/WebAuthn/条件付き OTP | 細粒度制御 |
| **SSO** | △ 同一 User Pool 内のみ | ◎ Realm 内 + Back-Channel Logout | ログアウト完全性 |
| **LDAP 対応** | × 非対応 | ◎ User Federation | レガシー IdP 接続 |
| **可用性 SLA** | ◎ 99.9%（AWS 保証） | △ 自前設計 | HA 構成の設計負荷 |

### 4.2 意思決定に必要な追加情報

要件定義で確定すべき判断材料：

1. **想定 MAU 規模** → コスト損益分岐判断（175,000 MAU）
2. **顧客 IdP の種類** → Entra ID のみ？ Okta？ LDAP？ → Cognito の LDAP 非対応が致命的か
3. **可用性要件** → 99.9% で足りるか、99.99% が必要か → Keycloak HA の設計コスト
4. **DR 要件** → RTO/RPO の具体値 → Cognito なら低コスト、Keycloak なら高コスト
5. **カスタマイズ頻度** → クレーム追加・IdP 追加の頻度 → Keycloak の柔軟性が必要か
6. **コンプライアンス要件** → データ所在地・監査ログ → 両者で対応可能だが設計が異なる

---

## 5. PoC 成果物の資産価値

### 5.1 本番に引き継げる成果物

| 成果物 | 再利用度 | 備考 |
|--------|---------|------|
| Lambda Authorizer（index.py） | ◎ | マルチイシュア対応済。イシュア追加で拡張可 |
| Terraform モジュール（infra/） | ○ | 構造は流用可能。環境変数・ネットワーク設計は要修正 |
| 認可アーキテクチャ設計 | ◎ | Pattern 2（固定クレーム + サービス解釈）は本番適用可 |
| ADR 9 件 | ◎ | 意思決定の履歴として永続的に有用 |
| Identity Broker パターン設計 | ◎ | マルチ IdP スケーリングの設計指針 |
| JWKS 公開判断 | ◎ | セキュリティレビューの根拠として引用可 |
| テストシナリオ | ○ | 本番テスト計画のベースライン |
| React SPA（app/） | △ | PoC 用。本番 SPA は別途開発 |

### 5.2 本番では作り直しが必要なもの

| 成果物 | 理由 |
|--------|------|
| ネットワーク設計 | VPC・サブネット・セキュリティグループは本番設計が必要 |
| Auth0 設定 | Entra ID / Okta に置き換え |
| Keycloak Dockerfile | start --optimized + HTTPS 対応が必要 |
| CORS 設定 | localhost → 本番ドメイン |
| API Gateway 設計 | エンドポイント構成は業務要件次第 |

---

## 6. 総合評価

### PoC としての完成度: **A（優秀）**

- 8 Phase すべてで実動検証が完了
- Cognito / Keycloak の比較が定量的（コスト）・定性的（運用・機能）の両面で実施済み
- 本番設計に直結する認可アーキテクチャ・Identity Broker パターンが確立
- 意思決定の根拠が ADR として構造化されている

### 要件定義に進む準備状況: **B+（概ね準備完了、一部補完が必要）**

- 技術検証は十分だが、本番との差分整理が必要
- 運用・組織面の要件が未定義（これは要件定義フェーズの本来の仕事）
- Entra ID 実接続の未検証がリスク要因として残る
