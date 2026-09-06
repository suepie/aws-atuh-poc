#!/usr/bin/env python3
"""用語の統一・体裁の修正・ID の振り直しを、Excel の現在値に対して一括で適用する。

用語の決定（2026-09-07）:
  1. 利用者 → ユーザ
  2. 認証製品は Keycloak と書く。2 つあるので Keycloak-Broker / Keycloak-IdP で区別する
  3. 接続先 / 顧客認証システム → 顧客IdP
  4. テナント → 顧客（組織は「顧客の中の部署」として使い分ける）
  5. 通行証 → JWT
  6. ブローカー → Keycloak-Broker
あわせて実施:
  - HI-03〜08 の成果物欄、テストの前提欄の空欄を埋める
  - 分類を 35 種類 → 16 種類に統一
  - 運用シートの人日を小数第 1 位に丸める
  - ID を表示順に振り直す
出力: SYNC_全シート.tsv（シートごと差し替え用）と ../excel-terms-2026-09-07.md
"""
import json, csv, re, os, collections

W = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(W, '..')
d = json.load(open('/tmp/all.json'))
S = lambda x: '' if x is None else str(x)

# ================= 用語の置換 =================
# 順番に意味がある
RULES = [
 # 2・6. Keycloak の書き分け
 ('IdP-Keycloak', 'Keycloak-IdP'),
 ('Broker-Keycloak', 'Keycloak-Broker'),
 ('認証製品の版', 'Keycloak の版'), ('認証製品を更新', 'Keycloak を更新'),
 ('認証製品の導入部品', 'Keycloak の導入部品'), ('認証製品の更新', 'Keycloak の更新'),
 ('製品ベンダー', 'Keycloak のベンダー'), ('製品更新', 'Keycloak の更新'),
 ('認証製品', 'Keycloak-Broker'),
 ('ブローカー側', 'Keycloak-Broker 側'), ('ブローカーでは', 'Keycloak-Broker では'),
 ('ブローカーが', 'Keycloak-Broker が'), ('ブローカーの', 'Keycloak-Broker の'),
 ('ブローカー', 'Keycloak-Broker'),
 # 3. 顧客IdP
 ('顧客の認証システム', '顧客IdP'), ('顧客認証システム', '顧客IdP'),
 ('顧客 IdP', '顧客IdP'),
 ('接続先（顧客IdP）管理', '顧客IdP管理'),
 ('接続先の選択（1 テナントに複数 IdP）', '顧客IdPの選択（1 顧客に複数）'),
 ('接続先の自動振り分け', '顧客IdPの自動振り分け'),
 ('接続先の登録', '顧客IdPの登録'), ('接続先を登録', '顧客IdPを登録'),
 ('接続先の設定', '顧客IdPの設定'), ('接続先一覧', '顧客IdP一覧'),
 ('接続先が', '顧客IdPが'), ('接続先を', '顧客IdPを'), ('接続先の', '顧客IdPの'),
 ('接続先へ', '顧客IdPへ'), ('接続先に', '顧客IdPに'), ('接続先は', '顧客IdPは'),
 ('接続先', '顧客IdP'),
 ('IdP ごとの', '顧客IdPごとの'), ('IdP 属性', '顧客IdP属性'),
 ('IdP 側の責務', 'Keycloak-IdP 側の責務'), ('IdP 側の引き渡し', 'Keycloak-IdP 側の引き渡し'),
 ('IdP 側は基盤', 'Keycloak-IdP 側は基盤'), ('IdP 側の基盤', 'Keycloak-IdP 側の基盤'),
 ('IdP として成立させる', '顧客IdPを持たない顧客の受け皿として成立させる'),
 # 4. 顧客
 ('顧客（テナント）', '顧客'), ('テナント管理者', '顧客の管理者'),
 ('テナント越境', '顧客越境'), ('テナントを越えて', '顧客を越えて'),
 ('テナントの', '顧客の'), ('テナントに', '顧客に'), ('テナントが', '顧客が'),
 ('テナントを', '顧客を'), ('テナント', '顧客'),
 # 5. JWT
 ('通行証（JWT）', 'JWT'), ('通行証', 'JWT'),
 ('トークン発行・交換', 'JWT の発行・交換'), ('システム間トークン', 'システム間 JWT'),
 ('トークンの交換', 'JWT の交換'), ('トークン取得・保存', 'JWT の取得・保存'),
 # 1. ユーザ
 ('利用者', 'ユーザ'),
 # 表記の統一
 ('日入替', '日ごとの入れ替え'), ('認証基盤の運用者', '本基盤の運用者'),
]
def conv(s):
    if not isinstance(s, str): return s
    for a, b in RULES: s = s.replace(a, b)
    s = re.sub(r'ユーザユーザ', 'ユーザ', s)
    s = re.sub(r'顧客IdPIdP', '顧客IdP', s)
    s = re.sub(r'Keycloak-Keycloak', 'Keycloak', s)
    # 助詞・空白の整形
    s = s.replace('JWTに', 'JWT に').replace('JWTを', 'JWT を').replace('JWTの', 'JWT の')
    s = s.replace('システム間 JWTの', 'システム間 JWT の')
    s = s.replace('（Keycloak-Broker側）', '（Keycloak-Broker 側）')
    s = s.replace('Keycloak-Broker側', 'Keycloak-Broker 側')
    s = s.replace('のの', 'の')
    return s

# ================= 体裁の修正 =================
HI = {'HI-03': 'レビュー記録。2 回目の指摘が一覧化されている',
      'HI-04': '改訂済みの設計書。2 回目の指摘がすべて処理されている',
      'HI-05': 'レビュー記録。3 回目の指摘が一覧化されている',
      'HI-06': '改訂済みの設計書。3 回目の指摘がすべて処理されている',
      'HI-07': 'レビュー記録。4 回目の指摘が一覧化されている',
      'HI-08': '改訂済みの設計書。4 回目の指摘がすべて処理されている'}
CLS = {'H-A 全体・方式設計': 'HA 全体・方式設計', 'H-B 機能設計': 'HB 機能設計',
 'H-D データ設計': 'HD データ設計', 'H-E IF設計': 'HE つなぎ目設計', 'H-E つなぎ目設計': 'HE つなぎ目設計',
 'H-G 権限・監査': 'HG 権限・監査', 'H-H 運用補完': 'HH 運用設計', 'H-I レビュー・合意': 'HI レビュー・合意',
 'H-J プロダクト固有設計': 'HJ Keycloak の作り込み', 'HJ Keycloak-Broker の作り込み': 'HJ Keycloak の作り込み',
 'H-K 契約・顧客提供成果物': 'HK 顧客提供成果物', 'H-L 認証実装ガイド': 'GD アプリ向けガイド',
 'G-1 Runbook': 'G 手順書', 'G 手順書': 'G 手順書', 'G-3': 'G 運用設計', 'G-4 drawio清書': 'G 構成図',
 'A-1 仮定値の扱い': 'A 調査・PoC', 'E-1 dev/stg': 'E 方式判断', 'E-2': 'E 方式判断',
 'E-4': 'E 方式判断', 'E-5': 'E 方式判断', 'D-9': 'D 判断', 'D-11': 'D 判断', 'D-12': 'D 判断',
 'D-15': 'D 判断', 'D-18 DR再判断': 'D 判断', 'D-18 DR改訂': 'D 判断', 'D-20': 'D 判断'}
TPRE = {'振り分けできないときの切替': '自社拡張の実装が完了していること', '顧客IdPの選択': '自社拡張の実装が完了していること',
 '初回登録と属性の更新': 'A 結合が完了していること', 'ログインのたびの属性の追随': 'A 結合が完了していること',
 '顧客側からの更新の反映': '受信窓口の実装が完了していること', '削除通知の読み替え': '受信窓口の実装が完了していること',
 '顧客側からの検索': '受信窓口の実装が完了していること', '登録された経路の区分': 'A 結合が完了していること',
 '停止済みユーザの再開': '停止と再開の実装が完了していること', '業務システム側のユーザ自動作成': '業務システムの検証環境が用意できていること',
 '業務システムから他アプリへの連携': '業務システムの検証環境が用意できていること', '署名鍵の入れ替え': '鍵管理の構築が完了していること',
 '接続用パスワードの入れ替え': '鍵管理の構築が完了していること', '証明書の期限監視': '期限監視の実装が完了していること',
 'テスト環境の構築と維持': '—（テストの前提そのもの）', 'テストデータの作成': 'テスト環境の構築が完了していること',
 '回帰テストの自動化': 'B 総合の試験仕様が確定していること', '不具合の管理と是正の確認': '—（テスト期間を通じて実施）',
 'テスト計画・仕様の作成とレビュー': '基本設計が承認されていること'}

# ================= 適用 =================
bd, dm, ts, fl, gl, sm, op = (d[k] for k in ['bd', 'dm', 'ts', 'fl', 'gl', 'sm', 'op'])
for r in bd:
    for c in list(r): r[c] = conv(S(r[c]))
    if r['ID'] in HI: r['成果物と完了条件'] = HI[r['ID']]
    if r['ID'] == 'D-15': r['成果物と完了条件'] = '決定記録。一時的に強い権限を出す仕組みをどこに置くかが 1 つに確定している'
    r['分類'] = CLS.get(r['分類'], r['分類'])
for rows in (dm, ts, fl, gl, sm, op):
    for r in rows:
        for c in list(r): r[c] = conv(S(r[c]))
for r in ts:
    if not r['前提'].strip(): r['前提'] = TPRE.get(r['テスト項目'], '—')
for r in op:
    for c in ['初年度 人日', '定常 人日']: r[c] = f'{float(r[c]):.1f}'

# ID の振り直し（表示順）
seq = collections.Counter()
for r in dm:
    p = r['ID'][:3]; seq[p] += 1; r['ID'] = f'{p}-{seq[p]:02d}'
PRE = {'A 結合': 'IT', 'B 総合': 'ST', 'C 実機': 'RI', 'D 性能': 'PT', 'E 可用性・災害復旧': 'DR',
       'F セキュリティ': 'SEC', 'G 運用': 'OP', 'H 受入': 'UAT', 'I テスト共通': 'TE'}
seq = collections.Counter()
for r in ts:
    p = PRE[r['区分']]; seq[p] += 1; r['ID'] = f'{p}-{seq[p]:02d}'

# 機能名一覧の行数・人日を基本設計から計算し直す
n2 = collections.Counter(); b2 = collections.Counter(); t2 = collections.Counter()
for r in bd:
    n2[r['機能名']] += 1; b2[r['機能名']] += float(r['人日'] or 0)
    if r['スコープ'] == '対象': t2[r['機能名']] += float(r['人日'] or 0)
for r in fl:
    r['行数'] = str(n2[r['機能名']]); r['人日'] = f"{b2[r['機能名']]:g}"; r['うち対象'] = f"{t2[r['機能名']]:g}"
gn = collections.Counter(); gd = collections.Counter()
for r in bd: gn[r['機能グループ']] += 1; gd[r['機能グループ']] += float(r['人日'] or 0)
for r in gl: r['行数'] = str(gn[r['機能グループ']]); r['人日'] = f"{gd[r['機能グループ']]:g}"
# サマリを作り直す
b = collections.Counter(); s2 = collections.Counter(); s3 = collections.Counter(); s4 = collections.Counter(); cnt = collections.Counter()
for r in bd:
    if r['スコープ'] == '対象': b[(r['機能グループ'], r['機能名'])] += float(r['人日'] or 0)
for r in dm:
    k = (r['機能グループ'], r['機能名']); cnt[k] += 1
    s2[k] += float(r['詳細設計 人日'] or 0); s3[k] += float(r['製造 人日'] or 0)
for r in ts:
    k = (r['機能グループ'], r['機能名']); cnt[k] += 1; s4[k] += float(r['人日'] or 0)
G = [r['機能グループ'] for r in gl]; gi = {g: i for i, g in enumerate(G)}
fi = {r['機能名']: i for i, r in enumerate(fl)}
keys = sorted(set(list(b) + list(cnt)), key=lambda k: (gi.get(k[0], 999), k[0], fi.get(k[1], 999), k[1]))
sm2 = [{'機能グループ': k[0], '機能名': k[1], '① 基本設計': f'{b[k]:g}', '② 詳細設計': f'{s2[k]:g}',
        '③ 製造': f'{s3[k]:g}', '④ テスト': f'{s4[k]:g}', '合計': f'{b[k]+s2[k]+s3[k]+s4[k]:g}',
        '②③④ 行数': str(cnt[k])} for k in keys]

# ================= 出力 =================
def out(name, rows, cols):
    with open(os.path.join(W, name), 'w', encoding='utf-8', newline='') as fp:
        w = csv.writer(fp, delimiter='\t', lineterminator='\n'); w.writerow(cols)
        for r in rows: w.writerow([S(r.get(c, '')) for c in cols])
BDC = ['ID', '分類', '作業種別', '機能グループ', '機能名', '項目', '概要', '成果物と完了条件', '人日',
       '担当（案②: 一部移管）', '担当（案③: アプリ構築）', '判断根拠', '根拠の補足', 'スコープ', '当初想定', '依存', '状態', '出典', '機能ID']
out('SHEET_基本設計.tsv', bd, BDC)
out('SHEET_詳細設計_製造.tsv', dm, ['ID', '分類', '機能グループ', '機能名', '項目', '概要・完了定義', '詳細設計 人日', '製造 人日', '内訳'])
out('SHEET_テスト.tsv', ts, ['区分', 'ID', '機能グループ', '機能名', 'テスト項目', 'テスト観点', '人日', '対応要件', '前提'])
out('SHEET_機能名一覧.tsv', fl, ['系統', '機能グループ', '機能名', '機能ID', '概要', '基盤', 'アプリ', '行数', '人日', 'うち対象'])
out('SHEET_機能グループ一覧.tsv', gl, ['機能グループ', '系統', '概要', '行数', '人日'])
out('SHEET_サマリ工程別.tsv', sm2, ['機能グループ', '機能名', '① 基本設計', '② 詳細設計', '③ 製造', '④ テスト', '合計', '②③④ 行数'])
out('SHEET_運用定常.tsv', op, ['区分', 'ID', '作業', '内容', '頻度', '1 回の工数（時間）', '初年度 回数', '初年度 人日', '定常 回数', '定常 人日', '担当'])

tot = lambda rows, c: sum(float(r[c] or 0) for r in rows)
with open(os.path.join(R, 'excel-terms-2026-09-07.md'), 'w', encoding='utf-8') as fp:
    fp.write('# 用語の統一と体裁の修正（2026-09-07）\n\n')
    fp.write('- **やったこと**: 用語 6 組の統一 ＋ 体裁の修正 57 件 ＋ ID の振り直し 114 件を、**一度に全シートへ適用**した\n')
    fp.write('- **反映**: シートごとに `wbs-text/SHEET_*.tsv` で**全面置換**する（部分置換より安全）\n\n')
    fp.write('## 用語の決定と置換\n\n| # | 決定 | 主な置換 |\n|---|---|---|\n')
    fp.write('| 1 | ユーザ | 利用者 → ユーザ |\n')
    fp.write('| 2 | Keycloak-Broker / Keycloak-IdP | 認証製品 → Keycloak-Broker ／ IdP-Keycloak → Keycloak-IdP ／ 製品の版・更新・ベンダーの話は Keycloak |\n')
    fp.write('| 3 | 顧客IdP | 顧客認証システム・顧客の認証システム・接続先 → 顧客IdP |\n')
    fp.write('| 4 | 顧客（組織と使い分け） | テナント → 顧客。組織は「顧客の中の部署」として残す |\n')
    fp.write('| 5 | JWT | 通行証 → JWT ／ トークン発行・交換 → JWT の発行・交換 ／ システム間トークン → システム間 JWT |\n')
    fp.write('| 6 | Keycloak-Broker | ブローカー → Keycloak-Broker |\n\n')
    fp.write('> **残した語**: `アクセストークン` `リフレッシュトークン` `トークンエンドポイント` は OAuth の正式名なのでそのまま。'
             '`SAML` `OIDC` と `旧方式` `新方式` の併用も、正式名と平易な言い換えの使い分けとして残した。\n\n')
    fp.write('## 主な名前の変更（マスタに影響）\n\n| 種別 | 変更前 | 変更後 |\n|---|---|---|\n')
    for kind, before in [('機能グループ', '接続先（顧客 IdP）管理'), ('機能グループ', 'トークン発行・交換'),
                         ('機能グループ', 'ローカルログイン（Keycloak-IdP 収容）'),
                         ('機能名', '接続先の自動振り分け'), ('機能名', '接続先の選択（1 テナントに複数 IdP）'),
                         ('機能名', '顧客認証システムへのログイン委譲（OIDC）'), ('機能名', '顧客認証システムの接続登録'),
                         ('機能名', '利用者の停止（消さずに無効化）'), ('機能名', 'テナント越境の防止（認証製品側）'),
                         ('機能名', '通行証（JWT）に載せる項目の定義'), ('機能名', 'Broker-Keycloak と IdP-Keycloak の連携'),
                         ('機能名', 'Keycloak-IdP 収容ユーザのログイン'), ('機能名', '接続情報の自動追随')]:
        fp.write(f'| {kind} | {before} | **{conv(before)}** |\n')
    fp.write('\n## 検算\n\n| シート | 行数 | 人日 |\n|---|---:|---|\n')
    fp.write(f'| 基本設計 | {len(bd)} | 全量 {tot(bd,"人日"):g} / 対象 {sum(float(r["人日"] or 0) for r in bd if r["スコープ"]=="対象"):g} |\n')
    fp.write(f'| 詳細設計・製造 | {len(dm)} | 詳細設計 {tot(dm,"詳細設計 人日"):g} / 製造 {tot(dm,"製造 人日"):g} |\n')
    fp.write(f'| テスト | {len(ts)} | {tot(ts,"人日"):g} |\n')
    fp.write(f'| 機能名一覧 | {len(fl)} | — |\n| 機能グループ一覧 | {len(gl)} | — |\n')
    fp.write(f'| サマリ(工程別) | {len(sm2)} | 合計 {sum(float(r["合計"]) for r in sm2):g} |\n')
    fp.write(f'| 運用（定常） | {len(op)} | 初年度 {tot(op,"初年度 人日"):.1f} / 定常 {tot(op,"定常 人日"):.1f} |\n')
print('基本設計', len(bd), tot(bd, '人日'), '対象', sum(float(r['人日'] or 0) for r in bd if r['スコープ'] == '対象'))
print('詳細設計', tot(dm, '詳細設計 人日'), '製造', tot(dm, '製造 人日'), 'テスト', tot(ts, '人日'))
print('サマリ', len(sm2), sum(float(r['合計']) for r in sm2))
print('運用', f"{tot(op,'初年度 人日'):.1f}", f"{tot(op,'定常 人日'):.1f}")
print('残存語チェック:')
blob = '\n'.join(S(v) for rows in (bd, dm, ts, fl, gl, sm2, op) for r in rows for v in r.values())
for w_ in ['利用者', '認証製品', 'ブローカー', '接続先', '顧客認証システム', 'テナント', '通行証', 'IdP-Keycloak', 'Broker-Keycloak']:
    c = blob.count(w_)
    print(f'   {w_:16s} {c}')
