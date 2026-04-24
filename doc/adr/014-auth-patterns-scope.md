# ADR-014: 共有認証基盤が対応する認証パターンの範囲

- **ステータス**: Proposed（要件定義フェーズで Accepted に昇格予定）
- **日付**: 2026-04-24
- **関連**:
  - [auth-patterns.md](../common/auth-patterns.md)（パターン総覧と Cognito/Keycloak 対応詳細）
  - 将来の **ADR-015**（Cognito vs Keycloak 最終選定）に直接影響

---

## Context

PoC では SPA + Authorization Code + PKCE のみを検証している。しかし共有認証基盤として運用するには、利用システムから多様な認証パターンへの対応要求が想定される:

| 想定される利用パターン | 例 |
|------------------|-----|
| ブラウザ SPA | 既存の React/Vue 業務画面 |
| SSR バックエンド | Next.js / Spring MVC / Rails |
| ネイティブモバイル | 顧客向けスマホアプリ |
| バッチ・連携処理（M2M） | 夜間バッチ、ETL、API 同士の連携 |
| マイクロサービス間（ユーザー文脈伝播） | サービス分割が進んだ業務システム |
| CLI / IoT デバイス | 運用ツール、機器連携 |
| レガシー業務システム（SAML） | 既存パッケージソフト |
| 高セキュリティ M2M（mTLS） | 金融 API、FAPI 準拠 |

**全パターンに対応するのは過剰**だが、**「どこまで必須とするか」が Cognito vs Keycloak の選定に直結する**:

- Token Exchange / Device Code / SAML IdP / mTLS の **いずれかが必須なら Keycloak 必須**
- これらが不要なら Cognito で完結可能

したがって、認証パターン範囲の確定が **プラットフォーム選定の前提条件**となる。

---

## Decision（Proposed）

要件定義フェーズの結果を踏まえて確定するが、**現時点での暫定推奨**は以下:

### 必須（Must）— 全顧客で共通必要

| パターン | 理由 | Cognito | Keycloak |
|---------|------|:------:|:------:|
| **SPA（PKCE）** | 標準的なフロントエンド | ✅ | ✅ |
| **SSR Web App（Confidential Client）** | サーバサイドレンダリングは現代の Web 標準 | ✅ | ✅ |
| **M2M（Client Credentials）** | バッチ・連携処理は必ず存在 | ✅（要 Resource Server） | ✅ |

### 強推奨（Should）— 多くの顧客で必要

| パターン | 理由 | Cognito | Keycloak |
|---------|------|:------:|:------:|
| **ネイティブモバイル（PKCE）** | 顧客向けアプリ提供時に必要 | ✅ | ✅ |
| **Token Exchange** | マイクロサービス化が進む顧客で必要 | ❌ | ✅ |

### 検討（Could）— 顧客要件次第

| パターン | 検討トリガー | Cognito | Keycloak |
|---------|----------|:------:|:------:|
| **SAML IdP として発行** | 顧客の業務システムが SAML SP のみ対応 | ❌ | ✅ |
| **SAML SP として受入** | 顧客 IdP が SAML 専用（ADFS 等） | ✅ | ✅ |
| **Device Code** | CLI / IoT 連携要件あり | ❌ | ✅ |

### 不採用（Won't）

| パターン | 理由 |
|---------|------|
| **mTLS** | FAPI 準拠の金融系のみ。共有基盤としては過剰 |
| **ROPC** | OAuth 2.1 で非推奨、レガシー移行の暫定用途のみ |

---

## Consequences

### プラットフォーム選定への影響

本 ADR の範囲確定により、プラットフォーム選定（**ADR-015**）の方向性が決まる:

| 必須範囲のシナリオ | 推奨プラットフォーム | 理由 |
|----------------|----------------|------|
| Must のみ（SPA + SSR + M2M） | **Cognito 可、Keycloak 可** | コスト・運用で判断（ADR-006） |
| Must + ネイティブモバイル | **Cognito 可、Keycloak 可** | 同上 |
| Must + **Token Exchange** | **Keycloak 必須** | Cognito 非対応 |
| Must + **SAML IdP 発行** | **Keycloak 必須** | Cognito 非対応 |
| Must + **Device Code** | **Keycloak 必須** | Cognito 非対応 |

### 4 つの「Cognito では実現不可」パターンの再確認

1. **Token Exchange（RFC 8693）** — マイクロサービス間ユーザー文脈伝播
2. **Device Code Flow** — CLI / IoT 認証
3. **SAML IdP 発行** — 既存 SAML SP（業務システム）への認証提供
4. **mTLS** — FAPI 準拠

→ いずれかが顧客要件に存在する場合、**Cognito 単独では不可**。Keycloak または ハイブリッド構成が必要。

### Negative

- 検討範囲が広いとヒアリング工数が増大
- 範囲を絞りすぎると後付け対応のコストが大きい（特に Token Exchange）

### Neutral

- PoC で全パターンを検証する必要はない（範囲確定後に追加検証）

---

## Alternatives Considered

| 案 | 判断 |
|----|------|
| 全パターン対応（Keycloak 一択） | 過剰、運用コスト過大、却下 |
| SPA のみ（PoC 現状維持） | 共有基盤として機能不足、却下 |
| **要件定義で必須範囲を決め、それに基づき選定**（採用） | 顧客要件に最適化、コスト最適化が可能 |

---

## Decision に必要なヒアリング項目

要件定義（Phase B 技術要件 / Phase A 事業要件）で以下を確認:

| 項目 | 回答が「Yes」なら… |
|------|----------------|
| 顧客のシステムで SSR バックエンドはあるか | **SSR を Must に（ほぼ確定）** |
| 夜間バッチ / API 連携処理はあるか | **M2M を Must に（ほぼ確定）** |
| ネイティブモバイルアプリはあるか | ネイティブを Should/Must に |
| マイクロサービス化が進んでいるか / 進める予定か | **Token Exchange を Should に → Keycloak 必須** |
| 既存業務システムで SAML 専用のものはあるか | **SAML IdP 発行を Should/Must に → Keycloak 必須** |
| CLI ツール / IoT デバイスからの認証要件はあるか | Device Code を Could/Should に → Keycloak 必須 |
| 金融・医療 API で FAPI 準拠が要求されるか | mTLS を Should に → Keycloak 必須 |

---

## Follow-up

1. **要件定義フェーズの Phase A / B のヒアリング項目**に上記 7 項目を組み込む（[requirements-hearing-strategy.md](../requirements/requirements-hearing-strategy.md) 更新）
2. ヒアリング結果を踏まえ、本 ADR の範囲を Proposed → Accepted に昇格
3. 確定範囲に基づき **ADR-015**（Cognito vs Keycloak 最終選定）を作成
4. 必須範囲のうち PoC 未検証のもの（SSR / M2M）を **Phase 9** で追加検証
