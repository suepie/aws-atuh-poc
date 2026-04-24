# ADR-012: VPC Lambda Authorizer + Internal ALB による JWKS プライベート化

- **ステータス**: Accepted
- **日付**: 2026-04-23
- **関連**: [ADR-002](002-lambda-authorizer.md)、[ADR-010](010-keycloak-private-subnet-vpc-endpoints.md)、[ADR-011](011-auth-frontend-network-design.md)、[keycloak-network-architecture.md §6.5](../common/keycloak-network-architecture.md)、[jwks-public-exposure.md](../common/jwks-public-exposure.md)

---

## Context

PoC 現構成では、Lambda Authorizer は **VPC 外（AWS マネージドネットワーク）で実行**されている。この構成は以下の特性がある:

1. **JWKS 取得がインターネット経由**
   - Keycloak JWKS → Public ALB（internet-facing）経由で取得
   - Cognito JWKS → AWS のパブリックエンドポイント経由で取得
2. **Lambda の出口 IP は予測不能**
   - そのため Public ALB の JWKS パスは `0.0.0.0/0` で全公開せざるを得ない
   - `jwks-public-exposure.md` §6 の検証で、Public ALB を IP 制限するとタイムアウトすることを実証済み
3. **ネットワーク攻撃面が大きい**
   - JWKS は公開鍵のみのため暗号学的リスクはないが、ALB 自体がインターネットに露出
   - DDoS、スキャン、0-day 脆弱性の標的になり得る

本番の理想形としては、**JWKS も含めて全てを VPC 内で完結**させ、インターネット露出を最小化したい。

その検証のため、PoC 上でも以下を確認する必要がある:

- VPC 内 Lambda が Internal ALB 経由で Keycloak JWKS を取得できること
- VPC Endpoint 経由で Cognito JWKS を取得できること
- 既存の VPC 外 Lambda と VPC 内 Lambda が**同じ認可ロジック**で動作すること（コード再利用性）
- Public ALB の SG を厳格化しても VPC 内 Lambda 経路は影響を受けないこと

---

## Decision

**既存の Lambda Authorizer と並列に、VPC 内配置版の Authorizer Lambda を新設する。**

### 要点

1. **既存 Authorizer（非 VPC）は変更しない**
   - `/v1/*` エンドポイントで引き続き使用
   - 認可ロジックは変更せず、追加の環境変数設定だけで VPC 版に流用可能な設計

2. **新規 VPC Authorizer を Private Subnet に配置**
   - 既存 Authorizer と**完全同一のコード**（`lambda/authorizer/index.py`）を使用
   - 動作差は環境変数のみで切り替え

3. **Internal ALB を新設**
   - `internal = true`、Private Subnet 配置
   - Public ALB と同じ ECS Target Group を共有（Keycloak 単一クラスタ）
   - VPC 内のみから到達可能

4. **VPC Endpoint for cognito-idp を新設**
   - `com.amazonaws.ap-northeast-1.cognito-idp` Interface Endpoint
   - Private DNS 有効化 → Cognito JWKS が VPC 内 IP に解決される
   - NAT Gateway 不要（コスト $32/月削減）

5. **Lambda コードに `JWKS_URL_OVERRIDES` 機構を追加**
   - JWT の `iss` が Public ALB URL の場合、環境変数で指定された Internal ALB の JWKS URL に置換して取得
   - OIDC Discovery の結果が VPC 外を指す問題を回避
   - 既存 Lambda は環境変数未設定のため従来通り（互換性維持）

6. **API Gateway に `/v2/*` エンドポイントを新設**
   - `/v1/*` = 既存 Authorizer（非 VPC・インターネット経由）
   - `/v2/*` = VPC Authorizer（VPC 内完結）
   - 同じ JWT で両方テスト可能 → 結果の比較検証

7. **カスタムドメイン / Route 53 PHZ は PoC では不使用**
   - 本番では Split-horizon DNS（`--hostname=https://auth.example.com` で統一）
   - PoC では ALB 自動生成 DNS + `JWKS_URL_OVERRIDES` で簡略化
   - [keycloak-network-architecture.md §6.5](../common/keycloak-network-architecture.md) に本番理想形として記載

---

## Consequences

### Positive

- **JWKS 取得経路が VPC 内で完結**（Public ALB を経由しない経路が確立）
- **既存 Lambda のコードを 1 行も変えずに VPC 版を追加可能**（環境変数のみで制御）
- Public ALB SG を将来 CloudFront プレフィックスリストのみに絞っても、`/v2/*` ルートは影響を受けないことが検証できる
- 本番移行時の技術的な妥当性が PoC で裏取りできる
- `ADR-011` の CloudFront + WAF 構成と組み合わせると、**Admin ALB を internet-facing のまま + VPC Lambda で完全プライベート認可**という 2 層防御が完成する

### Negative

- **月額 ~$25 の追加コスト**（Internal ALB $17 + VPC Endpoint $7 + 多少のトラフィック料）
- リソース数が増える（Internal ALB、TG、Listener、VPC Endpoint、VPC Lambda、新 SG）
- 2 つの Authorizer の挙動を一致させ続ける運用負担（環境変数のみの差分のため小さい）

### Neutral

- `/v1/*` と `/v2/*` の両方が同時に稼働（PoC 期間中は並列、本番では `/v2/*` のみ残す想定）
- PoC では Route 53 PHZ を使わないため、完全な Split-horizon DNS 動作は本番で追加検証が必要

---

## Alternatives Considered

### 案 A: NAT Gateway を使って既存 Authorizer を VPC 内に移行
- **棄却理由**: NAT Gateway $32/月が恒常的に発生。Internal ALB + VPC Endpoint 方式より高コスト。またインターネット経由を残すため「完全プライベート」の検証にならない

### 案 B: 既存 Authorizer を VPC 化して置き換え（並列配置しない）
- **棄却理由**: 検証時に既存動作との比較ができない。既存環境への影響リスクがある。切り戻しが困難

### 案 C: Keycloak の `hostname-backchannel-dynamic=true` で URL 分離
- **棄却理由**: Keycloak 側の設定が複雑化。PoC の簡略化と本番の理想形（Split-horizon DNS）の両方から外れる。ADR-011 の方針とも整合しない

### 案 D: Public ALB の DNS を VPC 内部で Private IP に解決させる
- **棄却理由**: ALB 自動生成 DNS を差し替えるのは公式にはサポートされない。カスタムドメイン + Route 53 PHZ が前提となり、PoC の簡略化を放棄することになる

---

## Implementation

実装ファイル一覧:

| ファイル | 内容 |
|---------|------|
| `infra/keycloak/internal-alb.tf`（新規） | Internal ALB + TG + Listener + SG |
| `infra/keycloak/vpc-endpoint-cognito.tf`（新規） | cognito-idp Interface Endpoint |
| `infra/keycloak/vpc-lambda-authorizer.tf`（新規） | VPC Lambda + IAM + SG + Log Group |
| `infra/keycloak/ecs.tf`（変更） | ECS Service に Internal ALB の TG を追加 |
| `infra/keycloak/outputs.tf`（変更） | VPC Lambda function ARN / name を出力 |
| `infra/api-vpc-test.tf`（新規） | `/v2/*` エンドポイント、VPC Authorizer 参照 |
| `lambda/authorizer/index.py`（変更、最小） | `JWKS_URL_OVERRIDES` ロジック追加（既存動作に影響なし） |

検証シナリオ（本 PoC 内で実施）:

1. bob-kc（Keycloak JWT）で `/v1/expenses`（非 VPC Authorizer）→ 200 OK
2. bob-kc で `/v2/expenses`（VPC Authorizer）→ 200 OK
3. CloudWatch Logs で両 Authorizer の JWKS 取得ログを比較（URL が Public ALB vs Internal ALB）
4. Public ALB SG を `0.0.0.0/0` から特定 IP のみに絞って再実行
   - `/v1/*` → 401（期待通り失敗）
   - `/v2/*` → 200（VPC 内経路のため成功）
5. Cognito ユーザー（alice）でも同様に `/v2/*` が動作することを確認（VPC Endpoint 経由）

クリーンアップ: `terraform destroy -target` で追加リソースのみ破棄可能。

---

## References

- [keycloak-network-architecture.md §6.5 本番理想形：完全プライベート構成](../common/keycloak-network-architecture.md)
- [jwks-public-exposure.md §6 検証結果](../common/jwks-public-exposure.md)
- [ADR-002 Lambda Authorizer](002-lambda-authorizer.md)
- [ADR-010 Keycloak Private Subnet 移行](010-keycloak-private-subnet-vpc-endpoints.md)
- [ADR-011 認証基盤前段ネットワーク設計](011-auth-frontend-network-design.md)
