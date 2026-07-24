# 基本設計 計画書（設計単元分割 + 調査体制）

作成日: 2026-07-23
更新: 2026-07-23 ユーザー指示によりインフラ前提を大幅更新（ROSA 想定 / IdP 1000+ / IdP-KC 別アカウント / インターネット境界は他組織管理）
ステータス: Draft（暫定前提で着手、ヒアリング結果で更新）

## 0. 背景・なぜここで決めるか

要件定義（FR 75 件 / NFR 75 件 / ADR 60 本 / hearing-checklist 127 項目）は約 80-85% 完成。
未回答ヒアリング項目は残るが、暫定前提を明示して凍結すれば基本設計に着手可能と評価した。
本書は (1) 暫定前提パラメータ、(2) 基本設計の単元分割（U1〜U10）、(3) 単元ごとの調査・設計体制を定義する。

評価の根拠となった棚卸し結果（2026-07-23 実施、5 系統並列調査）:
- 要件定義本体: ブロッキング TBD は 5 群に集約（MAU 規模 / FIPS・SLA・RTO/RPO / テナント分離粒度 / ユーザーカテゴリ / ID 層設計）
- proposal/fr: 実装設計未着手領域 = Realm/Org 構成・Authentication Flow・Custom SPI・Protocol Mapper・SCIM エンドポイント・ユーザ管理画面 API
- proposal/nfr + common: §C-7 が実装アーキテクチャ SSOT。NFR 数値は概ね確定（推奨デフォルト）
- ADR 60 本: 優先度 A（基本設計前に詳細化必須）= ADR 017/018/025/033/038/039/045/054/055/059/060
- 設計資産: doc/common + doc/reference の 68 ファイル中 63 が流用可能。新規に起こす領域は 5 つ

## 1. 暫定前提パラメータ（U1 で正式凍結）

ヒアリング未回答項目は以下の暫定値で設計を進め、確定時に差分改訂する。

| # | パラメータ | 暫定値 | 根拠 / 影響 |
|---|-----------|--------|------------|
| P-01 | プラットフォーム | Keycloak（Cognito 不採用確定）、**実行基盤 = ROSA HCP + RHBK Operator 推奨**（変更可能性あり） | 2026-07-23 ユーザー指示 + 同日調査（[research/rosa-hcp-adoption-research.md](research/rosa-hcp-adoption-research.md)）: Classic は新規作成期限公式化で HCP 一択 / **RHBK は ROSA 内包で追加サブスク不要** / 大阪対応済み。ADR-056 は改訂骨子作成済み |
| P-02 | MAU 規模 | **10M MAU 上限で設計（2026-07-23 ユーザー凍結）** | ADR-032/033 と整合。NFR-3 のレンジ記述（1 万〜100 万）は U1 で 10M 上限に改訂。過大なら縮小は容易 |
| P-03 | FIPS 140-2 | 不要 | Yes なら RHBK 必須化で全面見直し |
| P-04 | SLA | 99.9% | NFR-AVL-001 推奨デフォルト |
| P-05 | DR | Tier 2: RTO 1h / RPO 1min、Active-Passive（東京→大阪） | ADR-051 |
| P-06 | テナント分離 | L2 単一 Realm + Organizations + tenant_id クレーム | ADR-017/033/058 |
| P-07 | ユーザーカテゴリ | γ シナリオ（管理者層のみローカル、P-3 はフェデ強制） | §FR-1.2.0.0 第一推奨。β フォールバック余地を残す |
| P-08 | 識別子 | 3 階層（Layer A sub UUID / Layer B `<tenant>-<userid>` / Layer C IdP sub）、email は補助属性 | ADR-018/054/055 |
| P-09 | トークン | AT 30 分 / RT 30 日 + Rotation / 絶対 24h / アイドル 1h / 署名 ES256 | §NFR-4.2、ADR-045 |
| P-10 | JWT クレーム | Stage 1 最小（iss/sub/aud/azp/tenant_id/exp/iat）、PII 非搭載 | ADR-030 |
| P-11 | SSO 信頼レベル | L1 完全信頼デフォルト、L3 は規制業種オプション | §FR-4.2 |
| P-12 | プロビジョニング | JIT + SCIM 受信併用（native inbound SCIM 非依存、Custom Authenticator SPI 案 B、3 系統 Flow 配置） | PoC V1〜V3'' 検証済 |
| P-13 | ServiceNow | パターン ②（L1 SCIM + L2 SAML JIT） | ADR-023 §L |
| P-14 | アプリ標準プロトコル | 新規 = OIDC / 既存 SP = SAML | saml-vs-oidc §16、ADR-023 §L.9-10 |
| P-15 | 実行基盤詳細 | **ROSA HCP**（Classic 不採用）。東京 + 大阪対称構成成立（大阪対応を AWS 公式表で確認済み、ADR-056:294 TBD 解消） | 残論点: 大阪側インスタンス在庫・vCPU クォータ実確認 / 3y 契約見積 / RHBK×upstream SPI 互換実証。Workload Identity は ROSA 標準の pod identity webhook + IRSA 方式へ（ADR-041 改訂、STS 2 段チェーン設計は維持） |
| P-16 | ブローカー接続 IdP 数 | **1000 超の可能性あり** → 調査判定 = **条件付き成立（要 PoC）**（[research/keycloak-1000idp-scalability-research.md](research/keycloak-1000idp-scalability-research.md)） | KC 26.0 で 1K IdP 目標の構造改修完了（Epic #30084）だが公式実測なし・正の運用実例なし。**必須対策 7 点**（バージョン固定 / IdP 一覧非表示の維持 = HRD SPI が性能上の必須条件に格上げ / Org 紐付け必須 / realm export 運用禁止 / Terraform state 分割 or API 化 / キャッシュサイジング / IdP 数関数の監視）+ **PoC P-1〜P-7**。超過時の拡張パス = ADR-033 2-tier の IdP-KC シャーディング |
| P-17 | IdP-KC 配置 | **ブローカーとは別 AWS アカウント**に構築。同アカウント内のアプリからユーザ登録・削除等を直接実施する想定（変更可能性あり） | ADR-033/§C-7（Auth Platform Acct 同居前提）の改訂が必要。クロスアカウント経路 + アプリ→IdP-KC のユーザ CRUD API 設計（Admin API or SCIM）が新規論点。**クラスタトポロジ = 別アカウント 2 クラスタ維持で凍結（2026-07-23 ユーザー判断。増分 +約 $500/月 + DR 側は許容、権限分界・障害隔離を優先）** |
| P-18 | インターネット境界 | **他組織管理の監査アカウント**に集約: Inbound = CloudFront + WAF + ALB または NLB + Network Firewall / Outbound = Network Firewall（ドメインフィルタ） | **我々の管理外**。ADR-039 v2 の「ネットワーク監査 Acct」は自管理前提だったため責任分界を改訂。Egress ドメイン許可は申請ベース → 顧客 IdP 追加(1000+)ごとの許可申請プロセスが IdP 追加リードタイム SLA（<1 営業日）と衝突する恐れ |

## 2. 基本設計 単元分割（U1〜U10）

### U1. 全体アーキテクチャ・前提凍結（最優先・他全単元の入口）
- 決めること: P-01〜P-18 の正式凍結、コア/エッジ（ハイブリッド §C-6）境界基準。~~MAU レンジ / クラスタトポロジ~~ → **2026-07-23 ユーザー凍結済み（MAU 10M 上限 / 別 Acct 2 クラスタ維持）**
- 主インプット: §C-7、ADR-032/033/039/055 §A.6-A.7/056/058、research/rosa-hcp-adoption-research.md、research/keycloak-1000idp-scalability-research.md、hearing-checklist ゲート項目
- 既知の矛盾・改訂必要文書（本単元で解消）:
  1. MAU 前提 100K〜10M の幅（P-02）
  2. ~~EKS vs ECS~~ → **ROSA HCP + RHBK Operator で解消（2026-07-23 調査済み）**。ADR-056 改訂骨子は research/rosa-hcp-adoption-research.md に作成済み。波及: ADR-041（IRSA 方式へ）/ ADR-055 §A.6-A.7 / ADR-051（大阪成立追記）/ rosa-detailed-analysis.md / rhbk-support-and-pricing.md
  3. ADR-040 PAM は Out of Scope 化済みだが §FR-8.6/NFR 側に記述残存 → 参照整理
  4. ADR-033/§C-7: IdP-KC 同一 Acct 前提 → 別 Acct 配置（P-17）に改訂
  5. ADR-039 v2: ネットワーク監査 Acct 自管理前提 → 他組織管理（P-18）に責任分界を改訂
  6. ~~§NFR-3.1/3.2「10K IdPs 実証あり」~~ → **誤りと判明、2026-07-23 修正済み**（10K は Keycloak #45293 の未実装将来目標。実装済みは 1K 目標のみ、実測未公開） |

### U2. Keycloak 論理設計
- 決めること: Realm/Organizations 構成詳細、2-tier（Broker KC ↔ IdP-KC）間フェデレーション設定、Authentication Flow 5 系統（ローカル / フェデ / HRD / ステップアップ / Adaptive）、Custom SPI 仕様（HRD Authenticator[ADR-055] / JIT 制御 SPI 案 B / Re-Activation SPI / mfa_indicator Mapper）、Protocol Mapper 一式（aud/azp/tenant_id/roles）、User Profile 明示宣言
- 主インプット: ADR-017/033/055、jit-scim §10.4.F、PoC V3''（SPI 3 系統 Flow 配置）、hrd-implementation-keycloak.md
- 制約: SPI は Browser forms / First Broker / Post Broker の 3 系統配置必須（PoC F-6）、per-Mapper syncMode=IMPORT
- **新規論点（P-16）**: 単一 Realm での 1000+ IdP/Organizations のスケール実証（Admin Console 劣化・realm cache・#46605 リグレッション・ログインページは HRD 前提で IdP 一覧非表示）。閾値超過時の Realm 分割 or Broker 多段の代替案も併記する

### U3. ID・プロビジョニング・ライフサイクル設計
- 決めること: 3 階層識別子の DB スキーマ / マッピング DB（ADR-054）、JIT/SCIM 共存の Case 1-5 判別ロジック、ライフサイクル S1-S10・責任分界 L1-L3、削除 3 段階モデル（§10.4.K）+ Phase 2 物理削除バッチ仕様（deprovisioned_at）、SCIM エンドポイント設計（/scim/v2、Metatavu PoC 3 点の残検証）
- 主インプット: ADR-018/025/054、jit-scim-coexistence-keycloak.md §10.4.G/H/I/J/K/L、scim-deletion-realtime-detection.md
- ゲート: B-SCIM-12(SAML)/B-SCIM-13(LDAP 🚨)/B-SCIM-14(実 IdP)、B-JIT-LC-1/B-JIT-RA-1/B-SCIM-JIT-1
- **新規論点（P-17）**: IdP-KC 同居アカウントのアプリからのユーザ登録・削除経路の設計（Keycloak Admin API 直叩き vs SCIM vs 専用 API 層）。`provisioned_by` の第 3 の値（app 発 CRUD）とライフサイクル S1-S10・Re-Activation SPI 除外条件への影響整理

### U4. 認証体験・UX 設計
- 決めること: HRD 画面フロー + フォールバック UX、ログイン画面ブランディング（ADR-024 パターン A/A'）、Post-login Landing（Pattern 1）+ Sorry Page（CloudFront + Lambda@Edge）、MFA 4 ケース別フロー（amr 評価 → WebAuthn → TOTP → ローカル）、A11y WCAG 2.2 AA 適用箇所
- 主インプット: ADR-020/021/022/024/026/031/043、§FR-3.4/3.5、§FR-4.3

### U5. トークン・セッション・認可設計
- 決めること: JWT クレーム辞書（Stage 1 正式版 + 顧客拡張規約）、TTL 体系の最終値、Token Exchange 対象パターン（RFC 8693 v2、PoC 検証済）、Revocation 運用（侵害ウィンドウ設計）、ログアウト 4 レイヤー実装（Back-Channel 含む）、CSRF 3 層分界の RP 実装ガイド
- 主インプット: ADR-030/057/060、§FR-5/§FR-6、token-exchange-spec-and-patterns.md、session-management-deep-dive.md

### U6. インフラ・ネットワーク設計
- 決めること: アカウント体系の IAM/クロスアカウント詳細（Broker Acct ↔ IdP-KC Acct 間経路含む）、VPC/サブネット/SG 設計、ROSA クラスタ設計（Classic/HCP、Machine Pool、大阪対応）、Aurora パラメータ・サイジング、Keycloak CPU 律速サイジング（フェデ比率 × PW ハッシュコスト）、/admin 保護
- 主インプット: ADR-039 v2/010/012/013、keycloak-network-architecture.md、keycloak-cpu-bottleneck-sizing-guide.md、rosa-detailed-analysis.md、§C-7.2
- **新規論点（P-18）**: インターネット境界（Inbound: CloudFront+WAF+ALB or NLB+Network Firewall / Outbound: Network Firewall ドメインフィルタ）は**他組織管理の監査アカウント**。本単元は「先方への要求仕様」と「自アカウント内設計」を分離して起こす。特に (1) ブローカーのフェデレーション Egress（顧客 IdP の token/JWKS エンドポイント、1000+ ドメイン）の許可申請フロー、(2) NLB 経路の場合の TLS 終端と WAF 適用範囲、(3) Keycloak前段の X-Forwarded-For/プロキシ設定の整合、(4) /admin 保護(ADR-039 §E)の WAF 全 IP Deny は他組織への**要求仕様**となるため、自管理側で ALB Listener Rule 403 + Internal 経路限定(SSM/踏み台)の二重化を必須とする。Keycloak の admin 専用ホスト名分離(`hostname-admin`)の採用も U6 で検討

### U7. セキュリティ・コンプライアンス設計
- 決めること: KMS 3 階層 CMK の命名・Key Policy・ローテーション、ITDR 実装（Event Listener → EventBridge → Risk Engine、Phase 1 = Compromised Credentials + Brute Force）、Log scrubbing 辞書（ADR-060 §A）、Golden 検知 G-1〜6、Bot 対策（WAF ATP）、Workload Identity（Pod Identity + Federated Credentials）、PCI DSS ギャップ 3 点（監査ログ 12 ヶ月 / Phishing-resistant MFA / 漏えい SOP）の実装計画
- 主インプット: ADR-034/035/041/042/045/046/060、pci-dss-appi-compliance-gap.md、pci-dss-v401-scope-for-auth-platform.md

### U8. 可用性・DR 設計
- 決めること: Multi-AZ 構成詳細、Active-Passive フェイルオーバー手順（自動 80% + 手動承認 20%）、Aurora Global DB + Infinispan キャッシュ非同期の扱い（全ユーザー再認証許容の明文化）、~~Realm Export 自動化~~ → 復元 2 経路（D-U8-06 で Export 全廃）、Route 53 Health Check、DR 訓練計画（ADR-044 連動）
- 主インプット: ADR-051/044、keycloak-dr-aurora-sync.md、§NFR-1/§NFR-5

### U9. 運用・監視・IaC 設計
- 決めること: OTel + AMP/AMG/X-Ray 計装ポイント、SLO 定義書 + Burn Rate Alert、ログ 3 層保管（Hot/Warm/Cold）実装、Runbook A〜G 整備、Terraform モジュール分割 + State 管理、CI/CD（SPI ビルド含む）、Central Canary（ADR-059 App Registry スキーマ）
- 主インプット: ADR-053/059/046、§NFR-6、PoC Terraform 資産（Stage A）
- **新規論点（P-16/P-18）**: 顧客 IdP 追加ランブックに他組織への Egress ドメイン許可申請を組み込み、NFR の IdP 追加リードタイム（<1 営業日）との整合を取る（申請 SLA 次第で NFR 側の改訂 or 事前一括許可方式の交渉）。1000+ IdP の IaC 管理方式（Terraform の分割・実行時間）も本単元

### U10. 周辺連携・移行設計
- 決めること: ServiceNow 連携詳細（L2 SAML JIT 設定、sys_user Matching Field、並走 4 Phase）、ユーザ管理画面 API 仕様（ADR-038 Phase 1 MVP: CRUD/招待/ロール/監査 + Organization 管理）、Webhook 配信機構（HMAC + DLQ）、既存システム移行（並走 + User Storage SPI、PW ハッシュ互換判定、ADR-019/054 5 Phase）
- 主インプット: ADR-019/023/038/048/054、servicenow-sso-user-linking-guide.md、§NFR-9

## 3. 依存関係と進行 Wave

```
U1（前提凍結）
 ├─ Wave 1: U2 Keycloak 論理 / U3 ID・プロビ / U6 インフラ ← コア。相互参照あり
 ├─ Wave 2: U4 UX / U5 トークン・認可 / U7 セキュリティ / U8 DR ← Wave 1 の構成を前提
 └─ Wave 3: U9 運用 / U10 周辺連携・移行 ← 全体像確定後に詳細化
横断: 整合性レビュー（Wave 完了ごとに ADR・§C-7 との突合）
```

- U2↔U3 は密結合（SPI と ライフサイクルの両輪）。同一 Wave で相互参照しながら進める。
- U6 は U1 の実行基盤決定（P-15）が唯一の前提。決定後は独立に進行可能。
- U5 の Back-Channel Logout / Token Exchange は U2 の Client/Flow 設計に反映するため、Wave 2 開始時に U2 へフィードバックする。

## 4. 調査・設計体制（エージェント分担）

各単元 1 エージェント（担当領域の ADR + 設計資産を読み込み、設計ドキュメント案を起草）+ メインセッションが統合・整合性管理。

| 単元 | 成果物（doc/basic-design/） | 先行調査で追加確認が必要な点 |
|------|---------------------------|------------------------------|
| U1 | 01-architecture-baseline.md | MAU 幅の解消ロジック、ROSA Classic vs HCP + RHBK サブスク、コア/エッジ判定基準 |
| U2 | 02-keycloak-logical-design.md | **1000+ IdP/Org スケール実証（最重要）**、Organizations の属性格納制約、SPI 3 系統配置の realm.json 表現 |
| U3 | 03-identity-provisioning-design.md | Metatavu SCIM 残 PoC、B-SCIM-13(LDAP) の扱い、アプリ発ユーザ CRUD 経路（P-17） |
| U4 | 04-auth-ux-design.md | Keycloak Theme と A11y の両立、Sorry の Lambda@Edge 実装 |
| U5 | 05-token-session-authz-design.md | クレーム辞書のテナント拡張規約、RP 実装ガイド様式 |
| U6 | 06-infra-network-design.md | サイジング計算（フェデ比率 B-BROK-1 の暫定値要設定）、他組織管理の境界アカウントへの要求仕様書式、Broker↔IdP-KC クロスアカウント経路 |
| U7 | 07-security-compliance-design.md | Log scrubbing regex 辞書、ITDR Risk Engine 閾値 |
| U8 | 08-availability-dr-design.md | Infinispan 非同期の再認証影響定量化 |
| U9 | 09-operations-observability-design.md | OTel Keycloak 計装の実装方式、Canary Blueprint |
| U10 | 10-integration-migration-design.md | ユーザ管理画面 API の OpenAPI 化、移行 PW ハッシュ調査票 |

進め方（1 Wave = 調査 → 設計案起草 → メイン統合レビュー → ADR 追記/改訂）:
1. U1 をメインセッション + 単発調査エージェントで先行決着（矛盾 3 件の解消が中心）
2. Wave 1 の 3 単元を並列起動（各エージェントに担当 ADR・資産リストと暫定前提 P-01〜18 を引き渡す）
3. Wave 完了ごとに整合性レビューを 1 本走らせ、§C-7 / ADR / hearing-checklist へ差分反映
4. ヒアリング回答が届いた時点で該当単元の前提を差し替え、影響差分のみ改訂

## 5. ヒアリング確定待ちで設計を止めない運用

- 暫定値で設計 → 各設計書の冒頭に「前提: P-XX（暫定）」を明記 → 確定時に前提表だけ見て影響単元を特定できるようにする
- Phase 1 契約前ゲート 8 項目（B-JIT-LC-1 / B-JIT-RA-1 / B-SCIM-JIT-1/3 / B-JIT-DEL-1/2 / B-SCIM-HC-1 / B-TENANT-*）は U3 の設計書に「ゲート未通過」欄を設けて追跡
- Keycloak 必須化 6 条件（Token Exchange / Device Code / SAML IdP 発行 / LDAP / UMA / Back-Channel Logout）はいずれも P-01（Keycloak）で吸収済みのため、基本設計はブロックしない
