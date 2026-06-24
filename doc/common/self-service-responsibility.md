# セルフサービスの責任配置 — 浅いブローカー設計での割切り

> **位置付け**: 本基盤が「**浅いブローカー**（認証は顧客 IdP に集約、broker は OIDC リレー層）」を採用した結果として、パスワード変更・MFA 登録・プロフィール編集などのセルフサービス機能を broker 側で **どこまで持つか / 出すべきでないか** を 9 機能 × 5 ユーザー種別で棚卸ししたリファレンス。
>
> **対象読者**: 認証基盤設計者 / 顧客 PoC 担当 / 営業 / セキュリティレビュー担当 / 提案資料 (PowerPoint) 作成者
>
> **関連**:
> - [user-types-and-auth.md](user-types-and-auth.md) — 5 ユーザー種別と認証方式
> - [identity-broker-multi-idp.md](identity-broker-multi-idp.md) — Identity Broker パターン
> - [ADR-009 MFA 責任の集約](../adr/009-mfa-responsibility-by-idp.md) — MFA は認証主体（パスワード保管側）が提供する原則
> - [§FR-7 ユーザー管理](../requirements/proposal/fr/07-user.md) — セルフサービス要件

---

## 目次

0. [章共通の前提：ユーザー種別 × 3 章責任マッピング](#0-章共通の前提ユーザー種別--3-章責任マッピング)
1. [結論サマリー](#1-結論サマリー)
2. [前提：浅いブローカーとは](#2-前提浅いブローカーとは)
3. [セルフサービス機能 9 種類の棚卸し](#3-セルフサービス機能-9-種類の棚卸し)
4. [Broker 側に残る 3 つの中身](#4-broker-側に残る-3-つの中身)
5. [ユーザータイプ別の責任マトリクス](#5-ユーザータイプ別の責任マトリクス)
6. [アンチパターン](#6-アンチパターン)
7. [Keycloak での実装上の打ち手](#7-keycloak-での実装上の打ち手)
8. [PowerPoint 構成案](#8-powerpoint-構成案)
9. [顧客説明 30 秒メッセージ](#9-顧客説明-30-秒メッセージ)

---

## 0. 章共通の前提：ユーザー種別 × 3 章責任マッピング

**ユーザー管理（CRUD）/ プロビジョニング / セルフサービス** の 3 章は、どれも「**誰のために誰が何をするか**」を割り当てる議論です。最初に「誰がいるのか」と「その認証ソースは何か」を揃えておかないと、3 章すべてで「今のは end user の話？運用者の話？」という質疑が混入します。

そこで本ドキュメント（およびその親テーマであるユーザー管理・プロビジョニング・セルフサービス章）は、以下の **5 ユーザー種別 × 3 観点 + 認証ソース** のマッピング表を **章共通の前提合意スライド** として最初に提示します。

| ユーザー種別 | 認証ソース | 管理（CRUD）責任 | プロビジョニング方式 | セルフサービス提供場所 |
|---|---|---|---|---|
| **Platform Admin** | Broker (ローカル) | 基盤運用チーム | 手動（Admin Console / kcadm.sh）| Broker |
| **Tenant Admin (IdP 無)** | Broker (ローカル) | 基盤運用 or 顧客側 | 手動 or 簡易招待 | Broker |
| **Tenant Admin (IdP 有)** | 顧客 IdP | 顧客 IdP 管理者 | JIT + ロール手動付与 | **顧客 IdP** |
| **End User (連携)** | 顧客 IdP | 顧客 IdP 管理者 | JIT (or 将来 SCIM) | **顧客 IdP** |
| **End User (ローカル)** | Broker (ローカル) | 顧客 Tenant Admin | 手動招待 or セルフ登録 | Broker |

→ ユーザー種別は [user-types-and-auth.md](user-types-and-auth.md) の 5 カテゴリと一致。認証ソース行が "Broker (ローカル)" のユーザーは broker が全責任、"顧客 IdP" のユーザーは認証関連は顧客 IdP に集約（[ADR-009 MFA 責任原則](../adr/009-mfa-responsibility-by-idp.md) の一般化）。

### この表が章の 3 観点をどう統合するか

| 章 | この表のどこを見るか | 詳細 |
|---|---|---|
| **ユーザー管理（CRUD）** | 3 列目「管理責任」 | Broker (ローカル) ユーザーは基盤運用 or 顧客側、IdP 連携ユーザーは顧客 IdP 管理者 |
| **プロビジョニング** | 4 列目「プロビジョニング方式」 | 連携 = JIT or SCIM、ローカル = 手動招待 or セルフ登録 |
| **セルフサービス** | 5 列目「提供場所」 | 連携 = 顧客 IdP、ローカル = Broker（[§3](#3-セルフサービス機能-9-種類の棚卸し) で詳細棚卸し） |

### 顧客との前提合意のしかた

このマッピング表は **顧客との初回擦り合わせで「この 5 種別と認証ソースで合っていますか」を確認する** ために使うのが本来の用途です。例えば顧客から:

- 「うちは End User Fed しかいない」→ Broker (ローカル) 行を deck から削除して議論をシンプル化
- 「Tenant Admin に IdP 無は想定してない」→ Tenant Admin (IdP 無) 行を削除、運用者は全員 Platform Admin として整理
- 「IdP を持たないが SSO は別途設計する」→ Tenant Admin / End User (ローカル) は本基盤で持たないとして外す

…と言われた場合、後続の管理・プロビジョニング・セルフサービス章の議論範囲が **章を跨いで一貫して縮小** し、深掘り時間を要件に直結する部分に集中投下できます。

---

## 1. 結論サマリー

| 観点 | 判断 |
|---|---|
| **本方針の核心** | 「**認証情報を保持する側がセルフサービスを提供する責務**」（[ADR-009](../adr/009-mfa-responsibility-by-idp.md) の MFA 帰属原則の一般化）|
| **連携ユーザー（顧客 IdP 経由）に対する broker 側セルフサービス** | **原則ゼロ**（アカウント設定画面 無効化が正解） |
| **Broker 側に残る例外** | 3 つだけ：①ローカルユーザー向け / ②broker セッション管理 / ③GDPR 対応 |
| **設計判断のキーポイント** | アカウント設定画面 は Realm 単位で制御可能。連携ユーザーには Account Portal をリダイレクト or 隠蔽する |

→ 「**浅いブローカー = broker 側は薄く保つ**」設計の自然な帰結。本来 IdP 側の責務を broker 側に再実装するのは**アンチパターン**。

---

## 2. 前提：浅いブローカーとは

「浅いブローカー」は、本基盤が採用するレイヤ深度のスペクトルにおける位置:

| レベル | broker が保有する範囲 | 本基盤 |
|---|---|---|
| L1: 完全リレー | 認証情報も属性も保持しない、URL リダイレクトのみ | ❌ |
| **L2: 浅いブローカー（本採用）** | JIT で user 行を作成、`tenant_id`/`roles` だけ broker が管理。認証情報・MFA・プロフィールは IdP 側 | ✅ |
| L3: 中間ブローカー | broker が独自の属性スキーマを保持、IdP と同期 | ❌ |
| L4: プライマリ IdP | broker がプライマリのアイデンティティストア、外部 IdP は補助 | ❌（ローカルユーザー専用領域として一部 L4） |

→ 本基盤は L2 を採用。Broker は **認可境界（`tenant_id`、ロール）の保持**だけが責務であり、**認証クレデンシャル・MFA・個人プロフィール**は IdP 側が authoritative。

> **「浅いブローカーは具体的に何を保持し、何を持たないか」** の Keycloak DB スキーマレベルの完全リストは [broker-data-model.md](broker-data-model.md) を参照（7 カテゴリ + 持たないもの対比 + JWT クレームへの反映 + ER 図）。

---

## 3. セルフサービス機能 9 種類の棚卸し

連携ユーザー（顧客 IdP 経由ログイン）視点で各機能の所在を整理:

| # | 機能 | 浅いブローカー時の所在 | Broker (Keycloak) 側で UI 提供 | 理由 |
|---|---|---|:---:|---|
| 1 | パスワード変更・リセット | 顧客 IdP | ❌ 不要 | broker は password を保管しない |
| 2 | MFA 登録・解除（TOTP/WebAuthn/SMS） | 顧客 IdP | ❌ 不要 | MFA 責任は認証主体に帰属（[ADR-009](../adr/009-mfa-responsibility-by-idp.md)）|
| 3 | プロフィール編集（氏名・電話） | 顧客 IdP | ❌ 不要 | JIT で次回ログイン時に再同期 |
| 4 | メールアドレス変更 | 顧客 IdP | ❌ 不要 | 顧客 IdP が authoritative |
| 5 | メール検証 (verify email) | 顧客 IdP | ❌ 不要 | IdP 側で済んでから連携される |
| 6 | リカバリーコード / バックアップコード | 顧客 IdP | ❌ 不要 | broker は認証クレデンシャルなし |
| 7 | **Broker 側セッション管理**（"このアプリ群でログイン中" 表示・強制ログアウト） | Broker | 🟡 **任意・有用** | IdP セッションとは別の "broker session" が存在するため、可視化・破棄手段はあると親切 |
| 8 | リンクされた IdP の管理（複数 IdP 接続時） | Broker | 🟡 **複数 IdP 受容時のみ** | 通常 1 顧客 = 1 IdP なら不要 |
| 9 | **アカウント削除・データエクスポート (GDPR)** | Broker + IdP | 🟡 **broker 分は必須** | broker DB に残るデータ（federated link、last login、role、tenant_id）の取扱責任が残る |

---

## 4. Broker 側に残る 3 つの中身

### ① 基盤運用者・テナント管理者向けセルフサービス

これは「浅いブローカー」の対象外ユーザー領域:

| ユーザー | 認証主体 | 必要セルフサービス |
|---|---|---|
| Platform Admin（基盤運用チーム） | Broker (ローカル) | パスワード変更、MFA 登録（TOTP/WebAuthn）、プロフィール編集 |
| Tenant Admin（IdP を持たない顧客の管理者）| Broker (ローカル) | 同上 |
| End User（ローカル）— SMB 顧客が IdP 持たない場合 | Broker (ローカル) | 同上 |

→ これらは federated ではないので **通常の Keycloak アカウント設定画面 をそのまま使う**。

### ② Broker 側セッション管理

連携ユーザーであっても broker のセッション (`KEYCLOAK_SESSION` cookie) は実在:

```
[顧客 IdP] ── 認証成功 ──→ [Broker (Keycloak)]
                              │
                              └─→ KEYCLOAK_SESSION cookie 発行
                                  ↓
                              [接続アプリ群] とのアプリセッション
```

提供する価値:
- IdP 側ログアウトしても broker セッションが残ると SSO が誤動作する場合がある
- ユーザー視点で「どこにログインしているか」を可視化する価値あり
- Keycloak アカウント設定画面 の **"Devices" タブ**で対応可能

→ **アカウント設定画面 は Devices タブだけ ON、他は OFF** が現実解。

### ③ GDPR データ開示・アカウント削除

法的責任。連携ユーザーであっても broker は以下を持つ:
- `federated_identity` テーブル（IdP との紐付け）
- `tenant_id` / `roles` 属性
- `events` テーブル（ログイン履歴）
- `user_session` テーブル
- `last_login` 等のメタデータ

GDPR Article 15 (Right of Access) / Article 17 (Right to Erasure) 対応:

| 要件 | broker 側の対応 |
|---|---|
| データ開示 | Admin API で当該ユーザーの全データを export → 提供 |
| データ削除 | Admin API で user 削除（federated_identity も連動削除） |
| ポータビリティ | JSON 等で機械可読出力 |

→ Keycloak 標準には GDPR ボタンは存在しないので、**運用フロー**で対応（ヘルプデスク → Admin API）。SLA で「依頼から 30 日以内」等を明示。

---

## 5. ユーザータイプ別の責任マトリクス

[user-types-and-auth.md](user-types-and-auth.md) の 5 ユーザー種別に当てはめると:

| ユーザー種別 | 認証主体 | パスワード/MFA セルフサービス | プロフィール編集 | Broker セッション管理 | アカウント設定画面 アクセス |
|---|---|:---:|:---:|:---:|---|
| **Platform Admin**（基盤運用者） | Broker (ローカル) | ✅ Broker | ✅ Broker | ✅ Broker | 全機能 ON |
| **Tenant Admin (IdP 無)** | Broker (ローカル) | ✅ Broker | ✅ Broker | ✅ Broker | 全機能 ON |
| **Tenant Admin (IdP 有)** | 顧客 IdP | ❌ IdP 側 | ❌ IdP 側 | 🟡 任意 | Devices タブのみ ON or 全 OFF |
| **End User (連携)** | 顧客 IdP | ❌ IdP 側 | ❌ IdP 側 | 🟡 任意 | 同上 |
| **End User (ローカル)** | Broker (ローカル) | ✅ Broker | ✅ Broker | ✅ Broker | 全機能 ON |

判断ロジック:
```
if user.is_federated:
    アカウント設定画面 = 隠蔽 or Devices のみ
else:  # ローカルユーザー
    アカウント設定画面 = 標準提供
```

---

## 6. アンチパターン

| やってはいけない | 理由 | 起きる症状 |
|---|---|---|
| 連携ユーザーに broker 側のパスワード変更画面を出す | broker が password を保管していないので「変更」がそもそも成立しない | ユーザーが「パスワード変えたのにログインできない」とサポート問い合わせ |
| 連携ユーザーに broker 側 MFA 登録を求める | 二重 MFA（IdP 側 + broker 側）。[ADR-009](../adr/009-mfa-responsibility-by-idp.md) と矛盾 | ログインに数十秒余分にかかり UX 悪化、運用問い合わせ増 |
| 連携ユーザーが broker 側プロフィールを編集できる | 次回ログインで IdP の値で上書きされる | 「編集したのに戻った」「どこが正なのか分からない」混乱 |
| アカウント設定画面 を realm 横断で一律 ON | 連携 / ローカルが混在し UX 一貫性なし | 連携ユーザーが「変更ボタンがあるのに動かない」を経験 |
| 連携ユーザーに broker 側パスワードリセットメールが届く | broker が SMTP 経由で送信できてしまうが、リセットしてもログインに使われず無意味 | ユーザー混乱、フィッシング誤認の可能性 |
| GDPR 削除依頼を broker 側だけで処理 | 顧客 IdP 側のデータは残る | 法的責任の一部しか果たせない（顧客 IdP 管理者への依頼フロー必須） |

---

## 7. Keycloak での実装上の打ち手

### 7.1 アカウント設定画面 全体無効化（最も単純）

連携ユーザーのみが想定される Realm の場合:
```bash
# kcadm.sh で account client を disable
kcadm.sh update clients/{account-client-uuid} -r auth-poc -s enabled=false
```

→ 全ユーザーが アカウント設定画面 利用不可。ローカルユーザーがいる場合は使えない方法。

### 7.2 アカウント設定画面 機能の選択的 ON/OFF（推奨）

Keycloak Realm Settings → "User Profile" + "Themes" で:
- "Edit username" → OFF
- "Edit email" → OFF（連携ユーザーは IdP 側で管理）
- "Delete account" → ON（GDPR 対応）

Account Theme をカスタマイズして連携ユーザーには「プロフィール編集は社内 IdP の管理画面で行ってください」リンクを表示（顧客 IdP の Account Portal URL）。

### 7.3 連携ユーザーを アカウント設定画面 から除外

Authentication Flow で `Identity Provider` 経由ログインの場合、アカウント設定画面 アクセスを拒否する Custom Authenticator を挟む方法（要 SPI 実装）。

簡易版: Theme template (`account.ftl`) で `federatedIdentities` が存在するユーザーには警告メッセージ + リダイレクトボタンのみ表示。

### 7.4 Devices タブのみ ON

Keycloak v26 では アカウント設定画面 の各セクション（Personal info / Account security / Applications / Linked accounts）は theme でカスタマイズ可能。連携ユーザーには Sessions セクション（= Devices タブ）のみ表示する theme を作成。

### 7.5 GDPR 対応の運用フロー

```
顧客 IdP 管理者 / ユーザー
    │
    ├─ データ開示依頼 → ヘルプデスク
    │       │
    │       └─ kcadm.sh get users/{id} + 関連テーブル export → JSON 提供
    │
    └─ アカウント削除依頼 → ヘルプデスク
            │
            └─ kcadm.sh delete users/{id} → federated_identity 連動削除
                 + 顧客 IdP 側削除を顧客 IdP 管理者に依頼
```

SLA: 依頼受領から 30 日以内（GDPR 要件）。

---

## 8. PowerPoint 構成案

### スライド 1: 「セルフサービスはどこで提供するか」

タイトル: **認証情報を保持する側が提供する責務**

| | パスワード変更 | MFA 登録 | プロフィール編集 | メール変更 | セッション管理 | GDPR 削除 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| 顧客 IdP 提供 | ✅ | ✅ | ✅ | ✅ | ✅（IdP 側）| ✅（IdP 側）|
| Broker 提供 | ❌ | ❌ | ❌ | ❌ | 🟡 任意 | 🟡 broker 分のみ |

メッセージ: **「連携ユーザーには Broker 側セルフサービスは原則出さない」**

### スライド 2: 「Broker 側に残る 3 つだけ」

```
[顧客 IdP] ←──認証クレデンシャル・MFA・プロフィール
                              │
                              ↓
                         認証成功
                              │
                              ↓
[Broker (Keycloak)]
    ├─ ① ローカルユーザー (Platform/Tenant Admin) 向けセルフサービス
    ├─ ② Broker 側セッション管理 (Devices タブ)
    └─ ③ GDPR データ開示・削除 (運用フロー)
```

### スライド 3: 「ユーザー種別ごとの方針」

5 ユーザー種別マトリクス（[§5](#5-ユーザータイプ別の責任マトリクス) の表を slide 用に簡略化）

メッセージ: **「ローカルユーザーには通常通り、連携ユーザーには出さない」**

### スライド 4: 「アンチパターン警告」

| ❌ | やってしまうと |
|---|---|
| 連携ユーザーに broker 側 PW 変更画面を出す | 「変えたのに動かない」サポート問い合わせ |
| 連携ユーザーに broker 側 MFA 登録 | 二重 MFA で UX 悪化 |
| broker 側プロフィール編集を許可 | IdP 同期で上書きされ混乱 |
| アカウント設定画面 を一律 ON | 連携 / ローカル混在で UX 不一致 |

打ち手:
- アカウント設定画面 を Realm 設定で機能別 ON/OFF
- 連携ユーザーには顧客 IdP の Account Portal へリダイレクト

### スライド 5（任意）: 「GDPR 対応の運用」

依頼受領 → ヘルプデスク → kcadm.sh → 30 日以内対応 のフロー図。

---

## 9. 顧客説明 30 秒メッセージ

> 「セルフサービス（パスワード変更・MFA 登録・プロフィール編集）は、**認証情報を保持している側が提供する責務**です。本基盤は浅いブローカー設計なので、認証情報は顧客 IdP に集約しており、broker 側にセルフサービス UI を出すと『顧客 IdP と broker の二重 UI』になり混乱を招きます。
>
> 例外は (1) 顧客 IdP を持たないローカル運用者向け（基盤管理者・小規模顧客の管理者等）(2) ユーザーが broker 側セッションを破棄する手段の提供 (3) GDPR 対応のデータ開示・削除、の **3 つだけ** です。
>
> これは ADR-009 の MFA 責任原則を一般化したもので、本基盤の Identity Broker 設計と整合します。」

---

## 改訂履歴

- 2026-06-08: 初版作成。浅いブローカー設計でのセルフサービス機能棚卸し（9 機能 × 5 ユーザー種別）、broker 側に残る 3 例外、アンチパターン、Keycloak 実装上の打ち手、PowerPoint 構成案を網羅
