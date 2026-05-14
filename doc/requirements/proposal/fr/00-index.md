# 機能要件（FR）章一覧

> 上位 SSOT: [../00-index.md](../00-index.md)
> 詳細マトリクス: [../../functional-requirements.md](../../functional-requirements.md)（FR-AUTH/FED/MFA/SSO/AUTHZ/USER/ADMIN/INT）

---

## 章一覧

| 章 | ファイル | 内容 | 一次ソース（FR カタログ） |
|---|---|---|---|
| §FR-1 | [01-auth.md](01-auth.md) | 認証（認証フロー / パスワード） | [FR-AUTH §1](../../functional-requirements.md) |
| §FR-2 | [02-federation.md](02-federation.md) | フェデレーション（IdP 接続 / ユーザー処理 / マルチテナント運用） | [FR-FED §2](../../functional-requirements.md) |
| §FR-3 | [03-mfa.md](03-mfa.md) | MFA（要素 / 適用ポリシー） | [FR-MFA §3](../../functional-requirements.md) |
| §FR-4 | [04-sso.md](04-sso.md) | SSO（同一 IdP / クロス IdP） | [FR-SSO §4.1](../../functional-requirements.md) |
| §FR-5 | [05-logout-session.md](05-logout-session.md) | ログアウト・セッション管理（4 レイヤー / ライフサイクル / Revocation） | [FR-SSO §4.2-4.3](../../functional-requirements.md) |
| §FR-6 | [06-authz.md](06-authz.md) | 認可（JWT クレーム / 4 パターン） | [FR-AUTHZ §5](../../functional-requirements.md) |
| §FR-7 | [07-user.md](07-user.md) | ユーザー管理（CRUD / 属性ロール / セルフサービス / プロビジョニング） | [FR-USER §6](../../functional-requirements.md) |
| §FR-8 | [08-admin.md](08-admin.md) | 管理機能（設定 / 監査 / 委譲・カスタマイズ） | [FR-ADMIN §7](../../functional-requirements.md) |
| §FR-9 | [09-integration.md](09-integration.md) | 外部統合（プロトコル / ログ / API） | [FR-INT §8](../../functional-requirements.md) |

---

## 章間の依存関係

```mermaid
flowchart LR
    FR1["§FR-1 認証<br/>(ローカル認証)"]
    FR2["§FR-2 フェデ<br/>(外部 IdP)"]
    FR3["§FR-3 MFA"]
    FR4["§FR-4 SSO"]
    FR5["§FR-5 ログアウト"]
    FR6["§FR-6 認可<br/>(JWT クレーム)"]
    FR7["§FR-7 ユーザー管理"]
    FR8["§FR-8 管理機能"]
    FR9["§FR-9 外部統合"]

    FR1 --> FR3
    FR2 --> FR3
    FR1 --> FR4
    FR2 --> FR4
    FR4 --> FR5
    FR1 --> FR6
    FR2 --> FR6
    FR7 --> FR1
    FR7 --> FR2
    FR8 --> FR7
    FR9 -.OIDC/SAML/SCIM.- FR1
    FR9 -.OIDC/SAML/SCIM.- FR2

    style FR1 fill:#e3f2fd,stroke:#1565c0
    style FR2 fill:#e3f2fd,stroke:#1565c0
    style FR6 fill:#fff3e0,stroke:#e65100
```

---

## 関連

- [../00-index.md](../00-index.md): proposal 全体 SSOT
- [../nfr/00-index.md](../nfr/00-index.md): 非機能要件章一覧
- [../common/01-architecture.md](../common/01-architecture.md): Identity Broker アーキテクチャ
- [../common/02-platform.md](../common/02-platform.md): プラットフォーム選定
