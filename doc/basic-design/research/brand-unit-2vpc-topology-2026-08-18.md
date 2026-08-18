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
