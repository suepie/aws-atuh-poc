# PowerPoint 資料 構成案・参考資料マトリクス（API プラットフォーム標準）

> **目的**: 関係者提示用 PowerPoint 資料の **大項目構成 + 各項目の参考資料一覧**を整理した SSOT。
> **背景**: ヒアリングと並行して資料を準備するため、各章・項目で **どのドキュメントを参照すれば良いか** を一覧化。
> **対象読者**: PowerPoint 作成担当者 / 要件定義レビュー担当者 / 関係者提示担当者
> **更新基準**: 大項目構成の変更時、参考資料追加時
> **対比**: 認証側 [../requirements/powerpoint-outline-and-references.md](../requirements/powerpoint-outline-and-references.md) の API 版。本標準は 2 系統並行カタログ + ガードレール配信が中核ストーリー（認証側は単一プラットフォーム選定が中核）。

---

## 0. 構成サマリー

| 章 | 項目数 | 主題 | スライド枚数目安 | 時間配分目安 |
|:-:|:-:|---|:-:|:-:|
| 1 | 5 | 全体方針・前提（検討方針 / 基本方針 / スコープ / 4 層モデル / ナラティブ）| 24 | 30 分 |
| 2 | 3 | **アーキパターン選定**（ステップ ⓪、SPA+API / SSR+API / SSR モノリス）| 14 | 20 分 |
| 3 | 3 | 公開範囲（信頼プロファイル）（ステップ ①、5 Profile 統合概念）| 14 | 20 分 |
| 4 | 4 | 認証認可（ステップ ②、共有認証基盤連携 / API Key / mTLS / IAM）| 16 | 24 分 |
| 5 | 2 | 流量制御・課金（ステップ ③）| 10 | 18 分 |
| 6 | 4 | 実装ランタイム（ステップ ④、Serverless / Container / モノリス / 選定基準）| 16 | 24 分 |
| 7 | 3 | ガードレール（ステップ ⑤、FMS / SCP / Service Catalog）| 12 | 18 分 |
| 8 | 3 | 観測性（ステップ ⑥、ログ / トレース / メトリクス）| 12 | 18 分 |
| 9 | 6 | 非機能要件（可用性・性能・セキュリティ・DR・運用・コンプラ・コスト・互換性）| 24 | 30 分 |
| 10 | 3 | 横断（共有認証基盤接続点 / 監査ガバナンス / Service Catalog 提供物）| 12 | 20 分 |
| **計** | **36** | - | **~152** | **~220 分（3.7 時間）** |

> ヒアリング 3 回会議計画と照合：M1（章 1-2 中心：方針・アーキパターン）/ M2（章 3-6 中心：技術中核）/ M3（章 7-10 + 最終意思決定：ガードレール・観測・NFR・横断）

### 🔑 PowerPoint と社内 SSOT の narrative 差分（重要）

| 文書 | 主読者 | 提示順序 | narrative |
|---|---|---|---|
| **PowerPoint（本文書）** | 関係者（経営層 / Platform / SecOps / アプリオーナー）| **検討方針 → 基本方針 → スコープ → アーキパターン → 個別要件** | 「**範囲を絞り、必要な統制と共通ルールは守らせ、それ以外はアプリ裁量に委ねる**」 |
| **proposal/ 提示版** | アプリ開発リード + アーキテクト | 6 ステップ ナラティブ（⓪〜⑥）に沿った技術論述 | 「アーキパターン → 公開範囲 → 認証 → 流量 → ランタイム → ガードレール → 観測性」（[proposal/00-index.md](proposal/00-index.md) §1）|
| **requirements-document-structure.md SSOT** | プロジェクト管理者・進捗追跡 | 7 ステップ + ドキュメント体系 + 状態ダッシュボード | 「全体構造・依存関係・進捗の単一情報源」|

**両者の関係**: **要件内容は同じ**。**見せ方の順序のみ違う**。PowerPoint は「**経営層が納得する順序（方針 → スコープ → 個別）**」、社内 SSOT は「**技術論述の順序（ステップ ⓪〜⑥）**」。詳細は §1.1 / §1.4。

---

## 1. 全体方針・前提（5 項目）

### 1.1 検討方針（3 つのスタンス）★ 最初のスライド

**概要**: AWS の API 提供手段は多岐に渡り、すべてを標準で縛ると肥大化する。本検討は **「範囲を絞り、守らせるところは明確に、それ以外はアプリ裁量に委ねる」** スタンスで進める。3 つのスタンス（**強制的な禁止 / 一貫性を持った統制 / 独立性を認める**）として整理。

#### スライド構成案（3 枚）

| # | スライド | 内容 |
|---|---|---|
| 1 | 検討方針の宣言 | 導入文 + 業界標準（Paved Road / Golden Path / Guardrails-not-Gates）への対応を明示 |
| 2 | 3 つのスタンス一覧 | 強制的な禁止（絞る / 守らせる）/ 一貫性を持った統制（揃える）/ 独立性を認める（委ねる）+ 強制度マトリクス |
| 3 | 業界用語との対応 | Guardrails / Paved Road / Freedom and Responsibility と本標準の対応表 |

#### 重要メッセージング

| 言ってはいけない | 言うべき |
|---|---|
| ❌ 「AWS のすべての API 提供手段を標準化します」 | ✅ 「**範囲を絞り、守るべき統制と共通ルールを明確化**します」 |
| ❌ 「アプリの自由は最小限にします」 | ✅ 「**ガードレール外はアプリ裁量に委ねる**」（強制最小化） |
| ❌ 「独自フレームワークを作ります」 | ✅ 「**業界標準（Netflix Paved Road / Spotify Golden Path）の Platform Engineering アプローチ**」 |

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/00-index.md §0 基本方針](proposal/00-index.md) |
| **内部 SSOT** | [requirements-document-structure.md §0.1](requirements-document-structure.md) |
| **外部** | [Netflix Tech Blog: Scaling Appsec at Netflix](https://netflixtechblog.medium.com/scaling-appsec-at-netflix-6a13d7ab6043) / [Spotify Engineering: Golden Paths](https://engineering.atspotify.com/2020/08/how-we-use-golden-paths-to-solve-fragmentation-in-our-software-ecosystem) / [The New Stack: Paved Roads, Golden Paths, Guardrails and Railroads](https://thenewstack.io/paved-roads-golden-paths-guardrails-and-railroads/) / [Google Cloud: Platform Engineering Control Mechanisms](https://cloud.google.com/blog/products/application-modernization/platform-engineering-control-mechanisms) / [Jason Chan: Guardrails not Gatekeepers](https://platformsecurity.com/blog/guardrails-not-gatekeepers-platform-security-scales-with-engineering) |

### 1.2 基本方針 4 軸

**概要**: 各要件の「中身」を判断する 4 つの価値軸：**絶対安全 / どんなアプリでも / 効率よく / 低運用負荷・コスト**。1.1 の検討方針（決め方の姿勢）と対をなす。

#### スライド構成案（2 枚）

| # | スライド | 内容 |
|---|---|---|
| 1 | 4 軸の一覧 | 各軸の解釈（OWASP / Well-Architected / Paved Road 等）+ どんな判断にどう使うか |
| 2 | 検討方針との対応マトリクス | 「絞る」は どんなアプリでも、「守らせる」は 絶対安全 + 低運用負荷、「揃える」は 効率よく + どんなアプリでも、「委ねる」は どんなアプリでも |

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/00-index.md §0](proposal/00-index.md) |
| **内部 SSOT** | [requirements-document-structure.md §0.1 本標準の基本方針](requirements-document-structure.md) |
| **外部** | [AWS Well-Architected Framework](https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html) / [Serverless Applications Lens](https://docs.aws.amazon.com/wellarchitected/latest/serverless-applications-lens/welcome.html) / [OWASP API Security Top 10](https://owasp.org/API-Security/) |

### 1.3 スコープ宣言（対象 / 対象外）

**概要**: 本標準が対象とする Workload を明示。「外部から HTTP(S) を受ける Workload」全般（SSR モノリス含む）、非 HTTP は別フレーム（Workload 標準）で扱う前提。

#### 対象 / 対象外（スライド 1 枚にまとめる）

| 区分 | 対象 / 対象外 | 例 |
|---|---|---|
| ✅ **対象** | 純粋な API（HTTP API / REST API / GraphQL / WebSocket）| API Gateway + Lambda、ALB + ECS、AppSync 等 |
| ✅ **対象** | SSR モノリス | Next.js full-stack、Nuxt、Rails、Spring Boot + Thymeleaf |
| ✅ **対象** | マイクロサービス間 API | Service Connect / VPC Lattice 経由 |
| ✅ **対象** | 内部 Webhook 受け口 | EventBridge / Lambda Function URL |
| ❌ **対象外** | バッチ・ETL | Step Functions / Glue / EMR 等は別フレーム |
| ❌ **対象外** | ML 推論ジョブ | SageMaker 等は別フレーム |
| ❌ **対象外** | データパイプライン | Kinesis / Kafka は別フレーム |

| 種別 | 参考資料 |
|---|---|
| **内部 SSOT** | [00-index.md §0.1 対象 Workload](00-index.md) |
| **proposal** | [proposal/00-index.md §1 7 ステップ](proposal/00-index.md) |
| **外部** | [AWS Solutions Library: Multi-Account Strategy](https://docs.aws.amazon.com/prescriptive-guidance/latest/multi-account-strategy/welcome.html) |

### 1.4 4 層モデル + 横串（論述構造）

**概要**: 「公開範囲 → 認証認可 → 流量制御 → 実装ランタイム + 横串（観測性・ガードレール・コスト）」の論述構造。**AWS 公式に「4 層モデル」と名付けたフレームワークではなく、複数の AWS 公式 doc + 業界標準に共通する論述順を抽出した本標準の合成・命名**である点を明示。

#### スライド構成案（3 枚）

| # | スライド | 内容 |
|---|---|---|
| 1 | 4 層 + 横串 概念図 | 4 層を縦に、横串を横断で配置した全体図 |
| 2 | 抽出元の一覧 | 7 ソース（AWS 公式 4 + 業界標準 3）の一覧 |
| 3 | 「AWS 流」の射程 | 直接引用ではなく構造的合致の意味で使用、レビュアー対応の標準回答 |

| 種別 | 参考資料 |
|---|---|
| **内部 SSOT** | [requirements-document-structure.md 付録 A.0 章立て構造の根拠](requirements-document-structure.md) |
| **proposal** | [proposal/common/01-reference-architecture.md §C-1.1 4 層モデル全体図](proposal/common/01-reference-architecture.md) |
| **外部** | [Amazon API Gateway Developer Guide](https://docs.aws.amazon.com/apigateway/latest/developerguide/welcome.html) / [Multi-tenant SaaS API access (AWS Prescriptive Guidance)](https://docs.aws.amazon.com/prescriptive-guidance/latest/saas-multitenant-api-access-authorization/) / [Microservices Patterns: API Gateway Pattern](https://microservices.io/patterns/apigateway.html) / [OWASP API Security Top 10](https://owasp.org/API-Security/) |

### 1.5 7 ステップ ナラティブ（語る順序）

**概要**: 検討の論理順序を 7 ステップ（⓪〜⑥）で示す。提示版（proposal/）はこのステップに沿って構成。

```
⓪ アーキパターン選定 → ① 公開範囲 → ② 認証認可 → ③ 流量制御・課金
→ ④ 実装ランタイム → ⑤ ガードレール → ⑥ 観測性
```

#### スライド構成案（2 枚）

| # | スライド | 内容 |
|---|---|---|
| 1 | 7 ステップ図 | mermaid フロー（⓪ を緑、①〜⑥ を黄〜ピンクのグラデーション）|
| 2 | 各ステップで答える問い | 表（ステップ × 問い × 一次ソース）|

| 種別 | 参考資料 |
|---|---|
| **内部 SSOT** | [requirements-document-structure.md §0.2-0.3](requirements-document-structure.md) |
| **proposal** | [proposal/00-index.md §1](proposal/00-index.md) |

---

## 2. アーキパターン選定（ステップ ⓪、3 項目）★ 中核論点

### 2.1 3 アーキパターンの比較

**概要**: SPA + 別 API / SSR + 別 API / SSR モノリスの 3 パターンを並列で比較。本標準は **3 つすべてサポート対象**、選定は各アプリに委ねる方針。

#### スライド構成案（4 枚）

| # | スライド | 内容 |
|---|---|---|
| 1 | 3 パターン全体図 | 各構成のブロック図（クライアント → LB → 実装の流れ）|
| 2 | 詳細比較表 | 観点 × A/B/C パターン（公開範囲・認証・流量・課金・実装・スキル・コスト・適性）|
| 3 | アーキ別の留意点 | A: 業界主流 / B: SEO+モバイル / C: フルスタック・小中規模 |
| 4 | 本標準のスタンス | 「3 つすべてサポート、選定は各アプリに委ねる、決定木で支援」|

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/common/02-runtime-selection-criteria.md §C-2.1 アーキパターン選定](proposal/common/02-runtime-selection-criteria.md) |
| **hearing-checklist** | B-001, B-001-α, B-001-β |
| **hearing-script** | [12-architecture-pattern.md](hearing-script/12-architecture-pattern.md) |
| **外部** | [Next.js Documentation](https://nextjs.org/docs) / [Web.dev: Rendering on the Web](https://web.dev/articles/rendering-on-the-web) / [Microservices.io: API Gateway Pattern](https://microservices.io/patterns/apigateway.html) |

### 2.2 選定決定木

**概要**: モバイル連携 / SEO / フルスタックチーム / 規模 を順に問う決定木。機械的に判定可能な設計。

#### スライド構成案（2 枚）

| # | スライド | 内容 |
|---|---|---|
| 1 | 決定木の図 | mermaid 縦フロー（モバイル → SEO → スキル → 規模 → A/B/C）|
| 2 | デフォルト推奨 | 迷ったら：A、SEO+フルスタック+中小：C、SEO+大規模：B |

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/common/02-runtime-selection-criteria.md §C-2.1.2](proposal/common/02-runtime-selection-criteria.md) |

### 2.3 SSR モノリス特有の論点 ★ 新規追加

**概要**: SSR モノリス採用時、API Gateway 系と異なる **5 つの観点の手段差分**（公開範囲 / 認証 / 流量 / 課金 / 観測性）を整理。

#### スライド構成案（3 枚）

| # | スライド | 内容 |
|---|---|---|
| 1 | モノリスでの 5 観点の差分表 | 観点 × API Gateway 系 / SSR モノリス（path-based / ALB+Cognito / WAF rate / session 計測 / OTel SDK）|
| 2 | モノリス採用時のチェックリスト | フルスタック / 中小規模 / per-tenant 課金不要 / 将来 API 切り出しリスク評価 |
| 3 | 将来の API 切り出し戦略 | §C-2.3 段階移行パスの 3 段階（内部整理 → 切り出し → リプラット）|

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/06-container-standard.md §6.1.A モノリス vs マイクロサービス](proposal/fr/06-container-standard.md) / [proposal/common/02-runtime-selection-criteria.md §C-2.3 段階移行](proposal/common/02-runtime-selection-criteria.md) |
| **hearing-checklist** | A-102-α, A-111, B-002〜B-005 |
| **hearing-script** | [12-architecture-pattern.md](hearing-script/12-architecture-pattern.md) |
| **外部** | [AWS Containers Blog: Securing ECS apps with ALB + Cognito](https://aws.amazon.com/blogs/containers/securing-amazon-elastic-container-service-applications-using-application-load-balancer-and-amazon-cognito/) / [OpenTelemetry: Best Practices for Containers](https://opentelemetry.io/docs/specs/otel/configuration/) |

---

## 3. 公開範囲（信頼プロファイル）（ステップ ①、3 項目）

### 3.1 公開範囲（信頼プロファイル）★ 統合概念化

**概要**: 公開範囲を **「ネットワーク × 認証 × 既定 WAF」の 3 要素を 1 つのパッケージにした信頼プロファイル**として再定義。5 つの Profile から 1 つを選べば、3 要素の既定セットが自動で決まる。Service Catalog 製品と 1:1 で対応。

#### スライド構成案（5 枚）★ 概念定義 → 統合表 → 決定木 → チューニング軸 → モノリス特記

| # | スライド | 内容 |
|---|---|---|
| 1 | **概念定義**：信頼プロファイル | 公開範囲 = ① ネットワーク到達範囲 + ② 認証要件 + ③ 既定 WAF プロファイル を **1 つに束ねた概念**、3 要素を別々に選ぶのではなく **Profile を 1 つ選べば既定が決まる** |
| 2 | **5 Profile 統合表** | **パブリック（認証有）/ パブリック（オープン）/ 社内 / パートナー / 社内限定** × ①②③ |
| 3 | **Profile 選定フロー（決定木）** | インターネット？ → 認証必要？ → 同 Org？ → 5 Profile に到達 |
| 4 | **チューニング可能軸** | Profile = 既定値、別軸（流量閾値・Bot Control 採用・mTLS escalation・アプリ独自 WAF）で個別調整可能 |
| 5 | **「パブリック（オープン）」の扱い** | 「アプリ UI を持たない」デフォルト、ランディング・マーケのみ、認証フローは認証基盤 Hosted UI 委譲 |

#### 重要メッセージング

| 言ってはいけない | 言うべき |
|---|---|
| ❌ 「ネットワークと認証と WAF を別々に決めます」（複雑、組合せ破綻）| ✅ 「**Profile を 1 つ選べば 3 要素の既定が決まります**」（シンプル、業界主流）|
| ❌ 「5 区分の組合せで設計を考えてください」 | ✅ 「**1 つの Profile が 1 つの Service Catalog 製品に対応**します」 |
| ❌ 「カスタマイズは Profile を作るときに全部決めます」 | ✅ 「**Profile = 既定値、業務要件で別軸チューニング可能**」|

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/01-exposure-boundary.md §1.0 / §1.1 信頼プロファイル統合定義](proposal/fr/01-exposure-boundary.md) / [proposal/fr/02-authn-authz.md §2.B 未認証エンドポイントの標準保護](proposal/fr/02-authn-authz.md) |
| **hearing-checklist** | B-101, B-102, B-103, B-107, B-108 |
| **hearing-script** | [01-exposure-boundary.md](hearing-script/01-exposure-boundary.md), [02-authn-authz.md](hearing-script/02-authn-authz.md) |
| **外部** | [API Gateway Endpoint Types](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-api-endpoint-types.html) / [Protect APIs with API Gateway and perimeter protection (AWS Security Blog)](https://aws.amazon.com/blogs/security/protect-apis-with-amazon-api-gateway-and-perimeter-protection-services/) / [Stripe API Authentication](https://docs.stripe.com/api/authentication) / [AWS Well-Architected Security Pillar - Identity and Access Management](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/identity-and-access-management.html) |

### 3.2 ネットワーク構成（HTTP API / REST API / CloudFront / PrivateLink）

**概要**: 区分別の標準ネットワーク構成。HTTP API vs REST API の選定、CloudFront 前段の必須化、PrivateLink / VPC Lattice 連携。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/01-exposure-boundary.md §1.2](proposal/fr/01-exposure-boundary.md) |
| **hearing-checklist** | B-104（HTTP/REST デフォルト）, B-105（CloudFront 必須化）, B-106（VPC Lattice 採用）|
| **hearing-script** | [01-exposure-boundary.md](hearing-script/01-exposure-boundary.md) |
| **外部** | [HTTP API vs REST API (AWS Docs)](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-vs-rest.html) / [Building private cross-account APIs (AWS Blog)](https://aws.amazon.com/blogs/compute/building-private-cross-account-apis-using-amazon-api-gateway-and-aws-privatelink/) / [Amazon VPC Lattice](https://docs.aws.amazon.com/vpc-lattice/latest/ug/what-is-vpc-lattice.html) |

### 3.3 区分変更プロセス（昇格・降格）

**概要**: 公開範囲の昇格（Internal → Public）/ 降格（Partner → Internal）の承認プロセス + リードタイム + 緊急時。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/01-exposure-boundary.md §1.3](proposal/fr/01-exposure-boundary.md) |
| **hearing-checklist** | D-101, D-102, D-103 |
| **hearing-script** | [10-final-decisions.md](hearing-script/10-final-decisions.md) |

---

## 4. 認証認可（ステップ ②、4 項目）

### 4.1 共有認証基盤との連携

**概要**: 共有認証基盤（[../requirements/](../requirements/00-index.md)）の利用側として、JWT 検証 / JWKS 取得 / 障害時縮退の標準を整理。

#### スライド構成案（3 枚）

| # | スライド | 内容 |
|---|---|---|
| 1 | 接続全体図 | 共有認証基盤と本標準の境界（JWT 発行 / 検証 / JWKS）|
| 2 | 検証手段の選択肢 | API Gateway JWT Authorizer / Cognito Authorizer / Lambda Authorizer / ALB Authentication |
| 3 | 障害時の縮退挙動 | JWKS キャッシュ TTL、認証基盤側障害時の API 挙動（401 / 503）|

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/02-authn-authz.md §2.1](proposal/fr/02-authn-authz.md) / [proposal/common/03-shared-auth-boundary.md](proposal/common/03-shared-auth-boundary.md) |
| **hearing-checklist** | B-201, B-202, B-203, C-2001, C-2002 |
| **hearing-script** | [02-authn-authz.md](hearing-script/02-authn-authz.md) |
| **関連 SSOT** | [../requirements/](../requirements/00-index.md) 共有認証基盤の要件定義 |
| **外部** | [Control access to HTTP APIs with JWT authorizers](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-jwt-authorizer.html) |

### 4.2 Partner 認証（OAuth Client Credentials デフォルト / API Key Legacy / mTLS 規制対応）★ 全面刷新 + §2.2.7 リファレンス実装

**概要**: B2B Partner 向けの認証標準を **OAuth Client Credentials（業界主流：Salesforce / Microsoft Graph / Stripe モダン版）をデフォルト** に確定。API Key は Legacy / Trial 用途に退き、mTLS は規制業界の escalation。
**追加 (2026-06-10)**：§2.2.7「Partner 認証 詳細フロー（リファレンス実装）」を proposal に追加。Partner 開発者向けのリファレンス、Service Catalog 製品の元仕様。

#### スライド構成案（5 枚 + リファレンス補足 3 枚）

| # | スライド | 内容 |
|---|---|---|
| 1 | 認証方式 5 種類の比較 | API Key / API Key + IP / OAuth Client Credentials / JWT Bearer / mTLS の信頼レベル × 業界実例 |
| 2 | 本標準のデフォルト推奨 | **OAuth Client Credentials を新規デフォルト**、API Key Legacy 用、mTLS 規制対応 |
| 3 | Partner identity モデル | Per-Partner-App × Per-Environment（業界標準）、共有認証基盤側で M2M Client 管理 |
| 4 | クレデンシャルライフサイクル | 発行 → 配布 → ローテーション → Overlap 24-72h → Revocation 24h |
| 5 | Partner-tier 別構成例 | Bronze（API Key）/ Silver（OAuth）/ Gold（OAuth+mTLS+FAPI 2.0）|
| **R1** | **API Key + OAuth 併用の必要性**（§2.2.7.1 / §2.2.7.2）| API Key = 識別、OAuth = 認証 の役割分担、AWS 公式の明記 |
| **R2** | **詳細フロー シーケンス図**（§2.2.7.3）| セットアップ + 実行時 + Token Refresh、mermaid 図 |
| **R3** | **アンチパターン / 推奨 SDK**（§2.2.7.7 / §2.2.7.10）| ✗ vs ✓ の対比表、推奨 SDK ライブラリ一覧 |

→ R1〜R3 は Partner 開発者向け補足、または社内技術者・Service Catalog 製品設計者向けの深掘り資料。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/02-authn-authz.md §2.2 Partner 認証](proposal/fr/02-authn-authz.md) / **[§2.2.7 Partner 認証 詳細フロー（リファレンス実装）](proposal/fr/02-authn-authz.md)** ⭐ / [proposal/common/03-shared-auth-boundary.md §C-3.1 C. Partner M2M Client 管理機能](proposal/common/03-shared-auth-boundary.md) |
| **hearing-checklist** | **B-211** ⭐, B-212, B-214, B-215, B-216, B-217, B-218, B-219, B-220, D-241 |
| **hearing-script** | [02-authn-authz.md](hearing-script/02-authn-authz.md) |
| **外部** | [OAuth 2.0 Client Credentials (RFC 6749 §4.4)](https://datatracker.ietf.org/doc/html/rfc6749#section-4.4) / [OAuth 2.0 JWT Bearer (RFC 7523)](https://datatracker.ietf.org/doc/html/rfc7523) / [OAuth 2.0 Mutual-TLS (RFC 8705)](https://datatracker.ietf.org/doc/html/rfc8705) / [FAPI 2.0 Security Profile](https://openid.net/specs/fapi-2_0-security-profile.html) / [Stripe API Authentication](https://docs.stripe.com/api/authentication) / [Salesforce OAuth 2.0 Client Credentials](https://help.salesforce.com/s/articleView?id=sf.remoteaccess_oauth_client_credentials_flow.htm) / [AWS Marketplace SaaS Listings](https://docs.aws.amazon.com/marketplace/latest/userguide/saas-listings.html) / [Usage Plans and API Keys for REST APIs](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-api-usage-plans.html) — "Don't use API keys for authentication" 公式明記 |
| **推奨 SDK**（§2.2.7.7）| [Spring Security OAuth2 Client (Java)](https://docs.spring.io/spring-security/reference/servlet/oauth2/client/index.html) / [openid-client (Node)](https://github.com/panva/openid-client) / [requests-oauthlib (Python)](https://github.com/requests/requests-oauthlib) / [golang.org/x/oauth2/clientcredentials (Go)](https://pkg.go.dev/golang.org/x/oauth2/clientcredentials) / [MSAL.NET (.NET)](https://learn.microsoft.com/en-us/entra/msal/dotnet/) |

### 4.3 IAM auth（Internal / Private 向け）

**概要**: AWS 内部からの呼出向け IAM auth（SigV4） + Cross-account Resource Policy + VPC Lattice Auth Policy。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/02-authn-authz.md §2.3](proposal/fr/02-authn-authz.md) |
| **hearing-checklist** | B-221, B-222 |
| **hearing-script** | [02-authn-authz.md](hearing-script/02-authn-authz.md) |
| **外部** | [API Gateway IAM Authentication](https://docs.aws.amazon.com/apigateway/latest/developerguide/permissions.html) / [VPC Lattice Auth Policies](https://docs.aws.amazon.com/vpc-lattice/latest/ug/auth-policies.html) |

### 4.4 Authorizer 選定 + SSR モノリス認証 + 未認証エンドポイント保護

**概要**: Authorizer 4 種（IAM / Cognito / JWT / Lambda）の選定基準 + SSR モノリスでは ALB + Cognito session が第一選択 + **未認証エンドポイント保護パターン**（§2.B、アプリ UI を持たないデフォルト）。

#### スライド構成案（4 枚）

| # | スライド | 内容 |
|---|---|---|
| 1 | Authorizer 4 種選定 | IAM / Cognito / JWT / Lambda の使い分け |
| 2 | SSR モノリス認証 | ALB + Cognito session の第一選択 |
| 3 | 未認証エンドポイント保護（§2.B）| **「アプリ UI を持たない」デフォルト**、Hosted UI / IdP-Initiated 委譲、業界主流 5 パターン（Salesforce / Workday / Slack / Notion / Microsoft 365）|
| 4 | サインアップ要否判断 | B2B + IdP 連携なら JIT で不要、B2C / Trial / SMB のみ必要 |

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/02-authn-authz.md §2.4, §2.A モノリス, §2.B 未認証保護](proposal/fr/02-authn-authz.md) |
| **hearing-checklist** | B-241, B-242, B-243, B-002（モノリス認証）, **B-107** ⭐, B-108, D-1402-α |
| **hearing-script** | [02-authn-authz.md](hearing-script/02-authn-authz.md), [01-exposure-boundary.md](hearing-script/01-exposure-boundary.md), [12-architecture-pattern.md](hearing-script/12-architecture-pattern.md) |
| **外部** | [ALB Authenticate-OIDC](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/listener-authenticate-users.html) / [AWS Verified Permissions](https://docs.aws.amazon.com/verifiedpermissions/) / [AWS WAF ATP (Account Takeover Prevention)](https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-atp.html) / [AWS WAF ACFP (Account Creation Fraud Prevention)](https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups-acfp.html) |

---

## 5. 流量制御・課金（ステップ ③、2 項目）

### 5.1 流量制御（throttle / quota / 超過時挙動）

**概要**: REST API + Usage Plan 標準、HTTP API は WAF rate-based + 自前実装、SSR モノリスは WAF + アプリ内 throttling。

#### スライド構成案（3 枚）

| # | スライド | 内容 |
|---|---|---|
| 1 | 標準値（throttle / burst / quota）| Public B2C / Internal / Partner の 3 段階デフォルト |
| 2 | アーキ別の手段 | API GW（Usage Plan）/ HTTP API（WAF + DDB）/ SSR モノリス（WAF + アプリ内）|
| 3 | 超過時挙動と SLO 扱い | 429 のアラート閾値 + SLO 対象外扱いの整理 |

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/03-throttling-quota.md](proposal/fr/03-throttling-quota.md) / [proposal/fr/03-throttling-quota.md §3.A モノリスでの留意点](proposal/fr/03-throttling-quota.md) |
| **hearing-checklist** | B-301〜B-342, B-003（モノリス流量）|
| **hearing-script** | [03-throttling-quota.md](hearing-script/03-throttling-quota.md), [12-architecture-pattern.md](hearing-script/12-architecture-pattern.md) |
| **外部** | [API Gateway Throttling](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-request-throttling.html) / [AWS WAF Rate-based Rules](https://docs.aws.amazon.com/waf/latest/developerguide/waf-rate-based-rules.html) |

### 5.2 利用者識別 + 課金按分（API Key / JWT クレーム / cost allocation tag）

**概要**: 利用者識別子（API Key / JWT クレーム）、必須タグセット、CUR + Athena による按分パイプライン。SSR モノリスは session / `tenant_id` 計測 + EMF カスタム次元。

#### スライド構成案（3 枚）

| # | スライド | 内容 |
|---|---|---|
| 1 | 必須タグセット（7 種）| CostCenter / Project / Environment / Application / Exposure / Tenant / DataClassification |
| 2 | 按分の最小粒度 | テナント / 部門 / アプリ単位、各々のメリット・デメリット |
| 3 | 按分パイプライン | API Key (per-tenant) または JWT クレーム → EMF → CUR + Athena → QuickSight |

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/04-metering-billing.md](proposal/fr/04-metering-billing.md) / [proposal/fr/04-metering-billing.md §4.A モノリスでの留意点](proposal/fr/04-metering-billing.md) |
| **hearing-checklist** | B-401, B-402, B-411, B-412, B-431, B-432, D-401, D-411, D-412, D-413, B-004（モノリス按分）|
| **hearing-script** | [03-throttling-quota.md](hearing-script/03-throttling-quota.md), [04-metering-billing.md](hearing-script/04-metering-billing.md), [12-architecture-pattern.md](hearing-script/12-architecture-pattern.md) |
| **外部** | [Account-level cost allocation tags (AWS Cost Management)](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/cost-alloc-tags.html) / [CUR 2.0 / Data Exports](https://docs.aws.amazon.com/cur/latest/userguide/) / [Building a cost allocation strategy (AWS)](https://docs.aws.amazon.com/whitepapers/latest/tagging-best-practices/building-a-cost-allocation-strategy.html) |

---

## 6. 実装ランタイム（ステップ ④、4 項目）

### 6.1 Serverless 標準（API Gateway + Lambda）

**概要**: HTTP API デフォルト、Lambda + Powertools + arm64、DynamoDB / Aurora Serverless v2、EventBridge + SQS 非同期。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/05-serverless-standard.md](proposal/fr/05-serverless-standard.md) |
| **hearing-checklist** | B-501〜B-552 |
| **hearing-script** | [05-serverless-standard.md](hearing-script/05-serverless-standard.md) |
| **外部** | [Powertools for AWS Lambda](https://aws.amazon.com/powertools-for-aws-lambda/) / [Serverless Applications Lens](https://docs.aws.amazon.com/wellarchitected/latest/serverless-applications-lens/welcome.html) / [Aurora Serverless v2](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2.html) |

### 6.2 Container 標準（ECS Fargate）

**概要**: Fargate デフォルト、共有 ALB、Service Connect / VPC Lattice、Task Role 最小権限、Blue/Green デプロイ。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/06-container-standard.md §6.1〜§6.5](proposal/fr/06-container-standard.md) |
| **hearing-checklist** | B-601〜B-652 |
| **hearing-script** | [06-container-standard.md](hearing-script/06-container-standard.md) |
| **外部** | [ECS Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-best-practices.html) / [ECS Service Connect](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service-connect.html) / [VPC Lattice for ECS](https://aws.amazon.com/blogs/containers/build-secure-multi-account-multi-vpc-connectivity-for-your-applications-with-amazon-vpc-lattice/) |

### 6.3 モノリス vs マイクロサービス ★ 新規追加

**概要**: Container 系の 2 構成パターン（モノリス / マイクロサービス）の選定基準と運用差分。SSR モノリスは Container 一択（Lambda の制約で不可）。

#### スライド構成案（3 枚）

| # | スライド | 内容 |
|---|---|---|
| 1 | 2 パターン比較表 | 観点 × モノリス / マイクロサービス（責務 / LB / 通信 / Task Role / デプロイ / スケール / 可観測性 / 適性規模）|
| 2 | モノリス採用時のベースライン | ALB 1 つで path-based / Service Connect 不要 / Task Role 1 つで広めの権限 |
| 3 | マイクロサービス採用時のチェック | サービス境界 / Service Connect / 最小権限 / サービス境界トレース |

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/06-container-standard.md §6.1.A](proposal/fr/06-container-standard.md) |
| **hearing-checklist** | B-001-α, B-001-β（モノリス規模上限）|
| **hearing-script** | [12-architecture-pattern.md](hearing-script/12-architecture-pattern.md) |
| **外部** | [AWS Architecture Blog: Microservices on AWS](https://aws.amazon.com/microservices/) / [Martin Fowler: MonolithFirst](https://martinfowler.com/bliki/MonolithFirst.html) / [Microservices.io: Monolithic Architecture](https://microservices.io/patterns/monolithic.html) |

### 6.4 ランタイム選定基準（決定木）

**概要**: アーキパターン → 実装ランタイムの 2 段階決定木。「迷ったら Serverless、モノリスは Container 一択、長時間 / WebSocket / Cold Start NG は Container」。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/common/02-runtime-selection-criteria.md §C-2.2](proposal/common/02-runtime-selection-criteria.md) |
| **hearing-checklist** | D-1901, D-1902, D-1911, D-1912 |
| **hearing-script** | [10-final-decisions.md](hearing-script/10-final-decisions.md) |
| **外部** | [When to use API Gateway vs Lambda Function URLs (theburningmonk)](https://theburningmonk.com/2024/03/when-to-use-api-gateway-vs-lambda-function-urls/) |

---

## 7. ガードレール（ステップ ⑤、3 項目）

### 7.1 監査アカウント Firewall Manager（FMS 配信）

**概要**: Bot Control 範囲、Managed Rules 段階投入、Shield Advanced 採用、DNS Firewall の Domain List。

#### スライド構成案（3 枚）

| # | スライド | 内容 |
|---|---|---|
| 1 | FMS 配信物の全体図 | WAF / Shield / SG / Network Firewall / Route53 DNS Firewall |
| 2 | WAF Managed Rules 段階投入 | count → block（2 週間移行）+ Bot Control はコスト感度高 |
| 3 | 「上書き不可・追加可」構造 | First/Last rule group + アプリ独自ルールの位置 |

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/07-guardrails.md §7.1](proposal/fr/07-guardrails.md) |
| **hearing-checklist** | D-701〜D-704, D-1221, D-1222 |
| **hearing-script** | [07-guardrails.md](hearing-script/07-guardrails.md) |
| **外部** | [AWS Firewall Manager](https://aws.amazon.com/firewall-manager/) / [FMS Multi-admin (AWS Blog)](https://aws.amazon.com/blogs/security/enable-multi-admin-support-to-manage-security-policies-at-scale-with-aws-firewall-manager/) / [AWS Managed Rules for WAF](https://docs.aws.amazon.com/waf/latest/developerguide/aws-managed-rule-groups.html) |

### 7.2 SCP / Config Rules / 例外承認

**概要**: 予防的（SCP）+ 発見的（Config Rules）の組合せ、LZA 採用 vs 自前構築、例外申請プロセス。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/07-guardrails.md §7.2, §7.4](proposal/fr/07-guardrails.md) |
| **hearing-checklist** | D-721, D-722, D-741, D-742 |
| **hearing-script** | [07-guardrails.md](hearing-script/07-guardrails.md) |
| **外部** | [Landing Zone Accelerator](https://aws.amazon.com/solutions/implementations/landing-zone-accelerator-on-aws/) / [AWS Control Tower Controls](https://docs.aws.amazon.com/controltower/latest/userguide/controls.html) / [Service Control Policies](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html) |

### 7.3 Service Catalog 標準提供物

**概要**: 8 つの標準製品ラインナップ、IaC モジュール体系、開発者ポータル、SSR モノリス用テンプレ追加。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/common/05-self-service-catalog.md](proposal/common/05-self-service-catalog.md) |
| **hearing-checklist** | D-2201, D-2202, D-2241, D-2201-α（モノリステンプレ）|
| **hearing-script** | [07-guardrails.md](hearing-script/07-guardrails.md), [10-final-decisions.md](hearing-script/10-final-decisions.md) |
| **外部** | [AWS Service Catalog](https://docs.aws.amazon.com/servicecatalog/latest/adminguide/) / [AWS CDK](https://docs.aws.amazon.com/cdk/) / [Backstage (CNCF)](https://backstage.io/) |

---

## 8. 観測性（ステップ ⑥、3 項目）

### 8.1 ログ標準（構造化ログ + Powertools + ADOT サイドカー）

**概要**: 構造化ログ（JSON）、Lambda は Powertools、ECS は OpenTelemetry SDK + ADOT サイドカー、Data Protection Policy で PII マスキング、Retention 標準化。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/08-observability.md §8.1, §8.A モノリスでの留意点](proposal/fr/08-observability.md) |
| **hearing-checklist** | C-811, C-812, C-813, B-005（モノリス観測性）|
| **hearing-script** | [08-observability.md](hearing-script/08-observability.md), [12-architecture-pattern.md](hearing-script/12-architecture-pattern.md) |
| **外部** | [Powertools for AWS Lambda - Logger](https://docs.aws.amazon.com/powertools/python/latest/core/logger/) / [CloudWatch Logs Data Protection](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/mask-sensitive-log-data.html) |

### 8.2 トレース（X-Ray → ADOT 移行）

**概要**: **X-Ray SDK が 2026-02-25 maintenance mode → ADOT (OpenTelemetry) 移行が事実上必須**、サンプリング戦略。

#### スライド構成案（2 枚）

| # | スライド | 内容 |
|---|---|---|
| 1 | X-Ray → ADOT 移行 | maintenance mode の経緯 + ADOT で X-Ray バックエンド継続使用可 |
| 2 | サンプリング標準 | 業務別デフォルト（決済 100% / 一般 5% / バッチ 1%）|

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/08-observability.md §8.2](proposal/fr/08-observability.md) |
| **hearing-checklist** | C-821, C-822, C-823 |
| **hearing-script** | [08-observability.md](hearing-script/08-observability.md) |
| **外部** | [ADOT (AWS Distro for OpenTelemetry)](https://aws-otel.github.io/) / [AWS X-Ray Transitions to OpenTelemetry (InfoQ, 2025-11)](https://www.infoq.com/news/2025/11/aws-opentelemetry/) |

### 8.3 メトリクス・アラート・監査ログ

**概要**: SLO テンプレ（Critical 99.99% / Standard 99.95% / Internal 99.5%）、アラート通知先、Synthetics 必須化、CloudTrail Org Trail。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/fr/08-observability.md §8.3, §8.4](proposal/fr/08-observability.md) |
| **hearing-checklist** | C-831, C-832, C-833, D-841, D-842 |
| **hearing-script** | [08-observability.md](hearing-script/08-observability.md) |
| **外部** | [CloudWatch Synthetics](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Synthetics_Canaries.html) / [CloudTrail Organization Trail](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/creating-trail-organization.html) / [Google SRE Workbook: SLO](https://sre.google/workbook/implementing-slos/) |

---

## 9. 非機能要件（6 項目）

### 9.1 可用性・性能・拡張性（§NFR-API-1/2/3）

**概要**: 3 Tier（Critical 99.99% / Standard 99.95% / Internal 99.5%）、Cold start 対策（Provisioned Concurrency / ECS 常時稼働）、ピーク係数 10x、本番アカウント増枠リスト。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/nfr/01-availability.md](proposal/nfr/01-availability.md), [proposal/nfr/02-performance.md](proposal/nfr/02-performance.md), [proposal/nfr/03-scalability.md](proposal/nfr/03-scalability.md) |
| **hearing-checklist** | C-901〜C-1122 |
| **hearing-script** | [09-nfr.md](hearing-script/09-nfr.md) |
| **外部** | [Well-Architected Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html) / [Service Quotas](https://docs.aws.amazon.com/general/latest/gr/aws_service_limits.html) |

### 9.2 セキュリティ死守事項（§NFR-API-4）

**概要**: TLS 1.2+ 必須、CMK 暗号化、シークレットローテーション、Security Hub 準拠標準、死守事項マトリクス。

#### スライド構成案（3 枚）

| # | スライド | 内容 |
|---|---|---|
| 1 | 死守事項マトリクス | 領域（通信 / 認証 / 認可 / WAF / シークレット / 暗号化 / ガードレール / 監査）× 最低ライン |
| 2 | Security Hub 準拠標準 | CIS / FSBP / PCI DSS の選択肢 |
| 3 | Inspector / GuardDuty 採用範囲 | 脆弱性スキャンの対象 |

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/nfr/04-security.md](proposal/nfr/04-security.md) |
| **hearing-checklist** | C-1201〜C-1232, D-1241 |
| **hearing-script** | [09-nfr.md](hearing-script/09-nfr.md) |
| **外部** | [Well-Architected Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html) / [OWASP API Security Top 10](https://owasp.org/API-Security/) / [AWS Security Hub Standards](https://docs.aws.amazon.com/securityhub/latest/userguide/standards-reference.html) |

### 9.3 DR / BCP（§NFR-API-5）

**概要**: Critical Tier はマルチリージョン Active-Active、Standard は Active-Standby、Internal は単一リージョン。切替訓練の必須化スコープ。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/nfr/05-dr.md](proposal/nfr/05-dr.md) |
| **hearing-checklist** | D-1301〜D-1322 |
| **hearing-script** | [09-nfr.md](hearing-script/09-nfr.md) |
| **外部** | [AWS Resilience Hub](https://docs.aws.amazon.com/resilience-hub/) / [Disaster Recovery of Workloads on AWS](https://docs.aws.amazon.com/whitepapers/latest/disaster-recovery-workloads-on-aws/disaster-recovery-workloads-on-aws.html) |

### 9.4 運用 + IaC + CI/CD（§NFR-API-6）

**概要**: ダッシュボード必須化、通知プラットフォーム（PagerDuty / Opsgenie）、CodeDeploy Canary、コンテナベースイメージ再ビルド頻度、ポストモーテム公開範囲。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/nfr/06-operations.md](proposal/nfr/06-operations.md) |
| **hearing-checklist** | C-1401〜C-1422 |
| **hearing-script** | [09-nfr.md](hearing-script/09-nfr.md) |
| **外部** | [AWS CodeDeploy](https://docs.aws.amazon.com/codedeploy/) / [AWS Operational Excellence Pillar](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/welcome.html) |

### 9.5 コンプラ + 監査ログ（§NFR-API-7）

**概要**: 適用規制（PCI / HIPAA / FISC / GDPR / 個人情報保護法）、Security Hub 標準、PII 保持期間、データ所在地、業界認定、Audit Manager。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/nfr/07-compliance.md](proposal/nfr/07-compliance.md) |
| **hearing-checklist** | D-1501〜D-1531 |
| **hearing-script** | [09-nfr.md](hearing-script/09-nfr.md), [10-final-decisions.md](hearing-script/10-final-decisions.md) |
| **外部** | [AWS Audit Manager](https://docs.aws.amazon.com/audit-manager/) / [AWS Artifact](https://aws.amazon.com/artifact/) / [GDPR Center on AWS](https://aws.amazon.com/compliance/gdpr-center/) |

### 9.6 コスト・互換性・移行性（§NFR-API-8/9）

**概要**: 予算アラート、コスト異常検知、arm64 移行、API バージョニング（URL path）、Deprecation 期間、既存アプリ移行期限。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/nfr/08-cost.md](proposal/nfr/08-cost.md), [proposal/nfr/09-compatibility.md](proposal/nfr/09-compatibility.md) |
| **hearing-checklist** | C-1611, C-1612, C-1701, C-1702, D-1601〜D-1722 |
| **hearing-script** | [09-nfr.md](hearing-script/09-nfr.md), [10-final-decisions.md](hearing-script/10-final-decisions.md) |
| **外部** | [AWS Budgets](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html) / [Cost Anomaly Detection](https://docs.aws.amazon.com/cost-management/latest/userguide/manage-ad.html) / [Graviton Migration](https://github.com/aws/aws-graviton-getting-started) |

---

## 10. 横断（3 項目）

### 10.1 共有認証基盤との接続点（§C-API-3）

**概要**: 認証基盤側の契約（OIDC Discovery / JWKS / 鍵ローテーション + **Hosted UI 提供 + Partner M2M Client 管理**）、本標準側の検証動作、障害分離・縮退運転。

#### スライド構成案（4 枚）

| # | スライド | 内容 |
|---|---|---|
| 1 | OIDC / OAuth 基本契約 | Discovery / JWKS / Token / Logout / Authorization Code Flow |
| 2 | Hosted UI 提供（B 追加項目）| Hosted UI / サインアップ UI / HRD ページ / パスワードリセット UI の提供有無、認証側に申し送り |
| 3 | Partner M2M Client 管理（C 追加項目）| App Client 台帳 / Client Credentials 発行 / Scope 管理 / Token endpoint / Revocation API、認証側に申し送り |
| 4 | 障害分離・縮退運転 | JWKS キャッシュ TTL / 認証基盤側障害時の API 挙動（401 / 503）|

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/common/03-shared-auth-boundary.md §C-3.1 A / B / C](proposal/common/03-shared-auth-boundary.md) |
| **hearing-checklist** | C-2001, C-2002, B-201, B-202, B-203, **B-107** ⭐, B-108, B-211 ⭐, B-214, D-1402-α |
| **hearing-script** | [02-authn-authz.md](hearing-script/02-authn-authz.md), [01-exposure-boundary.md](hearing-script/01-exposure-boundary.md) |
| **関連 SSOT** | [../requirements/](../requirements/00-index.md) 共有認証基盤の要件定義 |
| **認証側に申し送る論点** | (1) Hosted UI 提供有無、(2) サインアップ UI 提供有無、(3) HRD ページ所在、(4) Partner M2M App Client 管理機能、(5) Partner App 識別単位（Per-Partner-App × Per-Env） |

### 10.2 監査アカウントとのガバナンス境界（§C-API-4）

**概要**: 役割分担（SecOps / Platform / アプリ）、配信パス（FMS / Service Catalog / SCP / Config Rules）、集約パス（CloudTrail / Config / S3 access log）、操作監査。

#### スライド構成案（3 枚）

| # | スライド | 内容 |
|---|---|---|
| 1 | 役割分担マトリクス | SecOps / Platform / アプリ × 各領域（FMS / WAF / Service Catalog / 例外承認）|
| 2 | 配信パス図 | 監査アカウント → 各アプリ（FMS / Catalog / SCP）の自動配信 |
| 3 | 集約パス図 | 各アプリ → 監査アカウント（CloudTrail / Config / VPC Flow Logs）の集約 |

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/common/04-audit-governance.md](proposal/common/04-audit-governance.md) |
| **hearing-checklist** | D-2101, D-2102, D-2111, D-2112, D-2122, D-2131, D-2132 |
| **hearing-script** | [07-guardrails.md](hearing-script/07-guardrails.md), [10-final-decisions.md](hearing-script/10-final-decisions.md) |
| **外部** | [AWS Security Reference Architecture (SRA)](https://docs.aws.amazon.com/prescriptive-guidance/latest/security-reference-architecture/) / [AWS Control Tower](https://docs.aws.amazon.com/controltower/latest/userguide/what-is-control-tower.html) |

### 10.3 Service Catalog 標準提供物（§C-API-5）

**概要**: 8 つの製品ラインナップ、IaC モジュール体系、バージョン管理・更新通知、開発者ポータル。SSR モノリス用テンプレを追加するかの判断。

| 種別 | 参考資料 |
|---|---|
| **proposal** | [proposal/common/05-self-service-catalog.md](proposal/common/05-self-service-catalog.md) |
| **hearing-checklist** | D-2201, D-2202, D-2241, C-2211, C-2212, C-2221, C-2222 + D-2201-α（モノリス）|
| **hearing-script** | [07-guardrails.md](hearing-script/07-guardrails.md), [10-final-decisions.md](hearing-script/10-final-decisions.md) |
| **外部** | [AWS Service Catalog Best Practices](https://docs.aws.amazon.com/servicecatalog/latest/adminguide/best-practices.html) / [Backstage (Spotify)](https://backstage.io/) |

---

## 11. ユーザー要望 6 テーマ ↔ 新 36 項目のマッピング表

> **目的**: 当初提示された 6 つの要望テーマが新構造のどこに配置されたか、**抜けがないかの確認**用。

| # | ユーザー要望 6 テーマ | 新項目 | 状態 |
|:-:|---|---|:-:|
| 1 | 公開範囲ルール（Public / Internal）| **3.1 信頼プロファイル統合定義（5 Profile）** + **3.2 ネットワーク構成** + **3.3 Profile 変更プロセス** | ✅ 拡張（信頼プロファイル統合概念に再定義）|
| 2 | 流量制限・課金管理 | **5.1 流量制御** + **5.2 利用者識別・課金按分** | ✅ 2 項目に分離 |
| 3 | 監査アカウントの FirewallManager 説明と運用 | **7.1 FMS** + **7.2 SCP/Config** + **10.2 監査ガバナンス境界** | ✅ 3 項目に分離（配信機構 + 横断ガバナンス）|
| 4 | 標準アーキ（Serverless / ECS）| **6.1 Serverless** + **6.2 Container** + **6.3 モノリス vs マイクロサービス** + **6.4 選定基準** | ✅ 拡張（モノリスサブパターン追加）|
| 5 | セキュリティ死守事項 | **9.2 セキュリティ死守事項** | ✅ 死守事項マトリクスで明示 |
| 6 | ログのベストプラクティス | **8.1 ログ標準** + **8.2 トレース** + **8.3 メトリクス・監査ログ** | ✅ 3 項目に分離 |

### 新規追加項目（30 件）

| 新項目 | 追加理由 | 該当 § |
|---|---|---|
| **1.1 検討方針（3 スタンス）** | 業界標準（Paved Road / Guardrails）への準拠を冒頭で示す必要 | proposal/00-index.md §0 + Platform Engineering 業界資料 |
| **1.2 基本方針 4 軸** | 認証側から継承、各要件の評価軸 | proposal/00-index.md §0 |
| **1.3 スコープ宣言** | SSR モノリス含む / 非 HTTP 対象外の明示 | 00-index.md §0.1 |
| **1.4 4 層モデル** | 論述構造の根拠提示、AWS 公式命名でないことの明示 | requirements-document-structure.md 付録 A.0 |
| **1.5 7 ステップ ナラティブ** | 論述順の整理 | proposal/00-index.md §1 |
| **2.x アーキパターン選定（3 項目）** | SSR モノリス含む 3 パターンの選定支援 | §C-API-2 §C-2.1 |
| **4.4 SSR モノリス認証** | ALB + Cognito session の第一選択 | §FR-API-2 §2.A |
| **5.x モノリス向けの流量・課金代替** | API Key/Usage Plan 不可への対応 | §FR-API-3 §3.A, §FR-API-4 §4.A |
| **6.3 モノリス vs マイクロサービス** | Container 系 2 パターン整理 | §FR-API-6 §6.1.A |
| **8.x モノリス観測性** | OTel SDK + ADOT サイドカー | §FR-API-8 §8.A |
| **10.x 横断章（共有認証境界 / 監査 / Catalog）** | 接続点・ガバナンス境界・自己 service 配布の明示 | §C-API-3, 4, 5 |

---

## 12. PowerPoint スライド構成テンプレ

各大項目を以下の **基本テンプレ 3-5 スライド** で構成：

| スライド種別 | 内容 | 想定枚数 |
|---|---|---|
| **概要スライド** | 何を決めるか / なぜ重要か / 関連項目 | 1 枚 |
| **選択肢提示** | A/B/C 案の比較表（業界標準 + 本標準推奨）| 1-2 枚 |
| **業界標準・参考事例** | AWS 公式 / Platform Engineering 系の引用 | 1 枚（必要時）|
| **本標準での推奨** | ベースライン + 理由 + 例外条件 | 1 枚 |
| **ヒアリング質問** | 関係者に確認する項目リスト | 1 枚 |

### スライド作成のコツ

| Tips | 内容 |
|---|---|
| **§の対応を明示** | 各スライド左下に「§FR-API-1」「B-104」等の対応 ID を小さく表示 |
| **Mermaid 図のスクショ** | proposal 内の Mermaid 図を PNG/SVG で書き出して貼る |
| **本標準の推奨をハイライト** | ⭐ マークで「本標準推奨」を明示 |
| **業界実例を 1-2 枚追加** | 「Netflix / Spotify / Auth0 はこの設計」と示すと納得度向上 |
| **比較表は最大 5 列まで** | スライドで読める列数は 4-5 が限界、それ以上は分割 |
| **3 つのスタンスを冒頭で固定** | 1.1 で示した「強制的な禁止 / 一貫性ある統制 / 独立性」を以降のスライドで参照しやすくする |

### 認証側との差分

| | 認証側 | API 側（本書）|
|---|---|---|
| **章の冒頭** | アーキ方針（集約 → 例外）| **検討方針 3 スタンス + 基本方針 4 軸** |
| **中核章** | §1.5 製品選定（Cognito vs Keycloak）| **§2 アーキパターン選定（3 パターン）**+ §6.4 ランタイム選定基準 |
| **narrative** | 集約をデフォルト | 「絞る → 守らせる → 揃える → 委ねる」 |
| **業界引用** | KuppingerCole / Microsoft Federated Identity | Netflix Paved Road / Spotify Golden Path / Guardrails-not-Gates |

---

## 13. ヒアリング会議への適用

### 3 回ヒアリング計画との対応

| 章 | ヒアリング回 | 含まれる項目 | スライド範囲 |
|---|---|---|---|
| **章 1 全体方針・前提（5）** | **M1** | 1.1〜1.5 全て | 約 24 枚 |
| **章 2 アーキパターン選定（3）** | **M1** ★ 中核 | 2.1〜2.3 全て | 約 14 枚 |
| **章 3 公開範囲（3）** | **M2** | 3.1〜3.3 全て | 約 12 枚 |
| **章 4 認証認可（4）** | **M2** | 4.1〜4.4 全て | 約 16 枚 |
| **章 5 流量制御・課金（2）** | **M2** | 5.1〜5.2 全て | 約 10 枚 |
| **章 6 実装ランタイム（4）** | **M2** | 6.1〜6.4 全て | 約 16 枚 |
| **章 7 ガードレール（3）** | **M3** | 7.1〜7.3 全て | 約 12 枚 |
| **章 8 観測性（3）** | **M3** | 8.1〜8.3 全て | 約 12 枚 |
| **章 9 非機能要件（6）** | **M3** | 9.1〜9.6 全て | 約 24 枚 |
| **章 10 横断（3）** | **M3** | 10.1〜10.3 全て | 約 12 枚 |

### 想定スケジュール

| 回 | スライド範囲 | 時間 | 主な対象者 |
|---|---|---|---|
| **M1 第 1 回** | 章 1（24 枚）+ 章 2（14 枚）= **38 枚** | 2 時間 | 経営層 + Platform リード + アプリリード |
| **M2 第 2 回** | 章 3〜6（54 枚）= **54 枚** | 2.5 時間 | アプリリード + アーキテクト |
| **M3 第 3 回** | 章 7〜10（60 枚）= **60 枚** | 2.5 時間 | SecOps + SRE + 経営層 + 意思決定者 |

→ **合計 7 時間**（3 回会議）で全 ~152 枚をカバー。M2 が技術中核で密度高、M1 と M3 でバランス。

### Phase A〜D との対応

| 章 | 対応 Phase | 主目的 |
|---|---|---|
| 章 1.1〜1.5 | **Phase A** | 既存現状・前提共有、検討方針合意 |
| 章 2 | **Phase B-0** ⭐ | アーキパターン選定（中核判断） |
| 章 3〜6 | **Phase B-1〜5** | 技術中核（公開範囲・認証・流量・ランタイム） |
| 章 7〜8 | **Phase C / D** | ガードレール・観測性（運用視点）|
| 章 9 | **Phase C / D** | 非機能要件 |
| 章 10 | **Phase D** | 最終判断（境界 / 監査 / 提供物） |

---

## 14. 関連ドキュメント

### 一次資料（本標準の SSOT）

- [hearing-checklist.md](hearing-checklist.md) — 全 144 項目の SSOT
- [proposal/00-index.md](proposal/00-index.md) — 関係者提示版 SSOT
- [proposal/common/01-reference-architecture.md](proposal/common/01-reference-architecture.md) — §C-API-1 全体参照アーキ
- [proposal/common/02-runtime-selection-criteria.md](proposal/common/02-runtime-selection-criteria.md) — §C-API-2 アーキパターン + ランタイム選定基準
- [requirements-document-structure.md](requirements-document-structure.md) — 要件定義 SSOT（ナラティブ・依存関係・進捗）

### proposal/ サブフォルダ

- [proposal/fr/](proposal/fr/00-index.md) — §FR-API-1〜8 機能要件（8 章）
- [proposal/nfr/](proposal/nfr/00-index.md) — §NFR-API-1〜9 非機能要件（9 章、IPA マッピング）
- [proposal/common/](proposal/common/00-index.md) — §C-API-1〜5 横断章（5 章）

### ヒアリング資料

- [hearing-script/README.md](hearing-script/README.md) — 関係者送付用敬体スクリプト群（11 ファイル）
- [hearing-script/12-architecture-pattern.md](hearing-script/12-architecture-pattern.md) ⭐ — アーキパターン選定（Phase B-0、中核）

### 関連 SSOT（境界対面）

- [../requirements/00-index.md](../requirements/00-index.md) — 共有認証基盤の要件定義（接続対面）
- [../requirements/powerpoint-outline-and-references.md](../requirements/powerpoint-outline-and-references.md) — 認証側 PowerPoint 戦略シート（本書の雛形）

### 業界標準・参考フレームワーク（外部）

- [Netflix Tech Blog: Scaling Appsec at Netflix](https://netflixtechblog.medium.com/scaling-appsec-at-netflix-6a13d7ab6043) — Paved Road の起源
- [Spotify Engineering: Golden Paths](https://engineering.atspotify.com/2020/08/how-we-use-golden-paths-to-solve-fragmentation-in-our-software-ecosystem) — Golden Path 思想
- [The New Stack: Paved Roads, Golden Paths, Guardrails and Railroads](https://thenewstack.io/paved-roads-golden-paths-guardrails-and-railroads/) — 4 概念の横断解説
- [Google Cloud: Platform Engineering Control Mechanisms](https://cloud.google.com/blog/products/application-modernization/platform-engineering-control-mechanisms) — Gates/Guardrails/Paved paths の整理
- [Jason Chan: Guardrails not Gatekeepers](https://platformsecurity.com/blog/guardrails-not-gatekeepers-platform-security-scales-with-engineering) — 用語起源
- [AWS Well-Architected Framework](https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html)
- [AWS Serverless Applications Lens](https://docs.aws.amazon.com/wellarchitected/latest/serverless-applications-lens/welcome.html)
- [AWS Prescriptive Guidance: Multi-tenant SaaS API access](https://docs.aws.amazon.com/prescriptive-guidance/latest/saas-multitenant-api-access-authorization/introduction.html)
- [AWS Security Reference Architecture (SRA)](https://docs.aws.amazon.com/prescriptive-guidance/latest/security-reference-architecture/welcome.html)
- [OWASP API Security Top 10](https://owasp.org/API-Security/)
- [Microservices Patterns: API Gateway Pattern (Chris Richardson)](https://microservices.io/patterns/apigateway.html)
- [IPA 非機能要求グレード 2018](https://www.ipa.go.jp/sec/softwareengineering/std/ent03-b.html)

---

## 15. 改訂履歴

| 日付 | 内容 |
|---|---|
| 2026-06-03 | 初版作成。ユーザー要望 6 テーマ → 36 項目（10 章）に再編成。SSR モノリス対応（§2 アーキパターン選定、§6.3 モノリス vs マイクロサービス、§4.4 / §5 / §8 でモノリス論点反映）。3 回ヒアリング対応 + 認証側との narrative 差分明示。業界標準（Netflix Paved Road / Spotify Golden Path / Guardrails-not-Gates）を §1.1 検討方針の根拠として組み込み |
| 2026-06-03 | **Public 2 段階細分化**（Public-Authenticated / Public-Unauthenticated）+ **アプリ UI を持たないデフォルト**（§3.1 4 枚、§4.4 4 枚に拡張）+ **Partner 認証 OAuth Client Credentials デフォルト化**（§4.2 5 枚に全面刷新、業界主流に整合）+ **§C-API-3 §C-3.1 認証基盤契約の B/C 追加**（Hosted UI 提供 + Partner M2M Client 管理を申し送り、§10.1 4 枚に拡張）。ヒアリング項目追加：B-103, B-107 ⭐, B-108, B-211 ⭐（修正）, B-214〜B-220, D-241, D-1402-α |
| 2026-06-10 | **公開範囲を「信頼プロファイル」として統合概念化**：ネットワーク × 認証 × 既定 WAF の 3 要素を 1 つのパッケージとして束ね、Profile 名を日本語化（パブリック（認証有 / オープン）、社内、パートナー、社内限定）。§3.1 を 4 枚 → 5 枚（概念定義 → 統合表 → 決定木 → チューニング軸 → モノリス特記）に再編。章タイトル「公開範囲 → 公開範囲（信頼プロファイル）」|
| 2026-06-10 | **§2.2.7 Partner 認証 詳細フロー（リファレンス実装）正式組込み**：API Key と OAuth の役割分担、4 つの併用パターン、シーケンス図（セットアップ / 実行時 / Token Refresh）、リクエスト具体例、エラーケース、API Gateway 設定、Token Cache 戦略、推奨 SDK、監査ログ識別、mTLS 併用、アンチパターン。PowerPoint §4.2 にリファレンス補足スライド R1〜R3 を追加 |
