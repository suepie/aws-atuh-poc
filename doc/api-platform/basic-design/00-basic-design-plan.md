# API プラットフォーム 基本設計 計画書

作成日: 2026-07-06
ステータス: Draft（ガイドライン章先行、実装物は後続 Phase）

## 0. 背景・なぜここで決めるか

API プラットフォーム標準の要件定義（`proposal/` 配下: §FR-API-1〜8 / §NFR-API-1〜9 / §C-API-1〜6）は骨格完成。ADR-039（ネットワーク監査アカウント）/ ADR-059（中央認証チェック）で主要な実装方針も確定した。本フェーズでは要件・ADR を **アプリチームが従うガイドライン** と **動く実装物** に落とす。

**⚠ スコープ確定（2026-07-06 ユーザー指示）**: 本基本設計は当初の全 8 領域網羅ではなく、以下 **2 領域に絞る**:

1. **クラウド観点ガイドライン類**（アプリチーム向け）
   - API GW / CloudFront による流量・課金制御ルール
   - 静的解析・テストプロセス等アプリ側セキュリティの工夫
2. **Swagger（OpenAPI）駆動の認証外形監視の実装**
   - サンプルプログラム・汎用モジュール・テスト

**proposal/ の位置付け**: 要件定義 SSOT として維持（参照物）。本基本設計は proposal を参照しつつ、実装ガイド + 実装物に具体化する。

## 1. 前提（proposal / ADR から凍結）

本基本設計は以下を前提とする。変更時は該当 ADR / proposal を先に改訂する。

| # | 前提 | 出典 | 備考 |
|---|------|------|------|
| BD-P-01 | ネットワーク監査アカウントにアプリごと独立 CloudFront + WAF、5 アカウント体系 | ADR-039 v2 | ⚠ ROSA 側基本設計 P-18 で「他組織管理の監査アカウント」に責任分界改訂の可能性あり。API プラットフォーム側は自管理前提で記述し、差分は §16 で吸収 |
| BD-P-02 | Origin Protection = Custom Header + CloudFront IP allowlist（Pattern A）、Secret 30 日ローテ | ADR-039 §C-4 | Public API GW / Public ALB |
| BD-P-03 | 認証実装漏れ検知 = 中央認証チェック（Pattern β、ネットワーク監査アカウント集約）| ADR-059 | App Registry + OpenAPI Registry で全アプリ自動追随 |
| BD-P-04 | 認証方式 = 7 パターン（P-1〜P-7）+ 5 大分類、Tier 表現廃止 | §C-API-6 §C-6.2.5 | OAuth トークン / 証明書 / 共有秘密キー / AWS IAM 署名 |
| BD-P-05 | 検知 5 レイヤー（IaC / Config / Static Code / Runtime Log / Behavioral）で 95-99% 担保 | §C-API-6 §C-6.6 | 本基本設計は L1/L3（静的解析）と L5（外形監視）を実装対象化 |
| BD-P-06 | 認証チェックの実行基盤 = **Lambda（Node.js 22 / AWS SDK v3）**。Synthetics（`syn-nodejs-puppeteer-16.1` 等）は将来オプション（18 章 §18.4） | 2026-07-06 確認 / 18 章 | 現行は Lambda。Synthetics 系ランタイム値は将来用に確認済み（旧 `-7.0` は Deprecated）|
| BD-P-07 | 課金按分 = Cost Allocation Tag + Usage Plan API Key 経由の Partner 識別 | §FR-API-4 | Athena 集計 |
| BD-P-08 | Service Catalog 製品テンプレで死守事項（認証必須 / Origin Protection / タグ）を強制 | §C-API-5 | アプリチームは製品起動で自動準拠 |

## 2. 章立て（12 章 + index + plan）

### ① クラウドガイドライン類（アプリチーム向け）

| # | ファイル | 主題 | 主インプット | 担当 |
|---|---------|------|------------|------|
| 01 | `01-cloud-guidelines-overview.md` | ガイドライン総論・読み方・死守事項要約 | §C-API-1/5/6 | 骨格作成者 |
| 02 | `02-rate-limiting-quota-rules.md` | 流量制御ルール（WAF Rate-based / Usage Plan / method throttle / CloudFront）| §FR-API-3、ADR-052 | 検証エージェント |
| 03 | `03-billing-cost-allocation-rules.md` | 課金制御・按分ルール（Cost Tag / Budgets / Partner 按分 / Outbound SaaS）| §FR-API-4、§NFR-API-8 | 検証エージェント |
| 04 | `04-static-analysis-guidelines.md` | 静的解析（cfn-guard / cdk-nag / Semgrep）ガイド | §C-API-6 §C-6.6.4/.6 | 検証エージェント |
| 05 | `05-security.md` | セキュリティ 3 本柱（ネットワーク / 認証制御 / テストプロセス）| §C-API-6 §C-6.6.9 / 認証 06 章 / ADR-039/057 | 検証エージェント |
| 06 | `06-logging-monitoring.md` | ログ・監視（最低限 OBS-1〜4：アクセスログ / 相関 ID / マスク / 保持）横断関心事 | §FR-API-4 §4.2 / 05 章 / 認証基盤ログ | 検証エージェント |

### ② Swagger 駆動 認証外形監視の実装

| # | ファイル | 主題 | 主インプット | Phase |
|---|---------|------|------------|:---:|
| 10 | `10-external-monitoring-overview.md` | 外形監視 総論（ADR-059 要約 + 実装物ナビ）| ADR-059、§C-6.6.8 | 後続 |
| 11 | `11-central-probe-architecture.md` | 認証チェック 詳細設計（処理フロー / Hybrid 検証 / 4×4 真偽値表 / Positive トークン管理）| ADR-059、§C-6.6.8 | 後続 |
| 12 | `12-app-registry-design.md` | App Registry（DynamoDB）スキーマ・CRUD | ADR-059 | 後続 |
| 13 | `13-openapi-registry-design.md` | OpenAPI Registry（S3）構造・Export Custom Resource | ADR-059、§C-API-5 | 後続 |
| 14 | `14-probe-implementation-guide.md` | probe lib 実装ガイド + モノリス / Private 対応（Synthetics は将来オプション）| ADR-059 §D/§E | 後続 |
| 15 | `15-alert-routing-design.md` | 4×4 真偽値表 Alert Router 設計（P1/P2/P3 分岐）| §C-6.6.8 | 後続 |
| 16 | `16-cross-account-iam-design.md` | クロスアカウント登録 5 案比較 / StackSets 配布 | ADR-039/059 | 後続 |
| 17 | `17-deployment-integration-and-registration.md` | デプロイ検知と登録（Service Catalog / CI/CD / EventBridge の 3 層）| §C-API-5 / ADR-059 | 後続（質問対応で追加）|
| 18 | `18-scan-modes-and-scheduling.md` | スキャン実行モード（M1 差分/自動 + M3 フル/手動、Lambda 基盤一本化）— 実行モデル SSOT | ADR-059 | 後続（実行モデル見直しで追加）|

## 3. 実装物（code-samples/、認証基盤と分離）

**⚠ フォルダ分離（2026-07-06 ユーザー指示）**: 実装物は本リポジトリ内 `doc/api-platform/basic-design/code-samples/` に配置。認証基盤側（`keycloak/` 等）とは混在させない。

| ディレクトリ | 内容 | Phase |
|---|---|:---:|
| `code-samples/central-probe-lib/` | 中央認証チェック（probe lib）完全実装 + 単体テスト + README | 後続 |
| `code-samples/multi-checks-blueprint/` | Multi Checks JSON テンプレ + synthetics.json | 後続 |
| `code-samples/app-registry-lambda/` | App Registry CRUD Lambda | 後続 |
| `code-samples/openapi-export-lambda/` | OpenAPI Export Custom Resource Lambda | 後続 |
| `code-samples/alert-router-lambda/` | 4×4 分類 + SNS routing Lambda | 後続 |
| `code-samples/iac-guard-rules/` | cfn-guard / cdk-nag ルールセット | ガイドライン章と並行 |
| `code-samples/semgrep-rules/` | Semgrep ルール（言語別）| ガイドライン章と並行 |

## 4. Phase 分割

| Phase | 内容 | 状態 |
|---|---|:---:|
| **Phase 1** | 骨格（00-index / 00-plan / 01-overview）+ ガイドライン章 02-06 | 🚧 着手（2026-07-06）|
| Phase 2 | 外形監視設計章 10-18 | 未着手 |
| Phase 3 | 実装物（code-samples/）| 未着手 |
| Phase 4 | PoC 検証（ネットワーク監査アカウントモック + 1 App アカウント相当）| 未着手 |

## 5. 品質方針（ファクト検証の徹底）

**⚠ ユーザー指示（2026-07-06）**: 「必ず嘘がないことなど調べながら」。AWS 固有の仕様値（Usage Plan 上限・WAF Rate-based 仕様・CloudFront 制約・cfn-guard / Semgrep 構文・Synthetics Runtime）は **AWS 公式ドキュメント / 一次資料で裏取り**した上で記述する。各章は末尾に「検証済み事実」節を設け、確認した一次資料 URL を明示する。

## 6. 決定採番

- ガイドライン章の設計判断: **D-G-nn**
- 外形監視章の設計判断: **D-M-nn**
- 各章末尾に「未決事項」「他章への引き渡し」を記載

## 7. 未決事項（Phase 1 時点）

| ID | 内容 | 影響章 |
|---|---|---|
| BD-Q-01 | ROSA 側 P-18（監査アカウント他組織管理）が確定した場合の Origin Protection / probe の責任分界改訂 | 01/16 |
| BD-Q-02 | 流量制御の tier 別標準値（Bronze/Silver/Gold 廃止後の Partner 区分）| 02 |
| BD-Q-03 | ~~Cost Center / タグ体系の組織側標準との整合~~ → **kebab-case（`app-id`/`env`/`cost-center`/`owner`）で確定**（App Registry と一致、proposal PascalCase 例は正規化）。組織側標準名との最終突合のみ残 | 03（解決済み）|
| BD-Q-04 | 静的解析の言語別ルール整備優先順位（Python / Node / Java / Go）| 04 |
| BD-Q-05 | 外部 pen test のベンダー選定・予算 | 05 |
