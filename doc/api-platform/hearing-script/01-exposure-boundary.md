# §FR-API-1 公開境界（Public / Internal / Partner / Private）

> 元データ: [../hearing-checklist.md B-1](../hearing-checklist.md#b-1-公開境界fr-api-1)
> 対象: アプリリード / アーキテクト
> 関連章: [§FR-API-1](../proposal/fr/01-exposure-boundary.md)

---

### 【Internal → Public 昇格時の対応方針】 (API-B-101, 🟡)

「Internal だが将来 Public 化する可能性がある」API について、初期から **Public 構成（CloudFront + WAF + JWT 認証）で組む**か、**Internal 構成で組んで後で昇格させる**か、いずれの方針が望ましいかご教示ください。
昇格時のコスト（再構成 / クライアント影響）と初期コストの比較見解も併せていただけますと幸いです。
**目的**: [§FR-API-1 §1.1 / §1.3](../proposal/fr/01-exposure-boundary.md) で公開境界の変更プロセスを定義しています。本標準で「**昇格を前提とした構成テンプレ**」を提供するか、「**昇格申請をハードルとして残す**」かで Service Catalog 製品ラインナップが変わります。

---

### 【IP allowlist のみで Public を許容するか】 (API-B-102, 🟡)

「IP allowlist のみで Public 公開」とする運用を本標準で許容しますか。
本標準は **IP allowlist のみで公開する API は原則 Partner 区分扱い**（API Key + WAF を併用、または mTLS）を推奨していますが、既存運用への影響を含めご見解をお願いします。
**目的**: [§FR-API-1 §1.1](../proposal/fr/01-exposure-boundary.md) の区分定義。IP allowlist を「Public + IP 制限」とするか「Partner 区分」とするかで、認証要件と監査アカウントの FMS 配信ルールが異なります（[§FR-API-7](../proposal/fr/07-guardrails.md)）。

---

### 【HTTP API / REST API のデフォルト選定】 (API-B-104, 🔥)

新規 API の **デフォルト** を HTTP API / REST API のどちらにする方針が望ましいかご教示ください。
- **HTTP API デフォルト**：約 71% 安価・低レイテンシ。ただし Usage Plan / API Key 非対応
- **REST API デフォルト**：機能フル。Usage Plan / Private endpoint / mTLS をネイティブサポート
- **要件別に選択**（Usage Plan 必要なら REST、それ以外は HTTP）
**目的**: 本標準の中核選定の 1 つ（[§FR-API-1 §1.2 / §FR-API-5 §5.1](../proposal/fr/05-serverless-standard.md)）。デフォルトを決めると Service Catalog 製品の構成と運用ノウハウの蓄積方向が決まります。

---

### 【CloudFront 全 Public API 必須化】 (API-B-105, 🔥)

すべての Public API で **CloudFront を前段に置くことを必須化**しますか。
CloudFront 前段は次の利点があります：
- AWS WAF を Edge で評価（リージョン WAF より広範な防御）
- 直叩き防止（origin custom header secret パターン）
- エッジキャッシュによる性能向上
ただし固定費（リクエスト課金 + データ転送）が増加します。
**目的**: [§FR-API-1 §1.2 / §C-API-1 §C-1.2](../proposal/common/01-reference-architecture.md) の参照アーキ確定。必須化なら Service Catalog 製品の全 Public 系に CloudFront を組み込み、任意なら選択肢として残します。

---

### 【VPC Lattice の採用範囲】 (API-B-106, 🟡)

**VPC Lattice**（クロス VPC / クロスアカウントの service-to-service 通信を SigV4 / IAM で実現）の採用範囲をご教示ください。
- 全クロスアカウント内部 API で標準化
- 一部の新規アプリのみ採用
- 既存 PrivateLink / VPC ピアリングとの混在を許容
- 採用しない
**目的**: [§FR-API-1 §1.2 / §FR-API-6 §6.3](../proposal/fr/06-container-standard.md) のクロスアカウント通信標準。Lattice 採用範囲で **既存 PrivateLink 資産の扱い**と **Service Connect / Lattice の選定境界**が決まります。

---

## ヒアリング後の確定事項チェックリスト

Phase B-1 完了時点で、以下が揃っていることを確認してください：

- [ ] HTTP API / REST API のデフォルト方針（B-104）
- [ ] CloudFront 必須化判断（B-105）
- [ ] VPC Lattice の採用範囲（B-106）

これらが揃うと **§FR-API-1 公開境界** と **§C-API-1 参照アーキ** の章を確定できます。
