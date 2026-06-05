# Keycloak Hook アーキテクチャ — 初期実装 + 運用作業 詳細メモ

> **位置付け**: Keycloak（26 LTS）の **Hook 機能を 2 種類（INBOUND / OUTBOUND）に分類**し、**初期実装で必要なこと + 運用時の追加・変更作業 + 落とし穴** を一元化した技術メモ。本プロジェクトは Keycloak 優位の方針のため、Keycloak 特化で整理（Cognito は対比目的のみ最小限）。
> **対象読者**: Keycloak 設計・実装担当者 / SRE / 認証基盤ヒアリング担当 / 製品選定レビュー担当
> **調査ベース**: 2026-06 時点の Keycloak 26.6 系（LTS）/ Phase Two `keycloak-events` / RHBK 26.4 公式ドキュメント
> **関連**:
> - [auth-patterns.md](auth-patterns.md) — 認証パターン総覧
> - [authz-architecture-design.md](authz-architecture-design.md) — 認可アーキテクチャ
> - [subdomain-architecture-notes.md](subdomain-architecture-notes.md) — サブドメイン構成
> - [token-exchange-spec-and-patterns.md](token-exchange-spec-and-patterns.md) — Token Exchange
> - [§4.1 認可スタンス + JWT クレーム設計](../requirements/proposal/fr/06-authz.md) — JWT クレーム最小化方針
> - [§4.6 強制再認証・ステップアップ](../requirements/powerpoint-outline-and-references.md)
> - [§6.2 デフォルト権限](../requirements/powerpoint-outline-and-references.md)

---

## 目次

1. [Hook の 2 分類（INBOUND vs OUTBOUND） + SCIM 受信は別軸](#1-hook-の-2-分類inbound-vs-outbound--scim-受信は別軸)
2. [INBOUND Hook = Keycloak SPI 詳細](#2-inbound-hook--keycloak-spi-詳細)
3. [OUTBOUND Webhook 実装パターン + SCIM 受信プラグイン](#3-outbound-webhook-実装パターン)
4. [SSF / CAEP（業界次世代標準）対応状況](#4-ssf--caep業界次世代標準対応状況)
5. [初期実装で必要なこと（時系列）](#5-初期実装で必要なこと時系列)
6. [運用時の作業（シナリオ別フロー）](#6-運用時の作業シナリオ別フロー)
7. [既知の落とし穴 + 性能 + セキュリティ](#7-既知の落とし穴--性能--セキュリティ)
8. [本プロジェクトでの設計指針（採用パターン + ライセンス考慮）](#8-本プロジェクトでの設計指針)
9. [リファレンス](#9-リファレンス)

---

## 1. Hook の 2 分類（INBOUND vs OUTBOUND）+ SCIM 受信は別軸

### 1.1 機能 3 軸の整理（重要）

本ドキュメントの「Hook」は INBOUND/OUTBOUND の 2 種類だが、**SCIM 受信は Hook とは別軸の「プロトコル受信機能」** として独立した判断軸になる:

| 軸 | **INBOUND Hook**（Keycloak SPI）| **OUTBOUND Webhook** | **SCIM 受信機能**（別軸、参考）|
|---|---|---|---|
| **性質** | Keycloak 内部処理の拡張 | Keycloak → 外部の事後通知 | 外部 → Keycloak へのプロビジョニング受信 |
| **実行場所** | Keycloak 内部（JVM 内）| 外部システム | Keycloak の SCIM Endpoint |
| **タイミング** | 認証/トークン/登録フロー**の途中に介入**（同期）| イベント発生**後の事後通知**（非同期推奨）| 顧客 IdP からの SCIM Push を受信 |
| **失敗時影響** | **認証フロー停止可能** | 業務処理影響、認証は完了済 | プロビジョニング失敗、認証フローには無関係 |
| **主用途** | カスタム認証 / JWT クレーム拡張 / 属性マッピング / 外部 DB 連携 | 業務同期 / SIEM 通知 / Slack/Teams 連携 | Workday / Microsoft Entra / Okta 等からのユーザー作成・更新・削除 |
| **仕様基盤** | Keycloak Provider/ProviderFactory パターン（Java ServiceLoader）| HTTP POST、業界標準 **RFC 8417 SET / SSF / CAEP** | RFC 7644 SCIM 2.0 |
| **Keycloak 標準提供** | ✅ **8 種類の SPI（Authenticator / Protocol Mapper / Event Listener / Identity Provider Mapper / User Storage / Theme / Email Sender / Required Action）** | ❌ **標準なし、OSS 拡張 or 自作必須** | ⭐ **2026-04 Keycloak 26.6 で Experimental 追加**（→ §3.5）|
| **本プロジェクト採否** | ✅ 必須（Keycloak 採用時の前提）| 顧客次第（オプション）| §5.1 で判断（JIT のみなら不要）|

### 1.2 重要な前提

- **INBOUND Hook は Keycloak 採用時に必ず使う**（製品選定後の必須要素）— ただし **約 95% は標準 SPI 機能でカバー、カスタム SPI 開発は限定的**（→ §2.2）
- **OUTBOUND Webhook は必要に応じて追加**（顧客次第のオプション要素、→ §3）
- **SCIM 受信は §5.1 フェデユーザ同期方針で独立判断**（INBOUND Hook とは別物、→ §3.5 + §8.1）

### 1.3 よくある誤解（明示的注意）

| ❌ 誤解 | ✅ 正しい整理 |
|---|---|
| 「INBOUND が必須なので Phase Two SCIM Plugin が必要」 | **別物**。INBOUND Hook（SPI）は Keycloak 標準で 95% カバー、追加プラグイン不要。**SCIM Plugin は「SCIM 受信機能を採用するか」で独立判断** |
| 「Phase Two = Webhook + SCIM 両方」と一体採用必須 | **Phase Two は機能別に分かれた複数 OSS 拡張**。Webhook = `keycloak-events`、SCIM = SaaS / 別拡張で独立採否可能 |
| 「SCIM 受信は Webhook で代替可能」 | **逆方向の話**。SCIM 受信 = 外部 → Keycloak、Webhook = Keycloak → 外部。代替関係ではなく相補関係 |

---

## 2. INBOUND Hook = Keycloak SPI 詳細

### 2.1 共通の実装パターン

すべての SPI は **Provider + ProviderFactory** の 2 インターフェース実装 + `META-INF/services/<FactoryInterface>` のサービス定義ファイル配置（Java ServiceLoader）。Quarkus 化された 17 以降の必須運用:

```
1. JDK 17+ で Java 実装
2. mvn clean package で JAR ビルド（依存は provided スコープ）
3. JAR を ${KC_HOME}/providers/ にコピー
4. bin/kc.sh build を実行（閉世界アセンブリ再構築）
5. bin/kc.sh start で起動
6. Admin Console > Server Info > Providers タブで Factory 検出確認
```

❌ **WildFly 時代のホットデプロイは廃止**（17+）。
✅ **CI/CD で Container Image に焼き込む** のが標準パターン。

### 2.2 SPI 一覧と用途マトリクス

| # | SPI 名 | 用途 | 標準提供範囲 | カスタム実装の必要度 |
|:-:|---|---|---|:-:|
| 1 | **Protocol Mapper SPI** | JWT/SAML Assertion クレーム編集 | User Attribute / Role / Group / Hardcoded / Audience / Script Mapper 等で **約 95% カバー** | 動的計算・外部 API 呼出時のみ |
| 2 | **Authenticator SPI** | カスタム認証ステップ（カスタム MFA / リスクベース / ステップアップ）| 標準: Username/Password Form / OTP / WebAuthn / Kerberos / X.509 等 | カスタム MFA・特殊フロー時 |
| 3 | **Event Listener SPI** | 認証イベント / 管理イベントのリッスン | **`jboss-logging`** と **`email`** のみ（HTTP Webhook 等は OSS 拡張）| Webhook 送出時は必須（→ §3）|
| 4 | **Identity Provider Mapper SPI** | 外部 IdP（SAML/OIDC/Social）属性 → Keycloak 属性マッピング | Attribute Importer / Username Template / Role Mapper / Advanced Claim/Attribute Mapper 等 | SAML Group → KC Group 等の複雑ケースのみ |
| 5 | **User Storage SPI** | 外部 DB / レガシー認証連携 | **LDAP / AD は標準ビルトイン**（SPI 開発不要）| LDAP/AD 以外の外部 DB のみ |
| 6 | **Theme SPI** | ログイン画面・アカウントコンソール見た目 | FreeMarker + CSS + JS のディレクトリ上書きで多くは賄える | 高度カスタマイズ時のみ |
| 7 | **Email Sender SPI** | メール送信 | SMTP のみ | SendGrid/SES/Mailgun API ベース時 |
| 8 | **Required Action SPI** | ログイン後の強制アクション（PW 更新 / 規約同意 / MFA 登録）| 標準: Update Password / Configure OTP / Update Profile 等 | カスタム強制アクション時 |

### 2.3 各 SPI 詳細

#### Protocol Mapper SPI（最重要 — JWT クレーム拡張）

**実装インターフェース**: `AbstractOIDCProtocolMapper` を継承し `OIDCAccessTokenMapper` / `OIDCIDTokenMapper` / `UserInfoTokenMapper` のうち必要な mixin を実装。

**標準 Mapper で対応可能なケース（カスタム SPI 不要）**:
- ユーザー属性 → クレーム（`User Attribute Mapper`）
- ロール / グループ → クレーム
- 固定値（`Hardcoded Claim`）
- audience の指定
- JavaScript で計算（`Script Mapper`、ただし本番非推奨派あり）

**カスタム SPI が必要なケース**:
- 外部 REST API を毎回叩いて動的にクレーム生成
- 複雑な属性変換ロジック
- カスタムビジネスルールでのクレーム編集

**運用上の重要事項**:
- ⚠ **トークン発行ごとに毎回実行** — 外部 API 呼出は厳禁。やむを得ない場合は **Caffeine 等で Realm 内キャッシュ実装必須**
- ⚠ クレーム追加は **既存トークンには適用されない**（次回トークン発行から有効、Refresh Token 保有者は更新時まで遅延）

#### Authenticator SPI（カスタム MFA / ステップアップ）

**実装インターフェース**: `Authenticator` + `AuthenticatorFactory` + FreeMarker テンプレート（フォーム表示用）。

**Authentication Flow への組込**:
- Admin Console > Authentication > Flows で新規 Flow 作成
- Execution として追加、`REQUIRED` / `ALTERNATIVE` / `CONDITIONAL` / `DISABLED` を選択
- Client 単位での Flow オーバーライドも可能

**ステップアップ認証実装の中核**:
- `acr_values` 引き上げ要求受信時のフロー分岐
- 既存セッションから AAL 評価 → 不足時に追加認証ステップ起動
- Conditional Authenticator で動的判定

**実装難易度**: 中〜高（FreeMarker + Java + `AuthenticationFlowContext` の理解必須）

**バージョン互換性**:
- 24.0: `UserProfileDecorator` 変更
- 25.0: `AccessToken/IDToken` deprecated メソッド削除
- 26.0: `ClusterProvider` 新メソッド追加

Authenticator 自体の API は比較的安定だが、依存する Token/Session モデルの破壊変更を喰らうケースあり。

#### Event Listener SPI（Webhook 送出基盤）

**実装インターフェース**: `EventListenerProvider#onEvent(Event)` + `onEvent(AdminEvent, boolean)`。

**標準提供**: `jboss-logging`（ログ出力）+ `email`（管理者通知）のみ。

**HTTP Webhook 送出はサードパーティ拡張または自作**（→ §3 詳細）

**重要な落とし穴**:
- ⚠ **同期実行**（ログインリクエストと同一スレッド）
- ⚠ **HTTP 送出を同期実装すると送信先レイテンシがログイン応答時間に上乗せ**
- ✅ **必ず非同期化**（ExecutorService / 内部キュー経由）

#### Identity Provider Mapper SPI

外部 IdP（SAML/OIDC/Social）からの属性マッピング。**標準 Mapper の網羅性が高く、カスタム実装は限定的**。

標準提供: Attribute Importer / Username Template Importer / Hardcoded Role/Attribute / External Role to Role / Advanced Claim to Role / Advanced Attribute to Role 等。

カスタム必要例: SAML Group claim を Keycloak Group に詳細マッピング等。

#### User Storage SPI

外部 DB 連携。**LDAP/AD は標準ビルトイン**で SPI 開発不要。LDAP Mapper（user-attribute / group-ldap / role-ldap / msad-user-account-control 等）も標準提供。

カスタム必要例: 既存独自 DB の移行期、レガシー認証 API ラップ。

25.0 で `UserQueryProvider` メソッドシグネチャ変更あり → バージョンアップ時の再ビルド必須。

---

## 3. OUTBOUND Webhook 実装パターン

### 3.1 Keycloak 本体は標準未対応

**2026-06 現在も Webhook は標準機能なし**。GitHub Discussion [#41175](https://github.com/keycloak/keycloak/discussions/41175) で議論中だがロードマップ入り未確定。

### 3.2 主要 OSS / コミュニティ拡張

| 拡張 | リポジトリ | メンテ | 特徴 |
|---|---|:-:|---|
| **Phase Two `keycloak-events`** ⭐ | [p2-inc/keycloak-events](https://github.com/p2-inc/keycloak-events) | **活発（商用 SaaS 採用）** | **デファクトスタンダード**。HMAC 署名（SHA256/SHA1）、指数バックオフリトライ、イベントタイプ ワイルドカード フィルタ（`access.*` 等）、REST API での Webhook CRUD、Audit Log REST API、Scriptable handlers。**Apple Business Manager 等のエンタープライズ実績**。Maven Central 公開、Apache 2.0 |
| **vymalo/keycloak-webhook** | [vymalo/keycloak-webhook](https://github.com/vymalo/keycloak-webhook) | アクティブ | モジュラー設計（HTTP / AMQP-RabbitMQ / Syslog 各 Provider 分離）、OpenAPI 生成クライアント |
| **aznamier/keycloak-event-listener-rabbitmq** | [aznamier/...](https://github.com/aznamier/keycloak-event-listener-rabbitmq) | やや低速 | RabbitMQ 専用 |
| **juliuskrah/keycloak-kafka-event-listener** | [juliuskrah/...](https://github.com/juliuskrah/keycloak-kafka-event-listener) | 限定的 | Kafka 専用 |
| **jessylenne/keycloak-event-listener-http** | [jessylenne/...](https://github.com/jessylenne/keycloak-event-listener-http) | 古い | 単純 HTTP POST |

**業界の確立した知見**: **Phase Two `keycloak-events` を採用することがデファクト**。「Keycloak Webhook が欲しい」→「まず Phase Two」が業界共通認識。

### 3.3 Phase Two `keycloak-events` の主要機能

- **HMAC 署名**: SHA256/SHA1 で送信ボディを署名、`X-Keycloak-Signature` ヘッダ付与
- **指数バックオフリトライ**: 初期 1s、最大 60s、5xx/timeout のみリトライ（4xx はしない、業界標準パターン）
- **イベントタイプ フィルタ**: ワイルドカード対応（`access.*` で認証系全部、`admin.*` で管理操作全部）
- **REST API**: `POST /auth/realms/<realm>/webhooks` で CRUD
- **Audit Log API**: イベント履歴の検索・取得
- **Scriptable handlers**: GraalJS で受信側カスタムロジック挿入可能

### 3.4 自作する場合の設計パターン

Phase Two 採用しない場合 / 強い要件がある場合の Event Listener SPI 自作:

```java
public class CustomWebhookEventListenerProvider implements EventListenerProvider {
    private final ExecutorService executor;  // 非同期化必須
    private final HttpClient httpClient;     // Java 11+ HttpClient

    @Override
    public void onEvent(Event event) {
        executor.submit(() -> sendWebhook(event));  // 非同期送出
    }

    private void sendWebhook(Event event) {
        String body = serializeEvent(event);
        String signature = hmacSha256(secret, body);
        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create(webhookUrl))
            .header("X-Keycloak-Signature", signature)
            .header("X-Keycloak-Event-Id", event.getId())
            .POST(BodyPublishers.ofString(body))
            .build();
        sendWithRetry(request);  // 指数バックオフ
    }
}
```

**設計要素**:
1. **非同期化**: `ExecutorService` で別スレッド実行（ログイン応答ブロック回避）
2. **HMAC 署名**: GitHub Webhooks 互換パターン
3. **Retry**: 指数バックオフ（初期 1s、倍率 2、jitter 0.5、最大 60s）
4. **Dead Letter Queue**: 失敗イベントを別 DB or S3 に蓄積
5. **冪等性 ID**: `event_id` を必ず付与（受信側で重複排除）
6. **順序保証**: Keycloak は順序保証無し → 受信側で timestamp ソート

**参考実装**: Phase Two の `HttpSenderEventListenerProvider` のソースが最良の教材。

### 3.5 Cognito との対比（参考）

| 機能 | Cognito | Keycloak |
|---|:-:|:-:|
| 標準 Webhook | ❌ → EventBridge + Lambda 自作 | ❌ → Phase Two 拡張 or 自作 |
| HMAC 署名 / Retry | EventBridge + SQS で実装 | Phase Two 標準対応 |
| 設定難易度 | AWS リソース 4-5 種類組合せ | Phase Two 採用なら 5-10 分作業 |

→ **Keycloak + Phase Two の方が Webhook 運用容易**（AWS マネジメントコスト不要）。

### 3.6 SCIM 受信プラグイン（別軸、参考整理）

> **重要**: SCIM 受信は **OUTBOUND Webhook とは別軸の機能**。Phase Two Webhook (`keycloak-events`) を採用したからといって SCIM 受信機能が付いてくるわけではない。**独立して採否判断する**。

#### 3.6.1 2026-04 の重要な状況変化: Keycloak ネイティブ SCIM Realm API

| 項目 | 内容 |
|---|---|
| **公式発表** | [Keycloak 26.6 で SCIM Realm API を Experimental Feature として追加](https://www.keycloak.org/2026/04/scim-as-experimental-feature)（2026-04）|
| **対応方向** | **SCIM Server**（受信のみ）— 外部システム（顧客 IdP）が Keycloak ユーザー・グループを管理 |
| **対応オペレーション** | POST / GET / PATCH / PUT / DELETE、フィルタリング、ページネーション |
| **未対応** | バルク操作 / パスワード管理 / ソート |
| **互換性最優先** | **Microsoft Entra ID 互換性**を最優先設計（Entra SCIM Validator で検証）|
| **本番採用判断** | ⚠ **Experimental** のため API 変更可能性あり、本番採用は慎重に。デフォルトでは無効、明示的に有効化必要 |
| **将来性** | カスタムスキーマ / UI 機能はロードマップ上、**将来は本命候補** |

#### 3.6.2 SCIM 受信プラグインの選択肢（2026-06 時点）

| 選択肢 | 状況 | OSS / 商用 | 推奨度 |
|---|---|---|:-:|
| **A. Keycloak 26.6+ ネイティブ Experimental** | 2026-04 追加、Microsoft Entra ID 互換最優先 | ✅ OSS（Apache 2.0）| ★★ 将来の本命、現時点は様子見 |
| **B. Phase Two SCIM**（Per-org SCIM endpoints）| **Production 利用実績あり**（"already in production use"）、SaaS で広く採用 | ⚠ Phase Two 全般 Elastic License v2、コア OSS かは要確認 | ★★★ 既に Phase Two 採用なら一体化、マルチテナント設計が秀逸 |
| **C. Captain-P-Goldfish/scim-for-keycloak** | **OSS 版は kc-21 で EOL**（Keycloak 26 非対応）、Enterprise 版のみ継続 | OSS（EOL）/ Enterprise | ✕ **新規採用候補から外れる** |
| **D. mitodl/keycloak-scim** | SCIM Client プラグイン（送信側）| OSS | △ 受信ではないため本件用途と方向違い |
| **E. SCIM 受信不要**（JIT のみ）| §5.1 JIT-first 方針なら採用しない | - | ★★★ ミニマル構成、推奨デフォルト |

#### 3.6.3 採用パターン 4 マトリクス（Webhook + SCIM 受信の組合せ）

| パターン | SCIM 受信 | Webhook | プラグイン構成 | 想定シーン |
|---|:-:|:-:|---|---|
| **A. ミニマル** | ❌ JIT のみ | ❌ なし | プラグイン 0 | 最軽量、初期 PoC / §5.1 JIT-first 顧客 |
| **B. Webhook 追加** ⭐推奨初期 | ❌ JIT のみ | ✅ 必要 | Phase Two `keycloak-events` のみ | **中庸、Webhook 必要顧客 5-20% 想定** |
| **C. SCIM 追加**（Webhook 不要）| ✅ 必要 | ❌ なし | SCIM Plugin のみ | SCIM 受信顧客のみ、Webhook 不要レア |
| **D. フル機能** | ✅ 必要 | ✅ 必要 | **Phase Two で SCIM + Webhook + Audit Log 統合** | 大口顧客対応、同一ベンダー一体運用 |

#### 3.6.4 Phase Two SCIM の Per-org SCIM endpoints の特徴

- ✅ **1 組織 = 1 SCIM Endpoint** のマルチテナント設計
- ✅ 顧客企業ごとに独立した SCIM URL（`https://auth.example.com/scim/v2/orgs/{org_id}/`）
- ✅ 顧客企業の Microsoft Entra / Okta から SCIM Provisioning 設定可能
- ✅ Phase Two の他機能（Organizations / Webhooks / Audit Logs / Magic Links）と統合
- ⚠ Per-org エンドポイント方式は **マルチテナント B2B SaaS との相性が良い**（本プロジェクト適合）

#### 3.6.5 本プロジェクトでの段階的採用ロードマップ

| Phase | SCIM 受信 | Webhook | コメント |
|---|---|---|---|
| **Phase 1（初期、推奨）** | ❌ 不要 | ✅ Phase Two `keycloak-events` | パターン B、Webhook 基盤確立 |
| **Phase 2（大口顧客追加時）** | ✅ Phase Two SCIM 追加 | ✅ 継続 | パターン D、同一ベンダーで運用統合 |
| **Phase 3（将来）** | Keycloak 26+ ネイティブへ移行検討 | ✅ 継続 | ネイティブ機能の安定化を待つ |

---

## 4. SSF / CAEP（業界次世代標準）対応状況

### 4.1 概要

- **SSF (Shared Signals Framework)**: OpenID Foundation 標準、RFC 8417 SET (Security Event Token) ベースの認証イベント PUSH 仕様
- **CAEP (Continuous Access Evaluation Protocol)**: SSF 上の認証イベント仕様（`session-revoked` / `credential-change` / `token-claims-change` 等）
- **業界主要 IdP の対応**: Microsoft Entra（CAE 独自実装）、Okta（SSF Transmitter/Receiver 両対応）、Authentik（2025.2+ Transmitter 標準対応）

### 4.2 Keycloak の対応状況（2026-06 時点）

| 項目 | 状況 |
|---|---|
| **ネイティブサポート** | ❌ **未対応** |
| **コミュニティ PoC** | [identitytailor/keycloak-ssf-support](https://github.com/identitytailor/keycloak-ssf-support)（Thomas Darimont、Keycloak コミッタ）|
| **進行中の PR** | 2026 年 4 月に PR #48256 で SSF Transmitter 提案中（Apple Business Manager 互換）|
| **設計ドキュメント** | [Thomas Darimont の Gist](https://gist.github.com/thomasdarimont/75b14d423ee47392d10f86643244b2a2) |

### 4.3 業界比較

| OSS IdP | SSF Transmitter | SSF Receiver |
|---|:-:|:-:|
| **Keycloak** | ❌ PoC のみ | ❌ |
| **Authentik** | ✅ 2025.2+ Enterprise | ⚠ 部分対応 |
| Auth0 (商用) | ⚠ Beta | ⚠ Beta |
| Microsoft Entra | ✅ CAE 独自実装 | ✅ |
| Okta | ✅ | ✅ |

**業界の確立した知見**: 「Keycloak で SSF/CAEP が必要なら 2026 年時点では自前パッチ覚悟、もしくは Authentik 検討」が共通認識。本プロジェクトでは **将来拡張枠** として位置付け、当面は Phase Two Webhook で代替。

---

## 5. 初期実装で必要なこと（時系列）

### Phase 0: 開発環境セットアップ（1-2 日）

| # | 作業 | 詳細 |
|:-:|---|---|
| 1 | JDK 17+ インストール | Keycloak 26 は JDK 17/21 サポート |
| 2 | Maven 3.8+ or Gradle | プロジェクトビルド用 |
| 3 | IntelliJ IDEA Community 等 IDE | SPI デバッグ環境 |
| 4 | Keycloak 開発インスタンス | Docker / Quay / Operator のいずれか |
| 5 | サンプルプロジェクト取得 | [keycloak/keycloak-quickstarts](https://github.com/keycloak/keycloak-quickstarts) の `extension/` 配下 + [dasniko/keycloak-extensions-demo](https://github.com/dasniko/keycloak-extensions-demo) |

### Phase 1: 最初の SPI 実装（1-3 日）

| # | 作業 | 詳細 |
|:-:|---|---|
| 1 | プロジェクト初期化 | quickstarts テンプレートを流用 |
| 2 | `pom.xml` 依存設定 | `org.keycloak:keycloak-server-spi` `keycloak-server-spi-private` `keycloak-services` を **`provided` スコープ** 指定 |
| 3 | `@AutoService` 利用 | Google AutoService で `META-INF/services` 自動生成推奨 |
| 4 | Provider + ProviderFactory 実装 | 用途別の SPI インターフェース実装 |
| 5 | `mvn clean package` | JAR ビルド |
| 6 | JAR を `${KC_HOME}/providers/` に配置 | デプロイ |
| 7 | `bin/kc.sh build` 実行 | 閉世界アセンブリ再構築 |
| 8 | `bin/kc.sh start` 起動 | サーバー起動 |
| 9 | Admin Console > Server Info > Providers | Factory ID 検出確認 |
| 10 | Realm/Client で SPI 有効化 | GUI / kcadm.sh / Realm Export / Terraform |

### Phase 2: CI/CD パイプライン構築（2-5 日）

| # | 作業 | 詳細 |
|:-:|---|---|
| 1 | GitHub Actions ワークフロー | `mvn package` → JAR アーティファクト生成 |
| 2 | Container Image 構築 | カスタム SPI 焼込み Keycloak Image（Dockerfile で `COPY *.jar /opt/keycloak/providers/` + `RUN kc.sh build`）|
| 3 | Image Registry プッシュ | ECR / GHCR / Quay |
| 4 | Helm Chart / Operator 対応 | K8s 展開 |
| 5 | ステージング環境デプロイ | 検証用 Realm + テストクライアント |
| 6 | リモートデバッグ設定 | `bin/kc.sh start-dev --debug` でポート 8787 オープン |

### Phase 3: IaC 化（3-7 日）

| # | 作業 | 詳細 |
|:-:|---|---|
| 1 | Terraform Provider 導入 | **`keycloak/terraform-provider-keycloak`** （元 `mrparkers/keycloak`、2026 年公式組織に移管完了）|
| 2 | Realm 設定の Terraform 記述 | Realm / Client / Authentication Flow / Mapper / Identity Provider 等 |
| 3 | Keycloak Operator 検討 | K8s 環境なら `KeycloakRealmImport` CR（**新規投入のみ、Update/Delete 非対応**）|
| 4 | Realm Export / Import 運用 | シークレットは別管理（Sealed Secrets / HashiCorp Vault） |
| 5 | RightCrowd Operator 検討 | [RightCrowd/keycloak-realm-operator](https://github.com/RightCrowd/keycloak-realm-operator) — Realm 内リソースの差分管理対応（公式 Operator の欠点補完） |

**実現解**: Terraform Provider + Keycloak Operator の併用が現実解（Operator 単独では Realm 初期投入のみで差分管理に弱い）。

### Phase 4: Webhook 基盤導入（Phase Two 採用なら 1-2 日）

| # | 作業 | 詳細 |
|:-:|---|---|
| 1 | Phase Two JAR 取得 | Maven Central or GitHub Release |
| 2 | `providers/` に配置 + `kc.sh build` | 標準デプロイフロー |
| 3 | Webhook タブ確認 | Admin Console で Webhooks 管理 UI 追加 |
| 4 | Webhook Subscriber 登録 | URL / Event Type / HMAC secret 設定 |
| 5 | 受信側エンドポイント実装 | HMAC 検証 + 冪等性 + 2xx 即時返却 |
| 6 | E2E 動作確認 | テストイベント発火 → 受信側ログ確認 |

### 初期実装の総工数目安

| シナリオ | 工数目安 |
|---|---|
| **標準 Mapper のみ + Phase Two Webhook**（カスタム SPI なし）| **1-2 週間**（IaC + CI/CD 含む）|
| **+ カスタム Protocol Mapper 1 個** | + 1 週間 |
| **+ カスタム Authenticator（ステップアップ等）1 個** | + 2-3 週間 |
| **+ User Storage SPI（外部 DB 連携）** | + 2-4 週間 |

---

## 6. 運用時の作業（シナリオ別フロー）

### 6.1 シナリオ: 新しい JWT クレームを 1 つ追加

| ケース | 作業 | 所要時間 |
|---|---|:-:|
| **ユーザー属性ベース**（標準 Mapper）| Admin Console > Clients > Client Scopes > Mappers > User Attribute Mapper 追加 / または Terraform `keycloak_openid_user_attribute_protocol_mapper` リソース 1 つ追加 | **5-10 分** |
| **ロール / グループベース** | 標準 Role/Group Mapper 設定 | **5-10 分** |
| **動的計算**（JavaScript）| Script Mapper（`--features=scripts` 有効化必須、本番非推奨派あり）| **30 分-1 時間** |
| **外部 API 呼出が必要** | カスタム Protocol Mapper SPI 開発 → 再デプロイ | **半日-数日** + デプロイ作業 |

**影響範囲**:
- 次回トークン発行から反映
- **既発行 Refresh Token を持つユーザーは更新時まで遅延**
- ロールアウト戦略: Refresh Token TTL を短縮しておく / 重要変更時は全 Token Revocation

### 6.2 シナリオ: 新しい Webhook 送信先を 1 つ追加（Phase Two 採用前提）

| # | 作業 | 詳細 |
|:-:|---|---|
| 1 | HMAC `secret` 生成 | OpenSSL / KMS / Vault で 32 バイト乱数 |
| 2 | 送信先と secret 共有 | HashiCorp Vault / AWS Secrets Manager 推奨 |
| 3 | Admin Console > Webhooks タブ | URL / Event Type フィルタ / HMAC secret 入力 / または REST API `POST /auth/realms/<realm>/webhooks` |
| 4 | 受信側エンドポイント実装 | 2xx 即時返却、HMAC 検証、冪等性（同一 `event_id` 重複排除）、5xx でリトライ発生意識 |
| 5 | テストイベント発火 | 動作確認 |
| 6 | 監視追加 | 失敗率 / レイテンシ / Dead Letter |

**所要時間**: **10-30 分**（既存 Webhook 基盤がある場合）

### 6.3 シナリオ: カスタム Authenticator（カスタム MFA 等）を 1 つ追加

| # | 作業 | 詳細 | 所要時間 |
|:-:|---|---|:-:|
| 1 | Java SPI 実装 | Authenticator + AuthenticatorFactory + FreeMarker テンプレート | **数日-数週間** |
| 2 | 単体テスト | Mock ベース + 統合テスト | 1-2 日 |
| 3 | Container Image 再構築 | カスタム SPI を焼込み | 数時間 |
| 4 | ステージング `providers/` に配置 | 検証環境デプロイ | 1 時間 |
| 5 | ステージング Realm に Flow 追加 | Authentication Flow 設計 + Execution 追加 | 1-2 時間 |
| 6 | テストクライアントで動作確認 | E2E テスト | 半日 |
| 7 | 本番 Container Image 再構築 + ロールアウト | Rolling Update（26.6+ パッチ間ローリング対応）| 1-2 時間 |
| 8 | A/B 検証 | Client 単位 Flow オーバーライドで段階展開 | - |

**所要時間**: 初回 **2-4 週間**、2 個目以降は **1-2 週間**

### 6.4 シナリオ: Keycloak のメジャー/マイナーバージョンアップ

| バージョン | 主な SPI 破壊変更 |
|---|---|
| **24.0** | `UserProfileDecorator` インターフェース変更 |
| **25.0** | `UserQueryProvider` シグネチャ変更 / `AccessToken/IDToken/JsonWebToken` deprecated メソッド削除 / `PasswordHashProvider#encode` deprecated |
| **26.0** | `ClusterProvider` 新メソッド追加 / `SingleUseObjectProvider` 仕様変更 / HTTP Client redirect デフォルト変更 |

**作業量目安**:
- SPI 1 本あたり **数時間-数日のソース修正**
- + 再ビルド + 回帰テスト
- + 本番ロールアウト

**ダウンタイム**:
- 26.6 以降同一マイナー内パッチは **ローリング可能**
- マイナー/メジャーは **Blue-Green 推奨**

**業界の知見**: **SPI 内製を選んだ時点で継続メンテ工数を見込む必要あり**。Quarkus 化（17 系）+ RESTEasy Classic 廃止は最大の地雷だったが既に通過済み。

### 6.5 シナリオ: Webhook 送信先（受信エンドポイント）の追加・変更

| 変更内容 | 作業 |
|---|---|
| **URL 変更** | Admin Console で Webhook 編集（5 分）|
| **Event Type フィルタ追加** | Webhook 編集（5 分）|
| **HMAC secret ローテーション** | 旧 secret で送信中 → 新 secret 配布 → 切替 → 旧失効（10-30 分）|
| **新規受信側アプリ追加** | 6.2 と同じ |

### 6.6 運用作業量サマリー

| 作業頻度 | 作業内容 | 1 回あたり工数 |
|---|---|---|
| **月数回** | 標準 Mapper / Webhook Subscriber 追加 | 5-30 分 |
| **四半期数回** | カスタム Protocol Mapper / Identity Provider Mapper 追加 | 半日-数日 |
| **年数回** | カスタム Authenticator / User Storage SPI 追加 | 1-4 週間 |
| **年 1-2 回** | Keycloak バージョンアップ（マイナー）| SPI 数 × 数時間-数日 + 検証期間 |
| **継続** | Webhook 監視 / Dead Letter 処理 / HMAC ローテーション | 数時間/月 |

---

## 7. 既知の落とし穴 + 性能 + セキュリティ

### 7.1 性能の落とし穴

| # | 問題 | 影響 | 対策 |
|:-:|---|---|---|
| 1 | **Event Listener の同期実行** | Webhook 送信先レイテンシがログイン応答時間に上乗せ | **必ず非同期化**（ExecutorService 経由）|
| 2 | **Pre-Token-Generation の遅延** | トークン発行ごとに毎回実行、外部 API 呼出で大幅劣化 | 外部 API は厳禁、必要なら Caffeine 等でキャッシュ |
| 3 | **ロール数増加で SQL N+1 化** | [GitHub #15174](https://github.com/keycloak/keycloak/discussions/15174) — トークン生成時に劣化 | Realm 設計でロール最小化、グループ階層化 |
| 4 | **Webhook の順序保証なし** | アプリ側で受信順序逆転発生 | `event_id` + `timestamp` で受信側ソート、Kafka 経由検討 |

### 7.2 セキュリティの落とし穴

| # | 問題 | 対策 |
|:-:|---|---|
| 1 | **Protocol Mapper でクレーム改ざん** | `sub` / `azp` / `iss` 等のコアクレーム上書き禁止のレビュー徹底 |
| 2 | **Authenticator SPI の認証バイパス** | 認証判定ロジックのレビュー + 統合テスト必須 |
| 3 | **Webhook の HMAC 検証漏れ** | 受信側で必ず HMAC 検証、ヘッダ欠落時は 401 |
| 4 | **Webhook 受信エンドポイントの DoS** | Rate Limit / WAF 設定、認証必須 |
| 5 | **SPI 開発者の OIDC 仕様知識不足** | 開発前に OAuth/OIDC 仕様精読、ペアレビュー |

### 7.3 テスト・運用の落とし穴

| # | 問題 | 対策 |
|:-:|---|---|
| 1 | **SPI 単体テスト困難性** | Testcontainers + 実 Keycloak コンテナで統合テスト ([dasniko demo](https://github.com/dasniko/keycloak-extensions-demo) 参考)|
| 2 | **マネージド Keycloak の制約** | Cloud-IAM 等のマネージドサービスは `providers/` 直接アクセス不可、専用 UI 経由必須 |
| 3 | **Realm Export のシークレット混在** | Export 前にシークレット除外、別管理 |
| 4 | **Keycloak Operator の Realm 同期制限** | 新規投入のみ、Update/Delete 非対応 → RightCrowd Operator や Terraform で補完 |

### 7.4 商用サポート観点

- **Red Hat RHBK**: SPI による拡張自体は可能、**ただし Red Hat サポート対象は「テスト済み構成」に限定**。カスタム SPI は「動作するが Red Hat サポート対象外」が原則
- **Phase Two SaaS**: Phase Two が SaaS 製品として商用提供、エンタープライズ顧客実績多数
- **Cloud-IAM**: マネージド Keycloak、Custom Extension マーケットプレース型管理

---

## 8. 本プロジェクトでの設計指針

### 8.1 採用方針（初期）

| 観点 | 方針 |
|---|---|
| **INBOUND Hook** | 標準 SPI 機能を最大活用、カスタム SPI は必要最小限 |
| **Protocol Mapper** | 標準 User Attribute Mapper / Role Mapper 中心、カスタム SPI なし（§4.1 最小クレーム設計と整合）|
| **Authenticator** | 標準（Username/Password + OTP + WebAuthn）で開始、ステップアップ等は §4.6 の必要性確定後に検討 |
| **Event Listener** | **Phase Two `keycloak-events` を採用**、自作なし（メンテ性・実績で最有力）|
| **OUTBOUND Webhook** | Phase Two `keycloak-events` 経由で必要な顧客にのみ提供、デフォルトはオフ |
| **SCIM 受信プラグイン（別軸）** | **§5.1 JIT-first 方針なら Phase 1 では不要**、大口顧客追加時に **Phase Two SCIM** を Phase 2 で追加検討（→ §3.6）|
| **SSF / CAEP** | 当面未対応、将来拡張として §7.4 ITDR と連動検討 |
| **IaC** | Terraform Provider（`keycloak/terraform-provider-keycloak`）+ Keycloak Operator（K8s 採用時）|

### 8.2 段階的拡張ロードマップ（3 軸: INBOUND Hook / OUTBOUND Webhook / SCIM 受信）

| Phase | INBOUND Hook | OUTBOUND Webhook | SCIM 受信 | コメント |
|---|---|---|---|---|
| **Phase 1（初期、推奨）** | 標準 SPI + IaC（Terraform）| **Phase Two `keycloak-events`** | ❌ 不要（JIT のみ）| 採用パターン B（§3.6.3）、Webhook 必要顧客 5-20% に対応 |
| **Phase 2（大口顧客追加時）** | + カスタム Protocol Mapper（業務ロール拡張、必要時のみ）| 継続（Subscriber 増設）| **Phase Two SCIM 追加**（採用パターン D、同一ベンダー統合）| 大口顧客の SCIM 受信要件対応 |
| **Phase 3（高度要件時）** | + カスタム Authenticator（ステップアップ / リスクベース）| 継続 | Keycloak 26+ ネイティブ Experimental の安定化を待って移行検討 | SSF/CAEP 採否、§7.4 ITDR と連動 |

### 8.3 ヒアリングで確認すべき項目（Hook + SCIM 観点）

| # | 項目 | 影響 |
|:-:|---|---|
| 1 | OUTBOUND Webhook を必要とする業務シナリオ | Phase Two `keycloak-events` 採用判断 |
| 2 | **SCIM 受信を必要とする顧客の有無**（§5.1 同期方針）| **SCIM Plugin 採否**（パターン A/B vs C/D、§3.6.3）|
| 3 | カスタム MFA / ステップアップの要否 | カスタム Authenticator 開発の有無（§4.6）|
| 4 | 外部 DB / レガシー認証連携の有無 | User Storage SPI 開発の有無 |
| 5 | JWT に載せる業務ロールの粒度 | カスタム Protocol Mapper の必要性（§4.1）|
| 6 | SSF/CAEP 対応の将来要件 | Phase 3 計画への影響 |
| 7 | **大口顧客で SCIM + Webhook 両方期待されるか** | **Phase Two 一本化（パターン D）採否** |
| 8 | **退職反映 SLA の厳しさ** | SCIM 必須化判定（Webhook + JIT で代替不可な場合のみ SCIM 必須）|

### 8.4 SPI 開発の内製 vs 外注判断

| 観点 | 内製 | 外注 |
|---|---|---|
| Java/Keycloak 知見有 | ◎ | ○ |
| Java/Keycloak 知見無 | ✕ 学習コスト高 | ◎（Skycloak / SPI Factory 等専門ベンダー）|
| 継続的開発予定 | ◎ ノウハウ蓄積 | ✕ ベンダー依存 |
| 単発開発 | ✕ 教育コスト | ◎ |

→ **本プロジェクトは継続開発前提のため内製推奨**、初期は Skycloak 等の外部レビューを併用も選択肢。

### 8.5 Phase Two ライセンス考慮（Elastic License v2）

Phase Two 拡張全般（`keycloak-events` / `keycloak-orgs` / SCIM 拡張等）は **Elastic License v2 (ELv2)** を採用。本プロジェクトでの考慮事項:

| 利用形態 | ELv2 制約 | 本プロジェクト適合性 |
|---|:-:|:-:|
| **社内認証基盤として利用** | ✅ OK | ✅ 完全適合 |
| **顧客向け B2B SaaS の認証機能として組み込み**（本プロジェクト想定）| ✅ 一般的に OK | ✅ **適合**（業務 SaaS の中核機能ではない、認証は補助的位置付け）|
| **改変・再配布** | ✅ OK | - |
| **「Keycloak as a Service」競合 SaaS 化**（認証基盤そのものを商用提供）| ❌ NG | ⚠ 該当する可能性あれば**法務確認必要** |
| **ライセンス回避目的の改変** | ❌ NG | - |

**判断**: **本プロジェクトの想定（B2B SaaS への認証機能組み込み）では ELv2 制約は問題なし**。ただし「認証基盤そのものを SaaS 製品として顧客に提供」する事業展開を検討する場合は、Phase Two との商用ライセンス契約 or 代替実装の判断が必要。

**代替**: Phase Two を採用しない場合は **Event Listener SPI で自作**（§3.4 参照、Phase Two のソースコードが教材として有用）。ただし HMAC 署名 / リトライ / DLQ 等を自前実装する必要があり、初期実装 2-4 週間 + 継続メンテ工数を見込む。

---

## 9. リファレンス

### 9.1 Keycloak 公式

- [Server Developer Guide](https://www.keycloak.org/docs/latest/server_development/index.html)
- [Upgrading Guide](https://www.keycloak.org/docs/latest/upgrading/index.html)
- [Configuring providers](https://www.keycloak.org/server/configuration-provider)
- [Operator: Realm Import](https://www.keycloak.org/operator/realm-import)
- [Extensions Catalog](https://www.keycloak.org/extensions)
- [Migrating to Quarkus distribution](https://www.keycloak.org/migration/migrating-to-quarkus)
- [keycloak-quickstarts](https://github.com/keycloak/keycloak-quickstarts) — `extension/` ディレクトリにサンプル豊富

### 9.2 GitHub Discussions / Issues（Keycloak 本体）

- [#41175 Built-in support for sending keycloak events via webhooks](https://github.com/keycloak/keycloak/discussions/41175)
- [#14217 SSF/CAEP/RISC support](https://github.com/keycloak/keycloak/discussions/14217)
- [#15174 Token generation cache size](https://github.com/keycloak/keycloak/discussions/15174)
- [#32902 SPI breaking-change migration guide](https://github.com/keycloak/keycloak/discussions/32902)

### 9.3 Red Hat RHBK 公式

- [RHBK 26.0 Server Developer Guide - SPI](https://docs.redhat.com/en/documentation/red_hat_build_of_keycloak/26.0/html/server_developer_guide/providers)
- [RHBK 26.4 User Storage SPI](https://docs.redhat.com/en/documentation/red_hat_build_of_keycloak/26.4/html/server_developer_guide/user-storage-spi)
- [RHBK Operator Custom Extensions KB#7060151](https://access.redhat.com/solutions/7060151)

### 9.4 主要 OSS 拡張

**OUTBOUND Webhook**:
- ⭐ [p2-inc/keycloak-events (Phase Two)](https://github.com/p2-inc/keycloak-events) / [Webhooks docs](https://phasetwo.io/docs/audit-logs/webhooks/) — ELv2、デファクト
- [vymalo/keycloak-webhook](https://github.com/vymalo/keycloak-webhook)

**SCIM 受信プラグイン**（別軸）:
- ⭐ [Keycloak 26.6 SCIM Realm API Experimental（公式発表 2026-04）](https://www.keycloak.org/2026/04/scim-as-experimental-feature) — 将来の本命
- [Phase Two SCIM (Per-org SCIM endpoints)](https://phasetwo.io/) — Production 利用実績あり
- ❌ [Captain-P-Goldfish/scim-for-keycloak](https://github.com/Captain-P-Goldfish/scim-for-keycloak) — **OSS 版は kc-21 で EOL**（参考のみ）
- [mitodl/keycloak-scim](https://github.com/mitodl/keycloak-scim) — SCIM Client 拡張（送信側、本件用途と方向違い）
- [Keycloak SCIM Support Survey Feedback (2026-02)](https://www.keycloak.org/2026/02/scim-support-survey-feedback) — 公式の SCIM 統合方針

**SSF/CAEP**:
- [identitytailor/keycloak-ssf-support](https://github.com/identitytailor/keycloak-ssf-support) — Thomas Darimont の SSF PoC

**IaC / 運用**:
- [keycloak/terraform-provider-keycloak](https://github.com/keycloak/terraform-provider-keycloak)
- [RightCrowd/keycloak-realm-operator](https://github.com/RightCrowd/keycloak-realm-operator)
- [dasniko/keycloak-extensions-demo](https://github.com/dasniko/keycloak-extensions-demo)

**ライセンス**:
- [Elastic License v2 (Phase Two 全般)](https://www.elastic.co/licensing/elastic-license)

### 9.5 業界記事・実装事例

- [Baeldung: Custom Protocol Mapper](https://www.baeldung.com/keycloak-custom-protocol-mapper)
- [Skycloak: Ultimate Guide to Custom Authentication Flows](https://skycloak.io/blog/ultimate-guide-to-custom-authentication-flows/)
- [Skycloak: Attribute Mapping in Brokering](https://skycloak.io/blog/attribute-mapping-in-keycloak-during-oidc-identity-brokering/)
- [Darren Sapalo: Send Keycloak webhook events](https://sapalo.dev/2021/06/16/send-keycloak-webhook-events/)
- [dev.to: Building Event Listener SPI Plugin](https://dev.to/adwaitthattey/building-an-event-listener-spi-plugin-for-keycloak-2044)
- [Cloud-IAM: Custom Extensions](https://documentation.cloud-iam.com/resources/custom-extension.html)
- [Thomas Darimont SSF design gist](https://gist.github.com/thomasdarimont/75b14d423ee47392d10f86643244b2a2)
- [Andrew Doering: AuthZEN + SSF series (2026)](https://andrewdoering.org/blog/2026/authzen-shared-signals-framework-part-1-fundamentals/)
- [Mesut Pişkin: 2FA via Email in Keycloak (Custom Auth SPI)](https://medium.com/@mesutpiskin/two-factor-authentication-via-email-in-keycloak-custom-auth-spi-935bbb3952a8)

### 9.6 関連内部ドキュメント

- [auth-patterns.md](auth-patterns.md) — 認証パターン総覧
- [authz-architecture-design.md](authz-architecture-design.md) — 認可アーキテクチャ
- [token-exchange-spec-and-patterns.md](token-exchange-spec-and-patterns.md) — Token Exchange
- [subdomain-architecture-notes.md](subdomain-architecture-notes.md) — サブドメイン構成
- [keycloak-network-architecture.md](keycloak-network-architecture.md) — Keycloak ネットワーク構成
- [platform-architecture-patterns.md](platform-architecture-patterns.md) — プラットフォーム別アーキ

---

## 改訂履歴

- 2026-06-05: 初版作成。Keycloak 26 特化、INBOUND/OUTBOUND Hook 分類 + Phase Two `keycloak-events` を OUTBOUND デファクトと位置付け + SSF/CAEP 未対応の現状整理 + 初期実装/運用作業の時系列フロー + 落とし穴集約。本プロジェクト設計指針として「Phase Two 採用 + 標準 SPI 中心 + カスタム SPI 最小化」を確定
- 2026-06-05: **SCIM 受信プラグインを独立軸として整理（§1 + §3.6 + §8）**。前版で混同していた「INBOUND Hook = SCIM Plugin 必須」を明示的に訂正。2026-04 の Keycloak 26.6 ネイティブ SCIM Realm API Experimental 追加情報を反映、Captain-P-Goldfish の OSS 版 kc-21 EOL を記録、Phase Two SCIM の Per-org endpoints 設計をマルチテナント向け推奨に位置付け。**採用パターン 4 マトリクス（A ミニマル / B Webhook のみ推奨初期 / C SCIM のみ / D フル機能）** を §3.6.3 に追加。**Elastic License v2 (ELv2) 適合性評価** を §8.5 に追加（本プロジェクト B2B SaaS 組込は ELv2 OK と判定）|
