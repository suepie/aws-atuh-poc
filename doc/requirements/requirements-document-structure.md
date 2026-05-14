# 要件定義資料の構成案（SSOT）

> 最終更新: 2026-05-13（SSOT 化：§0 ナラティブ / §8 依存関係 / §9 状態ダッシュボード / §10 ID 体系ルール を追加）
> 目的: 要件定義フェーズで作成すべきドキュメント体系・作成順序・**語る順序（ナラティブ）**・状態の単一情報源
> 位置付け: 本ドキュメントは要件定義フェーズの **SSOT (Single Source of Truth)**。プロセス（どう進めるか）は [requirements-process-plan.md](requirements-process-plan.md)、ヒアリング項目は [hearing-checklist.md](hearing-checklist.md) を参照。

---

## 0. 要件定義の語る順序（ナラティブ）

### 0.1 本基盤の北極星（全要件のトーン判断基準）

本基盤は **「絶対安全に、どんなアプリでも、効率よく認証し、運用負荷やコストがかからない」共通認証基盤** を目指す。すべての要件は次の 4 軸で評価する：

| 北極星の柱 | 解釈 |
|---|---|
| **絶対安全** | セキュリティ最優先（OAuth 2.1 / NIST SP 800-63B Rev 4 / 業界最新ベストプラクティス準拠）|
| **どんなアプリでも** | 認証フロー・IdP・クライアント種別の網羅性 |
| **効率よく認証** | 顧客追加・システム追加のフリクションレス |
| **運用負荷・コスト最小** | マネージド優先、自前運用は限定 |

すべての要件は **AWS マルチアカウント前提**で **Cognito / Keycloak OSS / Keycloak RHBK のいずれでも構成可能**な設計を採用する。proposal/ 配下の各ファイル / functional-requirements.md / non-functional-requirements.md の各セクションは、この 4 軸に対する立場を明示すること。

### 0.2 要件定義の 5 ステップ（語る順序）

要件定義書（`requirements-spec.md`）および対顧客説明資料は、以下の 5 ステップで論理を組み立てる。**「対応する認証フローを示す → それを実現する構成として Broker を採用 → 実装プラットフォームを選定」** が本フェーズの中核ストーリー。

```mermaid
flowchart LR
    S1["①<br/>対応する<br/>認証フロー"] --> S2["②<br/>対応する<br/>IdP 接続要件"]
    S2 --> S3["③<br/>Broker パターン<br/>採用根拠"]
    S3 --> S4["④<br/>Cognito vs<br/>Keycloak 選定"]
    S4 --> S5["⑤<br/>非機能要件<br/>(可用性 / DR / 性能 / セキュリティ / コスト)"]

    style S3 fill:#fff3e0,stroke:#e65100
    style S4 fill:#e3f2fd,stroke:#1565c0
```

### 0.3 各ステップで答える問いと参照先

| Step | 答える問い | 一次ソース | 補強ドキュメント |
|:---:|---|---|---|
| ① | **どんな認証フローに対応する基盤か？**（SPA / SSR / Mobile / M2M） | [functional-requirements.md §1.1 FR-AUTH 認証フロー](functional-requirements.md) | [auth-patterns.md](../common/auth-patterns.md)、[system-design-patterns.md](../common/system-design-patterns.md) |
| ② | **どんな顧客 IdP 構成に対応する基盤か？**（Entra ID / Okta / Google / SAML / LDAP） | [functional-requirements.md §2 FR-FED](functional-requirements.md) | [identity-broker-multi-idp.md](../common/identity-broker-multi-idp.md) |
| ③ | **なぜ Broker パターンか？**（代替案として個別連携 / Mesh / Fabric / BYOI と比較） | [identity-broker-multi-idp.md](../common/identity-broker-multi-idp.md) | [sso-implementation-types.md](../reference/sso-implementation-types.md)、[user-types-and-auth.md](../common/user-types-and-auth.md) |
| ④ | **Cognito か Keycloak か？**（要件 × 制約 × コスト） | [platform-selection-decision.md](platform-selection-decision.md) | [ADR-006](../adr/006-cognito-vs-keycloak-cost-breakeven.md)、[ADR-014](../adr/014-auth-patterns-scope.md)、[ADR-015](../adr/015-rhbk-validation-deferred.md) |
| ⑤ | **可用性・DR・性能・コストの目標は？** | [non-functional-requirements.md](non-functional-requirements.md) | [keycloak-network-architecture.md](../common/keycloak-network-architecture.md)、[ADR-010〜013](../adr/) |

### 0.4 ステップ ③（Broker 採用根拠）の論理構造

Broker パターン採用の根拠は ① と ② から導出される（独立した「Broker を採用する理由」ではない）:

| ①／② の要件 | 帰結 |
|---|---|
| FR-AUTH-001〜003 が Must（複数の Grant Type / Client 種別を統一的に提供） | OIDC/OAuth 標準実装の認可サーバーが必要 |
| FR-FED-010 が Must（複数顧客 IdP を並行運用） | 集約点が必要 = **Hub-and-Spoke** |
| FR-FED-011 が Must（顧客追加で各システム変更不要） | 各システムが見る issuer は 1 つ = **Broker が JWT 一元化** |
| FR-FED-009 が Must（IdP ごとのクレーム差異を吸収） | 属性変換層が必要 = **Broker の attribute mapping / Protocol Mapper** |

→ ①②③ の要件が確定すれば、Broker パターン採用は**自動的に導かれる**（選択というより必然）。Cognito vs Keycloak は ④ で「どの Broker 実装か」のみが残論点。

---

## 1. ドキュメント体系の全体像

```
doc/requirements/
├── 00-index.md                          ← 本フォルダのインデックス
│
├── [顧客向け要件定義提示・社内総括]
│   ├── proposal/                        ← 顧客向け要件定義 提示版（フォルダ化、章ごとにファイル分割）
│   │   ├── 00-index.md                  ← proposal SSOT（北極星・5 ステップ・章ナビ）
│   │   ├── 02-auth.md                   ← §2 認証
│   │   ├── 03-federation.md             ← §3 フェデレーション（§3.2 はサブ・サブ分割済）
│   │   ├── 04-mfa.md 〜 16-poc-note.md  ← §4〜§16
│   └── poc-summary-evaluation.md        ← 社内 PoC 総括評価（作成済、要件提示の裏どり資料）
│
├── [ヒアリング]
│   ├── requirements-hearing-strategy.md ← ヒアリング戦略（作成済み）
│   ├── hearing-phase-a.md               ← Phase A: 事業要件ヒアリング記録
│   ├── hearing-phase-b.md               ← Phase B: 技術要件ヒアリング記録
│   ├── hearing-phase-c.md               ← Phase C: 運用・セキュリティ要件記録
│   └── hearing-phase-d.md               ← Phase D: 最終判断会議記録
│
├── [要件定義書]
│   ├── requirements-spec.md             ← 要件定義書（本体）
│   ├── functional-requirements.md       ← 機能要件一覧
│   ├── non-functional-requirements.md   ← 非機能要件一覧
│   └── platform-selection-decision.md   ← プラットフォーム選定判断書
│
└── [付録]
    ├── migration-strategy.md            ← 移行戦略（既存 → 新基盤）
    └── cost-estimation.md               ← コスト見積もり（詳細版）
```

---

## 2. 各ドキュメントの概要と作成順序

### Phase 1: 顧客向け要件定義提示・社内総括（Week 1 前半）

| # | ドキュメント | 目的 | 状態 |
|---|------------|------|------|
| 1 | proposal/（フォルダ）| **顧客向け要件定義 提示版**（章ごとにファイル分割、FR/NFR と 1:1 対応で要件ベースライン提示） | 🚧 §2 / §3.1 / §3.2 記載済、他は骨格のみ |
| 2 | poc-summary-evaluation.md | **社内** PoC 成果総括（要件提示の裏どり資料、顧客には直接出さない） | ✅ 作成済み |

**proposal/ の構成**（[proposal/00-index.md](proposal/00-index.md) 参照）:
- 00-index.md = SSOT（はじめに・北極星・5 ステップ・章ナビ）
- 02-auth.md = §2 認証（§2.1 認証フロー / §2.2 パスワード）
- 03-federation.md = §3 フェデレーション（§3.1 IdP 接続 / §3.2.1 JIT / §3.2.2 属性マッピング / §3.2.3 MFA 重複回避 / §3.3 マルチテナント運用）
- 04-mfa.md = §4 MFA（§4.1 要素 / §4.2 適用ポリシー）
- **05-sso.md = §5 SSO**（§5.1 同一 IdP / §5.2 クロス IdP）
- **06-logout-session.md = §6 ログアウト・セッション管理**（§6.1 ログアウト 4 レイヤー / §6.2 ライフサイクル / §6.3 Revocation）
- 07-authz.md = §7 認可（§7.1 基本 / §7.2 細粒度）
- 08-user.md = §8 ユーザー管理（§8.1〜§8.4）
- 09-admin.md = §9 管理機能（§9.1〜§9.3）
- 10-integration.md = §10 外部統合（§10.1〜§10.3）
- 11-architecture.md = §11 Identity Broker
- 12-platform.md = §12 実装プラットフォーム
- 13-nfr.md = §13 非機能要件（§13.1〜§13.9）
- 14-tbd-summary.md = §14 TBD まとめ
- 15-schedule.md = §15 スケジュール
- 16-poc-note.md = §16 PoC 控えめ

**注**: 旧 §5 SSO・ログアウト を §5 SSO と §6 ログアウト・セッション管理 に分割（2026-05-13）。FR-SSO/LOGOUT カテゴリは ID 体系維持。

**各サブセクション**: "**ベースライン**" + "**TBD / 要確認**" の対構造。詳細マトリクスは functional-requirements.md / non-functional-requirements.md へリンク委譲。

**各章の冒頭規約（§X.0 前提と背景）**: proposal/ 配下の各章（§2〜§16）は冒頭に **§X.0「前提と背景」**を必ず置く。構成：
1. **用語整理** — 本章で扱う概念の定義（共通認証基盤の文脈で）
2. **なぜここ（§X）で決めるか** — 他章との関係を mermaid で図化
3. **本章で扱うサブセクションの一覧**

理由：顧客は認証技術の専門家ではないため、各章でいきなり要件案を出すと「なぜそれを決める必要があるのか」が伝わらず合意取りが空回りする。事前に共通理解を作ってから本論に入る。

### Phase 2: ヒアリング実施（Week 1-3）

| # | ドキュメント | 目的 | 作成タイミング |
|---|------------|------|-------------|
| 3 | requirements-hearing-strategy.md | ヒアリング計画 | ✅ 作成済み |
| 4 | hearing-phase-a.md | 事業要件の確認結果 | Week 1 ヒアリング後 |
| 5 | hearing-phase-b.md | 技術要件の確認結果 | Week 2 ヒアリング後 |
| 6 | hearing-phase-c.md | 運用・セキュリティ要件の確認結果 | Week 3 ヒアリング後 |

### Phase 3: 要件定義書作成（Week 3-4）

| # | ドキュメント | 目的 | 作成タイミング |
|---|------------|------|-------------|
| 7 | requirements-spec.md | 要件定義書（本体） | ヒアリング完了後 |
| 8 | functional-requirements.md | 機能要件の詳細 | 7 と並行 |
| 9 | non-functional-requirements.md | 非機能要件の詳細 | 7 と並行 |
| 10 | platform-selection-decision.md | Cognito / Keycloak 最終判断 | 要件確定後 |

### Phase 4: 付録・補足資料（Week 4-5）

| # | ドキュメント | 目的 | 作成タイミング |
|---|------------|------|-------------|
| 11 | migration-strategy.md | 既存システムからの移行戦略 | 要件確定後 |
| 12 | cost-estimation.md | 詳細コスト見積もり | プラットフォーム確定後 |

---

## 3. 要件定義書（requirements-spec.md）の構成案

要件定義の中核ドキュメント。ヒアリング結果を統合して作成する。

```markdown
# 共有認証基盤 要件定義書

## 1. はじめに
  1.1 文書の目的
  1.2 対象範囲
  1.3 用語定義
  1.4 関連ドキュメント

## 2. ビジネス要件
  2.1 プロジェクトの背景と目的
  2.2 対象システム一覧
  2.3 ステークホルダー
  2.4 ビジネス上の制約（予算・期限・法規制）

## 3. システム概要
  3.1 システム構成図（PoC architecture.md ベース）
  3.2 認証基盤の責任範囲
  3.3 利用システムの責任範囲
  3.4 責任分界点

## 4. 機能要件（→ functional-requirements.md で詳細化）
  4.1 認証機能
    - ローカルユーザー認証
    - フェデレーション認証（Entra ID / Okta / SAML）
    - MFA（TOTP / WebAuthn / SMS）
    - SSO（シングルサインオン / シングルログアウト）
  4.2 認可機能
    - JWT クレーム設計
    - ロールベースアクセス制御
    - テナント分離
  4.3 ユーザー管理機能
    - プロビジョニング（JIT / SCIM / 手動）
    - ユーザー属性管理
    - セルフサービス（パスワードリセット等）
  4.4 テナント管理機能
    - IdP 追加・削除
    - テナント設定管理
  4.5 管理者機能
    - 管理コンソール
    - 監査ログ閲覧
    - 設定変更

## 5. 非機能要件（→ non-functional-requirements.md で詳細化）
  5.1 可用性（SLA / HA 構成）
  5.2 性能（応答時間 / スループット / 同時接続数）
  5.3 拡張性（MAU スケール / IdP 追加 / リージョン追加）
  5.4 セキュリティ
    - トークン管理（TTL / Revocation / ストレージ）
    - 通信暗号化（TLS / mTLS）
    - データ暗号化（at-rest / in-transit）
    - 監査ログ（保存期間 / 改ざん防止）
    - ブルートフォース対策
  5.5 DR / BCP
    - RTO / RPO 目標
    - フェイルオーバー方式
    - バックアップ戦略
  5.6 運用性
    - 監視・アラート
    - ログ管理
    - バージョンアップ方針
    - 変更管理プロセス
  5.7 互換性・移行性
    - 既存システムとの互換性
    - 段階的移行のサポート

## 6. 外部インターフェース
  6.1 利用システムとのインターフェース（OIDC / JWT）
  6.2 外部 IdP とのインターフェース（OIDC / SAML）
  6.3 管理系 API

## 7. データ要件
  7.1 ユーザーデータ（保存項目 / 保存期間 / 暗号化）
  7.2 セッションデータ
  7.3 監査ログデータ
  7.4 データフロー図

## 8. 制約事項
  8.1 技術的制約（AWS リージョン / マネージドサービス制約）
  8.2 法的制約（個人情報保護法 / 業界規制）
  8.3 組織的制約（運用体制 / スキルセット）

## 9. 前提条件
  9.1 PoC で確認済みの前提
  9.2 本番で追加検証が必要な事項

## 10. リスクと対策
  10.1 技術リスク
  10.2 運用リスク
  10.3 ビジネスリスク

## 11. プラットフォーム選定（→ platform-selection-decision.md で詳細化）
  11.1 評価基準と重み付け
  11.2 Cognito / Keycloak 比較スコアリング
  11.3 推奨と根拠

## 12. ロードマップ
  12.1 マイルストーン
  12.2 フェーズ分割（設計 → 開発 → テスト → 移行 → 運用開始）
  12.3 依存関係
```

---

## 4. 機能要件一覧（functional-requirements.md）の構成案

機能要件の **実体（ID 一覧・優先度・PoC 状況）は [functional-requirements.md](functional-requirements.md) を一次ソース**とする。本セクションでは構成原則のみを示す。

### 4.1 カテゴリ体系（FR）

各カテゴリは性質ごとにサブセクション化されている（[functional-requirements.md](functional-requirements.md) 参照）。

| § | カテゴリ | 接頭辞 | サブセクション |
|---|---|---|---|
| 1 | 認証 | `FR-AUTH-*` | §1.1 認証フロー / §1.2 パスワード・ローカル管理 |
| 2 | フェデレーション | `FR-FED-*` | §2.1 IdP 接続種別 / §2.2 ユーザー処理 / §2.3 マルチテナント運用 |
| 3 | MFA | `FR-MFA-*` | §3.1 MFA 要素 / §3.2 適用ポリシー |
| 4 | SSO・ログアウト | `FR-SSO-*` | §4.1 SSO / §4.2 ログアウト / §4.3 セッション管理 |
| 5 | 認可 | `FR-AUTHZ-*` | §5.1 クレームベース基本認可 / §5.2 細粒度認可 |
| 6 | ユーザー管理 | `FR-USER-*` | §6.1 CRUD / §6.2 属性・ロール / §6.3 セルフサービス / §6.4 プロビジョニング |
| 7 | 管理機能 | `FR-ADMIN-*` | §7.1 基盤設定管理 / §7.2 監査 / §7.3 委譲・カスタマイズ |
| 8 | 外部統合 | `FR-INT-*` | §8.1 プロトコル準拠 / §8.2 ログ・監視 / §8.3 API・IaC・Webhook |

### 4.2 表項目の必須カラム

functional-requirements.md の各表は以下のカラムを必ず持つ:

| カラム | 用途 |
|---|---|
| ID | `FR-{CAT}-NNN` |
| 要件 | 短い記述 |
| 優先度 | Must / Should / Could / Won't / TBD（凡例は functional-requirements.md §凡例） |
| Cognito 列 | ✅ / ⚠ / ❌ + 実現方法の手がかり |
| Keycloak 列 | 同上 |
| PoC | 検証 Phase or ❌ |
| 状態 | ✅ 確定 / 🟡 デフォルト / 🔴 TBD |

---

## 5. 非機能要件一覧（non-functional-requirements.md）の構成案

非機能要件の **実体は [non-functional-requirements.md](non-functional-requirements.md) を一次ソース**とする。本セクションでは構成原則のみを示す。

### 5.1 カテゴリ体系（NFR）

性質が混在するカテゴリはサブセクション化されている（[non-functional-requirements.md](non-functional-requirements.md) 参照）。

| § | カテゴリ | 接頭辞 | サブセクション |
|---|---|---|---|
| 1 | 可用性 | `NFR-AVL-*` | （フラット）|
| 2 | 性能 | `NFR-PERF-*` | §2.1 応答時間 / §2.2 スループット |
| 3 | 拡張性 | `NFR-SCL-*` | （フラット）|
| 4 | セキュリティ | `NFR-SEC-*` | §4.1 暗号化・鍵管理 / §4.2 トークン・セッション / §4.3 攻撃対策 / §4.4 ネットワーク・境界制御 |
| 5 | DR / BCP | `NFR-DR-*` | （フラット）|
| 6 | 運用 | `NFR-OPS-*` | §6.1 監視・ロギング / §6.2 デプロイ・パッチ / §6.3 体制・運用 SLA |
| 7 | 法務 / コンプラ | `NFR-COMP-*` | §7.1 規制・法令対応 / §7.2 業界認定・監査 / §7.3 データガバナンス |
| 8 | コスト | `NFR-COST-*` | （フラット）|
| 9 | 移行性 | `NFR-MIG-*` | （フラット）|

### 5.2 表項目の必須カラム

| カラム | 用途 |
|---|---|
| ID | `NFR-{CAT}-NNN` |
| 要件 | 短い記述 |
| 目標値 | 数値 or 定性記述（TBD 可） |
| Cognito での実現方法 | |
| Keycloak での実現方法 | |
| PoC 状況 | 計測値 or 未計測 |
| 状態 | ✅ / 🟡 / 🔴 |

---

## 6. プラットフォーム選定判断書（platform-selection-decision.md）の構成案

```markdown
# プラットフォーム選定判断書

## 1. 評価基準

| # | 評価基準 | 重み | 説明 |
|---|---------|------|------|
| 1 | コスト（初期 + 運用） | 高 | 3 年 TCO で比較 |
| 2 | 可用性・SLA | 高 | 可用性目標の達成可否 |
| 3 | カスタマイズ性 | 中 | クレーム・ログイン画面・フロー |
| 4 | 運用負荷 | 高 | 日常運用 + 障害対応の工数 |
| 5 | マルチ IdP 対応 | 中 | 顧客 IdP の種類への対応力 |
| 6 | DR コスト | 中 | DR 構成の追加コスト |
| 7 | エコシステム | 低 | AWS サービス統合 / OSS 連携 |
| 8 | ベンダーロックイン | 低 | 将来の移行可能性 |

## 2. スコアリング（ヒアリング結果を反映して記入）

| 評価基準 | Cognito | Keycloak | 判定 |
|---------|---------|----------|------|
| ... | ... | ... | ... |

## 3. 総合判定と推奨

## 4. リスク・懸念事項

## 5. 承認
```

---

## 7. 作成スケジュール

```
Week 0 (現在):
  ✅ poc-summary-evaluation.md
  ✅ requirements-hearing-strategy.md
  ✅ requirements-document-structure.md（本ドキュメント、SSOT 化）
  🚧 proposal/（顧客向け要件定義 提示版、章ごとファイル化、§2/§3.1/§3.2 記載済）

Week 1:
  📋 proposal/ 各章のサブセクションごとに合意取り＆中身埋め
  📋 hearing-phase-a.md（事業要件ヒアリング実施後）

Week 2:
  📋 hearing-phase-b.md（技術要件ヒアリング実施後）

Week 3:
  📋 hearing-phase-c.md（運用・セキュリティ要件ヒアリング実施後）
  📋 requirements-spec.md（ドラフト着手）
  📋 functional-requirements.md
  📋 non-functional-requirements.md

Week 4:
  📋 hearing-phase-d.md（最終判断会議）
  📋 platform-selection-decision.md
  📋 requirements-spec.md（確定版）

Week 5:
  📋 migration-strategy.md
  📋 cost-estimation.md
```

---

## 8. ドキュメント間の依存関係と読み順

### 8.1 読み順（新規参画者向け）

要件定義フェーズに新たに加わる人が最短で把握するための推奨読み順:

```mermaid
flowchart TD
    R0["1. 本ドキュメント §0 ナラティブ<br/>(全体ストーリー把握)"]
    R1["2. poc-summary-evaluation.md<br/>(PoC 成果と不足箇所)"]
    R2["3. functional-requirements.md<br/>(対応する機能の範囲)"]
    R3["4. identity-broker-multi-idp.md<br/>(Broker パターン採用根拠)"]
    R4["5. non-functional-requirements.md<br/>(可用性 / DR / セキュリティ / コスト)"]
    R5["6. platform-selection-decision.md<br/>(Cognito vs Keycloak)"]
    R6["7. requirements-process-plan.md<br/>(進め方・終了基準)"]
    R7["8. hearing-checklist.md<br/>(残 TBD 項目)"]

    R0 --> R1 --> R2 --> R3 --> R4 --> R5 --> R6 --> R7
```

### 8.2 書く順序（作成依存関係）

ドキュメント間の依存（A が B の前提）:

```mermaid
flowchart LR
    PoC["poc-summary-<br/>evaluation.md"]

    Strategy["requirements-<br/>hearing-strategy.md"]
    Checklist["hearing-<br/>checklist.md"]
    Process["requirements-<br/>process-plan.md"]
    Structure["requirements-<br/>document-structure.md<br/>(本 SSOT)"]

    FR["functional-<br/>requirements.md"]
    NFR["non-functional-<br/>requirements.md"]

    Vendor["rhbk-vendor-<br/>inquiry.md"]

    Hearing["hearing-phase-<br/>a/b/c/d.md"]

    Platform["platform-selection-<br/>decision.md"]
    Spec["requirements-<br/>spec.md"]

    PoC --> Structure
    PoC --> Strategy
    Strategy --> Checklist
    Structure --> FR
    Structure --> NFR
    Structure --> Process
    Process --> Hearing
    Checklist --> Hearing
    Vendor --> Platform
    Hearing --> FR
    Hearing --> NFR
    Hearing --> Platform
    FR --> Spec
    NFR --> Spec
    Platform --> Spec

    style Structure fill:#fff3e0,stroke:#e65100
    style Spec fill:#e3f2fd,stroke:#1565c0
```

---

## 9. ドキュメント状態ダッシュボード

> 各ドキュメントの作成・更新状況を一元管理。状態は実際の作成状況に応じて更新する。

### 9.1 顧客向け要件定義提示・社内総括

| ドキュメント | 役割 | 状態 | 最終更新 |
|---|---|:---:|---|
| **[proposal/](proposal/00-index.md)** ⭐ | **顧客向け要件定義 提示版**（フォルダ化、章ごとファイル分割、FR/NFR と 1:1 対応）| 🚧 §2 / §3 / §4 / §5 / §6 記載済、§7〜§16 骨格のみ | 2026-05-13 |
| [poc-summary-evaluation.md](poc-summary-evaluation.md) | **社内** PoC 成果総括・不足箇所分析（要件提示の裏どり） | ✅ Done | 2026-05-13 |

### 9.2 ヒアリング

| ドキュメント | 役割 | 状態 | 最終更新 |
|---|---|:---:|---|
| [requirements-hearing-strategy.md](requirements-hearing-strategy.md) | Phase A〜D の進め方 | ✅ Done | 2026-04-21 |
| [hearing-checklist.md](hearing-checklist.md) | 全 67 項目の TBD 一覧 | ✅ Done | 2026-05-13 |
| hearing-phase-a.md | 事業要件ヒアリング記録 | ⏳ 未実施 | — |
| hearing-phase-b.md | 技術要件ヒアリング記録 | ⏳ 未実施 | — |
| hearing-phase-c.md | 運用・セキュリティ要件記録 | ⏳ 未実施 | — |
| hearing-phase-d.md | 最終判断会議記録 | ⏳ 未実施 | — |

### 9.3 要件定義書

| ドキュメント | 役割 | 状態 | 最終更新 |
|---|---|:---:|---|
| **requirements-document-structure.md（本 SSOT）** | 構成・ナラティブ・状態 | 🔄 SSOT 化済（継続更新） | 2026-05-13 |
| [requirements-process-plan.md](requirements-process-plan.md) | 4 段階プロセス・終了基準 | ✅ Done | 2026-05-08 |
| [functional-requirements.md](functional-requirements.md) | 機能要件一覧（~75 件、全 8 カテゴリ サブセクション化済） | 🔄 ヒアリング待ち（TBD 多数） | 2026-05-13 |
| [non-functional-requirements.md](non-functional-requirements.md) | 非機能要件一覧（~75 件、SEC/PERF/OPS/COMP サブセクション化済） | 🔄 ヒアリング待ち（TBD 多数） | 2026-05-13 |
| [platform-selection-decision.md](platform-selection-decision.md) | Cognito / Keycloak 選定判断 | 🚧 ドラフト（評価基準のみ） | 2026-05-08 |
| [rhbk-vendor-inquiry.md](rhbk-vendor-inquiry.md) | Red Hat 問い合わせ文面 | ✅ Done（送付待ち） | — |
| requirements-spec.md | 要件定義書本体 | 📋 未着手 | — |

### 9.4 付録

| ドキュメント | 役割 | 状態 |
|---|---|:---:|
| migration-strategy.md | 既存システムからの移行戦略 | 📋 未着手 |
| cost-estimation.md | 詳細コスト見積もり | 📋 未着手 |

### 9.5 状態凡例

| 記号 | 意味 |
|:---:|---|
| ✅ Done | 完成。継続的な微修正のみ |
| 🔄 進行中 | 主要内容は揃っているが、ヒアリング結果等で更新中 |
| 🚧 ドラフト | 骨格はあるが内容未確定 |
| ⏳ 未実施 | 前提イベント（ヒアリング等）待ち |
| 📋 未着手 | 着手予定 |

---

## 10. ID 体系と改廃ルール

### 10.1 ID 体系（横断ルール）

| 種別 | 形式 | 例 | 採番ルール |
|---|---|---|---|
| 機能要件 | `FR-{CAT}-NNN` | `FR-AUTH-002` | カテゴリごとに連番。**一度採番した ID は再利用しない**（廃止時も欠番として残す） |
| 非機能要件 | `NFR-{CAT}-NNN` | `NFR-AVL-001` | 同上 |
| ADR | `ADR-NNN` | `ADR-012` | プロジェクト横断連番 |
| ヒアリング | `{Phase}-NNN` | `B-104` | Phase（A/B/C/D）+ 連番 |

### 10.2 サブセクション化の指針

要件群の性質が同一カテゴリ内で分かれる場合、ID は連続のまま**サブセクションで分ける**（既存参照を破壊しない）。

**実例**:
- **FR-AUTH-001〜014**: 001〜008 は OAuth/OIDC フロー、009〜014 はパスワード・ローカル管理。意味は別物だが既に番号参照されているため、ID は維持し §1.1/§1.2 でサブセクション化（2026-05-13）。
- **FR-FED §2.1/§2.2/§2.3**: IdP 接続種別 / ユーザー処理 / マルチテナント運用に分割（2026-05-13）。
- **FR-MFA §3.1/§3.2**: MFA 要素 / 適用ポリシーに分割（2026-05-13）。
- **FR-SSO §4.1/§4.2/§4.3**: SSO / ログアウト / セッション管理に分割（2026-05-13）。
- **FR-AUTHZ §5.1/§5.2**: クレームベース基本認可 / 細粒度認可に分割（2026-05-13）。
- **FR-USER §6.1〜§6.4**: CRUD / 属性・ロール / セルフサービス / プロビジョニングに分割（2026-05-13）。
- **FR-ADMIN §7.1/§7.2/§7.3**: 基盤設定 / 監査 / 委譲・カスタマイズに分割（2026-05-13）。
- **FR-INT §8.1/§8.2/§8.3**: プロトコル / ログ・監視 / API・IaC・Webhook に分割（2026-05-13）。
- **NFR-PERF §2.1/§2.2**: 応答時間 / スループットに分割（2026-05-13）。
- **NFR-SEC §4.1〜§4.4**: 暗号化 / トークン・セッション / 攻撃対策 / ネットワークに分割（2026-05-13）。
- **NFR-OPS §6.1〜§6.3**: 監視 / デプロイ / 体制に分割（2026-05-13）。
- **NFR-COMP §7.1〜§7.3**: 規制 / 業界認定 / データガバナンスに分割（2026-05-13）。

### 10.3 ドキュメント追加時の手順

1. 本 SSOT §9 ダッシュボードに行を追加
2. §1 体系図に位置づけを追記
3. §0 ナラティブのどの Step に対応するか明記
4. 他ドキュメントからのリンクが必要なら追記

### 10.4 ドキュメント廃止時の手順

1. ファイル削除前に**廃止理由とリンク先を本 SSOT に残す**（短い「廃止」エントリ）
2. 他ドキュメントからのリンクを grep で洗い出して更新
3. doc/old/ への移動も選択肢（読み取り専用扱い）

---

## 11. 関連ドキュメント

- [requirements-process-plan.md](requirements-process-plan.md): 要件定義の進め方（4 段階）
- [requirements-hearing-strategy.md](requirements-hearing-strategy.md): ヒアリング戦略
- [hearing-checklist.md](hearing-checklist.md): ヒアリング項目（単一一覧）
- [functional-requirements.md](functional-requirements.md): 機能要件
- [non-functional-requirements.md](non-functional-requirements.md): 非機能要件
- [platform-selection-decision.md](platform-selection-decision.md): プラットフォーム選定
- [poc-summary-evaluation.md](poc-summary-evaluation.md): PoC 総括
