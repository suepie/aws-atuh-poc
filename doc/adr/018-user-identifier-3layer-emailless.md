# ADR-018: ユーザー識別子 3 階層戦略（メール非保有 + 顧客独自 ID 対応）

- **ステータス**: Proposed（要件定義フェーズで Accepted に昇格予定）
- **日付**: 2026-06-12
- **関連**:
  - [§FR-1.2.0.D ユーザー識別子戦略](../requirements/proposal/fr/01-auth.md#fr-120d-ユーザー識別子戦略--メール非保有顧客独自-id-への対応)
  - [§FR-2.2.1.A 同一テナント内ユーザー重複の扱い](../requirements/proposal/fr/02-federation.md#fr-2.2.1.a-同一テナント内ユーザー重複の扱い)
  - [ADR-019 既存システム移行戦略](019-existing-system-migration.md)
  - 関連 Claude 内部メモリ: `project_identifier_strategy_emailless.md`
  - [ADR-020 HRD ヒントキー戦略](020-hrd-hint-keys-mixed-login.md)

---

## Context

業界の認証基盤デザインの多くは **email を主識別子（unique key / matching key / 復旧手段）** に置く設計を前提としている（OIDC standard claim `email` / Cognito の Sign-in Alias / Auth0 の Database Connection / 多くの IdP の NameID Format = emailAddress）。

しかし B2B 顧客の現実:

- **フィールドワーカー / 工場 / 病院 / 小売 / 教育現場では、メールアドレスを付与されていないユーザーが普通に存在する**（業界調査：Authgear / OLOID 2026）
- 顧客が**独自 ID 体系**（社員番号、学籍番号、店舗番号、技能者 ID 等）を既に持っており、新基盤でもこれを正準識別子として使いたいという要望がある
- 顧客の既存システムが「**システムごとにユーザーを別 ID で管理**」しているレガシー構成のため、新基盤に集約する段で「**どの ID を正準とするか**」を決める必要がある

「email 前提」を維持すると、JIT 突合・パスワードリセット・アカウント復旧・通知のすべてが破綻する。

---

## Decision

業界標準の **3 階層識別子モデル**を採用し、各層を明確に分離して管理する:

| Layer | 値の例 | 採番者 | 可変性 | 用途 |
|---|---|---|---|---|
| **A** `sub` | UUID `a1b2c3d4-...` | 本基盤 | **不変** | 内部参照、JWT `sub` クレーム、全 DB FK、監査ログ |
| **B** `external_id` / `preferred_username` | `ACME-EMP-0042` | 顧客 | 可（運用上）| 顧客向け表示、ヒューマンリーダブル ID、検索 |
| **C** `identities[].userId` | IdP の `sub` | 顧客 IdP | **不変**（IdP 側で）| フェデ突合、IdP リンク |

JIT 突合キーは「`tenant_id` + persistent NameID」が**第一推奨**で、**email は補助属性**として扱う。

---

## 3 階層モデルの図解

```mermaid
flowchart LR
    subgraph C["Layer C: IdP 側識別子"]
        CSub["IdP の sub<br/>例: ENTRA-abc123<br/>不変・IdP が採番"]
    end
    subgraph B["Layer B: 顧客可視 ID"]
        Ext["external_id / preferred_username<br/>例: ACME-EMP-0042<br/>顧客が決定・運用上可変"]
    end
    subgraph A["Layer A: 基盤生成内部 ID"]
        Sub["sub (UUID)<br/>例: a1b2c3d4-...<br/>不変・基盤が採番<br/>JWT sub クレーム / 全 DB FK"]
    end

    C -.identities[].userId.-> A
    B -.preferred_username 属性.-> A

    style A fill:#fff8e1
    style B fill:#e8f5e9
    style C fill:#e3f2fd
```

### Failure Mode（混同するとどうなるか）

| 誤設計 | 起きる事故 |
|---|---|
| Layer B を主キー（FK）として DB に持つ | 顧客が「社員番号体系変更」「人事システム刷新」したときに全 FK 壊滅 |
| Layer A しか保持しない（B を持たない）| 顧客側で「うちの社員 ACME-001 は基盤で誰?」が解決不能、SCIM/API 照会不可 |
| Layer A と C を混同（IdP sub を基盤 sub にしてしまう）| 顧客が IdP 切替（Okta → Entra）時に同一人物が別 sub になり、ロール・履歴ロスト |
| email を Layer A の代替に使う | email 改名・退職メール再利用で同一人物判定が壊れる |

---

## JIT 突合キー設計（email 非依存）

### 業界アンチパターン

| アンチパターン | 出典・理由 |
|---|---|
| ❌ **email を unique key として JIT 突合** | Salesforce / Okta / ThousandEyes 公式：「email should never be used as the unique key」|
| ❌ NameID Format = `emailAddress` を強制 | 顧客 IdP に email がない場合に破綻 |
| ❌ Layer B（顧客独自 ID）を直接 JWT `sub` に流す | 顧客が ID 改番すると全アプリの FK が壊れる |

### 業界推奨

| 推奨パターン | 出典 |
|---|---|
| ✅ canonical ID 優先順位: `oid`（Microsoft）> `sub`（OIDC）> `nameidentifier`（SAML 古典）| ThousandEyes JIT Provisioning Doc |
| ✅ NameID Format: **`persistent`**（IdP 内不変、業界第一推奨）| SAML 2.0 仕様 + Atlassian / Bitbucket JIT ガイド |
| ✅ 複合キー: `tenant_id` + Layer B `external_id` | Slack / Notion / Linear の B2B SaaS 実装パターン |

### 顧客状況別の推奨突合キー

| 顧客状況 | 推奨突合キー | 備考 |
|---|---|---|
| 顧客 IdP が email を発行 | `tenant_id + persistent NameID`（第一）、email は補助 | email 変更耐性確保 |
| 顧客 IdP が email を発行しない（or 一部のみ）| `tenant_id + persistent NameID + external_id` | external_id を IdP 属性として送信してもらう |
| 顧客が「社員番号で突合」を要望 | `tenant_id + employeeNumber` 属性（顧客独自 mapping）| 属性マッピング設定を顧客テナントごとに分離 |

---

## 顧客独自 ID の受け入れ方針

### 命名空間設計

```
顧客可視                     基盤内部表現
ACME-EMP-0042   →   preferred_username: "ACME-EMP-0042"
                    custom:external_id: "ACME-EMP-0042"
                    custom:tenant_id:   "acme"
                    sub:                "a1b2c3d4-..." (UUID, 不変)
```

### 不変性ポリシー

| 識別子 | 不変性 | 改名できる主体 | 履歴保持 |
|---|---|---|---|
| Layer A `sub` | **絶対不変** | なし | — |
| Layer B `external_id` | 運用上可変 | 顧客側管理者 / 基盤側（顧客申請）| 過去値を `external_id_history` に保持 |
| Layer B `preferred_username` | 運用上可変 | 同上 | 同上 |
| Layer C `identities[].userId` | IdP 内不変 | IdP 側でのみ | IdP 切替時は新規 link 追加 |

---

## プラットフォーム制約（Cognito vs Keycloak）

email 非保有 + 顧客独自 ID 対応における**プラットフォーム機能差**:

| 制約 | Cognito | Keycloak |
|---|---|---|
| **email を必須にしない** | ✅ 可（**Pool 作成時のみ**、後から変更不可）| ✅ 可（Realm 設定で随時変更可）|
| **username の不変性** | **❌ 不変、作成後変更不可** | ✅ 変更可（管理者 / セルフ）|
| **`preferred_username`** | alias として可、ただし「必須属性と alias は同時設定不可」「alias 設定時は登録時に値を入力不可」| username と独立、任意設定可 |
| **必須属性の追加・変更**（Pool/Realm 作成後）| **❌ 不可** | ✅ 可 |
| **顧客独自 ID 受け入れ** | カスタム属性 `custom:external_id` で可 | カスタム属性 + Identity Provider Mapper で柔軟 |
| **Email 不在時のアカウント復旧** | SES 連携前提強い、Admin Reset 可、SMS 連携可 | Admin Reset + **Recovery Codes（2025-10 公式機能）** + SMS |
| **NameID Format 受け入れ柔軟性** | mapping は可だが editing UI 限定 | Identity Provider Mapper で任意マッピング |

### 結論

- **email 非保有ユーザーを多く持つ顧客は Keycloak で対応する方が運用摩擦が小さい**
- Cognito での実装は技術的に可能だが、`username の不変性` × `preferred_username alias の制約` × `必須属性変更不可` のコンビにより、Pool 設計を間違えると**運用後の修正手段が極めて限定的**になる

---

## アカウント復旧・通知の代替手段（email 非保有時）

### NIST SP 800-63B-4（2025-08 公開）の制約

| 制約 | 内容 |
|---|---|
| **SMS OTP** | **Restricted authenticator** に格下げ（仕様上禁止ではないが、リスク承認が必要）|
| **email を out-of-band 2FA に使用** | **不可** |
| 推奨復旧モデル | **物理 multi-factor デバイス 2 つ**（プライマリ + バックアップ）|

### email-less 復旧手段の評価

| 手段 | NIST 800-63B-4 適合 | 適用シナリオ | 備考 |
|---|---|---|---|
| **Recovery Codes**（紙配布 + ユーザー保管）| ✅ 推奨 | 全員（汎用）| Keycloak 26.x で公式機能、Cognito は Lambda 実装 |
| **Admin Reset**（管理者主導の新 PW 再発行）| ✅ 推奨 | 工場・病院など対面で配布可能 | 内部統制プロセスに乗せる必要あり |
| **WebAuthn / Passkey 多重登録** | ✅ 強推奨 | スマホ / Yubikey 等を 2 つ登録 | NIST 800-63B Rev 4 が明示的に推奨 |
| **Push Notification**（モバイルアプリ）| ✅ 推奨 | スマホ持参の現場ワーカー | ベンダーロックインに注意 |
| **SMS OTP** | ⚠ Restricted（リスク承認必要）| 復旧手段に限り条件付きで容認可 | SIM スワップ攻撃リスク |
| **セキュリティ質問** | ❌ NIST が明確に非推奨（2017〜）| 採用しない | — |

---

## Consequences

### Positive

- 業界標準パターンに準拠（Microsoft Entra / Auth0 / Okta / Salesforce すべて同じ構造）
- email 改名・退職メール再利用で同一人物判定が壊れない
- 顧客が ID 体系変更しても基盤 FK は壊れない
- Keycloak 確定方向（[[project-platform-direction-keycloak]]）を補強

### Negative

- カスタム属性が 3 つ必須（`external_id` / `tenant_id` / `external_id_history`）
- 顧客 IdP 側に「persistent NameID 送出」「employeeNumber 属性送信」等の設定依頼が必要
- 認証復旧フローを email/SMS から Recovery Codes / Push に切替える運用設計が必要

---

## 参考資料

- **AWS Cognito 公式ドキュメント**:
  - [Working with user attributes](https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-settings-attributes.html)
  - [Mapping IdP attributes to profiles and tokens](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-specifying-attribute-mapping.html)
- **Keycloak 公式ドキュメント**:
  - [Recovery Authentication Codes](https://www.keycloak.org/2025/10/recovery-codes) — 2025-10 リリース公式機能
  - [Managing users](https://www.keycloak.org/docs/latest/server_admin/index.html)
- **NIST**:
  - [SP 800-63B-4 Digital Identity Guidelines](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-63B-4.pdf)
- **JIT 突合 / SAML NameID**:
  - [Salesforce Federation ID for SSO](https://developer.salesforce.com/docs/atlas.en-us.packagingGuide.meta/packagingGuide/environment_hub_sso_mapping_federation_formula.htm)
  - [ThousandEyes SAML JIT Provisioning](https://docs.thousandeyes.com/product-documentation/user-management/user-registration/saml-jit-provisioning)
  - [Microsoft Entra: Customize SAML token claims](https://learn.microsoft.com/en-us/entra/identity-platform/saml-claims-customization)
- **フィールドワーカー認証パターン**:
  - [Authgear: Frontline workforce authentication](https://www.authgear.com/post/auth0-alternatives-for-frontline-workforce-authentication)
  - [OLOID: Workforce IAM Complete Guide](https://www.oloid.com/blog/workforce-identity-and-access-management)
