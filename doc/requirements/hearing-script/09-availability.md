# C-1: 可用性・性能・DR

> 元データ: [../hearing-checklist.md](../hearing-checklist.md)  
> 対象: インフラチーム / SRE / セキュリティチーム  
> 関連: [proposal §NFR-1](../proposal/nfr/01-availability.md), [§NFR-2](../proposal/nfr/02-performance.md), [§NFR-5](../proposal/nfr/05-dr.md)
>
> **新 §X.Y 構造との対応**（[hearing-checklist.md §0〜§5](../hearing-checklist.md) で subject-matter 軸の一覧確認可）:
> - **§5.1 可用性・SLA・DR**: C-101（SLA 目標）、C-102（RTO）、C-103（RPO）、C-104（フェイルオーバー方式）、C-107（メンテナンス窓）
> - **§5.2 性能・スケール**: C-105（認証応答時間）、C-106（ピーク時想定）
>
> hearing-script/ は **会議組み立て用に旧 Phase 軸**でファイル分割、hearing-checklist.md は **読み物として subject-matter 軸**で集約。両軸を併用。

---

### 【SLA 目標】 (C-101, 🔥)

本基盤の SLA 目標値をご教示ください:
- 99.9%（年間ダウンタイム 約 8.76 時間）
- 99.95%（年間ダウンタイム 約 4.38 時間）
- 99.99%（年間ダウンタイム 約 52.6 分）

**目的**: 可用性設計の核心。**99.99% は Multi-AZ + Multi-Region + Active-Active 必須**となり、Cognito（AWS マネージドで Multi-AZ 自動）と Keycloak（自前 ECS / EKS で Multi-AZ + Aurora Global DB 設計が必要）でコスト・運用工数が大きく変わります。

---

### 【RTO（目標復旧時間）】 (C-102, 🔥)

災害復旧時の **目標復旧時間（Recovery Time Objective）** をご教示ください。
具体的な時間（分 / 時間 / 日）でお答えいただけますと幸いです。
- 5 分以内（Hot Standby）
- 1 時間以内（Warm Standby）
- 4 時間以内（Pilot Light）
- 24 時間以内（Backup & Restore）

**目的**: DR 構成の選定（Pilot Light / Warm Standby / Hot Standby / Active-Active）、Cognito の Multi-Region 構成（手動 User Pool 作成）/ Keycloak の Aurora Global DB + ECS Multi-Region 設計の判断、コスト見積に必要な情報です。

---

### 【RPO（目標復旧時点）】 (C-103, 🔥)

災害復旧時の **目標復旧時点（Recovery Point Objective）** = データ損失許容量をご教示ください:
- 0 分（同期レプリケーション、データ損失ゼロ）
- 5 分以内
- 1 時間以内
- 24 時間以内（日次バックアップ）

**目的**: データレプリケーション設計、Aurora Global DB 採用、Cognito Multi-Region データ同期方式の判断に必要な情報です。**RPO 0 は同期レプリケーション必須**でレイテンシ影響が出ます。

---

### 【フェイルオーバー方式】 (C-104, 🔥)

DR 時のフェイルオーバー方式をご教示ください:
- 自動（Route 53 ヘルスチェック / 自動切替）
- 手動（運用チームが判断して切替）
- ハイブリッド（自動検知 + 手動承認）

**目的**: DR 運用フロー設計、誤判定リスク（自動）vs 切替遅延（手動）のトレードオフ判断、運用体制との整合性確認に必要な情報です。

---

### 【認証応答時間目標】 (C-105, 🟡)

認証エンドポイントの応答時間目標をご教示ください:
- P95（95 パーセンタイル）の目標 ms
- P99（99 パーセンタイル）の目標 ms

**目的**: パフォーマンス設計、Cognito / Keycloak の単一ノード性能（Keycloak 26.4 ベンチマーク: 1 vCPU で 15 logins/sec）への適合性確認、必要なリソース見積に必要な情報です。

---

### 【ピーク時想定】 (C-106, 🟡)

朝の業務開始時刻や月末処理など、ピーク時の同時アクセス倍率の想定をご教示ください。
平常時の何倍程度（例: 3 倍 / 5 倍 / 10 倍）でお答えいただけますと幸いです。
**目的**: Auto Scaling 設定（Keycloak ECS / EKS の最小 / 最大タスク数）、Cognito の RPS クォータ申請（UserAuthentication 120 RPS が Soft Limit）への対応設計、容量設計に必要な情報です。

---

### 【計画メンテナンス窓】 (C-107, 🟢)

月あたりの計画メンテナンス窓として許容される時間をご教示ください:
- 月 1 時間以内
- 月 4 時間以内
- 月 8 時間以内
- メンテナンス窓不要（無停止運用必須）

**目的**: SLA 計算への影響、メンテナンス窓設定（深夜帯 / 週末等）、ローリングアップデート方式の必要性判断に必要な情報です。
