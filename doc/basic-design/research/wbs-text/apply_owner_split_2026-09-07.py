#!/usr/bin/env python3
"""要件マッピングの担当を 6 者に分け、複数の担当が実作業を持つ要件は枝番（-a / -b）で行を分ける（P4）。
あわせて P1（DR ③ 行の文言）/ P2（Auth0 は対象）/ P3（90 日は対象で計上）を反映する。

担当の 6 値:
  インフラ（本基盤） / アプリ（Keycloak-IdP） / アプリ（業務アプリ） / アプリ（管理画面・idm-api） / 顧客（顧客IdP） / 他組織（境界・共通基盤）
"""
import csv, os, re, collections

W = os.path.dirname(os.path.abspath(__file__)); P = lambda n: os.path.join(W, n)
def load(n):
    with open(P(n), encoding='utf-8', newline='') as fp:
        rd = csv.reader(fp, delimiter='\t'); h = next(rd)
        return h, [dict(zip(h, r + [''] * (len(h) - len(r)))) for r in rd if any(r)]
def save(n, h, rows):
    with open(P(n), 'w', encoding='utf-8', newline='') as fp:
        w = csv.writer(fp, delimiter='\t', lineterminator='\n'); w.writerow(h)
        for r in rows: w.writerow([r.get(c, '') for c in h])
H, rm = load('SHEET_要件マッピング.tsv'); HD, dm = load('SHEET_詳細設計_製造.tsv')
delta = []
def log(sheet, ID, kind, col, old, new): delta.append((sheet, ID, kind, col, old, new))
def get(ID): return next(r for r in rm if r['要件ID'] == ID)
def setv(ID, col, new):
    r = get(ID)
    if r[col] != new: log('要件マッピング', ID, '変更', col, r[col], new); r[col] = new

INF, IDP, APP, ADM, CUS, EXT = ('インフラ（本基盤）', 'アプリ（Keycloak-IdP）', 'アプリ（業務アプリ）', 'アプリ（管理画面・idm-api）', '顧客（顧客IdP）', '他組織（境界・共通基盤）')

# ---------------------------------------------------------------- P1 / P2 / P3
for ID, item, desc in [('MKA-12', '控えの別地域への複製の設定', '本番の控え（スナップショット）が切替先の地域へ複製され、遅れが監視できる'),
                       ('MKA-13', '再構築手順のコード化（切替と切り戻し）', '作り直しの手順がコードから流れ、戻すこともできる')]:
    r = next(x for x in dm if x['ID'] == ID)
    log('WBS(詳細設計_製造)', ID, '変更', '項目', r['項目'], item); r['項目'] = item
    log('WBS(詳細設計_製造)', ID, '変更', '概要・完了定義', r['概要・完了定義'], desc); r['概要・完了定義'] = desc
setv('FR-FED-001', '担当の理由', 'Auth0 も Phase 1 の対象（2026-09-07 決定）。PoC で使った接続を実機突合（RI-02）に流用する')
setv('FR-USER-013', '担当の理由', '対象で計上（2026-09-07 決定）。顧客IdP 経由で自動作成したユーザだけが対象で、Keycloak-IdP 収容ユーザはアプリ側の判断')

# ---------------------------------------------------------------- P4-1 既存「アプリ」行の振り分け
APP_MAP = {
 IDP: ['FR-AUTH-009', 'FR-AUTH-010', 'FR-AUTH-011', 'FR-AUTH-012', 'FR-AUTH-013', 'FR-AUTH-014', 'FR-MFA-001', 'FR-MFA-002', 'FR-MFA-005',
       'FR-MFA-007', 'FR-MFA-009', 'FR-USER-004', 'FR-USER-010', 'NFR-SEC-009', 'NFR-SEC-010-2', 'NFR-MIG-001', 'NFR-MIG-002'],
 APP: ['FR-AUTHZ-003', 'FR-AUTHZ-009', 'FR-AUTHZ-010'],
 ADM: ['FR-AUTHZ-004', 'FR-USER-005', 'FR-USER-008', 'FR-USER-009', 'FR-USER-012', 'FR-ADMIN-001', 'FR-ADMIN-005', 'FR-ADMIN-006', 'FR-ADMIN-010', 'FR-ADMIN-011'],
}
SPLIT_LATER = ['FR-AUTH-001', 'FR-SSO-003', 'FR-SSO-010', 'FR-AUTHZ-007', 'FR-USER-001', 'FR-INT-007', 'NFR-PERF-003']
app_rows = [r['要件ID'] for r in rm if r['担当'] == 'アプリ']
covered = set(sum(APP_MAP.values(), [])) | set(SPLIT_LATER)
assert set(app_rows) <= covered, set(app_rows) - covered
for owner, ids in APP_MAP.items():
    for ID in ids: setv(ID, '担当', owner)
for r in rm:
    if r['担当'] == 'インフラ': setv(r['要件ID'], '担当', INF)
    elif r['担当'] == '他組織': setv(r['要件ID'], '担当', EXT)
setv('NFR-MIG-001', '担当の理由', '本基盤は受け入れ口（SCIM 受信・管理 API・JIT）を提供するのみ。旧システムからの吸い上げと Keycloak-IdP への投入はアプリ側')
setv('NFR-MIG-002', '担当の理由', 'パスワードのハッシュを持つのは Keycloak-IdP。Keycloak 非対応のハッシュ方式なら Keycloak-IdP 側の拡張（アプリ責務）')

# ---------------------------------------------------------------- P4-2 行の分割
def split(ID, parts):
    """parts = [(枝, 担当, 構築場所, 項目の補足, 担当の理由, ①, ②, ③, ④, 状況)] — 先頭の枝が元の行を引き継ぐ"""
    i = next(i for i, r in enumerate(rm) if r['要件ID'] == ID); base = rm.pop(i)
    log('要件マッピング', ID, '分割', '要件ID', ID, ' / '.join(f'{ID}-{p[0]}' for p in parts))
    for k, (suf, owner, place, item_note, why, a, b, c, d, st) in enumerate(parts):
        r = dict(base); r['要件ID'] = f'{ID}-{suf}'; r['担当'] = owner; r['構築場所'] = place
        r['項目'] = f"{base['項目']}（{item_note}）"; r['担当の理由'] = why
        r['① 基本設計'], r['② 詳細設計'], r['③ 製造'], r['④ テスト'], r['状況'] = a, b, c, d, st
        rm.insert(i + k, r)
FULL, APPONLY, CUSONLY, EXTONLY = '全工程あり', 'アプリ側で実施', '顧客側で実施', '他組織で実施'
split('FR-AUTH-001', [
 ('a', INF, 'Keycloak-Broker', '本基盤運用者', 'Keycloak-Broker にローカルで残るのは運用者だけ。認証は WebAuthn 必須（NFR-SEC-021）', 'HB-F-AUTH-01 HG-09', 'DDB-19', 'MKB-31', 'SEC-10', FULL),
 ('b', IDP, 'Keycloak-IdP', '顧客IdP を持たない顧客のユーザ', 'Keycloak-IdP に収容するユーザの話。本基盤は ROSA の引き渡しまで（NFR-OPS-012）', '', '', '', '', 'アプリ側で実施（Keycloak-IdP 側。本基盤は ROSA の引き渡しまで＝NFR-OPS-012）')])
split('FR-FED-012', [
 ('a', INF, 'Keycloak-Broker', '取り込み側', '追加認証済みの印（amr）を取り込み、二重に求めない設定は Keycloak-Broker 側', 'HB-F-AUTH-05 HB-F-AUTH-09 HE-14 HE-23', 'DDB-01 DDB-18', 'MKB-02 MKB-30', 'RI-01 ST-04 ST-28', FULL),
 ('b', CUS, 'その他', '実施側', '追加認証そのものは顧客IdP（Keycloak-IdP 収容ユーザは Keycloak-IdP）が行い、結果を amr で返す。接続ガイドで求める', '', '', '', 'RI-01', CUSONLY)])
for ID, note_app, guide in [('FR-SSO-003', 'アプリの実装', 'GD-22'), ('FR-AUTHZ-007', 'アプリの実装', 'GD-16 GD-18'),
                            ('FR-INT-007', 'アプリの実装', 'GD-16 GD-18'), ('NFR-PERF-003', 'アプリの実装', 'GD-16 GD-18')]:
    split(ID, [
     ('a', APP, 'その他', note_app, '業務アプリ側の実装。本基盤はガイドとサンプルで示す', '', '', '', '', APPONLY),
     ('b', INF, 'Keycloak-Broker', 'ガイド・サンプル', 'アプリ開発者向けガイドとサンプル実装・試用環境を本基盤が提供する', guide, 'DDJ-05', 'MKJ-05', 'UAT-04', FULL)])
for ID, note in [('FR-SSO-010', '管理画面からの操作'), ('FR-USER-001', '管理画面と API')]:
    split(ID, [
     ('a', ADM, 'その他', note, '管理画面・idm-api 側の実装。Keycloak-Broker の管理 API を内部経路で呼ぶ', '', '', '', '', APPONLY),
     ('b', INF, 'Keycloak-Broker', '本基盤側の受け口', '管理 API の内部公開（F-INT-14）: 経路・呼び出し元の資格・許す操作の範囲', 'HE-24', 'DDE-12', 'MKB-32', 'IT-17', FULL)])
r = get('FR-AUTHZ-001')
split('FR-AUTHZ-001', [
 ('a', INF, 'Keycloak-Broker', 'JWT に載せる側', 'JWT に載せる項目と要求できる範囲は本基盤が定義し発行する', r['① 基本設計'], r['② 詳細設計'], r['③ 製造'], r['④ テスト'], FULL),
 ('b', APP, 'その他', '判定する側', '載った情報で可否を判断するのは業務アプリ（認可・権限判定は本基盤ではやらない）', '', '', '', '', APPONLY)])
r = get('FR-AUTHZ-002')
split('FR-AUTHZ-002', [
 ('a', INF, 'Keycloak-Broker', '認証側の越境防止と tenant_id', '他顧客の顧客IdP で入れないことと、顧客を指す値を JWT に載せることは Keycloak-Broker 側（F-AZ-05）', r['① 基本設計'], r['② 詳細設計'], r['③ 製造'], r['④ テスト'], FULL),
 ('b', ADM, 'その他', '権限データ側の越境防止', '権限データや業務データで他顧客に触れさせないのは管理画面・idm-api と業務アプリの責務', '', '', '', '', APPONLY)])
r = get('FR-USER-006')
split('FR-USER-006', [
 ('a', INF, 'Keycloak-Broker', 'Keycloak-Broker 側', r['担当の理由'], r['① 基本設計'], r['② 詳細設計'], r['③ 製造'], r['④ テスト'], FULL),
 ('b', ADM, 'その他', '操作画面', '管理者が止める・戻す操作は管理画面から、管理 API の内部公開（F-INT-14）経由で行う', '', '', '', 'IT-17', APPONLY)])
for ID in ['FR-USER-011', 'NFR-COMP-009']:
    r = get(ID)
    split(ID, [
     ('a', INF, 'Keycloak-Broker', '本基盤の窓口と Keycloak-Broker 側', r['担当の理由'], r['① 基本設計'], r['② 詳細設計'], r['③ 製造'], r['④ テスト'], FULL),
     ('b', ADM, 'その他', '権限データ側', '権限データ・参照用データの消去は管理画面・idm-api 側。本基盤の手順（HK-07）から依頼する', '', '', '', 'OP-04', APPONLY)])
r = get('FR-FED-011')
split('FR-FED-011', [
 ('a', INF, 'Keycloak-Broker', '本基盤側の登録', r['担当の理由'] if r['担当の理由'] != '—' else '登録の手順と疎通確認は本基盤', r['① 基本設計'], r['② 詳細設計'], r['③ 製造'], r['④ テスト'], FULL),
 ('b', CUS, 'その他', '顧客側の設定', '自社 IdP 側の設定（接続先の登録・返す項目・証明書）は顧客が接続ガイドどおりに行う', '', '', '', 'UAT-02', CUSONLY)])
r = get('FR-USER-003')
split('FR-USER-003', [
 ('a', INF, 'Keycloak-Broker', '受信側', r['担当の理由'] if r['担当の理由'] != '—' else '受信窓口は Keycloak-Broker の上に立てる', r['① 基本設計'], r['② 詳細設計'], r['③ 製造'], r['④ テスト'], FULL),
 ('b', CUS, 'その他', '送信側', '顧客の人事システム・IdP 側の SCIM 送信設定と再送の作法は顧客が行う', '', '', '', 'RI-04', CUSONLY)])
for ID in ['NFR-SEC-011', 'NFR-SEC-012']:
    r = get(ID)
    split(ID, [
     ('a', EXT, 'その他', '境界側の実装', '境界を管理する他組織が WAF・DDoS 対策を持つ', '', '', 'MKA-04', 'SEC-05', EXTONLY),
     ('b', INF, 'Keycloak-Broker', '要求仕様と受入確認', '何を求めるかは本基盤の責務。要求仕様書（HK-10）を出し、受入確認を行う', 'HG-08 HK-10', '', '', 'IT-11 SEC-05' if ID == 'NFR-SEC-011' else 'SEC-05', '🔺 一部の工程のみ')])
for ID in ['NFR-SCL-004', 'NFR-OPS-011']:
    r = get(ID)
    split(ID, [
     ('a', INF, 'Keycloak-Broker', '本基盤側の作業', '登録から疎通確認までの所要時間は本基盤', r['① 基本設計'], r['② 詳細設計'], r['③ 製造'], r['④ テスト'], r['状況']),
     ('b', EXT, 'その他', '境界側の外向き許可', '顧客IdP 向けの外向き許可の追加は他組織（依頼から当日〜翌日）。約束する時間にこの分を含める', '', '', '', '', EXTONLY)])
for ID, note in [('FR-ADMIN-007', '閲覧'), ('NFR-OPS-003', '保管'), ('NFR-OPS-004', '検索'), ('NFR-COMP-007', '保管')]:
    r = get(ID)
    split(ID, [
     ('a', INF, 'Keycloak-Broker', '出力・項目・保持年数の指定', '何を記録し何年保つかは本基盤が決めて出力する', r['① 基本設計'], r['② 詳細設計'], r['③ 製造'], r['④ テスト'], FULL),
     ('b', EXT, 'その他', f'共通基盤側の{note}', f'記録の{note}は全体の共通基盤側。本基盤は指定した保持年数と形式で出すまで（OP-03 で確認）', '', '', '', 'OP-03', EXTONLY)])

# ---------------------------------------------------------------- 書き戻し
save('SHEET_要件マッピング.tsv', H, rm); save('SHEET_詳細設計_製造.tsv', HD, dm)
with open(P('SYNC_owner_split_2026-09-07.tsv'), 'w', encoding='utf-8', newline='') as fp:
    w = csv.writer(fp, delimiter='\t', lineterminator='\n'); w.writerow(['シート', 'ID', '種別', '列', '旧', '新'])
    for d in delta: w.writerow(d)

# ---------------------------------------------------------------- 検算
H2, bd = load('SHEET_基本設計.tsv'); H3, ts = load('SHEET_テスト.tsv')
ids = {r['ID'] for r in bd} | {r['ID'] for r in dm} | {r['ID'] for r in ts}
bad = [(r['要件ID'], x) for r in rm for c in ['① 基本設計', '② 詳細設計', '③ 製造', '④ テスト'] for x in r[c].split() if x not in ids]
print(f'要件マッピング: {len(rm)} 行 / {len(H)} 列 / 参照切れ: {bad or "なし"}')
print('担当:', dict(collections.Counter(r['担当'] for r in rm)))
print('状況:', dict(collections.Counter(r['状況'] for r in rm)))
print('分割した要件:', [d[1] for d in delta if d[2] == '分割'])
dup = [k for k, v in collections.Counter(r['要件ID'] for r in rm).items() if v > 1]
print('要件ID 重複:', dup or 'なし')
print(f'差分 {len(delta)} 件 → SYNC_owner_split_2026-09-07.tsv')
