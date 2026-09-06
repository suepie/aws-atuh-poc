#!/usr/bin/env python3
"""メモ整理（memo-triage-2026-09-06.md）を TSV SSOT に反映し、SYNC ファイルと変更ログを生成する。

入力: wbs-text/*_概要_成果物.tsv, SYNC_effort.tsv, /tmp/xl.json（Excel の現状: 項目名 E・状態 R・並び順）
出力: 同 TSV（項目・状態 列を追加）, SYNC_*.tsv, memo-triage-changelog-2026-09-06.md
"""
import csv, json, os, re, collections

W = os.path.dirname(os.path.abspath(__file__))
BODY = ['AG_概要_成果物.tsv', 'H-other_概要_成果物.tsv', 'HB-F_概要_成果物.tsv',
        'HB-other_廃止行_概要_成果物.tsv', 'HL-GD_概要_成果物.tsv']
OUT_OMIT = '対象外：省略・吸収'

# ---------- 読み込み ----------
rows = collections.OrderedDict()   # id -> dict
file_of = {}
for f in BODY:
    with open(os.path.join(W, f), encoding='utf-8') as fp:
        rd = list(csv.reader(fp, delimiter='\t'))
    hdr = rd[0]
    for r in rd[1:]:
        if not r or not r[0]:
            continue
        d = dict(zip(hdr, r))
        rows[d['WBS ID']] = d
        file_of[d['WBS ID']] = f
COLS = hdr  # 13 列

eff = {}
with open(os.path.join(W, 'SYNC_effort.tsv'), encoding='utf-8') as fp:
    for r in list(csv.reader(fp, delimiter='\t'))[1:]:
        eff[r[0]] = float(r[1])

xl = json.load(open('/tmp/xl.json'))
xl_order = [r[1]['A'] for r in xl]
xl_name = {r[1]['A']: r[1]['E'] for r in xl}
xl_state = {r[1]['A']: r[1].get('R', '未着手') for r in xl}
xl_eff = {r[1]['A']: float(r[1]['H'] or 0) for r in xl}

assert set(rows) == set(xl_order), (set(rows) ^ set(xl_order))

for i, d in rows.items():
    d['項目'] = xl_name[i]
    d['状態'] = xl_state[i]

log = []  # (id, 変更種別, 内容)
def L(i, kind, txt): log.append((i, kind, txt))

# ---------- 0. 人日の食い違い ----------
USER_EDITED = ['A-1.7', 'B-1.1', 'B-1.2', 'B-1.3', 'B-2.1', 'B-2.2', 'B-3', 'B-4.1', 'B-4.2', 'B-5', 'D-9.3b']
for i in USER_EDITED:
    if eff[i] != xl_eff[i]:
        L(i, '人日', f'{eff[i]} → {xl_eff[i]}（Excel 側の手入力を正とする）')
        eff[i] = xl_eff[i]
for i in [i for i in rows if eff[i] != xl_eff[i]]:
    L(i, '人日', f'{eff[i]} → {xl_eff[i]}（Excel 側の編集を正とする）')
    eff[i] = xl_eff[i]

# ---------- 1. 削除（人日 0 の旧集計行・廃止行） ----------
DELETE = ['HB-09', 'HB-10', 'HB-11', 'HB-12', 'HB-13', 'HB-14', 'B-1.3', 'D-3', 'D-4', 'D-10', 'A-4']
for i in DELETE:
    assert eff[i] == 0, (i, eff[i])
    L(i, '削除', f'人日 0 の旧集計行・廃止行（{rows[i]["項目"]}）')
    del rows[i]; del eff[i]

# ---------- 2. 項目名の変更（接頭辞・改名） ----------
RENAME = {
    # 前提／共通／認証／運用設計／セキュリティ／構成図／構成
    'HA-01': '前提：設計書 総則（目的・範囲・読み方）', 'HA-02': '前提：前提条件一覧', 'HA-03': '前提：用語集・略語集',
    'HA-06': '共通：エラー処理方式設計（方針は 1 冊、個別のエラーは各 API 仕様書）',
    'HA-07': '共通：ログ出力方式設計（レベル/フォーマット/ローテーション）',
    'HA-09': '共通：排他制御・同時実行設計', 'HA-11': '共通：文字コード・日時・タイムゾーン方式',
    'HA-12': '共通：多言語・i18n 方式設計（認証製品のテーマ言語設定を含む）',
    'HA-13': '共通：キャッシュ方式設計', 'HA-14': '共通：採番設計（ID 採番方式・重複回避）',
    'HA-16': '共通：命名規約（リソース/API/DB）', 'HA-17': '共通：Terraform 設計規約',
    'HA-18': '共通：API 設計規約（命名・エラー・ページング・冪等・版管理と廃止方針）',
    'HA-19': '共通：画面設計規約', 'HA-21': '共通：性能設計書（目標値・処理方式・チューニング方針）',
    'HA-22': '共通：キャパシティ・データ量見積（テーブル別・増加率・5 年後）',
    'HA-25': '共通：トレーサビリティ維持運用ルール', 'HA-26': '共通：鍵管理設計書（3 階層の鍵と暗号化の境界）',
    'HA-27': '共通：システム用アカウント台帳の設計', 'HB-01': '共通：機能一覧の成果物化',
    'HE-01': '共通：IF 一覧（内部・同期／非同期）', 'HE-03': '共通：IF 一覧（外部）',
    'HA-10': '認証：セッション管理方式設計（ログイン状態の保持・タイムアウト・ログアウト）',
    'G-3': '運用設計：当番体制と通知先の割り当て',
    'HB-F-ADM-14': '運用設計：テナント（Organization）作成', 'HB-F-ADM-15': '運用設計：テナント設定編集',
    'HB-F-ADM-16': '運用設計：IdP 接続 登録（6 ステップ）', 'HB-F-ADM-17': '運用設計：IdP 接続 編集・証明書更新',
    'HB-F-ADM-18': '運用設計：監査ログ照会', 'HB-F-ADM-19': '運用設計：権限棚卸しキャンペーン（定期起動を含む）',
    'HB-F-INT-11': '運用設計：顧客 IdP 接続情報の自動追随（証明書入替への追随）',
    'HG-04': '運用設計：監査ログ イベント一覧', 'HG-05': '運用設計：監査ログ 取得項目・保持年数・置き場所',
    'HG-06': '運用設計：認可判定の記録の統合',
    'HH-01': '運用設計：監視項目一覧（メトリクス）', 'HH-02': '運用設計：監視項目一覧（ログ・合成監視）',
    'HH-03': '運用設計：閾値・通知先設計', 'HH-04': '運用設計：顧客の受け入れ設計（設計面。手順書とは別）',
    'HH-05': '運用設計：環境設計書（本番 / stg / dev の構成差分）',
    'D-16.1': '運用設計：業務システム（ServiceNow）への移行を 4 段階で進める手順',
    'D-16.3': '運用設計：業務システムにしかいない利用者の移行方針',
    'D-20': '運用設計：運用委託先から個人情報を見せない記録方式',
    'HG-07': 'セキュリティ：不審な挙動を判定する条件と主要指標の定義', 'HG-08': 'セキュリティ：攻撃経路対応表（33 経路×対策）',
    'G-4.2': '構成図：ネットワーク詳細図', 'HA-04': '構成図：全体構成図（論理・清書を含む）', 'HA-05': '構成図：全体構成図（物理・清書を含む）',
    'HJ-17': '構成：クラスタ構成設計書（ノード群・配置制約・自動増減）',
    'HJ-18': '構成：認証製品の導入部品・設定定義の設計（版数・更新戦略）',
    'HJ-19': '構成：クラスタ運用の境界と責任分界（ベンダー保守との分担）',
    # 調査計画
    'A-1.7': '調査計画：仮定値の根拠整理', 'A-3.1': '調査計画：SCIM 受信窓口の試作', 'A-3.2': '調査計画：SCIM 適合検査に通るか',
    'A-3.3': '調査計画：SCIM の作成・更新・削除の写像', 'A-6.1': '調査計画：顧客 IdP 実機①（仮の IdP）との差',
    'A-6.2': '調査計画：顧客 IdP 実機②（仮の IdP・SAML）との差', 'A-6.3': '調査計画：実機での拡張の発火と記録',
    'A-6.4': '調査計画：実機差の設計反映', 'A-13': '調査計画：メール非保有者の 3 経路完走',
    'A-11': '調査計画：テナントの存在を推測されないか', 'A-15': '調査計画：記録の可視性（承認ゲートの照会）',
    'A-20': '調査計画：管理用の口からパスワードのハッシュが読めないことの実機確認',
    # SCIM 明記
    'HB-F-PROV-03': '機能仕様書: SCIM 受信 利用者作成', 'HB-F-PROV-04': '機能仕様書: SCIM 受信 利用者更新',
    'HB-F-PROV-05': '機能仕様書: SCIM 受信 利用者削除（消さずに無効化へ読み替え）',
    'HB-F-PROV-06': '機能仕様書: SCIM 受信 利用者検索・絞り込み', 'HB-F-PROV-07': '機能仕様書: SCIM 受信 グループ連携',
    'HE-09': 'SCIM 受信仕様（顧客の人事システム・IdP → 本基盤：窓口・項目の対応づけ・絞り込み・削除の無効化読み替え）',
    # 属性統一 / JWT
    'HB-F-PROV-08': '機能仕様書: 項目名の変換・統一（顧客ごとの項目名 → 基盤の統一名。統一名の辞書を含む）',
    'HD-18': 'IdP ごとの項目名変換方針（変換表の置き場所と変換規則）',
    'HD-05': '利用者属性に載せる項目の宣言設計（メール非保有対応を含む）',
    'D-8b': '顧客ごとの追加項目（社員番号・部署など）の受入上限と形式',
    'HJ-07': 'JWT（通行証）に載せる項目と要求範囲の定義書',
    # Realm 統合後の改名
    'HJ-01a': 'Realm / Organizations 構成設計書', 'HJ-02a': '認証フローの組み立て順序（3 系統）', 'HJ-10a': '認証製品の設定値一覧',
    # HRD
    'HJ-03': 'HRD：自社拡張の仕様書（接続先の自動振り分け・判定ロジック）',
    # その他の改名
    'HB-F-AUTH-14': '機能仕様書: 2 台目の認証器登録時の本人再確認',
    'HB-F-AUTH-07': '機能仕様書: 初回フェデレーションログイン時の利用者自動登録（JIT）',
    'HB-F-AUTH-02': '機能仕様書: HRD（識別子先行による IdP 解決。判定できないときのパスワード入力への切替を含む）',
    'HB-F-AUTH-21': '機能仕様書: アカウント列挙対策（応答同一化・画面文言）',
    'HB-F-PROV-10': '機能仕様書: 利用者の停止（消さずに無効化・停止日時の記録）',
    'HB-F-BAT-03': '機能仕様書: システム間の整合突合（どのシステム間で何を合わせるかの一覧を含む）',
    'HB-F-BAT-01': '機能仕様書: 90 日休眠バッチ（JIT・直接収容の利用者が対象、SCIM 利用者は除外）',
    'HD-24': '利用者と記録の保持・停止・消去の全体方針',
    'HD-22': '機能とテーブルの CRUD 対応表（権限設計との突合を含む）',
    'HD-25': '索引・分割・DB チューニング方針（権限 DB ＋ 認証製品 DB）',
    'HE-19a': '鍵・証明書一覧：署名に使う鍵', 'HE-19b': '鍵・証明書一覧：通信を暗号化する証明書',
    'HE-19c': '鍵・証明書一覧：システム同士が相互に確認する証明書', 'HE-19d': '鍵・証明書一覧：顧客から受け取る証明書',
    'D-12': '証明書（顧客 IdP の SAML 署名・本基盤の SAML 署名・TLS）を止めずに入れ替える運用手順',
    'HF-01': 'バッチ一覧', 'HC-03b': '画面遷移図（管理画面・テナント管理者向け）',
    'B-2.1': '配信基盤（CloudFront）から境界管理組織の入口までの繋ぎ方の技術検討',
    'B-2.2': '境界管理組織との協議用の比較資料の作成', 'B-3': '使用する IP アドレス範囲の確定と重複確認',
    'B-4.1': '外向き通信の許可運用に関する境界管理組織との合意資料',
    'B-5': '死活監視を攻撃と誤検知させないための境界管理組織との合意',
    'D-5': 'システム同士が API を呼ぶときに持たせる権限の範囲（呼び出し元ごと）',
    'D-8a': '管理画面・アプリ経由で作った利用者の区分と自動停止の扱い',
    'D-19': '認証システムのまとまり数の決定記録（Realm 統合）',
    'D-18.5': '災害対策をスコープ外とする判断の記録と顧客への説明資料',
    'E-7': 'ログの中央集約（他組織の監査アカウント）の制約確認',
    'E-3': '継続的な費用管理（AWS 基盤チームの仕組みに倣い、本基盤固有の項目のみ）',
    'E-6': 'DB 接続に公式部品を使うかの判断',
    'HE-18a': None, 'HE-22a': None,  # placeholder（新規行で定義）
}
for i, n in RENAME.items():
    if n is None or i not in rows:
        continue
    if rows[i]['項目'] != n:
        L(i, '項目名', f'「{rows[i]["項目"]}」→「{n}」')
        rows[i]['項目'] = n
# 認証製品内の画面
SCREEN_KC = {'a': '識別子の入力画面（HRD）', 'b': 'パスワードの入力画面', 'c': '接続先の選択画面', 'd': '追加認証の入力画面',
             'e': '追加認証の登録画面', 'f': '復旧コードの入力画面', 'g': '復旧コードの表示画面', 'h': 'パスワードの変更画面',
             'i': 'パスワードの再設定画面', 'j': 'エラー・案内の表示画面', 'k': 'ログイン後の遷移先画面（認証製品の外の着地ページになり得る）',
             'l': '同意の確認画面'}
for k, n in SCREEN_KC.items():
    i = 'HC-04' + k
    new = f'画面（認証製品内）：{n}'
    L(i, '項目名', f'「{rows[i]["項目"]}」→「{new}」'); rows[i]['項目'] = new

# ---------- 3. スコープ外（省略・吸収） ----------
OMIT = {
    'A-2.2': '自明として省略', 'A-2.3': '自明として省略', 'A-2.4': '自明として省略', 'A-17': '自明として省略',
    'A-18': '自明として省略', 'A-19': '自明として省略', 'A-9': '自明として省略',
    'A-16': '1 ブランドのみの前提で不要', 'A-14': 'INT-12（CAEP）と同じく初期リリース対象外',
    'D-2': 'ステップアップ認証は不要と決定', 'D-15': 'ステップアップ認証は不要と決定',
    'HB-F-AUTH-17': 'ステップアップ認証は不要と決定', 'GD-25': 'ステップアップ認証は不要と決定',
    'D-17.1': '設計書はまだ無い前提のため改訂作業は不要。内容は HJ-02a に吸収',
    'D-17.2': '同上。内容は HB-F-PROV-09 に吸収', 'D-17.3': '同上。内容は HB-F-AUTH-10〜13 に吸収',
    'D-17.4': '同上。内容は HB-F-AUTH-10〜13 に吸収', 'D-17.5': '同上（突合の対象となる改訂が無い）',
    'D-8c': 'D-8a に吸収（区分と自動停止の扱いを 1 行で決める）', 'D-9.2': 'HG-05 に吸収（監査ログの置き場所・保持年数）',
    'D-11': 'HJ-14 IdP 接続仕様テンプレート（SAML/OIDC 別）に吸収', 'D-14': 'HB-F-AUTH-21 アカウント列挙対策に吸収（画面文言）',
    'E-1.1': 'E-1.2 に吸収（費用比較は構成決定と一体）', 'E-1.3': '④ テストで計上（試験用データの作り方）',
    'F-1': '各タスクの工数で対応', 'F-2': '各タスクの工数で対応', 'F-3': '各タスクの工数で対応',
    'F-4': '設計書はまだ無い前提のため統合作業は不要',
    'G-4.1': 'HA-04 / HA-05 に吸収（清書を含める）', 'HA-08': 'HD-02 ストア間の整合方針に吸収',
    'HA-15': 'HA-18 API 設計規約に吸収（版管理と廃止方針）',
    'HB-15': '各機能仕様書の「主要な流れ」に吸収', 'HB-16': '各機能仕様書の「主要な流れ」に吸収', 'HB-17': '各機能仕様書の「主要な流れ」に吸収',
    'HB-18': '状態は HD-21 値の一覧と PROV-09/10/11 で表現するため省略', 'HB-19': '同上（トークン・セッションは HA-10 で表現）',
    'HC-11': '② 詳細設計で計上',
    'HD-08': '② 詳細設計 DDD-01 で計上（基本設計は ER 図まで）', 'HD-09': '② 詳細設計 DDD-02 で計上',
    'HD-10': '② 詳細設計 DDD-03 で計上', 'HD-12': '② 詳細設計 DDD-05 で計上', 'HD-13': '② 詳細設計 DDD-06 で計上',
    'HD-14': '② 詳細設計 DDD-07 で計上',
    'HD-16': 'HB-F-PROV-17 統合射影に吸収', 'HD-17': 'HB-F-PROV-08 に吸収（統一名の辞書）', 'HD-23': 'HD-22 に吸収',
    'HE-02': 'HE-01 に吸収（内部 IF 一覧を 1 冊に）', 'HE-08': 'HA-18 API 設計規約に吸収', 'HE-10': 'HE-09 に吸収（最初から仕様に含める）',
    'HE-17': 'HJ-14 に吸収', 'HF-03': 'HB-F-BAT-01 / BAT-09 の機能仕様書に吸収（同じバッチを 2 冊で書かない）',
    'HF-05': 'HB-F-BAT-04 / 05 / 07 の機能仕様書に吸収',
    'HJ-08': 'HD-05 に吸収（同一内容）', 'HJ-15': 'HD-18 に吸収', 'HJ-16': 'HJ-03 に吸収（同一内容）',
    'HB-F-PROV-01': 'HB-F-AUTH-07 に吸収（同じ出来事の 2 面）', 'HB-F-AUTH-03': 'HB-F-AUTH-02 に吸収（HRD の一部）',
    'HB-F-BAT-08': 'HB-F-ADM-19 に吸収（定期起動部分）', 'HB-F-INT-10': '価値が薄く、API プラットフォーム側の外形監視と重なるため省略',
    'HB-F-INT-12': '初期リリース対象外（概要に明記済み）',
}
for i, why in OMIT.items():
    d = rows[i]
    assert d['スコープ'] == '対象', (i, d['スコープ'])
    d['スコープ'] = OUT_OMIT
    d['根拠の補足'] = f'【省略・吸収】{why}。人日は復活時のために残す'
    L(i, 'スコープ', f'対象 → {OUT_OMIT}（{why}）')

# ---------- 4. 担当 ----------
K2, K3 = '担当（案②: 一部移管）', '担当（案③: アプリ構築）'
APP2 = ['HB-F-ADM-%02d' % n for n in range(1, 11)] + ['HB-20', 'HB-21', 'HB-22', 'D-9.3a', 'D-8a', 'HC-07', 'HC-10',
                                                        'HB-F-AZ-09', 'D-16.1', 'D-16.3']
for i in APP2:
    if rows[i][K2] != 'アプリチーム':
        L(i, '担当②', f'{rows[i][K2]} → アプリチーム'); rows[i][K2] = 'アプリチーム'
    if rows[i][K3] != 'アプリチーム':
        L(i, '担当③', f'{rows[i][K3]} → アプリチーム'); rows[i][K3] = 'アプリチーム'
for i in ['HB-F-AZ-07', 'HB-F-AZ-08']:
    L(i, '担当②', f'{rows[i][K2]} → 基盤チーム'); rows[i][K2] = '基盤チーム'
    L(i, '担当③', f'{rows[i][K3]} → アプリチーム'); rows[i][K3] = 'アプリチーム'
    rows[i]['根拠の補足'] = '認証製品の標準機能で、基盤側は設定のみ（0.5）。使う側の手引きは GD-34 で扱う'
for i in ['HC-06', 'HC-08', 'HB-F-INT-04', 'HE-13']:
    if rows[i][K2] != '要判断':
        L(i, '担当②', f'{rows[i][K2]} → 要判断'); rows[i][K2] = '要判断'
rows['HC-06']['根拠の補足'] = '画面を分担する場合はデザイン統一の協議が必要（合わせるのが大変というリスク）'
rows['HC-08']['根拠の補足'] = rows['HC-06']['根拠の補足']
rows['HB-F-INT-04']['根拠の補足'] = 'Webhook の送信は基盤・受信はアプリを想定。送信も含めて両方アプリに任せる案もあり協議'
rows['HE-13']['根拠の補足'] = rows['HB-F-INT-04']['根拠の補足']
rows['HC-07']['根拠の補足'] = '細部はアプリに委ねる。ただし認証製品内の 12 画面分は基盤が対応する'
rows['HB-F-AZ-09']['根拠の補足'] = '権限データ側の判定記録。認証製品のログイン記録は HG-04 で基盤が持つ'
for i in ['HB-F-ADM-%02d' % n for n in range(1, 11)]:
    rows[i]['根拠の補足'] = '統合後の Keycloak 上の利用者（IdP を持たないテナントの利用者と運用者）を管理画面から操作する機能。管理画面がアプリ担当なので案②でもアプリ。PW/MFA リセット・強制ログアウトは認証製品の管理 API を呼ぶだけで作業は薄い'

# ---------- 5. 作業種別・状態 ----------
L('HB-08', '作業種別', f'{rows["HB-08"]["作業種別"]} → レビュー・合意'); rows['HB-08']['作業種別'] = 'レビュー・合意'
STATE = {}
for i in ['D-6', 'E-8', 'HB-F-AUTH-18', 'HB-F-AUTH-11', 'HB-F-AUTH-13', 'HB-F-AUTH-22', 'HB-F-INT-01', 'HB-F-INT-02',
          'HB-F-INT-03', 'HE-16', 'D-16.2', 'HB-F-INT-07', 'HB-F-INT-08', 'D-8a']:
    STATE[i] = '要件確認'
for i in ['HB-F-ADM-20', 'HB-F-ADM-21']:
    STATE[i] = '保留'
for i in ['HA-20', 'HA-23', 'HA-24']:
    STATE[i] = '着手'
for i, s in STATE.items():
    if rows[i]['状態'] != s:
        L(i, '状態', f'{rows[i]["状態"]} → {s}'); rows[i]['状態'] = s

# ---------- 6. 人日 ----------
for i, v in {'E-3': 1.0, 'E-6': 1.0, 'D-19': 1.0, 'HA-18': 2.0}.items():
    L(i, '人日', f'{eff[i]} → {v}'); eff[i] = v
rows['D-19']['根拠の補足'] = '2026-09-02 に Realm 統合として決定済み。決定記録のみ残す'
rows['E-6']['根拠の補足'] = '公式 JDBC か接続プール（RDS Proxy）かの判断。1 人日で足りる'

# ---------- 7. 概要の加筆 ----------
ADD = {
    'HB-F-PROV-09': '登録経路（JIT / SCIM / 管理画面 / アプリ API / 運用者 / 移行）の区別であり、OIDC / SAML の区別ではない（それは IdP 接続の属性）',
    'HB-F-BAT-01': '1 本のバッチで、SCIM 管理下の利用者は除外条件で外す（顧客 IdP が正なので基盤側で勝手に止めない）',
    'HB-F-AUTH-07': '認証製品の初回ログイン処理と、その結果として利用者を作るポリシー（属性・重複時の扱い）を 1 冊で書く',
    'HB-F-AUTH-02': '判定できないときのパスワード入力への切替（フォールバック）を含む',
    'HD-25': 'Aurora のパラメータ・接続プール方針・認証製品の標準表の索引方針を含む',
    'HF-01': '基盤が持つバッチは 6 本（90 日休眠 / 整合突合 / JWT 署名鍵ローテ / client_secret ローテ / 証明書期限監視 / 物理削除）',
    'HE-14': '内訳: 認可エンドポイント / トークンエンドポイント / クレーム / ログアウト',
    'HE-15': '内訳: メタデータ / Assertion / シングルログアウト',
    'HE-16': '内訳: SSO / JIT 属性 / ログアウト',
    'HE-13': '内訳: イベント 7 種と本文 / 署名（HMAC）/ 再送と順序',
    'HE-09': '認証製品の標準 SCIM 受信は使わず（成熟度不足）、受信窓口は自作またはプラグインの方針',
    'HB-F-PROV-03': '受信窓口は自作またはプラグインの方針（認証製品の標準 SCIM 受信は使わない）',
    'A-6.1': '仮の IdP を用意して実施', 'A-6.2': '仮の IdP を用意して実施', 'A-6.3': '仮の IdP を用意して実施', 'A-6.4': '仮の IdP を用意して実施',
    'D-5': '例: 管理 API（Lambda）→ 認証製品の管理用の口、バッチ → 管理 API。アカウント越境の配送が対象外になったので範囲は縮小',
    'HC-07': '認証製品内の 12 画面分は基盤が対応する',
    'D-16.2': 'ADR-023 では「ServiceNow 側の利用者は残したまま認証で遮断」と決めているが、顧客要件としては未確認',
    'HB-F-ADM-19': '定期起動（旧 BAT-08）を含む',
    'HD-22': '対象は権限 DB と認証製品の利用者属性（認証製品の標準表は触らない）',
    'HE-01': '内部の同期 IF と非同期 IF を 1 冊にまとめる',
    'HA-18': 'エラー・ページング・冪等（旧 HE-08）と版管理・廃止方針（旧 HA-15）を含む',
    'HA-04': '清書（旧 G-4.1）を含む', 'HA-05': '清書（旧 G-4.1）を含む',
    'HD-24': 'ライフサイクル設計書の表紙。保持年数・停止・消去の全体方針を示し、各機能仕様書がこれに従う',
    'HB-F-BAT-03': '同期・整合突合設計書の表紙。顧客 IdP / SCIM ↔ 認証製品 ↔ 権限 DB の間で何を合わせるかの一覧を含む',
}
for i, t in ADD.items():
    rows[i]['概要'] = rows[i]['概要'].rstrip('。') + '。' + t
    L(i, '概要', f'追記: {t}')

# ---------- 8. 成果物に収載先を付ける ----------
DELIV = {
    '利用者ライフサイクル設計書': ['HD-24', 'HB-F-PROV-09', 'HB-F-PROV-10', 'HB-F-PROV-11', 'HB-F-BAT-01', 'HB-F-BAT-09', 'HJ-04', 'D-8a'],
    '同期・整合突合設計書': ['HB-F-BAT-03', 'HD-02'],
    '鍵・証明書管理設計書': ['HE-19a', 'HE-19b', 'HE-19c', 'HE-19d', 'HA-26', 'HB-F-BAT-04', 'HB-F-BAT-05', 'HB-F-BAT-07', 'D-12', 'G-1.5'],
    '項目名の変換・統一設計書': ['HB-F-PROV-08', 'HD-05', 'HD-18', 'D-8b'],
    '多要素認証設計書': ['HB-F-AUTH-%02d' % n for n in range(10, 17)] + ['HB-F-ADM-09', 'HC-04d', 'HC-04e', 'HC-04f', 'HC-04g'],
    '権限データ更新設計書（アプリ）': ['HB-F-PROV-15', 'HB-F-PROV-16', 'HB-F-PROV-17', 'HB-F-AZ-01', 'HB-F-AZ-02', 'HB-F-AZ-03', 'HB-F-AZ-04'],
    'ログ設計書': ['HA-07', 'HG-04', 'HG-05', 'HG-06', 'HC-10', 'E-7', 'D-20', 'HD-15'],
}
for book, ids in DELIV.items():
    for i in ids:
        rows[i]['成果物と完了条件'] = f'→ 収載先: {book}。' + rows[i]['成果物と完了条件']
        L(i, '成果物', f'収載先「{book}」を先頭に追記')

# ---------- 9. 分割（親を子で置き換え） ----------
def child(parent, cid, name, days, **over):
    d = dict(rows[parent]); d['WBS ID'] = cid; d['項目'] = name
    d.update(over); return d, days

NEW = []  # (parent, [(row, days)])
p = 'E-4'
NEW.append((p, [child(p, 'E-4a', '本番設定: 同時受付数の上限', 1),
                child(p, 'E-4b', '本番設定: 外部に出さないパスの遮断表', 1),
                child(p, 'E-4c', '本番設定: クラスタ内通信の暗号化と 30 日入替', 1),
                child(p, 'E-4d', '本番設定: クラスタ内のノード発見方式', 1),
                child(p, 'E-4e', '本番設定: ログイン状態の永続化の確認', 1)]))
p = 'HC-01'
NEW.append((p, [child(p, 'HC-01a', '画面（認証製品内）：画面一覧・画面 ID 体系（12 画面）', 1, **{K2: '基盤チーム', K3: '基盤チーム'}),
                child(p, 'HC-01b', '画面（管理画面）：画面一覧・画面 ID 体系（20 画面）', 1)]))
SCR = {
    'HC-05a': ['顧客一覧', '顧客の登録・設定', '接続先一覧', '接続先の登録', '接続先の設定・証明書更新', '顧客追加の承認'],
    'HC-05b': ['利用者一覧・検索', '利用者詳細', '利用者の登録', '利用者の変更', '利用者の停止・再開', 'パスワード初期化・追加認証の解除', '利用者の招待', '一括登録・ファイル出力'],
    'HC-05c': ['使えるアプリの割当', 'アプリ内の役割の割当', '組織属性の設定', '権限のひな形・棚卸し'],
    'HC-05d': ['操作記録の照会', '権限判定の記録の照会'],
}
for p, names in SCR.items():
    NEW.append((p, [child(p, f'{p}-{n+1}', f'画面（管理画面）：{nm}', 0.5) for n, nm in enumerate(names)]))
p = 'HB-F-AZ-05'
NEW.append((p, [child(p, 'HB-F-AZ-05a', '機能仕様書: テナント越境の防止（認証製品側：他テナントの IdP で入れない）', 0.25, **{K2: '基盤チーム', K3: 'アプリチーム'}),
                child(p, 'HB-F-AZ-05b', '機能仕様書: テナント越境の防止（権限データ側：他テナントのデータに触れない）', 0.5, **{K2: 'アプリチーム', K3: 'アプリチーム'})]))
p = 'HE-22'
NEW.append((p, [child(p, 'HE-22a', 'API エラーコード体系（認証製品の標準エラー）', 1, **{K2: '基盤チーム', K3: '基盤チーム'}),
                child(p, 'HE-22b', 'API エラーコード体系（管理 API）', 2, **{K2: 'アプリチーム', K3: 'アプリチーム'})]))
p = 'HE-18'
NEW.append((p, [child(p, 'HE-18a', '外部 IF 漏えいパスワード検知（HIBP）', 1, **{'状態': '要件確認'}),
                child(p, 'HE-18b', '外部 IF メール送信（SES）', 1, **{'状態': '要件確認'})]))

new_ids = []
for parent, kids in NEW:
    assert abs(sum(k[1] for k in kids) - eff[parent]) < 1e-9, (parent, eff[parent])
    items = list(rows.items()); idx = [k for k, _ in items].index(parent)
    items = items[:idx] + [(k[0]['WBS ID'], k[0]) for k in kids] + items[idx + 1:]
    rows = collections.OrderedDict(items)
    f = file_of[parent]
    for k, days in kids:
        eff[k['WBS ID']] = days; file_of[k['WBS ID']] = f; new_ids.append(k['WBS ID'])
    del eff[parent]
    L(parent, '分割', f'→ {", ".join(k[0]["WBS ID"] for k in kids)}（人日合計は不変）')

# ---------- 10. 並び順 ----------
order = [i for i in xl_order if i not in DELETE]
for parent, kids in NEW:
    idx = order.index(parent); order[idx:idx + 1] = [k[0]['WBS ID'] for k in kids]
for i in DELETE:
    pass  # already absent
def move_after(target, ids):
    global order
    for i in ids:
        order.remove(i)
    idx = order.index(target) + 1
    order[idx:idx] = ids
# A: 調査計画 → 省略
A_plan = ['A-1.7', 'A-3.1', 'A-3.2', 'A-3.3', 'A-6.1', 'A-6.2', 'A-6.3', 'A-6.4', 'A-13', 'A-11', 'A-14', 'A-15', 'A-20']
A_omit = ['A-2.1', 'A-2.2', 'A-2.3', 'A-2.4', 'A-17', 'A-18', 'A-19', 'A-9', 'A-16', 'A-7']
for i in A_plan + A_omit:
    order.remove(i)
order[0:0] = A_plan + A_omit
move_after('HB-F-AUTH-16', ['HB-F-ADM-09'])              # MFA
move_after('HB-F-AUTH-20', ['D-13'])                     # 締め出し
move_after('HB-F-AUTH-22', ['HA-10'])                    # セッション
move_after('HB-F-AZ-08', ['D-5'])                        # システム間権限
move_after('HB-F-ADM-11', ['HB-F-AZ-03'])
move_after('HB-F-ADM-12', ['HB-F-AZ-04'])
move_after('HB-F-PROV-17', ['HB-F-AZ-01', 'HB-F-AZ-02', 'HD-16'])
move_after('HB-F-PROV-08', ['HD-05', 'HD-18', 'HJ-15', 'HD-17', 'D-8b'])
move_after('HB-F-PROV-11', ['HD-24', 'HB-F-BAT-01', 'HB-F-BAT-09', 'HJ-04', 'D-8a', 'D-8c'])
move_after('HD-02', ['HB-F-BAT-03', 'HB-F-BAT-02', 'HA-08'])
move_after('HE-19d', ['HA-26', 'HB-F-BAT-04', 'HB-F-BAT-05', 'HB-F-BAT-07', 'D-12', 'G-1.5', 'HF-05'])
move_after('HA-07', ['HG-04', 'HG-05', 'HG-06', 'D-9.2', 'HC-10', 'E-7', 'D-20', 'HD-15'])
move_after('HA-05', ['G-4.1', 'G-4.2', 'HJ-17', 'HJ-18', 'HJ-19'])
move_after('HA-18', ['HA-15', 'HE-08'])
move_after('HB-F-AUTH-07', ['HB-F-PROV-01'])
move_after('HB-F-AUTH-02', ['HB-F-AUTH-03'])
move_after('HB-F-ADM-19', ['HB-F-BAT-08'])
move_after('HJ-03', ['HJ-16'])
move_after('HJ-14', ['D-11', 'HE-17'])
move_after('HE-09', ['HE-10'])
move_after('HE-01', ['HE-02'])
move_after('HD-22', ['HD-23'])
move_after('HB-F-AUTH-21', ['D-14'])
move_after('HG-05', ['D-9.2'])
assert len(order) == len(rows) and set(order) == set(rows), (len(order), len(rows))
rows = collections.OrderedDict((i, rows[i]) for i in order)

# ---------- 書き出し: 本体 TSV ----------
NEWCOLS = ['WBS ID', '項目'] + COLS[1:] + ['状態']
by_file = collections.defaultdict(list)
for i, d in rows.items():
    by_file[file_of[i]].append(d)
for f in BODY:
    with open(os.path.join(W, f), 'w', encoding='utf-8', newline='') as fp:
        w = csv.writer(fp, delimiter='\t', lineterminator='\n')
        w.writerow(NEWCOLS)
        for d in by_file[f]:
            w.writerow([d.get(c, '') for c in NEWCOLS])

# ---------- SYNC ----------
def code_table(name, values):
    return {v: n + 1 for n, v in enumerate(values)}
C_WORK = code_table('作業種別', ['ガイド・手順書の執筆', 'レビュー・合意', '外部調整', '実機検証・照会', '設計書の執筆', '調査・計画'])
C_K2 = code_table('担当②', ['アプリチーム', '基盤チーム', '要判断'])
C_K3 = code_table('担当③', ['アプリチーム', '共同', '基盤チーム'])
C_BASIS = code_table('判断根拠', ['事故防止', '他組織との調整', '代替手段あり', '利用者が 1 箇所になり不要', '後から追加可能', '改ざん防止', '業務データ',
                                '業務ルール依存', '構成の前提', '権限移管に伴い不要', '横断（対象縮小）', '法令・契約', '画面のみ', '製品機能', '認証の中核', '運用に必須'])
C_SCOPE = code_table('スコープ', ['対象', '対象外：災害対策をやらない', '対象外：認証製品を 1 つに統合', OUT_OMIT])
C_INIT = code_table('当初想定', ['当初あり', '新規: 機能追加', '新規: 自社構築', '新規: 規模', '新規: 非機能・運用'])
C_STATE = code_table('状態', ['未着手', '着手', '要件確認', '保留', '完了'] + sorted({d['状態'] for d in rows.values()} - {'未着手', '着手', '要件確認', '保留', '完了'}))
with open(os.path.join(W, 'SYNC_class.tsv'), 'w', encoding='utf-8') as fp:
    fp.write('# 凡例（コード → 値）\n')
    for title, tbl in [('作業種別', C_WORK), ('担当（案②)', C_K2), ('担当（案③)', C_K3), ('判断根拠', C_BASIS), ('スコープ', C_SCOPE), ('当初想定', C_INIT), ('状態', C_STATE)]:
        fp.write(f'## {title}\n')
        for v, n in tbl.items():
            fp.write(f'{n}\t{v}\n')
    fp.write('\nWBS ID\t作業種別\t担当（案②: 一部移管）\t担当（案③: アプリ構築）\t判断根拠\tスコープ\t当初想定\t状態\n')
    for i, d in rows.items():
        fp.write('\t'.join([i, str(C_WORK[d['作業種別']]), str(C_K2[d[K2]]), str(C_K3[d[K3]]), str(C_BASIS[d['判断根拠']]),
                            str(C_SCOPE[d['スコープ']]), str(C_INIT[d['当初想定']]), str(C_STATE[d['状態']])]) + '\n')
notes = collections.OrderedDict()
for i, d in rows.items():
    notes.setdefault(d['根拠の補足'], []).append(i)
with open(os.path.join(W, 'SYNC_note.tsv'), 'w', encoding='utf-8') as fp:
    fp.write('根拠の補足\t対象 WBS ID\n')
    for n, ids in notes.items():
        fp.write(f'{n}\t{",".join(ids)}\n')
with open(os.path.join(W, 'SYNC_effort.tsv'), 'w', encoding='utf-8') as fp:
    fp.write('WBS ID\t人日\n')
    for i in rows:
        fp.write(f'{i}\t{eff[i]:g}\n')
with open(os.path.join(W, 'SYNC_order.tsv'), 'w', encoding='utf-8') as fp:
    fp.write('WBS ID\t並び順\n')
    for n, i in enumerate(rows, 1):
        fp.write(f'{i}\t{n}\n')
with open(os.path.join(W, 'SYNC_name.tsv'), 'w', encoding='utf-8') as fp:
    fp.write('WBS ID\t項目（新）\n')
    for i, d in rows.items():
        if i in new_ids or xl_name.get(i) != d['項目']:
            fp.write(f'{i}\t{d["項目"]}\n')
with open(os.path.join(W, 'SYNC_text.tsv'), 'w', encoding='utf-8') as fp:
    fp.write('WBS ID\t列\t新しい値\n')
    for i, kind, txt in log:
        if kind in ('概要', '成果物') and i in rows:
            col = '概要' if kind == '概要' else '成果物と完了条件'
            fp.write(f'{i}\t{col}\t{rows[i][col]}\n')
with open(os.path.join(W, 'SYNC_new_rows.tsv'), 'w', encoding='utf-8', newline='') as fp:
    w = csv.writer(fp, delimiter='\t', lineterminator='\n')
    w.writerow(['親 ID'] + NEWCOLS + ['人日'])
    for parent, kids in NEW:
        for k, days in kids:
            w.writerow([parent] + [k.get(c, '') for c in NEWCOLS] + [f'{days:g}'])
with open(os.path.join(W, 'SYNC_delete.tsv'), 'w', encoding='utf-8') as fp:
    fp.write('WBS ID\t理由\n')
    for i in DELETE:
        fp.write(f'{i}\t人日 0 の旧集計行・廃止行\n')
    for parent, kids in NEW:
        fp.write(f'{parent}\t分割により {", ".join(k[0]["WBS ID"] for k in kids)} へ置換\n')

# ---------- 変更ログ ----------
tot = sum(eff.values()); tgt = sum(v for i, v in eff.items() if rows[i]['スコープ'] == '対象')
by_scope = collections.Counter()
for i, d in rows.items():
    by_scope[d['スコープ']] += eff[i]
k2 = collections.Counter(); k3 = collections.Counter()
for i, d in rows.items():
    if d['スコープ'] == '対象':
        k2[d[K2]] += eff[i]; k3[d[K3]] += eff[i]
with open(os.path.join(W, '..', 'memo-triage-changelog-2026-09-06.md'), 'w', encoding='utf-8') as fp:
    fp.write('# メモ整理の反映ログ（2026-09-06）\n\n')
    fp.write(f'- 行数: {len(xl_order)} → {len(rows)}（削除 {len(DELETE)}・分割で {sum(len(k) for _, k in NEW) - len(NEW)} 増）\n')
    fp.write(f'- 全量 {tot:g} 人日 / Phase 1 対象 {tgt:g} 人日\n\n')
    fp.write('| スコープ | 人日 |\n|---|---:|\n')
    for s, v in by_scope.items():
        fp.write(f'| {s} | {v:g} |\n')
    fp.write('\n| 担当（対象のみ） | 案② | 案③ |\n|---|---:|---:|\n')
    for t in ['基盤チーム', 'アプリチーム', '要判断', '共同']:
        fp.write(f'| {t} | {k2.get(t, 0):g} | {k3.get(t, 0):g} |\n')
    fp.write(f'\n## 行別の変更（{len(log)} 件）\n\n| WBS ID | 種別 | 内容 |\n|---|---|---|\n')
    for i, kind, txt in log:
        fp.write(f'| {i} | {kind} | {txt} |\n')
print(f'rows {len(rows)} total {tot:g} target {tgt:g}')
print(dict(by_scope)); print('k2', dict(k2)); print('k3', dict(k3))
