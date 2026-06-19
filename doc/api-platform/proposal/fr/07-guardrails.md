# §FR-API-7 ガードレール（監査アカウント FMS 連携）

> 親 SSOT: [../00-index.md](../00-index.md) §FR-API-7
> ヒアリング: [../../hearing-script/07-guardrails.md](../../hearing-script/07-guardrails.md)

---

## §7.0 前提と背景

### §7.0.1 用語整理

| 用語 | 定義 |
|---|---|
| **ガードレール（guardrail）** | アプリ開発者が外せない（外せても監査される）標準ルール |
| **AWS Firewall Manager (FMS)** | Organizations 配下の全アカウントに横断的にセキュリティポリシーを配信するマネージドサービス |
| **Delegated Administrator** | FMS / Security Hub などを管理アカウントから委譲された運用アカウント。本標準では **監査アカウント / Security Tooling アカウント** |
| **Auto remediation** | FMS が非準拠リソースに自動でルール適用、上書きを禁止する挙動 |
| **First/Last rule group** | FMS が配信する Web ACL の最初と最後の枠。各アプリ中央に独自ルール差し込み可 |

### §7.0.2 なぜここ（§7）で決めるか

要望テーマの「**監査アカウントの FirewallManager からのルールの説明と運用**」の中核。

ガードレールは「**何を全 API で必ず守らせるか**」を定義し、各アプリの自治と中央統制の境界を引く。SCP / Config Rules / Service Catalog と一体で運用する。

```mermaid
flowchart TB
    Audit[監査アカウント<br/>Delegated Admin] -->|WAF/SG/Network FW 配信| Apps[各アプリアカウント]
    Audit -->|Config Rules 配信| Apps
    Audit -->|SCP 配信| Apps
    Audit -->|Service Catalog 配信| Apps
    Apps -.集約.->|CloudTrail / Config| AuditLog[監査アカウント S3]
```

### §7.0.3 §7.0.A 本標準のスタンス

| 基本方針 | 本章での具体化 |
|---|---|
| 絶対安全 | **WAF Managed Rules（OWASP / Bad Input / IP Reputation）+ rate-based を全 Public/Partner API に必須**配信 |
| どんなアプリでも | 配信は **タグベース**（`Exposure=public` のリソースに自動アタッチ）、サービス種別（CloudFront / ALB / APIGW）横断 |
| 効率よく | **First/Last rule group** を活用してアプリ側の自由度を残す（中央ルールに独自ルール差し込み可） |
| 運用負荷・コスト最小 | Bot Control 等のプレミアム機能は **URI スコープを絞って導入**、count → block の段階投入 |

### §7.0.4 本章で扱うサブセクション

| § | サブセクション | 主題 |
|---|---|---|
| §7.1 | FMS 配信ポリシー | 配信種別・対象スコープ・上書き挙動 |
| §7.2 | SCP / Config Rules | 予防的・発見的ガードレール |
| §7.3 | Service Catalog 配信 | 標準スタックを製品として配布 |
| §7.4 | 例外承認プロセス | ガードレール逸脱時の手続き |

---

## §7.1 FMS 配信ポリシー

**このサブセクションで定めること**：監査アカウントから配信する FMS ポリシーの種別と内容。
**主な判断軸**：Public 公開リソースを死守、コスト過大化（Bot Control 等）を避ける。
**§7 全体との関係**：本サブセクションがガードレールの主要レイヤ。

### §7.1.1 ベースライン（配信種別）

| FMS ポリシー種別 | 配信対象 | 配信内容（暫定） |
|---|---|---|
| **AWS WAF v2** | `Exposure=public/partner` の CloudFront / ALB / API Gateway | `AWSManagedRulesCommonRuleSet`（OWASP Top 10）<br/>`AWSManagedRulesKnownBadInputsRuleSet`<br/>`AWSManagedRulesAmazonIpReputationList`<br/>`AWSManagedRulesAnonymousIpList`<br/>rate-based rule（標準 2,000 req / 5min / IP） |
| **AWS WAF v2 (extended)** | 重要 API のみ（login / payment 等の URI スコープ） | `AWSManagedRulesBotControlRuleSet`（CommonTargetedBotControl、URI scope） |
| **Security Group baseline** | 全アカウント | Public S3 / 0.0.0.0/0 inbound 等の禁止 |
| **VPC Common SG** | 全 VPC | 共通インバウンド許可ルール（必要に応じて） |
| **AWS Network Firewall** | 共有 VPC / Transit Gateway | 必要時のみ。コスト要件 |
| **Route53 Resolver DNS Firewall** | 全 VPC | AWS Managed Domain List で C2 ドメイン遮断 |
| **AWS Shield Advanced** | 重要 Public エンドポイント | 大規模 DDoS 対策必要時のみ（高コスト） |

### §7.1.2 上書き挙動の標準

- **First rule group** に共通必須ルール（WAF Managed Rules）を配信、**Last rule group** に共通カウントオンリー（観測のみ）
- **中央枠の間にアプリ独自ルールを差し込み可**（FMS の First/Last の仕様を活用）
- WCU 上限（1500）あり、Managed Rule を盛りすぎると後から自前ルールを足せなくなる → **WCU 予算を中央 1000 / アプリ 500** で分配（暫定）

### §7.1.3 監査アカウント / Delegated Admin の構成

- **Delegated Administrator**：監査アカウント（Security Tooling アカウント、Control Tower の Audit account 相当）
- **Multi-admin**：最大 10 名まで委譲可、Restricted administrative scope で OU/Account/Policy/Region 単位の管轄絞り
- **前提**：AWS Config を全アカウントで有効化（StackSets で配布）

### §7.1.4 TBD / 要確認

- Q: **Bot Control を全 Public API に当てるか**、login/payment 等の URI スコープ限定か（コスト要件）→ `API-D-701`
- Q: WAF Managed Rules の **段階投入計画**（count → block の期間、観測ベース）→ `API-D-702`
- Q: AWS Shield Advanced の **採用範囲**（高コスト、必要 API のみ）→ `API-D-703`
- Q: Route53 Resolver DNS Firewall の **既定 Domain List** → `API-D-704`

---

## §7.2 SCP / Config Rules

**このサブセクションで定めること**：予防的（SCP）・発見的（Config Rules）ガードレール。
**主な判断軸**：WAF と並ぶ多層防御、必須タグ強制、暗号化必須化。
**§7 全体との関係**：§7.1 FMS と相補。

### §7.2.1 ベースライン（SCP）

- リージョン制限（許可リージョン以外の API 作成禁止）
- Root user の使用禁止
- CloudTrail / Config の無効化禁止
- IAM Identity Center / SSO 経由のみ操作可
- パブリック S3 / 暗号化なし S3 禁止

### §7.2.2 ベースライン（Config Rules）

#### A. リソース構成系

- 必須タグ（§FR-API-4 §4.3 のセット）が欠落していないか
- API Gateway / ALB に WAF がアタッチされているか
- Lambda 関数の環境変数が KMS 暗号化されているか
- ECS Task definition の Logging Driver が awslogs かつ Log Group 暗号化されているか
- VPC Flow Logs が有効か
- CloudWatch Log Group の Retention が設定されているか

#### B. 認証 Authorizer 強制系（Fail-closed 担保）⭐ 新規

[§FR-API-2 §2.8 Fail-closed 原則](02-authn-authz.md) を継続監査する Config Rules：

| Config Rule | 検査内容 | 違反時の挙動 |
|---|---|---|
| `api-gw-method-authorizer-required` | API Gateway REST/HTTP API の **全 method に Authorizer 設定済**（NONE 以外）か | 非準拠 → 即時通知 + 例外台帳照合 |
| `lambda-function-url-auth-type-iam` | Lambda Function URL の `AuthType` が `AWS_IAM`（または `NONE` でも例外台帳に登録済）か | 非準拠 → 即時通知 |
| `alb-listener-authentication-enforced` | Internet-facing ALB の Listener Rule に **認証統合（OIDC / Cognito）or アプリ middleware 認証タグ**があるか | 非準拠 → 即時通知 |
| `apigw-rest-api-public-access-blocked` | Private endpoint type 推奨の API が Regional / Edge で公開されていないか（例外台帳照合）| 警告 |

→ 「**認証なし API が漏れた**」事故を Config Rule で自動検知。例外申請台帳と照合し、未登録の認証なし API は即時アラート。

#### C. ネットワーク + 認証 両方必須系（Zero Trust 担保）⭐ 新規

[§NFR-API-4 §4.5 Zero Trust 原則](../nfr/04-security.md) を担保する Config Rules：

| Config Rule | 検査内容 |
|---|---|
| `internal-api-iam-auth-required` | 社内 / 社内限定 Profile タグの付いた API Gateway / ALB が **IAM auth または JWT Authorizer を設定済**か |
| `sg-only-network-not-allowed` | 社内限定 Profile タグの API が **SG だけで認証 Authorizer なし** で構成されていないか（例外台帳照合）|

### §7.2.3 TBD / 要確認

- Q: SCP / Config Rules の **既定セット**は Landing Zone Accelerator (LZA) を採用するか自前か → `API-D-721`
- Q: Config Rule の **自動修復**（Systems Manager Automation）採用範囲 → `API-D-722`
- Q: Authorizer 必須化 Config Rule の **自動修復**（API method を deny に変更）を採用するか → `API-D-723` ⭐
- Q: 認証なし API 例外台帳と Config Rule の **照合自動化**（ServiceNow / DynamoDB 等のデータソース）→ `API-D-724` ⭐

---

## §7.3 Service Catalog 配信

**このサブセクションで定めること**：標準アーキテクチャを **製品（IaC スタック）として配布**する仕組み。
**主な判断軸**：開発者 self-service、ガードレール準拠の自動性。
**§7 全体との関係**：§FR-API-1〜6 の標準を実装テンプレ化する出口。

### §7.3.1 ベースライン

- **Service Catalog Portfolio**：監査アカウントで作成、AWS Organizations で配布
- **製品例**（暫定）：
  - `api-gateway-http-public`（CloudFront + WAF + HTTP API + Lambda + DynamoDB）
  - `api-gateway-rest-partner`（REST API + Custom Domain + Usage Plan + mTLS optional）
  - `ecs-fargate-public`（CloudFront + WAF + ALB + ECS Fargate）
  - `ecs-fargate-internal`（Internal ALB + ECS Fargate + Service Connect）
  - `lambda-function-url-internal`（Function URL + IAM auth）
- **共通**：必須タグセット組み込み、CloudWatch Log Group 標準、X-Ray / ADOT 有効化、暗号化既定

### §7.3.2 TBD / 要確認

- Q: Service Catalog 提供物の **IaC 言語**（CDK / Terraform / CloudFormation）→ `API-C-731`
- Q: 製品のバージョン管理・更新通知の仕組み → `API-C-732`

---

## §7.4 例外承認プロセス

**このサブセクションで定めること**：標準外パターン採用や FMS ルール一時無効化時の手続き。
**主な判断軸**：監査証跡を残す、期限付き、影響範囲を明示。
**§7 全体との関係**：すべての §7 ルールに対する例外プロセス。

### §7.4.1 ベースライン

- **申請内容**：標準外採用の理由 / 影響範囲 / 代替コントロール / 期限
- **承認者**：セキュリティチーム + アーキテクチャ委員会（暫定）
- **記録**：例外台帳（社内ツール）+ リソースタグ（`Exemption=approved-2026-xx-xx`）
- **期限超過**：自動で Config Rule から非準拠通知

### §7.4.2 TBD / 要確認

- Q: **例外申請のリードタイム目標**（通常 / 緊急）→ `API-D-741`
- Q: 例外台帳の **保管場所** → `API-D-742`

---

## §7.x 関連ドキュメント

- [§C-API-4 監査ガバナンス](../common/04-audit-governance.md) — 監査アカウントとの境界・役割整理
- [§C-API-5 標準提供物](../common/05-self-service-catalog.md) — Service Catalog 詳細
- [§NFR-API-4 セキュリティ](../nfr/04-security.md) — 死守事項の根拠
- [§NFR-API-7 コンプライアンス](../nfr/07-compliance.md) — 監査・規制要件
