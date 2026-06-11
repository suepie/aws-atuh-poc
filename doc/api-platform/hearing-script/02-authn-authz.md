# §FR-API-2 認証認可

> 元データ: [../hearing-checklist.md B-2](../hearing-checklist.md#b-2-認証認可fr-api-2)
> 対象: アプリリード / セキュリティ
> 関連章: [§FR-API-2](../proposal/fr/02-authn-authz.md) / [§C-API-3](../proposal/common/03-shared-auth-boundary.md)

---

### 【Access Token / ID Token の選定】 (API-B-201, 🔥)

共有認証基盤から発行されるトークンのうち、本標準（各アプリの API 認証）で **Access Token / ID Token のどちらを使う**方針が望ましいかご教示ください。
OAuth 2.0 の推奨は Access Token（リソースアクセス用）です。ID Token はユーザー識別用（UI 表示等）の用途であり、API 認証への利用は OAuth 仕様の趣旨と一致しない場面があります。
**目的**: [§FR-API-2 §2.1](../proposal/fr/02-authn-authz.md) / [§C-API-3](../proposal/common/03-shared-auth-boundary.md) の認証契約確定。共有認証基盤側との **トークン受け渡し仕様**が決まります。

---

### 【必須検証クレームリスト】 (API-B-202, 🔥)

JWT 検証で **必ず検証する**クレームのリストをご教示ください。
- 標準必須: `iss`（発行元）、`aud`（対象オーディエンス）、`exp`（有効期限）
- 推奨追加: `nbf`（有効開始）、`iat`（発行時刻）、`azp`（authorized party）、`scope`
- カスタム: `tenant_id`（マルチテナント分離）、`roles`（認可）
**目的**: [§FR-API-2 §2.1](../proposal/fr/02-authn-authz.md) で各アプリが共通に守る検証ルールを定めます。クレーム漏れがあるとセキュリティ脆弱性となるため、最低ラインの統一が必要です。

---

### 【JWKS が Private のときの取得方式】 (API-B-203, 🔥)

共有認証基盤の JWKS エンドポイントが **プライベート化されている場合**（PoC で検討中）、本標準側でどう取得するか、ご見解をお願いします。
選択肢:
- API Gateway / ALB のマネージド Authorizer が直接取得（VPC 経由 / VPC Endpoint）
- Lambda Authorizer で取得して検証（カスタムロジック）
- 各アプリで JWKS をローカルキャッシュし定期同期
**目的**: [§C-API-3 §C-3.1 / §C-3.2](../proposal/common/03-shared-auth-boundary.md) の境界仕様確定。JWKS が Public（既定）か Private（PoC 検討中）で、本標準の検証構成が大きく変わります。

---

### 【Partner 新規デフォルト認証】 (API-B-211, 🔥)

> **前提**：本問は **Phase A の API-A-112 / A-113 で Partner B2B M2M がスコープに含まれる**ことが確認された場合のみ確認します。「Partner B2B 連携なし」なら本問は skip です。

Partner 区分（B2B 接続）API の **新規デフォルト認証方式** を、以下のいずれにする方針が望ましいかご教示ください。

業界主流（Salesforce / Microsoft Graph / Stripe モダン版）は **OAuth 2.0 Client Credentials Grant** をデフォルトとしています。本標準もこれを推奨しています。

選択肢:
- **A. OAuth Client Credentials**（業界主流、本標準推奨）+ API Key は legacy / trial 用に退く
- **B. API Key を維持**（既存 Partner 互換性重視、旧来 B2B 方式）
- **C. Partner-tier 制**（Bronze=API Key / Silver=OAuth / Gold=mTLS）

**目的**: [§FR-API-2 §2.2](../proposal/fr/02-authn-authz.md) のデフォルト確定。OAuth Client Credentials を選ぶと、Partner Application 台帳の管理が **共有認証基盤側** に依存します（[§C-API-3](../proposal/common/03-shared-auth-boundary.md)）。認証側でも Partner Client 管理機能は現状未要件化のため、本問が「Yes」になった場合は **認証側に追加要件として申し送り**ます（[escalation-to-auth.md §1.1](../escalation-to-auth.md)）。

---

### 【API Key の有効期限・ローテーション】 (API-B-212, 🟡)

API Key（Legacy / Trial 用途）の有効期限とローテーションポリシーをご教示ください。
- ローテーション周期（90 日 / 180 日 / 1 年 / 任意）
- ローテーション時の旧キー併存期間（Overlap Period、24-72h が業界標準）
- 自動ローテーション vs 手動申請
**目的**: [§FR-API-2 §2.2 / §NFR-API-4 §4.2](../proposal/nfr/04-security.md) のシークレット管理標準。長すぎると漏洩リスク、短すぎると Partner 側運用負荷増。

---

### 【Partner identity 識別単位】 (API-B-214, 🟡)

Partner Application Credentials の **識別単位**をご教示ください。業界標準は Per-Partner-App × Per-Environment（Acme Mobile (prod), Acme Mobile (stg), Acme Web (prod) のように細分化）です。

選択肢:
- **A. Per-Partner-App × Per-Environment**（業界標準、本標準推奨）
- **B. Per-Partner Organization**（Acme Corp 全体に 1 Credential、シンプル運用）
- **C. Hybrid**（Partner 規模次第）

**目的**: [§FR-API-2 §2.2 / §C-API-3](../proposal/common/03-shared-auth-boundary.md) の Partner App 台帳設計。識別単位が決まると認証基盤側の App Client 管理機能の要件が決まります。

---

### 【Partner Scope / Permission の細粒度】 (API-B-215, 🟡)

Partner ごとの認可（何ができるか）の表現方法をご教示ください。
- OAuth scope のみ（`orders:read`, `orders:write` 等）
- OAuth scope + AWS Verified Permissions（Cedar）併用
- 自前 Lambda Authorizer のカスタムロジック
**目的**: [§FR-API-2 §2.2 / §FR-API-2 §2.4](../proposal/fr/02-authn-authz.md) の認可標準。Partner ごとの細粒度認可が複雑なら Verified Permissions / OPA に拡張します。

---

### 【Partner クレデンシャルのローテーション + Overlap Period】 (API-B-216, 🟡)

Partner クレデンシャル（OAuth Client Credentials の client_secret）のローテーション周期と Overlap Period をご教示ください。
- ローテーション周期（90 日 / 180 日 / 1 年）
- Overlap Period（旧新併存期間、24-72h が業界標準）
- Compromise 検知時の Revocation リードタイム（24h 以内が標準）
**目的**: [§FR-API-2 §2.2 / §NFR-API-4](../proposal/nfr/04-security.md) のクレデンシャルライフサイクル管理。

---

### 【Partner オンボーディングフロー】 (API-B-217, 🟡)

新規 Partner のオンボーディングフロー（申請 → 承認 → Credential 発行）の所在をご教示ください。
- 自社開発ポータル（社内システム）
- AWS Marketplace（SaaS Listings）
- 営業個別契約 + 手動発行
- 上記組合せ
**目的**: [§FR-API-2 §2.2](../proposal/fr/02-authn-authz.md) のオンボーディング標準。AWS Marketplace は課金統合パートナーシップで有用、自社開発はカスタマイズ性が高い反面、構築コストあり。

---

### 【Partner-tier の差別化】 (API-B-218, 🟢)

Partner を tier 別（Bronze / Silver / Gold 等）に差別化する方針はありますか。
- なし（全 Partner 同じ認証 / SLA / コスト）
- 2 tier（Standard / Premium）
- 3 tier（Bronze / Silver / Gold 等）
**目的**: [§FR-API-2 §2.2](../proposal/fr/02-authn-authz.md) の Partner-tier 構成。tier 別に認証方式（API Key / OAuth / mTLS）や SLA を変えるかが決まります。

---

### 【既存 Partner の認証方式と互換性】 (API-B-219, 🟡)

既存 Partner（既に契約・運用中）の認証方式と、本標準への移行可否をご教示ください。
- 全件 OAuth Client Credentials に移行可（移行期間 N ヶ月）
- 一部の重要 Partner は既存方式（API Key 等）を維持
- 既存は全て維持、新規のみ OAuth
**目的**: [§FR-API-2 §2.2 / §NFR-API-9](../proposal/nfr/09-compatibility.md) の移行範囲。

---

### 【mTLS 証明書の発行・配布元】 (API-B-220, 🟡)

mTLS を採用する Partner（規制業界・重要パートナー）の場合、クライアント証明書の発行・配布元はどこを想定されますか。
- 自社 PKI（既存があれば）
- AWS Private Certificate Authority (Private CA)
- Partner 側 CA（信頼ルートを Truststore に追加）
- 上記の組合せ
**目的**: [§FR-API-2 §2.2](../proposal/fr/02-authn-authz.md) の mTLS 運用設計。発行元によって Truststore 管理・失効リスト（CRL）運用が変わります。

---

### 【Internal 区分の標準認証】 (API-B-221, 🟡)

Internal 区分（社内マイクロサービス間 API）の標準認証は **IAM auth（SigV4）** / **JWT** のどちらをデフォルトとする方針が望ましいかご教示ください。
- **IAM auth**：AWS ネイティブ、Cross-account も Resource Policy で制御
- **JWT**：エンドユーザーの認可情報（テナント・ロール）が必要なら有利
既存アプリが JWT 前提で実装されている場合の混在許容方針も併せて教えてください。
**目的**: [§FR-API-2 §2.3](../proposal/fr/02-authn-authz.md) の Internal デフォルト確定。VPC Lattice の Auth Policy（IAM ベース）と相性があります。

---

### 【Cross-account IAM 信頼関係の配布】 (API-B-222, 🟢)

Cross-account API 呼び出し（Account A → Account B の API）のための IAM 信頼関係セットアップを、Service Catalog で標準テンプレとして配布しますか、それとも各アプリで自前構築する方針ですか。
**目的**: [§FR-API-2 §2.3 / §C-API-5](../proposal/common/05-self-service-catalog.md) のテンプレ範囲。配布対象なら Service Catalog 製品（cross-account IAM role pattern）を追加します。

---

### 【GitHub Actions / GitLab CI で OIDC Federation 必須化するか】 (API-B-225, 🔥)

CI/CD パイプライン（GitHub Actions、GitLab CI、Bitbucket Pipelines 等）から AWS API を呼び出す際の認証を、**OIDC Federation（AssumeRoleWithWebIdentity）必須化**する方針でよろしいかご確認ください。

AWS 公式推奨パターン（2022〜）は：
- パイプラインで **永続 AWS Access Key を埋め込まない**（Secrets に長期保存しない）
- 代わりに **CI/CD プロバイダの OIDC token** を使い、AWS STS で **一時 credentials（15 分〜1h TTL）** を取得
- Trust Policy で repo / branch / environment 単位の細粒度制御

選択肢:
- **新規 CI/CD は OIDC 必須化、既存も N ヶ月以内に移行**
- 新規のみ OIDC、既存は維持
- 任意（Access Key 直接埋め込みも許容、本標準推奨と乖離）

**目的**: [§FR-API-2 §2.3.A.2 §2.3.A.3](../proposal/fr/02-authn-authz.md) の CI/CD 認証標準。Access Key 直接埋め込みは漏洩リスクが高く、業界アンチパターンとされています。

---

### 【on-prem 認証のデフォルト】 (API-B-226, 🟡)

社内 on-prem サーバから AWS API を呼び出す場合、**mTLS** と **OAuth Client Credentials**（共有認証基盤利用、§2.3.A.5）のどちらをデフォルトとする方針が望ましいかご教示ください。
- **mTLS**：既存 PKI 資産があれば自然、エンタープライズ標準
- **OAuth Client Credentials**：PKI 不要、共有認証基盤 1 箇所で管理
- 用途別判断（PKI ある資産は mTLS、新規は OAuth 等）

**目的**: [§FR-API-2 §2.3.A.2 §2.3.A.5](../proposal/fr/02-authn-authz.md) の on-prem 認証標準。既存 PKI 資産の有無で判断が変わります。

---

### 【Vendor SaaS の External ID 必須化】 (API-B-227, 🟡)

Vendor SaaS（Datadog / Splunk / New Relic / Snyk 等）と AWS の連携で **External ID 必須化**するスコープをご教示ください。

External ID は Vendor 発行のランダム文字列を Trust Policy に埋め込み、**confused deputy 攻撃**（他顧客の Trust Policy 流用）を防ぐ AWS 公式パターンです。

選択肢:
- 全 Vendor 連携で必須化（Trust Policy 標準テンプレで配布）
- 主要 Vendor のみ必須（Datadog / Splunk 等）
- Vendor 側が要求するもののみ（既存維持）

**目的**: [§FR-API-2 §2.3.A.2 §2.3.A.4](../proposal/fr/02-authn-authz.md) の Vendor 連携セキュリティ最低ライン。Trust Policy 標準テンプレ化なら Service Catalog 配布対象になります。

---

### 【レガシー API Key 認証の許容範囲・移行期限】 (API-B-228, 🟡)

レガシーシステム（モダン認証非対応、API Key 直接埋め込み等）の **本標準への移行期限**をご教示ください。

選択肢:
- 半年以内に全件移行（厳格）
- 1 年以内、Tier 別優先順位（Critical 優先）
- 個別判断（システム廃止予定があれば現状維持等）
- 移行期限なし（永久に許容しない方針なら例外申請制）

**目的**: [§FR-API-2 §2.3.A.6 §2.3.A.7 / §NFR-API-9](../proposal/nfr/09-compatibility.md) の移行戦略。API Key 直接埋め込みは漏洩リスクが高く、本標準の死守事項（§NFR-API-4）と矛盾するため移行が前提です。

---

### 【Lambda Authorizer の使用制限】 (API-B-241, 🟡)

Lambda Authorizer（カスタムロジックでの認証認可）の使用を、**例外承認制**（標準は IAM auth / マネージド JWT Authorizer）にする方針はいかがでしょうか。
Lambda Authorizer はレイテンシ +20-100ms / コスト増 / キャッシュ設計必須のため、無制限採用は本標準の方針と衝突します。
**目的**: [§FR-API-2 §2.4](../proposal/fr/02-authn-authz.md) の Authorizer 選定方針。例外承認制にすると本標準の運用負荷・コスト最適化が達成しやすくなります。

---

### 【Lambda Authorizer のキャッシュ TTL】 (API-B-242, 🟢)

Lambda Authorizer を採用する場合の、認証結果キャッシュ TTL の標準値をご教示ください。
一般的に Cognito Authorizer は 5 分、JWT は exp までが基準です（API Gateway カスタム Authorizer は 5 分上限）。
**目的**: [§FR-API-2 §2.4 / §C-API-3 §C-3.3](../proposal/common/03-shared-auth-boundary.md) のレイテンシ / コスト / 一貫性のバランス確定。

---

### 【AWS Verified Permissions の採用】 (API-B-243, 🟢)

AWS Verified Permissions（Cedar 言語ベースの細粒度認可サービス）を本標準の認可標準として採用する方針はありますか。
- 全面採用（細粒度認可の社内標準）
- 試験採用（特定アプリのみ）
- 採用しない（アプリ自前 ABAC / RBAC）
**目的**: [§FR-API-2 §2.4](../proposal/fr/02-authn-authz.md) の細粒度認可標準。共有認証基盤の認可基盤と相補的に動作する場合があります。

---

## ヒアリング後の確定事項チェックリスト

- [ ] Access / ID Token の選定（B-201）
- [ ] 必須検証クレームリスト（B-202）
- [ ] JWKS 取得方式（B-203）
- [ ] Partner デフォルト認証（B-211）
- [ ] Internal デフォルト認証（B-221）

これらが揃うと **§FR-API-2 認証認可** と **§C-API-3 共有認証基盤との接続点** を確定できます。
