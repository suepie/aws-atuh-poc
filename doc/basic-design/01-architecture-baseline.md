# U1: 全体アーキテクチャ・前提凍結（Architecture Baseline）

作成日: 2026-07-23
ステータス: **凍結（Baseline v1）** — ヒアリング確定時は本書の前提表のみ差し替え、影響単元を特定して改訂する
上位文書: [00-basic-design-plan.md](00-basic-design-plan.md)

## 1.0 背景・なぜここで決めるか

基本設計の全単元（U2〜U10）は共通の前提セットの上に成立する。ヒアリング未回答項目が残る中で設計を止めないため、本書で前提を「凍結値 + 根拠 + 変更時の影響範囲」の形で固定し、各設計書は本書の P 番号を参照する。前提が変わった場合は本書だけを見れば影響単元を特定できる。

## 1.1 凍結済み前提（Baseline v1）

| # | 前提 | 凍結値 | 凍結日・根拠 | 変更時の影響単元 |
|---|------|--------|--------------|------------------|
| P-01 | プラットフォーム | **Keycloak / ROSA HCP + RHBK Operator**（RHBK サブスクは ROSA 内包・追加費用なし） | 2026-07-23 ユーザー指示 + [ADR-056 改訂](../adr/056-rosa-adoption-decision.md)・[research](research/rosa-hcp-adoption-research.md) | 全単元 |
| P-02 | MAU 規模 | **10M MAU 上限で設計** | 2026-07-23 ユーザー凍結。ADR-032/033 整合 | U2/U6/U8（サイジング・コスト） |
| P-03 | FIPS 140-2 | **不要（確定 2026-07-30）** | hearing C-201 回答 = 必須ではない | U7 |
| P-04 | SLA | 99.9%（暫定） | NFR-AVL-001 推奨デフォルト。ROSA HCP 自体は 99.95% | U6/U8/U9 |
| P-05 | DR | **Tier 3+: 手動 DR / RTO ≈ 14 日（大阪でオンデマンド再構築）/ RPO は Aurora 自動バックアップ + PITR 依存（2026-07-30 転換）**。**2 シナリオ: ① リージョン災害=大阪再構築+リストア / ② 論理破壊(IdP データ破壊・ランサム)=PITR・イミュータブルスナップショット(Backup Vault Lock)からリストア**。従前のピロットライト RTO 1h・大阪ウォーム待機は廃止 → **U8/U6/ADR-051 要改訂** | 2026-07-30 決定、ADR-051（要改訂） | U8/U6 |
| P-06 | テナント分離 | L2 単一 Realm + Organizations + tenant_id クレーム | ADR-017（2026-07-23 更新） | U2/U3 |
| P-07 | ユーザーカテゴリ | **P-1〜P-4 全カテゴリ受入（確定 2026-07-30）。テナント管理者含め全顧客ユーザーはフェデレーション**: 顧客 IdP 保有テナント = 顧客 IdP / 非保有テナント = **IdP-KC 収容（Broker から見て IdP の一つ）**。**Broker ローカルは基盤運用者/Break-Glass のみ**。従前 γ「管理者層のみローカル」から転換 → **U2 Browser Flow / U3 プロビ経路 / U4・U7 MFA（管理者=ローカル前提）要改訂** | A-5-2 回答 | U2/U3/U4/U7 |
| P-08 | 識別子 | 3 階層（sub UUID / `<tenant>-<userid>` / IdP sub）、email 補助 | ADR-018/054/055 | U2/U3/U5 |
| P-09 | トークン | AT 30 分 / RT 30 日 + Rotation / 絶対 24h / アイドル 1h / ES256 | §NFR-4.2、ADR-045 | U5 |
| P-10 | JWT クレーム | Stage 1 最小、PII 非搭載 | ADR-030 | U5 |
| P-11 | SSO 信頼レベル | L1 完全信頼デフォルト、L3 は規制業種オプション | §FR-4.2 | U4/U5 |
| P-12 | プロビジョニング | JIT + SCIM 受信併用、Custom Authenticator SPI 案 B、3 系統 Flow 配置。**LDAP User Federation 経路は対象外（2026-07-30、LDAP 顧客なし）** | PoC V1〜V3'' 検証済 | U2/U3 |
| P-13 | ServiceNow | パターン ②（L1 SCIM + L2 SAML JIT） | ADR-023 §L | U10 |
| P-14 | アプリ標準プロトコル | 新規 = OIDC / 既存 SP = SAML | saml-vs-oidc §16 | U5/U10 |
| P-15 | リージョン | 東京 ap-northeast-1（常用）+ 大阪 ap-northeast-3（**DR 時オンデマンド再構築、平時は ROSA 事前プロビジョニングなし** — 2026-07-30 DR 転換）。Aurora バックアップ/スナップショットは平時から保全 | P-05 連動、[research](research/rosa-hcp-adoption-research.md) | U6/U8 |
| P-16 | 接続 IdP 数 | **1000 超想定 — 条件付き成立**。必須対策 7 点を U2 設計制約とする。**G-IdP-Scale は実測困難のため仮定値（1000/2000 IdP・フェデ:IdP-KC = 50:50〔B-BROK-1 暫定〕）で設計継続、PoC は後追い検証に格下げ（2026-07-30）** | [research](research/keycloak-1000idp-scalability-research.md)、ADR-017 更新 | U2/U6/U9 |
| P-17 | アカウント/クラスタ | **IdP-KC は Broker と別 AWS アカウント、ROSA HCP × 2 クラスタ**（2026-07-23 ユーザー凍結）。同 Acct アプリからのユーザ CRUD 想定（変更可能性あり） | ADR-033 更新 | U3/U6/U7 |
| P-18 | インターネット境界 | **他組織管理の監査 Acct**（In: CF+WAF+ALB or NLB+NWFW / Out: NWFW ドメインフィルタ）。当該設定は**要求仕様**として起こす | ADR-039 v3 | U6/U7/U9 |

## 1.2 アカウント体系（P-17/P-18 反映版）

ADR-039 の 5 アカウント体系を Broker/IdP-KC 分割で **6 アカウント体系**に拡張する（U6 D-U6-01 で確定）:

| アカウント | 管理主体 | 主な内容 |
|-----------|---------|---------|
| ネットワーク監査 Acct | **他組織（管理外）** | Inbound: CloudFront + WAF + ALB or NLB + Network Firewall / Outbound: Network Firewall（ドメインフィルタ）。我々からは**要求仕様書**で連携 |
| ネットワーク Acct | 他組織想定（要確認） | Transit GW / DX / VPN |
| 監査 Acct | 弊社 | Org Trail / 監査ログ集約 S3 |
| **Broker Acct** | 弊社 | Broker KC（ROSA HCP クラスタ #1）+ Aurora + ITDR + 管理画面 Backend |
| **IdP-KC Acct** | 弊社 | IdP-KC（ROSA HCP クラスタ #2）+ Aurora + **同居アプリ（ユーザ CRUD を直接実施）** |
| App Acct × N | 各アプリチーム | Internal ALB + アプリ本体 |

補足: 旧「Auth Platform Acct」は Broker Acct / IdP-KC Acct に分割された。DR(大阪)側は Broker/IdP-KC それぞれにパイロットライト・クラスタを持つ（コストは U6 で再試算）。

## 1.3 コア/エッジ境界基準（§C-6 ハイブリッドの適用）

§C-6 の判定基準をそのまま基本設計の入口基準として凍結する:
- コア層(標準 80%): 本基盤(Broker KC)に OIDC で統合
- エッジ層(〜20%): 次のいずれかに該当するアプリのみ独自基盤を許容し Federation で SSO 維持 — ①コア層で対応不可の技術要件 ②コア層 SLA/AAL を大幅超過 ③完全独自の認証フロー ④アプリオーナーの強い独自運用要望 ⑤規制上の物理独立要件
- **P-17 の「IdP-KC 同居アプリ」はエッジ層ではない**(IdP-KC を利用する基盤側コンポーネント扱い)。U3 で CRUD 経路を設計する

## 1.4 解消済みの矛盾と残タスク

| 項目 | 状態 |
|------|------|
| EKS vs ECS(§C-7 vs ADR-056) | ✅ 解消 — ROSA HCP に統一(ADR-056 逆転、ADR-041/051/055 波及改訂済み、2026-07-23) |
| MAU 幅(100K〜10M) | ✅ 解消 — 10M 上限で凍結。**残タスク: NFR-3 §NFR-3.0.A のレンジ記述(1 万〜100 万)を 10M 上限に改訂** |
| §NFR-3「10K IdPs 実証あり」誤記 | ✅ 修正済み(2026-07-23、3 箇所) |
| ADR-040(PAM) OOS 残存参照 | ⬜ 残 — §FR-8.6 / §NFR-4 側の記述を「運用体制側で別途」の参照に整理(軽微、U7 着手時に実施) |
| §C-7 の EKS 記述・Auth Platform Acct 単一表記 | ⬜ 残 — ROSA HCP / Broker+IdP-KC 分割への改訂は U6 の成果物確定後に一括反映(SSOT の二重更新を避ける) |

## 1.4a 2026-07-30 意思決定による前提・スコープ更新

ユーザー判断により以下を確定/転換。ブロック度「高」だった 11 件の大半が解消し、詳細設計へ進める状態になった。ただし一部は**設計本文の改訂タスク**を伴う（[00a §2 D-17/D-18](00a-remaining-tasks-and-effort.md) に登録）。

| 決定 | 内容 | 影響 |
|---|---|---|
| C-201 FIPS | **不要で確定** | P-03 確定。U7 見直し不要 |
| A-5-2 利用者 | **P-1〜P-4 全受入。テナント管理者含め全ユーザーはフェデ（顧客 IdP / IdP-KC 収容）。Broker ローカルは運用者のみ** | P-07 転換 → **U2/U3/U4/U7 の「管理者ローカル」前提を要改訂（D-17）** |
| B-BROK-1 フェデ比率 | **未定 → 50:50 暫定で進行** | U6 サイジング入力（[C-1](00a-remaining-tasks-and-effort.md) を 50/50 で再計算） |
| B-LDAP-1 LDAP | **LDAP は無くなった** | **G-LDAP / B-SCIM-13 / D3-04 ldap 経路 / ADR-025 §H を対象外化**。U2/U3 の LDAP 記述は「Phase 1 対象外」注記 |
| B-PCI-1 PCI DSS | **対応不要になった** | **G-PCI-WAF / B-MFA-PCI-1 廃止。U7 の PCI スコープを「Phase 1 対象外」化**（削除でなく降格、将来再開可） |
| G-IdP-Scale | **実測困難 → 仮定値で設計継続**、PoC は後追い検証 | 非ブロッカー化（P-16 に反映） |
| G-SPI-Compat | **検証する** | A-2 継続（実施確定） |
| G-DPA（APPI 28） | **クラウド利用の同意は取得方針。Red Hat SRE の越境閲覧は確認中** | ブロッカーから「確認中の 1 項目」に軟化。ROSA 再検討リスクは大幅低下 |
| G-EDGE-DR | **手動 DR / RTO ≈ 14 日（大阪でオンデマンド再構築）** | **P-05/P-15 転換。ピロットライト・RTO 1h 廃止 → U8/U6/ADR-051 要改訂（D-18）**。エッジ DR 自動切替の合意は不要に |
| G-EGRESS | **初期一括 + 追加は都度依頼（先方は当日/翌日対応）** | 方式①で合意方向。**NFR-3 の IdP 追加リードタイム（次営業日以内）は成立** |

## 1.5 Phase 1 前 PoC ゲート(基本設計と並行)

| ゲート | 内容 | 担当単元 |
|--------|------|---------|
| G-IdP-Scale | 1000/2000 IdP 実測 PoC P-1〜P-7。**2026-07-30: 実測困難のため仮定値で設計継続 → ブロッカーでなく「後追い検証」に格下げ** | U2 |
| G-SPI-Compat | RHBK 26.4 × upstream 26.x Custom SPI 互換(HRD/Re-Activation) | U2 |
| G-UProfile-Email | **2026-08-03 追加(FC-5)**: User Profile で `email` を任意化した際の Keycloak 既知不具合(依存属性 firstName/lastName の検証失敗 [kc#21265]・`UPDATE_EMAIL`/Verify Profile の optional 無視 [kc#33497])を回避し、email 非保有ユーザーが登録/ログイン/更新を完走できるか実機検証。**email 非保有顧客(工場系)収容の前提条件**(U2 §2.6 設計制約 4 / §2.8.1) | U2 |
| G-SCIM | SCIM Facade の SCIM 2.0 準拠検証(Entra/Okta SCIM Validator + D1/D2 E2E + Soft Delete 写像 + deprovisioned_at セット確認。U3 §3.7.2 で再定義。旧 Metatavu 3 点は Metatavu 採用判断時のみ)。**2026-07-24 拡張(U3 §3.8)**: ① スケール次元(500/1000 テナント externalId 検索 p99 / バルク 5 万件中の他テナント遅延 / Writer 流量制御下 Aurora 負荷 — G-IdP-Scale と同一データセット併走)② 非 IdP E2E(D1 SCIM→EventBridge→統合射影→初回ログイン sub バックフィル + 読取 p99) | U3 |
| ~~G-LDAP~~ | ❌ **廃止(2026-07-30、LDAP 顧客なし)** — B-SCIM-13 も不要 | — |
| G-OSAKA | 大阪インスタンス在庫・vCPU クォータ実確認 | U6 |
| G-EGRESS | **合意方向(2026-07-30): 初期は一括、追加分は都度依頼（先方は依頼次第 当日〜翌日対応）→ 方式① + §NFR-3 リードタイム（次営業日以内）は成立**（U6 §6.7.3 D-U6-13、U9 §9.7.1） | U6/U9 |
| ~~G-PCI-WAF~~ | ❌ **廃止(2026-07-30、PCI DSS 対応不要)** — B-MFA-PCI-1 も不要 | — |
| G-DPA | **軟化(2026-07-30): クラウド利用の APPI 同意は取得方針。残は Red Hat SRE 越境閲覧の確認中 1 点**（U7 §7.7.4） | U7 |
| G-EDGE-DR | **転換(2026-07-30): 手動 DR / RTO ≈ 14 日で大阪オンデマンド再構築 → RTO 1h・エッジ自動切替合意は不要。論点は「大阪再構築 Runbook」へ**（U8 要改訂） | U8 |

> 用語注意: L1〜L4 は文脈で意味が異なる(U5 ログアウトレイヤー / ITDR 対応レベル / PAM 4 層 / U3 責任分界 / SN L1/L2)。各書で参照先を明記する。

## 1.6 Wave 1 への引き渡し

U2(Keycloak 論理設計)/ U3(ID・プロビジョニング)/ U6(インフラ・NW)は本書 P-01〜P-18 を前提に着手可能。各設計書の冒頭に「前提: 本書 Baseline v1」を明記すること。

## 改訂履歴

- 2026-08-03: §1.5 ゲート表に **G-UProfile-Email** 追加（FC-5、email 非保有ユーザー収容のための User Profile `email` 任意化の実機検証。U2 §2.6 設計制約 4 / §2.8.1）。あわせて移行系の是正 4 件を各書へ反映（ADR-019 §B 方式②前提+方式①フォールバック / §NFR-9.1 Partial Import 1000 件バッチ規約 / §FR-2.3.2.B email 非保有版 周知差分 / ADR-038 §C 資格情報配布モード）。
- 2026-07-30: **ユーザー意思決定 10 件を反映**（§1.4a 新設）。P-03 FIPS 不要確定 / P-05・P-15 DR を手動 14 日・大阪オンデマンド再構築へ転換 / P-07 全ユーザーフェデ化（管理者ローカル前提の U2/U3/U4/U7 要改訂 D-17）/ P-12 LDAP 対象外 / P-16 G-IdP-Scale 仮定値化。ゲート表: G-LDAP・G-PCI-WAF 廃止 / G-DPA・G-EGRESS 軟化・合意方向 / G-EDGE-DR 転換（D-18）。
- 2026-07-23: Wave 2 整合性レビュー反映 — §1.5 ゲート表に G-PCI-WAF / G-DPA / G-EDGE-DR の 3 行追加(M-11)、L1〜L4 用語注意の 1 行追加(L-7)。Baseline v1 の凍結前提(P-01〜P-18)自体は変更なし。
