# U8: 可用性・DR 設計

作成日: 2026-07-23
ステータス: Draft v1（Wave 2）
前提: [01-architecture-baseline.md](01-architecture-baseline.md) **Baseline v1**（特に P-04 SLA 99.9% / P-05 DR Tier 2: RTO 1h・RPO 1min・Active-Passive / P-15 東京+大阪 / P-01 ROSA HCP + RHBK Operator / P-02 10M MAU）
上位文書: [00-basic-design-plan.md](00-basic-design-plan.md) U8
物理配置の前提: [06-infra-network-design.md](06-infra-network-design.md)（D-U6-03/05/07、§6.8.2 の U8 引き渡し）

---

## 8.0 背景・なぜここで決めるか・スコープ

### 8.0.1 背景 — 旧 ADR-051 の前提が 2 点崩れた

[ADR-051](../adr/051-multi-region-dr-failover.md)（2026-06-23 作成）は「Active-Passive Warm Standby + Aurora Global DB」の大枠を定めたが、基本設計 Wave 1 で**前提が 2 点崩れた**:

1. **「Realm Export 日次自動 → S3 → DR Import」戦略の不成立**。P-16（接続 IdP 1000+）環境では realm representation が 30MB 級に達し、realm 全体 export/import は運用として成立しない（keycloak#14851 / [U2 §2.7.4](02-keycloak-logical-design.md) で**全面禁止**が設計制約化済み）。ADR-051 冒頭警告（2026-07-23）のとおり、構成復元は **IaC 再適用（Git SSOT）+ Aurora Global DB** へ差し替える必要がある — **本書がこの正式改訂の設計根拠**であり、§8.8 に「ADR-051 改訂案」を示す。
2. **実行基盤の EKS → ROSA HCP 転換**（ADR-056 逆転、P-01）。大阪 ap-northeast-3 の ROSA HCP 対応が確認され東西対称構成が成立（[research](research/rosa-hcp-adoption-research.md) #2）。さらに KC 26.1 以降 **jdbc-ping がデフォルト**・**multi-cluster v2 で外部 Infinispan 要件が撤廃**され、「同期は Aurora（DB）のみを single source of truth とする」構成に簡素化された（research #8、RHBK 26.4 HA Guide は Aurora PostgreSQL 15-17 を multi-site HA サポート DB に明記）。

加えて、旧 ADR-051 には**実機制約との矛盾**が 1 点ある: 「DR Region Warm Standby（KC Scale 1 で待機）」は、**Aurora Global Secondary が read-only であり Keycloak は起動時に DB 書込を要するため成立しない**（[keycloak-dr-aurora-sync.md §4.1](../reference/keycloak-dr-aurora-sync.md)）。本書で「インフラ Warm + KC Scale 0」のパイロットライトに正式修正する（§8.6、D-U8-07）。

### 8.0.2 本書の位置づけと決定の型

- 本書は §NFR-1（可用性）/ §NFR-5（DR）の要件を、U6 で確定した物理配置（ROSA HCP × 2 クラスタ × 2 リージョン、Aurora Global 2 系統）の上で**手順・数値・成立性検証まで**落とす。
- 決定は D-U8-nn、他組織（NW 監査 Acct 管理者）への要求は REQ-DR-nn で採番する（U6 の A 部/B 部分離原則 §6.0.2 を踏襲 — **DR 切替の生命線が他組織要求に依存しないこと**を設計原則とする）。
- スコープ: リージョン内可用性 / DR 構成（構成データ・ユーザデータの復元戦略）/ フェイルオーバー・フェイルバック手順 / RTO 1h 積み上げ検証 / セッションの扱い / パイロットライト / DR 訓練。
- 非スコープ: 監視実装・Runbook 本文・Burn Rate Alert 実装（→ U9。本書は仕様を引き渡す）、KMS Key Policy 詳細（→ U7、[ADR-045](../adr/045-cryptographic-key-management-strategy.md) MRK 前提のみ利用）、バックアップの法定保管詳細（§NFR-5.3/5.4 のベースライン値を採用）。

---

## 8.1 可用性設計（リージョン内・東京）

### 8.1.1 決定 D-U8-01: SLA 99.9% のエラーバジェットと直列可用性の成立性

| 項目 | 値 | 根拠 |
|---|---|---|
| SLA | **99.9%**（月間エラーバジェット **43.8 分** / 年間 8.76 時間） | P-04、§NFR-1.1 |
| 計測対象 | 認証エンドポイント（OIDC `/token` `/auth` / SAML）成功率。アプリ側計測の認証成功率も SLO 判定に含める | §NFR-1.0.A / §NFR-1.1 |
| 除外 | 計画メンテナンス窓（月 1 回・深夜 2-4 時、7 日前通知）/ 顧客起因 / **顧客 IdP 起因のフェデレーション失敗** | §NFR-1.2。顧客 IdP は責任分界外（L1 側） |

**直列可用性の積み上げ（設計目標の妥当性確認）**:

| コンポーネント | 公称/設計可用性 | 統制 |
|---|---|---|
| 他組織エッジ（CloudFront + WAF + NFW） | **要求値 99.95%**（REQ-DR-04、§8.9） | 他組織 — 保証不能 |
| ROSA HCP（Control Plane SLA） | 99.95% | Red Hat SRE |
| KC Pod 層（3 AZ、N≥3、PDB） | 99.99% 設計 | 弊社 |
| Internal ALB / PrivateLink | 99.99% | 弊社 |
| Aurora Multi-AZ（Writer + Reader×2） | 99.99% | AWS |
| **直列合成（概算）** | **≈ 99.87〜99.92%** | — |

→ 自管理部分のみなら 99.9% は余裕をもって成立。**律速は他組織エッジ**であり、エッジ可用性 99.95% 以上を要求仕様として明文化する（REQ-DR-04）。エッジ要求が未達でも、Sorry Page（ADR-022、Lambda@Edge/CF エラーページ — これもエッジ側要求 REQ-IN-07）で劣化を可視化する。

### 8.1.2 決定 D-U8-02: ROSA HCP Multi-AZ / PDB / HPA 方針

U6 D-U6-03/04（3 AZ × Machine Pool、c7g.xlarge ベースライン）を前提に、Pod 配置と自動復旧を次で確定する:

| 項目 | Broker KC | IdP-KC | 根拠 |
|---|---|---|---|
| 最小レプリカ | **3**（AZ ごと 1 以上、topologySpreadConstraints `topology.kubernetes.io/zone` maxSkew=1） | 3 | P-04、U6 §6.2.2 |
| PDB | **maxUnavailable=1**（KC CR 由来 StatefulSet に対して設定） | 同左 | ローリング時も 2 AZ 分の容量維持 |
| HPA | CPU 60% 目標（Broker は署名系で CPU 線形、U6 §6.5.2） | CPU 60% + **Scale-Out 予兆トリガ（`login_success_password_rate` > 8 TPS/node 3 分）を優先**（Argon2id + JVM warmup が遅いため、U6 §6.5.4） | sizing-guide §9 |
| ノード障害 | Machine Pool 自動置換（Red Hat SRE 管理）+ jdbc-ping による自動クラスタ再編（外部ディスカバリ機構不要） | 同左 | research #8 |
| ヘルスチェック | ALB → KC `/health/ready`（KC 側 health-enabled、management port）。閾値 3 回 × 10 秒 | 同左 | ADR-051 §D.2 踏襲 |
| SPOF 点検 | ALB Multi-AZ / VPC Endpoint 3 AZ / PrivateLink Endpoint 3 AZ（U6 §6.3.2）/ NAT なし構成（Private + Endpoint 群） | — | §NFR-1.4 |

### 8.1.3 決定 D-U8-03: Aurora Multi-AZ とリージョン内フェイルオーバー

- 構成: Writer + Reader × 2（3 AZ、U6 D-U6-07）。**リージョン内 Writer 障害は Aurora Managed Failover（< 1 分）で自動**（ADR-051 §E.1 の自動化区分を維持）。
- KC は Cluster（Writer）エンドポイントのみ接続（U6 D-U6-08）。Writer 交代時は JDBC socket/login timeout（ALB/R53 TTL 30s より短く設定）で早期切断 → Agroal プール再接続。**この再接続時間の実測が RDS Proxy 再評価（U6 O-3）の判定材料** → §8.9 で追跡。
- jdbc-ping 制約: Writer 交代中はディスカバリ書込が一時失敗するため、**クラスタ全 Pod の同時再起動を伴う操作は Writer 安定後に実施**（U6 §6.4.2 → U9 Runbook 禁則）。

### 8.1.4 決定 D-U8-04: ゼロダウンデプロイ（RHBK Operator ローリング）

| 変更種別 | 方式 | ダウンタイム |
|---|---|---|
| KC 設定変更・**パッチ版数**（26.x.y → 26.x.y+1） | RHBK Operator の Update 戦略 **Auto**（互換判定に基づくローリング再起動。PDB maxUnavailable=1 併用） | ゼロ（Persistent user sessions が DB 保存のため Pod 入替でセッション不断、sticky 不要） |
| **マイナー版数**（26.x → 26.x+1、DB スキーマ移行を伴い得る） | 計画メンテナンス窓（月 1 深夜、§NFR-1.2）で実施。事前に **Staging 1000 IdP 合成データセット回帰**（U2 §2.7.1 制約 1）通過必須 | 窓内（SLA 除外） |
| Operator 自体（OLM） | **Explicit（手動承認）** — 自動更新禁止 | ゼロ | 
| Custom SPI 差替 | KC イメージ再ビルド → パッチ版数と同じローリング。G-SPI-Compat 通過が前提 | ゼロ |

根拠: U2 §2.7.1（バージョン固定 + 昇格前検証、#46605 リグレッション前例）。デプロイ CI/CD の実装は U9。

---

## 8.2 DR 構成の全体像（Tier と対象データ）

### 8.2.1 決定 D-U8-05: RTO/RPO Tier と Failover モデル（ADR-051 骨格の維持）

ADR-051 の骨格は維持する（変更するのは復元戦略 §8.3 と待機形態 §8.6）:

| 項目 | 決定 | 変更有無 |
|---|---|---|
| モデル | **Active-Passive（東京 Primary → 大阪 DR）、自動化 80% + データ層 Cross-Region は手動承認 20%**（Split-Brain 防止） | 維持（ADR-051 §E） |
| Tier 2（標準・P-05） | **RTO 1h / RPO 1min** — 成立性検証は §8.4.3 | 維持 |
| Tier 1（規制業種オプション） | RTO 30 分。**パイロットライトでは不成立**（§8.4.4）→ Hot Standby 前提の Phase 2 オプションとして棚上げ | 位置づけ明確化 |
| Tier 3 | RTO 4h / RPO 15min | 維持 |
| 待機形態 | **パイロットライト（インフラ Warm + KC Scale 0）**。旧「Warm Standby KC Scale 1」は Aurora Secondary read-only 制約により**不成立のため修正** | **変更**（§8.6、§8.0.1） |
| Active-Active | 不採用継続 — 東阪レイテンシは公式要件（<10ms）上限で保証不能 + External Infinispan 復活は multi-cluster v2 の簡素化に逆行（[keycloak-dr-aurora-sync §5.1](../reference/keycloak-dr-aurora-sync.md)） | 維持 |

### 8.2.2 データ分類と DR 手段（SSOT 表）

**Keycloak の realm 構成（Clients / IdP / Flow / Org）はすべて DB に格納されるため、Aurora Global DB がユーザデータと構成データを一体で複製する**。この事実が旧 Realm Export 戦略を不要にする中核である:

| データ | 保存場所 | DR 手段 | RPO |
|---|---|---|---|
| ユーザ（ID/PW ハッシュ/属性/WebAuthn/TOTP） | Aurora（Broker / IdP-KC 各系統） | **Aurora Global DB** | < 1 min（実測 lag 典型 < 1s） |
| Realm 構成（Clients/IdP 1000+/Mapper/Flow/Org/User Profile） | Aurora（同上） | **Aurora Global DB**（リージョン障害時）+ **IaC 再適用**（論理破壊時、§8.3） | < 1 min / Git は常時最新 |
| ユーザセッション（オンライン/オフライン） | Aurora（KC 26 Persistent user sessions） | Aurora Global DB（ただし SLA 上は失効許容 — §8.5） | < 1 min（保証はしない） |
| 認証セッション（ログイン途中）/ アクショントークン / loginFailures | **Infinispan のみ** | **同期しない（失効許容）** | 対象外（§8.5） |
| JWT 署名鍵（ES256 realm keys） | Aurora（realm 構成の一部） | Aurora Global DB → **フェイルオーバー後も同一 kid / JWKS 不変** | < 1 min |
| インフラ暗号鍵 | KMS | **MRK**（大阪レプリカ、ADR-045。Aurora/監査ログ系のみ。Secrets/Break-Glass は Regional、U7 D-U7-01） | 0 |
| ITDR / Adaptive / Tenant Audit / DSAR | DynamoDB | **Global Tables**（ADR-051 §B.2。暫定、O-U8-9） | < 1 min |
| 監査ログ / SPA bundle / DSAR Export | S3 | **CRR**（ADR-051 §B.3。SPA はデプロイ時両リージョン） | 15 min / 即時 |
| `idmap` 補助 DB（U6 §6.4.1） | Broker Acct Aurora 別 DB | **同一 Aurora Global クラスタに同居** → 追加機構不要 | < 1 min |
| IaC / SPI 成果物 | Git / ECR | Git（リージョン非依存）+ **ECR クロスリージョンレプリケーション** | 0 |

---

## 8.3 DR 構成の再設計 — 構成データ復元戦略（ADR-051 改訂案の中核）

### 8.3.1 決定 D-U8-06: Realm Export を全面廃止し、復元経路を 2 系統に再定義する

**Realm Export は DR 目的を含む一切の用途で使用しない**（U2 §2.7.4 制約 4 の完全準拠。日次 Export・S3 保管・DR Import・RB-DR-04 を全廃）。復元は障害の性質で 2 経路に分ける:

| 復元経路 | 対象障害 | 手段 | 構成の SSOT |
|---|---|---|---|
| **経路 1: リージョン障害** | 東京全損・Aurora Primary 到達不能 | **Aurora Global DB Promote のみ**。realm 構成もユーザも DB に一体で複製済みのため、大阪 KC は昇格後の DB を読むだけで**構成再投入は一切不要** | Aurora（= Git と一致していることをドリフト検知で担保） |
| **経路 2: 論理破壊** | Realm 誤削除・構成破損・ランサムウェア・不正変更（リージョンは健在） | **(a) Aurora PITR**（粒度 5 分 / 保持 35 日、§NFR-5.4）で破壊直前へ巻き戻し、**(b) 直近の正当変更分は IaC 再適用で再生**: 基盤層 = Terraform（Realm 設定/Flow/SPI 配備/共通 Scope、単一 state — 分割の最終形は U9 D-U9-09）、テナント層 = **オンボーディングパイプライン（自作オンボーディング API による Admin API 差分適用、テナント単位宣言ファイル。keycloak-config-cli は K-1〔realm representation 禁止、U2 §2.7.4〕と原理衝突のため不採用 — U9 D-U9-10）**で該当テナントのみ再生 | **Git**（Terraform + テナント宣言ファイル） |

- 経路 2 で「全 1000+ IdP を Git から一括再生」は行わない（Admin API 負荷 + 時間の点で非現実的、U2 §2.7.5 と同根）。**PITR を主、IaC 再生は差分（破壊時刻以降の正当変更）に限定**する。破壊時刻の特定は Admin Events + 監査ログ（監査 Acct S3、改変不能）による。
- 旧 ADR-051 §A.2「Keycloak Realm 破損 = Realm Export Restore、RPO 24 時間」は「**PITR + 差分 IaC 再生、RPO 5 分（PITR 粒度）**」に置き換わる — RPO が 24h → 5min へ**大幅改善**する点は改訂の副次効果として明記する。

### 8.3.2 決定 D-U8-07: 整合性検証 = IaC ドリフト検知（Git ⇔ 稼働 KC の突合）

経路 1 が成立する条件は「Aurora の中身 = Git の宣言」が常時保たれていることである。手当てを設計制約にする:

| # | 施策 | 内容 | 主管 |
|---|---|---|---|
| 1 | 変更経路の一本化 | 基盤層 = Terraform / テナント層 = オンボーディングパイプライン**以外の構成変更を禁止**（Admin Console 直接変更は緊急時 Break-Glass のみ、事後 Git 反映必須） | 本書（原則）/ U9（統制） |
| 2 | 定期ドリフト検知 | 日次 CI で (a) Terraform `plan` 差分ゼロ確認（基盤層）、(b) テナント層は Admin API 読取（IdP/Org/Mapper 単位）と宣言ファイルの突合スクリプト。**realm 全体 export は使わない**（IdP 単位 GET のページング走査） | U9 実装 |
| 3 | ドリフト時対応 | 差分検知 → 監査ログ照合 → 正当なら Git へ逆反映 / 不正なら経路 2 発動判断（ITDR 連携、ADR-035） | U9 Runbook |
| 4 | DR 訓練での検証 | Game Day（§8.7.2）で「大阪昇格後の KC 構成 = Git 宣言」の突合を合格基準に含める | 本書 §8.7 |

---

## 8.4 フェイルオーバー手順と RTO 1h の積み上げ検証

### 8.4.1 決定 D-U8-08: フェイルオーバー判断基準（自動 80% / 手動承認 20%）

ADR-051 §E.1 の区分を維持しつつ、判断を早めるため**リージョン障害判定チェックリスト（RB-DR-00、新設）**を定義する:

| 判定材料 | 例 |
|---|---|
| AWS Health Dashboard | ap-northeast-1 の複数サービス Event |
| 合成監視（外形） | 東京 auth エンドポイント成功率 < 50% が 3 分継続、大阪からの東京到達性 |
| Aurora | Writer 接続不能 + リージョン内 Failover 不成立 |
| 判定 | 上記 2 系統以上該当 → 「リージョン障害」と宣言し承認プロセスへ（単一 AZ・単一コンポーネント障害は §8.1 の自動復旧に委ねる） |

手動承認（Aurora Global Promote / DR 全体切替 / Failback）は IR Lead 起案 → CTO 承認（ADR-051 §E.2 フロー維持）。**承認 SLA = 検知から 15 分以内**を運用目標とし、Game Day で計測する。

### 8.4.2 フェイルオーバータイムライン（Tier 2 想定、worst-case 積み上げ）

並行化可能な作業（ノード増設は DB 昇格を待たない）を明示した設計タイムライン:

| 時刻 | トラック | アクション | 所要（worst） |
|---|---|---|---|
| T+0 | 検知 | 障害発生。外形監視・R53 Health Check（3 回 × 10s）異常 | — |
| T+3 | 検知 | 複合アラーム確定 → PagerDuty → SRE Lead | 3 min |
| T+3〜10 | 判断 | RB-DR-00 チェックリスト判定 + War Room 招集 | 7 min |
| T+10〜20 | 判断 | CTO 承認（**手動 20% 部分**。目標 15 分、worst 20 分） | 10 min |
| T+20〜25 | **A: DB** | RB-DR-01: Aurora Global **unplanned Managed Failover**（Secondary detach & promote）× 2 系統（Broker / IdP-KC 並行実行） | 5 min |
| T+20〜35 | **B: 基盤**（A と並行） | RB-DR-03: 大阪 Machine Pool スケールアップ 2 → 6 ノード（c7g.large → xlarge 系プール、事前定義済み）。HCP ノード供給 12-15 min | 15 min |
| T+25〜38 | **A→B 合流** | KC Scale 0 → 3+（Broker/IdP-KC）: 昇格済み Writer へ接続、jdbc-ping 登録、JVM 起動 + キャッシュ初期ロード（イメージは ECR レプリケーション済み・ノードに pre-pull） | 8-13 min |
| T+38〜45 | 検証 | 合格基準チェック: ログイン成功（フェデ/ローカル各 1）、JWKS 応答・kid 一致、token/refresh、Broker→IdP-KC PrivateLink 疎通（大阪側複製済み、U6 §6.8.2）、`idmap` 参照 | 7 min |
| T+45〜50 | DNS/エッジ | RB-DR-02: Route 53 Failover（弊社管理レコード、TTL 30s）+ **他組織エッジのオリジン切替**（事前設定 Origin Group なら自動 / 手動なら REQ-DR-01 の SLA 内） | 5 min |
| **T+50** | 完了 | 全面切替宣言・顧客通知。**バッファ 10 分** | — |

補足: 静的資産（Sorry/SPA）は CloudFront Origin Failover により T+数分で先行復旧（部分復旧）。ADR-051 §H.1 の 40 分想定に対し、本書は KC 起動遅延（JVM + キャッシュ）と他組織エッジ調整を織り込んで 50 分とした。

### 8.4.3 決定 D-U8-09: **RTO 1h は「条件付き成立」**（結論）

worst-case 積み上げ 50 分 + バッファ 10 分で **Tier 2 RTO 1h は成立する**。ただし以下 5 条件が前提であり、いずれかが欠けると成立しない。各条件はゲート/要求仕様として追跡する:

| # | 成立条件 | 欠落時の影響 | 担保手段 |
|---|---|---|---|
| 1 | 手動承認が T+20 までに完了 | +10〜30 min | 承認 SLA 15 分 + Game Day 実測（§8.7） |
| 2 | 大阪の EC2 在庫・vCPU クォータ事前確保 | ノード供給不能 = RTO 崩壊 | **G-OSAKA**（U1 §1.5。クォータは東京ピーク同等値を事前申請） |
| 3 | KC イメージ・SPI 成果物が大阪 ECR に常時レプリケーション済み + パイロットライトノードへ pre-pull | +5〜10 min | §8.6 平時同期、CI で東西同時 push |
| 4 | **他組織エッジの DR 切替が「事前設定済み自動」または切替 SLA ≤ 10 分** | DNS/エッジで律速 → RTO 未達 | **REQ-DR-01〜03**（§8.4.5、要求仕様） |
| 5 | PrivateLink（Broker→IdP-KC）大阪側の事前複製 | 2-tier ログイン不能 | U6 §6.8.2 で配置確定済み。訓練で疎通確認 |

### 8.4.4 Tier 1（RTO 30 分）はパイロットライトでは不成立

積み上げ上、T+20 承認 + T+35 ノード供給の時点で 30 分を超過する。Tier 1 は **Hot Standby（大阪 KC 常時稼働）が必須だが、Aurora Global Secondary read-only 制約により「大阪 KC を東京 Writer にクロスリージョン接続で常時稼働」等の別方式検討が必要**であり、Phase 1 では**提供しない**（規制業種顧客の契約要求が発生した時点で Phase 2 検討、ADR-051 §G.2 のコスト前提も再試算）。

### 8.4.5 DNS 切替・エッジ DR の要求仕様（他組織管理 — B 部）

P-18 により公開エッジ（CloudFront + WAF + ALB/NLB + NFW）は他組織管理であり、**DR 切替の最終段が管理外**にある。U6 §6.8.2 ③の「Route 53 Failover は誰の管理か」への回答として、以下を要求仕様に追加する（U6 §6.7 の要求仕様書 v1 への追補）:

| # | 要求 | 内容 |
|---|---|---|
| REQ-DR-01 | **大阪オリジンの事前登録** | 弊社の各公開ドメイン（auth / idp / admin-SPA / scim-* / launchpad）の CloudFront に、大阪側 Internal ALB（または NLB）を**セカンダリオリジンとして平時から登録**（Origin Group、failover_criteria 5xx）。切替は自動化され人手を要さないこと |
| REQ-DR-02 | 手動切替のフォールバック SLA | Origin Group 構成が不可の場合、弊社の DR 宣言から**オリジン切替完了まで ≤ 10 分**の対応 SLA を合意すること（24/365） |
| REQ-DR-03 | DR 時の Egress 同等性 | 大阪側 Broker KC CIDR からの顧客 IdP 向け Egress（1000+ FQDN、REQ-OUT-01 のルールグループ）が**東京と同一内容で大阪側 NFW にも平時から適用**されていること（Failover 後に申請が必要な構成は不可） |
| REQ-DR-04 | エッジ可用性 | エッジ経路全体の可用性 99.95% 以上（§8.1.1 の直列成立条件） |
| REQ-DR-05 | DR 訓練参加 | 年 1 回以上、弊社 Game Day（§8.7）への切替訓練参加（最低限 Origin Failover の実動確認） |

**REQ-DR-01/02 のいずれも合意できない場合、RTO 1h は保証できない**（条件 4 欠落）→ 顧客 SLA 記述を「RTO 1h（エッジ切替を除く）」へ改める必要があり、契約前に決着させる（§8.9 未決 O-U8-1。**G-EDGE-DR** として U1 §1.5 登録済み — REQ-DR-01 or 02 合意なしに RTO 1h を SLA 記載禁止）。

---

## 8.5 Infinispan / セッションの扱い — 「大阪側は全ユーザー再認証」の明文化

### 8.5.1 決定 D-U8-10: セッション連続性は SLA 対象外（全ユーザー再認証を標準とする）

jdbc-ping + multi-cluster v2 前提では**リージョン間で共有されるのは Aurora のみ**であり、Infinispan キャッシュ（認証セッション・work・loginFailures・actionTokens）は大阪で空から再構築される。よって:

> **リージョンフェイルオーバー時、全ユーザーは再認証（再ログイン）となることを製品仕様として明文化し、顧客 SLA・利用規約に記載する。**「再ログインのみで業務再開可能」（WebAuthn/TOTP は Aurora 経由で大阪でも有効）が顧客への説明線（ADR-051 §C.4 の維持・格上げ）。

実際には KC 26 の Persistent user sessions により SSO セッションは DB 複製されており、キャッシュ再構築後にセッションが有効と扱われる**可能性がある**（keycloak-dr-aurora-sync §4.4）。これは**アップサイドであり保証しない**（保証すると RPO 検証対象が増え、訓練合格基準が複雑化するため）。フェデレーションユーザー（P-07 γ: 大多数）は顧客 IdP 側セッションが生きていれば**パスワード再入力なしの再認証**で完了する点も顧客説明に含める。

### 8.5.2 RPO への影響整理（データ種別ごとの確定）

| データ | RPO | 扱い |
|---|---|---|
| ユーザ・credential・realm 構成・`idmap` | **≤ 1 min**（P-05 の RPO はこれを指す。実測 lag 典型 < 1s） | 保証対象 |
| 発行済み Access Token（ES256、30 min） | **影響なし** — 自己完結 + 署名鍵が Aurora 複製で kid 不変のため、切替中もアプリ側 JWT 検証は継続 | 保証対象（JWKS 不変を検証項目に含む） |
| Refresh Token / オフラインセッション | DB 複製されるが、**切替時の失効（再認証要求）を許容** | 失効許容 |
| SSO セッション | 同上（§8.5.1） | 失効許容 |
| 認証セッション（ログイン途中）・アクショントークン（PW リセットリンク等） | **消失** — 再試行・再送で回復 | 対象外と明記 |
| loginFailures（ブルートフォース カウンタ） | **消失** — 一時的セキュリティ低下 | 対象外だが緩和必須（下記 #4） |
| `rds.global_db_rpo` | **Phase 1 は設定しない**。lag > 60s でプライマリ書込ブロック = 認証停止（ログインはセッション書込を伴う）という可用性毒性が RPO 保証益を上回る。lag 監視（> 10s warning / > 30s critical、U9）で担保し、Tier 1 契約発生時に再評価 | 決定 |

### 8.5.3 keycloak-dr-aurora-sync.md 既知ギャップの解消状況

[keycloak-dr-aurora-sync.md](../reference/keycloak-dr-aurora-sync.md)（2026-03 調査）が挙げた問題の本設計での帰結:

| 既知ギャップ | 本設計での状態 |
|---|---|
| キャッシュ無効化メッセージ（work）が Region 間で届かない → 旧 PW ログイン可・無効化未反映（同 §4.5） | **構成上排除** — Active-Passive + KC Scale 0 のため両リージョン同時稼働が存在せず、大阪 KC は常に空キャッシュで新規起動 = DB 最新を読む（同 §4.5 の結論を設計制約として固定。**Hot Standby を将来検討する場合はこの問題が復活する**ことを Phase 2 検討条件に明記） |
| Aurora Secondary read-only で KC 起動不可（§4.1） | **設計に反映** — パイロットライト = KC Scale 0（D-U8-07）。旧 ADR-051「Scale 1」を修正 |
| 全ユーザー再認証（§4.3） | **明文化して許容**（D-U8-10） |
| ブルートフォースカウンタリセット（§4.3） | 緩和策: フェイルオーバー後 60 分間、エッジ WAF の認証系 Rate Limit を強化モードへ（要求仕様 REQ-IN-01 の Rate Limit 可変運用として他組織へ依頼 / 不可なら ITDR（ADR-035）の Brute Force 検知感度を一時引上げ — U7/U9 引き渡し） |
| 認証セッション・アクショントークン消失（§4.3） | 許容（再試行・再送）。顧客向け Failover 告知文テンプレートに「発行済みパスワードリセットリンクは無効化」を記載（U9 Runbook 添付） |
| フェイルバック時のデータ消失リスク（§5.5 やってはいけないこと） | §8.7.1 手順に禁止操作として組込み |

---

## 8.6 パイロットライト詳細（大阪）

### 8.6.1 決定 D-U8-11: 平時の大阪最小構成

U6 §6.2.3 のコスト前提（cluster fee + 最小 worker）を構成として確定する:

| レイヤ | 平時の状態 | Failover 時 |
|---|---|---|
| ROSA HCP × 2（Broker / IdP-KC） | **クラスタ稼働**（cluster fee $182.5/月 × 2）+ infra Pool **c7g.large × 2 ノード/クラスタ**（テイントなし、Operator 群・監視エージェントのみ稼働） | **KC 専用 Pool（labeled/tainted、min 0 で事前定義 — U6 §6.2.4、2026-07-24 明確化: KC Pod は toleration/nodeSelector を持つため infra ノードには載らない）** を 0 → 6+ ノード（c7g.xlarge/2xlarge）へ |
| RHBK Operator / KC CR | **導入済み・KC CR replicas=0**（Aurora Secondary read-only のため起動不能 = 起動させない）。KC イメージは 2 ノードへ pre-pull（DaemonSet or ImageCache） | replicas 0 → 3+（東京と同一 CR 定義、接続先は大阪 Aurora エンドポイント — 環境差分は Kustomize overlay 1 点のみ） |
| Aurora | Global Secondary Reader × 1 / 系統（Warm） | Promote → Writer + Reader 増設（事後） |
| Internal ALB / PrivateLink / VPC Endpoint 群 | **事前作成・常時稼働**（Region 内リソースのため東京と別個に作成済み、U6 §6.8.2） | そのまま利用 |
| Secrets / KMS | Secrets Manager マルチリージョンレプリカ（**複製先暗号鍵は大阪側 Regional CMK — U7 D-U7-01 のとおり Secrets 系 CMK は MRK 化しない**）+ Aurora/監査ログ系のみ KMS MRK レプリカ（U7 §7.1.1 の MRK 対象表参照） | そのまま利用 |
| DynamoDB / S3 | Global Tables / CRR で受動同期 | そのまま利用 |

### 8.6.2 平時の同期対象（「大阪が腐らない」ための定常運用）

| 対象 | 方式 | 検証 |
|---|---|---|
| ユーザ + realm 構成 | Aurora Global（ストレージレベル連続複製） | lag 監視（§8.5.2） |
| KC イメージ / SPI | CI が東西 ECR へ同時 push（ECR レプリケーションルール） | CI で東西 digest 一致検査 |
| IaC | 同一 Git。**東京 apply 成功 = 大阪 overlay の plan 実行（apply はしない）を CI に組込み**、大阪定義の陳腐化を検知 | 日次 CI |
| DNS / エッジ | 大阪オリジン事前登録（REQ-DR-01）、R53 Failover レコード事前定義（Secondary 側 Health Check は KC 非依存の ALB 疎通に設定 — KC Scale 0 で常時 unhealthy になる誤設計を禁止） | Game Day |
| 監視 | 大阪側の外形監視・アラームも平時から稼働（「DR 側の監視が死んでいた」を防ぐ） | U9 |
| Log scrubbing | **大阪側にも Fluent Bit Aggregator・マスキング経路（U7 §7.3.1）を平時配備**（Failover 後に平文ログが流れる構成を禁止） | U7/U9 |

### 8.6.3 起動時間見積り（RTO 内訳の根拠）

| ステップ | 見積り | 根拠 |
|---|---|---|
| Machine Pool スケールアップ（2 → 6 ノード） | **12-15 min** | ROSA HCP ノード供給の一般値。**Game Day で実測し本表を更新**（初回訓練の必須計測項目） |
| KC Pod 起動（replicas 0→3、イメージ pre-pull 済み） | 2-3 min/Pod（JVM 起動 + DB 接続 + jdbc-ping 登録） | PoC 実測レンジ |
| キャッシュ初期ロード（realms 200k entries 設計、U6 D-U6-10） | 初回リクエスト負荷で漸進ロード。**ウォームアップ時間は PoC P-4 の測定対象**（U2 §2.7.6 — DR 切替時間に直結と明記済み） | G-IdP-Scale P-4 |
| 合計（KC サービスイン） | **20-25 min**（承認完了から） | §8.4.2 の T+20 → T+45 と整合 |

---

## 8.7 フェイルバック手順と DR 訓練計画

### 8.7.1 決定 D-U8-12: フェイルバックは計画 Switchover（手動承認・RPO 0）

keycloak-dr-aurora-sync §5.5 の手順を正式化する（大阪 Primary 継続期間中に大阪で書かれたデータの保全が目的）:

1. 東京リージョン復旧確認（AWS Health + 自主疎通）。
2. **東京旧 Aurora を独立再起動しない / Global Cluster を削除しない / 同期完了前に東京を Primary へ戻さない**（禁止 3 操作 — 実行すると大阪期間中のデータ消失）。
3. 東京クラスタを大阪 Primary の **Secondary として再参加**させ、全量レプリケーション完了を確認（lag = 0 近傍）。
4. 計画メンテナンス窓で **Aurora 計画 Switchover**（RPO 0）× 2 系統 → 東京 Writer 復帰。
5. 東京 KC を起動（大阪期間中に KC バージョン/SPI を上げていた場合は東西一致を確認してから）→ 検証（§8.4.2 と同じ合格基準）→ DNS/エッジを東京へ戻す → 大阪 KC replicas=0 へ縮退、Machine Pool を最小へ。
6. 事後: ドリフト検知（§8.3.2）を東西とも実行し Git 一致を確認。AAR（After Action Review）起票。

フェイルバックは全段**手動承認**（ADR-051 §E.1 維持）。切戻しを急がない — 大阪 Primary のまま数日運用しても構成上の問題はない（性能は東阪レイテンシ分アプリ側で劣化し得るため、SLO 監視で判断）。

### 8.7.2 決定 D-U8-13: DR 訓練計画（ADR-044 Game Day 連動、年 2 回）

[ADR-044](../adr/044-tabletop-exercise-incident-drill.md) の演習体系 D（Game Day、半期 = **年 2 回**。§NFR-5.5 の「年 1-2 回」の上限側を採る）に本書の検証項目を割り当てる:

| 回 | 内容 | 方式 | 合格基準 |
|---|---|---|---|
| H1（上期） | **S-07 リージョン障害フル切替**（ADR-044 S-07） | Aurora **計画 Switchover**（RPO 0、顧客影響を再認証のみに限定）+ 大阪スケールアップ + エッジ切替（REQ-DR-05 で他組織参加） | RTO ≤ 60 min 実測 / §8.4.2 各トラック実測値の採取（特に初回: Machine Pool 供給時間・キャッシュウォームアップ）/ 昇格後構成 = Git 突合（§8.3.2 #4）/ フェイルバック完走 |
| H2（下期） | **経路 2 復元訓練**（論理破壊）+ Runbook 検証 | Staging で realm 構成破壊 → PITR + 差分 IaC 再生（RB-DR-04'） | 復元 RPO ≤ 5 min / テナント単位再生の完走 / RB-DR-00〜05 の完走率 100% |
| 通年 | 技術 Tabletop（四半期、ADR-044 B）のうち 1 回を「承認フロー 15 分以内」の机上検証に充当 | 机上 | 承認 SLA 達成 |

- 通知: アプリ運用へ 2 週間前・顧客へ 3 営業日前（§NFR-5.5）。アプリ側確認項目（ログイン/JWT 検証/Refresh/JWKS）は §NFR-5.5 の役割分担表に従う。
- KPI: 演習 RTO 達成率 90%+ / RPO 達成率 100% / Runbook 完走率 100% / AAR Action 90 日完了率 100%（ADR-051 §F.2 維持）。
- Runbook 体系（U9 起草、本書が仕様）: RB-DR-00 判定チェックリスト（**新設**）/ RB-DR-01 Aurora Promote × 2 系統 / RB-DR-02 DNS・エッジ切替（REQ-DR-02 の連絡手順含む）/ RB-DR-03 大阪スケールアップ + KC 起動 + 検証 / **RB-DR-04' PITR + 差分 IaC 再生（旧 Realm Restore を置換）** / RB-DR-05 フェイルバック（禁止 3 操作を冒頭に明記）。

---

## 8.8 ADR-051 改訂案（本書確定後にユーザーが ADR-051 へ反映）

差し替え対象セクションと新記述の骨子。**本書 D-U8-05〜13 が改訂の設計根拠**であり、ADR 側は結論 + 本書参照の形に圧縮することを推奨（feedback_adr_split_pattern 準拠）:

| # | ADR-051 の対象箇所 | 改訂内容（骨子） |
|---|---|---|
| 1 | 冒頭ステータス / 2026-07-23 警告注記 | 警告を解消済みに変更: 「基本設計 U8（本書）で正式改訂済み」とし、Accepted へ昇格可 |
| 2 | Decision 表「Keycloak」行 | 「EKS 両 Region、DR は Warm Standby（Scale 1）」→ **「ROSA HCP 東西対称、DR はパイロットライト（インフラ Warm + KC Scale 0 — Aurora Secondary read-only のため KC は起動不能）」**（D-U8-07） |
| 3 | Decision 表「Realm 設定」行 | 「GitOps + Realm Export 日次自動 → S3 → DR Import」→ **「Aurora Global DB（realm 構成は DB に一体複製、リージョン障害時は Promote のみで復元完了）+ IaC 再適用（論理破壊時: PITR 主・差分再生。基盤層 Terraform + テナント層オンボーディングパイプライン）。Realm Export は全用途で禁止（U2 §2.7.4）」**（D-U8-06） |
| 4 | §A.2 表「Keycloak Realm 破損」行 | 「Realm Export Restore + 手動 / RTO 30 分-2h / RPO 24h」→ **「Aurora PITR + 差分 IaC 再生 / RTO 1-2h / RPO 5 分」**（改善として明記） |
| 5 | §C 全体（C.1〜C.4） | 全面書換: C.1 戦略表に「E. Aurora Global 一体復元 + IaC（本書）」を追加し採用、旧 B 案の Export 部分を廃止。C.2 表の「Realm 設定 = GitOps Export 日次 / RPO 24h」行を削除し §8.2.2 の SSOT 表へ差替。C.3 は §8.3 参照に置換（keycloak provider の全 Realm IaC 化例示は 1000+ IdP で不成立のため削除、2 層 IaC へ）。C.4 は §8.5 参照へ |
| 6 | §D / 全文の EKS 表記 | 「EKS Keycloak Replicas 6 / EKS DR Scale Up」→ ROSA HCP Machine Pool + KC CR replicas 表記へ読み替え確定（図の差替は任意、本書 §8.4.2 参照で可） |
| 7 | §E.3 Runbook 表 | RB-DR-00 新設 / RB-DR-04 → **RB-DR-04'（PITR + 差分 IaC 再生）**へ置換 / RB-DR-02 に他組織エッジ連絡手順（REQ-DR-02）を追加（§8.7.2） |
| 8 | §G コスト | EKS 行を ROSA HCP 4 クラスタ実額（U6 §6.2.3 ≈ **$2,032/月**（infra Pool 別建て込み、うち大阪パイロットライト 2 クラスタ ≈ $602/月））参照へ差替。Tier 1 Hot Standby 行に「方式再検討要（read-only 制約）、Phase 2」と注記（§8.4.4） |
| 9 | §H シミュレーション | §8.4.2 のタイムライン（T+50、条件 5 点付き成立）へ差替。「他組織エッジ切替」ステップの明示追加 |
| 10 | Consequences | Positive「Realm Export 日次自動で設定同期」を「realm 構成も Aurora Global で RPO<1min 同期（Export 廃止で運用負荷減）」へ、Negative「Realm Export RPO 24 時間」を削除し「論理破壊時 RPO 5 分（PITR）」へ。**新 Negative: DR 切替最終段（エッジ）が他組織依存（REQ-DR-01/02 未合意時は RTO 1h 非保証）** |
| 11 | 関連リンク | ADR-040 への参照は**維持**し、注記を「2026-07-23 Accepted 復帰（Phase 1 α/β）。DR 発動承認・Break-Glass は ADR-040 §C/§H + U7 §7.6 参照」へ更新。本書（basic-design/08）と U6 §6.8.2 への参照を追加 |
| 12 | Decision 冒頭文・Decision 表（M-10） | Decision 冒頭文「Warm Standby」→「パイロットライト（インフラ Warm + KC Scale 0）」、「Tier 1 オプション提供」→「Tier 1 は Phase 2 検討（Phase 1 は提供しない、§8.4.4）」。Decision 表の Failover モデル行・S3 行の「Export 一時保管」も削除（D-U8-06 Export 全廃と整合） |

---

## 8.9 未決事項と他単元への引き渡し

### 8.9.1 未決事項

| # | 項目 | 内容 | 期限/ゲート |
|---|---|---|---|
| O-U8-1 | **エッジ DR 切替の他組織合意** | REQ-DR-01（Origin Group 事前登録・自動切替）or REQ-DR-02（切替 SLA ≤ 10 分）。**未合意なら RTO 1h 非保証 → 顧客 SLA 文言修正が必要**（§8.4.5） | 要求仕様書 v1 追補の回答時（Phase 1 契約前） |
| O-U8-2 | **G-OSAKA** | 大阪インスタンス在庫 + vCPU クォータ実確認（RTO 成立条件 2）。クォータは東京ピーク同等値で事前申請 | Phase 1 前 PoC ゲート（U1 §1.5） |
| O-U8-3 | Machine Pool スケールアップ実測 | 12-15 min 見積りの実測補正（§8.6.3） | 初回 Game Day（H1） |
| O-U8-4 | キャッシュウォームアップ実測 | 1000+ IdP データセットでの再起動・初期ロード時間 | PoC P-4（U2 主管） |
| O-U8-5 | RDS Proxy 再評価（U6 O-3） | Writer Failover 時の KC 再接続時間が RTO 内訳を圧迫する場合のみ | Game Day H1 実測後 |
| O-U8-6 | multi-cluster v2 の RHBK サポート版数 | research 残 TBD。未サポートなら upstream 手順（keycloak-benchmark cross-site-rosa）とのサポート切り分けを Red Hat に確認 | RHBK 26.4 導入前 |
| O-U8-7 | Tier 1（RTO 30 分）方式 | read-only 制約下の Hot Standby 代替方式（Phase 2。規制業種契約が発生した場合のみ） | Phase 2 |
| O-U8-8 | B-DR-1〜5（ヒアリング） | RTO/RPO/Tier 1 要否/訓練頻度/DR リージョンの顧客確定。本書は推奨デフォルト（Tier 2/年 2 回/大阪）で凍結済み、回答で差分改訂 | ヒアリング |
| O-U8-9 | **ITDR DynamoDB の大阪側方式 + Break-Glass 大阪側実体** | ITDR DynamoDB の大阪側方式（Global Tables 継続 vs 再構築許容 — 履歴 7 日分の消失可否）+ Break-Glass 大阪側実体（金庫・FIDO2・Regional 鍵）を **U7 O-U7-7 と合同で確定**。暫定 = Global Tables（ADR-051 §B.2 踏襲、§8.2.2） | U7 と合同（Phase 1 実装前） |

### 8.9.2 U9（運用・監視・IaC）への引き渡し

- **Runbook**: RB-DR-00〜05（§8.7.2 の仕様。禁止 3 操作 / 承認 SLA 15 分 / 検証合格基準を含む。**RB-DR-00 に ITDR 抑制/強化フラグ切替（U7 §7.2.3: G-2/G-3 通知のみ降格 + Brute Force 感度引上げ）を含む**）+ 顧客向け Failover 告知文テンプレート（再認証・リセットリンク無効化の記載、§8.5.3）。
- **監視**: Aurora Global lag（>10s warn / >30s crit）、大阪側外形監視の常時稼働、東西 ECR digest 一致、日次ドリフト検知 CI（§8.3.2 #2）、SLO Burn Rate Alert（月間バジェット 43.8 分、§8.1.1）。
- **禁則の継承**: realm 全体 export 禁止（U2 §2.7.4）/ 全 Pod 同時再起動は Writer 安定後（U6 §6.4.2）/ フェイルバック禁止 3 操作（§8.7.1）。
- **IaC**: 大阪 overlay の日次 plan 検証、Machine Pool スケールアップ定義（min 0 プール）の Terraform 化。

### 8.9.3 決定一覧（サマリ）

| # | 決定 | 節 |
|---|---|---|
| D-U8-01 | SLA 99.9% エラーバジェット 43.8 分/月、律速は他組織エッジ（99.95% を要求） | §8.1.1 |
| D-U8-02 | 3 AZ + PDB maxUnavailable=1 + HPA（IdP-KC は予兆トリガ優先） | §8.1.2 |
| D-U8-03 | リージョン内 DB Failover は自動（<1 分）、KC 再接続時間を O-U8-5 で追跡 | §8.1.3 |
| D-U8-04 | パッチ = Operator Auto ローリング（ゼロダウン）/ マイナー = メンテ窓 + 1000 IdP 回帰 | §8.1.4 |
| D-U8-05 | ADR-051 骨格維持（A-P / 80-20 / Tier 2 標準）、待機形態のみパイロットライトへ修正 | §8.2.1 |
| D-U8-06 | **Realm Export 全廃**。復元 2 経路 = リージョン障害: Aurora Global 一体復元 / 論理破壊: PITR + 差分 IaC 再生（RPO 24h → 5min に改善） | §8.3.1 |
| D-U8-07 | パイロットライト = インフラ Warm + **KC Scale 0**（Aurora Secondary read-only 制約） | §8.6.1 |
| D-U8-08 | RB-DR-00 判定基準 + 承認 SLA 15 分 | §8.4.1 |
| D-U8-09 | **RTO 1h = 条件付き成立**（worst 50 分 + バッファ 10 分、成立条件 5 点） | §8.4.3 |
| D-U8-10 | 全ユーザー再認証を製品仕様として明文化（Persistent sessions の継続は保証しないアップサイド） | §8.5.1 |
| D-U8-11 | 大阪最小構成・平時同期対象・起動時間見積り | §8.6 |
| D-U8-12 | フェイルバック = 計画 Switchover（RPO 0）+ 禁止 3 操作 | §8.7.1 |
| D-U8-13 | DR 訓練 = Game Day 年 2 回（H1 フル切替 / H2 論理破壊復元） | §8.7.2 |

---

## 改訂履歴

- 2026-07-23: 初版（Wave 2 起草）。Baseline v1 準拠。Realm Export 戦略の全廃と復元 2 経路への再設計（ADR-051 改訂案 §8.8 として提示）、パイロットライト KC Scale 0 修正、RTO 1h 条件付き成立（5 条件）の積み上げ検証、REQ-DR-01〜05 要求仕様新設。
- 2026-07-23 (v1.1): Wave 2 整合性レビュー反映 — §8.8 #11 を ADR-040 参照**維持**（Accepted 復帰注記）へ差替 + #12 追加（ADR-051 Decision 冒頭文・表の Warm Standby → パイロットライト修正、H-2/M-1/M-10）、コスト参照を U6 §6.2.3 ≈ $2,032/月へ修正（M-1）、KMS MRK 記述の精密化（Secrets 系は Regional、§8.6.1/§8.2.2、M-2）、O-U8-9 新設（ITDR DynamoDB 大阪側方式 + Break-Glass 実体、U7 O-U7-7 合同、M-3）、RB-DR-00 に ITDR 抑制/強化フラグ切替を追記（M-4）、REQ-DR-01 対象ドメインに launchpad 追加（M-9）、G-EDGE-DR ゲート採番付記（M-11）、大阪側 Aggregator・マスキング経路の平時配備を追記（L-2）。
- 2026-07-24 (v1.2): Wave 3 最終レビュー反映 — §8.3.1 経路 2 のテナント層再生エンジンを「Admin API / keycloak-config-cli」併記から**自作オンボーディング API による Admin API 差分適用に一本化**（keycloak-config-cli 不採用、U9 D-U9-10 / H-1）、基盤層「単一 state」に分割の最終形 = U9 D-U9-09 を注記（L-7）。
