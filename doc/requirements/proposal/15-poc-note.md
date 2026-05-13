# §15 参考：弊社内の事前検証について

> 上位 SSOT: [00-index.md](00-index.md)
> 内部資料: [../poc-summary-evaluation.md](../poc-summary-evaluation.md)
> ステータス: 📋 骨格のみ

---

## 15.1 事前検証の位置づけ

本提案は、事前に **弊社内で技術検証（PoC）を実施した結果に基づく**。Cognito / Keycloak それぞれで認証・認可・DR・マルチ IdP・VPC 完全プライベート JWKS まで検証済み。

検証内容の詳細結果が必要な場合は、別途共有可能。

## 15.2 検証範囲（概要）

| 検証カテゴリ | Cognito | Keycloak |
|---|:---:|:---:|
| 基本認証フロー（OIDC / PKCE / Hosted UI） | ✅ | ✅ |
| 認可（JWT クレーム / Lambda Authorizer） | ✅ | ✅ |
| マルチ IdP / フェデレーション（Auth0） | ✅ | ✅ |
| DR / マルチリージョン | ✅（手動切替） | （Aurora Global DB は本番フェーズ） |
| MFA / SSO / Auth0 Brokering | ✅ | ✅ |
| クレームマッピング / マルチテナント認可 | ✅（Phase 8） | ✅（Phase 9） |
| VPC 完全プライベート JWKS | — | ✅（Phase 9） |

詳細: [../poc-summary-evaluation.md](../poc-summary-evaluation.md)

## 15.3 PoC で実施していない / 本番フェーズで実施する事項

- Entra ID / Okta での実地検証（PoC は Auth0 で代替）
- Route 53 自動フェイルオーバー
- 大規模負荷試験
- 商用サポート（RHBK）の運用評価

詳細: [../poc-summary-evaluation.md §残課題](../poc-summary-evaluation.md)
