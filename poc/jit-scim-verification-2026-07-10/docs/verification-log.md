# 検証結果ログ

> **実施日**: YYYY-MM-DD
> **実施者**: XXX
> **環境**: Keycloak 26.6 + PostgreSQL 16（本 PoC）
> **参照**: [README.md](../README.md) / [execution-guide.md](execution-guide.md)

---

## 1. 環境構築（Day 1）

| 項目 | 状態 | メモ |
|---|:---:|---|
| Docker Compose 起動 | ⏳ | |
| Keycloak 26.6 起動 | ⏳ | |
| PoC Realm インポート | ⏳ | |
| SCIM Realm API 有効化 | ⏳ | |
| SPI JAR ビルド | ⏳ | |
| SPI JAR デプロイ | ⏳ | |

---

## 2. V1: Metatavu SCIM Custom Attribute Mapping

**参照**：[tests/v1-metatavu-scim.sh](../tests/v1-metatavu-scim.sh)

### 2.1 テスト結果

| Test | 内容 | 結果 | HTTP | メモ |
|---|---|:---:|---|---|
| Test 1 | SCIM Realm API 有効性 | ⏳ | | |
| Test 2 | SCIM POST /Users（標準属性）| ⏳ | | |
| Test 3 | SCIM POST /Users（カスタム属性）| ⏳ | | |
| Test 4 | SCIM PATCH で active=false | ⏳ | | |

### 2.2 判定

- **総合**：⏳ PASS / FAIL / PARTIAL
- **Fallback**：⏳ 不要 / 代替 A（Custom Authenticator SPI で自動セット）/ 代替 B（Custom Schema）/ 代替 C（LDAP 経由）
- **Phase 1 実装への影響**：⏳

### 2.3 詳細ログ

```
[貼り付け予定]
```

---

## 3. V2: Sync Mode Override

**参照**：[tests/v2-sync-mode-override.sh](../tests/v2-sync-mode-override.sh)

### 3.1 テスト結果

| Test | 内容 | 結果 | HTTP | メモ |
|---|---|:---:|---|---|
| Test 1 | IdP 作成（Sync Mode = FORCE）| ⏳ | | |
| Test 2 | 通常 Mapper 作成 | ⏳ | | |
| Test 3 | Sync Mode Override Mapper 作成 | ⏳ | | |
| Test 4 | 設定保存確認 | ⏳ | | |

### 3.2 判定

- **総合**：⏳ PASS / FAIL / PARTIAL
- **Fallback**：⏳ 不要 / Realm 全体 IMPORT 化
- **Phase 1 実装への影響**：⏳

### 3.3 詳細ログ

```
[貼り付け予定]
```

---

## 4. V3': Custom Authenticator SPI

**参照**：[tests/v3-custom-authenticator.sh](../tests/v3-custom-authenticator.sh)

### 4.1 テスト結果

| Test | 内容 | 結果 | メモ |
|---|---|:---:|---|
| Test 1 | SPI ロード確認 | ⏳ | |
| Test 2 | Browser Flow への組込 | ⏳ | |
| Test 3 | 事前状態確認 | ⏳ | |
| Test 4 | Direct Access Grant ログイン | ⏳ | |
| 手動 | ブラウザ経由ログイン → last_login 反映 | ⏳ | |

### 4.2 判定

- **総合**：⏳ PASS / FAIL / PARTIAL
- **Fallback**：⏳ 不要 / 案 A（enlistAfterCompletion）/ 案 C（外部 DB 別管理）
- **Phase 1 実装への影響**：⏳

### 4.3 詳細ログ

```
[貼り付け予定]
```

---

## 5. Phase 1 実装計画への影響

### 5.1 SCIM プラグイン選定

- 採用：⏳ Metatavu keycloak-scim-server / Keycloak 26 native SCIM Realm API / その他
- 選定理由：⏳
- 追加工数：⏳ なし / +Xw

### 5.2 SPI 実装方式

- 採用：⏳ 案 A（enlistAfterCompletion）/ **案 B（Custom Authenticator SPI）** / 案 C（外部 DB）
- 選定理由：⏳
- 追加工数：⏳ なし / +Xw

### 5.3 Fallback 発動状況

| 項目 | 発動 | 対応 |
|---|:---:|---|
| V1 Fallback | ⏳ | |
| V2 Fallback | ⏳ | |
| V3' Fallback | ⏳ | |

---

## 6. 既存ドキュメントへの反映

- [ ] [jit-scim §10.4.F 新設](../../../doc/common/jit-scim-coexistence-keycloak.md)（PoC 検証結果セクション）
- [ ] [hearing-checklist B-SCIM-7/8/9/10](../../../doc/requirements/hearing-checklist.md) の状態を ⏳ → 済み
- [ ] [ADR-025 §I.2](../../../doc/adr/025-scim-positioning-and-receive-stance.md) の PoC 検証結果を反映
- [ ] [ADR-060 §C.2.3](../../../doc/adr/060-auth-protocol-attack-path-residual-tbd.md) の SPI 実装方式を確定

---

## 7. 総合結論

### 7.1 SCIM は問題なく実装できるか

- 答え：⏳
- 根拠：⏳

### 7.2 JIT ユーザは削除できるか

- 答え：⏳
- 根拠：⏳

### 7.3 Phase 1 リリース可否

- 判定：⏳ GO / GO with Fallback / NO-GO
- 条件：⏳

---

**変更履歴**

| 日付 | 内容 |
|---|---|
| YYYY-MM-DD | 初版作成、V1/V2/V3' 実施 |
