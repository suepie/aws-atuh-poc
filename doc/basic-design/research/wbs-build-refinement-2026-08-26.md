# 製造（詳細設計+構築）WBS 精緻化 — 全 DU 内訳分解 + 分岐プール + 集計是正

- **日付**: 2026-08-26
- **種別**: research note（見積り精緻化シリーズ ②製造。① 基本設計 = [00a v2](../00a-remaining-tasks-and-effort.md)、③ テスト = [wbs-gap-audit §10](wbs-gap-audit-2026-08-12.md) に続く）
- **対象**: [00b](../00b-design-unit-breakdown.md) の全 DU（[gap-audit §8](wbs-gap-audit-2026-08-12.md) の per-DU 人日）
- **規約**（00a v2 と同一思想、製造用に調整）:
  1. **work item = 1〜6 人日・1 項目 1 成果物**。8 人日以上（M/L）の DU は必ず内訳分解（内訳セル「項目 x; 項目 y」形式。Excel 側で行分割可能な粒度）。
  2. **場合分け = 構築側分岐プール CB-\***（トリガー顕在時のみベース繰入れ。00a の C-\*〔設計側〕とは別枠・二重計上しない）。
  3. **最新決定の同期**: 2-VPC 分離(B 案)・DU-U9O-09 per-brand 確定・対象外/条件付き DU の集計除外。
  4. **算術検算**: §8 の stale 3 件を是正。

---

## 1. 集計の是正（§8 の stale 分）

| # | 問題 | 是正 | 増減 |
|---|---|---|---:|
| 1 | DU-U2-09 が §8 で旧値 18（2026-08-15 に方式確定で 8 へ縮小済み） | 8 に更新 | **-10** |
| 2 | DU-U7-16（SRE ライブログ対策、2026-08-14 起票 +10）が §8 集計に不在 | U7 へ +10 | **+10** |
| 3 | **DU-U10-04（移行 4 集団）= 2026-08-17 対象外なのに §8 で 14 を計上** | 集計から除外 | **-14** |
| 4 | **DU-U10-11（PasswordHashProvider）= 🟡条件付（B-MIG-1 回答次第）なのにベース混入** | 分岐プール CB-4 へ移動 | **-8** |
| 5 | 🆕 DU-U6-14 新設（2-VPC 分離 B 案の VPC-M 構築、下記 §3 U6） | U6 へ +8 | **+8** |
| | **是正後ベース** | 1,044 → | **1,030** |

---

## 2. 8 月決定の製造への反映

- **2-VPC 分離（B 案、2026-08-18 採用）**: DU-U6-06（Lambda 実行基盤）は**層③同居 → VPC-M アタッチ**に変更。DU-U6-05 は **EPS-Admin / EPS-OIDC の Endpoint Service 化**を含む。**DU-U6-14 を新設**（VPC-M 構築 + IF Endpoint 群 + CGNAT/ルート、[topology note](brand-unit-2vpc-topology-2026-08-18.md)）。
- **DU-U9O-09 = per-brand 確定**（2026-08-16 B-AUDITLOG-BRAND-1）→ 🔒。実装内容 = per-brand ログ経路 + WORM 7 年整合。
- **P-17 再検討中**: U6 の全 IaC は**トポロジ確定（00a D-19）後に着手**。変更決定時は CB-2。
- **P-05 DR 再オープン**: DU-U8-02/03/04 は **DR 方式確定（00a D-18.2）が着手条件**。ウォーム復活時は CB-3。

---

## 3. 全 DU 内訳分解（ベース 1,030 人日）

> 表記: 「項目 人日; …」。S 帯（≤6）は 1〜2 項目で簡記。分解しても DU 合計は §8 値と一致（是正分除く）。

### U2 Keycloak 論理（96 ← 106-10）

| DU | 人日 | 内訳（work item × 人日） |
|---|---:|---|
| U2-01 | 4 | Realm/Org IaC 2; Org attribute 定義 1; 再現検証 1 |
| U2-02 | 10 | client/scope/mapper 定義 3; PrivateLink 経由疎通 3; storeToken=false×id_token_hint 検証 2; TTL 整合 2 |
| U2-03 | 11 | browser-std 2; HRD flow 2; first-broker 2; post-broker 2; forms サブフロー 1; Flow 回帰ハーネス 2 |
| U2-04 | 24 | HRD Authenticator 実装 6; JIT 制御(案 B) 6; Re-Activation 4; mfa_indicator/emit 3; ビルド・署名・SBOM ハーネス 3; 単体テスト固定 2 |
| U2-05 | 4 | Mapper 定義 2; syncMode=IMPORT 保護検証 1; PII 非搭載チェック 1 |
| U2-06 | 9 | User Profile 宣言 3; 3 経路完走検証 4; 検証失敗 UX 例外系 2 |
| U2-07 | 4 | SAML Client テンプレ 2; NameID/署名検証 1; Mapper 1 |
| U2-08 | 12 | キャッシュ設定 3; 接続予算適用 2; HRD 前提設定 2; 1000IdP 合成回帰の CI 組込 3; 監視閾値 2 |
| U2-09 | 8 | Realm IaC モジュール化(brand パラメータ化・1 Realm instantiate) 4; issuer 解決規律の RP 検証整合 2; theme per-realm 変数化 2 |
| U2-10 | 10 | BCL 連鎖 3; TTL 共通変数 2; acr/prompt/max_age 転送 3; login_hint 書式契約 2 |

### U3 ID・プロビ（134）

| DU | 人日 | 内訳 |
|---|---:|---|
| U3-01 | 10 | authz 系スキーマ DDL 4; brand_id 一級キー/不変条件の制約実装 3; マイグレーション+単体 3 |
| U3-02 | 11 | 判定 1-3 実装 4; Case 1-6 テーブル 3; 安全側拒否+単体固定 4 |
| U3-03 | 22 | 受信 API/認証 5; フィルタ/ページング 3; 属性正準化写像 4; DELETE→Soft Delete 写像 3; テナント二重照合 3; Validator 回帰 4 |
| U3-04 | 22 | projection ストア設計実装 4; 3 書込フィード(冪等 upsert) 6; /api/me/context read 4; version/最新勝ち 3; 読取性能チューニング 5 |
| U3-05 | 12 | outbox DDL+1Tx 書込 4; リレー Lambda(必達/再送/DLQ) 4; shadow 制御連携(冪等) 2; 数分リコンサイル 2 |
| U3-06 | 10 | 状態機械 S1-S10 実装 4; 3 段階削除(遮断/Soft/物理準備) 3; deprovisioned_at 起算+単体 3 |
| U3-07 | 11 | Re-Activation 判定(同一 Tx) 4; SCIM 除外条件 3; 誤発火シナリオ単体固定 4 |
| U3-08 | 12 | CronJob 実装 4; jit のみ対象/idpkc% 除外 3; 10M 分割実行+実測 5 |
| U3-09 | 9 | reactivated outbox 3; shadow enable 側(冪等) 3; 削除との対称性検証 3 |
| U3-10 | 9 | sub 通知受信ハンドラ 3; authz スタブ生成+バックフィル 3; 順序/冪等検証 3 |
| U3-11 | 6 | source レジストリ格納 3; Mapper/User Profile 生成連動 3 |

### U4 UX（74）

| DU | 人日 | 内訳 |
|---|---:|---|
| U4-01 | 10 | 画面 1 Theme 4; HRD 降格 UX 3; 応答同一化検証 3 |
| U4-02 | 5 | ニュートラルテーマ 3; messages 集約 1; CSRF hidden 不改変検査 1 |
| U4-03 | 12 | WebAuthn エンロール 4; TOTP(QR/手動キー) 3; ケース A-D UX 3; フォールバックリンク 2 |
| U4-04 | 12 | launchpad SPA 6; /api/me/apps 連携 3; 直叩き着地制御 3 |
| U4-05 | 5 | Sorry SPA 3; 表示 6/禁止 5 検証 2 |
| U4-06 | 10 | A11y 実装対応 6; CI 自動検査 2; 手動/当事者テスト準備 2 |
| U4-07 | 3 | messages 分離+決定明文化 3 |
| U4-08 | 4 | Forgot Password 画面 2; 本人確認方式実装 2 |
| U4-09 | 5 | セッション一覧 3; 自己失効 2 |
| U4-10 | 4 | 2 台目 step-up 必須化 3; 拒否 UX 1 |
| U4-11 | 4 | メール非依存リカバリ導線 3; Recovery Code UX 1 |

### U5 トークン・認可（74）

| DU | 人日 | 内訳 |
|---|---:|---|
| U5-01 | 5 | クレーム/TTL Config 3; PII チェック 3 箇所組込 2 |
| U5-02 | 8 | TE クライアント設定 4; 監査ログ 2; 境界テスト 2 |
| U5-03 | 12 | not-before push 3; 一斉 revoke 3; BCL 4; L4 Runbook 連動 2 |
| U5-04 | 5 | idm:* スコープセット 3; CC 開放+物理削除非定義検証 2 |
| U5-05 | 10 | RP ガイド完全版 6; Sorry 規約 2; 契約文言化 2 |
| U5-06 | 20 | SET エミッタ(outbox 起点) 6; SSF Stream 管理 4; RP receiver SDK 6; opt-in 配信+検証 4 |
| U5-07 | 10 | at+jwt 7 点検証 3; RFC 9470 step-up 3; 同時セッション SPI 2; TE act/may_act 2 |
| U5-08 | 4 | DPoP サイジング入力 2; Phase2 トリガー明文化 2 |

### U6 インフラ・NW（146 ← 138+8。**着手条件 = P-17 確定(00a D-19)**）

| DU | 人日 | 内訳 |
|---|---:|---|
| U6-01 | 12 | Org/Acct IaC 5; EventBridge 越境経路+resource policy 4; IAM 相互信頼なし検証 3 |
| U6-02 | 24 | ROSA HCP×2 プロビ IaC 8; Machine Pool 2 系統 4; サイジング適用(P-02 初回値) 4; HPA/テイント 4; G-IdP-Scale データセット併走整備 4 |
| U6-03 | 12 | identity Aurora 4; authz 系 Aurora 4; CMK/SG/ロール分離検証 4 |
| U6-04 | 13 | auth/idp Ingress(NFW→TGW→ALB) 5; api(API GW) 4; SPA(OAC) 2; REQ-IN-12/13 準拠検証 2 |
| U6-05 | 12 | kc-admin 内部 NLB 4; **EPS-Admin/EPS-OIDC Endpoint Service 化(2-VPC 反映)** 4; フェデ backchannel IF Endpoint+PHZ 4 |
| U6-06 | 10 | Lambda 実行基盤(**VPC-M アタッチに変更**) 4; API GW JWT L1 3; 専用サブネット/SG 3 |
| U6-07 | 12 | VPC Endpoint 群 4; Egress ルールグループ要求(B 部) 4; 1000+ FQDN 申請フロー 4 |
| U6-08 | 5 | L2 403+SG エッジ限定 3; hostname-admin 分離 2 |
| U6-09 | 5 | CIDR 台帳 IaC 化 3; 衝突検査 CI 2 |
| U6-10 | 9 | per-tenant レート制限 4; tenant_id 一貫強制 3; realm 分離基準 2 |
| U6-11 | 10 | ACM Private CA 4; 証明書自動ローテ 3; NetworkPolicy 3 |
| U6-12 | 6 | SES(sandbox 解除/SPF/DKIM/DMARC) 4; VPCE+バウンス 2 |
| U6-13 | 8 | Public Zone+PHZ 3; クロスアカウント RAM 2; Resolver ルール(REQ-OUT-04) 3 |
| **U6-14** 🆕 | 8 | **VPC-M 構築(Lambda/Endpoint/Aurora サブネット×3AZ)** 4; IF Endpoint 群配置(events/Secrets/KMS/Logs 等) 2; CGNAT/ルート設計適用(TGW 非 attach) 2（[topology](brand-unit-2vpc-topology-2026-08-18.md)） |

### U7 セキュリティ（166 ← 156+10）

| DU | 人日 | 内訳 |
|---|---:|---|
| U7-01 | 12 | CMK 設計 IaC 5; Key Policy 3 ロール 4; 削除/変更即時通知 3 |
| U7-02 | 6 | Realm Key 90 日+30 日並走 CronJob 4; 失敗時手動手順 2 |
| U7-03 | 22 | Event Listener 5; EventBridge→Risk Engine 基盤 5; Golden 4 シグナル実装 8; Phase 1a 通知 4 |
| U7-04 | 12 | 辞書 M-1〜14 実装 5; Aggregator 集中適用 4; 週 1 監査スキャン 3 |
| U7-05 | 5 | Pod Identity/IRSA 3; SA 最小権限検証 2 |
| U7-06 | 22 | AWS IIC 構成 6; Session Manager/踏み台 5; Break-Glass 実装 5; 訓練手順+監査 6 |
| U7-07 | 10 | 4 軸分離 IaC 5; SCP(両方に届く単一ロール禁止) 3; 検証 2 |
| U7-08 | 5 | PW ポリシー 2; WebAuthn/TOTP Policy 両 Realm 3 |
| U7-09 | 9 | REQ-IN-01 明細要求 3; KC Brute Force/列挙対策 4; Turnstile トリガー定義 2 |
| U7-10 | 10 | NHI 台帳 4; 孤立検知 CronJob 3; 失効伝播(ADR-064 機構) 3 |
| U7-11 | 5 | 同意記録+撤回 3; レシート 2 |
| U7-12 | 10 | ローテ Lambda 5; KC 2 世代並走 3; 直書き禁止 CI lint 2 |
| U7-13 | 9 | ミラー同期検証ゲート(Trivy+Cosign) 5; Critical CVE 緊急同期 Runbook 2; 検証 2 |
| U7-14 | 9 | SOP 実体文書 4; Tabletop 3; DPA 追跡機械化 2 |
| U7-15 | 10 | service-account client 分離 4; NLB SG 最小化 3; 全操作監査+mTLS 検討 3 |
| U7-16 | 10 | stdout PII マスキング実装(K-13) 4; Approved Access 有効化 2; SRE アクセス監査保全(CLO→CW) 4 |

### U8 可用性・DR（102。**U8-02/03/04 の着手条件 = DR 方式確定(00a D-18.2)**）

| DU | 人日 | 内訳 |
|---|---:|---|
| U8-01 | 10 | SLO Recording Rules 4; Multi-burn-rate Alert 4; ダッシュボード 2 |
| U8-02 | 12 | 再構築パイプライン IaC 6; 発動判断組込 3; 方式確定反映(D-18.2) 3 |
| U8-03 | 12 | Aurora Global 4; PITR/定期 SS 4; Vault Lock(削除権限分離) 4 |
| U8-04 | 15 | RB-DR Runbook 実体 6; Game Day H1 準備 4; 実施+AAR 5 |
| U8-05 | 5 | IaC 再適用経路 3; Aurora Global 経路+Realm Export 全廃検証 2 |
| U8-06 | 5 | min3/PDB/topologySpread 3; /health/ready+HPA 2 |
| U8-07 | 8 | JDBC timeout/Agroal 調整 4; Writer フェイルオーバー実測+Proxy 要否 4 |
| U8-08 | 8 | ローリング戦略実装 4; Staging 1000IdP 回帰枠 4 |
| U8-09 | 6 | SLA/RPO 文言 3; Failover 後 WAF/ITDR 強化 3 |
| U8-10 | 10 | ブランド系 DR 編入 IaC 5; 大阪 projection 再構築 3; SSOT 表 2 |
| U8-11 | 8 | Promote 後 outbox 必達 4; 二重送信防止+Game Day 項目化 4 |
| U8-12 | 3 | ADR-051 反映 3 |

### U9 運用・IaC（150）

| DU | 人日 | 内訳 |
|---|---:|---|
| U9I-01 | 22 | モジュール分割設計 6; state マトリクス 4; 基盤層実装 6; テナント層+日次ドリフト検知 6 |
| U9I-02 | 14 | GH Actions 5; ArgoCD/GitOps 5; ECR ミラー+SLSA 4 |
| U9I-03 | 12 | 別 WF+ECR コンテナ Lambda 5; SAM/CDK 2 アカウント 4; EventBridge Scheduler バッチ枠 3 |
| U9O-01 | 13 | OTel Collector 5; Micrometer 統合 4; Cardinality/Trace Sampling 4 |
| U9O-02 | 13 | Hot/Cold 層 IaC 5; SIEM 相関 4; 監査スキャン 4 |
| U9O-03 | 25 | Runbook 残 22 冊(必須 13 は 00a G-1) 12; 禁則 K-1〜13 CI 機械強制 5; ゲート G-* 運用組込 4; 体系整備 4 |
| U9O-04 | 12 | オンボーディング API 6; メタデータ自動更新組込(A-9 結果) 3; 証明書ローテ運用 3 |
| U9O-05 | 11 | Canary 実装 5; App/OpenAPI Registry 連携 4; 監査 Acct 集約 2 |
| U9O-06 | 10 | 決定ログ実装 4; サンプリング 2; recert キャンペーン 4 |
| U9O-07 | 5 | 合成データ/マスキング 3; 機械検査 2 |
| U9O-08 | 8 | X-Ray/CW アラーム 4; AMG ダッシュボード+Runbook 紐付け 4 |
| U9O-09 | 5 | **per-brand 確定済(B-AUDITLOG-BRAND-1)** → per-brand ログ経路実装 3; WORM 7 年整合 2 |

### U10 連携・移行（88 ← 110-14-8）

| DU | 人日 | 内訳 |
|---|---:|---|
| U10-01 | 14 | SAML Client CL-SN-01 実装 5; パターン② 統合 5; Matching Field 突合+検証 4 |
| U10-02 | 24 | OpenAPI 定義 4; CRUD 実装 6; 権限/authz 実装 5; projection read 3; /api/me/* 3; CC 経路 3 |
| U10-03 | 12 | HMAC 署名 3; DLQ/再送 8 回 4; 配信 7 種 3; ±5 分リプレイ防止 2 |
| ~~U10-04~~ | 0 | 🚫 対象外(2026-08-17、移行はアプリ側)。**§8 の 14 計上を除外是正** |
| U10-05 | 5 | DSAR SOP 3; 応答期限契約化 2 |
| U10-06 | 6 | 遮断連鎖 T-1〜5 4; 残余時間契約明示 2 |
| U10-07 | 4 | RTBF 境界文書 2; 決定ログ sub 仮名化 2 |
| U10-08 | 12 | M0-M3 テナント別 Runbook 5; 重複 sys_user 統合スクリプト 4; 受入 T-1〜5 3 |
| U10-09 | 5 | Break Glass 構成 3; SIEM 通知+四半期テスト 2 |
| U10-10 | 6 | SN OAuth クライアント(CC) 3; 他アプリ OIDC RP 登録+サイレント発行検証 3 |
| ~~U10-11~~ | 0 | 🟡条件付(B-MIG-1 回答次第) → **分岐プール CB-4 へ移動(-8)** |

**ベース合計 = 96+134+74+74+146+166+102+150+88 = 1,030 人日** ✓

---

## 4. 構築側 分岐プール CB-*（トリガー顕在時のみベース繰入れ。00a C-*〔設計側〕と別枠）

| 分岐 ID | トリガー(〜の状態で〜の場合) | 追加作業(構築側) | 増分 |
|---|---|---|---:|
| CB-1 | G-SPI-Compat FAIL で SPI 方式変更(upstream 継続/実装方式変更)の場合 | U2-04 SPI 群の再実装 + Flow/回帰の作り直し | +15 |
| CB-2 | P-17 でクラスタトポロジ変更を決定した場合(00a D-19/C-D19 の構築側) | U6 IaC 手戻り(クラスタ/CIDR/EPS/越境経路の作り直し) | +20 |
| CB-3 | D-18.2 で部分ウォーム DR 復活を決定した場合(00a C-D18 の構築側) | U8 常設構成(大阪クラスタ/常時 Global)構築 | +12 |
| CB-4 | B-MIG-1 で「旧ハッシュが KC ネイティブ外」と回答された場合 | DU-U10-11 Custom PasswordHashProvider SPI | +8 |
| CB-5 | 他組織回答が要求と乖離した場合(00a C-B1 の構築側) | Ingress/Egress(U6-04/07)の再構築 | +8 |
| CB-6 | G-SCIM FAIL で Facade 方式変更の場合 | U3-03/04 の受信/射影再実装 | +10 |
| | **合計** | | **+73** |

---

## 5. 工程分割の更新（gap-audit §9 の置換値）

| 工程 | 人日 | 根拠 |
|---|---:|---|
| ① 基本設計クローズ | **269**（+条件付き 65） | [00a v2](../00a-remaining-tasks-and-effort.md) |
| ② 詳細設計 | **≈412** | 1,030 × 40% |
| ③ 構築 | **≈618** | 1,030 × 60% |
| ④ テスト | **≈363** | [gap-audit §10](wbs-gap-audit-2026-08-12.md) |
| **ベース総計** | **≈1,662** | 269+412+618+363（旧 1,676 → 是正 -14） |
| **条件付きプール** | **+138** | 設計側 C-* 65 + 構築側 CB-* 73 |
| **上限(全分岐顕在時)** | **≈1,800** | |

---

## 6. Excel 反映時の注意

- WBS(詳細設計_製造) は本ノート §3 の内訳列を「サブ行 or 内訳セル」で反映。DU 合計は §3 の値が正（§8 stale 3 件は本ノートで是正済み）。
- U10-04(0)・U10-11(0→CB-4) の行は残して状態列で対象外/条件付を明示（行削除しない）。
- CB-* は WBS(基本設計) の C-* プール表と同形式で「構築分岐」表を追加（未顕在/顕在の状態管理）。
- ②/③ の 40/60 分割は per-DU 一律適用（従来どおり）。
