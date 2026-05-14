# 共有認証基盤 要件定義 提示版（SSOT）

> 作成日: 2026-05-13
> 最終更新: 2026-05-14（フォルダ構造を fr/ nfr/ common/ に再編、章番号を §FR-X / §NFR-X / §C-X に統一）
> ステータス: 🚧 サブセクションごとに合意取り中
> 対象読者: 顧客（要件定義 初期合意フェーズ）
> 上位 SSOT: [../requirements-document-structure.md](../requirements-document-structure.md)

---

## 0. はじめに

### 0.1 本資料群の目的

共有認証基盤の構築にあたり、要件定義の初期合意を取るための **要件ベースライン提示資料**。各章は独立した md ファイルに分割し、本ファイル（00-index.md）が **proposal SSOT** として全章を統括する。

### 0.2 本基盤の北極星（Vision Statement）

本基盤は **「絶対安全に、どんなアプリでも、効率よく認証し、運用負荷やコストがかからない」共通認証基盤** を目指す。各機能・非機能要件は次の 4 軸で判断する：

| 北極星の柱 | 解釈 | 反映先 |
|---|---|---|
| **絶対安全** | セキュリティ最優先（業界最新ベストプラクティス準拠） | 各章の "ベースライン" は OAuth 2.1 / NIST SP 800-63B Rev 4 等を参照 |
| **どんなアプリでも** | 認証フロー・IdP・クライアント種別の網羅性 | [§FR-1 認証](fr/01-auth.md) / [§FR-2 フェデレーション](fr/02-federation.md) / [§C-1 Identity Broker](common/01-architecture.md) |
| **効率よく認証** | 顧客追加・システム追加のフリクションレス | [§FR-2.3 マルチテナント運用](fr/02-federation.md) / [§FR-4 SSO](fr/04-sso.md) |
| **運用負荷・コスト最小** | マネージド優先、自前運用は限定 | [§C-2 プラットフォーム選定軸](common/02-platform.md) / [§NFR-6 運用](nfr/06-operations.md) / [§NFR-8 コスト](nfr/08-cost.md) |

すべての要件は **AWS マルチアカウント前提**で **Cognito / Keycloak OSS / Keycloak RHBK のいずれでも構成可能**な設計を採用する。

### 0.3 本資料の読み方

各章のサブセクションは以下の対構造で記載する:

| ラベル | 内容 |
|---|---|
| **ベースライン** | 弊社が現時点で「こう定義したい」と提示する要件案（推奨値・想定範囲） |
| **TBD / 要確認** | 確定のために御社から教えていただく必要がある事項（ヒアリングで確定） |

詳細マトリクスは [../functional-requirements.md](../functional-requirements.md) / [../non-functional-requirements.md](../non-functional-requirements.md) にリンクで委譲し、本資料は要件の方向性合意に集中する。

### 0.4 フォルダ構造

```
proposal/
├── 00-index.md          ← 本ファイル（SSOT）
├── fr/                  ← 機能要件（§FR-1 〜 §FR-9）
│   ├── 01-auth.md
│   ├── 02-federation.md
│   ├── 03-mfa.md
│   ├── 04-sso.md
│   ├── 05-logout-session.md
│   ├── 06-authz.md
│   ├── 07-user.md
│   ├── 08-admin.md
│   └── 09-integration.md
├── nfr/                 ← 非機能要件（§NFR-1 〜 §NFR-9、IPA 6 大項目マッピング付き）
│   ├── 00-index.md
│   ├── 01-availability.md
│   ├── 02-performance.md
│   ├── 03-scalability.md
│   ├── 04-security.md
│   ├── 05-dr.md
│   ├── 06-operations.md
│   ├── 07-compliance.md
│   ├── 08-cost.md
│   └── 09-migration.md
└── common/              ← 横断（§C-1 〜 §C-5）
    ├── 01-architecture.md
    ├── 02-platform.md
    ├── 03-tbd-summary.md
    ├── 04-schedule.md
    └── 05-poc-note.md
```

---

## 1. 要件ベースラインの全体像

### 1.1 合意したい 5 ステップ

```mermaid
flowchart LR
    S1["①<br/>対応する<br/>認証フロー"] --> S2["②<br/>対応する<br/>IdP 接続要件"]
    S2 --> S3["③<br/>Identity Broker<br/>パターン採用"]
    S3 --> S4["④<br/>実装<br/>プラットフォーム"]
    S4 --> S5["⑤<br/>非機能要件<br/>(可用性 / DR / コスト)"]

    style S3 fill:#fff3e0,stroke:#e65100
    style S4 fill:#e3f2fd,stroke:#1565c0
```

各ステップが順番に積み上がる構造。① と ② を確定すると、③ は構造的に決まる。④ は ①〜③ の要件次第。

### 1.2 機能要件（FR）章一覧

| 章 | ファイル | 内容 | 一次ソース（詳細） |
|---|---|---|---|
| §FR-1 | [fr/01-auth.md](fr/01-auth.md) | 認証（認証フロー / パスワード） | [FR-AUTH §1](../functional-requirements.md) |
| §FR-2 | [fr/02-federation.md](fr/02-federation.md) | フェデレーション（IdP 接続 / ユーザー処理 / マルチテナント運用） | [FR-FED §2](../functional-requirements.md) |
| §FR-3 | [fr/03-mfa.md](fr/03-mfa.md) | MFA（要素 / 適用ポリシー） | [FR-MFA §3](../functional-requirements.md) |
| §FR-4 | [fr/04-sso.md](fr/04-sso.md) | SSO（同一 IdP / クロス IdP） | [FR-SSO §4.1](../functional-requirements.md) |
| §FR-5 | [fr/05-logout-session.md](fr/05-logout-session.md) | ログアウト・セッション管理（4 レイヤー / ライフサイクル / Revocation） | [FR-SSO §4.2-4.3](../functional-requirements.md) |
| §FR-6 | [fr/06-authz.md](fr/06-authz.md) | 認可（JWT クレーム / 4 パターン） | [FR-AUTHZ §5](../functional-requirements.md) |
| §FR-7 | [fr/07-user.md](fr/07-user.md) | ユーザー管理（CRUD / 属性ロール / セルフサービス / プロビジョニング） | [FR-USER §6](../functional-requirements.md) |
| §FR-8 | [fr/08-admin.md](fr/08-admin.md) | 管理機能（設定 / 監査 / 委譲・カスタマイズ） | [FR-ADMIN §7](../functional-requirements.md) |
| §FR-9 | [fr/09-integration.md](fr/09-integration.md) | 外部統合（プロトコル / ログ / API） | [FR-INT §8](../functional-requirements.md) |

### 1.3 非機能要件（NFR）章一覧 — IPA 非機能要求グレード対応

| 章 | ファイル | 内容 | IPA 大項目 |
|---|---|---|---|
| - | [nfr/00-index.md](nfr/00-index.md) | NFR 全体 + IPA マッピング | - |
| §NFR-1 | [nfr/01-availability.md](nfr/01-availability.md) | 可用性（SLA / RTO / RPO） | **A. 可用性** |
| §NFR-2 | [nfr/02-performance.md](nfr/02-performance.md) | 性能（応答時間 / スループット） | **B. 性能・拡張性** |
| §NFR-3 | [nfr/03-scalability.md](nfr/03-scalability.md) | 拡張性（MAU / 同時接続） | **B. 性能・拡張性** |
| §NFR-4 | [nfr/04-security.md](nfr/04-security.md) | セキュリティ（脅威対策 / 暗号化 / ゼロトラスト） | **E. セキュリティ** |
| §NFR-5 | [nfr/05-dr.md](nfr/05-dr.md) | DR（リージョン障害対応） | **A. 可用性（災害対策）** |
| §NFR-6 | [nfr/06-operations.md](nfr/06-operations.md) | 運用（監視 / デプロイ / サポート） | **C. 運用・保守性** |
| §NFR-7 | [nfr/07-compliance.md](nfr/07-compliance.md) | コンプライアンス（規制 / 認定） | **E + C**（独立章） |
| §NFR-8 | [nfr/08-cost.md](nfr/08-cost.md) | コスト（3 年 TCO） | （IPA 範囲外、独立章） |
| §NFR-9 | [nfr/09-migration.md](nfr/09-migration.md) | 移行性（既存基盤からの移行） | **D. 移行性** |

> 注: IPA グレードの **F. システム環境・エコロジー** はクラウド（AWS）前提で本基盤独自要件にはならないため省略。

### 1.4 横断章（Common）

| 章 | ファイル | 内容 |
|---|---|---|
| §C-1 | [common/01-architecture.md](common/01-architecture.md) | アーキテクチャ — Identity Broker パターン |
| §C-2 | [common/02-platform.md](common/02-platform.md) | 実装プラットフォーム（Cognito / Keycloak OSS / RHBK）選定軸 |
| §C-3 | [common/03-tbd-summary.md](common/03-tbd-summary.md) | TBD / 要確認 事項サマリー |
| §C-4 | [common/04-schedule.md](common/04-schedule.md) | 想定スケジュール |
| §C-5 | [common/05-poc-note.md](common/05-poc-note.md) | 弊社内の事前検証について（PoC 控えめ） |

---

## 2. 全体スケジュール

（埋める：本資料合意 → ヒアリング → 要件定義書 → 設計 → 実装 の各マイルストーン）

詳細: [common/04-schedule.md](common/04-schedule.md)

---

## 3. 関連ドキュメント

- [../requirements-document-structure.md](../requirements-document-structure.md): 要件定義フェーズ全体 SSOT
- [../functional-requirements.md](../functional-requirements.md): 機能要件詳細（FR-AUTH/FED/MFA/SSO/AUTHZ/USER/ADMIN/INT、各サブセクション付き）
- [../non-functional-requirements.md](../non-functional-requirements.md): 非機能要件詳細（NFR-AVL/PERF/SCL/SEC/DR/OPS/COMP/COST/MIG）
- [../../common/identity-broker-multi-idp.md](../../common/identity-broker-multi-idp.md): Broker パターン詳細
- [../platform-selection-decision.md](../platform-selection-decision.md): プラットフォーム選定判断書
- [../hearing-checklist.md](../hearing-checklist.md): ヒアリング項目一覧
