# 15. アラート検知 Lambda 設計

※ ファイル名の alert-routing は変更していない（リンク維持のため）。本章の「アラート検知 Lambda」は旧称 Alert Router（IaC 上のロール名 `alert-router-lambda-role` / 実装ディレクトリ `code-samples/alert-router-lambda/` も識別子のため据え置き）。

前提: [00-basic-design-plan.md](00-basic-design-plan.md) / [11-central-probe-architecture.md](11-central-probe-architecture.md)
実装: [code-samples/alert-router-lambda/](code-samples/alert-router-lambda/) / データ契約: [code-samples/README.md §2.5（4×4 真偽値表）/ §2.7（Alert イベント形式）](code-samples/README.md)

---

## §15.0 前提と背景

**この章で定めること**: 認証実装確認処理が検知した非 OK（CRITICAL/WARN/INFO）を、**適切な担当・SLA の SNS トピックへ振り分ける**仕組み。
**なぜ要るか**: 「全部 Security に飛ばす」と誤検知（token 失効等）で Security を疲弊させる。4×4 分類で担当を分け、**誤った P1 を防ぐ**。

---

## §15.1 分類 → 通知先の対応

認証実装確認処理の `classify.js`（11 章 §11.2.2）が付けた severity/priority で振り分ける。

| severity | priority | routingKey | 通知先 | SLA | 典型 |
|---|:---:|:---:|---|:---:|---|
| CRITICAL | P1 | p1 | Security オンコール | 即時 | 認証 missing（Neg=2xx）|
| WARN | P2 | p2 | Platform チーム | 24h | token 失効 / endpoint 不在 |
| INFO | P3 | p3 | App team | 通常 | Backend バグ（Pos=5xx）|
| OK | — | — | 通知なし | — | 正常 |

```mermaid
flowchart LR
    CC[認証実装確認処理<br/>classify 済み] -->|Alert イベント| AR[アラート検知 Lambda]
    AR --> D{severity}
    D -->|CRITICAL| P1[SNS P1<br/>Security 即時]
    D -->|WARN| P2[SNS P2<br/>Platform 24h]
    D -->|INFO| P3[SNS P3<br/>App team]
    D -->|OK| SKIP[skip]
    style P1 fill:#ffcdd2
    style P2 fill:#fff9c4
    style P3 fill:#c8e6c9
```

実装対応: [`alert-router-lambda/index.js`](code-samples/alert-router-lambda/index.js) + `lib/format.js`（SLA 文言整形）。

---

## §15.2 通知先 ARN の解決

Alert イベント（[README §2.7](code-samples/README.md)。**§2.6 は検査起動イベント**で別物）**自体には SNS ARN が含まれない**。アラート検知 Lambda が解決する:

```mermaid
flowchart TD
    E[Alert イベント<br/>appId/env/severity] --> L{App Registry<br/>alertRouting あり?}
    L -->|Yes| R[alertRouting.pX の ARN]
    L -->|No| DF[環境変数<br/>DEFAULT_PX_TOPIC_ARN]
    R --> PUB[SNS Publish]
    DF --> PUB
```

0. severity から routingKey（p1 / p2 / p3）を決める。**未知の severity は捨てずに P2（Platform）へ寄せる**（検査側と通知側で enum がずれても通知を落とさないための保険。処理設計 通知-01 / M-Q-PD-26）
1. **App Registry（S3 台帳）の `alertRouting {p1,p2,p3}`** を `registry/{appId}/{env}.json` の GetObject で引く（12 章 §12.1）
2. 無ければ **環境変数 `DEFAULT_P1/P2/P3_TOPIC_ARN`** に fallback。**台帳そのものが取得できない場合（不存在・GetObject 失敗）も同様に全社デフォルトへ fallback して通知を続行する**（台帳の一時的な読み取り失敗で P1 通知を落とさない。**通知が届かないより、宛先が粗くても届く方が安全**。処理設計 通知-01）
3. どちらも無ければ ARN 未解決エラー → throw（**リトライ / On-failure Destination（送信先 SQS）**で可視化。MM-5、18 章 §18.5.1）

→ アプリ個別の通知先（alertRouting）と全社デフォルト（環境変数）の 2 段構え。**「解決できない」で止めるのは全社デフォルトすら無いときだけ**で、それ以外は必ずどこかへ届く。

> **Phase 4 検証済み**（[LocalStack](research/phase4-local-verification-results.md)）: probe イベント（ARN なし）→ App Registry から alertRouting.p1 解決 → SNS Publish → 実 MessageId 取得。**本番ルーティング経路が end-to-end 成立**。【注意】当時の検証は **DynamoDB 実装（GetItem）**で行ったもので、現行の台帳は **S3（GetObject）**。解決ロジックの成立自体は変わらないが、API は読み替えること。

---

## §15.3 通知メッセージ

`lib/format.js` が severity 別に SLA 文言を付けて整形:
- Subject: どのアプリ・どの endpoint で何が起きたか
- Body: negStatus/posStatus、reason、対応 SLA（P1 即時 / P2 24h / P3 通常）
- MessageAttributes: severity / priority / appId / env（SNS フィルタ用）

---

## §15.4 バッチ耐性・エラー処理

- probe からの Invoke は **配列が既定**。認証実装確認処理は**同一アプリの検知をまとめて 1 回で送る**（endpoint ごとに invoke すると、1 アプリで大量の認証漏れがあったときに通知が溢れるため。処理設計 認証実装チェック-08）。単一イベントで来ても同じ経路で処理する（後方互換）
- 1 件でも失敗したら throw → Lambda 失敗（既定 2 回リトライ = 1 分後・2 分後 → **On-failure Destination（送信先 SQS）**へ。滞留は MM-5 で検知、18 章 §18.5.1）
- `classify.js` と `format.js` の `SEVERITY_META` が 4×4 の SSOT を共有（分類ずれ防止）

---

## §15.5 設計判断

| ID | 判断 | 根拠 |
|---|---|---|
| D-M-15-1 | 4×4 分類で P1/P2/P3 に振り分け（全部 Security でない）| 誤検知で Security を疲弊させない |
| D-M-15-2 | ARN は App Registry alertRouting → 環境変数デフォルトの 2 段解決。**台帳が取得できない場合も全社デフォルトへ fallback して通知を続行**し、**未知の severity は P2 へ寄せる**（処理設計 通知-01）| アプリ個別 + 全社既定の両立。通知の欠落を防ぐことを最優先（§15.2）|
| D-M-15-3 | 分類ロジックは probe の classify.js と SSOT 共有 | 二重実装のずれ防止 |
| D-M-15-4 | ARN 未解決は throw（リトライ → **On-failure Destination（送信先 SQS）**）| 設定不備を握り潰さず可視化。Destination は試行回数・リクエスト・レスポンスを JSON で残せ、DLQ（本文 + エラー先頭 1KB のみ）より調査が容易（2026-09-14 確定、18 章 §18.5.2）|
| D-M-15-5 | probe からの Invoke は **同一アプリの検知をまとめた配列が既定**（2026-09-15 確定、処理設計 認証実装チェック-08）| endpoint ごとの invoke では 1 アプリの大量検知で通知が溢れる（§15.4）|

---

## §15.6 未決事項

| ID | 内容 |
|---|---|
| M-Q-15-1 | SNS の先（PagerDuty / Slack / メール）の接続方式 |
| M-Q-15-2 | P1 の自動 deny / rollback 連動の要否（05 章 §5.7 のインシデント対応と連携）|
| M-Q-15-3 | 誤検知抑制（同一 endpoint の連続アラート抑制 / dedup）|
