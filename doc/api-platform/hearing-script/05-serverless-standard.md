# §FR-API-5 標準アーキテクチャ：Serverless

> 元データ: [../hearing-checklist.md B-4](../hearing-checklist.md#b-4-serverless-標準fr-api-5)
> 対象: アプリリード / アーキテクト
> 関連章: [§FR-API-5](../proposal/fr/05-serverless-standard.md)

---

### 【HTTP API / REST API デフォルト固定】 (API-B-501, 🔥)

> ※ B-104 と重複しますが、本章で改めて確定します。

新規 Serverless API の **デフォルト**を以下のいずれにするかご確定ください：
- **原則 HTTP API**：コスト・低レイテンシ優先、Usage Plan 必要時のみ REST API
- **原則 REST API**：機能フル、コストはマネージドサービス料金として受容
- **要件別判定フロー**：[§FR-API-5 §5.1](../proposal/fr/05-serverless-standard.md) の選定マトリクスで自動判定
**目的**: Service Catalog 製品の主力ラインナップが決まります。

---

### 【Edge-optimized vs Regional + CloudFront】 (API-B-502, 🟡)

API Gateway の Edge-optimized エンドポイント（AWS 管理 CloudFront 経由）と、Regional + 自前 CloudFront 前段のどちらを既定にする方針が望ましいかご教示ください。
- **Edge-optimized**：シンプル、ただし WAF は前段で別途必要
- **Regional + CloudFront**：WAF を CloudFront にバインド可、直叩き防止が組みやすい（本標準推奨）
**目的**: [§FR-API-5 §5.1 / §C-API-1 §C-1.2](../proposal/common/01-reference-architecture.md) の参照アーキ確定。

---

### 【Lambda ランタイムの推奨優先順位】 (API-B-511, 🟡)

新規 Lambda アプリで採用する **ランタイムの社内推奨優先順位** をご教示ください。
候補：Python 3.13 / Node.js 22 / Go 1.x / Java 21 / .NET / Rust
- 第一推奨（最初に検討するもの）
- 第二推奨
- 採用禁止 / 限定（既存資産以外では使わない）
**目的**: [§FR-API-5 §5.2](../proposal/fr/05-serverless-standard.md) のランタイム標準。Powertools 提供範囲・Snap Start 対応・運用ノウハウの集約方向に影響します。

---

### 【arm64 (Graviton) 新規デフォルト化】 (API-B-512, 🟡)

新規 Lambda 関数の **デフォルトアーキテクチャ**を arm64 (Graviton2) にするか、x86_64 を継続するか、ご見解をお願いします。
arm64 は同性能で約 20% 安価ですが、一部のネイティブライブラリで互換性問題が発生する場合があります。
**目的**: [§FR-API-5 §5.2 / §NFR-API-8](../proposal/nfr/08-cost.md) のコスト最適化と互換性のバランス。

---

### 【Lambda Extension 標準セット】 (API-B-513, 🟢)

Lambda Extension（ADOT Collector / Secrets Manager extension / Powertools 等）の **標準セット**を Service Catalog で配布する方針はありますか。
標準セット導入の利点：観測性 / シークレット取得の統一、開発者の認知負荷低減。
欠点：固定的な依存、バージョン管理コスト。
**目的**: [§FR-API-5 §5.2 / §C-API-5](../proposal/common/05-self-service-catalog.md) の Service Catalog 製品設計。

---

### 【新規アプリのデフォルト DB】 (API-B-521, 🟡)

新規アプリのバックエンド DB について、本標準のデフォルト推奨をどちらにする方針が望ましいかご教示ください。
- **DynamoDB on-demand**（サーバレス親和性最高、アクセスパターン先決め必須）
- **Aurora Serverless v2**（リレーショナル、min ACU=0 で休止可能、2025〜）
- **要件別**（リレーショナル要件あれば Aurora、それ以外は DynamoDB）
**目的**: [§FR-API-5 §5.3](../proposal/fr/05-serverless-standard.md) のデフォルト選定。新規アプリの DB アクセスパターンに大きな影響。

---

### 【RDS Proxy 採用基準】 (API-B-522, 🟢)

RDS Proxy の採用基準を本標準で明文化する方針はありますか。
本標準の推奨は「**Aurora Serverless v2 と組まない場合のみ採用**」（二重コスト回避）です。
**目的**: [§FR-API-5 §5.3](../proposal/fr/05-serverless-standard.md) の DB アクセス標準。

---

### 【クロスアカウント EventBridge の標準化】 (API-B-541, 🟢)

クロスアカウントのイベント配信（EventBridge custom event bus + リソースポリシー）を、本標準の **標準パターン**として整備する方針はありますか。
**目的**: [§FR-API-5 §5.4](../proposal/fr/05-serverless-standard.md) のイベント駆動標準。マイクロサービス間の標準パスとして整備すると、各アプリで同じ設計を繰り返す手間が省けます。

---

### 【メッセージスキーマのバージョニング】 (API-B-542, 🟢)

EventBridge メッセージスキーマの **バージョニング方針**をご教示ください。
- EventBridge Schema Registry を活用（マネージド、Java/Python コード自動生成）
- 自前管理（OpenAPI / JSON Schema を Git 管理）
- バージョン管理しない
**目的**: [§FR-API-5 §5.4 / §NFR-API-9](../proposal/nfr/09-compatibility.md) のイベントスキーマ互換性管理。

---

### 【AppSync の位置づけ】 (API-B-551, 🟢)

AppSync（GraphQL マネージドサービス）を本標準の **選択肢**に入れる方針か、**例外承認制**にする方針か、ご見解をお願いします。
AppSync は GraphQL / Subscription / 複数バックエンド集約に強いですが、Lambda + REST 慣れたチームには学習コストがあります。
**目的**: [§FR-API-5 §5.5](../proposal/fr/05-serverless-standard.md) のラインナップ確定。

---

### 【Function URL の使用範囲】 (API-B-552, 🟢)

Lambda Function URL（API Gateway なし、HTTPS 直接公開）の使用範囲を、本標準で **Webhook + 内部用途（IAM auth）に限定**する方針でよろしいかご確認ください。
**目的**: [§FR-API-5 §5.5](../proposal/fr/05-serverless-standard.md) の例外パターン管理。API Gateway 機能（throttle / API Key）が必要なケースでの誤用を防ぎます。

---

## ヒアリング後の確定事項チェックリスト

- [ ] HTTP API / REST API デフォルト（B-501）
- [ ] Lambda ランタイム推奨順位（B-511）
- [ ] arm64 新規デフォルト化（B-512）
- [ ] 新規アプリのデフォルト DB（B-521）

これらが揃うと **§FR-API-5 Serverless 標準** と **Service Catalog の Serverless 製品ラインナップ** を確定できます。
