# §FR-API-1 公開範囲（信頼プロファイル）（Public / Internal / Partner / Private）

> 元データ: [../hearing-checklist.md B-1](../hearing-checklist.md#b-1-公開範囲（信頼プロファイル）fr-api-1)
> 対象: アプリリード / アーキテクト
> 関連章: [§FR-API-1](../proposal/fr/01-exposure-boundary.md)

---

### 【Internal → Public 昇格時の対応方針】 (API-B-101, 🟡)

「Internal だが将来 Public 化する可能性がある」API について、初期から **Public 構成（CloudFront + WAF + JWT 認証）で組む**か、**Internal 構成で組んで後で昇格させる**か、いずれの方針が望ましいかご教示ください。
昇格時のコスト（再構成 / クライアント影響）と初期コストの比較見解も併せていただけますと幸いです。
**目的**: [§FR-API-1 §1.1 / §1.3](../proposal/fr/01-exposure-boundary.md) で公開範囲（信頼プロファイル）の変更プロセスを定義しています。本標準で「**昇格を前提とした構成テンプレ**」を提供するか、「**昇格申請をハードルとして残す**」かで Service Catalog 製品ラインナップが変わります。

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

### 【未認証アクセスが必須のエンドポイント棚卸し】 (API-B-103, 🔥)

各アプリで **未認証アクセス（JWT を要求しない）が必須なエンドポイント**を棚卸ししていただけますでしょうか。
本標準では公開範囲を **パブリック（認証有）**（JWT 必須）と **パブリック（オープン）**（認証不要）の 2 Profile に分けて扱うため、後者に該当するエンドポイントを明確化したい意図があります。

代表的な該当例：
- ランディング・マーケティングページ（HTML / Web）
- 価格・公開カタログ（HTML / 公開 API）
- 公開データ API（`/api/v1/public/*`）
- ヘルスチェック（外部公開する場合）
- `robots.txt` / `sitemap.xml`
- HRD（Home Realm Discovery）ページ（採用時）

**目的**: [§FR-API-1 §1.1 公開範囲（信頼プロファイル） 5 区分](../proposal/fr/01-exposure-boundary.md) / [§FR-API-2 §2.B 未認証エンドポイントの標準保護パターン](../proposal/fr/02-authn-authz.md) の対象スコープ確定。パブリック（オープン） に該当するエンドポイントがどの程度あるかで、CloudFront キャッシュ戦略・WAF 設定の標準化方針が決まります。

---

### 【サインイン / サインアップ UI をアプリで持つかどうか】 (API-B-107, 🔥)

各アプリは **サインイン / サインアップ UI を自前で実装する**方針ですか、それとも **共有認証基盤の Hosted UI に委譲する**方針ですか。

本標準のデフォルトスタンスは「**アプリ UI を持たない**」（業界主流: Salesforce / Workday / ServiceNow / Slack / Notion 等が Hosted UI 委譲を採用）です。

選択肢:
- **A. IdP-Initiated SSO（完全委譲）**: アプリ UI なし、顧客 IdP の画面から開始
- **B. SP-Initiated（テナント別 URL）**: 「ログイン」リンクのみ、URL に tenant 埋込
- **C. SP-Initiated + HRD**: メアド入力ページのみ、ドメインから IdP 判定
- **D. Hosted UI 委譲（Cognito / Keycloak login page）**: 「ログイン」リンクのみ
- **E. アプリ完全実装**: アプリ内でフォーム実装（例外承認制を想定）

**目的**: [§FR-API-2 §2.B](../proposal/fr/02-authn-authz.md) のデフォルトスタンス確定。「アプリ UI を持たない」を本標準のデフォルトにすると、パブリック（オープン） は主にマーケ・公開データ系に絞られ、設計がシンプルになります。本問は認証側（doc/requirements/）の方針判断と連動します。

---

### 【サインアップフローの所在】 (API-B-108, 🟡)

サインアップ機能（新規ユーザー作成）が必要なアプリの場合、サインアップフローはどこで実行されますか。
- **IdP 連携 JIT**（初回ログインで自動作成、サインアップ UI 不要）
- **認証基盤の Hosted UI**（B2C / Trial / SMB 向け、認証基盤側でフォーム）
- **アプリ内実装**（例外、強いカスタマイズ要件）
- **不要**（招待型フローのみ、または管理者が手動作成）

**目的**: [§FR-API-2 §2.B サインアップの要否判断](../proposal/fr/02-authn-authz.md) の確定。B2B 顧客 IdP 連携前提なら JIT が標準、B2C 等は Hosted UI 委譲が標準です。

---

## ヒアリング後の確定事項チェックリスト

Phase B-1 完了時点で、以下が揃っていることを確認してください：

- [ ] HTTP API / REST API のデフォルト方針（B-104）
- [ ] CloudFront 必須化判断（B-105）
- [ ] VPC Lattice の採用範囲（B-106）

これらが揃うと **§FR-API-1 公開範囲（信頼プロファイル）** と **§C-API-1 参照アーキ** の章を確定できます。
