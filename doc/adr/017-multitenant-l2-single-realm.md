# ADR-017: マルチテナント L2（単一 Pool/Realm + 複数 IdP）採用根拠

- **ステータス**: Proposed（要件定義フェーズで Accepted に昇格予定）
- **日付**: 2026-06-11
- **関連**:
  - [§FR-2.3.A アーキテクチャ判断](../requirements/proposal/fr/02-federation.md#fr-23a-アーキテクチャ判断単一-poolrealm--複数-idp-を採用)
  - [ADR-006](006-cognito-vs-keycloak-cost-breakeven.md)（Cognito vs Keycloak コスト損益分岐）
  - 関連 Claude 内部メモリ: `project_multitenant_l2_rationale.md`

---

## Context

マルチテナント認証基盤の設計で「**1 つの Pool/Realm に複数顧客 IdP を並列収容（A 案 = L2 論理分離）**」と「**顧客テナント別の Pool/Realm（B 案 = L3 物理分離）**」のどちらをデフォルトにするか確定が必要。技術的に「Keycloak は数千 Realm 可能」と分かっていても、それが**運用に耐えるか**は別問題。顧客や経営層から「なぜ物理分離しないのか」「Broker 化の効果は定量的にどれくらいか」の問いが想定され、定量根拠が必要。

---

## Decision

**A 案（単一 Pool/Realm + 複数 IdP、論理分離）をデフォルト採用**。B 案（テナント別 Pool/Realm）は規制要件・データ所在分離が法的に強制される顧客のみ例外適用。

---

## A. マルチ Realm 運用の技術的限界（Keycloak バージョン別）

| Keycloak バージョン | Realm 数の実用上限 | 主なボトルネック |
|---|---|---|
| 〜25.x | **100〜200 Realm** | Realm 作成時間が指数関数的に増加、Admin Console 遅延 |
| 26.0〜26.3 | 〜500 Realm | キャッシュ設定チューニング必須 |
| **26.4+** | **1,000+ Realm**（最大 2,600 本番事例あり）| REST endpoint のスケーラビリティ改善、N+1 クエリ修正 |

**実証データ**:
- 本番運用事例: 2,600 Realm 稼働中（Admin Interface・主要 API は問題なし）
- テスト最大値: 3,000 Realm でベンチマーク実施
- ピーク性能: Keycloak Benchmark で 12,000 RPS のスケーラビリティ実証

→ 「数千 Realm 可能」は **26.4 以降**の話。25.x 系では 100〜200 Realm で実用上限。バージョンアップに引きずられない A 案が安全。

## B. 顧客数比例で増えるコストの 5 観点

### B-1. 設定変更の伝播コスト

| 変更内容 | 影響範囲 | コスト構造 |
|---|---|---|
| ブランディング変更（ロゴ・配色）| Realm ごとに Theme 設定 | Realm 数 × 適用時間 |
| IdP プロトコル変更（SAML 署名アルゴ更新等）| Realm ごとに IdP メタデータ再インポート | Realm 数 × 手作業 or IaC 適用 |
| セキュリティパッチ後の動作確認 | 全 Realm の health check | Realm 数 × 確認工数 |
| Password Policy 変更 | 全 Realm に同一ポリシー | Realm 数 × API call |

### B-2. 監視コストの爆発

- Prometheus メトリクスは Realm 単位ラベル → カーディナリティ急増
- **1,000 Realm × 20 メトリクス = 20,000 時系列**
- アラートルールも Realm 単位個別調整が必要

### B-3. キャッシュ・メモリ管理

- 推奨設定: 1 Realm あたり 50 キャッシュエントリ → 1,000 Realm で 50,000 必要
- Infinispan のキャッシュサイズ誤設定で OOM

### B-4. Realm 作成・削除の運用

- 100 Realm 超で作成時間が指数関数的に増加
- バッチでの大量作成は非推奨、API レート制限の設計が必要

### B-5. Admin Console UX の劣化

- 17.0.0 時点では 1,000 Realm で著しく低速
- 26.4 で大幅改善されたが Realm 切替 UI は依然線形検索

## C. コスト爆発の定量イメージ

| 顧客数 | A 案（単一 Realm + 複数 IdP）| B 案（Realm per テナント）|
|---|---|---|
| 10 社 | IdP 設定 10 件、Realm 1 件 | Realm 10 件 + IdP 設定 10 件 |
| 100 社 | IdP 設定 100 件、Realm 1 件 | **Realm 100 件 + IdP 設定 100 件**、設定変更 × 100 |
| 1,000 社 | IdP 設定 1,000 件、Realm 1 件 | **Realm 1,000 件**、Admin Console 重い、メトリクス爆発 |

→ A 案では「Realm 数 = 1 で固定」のため、**追加コストは IdP エントリの増加のみ**。設定変更・監視・キャッシュは Realm 数に依存しないため、顧客数増でも運用負荷は緩やかに上昇するだけ。

## D. Broker パターンの効果実証（WJAETS-2025 論文）

### 出典の確定情報

| 項目 | 内容 |
|---|---|
| 論文 ID | WJAETS-2025-0919 |
| 著者 | Preetham Kumar Dammalapati（Collabrium Systems LLC, USA）|
| タイトル | "Understanding federated identity management: Architecture, protocols and implementation" |
| 掲載誌 | World Journal of Advanced Engineering Technology and Sciences |
| 巻号 | Volume 15, Issue 3 (2025) |
| ISSN | 2582-8266 (Online)、公開 2025-06-03 |

### 主要データ

| 項目 | 値 |
|---|---|
| 直接統合点の削減 | **18 → 6 直接統合点**（= **約 67% 削減**）|
| Azure AD を Federation Broker として採用する企業 | **約 62%** |

### 注意事項

- 論文 PDF 本体はバイナリストリームで直接読めず、**Abstract（HTML ページ）の情報を基にしている**
- 「60% 削減」は丸めとして許容、正確には 67%（18→6）

---

## Consequences

### Positive

- 顧客数が増えても運用負荷は緩やかに上昇するだけ
- Broker パターン整合性を維持（issuer 1 つ、各システムが N 個の issuer を検証する必要なし）
- Keycloak バージョンアップに引きずられるリスクが低い
- 業界実証データ（WJAETS-2025 67% 統合点削減）を顧客説明に使える

### Negative

- データ物理分離が必要な規制顧客向けに B 案を例外的に運用する必要
- 論理分離の正しさを顧客に説明する負担（[§FR-2.3.A.1 § FR-2.3.A.2](../requirements/proposal/fr/02-federation.md#fr-23a1-何が分離共有されているか--論理分離の実態顧客が必ず聞く論点) で対応）

### B 案を例外的に採用する条件

| ケース | 理由 |
|---|---|
| 顧客契約で「データを物理的に分離」と明記 | データ所在地・暗号化キー分離が要件 |
| 規制上の理由（金融とそれ以外の混在禁止等）| コンプライアンス |
| 1 顧客が極めて大規模（10 万 MAU 超）| 性能・コスト個別最適化 |

---

## 参考資料

- **Keycloak Multi-Realm 運用**:
  - [Keycloak 26.4 Performance & Scalability Documentation](https://www.keycloak.org/server/concepts-scalability)
  - [Keycloak Benchmark Project](https://github.com/keycloak/keycloak-benchmark)
  - [Keycloak Issue #11784](https://github.com/keycloak/keycloak/issues/11784) — Realm 作成時間の指数関数的増加
- **Broker パターン効果**:
  - [WJAETS-2025-0919](https://wjaets.com/) — "Understanding federated identity management"（Vol.15 Issue 3, 2025-06-03, Preetham Kumar Dammalapati）
