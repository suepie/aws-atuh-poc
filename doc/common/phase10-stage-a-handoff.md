# Phase 10 Stage A 引き継ぎノート

> **作成日**: 2026-06-05
> **用途**: 別セッション（または別オペレーター）が Stage A を引き継ぐための bootstrap 資料
> **直近コミット**: `440830e` - "Phase 10 Stage A: realm.json SSOT化 + Token Exchange v2 + HA/HTTPS Terraform"

---

## 1. 30秒サマリ

- プラットフォーム選定は **Keycloak v26.2 系で確定方向**（要件定義フェーズの意思決定、[project-platform-direction-keycloak](../../../.claude/projects/-Users-suepie-Develop-10-project-aws-atuh-poc/memory/project_platform_direction_keycloak.md) 参照）
- Keycloak で要件全部を確実にカバーできるかを追加 PoC（Phase 10）で網羅検証中
- **Stage A の 4 タスクのうち A4 / A3 はローカル実機検証完了**、A1 / A2 は **Terraform/Dockerfile 完成だが AWS apply 未実施**
- 詳細は [phase10-stage-a-verification.md](phase10-stage-a-verification.md) を最初に読む

---

## 2. 完了済み（再実行不要）

### ✅ A4: realm.json を Phase 7-9 込み SSOT 化
- [keycloak/config/realm-export.json](../../keycloak/config/realm-export.json) に統合済（Roles / Protocol Mappers / Full Scope OFF / 4 テストユーザー + tenant_id 属性 / SSR client / Token Exchange clients）
- [keycloak/config/realm-idp-auth0.json.example](../../keycloak/config/realm-idp-auth0.json.example) で Phase 7 Auth0 IdP を環境変数テンプレ分離
- [keycloak/config/README.md](../../keycloak/config/README.md) に運用手順
- Docker Compose で fresh import → bob-kc 等で claim 注入を実機確認済

### ✅ A3: Token Exchange v2 + SSR Confidential Client
- [keycloak/Dockerfile](../../keycloak/Dockerfile) を Keycloak 26.2 + multi-stage build に書換
- `KC_FEATURES=token-exchange,token-exchange-standard,admin-fine-grained-authz`
- realm.json に `auth-poc-ssr` (Confidential SSR) と `auth-poc-target-api` (Token Exchange target) 追加
- RFC 8693 audience exchange 動作確認済（`aud=auth-poc-target-api` / `azp=auth-poc-backend`）

### ✅ Terraform コード記述完了（apply 未実施）
- A2: [infra/keycloak/ecs.tf](../../infra/keycloak/ecs.tf) / [rds.tf](../../infra/keycloak/rds.tf) / [security-groups.tf](../../infra/keycloak/security-groups.tf) / [ecs-autoscaling.tf](../../infra/keycloak/ecs-autoscaling.tf) (新規) / [variables.tf](../../infra/keycloak/variables.tf)
- A1: [tls.tf](../../infra/keycloak/tls.tf) (新規) / [alb.tf](../../infra/keycloak/alb.tf) / [main.tf](../../infra/keycloak/main.tf) (tls provider 追加)
- `terraform validate` ✓ / `terraform plan` → `Plan: 68 to add, 0 to change, 0 to destroy`

---

## 3. 次にやること（3 つの選択肢）

### Path A: AWS apply して A1 / A2 を実機検証 ★ 元の Stage A スコープ完遂

**所要時間**: terraform apply ~15 分 + ECR push ~3 分 + 起動安定 ~5 分 + 検証 ~30-60 分 = 合計 1.5-2 時間
**コスト**: 常時稼働 ~$190-200/月、停止運用なら ~$90/月

```bash
cd /Users/suepie/Develop/10_project/aws-atuh-poc/infra/keycloak

# 1. Pre-flight
cat terraform.tfvars  # db_password / keycloak_admin_password が PoC ダミーから変更されているか
terraform plan -out=stage-a.plan

# 2. Apply
terraform apply stage-a.plan

# 3. ECR push (Dockerfile が KC 26.2 + features 焼き付け版になっている)
cd /Users/suepie/Develop/10_project/aws-atuh-poc
make kc-push

# 4. ECS 起動待ち
aws ecs wait services-stable --cluster auth-poc-kc-cluster --services auth-poc-kc-service

# 5. 検証
# A2 - Infinispan cluster 形成
aws logs filter-log-events --log-group-name /ecs/auth-poc-kc \
  --filter-pattern "JGroups" --max-items 20
# A2 - RDS Multi-AZ
aws rds describe-db-instances --db-instance-identifier auth-poc-kc-db \
  --query 'DBInstances[0].{MultiAZ:MultiAZ,SecondaryAZ:SecondaryAvailabilityZone}'
# A1 - HTTPS
ALB_DNS=$(cd infra/keycloak && terraform output -raw keycloak_url | sed 's|http://||')
curl -kv https://$ALB_DNS/realms/auth-poc/.well-known/openid-configuration 2>&1 | grep issuer
# 期待: issuer に "https://" が含まれる
# A1 - 80→443 redirect
curl -kIs http://$ALB_DNS/realms/master | head -3
# 期待: 301 Moved Permanently / Location: https://...

# 6. フェイルオーバーテスト
TASK=$(aws ecs list-tasks --cluster auth-poc-kc-cluster --service-name auth-poc-kc-service --query 'taskArns[0]' --output text)
aws ecs stop-task --cluster auth-poc-kc-cluster --task $TASK
# 観察: ALB target health で UNHEALTHY → 新 task 起動 → HEALTHY 復帰

aws rds reboot-db-instance --db-instance-identifier auth-poc-kc-db --force-failover
# 観察: 60-120 秒の認証停止 → Keycloak 自動再接続後復旧

# 7. 検証結果を phase10-stage-a-verification.md に追記
```

詳細は [phase10-stage-a-verification.md §4-§5 と §7](phase10-stage-a-verification.md) を参照。

### Path B: Stage B（顧客要件直結検証）に進む

Stage A の AWS apply は後回しにして、コストをかけずに進められる検証に集中:

| Stage B 項目 | 所要 | AWS 必要 |
|---|---|---|
| B1: LDAP Federation (OpenLDAP コンテナ立てて) | 1-2日 | 不要（Docker でいける） |
| B2: HRD + CloudFront Lambda@Edge | 2-3日 | 必要（CloudFront 別途） |
| B3: First Broker Login UX 検証（7 シナリオ消化） | 2日 | 不要（Auth0 + ローカル Keycloak） |
| B4: 既存ユーザー移行 + Hash 互換 + SAML IdP 発行 | 2-3日 | 不要 |

Stage B の優先度判断は [phase10-stage-a-verification.md §8 Stage B 引継ぎ事項](phase10-stage-a-verification.md) を参照。

### Path C: 要件定義 proposal/ ドキュメントを Keycloak 確定で更新

[doc/requirements/proposal/](../requirements/proposal/) 配下の章を Keycloak 単独前提で書き直す:
- §C-2 プラットフォーム選定: Cognito vs Keycloak → OSS Keycloak vs RHBK に縮約
- §FR-2.3.3 IdP UX: ハイブリッド (A + C) Keycloak リファレンス（[project_idp_ux_hybrid_keycloak](../../../.claude/projects/-Users-suepie-Develop-10-project-aws-atuh-poc/memory/project_idp_ux_hybrid_keycloak.md)）を正式採用
- §FR-2.2.1.A 重複: First Broker Login Flow（Keycloak 標準）を主軸に
- §NFR-1/5 可用性/DR: Keycloak HA + Multi-AZ + マルチリージョン設計の本番要件
- §NFR-8 コスト: 損益分岐議論削除、HA/DR コスト試算に差し替え

これは要件定義チーム向けの整理作業。AWS リソース不要。

---

## 4. 絶対守ること（ユーザールール）

| ルール | 出典 |
|---|---|
| **コミットメッセージに `Co-Authored-By: Claude ...` を入れない** | [feedback_commit_style](../../../.claude/projects/-Users-suepie-Develop-10-project-aws-atuh-poc/memory/feedback_commit_style.md) |
| 検討過程はメモリに残す（feedback / project / reference の使い分け） | [feedback_memory_preference](../../../.claude/projects/-Users-suepie-Develop-10-project-aws-atuh-poc/memory/feedback_memory_preference.md) |
| proposal/ 各章は §X.0 で「背景・なぜここで決めるか」を必ず提示 | [feedback_section_prologue](../../../.claude/projects/-Users-suepie-Develop-10-project-aws-atuh-poc/memory/feedback_section_prologue.md) |

---

## 5. 最初に読むべきメモリ

新セッション開始時、まず以下を順に読む（auto-memory の `MEMORY.md` に index あり、`Read` ツールで該当ファイル参照）:

1. [project-platform-direction-keycloak](../../../.claude/projects/-Users-suepie-Develop-10-project-aws-atuh-poc/memory/project_platform_direction_keycloak.md) — **Keycloak 確定方向の根拠と論点シフト**（最重要、2026-06-05 保存）
2. [project-poc-approach](../../../.claude/projects/-Users-suepie-Develop-10-project-aws-atuh-poc/memory/project_poc_approach.md) — PoC Phase 1-9 全体像
3. [project-basic-policy](../../../.claude/projects/-Users-suepie-Develop-10-project-aws-atuh-poc/memory/project_basic_policy.md) — 基本方針 4 軸
4. [project-account-linking-investigation](../../../.claude/projects/-Users-suepie-Develop-10-project-aws-atuh-poc/memory/project_account_linking_investigation.md) — Keycloak First Broker Login Flow（A4 で活用済）
5. [project-idp-ux-hybrid-keycloak](../../../.claude/projects/-Users-suepie-Develop-10-project-aws-atuh-poc/memory/project_idp_ux_hybrid_keycloak.md) — IdP UX ハイブリッド（Path C で使用）
6. [project-cognito-2024-specs](../../../.claude/projects/-Users-suepie-Develop-10-project-aws-atuh-poc/memory/project_cognito_2024_specs.md) — Cognito 仕様（比較表更新時のみ参照）

---

## 6. 主要ファイル参照

### Stage A の成果物
- [doc/common/phase10-stage-a-verification.md](phase10-stage-a-verification.md) — **検証レポート（最初に読む）**
- [keycloak/config/realm-export.json](../../keycloak/config/realm-export.json) — Phase 7-9 込み realm SSOT
- [keycloak/config/README.md](../../keycloak/config/README.md) — realm 運用ガイド
- [keycloak/config/realm-idp-auth0.json.example](../../keycloak/config/realm-idp-auth0.json.example) — Auth0 IdP テンプレ
- [keycloak/Dockerfile](../../keycloak/Dockerfile) — KC 26.2 + features multi-stage
- [infra/keycloak/](../../infra/keycloak/) — Stage A の Terraform 一式

### 既存の Phase 1-9 資料（背景理解に）
- [doc/requirements/poc-summary-evaluation.md](../requirements/poc-summary-evaluation.md) — PoC 総括（Phase 1-9）
- [doc/common/architecture.md](architecture.md) — 全体アーキ
- [doc/common/identity-broker-multi-idp.md](identity-broker-multi-idp.md) — Identity Broker パターン
- [doc/common/auth-patterns.md](auth-patterns.md) — 認証パターン 9 種
- [doc/common/keycloak-network-architecture.md](keycloak-network-architecture.md) — Keycloak ネットワーク
- [doc/adr/](../adr/) — ADR 001-016

### 要件定義側（Path C で触る）
- [doc/requirements/proposal/00-index.md](../requirements/proposal/00-index.md) — proposal SSOT
- [doc/requirements/proposal/fr/](../requirements/proposal/fr/) — §FR-1〜9
- [doc/requirements/proposal/common/](../requirements/proposal/common/) — §C-1〜6

---

## 7. ローカル Keycloak の状態

セッション終了時に `docker compose down`（volume は保持）で停止済。再起動方法:

```bash
cd /Users/suepie/Develop/10_project/aws-atuh-poc/keycloak/
docker compose up -d
# realm-export.json + Dockerfile (KC 26.2 + token-exchange features) で起動済イメージあり
# 既存ボリュームがあるため --import-realm は OVERWRITE_EXISTING で動作

# 完全 fresh import したい場合:
docker compose down -v
docker compose build
docker compose up -d

# ヘルスチェック
curl -sf http://localhost:8080/health/ready && echo "ready"

# A4 検証の再現
ADMIN_TOKEN=$(curl -sf -X POST http://localhost:8080/realms/master/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password&client_id=admin-cli&username=admin&password=admin" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
# /admin/realms/auth-poc/clients/{auth-poc-spa の UUID}/evaluate-scopes/generate-example-access-token?userId={bob-kc の UUID}&scope=openid+profile+email+roles
# で tenant_id / roles / email を確認

# A3 Token Exchange の再現
INIT=$(curl -sf -X POST http://localhost:8080/realms/auth-poc/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=auth-poc-backend&client_secret=change-me-in-production" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
curl -s -X POST http://localhost:8080/realms/auth-poc/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "grant_type=urn:ietf:params:oauth:grant-type:token-exchange" \
  --data-urlencode "client_id=auth-poc-backend" \
  --data-urlencode "client_secret=change-me-in-production" \
  --data-urlencode "subject_token=$INIT" \
  --data-urlencode "subject_token_type=urn:ietf:params:oauth:token-type:access_token" \
  --data-urlencode "audience=auth-poc-target-api"
# → access_token に aud=auth-poc-target-api が出ること
```

---

## 8. 未コミットファイル（このセッションで触っていない）

別作業のため commit から除外したファイル:
- `doc/common/00-index.md` (M) — `hook-architecture-keycloak.md` の index 追加
- `doc/common/hook-architecture-keycloak.md` (??) — Keycloak Hook アーキテクチャの別途検討資料

これらは Stage A とは独立した検討。引き継ぎ後にユーザーが別途扱う可能性があるためそのまま残してある。

---

## 9. AWS apply するなら最初に確認すること

```bash
# AWS 認証情報・リージョン
aws sts get-caller-identity
aws configure get region   # ap-northeast-1 期待

# Terraform tfvars の secret
grep -E "(db_password|keycloak_admin_password)" infra/keycloak/terraform.tfvars
# → PoC ダミー値のままなら、本検証用に強いパスワードに変更

# 既存 Keycloak リソース（apply 前にあったらコンフリクトする）
aws ecs list-clusters --query 'clusterArns[?contains(@, `auth-poc-kc`)]'
aws rds describe-db-instances --query 'DBInstances[?contains(DBInstanceIdentifier, `auth-poc-kc`)].DBInstanceIdentifier'
# 何も返ってこなければ destroy 状態（terraform plan が 68 to add のはず）

# Makefile の関連ターゲット確認
grep -E "^(tf-apply-kc|kc-push|tf-destroy-kc):" Makefile
```

---

## 10. 引き継ぎ完了後の TODO

新セッションで `TodoWrite` を立てるなら次の構造で:

```
1. 引き継ぎノート phase10-stage-a-handoff.md を読む
2. ユーザーに次の方向性を確認（Path A/B/C のどれか）
3. 選択された Path の作業を開始
4. 進捗を都度 phase10-stage-a-verification.md に追記
5. 終了時に git commit（Co-Authored-By なし）
```
