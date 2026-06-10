# 認証側への申し送り SSOT（内部裏調整用）

> **位置付け**：本標準（API プラットフォーム）の要件定義の中で、**共有認証基盤側（doc/requirements/）で要件化・対応を依頼すべき項目**を集約した内部 SSOT。
> **対象**：API プラットフォーム / 認証基盤 両方の要件定義チーム。
> **PowerPoint への露出**：**しない**（裏調整、ステークホルダー向けスライドには出さない）。
> **更新基準**：本標準のヒアリング結果で新たな依存・申し送り事項が発生した時点。

---

## 0. なぜこのドキュメントが必要か

本標準は **共有認証基盤の利用側**として位置づけられるため（[proposal/common/03-shared-auth-boundary.md §C-API-3](proposal/common/03-shared-auth-boundary.md)）、本標準の要件確定には**認証基盤側の対応**が前提となる項目が存在する。

これらを：

- ✅ 本標準内では「**依存・申し送り事項**」として記録
- ✅ 認証側 SSOT（`../requirements/requirements-document-structure.md`）への提起内容として整理
- ✅ 認証側ヒアリング・要件定義の進捗と sync

本ドキュメントは、その**裏調整の SSOT**。

---

## 1. 申し送り項目一覧（優先度順）

### 1.1 Partner M2M Client 管理機能 ★ 条件付き（M2M 要件化の場合のみ）

> **発生章**：[proposal/fr/02-authn-authz.md §2.2](proposal/fr/02-authn-authz.md), [proposal/common/03-shared-auth-boundary.md §C-3.1 C](proposal/common/03-shared-auth-boundary.md)
> **前提**：API-A-112 / A-113 のヒアリングで Partner B2B M2M がスコープに含まれることが確認された場合のみ
> **状態**：⏳ M2M スコープ確認待ち

#### 認証側現状調査結果（2026-06-03 時点）

| 観点 | 認証側現状 | 本標準ニーズ | ギャップ |
|---|---|---|:---:|
| OAuth Client Credentials Grant プロトコル認識 | ✅ §FR-1.1 C / FR-AUTH-004 Must / §FR-6.3.2 | 同左 | ✅ |
| Confidential Client / Service Account の概念 | ✅ auth-patterns.md §2.0-2.1 | 同左 | ✅ |
| 「Partner（外部企業 B2B）」の独立カテゴリ | ❌ 不在 | 必要 | 🔴 |
| Per-Partner-App × Per-Environment 識別単位 | ❌ 不在 | 必要 | 🔴 |
| Credential ローテーション周期 / Overlap Period | ❌ 不在 | 必要 | 🔴 |
| Credential Revocation API | ❌ 不在 | 必要 | 🔴 |
| Self-service オンボーディングポータル | ❌ 不在 | 必要 | 🔴 |
| OAuth scope per Partner | ⚠ プロトコル機能のみ | 細粒度管理 | 🟡 |
| 一般的 Client 管理機能 | ✅ FR-ADMIN-004 / §FR-8.1 | 同左 | ✅ |

#### 提案：認証側への追加要件（M2M 要件化された場合）

| # | 提案項目 | 認証側で配置すべき章 | 新規 / 拡張 |
|---|---|---|:---:|
| 1 | **Partner を独立カテゴリ「P-7」として追加** | user-types-and-auth.md / hearing-checklist §1.1〜1.3 | **新規** |
| 2 | Partner M2M App Client 物理単位 | §FR-2.3 マルチテナント運用に「Partner 軸」追加 | 拡張 |
| 3 | Per-Partner-App × Per-Env 識別単位 | §FR-2.3 / §FR-8.1 | 拡張 |
| 4 | Partner Client 台帳 API | §FR-8.1 基盤設定管理（FR-ADMIN-004 拡張）| 拡張 |
| 5 | Credential ローテーション周期 / Overlap | §FR-8.1 + §NFR-4 セキュリティ | 拡張 |
| 6 | Revocation API（24h 以内対応）| §FR-8.1 + §NFR-4 | 拡張 |
| 7 | Self-service Partner オンボーディングポータル | §FR-7.3 セルフサービス機能 / 新章 §FR-Partner | **新規** |
| 8 | scope per Partner（細粒度）| §FR-6 認可 | 拡張 |

#### 進捗管理

- [ ] **A-112 / A-113 ヒアリング実施**（Partner B2B M2M スコープ確認）
- [ ] 認証側との合議 setup
- [ ] 認証側で「Partner P-7」カテゴリ追加合意
- [ ] 認証側の関連章（§FR-2.3 / §FR-8.1 / §FR-6）への要件追加
- [ ] Self-service ポータル要件化判断（新章 §FR-Partner 立ち上げ要否）

---

### 1.2 Hosted UI 提供有無

> **発生章**：[proposal/fr/02-authn-authz.md §2.B](proposal/fr/02-authn-authz.md), [proposal/common/03-shared-auth-boundary.md §C-3.1 B](proposal/common/03-shared-auth-boundary.md)
> **状態**：⏳ 認証側方針確認待ち

本標準は「**アプリ UI を持たない**」をデフォルトとしている（業界主流：Salesforce / Workday / ServiceNow / Slack / Notion 等が Hosted UI 委譲）。これを成立させるため、認証基盤側の Hosted UI 提供が前提となる。

#### 認証側で確定が必要な項目

| 項目 | 認証側で確定すべき内容 | 本標準への影響 |
|---|---|---|
| **Hosted UI 提供有無** | Cognito Hosted UI / Keycloak login page の提供 | アプリ UI を持たないデフォルトの成立条件 |
| **サインアップ UI 提供有無** | B2C / Trial 向けの新規登録フォーム | サインアップ要件があるアプリの設計指針 |
| **HRD（Home Realm Discovery）ページ所在** | 認証基盤側か、本標準アプリ側か | パターン C 採用時の責任分界 |
| **パスワードリセット UI 提供有無** | パスワードリセット要求フォーム | アプリ UI 不要な範囲の確定 |

#### 進捗管理

- [ ] 認証側で Hosted UI 提供方針確定
- [ ] サインアップ UI 提供有無確定
- [ ] HRD ページ所在確定
- [ ] 本標準 §2.B のデフォルト「アプリ UI を持たない」確定

---

### 1.3 JWKS プライベート化方針

> **発生章**：[proposal/fr/02-authn-authz.md §2.1](proposal/fr/02-authn-authz.md), [proposal/common/03-shared-auth-boundary.md §C-3.1 A](proposal/common/03-shared-auth-boundary.md)
> **状態**：⏳ 認証側 PoC 結果待ち

本標準の JWT 検証方式は、認証側で JWKS endpoint が Public か Private かで変わる。PoC 段階で Private 化を検討中。

#### 進捗管理

- [ ] 認証側で JWKS プライベート化最終判断
- [ ] Private 化された場合の本標準側取得方式確定（API-B-203）

---

### 1.4 認証基盤側 SLA

> **発生章**：[proposal/common/03-shared-auth-boundary.md §C-3.1.2](proposal/common/03-shared-auth-boundary.md)
> **状態**：🟡 暫定値で進行中

本標準の §NFR-API-1 可用性 / §C-3.3 障害分離は認証基盤側 SLA に依存する。

| 項目 | 本標準の暫定想定 | 認証側で確定要 |
|---|---|---|
| Discovery / JWKS 可用性 | 99.99% | ⏳ |
| JWT 発行レイテンシ p99 | < 500ms | ⏳ |
| Hosted UI 可用性 | 99.95% | ⏳ |
| 鍵ローテーション通知期間 | 30 日 | ⏳ |
| Partner App Client 発行リードタイム | 1 営業日以内 | ⏳ |

#### 進捗管理

- [ ] 認証側で SLA 確定
- [ ] 本標準 §C-3.1.2 を確定値で更新

---

## 2. 申し送りプロセス

### 2.1 タイミング

| 段階 | アクション |
|---|---|
| **本標準ヒアリング前** | A-112 / A-113 等の依存項目を整理、認証側に「依存事項あり」を共有 |
| **本標準ヒアリング後** | A-112 / A-113 等の確認結果に応じて、認証側に要件追加を正式提起 |
| **認証側要件確定後** | 本標準の §2.2 / §C-3.1 等を確定値で更新、PowerPoint へも反映 |

### 2.2 認証側との合議の場

- 認証側 SSOT（[../requirements/requirements-document-structure.md](../requirements/requirements-document-structure.md)）の更新依頼
- 認証側ヒアリング項目（[../requirements/hearing-checklist.md](../requirements/hearing-checklist.md)）への新規項目追加依頼
- 認証側ヒアリングと本標準ヒアリングの sync（API-A-112 / 113 結果共有）

---

## 3. 関連ドキュメント

### 本標準側

- [proposal/fr/02-authn-authz.md §2.2 Partner 認証](proposal/fr/02-authn-authz.md)
- [proposal/fr/02-authn-authz.md §2.B 未認証エンドポイントの標準保護パターン](proposal/fr/02-authn-authz.md)
- [proposal/common/03-shared-auth-boundary.md §C-3.1](proposal/common/03-shared-auth-boundary.md)
- [hearing-checklist.md Phase A](hearing-checklist.md)

### 認証側

- [../requirements/00-index.md](../requirements/00-index.md)
- [../requirements/hearing-checklist.md](../requirements/hearing-checklist.md)
- [../requirements/proposal/fr/08-admin.md FR-ADMIN-004 Client 管理](../requirements/proposal/fr/08-admin.md)
- [../requirements/proposal/fr/02-federation.md §FR-2.3 マルチテナント](../requirements/proposal/fr/02-federation.md)
- [../requirements/proposal/fr/06-authz.md §FR-6.3 認可](../requirements/proposal/fr/06-authz.md)

---

## 4. 改訂履歴

| 日付 | 内容 |
|---|---|
| 2026-06-03 | 初版作成。Partner M2M Client 管理（条件付き、M2M 要件化の場合のみ）/ Hosted UI 提供 / JWKS プライベート化 / 認証側 SLA の 4 項目を申し送り SSOT 化 |
