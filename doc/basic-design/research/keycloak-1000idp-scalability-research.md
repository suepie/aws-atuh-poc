# 調査報告: 単一 Realm + Organizations での 1000+ 顧客 IdP スケーラビリティ

調査日: 2026-07-23 / 対象: Keycloak 26.x / 関連: P-16、U2、ADR-017/033/055、§NFR-3

## 総合判定: **条件付き成立(要 PoC)**

- Keycloak は **26.0.0(2024-10)で「1 Realm に 1000+ IdP」を明示目標とした構造改修を完了**(Epic #30084、目標記述「scale to 1K identity providers, each organization with at least 10」)。realm 表現への全 IdP 同梱・realm cache への eager load という根本問題は解消済み。
- ただし:
  - (a) **1000 IdP の公式ベンチマーク実測は未公開**(keycloak-benchmark#382 が Open のまま)
  - (b) **ログイン/アカウントコンソール UI の大量 IdP 対応(10K 目標)は未実装**(#45293、Open / Milestone: Future)
  - (c) 26.5.4 で多テナント系 O(N²) リグレッション前例(#46605)
- 本設計は HRD Custom SPI(ADR-055)で **ログイン画面に IdP 一覧を出さない**ため (b) の最大リスクを設計側で回避済み。

## 経緯(一次資料)

| Issue | 内容 | 状態 |
|---|---|---|
| #21071 | 親 Epic「1000+ IdP in a realm(might be even 10k or more)」 | Closed 2024-07 |
| #30084 | 実行 Epic「Scalability of Identity Providers」受入基準 4 点(realm rep から IdP 除去 / eager load 廃止 / ログインのサーバサイドフィルタ / サーバサイド検索)完了 | Closed 2024-08 |
| #31249〜31254 | 新 SPI `IdentityProviderStorageProvider` + JPA/Infinispan 実装(IdP 専用キャッシュ)、RealmModel IdP メソッド Deprecate | Closed 2024-07〜08 |
| #21072 / #21954 / #32090 | realm GET/PUT から IdP 除去 / モデルレベルページネーション / ログイン時 IdP 取得の全件ロード廃止 | Closed 2024-07〜08 |
| → 26.0.0 リリースノートに「realm representation no longer holds the list of identity providers」明記 | | |
| #45293 | 「up to 10K IdPs without noticeable impact」= **未実装の将来目標**(2026-01 起票) | **Open** |
| keycloak-benchmark#382 | 数千 IdP ベンチ用データセット整備 | **Open** |

改修前の実害報告: 4000 IdP で Admin Console 描画 30 秒 / realm JSON 30.4MB(Discussion #8608)、Admin Events 併用時の realm 更新失敗(#14851)、学術フェデ 3-4 千 IdP で「works terribly」(#21071 参照の KEYCLOAK-17860)。
**26.x での数百〜数千 IdP の正の公開実例は存在しない** → 本 PoC が事実上の一次検証となる。

## Organizations スケール

- 目標(#30085、Closed): **1 Realm 10k organizations でログイン劣化なし**(認証 / トークン / Admin API/UI / FGAP 各観点)。1000 org は目標の 1/10 で設計上余裕圏(ただし公式ベンチ実測なし)。
- Org→IdP 解決は `IdentityProviderStorageProvider` の org 単位クエリ(全件スキャンでない)。org 紐付け IdP はログインページ既定非表示(26.0)。
- 26.6 で Organization Groups、26.7 で org 管理の fine-grained 委譲ロール追加(テナント委譲管理に有用)。

## Terraform 1000+ IdP 管理

- provider 固有の既知 issue はないが、1000 IdP × (IdP + Mapper 4-6 + org 紐付け) ≒ **5,000〜8,000 リソース**。単一 state は refresh でリソースごとに Admin API を叩くため plan が分〜十分オーダー + API 負荷集中が予想され**設計として不成立**。
- 対策: (1) state をテナント単位 or 50-100 社バッチで分割、(2) 日常のテナント追加はオンボーディングパイプライン(Admin API / keycloak-config-cli)へ寄せ、Terraform は基盤層(Realm/Flow/SPI)のみ、(3) `-refresh=false` + 対象限定 apply を CI 標準化。3 レイヤー IdP オンボーディング方針(§FR-2.3.2)と整合。

## 限界時の代替アーキテクチャ

| 選択肢 | 評価 |
|---|---|
| Realm 分割(シャーディング) | 次善。ADR-017 の運用コスト 5 観点が復活 + #46605 型多 Realm リグレッションを再輸入 |
| **Broker 多段(2-tier 拡張)** | **有力**。ADR-033 の IdP-KC 側を 500 IdP/クラスタ等でシャーディングすれば Broker KC の IdP 数を圧縮できる。1000 社超過時の拡張パスとして基本設計に明記 |
| Custom IdP storage SPI | 26.0 で SPI 正式化により技術的に可能だが実績乏。Phase 2 研究テーマ |
| SAML プロキシ前置(SATOSA) | 学術フェデ型要件(全 IdP 一覧 + メタデータ自動同期)のみ。本 B2B 要件では不要 |

## 必須対策 7 点(条件付き成立の条件)

1. Keycloak 26.0+ 必須・**バージョン固定 + 昇格前検証**(#46605 の通りパッチで O(N²) 混入前例)
2. **ログイン画面・アカウントコンソールに IdP 一覧を出さない設計の維持**(#45293 未解決の間、HRD SPI は UX 選好でなく性能成立の前提条件)
3. IdP は必ず **Organization 紐付け**で登録(非 org のグローバル IdP を増やさない)
4. **realm 全体 export/import・realm representation を扱う運用を禁止**(IdP 単位 API のみ。#14851 系再発防止)
5. Terraform **state 分割 or オンボーディング API 化**
6. Infinispan の IdP 専用キャッシュの**サイジング明示設計**(26.4 ベンチ: cache 10k→200k entries で Aurora CPU 77.8%→63.8%)
7. 監視: IdP 系 Admin API p99 / first-broker-login 含むログイン p99 を **IdP 数の関数として継続計測**

## PoC 実測項目(U2 ゲート)

| # | 測定 | 合否目安 |
|---|---|---|
| P-1 | IdP+Org 一括投入(100/500/1000/2000、各 Mapper 5)の投入時間 | 線形増加 |
| P-2 | 認証フロー p99(HRD→IdP 解決→フェデ→first-broker-login)1000/2000 vs 10 IdP | 劣化 +10% 以内 |
| P-3 | Admin Console IdP 一覧・検索・編集、Org 一覧応答 | 3 秒以内 |
| P-4 | キャッシュメモリ実測 + 再起動時間 | IdP 数に線形 |
| P-5 | IdP 追加/無効化 1 件の他テナントログインへの波及 | 波及なし |
| P-6 | Terraform 単一 vs 分割 state の plan 時間 | 分割閾値決定 |
| P-7 | パッチアップグレード(26.x→26.x+1)を 1000 IdP データセットで実施 | リグレッション検知手順確立 |

## 既存文書との矛盾(要修正)

- **§NFR-3.1/3.2「10K IdPs 性能劣化なし実証あり」は誤り**: 10K は #45293 の未実装将来目標。実装済みは 1K 目標(26.0)で実測は未公開。→ 修正済み(2026-07-23)
- ADR-017「A 案の追加コストは IdP エントリの増加のみ」は片面的 → 本調査の条件付き成立 + 必須対策 7 点を Consequences に追記すべき
- ADR-055 の HRD SPI 前提は「性能要件由来の必須制約」に格上げ

## 主要一次資料

- https://github.com/keycloak/keycloak/issues/21071 / 30084 / 31249-31254 / 21072 / 21954 / 32090(1K IdP 改修一式)
- https://www.keycloak.org/2024/10/keycloak-2600-released
- https://github.com/keycloak/keycloak/issues/45293(10K は Open 将来目標)
- https://github.com/keycloak/keycloak-benchmark/issues/382(ベンチ未整備)
- https://github.com/keycloak/keycloak/discussions/8608 / issues/14851(改修前 4000 IdP 実害)
- https://github.com/keycloak/keycloak/issues/30085(10k orgs 目標)/ 46605(多 Realm O(N²))
- https://www.keycloak.org/2025/10/keycloak-benchmark(26.4 公式ベンチ、IdP 数は対象外)
- https://www.keycloak.org/docs-api/latest/javadocs/org/keycloak/models/IdentityProviderStorageProvider.html
