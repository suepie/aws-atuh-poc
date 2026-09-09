#!/usr/bin/env python3
"""縮小版（2026-09-09）のフィルタ列を各シートに足す。

前提（ユーザー指示 8 条件）:
  R1 環境は 3 面
  R2 Keycloak-Broker は我々が作る
  R3 提供する API は標準のみ（カスタムは作らない）
  R4 セキュリティの考慮はネットワークのみ（シャドウユーザーはそのまま＝伝播は作らない）
  R5 DR はバックアップを取るのみ（リストア・切替は後回し）
  R6 DB チューニングなど性能は考慮しない
  R7 Keycloak-Broker と Keycloak-IdP を作るのみ
  R8 HRD は我々が作る（← R3 の唯一の例外）

追加する列（元の人日は 1 つも書き換えない）:
  「縮小版」      = 対象 / 一部 / 対象外
  「縮小版 人日」  = 対象はそのまま、一部は比率をかけた値、対象外は 0
"""
import csv, os, collections, sys

W = os.path.dirname(os.path.abspath(__file__)); P = lambda n: os.path.join(W, n)
def load(n):
    with open(P(n), encoding='utf-8', newline='') as fp:
        rd = csv.reader(fp, delimiter='\t'); h = next(rd)
        return h, [dict(zip(h, r + [''] * (len(h) - len(r)))) for r in rd if any(r)]
def save(n, h, rows):
    with open(P(n), 'w', encoding='utf-8', newline='') as fp:
        w = csv.writer(fp, delimiter='\t', lineterminator='\n'); w.writerow(h)
        for r in rows: w.writerow([r.get(c, '') for c in h])
num = lambda x: float(x) if str(x).strip() else 0.0
def fmt(x):
    x = round(x * 4) / 4                      # 0.25 刻みに丸める
    return '' if x == 0 else (str(int(x)) if float(x).is_integer() else str(x))

IN, PART, OUT = '対象', '一部', '対象外'
# 機能名 → (区分, 縮小版に残す比率, 理由)
RULES = {
 # ---------------- R8 HRD は我々（R3 の例外）
 '顧客IdPの自動振り分け': (IN, 1.0, 'R8 HRD は我々が作る'),
 '振り分け失敗時のパスワード入力への切替': (IN, 1.0, 'R8 HRD の一部'),
 '顧客IdPの選択（1 顧客に複数）': (IN, 1.0, 'R8 HRD の一部'),
 'ユーザの存在推測の防止': (PART, 0.5, 'R8 HRD の応答を揃えるところまで。試行回数の制限は後回し'),
 # ---------------- R2 / R7 Keycloak を作る
 '顧客IdPへのログイン委譲（OIDC）': (IN, 1.0, 'R2 Keycloak-Broker の中核'),
 '顧客IdPへのログイン委譲（SAML）': (IN, 1.0, 'R2 Keycloak-Broker の中核'),
 '初回ログイン時のユーザ自動作成（JIT）': (IN, 1.0, 'R2 フェデが動く前提'),
 'ログイン時の属性更新': (IN, 1.0, 'R2 フェデが動く前提'),
 'Keycloak-Broker と Keycloak-IdP の連携': (IN, 1.0, 'R7 2 台をつなぐところ'),
 'Keycloak-IdP 収容ユーザのログイン': (IN, 1.0, 'R7'),
 'Keycloak-IdP 側の引き渡しと責任分界': (IN, 1.0, 'R7 IdP 側も作って渡す'),
 'ログイン状態の保持とタイムアウト': (IN, 1.0, 'R2 ログインが成立する前提'),
 'アプリへのログアウト連携': (IN, 1.0, 'R2 ログインが成立する前提'),
 'ログイン画面の表示（ブランド・並び順）': (IN, 1.0, 'R2 利用者が触る面'),
 'エラー・案内画面（Keycloak-Broker）': (IN, 1.0, 'R2 利用者が触る面'),
 '顧客IdP から受け取る属性の名前の統一': (IN, 1.0, 'R2 フェデが動く前提'),
 'Realm・ブランド区画構成': (IN, 1.0, 'R2 Keycloak の土台'),
 '顧客の作成': (IN, 1.0, 'R2 顧客を載せる最小操作'),
 '顧客IdPの接続登録': (IN, 1.0, 'R2 顧客を載せる最小操作'),
 '接続設定の変更・証明書更新': (IN, 1.0, 'R2 証明書が切れると止まるため外せない'),
 'アプリへの JWT 発行': (IN, 1.0, 'R3 標準 API の中核'),
 'システム間 JWT の発行': (IN, 1.0, 'R3 標準 API'),
 'アプリの接続登録（クライアント登録）': (IN, 1.0, 'R3 アプリを繋ぐ最小操作'),
 '顧客越境の防止（Keycloak-Broker 側）': (IN, 1.0, 'R2 Keycloak 側の設定で成立。外すと事故が起きる'),
 # ---------------- インフラ
 'ネットワーク構成': (IN, 1.0, 'R4 セキュリティの考慮はネットワークのみ'),
 'クラスタ構成': (IN, 1.0, 'R7 Keycloak を載せる土台'),
 '環境構成（本番 / stg / dev）': (IN, 1.0, 'R1 3 面'),
 '全体構成（論理・物理）': (IN, 1.0, '構成図がないと作れない'),
 '他組織との構成調整': (IN, 1.0, 'R4 ネットワーク境界の相手あり作業'),
 '命名・構成管理規約': (IN, 1.0, '構成をコードで持つ前提'),
 '設計書の総則・前提・用語': (IN, 1.0, '設計の入口'),
 'データベース設計（Keycloak-Broker）': (PART, 0.4, 'R6 構築だけ。索引・分割・チューニングは後回し'),
 # ---------------- 一部だけ残す
 'バックアップ・復元': (PART, 0.4, 'R5 取得の仕組みだけ。復元手順と訓練は後回し'),
 '攻撃経路と対策': (PART, 0.4, 'R4 ネットワークの遮断・流量制限のみ。疑似攻撃検査は後回し'),
 '鍵・暗号化の管理方式': (PART, 0.5, 'R4 通信の暗号化と Keycloak 標準の鍵まで。鍵の階層設計は後回し'),
 'JWT 署名鍵の定期入れ替え': (PART, 0.5, 'Keycloak 標準の入れ替えまで。自動化と並走管理は後回し'),
 '監視項目・閾値・通知': (PART, 0.5, '死活と主要な値だけ。細かい閾値設計は後回し'),
 '監査ログの出力と保管': (PART, 0.5, 'Keycloak の標準出力を流すところまで。保管年数の作り込みは後回し'),
 'Keycloak の更新・保守': (PART, 0.5, '更新手順と HRD 拡張の配置まで'),
 '共通方式（エラー・ログ・整合・排他ほか）': (PART, 0.5, '文字コード・日時・ログの最小限'),
 'API 設計規約': (PART, 0.5, '標準 API をそのまま渡すため、エラーの返し方の整理だけ'),
 'アプリ開発者向けガイド（共通部）': (PART, 0.6, 'R3 標準 API を渡すので、使い方の説明は要る'),
 '開発・検証環境': (PART, 0.6, 'R1 3 面ぶんの用意。テストデータの作り込みは最小限'),
 '緊急時の管理者アクセス': (PART, 0.5, '入れる経路だけ確保'),
 '運用者アカウントと権限の保護': (PART, 0.5, '権限を配りすぎない設定だけ'),
 '運用手順書': (PART, 0.3, '起動・停止・切り分けの最小限'),
 '運用体制・当番': (PART, 0.3, '最小限の取り決め'),
 '稼働率・復旧目標（SLA / SLO）': (PART, 0.5, '目標値を置くだけ'),
 'トレーサビリティ': (PART, 0.5, '縮小版の範囲だけ追う'),
 '設計レビュー・説明会': (PART, 0.5, '対象が減るぶんレビューも減る'),
 '顧客の解約': (PART, 0.5, '止めるところまで。段階的な消去は後回し'),
 # ---------------- 対象外
 '顧客IdP からのユーザ情報の同期': (OUT, 0, 'R3 SCIM 受信は標準に無い（削減候補として合意済み）'),
 'ユーザの登録経路の区分': (OUT, 0, 'R3 標準に無い'),
 'ユーザの停止（消さずに無効化）': (OUT, 0, 'R4 シャドウユーザーはそのまま'),
 '停止済みユーザの再開': (OUT, 0, 'R4 シャドウユーザーはそのまま'),
 '長期未使用者の自動停止': (OUT, 0, 'R3 標準に無い'),
 '保存期限切れデータの消去': (OUT, 0, 'R3 標準に無い'),
 '顧客IdP の接続情報の自動追随': (OUT, 0, 'R3 標準に無い。手で入れ替える'),
 '顧客IdP・本基盤の証明書の期限監視': (OUT, 0, 'R3 標準に無い。手で見る'),
 'アプリの接続用パスワードの定期入れ替え': (OUT, 0, 'R3 自動化は作らない。手で入れ替える'),
 '不正なログインの兆候の検知': (OUT, 0, 'R4 セキュリティはネットワークのみ'),
 '個人情報の取り扱い': (OUT, 0, 'R4 セキュリティはネットワークのみ'),
 '本人からの開示・削除請求への対応': (OUT, 0, 'R4 セキュリティはネットワークのみ'),
 '顧客番号と基盤識別子の対応づけ': (OUT, 0, 'R7 権限側。Keycloak の外'),
 'アプリ向け管理 API の公開': (OUT, 0, 'R7 Keycloak を作るのみ'),
 '業務システムへの認証提供': (OUT, 0, 'R7 Keycloak を作るのみ'),
 '業務システム側のユーザ自動作成': (OUT, 0, 'R7 Keycloak を作るのみ'),
 '業務システムから他アプリへの連携': (OUT, 0, 'R7 Keycloak を作るのみ'),
 '利用規約への同意取得と記録': (OUT, 0, '要否が未確定'),
 '追加認証の利用': (OUT, 0, 'R7 追加認証は Keycloak-IdP 側（アプリ責務）。Keycloak-Broker では持たない'),
 '追加認証の登録': (OUT, 0, 'R7 同上'),
 '管理操作の 3 段階権限確認': (OUT, 0, 'R7 管理画面側。Keycloak を作るのみ'),
 '性能目標・チューニング方針': (OUT, 0, 'R6 性能は考慮しない'),
 'キャパシティ・データ量見積': (OUT, 0, 'R6 性能は考慮しない'),
 '同時実行・上限値の設定': (OUT, 0, 'R6 性能は考慮しない'),
 '性能試験の計画': (OUT, 0, 'R6 性能は考慮しない'),
 '災害対策（別地域への切替）': (OUT, 0, 'R5 バックアップを取るのみ'),
 '運用プロセス（受付・変更・障害）': (OUT, 0, '運用開始後の話。後回し'),
 'サービスレベルの測定と報告': (OUT, 0, '運用開始後の話。後回し'),
 '定期作業の計画と引き継ぎ': (OUT, 0, '運用開始後の話。後回し'),
 '既存からの移行': (OUT, 0, '切替はアプリ側。後回し'),
 '顧客向け説明資料': (OUT, 0, '契約に添える資料。後回し'),
}
# 項目レベルの上書き（機能名の判定と違えたい行）
ITEM_OVER = {
 'MKA-14': (PART, 0.5, 'R5 バックアップの構築まで。復元の実機確認は後回し'),
 'DR-04':  (OUT, 0, 'R5 復元は後回し'),
 'DR-03':  (OUT, 0, 'R5 可用性の試験は後回し'),
 'MKI-17': (OUT, 0, 'R5 切替訓練は後回し'),
 'SEC-04': (OUT, 0, 'R4 疑似攻撃検査は後回し'),
 'IT-11':  (IN, 1.0, 'R4 ネットワークの疎通・遮断は縮小版でも必須'),
 'SEC-05': (IN, 1.0, 'R4 境界側の対策の受入確認'),
}

SHEETS = {'基本設計': ['人日'], '詳細設計_製造': ['詳細設計 人日', '製造 人日'], 'テスト': ['人日']}
H, D, BEFORE = {}, {}, {}
for n in SHEETS: H[n], D[n] = load(f'SHEET_{n}.tsv')
for n, cols in SHEETS.items():
    BEFORE[n] = (len(D[n]), {c: sum(num(r[c]) for r in D[n]) for c in cols})

miss, tot = set(), collections.Counter()
for n, cols in SHEETS.items():
    newcols = ['縮小版'] + [f'縮小版 {c}' for c in cols]
    for c in newcols:
        if c not in H[n]: H[n].append(c)
    for r in D[n]:
        kind, ratio, why = RULES.get(r['機能名'], (None, None, None))
        if kind is None:
            miss.add(r['機能名']); kind, ratio, why = OUT, 0, '（未分類）'
        if r.get('ID') in ITEM_OVER: kind, ratio, why = ITEM_OVER[r['ID']]
        if n == '基本設計' and r['スコープ'] != '対象':
            kind, ratio, why = OUT, 0, f"Phase 1 でも{r['スコープ']}"
        r['縮小版'] = kind
        r['縮小版の理由'] = why
        for c in cols:
            v = num(r[c]) * ratio
            r[f'縮小版 {c}'] = fmt(v); tot[(n, c)] += round(v * 4) / 4
    if '縮小版の理由' not in H[n]: H[n].append('縮小版の理由')

errs = []
if miss: errs.append(f'RULES に無い機能名 {len(miss)} 件: {sorted(miss)}')
for n, cols in SHEETS.items():
    if BEFORE[n][0] != len(D[n]): errs.append(f'{n}: 行数が変わった')
    for c in cols:
        if abs(BEFORE[n][1][c] - sum(num(r[c]) for r in D[n])) > 1e-9: errs.append(f'{n}.{c}: 元の人日が変わった')
if errs:
    print('❌ エラー'); [print('  -', e) for e in errs]; sys.exit(1)

for n in SHEETS: save(f'SHEET_{n}.tsv', H[n], D[n])
print('✅ 元の行数・人日は不変')
for n, cols in SHEETS.items():
    c1 = collections.Counter(r['縮小版'] for r in D[n])
    print(f"  {n}: {dict(c1)}")
o = {c: BEFORE[n][1][c] for n, cols in SHEETS.items() for c in cols}
print(f"\n① {tot[('基本設計','人日')]} / {o['人日']}   "
      f"② {tot[('詳細設計_製造','詳細設計 人日')]} / {o['詳細設計 人日']}   "
      f"③ {tot[('詳細設計_製造','製造 人日')]} / {o['製造 人日']}   "
      f"④ {tot[('テスト','人日')]} / {sum(num(r['人日']) for r in D['テスト'])}")
print(f"縮小版 合計 {sum(tot.values())} 人日（フル 1026 人日の {sum(tot.values())/1026*100:.0f}%）")
