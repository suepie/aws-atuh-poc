# U6 付属: ネットワークフロー詳細図(基本設計時点)

作成: 2026-07-24 / 前提: [01 Baseline v1](01-architecture-baseline.md) + [06 U6 v1.4](06-infra-network-design.md) / 出典: ユーザー検討(フロー表 B-*/I-* 系)+ 抜けチェック(§A.3)
ステータス: Draft v1(mermaid 版。drawio 清書は別タスク)

## A.0 本書の位置づけ

U6 §6.1.1 の簡略図を、**入口・出口の全フロー(ID 付き)** と **ROSA HCP クラスタ内部** の 2 レベルに詳細化する。作図前提:

- **O-10 は案 B(zero-egress)前提で作図**: クラスタ VPC に NAT を置かず、①運用系(registry/STS 等)= VPC Endpoint 群で VPC 内完結 ②外向き(フェデ等)= TGW → 他組織 Egress VPC(NAT + NFW)。正式クローズは先方 TGW 接続可否確認後(U6 §6.8.1 O-10)
- 名前解決: **弊社(Broker Acct)の Route 53 Public Hosted Zone** で `auth./idp./scim-broker./scim-idp./admin./launchpad./api.` の CNAME(Alias)を**他組織 CloudFront のディストリビューションドメインに向ける**。DNS は弊社統制・エッジ実体は他組織という分担(REQ-OUT-04 の Resolver 整合と対)

## A.1 全体構成図(全フロー ID 付き)

```mermaid
flowchart TB
  %% ============ 外部 ============
  USER["利用者ブラウザ<br/>(エンドユーザ / テナント管理者)"]
  CIDP["顧客 IdP 1000+<br/>Entra/Okta/SAML"]
  HRIS["顧客 HRIS / IdP<br/>SCIM クライアント"]
  CAPP["顧客アプリ<br/>Webhook 受信 endpoint"]
  HIBP["HIBP<br/>api.pwnedpasswords.com"]
  CAD["顧客 AD<br/>(LDAPS 顧客のみ・条件付き)"]

  %% ============ DNS ============
  subgraph DNSZ["Broker Acct: Route 53 Public Zone(弊社統制)"]
    R53["auth. / idp. / scim-*. / admin. / launchpad. / api.<br/>CNAME → 他組織 CloudFront 各ディストリビューション"]
  end

  %% ============ 他組織 ============
  subgraph OTHER["═══ 他組織管理(要求仕様 REQ-* の対象)═══"]
    subgraph NAIN["NW 監査 Acct: Inbound"]
      CF["CloudFront + WAF(用途別)<br/>auth / idp / scim-broker / scim-idp<br/>admin(REQ-IN-03) / launchpad(REQ-IN-11) / api(REQ-IN-12)"]
      EDGE["ALB or NLB(In-B 推奨)<br/>+ Network Firewall Inbound"]
    end
    subgraph NAOUT["NW 監査 Acct: Egress VPC"]
      NFWO["NAT + Network Firewall<br/>ドメインフィルタ(REQ-OUT-01〜06)"]
    end
    subgraph NWA["NW Acct(要確認)"]
      TGW["Transit Gateway"]
    end
  end

  %% ============ Red Hat ============
  subgraph RH["Red Hat サービスアカウント"]
    CP1["HCP Control Plane #1<br/>API×2 + etcd×3(3AZ)"]
    CP2["HCP Control Plane #2<br/>API×2 + etcd×3(3AZ)"]
  end

  %% ============ Broker Acct ============
  subgraph BRK["🟠 Broker Acct(公開フェデの窓口)"]
    BALB["Internal ALB(専用サブネット)<br/>TLS 終端(In-B) / /admin 403 / secret hdr=追加層"]
    BKC["ROSA HCP #1: Broker KC<br/>(内部詳細は §A.2)"]
    BAPI["idm-api デプロイ #1<br/>= 管理画面 Backend + /api/me/apps"]
    BITDR["ITDR: EventBridge → Risk Engine λ<br/>→ DynamoDB(Global Tables)"]
    BWH["Webhook Dispatcher<br/>SQS + λ + DLQ"]
    BAUR[("Aurora Broker DB<br/>+ idmap 別 DB")]
    BPL["PrivateLink EP → RH CP #1"]
    BVPCE["VPC Endpoint 群<br/>S3/ECR/STS/KMS/Logs/SES(zero-egress)"]
  end

  %% ============ IdP-KC Acct ============
  subgraph IKC["🟡 IdP-KC Acct(PW ハッシュ保有・最も閉じる)"]
    IALB["Internal ALB"]
    IES["Ingress NLB を<br/>Endpoint Service 化(単方向着信)"]
    IKCP["ROSA HCP #2: IdP-KC<br/>(内部詳細は §A.2)"]
    IAPI["idm-api デプロイ #2<br/>= 専用 API 層(ユーザ CRUD)"]
    APPC["同居アプリ"]
    IAUR[("Aurora IdP-KC DB<br/>(PW ハッシュ)")]
    IPL["PrivateLink EP → RH CP #2"]
    IVPCE["VPC Endpoint 群(zero-egress)"]
  end

  %% ============ 監査 / App / 大阪 ============
  subgraph AUD["🔵 監査 Acct"]
    S3A[("監査 S3<br/>Object Lock 7y")]
    CAN["Central Canary(U9 D-U9-16)<br/>外形監視 + 認証実装漏れ検知"]
  end
  subgraph APPA["🟢 App Acct × N(内部詳細 = §A.1.1)"]
    RP["アプリ(RP)<br/>OIDC クライアント + JWT 検証器"]
  end
  OSA["大阪(DR): パイロットライト ×2<br/>infra Pool 稼働 + KC Pool min0 + Aurora Global Secondary"]

  %% ============ フロー(Inbound 公開) ============
  USER -.->|"名前解決"| R53
  USER ==>|"B-I1/I-I1 ログイン(auth./idp.)<br/>+ 管理画面/launchpad(追加 B-I6)"| CF
  CF ==> EDGE ==> TGW
  TGW ==>|"auth./admin./launchpad./api./scim-broker."| BALB
  TGW ==>|"idp./scim-idp."| IALB
  HRIS ==>|"B-I3/I-I4 SCIM(scim-*.)"| CF
  BALB --> BKC
  BALB --> BAPI
  IALB --> IKCP
  IALB --> IAPI

  %% ============ フロー(私設) ============
  RP -->|"B-I2 token/JWKS/introspection<br/>(VPC 内、ADR-012)"| TGW
  BKC -->|"B-O2 バックチャネル<br/>PrivateLink 単方向"| IES --> IKCP
  APPC -->|"I-I3 ユーザ CRUD(Acct 内)"| IAPI --> IKCP
  IKCP -->|"I-O2 idmap イベント(経路5)<br/>+ ITDR イベント(経路6・追加 I-O6)"| BITDR
  BKC --> BAUR
  IKCP --> IAUR
  BKC -->|"B-O4 監査ログ(IRSA+VPCE)"| S3A
  IKCP -->|"I-O3 監査ログ"| S3A
  BWH ==>|"B-O7(追加) Webhook 配信<br/>REQ-OUT-06"| NFWO --> CAPP
  CAN -.->|"AUD-1(追加) 外形監視<br/>インターネット経由で公開入口を検査"| CF

  %% ============ フロー(Outbound 公開) ============
  BKC ==>|"B-O1 フェデ Egress<br/>token/JWKS/userinfo 1000+ FQDN"| TGW
  TGW ==> NFWO ==> CIDP
  BKC -.->|"B-O8(追加) HIBP(管理者 PW)"| NFWO
  IKCP -.->|"I-O7(追加) HIBP(ローカル PW 主)"| NFWO
  NFWO -.-> HIBP
  BKC -.->|"B-O10(追加・条件付き) LDAPS :636<br/>G-LDAP ゲート未通過"| NFWO -.-> CAD
  BKC -->|"B-O9(追加) メール送信<br/>SES VPC Endpoint"| BVPCE
  IKCP -->|"I-O8(追加) メール送信"| IVPCE

  %% ============ 管理系 ============
  BKC -.->|"B-M Worker⇄CP"| BPL -.-> CP1
  IKCP -.->|"I-M Worker⇄CP"| IPL -.-> CP2
  BAUR -.->|"B-O6 Aurora Global <1min"| OSA
  IAUR -.->|"I-O5 Aurora Global"| OSA

  classDef pub fill:#ffebee,stroke:#c62828
  classDef other fill:#f3e5f5,stroke:#7b1fa2,stroke-dasharray: 5 5
  classDef rh fill:#ffe0b2,stroke:#e65100,stroke-dasharray: 3 3
  class OTHER other
  class RH rh
```

凡例: 太線 = 公開経路(入口/宛先がインターネット)/ 細線 = 私設(弊社 Acct 内・Acct 間)/ 点線 = 管理系・監視・条件付き。`(追加)` = 元表に無かった抜け候補(§A.3)。

## A.1.1 アプリ側(RP)の構成 2 パターンと認証基盤への接続(2026-07-28 追記)

§A.1 の `App Acct × N` の中身を詳細化する。**最重要の原則**を先に述べる:

> **認証基盤(Broker)は「OIDC の標準エンドポイント群」を提供するだけ**である — `authorize`(ログイン画面) / `token`(コード→トークン交換・リフレッシュ) / `JWKS`(署名検証用の公開鍵) / `logout` / `userinfo`。**各アプリは "RP(Relying Party)" を自分側に持つ**。RP は 2 つの部品からなる:
> 1. **OIDC クライアント**(ログインのリダイレクトとトークン交換を行う。SPA なら Public Client + PKCE、サーバーサイドなら Confidential Client = BFF)
> 2. **JWT 検証器**(API 呼び出しごとにトークンを検証する。**オフライン検証** = キャッシュした JWKS で署名・`iss`/`aud`/`exp`/`tenant_id` をローカル確認)
>
> **認証基盤はリクエスト毎の経路には立たない**。JWT 検証はアプリ側でオフライン完結し、認証基盤を叩くのは (a) ログイン時 (b) JWKS の定期更新(既定 1h キャッシュ、[ADR-012](../adr/012-vpc-lambda-authorizer-internal-jwks.md) の VPC 内経路)だけ。「毎回認証基盤に問い合わせる」構成ではない。

### パターン 1: CloudFront + WAF + S3 / API Gateway + Lambda(サーバーレス)

```mermaid
flowchart LR
  U["ブラウザ"]
  subgraph EDGE["他組織エッジ"]
    CFA["CloudFront + WAF<br/>(SPA配信 / API 前段)"]
  end
  subgraph AUTH["認証基盤 Broker(auth.basis)"]
    AZ["OIDC 標準エンドポイント<br/>authorize / token / JWKS / logout"]
  end
  subgraph APP["App Acct(パターン1: サーバーレス)"]
    S3["S3<br/>SPA 静的アセット"]
    APIGW["API Gateway"]
    LAUTH["Lambda Authorizer<br/><b>= JWT 検証器(オフライン)</b><br/>JWKS キャッシュ + iss/aud/exp/tenant_id 検証"]
    LBIZ["Lambda<br/>業務ロジック"]
    BFF["(任意) BFF Lambda<br/>Confidential Client<br/>= OIDC クライアント"]
  end
  U -->|"1 SPA 取得"| CFA --> S3
  U -.->|"2 ログイン(frontchannel)"| AZ
  BFF -.->|"3 code→token / refresh<br/>(VPC内・B-I2)"| AZ
  U -->|"4 API 呼出(Bearer JWT)"| CFA --> APIGW
  APIGW -->|"5 検証依頼<br/>(結果を API GW がキャッシュ)"| LAUTH
  LAUTH -.->|"JWKS 取得<br/>(VPC内・1h キャッシュ・ADR-012)"| AZ
  LAUTH -->|"offline 検証OK → allow"| APIGW --> LBIZ
```

- **SPA 直(BFF なし)の場合**: BFF Lambda を置かず、SPA(ブラウザ) が Public Client + PKCE でログイン〜`code→token` 交換を**ブラウザからインターネット経由(公開 token エンドポイント)**で行う。トークンは SPA メモリ保持。API 検証は同じく Lambda Authorizer。
- **BFF ありの場合(推奨)**: BFF Lambda が Confidential Client として `code→token` を**サーバーサイド(VPC 内経路 B-I2)**で行い、ブラウザにはアプリセッション Cookie のみ渡す(トークンをブラウザに置かない)。

### パターン 2: LB(ALB) + ECS(コンテナ)

```mermaid
flowchart LR
  U["ブラウザ"]
  subgraph EDGE["他組織エッジ"]
    CFB["CloudFront + WAF"]
  end
  subgraph AUTH["認証基盤 Broker(auth.basis)"]
    AZ2["OIDC 標準エンドポイント<br/>authorize / token / JWKS / logout"]
  end
  subgraph APP2["App Acct(パターン2: コンテナ)"]
    ALB["Internal ALB"]
    subgraph ECS["ECS タスク"]
      MW["OIDC ミドルウェア / oauth2-proxy(sidecar)<br/><b>= OIDC クライアント + JWT 検証器</b>"]
      BIZ["業務コンテナ"]
    end
  end
  U -->|"1 アクセス"| CFB --> ALB --> MW
  U -.->|"2 ログイン(frontchannel)"| AZ2
  MW -.->|"3 code→token / refresh<br/>(VPC内・B-I2)"| AZ2
  MW -.->|"JWKS 取得(VPC内・キャッシュ)"| AZ2
  MW -->|"offline 検証OK"| BIZ
```

- ECS アプリは **OIDC ミドルウェア**(言語フレームワークのライブラリ)or **oauth2-proxy 等の sidecar/リバースプロキシ**で「ログイン(OIDC クライアント)」と「毎リクエストの JWT 検証(オフライン)」の両方を担う。API Gateway / Lambda Authorizer は使わず、**検証はアプリ内(またはサイドカー)**で行う。
- 内部マイクロサービス間の伝播が必要なら Token Exchange(RFC 8693、[U5 §5.3](05-token-session-authz-design.md))を Broker に要求する経路が加わる。

### 「認証基盤に来るもの」= 役割・エンドポイント・頻度(両パターン共通)

| # | 何が来るか(呼ぶ側) | 役割 | 叩く先 | 経路 | 頻度 |
|---|---|---|---|---|---|
| 1 | **ブラウザ** | ユーザ認証(ログイン画面) | `authorize` / login | 公開(他組織エッジ、frontchannel) | ログイン時のみ |
| 2 | **BFF / ECS ミドルウェア**(= OIDC クライアント) | コード→トークン交換・リフレッシュ | `token` | **VPC 内(B-I2、ADR-012)**。SPA 直のみ公開経路 | ログイン / リフレッシュ時 |
| 3 | **Lambda Authorizer / ECS ミドルウェア**(= JWT 検証器) | 署名検証用の公開鍵取得 | `JWKS` | **VPC 内・1h キャッシュ(ADR-012)** | 定期(**リクエスト毎ではない**) |
| 4 | (任意) アプリ Backend | 組織コンテキスト / エンタイトルメント取得 | idm-api `/api/me/context`([U3 D3-16](03-identity-provisioning-design.md)) | VPC 内 | 認可判断時(短 TTL キャッシュ可) |

→ **JWT の検証そのもの(iss/aud/exp/tenant_id/署名)はアプリ側でオフライン完結**し、この表の 1〜4 のどれも「リクエスト毎に認証基盤を叩く」ものではない。認証基盤は per-request の経路に立たない(= スケール・可用性のボトルネックにならない)。

### 「Lambda Authorizer なのか認証アプリなのか」への回答

- **Lambda Authorizer は "アプリ側の JWT 検証器"** であって「認証基盤が各アプリのために動かす認証アプリ」ではない。**オフライン検証**(キャッシュ JWKS + クレーム検証)を行い、結果を API Gateway がキャッシュする。認証基盤へ毎回問い合わせているわけではない。
- **認証基盤側にアプリごとの "認証アプリ" は存在しない**。認証基盤は標準 OIDC エンドポイントを提供するだけで、RP(OIDC クライアント + 検証器)は各 App Acct 側の実装。検証器の実体がパターン 1 では Lambda Authorizer、パターン 2 では ECS の OIDC ミドルウェア / oauth2-proxy sidecar、という違いだけ。
- リアルタイム失効(退職者即遮断)が要る規制ケースのみ、Phase 3 で **API GW での Token Introspection**(オンライン検証)を選択肢に加える([U5 §5.2.4 Z-4](05-token-session-authz-design.md))。Phase 1 はオフライン検証 + 短 TTL が既定。
- RP 実装の必須事項(state+PKCE / Bearer 検証 / aud・tenant_id 検証 / リフレッシュ実装 / Back-Channel Logout 受信)は [U5 §5.6 RP 実装ガイド](05-token-session-authz-design.md)、認証実装漏れの検知は [Central Canary(ADR-059 / U9 §9.8)](09-operations-observability-design.md)。

## A.2 ROSA HCP クラスタ内部詳細(Broker/IdP-KC 共通、差分は §A.2.2)

**この粒度の図は本書が初出**(U6 §6.1.1 はアカウントレベル、doc/common/drawio は EKS 前提で未改版)。

```mermaid
flowchart TB
  subgraph RHACC["Red Hat サービスアカウント(顧客課金・VPC 外)"]
    API["API Server ×2 + oauth"]
    ETCD["etcd ×3(3AZ)"]
    OLMCP["OLM 本体 / Ingress Operator /<br/>ネットワーク系 Operator(CP 側で稼働)"]
    SRE["Red Hat SRE<br/>backplane 経由 JIT(短命・MFA・監査)"]
  end

  subgraph VPC["クラスタ VPC(Machine CIDR、例 10.64.0.0/16)— サブネット 4 層(U6 §6.2.1)"]
    subgraph STGW["① TGW Attachment Subnet /28 ×3AZ"]
      TGWA["TGW ENI"]
    end
    subgraph SALB["② ALB 専用 Subnet /26-27 ×3AZ"]
      ALB["Internal ALB(TLS 終端)"]
    end
    subgraph SWRK["③ Worker Subnet /24+ ×3AZ(ノード数ベース採番・install 後不変)"]
      subgraph MPI["Machine Pool: default(infra) — テイントなし・準静的<br/>c7g.large×2-3(O-11: xlarge/r7g/m7g 比較中)"]
        RTR["IngressController<br/>router pod(NLB 受け)"]
        MON["Prometheus(platform + UWM)<br/>※UWM は新規クラスタ既定無効<br/>→ Day-2 有効化必須(KC scrape 用)"]
        REG["image registry(デフォルト配備)"]
        OLM["OperatorHub 導入 Operator<br/>(RHBK Operator 等)<br/>※OLM 本体は RH 側 CP"]
        FAC["SCIM Facade"]
        AGG["Fluent Bit Aggregator(マスキング集中)<br/>+ OTel Collector"]
      end
      subgraph MPK["Machine Pool: keycloak — taint dedicated=keycloak:NoSchedule・動的<br/>c7g.xlarge min3 / max9(Broker) max18(IdP-KC)<br/>+ 2xlarge Pool(min0 事前定義・Blue/Green)"]
        KC["KC Pod ×3+<br/>(HPA → Pending → Cluster Autoscaler)"]
        FBD["Fluent Bit DaemonSet<br/>(taint toleration 付き)"]
      end
      PIW["pod identity webhook(組込)<br/>SA Token(1h) → STS AssumeRoleWithWebIdentity"]
    end
    subgraph SDB["④ Aurora Subnet /27-28 ×3AZ"]
      AUR[("Aurora PostgreSQL<br/>Writer のみ・プール 30/30/30")]
    end
    PLEP["PrivateLink Endpoint<br/>(Worker → CP 専用)"]
    VPCE["VPC Endpoint 群: S3 / ECR(ミラー) / STS /<br/>KMS / Logs / Secrets / SES(zero-egress)"]
  end

  ALB -->|"HTTP(自 VPC 内で平文化)"| RTR -->|"Route/Service"| KC
  KC -->|"jdbc-ping + SQL(SG 直結)"| AUR
  KC -.->|"kubelet/CSR/メトリクス"| PLEP -.-> API
  API -.-> ETCD
  KC -->|"IRSA 一時クレデンシャル"| PIW --> VPCE
  FBD -->|"ログ(生)"| AGG -->|"マスキング後"| VPCE
  FAC -->|"Admin API(クラスタ内 Service)"| KC
  MON -.->|"scrape"| KC
```

### A.2.1 クラスタ内 IP レンジ(OVN-Kubernetes)

| レンジ | 既定値(HCP) | 備考 |
|--------|------------|------|
| Machine CIDR | クラスタ VPC の CIDR | サブネット 4 層(U6 §6.2.1)。**install 後変更不可** |
| **Pod CIDR** | `10.128.0.0/14`(hostPrefix /23 → **ノードあたり 510 Pod IP**、公式文言) | OVN のオーバーレイ。**VPC 外に露出しない**が、Machine/Service CIDR・社内 NW・顧客 AD 系と重複禁止。**実効 Pod 密度は kubelet の maxPods 既定 250 で頭打ち**(/23 は余裕枠。HCP のテスト済み上限もノードあたり 250 Pod、2026-07-24 検証追記) |
| Service CIDR | `172.30.0.0/16` | クラスタ内仮想 IP。同上の重複禁止 |
| **OVN 内部予約レンジ(2026-07-24 検証追記)** | `100.64.0.0/16`(join)/ `100.88.0.0/16`(transit)/ `169.254.0.0/17`(masquerade、4.17+)/ **`172.20.0.1`(HCP 内部 K8s API 静的アドレス)** | これらも社内 NW・顧客 AD 系と**重複禁止**(公式 IMPORTANT)。**顧客側が CGN 帯 100.64.0.0/10 を使うケースは実在**するため、顧客オンボーディング時の CIDR 照会項目に含める |
| 採番の含意 | — | Worker サブネットは **Pod 数でなくノード数**で採番すれば足りる(Pod IP はオーバーレイ側)。Broker/IdP-KC 両クラスタで既定値をそのまま使っても衝突しない(オーバーレイは独立)が、**将来の submariner/直接ルーティング余地を残すなら両クラスタで Pod/Service CIDR をずらす**(未決 → U6 O 項目へ) |

### A.2.1b クラスタ内通信の原則(2026-07-24 公式検証で明文化)

- **⚠ private NLB のヘアピン制限**(公式トラブルシューティング): NLB のクライアント IP 保持により、**router pod と同一ノード上のワークロードから、その router を受ける private NLB への通信が失敗しうる**。infra Pool には router pod と SCIM Facade / Aggregator が同居するため、**同一クラスタ内のコンポーネント間通信は外部 FQDN(NLB 経由)を使わず、クラスタ内 Service 経由を原則とする**(§A.2 図の「FAC → KC はクラスタ内 Service」はこの原則の適用)。
- ファクトチェック実施(2026-07-24、公式一次資料 16 項目): ❌ 1 件(OLM 配置 → 修正済み)、⚠ 5 件(レプリカ≥2 条件 / SA Token 表現 / 追加 IC の顧客管理扱い / ローリング既定値 maxSurge=1・maxUnavailable=0 と drain 猶予 / UWM 既定無効)— いずれも本書と U6 v1.5 に反映済み。主要出典は U6 v1.5 改訂履歴参照。

### A.2.2 Broker / IdP-KC の内部差分

| 観点 | Broker #1 | IdP-KC #2 |
|------|-----------|-----------|
| KC Pool max | 9(署名系 CPU) | 18(Argon2id 支配、フェデ比率感度) |
| 外向き(インターネット) | **重い**: B-O1 フェデ 1000+ FQDN + B-O7 Webhook + B-O8 HIBP | **HIBP(I-O7)と SES のみ**(外部 IdP へフェデしない) |
| 追加コンポーネント | idm-api #1(管理画面 Backend)/ ITDR / Webhook Dispatcher | idm-api #2(専用 API 層)/ 同居アプリ |
| PrivateLink | IdP-KC への **送信側**(Endpoint) | Ingress NLB を **Endpoint Service 化して着信のみ**(逆流不能) |
| DB | Broker DB + **idmap 別 DB** | IdP-KC DB(**PW ハッシュ**) |

### A.2.3 テイント配置・スケール連鎖・クラスタ内通信(2026-07-28 追加)

HCP には専用 Infra Node が無く infra 系が Worker に同居する(U6 §6.2.1)。**2 Pool 役割分離**(U6 §6.2.2 D-U6-04)の配置・スケール・通信を 3 図で示す。

#### 図 A.2.3-1: テイント/トレラントで「何がどこに載るか」

```mermaid
flowchart TB
    subgraph POD["生成される Pod"]
        KCPOD["KC Pod<br/>toleration: dedicated=keycloak<br/>nodeSelector: workload=keycloak<br/>(中: keycloak コンテナ = SPI 焼込 image)"]
        INFPOD["infra Pod(router / Prometheus / registry /<br/>RHBK Operator / SCIM Facade / Fluent Bit)<br/>toleration: なし"]
    end
    SCHED{"kube-scheduler<br/>テイント許容? + ラベル一致?"}
    KCPOD --> SCHED
    INFPOD --> SCHED
    subgraph KCPOOL["keycloak Pool ノード(EC2)<br/>taint=dedicated=keycloak:NoSchedule / label=workload=keycloak"]
        K1["KC Pod のみ"]:::kc
    end
    subgraph INFRAPOOL["default(infra) Pool ノード(EC2)<br/>テイントなし / label=default(ROSA 必須の無テイント Pool・レプリカ≥2)"]
        I1["router / Prometheus / registry /<br/>Operator / SCIM Facade / Fluent Bit"]:::inf
    end
    SCHED -->|"テイント許容 + label 一致 → 許可"| KCPOOL
    SCHED -->|"KC のテイントを許容せず → 弾かれ default へ"| INFRAPOOL
    classDef kc fill:#e3f2fd,stroke:#1565c0
    classDef inf fill:#fff8e1,stroke:#f57f17
```

**要点**: テイント=締め出し。KC Pool の `NoSchedule` テイントを許容する KC Pod だけが入り、infra Pod は許容しないため**自動的に default Pool へ落ちる**。分離の主役はテイント。

#### 図 A.2.3-2: スケールの連鎖(HPA → Pending → Cluster Autoscaler → EC2)

```mermaid
sequenceDiagram
    autonumber
    participant Load as ログイン負荷
    participant HPA
    participant Dep as KC(StatefulSet/CR)
    participant Sched as kube-scheduler
    participant CA as Cluster Autoscaler
    participant NP as KC MachinePool
    participant ASG as AWS ASG
    participant Node as 新 Worker(EC2)

    Load->>HPA: CPU 60%超 / 予兆(login_success_password_rate>8/node・3分)
    HPA->>Dep: replicas 3→5
    Dep->>Sched: 新 KC Pod ×2 (toleration+nodeSelector=keycloak)
    Sched-->>Dep: KC Pool に空き無 → Pod=Pending(Unschedulable)
    CA->>Sched: Pending Pod 検知(要件=label:keycloak)
    CA->>NP: KC Pool の replicas を +N(★この Pool だけ)
    NP->>ASG: EC2 起動(RHCOS AMI + taint/label 自動付与)
    ASG->>Node: 新 EC2 起動 → Node 参加(12-15分)
    Node-->>Sched: label=keycloak + taint=NoSchedule で登録
    Sched->>Node: Pending KC Pod を配置
    Note over CA,Node: infra Pool は要件不一致で触られない<br/>= KC バーストが infra を巻き込まない
```

**要点**: Pod スケール(HPA)と Node スケール(Cluster Autoscaler)は別コントローラ。**CA は「Pending Pod の要件に一致する Pool」だけを増設**するため、KC 急増は KC Pool のみで吸収。縮小は cordon → drain(PDB `maxUnavailable=1` 尊重) → EC2 終了。ローリング更新は既定 `maxSurge=1/maxUnavailable=0`(§A.2.1b)。

#### 図 A.2.3-3: クラスタ内通信(誰がどこと話すか)

```mermaid
flowchart TB
    NLB["IngressController NLB(Private)"]
    subgraph INFRA["default(infra) Pool ノード"]
        RT["router pod(haproxy)"]
        PR["Prometheus(UWM・要 Day-2 有効化)"]
        SF["SCIM Facade"]
        FB["Fluent Bit Aggregator"]
    end
    subgraph KCP["keycloak Pool ノード"]
        KCa["KC Pod A"]
        KCb["KC Pod B"]
    end
    AUR[("Aurora Writer")]
    CP["Red Hat HCP(Control Plane)"]
    S3[("監査 S3")]

    NLB -->|"HTTPS(L7 route)"| RT
    RT ==>|"Pod 網越し(クロスノード/プール)"| KCa
    RT ==> KCb
    PR -.->|"/metrics scrape(クロスプール)"| KCa
    SF -.->|"Admin API=内部 Service(ClusterIP)<br/>/admin 403 を通らない(§A.2.1b 原則)"| KCa
    KCa <-->|"Infinispan 分散cache + jdbc-ping(DB経由発見)"| KCb
    KCa -->|"SG 直 JDBC(Writerのみ・pool initial=min=max)"| AUR
    KCb --> AUR
    FB -.->|"ログ集約(IRSA)"| S3
    KCa -.->|"PrivateLink Worker→CP(組込)"| CP
    classDef inf fill:#fff8e1,stroke:#f57f17
    classDef kc fill:#e3f2fd,stroke:#1565c0
    class RT,PR,SF,FB inf
    class KCa,KCb kc
```

**要点**:
- ユーザ経路: NLB → router pod(infra) → KC Pod(KC Pool)。Pool をまたぐが同一 AZ 配置で AZ 内に閉じる。
- SCIM Facade → KC Admin API は**クラスタ内 Service(ClusterIP)で内部到達** = 外部 ALB の `/admin 403` を通らない(in-cluster を選ぶ理由。§A.2.1b の private NLB ヘアピン制限回避も同根)。
- 監視: Prometheus(infra)が KC Pod `/metrics` をクロスプール scrape(UWM Day-2 有効化前提)。
- KC↔KC: Infinispan + jdbc-ping(DB 経由発見)。KC→Aurora: SG 直 JDBC。Worker→CP: PrivateLink(HCP 組込)。

**コンテナ粒度**: KC Pod=`keycloak` 1 コンテナ(Custom SPI は image 焼込のため追加なし)。router=haproxy / Prometheus / SCIM Facade / Fluent Bit は各 1 コンテナ。これらを「どの Pool の EC2 に載せるか」をテイントで振り分ける。

## A.3 抜けチェック結果(元表に無かったフロー 8 系統)

元表(B-I1〜B-O6 / I-I1〜I-O5)は 10 冊と概ね整合。以下が**追加候補**(図には `(追加)` で反映済み):

| # | フロー | 内容 | 根拠 |
|---|--------|------|------|
| B-I6 | **管理画面 SPA / launchpad / idm-api 公開入口** | テナント管理者 → CF(admin. REQ-IN-03)→ idm-api #1。launchpad SPA 配信(REQ-IN-11)+ `GET /api/me/apps`(REQ-IN-12)+ **Sorry SPA(/sorry)** も同系 | U10 D-U10-08、U4 D-U4-06/07 |
| B-O7 | **Webhook 配信** | Dispatcher(SQS+λ)→ 顧客アプリ endpoint。**REQ-OUT-06(送信元が KC Pod でない別枠)** | U10 D-U10-11 |
| B-O8 / I-O7 | **HIBP Egress** | `api.pwnedpasswords.com`(k-Anonymity・fail-open)。**IdP-KC が主利用者** — 「IdP-KC は外向きほぼ無し」の重要な例外(REQ-OUT-01 の送信元スコープ拡張要求済み) | U7 §7.2.2 |
| B-O9 / I-O8 | **メール送信(SES)** | 招待・PW リセット・MFA 登録・侵害通知テンプレート(U4 §4.3)。SES VPC Endpoint 経由なら zero-egress 維持。**SES サンドボックス解除・SPF/DKIM(Route 53)が未設計 → U6/U9 未決に追加すべき** | U4/U7 |
| I-O6 | **ITDR イベント(経路 6)** | IdP-KC → Broker EventBridge PutEvents。元表 B-I4 は idmap(経路 5)のみで **ITDR 用の経路 6 が漏れ** | U6 D-U6-02 6 経路、U7 D-U7-04 |
| B-O10 | **LDAPS(条件付き)** | 顧客 AD へ TCP:636(REQ-OUT 付帯 3 ルール)。**G-LDAP(B-SCIM-13)ゲート未通過のため点線** | ADR-025 §H、ADR-039 §F.1.A |
| AUD-1 | **Central Canary 外形監視** | 監査 Acct → インターネット経由で公開入口(auth. 等)を合成ログイン検査 + `canary-central-readonly` Client | U9 D-U9-16 |
| DNS 系 | **Route 53 の 3 役割の明示** | ① Public Zone: CNAME → 他組織 CF(弊社統制)② PHZ: Acct 内内部名 ③ **Resolver: NFW の FQDN 評価と同一解決系(REQ-OUT-04)** | U6 §6.7.3 |

補足(元表への軽微な指摘):
- **ServiceNow(CL-SN-01)**: サーバ間通信は不要(SAML POST binding はブラウザ経由)のため B-I1 の変種として扱えば足りる。別フロー不要と判断
- **B-O5/I-O4 の「Zero-egress」表記**: O-10 の正式クローズ前のため「案 B 前提」と注記(§A.0)

## A.4 未決事項(本書発)

| # | 内容 | 引き渡し先 |
|---|------|-----------|
| A6a-1 | SES 送信設計(サンドボックス解除 / SPF/DKIM / 送信ドメイン `no-reply@` の Zone 登録) | U6/U9 |
| A6a-2 | 両クラスタの Pod/Service CIDR をずらすか(既定値共用で衝突はしないが将来の直接ルーティング余地) | U6 O 項目 |
| A6a-3 | Canary の送信元(監査 Acct)からの外形監視経路が他組織 WAF の Bot 対策(REQ-IN-01)に誤検知されない除外合意 | U9/REQ 追補 |
| A6a-4 | drawio 清書(本書 mermaid → AWS アイコン版、doc/common/drawio の EKS 旧図の置換) | 別タスク |

## A.5 IP アドレス割当計画(第 1 案、2026-07-24)

> **位置づけ**: 社内 NW・顧客 AD・他組織(NW 監査/NW Acct)の CIDR 一覧が未入手のため**仮案**。照会(A6a-5)で衝突が出た場合は本節のみ差し替える。**CIDR は ROSA install 後変更不可のため、Phase 1 構築前に本表の凍結が必須**。

### A.5.1 採番の全体方針

| 空間 | 帯 | 用途 |
|------|-----|------|
| **実ネットワーク(VPC)** | `10.64.0.0/13` = 東京 / `10.72.0.0/13` = 大阪 | 弊社の全 VPC をここから採番(リージョンをビット境界で分離、集約経路が書きやすい) |
| **アプリ用ガイド** | `10.68.0.0/14` 帯から /21 ずつ | App Acct × N への払い出し推奨帯(各アプリチーム管理だが、TGW 経路重複回避のため中央台帳で採番) |
| **クラスタオーバーレイ(Pod)** | `10.128.0.0/9` を**台帳上「オーバーレイ専用」として一括予約** | 各クラスタの Pod CIDR(/14 × 4)+ 将来クラスタ分。実ネットワークには一切使わない |
| **Service CIDR** | `172.27.0.0 〜 172.30.0.0` の /16 × 4 | クラスタごとにずらす(下表)。**172.31.0.0/16 は AWS デフォルト VPC、172.17.0.0/16 は Docker 既定ブリッジのため回避** |
| **禁止(予約)** | `100.64.0.0/16` / `100.88.0.0/16` / `169.254.0.0/17` / `172.20.0.1` | OVN 内部 + HCP 予約(§A.2.1)。全クラスタ共通・変更しない |

### A.5.2 アカウント別 VPC 割当表

| Acct | リージョン | VPC 名(論理) | CIDR | 中身 | 備考 |
|------|-----------|--------------|------|------|------|
| Broker | 東京 | broker-tyo | **10.64.0.0/21** | ROSA #1 + Internal ALB + Aurora(Broker/idmap) + Lambda 統合 | Machine CIDR = 本 CIDR |
| IdP-KC | 東京 | idpkc-tyo | **10.64.8.0/21** | ROSA #2 + Internal ALB + Aurora(IdP-KC) + **同居アプリ用サブネット** | 同居アプリの実行形態(ROSA 同居 or 別コンピュート)未確定 → 別コンピュートなら /23 をアプリ層に割く(A6a-6) |
| 監査 | 東京 | audit-tyo(任意) | 10.64.16.0/24 | Canary を VPC 内実行する場合のみ(外形監視は VPC 不要のため通常は未作成) | 任意 |
| (予備) | 東京 | — | 10.64.32.0/19 ほか | IdP-KC シャーディング時の第 3 クラスタ等(P-16 拡張パス) | 台帳予約のみ |
| Broker | 大阪 | broker-osa | **10.72.0.0/21** | 東京と対称(パイロットライト。**Failover 後の東京同等スケールを収容できる同サイズで事前確保**) | — |
| IdP-KC | 大阪 | idpkc-osa | **10.72.8.0/21** | 同上 | — |
| App × N | 東京 | (各チーム) | 10.68.0.0/14 から /21 ずつ | アプリ本体 + Internal ALB | 中央台帳で採番のみ管理 |
| 他組織(NW 監査/NW) | — | — | **未入手 → REQ で CIDR 一覧交換** | Inbound エッジ / Egress VPC / TGW | 弊社の使用帯 + 禁止帯を先に提示する(A6a-5) |

### A.5.3 クラスタ VPC 内サブネット割付(例: broker-tyo 10.64.0.0/21。他 3 VPC は同形)

| 層 | サブネット(AZ-a / AZ-c / AZ-d) | サイズ | 収容物 | サイジング根拠 |
|----|-------------------------------|--------|--------|----------------|
| ① Worker | 10.64.0.0/24 / 10.64.1.0/24 / 10.64.2.0/24 | /24 × 3(251 IP/AZ) | KC Pool + infra Pool + 2xlarge Pool のノード(全 Pool 同居可)、Fluent Bit 等はノード IP 消費なし | **ノード数ベース**(OVN、§A.2.1)。max 9〜18 ノード + surge + 将来増でも余裕 |
| ② ALB | 10.64.3.0/26 / .64/26 / .128/26 | /26 × 3 | Internal ALB(スケール時の ENI 増加を許容) | ALB は AZ あたり最低 /27 推奨 → /26 で余裕 |
| ③ Lambda/統合 | 10.64.4.0/26 / .64/26 / .128/26 | /26 × 3 | **Webhook Dispatcher λ / idmap 更新ハンドラ λ / (idm-api を λ 実装にする場合)** — Aurora 接続と TGW 経由 Egress のため VPC アタッチ必須 | λ の ENI 消費(同時実行数に比例) |
| ④ Aurora | 10.64.5.0/27 / .32/27 / .64/27 | /27 × 3 | Aurora Writer/Reader + (Broker のみ)idmap DB | DB Subnet Group |
| ⑤ VPC Endpoint | 10.64.5.96/27 / .128/27 / .160/27 | /27 × 3 | S3/ECR/STS/KMS/Logs/Secrets/SES + **HCP PrivateLink EP** | Interface EP は ENI 1 個/AZ/サービス |
| ⑥ TGW Attachment | 10.64.5.192/28 / .208/28 / .224/28 | /28 × 3 | TGW ENI 専用(推奨プラクティス: 専用最小サブネット) | /28 固定 |
| (予備) | 10.64.6.0/23 | /23 | 将来層(例: 同居アプリを ECS にする場合等) | — |

### A.5.4 ROSA クラスタ内部レンジ割当表(4 クラスタ)

| クラスタ | Machine CIDR | Pod CIDR(hostPrefix /23) | Service CIDR | OVN 予約(共通・固定) |
|----------|--------------|--------------------------|--------------|----------------------|
| broker-tyo | 10.64.0.0/21 | **10.128.0.0/14** | **172.30.0.0/16** | 100.64.0.0/16(join)/ 100.88.0.0/16(transit)/ 169.254.0.0/17(masq)/ 172.20.0.1(内部 API) |
| idpkc-tyo | 10.64.8.0/21 | **10.132.0.0/14** | **172.29.0.0/16** | 同上 |
| broker-osa | 10.72.0.0/21 | **10.136.0.0/14** | **172.28.0.0/16** | 同上 |
| idpkc-osa | 10.72.8.0/21 | **10.140.0.0/14** | **172.27.0.0/16** | 同上 |

- **Pod/Service をクラスタごとにずらす理由**(= A6a-2 の推奨解): オーバーレイは独立なので共用でも動くが、①将来の submariner/直接ルーティングの余地 ②ログ・トラブルシュート時に IP を見ただけでクラスタを特定できる運用利点 ③追加コストゼロ(採番だけ)。**本表で A6a-2 は「ずらす」で解消提案**
- Pod /14 = ノード 510 台分の /23 を収容(max 18+α ノードに対し大幅余裕だが、縮めるメリットがないため既定幅を維持)
- 実効 Pod 密度は maxPods 250/ノード で頭打ち(§A.2.1)

### A.5.5 禁止・照会リスト(CIDR 台帳の「使用不可」ページ)

| 帯 | 理由 | 状態 |
|----|------|------|
| 10.128.0.0/9 | クラスタオーバーレイ専用(Pod CIDR × 将来分) | 弊社予約 |
| 172.27.0.0/16 〜 172.30.0.0/16 | Service CIDR × 4 | 弊社予約 |
| 172.31.0.0/16 | AWS デフォルト VPC 帯 | 回避 |
| 172.17.0.0/16 | Docker 既定ブリッジ(開発環境との事故防止) | 回避 |
| 100.64.0.0/16 / 100.88.0.0/16 / 169.254.0.0/17 / 172.20.0.1 | OVN join/transit/masquerade + HCP 内部 API(§A.2.1) | 予約(変更しない) |
| 社内 NW / 顧客 AD・IdP 側レンジ | **未入手** — 特に CGN 帯 100.64.0.0/10 の使用有無 | **照会中(A6a-5)**。顧客はオンボーディング時照会(U9) |
| 他組織 VPC / TGW 帯 | **未入手** | REQ で交換(A6a-5) |

### A.5.6 本節の未決

| # | 内容 | 引き渡し先 |
|---|------|-----------|
| A6a-5 | 社内 NW・他組織(NW 監査/NW Acct)の CIDR 一覧の入手と衝突確認 → 本表の凍結。弊社帯(10.64/13・10.72/13・10.68/14・予約帯)を先方へ先に提示 | 要求仕様書 v1 付属 / 社内 NW チーム |
| A6a-6 | IdP-KC 同居アプリの実行形態(ROSA 同居 namespace or 別コンピュート)→ ③/予備層の使い方確定 | U3/アプリチーム |
| A6a-2 | (更新)Pod/Service ずらしは §A.5.4 の 4 クラスタ案で「ずらす」を推奨解として提示 → U6 承認で解消 | U6 |

## 改訂履歴

- 2026-07-24: 初版。ユーザー提供のフロー表(B-*/I-* 系)を全量反映 + 抜け 8 系統を追加 + ROSA 内部詳細図(初出)+ OVN IP レンジ表。
- 2026-07-28 (v1.3): **§A.1.1 新設 — アプリ側(RP)の構成 2 パターン**(パターン1 CloudFront+WAF+S3 / API GW + Lambda Authorizer、パターン2 ALB+ECS + OIDC ミドルウェア/oauth2-proxy)+ 「認証基盤に来るもの」の役割・頻度表 + 「Lambda Authorizer = アプリ側のオフライン検証器であって認証基盤の per-request 経路ではない」を明確化。
- 2026-07-24 (v1.2): **§A.5 IP アドレス割当計画(第 1 案)新設** — 東京 10.64/13・大阪 10.72/13・アプリ 10.68/14 の採番方針、アカウント別 VPC 表(/21 × 4 + 予備)、サブネット 6 層割付(Worker /24・ALB /26・**Lambda 統合 /26(Webhook/idmap λ の VPC アタッチ用に新設)**・Aurora /27・VPCE /27・TGW /28)、4 クラスタの Pod/Service CIDR ずらし案(A6a-2 の推奨解)、禁止・照会リスト。新未決 A6a-5(CIDR 照会・凍結)/ A6a-6(同居アプリ実行形態)。
- 2026-07-24 (v1.1): **公式ドキュメント・ファクトチェック反映**(16 項目検証、❌1 + ⚠5)— OLM 本体は RH 側 CP(Worker は導入 Operator のみ)/ SRE=backplane JIT(break-glass は顧客側機能の名称)/ UWM 新規クラスタ既定無効 → Day-2 有効化必須 / maxPods 250 追記 / OVN 内部予約レンジ(100.64/16・100.88/16・169.254/17・172.20.0.1)追加 / **NLB ヘアピン制限とクラスタ内 Service 原則の明文化(§A.2.1b)**。
