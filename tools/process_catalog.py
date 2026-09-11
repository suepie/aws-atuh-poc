#!/usr/bin/env python3
"""認証実装確認処理 — 処理分解カタログ（データ定義）

SSOT: doc/api-platform/basic-design/research/process-design-template.md
本ファイルを更新したら上記 md の処理カタログ表も同時に更新すること。

系統（処理 ID の接頭辞）:
  巡回 … 対象検索 Lambda が 1 時間毎に回す処理
  全量 … 全量確認のときだけ動く処理（起動・全件取得・アプリ単位への割り振り）
  確認 … 1 アプリを検査する処理（巡回起点／全量起点のどちらでも同じ）
  通知 … アラート検知 Lambda / CloudWatch による通知
  運用 … 人手・異常系（メタ監視・DLQ・手動更新）
  連携 … アプリ（ベンダー）側の接点
"""

GROUPS = {
    "巡回": ("巡回・対象検索", "FFD966"),
    "全量": ("全量確認", "9DC3E6"),
    "確認": ("認証実装確認（1 アプリ）", "C6E0B4"),
    "通知": ("アラート通知", "F4B183"),
    "運用": ("運用・異常系", "C9C9C9"),
    "連携": ("アプリ接点", "D9B3E6"),
}


def P(pid, sheet, name, trigger, src, dst, mode, actor, freq, summary, perm, seq, hint, d=None):
    """1 処理の定義。

    d（詳細）は設計が固まった処理にだけ与える。与えると Excel の該当欄が
    「記入済み（白セル）」で生成され、未指定の欄だけ黄色の記入待ちで残る。
    **Excel に直接書かず必ずここへ書く**（再生成で消えるため）。

    d のキー（すべて任意）:
      position   str        フロー内の位置
      pre        str/list   前提条件・事前状態
      inputs     [[項目, 型, 必須, 取得元, 説明・例], ...]
      outputs    [[項目, 型, 出力先, 説明・例], ...]
      steps      [[処理内容, 補足・参照], ...]        # 番号は自動付番
      exceptions [[ケース, 検知方法, 動作, 通知, 参照], ...]
      idem       (再実行時の振る舞い, 状態更新のタイミング)
      authnote   str/list   認証方式・補足
      logs       [[種別, 名称・項目, 内容, 備考], ...]
      perf       (想定件数 / 所要時間, 上限・制約)
      opens      [[ID, 内容, 確認先, 期限], ...]
    """
    return dict(id=pid, sheet=sheet, name=name, group=pid.split("-")[0], trigger=trigger,
                src=src, dst=dst, mode=mode, actor=actor, freq=freq, summary=summary,
                perm=perm, seq=seq, hint=hint, d=d)


PROCESSES = [
    # ---------------- 巡回・対象検索（対象検索 Lambda）
    P("巡回-01", "認証実装確認処理開始", "認証実装確認処理開始", "巡回（1 時間毎）",
      "EventBridge Scheduler（rate(1 hour)）", "対象検索 Lambda", "非同期", "EventBridge Scheduler", "1 時間毎",
      "監視対象の変更有無を確認する巡回処理を定期起動する。",
      "Scheduler 実行ロール / lambda:InvokeFunction / lambda.{region}.amazonaws.com",
      "EventBridge Scheduler -> 対象検索 Lambda : Invoke（payload なし）",
      "リトライポリシー・Scheduler 側 DLQ の設定値を明記する（WBS A6-d）"),
    P("巡回-02", "対象アカウント一覧取得", "対象アカウント一覧取得", "巡回（1 時間毎）",
      "対象検索 Lambda", "AWS Organizations", "同期", "対象検索 Lambda", "巡回ごとに 1 回",
      "巡回対象となる App アカウントの一覧を取得する。",
      "organizations:ListAccounts（委任ポリシー方式が推奨。M-Q-17-2）/ organizations.us-east-1.amazonaws.com",
      "対象検索 Lambda -> Organizations : ListAccounts\nOrganizations --> 対象検索 Lambda : アカウント一覧",
      "列挙方式（委任 / AssumeRole / 静的リスト）と対象範囲（全体 / OU）を確定する"),
    P("巡回-03", "対象アカウント接続権限取得", "対象アカウント接続権限取得", "巡回（1 時間毎）",
      "対象検索 Lambda", "STS →（各 App の）DiscoveryReadRole", "同期", "対象検索 Lambda", "アカウントごとに 1 回",
      "App アカウントの認証構成情報を読むための一時クレデンシャルを取得する。",
      "sts:AssumeRole + ExternalId / sts.{region}.amazonaws.com（リージョナル STS）",
      "対象検索 Lambda -> STS : AssumeRole(DiscoveryReadRole, ExternalId)\nSTS --> 対象検索 Lambda : 一時クレデンシャル",
      "クレデンシャルの有効期限とキャッシュ方針を明記する"),
    P("巡回-04", "認証構成情報一覧取得", "認証構成情報一覧・版数取得", "巡回（1 時間毎）",
      "対象検索 Lambda", "認証構成情報連携バケット（App アカウント）", "同期", "対象検索 Lambda", "アカウントごとに 1 回",
      "連携バケットの {appId}/ を列挙し、各ファイルの版数（VersionId）を取得する（本文は取得しない）。",
      "s3:ListBucket / s3:ListBucketVersions / s3.{region}.amazonaws.com",
      "対象検索 Lambda -> 連携バケット : List（{appId}/ プレフィックス）\n連携バケット --> 対象検索 Lambda : キー一覧 + VersionId",
      "ページング処理と、monitoring.yaml が無いプレフィックスの扱いを明記する"),
    P("巡回-05", "前回確認状態取得", "前回確認状態取得", "巡回（1 時間毎）",
      "対象検索 Lambda", "認証構成情報配置バケット（registry/）", "同期", "対象検索 Lambda", "アプリごとに 1 回",
      "前回巡回時に確認した版数（lastArtifactVersions）などの状態を台帳から読み取る。",
      "s3:GetObject（同一アカウント）/ s3.{region}.amazonaws.com",
      "対象検索 Lambda -> 配置バケット : GetObject(registry/{appId}/{env}.json)\n配置バケット --> 対象検索 Lambda : 台帳 JSON（無ければ新規扱い）",
      "台帳が存在しない場合（初回）の扱いを明記する"),
    P("巡回-06", "認証構成情報比較", "認証構成情報比較", "巡回（1 時間毎）",
      "対象検索 Lambda（内部）", "—", "内部", "対象検索 Lambda", "アプリごとに 1 回",
      "連携バケットの版数と台帳の記録値を比較し、認証実装確認の要否を判定する。",
      "—（AWS 呼び出しなし）",
      "対象検索 Lambda : VersionId ↔ lastArtifactVersions を比較\n判定結果 = 変更あり / 変更なし / 新規",
      "【重要】比較は版数（メタデータ）で行い、内容ハッシュ比較にしない（17 §17.2.1 差分判定の 3 原則）"),
    P("巡回-07", "認証構成情報取得", "認証構成情報取得", "巡回（1 時間毎）",
      "対象検索 Lambda", "認証構成情報連携バケット（App アカウント）", "同期", "対象検索 Lambda", "変更のあったアプリのみ",
      "変更が検知されたアプリの認証構成情報（monitoring.yaml / openapi.yaml / deploy-info.json）を取得する。",
      "s3:GetObject / s3:GetObjectVersion / s3.{region}.amazonaws.com",
      "対象検索 Lambda -> 連携バケット : GetObject(monitoring.yaml, openapi.yaml)\n連携バケット --> 対象検索 Lambda : ファイル本体",
      "サイズ上限・文字コード・取得失敗時の扱いを明記する"),
    P("巡回-08", "認証構成情報検証", "認証構成情報検証", "巡回（1 時間毎）",
      "対象検索 Lambda（内部）", "—", "内部", "対象検索 Lambda", "取得ごとに 1 回",
      "monitoring.yaml のスキーマ検証と、appId とプレフィックスの一致検証を行う。",
      "—（AWS 呼び出しなし）",
      "対象検索 Lambda : YAML パース -> JSON Schema 検証 -> appId 一致検証\nNG の場合は 巡回-12 構成情報不備通知へ",
      "不備の分類（取り込み拒否 / 既定値で継続）を項目ごとに定義する（17 §17.3 の表）"),
    P("巡回-09", "認証構成情報登録", "認証構成情報登録", "巡回（1 時間毎）",
      "対象検索 Lambda", "認証構成情報配置バケット（registry/）", "同期", "対象検索 Lambda", "変更のあったアプリのみ",
      "台帳へ設定値を同期し、確認状態を更新する。中央管理項目（通知先・監視有効フラグ）は上書きしない。",
      "s3:PutObject（ETag 条件付き PUT, If-Match）/ s3.{region}.amazonaws.com",
      "対象検索 Lambda -> 配置バケット : PutObject（If-Match: 読取時 ETag）\n412 の場合は再読取してリトライ",
      "alertRouting / enabled を上書きしないマージ規則と、412 競合時のリトライ回数を明記する"),
    P("巡回-10", "API仕様登録", "API 仕様登録", "巡回（1 時間毎）",
      "対象検索 Lambda", "認証構成情報配置バケット（openapi/）", "同期", "対象検索 Lambda", "変更のあったアプリのみ",
      "取得した API 仕様（openapi.yaml）を中央の仕様保管領域へ複写する。",
      "s3:PutObject / s3.{region}.amazonaws.com",
      "対象検索 Lambda -> 配置バケット : PutObject(openapi/{accountId}/{appId}/openapi.yaml)",
      "キー導出規則と上書き方針（Versioning による履歴保全）を明記する"),
    P("巡回-11", "認証実装確認依頼", "認証実装確認依頼", "巡回（1 時間毎）",
      "対象検索 Lambda", "認証実装チェック Lambda", "非同期", "対象検索 Lambda", "変更のあったアプリごと",
      "変更が確定したアプリを対象に認証実装の確認を依頼する（自動差分検査＝モード1）。",
      "lambda:InvokeFunction（InvocationType=Event）/ lambda.{region}.amazonaws.com",
      "対象検索 Lambda -> 認証実装チェック Lambda : Invoke(Event, {mode:'delta', appId, env})\n※ 依頼成功後に 巡回-09 の版数を確定更新",
      "非同期リトライ（2 回）と DLQ の設定、依頼失敗時に台帳を更新しないこと（at-least-once）を明記する"),
    P("巡回-12", "構成情報不備通知", "構成情報不備通知", "巡回（1 時間毎）",
      "対象検索 Lambda", "SNS（P2 Platform）", "同期", "対象検索 Lambda", "不備検出時",
      "認証構成情報の不備（appId 不一致・必須項目欠落・認証方式の値が不正など）を通知する。",
      "sns:Publish / sns.{region}.amazonaws.com",
      "対象検索 Lambda -> SNS(P2) : Publish（不備種別・appId・該当項目）",
      "不備種別ごとの文面と、毎巡回で重複通知しない抑制方式を定義する"),
    P("巡回-13", "監視対象消滅検知", "監視対象消滅・鮮度低下検知", "巡回（1 時間毎）",
      "対象検索 Lambda", "配置バケット（registry/）+ SNS（P2）", "同期", "対象検索 Lambda", "巡回ごとに 1 回",
      "認証構成情報の消滅（アプリ廃止の可能性）と、長期間更新されていない状態（鮮度低下）を検知する。",
      "s3:PutObject（enabled=false）/ sns:Publish",
      "対象検索 Lambda : 台帳あり かつ 構成情報なし -> enabled=false + 棚卸しアラート\n対象検索 Lambda : 最終更新が閾値超 -> 鮮度低下アラート",
      "鮮度低下の閾値（仮 90 日、M-Q-17-3）と、一時的な取得失敗との区別を定義する"),
    P("巡回-14", "巡回結果メトリクス送信", "巡回結果メトリクス送信", "巡回（1 時間毎）",
      "対象検索 Lambda", "CloudWatch", "同期", "対象検索 Lambda", "巡回ごとに 1 回",
      "巡回の成功・失敗アカウント数などを、監視機構自身の稼働監視用メトリクスとして送信する。",
      "cloudwatch:PutMetricData / monitoring.{region}.amazonaws.com",
      "対象検索 Lambda -> CloudWatch : PutMetricData(DiscoveryLastSuccess, DiscoveryAccountErrors)",
      "メトリクス名・ディメンション・欠損時の扱い（MM-1 は 2h 欠損で発報）を明記する"),

    # ---------------- 全量確認
    P("全量-01", "全量確認処理開始（定期）", "全量確認処理開始（定期）", "全量（日次）",
      "EventBridge Scheduler（日次）", "認証実装チェック Lambda", "非同期", "EventBridge Scheduler", "日次",
      "認証構成情報の変化に関係なく全アプリを確認するため、全量確認を定期起動する。",
      "Scheduler 実行ロール / lambda:InvokeFunction",
      "EventBridge Scheduler -> 認証実装チェック Lambda : Invoke(Event, {mode:'full'})",
      "実行時刻帯（M-Q-18-3）と、巡回（巡回-01）と時間帯が重ならない配慮を明記する"),
    P("全量-02", "全量確認処理開始（手動）", "全量確認処理開始（手動）", "全量（手動・随時）",
      "運用者（CLI / コンソール）", "認証実装チェック Lambda", "非同期", "運用者", "随時（監査前・障害後など）",
      "運用者の判断で全量確認を実行する。実装は定期起動と同一で、起動元が人である点だけが異なる。",
      "lambda:InvokeFunction（実行者の IAM）",
      "運用者 -> 認証実装チェック Lambda : Invoke(Event, {mode:'full'})\n※ 特定アプリのみ: {mode:'full', appId, env}",
      "実行権限を持つ者の範囲（共通基盤チームのみか、アプリチームも可か。M-Q-18-3）を確定する"),
    P("全量-03", "監視対象一覧取得", "監視対象一覧取得", "全量（日次・手動）",
      "認証実装チェック Lambda", "認証構成情報配置バケット（registry/）", "同期", "認証実装チェック Lambda", "全量確認ごとに 1 回",
      "台帳を全件読み出し、監視有効な対象アプリの一覧を得る。",
      "s3:ListBucket / s3:GetObject",
      "認証実装チェック Lambda -> 配置バケット : List(registry/) -> GetObject（各件）\n配置バケット --> 認証実装チェック Lambda : 台帳 JSON 群",
      "enabled=false のレコードを除外すること、List のページングを明記する"),
    P("全量-04", "アプリ単位確認依頼", "アプリ単位確認依頼（fan-out）", "全量（日次・手動）",
      "認証実装チェック Lambda", "認証実装チェック Lambda（自身）", "非同期", "認証実装チェック Lambda", "対象アプリ数分",
      "全量確認を「1 実行 = 1 アプリ」に分割し、Lambda の実行時間上限に構造的に当たらないようにする。",
      "lambda:InvokeFunction（自身）/ lambda.{region}.amazonaws.com",
      "認証実装チェック Lambda(mode=full) -> 認証実装チェック Lambda(1 アプリ分) : アプリ数分 Invoke(Event)",
      "同時実行数の上限・スロットリング時の扱いを明記する"),

    # ---------------- 認証実装確認（1 アプリ・巡回/全量 共通）
    P("確認-01", "認証構成情報参照", "認証構成情報参照", "共通（巡回・全量とも）",
      "認証実装チェック Lambda", "認証構成情報配置バケット（registry/）", "同期", "認証実装チェック Lambda", "アプリごとに 1 回",
      "確認対象アプリの設定値（検査先 URL・認証方式・トークン設定）を台帳から取得する。",
      "s3:GetObject",
      "認証実装チェック Lambda -> 配置バケット : GetObject(registry/{appId}/{env}.json)\n配置バケット --> 認証実装チェック Lambda : 台帳 JSON",
      "台帳が取得できない場合（削除・権限不足）の扱いを明記する"),
    P("確認-02", "API仕様取得", "API 仕様取得", "共通（巡回・全量とも）",
      "認証実装チェック Lambda", "認証構成情報配置バケット（openapi/）", "同期", "認証実装チェック Lambda", "アプリごとに 1 回",
      "確認対象の endpoint 一覧と公開明示（MON-1）を取得する。",
      "s3:GetObject",
      "認証実装チェック Lambda -> 配置バケット : GetObject(openApiS3Key)\n配置バケット --> 認証実装チェック Lambda : API 仕様",
      "API 仕様が存在しない場合（モノリスの endpoint 列挙方式）の分岐を明記する"),
    P("確認-03", "正常系確認用トークン取得", "正常系確認用トークン取得", "共通（巡回・全量とも）",
      "認証実装チェック Lambda", "Secrets Manager → 認証基盤 /token", "同期", "認証実装チェック Lambda", "確認ごとに 1 回",
      "正常系アクセス確認で使う短命トークンを取得する。",
      "secretsmanager:GetSecretValue / 認証基盤の公開 /token（インターネット経由・OAuth client_credentials）",
      "認証実装チェック Lambda -> Secrets Manager : GetSecretValue\n認証実装チェック Lambda -> 認証基盤 /token : client_credentials\n認証基盤 --> 認証実装チェック Lambda : access_token（短命）",
      "トークンのキャッシュ有無・失効時の再取得・ログへのマスク（トークンを出力しない）を明記する"),
    P("確認-04", "未認証アクセス確認", "未認証アクセス確認", "共通（巡回・全量とも）",
      "認証実装チェック Lambda", "CloudFront → WAF → API GW / ALB", "同期", "認証実装チェック Lambda", "endpoint ごとに 1 回",
      "認証情報なしでリクエストし、正しく拒否されるか（401/403、Cookie 系は 302）を確認する。2xx なら認証実装漏れ。",
      "認証不要（Public 経路）/ HTTPS 443 / X-Auth-Probe ヘッダ付与（WAF 誤検知回避）",
      "認証実装チェック Lambda -> CloudFront : リクエスト（認証ヘッダなし, X-Auth-Probe）\nCloudFront -> API GW / ALB : Origin Protection 付与\nAPI GW / ALB --> 認証実装チェック Lambda : ステータスコード（本文は読み捨て）",
      "公開明示（x-synthetics-skip-auth-check）付き endpoint の扱い、タイムアウト値、endpoint 単位の継続（1 件失敗で打ち切らない）を明記する",
      d=dict(
        position="確認-02 で得た endpoint リストのループ内。本処理（未認証）→ 確認-05（正常系）→ 確認-06（判定）の順で 1 endpoint を処理する（11 §11.1 ④）。"
                 "本処理は「認証が効いているか」を直接確かめる本機構の中核で、2xx が返れば認証実装漏れとして P1 になる。",
        pre=[
          "確認-01 で台帳から baseUrl / authPattern を取得済み",
          "確認-02 で endpoint 記述子（method / path / rawPath / skipAuthCheck）を取得済み。MON-1 の公開印は解釈済み",
          "識別ヘッダ X-Auth-Probe の値を Secrets Manager から取得済み",
          "対象アプリの WAF に識別ヘッダの許可ルールが入っていること（M-Q-11-5）。未設定だと WAF ブロックによる WARN が多発する（11 §11.2.4）",
        ],
        inputs=[
          ["baseUrl", "string", "✅", "台帳 registry/{appId}/{env}.json（確認-01）",
           "検査先の CloudFront URL。例 https://expense.example.com（API GW の直 URL ではない。12 章）"],
          ["authPattern", "enum（6 値）", "✅", "同上",
           "期待ステータスの分岐に使う。api-gw-jwt / alb-code-jwt / alb-cookie-monolith / bff-cookie-session / api-gw-iam / lambda-url-iam"],
          ["ep.method", "string", "✅", "確認-02（extractEndpoints）", "HTTP メソッド。例 GET"],
          ["ep.path", "string", "✅", "確認-02",
           "path parameter を dummy 値（x-canary-path-params）で解決済みのパス。例 /api/users/1"],
          ["ep.rawPath", "string", "✅", "確認-02",
           "テンプレートのままのパス。ログ・アラートの識別子に使う。例 /api/users/{id}"],
          ["ep.skipAuthCheck", "boolean", "—", "確認-02（x-synthetics-skip-auth-check）",
           "true = public と明示された endpoint。本処理をスキップする。未記載は false（= 認証必須、MON-1 の default-deny）"],
          ["X-Auth-Probe 識別値", "string（secret）", "✅", "Secrets Manager（共通基盤アカウント）",
           "WAF 許可ルールの照合キー。ログ・アラート本文に出さない（OBS-3）"],
        ],
        outputs=[
          ["negStatus", "number / null", "確認-06（メモリ内で受け渡し）",
           "観測した HTTP ステータス。公開印によるスキップ時は null（＝ 判定対象外で OK）"],
          ["wafBlocked", "boolean", "確認-06（同上）",
           "WAF による遮断と判別できた場合に true。403 を「認証が効いている」と誤認させないための区別（11 §11.2.4）"],
          ["観測不能フラグ", "boolean", "確認-06（同上）", "接続不能・タイムアウト等でステータスを得られなかった場合に true"],
          ["probe 実行ログ", "JSON 1 行", "CloudWatch Logs",
           "appId / env / method / rawPath / negStatus / 所要 ms / 相関 ID。§9 参照"],
        ],
        steps=[
          ["ep.skipAuthCheck が true なら本処理をスキップし negStatus = null を返す",
           "MON-1（13 §13.3.0）。未記載は認証必須として probe する（default-deny）。公開印の妥当性レビューは中央の月次棚卸しの役割"],
          ["リクエストを組み立てる。Authorization・Cookie を一切付けず、X-Auth-Probe 識別ヘッダのみを付与する",
           "「認証情報を付けない」ことが検査の本体。識別ヘッダは WAF 誤爆回避のため（11 §11.2.4 主対策）"],
          ["宛先は baseUrl（CloudFront）。Origin Protection ヘッダは付けない",
           "実ユーザーと同じ経路（CloudFront → WAF → Origin Protection → API GW / ALB）を通すため。X-Origin-Verify は CloudFront が付与する（10 §10.1.6）"],
          ["リダイレクトを自動追従しない設定で送信する",
           "alb-cookie-monolith / bff-cookie-session は 302 そのものが期待値のため、追従すると観測できない（11 §11.3）"],
          ["応答ステータスを回収する。応答ボディは読み捨てる（drain）",
           "メモリ確保を避け、機微データを保持しないため。probe lib lib/probe.js の実装方針に準拠"],
          ["応答が WAF による遮断と判別できる場合（CloudFront / WAF 由来のエラー応答）は wafBlocked = true を付けて返す",
           "認証レイヤー由来の 403 と区別する。区別できないと偽陰性（認証漏れを OK と判定）が起きる（11 §11.2.4）"],
          ["接続不能・タイムアウト等の例外は throw せず、観測不能として記録し次の endpoint へ進む",
           "1 endpoint の失敗で残りの endpoint を打ち切らない（18 §18.5.2）"],
          ["negStatus / wafBlocked / 観測不能フラグを確認-06 へ渡す",
           "期待値との突き合わせ（authPattern 別の 401/403 or 302）と 4×4 判定は確認-06 の責務。本処理は観測に徹する"],
        ],
        exceptions=[
          ["公開印（x-synthetics-skip-auth-check: true）付き endpoint", "確認-02 の記述子",
           "probe せず negStatus = null", "通知なし（OK 判定）", "13 §13.3.0 / README §2.3"],
          ["WAF が probe を遮断（403）", "応答の形が CloudFront / WAF 由来",
           "wafBlocked = true として返す", "確認-06 で WARN「境界でブロック」→ P2 Platform", "11 §11.2.4"],
          ["接続不能 / DNS 解決失敗 / TLS 証明書エラー", "例外捕捉",
           "観測不能として記録し次の endpoint へ継続", "確認-06 で WARN（構成）→ P2 Platform", "18 §18.5.2"],
          ["タイムアウト（接続 3 秒 / 応答 10 秒 超過）", "同上", "同上", "同上", "§10 上限・制約"],
          ["5xx が返る", "ステータス", "そのまま観測値として返す（本処理では異常扱いしない）",
           "確認-06 の判定に委ねる", "11 §11.2.2"],
          ["2xx が返る", "ステータス", "そのまま観測値として返す",
           "確認-06 で CRITICAL（認証実装漏れ）→ P1 Security 即時", "11 §11.2.2 / README §2.5"],
        ],
        idem=(
          "参照系の読み取り検査であり状態を持たないため、何度実行しても結果は変わらず安全（冪等）。"
          "対象検索 → 検査の invoke は at-least-once（18 §18.5.2）で重複起動しうるが、重複しても無害。"
          "※ 更新系メソッドを probe する場合の副作用は M-Q-11-6（§11 未決）を参照",
          "本処理は台帳・S3・メトリクスのいずれも更新しない。観測値はメモリ上で確認-06 へ渡すのみで、"
          "メトリクス送信は確認-07、通知は確認-08 以降に集約する",
        ),
        authnote=[
          "認証情報は付与しない（付与しないことが検査の本体）。Authorization / Cookie とも送らない",
          "X-Auth-Probe の識別値は Secrets Manager 管理。ログ・アラート本文・例外メッセージに出さない（OBS-3 機微情報のマスク）",
          "Origin Protection（X-Origin-Verify）は CloudFront が付与するため probe 側では付与しない",
          "AWS API の呼び出しは伴わない（Secrets の取得は確認-03 / 起動時に済ませる）。本処理の通信はインターネット向け HTTPS 443 のみ",
        ],
        logs=[
          ["ログ", "probe 実行ログ",
           "appId / env / authPattern / method / rawPath / negStatus / wafBlocked / 所要 ms / 相関 ID（実行 ID）",
           "1 endpoint 1 行。識別ヘッダ値・トークンはマスク（06 章 OBS-2 相関 ID / OBS-3 マスク）"],
          ["ログ", "スキップログ", "公開印により probe しなかった endpoint（appId / rawPath）",
           "公開印の濫用レビュー（月次棚卸し）の入力になる"],
          ["メトリクス", "（本処理では送信しない）", "EndpointsProbed ほかの集計送信は確認-07 に集約",
           "endpoint ごとに PutMetricData すると呼び出し回数と費用が endpoint 数に比例するため"],
        ],
        perf=(
          "1 アプリ 30 endpoint 想定（費用見積 P-3）で Negative 30 回。1 回あたり 0.1〜1 秒、"
          "1 アプリ分で 30 秒以内が目安。閾値の本決めは W3-5（性能実測）",
          "Lambda 15 分（1 実行 = 1 アプリ、18 §18.5.3）/ タイムアウト 接続 3 秒・応答 10 秒（暫定、W3-5 で確定）/ "
          "endpoint は直列実行を前提（並列化は WAF レートルール誤爆と表裏。並列化する場合は M-Q-11-5 の許可ルールと併せて判断）",
        ),
        opens=[
          ["M-Q-11-5", "probe 識別ヘッダ（X-Auth-Probe）の WAF 許可ルール。未設定だと WAF ブロックによる WARN が多発し、偽陰性のリスクも残る",
           "境界管理チーム（ネットワーク監査アカウント）", "調整中"],
          ["M-Q-11-6", "【新規】更新系メソッド（POST / PUT / PATCH / DELETE）に対する未認証確認の可否。"
           "現行 11 §11.5 は Positive のみ本番 POST をスキップと定めており、Negative は全メソッドが対象。"
           "認証が正しく効いていれば 401/403 で副作用はないが、"
           "まさに検知したい『認証漏れ』のときだけ本番データを更新してしまう。"
           "案: ① 本番の Negative も GET 限定（更新系の認証漏れを検知できない穴が残る）"
           "② 更新系は空ボディ・不正 Content-Type で送り、401/403 以外はすべて認証漏れ疑いとする（副作用を最小化しつつ検知は維持。推奨）"
           "③ 更新系は stg のみで検査（本番との構成差の分だけ保証が落ちる）",
           "共通基盤チーム + アプリ（顧客合意）", "未定"],
          ["—", "タイムアウト値（接続 3 秒 / 応答 10 秒）と直列 / 並列の本決め", "W3-5 性能実測で確定", "Phase 3"],
        ],
      )),
    P("確認-05", "正常系アクセス確認", "正常系アクセス確認", "共通（巡回・全量とも）",
      "認証実装チェック Lambda", "CloudFront → WAF → API GW / ALB", "同期", "認証実装チェック Lambda", "endpoint ごとに 1 回",
      "有効なトークン付きでリクエストし、200 が返ることで API 稼働と確認処理自体の健全性を確かめる。",
      "Bearer（確認-03 のトークン）/ HTTPS 443 / X-Auth-Probe ヘッダ付与",
      "認証実装チェック Lambda -> CloudFront : GET（Authorization: Bearer …, X-Auth-Probe）\nAPI GW --> 認証実装チェック Lambda : ステータスコード",
      "参照系のみ実行すること（更新系を叩かない）、対象 endpoint の選定規則を明記する"),
    P("確認-06", "確認結果判定", "確認結果判定（4×4）", "共通（巡回・全量とも）",
      "認証実装チェック Lambda（内部）", "—", "内部", "認証実装チェック Lambda", "endpoint ごとに 1 回",
      "未認証アクセス確認と正常系アクセス確認の結果の組み合わせから、重要度（CRITICAL / WARN / INFO / OK）を判定する。",
      "—（AWS 呼び出しなし）",
      "認証実装チェック Lambda : (未認証結果, 正常系結果) -> 4×4 真偽値表 -> 重要度決定\nWAF 起因の 403 は WARN（構成）に分類",
      "4×4 の全組み合わせと重要度の対応表を貼る（code-samples/README §2 が正）"),
    P("確認-07", "確認結果メトリクス送信", "確認結果メトリクス送信", "共通（巡回・全量とも）",
      "認証実装チェック Lambda", "CloudWatch", "同期", "認証実装チェック Lambda", "確認ごとに 1 回",
      "確認結果をメトリクス化し、保険系アラーム（AuthCheckCritical > 0）の入力とする。",
      "cloudwatch:PutMetricData / monitoring.{region}.amazonaws.com",
      "認証実装チェック Lambda -> CloudWatch : PutMetricData(AuthCheckCritical ほか, ディメンション=appId/env)",
      "ディメンション設計（アプリ数比例でメトリクス課金が増える点に注意）を明記する"),
    P("確認-08", "検知結果通知依頼", "検知結果通知依頼", "共通（巡回・全量とも）",
      "認証実装チェック Lambda", "アラート検知 Lambda", "非同期", "認証実装チェック Lambda", "重要度≠OK 時",
      "判定済みの検知結果を、通知の振り分けを行うアラート検知 Lambda へ引き渡す。",
      "lambda:InvokeFunction（InvocationType=Event）",
      "認証実装チェック Lambda -> アラート検知 Lambda : Invoke(Event, 4×4 判定済みイベント)",
      "イベント形式（README §2.6）と、配列でのバッチ送付の可否を明記する"),

    # ---------------- アラート通知
    P("通知-01", "通知先解決", "通知先解決", "共通（検知時）",
      "アラート検知 Lambda", "認証構成情報配置バケット（registry/）", "同期", "アラート検知 Lambda", "イベントごとに 1 回",
      "台帳の通知先設定から送信先を解決する。未設定時は全社デフォルトを使う。",
      "s3:GetObject",
      "アラート検知 Lambda -> 配置バケット : GetObject（alertRouting 参照）\n未設定 -> 全社デフォルト ARN",
      "2 段解決（アプリ個別 → 全社デフォルト）の順序と、未解決時に throw する仕様を明記する"),
    P("通知-02", "重要度別通知送信", "重要度別通知送信", "共通（検知時）",
      "アラート検知 Lambda", "SNS（P1 Security / P2 Platform / P3 App）", "同期", "アラート検知 Lambda", "イベントごとに 1 回",
      "重要度に応じた宛先へ通知を送信する。",
      "sns:Publish / sns.{region}.amazonaws.com",
      "アラート検知 Lambda -> SNS(P1|P2|P3) : Publish（件名・本文・appId・endpoint・判定根拠）",
      "通知本文のテンプレートと、1 件でも失敗したら throw（DLQ 発火）する仕様を明記する"),
    P("通知-03", "メトリクス閾値通知", "メトリクス閾値通知（保険系）", "共通（閾値超過時）",
      "CloudWatch Alarm", "SNS", "非同期", "CloudWatch", "閾値超過時",
      "アラート検知 Lambda の経路とは独立に、メトリクス閾値からも発報する（発報 2 系統の保険側）。",
      "CloudWatch Alarm → SNS（アラームアクション）",
      "CloudWatch Alarm(AuthCheckCritical > 0) -> SNS : 通知",
      "即時系（アラート検知 Lambda）と保険系の重複通知の扱いを明記する"),

    # ---------------- 運用・異常系
    P("運用-01", "監視機構稼働監視通知", "監視機構稼働監視通知（MM-1〜5）", "随時（異常時）",
      "CloudWatch Alarm", "SNS（P2 Platform）", "非同期", "CloudWatch", "閾値超過時",
      "監視機構そのものの停止・失敗を検知して発報する（監視の空白＝検知の空白を防ぐ）。",
      "CloudWatch Alarm → SNS",
      "Alarm(DiscoveryLastSuccess 2h 欠損 / Lambda Errors / DLQ 滞留) -> SNS(P2)",
      "MM-1〜5 の各アラーム定義（対象メトリクス・閾値・評価期間）を一覧化する"),
    P("運用-02", "処理失敗退避・再処理", "処理失敗退避・再処理（DLQ）", "随時（異常時）",
      "各 Lambda（非同期実行の失敗）", "SQS DLQ → 運用者", "非同期", "Lambda / 運用者", "失敗時",
      "非同期呼び出しがリトライ後も失敗した場合に退避し、後から再処理・原因調査できるようにする。",
      "Lambda 非同期呼び出しの DLQ 設定 / sqs:ReceiveMessage・DeleteMessage（運用者）",
      "Lambda(失敗) -> 自動リトライ(2 回) -> SQS DLQ\n運用者 -> DLQ : 内容確認 -> 再実行",
      "DLQ の保持期間・再処理手順（Runbook 化）・滞留アラーム（MM-4/5）を明記する"),
    P("運用-03", "監視設定手動更新", "監視設定手動更新", "随時（運用操作）",
      "運用者", "認証構成情報配置バケット（registry/）", "同期", "運用者", "随時",
      "監視の有効・無効の切替や通知先の設定など、中央管理項目を運用者が更新する。",
      "s3:GetObject / s3:PutObject（ETag 条件付き）",
      "運用者 -> 配置バケット : GetObject -> 編集 -> PutObject（If-Match）\n巡回と競合した場合は 412 -> 再取得",
      "巡回（巡回-09）との競合手順、変更履歴の追跡（Versioning）、承認フローの要否を明記する"),

    # ---------------- アプリ接点
    P("連携-01", "認証構成情報配置", "認証構成情報配置（アプリ側）", "随時（デプロイのたび）",
      "ベンダー CI（デプロイパイプライン最終段）", "認証構成情報連携バケット（App アカウント）", "同期", "ベンダー CI", "デプロイのたび",
      "デプロイ成功後に認証構成情報を配置する。本監視の入口であり、アプリ（ベンダー）側の責務。",
      "ArtifactUploadRole-{appId} を Assume / s3:PutObject（{appId}/* 限定）/ s3.{region}.amazonaws.com",
      "ベンダー CI -> STS : AssumeRole(ArtifactUploadRole-{appId})\nベンダー CI -> 連携バケット : PutObject(monitoring.yaml, openapi.yaml, deploy-info.json)",
      "デプロイ成功後に実行すること（順序逆転の禁止）、配置漏れは原則アプリ責任（M-Q-17-7）である旨を明記する"),
]
