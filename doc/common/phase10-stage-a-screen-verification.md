# Phase 10 Stage A 画面 / 接続検証シナリオ集

> **作成日**: 2026-06-06
> **対象**: Phase 10 Stage A 反映後の AWS 環境（Keycloak 26.2 + HA + HTTPS 化）
> **前提**: `infra/keycloak` の apply 完了 + `make kc-push` 完了 + ECS desired=2 で稼働中
> **関連**: [phase10-stage-a-handoff.md](phase10-stage-a-handoff.md) / [phase10-stage-a-verification.md](phase10-stage-a-verification.md)

---

## 0. 環境スナップショット（apply 直後）

| 項目              | 値                                                                                                  |
| ----------------- | --------------------------------------------------------------------------------------------------- |
| AWS アカウント    | 471147325833                                                                                        |
| リージョン        | ap-northeast-1                                                                                      |
| Realm             | `auth-poc`                                                                                          |
| **Public ALB**    | `https://auth-poc-kc-alb-595677258.ap-northeast-1.elb.amazonaws.com`                                |
| **Admin ALB**     | `https://auth-poc-kc-admin-alb-1711881233.ap-northeast-1.elb.amazonaws.com`                         |
| Internal ALB      | `http://internal-auth-poc-kc-internal-alb-122478092.ap-northeast-1.elb.amazonaws.com`（VPC 内のみ） |
| ECS Cluster       | `auth-poc-kc-cluster`                                                                               |
| ECS Service       | `auth-poc-kc-service`（desired=2 / Auto Scaling min=2 max=4）                                       |
| RDS               | `auth-poc-kc-db`（Multi-AZ=true, Secondary=ap-northeast-1c）                                        |
| Lambda Authorizer | `auth-poc-kc-vpc-authorizer`                                                                        |
| Admin パスワード  | `infra/keycloak/terraform.tfvars` の `keycloak_admin_password`                                      |

> ⚠️ **HTTPS 証明書は自己署名**（CN=`auth-poc-keycloak.poc.local`）。ブラウザでは警告画面を経由、curl では `-k` フラグ必須。本番では ACM 公開証明書 + Route 53 カスタムドメインに差し替える。

### ALB の役割分担

```
Public ALB (auth-poc-kc-alb)
  ├─ /realms/*/.well-known/*       → 全IP許可（OIDC Discovery、Lambda 等 Resource Server 用）
  ├─ /realms/*/protocol/.../certs  → 全IP許可（JWKS）
  └─ それ以外（ログイン画面、token endpoint 等）→ allowed_cidr_blocks の IP のみ

Admin ALB (auth-poc-kc-admin-alb)
  └─ /admin/*（Admin Console）   → SG レベルで管理者 IP のみ（L4 で遮断）

Internal ALB (auth-poc-kc-internal-alb)
  └─ /realms/*/protocol/.../certs → VPC 内のみ（Lambda VPC authorizer 用）
```

---

## 1. ブラウザ画面からの検証

### シナリオ A: HTTPS 化と自己署名証明書の警告

**目的**: Stage A-1 の HTTPS 終端が機能していることを確認。

**手順**:

1. ブラウザで `https://auth-poc-kc-alb-595677258.ap-northeast-1.elb.amazonaws.com/realms/auth-poc` を開く
2. 「接続はプライベートではありません」（Chrome）/「警告：潜在的なセキュリティリスク」（Firefox）が表示される
3. 「詳細設定」→「危険性を承知でアクセス」で続行

**期待結果**:

- 警告を超えると `{"realm":"auth-poc","public_key":"...","token-service":"https://.../protocol/openid-connect","account-service":"https://.../account","tokens-not-before":0}` のような JSON が表示される
- `token-service` / `account-service` が **`https://`** で発行されている → KC が ALB の TLS 終端を `X-Forwarded-Proto` で正しく認識している

**失敗時の確認**:

- HTTP `http://...` でアクセスしたら 301 Moved Permanently で `https://...` に redirect されるか
- ALB の 443 listener 状態: `aws elbv2 describe-listeners --load-balancer-arn $(aws elbv2 describe-load-balancers --names auth-poc-kc-alb --query 'LoadBalancers[0].LoadBalancerArn' --output text)`

---

### シナリオ B: Admin Console ログイン

**目的**: Admin ALB 経由で Keycloak Admin Console にアクセスできることを確認。

**前提**: あなたのグローバル IP が `infra/keycloak/terraform.tfvars` の `allowed_cidr_blocks` に含まれている（または `make ip-set-my-ip` で自動追加）。

**手順**:

1. ブラウザで `https://auth-poc-kc-admin-alb-1711881233.ap-northeast-1.elb.amazonaws.com/admin/master/console/` を開く
2. 自己署名警告を承認
3. ユーザー名 `admin` / パスワードは `terraform.tfvars` の `keycloak_admin_password` の値
4. ログイン後、左上のドロップダウンで `auth-poc` realm に切替

**期待結果**:

- Master realm でログイン成功 → Realm Selector に `auth-poc` が表示される
- `auth-poc` realm を選択すると Clients / Users / Realm Settings 等が見える
- Clients に `auth-poc-spa` / `auth-poc-backend` / `auth-poc-ssr` / `auth-poc-target-api` の 4 つが存在
- Users に `alice-kc` / `bob-kc` / `carol-kc` / `dave-kc` の 4 ユーザーが存在

**失敗時の確認**:

- IP が allowed_cidr_blocks に入っているか: `make ip-show`
- Admin SG の ingress 状態: `aws ec2 describe-security-groups --group-ids $(aws ec2 describe-security-groups --filters Name=group-name,Values=auth-poc-kc-alb-admin-sg --query 'SecurityGroups[0].GroupId' --output text) --query 'SecurityGroups[0].IpPermissions'`
- 必要なら `make ip-add IP=<あなたのIP>`

---

### シナリオ C: SPA（app-keycloak）からのログイン

**目的**: ローカル SPA から Authorization Code Flow + PKCE で AWS 上の Keycloak を認証バックエンドとして使えることを確認。

**手順**:

```bash
# 1. SPA の環境変数を AWS の Keycloak に向ける
cd /workspaces/aws-atuh-poc
make app-kc-env  # .env.local に terraform output から VITE_KEYCLOAK_AUTHORITY 等を書き出す

# 2. SPA 起動
make app-kc-dev  # → http://localhost:5174
```

3. ブラウザで `http://localhost:5174` を開く
4. 「Login with Keycloak」ボタン → 自動的に Keycloak ログイン画面（自己署名警告経由）に遷移
5. `alice-kc` / `password` （または realm-export.json のテストユーザーの password 値）でログイン
6. SPA に戻ってきて、ユーザー情報 + ID/Access Token が表示される

**期待結果**:

- 認証後、SPA がユーザーのトークンを受け取れている
- Access Token をデコード（jwt.io 等）すると以下のクレームが入っている:
  - `iss` = `https://auth-poc-kc-alb-.../realms/auth-poc`
  - `sub` = alice-kc の UUID
  - `tenant_id` = `acme-corp`
  - `realm_access.roles` に `employee` が含まれる
  - `preferred_username` = `alice-kc`

**失敗時の確認**:

- `.env.local` の `VITE_KEYCLOAK_AUTHORITY` が正しいか
- ブラウザのコンソールで CORS エラーが出ていないか → Keycloak Client の `Web Origins` に `http://localhost:5174` が登録されているか確認
- Public ALB が 443 で外向きに到達できるか: `curl -kIs https://auth-poc-kc-alb-.../realms/master | head -1` → `200 OK`

---

### シナリオ D: テストユーザー別の挙動確認

**目的**: マルチテナント claim マッピング（[claim-mapping-setup.md](../keycloak/claim-mapping-setup.md) Phase 8 の検証）が AWS 環境でも維持されていることを確認。

**手順**: シナリオ C と同じ手順を各ユーザーで実行し、Access Token のクレームを比較。

| ユーザー   | tenant_id  | roles    | 期待される操作                        |
| ---------- | ---------- | -------- | ------------------------------------- |
| `alice-kc` | acme-corp  | employee | 一般社員視点。経費申請のみ可能        |
| `bob-kc`   | acme-corp  | manager  | 承認操作が可能                        |
| `carol-kc` | acme-corp  | admin    | テナント管理画面アクセス可            |
| `dave-kc`  | globex-inc | manager  | bob-kc とは別テナント、データ分離確認 |

**期待結果**:

- 全ユーザーで `iss` / `aud` は同じ
- `tenant_id` がユーザー固有値で発行される
- `realm_access.roles` に Realm Role が正しく入る

---

## 2. OIDC エンドポイントの curl 検証

### シナリオ E: HTTP → HTTPS リダイレクト

```bash
curl -kIs http://auth-poc-kc-alb-595677258.ap-northeast-1.elb.amazonaws.com/realms/auth-poc | head -5
```

**期待結果**:

```
HTTP/1.1 301 Moved Permanently
Server: awselb/2.0
Location: https://auth-poc-kc-alb-.../realms/auth-poc:443
```

### シナリオ F: OIDC Discovery

```bash
ALB=auth-poc-kc-alb-595677258.ap-northeast-1.elb.amazonaws.com
curl -ks https://$ALB/realms/auth-poc/.well-known/openid-configuration | python3 -m json.tool | head -30
```

**期待結果**:

- `issuer`: `https://auth-poc-kc-alb-.../realms/auth-poc`
- `authorization_endpoint` / `token_endpoint` / `jwks_uri` / `userinfo_endpoint` 全て `https://` 始まり
- `grant_types_supported` に `urn:ietf:params:oauth:grant-type:token-exchange` が含まれる ← Stage A-3 で焼き付けた token-exchange-standard feature の証拠

### シナリオ G: JWKS（Public ALB と Internal ALB）

```bash
# 1. Public ALB（インターネット側）
curl -ks https://$ALB/realms/auth-poc/protocol/openid-connect/certs | python3 -m json.tool | head -20

# 2. Internal ALB（VPC 内のみ。Lambda VPC authorizer がこちらを参照）
# → ローカルからは到達不可。ECS Exec or 別の VPC 内 EC2 から検証
make kc-exec  # ECS task に入る
curl -s http://internal-auth-poc-kc-internal-alb-.../realms/auth-poc/protocol/openid-connect/certs
```

**期待結果**:

- 両 ALB で同じ `keys[]` が返る（同じ Keycloak バックエンド）
- `kid` が一致

---

## 3. Token Exchange (RFC 8693) 検証 — Stage A-3 の証跡

### シナリオ H: Client Credentials で initial token

```bash
ALB=auth-poc-kc-alb-595677258.ap-northeast-1.elb.amazonaws.com
INIT_TOKEN=$(curl -ks -X POST https://$ALB/realms/auth-poc/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=auth-poc-backend&client_secret=change-me-in-production" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo $INIT_TOKEN | cut -d. -f2 | base64 -d 2>/dev/null | python3 -m json.tool | head -20
```

**期待結果**:

- `aud` に `auth-poc-backend` 含まれる（initial token なので azp と一致）
- `azp = auth-poc-backend`
- `realm_access.roles` に backend の service account role

### シナリオ I: Token Exchange v2（audience 切替）

```bash
# initial token を auth-poc-target-api 向けに exchange
curl -ks -X POST https://$ALB/realms/auth-poc/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "grant_type=urn:ietf:params:oauth:grant-type:token-exchange" \
  --data-urlencode "client_id=auth-poc-backend" \
  --data-urlencode "client_secret=change-me-in-production" \
  --data-urlencode "subject_token=$INIT_TOKEN" \
  --data-urlencode "subject_token_type=urn:ietf:params:oauth:token-type:access_token" \
  --data-urlencode "audience=auth-poc-target-api" \
  | python3 -m json.tool
```

**期待結果**:

- レスポンスに `access_token` / `issued_token_type=urn:ietf:params:oauth:token-type:access_token`
- 取得した token をデコードすると **`aud = auth-poc-target-api`** ← オーディエンス切替成功
- `azp = auth-poc-backend`（発行元クライアントは backend のまま）
- これが Stage A-3 RFC 8693 標準準拠 Token Exchange の動作証跡

**失敗時の確認**:

- Client `auth-poc-backend` の Capability config で `Standard token exchange enabled` が ON か
- `KC_FEATURES=token-exchange-standard` が container に反映されているか: `make kc-exec` → `/opt/keycloak/bin/kc.sh show-config | grep features`

---

## 4. インフラ HA 検証

### シナリオ J: ECS task stop でフェイルオーバー

```bash
# 1. Running task の確認
aws ecs list-tasks --cluster auth-poc-kc-cluster --service-name auth-poc-kc-service \
  --region ap-northeast-1 --query 'taskArns'

# 2. 片方を停止
TASK=$(aws ecs list-tasks --cluster auth-poc-kc-cluster --service-name auth-poc-kc-service \
  --region ap-northeast-1 --query 'taskArns[0]' --output text)
aws ecs stop-task --cluster auth-poc-kc-cluster --task $TASK --region ap-northeast-1 \
  --query 'task.{lastStatus:lastStatus,stopCode:stopCode}'

# 3. 停止と並行して別ターミナルで継続的に discovery を叩く
while true; do
  curl -ks -w "%{http_code} %{time_total}s\n" -o /dev/null \
    https://auth-poc-kc-alb-595677258.ap-northeast-1.elb.amazonaws.com/realms/auth-poc
  sleep 1
done

# 4. ALB Target Health で UNHEALTHY → 新タスク → HEALTHY を観察
make kc-status
```

**期待結果**:

- task stop 直後: 残った 1 タスクで継続応答（200 OK）→ HA の威力
- 30-60 秒後: 新タスクが起動して target healthy 復帰
- 100% リクエスト 200 が返り続ける（瞬間的な 502/503 が出る可能性はある）

### シナリオ K: ECS service kill → 自動回復

```bash
# 2 タスクとも停止
for t in $(aws ecs list-tasks --cluster auth-poc-kc-cluster --service-name auth-poc-kc-service \
  --region ap-northeast-1 --query 'taskArns[]' --output text); do
  aws ecs stop-task --cluster auth-poc-kc-cluster --task $t --region ap-northeast-1 --no-cli-pager
done

# サービス停止状態の観察
make kc-status

# 一時的に 503 が返る
curl -kIs https://auth-poc-kc-alb-595677258.ap-northeast-1.elb.amazonaws.com/realms/auth-poc

# ECS service が desired=2 を維持しようとして自動再起動
aws ecs wait services-stable --cluster auth-poc-kc-cluster --services auth-poc-kc-service --region ap-northeast-1
```

**期待結果**:

- 停止直後は 503 が返る期間が約 1-2 分
- desired=2 に向けて ECS が自動的に新タスクを起動
- 2-5 分で完全復旧

### シナリオ L: RDS フェイルオーバー手動実行

```bash
# Multi-AZ 設定確認
aws rds describe-db-instances --db-instance-identifier auth-poc-kc-db \
  --region ap-northeast-1 \
  --query 'DBInstances[0].{MultiAZ:MultiAZ,Primary:AvailabilityZone,Secondary:SecondaryAvailabilityZone}'

# フェイルオーバー実行（数分間 DB 接続が中断）
aws rds reboot-db-instance --db-instance-identifier auth-poc-kc-db \
  --force-failover --region ap-northeast-1

# Keycloak 側の挙動を観察（ログイン試行）
ALB=auth-poc-kc-alb-595677258.ap-northeast-1.elb.amazonaws.com
while true; do
  RESULT=$(curl -ks -o /dev/null -w "%{http_code}" https://$ALB/realms/auth-poc)
  echo "$(date +%H:%M:%S) $RESULT"
  sleep 2
done

# Keycloak のログで再接続を確認
make kc-logs
```

**期待結果**:

- フェイルオーバー中（60-120 秒程度）: 一時的に 503 や DB エラーが出る
- Keycloak ログに `JDBC Connection Lost` → `Reconnected` の遷移が見える
- Primary AZ と Secondary AZ が入れ替わる（再度 describe-db-instances で確認）
- 完了後はサービス完全復旧

### シナリオ M: Infinispan セッション共有（HA クラスタ動作確認）

**目的**: 2 タスク間でセッションキャッシュが共有されることを確認 → Sticky Session 不要の証跡。

**手順**:

```bash
# 1. ログイン
ALB=auth-poc-kc-alb-595677258.ap-northeast-1.elb.amazonaws.com
SESSION=$(curl -ks -c /tmp/kc-cookies.txt -b /tmp/kc-cookies.txt \
  -X POST https://$ALB/realms/auth-poc/protocol/openid-connect/token \
  -d "grant_type=password&client_id=auth-poc-spa&username=alice-kc&password=password" \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('refresh_token',''))")

# 2. 片方の task に target を絞り込んで refresh
# （ALB は round-robin なので複数回呼べば両 task に当たる）
for i in 1 2 3 4 5; do
  RESULT=$(curl -ks -X POST https://$ALB/realms/auth-poc/protocol/openid-connect/token \
    -d "grant_type=refresh_token&client_id=auth-poc-spa&refresh_token=$SESSION" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('access_token','ERROR')[:30])")
  echo "Try $i: $RESULT"
done
```

**期待結果**:

- 5 回連続でリフレッシュトークンが受け取れる（どの task が処理しても同じ refresh token で OK）
- 失敗例: 1 回目は成功するが 2 回目以降エラー → セッション共有失敗（Infinispan が動いていない）

**追加確認**: Keycloak の Admin Console で Sessions タブを開き、`alice-kc` のセッションが 1 つだけ（同一ユーザー）であることを確認。

### シナリオ N: Infinispan クラスタビュー直接確認

```bash
# Container 内のログから直接確認
aws logs filter-log-events --log-group-name /ecs/auth-poc-kc --region ap-northeast-1 \
  --start-time $(($(date +%s) * 1000 - 60 * 60 * 1000)) \
  --filter-pattern 'ISPN000094' \
  --query 'events[-3:].[timestamp,message]' --output text
```

**期待結果**: 最新の cluster view が `(2) [ip-X, ip-Y]` の形（2 ノード参加）になっている。

---

## 5. ALB ルーティングと Lambda 連携

### シナリオ O: Public ALB のパスベース IP 制限

```bash
ALB=auth-poc-kc-alb-595677258.ap-northeast-1.elb.amazonaws.com

# 1. JWKS は全 IP 許可（Lambda 等の Resource Server からアクセス可能想定）
curl -ksI https://$ALB/realms/auth-poc/protocol/openid-connect/certs | head -1
# 期待: HTTP/1.1 200 OK

# 2. login page は IP 制限あり
curl -ksI https://$ALB/realms/auth-poc/account | head -1
# 期待: あなたの IP が allowed_cidr_blocks にあれば 200、なければ 403 / Forbidden
```

### シナリオ P: Internal ALB → Lambda VPC Authorizer

**目的**: ADR-012 の「VPC 内 Lambda が Internal ALB 経由で JWKS を取って JWT 検証する」フローを確認。

```bash
# Lambda invoke（API Gateway 経由）または直接 invoke
# 認証付き API Gateway endpoint を叩いて Lambda authorizer が JWT を verify するかを観察

# 1. Token 取得
ALB_PUB=auth-poc-kc-alb-595677258.ap-northeast-1.elb.amazonaws.com
TOKEN=$(curl -ks -X POST https://$ALB_PUB/realms/auth-poc/protocol/openid-connect/token \
  -d "grant_type=password&client_id=auth-poc-spa&username=alice-kc&password=password" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 2. API Gateway 経由で Lambda invoke（API Gateway の Authorizer が attach されていれば）
# infra 側の output から取得（Tokyo stack）:
cd /workspaces/aws-atuh-poc/infra
API_URL=$(terraform output -raw api_url 2>/dev/null || echo "（要確認）")
curl -s -H "Authorization: Bearer $TOKEN" "$API_URL/expenses"

# 3. Lambda authorizer のログで JWT 検証成功を確認
aws logs tail /aws/lambda/auth-poc-kc-vpc-authorizer --since 5m --region ap-northeast-1
```

**期待結果**:

- Lambda が JWKS を Internal ALB から取得（VPC 内通信、インターネット不要）
- JWT signature 検証成功
- 期待されるクレーム（`iss`, `aud`, `exp`, `tenant_id`）が抽出されて API Gateway に context として渡る

---

## 6. 監視 / 運用観点

### シナリオ Q: CloudWatch Logs 確認

```bash
# Keycloak アプリケーションログ（ECS task）
make kc-logs LOG_SINCE=30m

# Lambda authorizer ログ
make logs-authorizer LOG_SINCE=30m

# ECS Service event（rolling deployment 履歴）
aws ecs describe-services --cluster auth-poc-kc-cluster --services auth-poc-kc-service \
  --region ap-northeast-1 --query 'services[0].events[0:10].[createdAt,message]' --output text
```

### シナリオ R: Auto Scaling の動作確認

```bash
# 現在の Auto Scaling target / policy
aws application-autoscaling describe-scalable-targets --service-namespace ecs \
  --region ap-northeast-1 \
  --query 'ScalableTargets[?ResourceId==`service/auth-poc-kc-cluster/auth-poc-kc-service`]'

aws application-autoscaling describe-scaling-policies --service-namespace ecs \
  --region ap-northeast-1 \
  --query 'ScalingPolicies[?ResourceId==`service/auth-poc-kc-cluster/auth-poc-kc-service`].{Name:PolicyName,Type:PolicyType,Target:TargetTrackingScalingPolicyConfiguration.TargetValue}'

# 負荷をかけて Scale-out を観察（要注意：本番想定の負荷ではない）
ALB=auth-poc-kc-alb-595677258.ap-northeast-1.elb.amazonaws.com
ab -n 5000 -c 50 https://$ALB/realms/auth-poc/.well-known/openid-configuration
# → CloudWatch でメトリクス確認: ECSServiceAverageCPUUtilization
```

### シナリオ S: コスト確認

```bash
# 今月の ECS / RDS コスト試算
aws ce get-cost-and-usage \
  --time-period Start=$(date -d 'first day of this month' +%Y-%m-%d),End=$(date +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics UnblendedCost \
  --filter '{"Tags":{"Key":"Name","Values":["auth-poc-kc-*"]}}' \
  --group-by Type=DIMENSION,Key=SERVICE
# 期待: ECS Fargate + RDS で合計 $90-100/月 程度（Multi-AZ + 2 task 常時稼働）
```

---

## 7. 既知の課題と対応指針

### 課題 1: 自己署名証明書のブラウザ警告

- **影響**: SPA / Admin Console のアクセスごとに警告画面を経由
- **PoC 内では**: ブラウザで「危険性を承知で続行」を選択 / curl は `-k`
- **本番対応**: ACM 公開証明書 + Route 53 カスタムドメイン（`auth.<your-domain>`）に差し替え。`infra/keycloak/tls.tf` を削除し、`alb.tf` の `certificate_arn` を公開証明書 ARN に変更

### 課題 2: ECS rolling update 中の一時的 singleton

- **症状**: rolling deployment 中、新タスクが JGroups の stale entry を発見して JOIN 試行 → timeout → singleton 化することがある
- **影響**: 一時的に Infinispan キャッシュ共有が切れる（数十秒）
- **対応指針**:
  - 検証時は `desired=0 → 2` の fresh restart で確実にクラスタ形成
  - 本番では Keycloak の JDBC_PING パラメータ（`info_writer_sleep_time` 短縮 / `clear_table_on_view_change`）の tuning、または ECS preStop hook で JGROUPSPING テーブルの自分の行を削除する処理を追加

### 課題 3: SG state drift（要次回 plan 時に対処）

- **症状**: ECS SG の port 7800 ルール（`aws_security_group_rule.ecs_jgroups_{ingress,egress}`）が terraform state と AWS 実態で ID 不整合
- **応急対処済み**: AWS CLI で手動再追加（ingress=`sgr-00445aede27a1815e`, egress=`sgr-06a9de8cbcb2a8dde`）
- **本格対応**: 次回 `terraform plan` で drift を確認し、`terraform state rm` → `terraform import` で正規化、または同等ルールの replace として apply

### 課題 4: `aws_lb_listener.http` の deprecation warning

- **症状**: `default_action[0].fixed_response cannot be specified when default_action[0].type is "redirect"`
- **影響**: 実害なし（state に旧 fixed_response が残るが現在の動作は redirect のみ）
- **対応**: 次回 plan で `fixed_response` ブロックが state から落ちることを確認、または `terraform refresh` で正規化

### 課題 5: `--import-realm` の skip 動作 — Stage A 反映で実機ヒット

- **症状**: 新 image (KC 26.2 + 更新済 realm.json) を ECR push して ECS で起動しても、**既存 realm が DB に残っていると import が skip され、新設定が反映されない**
  - 例: Token Exchange v2 (`auth-poc-target-api` client、`standard.token.exchange.enabled` 属性) を curl すると `invalid_client: Audience not found`
  - Admin REST API で realm を確認すると **`auth-poc-target-api` クライアント自体が存在しない**
- **原因**: Keycloak の `--import-realm` フラグは既存 realm を上書きしない仕様（デフォルト）
- **対処方針**: 詳細は [keycloak/config/README.md](../../keycloak/config/README.md) の「既存 realm が存在する環境での `--import-realm` の挙動」セクション参照
  - **本番**: Partial Import + PR ベース運用（Admin Console 直接変更禁止）
  - **PoC リフレッシュ**: realm DELETE → ECS force-new-deployment で fresh import

### 課題 6: terraform output が `http://` のまま

- **症状**: `outputs.tf` の `keycloak_url` 系が `http://` 始まり
- **影響**: SPA の `make app-kc-env` で出力される `.env.local` も `http://` になる → ブラウザで HTTPS にリダイレクトされるが、初回アクセスが余分に redirect する
- **対応**: `infra/keycloak/outputs.tf` で `https://` 始まりに変更（次回コミットで対応）

---

## 8. 検証時のクイックリファレンス

```bash
# 最頻出 3 コマンド
make kc-status     # ECS / ALB / RDS の状態
make kc-logs       # Keycloak アプリログ tail
make kc-admin-url  # Admin Console の URL を表示

# IP 制限
make ip-show       # 現在の許可 IP 一覧
make ip-set-my-ip  # 自分のグローバル IP を allowed_cidr_blocks に追加

# Token Exchange の最短再現コマンド
ALB=auth-poc-kc-alb-595677258.ap-northeast-1.elb.amazonaws.com
INIT=$(curl -ks -X POST https://$ALB/realms/auth-poc/protocol/openid-connect/token \
  -d "grant_type=client_credentials&client_id=auth-poc-backend&client_secret=change-me-in-production" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
curl -ks -X POST https://$ALB/realms/auth-poc/protocol/openid-connect/token \
  --data-urlencode "grant_type=urn:ietf:params:oauth:grant-type:token-exchange" \
  --data-urlencode "client_id=auth-poc-backend" \
  --data-urlencode "client_secret=change-me-in-production" \
  --data-urlencode "subject_token=$INIT" \
  --data-urlencode "subject_token_type=urn:ietf:params:oauth:token-type:access_token" \
  --data-urlencode "audience=auth-poc-target-api" | python3 -m json.tool

# Stage A 完全停止（コスト節約）
make tf-destroy-kc  # ALB + ECS + RDS + ECR の全削除

# Stage A 一時停止（最小コスト維持）
aws ecs update-service --cluster auth-poc-kc-cluster --service auth-poc-kc-service --desired-count 0 --region ap-northeast-1
aws rds stop-db-instance --db-instance-identifier auth-poc-kc-db --region ap-northeast-1
# → 再開: --desired-count 2 / start-db-instance（7 日経過すると自動で起動するので注意）
```
