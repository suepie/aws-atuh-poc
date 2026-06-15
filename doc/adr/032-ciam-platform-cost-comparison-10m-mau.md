# ADR-032: 10M MAU 規模における CIAM プラットフォーム選定 — Keycloak / Cognito / Entra External ID / Auth0/Okta コスト比較

- **ステータス**: Proposed（要件定義フェーズで Accepted に昇格予定）
- **日付**: 2026-06-12
- **関連**:
  - [ADR-006: Cognito vs Keycloak コスト損益分岐点の分析](006-cognito-vs-keycloak-cost-breakeven.md) — 損益分岐点 17.5 万 MAU の前提を継承し、10M MAU 規模に拡張
  - [ADR-016: Cognito 機能ティア（Lite / Essentials / Plus）の機能マトリクスと選定基準](016-cognito-feature-tier-selection.md)
  - [ADR-017: マルチテナント L2（単一 Pool/Realm + 複数 IdP）採用根拠](017-multitenant-l2-single-realm.md)
  - [ADR-019: 既存システムからの移行戦略](019-existing-system-migration.md)
  - [ADR-028: IdP なし顧客のローカルユーザー管理](028-idpless-customer-local-user-management.md)
  - [ADR-029: ローカルユーザーの定義 — 利用者カテゴリと範囲シナリオ](029-local-user-categories-and-scope-scenarios.md)
  - [ADR-030: 最小 JWT クレーム設計と接続元アプリ表現](030-minimal-jwt-claim-design.md)

---

## Context

[ADR-006](006-cognito-vs-keycloak-cost-breakeven.md) で Cognito vs Keycloak の損益分岐点（**17.5 万 MAU**）を整理したが、本要件で想定される **10M MAU（1,000 万）規模** + **ローカルユーザ + IdP 自社運用** の前提下では、より広い選択肢で比較が必要となった。

具体的には、想定 IdP 候補を以下に拡張：

- **Amazon Cognito**（Lite / Essentials / Plus、AWS マネージド）
- **Microsoft Entra External ID**（旧 Azure AD B2C、Microsoft マネージド）
- **Auth0 / Okta Customer Identity Cloud**（Okta 傘下、SaaS）
- **Keycloak OSS**（自前ホスト、OSS）
- **Red Hat build of Keycloak (RHBK)**（Red Hat サポート付き）

### 重要な前提整理：Workforce IAM vs CIAM

各社製品は **「従業員向け（Workforce）」** と **「顧客向け（CIAM）」** で別ライセンス。10M ユーザは CIAM 想定であり、本 ADR は CIAM 向け製品ティアで比較する。

| ベンダー | Workforce 製品 | CIAM 製品（10M ユーザ用） |
|---|---|---|
| AWS | – | Cognito（Lite / Essentials / Plus） |
| Microsoft | Entra ID（旧 Azure AD）P1 / P2 | **Microsoft Entra External ID**（旧 Azure AD B2C）|
| Okta | Okta Workforce Identity Cloud | **Okta Customer Identity Cloud（= Auth0、2021 買収）** |
| Auth0 | – | **Auth0 B2C / B2B**（Okta 傘下）|
| Red Hat / Keycloak | Keycloak OSS / RHBK | Keycloak OSS / RHBK（同一製品） |

- Okta Workforce Identity は **10M B2C 用途では不適**（1 user $2-6/month で年 $20M〜）
- **Okta CIAM = Auth0** なので、両社は実質同一製品として扱う

---

## 1. Amazon Cognito — 公式単価 × 個数

### 公式ソース
- [Amazon Cognito - Pricing](https://aws.amazon.com/cognito/pricing/)

### 単価表（2026 年公式）

| Tier | 単価構造 | 無料枠 |
|---|---|---|
| **Lite** | **ボリュームディスカウント**（段階課金）| 10K MAU 無料 |
| **Essentials**（新規 Pool デフォルト）| **$0.015 / MAU**（フラット）| 10K MAU 無料 |
| **Plus** | **$0.020 / MAU**（フラット）| **無料枠なし** |

> ⚠ 2024-11-22 以前作成の Pool は **50K MAU 無料**（5 倍）。本試算は新規 Pool（10K 無料）前提。

### Lite ティアのボリュームディスカウント詳細

| 範囲 | 単価 |
|---|---:|
| 0 - 50,000 MAU | **無料** |
| 50,001 - 100,000 MAU | $0.0055 / MAU |
| 100,001 - 1,000,000 MAU | $0.0046 / MAU |
| 1,000,001 - 10,000,000 MAU | $0.00325 / MAU |
| 10,000,001 MAU 以上 | $0.0025 / MAU |

### 10M MAU での月額計算

#### Cognito Lite

| 範囲 | 個数 | 単価 | 小計 |
|---|---:|---:|---:|
| 0 - 50K（無料）| 50,000 | $0 | $0 |
| 50K - 100K | 50,000 | $0.0055 | $275 |
| 100K - 1M | 900,000 | $0.0046 | $4,140 |
| 1M - 10M | 9,000,000 | $0.00325 | $29,250 |
| **月額合計** | | | **$33,665** |
| **年額** | | | **$403,980** |

#### Cognito Essentials

| 計算 | 結果 |
|---|---:|
| (10,000,000 - 10,000) × $0.015 | **$149,850 / 月** |
| **年額** | **$1,798,200** |

#### Cognito Plus

| 計算 | 結果 |
|---|---:|
| 10,000,000 × $0.020（無料枠なし）| **$200,000 / 月** |
| **年額** | **$2,400,000** |

### ティア別機能差

| 機能 | Lite | Essentials | Plus |
|---|:---:|:---:|:---:|
| 基本ログイン / OIDC | ✅ | ✅ | ✅ |
| User Pool | ✅ | ✅ | ✅ |
| MFA | △（SMS のみ）| ✅（SMS / TOTP）| ✅（+ WebAuthn）|
| Managed Login（Hosted UI）| ❌ | ✅ | ✅ |
| Advanced Security Features（ATP、Risk-Based）| ❌ | ❌ | ✅ |
| M2M（Client Credentials）| ❌ | △ | ✅ |
| Custom attributes | 制限 | ✅ | ✅ |

→ **ローカルユーザを持つ + フル IdP 機能なら最低でも Essentials 必要、M2M / Partner B2B もあるなら Plus**。

---

## 2. Microsoft Entra External ID — 公式単価 × 個数

### 公式ソース
- [External ID Pricing - Microsoft Learn](https://learn.microsoft.com/en-us/entra/external-id/external-identities-pricing)
- [Microsoft Entra External ID—Pricing - Microsoft Security](https://www.microsoft.com/en-us/security/pricing/microsoft-entra-external-id)

### 単価表（2026 年公式）

| Tier | 単価 | 無料枠 |
|---|---:|---|
| **External ID Basic（Premium P1 統合）**| **$0.03 / MAU** | **50K MAU 無料** |

> ⚠ 2025-05 まで $0.01625 のディスカウント期間あり、現在は通常価格 $0.03 に戻る。

### 10M MAU での月額計算

| 計算 | 結果 |
|---|---:|
| (10,000,000 - 50,000) × $0.03 | **$298,500 / 月** |
| **年額** | **$3,582,000** |

### 追加コスト（要件次第）

| 機能 | 単価 |
|---|---|
| SMS phone authentication add-on | 国別 4 種のメーター課金 |
| Premium P2 機能（Risk Detection 等）| 別ライセンス、要見積もり |

---

## 3. Auth0 / Okta Customer Identity Cloud — 公式と業界実勢

### 公式ソース
- [Auth0 Pricing Changes for Customer Identity Cloud](https://auth0.com/blog/upcoming-pricing-changes-for-the-customer-identity-cloud/)
- 10M MAU 規模は **Enterprise（カスタム価格）**

### 単価表（2026 年）

| プラン | 単価 / 月額目安 |
|---|---|
| Free | 7,500 MAU まで |
| B2C Essentials | $35〜（500 MAU〜）|
| B2C Professional | $240〜（1,000 MAU〜）|
| **Enterprise**（10M MAU 用）| **カスタム交渉価格** |

### 10M MAU での実勢推定（複数の業界レポートより）

| シナリオ | 推定月額 | 年額 |
|---|---:|---:|
| Enterprise（標準機能）| $20,000 - 50,000 / 月 | $240,000 - 600,000 |
| Enterprise（Advanced Security、SLA 99.99%、PSO 含む）| $50,000 - 100,000 / 月 | **$600,000 - 1,200,000** |
| Private Cloud Deployment | $80,000 - 150,000 / 月 | $960,000 - 1,800,000 |

→ **正確な金額は Okta セールスチームに直接見積もり依頼必須**。

---

## 4. Keycloak 自前ホスト — AWS インフラ 単価 × 個数

### 公式ソース
- [Red Hat build of Keycloak 26.4 High Availability Guide](https://docs.redhat.com/en/documentation/red_hat_build_of_keycloak/26.4/pdf/high_availability_guide/Red_Hat_build_of_Keycloak-26.4-High_Availability_Guide-en-US.pdf)
- [Keycloak Performance Benchmarks (2025-10)](https://www.keycloak.org/2025/10/keycloak-benchmark)

### サイジング根拠（Red Hat 公式 + 10M MAU 想定）

| パラメータ | 値 | 根拠 |
|---|---|---|
| 想定 DAU（30% DAU/MAU）| 3M | B2C 業界標準 |
| 想定 認証ピーク TPS | 50 logins/sec | 業務時間ピーク係数 10x |
| 必要 vCPU（per pod 3 ノードクラスタ）| 50 / 8 ≈ 7 vCPU | RHBK HA Guide：**1 vCPU / 8 password logins/sec** |
| 必要メモリ（per pod）| 1250 MB + 500 MB × concurrent session/100K | RHBK HA Guide：base 1250 MB + 500 MB/100K セッション |
| 想定同時セッション | 200K | DAU の 7% 想定 |
| メモリ計算 | 1250 + 1000 = ~2.3 GB → 4 GB に切り上げ | 余裕込み |
| **構成** | **3 task × 4 vCPU + 8 GB RAM（HA / 3 AZ）**| HA 最小構成 |

### 各 AWS リソースの単価 × 個数（2026 公式価格）

#### ECS Fargate
- 公式：[AWS Fargate Pricing](https://aws.amazon.com/fargate/pricing/)

| 項目 | 単価 | 個数 | 月額計算 | 月額 |
|---|---:|---:|---|---:|
| vCPU | $0.04048 / vCPU-hr | 3 task × 4 vCPU × 730 hr | $0.04048 × 3 × 4 × 730 | **$354.61** |
| Memory | $0.004445 / GB-hr | 3 task × 8 GB × 730 hr | $0.004445 × 3 × 8 × 730 | **$77.81** |
| Auto-scaling burst（+50%）| | | | **+$216** |
| **小計**（Fargate）| | | | **$649 / 月** |

#### Aurora PostgreSQL Serverless v2
- 公式：[Aurora Serverless v2 Pricing](https://aws.amazon.com/rds/aurora/serverless/)

| 項目 | 単価 | 個数 | 月額計算 | 月額 |
|---|---:|---:|---|---:|
| ACU 時間 | $0.12 / ACU-hr | 平均 6 ACU × 730 hr | $0.12 × 6 × 730 | **$525.60** |
| ストレージ | $0.10 / GB-月 | 200 GB | $0.10 × 200 | **$20** |
| バックアップ | $0.021 / GB-月 | 400 GB | $0.021 × 400 | **$8.40** |
| **小計**（Aurora）| | | | **$554 / 月** |

#### ElastiCache for Redis
- 公式：[ElastiCache Pricing](https://aws.amazon.com/elasticache/pricing/)

| 項目 | 単価 | 個数 | 月額計算 | 月額 |
|---|---:|---:|---|---:|
| cache.r6g.large（2 vCPU + 13.07 GB）| $0.206 / hr | 2 node × 730 hr | $0.206 × 2 × 730 | **$300.76** |
| **小計**（ElastiCache）| | | | **$301 / 月** |

#### ALB + CloudFront + NAT Gateway + ログ + その他

| リソース | 単価 / 構成 | 月額計算 | 月額 |
|---|---|---|---:|
| ALB（時間 + LCU）| $0.0225/hr × 730 + LCU ~$10 | $16.43 + $10 | **$26** |
| CloudFront（Hosted UI 静的）| $0.085/GB out + Req | 50 GB out + 50M req | **~$60** |
| NAT Gateway（3 AZ）| $0.045/hr × 3 × 730 | $0.045 × 3 × 730 | **$98.55** |
| CloudWatch Logs / X-Ray | $0.50/GB ingest + storage | 100 GB ingest | **~$53** |
| S3 backup | $0.023/GB | ~50 GB | **~$12** |
| Data Transfer out | $0.09/GB | ~50 GB | **~$50** |
| **小計**（その他）| | | **~$300 / 月** |

#### Keycloak インフラ 月額・年額合計

| 区分 | 月額 | 年額 |
|---|---:|---:|
| ECS Fargate | $649 | $7,788 |
| Aurora Serverless v2 | $554 | $6,648 |
| ElastiCache Redis | $301 | $3,612 |
| その他（ALB / CF / NAT / Logs / S3 / DT）| $300 | $3,600 |
| **インフラ合計** | **$1,804** | **$21,648** |

### 運用コスト（Operations）

| 項目 | 想定 | 年額（日本基準）|
|---|---|---:|
| 平日対応 SRE（0.5 FTE）| 構築・運用・パッチ追従 | **¥1,500 万 ≈ $100K** |
| 24/7 オンコール（追加 0.3 FTE）| 重大インシデント対応 | + ¥900 万 ≈ + $60K |

### Keycloak Total（自前ホスト）

| 構成 | インフラ | 運用 | ライセンス | **年額** |
|---|---:|---:|---:|---:|
| **OSS（平日対応）** | $22K | $100K | $0 | **$122K** ⭐ |
| **OSS（24/7）** | $22K | $160K | $0 | $182K |
| **RHBK（平日対応）** | $22K | $100K | $50-100K | $172-222K |
| **RHBK（24/7、Red Hat サポート利用）**| $22K | $100K | $100-150K | $222-272K |

→ RHBK ライセンスは [Red Hat 認定リセラ見積もり](https://access.redhat.com/products/red-hat-build-of-keycloak) 必須。

---

## 5. 比較統合表（10M MAU 年額）

| 製品 | 計算式 | 年額 USD | 年額 ¥（1$=150¥）|
|---|---|---:|---:|
| **Keycloak OSS（平日）** ⭐ | $22K + $100K | **$122K** | **¥1,830 万** |
| Keycloak OSS（24/7） | $22K + $160K | $182K | ¥2,730 万 |
| RHBK（平日 + ライセンス）| $22K + $100K + $50-100K | $172-222K | ¥2,580-3,330 万 |
| RHBK（24/7 + Red Hat サポート）| $22K + $100K + $100-150K | $222-272K | ¥3,330-4,080 万 |
| Auth0 Enterprise（最低想定）| – | $240K | ¥3,600 万 |
| **Cognito Lite** | $0.00325 × 9M + $0.0046 × 900K + $0.0055 × 50K | **$404K** | **¥6,060 万** |
| Auth0 Enterprise（標準）| – | $600K | ¥9,000 万 |
| Auth0 Enterprise（Advanced）| – | $1,200K | ¥1.8 億 |
| **Cognito Essentials** | $0.015 × 9.99M | **$1,798K** | **¥2.7 億** |
| **Cognito Plus** | $0.020 × 10M | **$2,400K** | **¥3.6 億** |
| **Entra External ID** | $0.03 × 9.95M | **$3,582K** | **¥5.4 億** |

### 視覚化（年額、千ドル）

```
$3582K ┤                                            ████ Entra External ID
$2400K ┤                                      ████ Cognito Plus
$1800K ┤                                ████ Cognito Essentials
$1200K ┤                          ████ Auth0 Advanced
$ 600K ┤                    ████ Auth0 Standard
$ 404K ┤              ████ Cognito Lite
$ 240K ┤        ████ Auth0 Enterprise min / RHBK
$ 122K ┤  ████ Keycloak OSS ⭐
$   0K ┴────────────────────────────────────────────
```

### 3 年累積 TCO

| 製品 | 3 年累積 |
|---|---:|
| **Keycloak OSS（平日対応）** | **$366K** ⭐ |
| Keycloak OSS（24/7） | $546K |
| RHBK（平日対応）| $516-666K |
| Cognito Lite | $1,212K |
| Auth0 Enterprise（標準）| $1,800K |
| Cognito Essentials | $5,394K |
| Cognito Plus | $7,200K |
| Entra External ID | $10,746K |

---

## 6. ADR-006 損益分岐との関係

[ADR-006](006-cognito-vs-keycloak-cost-breakeven.md) で「**175,000 MAU が損益分岐点**」と整理した。**10M MAU は分岐点の 57 倍**を遥かに超えており、Cognito Essentials との差額は **年 $1.68M（¥2.5 億）/ 3 年 $5M（¥7.5 億）**。

```
              損益分岐点（Cognito Essentials vs Keycloak OSS）
                  ↓ ~175,000 MAU
    │
    │                                      Cognito Essentials
    │                                       ╱
    │                                    ╱
    │                                 ╱
    │ ─────────────────────╱── Keycloak OSS（ほぼ flat）
    │ ╱
    └────────────────────────────────→ MAU
    0          175K              10M
```

---

## 7. 機能比較（10M MAU CIAM 用途で重要な観点）

| 機能 | Cognito Essentials | Entra External ID | Auth0 / Okta CIAM | Keycloak OSS / RHBK |
|---|:---:|:---:|:---:|:---:|
| OIDC / OAuth 2.0 | ✅ | ✅ | ✅ | ✅ |
| SAML SP / IdP | ✅ | ✅ | ✅ | ✅ |
| 顧客 IdP Federation 数 | △（制限）| ✅ | ✅ 60+ コネクタ | ✅ 無制限 |
| マルチテナント | △ Pool 分離 | △ tenant 分離 | ✅ Organizations | ✅ Realm |
| MFA（TOTP / SMS / WebAuthn）| ✅（Plus 推奨）| ✅ | ✅ | ✅ |
| Adaptive Auth / Risk Based | △ Plus のみ | ✅ P2 | ✅ Enterprise | △ 拡張可（自社開発）|
| Hosted UI | ✅ Managed Login | ✅ Custom Policies | ✅ Universal Login | ✅ Themes |
| UI カスタマイズ（フル CSS / HTML）| △ 制約あり | △ 制約あり | ✅ | ✅ Theme 自由 |
| Token カスタマイズ | △ Pre Token Lambda | ✅ Custom Claims | ✅ Hooks / Actions | ✅ Protocol Mapper |
| Custom Authentication Flow | △ 制約 | △ User Flows | ✅ Actions | ✅ SPI 完全自由 |
| **Bring Your Own DB**（既存ユーザ DB 統合）| ❌ | ❌ | ✅ Custom DB | ✅ User Storage SPI |
| **Token Exchange RFC 8693** | ❌ | △ | △ | ✅ ネイティブ |
| Audit Log | ✅ CloudTrail | ✅ | ✅ | ✅ Event Listener |
| コンプラ認証（SOC 2 / ISO 27001 等）| ◎ AWS 標準 | ◎ Microsoft 標準 | ◎ | △ 自社取得（RHBK は ✅）|
| SDK | ◎ AWS SDK | ✅ MSAL | ✅ Auth0 SDK 充実 | △ OSS ライブラリ |
| 日本語サポート | ○ AWS | ○ Microsoft | △ 限定 | △（RHBK は ◎ Red Hat 日本）|
| ベンダーロックイン | ❌ 強い | ❌ 強い | ❌ 強い | ◎ なし（OSS）|

---

## 8. Decision

### Decision Matrix

| 評価軸 | Keycloak OSS | RHBK | Cognito Essentials | Entra Ext ID | Auth0 Enterprise |
|---|:---:|:---:|:---:|:---:|:---:|
| コスト（10M MAU 年額）| ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐ | ⭐⭐ |
| 運用負荷 | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| カスタマイズ性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| Token Exchange (RFC 8693) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐ | ⭐⭐⭐ |
| 既存ローカルユーザ DB 統合 | ⭐⭐⭐⭐⭐（SPI）| ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐ | ⭐⭐⭐（Custom DB）|
| ベンダーロックイン | ⭐⭐⭐⭐⭐ なし | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐ |
| コンプラ認証 | ⭐⭐ 自社取得 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 日本語サポート | ⭐⭐ コミュニティ | ⭐⭐⭐⭐⭐ Red Hat 日本 | ⭐⭐⭐⭐ AWS | ⭐⭐⭐⭐ MS | ⭐⭐ |

### Decision

**第 1 推奨：Keycloak OSS（平日対応 + 自社オンコール）**
- 年額 $122K（¥1,830 万）
- ADR-006 損益分岐点 17.5 万 MAU の **57 倍**規模で **コスト優位 14 倍 vs Cognito Essentials**
- [ADR-019](019-existing-system-migration.md) の User Storage SPI で既存ローカルユーザ DB 統合可
- 既存方向（[project_platform_direction_keycloak.md](../../.claude/memory/project_platform_direction_keycloak.md)）と一致
- [ADR-030](030-minimal-jwt-claim-design.md) の最小 JWT クレーム設計と Protocol Mapper / SPI 自由度で完全整合

**第 2 推奨：RHBK（規制業界 / FIPS 140-2 / 24/7 必須なら）**
- 年額 $172-272K（¥2,580-4,080 万）
- Red Hat 日本のサポート + 認定資料一式
- [ADR-015](015-rhbk-validation-deferred.md) の本番設計フェーズ検証対象

### 棄却理由

| 製品 | 棄却理由 |
|---|---|
| Cognito Essentials | 年 $1.8M、Keycloak OSS と比べて **+$1.68M/年** の追加負担、Token Exchange 非対応で ADR-030 マイクロサービス OBO 設計と矛盾 |
| Cognito Plus | 年 $2.4M、Adaptive Auth が必要なら検討余地あるが価格差大 |
| Entra External ID | 年 $3.58M、最高額。Microsoft 365 統合が決定的要件でない限り選ばない |
| Auth0 Enterprise | 機能最強だがロックインリスク + 価格上昇トレンド + 日本語サポート弱、コスト交渉次第で再評価 |
| Cognito Lite | コストは健闘（$404K）だが、Managed Login 不可・MFA 制約・カスタムクレーム制約大で 10M B2C 用途には不十分 |

---

## Consequences

### Positive

- **コスト優位**：3 年で Cognito Essentials 比 **$5M（¥7.5 億）節約**、Entra External ID 比 **$10M（¥15 億）節約**
- **既存資産活用**：[ADR-019](019-existing-system-migration.md) User Storage SPI で既存ローカルユーザ DB 統合、移行リスク低減
- **Token Exchange RFC 8693 ネイティブサポート**：[ADR-030](030-minimal-jwt-claim-design.md) のマイクロサービス OBO 設計と完全整合
- **ベンダーロックインなし**：OIDC 標準準拠で将来の移行容易
- **マルチテナント L2**（[ADR-017](017-multitenant-l2-single-realm.md)）の Realm 設計と整合

### Negative

- **自社運用負荷**：パッチ追従、HA 設計、DR 構成、24/7 体制を自社責任
- **コンプラ認証は自社取得**：SOC 2 / ISO 27001 等を必要に応じて自社で取得
- **PoC 必須**：10M MAU 想定の負荷試験で Aurora ACU sizing / JWKS endpoint レイテンシを実機確認
- **0.5 FTE 確保**：構築フェーズ + 運用フェーズで継続的に SRE 人材確保
- **Red Hat 移行可能性の維持**：将来 RHBK 切替（24/7 サポート要件発生時）を想定した設計

### Risks & Mitigations

| リスク | 対策 |
|---|---|
| 運用ミスでダウン | 適切な人員確保、構築フェーズで充実したテスト、Multi-AZ + DR 構成 |
| パッチ追従漏れで脆弱性 | 四半期パッチサイクルの確立、RHBK 移行で軽減 |
| スケール時のチューニング | PoC で 10M MAU 想定負荷試験、Aurora ACU 動的スケール |
| キーローテーション運用 | [ADR-030](030-minimal-jwt-claim-design.md) クレーム設計と統合 |
| コンプラ取得 / 監査対応 | Audit Manager / Security Hub で補完 |

---

## 留意事項（コスト試算の精度を上げるため）

1. **Cognito 旧 Pool は 50K MAU 無料**（5 倍お得）→ 移行ではなく新規 Pool 採用想定
2. **Cognito 通信費（SMS / メール）** は追加料金、SMS 多用なら +$10K-30K/年
3. **Cognito Lite** はマネージドログイン不可、本格 UI には Essentials 必要
4. **Entra External ID** は P1/P2 統合され $0.03 単一料金に簡素化（2025 以降）
5. **Auth0 価格** は公開価格と乖離、社内見積もりで確定要
6. **Keycloak 運用人月** は日本基準 ¥1,500 万（米基準 $100K）で換算、自社人件費レート確認要
7. **RHBK ライセンス** は規模・サポートレベル次第、Red Hat 認定リセラに正式見積もり
8. **Aurora 課金モデル**：Standard vs I/O-Optimized（高 I/O なら +30%）の選定要
9. **想定 DAU/MAU 30%**、想定ピーク 10x burst は業界平均、実トラフィックで検証要
10. **PoC 必須**：10M MAU 想定の負荷試験を Keycloak で実施し、Aurora ACU sizing 確定

---

## References（公式ドキュメント）

### AWS Cognito
- [Amazon Cognito - Pricing](https://aws.amazon.com/cognito/pricing/)
- [AmazonCognito pricing dimensions - Vantage](https://cur.vantage.sh/aws/amazoncognito/)
- [AWS Cognito Pricing Calculator (Jun 2026) - Costgoat](https://costgoat.com/pricing/amazon-cognito)
- [2026 Amazon Cognito's latest pricing - Logto blog](https://blog.logto.io/amazon-cognito-pricing)

### Microsoft Entra External ID
- [External ID Pricing - Microsoft Learn](https://learn.microsoft.com/en-us/entra/external-id/external-identities-pricing)
- [Microsoft Entra External ID—Pricing](https://www.microsoft.com/en-us/security/pricing/microsoft-entra-external-id)
- [Understanding External Identities Pricing - M365.fm](https://www.m365.fm/blog/understanding-external-identities-pricing-in-microsoft-entra-id/)
- [Microsoft Entra External ID General Availability](https://blog.admindroid.com/microsoft-entra-external-id/)

### Auth0 / Okta
- [Auth0 Pricing Changes for Customer Identity Cloud](https://auth0.com/blog/upcoming-pricing-changes-for-the-customer-identity-cloud/)
- [Auth0 Pricing Explained - Security Boulevard](https://securityboulevard.com/2025/09/auth0-pricing-explained-and-why-startups-call-it-a-growth-penalty/)
- [Auth0 Pricing 2026 - Costbench](https://costbench.com/software/identity-access-management/auth0/)

### Keycloak / RHBK
- [Red Hat build of Keycloak 26.4 High Availability Guide](https://docs.redhat.com/en/documentation/red_hat_build_of_keycloak/26.4/pdf/high_availability_guide/Red_Hat_build_of_Keycloak-26.4-High_Availability_Guide-en-US.pdf)
- [Concepts for sizing CPU and memory resources - Red Hat Docs](https://docs.redhat.com/en/documentation/red_hat_build_of_keycloak/26.2/html/high_availability_guide/concepts-memory-and-cpu-sizing-)
- [Keycloak Performance Benchmarks (2025-10)](https://www.keycloak.org/2025/10/keycloak-benchmark)
- [RHBK Product Page](https://access.redhat.com/products/red-hat-build-of-keycloak)

### AWS Infrastructure（Keycloak 自前ホスト用）
- [AWS Fargate Pricing](https://aws.amazon.com/fargate/pricing/)
- [Aurora Serverless v2 Pricing](https://aws.amazon.com/rds/aurora/serverless/)
- [Aurora Pricing (Standard vs I/O-Optimized)](https://aws.amazon.com/rds/aurora/pricing/)
- [ElastiCache Pricing](https://aws.amazon.com/elasticache/pricing/)
- [cache.r6g.large pricing and specs - Vantage Instances](https://instances.vantage.sh/aws/elasticache/cache.r6g.large)
- [AWS Aurora Pricing Guide (2026) - Bytebase](https://www.bytebase.com/blog/understanding-aws-aurora-pricing/)
