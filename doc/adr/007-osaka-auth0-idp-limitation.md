# ADR-007: 大阪リージョンでAuth0 OIDC IdP接続不可の記録

**ステータス**: Accepted
**日付**: 2026-03-18
**最終更新**: 2026-05-13（手動 endpoint workaround による Terraform 化を追記）

## コンテキスト

Phase 5 のDR検証で、大阪リージョン（ap-northeast-3）のCognito User PoolにAuth0をOIDC IdPとして追加しようとしたところ、`Unable to contact well-known endpoint` エラーで作成できなかった。

## 調査結果

- Auth0のDiscoveryエンドポイント（`/.well-known/openid-configuration`）はローカルからは正常にアクセス可能
- 東京リージョン（ap-northeast-1）では同じ設定でAuth0 IdP作成に成功
- 末尾スラッシュの有無、`attributes_request_method`（GET/POST）を変更しても解消せず
- AWS公式ドキュメントには大阪リージョン固有のOIDC IdP制限は記載なし

## 推定原因

- 大阪リージョンのCognitoからAuth0（US リージョン）への外部HTTPS接続に問題がある可能性
- AWS内部のネットワーク経路の問題（大阪→USのレイテンシまたはタイムアウト）
- Auth0 Free プランの地理的制限の可能性

## 決定（初期 2026-03-18）

- DR検証はAuth0なし（Hosted UIローカルユーザー）で実施
- フェデレーションのDR検証は本番環境（Entra ID）で実施する

## 更新（2026-04 以降の workaround）

その後の検証で、**`.well-known` 自動検出はバイパス可能**であることが判明:

- Cognito IdP 作成時、コンソールの **「Manual input」モード** または Terraform で `authorize_url` / `token_url` / `attributes_url` / `jwks_uri` を**手動指定**すれば、`.well-known` 取得失敗を回避できる
- 現在の [infra/dr-osaka/cognito.tf:109-138](../../infra/dr-osaka/cognito.tf) では完全に Terraform 管理化されている（コンソール手動作成 → `terraform import` ではなく、Terraform から直接作成可能）
- `lifecycle { ignore_changes = [provider_details] }` で再作成を防ぐ
- 結果として、**DR Cognito + Auth0 フェデレーションも検証範囲に含まれ、Phase 5 で動作確認済**（[poc-results.md §2 認証 5 パターン](../common/poc-results.md)「DR Auth0 フェデレーション ✅」）

## 本番への影響（更新版）

- **大阪リージョン Cognito の OIDC IdP 作成は技術的に可能**（手動 endpoint 指定が前提）
- Entra ID 本番接続時も同様に、`.well-known` 自動検出が失敗した場合は手動 endpoint で対応可
- ただし、設定変更時の運用負荷（手動 endpoint URL の管理）が増えることに留意

## 要確認事項

- 本番構築時にEntra IDで大阪リージョンのCognito IdP作成が `.well-known` 自動検出で成功するか確認（Auth0 と挙動が異なる可能性あり）
- 自動検出が失敗した場合も、手動 endpoint 指定で同等構成が可能であることは確認済

## 本番への影響

**影響は限定的と判断:**
- 本番で使用するEntra IDはMicrosoftのグローバルインフラであり、AWS全リージョンから到達可能
- Auth0 FreeはUSリージョンのみにホストされるため、大阪からの接続に制限がある可能性
- Entra IDのDiscovery URL（`login.microsoftonline.com`）はCDN配信されており、リージョン依存性が低い

## 要確認事項

