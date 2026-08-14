# ROSA HCP: Red Hat SRE によるライブ Pod ログ可視性 — 深掘り調査と対策

- **日付**: 2026-08-14
- **種別**: research note（G-DPA〔APPI 法 28 条〕の技術的裏付け深掘り）
- **背景**: ログ詳細設計の棚卸し（2026-08-12）で、「保管 3 層はマスク済み・コントロールプレーン監査ログ経路は [ADR-056 L6](../../adr/056-rosa-adoption-decision.md) / 禁則 K-12 で封鎖」まで対処済みだが、**`oc logs`（`kubectl logs`）による稼働中 Pod の stdout 直読み**という経路が、承認・監査・ソース側マスクのいずれも未設計であることが判明。本ノートで一次情報を確定し対策を起票する。
- **関連**: [ADR-056](../../adr/056-rosa-adoption-decision.md)（ガードレール L1-L6）、[07 §7.7.4](../07-security-compliance-design.md)（ログ経路の越境評価）、[07 §7.3.1](../07-security-compliance-design.md)（Log scrubbing M-1〜14）、[09 §9.3](../09-operations-observability-design.md)（ログ 3 層）、[reference/rosa-detailed-analysis.md §11](../../reference/rosa-detailed-analysis.md)、ゲート **G-DPA**（[01 §1.5](../01-architecture-baseline.md)）

---

## 1. 問題の定式化

**マスキング境界が stdout の「下流」にある。**

```
Keycloak Pod ──(stdout 平文)──▶ ノード /var/log/pods ──▶ Fluent Bit ──(M-1〜14 スクラブ)──▶ 3層保管(CW/OpenSearch/S3)
                                    ▲ ここに「マスク前平文」が一旦書かれる
                                    │
                          oc logs / oc debug node / EC2 serial console
                                    │
                             Red Hat SRE（昇格時）
```

- M-1〜14（[DU-U7-04](../00b-design-unit-breakdown.md)）は **Fluent Bit Aggregator（stdout の後段）**で適用される。すなわち保管層は守るが、**ノード上の `/var/log/pods` に書かれる生 stdout はマスクされない**。
- Keycloak は既定でユーザー名・メール・IP・（設定次第で）トークン断片を INFO/DEBUG ログに吐き得る。→ **stdout 生ログ = マスク前 PII**。
- この生ログを読める主体に **Red Hat SRE（HCP のインフラ運用者、越境所在）**が含まれるかが APPI 法 28 条の技術的争点。

---

## 2. 一次情報で確定した事実（ROSA HCP）

出典 URL を各事実に付す。`docs.redhat.com` は WebFetch が 403 のため AWS ミラー / access.redhat.com / rosaworkshop / 検索スニペットで確認（要最終確認は §5）。

### 2.1 アーキテクチャとログの物理所在
| 事実 | 出典 |
|---|---|
| HCP のコントロールプレーン（API server / etcd）は **Red Hat 所有 AWS アカウント**、worker ノード + kubelet は **顧客 VPC**。接続は PrivateLink | AWS blog "Diving into ROSA with HCP" / [docs.aws rosa-architecture-models](https://docs.aws.amazon.com/rosa/latest/userguide/rosa-architecture-models.html) |
| Pod の stdout/stderr は **worker ノード（顧客アカウント）上の `/var/log/pods`・`/var/log/containers` にコンテナランタイムがマスクなしで書く**。`oc logs` は API server → kubelet → ノード上ファイルを読む（K8s 標準挙動、ROSA も `oc logs` 利用を前提化） | [rosaworkshop logging](https://www.rosaworkshop.io/ostoy/9-logging/)（推論部は §5-5） |
| **Red Hat が保持するのはクラスタ監査ログのみ。アプリ/インフラログは収集・集約・転送しない**（顧客が自前で収集） | [access.redhat 6433501](https://access.redhat.com/solutions/6433501) / cloud.redhat.com o11y |

→ 「Red Hat がアプリログを常時吸い上げない」＝**恒常パイプラインには入らない**（07 §7.7.4 の表と整合）。ただしこれは「SRE が必要時に `oc logs` で読めない」ことを意味しない（下記）。

### 2.2 SRE のアクセスモデル（最小権限だが昇格経路あり）
| 事実 | 出典 |
|---|---|
| SRE は **backplane プロキシ経由・最小権限（least privilege）** が原則。定常運用では昇格不要 | [access.redhat 6957082](https://access.redhat.com/solutions/6957082) / [docs.aws infrastructure-security](https://docs.aws.amazon.com/rosa/latest/userguide/infrastructure-security.html) |
| ただし **昇格経路が存在**：手動 SRE アクセスは 4 分類（Red Hat Portal / corporate SSO / **OpenShift elevation via Red Hat SSO** / AWS access/elevation〔60 分制限・完全監査〕）。**OpenShift 昇格時は cluster-admin 相当**＝任意 Pod の `oc logs` が RBAC 上可能 | docs.redhat policies-and-service-definition（スニペット経由） |
| **break-glass では EC2 serial console 経由でノードにアクセスしログ収集**する運用が明記。`oc debug node` も cluster-admin なら可 → ノード上 `/var/log/pods` の生ログへ到達手段あり | [cloud.redhat break-glass](https://cloud.redhat.com/experts/rosa/break-glass/) |
| **全 SRE アクセスは MFA 必須。全認証試行・全変更が実行 SRE の個人識別子付きで監査に記録**、SIEM で 1 年保持 | docs.redhat policies-and-service-definition / [rosaworkshop FAQ](https://www.rosaworkshop.io/rosa/14-faq/) |

### 2.3 顧客が使えるアクセス制御 — Approved Access（中核対策）
| 事実 | 出典 |
|---|---|
| **Approved Access**（旧称/関連: Access Protection / Access Requests）: SRE が昇格アクセスを要求するとクラスタオーナーにメール通知、顧客が承認/拒否。拒否時は SRE がリソースに直接作用できない | [docs.redhat approved-access](https://docs.redhat.com/en/documentation/red_hat_openshift_service_on_aws/4/html/support/approved-access) / [docs.openshift rosa approved-access](https://docs.openshift.com/rosa/support/approved-access.html) |
| **既定では無効。有効化にはサポートチケットが必要** | 同上 |
| CCS モデルの ROSA では **顧客がクラスタ監査ログを閲覧可能**（Cluster Logging Operator → CloudWatch、または未導入時はサポート依頼） | rosaworkshop FAQ / AWS blog security-auditing-in-rosa |
| Private cluster（private API + PrivateLink）は**ネットワーク露出低減であって SRE の論理アクセスは残る**（別経路の IAM/backplane） | docs.aws infrastructure-security |
| SRE 所在（follow-the-sun）地域は **Red Hat Subprocessor List** に委ねられ FAQ 本文は明示せず。地理制限は DPA/OSA 側の契約問題 | [redhat DPA/DPL](https://www.redhat.com/en/about/agreements/dpl) |

---

## 3. 結論：Keycloak Pod の stdout 平文ログを SRE は見られるか

**条件付き Yes。**
- 定常運用では SRE は最小権限で、任意 Pod のログを常時見られる設計ではない。
- **しかし cluster-admin へ昇格した SRE、または break-glass でノードに入った SRE は、Keycloak Pod の stdout 生ログ（マスク前平文）を技術的に閲覧しうる。**
- これは「越境委託先（Red Hat 社員）が委託元の直接管理下にない状態で PII を閲覧しうる」構図であり、**APPI 法 28 条（＋ 25 条 委託先監督）の技術的裏付けが必要**。

**既存 L6 / K-12 では塞げない理由**：L6/K-12 は**コントロールプレーン監査ログ**に Secret/PII のボディが流入しない統制（audit profile 固定）。`oc logs` は **worker ノード上の生ログを読む別経路**で、audit profile とは無関係。

**既存 07 §7.7.4 の「L4 + DPA でカバー」記述の不正確さ**：ADR-056 の **L4 は `kubectl get secrets -A` の中身監査**であって `oc logs` 閲覧を監視しない。よって現状 L4 はこの経路を実際にはカバーしていない（言葉が先走り）。

---

## 4. 対策（3 層 + 契約）

| # | 対策 | 位置づけ | 効果 | 起票先 |
|---|---|---|---|---|
| **① ソース側 stdout マスキング/ログレベル統制** | **根本対策（最優先）** | Keycloak がノードに書く前にマスク＝生 PII をノードに残さない。`oc logs` しても平文が出ない | **DU-U7-16（新）**、K-13 |
| **② Approved Access 有効化（必須化）** | 承認ゲート（補完） | SRE 昇格に顧客承認を必須化。承認/拒否ログを 28 条の委託先監督エビデンスに | ADR-056 採用条件 / DU-U7-16 |
| **③ SRE アクセス監査の顧客保全** | 事後検知/監督記録（補完） | Cluster Logging Operator → CloudWatch で SRE アクセス（個人識別子付き）を顧客側に独立保全 | DU-U7-16 / DU-U9O-02 |
| **④ データ所在の契約統制** | 契約対策 | Subprocessor List / DPA / SCC で SRE 所在と越境根拠（基準適合体制）を整理 | DU-U7-14（G-DPA）|

### 4.1 ① の具体（設計の肝）
- **stdout に PII を出さない**：Keycloak のログ設定を構造化（JSON）＋アプリ層で PII フィールドをマスク/ハッシュ化してから stdout へ。生 PII（email/username/IP/トークン断片）をノードに書かせない。
- **本番ログレベル固定**：本番で `DEBUG`/`TRACE` 禁止（例外スタックトレースへの PII 混入・トークン漏れの温床）。CI/Config lint と日次ドリフト検知で機械強制 → **禁則 K-13**。
- M-1〜14（Fluent Bit 下流）は**保管層の第二防壁**として維持（ソース側で漏れた場合の保険）。二重化の設計意図を明記。
- **限界**：Keycloak が内部的にどこまで stdout マスクできるかは実装検証が要る（イベントリスナ経由のカスタム appender / log MDC フィルタ等）。**PoC/実装で「`oc logs` に PII が出ないこと」を実機確認**する（G-SRE-LogVis）。

---

## 5. 未確認・要確認（Red Hat / 法務）

1. **`oc logs`（read）が顧客取得可能な監査ログに残るか** — OpenShift 監査は get/list を記録しうるが、SRE の「ログ閲覧」read を顧客側から確実に追えるかは一次断定できず。→ Red Hat 確認（**B-SRE-LOG-2**）。
2. **Approved Access が緊急 break-glass（EC2 serial console）もゲートするか** — 昇格アクセスへの承認は明記されるが、真の緊急経路は事後監査型の可能性。→ 確認（**B-SRE-LOG-1**）。
3. **Approved Access の ROSA HCP 対応 GA/対象版数** — support 章は ROSA 4 全般で HCP 包含と解されるが名指し一次記述は未取得（docs 403）。→ 現行版で確認（**B-SRE-LOG-1**）。
4. **SRE 所在地域の地理制限を契約保証できるか** — Subprocessor List / DPA 実物確認（**B-DPA-2**、DU-U7-14 連動）。
5. **`/var/log/pods` 経路の ROSA 固有明示** — ノード生ログ保存と kubelet 経由読み出しは K8s 標準挙動からの推論。ROSA 固有図での明示ソース未取得（実害は §3 の結論を変えない）。

---

## 6. 起票サマリ（本ノートから発行）

- **ゲート G-SRE-LogVis**（新）: 「`oc logs` に PII が出ないソース側マスキング + Approved Access 有効化 + SRE アクセス監査の顧客保全」の実機確認。**G-DPA の技術的裏付け**として紐付け。
- **DU-U7-16**（新）: SRE ライブログ可視性対策（① ソース側 stdout マスキング + 本番ログレベル固定 + ② Approved Access 有効化 + ③ SRE アクセス監査の顧客保全）。
- **禁則 K-13**（新）: 本番ログレベル `DEBUG`/`TRACE` 禁止 + stdout への生 PII 出力禁止（CI/Config lint + 日次ドリフト検知）。
- **ADR-056 ガードレール L7**（新）: ライブ Pod stdout/`oc logs` 経路の統制（①②③）。**Approved Access 有効化を採用条件に追加**。
- **ヒアリング**: B-SRE-LOG-1 / B-SRE-LOG-2 / B-DPA-2。
- **07 §7.7.4 修正**: 「残る論点」を正確化（L4 は本経路を覆わない旨 + L7/G-SRE-LogVis へ委譲）。
