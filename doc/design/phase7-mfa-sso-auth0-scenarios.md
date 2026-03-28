# Phase 7: MFA・SSO・Auth0 検証シナリオ

**作成日**: 2026-03-26

---

## 目的

Keycloak環境でMFA・SSO・Auth0連携を検証し、Cognito構成との違いを明らかにする。

---

## シナリオ7-1: Keycloak MFA（TOTP）有効化

### 目的
ローカルユーザーにTOTP MFAを設定し、ログインフローを確認する。

### 事前準備
- Keycloak Admin Console にアクセス可能
- Google Authenticator 等のTOTPアプリを用意

### 手順

| # | 操作 | 期待結果 |
|---|------|---------|
| 1 | Admin Console → `auth-poc` realm → Authentication → Required actions → `Configure OTP` を **Default Action** に設定 | 全ユーザーに次回ログイン時TOTP登録を強制 |
| 2 | SPA (localhost:5174) → ログイン → test@example.com / TestUser1! | TOTP登録画面が表示される（QRコード） |
| 3 | Google Authenticator でQRコードをスキャン → コード入力 | TOTP登録完了 → SPA にリダイレクト |
| 4 | ログアウト → 再ログイン → PW入力 | TOTP入力画面が表示される |
| 5 | TOTPコード入力 | ログイン成功 |
| 6 | トークンビューアーで確認 | `acr` クレームに認証レベルが含まれるか確認 |

### Cognito との対比
| 観点 | Cognito | Keycloak |
|------|---------|----------|
| MFA有効化 | User Pool設定（Terraform） | Admin Console → Authentication |
| TOTP登録 | Hosted UI 内で自動 | Keycloakログイン画面内で自動 |
| MFA強制タイミング | Required / Optional | **Required Actions で柔軟に制御** |

### 結果
| 確認項目 | 結果 | 備考 |
|---------|:----:|------|
| TOTP登録画面表示 | ⬜ | |
| TOTP登録→ログイン成功 | ⬜ | |
| 再ログイン時TOTP要求 | ⬜ | |

---

## シナリオ7-2: MFA + ECS再起動（障害耐性）

### 目的
MFAデータ（TOTPシークレット）がECS再起動後も維持されるか確認する。

### 手順

| # | 操作 | 期待結果 |
|---|------|---------|
| 1 | シナリオ7-1完了状態（TOTP登録済み） | |
| 2 | ECSタスク停止: `aws ecs update-service --cluster auth-poc-kc-cluster --service auth-poc-kc-service --desired-count 0` | Keycloak停止 |
| 3 | ECSタスク起動: `aws ecs update-service ... --desired-count 1` | Keycloak起動（2-3分） |
| 4 | SPA → ログイン → PW入力 | TOTP入力画面が表示される |
| 5 | 元のTOTPコード入力 | **ログイン成功（TOTP再登録不要）** |

### 確認ポイント
- MFAデータは `credential` テーブル（RDS）に保存 → ECS再起動で消えない
- Cognito でも同様（マネージドなので当然だが、仕組みが異なる）

### 結果
| 確認項目 | 結果 | 備考 |
|---------|:----:|------|
| ECS再起動後にTOTP有効 | ⬜ | |
| TOTP再登録不要 | ⬜ | |

---

## シナリオ7-3: MFA + RDS障害（障害耐性）

### 目的
RDS停止→復旧後にMFAデータが維持されるか確認する。

### 手順

| # | 操作 | 期待結果 |
|---|------|---------|
| 1 | TOTP登録済み状態 | |
| 2 | RDS停止: `aws rds stop-db-instance --db-instance-identifier auth-poc-kc-db` | RDS停止（5-10分） |
| 3 | RDS停止完了を確認 | `stopped` 状態 |
| 4 | SPA → ログイン試行 | **失敗**（Keycloak→RDS接続エラー → Keycloak停止） |
| 5 | RDS起動: `aws rds start-db-instance --db-instance-identifier auth-poc-kc-db` | RDS起動（5-10分） |
| 6 | ECSタスクが自動再起動するのを待つ | Keycloak復旧 |
| 7 | SPA → ログイン → PW入力 → TOTP入力 | **ログイン成功（MFAデータ維持）** |

### 確認ポイント
- `credential` テーブルはRDSの永続データ → RDS再起動で消えない
- RDS停止中はKeycloakも停止する（Phase 6 シナリオ3-2で確認済み）

### 結果
| 確認項目 | 結果 | 備考 |
|---------|:----:|------|
| RDS復旧後にTOTP有効 | ⬜ | |
| TOTP再登録不要 | ⬜ | |

---

## シナリオ7-4: SSO確認（複数Client）

### 目的
同一Realm内の複数ClientでSSOが動作するか確認する。

### 事前準備
Admin Console → `auth-poc` realm → Clients → **Create client** で2つ目のClientを作成:

| 項目 | 値 |
|------|-----|
| Client ID | `auth-poc-spa-2` |
| Client Authentication | OFF（Public） |
| Standard Flow | ON |
| Valid Redirect URIs | `http://localhost:5175/*` |
| Web Origins | `http://localhost:5175` |

→ `app-keycloak` をコピーしてポート5175で起動するか、同じSPAの別タブで検証

### 手順

| # | 操作 | 期待結果 |
|---|------|---------|
| 1 | SPA-A (localhost:5174, client=auth-poc-spa) → ログイン → PW + TOTP | ログイン成功 |
| 2 | SPA-B (localhost:5175, client=auth-poc-spa-2) → ログインボタン | **PW/TOTP入力なしでログイン成功**（SSO） |
| 3 | Admin Console → Sessions | 1つのSSOセッションに2つのClient Sessionが紐づいている |
| 4 | SPA-A → ログアウト | SPA-Aからログアウト |
| 5 | SPA-B → ページリロード or API呼び出し | **SPA-Bも無効化されているか**（Back-Channel Logout） |

### Cognito との対比
| 観点 | Cognito + Auth0 | Keycloak |
|------|----------------|----------|
| SSO範囲 | Auth0セッション経由（User Pool横断） | **Realm内の全Client（ネイティブ）** |
| SSO時に外部通信 | Auth0に毎回リダイレクト | **Keycloak内で完結（高速）** |
| Back-Channel Logout | 非対応 | **対応** |

### 結果
| 確認項目 | 結果 | 備考 |
|---------|:----:|------|
| Client AログインでClient BがSSO | ⬜ | |
| TOTP再入力不要 | ⬜ | |
| Client Aログアウト→Client B無効 | ⬜ | |

---

## シナリオ7-5: Auth0 Identity Brokering

### 目的
Auth0をKeycloakの外部IdPとして設定し、フェデレーション認証を確認する。

### 事前準備

#### Auth0 側
1. Auth0 Dashboard → Applications → Create Application → **Regular Web Application**
2. Settings:
   - Allowed Callback URLs: `http://auth-poc-kc-alb-256501875.ap-northeast-1.elb.amazonaws.com/realms/auth-poc/broker/auth0/endpoint`
   - Allowed Logout URLs: `http://auth-poc-kc-alb-256501875.ap-northeast-1.elb.amazonaws.com/realms/auth-poc/broker/auth0/endpoint/logout_response`
3. Domain, Client ID, Client Secret をメモ

#### Keycloak 側
1. Admin Console → `auth-poc` realm → Identity Providers → Add Provider → **OpenID Connect v1.0**
2. 設定:

| 項目 | 値 |
|------|-----|
| Alias | `auth0` |
| Display Name | `Login with Auth0` |
| Discovery Endpoint | `https://<auth0-domain>/.well-known/openid-configuration` |
| Client ID | Auth0のClient ID |
| Client Secret | Auth0のClient Secret |
| Client Authentication | Client secret sent as post |
| Default Scopes | `openid profile email` |
| Trust Email | ON |

### 手順

| # | 操作 | 期待結果 |
|---|------|---------|
| 1 | SPA → ログイン画面 | 「Login with Auth0」ボタンが表示される |
| 2 | 「Login with Auth0」クリック | Auth0ログイン画面にリダイレクト |
| 3 | Auth0でユーザー作成 or 既存ユーザーでログイン | Auth0認証成功 → Keycloakに戻る |
| 4 | 初回: Keycloakアカウントリンク画面 | メールアドレス確認 or 自動リンク |
| 5 | SPA にリダイレクト | ログイン成功 |
| 6 | トークンビューアー確認 | issuer=Keycloak（Auth0ではない）、ユーザー属性がマッピングされている |
| 7 | Admin Console → Users | フェデレーションユーザーが作成されている（`federated_identity` テーブル） |

### Cognito との対比
| 観点 | Cognito + Auth0 | Keycloak + Auth0 |
|------|----------------|-----------------|
| 設定方法 | Terraform（OIDC IdP設定） | Admin Console（Identity Providers） |
| トークン発行元 | Cognito | **Keycloak**（Auth0ではない） |
| JITプロビジョニング | 自動（identities クレーム付与） | 自動（federated_identity テーブル） |

### 結果
| 確認項目 | 結果 | 備考 |
|---------|:----:|------|
| Auth0ログイン画面表示 | ✅ | Keycloakログイン画面に「Login with Auth0」ボタン自動表示 |
| Auth0認証→Keycloakに戻る | ✅ | |
| JITプロビジョニング | ✅ | 初回に「Update Account Information」画面が表示される（First Broker Login フロー） |
| トークンのissuer=Keycloak | ✅ | |

### 検証中に発見した問題

#### 問題1: First Broker Login でプロフィール情報が空

Auth0から`profile`と`email`のスコープ情報が返らず、「Update Account Information」画面でemail/name が空になった。

**原因**: IdP設定の Default Scopes が `openid` のみで `profile email` が含まれていなかった可能性。
**対処**: IdP設定で Default Scopes に `openid profile email` を設定する。または First Broker Login フローで `Review Profile` を Disabled にする。

#### 問題2: Auth0経由ログイン後にKeycloak MFAを要求される（二重MFA）

Auth0で認証成功後、KeycloakのTOTP登録/入力を求められる。

**原因**: シナリオ7-1でMFAを全ユーザーに強制する設定にしたため、フェデレーションユーザーにもKeycloakのMFAが適用される。
**影響**: Auth0側でもMFAを有効にすると、ユーザーは Auth0 MFA → Keycloak MFA の二重MFAを強いられる。
**対処**: シナリオ7-6で、フェデレーションユーザーにはKeycloak MFAをスキップする認証フローを設定する。

```mermaid
flowchart TB
    subgraph Current["現状（問題あり）"]
        C1["Auth0でPW認証"] --> C2["Auth0 MFA（設定時）"]
        C2 --> C3["Keycloakに戻る"]
        C3 --> C4["★ Keycloak MFA要求（二重）"]
        C4 --> C5["ログイン完了"]
    end

    subgraph Expected["あるべき姿"]
        E1["Auth0でPW認証"] --> E2["Auth0 MFA（設定時）"]
        E2 --> E3["Keycloakに戻る"]
        E3 --> E4["Keycloak MFAスキップ"]
        E4 --> E5["ログイン完了"]
    end

    style Current fill:#fff0f0,stroke:#cc0000
    style Expected fill:#d3f9d8,stroke:#2b8a3e
```

**設計原則**: MFAは**パスワードを管理している側が提供**する。
- ローカルユーザー → KeycloakがMFA提供
- フェデレーションユーザー → IdP（Auth0/Entra ID）がMFA提供、KeycloakはMFAスキップ |

---

## シナリオ7-6: Auth0 SSO + MFA

### 目的
Auth0経由でログイン後のSSO動作と、MFAの二重要求がないことを確認する。

### 事前準備
- Auth0 Dashboard → Security → Multi-factor Auth → **Enable** (TOTP)
- シナリオ7-5完了（Auth0 IdP設定済み）

### 手順

| # | 操作 | 期待結果 |
|---|------|---------|
| 1 | SPA-A → 「Login with Auth0」→ Auth0でPW + Auth0 MFA（TOTP） | SPA-Aログイン成功 |
| 2 | SPA-B → ログインボタン | **PW/MFA不要でログイン**（Keycloak SSOセッション有効） |
| 3 | Keycloak MFAが要求されないことを確認 | **Auth0 MFAとKeycloak MFAが二重にならない** |
| 4 | ログアウト → 再度Auth0でログイン | Auth0セッション有効なら**Auth0 MFAもスキップ** |

### MFA責任の確認

```
Auth0ユーザー:  Auth0がMFA提供 → KeycloakはMFAスキップ
ローカルユーザー: KeycloakがMFA提供
→ 二重MFAにならないことを確認
```

### 二重MFA解消の手順

1. Admin Console → Users → Auth0経由ユーザー → **Credentials** タブ → OTPエントリを **Delete**
2. **Required Actions** タブ → `Configure OTP` を削除
3. ログアウト → Auth0で再ログイン

これにより、browserフローの `Condition - User Configured` が「OTP未設定」と判定し、OTPサブフロー全体がスキップされる。

```
browser Browser - Conditional OTP    (Conditional)
├── Condition - User Configured      (Required)  ← 「OTP設定済みか？」を判定
│   → ローカルユーザー: true → OTP Form表示
│   → Auth0ユーザー（OTP削除後）: false → サブフロー全体スキップ
└── OTP Form                         (Required)
```

### 結果
| 確認項目 | 結果 | 備考 |
|---------|:----:|------|
| Auth0 MFAでログイン成功 | ✅ | |
| Keycloak MFA二重要求なし | ✅ | Auth0ユーザーのOTP削除で解消 |
| SSO: Client BでPW/MFA不要 | ✅ | シナリオ7-4で確認済み |
| Auth0 SSOセッションでMFAスキップ | ✅ | Auth0セッション有効時 |

---

## 検証の進め方

```mermaid
flowchart TD
    A["7-1: MFA有効化\n(Admin Console設定)"] --> B["7-2: MFA + ECS再起動\n(障害耐性)"]
    B --> C["7-3: MFA + RDS障害\n(障害耐性)"]
    C --> D["7-4: SSO確認\n(複数Client)"]
    D --> E["7-5: Auth0 Identity Brokering\n(外部IdP設定)"]
    E --> F["7-6: Auth0 SSO + MFA\n(二重MFA確認)"]
    F --> G["結果まとめ\n→ ドキュメント更新"]
```

---

## 結果サマリー

| シナリオ | 結果 | Cognito優位 | Keycloak優位 | 備考 |
|---------|:----:|:-----------:|:----------:|------|
| 7-1 MFA有効化 | ✅ | | ✅ | 認証フローで柔軟に制御可能 |
| 7-2 MFA + ECS再起動 | ✅ | | | MFAデータはDB保存、ECS再起動で消えない |
| 7-3 MFA + RDS障害 | ✅ | | | RDS復旧後もMFAデータ維持 |
| 7-4 SSO（複数Client） | ✅ | | ✅ | Realm内ネイティブSSO、外部通信不要 |
| 7-5 Auth0 Brokering | ✅ | | | Identity Brokering動作確認 |
| 7-6 Auth0 MFAスキップ | ✅ | | ✅ | Conditional OTPで二重MFA回避 |

---

## 検証で得られたノウハウ

### MFA関連

| ノウハウ | 詳細 |
|---------|------|
| **MFAデータの保存場所** | `credential` テーブル（DB）にのみ保存。Infinispanには保存されない。ECS再起動・RDS障害復旧で消えない |
| **MFA有効化の方法** | ① Required Actions で `Configure OTP` を Default Action に設定（新規ユーザー向け）<br/>② 既存ユーザーには Users → Required Actions で個別に追加が必要 |
| **MFA強制のタイミング** | Default Action を ON にしただけでは既存ユーザーに適用されない。既存ユーザーには個別設定が必要 |
| **フェデレーションユーザーのMFAスキップ** | `Condition - User Configured` を使い、OTP未設定ユーザー（=フェデレーション）をスキップ。フェデレーションユーザーの Credentials から OTP を削除する |
| **設計原則** | MFAは**パスワードを管理している側**が提供。ローカル→Keycloak、フェデレーション→IdP側 |

### SSO関連

| ノウハウ | 詳細 |
|---------|------|
| **SSO範囲** | 同一Realm内の全Clientで自動有効。設定不要 |
| **SSO の仕組み** | Keycloakドメインの `KEYCLOAK_SESSION` Cookie。ブラウザ単位で共有 |
| **シークレットモード** | Cookieが隔離されるためSSOは効かない（正常動作） |
| **Realm間SSO** | 不可。SSO が必要なサービスは1つのRealmに統合する |
| **Cognito+Auth0との違い** | Cognito+Auth0: SSOはAuth0セッション（外部通信あり）。Keycloak: ネイティブSSO（外部通信なし、高速） |

### Auth0 Identity Brokering関連

| ノウハウ | 詳細 |
|---------|------|
| **設定場所** | Admin Console → Identity Providers → OpenID Connect v1.0 |
| **ボタン表示** | IdPを追加するだけでログイン画面に自動表示（SPA側の変更不要）。Cognitoでは `identity_provider` パラメータの明示指定が必要だった |
| **First Broker Login** | 初回ログイン時に「Update Account Information」画面が表示される。profile/email のスコープを設定すれば自動入力される |
| **Default Scopes** | `openid profile email` を必ず設定。`openid` のみだとemail/name が空になる |
| **Auth0 Callback URL** | `http://<keycloak>/realms/<realm>/broker/<alias>/endpoint` の形式 |
| **トークン発行元** | Auth0ではなく**Keycloak**がトークンを発行（issuer=Keycloak）。Cognito+Auth0と同じ構造 |
| **二重MFA問題** | デフォルトではフェデレーションユーザーにもKeycloakのMFAが適用される。`Condition - User Configured` + OTP未設定で回避 |

### Keycloak運用関連

| ノウハウ | 詳細 |
|---------|------|
| **ECS頻繁停止** | `start-dev` モードのCPU負荷が高く、ALBヘルスチェック失敗でタスクが停止される。2 vCPU / 4 GB に増強で改善するが根本解決にはならない |
| **復旧コマンド** | `aws ecs update-service --cluster auth-poc-kc-cluster --service auth-poc-kc-service --force-new-deployment` |
| **本番での対策** | `start --optimized` モード + HTTPS で CPU負荷が大幅に低下。PoC固有の問題 |

### Cognito vs Keycloak（Phase 7 で明らかになった差分）

```mermaid
flowchart TB
    subgraph KC_Adv["Keycloak が優位な点（Phase 7 で確認）"]
        K1["MFA条件分岐が認証フローで設定可能\n（Cognitoはカスタム実装必要）"]
        K2["SSO がRealm内ネイティブ\n（外部IdP不要、高速）"]
        K3["IdP追加でログイン画面自動更新\n（SPA変更不要）"]
        K4["Back-Channel Logout\n（Cognito未対応）"]
        K5["MFA DR時に自動同期\n（Aurora Global DB）"]
    end

    subgraph C_Adv["Cognito が優位な点（変わらず）"]
        C1["マネージドで安定稼働\n（ECS頻繁停止問題なし）"]
        C2["設定変更がTerraformで一元管理"]
        C3["運用チーム不要"]
    end

    style KC_Adv fill:#f5f0ff,stroke:#6600cc
    style C_Adv fill:#d3f9d8,stroke:#2b8a3e
```
