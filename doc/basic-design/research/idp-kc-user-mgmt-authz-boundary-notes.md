# 検討ノート: 統合ユーザ管理（IdP-KC 収容ユーザ）の CRUD と認可の境界

日付: 2026-07-24 / 出典: ユーザーとの設計討議。
関連: [03-identity-provisioning-design.md](../03-identity-provisioning-design.md)（U3 D3-05）、[02-keycloak-logical-design.md](../02-keycloak-logical-design.md)（U2 §2.5.4 ハイブリッド C）、[04-auth-ux-design.md](../04-auth-ux-design.md)（U4 §4.4.3 エンタイトルメント API）、[05-token-session-authz-design.md](../05-token-session-authz-design.md)（U5 §5.8 `idm:*`）、[ADR-038](../../adr/038-tenant-admin-portal.md)、[ADR-030](../../adr/030-minimal-jwt-claim-design.md)、§FR-6。

> **【ステータス: 旧モデル・要読替え】** 本ノート（2026-07-24）は初期討議の記録で、以後の決定で**トポロジが変わっている**。現行は **ブランド主役（[ADR-063](../../adr/063-brand-unit-architecture.md)）**: 「authz/idmap は Broker」ではなく **ブランドユニット（IdP-KC 側）に配置**、「管理 API = Broker」ではなく **#2（ブランド）内で CRUD/権限が完結**、削除は **Broker-first 二面同期ではなく A 案 outbox（[ADR-064](../../adr/064-deprovisioning-propagation-outbox.md)）**。実行形態は Lambda（[ADR-062](../../adr/062-idm-api-execution-form-lambda.md)）。**エンタイトルメント/認可境界の思想（§2 の結論部）は現行でも有効**だが、DB/アカウント配置の記述は上記 ADR と [control-plane ノート](control-plane-crud-authz-flows-notes.md)・[U3 D3-14〜17](../03-identity-provisioning-design.md) を正とすること。

## 0. 問い

IdP を持たない顧客のユーザは全て IdP-KC に収容される。同居アプリがユーザ CRUD を行う（U3 D3-05 = 専用 API 層 案 C）。
- (a) 統合ユーザ管理は **CRUD だけに閉じるべきか**、それとも **認可の一部も持つべきか**。
- (b) 「どのアプリを使えるか」（エンタイトルメント）は**顧客 IdP を持つテナントにも必要ではないか**。

## 1. 前提の再確認（この経路の特殊性）

1. **トークンは常に Broker が発行**（ADR-033）。IdP-KC 収容ユーザも `ブラウザ→Broker→(フェデ)→IdP-KC で認証→Broker がアプリ向け JWT 発行`。**アプリは IdP-KC からトークンを受けない**。
2. **CRUD（書き）と認証（読み）は別経路**: 書き = 同居アプリ→専用 API 層(ADR-038 Backend)→IdP-KC Admin API / 読み = Broker 発行 JWT。
3. よって「認可をどこに置くか」= JWT に載せるか / Backend DB に持つか / 各アプリに委ねるか、の選択。

## 2. 結論

### 2.1 (b) エンタイトルメントは全テナントで必要（フェデ系も）

**「どのアプリを使えるか」= エンタイトルメントは、フェデ系・非 IdP 系を問わず必要。** 本基盤が複数アプリを束ねる集約点であり、顧客 IdP は本基盤上の全アプリを把握していないことが多い。launchpad（U4 §4.4.3）は全ユーザ共通で「使えるアプリ」を出す。

違いは **有無ではなく「源（authoring の場所）」**:

| | エンタイトルメント | 源 |
|---|---|---|
| フェデ系 | **必要** | ① 顧客 IdP の group をマッピング、または ② 本基盤の管理画面で authoring |
| 非 IdP 系 | **必要** | 本基盤の管理画面で authoring（上流 IGA が無い） |

→ **本基盤が「解決済みエンタイトルメント」を全テナント分保持**し、launchpad/アプリは 1 本で問い合わせる。源の違いは本基盤が吸収（アプリ契約はフェデ/非 IdP で同一形）。

### 2.2 (a) CRUD には閉じない。ただし持つのは「粗粒度」まで

認可を 3 層に分け、本基盤は L-認可2 の一部までを持つ:

| 層 | 内容 | 所有者 | JWT |
|---|---|---|---|
| L-認可1: 認証+アイデンティティ | 本人性・`tenant_id`・MFA レベル | **Keycloak（IdP-KC/Broker）** | tenant_id/sub のみ（Stage 1） |
| L-認可2: 粗粒度（組織コンテキスト + エンタイトルメント + 機能ロールの器） | 下記 §3 | **専用 API 層 = ADR-038 Backend DB（SSOT）** | 原則載せない |
| L-認可3: 細粒度（リソース×アクション・閾値・ルーティング） | 「この経費 Z を承認できるか」「¥100万超は経理管理者」 | **各アプリ** | 載せない |

- **粗粒度認可の SSOT = ADR-038 Backend DB**。ハイブリッド C（U2 §2.5.4）を維持し**業務アプリ JWT に roles を載せない**（ADR-030 サイズ/PII/バージョン結合回避）。既存エンタイトルメント API（U4 §4.4.3 `GET /api/me/apps`）と同一 SSOT。
- Keycloak の groups/roles を authoring に使わない（単一 Realm×1000+ テナントで肥大、JWT 非搭載方針、アプリの Admin API 結合を避ける）。KC は認証+`tenant_id` に専念。
- 例外: 管理系 Client（テナント管理画面自身）のみ realm role を JWT で受けてよい（ハイブリッド C どおり）。

## 3. 「業務ロール」の程度 — 組織ロールまで。機能ロールはアプリ

判定基準 = **複数アプリで再利用されるか**。出張予約 × 経費精算の承認フローで確認:
- 経費精算: 申請→**上長**承認→¥10万超は**部門長**→¥100万超は**経理管理者**
- 出張予約: 国内は**上長**承認→海外は**部門長**＋**旅行管理者**

両アプリが「上長」「部門」を再利用 → **組織データは本基盤が 1 箇所で持つべき**（人事異動を 1 回の更新で両アプリに反映）。一方「経理管理者/旅行管理者/¥100万閾値/海外ルーティング」は各アプリ内でしか意味を持たない → アプリが定義・実行。

### 所有者の仕分け

| 項目 | 例 | 所有者 | 理由 |
|---|---|---|---|
| アプリ エンタイトルメント | 経費/出張を使える | **本基盤** | 全テナント共通・集約点（§2.1） |
| **組織ロール（横断）** | 部門 / 上長 / 役職 / コストセンター / 雇用形態 | **本基盤** | 両アプリが再利用。異動を 1 箇所で |
| 機能ロール（アプリ内） | 「経理担当」「旅行管理者」 | **アプリが定義**（割当の保管は本基盤でも可） | そのアプリ内でしか意味がない |
| 認可ルール・閾値 | ¥100万超は経理管理者 / 海外は部門長+旅行管理者 | **アプリ** | 固有ロジック。本基盤に持つと 1000テナント×N アプリで破綻 |
| リソース単位判定 | 「この申請 Z を承認できるか」 | **アプリ** | 細粒度・状態依存 |

### 機能ロール「割当」の器だけは本基盤が運ぶことがある

`田中 → 経費精算で "経理担当"` の**割当**は、フェデ系 = 顧客 IdP group から流し込み / 非 IdP 系 = 本基盤の管理画面で authoring。**本基盤は opaque な per-app role 文字列を運ぶだけで、意味はアプリが定義**。→ 非 IdP テナントの「管理主体が居ない」問題を解消しつつ、本基盤はアプリ内認可ロジックを抱えない。

## 4. 境界の原則（一言で）

- **本基盤が持つ**: 「組織の中で何者か（部門・上長・役職・CC・雇用形態）」＋「どのアプリに入れるか」＋（非 IdP は）機能ロール割当の**器**。
- **アプリが持つ**: 「自分の中で何ができるか」（機能ロールの意味・閾値・ルーティング・リソース判定）。
- **業務ロール = 組織ロールまで。機能ロールは器だけ、中身はアプリ。**

## 5. 決定事項 / 未決

### 5.1 決定（2026-07-24 ユーザー確定）

| # | 論点 | 決定 |
|---|---|---|
| AZB-1 | 組織データの範囲 | **本基盤が持つ**: 役職 / 入社年度 / 部門 / 上長 / コストセンター / 雇用形態 等の「個人に紐づく組織属性」。「具体的に何ができるか」は各アプリが判断（境界どおり）。保管先の KC User Profile vs Backend DB の割り振りは U3 で確定 |
| AZB-2 | 配信方式 | **API pull（`/api/me/context`）に確定**。JWT には載せない（JWT 最小化・ハイブリッド C 維持） |
| AZB-3 | 機能ロール割当を共通のユーザ一覧/編集画面で操作可能にするか | **Yes**（opaque 文字列 + アプリが解釈）。**IdP テナント・非 IdP テナントで共通**の authoring 面 |
| **AZB-5** | **顧客 IdP テナントの組織属性を本基盤に持たせるか** | **持たせる（推奨確定）**。理由=アプリ契約をフェデ/非 IdP で同一にするため（持たないと部門/上長で認可するアプリがフェデ系で動かない）。**JWT 最小化とは独立**（トークンの話と保管の話は別、配信は API）。条件: ①フェデ系は SCIM/JIT で**同期した射影**として保管、**SoT は顧客 IdP/HRIS**（U3 §3.4） ②認可に要る部分集合のみ（Minimum Storage, ADR-025） ③認可駆動属性は **SCIM 即時が望ましい**（JIT はログイン時更新で鮮度差あり、アプリと合意） |

### 5.2 未決

| # | 論点 | 推奨 |
|---|---|---|
| AZB-1b | 組織属性の保管先割り振り（単純 per-user 属性 = KC User Profile / 関係・多アプリ割当 = Backend DB） | U3 で確定。機能ロール割当（per-app）は Backend DB |
| AZB-4 | フェデ系 group→組織ロール/機能ロール割当 マッピング（U2 §2.5.4 Advanced Claim to Role）の追加 | **共通管理画面 authoring を両テナントの標準**とし、IdP group 駆動は後付けの上乗せオプション |

## 5.3 SCIM 単一受け口モデル（2026-07-24 確定）

顧客 IdP からの SCIM は **1 エンドポイント（Facade）にのみ**行う。**Broker と管理画面アプリの 2 箇所に顧客 IdP から SCIM させない**（設定 2 倍・障害点 2 倍・不整合の温床）。

- **SCIM の受け口は Facade だけ**。管理画面 / `/api/me/context` は **SCIM を受けず読むだけ**。「Keycloak が無い場所で SCIM を受けられるか」= Yes、**Facade 自体が非 Keycloak の SCIM アダプタ**（U3 D3-11）。
- **書き分け**: SCIM →（Facade）→ **Keycloak**（identity + 組織属性）／ 機能ロール割当・エンタイトルメントは**管理画面 authoring → Backend DB**（SCIM は触らない）。
- **組織属性は SCIM Enterprise User 拡張で標準的に運べる**（`department` / `manager` / `costCenter` / `organization` / `division` / `employeeNumber`）。入社年度・雇用形態はカスタム属性。いずれも Facade → Keycloak user 属性（User Profile 宣言）。
- **保管先（AZB-1b 推奨）**: 組織属性 = **Keycloak user 属性（単一ストア）**。関係データ（機能ロール割当・エンタイトルメント・idmap）のみ Backend DB。→ Facade の書込先が 1 つで最もシンプル。

### Facade の実体（どこで構築・何を受ける）

| 項目 | Broker Facade | IdP-KC Facade |
|---|---|---|
| 置き場所 | **Broker Acct の ROSA クラスタ内**（default/infra Pool 常駐 Deployment + 専用 HPA、O-9 暫定） | **IdP-KC Acct の ROSA クラスタ内**（同上） |
| 方向 | D2: 顧客 IdP → Broker（フェデ系） | D1: 顧客 HRIS → IdP-KC（非 IdP 系） |
| Inbound | SCIM 2.0 HTTPS。Internet → 他組織 CF+WAF（`scim-broker`/`scim-idp`、送信元 IP 許可 + テナント別 Rate Limit, REQ-IN-09）→ TGW → 自管理 Internal ALB → Facade。認証 = テナント別 opaque Bearer（Secrets Manager）+ URL `{tenant_id}` と token→tenant 不一致は 403 | 同左 |
| 書き込み | **クラスタ内 Service 経由で Keycloak Admin API**（identity + 組織属性）。DELETE は Soft Delete 写像 | 同左 + **idmap は EventBridge クロスアカウント → Broker**（§6.1.2 経路5） |

- **なぜ in-cluster か**: Admin API は `hostname-admin` 内部限定 + 外部 ALB /admin 403（U6 §6.6）。**クラスタ内 Facade は内部 Service で Admin API に到達**でき、外部 /admin 境界を通らず露出面を増やさない。
- **1 Facade = 全テナント**（パス `/t/{tenant_id}/scim/v2` でマルチテナント。テナント別デプロイではない）。
- **非対称**: 受信は internet-facing（エッジ経由 + WAF/IP/token）／書き込みは in-cluster（内部）。
- **AZB-5 の帰結**: Facade の書込範囲が「identity のみ」→「identity + 組織属性（SCIM Enterprise 拡張）」に拡大 → **U3 D3-11 のサポート操作表に組織属性の PUT/PATCH を明記**する。

## 5.4 SCIM Facade の 1000+ テナント スケール（2026-07-24 検討・**未確定 / 方向性のみ**）

> ⚠ **未定**。方向性の記録であり、PoC 実測（下記ゲート）で確定する。

**前提の正し方**: Facade は**テナントごとではない**。アカウントごとに **1 つの多テナント Facade**（Broker Acct / IdP-KC Acct に各 1）、テナントは URL パス `/t/{tenant_id}` + トークンで分離。「1000+ テナント = 1000 Facade」ではない。

**要点**: Facade 自体はステートレス → HPA で水平スケール、**ボトルネックにならない**。詰まるのは「その先」:

| # | ボトルネック | 効く場面 |
|---|---|---|
| 1 | **Keycloak Admin API + Aurora 書込負荷**（SCIM 1 操作 = Admin API = Aurora 書込） | テナント初期一括投入・定期リコンサイル |
| 2 | **テナント間干渉（ノイジーネイバー）** | 新規テナント onboarding の一括投入 |
| 3 | **externalId マッチング検索**（`filter=externalId eq` = 単一 Realm 数百万ユーザの検索、**P-16 と同根**） | 全更新系 |

**性質**: SCIM は認証でなくプロビジョニング → 定常秒間量は小さい（≈1-2 ops/s 規模）。**設計を殺すのはバルク（onboarding / full sync）**。SCIM 送信テナント ≤ IdP 数（SCIM はオプトイン、JIT のみは送らない）。

**方向性（手当て候補、未確定）**:
1. **Facade ↔ 書込の非同期分離**: 受信は即 202、Admin API 書込は**キュー（SQS/Kafka）経由の Writer ワーカーで流量制御**（同期 1:1 でバルクを流さない）。
2. **テナント別レート整形 + フェア queueing**（REQ-IN-09 の 10 req/s を Writer 側の公平配分にも効かせる）。
3. **一括投入は専用パス**（リアルタイム SCIM と分離、レート整形・進捗管理）。
4. **`scim_external_id` インデックス化**（検索高速化、P-16 と同じ土俵）。
5. **冪等・リトライ前提の Writer**。

**PoC ゲート追加提案（G-SCIM にスケール次元を追加、G-IdP-Scale と同一データセットで併走）**:
- 500/1000 テナント相当の externalId マッチング検索 p99（単一 Realm・数百万ユーザ）
- 一括投入（1 テナント 5 万件）中の他テナント SCIM 遅延（フェアネス）
- Writer 流量制御下の Admin API / Aurora CPU・書込 IOPS

**未決**: 実行形態（U6 O-9: ROSA 常駐 vs 非同期 Writer 構成）/ キュー採否と方式 / バルク経路の要否 — いずれも PoC 実測後に確定。

## 5.5 `/api/me/context` の読取経路（アカウント跨ぎ）（2026-07-24 検討・方向性）

**問い**: フェデ系ユーザは Broker KC、非 IdP 系は IdP-KC KC とアカウント跨ぎで読むのか。

**原則（確定方向）**: **リクエスト時はどちらの Keycloak も読まない・アカウント跨ぎしない**。アプリは常に Broker 発行 JWT（`sub`=Layer A + `tenant_id`）を持つ → **`/api/me/context` は「Broker `sub` をキーにした単一の射影(projection)」を 1 read するだけ**。クロスアカウントの手間は**書込（プロビ）時に寄せる**。
- 理由: request 時クロスアカウント読取は P-17 分離（Broker↔IdP-KC の IAM/Admin API 相互到達を作らない §6.1.2）に反する + レイテンシ/負荷（10M 規模）。

**推奨アーキテクチャ**: **Broker Acct に統合射影（Backend DB）**を置く（既存 idmap 統合 §6.1.2 経路5「Layer A FK 一元性を Broker Acct 側で維持」と同じ集約点）。
- 保持: 組織属性 + エンタイトルメント + 機能ロール割当。キー = Broker `sub`。
- **書込フィード**: ①フェデ D2 SCIM → Broker Facade（同一 Acct 直 upsert）② 非 IdP D1 SCIM/アプリ CRUD → IdP-KC → **EventBridge → Broker ハンドラ → upsert**（idmap と同機構）③ 管理画面 authoring → 直。
- **読取**: 射影のみ（Keycloak 非経由）。フェデ/非 IdP を区別しない = アプリ契約同一の実装的裏付け。組織属性も射影に入れる。

**wrinkle（sub 未生成）**: 非 IdP ユーザは D1 SCIM 時点で Broker `sub` 未生成（Broker shadow は初回 first-broker-login で生成）。→ 射影は `(tenant_id + external_id)` 安定キーで先に作り、**Broker `sub` を初回ログイン時にバックフィル**（first-broker-login SPI がリンクイベント emit）。`/api/me/context` はログイン済みにしか呼ばれない = 読取時に必ず `sub` あり。

**鮮度**: SCIM 即時で射影更新（認可駆動属性の即反映）。JIT はログイン時更新（stale をアプリ合意）。読取は短 TTL キャッシュ可。

**残る設計判断（U6/U3 引き渡し・未確定）**:
| # | 論点 | 傾き |
|---|---|---|
| RC-1 | 射影ストア（Aurora idmap 同居 / DynamoDB） | **Aurora 同居**（idmap と同集約点・整合） |
| RC-2 | `/api/me/context` 提供場所 + IdP-KC 同居アプリの到達経路（(i)Broker Acct 提供・アプリは token/JWKS と同経路 /(ii)IdP-KC へ読取レプリカ） | **(i)**（単一 SSOT。到達経路は U6 確定） |
| RC-3 | sub バックフィル（first-broker-login SPI emit / バッチ突合） | **SPI emit**（3 系統 Flow 相乗り） |
| RC-4 | 射影一貫性（EventBridge at-least-once + 冪等 upsert + version 列） | 冪等 + version 最新勝ち |

**ゲート**: idmap EventBridge 経路の延長のため新規リスク小。G-SCIM に「非 IdP: D1 SCIM→EventBridge→射影→初回ログイン sub バックフィル」の E2E + 読取 p99（10M）を追加。

## 6. 反映先（本体ドキュメントへの統合候補）

- **U3 D3-05 / §3.1**: 専用 API 層のスコープに「組織属性 + エンタイトルメント + 機能ロール割当（器）」を明記。組織属性（部門/上長/CC/雇用形態）の User Profile or Backend スキーマ（AZB-1）。
- **ADR-038**: 管理画面スコープに「アプリ割当・組織ロール・機能ロール割当 authoring」を追加。
- **U4 §4.4.3**: エンタイトルメント API を `/api/me/apps` から `/api/me/context`（アプリ + 組織コンテキスト + 割当）へ拡張、全テナント共通契約であることを明記。
- **U5 §5.8**: `idm:*` に `idm:entitlements:*` / `idm:orgroles:*`（または `idm:context:read`）を追加。
- **U2 §2.5.4**: ハイブリッド C の「業務アプリ JWT に roles 非搭載」を維持しつつ、粗粒度認可 SSOT = Backend DB であることを相互参照。

## 7. 検証結果と本体反映（2026-07-24、メインセッション）

**検証**: 既存 10 冊 + RFC 7643 と突合。**方針は全て既存設計と整合**（ハイブリッド C / P-10 / D3-05 / D3-11 / D-U6-02 / U7 emit 専任 / P-17）。SCIM Enterprise 拡張の属性列挙（employeeNumber/costCenter/organization/division/department/manager）は RFC 7643 §4.3 どおり ✅。

**訂正 2 点**（本体反映時に修正済み）:
1. **`manager` は参照型**（complex、value = SCIM リソース id）のため文字列属性へ直写像不可 → **`manager_ref` = 同一テナント内 `external_id` へ正規化**する規約に修正（解決不能時は保留キュー）。
2. **RC-3（sub バックフィルの emit）**: First Broker Login Authenticator SPI が直接 emit するのではなく、**Event Listener SPI（emit 専任、U7 D-U7-04）が `IDENTITY_PROVIDER_FIRST_LOGIN` を EventBridge へ送る**形に修正（SPI 責務分離の維持）。

**反映先（§6 の候補に 3 箇所追加して実施）**: U3 §3.8 新設（D3-14〜16、本ノートの正式反映先）/ U2 §2.5.4 / U4 §4.4.3（`/api/me/context` 拡張）/ U5 §5.8（`idm:context:read` / `idm:assignments:write`）/ **U10 §10.2.2（§6 で漏れ — OpenAPI 骨子側の更新）** / ADR-038 注記 / **Baseline §1.5 G-SCIM 拡張（スケール次元 + 非 IdP E2E — §5.4/§5.5 のゲート提案の正式登録）**。**D3-01 への組織属性 8 行追加**（User Profile 宣言、U2 §2.6 realm.json 反映待ち）も §6 に無かった必須作業として実施。

## 8. 非 IdP ユーザの CRUD/削除モデル（2026-07-24 ユーザー確定 — **mode A 単独 / 管理画面同期のみ**）

### 8.1 要件（確定）

非 IdP テナントのユーザは **各企業の担当者（テナント管理者）が「ユーザ一覧/編集画面」から作成・編集・削除できれば良い**。→ **mode A（管理画面 = SoT）単独**で確定。

**採用しないもの（Phase 1）**:
- **HRIS / D1 SCIM（mode B）** — 使わない前提（要念押し確認）。
- **アプリ発 CRUD（mode C、D3-05 の `app` 経路）** — Phase 1 スコープ外（下記 8.5）。
- **EventBridge 削除経路** — mode C が無いため削除には不要。
- **非 IdP ユーザの 90 日休眠バッチ** — 本基盤が SoT のため自動削除しない。「数年休眠で削除」が要件化したら**テナント別リテンションポリシー**（管理画面の一括操作 or opt-in）として後付け。

### 8.2 CRUD は管理画面同期のみ。ただし削除は「両側同期」

管理 API は **Broker 側 idm-api（Broker Acct, ROSA）**に置き、IdP-KC へは既存 **Broker→IdP-KC PrivateLink**（単方向）で届かせる。1 つの API が両側を同期で触る。

| 操作 | 同期の中身 | Broker 関与 |
|---|---|---|
| **作成** | IdP-KC のみ（Broker shadow は初回ログイン時に自動生成） | なし |
| **編集**（組織属性等） | IdP-KC + 射影更新 | 射影のみ |
| **削除** | **① Broker shadow 無効化 + `not_before`（セッション/RT 即失効, ローカル Admin API）→ ② IdP-KC Soft Delete（PrivateLink 経由）→ ③ 射影 deprovisioned** | **必須** |

- **削除の順序が命**: ①（shadow 無効化）を**先**にする。アクティブアクセスを切るのは shadow の `enabled=false`（Keycloak は refresh 時に user.enabled 検査 → 即 invalid_grant）。①成功後に②失敗ならリトライ（ユーザは既に遮断済みで安全）。①失敗なら中断。
- **なぜ両側か**: IdP-KC だけ消しても **Broker セッション/RT は独立**（Broker は refresh 時に IdP-KC を再確認しない）→ shadow を無効化しないと**退職者が最大 24h（セッション max）アクセス可能**。
- 全て**同期（数百 ms）で完結**。非同期・イベント連携不要。

### 8.3 唯一の安全網：日次リコンサイル

2 アカウントへの 2 コールは分散 Tx ではない → **日次で「IdP-KC の `deprovisioned_at` 有り ↔ Broker shadow enabled」を突合して補正**。idpkc shadow は 90 日バッチ除外のため、これがその代替の砦。

### 8.4 SCIM を内部伝播に使わない根拠（調査確定）

「IdP-KC → Broker を SCIM で」案は**却下**。
- **Keycloak には SCIM 送信クライアント（outbound）が core 未実装**（将来機能 — [keycloak.org survey feedback](https://www.keycloak.org/2026/02/scim-support-survey-feedback) / [keycloak#13484](https://github.com/keycloak/keycloak/issues/13484)、2026-07-27 検証）。受信サーバは 26.6 で experimental 追加だが outbound とは別レイヤ。→ 送信はサードパーティ拡張（suvera/mitodl 等）or 自作が必要 = §2.7.1（バージョン固定・RHBK サポート）と衝突。
- **scim_active 意味崩壊**（内部フェデを「外部顧客 SoT」と誤認 = D3-05 案 B の混線再発）。
- shadow のバッチ除外印は scim_active でなく**既存 `jit_idp_alias=idpkc-oidc01`**（作成時=初回ログイン SPI で付与、バッチ側が読んで除外）。

**3 択比較の結論**: SCIM プロトコル ＜ 純 JIT ＜ EventBridge ＜ **同期（mode A では最良）**。リアルタイム deprovisioning の手段は SCIM でなく EventBridge/同期で、mode A なら**同期が最良**（即時・SCIM リスクなし・DLQ 不要）。

### 8.5 Phase 2 送り（mode C を入れる場合のみ EventBridge 復活）

- **アプリを人事 SoT にするテナント（mode C）**を将来提供する場合のみ、IdP-KC 発 deactivate を Broker へ伝える **EventBridge（at-least-once + 冪等 + version 最新勝ち + DLQ + リコンサイル）**が必要。実装詳細は本ノート前段の議論（resource-based policy で PutEvents 許可 / §6.1.2 経路5 と同型 / AssumeRole 不要）参照。
- **アプリはアイデンティティを消さない**のが原則（共有 ID の巻き添え防止）。アプリ発の休眠対応は**そのアプリのエンタイトルメント剥奪**に留める（アイデンティティ削除ではない）。

### 8.6 反映先（本体統合候補）→ **2026-07-24 反映完了**

- ✅ **U3 §3.8 / §3.4**: **D3-17 新設**（両側同期 + リコンサイル + SCIM 却下 + Phase スコープ）+ D3-09 に `jit_idp_alias=idpkc%` バッチ除外を追記。
- ✅ **U3 §3.2（D3-04）**: 経路 ④ に「非 IdP mode A を含む」注記。**provisioned_by 値（local-admin vs portal）は未決のまま D3-17 に登録**（指示どおり確定させず）。
- ✅ **ADR-038 / U10 §10.2.2**: 両側同期の旨を注記（deactivate 行 + ADR 注記 2）。
- ✅ **Phase スコープ**: D3-17 冒頭に明記（mode B は「要念押し確認」も転記）。
- **周辺検討で追加した反映（メインセッション検証、2026-07-24）**:
  - ✅ **U6 §6.3.2**: 旧文言「クロスアカウント CRUD 経路は設けない」を**アプリ発 CRUD 限定に精密化**（§8 と矛盾しないよう）+ 管理画面経路を追加。**PrivateLink の宛先は IdP-KC 側 idm-api とし、Admin API は in-cluster のみ**（D-U6-11 / 06a §A.2.1b との整合解釈 — Admin API を PrivateLink に直接露出しない）。ルート実装形 = **O-12 新設**。
  - ✅ **U5 §5.4.2**: 削除 ① は既存の強制ログアウト API（`users/{id}/logout`）と同一である旨 + **発行済み AT ≤30 分の残存は Z 系ゾンビ窓の受容範囲内**（新たな悪化なし）の注記。
  - ✅ **U9**: **RB-USR-06（日次リコンサイル）** 追加、Runbook 全 36 冊に再計上。
  - 検証結果: 「refresh 時 user.enabled 検査 → invalid_grant」「Broker は refresh 時に IdP-KC 非再確認」「Keycloak SCIM 送信不可」の 3 主張はいずれも正 ✅。

