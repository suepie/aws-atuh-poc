# JWKS エンドポイントの公開に関する設計判断

**作成日**: 2026-04-20
**結論**: OIDCの公開エンドポイント（JWKS含む）はインターネット公開する。
Admin Consoleは別ALBでネットワーク分離する。

---

## 1. 前提：OIDC / OAuth 2.0 の仕様上の位置づけ

### JWKS エンドポイントとは

JWKSエンドポイント（`/.well-known/jwks.json`）は、JWT の署名検証に使う
**公開鍵の配布先**である。

```mermaid
flowchart LR
    KC["Keycloak<br/>（秘密鍵で署名）"]
    JWKS["JWKS エンドポイント<br/>（公開鍵を配布）"]
    RS["Resource Server<br/>（公開鍵で検証）"]

    KC -->|"JWTを発行<br/>秘密鍵で署名"| RS
    RS -->|"公開鍵を取得"| JWKS
    RS -->|"ローカルで署名検証"| RS
```

**RFC 7517（JSON Web Key）** で標準化されている仕様であり、
OAuth 2.0 / OpenID Connect のトークン検証インフラの根幹を成す。

### エンドポイントが返すもの

```json
{
  "keys": [
    {
      "kty": "RSA",
      "kid": "e3KFx04c50aA...",
      "use": "sig",
      "n": "0vx7agoebGcQ...",   ← 公開鍵の modulus
      "e": "AQAB"               ← 公開鍵の exponent
    }
  ]
}
```

**含まれるもの**: 公開鍵（`n`, `e`）のみ
**含まれないもの**: 秘密鍵（`d`, `p`, `q`, `dp`, `dq`, `qi`）は一切含まれない

---

## 2. 公開しても安全である根拠

### 2.1 暗号学的根拠

| 項目 | 説明 |
|------|------|
| 公開鍵の役割 | JWT署名の**検証**のみに使用 |
| 秘密鍵の役割 | JWT署名の**生成**に使用（JWKS には含まれない） |
| 公開鍵から秘密鍵を推定できるか | **不可能**（RSA / ECDSAの数学的安全性による） |

公開鍵暗号方式（RSA / ECDSA）では、公開鍵を知っていても秘密鍵を算出することは
計算量的に不可能（RSA-2048で2^112ビットセキュリティ）。
**これが「公開鍵」と呼ばれる理由であり、公開することが前提の設計**。

### 2.2 攻撃者が公開鍵を取得しても可能な行為

| 攻撃 | 可能か | 理由 |
|------|:------:|------|
| JWTの署名を検証する | ✅ | 正当な行為（公開鍵の本来の用途） |
| JWTの中身を読む | ✅ | JWTはBase64なので元々読める（暗号化ではない） |
| **偽のJWTを作成する** | **❌** | 秘密鍵がないと署名できない |
| **既存JWTを改ざんする** | **❌** | 署名が合わなくなり検証失敗する |
| **秘密鍵を推定する** | **❌** | 計算量的に不可能 |

### 2.3 HTTPS / TLS との比較

TLS証明書も同じ原理で動作している：

| | TLS証明書 | JWKS |
|--|----------|------|
| 公開鍵 | 全世界に配布（ブラウザが取得） | 全Resource Serverに配布 |
| 秘密鍵 | サーバー内に保管 | Keycloak/Cognito内に保管 |
| 公開鍵の公開 | **前提（インターネット上で公開）** | **前提（RFC 7517）** |

---

## 3. 公開する必要がある根拠

### 3.1 OIDC仕様上の要件

OpenID Connect Discovery 1.0 仕様では、`jwks_uri` は
`.well-known/openid-configuration` で公開され、全 Relying Party（Resource Server）が
アクセスできることが前提となっている。

**CognitoのJWKS**: `https://cognito-idp.{region}.amazonaws.com/{poolId}/.well-known/jwks.json`
→ **完全にパブリック**。認証不要でアクセス可能。

**Auth0のJWKS**: `https://{domain}/.well-known/jwks.json`
→ **完全にパブリック**。

**OktaのJWKS**: `https://{domain}/oauth2/default/v1/keys`
→ **完全にパブリック**。

**Google**: `https://www.googleapis.com/oauth2/v3/certs`
→ **完全にパブリック**。

**業界の全主要IdPがJWKSをパブリックに公開している。**

### 3.2 Resource Server がアクセスする必要性

```mermaid
sequenceDiagram
    participant RS as Resource Server<br/>（Lambda / ECS / Spring Boot）
    participant JWKS as JWKS エンドポイント
    participant IdP as IdP（秘密鍵保持）

    Note over RS: JWT を受け取った
    RS->>JWKS: GET /.well-known/jwks.json
    JWKS->>RS: 公開鍵を返却
    RS->>RS: ローカルで署名検証<br/>（IdP への問い合わせ不要）
    Note over RS: 検証成功 → リクエスト処理
    Note over RS,IdP: IdP に毎回問い合わせないのが<br/>JWT の性能上のメリット
```

Resource Server が JWT をローカル検証するためには、**公開鍵を事前に取得する必要がある**。
公開鍵が取得できなければ、以下の代替手段しかなくなる：

| 代替手段 | デメリット |
|---------|----------|
| Token Introspection（毎リクエストIdPに問い合わせ） | パフォーマンス大幅劣化、IdPが単一障害点 |
| 公開鍵をハードコード | 鍵ローテーション時にデプロイが必要 |
| 同一VPC内に全Resource Serverを配置 | Lambda等をVPC内に置く必要（NAT Gateway費用） |

### 3.3 公開しない場合のアーキテクチャへの影響

```mermaid
flowchart TB
    subgraph IfPublic["✅ JWKS公開（標準構成）"]
        Lambda1["Lambda Authorizer<br/>（VPC外）"]
        ECS1["ECS Backend<br/>（VPC内）"]
        Partner1["パートナーシステム<br/>（別VPC/別クラウド）"]
        JWKS1["JWKS エンドポイント<br/>（パブリック）"]

        Lambda1 -->|取得可能| JWKS1
        ECS1 -->|取得可能| JWKS1
        Partner1 -->|取得可能| JWKS1
    end

    subgraph IfPrivate["⚠ JWKS非公開（制約あり）"]
        Lambda2["Lambda Authorizer<br/>（VPC内必須）"]
        ECS2["ECS Backend<br/>（VPC内必須）"]
        Partner2["パートナーシステム<br/>（VPN必須）"]
        JWKS2["JWKS エンドポイント<br/>（VPC内のみ）"]
        NAT["NAT Gateway<br/>（$30+/月）"]

        Lambda2 -->|VPC内通信| JWKS2
        ECS2 -->|VPC内通信| JWKS2
        Partner2 -->|VPN経由| JWKS2
        Lambda2 -.->|外部通信に必要| NAT
    end
```

---

## 4. 公開すべきエンドポイントと非公開にすべきエンドポイント

| パス | 公開 | 理由 |
|------|:---:|------|
| `/.well-known/openid-configuration` | ✅ | OIDC Discovery（仕様上必須） |
| `/realms/{realm}/protocol/openid-connect/certs` | ✅ | JWKS公開鍵（署名検証用） |
| `/realms/{realm}/protocol/openid-connect/auth` | ✅ | 認証エンドポイント（ブラウザがアクセス） |
| `/realms/{realm}/protocol/openid-connect/token` | ✅ | トークンエンドポイント（SPA/Backend） |
| `/realms/{realm}/protocol/openid-connect/logout` | ✅ | ログアウト |
| **`/admin/*`** | **❌** | **Admin Console（管理者のみ）** |
| **`/metrics`** | **❌** | **Prometheus等の監視用** |
| **`/health/*`** | **❌** | **ヘルスチェック（内部用）** |

---

## 5. 本PoCでの設計

```mermaid
flowchart TB
    subgraph Internet["インターネット"]
        Browser["ブラウザ"]
        Lambda["Lambda Authorizer"]
        ExtRS["外部 Resource Server"]
    end

    subgraph AWS["AWS"]
        ALB_Public["Public ALB<br/>L4 SG: 0.0.0.0/0<br/>L7 Rule でパスベース制限"]
        ALB_Admin["Admin ALB<br/>L4 SG: 管理者IP限定<br/>L7: 全パス転送"]
        KC["Keycloak ECS"]
    end

    Browser -->|ログイン (IP制限)| ALB_Public
    Lambda -->|JWKS (全IP可)| ALB_Public
    ExtRS -->|JWKS (全IP可)| ALB_Public
    ALB_Admin -->|Admin Console| KC
    ALB_Public --> KC
    ALB_Admin --> KC
```

### 5.1 Public ALB の L7 パスベース制限（実装実態）

L4（SG）レベルでは `0.0.0.0/0` を許可しているが、**L7（Listener Rule）レベルで 3 段階の制限**を掛けている。

| 優先度 | パス条件 | ソース IP 条件 | 動作 |
|:------:|---------|:------------:|------|
| 100 | `/realms/*/.well-known/*` + `/realms/*/protocol/openid-connect/certs` | なし（全 IP） | Keycloak に転送 |
| 200 | 任意 | `my_ip + allowed_cidr_blocks` | Keycloak に転送 |
| default | — | — | **403 Forbidden 固定レスポンス** |

**要点**:
- JWKS / OIDC Discovery は Lambda Authorizer 等の出口 IP が不定のため**全 IP 許可が必須**
- ログイン画面・トークンエンドポイントはブラウザ IP が予測可能なため**IP 制限可能**
- L4 で SG を絞るとすべてのパスが不可になるため、L7 でパスベース制限している

| ALB | 用途 | L4 SG | L7 制限 |
|-----|------|-------|-------|
| Public ALB | OIDC認証 + JWKS | `0.0.0.0/0` | パスベース IP 制限（上記表） |
| Admin ALB | Admin Console | 管理者IP限定 | なし（全パス転送） |

> 詳細な IP 制限マトリクス・本番移行要件は [keycloak-network-architecture.md](keycloak-network-architecture.md) 参照。

---

## 6. 検証結果（PoCで実測）

公開が必要であることを実際に検証した。

### 検証手順

1. Public ALB の SG（L4）を `0.0.0.0/0` から特定IPのみに変更
   （Lambda の出口 IP は許可リスト外）
2. SPA から API Tester 経由で Backend Lambda にリクエスト
3. Lambda Authorizer が Keycloak の JWKS エンドポイントへアクセス試行

### 結果

| 状態 | Lambda Authorizer 動作 | API レスポンス |
|------|--------------------|--------------|
| Public ALB SG = `0.0.0.0/0` | ✅ JWKS 取得成功 | 200 OK |
| Public ALB SG = 特定IPのみ | ❌ JWKS取得タイムアウト/拒否 | 403 / CORS エラー |

→ Lambda（VPC外）から Keycloak の JWKS エンドポイントに到達できない場合、
  JWT 検証が一切できなくなる。

### この結果が示すこと

- 「Admin Console と JWKS を同じ ALB の SG だけで制限する」設計は不可
- 解決策は次の 3 つ:
  1. ALB を**公開用と管理用に分離**する（Public ALB + Admin ALB）
  2. **Lambda を VPC 内に配置**して VPC 内 IP を許可する
  3. **L7 Listener Rule でパスベース制限**する（SG は全開、JWKS パスのみ全公開、他は IP 制限）
- **本 PoC は 1 + 3 の組み合わせを採用**:
  - ALB 分離（Public + Admin）で管理画面を Admin ALB 側に隔離
  - さらに Public ALB 側は L7 でパスベース制限（JWKS は全公開、他は IP 制限、不明パスは 403）

---

## 7. 参考文献

- [RFC 7517 - JSON Web Key (JWK)](https://datatracker.ietf.org/doc/html/rfc7517)
- [OpenID Connect Discovery 1.0](https://openid.net/specs/openid-connect-discovery-1_0.html)
- [Keycloak - Configuring the hostname (v2)](https://www.keycloak.org/server/hostname) — `hostname-admin` による Admin 分離
- [Keycloak - Configuring the Management Interface](https://www.keycloak.org/server/management-interface) — 管理ポート分離
- [Keycloak - Configuring for production](https://www.keycloak.org/server/configuration-production) — 本番設定ガイド
- [AWS Cognito JWKS](https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-tokens-verifying-a-jwt.html) — Cognito もパブリック公開
- [Understanding the OIDC JWK Endpoint - MojoAuth](https://mojoauth.com/blog/understanding-the-oidc-json-web-key-jwk-endpoint-in-authentication)
- [Mastering JWKS: JSON Web Key Sets Explained](https://www.janbrennenstuhl.eu/jwks-json-web-key-set/)
