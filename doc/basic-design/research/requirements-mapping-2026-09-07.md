# 要件 × 工程のマッピング

- **日付**: 2026-09-07（第 2 版）
- **要件 177 件**を行、工程を列にした。**この表だけで読み切れるよう、項目・種別・概要・担当範囲を並べた**
- 各セルには対応する WBS の ID が入る。空欄はその工程に作業が無いことを意味する
- **反映用**: `wbs-text/SHEET_要件マッピング.tsv`（10 列）

## 列の構成（2026-09-07 改）

担当範囲の 1 列を **3 列に分けた**。「やるかどうか」「どこに作るか」「誰が作るか」は別の軸なので、分けた方が絞り込みやすい。

| 列 | 値 | 件数 |
|---|---|---|
| **要件実現対象** | 対象 154 ／ 対象外 23 | Phase 1 でその要件を満たすかどうか |
| **構築場所** | Keycloak-Broker 117 ／ Keycloak-IdP 15 ／ その他 22 ／ —（対象外）23 | どこに作るか。「その他」はアプリ側のシステムや顧客側 |
| **担当** | インフラ 117 ／ アプリ 36 ／ 顧客 1 ／ —（対象外）23 | 誰が作るか |

全 14 列は 要件ID / 種別 / 優先度 / 要件実現対象 / 構築場所 / 担当 / 担当の理由 / 項目 / 概要 / ① 基本設計 / ② 詳細設計 / ③ 製造 / ④ テスト / 状況。

> **2026-09-07 変更**: 別シートにする予定だった「要件一覧」は**作らないことにした**。優先度と担当の理由をこの表に取り込み、分類（要件ID の接頭辞で分かる）と出典の節（本書で管理）を落とした。**要件を見るシートは 1 枚だけ**になる。

## 状況

| 状況 | 件数 | 意味 |
|---|---:|---|
| 全工程あり | 100 | 本基盤の 4 工程すべてに作業がある |
| 🔺 一部の工程のみ | 8 | 文書で完結するなど、空欄で正しいもの |
| アプリ側で実施 | 25 | 本基盤の WBS には無い。アプリ側の WBS で管理する |
| アプリ側で実施（本基盤にも 4 工程あり） | 11 | 主体はアプリだが、本基盤側にも関わる作業がある |
| 顧客側で実施 | 1 | 顧客IdP 側で満たす |
| Phase 1 では作らない | 23 | 対象外 |
| 別シートで管理（コスト見積もり） | 9 | 見積りの話で、作る作業が無い |
| **計** | **177** | |

**インフラ担当の 117 件のうち、100 件が全工程そろい、8 件が一部のみ、どの工程にも無いものは 0 件。**

## 今回足した消去まわりの行

| 工程 | ID | 項目 | 人日 |
|---|---|---|---:|
| ① 基本設計 | HD-24 | ユーザと記録の保持年数と消去の方針 | 1.5 |
| ① 基本設計 | HK-07 | 本人からの開示・削除請求への対応手順 | 1 |
| ② 詳細設計 | — | 保持期間と消去の実装設計 | 1.5 |
| ② 詳細設計 | — | 開示と削除の求めへの対応の実装設計 | 1 |
| ③ 製造 | — | 消去処理の実装 | 2 |
| ③ 製造 | — | 開示と削除の手段の実装 | 1.5 |
| ④ テスト | — | 保持期間と消去 | 2 |
| ④ テスト | — | 本人からの開示・削除請求への対応 | 1.5 |

→ **FR-USER-011（ユーザ削除時の関連データ削除）と NFR-COMP-009（個人データ削除権）が全工程そろった**。

## 工程の合計

| 工程 | 行数 | 人日 |
|---|---:|---:|
| ① 基本設計 | 147 | 全量 218.5 / 対象 205.5 |
| ② 詳細設計 | 76 | 174.5 |
| ③ 製造 | 90 | 259 |
| ④ テスト | 88 | 331 |
| **計** | | **970** |

## 🔺 一部の工程にしかない 8 件（いずれも意図どおり）

| 要件ID | 項目 | ① | ② | ③ | ④ | なぜ空欄でよいか |
|---|---|:-:|:-:|:-:|:-:|---|
| NFR-AVL-001 | サービス稼働率 SLA | ○ | — | — | ○ | 顧客への約束を書き、実測で確かめる。作る作業は無い |
| NFR-PERF-008 | データベースの応答時間 | ○ | ○ | — | ○ | 設定値の設計まで。作る対象はデータベースの構築行に含まれる |
| NFR-SCL-004 | 顧客IdP 追加の所要時間 | ○ | — | ○ | ○ | 接続登録の実装で満たす。専用の詳細設計は不要 |
| NFR-SCL-007 | データベースの増強 | ○ | ○ | — | ○ | 同上 |
| NFR-OPS-007 | 設定変更の進め方 | ○ | — | — | — | 運用の取り決め。実装も試験も無い |
| NFR-OPS-008 | 障害対応の体制 | ○ | — | ○ | ○ | 体制の設計と手順書。実装は通知の設定のみ |
| NFR-OPS-009 | 運用にかかる人手 | ○ | — | — | — | 運用（定常）シートが受け皿 |
| NFR-OPS-011 | 顧客追加の所要時間の約束 | ○ | — | ○ | ○ | 接続登録の実装で満たす |

## 全 177 件

| 要件ID | 項目 | 種別 | 担当範囲 | ① | ② | ③ | ④ | 状況 |
|---|---|---|---|:-:|:-:|:-:|:-:|---|
| FR-AUTH-001 | ID/PW 認証（ローカルユーザー） | 機能 | Keycloak-IdP | ○ | ○ | ○ | ○ | Keycloak-IdP の責務 |
| FR-AUTH-002 | Authorization Code + PKCE（SPA /  | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-AUTH-003 | Authorization Code + client_secr | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-AUTH-004 | Client Credentials（M2M） | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-AUTH-005 | Token Exchange（RFC 8693） | 機能 | 対象外 | — | — | — | — | Phase 1 では作らない |
| FR-AUTH-006 | Device Code Flow（画面のない機器・CLI 向けロ | 機能 | 対象外 | — | — | — | — | Phase 1 では作らない |
| FR-AUTH-007 | mTLS Client Authentication（RFC 8 | 機能 | 対象外 | — | — | — | — | Phase 1 では作らない |
| FR-AUTH-008 | ROPC（Password Grant） | 機能 | 対象外 | — | — | — | — | Phase 1 では作らない |
| FR-AUTH-009 | パスワードポリシー（最小長・複雑性） | 機能 | Keycloak-IdP | ○ | ○ | ○ | ○ | Keycloak-IdP の責務 |
| FR-AUTH-010 | パスワード履歴（N 個と一致禁止） | 機能 | Keycloak-IdP | ○ | ○ | ○ | ○ | Keycloak-IdP の責務 |
| FR-AUTH-011 | アカウントロック（連続失敗） | 機能 | Keycloak-IdP | ○ | ○ | ○ | ○ | Keycloak-IdP の責務 |
| FR-AUTH-012 | パスワード有効期限 | 機能 | Keycloak-IdP | ○ | ○ | ○ | ○ | Keycloak-IdP の責務 |
| FR-AUTH-013 | セルフサービスパスワードリセット | 機能 | Keycloak-IdP | — | — | — | — | Keycloak-IdP の責務 |
| FR-AUTH-014 | 初期パスワード強制変更 | 機能 | Keycloak-IdP | — | — | — | — | Keycloak-IdP の責務 |
| FR-AUTH-015 | DPoP（RFC 9449、送信者に縛った JWT） | 機能 | 対象外 | — | — | — | — | Phase 1 では作らない |
| FR-FED-001 | Auth0 OIDC IdP 連携 | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-FED-002 | Entra ID（Azure AD）OIDC 連携 | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-FED-003 | Okta OIDC 連携 | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-FED-004 | Google Workspace OIDC 連携 | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-FED-005 | SAML 2.0 IdP として受け入れ（SP モード） | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-FED-006 | SAML 2.0 IdP として発行（IdP モード） | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-FED-007 | LDAP / AD 直接連携 | 機能 | 対象外 | — | — | — | — | Phase 1 では作らない |
| FR-FED-008 | JIT プロビジョニング | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-FED-009 | 属性マッピング / クレーム変換 | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-FED-010 | 複数 IdP 並行運用（マルチテナント） | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-FED-011 | 顧客追加時のオンボーディングフロー | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-FED-012 | フェデレーション時の MFA 重複回避 | 機能 | 顧客IdP | — | — | — | ○ | 顧客IdP の責務 |
| FR-FED-013 | ログイン画面で IdP 選択 UX | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-FED-014 | Custom Domain での federation | 機能 | 対象外 | — | — | — | — | Phase 1 では作らない |
| FR-MFA-001 | TOTP（Google Authenticator 等） | 機能 | Keycloak-IdP | — | — | — | — | Keycloak-IdP の責務 |
| FR-MFA-002 | WebAuthn / FIDO2（Passkeys） | 機能 | Keycloak-IdP | — | — | — | — | Keycloak-IdP の責務 |
| FR-MFA-003 | SMS OTP | 機能 | 対象外 | — | — | — | — | Phase 1 では作らない |
| FR-MFA-004 | メール OTP | 機能 | 対象外 | — | — | — | — | Phase 1 では作らない |
| FR-MFA-005 | バックアップコード | 機能 | Keycloak-IdP | — | — | — | — | Keycloak-IdP の責務 |
| FR-MFA-006 | 条件付き MFA（IP / リスクベース） | 機能 | 対象外 | — | — | — | — | Phase 1 では作らない |
| FR-MFA-007 | MFA 強制 / 任意の切替（ロール単位） | 機能 | Keycloak-IdP | — | — | — | — | Keycloak-IdP の責務 |
| FR-MFA-008 | 端末記憶（Trusted Device） | 機能 | 対象外 | — | — | — | — | Phase 1 では作らない |
| FR-MFA-009 | 管理者の MFA 強制 | 機能 | Keycloak-IdP | — | — | — | — | Keycloak-IdP の責務 |
| FR-SSO-001 | 同一 IdP 内の複数 Client 間 SSO | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-SSO-002 | Auth0/Entra 経由のクロス IdP SSO | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-SSO-003 | ローカルログアウト（アプリ Cookie 削除のみ） | 機能 | アプリ | ○ | ○ | ○ | ○ | アプリ の責務 |
| FR-SSO-004 | IdP セッション破棄（OIDC RP-Initiated Lo | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-SSO-005 | フェデレーション IdP セッション破棄（連動ログアウト） | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-SSO-006 | Front-Channel Logout | 機能 | 対象外 | — | — | — | — | Phase 1 では作らない |
| FR-SSO-007 | Back-Channel Logout（RFC 8606） | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-SSO-008 | セッションタイムアウト設定 | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-SSO-009 | アクセストークン強制無効化（Revocation） | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-SSO-010 | 強制全セッション破棄（管理者操作） | 機能 | アプリ | — | — | — | — | アプリ の責務 |
| FR-AUTHZ-001 | JWT クレームベース認可 | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-AUTHZ-002 | tenant_id によるテナント分離 | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-AUTHZ-003 | roles クレームによるロール認可 | 機能 | アプリ | — | — | — | — | アプリ の責務 |
| FR-AUTHZ-004 | ロール階層（継承） | 機能 | アプリ | — | — | — | — | アプリ の責務 |
| FR-AUTHZ-005 | scope ベース認可（M2M） | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-AUTHZ-006 | カスタムクレーム注入（任意属性） | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-AUTHZ-007 | API Gateway 認可統合（Lambda Authoriz | 機能 | アプリ | ○ | ○ | ○ | ○ | アプリ の責務 |
| FR-AUTHZ-008 | マルチイシュア対応（複数 User Pool / Realm） | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-AUTHZ-009 | リソースレベル認可（UMA 2.0 / Fine-grained | 機能 | アプリ | — | — | — | — | アプリ の責務 |
| FR-AUTHZ-010 | 動的属性ベース認可（ABAC） | 機能 | アプリ | — | — | — | — | アプリ の責務 |
| FR-USER-001 | ユーザー作成 / 更新 / 削除（CRUD） | 機能 | アプリ | — | — | — | — | アプリ の責務 |
| FR-USER-002 | カスタム属性（任意フィールド） | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-USER-003 | SCIM 2.0 プロビジョニング | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-USER-004 | セルフサービスプロフィール編集 | 機能 | Keycloak-IdP | ○ | ○ | ○ | ○ | Keycloak-IdP の責務 |
| FR-USER-005 | ユーザー検索・一覧 | 機能 | アプリ | — | — | — | — | アプリ の責務 |
| FR-USER-006 | ユーザー有効化 / 無効化（suspend） | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-USER-007 | ユーザーグループ管理 | 機能 | 対象外 | ○ | — | — | — | Phase 1 では作らない |
| FR-USER-008 | ロール割り当て | 機能 | アプリ | — | — | — | — | アプリ の責務 |
| FR-USER-009 | バルクインポート（CSV / JSON） | 機能 | アプリ | — | — | — | — | アプリ の責務 |
| FR-USER-010 | ユーザーパスワード強制リセット | 機能 | Keycloak-IdP | — | — | — | — | Keycloak-IdP の責務 |
| FR-USER-011 | ユーザー削除時の関連データ削除（GDPR 等） | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-USER-012 | ユーザー作成時の招待メール | 機能 | アプリ | — | — | — | — | アプリ の責務 |
| FR-ADMIN-001 | 管理コンソール UI | 機能 | アプリ | — | — | — | — | アプリ の責務 |
| FR-ADMIN-002 | テナント追加・削除 | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-ADMIN-003 | IdP 追加・削除・更新 | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-ADMIN-004 | クライアント（App）管理 | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-ADMIN-005 | ロール定義管理 | 機能 | アプリ | — | — | — | — | アプリ の責務 |
| FR-ADMIN-006 | パーミッション管理（細粒度） | 機能 | アプリ | — | — | — | — | アプリ の責務 |
| FR-ADMIN-007 | 監査ログ閲覧 | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-ADMIN-008 | 設定変更履歴 | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-ADMIN-009 | テナント別設定の分離 | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-ADMIN-010 | 管理者ロール（RBAC for Admin） | 機能 | アプリ | — | — | — | — | アプリ の責務 |
| FR-ADMIN-011 | テナント管理者の委譲（顧客の自社運用） | 機能 | アプリ | — | — | — | — | アプリ の責務 |
| FR-ADMIN-012 | カスタマイズ可能なログイン UI | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-INT-001 | OIDC 1.0 / OAuth 2.0 標準準拠 | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-INT-002 | OIDC Discovery（`.well-known`） | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-INT-003 | JWKS 公開エンドポイント | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-INT-004 | SAML 2.0 メタデータ | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-INT-005 | Webhook イベント通知（user.created 等） | 機能 | 対象外 | — | — | — | — | Phase 1 では作らない |
| FR-INT-006 | 管理 REST API | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-INT-007 | API Gateway / Lambda Authorizer  | 機能 | アプリ | ○ | ○ | ○ | ○ | アプリ の責務 |
| FR-INT-008 | 監査ログ外部出力（CloudWatch / S3 / Kines | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-INT-009 | 監査ログ SIEM 連携（Splunk / Datadog） | 機能 | 対象外 | — | — | — | — | Phase 1 では作らない |
| FR-INT-010 | Terraform / IaC 管理 | 機能 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-AVL-001 | サービス稼働率 SLA | 非機 | Keycloak-Broker | ○ | — | — | ○ | 🔺 一部の工程のみ（文書で完結するものを含む） |
| NFR-AVL-002 | 計画メンテナンス窓 | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-AVL-003 | マルチ AZ 配置 | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-AVL-004 | 自動復旧（コンテナ障害） | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-AVL-005 | 単一障害点の排除 | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-AVL-006 | デプロイ時のダウンタイム | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-PERF-001 | 認証応答時間（P50 / P95 / P99） | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-PERF-002 | 同時認証リクエスト処理能力 | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-PERF-003 | Lambda Authorizer 応答時間 | 非機 | アプリ | ○ | ○ | ○ | ○ | アプリ の責務 |
| NFR-PERF-004 | JWT 検証スループット | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-PERF-005 | JWKS キャッシュ TTL | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-PERF-006 | API Gateway スロットリング | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-PERF-007 | 認証ピーク時間帯への耐性 | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-PERF-008 | DB 応答時間（Keycloak のみ） | 非機 | Keycloak-Broker | ○ | ○ | — | ○ | 🔺 一部の工程のみ（文書で完結するものを含む） |
| NFR-SCL-001 | MAU スケール上限 | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-SCL-002 | ピーク時同時セッション数 | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-SCL-003 | 顧客テナント数（IdP 数）スケール | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-SCL-004 | IdP 追加リードタイム | 非機 | Keycloak-Broker | ○ | — | ○ | ○ | 🔺 一部の工程のみ（文書で完結するものを含む） |
| NFR-SCL-005 | 自動スケーリング | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-SCL-006 | マルチリージョン対応（複数地域での同時稼働） | 非機 | 対象外 | — | — | — | — | Phase 1 では作らない |
| NFR-SCL-007 | データベーススケール（Keycloak） | 非機 | Keycloak-Broker | ○ | ○ | — | ○ | 🔺 一部の工程のみ（文書で完結するものを含む） |
| NFR-SEC-001 | 通信暗号化 | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-SEC-002 | データ暗号化（at-rest） | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-SEC-003 | トークン署名アルゴリズム | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-SEC-004 | Access Token TTL | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-SEC-005 | Refresh Token TTL | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-SEC-006 | ID Token TTL | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-SEC-007 | Refresh Token Rotation | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-SEC-008 | トークン失効（Revocation） | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-SEC-009 | パスワード保管アルゴリズム | 非機 | Keycloak-IdP | ○ | ○ | ○ | ○ | Keycloak-IdP の責務 |
| NFR-SEC-010 | ブルートフォース対策 | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-SEC-011 | WAF 適用 | 非機 | 対象外 | — | — | — | ○ | Phase 1 では作らない |
| NFR-SEC-012 | DDoS 対策 | 非機 | 対象外 | — | — | — | — | Phase 1 では作らない |
| NFR-SEC-013 | ペネトレーションテスト | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-SEC-014 | 脆弱性スキャン | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-SEC-015 | シークレット管理 | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-SEC-016 | ネットワーク分離（Private Subnet） | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-SEC-017 | 管理画面アクセス制御 | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-SEC-018 | JWKS エンドポイント保護 | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-SEC-019 | 内部通信の認証（Lambda → Keycloak） | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-SEC-020 | セッション固定攻撃対策 | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-DR-001 | RTO（目標復旧時間） | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-DR-002 | RPO（目標復旧地点） | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-DR-003 | フェイルオーバー方式 | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-DR-004 | バックアップ保存期間 | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-DR-005 | PITR（Point-in-Time Recovery） | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-DR-006 | クロスリージョンバックアップ | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-DR-007 | DR 訓練 | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-DR-008 | DR 切替時のセッション維持 | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-OPS-001 | 監視・メトリクス | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-OPS-002 | アラート通知 | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-OPS-003 | ログ保存期間 | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-OPS-004 | ログ検索性 | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-OPS-005 | バージョンアップ方針 | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-OPS-006 | パッチ適用（CVE 対応） | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-OPS-007 | 設定変更プロセス | 非機 | Keycloak-Broker | ○ | — | — | — | 🔺 一部の工程のみ（文書で完結するものを含む） |
| NFR-OPS-008 | インシデント対応体制 | 非機 | Keycloak-Broker | ○ | — | ○ | ○ | 🔺 一部の工程のみ（文書で完結するものを含む） |
| NFR-OPS-009 | 運用工数（人月） | 非機 | Keycloak-Broker | ○ | — | — | — | 🔺 一部の工程のみ（文書で完結するものを含む） |
| NFR-OPS-010 | デプロイ自動化（CI/CD） | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-OPS-011 | テナント追加の運用 SLA | 非機 | Keycloak-Broker | ○ | — | ○ | ○ | 🔺 一部の工程のみ（文書で完結するものを含む） |
| NFR-COMP-001 | 個人情報保護法対応 | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-COMP-002 | GDPR / CCPA（海外展開時） | 非機 | 対象外 | — | — | — | — | Phase 1 では作らない |
| NFR-COMP-003 | SOC 2 Type II | 非機 | 対象外 | — | — | — | — | Phase 1 では作らない |
| NFR-COMP-004 | ISO 27001 | 非機 | 対象外 | — | — | — | — | Phase 1 では作らない |
| NFR-COMP-005 | PCI DSS（金融） | 非機 | 対象外 | — | — | — | — | Phase 1 では作らない |
| NFR-COMP-006 | FIPS 140-3 認定（暗号モジュール認定、旧 140-2） | 非機 | 対象外 | — | — | — | ○ | Phase 1 では作らない |
| NFR-COMP-007 | 監査ログ保存期間（法令要件） | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-COMP-008 | データ所在地（リージョン制限） | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-COMP-009 | 個人データ削除権（GDPR Right to Erasure） | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-COMP-010 | アクセス監査の追跡可能性 | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-COMP-011 | 暗号鍵のローテーションと所在の可視化 | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-COST-001 | 初期構築費 | 非機 | Keycloak-Broker | — | — | — | — | 別シートで管理（コスト見積もり） |
| NFR-COST-002 | 月額固定インフラ費 | 非機 | Keycloak-Broker | — | — | — | — | 別シートで管理（コスト見積もり） |
| NFR-COST-003 | MAU あたりコスト（連携） | 非機 | Keycloak-Broker | — | — | — | — | 別シートで管理（コスト見積もり） |
| NFR-COST-004 | DR 追加月額 | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 別シートで管理（コスト見積もり） |
| NFR-COST-005 | 運用人件費 | 非機 | Keycloak-Broker | ○ | — | — | — | 別シートで管理（コスト見積もり） |
| NFR-COST-006 | RHBK サブスクリプション | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 別シートで管理（コスト見積もり） |
| NFR-COST-007 | 損益分岐 MAU（連携のみ） | 非機 | Keycloak-Broker | — | — | — | — | 別シートで管理（コスト見積もり） |
| NFR-COST-008 | 3 年 TCO（10 万 MAU 想定） | 非機 | Keycloak-Broker | — | — | — | — | 別シートで管理（コスト見積もり） |
| NFR-COST-009 | 3 年 TCO（50 万 MAU 想定） | 非機 | Keycloak-Broker | — | — | — | — | 別シートで管理（コスト見積もり） |
| NFR-MIG-001 | 既存認証システムからのユーザー移行 | 非機 | アプリ | — | — | — | — | アプリ の責務 |
| NFR-MIG-002 | パスワード移行（ハッシュ持ち越し） | 非機 | アプリ | — | — | — | — | アプリ の責務 |
| NFR-MIG-003 | ベンダーロックイン回避 | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-MIG-004 | データエクスポート | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-MIG-005 | 段階的移行（並行稼働） | 非機 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
