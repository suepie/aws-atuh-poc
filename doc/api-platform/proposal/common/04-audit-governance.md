# §C-API-4 監査アカウントとのガバナンス境界

> 親 SSOT: [../00-index.md](../00-index.md) §C-API-4
> ヒアリング: [../../hearing-script/07-guardrails.md](../../hearing-script/07-guardrails.md)

---

## §C-4.0 前提と背景

### §C-4.0.1 用語整理

| 用語 | 定義 |
|---|---|
| **監査アカウント** | Security Tooling 兼 FMS Delegated Admin、Control Tower の Audit account 相当 |
| **配信（push）** | 監査アカウントから各アプリへの FMS / Service Catalog / SCP / Config Rules の自動配布 |
| **集約（pull）** | 各アプリから監査アカウントへの CloudTrail / Config / S3 access log の証跡集約 |
| **責任分界点** | 監査アカウントとアプリアカウントの責任範囲の境界 |

### §C-4.0.2 なぜここ（§C-4）で決めるか

要望テーマの「**監査アカウントの FirewallManager からのルールの説明と運用**」のうち、**運用面の境界**を本章で定義する。配信ルールの **中身** は §FR-API-7 ガードレール、本章は **役割分担・運用責務** を定義する。

```mermaid
flowchart TB
    Audit[監査アカウント<br/>(Delegated Admin)]

    Audit -->|push: FMS| WAF[各アプリ:<br/>WAF / SG / Network FW]
    Audit -->|push: Config Rules| Compliance[各アプリ:<br/>Compliance 監視]
    Audit -->|push: Service Catalog| Stack[各アプリ:<br/>標準スタック]
    Audit -->|push: SCP| Preventive[各アプリ:<br/>予防的制御]

    Apps[各アプリアカウント] -->|pull: CloudTrail| Audit
    Apps -->|pull: Config aggregator| Audit
    Apps -->|pull: S3 access log| Audit
    Apps -->|pull: VPC Flow Logs| Audit
```

### §C-4.0.3 §C-4.0.A 本標準のスタンス

| 基本方針 | 本章での具体化 |
|---|---|
| 絶対安全 | 監査アカウントの権限分離、Delegated Admin の操作監査 |
| どんなアプリでも | 配信ポリシーは **タグベース**（OU 単位ではなくリソース属性で適用） |
| 効率よく | アプリ側が「気にせず」標準に従えば自動的にガードレール準拠になる |
| 運用負荷・コスト最小 | 多層防御（WAF + Config + SCP + Service Catalog）でカバー範囲を分散 |

### §C-4.0.4 本章で扱うサブセクション

| § | サブセクション |
|---|---|
| §C-4.1 | 役割分担・責任分界点 |
| §C-4.2 | 配信パス（push） |
| §C-4.3 | 集約パス（pull） |
| §C-4.4 | 操作監査 |

---

## §C-4.1 役割分担・責任分界点

**このサブセクションで定めること**：監査アカウント / Platform チーム / アプリチームの責任境界。
**主な判断軸**：明確な権限分離、誰が何を承認するか。
**§C-4 全体との関係**：本章の中核。

### §C-4.1.1 ベースライン（責任分界）

| 領域 | 監査アカウント / SecOps | Platform チーム | アプリチーム |
|---|:---:|:---:|:---:|
| FMS ポリシー作成・配信 | ✅ | 連携 | - |
| Service Catalog 製品作成 | レビュー | ✅ | - |
| SCP / Org 構造 | ✅ | 連携 | - |
| WAF ルールチューニング（中央） | ✅ | - | - |
| WAF ルールチューニング（アプリ独自） | レビュー | - | ✅ |
| CloudTrail / Config 集約運用 | ✅ | - | - |
| アプリの WAF メトリクス監視 | サマリ | - | ✅ |
| 例外申請承認 | ✅ | 連携 | 申請 |

### §C-4.1.2 TBD / 要確認

- Q: **SecOps と Platform の境界**確定（人員アサインに依存）→ `API-D-2101`
- Q: アプリチームによる **WAF 独自ルール追加の権限範囲**（First/Last の枠内）→ `API-D-2102`

---

## §C-4.2 配信パス（push）

**このサブセクションで定めること**：監査アカウントから各アプリへの配信メカニズム。
**主な判断軸**：自動性、上書き禁止、変更通知。
**§C-4 全体との関係**：§FR-API-7 ガードレールの運用面。

### §C-4.2.1 ベースライン

| 配信物 | メカニズム | 対象決定 |
|---|---|---|
| WAF / SG / Network FW | **AWS Firewall Manager** | タグベース（`Exposure=public/partner` 等） |
| Config Rules | **AWS Config + Organizations** | OU 単位 + タグ |
| SCP | **AWS Organizations** | OU 単位 |
| Service Catalog 製品 | **Service Catalog Portfolio** + AWS Organizations 共有 | アカウント単位 |
| Backup Plan | **AWS Backup**（Org 配信） | タグベース |

### §C-4.2.2 変更通知ルール

- **Breaking 変更**（既存リソースに非準拠が発生する変更）：30 日前通知
- **追加変更**（既存に影響しない）：通知のみ、即時適用
- 通知手段：Slack + メール + Service Catalog 製品の changelog

### §C-4.2.3 TBD / 要確認

- Q: 通知期間の **業務影響別調整**（Critical アプリは 60 日前等）→ `API-D-2111`
- Q: 変更通知の **配信先**（管理者の連絡先一覧管理）→ `API-D-2112`

---

## §C-4.3 集約パス（pull）

**このサブセクションで定めること**：アプリから監査アカウントへの証跡集約。
**主な判断軸**：完全性、保管期間、コスト。
**§C-4 全体との関係**：§FR-API-8 §8.4 / §NFR-API-7 と連動。

### §C-4.3.1 ベースライン

| 証跡 | 集約手段 | 保管期間 |
|---|---|---|
| CloudTrail（管理 API call） | Org trail → 監査アカウント S3 | 7 年（Object Lock） |
| CloudTrail Data Events | 個別有効化 → 監査アカウント S3 | 1 年（コスト要件次第） |
| Config 履歴 | Config Aggregator | 7 年 |
| S3 server access log | 各アプリ S3 → 監査アカウント S3 | 1 年 |
| VPC Flow Logs | 各 VPC → 監査アカウント S3 / CloudWatch | 90 日 |
| GuardDuty findings | Security Hub に集約 | 90 日 |

### §C-4.3.2 TBD / 要確認

- Q: VPC Flow Logs の **集約必須化範囲**（全 VPC / Public 系のみ）→ `API-C-2121`
- Q: Object Lock の **モード**（Compliance / Governance）→ `API-D-2122`

---

## §C-4.4 操作監査

**このサブセクションで定めること**：監査アカウント自身の操作監査。
**主な判断軸**：監査者の権限濫用防止、4 eyes principle。
**§C-4 全体との関係**：監査の監査。

### §C-4.4.1 ベースライン

- **Delegated Admin 操作は管理アカウントの CloudTrail に記録**
- **重要変更（FMS ポリシー削除、Service Catalog 製品廃止 等）は 2 名承認**（4 eyes）
- **Break Glass アカウント**：緊急時専用、Hardware MFA 必須、操作は全件レビュー

### §C-4.4.2 TBD / 要確認

- Q: 2 名承認の **対象操作リスト**確定 → `API-D-2131`
- Q: Break Glass の **承認・運用** → `API-D-2132`

---

## §C-4.x 関連ドキュメント

- [§FR-API-7 ガードレール](../fr/07-guardrails.md) — 配信物の中身
- [§FR-API-8 観測性](../fr/08-observability.md) — CloudTrail 詳細
- [§NFR-API-4 セキュリティ](../nfr/04-security.md) — 死守事項マトリクス
- [§NFR-API-7 コンプラ](../nfr/07-compliance.md) — 監査要件
