# 単一 VPC 集約のリスク評価と分離トリガー（AWS 出典付き）

- **日付**: 2026-08-18
- **種別**: research note（U6 §6.2 VPC/サブネット設計 / ADR-062・063 の裏付け）
- **問い**: 認証基盤（Keycloak クラスタ ＋ identity Aurora〔PW ハッシュ〕＋ authz Aurora ＋ idm-api Lambda）を **1 つの VPC に集約**した場合のリスクは何か。単一 VPC を受容する条件と、将来 VPC/アカウント分離へ格上げするトリガーを決める。
- **背景**: 現行 06 ベースライン（A 案）は **idm-api Lambda ENI をクラスタ VPC の層③に同居**させている（[06 §6.2.1 D-U6-11](../06-infra-network-design.md)）。本ノートはこの構成の AWS 公式線に照らしたリスクを整理する。
- **関連**: [ADR-062 idm-api=Lambda](../../adr/062-idm-api-execution-form-lambda.md)（P0/P1 障害ドメイン分離）/ [ADR-063 §認可データ配置粒度 A+C](../../adr/063-brand-unit-architecture.md)（identity/authz を別 Aurora/CMK/SG）/ [rosa-vpc-ip-conservation](rosa-vpc-ip-conservation-2026-08-17.md)（PrivateLink・CIDR）/ [rosa-sre-live-log-visibility](rosa-sre-live-log-visibility-2026-08-14.md)（G-DPA・SRE 隣接）

---

## 1. AWS 公式線の要旨（アカウント ＞ VPC ＞ サブネット/SG）

AWS は VPC を「絶対的なセキュリティ境界」ではなく**「アカウント境界のサブセット」「データ機微度に応じた層分割の一手段」**と位置づけ、**機微度が上がるほど境界を サブネット→VPC→アカウント へ格上げ**せよとする。

- **Well-Architected SEC05-BP01「Create network layers」**: **「全リソースを単一 VPC/サブネットに作る」を明示的アンチパターン**とし、機微度で境界格上げを規定（未確立時リスク＝**High**）。[出典](https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_network_protection_create_layers.html)
- **AWS SRA（Application account）**: 「VPC はワークロードセグメント分離（アカウント境界のサブセット）／単一 VPC 内の層分離は SG（インスタンスレベル）」。**「VPC 内リソースはデフォルトで相互ルーティング可能」**と明記。[出典](https://docs.aws.amazon.com/prescriptive-guidance/latest/security-reference-architecture/application.html)

→ 認証基盤全体を 1 VPC に集約する構図は、この SEC05-BP01 アンチパターンに直接該当する。PW ハッシュ DB・認可 DB は環境内で最高機微に属するため、公式論理では「サブネット分離では足りず VPC/アカウント境界を検討すべき層」。

---

## 2. リスク一覧（重要度順・AWS 出典＋本基盤含意＋現行緩和＋残差）

| # | リスク | AWS 出典 | 本基盤での含意 | 現行緩和 | 残差 |
|---|---|---|---|---|---|
| ① | **横展開・ブラスト半径** | SEC05-BP02（層内を認証済みと仮定するな／east-west 最小権限／SG は L4 の"出発点"）+ account 分離が横展開を防ぐ | idm-api Lambda（P1・API GW 経由でインターネット隣接）＋ KC ノード（PW ハッシュ）＋ identity/authz Aurora が同一 VPC。**到達性はデフォルト開通・唯一の壁が SG** | SG 最小権限＋NetworkPolicy＋4 層サブネット | **ソフト境界**（設定の正しさ 1 枚に集約）。現行 D-U6-11 の「引き分け」評価は Admin API 経路限定で、**identity/authz Aurora・クラスタ網への横展開全体は未評価** |
| ② | **PrivateLink 単方向境界の喪失** | Multi-VPC WP（consumer→provider の接続開始のみ）／SEC05-BP02（peering でなく PrivateLink） | 単一 VPC は双方向到達（SG 次第）。侵害クラスタノード→authz Aurora、侵害 idm-api→クラスタ網が**構造的に塞げない** | — | ハード境界（構造分離）が無い |
| ③ | **機微データの comingling** | Organizing WP（機微データストアは専用境界へ／account-level でブラスト半径限定）／SRA（別境界でロール・鍵・データの comingling 回避） | identity CMK／authz CMK／Lambda 実行ロール／Admin API 資格が同一 VPC 境界内 | A+C でデータ層は別 CMK/SG（[D-U7-19](../07-security-compliance-design.md)） | **VPC 境界は共有**。AWS 線では最高機微は専用 VPC/アカウントへ格上げ推奨 |
| ④ | **監査・コンプラ境界の肥大** | SRA（VPC=ワークロードセグメント分離） | identity（PII/PW）＋管理ツール＋認可 DB が 1 VPC → **セグメンテーション論証（APPI/監査）が困難** | — | 証跡が不明瞭 |
| ⑤ | **ROSA/Red Hat SRE 隣接（本基盤固有）** | （一般原則の適用） | クラスタ VPC は ROSA 運用領域で SRE が backplane で触る。authz/idm-api を同 VPC に置くと機微面が「Red Hat 運用が走る VPC」に同居 | SRE は AWS アカウント権限なし（IAM 分離）ゆえ Aurora 直アクセスはしない | [G-DPA/SRE 可視性](rosa-sre-live-log-visibility-2026-08-14.md)の隔離方向と逆 |
| ⑥ | **ライフサイクル/DR の結合** | — | クラスタ保守（ROSA 変更・ノードサイクル・VPC レベル変更）と編集/authz が運命共同体。コールド DR 再構築で巻き込む | — | 独立進化・独立再構築ができない |
| ⑦ | **IP/CIDR・スケール結合（副次）** | — | 全部 /23 共有・Transit-routable 単位。編集/authz の成長がクラスタ IP と競合 | 別 VPC なら小 CIDR＋TGW 隠蔽可（[research](rosa-vpc-ip-conservation-2026-08-17.md)） | — |
| ⑧ | **VPC レベル障害ドメイン（副次・稀）** | — | 誤 NACL/ルート・ENI/SG 上限到達が両方に波及 | — | 稀 |

> **表現の正確性（AWS 一次情報の限界）**: (a) AWS は「VPC は絶対境界」とは述べず「アカウント境界のサブセット」と相対化する（最強はアカウント）。よって主張は「VPC 分割 vs 単一 VPC」より **「機微度に境界を格上げしていない（SEC05-BP01/SRA）」** の枠組みが忠実。(b) PrivateLink の単方向は**接続開始方向**の話（確立後の応答は返る）。(c) 「SG は横展開に弱い」と明文で述べた AWS の一文は未取得（デフォルト相互ルーティング＋BP02 アンチパターンからの妥当な含意）。(d) Keycloak/認可 DB への名指しガイダンスは無く、一般原則の適用。

---

## 3. 単一 VPC を受容する条件（採る場合の必須要件）

Phase 1 で A 案（単一 VPC）を採るなら、SEC05-BP02 を満たすため以下を**必須**とする:

1. **east-west 最小権限**: Lambda SG→Admin NLB SG のみ／authz Aurora SG＝Lambda SG のみ／**identity Aurora SG＝KC Pod のみ**（idm-api は identity Aurora に触れない＝Admin API 経由のみを SG で担保）＋ NetworkPolicy で pod 間も絞る。
2. **横展開検知**: VPC Flow Log ＋ GuardDuty ＋ Golden 検知に「東西の想定外接続」を追加。
3. **data perimeter**（RCP/SCP）で ID・リソース・ネットワークの三点を予防ガードレール化。[出典](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_data-perimeters.html)
4. **層順の機械検査**: 最内側＝identity Aurora（PW ハッシュ）／最外側＝idm-api Lambda。両者が同一 SG に触れないことを CI で検査。

---

## 4. 分離トリガー（VPC/アカウント境界へ格上げする条件）

以下のいずれかが立ったら **2 VPC（Keycloak/identity VPC ＋ 管理/authz VPC）** へ、さらに強ければ **authz 別アカウント**（[ADR-063 オプション B](../../adr/063-brand-unit-architecture.md)）へ格上げする:

- 規制ブランド（アカウントレベル分離が契約/監査要件）
- 高保証契約・PCI/APPI で明確なセグメンテーション証跡が要る
- Red Hat SRE 隣接からの authz/管理面の隔離を強化したい（G-DPA 連動）
- ブラスト半径を「SG 設定の正しさ」でなく「ネットワーク構造」で縮めたい

**現行の推奨方向（2026-08-18）**: AWS が SEC05-BP01 で単一 VPC 集約を **High リスクのアンチパターン**とすることを踏まえ、**2 VPC 分離（B 案）を基本方向**とする。idm-api は 1 本のまま管理 VPC に置き、Keycloak Admin API へは PrivateLink 単方向、authz Aurora は管理 VPC 内直結。identity Aurora は Keycloak VPC で Pod のみが触る。詳細トポロジ・ENI・PrivateLink フローは [rosa-vpc-ip-conservation](rosa-vpc-ip-conservation-2026-08-17.md) と 06a §A.6。

---

## 主要出典
- SEC05-BP01 Create network layers: https://docs.aws.amazon.com/wellarchitected/latest/framework/sec_network_protection_create_layers.html
- SEC05-BP02 Control traffic flow within your network layers: https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/sec_network_protection_layered.html
- AWS SRA – Application account: https://docs.aws.amazon.com/prescriptive-guidance/latest/security-reference-architecture/application.html
- Multi-VPC WP – AWS PrivateLink: https://docs.aws.amazon.com/whitepapers/latest/building-scalable-secure-multi-vpc-network-infrastructure/aws-privatelink.html
- Organizing your AWS environment – Benefits of multiple accounts: https://docs.aws.amazon.com/whitepapers/latest/organizing-your-aws-environment/benefits-of-using-multiple-aws-accounts.html
- Zero Trust: An AWS perspective: https://aws.amazon.com/blogs/security/zero-trust-architectures-an-aws-perspective/
- Establishing a data perimeter on AWS: https://aws.amazon.com/blogs/security/establishing-a-data-perimeter-on-aws/
