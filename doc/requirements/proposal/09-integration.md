# §9 外部統合

> 上位 SSOT: [00-index.md](00-index.md)
> 詳細: [../functional-requirements.md §8 FR-INT](../functional-requirements.md)
> カバー範囲: FR-INT §8.1 プロトコル / §8.2 ログ・監視 / §8.3 API・IaC・Webhook
> ステータス: 📋 骨格のみ

---

## 9.1 プロトコル準拠（→ FR-INT §8.1）

### ベースライン（仮）

OIDC 1.0 / OAuth 2.0 / SAML 2.0 / JWKS 公開エンドポイント / API Gateway 統合の標準準拠。

### TBD / 要確認（仮）

統合先システムの対応プロトコル

---

## 9.2 ログ・監視（→ FR-INT §8.2）

### ベースライン（仮）

CloudWatch / S3 / Kinesis への監査ログ外部出力。SIEM 連携は要件次第。

### TBD / 要確認（仮）

使用中の SIEM（Splunk / Datadog 等）、ログ保存期間

---

## 9.3 API・IaC・Webhook（→ FR-INT §8.3）

### ベースライン（仮）

管理 REST API、Terraform / IaC 管理、Webhook イベント通知（要件次第）。

### TBD / 要確認（仮）

既存 CI/CD / IaC との統合要件、Webhook で連携したいイベント
