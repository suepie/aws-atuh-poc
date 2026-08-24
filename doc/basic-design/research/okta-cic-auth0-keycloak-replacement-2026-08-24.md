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

## 4A. 課金軸の全体像（何の単位で課金されるか・全軸）

**課金モデルの構造 = 「プラン基本料（MAU 階段式）＋ アドオン（同梱数超過・上位機能ゲート）」の二層**。2026-07-17 に公式 pricing が **B2C / B2B 別**に分離。**高度機能の多くは従量課金でなく「Enterprise プランゲート＋個別アドオン契約（＝単価非公開・要見積）」**。年額は月額×11（実質 1 ヶ月無料）。出典: [pricing.md](https://auth0.com/pricing.md)

### (1) 基本プランの課金軸（B2C / B2B）

| 課金軸 | 単位 | 無料枠 | 追加/超過単価 | 適用 |
|---|---|---|---|---|
| **MAU** | 月内に 1 回以上トークン発行した非内部ユーザーのユニーク user_id 数 | Free 25,000 MAU | B2C: Essentials $35(500)→$3,500(5万) / Pro $240→$3,200(2万)、以降 contact / **B2B は同 MAU で 3〜4 倍**（Essentials $150(500)→$3,800(2万)、$30,000+ で contact）| 両方 |
| **M2M トークン** | **月間発行トークン数**（クライアント数ではない）| Free/Essentials 1,000 / Pro 5,000 | B2C アドオン 7,500 tok $30/月 → 30 万 tok $1,200/月。B2B は 2,500 tok $10/月〜 | 両方 |
| **Enterprise Connections** | **外部 IdP 接続数/月**（SAML/OIDC/AD/LDAP）| Free 1 / Essentials 3 / Pro 5 同梱 | **$100/月/接続、公開上限 30**（超過は Enterprise 要見積） | **B2B のみ** |
| **Enterprise MFA** | 定額アドオン | — | Essentials $100/月 / Pro 同梱 | B2B |
| **Organizations（B2B テナント数）** | 組織数 | Free 5 | **数量課金なし**（実質 MAU と接続で課金。組織を増やす=課金ではない）| B2B |
| **AI Agents アドオン** | 定率上乗せ | — | **基本料 +50%** | 両方 |

### (2) Auth0 FGA（Fine-Grained Authorization）＝ 別製品・別契約（本体 MAU と独立）

本番は Enterprise 契約必須、**単価は全て非公開・要見積**。メータリングは複合軸: [出典](https://docs.fga.dev/subscription-plans)
- **保存 tuples 数**（relationship tuples、Free 5 万 / Enterprise 1,000 万〜追加購入）
- **FGA 側 MAU**（本体 MAU とは別カウント）
- **Stores 数**（Free 10 / Ent 20）
- **API レート**（Check/BatchCheck: Free 20→Ent 500 req/s、Write: 20→150 req/s）
- 「1 tuple/1 query いくら」の公開価格は**存在しない**。

### (3) アドオン／上位プランゲート（多くは非公開・要見積）

| 機能 | 課金形態 | 出典 |
|---|---|---|
| **Adaptive MFA** | Enterprise + アドオン必須（非公開） | [docs](https://auth0.com/docs/secure/multi-factor-authentication/adaptive-mfa) |
| **Highly Regulated Identity（FAPI/CIBA/顧客管理鍵）** | Enterprise + HRI アドオン必須（非公開） | [docs](https://auth0.com/docs/secure/highly-regulated-identity) |
| **Attack Protection（breached PW/brute force/bot）** | 標準だが bot 検知等は上位ゲート、単体従量なし | Auth0 資料 |
| **Custom Domains** | Free 1、拡張は上位プラン | [pricing.md](https://auth0.com/pricing.md) |
| **ログ保持** | プラン依存（Starter 1 日 / Essentials 5 日 / Pro 10 日 / **Enterprise 30 日**）。超過は Log Streaming で外部保管（**外部 SIEM 費は顧客別負担**） | [docs](https://auth0.com/docs/deploy-monitor/logs/log-data-retention) |
| **Private Cloud（専用デプロイ）** | Enterprise 限定・定額 dedicated（Basic/Performance 500RPS/Perf+ 1,500RPS）、**単価非公開**（第三者集計 年 $30,000〜は推測） | [G2](https://www.g2.com/products/auth0/pricing) |
| **Actions（拡張実行）** | 実行回数課金の明示記載なし（現状「従量なし」と推定） | 要確認 |

### (4) サポート/SLA・通信費（Auth0 請求外）

- **サポート**: Self Service は同梱 / **Premier Success（Basic 24x5・Silver/Gold 24/7）は有償・非公開**。99.99% SLA は Enterprise 付随。[出典](https://auth0.com/docs/troubleshoot/customer-support/support-plans)
- **⚠ SMS/音声（MFA・Passwordless）は Auth0 課金外＝ Twilio 等別契約・顧客負担**（目安 $0.0083/SMS+キャリア費。10 万ユーザー×月1通で $830+/月 の想定外コスト）。[出典](https://auth0.com/docs/secure/multi-factor-authentication/multi-factor-authentication-factors/configure-sms-voice-notifications-mfa)

### (5) MAU の数え方（確定事実）

- **定義 = 月内にトークン発行した非内部ユーザーのユニーク数**。**リフレッシュトークンは非カウント**。**同一 user_id が複数アプリ/複数トークンでも月内 1 MAU**。B2C/B2B で数え方は同じ（料金と同梱物が違う）。[出典](https://auth0.com/blog/auth0-monthly-active-user-mau-explained/)

### (6) 見落としやすい「隠れ課金軸」

1. **M2M は"発行トークン数"課金**（クライアント数でない）→ マイクロサービス/サーバーレスで急増、同梱 1,000 を即枯渇。
2. **同 MAU でも B2B は B2C の 3〜4 倍**。ユースケース判定で跳ねる。
3. **Enterprise Connections 公開上限 30 → 超過は強制 Enterprise 要見積**。**本件 1000+ IdP は $100/月×多数で破綻的**、かつ接続は MAU と別軸。
4. **SMS/音声は Twilio 別請求**（Auth0 請求に出ない想定外コストの筆頭）。
5. **ログ保持 最短 1 日〜最長 30 日**、長期は外部 SIEM 別課金。
6. **Adaptive MFA / HRI(FAPI) / Private Cloud は全て Enterprise+個別アドオンで非公開見積**（予算化困難）。
7. **AI Agents アドオンは基本料 +50%** の定率上乗せ。
8. **FGA は完全別製品・別契約**（tuples/MAU/stores/レートの複合、全て非公開）。
9. **無料 MAU 枠の表記揺れ**（現行 pricing.md は 25,000、旧資料は 7,500）→ 契約時点で要確認。
10. **年額＝月額×11 の一括前払い**。

> **本基盤への含意**: 課金軸が **MAU・M2M トークン・接続数・FGA・各アドオン・外部通信費** と多層で、**どれも大規模で効いてくる**。特に **① 接続数課金（1000+ IdP の Broker 用途と致命的不整合）② B2B 割増 ③ 高度機能が全て Enterprise 非公開見積** の 3 点で、**MAU 単価だけ見た試算より実 TCO は大きく膨らむ**。確定額は Auth0 営業の実見積が必須。

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
