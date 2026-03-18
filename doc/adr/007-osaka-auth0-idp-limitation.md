# ADR-007: 大阪リージョンでAuth0 OIDC IdP接続不可の記録

**ステータス**: Accepted
**日付**: 2026-03-18

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

## 決定

- DR検証はAuth0なし（Hosted UIローカルユーザー）で実施
- フェデレーションのDR検証は本番環境（Entra ID）で実施する

## 本番への影響

**影響は限定的と判断:**
- 本番で使用するEntra IDはMicrosoftのグローバルインフラであり、AWS全リージョンから到達可能
- Auth0 FreeはUSリージョンのみにホストされるため、大阪からの接続に制限がある可能性
- Entra IDのDiscovery URL（`login.microsoftonline.com`）はCDN配信されており、リージョン依存性が低い

## 要確認事項

- 本番構築時にEntra IDで大阪リージョンのCognito IdP作成が成功するか検証
- 失敗した場合はAWSサポートに問い合わせ
