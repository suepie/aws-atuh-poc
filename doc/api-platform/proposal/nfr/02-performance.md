# §NFR-API-2 性能

> 親 SSOT: [../00-index.md](../00-index.md) §NFR-API-2
> IPA グレード: **B. 性能・拡張性**（応答時間）
> ヒアリング: [../../hearing-script/09-nfr.md](../../hearing-script/09-nfr.md)

---

## §2.0 前提と背景

### §2.0.1 用語整理

| 用語 | 定義 |
|---|---|
| **レイテンシ** | リクエストから応答までの時間 |
| **p99** | 99 パーセンタイル（99% のリクエストがこの時間内に応答） |
| **Cold start** | Lambda / Fargate 等で関数・コンテナが新規起動する遅延 |
| **TPS / RPS** | Transactions / Requests per second |

### §2.0.2 なぜここ（§2）で決めるか

性能 SLO は実装ランタイム選定（§FR-5/6）に直接影響する。Cold start 許容可否で Serverless / Container の判断が分かれる。

### §2.0.3 IPA グレード対応

| IPA 中項目 | 本章での対応 |
|---|---|
| 通常時の業務量 / 応答時間 | §2.1 |
| 業務量の増減傾向 / ピーク係数 | §NFR-API-3 拡張性 |

### §2.0.4 §2.0.A 本標準のスタンス

| 基本方針 | 本章での具体化 |
|---|---|
| 絶対安全 | レイテンシ要件は **CloudWatch メトリクスで自動アラート**、SLO 違反通知 |
| どんなアプリでも | Tier 別レイテンシテンプレ（Real-time / Standard / Batch） |
| 効率よく | Cold start 対策（Provisioned Concurrency）は要件時のみ。固定費明示 |
| 運用負荷・コスト最小 | Memory size 最適化（過剰割当抑止）、サンプリング |

### §2.0.5 本章で扱うサブセクション

| § | サブセクション |
|---|---|
| §2.1 | レイテンシ Tier |
| §2.2 | Cold start 対策 |
| §2.3 | 性能テスト・観測 |

---

## §2.1 レイテンシ Tier

**このサブセクションで定めること**：API カテゴリ別のレイテンシ目標。
**主な判断軸**：ユーザー体験、計測可能性。
**§2 全体との関係**：§2.2 / §2.3 の設計目標。

### §2.1.1 ベースライン

| Tier | p50 | p99 | 採用条件 |
|---|---:|---:|---|
| **Real-time** | < 100ms | < 300ms | エンドユーザー直接 / モバイル |
| **Standard** | < 300ms | < 1s | 通常 Web API |
| **Bulk** | < 1s | < 5s | レポート / 集計 |
| **Async** | N/A | N/A | キュー経由、SLA は処理完了時間で別管理 |

### §2.1.2 TBD / 要確認

- Q: **既存アプリの実測ベースライン**は取得可能か → `API-C-1001`
- Q: 各 Tier の **割当方針**（用途別 / クリティカリティ別）→ `API-C-1002`

---

## §2.2 Cold start 対策

**このサブセクションで定めること**：Lambda / Fargate の Cold start への対応標準。
**主な判断軸**：レイテンシ要件 vs 固定費。
**§2 全体との関係**：§2.1 のうち Real-time Tier 達成手段。

### §2.2.1 ベースライン

| 手段 | 採用条件 |
|---|---|
| **Memory size 増 → CPU 比例** | 第一選択。コスト効果が良い |
| **arm64 (Graviton)** | コストパフォーマンス改善 |
| **SnapStart**（Java / .NET / Python） | 既定で有効化可能なときに有効 |
| **Provisioned Concurrency** | Real-time Tier かつ実測で必要なときのみ。**固定費を明示** |
| **Always-On コンテナ（ECS）** | コンテナ系で Cold start 完全排除 |

### §2.2.2 TBD / 要確認

- Q: Real-time Tier API に **Provisioned Concurrency を既定設定するか** → `API-C-1011`
- Q: ECS Fargate task の **既定 desired count**（Cold start なしの起動状態保持）→ `API-C-1012`

---

## §2.3 性能テスト・観測

**このサブセクションで定めること**：性能 SLO 達成可否の継続的検証。
**主な判断軸**：継続観測、誤検知抑制。
**§2 全体との関係**：§2.1 SLO の根拠データ。

### §2.3.1 ベースライン

- **負荷テスト**：本番リリース前に必須。Artillery / k6 / Locust 等
- **継続観測**：CloudWatch Metrics + X-Ray Service Map / ADOT で p50 / p99 / Latency by integration
- **アラート**：p99 が SLO を超えたら 5 分継続で通知

### §2.3.2 TBD / 要確認

- Q: 負荷テストの **本番リリース前必須化**範囲（Critical / Standard / 全部）→ `API-C-1021`
- Q: 性能リグレッション検知の **CI への統合** → `API-C-1022`

---

## §2.x 関連ドキュメント

- [§NFR-API-1 可用性](01-availability.md) — タイムアウトとの関係
- [§NFR-API-3 拡張性](03-scalability.md) — TPS / RPS のスケール
- [§FR-API-5 Serverless 標準](../fr/05-serverless-standard.md) — Lambda 性能調整
