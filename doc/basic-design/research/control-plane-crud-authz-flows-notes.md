# 検討ノート: コントロールプレーンの CRUD / 権限編集フロー（誰が・どの DB を・どの Keycloak を叩くか）

日付: 2026-08-05 /    
起票理由: ユーザー検討（「ユーザー CRUD はアプリが IdP・DB はブローカーと理解しているが、IdP アカウントの Lambda から Broker Keycloak Pod を叩くのか？   権限編集はどこから叩くのか。図で表現してほしい」）。E（アカウント配置）/ F（実行形態）の理解整理。  
関連: [idp-kc-user-mgmt-authz-boundary-notes.md §8](idp-kc-user-mgmt-authz-boundary-notes.md)、[03-identity-provisioning-design.md](../03-identity-provisioning-design.md)（D3-14/17）、[10-integration-migration-design.md §10.2](../10-integration-migration-design.md)（D-U10-07 idm-api ×2）、[06-infra-network-design.md](../06-infra-network-design.md)（D-U6-06 PrivateLink 単方向 / D-U6-11 Admin API in-cluster）、[idm-api-ingress-execution-comparison-notes.md](idm-api-ingress-execution-comparison-notes.md)（実行形態×ingress の 3 案比較・ROSA サポート境界・mTLS）、[attribute-canonicalization-notes.md](attribute-canonicalization-notes.md)（属性正準化）、[me-context-projection-comparison-notes.md](me-context-projection-comparison-notes.md)（射影 vs 都度 join）。

## 1. 最重要の前提：「DB」は 2 つあり別物

CRUD と権限編集は**叩く DB も Keycloak も全く別**。ここを混同すると経路が分からなくなる。

| DB | 何を持つ | アカウント | 誰が書くか | Keycloak を叩くか |
|---|---|---|---|---|
| **① identity DB**＝**IdP-KC の Keycloak Aurora** | ユーザー本体（アカウント）| **IdP-KC Acct** | ユーザー CRUD | ✅ IdP-KC Keycloak（自アカウント）|
| **② authz DB**＝**Backend DB** | 権限（エンタイトルメント・機能ロール割当）+ idmap + projection | **ブランドユニット（IdP-KC 側）**（案 b・[ADR-063](../../adr/063-brand-unit-architecture.md)）| 権限編集 | ❌ Keycloak を叩かない |

**帰結**:
- **ユーザー CRUD の書込先は「Broker の DB」ではなく「IdP-KC 自身の Keycloak（同じ IdP-KC アカウント）」**。
- **「Broker の DB」は権限（authz）専用**で、CRUD とは別フロー。
- **IdP アカウントのサービスが Broker Keycloak を叩くことは無い**（P-17：逆方向の Admin API 到達を作らない）。ユーザー CRUD は IdP-KC アカウント内で完結する。
- **Broker Keycloak を叩くのは idm-api #1 の "Broker shadow 操作"（遮断/復活）だけ**、しかもローカル ClusterIP。

## 1.5 登場する画面/アプリと配置の決定（E 反映、2026-08-06）

> **実行形態 = Lambda に確定（[ADR-062](../../adr/062-idm-api-execution-form-lambda.md)、O-9 決定）**。以下の図・フローは Lambda 前提。

**画面は 1 枚、バックエンドのアプリは 2 つ、同居アプリは別物（Phase 1 対象外）**：

| もの | 種類 | 置き場所 | 役割 |
|---|---|---|---|
| **管理 SPA** | 人の画面（1 枚）| CloudFront/S3 | **ユーザー管理タブ + 権限管理タブ**（"2 画面" でなく 1 SPA の 2 タブ）|
| **idm-api #1（テナント管理 API）** | **Lambda**（ADR-062）| Broker Acct・VPC 層③ | **唯一の front door** |
| **idm-api #2（ユーザー連携 API）** | **Lambda**（ADR-062）| IdP-KC Acct・VPC 層③ | **内部 executor（①からのみ呼ばれる）** |
| **同居アプリ** | プログラム（M2M）| 非推奨（App Acct へ）| 経路⑤ CRUD。Phase 1 対象外 |

**決定（本セッションの議論の反映）**：
- **入口は①（Broker）に一本化**（人＝SPA も 機械＝アプリも①を叩く）。①は**共有 front door** として JWT/brand スコープ検証し、**ブランドの②へ CRUD も権限編集もルーティング**。**経路⑤（②直・同居）は①経由へ寄せて実質廃す**。
- **認可 DB＝ブランドユニット（IdP-KC 側）**（2026-08-06 案 b・[ADR-063](../../adr/063-brand-unit-architecture.md)）：ブランドを将来の隔離/複製単位とし、**authz/idmap/projection はブランド内に置く。Broker は authz を持たない**（共有＝認証/ログイン描画/`sub`/ルーティング/shadow のみ）。federated も **`sub`+`brand_id` キーでブランド authz に保持**（初回ログイン時に Broker→ブランドへ sub 通知、write 時のみ越境）。不変条件: ① sub グローバル安定 ② brand_id 一級キー ③ cross-brand join なし ④ Broker 共有関心のみ。
- **編集アプリ＝authz API の呼出側**でどこで動いてもよい（DB を IdP 側へ動かす必要はない）。
- **IdP-KC＝隔離した自前アカウント（VPC 分割でなくアカウント分割）**：PW ハッシュのブラスト半径のため。**業務アプリを同居させない**。
- **SPA は 1 枚のまま capability 適応**（CRUD タブは hosted のみ活性、federated はグレー）。2 SPA 化は mixed テナントで逆効果。

## 2. 構成図（Lambda 前提、ADR-062）

```mermaid
flowchart TB
    ADM["管理者(ブラウザ)"]
    CF["CloudFront api.basis(WAF)"]
    GW["API GW(JWT L1)"]
    SPA["管理 SPA(S3)"]

    subgraph B["Broker Acct（共有・1）"]
        API1["idm-api #1 = Lambda<br/>共有 front door(brand ルーティング)"]
        NLBB["内部NLB kc-admin"]
        BKC["Broker Keycloak<br/>Admin API"]
        BDB[("Broker Aurora<br/>= Broker shadow のみ")]
    end

    subgraph I["IdP-KC Acct（ブランドユニット）"]
        API2["idm-api #2 = Lambda<br/>CRUD + 権限 + projection"]
        NLBI["内部NLB kc-admin"]
        IKC["IdP-KC Keycloak<br/>Admin API"]
        IDB[("IdP-KC Aurora<br/>= ①identity DB")]
        BAZ[("ブランド authz + idmap + projection<br/>= ②(sub+brand_id キー)")]
        BAPP["ブランドのアプリ"]
    end

    ADM --> CF
    CF --> SPA
    CF --> GW -->|"invoke"| API1
    API1 -->|"shadow遮断: 内部NLB"| NLBB --> BKC
    API1 ==>|"CRUD+権限を委譲: PrivateLink単方向"| API2
    API2 -->|"identity: 内部NLB"| NLBI --> IKC
    IKC --> IDB
    API2 -->|"権限/idmap/projection: ローカル"| BAZ
    BAPP -->|"/api/me/context ローカルread"| BAZ
    BKC -.->|"初回sub通知(write時のみ越境)"| BAZ
```

- **authz / idmap / projection はブランドユニット（IdP-KC 側）**（案 b・ADR-063）。**Broker は shadow のみ**。**ブランドのアプリは `/api/me/context` をブランドローカル read（越境なし）**。
- **idm-api は Lambda**（ADR-062）。Keycloak Admin API へは内部 NLB（`scheme=internal` + SG 限定 + server-TLS + アプリ層認証）経由。Ingress = `CloudFront(api.) → API GW(JWT L1) → Lambda invoke`。
- **越境は最小**：`#1→#2`（CRUD+権限委譲、PrivateLink 単方向）/ `Broker→ブランド`（初回 sub 通知、write 時のみ、EventBridge）/ `#1→Broker shadow`（遮断）。**ホットパス（アプリの context read）は越境ゼロ**。

## 3. フロー①：ユーザー作成（管理画面から、hosted ユーザー、経路④ `local-admin`）

```mermaid
sequenceDiagram
    participant SPA as 管理SPA(→APIGW)
    participant A1 as idm-api #1 Lambda (Broker)
    participant A2 as idm-api #2 Lambda (IdP-KC)
    participant IKC as IdP-KC Keycloak (内部NLB)
    participant IDB as IdP-KC Aurora (identity)

    SPA->>A1: POST /users (作成, APIGW→Lambda)
    A1->>A2: PrivateLink 単方向で委譲
    A2->>IKC: Admin API (内部NLB経由)
    IKC->>IDB: ユーザー作成
    Note over IKC,IDB: 書込先は IdP-KC 自身の DB<br/>Broker の DB ではない
    A1-->>SPA: 完了 (Broker shadow は初回ログイン時に JIT 生成)
```

- **Admin API を PrivateLink へ直接露出しない**（#1 は #2 を呼び、Admin API 書込は IdP-KC クラスタ内で完結、D-U6-06 §6.3.2）。

## 4. フロー②：ユーザー作成（アプリから、経路⑤・IdP-KC 内で完結）

```mermaid
sequenceDiagram
    participant APP as 同居アプリ (IdP-KC Acct)
    participant A2 as idm-api #2 (IdP-KC)
    participant IKC as IdP-KC Keycloak (ClusterIP)
    participant IDB as IdP-KC Aurora

    APP->>A2: POST /users (同一アカウント内)
    A2->>IKC: Admin API (クラスタ内)
    IKC->>IDB: ユーザー作成
    Note over APP,IDB: 越境なし・Broker を一切触らない
```

- 経路⑤（`provisioned_by=app`）は D3-17 で **Phase 1 対象外**（モデルとして記載）。

## 4.5 補足：プロビジョニング経路④/⑤ の区別と「同居」の是非

### 経路④ と ⑤ は別物（"M2M か SPA か" は別経路）

手動系プロビジョニングは 2 経路あり混同しやすい（D3-04）：

| 経路 | 入口 | 誰が | 認証 | `provisioned_by` | 本ノートの図 |
|---|---|---|---|---|---|
| **④ 管理者作成** | **管理 SPA**（P-2 テナント管理ポータル / P-1 運用者）| 人間 | ユーザー AT | `local-admin` | **フロー①** |
| **⑤ アプリ発 CRUD** | **同居アプリ（プログラム）** | 機械（M2M）| Client Credentials | `app` + `provisioned_app` | **フロー②** |

- **SPA からの作成＝経路④（local-admin）**、**M2M アプリの作成＝経路⑤（app）**。**経路⑤は M2M 専用で SPA を含まない**。
- **経路⑤は Phase 1 対象外（D3-17）**。当面は経路④（SPA）のみ考えればよい。

### 「同居」の是非（P-17 前提の再考、2026-08-05）

- P-17 は「**同 Acct アプリからのユーザ CRUD 想定（変更可能性あり）**」＝**変更含みの前提**。
- **懸念**：IdP-KC は **PW ハッシュ**を持つ。業務アプリを IdP-KC アカウントに同居させると、**アプリ侵害のブラスト半径が credential ストアに及ぶ**（E の隔離論）。
- **推奨**：**アプリは App Acct に置き、CRUD は idm-api #1（Broker front door）を Client Credentials で呼んで #2 へ委譲**。→ **IdP-KC への新規 ingress 不要**（既存 Broker→IdP-KC PrivateLink 再利用）＋ **credential 隔離維持**。
- **Phase 1 は経路⑤ 自体が対象外**のため当面 moot。ただし**設計前提を "同居しない" 方向に倒しておく**（P-17 の「同居前提」を緩める提案）。

### hosted / federated の分離（CRUD は hosted 専用）

- **CRUD（作成/削除）は本質的に hosted 専用**。federated は顧客 IdP が作成/削除するため CRUD 不可 → **CRUD バックエンド（#2/IdP-KC）は既に "hosted 専用"** 経路。federated 管理は **shadow 遮断（Broker #1）+ 権限編集（ブランド authz、#2、ADR-063）**。**別 tier・別アカウントで既に分離済み**。
- **画面（管理 SPA）は 1 つのまま**、出自で操作を出し分け（CRUD タブは hosted のみ活性、federated はグレー）。**2 SPA 化は mixed テナントで逆効果**（capability 適応の結論）。

## 5. フロー③：権限編集（ブランドユニット側、案 b・ADR-063）

```mermaid
sequenceDiagram
    participant SPA as 管理SPA(→APIGW)
    participant A1 as idm-api #1 (Broker/front door)
    participant A2 as idm-api #2 (ブランド/IdP-KC)
    participant AZ as ブランド authz+projection (IdP-KC側)

    SPA->>A1: PUT /users/{sub}/roles
    A1->>A2: brand スコープでルーティング(PrivateLink)
    A2->>AZ: ②authz へ書込 + projection upsert (ローカル)
    Note over A2,AZ: Keycloak は叩かない(権限=Backend DB)<br/>brand_id + sub キー
    A2-->>A1: 完了
    A1-->>SPA: 完了
```

- **管理 SPA → #1（Broker front door, brand ルーティング）→ #2（ブランド）→ ブランド authz DB（IdP-KC 側）ローカル**。Keycloak は叩かない。
- **federated ユーザーの権限もブランド authz に持つ**（`sub`+`brand_id` キー。IdP-KC の identity レコードが無くても Backend DB の行は持てる。初回ログイン時に Broker→ブランドへ sub 通知で行生成）。

## 6. フロー④：削除（IdP-KC 削除トリガー → Broker shadow 無効化、2026-08-06 更新）

> **旧「Broker-first 二面同期」から変更**：per-brand の **「IdP-KC の削除をトリガーに Broker shadow を無効化」**（ADR-063 の shadow 制御 = **非同期イベント〔案 i〕**を確定）。ブランド主役と一致。

```mermaid
sequenceDiagram
    participant SRC as 削除元(管理者/SCIM)
    participant A2 as idm-api #2 (ブランド/IdP-KC)
    participant IKC as IdP-KC Keycloak
    participant EB as EventBridge(IdP-KC→Broker)
    participant SH as shadow制御 Lambda(Broker)
    participant BKC as Broker Keycloak

    SRC->>A2: ユーザー削除
    A2->>IKC: soft-delete(enabled=false + deprovisioned_at)
    A2->>EB: user.deprovisioned {sub, brand_id, at}
    EB->>SH: 配信(at-least-once)
    SH->>BKC: shadow を enabled=false + not_before + session revoke(内部NLB)
    Note over SH,BKC: 冪等(既に無効ならno-op)・sub キー
```

- **トリガー**：idm-api #2 が soft-delete 実行時に `user.deprovisioned {sub, brand_id, at}` を発行（削除の実行主体ゆえ確実。Keycloak Event Listener SPI 併用も可）。
- **伝送**：EventBridge クロスアカウント（IdP-KC→Broker、既存経路）。**ハンドラ**：shadow 制御 Lambda（Broker）が Broker KC で `enabled=false` + `not_before` + セッション revoke（内部 NLB）。
- **soft-delete（Phase 1）**：物理削除は Phase 2（retention 後、D3-09）。
- **federated**：IdP-KC に identity 無しのため本トリガーは発火しない → **SCIM deprovision（SCIM Facade がイベント発行）or 90 日バッチ**で shadow 無効化。
- **セーフティネット**：日次リコンサイル（IdP-KC `deprovisioned_at` ↔ Broker shadow `enabled` 不整合是正）＝イベント取りこぼし対策。
- **トレードオフ（窓）**：IdP-KC-first のため shadow 無効化まで**数秒の伝播窓**。AT 30 分 + リコンサイルで許容。**即時ゼロ窓が要件なら削除パスで同期 shadow 無効化を併用**（逆方向同期）に切替可。

## 7. まとめ（E/F の核心）

- **ユーザー CRUD**：**IdP-KC アカウント内で完結**（`#2 → IdP-KC Keycloak → IdP-KC Aurora`）。**Broker Keycloak は叩かない**。管理画面起点のときだけ `#1 → #2` を PrivateLink で 1 本越境。
- **権限編集**：**ブランドユニット内で完結**（`#1 front door → #2 → ブランド authz DB`、案 b・ADR-063）。**Keycloak を叩かない**（権限は Backend DB、`sub`+`brand_id` キー）。**アプリの `/api/me/context` はブランドローカル read（越境ゼロ）**。
- **Broker Keycloak を叩くのは #1 の shadow 操作（遮断/復活）だけ**、内部 NLB 経由。**Broker は authz を持たない**（共有＝認証/ログイン描画/sub/ルーティング/shadow）。
- **実行形態 = Lambda（ADR-062）**：idm-api #1/#2 は Lambda。Keycloak Admin API へは**内部 NLB（scheme=internal + SG 限定 + server-TLS + アプリ層認証）**で到達。決め手は **auth-critical な Keycloak（P0）と管理ツール idm-api（P1）を別障害ドメインに分離**。
- **配置 = ブランドユニット（ADR-063）**：ブランドを将来の隔離/複製単位とし、authz/idmap/projection/CRUD/アプリをブランド側に。**Broker は共有 1 つ**（ログインはブランド別テーマを 1 Broker で描画）。不変条件: sub グローバル / brand_id 一級キー / cross-brand join なし / Broker 共有関心のみ。

## 8. 未決（E/F 関連）

- **O-9**: **Lambda で確定（ADR-062）**。本ノートは Lambda 前提に更新済み。残る実装論点は内部 NLB の堅牢化（特に #2 = credential アカウント）。
- **O-12**: `#1 → #2` の内部ルート（PrivateLink NLB 上の内部リスナ）+ S2S 認可（CC scope）。
- **経路⑤ / EventBridge 削除経路**は Phase 1 対象外（D3-17）。射影フィード②は D1 SCIM E2E でのみ PoC 検証（G-SCIM）。
