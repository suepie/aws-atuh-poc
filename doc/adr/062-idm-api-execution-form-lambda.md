# ADR-062: ユーザー管理 API（idm-api）の実行形態 = Lambda 採用（O-9 決定）

- **ステータス**: Proposed（基本設計フェーズで Accepted 昇格予定）
- **日付**: 2026-08-06 作成、2026-08-08 更新（本文をブランド主役トポロジに反映〔[ADR-063](063-brand-unit-architecture.md)〕、削除/デプロビ伝播を [ADR-064](064-deprovisioning-propagation-outbox.md) へ分離。**実行形態=Lambda の決定は不変**）
- **決定**: **idm-api（管理コントロールプレーン = ブランド管理 API〔主役〕+ 中央 shadow 制御 Lambda + 非同期の糊）を AWS Lambda で実装する**（ROSA 常駐案を退け、O-9 を Lambda で確定）。**本 ADR のスコープは実行形態（Lambda）**。トポロジ(ブランド主役)は [ADR-063](063-brand-unit-architecture.md)、削除伝播は [ADR-064](064-deprovisioning-propagation-outbox.md)。
- **対応する前提**: **[P-20 管理コントロールプレーンの実行形態](../basic-design/01-architecture-baseline.md)**（2026-08-17 正式採番。旧 O-9。それまで P 表に不在で、Excel 側が仮採番 `D-IDMAPI-1` で追跡していた）
- **関連**:
  - [ADR-038 ユーザ管理画面](038-tenant-admin-portal.md)（本 API の親。SPA + idm-api の構成）
  - [ADR-056 ROSA 採用判断](056-rosa-adoption-decision.md)（Keycloak は ROSA HCP。本 ADR は "idm-api は ROSA に載せない" と決める）
  - [ADR-039 ネットワーク監査アカウント設計](039-centralized-network-account-edge-layer.md)（6 アカウント体系・エッジ）
  - [U6 §6.3 D-U6-06/11](../basic-design/06-infra-network-design.md)（PrivateLink 単方向 / Admin API in-cluster 方針 — 本 ADR で一部見直し）
  - [U10 §10.2 D-U10-07/08](../basic-design/10-integration-migration-design.md)（idm-api = 単一 OpenAPI × 2 デプロイ）
  - 検討材料: [research/idm-api-ingress-execution-comparison-notes.md](../basic-design/research/idm-api-ingress-execution-comparison-notes.md)（A/B/Lambda 3 案比較・NLB 露出・mTLS・ROSA サポート境界）、[research/control-plane-crud-authz-flows-notes.md](../basic-design/research/control-plane-crud-authz-flows-notes.md)（CRUD/権限フロー）

---

## Context

### 決めること（O-9）

管理コントロールプレーン **idm-api**（[ADR-038](038-tenant-admin-portal.md) の Backend、単一 OpenAPI をブランド〔IdP-KC Acct〕へデプロイ = idm-api〔主役: CRUD/権限/authz/projection〕。中央〔Broker Acct〕は shadow 制御 Lambda のみ）を **どの実行形態で動かすか**（O-9）。**トポロジ(ブランド主役)は [ADR-063](063-brand-unit-architecture.md)**。候補は 3 つ:

- **A: ROSA 常駐 + Route**（既存 ingress チェーンに `api.` で相乗り、L1 JWT はクラスタ内フィルタ）
- **B: ROSA 常駐 + API GW**（API GW → VPC Link → Private NLB → IngressController → Pod）
- **C: Lambda**（API GW → Lambda ネイティブ invoke）

### 前提・制約

1. **Keycloak Admin API は既定 ClusterIP**（クラスタ内到達のみ、外部 ALB は `/admin` 403、[D-U6-11](../basic-design/06-infra-network-design.md)）。→ Lambda は Pod ネットワーク外なので、到達には**内部 NLB での露出**が要る。
2. **Keycloak は認証の中核 = P0**（可用性喪失 = 全ログイン不可）。idm-api は**管理ツール = P1 相当**。
3. **credential 隔離**：IdP-KC は PW ハッシュを持つ隔離アカウント（[ADR-033/P-17](../basic-design/01-architecture-baseline.md)）。

### 検討の要点（research ノートで詳細）

- **NLB 露出は "外部" には効かない**：内部 NLB は `scheme=internal`（インターネット到達不可）。公開されるのは `api.basis` の idm-api エンドポイントだけで、これは**全案共通**。露出差は "VPC 内の内部到達可能性" のみで、**SG + server-TLS + アプリ層認証で防御可能**（過大評価しない）。
- **mTLS は必須でない**：server-TLS + SG + Admin API のアプリ層認証で足りる。mTLS を足すなら Secrets Manager 自動ローテ（rotation Lambda + ACM PCA）で運用可。
- **cold start**：対話的な管理 UX で数百 ms〜1s の初回遅延。許容範囲（必要なら provisioned concurrency）。
- **本質的トレードオフ**：「Admin API をネットワークに出さない（ClusterIP）」と「idm-api を Keycloak クラスタから切り離す」は**両立しない**。ROSA 常駐は前者、Lambda は後者を取る。

## Decision

**idm-api（ブランド管理 API）・shadow 制御 Lambda・非同期の糊 とも AWS Lambda で実装する。** 具体:

1. **Ingress**：`CloudFront(api.basis, WAF) → API Gateway（JWT authorizer L1 + throttle）→ Lambda（ネイティブ invoke）`。VPC Link/NLB を ingress に挟まない（最短）。**（2026-08-06 補足: 組織方針 = 全 inbound NFW 通過必須、ただし **静的 SPA と API GW は例外**〔U6 REQ-IN-12〕。API GW はこの例外ゆえ本 ingress は NFW 経路外で準拠 = そのまま維持。Option 2〔ALB→Lambda ターゲット〕/ Option 3〔Private API GW〕は不要）**
2. **Lambda の VPC アタッチ**：**2 VPC 分離（B 案）採用（2026-08-18）** — idm-api Lambda は **管理 VPC（VPC-M）** にアタッチ（旧: クラスタ VPC 層③に同居）。VPC-M で authz Aurora へ SG 直、**Keycloak Admin API へは PrivateLink 単方向（EPS-Admin）**、identity Aurora（VPC-K）へはルート/SG を持たない。根拠＝[単一 VPC リスク評価](../basic-design/research/single-vpc-consolidation-risk-2026-08-18.md)（SEC05-BP01 アンチパターン）、構成図用 詳細＝[2-VPC トポロジ](../basic-design/research/brand-unit-2vpc-topology-2026-08-18.md)。
3. **Keycloak Admin API 到達**：各クラスタに **内部 NLB（`scheme=internal`）** を新設し、**SG を Lambda の SG に限定 + 最低 server-TLS + Admin API のアプリ層認証**で守る。ClusterIP 単独方針（D-U6-11）を本用途に限り "内部 NLB + 厳格 SG" に見直す。
4. **越境**：CRUD/権限はブランド(idm-api)内でローカル完結。**旧「中央→ブランド idm-api の PrivateLink 委譲」は [ADR-063](063-brand-unit-architecture.md) で撤回**。越境は EventBridge 2 本（削除 `user.deprovisioned`=[ADR-064](064-deprovisioning-propagation-outbox.md) / 初回 sub 通知）+ フェデ backchannel PrivateLink（Broker→IdP-KC、[D-U6-06](../basic-design/06-infra-network-design.md)）。
5. **非同期の糊**（shadow 制御 / outbox リレー / Webhook Dispatcher / idmap・projection ハンドラ〔ブランドローカル〕）も **Lambda（層③）**（U9 D-U9-18）。

### 決め手

**auth-critical な Keycloak クラスタ（P0）と、管理ツール idm-api（P1）を別の障害ドメインに分離する**ことを最優先する。ROSA 常駐は idm-api のデプロイ・資源・クラスタライフサイクル（アップグレード等）を Keycloak と共有し、**管理ツールの都合が中核認証に波及し得る**。Lambda は**完全に別の failure domain**でこれを断つ。露出・mTLS の弱点は「外部に効かない + SG/server-TLS/アプリ層認証で防御 + cold start 許容」で受容可能と判断した。

## Consequences

### Positive

- **Keycloak クラスタに idm-api が一切影響しない**（デプロイ・資源・ライフサイクル完全分離）。中核認証の可用性を守る。
- **Ingress**（API GW → Lambda ネイティブ、L1 JWT・throttle・WAF は API GW 標準）。api. は **API GW が NFW 通過必須の例外**ゆえ NFW 経路外で準拠（U6 REQ-IN-12）。
- **scale-to-zero / クラスタ資源非消費**（管理系はバースト薄い）。
- CI/CD が Keycloak（GitOps）と独立。

### Negative（受容するリスク）

- **Keycloak Admin API に内部 NLB エンドポイントができる**（ClusterIP 単独でなくなる。ただし `scheme=internal` で**インターネット非露出**、公開面は in-cluster と同じ）。差は VPC 内東西経路が 1 本増える分で、SG を Lambda SG 限定 + server-TLS + アプリ層認証で緩和（**idm-api 侵害時の Admin API 到達は in-cluster と同等=引き分け**）。idm-api 側（credential アカウント）は特に厳格に。
- **cold start**（対話 UX）。→ 許容。厳しければ provisioned concurrency（scale-to-zero を失う点は承知）。
- **証明書/シークレット運用を自前**（Secrets Manager + rotation Lambda）。mesh の自動化は使えない。
- **Lambda 別パイプライン**（GitOps と別系統）。

### Constraints（実装時の必須条件）

- 内部 NLB は **`scheme=internal`**・**SG を idm-api Lambda の SG のみ許可**・**最低 server-TLS**・**Admin API のアプリ層認証（管理クライアント資格情報）必須**。
- **idm-api（IdP-KC = credential アカウント）側の内部 NLB は特に厳格に**（`scheme=internal` でインターネット非露出。SG を Lambda SG 限定・監査・可能なら mTLS 優先検討）。
- **越境は EventBridge 中心**（削除=ADR-064 / 初回 sub 通知）。S2S 認可（shadow 制御 Lambda 等）= Client Credentials（`idm:*` scope、U5 §5.8）。**旧「中央→ブランド idm-api の PrivateLink 委譲」は ADR-063 で撤回**。
- Lambda は VPC 層③ に ENI アタッチ。Aurora は SG 直。越境の全体像は [06a §A.6](../basic-design/06a-network-flow-diagrams.md)、削除伝播は ADR-064。
- **L1 = API GW ネイティブ JWT authorizer を採る場合、Broker の JWKS はパブリック到達可能である必要がある**（AWS マネージド側が issuer の `jwks_uri` を取得。private VPC エンドポイント不可、公開鍵は最大 2h キャッシュ）。現設計は `auth.` が公開（[ADR-013](013-cloudfront-waf-ip-restriction.md) L7 Rule#100 で JWKS / `.well-known` 全 IP 許可）ゆえ成立するが、**JWKS 公開を IP 制限等で絞る要件が出た場合は L1 を Lambda authorizer（VPC 内、[ADR-012](012-vpc-lambda-authorizer-internal-jwks.md)）へ切り替える**（U5 §5.6.3b）。

## Alternatives Considered

| 案 | 内容 | 不採用理由 |
|---|---|---|
| **A: ROSA 常駐 + Route** | 既存 ingress 再利用、Admin API は ClusterIP（露出なし）| idm-api が Keycloak クラスタに**同居**＝デプロイ/資源/ライフサイクルを共有。**中核認証への波及リスクを断てない** |
| **B: ROSA 常駐 + API GW** | A + API GW（JWT/throttle）| A と同じ同居問題 + ingress にホップ増 |
| **A': ROSA + 専用ノードプール** | 専用ノード + namespace + 独立 GitOps で資源/デプロイを分離、Admin API は ClusterIP 維持 | **資源・デプロイ分離は満たすが、クラスタのコントロールプレーン/アップグレード周期は共有**。"クラスタ ライフサイクルごと分離したい" 要件を満たさないため不採用（ただし将来 Lambda を退く場合の第一代替として保持）|
| **C: idm-api を CRUD/authz の 2 Lambda に分割** | Lambda-CRUD（Keycloak Admin API）と Lambda-Authz（authz Aurora）に責務分割 | **不採用（Phase 1）**。1 操作（例: ユーザ＋ロール追加）は Keycloak（HTTP Admin API）と authz Aurora（JDBC）の **2 システムへの dual write** で、これは **1 ACID Tx に入らない**（2 相コミット不可）。分割してもこの dual write は消えず、逆に **Lambda↔Lambda という 2 つ目の分散境界**を足す → 部分失敗の孤児（Keycloak にユーザだけ/authz 行だけ）・**冪等性**・**補償（saga）**・リコンサイルが増える。さらに **outbox の「1 トランザクショナルストアにアンカー」（[ADR-064](064-deprovisioning-propagation-outbox.md)）が崩れる**（authz Lambda の outbox Tx に Keycloak 作用を含められない）。**整合性は改善しない**。→ **単一 Lambda（1 実行内で try/compensate）＋ outbox** で足りる。セキュリティ動機（両方に届く単一コンポーネントを消す）も、各半分の被害が依然重大＋オーケストレータが実質両方に届くため**実利薄**（[ADR-063 §認可データ配置粒度の脅威分解](063-brand-unit-architecture.md)と同じ結論）。**規制の職務分離（identity 変更と authz 変更の実行主体分離）が要件化したら ADR-063 オプション B とセットで再評価** |
| **D: Step Functions でオーケストレーション** | idm-api を分割し Step Functions で saga 制御 | **不採用（Phase 1）**。分割時のサーガを堅牢化する**正しい道具**（durable 実行・Retry/Catch・補償の宣言化・可視性）だが、**ACID は生まれない**（結果整合 Saga のまま）→ 中間不整合の窓・**冪等性は Lambda 側の責任**・補償自体の失敗処理・状態遷移課金/レイテンシは残る。2 書込程度の管理操作には**オーバーキル**で、C と同じく単一 Lambda＋outbox で足りる。**採用局面 = 分割が強制される時（規制 SoD、案 C 再評価とセット）／本質的に多段・長時間・承認ゲート付きワークフロー（例: SN オンボーディング多段調整、人手承認付きプロビジョニング）**。Step Functions は「分割のデメリットを消す魔法」ではなく「分割を選んだ後にそれを堅牢に回す手段」 |

## Open Items

- **O-12（再定義）**: 旧「中央→ブランド idm-api の PrivateLink 委譲」は ADR-063 で撤回。残論点 = **越境イベント経路（削除/初回 sub 通知）の S2S 認可の具体**（shadow 制御 Lambda、ADR-064 / U5 §5.8）。
- **O-APP-1**: API GW を公開 or Private（VPC Endpoint 経由 NFW）。P-18 露出最小化との兼ね合い（U6）。
- **cold start 緩和**：provisioned concurrency の要否・コスト（管理系トラフィック実測後）。
- **idm-api の Admin API 内部 NLB 堅牢化**：credential アカウントゆえ mTLS 優先検討 + G-DPA（SRE 越境）とのセキュリティレビュー。
- U6 §6.3（D-U6-11「Admin API in-cluster 単独」）と U10 §10.2（idm-api 実行形態）を本 ADR に合わせて改訂。
