# Amazon Cognito 適合性分析 — 現行要件を満たせるか

作成: 2026-09-16 / 最終更新: 2026-09-25（v4 — トークン制御の実装モデル §5.5 を追加）
位置づけ: **別世界線の検討（調査のみ）**。本書は現行の設計判断（Keycloak 採用、[ADR-032](../adr/032-ciam-platform-cost-comparison-10m-mau.md)）を変更しない。
評価対象: 現行の前提 **P-01〜P-20**（[01-architecture-baseline.md](../basic-design/01-architecture-baseline.md)）と主要な設計判断
調査方法: AWS / ServiceNow の公式ドキュメントで裏取り。出典は §10
関連: **DR は [02-dr-analysis.md](02-dr-analysis.md) に分離**

> **v2 での変更（2026-09-16）**: 初版で「代替不能」と判定した **SAML IdP 不可を 🟢 解消に変更**した。理由は 2 点 — ①本基盤が SAML IdP として提供する相手は **ServiceNow 1 本のみ**であることを設計側で確認 ②**ServiceNow の OIDC SSO が自動ユーザープロビジョニング（JIT）を公式にサポート**していることを確認。経緯は §4。
> これにより **代替不能な障害は「接続 IdP 数 1,000」の 1 件だけ**になった。

---

## 1. 結論

**現行要件のままでは Cognito に載せ替えできない。ただし障害は 1 点に絞られた。**

| 判定 | 件数 | 内容 |
|---|:-:|---|
| 🔴 **代替不能 / 重大** | **3** | **接続 IdP 数の天井 1,000**（P-16）/ **DR 先に大阪が選べない**（P-15）/ **TOTP MFA が DR 中に使えない**（[02](02-dr-analysis.md)）|
| 🟠 **要件かアーキの変更が必要** | 6 | ES256 / 属性スキーマ不可逆 / セッション制御 / `sub` の形式 / **アクセストークンの `aud` 欠落**（§5.5）/ **トークン制御が単一 Lambda に集約**（§5.5） |
| 🟢 **解消** | 1 | SAML IdP 不可 → ServiceNow の OIDC 化で回避可（§4） |
| 🟡 **自作で埋まる**（Keycloak でも自作する） | 4 | SCIM 受信 / HRD / JIT 制御 / 管理 API |
| 🟢 **Cognito の方が容易** | 4 | パスワード API / ブローカー分離が不要 / 運用負荷 / 構築工数 |

**判断は 2 つの軸に集約される** — ①**接続する顧客 IdP が 1,000 に収まるか** ②**DR を海外リージョンに置けるか（法務判断）**。

> **DR は別文書に切り出した** → **[02-dr-analysis.md](02-dr-analysis.md)**。2026-06 に Multi-Region Replication が登場して手段は生まれたが、**大阪非対応・TOTP MFA 不可・新規ユーザー不可**という 3 つの壁がある。一方 **RTO は現行 Keycloak 設計（≈ 14 日）より桁違いに良い**。

コスト面では **初回リリース規模（100〜500 万 MAU）で Cognito の方が安い**（§7）。

---

## 2. 前提 P-01〜P-20 の充足マトリクス

| # | 前提 | Cognito での可否 | 根拠 |
|---|---|:---:|---|
| P-01 | プラットフォーム = Keycloak / ROSA | — | 本検討の対象（置き換え前提） |
| P-02 | MAU 10M（初回 100〜500 万） | ✅ | Users per user pool = 40,000,000（調整可） |
| P-03 | FIPS 140-3 不要（見込み） | ✅ | AWS マネージド。要件化した場合は別途確認 |
| P-04 | SLA 99.9% | ✅ | AWS SLA に依存 |
| P-05 | DR（RTO 1 日 / RPO 5 分） | 🟠 | **Multi-Region Replication（2026-06 提供開始）で RTO は分オーダー**。ただし RPO の数値保証なし・機能制限あり → [02-dr-analysis.md](02-dr-analysis.md) |
| **P-06** | **テナント分離 L2 単一 Realm + Organizations + tenant_id** | 🟠 | **Organizations 相当が無い**。groups はフラット。tenant_id はカスタム属性で代替可 |
| P-07 | 全顧客ユーザーはフェデレーション、IdP-KC 収容 | 🟢 | **2 層に分ける必要が消える**（§6.2）。1 つの user pool がローカル収容とフェデレーションを兼ねる |
| **P-08** | **識別子 3 階層（sub UUID / `<tenant>-<userid>` / IdP sub）** | 🟠 | **`sub` は RFC UUID ではない**（公式明記）。username は変更不可・削除後は再利用可 |
| **P-09** | **AT 30 分 / RT 30 日 + Rotation / 絶対 24h / アイドル 1h / ES256** | 🟠 | **ES256 不可（RS256 固定）**。セッション cookie は **1 時間固定・非設定** |
| P-10 | JWT クレーム最小・PII 非搭載 | 🟠 | ID トークンは app client の read 属性で制御可。ただし **ServiceNow OIDC 化で PII 経路の再設計が要る**（§4.3a）。**アクセストークン側は別問題で `aud` が無く、整形は Lambda 一択** → §5.5 |
| P-11 | SSO 信頼レベル L1 / L3 | 🟡 | L3（顧客 IdP へのログアウト連鎖）は標準に無く自作 |
| **P-12** | **JIT + SCIM 受信、Custom Authenticator SPI 案 B** | 🟡 | SCIM 受信は自作（Keycloak でも自作）。SPI 相当は Lambda トリガーで代替 |
| **P-13** | **ServiceNow パターン ②（L1 SCIM + L2 SAML JIT）** | **🟢** | **OIDC SSO + 自動プロビジョニングが公式機能として存在**（§4.2）。L2 を SAML → OIDC に組み替え |
| **P-14** | **新規 = OIDC / 既存 SP = SAML** | **🟢** | **SAML 提供先は ServiceNow 1 本のみ**（§4.1）。OIDC へ倒せば SAML IdP 能力が不要になる |
| P-15 | 東京 + 大阪 DR | **🔴** | **大阪は MRR 非対応**。DR 先が海外になり **APPI 越境移転（法 28 条）が新規発生** → [02-dr-analysis.md §3](02-dr-analysis.md) |
| **P-16** | **接続 IdP 数 1000 超想定** | **🔴** | **Identity providers per user pool = 既定 300 / 上限 1,000**（§3） |
| P-17 | IdP-KC を別アカウント・2 クラスタ | 🟢 | **概念が消える**（§6.2） |
| P-18 | インターネット境界は他組織管理 | 🟠 | Cognito はパブリックエンドポイント。CloudFront 前段配置の可否は**要確認 U-2** |
| P-19 | ブランド = Realm、issuer はブランド毎に単一 | 🟠 | user pool = issuer。ブランド分離は自然だが、IdP 上限の回避でプールを割ると issuer が増える |
| P-20 | idm-api（管理コントロールプレーン） | 🟢 | AWS SDK で大部分が置き換わる。**最も工数が減る箇所** |

---

## 3. 🔴 唯一の代替不能な障害 — 接続 IdP 数の天井が 1,000

### 3.1 一次資料

[Quotas in Amazon Cognito](https://docs.aws.amazon.com/cognito/latest/developerguide/limits.html) の **Quotas on resource number and size → User pools resource quotas** の表。

| Resource | Quota | Adjustable | Maximum quota |
|---|---:|:---:|---:|
| App clients per user pool | 1,000 | Yes | 10,000 |
| User pools per Region | 1,000 | Yes | 10,000 |
| **Identity providers per user pool** | **300** | **Yes** | **1,000** |
| Resource servers per user pool | 25 | Yes | 300 |
| Users per user pool | 40,000,000 | Yes | **Contact your account team** |

列の意味:

- **Quota** = 既定値
- **Adjustable** = Service Quotas から引き上げ申請できるか
- **Maximum quota** = **申請で到達できる上限**

### 3.2 この表の読みどころ

**`Users per user pool` だけ Maximum が "Contact your account team" なのに対し、`Identity providers per user pool` は 1,000 という数値で打ち切られている。**

AWS のクォータ表ではこの書き分けに意味があり、「アカウントチームに相談」は交渉余地を示し、**数値が入っているものは自己申請で到達できる天井**を意味する。P-16 は「1000 **超**想定」なので、**初日から上限に張り付く**。

確認は [Service Quotas コンソール（Cognito user pools）](https://console.aws.amazon.com/servicequotas/home/services/cognito-idp/quotas)で実値を見るのが確実。

### 3.3 Keycloak 側との比較

P-16 の出所は自社調査 [keycloak-1000idp-scalability-research.md](../basic-design/research/keycloak-1000idp-scalability-research.md)（2026-07-23）。

| Issue | 内容 | 状態 |
|---|---|---|
| **#21071** | 親 Epic「**1000+ IdP in a realm（might be even 10k or more）**」 | Closed 2024-07 |
| #30084 | 実行 Epic「Scalability of Identity Providers」受入基準 4 点完了 | Closed 2024-08 |
| #31249〜31254 | 新 SPI `IdentityProviderStorageProvider` + IdP 専用キャッシュ | Closed 2024-07〜08 |
| **#45293** | 「up to **10K IdPs** without noticeable impact」= 将来目標 | **Open** |
| keycloak-benchmark#382 | 数千 IdP ベンチ用データセット整備 | **Open** |

| | Keycloak | Cognito |
|---|---|---|
| 現在の目標値 | **1,000+**（26.0 で構造改修完了） | **1,000**（申請上の天井） |
| その先 | **10K を視野**（#45293、Open） | **なし** |
| 実測の裏付け | 公式ベンチ未公開（#382 Open）→ 本件は PoC 後追い | クォータとして明示 |

**Keycloak にとって 1,000 は通過点、Cognito にとっては天井**という構造的な差。なお公平に言えば **Keycloak 側も 1000 IdP の実測は未公開**で、違うのは「上限として宣言されているか否か」。

### 3.4 回避策（プール分割）とその副作用

user pool を複数に割れば IdP 総数は増やせる（最大 1,000 pool × 1,000 IdP）。ただし現行設計の根幹が崩れる。

| 崩れるもの | 内容 |
|---|---|
| **P-06 L2 単一 Realm** | `tenant_id` クレームによる単一境界が成立しなくなる |
| **P-19 issuer はブランド毎に単一** | pool ごとに issuer が変わる。**アプリは N 個の issuer を検証する** |
| ユーザー横断の検索・棚卸し | プールを跨いだ ListUsers ができない。管理・監査・停止伝播がプール数分になる |
| アプリの Client 管理 | app client は pool ごと。同じアプリを N pool に登録する |

→ [ADR-017](../adr/017-multitenant-l2-single-realm.md) の設計を捨てる判断になる。

### 3.5 判定を動かす鍵 = ブランドあたりの IdP 実数

P-19 で **Phase 1 = 1 ブランド**。**ブランド = user pool** と対応させたとき、そのブランドに紐づく顧客 IdP が 1,000 未満に収まるなら、「将来ブランドが増えたら pool を増やす」という自然な拡張になり、**P-06 を崩さずに済む**。

**顧客 IdP の実数が分かれば 🔴 が 🟠 に下がる。**（未確認 U-6）

---

## 4. 🟢【解消】SAML IdP 不可 — ServiceNow の OIDC 化で回避できる

初版では「代替不能」と判定したが、調査の結果**解消可能**と分かった。経緯を記録として残す。

### 4.1 Cognito は SAML IdP になれない（事実そのものは変わらない）

| # | パターン | Cognito の役割 | 可否 |
|:-:|---|---|:-:|
| A | 自社アプリ → Cognito（OIDC / OAuth2） | **OIDC の IdP** | ✅ |
| B | 外部 SAML IdP（AD FS / Entra）→ Cognito | **SAML の SP** | ✅ |
| **C** | **Cognito → 外部 SAML SP（ServiceNow 等）** | **SAML の IdP** | ❌ **不可** |
| D | IdP-initiated SAML（外部 IdP 起点）→ Cognito | SAML の SP | ✅（条件付き） |
| E | Cognito user pool → Cognito identity pool | third-party IdP | ✅（AWS 内部・SAML ではない） |

**根拠**: [Using SAML identity providers with a user pool](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-saml-idp.html) が公開している SAML 用エンドポイントは 2 つだけ。

```
SP entity ID : urn:amazon:cognito:sp:{us-east-1_EXAMPLE}
ACS URL      : https://{Your user pool domain}/saml2/idpresponse
```

ACS は「アサーションを**受け取る**先」で、IdP に必要な **SSO エンドポイントも IdP メタデータも存在しない**。本文も一貫している。

> Amazon Cognito can **process SAML assertions from** your third-party providers into that SSO standard.
> …authenticates local and third-party IdP users and **issues JSON web tokens (JWTs)**.
> **A user pool can be a third-party IdP to an identity pool.**（IdP になれる相手は identity pool だけ）

**入力は SAML を受けられるが、出力は JWT のみ。** これは出力側の制約なので、内部構成（ブローカー分離の有無）では解決しない。

### 4.2 しかし提供先は ServiceNow 1 本だけで、ServiceNow は OIDC でも JIT できる

**(1) 提供先の棚卸し**

[api-provision-matrix](../basic-design/research/api-provision-matrix-2026-09-09.md) の「業務システムへの認証提供」は 1 行のみ。

| 機能 | エンドポイント | 備考 |
|---|---|---|
| 業務システムへの認証提供 | `POST/GET /realms/{r}/protocol/saml` | **ServiceNow へは SAML で提供する** |

[U10](../basic-design/10-integration-migration-design.md) の SAML Client 定義も `CL-SN-01`（ServiceNow 用）1 本のみ。**他に SAML IdP 能力を要求する連携先はない。**

**(2) ServiceNow の OIDC SSO は自動プロビジョニングに対応している**

[Create an OpenID Connect (OIDC) configuration for Single Sign-on](https://www.servicenow.com/docs/bundle/zurich-platform-security/page/integrate/single-sign-on/task/create-OIDC-configuration-SSO.html)（Zurich / Xanadu / Yokohama に同一ページ）:

> **When automatic user provisioning is enabled, a user record is automatically created in the ServiceNow instance if that user record does not exist.**

| フィールド | 内容 |
|---|---|
| **Automatically provision users** | IdP のユーザーに SN アカウントが無い場合、User テーブルに自動作成 |
| **Provision using** | **ID Token / User Info endpoint / Both** から選択 |
| Provision data source | ID token 側のデータソース |
| User Info Datasource | userinfo 側のデータソース |
| **Update User on next login** | 次回ログイン時にユーザーレコードを更新 |
| Update User Interval Time | 更新の最小間隔（既定 3,600 秒） |
| User roles applied to provisioned users | 自動作成したユーザーへのロール付与 |

前提条件も Cognito で満たせる。

| ServiceNow が要求 | Cognito |
|---|:-:|
| Client ID / Client Secret | ✅ confidential app client |
| **Well-known configuration URL** | ✅ `https://cognito-idp.{region}.amazonaws.com/{poolId}/.well-known/openid-configuration` |
| Multiple Provider Single Sign-On Installer プラグイン | ✅ SAML 版と同じプラグイン |

**(3) SAML 版より素直**

| | SAML 版 | OIDC 版 |
|---|---|---|
| JIT の実装 | 一時テーブル `u_imp_saml_user_<suffix>` + transform map 経由 | **設定フィールドで直接** User テーブルへ |
| 属性の再同期 | 標準機能なし | **Update User on next login + 間隔設定** |
| 取得元 | Assertion のみ | **ID Token / userinfo / 両方**を選べる |

### 4.3 ただし移行で 3 つ変わる

**(a) PII の扱いが P-10 と衝突する ★要注意**

現行 U10 の整理:

> **PII 整合の注記**: SAML Assertion への氏名・email 送出は JWT の PII 非搭載原則（P-10 / U5 §5.1.4）の**対象外**（宛先 SP 限定・署名付き・ブラウザ POST の point-to-point 配送）

OIDC に倒すと ID トークンに PII を載せることになり、**P-10 と正面衝突**する。

**回避策**: ServiceNow の `Provision using` で **User Info endpoint** を選べば、PII は ID トークンではなく userinfo から取得される。ID トークンは最小クレームのまま保てる。**この選択肢の存在が OIDC 化の成立条件**。

**(b) 識別子のマッピングを組み直す**

| | SAML 版 | OIDC 版 |
|---|---|---|
| 主識別子 | NameID = `username` 全体（format = unspecified） | `sub` または任意クレーム |
| 突合キー | SAML Attribute `employee_number` = `external_id` 生値 | ID token / userinfo のクレーム |

SN 側の matching field は「**移行前に確定し、以後変更しない**」（SN guide アンチパターン 2）とされているため、**移行タイミングでしか変えられない**。

**(c) Token Exchange が使えない**

「業務システムから他アプリへの連携」は `token-exchange` 前提だが、**Cognito は RFC 8693 非対応**。ただし **Phase 1 対象外**（FR-AUTH-005）のため当面はブロッカーにならない。

**(d) 副次的に解決するもの**

- **IdP-Initiated SSO の無効化**（[ADR-057](../adr/057-csrf-protection-responsibility-boundary.md) §E.2 の CSRF 対策）→ OIDC は RP-initiated が基本なので論点自体が消える
- **SAML 署名鍵・証明書のローテーション**（U7 / ADR-045 への要求）→ 不要になる
- **顧客ごとの SAML Client 発行**（SN インスタンス単位に 1 本）→ app client に置き換え。app client は 1 pool あたり既定 1,000 / 上限 10,000 で IdP 上限より余裕がある

---

## 5. 🟠 要件かアーキテクチャの変更が必要なもの

### 5.1 署名アルゴリズムが RS256 固定（P-09）

- Cognito は **RS256 のみ**。設定項目が存在しない
- JWKS に出るのは常に `"kty": "RSA"` で、**EC 鍵は原理的に現れない**

P-09 は **ES256** を指定（§NFR-4.2 / ADR-045）。

**回避策**: 後段の Lambda / API 層で RS256 トークンを検証し自前で ES256 を再発行する。ただし「認証基盤がトークンを発行する」構造を壊すので、**実質的に自前 IdP を持つのと変わらない**。

→ **まず「ES256 は必須要件か」を確認すべき**（未確認 U-5）。規制要件でなく設計選好なら RS256 受容で解決する。

> なお **SAML 側の署名は RSA-SHA256** と U10 が定めており（「P-09 の ES256 は JWT 側の規約であり SAML には適用しない」）、ServiceNow を OIDC 化すると SAML 署名鍵の論点自体が消える。

### 5.2 カスタム属性スキーマが不可逆（属性正準化 D3-15）

公式の記述:

> You can add up to **50 custom attributes** to your user pool.
> **You can't remove or change it after you add it to the user pool.**

| 制約 | 値 |
|---|---|
| カスタム属性の数 | **50（調整不可）** |
| 属性名の文字数 | **20 文字** |
| 属性値のサイズ | 2,048 バイト |
| ID トークンへの出力 | **文字列としてのみ**（number / boolean も文字列化） |
| 必須/任意の切替 | **プール作成後は変更不可** |

現行の[正準スキーマ](../basic-design/research/attribute-canonicalization-notes.md)は組織属性 8 + ライフサイクル属性 + `tenant_id` + 識別子系で **15〜20 個規模**。50 枠自体は足りるが、**一度作ったら消せない**ため設計変更のたびに廃棄属性が溜まる。

**さらに踏みやすい罠**が公式に明記されている。

> Sign-in with a third-party IdP: … This is possible but **not practical**, because the user will only be able to sign in one time. On sign-in attempts after their first, Amazon Cognito **rejects the attempt** because of the mapping rule to a now-unwriteable attribute.

immutable 属性に IdP マッピングを張ると **2 回目のログインが失敗する**。現行の「②基盤付与を①顧客写像で上書きしない規約」（syncMode=IMPORT 相当）を実装しようとするとここに直撃する。

### 5.3 セッション制御の粒度が足りない（P-09）

| P-09 の要件 | Cognito |
|---|---|
| アクセストークン 30 分 | ✅ 設定可（5 分〜1 日） |
| リフレッシュトークン + Rotation | ⚠ **2025-04 追加。Essentials / Plus が必要**。有効化すると `REFRESH_TOKEN_AUTH` が使えない |
| **絶対タイムアウト 24h** | ❌ 相当する概念が無い |
| **アイドルタイムアウト 1h** | ⚠ managed login の cookie が 1 時間だが **設定不可・スライドしない** |
| ログアウトでセッション破棄 | ⚠ **`GlobalSignOut` では cookie が消えない**。Logout エンドポイントへのリダイレクトが必須 |

最後の項目は事故になりやすい。「サインアウトしたのにブラウザを戻ると資格情報なしで再認証される」状態が残る。

### 5.4 `sub` が RFC UUID ではない（P-08）

> Amazon Cognito generates `sub` in an Amazon Cognito-specific format that **doesn't conform to a specific UUID format, including RFC UUID**. You shouldn't strictly validate the format of `sub`.

P-08 は「3 階層（**sub UUID** / `<tenant>-<userid>` / IdP sub）」。開発標準で「**アプリ側 DB の外部キーは必ず `sub`**」と定めているため、アプリが `UUID` 型カラムを切っていると型が合わない。

影響は限定的だが、**アプリ標準の文言修正とベンダーへの再告知**が必要。あわせて `username` は**作成後変更不可**（規約と相性が良い）だが**削除後は再利用できてしまう**点も確認が要る。

### 5.5 トークン制御の実装モデル — 宣言的マッパー vs 単一 Lambda（P-10 / ADR-030）★v4 新規

Keycloak と Cognito の差は「できる / できない」ではなく、**コードに落ちる範囲と、そのコードが何本に分かれるか**にある。Cognito でも全て実装可能だが、**実装の総量が多く、かつ 1 本の関数に集約される**。

#### (a) やりたいこと別の実現手段

◎ = 宣言的（設定のみ）/ ▲ = コード必要 / ✕ = 不可

| やりたいこと | Keycloak | Cognito |
|---|:---:|:---:|
| ユーザー属性をクレームに | ◎ User Attribute Mapper | ◎ ID トークンには自動搭載 |
| クレーム名の変更・名前空間・ネスト | ◎ Token Claim Name（`a.b.c` 記法） | ▲ Lambda |
| ロール / グループをクレームに | ◎ Realm/Client Role・Group Membership Mapper | ◎ `cognito:groups` は自動。**整形・絞り込みは** ▲ |
| **アクセストークンへの独自クレーム** | ◎ マッパーのチェックボックス | ▲ **Pre Token Generation V2 + Essentials/Plus** |
| **`aud`（audience）の制御** | ◎ Audience Mapper | **✕ → ▲**（下記 (b)） |
| 要求スコープに応じた出し分け | ◎ Client Scope にマッパーを紐付け | ▲ Lambda 内で分岐 |
| クライアント（Web/モバイル）別の出し分け | ◎ Client Scope 割当 | ▲ Lambda 内で `clientId` 分岐 |
| 値の加工・計算・条件付き値 | ▲ Java ProtocolMapper SPI | ▲ Lambda |
| 外部 DB / API を引いて付与 | ▲ Java SPI（Keycloak 内の同期 I/O は非推奨） | ▲ **Lambda（VPC・IAM が揃い素直）** |
| フェデ時 IdP クレーム → ローカル属性 | ◎ Attribute Importer | ◎ 属性マッピング（**1:1 のみ・変換不可**） |
| **IdP クレーム値に応じたロール / グループ付与** | ◎ **Advanced Claim to Role / to Group** | **✕ → ▲** Lambda + `AdminAddUserToGroup` |
| pairwise subject（クライアント別 `sub`） | ◎ Pairwise Subject Identifier Mapper | ✕ |
| クレームの削除・秘匿 | ◎ マッパーを外す | ▲ `claimsToSuppress` |

#### (b) `aud` 欠落は Lite を選べなくする 3 本目の理由

[ADR-030 §F](../adr/030-minimal-jwt-claim-design.md) が既に指摘しているとおり、**Cognito のアクセストークンには `aud` クレームが無い**（`client_id` / `scope` / `token_use` のみ）。ADR-030 §E は `aud` を **「❌ 削るな（token confused deputy 攻撃）」** と判定しており、対処 A（**Pre Token Generation V2 で注入**）を本基盤推奨としている。

**V2 は Essentials / Plus ティア必須**。したがって §7「読み方 2」の Lite 棄却理由に **3 本目**として加わる。

> 対処 B（API 側で `aud` 検証を捨て `client_id` 検証に置換）なら Lite でも通るが、OAuth 標準から外れ、API プラットフォーム側の検証規約（ADR-030 §E）を崩す。

#### (c) トークン制御が Pre Token Generation 1 本に集約される

Cognito の Lambda トリガーは **User Pool あたりトリガー種別ごとに 1 本**。結果として次がすべて同じ関数に相乗りする。

| 責務 | Keycloak での置き場所 | Cognito |
|---|---|---|
| 停止伝播の判定 | Custom Authenticator SPI（案 B） | Pre Token Generation |
| `aud` 注入 | Audience Mapper（**設定**） | Pre Token Generation |
| クレーム整形・名前空間 | Protocol Mapper（**設定**） | Pre Token Generation |
| IdP クレーム → ロール / グループ | Advanced Claim to Role/Group（**設定**） | Pre Token Generation |

生じる差:

- **全トークン発行（リフレッシュ含む）の同期パス上に Lambda が常駐**する。例外 = ログイン失敗、コールドスタート = 認証レイテンシ
- 接続アプリが増えるたびに `clientId` 分岐がこの 1 関数に積まれる。**共有基盤の単一障害点かつ変更集中点**になる
- Keycloak 側は上記 4 つのうち **3 つが宣言的マッパー**（コード 0 行・実行時障害点なし・IaC で即時反映）

#### (d) 判定

**🔴 にはならない。** すべて Lambda で実装可能であり、代替不能な障害ではない。効果は次の 2 点にとどまる。

1. 🟠 が 2 件増える（`aud` 欠落 / 単一 Lambda への集約）
2. §7「読み方 1」の根拠が**構築工数の差だけ**に痩せる（Lite 比較が使えないため）

したがって **判断の主軸が U-6 / U-13 / U-8 であることは変わらない**。本節は、それら 3 件がクリアして「コストと 🟠 群のトレードオフ」に落ちた場合に、🟠 群の重さを測る材料として使う。

---

## 6. 🟡 自作で埋まるもの / 🟢 Cognito が有利なもの

### 6.1 自作が必要（ただし Keycloak でも自作する）

| 項目 | Cognito | 現行 Keycloak |
|---|---|---|
| **SCIM 受信** | 標準機能なし → Facade 自作 | 同じく Facade 自作（D3-11） |
| **HRD（振り分け）** | `idp_identifier` + Identifiers per IdP 50 で**ドメイン振り分けは可能**。識別子ベースは自作 | 方式 A Custom SPI（ADR-055） |
| **JIT の制御** | Pre sign-up / Pre token generation Lambda トリガー | Custom Authenticator SPI 案 B |
| **停止伝播・ライフサイクル** | AdminDisableUser + カスタム属性 + EventBridge | 同等の自作 |

→ **この 4 つは「どちらも自作」という点では差分にならない。**

ただし **自作の総量と分割可能性は同じではない**。トークン整形・`aud` 注入・ロール付与は Keycloak では宣言的マッパー（設定）で済むのに対し、Cognito では上記の停止伝播判定と**同じ Pre Token Generation 関数**に集約される。詳細は **§5.5 (c)**。

### 6.2 ブローカーと IdP を分ける必要が消える ★新規

現行で 2 層（Broker KC + IdP-KC）に分けている理由は [ADR-033](../adr/033-keycloak-2tier-broker-idp-architecture.md) と P-17。

> **IdP-KC = 隔離した自前アカウント**（VPC 分割でなく**アカウント分割**）: **PW ハッシュのブラスト半径**のため、業務アプリを同居させない

**「自分でパスワードハッシュを持つから隔離が要る」**という動機なので、AWS がパスワードを保持する Cognito では**この分離動機自体が消える**。1 つの user pool が「ローカルユーザーの収容」と「外部 IdP へのフェデレーション」を兼ねる。

同時に不要になるもの: **ROSA クラスタ 2 つ / Aurora 2 つ / アカウント分割 / PrivateLink 単方向 / 内部 NLB 2 本 / VPC-K・VPC-M 分離**。**U6（インフラ設計）の相当部分が消える。**

### 6.3 その他

| 項目 | 内容 |
|---|---|
| **パスワード変更・再設定 API** | `ChangePassword` / `ForgotPassword` / `ConfirmForgotPassword` が**標準 API として存在**。Keycloak で未決の A-1（画面誘導しかない）・§4.3（忘れた人の再設定）・M-Q-11-6（2-tier での `kc_action`）が**まるごと消える** |
| **運用負荷** | クラスタ版上げ・証明書更新・SRE 境界（ADR-056 §L7）が消える |
| **構築工数** | idm-api（P-20）の大半が AWS SDK 呼び出しに置き換わる。現行 WBS **545〜1,026 人日**の相当部分が削減対象 |
| **拡張 1 件あたりの実装コスト** ★v4 | **コードを書くことになった場合の単価は Cognito の方が軽い**。Lambda は Node / Python で書け、**IdP 本体のイメージ再ビルドが不要**、要員も調達しやすい。対して Keycloak の Custom SPI は Java + カスタムイメージ CI + **Keycloak バージョン追従**（`spi-private` は破壊的変更あり）+ **Red Hat サポート対象外**という固定費を伴う。§5.5 は「コードに落ちる件数」で Keycloak 有利と述べているが、**単価はこの逆**である点を併記する |

---

## 7. コストの再計算

Cognito の料金は **フェデレーション（SAML/OIDC）ユーザーが全ティア共通で $0.015/MAU**。P-07 により顧客ユーザーの相当数がフェデレーション扱いになるため、ティア選択の効果は限定的。

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
2. ただし **Lite は ①Managed Login 不可・②Refresh Token Rotation 不可・③アクセストークンへの `aud` 注入不可**（Pre Token Generation V2 が Essentials/Plus 必須 → **§5.5 (b)**）。実用上は Essentials → **$180K/年**。**結果として 100 万 MAU の比較は「$119K ≈ $122K」ではなく「Essentials $180K vs Keycloak $122K」で確定**し、読み方 1 の根拠は**構築工数の差だけ**になる
3. **500 万を超えると逆転**。10M では [ADR-032](../adr/032-ciam-platform-cost-comparison-10m-mau.md) の結論（14 倍差）がそのまま再現される
4. P-02 は「**設計上限 10M / 初回 100〜500 万**」なので、**損益分岐は初回リリースと最終到達点の間にある**

> ⚠ **M2M（client_credentials）は別課金**: $0.00225 / トークンリクエスト。現行設計は M2M トークンを常用するため**別途見積もりが必要**（未確認 U-4）。

---

## 8. もし Cognito でやるなら — 変更が必要な決定

| 決定 | 現状 | 必要な変更 |
|---|---|---|
| **P-16 / ADR-017** | 1000 超 IdP・L2 単一 Realm | **ブランドあたり 1,000 未満に収まることを確認**。収まらなければプール分割前提のマルチ issuer 設計へ |
| **P-13 / ADR-023 / U10** | ServiceNow L2 = SAML JIT | **L2 を OIDC SSO + Automatically provision users に組み替え**。§4.3 の 3 点（PII は userinfo 経由 / 突合キーの再設計 / Token Exchange 不可）を反映。SAML Client `CL-SN-01` は廃止し OIDC Client へ |
| **P-14** | 既存 SP = SAML | **ServiceNow のみだったため撤廃可**。「全 SP が OIDC」に統一 |
| **P-09 / ADR-045** | ES256 / 絶対 24h / アイドル 1h | **RS256 受容**。セッション設計を作り直す。SAML 署名鍵の要求（U7）は ServiceNow OIDC 化で消える |
| **P-10 / U5** | JWT は PII 非搭載 | ServiceNow への PII 送出経路を **userinfo に確定**して明文化 |
| **D3-15 属性正準化** | User Profile 宣言 + syncMode 制御 | **不可逆スキーマ前提で属性表を凍結**。immutable + IdP マッピングの禁則を追加 |
| **P-08 / ADR-018** | sub = UUID | **sub は不透明文字列**としてアプリ標準を改訂 |
| **P-17 / ADR-033 / U6** | Broker + IdP-KC の 2 クラスタ・アカウント分割 | **2 層構成を廃止**（§6.2）。U6 の VPC / NLB / PrivateLink 設計が大幅縮小 |
| **ADR-062 / P-20** | idm-api = Lambda | 大幅縮小（AWS SDK 直呼びへ） |
| **D3-05** | アプリ発 CRUD は専用 API 層 | Cognito Admin API + IAM で代替可能か再評価 |
| **ADR-057 §E.2** | SAML IdP-Initiated SSO 拒否 | OIDC 化で論点消滅 |

---

## 9. 未確認事項

| # | 項目 | なぜ要るか | 優先 |
|---|---|---|:-:|
| **U-6** | **ブランドあたりの顧客 IdP 実数** | **唯一の 🔴 を 🟠 に下げられるか**が決まる。P-19 で Phase 1 = 1 ブランド | **最優先** |
| **U-5** | **ES256 は規制要件か設計選好か** | 後者なら 🟠 が 1 件減る | 高 |
| ~~U-1~~ | ~~DR の可否と RPO~~ → **調査完了**。[02-dr-analysis.md](02-dr-analysis.md) に分離。新たな未確認 U-8〜U-13 を同文書に記載 | — | 済 |
| U-2 | **P-18 境界**: Cognito のパブリックエンドポイントを他組織管理の CloudFront + WAF 配下に置けるか | 現行の境界設計の前提 | 中 |
| U-3 | **PCI DSS / APPI**: 責任共有モデル下での証跡・削除証明 | [3 段階削除モデル](../basic-design/03-identity-provisioning-design.md)の第 3 段階（物理削除 + 完了証明書）が成立するか | 中 |
| U-4 | **M2M 課金の実測見積り** | $0.00225 × 想定トークンリクエスト回数 | 中 |
| U-7 | **ServiceNow OIDC の実機検証** | 公式には JIT 対応と明記。ただし OIDC SSO は SAML より事例が少なく、IdP 実装との相性で失敗報告もある | 中 |

---

## 10. 出典

### AWS 公式
- [Quotas in Amazon Cognito](https://docs.aws.amazon.com/cognito/latest/developerguide/limits.html) — IdP 数・プール数・カスタム属性数ほか
- [Working with user attributes](https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-settings-attributes.html) — カスタム属性の不可逆性・`sub` の形式・immutable 属性の罠
- [Amazon Cognito Pricing](https://aws.amazon.com/cognito/pricing/) — Lite / Essentials / Plus 単価、M2M 単価
- [Using SAML identity providers with a user pool](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-saml-idp.html) — SP entity ID / ACS URL のみ公開（IdP 側の口が無い根拠）
- [Understanding the identity (ID) token](https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-the-id-token.html) — RS256 固定
- [Refresh tokens](https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-the-refresh-token.html) — Rotation の挙動
- [Amazon Cognito now supports refresh token rotation](https://aws.amazon.com/about-aws/whats-new/2025/04/amazon-cognito-refresh-token-rotation/) — 2025-04 提供開始・ティア要件
- [User pool managed login](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-managed-login.html) — セッション cookie 1 時間

### ServiceNow 公式
- [Create an OpenID Connect (OIDC) configuration for Single Sign-on](https://www.servicenow.com/docs/bundle/zurich-platform-security/page/integrate/single-sign-on/task/create-OIDC-configuration-SSO.html) — **自動ユーザープロビジョニング対応の根拠**（§4.2）
- [Multiple Provider Single Sign-On](https://www.servicenow.com/docs/bundle/zurich-platform-security/page/integrate/single-sign-on/concept/c_MultipleProviderSingleSignOn.html) — SAML / OIDC 両対応
- [SAML user provisioning](https://www.servicenow.com/docs/r/platform-security/authentication/c_SAMLUserProvisioning.html) — SAML 版 JIT（一時テーブル + transform map 方式）

### コミュニティ / 補足
- [AWS re:Post — AWS Cognito as a SAML IdP](https://repost.aws/questions/QUxHUXiD0PRXa4iabxu62IrA/aws-cognito-as-a-saml-idp) — SAML IdP 非対応の確認
- [AWS re:Post — Is the Cognito hosted UI browser session length configurable?](https://repost.aws/questions/QUjTUqjCB-QuyVW6B-HQYSFg/is-the-cognito-hosted-ui-browser-session-length-configurable) — cookie 長の非設定性
- [Teaching Cognito to speak SAML（Medium）](https://medium.com/@johannesfloriangeiger/teaching-cognito-to-speak-saml-35f99262b739) — Keycloak を SAML facade にする回避策（本件では採らない）

### 本プロジェクト
- [ADR-032 CIAM プラットフォーム選定（10M MAU コスト比較）](../adr/032-ciam-platform-cost-comparison-10m-mau.md)
- [ADR-016 Cognito 機能ティア選定](../adr/016-cognito-feature-tier-selection.md) / [ADR-006 損益分岐](../adr/006-cognito-vs-keycloak-cost-breakeven.md)
- [ADR-017 マルチテナント L2](../adr/017-multitenant-l2-single-realm.md) / [ADR-023 ServiceNow SP 連携](../adr/023-servicenow-sp-integration.md) / [ADR-033 2-tier](../adr/033-keycloak-2tier-broker-idp-architecture.md)
- [01-architecture-baseline.md 前提 P-01〜P-20](../basic-design/01-architecture-baseline.md)
- [10-integration-migration-design.md（U10、ServiceNow 連携）](../basic-design/10-integration-migration-design.md)
- [attribute-canonicalization-notes.md](../basic-design/research/attribute-canonicalization-notes.md)
- [keycloak-1000idp-scalability-research.md](../basic-design/research/keycloak-1000idp-scalability-research.md)
