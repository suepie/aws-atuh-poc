# 要件マッピングのレビュー対応（2026-09-07）

- **経緯**: 要件マッピング（177 要件 × ①②③④）を要件定義書・基本設計・ADR・WBS と突合したレビューで、担当境界の抜けと 9/2「Realm 統合」→ 9/6「2 台構成へ戻す」の未伝播を検出。ユーザー判断 5 件を受けて SSOT を更新した
- **反映済み**: `wbs-text/SHEET_*.tsv` 7 本（スクリプト `wbs-text/apply_req_mapping_fix_2026-09-07.py`、差分一覧 `wbs-text/SYNC_reqfix_2026-09-07.tsv` 200 件）＋ **同日追加決定 P1〜P4**（`wbs-text/apply_owner_split_2026-09-07.py`、差分 `wbs-text/SYNC_owner_split_2026-09-07.tsv` 188 件、§7）
- **未反映**: Excel（§4 の指示で全面置換）、設計書・ADR・要件定義書（§5 の一覧に沿って改訂）

---

## 1. 決定（ユーザー 2026-09-07）

| # | レビュー指摘 | 決定 | SSOT への反映 |
|---|---|---|---|
| 1 | Keycloak-Broker ⇄ Keycloak-IdP の連携が要件にも WBS にも無い | **追加する** | 要件 FR-FED-015 新設。機能名 F-AUTH-09 を復活（「Realm 統合により対象外」を撤回）。① HB-F-AUTH-09 / HE-23 / HI-11、② DDB-18 / DDE-11 / DDI-10、③ MKA-20 / MKB-30 / MKI-19、④ IT-16 / ST-28 |
| 2 | Keycloak-IdP 側の非機能の担当が未定義 | **追加する。ただし「アプリ責務として整理する」意図は残す** | 要件マッピングに **15 列目「Keycloak-IdP 側」** を追加し、非機能 63 行に「アプリ（Keycloak-IdP 側でも同じ要件を満たす。本基盤は ROSA の引き渡しまで）」を入れた。責任分界そのものは要件 **NFR-OPS-012** + ① **D-21 責任表** で明文化 |
| 3 | 停止・削除の伝播（shadow 無効化）が消えている | **伝播は作らない。** Keycloak-IdP 側で止めた後に残るのは Keycloak-Broker のセッション上限までで、**上限は 12 時間**（従来 24 時間から変更） | F-PROV-12 / F-PROV-13 / F-BAT-02 の理由を「Realm 統合により対象外」→「伝播しない、12 時間で受容」に書き換え。FR-USER-006 / FR-SSO-008 / NFR-SEC-005 の概要に 12 時間を明記。**ADR-064（outbox + shadow 制御）と U3 D3-17 は Phase 1 対象外化が必要**（§5） |
| 4 | パスワード要件 6 行が ROSA 引き渡し作業に紐付いている | **その通り** | FR-AUTH-001 / 009 / 010 / 012、FR-USER-004、NFR-SEC-009 の ①〜④ を空にし、状況を「アプリ側で実施（Keycloak-IdP 側。本基盤は ROSA の引き渡しまで＝NFR-OPS-012）」に。引き渡し行（HJ-20 / DDG-01 / MKA-01 / MKJ-01 / IT-03）は新機能名 **F-AUTH-29「Keycloak-IdP 側の引き渡しと責任分界」** に付け替え |
| 5 | WBS(基本設計) の見出しが旧値（754 / 704 / Realm 統合 / DR 対象外） | **修正対象** | Excel 側の固定文（§4.3） |

> **12 時間について**: SSOT では「上限 12 時間」で統一したが、設計書側は P-09 / U5 §5.2.2 / U2 §2.2.5 が「絶対 24h」のまま。§5 で改訂対象に挙げた。NIST AAL2 の上限は 24 時間なので 12 時間は厳しい側であり、設計上の支障はない。

---

## 2. 追加した要件（漏れ 9 件）

| 要件ID | 項目 | 構築場所 / 担当 | ① | ② | ③ | ④ | 備考 |
|---|---|---|---|---|---|---|---|
| **FR-FED-015** | Keycloak-Broker ⇄ Keycloak-IdP 連携 | Keycloak-Broker / インフラ | HB-F-AUTH-09 HE-23 HI-11 | DDB-18 DDE-11 DDI-10 | MKA-20 MKB-30 MKI-19 | IT-16 ST-28 | HE-23 は **要求仕様としてアプリチームへ渡す接続仕様**（broker-rp Client・返す項目・login_hint 書式・ログアウト連鎖・上限 12 時間・閉域単方向）。IT-16 の前提は「アプリチームの Keycloak-IdP が検証環境で起動していること」 |
| **NFR-OPS-012** | Keycloak-IdP 側の構築・運用の責任分界 | Keycloak-IdP / インフラ（ROSA まで） | D-21 HJ-20 | DDG-01 | MKA-01 MKJ-01 | IT-03 | D-21 = 非機能要件ごとに Keycloak-IdP 側の担当を表にする（列「Keycloak-IdP 側」の根拠） |
| **NFR-SEC-021** | 運用者アカウントと権限の保護 | Keycloak-Broker / インフラ | G-1.6 G-5.6 HG-09 | DDB-19 DDG-11 | MKA-17 MKB-31 | OP-09 SEC-10 | ADR-040 Phase 1 α（WebAuthn 必須・常時全権の禁止・Break-Glass）。FR-MFA-009 の「運用者分」はここで満たす |
| **FR-USER-013** | 長期未使用ユーザの自動停止（90 日） | Keycloak-Broker / インフラ | HB-F-BAT-01 | DDF-05 | MKF-06 | ST-29 | 顧客IdP 経由で自動作成したユーザのみ。要否は B-JIT-LC-1 で最終確認 |
| **NFR-SEC-022** | サプライチェーン対策（依存の検査・イメージ署名・部品一覧） | Keycloak-Broker / インフラ | HJ-06 HJ-22 | DDH-02 | MKA-21 MKC-05 | SEC-09 | ADR-046 Phase 1 = SLSA L2。テスト SEC-09 だけが先行していた |
| **NFR-SEC-023** | 不正兆候の検知 | Keycloak-Broker / インフラ | HH-06 | DDG-14 | MKH-07 | OP-12 | ADR-035 Phase 1a = 検知して通知するまで、自動遮断なし |
| **NFR-OPS-013** | 環境構成（本番 / 検証 / 開発） | Keycloak-Broker / インフラ | HH-05 | DDG-05 | MKA-07 MKA-08 | IT-13 TE-01 TE-02 | 既存行に紐付けただけ（新規作業なし） |
| **NFR-SEC-010-2** | 侵害クレデンシャル検出 | Keycloak-IdP / アプリ | — | — | — | — | 要件定義書にあったが転記漏れ |
| **FR-AUTH-016** | 利用規約への同意取得と記録 | Keycloak-Broker / インフラ | D-22 | — | — | — | 要否未確定。判断 0.5 人日のみ計上（状態「要件確認」） |

あわせて **FR-INT-006（管理 REST API）** に本基盤側の受け口 **F-INT-14「管理 API の内部公開（idm-api 向け）」**（HE-24 / DDE-12 / MKB-32 / IT-17）を追加し、FR-SSO-010・FR-USER-001（管理画面からの操作）をここに紐付けた。

---

## 3. 矛盾の修正（確認用）

適用済み。戻す場合は `SYNC_reqfix_2026-09-07.tsv` の旧値を使う。

| # | 要件 | 修正 |
|---|---|---|
| C1 | FR-AUTH-011 アカウントロック | Keycloak-IdP 側のパスワードロック（アプリ）。Keycloak-Broker の実在推測防止（HB-F-AUTH-21 系）は NFR-SEC-010 のみに残し、本行の ①〜④ は空に |
| C2 | FR-FED-012 MFA 重複回避 | 担当「顧客」→ **Keycloak-Broker / インフラ**。追加認証は顧客IdP／Keycloak-IdP の責務だが、追加認証済みの印（amr）を取り込み二重に求めない設定は Keycloak-Broker 側 |
| C3 | FR-SSO-003 / FR-AUTHZ-007 / FR-INT-007 / NFR-PERF-003 | 廃止行 HK-03 の参照を GD-22 / GD-16 / GD-18 に置換。項目名から「Lambda Authorizer」を外し「API 入口での JWT 検証」に |
| C4 | NFR-SEC-011 WAF / NFR-SEC-012 DDoS | 「Phase 1 では作らない」→ **対象・担当「他組織」**。① HG-08 + 新規 **HK-10 境界への要求仕様書**、③ MKA-04、④ IT-11 / SEC-05 |
| C5 | NFR-DR-003 / NFR-DR-008 | DR-003 の概要に「手動・大阪で作り直し、D-18.2 待ち、顧客希望 RTO 1 日との差は D-18.1 で明示」。**DR-008 セッション維持は対象外**（作り直す方式では引き継げない。再ログイン前提を DR-02 で確認） |
| C6 | FR-FED-013 | 「IdP を選べる」→「識別子から自動で振り分ける（HRD）。一覧は見せない。1 顧客に複数ある場合のみ選ばせる」 |
| C7 | FR-ADMIN-007 監査ログ閲覧 | 「参照は共通基盤側、本基盤に照会画面は作らない」を明記 |
| C8 | FR-SSO-009 / NFR-SEC-008 失効 | 「セッションとリフレッシュトークンは即時失効、アクセストークンは最大 30 分残る」を明記 |
| C9 | FR-SSO-010 / FR-USER-001 | 本基盤側の受け口（F-INT-14）を ①〜④ に付け、状況を「アプリ側で実施（本基盤にも 4 工程あり）」に |
| C10 | FR-USER-011 / NFR-COMP-009 消去 | 消去対象は Keycloak-Broker・Keycloak-IdP（アプリ）・権限データ（アプリ）・共通ログ基盤にまたがる。HK-07 は横断手順 |
| C11 | NFR-PERF-006 | 「API Gateway スロットリング」→「流量制限（同時受付数の上限）」。境界側は NFR-SEC-011 |
| C12 | NFR-SCL-004 / NFR-OPS-011 | 他組織の外向き許可追加（当日〜翌日）を含むことを明記 |
| C13 | NFR-COST-006 RHBK | 「確定（ROSA に内包・追加費用なし、P-01）」。①〜④ は空に |
| C14 | NFR-COMP-006 / FR-USER-007 | 対象外なのに付いていた SEC-06 / HB-F-PROV-07 を外す |
| C15 | FR-FED-001 Auth0 | 理由に「PoC の代替。Phase 1 の契約対象かは要確認」 |
| C16 | FR-USER-006 停止 | 「Keycloak-IdP 側で止めた写しは伝播しない。12 時間で受容」 |
| C17 | FR-SSO-008 / NFR-SEC-005 | 上限 12 時間（旧 24 時間）、リフレッシュトークンはセッションに従属 |
| C18 | NFR-SEC-019 内部通信 | 「Lambda → Keycloak」→「idm-api → 管理 API、Keycloak-Broker → Keycloak-IdP」。① HE-23 / HE-24、④ IT-16 / IT-17 を追加 |
| C19 | FR-MFA-009 管理者 MFA | 顧客の管理者分はアプリ、本基盤運用者分は NFR-SEC-021 |
| C20 | NFR-AVL-001 SLA | 顧客IdP を持たない顧客のログインは Keycloak-IdP（アプリ運用）にも依存する。約束の範囲と除外条件を HK-02 で明示 |
| — | HJ-10b / HB-F-AUTH-01 | HJ-10b のスコープ理由「Keycloak-Broker を 1 つに統合」→「Keycloak-IdP 側の責務」。HB-F-AUTH-01 は運用者分のみの仕様書に縮小 |

### 3.1 要判断 → 同日決定済み（§7）

| # | 内容 | 決定（2026-09-07） |
|---|---|---|
| P1 | ③ MKA-12 / MKA-13 が手動・作り直し方式と食い違う | 推奨どおり文言修正（人日据え置き）。D-18.2 で方式が覆れば戻す |
| P2 | FR-FED-001 Auth0 | **対象のまま**（PoC の接続を RI-02 に流用） |
| P3 | FR-USER-013 90 日自動停止 | **対象で計上** |
| P4 | 担当列の 6 者分割 | **分ける。複数の担当が実作業を持つ要件は枝番で行を分ける**（23 要件 → 46 行） |

---

## 4. Excel への指示

### 4.1 シートの全面置換（7 本）

`wbs-text/SHEET_*.tsv` で該当シートの表部分を全面置換する（見出しの固定文は残す）。

| シート | TSV | 行数 | 人日 |
|---|---|---:|---|
| WBS(基本設計) | SHEET_基本設計.tsv | 158 | 全量 233.5 / 対象 220.5 |
| WBS(詳細設計_製造) | SHEET_詳細設計_製造.tsv | 181 | 詳細設計 184 / 製造 276.5 |
| WBS(テスト) | SHEET_テスト.tsv | 94 | 345 |
| 要件マッピング | SHEET_要件マッピング.tsv | **209**（15 列。枝番で分けた 23 要件を含む） | — |
| 機能名一覧 | SHEET_機能名一覧.tsv | 140 | 集計列は再計算済み |
| 機能グループ一覧 | SHEET_機能グループ一覧.tsv | 33 | 同上 |
| サマリ(工程別) | SHEET_サマリ工程別.tsv | 83 | 合計 **1026** |

変化: ① 218.5 → 233.5（+15）／ ② 174.5 → 184（+9.5）／ ③ 259 → 276.5（+17.5）／ ④ 331 → 345（+14）／ 合計 969.5 → **1026（+56.5）**。

### 4.2 要件マッピングの列（12 → 15 列）

要件ID / 種別 / 優先度 / 要件実現対象 / 構築場所 / 担当 / 担当の理由 / 項目 / 概要 / ① 基本設計 / ② 詳細設計 / ③ 製造 / ④ テスト / 状況 / **Keycloak-IdP 側**

- 担当は **6 値**: インフラ（本基盤）/ アプリ（Keycloak-IdP）/ アプリ（業務アプリ）/ アプリ（管理画面・idm-api）/ 顧客（顧客IdP）/ 他組織（境界・共通基盤）。対象外は「—」
- 複数の担当が実作業を持つ要件は **要件ID に枝番（-a / -b）** を付けて行を分け、項目名の末尾に「（本基盤運用者）」などの補足を付けた。枝番の a は元の行を引き継ぐ（§7.2）
- 状況の値を追加: 「アプリ側で実施（Keycloak-IdP 側…）」「他組織で実施（本基盤は要求仕様と受入確認）」「要件確認（判断のみ計上）」「確定（RHBK は ROSA に内包…）」
- 「Keycloak-IdP 側」列の値: アプリ（主体）16 / アプリ（Keycloak-IdP 側でも同じ要件を満たす。本基盤は ROSA の引き渡しまで）63 / 本基盤（ROSA 引き渡しまで）→ アプリ 1 / その他の個別注記 12 / — 94

### 4.3 見出しの固定文（手で直す）

**WBS(基本設計) 1〜5 行目**は 9/2 時点の数字と決定（754 / 704、Realm 統合、DR 対象外、案①②③）のままなので、次の 2 行に差し替える。

> WBS ① 基本設計 — 全量 233.5 人日 / 対象 220.5 人日 / 158 行（「スコープ」列で「対象」を絞れば今やる分。対象外 13.0 ＝ 省略・吸収 7 行 10.0 ＋ Keycloak-IdP 側の責務 3 行 3.0）
> ★前提（2026-09-07）: Keycloak-Broker と Keycloak-IdP の 2 台構成。Keycloak-IdP は ROSA の引き渡しまでが本基盤、以降はアプリ責務（D-21 責任表）。停止の伝播は作らず、セッション上限 12 時間で受容。担当・スコープ・当初想定の語彙は変更なし

**WBS(詳細設計_製造) / WBS(テスト) の 1〜4 行目**も旧値（473 / 743 / 429 等）のまま。それぞれ「② 184 / ③ 276.5、181 行」「④ 345 人日、94 項目」に直す。

### 4.4 検収

1. サマリ(工程別) の合計が 1026、行数 83
2. 要件マッピングの ①〜④ の ID が全部 WBS に存在する（参照切れ 0、HK-03 参照 0）
3. 機能名一覧の 行数 / 人日 / うち対象 が WBS(基本設計) と一致（F-AUTH-01 は 2 行 2.5・うち対象 0.5、F-AUTH-29 は 2 行 3、F-AUTH-09 は 3 行 4.5）
4. 状況の集計: 全工程あり 114 / 一部 10 / アプリ側 42 / 顧客側 3 / 他組織 8 / 対象外 22 / 別シート 8 / 確定 1 / 要件確認 1（計 209）
5. 担当の集計: インフラ（本基盤）134 / アプリ（Keycloak-IdP）18 / アプリ（管理画面・idm-api）16 / アプリ（業務アプリ）8 / 他組織 8 / 顧客 3 / — 22

---

## 5. 設計書・ADR・要件定義書の改訂一覧（未着手）

SSOT と設計書の間で今ずれているのは次の 3 点。**(a) 12 時間**、**(b) 停止伝播の対象外化**、**(c) 新要件 ID**。

| 優先 | 文書 | 箇所 | 内容 |
|---|---|---|---|
| 🔴 | [01-architecture-baseline.md](../01-architecture-baseline.md) | P-09 / P-17 / §1.2 | (a) 絶対 24h → **12h**。(b) Broker Acct の「shadow 制御 Lambda」を Phase 2 へ。P-17 を「2 クラスタ確定、Keycloak-IdP は ROSA 引き渡しまで本基盤・以降アプリ責務」で再凍結。前提 **P-21（Keycloak-IdP 責任分界）** を採番 |
| 🔴 | [05-token-session-authz-design.md](../05-token-session-authz-design.md) | §5.2.2 D-U5-02 / §5.2.4 / §5.5.1 | (a) SSO Session Max 24h → 12h（RT 実効寿命も 12h）。§5.5.1 idpkc-oidc01 ログアウト連鎖 ON は維持（FR-FED-015 の一部） |
| 🔴 | [02-keycloak-logical-design.md](../02-keycloak-logical-design.md) | §2.2.2〜2.2.5 | (a) §2.2.5 #2 の IdP-KC Realm TTL 同値を 12h に。(c) §2.2 冒頭に「IdP-KC 側は アプリ責務。本節の IdP-KC 側項目は接続仕様 HE-23 としてアプリへ渡す要求仕様」を明記 |
| 🔴 | [03-identity-provisioning-design.md](../03-identity-provisioning-design.md) | D3-17 / §3.x shadow 図 | (b) 「IdP-KC トリガーのイベント駆動 shadow 無効化 + 日次リコンサイル」を **Phase 1 対象外**（12h 受容）に。90 日バッチの idpkc 除外規則は維持（FR-USER-013） |
| 🔴 | [ADR-064](../../adr/064-deprovisioning-propagation-outbox.md) | Status | (b) Phase 1 では実装しない旨を Status に追記（Deferred）。理由 = 残存窓 12h を受容 |
| 🟠 | [ADR-063](../../adr/063-brand-unit-architecture.md) | §Broker 責務表 / Open Items | (b) 「Broker shadow（遮断キルスイッチ）」「中央 shadow 制御 Lambda」を Phase 2 に格下げ |
| 🟠 | [06-infra-network-design.md](../06-infra-network-design.md) | §6.1 Broker Acct 表 / §6.3 クロスアカウント 8 経路 | (b) 「削除 shadow bus」経路を Phase 2 に（8 → 7 経路）。D-U6-06 PrivateLink は FR-FED-015 の根拠として維持 |
| 🟠 | [06a-network-flow-diagrams.md](../06a-network-flow-diagrams.md) / [09](../09-operations-observability-design.md) / [10](../10-integration-migration-design.md) / [00b](../00b-design-unit-breakdown.md) | shadow 関連の図・DU 行 | (b) 同上の注記 |
| 🟠 | [02a-broker-idpkc-federation.md](../02a-broker-idpkc-federation.md) | §0 / §3 | (a) TTL 表を 12h に。(c) 冒頭に責任分界（IdP-KC 側 = アプリ）を追記 |
| 🟠 | [functional-requirements.md](../../requirements/functional-requirements.md) | §2 / §1 / §6 / §5 / §8 | (c) FR-FED-015 / FR-AUTH-016 / FR-USER-013 を追加。FR-AUTHZ-007 / FR-INT-007 の項目名から Lambda Authorizer を外す。FR-FED-013 の文言修正 |
| 🟠 | [non-functional-requirements.md](../../requirements/non-functional-requirements.md) | §4 / §6 / §5 / §8 | (c) NFR-SEC-021 / 022 / 023、NFR-OPS-012 / 013 を追加。NFR-SEC-011 / 012 を「他組織提供・要求仕様は本基盤」に。NFR-DR-008 対象外。NFR-PERF-006 / NFR-SEC-019 の項目名修正。NFR-SEC-005 実効 12h。NFR-COST-006 確定 |
| 🟡 | [hearing-checklist.md](../../requirements/hearing-checklist.md) | C-206-3 / 新規 | (a) 絶対経過タイムアウトの回答 = 12h。(c) **B-IDPKC-1「Keycloak-IdP 側の責任分界の合意」**を Phase 1 契約前ゲートに追加 |
| 🟡 | [customer-explanation/01-login-session.md](../../requirements/customer-explanation/01-login-session.md) / [04-security.md](../../requirements/customer-explanation/04-security.md) / [common/session-lifecycle-and-flows.md](../../common/session-lifecycle-and-flows.md) | 24 時間の記述 | (a) 12 時間へ。`grep -nE "絶対 ?24|Max ?= ?24|24 時間"` で洗い出す（供給網の「Critical 24h」など無関係の 24h と混同しないこと） |
| 🟡 | [ADR-033](../../adr/033-keycloak-2tier-broker-idp-architecture.md) / [ADR-056](../../adr/056-rosa-adoption-decision.md) | 責任分界 | (c) IdP-KC クラスタは ROSA 引き渡し後アプリ運用。SRE 分界表に「Keycloak-IdP のアプリ責務」列を追加 |
| 🟡 | [ADR-040](../../adr/040-pam-jit-admin-privilege-management.md) | §I | (c) NFR-SEC-021 / HG-09 との対応を追記（P1-01 は HK-10、P1-07 は HG-04/05 で既に計上） |

---

## 6. 決定の要約（SSOT に埋め込んだ文言）

- **伝播しない**: 「片方で止めた事実をもう一方へ必ず伝える。2026-09-07 決定: 伝播しない。Keycloak-IdP 側で止めた後の残存は Keycloak-Broker のセッション上限（12 時間）で受容する」（F-PROV-12 / 13 / F-BAT-02）
- **引き渡し境界**: 「Keycloak-IdP 用の基盤（ROSA）をどこまで作って渡すか、渡した後の非機能（可用性・復旧・監視・更新・鍵・ログ）を誰が持つか。本基盤は ROSA の引き渡しまで、以降はアプリ責務」（F-AUTH-29 / NFR-OPS-012 / D-21）
- **接続仕様は要求仕様**: 「Keycloak-IdP 側の Client・Realm 設定は要求仕様（HE-23）としてアプリチームへ渡す」（F-AUTH-09 / FR-FED-015）

---

## 7. 同日追加決定（P1〜P4）の反映

### 7.1 P1〜P3

| # | 反映 |
|---|---|
| P1 | ③ MKA-12「データ複製の設定」→「控えの別地域への複製の設定（スナップショットが切替先へ複製され、遅れが監視できる）」、MKA-13「切替と切り戻しの自動化」→「再構築手順のコード化（切替と切り戻し）」。人日は据え置き |
| P2 | FR-FED-001 の理由を「Auth0 も Phase 1 の対象。PoC の接続を実機突合（RI-02）に流用」に |
| P3 | FR-USER-013 の理由を「対象で計上」に |

### 7.2 P4 担当の 6 者分割

**振り分け（行を分けないもの）**: 旧「アプリ」37 行を、パスワード・MFA・移行系 17 行 → アプリ（Keycloak-IdP）、認可判定 3 行 → アプリ（業務アプリ）、ユーザ・ロール・管理画面系 10 行 → アプリ（管理画面・idm-api）に振り分けた。旧「インフラ」は インフラ（本基盤）、旧「他組織」は 他組織（境界・共通基盤）。

**枝番で分けた 23 要件**（a = 元の行を引き継ぐ側）:

| 要件 | a | b |
|---|---|---|
| FR-AUTH-001 ID/PW 認証 | インフラ: 本基盤運用者（HB-F-AUTH-01 / HG-09 / DDB-19 / MKB-31 / SEC-10） | アプリ（Keycloak-IdP）: 顧客のユーザ |
| FR-FED-012 MFA 重複回避 | インフラ: amr の取り込み | 顧客: 追加認証の実施（RI-01） |
| FR-SSO-003 / FR-AUTHZ-007 / FR-INT-007 / NFR-PERF-003 | アプリ（業務アプリ）: 実装 | インフラ: ガイド・サンプル（GD-16/18/22, DDJ-05, MKJ-05, UAT-04） |
| FR-SSO-010 / FR-USER-001 | アプリ（管理画面・idm-api）: 画面と API | インフラ: 受け口 F-INT-14（HE-24 / DDE-12 / MKB-32 / IT-17） |
| FR-AUTHZ-001 クレーム認可 | インフラ: JWT に載せる側 | アプリ（業務アプリ）: 判定する側 |
| FR-AUTHZ-002 テナント分離 | インフラ: 認証側の越境防止と tenant_id | アプリ（管理画面・idm-api）: 権限データ側の越境防止 |
| FR-USER-006 停止 | インフラ: Keycloak-Broker 側 | アプリ（管理画面・idm-api）: 操作画面（IT-17） |
| FR-USER-011 / NFR-COMP-009 消去 | インフラ: 窓口と Keycloak-Broker 側 | アプリ（管理画面・idm-api）: 権限データ側（OP-04） |
| FR-FED-011 オンボーディング | インフラ: 本基盤側の登録 | 顧客: 自社 IdP 側の設定（UAT-02） |
| FR-USER-003 SCIM | インフラ: 受信側 | 顧客: 送信側（RI-04） |
| NFR-SEC-011 WAF / NFR-SEC-012 DDoS | 他組織: 境界側の実装（MKA-04 / SEC-05） | インフラ: 要求仕様 HK-10 と受入確認 |
| NFR-SCL-004 / NFR-OPS-011 リードタイム | インフラ: 本基盤側の作業 | 他組織: 外向き許可の追加（当日〜翌日） |
| FR-ADMIN-007 閲覧 / NFR-OPS-003 保存期間 / NFR-OPS-004 検索 / NFR-COMP-007 法令保存 | インフラ: 出力・項目・保持年数の指定 | 他組織（共通基盤）: 保管・検索・閲覧（OP-03） |

**Excel への追加指示**: 要件マッピングは 209 行に増えるので、§4.1 の全面置換で取り込む。テストの「対応要件」列は枝番なしの要件ID のままで、前方一致で読む。

**要件定義書への波及**: 枝番は Excel 側の管理単位で、要件定義書の ID は増やさない。ただし FR-AUTHZ-001/002・FR-USER-006/011 の「アプリ側の責務」の文言は §5 の改訂時に本文へ写す。
