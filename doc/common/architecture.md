# ⚠ このドキュメントは移管されました

**移管先**: [§C-7 実装アーキテクチャ — 全体構成図と構成要素詳細（本番想定）](../requirements/proposal/common/07-implementation-architecture.md)

**移管日**: 2026-06-24
**理由**: 要件定義の最終 SSOT として `proposal/common/` 配下に集約。アーキテクチャ全体構成（ADR-001〜053 統合、28 構成要素 + 6 シーケンス + 4 データフロー）は §C-7 として要件定義章構成に正式組込。

---

## 新しい参照先

| 用途 | 新パス |
|---|---|
| 実装アーキテクチャ SSOT（本ファイル後継）| [§C-7 実装アーキテクチャ](../requirements/proposal/common/07-implementation-architecture.md) |
| アーキテクチャ採用根拠 / Identity Broker 論証 | [§C-1 アーキテクチャ](../requirements/proposal/common/01-architecture.md) |
| プラットフォーム選定 | [§C-2 プラットフォーム](../requirements/proposal/common/02-platform.md) |
| ハイブリッド統合根拠 | [§C-6 ハイブリッド統合](../requirements/proposal/common/06-architecture-decision-hybrid.md) |
| PoC 実構成（履歴）| [architecture-poc-history.md](architecture-poc-history.md) |

---

## 章マッピング（旧 → 新）

| 旧章番号 | 新章番号 |
|---|---|
| §0 本資料の位置付け | §C-7.0 |
| §0.3 確定 ADR との対応 | §C-7.0.3 |
| §1 全体概要 | §C-7.1 |
| §1.2 主要アーキ判断 | §C-7.1.2 |
| §2 アーキテクチャ全体構成図 | §C-7.2 |
| §2.2 アーキテクチャ全体図 | §C-7.2.2 |
| §2.3 AWS アカウント境界 | §C-7.2.3 |
| §3.1 アクター | §C-7.3.1 |
| §3.2 AWS アカウント構成 | §C-7.3.2 |
| §3.3 Network 層 | §C-7.3.3 |
| §3.4 Broker Keycloak | §C-7.3.4 |
| §3.5 IdP Keycloak | §C-7.3.5 |
| §3.6 外部 IdP 接続 | §C-7.3.6 |
| §3.7 外部 SP 接続 | §C-7.3.7 |
| §3.8 UI レイヤー | §C-7.3.8 |
| §3.9 プロビジョニング・統合層 | §C-7.3.9 |
| §3.10 セキュリティ・検知層（ITDR + Adaptive Auth）| §C-7.3.10 |
| §3.11 AWS edge Sorry 制御 | §C-7.3.11 |
| §3.12 監査・コンプライアンス層 | §C-7.3.12 |
| §3.13 ユーザ管理画面 バックエンド | §C-7.3.13 |
| §3.14 移行層 | §C-7.3.14 |
| §3.15 特権アクセス管理 PAM | §C-7.3.15 |
| §3.16 Workload Identity | §C-7.3.16 |
| §3.17 Bot Detection / Credential Stuffing | §C-7.3.17 |
| §3.18 Accessibility 設計 | §C-7.3.18 |
| §3.19 Tabletop Exercise | §C-7.3.19 |
| §3.20 鍵管理アーキテクチャ | §C-7.3.20 |
| §3.21 Supply Chain Security | §C-7.3.21 |
| §3.22 PQC 対応 | §C-7.3.22 |
| §3.23 Data Portability + DSAR | §C-7.3.23 |
| §3.24 Vendor Risk Management | §C-7.3.24 |
| §3.25 モバイルアプリ認証 | §C-7.3.25 |
| §3.26 Multi-Region DR / Failover | §C-7.3.26 |
| §3.27 マルチテナント Isolation + Rate Limit | §C-7.3.27 |
| §3.28 Observability | §C-7.3.28 |
| §4 主要シーケンス図（6 枚）| §C-7.4 |
| §5 データフロー詳細（4 枚）| §C-7.5 |
| §6 関連 ADR マッピング | §C-7.6 |
| §7 drawio 転記時の注意 | §C-7.7 |
| §8 残作業と更新ポリシー | §C-7.8 |
| §9 関連ドキュメント | §C-7.9 |

---

## 後方互換性の注意

このファイルへのリンクは段階的に §C-7 に張り替えてください。リンクは当面（少なくとも 1 年間）リダイレクト目的で残しますが、新規参照は **必ず §C-7 を使用**してください。

このファイルへ Edit / Write を行わないでください。すべての更新は [§C-7](../requirements/proposal/common/07-implementation-architecture.md) で行います。
