# 顧客送付用ヒアリングスクリプト

> 目的: [hearing-checklist.md](../hearing-checklist.md) の全項目を **顧客にそのまま送付できる敬体形式**で出力したもの。各質問の「目的・必要な理由」を併記。
> SSOT: [hearing-checklist.md](../hearing-checklist.md)（ID / 優先度 / 関連 FR/NFR / 章番号は本ファイル側を正とする）
>
> **構造再編成**（2026-05-25）: hearing-checklist.md は **§0〜§5（subject-matter 軸）** に再編成済。hearing-script/ は会議組み立て用に **旧 Phase 軸（A/B/C/D）** のままファイル分割（両軸を併用）。各ファイル冒頭に **新 §X.Y との対応マップ**を追加済み。

---

## ファイル構成（旧 Phase 軸）

| ファイル | 内容 | 主な対応項目 |
|---|---|---|
| [00-common.md](00-common.md) | Phase A 事業要件 | A-1〜A-14 + A-5-2/3/4 + A-11 系 |
| [01-auth-flow.md](01-auth-flow.md) | **マスター表 C** + 補足 1〜5（認証フロー / Grant Type） | **B-100**（旧 B-101〜B-109 + B-202 + B-303 + B-304 + B-504 + B-704 + C-204-5 + C-207 統合）|
| [02-idp-federation.md](02-idp-federation.md) | **マスター表 A / B**（IdP 接続種別）| **B-200**（旧 A-13）、**B-200-B**（旧 A-6 / B-201〜B-207）、B-208、B-609 |
| [03-authz-jwt.md](03-authz-jwt.md) | 認可・JWT 要件 | B-301、B-302、B-305（旧 B-303/B-304 はマスター表 C に統合）|
| [04-user-management.md](04-user-management.md) | ユーザー管理・プロビジョニング | B-401〜B-410 |
| [05-mfa.md](05-mfa.md) | MFA 要素・適用ポリシー | B-501〜B-509（旧 B-504 はマスター表 C に統合）|
| [06-multitenancy.md](06-multitenancy.md) | マルチテナント運用 | B-601〜B-612 + B-605-3（退職反映 SLA）|
| [07-logout-session.md](07-logout-session.md) | ログアウト・セッション管理 | B-701〜B-706（旧 B-704 はマスター表 C に統合）|
| [08-sso-details.md](08-sso-details.md) | SSO 詳細 | B-801〜B-803 |
| [09-availability.md](09-availability.md) | 可用性・性能・DR | C-101〜C-107 |
| [10-security-compliance.md](10-security-compliance.md) | セキュリティ・コンプライアンス | C-201〜C-217（旧 C-204-5 / C-207 はマスター表 C に統合）|
| [11-operations.md](11-operations.md) | 運用体制・最終判断 | C-301〜C-306 + D-1〜D-6 |

---

## 新 §X.Y 構造との対応

各ファイルの冒頭に **「新 §X.Y 構造との対応」** ブロックを記載。subject-matter 軸で項目を探したい場合は [hearing-checklist.md §0〜§5](../hearing-checklist.md) を起点に使ってください。

| 新セクション | 主に参照するスクリプトファイル |
|---|---|
| **§1 前提合意** | 00-common.md (A-5-2/3/4, A-11, A-11-α) + 11-operations.md (D-6) |
| **§2 サービスとしての要件** | 00-common.md + 04-user-management.md + 05-mfa.md + 06-multitenancy.md + 07-logout-session.md + 08-sso-details.md + 10-security-compliance.md + 11-operations.md |
| **§3 既存接続元・アプリの現状把握** | **01-auth-flow.md（マスター表 C）+ 02-idp-federation.md（マスター表 A/B）** + 00-common.md + 04 + 06 + 07 + 10 |
| **§4 基盤としてサポートしたい技術仕様** | 03-authz-jwt.md + 05-mfa.md + 06-multitenancy.md + 07-logout-session.md + 08-sso-details.md + 10-security-compliance.md |
| **§5 非機能要件** | 09-availability.md + 10-security-compliance.md + 11-operations.md |

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

一部の重要質問（例: [B-401 SCIM 採否](04-user-management.md)）は **拡張テンプレ**（位置づけ / 回答で決まること / なぜ今聞くのか / 比較イメージ / 質問 / 関連）を採用しています。

- **優先度**: 🔥 最優先（事業判断・プラットフォーム選定直結）/ 🟡 重要 / 🟢 通常
- **ID**: A-XX / B-XXX / C-XXX / D-X
- **目的**: なぜこの質問をするか、どの設計判断に必要か

---

## ヒアリング推奨順序

1. **§1 前提合意 6 件すべて**: 後続全質問の範囲を規定する最上位判断（A-5-2/3/4、A-11/A-11-α、D-6）
2. **§3.1〜§3.3 の 3 大マスター表**（B-200 / B-200-B / B-100）: 「弊社 IdP × 顧客 IdP × アプリ」のマトリクス完結で Cognito vs Keycloak が事実上確定
3. **§2.1〜§2.2 の事業・規制要件**: コスト試算とコンプラ範囲確定の入力
4. その他の §2.3〜§2.8（サービス契約に関わる方針）
5. §4 技術仕様詳細
6. §5 NFR

→ 旧 Phase 軸でヒアリング会議を組み立てる場合は **A → B → C → D**（事業 → 技術 → 運用 → 意思決定）の順で進めると、後段の判断に必要な情報が手戻りなく揃います。

---

## 補足

- 全 124 項目の網羅版です（マスター表 C への統合により旧 17 項目を strikethrough、新 B-100 マスター表行を追加）
- 「Keycloak 必須化要因」「RHBK 必須化要因」の判定フローは [hearing-checklist.md 補足セクション](../hearing-checklist.md#補足-cognito-knockout-判定フロー) を参照してください
- 元データの設計詳細・対応能力マトリクス・業界実例は [proposal/](../proposal/) 配下の各章を参照してください
- マスター表 C 補足 1〜5（BFF / JWT 検証場所 / Knockout 条件 K1〜K8 技術根拠 / 業界トレンド / FAQ）は [01-auth-flow.md](01-auth-flow.md#マスター表-c-の補足) に集約
