# PoC 検証結果サマリー（Phase 1〜5）

**最終更新**: 2026-03-18

---

## 1. 検証目的と達成状況

| 目的 | 達成 | Phase |
|------|:---:|-------|
| Cognito ハイブリッド構成の実現性検証 | ✅ | 1-4 |
| OIDC フェデレーション認証の動作確認 | ✅ | 2 |
| Lambda Authorizer による JWT検証 | ✅ | 3 |
| マルチissuer対応の動作確認 | ✅ | 4 |
| 認証フローの可視化 | ✅ | 1-4 |
| マルチリージョンDR検証 | ✅ | 5 |

---

## 2. 検証シナリオと結果

### 認証（5パターン）

| パターン | ログイン | JWT取得 | issuerType |
|---------|:---:|:---:|:---:|
| Hosted UI（集約Cognito） | ✅ | ✅ | central |
| Auth0 フェデレーション（集約） | ✅ | ✅ | central |
| ローカルCognito | ✅ | ✅ | local |
| DR Hosted UI（大阪） | ✅ | ✅ | dr |
| DR Auth0 フェデレーション（大阪） | ✅ | ✅ | dr |

### 認可

| テスト | 結果 |
|--------|:---:|
| トークンあり → API呼び出し | ✅ 200 OK |
| トークンなし → API呼び出し | ✅ 401 Unauthorized |
| 集約Cognitoトークン → issuerType=central | ✅ |
| ローカルCognitoトークン → issuerType=local | ✅ |
| DR Cognitoトークン → issuerType=dr | ✅ |

### ログアウト

| テスト | 結果 |
|--------|:---:|
| 通常ログアウト（集約） | ✅ |
| 通常ログアウト（ローカル） | ✅ |
| 通常ログアウト（DR） | ✅ |
| 完全ログアウト SSO破棄（集約+Auth0） | ✅ |
| 完全ログアウト SSO破棄（DR+Auth0） | ✅ |
| SSO動作確認（ログアウト後再ログインでパスワード不要） | ✅ |

### DR

| テスト | 結果 |
|--------|:---:|
| 大阪Cognito作成 | ✅ |
| 大阪Auth0フェデレーション | ✅（コンソール手動作成） |
| 大阪JWTでAPI認可 | ✅ |
| 東京→大阪切替時のSSO維持 | ✅ |

---

## 3. 技術的知見

### Cognito 固有

| 知見 | 詳細 | 対応 |
|------|------|------|
| アクセストークンに`aud`がない | `client_id`クレームが代わり | PyJWTの`verify_aud`オフ + 手動検証 |
| フェデレーションでUser Pool内にユーザー作成 | JITプロビジョニング | MAU課金（$0.015/MAU）が発生 |
| Hosted UIログアウトは外部IdPセッション非破棄 | SSO仕様 | 完全ログアウトは多段リダイレクト |
| 大阪から Auth0 の .well-known 自動検出失敗 | 原因不明（Entra IDでは発生しない可能性） | コンソール Manual input で回避 |

### Lambda / ビルド

| 知見 | 詳細 | 対応 |
|------|------|------|
| cryptographyバイナリの互換性 | macOSビルドはLambda(Linux)で動かない | `--platform manylinux2014_x86_64` |
| venv 使用推奨 | システムpipの問題回避 | `build.sh` でvenv自動作成 |

### SPA / oidc-client-ts

| 知見 | 詳細 | 対応 |
|------|------|------|
| UserManagerインスタンス共有必須 | CallbackPageで別インスタンスを作るとイベント不達 | Context経由で共有 |
| マルチUserManagerのstateStore衝突 | 同じsessionStorageキーでstate消費競合 | プレフィックス分離（oidc.central./local./dr.） |
| ログアウト先の動的切替 | ログイン元のCognitoに合わせる必要 | JWTのissクレームでgetUserType()判定 |
| Auth0 Allowed Logout URLsの完全一致 | URLエンコード済みの形で登録必要 | returnToパラメータと同一文字列で登録 |

---

## 4. 本番適用に向けた残課題

| カテゴリ | 課題 | 優先度 |
|---------|------|--------|
| 認証 | Entra ID / Okta での実地検証 | 高 |
| 認証 | Pre Token Lambda（テナント識別グループ付与） | 高 |
| 認証 | クレームマッピング（IdP属性→カスタム属性） | 高 |
| 認可 | グループベース認可ルール実装 | 高 |
| 認可 | テナントスコープ検証 | 中 |
| DR | Route 53 フェイルオーバー（自動切替） | 中 |
| DR | 大阪Cognito+Entra IDの接続検証 | 中 |
| 比較 | Keycloak構成の構築・比較（Phase 6） | 中 |
| コスト | 顧客のMAU規模確認（損益分岐点17.5万MAU） | 高 |

---

## 5. 次のPhase

| Phase | 内容 | 目的 |
|-------|------|------|
| 6 | Keycloak構成（第2パターン） | Cognitoとの運用負荷・コスト比較 |
