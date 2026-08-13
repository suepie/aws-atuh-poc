# ADR-061: デプロイ検知の pull 型統一（中央巡回による発見・差分検知）

日付: 2026-08-06（改訂 2026-08-07）
ステータス: Accepted

> ⚠ **改訂（2026-08-07）: 巡回の読み取り対象を「デプロイ資材（API GW deploymentId）」から「CodeCommit のコミット差分」単独に変更**。
> - 前提: 各アプリのコードリポジトリは **App アカウントの CodeCommit**（2025-11-24 に AWS が CodeCommit を完全 GA へ復帰、新規利用可）。
> - 変更検知 = `GetBranch` で先端コミット ID を取得し、台帳の `lastCheckedCommitId` と比較 → 変化あれば `GetDifferences` のパスで対象アプリを特定 → M1 検査。**「以前確認した範囲からの変更」を Git のコミット ID で表現**する（ユーザー提案 2026-08-07）。
> - メタデータは資源タグでなく **リポジトリ内 `monitoring.yaml`（config-as-code）**、OpenAPI も **リポジトリ内の spec** を正本として取得（`GetFile`）。`apigateway:GET` の資材読取は廃止し、読み取りロールは **codecommit read のみ**に縮小。
> - **モノリス（ALB 直）もリポジトリは列挙できるため自動発見の対象になる**（旧設計の「モノリスは手動登録」の穴が解消）。
> - **受容した穴（git 単独の代償、ユーザー決定）**: ① コンソール直変更（Authorizer 外し等）は git に現れず**見逃す** ② コミット直後は未デプロイのため旧版検査の偽安心があり得る。補完: ① は検知 5 レイヤーの **L2 Config Rules**（AuthorizationType=NONE の drift 検知、§FR-API-7）と **M3 手動フル**、② は次回巡回の再検査と M3。
> - Lambda 構成は **3 本**（発見 / 認証実装チェック / Alert Router）。
> - 本文の「deploymentId 比較」「apigateway:GET」は上記に読み替える。基本設計 12/13/16/17/18 章は改訂反映済み。
>
> ⚠ **追記（2026-08-13）: 台帳ストアを DynamoDB → S3 に統合**。分析の結果、台帳で本当に消せない情報は **lastCheckedCommitId（巡回状態）/ alertRouting / enabled（中央管理項目）の 3 つだけ**で、書き手は発見 Lambda 1 本（1h 毎・直列）・データ量はアプリ数百でも MB 未満のため、DynamoDB の性能・整合性が必要な要素がない。**OpenAPI Registry と同じ S3 バケット（Monitoring Registry）に `registry/{appId}/{env}.json` として同居**させ、ストアを S3 1 つに集約（ユーザー決定 2026-08-13。2026-08-07 の「DDB 維持」を更新）。代償: enabled/alertRouting の運用操作が JSON 編集になる・巡回を並列化する場合は排他制御の作り込みが要る（ETag 条件付き PUT で対応可）。DynamoDB は構成から消滅し、AWS リソースは **S3×1 + Lambda×3 + Scheduler + SNS/CloudWatch/Secrets** に縮小。
関連: [ADR-059 認証実装確認処理（Central Auth Check Canary）](059-central-auth-check-canary-architecture.md) / [基本設計 17 章](../api-platform/basic-design/17-deployment-integration-and-registration.md) / [18 章](../api-platform/basic-design/18-scan-modes-and-scheduling.md)

---

## Context

認証実装確認処理（ADR-059、Pattern β）の M1（デプロイ差分スキャン）は、**「アプリがデプロイされたことをどう検知するか」**に依存する。当初設計（基本設計 17 章 初版）は **push 型の 3 層構成**だった:

| 層 | 方式 | 内容 |
|---|---|---|
| 理想 | 案 A: Service Catalog 製品内 Custom Resource | 製品 deploy 時に App Registry 登録 + OpenAPI Export を自動実行 |
| 現実 | 案 B: CI/CD 登録ステップ | パイプライン末尾で登録 Lambda を invoke |
| 保険 | 案 C: EventBridge（CloudTrail）| 未登録の API GW 作成を検知してアラート |

この push 型には以下の課題があった:

1. **アプリ側にフットプリントが残る**: 製品内蔵とはいえ Custom Resource 2 つ（登録 + Export）がアプリの stack 内で動き、App アカウント → 共通基盤アカウントへの**書き込みクロスアカウント権限**が必要
2. **登録漏れの保険が別途必要**: 案 A/B を迂回した deploy を案 C で拾う 3 層構造は複雑
3. **モノリス（API GW なし）は案 C の保険も効かない**

ユーザーから「**資材をこちら（中央）から監視するシンプルなやり方は難しそうか。トリガーはこちらで引くに統一するのでも良い**」（2026-08-06）の提起があり、pull 型を比較検討した。

## 検討した選択肢

### 案 1: push 型 3 層（当初設計）

- ✅ deploy 直後（秒〜分）に検知、メタデータ（authPattern / 通知先）が製品パラメータで正確
- ⚠ 上記課題 1〜3。登録経路 2 つ + 保険 1 つの 3 層を維持し続けるコスト

### 案 2: pull 型 中央巡回（採用）

EventBridge Scheduler → 発見 Lambda（共通基盤アカウント）が定期巡回:

```
① Organizations で App アカウントを列挙
② 各アカウントへ読み取り専用ロールで AssumeRole（StackSets で一括配布）
③ API GW を list、stage の deploymentId / lastUpdatedDate を取得
④ 前回スナップショット（App Registry）と比較
⑤ 変化あり → get-export で OpenAPI を中央が取得（pull）→ そのアプリを probe（M1）
⑥ 未登録の API GW → 台帳へ自動登録（タグから authPattern 等を補完、不足はアラート）
```

- ✅ **アプリ側フットプリント実質ゼロ**（タグ付与のみ。Custom Resource / Export 廃止）
- ✅ **登録漏れが構造的に起きない**（中央が発見する側。3 層の保険が不要）
- ✅ **トリガーが中央に統一**（アプリ側イベントに依存しない）
- ✅ クロスアカウント権限が「App→中央の書き込み」から「中央→App の読み取り」に反転（最小権限で配布も容易）
- ⚠ **検知遅延 = 巡回間隔**（採用値 1 時間 → デプロイ後最大 1 時間の露出窓）
- ⚠ メタデータは資材から導出不可 → タグ規約 + 既定値 + 不足アラートで補完
- ⚠ モノリス（ALB 直）は自動発見不可 → 手動登録（push 型でも同じ制約）

### 案 3: ハイブリッド（pull 主体 + push 高速化オプション）

- ✅ 即時性と漏れゼロを両立
- ⚠ 経路が 2 つ残り、簡素化の目的に反する

## Decision

**案 2（pull 型 中央巡回）に統一する。巡回間隔は 1 時間。**

| 項目 | 決定 |
|---|---|
| M1 トリガー | **EventBridge Scheduler（1 時間毎）→ 発見 Lambda** による差分検知。アプリ側イベントは使わない |
| 発見・登録 | 発見 Lambda が API GW を列挙し App Registry へ**自動登録**（書き手はアプリでなく中央）|
| OpenAPI 取得 | 中央が AssumeRole + `get-export` で **pull**（openapi-export Custom Resource 廃止）|
| メタデータ | タグ規約（`app-id` / `env` / `auth-pattern` 等）から補完。不足時は既定値（Negative のみ検査）+「メタ不足」アラート。通知先（alertRouting）は台帳側で共通基盤チームが管理 |
| モノリス | 自動発見不可のため**手動登録**（台帳へ直接。件数少の前提）|
| Service Catalog 製品 | 登録系 Custom Resource を外し、**認証必須 / Origin Protection / タグ付与**に専念 |
| 検知遅延の受容 | 最大 1 時間。デプロイ前のガード（04 章静的解析 + 製品テンプレの認証必須）が一次防衛であり、外形監視は「すり抜けの検知網」のため 1 時間で許容（ユーザー決定 2026-08-06）|

### 実装物への影響

| 対象 | 変更 |
|---|---|
| `app-registry-lambda` / `openapi-export-lambda`（Custom Resource）| **廃止方向**（参考実装として保管。登録 API 部分は発見 Lambda から流用可）|
| 発見 Lambda（discovery）| **新規**（Phase 3 実装 + PoC 対象）|
| App Registry スキーマ | スナップショット属性（`deploymentId` / `lastSeenAt` / `discoveredBy`）を追加 |
| probe lib / classify / Alert Router | 変更なし |

## Consequences

- 17 章は 3 層構成から「中央巡回 1 本 + モノリス手動」に全面書換（基本設計側に反映済み）
- 18 章 M1 の定義が「デプロイイベント駆動」→「**巡回差分（1 時間毎の自動検知）**」に変わる。M3（手動フル）は不変
- 16 章のクロスアカウント IAM は書き込み系が消え、**読み取りロールの StackSets 配布**が主になる
- 検知遅延 1 時間を短縮したくなった場合は、巡回間隔の短縮（5〜15 分、コスト影響は軽微）または案 3 のハイブリッド化で対応可能（将来オプション）

---

## 付録: 旧 push 型内での書き込み経路 5 案比較（記録）

push 型（案 1）を前提としていた時期に、「App アカウントから中央の App Registry / OpenAPI Registry へどう書き込むか」を 5 案比較していた（旧基本設計 16 章）。pull 型統一で書き込み経路自体が消えたため不採用となったが、記録として残す。

| 案 | 仕組み | 評価（当時）|
|---|---|---|
| 1: 中央 Lambda + クロスアカウント Invoke | App アカウントが中央 Lambda を Invoke | Invoke 権限 1 点で最小。同期のため中央障害で deploy ブロックの懸念。**当時の Phase 1 第一候補** |
| 2: App アカウント Lambda + AssumeRole | App 側 Lambda が中央ロールを引受け書込 | AssumeRole ロジックが各アプリに分散 |
| 3: EventBridge クロスアカウント Bus | App → 中央 Event Bus → 中央 Lambda | 非同期・疎結合・Archive 監査。**当時の規模拡大時移行先** |
| 4: DynamoDB Resource Policy 直書き | 中央 DDB を直接開放 | 攻撃面最大で**非推奨** |
| 5: 中央 S3 に Put → イベント反映 | 登録 JSON を S3 経由 | 疎結合、OpenAPI と経路統一可 |

→ pull 型では「書き込みは共通基盤アカウント内の発見 Lambda のみ」となり、この比較は不要になった（現行 16 章 §16.1）。
