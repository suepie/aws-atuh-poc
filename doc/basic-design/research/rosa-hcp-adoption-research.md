# 調査報告: ROSA 採用の残論点(Classic vs HCP / 大阪 / RHBK / Workload Identity / コスト)

調査日: 2026-07-23 / 関連: P-01/P-15、U1/U6、ADR-041/051/055/056

## 結論サマリ

1. **ROSA HCP 一択**。Red Hat が Classic の新規クラスタ作成に期限を公式化(「ROSA classic lifecycle update」access.redhat.com/articles/7087075)。HCP: SLA 99.95%、Red Hat SRE 運用、STS 必須、PrivateLink 標準。
2. **大阪(ap-northeast-3)対応済み — ADR-056 の TBD 解消**。AWS 公式リージョン表(docs.aws.amazon.com/general/latest/gr/rosa.html、2026-07-23 取得)で HCP/Classic とも Yes。**東京 + 大阪の ROSA HCP 対称 DR 構成が成立**(ADR-051 と整合)。残: 大阪側インスタンス在庫 + vCPU クォータの実確認のみ。
3. **RHBK は ROSA に内包され追加サブスク不要**(KB 7044244: RHBK エンタイトルメントは OCP サブスクに含まれ ROSA でも有効)。RHBK は「customer installed software」— Red Hat がサポート、運用は顧客。**旧試算の「RHBK サブスク別途 $5,000-20,000/3y」は ROSA 採用時には不要**。ROSA + Upstream KC は非合理(費用を払いつつコミュニティサポート)→ **RHBK Operator(OperatorHub)一択**。
4. **サポート責任分界**: ROSA インフラ(CP/worker OS/OpenShift/Operator 基盤)= Red Hat SRE / RHBK(Realm 設定・SPI・DB・アップグレード)= 顧客運用 + Red Hat サポート / **Custom SPI(HRD/Re-Activation 等)= 顧客責任**(SPI 起因でない KC 本体障害はサポート対象)。
5. **Workload Identity**: EKS Pod Identity は EKS 専用で ROSA に無し。ROSA は **クラスタ OIDC プロバイダ + pod identity webhook が標準組込**で、IRSA 相当(SA アノテーション → AssumeRoleWithWebIdentity、トークン 1h ローテーション)が公式手順(docs.redhat.com「Assuming an AWS IAM role for a service account」)。**ADR-041 は該当行の差し替えのみで 2 段階 STS チェーン設計は維持**。Cross-account は Red Hat Cloud Experts パターンあり。
6. **コスト(2026-07-23、料金据え置き確認)**: HCP cluster fee $0.25/h ≈ **$182.5/月/クラスタ**(実質固定)。Worker ROSA fee $0.171/4vCPU/h、1y 契約 33% 引 / **3y 契約 55% 引**(コンソール未対応、aws-redhat-partnerteam@amazon.com 経由)。EC2 は別途 RI/SP。
7. **クラスタトポロジ**: クラスタ 1 本追加の固定増分 ≒ **+$500/月前後**(cluster fee + 最小 worker 2 ノードの ROSA fee + EC2)。コストだけなら「1 クラスタ + namespace 分離(broker-kc / idp-kc + NetworkPolicy + 別 DB)」が合理的。**ただし P-17(IdP-KC 別 AWS アカウント)を採る場合は必然的に 2 クラスタ** → U1 で「別アカウント分離の目的 vs コスト」のトレードオフ判断が必要。DR 大阪はパイロットライトでも cluster fee + 最小 worker が別途。
8. **Aurora / Infinispan は好転**: KC 26.1 以降 **jdbc-ping がデフォルト**(multicast 不要、PoC 前提と完全整合)。multi-cluster v2 で外部 Infinispan 要件撤廃。RHBK 26.4 HA Guide が **Aurora PostgreSQL 15/16/17 を multi-site HA サポート DB に明記**、keycloak-benchmark 公式が「ROSA クロスサイト + Aurora」を手順化 — ADR-051 と方向一致。HCP でも worker は自アカウント VPC 内のため Aurora へは SG 直接続(旧調査の「PrivateLink 経由」は CP↔worker 間の話で DB 接続には不要 — rosa-detailed-analysis.md 要修正)。

## ADR-056 改訂案骨子

- **Decision**: 「Default 不採用(ECS Fargate + Upstream)」→ **「ROSA HCP + RHBK Operator を採用」**
- 形態: HCP(Classic は新規作成期限公式化のため対象外)/ 東京 + 大阪対称構成 / Phase 1 クラスタトポロジは P-17 判断に依存(1 クラスタ namespace 分離 or アカウント分離 2 クラスタ)
- 採用条件: ① PCI DSS/APPI 追加要件(etcd 非流入 + ガードレール + Red Hat AOC/DPA)整備計画承認、② 3y 契約見積取得(AWS パートナーチーム経由)、③ Stage A Terraform 書換 6-8 週の工数承認
- 残 TBD: ① Classic 正確 EOL 日付(HCP 採用なら非影響)、② 大阪インスタンス在庫・クォータ実確認、③ cluster fee の契約割引有無、④ RHBK 26.4 と upstream 26.x の Custom SPI 互換実証(ADR-055 の年 1-2 回追従前提)、⑤ multi-cluster v2 の RHBK サポート版数確認
- 波及改訂: ADR-041(Pod Identity → ROSA webhook + IRSA 方式)/ ADR-055 §A.6-A.7(ROSA パターン確定)/ ADR-051(大阪成立追記)/ rosa-detailed-analysis.md §4(RHBK サブスク行削除)・§7(大阪 Yes)・PrivateLink 記述修正 / rhbk-support-and-pricing.md §4.5

## RHBK サブスク要否トレードオフ表

| 選択肢 | 追加サブスク | KC サポート | 評価 |
|---|---|---|---|
| **ROSA HCP + RHBK Operator** | **$0(内包)** | Red Hat フル(運用は顧客) | **推奨** |
| ROSA HCP + Upstream KC | $0 | コミュニティのみ | 非合理 |
| ECS Fargate + Upstream(旧 Default) | $0 | コミュニティのみ | 最安だが商用サポートなし |
| EC2 RHEL + RHBK | Runtimes サブスク別途 | Red Hat | ROSA 不採用時のみ |

## 主要一次資料

- https://access.redhat.com/articles/7087075(Classic lifecycle)/ 7044244(RHBK エンタイトルメント)/ 7033107(RHBK Supported Configurations: ROSA 両方式 + Aurora 15-17)
- https://docs.aws.amazon.com/general/latest/gr/rosa.html(リージョン表・クォータ)
- https://aws.amazon.com/rosa/pricing/
- https://docs.redhat.com/en/documentation/red_hat_openshift_service_on_aws/4/html/authentication_and_authorization/assuming-an-aws-iam-role-for-a-service-account
- https://cloud.redhat.com/experts/rosa/cross-account-access-openid-connect/
- https://www.keycloak.org/2025/01/keycloak-2610-released(jdbc-ping デフォルト)/ keycloak.org/server/caching / keycloak-benchmark cross-site-rosa ガイド
- RHBK 26.4 High Availability Guide(2026-05-12 版)
