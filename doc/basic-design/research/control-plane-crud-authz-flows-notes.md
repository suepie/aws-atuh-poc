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
- **「Broker の DB」は shadow 専用**（authz はブランドユニット側、ADR-063）。CRUD とは別フロー。
- **アプリ/ #2 が Broker Keycloak を能動的に叩くことは無い**（P-17）。ユーザー CRUD も権限もブランド内で完結する。
- **Broker Keycloak を叩くのは中央 shadow 制御 Lambda の shadow 操作（無効化/復活）だけ**、内部 NLB 経由（**IdP-KC 削除イベントで発火**、フロー④）。

## 1.5 登場する画面/アプリと配置の決定（E 反映、2026-08-06）

> **実行形態 = Lambda に確定（[ADR-062](../../adr/062-idm-api-execution-form-lambda.md)、O-9 決定）**。以下の図・フローは Lambda 前提。

**画面は 1 枚、バックエンドのアプリは 2 つ、同居アプリは別物（Phase 1 対象外）**：

| もの | 種類 | 置き場所 | 役割 |
|---|---|---|---|
| **管理 SPA** | 人の画面（1 枚）| CloudFront/S3 | **ユーザー管理タブ + 権限管理タブ**（"2 画面" でなく 1 SPA の 2 タブ）|
| **エッジ（CloudFront/API GW）** | ルーティング（ステートレス）| エッジ | **JWT 検証(L1) + ブランド → そのブランドの #2 へ振る**（重い中央 front door は不要）|
| **idm-api #2（ブランド管理 API）** | **Lambda**（ADR-062）| **ブランドユニット（IdP-KC Acct）・層③** | **主役：CRUD + 権限編集 + authz + projection + idmap** |
| **shadow 制御 Lambda** | **Lambda**（ADR-062）| Broker Acct・層③ | **中央・薄い。Broker shadow の enable/disable のみ**（IdP-KC 削除イベントで発火、フロー④）|
| **同居アプリ** | プログラム（M2M）| 非推奨（App Acct へ）| 経路⑤ CRUD。Phase 1 対象外 |

**決定（本セッションの議論の反映）**：
- **編集・権限・CRUD は #2（ブランド側）が実体**（ユーザー編集・権限は per-brand のため）。**入口は #2**、**ルーティングはエッジ**（CloudFront/API GW がブランド → そのブランドの #2 へ、JWT L1 検証も）。**重い中央 front door（旧 #1）は置かない**。**経路⑤（同居アプリ）も #2 へ寄せる**（App Acct のアプリが #2 を Client Credentials で呼ぶ）。
- **中央（Broker）に残るのは shadow 制御だけ**（Broker が共有 1 つで shadow が中央 Broker KC にあるため）。**IdP-KC 削除をトリガーに Broker shadow を無効化**（非同期イベント、フロー④）。
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
        SHC["shadow制御 Lambda<br/>(中央・薄い)"]
        NLBB["内部NLB kc-admin"]
        BKC["Broker Keycloak<br/>shadow"]
        BDB[("Broker Aurora<br/>= shadow のみ")]
    end

    subgraph I["IdP-KC Acct（ブランドユニット）"]
        API2["idm-api #2 = Lambda<br/>主役: CRUD+権限+authz+projection"]
        NLBI["内部NLB kc-admin"]
        IKC["IdP-KC Keycloak"]
        IDB[("IdP-KC Aurora<br/>= identity")]
        BAZ[("ブランド authz+idmap+projection<br/>(sub+brand_id)")]
        BAPP["ブランドのアプリ"]
    end

    ADM --> CF
    CF --> SPA
    CF --> GW -->|"invoke(brand→#2)"| API2
    API2 -->|"identity: 内部NLB"| NLBI --> IKC
    IKC --> IDB
    API2 -->|"権限/idmap/projection: ローカル"| BAZ
    BAPP -->|"/api/me/context ローカルread"| BAZ
    API2 -.->|"削除: user.deprovisioned(EventBridge)"| SHC
    SHC -->|"shadow無効化: 内部NLB"| NLBB --> BKC
    BKC --- BDB
    BKC -.->|"初回sub通知(Broker→ブランド)"| BAZ
```

- **編集・権限・CRUD は #2（ブランド側）が実体**。**ルーティングはエッジ**（`CloudFront(api.) → API GW(JWT L1) → ブランドの #2 を invoke`）。**重い中央 front door は無し**。
- **中央（Broker）は shadow 制御 Lambda のみ**（IdP-KC 削除イベントで Broker shadow を無効化、フロー④）。**Broker は authz を持たない**。
- **authz / idmap / projection はブランドユニット**（案 b・ADR-063）。**ブランドのアプリは `/api/me/context` をブランドローカル read（越境なし）**。Keycloak Admin API へは内部 NLB 経由。
- **越境は最小**：`#2→Broker`（削除イベント）/ `Broker→ブランド`（初回 sub 通知）。**ホットパス（アプリの context read）は越境ゼロ**。

## 3. フロー①：ユーザー作成（管理画面から、hosted ユーザー、経路④ `local-admin`）

```mermaid
sequenceDiagram
    participant SPA as 管理SPA(→APIGW)
    participant A2 as idm-api #2 (ブランド/IdP-KC)
    participant IKC as IdP-KC Keycloak (内部NLB)
    participant IDB as IdP-KC Aurora (identity)

    SPA->>A2: POST /users (APIGW がブランド→#2 にルーティング)
    A2->>IKC: Admin API (内部NLB経由)
    IKC->>IDB: ユーザー作成
    Note over A2,IDB: ブランド内で完結(Broker 不介在)<br/>Broker shadow は初回ログイン時に JIT 生成
    A2-->>SPA: 完了
```

- **CRUD は #2 がブランド内（IdP-KC クラスタ内、内部 NLB）で完結**。Admin API を外部へ露出しない方針は維持（旧「#1 が #2 を委譲呼び」は CRUD ブランドローカル化で不要、ADR-063）。

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
- **推奨**：**アプリは App Acct に置き、CRUD は ブランドの #2（ブランド管理 API）を Client Credentials で（エッジ経由）呼ぶ**。→ **業務アプリを IdP-KC アカウントに同居させず** credential 隔離維持。
- **Phase 1 は経路⑤ 自体が対象外**のため当面 moot。ただし**設計前提を "同居しない" 方向に倒しておく**（P-17 の「同居前提」を緩める提案）。

### hosted / federated の分離（CRUD は hosted 専用）

- **CRUD（作成/削除）は本質的に hosted 専用**。federated は顧客 IdP が作成/削除するため CRUD 不可 → **CRUD バックエンド（#2/IdP-KC）は既に "hosted 専用"** 経路。federated 管理は **shadow 遮断（中央 shadow 制御、IdP-KC 削除トリガー、フロー④）+ 権限編集（ブランド authz、#2、ADR-063）**。**別 tier・別アカウントで既に分離済み**。
- **画面（管理 SPA）は 1 つのまま**、出自で操作を出し分け（CRUD タブは hosted のみ活性、federated はグレー）。**2 SPA 化は mixed テナントで逆効果**（capability 適応の結論）。

## 5. フロー③：権限編集（ブランドユニット側、案 b・ADR-063）

```mermaid
sequenceDiagram
    participant SPA as 管理SPA(→APIGW)
    participant A2 as idm-api #2 (ブランド/IdP-KC)
    participant AZ as ブランド authz+projection (IdP-KC側)

    SPA->>A2: PUT /users/{sub}/roles (APIGW がブランド→#2 にルーティング)
    A2->>AZ: ②authz へ書込 + projection upsert (ローカル)
    Note over A2,AZ: Keycloak は叩かない(権限=Backend DB)<br/>brand_id + sub キー
    A2-->>SPA: 完了
```

- **管理 SPA →（エッジ: API GW がブランド→#2 ルーティング）→ #2（ブランド）→ ブランド authz DB（IdP-KC 側）ローカル**。Keycloak は叩かない。中央 #1 は経由しない。
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

- **ユーザー CRUD**：**ブランド（#2/IdP-KC）内で完結**（`#2 → IdP-KC Keycloak → IdP-KC Aurora`）。**Broker Keycloak は叩かない**。**入口は #2**（エッジが brand→#2 ルーティング）、中央 #1 は経由しない。
- **権限編集**：**ブランドユニット内で完結**（`SPA →（エッジ）→ #2 → ブランド authz DB`、案 b・ADR-063）。**Keycloak を叩かない**（権限は Backend DB、`sub`+`brand_id` キー）。**アプリの `/api/me/context` はブランドローカル read（越境ゼロ）**。
- **Broker Keycloak を叩くのは中央 shadow 制御 Lambda の shadow 操作（無効化/復活）だけ**（IdP-KC 削除イベントで発火、フロー④）、内部 NLB 経由。**Broker は authz を持たない**（共有＝認証/ログイン描画/sub/ルーティング/shadow）。
- **実行形態 = Lambda（ADR-062）**：#2（ブランド管理 API）と 中央 shadow 制御は Lambda。Keycloak Admin API へは**内部 NLB（scheme=internal + SG 限定 + server-TLS + アプリ層認証）**で到達。決め手は **auth-critical な Keycloak（P0）と管理ツール（P1）を別障害ドメインに分離**。
- **配置 = ブランドユニット（ADR-063）**：ブランドを将来の隔離/複製単位とし、authz/idmap/projection/CRUD/アプリをブランド側に。**Broker は共有 1 つ**（ログインはブランド別テーマを 1 Broker で描画）。不変条件: sub グローバル / brand_id 一級キー / cross-brand join なし / Broker 共有関心のみ。

## 8. 未決（E/F 関連）

- **O-9**: **Lambda で確定（ADR-062）**。本ノートは Lambda 前提に更新済み。残る実装論点は内部 NLB の堅牢化（特に #2 = credential アカウント）。
- **越境イベント経路（旧 O-12 を再定義）**: `#2 → Broker`（削除 `user.deprovisioned`）/ `Broker → ブランド`（初回 sub 通知）= EventBridge。shadow 制御 Lambda の S2S 認可。**旧「#1→#2 PrivateLink 委譲」は CRUD がブランドローカル化したため不要**（front door はエッジルーティングに置換、ADR-063）。
- **front door トポロジ確定**: ブランド主役（#2 が CRUD+authz の実体）/ 中央は shadow 制御のみ / ルーティングはエッジ（ADR-063）。伝播窓の許容 SLA が残論点。
- **経路⑤ / EventBridge 削除経路**の実装詳細は D3-17（Phase 1 スコープ）。射影フィードは D1 SCIM E2E で PoC 検証（G-SCIM）。
