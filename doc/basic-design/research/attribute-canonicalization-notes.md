# 検討ノート: 組織属性の正準スキーマ化（顧客 IdP 属性を素通ししない）

日付: 2026-08-05 / 起票理由: ユーザー検討（「顧客 IdP はテナントごとに属性の有無もプロパティも違い動作保証できない。名前・ID 以外の属性はこちらで再定義し、移行時はマッピングにしたい」）を漏れなく設計に残すため。
関連: [03-identity-provisioning-design.md](../03-identity-provisioning-design.md)（D3-01 / D3-15）、[02-keycloak-logical-design.md](../02-keycloak-logical-design.md)（§2.5 Mapper / §2.6 User Profile）、[idp-kc-user-mgmt-authz-boundary-notes.md](idp-kc-user-mgmt-authz-boundary-notes.md)（AZB-1/5）、ADR-018 / ADR-025 / ADR-054。

## 1. 背景・なぜここで決めるか

本基盤は 1000 超の顧客 IdP とフェデレーションする。**顧客 IdP が送ってくる属性は、テナントごとに (a) 有無、(b) クレーム名、(c) 値の意味・粒度・信頼性がバラバラ**である。アプリがこの生クレームに依存すると、**テナントが変わるたびに動作が変わり、動作保証ができない**。

一方、組織属性（部署・上長・コストセンター等）は**アプリ横断で共通に使う**ため基盤が保持する方針（AZB-1 / D3-15）が既に確定している。したがって「基盤が持つとして、その値の出所と形をどう規律するか」を本ノートで確定する。

## 2. 二択と結論

| 案 | 内容 | 判定 |
|---|---|---|
| ① **素通し（pass-through）** | 顧客 IdP のクレームをそのままアプリへ渡す | ❌ **不採用**。有無・名前・値がバラバラ → 動作保証不可、PII 混入、スキーマ膨張 |
| ② **正準スキーマ + 写像（re-define）** | 基盤が**固定の正準スキーマ**を定義し、顧客クレームは**そこへ写像**、無ければ基盤付与 or null。アプリは**正準スキーマだけ**を受領 | ✅ **採用** |

**結論**: 名前・ID（Layer B `external_id` / `username`）以外の属性は**基盤側で正準スキーマとして再定義**し、顧客 IdP からは**写像で取り込む**（移行時は移行マッピング）。**アプリには生クレームを一切渡さず、正準スキーマの契約だけを保証する**。

> この方針は既存決定と整合している（新規の逆転ではなく明文化）：User Profile `unmanagedAttributePolicy=DISABLED`（未宣言属性は保存不可、§2.6）、JIT の Import 属性を `username` / `tenant_id` に限定（ADR-025 §762）、SCIM は Facade の 1 箇所受け（D3-11）。本ノートはこれらを「**属性正準化**」という 1 つの原則として束ねる。

## 3. 正準スキーマ（＝アプリへの契約）

正準スキーマ = **User Profile 明示宣言属性（D3-01 + D3-15）**。アプリが依存してよいのはこの集合のみ。

| 正準属性 | 種別 | 出所（source） | 備考 |
|---|---|---|---|
| `username`（`<tenant>-<userid>`） / `external_id` | 識別子 | 顧客 IdP（写像）or 基盤採番 | 名前・ID は再定義対象外（Layer B、ADR-018） |
| `tenant_id` | 認可キー | IdP Mapper（FORCE 相当） | テナント分離アンカー |
| `department` / `manager_ref` / `job_title` / `cost_center` / `organization` / `division` / `employment_type` / `hire_year` | 組織属性 | **正準スキーマへ写像 or 基盤付与**（本ノートの主対象） | D3-15。JWT 非搭載（API pull） |
| ライフサイクル属性（`provisioned_by` / `scim_active` / `last_login` 等） | 内部 | SPI / SCIM / Admin | Mapper 非対象（顧客クレームで上書きさせない） |

- **`manager_ref` は参照型の正規化**：SCIM Enterprise 拡張の `manager` は complex 参照型（value = SCIM リソース id）なので文字列へ直写像できない。**同一テナント内の `external_id` へ正規化して保存**（Facade が SCIM id → external_id を解決、解決不能は保留キューでリトライ）。D3-15 訂正 1。
- **SCIM Enterprise 拡張で標準的に運べる**のは `employeeNumber / costCenter / organization / division / department / manager`。`employment_type` / `hire_year` はカスタム属性（Facade スキーマ拡張で受理）。D3-15 訂正 2。

## 4. source 解決モデル（(テナント × 属性) ごとに 3 ケース）

正準スキーマの各属性は、テナントごとに次のどれかで埋まる：

| ケース | 条件 | 出所（SoR） | 書込機構 | 例 |
|---|---|---|---|---|
| **① 顧客写像** | 顧客 IdP / HRIS が当該属性を送る | **顧客 IdP/HRIS** | SCIM Facade の Enterprise 拡張写像 / JIT Mapper（該当属性のみ） | Entra が department を送る |
| **② 基盤付与** | 顧客が送らないがアプリが要る | **基盤**（管理画面 authoring） | 管理画面 → Backend/KC 書込 | 工場系で部署を基盤側で採番 |
| **③ 不要** | アプリが要らない | — | 収集しない（宣言もしない） | — |

- **同一属性でもテナントで SoR が変わる**（A 社は顧客写像、B 社は基盤付与）。これはテナントごとの設定で吸収する（属性ごとに「写像元クレーム or 基盤付与」を宣言）。
- **②で基盤付与した値が①の写像で上書きされない保証**：当該属性の Mapper を**非設定 or syncMode=IMPORT で初回のみ**にする（顧客が後から送っても基盤値を保持）。per-Mapper syncMode の運用規約（§2.5.4）に従う。

## 5. アプリへの保証契約

- **アプリは正準スキーマのみを受領**（`/api/me/context` 経由の API pull、JWT 非搭載）。**生の顧客クレームは絶対に渡さない**。
- **各属性は「存在する」か「明示的に null / 未設定」**のいずれか。アプリは**属性欠損を前提に実装**する（テナントによって②が無い＝null があり得る）。
- **未宣言属性は保存段階で破棄**（`unmanagedAttributePolicy=DISABLED`）＝顧客クレームのサイレント混入を物理的に防止。

## 6. hosted / federated と編集可否（AZB-1/5 と接続）

| population | 組織属性の SoR | 管理画面での編集 |
|---|---|---|
| **hosted（IdP なし顧客）** | 基盤（②基盤付与） | ✅ **編集可** |
| **federated（顧客 IdP）** | 顧客 IdP/HRIS（①顧客写像の射影） | ⚠ **読取のみ**（編集しても次の同期で上書き）。編集は顧客側で |

## 7. 移行時マッピング

- 初期移行の既存ユーザーは、**レガシー/顧客側の属性 → 正準スキーマへのマッピング表**を顧客ごとに用意して投入（正準スキーマに無いものは捨てる、足りないものは②基盤付与 or null）。
- 移行後の新規ユーザーは JIT/SCIM の写像で自動的に正準スキーマへ入る。
- マッピング表は B-IDM 系ヒアリング（属性スキーマ・保有率）と連動して顧客ごとに確定。

## 8. 未決・ゲート

- **正準スキーマの最終項目集合**：D3-15 の 8 属性で足りるか（アプリ要件ヒアリングで確定）。拡張は `ext_` プレフィックス + 宣言必須ルール（§2.6 未決）。
- **属性ごとの source 宣言をどこで持つか**（テナント設定 / IdP 設定の一部）→ U3 の SCIM スキーマ設計と同時。
- **G-SPI-Compat / G-UProfile-Email** と連動：email 非保有・依存属性バリデーション（FC-5）を正準スキーマの実機宣言で回避できること。

## 9. 反映先（案）

- **D3-01 / D3-15**：本ノートの「正準スキーマ + source 解決 3 ケース + アプリ保証」を設計制約として明文化。
- **§2.5.4（Mapper syncMode）/ §2.6（User Profile）**：②基盤付与を①写像で上書きしない規約を追記。
- **hearing-checklist（B-IDM 系）**：属性ごとの source（顧客写像 / 基盤付与）を顧客ごとに確認する項目。
