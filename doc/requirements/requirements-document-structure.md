# 要件定義資料の構成案

> 最終更新: 2026-04-21
> 目的: 要件定義フェーズで作成すべきドキュメント体系と作成順序の定義

---

## 1. ドキュメント体系の全体像

```
doc/requirements/
├── 00-index.md                          ← 本フォルダのインデックス
│
├── [報告・総括]
│   ├── poc-summary-evaluation.md        ← PoC 総括評価（作成済み）
│   └── poc-presentation.md              ← PoC 報告プレゼン資料（ステークホルダー向け要約）
│
├── [ヒアリング]
│   ├── requirements-hearing-strategy.md ← ヒアリング戦略（作成済み）
│   ├── hearing-phase-a.md               ← Phase A: 事業要件ヒアリング記録
│   ├── hearing-phase-b.md               ← Phase B: 技術要件ヒアリング記録
│   ├── hearing-phase-c.md               ← Phase C: 運用・セキュリティ要件記録
│   └── hearing-phase-d.md               ← Phase D: 最終判断会議記録
│
├── [要件定義書]
│   ├── requirements-spec.md             ← 要件定義書（本体）
│   ├── functional-requirements.md       ← 機能要件一覧
│   ├── non-functional-requirements.md   ← 非機能要件一覧
│   └── platform-selection-decision.md   ← プラットフォーム選定判断書
│
└── [付録]
    ├── migration-strategy.md            ← 移行戦略（既存 → 新基盤）
    └── cost-estimation.md               ← コスト見積もり（詳細版）
```

---

## 2. 各ドキュメントの概要と作成順序

### Phase 1: PoC 報告（Week 1 前半）

| # | ドキュメント | 目的 | ページ数目安 | 状態 |
|---|------------|------|-------------|------|
| 1 | poc-summary-evaluation.md | PoC 成果の総括・不足箇所の特定 | 10-15 | ✅ 作成済み |
| 2 | poc-presentation.md | ステークホルダー向け報告資料 | 5-8 | 📋 作成予定 |

**poc-presentation.md の構成案**:
1. PoC の目的と背景（1 ページ）
2. 検証した認証パターン（2 ページ: 図中心）
3. Cognito vs Keycloak 比較結果（1 ページ: 表）
4. コスト比較（1 ページ: グラフ）
5. 主要な技術的知見（1 ページ）
6. 要件定義で確認すべき事項（1 ページ）
7. 推奨ロードマップ（1 ページ）

### Phase 2: ヒアリング実施（Week 1-3）

| # | ドキュメント | 目的 | 作成タイミング |
|---|------------|------|-------------|
| 3 | requirements-hearing-strategy.md | ヒアリング計画 | ✅ 作成済み |
| 4 | hearing-phase-a.md | 事業要件の確認結果 | Week 1 ヒアリング後 |
| 5 | hearing-phase-b.md | 技術要件の確認結果 | Week 2 ヒアリング後 |
| 6 | hearing-phase-c.md | 運用・セキュリティ要件の確認結果 | Week 3 ヒアリング後 |

### Phase 3: 要件定義書作成（Week 3-4）

| # | ドキュメント | 目的 | 作成タイミング |
|---|------------|------|-------------|
| 7 | requirements-spec.md | 要件定義書（本体） | ヒアリング完了後 |
| 8 | functional-requirements.md | 機能要件の詳細 | 7 と並行 |
| 9 | non-functional-requirements.md | 非機能要件の詳細 | 7 と並行 |
| 10 | platform-selection-decision.md | Cognito / Keycloak 最終判断 | 要件確定後 |

### Phase 4: 付録・補足資料（Week 4-5）

| # | ドキュメント | 目的 | 作成タイミング |
|---|------------|------|-------------|
| 11 | migration-strategy.md | 既存システムからの移行戦略 | 要件確定後 |
| 12 | cost-estimation.md | 詳細コスト見積もり | プラットフォーム確定後 |

---

## 3. 要件定義書（requirements-spec.md）の構成案

要件定義の中核ドキュメント。ヒアリング結果を統合して作成する。

```markdown
# 共有認証基盤 要件定義書

## 1. はじめに
  1.1 文書の目的
  1.2 対象範囲
  1.3 用語定義
  1.4 関連ドキュメント

## 2. ビジネス要件
  2.1 プロジェクトの背景と目的
  2.2 対象システム一覧
  2.3 ステークホルダー
  2.4 ビジネス上の制約（予算・期限・法規制）

## 3. システム概要
  3.1 システム構成図（PoC architecture.md ベース）
  3.2 認証基盤の責任範囲
  3.3 利用システムの責任範囲
  3.4 責任分界点

## 4. 機能要件（→ functional-requirements.md で詳細化）
  4.1 認証機能
    - ローカルユーザー認証
    - フェデレーション認証（Entra ID / Okta / SAML）
    - MFA（TOTP / WebAuthn / SMS）
    - SSO（シングルサインオン / シングルログアウト）
  4.2 認可機能
    - JWT クレーム設計
    - ロールベースアクセス制御
    - テナント分離
  4.3 ユーザー管理機能
    - プロビジョニング（JIT / SCIM / 手動）
    - ユーザー属性管理
    - セルフサービス（パスワードリセット等）
  4.4 テナント管理機能
    - IdP 追加・削除
    - テナント設定管理
  4.5 管理者機能
    - 管理コンソール
    - 監査ログ閲覧
    - 設定変更

## 5. 非機能要件（→ non-functional-requirements.md で詳細化）
  5.1 可用性（SLA / HA 構成）
  5.2 性能（応答時間 / スループット / 同時接続数）
  5.3 拡張性（MAU スケール / IdP 追加 / リージョン追加）
  5.4 セキュリティ
    - トークン管理（TTL / Revocation / ストレージ）
    - 通信暗号化（TLS / mTLS）
    - データ暗号化（at-rest / in-transit）
    - 監査ログ（保存期間 / 改ざん防止）
    - ブルートフォース対策
  5.5 DR / BCP
    - RTO / RPO 目標
    - フェイルオーバー方式
    - バックアップ戦略
  5.6 運用性
    - 監視・アラート
    - ログ管理
    - バージョンアップ方針
    - 変更管理プロセス
  5.7 互換性・移行性
    - 既存システムとの互換性
    - 段階的移行のサポート

## 6. 外部インターフェース
  6.1 利用システムとのインターフェース（OIDC / JWT）
  6.2 外部 IdP とのインターフェース（OIDC / SAML）
  6.3 管理系 API

## 7. データ要件
  7.1 ユーザーデータ（保存項目 / 保存期間 / 暗号化）
  7.2 セッションデータ
  7.3 監査ログデータ
  7.4 データフロー図

## 8. 制約事項
  8.1 技術的制約（AWS リージョン / マネージドサービス制約）
  8.2 法的制約（個人情報保護法 / 業界規制）
  8.3 組織的制約（運用体制 / スキルセット）

## 9. 前提条件
  9.1 PoC で確認済みの前提
  9.2 本番で追加検証が必要な事項

## 10. リスクと対策
  10.1 技術リスク
  10.2 運用リスク
  10.3 ビジネスリスク

## 11. プラットフォーム選定（→ platform-selection-decision.md で詳細化）
  11.1 評価基準と重み付け
  11.2 Cognito / Keycloak 比較スコアリング
  11.3 推奨と根拠

## 12. ロードマップ
  12.1 マイルストーン
  12.2 フェーズ分割（設計 → 開発 → テスト → 移行 → 運用開始）
  12.3 依存関係
```

---

## 4. 機能要件一覧（functional-requirements.md）の構成案

| 要件 ID | カテゴリ | 要件名 | 優先度 | PoC 検証状況 | 備考 |
|---------|---------|--------|--------|-------------|------|
| FR-AUTH-001 | 認証 | ローカルユーザーのID/PW認証 | Must | ✅ Phase 1,4 | — |
| FR-AUTH-002 | 認証 | Entra ID フェデレーション | Must | ⚠ Auth0 で代替検証 | 実 Entra ID 要検証 |
| FR-AUTH-003 | 認証 | Okta フェデレーション | Should | ❌ 未検証 | 2 社目 IdP 追加 |
| FR-AUTH-004 | 認証 | SAML IdP 対応 | Could | ❌ 未検証 | レガシー顧客向け |
| FR-AUTH-005 | 認証 | LDAP 連携 | Could | ❌ 未検証 | Keycloak のみ対応 |
| FR-MFA-001 | MFA | TOTP 認証 | Must | ✅ Phase 7 | — |
| FR-MFA-002 | MFA | WebAuthn / FIDO2 | Should | ❌ 未検証 | Keycloak は対応 |
| FR-MFA-003 | MFA | フェデレーション時の MFA スキップ | Must | ✅ Phase 7 | 条件付き OTP |
| FR-SSO-001 | SSO | シングルサインオン | Must | ✅ Phase 7 | — |
| FR-SSO-002 | SSO | シングルログアウト | Must | ✅ Phase 7 | Back-Channel 対応 |
| FR-AUTHZ-001 | 認可 | JWT ベースロール認可 | Must | ✅ Phase 8 | — |
| FR-AUTHZ-002 | 認可 | テナント分離 | Must | ✅ Phase 8 | — |
| FR-AUTHZ-003 | 認可 | ロール階層 | Should | ✅ Phase 8 | — |
| FR-USER-001 | ユーザー管理 | JIT プロビジョニング | Must | ✅ Phase 2 | — |
| FR-USER-002 | ユーザー管理 | SCIM プロビジョニング | Could | ❌ 未検証 | 自動同期 |
| FR-USER-003 | ユーザー管理 | セルフサービスパスワードリセット | Should | ❌ 未検証 | — |
| FR-ADMIN-001 | 管理 | 管理コンソール | Must | ✅ Phase 6 | Keycloak Admin Console |
| FR-ADMIN-002 | 管理 | IdP 追加・削除 | Must | △ 概念設計のみ | オンボーディングフロー |

---

## 5. 非機能要件一覧（non-functional-requirements.md）の構成案

| 要件 ID | カテゴリ | 要件名 | 目標値 | PoC 状況 | ヒアリングで確定 |
|---------|---------|--------|--------|---------|-----------------|
| NFR-AVL-001 | 可用性 | サービス稼働率 | 99.9%〜99.99% | Cognito: 99.9% SLA | Phase C で確定 |
| NFR-AVL-002 | 可用性 | 計画メンテナンス窓 | 月 N 時間 | — | Phase C |
| NFR-PER-001 | 性能 | 認証応答時間 | < 2 秒（P99） | PoC 未計測 | Phase B |
| NFR-PER-002 | 性能 | 同時認証リクエスト | N req/s | PoC 未計測 | Phase A (MAU) |
| NFR-PER-003 | 性能 | Lambda Authorizer 応答 | < 100ms（キャッシュあり） | PoC: 15-60ms | — |
| NFR-SEC-001 | セキュリティ | 通信暗号化 | TLS 1.2+ | PoC: HTTP（Keycloak） | 本番必須 |
| NFR-SEC-002 | セキュリティ | データ暗号化 | AES-256 at-rest | PoC: 未対応 | 本番必須 |
| NFR-SEC-003 | セキュリティ | 監査ログ保存 | N 年 | PoC: CloudWatch 基本 | Phase C |
| NFR-SEC-004 | セキュリティ | パスワードポリシー | 要定義 | Cognito デフォルト | Phase C |
| NFR-SEC-005 | セキュリティ | アカウントロック | N 回失敗で N 分ロック | 未定義 | Phase C |
| NFR-SEC-006 | セキュリティ | トークン失効 | 即時 / N 分以内 | 未検証 | Phase C |
| NFR-DR-001 | DR | RTO | N 分 | 手動切替のみ | Phase C |
| NFR-DR-002 | DR | RPO | N 分 | 未計測 | Phase C |
| NFR-DR-003 | DR | フェイルオーバー方式 | 自動 / 手動 | 手動のみ検証 | Phase C |
| NFR-OPS-001 | 運用 | 監視ツール | 要定義 | CloudWatch | Phase C |
| NFR-OPS-002 | 運用 | アラート条件 | 要定義 | 未定義 | Phase C |
| NFR-OPS-003 | 運用 | バックアップ | 日次 / PITR | 手動 | Phase C |
| NFR-OPS-004 | 運用 | バージョンアップ方針 | N ヶ月以内 | Keycloak 26.0 | Phase C |
| NFR-SCL-001 | 拡張性 | MAU スケール上限 | N 万 MAU | 175K MAU 損益分岐 | Phase A |
| NFR-SCL-002 | 拡張性 | IdP 追加リードタイム | N 営業日 | 未定義 | Phase C |

---

## 6. プラットフォーム選定判断書（platform-selection-decision.md）の構成案

```markdown
# プラットフォーム選定判断書

## 1. 評価基準

| # | 評価基準 | 重み | 説明 |
|---|---------|------|------|
| 1 | コスト（初期 + 運用） | 高 | 3 年 TCO で比較 |
| 2 | 可用性・SLA | 高 | 可用性目標の達成可否 |
| 3 | カスタマイズ性 | 中 | クレーム・ログイン画面・フロー |
| 4 | 運用負荷 | 高 | 日常運用 + 障害対応の工数 |
| 5 | マルチ IdP 対応 | 中 | 顧客 IdP の種類への対応力 |
| 6 | DR コスト | 中 | DR 構成の追加コスト |
| 7 | エコシステム | 低 | AWS サービス統合 / OSS 連携 |
| 8 | ベンダーロックイン | 低 | 将来の移行可能性 |

## 2. スコアリング（ヒアリング結果を反映して記入）

| 評価基準 | Cognito | Keycloak | 判定 |
|---------|---------|----------|------|
| ... | ... | ... | ... |

## 3. 総合判定と推奨

## 4. リスク・懸念事項

## 5. 承認
```

---

## 7. 作成スケジュール

```
Week 0 (現在):
  ✅ poc-summary-evaluation.md
  ✅ requirements-hearing-strategy.md
  ✅ requirements-document-structure.md（本ドキュメント）

Week 1:
  📋 poc-presentation.md（報告プレゼン）
  📋 hearing-phase-a.md（事業要件ヒアリング実施後）

Week 2:
  📋 hearing-phase-b.md（技術要件ヒアリング実施後）

Week 3:
  📋 hearing-phase-c.md（運用・セキュリティ要件ヒアリング実施後）
  📋 requirements-spec.md（ドラフト着手）
  📋 functional-requirements.md
  📋 non-functional-requirements.md

Week 4:
  📋 hearing-phase-d.md（最終判断会議）
  📋 platform-selection-decision.md
  📋 requirements-spec.md（確定版）

Week 5:
  📋 migration-strategy.md
  📋 cost-estimation.md
```
