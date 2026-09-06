# 要件の一覧（工程マッピングの前段）

- **日付**: 2026-09-07
- **出典**: `doc/requirements/functional-requirements.md`（FR 91）、`non-functional-requirements.md`（NFR 85）、`proposal/fr/01-auth.md`（FR-AUTH-015 新規想定 1）
- **件数**: **177 件**
- **反映用**: `wbs-text/SHEET_要件一覧.tsv`

## 担当範囲の考え方

要件は Keycloak-IdP 側も作る前提で書かれているため、現在の分担（Keycloak-IdP は基盤だけ作って引き渡す／認可はこちらでは行わない／追加認証は IdP の責務）に合わせて振り直した。

| 担当範囲 | 意味 | 件数 |
|---|---|---:|
| **Keycloak-Broker** | 本基盤（基盤チーム）が作る | 117 |
| **Keycloak-IdP** | 基盤は基盤（ROSA）まで作って引き渡し、設定はアプリチーム | 15 |
| **顧客IdP** | 顧客側の責務 | 1 |
| **アプリ** | アプリチームの責務（管理画面・認可・移行） | 21 |
| **対象外** | Phase 1 では作らない | 23 |
| **計** | | **177** |

## 分類別

| 分類 | 件数 | Keycloak-Broker | Keycloak-IdP | 顧客IdP | アプリ | 対象外 |
|---|---:|---:|---:|---:|---:|---:|
| FR-AUTH 認証方式 | 15 | 3 | 7 | 0 | 0 | 5 |
| FR-FED フェデレーション | 14 | 11 | 0 | 1 | 0 | 2 |
| FR-MFA 多要素認証 | 9 | 0 | 5 | 0 | 0 | 4 |
| FR-SSO SSO・ログアウト | 10 | 7 | 0 | 0 | 2 | 1 |
| FR-AUTHZ 認可 | 10 | 5 | 0 | 0 | 5 | 0 |
| FR-USER ユーザ管理 | 12 | 4 | 2 | 0 | 5 | 1 |
| FR-ADMIN 管理機能 | 12 | 7 | 0 | 0 | 5 | 0 |
| FR-INT 外部連携 | 10 | 7 | 0 | 0 | 1 | 2 |
| NFR-AVL 可用性 | 6 | 6 | 0 | 0 | 0 | 0 |
| NFR-PERF 性能 | 8 | 7 | 0 | 0 | 1 | 0 |
| NFR-SCL 拡張性 | 7 | 6 | 0 | 0 | 0 | 1 |
| NFR-SEC セキュリティ | 20 | 17 | 1 | 0 | 0 | 2 |
| NFR-DR 災害復旧 | 8 | 8 | 0 | 0 | 0 | 0 |
| NFR-OPS 運用性 | 11 | 11 | 0 | 0 | 0 | 0 |
| NFR-COMP コンプライアンス | 11 | 6 | 0 | 0 | 0 | 5 |
| NFR-COST コスト | 9 | 9 | 0 | 0 | 0 | 0 |
| NFR-MIG 移行性 | 5 | 3 | 0 | 0 | 2 | 0 |
| **計** | **177** | **117** | **15** | **1** | **21** | **23** |

## 優先度

| 優先度 | 件数 |
|---|---:|
| 推奨値あり | 58 |
| Must | 51 |
| TBD | 29 |
| Should | 24 |
| Could | 8 |
| 不要 | 6 |
| Won't | 1 |

## 全 177 件

| 要件ID | 項目 | 概要 | 優先度 | 担当範囲 | 調整の理由 |
|---|---|---|---|---|---|
| **FR-AUTH 認証方式** | | | | | |
| FR-AUTH-001 | ID/PW 認証（ローカルユーザー） | ID とパスワードで直接ログインできること。顧客IdP を持たない顧客のユーザと運用者が使う | Must | Keycloak-IdP | Keycloak-IdP に収容するユーザの話。基盤は基盤（ROSA）まで作って引き渡す |
| FR-AUTH-002 | Authorization Code + PKCE（SPA / モバイル） | 画面を持つアプリが、標準の手順（認可コード＋PKCE）でログインを開始し JWT を受け取れること | Must | Keycloak-Broker |  |
| FR-AUTH-003 | Authorization Code + client_secret（SSR） | サーバ側で処理するアプリが、接続用パスワードを使う標準の手順でログインできること | Must | Keycloak-Broker |  |
| FR-AUTH-004 | Client Credentials（M2M） | 人ではなくシステムが API を呼ぶための資格を発行できること | Must | Keycloak-Broker |  |
| FR-AUTH-005 | Token Exchange（RFC 8693） | あるアプリ向けの JWT を、別のアプリ向けに交換できること | TBD | 対象外 | Phase 1 では作らない。必要になれば Keycloak の標準機能で足せる |
| FR-AUTH-006 | Device Code Flow（画面のない機器・CLI 向けログイン） | 画面のない機器や CLI からログインできること | 不要 | 対象外 | 2026-08-16 の判断で Phase 1 対象外 |
| FR-AUTH-007 | mTLS Client Authentication（RFC 8705、証明書によるアプリ認証） | 証明書でアプリを認証できること | 不要 | 対象外 | 2026-08-16 の判断で対象外。金融水準の顧客が現れたときに再評価 |
| FR-AUTH-008 | ROPC（Password Grant） | アプリがユーザのパスワードを直接受け取ってログインさせる方式 | Won't | 対象外 | 採用しない（安全でないため） |
| FR-AUTH-009 | パスワードポリシー（最小長・複雑性） | パスワードの最小の長さと文字種の組み合わせを決められること | Must | Keycloak-IdP | ローカルに収容するユーザだけの話。フェデレーションのユーザは顧客IdP 側の規則に従う |
| FR-AUTH-010 | パスワード履歴（N 個と一致禁止） | 過去に使ったパスワードを一定個数まで再利用させないこと | Should | Keycloak-IdP | 同上 |
| FR-AUTH-011 | アカウントロック（連続失敗） | パスワードを連続で間違えたら一時的にログインを受け付けないこと | Must | Keycloak-IdP | 同上。Keycloak-Broker はパスワードを持たないため、こちらの対象は顧客IdP の実在推測の防止に置き換わる |
| FR-AUTH-012 | パスワード有効期限 | パスワードに有効期限を設けられること | Should | Keycloak-IdP | 同上 |
| FR-AUTH-013 | セルフサービスパスワードリセット | ユーザが自分でパスワードを再設定できること | Must | Keycloak-IdP | 同上 |
| FR-AUTH-014 | 初期パスワード強制変更 | 初回ログイン時にパスワードの変更を強制できること | Should | Keycloak-IdP | 同上 |
| FR-AUTH-015 | DPoP（RFC 9449、送信者に縛った JWT） | JWT を受け取った本人以外が使い回せないよう、送信者を JWT に縛りつけること（DPoP） | TBD | 対象外 | 提案書で新規想定として挙げた項目。Phase 1 では作らない |
| **FR-FED フェデレーション** | | | | | |
| FR-FED-001 | Auth0 OIDC IdP 連携 | Auth0 を顧客IdP として接続できること | 推奨値あり | Keycloak-Broker |  |
| FR-FED-002 | Entra ID（Azure AD）OIDC 連携 | Entra ID（Azure AD）を顧客IdP として接続できること | Must | Keycloak-Broker |  |
| FR-FED-003 | Okta OIDC 連携 | Okta を顧客IdP として接続できること | Should | Keycloak-Broker |  |
| FR-FED-004 | Google Workspace OIDC 連携 | Google Workspace を顧客IdP として接続できること | Could | Keycloak-Broker |  |
| FR-FED-005 | SAML 2.0 IdP として受け入れ（SP モード） | 旧方式（SAML）の顧客IdP からログインを受け入れられること | Should | Keycloak-Broker |  |
| FR-FED-006 | SAML 2.0 IdP として発行（IdP モード） | 本基盤が旧方式（SAML）の提供元として、業務システムへログインを提供できること | TBD | Keycloak-Broker | ServiceNow 連携で必要 |
| FR-FED-007 | LDAP / AD 直接連携 | 社内ディレクトリ（LDAP / AD）に直接つなげること | TBD | 対象外 | Phase 1 では作らない |
| FR-FED-008 | JIT プロビジョニング | 顧客IdP 経由で初めて来た人を、その場でユーザとして自動作成できること | Must | Keycloak-Broker |  |
| FR-FED-009 | 属性マッピング / クレーム変換 | 顧客ごとにバラバラな属性名を、基盤の統一名に変換して取り込めること | Must | Keycloak-Broker |  |
| FR-FED-010 | 複数 IdP 並行運用（マルチテナント） | 複数の顧客IdP を同時に運用でき、顧客ごとに分離できること | Must | Keycloak-Broker |  |
| FR-FED-011 | 顧客追加時のオンボーディングフロー | 新しい顧客を迎え入れるときの、登録から利用開始までの流れが用意されていること | Must | Keycloak-Broker |  |
| FR-FED-012 | フェデレーション時の MFA 重複回避 | 顧客IdP 側で追加認証を済ませた人に、本基盤で二重に追加認証を求めないこと | Must | 顧客IdP | 追加認証は顧客IdP の責務。Keycloak-Broker は関与しない |
| FR-FED-013 | ログイン画面で IdP 選択 UX | ログイン画面でどの顧客IdP を使うかを選べること | Should | Keycloak-Broker |  |
| FR-FED-014 | Custom Domain での federation | 顧客ごとの独自ドメインでフェデレーションできること | Should | 対象外 | Phase 1 では作らない |
| **FR-MFA 多要素認証** | | | | | |
| FR-MFA-001 | TOTP（Google Authenticator 等） | スマートフォンアプリの数字コードで追加認証できること | Must | Keycloak-IdP | 追加認証は Keycloak-Broker では扱わない。ローカル収容ユーザは Keycloak-IdP 側 |
| FR-MFA-002 | WebAuthn / FIDO2（Passkeys） | 生体認証やセキュリティキーで追加認証できること | Should | Keycloak-IdP | 同上 |
| FR-MFA-003 | SMS OTP | SMS の数字コードで追加認証できること | Could | 対象外 | Phase 1 では作らない |
| FR-MFA-004 | メール OTP | メールの数字コードで追加認証できること | Could | 対象外 | Phase 1 では作らない |
| FR-MFA-005 | バックアップコード | 端末を失くしたときに使う予備のコードを発行できること | Should | Keycloak-IdP | 同上 |
| FR-MFA-006 | 条件付き MFA（IP / リスクベース） | 接続元やリスクに応じて追加認証を出し分けられること | Should | 対象外 | Phase 1 では作らない |
| FR-MFA-007 | MFA 強制 / 任意の切替（ロール単位） | 追加認証を必須にするか任意にするかを役割ごとに切り替えられること | Must | Keycloak-IdP | 同上 |
| FR-MFA-008 | 端末記憶（Trusted Device） | 一度確認した端末を覚えて、次回から追加認証を省けること | Could | 対象外 | Phase 1 では作らない |
| FR-MFA-009 | 管理者の MFA 強制 | 管理者には追加認証を必ず求めること | Must | Keycloak-IdP | 同上 |
| **FR-SSO SSO・ログアウト** | | | | | |
| FR-SSO-001 | 同一 IdP 内の複数 Client 間 SSO | 同じ顧客の複数のアプリを、一度のログインで行き来できること | Must | Keycloak-Broker |  |
| FR-SSO-002 | Auth0/Entra 経由のクロス IdP SSO | 顧客IdP を経由した場合も、複数のアプリを一度のログインで行き来できること | Must | Keycloak-Broker |  |
| FR-SSO-003 | ローカルログアウト（アプリ Cookie 削除のみ） | アプリ側だけでログアウトできること（本基盤の状態は保つ） | Must | アプリ | アプリ側の実装。ガイドで示す |
| FR-SSO-004 | IdP セッション破棄（OIDC RP-Initiated Logout） | 本基盤のログイン状態を破棄できること | Must | Keycloak-Broker |  |
| FR-SSO-005 | フェデレーション IdP セッション破棄（連動ログアウト） | 本基盤のログアウトを顧客IdP 側にも連動させられること | Should | Keycloak-Broker |  |
| FR-SSO-006 | Front-Channel Logout | 画面経由で他のアプリにログアウトを伝えられること | Should | 対象外 | Back-Channel を採用するため作らない |
| FR-SSO-007 | Back-Channel Logout（RFC 8606） | サーバ間の通知で他のアプリにログアウトを伝えられること | Should | Keycloak-Broker |  |
| FR-SSO-008 | セッションタイムアウト設定 | ログイン状態が切れるまでの時間を設定できること | Must | Keycloak-Broker |  |
| FR-SSO-009 | アクセストークン強制無効化（Revocation） | 発行済みの JWT を強制的に使えなくできること | Should | Keycloak-Broker |  |
| FR-SSO-010 | 強制全セッション破棄（管理者操作） | 管理者の操作で、対象のログイン状態をまとめて破棄できること | Must | アプリ | 管理画面からの操作。Keycloak-Broker は API を提供する |
| **FR-AUTHZ 認可** | | | | | |
| FR-AUTHZ-001 | JWT クレームベース認可 | JWT に載せた情報でアプリが可否を判断できること | Must | Keycloak-Broker | JWT を出すところまでが本基盤。判断はアプリ |
| FR-AUTHZ-002 | tenant_id によるテナント分離 | 顧客を指す値で、他の顧客のデータに触れられないようにできること | Must | Keycloak-Broker | Keycloak-Broker 側の越境防止。権限データ側の越境防止はアプリ |
| FR-AUTHZ-003 | roles クレームによるロール認可 | 役割を表す情報で可否を判断できること | Must | アプリ | 認可はこちらでは行わない |
| FR-AUTHZ-004 | ロール階層（継承） | 役割に上下関係を持たせられること | Should | アプリ | 同上 |
| FR-AUTHZ-005 | scope ベース認可（M2M） | システム間の呼び出しで、許す範囲を限定できること | Must | Keycloak-Broker |  |
| FR-AUTHZ-006 | カスタムクレーム注入（任意属性） | 任意の属性を JWT に載せられること | Must | Keycloak-Broker |  |
| FR-AUTHZ-007 | API Gateway 認可統合（Lambda Authorizer） | API の入口で JWT を検証して可否を判断できること | Must | アプリ | アプリ側の実装。ガイドで示す |
| FR-AUTHZ-008 | マルチイシュア対応（複数 User Pool / Realm） | 発行元が複数あっても正しく検証できること | Must | Keycloak-Broker |  |
| FR-AUTHZ-009 | リソースレベル認可（UMA 2.0 / Fine-grained） | データ 1 件ごとに細かく可否を判断できること | Could | アプリ | 認可はこちらでは行わない |
| FR-AUTHZ-010 | 動的属性ベース認可（ABAC） | 属性の組み合わせで動的に可否を判断できること | Could | アプリ | 同上 |
| **FR-USER ユーザ管理** | | | | | |
| FR-USER-001 | ユーザー作成 / 更新 / 削除（CRUD） | ユーザを作る・変える・消せること | Must | アプリ | 管理画面はアプリ。Keycloak-Broker は API を提供する |
| FR-USER-002 | カスタム属性（任意フィールド） | 顧客ごとの追加の項目を持たせられること | Must | Keycloak-Broker | 属性の宣言と変換は本基盤 |
| FR-USER-003 | SCIM 2.0 プロビジョニング | 顧客の人事システムから SCIM でユーザを受け取れること | TBD | Keycloak-Broker |  |
| FR-USER-004 | セルフサービスプロフィール編集 | ユーザが自分で自分の情報を変えられること | Must | Keycloak-IdP | ローカル収容ユーザの話 |
| FR-USER-005 | ユーザー検索・一覧 | ユーザを検索・一覧表示できること | Must | アプリ | 管理画面はアプリ |
| FR-USER-006 | ユーザー有効化 / 無効化（suspend） | ユーザを一時的に使えなくする／戻せること | Must | Keycloak-Broker | 停止と再開は本基盤。画面はアプリ |
| FR-USER-007 | ユーザーグループ管理 | ユーザをグループでまとめられること | Should | 対象外 | Phase 1 では作らない（SCIM のグループ連携も対象外） |
| FR-USER-008 | ロール割り当て | ユーザに役割を割り当てられること | Must | アプリ | 権限はこちらでは扱わない |
| FR-USER-009 | バルクインポート（CSV / JSON） | ファイルからまとめてユーザを取り込めること | Should | アプリ | 管理画面はアプリ |
| FR-USER-010 | ユーザーパスワード強制リセット | 管理者がユーザのパスワードを強制的に初期化できること | Must | Keycloak-IdP | ローカル収容ユーザの話 |
| FR-USER-011 | ユーザー削除時の関連データ削除（GDPR 等） | ユーザを消すときに関連するデータも消せること | Should | Keycloak-Broker | 保持と消去の方針は本基盤で決める |
| FR-USER-012 | ユーザー作成時の招待メール | 新しいユーザに招待を送れること | Should | アプリ | 管理画面はアプリ |
| **FR-ADMIN 管理機能** | | | | | |
| FR-ADMIN-001 | 管理コンソール UI | 管理のための画面があること | Must | アプリ | 管理画面はアプリが作る |
| FR-ADMIN-002 | テナント追加・削除 | 顧客を追加・削除できること | Must | Keycloak-Broker | 設計は本基盤。細部は運用設計で詰める |
| FR-ADMIN-003 | IdP 追加・削除・更新 | 顧客IdP を追加・変更・削除できること | Must | Keycloak-Broker |  |
| FR-ADMIN-004 | クライアント（App）管理 | アプリの接続登録を管理できること | Must | Keycloak-Broker |  |
| FR-ADMIN-005 | ロール定義管理 | 役割の定義を管理できること | Must | アプリ | 権限はこちらでは扱わない |
| FR-ADMIN-006 | パーミッション管理（細粒度） | 権限を細かく設定できること | Could | アプリ | 同上 |
| FR-ADMIN-007 | 監査ログ閲覧 | 監査の記録を閲覧できること | Must | Keycloak-Broker | 出力と集約は本基盤。参照は全体の共通基盤で行う |
| FR-ADMIN-008 | 設定変更履歴 | 設定を変えた履歴が残ること | Should | Keycloak-Broker |  |
| FR-ADMIN-009 | テナント別設定の分離 | 顧客ごとに設定を分けられること | Must | Keycloak-Broker |  |
| FR-ADMIN-010 | 管理者ロール（RBAC for Admin） | 管理者にも役割を持たせて操作を制限できること | Must | アプリ | 管理画面の権限はアプリ |
| FR-ADMIN-011 | テナント管理者の委譲（顧客の自社運用） | 顧客の管理者に運用の一部を任せられること | Should | アプリ | 同上 |
| FR-ADMIN-012 | カスタマイズ可能なログイン UI | ログイン画面の見た目を変えられること | Should | Keycloak-Broker | 振り分けの識別子入力画面とエラー画面は本基盤で作る |
| **FR-INT 外部連携** | | | | | |
| FR-INT-001 | OIDC 1.0 / OAuth 2.0 標準準拠 | OIDC / OAuth 2.0 の標準に従っていること | Must | Keycloak-Broker |  |
| FR-INT-002 | OIDC Discovery（`.well-known`） | 接続情報を公開の場所から自動で取得できること | Must | Keycloak-Broker |  |
| FR-INT-003 | JWKS 公開エンドポイント | 署名鍵を公開の場所から取得できること | Must | Keycloak-Broker |  |
| FR-INT-004 | SAML 2.0 メタデータ | 旧方式（SAML）の接続情報を交換できること | Should | Keycloak-Broker |  |
| FR-INT-005 | Webhook イベント通知（user.created 等） | ユーザの変更をアプリへ通知できること（Webhook） | Should | 対象外 | Phase 1 では作らない |
| FR-INT-006 | 管理 REST API | 管理のための API があること | Must | Keycloak-Broker |  |
| FR-INT-007 | API Gateway / Lambda Authorizer 統合 | API の入口で JWT を検証する仕組みと組み合わせられること | Must | アプリ | アプリ側の実装。ガイドで示す |
| FR-INT-008 | 監査ログ外部出力（CloudWatch / S3 / Kinesis） | 監査の記録を外部へ出力できること | Must | Keycloak-Broker | 全体の共通基盤へ出して集約する |
| FR-INT-009 | 監査ログ SIEM 連携（Splunk / Datadog） | 監査の記録を分析製品へ連携できること | Could | 対象外 | 共通基盤側の範囲 |
| FR-INT-010 | Terraform / IaC 管理 | 構成をコードで管理できること | Must | Keycloak-Broker |  |
| **NFR-AVL 可用性** | | | | | |
| NFR-AVL-001 | サービス稼働率 SLA | 顧客に約束する稼働率を定めて満たすこと | TBD | Keycloak-Broker |  |
| NFR-AVL-002 | 計画メンテナンス窓 | 計画的に止める時間の枠を定めること | TBD | Keycloak-Broker |  |
| NFR-AVL-003 | マルチ AZ 配置 | 複数の区画に分けて配置し、片方が落ちても動くこと | 推奨値あり | Keycloak-Broker |  |
| NFR-AVL-004 | 自動復旧（コンテナ障害） | 部品が落ちたときに自動で立ち上がり直すこと | 推奨値あり | Keycloak-Broker |  |
| NFR-AVL-005 | 単一障害点の排除 | 1 か所が落ちると全部止まる箇所を無くすこと | 推奨値あり | Keycloak-Broker |  |
| NFR-AVL-006 | デプロイ時のダウンタイム | 入れ替えのときにログインを止めないこと | 推奨値あり | Keycloak-Broker |  |
| **NFR-PERF 性能** | | | | | |
| NFR-PERF-001 | 認証応答時間（P50 / P95 / P99） | ログインの応答時間が目標に収まること | 推奨値あり | Keycloak-Broker |  |
| NFR-PERF-002 | 同時認証リクエスト処理能力 | 同時に来るログインの数を目標まで捌けること | TBD | Keycloak-Broker |  |
| NFR-PERF-003 | Lambda Authorizer 応答時間 | API の入口での判定が目標時間に収まること | 推奨値あり | アプリ | アプリ側の実装 |
| NFR-PERF-004 | JWT 検証スループット | JWT の検証を目標の件数まで捌けること | 推奨値あり | Keycloak-Broker |  |
| NFR-PERF-005 | JWKS キャッシュ TTL | 署名鍵の取得結果を一定時間持ち回して負荷を下げること | 推奨値あり | Keycloak-Broker |  |
| NFR-PERF-006 | API Gateway スロットリング | 過大な要求を受けたときに流量を絞れること | TBD | Keycloak-Broker |  |
| NFR-PERF-007 | 認証ピーク時間帯への耐性 | 始業時などの山に耐えられること | 推奨値あり | Keycloak-Broker |  |
| NFR-PERF-008 | DB 応答時間（Keycloak のみ） | データベースの応答時間が目標に収まること | 推奨値あり | Keycloak-Broker |  |
| **NFR-SCL 拡張性** | | | | | |
| NFR-SCL-001 | MAU スケール上限 | 想定するユーザ数まで伸ばせること | TBD | Keycloak-Broker |  |
| NFR-SCL-002 | ピーク時同時セッション数 | 同時にログインしている数の山に耐えられること | TBD | Keycloak-Broker |  |
| NFR-SCL-003 | 顧客テナント数（IdP 数）スケール | 顧客IdP の数が増えても捌けること | TBD | Keycloak-Broker |  |
| NFR-SCL-004 | IdP 追加リードタイム | 顧客IdP を追加してから使えるまでの時間が目標に収まること | 推奨値あり | Keycloak-Broker |  |
| NFR-SCL-005 | 自動スケーリング | 負荷に応じて自動で増減すること | 推奨値あり | Keycloak-Broker |  |
| NFR-SCL-006 | マルチリージョン対応（複数地域での同時稼働） | 複数の地域で同時に動かせること | 不要 | 対象外 | 災害対策の結論に従属。Phase 1 では別地域は待機のみ |
| NFR-SCL-007 | データベーススケール（Keycloak） | データベースを増強できること | 推奨値あり | Keycloak-Broker |  |
| **NFR-SEC セキュリティ** | | | | | |
| NFR-SEC-001 | 通信暗号化 | 通信が暗号化されていること | 推奨値あり | Keycloak-Broker |  |
| NFR-SEC-002 | データ暗号化（at-rest） | 保管したデータが暗号化されていること | 推奨値あり | Keycloak-Broker |  |
| NFR-SEC-003 | トークン署名アルゴリズム | JWT の署名方式が安全なものであること | 推奨値あり | Keycloak-Broker |  |
| NFR-SEC-004 | Access Token TTL | JWT の有効期限が適切に短いこと | 推奨値あり | Keycloak-Broker |  |
| NFR-SEC-005 | Refresh Token TTL | 更新用の資格の有効期限が定められていること | 推奨値あり | Keycloak-Broker |  |
| NFR-SEC-006 | ID Token TTL | 本人確認結果の有効期限が定められていること | 推奨値あり | Keycloak-Broker |  |
| NFR-SEC-007 | Refresh Token Rotation | 更新用の資格を使うたびに入れ替えること | 推奨値あり | Keycloak-Broker |  |
| NFR-SEC-008 | トークン失効（Revocation） | 発行済みの資格を失効させられること | 推奨値あり | Keycloak-Broker |  |
| NFR-SEC-009 | パスワード保管アルゴリズム | パスワードを安全な方式で保管すること | 推奨値あり | Keycloak-IdP | ローカル収容ユーザの話 |
| NFR-SEC-010 | ブルートフォース対策 | 総当たりを防ぐこと | 推奨値あり | Keycloak-Broker | Keycloak-Broker はパスワードを持たないため、振り分けの実在推測の防止と試行回数の制限に置き換える |
| NFR-SEC-011 | WAF 適用 | 外部からの攻撃を入口で遮ること（WAF） | 推奨値あり | 対象外 | WAF 側で行う。本基盤では実装しない |
| NFR-SEC-012 | DDoS 対策 | 大量の通信で止められないようにすること | 推奨値あり | 対象外 | 同上 |
| NFR-SEC-013 | ペネトレーションテスト | 疑似攻撃検査を定期的に受けること | TBD | Keycloak-Broker |  |
| NFR-SEC-014 | 脆弱性スキャン | 部品の弱点を定期的に検査すること | 推奨値あり | Keycloak-Broker |  |
| NFR-SEC-015 | シークレット管理 | 接続用パスワードや鍵を安全に保管すること | 推奨値あり | Keycloak-Broker |  |
| NFR-SEC-016 | ネットワーク分離（Private Subnet） | 外から直接触れない区画に置くこと | 推奨値あり | Keycloak-Broker |  |
| NFR-SEC-017 | 管理画面アクセス制御 | 管理のための入口を限られた元からだけ通すこと | 推奨値あり | Keycloak-Broker |  |
| NFR-SEC-018 | JWKS エンドポイント保護 | 署名鍵の公開先を守ること | 推奨値あり | Keycloak-Broker |  |
| NFR-SEC-019 | 内部通信の認証（Lambda → Keycloak） | 内部の呼び出しでも相手を確認すること | 推奨値あり | Keycloak-Broker |  |
| NFR-SEC-020 | セッション固定攻撃対策 | ログインの前後で状態を作り替え、乗っ取りを防ぐこと | 推奨値あり | Keycloak-Broker |  |
| **NFR-DR 災害復旧** | | | | | |
| NFR-DR-001 | RTO（目標復旧時間） | 目標の時間内に復旧できること | TBD | Keycloak-Broker |  |
| NFR-DR-002 | RPO（目標復旧地点） | 失うデータを目標の範囲に収めること | TBD | Keycloak-Broker |  |
| NFR-DR-003 | フェイルオーバー方式 | 別地域へ切り替える方式が定まっていること | TBD | Keycloak-Broker |  |
| NFR-DR-004 | バックアップ保存期間 | 控えを一定期間保つこと | 推奨値あり | Keycloak-Broker |  |
| NFR-DR-005 | PITR（Point-in-Time Recovery） | 時点を指定して戻せること | 推奨値あり | Keycloak-Broker |  |
| NFR-DR-006 | クロスリージョンバックアップ | 控えを別の地域にも置くこと | 推奨値あり | Keycloak-Broker |  |
| NFR-DR-007 | DR 訓練 | 復旧の訓練を定期的に行うこと | TBD | Keycloak-Broker |  |
| NFR-DR-008 | DR 切替時のセッション維持 | 切り替えてもログインし直さずに済むこと | 推奨値あり | Keycloak-Broker |  |
| **NFR-OPS 運用性** | | | | | |
| NFR-OPS-001 | 監視・メトリクス | 動きを測る値が取れること | 推奨値あり | Keycloak-Broker |  |
| NFR-OPS-002 | アラート通知 | 異常を検知したら通知が届くこと | 推奨値あり | Keycloak-Broker |  |
| NFR-OPS-003 | ログ保存期間 | 記録を定められた期間保つこと | TBD | Keycloak-Broker |  |
| NFR-OPS-004 | ログ検索性 | 記録を必要な条件で探せること | 推奨値あり | Keycloak-Broker | 参照は全体の共通基盤で行う |
| NFR-OPS-005 | バージョンアップ方針 | Keycloak の版を上げる方針が定まっていること | TBD | Keycloak-Broker |  |
| NFR-OPS-006 | パッチ適用（CVE 対応） | 弱点への修正を定めた期間内に当てること | 推奨値あり | Keycloak-Broker |  |
| NFR-OPS-007 | 設定変更プロセス | 設定を変えるときの手順が定まっていること | 推奨値あり | Keycloak-Broker |  |
| NFR-OPS-008 | インシデント対応体制 | 障害に対応する体制があること | TBD | Keycloak-Broker |  |
| NFR-OPS-009 | 運用工数（人月） | 運用にかかる人手が想定の範囲に収まること | 推奨値あり | Keycloak-Broker |  |
| NFR-OPS-010 | デプロイ自動化（CI/CD） | 入れ替えを自動で行えること | 推奨値あり | Keycloak-Broker |  |
| NFR-OPS-011 | テナント追加の運用 SLA | 顧客を追加してから使えるまでの時間を約束できること | TBD | Keycloak-Broker |  |
| **NFR-COMP コンプライアンス** | | | | | |
| NFR-COMP-001 | 個人情報保護法対応 | 個人情報保護法に沿った扱いをすること | 推奨値あり | Keycloak-Broker |  |
| NFR-COMP-002 | GDPR / CCPA（海外展開時） | 海外の個人情報の規則に沿えること | TBD | 対象外 | 海外展開時に再評価 |
| NFR-COMP-003 | SOC 2 Type II | 第三者認証（SOC 2）に対応できること | TBD | 対象外 | 取得の予定が決まってから |
| NFR-COMP-004 | ISO 27001 | 第三者認証（ISO 27001）に対応できること | TBD | 対象外 | 同上 |
| NFR-COMP-005 | PCI DSS（金融） | カード業界の基準に対応できること | TBD | 対象外 | 該当する顧客が現れてから |
| NFR-COMP-006 | FIPS 140-3 認定（暗号モジュール認定、旧 140-2） | 暗号の実装が国の認定を受けていること | 不要 | 対象外 | 不要と確定（2026-07-30） |
| NFR-COMP-007 | 監査ログ保存期間（法令要件） | 法令が求める期間まで記録を保つこと | TBD | Keycloak-Broker |  |
| NFR-COMP-008 | データ所在地（リージョン制限） | データを置く地域を限定できること | TBD | Keycloak-Broker |  |
| NFR-COMP-009 | 個人データ削除権（GDPR Right to Erasure） | 本人の求めに応じてデータを消せること | TBD | Keycloak-Broker |  |
| NFR-COMP-010 | アクセス監査の追跡可能性 | 誰がいつ何をしたかを追えること | 推奨値あり | Keycloak-Broker |  |
| NFR-COMP-011 | 暗号鍵のローテーションと所在の可視化 | 鍵を定期的に入れ替え、どこにあるか分かること | 推奨値あり | Keycloak-Broker |  |
| **NFR-COST コスト** | | | | | |
| NFR-COST-001 | 初期構築費 | 初期に作るための費用が見積もられていること | 推奨値あり | Keycloak-Broker |  |
| NFR-COST-002 | 月額固定インフラ費 | 毎月かかる設備の費用が見積もられていること | 推奨値あり | Keycloak-Broker |  |
| NFR-COST-003 | MAU あたりコスト（連携） | ユーザ 1 人あたりの費用が把握できること | 推奨値あり | Keycloak-Broker |  |
| NFR-COST-004 | DR 追加月額 | 災害対策を持つ場合の追加費用が把握できること | 推奨値あり | Keycloak-Broker |  |
| NFR-COST-005 | 運用人件費 | 運用にかかる人件費が見積もられていること | 推奨値あり | Keycloak-Broker |  |
| NFR-COST-006 | RHBK サブスクリプション | Keycloak の商用サポート費用の要否が定まっていること | TBD | Keycloak-Broker |  |
| NFR-COST-007 | 損益分岐 MAU（連携のみ） | どの規模から自前が有利になるかが分かること | 推奨値あり | Keycloak-Broker |  |
| NFR-COST-008 | 3 年 TCO（10 万 MAU 想定） | 3 年分の総額が把握できること（小規模） | 推奨値あり | Keycloak-Broker |  |
| NFR-COST-009 | 3 年 TCO（50 万 MAU 想定） | 3 年分の総額が把握できること（中規模） | 推奨値あり | Keycloak-Broker |  |
| **NFR-MIG 移行性** | | | | | |
| NFR-MIG-001 | 既存認証システムからのユーザー移行 | 既存の認証からユーザを移せること | 不要 | アプリ | 2026-08-17 の判断で本基盤の対象外。移行はアプリ側 |
| NFR-MIG-002 | パスワード移行（ハッシュ持ち越し） | パスワードを暗号化したまま引き継げること | 不要 | アプリ | 同上 |
| NFR-MIG-003 | ベンダーロックイン回避 | 特定の製品に縛られない作りであること | 推奨値あり | Keycloak-Broker |  |
| NFR-MIG-004 | データエクスポート | データを取り出せること | 推奨値あり | Keycloak-Broker |  |
| NFR-MIG-005 | 段階的移行（並行稼働） | 新旧を並行して動かしながら段階的に移せること | 推奨値あり | Keycloak-Broker | 切替の計画は本基盤、実施はアプリ |
