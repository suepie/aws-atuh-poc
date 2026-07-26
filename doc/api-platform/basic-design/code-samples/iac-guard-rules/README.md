# iac-guard-rules — cfn-guard 標準ルールセット

IaC（CloudFormation / Terraform plan JSON）の **deploy 前**認証・設定検証ルール。
[04 章 静的解析ガイドライン](../../04-static-analysis-guidelines.md) §4.2 の実装物で、
死守事項 **SA-1**（IaC は cfn-guard/cdk-nag を CI 強制）/ **SA-3**（検知は deploy ブロック）に対応する。

構文は 04 章 §4.2.2 / [§C-6.6.4](../../../proposal/common/06-external-api-auth-architecture.md) で
検証済みの Guard rules language DSL（`let` / `rule ... when` / clause / `<<...>>` メッセージ）に準拠。

## 各ルールの意味

| ファイル | 検査内容 | 根拠 | 対応漏れパターン |
|---|---|---|:---:|
| `api-gw-authorizer-required.guard` | API GW Method の `AuthorizationType != NONE` / Lambda Function URL の `AuthType == AWS_IAM` / ALB Listener の `authenticate-oidc`・`authenticate-cognito` action | §C-API-6 P1、04 章 §4.2.2 | P1 / P6 |
| `origin-protection-required.guard` | Public API GW の Resource Policy が CloudFront Prefix List + `X-Origin-Verify` カスタムヘッダ検証を持つ / Public ALB SG は origin-facing prefix list のみ | ADR-039 §C-4 | — |
| `required-tags.guard` | `app-id` / `env` / `cost-center` / `owner` タグ必須（kebab-case、値の規約も検証） | 03 章 BL-1 / §3.2.1 | — |

## cfn-guard validate の実行方法

```bash
# 単一ルール
cfn-guard validate -r api-gw-authorizer-required.guard -d cloudformation/

# ディレクトリ内の全ルールを一括適用
cfn-guard validate -r . -d cloudformation/

# Terraform の場合は plan を JSON 化してから
terraform show -json plan.tfplan > plan.json
cfn-guard validate -r . -d plan.json
```

違反があると cfn-guard は non-zero exit で終了する（CI で PR / deploy をブロック）。

### CI 統合（GitHub Actions 例、04 章 §4.5.2）

```yaml
- name: cfn-guard validate
  run: cfn-guard validate -r iac-guard-rules/ -d cloudformation/
# 失敗時は step が non-zero exit → PR ブロック（SA-3）
```

## cdk-nag との併用

CDK 採用アプリでは **cdk-nag（`AwsSolutionsChecks`）を第一**に、独自要件を cfn-guard で補完する
（04 章 §4.1「選定原則」/ D-G-040）。役割分担:

| 検査 | 担当 | 実在ルール ID / 手段 |
|---|---|---|
| API の authorization 実装 | **cdk-nag** | `AwsSolutions-APIG4` |
| REST API stage の WAFv2 web ACL 関連付け | **cdk-nag** | `AwsSolutions-APIG3` |
| ALB の access logs | **cdk-nag** | `AwsSolutions-ELB2` |
| API GW access logging / CloudWatch logging | cdk-nag | `AwsSolutions-APIG1` / `AwsSolutions-APIG6` |
| **Lambda Function URL の AuthType** | **cfn-guard**（本ルールセット） | cdk-nag に該当ルールが存在しないため（04 章 D-G-042）`api-gw-authorizer-required.guard` で担保 |
| Origin Protection（Prefix List + X-Origin-Verify） | **cfn-guard**（本ルールセット） | `origin-protection-required.guard` |
| 必須タグ | **cfn-guard**（本ルールセット） | `required-tags.guard` |

> ⚠ **非実在ルール ID に注意**（04 章 §4.3.2 / §4.x 検証済み事実）:
> cdk-nag に **`LMB` prefix は存在しない**（Lambda は `AwsSolutions-L1` のみ）。
> ALB access logging は **`AwsSolutions-ELB2`**（**`ELB7` は存在しない**）。
> 旧サンプルにあった **`LMB5` / `ELB7` は誤りであり、本ルールセットでは使用しない**。

### cdk-nag 適用（TypeScript、04 章 §4.3.1）

```typescript
import { AwsSolutionsChecks } from 'cdk-nag';
import { App, Aspects } from 'aws-cdk-lib';

const app = new App();
const stack = new MyApiStack(app, 'MyApiStack');
Aspects.of(stack).add(new AwsSolutionsChecks({ verbose: true }));
```

## 運用注意（04 章 §4.2.3 / §4.7）

- `/health` 等の正当な例外は guard ルールにコメント注釈で明示し、**例外承認（§4.7）**を経る。
- ルールセットは共通リポジトリで集中管理し、各アプリは consumer（ドリフト防止）。
- 段階導入: 既存 stack は warn、新規は error。
- cdk-nag の suppress は `NagSuppressions.addResourceSuppressions()` で個別に理由必須記載、
  チケット ID を付与して監査対象化（§4.3.3 / §4.7）。

## 参照

- [04 章 静的解析ガイドライン](../../04-static-analysis-guidelines.md) §4.2 / §4.3 / §4.5
- [§C-API-6 §C-6.6.4](../../../proposal/common/06-external-api-auth-architecture.md) — L1 IaC 実装サンプル
- [03 章 課金・コスト配賦ルール](../../03-billing-cost-allocation-rules.md) §3.2.1 — 必須タグ標準
- [ADR-039](../../../../adr/039-centralized-network-account-edge-layer.md) §C-4 — Origin Protection
- [cdk-nag 公式 RULES.md](https://github.com/cdklabs/cdk-nag/blob/main/RULES.md)（ルール ID 実在確認元）
