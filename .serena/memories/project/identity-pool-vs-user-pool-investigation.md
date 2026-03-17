# Identity Pool vs User Pool 調査結果（2026-03-17）

## 背景
ユーザーが「共通基盤はIdentity Poolで認証、User Poolは各アカウントのローカルユーザー用」という理解を持っていた。調査の結果、User Poolが正しい選択であると確認。

## 結論
- Identity Pool は JWT を発行しない（AWS STS 認証情報のみ）
- API Gateway + Lambda Authorizer パターンには User Pool が必須
- OIDC フェデレーション、クレームマッピング、Pre Token Lambda はすべて User Pool の機能
- Identity Pool はSPAからS3直接アクセス等の場合にのみ必要

## 現在のTerraform構成（User Pool）は正しい

## ドキュメントへの反映
- doc/old/ のドキュメントでは「User Pool」「Identity Pool」の区別が不明確
- 今後の設計ドキュメントでは明示的に区別する
