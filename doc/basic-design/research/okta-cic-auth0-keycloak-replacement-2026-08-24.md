# Okta CIC（Auth0）は Keycloak 2-tier の代替になるか — 2026-08 再確認

- **日付**: 2026-08-24
- **種別**: research note（プラットフォーム選定の再確認。[ADR-058 Alt 1](../../adr/058-auth-platform-alternatives-comparison.md) / [ADR-032](../../adr/032-ciam-platform-cost-comparison-10m-mau.md) の 2026 更新）
- **発端**: 「**Okta CIC** がブローカーか IdP もしくは両方で Keycloak の代わりにならないか」という問い合わせ。最新（2025〜2026）情報で再評価。
- **前提要件**: 自前ホスト（ROSA/AWS）Keycloak 2-tier = Broker（1000+ 顧客 IdP フェデ）+ IdP-KC（メール非保有ローカルユーザ収容）。10M MAU 上限（初回 100〜500 万）。データ主権（identity Aurora〔PW ハッシュ〕を自社 VPC に閉じ込め、[SRE 越境/G-DPA](rosa-sre-live-log-visibility-2026-08-14.md) を統制）。メール非依存の識別子先行 HRD（[ADR-055](../../adr/055-hrd-implementation-method-selection.md)）。
- **結論（先出し）**: **機能的には Broker/IdP の多くをこなせるが、"現行の自前ホスト運用モデルの全面代替" にはならない**。決定的理由 = **Okta CIC は SaaS/Okta 運用のみで self-host 不在**。加えてコスト（10-30 倍）・接続数課金（Broker 用途に最悪）・メール依存 HRD が本基盤要件と衝突。**ADR-058 Alt 1 の不採用判断は 2026 最新でも維持**。

---

## 1. 製品の実体

- Okta フラグシップは 2 系統：**WIC（Workforce＝従業員 IAM）** と **CIC（Customer Identity Cloud＝"powered by Auth0"）**。**CIC ＝ Auth0** で確定（2021 買収以降 Auth0 が CIC の基盤エンジン）。
- 出典: [Okta CIC 発表](https://www.okta.com/newsroom/press-releases/okta-introduces-okta-customer-identity-cloud-to-help-businesses-grow-user/)

## 2. デプロイ形態 = SaaS のみ（✕ の決定的理由）

- 提供形態は **① Public Cloud（マルチテナント SaaS）／② Private Cloud（シングルテナント専有だが Okta 運用、AWS/Azure）** の 2 つのみ。
- **Private Cloud も「Okta が運用する専有インスタンス」**。顧客 VPC へは PrivateLink で繋ぐが**サービス実体は Okta 側**。**顧客が自社 AWS/ROSA 上で self-host する製品は存在しない**。
- → **現行の「identity データを自社 VPC に閉じ込め自社統制」モデルは SaaS では原理的に不可**。むしろデータ主権は SaaS の方が弱く、APPI/越境の懸念は現状より悪化。
- 出典: [Auth0 Private Cloud](https://auth0.com/docs/private-cloud) / [AWS deployment](https://auth0.com/platform/cloud-deployment/aws)

## 3. Broker / IdP / 両方 の代替可否

| 役割 | 可否 | 決め手 |
|---|---|---|
| **Broker（1000+ 顧客 IdP フェデ）** | **△ 条件付き・摩擦大** | Enterprise で接続 "unlimited" だが、① 接続は MAU と別軸の**接続数課金**（公開上限 30）② **Org あたり接続 10 のハード上限** ③ Management API が接続/Org を 100〜1000 件でページング（1000+ テナント列挙に既知摩擦）④ **HRD がメールドメイン照合ベース**。**メール非依存の識別子先行 HRD は標準に無く Actions 自作前提** |
| **IdP（メール非保有ローカルユーザ）** | **○ 機能的に可能** | **Flexible Identifiers / Requires Username** で email 無し・username（社員番号）運用可。**Inbound SCIM は GA**（2026-04-28、/groups は Limited EA）。ただし Custom SPI 相当の深い認証カスタムが **Actions（Node.js・定義済みトリガー点のみ）** に収まるか要 PoC |
| **両方（自前ホスト運用モデル全体）** | **✕ 不可** | **Okta CIC は SaaS/Okta 運用のみ**（§2）。self-host という現行前提が成立しない |

出典: [Entity Limit Policy](https://auth0.com/docs/troubleshoot/customer-support/operational-policies/entity-limit-policy)（per-org 10 / Org 10万〜200万）/ [SAML 接続数サポート記事](https://support.auth0.com/center/s/article/Limit-to-the-Number-of-SAML-Connections-Created-Within-a-Tenant)（100 接続超ページング）/ [Identifier First HRD](https://auth0.com/docs/authenticate/login/auth0-universal-login/identifier-first)（メールドメイン照合）/ [Requires Username](https://support.auth0.com/center/s/article/Is-it-possible-to-create-users-using-username-and-password-instead-of-the-email-password-combination) / [Inbound SCIM GA](https://www.okta.com/blog/product-innovation/inbound-scim-for-okta-customer-identity-cloud-is-now-generally-available/) / [Actions で HRD 議論](https://community.auth0.com/t/identifier-first-login-rule-hook-action/131804)

## 4. コスト（歴史的な不採用理由・最新でも同じ）

| 規模 | Okta CIC（Auth0） | 自前 Keycloak |
|---|---|---|
| 100K MAU | ~$180K/年 | ~$18K/年 |
| 1M MAU | ~$300K+/年 | ~$36K/年 |
| **10M MAU** | **$1M〜$3M/年（要見積）** | ~$122K/年（ADR-058） |
| + Enterprise 接続 | 100 顧客で **+$200K〜$400K/年**（MAU と別枠） | — |

- **課金軸 = MAU + B2B は"接続数"が独立軸**。**公開プランは MAU も接続数（最大 30）も低上限で、本件は全レンジ要見積**。
- **損益分岐 = 1 万 MAU 超で Keycloak 有利**（二次情報の一致）。本基盤（数百万〜1000 万 MAU + 1000+ IdP）は **SaaS が最も不利な帯域**、かつ **Broker こそ接続数課金で高くつく用途**。
- ⚠ 数値はベンダー系ブログ/二次情報の**推定**（5M/10M は公開情報なし＝**完全要見積**）。方向性（SaaS が大規模で桁違い高コスト）は信頼できるが絶対額は参考値。
- 出典: [SSOJet growth-penalty](https://ssojet.com/blog/auth0-pricing-growth-penalty) / [SSOJet $34k SAML](https://ssojet.com/blog/why-does-auth0-charge-34k-yr-for-2-500-maus-to-enable-saml) / [Security Boulevard](https://securityboulevard.com/2025/09/auth0-pricing-explained-and-why-startups-call-it-a-growth-penalty/) / [KeycloakPro TCO](https://keycloakpro.com/blog/keycloak-vs-auth0-vs-okta-cost-comparison) / [Auth0 pricing](https://auth0.com/pricing)

## 5. 本基盤特有の追加の引っかかり（2026 新発見）

1. **⚠ Enterprise 認証 API 上限 = 100 RPS/tenant** — 10M MAU ピークログインで要交渉・要確認（[Rate Limit Policy](https://auth0.com/docs/policies/rate-limit-policy/database-connections-rate-limits)）。
2. **メール非依存 HRD が標準に無い** — 本基盤一級要件（工場系メール非保有）と衝突、Actions 自作でも深さ不確実。
3. **Private Cloud の東京（日本）可用性が未確定** — 2025 拡張は Mexico/HK/Calgary。Public Cloud には JP あり。データレジデンシー必須なら Okta 営業に直接確認要（[Public Cloud Endpoints](https://auth0.com/docs/troubleshoot/customer-support/operational-policies/public-cloud-service-endpoints) / [2025-07 更新](https://auth0.com/blog/july-2025-product-updates-new-security-features-global-regions-and-developer-previews/)）。
4. **Actions は Node.js・トリガー点限定** — Keycloak Custom SPI（認証フロー差し替え）と同等の自由度なし（Rules/Hooks は 2026-11-18 廃止）。

## 6. 再採用トリガーの状態

- [ADR-058](../../adr/058-auth-platform-alternatives-comparison.md) の再採用条件 = 「SaaS CIAM が 10M MAU で **$500K/年以下**」。2026 時点でも $1M〜$3M/年＋接続課金で**未達**。
- 加えて **self-host 不在・データ主権**は価格では解決しないため、**現状は再検討の閾値に達していない**。

## 7. 結論（問い合わせへの回答）

- **代わりになるか = 部分 Yes（機能）／全体 No（アーキテクチャ）**。
- **IdP 単体は機能的に成立**するが、**Broker は接続数課金・per-org 10・メール依存 HRD で摩擦大**、**両方＝自前ホスト運用モデルの全面代替は self-host 不在で不可**。
- **Okta CIC を選ぶ = Keycloak 2-tier の置換でなく "CIAM を SaaS 化する別アーキテクチャ移行"**（データ主権・コスト・カスタム深度を、マネージド DX と引き換えに手放す判断）。本基盤の確定方針（自社統制・低コスト・メール非保有・深い HRD）とは逆行。

## 8. 要一次確認 / 要見積（断定できていない点）

1. **5M/10M MAU の Auth0 実勢価格**（公開情報なし → 要見積）。
2. **1000+ エンタープライズ接続時の Auth0 単価**（30 接続超は非公開 → 要見積）。
3. **10M MAU / 1000+ IdP を単一テナントで収容可か**（Entity Limit・100 RPS 引き上げ可否 → 要 PoC/確認）。
4. **passkey/WebAuthn の GA 状況と email-less 併用可否**（一次未精読）。
5. **非メール HRD を Actions で実装した場合の実現度・限界**（公式標準に無く → 要 PoC）。
6. **Private Cloud 東京可用性**（未確定 → Okta 営業確認）。
7. コスト数値は二次情報の推定（絶対額は参考値、確定は実見積）。
