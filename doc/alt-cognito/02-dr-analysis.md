# Cognito の DR — Multi-Region Replication の実態と適合性

作成: 2026-09-16
位置づけ: [01-requirement-gap-analysis.md](01-requirement-gap-analysis.md) の **未確認 U-1（DR）**を掘り下げたもの。別世界線の検討であり本線の設計を変更しない。
対象要件: **P-05（RTO 1 日 / DR 障害時 3 日、RPO 5 分）** / **P-15（東京 + 大阪）**

---

## 1. 結論

**DR の「手段」は 2026-06 に登場した。しかし本件の要件には 3 つの壁がある。**

| # | 壁 | 深刻度 |
|:-:|---|:-:|
| **1** | **大阪リージョンが非対応**。日本国内でのペアが組めず、DR 先は韓国・シンガポール等の**海外**になる → **APPI 越境移転（法 28 条）が新規に発生** | 🔴 |
| **2** | **TOTP MFA がセカンダリで動かない**。MFA 設定済みユーザーは**フェイルオーバー中に一切ログインできない** | 🔴 |
| **3** | **フェデレーションユーザーは「プライマリで 1 回でもログイン済み」でないとセカンダリで認証できない**。新規ユーザー（JIT）は DR 中ログイン不可 | 🟠 |

一方で**良い面もはっきりしている**。

- **RTO は現行 Keycloak 設計より桁違いに良い**（Route 53 ヘルスチェックで分オーダー vs 現行 Tier 3+ の **RTO ≈ 14 日**）
- サインイン済みユーザーは**再認証なしで継続**でき、どちらのリージョンが発行したトークンも相互に有効

**総合判定: 🟠（要件かアーキの変更が必要）**。壁 1 は法務判断、壁 2 は MFA 方式の見直しで動く余地がある。

---

## 2. Multi-Region Replication（MRR）とは

**2026-06-04 提供開始**の機能（[AWS What's New](https://aws.amazon.com/about-aws/whats-new/2026/06/amazon-cognito-multi-region/)）。

### 2.1 仕組み

> When you configure MRR, Amazon Cognito creates separate user pools with **a shared user pool ID**. Each replica user pool hosts authentication services for a shared user directory. The primary user pool serves as the **authoritative source** for administrative configuration and write operations such as password resets and user sign-up. **Secondary user pools can't create users.**

| 項目 | 内容 |
|---|---|
| 構成 | プライマリ 1 + **セカンダリ 1（最大 1 つのみ）** |
| user pool ID | **両リージョンで共有**（同じ ID） |
| 複製の向き | **プライマリ → セカンダリの一方向** |
| 複製されるもの | ユーザー・**資格情報（パスワード）**・user pool 設定・フェデレーション設定 |
| 整合性 | **結果整合性**（"might introduce brief delays … eventually consistent"） |
| トークン | **どちらのリージョンが発行したトークンも両方で有効** |

### 2.2 前提条件

| 前提 | 内容 |
|---|---|
| フィーチャープラン | **Essentials または Plus**。**Lite では有効化できない** |
| 暗号鍵 | **マルチリージョン カスタマーマネージド KMS キーが必須**。全レプリカリージョンで利用可能であること |
| インフラ世代 | **「modern Amazon Cognito infrastructure」が必要**。旧世代のプールは AWS によるアップグレード待ちで、コンソールに例外メッセージが出る |
| issuer | リージョン跨ぎのトークン検証一貫性のため **issuer の更新を推奨**。ブログによれば**クライアントアプリの URL 更新と再デプロイが必要** |

---

## 3. 🔴 壁 1: 大阪が対応していない

### 3.1 対応リージョン（公式・2026-06-04 時点）

> US East (Ohio, N. Virginia), US West (N. California, Oregon), **Asia Pacific (Mumbai, Seoul, Singapore, Sydney, Tokyo)**, Canada (Central), Europe (Frankfurt, Ireland, London, Paris, Stockholm), and South America (São Paulo)

| リージョン | 対応 |
|---|:-:|
| **東京（ap-northeast-1）** | ✅ |
| **大阪（ap-northeast-3）** | ❌ **非対応** |
| ソウル / シンガポール / シドニー / ムンバイ | ✅ |

**P-15 は「東京 ap-northeast-1（常用）+ 大阪 ap-northeast-3（DR）」**なので、**そのままでは組めません**。

### 3.2 これが法務論点に直結する

現行の APPI 整理は「**データは国内**」を前提に組み立てられています。[appi-legal-issues-summary.md](../common/appi-legal-issues-summary.md) より:

> **懸念**: 東京・大阪リージョンのみ（データは国内）なら、外国関連の公表は不要ではないか。

> **AWS** | ① クラウド事業者が所在する外国の名称 ② 個人データが保存されるサーバが所在する外国の名称（**本基盤は日本国内**）

MRR のセカンダリを**ソウルやシンガポールに置くと、個人データ（パスワード資格情報を含む）が国外のサーバに保存されます**。これは法 32 条の公表内容が変わるだけでなく、**法 28 条（外国にある第三者への提供）の越境移転根拠**を新たに立てる必要が生じます。

| 越境移転の根拠 | 韓国 / シンガポール / 豪州の場合 |
|---|---|
| 同等水準国 | ❌ 日本の指定は **EU と英国のみ**。いずれも該当しない |
| 規則 16 条の体制整備 | ⚠ AWS との契約で構成可能だが、**基準適合体制の整備 + 本人への情報提供**が必要 |
| 本人同意 | ⚠ 「外国にある第三者への提供」の同意を**全ユーザーから**取得する必要 |

現行設計は **Red Hat SRE の越境アクセス（懸念 B）1 点**に論点を絞り込んでいます（「残るは Red Hat SRE の越境閲覧の確認 1 点」）。MRR を海外リージョンで使うと、**論点が「越境アクセス」から「越境保存」に拡大**します。前者より後者の方が重い論点です。

### 3.3 取りうる選択肢

| 案 | 内容 | 評価 |
|---|---|---|
| ① 大阪の対応を待つ | AWS のリージョン拡大待ち | ⚠ 時期未定。**設計の前提にできない** |
| ② ソウル等を DR 先にする | 越境移転の根拠を整備 | ⚠ 法務判断。**顧客合意も要る可能性** |
| ③ MRR を使わず単一リージョン | DR なし（東京のみ） | ⚠ P-05 を満たさない。ただし**現行 Keycloak も実質これに近い**（§7） |
| ④ MRR + バックアップ併用 | MRR は使わず、ユーザーデータのエクスポートで代替 | ❌ **パスワードをエクスポートできない**（§6.3） |

---

## 4. 🔴 壁 2: TOTP MFA がセカンダリで動かない

公式の明記です。

> **TOTP MFA is not supported in secondary replicas.** Users with TOTP MFA configured **must authenticate when the user pool in the primary Region is servicing requests.**

つまり **TOTP を設定済みのユーザーは、フェイルオーバー中に認証できません**。「MFA をスキップして入れる」のではなく、**プライマリが復旧するまでログイン不可**です。

本件では §FR-5.2 が **NIST AAL2** を参照しており、MFA は前提機能です。**MFA を有効にしているユーザーほど DR 中に締め出される**という、要件と逆向きの挙動になります。

**回避策の方向性:**

| 案 | 内容 | 注意 |
|---|---|---|
| SMS MFA / Email MFA へ寄せる | TOTP 以外の要素を使う | AAL2 の要件充足度が下がる（SMS は NIST で非推奨方向）。SMS/Email はリージョンごとに個別設定が必要 |
| Passkey / WebAuthn | Cognito は WebAuthn 対応（1 ユーザー 20 authenticator まで） | **セカンダリでの対応可否は未確認**（U-8） |
| DR 中は MFA 必須ユーザーを諦める | 事業影響を受容 | 管理者・特権ユーザーほど MFA 必須なので、**DR 中に管理者が入れない**ことになりかねない |

---

## 5. 🟠 壁 3: フェデレーションユーザーの初回ログイン制約

公式の明記です。

> **Federated users can only sign in to a secondary user pool in the failover state if they have previously signed in to the primary user pool.**

**P-07 は「全顧客ユーザーはフェデレーション」**なので、この制約が全ユーザーにかかります。

| ユーザー | フェイルオーバー中 |
|---|:-:|
| プライマリでログイン実績あり | ✅ ログイン可 |
| **初回ログイン（= JIT でこれから作られる）** | ❌ **ログイン不可** |

**P-12（JIT プロビジョニング）と正面衝突**します。DR 中に入社・異動・新規契約で発生したユーザーは、プライマリが復旧するまで一切利用できません。

P-05 の「**DR 障害時 3 日**」を採ると、**最大 3 日間、新規ユーザーがゼロ人も入れない**ことになります。事業影響を先に評価すべき論点です。

---

## 6. その他の制約

### 6.1 セカンダリでできないこと

| 操作 | 可否 |
|---|:-:|
| ユーザーのサインイン・トークン発行 | ✅（ACTIVE 時） |
| リフレッシュトークンによる更新（`GetTokensFromRefreshToken`）| ✅ |
| グローバルサインアウト / トークン失効 | ✅ |
| **ユーザーの新規作成**（サインアップ・管理者作成とも） | ❌ |
| **パスワードのリセット** | ❌ |
| **プロフィールの変更** | ❌ |
| **TOTP MFA での認証** | ❌ |

公式は UI 側での対処を求めています。

> In a failover state, **disable these operations in the user interface** and make them available after your health check restores access to the primary user pool.

→ **アプリ側に「DR モード」の画面制御を実装する義務**が発生します。これは Keycloak 版には無い作業です。

### 6.2 リージョンごとに手動設定が要るもの

以下はプライマリから自動同期**されず**、レプリカ側で個別に設定します。

- **Lambda トリガー** ← JIT 制御を Lambda で実装する設計なら**二重管理**
- Email 設定 / 脅威保護通知の Email 設定 / SMS 設定
- **AWS WAF web ACL**
- ログエクスポート設定 / タグ

### 6.3 ロックアウトカウンタが同期されない

> The count of password-based authentication attempts before lockout **isn't synchronized across Regions.** Each replica maintains its own count of failed authentication attempts.

平時は問題になりませんが、**両リージョンが到達可能な状態では試行回数が実質 2 倍**になります。ブルートフォース耐性の評価に影響します。

### 6.4 そもそもバックアップでの代替はできない

MRR を使わない場合の代替手段として「ユーザーをエクスポートして別リージョンに復元」を考えたくなりますが、**Cognito はパスワードハッシュをエクスポートできません**。`ListUsers` / `AdminGetUser` で取れるのは属性のみです。

→ **MRR を使わない限り、パスワードを持つユーザーの DR は原理的に成立しません**（全員にパスワード再設定を強いることになる）。これが「Cognito の DR は難しい」と言われてきた理由であり、**MRR はまさにその解決策として出てきた機能**です。

---

## 7. フェイルオーバーの実際

### 7.1 2 つの経路で挙動が違う

| 経路 | フェイルオーバー方式 |
|---|---|
| **Managed login / フェデレーション / M2M** | **Route 53 ヘルスチェック**を user pool ドメインに紐付ける。unhealthy になると Cognito が自動でセカンダリから応答する |
| **Cognito API / SDK 直接呼び出し** | **自動ではない。アプリ側でルーティングを実装する** |

公式:

> If you use the Amazon Cognito APIs or SDKs … **your application is responsible for routing traffic** to the Amazon Cognito service regional endpoint.

→ アプリのバックエンド（または BFF）に**リージョン切替ロジックを実装**する必要があります。同じ Route 53 ヘルスチェックを参照して判断することが推奨されています。

### 7.2 常時稼働で、切替は DNS

> both primary and secondary regional endpoints **remain active and ready to serve your traffic at all times**

セカンダリは**常時起動**（コールドスタンバイではない）。切替は DNS レベルなので、**RTO は分オーダー**が期待できます。

---

## 8. P-05 / P-15 への適合判定

| 要件 | 値 | MRR での実力 | 判定 |
|---|---|---|:-:|
| **RTO** | 1 日（DR 障害時 3 日） | Route 53 ヘルスチェック + DNS 切替で**分オーダー** | ✅ **大幅に上回る** |
| **RPO** | **5 分** | **「結果整合性」としか書かれておらず数値保証なし** | ⚠ **約束できない** |
| **リージョン** | 東京 + **大阪** | **大阪非対応**。海外ペアになる | ❌ |

**RPO について**: 公式は "might introduce brief delays" / "eventually consistent" とだけ述べ、**遅延の数値も SLA も示していません**。実運用では数秒〜数十秒と推測されますが、**「RPO 5 分」を契約上の約束にはできません**。実測して自社の値として持つか、要件を「ベストエフォート」に緩めるかの判断が要ります。

---

## 9. コスト

### 9.1 単価（[AWS News Blog](https://aws.amazon.com/blogs/aws/improve-your-application-resilience-with-amazon-cognito-multi-region-replication/) より）

> For user authentication, the add-on costs **$0.0045 per monthly active user per replica Region for Essentials tier** customers and **$0.006 per monthly active user per replica region for Plus tier** customers.
> For machine-to-machine: the add-on is a **30% charge** on top of the standard volume-based pricing for successful tokens issued.

### 9.2 本件での上乗せ額（Essentials + レプリカ 1）

| MAU | MRR 上乗せ（月額） | MRR 上乗せ（年額） |
|---:|---:|---:|
| 100 万 | $4,500 | **+$54K** |
| 500 万 | $22,500 | **+$270K** |
| 1,000 万 | $45,000 | **+$540K** |

### 9.3 DR 込みの総額（Cognito Essentials + MRR）

| MAU | 認証（§01 §7） | MRR | **合計（年額）** | Keycloak インフラ |
|---:|---:|---:|---:|---:|
| **100 万** | $180K | +$54K | **$234K** | $122K |
| **500 万** | $900K | +$270K | **$1.17M** | $122K |
| **1,000 万** | $1.8M | +$540K | **$2.34M** | $122K |

**DR を入れると、初回リリース規模でも Keycloak インフラ費のほぼ 2 倍**になります。ただし Keycloak 側の $122K には**構築 545〜1,026 人日が含まれていない**ので、初年度の総額比較では依然 Cognito が優位な可能性があります（§10 参照）。

> ⚠ MRR の MAU 課金がフェデレーションユーザーにも同単価で適用されるかは**ブログの記述からは断定できません**（未確認 U-9）。上表は全 MAU に適用される前提の概算です。

---

## 10. 現行 Keycloak の DR との比較

ここは**公平に見て Cognito が優れています**。

| 項目 | 現行 Keycloak（P-05 設計値） | Cognito MRR |
|---|---|---|
| **RTO** | **≈ 14 日**（Tier 3+ 手動 DR、**大阪でオンデマンド再構築**、平時は ROSA 未プロビジョニング） | **分オーダー** |
| RPO | Aurora バックアップ / スナップショット依存 | 結果整合性（数値保証なし） |
| 平時コスト | **ほぼゼロ**（大阪に常設なし） | **+$54K〜540K/年** |
| リージョン | 東京 + **大阪**（国内） | 東京 + **海外** |
| DR 中の機能制限 | 復旧後はフル機能 | **新規ユーザー不可 / PW リセット不可 / TOTP MFA 不可** |

**現行設計は「安いが遅い」、MRR は「速いが高く、機能が欠ける」**という対照になっています。

なお P-05 は **2026-08-16 に「⚠ 再検討中（DR 一式をヒアリング対象化）」**へ差し戻されており、**顧客希望値（RTO 1 日 / RPO 5 分）と現行のコールド DR 方針が両立していない**ことが既に認識されています。

> **P-05 … **この 2 値は下記コールド DR 方針と両立しない**（後述の Aurora 制約、U8 §8.3.1a）

→ **「RTO 1 日」を本当に満たしたいなら、Keycloak 側も現行のコールド DR では足りません。** DR 要件が確定すると、**Keycloak 側のコストも上がる**点は公平に見ておく必要があります。この比較は「Cognito に DR コストが乗る」だけの話ではありません。

---

## 11. 未確認事項

| # | 項目 | なぜ要るか |
|---|---|---|
| **U-8** | **Passkey / WebAuthn はセカンダリで動くか** | TOTP が不可と明記される一方、WebAuthn の記載がない。動くなら壁 2 の回避策になる |
| **U-9** | **MRR の MAU 課金はフェデレーションユーザーにも同単価か** | コスト試算の精度に直結 |
| **U-10** | **レプリケーション遅延の実測値** | 「RPO 5 分」を約束できるかの判断材料。公式に数値なし |
| **U-11** | **大阪リージョンの対応予定** | 法務論点を回避できる唯一の道。AWS へ確認 |
| **U-12** | **「modern infrastructure」の適用状況** | 新規作成プールは対象と思われるが、明示確認が要る |
| **U-13** | **海外レプリカ時の APPI 整理** | 法 28 条の根拠（規則 16 条体制整備 / 本人同意）をどう立てるか。**法務判断事項** |

---

## 12. 出典

### AWS 公式
- [Amazon Cognito now supports multi-Region replication](https://aws.amazon.com/about-aws/whats-new/2026/06/amazon-cognito-multi-region/) — 2026-06-04 提供開始、**対応リージョン一覧**（大阪非対応の根拠）
- [Multi-Region replication for user pools（開発者ガイド）](https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-multi-region.html) — 仕組み・制限・セカンダリで使える API 一覧・フェイルオーバー設定
- [Improve your application resilience with Amazon Cognito multi-Region replication（News Blog）](https://aws.amazon.com/blogs/aws/improve-your-application-resilience-with-amazon-cognito-multi-region-replication/) — **単価**・設定手順・フェイルオーバーの実際
- [CreateUserPoolReplica API](https://docs.aws.amazon.com/cognito-user-identity-pools/latest/APIReference/API_CreateUserPoolReplica.html) / [AWS::Cognito::UserPoolReplica](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-cognito-userpoolreplica.html) — IaC 対応
- [Amazon Cognito unlocks advanced capabilities with next-generation infrastructure](https://aws.amazon.com/blogs/security/amazon-cognito-unlocks-advanced-capabilities-with-next-generation-infrastructure/) — modern infrastructure の説明

### 補足
- [AWS Cognito Adds Multi-Region Failover for Authentication（InfoQ）](https://www.infoq.com/news/2026/06/cognito-replication-aws/)

### 本プロジェクト
- [01-requirement-gap-analysis.md](01-requirement-gap-analysis.md) — 本書の親文書
- [appi-legal-issues-summary.md](../common/appi-legal-issues-summary.md) — 「データは国内」前提の APPI 整理
- [01-architecture-baseline.md](../basic-design/01-architecture-baseline.md) — P-05 / P-15
