#!/usr/bin/env python3
"""機能 × 提供 API の対応表を作る（2026-09-09）。

方針転換: アプリへは「認証機能の API」を提供できればよい。Keycloak 標準にある API はそのまま渡し、
無いものだけカスタム（SPI / 前段 API）を個別に相談する。Broker と Keycloak-IdP で表を分ける。

区分（そのまま渡せるか）:
  ✅ 標準           … Keycloak 標準 API。設定するだけでアプリに渡せる
  ⚠ 標準（制約）    … 標準 API はあるが、そのままアプリに渡すと問題がある（権限が広すぎる 等）
  ⚙ 設定のみ        … アプリが呼ぶ API は無い。Keycloak 側の設定で満たす
  🔧 カスタム必要    … 標準に無い。SPI / 前段 API / バッチを作る
  ⛔ 使わない        … 標準にあるが、使わないと決めたもの
  ❌ 不可           … 原理的に提供できない

出力: SHEET_API提供一覧.tsv / ../api-provision-matrix-2026-09-09.md
"""
import csv, os, collections

W = os.path.dirname(os.path.abspath(__file__)); P = lambda n: os.path.join(W, n)
fl = list(csv.DictReader(open(P('SHEET_機能名一覧.tsv'), encoding='utf-8'), delimiter='\t'))
FUNC = {f['機能ID']: f for f in fl}

STD, LIM, CFG, CUS, NG = '✅ 標準', '⚠ 標準（制約）', '⚙ 設定のみ', '🔧 カスタム必要', '❌ 不可'
OUT = '⛔ 使わない（決定）'
APP, ADMIN, USER, SYS, BROWSER = 'アプリ（M2M）', '管理画面', 'エンドユーザ本人', 'バッチ・システム', 'ブラウザ（画面遷移）'

# (対象, 機能ID, API 名, メソッドとパス, 呼ぶ主体, 区分, 備考)
ROWS = [
# ============================ Keycloak-Broker: ログインとトークン（アプリが直接使う）
('Broker','F-AUTH-05','接続情報の公開','GET /realms/{r}/.well-known/openid-configuration',APP,STD,'アプリはこの 1 本から他の入口を自動取得できる。手で URL を配らない'),
('Broker','F-AUTH-05','ログイン開始（認可）','GET /realms/{r}/protocol/openid-connect/auth',BROWSER,STD,'認可コード + PKCE。顧客IdP への振り分けはこの先で Keycloak が行う'),
('Broker','F-AUTH-05','JWT の取得・更新','POST /realms/{r}/protocol/openid-connect/token',APP,STD,'認可コード交換 / リフレッシュ / システム間の 3 用途が同じ入口'),
('Broker','F-AUTH-05','ユーザ情報の取得','GET /realms/{r}/protocol/openid-connect/userinfo',USER,STD,'JWT に載せない属性をここで補う。JWT を軽くしたいときの受け皿'),
('Broker','F-AUTH-05','署名鍵の公開','GET /realms/{r}/protocol/openid-connect/certs',APP,STD,'アプリ側の JWT 検証に必須。鍵の入れ替えに自動追随する前提'),
('Broker','F-AUTH-06','SAML の接続情報','GET /realms/{r}/protocol/saml/descriptor',APP,STD,'顧客IdP・業務システムとの交換用'),
('Broker','F-AUTH-06','SAML の送受信','POST/GET /realms/{r}/protocol/saml',BROWSER,STD,'受け入れ（SP）と提供（IdP）の両方が同じ入口'),
('Broker','F-AZ-07','システム間 JWT の発行','POST /realms/{r}/protocol/openid-connect/token（client_credentials）',APP,STD,'アプリ・バッチが API を呼ぶための資格。スコープで範囲を絞る'),
('Broker','F-AZ-08','JWT の交換','POST /realms/{r}/protocol/openid-connect/token（token-exchange）',APP,STD,'Phase 1 対象外（FR-AUTH-005）。必要になったら設定で有効化'),
('Broker','F-AZ-10','JWT に載せる項目','（API なし）Protocol Mapper / Client Scope の設定',APP,CFG,'載せる項目はアプリごとにスコープで出し分ける。設計は必要だがアプリが呼ぶ API は無い'),
('Broker','F-AUTH-23','ログイン状態の保持','POST /realms/{r}/protocol/openid-connect/token（refresh_token）',APP,STD,'有効期間は Realm 設定。上限 12 時間（2026-09-07 決定）'),
('Broker','F-AUTH-24','ログアウト','GET/POST /realms/{r}/protocol/openid-connect/logout',BROWSER,STD,'本人のログイン状態を破棄。顧客IdP 側への連鎖は IdP ごとの設定'),
('Broker','F-AUTH-24','他アプリへのログアウト通知','（Keycloak → アプリ）Back-Channel Logout',APP,STD,'**アプリ側が受信の入口を作る**。Keycloak が呼びに行く向きなので、提供 API ではなくアプリへの実装要求'),
('Broker','F-AZ-10','JWT の失効','POST /realms/{r}/protocol/openid-connect/revoke',APP,LIM,'リフレッシュトークンは即時に効く。アクセストークンは署名だけで検証するアプリには最大 30 分残る（FR-SSO-009）'),
('Broker','F-AZ-10','JWT の有効性照会','POST /realms/{r}/protocol/openid-connect/token/introspect',APP,STD,'失効を即座に反映したい重要な操作で使う。毎回呼ぶと Keycloak の負荷になる'),
# ============================ Keycloak-Broker: 管理系（Admin REST API）
('Broker','F-ADM-16','顧客IdP の登録','POST /admin/realms/{r}/identity-provider/instances',ADMIN,LIM,'標準にある。ただし Admin API は Realm 全体に効くため、そのままアプリへは渡せない（後述の権限の絞り込みが前提）'),
('Broker','F-ADM-17','顧客IdP の変更・証明書更新','PUT /admin/realms/{r}/identity-provider/instances/{alias}',ADMIN,LIM,'同上'),
('Broker','F-ADM-16','顧客IdP の接続情報の取り込み','POST /admin/realms/{r}/identity-provider/import-config',ADMIN,STD,'相手の接続情報（メタデータ URL）から設定値を起こす'),
('Broker','F-INT-11','接続情報の自動追随','（標準に無い）',SYS,CUS,'定期的に取り込み直す仕組みは標準に無い。Admin API を叩くバッチを作る'),
('Broker','F-ADM-14','顧客の作成','POST /admin/realms/{r}/organizations',ADMIN,LIM,'Keycloak 26 の Organizations を顧客の単位に使う'),
('Broker','F-ADM-15','顧客設定の編集','PUT /admin/realms/{r}/organizations/{id}',ADMIN,LIM,'ドメイン・表示名など'),
('Broker','F-ADM-23','顧客の解約','DELETE /admin/realms/{r}/organizations/{id}',ADMIN,LIM,'所属ユーザの扱いは別途の手順が要る（消さずに止める方針）'),
('Broker','F-ADM-16','顧客と顧客IdP の紐付け','POST /admin/realms/{r}/organizations/{id}/identity-providers',ADMIN,LIM,'顧客ごとに使える顧客IdP を限定する。越境防止の土台'),
('Broker','F-ADM-01','ユーザの検索・一覧','GET /admin/realms/{r}/users',ADMIN,LIM,'標準にある。件数の区切りと検索条件も標準'),
('Broker','F-ADM-01','ユーザの詳細参照','GET /admin/realms/{r}/users/{id}',ADMIN,LIM,''),
('Broker','F-ADM-03','ユーザの登録','POST /admin/realms/{r}/users',ADMIN,LIM,''),
('Broker','F-ADM-03','ユーザの変更','PUT /admin/realms/{r}/users/{id}',ADMIN,LIM,'属性の追加は User Profile で宣言した項目のみ'),
('Broker','F-ADM-05','ユーザの利用可否の切替','PUT /admin/realms/{r}/users/{id}（enabled）',ADMIN,LIM,'停止・再開はこの 1 本'),
('Broker','F-PROV-10','ユーザの停止','PUT /admin/realms/{r}/users/{id}（enabled=false）',SYS,LIM,'停止日時の記録は属性で持つ（標準の項目に無いため User Profile で宣言）'),
('Broker','F-PROV-11','停止済みユーザの再開','PUT /admin/realms/{r}/users/{id}（enabled=true）',SYS,LIM,'誤って戻さない条件の判定は呼ぶ側の責任'),
('Broker','F-ADM-05','ユーザの削除','DELETE /admin/realms/{r}/users/{id}',ADMIN,LIM,'Phase 1 は消さずに止める方針のため通常は使わない'),
('Broker','F-ADM-10','強制ログアウト（1 人）','POST /admin/realms/{r}/users/{id}/logout',ADMIN,LIM,''),
('Broker','F-ADM-10','強制ログアウト（全員）','POST /admin/realms/{r}/logout-all',ADMIN,LIM,'事故対応用。顧客単位の一括は標準に無く、対象を絞って繰り返す'),
('Broker','F-ADM-01','ログイン状態の一覧','GET /admin/realms/{r}/users/{id}/sessions',ADMIN,LIM,''),
('Broker','F-AUTH-20','締め出しの解除','DELETE /admin/realms/{r}/attack-detection/brute-force/users/{id}',ADMIN,STD,'連続失敗で止まったユーザを戻す。締め出しそのものは Realm 設定'),
('Broker','F-INT-13','アプリの接続登録','POST /admin/realms/{r}/clients',ADMIN,LIM,'ひな形を用意して登録する'),
('Broker','F-INT-13','アプリの接続登録（申請式）','POST /realms/{r}/clients-registrations/{provider}',APP,STD,'管理者が発行した引換券（initial access token）でアプリ側が自分で登録できる。Admin API を渡さずに済む'),
('Broker','F-INT-13','引換券の発行','POST /admin/realms/{r}/clients-initial-access',ADMIN,LIM,'上の申請式で使う券'),
('Broker','F-BAT-05','接続用パスワードの再発行','POST /admin/realms/{r}/clients/{id}/client-secret',ADMIN,LIM,'入れ替えの周期と通知は運用側で作る'),
('Broker','F-BAT-04','署名鍵の状態確認','GET /admin/realms/{r}/keys',ADMIN,LIM,'鍵の追加・無効化は components API。並走期間の管理は運用手順'),
('Broker','F-BAT-07','証明書期限の監視','（標準に無い）',SYS,CUS,'期限が近いものを知らせる仕組みは標準に無い。API を読むバッチを作る'),
('Broker','F-ADM-25','監査ログの取得','GET /admin/realms/{r}/events / GET /admin/realms/{r}/admin-events',ADMIN,LIM,'保管と検索は全体の共通基盤側。Keycloak の標準出力を流す方式が主で、この API は補助'),
('Broker','F-AZ-06','管理操作の権限の絞り込み','（API ではなく設定）Admin Permissions（FGAP v2）',ADMIN,CFG,'Keycloak 26.2 以降の標準機能。ユーザ・グループ・顧客の単位で管理権限を絞れる。**アプリへ Admin API を渡す場合の前提**'),
# ============================ Keycloak-Broker: 標準に無いもの
('Broker','F-AUTH-02','ログインの振り分け（HRD）','（一部のみ標準）Organizations のドメイン一致',BROWSER,CUS,'メールのドメインで振り分けるのは標準。**識別子（顧客コード）で振り分けるには拡張が要る**'),
('Broker','F-PROV-03','ユーザ登録の受信（SCIM）','（標準に無い）',SYS,CUS,'**Keycloak に SCIM の受信機能は無い**。作るか、外部の実装を持ち込むか、使わないかの判断が要る'),
('Broker','F-PROV-03','ユーザ更新の受信（SCIM）','（標準に無い）',SYS,CUS,'同上'),
('Broker','F-PROV-03','削除通知の受信（SCIM）','（標準に無い）',SYS,CUS,'同上'),
('Broker','F-PROV-03','ユーザ検索の受信（SCIM）','（標準に無い）',SYS,CUS,'同上'),
('Broker','F-INT-04','アプリへの変更通知（Webhook）','（標準に無い）',APP,CUS,'イベントを外へ送るには拡張が要る。Phase 1 対象外'),
('Broker','F-BAT-01','長期未使用者の自動停止','（標準に無い）',SYS,CUS,'最終ログイン日時での抽出と停止は Admin API を使うバッチを作る'),
('Broker','F-BAT-09','保存期限切れの消去','（標準に無い）',SYS,CUS,'同上。Phase 1 は準備のみ'),
('Broker','F-AUTH-21','実在推測の防止','（標準に無い）',BROWSER,CUS,'応答を同じにする作り込みが要る'),
('Broker','F-PROV-01','初回ログイン時のユーザ自動作成','（API なし）First Broker Login Flow の設定',SYS,CFG,'設定で満たす。ただし登録経路の区分を付けるには拡張が要る'),
('Broker','F-PROV-08','項目名の変換・統一','（API なし）IdP Mapper / User Profile の設定',SYS,CFG,'顧客ごとの変換表は設定として持つ'),
('Broker','F-AZ-05','顧客越境の防止','（API なし）Organizations + フローの設定',SYS,CFG,'顧客と顧客IdP の紐付けで構造的に防ぐ'),
('Broker','F-AUTH-25','ログイン画面','（API なし）テーマ',BROWSER,CFG,'画面はテーマで作る。アプリから呼ぶ API は無い'),
('Broker','F-INT-01','業務システムへの認証提供','POST/GET /realms/{r}/protocol/saml',BROWSER,STD,'ServiceNow へは SAML で提供する'),
# ============================ Keycloak-IdP
('IdP','F-AUTH-01','ID/PW でのログイン','GET /realms/{r}/protocol/openid-connect/auth',BROWSER,STD,'Broker から委譲されて動く。アプリが直接呼ぶことはない'),
('IdP','F-AUTH-19','パスワードの変更（本人）','GET /realms/{r}/protocol/openid-connect/auth?kc_action=UPDATE_PASSWORD',BROWSER,STD,'**A-1 決定: 画面へ誘導**。アプリは自分の画面から このパラメータ付きで送るだけ。メール不要。戻り先に `kc_action_status` が付く。※Account API のパスワード変更は現行 Keycloak で廃止済みのため、この方式が標準の答え'),
('IdP','F-AUTH-18','パスワードの自己再設定','（標準に無い / 画面はある）',USER,CUS,'画面の「パスワードをお忘れですか」はメール前提。**メールを持たないユーザには使えない**ため別手段が要る'),
('IdP','F-ADM-07','パスワードの初期化（管理者）','PUT /admin/realms/{r}/users/{id}/reset-password',ADMIN,LIM,'**これは標準にある**。今のパスワードは確認しない。一時パスワードにもできる'),
('IdP','F-AUTH-19','変更の強制（初回など）','PUT /admin/realms/{r}/users/{id}/execute-actions-email',ADMIN,LIM,'メールで誘導する方式。メールを持たないユーザには使えない'),
('IdP','F-AUTH-19','変更の強制（メールなし）','PUT /admin/realms/{r}/users/{id}（requiredActions）',ADMIN,LIM,'次のログイン時に変更画面を出す。メール不要でこちらが実用的'),
('IdP','(なし)','パスワードの取得','—',USER,NG,'**パスワードは復元できない形で保管するため、取得する API は原理的に作れない**（Keycloak に限らない）。用途を伺って別の手段に置き換える'),
('IdP','F-AUTH-01','パスワードの照合','（推奨できる標準が無い）',APP,CUS,'ID とパスワードの正誤だけを判定する API は、標準では非推奨の方式しかない（FR-AUTH-008 で不採用）。ログイン画面へ誘導する形に置き換える'),
('IdP','F-AUTH-10','追加認証（数字コード）','（API なし）Authentication Flow の設定',BROWSER,CFG,'ログイン画面の中で完結する'),
('IdP','F-AUTH-12','追加認証の登録','GET /realms/{r}/protocol/openid-connect/auth?kc_action=CONFIGURE_TOTP',BROWSER,STD,'**A-1 と同じ仕組み**。アプリの画面から登録へ送れる。登録そのものを API で行う標準は無いが、誘導は標準でできる。※登録されたかは戻り値を信用せず `acr` 等で確認する'),
('IdP','F-ADM-09','追加認証の解除（管理者）','DELETE /admin/realms/{r}/users/{id}/credentials/{credentialId}',ADMIN,LIM,'**標準にある**。端末紛失時の復旧に使う'),
('IdP','F-AUTH-10','認証手段の一覧（本人）','GET /realms/{r}/account/credentials',USER,STD,'本人のトークンで呼べる。登録済みの手段の確認に使う'),
('IdP','F-AUTH-12','認証手段の削除（本人）','DELETE /realms/{r}/account/credentials/{id}',USER,LIM,'標準にあるが非推奨の扱い。画面へ誘導する方が安全'),
('IdP','F-ADM-03','自分の情報の参照・更新','GET/POST /realms/{r}/account/',USER,STD,'**本人のトークンで呼べる**。管理 API を渡さずにプロフィール編集を実現できる'),
('IdP','F-ADM-10','自分のログイン状態の確認・破棄','GET/DELETE /realms/{r}/account/sessions',USER,STD,'同上'),
('IdP','F-AUTH-01','連携先の確認・解除（本人）','GET/DELETE /realms/{r}/account/linked-accounts',USER,STD,'同上'),
('IdP','F-ADM-03','ユーザの登録・変更・停止','POST/PUT /admin/realms/{r}/users …',ADMIN,LIM,'Broker 側と同じ Admin API。IdP-KC 側のユーザが対象'),
('IdP','F-AUTH-22','流出パスワードの使用拒否','（標準に無い）',SYS,CUS,'照合する仕組みは標準に無い'),
('IdP','F-AUTH-16','メールを持たない人の復旧','（標準に無い）',ADMIN,CUS,'管理者の承認を経て復旧する手順を作る'),
('IdP','F-AUTH-20','連続失敗時の締め出し','（API なし）Realm 設定 + attack-detection',SYS,CFG,'解除は Broker 側と同じ API'),
# ============================ 追補（Broker）
('Broker','F-AUTH-04','顧客IdP の指定','GET /realms/{r}/protocol/openid-connect/auth?kc_idp_hint={alias}',BROWSER,STD,'アプリが送り先を指定できる標準のパラメータ。振り分けを画面に頼らない手段'),
('Broker','F-AUTH-03','振り分け失敗時の切替','（API なし）フローの設定 + 拡張',BROWSER,CUS,'判定できなかったときの逃げ道。HRD の拡張と一体で作る'),
('Broker','F-PROV-02','ログイン時の属性更新','（API なし）IdP Mapper の syncMode 設定',SYS,CFG,'2 回目以降に上書きする項目を Mapper ごとに決める'),
('Broker','F-AUTH-09','Keycloak-Broker と Keycloak-IdP の連携','（API なし）IdP エントリの設定',SYS,CFG,'Broker から見て Keycloak-IdP は顧客IdP の 1 つ。Keycloak-IdP 側に求める設定は接続仕様（HE-23）で渡す'),
('Broker','F-ADM-08','ユーザの招待','POST /admin/realms/{r}/organizations/{id}/members/invite-user',ADMIN,LIM,'Organizations の標準機能。**メール送信が前提**のため、メールを持たないユーザには使えない'),
('Broker','F-ADM-20','ユーザの一括登録','POST /admin/realms/{r}/partialImport',ADMIN,LIM,'標準にある。件数の上限に合わせて分割して投入する'),
('Broker','F-ADM-21','設定のファイル出力','POST /admin/realms/{r}/partial-export',ADMIN,LIM,'**ユーザは出力に含まれない**。ユーザの持ち出しは検索 API を繰り返すか、サーバ側の書き出し機能を使う'),
('Broker','F-ADM-24','本人からの開示・削除請求','GET /admin/realms/{r}/users/{id} / DELETE …',ADMIN,LIM,'標準 API の組合せで足りる。対応の記録は運用側で残す'),
('Broker','F-INT-14','管理 API の内部公開','（本基盤が決める）到達経路・呼び出し元の資格・許す操作',APP,CUS,'**今回の論点そのもの**。Admin API をどこまでアプリへ開くかを決め、権限の絞り込み（FGAP v2）と経路で守る'),
('Broker','F-INT-08','不正兆候の検知','GET /admin/realms/{r}/events + 外部の集計',SYS,CUS,'検知そのものは標準に無い。イベントを取り出して外で判定する'),
('Broker','F-INT-09','擬似ログインによる障害検知','（標準 API を外部から呼ぶ）',SYS,CFG,'専用 API は不要。ログイン用の標準の入口を監視から定期的に叩く'),
('Broker','F-PROV-09','登録経路の区分判定','（API なし）User Profile の属性 + 拡張',SYS,CUS,'どの経路で作られたかを属性で持つ。付与は拡張側'),
('Broker','F-INT-03','業務システムから他アプリへの連携','POST /realms/{r}/protocol/openid-connect/token（token-exchange）',APP,STD,'ServiceNow から他アプリの API を呼ぶ経路'),
# ============================ 逆点検（2026-09-09）で足りていなかったもの — G-1〜G-15
('Broker','F-AUTH-23','ログイン済みかの確認（画面遷移なし）','GET /realms/{r}/protocol/openid-connect/auth?prompt=none',BROWSER,STD,'**G-1**。画面を出さずにログイン状態を確かめる標準の方法。SPA が起動時に使う。画面のあるアプリには実質必須で、表から漏れていた'),
('Broker','F-AUTH-23','セッション状態の監視','GET /realms/{r}/protocol/openid-connect/login-status-iframe.html',BROWSER,STD,'**G-1**。別のタブでログアウトされたことに気づく仕組み。サーバ側でセッションを持つ作り（BFF）なら不要'),
('Broker','F-ADM-01','ユーザの件数取得','GET /admin/realms/{r}/users/count',ADMIN,LIM,'**G-3**。一覧の総件数。ページ送りの実装に要る'),
('Broker','F-ADM-01','属性でのユーザ検索','GET /admin/realms/{r}/users?q=key:value',ADMIN,LIM,'**G-3**。社員番号など独自の項目で引く手段。**3 階層の識別子の設計に直結**するのに表から漏れていた'),
('Broker','F-ADM-14','顧客のメンバー管理','GET/POST /admin/realms/{r}/organizations/{id}/members・DELETE .../members/{id}',ADMIN,LIM,'**G-4**。誰がどの顧客に属するかの付け外し。顧客の CRUD だけでは足りない'),
('Broker','F-ADM-14','顧客のメンバー件数','GET /admin/realms/{r}/organizations/{id}/members/count',ADMIN,LIM,'**G-4**。課金・レポートの母数'),
('Broker','F-PROV-01','顧客IdP との紐付けの付け外し','POST/DELETE /admin/realms/{r}/users/{id}/federated-identity/{alias}',ADMIN,LIM,'**G-5**。顧客が IdP を乗り換えたときの繋ぎ替え、重複ユーザの統合で使う。**移行と事故対応の要**'),
('Broker','F-AUTH-20','締め出し状態の確認','GET /admin/realms/{r}/attack-detection/brute-force/users/{id}',ADMIN,LIM,'**G-6**。「入れない」問い合わせの一次切り分け。解除だけ拾って状態確認が漏れていた'),
('Broker','F-AZ-10','失効の一斉通知','POST /admin/realms/{r}/clients/{id}/push-revocation',ADMIN,LIM,'**G-7**。ある時刻より前に出した JWT を無効として各アプリへ押し出す。**JWT が最大 30 分残る問題の緩和策**として設計に入れていたのに表から漏れていた'),
('Broker','F-ADM-25','記録する項目の設定','GET/PUT /admin/realms/{r}/events/config',ADMIN,LIM,'**G-8**。何を記録し何日残すかの設定。監査設計の前提だが表から漏れていた'),
('Broker','F-ADM-01','なりすまし（調査用）','POST /admin/realms/{r}/users/{id}/impersonation',ADMIN,OUT,'**G-9。2026-09-09 決定: 不要**。標準にはあるが使わない。**権限を配るときにこの操作を許さないことを明示する**（Admin Permissions の設定で落とす）'),
('Broker','F-ADM-25','アプリ単位のセッション一覧','GET /admin/realms/{r}/clients/{id}/user-sessions',ADMIN,LIM,'**G-10**。障害時に「どのアプリで何人繋がっているか」を見る'),
('Broker','F-ADM-25','サーバ情報の取得','GET /admin/serverinfo',ADMIN,LIM,'**G-12**。版数・有効な機能の確認。版上げの前後で使う'),
('Broker','F-ADM-25','死活と性能値の公開','GET /health・/health/ready・/health/live・/metrics（9000 番）',SYS,STD,'**G-2**。**既定では無効で、明示的に有効化が要る**。9000 番は業務用の口とは別。**2026-09-09 決定: 監視は ROSA のあるアカウントでそれぞれ行う**（Broker 用・Keycloak-IdP 用の各アカウント内で完結し、他組織が管理する境界は通さない）'),
('IdP','F-AUTH-10','同意した先の確認・取り消し','GET /realms/{r}/account/applications・DELETE .../applications/{clientId}/consent',USER,STD,'**G-11**。本人が「どのアプリに情報を渡したか」を見て取り消す。同意画面を使わない運用なら不要'),
('Broker','F-BAT-01','最終ログイン日時の取得','（標準に無い）',APP,CUS,'**G-13**。**Keycloak はユーザの最終ログイン日時を持たない**（記録イベントからしか分からない）。自動停止の判定にも、アプリの画面表示にも要るので拡張が必要'),
('IdP','F-AUTH-19','パスワードの変更日・期限の取得','（標準に無い）',APP,CUS,'**G-14**。「あと何日で期限」を出す標準の手段が無い'),
('Broker','F-ADM-05','一括の有効化・無効化','（標準に無い）1 件ずつの呼び出しをまとめる',SYS,CUS,'**G-15。2026-09-09 決定: 必要だが削減候補**。標準は 1 件ずつのため件数分の呼び出しになる。**数万人規模の停止が時間内に終わるかは性能試験で確かめる**'),
]
# この表で触れない機能と、その理由
SKIP = {
 'F-PROV-14': '権限側の話。認可はアプリ責務のため本基盤の提供 API に含めない',
 'F-PROV-15': '同上', 'F-PROV-16': '同上', 'F-PROV-17': '同上',
 'F-AZ-01': '認可はアプリ責務（2026-09-06 前提）。本基盤は JWT を渡すところまで',
 'F-AZ-02': '同上', 'F-AZ-03': '同上', 'F-AZ-04': '同上',
 'F-ADM-11': '同上', 'F-ADM-12': '同上', 'F-ADM-19': '同上', 'F-BAT-08': '同上',
 'F-ADM-13': '顧客の中の部署の管理。管理画面側の機能で、Keycloak の API では持たない',
 'F-AUTH-29': 'Keycloak-IdP の引き渡しと責任分界。API ではなく取り決め',
 'F-AUTH-14': 'Phase 1 対象外（2 台目の認証器の本人再確認）',
 'F-AUTH-17': 'ステップアップ認証は不要と決定済み',
 'F-AUTH-15': 'Phase 1 対象外（復旧用コード）',
 'F-AUTH-26': '画面。アプリから呼ぶ API は無い', 'F-AUTH-27': 'アプリ側の画面',
 'F-AUTH-28': '要否が未確定（D-22）。確定後に再整理する',
 'F-PROV-03': 'Phase 1 対象外（SCIM のグループ連携）',
 'F-PROV-12': '2026-09-07 決定により伝播しない', 'F-PROV-13': '同上', 'F-BAT-02': '同上',
 'F-BAT-03': 'Phase 1 対象外（日次の突合）',
 'F-INT-12': 'Phase 1 対象外（状態変化の即時通知）',
 'F-INT-07': 'メール送信。Keycloak の設定で送るもので、アプリへ渡す API は無い',
 'F-INT-02': 'ServiceNow 側の設定で自動作成させる。本基盤が出す API は無い',
 'F-ADM-18': '照会は全体の共通基盤側で行う（本基盤に照会画面を作らない）',
 'F-ADM-22': 'Phase 1 対象外（システム用アカウントの台帳）',
}

# 2026-09-09 のユーザー回答（1〜7）を反映したコスト区分
COST_CUT = {  # 削減候補（やらない判断ができれば消える）— キーは「提供する API」名（行単位で効かせる）
 'ユーザ登録の受信（SCIM）': 'A-5: 削減候補。ただし候補リストには残す',
 'ユーザ更新の受信（SCIM）': 'A-5: 削減候補', '削除通知の受信（SCIM）': 'A-5: 削減候補', 'ユーザ検索の受信（SCIM）': 'A-5: 削減候補',
 'パスワードの自己再設定': 'A-2: 初期パスワードの動線は準備するが削減候補',
 '一括の有効化・無効化': 'G-15: 必要だが削減候補',
}
COLS = ['対象', '機能ID', '機能グループ', '機能名', '提供する API（機能の粒度）', 'エンドポイント', '呼ぶ主体', '区分', 'コスト', '備考']
out = []
for tgt, fid, api, ep, who, kind, note in ROWS:
    f = FUNC.get(fid, {})
    if api in COST_CUT: cost = '🔻 削減候補'
    elif kind == CUS: cost = '🔺 標準外（追加コスト）'
    elif kind in (NG, OUT): cost = '— 提供しない'
    else: cost = '標準内'
    if api in COST_CUT: note = f'{note}／{COST_CUT[api]}'
    out.append({'対象': tgt, '機能ID': fid, '機能グループ': f.get('機能グループ', '—'), '機能名': f.get('機能名', '—'),
                '提供する API（機能の粒度）': api, 'エンドポイント': ep, '呼ぶ主体': who, '区分': kind,
                'コスト': cost, '備考': note})
with open(P('SHEET_API提供一覧.tsv'), 'w', encoding='utf-8', newline='') as fp:
    w = csv.writer(fp, delimiter='\t', lineterminator='\n'); w.writerow(COLS)
    for o in out: w.writerow([o[c] for c in COLS])

covered = {r[1] for r in ROWS}
rest = [f for f in fl if not f['機能ID'].startswith('NF-') and f['機能ID'] not in covered]
unexplained = [f['機能ID'] for f in rest if f['機能ID'] not in SKIP]

# ---------------------------------------------------------------- 報告用 md
R = os.path.join(W, '..')
def table(rows):
    s = '| 機能 | 提供する API | エンドポイント | 呼ぶ主体 | 区分 | コスト | 備考 |\n|---|---|---|---|:-:|:-:|---|\n'
    for o in rows:
        g = lambda t: str(t).replace('|', '/')
        s += (f"| {g(o['機能名'])} | {g(o['提供する API（機能の粒度）'])} | `{g(o['エンドポイント'])}` | {g(o['呼ぶ主体'])} "
              f"| {o['区分']} | {o['コスト'].replace('標準内','')} | {g(o['備考'])} |\n")
    return s
with open(os.path.join(R, 'api-provision-matrix-2026-09-09.md'), 'w', encoding='utf-8') as fp:
    fp.write('# 機能 × 提供 API の対応表（Keycloak-Broker / Keycloak-IdP）\n\n')
    fp.write('- **日付**: 2026-09-09 ／ **反映用**: `wbs-text/SHEET_API提供一覧.tsv`\n')
    fp.write('- **目的**: 認証の機能をアプリへ **API として渡す** 形に整理し直す。'
             'Keycloak の標準にある API はそのまま渡し、無いものだけ個別に相談する\n')
    fp.write('- `{r}` は Realm 名。エンドポイントは Keycloak 26 系の表記\n\n')
    fp.write('## 区分の意味\n\n| 区分 | 意味 | 件数 |\n|:-:|---|---:|\n')
    cnt = collections.Counter(o['区分'] for o in out)
    for k, v in [(STD, 'Keycloak 標準。設定するだけでアプリに渡せる'), (LIM, '標準 API はあるが、そのまま渡すと権限が広すぎる等の制約がある'),
                 (CFG, 'アプリが呼ぶ API は無い。Keycloak 側の設定で満たす'), (CUS, '標準に無い。拡張・前段の API・バッチのいずれかを作る'),
                 (OUT, '標準にあるが、使わないと決めたもの'), (NG, '原理的に提供できない')]:
        fp.write(f'| {k} | {v} | {cnt[k]} |\n')
    fp.write(f'| **計** | | **{len(out)}** |\n\n')
    fp.write('''## 0. 先に結論

1. **ログインとトークンの系は、そのままアプリに渡せる。** ログイン開始・JWT の取得と更新・ユーザ情報・署名鍵・ログアウト・失効・有効性照会は全部 Keycloak の標準で、追加で作るものは無い。**「認証機能ができて API を渡せればよい」という要望は、この範囲なら設定だけで満たせる**
2. **パスワードまわりが最大の穴。** 例に挙がった 2 つはどちらも素直には出せない
   - **パスワード変更 API は現行の Keycloak に無い**。かつて Account API にあったが削除された（[AccountCredentialResource は一覧・削除・ラベル変更のみ](https://github.com/keycloak/keycloak/blob/main/services/src/main/java/org/keycloak/services/resources/account/AccountCredentialResource.java)）
   - **パスワード取得 API は原理的に作れない**。復元できない形で保管しているため、Keycloak に限らずどの製品でも出せない
3. **管理系（Admin REST API）は「ある」が「そのまま渡す」と危ない。** ユーザ CRUD・停止・強制ログアウト・顧客IdP 登録などは標準で揃っているが、**Admin API のトークンは既定で Realm 全体に効く**。誰にどこまで渡すかを決めないと、アプリが他の顧客のユーザも触れてしまう
4. **標準に無いのは 21 件**。中身は SCIM 受信・振り分け（HRD）・Webhook・自動停止・証明書期限監視・パスワードまわり。**コストはここに集中する**

''')
    for tgt, title, lead in [('Broker', '1. Keycloak-Broker が提供する API',
            'アプリ・管理画面・業務システムが実際に呼ぶ入口。**ログインとトークンの系（✅ が並ぶ部分）はそのまま渡せる**。'),
            ('IdP', '2. Keycloak-IdP が提供する API',
            'パスワードを持つ側。**パスワードまわりは標準 API が薄く、ここが今回いちばんの論点**。')]:
        fp.write(f'## {title}\n\n{lead}\n\n')
        rows = [o for o in out if o['対象'] == tgt]
        for grp in dict.fromkeys(o['機能グループ'] for o in rows):
            fp.write(f'### {grp}\n\n' + table([o for o in rows if o['機能グループ'] == grp]) + '\n')
    fp.write('## 3. この表で扱っていない機能と理由\n\n| 機能ID | 機能 | 理由 |\n|---|---|---|\n')
    for f in rest:
        fp.write(f"| {f['機能ID']} | {f['機能名']} | {SKIP.get(f['機能ID'], '⚠ 未整理')} |\n")
    fp.write('''
非機能（NF-*）は構成・運用の設計であり、アプリへ渡す API を持たないため本表の対象外。

## 4. 決定（2026-09-09 ユーザー回答）

| # | 論点 | 決定 | 残る作業・確認 |
|---|---|---|---|
| **A-1** | パスワードの変更 | **Keycloak の画面へ誘導する**。アプリは自分の画面から `kc_action=UPDATE_PASSWORD` を付けてログインの入口へ送るだけでよい（Keycloak 標準の仕組み。**メール不要**） | 画面のカスタマイズ分担は §4.1 |
| **A-2** | パスワードの取得 | **不要**。初期パスワードの動線だけ用意する（管理 API で一時パスワードを設定 → 次のログインで変更を強制） | **削減候補としてマーク**（表の「コスト」列 🔻） |
| **A-3** | 管理 API をアプリへ渡すか | **渡す。一般利用者は触れない**（§4.2 で根拠と条件） | 守るべき条件 4 点 + 実機確認 1 件 |
| **A-4** | 管理 API の経路 | **アプリのサーバ / BFF から内部経路で呼ぶ**（ブラウザからは呼ばせない）。認識のとおり | 禁則 K-10 の書き換え |
| **A-5** | SCIM 受信 | **削減候補。ただし候補リストには残す** | 表の「コスト」列 🔻 でマーク済み |
| **A-6** | 振り分け（HRD） | **識別子で振り分ける（②）＝ 標準外**。コスト増としてマーク | 表の「コスト」列 🔺 |
| **A-7** | メール送信 | **アプリへ寄せたい**。技術的な可否は §4.3。**検討事項として残す** | ログインできない人の再設定が論点 |

### 4.1 A-1 の続き: ログイン画面のカスタマイズをアプリに分担できるか

**できる。ただし「作る人」と「載せる人」は分かれる。**

| 分担 | 内容 |
|---|---|
| **アプリチーム（作る）** | テーマの中身。スタイル・ロゴ・文言・画面のひな形。Keycloak のテーマは HTML のひな形（FreeMarker）・画像・文言ファイル・スタイルの集まりで、既存テーマを継承して**上書きしたいものだけ置く** |
| **本基盤（載せる）** | 実行イメージへの取り込みと配置。ROSA + Operator では**テーマを入れた専用イメージを作って差し替える**のが標準。Keycloak 26.2 以降は、同じ Keycloak 版であればテーマの入れ替えを**止めずに反映できる** |

**条件を 2 つ付ける。**

1. **上書きは最小限にする。** スタイル・ロゴ・文言だけの上書きなら版上げの影響をほぼ受けない。**HTML のひな形まで上書きすると、Keycloak の版を上げるたびに追随が要る**（公式にも「上書きした場合は新しい版で更新が必要になり得る」と明記）。ここを守れるかで運用コストが変わる
2. **受け渡しの形を決める。** アプリチームがテーマ一式を渡し、本基盤がイメージを作って載せる、という流れと、版上げ時の確認の分担を先に決める

### 4.2 A-3 の続き: 一般利用者が管理 API を触れてしまわないか

**触れない。** 一般利用者のトークンでは管理 API は動かず、`403` で拒否される。

- 管理 API は `realm-management` という専用の権限を要求する。**一般利用者のトークンにはこの権限が入っていない**ため、パラメータをどう変えても他の顧客のユーザは見えない
- 自分の情報を扱う Account API は、**呼んだ本人だけ**が対象になる作りで、他人を指定する余地が無い
- 顧客（Organizations）の一覧も、権限が無ければ返らない

**そのうえで、渡し方で守る条件が 4 つある。** これを外すと危なくなるので、設計に落とす。

| # | 条件 | 理由 |
|---|---|---|
| 1 | **管理 API はアプリのサーバ / BFF から呼ぶ。ブラウザには管理用の資格を出さない** | ブラウザに出した時点で利用者の手元に渡る（A-4 と同じ） |
| 2 | **管理用の資格はアプリごとに分け、必要な権限だけ付ける** | 「全部できる権限」を 1 つ配ると、事故の範囲が全顧客に広がる |
| 3 | **アプリの Client に「全権限をトークンに載せる」設定を使わない** | 利用者のトークンに管理権限が紛れ込むのを防ぐ |
| 4 | **どの顧客のデータを触ってよいかは Keycloak の権限の絞り込み（Admin Permissions）で制限する** | Keycloak 26.2 以降の標準機能。顧客単位の絞り込みは 26.7 以降 |

> ⚠ **実機確認が 1 件必要**: この絞り込みが **サービスアカウント（アプリのサーバ用の資格）に対しても効くか**は、以前の版で効かない報告がある。**効かない場合は、アプリごとに顧客を跨げないことを保証できないため、前段の API を作る判断に戻る**。PoC 項目として立てる（G-FGAP）

### 4.3 A-7 の続き: メールをアプリに寄せられるか

**2 つに分けて考える必要がある。**

| 場面 | アプリに寄せられるか | 方法 |
|---|---|---|
| **パスワードの変更**（ログインできる人） | **できる。メールも不要** | アプリの画面から `kc_action=UPDATE_PASSWORD` を付けてログインの入口へ送る。戻ってきたときに結果が付いてくる |
| **パスワードの再設定**（**忘れてログインできない人**） | **そのままでは寄せられない** | `kc_action` はログイン済みが前提。**アプリがメールを送り、リンク先でアプリが本人確認をし、そのうえで管理 API で一時パスワードを設定する**、という流れなら寄せられる。**「本人確認をアプリがやる」ことになる点が論点** |

**Keycloak が出す再設定リンクだけをアプリのメールに載せる、はできない。** リンクを発行して返す API が標準に無く、Keycloak が自分でメールを送る形しか用意されていないため。

→ **検討事項として残す**。決めるべきは「ログインできない人の本人確認を誰がやるか」で、メールを持たない利用者の扱い（既存の論点）と合わせて整理する。

## 4y. 逆点検（2026-09-09）— 普通に必要な API から見て足りないもの

**やったこと**: 「認証基盤がアプリに出すもの」の一般的な並び（① ログインとトークン ② 本人のセルフサービス ③ ユーザと顧客の管理 ④ 事故対応・問い合わせ対応 ⑤ 運用・監視）を先に立て、**そこから逆に表を突き合わせた**。結果 **15 件の抜け**が見つかり、表に追加した（90 → 107 行）。

| # | 抜けていたもの | 影響 | 状態 |
|---|---|---|---|
| **G-1** | **画面を出さずにログイン状態を確かめる**（`prompt=none` / セッション監視の枠） | **画面のあるアプリでは実質必須**。無いと起動のたびに画面が点滅する、別タブのログアウトに気づけない | ✅ 標準。追加した |
| **G-3** | **属性でのユーザ検索**（`?q=key:value`）と**件数取得** | **社員番号などの独自項目で引く手段。3 階層の識別子の設計に直結**。無いと一覧のページ送りも作れない | ✅ 標準。追加した |
| **G-7** | **失効の一斉通知**（push-revocation） | **「JWT が最大 30 分残る」問題の緩和策として設計に入れていたのに、API の表から漏れていた** | ✅ 標準。追加した |
| **G-5** | **顧客IdP との紐付けの付け外し** | 顧客が IdP を乗り換えたときの繋ぎ替え、重複ユーザの統合。**移行と事故対応の要** | ✅ 標準。追加した |
| **G-4** | **顧客のメンバー管理**（members の追加・削除・一覧・件数） | 顧客の作成だけでは「誰がその顧客に属するか」を動かせない | ✅ 標準。追加した |
| **G-2** | **死活と性能値**（9000 番の health / metrics） | ROSA の起動判定と監視に必須。**既定では無効で、有効化の指定が要る** | ✅ 標準。追加した |
| **G-8** | **記録する項目の設定**（events/config） | 何を記録し何日残すかの設定。監査設計の前提 | ✅ 標準。追加した |
| **G-6** | **締め出し状態の確認** | 「入れない」問い合わせの一次切り分け。解除だけ拾っていた | ✅ 標準。追加した |
| **G-10** | アプリ単位のセッション一覧 | 障害時にどのアプリで何人繋がっているかを見る | ✅ 標準。追加した |
| **G-12** | サーバ情報（版数・有効な機能） | 版上げの前後確認 | ✅ 標準。追加した |
| **G-11** | 同意した先の確認・取り消し（本人） | 同意画面を使わない運用なら不要 | ✅ 標準。追加した |
| **G-9** | **なりすまし（調査用）** | サポートが利用者の見え方を再現する | ⛔ **不要で決定**（2026-09-09）。権限を配るときにこの操作を落とす |
| **G-13** | **最終ログイン日時の取得** | **Keycloak はユーザの最終ログイン日時を持たない**。自動停止の判定にもアプリの画面表示にも要る | 🔺 標準外 |
| **G-14** | パスワードの変更日・期限の残り | 「あと何日で期限」を出す標準の手段が無い | 🔺 標準外 |
| **G-15** | 一括の有効化・無効化 | 標準は 1 件ずつ。**大量の停止は件数分の呼び出しになる** | 🔻 **必要だが削減候補**（2026-09-09）。行として追加した |

### この逆点検で分かった、より重要なこと

1. **抜けの多くは「アプリが使う機能」ではなく「事故対応・問い合わせ対応・運用」の API だった。** 機能から積み上げると、この層が落ちる。**顧客に約束する対応時間（SLA）を満たせるかは、この層の API が揃っているかで決まる**
2. **G-7（失効の一斉通知）は設計側にはあったのに API の表に無かった。** 設計書と API 表の突き合わせを一度やる必要がある
3. **G-13（最終ログイン日時）は Keycloak の構造上の欠落で、回避できない。** 自動停止（A-5 で削減候補にした SCIM とは別）の前提なので、**自動停止をやるなら拡張が必ず要る**
4. **標準外（追加コスト）は 14 → 16 件に増えた。** 増えた 2 件は最終ログイン日時とパスワード期限。一括操作（G-15）は新しい行ではなく、既存のバッチ側で吸収する

### 逆点検からの決定（2026-09-09）

| # | 決定 | 反映 |
|---|---|---|
| **G-9 なりすまし** | **不要**。標準にあるが使わない | 区分を ⛔ にした。**権限を配るときに、この操作を許さないことを明示する**（Admin Permissions の設定で落とす）。落とし忘れると「サポートが誰にでもなれる」状態が残るため、**設定の確認をセキュリティ試験の項目に入れる** |
| **G-15 一括の有効化・無効化** | **必要。ただし削減候補** | 行を追加し 🔻 を付けた。標準は 1 件ずつのため件数分の呼び出しになる。**数万人規模の停止が時間内に終わるかは性能試験で確かめる** |
| **G-2 監視の口** | **ROSA のあるアカウントでそれぞれ行う** | Broker 用・Keycloak-IdP 用の各アカウント内で完結し、**他組織が管理する境界は通さない**。境界側への要求事項が 1 つ減る |

**G-2 の決定に伴う確認**: Keycloak-IdP 側の監視はアプリチームの担当になる（本基盤は ROSA の引き渡しまで）。**引き渡しの範囲に「9000 番の有効化と、そこから先の監視の作り」を含めるか**を、責任分界の表（D-21）で決める。

### まだ確認できていないこと

- **一括操作の性能**（G-15）: 数万人規模の停止を 1 件ずつ呼んで間に合うか。**性能試験の項目に入れる**

## 4x. 判断が要る論点（当初版・記録）

| # | 論点 | 選択肢 | 推奨 |
|---|---|---|---|
| **A-1** | **パスワードの変更（本人）**をどう出すか | ① Keycloak の画面へ誘導する（変更を求める印を立て、次のログインで変更させる）／ ② 管理 API で設定する（**今のパスワードを確認しない**ので、アプリ側で本人確認をしてから呼ぶ）／ ③ 変更用の API を自分たちで作る | **①**。作るものが無く、パスワード規則の判定も Keycloak が行う。アプリは「変更画面へ送る」だけでよい |
| **A-2** | **パスワードの取得**の代わりに何を出すか | 用途による。「本人か確かめたい」なら ログイン画面へ誘導 ／「初期パスワードを配りたい」なら 管理 API で一時パスワードを設定 | **用途を伺ってから決める**。取得そのものは出せないと伝える |
| **A-3** | **管理 API をアプリへ渡すか** | ① 渡さない（本基盤が前段の API を作る＝当初の idm-api 案）／ ② 渡すが権限を絞る（Keycloak 26.2 以降の Admin Permissions で顧客・ユーザ単位に限定）／ ③ そのまま渡す | **②**。作るものを大幅に減らせる。ただし **サービスアカウントでの絞り込みは実機確認が要る**（[V1 時代に効かない報告あり](https://forum.keycloak.org/t/does-fine-grained-admin-permissions-work-with-service-accounts/22088)）。ここは PoC 項目に立てる |
| **A-4** | **管理 API の経路** | 現行の取り決め（[禁則 K-10](../09-operations-observability-design.md)）は「管理 API は内部経路のみ」。アプリへ渡すなら、この取り決めを見直すか、内部経路の中でアプリに開くかを決める | **内部経路の中で開く**。インターネットには出さない |
| **A-5** | **SCIM 受信をやるか** | ① やらない（初回ログインで作る方式だけにする）／ ② 作る／ ③ 外部の実装を持ち込む | **顧客の要望次第**。やらない判断ができれば、まとまった工数が消える |
| **A-6** | **振り分け（HRD）をどこまでやるか** | ① メールのドメインで振り分ける（**標準**）／ ② 識別子（顧客コード）で振り分ける（**拡張が要る**） | **顧客の識別子の形を確認してから**。① で足りるなら拡張が 1 つ減る |
| **A-7** | **招待・パスワード再設定のメール前提** | 標準の招待と再設定はメール送信が前提。メールを持たないユーザには使えない | **メール以外の配り方**を決める（管理者が直接渡す等） |

## 5. 既存の決定への影響

| 文書 | 現状 | この方針でどうなるか |
|---|---|---|
| [U10 §10.2 idm-api](../10-integration-migration-design.md) / [ADR-062](../../adr/062-idm-api-execution-form-lambda.md) | ユーザ管理 API を自前で作る（単一の OpenAPI、Lambda で提供） | **A-3 が ② なら、大部分が不要になる**。残るのは Keycloak に無い機能（射影・権限まわり）だけ。**ここが今回いちばん効く圧縮** |
| [禁則 K-10](../09-operations-observability-design.md) | 管理 API は内部経路のみ | A-4 の判断で書き換える |
| 要件 FR-INT-006 / F-INT-14 | 管理 API の内部公開 | 提供する API の一覧と、呼び出し元ごとの許す操作の表に置き換える |
| 要件マッピング | 機能 → 工程 | **機能 → API の列を足す**か、本表を別シートで持つ |
| [ADR-025 SCIM](../../adr/025-scim-positioning-and-receive-stance.md) | SCIM 受信を作る前提 | A-5 の判断次第で対象外にできる |

## 6. 出典

- Keycloak Admin REST API リファレンス: <https://www.keycloak.org/docs-api/latest/rest-api/index.html>
- Account REST API にパスワード変更が無いこと（ソース）: <https://github.com/keycloak/keycloak/blob/main/services/src/main/java/org/keycloak/services/resources/account/AccountCredentialResource.java>
- Admin Permissions（FGAP v2、26.2 で標準機能化）: <https://www.keycloak.org/2025/05/fgap-kc-26-2>
- Organizations に対する権限の絞り込み: <https://www.keycloak.org/2026/05/org-fgap>
''')

print(f'{len(out)} 行 / Broker {sum(1 for o in out if o["対象"]=="Broker")} / IdP {sum(1 for o in out if o["対象"]=="IdP")}')
print('区分:', dict(cnt))
print('機能ID がマスタに無い:', sorted(covered - set(FUNC) - {'(なし)'}) or 'なし')
print(f'表で扱う機能 {len(covered - {"(なし)"})} / 理由付きで除外 {len(rest)} / 理由なし {unexplained or "なし"}')
