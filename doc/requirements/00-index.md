# 要件定義ドキュメント

PoC完了後の要件定義フェーズに向けた資料。
報告・調整・ヒアリングの基盤となるドキュメント群。

> 🌟 **まずここから**: [requirements-document-structure.md](requirements-document-structure.md) が要件定義フェーズの **SSOT (Single Source of Truth)**。
> §0 ナラティブ（要件定義の語る順序）／§8 ドキュメント間の依存関係と読み順／§9 ドキュメント状態ダッシュボード が全体把握の入口。
>
> 📣 **顧客向け要件定義提示**: [proposal/00-index.md](proposal/00-index.md)（フォルダ化済、章ごとにファイル分割、FR/NFR と 1:1 対応、サブセクション単位でベースライン提示 + TBD/要確認）

## ドキュメント一覧

| ドキュメント | 内容 |
|------------|------|
| **[requirements-document-structure.md](requirements-document-structure.md)** ⭐ | **要件定義 SSOT**：ナラティブ・体系・依存関係・状態ダッシュボード・ID 体系ルール |
| **[proposal/](proposal/00-index.md)** 📣 | **顧客向け要件定義 提示版**（フォルダ化）：FR/NFR と 1:1 対応で要件ベースライン提示。proposal/00-index.md が SSOT、章ごとに 02-auth.md / 03-federation.md / ... と分割 |
| [poc-summary-evaluation.md](poc-summary-evaluation.md) | **社内** PoC 総括評価：成果・既存ドキュメント評価・不足箇所分析（要件提示の裏どり資料） |
| [requirements-hearing-strategy.md](requirements-hearing-strategy.md) | 要件定義ヒアリング戦略：確認事項・ステークホルダー・進め方 |
| [platform-selection-decision.md](platform-selection-decision.md) | プラットフォーム選定判断書（評価基準 / 候補 / スコアリングフレーム）— ドラフト |
| [rhbk-vendor-inquiry.md](rhbk-vendor-inquiry.md) | Red Hat / 認定リセラへの問い合わせ文面（Q1〜Q10、日英 + リセラ別補足） |
| [functional-requirements.md](functional-requirements.md) | 機能要件一覧（FR-AUTH / FED / MFA / SSO / AUTHZ / USER / ADMIN / INT、~75 件、Cognito vs Keycloak 比較列付き）|
| [non-functional-requirements.md](non-functional-requirements.md) | 非機能要件一覧（NFR-AVL / PERF / SCL / SEC / DR / OPS / COMPLIANCE / COST / MIG、~75 件、TBD 明示） |
| [requirements-process-plan.md](requirements-process-plan.md) | 要件定義の進め方（4 段階フロー、各要件の実装可能性評価フレーム、終了基準） |
| [hearing-checklist.md](hearing-checklist.md) | ヒアリング項目の単一一覧（67 項目、Phase A〜D、優先度・回答欄付き） |
