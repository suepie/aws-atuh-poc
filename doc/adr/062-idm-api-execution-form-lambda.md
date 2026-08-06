# ADR-062: ユーザー管理 API（idm-api）の実行形態 = Lambda 採用（O-9 決定）

- **ステータス**: Proposed（基本設計フェーズで Accepted 昇格予定）
- **日付**: 2026-08-06 作成
- **決定**: **idm-api（テナント管理 API #1 / ユーザー連携 API #2）を AWS Lambda で実装する**（ROSA 常駐案を退け、O-9 を Lambda で確定）
- **後続 refine（[ADR-063](063-brand-unit-architecture.md)、2026-08-06）**: 本 ADR の #1/#2 トポロジ（#1 front door が #2 へ委譲・`#1→#2` PrivateLink）は **ブランド主役**に更新済み — **#2 がブランド管理 API の実体（CRUD+権限+authz+projection）、front door はエッジルーティング（CloudFront/API GW）、中央に残るのは shadow 制御 Lambda のみ、越境は「削除 `user.deprovisioned`」「初回 sub 通知」の EventBridge**。**Lambda 実行形態の決定自体は不変**。以降本文の `#1→#2` 委譲・PrivateLink 記述はこの refine を前提に読むこと。
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

管理コントロールプレーン **idm-api**（[ADR-038](038-tenant-admin-portal.md) の Backend、単一 OpenAPI × 2 デプロイ = #1 テナント管理 API〔Broker Acct〕/ #2 ユーザー連携 API〔IdP-KC Acct〕）を **どの実行形態で動かすか**（O-9）。候補は 3 つ:

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

**idm-api #1 / #2 とも AWS Lambda で実装する。** 具体:

1. **Ingress**：`CloudFront(api.basis, WAF) → API Gateway（JWT authorizer L1 + throttle）→ Lambda（ネイティブ invoke）`。VPC Link/NLB を ingress に挟まない（最短）。
2. **Lambda の VPC アタッチ**：サブネット層③（[06a §A.5.3](../basic-design/06a-network-flow-diagrams.md)）。egress のため。
3. **Keycloak Admin API 到達**：各クラスタに **内部 NLB（`scheme=internal`）** を新設し、**SG を Lambda の SG に限定 + 最低 server-TLS + Admin API のアプリ層認証**で守る。ClusterIP 単独方針（D-U6-11）を本用途に限り "内部 NLB + 厳格 SG" に見直す。
4. **越境**：`#1 → #2` は PrivateLink 単方向（[D-U6-06](../basic-design/06-infra-network-design.md)）。`IdP-KC → Broker` は EventBridge（射影フィード）。
5. **非同期の糊**（射影フィードの EventBridge ハンドラ / Webhook Dispatcher / idmap 更新ハンドラ）も **Lambda（層③）**。

### 決め手

**auth-critical な Keycloak クラスタ（P0）と、管理ツール idm-api（P1）を別の障害ドメインに分離する**ことを最優先する。ROSA 常駐は idm-api のデプロイ・資源・クラスタライフサイクル（アップグレード等）を Keycloak と共有し、**管理ツールの都合が中核認証に波及し得る**。Lambda は**完全に別の failure domain**でこれを断つ。露出・mTLS の弱点は「外部に効かない + SG/server-TLS/アプリ層認証で防御 + cold start 許容」で受容可能と判断した。

## Consequences

### Positive

- **Keycloak クラスタに idm-api が一切影響しない**（デプロイ・資源・ライフサイクル完全分離）。中核認証の可用性を守る。
- **Ingress が最短**（API GW → Lambda ネイティブ、VPC Link/NLB 不要）。L1 JWT・throttle・WAF は API GW 標準。
- **scale-to-zero / クラスタ資源非消費**（管理系はバースト薄い）。
- CI/CD が Keycloak（GitOps）と独立。

### Negative（受容するリスク）

- **Keycloak Admin API に内部 NLB エンドポイントができる**（ClusterIP 単独でなくなる）。→ SG を Lambda SG に限定 + server-TLS + アプリ層認証 + `scheme=internal` で緩和。**#2 は credential アカウント（IdP-KC）の Admin API を内部 NLB に出す**ことになる点が最も注意（最厳格 SG + 監査）。
- **cold start**（対話 UX）。→ 許容。厳しければ provisioned concurrency（scale-to-zero を失う点は承知）。
- **証明書/シークレット運用を自前**（Secrets Manager + rotation Lambda）。mesh の自動化は使えない。
- **Lambda 別パイプライン**（GitOps と別系統）。

### Constraints（実装時の必須条件）

- 内部 NLB は **`scheme=internal`**・**SG を idm-api Lambda の SG のみ許可**・**最低 server-TLS**・**Admin API のアプリ層認証（管理クライアント資格情報）必須**。
- **#2（IdP-KC 側）の Admin API 内部 NLB は最厳格**（credential アカウント）。SG・監査・可能なら mTLS を優先検討。
- `#1 → #2` は PrivateLink 単方向のみ（逆流不可）。S2S 認可 = Client Credentials（`idm:*` scope）。
- Lambda は VPC 層③ に ENI アタッチ。Aurora は SG 直、越境は PrivateLink/EventBridge の 2 本のみ（[control-plane ノート](../basic-design/research/control-plane-crud-authz-flows-notes.md)）。

## Alternatives Considered

| 案 | 内容 | 不採用理由 |
|---|---|---|
| **A: ROSA 常駐 + Route** | 既存 ingress 再利用、Admin API は ClusterIP（露出なし）| idm-api が Keycloak クラスタに**同居**＝デプロイ/資源/ライフサイクルを共有。**中核認証への波及リスクを断てない** |
| **B: ROSA 常駐 + API GW** | A + API GW（JWT/throttle）| A と同じ同居問題 + ingress にホップ増 |
| **A': ROSA + 専用ノードプール** | 専用ノード + namespace + 独立 GitOps で資源/デプロイを分離、Admin API は ClusterIP 維持 | **資源・デプロイ分離は満たすが、クラスタのコントロールプレーン/アップグレード周期は共有**。"クラスタ ライフサイクルごと分離したい" 要件を満たさないため不採用（ただし将来 Lambda を退く場合の第一代替として保持）|

## Open Items

- **O-12**: `#1 → #2` の PrivateLink 内部ルート（Endpoint Service NLB の内部リスナ）+ S2S 認可の具体（U6/U5 §5.8）。
- **O-APP-1**: API GW を公開 or Private（VPC Endpoint 経由 NFW）。P-18 露出最小化との兼ね合い（U6）。
- **cold start 緩和**：provisioned concurrency の要否・コスト（管理系トラフィック実測後）。
- **#2 Admin API の内部 NLB 堅牢化**：credential アカメントゆえ mTLS 優先検討 + G-DPA（SRE 越境）とのセキュリティレビュー。
- U6 §6.3（D-U6-11「Admin API in-cluster 単独」）と U10 §10.2（idm-api 実行形態）を本 ADR に合わせて改訂。
