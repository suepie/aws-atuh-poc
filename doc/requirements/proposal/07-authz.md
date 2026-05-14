# §7 認可

> 上位 SSOT: [00-index.md](00-index.md)
> 詳細: [../functional-requirements.md §5 FR-AUTHZ](../functional-requirements.md)、[../../common/authz-architecture-design.md](../../common/authz-architecture-design.md)
> カバー範囲: FR-AUTHZ §5.1 基本 / §5.2 細粒度
> ステータス: 📋 骨格のみ

---

## 7.1 クレームベース基本認可（→ FR-AUTHZ §5.1）

### ベースライン（仮）

JWT クレーム（`tenant_id`, `roles`）で API Gateway + Lambda Authorizer によるロール認可 + テナント分離。

### TBD / 要確認（仮）

ロール体系、テナント分離の粒度、API 認可方式

---

## 7.2 細粒度認可（→ FR-AUTHZ §5.2）

### ベースライン（仮）

UMA 2.0 / ABAC は Could。要件次第で Keycloak Authorization Services を採用。

### TBD / 要確認（仮）

リソースレベル認可・動的属性認可の必要性
