# §FR-API-7 ガードレール（監査アカウント FMS 連携）

> 元データ: [../hearing-checklist.md D-3 / D-4 / D-12](../hearing-checklist.md#d-3-ガードレールfr-api-7)
> 対象: SecOps / Platform / 経営層
> 関連章: [§FR-API-7](../proposal/fr/07-guardrails.md) / [§C-API-4](../proposal/common/04-audit-governance.md)

---

### 【Bot Control の対象範囲】 (API-D-701, 🔥)

AWS WAF Bot Control（プレミアム料金）の対象範囲をご教示ください。
- **全 Public API に当てる**：包括的だがコスト大（数千 USD / 月 〜）
- **重要 URI のみ**（login / signup / payment / 検索 等）：本標準推奨
- **採用しない**：rate-based rule + Managed Rules で代用
**目的**: [§FR-API-7 §7.1 / §NFR-API-4 §4.3](../proposal/nfr/04-security.md) の WAF 配信内容と、[§NFR-API-8](../proposal/nfr/08-cost.md) のコスト。Bot Control はコスト感度が高い項目です。

---

### 【WAF Managed Rules の段階投入計画】 (API-D-702, 🟡)

WAF Managed Rules（OWASP Top 10 / Known Bad Inputs / IP Reputation 等）の本番投入を、**count → block の段階投入**で進める方針でよろしいかご確認ください。
段階投入の標準期間（例：count 2 週間 → block）も併せていただけますと幸いです。
**目的**: [§FR-API-7 §7.1](../proposal/fr/07-guardrails.md) の運用安全性。本番事故事例（最初から block で正当リクエストが遮断）を防ぎます。

---

### 【AWS Shield Advanced の採用範囲】 (API-D-703, 🟡)

AWS Shield Advanced（高度な DDoS 対策 + 専門サポート + 後払い保護）の採用範囲をご教示ください。
- 全 Public エンドポイント
- Critical な Public エンドポイントのみ（売上直結 / 公開特定 API）
- 採用しない（Shield Standard で十分）
Shield Advanced は **約 3,000 USD / 月** の固定費 + Org 配下リソース保護対応です。
**目的**: [§FR-API-7 §7.1 / §NFR-API-8](../proposal/nfr/08-cost.md) のコスト感度高項目。

---

### 【DNS Firewall の既定 Domain List】 (API-D-704, 🟢)

Route53 Resolver DNS Firewall で配信する既定の Domain List をご教示ください。
- AWS Managed Domain List（C2 ドメイン / Botnet Command and Control / Malicious Domain）
- 自社カスタム allow / deny list 追加
- 採用しない
**目的**: [§FR-API-7 §7.1](../proposal/fr/07-guardrails.md) の DNS レベル防御。Lambda / ECS からの不正通信検知に有効です。

---

### 【SCP / Config Rules の既定セット】 (API-D-721, 🔥)

SCP（予防的）+ Config Rules（発見的）の既定セットを、**Landing Zone Accelerator (LZA) を採用するか、自前構築するか**、ご見解をお願いします。
- LZA 採用：AWS 提供の標準セット、メンテナンスは Org が継続
- 自前：自社要件に最適化、メンテナンスコスト
- ハイブリッド：LZA をベースに追加カスタム
**目的**: [§FR-API-7 §7.2](../proposal/fr/07-guardrails.md) のガードレール基盤。LZA の有無で本標準の追加配信スコープが変わります。

---

### 【Config Rule の自動修復】 (API-D-722, 🟡)

Config Rule で非準拠検知後の **自動修復**（Systems Manager Automation で自動是正）の採用範囲をご教示ください。
- 全 Config Rule で自動修復有効
- タグ欠落・ログ保存期間欠落等の **軽微な是正のみ自動**、重要は通知のみ
- 自動修復は採用しない（全て通知 + 手動対応）
**目的**: [§FR-API-7 §7.2](../proposal/fr/07-guardrails.md) の運用負荷。自動修復は本標準準拠率の継続維持に有効ですが、誤修復リスクも考慮が必要です。

---

### 【例外申請のリードタイム】 (API-D-741, 🟡)

ガードレール逸脱 / 標準外採用の例外申請プロセスの **リードタイム目標**をご教示ください。
- 通常申請：N 営業日
- 緊急申請：M 時間
**目的**: [§FR-API-7 §7.4](../proposal/fr/07-guardrails.md) の例外管理。承認プロセスの SLA がアプリ開発スピードに影響します。

---

### 【例外台帳の保管場所】 (API-D-742, 🟢)

ガードレール例外の **台帳保管場所**をご教示ください。
- 社内ツール（Jira / ServiceNow / Confluence 等）
- AWS Audit Manager の Custom Control
- 自前 DynamoDB / RDS
**目的**: [§FR-API-7 §7.4](../proposal/fr/07-guardrails.md) の監査証跡。期限超過の自動検知が組めることが重要です。

---

### 【SecOps / Platform の境界】 (API-D-2101, 🔥)

監査アカウントとアプリアカウントの中間に位置する役割（**SecOps チームと Platform チーム**）の責任境界をご教示ください。

本標準の暫定提案：

| 領域 | SecOps | Platform | アプリ |
|---|:---:|:---:|:---:|
| FMS ポリシー作成・配信 | ✅ | 連携 | - |
| Service Catalog 製品作成 | レビュー | ✅ | - |
| WAF 中央ルール | ✅ | - | - |
| WAF アプリ独自ルール | レビュー | - | ✅ |
| 例外申請承認 | ✅ | 連携 | 申請 |

両チームが同一の場合、または異なる場合の運用境界をご見解いただきたいです。
**目的**: [§C-API-4 §C-4.1](../proposal/common/04-audit-governance.md) の責任分界。組織構成によって本標準の運用主体が変わります。

---

### 【アプリ側 WAF 独自ルールの権限範囲】 (API-D-2102, 🟡)

アプリチームによる **WAF 独自ルール追加の権限範囲**（FMS の First/Last rule group の間）をご教示ください。
- 全アプリ自由（中央枠の間で）
- ステージング・開発のみ自由、本番は SecOps レビュー
- 自由追加禁止、全件 SecOps 承認
**目的**: [§C-API-4 §C-4.1 / §FR-API-7 §7.1](../proposal/fr/07-guardrails.md) のアプリ自治範囲。中央統制と自治のバランスです。

---

## ヒアリング後の確定事項チェックリスト

- [ ] Bot Control の対象範囲（D-701）
- [ ] LZA / 自前の選定（D-721）
- [ ] SecOps / Platform の境界（D-2101）

これらが揃うと **§FR-API-7 ガードレール** と **§C-API-4 監査ガバナンス** を確定できます。
