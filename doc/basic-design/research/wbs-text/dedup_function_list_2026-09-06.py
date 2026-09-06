#!/usr/bin/env python3
"""機能名一覧の重複解消（2026-09-06）。

- ユーザーが Excel「機能名一覧」で付けた M 列「不要または重複」と並び順・改名・基盤/アプリ列を正とする
- 「／」複合の機能名を全廃し、WBS 行を 1 つの機能名に付け替える（FUNCMAP）
- 不要とされた機能名の WBS 行も付け替える
- 出力: SYNC_funcmap.tsv（WBS 行の I/J/T 付け替え）, SYNC_func.tsv（機能名一覧 v2・ユーザー配置）, SYNC_group.tsv（機能グループ一覧 v2）,
        ../function-list-dedup-2026-09-06.md（1 件ずつの見直し結果）
"""
import csv, json, os, collections

W = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(W, '..')
BODY = ['AG_概要_成果物.tsv', 'H-other_概要_成果物.tsv', 'HB-F_概要_成果物.tsv', 'HB-other_廃止行_概要_成果物.tsv', 'HL-GD_概要_成果物.tsv']
rows = collections.OrderedDict(); file_of = {}; hdr = None
for f in BODY:
    rd = list(csv.reader(open(os.path.join(W, f), encoding='utf-8'), delimiter='\t')); hdr = rd[0]
    for r in rd[1:]:
        if r and r[0]:
            d = dict(zip(hdr, r)); rows[d['WBS ID']] = d; file_of[d['WBS ID']] = f
eff = {r[0]: float(r[1]) for r in list(csv.reader(open(os.path.join(W, 'SYNC_effort.tsv'), encoding='utf-8'), delimiter='\t'))[1:]}
sheet = json.load(open('/tmp/funcsheet.json'))  # ユーザー編集後の機能名一覧（行順どおり）

# ---------- 機能名の正規化（ユーザーの改名を SSOT に取り込む） ----------
RENAME = {  # 旧機能名 -> 新機能名（機能ID は不変）
    'ローカルログイン': 'ローカルユーザー管理',
    '顧客認証システムへのログイン委譲': '顧客認証システムへのログイン委譲_OIDC',
    '顧客認証システムへのログイン委譲（旧方式）': '顧客認証システムへのログイン委譲_SAML',
    '初回ログイン時の利用者控え作成': 'ブローカー側のシャドウユーザ作成',
    'ログイン後の属性取り込み': 'ログイン後の属性取り込み_SCIM',
    '内部2段構えの認証連携': 'Broker-KeycloakとIdP-Keycloakの連携',
    '横断（顧客の解約運用）': '顧客の解約運用',
    '横断（ログイン画面）': 'IdP-Keycloakのログイン画面',
}
GROUP_OF = {  # ユーザーのグループ変更
    '顧客の解約運用': '運用', '横断（法令対応）': '運用', '横断（災害対策）': '運用', '横断（同意管理）': '運用',
    'IdP-Keycloakのログイン画面': 'ログイン画面',
}
X = '横断'; XA = '横断（全機能共通）'
# ---------- WBS 行の付け替え: WBS ID -> (機能グループ, 機能名, 機能ID) ----------
G = {}  # 機能名 -> (系統, グループ, 機能ID) をユーザーの一覧から
for r in sheet:
    if r[2] and (r[12] or '') in ('', '追加') and '／' not in str(r[2]):
        G[r[2]] = (r[0], r[1], r[3] or '横断')
G['sorryページ(ブローカー)'] = ('認証', 'エラー画面', 'F-AUTH-23'); G['sorryページ(アプリ)'] = ('認証', 'エラー画面', 'F-AUTH-24')
def T(name):
    s, g, fid = G[name]; return (g, name, fid)

FUNCMAP = {}
def M(ids, name):
    for i in ids.split(): FUNCMAP[i] = T(name)
# 不要または重複（ユーザー指定）
M('HC-04c HB-F-AUTH-04', '接続先の自動振り分け')                       # F-AUTH-04 選択画面 → HRD の一部
M('HG-06 HB-F-AZ-09', '操作記録の照会(アプリ)'); M('D-7a', '不正兆候の検知')   # F-AZ-09 権限判定の記録
M('HB-F-INT-06', '初回ログイン者の識別子通知')                          # F-INT-06（対象外）
M('HB-F-INT-05', '停止の確実な伝播')                                     # F-INT-05（対象外）
M('HB-F-INT-10', '定期的な擬似ログインによる障害検知')                  # F-INT-10
M('A-14 HB-F-INT-12 GD-36', 'アプリへの変更通知')                        # F-INT-12 CAEP
M('HB-F-BAT-06', 'システム用アカウントの台帳管理')                       # F-BAT-06
M('A-2.1 A-2.3 A-2.4 A-2.2', XA)                                          # 横断（自社拡張全般）
M('A-16', 'IdP-Keycloakのログイン画面')                                  # ブランド別表示（対象外）
M('D-15 D-18.1 D-18.2 D-18.3 D-18.4 D-19 HJ-17 HJ-18 HJ-19 HH-05', XA)   # 該当なし
M('D-20', '横断（法令対応）')
M('E-4a E-4b E-4c E-4d E-4e HD-03', XA)                                  # 横断（ログイン処理全般）
M('HB-15 HB-16 HB-17 HK-03 GD-11', XA)                                   # 代表シナリオ・該当なし
M('HF-01 HF-06 HF-07', '横断（定期処理共通）')                           # 定期実行処理全般
M('HE-09', '顧客システムからの利用者登録')                               # 顧客システムからの利用者情報受け取り
M('HF-05', '署名鍵の定期入れ替え')                                       # 鍵・証明書・権限見直しの定期処理
# 「／」複合 → 主となる 1 機能
M('A-6.3', '顧客認証システムへのログイン委譲_OIDC'); M('A-6.2', '顧客認証システムへのログイン委譲_SAML')
M('D-16.1 D-16.2 D-16.3', '業務システムへの認証提供')
M('D-17.1 D-17.5 HA-09', XA)
M('E-8', '連続失敗時の一時締め出し'); M('D-14', '利用者の存在推測の防止')
M('D-12', '証明書期限の監視'); M('G-1.5', '署名鍵の定期入れ替え')
M('HD-05 HJ-08', '項目名の変換・統一'); M('HJ-04', '初回ログイン時の自動登録')
M('HC-05b-1', '利用者の検索・一覧'); M('HC-05b-2', '利用者の詳細参照'); M('HC-05b-3', '利用者の登録'); M('HC-05b-4', '利用者の変更')
M('HC-05b-5', '利用者の利用可否の切替（管理者操作）'); M('HC-05b-6', 'パスワード初期化（管理者）'); M('HC-05b-7', '利用者の招待'); M('HC-05b-8', '利用者の一括登録')
M('HC-05c-1 HD-08', '使えるアプリの設定'); M('HC-05c-2', 'アプリ内の役割の設定'); M('HC-05c-3', '組織情報の編集'); M('HC-05c-4', '権限の棚卸し')
M('HC-11 HE-18b', '通知メールの送信'); M('HE-18a', '流出パスワードの使用拒否')
M('HD-10', '参照用データの更新'); M('HE-11', '停止の確実な伝播')
M('HF-03', '長期未使用者の自動停止'); M('HF-04', '日次の整合突合')
M('HG-02 HG-03', '管理操作の3段階権限確認'); M('HB-18', '利用者の停止（消さずに無効化）')
# 新設 sorry ページ
M('HC-04j', 'sorryページ(ブローカー)'); M('GD-31', 'sorryページ(アプリ)')
# ユーザーが基盤/アプリで 2 分した機能（同じ機能ID）
SPLIT_RULE = {
    '強制ログアウト': lambda i, d: '強制ログアウト（ブローカー）' if i in ('G-1.7',) else '強制ログアウト（アプリ）',
    '顧客の作成': lambda i, d: '顧客の作成(ブローカー)' if i in ('HB-F-ADM-14', 'G-1.1') else '顧客の作成(アプリ)',
    '操作記録の照会': lambda i, d: '操作記録の照会(ブローカー)' if i in ('HB-F-ADM-18', 'HG-04', 'HG-05', 'HD-15', 'E-7', 'D-9.2', 'HK-06') else '操作記録の照会(アプリ)',
}

log = []
for i, d in rows.items():
    old = (d['機能グループ'], d['機能名'], d['機能ID'])
    if i in FUNCMAP:
        new = FUNCMAP[i]
    else:
        n = RENAME.get(d['機能名'], d['機能名'])
        if n in SPLIT_RULE:
            n = SPLIT_RULE[n](i, d)
        if n in G:
            new = T(n)
        else:
            new = (GROUP_OF.get(n, d['機能グループ']), n, d['機能ID'])
    if new != old:
        d['機能グループ'], d['機能名'], d['機能ID'] = new; log.append((i, old, new))
unmapped = sorted({(d['機能グループ'], d['機能名']) for d in rows.values() if d['機能名'] not in G})
assert not unmapped, unmapped
by_file = collections.defaultdict(list)
for i, d in rows.items(): by_file[file_of[i]].append(d)
for f in BODY:
    with open(os.path.join(W, f), 'w', encoding='utf-8', newline='') as fp:
        w = csv.writer(fp, delimiter='\t', lineterminator='\n'); w.writerow(hdr)
        for d in by_file[f]: w.writerow([d.get(c, '') for c in hdr])
xl = {r[1]['A']: (r[1]['I'], r[1]['J']) for r in json.load(open('/tmp/xl.json'))}
n_map = 0
with open(os.path.join(W, 'SYNC_funcmap.tsv'), 'w', encoding='utf-8') as fp:
    fp.write('WBS ID\t機能グループ（I）\t機能名（J）\n')
    for i, d in rows.items():
        cur = (d['機能グループ'], d['機能名'])
        if i not in xl or xl[i] != cur:
            fp.write(f'{i}\t{cur[0]}\t{cur[1]}\n'); n_map += 1

# ---------- 機能名一覧 v2（ユーザーの配置・列） ----------
cnt = collections.Counter(); days = collections.Counter(); tgt = collections.Counter()
for i, d in rows.items():
    cnt[d['機能名']] += 1; days[d['機能名']] += eff[i]
    if d['スコープ'] == '対象': tgt[d['機能名']] += eff[i]
NOTE = {
    'ローカルユーザー管理': '', 'ログイン後の属性取り込み_SCIM': '要確認: 内容は「2 回目以降のログイン時に IdP の属性で更新する」処理（F-PROV-02 と同じ出来事）で SCIM ではない。F-PROV-02 に統合を推奨',
    'ブローカー側のシャドウユーザ作成': '要確認: F-PROV-01 初回ログイン時の自動登録と同じ出来事。どちらかに統合を推奨',
    'Broker-KeycloakとIdP-Keycloakの連携': 'Realm 統合（9/2）で対象外。一覧から外すか「対象外」と明記を推奨',
    '停止の確実な伝播': 'Realm 統合で対象外（WBS 行は残る）', '再開の確実な伝播': 'Realm 統合で対象外', '初回ログイン者の識別子通知': 'Realm 統合で対象外',
    '停止伝播の突合（短間隔）': 'Realm 統合で対象外', '重要操作時の追加認証': 'ステップアップ認証不要の決定で対象外',
    'sorryページ(ブローカー)': '新設。認証製品のエラー・案内画面（HC-04j）', 'sorryページ(アプリ)': '新設。403 → Sorry 誘導規約（GD-31）',
    '顧客システムからのグループ連携': '初期リリース対象外',
}
out = []
for r in sheet:
    name = r[2]
    if not name or (r[12] or '') not in ('', '追加') or '／' in name:
        continue
    fid = r[3] or ('F-AUTH-23' if name == 'sorryページ(ブローカー)' else 'F-AUTH-24' if name == 'sorryページ(アプリ)' else '横断')
    desc = (r[4] or '').replace('\n', ' ').replace('\r', '')
    if name == 'sorryページ(ブローカー)': desc = '認証製品が出すエラー・案内の画面。ログインや振り分けに失敗したときの文言と誘導'
    if name == 'sorryページ(アプリ)': desc = 'アプリ側が出す案内画面。権限が無い（403）ときの Sorry 画面への誘導規約'
    out.append([r[0], r[1], name, fid, desc, r[5] or '', r[6] or '', cnt[name], f'{days[name]:g}', f'{tgt[name]:g}', NOTE.get(name, '')])
with open(os.path.join(W, 'SYNC_func.tsv'), 'w', encoding='utf-8') as fp:
    fp.write('系統\t機能グループ\t機能名\t機能ID\t概要\t基盤\tアプリ\t行数\t人日\tうち対象\t備考\n')
    for o in out: fp.write('\t'.join(str(x) for x in o) + '\n')
listed = {o[2] for o in out}
assert set(cnt) <= listed, set(cnt) - listed

# ---------- 機能グループ一覧 v2 ----------
GDESC = {}
for l in open(os.path.join(W, 'SYNC_group.tsv'), encoding='utf-8'):
    c = l.rstrip('\n').split('\t')
    if c[0] != '機能グループ' and '／' not in c[0]: GDESC[c[0]] = (c[1], c[2])
GDESC['エラー画面'] = ('認証', 'ログインや権限判定に失敗したときに利用者へ案内する画面（認証製品側とアプリ側）')
GDESC['ログイン画面'] = ('横断', '認証製品が表示するログイン画面の並び・優先順位・ブランド別表示')
GDESC['運用'] = ('横断', '機能ではなく運用上の取り決め（解約・法令対応・災害対策・同意管理）')
gcnt = collections.Counter(); gdays = collections.Counter()
for i, d in rows.items(): gcnt[d['機能グループ']] += 1; gdays[d['機能グループ']] += eff[i]
order = []
for o in out:
    if o[1] not in order: order.append(o[1])
with open(os.path.join(W, 'SYNC_group.tsv'), 'w', encoding='utf-8') as fp:
    fp.write('機能グループ\t系統\t概要\t行数\t人日\n')
    for g in order:
        s, t = GDESC[g]; fp.write(f'{g}\t{s}\t{t}\t{gcnt[g]}\t{gdays[g]:g}\n')
assert set(gcnt) <= set(order), set(gcnt) - set(order)

# ---------- md ----------
with open(os.path.join(R, 'function-list-dedup-remap-2026-09-06.md'), 'w', encoding='utf-8') as fp:
    fp.write('# 機能名一覧の重複解消 — WBS 行の付け替え記録（機械生成）\n\n- **日付**: 2026-09-06\n- 見直しの判断は [function-list-dedup-2026-09-06.md](function-list-dedup-2026-09-06.md)\n')
    fp.write('- **結果**: 機能名 %d 件（重複解消前 134）。「／」複合 23 種と不要 17 種を全廃し、WBS %d 行の機能グループ/機能名/機能ID を付け替えた（`SYNC_funcmap.tsv`）\n\n' % (len(out), n_map))
    fp.write('## WBS 行の付け替え\n\n| WBS ID | 項目 | 旧 機能名 | 新 機能グループ | 新 機能名 |\n|---|---|---|---|---|\n')
    for i, old, new in log:
        fp.write(f'| {i} | {rows[i]["項目"][:40]} | {old[1]} | {new[0]} | {new[1]} |\n')
print('funcs', len(out), 'groups', len(order), 'remapped', len(log), 'sync rows', n_map)
