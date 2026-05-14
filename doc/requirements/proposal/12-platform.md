# §12 実装プラットフォーム

> 上位 SSOT: [00-index.md](00-index.md)
> 詳細: [../platform-selection-decision.md](../platform-selection-decision.md)、[../../adr/006-cognito-vs-keycloak-cost-breakeven.md](../../adr/006-cognito-vs-keycloak-cost-breakeven.md)、[../../adr/014-auth-patterns-scope.md](../../adr/014-auth-patterns-scope.md)、[../../adr/015-rhbk-validation-deferred.md](../../adr/015-rhbk-validation-deferred.md)
> ステータス: 📋 骨格のみ

---

## 12.1 候補プラットフォーム

| 観点 | AWS Cognito | Keycloak OSS | Keycloak RHBK |
|---|---|---|---|
| 性質 | マネージドサービス | OSS（自己ホスト） | OSS + Red Hat 商用サポート |
| 運用負荷 | 低 | 中〜高 | 中（Red Hat サポート） |
| 自由度 | 中 | 高 | 高 |
| 商用サポート | AWS Support | コミュニティ（ベストエフォート）| Red Hat 24/7 |
| 損益分岐 | 〜17.5 万 MAU | 大規模・特殊要件 | FIPS / 24/7 サポート必須時 |

## 12.2 選定論点

選定に関わる必須要件:
- [§2.1 認証フロー](02-auth.md#21-認証フロー--grant-type-fr-auth-11) - Token Exchange / Device Code / mTLS が Must → Keycloak 必須
- [§3.1 IdP 接続](03-federation.md#31-idp-接続種別-fr-fed-21) - SAML IdP 発行 / LDAP 直連携が Must → Keycloak 必須
- [§13.7 コンプライアンス](13-nfr.md#137-コンプライアンス-nfr-comp) - FIPS 140-2 が Must → RHBK 必須
- [§2.2 パスワード](02-auth.md#22-パスワードローカルユーザー管理-fr-auth-12) - 24/7 サポート必須 → Cognito / RHBK
- [§13.8 コスト](13-nfr.md#138-コスト-nfr-cost) - MAU 規模次第で損益分岐
- [§6 ログアウト・セッション管理](06-logout-session.md) - Back-Channel Logout / Access Token Revocation が Must → Keycloak 必須

## 12.3 TBD / 要確認

- MAU 規模（1 年後 / 3 年後）
- 商用サポート要否（24/7 / 営業時間 / 不要）
- 既存 AWS 利用状況
- FIPS 等のコンプライアンス要件
