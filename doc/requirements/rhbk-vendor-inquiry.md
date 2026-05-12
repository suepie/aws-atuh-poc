# Red Hat build of Keycloak ベンダ問い合わせ文書

**作成日**: 2026-05-08
**目的**: 本番採用判断のため、Red Hat および認定リセラに公開情報で確定できない事項を照会する
**根拠**: [doc/reference/rhbk-support-and-pricing.md §8 Red Hat への確認事項リスト](../reference/rhbk-support-and-pricing.md)

---

## 1. 問い合わせ概要

### 1.1 背景

- AWS 上で Keycloak を用いた共有認証基盤の本番化を検討中
- PoC は OSS Keycloak 26.0.8 on AWS ECS Fargate + RDS PostgreSQL で完了
- 本番採用にあたり **Red Hat build of Keycloak（RHBK）の商用サポート利用を検討**
- 公開情報で確定できない事項を照会したい

### 1.2 想定する問い合わせ先

| # | 問い合わせ先 | 種別 | 期待する回答 |
|---|---|---|---|
| 1 | **Red Hat 営業（Japan）** | 直接 | サポート方針の公式回答、subscriber 限定 KB の内容 |
| 2 | **SB C&S 株式会社** | 認定リセラ | 国内大手リセラ。Red Hat 製品のディストリビューション |
| 3 | **日商エレクトロニクス** | 認定リセラ | エンタープライズ向け Red Hat 製品取扱 |
| 4 | **TIS インテックグループ** | 認定リセラ | OSS / Red Hat 製品の SI 経験あり |
| 5 | **AWS Marketplace（参考）** | 第三者 | ROSA 経由の課金パスの確認 |

> 通常は #1 → #2-#4 のいずれかでクロスチェック。同一質問を複数社に投げて回答を比較するのが確実。

### 1.3 期待する成果物

| 項目 | 形式 |
|---|---|
| Q1〜Q10 への書面回答 | メール or 公式回答書 |
| 正式見積（4-core / 8-core / 16-core 各バンド、Standard / Premium 各ティア、1 年 / 3 年） | 正式見積書 |
| サブスクリプション ToS / SLA 抜粋 | 文書 |
| KB 7072950 / 7044045 の Resolution 本文 | subscriber アクセス or リセラ経由展開 |

---

## 2. 確認事項一覧（[reference/rhbk-support-and-pricing.md §8](../reference/rhbk-support-and-pricing.md) 由来）

| # | 確認事項 | 優先度 |
|---|---|:---:|
| **Q1** | **AWS ECS Fargate** 上の RHBK は商用サポート対象か | **Critical** |
| **Q2** | **AWS EKS / EKS Fargate** での RHBK サポート範囲（KB 7072950 Resolution 本文） | **Critical** |
| Q3 | RHBK 26.4.x 採用時の **Aurora PostgreSQL** バージョン要件（17.x の正式対応時期） | High |
| Q4 | Multi-Site HA で **Aurora PostgreSQL 必須** の根拠と RDS PostgreSQL での代替可否 | High |
| Q5 | 本番ワークロードの **コア計算ルール**（Fargate vCPU 換算、HPA 時の最大値 or 平均ベース） | High |
| Q6 | **Hot DR / Warm DR** の境界定義（フェイルオーバ時間、自動切替の有無） | Medium |
| **Q7** | 認定リセラ経由での **正式見積** | **Critical** |
| Q8 | Red Hat Runtimes と Application Foundations の **新規購入時の差** と将来移行 | Medium |
| Q9 | RHBK **26.0.x の Maintenance フェーズ終了時期** と 26.4.x への upgrade パス | Medium |
| Q10 | **OpenJDK / Quarkus** のサブスクリプション要件（RHBK 同梱で十分か） | Low |

---

## 3. メール文面（日本語版・リセラ宛）

> 用途: SB C&S / 日商エレ / TIS など国内認定リセラへの初回照会
> 推奨: 担当営業がいる場合は §3.1（簡略版）、新規問い合わせは §3.2（フルバージョン）

### 3.1 簡略版（既存の取引がある場合）

```
件名: Red Hat build of Keycloak（RHBK）本番採用に関する技術・価格照会のお願い

XX 様

いつもお世話になっております。
弊社では現在、AWS 上で Keycloak を用いた共有認証基盤を構築中で、
本番採用にあたり Red Hat build of Keycloak（RHBK）の商用サポート利用を検討しております。

公開情報で確定できない以下の事項について、ご回答いただけますでしょうか。
詳細な確認事項は別添「rhbk-vendor-inquiry-detail.md」をご参照ください。

最重要（Critical）
─────────────────────────
1. AWS ECS Fargate 上での RHBK は商用サポート対象になりますか？
   （ECS は Kubernetes ではないため、KB 7072950 のスコープ外と読めます）

2. AWS EKS / EKS Fargate での RHBK サポート範囲
   （KB 7072950 の Resolution 本文を共有いただけますでしょうか）

3. 正式見積もり
   - 構成: Red Hat Runtimes（または Application Foundations）
   - コア数: 4-core / 8-core / 16-core
   - サポートティア: Standard / Premium
   - 期間: 1 年 / 3 年
   - 想定環境: 本番 + Hot Standby DR

合わせて、Red Hat への直接エスカレーションが必要な事項があれば、
御社経由でアレンジいただけると助かります。

ご検討のほど、よろしくお願いいたします。
```

### 3.2 フル版（新規問い合わせ・初回コンタクト）

```
件名: 【見積依頼】Red Hat build of Keycloak（RHBK）本番採用検討に伴う技術・価格照会

XX 株式会社
営業ご担当者様

突然のご連絡失礼いたします。
弊社【会社名】の【部署名・氏名】と申します。

■ 背景
弊社では現在、AWS 上で Keycloak を用いた共有認証基盤の本番化を検討しております。
PoC は OSS Keycloak（Upstream）26.0.8 を AWS ECS Fargate + RDS PostgreSQL 16
の構成で完了しており、機能要件・基本性能ともに満たしている状態です。

本番採用にあたり、商用サポートの観点から
Red Hat build of Keycloak（以下 RHBK）の採用を検討しております。

つきましては、公開情報のみでは確定できない以下の事項について、
ご回答および見積をお願いしたくご連絡いたしました。

■ 想定構成
- Keycloak バージョン: RHBK 26.4.x（または 26.0.x）
- 実行基盤候補: 以下の比較検討中
    A. AWS ECS Fargate（現 PoC 構成、商用サポート対象可否を確認したい）
    B. AWS EKS / EKS Fargate
    C. ROSA（Red Hat OpenShift Service on AWS）
    D. EC2 RHEL 9 + コンテナ
- データベース: Amazon RDS for PostgreSQL 16.x（または Aurora PostgreSQL）
- HA: Multi-AZ + Hot DR（別リージョン）
- リージョン: ap-northeast-1（DR は ap-northeast-3 等）

■ 確認事項

[Critical 項目]

Q1. AWS ECS Fargate 上での RHBK の商用サポート対象可否
    Red Hat KB 7072950 の表題が「サードパーティーの Kubernetes 環境
    （EKS、AKS、GKE、xKS など）」となっており、ECS（AWS 独自オーケストレータ、
    Kubernetes ではない）のサポート可否が公開情報からは判断できません。
    Red Hat の公式見解をご確認いただけますでしょうか。

Q2. AWS EKS / EKS Fargate 上での RHBK サポート範囲
    KB 7072950 の Resolution 本文が subscriber 限定で確認できません。
    EKS / EKS Fargate での具体的なサポート条件、必要サブスクリプション、
    制約事項についてご教示ください。

Q7. 以下の構成での正式見積
    - 製品: Red Hat Runtimes（または Red Hat Application Foundations）
    - コア構成: 4-core、8-core、16-core の各バンド
    - サポートティア: Standard、Premium
    - 期間: 1 年、3 年
    - 利用環境: 本番 + Hot Standby DR
    - 補足: vCPU は 2:1 換算で問題なければ Fargate 4 vCPU × 2 タスク
            （= 4 cores）+ DR 同等で 8-core が想定です

[High 項目]

Q3. RHBK 26.4.x で Aurora PostgreSQL 17.x が正式サポート対象になる時期
Q4. Multi-Site HA における Aurora PostgreSQL 必須の根拠と
    RDS PostgreSQL での代替可否
Q5. 本番ワークロードのコア計算ルール（Fargate vCPU の換算、
    HPA 時の最大値ベースか平均ベースか）

[Medium 項目]

Q6. Hot DR と Warm DR の境界定義
    （フェイルオーバ時間、自動切替の有無）
Q8. Red Hat Runtimes と Application Foundations の新規購入時の差と
    将来の移行パス
Q9. RHBK 26.0.x の Maintenance フェーズ終了時期と
    26.4.x への upgrade パス・推奨タイミング

[Low 項目]

Q10. OpenJDK / Quarkus のサブスクリプション要件
     （RHBK 同梱で十分か、追加サブスクが必要か）

■ 希望スケジュール
- 初回回答: 2 週間以内
- 正式見積: 1 ヶ月以内
- 本番採用判断: 2026 年 Q3 までに完了予定

■ 回答形式
書面（PDF または社印付き Word）でいただけると社内稟議に添付できて
助かります。可能な範囲で構いません。

ご多忙のところ恐縮ですが、ご検討のほどよろしくお願い申し上げます。

──────────────────────
【会社名】
【部署】
【氏名】
【メール】
【電話】
──────────────────────
```

---

## 4. メール文面（英語版・Red Hat 直接 / Global Support 宛）

> 用途: Red Hat 営業に直接英語で照会する場合、または KB 7072950 の本文確認のために Red Hat Customer Portal Support Case を起票する場合

```
Subject: [Pre-sales inquiry] RHBK production adoption — support scope on AWS ECS / EKS, and pricing for 4-16 core deployments

Dear Red Hat Team,

I am writing on behalf of [Company Name] regarding the production adoption of
Red Hat build of Keycloak (RHBK).

# Background

We have completed a PoC of an AWS-based shared authentication platform using
upstream Keycloak 26.0.8 on AWS ECS Fargate with Amazon RDS for PostgreSQL 16.
We are now evaluating RHBK for production to obtain commercial support.

# Target architecture (under evaluation)

- RHBK version: 26.4.x (or 26.0.x)
- Runtime platform candidates (we are comparing):
    A. AWS ECS Fargate (our current PoC topology)
    B. AWS EKS / EKS Fargate
    C. ROSA (Red Hat OpenShift Service on AWS)
    D. Amazon EC2 with RHEL 9
- Database: Amazon RDS for PostgreSQL 16.x (or Aurora PostgreSQL)
- HA: Multi-AZ in primary region + Hot DR in secondary region
- Primary region: ap-northeast-1 (Tokyo); DR: ap-northeast-3 (Osaka)

# Questions we need to confirm before final decision

[Critical]

Q1. Is RHBK supported in production on **AWS ECS Fargate**?
    KB 7072950 is titled "Red Hat build of Keycloak Support on 3rd-party
    Kubernetes Environments (EKS, AKS, GKE, xKS)". Since AWS ECS is not
    a Kubernetes platform, it is unclear from the public summary whether
    ECS Fargate is in scope.

Q2. What is the exact support scope and subscription requirement for
    RHBK on **AWS EKS / EKS Fargate**?
    The Resolution body of KB 7072950 / 7044045 is subscriber-only.
    We would appreciate access to the full text or a written summary.

Q7. **Formal quote** for the following configurations:
    - Product: Red Hat Runtimes (or Red Hat Application Foundations)
    - Core bands: 4-core, 8-core, 16-core
    - Support tiers: Standard and Premium
    - Term: 1 year and 3 years
    - Topology: Production + Hot Standby DR
    - Sizing assumption: 4 vCPU x 2 tasks per environment (= 4 cores
      using the 2:1 vCPU-to-core ratio), with Hot DR doubling that.

[High]

Q3. When will Aurora PostgreSQL 17.x be officially listed as a
    supported database for RHBK 26.4.x?

Q4. The High Availability Guide states Aurora PostgreSQL is required
    for Multi-Site HA. Could you share the technical rationale, and
    whether RDS for PostgreSQL is acceptable for active/passive HA?

Q5. How is **core counting** computed for autoscaled workloads on
    Fargate? Is the 2 vCPU = 1 core ratio still applicable, and does
    HPA-based scaling count peak or average?

[Medium]

Q6. Could you clarify the boundary between Hot DR and Warm DR?
    (Failover time, automatic vs manual switchover.)

Q8. Differences between Red Hat Runtimes and Red Hat Application
    Foundations for new purchases, and the migration path.

Q9. End-of-maintenance schedule for RHBK 26.0.x, and the recommended
    upgrade path / timing for migrating to 26.4.x.

[Low]

Q10. Subscription requirements for OpenJDK and Quarkus when used as
     part of an RHBK deployment. Are they fully covered by the
     RHBK-bundled JVM, or do they require separate entitlements?

# Deliverables we are looking for

- Written response to Q1-Q10 (email or formal answer)
- Formal quote (PDF / signed) to support our internal procurement process
- Resolution body of KB 7072950 / 7044045

# Timeline

- Initial response: within 2 weeks if possible
- Formal quote: within 1 month
- Final platform decision: by end of Q3 2026

Thank you very much for your time. We look forward to your response.

Best regards,
[Name]
[Title / Department]
[Company]
[Email] [Phone]
```

---

## 5. リセラ別の補足情報

公開情報ベースの推測を含む。実際の取引方針は各社に確認のこと。

### 5.1 SB C&S 株式会社

- **特徴**: ソフトバンクグループの IT ディストリビュータ。Red Hat 製品の国内最大手の一角
- **強み**: 大規模顧客への営業ネットワーク、製品セミナー / トレーニング充実
- **想定窓口**: 法人営業 → Red Hat 担当 SE
- **問い合わせ方法**: 公式 Web サイトの問い合わせフォーム、または既存営業担当経由

### 5.2 日商エレクトロニクス

- **特徴**: 双日グループの SI 系商社。エンタープライズ向け
- **強み**: 金融・官公庁系の取引実績、構築サービスとの組み合わせ提案
- **想定窓口**: 営業部 → Red Hat ソリューション部門
- **特記**: 構築サービスとセットでの提案を期待される場合あり

### 5.3 TIS / インテックグループ

- **特徴**: SI 大手。Red Hat ビジネスパートナー
- **強み**: OSS / クラウド構築の実績、AWS との連携
- **想定窓口**: 営業 → クラウドソリューション部門
- **特記**: 自社 SI を含めた提案になる傾向

### 5.4 Red Hat 直接

- **対象**: 大規模案件（年間数千万円以上想定の場合）
- **方法**: [redhat.com/ja/contact](https://www.redhat.com/ja/contact) → 営業問い合わせ
- **長所**: 公式見解が直接取れる、エンジニアリング部門にエスカレーション可能
- **短所**: 中小規模案件はリセラに振られることが多い

### 5.5 推奨アプローチ

```
Step 1: 既存取引のあるリセラ（SB C&S 等）に §3.1 簡略版で打診
   ↓ 1-2 週間で見積と一次回答
Step 2: 並行で Red Hat に §4 英語版で直接問い合わせ
   ↓ 公式見解の取得（特に Q1 / Q2）
Step 3: 見積比較・公式回答との突き合わせ
   ↓ 必要なら追加照会
Step 4: platform-selection-decision.md のスコアリング更新
```

---

## 6. 回答受領後のチェックリスト

各社からの回答を受け取ったら、以下を [platform-selection-decision.md](platform-selection-decision.md) のスコアリングに反映する。

- [ ] Q1 回答受領: ECS Fargate の商用サポート可否が確定したか
- [ ] Q2 回答受領: EKS / EKS Fargate のサポート条件が明確化したか
- [ ] Q7 回答受領: 構成別の正式見積が揃ったか（最低 2 社からの相見積）
- [ ] 見積比較: 最安値と最高値の差を把握したか
- [ ] SLA 確認: Standard / Premium の応答時間 / 解決時間目標を取得したか
- [ ] 契約条件: 多年契約割引（20-40% 想定）の実額を確認したか
- [ ] エスカレーション経路: 障害時の連絡先・ハンドオフが明確か
- [ ] 国内法人格: 契約主体が日本法人（Red Hat 株式会社）か海外法人かを確認したか
- [ ] 為替リスク: 多年契約の場合の為替条項を確認したか

---

## 7. 関連ドキュメント

- [doc/reference/rhbk-support-and-pricing.md](../reference/rhbk-support-and-pricing.md) — 確認事項の根拠（事実マトリクス）
- [doc/reference/keycloak-upstream-vs-rhbk.md](../reference/keycloak-upstream-vs-rhbk.md) — RHBK 採用判断のフレーム
- [doc/adr/015-rhbk-validation-deferred.md](../adr/015-rhbk-validation-deferred.md) — PoC で RHBK 検証を実施しない判断
- [platform-selection-decision.md](platform-selection-decision.md) — プラットフォーム選定判断書（回答を反映する先）

---

## 8. 変更履歴

| 日付 | 内容 |
|---|---|
| 2026-05-08 | 初版（Q1-Q10 を rhbk-support-and-pricing.md §8 から展開、日本語簡略 / フル版・英語版・リセラ別補足を追加） |
