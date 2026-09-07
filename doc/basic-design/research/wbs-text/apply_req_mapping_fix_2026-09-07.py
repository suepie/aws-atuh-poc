#!/usr/bin/env python3
"""要件マッピングのレビュー（2026-09-07）で決めた対応を SSOT（SHEET_*.tsv）へ反映する。

決定（ユーザー 2026-09-07）:
  1. Keycloak-Broker ⇄ Keycloak-IdP の連携を要件・WBS に追加する
  2. Keycloak-IdP 側の非機能はアプリ責務として整理し、本基盤は ROSA の引き渡しまでとする（列を追加）
  3. 停止の伝播（shadow 無効化）は作らない。残存は Keycloak-Broker のセッション上限 12 時間で受容
  4. ROSA 引き渡しの行を機能要件（パスワード等）から外し、責任分界の要件（NFR-OPS-012）へ付け替える
  5. WBS(基本設計) の見出し（Excel 側の固定文）を現行値に直す
  + 漏れ 9 件の追加、矛盾 20 件の修正

やること:
  - 変更前の SSOT から サマリ(工程別)・機能名一覧の集計を再計算し、現行シートと一致することを先に確認する（導出規則の検証）
  - 7 シートを更新して SHEET_*.tsv を書き戻す
  - 差分一覧 SYNC_reqfix_2026-09-07.tsv（シート / ID / 種別 / 列 / 旧 / 新）を出す
  - 検算を表示する
"""
import csv, os, re, collections, copy, sys

W = os.path.dirname(os.path.abspath(__file__))
P = lambda n: os.path.join(W, n)
def load(n):
    with open(P(n), encoding='utf-8', newline='') as fp:
        rd = csv.reader(fp, delimiter='\t'); h = next(rd)
        return h, [dict(zip(h, r + [''] * (len(h) - len(r)))) for r in rd if any(r)]
def save(n, h, rows):
    with open(P(n), 'w', encoding='utf-8', newline='') as fp:
        w = csv.writer(fp, delimiter='\t', lineterminator='\n'); w.writerow(h)
        for r in rows: w.writerow([r.get(c, '') for c in h])
def num(x):
    try: return float(x)
    except: return 0.0
def fmt(x):
    return str(int(x)) if float(x).is_integer() else str(x)

H_BD, bd = load('SHEET_基本設計.tsv'); H_DM, dm = load('SHEET_詳細設計_製造.tsv'); H_TS, ts = load('SHEET_テスト.tsv')
H_FL, fl = load('SHEET_機能名一覧.tsv'); H_FG, fg = load('SHEET_機能グループ一覧.tsv'); H_SM, sm = load('SHEET_サマリ工程別.tsv')
H_RM, rm = load('SHEET_要件マッピング.tsv')
delta = []  # (シート, ID, 種別, 列, 旧, 新)
def log(sheet, rid, kind, col, old, new): delta.append((sheet, rid, kind, col, old, new))

# ---------------------------------------------------------------- 導出規則
def derive_fl(bd, fl):
    out = {}
    for f in fl:
        rows = [r for r in bd if r['機能名'] == f['機能名']]
        out[f['機能ID']] = (len(rows), sum(num(r['人日']) for r in rows), sum(num(r['人日']) for r in rows if r['スコープ'] == '対象'))
    return out
def derive_fg(bd, fg):
    out = {}
    for g in fg:
        rows = [r for r in bd if r['機能グループ'] == g['機能グループ']]
        out[g['機能グループ']] = (len(rows), sum(num(r['人日']) for r in rows))
    return out
def derive_sm(bd, dm, ts, fl):
    out = []
    for f in fl:
        n = f['機能名']
        a = sum(num(r['人日']) for r in bd if r['機能名'] == n and r['スコープ'] == '対象')
        b = sum(num(r['詳細設計 人日']) for r in dm if r['機能名'] == n)
        c = sum(num(r['製造 人日']) for r in dm if r['機能名'] == n)
        d = sum(num(r['人日']) for r in ts if r['機能名'] == n)
        k = sum(1 for r in dm if r['機能名'] == n) + sum(1 for r in ts if r['機能名'] == n)
        if a + b + c + d > 0:
            out.append({'機能グループ': f['機能グループ'], '機能名': n, '① 基本設計': fmt(a), '② 詳細設計': fmt(b),
                        '③ 製造': fmt(c), '④ テスト': fmt(d), '合計': fmt(a + b + c + d), '②③④ 行数': str(k)})
    return out

# ---------------------------------------------------------------- 事前検証（導出規則が現行シートを再現するか）
pre = derive_sm(bd, dm, ts, fl)
cur = {(r['機能グループ'], r['機能名']): r for r in sm}
mism = [(r['機能名'], c, r[c], cur[(r['機能グループ'], r['機能名'])][c]) for r in pre if (r['機能グループ'], r['機能名']) in cur
        for c in ['① 基本設計', '② 詳細設計', '③ 製造', '④ テスト', '②③④ 行数'] if num(r[c]) != num(cur[(r['機能グループ'], r['機能名'])][c])]
missing = [(r['機能グループ'], r['機能名']) for r in pre if (r['機能グループ'], r['機能名']) not in cur]
extra = [k for k in cur if k not in {(r['機能グループ'], r['機能名']) for r in pre}]
print(f'[事前検証] サマリ再計算: 不一致 {len(mism)} / 現行に無い {len(missing)} / 再計算に無い {len(extra)}')
for m in mism[:10]: print('   ', m)
pf = derive_fl(bd, fl)
fm = [(f['機能ID'], pf[f['機能ID']], (f['行数'], f['人日'], f['うち対象'])) for f in fl
      if (num(f['行数']), num(f['人日']), num(f['うち対象'])) != tuple(map(float, pf[f['機能ID']]))]
print(f'[事前検証] 機能名一覧 集計: 不一致 {len(fm)}')
for m in fm[:10]: print('   ', m)
if '--check' in sys.argv: sys.exit(0)

# ---------------------------------------------------------------- 共通ヘルパ
def bdrow(ID, cls, kind, grp, fn, item, desc, done, days, own2, own3, why, note, scope, initial, fid, state='未着手'):
    return {'ID': ID, '分類': cls, '作業種別': kind, '機能グループ': grp, '機能名': fn, '項目': item, '概要': desc,
            '成果物と完了条件': done, '人日': fmt(days), '担当（案②: 一部移管）': own2, '担当（案③: アプリ構築）': own3,
            '判断根拠': why, '根拠の補足': note, 'スコープ': scope, '当初想定': initial, '依存': '—', '状態': state, '出典': '', '機能ID': fid}
def insert_after(rows, key, newrow, keyfn):
    """同じ 機能名 の最後の行の後ろに入れる。無ければ同じ 機能グループ の最後の行の後ろ。"""
    idx = [i for i, r in enumerate(rows) if keyfn(r) == key]
    if not idx:
        idx = [i for i, r in enumerate(rows) if r['機能グループ'] == newrow['機能グループ']]
    pos = (idx[-1] + 1) if idx else len(rows)
    rows.insert(pos, newrow)
def setv(sheet, rows, idcol, ID, col, new):
    r = next(x for x in rows if x[idcol] == ID)
    if r[col] != new:
        log(sheet, ID, '変更', col, r[col], new); r[col] = new
def addrow(sheet, rows, row, idcol, keyfn=None):
    log(sheet, row[idcol], '追加', '—', '', row.get('項目') or row.get('テスト項目') or row.get('機能名'))
    if keyfn: insert_after(rows, keyfn(row), row, keyfn)
    else: rows.append(row)

BD, DM, TS, FL, FG, RM = 'WBS(基本設計)', 'WBS(詳細設計_製造)', 'WBS(テスト)', '機能名一覧', '機能グループ一覧', '要件マッピング'
FN_LINK = 'Keycloak-Broker と Keycloak-IdP の連携'
FN_HAND = 'Keycloak-IdP 側の引き渡しと責任分界'
FN_OPS = '運用者アカウントと権限の保護'
FN_ADMAPI = '管理 API の内部公開（idm-api 向け）'
FN_BAT01 = '長期未使用者の自動停止'
FN_ITDR = '不正兆候の検知'
FN_KCUPD = 'Keycloak の更新・保守'
FN_CONSENT = '利用規約への同意取得と記録'
FN_EDGE = '他組織との構成調整'
G_FED, G_LOCAL, G_OPS, G_INT, G_LIFE, G_DET, G_CONS, G_ARC = ('フェデレーションログイン', 'ローカルログイン（Keycloak-IdP 収容）', '非機能: 運用・監視',
    'アプリ・外部連携', 'ユーザの停止・再開・消去', '監視・検知', '同意管理', '非機能: システム構成')

# ================================================================ 1. 機能名一覧
def fl_set(fid, col, new): setv(FL, fl, '機能ID', fid, col, new)
fl_set('F-AUTH-09', '概要', 'Keycloak-Broker から見て Keycloak-IdP を顧客IdP の 1 つ（共有エントリ）として接続する。識別子の引き継ぎ・追加認証結果の取り込み・ログアウト連鎖・セッション上限の同値を含む。Keycloak-IdP 側の Client・Realm 設定は要求仕様としてアプリチームへ渡す（2026-09-07 復活: 2 台構成に戻したため）')
fl_set('F-AUTH-09', 'アプリ', '△')
fl_set('F-AUTH-01', '概要', '顧客側に認証システムが無い顧客のユーザが Keycloak-IdP に、本基盤の運用者が Keycloak-Broker に、ID とパスワードで直接ログインする。顧客のユーザ分は Keycloak-IdP 側（アプリ責務）、運用者分は本基盤')
fl_set('F-AUTH-01', 'アプリ', '△')
ACCEPT12 = '2026-09-07 決定: 伝播しない。Keycloak-IdP 側で止めた後の残存は Keycloak-Broker のセッション上限（12 時間）で受容する'
fl_set('F-PROV-12', '概要', f'片方で止めた事実をもう一方へ必ず伝える。{ACCEPT12}')
fl_set('F-PROV-13', '概要', f'再開も止めたときと同じ経路で伝える。{ACCEPT12}')
fl_set('F-BAT-02', '概要', f'止めた事実が確実に伝わったかを短い間隔で突き合わせる。{ACCEPT12}')
fl_set('F-BAT-01', '概要', '長期間（90 日）ログインのないユーザを自動で使えない状態にする定期処理。顧客IdP 経由で自動作成したユーザのみが対象で、Keycloak-IdP 収容ユーザと顧客システム連携ユーザは対象外')
fl_set('F-AUTH-28', '概要', '利用規約などへの同意を画面で取り、いつ誰がどの版に同意したかを記録する。要否は顧客回答待ち（D-22）')
def fl_add(after_fid, row):
    for c in ('行数', '人日', 'うち対象'): row.setdefault(c, '0')
    log(FL, row['機能ID'], '追加', '—', '', row['機能名'])
    i = next(i for i, r in enumerate(fl) if r['機能ID'] == after_fid); fl.insert(i + 1, row)
fl_add('F-AUTH-01', {'系統': '認証', '機能グループ': G_LOCAL, '機能名': FN_HAND, '機能ID': 'F-AUTH-29',
    '概要': 'Keycloak-IdP 用の基盤（ROSA）をどこまで作って渡すか、渡した後の非機能（可用性・復旧・監視・更新・鍵・ログ）を誰が持つか。本基盤は ROSA の引き渡しまで、以降はアプリ責務', '基盤': '○', 'アプリ': '△'})
fl_add('F-INT-13', {'系統': '連携', '機能グループ': G_INT, '機能名': FN_ADMAPI, '機能ID': 'F-INT-14',
    '概要': 'アプリ側の管理 API（idm-api）が Keycloak-Broker の管理 API を呼ぶための内部経路と、呼び出し元の資格・許す操作の範囲。ユーザの停止・全セッション破棄など管理画面からの操作はここを通る', '基盤': '○', 'アプリ': '△'})
fl_add('NF-OPS-04', {'系統': '非機能', '機能グループ': G_OPS, '機能名': FN_OPS, '機能ID': 'NF-OPS-11',
    '概要': '本基盤運用者のローカル認証（WebAuthn 必須）、常時の全権付与の禁止と必要時だけの昇格、緊急時アクセスとの関係、定期棚卸し', '基盤': '○', 'アプリ': '-'})

# ================================================================ 2. WBS(基本設計)
KEY = lambda r: r['機能名']
# 2-1 引き渡し行を F-AUTH-29 へ付け替え
for ID in ['HJ-20']:
    setv(BD, bd, 'ID', ID, '機能名', FN_HAND); setv(BD, bd, 'ID', ID, '機能ID', 'F-AUTH-29')
setv(BD, bd, 'ID', 'HJ-10b', 'スコープ', '対象外：Keycloak-IdP 側の責務')
setv(BD, bd, 'ID', 'HJ-10b', '判断根拠', '構成の前提')
setv(BD, bd, 'ID', 'HJ-10b', '根拠の補足', 'Keycloak-IdP 側の設定値はアプリチームが決める。本基盤が求める値は接続仕様（HE-23）に限る')
setv(BD, bd, 'ID', 'HB-F-AUTH-01', '概要', '本基盤の運用者が Keycloak-Broker に ID とパスワード＋WebAuthn で直接ログインする機能。顧客のユーザ分（Keycloak-IdP 収容）はアプリ側の仕様とし、本仕様書は運用者分のみ')
setv(BD, bd, 'ID', 'HB-F-AUTH-01', '成果物と完了条件', '機能仕様書 1 本。運用者の認証手段・失敗時にユーザへ返す内容が定義されレビュー承認済み（パスワード桁数等の顧客ユーザ向け規則は対象外）')
setv(BD, bd, 'ID', 'HB-F-AUTH-01', '根拠の補足', 'Keycloak-Broker にローカルで残るのは運用者だけ。顧客ユーザのパスワード規則は Keycloak-IdP（アプリ責務）')
# 2-2 追加
new_bd = [
 bdrow('HB-F-AUTH-09', 'HB-F 機能仕様書', '設計書の執筆', G_FED, FN_LINK, '機能仕様書: Keycloak-IdP へのログイン委譲',
       'Keycloak-Broker が Keycloak-IdP を顧客IdP の 1 つ（共有エントリ）として扱い、識別子の引き継ぎ・初回作成・追加認証結果（amr）の取り込みを行う',
       '機能仕様書。渡す情報・受け取る情報・拒否時の扱い・2 回目以降は Keycloak-IdP を呼ばないことが定まっている', 1, '基盤チーム', '基盤チーム', '認証の中核',
       '2 台構成に戻したため復活。顧客IdP を持たない顧客のログインはすべてここを通る', '対象', '新規: 機能追加', 'F-AUTH-09'),
 bdrow('HE-23', 'HE つなぎ目設計', '設計書の執筆', G_FED, FN_LINK, 'Keycloak-Broker ⇄ Keycloak-IdP 接続仕様（要求仕様としてアプリチームへ渡す）',
       'Keycloak-IdP 側に求める Client（broker-rp）・返す項目（tenant_id / username / amr）・login_hint の書式・ログアウト連鎖・セッション上限の同値（12 時間）・接続経路（閉域・単方向）を 1 冊にまとめる',
       '接続仕様書。両チームが合意し、Keycloak-IdP 側の設定値がこの 1 冊で作れる', 2.5, '基盤チーム', '基盤チーム', '認証の中核',
       'U2 §2.2.2〜2.2.5 / 02a / U6 D-U6-06 の決定を接続仕様の形にする。アプリチームとの境界そのもの', '対象', '新規: 機能追加', 'F-AUTH-09'),
 bdrow('HI-11', 'HI レビュー・合意', 'レビュー・合意', G_FED, FN_LINK, '接続仕様のアプリチームとの合意',
       '接続仕様（HE-23）をアプリチームとレビューし、Keycloak-IdP 側の設定値と検証環境の提供時期を合意する',
       '合意記録。設定値・検証環境の提供時期・連絡先が定まっている', 1, '基盤チーム', '基盤チーム', '構成の前提',
       '合意が無いと結合試験（IT-16）が始められない', '対象', '新規: 機能追加', 'F-AUTH-09'),
 bdrow('D-21', 'D 判断', 'レビュー・合意', G_LOCAL, FN_HAND, 'Keycloak-IdP 側の非機能責任表（可用性・復旧・監視・更新・鍵・ログ）',
       '非機能要件ごとに Keycloak-IdP 側では誰が満たすかを表にする。本基盤は ROSA の引き渡しまで、以降はアプリ責務とする方針を明文化する',
       '責任表。非機能要件の全行に Keycloak-IdP 側の担当が入っている', 1.5, '基盤チーム', '基盤チーム', '構成の前提',
       '要件マッピングの「Keycloak-IdP 側」列の根拠。曖昧だと SLA と運用で揉める', '対象', '新規: 非機能・運用', 'F-AUTH-29'),
 bdrow('HG-09', 'HG 権限・監査', '設計書の執筆', G_OPS, FN_OPS, '運用者アカウントの認証と権限モデル（WebAuthn 必須・常時全権の禁止・緊急時との関係）',
       '本基盤運用者のローカル認証を WebAuthn 必須とし、常時の全権付与を禁止して必要時だけ昇格する権限モデルと、緊急時アクセス（G-1.6）との関係を決める',
       '設計書の章。認証手段・権限の 2 状態・昇格の手順・記録が定まっている', 2, '基盤チーム', '基盤チーム', '事故防止',
       'ADR-040 Phase 1 α（P1-04 / P1-08 / P1-09）。運用者は Keycloak-Broker にローカルで残る唯一の人', '対象', '新規: 非機能・運用', 'NF-OPS-11'),
 bdrow('HB-F-BAT-01', 'HB 機能設計', '設計書の執筆', G_LIFE, FN_BAT01, '機能仕様書: 長期未使用者の自動停止（90 日）',
       '顧客IdP 経由で自動作成したユーザのうち 90 日ログインの無いものを止める定期処理。Keycloak-IdP 収容ユーザ・顧客システム連携ユーザは対象外',
       '機能仕様書。対象の条件・除外の条件・止めたときの記録が定まっている', 1, '基盤チーム', '基盤チーム', '法令・契約',
       'U3 D3-17 の除外規則を含む。要否は B-JIT-LC-1 で最終確認', '対象', '新規: 機能追加', 'F-BAT-01'),
 bdrow('HJ-22', 'HJ Keycloak の作り込み', '設計書の執筆', G_OPS, FN_KCUPD, '自社拡張と実行イメージの供給網対策（依存の検査・署名・部品一覧）',
       '自社拡張と実行イメージについて、依存の検査・イメージの署名・部品一覧（SBOM）の出し方を決める',
       '設計書の章。検査の道具・署名の方式・部品一覧の形式が定まっている', 1, '基盤チーム', '基盤チーム', '事故防止',
       'ADR-046 Phase 1 = SLSA L2。テスト SEC-09 の根拠となる設計が無かった', '対象', '新規: 非機能・運用', 'NF-OPS-05'),
 bdrow('HH-06', 'HH 運用設計', '設計書の執筆', G_DET, FN_ITDR, '運用設計：不正兆候の検知項目と通知',
       'ログイン失敗の急増・同一送信元の連続試行・新しい顧客IdP からの大量の初回作成など、不正の兆候として見張る項目と通知先を決める。検知して知らせるまでとし、自動遮断はしない',
       '項目一覧。検知の条件・閾値・通知先が定まっている', 1, '基盤チーム', '基盤チーム', '事故防止',
       'ADR-035 Phase 1a（検知通知のみ）。監視項目（HH-01〜03）とは別に不正の観点で持つ', '対象', '新規: 非機能・運用', 'F-INT-08'),
 bdrow('HE-24', 'HE つなぎ目設計', '設計書の執筆', G_INT, FN_ADMAPI, '管理 API の内部公開経路と呼び出し元の権限範囲',
       'アプリ側の管理 API（idm-api）が Keycloak-Broker の管理 API を呼ぶ経路（内部 NLB・インターネット非露出）、呼び出し元の資格（システム間 JWT）と許す操作の範囲、記録の残し方を決める',
       '接続仕様。経路・資格・許す操作の一覧が定まっている', 2, '基盤チーム', '基盤チーム', '事故防止',
       '禁則 K-10（管理 API は内部経路のみ）の実体。ユーザの停止・全セッション破棄など管理画面からの操作はここを通る', '対象', '新規: 機能追加', 'F-INT-14'),
 bdrow('HK-10', 'HK 顧客提供成果物', 'ガイド・手順書の執筆', G_ARC, FN_EDGE, '境界（WAF・NWFW）への要求仕様書／渡す相手: 境界を管理する組織',
       'ログイン口の流量制限・署名鍵公開先の保護・管理画面の遮断・顧客IdP 向け外向き許可など、境界側に求める設定を要求仕様書にする',
       '要求仕様書。要求ごとに値と根拠、確認方法が書かれている', 1.5, '基盤チーム', '基盤チーム', '事故防止',
       'WAF・DDoS は他組織が持つが、何を求めるかは本基盤の責務。HG-08 の「WAF 側で行う前提」の受け皿', '対象', '新規: 非機能・運用', 'NF-ARC-06'),
 bdrow('D-22', 'D 判断', '調査・計画', G_CONS, FN_CONSENT, '同意取得の要否と方式の判断',
       '利用規約などへの同意をログイン画面で取るか、アプリ側で取るか、取らないかを顧客に確認して決める',
       '決定記録。要否と、取る場合の場所と記録先が定まっている', 0.5, '基盤チーム', '基盤チーム', '業務ルール依存',
       '要件未確定。顧客回答待ち', '対象', '新規: 機能追加', 'F-AUTH-28', state='要件確認'),
]
for r in new_bd: addrow(BD, bd, r, 'ID', KEY)
# HB-F-AUTH-09 は機能名の先頭に置きたいので並べ直し（同じ機能名の中で HB-F → HE → HI の順）
def reorder_link():
    ids = ['HB-F-AUTH-09', 'HE-23', 'HI-11']
    rows = [next(r for r in bd if r['ID'] == i) for i in ids]
    for r in rows: bd.remove(r)
    last = max(i for i, r in enumerate(bd) if r['機能グループ'] == G_FED and r['機能名'] != FN_LINK)
    for k, r in enumerate(rows): bd.insert(last + 1 + k, r)
reorder_link()

# ================================================================ 3. WBS(詳細設計_製造)
def dmrow(ID, cls, grp, fn, item, desc, dd='', mk='', note=''):
    return {'ID': ID, '分類': cls, '機能グループ': grp, '機能名': fn, '項目': item, '概要・完了定義': desc,
            '詳細設計 人日': fmt(dd) if dd != '' else '', '製造 人日': fmt(mk) if mk != '' else '', '内訳': note}
for ID in ['DDG-01', 'MKA-01', 'MKJ-01']:
    setv(DM, dm, 'ID', ID, '機能名', FN_HAND)
setv(DM, dm, 'ID', 'DDG-01', '概要・完了定義', 'どこまで作って渡すか・渡した後の責任の持ち方（D-21 責任表）・初期状態に何を入れるかが確定し、引き渡し仕様書として 1 冊になっている')
new_dm = [
 dmrow('DDB-18', 'DD-B 機能の詳細設計', G_FED, FN_LINK, 'Keycloak-IdP 接続の詳細設計', '共有エントリの定義項目・属性の写し方（amr → 追加認証済みの印）・login_hint の渡し方・ログアウト連鎖の設定が実装できる粒度で書かれている', dd=2),
 dmrow('DDE-11', 'DD-E つなぎ目（IF）の詳細設計', G_FED, FN_LINK, '接続仕様の実装レベル定義（Keycloak-IdP 側へ渡す設定値）', 'Keycloak-IdP 側の Client・返す項目・セッション上限（12 時間）・経路の設定値が一覧で確定し、アプリチームへ渡っている', dd=1.5),
 dmrow('DDI-10', 'DD-I 単体試験の仕様', G_FED, FN_LINK, '単体試験仕様: Keycloak-IdP 接続', '初回・2 回目（Keycloak-IdP を呼ばない）・追加認証済みの印・ログアウト連鎖・上限時間の観点と期待結果が定義されている', dd=1),
 dmrow('MKA-20', 'MK-A 環境・基盤の構築', G_FED, FN_LINK, 'Keycloak-IdP への閉域経路の構築（Keycloak-Broker 側）', '閉域接続（PrivateLink）の受け口と名前解決が作られ、Keycloak-IdP 側と疎通する', mk=3, note='経路2+名前解決1'),
 dmrow('MKB-30', 'MK-B Keycloak-Brokerの設定・構築', G_FED, FN_LINK, 'Keycloak-IdP 接続の設定（共有エントリ・写し込み・ログアウト連鎖）', '共有エントリが登録され、識別子が引き継がれ、追加認証の結果が写り、ログアウトが連鎖する', mk=3),
 dmrow('MKI-19', 'MK-I 単体試験の実施', G_FED, FN_LINK, '単体試験: Keycloak-IdP 接続', '試験仕様どおりに実施し、不具合が是正されている', mk=2),
 dmrow('DDB-19', 'DD-B 機能の詳細設計', G_OPS, FN_OPS, '運用者認証と権限モデルの実装設計', 'WebAuthn の必須化・権限の 2 状態・昇格と失効の手順・記録が実装できる粒度で書かれている', dd=1.5),
 dmrow('MKB-31', 'MK-B Keycloak-Brokerの設定・構築', G_OPS, FN_OPS, '運用者アカウントと権限モデルの構築', 'パスワードだけでは入れず、常時の全権が無く、昇格と失効が動き記録される', mk=2),
 dmrow('DDF-05', 'DD-F 定期処理の詳細設計', G_LIFE, FN_BAT01, '自動停止の実装仕様', '対象の抽出条件・除外条件・実行間隔・記録が確定している', dd=1),
 dmrow('MKF-06', 'MK-F 定期処理の実装', G_LIFE, FN_BAT01, '自動停止の実装', '90 日ログインの無い対象ユーザだけが止まり、除外対象は止まらず、記録が残る', mk=1.5),
 dmrow('MKA-21', 'MK-A 環境・基盤の構築', G_OPS, FN_KCUPD, '依存の検査・イメージ署名・部品一覧の組み込み', '検査と署名が自動で通り、署名の無いイメージは配置できず、部品一覧が出せる', mk=2),
 dmrow('DDG-14', 'DD-G 基盤構成の実装設計', G_DET, FN_ITDR, '不正兆候の検知の実装設計', '検知の条件・集計の単位・閾値・通知先が実装できる粒度で書かれている', dd=1),
 dmrow('MKH-07', 'MK-H 監視・運用の構築', G_DET, FN_ITDR, '不正兆候の検知の構築', '兆候が検出され、通知が届く', mk=2),
 dmrow('DDE-12', 'DD-E つなぎ目（IF）の詳細設計', G_INT, FN_ADMAPI, '管理 API の内部公開の実装仕様', '経路・呼び出し元の資格・許す操作の範囲・記録の項目が実装できる粒度で書かれている', dd=1.5),
 dmrow('MKB-32', 'MK-B Keycloak-Brokerの設定・構築', G_INT, FN_ADMAPI, '管理 API の内部公開の構築', '内部経路からだけ呼べ、許した操作だけが通り、記録が残る', mk=2),
]
for r in new_dm: addrow(DM, dm, r, 'ID', KEY)

# ================================================================ 4. WBS(テスト)
def tsrow(k, ID, grp, fn, item, view, days, req, pre):
    return {'区分': k, 'ID': ID, '機能グループ': grp, '機能名': fn, 'テスト項目': item, 'テスト観点': view, '人日': fmt(days), '対応要件': req, '前提': pre}
setv(TS, ts, 'ID', 'IT-03', '機能名', FN_HAND)
setv(TS, ts, 'ID', 'IT-03', '対応要件', 'NFR-OPS-012')
setv(TS, ts, 'ID', 'IT-13', '対応要件', 'NFR-OPS-013')
setv(TS, ts, 'ID', 'SEC-09', '対応要件', 'NFR-SEC-014・022 / NFR-OPS-006')
setv(TS, ts, 'ID', 'SEC-06', '対応要件', 'NFR-SEC-001・002・003')
setv(TS, ts, 'ID', 'ST-18', '対応要件', 'FR-USER-006 / FR-SSO-009・010 / NFR-SEC-008')
setv(TS, ts, 'ID', 'DR-02', 'テスト観点', '切替でログインし直しが要ることが設計どおり（別地域再構築のため状態は引き継がない）／発行済みのJWTが切替先で検証できる／署名鍵が切替先にも揃っている')
new_ts = [
 tsrow('A 結合', 'IT-16', G_FED, FN_LINK, 'Keycloak-IdP とのつなぎ目', '閉域経路で接続情報と署名鍵が取れる／識別子が引き継がれ再入力が要らない／追加認証の結果が写る／Keycloak-IdP 側がエラーを返したときの表示／2 回目以降は Keycloak-IdP を呼ばない', 4, 'FR-FED-015', 'アプリチームの Keycloak-IdP が検証環境で起動し、接続仕様（HE-23）が合意されていること'),
 tsrow('A 結合', 'IT-17', G_INT, FN_ADMAPI, '管理 API の内部到達と権限範囲', '内部経路から呼べる／外部から呼べない／許した操作だけ通る／範囲外の操作が拒否され記録される', 2, 'FR-INT-006 / FR-SSO-010 / FR-USER-001', 'システム間 JWT の実装が完了していること'),
 tsrow('B 総合', 'ST-28', G_FED, FN_LINK, '顧客IdP を持たない顧客のログインの一連', '初回ログインでユーザが作られる／2 回目は入り直さずに使える／ログアウトで Keycloak-IdP 側の状態も消える／上限時間（12 時間）で両方切れる／Keycloak-IdP 側で止めた人が次の認証で入れない', 3, 'FR-FED-015 / FR-USER-006 / FR-SSO-005', 'A 結合（IT-16）が完了していること'),
 tsrow('B 総合', 'ST-29', G_LIFE, FN_BAT01, '長期未使用者の自動停止', '90 日ログインの無い対象ユーザが止まる／除外対象（Keycloak-IdP 収容・顧客システム連携）は止まらない／止めた記録が残る／再ログインで条件どおり再開する', 1.5, 'FR-USER-013', '自動停止の実装が完了していること'),
 tsrow('F セキュリティ', 'SEC-10', G_OPS, FN_OPS, '運用者アカウントの保護', 'パスワードだけでは入れない／常時の全権が付いていない／昇格が記録され期限で失効する／緊急時アクセスの使用が通知される／棚卸しで不要なアカウントが検出される', 2, 'NFR-SEC-021', '運用者アカウントと権限モデルの構築が完了していること'),
 tsrow('G 運用', 'OP-12', G_DET, FN_ITDR, '不正兆候の検知と通知', '失敗の急増で通知が届く／同一送信元の連続試行で通知が届く／誤検知が運用に耐える頻度／通知から初動手順（G-1.3）につながる', 1.5, 'NFR-SEC-023', '不正兆候の検知の構築が完了していること'),
]
for r in new_ts:
    log(TS, r['ID'], '追加', '—', '', r['テスト項目'])
    last = max(i for i, x in enumerate(ts) if x['区分'] == r['区分']); ts.insert(last + 1, r)

# ================================================================ 5. 要件マッピング
COL_IDP = 'Keycloak-IdP 側'
if COL_IDP not in H_RM: H_RM.append(COL_IDP)
def rm_get(ID): return next(r for r in rm if r['要件ID'] == ID)
def rm_set(ID, **kw):
    for c, v in kw.items(): setv(RM, rm, '要件ID', ID, c, v)
def cells(ID, a='', b='', c='', d=''):
    rm_set(ID, **{'① 基本設計': a, '② 詳細設計': b, '③ 製造': c, '④ テスト': d})
def sub(ID, col, old, new):
    r = rm_get(ID); v = r[col].split(); v = [new if x == old else x for x in v]
    rm_set(ID, **{col: ' '.join(sorted(set(v)))})
def addcell(ID, col, *ids):
    r = rm_get(ID); v = set(r[col].split()) | set(ids); rm_set(ID, **{col: ' '.join(sorted(v))})
def rmcell(ID, col, *ids):
    r = rm_get(ID); v = set(r[col].split()) - set(ids); rm_set(ID, **{col: ' '.join(sorted(v))})

# 5-1 決定 4: ROSA 引き渡し行を機能要件から外す
ST_IDP = 'アプリ側で実施（Keycloak-IdP 側。本基盤は ROSA の引き渡しまで＝NFR-OPS-012）'
for ID in ['FR-AUTH-001', 'FR-AUTH-009', 'FR-AUTH-010', 'FR-AUTH-012', 'FR-USER-004', 'NFR-SEC-009']:
    cells(ID); rm_set(ID, 状況=ST_IDP)
rm_set('FR-AUTH-001', 概要='ID とパスワードで直接ログインできること。顧客IdP を持たない顧客のユーザは Keycloak-IdP（アプリ責務）、本基盤の運用者は Keycloak-Broker（NFR-SEC-021）で満たす')
# 5-2 矛盾の修正
rm_set('FR-AUTH-011', 状況='アプリ側で実施（Keycloak-IdP 側）', 担当の理由='パスワードのロックは Keycloak-IdP 側（アプリ）。Keycloak-Broker はパスワードを持たないため、本基盤側の対策は NFR-SEC-010（実在推測の防止・試行回数の制限）で扱う'); cells('FR-AUTH-011')
rm_set('FR-FED-012', 構築場所='Keycloak-Broker', 担当='インフラ',
       担当の理由='追加認証そのものは顧客IdP／Keycloak-IdP の責務。Keycloak-Broker 側は追加認証済みの印（amr）を取り込み、二重に求めない設定を持つ',
       状況='全工程あり')
cells('FR-FED-012', 'HB-F-AUTH-05 HB-F-AUTH-09 HE-14 HE-23', 'DDB-01 DDB-18', 'MKB-02 MKB-30', 'RI-01 ST-04 ST-28')
for ID, col, new in [('FR-SSO-003', '① 基本設計', 'GD-22'), ('FR-AUTHZ-007', '① 基本設計', 'GD-16 GD-18'),
                     ('FR-INT-007', '① 基本設計', 'GD-16 GD-18'), ('NFR-PERF-003', '① 基本設計', 'GD-16 GD-18')]:
    rm_set(ID, **{col: new})
rm_set('FR-AUTHZ-007', 項目='API 入口での JWT 検証（アプリ側の認可統合）', 概要='API の入口でアプリが JWT を検証して可否を判断できること（ガイドで示す。Lambda Authorizer は PoC 時の実装名）')
rm_set('FR-INT-007', 項目='API 入口での JWT 検証との統合', 概要='API の入口で JWT を検証する仕組み（API Gateway 等）と組み合わせられること（ガイドで示す）')
rm_set('NFR-PERF-003', 項目='API 入口での JWT 検証の応答時間（アプリ側）', 概要='API の入口での判定が目標時間に収まること。署名鍵の一時保持（GD-18）が前提')
rm_set('NFR-SEC-011', 要件実現対象='対象', 構築場所='その他', 担当='他組織', 担当の理由='WAF は境界を管理する他組織が持つ。本基盤は要求仕様（HK-10）を出し、受入確認（SEC-05）を行う',
       状況='他組織で実施（本基盤は要求仕様と受入確認）')
cells('NFR-SEC-011', 'HG-08 HK-10', '', 'MKA-04', 'IT-11 SEC-05')
rm_set('NFR-SEC-012', 要件実現対象='対象', 構築場所='その他', 担当='他組織', 担当の理由='同上。DDoS 対策は境界側の責務、本基盤は要求仕様と受入確認',
       状況='他組織で実施（本基盤は要求仕様と受入確認）')
cells('NFR-SEC-012', 'HG-08 HK-10', '', 'MKA-04', 'SEC-05')
rm_set('NFR-SEC-018', 担当の理由='署名鍵の公開先は公開のまま、流量制限は境界（他組織）に要求する'); addcell('NFR-SEC-018', '① 基本設計', 'HK-10')
rm_set('FR-FED-013', 項目='ログイン画面での顧客IdP への振り分け（HRD）', 概要='ログイン画面で入力した識別子から顧客IdP を自動で判定して送ること。顧客IdP の一覧は見せない。1 顧客に複数ある場合のみ選ばせる')
rm_set('FR-ADMIN-007', 概要='監査の記録を閲覧できること。参照は全体の共通基盤側で行い、本基盤に照会画面は作らない（本基盤は出力と集約まで）')
rm_set('FR-SSO-009', 概要='発行済みの JWT を強制的に使えなくできること。セッションとリフレッシュトークンは即時失効、アクセストークンは署名のみで検証されるため最大 30 分は残る（契約説明に明記）')
rm_set('NFR-SEC-008', 概要='発行済みの資格を失効させられること（アクセストークンの残存 30 分は FR-SSO-009 と同じ）')
rm_set('FR-SSO-010', 状況='アプリ側で実施（本基盤にも 4 工程あり）', 担当の理由='管理画面からの操作。Keycloak-Broker は管理 API の内部公開（F-INT-14）で受け口を提供する')
cells('FR-SSO-010', 'HE-24', 'DDE-12', 'MKB-32', 'IT-17')
rm_set('FR-USER-001', 状況='アプリ側で実施（本基盤にも 4 工程あり）', 担当の理由='管理画面はアプリ。Keycloak-Broker は管理 API の内部公開（F-INT-14）で受け口を提供する')
cells('FR-USER-001', 'HE-24', 'DDE-12', 'MKB-32', 'IT-17')
addcell('FR-INT-006', '① 基本設計', 'HE-24'); addcell('FR-INT-006', '② 詳細設計', 'DDE-12'); addcell('FR-INT-006', '③ 製造', 'MKB-32'); addcell('FR-INT-006', '④ テスト', 'IT-17')
rm_set('FR-INT-006', 担当の理由='Keycloak 標準の管理 API。内部経路・呼び出し元の資格・許す操作の範囲を本基盤が決める（F-INT-14）')
rm_set('FR-USER-006', 概要='ユーザを一時的に使えなくする／戻せること。Keycloak-IdP 側で止めたユーザの Keycloak-Broker 側の写しは伝播しない。残存は Keycloak-Broker のセッション上限（12 時間）で受容（2026-09-07 決定）')
rm_set('FR-USER-011', 担当の理由='保持と消去の方針は本基盤で決める。消去の対象は Keycloak-Broker・Keycloak-IdP（アプリ）・権限データ（アプリ）・共通ログ基盤にまたがるため、HK-07 は横断の手順とする')
rm_set('NFR-COMP-009', 担当の理由='同上。本人からの請求は本基盤が窓口になり、Keycloak-IdP 側と権限データ側（アプリ）へ依頼する')
rm_set('NFR-PERF-006', 項目='流量制限（同時受付数の上限）', 概要='過大な要求を受けたときに Keycloak-Broker 側で流量を絞れること（API Gateway は使わない。境界側の流量制限は NFR-SEC-011）')
rm_set('NFR-SCL-004', 概要='顧客IdP を追加してから使えるまでの時間が目標に収まること。境界側の外向き許可の追加（他組織、当日〜翌日）を含む')
rm_set('NFR-OPS-011', 概要='顧客を追加してから使えるまでの時間を約束できること。境界側の外向き許可の追加（他組織、当日〜翌日）を含む')
rm_set('NFR-COST-006', 状況='確定（RHBK は ROSA に内包され追加費用なし。P-01）'); cells('NFR-COST-006')
rmcell('NFR-COMP-006', '④ テスト', 'SEC-06')
rmcell('FR-USER-007', '① 基本設計', 'HB-F-PROV-07')
rm_set('FR-FED-001', 担当の理由='Auth0 は PoC の代替。Phase 1 の契約対象 IdP かは要確認（Entra が Must、Okta が Should、Google が Could）')
rm_set('NFR-SEC-005', 概要='更新用の資格の有効期限が定められていること。設定上限は 30 日だが、実効はセッションの上限（12 時間）に従属する')
rm_set('FR-SSO-008', 概要='ログイン状態が切れるまでの時間を設定できること。無操作 1 時間・上限 12 時間（2026-09-07 更新、旧 24 時間）')
rm_set('NFR-SEC-019', 項目='内部通信の認証（idm-api → 管理 API、Keycloak-Broker → Keycloak-IdP）', 概要='内部の呼び出しでも相手を確認すること。管理 API は内部経路と資格で、Keycloak-IdP へは閉域の単方向接続で確認する')
addcell('NFR-SEC-019', '① 基本設計', 'HE-23', 'HE-24'); addcell('NFR-SEC-019', '④ テスト', 'IT-16', 'IT-17')
rm_set('FR-MFA-009', 担当の理由='顧客の管理者分は Keycloak-IdP（アプリ）。本基盤運用者分は NFR-SEC-021 で本基盤が満たす')
rm_set('NFR-DR-003', 概要='別地域へ切り替える方式が定まっていること。現行の方向は手動・大阪で作り直し（復旧方式の決定 D-18.2 待ち。顧客希望 RTO 1 日との差は D-18.1 で明示）')
rm_set('NFR-DR-008', 要件実現対象='対象外', 構築場所='—', 担当='—', 担当の理由='別地域で作り直す方式ではログイン状態を引き継げない。再ログイン前提を DR-02 で確認する', 状況='Phase 1 では作らない（再ログイン前提。DR-02 で確認）')
cells('NFR-DR-008', '', '', '', 'DR-02')
rm_set('NFR-AVL-001', 担当の理由='顧客IdP を持たない顧客のログインは Keycloak-IdP（アプリ運用）の稼働にも依存する。約束する稼働率の範囲と除外条件を HK-02 で明示する')
# 5-3 追加
def rm_new(ID, kind, pri, tgt, place, owner, why, item, desc, a, b, c, d, st, idp):
    row = {'要件ID': ID, '種別': kind, '優先度': pri, '要件実現対象': tgt, '構築場所': place, '担当': owner, '担当の理由': why, '項目': item, '概要': desc,
           '① 基本設計': a, '② 詳細設計': b, '③ 製造': c, '④ テスト': d, '状況': st, COL_IDP: idp}
    log(RM, ID, '追加', '—', '', item)
    # 同じ接頭辞（FR-FED 等）の最後の行の後ろに入れる
    key = lambda s: re.match(r'^N?FR-[A-Z]+', s).group(0)
    idx = [i for i, r in enumerate(rm) if key(r['要件ID']) == key(ID)]
    rm.insert(idx[-1] + 1, row)
rm_new('FR-FED-015', '機能要件', 'Must', '対象', 'Keycloak-Broker', 'インフラ',
       '顧客IdP を持たない顧客のユーザは全員ここを通る。Keycloak-IdP 側の Client・Realm 設定は要求仕様（HE-23）でアプリチームへ渡す',
       'Keycloak-Broker ⇄ Keycloak-IdP 連携',
       '顧客IdP を持たない顧客のユーザを Keycloak-Broker から Keycloak-IdP へ委譲してログインさせられること。識別子の引き継ぎ・追加認証結果の取り込み・ログアウト連鎖・セッション上限の同値（12 時間）・閉域の単方向接続を含む',
       'HB-F-AUTH-09 HE-23 HI-11', 'DDB-18 DDE-11 DDI-10', 'MKA-20 MKB-30 MKI-19', 'IT-16 ST-28', '全工程あり',
       'アプリ（要求仕様どおりに broker-rp Client と Realm 設定を作る）')
rm_new('FR-AUTH-016', '機能要件', 'TBD', '対象', 'Keycloak-Broker', 'インフラ', '要否未確定。顧客回答待ち（D-22 で判断のみ計上）',
       '利用規約への同意取得と記録', '利用規約などへの同意を取り、いつ誰がどの版に同意したかを記録できること',
       'D-22', '', '', '', '要件確認（判断のみ計上）', '—')
rm_new('FR-USER-013', '機能要件', 'Should', '対象', 'Keycloak-Broker', 'インフラ',
       '顧客IdP 経由で自動作成したユーザだけが対象。Keycloak-IdP 収容ユーザはアプリ側の判断。要否は B-JIT-LC-1 で最終確認',
       '長期未使用ユーザの自動停止', '90 日ログインの無いユーザを自動で止められること',
       'HB-F-BAT-01', 'DDF-05', 'MKF-06', 'ST-29', '全工程あり', 'アプリ（Keycloak-IdP 収容ユーザ分は任意）')
rm_new('NFR-SEC-010-2', '非機能要件', 'TBD', '対象', 'Keycloak-IdP', 'アプリ', 'パスワードを持つのは Keycloak-IdP 側',
       '侵害クレデンシャル検出', '流出したパスワードの使用を拒否できること', '', '', '', '', 'アプリ側で実施（Keycloak-IdP 側）', 'アプリ（主体）')
rm_new('NFR-SEC-021', '非機能要件', 'Must', '対象', 'Keycloak-Broker', 'インフラ',
       'Keycloak-Broker にローカルで残る唯一の人が運用者。ADR-040 Phase 1 α（P1-04 / P1-08 / P1-09）',
       '運用者アカウントと権限の保護', '本基盤運用者の認証を WebAuthn 必須とし、常時の全権付与を禁止し、緊急時アクセスと定期棚卸しを定めること',
       'G-1.6 G-5.6 HG-09', 'DDB-19 DDG-11', 'MKA-17 MKB-31', 'OP-09 SEC-10', '全工程あり', '—')
rm_new('NFR-SEC-022', '非機能要件', '推奨値あり', '対象', 'Keycloak-Broker', 'インフラ', 'ADR-046 Phase 1 = SLSA L2',
       'サプライチェーン対策（依存の検査・イメージ署名・部品一覧）', '自社拡張と実行イメージの依存を検査し、署名し、部品一覧（SBOM）を出せること',
       'HJ-06 HJ-22', 'DDH-02', 'MKA-21 MKC-05', 'SEC-09', '全工程あり', 'アプリ（Keycloak-IdP 側の実行イメージも同様に）')
rm_new('NFR-SEC-023', '非機能要件', '推奨値あり', '対象', 'Keycloak-Broker', 'インフラ', 'ADR-035 Phase 1a = 検知して通知するまで。自動遮断はしない',
       '不正兆候の検知', 'ログイン失敗の急増などの不正兆候を検知して通知できること',
       'HH-06', 'DDG-14', 'MKH-07', 'OP-12', '全工程あり', 'アプリ（パスワード側の兆候は Keycloak-IdP で検知）')
rm_new('NFR-OPS-012', '非機能要件', 'Must', '対象', 'Keycloak-IdP', 'インフラ',
       'ROSA の引き渡しまでが本基盤。以降の構築・運用はアプリ責務（D-21 責任表）',
       'Keycloak-IdP 側の構築・運用の責任分界', 'Keycloak-IdP 用の基盤（ROSA）をどこまで作って渡すか、渡した後の非機能を誰が持つかが合意されていること',
       'D-21 HJ-20', 'DDG-01', 'MKA-01 MKJ-01', 'IT-03', '全工程あり', '本基盤（ROSA 引き渡しまで）→ アプリ（引き渡し後の非機能すべて）')
rm_new('NFR-OPS-013', '非機能要件', '推奨値あり', '対象', 'Keycloak-Broker', 'インフラ', '—',
       '環境構成（本番 / 検証 / 開発）', '環境ごとの構成差分と、検証環境に本番データを入れない規律が定まっていること',
       'HH-05', 'DDG-05', 'MKA-07 MKA-08', 'IT-13 TE-01 TE-02', '全工程あり', 'アプリ（Keycloak-IdP 側の環境はアプリが用意）')
# 5-4 Keycloak-IdP 側 列（追加行以外）
IDP_NFR = 'アプリ（Keycloak-IdP 側でも同じ要件を満たす。本基盤は ROSA の引き渡しまで）'
for r in rm:
    if r.get(COL_IDP): continue
    if r['要件実現対象'] == '対象外' or r['要件ID'].startswith('NFR-COST'): r[COL_IDP] = '—'
    elif r['構築場所'] == 'Keycloak-IdP': r[COL_IDP] = 'アプリ（主体）'
    elif r['種別'] == '非機能要件' and r['構築場所'] == 'Keycloak-Broker': r[COL_IDP] = IDP_NFR
    elif r['要件ID'] in ('FR-SSO-005', 'FR-SSO-008', 'FR-USER-006', 'FR-FED-008', 'FR-FED-009', 'FR-AUTHZ-006', 'FR-USER-002'):
        r[COL_IDP] = 'アプリ（Keycloak-IdP 側の同じ設定は接続仕様 HE-23 に従う）'
    else: r[COL_IDP] = '—'
log(RM, '（全行）', '列追加', COL_IDP, '', 'Keycloak-IdP 側で誰が満たすか（アプリ／本基盤／—）')

# ================================================================ 6. 集計の再計算
pf = derive_fl(bd, fl)
for f in fl:
    n, a, b = pf[f['機能ID']]
    for c, v in [('行数', str(n)), ('人日', fmt(a)), ('うち対象', fmt(b))]:
        if num(f[c]) != num(v): f[c] = v
pg = derive_fg(bd, fg)
for g in fg:
    n, a = pg[g['機能グループ']]
    g['行数'] = str(n); g['人日'] = fmt(a)
sm = derive_sm(bd, dm, ts, fl)

# ================================================================ 7. 書き戻し
save('SHEET_機能名一覧.tsv', H_FL, fl); save('SHEET_機能グループ一覧.tsv', H_FG, fg); save('SHEET_基本設計.tsv', H_BD, bd)
save('SHEET_詳細設計_製造.tsv', H_DM, dm); save('SHEET_テスト.tsv', H_TS, ts); save('SHEET_サマリ工程別.tsv', H_SM, sm)
save('SHEET_要件マッピング.tsv', H_RM, rm)
with open(P('SYNC_reqfix_2026-09-07.tsv'), 'w', encoding='utf-8', newline='') as fp:
    w = csv.writer(fp, delimiter='\t', lineterminator='\n'); w.writerow(['シート', 'ID', '種別', '列', '旧', '新'])
    for d in delta: w.writerow(d)

# ================================================================ 8. 検算
def tot(rows, col, cond=lambda r: True): return sum(num(r[col]) for r in rows if cond(r))
print('--- 検算')
print(f"基本設計: {len(bd)} 行 / 全量 {fmt(tot(bd,'人日'))} / 対象 {fmt(tot(bd,'人日',lambda r:r['スコープ']=='対象'))}")
print(f"詳細設計・製造: {len(dm)} 行 / 詳細設計 {fmt(tot(dm,'詳細設計 人日'))} / 製造 {fmt(tot(dm,'製造 人日'))}")
print(f"テスト: {len(ts)} 行 / {fmt(tot(ts,'人日'))}")
print(f"機能名一覧: {len(fl)} 行 / 機能グループ一覧: {len(fg)} 行 / サマリ: {len(sm)} 行 / 合計 {fmt(tot(sm,'合計'))}")
print(f"要件マッピング: {len(rm)} 行 / {len(H_RM)} 列")
print('状況:', dict(collections.Counter(r['状況'] for r in rm)))
print('担当:', dict(collections.Counter(r['担当'] for r in rm)))
print('Keycloak-IdP 側:', dict(collections.Counter(r[COL_IDP] for r in rm)))
# 参照整合
ids = {r['ID'] for r in bd} | {r['ID'] for r in dm} | {r['ID'] for r in ts}
bad = [(r['要件ID'], x) for r in rm for c in ['① 基本設計', '② 詳細設計', '③ 製造', '④ テスト'] for x in r[c].split() if x not in ids]
print('マッピングの参照切れ:', bad or 'なし')
dead = [r['要件ID'] for r in rm if 'HK-03' in r['① 基本設計']]
print('HK-03（廃止行）参照:', dead or 'なし')
names = {f['機能名'] for f in fl}
print('機能名がマスタに無い行:', [(s, r['ID']) for s, rows in [('①', bd), ('②③', dm), ('④', ts)] for r in rows if r['機能名'] not in names] or 'なし')
print('ID 重複:', [k for k, v in collections.Counter([r['ID'] for r in bd] + [r['ID'] for r in dm] + [r['ID'] for r in ts]).items() if v > 1] or 'なし')
print(f'差分 {len(delta)} 件 → SYNC_reqfix_2026-09-07.tsv')
