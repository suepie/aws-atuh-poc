# Phase C: 非機能要件まとめ（NFR-API-1〜9）

> 元データ: [../hearing-checklist.md C-2〜C-6 + D-5/6/8/9/10](../hearing-checklist.md#c-2-可用性性能拡張性nfr-api-13)
> 対象: アプリリード / SRE / SecOps / 経理 / 経営層
> 関連章: [§NFR-API-1〜9](../proposal/nfr/00-index.md)

---

## 可用性（§NFR-API-1）

### 【新規 API のデフォルト Tier】 (API-C-901, 🟡)

新規 API のデフォルト Tier を **Standard**（可用性 99.95% / RTO < 1h）とする方針でよろしいかご確認ください。
Critical / Internal / Batch は要件次第で個別指定する想定です。
**目的**: [§NFR-API-1 §1.1](../proposal/nfr/01-availability.md) のデフォルト確定。

---

### 【Critical API のマネージド SLA 達成構成】 (API-C-902, 🟡)

Critical Tier（可用性 99.99%）は単一マネージドサービスの SLA（多くは 99.95%）では達成不可です。本標準では **マルチリージョン構成 + DynamoDB Global Tables / Aurora Global Database** を必須化する方針でよろしいかご確認ください。
**目的**: [§NFR-API-1 §1.1 / §NFR-API-5](../proposal/nfr/05-dr.md) の Critical Tier 構成標準。

---

### 【3 AZ 既定化】 (API-C-911, 🟢)

新規アカウントの **VPC 既定を 3 AZ**（東京は 4 AZ あり）にする方針でよろしいかご確認ください。
**目的**: [§NFR-API-1 §1.2](../proposal/nfr/01-availability.md) のマルチ AZ 既定。

---

### 【タイムアウト階層の業務別標準値】 (API-C-921, 🟢)

クライアント → APIGW → Lambda/ECS → DB/外部 API の各層のタイムアウト階層の **業務別標準値**をご教示ください。
**目的**: [§NFR-API-1 §1.3](../proposal/nfr/01-availability.md) の cascading failure 防止。

---

### 【Circuit Breaker 実装手段】 (API-C-922, 🟢)

外部依存への Circuit Breaker 実装手段の標準化方針をご教示ください。
- OSS ライブラリ（resilience4j / Polly / opossum 等）
- App Mesh / Service Connect の組込み機能
- Lambda 内自前実装
**目的**: [§NFR-API-1 §1.3](../proposal/nfr/01-availability.md) のレジリエンス標準。

---

## 性能（§NFR-API-2）

### 【既存実測ベースライン取得】 (API-C-1001, 🟡)

既存アプリの **レイテンシ実測ベースライン**取得は可能ですか。
既存値が分かると Tier 割当（Critical / Standard / Bulk）の妥当性検証に有用です。
**目的**: [§NFR-API-2 §2.1](../proposal/nfr/02-performance.md) の Tier 割当。

---

### 【Tier の割当方針】 (API-C-1002, 🟡)

レイテンシ Tier の割当方針をご教示ください。
- 業務カテゴリ別自動（決済は Real-time、レポートは Bulk 等）
- アプリ申請 + 承認
- 一律 Standard、要件あれば個別指定
**目的**: [§NFR-API-2 §2.1](../proposal/nfr/02-performance.md) の運用ルール。

---

### 【Real-time Tier に Provisioned Concurrency】 (API-C-1011, 🟡)

Real-time Tier API（p99 < 300ms）に **Lambda Provisioned Concurrency** を既定で設定する方針でよろしいかご確認ください。
Provisioned Concurrency は固定費が発生しますが、Cold start を排除できます。
**目的**: [§NFR-API-2 §2.2 / §NFR-API-8](../proposal/nfr/08-cost.md) のレイテンシ vs 固定費。

---

### 【ECS Fargate 既定 desired count】 (API-C-1012, 🟢)

ECS Fargate task の既定 desired count をご教示ください（Cold start なしの起動状態保持目的）。
- 1（最小、SLO 達成困難）
- 2（マルチ AZ、最小冗長）
- 3（3 AZ 各 1）
**目的**: [§NFR-API-2 §2.2 / §NFR-API-1](../proposal/nfr/01-availability.md) の可用性とコストのバランス。

---

### 【負荷テストの本番リリース前必須化】 (API-C-1021, 🟡)

本番リリース前の負荷テスト実施を **必須化する範囲**をご教示ください。
- 全 API
- Critical / Standard Tier
- Critical のみ
**目的**: [§NFR-API-2 §2.3](../proposal/nfr/02-performance.md) の SLO 達成検証。

---

### 【性能リグレッション検知の CI 統合】 (API-C-1022, 🟢)

性能リグレッション検知を CI/CD に統合する方針はありますか。
**目的**: [§NFR-API-2 §2.3](../proposal/nfr/02-performance.md) の継続性能保証。

---

## 拡張性（§NFR-API-3）

### 【既存実測ピーク取得】 (API-C-1101, 🟡)

既存アプリの **ピーク TPS 実測**取得は可能ですか。
**目的**: [§NFR-API-3 §3.1](../proposal/nfr/03-scalability.md) の標準値妥当性検証。

---

### 【ピーク係数の妥当性】 (API-C-1102, 🟡)

本標準のピーク係数（平常の 10x）は、季節変動・キャンペーン時に十分でしょうか。
**目的**: [§NFR-API-3 §3.1](../proposal/nfr/03-scalability.md) のスケール設計余裕。

---

### 【DynamoDB on-demand 選定基準】 (API-C-1111, 🟡)

DynamoDB の **on-demand vs provisioned + auto-scaling** の選定基準をご教示ください。
本標準の暫定推奨は「**新規は on-demand 既定**」（不規則トラフィックに強い、運用シンプル）です。
**目的**: [§NFR-API-3 §3.2 / §NFR-API-8](../proposal/nfr/08-cost.md) のコスト最適化。

---

### 【ECS scale-out 余裕】 (API-C-1112, 🟢)

ECS Application Auto Scaling の cooldown / step の標準値をご教示ください。
**目的**: [§NFR-API-3 §3.2](../proposal/nfr/03-scalability.md) のスケール応答性。

---

### 【本番アカウントの必須増枠リスト】 (API-C-1121, 🟡)

本番アカウントの **必須増枠リスト**（Lambda 同時実行 / API GW RPS / DynamoDB on-demand 等）を Service Catalog で初期化する方針はありますか。
**目的**: [§NFR-API-3 §3.3](../proposal/nfr/03-scalability.md) の本番障害予防。

---

### 【クォータ監視アラート通知先】 (API-C-1122, 🟢)

Service Quotas の 80% 到達アラートの通知先をご教示ください。
**目的**: [§NFR-API-3 §3.3 / §NFR-API-6](../proposal/nfr/06-operations.md) の運用連動。

---

## セキュリティ（§NFR-API-4）

### 【TLS 1.3 必須化】 (API-C-1201, 🟡)

TLS 1.3 を必須化する方針はありますか。旧クライアントとの互換性は問題ありませんか。
**目的**: [§NFR-API-4 §4.1](../proposal/nfr/04-security.md) の通信暗号化。

---

### 【内部 service mTLS 必須化】 (API-C-1202, 🟡)

内部 service 間（ECS Service Connect / Lattice）の mTLS を必須化する方針はありますか。
**目的**: [§NFR-API-4 §4.1 / §FR-API-6](../proposal/fr/06-container-standard.md) の内部通信。

---

### 【CMK の粒度】 (API-C-1211, 🟡)

KMS Customer Managed Key の粒度（アプリ単位 / 環境単位 / リソース種別単位）をご教示ください。
**目的**: [§NFR-API-4 §4.2](../proposal/nfr/04-security.md) のキー管理。

---

### 【シークレットローテーション未対応 DB の段階移行】 (API-C-1212, 🟡)

シークレット自動ローテーション未対応の DB（古い MySQL 等）の段階移行計画をご教示ください。
**目的**: [§NFR-API-4 §4.2 / §NFR-API-9](../proposal/nfr/09-compatibility.md) の移行スコープ。

---

### 【Security Hub 準拠標準】 (API-C-1231, 🟡)

Security Hub で評価する準拠標準をご教示ください。
- CIS AWS Foundations Benchmark
- AWS Foundational Security Best Practices (FSBP)
- PCI DSS Standard
- NIST 800-53
組合せ可能です。
**目的**: [§NFR-API-4 §4.4 / §NFR-API-7](../proposal/nfr/07-compliance.md) のコンプラ評価軸。

---

### 【Inspector のスコープ】 (API-C-1232, 🟢)

Amazon Inspector（脆弱性スキャン）の **対象スコープ**をご教示ください。
- 全 Lambda + ECR + EC2
- 重要 Lambda + ECR のみ
- ECR のみ
**目的**: [§NFR-API-4 §4.4](../proposal/nfr/04-security.md) の脆弱性管理コスト。

---

### 【JWKS キャッシュ TTL】 (API-C-2001, 🟢)

JWKS キャッシュ TTL の標準値をご教示ください。マネージド既定（5-15 分）で十分か、独自設定が必要か。
**目的**: [§C-API-3 §C-3.3](../proposal/common/03-shared-auth-boundary.md) の障害耐性。

---

### 【認証基盤障害時の縮退挙動】 (API-C-2002, 🟡)

共有認証基盤側障害（JWKS 取得失敗等）時の API 縮退挙動を、**401（認証失敗）** / **503（サービス不可）** のどちらにするか、ご見解をお願いします。
**目的**: [§C-API-3 §C-3.3](../proposal/common/03-shared-auth-boundary.md) のフォールトトレランス設計。

---

### 【VPC Flow Logs 集約必須化】 (API-C-2121, 🟡)

VPC Flow Logs の集約必須化範囲をご教示ください。
- 全 VPC
- Public 公開リソースの VPC のみ
- Production のみ
**目的**: [§C-API-4 §C-4.3](../proposal/common/04-audit-governance.md) の証跡完全性。

---

## DR（§NFR-API-5）

### 【新規 API のデフォルト Tier（DR）】 (API-D-1301, 🔥)

DR Tier（RPO/RTO）のデフォルトをご教示ください。
- Standard（RPO 1h / RTO 4h、Active-Standby）
- Internal（RPO 24h / RTO 24h、単一リージョン）
**目的**: [§NFR-API-5 §5.1](../proposal/nfr/05-dr.md) の DR 既定。

---

### 【Critical Tier の対象 API リスト】 (API-D-1302, 🔥)

Critical Tier（RPO < 5min / RTO < 30min、Active-Active マルチリージョン）に該当する **対象 API リスト**をご教示ください。
**目的**: [§NFR-API-5 §5.1](../proposal/nfr/05-dr.md) の Critical 対象確定。

---

### 【Critical Tier の対象リージョン】 (API-D-1311, 🟡)

Critical Tier のマルチリージョン対象（東京 + ?）をご教示ください。
- 東京（ap-northeast-1）+ 大阪（ap-northeast-3）：国内 2 拠点
- 東京 + シンガポール（ap-southeast-1）：海外バックアップ
**目的**: [§NFR-API-5 §5.2 / §NFR-API-7 §7.4](../proposal/nfr/07-compliance.md) のデータ所在地。

---

### 【Active-Standby のコスト試算】 (API-D-1312, 🟡)

Active-Standby（Warm / Pilot Light）の **コスト試算**は実施済みですか。
**目的**: [§NFR-API-5 §5.2 / §NFR-API-8](../proposal/nfr/08-cost.md) のコスト見通し。

---

### 【切替訓練の必須化スコープ】 (API-D-1321, 🟡)

DR 切替訓練の必須化スコープをご教示ください。
- Critical のみ年 2 回
- Standard 含めて年 1 回
- 訓練しない（IaC で復旧可能性を担保）
**目的**: [§NFR-API-5 §5.3](../proposal/nfr/05-dr.md) の実効性検証。

---

### 【Resilience Hub 採用範囲】 (API-D-1322, 🟢)

AWS Resilience Hub（構成評価ツール）の採用範囲をご教示ください。
**目的**: [§NFR-API-5 §5.3](../proposal/nfr/05-dr.md) の評価ツール。

---

## 運用（§NFR-API-6）

### 【ダッシュボード必須化範囲】 (API-C-1401, 🟡)

CloudWatch Dashboard 作成の必須化範囲をご教示ください。
**目的**: [§NFR-API-6 §6.1](../proposal/nfr/06-operations.md) の可視化標準。

---

### 【通知先プラットフォーム】 (API-C-1402, 🟡)

オンコール通知プラットフォームをご教示ください（PagerDuty / Opsgenie / Slack 等）。
**目的**: [§NFR-API-6 §6.1](../proposal/nfr/06-operations.md) のアラート設計。

---

### 【Critical Tier の段階デプロイ手段】 (API-C-1411, 🟡)

Critical Tier の段階デプロイ手段の必須化（CodeDeploy Canary / Lambda Alias weight）をご教示ください。
**目的**: [§NFR-API-6 §6.2](../proposal/nfr/06-operations.md) の本番リリース安全性。

---

### 【コンテナベースイメージの再ビルド頻度】 (API-C-1412, 🟢)

コンテナベースイメージ（Amazon Linux 2023 等）の再ビルド頻度の標準をご教示ください。
- 週次
- 月次
- 脆弱性検知時のみ
**目的**: [§NFR-API-6 §6.2](../proposal/nfr/06-operations.md) のパッチ管理。

---

### 【ステータスページの採用範囲】 (API-C-1421, 🟢)

外部公開のステータスページの採用範囲をご教示ください。
**目的**: [§NFR-API-6 §6.3](../proposal/nfr/06-operations.md) の顧客コミュニケーション。

---

### 【ポストモーテム公開範囲】 (API-C-1422, 🟢)

ポストモーテム（障害事後分析）の公開範囲をご教示ください。
- 社内全部
- チーム内
- 経営層のみ
**目的**: [§NFR-API-6 §6.3](../proposal/nfr/06-operations.md) の組織学習文化。

---

## コスト（§NFR-API-8）

### 【予算アラート閾値】 (API-C-1611, 🟡)

AWS Budgets のアラート閾値の既定値をご教示ください（50% / 80% / 100% / 120% 等）。
**目的**: [§NFR-API-8 §8.2](../proposal/nfr/08-cost.md) のコスト管理。

---

### 【異常検知の通知先】 (API-C-1612, 🟢)

Cost Anomaly Detection の通知先をご教示ください。
**目的**: [§NFR-API-8 §8.2](../proposal/nfr/08-cost.md) のコスト暴騰検知。

---

## 互換性・移行性（§NFR-API-9）

### 【バージョニング方式】 (API-C-1701, 🟡)

API バージョニング方式の既定をご教示ください。本標準推奨は URL path 方式（`/v1/...`）です。
**目的**: [§NFR-API-9 §9.1](../proposal/nfr/09-compatibility.md) の互換性管理。

---

### 【OpenAPI 公開の必須化範囲】 (API-C-1702, 🟡)

OpenAPI 仕様書公開の必須化範囲をご教示ください（Public / Partner / Internal / 全部）。
**目的**: [§NFR-API-9 §9.1 / §C-API-5](../proposal/common/05-self-service-catalog.md) の開発者ポータル。

---

### 【CDK vs Terraform】 (API-C-2211, 🟡)

社内推奨 IaC 言語をご教示ください。
- CDK（TypeScript / Python）
- Terraform
- 用途別（Service Catalog 製品は CDK、共有インフラは Terraform 等）
**目的**: [§C-API-5 §C-5.2](../proposal/common/05-self-service-catalog.md) の IaC 標準。

---

### 【既存 CFn アプリへの対応】 (API-C-2212, 🟡)

既存が **CloudFormation のみで実装されている**アプリへの対応方針をご教示ください。
- CDK / Terraform への移行を求める
- CFn のまま本標準準拠を許容
- 個別判断
**目的**: [§C-API-5 §C-5.2 / §NFR-API-9](../proposal/nfr/09-compatibility.md) の移行コスト。

---

### 【旧バージョン製品の併存期間】 (API-C-2221, 🟡)

Service Catalog 製品の **major バージョン更新時、旧バージョン製品を併存させる期間**をご教示ください。
- 6 ヶ月
- 12 ヶ月
- 業務影響別
**目的**: [§C-API-5 §C-5.3 / §NFR-API-9](../proposal/nfr/09-compatibility.md) の更新サイクル。

---

### 【アプリ側のアップデート義務】 (API-C-2222, 🟢)

Service Catalog 製品更新時の **アプリ側アップデート義務**をご教示ください。
- major：必須移行（旧バージョン終了時）
- minor：推奨
- patch：自動更新
**目的**: [§C-API-5 §C-5.3](../proposal/common/05-self-service-catalog.md) の更新運用。

---

## ヒアリング後の確定事項チェックリスト

- [ ] 新規 API のデフォルト Tier（C-901, D-1301）
- [ ] Critical Tier 対象 API リスト（D-1302）
- [ ] Security Hub 準拠標準（C-1231）
- [ ] ADOT 採用必須化（C-821、再確認）
- [ ] IaC 言語（C-2211）

これらが揃うと **§NFR-API 全章** を確定できます。
