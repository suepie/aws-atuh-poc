#!/usr/bin/env python3
"""消去まわりの行を ①②③④ に足し、要件マッピングを読み切れる列構成に作り直す。

2026-09-07 の回答:
  1. 消去の設計行を足してよい → ①②③④ に足す（FR-USER-011 / NFR-COMP-009 が埋まる）
  2. NFR-COST 系はコスト見積もりシートが受け皿 → 状況を「別シートで管理」にする
  3. 要件マッピングの列を 要件ID / 項目 / 種別 / 概要 / 担当範囲 / ①②③④ / 状況 にする
"""
import csv, os, re, collections

W = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(W, '..')
L = lambda n: list(csv.DictReader(open(os.path.join(W, n), encoding='utf-8'), delimiter='\t'))
def out(n, rows, cols):
    with open(os.path.join(W, n), 'w', encoding='utf-8', newline='') as fp:
        w = csv.writer(fp, delimiter='\t', lineterminator='\n'); w.writerow(cols)
        for r in rows: w.writerow([str(r.get(c, '')) for c in cols])

bd, dm, ts, fl, gl = (L(f'SHEET_{n}.tsv') for n in ['基本設計', '詳細設計_製造', 'テスト', '機能名一覧', '機能グループ一覧'])
req = L('SHEET_要件一覧.tsv')
FID = {r['機能ID']: r['機能名'] for r in fl}
GOF = {r['機能名']: r['機能グループ'] for r in fl}

# ---------- ① ----------
K = '基盤チーム'
NEW1 = [
 ('HD-24', 'HD データ設計', '設計書の執筆', '保存期限切れデータの消去',
  'ユーザと記録の保持年数と消去の方針',
  'ユーザと記録を何年保ち、いつどうやって消すかを決める。停止から消去までの段階と、消したことをどう示すかを含む',
  '方針。対象ごとの保持年数・消去の起点・消去の証跡の残し方が定まっている', 1.5, '法令・契約',
  '個人データを求めに応じて消せることは法令の要求。トリミングで方針の行が落ち、消去の起点が決まらないまま残っていた'),
 ('HK-07', 'HK 顧客提供成果物', 'ガイド・手順書の執筆', '本人からの開示・削除請求への対応',
  '本人からの開示・削除請求への対応手順',
  '本人から求められたときに、保有しているデータを開示し、または消すまでの手順を決める',
  '手順書。受付から回答までの期限・確認方法・記録の残し方が定まっている', 1, '法令・契約',
  '顧客が本人対応の窓口になるため、本基盤側の手順が無いと顧客が答えられない'),
]
for i, cls, wk, f, item, ov, dv, days, basis, note in NEW1:
    bd.append({'ID': i, '分類': cls, '作業種別': wk, '機能グループ': GOF[f], '機能名': f, '項目': item,
               '概要': ov, '成果物と完了条件': dv, '人日': f'{days:g}', '担当（案②: 一部移管）': K,
               '担当（案③: アプリ構築）': K, '判断根拠': basis, '根拠の補足': note, 'スコープ': '対象',
               '当初想定': '新規: 非機能・運用', '依存': '—', '状態': '未着手', '出典': '',
               '機能ID': [k for k, v in FID.items() if v == f][0]})
# ---------- ②③ ----------
NEW23 = [
 ('DD', 'D', '保存期限切れデータの消去', '保持期間と消去の実装設計',
  '対象の表ごとの保持年数・消去の起点・消去の順序と、消し残しの検出方法が確定している', 1.5),
 ('DD', 'B', '本人からの開示・削除請求への対応', '開示と削除の求めへの対応の実装設計',
  '本人を特定する方法・取り出す範囲・消す範囲と、対応の記録の残し方が確定している', 1),
 ('MK', 'F', '保存期限切れデータの消去', '消去処理の実装',
  '期限を過ぎたデータが自動で消え、消したことが記録に残る', 2),
 ('MK', 'B', '本人からの開示・削除請求への対応', '開示と削除の手段の実装',
  '本人分のデータを取り出せ、消せることを実機で確認できる', 1.5),
]
CLS = {'D': 'データの詳細設計', 'B': '機能の詳細設計'}
MCLS = {'F': '定期処理の実装', 'B': 'Keycloak-Broker の設定・構築'}
seq = collections.Counter()
for r in dm: seq[r['ID'][:3]] = max(seq[r['ID'][:3]], int(r['ID'].split('-')[1]))
for p, c, f, item, dv, days in NEW23:
    seq[p + c] += 1
    dm.append({'ID': f'{p}{c}-{seq[p+c]:02d}', '分類': f'{p}-{c} ' + (CLS if p == 'DD' else MCLS)[c],
               '機能グループ': GOF[f], '機能名': f, '項目': item, '概要・完了定義': dv,
               '詳細設計 人日': f'{days:g}' if p == 'DD' else '', '製造 人日': '' if p == 'DD' else f'{days:g}', '内訳': ''})
# ---------- ④ ----------
NEW4 = [
 ('B 総合', '保存期限切れデータの消去', '保持期間と消去', [
  '期限を過ぎたデータが消える', '期限内のデータが消えない', '消したことが記録に残る',
  '停止から消去までの段階が設計どおり', '消し残しが検出できる'], 2, 'FR-USER-011 / NFR-COMP-007', 'B 総合の前提が揃っていること'),
 ('G 運用', '本人からの開示・削除請求への対応', '本人からの開示・削除請求への対応', [
  '本人を特定できる', '保有しているデータを取り出せる', '求めに応じて消せる',
  '消したあと復元できないことを示せる', '対応の記録が残る', '期限内に回答できる'], 1.5, 'NFR-COMP-009', '手順書が完成していること'),
]
tseq = collections.Counter()
for r in ts: tseq[r['区分']] = max(tseq[r['区分']], int(r['ID'].split('-')[1]))
PRE = {'A 結合': 'IT', 'B 総合': 'ST', 'C 実機': 'RI', 'D 性能': 'PT', 'E 可用性・災害復旧': 'DR',
       'F セキュリティ': 'SEC', 'G 運用': 'OP', 'H 受入': 'UAT', 'I テスト共通': 'TE'}
for k, f, item, views, days, rq, pre in NEW4:
    tseq[k] += 1
    ts.append({'区分': k, 'ID': f'{PRE[k]}-{tseq[k]:02d}', '機能グループ': GOF[f], '機能名': f,
               'テスト項目': item, 'テスト観点': '／'.join(views), '人日': f'{days:g}', '対応要件': rq, '前提': pre})

# ---------- 並べ替えと採番 ----------
G = [r['機能グループ'] for r in gl]; gi = {g: i for i, g in enumerate(G)}
fi = {r['機能名']: i for i, r in enumerate(fl)}
bd.sort(key=lambda r: (gi.get(r['機能グループ'], 999), fi.get(r['機能名'], 999)))
dm.sort(key=lambda r: (gi.get(r['機能グループ'], 999), fi.get(r['機能名'], 999), 0 if r['詳細設計 人日'] else 1))
ko = {k: i for i, k in enumerate(PRE)}
ts.sort(key=lambda r: (ko[r['区分']], gi.get(r['機能グループ'], 999), fi.get(r['機能名'], 999)))
seq = collections.Counter()
for r in dm:
    p = r['ID'][:3]; seq[p] += 1; r['ID'] = f'{p}-{seq[p]:02d}'
seq = collections.Counter()
for r in ts:
    p = PRE[r['区分']]; seq[p] += 1; r['ID'] = f'{p}-{seq[p]:02d}'

BDC = ['ID', '分類', '作業種別', '機能グループ', '機能名', '項目', '概要', '成果物と完了条件', '人日',
       '担当（案②: 一部移管）', '担当（案③: アプリ構築）', '判断根拠', '根拠の補足', 'スコープ', '当初想定', '依存', '状態', '出典', '機能ID']
out('SHEET_基本設計.tsv', bd, BDC)
out('SHEET_詳細設計_製造.tsv', dm, ['ID', '分類', '機能グループ', '機能名', '項目', '概要・完了定義', '詳細設計 人日', '製造 人日', '内訳'])
out('SHEET_テスト.tsv', ts, ['区分', 'ID', '機能グループ', '機能名', 'テスト項目', 'テスト観点', '人日', '対応要件', '前提'])
# 一覧の集計を更新
n2 = collections.Counter(); b2 = collections.Counter(); t2 = collections.Counter()
for r in bd:
    n2[r['機能名']] += 1; b2[r['機能名']] += float(r['人日'] or 0)
    if r['スコープ'] == '対象': t2[r['機能名']] += float(r['人日'] or 0)
for r in fl: r['行数'] = str(n2[r['機能名']]); r['人日'] = f"{b2[r['機能名']]:g}"; r['うち対象'] = f"{t2[r['機能名']]:g}"
gn = collections.Counter(); gd = collections.Counter()
for r in bd: gn[r['機能グループ']] += 1; gd[r['機能グループ']] += float(r['人日'] or 0)
for r in gl: r['行数'] = str(gn[r['機能グループ']]); r['人日'] = f"{gd[r['機能グループ']]:g}"
out('SHEET_機能名一覧.tsv', fl, ['系統', '機能グループ', '機能名', '機能ID', '概要', '基盤', 'アプリ', '行数', '人日', 'うち対象'])
out('SHEET_機能グループ一覧.tsv', gl, ['機能グループ', '系統', '概要', '行数', '人日'])
# サマリ
b = collections.Counter(); s2 = collections.Counter(); s3 = collections.Counter(); s4 = collections.Counter(); cnt = collections.Counter()
for r in bd:
    if r['スコープ'] == '対象': b[(r['機能グループ'], r['機能名'])] += float(r['人日'] or 0)
for r in dm:
    k = (r['機能グループ'], r['機能名']); cnt[k] += 1
    s2[k] += float(r['詳細設計 人日'] or 0); s3[k] += float(r['製造 人日'] or 0)
for r in ts:
    k = (r['機能グループ'], r['機能名']); cnt[k] += 1; s4[k] += float(r['人日'] or 0)
keys = sorted(set(list(b) + list(cnt)), key=lambda k: (gi.get(k[0], 999), fi.get(k[1], 999)))
sm = [{'機能グループ': k[0], '機能名': k[1], '① 基本設計': f'{b[k]:g}', '② 詳細設計': f'{s2[k]:g}', '③ 製造': f'{s3[k]:g}',
       '④ テスト': f'{s4[k]:g}', '合計': f'{b[k]+s2[k]+s3[k]+s4[k]:g}', '②③④ 行数': str(cnt[k])} for k in keys]
out('SHEET_サマリ工程別.tsv', sm, ['機能グループ', '機能名', '① 基本設計', '② 詳細設計', '③ 製造', '④ テスト', '合計', '②③④ 行数'])

# ---------- 要件マッピング（列を作り直す） ----------
exec(open(os.path.join(W, 'build_req_map_2026-09-07.py')).read().split('# 要件ID -> 機能ID の対応')[1].split('bad = [')[0])
byfunc = collections.defaultdict(lambda: {'1': [], '2': [], '3': [], '4': []})
name2fid = {v: k for k, v in FID.items()}
for r in bd:
    f = name2fid.get(r['機能名'])
    if f and r['スコープ'] == '対象': byfunc[f]['1'].append(r['ID'])
for r in dm:
    f = name2fid.get(r['機能名'])
    if f: byfunc[f]['2' if r['詳細設計 人日'] else '3'].append(r['ID'])
tsq = collections.defaultdict(list)
for r in ts:
    for m in re.findall(r'(?:FR|NFR)-[A-Z]+-\d+', r['対応要件']): tsq[m].append(r['ID'])
    f = name2fid.get(r['機能名'])
    if f: byfunc[f]['4'].append(r['ID'])
J = lambda xs: ' '.join(sorted(set(xs))) if xs else ''
mp = []
for r in req:
    fids = M[r['要件ID']]
    p = {k: [] for k in '1234'}
    for f in fids:
        for k in '1234': p[k] += byfunc[f][k]
    if tsq.get(r['要件ID']): p['4'] = tsq[r['要件ID']]
    cov = sum(1 for k in '1234' if p[k])
    if r['要件ID'].startswith('NFR-COST'): st = '別シートで管理（コスト見積もり）'
    elif r['担当範囲'] == '対象外': st = 'Phase 1 では作らない'
    elif r['担当範囲'] != 'Keycloak-Broker': st = f'{r["担当範囲"]} の責務'
    elif cov == 4: st = '全工程あり'
    elif cov == 0: st = '🔴 どの工程にも無い'
    else: st = '🔺 一部の工程のみ（文書で完結するものを含む）'
    mp.append({'要件ID': r['要件ID'], '項目': r['項目'], '種別': r['種別'], '概要': r['概要'], '担当範囲': r['担当範囲'],
               '① 基本設計': J(p['1']), '② 詳細設計': J(p['2']), '③ 製造': J(p['3']), '④ テスト': J(p['4']), '状況': st})
MC = ['要件ID', '項目', '種別', '概要', '担当範囲', '① 基本設計', '② 詳細設計', '③ 製造', '④ テスト', '状況']
out('SHEET_要件マッピング.tsv', mp, MC)

st = collections.Counter(o['状況'] for o in mp)
T = lambda rows, c: sum(float(r[c] or 0) for r in rows)
with open(os.path.join(R, 'requirements-mapping-2026-09-07.md'), 'w', encoding='utf-8') as fp:
    fp.write('# 要件 × 工程のマッピング\n\n- **日付**: 2026-09-07（第 2 版）\n')
    fp.write(f'- **要件 {len(mp)} 件**を行、工程を列にした。**この表だけで読み切れるよう、項目・種別・概要・担当範囲を並べた**\n')
    fp.write('- 各セルには対応する WBS の ID が入る。空欄はその工程に作業が無いことを意味する\n')
    fp.write('- **反映用**: `wbs-text/SHEET_要件マッピング.tsv`（10 列）\n\n')
    fp.write('## 状況\n\n| 状況 | 件数 |\n|---|---:|\n')
    for k, v in st.most_common(): fp.write(f'| {k} | {v} |\n')
    fp.write(f'| **計** | **{len(mp)}** |\n\n')
    fp.write('## 今回足した消去まわりの行\n\n| 工程 | ID | 項目 | 人日 |\n|---|---|---|---:|\n')
    for i, cls, wk, f, item, ov, dv, days, basis, note in NEW1: fp.write(f'| ① 基本設計 | {i} | {item} | {days:g} |\n')
    for p, c, f, item, dv, days in NEW23:
        fp.write(f'| {"② 詳細設計" if p=="DD" else "③ 製造"} | — | {item} | {days:g} |\n')
    for k, f, item, views, days, rq, pre in NEW4: fp.write(f'| ④ テスト | — | {item} | {days:g} |\n')
    fp.write('\n→ **FR-USER-011（ユーザ削除時の関連データ削除）と NFR-COMP-009（個人データ削除権）が全工程そろった**。\n\n')
    fp.write('## 工程の合計\n\n| 工程 | 行数 | 人日 |\n|---|---:|---:|\n')
    fp.write(f'| ① 基本設計 | {len(bd)} | 全量 {T(bd,"人日"):g} / 対象 {sum(float(r["人日"] or 0) for r in bd if r["スコープ"]=="対象"):g} |\n')
    fp.write(f'| ② 詳細設計 | {sum(1 for r in dm if r["詳細設計 人日"])} | {T(dm,"詳細設計 人日"):g} |\n')
    fp.write(f'| ③ 製造 | {sum(1 for r in dm if r["製造 人日"])} | {T(dm,"製造 人日"):g} |\n')
    fp.write(f'| ④ テスト | {len(ts)} | {T(ts,"人日"):g} |\n')
    fp.write(f'| **計** | | **{sum(float(r["人日"] or 0) for r in bd if r["スコープ"]=="対象")+T(dm,"詳細設計 人日")+T(dm,"製造 人日")+T(ts,"人日"):g}** |\n\n')
    fp.write('## 全 %d 件\n\n| 要件ID | 項目 | 種別 | 担当範囲 | ① | ② | ③ | ④ | 状況 |\n|---|---|---|---|:-:|:-:|:-:|:-:|---|\n' % len(mp))
    for o in mp:
        fp.write(f"| {o['要件ID']} | {o['項目'][:32]} | {o['種別'][:2]} | {o['担当範囲']} | {'○' if o['① 基本設計'] else '—'} "
                 f"| {'○' if o['② 詳細設計'] else '—'} | {'○' if o['③ 製造'] else '—'} | {'○' if o['④ テスト'] else '—'} | {o['状況']} |\n")
print('① ', len(bd), T(bd, '人日'), '対象', sum(float(r['人日'] or 0) for r in bd if r['スコープ'] == '対象'))
print('②', T(dm, '詳細設計 人日'), '③', T(dm, '製造 人日'), '④', T(ts, '人日'))
for k, v in st.most_common(): print(f'  {k:34s} {v}')
