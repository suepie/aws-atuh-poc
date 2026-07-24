# U7: セキュリティ・コンプライアンス設計

作成日: 2026-07-23
ステータス: Draft v1（Wave 2）
**前提: [01-architecture-baseline.md](01-architecture-baseline.md) Baseline v1（P-01〜P-18、特に P-03 / P-17 / P-18）**
上位文書: [00-basic-design-plan.md](00-basic-design-plan.md) §U7

---

## 7.0 背景・なぜここで決めるか・スコープ

### 7.0.1 背景

要件定義フェーズでセキュリティ関連の方針は ADR 群として確定済みである — 鍵管理 3 階層（[ADR-045](../adr/045-cryptographic-key-management-strategy.md)）/ ITDR（[ADR-035](../adr/035-identity-threat-detection-response.md)）/ Adaptive（[ADR-034](../adr/034-adaptive-authentication.md)）/ Bot（[ADR-042](../adr/042-bot-detection-captcha.md)）/ Workload Identity（[ADR-041](../adr/041-workload-identity-spiffe.md)、2026-07-23 ROSA IRSA 化）/ Supply Chain（[ADR-046](../adr/046-supply-chain-security.md)）/ CSRF 分界（[ADR-057](../adr/057-csrf-protection-responsibility-boundary.md)）/ Log scrubbing・Golden 検知（[ADR-060](../adr/060-auth-protocol-attack-path-residual-tbd.md)）。しかし各 ADR は旧前提（EKS / 5 アカウント / Auth Platform Acct 単一）で書かれており、Wave 1 で確定した **ROSA HCP × 2 クラスタ（P-17）/ 6 アカウント体系（U6 D-U6-01）/ 他組織管理のインターネット境界（P-18）** の上での実装形が未確定だった。本書は方針 ADR を Wave 1 の物理構成に写像し、命名・閾値・配置・Phase 1 実装範囲を確定する。

さらに本書には次の 3 つの「他単元からの引き渡し」への回答責務がある:

1. **[ADR-040 PAM](../adr/040-pam-jit-admin-privilege-management.md) の復活取込**（2026-07-23 Accepted 復帰、Phase 1 α/β・10 名体制・Break-Glass）: 運用体制側で確定した PAM 設計と本基盤側（Keycloak Composite Role / /admin 経路 / 監査ログ集約）の接続を確定する（U1 §1.4 残タスク「ADR-040 OOS 残存参照の整理」の解消を含む）。[ADR-036](../adr/036-customer-audit-support.md)（同日更新: Phase 1 α/β サポート体制明示）とも同期する。
2. **U6 §6.3.2 からの引き渡し**: 2-tier クライアント認証の `private_key_jwt` / mTLS 昇格判断を「Secrets ローテーション設計とセットで時期確定」する（§7.5.3）。
3. **U6 O-10 zero-egress 案の評価**: セキュリティ / PCI / サプライチェーン統制の観点評価を本書で確定し、最終決定（先方 TGW 接続可否等）を U6 に返す（§7.7.5）。
4. **U6 §6.5.4 からの引き渡し**: Argon2id セキュリティパラメータ選定（§7.8.2）。

### 7.0.2 本書の構造原則 — P-18 による 2 部分離（U6 と整合）

P-18 により WAF / Bot Control / ATP / DDoS / Network Firewall はすべて**他組織管理の NW 監査 Acct** にあり、我々は実装できない。U6 の 2 部構成（A 部 = 自管理 / B 部 = 要求仕様）を本書でも貫徹する:

| 区分 | 本書での扱い | 例 |
|---|---|---|
| **自管理側（保証する）** | 本書 §7.1〜§7.6 + §7.8.2 で実装設計 | KMS / ITDR / Log scrubbing / Golden 検知 / IRSA / PAM / Keycloak Brute Force |
| **他組織への要求（保証しない）** | U6 §6.7 の REQ 体系に**追補要求として登録**（本書は要求内容の確定のみ） | WAF Bot Control・ATP（REQ-IN-01 内訳）/ CloudFront ログのマスキング条件（REQ-IN-10 新規）/ ATP ログ共有（REQ-OUT-05 新規） |

U6 §6.0.2 の生命線原則をセキュリティ面でも適用する: **B 部（他組織要求）が満たされなくても A 部単独で「破られない」最低線を持つ**（例: WAF ATP がなくても Keycloak Brute Force + ITDR で Credential Stuffing の最低防御線は成立、§7.8）。

### 7.0.3 スコープ / 非スコープ

| 領域 | 本書（U7） | 他単元 |
|---|---|---|
| KMS 3 階層 CMK の命名・Key Policy・ローテーション・MRK | ✅ 決定 | IaC 実装は U9 |
| ES256 Realm 署名鍵の管理方式・Cryptoperiod 運用 | ✅ 決定 | JWKS キャッシュ整合の RP 案内は U5 §5.6.3 |
| ITDR Phase 1 実装（パイプライン・閾値・誤検知運用） | ✅ 決定 | L4 の実行 API 面は U5 §5.4.3（確定済み・参照） |
| Log scrubbing（配置・辞書・監査スキャン） | ✅ 決定 | Dashboard / Runbook 実装は U9 |
| Golden 検知 G-1〜G-6 の Phase 1 範囲 | ✅ 決定 | Event Listener SPI の Flow 配置は U2（確定済み・参照） |
| Workload Identity（IRSA Role 設計 / FedID / 昇格判断） | ✅ 決定 | Terraform 実装は U9 |
| PAM 統合（ADR-040 ↔ 本基盤の接続点） | ✅ 決定 | 運用体制・採用・On-Call 詳細は ADR-040 §G〜§I（SSOT、本書は接続のみ） |
| PCI DSS ギャップ 3 点 + APPI の実装計画 | ✅ 決定 | 契約条項・法務レビューは法務、Runbook は U9 |
| Bot / DDoS の自管理・他組織分離 | ✅ 決定 | REQ 交渉・受入確認は U6 §6.7.4 プロセス |
| WAF ルール実装・ペネトレ実施計画詳細 | ❌ | 他組織（要求のみ）/ U9・Phase 1 実装時 |

### 7.0.4 前提（Baseline v1 からの主参照）

- **P-03 FIPS 140-2 不要（暫定）**: Argon2id 維持・upstream 互換の暗号構成でよい。FIPS 化に転じた場合は §7.8.2 と ADR-045 §C を全面再評価（RHBK FIPS モードで転換コスト小、[01 §1.1](01-architecture-baseline.md)）。
- **P-17**: Broker Acct / IdP-KC Acct の 2 アカウント × ROSA HCP 2 クラスタ。CMK・IRSA・ITDR の配置はすべてこの分割前提（旧 ADR の「Auth Platform Acct」表記は本書で読み替え確定）。
- **P-18**: インターネット境界は他組織管理。§7.0.2 の 2 部分離。

---

## 7.1 KMS 3 階層 CMK 実装設計

### 7.1.1 決定 D-U7-01: CMK 命名規則と配置（6 アカウント体系への写像）

**採用**: ADR-045 の 3 階層モデル（L1 基盤共通 / L2 アカウント別 / L3 テナント別)を維持し、alias 命名規則を **`alias/<scope>-<purpose>[-mrk]`**（scope = `org` | `broker` | `idpkc` | `audit`）で確定する。旧「Auth Acct」配置鍵は Broker / IdP-KC へ分割配置する。

**Phase 1 CMK 初期セット**:

| Alias | 階層 | 配置 Acct | 用途 | Key Spec | MRK（大阪） |
|---|---|---|---|---|:---:|
| `alias/audit-logs-mrk` | L1 | 監査 | 全 Acct 監査ログ S3（Object Lock 7 年）+ OpenSearch | SYMMETRIC | ✅ |
| `alias/org-cloudtrail-mrk` | L1 | 監査 | CloudTrail Organization Trail | SYMMETRIC | ✅ |
| `alias/broker-breakglass` | L1 | Broker | Break-Glass クレデンシャル Secrets（ADR-040 §C） | SYMMETRIC | ❌ Regional（DR 側は大阪 Acct 内で別鍵 + 物理金庫、§7.9.2） |
| `alias/broker-aurora-mrk` | L2 | Broker | Broker KC Aurora（Global DB） | SYMMETRIC | ✅ |
| `alias/idpkc-aurora-mrk` | L2 | IdP-KC | IdP-KC Aurora（**PW ハッシュ保有**、ADR-033 §D-1） | SYMMETRIC | ✅ |
| `alias/broker-idmap-mrk` | L2 | Broker | idmap 補助 DB（U6 §6.4.1）※ Broker Aurora 別 DB 同居中は broker-aurora-mrk に統合可 | SYMMETRIC | ✅ |
| `alias/broker-itdr` | L2 | Broker | ITDR DynamoDB（履歴・Risk Score） | SYMMETRIC | ❌（DR 方式は U8、§7.9.2） |
| `alias/broker-secrets` / `alias/idpkc-secrets` | L2 | 各 | Secrets Manager（client_secret / SCIM Bearer / HIBP API Key 等） | SYMMETRIC | ❌ |
| `alias/broker-s3` / `alias/idpkc-s3` | L2 | 各 | 各 Acct S3（SPA bundle / 一時領域） | SYMMETRIC | ❌ |
| `alias/tenant-<alias>-mrk` | L3 | Broker | 大規模・規制業種テナントのみ（B-KMS-3 確認後） | SYMMETRIC | ✅ |

- **根拠**: ADR-045 §A（3 階層）、P-17（Acct 分割 = ブラスト半径分離。**IdP-KC 侵害時に Broker 側 CMK へ到達できない**ことを D-U6-02「Broker↔IdP-KC 間 IAM Role なし」と併せて構造保証）、ADR-051/P-05（Aurora Global DB は MRK 必須）。
- **代替**: ① 全鍵 MRK 化 — Break-Glass / Secrets 系は Region 内完結が望ましく（漏洩時の影響を東京に限定）不採用。② 旧 ADR-045 の Auth Acct 単一配置維持 — P-17 と矛盾するため不採用。
- **未決**: L3 テナント別 CMK の対象顧客（B-KMS-3 ヒアリング待ち、Phase 1 は L2 共通で開始）。

### 7.1.2 決定 D-U7-02: Key Policy — Key Administrator / Key User / Auditor の SoD

**採用**: 全 CMK の Key Policy を次の 3 ロール構造で統一し、Terraform モジュール（U9）でテンプレート化する。

| ロール | 担当（ADR-040 10 名体制への割当） | 許可 Action | 制約 |
|---|---|---|---|
| **Key Administrator** | **Security Lead + Infra Lead の 2 名**（= Key Custodian、ADR-045 §D.4 の最低 2 名要件） | CreateKey / ScheduleKeyDeletion / DisableKey / PutKeyPolicy / Alias / Tag | `aws:MultiFactorAuthPresent=true` 必須 + **Encrypt/Decrypt 系は付与しない**（SoD）+ 操作は IIC JIT 昇格経由のみ（§7.6.2） |
| **Key User** | サービス Role（IRSA Role、§7.5.1）のみ | Encrypt / Decrypt / GenerateDataKey / ReEncrypt / DescribeKey | Resource を使用 CMK に限定（ワイルドカード禁止）。**人間 Principal への Key User 付与禁止** |
| **Auditor** | Security チーム Read-Only Role | List / Describe + CloudTrail 閲覧 | 監査 Acct 経由 |

- クロスアカウント許可は ADR-045 §F の方式を踏襲: `audit-logs-mrk` のみ Broker / IdP-KC の書込 Role（`kms:Encrypt`/`GenerateDataKey` 系）を Key Policy で許可（D-U6-02 経路 1/2 と対）。**他組織 Acct への Key 共有はゼロ**（P-18、IAM 信頼を持たない原則 D-U6-02 #4）。
- Key Custodian Agreement（書面、ADR-045 §D.4）は Phase 1 T-4 までに法務レビュー完了（ADR-040 P1-09 Break-Glass 手配と同時期）。離職時は Key Policy から即日削除 + 監査記録。
- KMS 監視（`ScheduleKeyDeletion` / `PutKeyPolicy` / `DisableKey` = High 即時通知等）は ADR-045 §G.1 の表を初期値としてそのまま採用し、通知は ITDR の SNS 系統（§7.2）に統合する。
- **根拠**: PCI DSS §3.6.1.4 / §3.7.7（SoD）、ADR-045 §E。
- **代替**: Key Administrator を CISO 専任部門とする案（ADR-045 原文）— Phase 1 は 10 名体制（ADR-040 §H）に CISO 部門が存在しないため、Security Lead + Infra Lead のクロス担当に読み替え。組織拡大時に専任へ移管。
- **未決**: なし。

### 7.1.3 決定 D-U7-03: ES256 JWT 署名鍵 — Keycloak Realm Key 管理 + 90 日 Cryptoperiod

**採用**: JWT 署名鍵（ES256、P-09）は **Keycloak 標準の Realm Keys（DB 保管の generated key）** で管理し、KMS には持ち込まない。保護は多層で行う:

| 層 | 実装 |
|---|---|
| 保管 | Realm Key（秘密鍵）は Broker Aurora 内 → `broker-aurora-mrk` で at-rest 暗号化（Envelope） |
| ローテーション | **90 日 Cryptoperiod**（ADR-045 §D.4）: 新鍵生成 → active 切替（sign = 新鍵のみ）→ 旧鍵は passive（verify のみ）で **30 日並走** → 無効化。Keycloak Admin API + CronJob（U9 実装、実行 Role は IRSA） |
| 緊急ローテ | Golden 検知 Critical（§7.4）発火時: 並走なしで旧鍵即時無効化 + not-before push（U5 §5.4.3）+ 全 RP へ JWKS 再取得注意喚起。SOP は U9 Runbook（B-GD-3 で承認体制確定） |
| RP 側整合 | JWKS キャッシュは `kid` ベースで新鍵へ追従（U5 §5.6.3 検証 6 点 #1）。並走 30 日 > RP キャッシュ TTL を保証 |
| DB ダンプ対策 | IdP-KC 側 Realm Key も同様（IdP-KC は 2-tier 内部トークンの署名のみ、アプリ向けトークンは Broker 再発行 — ADR-033）。MFA Secret 等のアプリ層追加暗号化（ADR-045 §B.2）は Phase 1 実装対象 |

- **根拠**: ADR-045 §D.4（90 日は Auth0/Okta 業界標準・QSA 説明容易・Golden JWT 被害範囲 1/4）。PCI DSS Req 3 は PAN 保護鍵が対象で JWT 署名鍵は literal 対象外の可能性大だが「CDE セキュリティに影響する鍵」として同等管理（[reference/pci-dss-v401 §6.4](../reference/pci-dss-v401-scope-for-auth-platform.md)、QSA 事前確認は Phase 1 β 監査準備時）。
- **代替**: ① KMS Asymmetric CMK で署名（Keycloak から KMS Sign API を呼ぶ Custom SPI）— 秘密鍵の非流出性は最強だが、**Keycloak に該当機能がなく Custom KeyProvider SPI 開発 + 全署名操作の KMS RTT 加算 + G-SPI-Compat 対象増**で Phase 1 過剰。Golden 検知 + 90 日ローテで残余リスクを受容し、金融顧客要件が出た場合の Phase 2 再評価とする（ADR-045 の `alias/keycloak-jwt-signing` は本決定により**予約のみ・Phase 1 未作成**）。② HSM（CloudHSM）— ADR-045 §H の通り Phase 2 規制業種要求時のみ。
- **未決**: KMS 署名 SPI の Phase 2 判断トリガー（金融顧客 / FAPI 要件）。§7.9.1 O-U7-1。

---

## 7.2 ITDR 実装設計（Phase 1 = Compromised Credentials + Brute Force）

### 7.2.1 決定 D-U7-04: パイプライン構成と配置

**採用**: ADR-035 §D のパイプラインを次の配置で確定する:

```
[Broker KC / IdP-KC]                       [Broker Acct]
 Event Listener SPI ──emit──> EventBridge ──> Risk Engine Lambda ──> DynamoDB（履歴・スコア）
 （EventBridge PutEvents のみ）  itdr-bus        │                      broker-itdr CMK
                                              ├─> SNS → Slack / (Phase 1 β: PagerDuty)
                                              ├─> CloudWatch Logs（SoR）→ 監査 Acct S3（§7.7.1）
                                              └─> Response Action → KC Admin API（L2〜L4）
```

| 項目 | 決定 |
|---|---|
| SPI 責務分離 | **Event Listener SPI = EventBridge emit のみ**。`last_login` / `provisioned_by` / Re-Activation 等の属性書込は Custom Authenticator SPI（U2/U3 確定済み、PoC F-6 / ADR-060 §C.2.3）。同一 JAR に混載しない |
| 集約先 | **Risk Engine / DynamoDB は Broker Acct に一元配置**。IdP-KC 側イベント（ローカル PW ログイン = Brute Force の主戦場）は **EventBridge クロスアカウント PutEvents** で Broker Acct itdr-bus へ送る |
| クロスアカウント経路 | D-U6-02 の 5 経路に「**IdP-KC → Broker: ITDR イベント（PutEvents のみ）**」を第 6 経路として追加することを U6 に差分要求（既存経路 5〔idmap〕と同一方式のため増分リスク小）。→ §7.9.3 U6 引き渡し |
| Response Action の経路 | Lambda → Broker KC Admin API は Broker Acct 内完結。**IdP-KC への Response（ローカルユーザの lockout 等）は IdP-KC の Keycloak Brute Force 標準機能に委ね、クロスアカウントの Admin API 逆流経路は作らない**（PrivateLink 単方向原則 D-U6-06 の維持） |
| SIEM 連携 | Phase 5（顧客要件次第、OCSF 第一）。Phase 1 は監査 Acct 集約のみ |

- **根拠**: ADR-035 §D、ADR-060 §C.3、P-17（片方向原則）。Layer A（Broker）にユーザ主キーがあり相関分析は Broker 側が自然。
- **代替**: 各 Acct に Risk Engine を二重配置 — 履歴 DB が分裂し Impossible Travel 等の将来拡張（Phase 2）で相関不能になるため不採用。
- **未決**: IdP-KC ローカルロックアウトと Broker 側スコアの整合（ロック中ユーザのフェデ経路試行の扱い）は Phase 1b チューニングで評価。

### 7.2.2 決定 D-U7-05: Phase 1 検知範囲と閾値初期値

**採用**: Phase 1 は ADR-035 §H の通り **Compromised Credentials（HIBP）+ Brute Force** の 2 領域に限定し、初期閾値を次で確定する:

| 検知 | 実装 | 閾値初期値 | 対応レベル |
|---|---|---|---|
| Brute Force（アカウント単位） | **Keycloak 標準 Brute Force Detection（両 Realm で有効化）** | 連続 5 失敗で一時ロック 30 分（§NFR-4.3 ベースライン）。permanent lockout は使わない（DoS 化防止） | L1 記録 + ロック（KC 内完結）。ロックイベントは SPI 経由で Risk Engine へ |
| Brute Force（横断パターン） | Risk Engine: 同一 IP から異なる `username` への失敗集中（Password Spraying） | **同一 IP・10 分間に 10 ユーザ以上で失敗 → 警戒（L1+通知）/ 30 ユーザ以上 → L3 相当通知**（Phase 1a は通知のみ、遮断は WAF 側要求 §7.8） | L1 → 運用者判断 |
| Compromised Credentials | **HIBP Pwned Passwords（k-Anonymity API、SHA-1 プレフィックス 5 桁送信のみ）** を①ローカル PW ログイン成功時 ②PW 設定/変更時に照会（IdP-KC + Broker のローカル管理者） | ヒット = 侵害 PW | ①ログイン時ヒット → **L2 強制再認証 + PW 変更強制 + ユーザ通知** ②設定時ヒット → 設定拒否 |
| リスクスコア帯 | ADR-060 §C.4 準拠 | Low 0-30 / Medium 31-60 / High 61-80 / Critical 81-100 | L1 / L2 / L3 / L4 |

- 対応レベルの実行面: **L2** = Forced Re-authentication（KC セッション削除 → 次アクセスで再認証）、**L3** = 対象ユーザの全セッション削除 + RT 失効 + 一時ロック + 管理者通知（U5 §5.4.2 個別ユーザ API と同一）、**L4** = U5 §5.4.3 の確定手順（not-before push + 全セッション削除 + Back-Channel Logout 一斉送信 + **AT ゾンビ窓 ≤30 分の追加監視**）。L4 発動は Phase 1 では**手動承認必須**（on-call 判断、自動化は Phase 2 以降）。
- HIBP の Egress: `api.pwnedpasswords.com` の REQ-OUT-01 への FQDN 追加に加え、**送信元スコープに IdP-KC KC Pod CIDR を追加する要求（適用範囲拡張。REQ-OUT-01 の送信元は Broker KC CIDR で定義されているため）を含める**（U6 引き渡し）。**zero-egress 案 B（U6 O-10）採用時も HIBP は実行時 Egress であり ECR ミラーの代替対象外**。API 障害時は **fail-open（照会スキップ + メトリクス記録）**とし、ログイン可用性を優先（照会は k-Anonymity のため PW 平文・フルハッシュは送信されない）。
- **根拠**: ADR-035 §H Phase 1、NIST SP 800-63B Rev 4（侵害クレデンシャル検出必須化）、フェデ主体（P-07 γ）の本基盤では PW 面が小さく 2 領域で費用対効果最大。
- **代替**: Phase 1 から Anomaly Login（GeoIP / Impossible Travel）— GeoIP データ整備・ベースライン学習が必要で、ADR-035 の段階導入（Phase 2 = +6 ヶ月）を維持。
- **未決**: 閾値の最終値（B-ITDR-6 FP 許容範囲・B-GD-1）。テナント別閾値カスタマイズ（ADR-034 §C）は Phase 2。

### 7.2.3 決定 D-U7-06: 誤検知（False Positive）運用

**採用**: ADR-060 §D.3 の段階活性化を ITDR 全体の運用原則として確定する:

| 期間 | モード | 内容 |
|---|---|---|
| Phase 1a（リリース〜+3 ヶ月） | **検知・通知のみ**（L2 以上の自動アクションは HIBP ヒット時 PW 変更強制のみ有効） | 全シグナルを DynamoDB + Slack に記録。週次で FP レビュー（Security Lead 主催、ADR-040 §H チーム C） |
| Phase 1b（+3 ヶ月〜） | **自動アクション有効化**（L2/L3） | FP 率 < 5%（週次レビュー実測）を有効化条件とする。シグナル単位で個別に有効化 |
| 常設 | 除外リスト | 検証済み送信元（監視 synthetic / 負荷試験）の allowlist を IaC 管理 + 四半期棚卸し |
| 常設 | DR/Game Day ウィンドウ | **DR フェイルオーバー / Game Day 実施ウィンドウ（RB-DR-00 宣言〜完了 + 2h）は G-2/G-3 を通知のみへ自動降格（抑制フラグは Runbook 組込、U8 §8.7 / U9）。同ウィンドウ中は Brute Force 検知感度を一段引上げ（U8 §8.5.3 の受領）** |
| 救済経路 | 誤ロック解除 | テナント管理者（ユーザ管理画面、3 層スコープ内）or 基盤運用者。解除操作は監査ログ必須 |

- ITDR 自体の閾値・除外リスト変更は**通常の IaC 変更管理（PR + レビュー）**とし、緊急時のみ運用者直接変更 + 事後 PR（操作は §7.6 の JIT 昇格範囲）。
- **根拠**: ADR-060 §D.3（3 ヶ月チューニング後に自動遮断）、基本方針「効率よく認証」（FP による UX 破壊防止）。
- **代替**: リリース時から全自動遮断 — 初期ベースライン不在で FP 多発が確実、不採用。
- **未決**: Phase 1b 移行判定の合否基準精緻化（B-GD-2）。

---

## 7.3 Log scrubbing（ADR-060 §A の実装確定)

### 7.3.1 決定 D-U7-07: 収集段マスキング 2 段構え + ROSA 配置

**採用**: 「**収集段マスク（主）+ 保存後スキャン（漏れ検知）**」の 2 段構え（ADR-060 §A.4)を、ROSA HCP の Machine Pool 役割分離（U6 D-U6-04）に合わせて次の配置で確定する:

| ログソース | 実装 | 配置 / 備考 |
|---|---|---|
| Keycloak Container stdout（両クラスタ） | **Fluent Bit DaemonSet（全ノード、軽量 collector。DaemonSet は KC Pool の taint〔`dedicated=keycloak:NoSchedule`、U6 §6.2.2〕への toleration 必須）→ Fluent Bit Aggregator（マスキング Filter 集中）→ CloudWatch Logs / 監査 Acct S3** | **Aggregator は default（infra）Pool に Deployment 配置**（KC Pool のバーストとリソース分離、U6 D-U6-04 の原則）。マスク処理の CPU を KC に食わせない |
| Internal ALB access log | S3 → EventBridge → **マスキング Lambda** → OpenSearch/S3（監査 Acct） | Broker / IdP-KC 各 Acct |
| CloudWatch Logs（Lambda / SCIM Facade / API 層） | Subscription Filter → マスキング Lambda | 同上 |
| **CloudFront access log（他組織管理）** | **B 部要求（REQ-IN-10 新規提案)**: ① 認証系ディストリビューションの OriginRequestPolicy/ログ設定で query string 記録を最小化（`code`/`state` 等が残らない設定）② ログを弊社監査 Acct へ配信する場合は S3 到達後に弊社 Lambda でマスク | P-18 帰結。**先方が未対応でも自管理側 2 層（ALB/KC）でトークン系は遮蔽される**が、認可 code が CF ログに残る余地は先方対応が必要 → 要求必須と位置付け |
| RP / アプリ側ログ | RP 実装ガイド（U5 §5.6）にマスキングパターン集を添付・**推奨** | 顧客責任（ADR-060 §I の「強制か推奨か」は推奨で確定 — 強制は検証手段がなく実効性がない） |

**マスキング辞書 初期セット**（ADR-060 §A.3 を基礎に本基盤固有分を追加。正規表現は IaC で一元管理し全レイヤ共通適用）:

| # | 対象 | パターン概要 |
|---|---|---|
| M-1〜3 | SAML | `SAMLResponse=` / `SAMLRequest=` / `RelayState=` → `[REDACTED]` |
| M-4〜6 | OIDC 認可 | `code=` / `code_verifier=` / `state=` |
| M-7〜10 | トークン | `Bearer eyJ…` / `access_token=` / `refresh_token=` / `id_token=` |
| M-11 | Cookie | `KEYCLOAK_SESSION` / `KEYCLOAK_IDENTITY` / `AUTH_SESSION_ID` 値 |
| M-12 | SCIM | `Authorization:` ヘッダ全般（SCIM Bearer Token、ADR-025 §I.1 経路） |
| M-13 | Logout | `logout_token=`（Back-Channel Logout、U5 §5.5.4 で新規に流れるため追加） |
| M-14 | Basic 認証 | `Authorization: Basic …`（client_secret_post 移行前の残存対策） |

**監査スキャン**: OpenSearch 定期クエリ（`Bearer eyJ` / `SAMLResponse=` / `code=` / `logout_token=`）を**週 1** 実行（U9 で Dashboard 化）。検出時 SOP: ①該当トークンの強制 Revocation + 対象ユーザ再認証（U5 §5.4）②マスク漏れパターンを辞書に追加 → IaC PR ③件数を CloudWatch Metrics（`log_scrubbing_leak_count`、目標 0）。マスク処理件数もメトリクス化し、**突然のゼロ件はパイプライン故障のアラート条件**とする（マスク失敗 = 平文流出の予兆）。

- **根拠**: ADR-060 §A（SAML P11 + OIDC O22 対応、収集段が全ソース横断で統一可能）、U5 §5.1.4 C-6（トークンペイロードのログ非出力）と同一線。
- **代替**: Keycloak 書込前マスクのみ — KC 内部実装依存で網羅不能（ADR-060 §A.4）、補助に留める。OpenShift Cluster Logging（Vector）への乗り換え — マスキング Filter 資産（ADR-060 §A.7 の Fluent Bit 設定・PoC 資産）流用と upstream 情報量を優先し Phase 1 は Fluent Bit。運用中に Operator 管理の利点が上回れば U9 で再評価。
- **未決**: B-LOG-1（マスク対象の追加要否、Compliance ヒアリング）。REQ-IN-10 の先方回答。

---

## 7.4 Golden 検知 G-1〜G-6 の Phase 1 実装範囲

### 7.4.1 決定 D-U7-08: Phase 1 = ルールベース 4 シグナル、統計モデル系は Phase 2

**採用**: ADR-060 §C.2.1 の 6 シグナルを「ベースライン学習の要否」で分割する:

| シグナル | 内容 | Phase 1 | 理由 |
|---|---|:---:|---|
| **G-2** 短時間大量発行 | 1 分 100 件超で警戒 / 1000 件超で Critical（初期値、B-GD-1） | ✅ | 単純カウント。Risk Engine の集計で実装可 |
| **G-3** 通常時間帯外の署名操作 | 深夜帯（初期値: JST 1:00-5:00）の発行レート急増（平常時中央値の 10 倍超で警戒） | ✅（簡易ルール版） | 固定時間帯ルールで開始、分布ベースは Phase 2 |
| **G-5** JWKS 鍵の異常使用 | 廃止済み `kid` の再登場 / 未知 `kid` / `kid` 未指定 | ✅ | ローテ履歴（§7.1.3）との照合のみ。**90 日ローテ運用と表裏一体のため Phase 1 必須** |
| **G-6** 認証イベントなしの AT 発行 | CODE_TO_TOKEN に対応する LOGIN/SSO イベントが存在しない発行 | ✅ | イベント相関（同一 session 内照合）。Golden JWT の最直接シグナル |
| G-1 異常な sub/aud 分布 | 発行分布の統計モデル逸脱 | ⬜ Phase 2 | ベースライン学習（3 ヶ月以上の履歴）が前提 |
| G-4 異常地理 IP + 未知デバイス | GeoIP + Device Fingerprint | ⬜ Phase 2 | ITDR Anomaly Login（Phase 2）のデータ基盤と同時導入 |
| L-GD-1〜5（Golden LDAP） | LDAP Bind Service Account 乗っ取り | ⬜ 条件付き | **LDAP 顧客の受入（B-SCIM-13 ゲート通過）と同時に有効化**。VPC Flow Log + REQ-OUT-03（先方 NFW Alert ログ共有）が入力 |

- 発火時の対応: 警戒（High 相当）= SOC 通知 + 手動調査 / **Critical = §7.1.3 の緊急鍵ローテ SOP + U5 §5.4.3 L4 手順**。Phase 1a は通知のみ → Phase 1b で G-2/G-5 の自動 L4 連動を判断（D-U7-06 と同じ段階活性化）。
- Event Listener SPI の emit 対象イベント（CODE_TO_TOKEN / REFRESH_TOKEN / CLIENT_LOGIN / LOGIN / LOGIN_ERROR / TOKEN_EXCHANGE / USER_REACTIVATED / **`REVOKE_GRANT` / `LOGOUT` 系（revoke・ログアウト監査 — U5 §5.9.2 の依頼受領）**）は U2 の SPI 仕様に反映済み前提（ADR-060 §C.5、U5 §5.9.2 の監査イベントも同梱）。
- **根拠**: ADR-060 §C（Golden 系は「検知 + 影響最小化」しかできない完全防御不可経路）。90 日 Cryptoperiod（§7.1.3）との組で被害ウィンドウを最大 90 日 → 実質「検知までの分単位」に短縮するのが設計意図。
- **代替**: Phase 1 で 6 シグナル全実装 — G-1/G-4 は学習データなしでは FP 源泉にしかならず、段階導入が合理的。
- **未決**: G-2/G-3 閾値の SOC 合意(B-GD-1/2)、緊急鍵ローテ SOP の承認体制（B-GD-3）。

---

## 7.5 Workload Identity 実装（ADR-041 2026-07-23 IRSA 化の実装確定）

### 7.5.1 決定 D-U7-09: ROSA IRSA の IAM Role 設計

**採用**: Pod → AWS リソースは **ROSA 標準の pod identity webhook + IRSA 方式**（クラスタ OIDC プロバイダ信頼、D-U6-02 #2）で統一し、Role 設計規約を次で確定する:

| 項目 | 規約 |
|---|---|
| Role 命名 | `<acct>-irsa-<namespace>-<serviceaccount>`（例: `broker-irsa-keycloak-kc-sa`） |
| Trust Policy | クラスタ OIDC プロバイダ + `sub = system:serviceaccount:<ns>:<sa>` **完全一致**（ワイルドカード禁止）+ `aud = sts.amazonaws.com` |
| 1 SA = 1 Role | SA の共有禁止（監査で「どの Pod か」を CloudTrail `sub` で特定可能に） |
| クラスタ分離 | Broker / IdP-KC は OIDC プロバイダも Role も完全別。**相互の Acct の Role を信頼する構成は禁止**（D-U6-02 #1 の IAM 面貫徹） |

**Phase 1 IRSA Role 初期セット**:

| Role（SA） | Acct | 許可（最小権限） |
|---|---|---|
| `broker-irsa-keycloak-kc-sa` | Broker | Secrets Manager（broker-secrets 配下 GetSecretValue のみ）/ KMS Decrypt（broker-secrets CMK） |
| `idpkc-irsa-keycloak-kc-sa` | IdP-KC | 同上（idpkc-secrets） |
| `*-irsa-logging-fluent-bit` | 両 | CloudWatch Logs PutLogEvents / 監査 Acct S3 PutObject（バケットポリシー側で SourceAccount 限定、削除不可） |
| `*-irsa-scim-facade` | 両 | Secrets（SCIM Bearer 検証鍵）/ EventBridge PutEvents（idmap 経路 5） |
| `broker-irsa-ops-key-rotation` | Broker | §7.1.3 CronJob 用（Secrets 更新のみ。KC Admin API は FedID 経由 §7.5.2） |
| Lambda 実行 Role（Risk Engine / マスキング） | Broker | DynamoDB（itdr テーブル限定）/ KMS（broker-itdr）/ SNS / KC Admin API 用クレデンシャル取得 |

- **根拠**: ADR-041（2026-07-23 改訂）、PCI DSS 8.6.1/8.6.2/8.6.3（対話利用不可・hardcode 禁止・1h 自動ローテーション）、Red Hat 公式手順。
- **代替**: EKS Pod Identity — ROSA に存在しないため不採用（ADR-041 冒頭注記）。SPIFFE/SPIRE — Phase 2 候補の位置づけ維持（マイクロサービス 50+ / マルチクラウド時）。
- **未決**: なし。

### 7.5.2 決定 D-U7-10a: Keycloak Federated Identity Credentials の適用範囲

**採用**: Keycloak への M2M アクセス（Admin API / Token Endpoint）は、**基盤内部コンポーネントから順に client_secret を廃止し K8s SA JWT の jwt-bearer 交換（Federated Identity Credentials）へ移行**する。

| クライアント | Phase 1 | 方式 |
|---|---|---|
| 管理画面 Backend（**Broker Acct**、ADR-038） | ✅ FedID | **Broker クラスタ** K8s SA JWT（audience=keycloak）→ **Broker KC** Token。KC 側は Broker クラスタの OIDC Discovery（ROSA は S3 公開済み）を JWKS URL に登録 |
| 専用 API 層（**IdP-KC Acct**、ADR-038 Backend 同基盤） | ✅ FedID | **IdP-KC クラスタ** K8s SA JWT（audience=keycloak）→ **IdP-KC KC** Token。KC 側は IdP-KC クラスタの OIDC Discovery を JWKS URL に登録 |
| 鍵ローテ CronJob / テナント一括 logout ジョブ（U5 §5.4.2） | ✅ FedID | 同上（Broker クラスタ） |
| ITDR Risk Engine Lambda（Response Action） | ⬜ client_secret 暫定 | Lambda は K8s SA を持たないため FedID 不可。**Confidential Client + Secrets Manager 保管 + 90 日ローテ**で開始し、§7.5.3 の昇格で private_key_jwt 化 |
| 外部アプリの CC クライアント（`idm:*` スコープ、U5 §5.8） | ⬜ client_secret | 顧客側は K8s 前提にできない。§7.5.3 のローテーション規約を適用 |

- **根拠**: ADR-041 §B（Secret ゼロ・1h 自動ローテ・K8s RBAC で発行制御）、PCI DSS 8.6.2。
- **代替**: 全クライアント一括 FedID 化 — Lambda / 顧客側が対象外のため不成立。方式を 2 系統（FedID / Secrets+ローテ）に限定し「secretの野良管理」だけを排除する。
- **未決**: ROSA の SA issuer JWKS を Broker KC から参照する際のネットワーク経路確認（VPC 内 or S3 公開 URL。実機確認は Phase 1 実装時、U9）。

### 7.5.3 決定 D-U7-10b: private_key_jwt / mTLS 昇格の時期確定（U6 §6.3.2 への回答）

**採用**: **「Secrets ローテーション自動化の Phase 1 整備 → Phase 2 開始時に private_key_jwt へ一括昇格」**で時期を確定する。

| 段階 | 内容 |
|---|---|
| **Phase 1（確定）** | 2-tier（Broker↔IdP-KC）および Confidential Service Client は `client_secret_post` を許容（PrivateLink 閉域が成立しているため、D-U6-06）。ただし次を必須とする: ① secret は Secrets Manager 保管（`*-secrets` CMK）+ **90 日自動ローテーション**（Rotation Lambda → KC Admin API で更新）② **Keycloak Client Secret Rotation ポリシー（2 世代並走）を有効化**し、ローテ時の瞬断をゼロ化 ③ realm.json / IaC への secret 直書き禁止（PCI 8.6.2、CI lint で機械検査 — U9） |
| **Phase 2 開始時（昇格、確定）** | 2-tier ブローカー接続・基盤内部 Confidential Client・`idm:*` CC クライアントを **private_key_jwt（RFC 7523）へ一括昇格**。鍵ペアはクライアント側生成・公開鍵のみ KC 登録（JWKS URL）、90 日ローテは同じ Rotation 基盤を流用（secret 更新 → 鍵ペア更新に置換するだけの設計とし、Phase 1 の自動化投資を無駄にしない） |
| **mTLS（Phase 3 / 条件付き）** | FAPI 2.0 / 金融顧客要件の発生時のみ（ADR-060 §B.4 Phase 3 と同一トリガー）。CA 運用（ADR-060 §I）の重さから標準昇格パスには含めない |

- **根拠**: U6 §6.3.2 の宿題（「Secrets ローテーション設計とセットで判断」）に対し、**昇格の前提条件はローテーション自動化そのもの**（private_key_jwt でも鍵ローテは必要であり、回す仕組みがない状態で方式だけ上げても運用が破綻する）。閉域 PrivateLink 下では client_secret_post の残余リスク（経路上の秘匿情報送信）は小さく、Phase 1 のリスクは受容可能。PCI 8.6.3（定期ローテ）は Phase 1 の 90 日で充足。
- **代替**: ① Phase 1 から private_key_jwt — Terraform keycloak provider / 各コンポーネントの鍵管理実装が Phase 1 クリティカルパスに乗る割に、閉域内でのセキュリティ増分が小さい。② 昇格せず client_secret 恒久 — 外部公開面（App Acct からの CC クライアント）が増える Phase 2 以降は送信型クレデンシャルの排除価値が上がるため不採用。
- **未決**: なし（時期確定が本項の成果）。U6 §6.3.2 / U2 §2.2.3 の「Phase 2 で昇格」注記を本決定で確定扱いにする。

---

## 7.6 PAM 統合（ADR-040 復活の本基盤設計への接続）

> ADR-040（2026-07-23 Accepted 復帰）は運用体制・ロードマップ・SLA の SSOT。本節は**本基盤側に発生する設計制約 4 点**（Composite Role / /admin 経路 / 監査ログ集約 / アカウント体系読み替え）の接続のみを確定する。二重定義を避けるため数値・体制は ADR-040 §G〜§I を参照。

### 7.6.1 決定 D-U7-11: ADR-040 4 層モデルの Wave 1 構成への写像

**採用**:

| ADR-040 層 | 本基盤側の接続点（本書で確定） |
|---|---|
| **L1 Break-Glass** | 各**自管理** Acct（監査 / Broker / IdP-KC）に 1 アカウント。クレデンシャル Secrets は `broker-breakglass` CMK（§7.1.1）+ 物理金庫 + FIDO2。**他組織 Acct（NW 監査 / NW）の Break-Glass は先方責務**（要求仕様にも含めない、D-U6-02 #4）。発動時の全操作は監査 Acct へ即時集約 + Slack #security 通知 |
| **L2 インフラ（IIC）** | IAM Identity Center の Permission Set を **6 アカウント体系（D-U6-01）× 3 チーム（ADR-040 §H）**で定義。**ADR-040 の「5 アカウント」記述は本書で 6 アカウント（Broker / IdP-KC 分割）へ読み替え確定**（ADR-040 P1-02 の実装入力）。Broker と IdP-KC の常任 Permission Set は**別チームメンバーでも同一人物への同時昇格を承認フローで排他**（両 Acct 同時侵害の防止、SoD 拡張） |
| **L3 アプリ（Keycloak）** | `realm-admin-eligible` / `realm-admin-active` の 2 状態 Composite Role を **Broker / IdP-KC 両 Realm に定義**（U2 Realm 設計へ引き渡し）。昇格 API（ADR-040 P1-05）+ EventBridge Lambda 自動剥奪（最大 4h）。昇格 API の実行主体は §7.5.2 FedID クライアント。**Admin Console / Admin API へのアクセスは内部ホスト名（`hostname-admin`）+ 内部経路のみ**（下記 D-U7-12） |
| **L4 テナント特権** | ユーザ管理画面（ADR-038）の破壊的操作 JIT 承認。API 面は U5 §5.8 の `idm:*` スコープ + SoD 承認フロー（U10 詳細化） |

- **根拠**: ADR-040 §A/§B、P-17。Composite Role 2 状態モデルは Keycloak ネイティブで追加製品ゼロ。
- **代替**: ADR-040 §F の通り（CyberArk 等は不採用済み）。
- **未決**: L3 昇格 API の実装配置（管理画面 Backend 同居 vs 独立ツール）— ADR-040 P1-05 の実装設計時（T-6〜T-3）に確定。

### 7.6.2 決定 D-U7-12: /admin 経路・監査ログ集約の整合確定

**採用**:

| 項目 | 確定内容 |
|---|---|
| /admin 保護 | **ADR-040 P1-01「CloudFront + WAF で IP 制限」は P-18 により他組織要求（REQ-IN-04）へ再定義済み**であり、実効防御は U6 D-U6-11 の 3 層（L1 WAF 要求 / **L2 自管理 ALB 403 = 生命線** / L3 `hostname-admin` 分離）で成立していることを PAM 側前提として確定。P1-01 の受入条件は「D-U6-11 L2/L3 の実装完了」に読み替える |
| 運用経路 | 特権セッションは **SSM Session Manager ポートフォワード標準 + VPN 併用**（D-U6-12）。SSM 全操作録画 → CloudWatch Logs → 監査 Acct S3（Object Lock）。IIC 昇格（L2）→ SSM 起動 → KC Admin（L3）のチェーンで、**インターネットからの /admin 到達経路は存在しない**構造を維持 |
| 監査ログ集約先 | ADR-040 §D.1 の保管表を **監査 Acct（D-U6-01 #3）= 唯一の集約先**として確定: IIC 昇格記録（Org Trail 7 年）/ SSM 録画（1 年 + Glacier 6 年）/ KC Admin Events（両 Realm、OpenSearch 1 年 + S3 6 年）/ ユーザ管理画面 Audit（同）。すべて S3 Object Lock（WORM）+ `audit-logs-mrk`。**運用者は監査 Acct に対し read-only**（PCI DSS 10.3） |
| 顧客説明 | **B-PAM-1〜4 ゲート**（Phase 1 α/β 対応時間帯 / Break-Glass 役員承認 / 監査ログ提供頻度 / Trust Center 公開範囲）を Phase 1 α 契約前ゲートとして参照。文言 SSOT は ADR-040 §I.5 / ADR-036 2026-07-23 追記 |
| ITDR 連携 | 特権系イベント（昇格 / Break-Glass ログイン / Admin Events の破壊的操作）を Risk Engine へ流し、Privileged Account Abuse 検知（ADR-035 領域 5）の**データ蓄積を Phase 1 から開始**（検知ロジック自体は Phase 4） |

- **根拠**: ADR-040 §D、ADR-039 §A.2、U6 §6.6。U1 §1.4 の残タスク（§FR-8.6 / §NFR-4.7 の OOS 残存注記整理）は本節の確定をもって「ADR-040 Accepted / 本書 §7.6 参照」への更新指示として U9（文書整合）へ引き渡す。
- **代替**: 監査ログの顧客テナント別 Acct 分離 — ADR-040 P2-03（Phase 2）。
- **未決**: B-PAM-1〜4（ヒアリング進行中）。Phase 1 α の業務時間外 Break-Glass 承認 SLA は「保証なし（Best Effort）」で契約明示（ADR-040 §I.3）。

---

## 7.7 PCI DSS ギャップ 3 点 + APPI 対応の実装計画

> 位置づけ: 本基盤は **Cat 2b（Security-Impacting / authentication server）で Out-of-Scope 化不可能**、Service Provider として **SAQ D-SP** 路線（[reference/pci-dss-v401 §2-4](../reference/pci-dss-v401-scope-for-auth-platform.md)）。PAN 非経由の維持（U5 クレーム辞書に PAN 系なし + §5.1.4 チェックリスト C-4）が Out-of-Scope（Cat 1 回避)の前提条件であり続ける。QSA 初回監査は ADR-040 Phase 1 β（T+6、Pβ-05）と同期。

### 7.7.1 決定 D-U7-13: 監査ログ 12 ヶ月（PCI Req 10.5.1）— CloudWatch 90 日 + S3 Object Lock 7 年

**採用**:

| 層 | 実装 | 保持 |
|---|---|---|
| Hot（即時分析） | CloudWatch Logs（各 Acct）+ 監査 Acct OpenSearch | **90 日**（Req 10.5.1「直近 3 ヶ月即時アクセス」充足。retention 設定を IaC 固定） |
| Cold（改ざん不能長期） | CloudWatch → Kinesis Data Firehose → **監査 Acct S3（Object Lock **Compliance mode**、`audit-logs-mrk`）** → Glacier 移行 | **7 年**（Req 10.5.1 の 12 ヶ月を包含 + ADR-039/040 の 7 年方針に統一） |
| 検索 | Athena（S3 直、パーティション = acct/source/日付） | 12 ヶ月超の調査・監査エビデンス抽出 |

- 対象ログ源（Phase 1 必須セット）: KC Events / KC Admin Events（両 Realm）、ALB access log、VPC Flow Log、CloudTrail（Org Trail）、SSM 録画、IIC 昇格記録、ITDR 判定ログ、SCIM Facade 監査、ユーザ管理画面 Audit、KMS CloudTrail イベント。**すべて Log scrubbing（§7.3）通過後に保存**（Cold 層に平文トークンを 7 年残さない）。
- Object Lock は **Compliance mode**（運用者・root でも削除不可）。誤設定巻き戻し不能リスクは「バケット分割（ソース別）+ 保持期間の段階設定」で緩和。
- **根拠**: PCI Req 10.5.1 verbatim（[gap doc §3.3](../common/pci-dss-appi-compliance-gap.md)）、現状最大ギャップ #1（CloudWatch 7d）の解消。
- **代替**: Governance mode — 特権による解除が可能で WORM 主張が弱く、QSA 説明性で劣後。Security Lake — Phase 1 は過剰、OCSF 移行（ITDR Phase 5）時に再評価。
- **未決**: OpenSearch のサイジング（ログ量実測後、U9）。

### 7.7.2 決定 D-U7-14: Phishing-resistant MFA（PCI Req 8.4/8.5.1）— WebAuthn を管理系必須・D-U4-04 整合

**採用**: TOTP の replay 窓（±30s）を踏まえ、**WebAuthn（FIDO2 / Passkeys）を次の範囲で必須化**する:

| 対象 | Phase 1 要件 | U4 との整合 |
|---|---|---|
| P-1 弊社運用者 | **WebAuthn 必須**（PW + WebAuthn、TOTP 不可） | D-U4-04 ケース D（管理者 PW+WebAuthn）そのまま |
| P-2 テナント管理者 | **WebAuthn 必須**（初回ログイン時エンロール強制） | D-U4-04 ケース B + エンロール強制 |
| P-4 ローカルフェデなし従業員 | WebAuthn 推奨・TOTP 許容（ケース C フォールバック） | D-U4-04 ケース B/C |
| P-3 フェデ従業員 | 顧客 IdP 側 MFA を信頼（`mfa_indicator` 評価、ADR-031）。**顧客 IdP の MFA 品質は契約の Responsibility Matrix で顧客責任と明記**（§7.7.4） | D-U4-04 ケース A |
| Break-Glass | FIDO2 ハードウェアキー必須（ADR-040 §C.2） | — |

- Recovery Codes 標準発行 + リセットは管理者 JIT 承認経路のみ（D-U4-04 / §7.6 L4)。Keycloak WebAuthn Policy（attestation / user verification 要件）の具体値は U2 Realm 設定へ引き渡し。
- **根拠**: PCI Req 8.4.2 / 8.5.1（replay 耐性）、NIST SP 800-63B Rev 4、gap doc 最大ギャップ #2。全アクセス MFA 必須化により Req 8.3.9（PW 90 日変更）を適用外化（gap doc Q4 の推奨解）。
- **代替**: 全ユーザ WebAuthn 強制 — P-4 のデバイス環境が保証できず UX 阻害。管理系必須 + 一般推奨の 2 段が業界標準。
- **未決**: B-PCI 系ヒアリング（顧客側の MFA 種別要求）。

### 7.7.3 決定 D-U7-15: 漏えい等報告 SOP（APPI 法 26 + 規則 7・8 条）

**採用**: SOP 骨子を次で確定し、Runbook 化（文書実体・訓練）は U9 + ADR-044 Tabletop に引き渡す:

| ステップ | 内容 | 期限 |
|---|---|---|
| ① 検知 | ITDR（§7.2）/ Golden 検知（§7.4）/ Log scrubbing 監査スキャン（§7.3）/ 外部通報 → Security Lead へエスカレーション | 即時 |
| ② トリアージ | **規則第 7 条 4 類型への該当判定**を判定表で実施: (2) 財産的被害のおそれ（認証情報 = ログイン ID + PW の漏えいは決済機能アプリ連携時に該当しうる）/ **(3) 不正アクセス起因 = 1 件でも報告対象** / (4) 千人超。ITDR Severity との対応: L3/L4 発火で本 SOP の起動判定を必須化 | 検知から 24h 以内 |
| ③ 封じ込め | U5 §5.4 の粒度（個別 / テナント / L4 全体）+ 必要時 §7.1.3 緊急鍵ローテ | 即時並行 |
| ④ **速報** | PPC 報告フォーム（概要 / 項目 / 件数 / 原因 / 二次被害 / 本人対応 / 公表 / 再発防止） | **知った時点から 3〜5 日** |
| ⑤ 顧客通知 | 影響テナントへ通知（契約の 12.9.2 系条項・インシデント通知条項に従う）。委託元（顧客）経由の本人対応整理 | 契約 SLA（Phase 1 α: メール + Slack、ADR-040 §I.1） |
| ⑥ **確報** | PPC へ確定内容報告 | **30 日以内（不正アクセス起因 = 60 日以内）** |
| ⑦ 事後 | AAR + 再発防止 + 監査 Acct へ記録（7 年）+ Trust 説明資料更新 | 30 日以内 |

- 体制: Phase 1 α は業務時間内（検知〜速報 3-5 日は業務時間対応でも達成可能な設計とするが、**重大インシデントの初動のみ Break-Glass 経路で時間外対応可**）。Phase 1 β で 24/7 On-Call に載せ替え（gap doc Q10 への回答）。
- **根拠**: APPI 法 26 + 規則 7・8 条 verbatim（[gap doc §4.5](../common/pci-dss-appi-compliance-gap.md)）、最大ギャップ #3。
- **代替**: なし（法定義務）。
- **未決**: PPC 報告実務担当（法務 or Security Lead）の指名、雛形の法務レビュー（T-6 まで）。

### 7.7.4 決定 D-U7-15b: APPI 委託先監督 — Red Hat DPA（ADR-056 採用条件 ①）ほか

**採用**: 委託先整理を次で確定し、**Red Hat DPA の締結を P-01（ROSA HCP）の Accepted 完全昇格条件として本書でも追跡**する:

| 委託先 | 論点 | 対応 |
|---|---|---|
| **Red Hat**（ROSA HCP CP / SRE） | 法 25（委託先監督）+ **法 28（SRE 越境アクセス = 外国第三者提供の可能性）** | **DPA に GDPR SCC 相当条項 + SRE 越境アクセスログ取得 + 監査権**（ADR-056 採用条件 ①）。技術側前提: **個人データ本体の etcd 非流入設計**（K8s Secret は鍵類のみ、個人データは Aurora に閉じ込め — 本書 §7.1 の暗号化境界がその実装）+ ガードレール L1-L5（ADR-056）。**法務確認で不可なら実行基盤再検討**（ADR-056 記載のエスカレーション） |
| AWS | 法 25/28（リージョンは国内 2 拠点で越境最小） | DPA / AOC 等の Artifact 整理（gap doc 必須対応 #3） |
| その他 SaaS（PagerDuty 等 Phase 1 β 導入分） | 法 25 | 導入時に第三者監査証跡（SOC 2 等）確認を必須プロセス化 |
| （逆方向）顧客 → 本基盤 | 本基盤 = 受託者 | **Responsibility Matrix + 12.9.2 written acknowledgment を契約書内明文で提供**（Portal 掲載単独では不可 — [reference §9](../reference/pci-dss-v401-scope-for-auth-platform.md)）。Trust Portal 静的版は B-PCI-7 判定次第（ADR-036） |

- **根拠**: APPI 法 25/28、ADR-056 §採用条件、gap doc §6。
- **未決**: Red Hat DPA 法務確認の完了（**Phase 1 契約前ゲート**、ADR-056）。B-PCI-7（Trust Portal）。

### 7.7.5 決定 D-U7-16: zero-egress（U6 O-10 案 B）のセキュリティ側評価 — 採用を推奨

**採用（セキュリティ観点の評価確定）**: **案 B（`zero_egress:true` + ECR ミラー + TGW 他組織 Outbound）をセキュリティ・コンプライアンス観点で推奨**とし、U6 O-10 の最終決定（先方 TGW 接続可否・ミラー運用負荷）への入力とする。

| 観点 | 評価 |
|---|---|
| サプライチェーン統制（ADR-046 連動） | ◎ **ECR ミラーが「配布層（L5）の単一検証点」になる**: ミラー同期パイプラインに Trivy スキャン + Cosign verify（署名検証）を組み込めば、**未検証イメージ・OLM カタログがクラスタに到達する経路が構造的に消える**（pull 時検証より強い事前検証モデル）。ADR-046 Phase 1 最低限（Trivy + 署名 + §6.4.3）の実装点をミラーに集約でき、運用箇所が減る |
| Egress 統制（PCI / P-18） | ◎ 自 Acct NAT 不在 + Worker の運用系 outbound が VPC 内完結 → **未知宛先への C2 通信の物理経路が縮小**。REQ-OUT-02（デフォルト Deny）の検証対象が「フェデ Egress のみ」に単純化され、QSA への Egress 統制説明が容易 |
| トレードオフ | △ ミラー同期の鮮度遅延（CVE 修正イメージの反映が同期周期に律速）→ **Critical CVE 時の緊急同期手順を U9 Runbook に必須追加**。OLM カタログミラーの運用工数（ADR-046 の Renovate/Trivy 運用と統合して吸収） |
| 帰結 | zero-egress は REQ-OUT（フェデ Egress 1000+ FQDN）の代替ではない（U6 §6.7.3 確定済み）。**「運用系 Egress の統制」を製品仕様レベルで確定させる選択**と位置付ける |

- **根拠**: ADR-046 §A（6 層 Defense の L3/L5）、rosa-hcp-machine-pool-egress-notes.md §2、PCI DSS 1.3 系（アウトバウンド制限）。
- **代替**: 案 A（NAT GW + 先方 NFW ドメインフィルタ）— 成立はするが、許可 FQDN（registry.redhat.io / quay 等 十数ドメイン）の維持が先方変更管理に載り、ミラー検証点も持てない。セキュリティ増分は案 B が明確に上。
- **未決**: 最終採否は U6 O-10（先方回答 + ミラー運用負荷実測）。本書はセキュリティ評価の確定のみ。

---

## 7.8 Bot / DDoS — 自管理と他組織要求の分離

### 7.8.1 決定 D-U7-17: 分離マトリクスとフォールバック最低線

**採用**（ADR-042 の Phase 1 採用セットを P-18 で再配置）:

| 層 | 対策 | 主体 | 位置づけ |
|---|---|---|---|
| L1 Network | **WAF Bot Control（Common + Targeted）+ ATP + 認証専用 Rate Limit + Shield** | **他組織（要求）** | REQ-IN-01 の WAF ルール内訳として**明細を要求仕様に追補**: ① Bot Control Common+Targeted ② ATP（ログイン POST パスへの適用、credential stuffing 検知）③ Rate Limit（/token・/auth 系: 2000 req/5min/IP 初期値）。**+ 新規 REQ-OUT-05: WAF / Bot Control / ATP の検知ログを弊社監査 Acct へ配信**（ITDR の相関入力。REQ-OUT-03 と同方式） |
| L2 アプリ | Cloudflare Turnstile + Custom SPI | 弊社 | **Phase 2 オプション**（ADR-042 2026-06-24 確定を維持）。**ただし発動トリガーに「REQ-IN-01 の Bot Control / ATP が先方に受け入れられない場合」を追加** — B 部不成立時の自管理側の埋め合わせ手段として前倒し検討する |
| L3 アカウント | Keycloak Brute Force + Account Enumeration 対策 + ITDR（§7.2） | 弊社 | Phase 1 必須（下記） |

**自管理側（保証する最低線）の実装確定**:

| 項目 | 設定 |
|---|---|
| Keycloak Brute Force Protection | 両 Realm 有効。5 連続失敗 / ロック 30 分 / permanent なし（§7.2.2） |
| Account Enumeration 対策 | 汎用エラーメッセージ（存在有無を返さない）+ Constant-time response。**HRD の応答同一化（U4 D-U4-02）と同一原則**であり、ログイン系の全応答で貫徹 |
| PW ポリシー | length(12) + 英数混在（PCI 8.3.6）+ HIBP 照会（§7.2.2）。U2 Realm Policy へ引き渡し |
| DDoS | インフラ面は他組織エッジ（CloudFront + Shield）に依存。自管理側は **KC Pool の HPA + Machine Pool autoscale（U6 §6.2.2）で L7 吸収余地を持つ**が、体積型 DDoS の防御は保証しない（Responsibility Matrix に明記） |

- **フォールバック評価（B 部不成立時）**: WAF Bot Control / ATP が未実装でも、Brute Force + Enumeration 対策 + ITDR + Rate Limit（自管理 ALB でのパスベース制限は限定的に可能）で「アカウント侵害の最低防御線」は成立する。ただし **PCI DSS §6.4.2（自動攻撃防御）の充足は WAF 側が前提**（ADR-042 判断根拠）のため、**REQ-IN-01 不成立のまま PCI 対応顧客と契約しないことをゲート条件**とする（G-EGRESS と同型の「未合意のまま契約禁止」原則。**G-PCI-WAF** として U1 §1.5 登録済み）。
- **根拠**: ADR-042（WAF+ATP で PCI §6.4.2 充足 / 検知率 90-95%）、P-18、U6 §6.0.2 生命線原則。
- **代替**: Phase 1 から Turnstile 常設 — SPI 継続メンテ負担で不採用済み（ADR-042）。商用 Bot Manager — 8-12 倍コストで不採用済み。
- **未決**: REQ-IN-01 明細・REQ-OUT-05 の先方回答。ATP 用のクレデンシャル形式連携（ATP はログイン POST ボディ形式の指定が必要 → Keycloak のフォームフィールド名を要求仕様に添付）。

### 7.8.2 決定 D-U7-18: Argon2id パラメータ（U6 §6.5.4 への回答）

**採用**: **Keycloak デフォルト（Argon2id、m=7MiB / t=5 / p=1）を Phase 1 パラメータとして確定**する。

- **根拠**: OWASP Password Storage Cheat Sheet の許容構成（m=7MiB, t=5 は OWASP 推奨系列の一つ）に合致し、P-03（FIPS 不要）で Argon2id 継続に障害なし。U6 §6.5 のサイジング（10 TPS/vCPU 前提・c7g 1:2 メモリ比）と整合し、**m=64MB 系への強化（= m7g 系へのインスタンス変更が必要）を要求しない**ため U6 の Machine Pool 設計を変更せず確定できる。
- **代替**: m=19MiB/t=2 等の高メモリ構成 — GPU 攻撃耐性は増すが、10M MAU ピークの同時ハッシュでメモリ圧迫 + スループット低下（IdP-KC ノード数増）。本基盤はフェデ主体（P-07 γ でローカル比率 3-5%）で PW 面が小さく、デフォルト維持が総合最適。
- **未決**: PoC でのスループット実測補正（U6 §6.5.1 の「KC デフォルトパラメータでの実測は PoC で補正」と共通）。

---

## 7.9 決定一覧・未決事項・他単元への引き渡し

### 7.9.1 決定一覧（サマリ）

| # | 決定 | 節 |
|---|------|-----|
| D-U7-01 | CMK 命名 `alias/<scope>-<purpose>[-mrk]`、6 アカウント体系へ分割配置、Aurora 系は MRK / Break-Glass・Secrets は Regional | §7.1.1 |
| D-U7-02 | Key Policy 3 ロール SoD（Key Admin = Security+Infra Lead の Custodian 2 名 / Key User = IRSA Role のみ / 人間への Key User 付与禁止） | §7.1.2 |
| D-U7-03 | ES256 署名鍵 = Keycloak Realm Key（DB + KMS at-rest）+ **90 日 Cryptoperiod・30 日並走**、KMS 署名 SPI は Phase 2 再評価 | §7.1.3 |
| D-U7-04 | ITDR パイプライン = SPI（emit 専任）→ EventBridge → Risk Engine Lambda → DynamoDB を **Broker Acct 集約**、IdP-KC からは PutEvents 第 6 経路（U6 差分要求） | §7.2.1 |
| D-U7-05 | Phase 1 検知 = HIBP（k-Anonymity、fail-open）+ Brute Force（5 回/30 分 + Spraying 横断検知）、L4 は手動承認 + U5 §5.4.3 手順 | §7.2.2 |
| D-U7-06 | 誤検知運用 = Phase 1a 通知のみ → 3 ヶ月チューニング（FP<5%）→ Phase 1b 自動アクション、allowlist IaC 管理 | §7.2.3 |
| D-U7-07 | Log scrubbing = Fluent Bit DaemonSet + **infra Pool 上の Aggregator でマスク** + Lambda（ALB/CW）+ 週次監査スキャン、辞書 M-1〜14、CloudFront 分は REQ-IN-10 要求 | §7.3.1 |
| D-U7-08 | Golden 検知 Phase 1 = **G-2/G-3(簡易)/G-5/G-6 の 4 シグナル**、G-1/G-4 は Phase 2、L-GD は LDAP 顧客受入と同時 | §7.4.1 |
| D-U7-09 | IRSA Role 規約（1 SA = 1 Role / sub 完全一致 / クラスタ間相互信頼禁止）+ Phase 1 Role 初期セット | §7.5.1 |
| D-U7-10a | KC への M2M = 基盤内部は Federated Identity Credentials（Secret ゼロ）、Lambda・顧客 CC は Secrets+ローテ系統 | §7.5.2 |
| D-U7-10b | **private_key_jwt 昇格 = Phase 2 開始時に一括**（Phase 1 は client_secret_post + Secrets Manager 90 日自動ローテ + KC 2 世代並走ローテ必須）、mTLS は Phase 3 条件付き — U6 §6.3.2 への回答 | §7.5.3 |
| D-U7-11 | PAM 4 層の写像確定: IIC = 6 Acct 読み替え + Broker/IdP-KC 同時昇格排他、Composite Role 2 状態を両 Realm（U2 引き渡し）、Break-Glass は自管理 3 Acct のみ | §7.6.1 |
| D-U7-12 | /admin = D-U6-11 3 層で P1-01 を読み替え、特権経路 = IIC→SSM→内部ホスト名、監査ログ集約先 = 監査 Acct 一元（WORM 7 年）、B-PAM-1〜4 ゲート参照 | §7.6.2 |
| D-U7-13 | 監査ログ = CW 90 日（即時 3 ヶ月充足）+ Firehose → S3 **Object Lock Compliance 7 年** + Athena、全ソース scrubbing 通過後保存 | §7.7.1 |
| D-U7-14 | Phishing-resistant MFA = **WebAuthn を P-1/P-2 必須**（D-U4-04 整合）、P-3 は mfa_indicator + 契約責任分界、MFA 必須化で Req 8.3.9 適用外化 | §7.7.2 |
| D-U7-15 | 漏えい報告 SOP 7 ステップ（速報 3-5 日 / 確報 30・60 日、規則 7 条 4 類型判定表、ITDR L3/L4 と接続）+ Red Hat DPA = Phase 1 契約前ゲート | §7.7.3-4 |
| D-U7-16 | zero-egress 案 B を**セキュリティ観点で採用推奨**（ECR ミラー = サプライチェーン単一検証点 + Egress 統制単純化）、最終決定は U6 O-10 | §7.7.5 |
| D-U7-17 | Bot/DDoS 分離 = WAF Bot Control/ATP/Rate Limit は要求仕様（REQ-IN-01 明細 + REQ-OUT-05 ログ共有）、自管理最低線 = KC Brute Force + Enumeration 対策 + ITDR。REQ-IN-01 不成立のまま PCI 顧客契約禁止 | §7.8.1 |
| D-U7-18 | Argon2id = KC デフォルト（m=7MiB/t=5）維持 — U6 §6.5.4 への回答、Machine Pool 設計変更なし | §7.8.2 |

### 7.9.2 未決事項（オープン項目）

| # | 項目 | 内容 | 期限 / ゲート |
|---|------|------|------------|
| O-U7-1 | KMS 署名 SPI / CloudHSM | 金融・FAPI 顧客要件発生時に §7.1.3 代替案 ① を再評価 | Phase 2 判断 |
| O-U7-2 | ITDR / Golden 閾値の最終値 | B-GD-1/2/3、B-ITDR-1〜6 ヒアリング + Phase 1b チューニング実測 | Phase 1b 移行時 |
| O-U7-3 | L3 テナント別 CMK 対象 | B-KMS-3（規制業種・大規模顧客の要求） | 顧客ヒアリング |
| O-U7-4 | REQ 追補の先方回答 | REQ-IN-10（CloudFront ログ最小化）/ REQ-IN-01 明細（Bot Control/ATP）/ REQ-OUT-05（WAF ログ共有）/ HIBP FQDN 追加 | 要求仕様書 v1 回答時（U6 §6.7.4 プロセスに同梱） |
| O-U7-5 | **Red Hat DPA 法務確認**（**G-DPA**） | APPI 法 28 相当措置 + SRE 越境ログ。不成立なら実行基盤（P-01）再検討に波及 | **Phase 1 契約前ゲート**（ADR-056 採用条件 ①、G-DPA として U1 §1.5 登録済み） |
| O-U7-6 | B-PAM-1〜4 | Phase 1 α/β 差分・Break-Glass 承認・監査ログ提供・公開範囲の顧客合意 | Phase 1 α 契約前（B-PAM-1/2 必須） |
| O-U7-7 | ITDR データ面の DR | DynamoDB（履歴）の大阪側扱い（Global Tables vs 再構築許容）+ Break-Glass の大阪側金庫・鍵の実体 | U8 と合同 |
| O-U7-8 | FedID の JWKS 経路実確認 | ROSA SA issuer の KC からの参照経路（§7.5.2） | Phase 1 実装時 |
| O-U7-9 | B-PCI-7 / Trust Portal | 静的版の要否（監査エビデンス提供のスケール） | PCI 対応顧客の具体化時 |

### 7.9.3 他単元への引き渡し

**U2（Keycloak 論理設計）へ**: Composite Role 2 状態モデルの両 Realm 定義（§7.6.1）/ WebAuthn Policy 具体値 + PW ポリシー length(12)（§7.7.2 / §7.8.1）/ Event Listener SPI の emit イベントセット確定（§7.4.1）/ Client Secret Rotation ポリシー（2 世代並走）の Client テンプレート反映（§7.5.3）/ private_key_jwt 昇格の Phase 2 確定（U2 未決 #4 のクローズ）。

**U6（インフラ・NW）へ**: D-U6-02 への第 6 経路追加要求（ITDR PutEvents、§7.2.1）/ 要求仕様書 v1 への追補 4 点（O-U7-4）/ O-10 へのセキュリティ側評価入力（案 B 推奨、§7.7.5）/ §6.3.2 クライアント認証の昇格時期確定の反映（§7.5.3）。

**U8（可用性・DR）へ**: MRK の大阪 Replica 構成（Aurora 系 + audit-logs、§7.1.1）/ 大阪側 Break-Glass 実体（金庫・FIDO2・Regional 鍵）と ITDR DynamoDB の DR 方式（O-U7-7）/ Failover 時の JWKS・鍵並走の不変性確認（Realm Key は Aurora Global で複製されるため大阪昇格後も `kid` 連続 — 検証項目として依頼）。

**U9（運用・監視・IaC）へ**: Runbook 化 5 点（緊急鍵ローテ SOP / 漏えい報告 SOP / L4 発動手順〔U5 §5.4.3 + 30 分監視窓〕/ Break-Glass 手順 / zero-egress 採用時の緊急イメージ同期）/ 監査スキャン Dashboard + `log_scrubbing_leak_count` 等メトリクス（§7.3）/ KMS 監視アラート（§7.1.2）/ Key Policy・IRSA Role・マスキング辞書・ITDR 閾値の IaC モジュール化 / secret 直書き検出 CI lint（§7.5.3）/ ADR-040 OOS 残存注記（§FR-8.6 / §NFR-4.7）の文書整合更新（§7.6.2）。

**U10（周辺連携）へ**: L4 テナント特権 JIT 承認の API / SoD フロー詳細（§7.6.1）/ 顧客契約への Responsibility Matrix・12.9.2 条項・MFA 責任分界（P-3 は顧客 IdP 責任）の反映（§7.7.2 / §7.7.4）。

**ADR への反映（本書確定後）**: ADR-045（Acct 分割読み替え + `keycloak-jwt-signing` 予約扱い）/ ADR-035・060（Phase 1 範囲・閾値の本書参照）/ ADR-041（Role 規約の本書参照）/ ADR-042（Turnstile 前倒しトリガー追加）。※ ADR-040 / 036 は別スレッド改訂中のため**本書からの参照のみ**とし、両ファイルへの書き込みは行わない。

---

## 改訂履歴

- 2026-07-23: 初版（Wave 2 起草）。Baseline v1（P-03/P-17/P-18）準拠。KMS 3 階層の 6 Acct 写像 + Realm Key 90 日 Cryptoperiod（D-U7-01〜03）、ITDR Phase 1（HIBP + Brute Force、Broker 集約、段階活性化、D-U7-04〜06）、Log scrubbing（infra Pool Aggregator + 辞書 M-1〜14、D-U7-07）、Golden 検知 Phase 1 = 4 シグナル（D-U7-08）、Workload Identity（IRSA 規約 + FedID + **private_key_jwt = Phase 2 昇格確定**、D-U7-09〜10）、**ADR-040 復活の取込**（6 Acct 読み替え + /admin 3 層整合 + 監査 Acct 一元、D-U7-11〜12）、PCI ギャップ 3 点 + APPI（Object Lock 7 年 / WebAuthn 必須範囲 / 漏えい SOP / Red Hat DPA ゲート / **zero-egress セキュリティ推奨**、D-U7-13〜16）、Bot/DDoS 分離 + Argon2id 確定（D-U7-17〜18）を決定。
- 2026-07-23 (v1.1): Wave 2 整合性レビュー反映 — §7.2.3 に DR/Game Day ウィンドウの G-2/G-3 自動降格 + Brute Force 感度引上げを追加（M-4）、§7.2.2 HIBP Egress を送信元スコープ拡張（IdP-KC KC Pod CIDR）+ zero-egress 非代替の明記へ拡張（M-5）、§7.5.2 の管理画面 Backend（Broker Acct）/ 専用 API 層（IdP-KC Acct）を 2 行に分割（M-6）、G-PCI-WAF / G-DPA のゲート採番付記（M-11、U1 §1.5 登録）、Event Listener emit セットに REVOKE_GRANT / LOGOUT 系追加（L-1、U5 §5.9.2 受領）、Fluent Bit DaemonSet の KC Pool taint toleration 必須を明記（L-2）。
