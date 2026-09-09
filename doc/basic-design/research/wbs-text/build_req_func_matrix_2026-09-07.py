#!/usr/bin/env python3
"""報告用: 要件 × 機能 のマッピング表を作る。

列: 要件ID / 要件 / 要件の概要 / 機能ID / 機能 / 機能の概要 / 担当 / 状況
  → 「要件 / 機能 / 要件の概要 / 機能の概要」の 4 列だけ見たいときは ID と右 2 列を隠す

機能の引き当ては 2 段階:
  ① 要件マッピングの ①②③④ に入っている WBS ID から、その行の機能名を逆引きする（= 実際に工数が付いている機能。最優先）
  ② 工程セルが空の要件（アプリ側 / 顧客 / 他組織 / 対象外）は、旧 build_req_map の要件→機能ID 対応を使う
  ③ どちらも無い場合は「—（本基盤に作る機能なし）」

出力: SHEET_要件機能マッピング.tsv / ../req-func-matrix-2026-09-07.md
"""
import ast, csv, os, re, collections

W = os.path.dirname(os.path.abspath(__file__)); P = lambda n: os.path.join(W, n)
L = lambda n: list(csv.DictReader(open(P(n), encoding='utf-8'), delimiter='\t'))
rm, bd, dm, ts, fl = (L(f'SHEET_{n}.tsv') for n in ['要件マッピング', '基本設計', '詳細設計_製造', 'テスト', '機能名一覧'])

FUNC = {f['機能ID']: f for f in fl}                     # 機能ID -> 機能名一覧の行
NAME2ID = {f['機能名']: f['機能ID'] for f in fl}
WBS2FUNC = {}                                            # WBS ID -> 機能ID
for rows in (bd, dm, ts):
    for r in rows:
        fid = r.get('機能ID') or NAME2ID.get(r['機能名'])
        if fid: WBS2FUNC[r['ID']] = fid
ORDER = {f['機能ID']: i for i, f in enumerate(fl)}       # 機能名一覧の並び順

# 旧マッピング（工程セルが空の要件のフォールバック）
src = open(P('build_req_map_2026-09-07.py'), encoding='utf-8').read()
LEGACY = ast.literal_eval('{' + re.search(r"^M = \{$(.*?)^\}$", src, re.S | re.M).group(1) + '}')
# 今回追加・付け替えた要件の対応（旧マッピングに無い / 変わったもの）
EXTRA = {
 'FR-FED-015': ['F-AUTH-09'], 'FR-AUTH-016': ['F-AUTH-28'], 'FR-USER-013': ['F-BAT-01'],
 'NFR-SEC-010-2': ['F-AUTH-22'], 'NFR-SEC-021': ['NF-OPS-11', 'NF-OPS-04'], 'NFR-SEC-022': ['NF-OPS-05'],
 'NFR-SEC-023': ['F-INT-08'], 'NFR-OPS-012': ['F-AUTH-29'], 'NFR-OPS-013': ['NF-ARC-05'],
 'FR-AUTH-001': ['F-AUTH-01'], 'FR-AUTH-009': ['F-AUTH-01'], 'FR-AUTH-010': ['F-AUTH-01'],
 'FR-AUTH-011': ['F-AUTH-20'], 'FR-AUTH-012': ['F-AUTH-01'], 'FR-USER-004': ['F-AUTH-01'],
 'NFR-SEC-009': ['F-AUTH-01'], 'FR-FED-012': ['F-AUTH-05'], 'FR-SSO-003': ['NF-DOC-01'],
 'FR-AUTHZ-007': ['NF-DOC-01'], 'FR-INT-007': ['NF-DOC-01'], 'NFR-PERF-003': ['NF-DOC-01'],
 'FR-SSO-010': ['F-ADM-10', 'F-INT-14'], 'FR-USER-001': ['F-ADM-03', 'F-ADM-03', 'F-ADM-05', 'F-INT-14'],
 'FR-AUTHZ-001': ['F-AZ-10', 'F-AZ-03'], 'FR-AUTHZ-002': ['F-AZ-05'], 'FR-USER-006': ['F-PROV-10', 'F-PROV-11', 'F-ADM-05'],
 'FR-USER-011': ['F-ADM-24', 'F-BAT-09'], 'NFR-COMP-009': ['F-ADM-24'], 'FR-FED-011': ['F-ADM-16', 'F-ADM-14'],
 'FR-USER-003': ['F-PROV-03', 'F-PROV-03', 'F-PROV-03', 'F-PROV-03'], 'NFR-SEC-011': ['NF-ARC-06', 'NF-SEC-01'],
 'NFR-SEC-012': ['NF-ARC-06', 'NF-SEC-01'], 'NFR-SCL-004': ['F-ADM-16'], 'NFR-OPS-011': ['NF-OPS-09', 'F-ADM-16'],
 'FR-ADMIN-007': ['F-ADM-18', 'F-ADM-25'], 'NFR-OPS-003': ['F-ADM-25'], 'NFR-OPS-004': ['F-ADM-18', 'F-ADM-25'],
 'NFR-COMP-007': ['F-ADM-25'], 'FR-INT-006': ['F-INT-13', 'F-INT-14', 'NF-STD-02'], 'NFR-SEC-019': ['NF-ARC-02'],
 'FR-MFA-009': ['F-AUTH-10'], 'NFR-DR-008': ['NF-AVL-01'], 'NFR-COST-006': ['NF-OPS-05'],
 # アプリ側の要件で、旧対応表に無かったもの（機能名一覧に対応する機能がある分だけ補う）
 'FR-AUTHZ-004': ['F-ADM-12', 'F-AZ-04'], 'FR-ADMIN-006': ['F-ADM-11', 'F-ADM-12'],
 'FR-ADMIN-011': ['F-AZ-06'], 'NFR-MIG-001': ['NF-MIG-02'], 'NFR-MIG-002': ['NF-MIG-02'],
}
# 特定の要件に紐づかない共通の作業（設計管理・提供資料）。表の末尾に「横断」として出す
CROSS = ['NF-MGT-01', 'NF-MGT-02', 'NF-MGT-03', 'NF-MGT-04', 'NF-MGT-05', 'NF-MGT-06', 'NF-MGT-07', 'NF-DOC-02']
def basename(rid): return re.sub(r'-[ab]$', '', rid)

out, stat = [], collections.Counter()
for r in rm:
    rid, bid = r['要件ID'], basename(r['要件ID'])
    fids = []
    for c in ['① 基本設計', '② 詳細設計', '③ 製造', '④ テスト']:
        for w in r[c].split():
            if WBS2FUNC.get(w) and WBS2FUNC[w] not in fids: fids.append(WBS2FUNC[w])
    via = '工程から逆引き'
    if not fids:
        fids = [f for f in EXTRA.get(rid, EXTRA.get(bid, LEGACY.get(bid, []))) if f in FUNC]
        via = '対応表' if fids else 'なし'
    stat[via] += 1
    fids.sort(key=lambda f: ORDER.get(f, 999))
    if not fids:
        out.append({'要件ID': rid, '要件': r['項目'], '要件の概要': r['概要'], '機能ID': '—',
                    '機能': '—（本基盤に作る機能なし）', '機能の概要': r['担当の理由'] if r['担当の理由'] != '—' else '',
                    '担当': r['担当'], '状況': r['状況'], '引き当て': via})
    for f in fids:
        out.append({'要件ID': rid, '要件': r['項目'], '要件の概要': r['概要'], '機能ID': f,
                    '機能': FUNC[f]['機能名'], '機能の概要': FUNC[f]['概要'],
                    '担当': r['担当'], '状況': r['状況'], '引き当て': via})

for f in CROSS:
    if f in FUNC and float(FUNC[f]['人日'] or 0) > 0:
        out.append({'要件ID': '（横断）', '要件': '特定の要件に紐づかない共通の作業', '要件の概要':
                    '設計書そのものの管理（総則・一覧・追跡・レビュー）と、顧客へ渡す資料。個々の要件ではなく全体に対して発生する',
                    '機能ID': f, '機能': FUNC[f]['機能名'], '機能の概要': FUNC[f]['概要'],
                    '担当': 'インフラ（本基盤）', '状況': '全工程あり', '引き当て': '横断'})

COLS = ['要件ID', '要件', '要件の概要', '機能ID', '機能', '機能の概要', '担当', '状況']
with open(P('SHEET_要件機能マッピング.tsv'), 'w', encoding='utf-8', newline='') as fp:
    w = csv.writer(fp, delimiter='\t', lineterminator='\n'); w.writerow(COLS)
    for o in out: w.writerow([o[c] for c in COLS])

# 未使用の機能（どの要件からも指されていない）
used = {o['機能ID'] for o in out}
unused = [f for f in fl if f['機能ID'] not in used]
byfunc = collections.Counter(o['機能ID'] for o in out if o['機能ID'] != '—')
R = os.path.join(W, '..')
with open(os.path.join(R, 'req-func-matrix-2026-09-07.md'), 'w', encoding='utf-8') as fp:
    fp.write('# 要件と機能の対応表（報告用）\n\n')
    fp.write(f'- **日付**: 2026-09-07 ／ **反映用**: `wbs-text/SHEET_要件機能マッピング.tsv`\n')
    fp.write(f'- **{len(rm)} 要件 × {len(used - {"—"})} 機能 = {len(out)} 行**（1 要件が複数の機能で実現される場合は行を分けた）\n')
    fp.write('- 列は **要件 / 機能 / 要件の概要 / 機能の概要** の 4 本が主。ID と 担当・状況 は絞り込み用で、報告時は隠してよい\n')
    fp.write('- 機能の引き当ては、要件に紐づく WBS 行の機能名から逆引きした（工程に工数が付いている機能）。'
             '工程が無い要件（アプリ側・顧客・他組織・対象外）は要件と機能の対応表から引いた\n\n')
    fp.write('## 内訳\n\n| 区分 | 件数 |\n|---|---:|\n')
    for k, v in stat.most_common(): fp.write(f'| {k} | {v} |\n')
    fp.write(f'| **要件の行数** | **{len(rm)}** |\n| 展開後の行数 | {len(out)} |\n\n')
    fp.write('## 担当別\n\n| 担当 | 行数 | 要件数 |\n|---|---:|---:|\n')
    for k, v in collections.Counter(o['担当'] for o in out).most_common():
        fp.write(f'| {k} | {v} | {len({o["要件ID"] for o in out if o["担当"] == k})} |\n')
    fp.write('\n## 機能が紐づかない要件\n\n')
    none = [o for o in out if o['機能ID'] == '—']
    if none:
        fp.write('| 要件ID | 要件 | 担当 | 状況 |\n|---|---|---|---|\n')
        for o in none: fp.write(f"| {o['要件ID']} | {o['要件']} | {o['担当']} | {o['状況']} |\n")
    else: fp.write('なし\n')
    fp.write('\n## どの要件からも指されていない機能\n\n')
    if unused:
        fp.write('| 機能ID | 機能 | 機能グループ | 人日 |\n|---|---|---|---:|\n')
        for f in unused: fp.write(f"| {f['機能ID']} | {f['機能名']} | {f['機能グループ']} | {f['人日']} |\n")
    else: fp.write('なし\n')
    fp.write('\n## 全 %d 行\n\n| 要件 | 機能 | 要件の概要 | 機能の概要 |\n|---|---|---|---|\n' % len(out))
    for o in out:
        g = lambda s: s.replace('|', '/').replace('\n', ' ')
        fp.write(f"| {g(o['要件'])} | {g(o['機能'])} | {g(o['要件の概要'])} | {g(o['機能の概要'])} |\n")

print(f'{len(out)} 行 / 要件 {len(rm)} / 機能 {len(used - {"—"})}')
print('引き当て:', dict(stat))
print('機能なし要件:', len(none), '/ 未使用機能:', len(unused))
print('1 要件あたり機能数 最大:', collections.Counter(o['要件ID'] for o in out).most_common(3))
