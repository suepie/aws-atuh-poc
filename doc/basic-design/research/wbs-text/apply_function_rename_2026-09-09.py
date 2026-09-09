#!/usr/bin/env python3
"""機能グループ・機能名の見直しを適用する（2026-09-09、N-1〜N-5 の回答を反映）。

決定:
  N-1 SCIM の送信元 = 顧客IdP のみ → 「顧客IdP からのユーザ情報の同期」
  N-2 機能名の製品名は残す         → §4.4（製品名を外す案）は適用しない
  N-3 機能グループの統合 4 件      → まとめて適用（24 → 20）
  N-4 機能名の統合                → 適用（97 → 88）。★タスクが 1 つも落ちないことを検算する
  N-5 主語の追加                  → まとめて適用

★最重要の不変条件（落ちたら異常終了する）:
  1. ①②③④ の行数が 1 行も変わらない
  2. ①②③④ の人日の合計が変わらない
  3. すべての WBS 行の 機能グループ / 機能名 が新しいマスタに存在する
  4. 機能名一覧の集計（行数・人日・うち対象）が WBS ① と一致する
"""
import csv, os, collections, sys

W = os.path.dirname(os.path.abspath(__file__)); P = lambda n: os.path.join(W, n)
def load(n):
    with open(P(n), encoding='utf-8', newline='') as fp:
        rd = csv.reader(fp, delimiter='\t'); h = next(rd)
        return h, [dict(zip(h, r + [''] * (len(h) - len(r)))) for r in rd if any(r)]
def save(n, h, rows):
    with open(P(n), 'w', encoding='utf-8', newline='') as fp:
        w = csv.writer(fp, delimiter='\t', lineterminator='\n'); w.writerow(h)
        for r in rows: w.writerow([r.get(c, '') for c in h])
num = lambda x: float(x) if str(x).strip() else 0.0
fmt = lambda x: str(int(x)) if float(x).is_integer() else str(x)

SHEETS = ['基本設計', '詳細設計_製造', 'テスト', 'サマリ工程別', 'API提供一覧', '機能名一覧', '機能グループ一覧']
H, D = {}, {}
for n in SHEETS: H[n], D[n] = load(f'SHEET_{n}.tsv')

# ---------------------------------------------------------------- 適用前の値（不変条件の基準）
def totals():
    bd, dm, ts = D['基本設計'], D['詳細設計_製造'], D['テスト']
    return {'①行': len(bd), '①全量': sum(num(r['人日']) for r in bd),
            '①対象': sum(num(r['人日']) for r in bd if r['スコープ'] == '対象'),
            '②③行': len(dm), '②': sum(num(r['詳細設計 人日']) for r in dm), '③': sum(num(r['製造 人日']) for r in dm),
            '④行': len(ts), '④': sum(num(r['人日']) for r in ts), 'API行': len(D['API提供一覧'])}
BEFORE = totals()
TASKS_BEFORE = {(n, r['ID']) for n in ['基本設計', '詳細設計_製造'] for r in D[n]} | {('テスト', r['ID']) for r in D['テスト']}

# ---------------------------------------------------------------- 1. 機能グループ（24 → 20）
GRP = {  # 旧 → 新
 'ログイン振り分け（HRD）': 'ログインの振り分け',
 'フェデレーションログイン': '顧客IdP 連携ログイン',
 'ローカルログイン（Keycloak-IdP 収容）': 'パスワードによるログイン',
 'パスワード・アカウント復旧': 'パスワードと復旧',
 '不正アクセス対策': 'ログイン口の保護',
 'セッション・ログアウト': 'セッションとログアウト',
 'ログイン画面・エラー画面': 'ログイン画面',
 '同意管理': 'ログイン画面',                              # 統合
 'ユーザ登録（顧客システム連携・SCIM）': 'ユーザ管理',        # 統合
 'ユーザ管理（管理画面・API）': 'ユーザ管理',
 '顧客IdP管理': '顧客IdP 管理',
 '権限管理': '認可・権限判定',                              # 統合
 'JWT の発行・交換': 'JWT の発行',
 'アプリ・外部連携': 'アプリ連携',
 '業務システム連携（ServiceNow）': '業務システムへの認証提供',
 'データ整合・突合': 'ユーザの停止・再開・消去',              # 統合
}
# 機能グループの並び順（新）
GORDER = ['ログインの振り分け', '顧客IdP 連携ログイン', 'パスワードによるログイン', '多要素認証', 'パスワードと復旧',
          'ログイン口の保護', 'セッションとログアウト', 'ログイン画面', 'ユーザ管理', 'ユーザ属性の統一',
          'ユーザの停止・再開・消去', '顧客・組織管理', '顧客IdP 管理', 'JWT の発行', '認可・権限判定',
          'アプリ連携', '業務システムへの認証提供', '監査・記録', '鍵・証明書管理', '監視・検知']

# ---------------------------------------------------------------- 2. 機能名（97 → 88）
# 統合: 旧機能名 → 生き残る機能ID
MERGE = {
 'SCIM 受信: ユーザの登録': 'F-PROV-03', 'SCIM 受信: ユーザの更新': 'F-PROV-03',
 'SCIM 受信: 削除通知（無効化へ読み替え）': 'F-PROV-03', 'SCIM 受信: ユーザの検索': 'F-PROV-03',
 'SCIM 受信: グループ連携': 'F-PROV-03',
 '追加認証（数字コード）': 'F-AUTH-10', '追加認証（生体・セキュリティキー）': 'F-AUTH-10',
 '追加認証の登録（数字コード）': 'F-AUTH-12', '追加認証の登録（生体・セキュリティキー）': 'F-AUTH-12',
 'ユーザの検索・一覧': 'F-ADM-01', 'ユーザの詳細参照': 'F-ADM-01',
 'ユーザの登録': 'F-ADM-03', 'ユーザの変更': 'F-ADM-03',
 'ユーザの利用可否の切替': 'F-ADM-05', 'ユーザの削除': 'F-ADM-05',
}
# 改名: 機能ID → (新機能名, 新しい概要 or None)
REN = {
 # §4.1 統合後の代表名
 'F-PROV-03': ('顧客IdP からのユーザ情報の同期',
   '顧客IdP から SCIM でユーザの登録・更新・削除通知・検索を受け取り、本基盤へ反映する。呼び出し口ごとの違いは提供 API 一覧で持つ。グループ連携は初期リリース対象外'),
 'F-AUTH-10': ('追加認証の利用', 'パスワードに加えて 2 つ目の要素で本人を確かめる。数字コードと生体・セキュリティキーの両方を含む'),
 'F-AUTH-12': ('追加認証の登録', '2 つ目の要素を初めて登録する流れ。数字コードと生体・セキュリティキーの両方を含む'),
 'F-ADM-01': ('ユーザの参照', '管理者が自分の顧客のユーザを検索・一覧表示し、1 人の詳細を参照する'),
 'F-ADM-03': ('ユーザの登録と変更', '管理者がユーザを新規に登録し、情報を変更する'),
 'F-ADM-05': ('ユーザの利用可否の切替・削除', '管理者がユーザを一時的に使えなくする／戻す。削除の求めもここで扱う（実際には消さずに使えない状態にする）'),
 # §4.2 主語を足す
 'F-AZ-08': ('別アプリ向け JWT への交換（Token Exchange）', 'あるアプリ向けに出した JWT を、別のアプリ向けの JWT に引き換える'),
 'F-BAT-07': ('顧客IdP・本基盤の証明書の期限監視', '顧客IdP の署名証明書と本基盤の署名証明書・TLS 証明書について、期限切れが近いものを検出して通知する'),
 'F-BAT-04': ('JWT 署名鍵の定期入れ替え', None),
 'F-BAT-05': ('アプリの接続用パスワードの定期入れ替え', None),
 'F-PROV-08': ('顧客IdP から受け取る属性の名前の統一', None),
 'F-INT-11': ('顧客IdP の接続情報の自動追随', None),
 'F-ADM-21': ('ユーザ一覧と操作記録のファイル出力', None),
 'F-BAT-03': ('本基盤とアプリの間のデータの突合', None),
 'F-AZ-01': ('アプリが使う権限情報の一括取得', None),
 'F-PROV-09': ('ユーザの登録経路の区分', None),
 'F-ADM-18': ('管理操作の記録の照会', None),
 'F-INT-08': ('不正なログインの兆候の検知', None),
 # §4.3 機能でないものを機能の名前に直す
 'F-AZ-10': ('アプリへの JWT 発行',
   'アプリへ渡す JWT を発行し、失効させ、有効性を確かめられるようにする。何を載せるか・要求できる範囲の定義はこの機能の設計作業（HJ-07）で行う'),
 'F-ADM-25': ('監査ログの出力と保管', None),
 'F-INT-14': ('アプリ向け管理 API の公開',
   'アプリのサーバから Keycloak-Broker の管理 API を呼べるようにする。到達経路・呼び出し元の資格・許してよい操作の範囲を決める'),
 'F-AUTH-29': (None, '本基盤が Keycloak-IdP 用の基盤（ROSA）をどこまで作って渡すか、渡した後の非機能を誰が持つかの取り決め。**機能ではなく合意事項**だが、作業の受け皿として機能名の位置に置く'),
}
# 機能グループの移動（機能ID → 新グループ）
GMOVE = {'F-AZ-10': 'JWT の発行'}

# ---------------------------------------------------------------- 3. 適用
fl = D['機能名一覧']
FID2NAME = {f['機能ID']: f['機能名'] for f in fl}
NAME2FID = {f['機能名']: f['機能ID'] for f in fl}
# 3-1 マスタ側: 統合で消える行を落とし、生き残りを改名
absorbed = {}                                   # 消える機能ID → 生き残り機能ID
for oldname, keep in MERGE.items():
    fid = NAME2FID[oldname]
    if fid != keep: absorbed[fid] = keep
newname = {}                                    # 旧機能名 → 新機能名
for f in fl:
    fid = f['機能ID']
    if fid in absorbed: continue
    nm = REN.get(fid, (None, None))[0] or f['機能名']
    newname[f['機能名']] = nm
for oldname, keep in MERGE.items():
    newname[oldname] = REN.get(keep, (None, None))[0] or FID2NAME[keep]

fl2 = []
for f in fl:
    if f['機能ID'] in absorbed: continue
    nm, desc = REN.get(f['機能ID'], (None, None))
    if nm: f['機能名'] = nm
    if desc: f['概要'] = desc
    f['機能グループ'] = GMOVE.get(f['機能ID'], GRP.get(f['機能グループ'], f['機能グループ']))
    fl2.append(f)
D['機能名一覧'] = fl2
NEWNAMES = {f['機能名'] for f in fl2}
NEWGRP = {f['機能グループ'] for f in fl2}

# 3-2 各シートの 機能グループ / 機能名 / 機能ID を付け替える
for n in ['基本設計', '詳細設計_製造', 'テスト', 'サマリ工程別', 'API提供一覧']:
    for r in D[n]:
        if r.get('機能ID') in absorbed: r['機能ID'] = absorbed[r['機能ID']]
        if r['機能名'] in newname: r['機能名'] = newname[r['機能名']]
        fid = r.get('機能ID')
        r['機能グループ'] = (GMOVE.get(fid) or GRP.get(r['機能グループ'], r['機能グループ']))
        # 機能名からグループを引き直す（移動した機能に追随させる）
        m = next((f for f in fl2 if f['機能名'] == r['機能名']), None)
        if m: r['機能グループ'] = m['機能グループ']

# ---------------------------------------------------------------- 4. 並べ替えと集計の再計算
order = {g: i for i, g in enumerate(GORDER)}
NFG = [f['機能グループ'] for f in fl2 if f['系統'] == '非機能']
for g in dict.fromkeys(NFG): order.setdefault(g, 100 + len(order))
for n in ['基本設計', '詳細設計_製造', '機能名一覧']:
    D[n].sort(key=lambda r: order.get(r['機能グループ'], 999))
forder = {f['機能名']: i for i, f in enumerate(D['機能名一覧'])}
for n in ['基本設計', '詳細設計_製造']:
    D[n].sort(key=lambda r: (order.get(r['機能グループ'], 999), forder.get(r['機能名'], 999)))

bd, dm, ts = D['基本設計'], D['詳細設計_製造'], D['テスト']
for f in D['機能名一覧']:
    rows = [r for r in bd if r['機能名'] == f['機能名']]
    f['行数'] = str(len(rows)); f['人日'] = fmt(sum(num(r['人日']) for r in rows))
    f['うち対象'] = fmt(sum(num(r['人日']) for r in rows if r['スコープ'] == '対象'))
# 機能グループ一覧を作り直す
gsum = []
for g in dict.fromkeys(f['機能グループ'] for f in D['機能名一覧']):
    src = next(x for x in D['機能グループ一覧'] if GRP.get(x['機能グループ'], x['機能グループ']) == g)
    rows = [r for r in bd if r['機能グループ'] == g]
    gsum.append({'機能グループ': g, '系統': src['系統'], '概要': src['概要'],
                 '行数': str(len(rows)), '人日': fmt(sum(num(r['人日']) for r in rows))})
D['機能グループ一覧'] = gsum
# サマリを作り直す
sm = []
for f in D['機能名一覧']:
    n = f['機能名']
    a = sum(num(r['人日']) for r in bd if r['機能名'] == n and r['スコープ'] == '対象')
    b = sum(num(r['詳細設計 人日']) for r in dm if r['機能名'] == n)
    c = sum(num(r['製造 人日']) for r in dm if r['機能名'] == n)
    d = sum(num(r['人日']) for r in ts if r['機能名'] == n)
    k = sum(1 for r in dm if r['機能名'] == n) + sum(1 for r in ts if r['機能名'] == n)
    if a + b + c + d > 0:
        sm.append({'機能グループ': f['機能グループ'], '機能名': n, '① 基本設計': fmt(a), '② 詳細設計': fmt(b),
                   '③ 製造': fmt(c), '④ テスト': fmt(d), '合計': fmt(a + b + c + d), '②③④ 行数': str(k)})
D['サマリ工程別'] = sm

# ---------------------------------------------------------------- 5. ★不変条件の検査
AFTER = totals()
errs = []
for k in ['①行', '①全量', '①対象', '②③行', '②', '③', '④行', '④', 'API行']:
    if BEFORE[k] != AFTER[k]: errs.append(f'{k}: {BEFORE[k]} → {AFTER[k]}')
lost = TASKS_BEFORE - ({(n, r['ID']) for n in ['基本設計', '詳細設計_製造'] for r in D[n]} | {('テスト', r['ID']) for r in D['テスト']})
if lost: errs.append(f'消えたタスク {len(lost)} 件: {sorted(lost)[:10]}')
NEWNAMES = {f['機能名'] for f in D['機能名一覧']}; NEWGRP = {f['機能グループ'] for f in D['機能名一覧']}
for n in ['基本設計', '詳細設計_製造', 'テスト', 'サマリ工程別', 'API提供一覧']:
    bad = [(r.get('ID') or r.get('機能ID'), r['機能名']) for r in D[n] if r['機能名'] not in NEWNAMES and r['機能名'] != '—']
    if bad: errs.append(f'{n}: マスタに無い機能名 {len(bad)} 件 {bad[:5]}')
    badg = [(r.get('ID'), r['機能グループ']) for r in D[n] if r['機能グループ'] not in NEWGRP and r['機能グループ'] != '—']
    if badg: errs.append(f'{n}: マスタに無い機能グループ {len(badg)} 件 {badg[:5]}')
dupe = [k for k, v in collections.Counter(f['機能名'] for f in D['機能名一覧']).items() if v > 1]
if dupe: errs.append(f'機能名の重複: {dupe}')
if errs:
    print('❌ 不変条件エラー'); [print('  -', e) for e in errs]; sys.exit(1)

# ---------------------------------------------------------------- 6. 保存
for n in SHEETS: save(f'SHEET_{n}.tsv', H[n], D[n])
with open(P('SYNC_funcrename_2026-09-09.tsv'), 'w', encoding='utf-8', newline='') as fp:
    w = csv.writer(fp, delimiter='\t', lineterminator='\n')
    w.writerow(['種別', '旧', '新', '備考'])
    for o, nn in GRP.items(): w.writerow(['機能グループ', o, nn, '統合' if list(GRP.values()).count(nn) > 1 else '改名'])
    for o, nn in sorted(newname.items()):
        if o != nn: w.writerow(['機能名', o, nn, '統合' if o in MERGE else '改名'])
    for a, b in sorted(absorbed.items()): w.writerow(['機能ID（統合で廃番）', a, b, f'{FID2NAME[a]} → 統合先へ'])

print('✅ 不変条件クリア')
print(f"① {AFTER['①行']} 行 全量 {fmt(AFTER['①全量'])} / 対象 {fmt(AFTER['①対象'])}")
print(f"②③ {AFTER['②③行']} 行 ② {fmt(AFTER['②'])} / ③ {fmt(AFTER['③'])} ／ ④ {AFTER['④行']} 行 {fmt(AFTER['④'])}")
print(f"機能名一覧 {len(D['機能名一覧'])} 行（機能系 {sum(1 for f in D['機能名一覧'] if f['系統'] != '非機能')}）"
      f" / 機能グループ {len(D['機能グループ一覧'])}（機能系 {len([g for g in D['機能グループ一覧'] if g['系統'] != '非機能'])}）"
      f" / サマリ {len(D['サマリ工程別'])} 行 合計 {fmt(sum(num(r['合計']) for r in D['サマリ工程別']))}")
print(f'廃番になった機能ID {len(absorbed)} 件: {sorted(absorbed)}')
print(f"改名 {sum(1 for o, n2 in newname.items() if o != n2)} 件 → SYNC_funcrename_2026-09-09.tsv")
