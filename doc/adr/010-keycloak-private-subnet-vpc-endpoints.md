# ADR-010: Keycloak 環境を Private Subnet + VPC Endpoint 構成へ移行

- **ステータス**: Accepted
- **日付**: 2026-04-21
- **関連**: [ADR-008](008-keycloak-start-dev-for-poc.md)、[keycloak-network-architecture.md](../common/keycloak-network-architecture.md)

---

## Context

PoC 初期構成では、Keycloak の ECS タスク・RDS・ALB をデフォルト VPC の public サブネットに配置し、ECS タスクには `assign_public_ip = true` でパブリック IP を付与していた。理由は **ECR pull にインターネット経路が必要だったため**。

しかし本構成には以下のセキュリティ課題があった:

1. **ECS タスクにパブリック IP** — SG Ingress は ALB SG に限定しているが、タスク自体が公開ネットワーク上に露出。セキュリティ監査で指摘されやすい
2. **ECS Egress 全開** — 万一タスクが侵害された場合、任意の外部通信（C2 等）が可能
3. **RDS SG に自分の IP を許可** — `Temporary: from my IP for DB maintenance` として残存。本番では絶対 NG
4. **デフォルト VPC を使用** — サブネット設計が本番想定と乖離

本番の理想形（Private Subnet + VPC Endpoint）を PoC で検証することで、本番設計の再利用性を高めつつセキュリティ監査要件も満たす。

---

## Decision

Keycloak インフラを以下の構成に移行する:

### ネットワーク設計

- **カスタム VPC（10.0.0.0/16）** を新規作成（デフォルト VPC を不使用）
- **2 AZ × (Public / Private)** = 4 サブネット構成
  - Public: 10.0.1.0/24, 10.0.2.0/24（ALB のみ配置）
  - Private: 10.0.11.0/24, 10.0.12.0/24（ECS / RDS 配置）
- **Internet Gateway** は Public Subnet のみに経路、Private はインターネット経路なし

### VPC Endpoint

Private Subnet から AWS サービスへのアクセスは以下の Endpoint で VPC 内完結:

| サービス | タイプ | 用途 |
|---------|-------|------|
| ECR API | Interface | docker pull の認証・メタデータ |
| ECR DKR | Interface | docker image レイヤー取得 |
| S3 | Gateway | ECR image の実体（S3 バックエンド） |
| CloudWatch Logs | Interface | ECS タスクログ出力 |

**NAT Gateway は使用しない**（月 $32+ 対して VPC Endpoint は月 $22 で VPC 内完結のため）。

### SG Egress の最小化

ECS SG の Egress を以下に限定（従来は `0.0.0.0/0` 全開）:
- VPC CIDR への :443 TCP（VPC Endpoint 経由の AWS サービス）
- VPC CIDR への :5432 TCP（RDS）
- VPC CIDR への :53 UDP/TCP（VPC DNS Resolver）

### RDS SG のメンテ IP 削除

従来の「自分の IP を許可」ルールを削除。以後 DB アクセスは:
- 通常: ECS Task 経由
- メンテ: Bastion + SSM Session Manager（本番移行時に構築）

### Admin ALB はスコープ外

Admin ALB の internal 化（VPN 経由アクセス）は本 ADR のスコープ外とし、本番移行時のタスクとして残す（[keycloak-network-architecture.md](../common/keycloak-network-architecture.md) の N2）。

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
- **Admin ALB はまだ公開側** — N2 として本番移行時に対応

### Alternatives Considered

| 案 | 判断 |
|----|------|
| 現状維持（SG Egress のみ絞る） | パブリック IP が残るため却下 |
| Private Subnet + **NAT Gateway** | 月 $32+ で VPC Endpoint より高コスト。却下 |
| Private Subnet + **VPC Endpoint**（採用） | 月 $22、本番標準パターン。採用 |

---

## Follow-up

本番移行時に追加対応すべき項目:

- **N1**: HTTPS 化（ACM 証明書 + `start --optimized` モード）
- **N2**: Admin ALB を internal に変更 + VPN / DirectConnect 経路
- **N5**: Keycloak の `KC_HOSTNAME` を正式ドメインに設定
- **N10**: AWS WAF による攻撃検知
- **N11**: DB メンテアクセス経路（Bastion + SSM）の確立

詳細: [keycloak-network-architecture.md §6](../common/keycloak-network-architecture.md)
