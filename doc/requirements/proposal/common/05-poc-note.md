# §C-5 参考：弊社内の事前検証について

> 上位 SSOT: [00-index.md](00-index.md)
> 内部資料: [../../poc-summary-evaluation.md](../../poc-summary-evaluation.md)
> 位置付け: **顧客向けには控えめ提示**（PoC 報告書ではない）。詳細は内部資料に委譲。

---

## §C-5.0 本章の位置づけ

本提案は **弊社内で事前に技術検証（PoC）を実施した結果に基づく**ため、要件提示の各ベースラインには PoC で実証済みの裏付けがある。

ただし本資料は **要件提示版**であり PoC 報告書ではないため、本章は概要のみ提示する。詳細な検証結果が必要な場合は内部資料を共有可能。

---

## §C-5.1 PoC 実施範囲（概要）

**目的**: Cognito / Keycloak 両方で「共通認証基盤」が構築可能であることの実証。

| 検証カテゴリ | Cognito | Keycloak |
|---|:---:|:---:|
| 基本認証フロー（OIDC / PKCE / Hosted UI） | ✅ | ✅ |
| 認可（JWT クレーム / Lambda Authorizer） | ✅ | ✅ |
| マルチ IdP / フェデレーション（Auth0） | ✅ | ✅ |
| DR / マルチリージョン | ✅（手動切替） | （Aurora Global DB は本番フェーズ） |
| MFA / SSO / Auth0 Brokering | ✅ | ✅ |
| クレームマッピング / マルチテナント認可 | ✅ | ✅ |
| VPC 完全プライベート JWKS | — | ✅ |

詳細: [../../poc-summary-evaluation.md](../../poc-summary-evaluation.md)

---

## §C-5.2 PoC で実施していない / 本番フェーズで実施する事項

本資料の要件提示は PoC 実証範囲を超える領域も含む。これらは本番フェーズで個別に検証・対応する:

- **Entra ID / Okta での実地検証**（PoC は Auth0 を代替 IdP として実施）
- **Route 53 自動フェイルオーバー**（PoC は手動切替で代替検証）
- **大規模負荷試験**（10K MAU 超のシナリオ）
- **商用サポート（RHBK）の運用評価**
- **既存基盤からの移行検証**（顧客固有のため要件確定後）

詳細: [../../poc-summary-evaluation.md](../../poc-summary-evaluation.md)

---

## §C-5.3 PoC が要件提示に与える信頼度

| 領域 | 信頼度 | 根拠 |
|---|:---:|---|
| 基本機能（認証 / 認可 / SSO / MFA / フェデ）| **高** | Cognito / Keycloak 両方で実証 |
| 性能（Lambda Authorizer < 60ms 等）| 中〜高 | PoC 実測値ベース、本番規模での再計測必要 |
| マルチテナント運用 / クレームマッピング | **高** | Phase 8（Cognito）/ Phase 9（Keycloak）で実証 |
| VPC ネットワーク設計（プライベート JWKS）| **高** | Phase 9 で実証 |
| DR 自動フェイルオーバー | 中 | 手動切替まで実証、自動化は本番フェーズ |
| 大規模負荷 / 損益分岐 | 中 | 業界ベンチマーク + 試算ベース |

---

## §C-5.4 内部資料への参照

詳細な PoC 成果・既存ドキュメント評価・不足箇所分析は内部資料に集約:

- [../../poc-summary-evaluation.md](../../poc-summary-evaluation.md): PoC 総括評価
- [../../platform-selection-decision.md](../../platform-selection-decision.md): プラットフォーム選定の評価フレーム
- [../../../adr/](../../../adr/): 各種設計判断（ADR-006 / 010 / 011 / 012 / 013 / 014 / 015 等）
