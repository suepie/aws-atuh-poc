# V3'' 検証結果ログ（フェデ JIT 経路）

> **実施日**: YYYY-MM-DD
> **実施者**: XXX（別端末で実施）
> **環境**: Keycloak 26.6（同一インスタンス、customer-idp Realm + poc-jit-scim Realm の 2-Realm 構成）
> **参照**: [../QUICKSTART-OTHER-MACHINE.md §12](../QUICKSTART-OTHER-MACHINE.md) / [../../doc/common/jit-scim-coexistence-keycloak.md §10.4.F.9](../../../doc/common/jit-scim-coexistence-keycloak.md)
> **注記**: V3' は P-4 ローカル PW ユーザで実施、V3'' は P-3 フェデ JIT ユーザで追加検証

---

## 0. 実行環境の是正（V3' から追加、実機で判明した場合はここに記録）

| # | 事象 | 是正 |
|---|---|---|
| F-7 | | |
| F-8 | | |

---

## 1. セットアップ結果（setup-federation.sh）

| Step | 内容 | 状態 | メモ |
|---|---|:---:|---|
| Step 1 | customer-idp Realm 作成 | ⏳ | |
| Step 2 | User Profile 設定（provisioned_by/last_login/scim_active 宣言） | ⏳ | |
| Step 3 | OIDC IdP 'customer-idp' 追加 | ⏳ | |
| Step 4 | First Broker Login Flow 複製 + SPI 追加 | ⏳ | |
| Step 5 | Post Broker Login Flow 新規作成 + SPI 追加 | ⏳ | |

---

## 2. V3'' テスト結果（v4-federation-jit.sh）

**参照**：[tests/v4-federation-jit.sh](../tests/v4-federation-jit.sh)

### 2.1 自動テスト結果

| Test | 内容 | 結果 | メモ |
|---|---|:---:|---|
| Test 1 | OIDC IdP 'customer-idp' 登録確認 | ⏳ | |
| Test 2 | First Broker Login Flow の SPI 配置確認 | ⏳ | |
| Test 3 | Post Broker Login Flow の SPI 配置確認 | ⏳ | |

### 2.2 手動テスト結果

| Test | 内容 | 結果 | メモ |
|---|---|:---:|---|
| Test 4 | 初回フェデログイン → JIT 作成 + last_login 反映 | ⏳ | |
| Test 5 | 2 回目フェデログイン → last_login 更新（debounce 期間外） | ⏳ | |

### 2.3 属性検証結果

初回ログイン後の `fed-jit-user` 属性:

```json
{
  "username": "<記入>",
  "email": "<記入>",
  "enabled": true,
  "attributes": {
    "last_login": ["<記入 or NULL>"],
    "provisioned_by": ["<記入 or NULL>"]
  },
  "federatedIdentities": [
    {
      "identityProvider": "customer-idp",
      "userId": "<記入>",
      "userName": "<記入>"
    }
  ]
}
```

### 2.4 SPI 実行ログ（Keycloak Container ログ）

```
[記入予定]
docker compose logs keycloak 2>&1 | grep -E "LastLoginTracker|first-broker-login|post-broker-login"
```

---

## 3. 判定

- **総合**：⏳ PASS / FAIL / PARTIAL
- **理由**：
- **Fallback 発動**：⏳ 不要 / 案 X-A / 案 X-B / 案 X-C
- **Phase 1 実装への影響**：⏳

---

## 4. Phase 1 実装計画への影響

### 4.1 SPI Flow 配置（3 系統確定）

- **Browser Flow**：forms サブフロー内（V3' 実測済み）
- **First Broker Login Flow**：⏳（V3'' 実測）
- **Post Broker Login Flow**：⏳（V3'' 実測）

### 4.2 Terraform IaC 追加項目

```hcl
# 追加要のリソース
- keycloak_authentication_flow.first_broker_login_with_tracker
- keycloak_authentication_execution.first_broker_last_login
- keycloak_authentication_flow.post_broker_login_with_tracker
- keycloak_authentication_execution.post_broker_last_login
- keycloak_oidc_identity_provider.*.first_broker_login_flow_alias
- keycloak_oidc_identity_provider.*.post_broker_login_flow_alias
```

### 4.3 追加工数見積

- Flow 設定 IaC 化：⏳ +Xd
- 統合テスト（実 IdP）：⏳ +Xd
- 合計：⏳ +Xd

---

## 5. 既存ドキュメントへの反映（TODO）

- [ ] [jit-scim §10.4.F.9](../../../doc/common/jit-scim-coexistence-keycloak.md) の V3'' 検証結果反映（TBD → 実結果）
- [ ] [hearing-checklist B-SCIM-11](../../../doc/requirements/hearing-checklist.md) の状態 ⏳ → PASS/FAIL/PARTIAL
- [ ] [ADR-060 §C.2.3 F-9](../../../doc/adr/060-auth-protocol-attack-path-residual-tbd.md) に V3'' 実測結果追記
- [ ] 新是正 F-7 以降があれば [additional-poc-findings.md](additional-poc-findings.md) に追記

---

## 6. 総合結論

### 6.1 フェデ JIT ユーザで SPI は動作するか

- 答え：⏳ Yes / No / 条件付き
- 根拠：⏳

### 6.2 Phase 1 リリース判定への影響

- 判定：⏳ GO 継続 / GO with 3 系統 Flow 配置 / NO-GO
- 条件：⏳

---

**変更履歴**

| 日付 | 内容 |
|---|---|
| YYYY-MM-DD | 初版作成（V3'' 実施） |
