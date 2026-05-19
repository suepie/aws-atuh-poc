# 顧客送付用ヒアリングスクリプト

> 目的: [hearing-checklist.md](../hearing-checklist.md) の全項目を **顧客にそのまま送付できる敬体形式**で出力したもの。各質問の「目的・必要な理由」を併記。
> SSOT: [hearing-checklist.md](../hearing-checklist.md)（ID / 優先度 / 関連 FR/NFR / 章番号は本ファイル側を正とする）

---

## 構成

| ファイル | 内容 | 対応元 |
|---|---|---|
| [00-common.md](00-common.md) | Phase A 事業要件（14 項目） | A-1〜A-14 |
| [01-auth-flow.md](01-auth-flow.md) | 認証フロー / Grant Type（9 項目） | B-101〜B-109 |
| [02-idp-federation.md](02-idp-federation.md) | IdP 接続種別（8 項目） | B-201〜B-208 |
| [03-authz-jwt.md](03-authz-jwt.md) | 認可・JWT 要件(6 項目)| B-301〜B-306 |
| [04-user-management.md](04-user-management.md) | ユーザー管理・プロビジョニング（12 項目）| B-401〜B-410 |
| [05-mfa.md](05-mfa.md) | MFA 要素・適用ポリシー（9 項目） | B-501〜B-509 |
| [06-multitenancy.md](06-multitenancy.md) | マルチテナント運用（17 項目） | B-601〜B-612 |
| [07-logout-session.md](07-logout-session.md) | ログアウト・セッション管理（11 項目）| B-701〜B-706 |
| [08-sso-details.md](08-sso-details.md) | SSO 詳細（7 項目）| B-801〜B-803 |
| [09-availability.md](09-availability.md) | 可用性・性能・DR（7 項目） | C-101〜C-107 |
| [10-security-compliance.md](10-security-compliance.md) | セキュリティ・コンプライアンス（22 項目）| C-201〜C-217 |
| [11-operations.md](11-operations.md) | 運用体制・最終判断（12 項目） | C-301〜C-306 + D-1〜D-6 |

---

## 凡例

各項目は以下の形式で記載しています:

```markdown
---
### 【項目タイトル】 (ID, 優先度)

質問本文（敬体）。
追加で確認したい詳細。
**目的**: 本基盤側の意図と、この情報が必要な理由。
---
```

- **優先度**: 🔥 最優先（事業判断・プラットフォーム選定直結）/ 🟡 重要 / 🟢 通常
- **ID**: A-XX / B-XXX / C-XXX / D-X
- **目的**: なぜこの質問をするか、どの設計判断に必要か

---

## ヒアリング推奨順序

1. **Phase A**（事業要件）→ MAU 規模 / 業界規制 / 既存システムなど、後続の技術選定の前提
2. **Phase B**（技術要件）→ 認証フロー / 認可 / マルチテナント / SSO / ログアウトなど、機能要件
3. **Phase C**（運用・セキュリティ）→ SLA / コンプライアンス / 運用体制
4. **Phase D**（最終判断）→ プラットフォーム選定 / 移行戦略 / 予算 / リリーススケジュール

→ A → B → C → D の順で進めると、後段の判断に必要な情報が手戻りなく揃います。

---

## 補足

- 全 117 項目の網羅版です。プロジェクト初期に**🔥 最優先 34 項目を Stage 1 として先行確認**することで、プラットフォーム選定（Cognito Lite / Essentials / Plus or Keycloak OSS / RHBK）を早期に確定できます。
- 「Keycloak 必須化要因」「RHBK 必須化要因」の判定フローは [hearing-checklist.md 補足セクション](../hearing-checklist.md#補足-keycloak-必須要因と-rhbk-必須要因の判定フロー) を参照してください。
- 元データの設計詳細・対応能力マトリクス・業界実例は [proposal/](../proposal/) 配下の各章を参照してください。
