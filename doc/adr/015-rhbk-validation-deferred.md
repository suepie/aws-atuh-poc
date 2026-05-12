# ADR-015: PoC フェーズでの RHBK 検証は実施せず本番設計フェーズへ先送り

- **ステータス**: Proposed（本番設計フェーズで Accepted に昇格予定）
- **日付**: 2026-04-24
- **関連**:
  - [keycloak-upstream-vs-rhbk.md](../reference/keycloak-upstream-vs-rhbk.md)（Upstream / RHBK 比較・切替手順）
  - [ADR-006](006-cognito-vs-keycloak-cost-breakeven.md)（Cognito vs Keycloak コスト分析、RHBK 採用時に再計算が必要）
  - [ADR-008](008-keycloak-start-dev-for-poc.md)（PoC で start-dev モードを使用）

---

## Context

共有認証基盤として **Red Hat build of Keycloak（RHBK）** の採用可能性が議論された。RHBK は Keycloak の Red Hat 商用ディストリビューションで、以下の付加価値を提供する:

- **FIPS 140-2 認定**（金融・医療・政府系の要件）
- **Red Hat 24/7 商用サポート**
- **Red Hat バックポート CVE**（セキュリティパッチ）
- **認定済みコンテナイメージ**（UBI 9 ベース）

RHBK の検証を PoC で実施するには、`registry.redhat.io` への認証アクセスが必要であり、最低限 **Red Hat Developer Subscription**（無料）の登録が前提となる。

しかし、本 PoC 期間中、以下の制約から **Red Hat ライセンスの取得が困難** であることが確認された:

| 制約 | 影響 |
|------|------|
| 法人契約のリードタイム | 数週間〜数ヶ月、PoC 期間内に間に合わない |
| Developer Subscription（無料）の業務利用 | コンプライアンス上グレー、組織として推奨されない |
| registry.redhat.io へのアクセス | 上記いずれかが必要、PoC 中は手段なし |

→ **PoC 期間中に RHBK イメージを pull できないため、技術的な切替検証が不可能**。

一方で、以下の事実から、**Upstream で検証した結果は RHBK にも高い確度で転用可能**と判断できる:

1. Keycloak 17 以降（Quarkus 化）、**Upstream と RHBK の内部実装はほぼ完全に同一**
2. PoC で検証中の機能（OIDC、SAML、Identity Brokering、Pre Token Lambda 連携用クレーム、Protocol Mapper、TOTP MFA、Token Exchange）は **RHBK 24 系でも利用可能**
3. RHBK 固有の FIPS / 商用サポート / バックポート CVE は **Upstream で検証する性質ではない**（OIDC フローや Realm 設定の正しさを保証するものではない）

---

## Decision（Proposed）

**PoC フェーズでは Upstream Keycloak のみを使用し、RHBK の動作検証は本番設計フェーズへ先送りする**。

### スコープ確定

| 対象 | PoC | 本番設計フェーズ |
|------|:---:|:----------------:|
| OIDC / SAML / Federation 機能 | ✅ Upstream で検証 | （結果を流用） |
| Pre Token / Protocol Mapper | ✅ Upstream で検証 | （結果を流用） |
| Lambda Authorizer 連携 | ✅ Upstream で検証 | （結果を流用） |
| FIPS 140-2 モード | ❌ 検証不可 | ✅ 必要なら検証 |
| Red Hat 商用サポート挙動 | ❌ 検証不可 | ✅ 必要なら検証 |
| RHBK バージョン差分影響（26 → 24） | ❌ 検証不可 | ✅ 必要なら検証 |
| `registry.redhat.io` 経由イメージ配信 | ❌ 検証不可 | ✅ 必要なら検証 |

### 採否判断のタイミング

要件定義フェーズで以下を確認し、その結果に基づき本番フェーズで Upstream / RHBK のどちらを採用するか決定する:

| 確認項目 | RHBK 採用への影響 |
|---------|----------------|
| FIPS 140-2 認定 / 業界規制（金融・医療等）の要否 | **必須要因** |
| Red Hat 商用サポートの要否（24/7 SLA） | 強い候補 |
| 既存の Red Hat 製品利用実績 / サブスクリプション枠 | 採用の追い風 |
| Red Hat サブスクリプション予算（数十万〜数百万円/年）の確保可否 | **採否の決定要因** |
| Keycloak / Quarkus の自前運用ノウハウ | Upstream 採用の判断材料 |

---

## Consequences

### Positive

- **PoC スコープが明確化** — ライセンス取得待ちで PoC が滞らない
- **Upstream での検証結果が RHBK にもほぼそのまま転用可能**（内部実装同一の事実）
- 本番フェーズでの RHBK 切り替えタスクが**明確なリストとして整理**されている（[keycloak-upstream-vs-rhbk.md §5](../reference/keycloak-upstream-vs-rhbk.md)）
- 要件定義時に「なぜ PoC で RHBK を検証していないか」をドキュメント化された根拠で説明可能

### Negative

- **FIPS / 商用サポート挙動は本番フェーズまで未検証**のまま
- **バージョン差（Upstream 26 vs RHBK 24）の検証も本番フェーズに持ち越し**
- RHBK 採用判断を誤ると、本番直前で再検証が発生するリスクあり

### Neutral

- 本決定は「RHBK を採用しない」ではなく **「採否は本番設計時に判断」** を意味する
- [ADR-006](006-cognito-vs-keycloak-cost-breakeven.md) のコスト試算に **RHBK 採用ケースの追記** が必要
- 関連ドキュメント [keycloak-upstream-vs-rhbk.md](../reference/keycloak-upstream-vs-rhbk.md) を本番設計時の参照資料として確定

---

## Alternatives Considered

| 案 | 判断 |
|----|------|
| 個人の Developer Subscription を業務利用 | コンプライアンス上グレー、却下 |
| UBI 9 ベースで擬似 RHBK 構成を構築（自前で UBI に Keycloak をインストール） | 得るものより手間が大きい、却下（FIPS は別途必要、Red Hat バックポート CVE は得られない） |
| Red Hat 法人契約取得を待ってから PoC を継続 | リードタイム数週間〜数ヶ月、PoC スケジュール影響大、却下 |
| **Upstream で検証し本番設計時に RHBK 切替判断**（採用） | 内部実装同一の事実に基づく合理的判断 |

---

## Follow-up

本番設計フェーズで実施するタスク（[keycloak-upstream-vs-rhbk.md §5.1](../reference/keycloak-upstream-vs-rhbk.md)）:

1. Red Hat 法人契約の取得（営業窓口経由）
2. `registry.redhat.io` の認証情報を ECS へ組み込み（pull secret 設定）
3. ECR ミラーリング方式の実装（既存 ECR フローを流用）
4. RHBK バージョン選定（採用時点の最新 LTS）
5. Upstream 26 系 → RHBK 24 系のバージョン差分影響確認
6. FIPS モード起動の検証（要件があれば）
7. 商用サポート挙動の確認（実際にチケット起票テスト）

合わせて以下の判断・更新:

- 要件定義時に **FIPS 要否 / サポート要否 / 予算** を確認 → 本 ADR を Accepted に昇格 or 撤回
- 採用が確定した場合、ADR-006 のコスト試算を RHBK ケースで再計算（損益分岐 MAU の上方修正）
