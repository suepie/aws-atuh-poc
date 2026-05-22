# §NFR-API-4 セキュリティ（死守事項）

> 親 SSOT: [../00-index.md](../00-index.md) §NFR-API-4
> IPA グレード: **E. セキュリティ**
> ヒアリング: [../../hearing-script/09-nfr.md](../../hearing-script/09-nfr.md)

---

## §4.0 前提と背景

### §4.0.1 用語整理

| 用語 | 定義 |
|---|---|
| **死守事項** | 全 API で必ず守らせるセキュリティ最低ライン |
| **WAF** | Web Application Firewall。OWASP Top 10 等の Web 攻撃を遮断 |
| **mTLS** | Mutual TLS。クライアント証明書による双方向認証 |
| **SCP** | Service Control Policy（Org レベルで防御的に禁止） |

### §4.0.2 なぜここ（§4）で決めるか

要望テーマの「**セキュリティとして死守すべきこと**」の中核章。FR-7 ガードレールが**配信機構**を定義するのに対し、本章は **死守すべき具体的要件のリスト**を定義する。

```mermaid
flowchart LR
    NFR4[NFR-4 死守事項<br/>(要件リスト)] --> FR7[FR-7 ガードレール<br/>(配信機構)]
    FR7 --> FMS[FMS / SCP / Config Rules / Service Catalog]
```

### §4.0.3 IPA グレード対応

| IPA 中項目 | 本章での対応 |
|---|---|
| 認証・認可 | §FR-API-2 に委譲、本章は要件のみ |
| 暗号化 | §4.2 |
| アクセス制御 | §4.1 |
| 不正検知 / 監査 | §4.4 + §NFR-API-7 |
| マルウェア対策 | §4.5 |

### §4.0.4 §4.0.A 本標準のスタンス

| 基本方針 | 本章での具体化 |
|---|---|
| 絶対安全 | **OWASP Top 10 + AWS Well-Architected Security Pillar 全項目をベースライン化** |
| どんなアプリでも | 公開境界別の死守事項マトリクスを提示 |
| 効率よく | 死守事項のほとんどは **FMS / Service Catalog / SCP で自動配信**、自前実装は最小限 |
| 運用負荷・コスト最小 | マネージドサービス（AWS WAF / Secrets Manager / KMS / Shield Standard）優先 |

### §4.0.5 本章で扱うサブセクション

| § | サブセクション |
|---|---|
| §4.1 | 通信暗号化・境界制御 |
| §4.2 | データ暗号化・シークレット管理 |
| §4.3 | WAF・DDoS 対策 |
| §4.4 | 攻撃検知・脆弱性管理 |
| §4.5 | 死守事項マトリクス |

---

## §4.1 通信暗号化・境界制御

**このサブセクションで定めること**：API 通信路の暗号化と境界制御の最低ライン。
**主な判断軸**：TLS 1.2 以上、平文禁止、HSTS。
**§4 全体との関係**：§FR-1 公開境界の死守要件版。

### §4.1.1 ベースライン（死守事項）

- **TLS 1.2 以上必須**、TLS 1.3 推奨
- **HTTP → HTTPS リダイレクト**（CloudFront / ALB / API Gateway）
- **HSTS ヘッダ**（CloudFront / ALB ヘッダルール / Lambda）
- **ACM 証明書**（自己署名禁止）
- **Public エンドポイントは必ず WAF を前段に**
- **Internal でも IAM auth または mTLS で認証**、認証なし API 禁止
- **未認証ヘルスチェック**等の例外は WAF の rate-based / IP allowlist で限定

### §4.1.2 TBD / 要確認

- Q: **TLS 1.3 の必須化**（古いクライアント互換性との衝突）→ `API-C-1201`
- Q: 内部 service 間の **mTLS を必須化するか**（Service Connect / Lattice のサポート利用）→ `API-C-1202`

---

## §4.2 データ暗号化・シークレット管理

**このサブセクションで定めること**：保管時暗号化・シークレットローテーションの最低ライン。
**主な判断軸**：KMS CMK 利用、AWS Managed Key は内部用途のみ。
**§4 全体との関係**：§FR-8 観測性のログ暗号化、§FR-5/6 のシークレット管理の根拠。

### §4.2.1 ベースライン（死守事項）

- **at-rest 暗号化必須**（S3 / DynamoDB / RDS / EBS / Lambda 環境変数 / CloudWatch Logs）
- **CMK（顧客マネージドキー）を Public/Partner API で必須**、Internal/Private は AWS Managed Key 許容
- **Secrets Manager / SSM Parameter Store**：シークレットは平文埋め込み禁止
- **ローテーション**：DB 認証情報は 90 日、API Key は要件別（90 / 180 / 365 日）
- **CloudWatch Logs Data Protection Policy** で managed identifier（クレカ・SSN・AWS access key）マスキング GA

### §4.2.2 TBD / 要確認

- Q: CMK の **粒度**（アプリ単位 / 環境単位 / リソース種別単位）→ `API-C-1211`
- Q: シークレットローテーション **未対応 DB の段階移行計画** → `API-C-1212`

---

## §4.3 WAF・DDoS 対策

**このサブセクションで定めること**：Public / Partner API での攻撃遮断。
**主な判断軸**：AWS Managed Rules を活用、count → block の段階投入。
**§4 全体との関係**：§FR-7 §7.1 で配信されるルールセットの根拠。

### §4.3.1 ベースライン（死守事項）

- **AWS Managed Rules（必須）**：
  - `AWSManagedRulesCommonRuleSet`（OWASP Top 10 ベース）
  - `AWSManagedRulesKnownBadInputsRuleSet`
  - `AWSManagedRulesAmazonIpReputationList`
  - `AWSManagedRulesAnonymousIpList`
- **Rate-based rule**（IP 単位、5 分窓、標準 2,000 req / 5min）
- **Bot Control**：重要 URI（login / payment / signup）にスコープ限定
- **Shield Standard**：自動有効、全 Public エンドポイント
- **Shield Advanced**：必要な重要エンドポイントのみ（高コスト）
- **段階投入**：本番投入前に count モードで観測 → block への切替

### §4.3.2 TBD / 要確認

- Q: Bot Control の **対象 URI スコープ**確定 → `API-D-1221`
- Q: Shield Advanced 採用範囲 → `API-D-1222`

---

## §4.4 攻撃検知・脆弱性管理

**このサブセクションで定めること**：攻撃検知・脆弱性スキャン・パッチ管理。
**主な判断軸**：AWS マネージドサービスを優先。
**§4 全体との関係**：§NFR-API-6 運用との重なり。

### §4.4.1 ベースライン（死守事項）

- **GuardDuty**：全アカウントで有効化
- **Security Hub**：Org 横断、CIS Benchmark / AWS Foundational Best Practices / PCI DSS Standard
- **Amazon Inspector**：EC2 / ECR / Lambda の脆弱性スキャン
- **AWS Config**：必須リソース設定の継続監視
- **CloudTrail Org trail**：監査アカウントに集約（§FR-API-8 §8.4）

### §4.4.2 TBD / 要確認

- Q: Security Hub の **準拠標準**選定（CIS / AWS FSBP / PCI DSS のどれを必須化）→ `API-C-1231`
- Q: Inspector の **スコープ**（全 Lambda か重要関数のみか）→ `API-C-1232`

---

## §4.5 死守事項マトリクス

**このサブセクションで定めること**：公開境界別の死守事項を一覧で示す。
**主な判断軸**：境界別に厳しさが異なる項目を明示。
**§4 全体との関係**：§4.1〜§4.4 の集約ビュー。

### §4.5.1 ベースライン

| 死守事項 | Public | Partner | Internal | Private |
|---|:---:|:---:|:---:|:---:|
| TLS 1.2+ 必須 | ✅ | ✅ | ✅ | ✅ |
| 認証必須 | ✅ JWT | ✅ API Key/mTLS | ✅ IAM/JWT | ✅ IAM |
| WAF 必須 | ✅ | ✅ | ➖ | ➖ |
| WAF rate-based | ✅ | ✅ | ➖ | ➖ |
| CMK 暗号化 | ✅ | ✅ | ⚠ | ⚠ |
| Shield Standard | ✅ 自動 | ✅ 自動 | ➖ | ➖ |
| Shield Advanced | 重要のみ | ➖ | ➖ | ➖ |
| Bot Control | 重要 URI | 個別 | ➖ | ➖ |
| ログ PII マスク | ✅ | ✅ | ✅ | ✅ |
| Secrets Manager 必須 | ✅ | ✅ | ✅ | ✅ |
| CloudTrail Data Events | 重要のみ | 重要のみ | ➖ | ➖ |

### §4.5.2 TBD / 要確認

- Q: マトリクスの **粒度の妥当性**（業務カテゴリ単位の上書きも許容するか）→ `API-D-1241`

---

## §4.x 関連ドキュメント

- [§FR-API-7 ガードレール](../fr/07-guardrails.md) — 死守事項の配信機構
- [§NFR-API-7 コンプライアンス](07-compliance.md) — 規制・監査
- [§FR-API-2 認証認可](../fr/02-authn-authz.md) — 認証必須化
- [§FR-API-8 観測性](../fr/08-observability.md) — ログ暗号化・PII マスク
