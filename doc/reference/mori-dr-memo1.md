# Keycloak DR設計メモ：データ保存先とDR方針一覧

## 前提

本資料は、KeycloakをAWS ECS/Fargate上で稼働させ、東京リージョンをプライマリ、大阪リージョンをDR先とする構成を想定した整理です。

基本方針は以下です。

```text
Keycloak本体・テーマ・Provider
  → コンテナイメージ / ECRで管理

Realm / Client / User / Roleなど
  → Keycloak DB / Aurora PostgreSQLで管理

DB接続情報・SMTPパスワード・外部連携Secret
  → Secrets Managerで管理

ECSタスク内の一時ファイル・メモリキャッシュ
  → DR対象外。再生成または再ログイン許容
```

KeycloakのRealm export/importは、初期構築や設定移行には有用ですが、本番DRのバックアップ/リストアの主軸にはしない方針とします。  
本番DRでは、AuroraのクロスリージョンレプリケーションまたはAurora Global Databaseを中心に考えます。

---

## データ別 保存先・DR方針一覧

| データ/設定 | 主な保存先 | DRでの扱い | 推奨方針 |
|---|---|---|---|
| Keycloak本体バイナリ | ECRのコンテナイメージ | 大阪へ複製必要 | ECRクロスリージョンレプリケーション |
| Keycloakバージョン | ECRイメージタグ / Dockerfile | 大阪でも同一バージョンが必要 | `keycloak-custom:v26.x-custom.n` のように明示タグ管理 |
| カスタムテーマ | ECRイメージ内、または外部ボリューム | 大阪へ複製必要 | 原則ECRイメージに焼く |
| カスタムProvider / SPI / JAR | ECRイメージ内 | 大阪へ複製必要 | ECRイメージに焼く |
| `keycloak.conf` | コンテナ内、またはECS環境変数 | 大阪用設定が必要 | Dockerfileに固定値を焼かず、ECSタスク定義/IaCで管理 |
| `KC_DB` / `KC_DB_URL` | ECS環境変数 / Secrets Manager | 大阪では大阪Auroraを参照 | リージョン別に値を分ける |
| `KC_DB_USERNAME` / `KC_DB_PASSWORD` | Secrets Manager | 大阪へ複製・整合性必要 | Secrets Managerマルチリージョン複製、またはIaCで同等作成 |
| `KC_HOSTNAME` | ECS環境変数 / 設定ファイル | DR切替時に重要 | 同一FQDN運用なら東京/大阪で同じ値。リージョン別FQDNならRedirect URI含めて設計 |
| Realm | Aurora PostgreSQL | 大阪へ複製必須 | Aurora Global Database / クロスリージョンレプリカ |
| Client | Aurora PostgreSQL | 大阪へ複製必須 | DBレプリケーション |
| Client Secret | Aurora DB内、アプリ側Secretにも保持 | 大阪で整合性必須 | Keycloak DB + アプリ側Secrets Managerを両方DR対象 |
| Redirect URI / Web Origins | Aurora PostgreSQL | 大阪へ複製必須 | DBレプリケーション。FQDN変更時は事前に両方許可する設計も検討 |
| Role | Aurora PostgreSQL | 大阪へ複製必須 | DBレプリケーション |
| Group | Aurora PostgreSQL | 大阪へ複製必須 | DBレプリケーション |
| User | Aurora PostgreSQL | 大阪へ複製必須 | DBレプリケーション |
| User属性 | Aurora PostgreSQL | 大阪へ複製必須 | DBレプリケーション |
| パスワードハッシュ / Credential | Aurora PostgreSQL | 大阪へ複製必須 | DBレプリケーション |
| Identity Provider設定 | Aurora PostgreSQL | 大阪へ複製必須 | DBレプリケーション。ただし外部IdP側のRedirect URIも要確認 |
| User Federation設定 | Aurora PostgreSQL | 大阪へ複製必須 | DBレプリケーション。LDAP/AD等への接続経路もDR設計対象 |
| 認証フロー | Aurora PostgreSQL | 大阪へ複製必須 | DBレプリケーション |
| Required Action | Aurora PostgreSQL | 大阪へ複製必須 | DBレプリケーション |
| Password Policy | Aurora PostgreSQL | 大阪へ複製必須 | DBレプリケーション |
| Token有効期限設定 | Aurora PostgreSQL | 大阪へ複製必須 | DBレプリケーション |
| Realm署名鍵 / Keys | Aurora PostgreSQL | 大阪へ複製必須 | DBレプリケーション。これが失われると既存JWT検証に影響 |
| SMTP設定 | Aurora PostgreSQLに設定、パスワード等はSecret管理の場合あり | 大阪でも同じ送信設定が必要 | DB + Secrets Manager + SES設定をセットでDR |
| 管理者ユーザー | Aurora PostgreSQL | 大阪へ複製必須 | DBレプリケーション |
| 管理者初期パスワード環境変数 | ECS環境変数 / Secrets Manager | 初回作成後は通常DB側が主 | 初回起動用Secretとして管理。本番後は過信しない |
| オンラインユーザーセッション | Keycloak DB + メモリキャッシュ構成 | 可能ならDB側で復旧。ただし完全維持は保証しすぎない | DBレプリケーション。DR時は再ログイン許容を基本にする |
| オフラインセッション | DB + キャッシュ | 大阪へ複製対象 | DBレプリケーション |
| 認証途中の一時セッション | Infinispan / メモリ / DB構成依存 | 失われる前提 | DR時は再認証・再操作を許容 |
| Infinispanキャッシュ | ECSタスクのメモリ | 大阪へ複製しない | 起動後に再構築。リージョン間同期しない |
| `realms` / `users` / `authorization` キャッシュ | Infinispanローカルキャッシュ | 大阪へ複製しない | DBを正としてキャッシュは再生成 |
| `sessions` / `clientSessions` キャッシュ | Infinispan + DB構成依存 | リージョン間複製しない | DB永続化に寄せる。DR時は一部セッション喪失許容 |
| `loginFailures` | 分散キャッシュ | 大阪へ複製しない | DR後はリセット許容。厳密に必要ならDB/監査ログ側で補完 |
| 失効トークン / revoked tokens | DB / 内部状態 | 設計注意 | DBレプリケーションに寄せる。Realm exportだけでは不十分 |
| User/Admin Events | DB保存設定時はDB | 監査上必要ならDR対象 | DBレプリケーション + CloudWatch/S3への長期保管 |
| アクセスログ / アプリログ | CloudWatch Logs | 大阪へ複製必須ではないが保全推奨 | CloudWatch Logs保持期間設定、必要ならS3集約 |
| 監査ログ | CloudWatch Logs / DBイベント / 外部SIEM | 監査要件次第でDR対象 | S3やSecurity Lake等へ集約 |
| `/tmp` 等の一時ファイル | ECS/Fargate ephemeral storage | 複製不要 | タスク再作成で消えてよい前提 |
| コンテナローカルに置いた手作業ファイル | ECSタスク内 | 原則禁止 | ECR、Secrets、S3、EFS、IaCに移す |
| 証明書 | ACM / Secrets Manager | 大阪にも必要 | ACM証明書を大阪にも用意。ALBごとに設定 |
| ALB設定 | AWSリソース | 大阪に事前作成が望ましい | Terraform/CloudFormationで複製 |
| Route53レコード | Route53 | DR切替対象 | フェイルオーバールーティング、または手動切替 |
| ECSタスク定義 | ECS / IaC | 大阪に必要 | 同一定義をリージョン差分だけ変えて管理 |
| Security Group / Subnet / IAM Role | AWSリソース | 大阪に必要 | IaCで再現 |
| Secrets ManagerのSecret | Secrets Manager | 大阪へ複製必要 | Secrets Managerマルチリージョン複製、またはIaCで作成 |
| ECRリポジトリ / イメージ | ECR | 大阪へ複製必要 | ECRクロスリージョンレプリケーション |
| Aurora PostgreSQL | Aurora | 大阪へ複製必須 | Aurora Global Databaseまたはクロスリージョンレプリカ |

---

## 重要度別の整理

### 必ずDR対象にするもの

```text
・Aurora PostgreSQL / Keycloak DB
・ECRのKeycloakイメージ
・Secrets ManagerのDBパスワード、Client Secret連携情報、SMTP情報
・ECSタスク定義
・ALB / ACM / Security Group / IAM Role
・Route53切替設定
```

Keycloakの本質的な状態はDBに集約されます。  
そのため、DRの主役はECSタスク内の一時データではなく、Auroraのレプリケーションです。

---

### できればコード/IaC管理するもの

```text
・初期Realm定義
・Client定義
・認証フロー
・テーマ選択
・Password Policy
・ECSサービス定義
・ALB listener rule
・CloudWatch Logs設定
・Security Group
・IAM Role
・Secrets Manager Secret定義
```

Realm export/importやkeycloak-config-cliのような設定投入ツールは、初期構築・検証環境構築・設定差分管理には有用です。  
ただし、本番DRではDBレプリケーションを主軸にします。

---

### DR時に失われてもよいもの

```text
・ECS/Fargateの /tmp
・コンテナ内の一時作業ファイル
・メモリ上のキャッシュ
・認証途中の一時状態
・実行中プロセス状態
```

ECS/Fargateの一時ストレージはタスクに紐づく一時領域です。  
タスク再作成で消える前提にし、DR複製対象にはしません。

---

## 東京・大阪DR構成イメージ

```text
東京リージョン ap-northeast-1
  Route53
    ↓
  ALB
    ↓
  ECS / Fargate
    └─ Keycloak container
         ↓
  Aurora PostgreSQL Primary
  Secrets Manager
  ECR

        ↓ ECR replication
        ↓ Aurora cross-region replication / Global Database
        ↓ Secrets replication or IaC provisioning

大阪リージョン ap-northeast-3
  ALB
    ↓
  ECS / Fargate
    └─ Keycloak container
         ↓
  Aurora PostgreSQL Replica / Promoted DB
  Secrets Manager
  ECR
```

---

## DR切替時の実務フロー

```text
1. Aurora Global Database / クロスリージョンレプリカを大阪側で昇格
2. 大阪Secrets ManagerのDB接続先・パスワードを確認
3. 大阪ECSサービスを起動、またはdesired countを増やす
4. 大阪Keycloakが大阪Auroraへ接続
5. ALBヘルスチェックを確認
6. Route53を大阪ALBへ切替
7. アプリ側の認証疎通を確認
8. 必要に応じてユーザー再ログインを案内
```

---

## セッションに関する方針

DR時に「全ユーザーのログイン状態を完全に維持する」ことを前提にしすぎない方が安全です。

推奨方針は以下です。

```text
通常時のリージョン内HA
  → ECS複数タスク + ALB + Keycloakクラスタ/キャッシュ設計

リージョン障害時のDR
  → Aurora昇格 + 大阪ECS起動 + 必要に応じて再ログイン許容
```

セッション永続化により一部のログイン状態を維持できる可能性はありますが、認証途中の一時状態やメモリキャッシュは失われる前提で設計します。

---

## 避けるべき構成

以下はDR設計上避けるべきです。

```text
・Keycloakコンテナ内に重要ファイルを手作業配置する
・Realm exportファイルをコンテナ内だけに保存する
・コンテナ内ログを唯一の監査ログにする
・証明書や秘密情報をイメージに焼き込む
・latestタグだけで本番運用する
・大阪側のECSタスク定義やSecretsを手作業で後から作る
```

---

## 推奨する設計方針

```text
DBにあるもの
  → Aurora Global Database / クロスリージョンレプリカでDR

コンテナにあるもの
  → ECRクロスリージョンレプリケーションでDR

Secretにあるもの
  → Secrets Managerマルチリージョン複製、またはIaCで大阪にも作成

AWS構成
  → Terraform / CloudFormationで東京・大阪を同等に構築

キャッシュ・一時ファイル
  → 複製しない。大阪起動後に再生成

Realm export
  → 初期構築・設定差分管理の補助。本番バックアップの主軸にはしない
```

---

## 最終結論

KeycloakのDRで中心になるのは、以下の4点です。

```text
1. Aurora PostgreSQL
2. ECR
3. Secrets Manager
4. IaCで管理されたECS/ALB/Route53構成
```

ECSコンテナ内の一時データを大阪へ複製する設計は基本不要です。  
ECSタスクはステートレスな実行基盤として扱い、必要な状態はAurora、Secrets Manager、ECR、CloudWatch Logs、S3などに逃がす方針が安全です。
