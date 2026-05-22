# §FR-API-3 流量制御・クォータ

> 元データ: [../hearing-checklist.md B-3](../hearing-checklist.md#b-3-流量制御課金fr-api-3-fr-api-4)
> 対象: アプリリード / アーキテクト
> 関連章: [§FR-API-3](../proposal/fr/03-throttling-quota.md)

---

### 【既定 throttle 値の妥当性】 (API-B-301, 🟡)

本標準では暫定の throttle 標準値を以下で提示しています。妥当性をご評価ください：

| カテゴリ | Rate（RPS） | Burst |
|---|---:|---:|
| Public B2C | 1,000 / API key | 2,000 |
| Internal microservice | 5,000 / service | 10,000 |
| Partner B2B | 100 / API key | 200 |

既存アプリのピーク TPS に基づき、調整提案がございましたらご教示ください。
**目的**: [§FR-API-3 §3.1](../proposal/fr/03-throttling-quota.md) の標準値確定。アカウントレベル既定 10,000 RPS から逆算した値です。

---

### 【アカウント throttle 予防的増枠】 (API-B-302, 🟡)

AWS アカウント全体の throttle 上限（既定 10,000 RPS）を、**本番リリース前に予防的に増枠申請する**方針はいかがでしょうか。
- 現行のままで運用、必要時に増枠
- 本番アカウント全件で予防的増枠（例：50,000 RPS）
- アプリ別に判断
**目的**: [§FR-API-3 §3.1 / §NFR-API-3 §3.3](../proposal/nfr/03-scalability.md) のアカウントクォータ管理。増枠リードタイム（通常 1-3 営業日）が本番障害につながる事例を防ぎます。

---

### 【メソッド単位の標準化】 (API-B-303, 🟢)

throttle をメソッド単位（GET / POST 別）で標準化する方針はありますか。
- 全メソッド統一値
- 書き込み系（POST/PUT/DELETE）は厳しく、読み取り（GET）は緩く
- アプリ個別判断
**目的**: [§FR-API-3 §3.1](../proposal/fr/03-throttling-quota.md) の粒度。書き込み系厳格化は DDoS と DB 過負荷対策に有効です。

---

### 【商用 API への quota 全面適用】 (API-B-311, 🟡)

quota（日次 / 月次累積）を商用 API に **全面適用** するか、内部利用（テスト・社内）は **無制限** とするか、ご見解をお願いします。
**目的**: [§FR-API-3 §3.2](../proposal/fr/03-throttling-quota.md) の運用範囲。無制限を許容すると **内部利用の暴走でコスト爆発**するリスクがあります。

---

### 【quota 超過時の課金モデル】 (API-B-312, 🟡)

quota 超過時の挙動を、**追加課金（オーバーエージ）** / **ハードカット（429 でブロック）** のどちらにする方針が望ましいかご教示ください。
- 追加課金：顧客都合で停止しない、ただし請求事務が複雑化
- ハードカット：シンプル、ただし業務影響あり
- プラン別に異なる挙動
**目的**: [§FR-API-3 §3.2 / §NFR-API-8](../proposal/nfr/08-cost.md) の事業モデル整合。

---

### 【月初リセットのタイムゾーン】 (API-B-313, 🟢)

月次 quota の月初リセットのタイムゾーンを、UTC / JST のどちらにする方針ですか。
**目的**: [§FR-API-3 §3.2](../proposal/fr/03-throttling-quota.md) のリセット仕様。Partner 契約書記載・利用者通知の前提となります。

---

### 【429 アラート化しきい値】 (API-B-321, 🟢)

429（Too Many Requests）の発生率をアラート化するしきい値をご教示ください。
- 例：5min 移動平均で 1% 超え → 通知 / 5% 超え → エスカレーション
**目的**: [§FR-API-3 §3.3 / §NFR-API-6 §6.1](../proposal/nfr/06-operations.md) の運用監視。

---

### 【429 を SLO 対象とするか】 (API-B-322, 🟢)

429 応答を可用性 SLO（[§NFR-API-1](../proposal/nfr/01-availability.md)）の **エラーとしてカウントするか / 対象外とするか**、ご見解をお願いします。
本標準は **正当なレート制限による 429 は SLO 対象外** とするのが妥当と考えていますが、ご意見をいただきたいです。
**目的**: SLO の計算基準を明確化し、誤った可用性低下評価を防ぎます。

---

### 【HTTP API で quota 要件あるなら】 (API-B-341, 🟡)

HTTP API（Usage Plan 非対応）を採用しているアプリで、後からテナント単位 quota 要件が発生した場合、**REST API へ移行**するか **自前実装**（Lambda Authorizer + DynamoDB カウンタ）を許容するか、ご見解をお願いします。
**目的**: [§FR-API-3 §3.4](../proposal/fr/03-throttling-quota.md) の代替手段選定。本標準で「HTTP API → REST 移行が推奨経路」と明示するかが分岐点です。

---

### 【自前実装のコスト試算】 (API-B-342, 🟢)

自前 quota 実装（Lambda Authorizer + DynamoDB アトミックカウンタ）を採用する場合の、DynamoDB スキーマ・コスト試算をご教示ください（既存事例があれば）。
**目的**: [§FR-API-3 §3.4](../proposal/fr/03-throttling-quota.md) の自前実装テンプレ提供可否判断。

---

## 利用者識別（§FR-API-4 §4.1）

### 【テナント識別子の主軸】 (API-B-401, 🔥)

マルチテナント運用するアプリにおいて、**テナント単位のメインの識別子** を **API Key** か **JWT カスタムクレーム（`tenant_id`）** のどちらにする方針が望ましいかご教示ください。
- **API Key 主軸**：B2B SaaS 型、Usage Plan と一体運用
- **JWT クレーム主軸**：マルチテナント SPA / モバイル型、JWT で完結
両者の併用も可能ですが、計測の主軸を 1 つに決める方が運用容易です。
**目的**: [§FR-API-4 §4.1 / §4.2](../proposal/fr/04-metering-billing.md) の計測パイプライン設計。主軸が決まると EMF カスタム次元・access log の必須フィールドが決まります。

---

### 【API Key のマスク方針】 (API-B-402, 🟡)

ログ・メトリクスに API Key を出力する際のマスク方針をご教示ください。
- 完全マスク（`***`）
- 先頭 4 + 末尾 4（例：`abc1***xyz9`）
- ハッシュ化（SHA-256 truncated）
**目的**: [§FR-API-4 §4.1 / §FR-API-8 §8.1](../proposal/fr/08-observability.md) の PII / シークレット保護。トラブルシュートと漏洩防止のバランスです。

---

## 計測・按分（§FR-API-4 §4.2 〜 §4.3）

### 【処理時間 × 利用者の按分要件】 (API-B-411, 🟡)

利用者按分の指標として、Request 数のみで十分か、**処理時間 × 利用者**（Lambda 実行時間ベース）まで按分する要件があるかご教示ください。
**目的**: [§FR-API-4 §4.2](../proposal/fr/04-metering-billing.md) の計測粒度。処理時間按分は EMF カスタム次元と CloudWatch コストが増加します。

---

### 【EMF カスタム次元のカーディナリティ】 (API-B-412, 🟢)

EMF（Embedded Metric Format）でテナント別等のカスタム次元を使う場合、想定されるカーディナリティ（テナント数）をご教示ください。
CloudWatch は次元数 × 値の組合せで課金が発生するため、大量テナントの場合は集計戦略を変える必要があります。
**目的**: [§FR-API-4 §4.2 / §NFR-API-8](../proposal/nfr/08-cost.md) のコスト試算。

---

### 【Tag enforcement の手段】 (API-B-431, 🟡)

必須タグ（CostCenter / Project / Environment / Application / Exposure / Tenant / DataClassification）の付与強制を、どの手段で実現するかご見解をお願いします。
- **Config Rule + SCP**（事後検知 + 予防的禁止）
- **IaC validation hooks**（pre-deploy で検証）
- 両方
**目的**: [§FR-API-4 §4.3 / §FR-API-7 §7.2](../proposal/fr/07-guardrails.md) のタグ強制機構。完全性とアプリ開発者の自由度のバランスです。

---

### 【既存リソースへの遡及付与】 (API-B-432, 🟡)

既存リソースへの必須タグの **遡及付与スコープ** をご教示ください。
- 全既存リソース対象（一括スクリプト）
- 重要リソースのみ
- 次回リプラット時に対応
**目的**: [§FR-API-4 §4.3 / §NFR-API-9](../proposal/nfr/09-compatibility.md) の移行範囲。タグ未付与だと CUR 按分が成立しません。

---

## ヒアリング後の確定事項チェックリスト

- [ ] テナント識別子の主軸（B-401）
- [ ] HTTP API / REST API のデフォルト（B-104 と再確認）
- [ ] 既存リソース遡及付与（B-432）

これらが揃うと **§FR-API-3 / §FR-API-4** を確定できます。
