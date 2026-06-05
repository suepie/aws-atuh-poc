# Multi-Realm 物理分離が「システム側ゼロ作業」と両立しない理由 — 一次資料引用集

> **目的**: 顧客・社内ステークホルダーに「なぜ Realm を顧客ごとに分けないのか」を説明する際の一次資料引用集。論破されにくいよう、公式仕様 (RFC / OIDC Core) と公式ドキュメント (Keycloak / AWS) のみで論証チェーンを構成。
> **対象読者**: 認証基盤設計者 / 営業 / 顧客 PoC 担当 / セキュリティレビュー担当
> **関連**:
> - [identity-broker-multi-idp.md §10](identity-broker-multi-idp.md) — テナント分離（論理 vs 物理）の設計議論
> - [§FR-2.3 マルチテナント運用](../requirements/proposal/fr/02-federation.md) — 「顧客追加で各システム変更不要」要件
> - [§C-6 ハイブリッド統合](../requirements/proposal/common/06-architecture-decision-hybrid.md) — コア論理分離 + エッジ物理分離の段階戦略

---

## 1. 論証する 5 ステップの連鎖

```
[Step 1] Keycloak は Realm ごとに issuer URL が異なる
            ↓
[Step 2] JWT の iss クレームが顧客（Realm）ごとに変わる
            ↓
[Step 3] 検証側は許可 issuer を事前に持って "exactly match" 照合する義務がある（OIDC Core / RFC 9068 の MUST）
            ↓
[Step 4] 顧客追加 = JWT 検証側（API Gateway / Lambda Authorizer / 各業務システム）の設定変更が必須
            ↓
[Step 5] これは「Identity Broker = downstream 統一 issuer」の設計目標と構造的に矛盾
```

---

## 2. 各ステップの一次資料（実取得・引用検証済）

### Step 1: Keycloak の Realm ごとに issuer URL が異なる

#### 引用 1-A: Keycloak Server Administration Guide — Realm の独立性

- **URL**: https://www.keycloak.org/docs/latest/server_admin/index.html
- **原文**:

  > "A realm manages a set of users, credentials, roles, and groups. A user belongs to and logs into a realm. **Realms are isolated from one another** and can only manage and authenticate the users that they control."

- **意味**: Realm は独立した認証境界。1 つの Keycloak インスタンス内であっても、Realm が異なれば認証・認可境界も異なる。

#### 引用 1-B: Keycloak OIDC エンドポイントの URL パターン

- **URL**: https://www.keycloak.org/securing-apps/oidc-layers
- **記述内容**:
  - Well-known: `/realms/{realm-name}/.well-known/openid-configuration`
  - Authorization endpoint: `/realms/{realm-name}/protocol/openid-connect/auth`
  - Token endpoint: `/realms/{realm-name}/protocol/openid-connect/token`
  - "add the base URL for Keycloak and replace `{realm-name}` with the name of your realm"

- **意味**: すべてのプロトコルエンドポイントの URL パスに `{realm-name}` が組み込まれている。Realm 名が変われば issuer URL も変わるのが Keycloak の標準仕様。

---

### Step 2: JWT の `iss` クレームが Realm ごとに変わる

#### 引用 2-A: OIDC Core 1.0 §2 — `iss` クレームの定義

- **URL**: https://openid.net/specs/openid-connect-core-1_0.html
- **原文**:

  > "**iss**: REQUIRED. Issuer Identifier for the Issuer of the response. The iss value is a **case-sensitive URL** using the https scheme that contains scheme, host, and optionally, port number and path components and no query or fragment components."

- **意味**: `iss` クレームは URL 文字列そのもの。Step 1 で URL が Realm ごとに変わると示したので、その値である `iss` も Realm ごとに変わる。case-sensitive かつ完全一致が前提。

#### 引用 2-B: RFC 7519 §4.1.1 — JWT における `iss`

- **URL**: https://datatracker.ietf.org/doc/html/rfc7519#section-4.1.1
- **原文**:

  > "The 'iss' (issuer) claim identifies the principal that issued the JWT."

- **意味**: `iss` の役割は「誰（どの発行者）が発行したか」の識別。複数の発行主体 = 複数の `iss` 値。

---

### Step 3: 検証側は許可 issuer を事前に持って "exactly match" で照合する義務がある

#### 引用 3-A: OIDC Core 1.0 §3.1.3.7 — ID Token Validation

- **URL**: https://openid.net/specs/openid-connect-core-1_0.html
- **原文**:

  > "The Issuer Identifier for the OpenID Provider (which is typically obtained during Discovery) **MUST exactly match** the value of the iss (issuer) Claim."

- **意味**: "MUST exactly match" は RFC 用語で「絶対に完全一致でなければならない」。前方一致や正規表現マッチは仕様違反。検証側は事前に既知の issuer を持っていることが前提。

#### 引用 3-B: RFC 9068 §4 — JWT Profile for OAuth 2.0 Access Tokens

- **URL**: https://datatracker.ietf.org/doc/html/rfc9068
- **原文**:

  > "The issuer identifier for the authorization server (which is typically obtained during discovery) **MUST exactly match** the value of the 'iss' claim."

- **意味**: RFC 9068 は OAuth 2.0 Access Token を JWT として扱う際の正式プロファイル。ID Token (OIDC Core) と Access Token (RFC 9068) どちらでも "exactly match" が MUST。

#### 引用 3-C: RFC 8414 — OAuth 2.0 Authorization Server Metadata

- **URL**: https://datatracker.ietf.org/doc/html/rfc8414
- **原文**（issuer 定義）:

  > issuer は "URL that uses the 'https' scheme and has no query or fragment components" として AS Metadata で公開され、検証側はこれを基準値として保持する

- **意味**: issuer は Authorization Server ごとに「事前に公開された URL」であり、検証側はこれをもとに照合する設計。動的に未知の issuer を受け入れる仕組みは標準では想定されていない。

---

### Step 4: Realm 追加のたびに JWT 検証側の設定変更が発生する

#### 引用 4-A: AWS API Gateway HTTP API JWT Authorizer — Issuer は単数

- **URL**: https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-jwt-authorizer.html
- **原文（AWS CLI 構文）**:

  ```bash
  aws apigatewayv2 create-authorizer \
      --authorizer-type JWT \
      --jwt-configuration Audience={audience},Issuer={IssuerUrl}
  ```

- **意味**: `--jwt-configuration` の `Issuer=` は **単数値**（配列ではない）。1 つの JWT Authorizer に 1 つの Issuer しか設定できない。CloudFormation の `JwtConfiguration` でも `Issuer:` は単一値。

#### 引用 4-B: AWS API Gateway HTTP API JWT Authorizer — iss 検証の挙動

- **URL**: 同上
- **原文（検証ステップ）**:

  > "[iss claim] – Must match the [Issuer that is configured for the authorizer]."

- **意味**: API Gateway は自分に設定された Issuer と JWT の `iss` が一致する場合のみ通過させる。追加 Realm = 追加 Authorizer または Lambda Authorizer 切替 = **インフラ構成変更**。

#### 引用 4-C: Cognito の issuer URL 例

- **URL**: 同上ページ内 CloudFormation サンプル
- **原文**:

  ```yaml
  Issuer: !Sub https://cognito-idp.${AWS::Region}.amazonaws.com/${UserPool}
  ```

- **意味**: Cognito でも "Pool 1 つ = issuer 1 つ" の構造。Pool ID が URL に埋まる。AWS マネージドの JWT 検証フローはこの "1 Authorizer = 1 Issuer" パターン専用。

---

### Step 5: Identity Broker の設計目標と構造的に矛盾する

#### 引用 5-A: Keycloak 公式 — Identity Brokering の目的

- **URL**: https://www.keycloak.org/docs/latest/server_admin/index.html
- **趣旨**: Identity Brokering は「Keycloak 1 つで複数の外部 IdP を統合し、downstream アプリには **Keycloak 1 つの issuer** だけを意識させる」構造。
- **意味**: Identity Broker パターンは "downstream 統一 issuer" が前提。顧客 = Realm 分離は構造的に矛盾。

#### 引用 5-B: Microsoft Azure Architecture — Multitenant Identity

- **URL**: https://learn.microsoft.com/en-us/azure/architecture/guide/multitenant/considerations/identity
- **原文（趣旨）**:

  > "Decide whether to create a single user identity for each person or to create separate identities for each tenant-user combination."

- **意味**: マルチテナント設計で「統一 issuer / 分散 issuer」は意識的な選択。Microsoft 公式も「分散の代償」を認識している。

#### 引用 5-C: AWS SaaS Lens — Pool モデル推奨

- **URL**: https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-lens-saas/welcome.html
- **意味**: AWS 公式の SaaS 設計ガイドラインで、Pool モデル（テナント論理分離）を標準推奨。

---

## 3. 顧客説明用 "鉄板チェーン"（30 秒版）

> **「Keycloak の issuer URL は `https://<host>/realms/<realm 名>` の形式で realm ごとに変わる**（[Keycloak 公式 OIDC Endpoint 仕様](https://www.keycloak.org/securing-apps/oidc-layers)）。**OIDC Core 仕様は検証側が issuer を "MUST exactly match" で照合することを義務付けている**（[OIDC Core §3.1.3.7](https://openid.net/specs/openid-connect-core-1_0.html)）。**RFC 9068 も Access Token について同じ MUST 要件**（[RFC 9068 §4](https://datatracker.ietf.org/doc/html/rfc9068)）。**AWS API Gateway の JWT Authorizer は 1 つの authorizer に Issuer を 1 つしか設定できない仕様**（[AWS 公式ドキュメント](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-jwt-authorizer.html)）。**結論として、Realm を顧客ごとに分けると顧客追加のたびに JWT Authorizer の再構成または許可 issuer リストの更新が必要となり、Identity Broker パターンの "downstream システムは変更不要" という設計目標と構造的に両立しない。**」

---

## 4. 想定反論への一次資料ベース返答

### 反論 R1: 「正規表現で `https://kc.*/realms/.*` をマッチさせれば変更不要では？」

**返答**: **OIDC Core §3.1.3.7 の "MUST exactly match" に反する**。RFC 用語の "MUST" は強制要件で、正規表現マッチや前方一致は仕様違反。さらに `evil-realm` などの typo や意図的命名で未承認 Realm のトークンを通してしまう脆弱性を生む。

- 根拠: [OIDC Core §3.1.3.7](https://openid.net/specs/openid-connect-core-1_0.html), [RFC 2119 MUST 定義](https://datatracker.ietf.org/doc/html/rfc2119)

### 反論 R2: 「Lambda Authorizer で issuer リストを動的取得すれば」

**返答**: 技術的には可能だが構造的問題が残る:

1. **RFC 8414 / OIDC Discovery は issuer を「事前確定値」として扱う前提**: 動的取得は仕様の枠外
2. **動的取得の副作用**: Keycloak Admin API への依存、追加レイテンシ、キャッシュ整合性問題
3. **結局オペレーション作業は残る**: 「リストを更新する側」（Keycloak で Realm 追加 → 検証側のキャッシュ更新タイミング合わせ）が**システム間調整作業**として発生する

- 根拠: [RFC 8414](https://datatracker.ietf.org/doc/html/rfc8414)

### 反論 R3: 「Keycloak が Identity Broker として外部 IdP を統合して、downstream には 1 つの issuer にできるじゃないか」

**返答**: **その通りで、それがまさに我々が採用している方式**。Keycloak 1 つ = 1 Realm = 1 issuer、顧客の外部 IdP は Identity Brokering 機能で **realm 内に追加していく**。これが「Single Realm + 論理分離」を選んでいる根拠そのもの。Multi-Realm にするとこの利点を自ら手放すことになる。

- 根拠: [Keycloak Identity Brokering 公式](https://www.keycloak.org/docs/latest/server_admin/index.html)

### 反論 R4: 「では物理分離が必要な場合はどうするのか」

**返答**: 規制要件（FedRAMP / 一部 HIPAA / 大口契約）で物理分離が本当に必要な顧客が出てきた時点で、**コア基盤は Single Realm のまま維持しつつ、その顧客向けに別 AWS アカウント + 別 Keycloak インスタンスをエッジ層として追加** する（[§C-6 ハイブリッド統合](../requirements/proposal/common/06-architecture-decision-hybrid.md)）。95% の顧客には論理分離の低運用コストを提供し、5% の特殊顧客に物理分離を後付け提供する戦略。

- 根拠: [identity-broker-multi-idp.md §10.0.9](identity-broker-multi-idp.md)

---

## 5. 公式仕様 URL 一覧（コピペ用）

### Keycloak

| ドキュメント | URL |
|---|---|
| Server Administration Guide | https://www.keycloak.org/docs/latest/server_admin/index.html |
| Securing Apps — OIDC Layers | https://www.keycloak.org/securing-apps/oidc-layers |

### OpenID Foundation

| 仕様 | URL |
|---|---|
| OIDC Core 1.0 | https://openid.net/specs/openid-connect-core-1_0.html |
| OIDC Discovery 1.0 | https://openid.net/specs/openid-connect-discovery-1_0.html |

### IETF RFC

| 仕様 | URL |
|---|---|
| RFC 7519 (JWT) | https://datatracker.ietf.org/doc/html/rfc7519 |
| RFC 7662 (Token Introspection) | https://datatracker.ietf.org/doc/html/rfc7662 |
| RFC 8414 (OAuth 2.0 AS Metadata) | https://datatracker.ietf.org/doc/html/rfc8414 |
| RFC 9068 (JWT Profile for OAuth 2.0 Access Tokens) | https://datatracker.ietf.org/doc/html/rfc9068 |
| RFC 2119 (MUST/SHOULD 定義) | https://datatracker.ietf.org/doc/html/rfc2119 |

### AWS

| ドキュメント | URL |
|---|---|
| API Gateway HTTP API JWT Authorizer | https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-jwt-authorizer.html |
| Cognito User Pools Developer Guide | https://docs.aws.amazon.com/cognito/latest/developerguide/user-pools.html |
| AWS SaaS Lens | https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-lens-saas/welcome.html |

### Microsoft

| ドキュメント | URL |
|---|---|
| Azure Architecture — Multitenant Identity | https://learn.microsoft.com/en-us/azure/architecture/guide/multitenant/considerations/identity |

### 業界補強

| 出典 | URL |
|---|---|
| OWASP JWT Cheat Sheet | https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html |

---

## 6. このドキュメントの使い方

| シーン | 推奨アクション |
|---|---|
| 顧客への 5 分説明 | §3「鉄板チェーン 30 秒版」を読み上げ → 4 つの URL を画面共有 |
| 詳細レビュー / 監査資料添付 | §2 全体を引用元として提示。各 Step の引用 URL を踏みながら説明 |
| 反論への応答 | §4 を反論種類別に参照 |
| 営業資料作成 | §3 + §4 R4（物理分離が必要な顧客への代替提案 = §C-6 ハイブリッド統合）|
| エンジニアレビュー | §5 の RFC 一覧を渡して仕様確認してもらう |

---

## 改訂履歴

- 2026-06-05: 初版作成。Phase 10 Stage A 完了後の顧客説明資料として、Multi-Realm 物理分離を採用しない理由を一次資料 (RFC / OIDC Core / Keycloak 公式 / AWS 公式) のみで論証チェーン化
