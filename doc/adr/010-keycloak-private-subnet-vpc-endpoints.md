# ADR-010: Keycloak 環境を Private Subnet + VPC Endpoint 構成へ移行

- **ステータス**: Accepted
- **日付**: 2026-04-21
- **関連**: [ADR-008](008-keycloak-start-dev-for-poc.md)、[keycloak-network-architecture.md](../common/keycloak-network-architecture.md)

---

## Context

PoC 初期構成では、Keycloak の ECS タスク・RDS・ALB をデフォルト VPC の public サブネットに配置し、ECS タスクには `assign_public_ip = true` でパブリック IP を付与していた。理由は **ECR pull にインターネット経路が必要だったため**。

本構成には以下のセキュリティ課題があった:

1. **ECS タスクにパブリック IP** — SG Ingress は ALB SG に限定していたが、タスク自体が公開ネットワーク上に露出。セキュリティ監査で指摘されやすい
2. **ECS Egress 全開** — 万一タスクが侵害された場合、任意の外部通信（C2 等）が可能
3. **RDS SG に自分の IP を許可** — `Temporary: from my IP for DB maintenance` として残存。本番では絶対 NG
4. **デフォルト VPC を使用** — サブネット設計が本番想定と乖離

本番の理想形を PoC で検証することで、本番設計の再利用性を高めつつセキュリティ監査要件も満たす。

---

## Decision

Keycloak インフラを **カスタム VPC + Private Subnet + VPC Endpoint** 構成へ移行する。

実装詳細（VPC CIDR、サブネット分割、VPC Endpoint 仕様、SG Egress ルール、IP 制限マトリクス、コスト影響）は **[keycloak-network-architecture.md](../common/keycloak-network-architecture.md)** に一元化する。本 ADR は判断記録として要点のみ残す。

### 要点

- **カスタム VPC**（デフォルト VPC を不使用）
- **Public / Private サブネット分離**（ALB は Public、ECS / RDS は Private）
- **VPC Endpoint で NAT Gateway を代替**（ECR API / ECR DKR / S3 Gateway / CloudWatch Logs）
- **ECS Egress を最小化**（VPC 内 :443 / :5432 / :53 のみ）
- **RDS SG のメンテ用 my_ip 許可を削除**（以後は Bastion + SSM 経由）
- **Admin ALB の internal 化はスコープ外**（本番移行タスクとして残す）

---

## Consequences

### Pros

- **パブリック IP 完全排除** — ECS / RDS はインターネットから到達不可
- **Egress 最小化** — 侵害時の横展開リスク低減
- **本番理想形を PoC で検証** — 本番設計がそのまま流用可能
- **ALB DNS 名保持** — SPA の環境変数変更不要
- **RDS はインプレース更新** — データロスなし

### Cons

- **月額コスト増** — +$22/月（VPC Endpoint Interface 3 個）
- **デバッグ性の低下** — DB 直接メンテが不可になる（Bastion 経由になる）
- **Admin ALB はまだ公開側** — 本番移行時に対応（keycloak-network-architecture.md §6 N2）

### Alternatives Considered

| 案 | 判断 |
|----|------|
| 現状維持（SG Egress のみ絞る） | パブリック IP が残るため却下 |
| Private Subnet + **NAT Gateway** | 月 $32+ で VPC Endpoint より高コスト。却下 |
| Private Subnet + **VPC Endpoint**（採用） | 月 $22、本番標準パターン。採用 |

---

## Follow-up

本番移行時に追加対応すべき項目は [keycloak-network-architecture.md §6](../common/keycloak-network-architecture.md) に番号付き（N1〜N15）で整理済。
