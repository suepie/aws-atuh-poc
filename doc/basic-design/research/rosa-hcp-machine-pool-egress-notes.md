# 検討ノート: ROSA HCP の実構成(Infra Node 不在 / Machine Pool / Egress / Aurora 接続)

日付: 2026-07-23 / 出典: ユーザー検討(別途調査)。U6 v1.2 改訂の根拠 / 関連: [06-infra-network-design.md](../06-infra-network-design.md)、[rosa-hcp-adoption-research.md](rosa-hcp-adoption-research.md)

## 1. HCP の構成実像

| レイヤ | 配置 | 中身 |
|--------|------|------|
| Control Plane | Red Hat サービスアカウント(顧客 VPC 外) | API server × 2 + etcd × 3、3 AZ 冗長。顧客課金・VPC に出ない。サイジングは Worker 数に応じ Red Hat 自動 |
| Worker のみ | 顧客 VPC Private Subnet | KC Pod + **infra 系ワークロードが相乗り** |
| PrivateLink Endpoint | 顧客 VPC 内 | Worker → CP 接続用 |

**最重要**: HCP には Classic の専用 Infra Node(router/registry/monitoring 用 3 ノード)が**存在しない**。これらは Worker に載る → Machine Pool の役割分離が必須(下記 3)。

## 2. 接続 3 系統 + Egress

- ユーザ(フロントチャネル): Internet → 他組織 CF+WAF+ALB/NLB(P-18) → (TGW/PrivateLink) → 自管理 Internal ALB(secret header + /admin 403) → IngressController NLB(Private) → KC Pod
- Red Hat SRE: PrivateLink 経由で CP 管理(顧客 /admin と完全別経路。Worker アクセスは Red Hat 側 break-glass)
- 顧客側メンテ: SSM ポートフォワード → Internal ALB/Admin(D-U6-12)
- Egress: Worker → **AZ ごとに Public Subnet + NAT GW が必須**(zero-egress 選択時を除く) → (a) 運用系: registry.redhat.io/quay/ECR/STS/S3/OLM (b) 顧客 IdP token/JWKS/userinfo 1000+ FQDN → 他組織 NFW ドメインフィルタ
- **zero-egress(`zero_egress:true`)**: ECR ミラー化で運用系 outbound を VPC 内完結 → NAT 不要、TGW で他組織 Outbound 専用経路へ。**P-18・PCI DSS 志向と製品仕様が噛み合う**ため積極検討(O-10)。フェデ Egress の REQ-OUT 要求は案 A/B いずれでも必要
- Ingress は新規 **NLB が既定**(CLB 廃止方向)。platform 用 Private NLB とアプリ公開用を追加 IngressController で分離が Red Hat 推奨

## 3. Machine Pool 役割分離(2 Pool 構成)

| Pool | テイント | 載せるもの | スケール |
|------|---------|-----------|---------|
| default(infra) | なし(**ROSA はテイントなし Pool 最低 1 必須**) | router / monitoring / registry / OLM / Operator / SCIM Facade | 準静的(クラスタ規模・監視量で手動確保。1000+ IdP では Prometheus メモリを先に見積る) |
| keycloak 専用 | `dedicated=keycloak:NoSchedule` | KC Pod のみ | 動的(HPA → Pending → Cluster Autoscaler が本 Pool のみ増設) |

- 分離しないと KC バーストが infra と食い合い「監視が飛ぶ・ingress が詰まる」(router は replica 固定、monitoring は Pod 数で自動増しない)
- スケール 3 主体は独立: CP = Red Hat 自動 / Worker = Pool 単位 / Pod = HPA
- **サイズ変更 = EC2 作り直し** → ピーク帯用 c7g.2xlarge は事前に別 Pool 定義(Blue/Green)。ノード増減・バージョンアップは PDB(maxUnavailable=1) + drain で無停止

## 4. Aurora コネクション設計の精緻化

| 項目 | 値 |
|------|-----|
| Agroal(Quarkus)デフォルト db-pool-max-size | **100/pod(放置厳禁)** |
| Keycloak 公式推奨 | **initial = min = max 等値**(チャーン回避 + server-side prepared statement 5 回実行で有効化) |
| r7g.xlarge max_connections | ≈ 3,300(`LEAST(DBInstanceClassMemory/9531392, 5000)`、32GB) |
| 総接続 | Broker 9×30=270 / IdP-KC 18×30=540、予約枠(superuser 3 + Aurora 内部 + Admin API クライアント + postgres_exporter + バッチ)控除後も大幅余裕 |
| 等値化トレードオフ | scale-out 時に新 Pod が即 min 本確保 — Writer 容量内で等値化が落とし所 |
| RDS Proxy/PgBouncer | 不要(一般則:「1 pod 接続 <5 × pod 数百」で初めて必要)。IdP-KC 数百 pod シャーディング段階で PgBouncer transaction mode を拡張パス検討 |
| idmap 補助 DB | API 層/バッチ側の別プールで独立計上 |

## 5. 第 2 弾検討(2026-07-24 追記、U6 v1.4 で反映)

- **大阪 DR の Pool 不整合**: KC Pod は toleration/nodeSelector 持ちのため、テイントなし infra ノードのみの大阪では Failover 時にスケジュール不能 → **大阪にも KC 専用 Pool(labeled/tainted、min 0)を事前定義**し 0→3+ スケール
- **infra Pool サイズ**: c7g.large(4GB) は 1000+ IdP/10M の Prometheus に不足懸念 → O-11 比較対象に c7g.xlarge / r7g / m7g 併記(台数でなくサイズで吸収)
- **サブネット 4 層設計**: TGW /28・ALB 専用 /26-27・Worker /24+(OVN のため Pod 数でなくノード数採番)・Aurora /27-28。**CIDR は install 後不変ゆえ事前確定必須**、大阪も東京同等スケール収容サイズで確保
- **secret header の格下げ**: Internal ALB トポロジで本来目的(CF 迂回防止)は達成済み → 主防御 = /admin 403 + SG エッジ送信元限定、secret header = 追加層(他組織のローテ運用依存のため)
- **In-B(NLB)推奨の TLS 根拠**: CloudFront は WAF のため終端不可避(両パターン共通)。2 段目を先方 ALB に置くと平文が他組織 VPC に出現 → NLB パススルーで**平文出現位置を自管理 VPC に閉じる**

## U6 への反映(2026-07-23 v1.2 で適用済み)

§6.2.1(CP/接続 3 系統/NAT・zero-egress O-10/NLB Ingress)/ §6.2.2(2 Pool 構成 + 2xlarge 事前 Pool)/ §6.2.3(infra Pool 加算 $2,032/月)/ §6.4.2(等値化 30/30/30 + 予約枠)/ §6.4.3(PgBouncer 拡張パス)/ §6.7.3(zero-egress と REQ-OUT の関係)/ §6.8.1(O-10/O-11)
