#!/usr/bin/env python3
"""要件を行、工程を列にしたマッピングを作る。

- 要件 → 機能ID の対応を定義し、機能ID → 各工程の WBS 行を引く
- ④ テストは既に「対応要件」列を持っているので、そちらを優先して使う
出力: SHEET_要件一覧.tsv（種別列を追加）/ SHEET_要件マッピング.tsv / ../requirements-mapping-2026-09-07.md
"""
import csv, os, re, collections

W = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(W, '..')
L = lambda n: list(csv.DictReader(open(os.path.join(W, n), encoding='utf-8'), delimiter='\t'))
req = L('SHEET_要件一覧.tsv'); bd = L('SHEET_基本設計.tsv'); dm = L('SHEET_詳細設計_製造.tsv')
ts = L('SHEET_テスト.tsv'); fl = L('SHEET_機能名一覧.tsv')
FID = {r['機能ID']: r['機能名'] for r in fl}

# 要件ID -> 機能ID の対応
M = {
'FR-AUTH-001': ['F-AUTH-01'], 'FR-AUTH-002': ['F-AUTH-05', 'F-INT-13'], 'FR-AUTH-003': ['F-AUTH-05', 'F-INT-13'],
'FR-AUTH-004': ['F-AZ-07'], 'FR-AUTH-005': ['F-AZ-08'], 'FR-AUTH-006': [], 'FR-AUTH-007': [], 'FR-AUTH-008': [],
'FR-AUTH-009': ['F-AUTH-01'], 'FR-AUTH-010': ['F-AUTH-01'], 'FR-AUTH-011': ['F-AUTH-20', 'F-AUTH-21'],
'FR-AUTH-012': ['F-AUTH-01'], 'FR-AUTH-013': ['F-AUTH-18'], 'FR-AUTH-014': ['F-AUTH-19'], 'FR-AUTH-015': [],
'FR-FED-001': ['F-AUTH-05', 'F-ADM-16'], 'FR-FED-002': ['F-AUTH-05', 'F-ADM-16'], 'FR-FED-003': ['F-AUTH-05', 'F-ADM-16'],
'FR-FED-004': ['F-AUTH-05', 'F-ADM-16'], 'FR-FED-005': ['F-AUTH-06', 'F-ADM-16'], 'FR-FED-006': ['F-INT-01'],
'FR-FED-007': [], 'FR-FED-008': ['F-PROV-01'], 'FR-FED-009': ['F-PROV-08', 'F-PROV-02'],
'FR-FED-010': ['F-AZ-05', 'NF-ARC-04'], 'FR-FED-011': ['F-ADM-16', 'F-ADM-14'], 'FR-FED-012': [],
'FR-FED-013': ['F-AUTH-02', 'F-AUTH-04', 'F-AUTH-25'], 'FR-FED-014': [],
'FR-MFA-001': ['F-AUTH-10', 'F-AUTH-12'], 'FR-MFA-002': ['F-AUTH-10', 'F-AUTH-12'], 'FR-MFA-003': [],
'FR-MFA-004': [], 'FR-MFA-005': ['F-AUTH-15'], 'FR-MFA-006': [], 'FR-MFA-007': ['F-AUTH-10'],
'FR-MFA-008': [], 'FR-MFA-009': ['F-AUTH-10'],
'FR-SSO-001': ['F-AUTH-23'], 'FR-SSO-002': ['F-AUTH-05', 'F-AUTH-23'], 'FR-SSO-003': ['NF-DOC-01'],
'FR-SSO-004': ['F-AUTH-24'], 'FR-SSO-005': ['F-AUTH-24'], 'FR-SSO-006': [], 'FR-SSO-007': ['F-AUTH-24'],
'FR-SSO-008': ['F-AUTH-23'], 'FR-SSO-009': ['F-PROV-10', 'F-AZ-10'], 'FR-SSO-010': ['F-ADM-10'],
'FR-AUTHZ-001': ['F-AZ-10'], 'FR-AUTHZ-002': ['F-AZ-05'], 'FR-AUTHZ-003': ['F-AZ-04'], 'FR-AUTHZ-004': [],
'FR-AUTHZ-005': ['F-AZ-07'], 'FR-AUTHZ-006': ['F-AZ-10', 'F-PROV-08'], 'FR-AUTHZ-007': ['NF-DOC-01'],
'FR-AUTHZ-008': ['NF-ARC-04', 'F-AZ-10'], 'FR-AUTHZ-009': [], 'FR-AUTHZ-010': [],
'FR-USER-001': ['F-ADM-03', 'F-ADM-03', 'F-ADM-05'], 'FR-USER-002': ['F-PROV-08'], 'FR-USER-003': ['F-PROV-03', 'F-PROV-03', 'F-PROV-03', 'F-PROV-03'],
'FR-USER-004': ['F-AUTH-01'], 'FR-USER-005': ['F-ADM-01'], 'FR-USER-006': ['F-PROV-10', 'F-PROV-11'],
'FR-USER-007': ['F-PROV-03'], 'FR-USER-008': ['F-ADM-12'], 'FR-USER-009': ['F-ADM-20'],
'FR-USER-010': ['F-ADM-07'], 'FR-USER-011': ['F-ADM-24', 'F-BAT-09'], 'FR-USER-012': ['F-ADM-08'],
'FR-ADMIN-001': ['F-ADM-01'], 'FR-ADMIN-002': ['F-ADM-14', 'F-ADM-23'], 'FR-ADMIN-003': ['F-ADM-16', 'F-ADM-17'],
'FR-ADMIN-004': ['F-INT-13'], 'FR-ADMIN-005': ['F-ADM-12'], 'FR-ADMIN-006': [], 'FR-ADMIN-007': ['F-ADM-18', 'F-ADM-25'],
'FR-ADMIN-008': ['F-ADM-25'], 'FR-ADMIN-009': ['F-AZ-05', 'F-ADM-15'], 'FR-ADMIN-010': ['F-AZ-06'],
'FR-ADMIN-011': [], 'FR-ADMIN-012': ['F-AUTH-25', 'F-AUTH-26'],
'FR-INT-001': ['F-AUTH-05', 'F-AZ-10'], 'FR-INT-002': ['F-INT-13'], 'FR-INT-003': ['F-BAT-04', 'F-INT-13'],
'FR-INT-004': ['F-AUTH-06', 'F-INT-01'], 'FR-INT-005': ['F-INT-04'], 'FR-INT-006': ['F-INT-13', 'NF-STD-02'],
'FR-INT-007': ['NF-DOC-01'], 'FR-INT-008': ['F-ADM-25'], 'FR-INT-009': [], 'FR-INT-010': ['NF-STD-04'],
'NFR-AVL-001': ['NF-AVL-03'], 'NFR-AVL-002': ['NF-OPS-05'], 'NFR-AVL-003': ['NF-ARC-03'],
'NFR-AVL-004': ['NF-ARC-03'], 'NFR-AVL-005': ['NF-ARC-03', 'NF-ARC-07'], 'NFR-AVL-006': ['NF-OPS-05'],
'NFR-PERF-001': ['NF-PRF-01'], 'NFR-PERF-002': ['NF-PRF-01', 'NF-PRF-03'], 'NFR-PERF-003': ['NF-DOC-01'],
'NFR-PERF-004': ['NF-PRF-01'], 'NFR-PERF-005': ['NF-STD-01'], 'NFR-PERF-006': ['NF-PRF-03'],
'NFR-PERF-007': ['NF-PRF-01', 'NF-PRF-04'], 'NFR-PERF-008': ['NF-ARC-07'],
'NFR-SCL-001': ['NF-PRF-02'], 'NFR-SCL-002': ['NF-PRF-02'], 'NFR-SCL-003': ['NF-PRF-02', 'F-ADM-16'],
'NFR-SCL-004': ['F-ADM-16'], 'NFR-SCL-005': ['NF-ARC-03'], 'NFR-SCL-006': [], 'NFR-SCL-007': ['NF-ARC-07'],
'NFR-SEC-001': ['NF-SEC-02', 'NF-ARC-02'], 'NFR-SEC-002': ['NF-SEC-02'], 'NFR-SEC-003': ['F-AZ-10', 'F-BAT-04'],
'NFR-SEC-004': ['F-AZ-10'], 'NFR-SEC-005': ['F-AUTH-23'], 'NFR-SEC-006': ['F-AZ-10'],
'NFR-SEC-007': ['F-AUTH-23'], 'NFR-SEC-008': ['F-PROV-10', 'F-ADM-10'], 'NFR-SEC-009': ['F-AUTH-01'],
'NFR-SEC-010': ['F-AUTH-21'], 'NFR-SEC-011': [], 'NFR-SEC-012': [], 'NFR-SEC-013': ['NF-SEC-01'],
'NFR-SEC-014': ['NF-OPS-05'], 'NFR-SEC-015': ['NF-SEC-02', 'F-BAT-05'], 'NFR-SEC-016': ['NF-ARC-02'],
'NFR-SEC-017': ['NF-OPS-04', 'NF-ARC-02'], 'NFR-SEC-018': ['NF-SEC-01'], 'NFR-SEC-019': ['NF-ARC-02'],
'NFR-SEC-020': ['F-AUTH-23'],
'NFR-DR-001': ['NF-AVL-01', 'NF-AVL-03'], 'NFR-DR-002': ['NF-AVL-01', 'NF-AVL-03'], 'NFR-DR-003': ['NF-AVL-01'],
'NFR-DR-004': ['NF-AVL-02'], 'NFR-DR-005': ['NF-AVL-02'], 'NFR-DR-006': ['NF-AVL-01'],
'NFR-DR-007': ['NF-AVL-01'], 'NFR-DR-008': ['NF-AVL-01'],
'NFR-OPS-001': ['NF-OPS-01'], 'NFR-OPS-002': ['NF-OPS-01'], 'NFR-OPS-003': ['F-ADM-25'],
'NFR-OPS-004': ['F-ADM-18', 'F-ADM-25'], 'NFR-OPS-005': ['NF-OPS-05'], 'NFR-OPS-006': ['NF-OPS-05'],
'NFR-OPS-007': ['NF-OPS-08'], 'NFR-OPS-008': ['NF-OPS-03', 'NF-OPS-08'], 'NFR-OPS-009': ['NF-OPS-10', 'NF-OPS-07'],
'NFR-OPS-010': ['NF-STD-04'], 'NFR-OPS-011': ['NF-OPS-09', 'F-ADM-16'],
'NFR-COMP-001': ['NF-SEC-03'], 'NFR-COMP-002': [], 'NFR-COMP-003': [], 'NFR-COMP-004': [], 'NFR-COMP-005': [],
'NFR-COMP-006': [], 'NFR-COMP-007': ['F-ADM-25'], 'NFR-COMP-008': ['NF-ARC-01'],
'NFR-COMP-009': ['F-ADM-24'], 'NFR-COMP-010': ['F-ADM-25', 'F-ADM-18'], 'NFR-COMP-011': ['F-BAT-04', 'F-BAT-05', 'F-BAT-07', 'NF-SEC-02'],
'NFR-COST-001': ['NF-OPS-07'], 'NFR-COST-002': ['NF-OPS-07'], 'NFR-COST-003': ['NF-OPS-07'],
'NFR-COST-004': ['NF-OPS-07', 'NF-AVL-01'], 'NFR-COST-005': ['NF-OPS-10'], 'NFR-COST-006': ['NF-OPS-05'],
'NFR-COST-007': ['NF-OPS-07'], 'NFR-COST-008': ['NF-OPS-07'], 'NFR-COST-009': ['NF-OPS-07'],
'NFR-MIG-001': [], 'NFR-MIG-002': [], 'NFR-MIG-003': ['F-AUTH-05', 'NF-STD-02'],
'NFR-MIG-004': ['F-ADM-23'], 'NFR-MIG-005': ['NF-MIG-02'],
}
bad = [k for k, v in M.items() for f in v if f not in FID]
assert not bad, bad
assert len(M) == len(req), (len(M), len(req))

# 機能ID -> 各工程の WBS ID
byfunc = collections.defaultdict(lambda: {'1': [], '2': [], '3': [], '4': []})
name2fid = {v: k for k, v in FID.items()}
for r in bd:
    f = name2fid.get(r['機能名'])
    if f and r['スコープ'] == '対象': byfunc[f]['1'].append(r['ID'])
for r in dm:
    f = name2fid.get(r['機能名'])
    if f: byfunc[f]['2' if r['詳細設計 人日'] else '3'].append(r['ID'])
# ④ は「対応要件」列を優先
ts_by_req = collections.defaultdict(list)
for r in ts:
    for m in re.findall(r'(?:FR|NFR)-[A-Z]+-\d+', r['対応要件']):
        ts_by_req[m].append(r['ID'])
    f = name2fid.get(r['機能名'])
    if f: byfunc[f]['4'].append(r['ID'])

# 種別列を要件一覧へ追加
for r in req: r['種別'] = '機能要件' if r['要件ID'].startswith('FR-') else '非機能要件'
RCOLS = ['要件ID', '種別', '分類', '項目', '概要', '優先度', '担当範囲', '調整の理由', '出典の節']
with open(os.path.join(W, 'SHEET_要件一覧.tsv'), 'w', encoding='utf-8', newline='') as fp:
    w = csv.writer(fp, delimiter='\t', lineterminator='\n'); w.writerow(RCOLS)
    for r in req: w.writerow([r[c] for c in RCOLS])

# マッピング
J = lambda xs: ' '.join(sorted(set(xs))) if xs else ''
out = []
for r in req:
    fids = M[r['要件ID']]
    p = {k: [] for k in '1234'}
    for f in fids:
        for k in '1234': p[k] += byfunc[f][k]
    if ts_by_req.get(r['要件ID']): p['4'] = ts_by_req[r['要件ID']]
    covered = sum(1 for k in '1234' if p[k])
    if r['担当範囲'] in ('Keycloak-Broker',):
        if covered == 4: st = '全工程あり'
        elif covered == 0: st = '🔴 どの工程にも無い'
        else: st = '🔺 一部の工程のみ'
    elif r['担当範囲'] == '対象外': st = '対象外'
    else: st = f'他者責務（{r["担当範囲"]}）'
    out.append({'要件ID': r['要件ID'], '種別': r['種別'], '分類': r['分類'], '項目': r['項目'],
                '優先度': r['優先度'], '担当範囲': r['担当範囲'],
                '対応する機能': ' / '.join(FID[f] for f in fids),
                '① 基本設計': J(p['1']), '② 詳細設計': J(p['2']), '③ 製造': J(p['3']), '④ テスト': J(p['4']),
                '状況': st})
MCOLS = ['要件ID', '種別', '分類', '項目', '優先度', '担当範囲', '対応する機能', '① 基本設計', '② 詳細設計', '③ 製造', '④ テスト', '状況']
with open(os.path.join(W, 'SHEET_要件マッピング.tsv'), 'w', encoding='utf-8', newline='') as fp:
    w = csv.writer(fp, delimiter='\t', lineterminator='\n'); w.writerow(MCOLS)
    for o in out: w.writerow([o[c] for c in MCOLS])

st = collections.Counter(o['状況'] for o in out)
kb = [o for o in out if o['担当範囲'] == 'Keycloak-Broker']
with open(os.path.join(R, 'requirements-mapping-2026-09-07.md'), 'w', encoding='utf-8') as fp:
    fp.write('# 要件 × 工程のマッピング\n\n- **日付**: 2026-09-07\n')
    fp.write(f'- **要件 {len(out)} 件**を行、**① 基本設計 / ② 詳細設計 / ③ 製造 / ④ テスト**を列にした\n')
    fp.write('- 各セルには対応する WBS の ID を入れた。**空欄はその工程に作業が無い**ことを意味する\n')
    fp.write('- **反映用**: `wbs-text/SHEET_要件マッピング.tsv`（要件一覧には種別の列を追加した）\n\n')
    fp.write('## 状況\n\n| 状況 | 件数 |\n|---|---:|\n')
    for k in ['全工程あり', '🔺 一部の工程のみ', '🔴 どの工程にも無い', '他者責務（Keycloak-IdP）',
              '他者責務（アプリ）', '他者責務（顧客IdP）', '対象外']:
        if st[k]: fp.write(f'| {k} | {st[k]} |\n')
    fp.write(f'| **計** | **{len(out)}** |\n\n')
    fp.write(f'**本基盤が作る {len(kb)} 件**のうち、全工程そろっているのが {sum(1 for o in kb if o["状況"]=="全工程あり")} 件、'
             f'一部のみが {sum(1 for o in kb if "一部" in o["状況"])} 件、どの工程にも無いのが '
             f'{sum(1 for o in kb if "どの工程にも" in o["状況"])} 件。\n\n')
    ng = [o for o in kb if 'どの工程にも' in o['状況']]
    if ng:
        fp.write('## 🔴 本基盤が作るのに、どの工程にも作業が無い要件\n\n| 要件ID | 項目 | 優先度 |\n|---|---|---|\n')
        for o in ng: fp.write(f"| {o['要件ID']} | {o['項目']} | {o['優先度']} |\n")
        fp.write('\n')
    part = [o for o in kb if '一部' in o['状況']]
    if part:
        fp.write('## 🔺 一部の工程にしか作業が無い要件\n\n| 要件ID | 項目 | ① | ② | ③ | ④ |\n|---|---|:-:|:-:|:-:|:-:|\n')
        for o in part:
            fp.write(f"| {o['要件ID']} | {o['項目']} | {'○' if o['① 基本設計'] else '—'} | {'○' if o['② 詳細設計'] else '—'} "
                     f"| {'○' if o['③ 製造'] else '—'} | {'○' if o['④ テスト'] else '—'} |\n")
        fp.write('\n')
    fp.write('## 全 %d 件\n\n| 要件ID | 種別 | 項目 | 担当範囲 | ① | ② | ③ | ④ | 状況 |\n|---|---|---|---|:-:|:-:|:-:|:-:|---|\n' % len(out))
    for o in out:
        fp.write(f"| {o['要件ID']} | {o['種別'][:2]} | {o['項目'][:34]} | {o['担当範囲']} | {'○' if o['① 基本設計'] else '—'} "
                 f"| {'○' if o['② 詳細設計'] else '—'} | {'○' if o['③ 製造'] else '—'} | {'○' if o['④ テスト'] else '—'} | {o['状況']} |\n")
print(f'{len(out)} 件')
for k, v in st.most_common(): print(f'  {k:22s} {v}')
print('種別:', collections.Counter(o['種別'] for o in out))
