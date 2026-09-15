#!/usr/bin/env python3
"""認証実装確認処理 — 処理分解カタログ（データ定義）

SSOT: doc/api-platform/basic-design/research/process-design-template.md
本ファイルを更新したら上記 md の処理カタログ表も同時に更新すること。

系統（処理 ID の接頭辞）— 実行主体の Lambda 名に揃える:
  対象検索       … 対象検索 Lambda の処理（1 時間毎の巡回）
  全量           … 認証実装チェック Lambda の処理のうち**全量確認固有**（起動・全件取得・アプリ単位への割り振り）
  認証実装チェック … 認証実装チェック Lambda の処理のうち**1 アプリの確認**（対象検索起点／全量起点で共通）
  通知           … アラート検知 Lambda / CloudWatch による通知
  運用           … 人手・異常系（メタ監視・DLQ・手動更新）
  連携           … アプリ（ベンダー）側の接点
"""

GROUPS = {
    "対象検索": ("1 時間毎の巡回", "FFD966"),
    "全量": ("全量確認 固有", "9DC3E6"),
    "認証実装チェック": ("1 アプリの確認・共通", "C6E0B4"),
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
    # ---------------- 対象検索（対象検索 Lambda・1 時間毎の巡回）
    P("対象検索-01", "認証実装確認処理開始", "認証実装確認処理開始", "対象検索（1 時間毎）",
      "EventBridge Scheduler（rate(1 hour)）", "対象検索 Lambda", "非同期", "EventBridge Scheduler", "1 時間毎",
      "監視対象の変更有無を確認する巡回処理を定期起動する。",
      "Scheduler 実行ロール / lambda:InvokeFunction / lambda.{region}.amazonaws.com",
      "EventBridge Scheduler -> 対象検索 Lambda : Invoke（payload なし）\n【シーケンス図の所在】17 §17.2.1 巡回シーケンス図（対象検索-01〜14 を通した図）/ 10 §10.1.7 F1",
      "リトライポリシー・Scheduler 側 DLQ の設定値を明記する（WBS A6-d）",
      d=dict(
        position="巡回の起点。本処理で対象検索 Lambda が 1 回起動し、その 1 実行の中で 対象検索-02〜14 が順に動く（17 §17.2.1）。",
        pre=[
          "EventBridge Scheduler・Scheduler 実行ロール・対象検索 Lambda が作成済み（WBS A6-d / A6-i / A7）",
          "Scheduler 用 DLQ（**SQS 標準キュー**。FIFO は Scheduler の DLQ に使用不可）が作成済み（WBS A5）",
          "Scheduler 実行ロールに lambda:InvokeFunction と sqs:SendMessage（DLQ 宛）が付与済み",
        ],
        inputs=[
          ["スケジュール式", "string", "○", "Scheduler 定義（IaC）",
           "rate(1 hour)。全スケジュール種別で起動精度は 60 秒（1:00 指定なら 1:00:00〜1:00:59 に起動）"],
          ["FlexibleTimeWindow", "OFF / FLEXIBLE", "○", "同上",
           "**Mode は指定必須**。本処理は OFF（毎正時付近に走らせ、全量確認（日次）と時間帯を分けるため）"],
          ["RetryPolicy", "object", "—", "同上",
           "MaximumRetryAttempts（0〜185）/ MaximumEventAgeInSeconds（60〜86400）。**AWS 公式に既定値の記載がないため明示設定する**（M-Q-PD-1）"],
          ["DeadLetterConfig.Arn", "string", "○", "同上", "Scheduler 用 DLQ（SQS 標準キュー）の ARN"],
          ["target payload", "—", "—", "—",
           "**渡さない**。「起動されたこと」自体がトリガで、対象の決定は 対象検索-02 以降が台帳と連携バケットから行う"],
        ],
        outputs=[
          ["対象検索 Lambda の起動", "非同期 Invoke", "対象検索 Lambda", "InvocationType は Scheduler が制御。Lambda 側は event を参照しない"],
          ["AWS/Scheduler メトリクス", "CloudWatch", "共通基盤アカウント",
           "InvocationAttemptCount / TargetErrorCount / TargetErrorThrottledCount / InvocationDroppedCount /（DLQ 設定時）InvocationsSentToDeadLetterCount"],
          ["DLQ メッセージ", "SQS", "Scheduler 用 DLQ",
           "リトライ枯渇時のみ。属性に ERROR_CODE / ERROR_MESSAGE / EXECUTION_ID / SCHEDULE_ARN / RETRY_ATTEMPTS / EXHAUSTED_RETRY_CONDITION が付く"],
        ],
        steps=[
          ["Scheduler が rate(1 hour) で起動する", "起動精度は 60 秒。FlexibleTimeWindow=OFF のため分散はしない"],
          ["Scheduler 実行ロールを引き受け、対象検索 Lambda を lambda:InvokeFunction で起動する",
           "Lambda 側リソースベースポリシーではなく、Scheduler 実行ロール方式（AWS 公式手順）"],
          ["起動に失敗した場合は RetryPolicy に従い**指数バックオフ**で再試行する",
           "MaximumRetryAttempts と MaximumEventAgeInSeconds の**どちらか早い方**で打ち切り"],
          ["リトライを使い切ったら DLQ へ配信する",
           "恒久エラー（non-retryable）でも DLQ へ入るが、その場合 EXHAUSTED_RETRY_CONDITION 属性は付かない"],
          ["対象検索 Lambda は event を参照せず、巡回処理（対象検索-02 以降）を開始する",
           "payload 非依存にすることで、手動再実行（空 payload の invoke）でも同じ経路で動く"],
        ],
        exceptions=[
          ["対象検索 Lambda のスロットリング", "AWS/Scheduler TargetErrorThrottledCount",
           "RetryPolicy に従い再試行", "リトライ成功なら通知なし", "§10 上限・制約"],
          ["リトライ枯渇で起動断念", "InvocationDroppedCount / InvocationsSentToDeadLetterCount",
           "DLQ へ退避（運用-02 で再処理）", "MM-2 → P2 Platform", "18 §18.5.1"],
          ["Scheduler 自体の障害", "DLQ メッセージの ERROR_CODE = AWS.Scheduler.InternalServerError",
           "同上", "MM-2 → P2 Platform", "—"],
          ["起動が丸ごと発生しない（スケジュール無効化・削除等）", "DiscoveryLastSuccess の 2 時間欠損（MM-1）",
           "—（検知のみ）", "MM-1 → P2 Platform", "18 §18.5.1 / M-Q-PD-2"],
          ["前回の巡回が 1 時間以内に終わらず多重起動", "Lambda の同時実行",
           "台帳の条件付き書き込み（If-Match）で後勝ちを防ぐ。予約同時実行 1 で多重起動自体を抑止することを推奨",
           "412 多発時は MM-3 経由で顕在化", "対象検索-09 / M-Q-PD-3"],
        ],
        idem=(
          "二重起動されても安全。台帳の更新はすべて If-Match 付きの条件付き書き込みで行い、"
          "競合した側は 412 を受けて再読込するため、上書き事故は起きない（対象検索-09）。"
          "検査の重複起動も probe が読み取り専用のため無害（18 §18.5.2 at-least-once）。",
          "本処理自体は状態を持たない。巡回状態（lastArtifactVersions）の更新は 対象検索-11 の"
          "検査依頼が成功した後に行う。",
        ),
        authnote=[
          "Scheduler 実行ロールの信頼ポリシーは Principal = scheduler.amazonaws.com に加え、"
          "**aws:SourceAccount と aws:SourceArn**（confused deputy 対策）を条件に付ける",
          "【注意】aws:SourceArn は**スケジュールグループ単位**で指定する（AWS 公式: 個別スケジュールや名前プレフィックスにスコープしてはならない）。"
          "ワイルドカードを使う場合は StringEquals でなく ArnLike を使う",
          "権限ポリシーは lambda:InvokeFunction（対象の関数 ARN に限定）+ sqs:SendMessage（DLQ に限定）",
        ],
        logs=[
          ["アプリログ", "巡回開始", "実行 ID（Lambda RequestId）・起動時刻・スケジュール ARN", "以降の全処理で相関 ID として引き回す（06 章 OBS-1）"],
          ["メトリクス", "AWS/Scheduler（標準）", "InvocationAttemptCount ほか §出力参照", "ディメンション ScheduleGroup。名前空間は AWS/Scheduler"],
        ],
        perf=(
          "1 時間に 1 回 = 約 730 回/月。Scheduler の無料枠（1,400 万起動/月）内で費用は実質ゼロ（RC-4）",
          "起動精度 60 秒 / 単一スケジュールへの操作は 10 TPS（調整不可）/ Input ペイロード上限 256KB（本処理では未使用）/ "
          "東京リージョンの起動スロットル 1,000 TPS",
        ),
        opens=[
          ["M-Q-PD-1", "RetryPolicy（MaximumRetryAttempts / MaximumEventAgeInSeconds）の設定値。"
           "**AWS 公式は 185 回・24 時間を「最大値」としか記載しておらず既定値が不明**のため、明示設定する。"
           "巡回は 1 時間ごとに再実行されるので、長時間リトライより早く諦めて DLQ + MM-2 で気づく方が望ましい（案: 2 回 / 600 秒）",
           "設計担当", ""],
          ["M-Q-PD-2", "【解決・2026-09-14】MM-1（巡回停止検知）の閾値は**緩和する**。"
           "AWS 公式がメトリクスの欠落を明記しているため、2 時間欠損での即発報は誤検知を招く。"
           "**検知が遅れること自体は許容**（本番と開発が同一構成であれば、本番リリース前に開発環境側で拾えるため）。"
           "残るのは実装値: 評価期間 6 時間 / TreatMissingData=breaching を初期値とし、運用実績で調整（18 §18.5.1 / WBS B3-i）",
           "設計担当", ""],
          ["M-Q-PD-3", "対象検索 Lambda に予約同時実行 1 を設定するか（多重起動の抑止）。"
           "設定すると多重起動は防げるが、スロットルされた起動が Scheduler 側のリトライ・DLQ に回る点に注意", "設計担当", ""],
        ],
      )),
    P("対象検索-02", "対象アカウント一覧取得", "対象アカウント一覧取得", "対象検索（1 時間毎）",
      "対象検索 Lambda", "AWS Organizations", "同期", "対象検索 Lambda", "巡回ごとに 1 回",
      "巡回対象となる App アカウントの一覧を取得する。",
      "organizations:ListAccounts（委任ポリシー方式が推奨。M-Q-17-2）/ organizations.us-east-1.amazonaws.com",
      "対象検索 Lambda -> Organizations : ListAccounts\nOrganizations --> 対象検索 Lambda : アカウント一覧\n【シーケンス図の所在】17 §17.2.1 巡回シーケンス図（対象検索-01〜14 を通した図）/ 10 §10.1.7 F1",
      "列挙方式（委任 / AssumeRole / 静的リスト）と対象範囲（全体 / OU）を確定する",
      d=dict(
        position="対象検索-01 の直後。巡回 1 回につき 1 度だけ実行し、以降の 対象検索-03〜13 をアカウント単位でループする。",
        pre=[
          "列挙方式が確定していること（**M-Q-17-2**。案 c = Organizations のリソースベース委任ポリシーが推奨）",
          "【注意】ListAccounts は**管理アカウントか委任管理者からしか呼べない**。共通基盤アカウントから直接呼ぶには、"
          "管理アカウントで PutResourcePolicy による委任が必要（organizations:ListAccounts は公式に委任可能アクションとして列挙されている）",
          "委任先（共通基盤アカウント）の Lambda ロール側にも organizations:ListAccounts の IAM 権限が要る（**両方揃わないと拒否される**）",
        ],
        inputs=[
          ["対象範囲", "OU / 明示リスト / 組織全体", "○", "Lambda 環境変数 or SSM",
           "組織全体だと管理アカウント・監査アカウント等も返るため、**App アカウントに絞る条件が必要**（M-Q-17-2）"],
          ["MaxResults", "number", "—", "実装定数",
           "**最大 20**（ListAccounts の上限。1000 ではない）。ページングは必須"],
        ],
        outputs=[
          ["対象アカウント一覧", "[{accountId, name, state}]", "対象検索-03 以降（メモリ内）",
           "State=ACTIVE のみを対象とする。SUSPENDED / PENDING_CLOSURE / CLOSED は除外"],
          ["列挙結果ログ", "JSON 1 行", "CloudWatch Logs", "取得件数・除外件数・ページ数。アカウント ID は出すがメールアドレスは出さない"],
        ],
        steps=[
          ["委任ポリシー経由で organizations:ListAccounts を呼ぶ（エンドポイントは organizations.us-east-1.amazonaws.com）",
           "Organizations は us-east-1 にホストされるグローバルサービス"],
          ["NextToken が null になるまでページングする。**空の結果が返っても打ち切らない**",
           "【注意】AWS 公式の警告: 「結果が空でも、まだ続きがある場合がある。NextToken が null になるまで繰り返すこと」"],
          ["各アカウントの **State** を見て ACTIVE 以外を除外する",
           "【注意】旧 `Status` パラメータは **2026-09-09 に廃止**。新規実装は **State** を使う（PENDING_ACTIVATION / ACTIVE / SUSPENDED / PENDING_CLOSURE / CLOSED）"],
          ["対象範囲の条件（OU / 明示リスト）で絞り込む",
           "組織全体を返すため、監視対象でないアカウント（管理・監査・ネットワーク等）を除外する"],
          ["結果が 0 件なら異常として扱い、巡回を中断してアラートする",
           "「対象が消えた」のか「権限を失った」のかを区別できないため、黙って 0 件で正常終了しない（誤って全アプリが消滅検知されるのを防ぐ、対象検索-13）"],
        ],
        exceptions=[
          ["AccessDeniedException（委任ポリシー未設定・IAM 権限不足）", "API 例外",
           "巡回を中断（アカウント単位の継続はしない）", "MM-2 → P2 Platform", "16 §16.3"],
          ["TooManyRequestsException（HTTP 400）", "API 例外",
           "SDK 標準リトライ（指数バックオフ）で吸収。それでも失敗なら中断",
           "MM-2 → P2 Platform", "§10 上限・制約"],
          ["空ページが返る（NextToken は非 null）", "応答",
           "**打ち切らず次ページへ進む**", "—", "AWS 公式の明示警告"],
          ["State=SUSPENDED / CLOSED のアカウント", "応答フィールド",
           "対象から除外。台帳に該当アプリがあれば 対象検索-13 で棚卸し対象",
           "棚卸しアラート → P2", "対象検索-13"],
          ["対象 0 件", "件数",
           "巡回を中断し、消滅検知（対象検索-13）を実行しない", "MM-2 → P2 Platform", "対象検索-13 の前提"],
        ],
        idem=(
          "読み取りのみで副作用なし。何度実行しても同じ結果が得られる。",
          "状態を更新しない。",
        ),
        authnote=[
          "**委任方式（推奨）**: 管理アカウントで organizations:PutResourcePolicy によりリソースベース委任ポリシーを設定し、"
          "共通基盤アカウントに organizations:ListAccounts を委任する。管理アカウントへの AssumeRole が不要になる",
          "【注意】委任ポリシーは最大 40,000 文字。**2026-06-30 以降 NotAction / NotResource は使用不可**",
          "代替案: 管理アカウントに列挙専用の読み取りロールを置き AssumeRole（案 a）/ SSM Parameter に静的リスト（案 b）。"
          "案 b はアカウント追加時の登録漏れ = 監視漏れに直結するため非推奨",
        ],
        logs=[
          ["アプリログ", "アカウント列挙結果", "取得件数 / State 別内訳 / 除外件数 / ページ数 / 所要 ms", "メールアドレスは出力しない（個人情報）"],
          ["メトリクス", "—", "本処理単体ではメトリクスを出さない", "巡回全体の結果は 対象検索-14 で集約"],
        ],
        perf=(
          "Phase 1 は約 3 アカウント（1 ページで完了）。将来 100 アカウントでも MaxResults=20 なら 5 ページ・1 秒未満",
          "**ListAccounts のスロットリング: アカウント単位 8 req/s（バースト 12）/ 組織単位 9 req/s（バースト 15）**。"
          "1 時間に 1 回・数ページの呼び出しなので余裕は大きい",
        ),
        opens=[
          ["M-Q-17-2", "列挙方式（委任ポリシー / AssumeRole / 静的リスト）と対象範囲（組織全体 / OU / 明示リスト）の確定", "管理アカウント管理者", ""],
          ["M-Q-PD-4", "App アカウントを識別する条件。OU 単位で括るのか、タグやアカウント名の規約で判定するのか。"
           "組織全体を返す API なので、何らかの絞り込み条件が必ず要る", "設計担当", ""],
        ],
      )),
    P("対象検索-03", "対象アカウント接続権限取得", "対象アカウント接続権限取得", "対象検索（1 時間毎）",
      "対象検索 Lambda", "STS →（各 App の）DiscoveryReadRole", "同期", "対象検索 Lambda", "アカウントごとに 1 回",
      "App アカウントの認証構成情報を読むための一時クレデンシャルを取得する。",
      "sts:AssumeRole + ExternalId / sts.{region}.amazonaws.com（リージョナル STS）",
      "対象検索 Lambda -> STS : AssumeRole(DiscoveryReadRole, ExternalId)\nSTS --> 対象検索 Lambda : 一時クレデンシャル\n【シーケンス図の所在】17 §17.2.1 巡回シーケンス図（対象検索-01〜14 を通した図）/ 10 §10.1.7 F1",
      "クレデンシャルの有効期限とキャッシュ方針を明記する",
      d=dict(
        position="対象検索-02 で得たアカウント一覧のループ先頭。ここで取得した一時クレデンシャルで 対象検索-04 と 対象検索-07 の S3 読み取りを行う。",
        pre=[
          "各 App アカウントに DiscoveryReadRole が StackSets で配布済み（16 §16.2 / WBS S0・S1）",
          "信頼ポリシーの Principal が対象検索 Lambda のロール 1 本に限定され、sts:ExternalId 条件が設定済み",
          "共通基盤側の Lambda ロールに sts:AssumeRole（各 App の DiscoveryReadRole ARN）が付与済み",
        ],
        inputs=[
          ["accountId", "string(12)", "○", "対象検索-02", "ロール ARN を機械的に組み立てる（全アカウント同一ロール名）"],
          ["ロール名", "string", "○", "実装定数", "DiscoveryReadRole（全 App アカウント共通）"],
          ["ExternalId", "string", "○", "Lambda 環境変数",
           "confused deputy 対策。**秘密情報ではない**（AWS 公式: ロールを閲覧できる者には見える）が、値は本基盤が生成し全アカウント共通で管理する"],
          ["DurationSeconds", "number", "—", "実装定数",
           "未指定なら既定 3600 秒。巡回 1 回は分オーダーで終わるため既定で足りる"],
        ],
        outputs=[
          ["一時クレデンシャル", "{AccessKeyId, SecretAccessKey, SessionToken, Expiration}", "対象検索-04 / 対象検索-07（メモリ内）",
           "**ログ・例外メッセージに出力しない**（06 章 OBS-3）"],
          ["AssumeRole 失敗フラグ", "boolean", "対象検索-13 / 対象検索-14",
           "失敗したアカウントは「巡回できなかった」として記録し、**消滅検知の対象から必ず除外する**"],
        ],
        steps=[
          ["ロール ARN を arn:aws:iam::{accountId}:role/DiscoveryReadRole として組み立てる",
           "全アカウントで同一ロール名にしているため、アカウントごとの設定表が不要（16 §16.2）"],
          ["**リージョナル STS エンドポイント**（sts.ap-northeast-1.amazonaws.com）へ AssumeRole する",
           "AWS 公式推奨。グローバルエンドポイントは us-east-1 単一リージョンでホストされ、**他リージョンへの自動フェイルオーバーがない**"],
          ["ExternalId を付与する", "信頼ポリシー側の sts:ExternalId 条件と一致しないと拒否される"],
          ["取得したクレデンシャルは**当該アカウントの処理が終わるまでメモリ上で使い回す**",
           "1 実行内では有効期限（既定 1 時間）に対して十分短いため、アカウントごとに 1 回の取得で足りる。**実行をまたいでの永続キャッシュはしない**"],
          ["失敗したら例外を捕捉し、そのアカウントをスキップして次のアカウントへ進む",
           "1 アカウントの失敗で巡回全体を止めない（18 §18.5.2）。失敗数は 対象検索-14 で DiscoveryAccountErrors として emit"],
        ],
        exceptions=[
          ["AccessDenied（ロール未配布 / 信頼ポリシー不一致 / ExternalId 不一致）", "API 例外",
           "当該アカウントをスキップし継続。**消滅検知の対象から除外**",
           "DiscoveryAccountErrors ≥ 1 → MM-3 → P2 Platform", "18 §18.5.1 / 対象検索-13"],
          ["ロールが存在しない（新規アカウントで StackSets 未反映）", "NoSuchEntity / AccessDenied",
           "同上。StackSets の自動デプロイ待ちとして扱う", "同上", "16 §16.4"],
          ["STS スロットリング", "ThrottlingException",
           "SDK 標準リトライ（指数バックオフ）。それでも失敗ならスキップ", "同上", "§10 上限・制約"],
          ["一時クレデンシャルの期限切れ（長時間実行時）", "S3 呼び出しの ExpiredToken",
           "当該アカウントで AssumeRole をやり直す", "—", "既定 1 時間・延長不可"],
        ],
        idem=(
          "読み取り専用の権限取得であり副作用なし。再実行すると新しいセッションが発行されるだけで、"
          "既存セッションへの影響はない。",
          "状態を更新しない。ただし**失敗したアカウントの記録は 対象検索-13 の消滅検知に必須**（巡回できなかったアカウントのアプリを"
          "「消滅した」と誤判定しないため）。",
        ),
        authnote=[
          "**ExternalId は秘密情報ではない**（AWS 公式）。漏洩対策ではなく confused deputy 対策であり、"
          "実効的な防御は信頼ポリシーの Principal を対象検索 Lambda のロール 1 本に限定している点にある",
          "一時クレデンシャルは**延長・更新不可**。期限が来たら取り直す",
          "クロスアカウント AssumeRole は**呼び出し元（共通基盤）アカウントの STS クォータのみ消費**し、"
          "App アカウント側のクォータは消費しない",
        ],
        logs=[
          ["アプリログ", "AssumeRole 結果", "accountId / 成功可否 / 所要 ms", "**クレデンシャル本体・SessionToken は絶対に出力しない**（OBS-3）"],
          ["監査ログ", "CloudTrail（App アカウント側）", "AssumeRole の記録", "誰がいつどのアカウントへ入ったかの監査証跡（16 §16.2）"],
        ],
        perf=(
          "Phase 1 は約 3 アカウント = 3 回/巡回。将来 100 アカウントでも 100 回/巡回で 1 秒未満",
          "**STS は 600 req/s（アカウント単位・リージョン単位）**。AssumeRole / GetCallerIdentity 等が同じ枠を共有する。"
          "セッション既定 1 時間・最大 12 時間（ロール側 MaxSessionDuration の範囲内）",
        ),
        opens=[],
      )),
    P("対象検索-04", "認証構成情報一覧取得", "認証構成情報一覧・版数取得", "対象検索（1 時間毎）",
      "対象検索 Lambda", "認証構成情報連携バケット（App アカウント）", "同期", "対象検索 Lambda", "アカウントごとに 1 回",
      "連携バケットの {appId}/ を列挙し、各ファイルの版数（VersionId）を取得する（本文は取得しない）。",
      "s3:ListBucket / s3:ListBucketVersions / s3.{region}.amazonaws.com",
      "対象検索 Lambda -> 連携バケット : List（{appId}/ プレフィックス）\n連携バケット --> 対象検索 Lambda : キー一覧 + VersionId\n【シーケンス図の所在】17 §17.2.1 巡回シーケンス図（対象検索-01〜14 を通した図）/ 10 §10.1.7 F1",
      "ページング処理と、monitoring.yaml が無いプレフィックスの扱いを明記する",
      d=dict(
        position="アカウントごとのループ内。対象検索-03 で得たクレデンシャルを使い、そのアカウントの連携バケットを 1 回走査して"
                 "「どのアプリが」「どの版数で」置かれているかの一覧を作る。本文はまだ取得しない。",
        pre=[
          "対象検索-03 で当該アカウントの一時クレデンシャルを取得済み",
          "連携バケット auth-monitoring-artifacts-{accountId} が StackSets で配布済み、**バージョニング有効**（16 §16.4 / WBS S2）",
          "DiscoveryReadRole に s3:ListBucket **および s3:ListBucketVersions** が付与済み（【注意】権限名が別。16 §16.2）",
        ],
        inputs=[
          ["バケット名", "string", "○", "規約から導出", "auth-monitoring-artifacts-{accountId}（全アカウント同一命名、M-Q-17-8）"],
          ["一時クレデンシャル", "object", "○", "対象検索-03", "当該アカウントの DiscoveryReadRole セッション"],
        ],
        outputs=[
          ["認証構成情報インベントリ", "[{appId, key, versionId, lastModified, isDeleteMarker}]", "対象検索-06（メモリ内）",
           "**IsLatest=true のものだけ**を抽出した現行版の一覧。appId はキーの先頭プレフィックスから導出"],
          ["巡回成功アカウント", "boolean", "対象検索-13", "このアカウントを走査できたことの記録（消滅検知の前提）"],
        ],
        steps=[
          ["**ListObjectVersions** でバケットを走査する（ListObjectsV2 ではない）",
           "【注意】**ListObjectsV2 は VersionId を返さない**。版数比較が本方式の検知シグナルであるため、VersionId を返す ListObjectVersions を使う。必要権限は s3:ListBucketVersions"],
          ["ページングする（KeyMarker + VersionIdMarker → NextKeyMarker / NextVersionIdMarker）。1 リクエスト最大 1,000 件",
           "旧版が多いとページ数が増えるため、連携バケットに**旧版の失効ライフサイクル**を設定しておく（WBS A3 と同型。M-Q-17-8）"],
          ["**IsLatest=true** の要素だけを残し、旧版は捨てる",
           "ListObjectVersions は全バージョンを返すため、フィルタしないと過去版を現行版と誤認する"],
          ["DeleteMarker かつ IsLatest=true のキーは「削除された」として記録する",
           "【注意】ListObjectsV2 では delete marker が現行のキーは**そもそも返らない**ため消滅が判別できない。ListObjectVersions を使う副次的な利点であり、対象検索-13 の消滅検知の一次シグナルになる"],
          ["キーを {appId}/{filename} として解釈し、appId 単位にグルーピングする",
           "{appId}/monitoring.yaml が存在するグループだけを監視対象候補とする（17 §17.3）"],
          ["monitoring.yaml が無いプレフィックスは候補から外す",
           "openapi.yaml だけが置かれている等の中途半端な状態。監視宣言がない以上、対象にしない（不備通知の対象にもしない）"],
          ["本文（GetObject）はここでは取得しない",
           "版数に変化がないアプリは本文取得そのものをスキップし、クロスアカウント転送をゼロにする（17 §17.2.1 差分判定の 3 原則 ②）"],
        ],
        exceptions=[
          ["バケットが存在しない（StackSets 未反映の新規アカウント）", "NoSuchBucket",
           "当該アカウントをスキップして継続", "DiscoveryAccountErrors → MM-3 → P2", "18 §18.5.2"],
          ["AccessDenied（s3:ListBucketVersions 権限漏れ）", "API 例外",
           "同上。**ListBucket だけ付与して ListBucketVersions を忘れる**のが典型的な設定漏れ", "同上", "16 §16.2"],
          ["monitoring.yaml が無いプレフィックス", "インベントリ",
           "監視対象候補から除外（通知もしない）", "—", "17 §17.3"],
          ["現行版が DeleteMarker", "IsLatest=true の DeleteMarker",
           "「削除された」として記録し、対象検索-13 へ渡す", "棚卸しアラート → P2", "対象検索-13"],
          ["503 Slow Down", "API 例外",
           "SDK 標準リトライ（指数バックオフ）。頻発する場合は旧版が過剰に蓄積している可能性",
           "継続失敗なら DiscoveryAccountErrors → MM-3", "§10 上限・制約"],
        ],
        idem=(
          "読み取りのみ。同じ時点で何度実行しても同じインベントリが得られる。",
          "状態を更新しない。",
        ),
        authnote=[
          "s3:ListBucket（ListObjectsV2 用）と **s3:ListBucketVersions**（ListObjectVersions 用）は**別の権限名**。本処理が使うのは後者",
          "対象はバケット全体（プレフィックス条件なし）。1 アカウント = 1 バケットで、そこに複数アプリのプレフィックスが同居する",
          "読み取りは AWS API 経由でインターネット境界を通らない（10 §10.1.6 経路 C）",
        ],
        logs=[
          ["アプリログ", "インベントリ取得結果", "accountId / 発見アプリ数 / 現行版キー数 / ページ数 / 所要 ms", "ファイル本文は取得しないため内容ログはなし"],
          ["アプリログ", "delete marker 検出", "accountId / appId / key", "対象検索-13 の入力となる"],
        ],
        perf=(
          "Phase 1 は 1 アカウントあたり数アプリ × 2〜3 ファイル = 数十バージョン。1 ページ（1,000 件）で完了する",
          "**ListObjectVersions は 1 リクエスト最大 1,000 件**（全バージョン込み）。旧版が蓄積するとページ数が増えるため、"
          "ライフサイクルでの旧版失効が前提。プレフィックス単位のレート上限は GET/HEAD 5,500 req/s・PUT 等 3,500 req/s で、本用途では問題にならない",
        ),
        opens=[
          ["M-Q-17-8", "連携バケットの命名規約・暗号化方式・**旧版のライフサイクル（保持期間）**。"
           "旧版が無制限に溜まると ListObjectVersions のページ数が増える", "設計担当", ""],
        ],
      )),
    P("対象検索-05", "前回確認状態取得", "前回確認状態取得", "対象検索（1 時間毎）",
      "対象検索 Lambda", "認証構成情報配置バケット（registry/）", "同期", "対象検索 Lambda", "アプリごとに 1 回",
      "前回巡回時に確認した版数（lastArtifactVersions）などの状態を台帳から読み取る。",
      "s3:GetObject（同一アカウント）/ s3.{region}.amazonaws.com",
      "対象検索 Lambda -> 配置バケット : GetObject(registry/{appId}/{env}.json)\n配置バケット --> 対象検索 Lambda : 台帳 JSON（無ければ新規扱い）\n【シーケンス図の所在】17 §17.2.1 巡回シーケンス図（対象検索-01〜14 を通した図）/ 10 §10.1.7 F1",
      "台帳が存在しない場合（初回）の扱いを明記する",
      d=dict(
        position="対象検索-04 の直後、アプリ単位のループ先頭。ここで読んだ前回状態と 対象検索-04 のインベントリを 対象検索-06 で突き合わせる。",
        pre=[
          "認証構成情報配置バケット（共通基盤アカウント）が作成済み・バージョニング有効（WBS A1）",
          "対象検索-04 で当該アカウントの現行版インベントリを取得済み",
          "【注意】この時点では **monitoring.yaml を未取得のため、そのアプリにどの環境（env）があるか分からない**。"
          "したがって台帳は appId 単位でプレフィックス走査する",
        ],
        inputs=[
          ["appId", "string", "○", "対象検索-04", "連携バケットのプレフィックスから導出した値"],
          ["registry/{appId}/ プレフィックス", "S3 キー", "○", "規約",
           "1 アプリ × N 環境 = N オブジェクト（registry/{appId}/prod.json, registry/{appId}/stg.json …）"],
        ],
        outputs=[
          ["前回状態", "[{env, lastArtifactVersions, lastRejectedVersions, enabled, ETag, …}]", "対象検索-06 / 対象検索-09（メモリ内）",
           "env ごとの台帳レコード。**ETag は 対象検索-09 の条件付き書き込み（If-Match）に使うため必ず保持する**"],
          ["初回フラグ", "boolean", "対象検索-06", "台帳レコードが 1 件も無い = 新規アプリ。全環境を「変更あり」として扱う"],
        ],
        steps=[
          ["registry/{appId}/ プレフィックスを List し、存在する env レコードのキーを得る",
           "monitoring.yaml 未取得の段階では env が不明なため、台帳側から現在登録されている env を知る"],
          ["各レコードを GetObject し、lastArtifactVersions / lastRejectedVersions / enabled / alertRouting を読む",
           "**応答の ETag を必ず保持する**。対象検索-09 の If-Match に使う（読んだ時点から誰も更新していないことの証明）"],
          ["1 件も無ければ初回フラグを立てる",
           "新規アプリ。この後 対象検索-06 で無条件に「変更あり」と判定され、対象検索-09 で台帳が自動生成される（登録漏れが構造的に起きない仕組み）"],
          ["enabled=false かつ lastRejectedVersions を持つレコードは**取り込み拒否レコード**として識別する",
           "前回の巡回で不備により取り込みを拒否したアプリ。対象検索-06 で「同じ版なら再通知しない」判定に使う（2026-09-14 確定）"],
          ["取得できなかった（AccessDenied 等）場合はアプリ単位でスキップして次のアプリへ進む",
           "中央側 S3 の読み取り失敗は設定不備の可能性が高い。1 アプリで巡回全体を止めない"],
        ],
        exceptions=[
          ["台帳レコードが存在しない（新規アプリ）", "List 結果が空",
           "初回フラグを立てて継続（正常系）", "—", "17 §17.2.1 新規発見"],
          ["レコードは在るが JSON が壊れている", "パース例外",
           "当該 env をスキップし、他の env は継続。台帳は上書きしない（人手での復旧対象）",
           "メタ不足アラート → P2 Platform", "M-Q-PD-5"],
          ["enabled=false（中央が意図的に監視停止）", "レコード値",
           "**検査は起動しないが、巡回による台帳同期は続ける**", "—", "12 章 中央管理項目"],
          ["enabled=false + lastRejectedVersions あり（取り込み拒否レコード）", "レコード値",
           "対象検索-06 で再評価。版数が変われば再取り込みを試みる", "—", "対象検索-06 / 対象検索-12"],
          ["AccessDenied / 通信エラー", "API 例外",
           "アプリ単位でスキップして継続", "DiscoveryAccountErrors → MM-3 → P2", "18 §18.5.2"],
        ],
        idem=(
          "読み取りのみ。副作用なし。",
          "状態を更新しない。**ETag を保持することが次工程（対象検索-09）の楽観ロックの前提**になる。",
        ),
        authnote=[
          "共通基盤アカウント内の S3 読み取りのため、IAM のみで完結（クロスアカウント権限は不要）",
          "【注意】対象検索-09 で If-Match による条件付き書き込みを使うには **s3:PutObject に加えて s3:GetObject も必要**（AWS 公式）。"
          "本処理で GetObject しているため要件は満たされる",
        ],
        logs=[
          ["アプリログ", "台帳読み取り結果", "appId / 取得した env 数 / 初回フラグ / 拒否レコードの有無", "alertRouting の SNS ARN は出力しない"],
        ],
        perf=(
          "1 アプリあたり List 1 回 + GetObject（env 数分、通常 1〜2 回）。Phase 1 全体で数十回/巡回",
          "S3 プレフィックス単位 GET/HEAD 5,500 req/s。台帳は KB オーダーで転送量は誤差",
        ),
        opens=[
          ["M-Q-PD-5", "台帳 JSON が破損していた場合の復旧手順（バージョニングからの巻き戻しを Runbook 化するか）。"
           "配置バケットはバージョニング有効なので旧版から復元可能", "運用設計（WBS W4-1）", ""],
        ],
      )),
    P("対象検索-06", "認証構成情報比較", "認証構成情報比較", "対象検索（1 時間毎）",
      "対象検索 Lambda（内部）", "—", "内部", "対象検索 Lambda", "アプリごとに 1 回",
      "連携バケットの版数と台帳の記録値を比較し、認証実装確認の要否を判定する。",
      "—（AWS 呼び出しなし）",
      "対象検索 Lambda : VersionId ↔ lastArtifactVersions を比較\n判定結果 = 変更あり / 変更なし / 新規\n【シーケンス図の所在】17 §17.2.1 巡回シーケンス図（対象検索-01〜14 を通した図）/ 10 §10.1.7 F1",
      "【重要】比較は版数（メタデータ）で行い、内容ハッシュ比較にしない（17 §17.2.1 差分判定の 3 原則）",
      d=dict(
        position="対象検索-04（現行版インベントリ）と 対象検索-05（前回状態）の突き合わせ。**本機構の検知シグナルを決める中核処理**で、"
                 "ここで「変更あり」と判定されたアプリだけが 対象検索-07 以降へ進む。",
        pre=[
          "対象検索-04 で現行版の VersionId 一覧を取得済み",
          "対象検索-05 で台帳の lastArtifactVersions / lastRejectedVersions を取得済み（初回はレコードなし）",
        ],
        inputs=[
          ["現行版 VersionId", "{monitoring.yaml: string, openapi.yaml: string}", "○", "対象検索-04", "連携バケットの IsLatest=true の版数"],
          ["lastArtifactVersions", "map / null", "—", "対象検索-05（台帳）",
           "前回**検査依頼まで成功した**版数。env ごとに同じ値が複写されている（2026-09-14 確定）"],
          ["lastRejectedVersions", "map / null", "—", "対象検索-05（台帳）", "前回**不備で取り込みを拒否した**版数。再通知抑制の判定に使う"],
          ["初回フラグ", "boolean", "—", "対象検索-05", "台帳レコードが 1 件も無い = 新規アプリ"],
        ],
        outputs=[
          ["判定結果", "enum(新規 / 変更あり / 変更なし / 拒否済みと同一)", "対象検索-07 以降（メモリ内）",
           "「変更あり」「新規」のみ 対象検索-07 へ進む。「拒否済みと同一」は本文取得も通知もせずスキップ"],
          ["判定ログ", "JSON 1 行", "CloudWatch Logs", "appId / 前回版数 / 今回版数 / 判定"],
        ],
        steps=[
          ["初回フラグが立っていれば無条件に「新規」と判定する", "台帳が無い = まだ一度も監視に入っていないアプリ（17 §17.2.1 新規発見）"],
          ["現行版 VersionId と lastArtifactVersions を比較する。**いずれか 1 ファイルでも異なれば「変更あり」**",
           "monitoring.yaml と openapi.yaml は独立に更新されうるため、AND ではなく OR で判定する"],
          ["【原則②】比較は**版数（メタデータ）**で行い、**ファイル内容のハッシュ比較にしてはならない**",
           "検知したいのは「アップロードされた＝デプロイされた」こと。内容が前回と同一でも、コード側で認証 middleware が外れている可能性がある。"
           "内容比較にすると『仕様書が変わらないデプロイ』を丸ごと取りこぼす（17 §17.2.1）"],
          ["ETag は**補助にとどめ、判定の主キーにしない**",
           "【注意】AWS 公式: マルチパートアップロードで作成したオブジェクトの ETag は MD5 と一致しない（`ハッシュ-N` 形式）。"
           "**SSE-KMS で暗号化した場合も ETag は MD5 ではない**。コンソール経由は 16MB 超で自動的にマルチパートになる"],
          ["「変更あり」かつ lastRejectedVersions と現行版数が**完全一致**する場合は「拒否済みと同一」と判定し、"
           "本文取得・通知とも行わずスキップする",
           "前回の巡回で不備により拒否した版がそのまま置かれている状態。毎時同じアラートを出さないための抑制（2026-09-14 確定）。"
           "アプリが修正して再アップロードすれば版数が変わるので、自動的に再評価される"],
          ["「変更なし」なら本文（GetObject）を取得せず次のアプリへ進む",
           "クロスアカポントの転送をゼロにする。変化がない限り連携バケットからは 1 バイトも読まない（原則②の副次効果）"],
          ["【原則③】判定結果は「**起動のトリガー**」であり、**検査範囲の絞り込みには使わない**",
           "変更のあったアプリは全 endpoint を検査する。どの endpoint が変わったかを版数差分から求める必要はない（18 §18.2.1）"],
        ],
        exceptions=[
          ["monitoring.yaml はあるが openapi.yaml が無い", "インベントリ",
           "monitoring.yaml の版数だけで判定。openapi.yaml は 対象検索-08 の検証で「endpoint 列挙方式」として扱う",
           "—", "17 §17.3 / §17.4 モノリス"],
          ["版数が**戻った**（過去版を再アップロードした等）", "版数の不一致",
           "「変更あり」と判定する（前回と違えば変更）", "—", "版数は単調増加ではなく不透明文字列のため、大小比較はしない"],
          ["現行版が DeleteMarker", "対象検索-04 の出力",
           "本処理では扱わず、対象検索-13 の消滅検知に委ねる", "棚卸しアラート → P2", "対象検索-13"],
          ["lastArtifactVersions が欠損（台帳はあるがフィールドが無い）", "台帳値",
           "「変更あり」として扱う（安全側）", "—", "旧スキーマからの移行時に起こりうる"],
        ],
        idem=(
          "純粋な比較処理で副作用なし。同じ入力なら常に同じ判定になる。",
          "状態を更新しない。**lastArtifactVersions の更新は 対象検索-11 の検査依頼が成功した後**に行うため、"
          "途中で失敗しても次回巡回で同じ差分が再検知される（at-least-once、18 §18.5.2）。",
        ),
        authnote=["AWS API の呼び出しを伴わない内部処理。"],
        logs=[
          ["アプリログ", "差分判定", "appId / 前回版数 / 今回版数 / 判定結果 / 判定理由", "版数は不透明文字列。そのまま出力してよい（機微情報ではない）"],
        ],
        perf=("アプリ数分のメモリ内比較。実質ゼロコスト", "—"),
        opens=[],
      )),
    P("対象検索-07", "認証構成情報取得", "認証構成情報取得", "対象検索（1 時間毎）",
      "対象検索 Lambda", "認証構成情報連携バケット（App アカウント）", "同期", "対象検索 Lambda", "変更のあったアプリのみ",
      "変更が検知されたアプリの認証構成情報（monitoring.yaml / openapi.yaml / deploy-info.json）を取得する。",
      "s3:GetObject / s3:GetObjectVersion / s3.{region}.amazonaws.com",
      "対象検索 Lambda -> 連携バケット : GetObject(monitoring.yaml, openapi.yaml)\n連携バケット --> 対象検索 Lambda : ファイル本体\n【シーケンス図の所在】17 §17.2.1 巡回シーケンス図（対象検索-01〜14 を通した図）/ 10 §10.1.7 F1",
      "サイズ上限・文字コード・取得失敗時の扱いを明記する",
      d=dict(
        position="対象検索-06 で「新規」または「変更あり」と判定されたアプリのみ実行する。ここで初めて連携バケットから本文を読む。",
        pre=[
          "対象検索-06 で変更ありと判定済み",
          "対象検索-03 の一時クレデンシャルが有効（期限切れなら取り直す）",
          "DiscoveryReadRole に s3:GetObject **および s3:GetObjectVersion** が付与済み（16 §16.2）",
        ],
        inputs=[
          ["バケット / キー", "string", "○", "対象検索-04", "auth-monitoring-artifacts-{accountId} / {appId}/monitoring.yaml ほか"],
          ["versionId", "string", "○", "対象検索-04",
           "**対象検索-04 で観測した版を versionId 指定で取得する**。無指定にしない（取得中に上書きされると版数と内容がずれるため）"],
        ],
        outputs=[
          ["monitoring.yaml 本文", "string(YAML)", "対象検索-08（メモリ内）", "監視宣言。UTF-8"],
          ["openapi.yaml 本文", "string(YAML/JSON)", "対象検索-08 / 対象検索-10", "API 仕様。存在しない場合は null"],
          ["deploy-info.json 本文", "string(JSON) / null", "対象検索-09", "任意。commitId / deployedAt。**検知には使わず追跡用の参考値**（17 §17.3）"],
        ],
        steps=[
          ["**versionId を明示指定して** GetObject する",
           "対象検索-04 で観測した版と、実際に取り込む内容を一致させるため。無指定だと取得のタイミングで別の版を読む可能性がある"],
          ["monitoring.yaml → openapi.yaml → deploy-info.json の順に取得する",
           "monitoring.yaml が取れなければ以降は不要（監視宣言がないため）"],
          ["取得した本文をサイズ上限で打ち切る",
           "想定は KB オーダー。異常に大きいファイルはメモリ保護のため拒否する（上限値は §10 / M-Q-PD-6）"],
          ["deploy-info.json が無い / 壊れている場合は無視して継続する",
           "任意項目であり、監視の動作には影響しない（17 §17.3）"],
          ["取得失敗はアプリ単位でスキップし、**台帳を更新しない**",
           "版数を更新しなければ次回巡回で同じ差分が再検知される（at-least-once）"],
        ],
        exceptions=[
          ["NoSuchKey / 404（取得直前に削除された）", "API 例外",
           "アプリ単位でスキップ。次回巡回または 対象検索-13 で消滅として扱う", "—", "対象検索-13"],
          ["405 Method Not Allowed", "API 応答",
           "指定した版が delete marker。消滅として扱う", "棚卸しアラート → P2", "delete marker を versionId 指定で取得した場合の AWS 仕様"],
          ["AccessDenied（s3:GetObjectVersion 権限漏れ）", "API 例外",
           "アプリ単位でスキップ。**versionId 指定の GetObject には s3:GetObject ではなく s3:GetObjectVersion が必要**（AWS 公式）",
           "DiscoveryAccountErrors → MM-3 → P2", "16 §16.2"],
          ["サイズ上限超過", "取得サイズ",
           "取り込み拒否とし、対象検索-12 で不備通知", "メタ不足アラート → P2", "M-Q-PD-6"],
          ["文字コードが UTF-8 でない / BOM 付き", "パース時",
           "BOM は除去して継続。デコード不能なら取り込み拒否", "メタ不足アラート → P2", "対象検索-08"],
        ],
        idem=(
          "読み取りのみ。versionId を固定しているため、何度取得しても同じ内容が得られる（S3 の版は不変）。",
          "状態を更新しない。取得失敗時に台帳を更新しないことで、次回巡回でのリトライが成立する。",
        ),
        authnote=[
          "【注意】**versionId を指定する GetObject には `s3:GetObjectVersion` が必要**（`s3:GetObject` では足りない）。16 章の権限に両方含めている",
          "取得した本文には顧客の API パス等が含まれる。ログには**本文を出力しない**（件数・サイズのみ）",
        ],
        logs=[
          ["アプリログ", "本文取得", "appId / key / versionId / サイズ / 所要 ms", "**本文は出力しない**（OBS-3）"],
        ],
        perf=(
          "変更のあったアプリのみ 2〜3 オブジェクト。Phase 1 では 1 巡回あたり 0〜数アプリ = 数回の GetObject",
          "想定サイズは monitoring.yaml 数 KB / openapi.yaml 数十〜数百 KB。上限値は M-Q-PD-6 で確定。"
          "Lambda のメモリ内に収める（S3 へのストリーミング処理はしない）",
        ),
        opens=[
          ["M-Q-PD-6", "認証構成情報のサイズ上限（openapi.yaml が巨大なアプリの扱い）。"
           "旧 CodeCommit 方式には GetFile の 6MB 制約があったが、S3 には該当する API 制約がないため、"
           "**Lambda のメモリと処理時間から上限を決める必要がある**（案: 1 ファイル 5MB）", "設計担当", ""],
        ],
      )),
    P("対象検索-08", "認証構成情報検証", "認証構成情報検証", "対象検索（1 時間毎）",
      "対象検索 Lambda（内部）", "—", "内部", "対象検索 Lambda", "取得ごとに 1 回",
      "monitoring.yaml のスキーマ検証と、appId とプレフィックスの一致検証を行う。",
      "—（AWS 呼び出しなし）",
      "対象検索 Lambda : YAML パース -> JSON Schema 検証 -> appId 一致検証\nNG の場合は 対象検索-12 構成情報不備通知へ\n【シーケンス図の所在】17 §17.2.1 巡回シーケンス図（対象検索-01〜14 を通した図）/ 10 §10.1.7 F1",
      "不備の分類（取り込み拒否 / 既定値で継続）を項目ごとに定義する（17 §17.3 の表）",
      d=dict(
        position="対象検索-07 の直後。ここで初めて「このアプリにどの環境（env）があるか」が判明し、以降の台帳更新・検査依頼の単位が確定する。",
        pre=["対象検索-07 で monitoring.yaml 本文を取得済み", "JSON Schema（W5-2 の配布物と同一）が Lambda に同梱されていること"],
        inputs=[
          ["monitoring.yaml 本文", "string(YAML)", "○", "対象検索-07", "—"],
          ["S3 プレフィックスの appId", "string", "○", "対象検索-04", "宣言値との一致検証に使う"],
          ["JSON Schema", "object", "○", "Lambda 同梱", "**アプリへ配布するものと同一のスキーマ**を使う（W5-2）。中央とアプリで判定が食い違わないようにする"],
        ],
        outputs=[
          ["検証済み構成", "{appId, environments:{env:{baseUrl, authPattern}}, testTokenSecret}", "対象検索-09 / 対象検索-11", "—"],
          ["env 一覧", "[string]", "対象検索-09 / 対象検索-11", "**ここで確定する**。台帳レコードと検査依頼はこの env 単位で行う"],
          ["不備リスト", "[{種別, 該当項目, 重大度}]", "対象検索-12", "取り込み拒否か既定値継続かの分類つき"],
        ],
        steps=[
          ["YAML をパースする。失敗したら**取り込み拒否**", "構文エラーは既定値で救えない"],
          ["JSON Schema で検証する", "アプリへ配布するスキーマと同一物を使い、アプリ側の事前検証と中央の判定を一致させる"],
          ["**appId が S3 プレフィックスと一致するか**を検証する。不一致なら**取り込み拒否**",
           "他アプリのプレフィックスに置かれた構成情報を取り込まないための最低限の防御（17 §17.3）"],
          ["environments が 1 つも無ければ**取り込み拒否**", "検査先が決まらないため監視できない"],
          ["各 env の baseUrl を検証する。欠落・形式不正は**その env を取り込み拒否**",
           "baseUrl が無ければ検査不能（17 §17.3）"],
          ["baseUrl のホストが**そのアプリに払い出されたドメイン**かを検証する。合致しなければ取り込み拒否",
           "【重要・2026-09-14 確定】外向き通信の宛先は台帳の baseUrl で決まるため、ここが実質的な宛先 allowlist の入口になる。"
           "任意ドメインを書けると監視基盤を踏み台にできてしまう（10 §10.1.6 代償統制）。"
           "検証は 2 段: ① ホストが**組織の許可ドメインサフィックス**（中央管理・SSM）配下であること "
           "② そのホストが**当該アプリのドメイン**であること（1 アプリ = 1 ホスト。他アプリのドメインを指定させない）。"
           "*.cloudfront.net のような共有ドメインはサフィックスとして許可しない（他社も使うため）"],
          ["authPattern が enum（6 値）に無い値なら**既定値 api-gw-jwt で継続**し、不備として記録する",
           "検査を止めるより、未認証確認だけでも回す方が安全側（17 §17.3）"],
          ["testTokenSecret の指定があれば形式のみ検証する（実在確認はしない）",
           "Secrets Manager への到達性確認は認証実装チェック-03 の責務"],
          ["取り込み拒否と判定した場合は 対象検索-12 へ渡し、**台帳には拒否レコードを書く**（対象検索-09）",
           "enabled=false + lastRejectedVersions + rejectedReason。これにより同じ版での再通知を抑制し、"
           "「不備で監視に入っていないアプリ」を台帳で可視化する（2026-09-14 確定）"],
        ],
        exceptions=[
          ["YAML 構文エラー", "パース例外", "取り込み拒否", "メタ不足アラート → P2 Platform", "対象検索-12"],
          ["appId 不一致", "検証", "取り込み拒否", "同上（**重大度を上げる**。他アプリ領域への誤配置または意図的な混入の可能性）", "17 §17.3"],
          ["baseUrl 欠落 / 形式不正", "検証", "当該 env のみ取り込み拒否（他の env は継続）", "同上", "17 §17.3"],
          ["baseUrl が組織の許可ドメインサフィックス外", "検証", "取り込み拒否（**継続しない**）", "同上（重大度を上げる）", "10 §10.1.6"],
          ["baseUrl が他アプリのドメイン", "検証（appId とホストの対応）", "取り込み拒否（**継続しない**）",
           "同上（重大度を上げる。監視基盤を別アプリへ向けようとする操作の可能性）", "2026-09-14 確定"],
          ["authPattern 不正", "検証", "既定値 api-gw-jwt で継続（未認証確認のみ有効）", "同上", "17 §17.3"],
          ["環境が減っていた（前回 prod+stg → 今回 prod のみ）", "env 一覧の差分",
           "残った env のみ同期。消えた env の台帳レコードは 対象検索-13 の棚卸し対象",
           "棚卸しアラート → P2", "M-Q-PD-8"],
        ],
        idem=("純粋な検証処理で副作用なし。", "状態を更新しない（拒否レコードの書き込みは 対象検索-09）。"),
        authnote=["AWS API の呼び出しを伴わない内部処理。"],
        logs=[
          ["アプリログ", "検証結果", "appId / env 一覧 / 不備種別 / 判定（拒否 or 継続）", "**baseUrl は出力してよいが、monitoring.yaml 全文は出力しない**"],
        ],
        perf=("アプリあたり数 ms。実質ゼロコスト", "—"),
        opens=[
          ["M-Q-PD-7", "【解決・2026-09-14】外向きの宛先は**そのアプリのドメインに限定**すると確定。"
           "残るのは実装値のみ: ① 組織の許可ドメインサフィックス一覧の確定と置き場（SSM 推奨）"
           "② appId とホストの対応をどう持つか（命名規約で導出するか、中央管理項目として台帳に持つか）", "設計担当", ""],
          ["M-Q-PD-8", "monitoring.yaml から環境が削除された場合の扱い（台帳レコードを enabled=false にするか、"
           "誤削除の可能性を考えて棚卸し通知にとどめるか）", "設計担当", ""],
        ],
      )),
    P("対象検索-09", "認証構成情報登録", "認証構成情報登録", "対象検索（1 時間毎）",
      "対象検索 Lambda", "認証構成情報配置バケット（registry/）", "同期", "対象検索 Lambda", "変更のあったアプリのみ",
      "台帳へ設定値を同期し、確認状態を更新する。中央管理項目（通知先・監視有効フラグ）は上書きしない。",
      "s3:PutObject（ETag 条件付き PUT, If-Match）/ s3.{region}.amazonaws.com",
      "対象検索 Lambda -> 配置バケット : PutObject（If-Match: 読取時 ETag）\n412 の場合は再読取してリトライ\n【シーケンス図の所在】17 §17.2.1 巡回シーケンス図（対象検索-01〜14 を通した図）/ 10 §10.1.7 F1",
      "alertRouting / enabled を上書きしないマージ規則と、412 競合時のリトライ回数を明記する",
      d=dict(
        position="対象検索-08 で検証を通った env ごとに実行する。**巡回で唯一の書き込み処理**であり、ここで台帳が実行用ビューとして同期される。",
        pre=[
          "対象検索-05 で当該レコードの **ETag を取得済み**（新規作成時は無し）",
          "対象検索-08 で env 一覧と検証済み構成を確定済み",
          "配置バケットがバージョニング有効（誤更新時に旧版へ戻せる）",
        ],
        inputs=[
          ["検証済み構成", "object", "○", "対象検索-08", "baseUrl / authPattern / testTokenSecret"],
          ["既存レコード + ETag", "object / null", "—", "対象検索-05", "**If-Match に使う**。null なら新規作成"],
          ["deployInfo", "object / null", "—", "対象検索-07", "追跡用参考値"],
          ["判定結果", "enum", "○", "対象検索-06 / 対象検索-08", "正常同期か、取り込み拒否レコードの書き込みか"],
        ],
        outputs=[
          ["台帳レコード", "S3 オブジェクト", "配置バケット registry/{appId}/{env}.json", "1 アプリ×環境 = 1 オブジェクト"],
          ["更新後 ETag", "string", "対象検索-11（メモリ内）", "**検査依頼成功後の版数確定更新で再度 If-Match に使う**"],
        ],
        steps=[
          ["既存レコードに検証済み構成をマージする。**alertRouting と enabled は既存値を保持し、上書きしない**",
           "この 2 つは中央管理項目であり、アプリ側の宣言で変えられてはならない（12 章 / 17 §17.3）。"
           "SNS ARN を外部ベンダーの手に置かないことと、アプリが勝手に監視を止められないようにすることが目的"],
          ["registeredAt は新規作成時のみ設定し、以降は保持する", "—"],
          ["lastSeenAt を現在時刻で更新する", "消滅検知・鮮度低下検知（対象検索-13）の基準"],
          ["**lastArtifactVersions はここでは更新しない**",
           "【注意】更新は 対象検索-11 の検査依頼が成功した後（17 §17.2.1 ⑦）。先に更新すると、検査依頼が失敗したときに"
           "「確認済み」と記録されたまま検査されない状態になる（偽安心）"],
          ["取り込み拒否の場合は enabled=false + lastRejectedVersions + rejectedReason を書く",
           "同じ版での再通知を抑制し、未監視アプリを台帳で可視化する（2026-09-14 確定）。"
           "**新規アプリでも最小レコードを作る**（拒否状態を記録する場所が必要なため）"],
          ["正常に取り込めた場合は lastRejectedVersions / rejectedReason を**クリアする**", "不備が解消されたことを台帳に反映する"],
          ["**If-Match（既存 ETag）付きで PutObject する**。新規作成時は **If-None-Match: *** を使う",
           "【注意】AWS 公式: If-Match には `s3:PutObject` に加えて **`s3:GetObject` も必要**。If-None-Match は `s3:PutObject` のみ。"
           "If-None-Match は 2024-08 GA、If-Match は 2024-11 GA で全リージョン利用可"],
          ["**412 Precondition Failed** なら再読込してマージし直し、上限回数まで再試行する",
           "他の書き手（運用者の手動更新＝運用-03、または多重起動した巡回）と競合した。"
           "**楽観ロックの敗北であり、状態を読み直してからリトライする**。上限は M-Q-PD-9"],
          ["**409 Conflict** なら単純リトライする",
           "AWS 公式: 並行する DELETE 等との競合。PutObject は単純リトライ可"],
          ["**404 Not Found**（If-Match 指定時）なら、レコードが削除されたとみなし新規作成に切り替える",
           "AWS 公式: 現行版が無い / delete marker / 並行 DELETE が先に成功した場合に返る"],
        ],
        exceptions=[
          ["412 Precondition Failed", "API 応答", "再読込 → マージ → 再試行（上限あり）",
           "上限超過で DiscoveryAccountErrors → MM-3 → P2", "M-Q-PD-9"],
          ["409 Conflict", "API 応答", "単純リトライ", "同上", "AWS 公式（並行 DELETE との競合）"],
          ["404 Not Found（If-Match 時）", "API 応答", "新規作成（If-None-Match: *）に切り替え", "—", "同上"],
          ["AccessDenied（s3:GetObject 未付与で If-Match が使えない）", "API 例外",
           "アプリ単位でスキップ", "DiscoveryAccountErrors → MM-3 → P2", "16 §16.3"],
          ["env が増えた（prod のみ → prod+stg）", "env 一覧",
           "新しい env のレコードを新規作成する", "—", "対象検索-08"],
        ],
        idem=(
          "同じ入力で再実行しても、マージ結果は同じ内容に収束する（冪等）。"
          "条件付き書き込みにより、競合時は必ずどちらか一方だけが成功する。",
          "**lastArtifactVersions はここでは更新しない**（対象検索-11 の成功後）。"
          "これにより、台帳同期には成功したが検査依頼に失敗した場合でも、次回巡回で同じ差分が再検知される（at-least-once、18 §18.5.2）。",
        ),
        authnote=[
          "共通基盤アカウント内の書き込みであり、クロスアカウント権限は発生しない（ADR-061 の pull 原則）",
          "【注意】**If-Match を使うには s3:GetObject が必須**（AWS 公式）。IAM 設計時に見落としやすい",
          "書き込み経路は対象検索 Lambda と運用者（運用-03）の 2 つ。両者とも If-Match を使うことで相互に上書きしない",
        ],
        logs=[
          ["アプリログ", "台帳更新", "appId / env / 新規 or 更新 / 拒否の有無 / 412 リトライ回数", "alertRouting の SNS ARN は出力しない"],
          ["監査", "S3 バージョニング", "更新前の版がバケットに保全される", "誤更新時の巻き戻し手段（M-Q-PD-5）"],
        ],
        perf=(
          "変更のあったアプリ × env 数。Phase 1 では 1 巡回あたり 0〜数回の PutObject",
          "S3 プレフィックス単位の PUT は 3,500 req/s。**単一オブジェクトへの条件付き書き込みは競合すると 412 になる**ため、"
          "同一レコードへの同時書き込みを増やさない設計（予約同時実行 1 の検討＝M-Q-PD-3）と併せて考える",
        ),
        opens=[
          ["M-Q-PD-9", "412 競合時のリトライ回数と待ち方（案: 3 回・短いジッタ付き）。"
           "競合相手は運用者の手動更新（運用-03）か多重起動した巡回で、いずれも頻度は低い", "設計担当", ""],
        ],
      )),
    P("対象検索-10", "API仕様登録", "API 仕様登録", "対象検索（1 時間毎）",
      "対象検索 Lambda", "認証構成情報配置バケット（openapi/）", "同期", "対象検索 Lambda", "変更のあったアプリのみ",
      "取得した API 仕様（openapi.yaml）を中央の仕様保管領域へ複写する。",
      "s3:PutObject / s3.{region}.amazonaws.com",
      "対象検索 Lambda -> 配置バケット : PutObject(openapi/{accountId}/{appId}/openapi.yaml)\n【シーケンス図の所在】17 §17.2.1 巡回シーケンス図（対象検索-01〜14 を通した図）/ 10 §10.1.7 F1",
      "キー導出規則と上書き方針（Versioning による履歴保全）を明記する",
      d=dict(
        position="対象検索-09 と同じく、検証を通ったアプリに対して実行する。検査側（認証実装チェック-02）が読む API 仕様の置き場を用意する。",
        pre=["対象検索-07 で openapi.yaml 本文を取得済み（無い場合は本処理をスキップ）", "配置バケットがバージョニング有効"],
        inputs=[
          ["openapi.yaml 本文", "string", "○", "対象検索-07", "デプロイされた版の写し"],
          ["accountId / appId", "string", "○", "対象検索-02 / 対象検索-04", "キー導出に使う"],
        ],
        outputs=[
          ["API 仕様の複写", "S3 オブジェクト", "配置バケット openapi/{accountId}/{appId}/openapi.yaml",
           "**認証実装チェック-02 が読む唯一の情報源**"],
          ["openApiS3Key", "string", "対象検索-09（台帳へ）", "検査側がキーを導出せずに済むよう、台帳に持たせる"],
        ],
        steps=[
          ["キーを openapi/{accountId}/{appId}/openapi.yaml として導出する",
           "accountId を含めることで、appId が別アカウントで重複しても衝突しない"],
          ["PutObject で**上書き**する（条件付き書き込みは使わない）",
           "書き手が対象検索 Lambda 1 本だけであり競合しないため。台帳（対象検索-09）と異なり中央管理項目も無い"],
          ["旧版はバージョニングが保全する",
           "「いつどの仕様で検査したか」を後から追える。旧版の失効はライフサイクルで管理（WBS A3）"],
          ["openapi.yaml が無いアプリは本処理をスキップする",
           "ALB 直モノリス等。endpoint は monitoring.yaml の列挙を使う（17 §17.4）"],
          ["台帳へ書く openApiS3Key は 対象検索-09 に渡す", "本処理では台帳を書かない（書き込み箇所を 1 つに集約するため）"],
        ],
        exceptions=[
          ["openapi.yaml が無い", "対象検索-07 の出力", "スキップ（正常系）", "—", "17 §17.4 モノリス"],
          ["PutObject 失敗", "API 例外", "アプリ単位でスキップし台帳も更新しない（次回巡回で再試行）",
           "DiscoveryAccountErrors → MM-3 → P2", "18 §18.5.2"],
          ["仕様が巨大", "サイズ", "対象検索-07 のサイズ上限で既に弾かれている", "—", "M-Q-PD-6"],
        ],
        idem=(
          "同じ内容を何度 Put しても結果は同じ（バージョンは増えるが現行版の内容は同一）。",
          "台帳は更新しない。openApiS3Key の台帳反映は 対象検索-09 が行う。",
        ),
        authnote=["共通基盤アカウント内の書き込み。クロスアカウント権限は不要"],
        logs=[["アプリログ", "spec 配置", "appId / キー / サイズ / VersionId", "仕様本文は出力しない"]],
        perf=("変更のあったアプリのみ 1 回の PutObject。数十〜数百 KB", "S3 PUT 3,500 req/s（プレフィックス単位）"),
        opens=[],
      )),
    P("対象検索-11", "認証実装確認依頼", "認証実装確認依頼", "対象検索（1 時間毎）",
      "対象検索 Lambda", "認証実装チェック Lambda", "非同期", "対象検索 Lambda", "変更のあったアプリごと",
      "変更が確定したアプリを対象に認証実装の確認を依頼する（自動差分検査＝モード1）。",
      "lambda:InvokeFunction（InvocationType=Event）/ lambda.{region}.amazonaws.com",
      "対象検索 Lambda -> 認証実装チェック Lambda : Invoke(Event, {mode:'delta', appId, env})\n※ 依頼成功後に 対象検索-09 の版数を確定更新\n【シーケンス図の所在】17 §17.2.1 巡回シーケンス図（対象検索-01〜14 を通した図）/ 10 §10.1.7 F1",
      "非同期リトライ（2 回）と DLQ の設定、依頼失敗時に台帳を更新しないこと（at-least-once）を明記する",
      d=dict(
        position="巡回の出口。対象検索-09 / 対象検索-10 で台帳と仕様を整えたアプリ×環境ごとに、認証実装チェック Lambda へ検査を依頼する。"
                 "**依頼が成功して初めて lastArtifactVersions を確定更新する**（17 §17.2.1 ⑦）。",
        pre=[
          "対象検索-09 で台帳の設定値同期が完了（lastArtifactVersions はまだ旧値）",
          "対象検索-10 で API 仕様の複写が完了",
          "認証実装チェック Lambda に**非同期呼び出しの On-failure Destination（送信先 SQS）**が設定済み（WBS A5。2026-09-14 に DLQ から変更）",
          "台帳の enabled が true であること（false なら依頼しない）",
        ],
        inputs=[
          ["appId / env", "string", "○", "対象検索-08", "検査対象の単位"],
          ["更新後 ETag", "string", "○", "対象検索-09", "依頼成功後の版数確定更新で If-Match に使う"],
          ["現行版 VersionId", "map", "○", "対象検索-04", "確定更新で lastArtifactVersions に書き込む値"],
        ],
        outputs=[
          ["検査依頼", "非同期 Invoke", "認証実装チェック Lambda", "payload = {mode:'delta', appId, env}"],
          ["lastArtifactVersions の確定更新", "S3 PutObject（If-Match）", "配置バケット registry/{appId}/{env}.json", "**依頼成功後のみ**"],
          ["失敗時の呼び出し記録", "SQS メッセージ（JSON）", "検査 Lambda 用 On-failure Destination",
           "リトライ枯渇時のみ。requestContext（試行回数・エラー種別）/ requestPayload / responsePayload を含む。MM-4 の入力"],
        ],
        steps=[
          ["enabled=false のレコードは依頼しない（スキップ）", "中央が意図的に監視を止めているアプリ（12 章）"],
          ["**非同期（InvocationType=Event）**で認証実装チェック Lambda を invoke する",
           "同期にすると 1 アプリの検査失敗・長時間化が巡回全体を巻き込む（18 §18.5.2）。"
           "**非同期のペイロード上限は 1 MB**（同期の 6 MB とは別）。本 payload は数十バイトで問題にならない"],
          ["payload は {mode:'delta', appId, env} のみとする",
           "検査側は台帳と仕様を自分で読む。**対象検索側は差分の中身を渡さない**（17 §17.2.1 差分判定の原則③）。"
           "これにより検査 Lambda はモード1/モード2 で同一実装になる"],
          ["invoke 呼び出しが成功（202 受理）したら、**台帳の lastArtifactVersions を If-Match 付きで更新する**",
           "【注意】ここが at-least-once の要。受理＝実行成功ではないが、受理後は Lambda 側のリトライ（下記）に委ねる"],
          ["invoke が失敗したら台帳を更新せず、次回巡回で再検知させる",
           "版数が旧いままなので、1 時間後の巡回が同じ差分を再び検知して依頼し直す"],
          ["複数 env がある場合は env ごとに独立して依頼・確定更新する",
           "片方の env で失敗しても、もう片方は成功として記録される。**lastArtifactVersions を env ごとに持つ設計の狙い**（2026-09-14 確定）"],
        ],
        exceptions=[
          ["invoke がスロットリング（429）", "API 例外",
           "**AWS 仕様では 429 / 5xx はイベントがキューに戻り、最大 6 時間・指数バックオフ（最大 5 分間隔）で再試行される**。"
           "呼び出し側は受理されなかった場合のみ台帳を据え置く", "長期化すれば MM-4 → P2", "AWS 公式（invocation-async-error-handling）"],
          ["検査 Lambda が関数エラーで失敗", "Lambda 側",
           "**関数エラー（コード例外・タイムアウト）は既定 2 回リトライ（1 分後・2 分後）**。枯渇で On-failure Destination へ",
           "MM-4（Destination 滞留 ≥ 1）→ P2 Platform", "18 §18.5.1 / AWS 公式"],
          ["同じイベントが 2 回配信される", "Lambda 非同期キューの結果整合性",
           "**AWS 公式が「同じイベントが複数回届きうる」と明記**。検査は読み取り専用で冪等のため無害",
           "—", "18 §18.5.2"],
          ["台帳の確定更新で 412", "S3 応答",
           "再読込 → 版数のみ再適用 → 再試行。**検査依頼は再送しない**（すでに受理済みで、再送すると二重検査になる）",
           "上限超過で MM-3 → P2", "対象検索-09 / M-Q-PD-9"],
          ["invoke 成功 → 台帳更新失敗（上限超過）", "—",
           "版数が旧いまま残り、次回巡回で**同じアプリを再度検査依頼する**（重複検査。冪等なので無害）",
           "MM-3 → P2", "at-least-once の受容した代償"],
        ],
        idem=(
          "**at-least-once**。同じ差分に対して検査依頼が複数回飛びうるが、検査は読み取り専用で冪等のため無害（18 §18.5.2）。"
          "AWS 公式も非同期キューが結果整合性であり同一イベントが複数回届きうると明記している。",
          "**lastArtifactVersions の更新はここだけ**（対象検索-09 では更新しない）。"
          "「依頼が受理されたこと」を確認してから版数を進めることで、"
          "依頼できていないのに『確認済み』と記録される偽安心を防ぐ。",
        ),
        authnote=[
          "lambda:InvokeFunction（対象の関数 ARN に限定）。共通基盤アカウント内のため AssumeRole は不要",
          "台帳更新には s3:PutObject + s3:GetObject（If-Match のため）",
        ],
        logs=[
          ["アプリログ", "検査依頼", "appId / env / mode / invoke 結果 / 相関 ID", "巡回の相関 ID を payload に含めるかは M-Q-PD-10"],
          ["アプリログ", "版数確定更新", "appId / env / 旧版数 / 新版数 / 412 リトライ回数", "—"],
        ],
        perf=(
          "変更のあったアプリ × env 数。Phase 1 では 1 巡回あたり 0〜数回",
          "非同期ペイロード上限 1 MB（本用途では数十バイト）。"
          "**同時実行数の上限に当たると 429 → キュー再投入（最大 6 時間）**。アプリ数が増えたら予約同時実行の割り当てを検討",
        ),
        opens=[
          ["M-Q-PD-10", "巡回の相関 ID を検査依頼の payload に含め、検査側ログまで追跡できるようにするか。"
           "含めると「どの巡回が起こした検査か」を追えるが、payload に検査側が使わない項目が増える", "設計担当", ""],
          ["M-Q-PD-11", "【解決・2026-09-14】失敗の受け皿は **On-failure Destination（送信先は SQS）** を採用。"
           "DLQ はイベント本文とエラーメッセージ先頭 1KB しか残らないのに対し、Destination は"
           "**呼び出し記録（requestContext の試行回数・requestPayload・responsePayload）を JSON で残せる**ため障害調査が容易。"
           "18 §18.5.1/§18.5.2・WBS A5 を改訂済み。"
           "※ EventBridge Scheduler 側は Destination 非対応のため**従来どおり DLQ（SQS 標準キュー）**（対象検索-01）",
           "—（解決済み）", ""],
        ],
      )),
    P("対象検索-12", "構成情報不備通知", "構成情報不備通知", "対象検索（1 時間毎）",
      "対象検索 Lambda", "SNS（P2 Platform）", "同期", "対象検索 Lambda", "不備検出時",
      "認証構成情報の不備（appId 不一致・必須項目欠落・認証方式の値が不正など）を通知する。",
      "sns:Publish / sns.{region}.amazonaws.com",
      "対象検索 Lambda -> SNS(P2) : Publish（不備種別・appId・該当項目）\n【シーケンス図の所在】17 §17.2.1 巡回シーケンス図（対象検索-01〜14 を通した図）/ 10 §10.1.7 F1",
      "不備種別ごとの文面と、毎巡回で重複通知しない抑制方式を定義する",
      d=dict(
        position="対象検索-08 で不備を検出したアプリに対して実行する。アプリ側に「監視に入れていない / 精度が落ちている」ことを知らせる唯一の経路。",
        pre=[
          "対象検索-08 で不備リストを取得済み",
          "対象検索-09 で拒否レコード（lastRejectedVersions）を書き込み済み、または書き込み予定であること",
          "SNS トピック（P2 Platform）が作成済み・宛先 DL が確定済み（WBS A4 / W1-5）",
        ],
        inputs=[
          ["不備リスト", "[{種別, 該当項目, 重大度}]", "○", "対象検索-08", "取り込み拒否か既定値継続かの分類つき"],
          ["appId / env / accountId", "string", "○", "対象検索-04 / 08", "通知本文の識別子"],
          ["lastRejectedVersions", "map / null", "—", "対象検索-05", "**前回と同じ版なら通知しない**判定に使う"],
          ["通知先 ARN", "string", "○", "台帳 alertRouting.p2 または全社デフォルト", "未設定なら全社デフォルト（15 章）"],
        ],
        outputs=[
          ["メタ不足アラート", "SNS メッセージ", "SNS（P2 Platform）", "不備種別・appId・該当項目・対処方法"],
          ["通知済みマーク", "—", "対象検索-09（拒否レコードとして書く）", "同じ版での再通知を防ぐ"],
        ],
        steps=[
          ["**lastRejectedVersions が現行版数と一致する場合は通知しない**",
           "前回の巡回で同じ版を既に拒否・通知済み。毎時 24 通のアラートを防ぐ（2026-09-14 確定）。"
           "アプリが修正して再アップロードすれば版数が変わり、自動的に再通知される"],
          ["不備種別ごとに本文を組み立てる",
           "「何が悪いか」だけでなく「どう直すか」を書く。受け手はベンダーの可能性があり、設計書を読んでいない前提で書く"],
          ["取り込み拒否（監視に入っていない）と、既定値で継続（精度が落ちている）を**本文で明確に区別する**",
           "前者は『いま監視されていない』という重大な状態であり、後者と同じ扱いにしてはならない"],
          ["appId 不一致・baseUrl の許可ドメイン外は**重大度を上げて通知する**",
           "他アプリ領域への誤配置や、監視基盤を任意ドメインへ向けようとする操作の可能性があるため（対象検索-08）"],
          ["SNS へ Publish する", "宛先は台帳の alertRouting.p2。未設定なら全社デフォルト（15 章）"],
          ["Publish 失敗は記録して継続する（巡回は止めない）", "通知の失敗で巡回全体を止めない（18 §18.5.2）"],
        ],
        exceptions=[
          ["前回と同じ版の不備", "lastRejectedVersions と一致", "通知しない（抑制）", "—", "2026-09-14 確定"],
          ["不備が解消された（正常に取り込めた）", "対象検索-08 の判定",
           "**解消の通知は出さず**、台帳の拒否フィールドをクリアするのみ", "—", "M-Q-PD-12"],
          ["SNS Publish 失敗", "API 例外", "記録して継続", "MM-3 経由で顕在化", "18 §18.5.2"],
          ["alertRouting 未設定", "台帳値", "全社デフォルトへ送る", "—", "15 章"],
          ["同一アプリで複数の不備", "不備リスト", "1 通にまとめて送る（不備ごとに 1 通にしない）", "—", "アラート数の抑制"],
        ],
        idem=(
          "同じ版に対しては 1 回しか通知しない（lastRejectedVersions による抑制）。"
          "版数が変わるまでは何度巡回しても通知は増えない。",
          "本処理自体は台帳を更新しない。拒否レコードの書き込みは 対象検索-09 に集約している。",
        ),
        authnote=["sns:Publish（対象トピックに限定）。共通基盤アカウント内のため AssumeRole は不要"],
        logs=[
          ["アプリログ", "不備通知", "appId / env / 不備種別 / 通知可否（抑制されたか）/ 宛先 ARN のハッシュ", "**SNS ARN そのものは出力しない**"],
        ],
        perf=("不備のあるアプリ数分。正常時はゼロ", "SNS の無料枠 1,000 通/月（RC-11）。不備が放置されない限り枠内"),
        opens=[
          ["M-Q-PD-12", "不備が解消されたときに「解消しました」の通知を出すか。"
           "出さない場合、受け手は自分で直したことを自覚しているはずという前提に依存する", "運用設計（WBS W4-1）", ""],
          ["M-Q-15-1", "P2 の宛先 DL（受信チームのヒアリングで確定）", "Platform チーム", "調整中"],
        ],
      )),
    P("対象検索-13", "監視対象消滅検知", "監視対象消滅・鮮度低下検知", "対象検索（1 時間毎）",
      "対象検索 Lambda", "配置バケット（registry/）+ SNS（P2）", "同期", "対象検索 Lambda", "巡回ごとに 1 回",
      "認証構成情報の消滅（アプリ廃止の可能性）と、長期間更新されていない状態（鮮度低下）を検知する。",
      "s3:PutObject（enabled=false）/ sns:Publish",
      "対象検索 Lambda : 台帳あり かつ 構成情報なし -> enabled=false + 棚卸しアラート\n対象検索 Lambda : 最終更新が閾値超 -> 鮮度低下アラート\n【シーケンス図の所在】17 §17.2.1 巡回シーケンス図（対象検索-01〜14 を通した図）/ 10 §10.1.7 F1",
      "鮮度低下の閾値（仮 90 日、M-Q-17-3）と、一時的な取得失敗との区別を定義する",
      d=dict(
        position="**全アカウントの巡回が終わった後に 1 回だけ**実行する。台帳にあるのに連携バケットに無いアプリを洗い出す、巡回の締めの処理。",
        pre=[
          "全アカウントの 対象検索-03〜11 が完了していること",
          "**どのアカウントの巡回に成功したかの記録**（対象検索-03 / 04 の出力）があること",
        ],
        inputs=[
          ["巡回成功アカウント一覧", "[accountId]", "○", "対象検索-03 / 04",
           "【注意】**本処理の正しさの前提**。失敗したアカウントを含めると誤判定する"],
          ["発見済みアプリ一覧", "[{accountId, appId}]", "○", "対象検索-04", "今回の巡回で monitoring.yaml が確認できたアプリ"],
          ["台帳の全レコード", "[{appId, env, lastSeenAt, enabled, …}]", "○", "配置バケット registry/ の List + Get", "—"],
          ["鮮度低下の閾値", "days", "○", "実装定数 / SSM", "仮 90 日（M-Q-17-3）"],
        ],
        outputs=[
          ["enabled=false 更新", "S3 PutObject（If-Match）", "配置バケット registry/", "消滅と判定したレコード"],
          ["棚卸しアラート", "SNS メッセージ", "SNS（P2 Platform）", "消滅・鮮度低下の一覧（1 通にまとめる）"],
        ],
        steps=[
          ["【注意】**巡回に失敗したアカウントのアプリは、本処理の対象から必ず除外する**",
           "**本処理で最も重要な安全弁**。AssumeRole 失敗やバケット未作成で走査できなかったアカウントのアプリを"
           "『消滅した』と判定すると、生きているアプリの監視を一括で止めてしまう（18 §18.5.2 の部分失敗分離と対）"],
          ["台帳にあるが今回の巡回で発見されなかったアプリを抽出する",
           "巡回成功アカウントに属するレコードのみが対象"],
          ["対象検索-04 で **delete marker が現行版**だったキーは、消滅の一次シグナルとして扱う",
           "【注意】ListObjectsV2 では delete marker が現行のキーは返らないため消滅が判別できない。"
           "ListObjectVersions を使っているからこそ『削除された』と『元から無い』を区別できる（対象検索-04）"],
          ["消滅と判定したレコードを enabled=false に更新する（If-Match 付き）",
           "**レコード自体は削除しない**。誤判定時に戻せることと、いつ監視を外したかの履歴を残すため"],
          ["lastSeenAt が閾値（仮 90 日）を超えているレコードを**鮮度低下**として抽出する",
           "『デプロイしたのに認証構成情報を上げ忘れている』の補助検知（17 §17.2.2）。"
           "**責任分界は原則アプリ側**（M-Q-17-7）であり、本検知は中央の補助にとどまる"],
          ["消滅・鮮度低下をまとめて 1 通の棚卸しアラートとして通知する",
           "アプリごとに 1 通にすると通知が溢れる。月次棚卸し（M-Q-17-3）の入力にもなる"],
          ["巡回対象アカウントが 0 件だった場合は**本処理を実行しない**",
           "対象検索-02 で列挙に失敗している可能性があり、全アプリを一斉に消滅扱いにしかねない"],
        ],
        exceptions=[
          ["巡回に失敗したアカウントのアプリ", "巡回成功記録", "**消滅判定の対象から除外**", "—", "本処理の前提"],
          ["delete marker が現行版", "対象検索-04", "消滅と判定（enabled=false + 棚卸し通知）", "棚卸しアラート → P2", "17 §17.2.1"],
          ["台帳にあるが連携バケットに無い（delete marker も無い）", "突合",
           "消滅と判定。ただしバケットごと消えている場合はアカウント単位の失敗の可能性があるため、"
           "**1 アカウントで大量に消滅判定が出る場合は自動更新せず通知のみに留める**",
           "棚卸しアラート → P2（重大度を上げる）", "M-Q-PD-13"],
          ["鮮度低下（lastSeenAt が閾値超）", "日時比較",
           "**enabled は変えない**（監視は継続）。通知のみ", "棚卸しアラート → P2", "17 §17.2.2"],
          ["すでに enabled=false のレコード", "台帳値", "再通知しない", "—", "重複通知の抑制"],
          ["取り込み拒否レコード（enabled=false + lastRejectedVersions）", "台帳値",
           "消滅ではないため消滅判定の対象外。鮮度低下の判定のみ行う", "—", "対象検索-12 と役割を分ける"],
        ],
        idem=(
          "同じ巡回結果に対しては同じ判定になる。すでに enabled=false のレコードは再更新・再通知しない。",
          "enabled を false に落とす**唯一の自動処理**。true に戻すのは 対象検索-09（認証構成情報が再び置かれた場合）"
          "または運用者の手動更新（運用-03）。",
        ),
        authnote=["配置バケットへの s3:ListBucket / GetObject / PutObject（If-Match のため GetObject 必須）+ sns:Publish"],
        logs=[
          ["アプリログ", "消滅検知", "対象 appId / env / 判定理由（delete marker or 不在）/ 除外したアカウント数", "—"],
          ["アプリログ", "鮮度低下検知", "appId / lastSeenAt / 経過日数", "—"],
        ],
        perf=(
          "台帳の全件 List + Get。Phase 1 は数十レコード。将来 30 アプリ×2 env = 60 レコードでも 1 秒未満",
          "台帳が数千レコード規模になったら List のページングと並列 Get を検討（現時点では不要）",
        ),
        opens=[
          ["M-Q-17-3", "『認証構成情報が上がってくるはずなのに無い』の突合方法（契約リスト / タグ / Service Catalog の払い出し実績のどれと突合するか）と"
           "**鮮度低下の閾値**（仮 90 日）", "設計担当 + 運用", ""],
          ["M-Q-PD-13", "1 アカウントで大量の消滅判定が出た場合に自動で enabled=false にしてよいか。"
           "安全弁として『N 件以上 / 全体の X% 以上なら自動更新せず通知のみ』の閾値を設けるか", "設計担当", ""],
        ],
      )),
    P("対象検索-14", "巡回結果メトリクス送信", "巡回結果メトリクス送信", "対象検索（1 時間毎）",
      "対象検索 Lambda", "CloudWatch", "同期", "対象検索 Lambda", "巡回ごとに 1 回",
      "巡回の成功・失敗アカウント数などを、監視機構自身の稼働監視用メトリクスとして送信する。",
      "cloudwatch:PutMetricData / monitoring.{region}.amazonaws.com",
      "対象検索 Lambda -> CloudWatch : PutMetricData(DiscoveryLastSuccess, DiscoveryAccountErrors)\n【シーケンス図の所在】17 §17.2.1 巡回シーケンス図（対象検索-01〜14 を通した図）/ 10 §10.1.7 F1",
      "メトリクス名・ディメンション・欠損時の扱い（MM-1 は 2h 欠損で発報）を明記する",
      d=dict(
        position="巡回の最終処理。**「巡回が動いていること」を外から観測できる唯一の信号**を出す。"
                 "これが止まることが MM-1（監視の空白）の検知トリガーになる。",
        pre=["対象検索-02〜13 が完了していること（一部アカウントの失敗は許容）"],
        inputs=[
          ["巡回結果サマリ", "{成功アカウント数, 失敗アカウント数, 発見アプリ数, 検査依頼数, 不備数}", "○", "対象検索-02〜13", "—"],
        ],
        outputs=[
          ["DiscoveryLastSuccess", "Count=1", "CloudWatch（共通基盤）", "**巡回が完走したこと**を示すハートビート。MM-1 の入力"],
          ["DiscoveryAccountErrors", "Count=N", "CloudWatch（共通基盤）", "巡回に失敗したアカウント数。MM-3 の入力"],
        ],
        steps=[
          ["巡回が完走したら DiscoveryLastSuccess = 1 を PutMetricData する",
           "【注意】**一部アカウントが失敗していても、巡回自体が完走したなら 1 を出す**。"
           "部分失敗は DiscoveryAccountErrors（MM-3）が受け持ち、MM-1 は『巡回そのものが動いていない』ことだけを見る。役割を混ぜない"],
          ["失敗アカウント数を DiscoveryAccountErrors として PutMetricData する",
           "0 件でも 0 を出す。**値を出さないと欠損と区別できない**"],
          ["ディメンションは最小限にする",
           "【注意】メトリクスはディメンションの組合せごとに課金される（RC-7 が最大費目）。"
           "アプリ単位のディメンションを付けるとアプリ数比例でコストが増える。巡回メトリクスはアプリ次元を持たせない"],
          ["PutMetricData の失敗は記録して握り潰す（巡回は成功扱いのまま）",
           "メトリクス送信の失敗で巡回結果を覆さない。ただし送信できないと MM-1 が誤発報する点は認識しておく"],
        ],
        exceptions=[
          ["巡回が異常終了（例外で落ちた）", "—",
           "DiscoveryLastSuccess を出さない → 2 時間欠損で MM-1 発報", "MM-1 → P2 Platform", "18 §18.5.1"],
          ["一部アカウントが失敗", "対象検索-03 / 04",
           "DiscoveryLastSuccess は 1、DiscoveryAccountErrors は N", "MM-3 → P2 Platform", "18 §18.5.1"],
          ["PutMetricData 失敗", "API 例外",
           "記録して継続（巡回は成功扱い）", "結果として MM-1 が誤発報しうる", "M-Q-PD-2"],
          ["メトリクス配信の遅延・欠落", "CloudWatch 側",
           "【注意】**AWS 公式が「メトリクスは best-effort で配信され、完全性・即時性は保証されない」と明記**。"
           "MM-1 の閾値設計で考慮する", "誤発報の可能性", "M-Q-PD-2"],
        ],
        idem=(
          "同じ巡回で複数回送っても、CloudWatch 側は同一タイムスタンプの値として扱う。実害はないが 1 回に留める。",
          "台帳等の状態は更新しない。",
        ),
        authnote=["cloudwatch:PutMetricData。共通基盤アカウント内のため AssumeRole は不要"],
        logs=[
          ["アプリログ", "巡回完了サマリ", "成功/失敗アカウント数・発見アプリ数・検査依頼数・不備数・総所要 ms", "運用ダッシュボードの元データ（WBS W4-3）"],
          ["メトリクス", "DiscoveryLastSuccess / DiscoveryAccountErrors", "上記", "名前空間・ディメンションは監視設計書（WBS B0-d）で確定"],
        ],
        perf=(
          "1 巡回あたり 1〜2 回の PutMetricData。カスタムメトリクス 2 種で月 $0.6（RC-7 の一部）",
          "**PutMetricData は 1 リクエスト 1 MB / 1,000 メトリクス / 1 メトリクスあたり 150 値 / 30 ディメンションまで**。"
          "本用途では上限に当たらない。API レートは 500 req/s",
        ),
        opens=[
          ["M-Q-PD-2", "【解決・2026-09-14】MM-1 の閾値は **2 時間欠損 → 6 時間欠損に緩和**。"
           "AWS 公式がメトリクスの best-effort 配信と『メトリクス停止後にアラームが直近データ点を再評価し続ける』挙動を警告しているため、"
           "短い閾値は誤発報を招く。**検知の遅れは許容する**（本番と開発が同一構成なら本番リリース前に開発側で拾える）。"
           "実装値は評価期間 6 時間 / TreatMissingData=breaching を初期値とし、運用実績で調整",
           "設計担当（WBS B3-i と連動）", ""],
          ["M-Q-PD-14", "巡回メトリクスにアプリ単位のディメンションを持たせないこと（コスト起因）の確認。"
           "アプリ別の巡回状況を見たい要望が出た場合はログ（CloudWatch Logs Insights）で代替する", "設計担当", ""],
        ],
      )),

    # ---------------- 全量確認
    P("全量-01", "全量確認処理開始（定期）", "全量確認処理開始（定期）", "全量（日次）",
      "EventBridge Scheduler（日次）", "認証実装チェック Lambda", "非同期", "EventBridge Scheduler", "日次",
      "認証構成情報の変化に関係なく全アプリを確認するため、全量確認を定期起動する。",
      "Scheduler 実行ロール / lambda:InvokeFunction",
      "EventBridge Scheduler -> 認証実装チェック Lambda : Invoke(Event, {mode:'full'})\n【シーケンス図の所在】18 §18.1 実行モード図・§18.3 / 10 §10.1.7 F2",
      "実行時刻帯（M-Q-18-3）と、巡回（対象検索-01）と時間帯が重ならない配慮を明記する",
      d=dict(
        position="全量確認の起点（定期側）。ここから 全量-03（対象一覧取得）→ 全量-04（fan-out）→ 認証実装チェック-01〜08 が動く。"
                 "認証構成情報に変化がなくても動く**唯一の経路**であり、コンソール直変更のような資材に現れない変化を最大 24 時間で捕捉する（18 §18.1.1）。",
        pre=[
          "日次 EventBridge Scheduler・実行ロールが作成済み（WBS A15-i）",
          "Scheduler 用 DLQ（SQS 標準キュー）が作成済み。**EventBridge Scheduler は On-failure Destination に非対応**のため、"
          "Lambda 側（全量-04 / 認証実装チェック）とは異なり DLQ を使う（2026-09-14 確定）",
          "巡回（対象検索-01）の実行時間帯と重ならないこと",
        ],
        inputs=[
          ["スケジュール式", "cron", "要", "Scheduler 定義（IaC）",
           "**cron は 6 フィールド必須**（分 時 日 月 曜 年）。日と曜の両方に * は指定できず、片方は ? にする"],
          ["ScheduleExpressionTimezone", "IANA TZ", "要", "同上",
           "JST 運用なら Asia/Tokyo を明示する。未指定だと UTC 解釈になり、意図した時間帯からずれる"],
          ["FlexibleTimeWindow", "OFF", "要", "同上",
           "**Mode は指定必須**。本設計は **OFF で確定**（2026-09-15）。FLEXIBLE の効果は「起動の分散によるスロットリング回避」だが、"
           "本設計はスケジュールが 2 本（巡回・全量）しかなく集中しないため効果がない。"
           "OFF なら『毎日 X 時に走る』と運用に説明でき、障害調査時も実行時刻が読める（起動精度は 60 秒）"],
          ["target payload", "JSON", "要", "同上", '{"mode":"full"} のみ。対象の決定は 全量-03 が台帳から行う'],
          ["RetryPolicy / DeadLetterConfig", "object", "要", "同上", "対象検索-01 と同じ方針（M-Q-PD-1 で実装値を確定）"],
        ],
        outputs=[
          ["認証実装チェック Lambda の起動", "非同期 Invoke", "認証実装チェック Lambda", "payload = {mode:'full'}"],
          ["AWS/Scheduler メトリクス", "CloudWatch", "共通基盤アカウント", "InvocationAttemptCount / TargetErrorCount / InvocationDroppedCount ほか"],
        ],
        steps=[
          ["日次 cron で起動する", "起動精度は 60 秒。FLEXIBLE を設定した場合はウィンドウ内で分散される"],
          ["巡回（毎正時付近）と重ならない時刻帯を選ぶ",
           "同時に走ると台帳への書き込み（対象検索-09）と読み取り（全量-03）が交錯し、"
           "巡回の途中状態を全量が読む可能性がある。実害は小さいが避けられる競合は避ける（実行時刻帯は M-Q-18-3）"],
          ["payload {\"mode\":\"full\"} を渡して認証実装チェック Lambda を起動する",
           "**手動起動（全量-02）と payload が同一**であり、実装上の分岐はない。トリガが Scheduler か人かだけの違い（18 §18.3）"],
          ["起動失敗は RetryPolicy に従い再試行し、枯渇したら DLQ へ配信する", "Scheduler は Destination 非対応のため DLQ（SQS 標準キュー）"],
        ],
        exceptions=[
          ["前日の全量確認がまだ終わっていない", "Lambda の同時実行",
           "二重に走るが、検査は読み取り専用で冪等のため無害。ただし同時実行数とメトリクスを二重消費する",
           "長時間化が続くなら Duration アラームで顕在化", "18 §18.5.3 / M-Q-PD-16"],
          ["認証実装チェック Lambda のスロットリング", "TargetErrorThrottledCount",
           "RetryPolicy に従い再試行", "リトライ成功なら通知なし", "§10 上限・制約"],
          ["リトライ枯渇", "InvocationDroppedCount / InvocationsSentToDeadLetterCount",
           "DLQ へ退避（運用-02 で再処理）", "MM-2 → P2 Platform", "18 §18.5.1"],
          ["全量確認が丸ごと動かない（スケジュール無効化等）", "FullScanLastSuccess の 48 時間欠損（MM-6）",
           "—（検知のみ）", "MM-6 → P2 Platform", "全量-05 / 18 §18.5.1"],
        ],
        idem=(
          "同じ日に複数回起動しても、検査は読み取り専用で冪等のため結果は変わらない（18 §18.5.2）。",
          "本処理は状態を持たない。台帳の更新も行わない（全量確認は**読むだけ**で、台帳を書くのは巡回の責務）。",
        ),
        authnote=[
          "Scheduler 実行ロールの信頼ポリシーは aws:SourceAccount + aws:SourceArn（**スケジュールグループ単位**）を条件に付ける",
          "権限は lambda:InvokeFunction（対象関数に限定）+ sqs:SendMessage（DLQ に限定）",
        ],
        logs=[
          ["アプリログ", "全量確認開始（定期）", "実行 ID / 起動時刻 / トリガ種別=scheduled", "手動起動と区別できるようトリガ種別を記録する"],
          ["メトリクス", "AWS/Scheduler（標準）", "上記", "ディメンション ScheduleGroup"],
        ],
        perf=(
          "1 日 1 回 = 約 30 回/月。Scheduler の無料枠内で費用は実質ゼロ（RC-4）",
          "起動精度 60 秒 / FLEXIBLE 指定時は最大 1440 分までウィンドウ設定可 / 単一スケジュールへの操作は 10 TPS",
        ),
        opens=[
          ["M-Q-18-3", "全量確認の実行時刻帯（巡回と重ならない時間）と、手動実行の権限範囲", "運用 / 設計担当", ""],
          ["M-Q-PD-15", "【解決・2026-09-15】**OFF で確定**。FLEXIBLE の効果（起動の分散によるスロットリング回避）は"
           "スケジュールが 2 本しかない本設計では得られず、実行時刻が読めなくなる不利益の方が大きいため",
           "—（解決済み）", ""],
          ["M-Q-PD-17", "【解決・2026-09-15】全量確認の停止検知を **MM-6** として新設。"
           "**全量-05 が FullScanLastSuccess を emit し、48 時間欠損で発報**（日次実行に対し 2 回分の余裕）。"
           "18 §18.5.1 / WBS B10-i・B1-i に反映済み", "—（解決済み）", ""],
        ],
      )),
    P("全量-02", "全量確認処理開始（手動）", "全量確認処理開始（手動）", "全量（手動・随時）",
      "運用者（CLI / コンソール）", "認証実装チェック Lambda", "非同期", "運用者", "随時（監査前・障害後など）",
      "運用者の判断で全量確認を実行する。実装は定期起動と同一で、起動元が人である点だけが異なる。",
      "lambda:InvokeFunction（実行者の IAM）",
      "運用者 -> 認証実装チェック Lambda : Invoke(Event, {mode:'full'})\n※ 特定アプリのみ: {mode:'full', appId, env}\n【シーケンス図の所在】18 §18.1 実行モード図・§18.3 / 10 §10.1.7 F2",
      "実行権限を持つ者の範囲（共通基盤チームのみか、アプリチームも可か。M-Q-18-3）を確定する",
      d=dict(
        position="全量確認の起点（手動側）。**実装は 全量-01（定期）と完全に同一**で、起動元が人である点だけが異なる（18 §18.3）。",
        pre=[
          "実行者が lambda:InvokeFunction の権限を持つこと（範囲は M-Q-18-3）",
          "Runbook「全量確認の手動実行手順」が整備されていること（WBS W4-1 ②）",
        ],
        inputs=[
          ["payload", "JSON", "要", "実行者",
           '全件: {"mode":"full"} / 特定アプリのみ: {"mode":"full","appId":"…","env":"…"}'],
          ["実行理由", "—", "—", "実行者",
           "監査前 / 大きな変更後 / インシデント後など。**payload には含めず、Runbook の実施記録に残す**"],
        ],
        outputs=[
          ["認証実装チェック Lambda の起動", "非同期 Invoke", "認証実装チェック Lambda", "定期起動と同一 payload"],
          ["実行の監査証跡", "CloudTrail", "共通基盤アカウント", "**誰がいつ実行したか**。手動操作の追跡はここに依存する"],
        ],
        steps=[
          ["**非同期（InvocationType=Event）で invoke する**",
           "同期にすると全量確認の完了まで応答を待つことになり、CLI 側がタイムアウトする。"
           "また同期呼び出しの応答上限 6MB に対して結果が大きくなりうる"],
          ["appId / env を指定した場合は **全量-04 の fan-out を行わず、その 1 アプリだけを検査する**",
           "対象が 1 件しかない状態で自己 invoke するのは無駄な往復になるため。"
           "**この分岐は 全量-03 で対象を 1 件に絞ることで自然に実現する**（実装上の特別扱いを増やさない）"],
          ["実行者・日時・理由を Runbook の実施記録に残す",
           "payload に理由を入れても検査側は使わない。運用記録として別に残す方が確実（W4-1 ②）"],
          ["定期実行と同時刻に重ならないよう配慮する", "重なっても無害だが、同時実行数とメトリクスを二重消費する"],
        ],
        exceptions=[
          ["権限不足", "AccessDenied", "実行できない（正常な拒否）", "—", "M-Q-18-3"],
          ["同期 invoke してしまった", "CLI タイムアウト",
           "Lambda 側は実行を継続する（呼び出し側が切れただけ）。結果はメトリクスと通知で確認する",
           "—", "Runbook に非同期指定を明記（W4-1 ②）"],
          ["定期実行と同時に走った", "Lambda の同時実行", "二重に検査されるが冪等のため無害",
           "—", "18 §18.5.2"],
          ["誤って連続実行した", "—",
           "検査は読み取り専用のため実害はないが、対象アプリへ短時間に複数回の検査リクエストが飛ぶ。"
           "**WAF のレートベースルールに抵触する可能性**があるため Runbook で注意喚起する",
           "WAF ブロックは認証実装チェック-06 で WARN に分類", "11 §11.2.4"],
        ],
        idem=(
          "何度実行しても検査結果は変わらない（読み取り専用）。ただし短時間の連続実行は対象アプリへの負荷になるため運用上は避ける。",
          "状態を更新しない。",
        ),
        authnote=[
          "実行者の IAM に lambda:InvokeFunction（対象関数に限定）。**実行の記録は CloudTrail に依存する**ため、"
          "共通基盤アカウントの CloudTrail が有効であることが前提",
          "実行権限を広く配ると「誰でも本番へ検査リクエストを流せる」状態になるため、範囲は明示的に決める（M-Q-18-3）",
        ],
        logs=[
          ["アプリログ", "全量確認開始（手動）", "実行 ID / トリガ種別=manual / appId・env 指定の有無", "定期起動と区別できるようにする"],
          ["監査ログ", "CloudTrail Invoke", "実行者の ARN / 時刻 / 関数名", "手動操作の追跡"],
        ],
        perf=("随時。頻度は運用次第（監査前・障害後など）", "定期実行と同じ経路のため上限も同じ"),
        opens=[
          ["M-Q-18-3", "手動実行の権限範囲（共通基盤チームのみか、アプリチームが自アプリを実行できるか）。"
           "後者を許す場合は appId を自分のアプリに限定する仕組みが要る", "運用 / セキュリティ", ""],
        ],
      )),
    P("全量-03", "監視対象一覧取得", "監視対象一覧取得", "全量（日次・手動）",
      "認証実装チェック Lambda", "認証構成情報配置バケット（registry/）", "同期", "認証実装チェック Lambda", "全量確認ごとに 1 回",
      "台帳を全件読み出し、監視有効な対象アプリの一覧を得る。",
      "s3:ListBucket / s3:GetObject",
      "認証実装チェック Lambda -> 配置バケット : List(registry/) -> GetObject（各件）\n配置バケット --> 認証実装チェック Lambda : 台帳 JSON 群\n【シーケンス図の所在】18 §18.1 実行モード図・§18.3 / 10 §10.1.7 F2",
      "enabled=false のレコードを除外すること、List のページングを明記する",
      d=dict(
        position="mode=full の本体の入口。全量-01 / 全量-02 のどちらから起動されても同じ処理を行い、検査対象の一覧を作る。",
        pre=["台帳（registry/）が存在すること", "配置バケットへの s3:ListBucket / GetObject 権限があること"],
        inputs=[
          ["registry/ プレフィックス", "S3 キー", "要", "規約", "registry/{appId}/{env}.json"],
          ["appId / env", "string", "—", "payload（全量-02 の手動指定時のみ）", "指定時は対象を 1 件に絞る"],
        ],
        outputs=[
          ["検査対象リスト", "[{appId, env}]", "全量-04（メモリ内）", "enabled=true のレコードのみ"],
          ["除外件数", "number", "ログ", "enabled=false で除外した件数。監視されていないアプリ数の把握に使う"],
        ],
        steps=[
          ["registry/ プレフィックスを List する。**1 リクエスト最大 1,000 キー**のためページングする",
           "ContinuationToken で繰り返す。Phase 1 は数十件で 1 ページに収まる"],
          ["各レコードを GetObject して enabled を確認する", "—"],
          ["**enabled=false のレコードを除外する**",
           "中央が意図的に監視を止めたアプリと、**不備で取り込みを拒否したアプリ（拒否レコード）**の両方が除外される。"
           "後者は enabled=false + lastRejectedVersions を持つ（対象検索-09）"],
          ["appId / env の指定があればその 1 件に絞る",
           "手動での部分実行（全量-02）。**ここで絞ることで 全量-04 の fan-out が自然に 1 件になり、実装上の分岐を増やさずに済む**"],
          ["対象が 0 件なら異常として通知し、以降を実行しない",
           "台帳が空 = 監視対象ゼロは通常あり得ない。権限不足や台帳の消失を黙って正常終了させない"],
          ["【重要】全量確認は**台帳と API 仕様に載っている endpoint しか見ない**",
           "認証構成情報のアップロード忘れがあると、新設した endpoint は台帳にも仕様にも現れないため検査対象に入らない。"
           "これは全量確認でも埋められない穴であり、責任分界（原則アプリ責任、M-Q-17-7）と staleness 検知（対象検索-13）で受ける（17 §17.2.2）"],
        ],
        exceptions=[
          ["List 失敗（AccessDenied 等）", "API 例外", "全量確認を中断する", "MM-4 → P2 Platform", "18 §18.5.1"],
          ["一部レコードの Get 失敗", "API 例外", "その 1 件を落として継続（他のアプリは検査する）",
           "件数をログに残し、多発時は MM-4 で顕在化", "18 §18.5.2"],
          ["レコードの JSON が壊れている", "パース例外", "その 1 件を落として継続", "同上", "M-Q-PD-5"],
          ["対象 0 件", "件数", "中断して通知", "MM-4 → P2 Platform", "—"],
          ["enabled=false が大半を占める", "件数",
           "検査は実施するが、**除外件数をログに残して棚卸しの材料にする**", "—", "対象検索-13 の棚卸しと連動"],
        ],
        idem=("読み取りのみで副作用なし。同じ台帳なら常に同じ対象リストが得られる。", "状態を更新しない。"),
        authnote=["共通基盤アカウント内の読み取り。クロスアカウント権限は不要"],
        logs=[
          ["アプリログ", "対象一覧取得", "総レコード数 / 対象件数 / enabled=false 除外件数 / ページ数", "—"],
        ],
        perf=(
          "Phase 1 は数十レコード（3 アプリ × 2 環境）。将来 30 アプリ × 2 環境 = 60 レコードでも 1 ページ・1 秒未満",
          "S3 List は 1 リクエスト最大 1,000 キー。数千レコード規模になったら並列 Get を検討（現時点では不要）",
        ),
        opens=[],
      )),
    P("全量-04", "アプリ単位確認依頼", "アプリ単位確認依頼（fan-out）", "全量（日次・手動）",
      "認証実装チェック Lambda", "認証実装チェック Lambda（自身）", "非同期", "認証実装チェック Lambda", "対象アプリ数分",
      "全量確認を「1 実行 = 1 アプリ」に分割し、Lambda の実行時間上限に構造的に当たらないようにする。",
      "lambda:InvokeFunction（自身）/ lambda.{region}.amazonaws.com",
      "認証実装チェック Lambda(mode=full) -> 認証実装チェック Lambda(1 アプリ分) : アプリ数分 Invoke(Event)\n【シーケンス図の所在】18 §18.1 実行モード図・§18.3 / 10 §10.1.7 F2",
      "同時実行数の上限・スロットリング時の扱いを明記する",
      d=dict(
        position="全量確認の出口。対象アプリごとに**自分自身を非同期で呼び直し**、「1 実行 = 1 アプリ」に分割する。"
                 "これにより全量を 1 実行に詰め込まずに済み、アプリ数が増えても Lambda の 15 分制限に構造的に当たらない（18 §18.5.3）。",
        pre=[
          "全量-03 で検査対象リストを取得済み",
          "認証実装チェック Lambda に On-failure Destination（送信先 SQS）が設定済み（WBS A5）",
        ],
        inputs=[
          ["検査対象リスト", "[{appId, env}]", "要", "全量-03", "enabled=true のみ"],
        ],
        outputs=[
          ["子の起動", "非同期 Invoke（自分自身）", "認証実装チェック Lambda", "payload = {mode:'delta', appId, env, origin:'full'}"],
          ["invoke 失敗件数", "number", "ログ / メトリクス", "1 件の失敗で全量を止めないため、件数として集計する"],
        ],
        steps=[
          ["対象ごとに**自分自身を非同期（InvocationType=Event）で invoke する**",
           "1 実行 = 1 アプリ。親は検査そのものを行わず、割り振りに徹する（責務分離）"],
          ["**同時に走らせる子の数を 10 件までに制限する**（2026-09-15 確定）",
           "対象が 10 件を超える場合は 10 件ずつに区切って invoke する。"
           "同時実行数を一気に消費して巡回起点の検査（対象検索-11）を圧迫するのを防ぐ。"
           "Phase 1 の規模（3 アプリ × 2 環境 = 6 件）では実質的に制限に当たらず、将来 30 アプリでも 6 バッチで収まる"],
          ["payload に **origin:'full'** を付けて起点を記録する",
           "検査側は origin を判定に使わず**ログにだけ出す**。これにより『巡回起点の検査』と『全量起点の検査』を"
           "後からログで区別できる。判定ロジックを分岐させないことで、モード1/モード2 で同一実装という原則を保つ"],
          ["【重要】**Lambda の再帰ループ検出に抵触しないことを確認する**",
           "AWS は同一リクエストチェーン内で約 16 回の呼び出しを検出すると次の起動を自動停止する（既定 ON・無料・X-Ray のトレースヘッダで計数）。"
           "本設計のチェーンは**親（mode=full）→ 子（1 アプリ）の深さ 2 で終わり**、子はさらに自分自身を呼ばないため閾値に達しない。"
           "ただし将来 fan-out を多段化する場合は要注意。停止された場合は RecursiveInvocationsDropped メトリクスに現れる"],
          ["invoke の失敗は記録して次の対象へ進む",
           "1 アプリの起動失敗で全量確認を止めない（18 §18.5.2）"],
          ["親は子の完了を待たない",
           "非同期のため即座に返る。結果はメトリクス（認証実装チェック-07）と通知（認証実装チェック-08）で収束する"],
          ["全対象の invoke が終わったら親は終了する", "親自身は検査結果を集計しない（集計はメトリクス側の役割）"],
        ],
        exceptions=[
          ["同時実行数の上限に当たる（429）", "API 例外",
           "**AWS 仕様では 429 / 5xx はイベントがキューに戻り、最大 6 時間・指数バックオフ（最大 5 分間隔）で再試行される**。"
           "呼び出し側は受理されなかった分のみ失敗として記録する",
           "長期化すれば MM-4 → P2 Platform", "AWS 公式（invocation-async-error-handling）"],
          ["子が関数エラーで失敗", "Lambda 側",
           "既定 2 回リトライ（1 分後・2 分後）。枯渇で On-failure Destination へ",
           "MM-4（Destination 滞留 ≥ 1）→ P2 Platform", "18 §18.5.1"],
          ["再帰ループ検出で停止された", "RecursiveInvocationsDropped メトリクス",
           "**本設計では発生しない想定**（深さ 2）。発生したら多段 fan-out の混入を疑う",
           "MM-4 相当として P2 Platform", "AWS 公式（invocation-recursion）"],
          ["同一アプリが巡回起点の検査と重なる", "—",
           "二重に検査されるが読み取り専用のため無害。origin でログ上は区別できる", "—", "18 §18.5.2"],
          ["対象が 1 件のみ（手動の部分実行）", "全量-03 の出力",
           "1 回だけ invoke する（特別扱いはしない）", "—", "全量-02"],
        ],
        idem=(
          "**at-least-once**。同じアプリへ複数回の検査依頼が飛びうるが、検査は読み取り専用で冪等のため無害。"
          "AWS 公式も非同期キューが結果整合性であり同一イベントが複数回届きうると明記している（18 §18.5.2）。",
          "状態を更新しない。**全量確認は台帳を書かない**（台帳を書くのは巡回の責務）。"
          "したがって lastArtifactVersions は全量確認では変化せず、巡回の差分判定に影響を与えない。",
        ),
        authnote=[
          "lambda:InvokeFunction（**自分自身の関数 ARN**）。共通基盤アカウント内のため AssumeRole は不要",
          "非同期のペイロード上限は 1 MB（同期の 6 MB とは別）。本 payload は数十バイトで問題にならない",
        ],
        logs=[
          ["アプリログ", "fan-out 実行", "対象件数 / invoke 成功件数 / 失敗件数 / 所要 ms", "—"],
          ["アプリログ", "子の起動", "appId / env / origin=full / 相関 ID", "親の実行 ID を引き回して親子を紐づける"],
        ],
        perf=(
          "対象アプリ数 × 1 invoke。Phase 1 は 6 件（3 アプリ × 2 環境）、将来 30 アプリでも 60 件で数秒",
          "**同時実行は 10 件までに制限する**（2026-09-15 確定）。既定の同時実行数 1,000 に対して十分小さく、"
          "巡回起点の検査（対象検索-11）と競合しない。アプリ単位の並列は別ドメインへのアクセスのため 1 アプリに負荷は集中しない。"
          "Lambda のスケーリングは 1 関数あたり 10 秒で 1,000 実行環境まで",
        ),
        opens=[
          ["M-Q-PD-18", "【解決・2026-09-15】**同時実行の上限を 10 件**とする。"
           "10 件ずつのバッチで invoke し、巡回起点の検査を圧迫しないようにする。"
           "アプリ数の見込み（数〜30 程度）に対して十分で、Phase 1 では制限に当たらない", "—（解決済み）", ""],
          ["M-Q-PD-19", "payload に origin を追加することの確認（検査側は判定に使わずログ出力のみ）。"
           "code-samples/README §2 のイベント形式に追記が必要", "設計担当", ""],
        ],
      )),

    P("全量-05", "全量確認結果メトリクス送信", "全量確認結果メトリクス送信", "全量（日次・手動）",
      "認証実装チェック Lambda", "CloudWatch", "同期", "認証実装チェック Lambda", "全量確認ごとに 1 回",
      "全量確認の fan-out が完了したことを示すハートビートを送信する。これが止まることが MM-6（全量確認の停止）の検知トリガーになる。",
      "cloudwatch:PutMetricData / monitoring.{region}.amazonaws.com",
      "認証実装チェック Lambda -> CloudWatch : PutMetricData(FullScanLastSuccess, FullScanTargets, FullScanInvokeErrors)"
      "\n【シーケンス図の所在】18 §18.1 実行モード図・§18.3 / 10 §10.1.7 F2",
      "メトリクス名・欠損時の扱い（MM-6 は 48 時間欠損で発報）を明記する",
      d=dict(
        position="全量確認の最終処理（親側）。**巡回における 対象検索-14 と対になる**。"
                 "子（1 アプリの検査）の結果は 認証実装チェック-07 が別途メトリクス化するため、本処理は「親が完走したか」だけを扱う。",
        pre=["全量-03 / 全量-04 が完了していること（一部アプリの invoke 失敗は許容）"],
        inputs=[
          ["全量確認サマリ", "{対象件数, invoke 成功件数, invoke 失敗件数, 除外件数}", "要", "全量-03 / 全量-04", "—"],
        ],
        outputs=[
          ["FullScanLastSuccess", "Count=1", "CloudWatch（共通基盤）",
           "**全量確認が完走したこと**を示すハートビート。MM-6 の入力（2026-09-15 新設）"],
          ["FullScanTargets", "Count=N", "CloudWatch（共通基盤）", "検査対象としたアプリ×環境の件数。増減の傾向把握に使う"],
          ["FullScanInvokeErrors", "Count=N", "CloudWatch（共通基盤）", "fan-out の invoke に失敗した件数"],
        ],
        steps=[
          ["fan-out が完了したら FullScanLastSuccess = 1 を PutMetricData する",
           "【重要】**「子の検査が終わったこと」ではなく「親が割り振りを終えたこと」を示す**。"
           "親は非同期のため子の完了を待たない（全量-04）。子の失敗は MM-4 が別に受け持つ"],
          ["一部アプリの invoke に失敗していても FullScanLastSuccess は 1 を出す",
           "対象検索-14 と同じ考え方。部分失敗は FullScanInvokeErrors（および MM-4）が受け持ち、"
           "MM-6 は『全量確認そのものが動いていない』ことだけを見る。役割を混ぜない"],
          ["対象件数・invoke 失敗件数もあわせて送信する", "0 件でも 0 を出す。値を出さないと欠損と区別できない"],
          ["ディメンションは最小限にする",
           "メトリクスはディメンションの組合せごとに課金される（RC-7 が最大費目）。アプリ次元は持たせない"],
          ["PutMetricData の失敗は記録して握り潰す", "メトリクス送信の失敗で全量確認の結果を覆さない"],
        ],
        exceptions=[
          ["全量確認が異常終了（例外で落ちた）", "—",
           "FullScanLastSuccess を出さない → 48 時間欠損で MM-6 発報", "MM-6 → P2 Platform", "18 §18.5.1"],
          ["対象 0 件で中断した（全量-03）", "—",
           "**FullScanLastSuccess を出さない**（完走していないため）", "MM-4 → P2 + 48 時間後に MM-6", "全量-03"],
          ["一部の invoke に失敗", "全量-04",
           "FullScanLastSuccess は 1、FullScanInvokeErrors は N", "MM-4 → P2 Platform", "18 §18.5.1"],
          ["PutMetricData 失敗", "API 例外", "記録して継続", "結果として MM-6 が誤発報しうる",
           "48 時間の猶予があるため、単発の失敗では発報に至らない"],
        ],
        idem=("同じ全量確認で複数回送っても CloudWatch 側は同一タイムスタンプの値として扱う。実害はないが 1 回に留める。",
              "状態を更新しない。**全量確認は台帳を書かない**（書くのは巡回の責務）。"),
        authnote=["cloudwatch:PutMetricData。共通基盤アカウント内のため AssumeRole は不要"],
        logs=[
          ["アプリログ", "全量確認完了サマリ", "対象件数 / invoke 成功・失敗件数 / 除外件数 / 総所要 ms / トリガ種別", "運用ダッシュボードの元データ（WBS W4-3）"],
          ["メトリクス", "FullScanLastSuccess / FullScanTargets / FullScanInvokeErrors", "上記", "名前空間・ディメンションは監視設計書（WBS B0-d）で確定"],
        ],
        perf=("1 日 1 回（+手動実行分）。カスタムメトリクス 3 種で月 $1 未満（RC-7 の一部）",
              "PutMetricData は 1 リクエスト 1 MB / 1,000 メトリクス / 30 ディメンションまで。本用途では上限に当たらない"),
        opens=[],
      )),

    # ---------------- 認証実装チェック（1 アプリ・対象検索/全量 共通）
    P("認証実装チェック-01", "認証構成情報参照", "認証構成情報参照", "共通（対象検索・全量とも）",
      "認証実装チェック Lambda", "認証構成情報配置バケット（registry/）", "同期", "認証実装チェック Lambda", "アプリごとに 1 回",
      "確認対象アプリの設定値（検査先 URL・認証方式・トークン設定）を台帳から取得する。",
      "s3:GetObject",
      "認証実装チェック Lambda -> 配置バケット : GetObject(registry/{appId}/{env}.json)\n配置バケット --> 認証実装チェック Lambda : 台帳 JSON\n【シーケンス図の所在】11 §11.1 検査実行シーケンス / 10 §10.1.7 F2",
      "台帳が取得できない場合（削除・権限不足）の扱いを明記する"),
    P("認証実装チェック-02", "API仕様取得", "API 仕様取得", "共通（対象検索・全量とも）",
      "認証実装チェック Lambda", "認証構成情報配置バケット（openapi/）", "同期", "認証実装チェック Lambda", "アプリごとに 1 回",
      "確認対象の endpoint 一覧と公開明示（MON-1）を取得する。",
      "s3:GetObject",
      "認証実装チェック Lambda -> 配置バケット : GetObject(openApiS3Key)\n配置バケット --> 認証実装チェック Lambda : API 仕様\n【シーケンス図の所在】11 §11.1 検査実行シーケンス / 10 §10.1.7 F2",
      "API 仕様が存在しない場合（モノリスの endpoint 列挙方式）の分岐を明記する"),
    P("認証実装チェック-03", "正常系確認用トークン取得", "正常系確認用トークン取得", "共通（対象検索・全量とも）",
      "認証実装チェック Lambda", "Secrets Manager → 認証基盤 /token", "同期", "認証実装チェック Lambda", "確認ごとに 1 回",
      "正常系アクセス確認で使う短命トークンを取得する。",
      "secretsmanager:GetSecretValue / 認証基盤の公開 /token（インターネット経由・OAuth client_credentials）",
      "認証実装チェック Lambda -> Secrets Manager : GetSecretValue\n認証実装チェック Lambda -> 認証基盤 /token : client_credentials\n認証基盤 --> 認証実装チェック Lambda : access_token（短命）\n【シーケンス図の所在】11 §11.1 検査実行シーケンス / 10 §10.1.7 F2",
      "トークンのキャッシュ有無・失効時の再取得・ログへのマスク（トークンを出力しない）を明記する"),
    P("認証実装チェック-04", "未認証アクセス確認", "未認証アクセス確認", "共通（対象検索・全量とも）",
      "認証実装チェック Lambda", "CloudFront → WAF → API GW / ALB", "同期", "認証実装チェック Lambda", "endpoint ごとに 1 回",
      "認証情報なしでリクエストし、正しく拒否されるか（401/403、Cookie 系は 302）を確認する。2xx なら認証実装漏れ。",
      "認証不要（Public 経路）/ HTTPS 443 / X-Auth-Probe ヘッダ付与（WAF 誤検知回避）",
      "認証実装チェック Lambda -> CloudFront : リクエスト（認証ヘッダなし, X-Auth-Probe）\nCloudFront -> API GW / ALB : Origin Protection 付与\nAPI GW / ALB --> 認証実装チェック Lambda : ステータスコード（本文は読み捨て）\n【シーケンス図の所在】11 §11.1 検査実行シーケンス / 10 §10.1.7 F2",
      "公開明示（x-synthetics-skip-auth-check）付き endpoint の扱い、タイムアウト値、endpoint 単位の継続（1 件失敗で打ち切らない）を明記する",
      d=dict(
        position="認証実装チェック-02 で得た endpoint リストのループ内。本処理（未認証）→ 認証実装チェック-05（正常系）→ 認証実装チェック-06（判定）の順で 1 endpoint を処理する（11 §11.1 ④）。"
                 "本処理は「認証が効いているか」を直接確かめる本機構の中核で、2xx が返れば認証実装漏れとして P1 になる。",
        pre=[
          "認証実装チェック-01 で台帳から baseUrl / authPattern を取得済み",
          "認証実装チェック-02 で endpoint 記述子（method / path / rawPath / skipAuthCheck）を取得済み。MON-1 の公開印は解釈済み",
          "識別ヘッダ X-Auth-Probe の値を Secrets Manager から取得済み",
          "対象アプリの WAF に識別ヘッダの許可ルールが入っていること（M-Q-11-5）。未設定だと WAF ブロックによる WARN が多発する（11 §11.2.4）",
        ],
        inputs=[
          ["baseUrl", "string", "○", "台帳 registry/{appId}/{env}.json（認証実装チェック-01）",
           "検査先の CloudFront URL。例 https://expense.example.com（API GW の直 URL ではない。12 章）"],
          ["authPattern", "enum（6 値）", "○", "同上",
           "期待ステータスの分岐に使う。api-gw-jwt / alb-code-jwt / alb-cookie-monolith / bff-cookie-session / api-gw-iam / lambda-url-iam"],
          ["ep.method", "string", "○", "認証実装チェック-02（extractEndpoints）", "HTTP メソッド。例 GET"],
          ["ep.path", "string", "○", "認証実装チェック-02",
           "path parameter を dummy 値（x-canary-path-params）で解決済みのパス。例 /api/users/1"],
          ["ep.rawPath", "string", "○", "認証実装チェック-02",
           "テンプレートのままのパス。ログ・アラートの識別子に使う。例 /api/users/{id}"],
          ["ep.skipAuthCheck", "boolean", "—", "認証実装チェック-02（x-synthetics-skip-auth-check）",
           "true = public と明示された endpoint。本処理をスキップする。未記載は false（= 認証必須、MON-1 の default-deny）"],
          ["X-Auth-Probe 識別値", "string（secret）", "○", "Secrets Manager（共通基盤アカウント）",
           "WAF 許可ルールの照合キー。ログ・アラート本文に出さない（OBS-3）"],
        ],
        outputs=[
          ["negStatus", "number / null", "認証実装チェック-06（メモリ内で受け渡し）",
           "観測した HTTP ステータス。公開印によるスキップ時は null（＝ 判定対象外で OK）"],
          ["wafBlocked", "boolean", "認証実装チェック-06（同上）",
           "WAF による遮断と判別できた場合に true。403 を「認証が効いている」と誤認させないための区別（11 §11.2.4）"],
          ["観測不能フラグ", "boolean", "認証実装チェック-06（同上）", "接続不能・タイムアウト等でステータスを得られなかった場合に true"],
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
          ["negStatus / wafBlocked / 観測不能フラグを認証実装チェック-06 へ渡す",
           "期待値との突き合わせ（authPattern 別の 401/403 or 302）と 4×4 判定は認証実装チェック-06 の責務。本処理は観測に徹する"],
        ],
        exceptions=[
          ["公開印（x-synthetics-skip-auth-check: true）付き endpoint", "認証実装チェック-02 の記述子",
           "probe せず negStatus = null", "通知なし（OK 判定）", "13 §13.3.0 / README §2.3"],
          ["WAF が probe を遮断（403）", "応答の形が CloudFront / WAF 由来",
           "wafBlocked = true として返す", "認証実装チェック-06 で WARN「境界でブロック」→ P2 Platform", "11 §11.2.4"],
          ["接続不能 / DNS 解決失敗 / TLS 証明書エラー", "例外捕捉",
           "観測不能として記録し次の endpoint へ継続", "認証実装チェック-06 で WARN（構成）→ P2 Platform", "18 §18.5.2"],
          ["タイムアウト（接続 3 秒 / 応答 10 秒 超過）", "同上", "同上", "同上", "§10 上限・制約"],
          ["5xx が返る", "ステータス", "そのまま観測値として返す（本処理では異常扱いしない）",
           "認証実装チェック-06 の判定に委ねる", "11 §11.2.2"],
          ["2xx が返る", "ステータス", "そのまま観測値として返す",
           "認証実装チェック-06 で CRITICAL（認証実装漏れ）→ P1 Security 即時", "11 §11.2.2 / README §2.5"],
        ],
        idem=(
          "参照系の読み取り検査であり状態を持たないため、何度実行しても結果は変わらず安全（冪等）。"
          "対象検索 → 検査の invoke は at-least-once（18 §18.5.2）で重複起動しうるが、重複しても無害。"
          "※ 更新系メソッドを probe する場合の副作用は M-Q-11-6（§11 未決）を参照",
          "本処理は台帳・S3・メトリクスのいずれも更新しない。観測値はメモリ上で認証実装チェック-06 へ渡すのみで、"
          "メトリクス送信は認証実装チェック-07、通知は認証実装チェック-08 以降に集約する",
        ),
        authnote=[
          "認証情報は付与しない（付与しないことが検査の本体）。Authorization / Cookie とも送らない",
          "X-Auth-Probe の識別値は Secrets Manager 管理。ログ・アラート本文・例外メッセージに出さない（OBS-3 機微情報のマスク）",
          "Origin Protection（X-Origin-Verify）は CloudFront が付与するため probe 側では付与しない",
          "AWS API の呼び出しは伴わない（Secrets の取得は認証実装チェック-03 / 起動時に済ませる）。本処理の通信はインターネット向け HTTPS 443 のみ",
        ],
        logs=[
          ["ログ", "probe 実行ログ",
           "appId / env / authPattern / method / rawPath / negStatus / wafBlocked / 所要 ms / 相関 ID（実行 ID）",
           "1 endpoint 1 行。識別ヘッダ値・トークンはマスク（06 章 OBS-2 相関 ID / OBS-3 マスク）"],
          ["ログ", "スキップログ", "公開印により probe しなかった endpoint（appId / rawPath）",
           "公開印の濫用レビュー（月次棚卸し）の入力になる"],
          ["メトリクス", "（本処理では送信しない）", "EndpointsProbed ほかの集計送信は認証実装チェック-07 に集約",
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
    P("認証実装チェック-05", "正常系アクセス確認", "正常系アクセス確認", "共通（対象検索・全量とも）",
      "認証実装チェック Lambda", "CloudFront → WAF → API GW / ALB", "同期", "認証実装チェック Lambda", "endpoint ごとに 1 回",
      "有効なトークン付きでリクエストし、200 が返ることで API 稼働と確認処理自体の健全性を確かめる。",
      "Bearer（認証実装チェック-03 のトークン）/ HTTPS 443 / X-Auth-Probe ヘッダ付与",
      "認証実装チェック Lambda -> CloudFront : GET（Authorization: Bearer …, X-Auth-Probe）\nAPI GW --> 認証実装チェック Lambda : ステータスコード\n【シーケンス図の所在】11 §11.1 検査実行シーケンス / 10 §10.1.7 F2",
      "参照系のみ実行すること（更新系を叩かない）、対象 endpoint の選定規則を明記する"),
    P("認証実装チェック-06", "確認結果判定", "確認結果判定（4×4）", "共通（対象検索・全量とも）",
      "認証実装チェック Lambda（内部）", "—", "内部", "認証実装チェック Lambda", "endpoint ごとに 1 回",
      "未認証アクセス確認と正常系アクセス確認の結果の組み合わせから、重要度（CRITICAL / WARN / INFO / OK）を判定する。",
      "—（AWS 呼び出しなし）",
      "認証実装チェック Lambda : (未認証結果, 正常系結果) -> 4×4 真偽値表 -> 重要度決定\nWAF 起因の 403 は WARN（構成）に分類\n【シーケンス図の所在】11 §11.1 検査実行シーケンス / 10 §10.1.7 F2",
      "4×4 の全組み合わせと重要度の対応表を貼る（code-samples/README §2 が正）"),
    P("認証実装チェック-07", "確認結果メトリクス送信", "確認結果メトリクス送信", "共通（対象検索・全量とも）",
      "認証実装チェック Lambda", "CloudWatch", "同期", "認証実装チェック Lambda", "確認ごとに 1 回",
      "確認結果をメトリクス化し、保険系アラーム（AuthCheckCritical > 0）の入力とする。",
      "cloudwatch:PutMetricData / monitoring.{region}.amazonaws.com",
      "認証実装チェック Lambda -> CloudWatch : PutMetricData(AuthCheckCritical ほか, ディメンション=appId/env)\n【シーケンス図の所在】11 §11.1 検査実行シーケンス / 10 §10.1.7 F2",
      "ディメンション設計（アプリ数比例でメトリクス課金が増える点に注意）を明記する"),
    P("認証実装チェック-08", "検知結果通知依頼", "検知結果通知依頼", "共通（対象検索・全量とも）",
      "認証実装チェック Lambda", "アラート検知 Lambda", "非同期", "認証実装チェック Lambda", "重要度≠OK 時",
      "判定済みの検知結果を、通知の振り分けを行うアラート検知 Lambda へ引き渡す。",
      "lambda:InvokeFunction（InvocationType=Event）",
      "認証実装チェック Lambda -> アラート検知 Lambda : Invoke(Event, 4×4 判定済みイベント)\n【シーケンス図の所在】11 §11.1 検査実行シーケンス / 10 §10.1.7 F2",
      "イベント形式（README §2.6）と、配列でのバッチ送付の可否を明記する"),

    # ---------------- アラート通知
    P("通知-01", "通知先解決", "通知先解決", "共通（検知時）",
      "アラート検知 Lambda", "認証構成情報配置バケット（registry/）", "同期", "アラート検知 Lambda", "イベントごとに 1 回",
      "台帳の通知先設定から送信先を解決する。未設定時は全社デフォルトを使う。",
      "s3:GetObject",
      "アラート検知 Lambda -> 配置バケット : GetObject（alertRouting 参照）\n未設定 -> 全社デフォルト ARN\n【シーケンス図の所在】15 §15.1 振り分けフロー / 10 §10.1.7 F3",
      "2 段解決（アプリ個別 → 全社デフォルト）の順序と、未解決時に throw する仕様を明記する"),
    P("通知-02", "重要度別通知送信", "重要度別通知送信", "共通（検知時）",
      "アラート検知 Lambda", "SNS（P1 Security / P2 Platform / P3 App）", "同期", "アラート検知 Lambda", "イベントごとに 1 回",
      "重要度に応じた宛先へ通知を送信する。",
      "sns:Publish / sns.{region}.amazonaws.com",
      "アラート検知 Lambda -> SNS(P1|P2|P3) : Publish（件名・本文・appId・endpoint・判定根拠）\n【シーケンス図の所在】15 §15.1 振り分けフロー / 10 §10.1.7 F3",
      "通知本文のテンプレートと、1 件でも失敗したら throw（DLQ 発火）する仕様を明記する"),
    P("通知-03", "メトリクス閾値通知", "メトリクス閾値通知（保険系）", "共通（閾値超過時）",
      "CloudWatch Alarm", "SNS", "非同期", "CloudWatch", "閾値超過時",
      "アラート検知 Lambda の経路とは独立に、メトリクス閾値からも発報する（発報 2 系統の保険側）。",
      "CloudWatch Alarm → SNS（アラームアクション）",
      "CloudWatch Alarm(AuthCheckCritical > 0) -> SNS : 通知\n【シーケンス図の所在】15 §15.1 振り分けフロー / 10 §10.1.7 F3",
      "即時系（アラート検知 Lambda）と保険系の重複通知の扱いを明記する"),

    # ---------------- 運用・異常系
    P("運用-01", "監視機構稼働監視通知", "監視機構稼働監視通知（MM-1〜5）", "随時（異常時）",
      "CloudWatch Alarm", "SNS（P2 Platform）", "非同期", "CloudWatch", "閾値超過時",
      "監視機構そのものの停止・失敗を検知して発報する（監視の空白＝検知の空白を防ぐ）。",
      "CloudWatch Alarm → SNS",
      "Alarm(DiscoveryLastSuccess 2h 欠損 / Lambda Errors / DLQ 滞留) -> SNS(P2)\n【シーケンス図の所在】18 §18.5 運用設計 / 10 §10.1.7 F3",
      "MM-1〜5 の各アラーム定義（対象メトリクス・閾値・評価期間）を一覧化する"),
    P("運用-02", "処理失敗退避・再処理", "処理失敗退避・再処理（DLQ）", "随時（異常時）",
      "各 Lambda（非同期実行の失敗）", "SQS DLQ → 運用者", "非同期", "Lambda / 運用者", "失敗時",
      "非同期呼び出しがリトライ後も失敗した場合に退避し、後から再処理・原因調査できるようにする。",
      "Lambda 非同期呼び出しの DLQ 設定 / sqs:ReceiveMessage・DeleteMessage（運用者）",
      "Lambda(失敗) -> 自動リトライ(2 回) -> SQS DLQ\n運用者 -> DLQ : 内容確認 -> 再実行\n【シーケンス図の所在】18 §18.5 運用設計 / 10 §10.1.7 F3",
      "DLQ の保持期間・再処理手順（Runbook 化）・滞留アラーム（MM-4/5）を明記する"),
    P("運用-03", "監視設定手動更新", "監視設定手動更新", "随時（運用操作）",
      "運用者", "認証構成情報配置バケット（registry/）", "同期", "運用者", "随時",
      "監視の有効・無効の切替や通知先の設定など、中央管理項目を運用者が更新する。",
      "s3:GetObject / s3:PutObject（ETag 条件付き）",
      "運用者 -> 配置バケット : GetObject -> 編集 -> PutObject（If-Match）\n巡回と競合した場合は 412 -> 再取得\n【シーケンス図の所在】18 §18.5 運用設計 / 10 §10.1.7 F3",
      "巡回（対象検索-09）との競合手順、変更履歴の追跡（Versioning）、承認フローの要否を明記する"),

    # ---------------- アプリ接点
    P("連携-01", "認証構成情報配置", "認証構成情報配置（アプリ側）", "随時（デプロイのたび）",
      "ベンダー CI（デプロイパイプライン最終段）", "認証構成情報連携バケット（App アカウント）", "同期", "ベンダー CI", "デプロイのたび",
      "デプロイ成功後に認証構成情報を配置する。本監視の入口であり、アプリ（ベンダー）側の責務。",
      "ArtifactUploadRole-{appId} を Assume / s3:PutObject（{appId}/* 限定）/ s3.{region}.amazonaws.com",
      "ベンダー CI -> STS : AssumeRole(ArtifactUploadRole-{appId})\nベンダー CI -> 連携バケット : PutObject(monitoring.yaml, openapi.yaml, deploy-info.json)\n【シーケンス図の所在】vendor-guide-artifact-upload.md §3.3 / 10 §10.1.7 F1",
      "デプロイ成功後に実行すること（順序逆転の禁止）、配置漏れは原則アプリ責任（M-Q-17-7）である旨を明記する"),
]
