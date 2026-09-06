# 要件 × 工程のマッピング

- **日付**: 2026-09-07
- **要件 177 件**を行、**① 基本設計 / ② 詳細設計 / ③ 製造 / ④ テスト**を列にした
- 各セルには対応する WBS の ID を入れた。**空欄はその工程に作業が無い**ことを意味する
- **反映用**: `wbs-text/SHEET_要件マッピング.tsv`（要件一覧には種別の列を追加した）

## 状況

| 状況 | 件数 |
|---|---:|
| 全工程あり | 100 |
| 🔺 一部の工程のみ | 10 |
| 🔴 どの工程にも無い | 7 |
| 他者責務（Keycloak-IdP） | 15 |
| 他者責務（アプリ） | 21 |
| 他者責務（顧客IdP） | 1 |
| 対象外 | 23 |
| **計** | **177** |

**本基盤が作る 117 件**のうち、全工程そろっているのが 100 件、一部のみが 10 件、どの工程にも無いのが 7 件。

## 🔴 本基盤が作るのに、どの工程にも作業が無い要件

| 要件ID | 項目 | 優先度 |
|---|---|---|
| FR-USER-011 | ユーザー削除時の関連データ削除（GDPR 等） | Should |
| NFR-COST-001 | 初期構築費 | 推奨値あり |
| NFR-COST-002 | 月額固定インフラ費 | 推奨値あり |
| NFR-COST-003 | MAU あたりコスト（連携） | 推奨値あり |
| NFR-COST-007 | 損益分岐 MAU（連携のみ） | 推奨値あり |
| NFR-COST-008 | 3 年 TCO（10 万 MAU 想定） | 推奨値あり |
| NFR-COST-009 | 3 年 TCO（50 万 MAU 想定） | 推奨値あり |

## 🔺 一部の工程にしか作業が無い要件

| 要件ID | 項目 | ① | ② | ③ | ④ |
|---|---|:-:|:-:|:-:|:-:|
| NFR-AVL-001 | サービス稼働率 SLA | ○ | — | — | ○ |
| NFR-PERF-008 | DB 応答時間（Keycloak のみ） | ○ | ○ | — | ○ |
| NFR-SCL-004 | IdP 追加リードタイム | ○ | — | ○ | ○ |
| NFR-SCL-007 | データベーススケール（Keycloak） | ○ | ○ | — | ○ |
| NFR-OPS-007 | 設定変更プロセス | ○ | — | — | — |
| NFR-OPS-008 | インシデント対応体制 | ○ | — | ○ | ○ |
| NFR-OPS-009 | 運用工数（人月） | ○ | — | — | — |
| NFR-OPS-011 | テナント追加の運用 SLA | ○ | — | ○ | ○ |
| NFR-COMP-009 | 個人データ削除権（GDPR Right to Erasure） | — | — | — | ○ |
| NFR-COST-005 | 運用人件費 | ○ | — | — | — |

## 空欄の読み方（誤解を避けるため）

空欄には 3 種類ある。**どれも「抜け」ではない場合がある**ので、下の区別で読む。

| 種類 | 例 | 扱い |
|---|---|---|
| **見積りや契約の話で、作る作業が無い** | NFR-COST 系 6 件・NFR-OPS-009 運用工数 | コスト見積もりシートと運用（定常）シートが受け皿。**WBS に行を作る必要は無い** |
| **文書だけで完結する** | NFR-AVL-001 稼働率 SLA・NFR-OPS-007 設定変更プロセス | ① で書いて ④ で確認する。②③ が空欄で正しい |
| **🔴 本当に抜けている** | FR-USER-011 ユーザ削除時の関連データ削除・NFR-COMP-009 個人データ削除権 | §下の「確認したいこと」参照 |

## 確認したいこと

| # | 要件 | 論点 |
|---|---|---|
| **1** | **FR-USER-011 ユーザ削除時の関連データ削除**（Should） | 消去の方針は「ユーザと記録の保持・停止・消去の全体方針」に入れる想定だったが、その行はトリミングで落ちている。**保存期限切れデータの消去（F-BAT-09）も現在は機能一覧にあるだけで設計行が無い**。個人データの削除は法令にも関わるので、① に 1 行足すことを推す |
| **2** | **NFR-COMP-009 個人データ削除権** | ④ テストにはあるが ①②③ に無い。上と同じ行で受けられる |
| **3** | **NFR-COST 系 6 件** | コスト見積もりシートが受け皿でよいか。よければ「別シートで管理」と明記して、このマッピングでは対象外にしたい |

## 全 177 件

| 要件ID | 種別 | 項目 | 担当範囲 | ① | ② | ③ | ④ | 状況 |
|---|---|---|---|:-:|:-:|:-:|:-:|---|
| FR-AUTH-001 | 機能 | ID/PW 認証（ローカルユーザー） | Keycloak-IdP | ○ | ○ | ○ | ○ | 他者責務（Keycloak-IdP） |
| FR-AUTH-002 | 機能 | Authorization Code + PKCE（SPA / モバ | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-AUTH-003 | 機能 | Authorization Code + client_secret | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-AUTH-004 | 機能 | Client Credentials（M2M） | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-AUTH-005 | 機能 | Token Exchange（RFC 8693） | 対象外 | — | — | — | — | 対象外 |
| FR-AUTH-006 | 機能 | Device Code Flow（画面のない機器・CLI 向けログイ | 対象外 | — | — | — | — | 対象外 |
| FR-AUTH-007 | 機能 | mTLS Client Authentication（RFC 870 | 対象外 | — | — | — | — | 対象外 |
| FR-AUTH-008 | 機能 | ROPC（Password Grant） | 対象外 | — | — | — | — | 対象外 |
| FR-AUTH-009 | 機能 | パスワードポリシー（最小長・複雑性） | Keycloak-IdP | ○ | ○ | ○ | ○ | 他者責務（Keycloak-IdP） |
| FR-AUTH-010 | 機能 | パスワード履歴（N 個と一致禁止） | Keycloak-IdP | ○ | ○ | ○ | ○ | 他者責務（Keycloak-IdP） |
| FR-AUTH-011 | 機能 | アカウントロック（連続失敗） | Keycloak-IdP | ○ | ○ | ○ | ○ | 他者責務（Keycloak-IdP） |
| FR-AUTH-012 | 機能 | パスワード有効期限 | Keycloak-IdP | ○ | ○ | ○ | ○ | 他者責務（Keycloak-IdP） |
| FR-AUTH-013 | 機能 | セルフサービスパスワードリセット | Keycloak-IdP | — | — | — | — | 他者責務（Keycloak-IdP） |
| FR-AUTH-014 | 機能 | 初期パスワード強制変更 | Keycloak-IdP | — | — | — | — | 他者責務（Keycloak-IdP） |
| FR-AUTH-015 | 機能 | DPoP（RFC 9449、送信者に縛った JWT） | 対象外 | — | — | — | — | 対象外 |
| FR-FED-001 | 機能 | Auth0 OIDC IdP 連携 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-FED-002 | 機能 | Entra ID（Azure AD）OIDC 連携 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-FED-003 | 機能 | Okta OIDC 連携 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-FED-004 | 機能 | Google Workspace OIDC 連携 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-FED-005 | 機能 | SAML 2.0 IdP として受け入れ（SP モード） | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-FED-006 | 機能 | SAML 2.0 IdP として発行（IdP モード） | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-FED-007 | 機能 | LDAP / AD 直接連携 | 対象外 | — | — | — | — | 対象外 |
| FR-FED-008 | 機能 | JIT プロビジョニング | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-FED-009 | 機能 | 属性マッピング / クレーム変換 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-FED-010 | 機能 | 複数 IdP 並行運用（マルチテナント） | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-FED-011 | 機能 | 顧客追加時のオンボーディングフロー | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-FED-012 | 機能 | フェデレーション時の MFA 重複回避 | 顧客IdP | — | — | — | ○ | 他者責務（顧客IdP） |
| FR-FED-013 | 機能 | ログイン画面で IdP 選択 UX | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-FED-014 | 機能 | Custom Domain での federation | 対象外 | — | — | — | — | 対象外 |
| FR-MFA-001 | 機能 | TOTP（Google Authenticator 等） | Keycloak-IdP | — | — | — | — | 他者責務（Keycloak-IdP） |
| FR-MFA-002 | 機能 | WebAuthn / FIDO2（Passkeys） | Keycloak-IdP | — | — | — | — | 他者責務（Keycloak-IdP） |
| FR-MFA-003 | 機能 | SMS OTP | 対象外 | — | — | — | — | 対象外 |
| FR-MFA-004 | 機能 | メール OTP | 対象外 | — | — | — | — | 対象外 |
| FR-MFA-005 | 機能 | バックアップコード | Keycloak-IdP | — | — | — | — | 他者責務（Keycloak-IdP） |
| FR-MFA-006 | 機能 | 条件付き MFA（IP / リスクベース） | 対象外 | — | — | — | — | 対象外 |
| FR-MFA-007 | 機能 | MFA 強制 / 任意の切替（ロール単位） | Keycloak-IdP | — | — | — | — | 他者責務（Keycloak-IdP） |
| FR-MFA-008 | 機能 | 端末記憶（Trusted Device） | 対象外 | — | — | — | — | 対象外 |
| FR-MFA-009 | 機能 | 管理者の MFA 強制 | Keycloak-IdP | — | — | — | — | 他者責務（Keycloak-IdP） |
| FR-SSO-001 | 機能 | 同一 IdP 内の複数 Client 間 SSO | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-SSO-002 | 機能 | Auth0/Entra 経由のクロス IdP SSO | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-SSO-003 | 機能 | ローカルログアウト（アプリ Cookie 削除のみ） | アプリ | ○ | ○ | ○ | ○ | 他者責務（アプリ） |
| FR-SSO-004 | 機能 | IdP セッション破棄（OIDC RP-Initiated Logo | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-SSO-005 | 機能 | フェデレーション IdP セッション破棄（連動ログアウト） | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-SSO-006 | 機能 | Front-Channel Logout | 対象外 | — | — | — | — | 対象外 |
| FR-SSO-007 | 機能 | Back-Channel Logout（RFC 8606） | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-SSO-008 | 機能 | セッションタイムアウト設定 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-SSO-009 | 機能 | アクセストークン強制無効化（Revocation） | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-SSO-010 | 機能 | 強制全セッション破棄（管理者操作） | アプリ | — | — | — | — | 他者責務（アプリ） |
| FR-AUTHZ-001 | 機能 | JWT クレームベース認可 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-AUTHZ-002 | 機能 | tenant_id によるテナント分離 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-AUTHZ-003 | 機能 | roles クレームによるロール認可 | アプリ | — | — | — | — | 他者責務（アプリ） |
| FR-AUTHZ-004 | 機能 | ロール階層（継承） | アプリ | — | — | — | — | 他者責務（アプリ） |
| FR-AUTHZ-005 | 機能 | scope ベース認可（M2M） | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-AUTHZ-006 | 機能 | カスタムクレーム注入（任意属性） | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-AUTHZ-007 | 機能 | API Gateway 認可統合（Lambda Authorizer | アプリ | ○ | ○ | ○ | ○ | 他者責務（アプリ） |
| FR-AUTHZ-008 | 機能 | マルチイシュア対応（複数 User Pool / Realm） | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-AUTHZ-009 | 機能 | リソースレベル認可（UMA 2.0 / Fine-grained） | アプリ | — | — | — | — | 他者責務（アプリ） |
| FR-AUTHZ-010 | 機能 | 動的属性ベース認可（ABAC） | アプリ | — | — | — | — | 他者責務（アプリ） |
| FR-USER-001 | 機能 | ユーザー作成 / 更新 / 削除（CRUD） | アプリ | — | — | — | — | 他者責務（アプリ） |
| FR-USER-002 | 機能 | カスタム属性（任意フィールド） | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-USER-003 | 機能 | SCIM 2.0 プロビジョニング | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-USER-004 | 機能 | セルフサービスプロフィール編集 | Keycloak-IdP | ○ | ○ | ○ | ○ | 他者責務（Keycloak-IdP） |
| FR-USER-005 | 機能 | ユーザー検索・一覧 | アプリ | — | — | — | — | 他者責務（アプリ） |
| FR-USER-006 | 機能 | ユーザー有効化 / 無効化（suspend） | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-USER-007 | 機能 | ユーザーグループ管理 | 対象外 | ○ | — | — | — | 対象外 |
| FR-USER-008 | 機能 | ロール割り当て | アプリ | — | — | — | — | 他者責務（アプリ） |
| FR-USER-009 | 機能 | バルクインポート（CSV / JSON） | アプリ | — | — | — | — | 他者責務（アプリ） |
| FR-USER-010 | 機能 | ユーザーパスワード強制リセット | Keycloak-IdP | — | — | — | — | 他者責務（Keycloak-IdP） |
| FR-USER-011 | 機能 | ユーザー削除時の関連データ削除（GDPR 等） | Keycloak-Broker | — | — | — | — | 🔴 どの工程にも無い |
| FR-USER-012 | 機能 | ユーザー作成時の招待メール | アプリ | — | — | — | — | 他者責務（アプリ） |
| FR-ADMIN-001 | 機能 | 管理コンソール UI | アプリ | — | — | — | — | 他者責務（アプリ） |
| FR-ADMIN-002 | 機能 | テナント追加・削除 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-ADMIN-003 | 機能 | IdP 追加・削除・更新 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-ADMIN-004 | 機能 | クライアント（App）管理 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-ADMIN-005 | 機能 | ロール定義管理 | アプリ | — | — | — | — | 他者責務（アプリ） |
| FR-ADMIN-006 | 機能 | パーミッション管理（細粒度） | アプリ | — | — | — | — | 他者責務（アプリ） |
| FR-ADMIN-007 | 機能 | 監査ログ閲覧 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-ADMIN-008 | 機能 | 設定変更履歴 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-ADMIN-009 | 機能 | テナント別設定の分離 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-ADMIN-010 | 機能 | 管理者ロール（RBAC for Admin） | アプリ | — | — | — | — | 他者責務（アプリ） |
| FR-ADMIN-011 | 機能 | テナント管理者の委譲（顧客の自社運用） | アプリ | — | — | — | — | 他者責務（アプリ） |
| FR-ADMIN-012 | 機能 | カスタマイズ可能なログイン UI | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-INT-001 | 機能 | OIDC 1.0 / OAuth 2.0 標準準拠 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-INT-002 | 機能 | OIDC Discovery（`.well-known`） | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-INT-003 | 機能 | JWKS 公開エンドポイント | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-INT-004 | 機能 | SAML 2.0 メタデータ | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-INT-005 | 機能 | Webhook イベント通知（user.created 等） | 対象外 | — | — | — | — | 対象外 |
| FR-INT-006 | 機能 | 管理 REST API | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-INT-007 | 機能 | API Gateway / Lambda Authorizer 統合 | アプリ | ○ | ○ | ○ | ○ | 他者責務（アプリ） |
| FR-INT-008 | 機能 | 監査ログ外部出力（CloudWatch / S3 / Kinesis | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| FR-INT-009 | 機能 | 監査ログ SIEM 連携（Splunk / Datadog） | 対象外 | — | — | — | — | 対象外 |
| FR-INT-010 | 機能 | Terraform / IaC 管理 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-AVL-001 | 非機 | サービス稼働率 SLA | Keycloak-Broker | ○ | — | — | ○ | 🔺 一部の工程のみ |
| NFR-AVL-002 | 非機 | 計画メンテナンス窓 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-AVL-003 | 非機 | マルチ AZ 配置 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-AVL-004 | 非機 | 自動復旧（コンテナ障害） | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-AVL-005 | 非機 | 単一障害点の排除 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-AVL-006 | 非機 | デプロイ時のダウンタイム | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-PERF-001 | 非機 | 認証応答時間（P50 / P95 / P99） | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-PERF-002 | 非機 | 同時認証リクエスト処理能力 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-PERF-003 | 非機 | Lambda Authorizer 応答時間 | アプリ | ○ | ○ | ○ | ○ | 他者責務（アプリ） |
| NFR-PERF-004 | 非機 | JWT 検証スループット | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-PERF-005 | 非機 | JWKS キャッシュ TTL | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-PERF-006 | 非機 | API Gateway スロットリング | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-PERF-007 | 非機 | 認証ピーク時間帯への耐性 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-PERF-008 | 非機 | DB 応答時間（Keycloak のみ） | Keycloak-Broker | ○ | ○ | — | ○ | 🔺 一部の工程のみ |
| NFR-SCL-001 | 非機 | MAU スケール上限 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-SCL-002 | 非機 | ピーク時同時セッション数 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-SCL-003 | 非機 | 顧客テナント数（IdP 数）スケール | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-SCL-004 | 非機 | IdP 追加リードタイム | Keycloak-Broker | ○ | — | ○ | ○ | 🔺 一部の工程のみ |
| NFR-SCL-005 | 非機 | 自動スケーリング | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-SCL-006 | 非機 | マルチリージョン対応（複数地域での同時稼働） | 対象外 | — | — | — | — | 対象外 |
| NFR-SCL-007 | 非機 | データベーススケール（Keycloak） | Keycloak-Broker | ○ | ○ | — | ○ | 🔺 一部の工程のみ |
| NFR-SEC-001 | 非機 | 通信暗号化 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-SEC-002 | 非機 | データ暗号化（at-rest） | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-SEC-003 | 非機 | トークン署名アルゴリズム | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-SEC-004 | 非機 | Access Token TTL | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-SEC-005 | 非機 | Refresh Token TTL | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-SEC-006 | 非機 | ID Token TTL | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-SEC-007 | 非機 | Refresh Token Rotation | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-SEC-008 | 非機 | トークン失効（Revocation） | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-SEC-009 | 非機 | パスワード保管アルゴリズム | Keycloak-IdP | ○ | ○ | ○ | ○ | 他者責務（Keycloak-IdP） |
| NFR-SEC-010 | 非機 | ブルートフォース対策 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-SEC-011 | 非機 | WAF 適用 | 対象外 | — | — | — | ○ | 対象外 |
| NFR-SEC-012 | 非機 | DDoS 対策 | 対象外 | — | — | — | — | 対象外 |
| NFR-SEC-013 | 非機 | ペネトレーションテスト | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-SEC-014 | 非機 | 脆弱性スキャン | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-SEC-015 | 非機 | シークレット管理 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-SEC-016 | 非機 | ネットワーク分離（Private Subnet） | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-SEC-017 | 非機 | 管理画面アクセス制御 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-SEC-018 | 非機 | JWKS エンドポイント保護 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-SEC-019 | 非機 | 内部通信の認証（Lambda → Keycloak） | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-SEC-020 | 非機 | セッション固定攻撃対策 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-DR-001 | 非機 | RTO（目標復旧時間） | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-DR-002 | 非機 | RPO（目標復旧地点） | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-DR-003 | 非機 | フェイルオーバー方式 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-DR-004 | 非機 | バックアップ保存期間 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-DR-005 | 非機 | PITR（Point-in-Time Recovery） | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-DR-006 | 非機 | クロスリージョンバックアップ | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-DR-007 | 非機 | DR 訓練 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-DR-008 | 非機 | DR 切替時のセッション維持 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-OPS-001 | 非機 | 監視・メトリクス | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-OPS-002 | 非機 | アラート通知 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-OPS-003 | 非機 | ログ保存期間 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-OPS-004 | 非機 | ログ検索性 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-OPS-005 | 非機 | バージョンアップ方針 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-OPS-006 | 非機 | パッチ適用（CVE 対応） | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-OPS-007 | 非機 | 設定変更プロセス | Keycloak-Broker | ○ | — | — | — | 🔺 一部の工程のみ |
| NFR-OPS-008 | 非機 | インシデント対応体制 | Keycloak-Broker | ○ | — | ○ | ○ | 🔺 一部の工程のみ |
| NFR-OPS-009 | 非機 | 運用工数（人月） | Keycloak-Broker | ○ | — | — | — | 🔺 一部の工程のみ |
| NFR-OPS-010 | 非機 | デプロイ自動化（CI/CD） | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-OPS-011 | 非機 | テナント追加の運用 SLA | Keycloak-Broker | ○ | — | ○ | ○ | 🔺 一部の工程のみ |
| NFR-COMP-001 | 非機 | 個人情報保護法対応 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-COMP-002 | 非機 | GDPR / CCPA（海外展開時） | 対象外 | — | — | — | — | 対象外 |
| NFR-COMP-003 | 非機 | SOC 2 Type II | 対象外 | — | — | — | — | 対象外 |
| NFR-COMP-004 | 非機 | ISO 27001 | 対象外 | — | — | — | — | 対象外 |
| NFR-COMP-005 | 非機 | PCI DSS（金融） | 対象外 | — | — | — | — | 対象外 |
| NFR-COMP-006 | 非機 | FIPS 140-3 認定（暗号モジュール認定、旧 140-2） | 対象外 | — | — | — | ○ | 対象外 |
| NFR-COMP-007 | 非機 | 監査ログ保存期間（法令要件） | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-COMP-008 | 非機 | データ所在地（リージョン制限） | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-COMP-009 | 非機 | 個人データ削除権（GDPR Right to Erasure） | Keycloak-Broker | — | — | — | ○ | 🔺 一部の工程のみ |
| NFR-COMP-010 | 非機 | アクセス監査の追跡可能性 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-COMP-011 | 非機 | 暗号鍵のローテーションと所在の可視化 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-COST-001 | 非機 | 初期構築費 | Keycloak-Broker | — | — | — | — | 🔴 どの工程にも無い |
| NFR-COST-002 | 非機 | 月額固定インフラ費 | Keycloak-Broker | — | — | — | — | 🔴 どの工程にも無い |
| NFR-COST-003 | 非機 | MAU あたりコスト（連携） | Keycloak-Broker | — | — | — | — | 🔴 どの工程にも無い |
| NFR-COST-004 | 非機 | DR 追加月額 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-COST-005 | 非機 | 運用人件費 | Keycloak-Broker | ○ | — | — | — | 🔺 一部の工程のみ |
| NFR-COST-006 | 非機 | RHBK サブスクリプション | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-COST-007 | 非機 | 損益分岐 MAU（連携のみ） | Keycloak-Broker | — | — | — | — | 🔴 どの工程にも無い |
| NFR-COST-008 | 非機 | 3 年 TCO（10 万 MAU 想定） | Keycloak-Broker | — | — | — | — | 🔴 どの工程にも無い |
| NFR-COST-009 | 非機 | 3 年 TCO（50 万 MAU 想定） | Keycloak-Broker | — | — | — | — | 🔴 どの工程にも無い |
| NFR-MIG-001 | 非機 | 既存認証システムからのユーザー移行 | アプリ | — | — | — | — | 他者責務（アプリ） |
| NFR-MIG-002 | 非機 | パスワード移行（ハッシュ持ち越し） | アプリ | — | — | — | — | 他者責務（アプリ） |
| NFR-MIG-003 | 非機 | ベンダーロックイン回避 | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-MIG-004 | 非機 | データエクスポート | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
| NFR-MIG-005 | 非機 | 段階的移行（並行稼働） | Keycloak-Broker | ○ | ○ | ○ | ○ | 全工程あり |
