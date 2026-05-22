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

### 【Partner 区分のデフォルト】 (API-B-211, 🟡)

Partner 区分（B2B 接続）API のデフォルト認証方式を、**API Key + WAF** か **mTLS** のどちらにする方針が望ましいかご教示ください。
- **API Key + WAF**：運用容易、Usage Plan による流量制御と一体化
- **mTLS**：強固な認証、ただし証明書ライフサイクル運用コスト
両者を Partner ごとに使い分ける選択肢もあります。
**目的**: [§FR-API-2 §2.2](../proposal/fr/02-authn-authz.md) のデフォルト選定。Service Catalog 製品のラインナップ（Partner 向けが mTLS 版か API Key 版か）に影響します。

---

### 【API Key の有効期限・ローテーション】 (API-B-212, 🟡)

API Key の有効期限とローテーションポリシーをご教示ください。
- ローテーション周期（90 日 / 180 日 / 1 年 / 任意）
- ローテーション時の旧キー併存期間
- 自動ローテーション vs 手動申請
**目的**: [§FR-API-2 §2.2 / §NFR-API-4 §4.2](../proposal/nfr/04-security.md) のシークレット管理標準。長すぎると漏洩リスク、短すぎると Partner 側運用負荷増。

---

### 【mTLS 証明書の発行・配布元】 (API-B-213, 🟡)

mTLS を採用する場合、クライアント証明書の発行・配布元はどこを想定されますか。
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
