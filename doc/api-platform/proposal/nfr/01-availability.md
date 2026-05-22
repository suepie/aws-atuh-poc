# §NFR-API-1 可用性

> 親 SSOT: [../00-index.md](../00-index.md) §NFR-API-1
> IPA グレード: **A. 可用性**
> ヒアリング: [../../hearing-script/09-nfr.md](../../hearing-script/09-nfr.md)

---

## §1.0 前提と背景

### §1.0.1 用語整理

| 用語 | 定義 |
|---|---|
| **SLA / SLO / SLI** | サービス提供約束 / 目標 / 計測指標 |
| **可用性** | 単位期間中、正常応答できる時間の割合（例 99.95% / 99.99%） |
| **マルチ AZ** | 同一リージョン内の複数 AZ にまたがって構成 |
| **エフェメラル障害** | 短時間で復旧する瞬断・スロットル |

### §1.0.2 なぜここ（§1）で決めるか

可用性は実装ランタイム（§FR-5/6）と公開境界（§FR-1）の設計を制約する。SLO を最初に定めることで、マルチ AZ 要否・冗長度・タイムアウト設計が決まる。

### §1.0.3 IPA グレード対応

| IPA 中項目 | 本章での対応 |
|---|---|
| 継続性 / 稼働率 | §1.1 |
| 目標復旧水準（業務単位）/ RPO / RTO | §NFR-API-5 DR に分離 |
| 業務継続性 | §NFR-API-5 |

### §1.0.4 §1.0.A 本標準のスタンス

| 基本方針 | 本章での具体化 |
|---|---|
| 絶対安全 | マネージドサービスの SLA を最大限活用、自前冗長は最小限 |
| どんなアプリでも | API カテゴリ別の SLO テンプレ（Critical / Standard / Internal） |
| 効率よく | マルチ AZ は既定（Lambda は自動、ECS は AZ spread 設定）、マルチリージョンは要件時のみ |
| 運用負荷・コスト最小 | Active-Active マルチリージョンはコスト高、Active-Standby を標準 |

### §1.0.5 本章で扱うサブセクション

| § | サブセクション |
|---|---|
| §1.1 | API カテゴリ別 SLO |
| §1.2 | マルチ AZ 構成 |
| §1.3 | 障害分離・タイムアウト |

---

## §1.1 API カテゴリ別 SLO

**このサブセクションで定めること**：API のクリティカリティ別に SLO を定義。
**主な判断軸**：ビジネス影響度、マネージドサービスの実 SLA。
**§1 全体との関係**：§1.2 / §1.3 / §NFR-5 DR の設計目標。

### §1.1.1 ベースライン

| カテゴリ | 可用性 SLO | RTO 目安 | 採用条件 |
|---|---:|---:|---|
| **Critical**（決済 / 認証） | 99.99% | < 5 分 | 売上直結 / 法規制 |
| **Standard**（業務 API） | 99.95% | < 1 時間 | 通常の本番 |
| **Internal**（社内利用） | 99.5% | < 4 時間 | 内部向け |
| **Batch / Async** | 99.0% | < 24 時間 | バッチ・非同期 |

参考：AWS マネージドの SLA
- API Gateway / Lambda / ECS Fargate / ALB：99.95%
- CloudFront：99.9%（月次計測）
- DynamoDB：99.99%（Global Tables は 99.999%）

### §1.1.2 TBD / 要確認

- Q: **新規 API のデフォルトカテゴリ**を Standard とするか → `API-C-901`
- Q: Critical API の **マネージド単体 SLA で達成できない場合**の構成（マルチリージョン / DynamoDB Global Tables 必須）→ `API-C-902`

---

## §1.2 マルチ AZ 構成

**このサブセクションで定めること**：単一リージョン内の冗長度標準。
**主な判断軸**：マネージドサービスの既定挙動、明示設定が要るところを押さえる。
**§1 全体との関係**：§1.1 の SLO 達成手段。

### §1.2.1 ベースライン

- **API Gateway / Lambda**：マネージドで自動マルチ AZ
- **ECS Fargate**：**`spread` AZ strategy** を既定（2025.09 以降 AZ rebalancing default 有効）、3 AZ サブネットを使用
- **ALB**：3 AZ を有効化
- **RDS / Aurora**：Multi-AZ 必須
- **DynamoDB**：AZ 障害は自動透過

### §1.2.2 TBD / 要確認

- Q: **3 AZ を新規アカウントの既定とするか**（東京は 4 AZ あり、コスト要件）→ `API-C-911`

---

## §1.3 障害分離・タイムアウト

**このサブセクションで定めること**：依存先障害が伝播しないための設計。
**主な判断軸**：cascading failure を防ぐ、依存先に応じたタイムアウト。
**§1 全体との関係**：§1.1 SLO 達成のための実装ガイダンス。

### §1.3.1 ベースライン

- **タイムアウト階層**（必須）：
  - クライアント → API Gateway（< 29 秒、API GW 上限）
  - API Gateway → Lambda / バックエンド（< 28 秒）
  - Lambda / ECS → DB / 外部 API（< 5 秒、要件次第）
- **リトライ**：Exponential backoff + jitter、最大回数明示
- **Circuit Breaker**：外部依存に対して導入（OSS ライブラリ / AppMesh / Lambda 内）
- **Bulkhead**：Lambda Reserved Concurrency や ECS Task 数で依存先別に隔離

### §1.3.2 TBD / 要確認

- Q: タイムアウト階層の **業務別標準値** → `API-C-921`
- Q: Circuit Breaker の **実装手段**（ライブラリ標準化）→ `API-C-922`

---

## §1.x 関連ドキュメント

- [§NFR-API-5 DR](05-dr.md) — マルチリージョン・RPO/RTO
- [§NFR-API-2 性能](02-performance.md) — レイテンシ目標とタイムアウト
- [§FR-API-6 Container 標準](../fr/06-container-standard.md) — AZ spread strategy
