# §FR-API-8 観測性（ログ・トレース・メトリクス）

> 元データ: [../hearing-checklist.md C-1](../hearing-checklist.md#c-1-観測性fr-api-8)
> 対象: アプリリード / SRE / SecOps
> 関連章: [§FR-API-8](../proposal/fr/08-observability.md)

---

### 【Log Group Retention の業務カテゴリ別マッピング】 (API-C-811, 🟡)

CloudWatch Log Group の保存期間を業務カテゴリ別にマッピングする方針をご教示ください。

本標準の暫定提案：

| カテゴリ | Retention | 用途 |
|---|---|---|
| 一般アプリログ | 30 日 | 開発・トラブルシュート |
| API access log | 90 日 | 利用分析 |
| 監査関連ログ | 7 年 | コンプラ |
| デバッグログ | 7 日 | 短期 |

業務別の調整提案がございましたらご教示ください。
**目的**: [§FR-API-8 §8.1 / §NFR-API-7](../proposal/nfr/07-compliance.md) のログ保持。CloudWatch Logs の長期保管はコスト感度が高いため、Retention の標準化が重要です（既定 "Never expire" は禁止）。

---

### 【Data Protection Policy の追加カスタムパターン】 (API-C-812, 🟢)

CloudWatch Logs Data Protection Policy（managed identifier でクレカ・SSN・AWS access key を自動マスク）に追加するカスタムパターンの要否をご教示ください。
- 社内特有の機密パターン（社員番号 / 内部ID 等）
- 業界固有パターン
- 追加なし（Managed のみで十分）
**目的**: [§FR-API-8 §8.1 / §NFR-API-4 §4.2](../proposal/nfr/04-security.md) の PII マスキング。

---

### 【高ボリューム API のサンプリング率】 (API-C-813, 🟢)

ヘルスチェック・高頻度 GET 等の高ボリューム API のログサンプリング率の標準値をご教示ください。
- 全件出力（100%）：完全だがコスト大
- ヘルスチェックは 1%、業務 API は 100%
- 業務別の調整
**目的**: [§FR-API-8 §8.1 / §NFR-API-8](../proposal/nfr/08-cost.md) のログコスト最適化。

---

### 【新規プロジェクト ADOT 採用必須化】 (API-C-821, 🟡)

新規プロジェクトのトレース実装を **ADOT (AWS Distro for OpenTelemetry) 必須化**する方針でよろしいかご確認ください。
- AWS X-Ray SDK は **2026-02-25 maintenance mode 入り**（更新終了）
- ADOT は OpenTelemetry 準拠で、X-Ray バックエンドへの送信も継続可能
- 新規は ADOT、既存は段階移行が公式推奨経路
**目的**: [§FR-API-8 §8.2](../proposal/fr/08-observability.md) のトレース標準。X-Ray SDK のサポート切れに伴う必須移行です。

---

### 【既存 X-Ray SDK プロジェクトの ADOT 移行】 (API-C-822, 🟡)

既存の X-Ray SDK 利用プロジェクトの **ADOT 移行スケジュール**をご教示ください。
- 半期 / 1 年以内の全件移行
- 次回更新時に併せて移行
- 当面継続（X-Ray SDK の maintenance 状態で受容）
**目的**: [§FR-API-8 §8.2 / §NFR-API-9](../proposal/nfr/09-compatibility.md) の移行計画。

---

### 【サンプリング率の業務別デフォルト】 (API-C-823, 🟢)

トレースサンプリング率の業務別デフォルトをご教示ください。
- 決済 / 認証：100%（全件トレース）
- 一般業務：5% + 1 req/sec（X-Ray 既定）
- バッチ：1%
**目的**: [§FR-API-8 §8.2 / §NFR-API-8](../proposal/nfr/08-cost.md) のトレースコスト最適化。

---

### 【SLO デフォルトテンプレ】 (API-C-831, 🟡)

SLO（Service Level Objective）のデフォルトテンプレの妥当性をご評価ください。

本標準の暫定提案：

| Tier | 可用性 | レイテンシ p99 |
|---|---:|---:|
| Critical | 99.99% | < 300ms |
| Standard | 99.95% | < 1s |
| Internal | 99.5% | < 5s |

調整提案がございましたらご教示ください。
**目的**: [§FR-API-8 §8.3 / §NFR-API-1 §1.1 / §NFR-API-2 §2.1](../proposal/nfr/02-performance.md) の SLO 標準。

---

### 【アラート通知先・エスカレーション】 (API-C-832, 🟡)

アラートの通知先プラットフォームとエスカレーションルールをご教示ください。
- 通知先：PagerDuty / Opsgenie / Slack / メール
- エスカレーション基準：Sev1 は 15 分以内応答、5 分応答なしで次のオンコールへ等
**目的**: [§FR-API-8 §8.3 / §NFR-API-6 §6.1](../proposal/nfr/06-operations.md) の運用体制連動。

---

### 【Synthetics の必須化範囲】 (API-C-833, 🟢)

CloudWatch Synthetics（外形監視 Canary）の必須化範囲をご教示ください。
- Critical Public API は必須
- 全 Public API
- 任意（アプリ判断）
**目的**: [§FR-API-8 §8.3](../proposal/fr/08-observability.md) の外形監視。SLO 計測の独立性確保に有効です。

---

## ヒアリング後の確定事項チェックリスト

- [ ] Log Group Retention の業務カテゴリマッピング（C-811）
- [ ] ADOT 採用必須化（C-821）
- [ ] SLO デフォルトテンプレ（C-831）
- [ ] アラート通知先（C-832）

これらが揃うと **§FR-API-8 観測性** と **アラート運用標準** を確定できます。
