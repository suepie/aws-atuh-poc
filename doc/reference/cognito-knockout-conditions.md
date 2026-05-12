# Cognito のノックアウト条件（採用不可・大幅制約条件の網羅）

> 最終更新: 2026-05-08
> 出典: AWS 公式ドキュメント（[Quotas](https://docs.aws.amazon.com/cognito/latest/developerguide/quotas.html), [FAQs](https://aws.amazon.com/cognito/faqs/)）+ 本 PoC 内検証 + 既存ドキュメント
> 関連: [auth-patterns.md](../common/auth-patterns.md)、[ADR-014](../adr/014-auth-patterns-scope.md)、[ADR-007](../adr/007-osaka-auth0-idp-limitation.md)

---

## 1. はじめに

「Cognito で実現できない」「対応に大きな工夫が必要」「将来スケールでブロックになる」条件を **完全網羅** することを目的とした参照ドキュメント。

要件定義のヒアリング時、**1 つでも該当があれば Cognito 単独採用が不可となる**項目を明示する。

### 影響度の凡例

| マーク | 意味 | 対応方針 |
|:----:|------|--------|
| 🔴 **Hard** | 完全非対応、回避策なし or 大規模実装が必要 | **Keycloak 必須化** or 大幅設計変更 |
| 🟠 **Soft** | 制約付き対応、回避策あり | 工夫で吸収可能 |
| 🟡 **Quota** | リソース・速度の上限 | 増枠申請 or アーキ変更で対応可 |
| 🔵 **Regional** | リージョン依存の制約 | 構成上の注意 |
| ⚪ **UX/運用** | UX・カスタマイズ・運用上の制約 | 受け入れ要否判断 |

---

## 2. Hard Knockouts（🔴 完全非対応）

**いずれか 1 つでも要件にあれば Cognito 採用不可 → Keycloak 必須**

### 2.1 OAuth / OIDC プロトコル系

| # | 項目 | Cognito 状態 | Keycloak 状態 | 影響 |
|---|------|-----------|-----------|------|
| K-01 | **Token Exchange（RFC 8693）** | ❌ ネイティブ非対応。Service A→B でユーザー文脈を伝播する標準手段が無い | ✅ ネイティブ対応 | マイクロサービス構成で致命的 |
| K-02 | **Device Authorization Grant（Device Code Flow）** | ❌ 非対応 | ✅ 標準対応 | CLI / IoT / TV アプリで認証不可 |
| K-03 | **mTLS Client Authentication（RFC 8705）** | ❌ 非対応 | ✅ FAPI Profile で対応 | FAPI 準拠（金融 API）で致命的 |
| K-04 | **Token Introspection（RFC 7662）** | ❌ 非対応（JWT 検証は自前で実施が前提） | ✅ `/protocol/openid-connect/token/introspect` で対応 | Opaque Token 対応の Resource Server で致命的 |
| K-05 | **Dynamic Client Registration（RFC 7591）** | ❌ 非対応 | ✅ Realm Management API | 自動 Client 発行が必要な多テナント基盤で致命的 |
| K-06 | **Pairwise Pseudonymous Identifier (PPID)** | ❌ 非対応（`sub` は固定の UUID） | ⚠ プラグイン対応 | プライバシー要件（GDPR 強化）で問題 |
| K-07 | **OIDC Back-Channel Logout（RFC 8606）** | ❌ 非対応 | ✅ ネイティブ対応 | 複数アプリ間の確実なログアウト同期で致命的 |
| K-08 | **OIDC Front-Channel Logout（OIDC 仕様）** | ❌ 非対応 | ✅ 対応 | 一部のレガシー SP 連携で問題 |
| K-09 | **Custom JWT Signing Key（BYO key）** | ❌ Cognito 管理の鍵のみ、ローテーションも AWS 管理 | ✅ Realm Key で BYO 可 | 顧客が鍵管理を要求する場合に致命的 |
| K-10 | **JWT 署名アルゴリズム ES256 / EdDSA** | ❌ RS256 のみ対応 | ✅ RS256/ES256/PS256/EdDSA 等 | FAPI / 軽量モバイル要件で問題 |

### 2.2 フェデレーション系

| # | 項目 | Cognito 状態 | Keycloak 状態 | 影響 |
|---|------|-----------|-----------|------|
| K-11 | **SAML IdP として発行**（自前で SAML を吐く側） | ❌ Cognito は OIDC IdP のみ、SAML 発行不可 | ✅ Realm が SAML IdP として動作 | レガシー業務システム（SAML SP のみ）連携で致命的 |
| K-12 | **LDAP / Active Directory 直接連携** | ❌ User Federation 機能なし。AD Connector 経由でも限定的 | ✅ User Storage SPI で対応 | オンプレ AD 直接利用要件で致命的 |
| K-13 | **Kerberos / SPNEGO 認証** | ❌ 非対応 | ✅ Kerberos Brokering | Windows 統合認証で致命的 |

### 2.3 認可系

| # | 項目 | Cognito 状態 | Keycloak 状態 | 影響 |
|---|------|-----------|-----------|------|
| K-14 | **UMA 2.0（User-Managed Access）** | ❌ 非対応 | ✅ Authorization Services | リソースオーナー同意の動的認可で致命的 |
| K-15 | **Fine-grained Authorization（ABAC ポリシー集中管理）** | ❌ アプリ側で実装が必要 | ✅ Policy Enforcer + Resource Server | 細粒度認可の集中管理で問題 |
| K-16 | **Composite Roles（ロール継承）** | ❌ Cognito Groups は階層なし、アプリ側実装必要 | ✅ Realm Role の Composite | ロール階層管理で大きな負担 |

### 2.4 認証フロー拡張

| # | 項目 | Cognito 状態 | Keycloak 状態 | 影響 |
|---|------|-----------|-----------|------|
| K-17 | **Required Actions の任意拡張**（規約同意・追加属性入力等を認証フロー内で要求） | ❌ ネイティブ非対応、別画面で実装必要 | ✅ Required Actions / Authentication Flow | エンタープライズ UX で致命的 |
| K-18 | **Step-Up Authentication（リスクベースの段階 MFA 強化）** | ⚠ Advanced Security で一部対応、柔軟性低 | ✅ Conditional Flow で宣言的 | 金融・医療系の段階認証で問題 |
| K-19 | **CIBA（Client-Initiated Backchannel Authentication）** | ❌ 非対応 | ✅ プレビュー対応 | コールセンター・店頭認証で問題 |

### 2.5 セキュリティ・コンプライアンス

| # | 項目 | Cognito 状態 | Keycloak 状態 | 影響 |
|---|------|-----------|-----------|------|
| K-20 | **FIPS 140-2 認定モードでの動作** | ⚠ FIPS Endpoint 利用は可能だが認証フロー全体での認定は限定的 | ⚠ Keycloak は **RHBK のみ FIPS モード対応** | 政府・防衛要件で問題 |
| K-21 | **データ完全性のための監査ログ署名 / WORM 保管** | ❌ CloudTrail 経由のみ、ネイティブ非対応 | ⚠ Event Listener で実装必要 | 監査要件強化で工数大 |

---

## 3. Soft Knockouts（🟠 制約付き対応）

**回避策はあるが、設計上の工夫・追加実装が必要**

### 3.1 トークン処理

| # | 項目 | Cognito の制約 | 回避策 | 工数 |
|---|------|------------|------|:---:|
| S-01 | **Access Token への即時失効（Revocation）** | Refresh Token のみ revoke 可、Access Token は exp まで有効 | アプリ側で Deny List 管理 or 短い TTL（5 分）+ ヘッダー検証 | 中 |
| S-02 | **Pre Token Generation Lambda V1: Access Token 修正不可** | V1 は ID Token のみ修正可、Access Token は不可 | **V2 を使用**（PoC で対応済）。`lambda_version = "V2_0"` 必須 | 既知の落とし穴 |
| S-03 | **Client Credentials Grant への Pre Token Lambda 非対応** | M2M トークンへのカスタムクレーム注入が不可 | Lambda Authorizer 側で固定マッピング | 小 |
| S-04 | **Refresh Token Rotation がデフォルト OFF** | OFF だと Refresh Token 漏洩時のリスク大 | App Client 設定で `RotationEnabled = true` を有効化 | 設定だけ |
| S-05 | **Email クレームが Access Token に含まれない** | ID Token のみ含まれる | Pre Token Lambda V2 で明示的に注入（PoC で対応） | 設定 + Lambda |
| S-06 | **Federated User の Group 名にプレフィックス**（`<pool>_<idp>`） | ロール抽出ロジックが複雑化 | Lambda 側で正規表現フィルタ（PoC で対応） | 中 |

### 3.2 認証 UX

| # | 項目 | Cognito の制約 | 回避策 | 工数 |
|---|------|------------|------|:---:|
| S-07 | **Hosted UI のフルカスタマイズ不可** | CSS / ロゴ画像のみ。HTML 構造変更不可 | 完全カスタマイズが必要なら自前 UI + `/oauth2/authorize` 連携 | 大 |
| S-08 | **IdP 選択ボタン自動表示なし** | `identity_provider` URL パラメータ必須 | 自前画面で IdP 選択 → URL 生成 | 中 |
| S-09 | **Login UX への JavaScript Hook 挿入不可** | カスタムロジック実装不可 | 自前 UI 化 | 大 |
| S-10 | **複数 username 形式の同時受入不可**（email + phone + username） | User Pool 作成時に 1 種類のみ選択 | 別 User Pool / Identity Pool 連携 | 大 |

### 3.3 ユーザー管理

| # | 項目 | Cognito の制約 | 回避策 | 工数 |
|---|------|------------|------|:---:|
| S-11 | **Federation User と Local User の手動マージ** | 標準機能では別ユーザー扱い、ID 統合は実装必要 | Identity Pool の Identity Linking + アプリ側のマッピング | 中〜大 |
| S-12 | **SCIM 2.0 プロビジョニング** | ネイティブ非対応 | Lambda + Cognito API で自前実装、または市販ツール | 大 |
| S-13 | **Webhook 通知（user.created 等）** | Pre/Post Confirmation Lambda Trigger で代替可だが SCIM 標準とは異なる | Lambda Trigger + EventBridge | 中 |
| S-14 | **テナント管理者の委譲（顧客が自社の Cognito を管理）** | AWS IAM 経由必須、顧客に IAM 権限を渡すのは現実的でない | 自前管理画面 + Cognito API 経由 | 大 |
| S-15 | **API 経由で SMS configuration を削除** | API 制約で削除不可、User Pool 再作成が必要 | 設計時に SMS の要否を確定させる | 設計判断 |

---

## 4. Quota Knockouts（🟡 リソース・速度の上限）

### 4.1 リソース数の上限

| # | 項目 | デフォルト | 最大値 | 調整可 | 影響 |
|---|------|---------|------|:----:|------|
| Q-01 | **User Pool 数 / Region** | 1,000 | 10,000 | ✅ | 多テナント設計次第（テナント=User Pool 案で詰む） |
| Q-02 | **App Clients / User Pool** | 1,000 | 10,000 | ✅ | 多システム連携で枯渇可能性 |
| Q-03 | **Identity Providers / User Pool** | 300 | 1,000 | ✅ | **マルチテナントで顧客ごと IdP の場合、ハードリミット** |
| Q-04 | **Resource Servers / User Pool** | 25 | 300 | ✅ | M2M scope 設計で枯渇 |
| Q-05 | **Custom Attributes / User Pool** | **50（固定）** | — | ❌ | **属性追加の事実上の上限** |
| Q-06 | **Groups / User Pool** | **10,000（固定）** | — | ❌ | 多テナント設計次第で枯渇 |
| Q-07 | **Groups / User** | **100（固定）** | — | ❌ | 細粒度ロール設計の上限 |
| Q-08 | **Identities linked to a user**（フェデレーション結合数） | **5（固定）** | — | ❌ | **複数 IdP からの同一ユーザー統合の上限** |
| Q-09 | **Scopes / Resource Server** | **100（固定）** | — | ❌ | 細粒度 scope 設計の上限 |
| Q-10 | **Scopes / App Client** | **50（固定）** | — | ❌ | 多 scope クライアントの上限 |
| Q-11 | **Callback / Logout URLs / App Client** | **100（固定）** | — | ❌ | マルチ環境 / マルチドメイン展開の上限 |
| Q-12 | **Custom Domains / Region** | **4（固定）** | — | ❌ | **多テナント・多ブランドでハードリミット** |
| Q-13 | **Identifiers / IdP** | **50（固定）** | — | ❌ | — |
| Q-14 | **Passkey/WebAuthn authenticators / User** | **20（固定）** | — | ❌ | デバイス多数登録ユーザーの上限 |
| Q-15 | **Pre Token Generation Lambda の変更数** | 5,000 | 増枠可 | ✅ | カスタムクレーム多数 |
| Q-16 | **Users / User Pool** | 40,000,000 | 増枠可 | ✅ | 通常は問題なし |

### 4.2 API レート上限

| # | カテゴリ | デフォルト RPS | 調整可 | 影響 |
|---|---------|------------|:----:|------|
| Q-21 | UserAuthentication | 120 | ✅ | ピーク時刻に枯渇可能性、増枠申請必要 |
| Q-22 | **UserFederation**（フェデレーション認証） | **25** | ✅ | フェデレーション中心の構成で要注意 |
| Q-23 | UserCreation | 50 | ✅ | 一括ユーザー作成時に枯渇 |
| Q-24 | UserAccountRecovery（パスワードリセット等） | **30** | ❌ | キャンペーン直後のパスワードリセット殺到で問題 |
| Q-25 | UserUpdate | **25** | ❌ | 一括属性更新時に枯渇 |
| Q-26 | UserList | **30** | ❌ | バックエンド側で頻繁にユーザー一覧取得すると枯渇 |
| Q-27 | UserPool 系（Read / Update / Resource） | **15-20** | ❌ | テナント管理画面の負荷で問題化 |
| Q-28 | ClientAuthentication（M2M token） | **150** | ❌ | M2M 大量稼働で枯渇 |
| Q-29 | **per-user Read / Write** | **10 RPS（固定）** | ❌ | 同一ユーザーへの高頻度操作で枯渇 |

### 4.3 トークン TTL 制約

| # | トークン | 設定可能範囲 | 影響 |
|---|---------|----------|------|
| Q-31 | **ID Token** | **5 分 〜 1 日** | 1 日超のセッションを Access/ID Token で維持できない |
| Q-32 | **Access Token** | **5 分 〜 1 日** | 同上、長時間バッチで問題 |
| Q-33 | Refresh Token | 1 時間 〜 3,650 日 | 自由度高め |
| Q-34 | **Hosted UI セッション Cookie** | **1 時間（固定）** | 1 時間超は Refresh Token 経由 |
| Q-35 | Authentication Session Token | 3 〜 15 分 | MFA 入力時間に制約 |
| Q-36 | サインアップ確認コード有効期間 | 24 時間（固定） | — |
| Q-37 | MFA コード有効期間 | **3〜15 分（固定）** | — |
| Q-38 | パスワードリセットコード | 1 時間（固定） | — |

### 4.4 ドメイン・リクエスト上限

| # | 項目 | デフォルト RPS | 調整可 |
|---|------|----------|:----:|
| Q-41 | 単一 IP からドメインへのリクエスト | **300（固定）** | ❌ |
| Q-42 | App Client への単一ドメインリクエスト | **300（固定）** | ❌ |
| Q-43 | ドメイン全体のリクエスト | **500（固定）** | ❌ |
| Q-44 | **JWKS（jwks.json）リクエスト / Region** | 50,000 | ❌ | キャッシュ前提の設計が必須 |

### 4.5 Email / SMS 制限

| # | 項目 | デフォルト | 影響 |
|---|------|---------|------|
| Q-51 | **Cognito 標準 Email 送信 / 日 / アカウント** | **50（固定）** | **本番では SES 連携必須** |
| Q-52 | パスワードリセット要求 / ユーザー / 時間 | 5〜20 | リスクベース調整あり |
| Q-53 | サインアップ確認再送 / ユーザー / 時間 | 5 | — |
| Q-54 | ChangePassword 要求 / ユーザー / 時間 | 5 | — |

---

## 5. Regional Knockouts（🔵 リージョン制約）

| # | 項目 | 制約 | 影響 |
|---|------|------|------|
| R-01 | **大阪リージョン Auth0 OIDC IdP 接続不可** | `ap-northeast-3` の Cognito から Auth0 の `.well-known` に到達できない（[ADR-007](../adr/007-osaka-auth0-idp-limitation.md)） | DR 構成で大阪採用時、Auth0 連携は手動 |
| R-02 | **User Pool はシングルリージョン** | マルチリージョン複製機能なし | DR には別 User Pool 構築が必要 |
| R-03 | **User Pool の Cross-Region 移行不可** | 完全マイグレーション機能なし | リージョン変更時はユーザー再登録 + 移行 Lambda |
| R-04 | **AWS GovCloud / 中国リージョンの機能差** | 一部機能（Hosted UI のカスタムドメイン等）が利用不可 | 政府系・中国展開時に注意 |
| R-05 | **Cognito API のリージョナルクォータ** | 増枠申請はリージョン単位、グローバルへの自動波及なし | 多リージョン展開時、各リージョンで申請必要 |

---

## 6. UX / カスタマイズ・運用 Knockouts（⚪）

| # | 項目 | 制約 | 影響 |
|---|------|------|------|
| U-01 | **Hosted UI の HTML 構造変更不可** | CSS / ロゴのみ | ブランディング要件強い場合 |
| U-02 | **複数言語・i18n** | ブラウザ言語自動判定なし、固定言語のみ | グローバル展開時 |
| U-03 | **メール / SMS テンプレート変数の制約** | 利用可能変数が限定的 | 凝った文面で問題 |
| U-04 | **管理者ロール（管理 UI 内 RBAC）** | AWS IAM のみ、Cognito 内の管理者階層なし | 顧客に管理権限を委譲できない |
| U-05 | **Account Console / セルフサービス UI** | ネイティブ提供なし（Keycloak は標準提供） | 自前実装必要 |
| U-06 | **Audit Log の独立ストア** | CloudTrail のみ、Cognito 専用イベントログなし | SIEM 連携時に整形が必要 |
| U-07 | **Realm のような完全テナント分離** | User Pool 単位は分離可だが、IdP 共通設定の継承が困難 | 多テナントで設定重複 |
| U-08 | **エクスポート機能（Realm Export 相当）** | ListUsers + 自前 ETL | バックアップ・移行に工夫必要 |
| U-09 | **Lambda Trigger からの Cognito 操作の制限** | 同一トリガー内で AdminAPI 呼び出し時の再帰実行の問題 | 設計上の注意 |
| U-10 | **ConsoleCustomization の動的変更** | App Client 設定変更が一部即時反映されない | 運用テストで遅延を考慮 |

---

## 7. PoC で実証した制約（既存ドキュメント参照）

| # | 項目 | 出典 |
|---|------|------|
| P-01 | Auth0 `.well-known` が大阪リージョンから到達不可 | [ADR-007](../adr/007-osaka-auth0-idp-limitation.md) |
| P-02 | Pre Token Lambda V1 で Access Token 修正不可 → V2 必須 | [poc-results.md](../common/poc-results.md) |
| P-03 | フェデレーションユーザーの内部 Group 名にプレフィックス | [poc-results.md](../common/poc-results.md) |
| P-04 | `attribute_mapping` 変更が既存 JIT ユーザーに反映されない | [poc-results.md](../common/poc-results.md) |
| P-05 | Auth0 logout の URL エンコード扱い | [poc-results.md](../common/poc-results.md) |
| P-06 | Cognito Authorizer のグループベース認可制限 → Lambda Authorizer 採用 | [ADR-002](../adr/002-lambda-authorizer.md) |

---

## 8. Knockout 判定チェックリスト

要件定義時、**以下のいずれかが Yes なら Cognito 単独採用は不可**:

### 🔴 Hard knockout（即決定）

- [ ] Token Exchange（マイクロサービス間ユーザー文脈伝播）が必要 → **K-01**
- [ ] Device Code Flow（CLI / IoT 認証）が必要 → **K-02**
- [ ] mTLS Client Authentication が必要 → **K-03**
- [ ] Token Introspection エンドポイントが必要 → **K-04**
- [ ] Dynamic Client Registration が必要 → **K-05**
- [ ] OIDC Back-Channel Logout が必要 → **K-07**
- [ ] BYO 署名鍵 / ES256/EdDSA が必要 → **K-09 / K-10**
- [ ] SAML IdP として発行が必要 → **K-11**
- [ ] LDAP / AD 直接連携が必要 → **K-12**
- [ ] UMA 2.0 / Fine-grained 認可が必要 → **K-14 / K-15**
- [ ] Required Actions（規約同意等）の認証フロー内拡張が必要 → **K-17**
- [ ] CIBA / Step-Up Authentication の高度実装が必要 → **K-18 / K-19**

### 🟠 Soft knockout（実装コストで判断）

- [ ] Access Token の即時失効が必須 → **S-01**
- [ ] Hosted UI のフルカスタマイズが必要 → **S-07**
- [ ] SCIM 2.0 プロビジョニングが必要 → **S-12**
- [ ] テナント管理者への管理権限委譲が必要 → **S-14**

### 🟡 Quota knockout（規模で判断）

- [ ] 顧客テナント数 × IdP 数 > 300（増枠で 1,000） → **Q-03**
- [ ] カスタム属性が 50 を超える設計 → **Q-05**
- [ ] ロールが 10,000 / グループが 10,000 を超える → **Q-06**
- [ ] 単一ユーザーへのフェデレーション IdP 結合が 5 を超える → **Q-08**
- [ ] カスタムドメインが 4 を超える（顧客ブランドごと等） → **Q-12**
- [ ] Access Token / ID Token の TTL を 1 日超で設計したい → **Q-32**
- [ ] フェデレーション認証 RPS が 25 を恒常的に超える（増枠申請） → **Q-22**

### 🔵 Regional knockout

- [ ] DR で大阪リージョンを使用 + Auth0 連携 → **R-01**
- [ ] User Pool のクロスリージョン複製が必要 → **R-02**

### ⚪ UX / 運用 knockout（受け入れ判断）

- [ ] 管理者 UI（管理権限委譲含む）を顧客に提供したい → **U-04 / U-07**
- [ ] セルフサービス Account UI が必要 → **U-05**
- [ ] 認証ログを独立ストアに保管したい → **U-06**

---

## 9. ノックアウトされた場合の選択肢

| 状態 | 推奨対応 |
|------|--------|
| 🔴 Hard が 1 つでも該当 | **Keycloak 採用**を確定（OSS or RHBK は別判断） |
| 🔴 なし、🟠 のみ複数 | Cognito で工夫実装 or Keycloak 検討 |
| 🟡 Quota のみ | 増枠申請可能性を確認、不可なら設計変更 |
| 🔵 Regional のみ | 構成変更（Entra ID 採用、リージョン変更等） |
| ⚪ のみ | Cognito 採用、UX 制約は受容 |

---

## 10. 出典・参考

### 公式 AWS 一次ソース

- **AWS Cognito Quotas（公式）**: <https://docs.aws.amazon.com/cognito/latest/developerguide/quotas.html>
- **AWS Cognito FAQs**: <https://aws.amazon.com/cognito/faqs/>
- **AWS Cognito Developer Guide**: <https://docs.aws.amazon.com/cognito/latest/developerguide/>

### 二次ソース

- DEV Community "Amazon Cognito: The Ugly Parts": <https://dev.to/raphael_jambalos/amazon-cognito-the-ugly-parts-and-our-workarounds-2k5p>
- AWS re:Post（公式 Q&A）: 各種制限の議論

### 本 PoC 内ドキュメント

- [auth-patterns.md](../common/auth-patterns.md): 認証パターン総覧（K-01〜04, K-11〜13 の詳細）
- [identity-broker-multi-idp.md](../common/identity-broker-multi-idp.md): マルチ IdP 設計（K-12 の詳細）
- [ADR-007](../adr/007-osaka-auth0-idp-limitation.md): R-01 の検証ログ
- [ADR-002](../adr/002-lambda-authorizer.md): P-06 の根拠
- [ADR-014](../adr/014-auth-patterns-scope.md): K-01〜03, K-11 を Keycloak 必須要因として整理
- [mfa-sso-comparison.md](mfa-sso-comparison.md): MFA / SSO 観点の比較
- [cognito-app-client.md](cognito-app-client.md): App Client 設計の制約
- [cognito-pricing-2024-revision.md](cognito-pricing-2024-revision.md): 料金体系（コスト面の knockout 判断）
- [functional-requirements.md §9](../requirements/functional-requirements.md): Cognito 不可 / Keycloak 必須要因
