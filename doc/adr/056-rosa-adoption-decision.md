# ADR-056: ROSA (Red Hat OpenShift Service on AWS) 採用判断

- **ステータス**: Proposed（要件定義フェーズでヒアリング結果を踏まえ Accepted / Rejected に確定予定）
- **日付**: 2026-06-25
- **関連**:
  - **[reference/rosa-detailed-analysis.md](../reference/rosa-detailed-analysis.md)** — **本 ADR の input source（詳細事実集約）**
  - [ADR-006 Cognito vs Keycloak コスト損益分岐](006-cognito-vs-keycloak-cost-breakeven.md)
  - [ADR-008 Keycloak start-dev for PoC](008-keycloak-start-dev-for-poc.md)
  - [ADR-015 RHBK validation deferred](015-rhbk-validation-deferred.md)
  - [reference/rhbk-support-and-pricing.md](../reference/rhbk-support-and-pricing.md)
  - [reference/keycloak-upstream-vs-rhbk.md](../reference/keycloak-upstream-vs-rhbk.md)
  - [requirements/rhbk-vendor-inquiry.md](../requirements/rhbk-vendor-inquiry.md) — Red Hat / リセラ照会
  - [§C-2 プラットフォーム選定](../requirements/proposal/common/02-platform.md)

---

## Context

### 背景

RHBK (Red Hat build of Keycloak) を商用サポート付きで動かす場合の**実行基盤候補**として ROSA (Red Hat OpenShift Service on AWS) が候補に上がった。ROSA は AWS と Red Hat が共同設計・サポートするマネージド OpenShift で、RHBK の第一級サポート対象。

本基盤の PoC は **ECS Fargate + RDS PostgreSQL** で稼働中（[Phase 1-9](../requirements/poc-summary-evaluation.md) + [Stage A 完了](../common/phase10-stage-a-verification.md)）。本番採用にあたり RHBK 商用サポート利用を検討する場合、**ECS Fargate での RHBK サポート対象可否が不明確**であり、その代替として ROSA への移行が検討材料となる。

### Why 本 ADR が必要

「RHBK 採用するか / どこで動かすか」の判断は以下の 4 要素に分岐する:

1. **そもそも RHBK 必須か**（Upstream Keycloak OSS で要件満たせるか）
2. RHBK 必須の場合、**どの実行基盤を選ぶか**:
   - **ROSA**（HCP / Classic）
   - **EKS / EKS Fargate**
   - **EC2 RHEL 9 + Podman / Docker**
   - **ECS Fargate**（サポート対象不明）
   - **OCP オンプレ**
3. 採用する場合の**コスト・移行工数**は妥当か
4. **Stage A の Terraform 投資**との整合性

本 ADR は **ROSA という選択肢に絞った採用判断** を記録する。EKS / EC2 RHEL 等の他選択肢は別途 ADR で扱う（または本 ADR の Alternatives セクションで簡潔に並列）。

### 詳細事実

ROSA の概要・アーキテクチャ・価格・SLA・本基盤での移行考慮の詳細は **[reference/rosa-detailed-analysis.md](../reference/rosa-detailed-analysis.md)** に集約。本 ADR は判断記録に集中する。

参照ハイライト:

| トピック | 参照 |
|---|---|
| ROSA Classic vs HCP の違い | [rosa-detailed-analysis.md §2](../reference/rosa-detailed-analysis.md) |
| 価格モデル詳細（Service Fee / EC2 / HCP Cluster Fee）| [§3](../reference/rosa-detailed-analysis.md) |
| 本基盤での月額試算（HCP 3y RI = ~$590/月、Classic = ~$989/月）| [§4](../reference/rosa-detailed-analysis.md) |
| SLA 99.95% + Shared Responsibility | [§5](../reference/rosa-detailed-analysis.md) |
| RHBK との統合（Operator / サブスク統合）| [§8](../reference/rosa-detailed-analysis.md) |
| 移行工数 6-8 週間 | [§9](../reference/rosa-detailed-analysis.md) |
| 採用判断フレーム | [§10](../reference/rosa-detailed-analysis.md) |
| **コントロールプレーンに入る情報とコンプライアンス影響（PCI DSS / APPI）** | **[§11](../reference/rosa-detailed-analysis.md#11-コントロールプレーンに入る情報とコンプライアンス影響pci-dss--appi)** |

---

## Decision

### 採用方針（Proposed）

**本基盤の現状要件では ROSA 採用の必然性が薄く、Default は採用しない**。

ただし以下の条件が満たされた場合に**採用判断を再評価**する:

| 条件 | 該当性確認方法 |
|---|---|
| **FIPS 140-2 / HIPAA / FedRAMP / ISMAP-Hi 等の規制要件が顧客に発生** | 要件定義 Phase B / C のヒアリング |
| **MAU 想定が 10M を超え、Keycloak HA + Multi-Region DR が大規模化** | [ADR-006 損益分岐](006-cognito-vs-keycloak-cost-breakeven.md) 再評価 |
| **複数 Red Hat ミドルウェア（RHBK + JBoss EAP + OpenShift AI 等）を統合運用したい** | プロジェクト全体スコープに依存 |
| **Red Hat と RHBK + ROSA 統合サブスク見積を取得し、TCO が許容範囲** | リセラ照会（[rhbk-vendor-inquiry.md Q7+Q8](../requirements/rhbk-vendor-inquiry.md)）|

### 採用時のコンプライアンス追加要件（PCI DSS / APPI）

HCP モデルではコントロールプレーンが **Red Hat 所有 AWS アカウント内**で動くため、採用時は以下を必須化する（詳細は [rosa-detailed-analysis.md §11](../reference/rosa-detailed-analysis.md#11-コントロールプレーンに入る情報とコンプライアンス影響pci-dss--appi)）:

| 規制 | ROSA HCP 採用時の追加要件 |
|---|---|
| **PCI DSS v4.0.1** | Red Hat AOC 年次取得 + §12.8 / §12.9 文書化 + CHD 非流入設計維持 + BYOK 適用 |
| **APPI** | Red Hat との DPA に法第 28 条「相当措置」相当の規定 + SRE 越境アクセスログ取得 + 個人データ非流入設計維持 + 委託先公表 |
| **共通設計原則** | K8s Secret に個人データを直接保存しない（鍵のみ）/ 個人データはアプリ DB（顧客 VPC 内）/ Aurora KMS は CMK (BYOK) |

**前提**: 「**個人データ・CHD 本体は etcd に入らない**」設計（K8s Secret には鍵類のみ、個人データはアプリ DB に閉じ込め）を維持できれば ROSA HCP は PCI DSS / APPI スコープ内クラスタとして許容される。

### 採用する場合の構成（参考）

ROSA を採用する場合の前提:

| 項目 | 構成 |
|---|---|
| **形態** | **ROSA HCP**（Classic より 30-50% 安く、新規推奨）|
| **リージョン** | ap-northeast-1 (東京) + (任意) ap-northeast-3 (大阪) で Multi-Region DR |
| **クラスタ構成** | Worker 3 ノード (m5.xlarge) × Multi-AZ |
| **DB** | Aurora PostgreSQL Multi-AZ（ROSA 外、PrivateLink 経由）|
| **RHBK** | OperatorHub から RHBK Operator install、`Keycloak` CR で realm 管理 |
| **コスト目安** | **約 $590-690/月** (3y RI、Aurora 含む) |
| **移行工数** | **6-8 週間**（Stage A Terraform 全面書き換え）|

### 採用しない場合の代替案（Default）

| 案 | 内容 | コスト | サポート |
|---|---|---|---|
| **A. Upstream Keycloak OSS + ECS Fargate** (現 PoC 構成維持) | 現行構成、Stage A Terraform 適用 | $190/月 | ❌ なし（コミュニティ）|
| **B. Upstream Keycloak OSS + EKS** | EKS Fargate / マネージド Node group | $300-500/月 | ❌ なし |
| **C. EC2 RHEL 9 + RHBK サブスク** | EC2 上で `start --optimized` モード起動 | $300-600/月 + RHBK サブスク | ✅ Red Hat |
| **D. ROSA HCP + RHBK Operator** | フルマネージド | $590-690/月 (3y RI) + 統合サブスク | ✅ 第一級 |

**Default 推奨は A**（現状 PoC 構成 + Stage A Terraform で本番化）。要件定義で RHBK 必須化が判明した場合は **C → D** の順で再評価。

---

## Consequences

### Positive（ROSA 採用しない場合の利点）

- **コスト最小化**: 現 PoC の ECS Fargate $190/月で運用可能
- **Stage A Terraform 投資が無駄にならない**: 既存の ECS / RDS / ALB / VPC Endpoint 構成を本番化可
- **既存チームのノウハウ活用**: AWS-native 運用 (CloudWatch / SSM / Terraform) を継続
- **シンプル**: マルチアカウント戦略・他 AWS リソースとの統合が clean

### Negative（ROSA 採用しない場合のリスク）

- **RHBK 商用サポート対象外の懸念**: ECS Fargate でのサポート可否が公開情報からは未確定（[rhbk-support-and-pricing.md §4.5](../reference/rhbk-support-and-pricing.md)）→ リセラに照会必要
- **規制業界顧客の取りこぼし**: FIPS 140-2 / HIPAA 厳格要件には Upstream OSS では応えにくい
- **将来のスケール時の制約**: 10M MAU + Multi-Region 等の大規模化で ROSA Operator の HA 自動化が魅力的になる可能性

### Compliance（PCI DSS / APPI 観点）

ROSA HCP モデル特有のコンプライアンス影響を整理:

- **PCI DSS v4.0.1**:
  - HCP コントロールプレーン etcd は Red Hat 所有 AWS アカウント内。**CHD 本体は etcd に入らない**設計を維持できればスコープ内クラスタとして許容
  - §12.8 (TPSP 管理) / §12.9 (責任分担マトリクス) → Red Hat AOC 年次取得 + 文書化必要
  - §3.6 / §3.7 (鍵管理) → K8s Secret に乗る JWT 署名鍵に対し Red Hat 側 KMS 暗号化 + BYOK 可否確認必要
- **APPI**:
  - **法第 25 条**（委託先監督）: Red Hat = 委託先扱い、DPA + 監査権規定必要
  - **法第 28 条**（外国第三者提供）★最大論点:
    - データ物理保存地は ap-northeast-1 (東京) → 国内
    - **Red Hat SRE の越境 JIT アクセス**が「外国にある第三者への提供」に該当する可能性
    - 対応: DPA に GDPR SCC 相当条項統合 + SRE 越境アクセスログ取得
  - 個人データ本体（Keycloak users テーブル / セッション）は Aurora（顧客 VPC）に閉じ込め、etcd 非流入設計を維持
- **共通設計原則**: 「K8s Secret に個人データを直接保存しない（鍵のみ）/ 個人データはアプリ DB（顧客 VPC 内）/ Aurora KMS は CMK (BYOK)」を必須化

**Upstream OSS + ECS Fargate (Default)** の場合、ECS タスク + RDS 全て顧客 AWS アカウント内に閉じるため、上記のコントロールプレーン越境論点は**発生しない**（PCI DSS / APPI 評価範囲がシンプル）。

→ 詳細は [rosa-detailed-analysis.md §11](../reference/rosa-detailed-analysis.md#11-コントロールプレーンに入る情報とコンプライアンス影響pci-dss--appi)

### Neutral

- **Stage A Terraform は ECS 前提**: ROSA 採用時は全面書き換えだが、現時点での投資は **本番化に直接効く**
- **将来 ROSA に切り替える選択肢は残る**: 本 ADR で「Default 採用しない」と決めても、要件変化で再評価可能
- **EKS との比較が別途必要**: ROSA 不採用なら EKS（マネージド Kubernetes）も比較対象になる

---

## Alternatives Considered

### Alt 1: ROSA Classic を採用

- 不採用理由: HCP より 50% 高い (~$989/月 vs ~$590/月)、新規導入時に Classic を選ぶ合理性なし
- HCP が 2024 年 GA 後、Red Hat 自身が新規は HCP 推奨

### Alt 2: ROSA HCP を Default で採用

- 判断: 現状要件では **コストが過剰**（ECS の 3-5 倍）
- RHBK 必須化が確定したら再評価

### Alt 3: EKS / EKS Fargate に移行

- 別 ADR で判断（本 ADR スコープ外）
- ROSA より安いが、RHBK サポートは「条件付き」（[KB 7072950](https://access.redhat.com/ja/solutions/7072950)）

### Alt 4: EC2 RHEL 9 + RHBK

- 別 ADR で判断（本 ADR スコープ外）
- ROSA より安く、RHBK 第一級サポート対象
- 運用は手動（systemd / Podman）でやや負荷あり

### Alt 5: Upstream Keycloak OSS + ECS Fargate（現 PoC 構成維持）

- **Default 採用**（本 ADR の Decision に記載）
- RHBK 商用サポートなしでも要件満たせる場合の最安・最シンプル選択肢

---

## Decision に必要なヒアリング項目

要件定義（Phase A / B / C）で以下を確認:

| 項目 | 回答が「Yes」なら… |
|---|---|
| FIPS 140-2 認証が必要な顧客はあるか | **RHBK 必須化 → ROSA / EC2 RHEL 再評価** |
| HIPAA / BAA 必須の医療顧客はあるか | **RHBK 必須化 → ROSA / EC2 RHEL 再評価** |
| 24/7 Premium サポート SLA を契約に含めるか | **Red Hat 商用サポート必要 → ROSA / EC2 RHEL 再評価** |
| 想定 MAU は 10M を超えるか | **大規模 → ROSA Operator 自動 HA が魅力的** |
| 複数 Red Hat ミドルウェアを統合運用予定か | **ROSA 規模効率が出る** |
| Red Hat / リセラから ROSA + RHBK 統合サブスク見積を取れたか | **TCO 試算で再評価可能** |
| 既存 OpenShift 運用経験があるか | **学習コスト軽減 → ROSA 候補度上がる** |
| **PCI DSS スコープ内システムを認証基盤上で扱うか**（CHD 取扱い顧客の有無）| **CHD 非流入設計レビュー必要 → 採用時の追加運用コスト** |
| **APPI 上、Red Hat SRE 越境アクセスが組織として許容可能か**（DPA + GDPR SCC 相当条項で対応可能か）| **法務確認必要、不可なら ROSA Classic（control plane も自社 AWS 内）に変更検討** |

→ これらが全て「No」なら **Upstream Keycloak OSS + ECS Fargate** で本番化が妥当。

---

## Follow-up

### 即時アクション（要件定義フェーズ着手前）

1. **リセラ照会**（[rhbk-vendor-inquiry.md §3.1](../requirements/rhbk-vendor-inquiry.md) の簡略版メール）を送付
   - Q1: ECS Fargate での RHBK サポート可否
   - Q7: ROSA HCP + RHBK 構成での正式見積（新規追加項目）
   - Q8: RHBK サブスクと OCP サブスクの統合可否
   - **期待回答期限**: 2 週間以内

2. **AWS Pricing Calculator で本試算**
   - ROSA HCP 3y RI + Aurora Multi-AZ + Lambda + CloudFront + WAF
   - 比較対象: 現 ECS Fargate 構成 + Aurora
   - 期待: 月額 / 年額 / 3 年 TCO の 3 種

3. **Stage A AWS apply の判断保留**
   - ROSA 採用なら Stage A Terraform は破棄になるため、apply は ROSA 判断確定後
   - ただし要件定義 / ヒアリングで「Upstream OSS で OK」が確定すれば即 apply 可

### 中期アクション（要件定義 Phase B / C）

| Task | 内容 | 工数 |
|---|---|---|
| FIPS / HIPAA 要件ヒアリング | 顧客に規制業界の含有確認 | 1 週間 |
| MAU 規模見込み確定 | 想定 MAU + 成長カーブ | 1 週間 |
| Red Hat 営業との直接打合せ | 統合サブスク条件・実装支援 | 2-4 週間 |
| **PCI DSS / APPI コンプライアンス要件ヒアリング** | CHD 取扱い顧客有無 + APPI 28 条法務確認 + Red Hat AOC 入手経路確認 | 2 週間 |
| ROSA 検証（必要時）| Phase 10 Stage C として AWS Marketplace から ROSA HCP 試用 | 2-3 週間 |

### Decision 昇格条件

本 ADR を Proposed → Accepted / Rejected に昇格する条件:

| 昇格先 | 条件 |
|---|---|
| **Accepted (ROSA 採用)** | リセラ見積取得 + FIPS/HIPAA 要件確定 + コスト承認 + **PCI DSS / APPI 追加要件の整備計画承認** |
| **Rejected (ROSA 不採用 = Default A: Upstream OSS + ECS)** | RHBK 商用サポート不要が確定 + ECS Fargate での Upstream OSS 運用に経営層合意 |
| **Hold (継続判断保留)** | 要件・MAU 規模が固まらず、Phase 10 Stage B 完了まで判断保留 |

---

## Notes

### 本 ADR と関連 ADR の整理

| ADR | 焦点 |
|---|---|
| **ADR-006** | Cognito vs Keycloak コスト損益分岐 (175K MAU) |
| **ADR-015** | RHBK 検証先送り判断 (PoC 段階) |
| **本 ADR-056** | ROSA 採用判断（Default 不採用、条件付き再評価）|
| 別途 ADR 候補 | EC2 RHEL + RHBK 採用判断 |
| 別途 ADR 候補 | EKS 採用判断 |
| 別途 ADR 候補 | Upstream OSS + ECS Fargate 本番化判断 |

### 重要な事実（[rosa-detailed-analysis.md](../reference/rosa-detailed-analysis.md) より）

- ROSA HCP は **2024 年 GA**、Red Hat 公式が新規推奨
- 月額目安 (3y RI、Keycloak HA 想定): **約 $590-690/月**
- 現 PoC ECS Fargate ($190/月) の **3-4 倍コスト**
- ap-northeast-1 (東京) 対応済、ap-northeast-3 (大阪) は要確認
- SLA 99.95%（Red Hat SRE 運用）
- RHBK は ROSA で第一級サポート対象 ([KB 7033107](https://access.redhat.com/articles/7033107))
- 移行工数 **6-8 週間**（Stage A Terraform 全面書き換え必要）
