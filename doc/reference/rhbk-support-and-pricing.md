# Red Hat build of Keycloak（RHBK）サポート対象範囲と価格

**作成日**: 2026-05-08
**目的**: 本番採用時に RHBK の商用サポートを受けるための要件と、現 PoC 構成との差分・価格構造の整理
**位置づけ**: 本ドキュメントは事実整理。判断は [requirements/platform-selection-decision.md](../requirements/platform-selection-decision.md)（未作成）で行う

---

## 0. TL;DR

- RHBK は **単体販売されない**。Red Hat Runtimes / Application Foundations / OCP のいずれかに包含
- 課金は **2-core / 4-core バンド単位**（vCPU は 2:1 でコア換算）
- **現 PoC の Keycloak 26.0.8 / RDS PostgreSQL 16.13 自体は RHBK サポート対象範囲内**
- ただし以下が要対応:
  - `start-dev` モード → `start --optimized` 必須
  - HTTP のみ → HTTPS 必須
  - OSS image → `registry.redhat.io/rhbk/keycloak-rhel9` への置換
- **ECS Fargate での稼働可否は公開情報からは確定不可**（subscriber 限定 KB の本文確認 or Red Hat 直接照会が必要）
- 公式の本番想定基盤は OpenShift（ROSA 含む）/ RHEL VM / EKS など Kubernetes プラットフォーム

---

## 1. RHBK とは

OSS Keycloak を Red Hat が商用パッケージとして配布・サポートしたもの。アップストリームの Keycloak と機能的にはほぼ同一だが、以下が付加される:

| 付加要素 | 内容 |
|---|---|
| ハードニング | RHEL ベースイメージ + UBI |
| サポート | 24x7 / Standard / Premium |
| ライフサイクル | メジャー 2〜3 年（後述） |
| CVE 対応 | バックポート提供 |
| 認定構成 | OS / DB / JVM / Container Platform マトリクス |

---

## 2. ライフサイクル

出典: [Life Cycle and Support Policies](https://access.redhat.com/support/policy/updates/red_hat_build_of_keycloak_notes)

- 約 6 か月ごとに偶数バージョンでマイナーリリース（26.0 → 26.2 → 26.4 …）
- 各マイナーは約 12 か月のメンテナンス
- **26.x は最低 2 年間、27.x 以降は 3 年間** のメジャーサポート
- 2 フェーズ:
  - **Full Support**: 次メジャーまで（パッチ・新機能・認定）
  - **Maintenance**: メジャーリリース後最低 6 か月（critical CVE / mission-critical bug のみ）

### サポート対象 RHBK 一覧（2026-05 時点）
| RHBK | 状態 |
|---|---|
| 26.4.x | Full Support（最新） |
| 26.2.x | Full / Maintenance 移行期 |
| **26.0.x** | Maintenance フェーズ寄り（PoC が使用） |
| 24.0.x | Maintenance |
| 22.0.x | Maintenance |

→ 本番採用するなら **26.4.x への更新を推奨**

---

## 3. サポート対象構成マトリクス

出典: [Red Hat build of Keycloak Supported Configurations (KB 7033107)](https://access.redhat.com/articles/7033107)

### 3.1 OS / プラットフォーム

| RHBK | OpenShift | RHEL | Windows Server | アーキ |
|---|---|---|---|---|
| 26.4.x | 4.20 / 4.19 / 4.18 / 4.17 / 4.16 / 4.14 | 9, 8 | 2022, 2019 | x86_64 / s390x / ppc64le / Aarch64 |
| 26.2.x | 4.19〜4.12 | 9, 8 | 2022, 2019 | 同上 |
| 26.0.x | 4.19〜4.12 | 9, 8 | 2022, 2019 | x86_64 / s390x / ppc64le |
| 24.0.x | 4.18〜4.12 | 9, 8 | 2022, 2019 | x86_64 系 |
| 22.0.x | 4.17〜4.12 | 9, 8 | 2022, 2019 | x86_64 系 |

> マネージド OpenShift（**ROSA / ARO / OSD / OKE**）も同等扱い。

### 3.2 Database

RHBK 26.0.x の場合:

| DB | テスト済バージョン | サポートバージョン |
|---|---|---|
| **PostgreSQL** | 16.8 | **16.x / 15.x / 14.x / 13.x** ← PoC 16.13 はここに該当 |
| **Aurora PostgreSQL** | 16.1 | 16.x / 15.x（Multi-Site HA で必須） |
| MySQL | 8.0.41 | 8.0 / 8.4 LTS |
| Oracle | 19c | 19c |
| SQL Server | 2022 | 2022 / 2019 |
| MariaDB | 10.11 | 10.11 / 10.6 LTS |

RHBK 26.4.x では **PostgreSQL 17.x** までサポート対象を拡大、Aurora PostgreSQL も AWS JDBC Wrapper 経由で全 RHBK 26.x で利用可能。

### 3.3 JVM

| RHBK | JVM |
|---|---|
| 26.4.x / 26.2.x / 26.0.x | Red Hat OpenJDK 21 / 17、Eclipse Temurin 21 / 17 |
| 24.0.x / 22.0.x | OpenJDK 17、Temurin 17 |

> コンテナ image 利用時は image に同梱（ubi9/openjdk-17）

### 3.4 コンテナイメージ

| 項目 | 値 |
|---|---|
| イメージ | `registry.redhat.io/rhbk/keycloak-rhel9:<version>` |
| ベース | UBI 9 Micro |
| アーキ | **amd64 のみ**（rhbk-rhel9 イメージ） |
| 認証 | registry.redhat.io への Red Hat ログイン or Service Account Token が必要 |
| 公開ポート | 8080/tcp, 8443/tcp, 9000/tcp |
| 実行ユーザ | UID 1000（非特権） |

出典: [Red Hat Ecosystem Catalog](https://catalog.redhat.com/en/software/containers/rhbk/keycloak-rhel9/64f0add883a29ec473d40906)

---

## 4. コンテナ実行基盤のサポート方針

### 4.1 公式マトリクスに明示されている基盤

| 基盤 | サポート | 出典 |
|---|:---:|---|
| **OpenShift Container Platform 4.x** | ✅ 一級サポート | KB 7033107 |
| **OpenShift マネージド（ROSA / ARO / OSD / OKE）** | ✅ 同上 | 同上 |
| **RHEL 9 / RHEL 8 上の VM / コンテナ** | ✅ サポート | 同上 |
| Windows Server 2022 / 2019 | ✅ サポート | 同上 |

> 補足: 「**RHEL 以外の Linux ディストリは認定・サポート対象外**」と明記されている（KB 7033107）

### 4.2 3rd-party Kubernetes（EKS / AKS / GKE）

別 KB に切り分け:
- 旧版: [KB 7044045](https://access.redhat.com/solutions/7044045)
- 新版: [**KB 7072950**](https://access.redhat.com/ja/solutions/7072950)（日本語版）

**KB 7072950 の公開部分**（subscriber でなくても見える範囲）:

- 表題: **「サードパーティーの Kubernetes 環境（EKS、AKS、GKE、xKS など）での Red Hat build of Keycloak のサポート」**
- Issue:
  - 「サードパーティーの Kubernetes 環境（EKS、AKS、GKE など）で使用する場合にサポートされますか?」
  - 「Red Hat OpenShift 以外の Kubernetes プラットフォームで使用するには、どのサブスクリプションが必要ですか?」
- Environment: **AWS EKS / AWS Fargate / Azure AKS / Google GKE / その他の xKS**
- Resolution: **subscriber 限定で本文非公開**

### 4.3 「AWS Fargate」の解釈

KB 7072950 の Environment 欄に "AWS Fargate" が登場するが、文脈と表題から **EKS Fargate（= Kubernetes 上の Fargate）** を指していると読むのが自然。

| サービス | Kubernetes か | KB 7072950 の対象か |
|---|:---:|---|
| **AWS ECS（EC2 / Fargate）** | ❌ AWS 独自オーケストレータ。Kubernetes ではない | **対象外と読むのが妥当**（表題が「Kubernetes 環境」のため） |
| **AWS EKS（EC2 / Fargate）** | ✅ マネージド Kubernetes | 対象 |
| OpenShift / ROSA | ✅ Kubernetes ベース | KB 7033107 で別途一級サポート |

### 4.4 「OpenShift 限定」と読める記述の正確なスコープ

[Keycloak 公式 docs リポジトリの containers.adoc L14-L18](https://github.com/keycloak/keycloak/blob/main/docs/guides/server/containers.adoc#L14-L18) に以下:

```
<@profile.ifProduct>

WARNING: This chapter applies only for building an image that you run
in a OpenShift environment. Only an OpenShift environment is supported
for this image. It is not supported if you run it in other Kubernetes
distributions.

</@profile.ifProduct>
```

`<@profile.ifProduct>` ブロックは RHBK ドキュメントでのみ表示される。レンダリング先:
- [RHBK 26.0 / Server Configuration Guide / Chapter 5](https://docs.redhat.com/en/documentation/red_hat_build_of_keycloak/26.0/html/server_configuration_guide/containers-)
- [RHBK 26.4 / 同 Chapter 5](https://docs.redhat.com/en/documentation/red_hat_build_of_keycloak/26.4/html/server_configuration_guide/containers-)

**重要**: WARNING の主語は **"this chapter" / "this image"** = **その章の Containerfile/Dockerfile 手順で作成したカスタムイメージ**。「RHBK 全体が OpenShift 限定」を意味するものではない。同章 L172 には Podman について次の記述もある:

> "Podman can be used only for creating or customizing images. **Podman is not supported for running Keycloak in production environments.**"

→ ビルド・カスタマイズ用途と本番ランタイムを区別している。

### 4.5 ECS / ECS Fargate のサポート可否（**確定不可領域**）

| 観点 | 状況 |
|---|---|
| KB 7033107（Supported Configurations） | OpenShift / RHEL / 3rd-party K8s（KB 別記）のみ列挙。**ECS の記述なし** |
| KB 7072950（3rd-party Kubernetes） | 表題が「**Kubernetes 環境**」。ECS は本来対象外と読める。**Resolution 本文 subscriber 限定で確認不可** |
| Server Configuration Guide | カスタムイメージは "OpenShift only"（章スコープ限定）。ECS への言及なし |
| Server Configuration Guide（一般のコンテナ運用） | Docker / Podman でのコンテナ稼働手順は記述あり。**ECS への明示の制約はなし** |

→ **公開情報の範囲では「ECS で稼働させた RHBK が商用サポート対象になるか」を断定する根拠は得られなかった**。

決定的な確認には以下のいずれかが必要:
1. Red Hat アカウントで KB 7072950 / 7044045 の Resolution 本文を読む
2. Red Hat 営業 / サポートに書面で問い合わせ
3. 認定リセラ（CDW、Insight、SB C&S 等）経由で公式回答を取得

---

## 5. サブスクリプションの構造

出典: [Subscriptions or Entitlements Requirements (KB 7044244)](https://access.redhat.com/articles/7044244) / [Application Services Subscription Guide](https://www.redhat.com/en/resources/application-services-subscription-guide-detail)

### 5.1 単体販売は不可

> "Red Hat build of Keycloak is not available for purchase as a separate and distinct product outside of the bundles in which it is included."

### 5.2 含まれるバンドル

| バンドル | RHBK 含有 | 本番採用候補 | 想定ユース |
|---|:---:|:---:|---|
| **Red Hat Runtimes** | ✅ | ◎ | ミドルウェアスタック中心。Keycloak のみが目的なら最有力 |
| **Red Hat Application Foundations** | ✅ | ○ | Runtimes の後継ブランド。新規購入はこちら |
| **Red Hat OpenShift Container Platform** | ✅ | △ | OpenShift を入れるなら自動で含まれる |
| **ROSA / ARO / OSD**（マネージド OCP） | ✅ | ○ | OCP サブスク扱い。クラウド従量課金 |
| Red Hat Integration | ✅ | × | 更新のみ（新規購入不可） |
| JBoss EAP | ✅ | × | 更新のみ |

### 5.3 課金モデル

- **2-core / 4-core バンド単位**（コアベース）
- vCPU は 2:1 でコア換算が基本（Red Hat 標準ルール）
- **本番 / QA / Staging はカウント対象**
- **単一開発者の dev はカウント不要**
- **Hot DR はカウント対象**、Warm / Cold DR は対象外
- **RHBK 使用コアは Runtimes / OCP のサブスク総コアにカウントされる**

### 5.4 公開価格レンジ（参考値）

公式リスト価格は契約規模・多年契約割引で大きく変動するため、**正式見積は Red Hat / 認定リセラに直接取得**が原則。以下は公開リセラサイトと集計サイトからの参考レンジ:

| 製品 | ティア | 参考価格レンジ | 出典 |
|---|---|---|---|
| Red Hat Runtimes（=RHBK 含む） | Standard 64C / 128vCPU 1年 | 要見積もり、リセラ表示あり | [CDW MW00279](https://www.cdw.com/product/red-hat-runtimes-standard-64-cores-128-vcpus/6905384) |
| Red Hat Runtimes | Premium 2C / 4vCPU 1年 | 要見積もり | [CDW MW00277](https://www.cdw.com/product/red-hat-runtimes-premium-subscription-1-year-2-cores-4-vcpus/6905380) |
| OCP（参考） | 2-core pack | **$1,000〜$2,500 / 2-core / 年**（≈ $500〜$1,250 / コア / 年） | [TrustRadius / Vendr 集計](https://www.trustradius.com/products/openshift/pricing) |
| ROSA（マネージド OCP on AWS） | Reserved 4vCPU 3y | **$0.076/hour 〜** | [AWS ROSA Pricing](https://aws.amazon.com/rosa/pricing/) |

> 大規模・多年契約では **20-40%** 程度の割引が一般的（複数集計サイトの記載）。

### 5.5 PoC 規模での試算例

仮定: 本番 Fargate タスク 2 vCPU × 2 タスク（HA）= 4 vCPU + Hot Standby（DR）4 vCPU

```
本番側     : 4 vCPU ÷ 2 = 2 cores
Hot DR 側  : 4 vCPU ÷ 2 = 2 cores
─────────────────────────────────
合計       : 4 cores → 4-core バンド 1 つ
```

> Red Hat Runtimes Standard / Premium 4-core バンドの正式価格は要見積もり。3 年契約で割引適用の試算が現実的。

---

## 6. 現 PoC 構成と RHBK サポートの差分マトリクス

| 項目 | PoC 現状 | RHBK サポート対象か | 必須対応 |
|---|---|:---:|---|
| **Keycloak バージョン** | OSS 26.0.8 | ✅ 対象（26.0.x z-stream） | 26.4.x への更新を推奨 |
| **コンテナイメージ** | OSS Quarkus image | ❌ | `registry.redhat.io/rhbk/keycloak-rhel9` へ置換 |
| **実行基盤** | **AWS ECS Fargate** | ❓ **公開情報で確定不可** | Red Hat へ確認 / EKS or ROSA への移行検討 |
| **DB** | RDS PostgreSQL 16.13 | ✅ | 維持 OK |
| **HA / DR** | 単一 AZ + DR は手動 | — | Hot DR ならコアカウント対象、Aurora PG が Multi-Site HA 必須（26.x） |
| **起動モード** | **start-dev**（[ADR-008](../adr/008-keycloak-start-dev-for-poc.md)） | ❌ | **`start --optimized` 化必須**。本番 start-dev は明示的禁止 |
| **HTTPS** | HTTP のみ | ❌ | ALB に ACM 証明書、KC_HOSTNAME 設定（PoC 既知課題 N1） |
| **アーキテクチャ** | x86_64 想定 | ✅ | rhbk-rhel9 image は amd64 のみ |
| **JVM** | コンテナ同梱 | ✅ | OpenJDK 21 / 17 |
| **JWKS / Network** | Public ALB + Internal ALB（[ADR-012](../adr/012-vpc-lambda-authorizer-internal-jwks.md)） | — | 構成は流用可。Split-horizon DNS は本番要件（[ADR-011](../adr/011-auth-frontend-network-design.md)） |

---

## 7. 本番採用時の実行基盤候補

サポート観点・既存設計との整合性で比較。

| 候補 | サポート | コスト | 既存設計との整合 | 学習コスト | 総合 |
|---|:---:|---|---|:---:|:---:|
| **A. ROSA**（マネージド OpenShift on AWS） | ◎ 一級サポート | RHBK は OCP に包含・別途課金不要。ROSA 固定費発生 | VPC / RDS / ALB は流用可。Operator デプロイで楽 | △ OpenShift 学習必要 | ◎ |
| **B. EKS（Fargate / EC2）** | ○ KB 7072950 の対象（subscriber 確認要） | RHBK サブスク（Runtimes）+ EKS 課金 | ECS → EKS 移行コスト中〜大。Operator 利用可 | ○ K8s 知識前提 | ○ |
| **C. EC2 RHEL 9** | ◎ RHEL は一級サポート | RHEL サブスク + RHBK サブスク | ECS の Fargate 利点を失う。Auto Scaling 自前 | ○ EC2 + RHEL は標準 | ○ |
| **D. ECS Fargate を維持** | ❓ 公開情報で確定不可 | 最小（既存維持） | ◎ 完全維持 | ◎ 変更なし | △ |

### A. ROSA（推奨パスのひとつ）
- **メリット**: OpenShift = RHBK の一級サポート対象。Operator で運用が標準化。RHBK 包含サブスク
- **デメリット**: ROSA の固定費（Control Plane）。OpenShift 学習コスト
- **ECS → ROSA 移行**: VPC / RDS / Aurora は流用可。コンテナ部分は Deployment / Operator に書き換え

### B. EKS / EKS Fargate
- **メリット**: AWS 寄りの運用ノウハウが活きる。サブスクは Runtimes で済む
- **デメリット**: KB 7072950 で対象だが Resolution 本文未確認のため**正式照会推奨**
- **ECS → EKS 移行**: タスク定義 → Pod / Deployment への書き換えが大きい

### C. EC2 RHEL
- **メリット**: 最もシンプルにサポート対象に入る
- **デメリット**: ECS / Fargate のマネージド利点を失う。AMI 管理 / パッチ / Auto Scaling 自前
- **ECS → EC2 移行**: 構成は退化方向。本番運用負荷が増える

### D. ECS Fargate 維持
- **メリット**: 既存設計をそのまま流用、最小工数
- **デメリット**: **RHBK 商用サポートの対象になるか公開情報では確定不可**。サポート目的の RHBK 採用と齟齬リスク
- **対応**: Red Hat 直接照会で確認すれば判断可能

---

## 8. Red Hat への確認事項リスト（要件定義フェーズで実施）

subscriber 限定 KB の本文確認 / 営業窓口への照会で確定すべき項目。

| # | 確認事項 | 確認方法 | 優先度 |
|---|---|---|:---:|
| Q1 | **AWS ECS Fargate 上の RHBK は商用サポート対象か** | KB 7072950 本文 / Red Hat 営業に書面照会 | **Critical** |
| Q2 | EKS Fargate での RHBK サポート範囲（KB 7072950 Resolution 本文） | subscriber アカウントで閲覧 / リセラ経由 | **Critical** |
| Q3 | RHBK 26.4.x 採用時の Aurora PostgreSQL のバージョン要件（17.x の正式対応時期） | Red Hat 営業 | High |
| Q4 | Multi-Site HA で **Aurora PostgreSQL 必須** の根拠と RDS PostgreSQL での代替可否 | Red Hat 営業 / サポート | High |
| Q5 | 本番ワークロードのコア計算ルール（Fargate vCPU の換算、HPA 時の最大値ベース or 平均ベース） | リセラ / Red Hat 営業 | High |
| Q6 | Hot DR / Warm DR の境界定義（フェイルオーバ時間、自動切替の有無） | KB 確認 | Medium |
| Q7 | 認定リセラ（日本国内: SB C&S / 日商エレ等）からの **正式見積もり** | リセラ営業 | **Critical** |
| Q8 | Red Hat Runtimes と Application Foundations の **新規購入時の差** と将来の移行 | Red Hat 営業 | Medium |
| Q9 | RHBK 26.0.x の Maintenance フェーズ終了時期と 26.4.x への upgrade パス | KB 確認 | Medium |
| Q10 | OpenJDK / Quarkus のサブスクリプション要件（RHBK 同梱で十分か） | KB 7044244 本文確認 | Low |

---

## 9. 要件定義書での扱い

本ドキュメントの結論を [requirements/platform-selection-decision.md](../requirements/platform-selection-decision.md)（未作成）の評価項目に組み込む:

- 「商用サポートを必須要件にするか」を **必須 / 推奨 / 不要** で確定
- 必須にする場合は Q1 / Q2 / Q7 を解消してから Cognito / Keycloak / RHBK の比較スコアリング実施
- 必須にしない場合は OSS Keycloak + サードパーティ MSP（GuardSquare / Inteca 等）も比較対象に追加

---

## 10. 出典

- [Red Hat build of Keycloak Supported Configurations (KB 7033107)](https://access.redhat.com/articles/7033107)
- [Subscriptions or Entitlements Requirements for RHBK (KB 7044244)](https://access.redhat.com/articles/7044244)
- [RHBK Support on 3rd-party Kubernetes Environments (KB 7072950, 日本語)](https://access.redhat.com/ja/solutions/7072950)
- [RHBK Support on 3rd-party Kubernetes Environments (KB 7044045, 旧)](https://access.redhat.com/solutions/7044045)
- [RHBK Life Cycle and Support Policies](https://access.redhat.com/support/policy/updates/red_hat_build_of_keycloak_notes)
- [RHBK 26.0 Server Configuration Guide / Containers Chapter](https://docs.redhat.com/en/documentation/red_hat_build_of_keycloak/26.0/html/server_configuration_guide/containers-)
- [RHBK 26.4 Server Configuration Guide / Containers Chapter](https://docs.redhat.com/en/documentation/red_hat_build_of_keycloak/26.4/html/server_configuration_guide/containers-)
- [Keycloak 公式 docs ソース: containers.adoc (GitHub)](https://github.com/keycloak/keycloak/blob/main/docs/guides/server/containers.adoc)
- [RHBK Container Image (Red Hat Ecosystem Catalog)](https://catalog.redhat.com/en/software/containers/rhbk/keycloak-rhel9/64f0add883a29ec473d40906)
- [Red Hat Application Services Subscription Guide](https://www.redhat.com/en/resources/application-services-subscription-guide-detail)
- [Red Hat OpenShift Pricing](https://www.redhat.com/en/technologies/cloud-computing/openshift/pricing)
- [AWS ROSA Pricing](https://aws.amazon.com/rosa/pricing/)
- [TrustRadius: OpenShift Pricing 2026](https://www.trustradius.com/products/openshift/pricing)

---

## 11. 関連ドキュメント

本ドキュメントは「**事実マトリクス**」に特化している。判断・選定の文脈は以下と組み合わせて参照する。

| ドキュメント | 役割 | 補完関係 |
|---|---|---|
| [keycloak-upstream-vs-rhbk.md](keycloak-upstream-vs-rhbk.md) | Upstream（OSS 版）と RHBK の **比較・切り替え難易度・本番判断フレーム** | 本ドキュメント（事実）→ あちら（判断観点） |
| [ADR-015: RHBK 検証を本番設計フェーズへ先送り](../adr/015-rhbk-validation-deferred.md) | PoC では RHBK 検証を実施しない判断とその根拠 | 本ドキュメントは「先送り後の本番判断材料」として位置づけ |
| [ADR-006: Cognito vs Keycloak コスト損益分岐](../adr/006-cognito-vs-keycloak-cost-breakeven.md) | コスト損益分岐 MAU の試算 | 本ドキュメントの §5.4 / §5.5 価格レンジを反映して再試算 |
| [ADR-008: PoC で start-dev モードを使用](../adr/008-keycloak-start-dev-for-poc.md) | PoC の起動モード判断 | 本ドキュメント §6 で「本番は `start --optimized` 必須」として再掲 |
| [keycloak-network-architecture.md](../common/keycloak-network-architecture.md) | ネットワーク構成と本番要件 | 本ドキュメント §6 の HTTPS / Hostname 必須化と整合 |
| [requirements/platform-selection-decision.md](../requirements/platform-selection-decision.md) | プラットフォーム選定判断書（評価基準 / スコアリング） | 本ドキュメントの §7 候補比較を評価基準に反映 |
| [requirements/rhbk-vendor-inquiry.md](../requirements/rhbk-vendor-inquiry.md) | Red Hat / 認定リセラへの問い合わせ文面 | 本ドキュメント §8 の Q1〜Q10 を実際の照会文に展開 |

### 読む順序の推奨

1. **「RHBK ってそもそも何？OSS 版とどう違う？」** → [keycloak-upstream-vs-rhbk.md](keycloak-upstream-vs-rhbk.md)
2. **「本番採用時のサポート対象は？価格は？」** → 本ドキュメント
3. **「PoC で検証しなかった理由は？」** → [ADR-015](../adr/015-rhbk-validation-deferred.md)
4. **「で、選定判断はどうする？」** → [platform-selection-decision.md](../requirements/platform-selection-decision.md)
5. **「Red Hat に何を聞けばよい？」** → [rhbk-vendor-inquiry.md](../requirements/rhbk-vendor-inquiry.md)

---

## 12. 変更履歴

| 日付 | 内容 |
|---|---|
| 2026-05-08 | 初版（本番採用時の RHBK サポート範囲調査・PoC 構成との差分・価格レンジ整理） |
| 2026-05-08 | §11 関連ドキュメント追加（keycloak-upstream-vs-rhbk.md / ADR-015 / platform-selection-decision.md / rhbk-vendor-inquiry.md との相互参照） |
