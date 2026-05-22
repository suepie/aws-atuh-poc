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

- **OIDC Discovery エンドポイント** が公開されている
  - URL: `https://<auth-issuer>/.well-known/openid-configuration`
  - **PoC 段階で JWKS をプライベート化する検討中**（[../../../requirements/](../../../requirements/00-index.md) 参照）
- **JWKS エンドポイント** が Discovery で示される URL から取得可能
- **発行する JWT のクレーム**：
  - 必須: `iss`, `aud`, `exp`, `iat`, `sub`
  - 推奨: `tenant_id`, `roles`, `email`（マスク済）
- **鍵ローテーション**：定期 / 緊急時、新旧両方を JWKS に並べる期間あり

### §C-3.1.2 認証基盤側 SLA（共有認証基盤要件定義側で確定）

| 項目 | 想定値（暫定）|
|---|---|
| Discovery / JWKS 可用性 | 99.99% |
| JWT 発行レイテンシ p99 | < 500ms |
| 鍵ローテーション通知期間 | 30 日 |

### §C-3.1.3 TBD / 要確認

- Q: JWKS の **プライベート化方針**最終判断（PoC 結果次第）→ 共有認証基盤側 SSOT
- Q: トークン形式（JWT / opaque + introspection）→ 共有認証基盤側で確定
- Q: クレームスキーマの **正式名**確定 → `API-B-203`（§FR-API-2 と同じ）

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
