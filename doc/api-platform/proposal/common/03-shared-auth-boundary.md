# §C-API-3 共有認証基盤との接続点

> 親 SSOT: [../00-index.md](../00-index.md) §C-API-3
> ヒアリング: [../../hearing-script/02-authn-authz.md](../../hearing-script/02-authn-authz.md)
> 関連: [../../../requirements/](../../../requirements/00-index.md) — 共有認証基盤の要件定義

---

## §C-3.0 前提と背景

### §C-3.0.1 用語整理

| 用語 | 定義 |
|---|---|
| **共有認証基盤** | OIDC/OAuth 認可サーバを提供する集中アカウント（doc/requirements/ の主題） |
| **JWKS** | JSON Web Key Set。JWT の検証鍵公開 endpoint |
| **Discovery エンドポイント** | `/.well-known/openid-configuration` |
| **Issuer** | JWT の `iss` クレーム、発行元 URL |

### §C-3.0.2 なぜここ（§C-3）で決めるか

API プラットフォーム標準は **共有認証基盤の利用側**として位置づけられる。両者の境界を本章で明示することで：

- どちらのドメインで何を要件定義するか曖昧にならない
- 接続インターフェースの依存契約を明確化

```mermaid
flowchart LR
    AuthDoc[doc/requirements/<br/>(共有認証基盤)] -->|JWT 発行<br/>JWKS 公開| Boundary[本章<br/>境界仕様]
    Boundary -->|JWT 検証<br/>JWKS 取得| APIDoc[doc/api-platform/<br/>(本標準)]
```

### §C-3.0.3 §C-3.0.A 本標準のスタンス

| 基本方針 | 本章での具体化 |
|---|---|
| 絶対安全 | JWKS は HTTPS 必須、キャッシュ TTL を明示、ローテーション対応 |
| どんなアプリでも | OIDC 標準準拠で実装手段を縛らない |
| 効率よく | API Gateway のマネージド JWT Authorizer を最大活用 |
| 運用負荷・コスト最小 | 自前 JWT 検証は最小限、共有基盤側の更新追従は自動 |

### §C-3.0.4 本章で扱うサブセクション

| § | サブセクション |
|---|---|
| §C-3.1 | 認証基盤側が提供する契約 |
| §C-3.2 | 本標準側が取る動作 |
| §C-3.3 | 障害分離・縮退運転 |

---

## §C-3.1 認証基盤側が提供する契約

**このサブセクションで定めること**：共有認証基盤が公開・約束するインターフェース。
**主な判断軸**：OIDC 標準、可用性、変更通知。
**§C-3 全体との関係**：§C-3.2 の前提。

### §C-3.1.1 ベースライン

#### A. OIDC / OAuth 基本契約

- **OIDC Discovery エンドポイント** が公開されている
  - URL: `https://<auth-issuer>/.well-known/openid-configuration`
  - **PoC 段階で JWKS をプライベート化する検討中**（[../../../requirements/](../../../requirements/00-index.md) 参照）
- **JWKS エンドポイント** が Discovery で示される URL から取得可能
- **発行する JWT のクレーム**：
  - 必須: `iss`, `aud`, `exp`, `iat`, `sub`
  - 推奨: `tenant_id`, `roles`, `email`（マスク済）
- **鍵ローテーション**：定期 / 緊急時、新旧両方を JWKS に並べる期間あり

#### B. ユーザー認証 UI 提供（本標準のデフォルト「アプリ UI を持たない」前提）

本標準のデフォルトは **「アプリ UI を持たない」**（[§FR-API-2 §2.B](../fr/02-authn-authz.md)）。これに対応するため、認証基盤側に以下の UI 提供を期待する：

- **Hosted UI（Cognito Hosted UI / Keycloak login page 等）**
  - サインイン UI（パスワード / IdP 選択 / MFA）
  - サインアップ UI（B2C / Trial / SMB 顧客向け）
  - パスワードリセット UI
- **HRD（Home Realm Discovery）ページ**
  - メアドドメインから顧客 IdP 自動判定
  - 採用パターン C 採用時、認証基盤側で提供される想定（要認証側確定）
- **アプリからのリダイレクト先 URL**（OAuth Authorization Code Flow の起点）

#### C. Partner M2M Client 管理機能（**条件付き — Partner B2B M2M がスコープの場合のみ**）

**前提**：[§FR-API-2 §2.2.0](../fr/02-authn-authz.md) で Partner B2B M2M が要件化された場合のみ本項を適用する（API-A-112 / A-113 で確認）。

**認証側の現状調査結果（2026-06-03 時点）**：
- 認証側で OAuth Client Credentials Grant（M2M）のプロトコル認識は **あり**（§FR-1.1 C / FR-AUTH-004 Must / §FR-6.3.2）
- しかし「**Partner（外部企業からの B2B M2M 呼び出し）**」という独立カテゴリは **不在**
- 現状の Client / App Client 概念は「**テナント内ユーザー向けアプリ**」用に設計されており、Partner B2B M2M との断絶あり
- Credential ローテーション・Revocation・Self-service オンボーディング・Per-Partner-App × Per-Env 識別単位は **全て未要件化**

**本標準から認証側への申し送り**（要件化された場合のみ、`escalation-to-auth.md` で詳細管理）：

1. **Partner を独立カテゴリ「P-7」として認証側に追加**
   - 既存 P-1（Platform Admin）〜 P-6（B2C Consumer）の次のスロットとして提案
   - User Type ではなく **Service Account / Confidential Client** カテゴリ
2. **Partner M2M App Client 台帳管理**（Per-Partner-App × Per-Environment）
   - 認証側 §FR-2.3 マルチテナント運用に「**Partner 軸**」を追加要請
3. **Client Credentials（client_id / client_secret）発行 + ローテーション API**
   - 認証側 §FR-8.1 基盤設定管理（FR-ADMIN-004 拡張）
4. **OAuth scope 管理**（Partner ごと細粒度）
   - 認証側 §FR-6 認可拡張
5. **Token endpoint** + **audience 制御** + **Revocation API**
   - 認証側 §FR-8.1 + §NFR-4 セキュリティ

→ 認証側との具体的調整は [escalation-to-auth.md](../../escalation-to-auth.md) で管理。

### §C-3.1.2 認証基盤側 SLA（共有認証基盤要件定義側で確定）

| 項目 | 想定値（暫定）|
|---|---|
| Discovery / JWKS 可用性 | 99.99% |
| JWT 発行レイテンシ p99 | < 500ms |
| Hosted UI 可用性 | 99.95% |
| 鍵ローテーション通知期間 | 30 日 |
| Partner App Client 発行リードタイム | 1 営業日以内 |

### §C-3.1.3 TBD / 要確認

#### OIDC / OAuth 基本

- Q: JWKS の **プライベート化方針**最終判断（PoC 結果次第）→ 共有認証基盤側 SSOT
- Q: トークン形式（JWT / opaque + introspection）→ 共有認証基盤側で確定
- Q: クレームスキーマの **正式名**確定 → `API-B-203`（§FR-API-2 と同じ）

#### Hosted UI（B 追加項目、認証側に申し送り）

- Q: **Hosted UI 提供有無**（Cognito Hosted UI / Keycloak login page）→ 認証側で確定
- Q: **サインアップ UI 提供有無**（B2C / Trial 向け）→ 認証側で確定
- Q: **HRD ページ提供有無 + 所在**（認証基盤 / アプリ）→ 認証側 + `API-D-1402-α`
- Q: パスワードリセット UI 提供有無 → 認証側で確定

#### Partner M2M Client 管理（C 追加項目、認証側に申し送り）

- Q: **Partner M2M App Client 管理機能** の認証基盤側提供範囲（必須 / 任意）→ 認証側で確定
- Q: Partner App Client 発行・ローテーション・revocation API の仕様 → 認証側で確定
- Q: Partner App Client の **識別単位**（Per-Partner-App × Per-Environment、業界標準）の認証基盤側での実装可否 → `API-B-214`
- Q: Partner OAuth scope 管理の細粒度 → `API-B-215`

---

## §C-3.2 本標準側が取る動作

**このサブセクションで定めること**：各アプリ側が JWT を受け取って検証する標準動作。
**主な判断軸**：マネージド優先、`aud`/`iss`/`exp` の必須検証。
**§C-3 全体との関係**：§C-3.1 の契約に対応する実装規約。

### §C-3.2.1 ベースライン

- **検証手段**：
  - HTTP API: マネージド JWT Authorizer
  - REST API: Cognito User Pool Authorizer（基盤が Cognito の場合）または Lambda Authorizer
  - ALB: Authenticate-OIDC（Web UI 用）
  - Lambda Authorizer 採用は **コスト・レイテンシ要件を満たす場合に限る**
- **必須検証**：`iss`, `aud`, `exp`
- **オプショナル検証**：`nbf`, `iat`, `azp`, `scope`
- **キャッシュ**：JWKS は 5-15 分キャッシュ、認証結果は `exp` まで（カスタム Authorizer は 5 分上限）

### §C-3.2.2 TBD / 要確認

- Q: **必須クレーム検証リスト**確定 → `API-B-202`（§FR-API-2 と同じ）
- Q: Lambda Authorizer の **キャッシュ TTL** → `API-B-242`（§FR-API-2 と同じ）

---

## §C-3.3 障害分離・縮退運転

**このサブセクションで定めること**：認証基盤側の障害が API プラットフォーム全体に波及しないための設計。
**主な判断軸**：JWKS の局所キャッシュ、依存性のサーキットブレーカー。
**§C-3 全体との関係**：§NFR-API-1 可用性との接点。

### §C-3.3.1 ベースライン

- **JWKS キャッシュ**：認証基盤側障害でもキャッシュ期間中は検証継続
- **API Gateway のマネージド Authorizer は自動キャッシュ**（一般 5-15 分）
- **障害時の挙動**：
  - キャッシュ有効期間中：継続提供
  - キャッシュ失効後：401（または 503）を返す、復旧後自動再開
- **マルチリージョン**：認証基盤側の DR と整合（§NFR-API-5 と相互参照）

### §C-3.3.2 TBD / 要確認

- Q: JWKS キャッシュの **TTL 標準値**（マネージドの既定値で十分か）→ `API-C-2001`
- Q: 認証基盤側障害時の **API 縮退挙動**（401 か 503 か）→ `API-C-2002`

---

## §C-3.x 関連ドキュメント

- [../../../requirements/](../../../requirements/00-index.md) — 共有認証基盤の要件定義（境界の対面）
- [§FR-API-2 認証認可](../fr/02-authn-authz.md) — 認証方式の詳細
- [§NFR-API-1 可用性](../nfr/01-availability.md) — 依存先障害耐性
