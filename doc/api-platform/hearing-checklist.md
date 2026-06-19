# API プラットフォーム標準 ヒアリングチェックリスト

> 本標準を確定するために関係者（アプリチーム / SecOps / Platform / 経営層）に確認すべき項目の **単一一覧**。
> 顧客送付用の敬体スクリプトは [hearing-script/](hearing-script/README.md) を参照。
> 親 SSOT: [requirements-document-structure.md](requirements-document-structure.md)

---

## ヒアリング設計

### Phase 構成

| Phase | 主題 | 想定対象 | 想定時間 |
|---|---|---|---|
| **Phase A** | 既存アプリ現状・前提（共通） | アプリリード + Platform | 60-90 分 |
| **Phase B** | 技術要件（公開範囲 / 認証 / 流量 / ランタイム / 観測性） | アプリリード + アーキテクト | 120-180 分 |
| **Phase C** | 運用・セキュリティ・コンプラ・コスト | SecOps + 運用 + 経営層 | 90-120 分 |
| **Phase D** | 最終判断（ガードレール承認 / 移行計画 / 体制） | 経営層 + SecOps + Platform | 60 分 |

### 凡例

- **優先度**: 🔥 最優先（本標準の中核判断）/ 🟡 重要 / 🟢 通常
- **ID**: `API-{Phase}-NNN` 形式
- **状態**: ⏳ 未確認 / 🟡 仮回答 / ✅ 確定

---

## Phase A: 既存アプリ現状・前提

> 対象: アプリリード / Platform / 既存運用担当

| ID | 質問 | 関連 FR/NFR | 優先度 | 状態 |
|---|---|---|:---:|:---:|
| API-A-101 | 標準化対象とする既存アプリ AWS アカウントの一覧と数 | §FR-API-1〜8 全般 | 🔥 | ⏳ |
| API-A-102 | 各アプリの現状実装（Serverless / Container / 混在 / その他）の概況 | §FR-API-5, §FR-API-6 | 🔥 | ⏳ |
| API-A-103 | 既存 API の公開範囲区分の現状（明確 / 曖昧）と曖昧な API の再評価可否 | §FR-API-1 | 🟡 | ⏳ |
| API-A-104 | 既存 API の月間リクエスト数・ピーク TPS の実測有無 | §NFR-API-2, §NFR-API-3 | 🟡 | ⏳ |
| API-A-105 | 既存アプリの AWS アカウント数と OU 構成 | §C-API-1 §C-1.4 | 🟡 | ⏳ |
| API-A-106 | Landing Zone Accelerator (LZA) / Control Tower の導入状況 | §C-API-1 §C-1.4 | 🟡 | ⏳ |
| API-A-107 | 共有認証基盤の利用状況・利用予定（フェーズ） | §C-API-3 | 🔥 | ⏳ |
| API-A-108 | 既存アプリの IaC 化率（CDK / Terraform / CFn / 手作業） | §C-API-5 | 🟡 | ⏳ |
| API-A-109 | 主要なアプリチームの技術スキル分布（Lambda 経験 / Container 経験） | §C-API-2 | 🟡 | ⏳ |
| API-A-110 | 本標準の対象範囲（全アプリ / 新規のみ / Critical のみ） | §NFR-API-9 | 🔥 | ⏳ |
| API-A-111 | 新規アプリで採用予定のアーキパターン（SPA+API / SSR+API / SSR モノリス）の想定分布 | §C-API-2 §C-2.1 | 🔥 | ⏳ |
| API-A-102-α | 既存アプリのうち SSR モノリス構成（Next.js full-stack / Rails / Spring Boot 等）の割合 | §C-API-2, §FR-API-6 | 🔥 | ⏳ |
| API-A-112 ⭐ | **Partner B2B API（外部企業からの M2M 呼び出し）連携の現状** — 該当アプリの有無、Partner 数 | §FR-API-1 §1.1, §FR-API-2 §2.2 | 🔥 | ⏳ |
| API-A-113 ⭐ | **Partner B2B API の新規想定** — 将来 1〜3 年で M2M 連携要件が発生する可能性 | §FR-API-1 §1.1, §FR-API-2 §2.2 | 🔥 | ⏳ |
| API-A-115 ⭐ | **非 AWS Internal 呼び出し元の現状棚卸し**（GitHub Actions / SaaS / on-prem / レガシーの内訳）| §FR-API-2 §2.3.A | 🔥 | ⏳ |

---

## Phase B: 技術要件

### B-0: アーキパターン選定（§C-API-2 §C-2.1）

| ID | 質問 | 関連 FR/NFR | 優先度 | 状態 |
|---|---|---|:---:|:---:|
| API-B-001 | 本標準で 3 アーキパターン（SPA+API / SSR+API / SSR モノリス）**すべてサポート対象**にするか | §C-API-2 §C-2.1 | 🔥 | ⏳ |
| API-B-001-α | SSR モノリスの **将来マイクロ化リスク**（モバイル要件等で API 切り出し）への扱い方針 | §C-API-2 §C-2.3, §NFR-API-9 | 🟡 | ⏳ |
| API-B-001-β | SSR モノリスの **規模上限**（同時タスク数 / TPS）の目安設定 | §C-API-2 §C-2.1, §NFR-API-3 | 🟡 | ⏳ |
| API-B-002 | SSR モノリスでの **認証は ALB + Cognito 標準化** で良いか | §FR-API-2 §2.A, §FR-API-6 | 🔥 | ⏳ |
| API-B-003 | SSR モノリスでの **流量制御は WAF rate-based + アプリ内 throttling** で良いか | §FR-API-3 §3.A | 🟡 | ⏳ |
| API-B-004 | SSR モノリスでの **per-tenant 課金按分**の要件（EMF カスタム次元 / CUR タグ集計） | §FR-API-4 §4.A | 🟡 | ⏳ |
| API-B-005 | SSR モノリスの **観測性スタック**標準化（OpenTelemetry SDK + ADOT Collector サイドカー） | §FR-API-8 §8.A | 🟡 | ⏳ |

### B-1: 公開範囲（§FR-API-1）

| ID | 質問 | 関連 FR/NFR | 優先度 | 状態 |
|---|---|---|:---:|:---:|
| API-B-101 | 「Internal だが将来 Public 化可能性あり」の API は初期から Public 構成か Internal で組むか | §FR-API-1 §1.1 | 🟡 | ⏳ |
| API-B-102 | 「IP allowlist のみで Public」を許容するか（本標準は Partner 区分推奨） | §FR-API-1 §1.1 | 🟡 | ⏳ |
| API-B-103 ⭐ | **未認証アクセスが必須のエンドポイント棚卸し**（ランディング / マーケ / 公開データ API のリスト）| §FR-API-1 §1.1, §FR-API-2 §2.B | 🔥 | ⏳ |
| API-B-104 | HTTP API / REST API のデフォルト選定方針 | §FR-API-1 §1.2 / §FR-API-5 §5.1 | 🔥 | ⏳ |
| API-B-105 | CloudFront を全 Public API で必須化するか | §FR-API-1 §1.2 | 🔥 | ⏳ |
| API-B-106 | VPC Lattice の採用範囲（クロスアカウント Internal で標準化するか） | §FR-API-1, §FR-API-6 | 🟡 | ⏳ |
| API-B-107 ⭐ | **サインイン / サインアップ UI をアプリで持つ標準アプリの有無**（認証側方針と連動、原則 Hosted UI 委譲）| §FR-API-1 §1.1, §FR-API-2 §2.B, §C-API-3 | 🔥 | ⏳ |
| API-B-108 | サインアップフローの所在（IdP 連携 JIT / 認証基盤 Hosted / アプリ実装）| §FR-API-2 §2.B, §C-API-3 | 🟡 | ⏳ |

### B-2: 認証認可（§FR-API-2）

| ID | 質問 | 関連 FR/NFR | 優先度 | 状態 |
|---|---|---|:---:|:---:|
| API-B-201 | API 認証に Access Token / ID Token のどちらを使うか | §FR-API-2 §2.1 / §C-API-3 | 🔥 | ⏳ |
| API-B-202 | 必須検証するクレームリスト（iss, aud, exp + α）| §FR-API-2 §2.1 / §C-API-3 | 🔥 | ⏳ |
| API-B-203 | 共有認証基盤の JWKS が Private のとき、本標準側でどう取得するか | §FR-API-2 §2.1 / §C-API-3 | 🔥 | ⏳ |
| API-B-211 ⭐ | **【A-112/A-113 で Partner B2B M2M 要件確認後】** Partner 新規デフォルト認証は OAuth Client Credentials で確定するか、API Key 互換性も標準に残すか | §FR-API-2 §2.2 | 🔥 | ⏳ |
| API-B-212 | API Key の有効期限・ローテーションポリシー（Legacy/Trial 用途）| §FR-API-2 §2.2 / §NFR-API-4 §4.2 | 🟡 | ⏳ |
| API-B-214 | Partner identity 識別単位（Per-Org / Per-App / Per-App×Env、業界標準は後者）| §FR-API-2 §2.2, §C-API-3 | 🟡 | ⏳ |
| API-B-215 | Partner Scope / Permission の細粒度（OAuth scope のみ / Verified Permissions 併用）| §FR-API-2 §2.2, §FR-API-2 §2.4 | 🟡 | ⏳ |
| API-B-216 | Partner クレデンシャルのローテーション周期 + Overlap period（24-72h 標準）| §FR-API-2 §2.2 / §NFR-API-4 | 🟡 | ⏳ |
| API-B-217 | Partner オンボーディングフロー（自社ポータル / AWS Marketplace / 個別契約）| §FR-API-2 §2.2 | 🟡 | ⏳ |
| API-B-218 | Partner-tier の差別化（Bronze / Silver / Gold）を持つか | §FR-API-2 §2.2 | 🟢 | ⏳ |
| API-B-219 | 既存 Partner の認証方式と互換性維持の要否 | §FR-API-2 §2.2, §NFR-API-9 | 🟡 | ⏳ |
| API-B-220 | mTLS 採用時の証明書発行元（自社 PKI / AWS Private CA / Partner 側 CA、旧 API-B-213）| §FR-API-2 §2.2 | 🟡 | ⏳ |
| API-B-221 | 社内 Profile の標準は IAM auth か JWT か（混在許容） | §FR-API-2 §2.3 | 🟡 | ⏳ |
| API-B-222 | Cross-account IAM 信頼関係を Service Catalog で配布するか | §FR-API-2 §2.3 | 🟢 | ⏳ |
| API-B-225 ⭐ | **GitHub Actions / GitLab CI で OIDC Federation 必須化するか**（Access Key 直接埋め込み禁止）| §FR-API-2 §2.3.A | 🔥 | ⏳ |
| API-B-226 | on-prem 認証は **mTLS / OAuth Client Credentials どちらをデフォルト**にするか | §FR-API-2 §2.3.A | 🟡 | ⏳ |
| API-B-227 | Vendor SaaS（Datadog / Splunk 等）の **External ID 必須化** スコープ | §FR-API-2 §2.3.A | 🟡 | ⏳ |
| API-B-228 | **レガシー API Key 認証**の許容範囲・移行期限 | §FR-API-2 §2.3.A, §NFR-API-9 | 🟡 | ⏳ |
| API-B-241 | Lambda Authorizer の使用を例外承認制にするか | §FR-API-2 §2.4 | 🟡 | ⏳ |
| API-B-242 | Lambda Authorizer のキャッシュ TTL 標準値 | §FR-API-2 §2.4 / §C-API-3 | 🟢 | ⏳ |
| API-B-243 | AWS Verified Permissions（Cedar）の採用範囲 | §FR-API-2 §2.4 | 🟢 | ⏳ |
| API-B-244 ⭐ | **アプリ側認可は JWT クレーム単独 / JWT + アプリ DB / Policy Engine のどれをデフォルトとするか** | §FR-API-2 §2.5 | 🔥 | ⏳ |
| API-B-245 ⭐ | **ユーザプロビジョニング標準（JIT / SCIM / Invitation / Self-Service）の使い分け基準** | §FR-API-2 §2.5, §C-API-3 §C-3.4 | 🔥 | ⏳ |
| API-B-246 | 退職者の即時削除要件（SCIM 必須化 vs 次回ログイン無効化で OK）| §FR-API-2 §2.5, §C-API-3 §C-3.4 / §NFR-API-7 | 🟡 | ⏳ |
| API-B-247 | 認証基盤 roles → アプリ permissions のマッピング規約（標準テンプレ提供か、アプリ判断か）| §FR-API-2 §2.5 | 🟡 | ⏳ |
| API-B-248 | 初回ログイン時のプロフィール完成 UX 必須化スコープ | §FR-API-2 §2.5 | 🟢 | ⏳ |
| API-B-249 ⭐ | **社内限定 Profile での SG のみ運用** を例外承認制とするか、原則禁止とするか（Zero Trust）| §FR-API-2 §2.7, §NFR-API-4 §4.5 | 🔥 | ⏳ |
| API-B-250 | VPC Lattice Auth Policy を社内 Profile のデフォルトとするか | §FR-API-2 §2.7, §FR-API-6 §6.3 | 🟡 | ⏳ |
| API-B-251 ⭐ | **Authorizer 強制の IaC validation hook 種別**（cfn-guard / OPA / CDK Aspect）| §FR-API-2 §2.8, §C-API-5 §C-5.1 | 🔥 | ⏳ |

### B-3: 流量制御・課金（§FR-API-3, §FR-API-4）

| ID | 質問 | 関連 FR/NFR | 優先度 | 状態 |
|---|---|---|:---:|:---:|
| API-B-301 | 既定 throttle 値の妥当性確認 | §FR-API-3 §3.1 | 🟡 | ⏳ |
| API-B-302 | アカウントレベル throttle の予防的増枠申請要否 | §FR-API-3 §3.1 / §NFR-API-3 | 🟡 | ⏳ |
| API-B-303 | メソッド単位の標準化（GET / POST 別の標準値） | §FR-API-3 §3.1 | 🟢 | ⏳ |
| API-B-304 ⭐ | WAF ヘッダ集約で使用するヘッダ名標準（`x-tenant-id` / `Authorization` の JWT クレーム由来 等）| §FR-API-3 §3.1.2 / §3.4 | 🟡 | ⏳ |
| API-B-305 | 複合キー採用時の WCU 予算（30 WCU/key、Web ACL 上限 1,500）| §FR-API-3 §3.1.2 | 🟡 | ⏳ |
| API-B-306 ⭐ | **長期 quota（日次/月次）が必要な API の有無**（Usage Plan 採用判断）| §FR-API-3 §3.2 | 🔥 | ⏳ |
| API-B-307 | AWS Marketplace SaaS 経由の API 提供想定の有無 | §FR-API-3 §3.2, §FR-API-2 §2.2 | 🟡 | ⏳ |
| API-B-308 | Partner subscription tier（Free/Basic/Pro/Enterprise）の管理粒度 | §FR-API-3 §3.2 | 🟡 | ⏳ |
| API-B-343 | 長期 quota 必要な HTTP API は REST 移行 vs 自前実装のどちらをデフォルトとするか | §FR-API-3 §3.4.2 | 🟡 | ⏳ |
| API-B-311 | 商用 API への quota 全面適用 / 内部利用無制限 | §FR-API-3 §3.2 | 🟡 | ⏳ |
| API-B-312 | quota 超過時の課金モデル（追加 / ハードカット） | §FR-API-3 §3.2 / §NFR-API-8 | 🟡 | ⏳ |
| API-B-313 | 月初リセットのタイムゾーン | §FR-API-3 §3.2 | 🟢 | ⏳ |
| API-B-321 | 429 のアラート化しきい値 | §FR-API-3 §3.3 / §NFR-API-6 | 🟢 | ⏳ |
| API-B-322 | 429 を SLO 対象外とするか | §FR-API-3 §3.3 / §NFR-API-1 | 🟢 | ⏳ |
| API-B-341 | HTTP API でテナント単位 quota 要件あれば REST 移行 vs 自前実装 | §FR-API-3 §3.4 | 🟡 | ⏳ |
| API-B-342 | 自前実装の DynamoDB スキーマ・コスト試算 | §FR-API-3 §3.4 / §NFR-API-8 | 🟢 | ⏳ |
| API-B-401 | テナント識別子は API Key か JWT カスタムクレームか | §FR-API-4 §4.1 | 🔥 | ⏳ |
| API-B-402 | API Key のマスク方針（先頭 4 + 末尾 4 等） | §FR-API-4 §4.1 / §FR-API-8 | 🟡 | ⏳ |
| API-B-411 | 処理時間 × 利用者の按分要件 / Request 数のみで十分か | §FR-API-4 §4.2 | 🟡 | ⏳ |
| API-B-412 | EMF カスタムメトリクスの次元数・カーディナリティ上限 | §FR-API-4 §4.2 / §NFR-API-8 | 🟢 | ⏳ |
| API-B-431 | Tag enforcement 手段（Config Rule + SCP / IaC validation） | §FR-API-4 §4.3 / §FR-API-7 | 🟡 | ⏳ |
| API-B-432 | 既存リソースへの必須タグ遡及付与スコープ | §FR-API-4 §4.3 / §NFR-API-9 | 🟡 | ⏳ |

### B-4: Serverless 標準（§FR-API-5）

| ID | 質問 | 関連 FR/NFR | 優先度 | 状態 |
|---|---|---|:---:|:---:|
| API-B-501 | HTTP API / REST API のデフォルト固定 | §FR-API-5 §5.1 | 🔥 | ⏳ |
| API-B-502 | Edge-optimized vs Regional + CloudFront 前段の既定 | §FR-API-5 §5.1 | 🟡 | ⏳ |
| API-B-511 | Lambda ランタイムの社内推奨優先順位 | §FR-API-5 §5.2 | 🟡 | ⏳ |
| API-B-512 | arm64 (Graviton) を新規デフォルト化するか | §FR-API-5 §5.2 / §NFR-API-8 | 🟡 | ⏳ |
| API-B-513 | Lambda extension 標準セットを Service Catalog 配布するか | §FR-API-5 §5.2 | 🟢 | ⏳ |
| API-B-521 | 新規アプリのデフォルト DB（DynamoDB / Aurora Serverless v2） | §FR-API-5 §5.3 | 🟡 | ⏳ |
| API-B-522 | RDS Proxy 採用基準 | §FR-API-5 §5.3 | 🟢 | ⏳ |
| API-B-541 | クロスアカウント EventBridge の標準化 | §FR-API-5 §5.4 | 🟢 | ⏳ |
| API-B-542 | メッセージスキーマのバージョニング方針 | §FR-API-5 §5.4 / §NFR-API-9 | 🟢 | ⏳ |
| API-B-551 | AppSync を選択肢に入れるか例外承認制か | §FR-API-5 §5.5 | 🟢 | ⏳ |
| API-B-552 | Function URL の使用範囲を Webhook と内部用途に限定するか | §FR-API-5 §5.5 | 🟢 | ⏳ |

### B-5: Container（ECS）標準（§FR-API-6）

| ID | 質問 | 関連 FR/NFR | 優先度 | 状態 |
|---|---|---|:---:|:---:|
| API-B-601 | 既存 EC2 採用アプリの Fargate 移行可否評価 | §FR-API-6 §6.1 / §NFR-API-9 | 🟡 | ⏳ |
| API-B-602 | Spot タスクの採用範囲 | §FR-API-6 §6.1 / §NFR-API-8 | 🟢 | ⏳ |
| API-B-621 | 共有 ALB の運用単位（プロジェクト / アカウント） | §FR-API-6 §6.2 / §NFR-API-8 | 🟡 | ⏳ |
| API-B-622 | ALB 認証統合（Cognito / OIDC）を標準扱いするか | §FR-API-6 §6.2 / §FR-API-2 | 🟡 | ⏳ |
| API-B-623 ⭐ | **ECS バックエンドの前段に ALB only / API GW + ALB のどちらをデフォルトとするか**（Pattern X / Pattern Y）| §FR-API-6 §6.2.A, §C-API-2 §C-2.1.5 | 🔥 | ⏳ |
| API-B-624 | Partner B2B が要件化された ECS バックエンドは API GW REST 必須化するか | §FR-API-6 §6.2.A, §FR-API-2 §2.2 | 🟡 | ⏳ |
| API-B-631 | Cloud Map / 自前 Consul 等からの Service Connect / Lattice 移行ロードマップ | §FR-API-6 §6.3 | 🟡 | ⏳ |
| API-B-632 | Service Connect / Lattice の mTLS 設定を標準化するか | §FR-API-6 §6.3 / §NFR-API-4 | 🟢 | ⏳ |
| API-B-641 | Task Role の粒度標準化 | §FR-API-6 §6.4 | 🟡 | ⏳ |
| API-B-642 | Execution Role の共通テンプレ Service Catalog 配布 | §FR-API-6 §6.4 | 🟢 | ⏳ |
| API-B-651 | 本番デプロイは Blue/Green 標準化か Rolling 可 | §FR-API-6 §6.5 / §NFR-API-6 | 🟡 | ⏳ |
| API-B-652 | ECS AZ spread strategy のデフォルト | §FR-API-6 §6.5 / §NFR-API-1 | 🟢 | ⏳ |

---

## Phase C: 運用・セキュリティ・コンプラ・コスト

### C-1: 観測性（§FR-API-8）

| ID | 質問 | 関連 FR/NFR | 優先度 | 状態 |
|---|---|---|:---:|:---:|
| API-C-811 | Log Group Retention の業務カテゴリ別マッピング | §FR-API-8 §8.1 / §NFR-API-7 | 🟡 | ⏳ |
| API-C-812 | Data Protection Policy の追加カスタムパターン | §FR-API-8 §8.1 / §NFR-API-4 | 🟢 | ⏳ |
| API-C-813 | 高ボリューム API のサンプリング率 | §FR-API-8 §8.1 / §NFR-API-8 | 🟢 | ⏳ |
| API-C-814 ⭐ | 認証検証 Athena クエリ（A 未認証通過 / B Authorization なし / C 認証失敗率）の **実行頻度・通知先** | §FR-API-8 §8.1.2 / §FR-API-2 §2.8 | 🔥 | ⏳ |
| API-C-815 | access log の `profile` / `authMethod` / `tenantId` フィールド **追加可否**（Stage Variables / Mapping Template）| §FR-API-8 §8.1.2 | 🟡 | ⏳ |
| API-C-821 | 新規プロジェクト ADOT 採用必須化 | §FR-API-8 §8.2 | 🟡 | ⏳ |
| API-C-822 | 既存 X-Ray SDK プロジェクトの ADOT 移行スケジュール | §FR-API-8 §8.2 / §NFR-API-9 | 🟡 | ⏳ |
| API-C-823 | サンプリング率の業務別デフォルト | §FR-API-8 §8.2 | 🟢 | ⏳ |
| API-C-831 | SLO デフォルトテンプレ（可用性 / レイテンシ） | §FR-API-8 §8.3 / §NFR-API-1 | 🟡 | ⏳ |
| API-C-832 | アラート通知先・エスカレーション | §FR-API-8 §8.3 / §NFR-API-6 | 🟡 | ⏳ |
| API-C-833 | Synthetics の必須化範囲 | §FR-API-8 §8.3 | 🟢 | ⏳ |

### C-2: 可用性・性能・拡張性（§NFR-API-1〜3）

| ID | 質問 | 関連 FR/NFR | 優先度 | 状態 |
|---|---|---|:---:|:---:|
| API-C-901 | 新規 API のデフォルト Tier を Standard とするか | §NFR-API-1 §1.1 | 🟡 | ⏳ |
| API-C-902 | Critical API のマネージド SLA 達成構成 | §NFR-API-1 §1.1 / §NFR-API-5 | 🟡 | ⏳ |
| API-C-911 | 3 AZ を新規アカウント既定とするか | §NFR-API-1 §1.2 | 🟢 | ⏳ |
| API-C-921 | タイムアウト階層の業務別標準値 | §NFR-API-1 §1.3 | 🟢 | ⏳ |
| API-C-922 | Circuit Breaker の実装手段標準化 | §NFR-API-1 §1.3 | 🟢 | ⏳ |
| API-C-1001 | 既存アプリの実測ベースライン取得可否 | §NFR-API-2 §2.1 | 🟡 | ⏳ |
| API-C-1002 | Tier の割当方針 | §NFR-API-2 §2.1 | 🟡 | ⏳ |
| API-C-1011 | Real-time Tier API に Provisioned Concurrency 既定設定 | §NFR-API-2 §2.2 / §NFR-API-8 | 🟡 | ⏳ |
| API-C-1012 | ECS Fargate task の既定 desired count | §NFR-API-2 §2.2 / §NFR-API-1 | 🟢 | ⏳ |
| API-C-1021 | 負荷テストの本番リリース前必須化範囲 | §NFR-API-2 §2.3 | 🟡 | ⏳ |
| API-C-1022 | 性能リグレッション検知の CI 統合 | §NFR-API-2 §2.3 | 🟢 | ⏳ |
| API-C-1101 | 既存アプリの実測ピーク取得 | §NFR-API-3 §3.1 | 🟡 | ⏳ |
| API-C-1102 | 季節変動・キャンペーン時のピーク係数妥当性 | §NFR-API-3 §3.1 | 🟡 | ⏳ |
| API-C-1111 | DynamoDB on-demand vs provisioned 選定基準 | §NFR-API-3 §3.2 / §NFR-API-8 | 🟡 | ⏳ |
| API-C-1112 | ECS scale-out 余裕（cooldown / step） | §NFR-API-3 §3.2 | 🟢 | ⏳ |
| API-C-1121 | 本番アカウントの必須増枠リストを Service Catalog で初期化 | §NFR-API-3 §3.3 | 🟡 | ⏳ |
| API-C-1122 | クォータ監視のアラート通知先 | §NFR-API-3 §3.3 / §NFR-API-6 | 🟢 | ⏳ |

### C-3: セキュリティ（§NFR-API-4）

| ID | 質問 | 関連 FR/NFR | 優先度 | 状態 |
|---|---|---|:---:|:---:|
| API-C-1201 | TLS 1.3 の必須化（旧クライアント互換性） | §NFR-API-4 §4.1 | 🟡 | ⏳ |
| API-C-1202 | 内部 service 間の mTLS を必須化するか | §NFR-API-4 §4.1 / §FR-API-6 | 🟡 | ⏳ |
| API-C-1211 | CMK の粒度（アプリ / 環境 / リソース種別） | §NFR-API-4 §4.2 | 🟡 | ⏳ |
| API-C-1212 | シークレットローテーション未対応 DB の段階移行 | §NFR-API-4 §4.2 / §NFR-API-9 | 🟡 | ⏳ |
| API-C-1231 | Security Hub の準拠標準（CIS / FSBP / PCI DSS） | §NFR-API-4 §4.4 / §NFR-API-7 | 🟡 | ⏳ |
| API-C-1232 | Inspector のスコープ（全 Lambda / 重要のみ） | §NFR-API-4 §4.4 | 🟢 | ⏳ |
| API-C-2001 | JWKS キャッシュ TTL 標準値（マネージド既定で十分か） | §C-API-3 §C-3.3 | 🟢 | ⏳ |
| API-C-2002 | 認証基盤側障害時の API 縮退挙動（401 / 503） | §C-API-3 §C-3.3 / §NFR-API-1 | 🟡 | ⏳ |
| API-C-2121 | VPC Flow Logs の集約必須化範囲 | §C-API-4 §C-4.3 | 🟡 | ⏳ |

### C-4: 運用（§NFR-API-6）

| ID | 質問 | 関連 FR/NFR | 優先度 | 状態 |
|---|---|---|:---:|:---:|
| API-C-1401 | ダッシュボード作成必須化範囲 | §NFR-API-6 §6.1 | 🟡 | ⏳ |
| API-C-1402 | 通知先プラットフォーム（PagerDuty / Slack） | §NFR-API-6 §6.1 | 🟡 | ⏳ |
| API-C-1411 | Critical Tier の段階デプロイ手段必須化 | §NFR-API-6 §6.2 | 🟡 | ⏳ |
| API-C-1412 | コンテナベースイメージの再ビルド頻度 | §NFR-API-6 §6.2 | 🟢 | ⏳ |
| API-C-1421 | ステータスページの採用範囲 | §NFR-API-6 §6.3 | 🟢 | ⏳ |
| API-C-1422 | ポストモーテム公開範囲 | §NFR-API-6 §6.3 | 🟢 | ⏳ |

### C-5: コスト（§NFR-API-8）

| ID | 質問 | 関連 FR/NFR | 優先度 | 状態 |
|---|---|---|:---:|:---:|
| API-C-1611 | 予算の既定アラート閾値（50/80/100/120%） | §NFR-API-8 §8.2 | 🟡 | ⏳ |
| API-C-1612 | 異常検知の通知先 | §NFR-API-8 §8.2 / §NFR-API-6 | 🟢 | ⏳ |

### C-6: 互換性・移行性（§NFR-API-9）

| ID | 質問 | 関連 FR/NFR | 優先度 | 状態 |
|---|---|---|:---:|:---:|
| API-C-1701 | バージョニング方式（URL path 推奨）確定 | §NFR-API-9 §9.1 | 🟡 | ⏳ |
| API-C-1702 | OpenAPI 公開の必須化範囲 | §NFR-API-9 §9.1 / §C-API-5 | 🟡 | ⏳ |
| API-C-2211 | CDK vs Terraform の社内推奨確定 | §C-API-5 §C-5.2 | 🟡 | ⏳ |
| API-C-2212 | 既存 CFn 資産アプリへの対応 | §C-API-5 §C-5.2 / §NFR-API-9 | 🟡 | ⏳ |
| API-C-2221 | 旧バージョン製品の併存期間 | §C-API-5 §C-5.3 / §NFR-API-9 | 🟡 | ⏳ |
| API-C-2222 | アプリ側のアップデート義務 | §C-API-5 §C-5.3 | 🟢 | ⏳ |

---

## Phase D: 最終判断

> 対象: 経営層 + SecOps + Platform リーダー

### D-1: 公開範囲・区分管理（§FR-API-1）

| ID | 質問 | 関連 | 優先度 | 状態 |
|---|---|---|:---:|:---:|
| API-D-101 | 公開範囲昇格の承認権限者（SecOps / アーキ委員会 / オーナー） | §FR-API-1 §1.3 | 🔥 | ⏳ |
| API-D-102 | 昇格申請のリードタイム目標 | §FR-API-1 §1.3 | 🟡 | ⏳ |
| API-D-103 | 緊急昇格のエスケープハッチ許容 | §FR-API-1 §1.3 | 🟡 | ⏳ |
| API-D-241 | FAPI 2.0 など規制業界準拠の Partner 要件 | §FR-API-2 §2.2 / §NFR-API-7 | 🟡 | ⏳ |
| API-D-245 | AWS Verified Permissions / Cedar を本標準のデフォルトに含めるか（escalation 扱い vs 標準採用）| §FR-API-2 §2.5, §FR-API-2 §2.6 | 🟡 | ⏳ |
| API-D-1402-α | HRD（Home Realm Discovery）ページの所在（認証基盤 / アプリ）| §FR-API-2 §2.B, §C-API-3 | 🟡 | ⏳ |

### D-2: タグ・課金按分（§FR-API-4）

| ID | 質問 | 関連 | 優先度 | 状態 |
|---|---|---|:---:|:---:|
| API-D-401 | 必須タグの最終確定（特に CostCenter 粒度） | §FR-API-4 §4.3 | 🔥 | ⏳ |
| API-D-411 | 按分の最小粒度（テナント / 部門 / アプリ） | §FR-API-4 §4.4 | 🔥 | ⏳ |
| API-D-412 | 共有リソース按分ルール | §FR-API-4 §4.4 | 🟡 | ⏳ |
| API-D-413 | 内部請求のサイクルと確定タイミング | §FR-API-4 §4.4 | 🟡 | ⏳ |

### D-3: ガードレール（§FR-API-7）

| ID | 質問 | 関連 | 優先度 | 状態 |
|---|---|---|:---:|:---:|
| API-D-701 | Bot Control の対象（全 Public / 重要 URI のみ） | §FR-API-7 §7.1 / §NFR-API-4 | 🔥 | ⏳ |
| API-D-702 | WAF Managed Rules の段階投入計画 | §FR-API-7 §7.1 | 🟡 | ⏳ |
| API-D-703 | AWS Shield Advanced の採用範囲 | §FR-API-7 §7.1 / §NFR-API-8 | 🟡 | ⏳ |
| API-D-704 | Route53 Resolver DNS Firewall の既定 Domain List | §FR-API-7 §7.1 | 🟢 | ⏳ |
| API-D-721 | SCP / Config Rules の既定セット（LZA / 自前） | §FR-API-7 §7.2 | 🔥 | ⏳ |
| API-D-722 | Config Rule の自動修復採用範囲 | §FR-API-7 §7.2 | 🟡 | ⏳ |
| API-D-723 ⭐ | Authorizer 必須化 Config Rule の **自動修復**（API method を deny に変更）を採用するか | §FR-API-7 §7.2.2 / §FR-API-2 §2.8 | 🔥 | ⏳ |
| API-D-724 ⭐ | 認証なし API 例外台帳と Config Rule の **照合自動化**（ServiceNow / DynamoDB 等のデータソース）| §FR-API-7 §7.2.2 / §FR-API-2 §2.8.3 | 🟡 | ⏳ |
| API-D-741 | 例外申請のリードタイム | §FR-API-7 §7.4 | 🟡 | ⏳ |
| API-D-742 | 例外台帳の保管場所 | §FR-API-7 §7.4 | 🟢 | ⏳ |

### D-4: 監査ログ（§FR-API-8）

| ID | 質問 | 関連 | 優先度 | 状態 |
|---|---|---|:---:|:---:|
| API-D-841 | Data Events の対象範囲（重要 S3 / Lambda） | §FR-API-8 §8.4 / §NFR-API-7 / §NFR-API-8 | 🟡 | ⏳ |
| API-D-842 | 監査ログ保管期間（7 年で十分か） | §FR-API-8 §8.4 / §NFR-API-7 | 🟡 | ⏳ |

### D-5: セキュリティ（§NFR-API-4）

| ID | 質問 | 関連 | 優先度 | 状態 |
|---|---|---|:---:|:---:|
| API-D-1221 | Bot Control の対象 URI スコープ確定 | §NFR-API-4 §4.3 / §FR-API-7 | 🔥 | ⏳ |
| API-D-1222 | Shield Advanced 採用範囲確定 | §NFR-API-4 §4.3 | 🟡 | ⏳ |
| API-D-1241 | 死守事項マトリクスの粒度妥当性 | §NFR-API-4 §4.5 | 🟡 | ⏳ |
| API-D-1242 ⭐ | **社内 / 社内限定 Profile の「Network のみ」許容例外**の承認プロセス | §NFR-API-4 §4.5, §FR-API-2 §2.7 / §2.8 | 🔥 | ⏳ |
| API-D-1243 | **ヘルスチェックエンドポイントの認証要否**（path 別 / 専用 path / IP 制限）の標準 | §NFR-API-4 §4.5 | 🟡 | ⏳ |

### D-6: DR（§NFR-API-5）

| ID | 質問 | 関連 | 優先度 | 状態 |
|---|---|---|:---:|:---:|
| API-D-1301 | 新規 API のデフォルト Tier | §NFR-API-5 §5.1 | 🔥 | ⏳ |
| API-D-1302 | Critical Tier の対象 API リスト確定 | §NFR-API-5 §5.1 | 🔥 | ⏳ |
| API-D-1311 | Critical Tier の対象リージョン | §NFR-API-5 §5.2 | 🟡 | ⏳ |
| API-D-1312 | Active-Standby のコスト試算 | §NFR-API-5 §5.2 / §NFR-API-8 | 🟡 | ⏳ |
| API-D-1321 | 切替訓練の必須化スコープ | §NFR-API-5 §5.3 | 🟡 | ⏳ |
| API-D-1322 | Resilience Hub の採用範囲 | §NFR-API-5 §5.3 | 🟢 | ⏳ |

### D-7: 運用体制（§NFR-API-6）

| ID | 質問 | 関連 | 優先度 | 状態 |
|---|---|---|:---:|:---:|
| API-D-1431 | 体制の既存組織への適用方法 | §NFR-API-6 §6.4 | 🔥 | ⏳ |
| API-D-1432 | AWS サポート契約のアカウント別レベル | §NFR-API-6 §6.4 | 🟡 | ⏳ |

### D-8: コンプラ・規制（§NFR-API-7）

| ID | 質問 | 関連 | 優先度 | 状態 |
|---|---|---|:---:|:---:|
| API-D-1501 | 適用される規制リスト確定 | §NFR-API-7 §7.1 | 🔥 | ⏳ |
| API-D-1502 | 業界規制対応アプリの本標準への含め方 | §NFR-API-7 §7.1 / §NFR-API-9 | 🔥 | ⏳ |
| API-D-1511 | 必要な認定リスト | §NFR-API-7 §7.2 | 🟡 | ⏳ |
| API-D-1512 | Audit Manager の採用範囲 | §NFR-API-7 §7.2 | 🟢 | ⏳ |
| API-D-1521 | PII の業務別保持期間 | §NFR-API-7 §7.3 | 🟡 | ⏳ |
| API-D-1522 | 開発環境のデータマスキング手段 | §NFR-API-7 §7.3 | 🟢 | ⏳ |
| API-D-1531 | グローバル展開時のデータ所在地ポリシー | §NFR-API-7 §7.4 / §NFR-API-5 | 🟡 | ⏳ |

### D-9: コスト最適化（§NFR-API-8）

| ID | 質問 | 関連 | 優先度 | 状態 |
|---|---|---|:---:|:---:|
| API-D-1601 | コストダッシュボードの必須化対象 | §NFR-API-8 §8.1 | 🟡 | ⏳ |
| API-D-1602 | コスト指標の目標値（USD/1M req） | §NFR-API-8 §8.1 | 🟢 | ⏳ |
| API-D-1621 | Savings Plan のコミット率 | §NFR-API-8 §8.3 | 🟡 | ⏳ |
| API-D-1622 | arm64 移行の既存アプリ計画 | §NFR-API-8 §8.3 / §NFR-API-9 | 🟡 | ⏳ |

### D-10: バージョニング・移行（§NFR-API-9）

| ID | 質問 | 関連 | 優先度 | 状態 |
|---|---|---|:---:|:---:|
| API-D-1711 | Deprecation 期間の業務別調整ルール | §NFR-API-9 §9.2 | 🟡 | ⏳ |
| API-D-1712 | 同時稼働 2 バージョン上限の妥当性 | §NFR-API-9 §9.2 | 🟡 | ⏳ |
| API-D-1721 | 既存 Critical アプリの移行期限確定 | §NFR-API-9 §9.3 | 🔥 | ⏳ |
| API-D-1722 | 移行支援体制（Platform / 各アプリ自前） | §NFR-API-9 §9.3 | 🔥 | ⏳ |

### D-11: アカウント体系・選定基準（§C-API-1, §C-API-2）

| ID | 質問 | 関連 | 優先度 | 状態 |
|---|---|---|:---:|:---:|
| API-D-1801 | 既存アカウント体系の再編要否 | §C-API-1 §C-1.4 | 🔥 | ⏳ |
| API-D-1802 | Workload OU の環境分離（アカウント分離 vs 同一） | §C-API-1 §C-1.4 | 🟡 | ⏳ |
| API-D-1901 | 選定基準の重みづけ妥当性 | §C-API-2 §C-2.1 | 🟡 | ⏳ |
| API-D-1902 | 評価軸の数値化（スコアシート）運用 | §C-API-2 §C-2.1 | 🟢 | ⏳ |
| API-D-1911 | 選定決定木の質問項目妥当性 | §C-API-2 §C-2.2 | 🟡 | ⏳ |
| API-D-1912 | 「Cold start NG」の判定基準 | §C-API-2 §C-2.2 / §NFR-API-2 | 🟡 | ⏳ |
| API-D-1921 | マイクロサービス境界のガイドライン | §C-API-2 §C-2.3 | 🟢 | ⏳ |
| API-D-1931 | EKS の本標準への含め方 | §C-API-2 §C-2.4 | 🟡 | ⏳ |

### D-12: 監査ガバナンス（§C-API-4）

| ID | 質問 | 関連 | 優先度 | 状態 |
|---|---|---|:---:|:---:|
| API-D-2101 | SecOps と Platform の境界確定 | §C-API-4 §C-4.1 | 🔥 | ⏳ |
| API-D-2102 | アプリチームによる WAF 独自ルール追加の権限範囲 | §C-API-4 §C-4.1 / §FR-API-7 | 🟡 | ⏳ |
| API-D-2111 | 配信変更通知期間の業務影響別調整 | §C-API-4 §C-4.2 | 🟡 | ⏳ |
| API-D-2112 | 変更通知の配信先 | §C-API-4 §C-4.2 / §NFR-API-6 | 🟢 | ⏳ |
| API-D-2122 | Object Lock のモード（Compliance / Governance） | §C-API-4 §C-4.3 / §NFR-API-7 | 🟡 | ⏳ |
| API-D-2131 | 2 名承認の対象操作リスト | §C-API-4 §C-4.4 | 🟡 | ⏳ |
| API-D-2132 | Break Glass の承認・運用 | §C-API-4 §C-4.4 | 🟡 | ⏳ |

### D-13: Service Catalog（§C-API-5）

| ID | 質問 | 関連 | 優先度 | 状態 |
|---|---|---|:---:|:---:|
| API-D-2201 | 初期ラインナップ 8 種類で確定するか | §C-API-5 §C-5.1 | 🔥 | ⏳ |
| API-D-2202 | 各製品の対応リージョン | §C-API-5 §C-5.1 / §NFR-API-5 | 🟡 | ⏳ |
| API-D-2241 | 開発者ポータルの構築範囲 | §C-API-5 §C-5.4 | 🟡 | ⏳ |

---

## サマリー

### Phase 別件数（暫定）

| Phase | 件数 | うち 🔥 最優先 |
|---|---:|---:|
| Phase A | 12 | 6 |
| Phase B | 48 | 10 |
| Phase C | 37 | 0 |
| Phase D | 47 | 14 |
| **合計** | **144** | **30** |

### Stage 1（最優先 25 項目）を先行確認することで、本標準の中核判断（公開範囲の判定 / プラットフォーム選定の方針 / 監査アカウント役割 / ガードレールの範囲）が早期確定できる。

---

## 関連ドキュメント

- [hearing-script/](hearing-script/README.md) — 顧客送付用敬体スクリプト
- [requirements-document-structure.md](requirements-document-structure.md) — SSOT
- [proposal/](proposal/00-index.md) — 要件提示版
