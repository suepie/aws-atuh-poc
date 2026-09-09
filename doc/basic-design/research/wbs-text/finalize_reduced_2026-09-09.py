#!/usr/bin/env python3
"""縮小版の列を残りのシートにも足し、サマリを作り直す（2026-09-09）。"""
import csv, os, collections
W=os.path.dirname(os.path.abspath(__file__)); P=lambda n: os.path.join(W,n)
def load(n):
    with open(P(n),encoding='utf-8',newline='') as fp:
        rd=csv.reader(fp,delimiter='\t'); h=next(rd)
        return h,[dict(zip(h,r+['']*(len(h)-len(r)))) for r in rd if any(r)]
def save(n,h,rows):
    with open(P(n),'w',encoding='utf-8',newline='') as fp:
        w=csv.writer(fp,delimiter='\t',lineterminator='\n'); w.writerow(h)
        for r in rows: w.writerow([r.get(c,'') for c in h])
num=lambda x: float(x) if str(x).strip() else 0.0
def fmt(x):
    x=round(x*4)/4
    return '' if x==0 else (str(int(x)) if float(x).is_integer() else str(x))
RANK={'対象':2,'一部':1,'対象外':0}; UNRANK={2:'対象',1:'一部',0:'対象外'}

hb,bd=load('SHEET_基本設計.tsv'); hd,dm=load('SHEET_詳細設計_製造.tsv'); ht,ts=load('SHEET_テスト.tsv')
# 機能名 → 縮小版の区分・理由（WBS 行の最大値を代表にする）
byfunc=collections.defaultdict(lambda:(0,''))
for s in (bd,dm,ts):
    for r in s:
        k=r['機能名']; cur=byfunc[k]
        if RANK[r['縮小版']]>cur[0]: byfunc[k]=(RANK[r['縮小版']], r['縮小版の理由'])

def addcol(h,rows,getter,cols=('縮小版','縮小版の理由')):
    for c in cols:
        if c not in h: h.append(c)
    for r in rows:
        v=getter(r)
        r['縮小版'],r['縮小版の理由']=v

# 機能名一覧
hf,fl=load('SHEET_機能名一覧.tsv')
if '縮小版 人日' not in hf: hf+= ['縮小版','縮小版 人日','縮小版の理由']
for f in fl:
    k,why=byfunc.get(f['機能名'],(0,'この工程に作業が無い'))
    f['縮小版']=UNRANK[k]; f['縮小版の理由']=why
    f['縮小版 人日']=fmt(sum(num(r['縮小版 人日']) for r in bd if r['機能名']==f['機能名']))
save('SHEET_機能名一覧.tsv',hf,fl)

# 機能グループ一覧
hg,fg=load('SHEET_機能グループ一覧.tsv')
if '縮小版 人日' not in hg: hg+=['縮小版','縮小版 人日']
for g in fg:
    ks=[RANK[f['縮小版']] for f in fl if f['機能グループ']==g['機能グループ']]
    g['縮小版']=UNRANK[max(ks)] if ks else '対象外'
    g['縮小版 人日']=fmt(sum(num(r['縮小版 人日']) for r in bd if r['機能グループ']==g['機能グループ']))
save('SHEET_機能グループ一覧.tsv',hg,fg)

# サマリ（作り直し）
hs,_=load('SHEET_サマリ工程別.tsv')
for c in ['縮小版','縮小版 ①','縮小版 ②','縮小版 ③','縮小版 ④','縮小版 合計']:
    if c not in hs: hs.append(c)
sm=[]
for f in fl:
    n=f['機能名']
    a=sum(num(r['人日']) for r in bd if r['機能名']==n and r['スコープ']=='対象')
    b=sum(num(r['詳細設計 人日']) for r in dm if r['機能名']==n)
    c=sum(num(r['製造 人日']) for r in dm if r['機能名']==n)
    d=sum(num(r['人日']) for r in ts if r['機能名']==n)
    ra=sum(num(r['縮小版 人日']) for r in bd if r['機能名']==n)
    rb=sum(num(r['縮小版 詳細設計 人日']) for r in dm if r['機能名']==n)
    rc=sum(num(r['縮小版 製造 人日']) for r in dm if r['機能名']==n)
    rd_=sum(num(r['縮小版 人日']) for r in ts if r['機能名']==n)
    k=sum(1 for r in dm if r['機能名']==n)+sum(1 for r in ts if r['機能名']==n)
    if a+b+c+d>0:
        sm.append({'機能グループ':f['機能グループ'],'機能名':n,'① 基本設計':fmt(a),'② 詳細設計':fmt(b),
                   '③ 製造':fmt(c),'④ テスト':fmt(d),'合計':fmt(a+b+c+d),'②③④ 行数':str(k),
                   '縮小版':f['縮小版'],'縮小版 ①':fmt(ra),'縮小版 ②':fmt(rb),'縮小版 ③':fmt(rc),
                   '縮小版 ④':fmt(rd_),'縮小版 合計':fmt(ra+rb+rc+rd_)})
save('SHEET_サマリ工程別.tsv',hs,sm)

# 提供API一覧
ha,api=load('SHEET_API提供一覧.tsv')
if '縮小版' not in ha: ha+=['縮小版','縮小版の理由']
for r in api:
    k,why=byfunc.get(r['機能名'],(0,'この機能は縮小版の対象外'))
    r['縮小版']=UNRANK[k]; r['縮小版の理由']=why
save('SHEET_API提供一覧.tsv',ha,api)

# 要件マッピング（参照している WBS 行から導く）
hr,rm=load('SHEET_要件マッピング.tsv')
if '縮小版' not in hr: hr+=['縮小版']
W2={r['ID']:r['縮小版'] for s in (bd,dm,ts) for r in s}
for r in rm:
    ks=[RANK[W2[x]] for c in ['① 基本設計','② 詳細設計','③ 製造','④ テスト'] for x in r[c].split() if x in W2]
    r['縮小版']=UNRANK[max(ks)] if ks else '対象外'
save('SHEET_要件マッピング.tsv',hr,rm)

print(f"サマリ {len(sm)} 行 / フル {fmt(sum(num(r['合計']) for r in sm))} / 縮小版 {fmt(sum(num(r['縮小版 合計']) for r in sm))}")
for n,rows in [('機能名一覧',fl),('機能グループ一覧',fg),('提供API一覧',api),('要件マッピング',rm)]:
    print(f"  {n} {len(rows)} 行: {dict(collections.Counter(r['縮小版'] for r in rows))}")
