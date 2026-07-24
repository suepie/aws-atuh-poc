# ADR-051: Multi-Region DR / Failover 詳細設計（Aurora Global + KMS MRK + IaC 再適用（Git SSOT））

- **ステータス**: Proposed（要件定義フェーズで Accepted に昇格予定）
- **日付**: 2026-06-23 作成、**2026-07-23 更新（ROSA HCP 転換: 大阪対称構成の成立確認 + multi-cluster v2 追記 + 基本設計 [U8](../basic-design/08-availability-dr-design.md) §8.8 に基づく正式改訂: Realm Export 全廃 → 復元 2 経路（IaC 再適用 + Aurora Global DB）/ パイロットライト（KC Scale 0）/ Tier 1 Phase 2 化 / コスト ROSA 実額化）**、**2026-07-24 更新（基本設計 Wave 3 [U9](../basic-design/09-operations-observability-design.md) 確定: テナント層 IaC 再生手段を「keycloak-config-cli / オンボーディング API」併記から自作オンボーディング API による Admin API 差分適用に一本化 — U9 D-U9-10）**

> **2026-07-23 実行基盤転換に伴う追記（[ADR-056](056-rosa-adoption-decision.md) 逆転）**:
> - **大阪（ap-northeast-3）は ROSA HCP 対応済み**（AWS 公式リージョン表 2026-07-23 確認）→ **東京 + 大阪の ROSA HCP 対称 DR 構成が成立**。本文の実行基盤記述（EKS/ECS 前提箇所）は ROSA HCP に読み替え。残 TBD: 大阪側インスタンス在庫・vCPU クォータの実確認
> - **Keycloak 26.1 以降 `jdbc-ping` がデフォルト**（multicast 不要、ノードディスカバリは KC DB 経由）。**multi-cluster v2 で外部 Infinispan 要件が撤廃**され、同期レプリケーション DB を single source of truth とする構成に簡素化。**RHBK 26.4 HA Guide は Aurora PostgreSQL 15/16/17 を multi-site HA サポート DB に明記**し、keycloak-benchmark 公式が「ROSA クロスサイト + Aurora」を手順化 — 本 ADR の Aurora Global DB 方針と方向一致（RHBK での multi-cluster v2 サポート版数確認は残 TBD）
> - 詳細: [basic-design/research/rosa-hcp-adoption-research.md](../basic-design/research/rosa-hcp-adoption-research.md)
> - ✅ **基本設計 [U8](../basic-design/08-availability-dr-design.md) で正式改訂済み（2026-07-23）**：「Realm Export 日次自動 → S3 → DR Import」戦略は 1000+ IdP 環境で不成立（[U2 §2.7.4](../basic-design/02-keycloak-logical-design.md) で realm 全体 export/import を全面禁止 — keycloak#14851 / 30MB representation 前例）のため**全廃**し、復元 2 経路 = **構成 = IaC 再適用（Git SSOT: Terraform 基盤層 + テナント層再生。テナント層は 2026-07-24 に自作オンボーディング API による Admin API 差分適用に一本化〔keycloak-config-cli は K-1〔realm representation 禁止〕と原理衝突のため不採用 — [U9 D-U9-10](../basic-design/09-operations-observability-design.md)〕）+ データ = Aurora Global DB** へ差し替えた（本文 Decision / §A.2 / §C / §E / §G / §H 反映済み。設計根拠は U8 D-U8-05〜13）
- **関連**:
  - **[basic-design/08 可用性・DR 設計（U8）](../basic-design/08-availability-dr-design.md)** — 本 ADR 正式改訂（2026-07-23）の設計根拠（D-U8-05〜13。手順・数値・成立性検証の SSOT）
  - [basic-design/06 インフラ・ネットワーク設計（U6）§6.8.2](../basic-design/06-infra-network-design.md) — 物理配置の前提（大阪側 PrivateLink 複製等）
  - [ADR-033 Keycloak 2-tier アーキテクチャ](033-keycloak-2tier-broker-idp-architecture.md)
  - [ADR-039 中央集約 Network 専用アカウント](039-centralized-network-account-edge-layer.md)
  - [ADR-040 PAM / JIT 管理者権限管理](040-pam-jit-admin-privilege-management.md) — **2026-07-23 Accepted 復帰（Phase 1 α/β）。DR 発動承認・Break-Glass は ADR-040 §C/§H + [U7 §7.6](../basic-design/07-security-compliance-design.md) 参照**
  - [ADR-044 Tabletop Exercise（Game Day 連動）](044-tabletop-exercise-incident-drill.md)
  - [ADR-045 鍵管理戦略集約（Multi-Region Key）](045-cryptographic-key-management-strategy.md)
  - [ADR-049 Vendor Risk Management（DORA 連動）](049-vendor-risk-management-tprm.md)
  - [§NFR-1 可用性](../requirements/proposal/nfr/01-availability.md)
  - [§NFR-5 DR](../requirements/proposal/nfr/05-dr.md)

---

## Context

### 背景

[§NFR-5 DR](../requirements/proposal/nfr/05-dr.md) では「RTO / RPO 要件」を抽象的に定義していたが、**具体的な Multi-Region 構成 + Failover 手順**は未定義のままだった。各 ADR で MRK / Cross-Region Replication への言及は散在していたが、**統合的な DR 戦略**として:

1. **Aurora Global Database** の採用判断（Read Replica vs Global vs Multi-AZ のみ）
2. **Keycloak Realm Replication** 戦略（Active-Active vs Active-Passive、Realm Export / Import 自動化）
3. **Network Acct（[ADR-039](039-centralized-network-account-edge-layer.md)）の Failover**（CloudFront / Route 53 / WAF）
4. **DynamoDB Global Tables**（ITDR / Adaptive Auth / Tenant Audit）
5. **S3 Cross-Region Replication**（監査ログ / SPA bundle / エラー / 案内画面 SPA）
6. **EKS Multi-Region**（Broker KC + IdP-KC 配置）
7. **Lambda + Step Functions** の Cross-Region 配置
8. **RTO / RPO 目標値**（Tier 別、規制業種顧客対応含む）
9. **Failover 自動化 vs 手動承認**（Split-Brain 防止）
10. **DR 訓練**（[ADR-044](044-tabletop-exercise-incident-drill.md) Game Day 連動）

### 規制要件

| 規制 | 関連条項 |
|---|---|
| **SOC 2 Type II A1.2** | システム可用性、Disaster Recovery プラン |
| **PCI DSS v4.0 §12.10.1** | インシデント対応 + BCP / DR |
| **ISO 27001 A.5.29-30** | 中断時の情報セキュリティ + ICT 継続性 |
| **ISO 22301** | BCMS（Business Continuity Management System）|
| **EU DORA**（2025/1）| 金融業 ICT Resilience（RTO/RPO 規制業種要件）|
| **金融庁 監督指針** | 重要システムの BCP + 訓練 |
| **NIST SP 800-34 Rev 1** | Contingency Planning Guide |
| **APPI 第 23 条** | 安全管理措置（事業継続）|

### 業界用語の整理

| 用語 | 意味 |
|---|---|
| **RTO**（Recovery Time Objective）| 復旧目標時間 |
| **RPO**（Recovery Point Objective）| データ損失許容時間 |
| **MTPD**（Maximum Tolerable Period of Disruption）| 最大許容停止時間 |
| **Active-Active** | 全リージョンで同時 Live、書込競合に注意 |
| **Active-Passive** | プライマリ + DR Standby、Failover 操作必要 |
| **Pilot Light** | 最小 Standby、Scale-up に時間 |
| **Warm Standby** | スケールダウン Standby |
| **Hot Standby** | フル Standby（最高速だが最高コスト）|
| **Aurora Global Database** | Cross-Region Replication（< 1 sec lag）、Managed Failover |
| **DynamoDB Global Tables** | Multi-Region Active-Active、Last-Writer-Wins |
| **Route 53 Health Check + Failover Routing** | DNS レベルの Failover |
| **Split-Brain** | 両 Region がプライマリと誤認、データ不整合 |
| **Failback** | プライマリ復旧後の元戻し |

---

## Decision

### 採用方針

**「Active-Passive パイロットライト（インフラ Warm + KC Scale 0）+ Region 単位 Failover + 自動化 80% + 手動承認 20%」**を採用。RTO 1 時間 / RPO 1 分を標準目標。**Tier 1（RTO 30 分）は Phase 2 検討（Phase 1 は提供しない、[U8 §8.4.4](../basic-design/08-availability-dr-design.md) — パイロットライトでは不成立）**。（2026-07-23 改訂: 旧「Warm Standby（KC Scale 1）」は Aurora Global Secondary が read-only で Keycloak が起動できないため不成立 — U8 D-U8-07）

| 項目 | 採用方針 |
|---|---|
| **プライマリ Region** | **ap-northeast-1（東京）** |
| **DR Region** | **ap-northeast-3（大阪）** |
| **Failover モデル** | **Active-Passive パイロットライト（インフラ Warm + KC Scale 0）**（Active-Active は Split-Brain リスク、運用負荷大。旧 Warm Standby（KC Scale 1）は Aurora Secondary read-only 制約で不成立 — U8 D-U8-07）|
| **RTO 標準** | **1 時間**（一般顧客）/ Tier 1（30 分）は **Phase 2 検討**（Phase 1 は提供しない、U8 §8.4.4）|
| **RPO 標準** | **1 分**（Aurora Global Database / DynamoDB Global Tables 採用）|
| **MTPD** | 4 時間（業界標準）|
| **Aurora** | **Aurora Global Database 必須**（Broker DB / IdP-KC DB 両方）|
| **DynamoDB** | **Global Tables**（ITDR / Adaptive Auth / Tenant Admin Audit / DSAR Requests）|
| **S3** | **Cross-Region Replication**（監査ログ / SPA bundle / エラー / 案内画面 SPA / DSAR Export 一時保管。**Realm Export 一時保管は廃止** — U8 D-U8-06）|
| **KMS** | **Multi-Region Keys (MRK)**（[ADR-045](045-cryptographic-key-management-strategy.md)）|
| **Keycloak** | **ROSA HCP 東西対称配置、DR はパイロットライト（インフラ Warm + KC CR replicas=0 — Aurora Secondary read-only のため KC は起動不能）**（U8 D-U8-07 / D-U8-11）|
| **Realm 設定** | **Aurora Global DB（realm 構成は DB に一体複製、リージョン障害時は Promote のみで復元完了）+ IaC 再適用（論理破壊時: PITR 主 + 差分再生。基盤層 Terraform + テナント層は自作オンボーディング API による Admin API 差分適用に一本化〔keycloak-config-cli は K-1〔realm representation 禁止〕と原理衝突のため不採用 — U9 D-U9-10、2026-07-24 確定〕）。Realm Export は全用途で禁止**（U2 §2.7.4 / U8 D-U8-06）|
| **CloudFront** | **Multi-Origin Failover**（自動）+ 全 Acct 共通 |
| **Route 53** | **Health Check + Failover Routing**（DNS TTL 30 秒）|
| **ROSA HCP / Lambda / Step Functions** | **両 Region に IaC で配置**、DR Region は最小構成（U8 §8.6.1）|
| **Failover 自動化** | **Tier 0/1 障害は自動**（CloudFront Origin Failover / Route 53）/ **データ層は手動承認**（Split-Brain 防止）|
| **Failback** | **手動承認必須**、データ整合性確認後 |
| **DR 訓練** | **半期 Game Day**（[ADR-044](044-tabletop-exercise-incident-drill.md) S-07 シナリオ）|

---

## A. RTO / RPO 階層

### A.1 顧客 Tier 別目標

| 顧客 Tier | RTO | RPO | 適用条件 |
|---|---|---|---|
| **Tier 1 Premium**（規制業種）| **30 分** | **1 分** | 金融 / 医療 / 公的機関 / DORA 適用顧客。**Phase 1 は提供しない（パイロットライトでは不成立、Hot Standby 別方式検討要 — Phase 2、U8 §8.4.4）** |
| **Tier 2 Standard**（一般 B2B）| **1 時間** | **1 分** | デフォルト |
| **Tier 3 Best Effort**（小規模）| **4 時間** | **15 分** | 試験運用 / PoC 顧客 |

### A.2 障害種別 × RTO/RPO

| 障害種別 | 影響範囲 | Failover 手段 | RTO | RPO |
|---|---|---|---|---|
| **単一 AZ 障害** | 1 AZ | Multi-AZ 自動 | < 1 分 | 0 |
| **ROSA HCP クラスタ障害** | Pod 全停止 | Machine Pool 自動置換 + jdbc-ping 再編 | 5-15 分 | 0 |
| **Aurora Primary 障害** | DB 書込不可 | Aurora Multi-AZ Failover | < 1 分 | 0 |
| **Keycloak Realm 破損**（論理破壊）| 認証不可 | **Aurora PITR + 差分 IaC 再生**（手動承認、U8 §8.3.1 経路 2）| 1 - 2 時間 | **5 分（PITR 粒度。旧 24 時間から大幅改善**、2026-07-23 改訂）|
| **Region 完全障害** | 全停止 | DR Region Failover（手動承認）| 30 分 - 1 時間 | < 1 分 |
| **CloudFront 障害**（[ADR-039](039-centralized-network-account-edge-layer.md)）| 全 Inbound 停止 | Origin Failover / DNS Failover | 5-15 分 | 0 |
| **KMS Region 障害** | 暗号化操作不可 | MRK Cross-Region | < 1 分 | 0 |
| **DDoS** | 性能低下 | Shield + WAF Rate Limit | リアルタイム | 0 |
| **Ransomware** | データ破壊 | Backup Restore + 監査 | 4-24 時間 | 〜24 時間 |

---

## B. データ層 DR 設計

### B.1 Aurora Global Database

```mermaid
flowchart TB
    subgraph Primary["プライマリ ap-northeast-1"]
        AuroraP[Aurora Primary Writer<br/>+ Reader x 2]
    end

    subgraph DR["DR ap-northeast-3"]
        AuroraDR[Aurora Secondary<br/>Read-Only<br/>Reader x 1（Warm）]
    end

    AuroraP -.|< 1 sec lag<br/>Storage-level Replication| AuroraDR

    subgraph Failover["Failover 時"]
        AuroraDRPromoted[Aurora Secondary<br/>→ Promoted to Primary<br/>RTO < 1 分（Managed Failover）]
        AuroraDR -.|Promote| AuroraDRPromoted
    end

    style Primary fill:#fff3e0
    style DR fill:#e3f2fd
    style Failover fill:#ffcdd2
```

#### 設定（Terraform 例）

```hcl
resource "aws_rds_global_cluster" "keycloak_idp" {
  global_cluster_identifier = "keycloak-idp-global"
  engine                    = "aurora-postgresql"
  engine_version            = "16.4"
  database_name             = "keycloak"
  storage_encrypted         = true
}

# プライマリ Region
resource "aws_rds_cluster" "primary" {
  provider                  = aws.tokyo
  cluster_identifier        = "keycloak-idp-primary"
  global_cluster_identifier = aws_rds_global_cluster.keycloak_idp.id
  engine                    = "aurora-postgresql"
  engine_version            = "16.4"
  kms_key_id                = aws_kms_key.auth_aurora_mrk.arn  # MRK (ADR-045)
  master_username           = "keycloak_admin"
  manage_master_user_password = true
  backup_retention_period   = 35
  preferred_backup_window   = "16:00-17:00"
}

# DR Region
resource "aws_rds_cluster" "secondary" {
  provider                  = aws.osaka
  cluster_identifier        = "keycloak-idp-secondary"
  global_cluster_identifier = aws_rds_global_cluster.keycloak_idp.id
  engine                    = "aurora-postgresql"
  engine_version            = "16.4"
  kms_key_id                = aws_kms_alias.auth_aurora_mrk_osaka.arn  # 同 MRK の Osaka エイリアス
  depends_on                = [aws_rds_cluster.primary]
}
```

#### 月額コスト試算（10M MAU）

| 項目 | プライマリ | DR | 月額 |
|---|---|---|---|
| Aurora db.r7g.xlarge × 3（Primary Writer + 2 Reader）| ✅ | — | $1,500 |
| Aurora db.r7g.xlarge × 1（DR Reader、Warm）| — | ✅ | $500 |
| ストレージ | 1 TB | 1 TB（同期）| $200 |
| Cross-Region Data Transfer | — | 10 GB/日 想定 | $80 |
| **合計** | | | **〜$2,280/月** |

### B.2 DynamoDB Global Tables

```hcl
resource "aws_dynamodb_table" "itdr_history" {
  name             = "itdr-login-history"
  billing_mode     = "PAY_PER_REQUEST"
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  hash_key  = "user_id"
  range_key = "timestamp"

  attribute { name = "user_id"; type = "S" }
  attribute { name = "timestamp"; type = "S" }

  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.auth_dynamodb_mrk.arn  # MRK
  }

  replica {
    region_name = "ap-northeast-3"  # Osaka DR
    kms_key_arn = aws_kms_alias.auth_dynamodb_mrk_osaka.arn
  }
}
```

#### 注意点

- **書込競合**：Last-Writer-Wins、ITDR / Adaptive Auth は append-only なので競合最小
- **eventually consistent**：通常数秒以内、Region 間 lag < 1 sec
- **コスト**：Replica 分のストレージ + Cross-Region 転送

### B.3 S3 Cross-Region Replication

```hcl
resource "aws_s3_bucket_replication_configuration" "audit_logs" {
  bucket = aws_s3_bucket.audit_logs.id
  role   = aws_iam_role.replication.arn

  rule {
    id     = "audit-logs-to-osaka"
    status = "Enabled"
    filter { prefix = "" }

    source_selection_criteria {
      sse_kms_encrypted_objects { status = "Enabled" }
    }

    destination {
      bucket        = aws_s3_bucket.audit_logs_dr.arn
      storage_class = "STANDARD"
      encryption_configuration {
        replica_kms_key_id = aws_kms_key.audit_logs_mrk_osaka.arn
      }
      replica_modifications {
        status = "Enabled"  # メタデータ変更も Replication
      }
      metrics {
        status = "Enabled"
        event_threshold { minutes = 15 }
      }
    }
  }
}
```

| バケット | RPO 目標 |
|---|---|
| 監査ログ（[ADR-040 / 045](045-cryptographic-key-management-strategy.md)）| 15 分（CRR デフォルト 99%）|
| SPA bundle（アカウント設定画面 / サービス選択画面 / ユーザ管理画面 / Sorry）| 即時（デプロイ時両 Region）|
| DSAR Export 一時保管 | 15 分 |
| Glacier 長期保管 | 24 時間（コスト最適化）|

---

## C. Keycloak 構成・データの復元戦略（2026-07-23 U8 正式改訂）

> **本節は基本設計 [U8 §8.2.2 / §8.3 / §8.5](../basic-design/08-availability-dr-design.md) で全面改訂された**。旧「GitOps + Realm Export 日次自動 → S3 → DR Import」は 1000+ IdP 環境で不成立（realm representation 30MB 級、keycloak#14851。U2 §2.7.4 で realm 全体 export/import は全用途禁止）のため**全廃**。以下は決定 + 要約であり、手順・数値の詳細は U8 が SSOT。

### C.1 戦略選定（改訂後）

| 案 | 評価 | 採否 |
|---|---|---|
| **A. Active-Active**（両 Region で同時 Live、Aurora Global で同期）| データ整合性課題、Split-Brain リスク大 + 東阪レイテンシは公式要件（<10ms）上限で保証不能 | ❌ |
| **B. Active-Passive + Aurora Global + Realm Export 日次**（旧採用案）| Realm Export が 1000+ IdP で不成立（U2 §2.7.4 全面禁止）| ❌ **廃止（2026-07-23）** |
| **C. Keycloak External-Site Replication**（Keycloak ネイティブ Cross-DC）| 設計複雑、運用負荷大、適用例少ない。multi-cluster v2 の簡素化（外部 Infinispan 撤廃）に逆行 | ❌ |
| **D. DB 同期のみ、IaC なし** | 論理破壊（Realm 誤削除・不正変更）時の復元経路がない | ❌ |
| **E. Aurora Global 一体復元 + IaC 再適用（Git SSOT）**（U8）| realm 構成は DB に一体複製 → リージョン障害は Promote のみ。論理破壊は PITR + 差分 IaC 再生 | ✅ **採用（U8 D-U8-06）** |

### C.2 復元 2 経路（決定要約 — 詳細は [U8 §8.3](../basic-design/08-availability-dr-design.md)）

**Keycloak の realm 構成（Clients / IdP / Flow / Org）はすべて DB に格納されるため、Aurora Global DB がユーザデータと構成データを一体で複製する** — この事実が旧 Realm Export 戦略を不要にする中核:

| 復元経路 | 対象障害 | 手段 | 構成の SSOT | RPO |
|---|---|---|---|---|
| **経路 1: リージョン障害** | 東京全損・Aurora Primary 到達不能 | **Aurora Global DB Promote のみ**（大阪 KC は昇格後の DB を読むだけ、構成再投入は一切不要）| Aurora（= Git と一致していることをドリフト検知で担保、U8 §8.3.2）| < 1 分 |
| **経路 2: 論理破壊** | Realm 誤削除・構成破損・ランサムウェア・不正変更 | **(a) Aurora PITR**（粒度 5 分 / 保持 35 日）で破壊直前へ巻き戻し + **(b) 差分（破壊時刻以降の正当変更）のみ IaC 再適用で再生** | **Git**（Terraform + テナント宣言ファイル）| **5 分**（旧 24 時間から大幅改善）|

### C.3 IaC の 2 層構成（旧「keycloak provider で全 Realm IaC 化」は削除）

- **基盤層 = Terraform**（Realm 設定 / Flow / SPI 配備 / 共通 Scope、単一 state）
- **テナント層 = 自作オンボーディング API による Admin API 差分適用に一本化**（テナント単位宣言ファイル。keycloak-config-cli は K-1〔realm representation 禁止〕と原理衝突のため不採用 — [U9 D-U9-10](../basic-design/09-operations-observability-design.md)、2026-07-24 確定）— 該当テナントのみ再生
- 「全 1000+ IdP を Git から一括再生」は行わない（Admin API 負荷 + 時間の点で非現実的）。**PITR 主・IaC 再生は差分限定**（U8 §8.3.1）
- 成立条件 = Git ⇔ 稼働 KC のドリフト検知（日次 CI、Break-Glass 直接変更は事後 Git 反映必須 — U8 §8.3.2）

### C.4 Session データの DR 戦略（→ [U8 §8.5](../basic-design/08-availability-dr-design.md)）

**リージョンフェイルオーバー時、全ユーザーは再認証となることを製品仕様として明文化**（U8 D-U8-10）:
- **Access Token / Refresh Token / SSO セッションは失効許容**（KC 26 Persistent user sessions による継続は保証しないアップサイド）
- **WebAuthn Resident Key / TOTP Secret は永続**（Aurora 経由で DR Region でも有効）
- → 「再ログインのみで業務再開可能」（フェデユーザーは顧客 IdP セッションが生きていればパスワード再入力なし）と顧客に説明

---

## D. Network Acct（ADR-039）の Failover

> 2026-07-23: 本節以降の図・表の「EKS Keycloak Replicas 6 / Replicas 1 → 6」表記は **ROSA HCP Machine Pool + KC CR replicas（DR 側は replicas=0 → 3+）** に読み替え確定（U8 §8.4.2 / §8.6。図の描き替えは省略）。

### D.1 CloudFront Multi-Origin Failover

```mermaid
flowchart TB
    User[ユーザー]
    R53[Route 53<br/>Health Check + Failover Routing<br/>TTL 30 秒]
    CFP[CloudFront Distribution<br/>Primary]
    CFD[CloudFront Distribution<br/>DR(同設定)]

    subgraph Auth1["プライマリ ap-northeast-1"]
        ALBP[ALB（Auth）]
        EKSP[EKS Keycloak<br/>Replicas 6]
    end

    subgraph Auth2["DR ap-northeast-3"]
        ALBD[ALB（Auth DR）]
        EKSD[EKS Keycloak<br/>Replicas 1 → 6（Failover）]
    end

    User --> R53
    R53 -->|Health OK| CFP
    R53 -.Failover.-> CFD
    CFP --> ALBP
    CFP -.|Origin Failover| ALBD
    CFD --> ALBD
    ALBP --> EKSP
    ALBD --> EKSD

    style Auth1 fill:#fff3e0
    style Auth2 fill:#e3f2fd
```

#### CloudFront Origin Group

```hcl
resource "aws_cloudfront_distribution" "auth" {
  origin_group {
    origin_id = "auth-group"
    failover_criteria {
      status_codes = [403, 404, 500, 502, 503, 504]
    }
    member { origin_id = "primary-alb" }
    member { origin_id = "dr-alb" }
  }
  # ...
}
```

### D.2 Route 53 Health Check + Failover

```hcl
resource "aws_route53_health_check" "auth_primary" {
  fqdn              = "auth-primary.basis.example.com"
  port              = 443
  type              = "HTTPS"
  resource_path     = "/health"
  failure_threshold = 3
  request_interval  = 10
}

resource "aws_route53_record" "auth" {
  zone_id = data.aws_route53_zone.basis.zone_id
  name    = "auth.basis.example.com"
  type    = "A"

  failover_routing_policy { type = "PRIMARY" }
  set_identifier  = "primary"
  health_check_id = aws_route53_health_check.auth_primary.id

  alias {
    name                   = aws_cloudfront_distribution.auth.domain_name
    zone_id                = aws_cloudfront_distribution.auth.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "auth_secondary" {
  # ... SECONDARY type で DR CloudFront を指す
}
```

### D.3 WAF / Shield / Turnstile の DR

| サービス | DR 戦略 |
|---|---|
| **AWS WAF**（[ADR-039](039-centralized-network-account-edge-layer.md)）| グローバル（CLOUDFRONT scope）、Region 障害の影響なし |
| **AWS Shield Advanced** | グローバル |
| **Cloudflare Turnstile**（[ADR-042](042-bot-detection-captcha.md)）| Cloudflare 側で Multi-Region、本基盤側 Failover 不要 |
| **Lambda@Edge** | グローバル分散実行 |
| **AWS WAF Captcha**（Turnstile フォールバック）| グローバル |

---

## E. Failover 自動化 vs 手動承認

### E.1 自動化基準

| 障害種別 | 自動 / 手動 | 理由 |
|---|---|---|
| 単一 AZ / Multi-AZ Failover | **自動** | AWS Managed |
| Aurora Primary Failover（同 Region 内）| **自動** | RDS Managed |
| CloudFront Origin Failover（同 Acct）| **自動** | CloudFront Managed |
| Route 53 Health Check Failover | **自動** | DNS レベル |
| Pod / Container 自動復旧 | **自動** | ROSA HCP（Machine Pool 自動置換 + jdbc-ping 再編、Red Hat SRE 管理）|
| **Aurora Global Promote（Cross-Region）** | **手動承認** | Split-Brain 防止 |
| **DR Region 全体 Failover** | **手動承認** | 影響範囲大 |
| **経路 2 発動（PITR + 差分 IaC 再生、論理破壊時）** | **手動承認** | 誤動作 Restore 防止（旧「Realm 設定 Restore」を置換 — U8 D-U8-06）|
| **Failback**（プライマリ復旧後） | **手動承認** | データ整合性確認後 |

### E.2 手動承認フロー（Aurora Cross-Region Promote 例）

```mermaid
sequenceDiagram
    actor SRE as SRE Lead
    participant Slack
    participant PD as PagerDuty
    actor IR as IR Lead
    actor CTO
    participant Runbook
    participant AWS

    Slack->>PD: Region 障害アラート（自動）
    PD->>SRE: Page
    SRE->>Slack: 状況確認
    SRE->>IR: War Room 招集
    IR->>CTO: 経営報告
    CTO->>IR: Failover 承認
    IR->>Runbook: Runbook 起動
    Runbook->>SRE: Step 1-N（手動 + コマンド）
    SRE->>AWS: Aurora Global Promote
    AWS-->>SRE: Promoted（< 1 分）
    SRE->>AWS: Route 53 Failover Manual Override
    SRE->>Slack: Failover 完了通知（顧客向け）
```

### E.3 Runbook の事前準備

| Runbook | 内容 |
|---|---|
| **RB-DR-00 リージョン障害判定チェックリスト**（2026-07-23 新設）| 判定材料 2 系統以上該当で「リージョン障害」宣言 → 承認プロセスへ（承認 SLA 15 分、U8 §8.4.1）|
| **RB-DR-01 Aurora Global Promote** | Step by Step + コマンド + ロールバック手順（Broker / IdP-KC 2 系統並行実行）|
| **RB-DR-02 Route 53 / エッジ切替** | Health Check Override + TTL 短縮 + **他組織エッジのオリジン切替連絡手順（REQ-DR-02、U8 §8.4.5）**（2026-07-23 追加）|
| **RB-DR-03 ROSA HCP DR Region Scale Up** | Machine Pool 2 → 6 ノード + KC CR replicas 0 → 3+ + 動作確認（旧 EKS Replica 1 → 6 を置換）|
| **RB-DR-04' PITR + 差分 IaC 再生**（旧 RB-DR-04 Keycloak Realm Restore を置換）| Aurora PITR 巻き戻し + 破壊時刻特定（Admin Events + 監査ログ）+ 差分 IaC 再生（U8 §8.3.1 経路 2）|
| **RB-DR-05 Failback** | DR → Primary 切戻し（計画 Switchover・RPO 0。**禁止 3 操作を冒頭に明記** — U8 §8.7.1）|

各 Runbook は Git 管理 + 演習で動作検証（[ADR-044](044-tabletop-exercise-incident-drill.md) Game Day）。

---

## F. DR 訓練（Game Day、ADR-044 連動）

### F.1 演習スケジュール

| 演習 | 頻度 | 内容 |
|---|---|---|
| **S-07 Region 障害**（[ADR-044](044-tabletop-exercise-incident-drill.md)）| 半期 | Tokyo 完全停止想定、Osaka へ Failover、RTO/RPO 計測 |
| **S-08 Aurora 破壊**（Ransomware 想定）| 年 1 | **PITR + 差分 IaC 再生（RB-DR-04'）** + 監査 |
| **RB-DR-00〜05 Runbook 検証** | 半期 | 各 Runbook が動作可能か検証（RB-DR-04' 含む）|
| **Failback 訓練** | 半期 | 切戻し手順の検証 |

### F.2 評価 KPI

| KPI | 目標 |
|---|---|
| 演習 RTO 達成率 | 90%+ |
| 演習 RPO 達成率 | 100% |
| Runbook 完走率 | 100% |
| AAR Action Items 90 日完了率 | 100% |

---

## G. コスト試算

### G.1 月額（10M MAU、DR 込）

| 項目 | プライマリ単独 | DR 込 | 差額 |
|---|---|---|---|
| Aurora（Primary Writer + 2 Reader + DR Reader 1）| $1,500 | $2,000 | +$500 |
| Aurora Storage + Cross-Region | $200 | $280 | +$80 |
| DynamoDB Global Tables（Replica）| $500 | $750 | +$250 |
| S3 Cross-Region Replication | $30 | $100 | +$70 |
| ROSA HCP 4 クラスタ（東京 Broker/IdP-KC 2 + 大阪パイロットライト 2）（2026-07-23 改訂: EKS 行を置換）| ≈ $1,430 | **≈ $2,032** | +$602 |
| Route 53 Health Check | $0 | $20 | +$20 |
| Lambda + Step Functions（両 Region 配置）| $300 | $400 | +$100 |
| KMS MRK | $250 | $400 | +$150 |
| Network Acct 共通 | $500 | $500 | $0 |
| **合計** | **〜$4,710/月** | **〜$6,480/月** | **+$1,770/月** |

- ROSA HCP 実額は **[U6 §6.2.3 v1.2](../basic-design/06-infra-network-design.md) が SSOT**（4 クラスタ ≈ **$2,032/月**、infra Pool 別建て込み。大阪パイロットライト 2 クラスタ ≈ $602/月 込み）。
- → **DR 追加コスト 約 +38%**（業界標準範囲。旧 EKS 前提の「約 30% 増」から更新）。

### G.2 規制業種 Tier 1（RTO 30 分）追加コスト

> **2026-07-23 改訂**: Tier 1 は **Phase 2 検討**（Phase 1 は提供しない）。Hot Standby は **Aurora Global Secondary read-only 制約により「大阪 KC 常時稼働」がそのままでは成立せず方式再検討要**（U8 §8.4.4）。以下の試算は旧 EKS 前提の参考値であり、Phase 2 検討時に再試算する。

| 項目 | 追加（参考値・要再試算）|
|---|---|
| DR Region Hot Standby（方式再検討要 — read-only 制約、Phase 2）| +$2,000/月 |
| Aurora DR Reader 増（× 2）| +$500/月 |
| **Tier 1 追加合計** | **+$2,500/月** |

---

## H. RTO/RPO 達成シミュレーション（2026-07-23 U8 改訂）

> 詳細タイムラインは **[U8 §8.4.2](../basic-design/08-availability-dr-design.md) が SSOT**。旧 40 分想定に対し、KC 起動遅延（JVM + キャッシュ）と**他組織エッジ調整**を織り込んだ worst-case 積み上げに更新。

### H.1 Tokyo 完全障害シナリオ（worst-case 積み上げ・要約）

| 時刻 | トラック | アクション |
|---|---|---|
| T+0〜3 | 検知 | 外形監視・R53 Health Check 異常 → 複合アラーム確定 → SRE Lead。静的資産（Sorry/SPA）は CloudFront Origin Failover で先行部分復旧 |
| T+3〜20 | 判断 | RB-DR-00 判定 + War Room 招集 + CTO 承認（承認 SLA 15 分、worst 20 分）|
| T+20〜25 | A: DB | RB-DR-01: Aurora Global unplanned Managed Failover × 2 系統（Broker / IdP-KC 並行）|
| T+20〜35 | B: 基盤（A と並行）| RB-DR-03: 大阪 Machine Pool スケールアップ 2 → 6 ノード（HCP ノード供給 12-15 分）|
| T+25〜38 | A→B 合流 | KC CR replicas 0 → 3+（昇格済み Writer へ接続、イメージは ECR レプリケーション済み・pre-pull）|
| T+38〜45 | 検証 | ログイン（フェデ/ローカル）、JWKS 応答・kid 一致、token/refresh、Broker→IdP-KC PrivateLink 疎通、`idmap` 参照 |
| T+45〜50 | DNS/エッジ | RB-DR-02: Route 53 Failover（TTL 30s）+ **他組織エッジのオリジン切替**（事前設定 Origin Group なら自動 / 手動なら REQ-DR-02 SLA ≤ 10 分）|
| **T+50** | 完了 | 全面切替宣言・顧客通知。**バッファ 10 分** |

→ **Tier 2 RTO 1h は「条件付き成立」**（worst 50 分 + バッファ 10 分）。成立条件 5 点: ①承認 T+20 まで完了 ②大阪 EC2 在庫・vCPU クォータ事前確保（G-OSAKA）③ECR 東西レプリケーション + pre-pull ④**他組織エッジ切替が自動 or SLA ≤ 10 分（REQ-DR-01〜03）** ⑤PrivateLink 大阪側事前複製 — いずれか欠落で不成立（U8 §8.4.3 D-U8-09）。

### H.2 Tier 1（RTO 30 分）は Phase 1 では不成立

積み上げ上、T+20 承認 + T+35 ノード供給の時点で 30 分を超過する。Tier 1 は Hot Standby 必須だが Aurora Secondary read-only 制約により別方式検討が必要 → **Phase 2 検討**（規制業種顧客の契約要求発生時、U8 §8.4.4）。旧「Hot Standby なら 25 分達成」試算は削除。

---

## I. 代替案検討

| 案 | 評価 | 採否 |
|---|---|---|
| **A. Multi-AZ のみ、DR なし** | Region 障害で全停止、規制違反 | ❌ |
| **B. Active-Active Multi-Region** | Split-Brain リスク大、運用負荷大、東阪レイテンシ保証不能 | ❌ |
| **C. Active-Passive パイロットライト（インフラ Warm + KC Scale 0）+ Aurora Global**（本 ADR、2026-07-23 改訂。旧 Warm Standby（KC Scale 1）は read-only 制約で不成立）| RTO 1h 条件付き成立（§H）、業界標準 | ✅ 採用 |
| **D. Pilot Light（インフラも都度構築する最小 Standby）** | RTO 数時間、Tier 2 目標未達（本 ADR の「パイロットライト」= インフラ Warm + KC Scale 0 とは別物 — U8 D-U8-07）| ❌ |
| **E. Hot Standby（大阪 KC 常時稼働）** | コスト 2 倍 + Aurora Secondary read-only 制約で方式再検討要 | △ Tier 1 向け Phase 2 検討 |
| **F. Cross-Cloud DR（AWS + GCP）** | 運用負荷膨大、Lock-in 緩和効果限定 | ❌ |
| **G. Backup-only Restore** | RPO 数時間、Tier 2 目標未達 | ❌ |

---

## J. Consequences

### Positive

- **SOC 2 A1.2 / PCI DSS §12.10 / ISO 22301 / DORA を 1 つの設計で同時充足**
- **Tier 2 RTO 1 時間（条件付き成立）/ RPO 1 分**（標準。Tier 1 は Phase 2 検討）
- **Aurora Global Database + DynamoDB Global Tables + S3 CRR + KMS MRK**で完全 Cross-Region
- **CloudFront Multi-Origin Failover** + **Route 53 Failover** で自動化 80%
- **realm 構成も Aurora Global で RPO < 1 分同期**（Realm Export 廃止で運用負荷減 + Git SSOT ドリフト検知で整合性担保 — 2026-07-23 改訂）
- **論理破壊時 RPO 5 分**（PITR 粒度。旧 Realm Export 前提の 24 時間から大幅改善）
- DR 訓練（Game Day 年 2 回）で**Runbook 実効性検証**

### Negative

- **DR 追加コスト 約 +38% 増**（月 +$1,770、ROSA 実額ベース — 2026-07-23 更新）
- Tier 1 は Phase 2 検討（Hot Standby 方式再検討 + コスト再試算要）
- **Active-Active 不採用**で書込競合の不安定さは回避するが、DR 切替に手動承認必要
- **Failback の運用負荷**（プライマリ復旧後のデータ整合性確認 + 禁止 3 操作の統制）
- **DR 切替最終段（エッジ）が他組織依存**（P-18。REQ-DR-01/02 未合意時は RTO 1h 非保証 → 顧客 SLA 文言修正が必要、U8 O-U8-1 — 2026-07-23 追加）

### Neutral

- Active-Active は将来の Phase 4 候補（Keycloak Cross-DC 機能が成熟次第）
- 顧客個別 Region 要件（EU 顧客の eu-west-1 等）は別途検討、本 ADR は国内顧客前提

### 我々のスタンス

| 基本方針の柱 | DR 設計での実現 |
|---|---|
| **絶対安全** | Multi-Region Active-Passive + 規制適合 + 半期演習 |
| **どんなアプリでも** | 全アプリ層が DR Region で稼働可能、Failover 透明 |
| **効率よく認証** | Aurora Global で RPO 1 分、再ログイン許容で UX 影響最小 |
| **運用負荷・コスト最小** | Active-Passive で運用負荷最小、コスト +30% で業界標準 |

---

## 参考資料

### AWS / 業界

- [AWS Disaster Recovery of Workloads on AWS](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-workloads-on-aws.html)
- [AWS Well-Architected Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html)
- [Aurora Global Database](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-global-database.html)
- [DynamoDB Global Tables](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GlobalTables.html)
- [Route 53 Health Checks and DNS Failover](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/dns-failover.html)
- [CloudFront Origin Failover](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/high_availability_origin_failover.html)
- [AWS Game Days](https://aws.amazon.com/gameday/)

### Keycloak

- [Keycloak Cross-DC Setup](https://www.keycloak.org/server/caching)
- [Keycloak Backup & Restore](https://www.keycloak.org/server/importExport)

### 規制 / フレームワーク

- [SOC 2 Type II A1.2 — System Availability](https://www.aicpa-cima.com/)
- [ISO 22301 Business Continuity](https://www.iso.org/standard/75106.html)
- [ISO 27001 A.5.29-30 ICT 継続性](https://www.iso.org/)
- [EU DORA Regulation](https://www.eiopa.europa.eu/digital-operational-resilience-act-dora_en)
- [NIST SP 800-34 Rev 1 Contingency Planning Guide](https://csrc.nist.gov/publications/detail/sp/800-34/rev-1/final)
- [PCI DSS v4.0 §12.10 IR + BCP](https://www.pcisecuritystandards.org/document_library/)
