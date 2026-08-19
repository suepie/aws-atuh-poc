# ブランドユニット 2-VPC 分離トポロジ（B案）— 構成図用 詳細

- **日付**: 2026-08-18
- **種別**: research note（構成図の一次資料。U6 §6.2 / 06a §A.6 / ADR-062・063 の実装詳細）
- **決定**: 単一 VPC（A案・アンチパターン）→ **2 VPC 分離（B案）を採用**（[single-vpc-consolidation-risk](single-vpc-consolidation-risk-2026-08-18.md) の 8 リスク評価に基づく）。ブランドユニット（IdP-KC アカウント）内を **VPC-K（Keycloak/identity）** と **VPC-M（管理/authz）** に分割。
- **前提**: [ADR-062](../../adr/062-idm-api-execution-form-lambda.md)（idm-api=Lambda・1 本）/ [ADR-063](../../adr/063-brand-unit-architecture.md)（ブランド主役・A+C）/ [ADR-064](../../adr/064-deprovisioning-propagation-outbox.md)（削除 outbox）/ [D-U6-06](../06-infra-network-design.md)（PrivateLink 単方向）/ [rosa-vpc-ip-conservation](rosa-vpc-ip-conservation-2026-08-17.md)（ENI・CIDR）
- ⚠ P-17（Broker/IdP-KC の 2 クラスタ構成）は別スレッドで再検討中。本ノートは「ブランドユニット内の VPC セグメンテーション」を扱い、上位のアカウント/クラスタ数が確定したら CIDR 実値のみ差し替える。

---

## 1. 2 VPC の役割（IdP-KC = ブランドユニット アカウント内）

| VPC | 役割 | 機微度 | ROSA 管理 | TGW attach | CIDR（例） |
|---|---|---|---|---|---|
| **VPC-K（Keycloak/identity）** | ROSA クラスタ（Keycloak）＋ **identity Aurora（PW ハッシュ）** ＋ Admin/OIDC 内部 NLB | **P0・最高機微** | ○ | **要**（idp. ログイン inbound が TGW 経由） | `10.64.0.0/23`（Transit-routable） |
| **VPC-M（管理/authz）** | **idm-api Lambda（1 本）**＋非同期の糊 Lambda ＋ **authz Aurora** ＋ Interface Endpoint 群 | P1・管理面 | × | **不要**（api. は API GW→Lambda invoke で VPC 非経由） | `100.65.0.0/25`（**CGNAT 可＝TGW 非広告で隠蔽**） |

> **要点**: VPC-M は **inbound を持たない**（api. は CloudFront→API GW→Lambda ネイティブ invoke で VPC ルーティング外）。Lambda ENI は **outbound 専用**（authz Aurora / Admin API PrivateLink / AWS サービス Endpoint）。→ **TGW 非 attach でよく、CIDR を CGNAT にして Transit から完全に隠せる**（[IP 節約ノート](rosa-vpc-ip-conservation-2026-08-17.md)の"隠蔽アイランド"）。

---

## 2. サブネット × リソース（AZ ごと ×3）

### VPC-K（`10.64.0.0/23`）
| サブネット | サイズ/AZ | リソース | 備考 |
|---|---|---|---|
| **TGW attach** | /28 | TGW ENI | idp. ログイン inbound の入口 |
| **ALB** | /27 | Internal ALB（L7・`/admin` 403） | ログイン前段。TGW から到達 |
| **Node** | /26（or CGNAT secondary） | ROSA worker（KC Pod・IngressController）／ **Login/OIDC NLB**（internal）／ **Admin NLB**（internal, `kc-admin`） | Pod は OVN オーバーレイ（VPC IP 非消費） |
| **Aurora** | /28 | **identity Aurora**（PW ハッシュ） | KC Pod のみ到達 |
| **Endpoint** | /27 | ROSA egress 用 IF/Gateway Endpoint（ECR/STS/S3/Logs/KMS/HIBP/SES） | zero-egress（O-10） |

### VPC-M（`100.65.0.0/25`）
| サブネット | サイズ/AZ | リソース | 備考 |
|---|---|---|---|
| **Lambda** | /27 | **idm-api Lambda ENI**／非同期の糊 Lambda ENI（outbox リレー・射影フィード・Webhook Dispatcher・idmap/projection ハンドラ） | Hyperplane ENI（1/AZ/SG） |
| **Endpoint** | /27 | **IF Endpoint①（→VPC-K Admin API EPS）**／AWS サービス IF・Gateway Endpoint（Secrets/KMS/Logs/STS/EventBridge/SQS/S3） | Admin API＋zero-egress |
| **Aurora** | /28 | **authz Aurora**（authz/idmap/projection） | idm-api Lambda のみ到達 |

---

## 3. 接続一覧（フロー ID × 経路 × プロトコル × PrivateLink 有無）

### Inbound
| ID | 経路 | プロトコル | PL |
|---|---|---|---|
| IN-1 | ブラウザ →(他組織)CF+WAF → **NFW → TGW** → VPC-K[TGW] → VPC-K[ALB: `/admin`403] → VPC-K[Node: Login/OIDC NLB] → KC Pod（idp. ログイン UI） | HTTPS | — |
| IN-2 | ブラウザ → CF+WAF → **API GW（JWT L1+throttle）→ Lambda ネイティブ invoke**（idm-api、VPC-M） | HTTPS | — |
| IN-3 | ブラウザ → CF+WAF → **OAC → S3**（admin./launchpad. SPA） | HTTPS | — |

### idm-api（VPC-M）outbound
| ID | 経路 | プロトコル | PL |
|---|---|---|---|
| M-1 | idm-api Lambda[VPC-M Lambda] → **authz Aurora[VPC-M Aurora]**（同一 VPC・SG 直） | 5432 | — |
| M-2 | idm-api Lambda[VPC-M] →(Route53 PHZ 解決)→ **IF Endpoint①[VPC-M Endpoint]** → **PrivateLink（EPS-Admin）** → **Admin NLB[VPC-K Node, `scheme=internal`]** → IngressController → **KC Admin API Pod**（CRUD） | 443（TLS 終端=IngressController／アプリ層認証=管理クライアント資格） | **○** |
| M-3 | idm-api/糊 Lambda[VPC-M] → **AWS IF/Gateway Endpoint[VPC-M Endpoint]** → Secrets Manager（資格）/ KMS / Logs / STS | 443 | （AWS PL） |
| M-4 | outbox リレー Lambda[VPC-M] → authz Aurora outbox[VPC-M] → **EventBridge IF Endpoint[VPC-M]** → EventBridge bus →（越境）Broker | 443 | （AWS PL） |

### 越境（Broker アカウント ↔ VPC-K / VPC-M）
| ID | 経路 | 種別 | PL |
|---|---|---|---|
| X-1 | **フェデ backchannel**：Broker KC Pod[Broker VPC] →(PHZ)→ IF Endpoint[Broker VPC] → **PrivateLink（EPS-OIDC）** → **Login/OIDC NLB[VPC-K Node]** → KC OIDC（token/jwks/userinfo、`idpkc-oidc01`、[D-U6-06](../06-infra-network-design.md)） | Broker→IdP-KC 単方向 | **○** |
| X-2 | **初回 sub 通知**：Broker → EventBridge →（越境）→ ブランドハンドラ Lambda[VPC-M] → authz Aurora（authz スタブ生成） | EventBridge | — |
| X-3 | **削除伝播**（=M-4 の続き）：idm-api → outbox → EventBridge →（越境）→ **Broker shadow 制御 Lambda** → Broker Admin NLB → Broker KC（shadow `enabled=false`、[ADR-064](../../adr/064-deprovisioning-propagation-outbox.md)） | EventBridge | — |

### VPC-K（ROSA）egress
| ID | 経路 | 備考 |
|---|---|---|
| K-1 | KC Pod → identity Aurora[VPC-K Aurora]（SG 直） | 5432・intra-VPC |
| K-2 | worker → AWS（ECR/STS/S3/Logs/KMS）＝ VPC-K Endpoint | zero-egress |
| K-3 | worker → registry.redhat.io/quay/OLM ＝ **ECR ミラー（zero_egress）** or NAT→NFW | O-10 |
| K-4 | KC → HIBP / SES | NFW egress |

---

## 4. Security Group（誰から誰へ・最小権限）

### VPC-K
| SG | ingress | egress |
|---|---|---|
| `sg-kc-pod` | Login/OIDC NLB・Admin NLB から | → `sg-identity-aurora`(5432) / VPC-K Endpoint(443) / 外部(K-3/4) |
| **`sg-identity-aurora`** | **5432 ← `sg-kc-pod` のみ** | — |
| `sg-login-oidc-nlb` | ALB(ログイン)／EPS-OIDC エンドポイント(X-1) から | → `sg-kc-pod` |
| `sg-admin-nlb` | **443 ← EPS-Admin エンドポイント(M-2) のみ** | → `sg-kc-pod`(IngressController) |
| `sg-alb` | TGW/エッジから | → `sg-login-oidc-nlb` |

### VPC-M
| SG | ingress | egress |
|---|---|---|
| `sg-idmapi-lambda` | （invoke は Lambda サービス経由・VPC ingress なし） | → `sg-authz-aurora`(5432) / `sg-adminapi-endpoint`(443) / `sg-aws-endpoint`(443) |
| **`sg-authz-aurora`** | **5432 ← `sg-idmapi-lambda` のみ** | — |
| `sg-adminapi-endpoint`（IF Endpoint①） | 443 ← `sg-idmapi-lambda` | （PrivateLink） |
| `sg-aws-endpoint` | 443 ← `sg-idmapi-lambda` | （PrivateLink） |

> **キー不変条件**: **idm-api Lambda（VPC-M）は identity Aurora（VPC-K）へのルートも SG 許可も持たない**。Keycloak へは **EPS-Admin（Admin API）経由のみ**で、Admin API は PW ハッシュを返さない。→ **管理面が全侵害されても PW ハッシュに到達不能・クラスタ網スキャン不能・VPC-K からの逆流不能**（PrivateLink 単方向）。

---

## 5. PrivateLink Endpoint Service 一覧

| EPS | provider（NLB） | consumer | 許可 principal | 用途 |
|---|---|---|---|---|
| **EPS-OIDC** | VPC-K Login/OIDC NLB（internal） | Broker VPC の IF Endpoint | **Broker アカウント**（`acceptance_required=true`） | フェデ backchannel（X-1、Broker→IdP-KC OIDC） |
| **EPS-Admin** | VPC-K Admin NLB `kc-admin`（internal） | VPC-M の IF Endpoint① | **同一アカウント（IdP-KC/brand）** | idm-api → Keycloak Admin API（M-2、CRUD） |

- **provider 側 NLB を 2 本に分離**（OIDC と Admin を別 EPS/別 NLB）＝ Admin API を OIDC/ログイン面から隔離（最小到達）。
- PrivateLink は **consumer→provider の接続開始のみ単方向**（provider は逆に接続を張れない）。DNS は各 consumer VPC の **Route 53 Private Hosted Zone** で `idp-admin.internal…` / `idp-oidc.internal…` を IF Endpoint に Alias。

---

## 6. 構成図（mermaid）

```mermaid
flowchart LR
  subgraph EDGE["他組織エッジ（P-18）"]
    CF["CloudFront + WAF"]
    NFW["Network Firewall"]
    APIGW["API Gateway<br/>(JWT L1)"]
    S3["S3(OAC)<br/>SPA"]
  end
  TGW(["Transit GW"])

  subgraph BR["Broker アカウント"]
    BKC["Broker KC Pod"]
    SHC["shadow 制御 Lambda"]
    BEP["IF Endpoint<br/>(→EPS-OIDC)"]
  end

  subgraph BRAND["IdP-KC = ブランドユニット アカウント"]
    subgraph VPCK["VPC-K (Keycloak/identity) 10.64.0.0/23"]
      ALB["Internal ALB<br/>/admin403 [ALB subnet]"]
      LNLB["Login/OIDC NLB<br/>[Node subnet]"]
      ANLB["Admin NLB kc-admin<br/>[Node subnet]"]
      KCP["KC Pod<br/>[Node subnet]"]
      IAUR[("identity Aurora<br/>PWハッシュ [Aurora subnet]")]
    end
    subgraph VPCM["VPC-M (管理/authz) 100.65.0.0/25 (CGNAT・TGW非attach)"]
      LMB["idm-api Lambda<br/>+糊 [Lambda subnet]"]
      EP1["IF Endpoint①<br/>→EPS-Admin [Endpoint subnet]"]
      ZAUR[("authz Aurora<br/>authz/idmap/projection [Aurora subnet]")]
    end
  end

  CF -->|IN-1 idp.| NFW --> TGW --> ALB --> LNLB --> KCP
  CF -->|IN-2 api.| APIGW -->|invoke| LMB
  CF -->|IN-3 admin.| S3
  KCP -->|K-1 5432| IAUR
  LMB -->|M-1 5432 SG直| ZAUR
  LMB -->|M-2| EP1 -.->|PrivateLink EPS-Admin| ANLB --> KCP
  BKC --> BEP -.->|PrivateLink EPS-OIDC 単方向| LNLB
  LMB -.->|M-4 EventBridge 越境| SHC --> BKC
```

---

## 7. 現行（A案・単一 VPC）からの差分

| 項目 | A案（現行 06 ベースライン） | B案（本ノート・採用） |
|---|---|---|
| idm-api Lambda ENI | クラスタ VPC の層③（同居） | **VPC-M（別 VPC）** |
| authz Aurora | クラスタ VPC 内（A+C 内部分離） | **VPC-M** |
| identity Aurora | クラスタ VPC 内 | **VPC-K（KC Pod のみ到達）** |
| idm-api → Admin API | intra-VPC 内部 NLB | **PrivateLink（EPS-Admin）単方向** |
| idm-api → identity Aurora | 同一 VPC（SG で遮断） | **ルートも SG も無し（構造遮断）** |
| Transit IP | VPC 全体が routable | **VPC-M は CGNAT/TGW 非 attach で隠蔽** |
| ブラスト半径 | SG 設定 1 枚に依存（ソフト） | **VPC＋PrivateLink 単方向（構造）** |

> **idm-api は 1 本のまま**（VPC を分けても Lambda は分けない）。CRUD＋authz のオーケストレーションは 1 実行内・outbox 1Tx アンカーを維持（[ADR-062 案 C/D 却下](../../adr/062-idm-api-execution-form-lambda.md)）。

---

## 8. フロー別シーケンス図

### 8.0 EventBridge 経路の補足（VPC 外のサービスとの関係）

**EventBridge はリージョナルなサーバーレスサービスで VPC/サブネットの中には無い**。VPC との接点は 2 つだけ:

1. **出す側（publish）**: VPC 内 Lambda（outbox リレー等）が `PutEvents` を呼ぶ。zero-egress（NAT なし）で届かせるため **`com.amazonaws.<region>.events` の Interface VPC Endpoint**（PrivateLink、VPC-M Endpoint subnet に ENI）を経由。
2. **受け側（consume）**: **EventBridge が Lambda を非同期 invoke**（Lambda サービス経由・**VPC の ingress を通らない**）。受信 Lambda の VPC ENI は outbound（Broker 内部 NLB 等）専用。

**クロスアカウント越境**は EventBridge の **bus-to-bus ルーティング**（AWS バックボーン内・VPC/PrivateLink 非経由）。宛先アカウントの event bus に **resource-based policy** を付けて送信元アカウントを許可する。方向は 2 本（① brand→Broker 削除 / ② Broker→brand 初回 sub 通知）。信頼性 = **at-least-once + 自動リトライ + DLQ(SQS) + 冪等消費**（[ADR-064](../../adr/064-deprovisioning-propagation-outbox.md)）。

> 図の凡例: **EventBridge は VPC の外の箱**／publish 線 = VPC-M の events IF Endpoint 経由（PrivateLink）／越境線 = bus→bus（EventBridge 内部）／invoke 線 = サービス→Lambda（VPC 非経由）。

### 8.1 JIT ユーザー登録（顧客 IdP フェデ・初回ログイン → shadow 生成 → authz スタブ）

```mermaid
sequenceDiagram
  autonumber
  actor U as ユーザー(ブラウザ)
  participant CF as CloudFront+WAF
  participant BKC as Broker KC
  participant CIdP as 顧客 IdP
  participant EB as EventBridge
  participant BH as ブランドハンドラ(VPC-M)
  participant ZA as authz Aurora(VPC-M)
  U->>CF: idp. ログイン(認可要求)
  CF->>BKC: authorize
  BKC-->>U: 302 顧客 IdP へ (front-channel)
  U->>CIdP: 顧客 IdP で認証
  CIdP-->>U: 302 code を Broker へ
  U->>BKC: code
  BKC->>CIdP: back-channel code→token / JWKS / userinfo
  Note over BKC,CIdP: ※IdP が「IdP-KC」の場合のみ back-channel は EPS-OIDC(PrivateLink) 経由
  BKC->>BKC: First Broker Login SPI が shadow を JIT 生成 (provisioned_by=jit)
  BKC->>EB: 初回のみ sub 通知 (Broker→brand)
  EB->>BH: invoke(初回 sub 通知)
  BH->>ZA: authz スタブ行 生成 (sub+brand_id)
  BKC-->>U: Broker トークン発行(ログイン完了)
```

### 8.1b 【新方式・比較用】事前登録 + 遅延バインド（Broker→brand の EventBridge を消す案）

> **位置づけ**: 2026-08-19 のユーザー提案。**現行（§8.1）を置き換えるものではなく比較のための併記**。採否は下表の判断材料と、アプリチームへの確認（QA）の回答で決める。

**着想**: `authz` 行を **`tenant_id` + `user_name`** で**事前に作っておき**、`sub` は**初回アクセス時にブランド側が自分で刻む**。こうすると **Broker が他アカウントの DB を触らなくなる**ため、`Broker → brand` 方向の EventBridge が不要になる。

```mermaid
sequenceDiagram
  autonumber
  actor A as テナント管理者
  participant AG as API Gateway
  participant IDM as idm-api(VPC-M)
  participant ZA as authz Aurora(VPC-M)
  actor U as ユーザー(ブラウザ)
  participant BKC as Broker KC
  participant CIdP as 顧客 IdP
  participant APP as アプリ

  rect rgb(240,248,255)
  Note over A,ZA: ① 事前登録（ログインより前・Keycloak を一切触らない）
  A->>AG: admin. で利用者を事前登録(tenant_id + user_name + 権限)
  AG->>IDM: invoke(CREATE)
  IDM->>ZA: authz 行 生成 (tenant_id + user_name, sub は NULL)
  Note over IDM,ZA: ブランド内で完結・越境ゼロ<br/>フェデ利用者なので Keycloak への作成は不要
  end

  rect rgb(255,250,240)
  Note over U,BKC: ② 初回ログイン（越境ゼロ）
  U->>BKC: ログイン
  BKC->>CIdP: 認証(back-channel)
  BKC->>BKC: shadow を JIT 生成 → sub 発番
  BKC-->>U: トークン発行 (sub + tenant_id + user_name)
  Note over BKC: EventBridge への publish なし
  end

  rect rgb(245,255,245)
  Note over APP,ZA: ③ 遅延バインド（ブランド内のローカル書き込み）
  U->>APP: アプリ利用開始
  APP->>IDM: /api/me/context (JWT)
  IDM->>ZA: sub で検索 → 無ければ tenant_id+user_name で検索し sub を刻む(冪等 upsert)
  IDM-->>APP: 権限コンテキスト返却
  Note over IDM,ZA: 以降は sub で引く（user_name 依存は初回の 1 回だけ）
  end
```

#### 現行（§8.1）との比較

| 観点 | 現行: Broker→brand 通知 | 新方式: 事前登録 + 遅延バインド |
|---|---|---|
| **Broker→brand の EventBridge** | **必要** | **不要**（消える） |
| brand→Broker の EventBridge（削除伝播） | 必要 | **必要（変わらず）** |
| `authz` の書き手 | **2 つ**（Broker 由来のスタブ + idm-api） | **1 つ**（idm-api のみ）に純化 |
| 初回ログイン時の権限 | スタブ行のみ（権限は後付け） | **登録時に付与済み**（`Q86`「ログインできたのに使えない」が起きない） |
| 事前に利用者を知る必要 | 不要 | **必要**（知れないテナントは現行方式に戻る） |
| JWT クレーム | `sub` + `tenant_id` | **`user_name` の追加が必要**（`ADR-030` Stage 1 の変更） |
| アプリへの依存 | なし | **`/api/me/context` の呼び出しが必須**（呼ばれないと紐づかない） |

#### 新方式が要求する前提（未確定）

1. **JWT に `user_name` を載せる** — `ADR-030` Stage 1 は現在 `sub` のみで `tenant_id`・`user_name` を含まない。**`user_name` はメールアドレスにしない**こと（`P-10` PII 非搭載に抵触するため、`<tenant>-<userid>` 形式とする）。
2. **`user_name` の一意性を「退職者を含めて」義務付ける** — 再割当されると**前任者の権限を継承する事故**が起きる（`ADR-018` が email を Layer A に使うことを禁じた理由と同型）。
   - **「削除時に全情報を消せば衝突しない」は成立しない**: 監査ログは 7 年保持（`NFR-COMP-007`）、Phase 1 は物理削除禁止（`jit-scim §10.4.K`）、`Q56` でも「記録内の本人を指す番号は残す」を推奨としている。
   - 契約文言だけでは顧客の人事都合で破られるため、**使用済み `user_name` の墓標を持ち再登録を拒否**する機構とセットにする。
3. **アプリが `/api/me/context` を必ず呼ぶ** — 呼ばれないと紐づかない。冪等 upsert・同時呼び出しの競合対策が要る。
4. **事前登録されていない利用者がログインしてきた場合の扱い** — 拒否するか空で作るか（`Q86` と同じ判断）。

#### 適用範囲

**全テナントに適用できるわけではない。** 事前に利用者を知れないテナント（SCIM も名簿提供も無い）は**現行方式（§8.1）が必要**。したがって**両方式の併存**になり、**EventBridge の作り込み自体は残る**（ただし通る量は減る）。

---

### 8.1c 【新方式・比較用】登録時に Broker 利用者を事前作成（`sub` を登録時点で確定）

> **位置づけ**: 2026-08-19 追加。§8.1b の派生案。**「アプリ生成 UUID と `sub` は性質が同じで、違いは存在するタイミングだけ」**という気づきから、**登録時点で `sub` を採ってしまう**案。

**着想**: `sub` が登録時に確定していれば、**突合キーそのものが不要**になる（`user_name` の使い回し禁止も要らない）。

```mermaid
sequenceDiagram
  autonumber
  actor A as テナント管理者
  participant IDM as idm-api(VPC-M)
  participant EB as EventBridge
  participant BL as Broker側 Lambda
  participant BKC as Broker KC(Admin NLB)
  participant ZA as authz Aurora(VPC-M)
  actor U as ユーザー
  participant CIdP as 顧客 IdP

  rect rgb(240,248,255)
  Note over A,ZA: ① 事前登録（sub をここで確定）
  A->>IDM: 利用者を事前登録
  IDM->>EB: 利用者作成要求(brand→Broker)
  EB->>BL: invoke
  BL->>BKC: Admin API で利用者作成 → sub 採番
  BL->>EB: sub 返却(Broker→brand)
  EB->>IDM: invoke
  IDM->>ZA: authz 行 生成 (sub をキーに)
  end

  rect rgb(255,250,240)
  Note over U,CIdP: ② 初回ログイン（越境ゼロ・突合不要）
  U->>BKC: ログイン
  BKC->>CIdP: 認証
  BKC->>BKC: 既存利用者に顧客 IdP をリンク（新規作成しない）
  BKC-->>U: トークン発行 (sub は登録時のもの)
  end
```

#### ⚠ 案 X の致命的な問題

**往復 2 回の越境が発生する。**`sub` を採るには Broker へ作成要求を出し（brand→Broker）、採番結果を受け取る（Broker→brand）必要がある。**現行 §8.1 の 1 回より増える。**

**同期呼び出し（PrivateLink）にはできない。**[U6 §6.3](../06-infra-network-design.md) が PrivateLink を採用した**根拠 1** は次のとおり:

> IdP-KC 側から Broker VPC へ**構造的に到達できない**単方向経路は、**IdP-KC（PW ハッシュ保有側）侵害時の横展開を経路レベルで遮断**する

**案 X は brand → Broker 方向**であり、**この防御が遮断したい向きそのもの**。よって PrivateLink で経路を開けるのは設計方針に反する。既存の `X-3`（削除伝播）も同じ理由で **EventBridge + Broker 側 Lambda**（ネットワーク経路は開けずイベントだけ渡す）にしてある。

**TGW を使えばよいのでは、という点も否定される**（[U6 §6.3](../06-infra-network-design.md) **根拠 2**）:

> TGW は **NW Acct（他組織想定）依存**となり、弊社 2 Acct 間の内部経路まで**他組織の変更管理に載る**（`P-18` の教訓）

#### 3 案の比較（結論）

| | 現行 §8.1 | 案 Y §8.1b（遅延バインド） | 案 X §8.1c（事前 `sub` 採番） |
|---|---|---|---|
| **Broker↔brand の越境（登録〜初回ログイン）** | **1 回**（Broker→brand） | **0 回** | **2 回**（往復） |
| 突合キー | 不要 | **必要**（`externalId` / `user_name`） | **不要** |
| `user_name` 使い回し禁止 | 不要 | **必要** | 不要 |
| JWT クレーム追加 | 不要 | **必要**（`tenant_id` + `user_name`） | 不要 |
| アプリへの依存 | なし | **`/api/me/context` 必須** | なし |
| 登録時の失敗の見え方 | — | — | **非同期のため即座に分からない** |
| 初回ログイン時の権限 | スタブのみ | **付与済み** | **付与済み** |

**案 X は突合の問題を消すが越境が倍増し、しかも同期にできないため「登録したのに Broker に居ない」状態が非同期で残る。** 案 Y の「越境 0 回」と比べて利点が乏しい。

**現時点の評価**: **案 Y（§8.1b）が最も筋が良い**。ただし成立条件（アプリの `/api/me/context` 呼び出し・クレーム追加・使い回し禁止）が満たせない場合は**現行 §8.1 を維持**する。案 X は**採らない**方向。

---

### 8.2 IdP-KC ローカルユーザー登録（非 IdP テナント・管理者作成）

```mermaid
sequenceDiagram
  autonumber
  actor A as テナント管理者
  participant AG as API Gateway
  participant IDM as idm-api(VPC-M)
  participant EPS as EPS-Admin(PrivateLink)
  participant IKC as IdP-KC Admin API
  participant ZA as authz Aurora(VPC-M)
  A->>AG: admin. でユーザー作成(role 付き)
  AG->>IDM: invoke(CREATE)
  IDM->>EPS: create user(local PW)
  EPS->>IKC: (PrivateLink EPS-Admin) Admin API
  IDM->>ZA: authz 行 生成 (sub+brand_id)
  Note over IDM,ZA: dual write を 1 実行内で順序制御+補償<br/>(Lambda を分割しない理由・ADR-062 案C却下)
  IDM-->>AG: 完了
```

### 8.3 削除①: IdP-KC ローカル削除（能動キルスイッチ・EventBridge 詳細込み）

```mermaid
sequenceDiagram
  autonumber
  actor A as 管理者
  participant IDM as idm-api(VPC-M)
  participant EPS as EPS-Admin
  participant IKC as IdP-KC Admin API
  participant ZA as authz Aurora(VPC-M)
  participant REL as outbox リレー(VPC-M)
  participant EEP as events IF Endpoint(VPC-M)
  participant EB as EventBridge (brand→Broker bus)
  participant SHC as shadow 制御 Lambda(Broker)
  participant BKC as Broker KC Admin API
  A->>IDM: DELETE user (API GW 経由)
  IDM->>EPS: soft-delete(enabled=false + deprovisioned_at)
  EPS->>IKC: (PrivateLink) Admin API
  IDM->>ZA: 【1Tx】projection deprovisioned + outbox 行(user.deprovisioned)
  Note over IDM,ZA: soft-delete と outbox を同一 Tx = 喪失なし
  REL->>ZA: 未送信 outbox をポーリング
  REL->>EEP: PutEvents(user.deprovisioned)
  EEP->>EB: PrivateLink(events endpoint) 経由で publish
  EB->>EB: brand bus Rule → Broker bus(クロスアカウント・resource policy)
  EB->>SHC: invoke(user.deprovisioned) ※VPC 非経由
  SHC->>BKC: shadow enabled=false + not_before + session revoke(冪等)
  Note over SHC,BKC: 重複配送も冪等で安全。失敗は DLQ + 数分リコンサイルが砦
```

### 8.4 削除②: 顧客 IdP + SCIM（能動・IdP-KC と同じパスに合流）

```mermaid
sequenceDiagram
  autonumber
  participant CIdP as 顧客 IdP(SCIM Client)
  participant AG as API Gateway
  participant SF as SCIM Facade(VPC-M)
  participant ZA as authz Aurora(VPC-M)
  participant REL as outbox リレー
  participant EB as EventBridge
  participant SHC as shadow 制御 Lambda(Broker)
  participant BKC as Broker KC
  CIdP->>AG: SCIM DELETE /Users/{id}
  AG->>SF: invoke
  SF->>ZA: 【1Tx】soft-delete(scim) + outbox 行
  REL->>EB: PutEvents(user.deprovisioned) (events IF Endpoint 経由)
  EB->>SHC: invoke(クロスアカウント)
  SHC->>BKC: shadow enabled=false + revoke(冪等)
  Note over CIdP,BKC: 顧客が SCIM を持てば「能動パス」に合流(§8.3 と同一終端)
```

### 8.5 削除③: 顧客 IdP + JIT のみ（受動＝信号が無い場合）

```mermaid
sequenceDiagram
  autonumber
  actor U as 元ユーザー(ブラウザ)
  participant CIdP as 顧客 IdP
  participant BKC as Broker KC
  participant APP as アプリ(RP)
  participant BATCH as 90日休眠バッチ(Broker)
  Note over CIdP: 顧客が自社 IdP でユーザー無効化<br/>→ 本基盤には削除信号が来ない
  rect rgb(255,238,238)
  Note over U,BKC: (1) 新規ログインは即塞がる
  U->>BKC: 再ログイン試行
  BKC-->>U: 302 顧客 IdP へ
  U->>CIdP: 認証
  CIdP-->>U: 拒否(無効化済み) → 新トークン発行されない
  end
  rect rgb(255,250,230)
  Note over U,APP: (2) 既存トークンはゾンビ窓
  U->>APP: 既存 AT で API 呼び(AT TTL 30分内は通る)
  Note over APP: AT 満了後の RT rotation は顧客 IdP 再認証が要り失敗
  Note over BKC: shadow は enabled=true のまま(最大 RT 満了 or 下記バッチまで残存)
  end
  rect rgb(238,244,255)
  Note over BATCH: (3) 受動クリーンアップ
  BATCH->>BKC: provisioned_by=jit かつ last_login>90日 の shadow を検出→disable
  Note over BATCH,BKC: idpkc shadow は除外(§8.3 の能動で処理済み)。<br/>即時性が要る顧客は SCIM(§8.4) / 将来 CAEP(G-SSF)
  end
```

> **能動 vs 受動の分岐点 = 削除信号の有無**。§8.3（idm-api 削除）と §8.4（SCIM DELETE）は「我々が観測できる削除」ゆえ**同一の能動パス**（outbox→EventBridge→shadow 制御）に合流。§8.5（顧客 IdP + JIT のみ）は**信号が構造的に来ない**ため受動（フェデ自然失敗＋90 日バッチ）。統一は **SCIM / CAEP のオプトイン**で提供される（[03 §3.8 経路表](../03-identity-provisioning-design.md) line 113-135、責任分界 L1-L3）。

### 8.6 EventBridge のトリガー詳細（publish=エンドポイント通信 / trigger=invoke）

**混同しやすい 2 種類の通信を分離する**:
- **publish（＝EventBridge を"叩く/キックする"）** = VPC 内 Lambda が `PutEvents` API を呼ぶ。zero-egress なので **`com.amazonaws.<region>.events` Interface Endpoint** の ENI を通る。← **ここだけがエンドポイント通信**。
- **trigger（＝EventBridge が Lambda を"起動する"）** = バス上の **Rule** が **Event Pattern** で一致 → **Target**（別バス or Lambda）へ push。Lambda Target なら **EventBridge が `lambda:InvokeFunction` で非同期 invoke**。consumer Lambda は**待ち受けエンドポイントを持たず、呼ばれる側**（VPC/エンドポイント非経由）。

**用語**: Event Bus（土管）／ Rule（Event Pattern で待ち受ける条件）／ Target（一致時の push 先）。

```mermaid
sequenceDiagram
  autonumber
  participant REL as outbox リレー Lambda(VPC-M)
  participant EEP as events IF Endpoint(VPC-M)
  participant BUSA as EventBridge brand bus(IdP-KC Acct)
  participant BUSR as EventBridge Broker bus(Broker Acct)
  participant SHC as shadow 制御 Lambda(Broker)
  participant BKC as Broker KC Admin API
  rect rgb(235,245,255)
  Note over REL,EEP: 【publish = 唯一の"エンドポイント通信"】
  REL->>REL: DNS: events.region.amazonaws.com<br/>→ IF Endpoint の private IP(Private DNS)
  REL->>EEP: HTTPS 443 PutEvents{Source, DetailType=user.deprovisioned, Detail={sub,brand_id}}
  EEP-->>BUSA: PrivateLink backbone でサービスへ到達
  end
  rect rgb(240,255,240)
  Note over BUSA,BUSR: 【trigger = Rule が Event Pattern 照合 → Target へ push】
  BUSA->>BUSA: Rule(pattern: detail-type=user.deprovisioned) に一致?
  BUSA->>BUSR: 一致 → Target=Broker bus(クロスアカウント)<br/>※Broker bus の resource policy が brand Acct を許可
  BUSR->>BUSR: Rule(同 pattern) に一致?
  BUSR->>SHC: 一致 → Target=Lambda を非同期 invoke<br/>(EventBridge が lambda:InvokeFunction、event=payload / エンドポイント不要)
  end
  SHC->>BKC: shadow enabled=false + not_before + session revoke(冪等)
  Note over BUSR,SHC: invoke 失敗時は Target の DLQ(SQS) + 自動リトライ
```

**要点**:
- 「Lambda が EventBridge を叩く」= **PutEvents（IF Endpoint 経由の API コール）**。
- 「EventBridge が Lambda を起動する」= **Rule 一致 → Target invoke**（push・エンドポイント不要）。
- クロスアカウントは **bus→bus**（宛先 bus の resource policy 許可、VPC/PrivateLink 非経由）。
- **1 つの Lambda（outbox リレー）が publish 側、別の Lambda（shadow 制御）が invoke される側**で、両者は EventBridge を挟んで**疎結合**（直接は繋がらない）。
