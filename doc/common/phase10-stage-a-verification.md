# Phase 10 / Stage A 検証レポート

> **作成日**: 2026-06-05
> **対象**: Keycloak v26.2 系を本番候補として確定するための追加 PoC 検証 Stage A
> **位置付け**: [doc/requirements/poc-summary-evaluation.md](../requirements/poc-summary-evaluation.md) の Phase 1-9 を補完する追加検証。プラットフォーム選定 Keycloak 方向確定（要件定義フェーズの意思決定）を裏付けるための実機確認

---

## 1. Stage A スコープと進捗

[doc/common/](.) の既存資料（auth-patterns / identity-broker-multi-idp / keycloak-network-architecture など）が PoC Phase 1-9 ベースなのに対し、本レポートは Keycloak 単独前提で Phase 10 として追加検証を進めた結果の一次資料。

| Task | 内容 | 状態 |
|---|---|:---:|
| **A4** | realm.json を Phase 7-9 込みの SSOT 化（Admin Console 手作業ゼロ運用） | ✅ ローカル検証済 |
| **A3** | Token Exchange v2 (RFC 8693) + SSR Confidential Client + M2M Client | ✅ ローカル検証済 |
| **A2** | ECS Multi-AZ + Auto Scaling + RDS Multi-AZ + Infinispan JDBC_PING クラスタ | 🟡 Terraform 完成、AWS apply 保留 |
| **A1** | `start --optimized` + ACM 自己署名 HTTPS + ALB 443 listener + Keycloak v26.2 化 | 🟡 Terraform/Dockerfile 完成、AWS apply 保留 |

---

## 2. A4: realm.json SSOT 化（完全達成）

### 課題（[poc-summary-evaluation.md §3.1](../requirements/poc-summary-evaluation.md) 既出）

旧 [keycloak/config/realm-export.json](../../keycloak/config/realm-export.json) は **155 行 / Phase 6 構成**のみ。Phase 7-9 で Admin Console から動的に追加した設定（TOTP / Identity Brokering / Conditional OTP / Protocol Mappers）が反映されていなかった。`make tf-destroy-kc` → `make tf-apply-kc` で再構築すると Phase 7-9 の検証構成が消失し、Admin Console での手作業 10 分が必須だった。

### 解決した内容

#### Phase 8/9 中核設定を realm.json に統合

| 設定項目 | 反映方法 |
|---|---|
| Unmanaged Attributes Enabled | `attributes.userProfileEnabled = "true"` |
| 追加 Realm Roles (`employee` / `manager`) | `roles.realm[]` に追加（既存 `user`/`admin`/`expense-approver` 保持で後方互換） |
| Protocol Mappers (`tenant_id` / `roles` / `email`) | `clients[auth-poc-spa].protocolMappers[]` |
| Full Scope Allowed OFF | `clients[*].fullScopeAllowed = false` |
| Scope Mappings | `scopeMappings[].roles` に 5 ロール |
| Phase 8/9 テストユーザー (alice-kc / bob-kc / carol-kc / dave-kc) | `users[]` に tenant_id 属性 + realmRoles 付き |
| Backchannel Logout 対応 | `attributes.backchannel.logout.session.required = "true"` |

#### Phase 7 Auth0 IdP は別ファイル化

環境変数依存（Auth0 tenant ごとに値が変わる）かつ secret 含むため、[keycloak/config/realm-idp-auth0.json.example](../../keycloak/config/realm-idp-auth0.json.example) をテンプレートとして分離。`${AUTH0_DOMAIN}` / `${AUTH0_CLIENT_ID}` / `${AUTH0_CLIENT_SECRET}` の placeholder で kcadm.sh import する運用に。

Conditional OTP Flow は Keycloak v26.2 標準の `browser` flow に組み込み済みのため、追加ファイル不要（フェデユーザーの OTP credential 未設定で自動スキップ）。

### 検証結果（fresh import）

Docker Compose で realm.json を import し、Admin REST API で各ユーザーの Token Evaluation を実施:

| ユーザー | tenant_id | roles | realm_access.roles（内部ロール混入） |
|---|---|---|---|
| `alice-kc` | `acme-corp` | `["employee"]` | `["employee"]` (クリーン) |
| `bob-kc` | `acme-corp` | `["manager"]` | `["manager"]` (クリーン) |
| `carol-kc` | `acme-corp` | `["admin"]` | `["admin"]` (クリーン) |
| `dave-kc` | `globex-inc` | `["manager"]` | `["manager"]` (クリーン) |

→ `offline_access` / `uma_authorization` 等が混入しないクリーンな claim 出力を確認。`fullScopeAllowed: false` の効果が立証された。

### 再現手順

```bash
cd keycloak/
docker compose down -v          # 既存ボリュームを完全削除
docker compose build            # Keycloak 26.2 + features を multi-stage build
docker compose up -d
# 起動完了後（~15s）:
curl -s http://localhost:8080/realms/auth-poc/.well-known/openid-configuration | jq .grant_types_supported
# → "urn:ietf:params:oauth:grant-type:token-exchange" が含まれていること

# bob-kc の token claim を Admin API で確認:
# 1) admin-cli で master realm token 取得
# 2) /admin/realms/auth-poc/clients/{spa-uuid}/evaluate-scopes/generate-example-access-token?userId={bob-uuid}
# 3) 戻り値の tenant_id / roles / realm_access.roles を確認
```

詳細は [keycloak/config/README.md](../../keycloak/config/README.md) 参照。

---

## 3. A3: Token Exchange v2 検証（完全達成）

### 検証目的

Keycloak v26.2 で GA となった **Standard Token Exchange v2 (RFC 8693)** が、本基盤で要件となるマイクロサービス間ユーザーコンテキスト伝播フローを実装できることを確認。Cognito 非対応の主要要因（[ADR-014](../adr/014-auth-patterns-scope.md)）の置き換え可能性を立証する。

### 構成

[Dockerfile](../../keycloak/Dockerfile) を Keycloak 26.2 + multi-stage build に書き換え、起動時 `kc.sh build` augmentation を image build に前倒し（`start --optimized` 化と一体で対応）。

```dockerfile
FROM quay.io/keycloak/keycloak:26.2 AS builder
ENV KC_DB=postgres
ENV KC_FEATURES=token-exchange,token-exchange-standard,admin-fine-grained-authz
RUN /opt/keycloak/bin/kc.sh build

FROM quay.io/keycloak/keycloak:26.2
COPY --from=builder /opt/keycloak/ /opt/keycloak/
COPY config/realm-export.json /opt/keycloak/data/import/
```

> 注: 機能名は `token-exchange-standard`（`-v2` サフィックス無し）。v26.2 では `token-exchange` (legacy v1, Deprecated) と `token-exchange-standard` (RFC 8693 v2 GA) が併存する。

### realm.json への追加 client

| Client | 役割 | 設定 |
|---|---|---|
| `auth-poc-backend` | M2M Client Credentials + Token Exchange v2 **subject** | `serviceAccountsEnabled: true` + `attributes.standard.token.exchange.enabled = "true"` + `oidc-audience-mapper` で target audience 許可 |
| `auth-poc-target-api` | Token Exchange v2 **target** (bearer-only API client) | `bearerOnly: true` + `attributes.standard.token.exchange.enabled = "true"` |
| `auth-poc-ssr` | SSR Confidential Client (Phase 10 認証パターン拡張 Must) | `publicClient: false` + `secret` + standard flow + PKCE + backchannel logout |

### 検証結果（fresh import 後の RFC 8693 E2E）

```bash
# Step 1: Client Credentials で初期 access token 取得
INIT=$(curl -s -X POST http://localhost:8080/realms/auth-poc/protocol/openid-connect/token \
  -d "grant_type=client_credentials&client_id=auth-poc-backend&client_secret=...")

# Step 2: Token Exchange v2 で audience を target API 向けに変換
RESP=$(curl -s -X POST http://localhost:8080/realms/auth-poc/protocol/openid-connect/token \
  --data-urlencode "grant_type=urn:ietf:params:oauth:grant-type:token-exchange" \
  --data-urlencode "client_id=auth-poc-backend" \
  --data-urlencode "client_secret=..." \
  --data-urlencode "subject_token=$INIT_TOKEN" \
  --data-urlencode "subject_token_type=urn:ietf:params:oauth:token-type:access_token" \
  --data-urlencode "audience=auth-poc-target-api")
```

戻り値:
- `issued_token_type: urn:ietf:params:oauth:token-type:access_token` ✓
- `token_type: Bearer` ✓
- `expires_in: 3600` ✓
- 交換後トークン claim: `iss=http://localhost:8080/realms/auth-poc` / **`aud=auth-poc-target-api`** (subject token の azp から audience に切り替わった証拠) / `azp=auth-poc-backend`

→ RFC 8693 準拠の audience exchange が動作。本番でマイクロサービス間トークン変換に転用可能。

### 既知の運用上の留意点

1. **subject/target 双方の opt-in 必須**: realm.json の `attributes.standard.token.exchange.enabled = "true"` が各 client に必要。本番テナント追加時はテンプレートで標準化する
2. **audience の権限制御**: subject の dedicated scope に `oidc-audience-mapper` を追加して target を明示的に許可する。クライアント数が多い場合は scope mapping 設計を本番設計フェーズで標準化
3. **legacy v1 (`token-exchange`) は Deprecated**: 既存実装の移行先として v2 が標準。互換性のため両方を build features に入れている

---

## 4. A2: Multi-AZ HA / Infinispan クラスタ（Terraform 完成、AWS apply 保留）

### 変更内容

| ファイル | 変更点 |
|---|---|
| [infra/keycloak/ecs.tf](../../infra/keycloak/ecs.tf) | `desired_count = var.keycloak_desired_count` (default 2), env vars 追加: `KC_CACHE=ispn` / `KC_CACHE_STACK=jdbc-ping` / `KC_DB_POOL_MAX_SIZE=30` |
| [infra/keycloak/rds.tf](../../infra/keycloak/rds.tf) | `multi_az = var.rds_multi_az` (default true) |
| [infra/keycloak/security-groups.tf](../../infra/keycloak/security-groups.tf) | ECS SG self-referencing TCP:7800 ingress/egress (JGroups messaging) |
| [infra/keycloak/ecs-autoscaling.tf](../../infra/keycloak/ecs-autoscaling.tf) (新規) | Application Auto Scaling target + CPU 70% / Memory 75% policies (min=2, max=4) |
| [infra/keycloak/variables.tf](../../infra/keycloak/variables.tf) | `keycloak_desired_count` / `keycloak_autoscale_min/max` / `keycloak_db_pool_max_size` / `rds_multi_az` 追加 |

### 設計判断

- **Infinispan クラスタ stack 選択**: `jdbc-ping` を採用。AWS Fargate で multicast (`MPING`) が機能しないため、PostgreSQL 上の `JGROUPSPING` テーブルで member discovery する方式。実際の cluster messaging は TCP:7800 で SG self-rule 必須
- **HikariCP プールサイズ**: RDS db.t4g.micro の `max_connections ≒ 105` を考慮し、`KC_DB_POOL_MAX_SIZE = 30` で task × 2 + 余裕分 → 約 60 接続。本番では RDS インスタンス上げ + pool 拡張を別途検討
- **Auto Scaling 指標**: CPU + Memory の二軸でターゲット追跡。Keycloak は JWT 署名・JIT プロビジョニング・パスワードハッシュで CPU バウンドだが、Infinispan キャッシュで Memory も逼迫しうるため両方を見る
- **ECS desired_count の lifecycle.ignore_changes**: PoC コスト管理目的の `aws ecs update-service ... --desired-count 0` 手動停止運用と互換性維持。Auto Scaling 動作中も Terraform は介入しない

### AWS apply 後の検証手順（次回セッション）

```bash
# 1. apply 直後の cluster health 確認
aws ecs describe-services --cluster auth-poc-kc-cluster --services auth-poc-kc-service \
  --query 'services[0].{desiredCount:desiredCount,runningCount:runningCount,deployments:deployments}'

# 2. Infinispan cluster 形成確認（CloudWatch Logs で JGroups メッセージを grep）
aws logs filter-log-events --log-group-name /ecs/auth-poc-kc \
  --filter-pattern "JGroups" --max-items 10

# 3. RDS Multi-AZ 確認
aws rds describe-db-instances --db-instance-identifier auth-poc-kc-db \
  --query 'DBInstances[0].{MultiAZ:MultiAZ,SecondaryAZ:SecondaryAvailabilityZone}'

# 4. フェイルオーバーテスト
#    A) ECS task 1 つを停止 → desired_count が即座に補充されること
aws ecs list-tasks --cluster auth-poc-kc-cluster --service-name auth-poc-kc-service
aws ecs stop-task --cluster auth-poc-kc-cluster --task <task-arn>
# 観察: ALB target health で UNHEALTHY → 新 task 起動 → HEALTHY 復帰の遷移

#    B) RDS フェイルオーバー強制
aws rds reboot-db-instance --db-instance-identifier auth-poc-kc-db --force-failover
# 観察: 60-120 秒の認証停止 → Keycloak 自動再接続後復旧
```

---

## 5. A1: HTTPS + start --optimized（Terraform/Dockerfile 完成、AWS apply 保留）

### 変更内容

| ファイル | 変更点 |
|---|---|
| [infra/keycloak/tls.tf](../../infra/keycloak/tls.tf) (新規) | `tls_private_key` + `tls_self_signed_cert` (1 年有効) → `aws_acm_certificate` import |
| [infra/keycloak/alb.tf](../../infra/keycloak/alb.tf) | Public/Admin ALB に 443 HTTPS listener 追加（TLS 1.3 policy）、80 listener は 443 redirect default に変更 |
| [infra/keycloak/security-groups.tf](../../infra/keycloak/security-groups.tf) | Public/Admin ALB SG に 443 ingress 追加 |
| [infra/keycloak/main.tf](../../infra/keycloak/main.tf) | `hashicorp/tls ~> 4.0` provider 追加 |
| [infra/keycloak/ecs.tf](../../infra/keycloak/ecs.tf) | env 更新: `KEYCLOAK_ADMIN*` → `KC_BOOTSTRAP_ADMIN_*` (v26 名称) / `KC_HOSTNAME=https://${aws_lb.keycloak.dns_name}` / `KC_HOSTNAME_BACKCHANNEL_DYNAMIC=true` / `KC_METRICS_ENABLED=true` / command を `start --optimized --import-realm` に変更 |
| [keycloak/Dockerfile](../../keycloak/Dockerfile) | Keycloak 26.0 → 26.2 / multi-stage build (`kc.sh build` 段階で features 焼き付け) |

### 設計判断

- **自己署名証明書を採用した理由**: ドメイン取得を待たずに `start --optimized` (HTTPS 要件) を検証するため。本番では ACM 公開証明書 + Route 53 カスタムドメインに差し替え（subdomain-architecture-notes.md §2 の Pattern A に従い `auth.<parent-domain>` 想定）
- **ALB TLS 終端 → ECS は HTTP のまま**: Keycloak 内部は HTTP:8080 で稼働、`KC_PROXY_HEADERS=xforwarded` で X-Forwarded-Proto を解釈して "https" を認識。`KC_HOSTNAME` で外部 URL を固定
- **`KC_HOSTNAME_BACKCHANNEL_DYNAMIC=true`**: Public ALB と Internal ALB で URL が異なる構成 (ADR-012) に対応。backchannel 通信時のみ動的に hostname 切替
- **`KC_BOOTSTRAP_ADMIN_*`**: Keycloak v26 から `KEYCLOAK_ADMIN*` は Deprecated 警告。新名称で初期 admin user を作成

### AWS apply 後の検証手順（次回セッション）

```bash
# 1. ACM 証明書状態確認
aws acm list-certificates --query 'CertificateSummaryList[?DomainName==`auth-poc-keycloak.poc.local`]'

# 2. ALB HTTPS listener 動作確認
ALB_DNS=$(terraform output -raw keycloak_public_url | sed 's|http://||')
curl -kv https://$ALB_DNS/realms/auth-poc/.well-known/openid-configuration 2>&1 | grep -E "(HTTP/|issuer)"
# 期待値:
#   - HTTP/1.1 200 OK
#   - issuer: https://auth-poc-kc-alb-xxx.elb.amazonaws.com/realms/auth-poc (https スキーム!)

# 3. 80 → 443 redirect 動作確認
curl -kIs http://$ALB_DNS/realms/master | head -3
# 期待値: HTTP/1.1 301 Moved Permanently / Location: https://...

# 4. start --optimized 起動高速化の確認
aws logs filter-log-events --log-group-name /ecs/auth-poc-kc \
  --filter-pattern "started in" --max-items 5
# 期待値: start --optimized では augmentation スキップで起動が 4-5 秒短縮
```

---

## 6. ローカル検証のまとめ表

| 検証観点 | ローカル成果 | 本番想定との差 |
|---|---|---|
| realm.json による Phase 7-9 再現性 | ✅ Admin Console 手作業ゼロで bob-kc 等の claim 注入動作 | 本番では Terraform provider or CI/CD で realm.json を git → apply 自動化 |
| Token Exchange v2 (RFC 8693) | ✅ audience 切替成功、subject/target 双方の opt-in 属性反映 | 本番では service mesh 内のマイクロサービス間 token chain で運用 |
| SSR Confidential Client | ✅ realm.json に `auth-poc-ssr` 投入、attributes/mappers 検証済 | 実 SSR app (Next.js / Spring Boot) を立てた E2E は Stage B 以降 |
| start --optimized + multi-stage build | ✅ Dockerfile build augmentation 完了 | ECS 起動時の augmentation スキップは AWS apply で立証予定 |
| Multi-AZ HA / Infinispan クラスタ | 🟡 Terraform 完成 | AWS apply 後、JGroups TCP messaging 動作 + RDS failover を実機確認 |
| HTTPS + ACM | 🟡 Terraform 完成 | AWS apply 後、HTTPS 443 + redirect + start --optimized の組合せ動作を実機確認 |

---

## 7. 次回セッションのチェックリスト

### Pre-apply

- [ ] [infra/keycloak/terraform.tfvars](../../infra/keycloak/terraform.tfvars) で `db_password` / `keycloak_admin_password` が PoC 用ダミーから変更されているか確認
- [ ] `allowed_cidr_blocks` で社内 NW or 検証担当 IP を追加（必要なら）
- [ ] AWS profile / region (ap-northeast-1) が正しいか確認

### Apply

```bash
cd infra/keycloak
terraform init -upgrade
terraform plan -out=stage-a.plan    # 68 to add の最終確認
terraform apply stage-a.plan         # ~15 分

# ECR push（kc.sh build 済 image）
make kc-push                         # Makefile の既存ターゲット

# ECS service が起動完了するまで待機（~5 分）
aws ecs wait services-stable --cluster auth-poc-kc-cluster --services auth-poc-kc-service
```

### Post-apply verification

- §4 の A2 検証手順（cluster health / JGroups / RDS Multi-AZ / フェイルオーバー）
- §5 の A1 検証手順（ACM / HTTPS / redirect / 起動時間短縮）
- realm.json fresh import が AWS でも動作（Phase 8/9 ユーザーで token claim 確認）
- Token Exchange v2 が AWS でも動作（curl で audience exchange）

### コスト管理

検証完了後の選択肢:
1. **そのまま運用**: ~$190-200/月
2. **一時停止**: ECS desired_count=0 + RDS stop → ~$90/月 (ALB+VPCE のみ)
3. **完全停止**: `make tf-destroy-kc` → $0、再開時は再 apply（~20 分）

---

## 8. Stage B 以降への引き継ぎ事項

[Stage A 全体評価レポート](../../README.md#stage-a-成果) の章を参照（次回作成予定）。Stage B 着手前に必要な情報:

1. **Token Exchange の本番運用設計**: subject/target opt-in 標準化、audience scope mapping 設計、service mesh 統合
2. **realm.json IaC 化の組織ルール**: Admin Console 変更禁止 + PR 必須運用ポリシーの確立
3. **HA 監視メトリクス**: Auto Scaling 動作確認、CloudWatch アラーム閾値、Prometheus `/metrics` endpoint 活用 (A1 で `KC_METRICS_ENABLED=true` 設定済)
4. **Phase 7 Auth0 IdP の本番 secret 管理**: AWS Secrets Manager + ECS Task Definition 経由の注入設計
