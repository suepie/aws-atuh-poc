# クレームマッピング・認可 検証シナリオ

**作成日**: 2026-04-15
**目的**: IdP属性（Auth0 / Cognito / Keycloak）を JWT クレームに載せ、Lambda Authorizer と Backend Lambda で認可判定できることを確認する。

---

## 1. 想定アプリケーション

マルチテナントSaaSの **経費精算システム**。

- 複数の会社（テナント）がアプリを利用
- 各会社の社員が自分の申請を作成、上司が承認、管理者が削除
- 他社の情報は絶対に見えてはいけない

---

## 2. ユーザー調達方針

| 種別 | 調達方法 | 用途 |
|------|---------|------|
| 一般ユーザー | **Auth0（IdP連携）→ Cognito central** にJITプロビジョニング | 顧客企業の社員（Entra ID / Okta相当） |
| 例外ユーザー | **Local Cognito で直接作成** | パートナー企業、外部委託者など |

**前提**: 本番では Auth0 の部分が Entra ID / Okta に置き換わる。検証では Auth0 を代替として使用。

---

## 3. テナント・ロール設計

### テナントモデル
- 1ユーザー = 1テナント所属（シンプル）
- テナントID例: `acme-corp`, `globex-inc`, `partner-co`

### ロール（3種）
| ロール | 権限 |
|-------|------|
| `employee` | 自分の申請を参照・作成 |
| `manager` | 自テナント内の全申請を参照・承認 |
| `admin` | 自テナント内の全申請を参照・承認・削除 |

※ 全テナント横断の super-admin はPoCスコープ外

---

## 4. クレーム設計（JWT最終形）

Auth0経由ユーザーもローカルCognitoユーザーも、同じ形のJWTになるように揃える。

```json
{
  "sub": "...",
  "email": "alice@acme.com",
  "custom:tenant_id": "acme-corp",
  "cognito:groups": ["manager"],
  "iss": "https://cognito-idp.ap-northeast-1.amazonaws.com/<pool-id>",
  "token_use": "id",
  ...
}
```

### クレームのソース

| クレーム | Auth0ユーザー | ローカルCognitoユーザー |
|---------|--------------|----------------------|
| `custom:tenant_id` | Auth0 `app_metadata.tenant_id` → attribute_mapping → custom属性 | Cognitoカスタム属性を直接設定 |
| `cognito:groups` | Auth0 `app_metadata.role` → Pre Token Lambda でグループに変換 | Cognito Group に直接追加 |

---

## 5. 認可設計

### APIエンドポイント

| Method | Path | 認可ルール |
|--------|------|-----------|
| `GET` | `/v1/expenses` | 自分の申請一覧（`employee`以上） |
| `POST` | `/v1/expenses` | 申請作成（`employee`以上、`tenant_id`は JWT から自動付与） |
| `GET` | `/v1/expenses/{id}` | 自申請 or 同テナント内 `manager` 以上 |
| `POST` | `/v1/expenses/{id}/approve` | 同テナント内 `manager` 以上 |
| `DELETE` | `/v1/expenses/{id}` | 同テナント内 `admin` |
| `GET` | `/v1/tenants/{tenantId}/expenses` | `manager`以上 かつ `tenantId == JWT.tenant_id` |

### 認可チェックの3層

```
[1] Lambda Authorizer（API Gateway層）
    - JWT署名検証（JWKS）
    - Context伝播: userId, email, tenantId, roles, issuerType

[2] Backend Lambda（認可ロジック層）
    - ロール要件チェック（エンドポイント別の最低ロール）
    - テナントスコープチェック（パス tenantId == JWT.tenant_id）

[3] データアクセス層（本番）
    - 全クエリに tenant_id 条件付与
    - PoCではインメモリ or ダミーデータ
```

---

## 6. テストユーザー

| Pool | User | Tenant | Role | 備考 |
|------|------|--------|------|------|
| Central (Auth0経由) | alice@acme.com | acme-corp | employee | 一般社員 |
| Central (Auth0経由) | bob@acme.com | acme-corp | manager | 上司 |
| Central (Auth0経由) | carol@acme.com | acme-corp | admin | 管理者 |
| Central (Auth0経由) | dave@globex.com | globex-inc | manager | 別テナント |
| Local | eve@partner.com | partner-co | employee | パートナー（IdP未連携） |

---

## 7. 検証テストケース

| # | シナリオ | 実行ユーザー | エンドポイント | 期待結果 |
|---|---------|-----------|--------------|---------|
| 1 | 自テナント内・権限OK | alice (employee) | GET /v1/expenses | 200 |
| 2 | 自テナント内・権限不足 | alice (employee) | POST /v1/expenses/x/approve | 403 |
| 3 | 承認権限あり | bob (manager) | POST /v1/expenses/x/approve | 200 |
| 4 | 別テナントアクセス | bob (manager) | GET /v1/tenants/globex-inc/expenses | 403 |
| 5 | 削除権限 | carol (admin) | DELETE /v1/expenses/x | 200 |
| 6 | manager が削除 | bob (manager) | DELETE /v1/expenses/x | 403 |
| 7 | ローカルCognitoユーザー | eve (employee) | GET /v1/expenses | 200 (issuerType=local, tenantId=partner-co) |
| 8 | tenant_id欠落JWT | (カスタム属性なし) | GET /v1/expenses | 403 |
| 9 | Keycloak発行JWTでも同じAPIが動く | Keycloak user | GET /v1/expenses | 200 |

---

## 8. 実装順序

1. **Cognito** カスタム属性 `tenant_id` / グループの整備
2. **Auth0** ユーザーの `app_metadata` に tenant_id / role を設定
3. **Cognito Identity Provider** の attribute_mapping に tenant_id 追加
4. **Pre Token Generation Lambda** 作成
   - Auth0由来ユーザーの `app_metadata.role` → Cognito groups形式に変換
   - tenant_id が無い場合は Deny
5. **Lambda Authorizer** 拡張（Context に `tenantId`, `roles` 追加）
6. **Backend Lambda** 拡張
   - 認可ユーティリティ関数（`require_role`, `require_tenant`）
   - 新エンドポイント追加
7. **API Gateway** に新エンドポイント追加
8. **テストユーザー作成** + 動作確認
9. **Keycloak版**: 同じクレーム名でProtocol Mapper設定

---

## 9. 本番で置き換わる箇所

| PoC | 本番 |
|-----|------|
| Auth0 | Entra ID / Okta |
| app_metadata.tenant_id | Entra ID の拡張属性 / Okta のプロファイル属性 |
| インメモリのダミーデータ | DynamoDB / RDS（行レベルで tenant_id フィルタ） |
| 個別にカスタム属性設定 | IdP側のユーザープロビジョニング自動化（SCIM等） |
