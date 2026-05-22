# §NFR-API-3 拡張性

> 親 SSOT: [../00-index.md](../00-index.md) §NFR-API-3
> IPA グレード: **B. 性能・拡張性**（スケール）
> ヒアリング: [../../hearing-script/09-nfr.md](../../hearing-script/09-nfr.md)

---

## §3.0 前提と背景

### §3.0.1 用語整理

| 用語 | 定義 |
|---|---|
| **拡張性** | 負荷増に対してスループット・容量をスケールできる能力 |
| **アカウントクォータ** | AWS リソースごとのアカウント上限（Lambda 同時実行 / API Gateway RPS 等） |
| **垂直スケール / 水平スケール** | 1 インスタンスを大きく / インスタンス数を増やす |

### §3.0.2 なぜここ（§3）で決めるか

スケール上限は **設計時の前提制約**であり、達成 SLO（§NFR-1/2）と表裏一体。アカウントクォータの既定値で詰むケースを早めに把握する。

### §3.0.3 IPA グレード対応

| IPA 中項目 | 本章での対応 |
|---|---|
| ピーク時の業務量 / ピーク係数 | §3.1 |
| 拡張性（スケール容易性） | §3.2 |

### §3.0.4 §3.0.A 本標準のスタンス

| 基本方針 | 本章での具体化 |
|---|---|
| 絶対安全 | アカウントクォータの **早期増枠申請**で本番直前の障害を防ぐ |
| どんなアプリでも | Auto Scaling 既定、Reserved Concurrency / Task Count は要件時のみ明示 |
| 効率よく | スケール限界の **継続観測**（80% 到達でアラート） |
| 運用負荷・コスト最小 | Predictive Scaling は不要、Target Tracking 中心 |

### §3.0.5 本章で扱うサブセクション

| § | サブセクション |
|---|---|
| §3.1 | スケール目標 |
| §3.2 | Auto Scaling 設定 |
| §3.3 | アカウントクォータ管理 |

---

## §3.1 スケール目標

**このサブセクションで定めること**：API カテゴリ別の想定 TPS とピーク係数。
**主な判断軸**：実測 / 想定の根拠、ピーク × N% の余裕。
**§3 全体との関係**：§3.2 / §3.3 の入力。

### §3.1.1 ベースライン

| Tier | 平常 TPS | ピーク TPS | ピーク係数 | 想定アカウント |
|---|---:|---:|---:|---|
| **High** | 1,000 | 10,000 | 10x | 大規模 Public |
| **Medium** | 100 | 1,000 | 10x | 通常本番 |
| **Low** | 10 | 100 | 10x | 内部・社内 |

- **アカウント既定**（Lambda 同時実行 1,000 / API GW 10,000 RPS / DynamoDB on-demand 4,000 RCU・40,000 WCU 等）を **早期に把握**

### §3.1.2 TBD / 要確認

- Q: 既存アプリの **実測ピーク**取得 → `API-C-1101`
- Q: 季節変動・キャンペーン時のピーク係数（10x で足りるか）→ `API-C-1102`

---

## §3.2 Auto Scaling 設定

**このサブセクションで定めること**：スケール戦略の標準。
**主な判断軸**：Target Tracking / Step / Schedule。
**§3 全体との関係**：§3.1 のスケール目標を達成する手段。

### §3.2.1 ベースライン

| サービス | スケール手段 | 既定 |
|---|---|---|
| **Lambda** | 自動（同時実行） | Reserved Concurrency は明示要件時のみ |
| **ECS** | Application Auto Scaling | Target Tracking（CPU 70% / Memory 70%）+ ALB request count per target |
| **DynamoDB** | on-demand or auto scaling | on-demand を新規既定（不規則トラフィック）|
| **Aurora** | Aurora Serverless v2 / Auto Scaling Read Replica | 要件次第 |

### §3.2.2 TBD / 要確認

- Q: DynamoDB の **on-demand vs provisioned + auto-scaling** の選定基準 → `API-C-1111`
- Q: ECS の **scale-out 余裕**（cooldown / step）→ `API-C-1112`

---

## §3.3 アカウントクォータ管理

**このサブセクションで定めること**：AWS アカウントクォータの監視と増枠申請。
**主な判断軸**：本番障害の予防、Service Quotas / Trusted Advisor の活用。
**§3 全体との関係**：§3.1 ピークを達成する前提。

### §3.3.1 ベースライン

- **Service Quotas** で重要クォータをダッシュボード化
- **CloudWatch アラーム** で 80% 到達通知
- **本番リリース前にピーク係数 × 2 まで増枠申請**
- 増枠リードタイム：通常 1-3 営業日（Business / Enterprise Support 推奨）

### §3.3.2 必須監視クォータ（暫定）

- Lambda 同時実行
- Lambda 関数数 / レイヤー数
- API Gateway アカウント RPS
- API Gateway 1 アカウントあたりの API 数 / Usage Plan 数
- ECS タスク数・ALB 数
- DynamoDB on-demand limit
- VPC 数 / ENI 数

### §3.3.3 TBD / 要確認

- Q: 本番アカウントの **必須増枠リスト**を Service Catalog で初期化するか → `API-C-1121`
- Q: クォータ監視の **アラート通知先** → `API-C-1122`

---

## §3.x 関連ドキュメント

- [§NFR-API-2 性能](02-performance.md) — TPS / レイテンシの相関
- [§FR-API-3 流量制御](../fr/03-throttling-quota.md) — スロットルとの境界
