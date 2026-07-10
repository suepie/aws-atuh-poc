# 実行手順書：JIT ユーザ削除 + SCIM 実装可能性検証（V1/V2/V3'）

> **前提**: [README.md](../README.md) の PoC 計画を理解済み
> **想定時間**: 3-4 時間（環境構築 1h + 検証 2h + 手動確認 1h）
> **一次資料**: [jit-scim §10.4.E](../../../doc/common/jit-scim-coexistence-keycloak.md) 14 件

---

## 0. 前提環境の確認

### 0.1 必要ツール

```bash
docker --version           # Docker 24+ 推奨
docker compose version     # v2 系
java -version              # OpenJDK 17 (SPI ビルド用)
mvn --version              # Maven 3.9+
jq --version               # JSON 処理
curl --version             # HTTP テスト
```

### 0.2 ポート衝突確認

本 PoC で使用するポート:
- `18080`: Keycloak PoC 環境（既存 PoC の 8080 を回避）
- `15432`: PostgreSQL PoC 環境（既存 PoC の 5432 を回避）

```bash
lsof -i :18080  # 未使用であること
lsof -i :15432  # 未使用であること
```

衝突する場合は `docker-compose.yml` のポート番号を変更。

---

## 1. Day 1: 環境構築（1 時間）

### 1.1 Docker Compose 起動

```bash
cd /Users/suepie/Develop/10_project/aws-atuh-poc/poc/jit-scim-verification-2026-07-10/

# 起動
docker compose up -d

# ログ確認（Keycloak 起動完了まで 1-2 分）
docker compose logs -f keycloak
# → "Keycloak XX.X.X started" を待つ
```

### 1.2 Keycloak 起動確認

```bash
# ヘルスチェック
curl http://localhost:18080/realms/master
# → 200 OK が返ること

# Admin Console アクセス確認
open http://localhost:18080/admin/
# → ログイン: admin / admin_poc_2026
```

### 1.3 PoC Realm インポート確認

```bash
# poc-jit-scim Realm が作成されているか
curl -s http://localhost:18080/realms/poc-jit-scim/.well-known/openid-configuration | jq .issuer
# → "http://localhost:18080/realms/poc-jit-scim" が返る

# テストユーザ確認
docker compose exec keycloak \
    /opt/keycloak/bin/kcadm.sh config credentials \
    --server http://localhost:8080 \
    --realm master --user admin --password admin_poc_2026

docker compose exec keycloak \
    /opt/keycloak/bin/kcadm.sh get users -r poc-jit-scim \
    --fields username,enabled,attributes
```

期待結果:
- `test-jit-user`（provisioned_by=jit）
- `test-scim-user`（provisioned_by=scim, scim_active=true）
- `test-inactive-jit`（provisioned_by=jit, last_login=2023-08-11 頃）

### 1.4 SCIM Realm API 有効化確認

```bash
# feature 'scim-realm-api' が有効か
curl -s http://localhost:18080/admin/serverinfo \
    -H "Authorization: Bearer $(./tests/get-token.sh)" \
    | jq '.features | map(select(.name == "scim-realm-api"))'
```

（`.features` 内に該当エントリがあれば OK）

---

## 2. Day 2: V1 + V2 実施（2 時間）

### 2.1 SPI JAR ビルド（V3' 準備）

```bash
cd spi/last-login-tracker
./build.sh

# 成果物確認
ls -la target/last-login-tracker.jar
```

### 2.2 SPI JAR デプロイ（Keycloak 再起動）

```bash
cd ../..
docker compose restart keycloak

# SPI ロード確認
docker compose logs keycloak 2>&1 | grep -i last-login-tracker
```

### 2.3 V1 実行

```bash
chmod +x tests/*.sh
./tests/v1-metatavu-scim.sh 2>&1 | tee docs/v1-log-$(date +%Y%m%d-%H%M).txt
```

### 2.4 V2 実行

```bash
./tests/v2-sync-mode-override.sh 2>&1 | tee docs/v2-log-$(date +%Y%m%d-%H%M).txt
```

---

## 3. Day 3: V3' 実施 + 総合判定（1 時間）

### 3.1 V3' 実行（半自動）

```bash
./tests/v3-custom-authenticator.sh 2>&1 | tee docs/v3-log-$(date +%Y%m%d-%H%M).txt
```

### 3.2 手動確認（Browser Flow）

Direct Access Grant では Browser Flow を通らないため、以下の手動確認が必要:

1. **Admin Console にログイン**
   ```
   http://localhost:18080/admin/
   → poc-jit-scim Realm 選択
   ```

2. **Realm Settings → Bindings → Browser Flow を変更**
   ```
   Browser Flow: browser-with-last-login
   Save
   ```

3. **Account Console にブラウザでログイン**
   ```
   http://localhost:18080/realms/poc-jit-scim/account
   → test-jit-user / test123 でログイン
   ```

4. **user_attribute.last_login 確認**
   ```bash
   TOKEN=$(./tests/get-token.sh)
   USER_ID=$(curl -s "http://localhost:18080/admin/realms/poc-jit-scim/users?username=test-jit-user&exact=true" \
             -H "Authorization: Bearer $TOKEN" | jq -r '.[0].id')
   curl -s "http://localhost:18080/admin/realms/poc-jit-scim/users/$USER_ID" \
        -H "Authorization: Bearer $TOKEN" | jq '.attributes'
   ```

5. **期待結果**
   ```json
   {
     "provisioned_by": ["jit"],
     "last_login": ["<現在の epoch ms>"]
   }
   ```

---

## 4. 検証結果ログの作成

すべての V が終わったら [docs/verification-log.md](verification-log.md) にサマリを記載:

```markdown
# 検証結果ログ 2026-07-XX

## V1: Metatavu SCIM Custom Attribute
- Test 1: [OK/NG]
- Test 2: [OK/NG]
- Test 3: [OK/NG]
- Test 4: [OK/NG]
- 判定: [PASS / FAIL / PARTIAL]
- Fallback 選定: [不要 / 代替 A / 代替 B / 代替 C]

## V2: Sync Mode Override
（同上）

## V3': Custom Authenticator SPI
（同上）

## Phase 1 実装への影響
- SCIM プラグイン: [Metatavu / Native / 代替]
- SPI 実装: [案 A / 案 B / 案 C]
- 追加工数: [なし / +Xw]
```

---

## 5. トラブルシューティング

### 5.1 Keycloak が起動しない

```bash
docker compose logs keycloak | tail -50

# よくある原因:
# - KC_FEATURES の値が不正 → docker-compose.yml 確認
# - PostgreSQL 未起動 → docker compose ps
# - Port 18080 衝突 → lsof -i :18080
```

### 5.2 SCIM Realm API が 404

```bash
# feature 有効化確認
docker compose exec keycloak env | grep KC_FEATURES

# Feature Preview 一覧確認（26.6 の SCIM Experimental）
# https://www.keycloak.org/2026/04/scim-as-experimental-feature
```

### 5.3 SPI がロードされない

```bash
# JAR が正しく配置されているか
docker compose exec keycloak ls -la /opt/keycloak/providers/

# JAR 内の META-INF/services 確認
unzip -p spi/last-login-tracker/target/last-login-tracker.jar \
    META-INF/services/org.keycloak.authentication.AuthenticatorFactory
# → com.example.keycloak.spi.LastLoginTrackerAuthenticatorFactory が出力される

# Keycloak 再起動
docker compose restart keycloak

# ログで確認
docker compose logs keycloak 2>&1 | grep -i "last-login-tracker"
```

### 5.4 環境完全リセット

```bash
docker compose down -v
docker compose up -d
```

---

## 6. 完了後

### 6.1 環境停止

```bash
docker compose stop
```

### 6.2 検証結果を親ドキュメントに反映

- **[jit-scim §10.4.F](../../../doc/common/jit-scim-coexistence-keycloak.md)** に検証結果セクション追加（V1/V2/V3' 各判定 + Fallback 選定）
- **[hearing-checklist B-SCIM-7/8/9/10](../../../doc/requirements/hearing-checklist.md)** の状態を ⏳ から済み（✅ or ⚠ or ❌）に更新
- **[ADR-025 §I.2](../../../doc/adr/025-scim-positioning-and-receive-stance.md)** の PoC 検証結果を反映

### 6.3 環境完全削除

```bash
docker compose down -v
docker rmi quay.io/keycloak/keycloak:26.6 postgres:16-alpine  # optional
```

---

## 7. 参考コマンド

### 7.1 Admin Token 取得ヘルパー

```bash
cat > tests/get-token.sh << 'EOF'
#!/bin/bash
curl -s -X POST "http://localhost:18080/realms/master/protocol/openid-connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "grant_type=password&client_id=admin-cli&username=admin&password=admin_poc_2026" \
    | jq -r '.access_token'
EOF
chmod +x tests/get-token.sh
```

### 7.2 全ユーザ属性ダンプ

```bash
TOKEN=$(./tests/get-token.sh)
curl -s "http://localhost:18080/admin/realms/poc-jit-scim/users" \
    -H "Authorization: Bearer $TOKEN" \
    | jq '.[] | {username, enabled, attributes}'
```
