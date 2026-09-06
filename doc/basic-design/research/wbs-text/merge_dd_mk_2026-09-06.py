#!/usr/bin/env python3
"""②③ を現行の基本設計（130 行 / 193.5 人日）に追いつかせる。

2026-09-06 の追加指示:
  1. 多要素認証はブローカーでは扱わない（フェデレーション含め IdP 側の責務）→ ②③ から外す
  2. SCIM は認証製品（Keycloak）の上に立てる → 別基盤を作らない。概要に明記
  3. IdP 側のクラスタ構成に追加の設計行は不要 → 現状維持
  4. 監査ログは全体の共通基盤へ出力して集約し、参照は保管先で行う → 保管領域を自前で作らない分を減らす
入力: SYNC_dd_mk.tsv + SYNC_dd_mk_add.tsv、機能グループ一覧の並び
出力: SYNC_dd_mk.tsv（統合・再採番済み）/ ../wbs-dd-mk-2026-09-06.md
"""
import csv, os, json, collections

W = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(W, '..')
DD, MK = '② 詳細設計', '③ 製造'

rows = []
for f in ['SYNC_dd_mk.tsv', 'SYNC_dd_mk_add.tsv']:
    p = os.path.join(W, f)
    if os.path.exists(p):
        rows += list(csv.DictReader(open(p, encoding='utf-8'), delimiter='\t'))
seen = set(); uniq = []
for r in rows:
    k = (r['工程'], r['機能グループ'], r['機能名'], r['項目'])
    if k in seen: continue
    seen.add(k); uniq.append(r)
rows = uniq

# --- 1. 多要素認証はブローカーで扱わない ---
drop = [r for r in rows if r['機能グループ'] == '多要素認証']
rows = [r for r in rows if r['機能グループ'] != '多要素認証']

# --- 2. SCIM は認証製品の上に立てる ---
for r in rows:
    if r['機能グループ'] == 'ユーザ登録（顧客システム連携・SCIM）':
        if '受信窓口の実装設計' in r['項目']:
            r['概要・完了定義'] = '入口の作り・呼び出し元の確認方法・応答と異常時の返し方が実装できる粒度で書かれている。窓口は認証製品の上に立てる（別の実行基盤は作らない）'
        if r['項目'] == '受信窓口の実装':
            r['概要・完了定義'] = '認証製品の上に立てた窓口で、顧客システムから登録・更新・削除・検索ができる'
            r['内訳'] = '部品の組み込み3+自作部分5'

# --- 4. 監査ログは全体の共通基盤へ出して集約する ---
for r in rows:
    if r['機能名'] == '監査ログの取得・保管方式':
        if r['項目'] == '記録の保管領域の実装設計':
            r['項目'] = '記録の出力先と保持の実装設計'
            r['概要・完了定義'] = '全体の共通基盤へ出す形式・経路・保持年数と、個人情報を伏せる箇所が確定している'
            r['人日'] = '2'
        if r['項目'] == '記録の出力設定と保管領域の構築':
            r['項目'] = '記録の出力設定と共通基盤への集約'
            r['概要・完了定義'] = '設計どおりの記録が出力され、全体の共通基盤に集約されて参照できる'
            r['人日'] = '3'; r['内訳'] = '出力設定2+集約の疎通1'
        if r['項目'] == '記録の出力と集約の実装仕様':
            r['概要・完了定義'] = '出力する項目・形式と、全体の共通基盤へ送る経路が確定している'

# --- 5. 機能名を機能名一覧に合わせる ---
for r in rows:
    if r['機能名'] == '顧客解約': r['機能名'] = '顧客の解約'
    if r['機能名'] == '情報洩時対応' or r['機能名'] == '情報漏洩時対応': r['機能名'] = '運用手順書'

# --- 6. 機能名ごとに行が対応するよう分割（合計は変えない） ---
def find(item):
    for r in rows:
        if r['項目'] == item: return r
    return None
def split(item, new_item, new_days, keep_days, new_func, note=''):
    r = find(item)
    if not r: return
    import copy
    n = copy.deepcopy(r); n['項目'] = new_item; n['人日'] = f'{new_days:g}'; n['機能名'] = new_func
    n['概要・完了定義'] = note or n['概要・完了定義']
    r['人日'] = f'{keep_days:g}'
    rows.insert(rows.index(r) + 1, n)
split('停止と再開の実装設計', '再開の条件判定の実装設計', 0.5, 1.5, '停止済み利用者の再開',
      '再開してよい条件と、誤って復活させないための除外条件が実装できる粒度で書かれている')
split('停止と再開の実装', '再開の実装', 1, 2, '停止済み利用者の再開',
      '条件を満たす場合だけ再開でき、除外条件に当たる場合は再開されない')
split('業務システム連携の設定と実装', '業務システム側の利用者自動作成の設定', 2, 4, '業務システム側の利用者自動作成',
      '初回ログインで相手側に利用者が作られ、渡した属性が反映される')
r = find('項目の対応づけと絞り込みの実装設計')
if r: r['機能名'] = 'SCIM 受信: 利用者の検索'
import copy
def add(after_item, wk, item, desc, days, func, grp=None):
    src = find(after_item)
    n = copy.deepcopy(src); n['工程'] = wk; n['項目'] = item; n['概要・完了定義'] = desc
    n['人日'] = f'{days:g}'; n['機能名'] = func; n['内訳'] = ''
    if grp: n['機能グループ'] = grp
    if wk != src['工程']:
        n['分類'] = ('DD-' if wk == DD else 'MK-') + src['分類'].split('-')[1]
    rows.insert(rows.index(src) + 1, n)
add('受信窓口の実装設計（入口・認証・応答）', DD, '更新の反映と競合の扱いの実装設計',
    '既にいる利用者を更新するときの項目の上書き規則と、競合したときの扱いが確定している', 1, 'SCIM 受信: 利用者の更新')
add('受信窓口の実装設計（入口・認証・応答）', DD, '削除通知の読み替えの実装設計',
    '削除の通知を受けたときに消さずに止める読み替えの規則と、記録の残し方が確定している', 1, 'SCIM 受信: 削除通知（無効化へ読み替え）')
add('受信窓口の実装', MK, '削除通知の読み替えの実装',
    '削除の通知で利用者が止まり、消えていないことを確認できる', 1.5, 'SCIM 受信: 削除通知（無効化へ読み替え）')
add('業務システム連携の設定と実装', MK, '他アプリへの連携の設定',
    '業務システムにログインした状態から他のアプリを呼べる', 1, '業務システムから他アプリへの連携')

# --- 並べ替えと再採番 ---
gorder = {}
for n, l in enumerate(open(os.path.join(W, 'SYNC_group.tsv'), encoding='utf-8')):
    c = l.rstrip('\n').split('\t')
    if c[0] != '機能グループ': gorder.setdefault(c[0], n)
forder = {}
for n, l in enumerate(open(os.path.join(W, 'SYNC_func.tsv'), encoding='utf-8')):
    c = l.rstrip('\n').split('\t')
    if len(c) > 2 and c[2] != '機能名': forder.setdefault(c[2], n)
rows.sort(key=lambda r: (gorder.get(r['機能グループ'], 999), r['機能グループ'],
                         forder.get(r['機能名'], 999), r['機能名'], 0 if r['工程'] == DD else 1))
seq = collections.Counter()
for r in rows:
    pre = 'DD' if r['工程'] == DD else 'MK'
    c = r['分類'].split(' ')[0].split('-')[1]
    seq[(pre, c)] += 1
    r['ID'] = f'{pre}{c}-{seq[(pre, c)]:02d}'

COLS = ['工程', 'ID', '分類', '機能グループ', '機能名', '項目', '概要・完了定義', '人日', '内訳']
with open(os.path.join(W, 'SYNC_dd_mk.tsv'), 'w', encoding='utf-8', newline='') as fp:
    w = csv.writer(fp, delimiter='\t', lineterminator='\n'); w.writerow(COLS)
    for r in rows: w.writerow([r.get(c, '') for c in COLS])
if os.path.exists(os.path.join(W, 'SYNC_dd_mk_add.tsv')): os.remove(os.path.join(W, 'SYNC_dd_mk_add.tsv'))

# --- 基本設計との突き合わせ ---
bd = json.load(open('/tmp/bd2.json'))
bd_g = collections.Counter(); bd_f = collections.Counter()
for r in bd:
    d = float(r['人日'] or 0)
    if r['スコープ'] == '対象': bd_g[r['機能グループ']] += d; bd_f[(r['機能グループ'], r['機能名'])] += d
d2 = sum(float(r['人日']) for r in rows if r['工程'] == DD)
d3 = sum(float(r['人日']) for r in rows if r['工程'] == MK)
n2 = sum(1 for r in rows if r['工程'] == DD)
g2 = collections.Counter(); g3 = collections.Counter(); have = set()
for r in rows:
    have.add((r['機能グループ'], r['機能名']))
    (g2 if r['工程'] == DD else g3)[r['機能グループ']] += float(r['人日'])
missing = sorted(k for k in bd_f if k not in have and bd_f[k] > 0)
extra = sorted(k for k in have if k not in bd_f)

with open(os.path.join(R, 'wbs-dd-mk-2026-09-06.md'), 'w', encoding='utf-8') as fp:
    fp.write('# ② 詳細設計・③ 製造 の WBS（基本設計 130 行に追いつかせた版）\n\n')
    fp.write('- **日付**: 2026-09-06（第 3 版）\n- **前提**: 基本設計 130 行 / 全量 193.5 人日 / Phase 1 対象 181.5 人日\n')
    fp.write('- **並び**: 機能グループ → 機能名 → 工程。1 つの機能の ② と ③ が隣り合う\n')
    fp.write('- **生成**: `wbs-text/merge_dd_mk_2026-09-06.py` / 反映用 `wbs-text/SYNC_dd_mk.tsv`\n\n')
    fp.write('## 今回の反映（4 つの指示）\n\n| # | 指示 | ②③ への反映 |\n|---|---|---|\n')
    fp.write('| 1 | 多要素認証はブローカーで扱わない（フェデレーション含め IdP 側の責務） | **6 行を削除**（② 3 人日 / ③ 5.5 人日 減） |\n')
    fp.write('| 2 | SCIM は認証製品（Keycloak）の上に立てる | 別の実行基盤は作らない。窓口の設計と実装の完了定義に明記。**工数は据え置き** |\n')
    fp.write('| 3 | IdP 側のクラスタ構成に追加の設計は不要 | **現状維持**（基盤の構築 6 ＋ 引き渡し 2 はそのまま） |\n')
    fp.write('| 4 | 監査ログは全体の共通基盤へ出力して集約し、参照は保管先で行う | 保管領域を自前で作らない分を減らした（② 3→2 / ③ 5→3） |\n\n')
    fp.write(f'| 工程 | 行数 | 人日 |\n|---|---:|---:|\n| ② 詳細設計 | {n2} | **{d2:g}** |\n')
    fp.write(f'| ③ 製造 | {len(rows)-n2} | **{d3:g}** |\n| **計** | **{len(rows)}** | **{d2+d3:g}** |\n\n')
    fp.write('## 機能グループ別\n\n| 機能グループ | ① 基本設計 | ② 詳細設計 | ③ 製造 |\n|---|---:|---:|---:|\n')
    for g in sorted(set(list(g2) + list(g3) + list(bd_g)), key=lambda x: gorder.get(x, 999)):
        fp.write(f'| {g} | {bd_g.get(g, 0):g} | {g2.get(g, 0):g} | {g3.get(g, 0):g} |\n')
    fp.write(f'| **計** | **{sum(bd_g.values()):g}** | **{d2:g}** | **{d3:g}** |\n\n')
    fp.write('## 基本設計にあって ②③ に無い機能\n\n| 機能グループ | 機能名 | ① 人日 | 理由 |\n|---|---|---:|---|\n')
    REASON = {'SCIM 受信: グループ連携': '初期リリース対象外。基本設計で対象外と宣言するところまで',
              '多要素認証': 'ブローカーでは扱わない（フェデレーション含め IdP 側の責務）',
              '追加認証（数字コード）': 'ブローカーでは扱わない（IdP 側の責務）',
              '追加認証の登録（数字コード）': 'ブローカーでは扱わない（IdP 側の責務）',
              '稼働率・復旧目標（SLA / SLO）': '顧客への約束を書く作業で、実装・構築が発生しない',
              '顧客向け説明資料': '契約に添える文書で、実装・構築が発生しない',
              'アプリ開発者向けガイド（共通部）': '文書の作成のみ。実装は「サンプル実装」で計上済み',
              '開発・検証環境': '「環境構成（本番 / stg / dev）」の構築行に集約',
              '管理操作の 3 段階権限確認': '基本設計で対象外（省略・吸収）',
              '設計書の総則・前提・用語': '②③ にも同じ位置づけの行があり、レビュー・整合に含める',
              'トレーサビリティ': '②③ のトレーサビリティ更新行で計上済み'}
    for g, f in missing:
        fp.write(f'| {g} | {f} | {bd_f[(g,f)]:g} | {REASON.get(f, "要確認")} |\n')
    if extra:
        fp.write('\n## ②③ にあって基本設計に無い機能\n\n| 機能グループ | 機能名 |\n|---|---|\n')
        for g, f in extra: fp.write(f'| {g} | {f} |\n')
    fp.write('\n## 全行\n\n| 工程 | ID | 分類 | 機能グループ | 機能名 | 項目 | 人日 |\n|---|---|---|---|---|---|---:|\n')
    for r in rows:
        fp.write(f"| {r['工程']} | {r['ID']} | {r['分類']} | {r['機能グループ']} | {r['機能名']} | {r['項目']} | {r['人日']} |\n")
print(f'② {n2}行 {d2:g} / ③ {len(rows)-n2}行 {d3:g} / 計 {len(rows)}行 {d2+d3:g}')
print('削除（多要素認証）', len(drop), '行', sum(float(r['人日']) for r in drop))
print('①にあって②③に無い:', missing)
print('②③にあって①に無い:', extra)
