# Amazon Cognito 適合性分析 — 現行要件を満たせるか

作成: 2026-09-16
位置づけ: **別世界線の検討（調査のみ）**。本書は現行の設計判断（Keycloak 採用、[ADR-032](../adr/032-ciam-platform-cost-comparison-10m-mau.md)）を変更しない。
評価対象: 現行の前提 **P-01〜P-20**（[01-architecture-baseline.md](../basic-design/01-architecture-baseline.md)）と主要な設計判断
調査方法: AWS 公式ドキュメント（クォータ・料金・属性仕様）で裏取り。出典は §8

---

## 1. 結論

**現行要件のままでは Cognito に載せ替えできない。** 代替実装で回避できない障害が **2 件**、アーキテクチャの作り直しを伴う障害が **4 件**ある。

| 判定 | 件数 | 内容 |
|---|---|---|
| 🔴 **代替不能** | 2 | SAML IdP になれない / 接続 IdP 数の天井 1,000 |
| 🟠 **要件かアーキの変更が必要** | 4 | ES256 / 属性スキーマ不可逆 / セッション制御 / テナント分離の器 |
| 🟡 **自作で埋まる**（Keycloak でも自作する） | 4 | SCIM 受信 / HRD / JIT 制御 / 管理 API |
| 🟢 **Cognito の方が容易** | 3 | パスワード変更・再設定 API / 運用負荷 / 構築工数 |

**最も効くのは 🔴 の 2 件**で、どちらも「設定や実装の工夫」では越えられません。

- **SAML IdP になれない** → P-13（ServiceNow）と P-14（既存 SP = SAML）が成立しない
- **IdP 上限 1,000** → P-16（1000 超想定）が設計上限に到達する

コストについては、**初回リリース規模（100〜500 万 MAU）では Cognito の方が安い可能性が高い**ことを確認しました（§6）。ただし上記の機能面が先に効きます。

---

## 2. 前提 P-01〜P-20 の充足マトリクス

| # | 前提 | Cognito での可否 | 根拠 |
|---|---|:---:|---|
| P-01 | プラットフォーム = Keycloak / ROSA | — | 本検討の対象（置き換え前提） |
| P-02 | MAU 10M（初回 100〜500 万） | ✅ | Users per user pool = 40,000,000（調整可） |
| P-03 | FIPS 140-3 不要（見込み） | ✅ | AWS マネージド。要件化した場合は別途確認 |
| P-04 | SLA 99.9% | ✅ | AWS SLA に依存 |
| P-05 | DR（RTO 1 日 / RPO 5 分） | 🟠 | プールのクロスリージョン複製は標準機能ではない。**要確認** |
| **P-06** | **テナント分離 L2 単一 Realm + Organizations + tenant_id** | 🟠 | **Organizations 相当が無い**。groups はフラット。tenant_id はカスタム属性で代替可 |
| P-07 | 全顧客ユーザーはフェデレーション、IdP-KC 収容 | 🟠 | IdP-KC 相当 = Cognito ローカルユーザー。ただし「Broker と IdP を分離」という多層構造は作れない |
| **P-08** | **識別子 3 階層（sub UUID / `<tenant>-<userid>` / IdP sub）** | 🟠 | **`sub` は RFC UUID ではない**（公式明記）。username は変更不可・再利用可 |
| **P-09** | **AT 30 分 / RT 30 日 + Rotation / 絶対 24h / アイドル 1h / ES256** | 🔴🟠 | **ES256 不可（RS256 固定）**。セッション cookie は **1 時間固定・非設定** |
| P-10 | JWT クレーム最小・PII 非搭載 | ✅ | app client の read 属性を絞れる。Pre token generation で制御可 |
| P-11 | SSO 信頼レベル L1 / L3 | 🟡 | L3（顧客 IdP へのログアウト連鎖）は標準に無く自作 |
| **P-12** | **JIT + SCIM 受信、Custom Authenticator SPI 案 B** | 🟡 | SCIM 受信は自作（Keycloak でも自作）。SPI 相当は Lambda トリガーで代替 |
| **P-13** | **ServiceNow パターン ②（L1 SCIM + L2 SAML JIT）** | 🔴 | **Cognito は SAML IdP になれない** |
| **P-14** | **新規 = OIDC / 既存 SP = SAML** | 🔴 | 同上。既存 SP への SAML 提供ができない |
| P-15 | 東京 + 大阪 DR | 🟠 | P-05 と同じ。**要確認** |
| **P-16** | **接続 IdP 数 1000 超想定** | 🔴 | **Identity providers per user pool = 既定 300 / 上限 1,000** |
| P-17 | IdP-KC を別アカウント・2 クラスタ | ✅ | 概念が消える（マネージドのため） |
| P-18 | インターネット境界は他組織管理 | 🟠 | Cognito はパブリックエンドポイント。CloudFront 前段配置の可否は**要確認** |
| P-19 | ブランド = Realm、issuer はブランド毎に単一 | 🟠 | user pool = issuer。ブランド分離は自然だが、IdP 上限の回避でプールを割ると issuer が増える |
| P-20 | idm-api（管理コントロールプレーン） | 🟢 | AWS SDK で大部分が置き換わる。**最も工数が減る箇所** |

---

## 3. 🔴 代替不能な障害

### 3.1 Cognito は SAML IdP になれない（P-13 / P-14）

**Cognito user pool は SAML の SP にはなれるが、IdP にはなれません。**

- 外部 SAML IdP（AD FS・Entra・Shibboleth 等）と**フェデレーションして受ける**ことはできる
- しかし Cognito が発行するのは **OIDC の JWT だけ**で、SAML アサーションを発行する機能が無い
- したがって **SAML しか話せない既存 SP は Cognito に接続できない**

現行設計はここを明確に要件化しています。

| 前提 | 内容 |
|---|---|
| **P-14** | アプリ標準プロトコル = 新規 OIDC / **既存 SP = SAML** |
| **P-13** | ServiceNow = パターン ②（L1 SCIM + **L2 SAML JIT**、[ADR-023 §L](../adr/023-servicenow-sp-integration.md)） |

**回避策と評価:**

| 案 | 内容 | 評価 |
|---|---|---|
| ① 既存 SP を OIDC へ改修 | ServiceNow ほか既存 SP 側の改修 | ❌ 顧客資産の改修。SaaS 側が OIDC 非対応なら不可 |
| ② SAML IdP を別途立てる | Cognito の前段/後段に SAML IdP を置く | ❌ **その IdP が Keycloak になる**。二重運用で本末転倒 |
| ③ ServiceNow を SCIM のみに縮退 | L2 SAML JIT を諦める | ⚠ ADR-023 の 4 パターン比較で ② を推奨とした根拠が崩れる |

→ **P-14 を「既存 SP も OIDC 必須」に変更できない限り、Cognito は選べません。**

### 3.2 接続 IdP 数の天井が 1,000（P-16）

AWS 公式のクォータです。

| リソース | 既定 | 調整可否 | **上限** |
|---|---:|:---:|---:|
| **Identity providers per user pool** | **300** | Yes | **1,000** |
| User pools per Region | 1,000 | Yes | 10,000 |
| App clients per user pool | 1,000 | Yes | 10,000 |
| Identifiers per identity provider | 50 | No | — |

P-16 は「**1000 超想定**」なので、**引き上げ後の上限ちょうどに張り付きます**。ヘッドルームがゼロです。

**回避策（プール分割）とその副作用:**

user pool を複数に割れば IdP 総数は増やせます（1,000 pool × 1,000 IdP）。しかし現行設計の根幹が崩れます。

| 崩れるもの | 内容 |
|---|---|
| **P-06 L2 単一 Realm** | テナント分離の方式そのもの。`tenant_id` クレームによる単一境界が成立しなくなる |
| **P-19 issuer はブランド毎に単一** | user pool ごとに issuer が変わる。**アプリは N 個の issuer を検証する**ことになる |
| ユーザー横断の検索・棚卸し | プールを跨いだ ListUsers ができない。管理画面・監査・停止伝播が全部プール数分になる |
| アプリの Client 管理 | app client はプールごと。同じアプリを N プールに登録する |

→ **「単一 Realm + tenant_id」という [ADR-017](../adr/017-multitenant-l2-single-realm.md) の設計を捨てることになります。**

---

## 4. 🟠 要件かアーキテクチャの変更が必要なもの

### 4.1 署名アルゴリズムが RS256 固定（P-09）

- Cognito は **RS256 のみ**。設定項目が存在しない
- JWKS に出るのは常に `"kty": "RSA"` で、**EC 鍵は原理的に現れない**

P-09 は **ES256** を指定しています（[§NFR-4.2](../basic-design/07-security-compliance-design.md) / ADR-045 鍵管理）。

**回避策:** 後段の Lambda / API 層で Cognito の RS256 トークンを検証し、自前で ES256 トークンを再発行する。ただしこれは「認証基盤がトークンを発行する」という構造を壊すので、**実質的に自前 IdP を持つのと変わりません**。

→ **まず「ES256 は必須要件か」を確認すべきです。** 鍵長・署名サイズの都合であって規制要件でないなら、RS256 受容で解決します。

### 4.2 カスタム属性スキーマが不可逆（属性正準化 D3-15）

公式の記述です。

> You can add up to **50 custom attributes** to your user pool.
> **You can't remove or change it after you add it to the user pool.**

さらに周辺のクォータも厳しめです。

| 制約 | 値 |
|---|---|
| カスタム属性の数 | **50（調整不可）** |
| 属性名の文字数 | **20 文字** |
| 属性値のサイズ | 2,048 バイト |
| ID トークンへの出力 | **文字列としてのみ**（number / boolean も文字列化） |
| 必須/任意の切替 | **プール作成後は変更不可** |

現行の[正準スキーマ](../basic-design/research/attribute-canonicalization-notes.md)は、組織属性 8 個 + ライフサイクル属性（`provisioned_by` / `scim_active` / `deprovisioned_at` / `deprovisioned_reason` / `last_login` …）+ `tenant_id` + 識別子系で、**すでに 15〜20 個規模**です。50 枠自体は足りますが、**一度作ったら消せない**ため、設計変更のたびに廃棄属性が溜まります。

**さらに踏みやすい罠**が公式に明記されています。

> Sign-in with a third-party IdP: … This is possible but **not practical**, because the user will only be able to sign in one time. On sign-in attempts after their first, Amazon Cognito **rejects the attempt** because of the mapping rule to a now-unwriteable attribute.

immutable 属性に IdP マッピングを張ると、**2 回目のログインが失敗します**。`external_id` のような「初回だけ書きたい」属性を immutable にすると踏みます。現行設計の「②基盤付与を①顧客写像で上書きしない規約」（syncMode=IMPORT 相当）を Cognito で実現しようとすると、ここに直撃します。

### 4.3 セッション制御の粒度が足りない（P-09）

| P-09 の要件 | Cognito |
|---|---|
| アクセストークン 30 分 | ✅ 設定可（5 分〜1 日） |
| リフレッシュトークン + Rotation | ⚠ **Rotation は 2025-04 追加。Essentials / Plus ティアが必要**。有効化すると `REFRESH_TOKEN_AUTH` が使えなくなる |
| **絶対タイムアウト 24h** | ❌ 相当する概念が無い |
| **アイドルタイムアウト 1h** | ⚠ managed login の cookie が 1 時間だが、**設定不可・スライドしない**（再ログインしても延長されない） |
| ログアウトでセッション破棄 | ⚠ **`GlobalSignOut` では cookie が消えない**。Logout エンドポイントへのリダイレクトが必須 |

とくに最後の項目は事故になりやすい挙動です。「サインアウトしたのに、ブラウザを戻ると資格情報の入力なしで再認証される」状態が残ります。

### 4.4 `sub` が RFC UUID ではない（P-08）

公式の記述です。

> Amazon Cognito generates `sub` in an Amazon Cognito-specific format that **doesn't conform to a specific UUID format, including RFC UUID**. You shouldn't strictly validate the format of `sub`.

P-08 は「3 階層（**sub UUID** / `<tenant>-<userid>` / IdP sub）」です。また[開発標準](../common/jit-scim-coexistence-keycloak.md)で「**アプリ側 DB の外部キーは必ず `sub`**」と定めているため、アプリが `UUID` 型カラムを切っていると**型が合いません**。

影響は限定的ですが、**アプリ標準の文言修正とベンダーへの再告知**が必要になります。

あわせて `username` の制約も確認が要ります。

- **作成後に変更できない**（`<tenant>-<userid>` の規約とは相性が良い）
- **削除後は再利用できてしまう**（同じ username で別人が作れる）

---

## 5. 🟡 自作で埋まるもの / 🟢 Cognito が有利なもの

### 5.1 自作が必要（ただし Keycloak でも自作する）

| 項目 | Cognito | 現行 Keycloak |
|---|---|---|
| **SCIM 受信** | 標準機能なし → Facade 自作 | 同じく Facade 自作（D3-11） |
| **HRD（振り分け）** | `idp_identifier` パラメータ + Identifiers per IdP 50 で**ドメイン振り分けは可能**。識別子ベースは自作 | 同じく方式 A Custom SPI（ADR-055） |
| **JIT の制御** | Pre sign-up / Pre token generation Lambda トリガー | Custom Authenticator SPI 案 B |
| **停止伝播・ライフサイクル** | AdminDisableUser + カスタム属性 + EventBridge | 同等の自作 |

→ **この 4 つは差分になりません。** どちらを選んでも自作します。

### 5.2 Cognito の方が容易

| 項目 | 内容 |
|---|---|
| **パスワード変更・再設定 API** | `ChangePassword` / `ForgotPassword` / `ConfirmForgotPassword` が**標準 API として存在**。Keycloak で未決になっている A-1（画面誘導しかない）・§4.3（忘れた人の再設定）・M-Q-11-6（2-tier での `kc_action`）が**まるごと消えます** |
| **運用負荷** | ROSA HCP × 2 クラスタ・Aurora × 2・版上げ・証明書更新・SRE 境界（ADR-056 §L7）が消える |
| **構築工数** | idm-api（P-20）の大半が AWS SDK 呼び出しに置き換わる。現行 WBS **545〜1,026 人日**の相当部分が削減対象 |

**この 3 点が「Cognito の方が安い」の実体**です。とくにパスワードまわりは、直近で未決が 3 件積み上がっている領域なので、それが消える価値は小さくありません。

---

## 6. コストの再計算

Cognito の料金は **フェデレーション（SAML/OIDC）ユーザーが全ティア共通で $0.015/MAU** です。P-07 により顧客ユーザーの相当数がフェデレーション扱いになるため、ティア選択の効果は限定的です。

### 前提
- フェデ : ローカル = **50 : 50**（B-BROK-1 暫定値）
- Lite ローカル: 最初の 90,000 が $0.0055、以降 $0.0046
- Essentials ローカル: $0.015

### 月額

| MAU | 内訳 | Lite | Essentials |
|---:|---|---:|---:|
| **100 万** | フェデ 50 万 $7,500 + ローカル 50 万 | **$9,881** | **$15,000** |
| **500 万** | フェデ 250 万 $37,500 + ローカル 250 万 | **$49,081** | **$75,000** |
| **1,000 万** | フェデ 500 万 $75,000 + ローカル 500 万 | $86,581 | **$150,000** |

### 年額比較

| | Cognito Lite | Cognito Essentials | Keycloak（AWS インフラのみ） |
|---|---:|---:|---:|
| 100 万 MAU | **$119K** | **$180K** | $122K |
| 500 万 MAU | $589K | $900K | $122K |
| 1,000 万 MAU | $1.04M | **$1.8M** | $122K |

**読み方:**

1. **100 万 MAU では Cognito Lite ≈ Keycloak インフラ費**（$119K vs $122K）。ここに Keycloak の**構築 545〜1,026 人日**が乗るので、**初回リリース規模なら Cognito が明確に安い**
2. ただし **Lite は Managed Login 不可・Refresh Token Rotation 不可**（[ADR-032](../adr/032-ciam-platform-cost-comparison-10m-mau.md) の棄却理由）。実用上は Essentials → **$180K/年**
3. **500 万を超えると逆転**。10M では [ADR-032](../adr/032-ciam-platform-cost-comparison-10m-mau.md) の結論（14 倍差）がそのまま再現される
4. P-02 は「**設計上限 10M で据え置き / 初回 100〜500 万**」なので、**損益分岐は初回リリースと最終到達点の間にある**

> ⚠ **M2M（client_credentials）は別課金**: $0.00225 / トークンリクエスト。アプリ間通信が多い設計では無視できません。現行設計は M2M トークンを常用するため、**別途見積もりが必要**です。

---

## 7. もし Cognito でやるなら — 変更が必要な決定

参考として、採用する場合に改訂が要る決定を列挙します。

| 決定 | 現状 | 必要な変更 |
|---|---|---|
| **P-14 / ADR-023** | 既存 SP = SAML、ServiceNow は SAML JIT | **既存 SP も OIDC 必須に変更**（顧客合意が要る） |
| **P-16 / ADR-017** | 1000 超 IdP・L2 単一 Realm | **プール分割前提のマルチ issuer 設計へ**。またはブランド単位で 1,000 IdP に収まることを確認 |
| **P-09 / ADR-045** | ES256 | **RS256 受容**。セッション設計（絶対 24h / アイドル 1h）を作り直す |
| **D3-15 属性正準化** | User Profile 宣言 + syncMode 制御 | **不可逆スキーマ前提で属性表を凍結**。immutable + IdP マッピングの禁則を追加 |
| **P-08 / ADR-018** | sub = UUID | **sub は不透明文字列**としてアプリ標準を改訂 |
| **ADR-062 / P-20** | idm-api = Lambda | 大幅縮小（AWS SDK 直呼びへ） |
| **D3-05** | アプリ発 CRUD は専用 API 層 | Cognito Admin API + IAM で代替可能か再評価 |

---

## 8. 未確認事項

本書の判定のうち、追加調査が必要なものです。

| # | 項目 | なぜ要るか |
|---|---|---|
| U-1 | **DR（P-05 / P-15）**: Cognito のクロスリージョン複製の可否と RPO | RTO 1 日 / RPO 5 分の要件に対する適合。**マネージドゆえに手が入らない**点が逆にリスク |
| U-2 | **P-18 境界**: Cognito のパブリックエンドポイントを他組織管理の CloudFront + WAF 配下に置けるか | 現行の境界設計が前提にしている |
| U-3 | **PCI DSS / APPI**: 責任共有モデル下での証跡・削除証明 | [3 段階削除モデル](../basic-design/03-identity-provisioning-design.md)の第 3 段階（物理削除 + 完了証明書）が Cognito で成立するか |
| U-4 | **M2M 課金の実測見積り** | トークンリクエスト単価 $0.00225 × 想定回数 |
| U-5 | **ES256 の必要性** | 規制要件か設計選好か。ここが後者なら 🟠 が 1 つ減る |
| U-6 | **ブランドあたりの IdP 数** | P-19 で Phase 1 = 1 ブランド。ブランド単位で 1,000 未満に収まるなら §3.2 の深刻度が下がる |

---

## 9. 出典

### AWS 公式
- [Quotas in Amazon Cognito](https://docs.aws.amazon.com/cognito/latest/developerguide/limits.html) — IdP 数・プール数・カスタム属性数ほか
- [Working with user attributes](https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-settings-attributes.html) — カスタム属性の不可逆性・`sub` の形式・immutable 属性の罠
- [Amazon Cognito Pricing](https://aws.amazon.com/cognito/pricing/) — Lite / Essentials / Plus 単価、M2M 単価
- [Using SAML identity providers with a user pool](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-saml-idp.html) — SP としての SAML 連携
- [Understanding the identity (ID) token](https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-the-id-token.html) — RS256 固定
- [Refresh tokens](https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-the-refresh-token.html) — Rotation の挙動
- [Amazon Cognito now supports refresh token rotation](https://aws.amazon.com/about-aws/whats-new/2025/04/amazon-cognito-refresh-token-rotation/) — 2025-04 提供開始・ティア要件
- [User pool managed login](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-managed-login.html) — セッション cookie 1 時間

### コミュニティ / 補足
- [AWS re:Post — Cognito as a SAML IdP](https://repost.aws/questions/QUxHUXiD0PRXa4iabxu62IrA/aws-cognito-as-a-saml-idp) — SAML IdP 非対応の確認
- [AWS re:Post — Is the Cognito hosted UI browser session length configurable?](https://repost.aws/questions/QUjTUqjCB-QuyVW6B-HQYSFg/is-the-cognito-hosted-ui-browser-session-length-configurable) — cookie 長の非設定性

### 本プロジェクト
- [ADR-032 CIAM プラットフォーム選定（10M MAU コスト比較）](../adr/032-ciam-platform-cost-comparison-10m-mau.md)
- [ADR-016 Cognito 機能ティア選定](../adr/016-cognito-feature-tier-selection.md)
- [ADR-006 Cognito vs Keycloak 損益分岐](../adr/006-cognito-vs-keycloak-cost-breakeven.md)
- [01-architecture-baseline.md 前提 P-01〜P-20](../basic-design/01-architecture-baseline.md)
- [attribute-canonicalization-notes.md](../basic-design/research/attribute-canonicalization-notes.md)
