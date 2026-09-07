#!/usr/bin/env python3
"""「本基盤」の使い分けを直す。

- 製品としての Keycloak-Broker の動き・設定・データを指しているもの → Keycloak-Broker
- システム全体（プロジェクトの範囲・契約・WBS）を指しているもの → 本基盤のまま
出力: 各 SHEET_*.tsv を書き換え、SYNC_kihan_fix.tsv（変更したセルの一覧）を作る
"""
import csv, glob, os, re, collections

W = os.path.dirname(os.path.abspath(__file__))
KB = 'Keycloak-Broker'
# 置換する語（前後の文脈ごと）。ここに無い「本基盤」はシステム全体を指すので残す
REP = [
 # --- 製品の動き・設定・データ ---
 ('本基盤で止めたユーザ', f'{KB} で止めたユーザ'),
 ('本基盤で止めた人', f'{KB} で止めた人'),
 ('顧客側と本基盤の食い違い', f'顧客側と {KB} の食い違い'),
 ('本基盤経由で業務システムに', f'{KB} 経由で業務システムに'),
 ('その場で本基盤のユーザとして', f'その場で {KB} のユーザとして'),
 ('顧客IdPを本基盤へ接続', f'顧客IdPを {KB} へ接続'),
 ('顧客IdPを本基盤に接続', f'顧客IdPを {KB} に接続'),
 ('本基盤の SAML 署名', f'{KB} の SAML 署名'),
 ('本基盤の入口を呼ぶ', f'{KB} の入口を呼ぶ'),
 ('本基盤が認証の提供元として', f'{KB} が認証の提供元として'),
 ('本基盤に照会画面は作らない', f'{KB} に照会画面は作らない'),
 ('本基盤の中核で', f'{KB} の中核で'),
 ('本基盤に直接 ID とパスワードで', f'{KB} に直接 ID とパスワードで'),
 ('業務システムへ本基盤がログインを提供し', f'業務システムへ {KB} がログインを提供し'),
 ('新しいアプリを本基盤に接続する', f'新しいアプリを {KB} に接続する'),
 ('本基盤が旧方式（SAML）の提供元として', f'{KB} が旧方式（SAML）の提供元として'),
 ('本基盤で二重に追加認証を求めない', f'{KB} で二重に追加認証を求めない'),
 ('（本基盤の状態は保つ）', f'（{KB} の状態は保つ）'),
 ('本基盤のログイン状態を破棄', f'{KB} のログイン状態を破棄'),
 ('本基盤のログアウトを顧客IdP 側にも', f'{KB} のログアウトを顧客IdP 側にも'),
 ('JWT を出すところまでが本基盤', f'JWT を出すところまでが {KB}'),
 ('属性の宣言と変換は本基盤', f'属性の宣言と変換は {KB}'),
 ('停止と再開は本基盤', f'停止と再開は {KB}'),
 ('振り分けの識別子入力画面とエラー画面は本基盤で作る', f'振り分けの識別子入力画面とエラー画面は {KB} で作る'),
 ('本基盤の証明書の更新', f'{KB} の証明書の更新'),
 ('本基盤の推奨形式', f'{KB} の推奨形式'),
 ('本基盤の推奨方式', f'{KB} の推奨方式'),
 ('本基盤側でも追える', f'{KB} 側でも追える'),
 ('本基盤側に照会の仕組みは作らない', f'{KB} 側に照会の仕組みは作らない'),
]
# 残すもの（確認用・プロジェクト／範囲／契約の話）
KEEP = ['本基盤にも 4 工程あり', '本基盤の対象外', '本基盤では実装しない', '本基盤側で実装しない範囲',
        '本基盤の運用者', '既存の認証から本基盤へ', '既存の仕組みから本基盤へ', '顧客と本基盤のどちらが',
        '本基盤側の手順が無いと', '出力と集約は本基盤', '設計は本基盤', '保持と消去の方針は本基盤',
        '切替の計画は本基盤']

log = []
for f in sorted(glob.glob(os.path.join(W, 'SHEET_*.tsv'))):
    rows = list(csv.DictReader(open(f, encoding='utf-8'), delimiter='\t'))
    if not rows: continue
    cols = list(rows[0].keys()); changed = False
    for r in rows:
        rid = r.get('要件ID') or r.get('ID') or r.get('機能名') or r.get('機能グループ') or ''
        for c in cols:
            v = r[c]
            if not isinstance(v, str) or '本基盤' not in v: continue
            nv = v
            for a, b in REP: nv = nv.replace(a, b)
            if nv != v:
                r[c] = nv; changed = True
                log.append([os.path.basename(f).replace('SHEET_', '').replace('.tsv', ''), rid, c, nv])
    if changed:
        with open(f, 'w', encoding='utf-8', newline='') as fp:
            w = csv.writer(fp, delimiter='\t', lineterminator='\n'); w.writerow(cols)
            for r in rows: w.writerow([r[c] for c in cols])
with open(os.path.join(W, 'SYNC_kihan_fix.tsv'), 'w', encoding='utf-8', newline='') as fp:
    w = csv.writer(fp, delimiter='\t', lineterminator='\n')
    w.writerow(['シート', '対象', '列', '新しい値'])
    for x in log: w.writerow(x)

rest = collections.Counter()
for f in sorted(glob.glob(os.path.join(W, 'SHEET_*.tsv'))):
    for r in csv.DictReader(open(f, encoding='utf-8'), delimiter='\t'):
        for v in r.values():
            if isinstance(v, str): rest[os.path.basename(f)] += v.count('本基盤')
print(f'置換したセル {len(log)} 件')
print('残った「本基盤」（システム全体を指すもの）:')
for k, v in rest.most_common():
    if v: print(f'   {k:34s} {v}')
print('  計', sum(rest.values()))
