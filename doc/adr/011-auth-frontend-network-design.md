# ADR-011: 認証基盤前段ネットワーク設計（HTTPS / カスタムドメイン / WAF / CloudFront）の統合判断

- **ステータス**: Proposed（要件定義フェーズで Accepted に昇格予定）
- **日付**: 2026-04-21
- **関連**:
  - [keycloak-network-architecture.md §6](../common/keycloak-network-architecture.md)（本番課題 N1 / N5 / N10 / N16）
  - [ADR-008](008-keycloak-start-dev-for-poc.md)（PoC での HTTP:80 採用）
  - [ADR-010](010-keycloak-private-subnet-vpc-endpoints.md)（Private Subnet + VPC Endpoint）

---

## Context

本番移行時、以下の 4 つのネットワーク設計判断が**セットで発生**する:

| # | 判断事項 | 現状 | 本番要件 |
|---|---------|------|---------|
| N1  | HTTPS 化 | HTTP:80（ALB 終端） | HTTPS:443 必須 |
| N5  | カスタムドメイン | ALB の AWS DNS 名 | `auth.example.com` 等の正式ドメイン |
| N10 | WAF の適用 | 未導入（IP 制限のみ） | 攻撃検知・レート制限・ボット対策 |
| N16 | CloudFront の配置 | 未導入（ALB 直接） | 導入有無を判断 |

### なぜ統合判断が必要か

1. **ACM 証明書の配置場所** が N1 / N5 / N16 に連動
   - ALB 終端なら ACM（ap-northeast-1 リージョナル）
   - CloudFront 終端なら ACM（us-east-1 グローバル）
2. **WAF の種類**（regional WAFv2 / global WAFv2）が N10 / N16 に連動
   - ALB 直接なら regional WAFv2（同リージョン）
   - CloudFront 経由なら global WAFv2（us-east-1）
3. **DDoS 対策**（Shield Standard / Advanced）が N16 に連動
   - CloudFront 経由だとエッジで DDoS 吸収
4. **Cognito / Keycloak 両対応**の要否
   - Cognito Hosted UI はカスタムドメイン設定が特殊（User Pool Domain）
   - Keycloak は ALB / CloudFront 任意で終端可能

個別に決めると後戻りコストが大きいため、一つの ADR で統合判断する。

---

## Options（構成パターン）

ALB 前段と終端の組み合わせで 4 パターンに整理:

| パターン | HTTPS 終端 | WAF 位置 | DDoS | カスタムドメイン | 追加月額目安 | 適用例 |
|--------|:---------:|:-------:|:----:|:--------------:|:-----------:|-------|
| **A: ALB のみ（現状）** | ALB (ACM regional) | なし | Shield Standard | Route 53 → ALB | $0 | PoC のみ。本番不可 |
| **B: ALB + regional WAFv2** | ALB (ACM regional) | ALB 直付け | Shield Standard | Route 53 → ALB | +$5〜 + WCU 課金 | 国内向け・シンプル構成 |
| **C: CloudFront + ALB + global WAFv2** | CloudFront (ACM us-east-1) | CloudFront 直付け | Shield Standard（エッジ吸収） | Route 53 → CloudFront → ALB | +$10〜 + リクエスト課金 | グローバル展開・標準パターン |
| **D: 上記 C + Shield Advanced** | 同上 | 同上 | Shield Advanced | 同上 | +$3,010/月 | 大規模・金融等 |

### 各パターンの詳細比較

| 評価軸 | A | B | C | D |
|--------|:-:|:-:|:-:|:-:|
| 実装難易度 | ★ | ★★ | ★★★ | ★★★ |
| 本番セキュリティ要件適合 | ❌ | ✅ | ✅ | ✅✅ |
| レイテンシ（国内） | 最速 | 最速 | やや増（+5〜10ms） | 同左 |
| レイテンシ（海外） | 遅い | 遅い | 速い（エッジ） | 同左 |
| ACM 証明書管理 | 1 箇所 | 1 箇所 | 2 リージョン（ap-northeast-1 + us-east-1）| 同左 |
| WAF ルール設計難易度 | — | 中 | 高（エッジ配信） | 同左 |
| DDoS 耐性 | 低 | 低 | 中 | 高（SLA 保証） |
| 運用コスト | 低 | 中 | 中〜高 | 高 |

### Cognito 側の制約

Cognito Hosted UI のカスタムドメインは **CloudFront が AWS 内部で自動配置**される（User Pool Domain 機能）。したがって:
- Keycloak 側のみ CloudFront 導入 → 運用ドメインが不均一
- 両者とも CloudFront 経由 → 運用ドメインを統一できる

---

## Decision（Proposed）

### 暫定推奨: Pattern B（ALB + regional WAFv2）を**デフォルト**、Pattern C（CloudFront）は以下の条件で採用

**Pattern C（CloudFront）を採用すべき条件**:
- ✅ 顧客拠点がグローバル分散している
- ✅ AWS Shield Advanced を使いたい（将来オプション）
- ✅ Cognito Hosted UI 側とドメイン体系を統一したい
- ✅ 静的コンテンツ（ログインページのアセット）も同じドメインで配信したい
- ✅ 既存の CloudFront 運用ノウハウがある

**それ以外（国内のみ・シンプル構成）なら Pattern B で十分**。

### 確定に必要な情報（要件定義でヒアリング）

| ヒアリング項目 | 回答が Pattern C を要請する場合 |
|-------------|------------------------------|
| 顧客拠点の地理的分布 | 海外拠点あり |
| DDoS 攻撃の想定有無 | Shield Advanced 検討レベル |
| Cognito / Keycloak 両対応でのドメイン統一要否 | 統一必須 |
| 既存の CloudFront 運用基盤 | あり（ナレッジ転用可） |
| 認証ドメインのブランディング戦略 | `auth.顧客ブランド.com` 等を顧客ごとに発行 |

### ACM 証明書配置ルール

Pattern 確定後:
- **Pattern B**: `ap-northeast-1` に ACM 証明書 1 つ
- **Pattern C**: `us-east-1`（CloudFront 用）+ `ap-northeast-1`（ALB 用、内部通信ヘルスチェックや直アクセス用）の 2 箇所

---

## Consequences

### Pros（統合判断によって得られる効果）

- ACM / WAF / CloudFront / DNS の**重複検討・再設計を回避**
- Cognito / Keycloak のドメイン戦略を**同時に整合**できる
- 要件定義での論点を **5 項目のヒアリング**に収束させられる

### Cons

- 判断を先送りにする構造上、**要件定義が遅延すると本番実装がブロック**される
- Pattern C 採用時は `us-east-1` の ACM 管理が必要（Terraform provider alias 設定など実装複雑化）

### 本 ADR の非対応スコープ

- **Admin ALB 側の前段設計**は本 ADR 対象外（keycloak-network-architecture.md N2、別 ADR 化予定）
- **API Gateway 前段の CloudFront**（SPA 配信用）も対象外（別議論）

---

## Alternatives Considered

| 案 | 判断 |
|----|------|
| 個別 ADR（N1 / N5 / N10 / N16 を別々に決定） | 判断が分散し一貫性が取れない。却下 |
| 決定を全て先送り | 本番実装直前に認識齟齬が発生する。却下 |
| 本 ADR で統合判断（採用） | 論点の抜け漏れを防ぎ、ヒアリング項目を収束できる |

---

## Follow-up

1. 要件定義ヒアリング（[requirements-hearing-strategy.md](../requirements/requirements-hearing-strategy.md) Phase C）で上記 5 項目を確認
2. 結果を踏まえ、本 ADR のステータスを **Proposed → Accepted** に更新
3. 決定パターンに基づく Terraform 実装（インフラ変更は別 PR）
4. Cognito 側カスタムドメイン設定との整合確認（User Pool Domain の制約調査）
