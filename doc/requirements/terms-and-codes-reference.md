# 用語・コード体系 対応表（横断リファレンス）

> 目的: 本要件定義で使用する**全コード体系**（Phase / P-X / I-X / α-δ / K1-K8 / L1-L4 等）の意味を 1 ページで対照確認できるリファレンス。
> 参照元: hearing-checklist.md / hearing-script/ / proposal/ で使われる略号・分類コード。
>
> **同じ記号が異なる文脈で違う意味を持つ**ことがある（例: L1〜L4 は SSO 信頼レベル / ログアウトレイヤー / テナント分離レベルの 3 箇所で使用）。**使用文脈を明示**して識別。

---

## 凡例

- **記号**: 略号・コード
- **意味**: 各記号の指すもの
- **文脈**: どの質問・章で使用される
- **典型例**: 該当する具体ケース

---

## 1. ステークホルダー軸: Phase A / B / C / D

> 旧構造（hearing-checklist.md の章分け）から、新構造（§0〜§5 subject-matter 軸）への移行に伴い **項目タグ**として保持。**ヒアリング会議の組み立て** に使う。

| Phase | 想定参加者 | 主な対象 | 項目数 |
|:---:|---|---|---:|
| **`A`** | プロダクトオーナー / 事業企画 / 営業 | 事業要件（MAU、顧客 IdP 分布、ブランディング 等）| 20 |
| **`B`** | 開発チーム / テックリード | 技術要件（Grant Type、JWT クレーム、テナント分離、SSO、MFA、ユーザー管理 等）| 63 |
| **`C`** | 情シス / SRE / セキュリティ | 運用・セキュリティ（SLA、RTO/RPO、監査ログ、コンプラ、AAL、トークン TTL 等）| 35 |
| **`D`** | 意思決定者 | 最終判断（プラットフォーム選定、移行戦略、予算、リリース 等）| 6 |

---

## 2. 利用者カテゴリ: P-1〜P-6

> 本基盤を**経由して認証を受けるユーザー**の分類。A-5-2 / §1.1 で確定する最上位判断。

| コード | 意味 | フェデ or ローカル | 典型例 |
|:---:|---|---|---|
| **P-1** | 基盤運用管理者 | 弊社内 IdP + Break Glass ローカル | 弊社運用チーム |
| **P-2** | 顧客企業のテナント管理者 | 顧客 IdP or ローカル | 顧客の IT 管理者 |
| **P-3** | 顧客企業の一般従業員（**フェデユーザー**）| 顧客 IdP 経由 | 顧客の従業員（Entra ID / Okta 等経由）|
| **P-4** | IdP を持たない顧客のユーザー（**ローカル**）| 本基盤内ローカル | 中小顧客で IdP 未導入のユーザー |
| **P-5** | Break Glass 用ローカル管理者 | 本基盤内ローカル（数名のみ）| 緊急時 / IdP 障害時の最後の砦 |
| **P-6** | B2C コンシューマーユーザー | 本基盤内ローカル | 一般消費者向け SaaS のエンドユーザー |

> **使用箇所**: A-5-2, A-5-3, §FR-1.2.0.0

---

## 3. インフラ運用者カテゴリ: I-1〜I-5

> 本基盤の**インフラを操作する人**（AWS IAM 等で認証する別系統、本基盤の Cognito/Keycloak 経由ではない）。A-5-4 / §1.3 で確認。

| コード | 意味 | 認証経路 | 典型例 |
|:---:|---|---|---|
| **I-1** | AWS インフラ運用者 | AWS IAM（IAM Identity Center / IAM ユーザー / IAM Role）、MFA 必須 | Cognito / Lambda / VPC / API Gateway / DynamoDB を AWS Console / CLI / Terraform で操作 |
| **I-2** | Keycloak / RHBK 運用者 | AWS IAM + kubectl auth / OpenShift OIDC、SSH キー | EKS / ECS / OpenShift 上の Keycloak を `kubectl` / `oc` / Helm で運用 |
| **I-3** | 監視・SRE 担当 | AWS IAM / Datadog SSO / Grafana OAuth、Read-Only 推奨 | CloudWatch / Datadog / Grafana / Splunk でアラート受信・ダッシュボード閲覧 |
| **I-4** | セキュリティ監査者 | AWS IAM / SIEM 認証、Read-Only 強制 | CloudTrail / Cognito 監査ログ / Keycloak Event Listener 出力を SIEM 経由で閲覧 |
| **I-5** | ベンダー / SI サポート | サポートチケット経由 / IAM Role STS 一時付与（24-72h）| Red Hat Support / AWS Support / 外部 SI ベンダー、緊急対応・設計支援等の一時的アクセス |

> **使用箇所**: A-5-4, §FR-1.2.0.0, §NFR-6.4

---

## 4. 採用シナリオ: α / β / γ / δ

> 本基盤が受け入れる**ローカルユーザー**の範囲を 4 シナリオから選択。A-5-3 / §1.2 で確定。

| コード | 意味 | 受入カテゴリ | ローカルユーザー規模 | 業界推奨度 |
|:---:|---|---|---|---|
| **α** | 全カテゴリ受入 | P-1〜P-6 全て | **最大** | B2C を含む大規模 SaaS |
| **β** | 管理者 + IdP なし顧客 | P-1 / P-2 / P-4 / P-5 | 中 | IT 成熟度がまちまちな B2B |
| **γ** | **管理者層のみ**（**業界推奨**）| P-1 / P-2 / P-5 | 小 | **エンタープライズ B2B SaaS** |
| **δ** | Break Glass のみ | P-1 / P-5 | 最小（数名）| 規制業種専用 SaaS（IdP 強制）|

> **使用箇所**: A-5-3, §FR-1.2.0.0

---

## 5. ブランディングパターン: A / A' / B / C

> A-11（軸 1 アプリ別）と A-11-α（軸 2 顧客別）の Yes/No 組合せで**自動判定**される実装パターン。

| パターン | 軸 1 アプリ別 | 軸 2 顧客別 | 説明 | 代表例 |
|:---:|:---:|:---:|---|---|
| **A** | ❌ No | ❌ No | アプリ画面のみカスタマイズ（最シンプル）| Slack / Notion / Microsoft 365 |
| **A'** | ✅ Yes | ❌ No | アプリ別に認証基盤側のログイン画面を変える | Auth0 / Microsoft Entra / Okta |
| **B** | -（任意）| ✅ Yes 部分 | 顧客別ブランディング（Cognito 20 顧客上限、規制業種等）| 顧客向け公開 SaaS |
| **C** | -（任意）| ✅ Yes 完全分離 | 顧客ごとに完全専用デザイン + 認証基盤を物理分離。**SSO 喪失 + Identity Broker パターン崩壊リスク** | Enterprise プラン相当（稀）|

> **使用箇所**: A-11, A-11-α, §FR-2.3.3, §FR-2.3.3.A
> **詳細**: [hearing-script/00-common.md ブランディング 2 軸](hearing-script/00-common.md)

---

## 6. マスター表 B（事業者・顧客 IdP 統合表）の列コード

> [02-idp-federation.md マスター表 B](hearing-script/02-idp-federation.md) の列。**2026-05-25 統合**: 旧マスター表 A（弊社内 IdP、1 行）と旧マスター表 B（顧客 IdP、N 行）を統合。

| 列 | 意味 | 選択肢コード | 詳細 |
|:---:|---|---|---|
| **区分** | 行の役割 | 事業者 / 顧客 | **事業者** = 弊社内 IdP（P-1 認証用、行 0）/ **顧客** = 顧客企業の IdP（P-3 認証用、行 1 以降） |
| **企業名** | 自由記入 | - | 弊社（事業者行）/ Acme Corp 等（顧客行）|
| **X** | IdP 製品 | A-1〜A-3 / B / C-1〜C-2 / D / E / F / G / H / I / J / K / L / M / N / O | Entra / Okta / Google / HENNGE / AD / IdP なし / Keycloak / Cognito 等 |
| **Y** | 接続プロトコル | α / β / γ / δ | OIDC / SAML / **LDAP 直結（Keycloak 必須化）** / 独自（接続不可）|
| **Z** | 接続経由（AD 利用時）| ① / ② / ③ / ④ | 直結 / AD FS 経由 / Entra Connect 経由 / **AD 直結（Keycloak 必須化）**。事業者行では「-」|
| **W** | SCIM 対応 | ✅ / ⚠ / ❌ / ❓ | 標準対応 / 上位ライセンス / 未対応 / 不明 |
| **V** | テナント分離希望 | L1 / L2 / L3 | 完全集約 / 論理分離（標準）/ 物理分離（追加コスト）。事業者行では「-」（弊社は顧客テナントではない）|
| **用途** | 対象ユーザー | - | 事業者行: **P-1 基盤運用管理者の認証** / 顧客行: **P-3 一般従業員の認証** |

> **使用箇所**: [B-200 マスター表 B](hearing-script/02-idp-federation.md)
> **dogfood ケース**: 弊社が自社の他部門向けにも本基盤を使う場合、弊社を行 0（事業者、P-1 用）と顧客行（P-3 用）の 2 行で記入

---

## 7. マスター表 C（御社アプリ）の列コード: P / Q / R / S / T

> [01-auth-flow.md マスター表 C](hearing-script/01-auth-flow.md) の列。**Cognito vs Keycloak 選定の決定打**。

| 列 | 意味 | 選択肢コード | 詳細 |
|:---:|---|---|---|
| **P** | クライアント種別 | a / b / c / d / e / f / g | SPA / SSR / モバイル / M2M バッチ / CLI・IoT / Backend API のみ / SAML SP のみ |
| **Q** | SPA 認証方式（列 P=a のみ）| α / β / γ / — | BFF / PKCE 直接 / 段階移行 / 該当なし |
| **R** | Backend API 経路 / JWT 検証場所 | ① / ② / ③ / ④ / ⑤ | API GW + Lambda Authorizer / ALB + ECS 直結 / Service Mesh / サーバー内完結 / Cognito Authorizer |
| **S** | 特殊要件フラグ（複数 ☑ 可）| K1〜K8（次節）| Cognito Knockout 条件 |
| **T** | 既存ローカル認証 + 移行方針 | N / M1〜M4 | なし / 段階移行 / 並行稼働 / 即時切替 / 維持 |

> **使用箇所**: [B-100 マスター表 C](hearing-script/01-auth-flow.md)

---

## 8. Cognito Knockout 条件: K1〜K8

> マスター表 C 列 S の特殊要件フラグ。**1 つでも☑あれば Keycloak 必須化確定**。

| コード | 内容 | 該当判定 | Cognito で詰む理由 |
|:---:|---|---|---|
| **K1** | Token Exchange（RFC 8693）| マイクロサービス間でエンドユーザー文脈を伝播（OBO 等）| ネイティブ非対応 |
| **K2** | Device Code Flow（RFC 8628）| CLI / IoT / Smart TV / AI Agent | Lambda + DynamoDB 自前実装が必要 |
| **K3** | mTLS Client Authentication（RFC 8705）| FAPI 準拠 / 高セキュリティ M2M | FAPI 不適合 |
| **K4** | DPoP（RFC 9449）| FAPI 2.0 準拠 / トークン盗難対策 | 標準非対応 |
| **K5** | SAML IdP 発行 | 既存 SAML SP アプリに本基盤が SAML を出す | Cognito は SAML SP（受信）のみ |
| **K6** | UMA 2.0 細粒度認可 | リソース所有者ベース認可 | ネイティブ機能なし |
| **K7** | Back-Channel Logout（RFC 8417）| 全 RP 連動ログアウト | 非対応 |
| **K8** | Access Token 即時 Revocation | 規制要件で短 TTL（15 分）でも侵害ウィンドウ許容不可 | 個別 revoke 不可（Refresh のみ）|

> **使用箇所**: [B-100 マスター表 C 列 S](hearing-script/01-auth-flow.md)、[補足 2 K1〜K8 技術根拠](hearing-script/01-auth-flow.md#補足-2-cognito-knockout-条件-k1k8-の技術的根拠)

---

## 9. NIST AAL レベル: AAL1 / AAL2 / AAL3

> 認証保証レベル（NIST SP 800-63B Rev 4）。C-210 / §2.6 で確定。

| コード | 意味 | 必要な MFA | アイドルタイムアウト | 絶対経過 | 採用例 |
|:---:|---|---|:---:|:---:|---|
| **AAL1** | パスワードのみ | 不要 | 任意 | 30 日 | 内部の機密性低システム |
| **AAL2** | MFA 必須（**推奨**）| TOTP 以上、Passkey 推奨 | **1 時間** | **24 時間** | 一般的な B2B SaaS |
| **AAL3** | 最高（Phishing-resistant）| Passkey / YubiKey | 15 分 | 12 時間 | 金融 / 政府系 |

> **使用箇所**: C-210, C-211, C-206-2, C-206-3, §FR-3.0, §FR-3.1, §FR-5.2

---

## 10. ⚠ 同じ記号で違う意味: L1〜L4 / L1〜L3 / L1-L8

> **L1〜L4 は 3 つの異なる文脈**で使用される。**使用文脈を明示**して識別する。

### 10a. SSO 信頼レベル: L1 / L2 / L3 / L4（B-801-1）

| コード | 意味 |
|:---:|---|
| **L1** | 完全信頼（業界標準）|
| **L2** | 部分信頼（TTL 別管理）|
| **L3** | 検証ありき（acr 検査 + ステップアップ）|
| **L4** | 不信任（毎回再認証）|

### 10b. ログアウトレイヤー: L1 / L2 / L3 / L4（B-701）

| コード | 意味 |
|:---:|---|
| **L1** | ローカル（アプリ側セッション破棄のみ）|
| **L2** | IdP セッション破棄 |
| **L3** | フェデ連動（外部 IdP セッションも破棄）|
| **L4** | Back-Channel（同 IdP 内全 RP に同期切断、RFC 8417）|

### 10c. テナント分離レベル: L1 / L2 / L3（マスター表 B 列 V / B-306）

> **大前提**: **Realm（Keycloak）と User Pool（Cognito）は同じ概念**（認証境界 = tenancy boundary）。両者ともユーザー / 外部 IdP / クライアントを内包する独立した認証単位で、**境界をまたいだ SSO は自動成立しない**。L1/L2/L3 はこの「境界をどう設けるか」の選択。

| コード | 意味 | 構成 | SSO 範囲 | 業界推奨度 |
|:---:|---|---|---|---|
| **L1** | 完全集約（顧客 IdP なし、共通基盤ローカルのみ）| 1 Realm/Pool、外部 IdP なし | 共通基盤内全アプリ | 顧客 IdP なしの場合のみ |
| **L2** | 論理分離（**標準**、単一 Pool/Realm + tenant_id クレーム）| **1 Realm/Pool** + 複数 IdP + `tenant_id` クレームで識別 | **同一顧客のアプリ間で自動成立** | **★業界推奨**（Slack / Notion / Auth0 / Entra B2B 等）|
| **L3** | 物理分離（規制業種向け、Pool/Realm per テナント、追加コスト）| **N Realm/Pool**（顧客数分）| 同一 Realm 内 = 同一顧客のアプリ間で成立 | コンプラ要件 / 顧客契約で物理分離必須な場合のみ |

#### よくある誤解の整理

| 誤解 | 訂正 |
|---|---|
| 「Realm をアプリ単位（システム単位）で分けるべき」| ❌ **非推奨**。各アプリで独立 Realm を作ると **アプリ間 SSO が完全に失われる** = SSO 基盤の意味なし |
| 「Realm を顧客（IdP）単位で分けることはできないのでは」| ✅ **可能**。それが L3 物理分離。**同一 Realm 内のアプリ間で SSO は成立**するため、顧客 acme のユーザーが acme の全アプリで SSO 可能 |
| 「全顧客で L3 にすれば最も安全」| ⚠ **Identity Broker パターン崩壊**、N×M Client 登録、Custom Domain 4 個 Hard Limit（Cognito）、設定ドリフト 等の重大デメリット |

#### L3 採用時のデメリット詳細

- **Client 登録の重複**: N 顧客 × M アプリ = N×M 個の Client 登録を保守（例: 50 社 × 10 アプリ = 500 Client）
- **アプリ追加コスト**: 新規アプリ = 全 N 顧客の Realm に登録（50 社なら 50 回）
- **顧客追加コスト**: 新 Realm 作成 + 全 M アプリの Client を登録（10 アプリなら 10 回）
- **Cognito Custom Domain**: 1 リージョン 4 個 Hard Limit → 5 顧客目で詰む
- **Identity Broker パターン崩壊**: 各アプリは「どの Realm に行くか」を判定する必要 = Broker 1 つを Trust できない
- **設定ドリフト**: Realm ごとに認証フロー / Theme / ポリシーが独立 → 顧客間で設定がずれる

#### 詳細グラデーション

[§C-1.4 物理分離レベルと Broker パターンの関係](proposal/common/01-architecture.md#c-14-物理分離レベルと-broker-パターンの関係) では **L1〜L6 の 6 段階**で詳細分析（L4: テナント別 AWS アカウント / L5: リージョン分離 / L6: 別 SaaS インスタンス）。マスター表 B 列 V の L1〜L3 はその簡易版。

### 10d. ブランディング カスタマイズレベル: L1-L3 / L4-L8（A-11-3）

| レベル | 意味 | 対応プラットフォーム |
|---|---|---|
| **L1-L3** | ロゴ・配色・スペーシング・基本配置 | Cognito Managed Login Branding で対応可 |
| **L4-L8** | 文言変更・要素追加削除・並び順変更・完全 HTML | **Keycloak Theme 必須**、または Cognito Custom UI 自前実装 |

---

## 11. アーキテクチャ移行案: A 案 / B 案 / C 案

> §FR-1.2.0 ローカルユーザー認証の主体、§C-1.3 で扱う移行戦略。

| コード | 意味 | 採用判断 |
|:---:|---|---|
| **A 案** | 共通基盤集約（**本基盤の前提**）| すべてのローカル認証を本基盤に集約 |
| **B 案** | 個別 IdP（Pool/Realm per テナント）| 物理分離が必要な特殊顧客のみ例外的に採用（B-607 連動）|
| **C 案** | ハイブリッド | 一部アプリのみ独自認証を維持（**移行期限定で許容**、マスター表 C 列 T M4 連動）|

> **使用箇所**: §FR-1.2.0, §C-1.3, [B-100 マスター表 C 列 T](hearing-script/01-auth-flow.md)

---

## 12. 既存ローカル認証 + 移行方針: N / M1〜M4

> マスター表 C 列 T のコード。

| コード | 意味 |
|:---:|---|
| **N** | なし（新規 or 既に共通基盤前提）|
| **M1** | あり / 段階移行（リリース時にすべて共通基盤集約）|
| **M2** | あり / 並行稼働（一定期間、独自認証 + 共通基盤の両方）|
| **M3** | あり / 即時切替（カットオーバー、リスク高）|
| **M4** | あり / 維持（C 案ハイブリッド、移行期限定で許容）|

> **使用箇所**: [B-100 マスター表 C 列 T](hearing-script/01-auth-flow.md)、§FR-1.2.0

---

## 13. パスワード・MFA 関連: TOTP / FIDO2 / WebAuthn / Passkey

> よく混同される MFA 関連略語。

| 略語 | 正式名称 | 何か |
|---|---|---|
| **TOTP** | Time-based One-Time Password（RFC 6238）| Authenticator アプリ（Google Authenticator 等）の 6 桁コード |
| **FIDO2** | Fast Identity Online 2 | 公開鍵暗号ベースの認証規格群（WebAuthn + CTAP）|
| **WebAuthn** | Web Authentication（W3C 標準）| ブラウザ API。FIDO2 の Web 部分 |
| **Passkey** | （ブランド名）| FIDO2 / WebAuthn を使った**端末同期型認証**。Apple / Google / Microsoft 等が推進 |
| **HOTP** | HMAC-based One-Time Password（RFC 4226）| カウンタベース OTP（古い）|
| **SMS OTP** | SMS One-Time Password | SMS でコード送信（NIST 非推奨、SS7 攻撃リスク）|

> **使用箇所**: B-502, B-503, C-211, C-212, §FR-3.1

---

## 14. プロビジョニング関連: JIT / SCIM / Webhook

> §FR-7.4.0、B-401 / B-405 で扱う 3 つのプロビジョニング方式。

| 略語 | 方向 | 契機 | 主体 |
|---|---|---|---|
| **JIT** プロビジョニング | 外部 IdP → 共通基盤（**ログインのついで**）| ユーザーが本基盤に初回ログインした瞬間 | 基盤側（自動）|
| **SCIM** プロビジョニング | 顧客 HR/IdP → 共通基盤（**独立 REST API**）| 顧客側で人事変更（入社/異動/退職）が起きた瞬間 | 顧客側 IdP（push）|
| **Webhook** 通知 | **共通基盤 → 各アプリ**（方向逆）| 基盤側でユーザーイベント発生 | 基盤側（push）|

> **使用箇所**: B-401, B-405, §FR-7.4.0
> ※「**JIT 管理者**」（必要時のみ管理者権限を付与、Microsoft Entra PIM 等）は別概念で、§FR-8.3 で扱う

---

## 15. プラットフォーム / ティア略号

| 略号 | 正式名称 | 何か |
|---|---|---|
| **Cognito** | Amazon Cognito | AWS マネージド ID 基盤 |
| **Lite** | Cognito Lite ティア | $0.0055/MAU〜 |
| **Essentials** | Cognito Essentials ティア | $0.015/MAU（フェデ利用なら追加コストなし）|
| **Plus** | Cognito Plus ティア | +$0.02/MAU（リスクベース MFA / 侵害検出）|
| **Keycloak** | Red Hat Keycloak（OSS）| オープンソース ID 基盤 |
| **RHBK** | Red Hat Build of Keycloak | Red Hat 商用サポート版（FIPS 140-2 対応）|

> **使用箇所**: D-1, C-301〜C-303, ADR-016, ADR-017

---

## 16. 認可の 2 つの意味（紛らわしい）

> §FR-6.0.A / 03-authz-jwt.md で扱う認可用語の区別。

| 意味 | 何の話か | 担当 |
|---|---|---|
| **意味 A: 認可フレームワーク**（OAuth 2.0 そのもの）| Token をどう発行するか（フロー / プロトコル）| **本基盤**（Authorization Server）|
| **意味 B: 認可判定**（リソース保護）| alice は /expense/123 を編集できるか? という業務判定 | **御社の各アプリ**（Resource Server）|

→ 本基盤のスタンス: **「意味 B の認可は御社アプリの責務」**（[§FR-6.0.A](proposal/fr/06-authz.md)）

---

## 17. SAML の 2 つの方向（紛らわしい）

> 02-idp-federation.md 冒頭で詳述。

| 方向 | 本基盤の役割 | 対応 |
|---|---|---|
| **SAML SP モード**（マスター表 B 列 Y β）| **受信側**（顧客 HENNGE/ADFS 等から SAML を受け取る）| ✅ Cognito / Keycloak 両方 |
| **SAML IdP モード**（マスター表 C 列 P=g / 列 S K5）| **発行側**（既存 SAML SP アプリに SAML を発行）| **❌ Cognito 非対応 / ✅ Keycloak のみ**（K5 = Keycloak 必須化）|

---

## 18. ヒアリングプロセス記号: 🔥 / 🟡 / 🟢 / ⏳ / ✅ / ⚠ / ❌

| 記号 | 意味 |
|:---:|---|
| **🔥** | 最優先（事業判断・プラットフォーム選定直結）|
| **🟡** | 重要 |
| **🟢** | 通常 |
| **⏳** | 未確認 |
| **✅** | 回答済 / 確定 |
| **⚠** | 要追加確認 |
| **❌** | ペンディング / 不採用 / 非対応 |

---

## 19. 要件マトリクスマーク（PoC 検証結果）

> functional-requirements.md / non-functional-requirements.md の各要件への状態マーク。

| マーク | 意味 | 対応 |
|:---:|---|---|
| **✅** | PoC 検証済 / 即実装可能 | そのまま採用、設計フェーズで詳細化 |
| **🟡** | 未検証だが実装可能（既知の方法あり）| PoC 追加検証 or 設計時に深掘り |
| **🟠** | 制約あり / 設計工夫が必要 | ADR 起票、設計フェーズで方針確定 |
| **❌** | プラットフォーム制約として実現不可 | 代替プラットフォーム or 顧客と再協議 |

> **使用箇所**: functional-requirements.md, requirements-process-plan.md §4

---

## 20. OAuth/OIDC 認証・認可フロー種別（6 種類）

> **「認可フロー」は文脈で 2 つの意味**を持つため、議論時には必ず文脈を明示する。[§C-1.2.D 認可フロー種別の整理](proposal/common/01-architecture.md#c-12d-bearer-jwt--jwks-の標準動作と認可フロー種別の整理) と整合。

| # | フロー名 | 内容 | 主役 | OAuth 標準用語 |
|:-:|---|---|---|---|
| 1 | **認証フロー**（Authentication Flow）| ユーザーが**誰か**を確認 + 識別 | 認証基盤 + 顧客 IdP | Authentication |
| 2 | **認可フロー（意味 A）**（Authorization Grant Flow）| OAuth 2.0 で **Token を発行する仕組み** | 認証基盤（Authorization Server）| Authorization Grant |
| 3 | **トークン検証フロー**（Token Validation）| Bearer JWT の**署名・有効期限・audience 検証** | API Gateway + Lambda Authorizer | Token Validation |
| 4 | **認可判定フロー（意味 B）**（Resource Access Control）| tenant_id / roles から **リソースアクセス可否を判定** | アプリ Backend | Authorization Decision |
| 5 | **ログアウトフロー**（Logout Flow）| セッション終了、4 レイヤー（L1〜L4）| 認証基盤 + アプリ + 顧客 IdP | Logout / SLO |
| 6 | **Federation フロー** | コア層 ↔ エッジ層 / 顧客 IdP 間の **トラスト連携** | 各認証層 | Federation |

> **「API 認可フロー」と呼ばれる経路**: #3 + #4 の複合フロー（Bearer JWT を API Gateway / Lambda Authorizer が受け取り、検証してから Backend が認可判定）

---

## 21. Bearer Token / JWT / JWKS / Token Introspection（API 認可関連用語）

> §C-1.2.B 構成図で登場する用語。OAuth/OIDC 標準の API 認可に関する基本概念。

| 用語 | 正式名称 / 規格 | 何か | 主な使用箇所 |
|---|---|---|---|
| **Bearer Token** | RFC 6750 | 「持参者トークン」。HTTP `Authorization: Bearer <token>` ヘッダーで送信。**持っていれば誰でも使える** | Bearer JWT の送信方式 |
| **JWT** | RFC 7519（JSON Web Token）| 認証基盤が発行した**署名付き Token**。ヘッダー / ペイロード / 署名の 3 部構成、Base64URL エンコード | sub / iss / aud / exp / tenant_id / roles 等をクレームに含む |
| **Bearer JWT** | RFC 6750 + RFC 7519 | Bearer Token として送信する JWT。OAuth/OIDC の **デファクト標準** | SPA → API Gateway 通信、§C-1.2.B 矢印「Bearer JWT」|
| **JWKS** | RFC 7517（JSON Web Key Set）| 認証基盤が**公開鍵一覧**を公開する仕組み。`/.well-known/jwks.json` Endpoint | Lambda Authorizer が公開鍵取得 → 1h キャッシュ → ローカル JWT 検証 |
| **kid** | RFC 7515（JWS）| Key ID。JWT ヘッダーに含まれる、使用すべき公開鍵の識別子 | JWKS 内の複数の公開鍵から該当のものを選択 |
| **Token Introspection** | RFC 7662 | API 側が**毎回認証基盤に問い合わせ**て Token の有効性を確認する方式 | 即時失効必須時のみ採用（[K8 Access Token Revocation](proposal/common/01-architecture.md#c-12c1-federation-hub-の-5-つの実装パターンと-spof-評価)）|

#### JWKS 方式 vs Token Introspection の選択

| 観点 | **JWKS 方式（本基盤標準）** | Token Introspection |
|---|---|---|
| **認証基盤への通信頻度** | 初回 + 1h ごと（キャッシュヒット）| **API 呼び出しの度** |
| **レイテンシ** | キャッシュヒット = 1ms 以下 | 毎回 50-200ms |
| **認証基盤負荷** | 軽 | 重 |
| **認証基盤の SPOF 影響** | **キャッシュ内は継続動作** | **基盤障害で全 API 停止** |
| **トークン即時失効** | ❌ TTL 内は失効不可 | ✅ 即座に反映 |

→ **本基盤標準は JWKS 方式**。Token Introspection は K8 規制要件時のみ採用。詳細は [§C-1.2.D.6](proposal/common/01-architecture.md#c-12d6-jwks-方式-vs-token-introspection-の選択)。

> **使用箇所**: §C-1.2.B 構成図、§C-1.2.D、§FR-6.1.A 最小クレーム設計

---

## 関連ドキュメント

- [hearing-checklist.md](hearing-checklist.md): 全 124 項目の SSOT（§0〜§5 構造）
- [hearing-script/](hearing-script/): 顧客送付用敬体スクリプト（旧 Phase 軸のファイル分割）
- [proposal/00-index.md](proposal/00-index.md): 顧客提示版 SSOT
- [hearing-checklist-excel-readme.md](hearing-checklist-excel-readme.md): Excel 転記用 TSV ガイド
