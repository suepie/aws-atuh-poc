# 別端末での PoC 実行手順（受け取り側向け Quick Start）

> **想定**: この PoC 一式（`poc/jit-scim-verification-2026-07-10/`）を別端末に持ち込んで実行する
> **想定所要時間**: 環境準備 30 分 + 検証実施 2-3 時間 = 計 3-4 時間
> **背景**: [../../doc/common/jit-scim-coexistence-keycloak.md §10.4.E](../../doc/common/jit-scim-coexistence-keycloak.md) の 14 件一次資料

---

## 0. 事前準備（Prerequisites）

### 0.1 必要ツール（バージョン確認コマンド付き）

別端末に以下がインストール済みであることを確認してください:

```bash
# 必須ツール
docker --version           # Docker 24.0+ 推奨
docker compose version     # Compose v2 系（v1 は非対応）
java -version              # OpenJDK 17 以上
mvn --version              # Maven 3.9+
jq --version               # jq 1.6+
curl --version             # curl 7.x+

# あれば便利
unzip --version            # JAR 内容確認用
```

**未インストールの場合**：

- **macOS**: `brew install --cask docker openjdk@17 && brew install maven jq`
- **Ubuntu/Debian**: `sudo apt install docker.io docker-compose-plugin openjdk-17-jdk maven jq`
- **Windows**: Docker Desktop + WSL2 + Ubuntu 環境を推奨

### 0.2 ポート衝突確認

本 PoC で使用するポート:

- `18080`: Keycloak PoC
- `15432`: PostgreSQL PoC

以下で未使用確認:

```bash
# macOS / Linux
lsof -i :18080 || echo "OK: 18080 free"
lsof -i :15432 || echo "OK: 15432 free"

# Windows (PowerShell)
Get-NetTCPConnection -LocalPort 18080 -ErrorAction SilentlyContinue
Get-NetTCPConnection -LocalPort 15432 -ErrorAction SilentlyContinue
```

**衝突する場合**：`docker-compose.yml` のポート番号を変更（`18080:8080` → `28080:8080` 等）。

### 0.3 リソース要件

- **メモリ**: 4GB 以上（Keycloak 2GB + PostgreSQL 512MB + Maven ビルド 1GB）
- **ディスク**: 5GB 以上（Docker Image 2GB + Maven `.m2` cache 1-2GB）

---

## 1. ファイル転送（元端末 → 別端末）

### 1.1 転送対象

**`poc/jit-scim-verification-2026-07-10/` ディレクトリ一式**（14 ファイル、約 100KB）

```
poc/jit-scim-verification-2026-07-10/
├── README.md
├── QUICKSTART-OTHER-MACHINE.md  ← 本書
├── docker-compose.yml
├── config/
│   └── realm-poc.json
├── spi/last-login-tracker/
│   ├── pom.xml
│   ├── build.sh
│   └── src/main/…（Java + META-INF）
├── tests/
│   ├── common.sh
│   ├── v1-metatavu-scim.sh
│   ├── v2-sync-mode-override.sh
│   └── v3-custom-authenticator.sh
└── docs/
    ├── execution-guide.md
    └── verification-log.md
```

### 1.2 転送方法（3 択）

#### 方法 A: tarball で転送（推奨、シンプル）

**元端末**（Mac）:

```bash
cd /Users/suepie/Develop/10_project/aws-atuh-poc/
tar -czf poc-jit-scim-2026-07-10.tar.gz poc/jit-scim-verification-2026-07-10/
ls -lh poc-jit-scim-2026-07-10.tar.gz  # サイズ確認
```

→ USB / AirDrop / メール添付 / クラウド（Google Drive / OneDrive 等）で別端末へ

**別端末**:

```bash
mkdir -p ~/poc-workspace && cd ~/poc-workspace
tar -xzf poc-jit-scim-2026-07-10.tar.gz
cd poc/jit-scim-verification-2026-07-10/
ls
```

#### 方法 B: Git 経由

**元端末**:

```bash
cd /Users/suepie/Develop/10_project/aws-atuh-poc/
git add poc/jit-scim-verification-2026-07-10/
git commit -m "PoC: JIT/SCIM verification env 2026-07-10"
git push
```

**別端末**:

```bash
git clone <repo-url>
cd aws-atuh-poc/poc/jit-scim-verification-2026-07-10/
```

#### 方法 C: rsync（同一ネットワーク時）

```bash
# 元端末から別端末へ
rsync -avz poc/jit-scim-verification-2026-07-10/ \
    user@other-host:~/poc-workspace/poc-jit-scim/
```

### 1.3 実行権限の確認

**別端末**：転送後、実行権限を再付与:

```bash
cd ~/poc-workspace/poc/jit-scim-verification-2026-07-10/  # 転送先ディレクトリに移動
chmod +x tests/*.sh spi/last-login-tracker/build.sh
ls -la tests/  # rwx が付いているか確認
```

---

## 2. 環境起動（別端末で実施）

### 2.1 Docker Compose 起動

```bash
cd ~/poc-workspace/poc/jit-scim-verification-2026-07-10/

# 起動（バックグラウンド）
docker compose up -d

# 起動確認（1-2 分待機）
docker compose ps
# → poc-postgres-16、poc-keycloak-266 の 2 コンテナが Up (healthy)

# ログ確認（Keycloak 完全起動まで）
docker compose logs -f keycloak
# → "Keycloak 26.6.X started" が出るまで待つ（Ctrl+C で抜ける）
```

### 2.2 Keycloak 疎通確認

```bash
# ヘルスチェック（HTTP 200 が返ること）
curl -o /dev/null -w "%{http_code}\n" http://localhost:18080/realms/master
# → 200

# PoC Realm 疎通確認
curl -s http://localhost:18080/realms/poc-jit-scim/.well-known/openid-configuration | jq .issuer
# → "http://localhost:18080/realms/poc-jit-scim"

# Admin Console ブラウザアクセス（オプション）
# URL: http://localhost:18080/admin/
# ID:  admin
# PW:  admin_poc_2026
```

### 2.3 テストユーザ確認

```bash
# 共通スクリプトを source（環境変数設定）
source tests/common.sh

# Admin token 取得
TOKEN=$(get_admin_token)
echo "Token: ${TOKEN:0:20}..."

# ユーザ一覧
curl -s "http://localhost:18080/admin/realms/poc-jit-scim/users" \
    -H "Authorization: Bearer $TOKEN" | jq '.[] | {username, enabled, attributes}'
```

**期待出力**：以下 3 ユーザが表示される
- `test-jit-user`（provisioned_by: jit）
- `test-scim-user`（provisioned_by: scim, scim_active: true）
- `test-inactive-jit`（provisioned_by: jit, last_login: 過去日）

---

## 3. SPI ビルド + デプロイ

### 3.1 Custom Authenticator SPI ビルド

```bash
cd spi/last-login-tracker/
./build.sh
```

**期待出力**：`✅ Build successful` + `target/last-login-tracker.jar`

**エラー時**：
- `mvn: command not found` → Maven 未インストール
- `java: command not found` → OpenJDK 17 未インストール
- ダウンロード遅い → `~/.m2/settings.xml` にプロキシ設定確認

### 3.2 SPI JAR デプロイ（Keycloak 再起動）

```bash
cd ~/poc-workspace/poc/jit-scim-verification-2026-07-10/
docker compose restart keycloak

# SPI ロード確認（数秒待つ）
sleep 30
docker compose logs keycloak 2>&1 | grep -i "last-login-tracker"
# → "Registered ... last-login-tracker" のような出力
```

---

## 4. 検証実施

### 4.1 V1: SCIM Custom Attribute Mapping

```bash
cd ~/poc-workspace/poc/jit-scim-verification-2026-07-10/
./tests/v1-metatavu-scim.sh 2>&1 | tee docs/v1-log-$(date +%Y%m%d-%H%M).txt
```

**確認するポイント**：
- Test 1: SCIM Realm API が有効か（HTTP 200 が期待）
- Test 2: 標準属性（active → enabled）反映
- Test 3: **カスタム属性（scim_active, provisioned_by）が書けるか** ← ここが重要
- Test 4: SCIM PATCH で active=false 反映

**結果例**：
- `[OK] user_attribute.scim_active = true` → V1 PASS ✅
- `[WARN] user_attribute.scim_active が設定されていない` → **V1 FAIL、Fallback A 発動**

### 4.2 V2: Sync Mode Override

```bash
./tests/v2-sync-mode-override.sh 2>&1 | tee docs/v2-log-$(date +%Y%m%d-%H%M).txt
```

**確認するポイント**：
- Test 3: Mapper 単位 `syncMode = IMPORT` の設定作成
- Test 4: 設定が正しく保存されているか（`syncMode = IMPORT` が返る）

**結果例**：
- `[OK] syncMode = IMPORT が Mapper 設定に保存されている` → V2 PASS ✅
- `[ERROR] syncMode = xxx（期待: IMPORT）` → V2 FAIL、Realm 全体 IMPORT 化検討

### 4.3 V3': Custom Authenticator SPI

```bash
./tests/v3-custom-authenticator.sh 2>&1 | tee docs/v3-log-$(date +%Y%m%d-%H%M).txt
```

**確認するポイント**：
- Test 1: SPI がロードされているか
- Test 2: Browser Flow への追加成功

**手動確認（必須）**：Direct Access Grant は Browser Flow を通らないので、以下を手動実施:

```
1. ブラウザで http://localhost:18080/admin/ にアクセス
2. Realm: poc-jit-scim に切替
3. Authentication → Flows → Bindings タブ
4. "Browser Flow" を "browser-with-last-login" に変更 → Save
5. 新しいブラウザ（Incognito）で:
   http://localhost:18080/realms/poc-jit-scim/account
6. test-jit-user / test123 でログイン
7. 元のターミナルで再度確認:
```

```bash
source tests/common.sh
TOKEN=$(get_admin_token)
USER_ID=$(find_user_id "$TOKEN" "test-jit-user")
LAST_LOGIN=$(get_user_attribute "$TOKEN" "$USER_ID" "last_login")
echo "last_login = $LAST_LOGIN"
```

**結果例**：
- `last_login = 17XXXXXXXXXXX`（現在時刻の epoch ms）→ **V3' PASS ✅、案 B 採用確定**
- `last_login = NULL` → V3' FAIL、案 A（enlistAfterCompletion）or 案 C（外部 DB）検討

---

## 5. 結果ログの記録

### 5.1 verification-log.md に転記

`docs/verification-log.md` の `⏳` を実際の結果で埋めます:

```bash
# エディタで開く
nano docs/verification-log.md
# または
code docs/verification-log.md
```

**記入項目**（各 Test の Result 欄）：
- ✅ PASS
- ❌ FAIL
- ⚠ PARTIAL

**各 V の判定サマリ**（総合 + Fallback 選定 + Phase 1 影響）も記入。

### 5.2 各テストログの保存

`tests/*.sh` 実行時に `tee docs/vX-log-*.txt` で自動保存されているログを確認:

```bash
ls -la docs/v*-log-*.txt
```

---

## 6. 結果を元端末に持ち帰る

### 6.1 成果物の抽出

```bash
cd ~/poc-workspace/poc/jit-scim-verification-2026-07-10/
tar -czf ../poc-results-$(date +%Y%m%d).tar.gz \
    docs/verification-log.md \
    docs/v*-log-*.txt \
    spi/last-login-tracker/target/last-login-tracker.jar
ls -lh ../poc-results-*.tar.gz
```

### 6.2 元端末（Mac）で反映

USB / メール / クラウド経由で `poc-results-*.tar.gz` を持ち帰り:

```bash
cd /Users/suepie/Develop/10_project/aws-atuh-poc/poc/jit-scim-verification-2026-07-10/
tar -xzf ~/Downloads/poc-results-*.tar.gz -C .

# 検証結果を確認
cat docs/verification-log.md
```

---

## 7. 環境クリーンアップ（別端末）

### 7.1 コンテナ停止

```bash
cd ~/poc-workspace/poc/jit-scim-verification-2026-07-10/
docker compose down  # 停止（volume 保持）
```

### 7.2 完全削除

```bash
# volume も削除
docker compose down -v

# イメージも削除
docker rmi quay.io/keycloak/keycloak:26.6 postgres:16-alpine

# ディレクトリごと
cd ~ && rm -rf ~/poc-workspace/
```

---

## 8. トラブルシューティング

### 8.1 Keycloak が起動しない

```bash
docker compose logs keycloak | tail -100

# よくある原因
```

| 症状 | 原因 | 対処 |
|---|---|---|
| `KC_FEATURES` エラー | 26.6 で feature 名が変わった | `docker-compose.yml` の KC_FEATURES を確認、`--help` で最新機能名確認 |
| `Connection refused` postgres | Postgres 未起動 | `docker compose logs postgres` |
| Port 衝突 | 18080 or 15432 使用中 | `docker-compose.yml` のポート変更 |
| メモリ不足 | Docker Desktop の割当不足 | Docker Desktop → Settings → Resources で 4GB 以上に |

### 8.2 SCIM API が 404

```bash
# feature 有効確認
docker compose exec keycloak env | grep KC_FEATURES

# 26.6 で正しい feature 名は "scim-realm-api"
# もし違う場合は https://www.keycloak.org/2026/04/scim-as-experimental-feature 確認

# Keycloak 起動時に有効化された feature 一覧
docker compose logs keycloak 2>&1 | grep -i "feature.*enabled"
```

### 8.3 SPI がロードされない

```bash
# JAR が providers ディレクトリに配置されているか
docker compose exec keycloak ls -la /opt/keycloak/providers/

# JAR 内の META-INF/services 確認
unzip -p spi/last-login-tracker/target/last-login-tracker.jar \
    META-INF/services/org.keycloak.authentication.AuthenticatorFactory

# → "com.example.keycloak.spi.LastLoginTrackerAuthenticatorFactory" が出力

# Keycloak 完全再起動
docker compose restart keycloak
docker compose logs -f keycloak | grep -i "last-login-tracker"
```

### 8.4 Maven ビルドが遅い / 失敗

```bash
# ネットワーク問題の場合
mvn clean package -DskipTests -X 2>&1 | tail -50

# Corporate proxy 環境の場合
# ~/.m2/settings.xml に proxy 設定
cat > ~/.m2/settings.xml << 'EOF'
<settings>
  <proxies>
    <proxy>
      <active>true</active>
      <protocol>http</protocol>
      <host>your.proxy.host</host>
      <port>8080</port>
    </proxy>
  </proxies>
</settings>
EOF
```

### 8.5 Direct Access Grant が失敗

```bash
# Client 設定確認
TOKEN=$(get_admin_token)
curl -s "http://localhost:18080/admin/realms/poc-jit-scim/clients?clientId=poc-test-client" \
    -H "Authorization: Bearer $TOKEN" | jq '.[0] | {clientId, directAccessGrantsEnabled, publicClient}'

# → directAccessGrantsEnabled: true が必要
```

---

## 9. 検証終了後のアクション

### 9.1 元端末で反映すべきドキュメント

検証結果を持ち帰ったら、以下 4 箇所を更新:

1. **[jit-scim §10.4.F](../../doc/common/jit-scim-coexistence-keycloak.md)** に PoC 検証結果セクション新設
2. **[hearing-checklist B-SCIM-7/8/9/10](../../doc/requirements/hearing-checklist.md)** の 🚨/🔴/🟡/⏳ → 実際の結果アイコンに更新
3. **[ADR-025 §I.2](../../doc/adr/025-scim-positioning-and-receive-stance.md)** の PoC 検証結果を反映
4. **[ADR-060 §C.2.3](../../doc/adr/060-auth-protocol-attack-path-residual-tbd.md)** の SPI 実装方式を確定（案 A/B/C）

### 9.2 Phase 1 実装フローの確定

検証結果を踏まえて、[README.md §5 Phase 1 実装への影響](README.md) を更新し、Phase 1 実装計画を確定。

---

## 10. サポート情報

### 10.1 一次資料参照

| # | 事実 | URL |
|---|---|---|
| E-4 | Keycloak 26.6 SCIM Experimental | https://www.keycloak.org/2026/04/scim-as-experimental-feature |
| E-8 | setSingleAttribute in EventListenerProvider 動かない | https://github.com/keycloak/keycloak/issues/14942 |
| E-9 | enlistAfterCompletion ConcurrentModificationException | https://github.com/keycloak/keycloak/issues/22902 |
| E-10 | EventListenerProvider Javadoc | https://www.keycloak.org/docs-api/latest/javadocs/org/keycloak/events/EventListenerProvider.html |
| E-11 | Sync Mode Override 4 モード | https://docs.redhat.com/en/documentation/red_hat_build_of_keycloak/22.0/html/server_administration_guide/identity_broker |
| E-12 | Per-Mapper syncMode Terraform | https://github.com/keycloak/terraform-provider-keycloak/blob/main/docs/resources/custom_identity_provider_mapper.md |

**全 14 件は [../../doc/common/jit-scim-coexistence-keycloak.md §10.4.E.5](../../doc/common/jit-scim-coexistence-keycloak.md) に完全リスト有**（別端末に持ち込む場合、このファイルもコピー推奨）。

### 10.2 想定判定結果パターン

| ケース | V1 | V2 | V3' | Phase 1 判定 |
|---|:---:|:---:|:---:|:---:|
| **理想（全 PASS）**| ✅ | ✅ | ✅ | ✅ GO、Fallback 不要 |
| **V1 FAIL のみ** | ❌ | ✅ | ✅ | ✅ GO、Fallback A（Custom Authenticator SPI 拡張で scim_active 自動セット）+1w |
| **V3' FAIL のみ** | ✅ | ✅ | ❌ | ⚠ GO with Fallback、案 A / 案 C 検討 +1-2w |
| **V1 + V3' FAIL** | ❌ | ✅ | ❌ | ⚠ GO with Fallback、Custom Authenticator SPI で両対応 +2-3w |
| **全 FAIL**| ❌ | ❌ | ❌ | ❌ NO-GO、設計見直し |

---

## 11. 連絡事項テンプレート（結果報告用）

検証完了後、元端末に報告する際のテンプレート:

```
【PoC 検証結果報告】JIT ユーザ削除 + SCIM 実装可能性
実施日: YYYY-MM-DD
実施環境: 別端末（<OS 種別>、<Docker Version>、<Java Version>）

■ 総合判定
- V1: [PASS / FAIL / PARTIAL]
- V2: [PASS / FAIL / PARTIAL]
- V3': [PASS / FAIL / PARTIAL]

■ Fallback 発動
- V1 Fallback: [不要 / 代替 A / 代替 B / 代替 C] → [追加工数]
- V2 Fallback: [不要 / Realm 全体 IMPORT] → [追加工数]
- V3' Fallback: [不要 / 案 A / 案 C] → [追加工数]

■ Phase 1 実装計画への影響
- SCIM プラグイン選定: [Metatavu / Native / 代替]
- SPI 実装方式: [案 A / 案 B / 案 C]
- 全体追加工数: [+Xw]

■ 詳細
docs/verification-log.md を参照

■ 添付
poc-results-YYYYMMDD.tar.gz（verification-log.md + tests/*log + SPI JAR）
```
