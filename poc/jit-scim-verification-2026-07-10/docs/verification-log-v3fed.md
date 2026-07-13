# V3'' 検証結果ログ（フェデ JIT 経路）

> **実施日**: 2026-07-10
> **実施者**: Claude Code（devcontainer 実機。手動ブラウザ部分は curl で二段認可コードフローをシミュレート）
> **環境**: Keycloak 26.6（同一インスタンス、customer-idp Realm + poc-jit-scim Realm の 2-Realm 構成）
> **参照**: [../QUICKSTART-OTHER-MACHINE.md §12](../QUICKSTART-OTHER-MACHINE.md) / [../../doc/common/jit-scim-coexistence-keycloak.md §10.4.F.9](../../../doc/common/jit-scim-coexistence-keycloak.md) / [additional-poc-findings.md](additional-poc-findings.md)
> **注記**: V3' は P-4 ローカル PW ユーザで実施、V3'' は **P-3 フェデ JIT ユーザ**で追加検証（本基盤の主用途）

---

## 0. 実行環境の是正（実機で判明）

| # | 事象 | 是正 |
|---|---|---|
| **F-7** | `setup-federation.sh` の**順序バグ**：Step 3 で IdP を作成する際 `firstBrokerLoginFlowAlias=first-broker-login-with-tracker` を参照するが、当該フローは Step 4-5 で作成されるため未存在 → **IdP 作成が HTTP 500**（`No available authentication flow with alias`） | **フロー作成（Step4-5）を IdP 作成（Step3）より前に**実行するようスクリプト順序を修正。暫定対処として、フロー作成後に IdP を再作成すれば 201 で通る |
| **F-8** | `config/user-profile-poc.json` に `_comment` キーがあり、User Profile 適用が **HTTP 400**（`Unrecognized field "_comment"`）。KC の UPConfig パーサは未知フィールドを拒否する | `_comment` を JSON から除去（コメントは別ファイル/ドキュメントに記載） |

> ※ V3'（V1-V3'）で判明した F-1〜F-6 は [additional-poc-findings.md](additional-poc-findings.md) 参照。

---

## 1. セットアップ結果（setup-federation.sh）

| Step | 内容 | 状態 | メモ |
|---|---|:---:|---|
| Step 1 | customer-idp Realm 作成 | ✅ | fed-jit-user / fed-jit-user-2 込みで作成（201） |
| Step 2 | User Profile 設定 | ⚠→✅ | 初回 400（F-8）。`_comment` 除去後 200。ENABLED + 9 属性宣言 |
| Step 3 | OIDC IdP 'customer-idp' 追加 | ⚠→✅ | 初回 500（F-7 順序バグ）。フロー作成後に再実行して 201 |
| Step 4 | First Broker Login Flow 複製 + SPI 追加 | ✅ | `first-broker-login-with-tracker`、Last Login Tracker を末尾 REQUIRED |
| Step 5 | Post Broker Login Flow 新規作成 + SPI 追加 | ✅ | `post-broker-login-with-tracker`、Last Login Tracker REQUIRED |

---

## 2. V3'' テスト結果（v4-federation-jit.sh + curl シミュレーション）

### 2.1 自動テスト結果（v4-federation-jit.sh Test 1-3）

| Test | 内容 | 結果 | メモ |
|---|---|:---:|---|
| Test 1 | OIDC IdP 'customer-idp' 登録確認 | ✅ | firstBrokerLoginFlowAlias / postBrokerLoginFlowAlias とも期待値 |
| Test 2 | First Broker Login Flow の SPI 配置確認 | ✅ | last-login-tracker が配置（top-level 末尾 REQUIRED。※top-level 要素が全 REQUIRED のため F-6 の罠は起きない） |
| Test 3 | Post Broker Login Flow の SPI 配置確認 | ✅ | last-login-tracker が REQUIRED で配置 |

### 2.2 ログインテスト結果（curl で二段認可コードフローを実行）

| Test | 内容 | 結果 | メモ |
|---|---|:---:|---|
| Test 4 | 初回フェデログイン → JIT 作成 + last_login 反映 | ✅ | **First Broker Login Flow** 経由で SPI が initial write |
| Test 5 | 2 回目フェデログイン → last_login 更新（debounce 期間外） | ✅ | **Post Broker Login Flow** 経由で SPI が update |

**フロー遷移（実測 hop）**：
```
[初回] auth(kc_idp_hint=customer-idp) -> broker/customer-idp/login -> customer-idp/auth
       -> [customer-idp login form POST] -> broker/customer-idp/endpoint(code)
       -> login-actions/first-broker-login   ← ★ First Broker Login Flow（SPI initial write）
       -> broker/after-first-broker-login
       -> login-actions/post-broker-login     ← ★ Post Broker Login Flow も続けて実行
       -> localhost:9999/cb?code=...          ← 完了

[2回目] auth -> ... -> broker/customer-idp/endpoint(code)
       -> login-actions/post-broker-login     ← ★ First はskip、Post Broker Login Flow のみ（SPI update）
       -> localhost:9999/cb?code=...
```

### 2.3 属性検証結果（初回ログイン後の fed-jit-user）

```json
{
  "username": "fed-jit-user",
  "email": "fed-jit-user@customer.example.com",
  "attributes": {
    "last_login": ["1783675449314"]      // ★ First Broker Login Flow の SPI が書込
  },
  "federatedIdentities": [
    { "identityProvider": "customer-idp", "userName": "fed-jit-user" }   // ★ 真の JIT ユーザ
  ]
}
```
- 2 回目ログイン後 `last_login` は `1783502681929`(2日前にセット) → `1783675482288` に更新。
- `provisioned_by` は **未セット**（現 SPI は last_login のみ書込。Phase 1 で SPI 拡張して `provisioned_by=jit` を付与する候補 = T3）。

### 2.4 SPI 実行ログ（Keycloak Container ログ）

```
# 初回（First Broker Login Flow）
INFO LastLoginTracker: initial write for user=fed-jit-user, now=1783675449314
INFO LastLoginTracker: wrote last_login=1783675449314 for user=fed-jit-user

# 2回目（Post Broker Login Flow、debounce 判定込み）
INFO LastLoginTracker: update for user=fed-jit-user, last=1783502681929, diff=172800359ms
INFO LastLoginTracker: wrote last_login=1783675482288 for user=fed-jit-user
```

### 2.5 【参考】JWT の実態（ブローカリングで登場する 2 トークン）

| | ① 顧客IdP(customer-idp) 発行 | ② ブローカー(poc-jit-scim) がアプリに再発行 |
|---|---|---|
| `iss` | `.../realms/customer-idp` | `.../realms/poc-jit-scim` |
| `azp`（受け手） | `broker-poc`（ブローカー用クライアント） | `poc-test-client`（アプリ） |
| `sub` | 顧客IdP側のユーザID | **poc-jit-scim で新規発番された JIT ユーザ ID** |
| カスタム属性 | — | Protocol Mapper 未設定のため token には出ない |

→ **アプリは顧客IdPのトークンを直接見ず、自基盤が再発行したトークンのみを受け取る**。フェデ時に `sub` はローカル発番され、federated_identity で顧客IdPと紐付く。

---

## 3. 判定

- **総合**：✅ **PASS** — フェデ JIT ユーザ（P-3）でも、**First Broker Login Flow（初回）+ Post Broker Login Flow（2 回目以降）**に SPI を配置すれば `last_login` が確実に書き込まれる。V3' の検証ギャップ（§4.4）を解消。
- **Fallback 発動**：不要。
- **Phase 1 実装への影響**：SPI は **3 系統 Flow 配置**（Browser forms / First Broker / Post Broker）で確定。

---

## 4. Phase 1 実装計画への影響

### 4.1 SPI Flow 配置（3 系統確定）

- **Browser Flow**：forms サブフロー内（V3' 実測済み、P-4 ローカル PW ユーザ経路）
- **First Broker Login Flow**：末尾 REQUIRED（V3'' 実測、P-3 フェデ初回）
- **Post Broker Login Flow**：REQUIRED（V3'' 実測、P-3 フェデ 2 回目以降）

### 4.2 Terraform IaC 追加項目

```hcl
- keycloak_authentication_flow.first_broker_login_with_tracker
- keycloak_authentication_execution.first_broker_last_login       # REQUIRED
- keycloak_authentication_flow.post_broker_login_with_tracker
- keycloak_authentication_execution.post_broker_last_login        # REQUIRED
- keycloak_oidc_identity_provider.*.first_broker_login_flow_alias = first-broker-login-with-tracker
- keycloak_oidc_identity_provider.*.post_broker_login_flow_alias  = post-broker-login-with-tracker
```

### 4.3 追加工数見積（目安）

- Flow 設定 IaC 化：+1d（3 系統 Flow + IdP 紐付け）
- 実 IdP との統合テスト：+1-2d
- SPI 拡張（`provisioned_by=jit` 自動セット、T3）：+0.5d（任意）

---

## 5. 既存ドキュメントへの反映（TODO）

- [ ] [jit-scim §10.4.F.9](../../../doc/common/jit-scim-coexistence-keycloak.md) の V3'' 検証結果反映（TBD → PASS）
- [ ] [hearing-checklist B-SCIM-11](../../../doc/requirements/hearing-checklist.md) の状態 ⏳ → ✅ PASS
- [ ] [ADR-060 §C.2.3 F-9](../../../doc/adr/060-auth-protocol-attack-path-residual-tbd.md) に V3'' 実測結果追記
- [x] 新是正 F-7 / F-8 を [additional-poc-findings.md](additional-poc-findings.md) に追記

---

## 6. 総合結論

### 6.1 フェデ JIT ユーザで SPI は動作するか

- 答え：**Yes（条件付き）** — First Broker Login Flow + Post Broker Login Flow への SPI 配置が前提。Browser Flow の forms 配置だけではフェデ経路（IdP Redirector 分岐）で動かない。
- 根拠：Test 4（初回=First Broker）/ Test 5（2 回目=Post Broker）とも last_login 書込を実測。

### 6.2 Phase 1 リリース判定への影響

- 判定：**GO with 3 系統 Flow 配置**。
- 条件：Browser(forms) + First Broker + Post Broker の 3 系統に SPI を配置（IaC 化）。

---

**変更履歴**

| 日付 | 内容 |
|---|---|
| 2026-07-10 | 初版作成（テンプレート） |
| 2026-07-10 | **実機で V3'' 実行。Test1-5 全 PASS、フェデ JIT 経路の SPI 動作を実証。F-7/F-8 追記。JWT 実態も記録** |
