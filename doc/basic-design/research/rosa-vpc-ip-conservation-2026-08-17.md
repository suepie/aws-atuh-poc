# ROSA HCP × Transit Gateway：VPC IP 節約と CIDR 隠蔽の検討

- **日付**: 2026-08-17
- **種別**: research note（U6 §6.2 サブネット設計 / O-10 egress の裏付け）
- **問い**: 「プライベートとはいえ TGW で繋がるので節約したい。ROSA の大きな IP レンジを TGW 側から隠せるか」→ front VPC(TGW+ALB) と ROSA VPC(NLB+クラスタ+DB) に分割し PrivateLink で繋ぐ案の是非。さらに「Transit と重なる routable は /24〜/22」「各 VPC /23・Broker 1・IdP 1・編集系別 VPC」で成立するか。
- **関連**: [06 §6.2](../06-infra-network-design.md)（サブネット設計 D-U6-03）/ [06 §6.3.2 D-U6-06](../06-infra-network-design.md)（バックチャネル PrivateLink）/ [06 §6.7.3 O-10](../06-infra-network-design.md)（egress）/ [ADR-056](../../adr/056-rosa-adoption-decision.md) / [ADR-063](../../adr/063-brand-unit-architecture.md)

---

## 1. 結論（3 行）

1. **「ROSA が VPC の大きな CIDR を食う」は EKS の常識を ROSA に当てはめた誤解**。ROSA は OVN オーバーレイで **Pod は VPC IP を消費しない**。routable を食うのは **Machine CIDR（ノード）だけ＝マルチ AZ 最小 /24**。
2. **PrivateLink 分割案は技術的に成立**（② を TGW 非 attach → ② の CIDR は完全に隠れ、重複も AWS 公式に OK）。ただし **egress が単方向 PrivateLink では出せない**のが唯一の関門。
3. **/23・Broker 1 VPC・IdP 1 VPC・編集系別 VPC は成立**。4 種別×3AZ が /23 に収まり、ノードは約 8 倍のヘッドルーム。唯一の判断は routable /22 を「そのまま晒す」か「CGNAT 退避で ALB だけに縮める」か。

---

## 2. 一次情報（要点・出典）

### 2.1 ROSA は VPC IP を大きく食わない（OVN オーバーレイ）
- ROSA/OpenShift の既定 CNI = **OVN-Kubernetes（Geneve オーバーレイ）**。Pod IP は cluster network CIDR（既定 `10.128.0.0/14`）から、Service は `172.30.0.0/16` から割当。**いずれも VPC 外の内部空間で VPC IP を消費しない**。[AWS blog: ROSA architecture and networking](https://aws.amazon.com/blogs/containers/red-hat-openshift-service-on-aws-architecture-and-networking/)（"The Service and POD CIDRs are private address spaces internal to OpenShift"）/ [OVN-Kubernetes plugin](https://docs.redhat.com/en/documentation/openshift_container_platform/4.16/html/networking/ovn-kubernetes-network-plugin)
- **EKS の AWS VPC CNI は Pod ごとに VPC IP を消費**（＝大きな CIDR を食う）。ROSA には当てはまらない。[EKS custom networking](https://aws.github.io/aws-eks-best-practices/networking/custom-networking/)
- **VPC(routable) を消費するのは Machine CIDR（ノードサブネット）だけ**。既定 `10.0.0.0/16`。最小 **マルチ AZ /24・シングル AZ /25**。ノードは overlay ゆえ ≒1〜2 IP/台（ENI プライマリ）。[Red Hat: IP addressing and subnets](https://cloud.redhat.com/experts/rosa/ip-addressing-and-subnets/) / [AWS: ROSA HCP getting started](https://docs.aws.amazon.com/rosa/latest/userguide/getting-started-hcp.html) / [rosaworkshop CIDR defaults](https://www.rosaworkshop.io/rosa/2-deploy/)
- Service/Pod CIDR は**他クラスタ・他 VPC と重複可**（クラスタ内部通信専用）。ただし **`100.64.0.0/16` は OVN が内部予約**（CGNAT を使う場合はこの /16 を回避）。[Red Hat: CIDR range definitions](https://docs.redhat.com/en/documentation/red_hat_openshift_service_on_aws/4/html/networking/cidr-range-definitions)

### 2.2 PrivateLink は CIDR を疎結合にする（TGW は CIDR を要求）
- **TGW は接続 VPC の CIDR をルートテーブルに要求し、メッシュ内で重複不可**（重複すると伝播されず到達不能）。[AWS: TGW VPC attachments](https://docs.aws.amazon.com/vpc/latest/tgw/tgw-vpc-attachments.html) ＝ IP 枯渇・CIDR 調整問題の根源。
- **PrivateLink は provider の CIDR をルートに要求せず、consumer/provider の CIDR が重複していても動作**（AWS 公式明記）。[Prescriptive Guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/integrate-third-party-services/architecture-1.html)（"allows for overlapping CIDR blocks"）/ [Multi-VPC whitepaper](https://docs.aws.amazon.com/whitepapers/latest/building-scalable-secure-multi-vpc-network-infrastructure/aws-privatelink.html)
- **Interface Endpoint の IP 消費 = AZ ごとに ENI 1 個/サービス**。[Create interface endpoint](https://docs.aws.amazon.com/vpc/latest/privatelink/create-interface-endpoint.html)
- **PrivateLink は単方向（consumer→provider）**。② の egress は別途。[PrivateLink FAQ](https://aws.amazon.com/privatelink/faqs/)
- コスト: PrivateLink データ処理 **$0.01/GB** < TGW **$0.02/GB**。時間課金は PrivateLink=エンドポイント×AZ×サービス数 / TGW=attach 単位。どちらが安いかはトラフィック量とサービス数次第。[PrivateLink pricing](https://aws.amazon.com/privatelink/pricing/) / [TGW pricing](https://aws.amazon.com/transit-gateway/pricing/)

---

## 3. /23 サブネット設計（4 種別 × 3 AZ）

/23（512 IP）を **AZ ごとに /25（128 IP）** で 3 つ、各 /25 を 4 種別に分割：

| 種別 | サイズ/AZ | usable | 最大消費（本基盤） |
|---|---|---|---|
| **Node（内部NLB＋Worker＋Infra）** | /26（64） | 59 | KC ~6-7＋Infra ~1＋NLB ENI ＝ ~10。**8 倍ヘッドルーム** |
| **ALB（Internal）** | /27（32） | 27 | ENI 自動増減。十分 |
| **TGW attachment** | /28（16） | 11 | AZ×1 |
| **Aurora** | /28（16） | 11 | Writer/Reader/Failover |
| **小計/AZ** | **/25（128）** | | |

- 3 AZ × /25 = 384 → **残り 1 つの /25 が丸ごと予備**（4 AZ 目・急拡張用）。
- Node 3×/26 = 合計 **/24 相当 = ROSA HCP 最小 Machine CIDR と一致**。使える Node IP 合計 ~177 に対し最大ノード ~20（KC max 18＋Infra、[06 §6.5](../06-infra-network-design.md)）→ **枯れない**。Pod はオーバーレイなのでノード増でも ENI 分しか増えない。

## 4. 3 案の比較（IP 節約目的）

| | A. 現状（VPC 全体を TGW） | B. secondary CGNAT CIDR（1 VPC・推奨候補） | C. PrivateLink 分割（front/ROSA 2 VPC） |
|---|---|---|---|
| TGW に晒す CIDR | VPC 全体（ノード含む） | **ALB＋TGW attach の極小 CIDR のみ** | **front VPC の極小 CIDR のみ** |
| ノード IP 隠蔽 | されない | ノードを CGNAT secondary（`100.64.0.0/16` 回避）に置き TGW 非広告（ALB で終端＝TGW はノード到達不要） | ② ごと隠れる・重複可 |
| 追加コスト | なし | **ほぼなし**（secondary CIDR は無料） | NLB Endpoint Service＋Interface Endpoint＋ALB→NLB 二段 |
| 構成の重さ | 軽 | 軽〜中（1 VPC のまま） | 重（2 VPC/Acct・経路増） |
| セキュリティ | — | — | **＋**（TGW 側から見えるのは公開 NLB のみ。クラスタ網スキャン不可＝IdP-KC ブラスト半径隔離と同方向） |
| egress | 現状どおり | 要 O-10（zero_egress 推奨） | 要 O-10（zero_egress ほぼ必須） |

**egress の関門（全案共通）**: PrivateLink は単方向なので ② の外向きは別経路。P-18 の集中 egress（他組織 NFW）は L3 到達＝TGW が要るため「② を完全に TGW から隠す」と両立しない。→ **zero_egress（案 B：ECR ミラー＋ VPC 内 Interface Endpoint）にすれば egress ≒ 0 で TGW egress 経路が不要**になり、CIDR 隠蔽が綺麗に閉じる（O-10 と直結）。

## 5. Transit 予算と編集系別 VPC

- **Broker /23 ＋ IdP /23 ＝ routable /22**。「Transit と重なるのは大きくても /22」と一致し**成立はする**が、2 クラスタで枠を使い切る。編集系別 VPC・将来ブランド分の余裕が要るなら **(a) 枠を /21 に拡張** か **(b) CGNAT 退避で各 VPC の routable を ALB だけ（~/27）に縮める**（→ 2 クラスタ＋別 VPC＋将来分が単一 /24 に収まる）。
- **編集系別 VPC（ユーザ編集 API #2 ＋ 管理 SPA、[ADR-063](../../adr/063-brand-unit-architecture.md)/[ADR-062](../../adr/062-idm-api-execution-form-lambda.md)）**: IdP-KC の Admin API（内部 NLB）へ cross-VPC 到達 → **PrivateLink 推奨**（既存 [D-U6-06](../06-infra-network-design.md) と同方式）。この VPC の routable は API 用 ALB だけで小さく、独自 /24 や CGNAT で十分。IdP-KC の /23 を圧迫しない。

## 6. 推奨と未確認

**推奨**: routable に載せるのは「インバウンド ALB ＋ TGW attach」だけとし、**ノード・Aurora・Interface Endpoint は CGNAT secondary（案 B）に退避**。egress は zero_egress（O-10 案 B）方向で固める。DB を ROSA VPC 同居させる点は全案で正しい（KC Pod→Aurora は VPC 内直結、[06 §6.4](../06-infra-network-design.md)）。PrivateLink 分割（案 C）は「② を完全隔離アイランドにしたい／将来ブランド多数で CIDR 調整を完全に無くしたい」場合の上位オプション。

**未確認（要 Red Hat 確認 / PoC）**:
1. **ノードサブネットを CGNAT secondary CIDR に置く ROSA 公式サポート**（手法は VPC/EC2 レベルで成立、Red Hat 明記は未確認・OVN 予約 `100.64.0.0/16` 回避必須）。
2. **ノード 1 台あたりの正確な ENI/IP 数**（overlay から ≒1〜2 と導出、実機 PoC 推奨）。
3. **集中 egress を必須にする場合の「egress 専用 小 CIDR だけ TGW attach」折衷**（AWS 公式パターンでなく論理導出、PoC 検証）。
