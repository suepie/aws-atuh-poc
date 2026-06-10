# Phase D: 最終判断（ガードレール承認・移行計画・体制）

> 元データ: [../hearing-checklist.md D-1 / D-11 / D-12 / D-13](../hearing-checklist.md#phase-d-最終判断)
> 対象: 経営層 / SecOps / Platform リーダー / アーキテクチャ委員会
> 関連章: 横断（特に [§FR-API-7](../proposal/fr/07-guardrails.md) / [§C-API-1](../proposal/common/01-reference-architecture.md) / [§C-API-2](../proposal/common/02-runtime-selection-criteria.md) / [§C-API-4](../proposal/common/04-audit-governance.md) / [§C-API-5](../proposal/common/05-self-service-catalog.md)）

---

## D-1: 公開範囲（信頼プロファイル）の昇格承認

### 【公開範囲（信頼プロファイル）昇格の承認権限者】 (API-D-101, 🔥)

公開範囲（信頼プロファイル）の昇格（社内限定 → 社内、社内 → パブリック、パートナー追加 等）の承認権限者をご教示ください。
- SecOps
- アーキテクチャ委員会
- プロジェクトオーナー
- 上記の段階承認
**目的**: [§FR-API-1 §1.3](../proposal/fr/01-exposure-boundary.md) のガバナンス。承認者が決まると申請プロセス・SLA・台帳管理が確定します。

---

### 【昇格申請のリードタイム目標】 (API-D-102, 🟡)

昇格申請の標準リードタイムをご教示ください（通常 / 緊急）。
**目的**: [§FR-API-1 §1.3](../proposal/fr/01-exposure-boundary.md) の運用 SLA。

---

### 【緊急昇格のエスケープハッチ】 (API-D-103, 🟡)

緊急昇格（インシデント対応等で公開範囲（信頼プロファイル）を一時的に変更）のエスケープハッチを許容しますか。許容する場合の事後監査手順をご教示ください。
**目的**: [§FR-API-1 §1.3](../proposal/fr/01-exposure-boundary.md) の例外運用。

---

## D-4: 監査ログ

### 【CloudTrail Data Events の対象範囲】 (API-D-841, 🟡)

CloudTrail Data Events（S3 object-level / Lambda Invoke）の対象範囲をご教示ください。
- 重要 S3 bucket（PII 保管・監査証跡）のみ
- 重要 Lambda（決済 / 認証）のみ
- 全リソース対象（コスト要件次第）
Data Events は管理 Events と別料金で、リクエスト課金（$0.10/100k events）です。
**目的**: [§FR-API-8 §8.4 / §NFR-API-7 / §NFR-API-8](../proposal/nfr/08-cost.md) のコスト感度。

---

### 【監査ログ保管期間（7 年）の妥当性】 (API-D-842, 🟡)

CloudTrail / S3 access log 等の監査ログ保管期間を **7 年** とする想定で問題ないかご確認ください。業界別規制で延長要否（金融 10 年等）をご教示ください。
**目的**: [§FR-API-8 §8.4 / §NFR-API-7 §7.2](../proposal/nfr/07-compliance.md) のコンプラ要件。

---

## D-5: セキュリティ最終判断

### 【Bot Control 対象 URI スコープ確定】 (API-D-1221, 🔥)

AWS WAF Bot Control を採用する場合の **対象 URI スコープ**を確定してください。
- login / signup / password reset
- payment / checkout
- search / catalog（高負荷攻撃対象）
- その他重要 URI
**目的**: [§NFR-API-4 §4.3 / §FR-API-7 §7.1](../proposal/fr/07-guardrails.md) の WAF 配信内容確定。Bot Control はコスト感度が高いため、対象を絞ります。

---

### 【Shield Advanced 採用範囲確定】 (API-D-1222, 🟡)

AWS Shield Advanced（約 3,000 USD/月）を採用する場合の対象エンドポイント（CloudFront / ALB / Route53 / EIP）を確定してください。
**目的**: [§NFR-API-4 §4.3](../proposal/nfr/04-security.md) のコスト確定。

---

### 【死守事項マトリクスの粒度妥当性】 (API-D-1241, 🟡)

[§NFR-API-4 §4.5 死守事項マトリクス](../proposal/nfr/04-security.md) の公開範囲（信頼プロファイル）別の粒度妥当性をご評価ください。
業務カテゴリ単位（決済 / 医療 / 一般）での **上書きを許容**するか、マトリクスは絶対基準とするかご見解をお願いします。
**目的**: 中央統制と業務最適化のバランス。

---

## D-7: 運用体制

### 【体制の既存組織への適用方法】 (API-D-1431, 🔥)

本標準で示す運用体制（24/7 オンコール / 業務時間 + 緊急 / 業務時間）を、既存組織にどう適用しますか。
- Platform チーム / SRE チームに集約
- 各アプリチームが自前 SRE
- ハイブリッド（Critical は Platform、その他はアプリ）
**目的**: [§NFR-API-6 §6.4](../proposal/nfr/06-operations.md) の体制設計。

---

### 【AWS サポート契約のアカウント別レベル】 (API-D-1432, 🟡)

各アカウントの AWS サポート契約レベルをご教示ください。
- Management / Audit / 共有認証基盤：Enterprise / Business
- 本番アプリアカウント：Business（推奨）
- 開発・ステージング：Developer
**目的**: [§NFR-API-6 §6.4 / §NFR-API-8](../proposal/nfr/08-cost.md) のサポート契約コスト。

---

## D-8: コンプラ・規制

### 【適用される規制リスト】 (API-D-1501, 🔥)

本標準の対象アプリで適用される規制リストをご教示ください。
- 個人情報保護法（日本）
- GDPR / CCPA（海外展開時）
- PCI DSS（決済）
- HIPAA（医療）
- FISC（金融）
- その他
**目的**: [§NFR-API-7 §7.1](../proposal/nfr/07-compliance.md) の対応スコープ。

---

### 【業界規制対応アプリの本標準への含め方】 (API-D-1502, 🔥)

業界規制対応アプリ（PCI DSS 決済 / HIPAA 医療 / FISC 金融 等）を本標準にどう含めますか。
- 本標準を **ベース** にし追加要件をアドオン
- 別アカウント・別標準として **分離**
- 例外承認制
**目的**: [§NFR-API-7 §7.1 / §NFR-API-9](../proposal/nfr/09-compatibility.md) の本標準スコープ。

---

### 【必要な認定リスト】 (API-D-1511, 🟡)

組織として保有 / 取得予定の認定をご教示ください。
- SOC 2 Type II
- ISMS / ISO 27001
- PrivacyMark
- PCI DSS Level 1
**目的**: [§NFR-API-7 §7.2](../proposal/nfr/07-compliance.md) の認定対応。

---

### 【Audit Manager 採用範囲】 (API-D-1512, 🟢)

AWS Audit Manager（監査エビデンス自動収集）の採用範囲をご教示ください。
**目的**: [§NFR-API-7 §7.2](../proposal/nfr/07-compliance.md) の監査自動化。

---

### 【PII の業務別保持期間】 (API-D-1521, 🟡)

PII（個人識別情報）の業務別保持期間をご教示ください。
業務終了後の削除タイミング（即時 / 1 年 / 3 年）も併せていただけますと幸いです。
**目的**: [§NFR-API-7 §7.3](../proposal/nfr/07-compliance.md) のデータライフサイクル。

---

### 【開発環境のデータマスキング手段】 (API-D-1522, 🟢)

開発・ステージング環境での PII データマスキング手段をご教示ください。
- AWS DMS（移行時マスキング）
- AWS Glue（バッチマスキング）
- 自前スクリプト
**目的**: [§NFR-API-7 §7.3](../proposal/nfr/07-compliance.md) の非本番環境保護。

---

### 【グローバル展開時のデータ所在地ポリシー】 (API-D-1531, 🟡)

グローバル展開時のデータ所在地ポリシーをご教示ください。
- 国内データは国内リージョンのみ（原則）
- 海外利用者は海外リージョンを許容（SCC 等）
- データ越境を最小化（暗号化 + マスキング）
**目的**: [§NFR-API-7 §7.4 / §NFR-API-5](../proposal/nfr/05-dr.md) のリージョン制約と DR の整合。

---

## D-9: コスト最適化

### 【コストダッシュボード必須化対象】 (API-D-1601, 🟡)

QuickSight 等のコストダッシュボードの必須化対象をご教示ください。
- 全アプリ
- 商用 / 課金関連のみ
- 経営層・部門責任者向け集約のみ
**目的**: [§NFR-API-8 §8.1](../proposal/nfr/08-cost.md) のコスト可視化。

---

### 【コスト指標の目標値】 (API-D-1602, 🟢)

USD / 1M req 等のコスト指標目標値をご教示ください（業種・業務別）。
**目的**: [§NFR-API-8 §8.1](../proposal/nfr/08-cost.md) のベンチマーク。

---

### 【Savings Plan コミット率】 (API-D-1621, 🟡)

Compute Savings Plan の **コミット率**（baseline 利用量の何 % をコミット）をご教示ください。
- 50%（柔軟だが割引率低）
- 70%（バランス、本標準推奨）
- 80%（最大割引、変動リスク）
**目的**: [§NFR-API-8 §8.3](../proposal/nfr/08-cost.md) のコミット戦略。

---

### 【arm64 移行計画】 (API-D-1622, 🟡)

既存 Lambda / ECS の arm64 (Graviton) 移行計画をご教示ください。
- 半期内に全件
- 次回更新時
- 互換性検証後の段階移行
**目的**: [§NFR-API-8 §8.3 / §NFR-API-9](../proposal/nfr/09-compatibility.md) のコスト最適化スコープ。

---

## D-10: バージョニング・移行

### 【Deprecation 期間の業務別調整】 (API-D-1711, 🟡)

API バージョン Deprecation 期間（Public 12 ヶ月 / Partner 6 ヶ月以上 / Internal 3 ヶ月）の業務別調整ルールをご教示ください。
**目的**: [§NFR-API-9 §9.2](../proposal/nfr/09-compatibility.md) の互換性運用。

---

### 【同時稼働 2 バージョン上限の妥当性】 (API-D-1712, 🟡)

同時稼働バージョンを **最大 2**（最新 + 1 個前）とする方針の妥当性をご評価ください。
**目的**: [§NFR-API-9 §9.2](../proposal/nfr/09-compatibility.md) の運用コスト管理。

---

### 【既存 Critical アプリの移行期限】 (API-D-1721, 🔥)

既存 Critical アプリの本標準への **移行期限**をご確定ください。
- 12 ヶ月以内
- 18 ヶ月以内
- 24 ヶ月以内
- 個別判断
**目的**: [§NFR-API-9 §9.3](../proposal/nfr/09-compatibility.md) の移行ロードマップ。

---

### 【移行支援体制】 (API-D-1722, 🔥)

既存アプリの本標準への移行支援体制をご教示ください。
- Platform / SRE チームが伴走支援
- 各アプリチームが自前対応
- 外部ベンダー活用
**目的**: [§NFR-API-9 §9.3](../proposal/nfr/09-compatibility.md) の移行コスト負担。

---

## D-11: アカウント体系・選定基準

### 【既存アカウント体系の再編要否】 (API-D-1801, 🔥)

本標準を導入するにあたり、既存 AWS アカウント体系の再編が必要かご見解をお願いします。
- 再編不要（既存で本標準のアカウント構成を実現可能）
- 部分再編（Security Tooling アカウントの新設等）
- 全面再編（Landing Zone Accelerator 導入を含めて）
**目的**: [§C-API-1 §C-1.4](../proposal/common/01-reference-architecture.md) の前提整理。再編コストは本標準の導入期間に大きく影響します。

---

### 【Workload OU の環境分離】 (API-D-1802, 🟡)

Workload OU の環境分離方式をご教示ください。
- prod / stg / dev でアカウント分離（推奨）
- 同一アカウント内で環境分離（VPC / タグ単位）
**目的**: [§C-API-1 §C-1.4 / §NFR-API-4](../proposal/nfr/04-security.md) の本番分離強度。

---

### 【選定基準の重みづけ妥当性】 (API-D-1901, 🟡)

[§C-API-2 §C-2.1 実装ランタイム選定基準の評価軸](../proposal/common/02-runtime-selection-criteria.md) の重みづけ（高 / 中 / 低）の妥当性をご評価ください。
**目的**: 選定決定木の精度。

---

### 【評価軸の数値化】 (API-D-1902, 🟢)

評価軸を **数値化したスコアシート**として運用するか、定性判断（決定木通過）で運用するかご見解をお願いします。
**目的**: [§C-API-2 §C-2.1](../proposal/common/02-runtime-selection-criteria.md) の運用形態。

---

### 【選定決定木の質問項目妥当性】 (API-D-1911, 🟡)

[§C-API-2 §C-2.2 選定フロー](../proposal/common/02-runtime-selection-criteria.md) の質問項目（長時間処理 / WebSocket / Cold start / 既存資産 / チームスキル）の妥当性をご評価ください。追加すべき軸はございますか。
**目的**: 決定木の網羅性。

---

### 【Cold start NG の判定基準】 (API-D-1912, 🟡)

「Cold start NG」（Real-time Tier）の判定基準を、Tier 自動判定 / 個別判断 のどちらにする方針が望ましいかご教示ください。
**目的**: [§C-API-2 §C-2.2 / §NFR-API-2](../proposal/nfr/02-performance.md) の選定明確性。

---

### 【マイクロサービス境界のガイドライン】 (API-D-1921, 🟢)

ハイブリッド構成（1 アプリ内で Serverless / Container 混在）の **マイクロサービス境界ガイドライン**をご教示ください。
- API / バッチで分割を許容
- 同一マイクロサービス内の混在は禁止
**目的**: [§C-API-2 §C-2.3](../proposal/common/02-runtime-selection-criteria.md) のハイブリッド運用。

---

### 【EKS の本標準への含め方】 (API-D-1931, 🟡)

EKS（Kubernetes）の本標準への含め方をご教示ください。
- 第 3 の選択肢に昇格（既存 K8s 資産があるなら）
- 例外承認制（標準は ECS）
- 採用禁止
**目的**: [§C-API-2 §C-2.4](../proposal/common/02-runtime-selection-criteria.md) のラインナップ最終確定。

---

## D-12: 監査ガバナンス（追加）

### 【配信変更通知期間】 (API-D-2111, 🟡)

FMS / Service Catalog 製品の Breaking 変更時の **通知期間**をご教示ください。
- 標準 30 日前
- Critical アプリは 60 日前
- 業務影響別
**目的**: [§C-API-4 §C-4.2](../proposal/common/04-audit-governance.md) の変更管理。

---

### 【変更通知の配信先】 (API-D-2112, 🟢)

配信変更通知の配信先（管理者連絡先一覧）の管理方法をご教示ください。
- 各アカウントの **Account Alternate Contact**（AWS 公式）
- 社内アプリ管理台帳
- Slack channel / Distribution List
**目的**: [§C-API-4 §C-4.2](../proposal/common/04-audit-governance.md) の到達保証。

---

### 【Object Lock のモード】 (API-D-2122, 🟡)

監査ログ S3 の Object Lock モードをご教示ください。
- **Compliance**：誰も削除不可（root user 含む）、確実だが緊急時の柔軟性なし
- **Governance**：特定 IAM 権限のみ削除可能
**目的**: [§C-API-4 §C-4.3 / §NFR-API-7](../proposal/nfr/07-compliance.md) の WORM 強度。

---

### 【2 名承認の対象操作リスト】 (API-D-2131, 🟡)

監査アカウントでの 2 名承認（4 eyes principle）対象操作リストをご教示ください。
- FMS ポリシー削除
- Service Catalog 製品廃止
- Log Group 削除
- Backup Vault 削除
**目的**: [§C-API-4 §C-4.4](../proposal/common/04-audit-governance.md) の権限濫用防止。

---

### 【Break Glass の運用】 (API-D-2132, 🟡)

Break Glass アカウント（緊急時専用、SCP も Override 可）の承認・運用ルールをご教示ください。
- 承認者：CTO / CISO
- 操作後のレビュー：全件
- MFA 種別：Hardware MFA 必須
**目的**: [§C-API-4 §C-4.4](../proposal/common/04-audit-governance.md) の緊急対応。

---

## D-13: Service Catalog

### 【初期ラインナップ確定】 (API-D-2201, 🔥)

[§C-API-5 §C-5.1 製品ラインナップ](../proposal/common/05-self-service-catalog.md) の暫定 8 製品で確定するかご確認ください。

| 製品名（暫定） | 構成 |
|---|---|
| api-gateway-http-public-lambda-dynamodb | CloudFront + WAF + HTTP API + JWT Authorizer + Lambda + DynamoDB |
| api-gateway-rest-partner-lambda | REST API + Custom Domain + Usage Plan + WAF + Lambda |
| api-gateway-private-internal-lambda | Private API + Lambda + Resource Policy |
| lambda-function-url-internal | Function URL + IAM auth |
| ecs-fargate-public-alb | CloudFront + WAF + ALB + ECS Fargate |
| ecs-fargate-internal-lattice | VPC Lattice + ECS Fargate + Service Connect |
| ecs-fargate-partner-alb-mtls | ALB + mTLS + WAF + ECS Fargate |
| appsync-graphql-public | AppSync + Cognito Authorizer + DynamoDB |

追加 / 削除 / 統合の提案がございましたらご教示ください。
**目的**: 開発リソース配分（最初に作る製品の優先度）の確定。

---

### 【製品の対応リージョン】 (API-D-2202, 🟡)

各 Service Catalog 製品の対応リージョン（東京 / 大阪両対応か）をご教示ください。
**目的**: [§C-API-5 §C-5.1 / §NFR-API-5](../proposal/nfr/05-dr.md) のリージョン展開。

---

### 【開発者ポータルの構築範囲】 (API-D-2241, 🟡)

開発者ポータルの構築範囲をご教示ください。
- Service Catalog UI（AWS 標準）のみで足りる
- 追加で社内ポータル（Backstage 等）を構築
- AWS Marketplace SaaS の SaaS Listings 活用
**目的**: [§C-API-5 §C-5.4](../proposal/common/05-self-service-catalog.md) のセルフサービス強度。

---

## ヒアリング後の確定事項チェックリスト

Phase D 完了時点で、以下が **確定**していることを確認してください：

- [ ] 公開範囲（信頼プロファイル）昇格の承認権限者（D-101）
- [ ] Bot Control 対象 URI（D-1221）
- [ ] LZA / 自前の選定（D-721、再確認）
- [ ] 規制リスト（D-1501）
- [ ] 業界規制対応アプリの扱い（D-1502）
- [ ] Critical Tier 対象 API リスト（D-1302）
- [ ] 既存 Critical アプリの移行期限（D-1721）
- [ ] 移行支援体制（D-1722）
- [ ] アカウント体系再編要否（D-1801）
- [ ] SecOps / Platform の境界（D-2101）
- [ ] 必須タグ（CostCenter 粒度）（D-401）
- [ ] 按分の最小粒度（D-411）
- [ ] Service Catalog 初期ラインナップ（D-2201）

これらが揃うと、本標準を **承認・発行可能**な状態になります。
