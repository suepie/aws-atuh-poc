# API プラットフォーム 基本設計 ドキュメント目録

作成: 2026-07-06 / Phase 1（ガイドライン章）着手時点

## スコープ（2 領域に絞込み）

本基本設計は proposal（要件定義 SSOT）を **アプリチーム向けガイドライン** と **動く実装物** に落とす。対象は 2 領域:

1. **クラウド観点ガイドライン類**（章 01-06）: 全体像、流量・課金制御、静的解析、セキュリティ、ログ・監視
2. **Swagger 駆動 認証外形監視の実装**（章 10-18 + code-samples/）

proposal（§FR-API-* / §NFR-API-* / §C-API-*）は参照物として維持。

## 読み順

1. [00-basic-design-plan.md](00-basic-design-plan.md) — 計画書（スコープ / 前提 BD-P-01〜08 / 章立て / Phase 分割 / 品質方針）
2. [01-cloud-guidelines-overview.md](01-cloud-guidelines-overview.md) — ガイドライン総論（アプリチームが最初に読む）
3. 各ガイドライン章（02-06）→ 外形監視章（10-18）

## 主要な構成図・フロー（全体像を掴む）

| 見たいもの | 場所 |
|---|---|
| **API 制御 全体像**（実行時パス + ガバナンスパス）| [01 §1.0.0](01-cloud-guidelines-overview.md) |
| **ガイドライン構成図**（統制領域 5 本柱）| [01 §1.0.0](01-cloud-guidelines-overview.md) |
| ガイドライン章の読み順ナビ | [01 §1.1](01-cloud-guidelines-overview.md) |
| **認証実装確認処理 構成図**（Pattern β 骨格）| [10 §10.1.1](10-external-monitoring-overview.md) |
| **認証実装確認処理 統合構成図**（登録・トリガー・検査・通知）| [10 §10.1.3](10-external-monitoring-overview.md) |
| **認証実装確認処理 E2E フロー**（deploy→検知→通知→是正）| [10 §10.1.4](10-external-monitoring-overview.md) |
| **認証実装確認処理 リソース一覧**（何が・どこで・何をするか）| [10 §10.1.5](10-external-monitoring-overview.md) |
| **認証実装確認処理 AWS 構成図**（リソース単位・In/Out 境界アカウント込み・通信経路一覧）| [10 §10.1.6](10-external-monitoring-overview.md) |
| **詳細通信フロー**（git 連携 W1-9 / 検査 P1-6 / 発報 N1-6。アカウント×リソース×エンドポイント）| [10 §10.1.7](10-external-monitoring-overview.md) |
| 用語（probe とは何か 等）| [10 §10.0.4](10-external-monitoring-overview.md) |
| 認証実装確認処理 実行シーケンス（1 実行の中身）| [11 §11.1](11-central-probe-architecture.md) |
| 課金按分パイプライン概念図 | [03 §3.1.2](03-billing-cost-allocation-rules.md) |

## 設計書一覧

### ① クラウドガイドライン類（アプリチーム向け）

| # | ファイル | 主な内容 | 状態 |
|---|---------|---------|:---:|
| 01 | [01-cloud-guidelines-overview.md](01-cloud-guidelines-overview.md) | 総論・読み方・死守事項要約・責務分担 | ✅ Phase 1 |
| 02 | [02-rate-limiting-quota-rules.md](02-rate-limiting-quota-rules.md) | 流量制御ルール（WAF / Usage Plan / method throttle / CloudFront）| ✅ Phase 1 |
| 03 | [03-billing-cost-allocation-rules.md](03-billing-cost-allocation-rules.md) | 課金制御・按分ルール（Cost Tag / Budgets / Partner / Outbound）| ✅ Phase 1 |
| 04 | [04-static-analysis-guidelines.md](04-static-analysis-guidelines.md) | 静的解析（cfn-guard / cdk-nag / Semgrep）| ✅ Phase 1 |
| 05 | [05-security.md](05-security.md) | セキュリティ 3 本柱（ネットワーク / 認証制御 / テストプロセス）| ✅ Phase 1 |
| 06 | [06-logging-monitoring.md](06-logging-monitoring.md) | ログ・監視（最低限 OBS-1〜4、アプリの自由度は縛らない横断関心事）| ✅ Phase 1 |

> **Phase 1 完了時の検証成果（ファクトチェックで発見・修正）**:
> - proposal §FR-API-3 の WAF 閾値範囲を修正（`100〜200億` → `10〜20億`、AWS API リファレンス確認）+ 評価窓の「固定」表記を「選択可」に
> - §C-API-6 §C-6.6.4 の cdk-nag 誤ルール ID を修正（`LMB5`/`ELB7` は非実在 → 正しい ID + Lambda URL は cfn-guard で担保と注記）
> - タグ命名を kebab-case（`app-id`/`cost-center`）に確定（proposal PascalCase 例から正規化、BD-Q-03 解決）

### ② Swagger 駆動 認証外形監視の実装

| # | ファイル | 主な内容 | 状態 |
|---|---------|---------|:---:|
| 10 | [10-external-monitoring-overview.md](10-external-monitoring-overview.md) | 外形監視 総論（Pattern β + 全体図 + 実装物ナビ + Phase4 検証状況）| ✅ Phase 2 |
| 11 | [11-central-probe-architecture.md](11-central-probe-architecture.md) | 認証実装チェック 詳細（処理フロー / Hybrid 検証 / 4×4 / Positive トークン管理）| ✅ Phase 2 |
| 12 | [12-app-registry-design.md](12-app-registry-design.md) | App Registry（S3 台帳 registry/{appId}/{env}.json / 巡回自動登録 / lastCheckedCommitId）| ✅ Phase 2 |
| 13 | [13-openapi-registry-design.md](13-openapi-registry-design.md) | OpenAPI Registry（S3 コピー置き場・正本は repo の openapi.yaml / アノテーション）| ✅ Phase 2 |
| 14 | [14-probe-implementation-guide.md](14-probe-implementation-guide.md) | 実装ガイド（probe lib 構成 / モノリス / Private / 要 PoC、Synthetics は将来）| ✅ Phase 2 |
| 15 | [15-alert-routing-design.md](15-alert-routing-design.md) | 4×4 → SNS 振り分け（P1/P2/P3 / ARN 2 段解決）| ✅ Phase 2 |
| 16 | [16-cross-account-iam-design.md](16-cross-account-iam-design.md) | クロスアカウント IAM（読み取りロール DiscoveryReadRole / StackSets 配布 / BD-Q-01）| ✅ Phase 2 |
| 17 | [17-deployment-integration-and-registration.md](17-deployment-integration-and-registration.md) | デプロイ検知と登録（**中央巡回 pull 型・1h**、[ADR-061](../../adr/061-deploy-detection-pull-model.md)。CodeCommit コミット差分・モノリスも自動発見）| ✅ Phase 2 |
| 18 | [18-scan-modes-and-scheduling.md](18-scan-modes-and-scheduling.md) ⭐ | **スキャン実行モード（自動差分検査（モード1、旧称 M1）/自動 1h + 手動全量検査（モード3、旧称 M3）/手動、常時定期検査（モード2、旧称 M2）は将来、Lambda 基盤一本化）— 実行モデル SSOT** | ✅ Phase 2 |

## 実装物（code-samples/、認証基盤と分離）

**Phase 3 実装完了（2026-07-25、34 ファイル、5 エージェント並行 + AWS 公式検証）**:

| ディレクトリ | 内容 | 状態 |
|---|---|:---:|
| [code-samples/README.md](code-samples/README.md) | **データ契約**（App Registry schema / OpenAPI アノテーション / CloudWatch Metrics / 4×4 真偽値表 / Runtime バージョン）| ✅ |
| [code-samples/central-probe-lib/](code-samples/central-probe-lib/) | 認証実装確認処理 本体（index + lib 6 + test + README）、Lambda（Node.js 22 / SDK v3）| ✅ |
| [code-samples/multi-checks-blueprint/](code-samples/multi-checks-blueprint/) | Multi Checks Blueprint（`steps` オブジェクト schema 検証済 + OAuth + `${AWS_SECRET}`）| ✅ |
| [code-samples/app-registry-lambda/](code-samples/app-registry-lambda/) | App Registry CRUD（**旧 push 型参考実装**、発見 Lambda に流用。ADR-061）| ✅（参考）|
| [code-samples/openapi-export-lambda/](code-samples/openapi-export-lambda/) | OpenAPI get-export → S3（**旧 push 型参考実装**、発見 Lambda に流用）| ✅（参考）|
| [code-samples/alert-router-lambda/](code-samples/alert-router-lambda/) | 4×4 分類 → SNS routing（test 19 PASS）| ✅ |
| [code-samples/iac-guard-rules/](code-samples/iac-guard-rules/) | cfn-guard 3 ルール（認証 / Origin Protection / タグ）| ✅ |
| [code-samples/semgrep-rules/](code-samples/semgrep-rules/) | Semgrep 言語別ルール（Python/Node/Java、P3/P5/P6）| ✅ |
| [research/phase4-local-verification-results.md](research/phase4-local-verification-results.md) | **Phase 4 ローカル検証結果（P4-1〜P4-3、実バグ 2 件修正）** | ✅ |
| [research/](research/) | AWS 仕様確認等の一次記録 | 随時 |

> **Phase 3 の検証成果**: Synthetics runtime/namespace/SDK v3 を公式確認、Multi Checks は `steps` オブジェクト schema（`checks` 配列ではない）を確認、`${AWS_SECRET:name:key}` 構文確認、Custom Resource 応答形式（4096 bytes 上限 / 必ず SUCCESS/FAILED 送信）確認、get-export の body は Uint8Array を確認。全 JS 構文 OK / 全 JSON valid / classify 16 + routing 19 テスト PASS。

## Phase 4 ローカル検証（P4-1〜P4-3、2026-07-25、課金ゼロ範囲を実行）

**実際にツールを走らせて検証し、実バグ 2 件を発見・修正**（詳細: [research/phase4-local-verification-results.md](research/phase4-local-verification-results.md)）:

| Phase | 実行内容 | 結果 |
|:---:|---|---|
| **P4-1** | cfn-guard 3.2.0 / Semgrep 1.171.0 を実コード（脆弱/健全フィクスチャ）に適用 | ✅ + **実バグ 2 件修正** |
| **P4-2** | alert-router routing テスト + Lambda handler ロード | ✅ alert-router 19 PASS |
| **P4-3** | canary の probe.js + classify.js を実 HTTP + synthetics スタブで統合実行 | ✅ 4 PASS（漏れ検知実証）|

**発見・修正した実バグ（走らせないと分からなかった）**:
1. Semgrep `fastapi-missing-auth-middleware` が健全コードで誤検知 → `patterns:` リスト形式 + `pattern-not-inside` 末尾 `...` で修正
2. cfn-guard `alb_must_have_auth_action` が標準 `[authenticate-oidc, forward]` 構成で誤 FAIL → `some` 演算子で修正

**2026-07-26 追加検証（Docker/LocalStack 実行）**:
- P4-1 完了: cfn-guard 3 ファイル + Semgrep 3 言語すべてフィクスチャ検証（origin-protection / required-tags もバグなしで PASS/FAIL 正動作）
- P4-2 SDK 実挙動: **LocalStack 3.8.1** で app-registry PutItem / alert-router SNS Publish（App Registry DDB 経由の本番ルーティング）を end-to-end 実証。⚠ LocalStack `latest`(2026.7.0) は auth token 必須 → community は `3.8.1` ピン留め必須
- P4-3 probe lib logic: **27 PASS**（classify 16 + probe統合 4 + extractEndpoints 7）。full orchestration は registry Scan が LocalStack で成立、S3 は LocalStack の virtual-host addressing（`forcePathStyle` 要、実 AWS 無関係）で境界

> **要 PoC 検証（P4-3 full / P4-4 / P4-5、実 AWS or SAM が必要）**: 認証実装チェック Lambda E2E（SAM local）/ Positive probe（Bearer・SigV4）/ Cookie モノリス Positive / **発見 Lambda（CodeCommit GetBranch・GetDifferences・GetFile + S3 台帳）E2E** / CloudWatch metrics 着地 / マルチアカウント E2E。手順は [research/phase4-environment-setup-guide.md](research/phase4-environment-setup-guide.md)（旧 get-export 検証は push 型時代の記録）。

## 参照する主要 proposal / ADR

| 出典 | 内容 |
|---|---|
| [§C-API-5](../proposal/common/05-self-service-catalog.md) | Service Catalog 製品テンプレ |
| [§C-API-6](../proposal/common/06-external-api-auth-architecture.md) | 7 パターン / 5 大分類 / 6 漏れパターン × 5 検知レイヤー |
| [§FR-API-3](../proposal/fr/03-throttling-quota.md) | 流量制御・クォータ |
| [§FR-API-4](../proposal/fr/04-metering-billing.md) | 利用者識別・課金按分 |
| [ADR-039](../../adr/039-centralized-network-account-edge-layer.md) | ネットワーク監査アカウント / Origin Protection |
| [ADR-059](../../adr/059-central-auth-check-canary-architecture.md) | Central Auth Check Canary（Pattern β）|

## 運用ルール

- **前提変更時**: 00-plan の BD-P 表を先に改訂 → 影響章を差分改訂
- **ファクト検証**: AWS 固有仕様は一次資料で裏取り、各章末尾「検証済み事実」に URL 明示
- **認証基盤との分離**: 本ディレクトリは API プラットフォーム専用。認証基盤側 `doc/basic-design/` とは独立
