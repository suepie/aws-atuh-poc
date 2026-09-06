#!/usr/bin/env python3
"""機能グループ > 機能名 > WBS タスク の上 2 階層に概要を付ける。

- 機能名 91 件の概要は function-table-2026-08-31.md（HB-F 行の概要と同一）から取る
- 機能グループ 31 件と横断系の概要は本スクリプト内で定義する
- 「／」で複数機能にまたがる値は、各要素の一言概要を連結して自動生成する
- ついでに TSV の機能グループ表記の揺れ 4 種を直す（SYNC_groupfix.tsv に出す）
出力: SYNC_group.tsv / SYNC_func.tsv / SYNC_groupfix.tsv / ../function-hierarchy-2026-09-06.md
"""
import csv, os, re, collections

W = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(W, '..')
BODY = ['AG_概要_成果物.tsv', 'H-other_概要_成果物.tsv', 'HB-F_概要_成果物.tsv', 'HB-other_廃止行_概要_成果物.tsv', 'HL-GD_概要_成果物.tsv']

# ---------- 91 機能の概要（function-table から） ----------
FUNC = collections.OrderedDict()   # 機能名 -> (系統, グループ, 概要)
for l in open(os.path.join(R, 'function-table-2026-08-31.md'), encoding='utf-8'):
    if l.startswith('| ') and l.count('|') == 5 and not l.startswith('| 系統') and not l.startswith('| F-'):
        c = [x.strip() for x in l.strip().strip('|').split('|')]
        if c[0] in ('認証', 'プロビジョニング', '管理', '認可', '連携', 'バッチ'):
            FUNC[c[2]] = (c[0], c[1], c[3])
assert len(FUNC) == 91, len(FUNC)
FID = {}
for l in open(os.path.join(R, 'function-table-2026-08-31.md'), encoding='utf-8'):
    if l.startswith('| F-'):
        c = [x.strip() for x in l.strip().strip('|').split('|')]
        FID[c[2]] = c[0]

# 今回の整理で変わった機能の概要を上書き
FUNC['利用者の停止（消さずに無効化）'] = ('プロビジョニング', '退職者の遮断と復職対応（停止・再開の伝播）', '利用者を削除せず使えない状態にし、停止日時を記録する機能。90 日休眠・SCIM の削除通知・管理者操作のいずれもここに集まる')
FUNC['初回ログイン時の自動登録'] = ('プロビジョニング', '自動登録', '顧客の認証システム経由で初めてログインした人を、その場で利用者として登録する機能（JIT）。初回ログイン時の利用者控え作成と同じ出来事')
FUNC['接続先の自動振り分け'] = ('認証', '接続先の振り分け', 'ログイン画面で入力された ID から、その人がどの接続先（顧客の認証システム）の利用者かを判定し、自動で振り分ける（HRD）。判定できないときのパスワード入力への切替を含む')
FUNC['重要操作時の追加認証'] = ('認証', '多要素認証', '重要な操作をするときだけ、その場で追加の認証を求める仕組み。ステップアップ認証は不要と決定したため対象外')
FUNC['顧客システムからの利用者登録'] = ('プロビジョニング', '顧客システムからの利用者受信（人事システム等からの登録・更新・削除）', '顧客の人事システムや IdP から SCIM で利用者の新規登録を受け取る機能。受信窓口は自作またはプラグイン')
FUNC['顧客システムからの利用者更新'] = ('プロビジョニング', '顧客システムからの利用者受信（人事システム等からの登録・更新・削除）', 'SCIM で顧客側からの利用者情報の変更を受け取って反映する機能')
FUNC['顧客システムからの削除通知'] = ('プロビジョニング', '顧客システムからの利用者受信（人事システム等からの登録・更新・削除）', 'SCIM で顧客側からの削除通知を受け取り、基盤側では消さずに使えない状態にする機能')
FUNC['顧客システムからの利用者検索'] = ('プロビジョニング', '顧客システムからの利用者受信（人事システム等からの登録・更新・削除）', 'SCIM で顧客側から利用者を検索・絞り込みで問い合わせられるようにする機能')
FUNC['顧客システムからのグループ連携'] = ('プロビジョニング', '顧客システムからの利用者受信（人事システム等からの登録・更新・削除）', 'SCIM で顧客側のグループ情報を受け取る機能。初期リリースでは対象外')
FUNC['項目名の変換・統一'] = ('プロビジョニング', '受け取ったデータの整形（項目名・区分の統一）', '顧客ごとにバラバラな項目名を、基盤内の統一名に変換して取り込む仕組み。統一名の辞書と IdP ごとの変換表を含む。アプリへ渡す JWT の項目定義とは別')
FUNC['登録経路の区分判定'] = ('プロビジョニング', '受け取ったデータの整形（項目名・区分の統一）', 'その利用者がどの経路（JIT / SCIM / 管理画面 / アプリ API / 運用者 / 移行）で登録されたかを区別し、後の自動処理の対象を判断できるようにする仕組み')
FUNC['内部2段構えの認証連携'] = ('認証', 'フェデレーション', '基盤内部で 2 段構えになっていた認証システム同士の連携。Realm 統合により対象外')
FUNC['停止の確実な伝播'] = ('プロビジョニング', '退職者の遮断と復職対応（停止・再開の伝播）', '片方のシステムで利用者を止めたとき、その事実をもう一方にも必ず伝えて確実に遮断する仕組み。Realm 統合により対象外')
FUNC['再開の確実な伝播'] = ('プロビジョニング', '退職者の遮断と復職対応（停止・再開の伝播）', '再び使えるようにした場合も、止めたときと同じ経路でもう一方に伝える仕組み。Realm 統合により対象外')

# ---------- 機能グループ 31 + 横断の概要 ----------
GROUP = collections.OrderedDict([
    ('ローカル認証', ('認証', '顧客側に認証システムが無いテナントの利用者と基盤の運用者が、本基盤に直接 ID とパスワードでログインするための機能群')),
    ('接続先の振り分け', ('認証', 'ログイン画面で入力された ID から、その人をどの顧客認証システムへ送るかを決める入口の機能群（HRD）。接続先の一覧を見せずに済ませる')),
    ('フェデレーション', ('認証', '顧客の認証システム（OIDC / SAML）に認証を委ね、その結果を受けてログインさせる中核の機能群。初回登録と属性の取り込みを含む')),
    ('多要素認証', ('認証', 'パスワードに加えて 2 つ目の要素（数字コード・生体・セキュリティキー）を求める機能群。登録と利用の両方を含む')),
    ('アカウント復旧・パスワード', ('認証', '端末の紛失やパスワード忘れから、利用者自身が復旧するための機能群')),
    ('不正アクセス対策', ('認証', '総当たり・利用者名の推測・流出パスワードなど、ログイン口への攻撃を防ぐ機能群')),
    ('自動登録', ('プロビジョニング', '顧客認証システム経由で初めてログインした人をその場で利用者として登録し、以後のログインで属性を更新する機能群（JIT）')),
    ('顧客システムからの利用者受信（人事システム等からの登録・更新・削除）', ('プロビジョニング', '顧客の人事システムや IdP から SCIM で利用者の登録・更新・削除を受け取る機能群。ログインを待たずに反映できる')),
    ('受け取ったデータの整形（項目名・区分の統一）', ('プロビジョニング', '顧客ごとにバラバラな項目名や登録経路を、基盤内の統一した形に揃える機能群。入口での前処理')),
    ('退職者の遮断と復職対応（停止・再開の伝播）', ('プロビジョニング', '退職などで利用者を止めた事実を確実に反映し、復職時に安全に再開するための機能群。消さずに無効化する')),
    ('権限管理側への引き渡し（識別子の紐付け・参照用データの更新）', ('プロビジョニング', '整えた利用者情報と識別子を権限管理側へ渡し、アプリが参照できる状態にする機能群。下流への受け渡し')),
    ('利用者管理', ('管理', '管理者が利用者を検索・登録・変更・停止・削除する基本操作の機能群')),
    ('利用者支援操作', ('管理', '管理者が利用者を助けるための操作の機能群（パスワード初期化・追加認証の解除・招待・強制ログアウト）')),
    ('権限管理', ('管理', 'どの利用者がどのアプリをどの役割で使えるかを設定し、定期的に見直す機能群')),
    ('組織・顧客管理', ('管理', '顧客（テナント）と組織の作成・設定を行う機能群')),
    ('接続先管理', ('管理', '顧客の認証システムを本基盤に接続し、設定と証明書を維持する機能群')),
    ('監査・一括処理', ('管理', '操作記録の照会、利用者の一括登録、ファイル出力、システム用アカウントの台帳など、管理業務を支える機能群')),
    ('権限情報の提供', ('認可', 'アプリが「この利用者は何ができるか」を問い合わせるための API の機能群')),
    ('権限判定', ('認可', 'ログイン時にアプリの利用可否と役割を判定する処理群')),
    ('アクセス制御', ('認可', 'テナント越境と管理操作の権限逸脱を防ぐ仕組み')),
    ('トークン管理', ('認可', 'システム同士が API を呼ぶための資格の発行と交換')),
    ('認可の記録', ('認可', '権限判定の結果を記録する機能')),
    ('業務システム連携（ServiceNow 等へのログイン提供）', ('連携', 'ServiceNow などの業務システムへ本基盤がログインを提供し、業務システム側に利用者を自動作成させる連携')),
    ('アプリへの通知', ('連携', '利用者の変更をアプリへ通知する仕組みと、利用者へのメール送信')),
    ('アカウント間連携', ('連携', '停止イベントや識別子を AWS アカウントをまたいで届ける経路。Realm 統合により対象外')),
    ('監視・検知', ('連携', '不正兆候の検知、擬似ログインによる障害検知、アプリ設置状況の確認')),
    ('接続情報の追随', ('連携', '顧客 IdP の証明書入れ替えに自動で追随する機能')),
    ('利用者の整理', ('バッチ', '長期未使用者の自動停止と、保存期限切れデータの消去')),
    ('データの突合と再送（伝えそこないの回収）', ('バッチ', 'システム間の伝えそこないを定期的に突き合わせて回収する処理')),
    ('鍵・証明書の維持', ('バッチ', '署名鍵・接続用パスワード・証明書を期限前に入れ替える定期処理')),
    ('アカウント・権限の点検', ('バッチ', '管理者不在アカウントの検出と、権限棚卸しの定期起動')),
    ('横断', ('横断', '特定の機能に属さず、全機能または複数機能に共通する設計・規約・構成・運用の作業。機能名の括弧内で対象範囲を示す')),
])
assert len(GROUP) == 32

# ---------- 横断系の機能名の概要 ----------
CROSS = collections.OrderedDict([
    ('横断（全機能共通）', '総則・規約・構成図・レビュー・顧客向け資料など、全機能に共通する作業'),
    ('横断（自社拡張全般）', '認証製品に組み込む自社拡張（SPI）全体に関わる作業（配置・ビルド・版数管理・互換確認）'),
    ('横断（ログイン画面のブランド別表示 ※機能一覧に未登録）', 'ブランドごとにログイン画面を切り替える構成。1 ブランドのみの前提で対象外'),
    ('横断（ログイン画面）', 'ログイン画面全般の設計（規約・文言・攻撃対策の画面側対応）'),
    ('横断（緊急時の運用）', '通常経路が使えないときの管理者アクセス（踏み台）'),
    ('横断（管理 API）', '管理 API 全体に共通する作業（応答目標など）'),
    ('該当なし', '機能に紐づかない作業（構成の判断・契約・体制・他組織との調整など）'),
    ('横断（ログイン処理全般）', 'ログイン処理の順序や本番設定など、ログイン系の全機能に関わる作業'),
    ('横断（顧客の解約運用）', '顧客がサービスから離脱するときの手順'),
    ('横断（法令対応）', '法令・契約に基づく対応（本人からの開示・削除請求など）'),
    ('横断（災害対策）', '別地域への切替に関する作業。災害対策は対象外'),
    ('横断（同意管理）', '利用規約などへの同意を取り、記録する仕組み'),
    ('横断（定期処理共通）', 'バッチ全体の実行基盤・スケジュール・多重起動制御'),
    ('横断（代表シナリオ）', '業務フロー図。各機能仕様書に吸収して対象外'),
    ('該当なし（章ごとに分割済み）', '旧集計行'),
    ('該当なし（対象外）', '対象外の行'),
    ('定期実行処理全般', 'バッチ一覧・実行基盤・スケジュール・多重起動など、バッチ全体に関わる作業'),
    ('管理画面の機能全般', '管理画面の全機能に共通する作業（画面一覧・遷移図）'),
    ('顧客システムからの利用者情報受け取り', 'SCIM 受信の仕様全体（窓口・項目対応・絞り込み・削除の読み替え）'),
    ('鍵・証明書・権限見直しの定期処理', '鍵・証明書のローテーションと権限棚卸しの定期処理の仕様'),
])

# ---------- TSV の機能グループ表記の揺れを直す ----------
GROUPFIX = {  # (機能グループ, 機能名) -> (新グループ, 新機能名)
    ('横断（全機能共通）', '横断（全機能共通）'): ('横断', '横断（全機能共通）'),
    ('横断（同意管理）', '横断（同意管理）'): ('横断', '横断（同意管理）'),
    ('横断', '横断（自社拡張全般)'): ('横断', '横断（自社拡張全般）'),
}
def fix(g, n):
    if (g, n) in GROUPFIX:
        return GROUPFIX[(g, n)]
    if g == '—':
        return ('横断', n)
    return (g, n)

rows = collections.OrderedDict(); file_of = {}; hdr = None
for f in BODY:
    rd = list(csv.reader(open(os.path.join(W, f), encoding='utf-8'), delimiter='\t'))
    hdr = rd[0]
    for r in rd[1:]:
        if r and r[0]:
            d = dict(zip(hdr, r)); rows[d['WBS ID']] = d; file_of[d['WBS ID']] = f
import json
_xl = {r[1]['A']: (r[1]['I'], r[1]['J']) for r in json.load(open('/tmp/xl.json'))}
fixes = []  # Excel の現状（/tmp/xl.json）と比べて I/J が変わる行
for i, d in rows.items():
    g, n = fix(d['機能グループ'], d['機能名'])
    d['機能グループ'] = g; d['機能名'] = n
    if i in _xl and _xl[i] != (g, n):
        fixes.append((i, _xl[i][0], _xl[i][1], g, n))
by_file = collections.defaultdict(list)
for i, d in rows.items():
    by_file[file_of[i]].append(d)
for f in BODY:
    with open(os.path.join(W, f), 'w', encoding='utf-8', newline='') as fp:
        w = csv.writer(fp, delimiter='\t', lineterminator='\n'); w.writerow(hdr)
        for d in by_file[f]:
            w.writerow([d.get(c, '') for c in hdr])
with open(os.path.join(W, 'SYNC_groupfix.tsv'), 'w', encoding='utf-8') as fp:
    fp.write('WBS ID\t機能グループ（新）\t機能名（新）\n')
    for i, og, on, g, n in fixes:
        fp.write(f'{i}\t{g}\t{n}\n')

# ---------- 一言概要（先頭 1 文） ----------
def brief(t):
    return t.split('。')[0]
NAME_DESC = collections.OrderedDict()  # 機能名 -> (系統, グループ, 機能ID, 概要)
for n, (s, g, t) in FUNC.items():
    NAME_DESC[n] = (s, g, FID.get(n, ''), t)
for n, t in CROSS.items():
    NAME_DESC[n] = ('横断', '横断', '横断', t)

def name_entry(n):
    if n in NAME_DESC:
        return NAME_DESC[n]
    parts = [p.strip() for p in n.split('／')]
    if all(p in NAME_DESC for p in parts):
        ss = sorted(set(NAME_DESC[p][0] for p in parts), key=list(['認証', 'プロビジョニング', '管理', '認可', '連携', 'バッチ', '横断']).index)
        gs = []
        for p in parts:
            if NAME_DESC[p][1] not in gs: gs.append(NAME_DESC[p][1])
        ids = '／'.join(NAME_DESC[p][2] for p in parts)
        desc = '複数機能にまたがる行。' + '／'.join(brief(NAME_DESC[p][3]) for p in parts)
        return ('／'.join(ss), '／'.join(gs), ids, desc)
    raise KeyError(n)

ALIAS = {'停止と再開': '退職者の遮断と復職対応（停止・再開の伝播）', '識別子と権限の連携': '権限管理側への引き渡し（識別子の紐付け・参照用データの更新）'}
def group_entry(g):
    if g in GROUP:
        return GROUP[g]
    parts = [ALIAS.get(p.strip(), p.strip()) for p in g.split('／')]
    ss = []
    for p in parts:
        if GROUP[p][0] not in ss: ss.append(GROUP[p][0])
    return ('／'.join(ss), '複数グループにまたがる行。' + '／'.join(brief(GROUP[p][1]) for p in parts))

# 使用中の値を集める
used_groups = collections.OrderedDict(); used_names = collections.OrderedDict()
eff = {r[0]: float(r[1]) for r in list(csv.reader(open(os.path.join(W, 'SYNC_effort.tsv'), encoding='utf-8'), delimiter='\t'))[1:]}
for i, d in rows.items():
    used_groups.setdefault(d['機能グループ'], []).append(i)
    used_names.setdefault(d['機能名'], []).append(i)

with open(os.path.join(W, 'SYNC_group.tsv'), 'w', encoding='utf-8') as fp:
    fp.write('機能グループ\t系統\t概要\t行数\t人日\n')
    for g in list(GROUP) + [g for g in used_groups if g not in GROUP]:
        s, t = group_entry(g); ids = used_groups.get(g, [])
        fp.write(f'{g}\t{s}\t{t}\t{len(ids)}\t{sum(eff[i] for i in ids):g}\n')
with open(os.path.join(W, 'SYNC_func.tsv'), 'w', encoding='utf-8') as fp:
    fp.write('機能名\t機能ID\t系統\t機能グループ\t概要\t行数\t人日\n')
    for n in list(NAME_DESC) + [n for n in used_names if n not in NAME_DESC]:
        s, g, fid, t = name_entry(n); ids = used_names.get(n, [])
        fp.write(f'{n}\t{fid}\t{s}\t{g}\t{t}\t{len(ids)}\t{sum(eff[i] for i in ids):g}\n')

# ---------- md ----------
with open(os.path.join(R, 'function-hierarchy-2026-09-06.md'), 'w', encoding='utf-8') as fp:
    fp.write('# 機能グループ > 機能名 の概要（WBS 基本設計の上 2 階層）\n\n')
    fp.write('- **日付**: 2026-09-06\n- **目的**: WBS(基本設計) は「機能グループ > 機能名 > WBS タスク」の 3 階層だが、上 2 階層に概要が無かったので付ける。ピボットでの検算の前提\n')
    fp.write('- **生成**: `wbs-text/build_function_hierarchy_2026-09-06.py`。機能名 91 件の概要は [function-table-2026-08-31.md](function-table-2026-08-31.md) と同一（今回の整理で変わった 14 件は上書き）。「／」で複数機能にまたがる値は各要素の一言概要を連結して自動生成\n')
    fp.write('- **Excel 反映**: `SYNC_group.tsv`（機能グループ一覧）/ `SYNC_func.tsv`（機能名一覧）を参照シートとして追加し、`SYNC_groupfix.tsv` で表記の揺れ %d 行を直す\n\n' % len(fixes))
    fp.write('## 1. 機能グループ（31 ＋ 横断）\n\n| 系統 | 機能グループ | 概要 | 行数 | 人日 |\n|---|---|---|---:|---:|\n')
    for g, (s, t) in GROUP.items():
        ids = used_groups.get(g, [])
        fp.write(f'| {s} | {g} | {t} | {len(ids)} | {sum(eff[i] for i in ids):g} |\n')
    comp = [g for g in used_groups if g not in GROUP]
    fp.write(f'\n複数グループにまたがる値（{len(comp)} 種・自動生成）は SYNC_group.tsv を参照。\n\n')
    fp.write('## 2. 機能名（91 ＋ 横断 %d）\n\n| 系統 | 機能グループ | 機能名 | 機能ID | 概要 | 行数 | 人日 |\n|---|---|---|---|---|---:|---:|\n' % len(CROSS))
    for n, (s, g, fid, t) in NAME_DESC.items():
        ids = used_names.get(n, [])
        fp.write(f'| {s} | {g} | {n} | {fid} | {t} | {len(ids)} | {sum(eff[i] for i in ids):g} |\n')
    compn = [n for n in used_names if n not in NAME_DESC]
    fp.write(f'\n複数機能にまたがる値（{len(compn)} 種・自動生成）は SYNC_func.tsv を参照。\n\n')
    fp.write('## 3. 表記の揺れの修正（%d 行）\n\n| WBS ID | 旧グループ | 旧機能名 | 新グループ | 新機能名 |\n|---|---|---|---|---|\n' % len(fixes))
    for i, og, on, g, n in fixes:
        fp.write(f'| {i} | {og} | {on} | {g} | {n} |\n')
print('groups used', len(used_groups), 'names used', len(used_names), 'fixes', len(fixes))
unused = [n for n in NAME_DESC if n not in used_names]
print('names defined but unused:', unused)
