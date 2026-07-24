# ADR-060: 認証プロトコル攻撃経路 残 TBD 対応（Log scrubbing / Token Binding / Adaptive Auth 連動強化）

- **ステータス**: Proposed（要件定義フェーズで Accepted 昇格予定）
- **日付**: 2026-07-08 作成、**2026-07-23 更新（基本設計 U7 実装確定を反映 — 変更履歴参照）**、**2026-07-24 更新（Flow 明示宣言の IaC 手段から keycloak-config-cli を除去 → Terraform 基盤層 + オンボーディング API に統一 — [U9 D-U9-10](../basic-design/09-operations-observability-design.md)）**
- **関連**:
  - [saml-vs-oidc-comparison.md §7.4 SAML 攻撃経路](../common/saml-vs-oidc-comparison.md#74-saml-改ざんの攻撃経路attack-pathと防御)
  - [saml-vs-oidc-comparison.md §7.5 OIDC 攻撃経路](../common/saml-vs-oidc-comparison.md#75-oidc--oauth-20-攻撃経路attack-pathと防御)
  - [ADR-023 ServiceNow SP 連携](023-servicenow-sp-integration.md)（SAML 連携における Golden SAML 対応の親 ADR）
  - [ADR-030 最小 JWT クレーム設計](030-minimal-jwt-claim-design.md)（OIDC Bearer JWT + 短寿命化）
  - [ADR-034 Adaptive Authentication](034-adaptive-authentication.md)（本 ADR §C の実装親 ADR）
  - [ADR-035 ITDR](035-identity-threat-detection-response.md)（本 ADR §C の検知パイプライン）
  - [ADR-045 鍵管理戦略](045-cryptographic-key-management-strategy.md)（Golden SAML/JWT 対策の親 ADR）
  - [ADR-050 モバイルアプリ認証](050-mobile-sdk-native-auth.md)（DPoP 導入時の RP SDK 影響）
  - [ADR-053 Observability Strategy](053-observability-strategy.md)（本 ADR §A Log scrubbing の実装親 ADR）
  - [ADR-057 CSRF 対策の責任分界](057-csrf-protection-responsibility-boundary.md)（Phase 2 で DPoP 導入判断が波及）
  - **[ADR-025 §H 顧客 IdP が LDAP(s) の場合](025-scim-positioning-and-receive-stance.md)** — §C.2.2 Golden LDAP 系シグナル L-GD-1〜L-GD-5 の起点となる LDAP Bind Service Account 乗っ取り論点（2026-07-08 追記）

---

## Context

### 背景

2026-07-06 に [saml-vs-oidc-comparison.md §7.4 + §7.5](../common/saml-vs-oidc-comparison.md) で **SAML 11 経路 + OIDC 22 経路 = 計 33 の攻撃経路** を体系整理した結果、以下 **3 領域の残 TBD** が浮上した:

1. **Log scrubbing**：SAML P11 + OIDC O22 共通、ALB / CloudFront / CloudWatch / Keycloak Container ログに **SAMLResponse / Authorization Code / Access Token / Refresh Token** 平文残存
2. **Token Binding**：OIDC O20 Token Substitution 完全防御（DPoP / mTLS Bound Token）、Phase 2 候補
3. **Adaptive Auth 連動強化**：SAML P3 Golden SAML + OIDC O3 Golden JWT の "完全防御不可経路" に対する **検知 + 影響最小化** 体制確立

### なぜ 1 つの ADR にまとめるか

- **3 領域とも「§7.4 / §7.5 攻撃経路整理から派生した残課題」で発生源が共通**、個別 ADR に分散すると経路整理との対応が追いにくくなる
- 3 領域とも **既存 ADR（034 / 045 / 053）の拡張** で、新規基盤設計ではない → 派生 ADR として 1 つに集約する方が管理コスト低
- Phase 1 で全て実装するわけではない（B は Phase 2 候補）ため、**優先度・トリガー条件を横断で示す** ことに価値がある

### 業界用語

| 用語 | 意味 |
|---|---|
| **Log scrubbing / Redaction** | ログ書込前 or 収集時に機微情報（トークン等）をマスク処理 |
| **DPoP**（RFC 9449、Demonstrating Proof of Possession）| Access Token を "送信者バウンド" にする OAuth 拡張、SPA/モバイル向け |
| **mTLS Bound Access Token**（RFC 8705）| クライアント証明書と Access Token を紐付け、証明書ない相手は使えない |
| **Golden 攻撃** | IdP の署名鍵を盗んで任意のトークンを偽造する攻撃系（SAML: Golden SAML / OIDC: Golden JWT）|
| **Fluent Bit / Firelens** | K8s Pod ログの ETL、マスキング Filter 設定可能 |

---

## Decision

**3 領域それぞれで Phase 1 / Phase 2 の対応方針を確定**、実装親 ADR に落とし込む:

| 領域 | Phase 1 対応 | Phase 2 候補 | 実装親 ADR |
|---|---|---|---|
| **A. Log scrubbing** | **Fluent Bit マスキング Filter + Lambda 変換 + 監査スキャン**（必須） | — | ADR-053 §拡張 |
| **B. Token Binding** | **短寿命化 + Refresh Rotation のみ**（影響最小化） | **DPoP 導入**（RP SDK 提供）+ mTLS Bound Token（金融顧客のみ） | ADR-057 §I 拡張 |
| **C. Adaptive Auth 連動強化** | **Golden 系 3 検知シグナル追加 + Event Listener SPI 拡張**（必須） | Behavioral Biometrics 統合 | ADR-034 / ADR-035 §拡張 |

**総合方針**：**Phase 1 で A + C を実装、B は Phase 2 に持越し** — SAML 33 経路 のうち Phase 1 完了後の残リスクは "O20 短寿命化のみ" の 1 件に集約される。

---

## A. Log scrubbing（SAML P11 + OIDC O22 対応）

> **2026-07-23 基本設計 U7 実装確定**: 本節の実装は [U7 §7.3](../basic-design/07-security-compliance-design.md) 参照。マスキング辞書に **M-13 `logout_token`（Back-Channel Logout）/ M-14 Basic 認証ヘッダ** を追加。

### A.1 対象データ

| プロトコル | マスク対象 |
|---|---|
| **SAML** | `SAMLResponse=<Base64>`（Assertion 含む）/ `SAMLRequest=<Base64>` / `RelayState=<value>` |
| **OIDC**（認可要求）| `code=<value>` / `state=<value>` / `code_verifier=<value>` / `code_challenge=<value>` |
| **OIDC**（トークン）| `access_token=<JWT>` / `refresh_token=<value>` / `id_token=<JWT>` / `Authorization: Bearer <JWT>` |
| **共通** | Session Cookie (`KEYCLOAK_SESSION`, `KEYCLOAK_IDENTITY` 等) / `Cookie:` ヘッダ全体 |

### A.2 対象レイヤ（各ログソースの扱い）

| ログソース | マスク実装 | 補足 |
|---|---|---|
| **ALB access log** | **S3 → EventBridge → Lambda マスキング → OpenSearch** | ALB は直接マスク不可、収集段で処理 |
| **CloudFront access log**（standard）| S3 → Lambda マスキング | query string 全体除外設定も可能（`OriginRequestPolicy`）|
| **CloudFront realtime log** | Kinesis Data Firehose + Lambda マスキング | Realtime 経路も同処理 |
| **CloudWatch Logs**（Lambda / API GW / EKS control plane）| CloudWatch Logs Subscription Filter → Lambda | 収集段でマスク |
| **Keycloak Container stdout**（EKS Pod）| **Fluent Bit sidecar + regex parser Filter** | 送信前にマスクして CW Logs / OpenSearch へ |
| **アプリ側 debug log**（RP 側）| **RP 実装ガイド + SDK 提供でマスク済ログ推奨** | 顧客側責任、ガイドで注意喚起 |

### A.3 マスキングパターン（正規表現ベース）

```
# SAML
s/SAMLResponse=[A-Za-z0-9%+\/=]+/SAMLResponse=[REDACTED]/g
s/SAMLRequest=[A-Za-z0-9%+\/=]+/SAMLRequest=[REDACTED]/g
s/RelayState=[^&\s]+/RelayState=[REDACTED]/g

# OIDC Authorization Code
s/code=[A-Za-z0-9_\-\.]+/code=[REDACTED]/g
s/code_verifier=[A-Za-z0-9_\-]+/code_verifier=[REDACTED]/g

# OIDC Tokens (JWT パターン)
s/Bearer eyJ[A-Za-z0-9_\-\.]+/Bearer [REDACTED]/g
s/access_token=eyJ[A-Za-z0-9_\-\.]+/access_token=[REDACTED]/g
s/refresh_token=[A-Za-z0-9_\-\.]+/refresh_token=[REDACTED]/g
s/id_token=eyJ[A-Za-z0-9_\-\.]+/id_token=[REDACTED]/g

# Session Cookie
s/(KEYCLOAK_SESSION|KEYCLOAK_IDENTITY)=[^;\s]+/\1=[REDACTED]/g
```

### A.4 実装レイヤ選択理由（なぜ収集段マスキング推奨か）

| 方式 | メリット | デメリット | 採用 |
|---|---|---|:---:|
| **書込前マスク**（Keycloak 側 log config で機微 field を出さない）| ローカルログにも残らない、根本策 | Keycloak 内部実装依存、debug 時に困る、SP 実装依存 | 補助 |
| **収集段マスク**（Fluent Bit / Lambda）| **全ログソース横断で統一**、Keycloak 実装無依存 | Pod ローカルには一瞬残る、収集失敗時に平文が SoR に残るリスク | **✅ 主** |
| **保存後マスク**（OpenSearch Ingest Pipeline）| 保存済ログを再処理可能 | 一時的に平文で S3/OpenSearch に届く | 補助 |

**推奨**：**収集段（Fluent Bit / Lambda）でマスク + 保存後スキャンで漏れ検知** の 2 段構え。

### A.5 監査 / 検知

- **定期スキャン**：OpenSearch で `Bearer eyJ`, `SAMLResponse=`, `code=` 等をパトロール（週 1）
- **発見時対応**：該当ログの発行トークンを **強制 Revocation + 該当ユーザーの再認証要求**
- **監査ログ**：マスク処理自体のログ（何件マスクしたか）を CloudWatch Metrics に

### A.6 実装 ADR

**[ADR-053 Observability Strategy §拡張](053-observability-strategy.md)** に組み込み。本 ADR-060 は要件・パターン提示、実装詳細は ADR-053 側で管理。

### A.7 Phase 1 実装 TODO

- [ ] Fluent Bit sidecar 設定サンプル作成（EKS Pod 用）
- [ ] Lambda マスキング関数のリファレンス実装（Node.js / Python）
- [ ] ALB / CloudFront ログ用 S3 → Lambda → OpenSearch パイプライン IaC
- [ ] マスキングパターン集を [customer-doc/security.md](../common/customer-doc/security.md) に転記
- [ ] 監査スキャンクエリを Grafana Dashboard 化

---

## B. Token Binding（OIDC O20 対応）

### B.1 対象攻撃

**OIDC O20 Token Substitution / Replay**：

```
1. 攻撃者が MITM / XSS / ログから被害者の Access Token を取得
2. 攻撃者は自分のブラウザで API に Access Token 送信 → 通ってしまう
3. 被害者アカウントで API 操作可能（Blast Radius = Access Token 有効期限まで）
```

**Bearer Token の宿命**：**"持っている人 = 使える人"**。Substitution / Replay を完全に防ぐには **送信者の身元を Access Token に紐付ける** 必要がある。

### B.2 選択肢比較

| 手段 | 標準 | 送信者検証方法 | 実装難度 | RP 摩擦 | 適用範囲 |
|---|---|---|:---:|:---:|---|
| **DPoP**（RFC 9449）| IETF Proposed Standard 2023 | クライアント秘密鍵で `DPoP` ヘッダ署名 | 中 | RP に SDK 必要 | SPA / モバイル / SPA + BFF |
| **mTLS Bound Access Token**（RFC 8705）| IETF Proposed Standard 2020 | クライアント証明書 (mTLS) と Access Token 紐付け | 高 | Client Cert 発行・管理 | **B2B / M2M / 金融** |
| **短寿命化のみ**（Phase 1 現状）| — | — | 低 | なし | **Blast Radius 縮小のみ**（完全防御ではない）|

### B.3 DPoP の動作原理（詳細）

```
【SPA 側】
1. SPA が起動時に一時鍵ペア (ES256) を生成、秘密鍵は Memory 保管
2. 認可要求時に DPoP-JWK を送信、IdP が Access Token に紐付け
3. API 呼び出し時:
   ・Authorization: DPoP <access_token>       ← Bearer ではなく DPoP スキーム
   ・DPoP: <JWT with sig by SPA private key>  ← リクエスト固有の署名 JWT

【API 側検証】
1. Access Token の cnf (confirmation) claim が DPoP-JWK と一致
2. DPoP JWT の署名を DPoP-JWK で検証
3. DPoP JWT の htm/htu が現在のリクエスト method/URI と一致
4. DPoP JWT の jti が使い捨て (Replay Cache)

【なぜ Substitution を防げるか】
攻撃者が Access Token を盗んでも、SPA の秘密鍵は Memory から取り出せない
→ DPoP JWT が作れない → API は拒否
```

### B.4 採用方針（Phase 1 / Phase 2 / Phase 3）

| Phase | 対応 | トリガー |
|---|---|---|
| **Phase 1（現状）** | **短寿命化のみ**（Access Token 30 分（[U5 §5.2.1](../basic-design/05-token-session-authz-design.md) 確定）+ Refresh Rotation）| — |
| **Phase 2 候補** | **DPoP 導入検討**（SPA + BFF）| ①ADR-057 §I で DPoP 採用可否検討時に前倒し / ②Access Token 漏洩事案発生 / ③金融顧客要件 |
| **Phase 3 候補** | **mTLS Bound Access Token 併用**（金融/決済顧客）| FAPI 2.0 準拠要件 or B2B API 顧客要件 |

### B.5 Phase 2 導入時の RP 影響

- **SPA 側 SDK 提供必要**：DPoP JWT 生成ライブラリを本基盤で標準提供（[hrd-implementation-keycloak.md](../common/hrd-implementation-keycloak.md) と同様のガイド化）
- **RP 実装ガイドで移行手順明示**：Bearer → DPoP は API GW / Lambda Authorizer 両対応
- **Keycloak 対応状況**：Keycloak 26.1 で DPoP 正式サポート、Keycloak 25 は Preview

### B.6 Phase 1 の残リスク明示

- **O20 Token Substitution は Phase 1 で完全防御されない**（短寿命化による影響最小化のみ）
- **顧客説明で明記**：「本基盤は Phase 1 で Access Token 30 分（[U5 §5.2.1](../basic-design/05-token-session-authz-design.md) 確定）+ Refresh Rotation で影響最小化、Phase 2 で DPoP により完全防御予定」

### B.7 実装 ADR

**[ADR-057 §I TBD 拡張](057-csrf-protection-responsibility-boundary.md)** に統合予定。本 ADR-060 は Phase 判断のみ、実装詳細は ADR-057 側で管理。

---

## C. Adaptive Auth 連動強化（SAML P3 + OIDC O3 + LDAP Bind Service Account 乗っ取り対応）

### C.1 対象攻撃

**完全防御不可経路**：

- **SAML P3 Golden SAML**：IdP 署名鍵盗難 → 任意 Assertion 偽造（SolarWinds 事件、2020）
- **OIDC O3 Golden JWT**：JWKS 秘密鍵盗難 → 任意 JWT 偽造
- **LDAP Bind Service Account 乗っ取り**（2026-07-08 追加、[ADR-025 §H.6](025-scim-positioning-and-receive-stance.md) L-5 論点）：本基盤が顧客 AD に bind する Service Account の資格情報漏洩 → 任意ユーザーとして bind 可能

**共通課題**：**署名鍵 / bind 資格情報が正当である以上、SP / RP から見て偽装との区別は不可能**。SP/RP 側では **"検知 + 影響最小化"** しかできない。

### C.2 検知シグナル（Adaptive Auth Risk Engine 拡張）

**[ADR-034 Adaptive Authentication](034-adaptive-authentication.md)** の Risk Engine に以下シグナルを追加:

#### C.2.1 Golden JWT / SAML 系シグナル（G-1〜G-6）

| シグナル | 検知内容 | 通常時 vs 異常時 |
|---|---|---|
| **G-1: 異常な Subject / aud での発行**| 通常発行しない `sub` / `aud` の組合わせ | 発行分布の統計モデル逸脱 |
| **G-2: 短時間の大量発行**（Bulk generation）| 攻撃者が鍵を使って大量偽造 | 1 分間 100 件超で警戒、1000 件超で即遮断 |
| **G-3: 通常時間帯外の署名操作**（Off-hours signing）| 業務時間外の署名操作増加 | Baseline: 業務時間中心分布 |
| **G-4: 異常な地理的 IP + 未知デバイス**| 攻撃者が偽造 token でログイン | GeoIP + Device Fingerprint 統合 |
| **G-5: JWKS 鍵の異常な使用パターン**| 廃止済 key ID の再登場、または `kid` 未指定 | JWKS ローテ履歴と照合 |
| **G-6: 認証イベントなしの Access Token 発行**（OIDC 特化）| Authorization Code フローを経由しない発行 | Keycloak Event Listener で監視 |

> **2026-07-23 基本設計 U7 実装確定（[D-U7-08](../basic-design/07-security-compliance-design.md)）**: Phase 1 実装 = **G-2 / G-3（簡易版）/ G-5 / G-6 の 4 シグナル**。統計学習を要する **G-1 / G-4 は Phase 2**。

#### C.2.2 Golden LDAP 系シグナル（L-GD-1〜L-GD-5、2026-07-08 追加）

**対象**：[ADR-025 §H.6](025-scim-positioning-and-receive-stance.md) LDAP Bind Service Account 乗っ取り

| シグナル | 検知内容 | 通常時 vs 異常時 |
|---|---|---|
| **L-GD-1: LDAP bind 大量失敗**| Service Account を使った試行錯誤 or Brute Force | 1 分間 5 件超で警戒、20 件超で bind 遮断 |
| **L-GD-2: 通常時間帯外の LDAP bind**（Off-hours LDAP）| Service Account の業務時間外使用 | Baseline: 業務時間中心分布（LDAP User Federation Sync 時刻を除外）|
| **L-GD-3: LDAP 検索クエリの異常パターン**| Service Account が予期しない DN / OU / 大量属性を検索 | `Users DN` 設定値の外側検索、または `objectClass=*` 等の全件クエリ |
| **L-GD-4: LDAP bind 元 IP の異常**| 本基盤 Auth Pod 以外からの bind 試行 | Keycloak Pod IAM Role でしか発生しないはず（[ADR-041 Workload Identity](041-workload-identity-spiffe.md) と照合）|
| **L-GD-5: Sync 頻度異常**| Full Sync 設定値（1 h or 5 min）を超える頻度、または大量属性変更 | Sync ログと差分照合 |

**特徴**：Golden JWT/SAML と違い、**LDAP は本基盤 → 顧客 AD の egress 通信で発生するため VPC Flow Log と組合わせて検知しやすい**（[ADR-039 v2 Network Firewall](039-centralized-network-account-edge-layer.md) 連動）。

#### C.2.3 last_login + provisioned_by 属性書込（2026-07-09 追加、JIT deprovisioning 統合）

**Event Listener SPI に以下 2 機能を統合**（Golden 検知系 SPI と同一 JAR、追加開発コスト小）:

| 機能 | 動作 | 目的 |
|---|---|---|
| **last_login 書込** | LOGIN イベント発生時、`user_attribute.last_login` に epoch ms を書込 | **PCI DSS Req 8.2.6（90 日未使用無効化）対応**、[jit-scim §10.4.A](../common/jit-scim-coexistence-keycloak.md) 依存 |
| **provisioned_by 書込** | REGISTER / IDENTITY_PROVIDER_FIRST_LOGIN 時に `provisioned_by=jit` + `jit_idp_alias`、SCIM プラグイン側で `provisioned_by=scim` + `scim_active=true` を書込 | **JIT/SCIM 判別ロジック**（[jit-scim §10.4.B](../common/jit-scim-coexistence-keycloak.md)）|

**背景**：
- **Keycloak 26.x には native の `last_login_time` フィールドが無い**（[Keycloak Issue #10545 継続 Open](https://github.com/keycloak/keycloak/issues/10545)）
- `user_session` は SSO Session Max（10h）で消滅
- `event_entity` は 10M MAU で 9 億行に肥大化 → **業界標準は Event Listener SPI + `user_attribute` 方式**
- 既存の [jit-scim §10.4](../common/jit-scim-coexistence-keycloak.md) スクリプトは `event_entity` 依存で 10M MAU 破綻 → [§10.4.A Event Listener SPI 版](../common/jit-scim-coexistence-keycloak.md) が代替

**実装統合例**：

> **⚠ 2026-07-09 追加調査結果**：以下の Event Listener + `setSingleAttribute` 直呼び実装は **[Keycloak Issue #14942](https://github.com/keycloak/keycloak/issues/14942)（Closed as not planned）により動かない可能性が極めて高い**。本番実装は **Custom Authenticator SPI に置換必須**（[jit-scim §10.4.E.2 案 B](../common/jit-scim-coexistence-keycloak.md)、確実性最高）。以下のコードは概念説明用リファレンスとして保持。詳細な代替実装 3 案と 14 件の一次資料引用は [jit-scim §10.4.E](../common/jit-scim-coexistence-keycloak.md) 参照。

```java
// ⚠ このコード例は Keycloak Issue #14942 により動かない可能性が極めて高い
// 実装時は jit-scim §10.4.E.2 案 B（Custom Authenticator SPI）に置き換え必須

public class UnifiedEventListener implements EventListenerProvider {
    @Override
    public void onEvent(Event event) {
        // 既存: Golden 検知系（G-1〜G-6 / L-GD-1〜L-GD-5）
        emitToEventBridge(event);

        // 追加①（2026-07-09）: last_login 書込（PCI DSS 8.2.6 対応）
        // ⚠ Keycloak Issue #14942 により setSingleAttribute が動かない可能性
        // 実装時は Custom Authenticator SPI（jit-scim §10.4.E.2 案 B）に置換
        if (event.getType() == EventType.LOGIN) {
            UserModel user = getUser(event);
            if (user != null) {
                user.setSingleAttribute("last_login", String.valueOf(event.getTime()));
            }
        }

        // 追加②（2026-07-09）: provisioned_by 書込（JIT/SCIM 判別）
        // ⚠ 同上、Custom Authenticator SPI 実装推奨
        if (event.getType() == EventType.IDENTITY_PROVIDER_FIRST_LOGIN) {
            UserModel user = getUser(event);
            if (user != null && user.getFirstAttribute("provisioned_by") == null) {
                user.setSingleAttribute("provisioned_by", "jit");
                user.setSingleAttribute("jit_idp_alias", event.getDetails().get("identity_provider"));
                user.setSingleAttribute("jit_created_at", String.valueOf(event.getTime()));
            }
        }
    }
}
```

**Phase 1 実装での置換方針**（2026-07-09 追記）：

- **Event Listener SPI**：Golden 検知系（G-1〜G-6 / L-GD-1〜L-GD-5）の EventBridge emit **のみ**
- **`last_login` / `provisioned_by` 書込**：**新規 Custom Authenticator SPI** で対応（[jit-scim §10.4.E.2 案 B](../common/jit-scim-coexistence-keycloak.md)）
- 詳細と 14 件一次資料引用：[jit-scim §10.4.E](../common/jit-scim-coexistence-keycloak.md)

**✅ 2026-07-10 実機 PoC 検証結果 — 案 B（Custom Authenticator SPI）確定 + Phase 1 実装制約 F-6 追加**

[poc/jit-scim-verification-2026-07-10/](../../poc/jit-scim-verification-2026-07-10/) で実機検証を実施した結果（詳細は [jit-scim §10.4.F](../common/jit-scim-coexistence-keycloak.md)）:

- ✅ **案 B PASS**：Custom Authenticator SPI の `user.setSingleAttribute("last_login", ...)` が認可コードフロー経由で **user_attribute への永続化を実測**（`last_login=1783666203620` 書込確認）
- ✅ **debounce 動作確認**：1 日以内の再ログインで値不変（skip 動作）
- ✅ **Event Listener SPI Issue #14942 の問題を回避**（Authentication Flow 内で transaction 明示制御）

**⚠ Phase 1 実装で最重要の制約 F-6 — SPI の配置**：

Custom Authenticator SPI を **top-level REQUIRED** に置くとログイン失敗する。実測ログ:

```
WARN REQUIRED and ALTERNATIVE elements at same level!
     Those alternative executions will be ignored: [auth-cookie, identity-provider-redirector, ...]
WARN authenticator 'last-login-tracker' requires user to be set ... but user is not set yet
-> LOGIN_ERROR invalid_user_credentials
```

**根拠**：Keycloak のフロー評価では、同一レベルに REQUIRED があると同レベルの ALTERNATIVE が無視される仕様。SPI は `requiresUser() = true` を返すため、user が確定した後に置く必要がある。

**必ずこの配置**（PoC で PASS した構成）:

```
browser-with-last-login
├── level0 Cookie (ALTERNATIVE)
├── level0 Identity Provider Redirector (ALTERNATIVE)
├── level0 Organization (ALTERNATIVE)
└── level0 forms (ALTERNATIVE)
    ├── level1 Username Password Form (REQUIRED)
    └── level1 Last Login Tracker (REQUIRED)   ← ★ ここに配置
```

**Phase 1 実装ガイド**：**Terraform 基盤層 + オンボーディング API（[U9 D-U9-10](../basic-design/09-operations-observability-design.md)、2026-07-24 更新: keycloak-config-cli は不採用）** で以下を明示宣言:

```hcl
resource "keycloak_authentication_execution" "last_login_tracker" {
  realm_id          = keycloak_realm.main.id
  parent_flow_alias = "browser-with-last-login-forms"  # ★ forms サブフロー内
  authenticator     = "last-login-tracker"
  requirement       = "REQUIRED"
  priority          = 30  # Username Password Form の後
}
```

**SPI プロトタイプ**：[poc/jit-scim-verification-2026-07-10/spi/last-login-tracker/](../../poc/jit-scim-verification-2026-07-10/spi/last-login-tracker/) を Phase 1 実装のベースとして流用可能（[ADR-055 HRD Authenticator SPI](055-hrd-implementation-method-selection.md) と同じ Java SPI 開発体制）

**⚠ 2026-07-10 追加 → ✅ 2026-07-13 V3'' 実測 PASS：F-9 フェデ JIT 経路制約と対策**

V3' PoC は **ローカル PW ユーザ（P-4）** で SPI 動作を確認したが、**フェデ JIT ユーザ（P-3、本基盤主用途）は Browser Flow の分岐構造上、上記 SPI 配置では動作しない**。

**Keycloak の分岐仕様**：`browser-with-last-login` の level0 に 4 つ ALTERNATIVE（Cookie / IdP Redirector / Organization / forms）が並ぶ。**1 つ成功すると他は skip**。フェデユーザは `IdP Redirector` で成功 → `forms` サブフロー全体（SPI 含む）が skip → **`last_login` が更新されない**。

**対策：3 系統 Flow 配置**（Phase 1 実装で全て IaC 化）:

| Flow | 対象 | 配置 | 実測状態 |
|---|---|---|---|
| Browser Flow | ローカル PW（P-4）| `forms` サブフロー末尾 | ✅ V3' PASS |
| **First Broker Login Flow** | フェデ JIT 初回（P-1〜P-3）| フロー末尾（Create User If Unique の後）| ✅ V3'' PASS |
| **Post Broker Login Flow** | フェデ JIT 2 回目以降（P-1〜P-3）| フロー末尾 | ✅ V3'' PASS |

**Identity Provider 設定で紐付け**：

```hcl
resource "keycloak_oidc_identity_provider" "customer_entra" {
  # ... IdP 設定 ...
  first_broker_login_flow_alias = "first-broker-login-with-tracker"
  post_broker_login_flow_alias  = "post-broker-login-with-tracker"
}
```

**✅ 2026-07-13 V3'' 実測結果**（[verification-log-v3fed.md](../../poc/jit-scim-verification-2026-07-10/docs/verification-log-v3fed.md)）:

- **T4 初回フェデログイン**：First Broker Login Flow 経由で SPI が initial write（`last_login=1783675449314`）
- **T5 2 回目ログイン**：Post Broker Login Flow 経由で SPI が update（`diff=172800359ms`, debounce 判定込み）
- **`federatedIdentities=[customer-idp]` 確認**：真の JIT ユーザ
- **新知見**：初回時 First + Post 両 Flow が続けて発火（debounce ロジックの両 Flow 対応が必要）
- **新是正 F-7**（setup-federation.sh IdP 作成順序バグ、修正済）/ **F-8**（`user-profile-poc.json` の `_comment` 拒否、除去済）

**⚠ V3'' 妥当性の範囲（重要な留保）**：V3'' の外部 IdP は **同一 Keycloak インスタンス内の別 Realm（`customer-idp`）を OIDC でモック化したもの**。以下は **未検証**（Phase 1 リリース前に追加検証推奨）:

| # | 未検証経路 | 優先度 | 理由 |
|---|---|:---:|---|
| **V3'''** | SAML IdP 経由フェデ | ⚠ 推奨 | V3'' は OIDC のみ。SAML の Assertion 解析 → NameID → JIT 作成の前段が別コードパス。Broker Flow 自体は共通なので通る可能性高いが未実測 |
| **V3''''** | **LDAP User Federation 経由** | 🚨 **必須** | LDAP は **User Storage SPI で Identity Provider ではない** → **Broker Flow を通らず**、First/Post Broker Login Flow 配置の SPI は **動作しない**。Browser Flow forms 経路で発火するかは別 PoC 必要 |
| **統合テスト** | 実 IdP（Entra ID / Okta / Auth0 等）| ⚠ Phase 1 β 必須 | Claims マッピング / 証明書チェーン / `iss` 形式 / `nonce` 実装 / TLS mTLS 等の実世界要因 |

**JWT 実態（V3'' で確認）**：ブローカ構成で 2 種類の JWT が登場。アプリは **ブローカ再発行の 2 番目トークンのみ受領**（`iss=poc-jit-scim`, `sub` は新規発番、カスタム属性は Protocol Mapper 別途要）。Phase 1 実装で `provisioned_by` / `scim_active` / `last_login` を JWT に含めるか要判断。

**Phase 1 実装前ゲート**（V3'' 完了後の残ゲート）：
- 🚨 [B-SCIM-13 V3''''（LDAP）](../requirements/hearing-checklist.md) — 最優先
- ⚠ [B-SCIM-12 V3'''（SAML）](../requirements/hearing-checklist.md)
- ⚠ [B-SCIM-14 実 IdP 統合テスト](../requirements/hearing-checklist.md) — Phase 1 β 段階

**関連 ADR / ドキュメント**：
- **[jit-scim §10.4.A / §10.4.B](../common/jit-scim-coexistence-keycloak.md)** — バッチスクリプト + JIT/SCIM 判別ロジック
- **[broker-data-model.md §2 ③](../common/broker-data-model.md)** — `user_attribute` に `last_login` / `provisioned_by` / `scim_active` を追加
- **[pci-dss-appi-compliance-gap.md §3.2 Req 8.2.6](../common/pci-dss-appi-compliance-gap.md)** — 対応方針
- **ADR-025 §H** — LDAP User Federation の場合の判別戦略（LDAP link 有無で追加識別）

**⚠ 2026-07-14 追加：C.2.3 に Re-Activation SPI 統合（重大なセキュリティ条件）**

90 日バッチで `enabled=false` にした JIT ユーザが復帰した際、Post Broker Login Flow の SPI で自動再有効化する必要があるが、**SCIM で明示削除されたユーザまでも誤って再有効化するとセキュリティ上重大**。LastLoginTracker SPI に Re-Activation ロジックを統合し、以下の条件分岐を必須とする:

```java
public class LastLoginAndReactivationAuthenticator implements Authenticator {

    @Override
    public void authenticate(AuthenticationFlowContext context) {
        UserModel user = context.getUser();
        String provisionedBy = user.getFirstAttribute("provisioned_by");
        String scimActive = user.getFirstAttribute("scim_active");

        // ===== Re-Activation ロジック（重大セキュリティ条件）=====
        if (!user.isEnabled()) {
            // ★ SCIM 管理下のユーザは Re-Activation 禁止（重大）
            //   SCIM DELETE は明示的な削除、フェデ経路で戻ってきても再有効化しない
            if ("scim".equals(provisionedBy) || "true".equals(scimActive)) {
                LOG.warnf("Re-Activation blocked (SCIM-managed): user=%s", user.getUsername());
                context.failure(AuthenticationFlowError.USER_DISABLED);
                return;
            }
            // ★ 管理者は Re-Activation 対象外（本基盤で明示管理、運用者操作待ち）
            if ("local-admin".equals(provisionedBy)) {
                LOG.warnf("Re-Activation blocked (local-admin): user=%s", user.getUsername());
                context.failure(AuthenticationFlowError.USER_DISABLED);
                return;
            }
            // JIT ユーザのみ自動再有効化
            if ("jit".equals(provisionedBy)) {
                user.setEnabled(true);
                user.setSingleAttribute("reactivated_at", String.valueOf(System.currentTimeMillis()));
                LOG.infof("Auto re-activated JIT user: %s", user.getUsername());
            } else {
                // provisioned_by 未設定など想定外は安全側で拒否
                LOG.warnf("Re-Activation blocked (unknown provisioned_by=%s): user=%s",
                          provisionedBy, user.getUsername());
                context.failure(AuthenticationFlowError.USER_DISABLED);
                return;
            }
        }

        // ===== Last Login 更新（既存ロジック、debounce 1 day）=====
        // ...
        context.success();
    }
}
```

**危険な誤発火シナリオ**（この分岐がないと発生）:
```
[Day 100] SCIM DELETE 受信 → enabled=false, scim_active=false
[Day 101] 顧客 IdP 側で退職処理漏れ（連携ミス）→ 本人ログイン試行
  → 顧客 IdP で認証成功 → broker で federated_identity 既存 hit
  → Post Broker Login Flow 発火
  → ★ Re-Activation SPI が SCIM 除外条件なし → user.setEnabled(true) ★
  → JWT 発行 → 元従業員が再ログイン成立 🚨
```

**Flow 配置の主戦場**：**Post Broker Login Flow**（Re-Activation の主要発火点、[jit-scim §10.4.I.4](../common/jit-scim-coexistence-keycloak.md) 参照）。

**監査ログ発行**：Re-Activation 発火時は `USER_REACTIVATED` イベント発行 → ADR-035 ITDR 連携（大量 Re-Activation 検知）。

**詳細**：[jit-scim §10.4.I Re-Activation SPI 実装仕様](../common/jit-scim-coexistence-keycloak.md) + [jit-scim §10.4.G/H JIT/SCIM ライフサイクル 10 シナリオ + 責任分界](../common/jit-scim-coexistence-keycloak.md)

### C.3 検知パイプライン（ADR-035 ITDR 連動）

```
Keycloak Event Listener SPI（署名操作イベント emit）
    │
    ▼
EventBridge（[ADR-035 §C-7.3.10](../requirements/proposal/common/07-implementation-architecture.md#c-7-3-10)）
    │
    ├─→ CloudWatch Logs（監査ログ、SoR）
    │
    ├─→ Lambda Risk Engine（[ADR-034 Adaptive Auth](034-adaptive-authentication.md)）
    │       │
    │       ├─→ DDB Risk Score 更新（ユーザー別）
    │       │
    │       └─→ 閾値超過時：
    │              ・Step-up MFA 強制
    │              ・Session Revocation（Keycloak Session Logout）
    │              ・全 Refresh Token 失効
    │
    └─→ Lambda ITDR Analyzer（[ADR-035](035-identity-threat-detection-response.md)）
            │
            └─→ 異常検知時：SOC 通知（PagerDuty / Slack）+ Trust Center 記録
```

### C.4 対応レベル 4 段階

| Risk Score | 対応 |
|---|---|
| Low (0-30) | ログのみ |
| Medium (31-60) | Step-up MFA 要求（2026-07-23: [U7](../basic-design/07-security-compliance-design.md) の L2「強制再認証」定義を正とする）|
| **High (61-80)** | **Session Revocation + 全 Refresh Token 失効 + ユーザー通知** |
| **Critical (81-100)** | **SOC 即時通知 + 該当鍵の緊急ローテ発動**（[ADR-045](045-cryptographic-key-management-strategy.md) 連動）|

### C.5 Keycloak 実装（Event Listener SPI 拡張）

**[§C-7.3.4.4 Custom SPIs](../requirements/proposal/common/07-implementation-architecture.md#c-7-3-4-4-custom-spi)** の Event Listener SPI に以下イベント追加:

```java
public class GoldenDetectionEventListener implements EventListenerProvider {
    @Override
    public void onEvent(Event event) {
        // 署名操作系イベントを EventBridge に emit
        if (event.getType() == EventType.CODE_TO_TOKEN
         || event.getType() == EventType.REFRESH_TOKEN
         || event.getType() == EventType.CLIENT_LOGIN) {
            emitToEventBridge(
                event.getType(),
                event.getUserId(),
                event.getClientId(),
                event.getIpAddress(),
                event.getSessionId(),
                event.getTime()
            );
        }
    }
}
```

### C.6 実装 ADR

- **検知シグナル追加**：[ADR-034 Adaptive Auth §拡張](034-adaptive-authentication.md)
- **パイプライン**：[ADR-035 ITDR §拡張](035-identity-threat-detection-response.md)
- **緊急鍵ローテ SOP**：[ADR-045 鍵管理戦略 §拡張](045-cryptographic-key-management-strategy.md)

### C.7 Phase 1 実装 TODO

**Golden JWT / SAML 系（G-1〜G-6）**:
- [ ] Event Listener SPI 拡張（G-1〜G-6 シグナル emit）
- [ ] Risk Engine Lambda に G-1〜G-6 シグナル評価ロジック追加
- [ ] 対応レベル 4 段階の閾値決定（ヒアリング B-GD-1〜3 参照）
- [ ] 緊急鍵ローテ Runbook（SOC 手順書）
- [ ] Grafana Dashboard で Golden 検知シグナル可視化

**Golden LDAP 系（L-GD-1〜L-GD-5、2026-07-08 追加）**（[ADR-025 §H.6](025-scim-positioning-and-receive-stance.md) L-5 論点）:
- [ ] Keycloak LDAP User Federation Provider の bind ログ収集（Event Listener SPI + Keycloak 内部ログ）
- [ ] VPC Flow Log で LDAP egress 通信の可視化（Auth Pod IP → 顧客 AD IP、[ADR-039 v2](039-centralized-network-account-edge-layer.md) Network Firewall 経路連動）
- [ ] Risk Engine Lambda に L-GD-1〜L-GD-5 シグナル評価ロジック追加
- [ ] 対応レベル 4 段階の閾値決定（B-LDAP-1〜7 ヒアリング参照）
- [ ] Bind Service Account の緊急ローテ Runbook（SOC 手順書）
- [ ] Grafana Dashboard で Golden LDAP 検知シグナル可視化（Golden JWT/SAML と統合）

---

## D. Consequences

### D.1 Positive

- **攻撃経路 33 件のうち残 TBD 3 件が計画的にクリア**（A + C は Phase 1、B は Phase 2）
- **業界標準準拠**：RFC 9449 DPoP / RFC 8705 mTLS Bound Token / OAuth 2.1 Rotation
- **Golden SAML / Golden JWT の "検知 + 影響最小化" 体制確立**（完全防御不可でも被害を分単位に限定）
- **顧客説明容易**：「33 経路のうち Phase 1 で完全防御 30 件、影響最小化 3 件」と明示可能
- **既存 ADR（034/035/045/053/057）拡張で完結**、新規基盤設計なし

### D.2 Negative / トレードオフ

- **B. DPoP 導入時の RP 側 SDK 提供コスト**（Phase 2 で発生）
- **A. Log scrubbing 実装コスト**（Fluent Bit 設定 + Lambda マスキング + IaC）
- **C. Adaptive Auth Risk Engine 拡張コスト**（G-1〜G-6 シグナル追加、閾値チューニング）
- **C. 誤検知（False Positive）リスク**：Bulk generation 閾値の初期値は運用しながら調整必要

### D.3 リスク軽減

- **A. マスク漏れ**：定期スキャン + 発見時の即 Revocation SOP
- **B. Phase 1 の残リスク**：短寿命化 + 顧客への明示で受容判断
- **C. 誤検知**：Phase 1 は "警戒のみ" → 3 ヶ月チューニング後に "自動遮断" 有効化

---

## E. Phase 1 / Phase 2 実装スケジュール

| Phase | 領域 | 対応 | 完了目標 |
|---|---|---|---|
| **Phase 1a**（要件定義完了直後）| A | Fluent Bit マスク Filter + Lambda マスキング + IaC | Phase 1 リリース時 |
| **Phase 1a** | C | Event Listener SPI 拡張 + Risk Engine G-1〜G-6 実装 | Phase 1 リリース時 |
| **Phase 1b**（Phase 1 リリース + 3 ヶ月）| C | 閾値チューニング + 自動遮断有効化 | Phase 1 リリース + 3 ヶ月 |
| **Phase 2 候補** | B | DPoP 導入（トリガー発生時） | 未定（トリガー次第）|
| **Phase 3 候補** | B | mTLS Bound Access Token 併用（金融顧客用）| 未定（顧客要件次第）|

---

## F. ヒアリング項目追加候補

| 項目 | 記号 | 対象 | 内容 |
|---|---|---|---|
| Log scrubbing 対象拡張要否 | B-LOG-1 | Compliance | ALB / CloudFront / CloudWatch 以外に追加対象あるか |
| DPoP 要件 | B-DPoP-1 | 顧客（特に金融）| Phase 2 前倒しトリガーになる要件あるか |
| mTLS Bound Token 要件 | B-DPoP-2 | 金融顧客 | FAPI 2.0 準拠要件あるか |
| Golden 検知シグナル閾値 | B-GD-1 | SOC | Bulk generation の閾値（現案：1 分 100 件警戒 / 1000 件遮断）|
| Golden 検知 自動遮断タイミング | B-GD-2 | SOC | Phase 1a リリース直後 vs 3 ヶ月チューニング後 |
| 緊急鍵ローテ SOP | B-GD-3 | SOC / SecOps | 承認体制、実施時間目標 |

> **2026-07-23**: B-GD-1/2/3・B-LOG-1 は [hearing-checklist.md](../requirements/hearing-checklist.md) へ正式登録（別担当実施）。

---

## G. 業界事例・裏どり

| 参照 | 内容 |
|---|---|
| [RFC 9449 DPoP](https://datatracker.ietf.org/doc/html/rfc9449) | DPoP 標準（2023-09）|
| [RFC 8705 OAuth 2.0 Mutual-TLS Client Authentication](https://datatracker.ietf.org/doc/html/rfc8705) | mTLS Bound Access Token 標準 |
| [FAPI 2.0 Security Profile](https://openid.net/specs/fapi-security-profile-2_0-final.html) | 金融向け、DPoP / mTLS Bound Token 必須要件 |
| [CISA Alert AA20-352A](https://www.cisa.gov/news-events/cybersecurity-advisories/aa20-352a) | Golden SAML 対策公式ガイド |
| [Auth0 - Detecting Malicious Actor (Golden SAML)](https://auth0.com/blog/detecting-malicious-actors-with-adaptive-authentication/) | Adaptive Auth × Golden 系検知の実装例 |
| [Fluent Bit Filters - Modify + Lua](https://docs.fluentbit.io/manual/pipeline/filters) | Log scrubbing 実装リファレンス |
| [AWS CloudFront Log field masking](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/AccessLogs.html) | CloudFront 実装リファレンス |

---

## H. 反映先

### H.1 ドキュメント反映（本 ADR 作成時に同期反映）

- [doc/adr/00-index.md](00-index.md)：ADR-060 追加
- [doc/common/saml-vs-oidc-comparison.md §7.4.5 / §7.5.5](../common/saml-vs-oidc-comparison.md)：残 TBD 3 件を「ADR-060 で解消」に更新
- [ADR-034 §関連](034-adaptive-authentication.md)：本 ADR §C 参照追加
- [ADR-035 §関連](035-identity-threat-detection-response.md)：本 ADR §C 参照追加
- [ADR-045 §関連](045-cryptographic-key-management-strategy.md)：本 ADR §C 参照追加
- [ADR-053 §関連](053-observability-strategy.md)：本 ADR §A 参照追加
- [ADR-057 §I](057-csrf-protection-responsibility-boundary.md)：本 ADR §B 参照追加

### H.2 顧客 / RP ガイド（Phase 2 拡充）

- **RP 実装ガイド + DPoP SDK 提供**（Phase 2 で発生）
- **customer-doc/security.md**：Log scrubbing 説明 + Golden 系対応方針明示

### H.3 ヒアリング項目追加候補

上記 §F の B-LOG-1 / B-DPoP-1/2 / B-GD-1/2/3 を [hearing-checklist.md](../requirements/hearing-checklist.md) に登録。

---

## I. TBD / 要検討

- **B. mTLS Bound Token の CA 運用**：顧客ごとに CA 発行するか、共通 CA から Client Cert 配布か
- ~~**C. Golden 検知の False Positive 抑制**：初期チューニング期間の運用体制~~ → **2026-07-23 [D-U7-06](../basic-design/07-security-compliance-design.md) でクローズ**（Phase 1a = 検知通知のみ → FP < 5% で 1b 自動化）
- ~~**A. RP 側ログの Scrubbing 要件強制**：顧客に強制すべきか、推奨に留めるか~~ → **2026-07-23「推奨」で確定**（[U7 §7.3.1](../basic-design/07-security-compliance-design.md)）

---

## J. 関連 ADR / メモリ

- [ADR-034 Adaptive Authentication](034-adaptive-authentication.md)（§C 実装親）
- [ADR-035 ITDR](035-identity-threat-detection-response.md)（§C パイプライン親）
- [ADR-045 鍵管理戦略](045-cryptographic-key-management-strategy.md)（§C 緊急ローテ親）
- [ADR-053 Observability Strategy](053-observability-strategy.md)（§A 実装親）
- [ADR-057 CSRF 対策の責任分界](057-csrf-protection-responsibility-boundary.md)（§B 統合先）
- [saml-vs-oidc-comparison.md §7.4 / §7.5](../common/saml-vs-oidc-comparison.md)（本 ADR の起点）

---

**変更履歴**

| 日付 | 内容 |
|---|---|
| 2026-07-08 | 初版作成（§7.4 / §7.5 攻撃経路整理からの残 TBD 3 領域統合 ADR、A. Log scrubbing / B. Token Binding DPoP・mTLS / C. Adaptive Auth 連動 Golden 検知 6 シグナル）|
| 2026-07-08 | **§C.2.2 Golden LDAP 系シグナル L-GD-1〜L-GD-5 追加**（[ADR-025 §H.6 L-5 論点](025-scim-positioning-and-receive-stance.md) 波及、LDAP Bind Service Account 乗っ取り検知）+ §C.7 Phase 1 実装 TODO に Golden LDAP 系追記 + ヘッダ関連に ADR-025 §H 追加 |
| 2026-07-09 | **§C.2.3 last_login + provisioned_by 属性書込追加**（[jit-scim §10.4.A/B](../common/jit-scim-coexistence-keycloak.md) 波及、旧 §10.4 の event_entity 依存が 10M MAU で破綻することが判明したため、Event Listener SPI に last_login / provisioned_by 書込を統合。PCI DSS Req 8.2.6 90 日未使用無効化 + JIT/SCIM 判別ロジックの本番実装親 ADR となる）|
| 2026-07-10 | **§C.2.3 実機 PoC 結果反映：案 B（Custom Authenticator SPI）確定 + F-6 forms サブフロー配置制約追記**（[poc/jit-scim-verification-2026-07-10 実測](../../poc/jit-scim-verification-2026-07-10/) で V3' PASS + debounce 動作確認 + top-level 配置時のログイン失敗を実測、Terraform 実装例追加、[jit-scim §10.4.F](../common/jit-scim-coexistence-keycloak.md) と同期）|
| 2026-07-10 | **§C.2.3 F-9 フェデ JIT 経路制約追記**（V3' はローカル PW ユーザで検証、フェデ JIT ユーザ（本基盤主用途 P-3）は Browser Flow 分岐構造上動作しないことを判明。Phase 1 実装で Browser Flow + First Broker Login Flow + Post Broker Login Flow の 3 系統に SPI 配置が必須。追加 PoC V3'' 別端末で実施予定、[jit-scim §10.4.F.9](../common/jit-scim-coexistence-keycloak.md) と同期）|
| 2026-07-13 | **§C.2.3 F-9 V3'' 実測 PASS 反映 + 妥当性範囲を明記**（[verification-log-v3fed.md](../../poc/jit-scim-verification-2026-07-10/docs/verification-log-v3fed.md) T1-T5 全 PASS。フェデ JIT 経路で First/Post Broker Login Flow の SPI 発火を実測。ただし V3'' の外部 IdP は Keycloak モック（OIDC のみ）であり **SAML/LDAP/実 IdP は未検証** → B-SCIM-12（SAML）/ B-SCIM-13（LDAP、🚨 最優先）/ B-SCIM-14（実 IdP 統合）を Phase 1 リリース前ゲートに追加。新知見：初回時 First+Post 両 Flow 続けて発火 / JWT はブローカ再発行のみアプリ受領、[jit-scim §10.4.F.9](../common/jit-scim-coexistence-keycloak.md) と同期）|
| 2026-07-14 | **§C.2.3 Re-Activation SPI 統合追記**（LastLoginTracker SPI に Re-Activation ロジック統合、SCIM 除外条件 + local-admin 除外条件 + 想定外拒否の 3 段階分岐、危険な誤発火シナリオ明記、監査ログ USER_REACTIVATED 発行と ADR-035 ITDR 連携、Flow 配置主戦場は Post Broker Login Flow、[jit-scim §10.4.G/H/I/J](../common/jit-scim-coexistence-keycloak.md) と同期）|
| 2026-07-23 | **基本設計 U7 実装確定を反映**（① §A Log scrubbing 実装は [U7 §7.3](../basic-design/07-security-compliance-design.md) 参照、辞書 M-13 `logout_token` / M-14 Basic 認証ヘッダ追加 ② 「Access Token 15-30 分」表記 2 箇所を「30 分（U5 §5.2.1 確定）」へ ③ §C.2.1 Phase 1 実装 = G-2/G-3（簡易）/G-5/G-6 の 4 シグナル、統計学習系 G-1/G-4 は Phase 2（D-U7-08）④ §I 残課題 A =「推奨」で確定（U7 §7.3.1）/ 残課題 C = D-U7-06 でクローズ ⑤ §C.4 Medium 対応は U7 の L2「強制再認証」定義を正とする ⑥ §F B-GD-1/2/3・B-LOG-1 は hearing-checklist へ正式登録（別担当実施））|
