# プラットフォーム選定判断書

**作成日**: 2026-05-08
**ステータス**: 🚧 **ドラフト（評価基準とフレームのみ）** — ヒアリング完了 / Red Hat 回答受領後に確定
**目的**: 共有認証基盤の本番採用プラットフォームを選定する判断書
**前提**: [requirements-document-structure.md §6](requirements-document-structure.md) の構成案に従う

---

## 0. ステータスと完了条件

### 現在の状態

| 項目 | 状態 |
|---|---|
| 評価基準の定義 | ✅ 本ドキュメントで完了 |
| 候補プラットフォームの列挙 | ✅ 本ドキュメントで完了 |
| Phase A 事業要件ヒアリング | ⏳ 未実施 |
| Phase B 技術要件ヒアリング | ⏳ 未実施 |
| Phase C 運用・セキュリティ要件ヒアリング | ⏳ 未実施 |
| Red Hat / リセラ回答受領（[rhbk-vendor-inquiry.md](rhbk-vendor-inquiry.md)） | ⏳ 未実施 |
| スコアリング | ⏳ 上記完了後に実施 |
| 総合判定 | ⏳ 同上 |
| 承認 | ⏳ 同上 |

### 確定条件

以下が全て揃った時点で本ドキュメントを正式版に昇格する:

1. ヒアリング Phase A〜C で「商用サポート要否」「予算」「FIPS 要否」「SLA 要件」が確定
2. [rhbk-vendor-inquiry.md](rhbk-vendor-inquiry.md) の Q1 / Q2 / Q7 への回答受領
3. ステークホルダー（事業側 / 技術側 / 運用側 / セキュリティ側）の合意

---

## 1. 評価基準

### 1.1 評価基準と重み付け

| # | 評価基準 | 重み | 説明 |
|---|---|:---:|---|
| C1 | **コスト（3 年 TCO）** | **高（×3）** | インフラ + ライセンス + 運用人件費 |
| C2 | **可用性・SLA** | **高（×3）** | 稼働率目標達成可否、フェイルオーバ要件 |
| **C3** | **商用サポート要否** | **高（×3）** | **追加された評価軸**。24/7 サポート / 公式エスカレーションパス / SLA |
| C4 | 運用負荷 | 高（×3） | 日常運用 + 障害対応の工数 |
| C5 | カスタマイズ性 | 中（×2） | クレーム / ログイン画面 / 認証フロー / IdP 追加 |
| C6 | マルチ IdP 対応 | 中（×2） | 顧客 IdP の種類への対応力（OIDC / SAML / LDAP） |
| C7 | DR コスト | 中（×2） | DR 構成の追加コスト |
| C8 | エコシステム | 低（×1） | AWS サービス統合 / OSS 連携 |
| C9 | ベンダーロックイン | 低（×1） | 将来の移行可能性 |
| C10 | スキルセット適合 | 中（×2） | 自社 / SI 体制での運用継続性 |
| **C11** | **法規制・認定要件適合** | 条件（×0/×3） | **FIPS 140-2 / 個人情報保護 / 業界規制が必須なら ×3、不要なら 0** |

### 1.2 商用サポート要否（C3）の判定軸

C3 は「**RHBK / マネージドサービスを採用するか、OSS 自前運用を採用するか**」を直接決める軸。Phase C ヒアリングで以下を確定する:

| 質問 | 確定すべきこと | スコアリング影響 |
|---|---|---|
| Q-S1 | 24/7 商用サポートは必須か？（応答時間 SLA 目標） | 必須なら OSS 自前運用は失格、または SI 委託コスト計上 |
| Q-S2 | 障害発生時、ベンダ起票によるエスカレーション経路が必要か？ | 必須なら RHBK / Cognito / Auth0 が候補 |
| Q-S3 | 認証基盤の障害時、自社で root cause analysis できる体制があるか？ | 体制不十分なら商用サポート必須 |
| Q-S4 | 監査要件で「ベンダサポート契約証跡」の提出を求められるか？ | 必須なら RHBK / マネージドサービス必須 |
| Q-S5 | 既存の Red Hat / AWS Enterprise Support 契約はあるか？ | 既存活用でコスト圧縮可 |

### 1.3 法規制要件（C11）の判定軸

該当する規制があれば C11 = ×3、なければ C11 = 0（評価対象外）として運用。

| 規制 | 影響 |
|---|---|
| FIPS 140-2 | RHBK 必須（Upstream OSS では対応不可）、Cognito も非対応 |
| FedRAMP | AWS GovCloud 系の特殊構成、Cognito の限定的対応 |
| 個人情報保護法 / GDPR | 全候補で対応可（実装次第） |
| PCI DSS | 全候補で対応可（実装次第、監査責任分担に注意） |
| 国内業界規制（FISC 等） | 構成と運用次第。要個別確認 |

---

## 2. 候補プラットフォーム

### 2.1 一次候補（PoC で検証済 or 公式マネージド）

| ID | プラットフォーム | サポート形態 | PoC 検証 |
|---|---|---|:---:|
| **P1** | **AWS Cognito**（マネージド） | AWS Enterprise Support | ✅ Phase 1〜5, 8 |
| **P2** | **OSS Keycloak on AWS ECS Fargate**（PoC 構成のまま） | 自前 / 第三者 MSP | ✅ Phase 6〜9 |
| **P3** | **RHBK on AWS ECS Fargate** | Red Hat 商用サポート | ❌（[ADR-015](../adr/015-rhbk-validation-deferred.md) で先送り） |
| **P4** | **RHBK on AWS EKS / EKS Fargate** | Red Hat 商用サポート | ❌ 未検証 |
| **P5** | **RHBK on ROSA**（Red Hat OpenShift Service on AWS） | Red Hat 商用サポート | ❌ 未検証 |
| **P6** | **RHBK on EC2 RHEL 9** | Red Hat 商用サポート | ❌ 未検証 |

### 2.2 二次候補（参考比較・現実的なフォールバック）

| ID | プラットフォーム | 備考 |
|---|---|---|
| P7 | Auth0（マネージド） | PoC で IdP として利用済み。エンタープライズ価格は要見積 |
| P8 | Phase Two / Cloud-IAM 等の Keycloak マネージド | 第三者 MSP。日本拠点が限定的 |
| P9 | Microsoft Entra External ID | 顧客側で Entra ID を採用済の場合のみ |

### 2.3 候補別の前提条件

| ID | 前提が成立するか確認すべき項目 |
|---|---|
| P1 | Cognito 仕様の機能制約を許容できるか（[ADR-007](../adr/007-osaka-auth0-idp-limitation.md) の Auth0 制約等） |
| P2 | 自前運用 / 第三者 MSP 委託の体制が確保できるか |
| P3 | **[Q1] ECS での RHBK が商用サポート対象か**（[rhbk-vendor-inquiry.md](rhbk-vendor-inquiry.md) Q1 で確認） |
| P4 | **[Q2] EKS / EKS Fargate の RHBK サポート条件**（同 Q2） |
| P5 | OpenShift 運用の学習コスト・ROSA の固定費許容 |
| P6 | EC2 自前運用の負荷許容（Auto Scaling / AMI 管理 / パッチ） |

---

## 3. スコアリング（テンプレート）

> **注**: ヒアリング・回答受領後に各セルを確定する。現時点は **空欄（評価軸の合意のみ）**。

### 3.1 スコアリング方法

- 各評価基準について 1〜5 の 5 段階で評価
- 重み × スコアで小計
- C3（商用サポート）と C11（法規制）は **「必須」となった瞬間に該当しない候補は失格**（合計点に関わらず除外）
- 最終スコア = 全評価基準の重み付き合計

### 3.2 スコアリングテーブル（記入待ち）

| 評価基準 | 重み | P1 Cognito | P2 OSS Keycloak/ECS | P3 RHBK/ECS | P4 RHBK/EKS | P5 RHBK/ROSA | P6 RHBK/EC2 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| C1 コスト（3年TCO） | ×3 | — | — | — | — | — | — |
| C2 可用性・SLA | ×3 | — | — | — | — | — | — |
| **C3 商用サポート** | ×3 | — | — | — | — | — | — |
| C4 運用負荷 | ×3 | — | — | — | — | — | — |
| C5 カスタマイズ性 | ×2 | — | — | — | — | — | — |
| C6 マルチIdP対応 | ×2 | — | — | — | — | — | — |
| C7 DRコスト | ×2 | — | — | — | — | — | — |
| C8 エコシステム | ×1 | — | — | — | — | — | — |
| C9 ベンダーロックイン | ×1 | — | — | — | — | — | — |
| C10 スキルセット適合 | ×2 | — | — | — | — | — | — |
| **C11 法規制要件** | ×0/×3 | — | — | — | — | — | — |
| **合計** |  | — | — | — | — | — | — |

### 3.3 暫定的な事前評価メモ（PoC 知見ベース）

> **正式スコアではない**。Phase A〜C ヒアリング前の所見。ヒアリングで覆る可能性あり。

| 評価基準 | 暫定所見 | 主たる根拠 |
|---|---|---|
| C1 コスト | 175k MAU 以下なら Cognito、それ以上なら Keycloak 系優位 | [ADR-006](../adr/006-cognito-vs-keycloak-cost-breakeven.md) |
| C2 可用性 | Cognito = AWS SLA、Keycloak 系 = 自前構成次第 | PoC 障害検証 |
| C3 商用サポート | Cognito (AWS Support) / RHBK 系（Red Hat） / OSS = 自前 | [rhbk-support-and-pricing.md §7](../reference/rhbk-support-and-pricing.md) |
| C4 運用負荷 | マネージド > 自前。Cognito 最小、ROSA 中、ECS / EC2 大 | PoC Phase 6〜7 |
| C5 カスタマイズ性 | Keycloak 系 ≫ Cognito。テーマ / Mapper / SPI で大差 | PoC Phase 7〜8 |
| C6 マルチIdP対応 | Keycloak ≫ Cognito（SAML / LDAP / 階層 IdP は Keycloak 優位） | [auth-patterns.md](../common/auth-patterns.md) |
| C7 DRコスト | Cognito = User Pool 別、Keycloak 系 = Aurora Global DB | [keycloak-dr-aurora-sync.md](../reference/keycloak-dr-aurora-sync.md) |
| C8 エコシステム | Cognito ≫ 他（IAM / Lambda 統合は AWS native） | Phase 3 |
| C9 ベンダーロックイン | Keycloak 系 ≫ Cognito（OIDC 標準準拠で移行可） | 一般論 |
| C10 スキルセット | 顧客次第。AWS スキル豊富なら Cognito、Java / Quarkus なら Keycloak | 要ヒアリング |
| C11 法規制 | FIPS 必須なら RHBK 系のみ生存、Cognito は非対応 | [keycloak-upstream-vs-rhbk.md §4.1](../reference/keycloak-upstream-vs-rhbk.md) |

---

## 4. 商用サポート要否（C3）に関する詳細評価

### 4.1 候補別のサポート提供元と SLA

| 候補 | サポート提供元 | 一次窓口 | SLA 例（要確認） |
|---|---|---|---|
| P1 Cognito | AWS | AWS Enterprise Support | Critical 15 分 / Business Critical 1 時間 |
| P2 OSS / 自前 | なし | 自社対応 / 第三者 MSP | 自社定義 |
| P3-P6 RHBK 系 | Red Hat | Red Hat Customer Portal | Premium: Severity 1 = 1 時間以内応答 |
| P7 Auth0 | Okta | Auth0 Support | Enterprise plan: Critical 15 分 |
| P8 Phase Two 等 | 第三者 | ベンダ次第 | ベンダ次第 |

### 4.2 RHBK 商用サポートを採用した場合の前提

| 前提 | 出典 / 確認状況 |
|---|---|
| 単体販売不可、Runtimes / Application Foundations / OCP 経由 | ✅ 確認済（[rhbk-support-and-pricing.md §5](../reference/rhbk-support-and-pricing.md)） |
| 2-core / 4-core バンド単位の課金 | ✅ 確認済 |
| 本番 + Hot DR はカウント、Warm/Cold DR は対象外 | ✅ 確認済 |
| **AWS ECS Fargate のサポート可否** | ❓ **公開情報で確定不可、[rhbk-vendor-inquiry.md Q1](rhbk-vendor-inquiry.md) で確認中** |
| AWS EKS / EKS Fargate のサポート可否 | ❓ KB 7072950 subscriber 限定、[rhbk-vendor-inquiry.md Q2](rhbk-vendor-inquiry.md) で確認中 |
| ROSA / RHEL は一級サポート対象 | ✅ 確認済 |
| Multi-Site HA は Aurora PostgreSQL 必須（26.x） | ⚠ 要確認、[rhbk-vendor-inquiry.md Q4](rhbk-vendor-inquiry.md) |

### 4.3 商用サポートが「必須」だった場合の判定フロー

```
Q: C3 商用サポートが必須要件か？
│
├─ Yes: 必須
│   │
│   ├─ Q: ECS Fargate 維持が前提か？
│   │   │
│   │   ├─ Yes → P3 RHBK/ECS（Q1 回答待ち）
│   │   │       Q1=NG なら → P1 Cognito へ振替 or 基盤変更必要
│   │   │
│   │   └─ No  → P4/P5/P6/P1 から選定
│   │
│   └─ → P2 OSS/ECS は失格、または「第三者 MSP 委託」前提でのみ残る
│
└─ No: 不要
    │
    └─ → P2 OSS/ECS が最有力（PoC 構成そのまま）
```

### 4.4 商用サポートが「推奨だが必須ではない」だった場合

- C3 を「重み ×3 → ×2」に下げて再評価
- P2 OSS/ECS が C1（コスト）と C4（運用負荷の許容）次第で生存
- 「**段階的移行戦略**」を併用: 初期は OSS、規模拡大後に RHBK へ移行

---

## 5. 総合判定（記入待ち）

### 5.1 推奨案

> 確定後に記入。テンプレート例:
>
> 「**第一推奨: Pn**（合計スコア XX）」
> 「**第二推奨: Pm**（合計スコア YY）」
> 「**理由**: ...」

### 5.2 採用条件

> 第一推奨案を採用するために満たすべき条件を列挙する:
>
> - [ ] Red Hat 商用サポートの正式契約（Q1 / Q7 完了）
> - [ ] HTTPS / カスタムドメイン化（[ADR-011](../adr/011-auth-frontend-network-design.md)）
> - [ ] start-dev → start --optimized 化（[ADR-008](../adr/008-keycloak-start-dev-for-poc.md) の解消）
> - [ ] DR 構成の確定（Hot / Warm / Cold）
> - [ ] 移行戦略の合意（[migration-strategy.md](migration-strategy.md)（未作成））

### 5.3 棄却した案とその理由

> 第二〜第六候補を棄却した理由を列挙する。

---

## 6. リスク・懸念事項

### 6.1 評価時点で識別済みのリスク

| # | リスク | 影響 | 対策 |
|---|---|:---:|---|
| R1 | RHBK on ECS Fargate の正式サポート可否が確定しない | 高 | [rhbk-vendor-inquiry.md Q1](rhbk-vendor-inquiry.md) で確定。NG なら基盤変更（P4 or P5 へ） |
| R2 | RHBK サブスクリプション価格が予算超過 | 中 | 多年契約割引 20-40%、Standard ティアで様子見 |
| R3 | Cognito 採用時の機能制約（[ADR-007](../adr/007-osaka-auth0-idp-limitation.md) のような IdP 制約） | 中 | カスタム実装 or 外部 IdP 連携で吸収 |
| R4 | ROSA への移行時の運用ノウハウ不足 | 中 | Red Hat トレーニング / 認定リセラ SI 起用 |
| R5 | OSS 自前運用時の障害対応体制不在 | 高 | 第三者 MSP 起用 or 24/7 自社体制構築 |
| R6 | 26.0.x が Maintenance フェーズで CVE 対応のみとなる | 低 | 本番採用は 26.4.x からスタート |

### 6.2 ヒアリング結果次第で発生し得るリスク

| トリガ | 発生し得るリスク |
|---|---|
| FIPS 140-2 必須が判明 | Cognito / OSS は失格、RHBK 系のみ生存 → コスト前提が変わる |
| 24/7 SLA が必須が判明 | OSS 自前運用は失格、第三者 MSP コストが追加 |
| 予算が想定の 1/2 に縮小 | RHBK Premium → Standard、または P1 Cognito へ |
| MAU が想定の 5 倍に拡大 | コスト試算の前提崩壊、再見積もり必要 |
| マルチリージョン要件追加 | ROSA / Aurora Global DB 前提、構成大幅見直し |

---

## 7. 承認

| 役割 | 氏名 | 判定 | 日付 | コメント |
|---|---|:---:|---|---|
| 事業オーナー | — | ⏳ | — | — |
| 技術責任者 | — | ⏳ | — | — |
| 運用責任者 | — | ⏳ | — | — |
| セキュリティ責任者 | — | ⏳ | — | — |
| プロジェクトマネージャ | — | ⏳ | — | — |

---

## 8. 関連ドキュメント

| ドキュメント | 役割 |
|---|---|
| [requirements-document-structure.md](requirements-document-structure.md) | 本ドキュメントの位置づけと構成案 |
| [requirements-hearing-strategy.md](requirements-hearing-strategy.md) | ヒアリング Phase A〜D 戦略 |
| [poc-summary-evaluation.md](poc-summary-evaluation.md) | PoC 総括（評価のインプット） |
| [rhbk-vendor-inquiry.md](rhbk-vendor-inquiry.md) | Red Hat / リセラ照会文（C3 評価のインプット） |
| [doc/reference/rhbk-support-and-pricing.md](../reference/rhbk-support-and-pricing.md) | RHBK サポート対象範囲と価格（事実マトリクス） |
| [doc/reference/keycloak-upstream-vs-rhbk.md](../reference/keycloak-upstream-vs-rhbk.md) | Upstream vs RHBK 比較・本番判断フレーム |
| [ADR-006](../adr/006-cognito-vs-keycloak-cost-breakeven.md) | コスト損益分岐 |
| [ADR-014](../adr/014-auth-patterns-scope.md) | 認証パターン対応範囲 |
| [ADR-015](../adr/015-rhbk-validation-deferred.md) | PoC で RHBK 検証先送り |

---

## 9. 変更履歴

| 日付 | 内容 |
|---|---|
| 2026-05-08 | 初版（評価基準・候補列挙・スコアリングフレームのみ。スコア確定はヒアリング・Red Hat 回答受領後） |
