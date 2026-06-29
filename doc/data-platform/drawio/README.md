# データプラットフォーム drawio 図一覧

> 配置: `doc/data-platform/drawio/`
> 編集方法: VS Code 拡張機能「Draw.io Integration」、オンライン版（diagrams.net）、デスクトップ版で編集可能
> アイコン: AWS Architecture Icons（mxgraph.aws4.*）

## ファイル一覧

| ファイル | 内容 | 対応 SSOT |
|---|---|---|
| [required-architecture.drawio](required-architecture.drawio) | **必須項目のみの構成図**（§4.5.2「必須 41 項目」を抽出した構成図、任意 31 項目は含まない）| [account-architecture-analysis.md §4.5.2](../account-architecture-analysis.md) |
| [required-architecture.mmd](required-architecture.mmd) | 上記の Mermaid 版（概要レビュー用） | 同上 |

## 設計方針

- **AWS Architecture Icons** を採用（`mxgraph.aws4.resourceIcon`）。Service Icon は公式アセット相当
- **アカウント境界**は太枠で表現（緑=Producer / オレンジ=中央 / 青=横断）
- **層構造**は subgraph / mxCell コンテナで階層化
- **アクター**は黄色の楕円（IAM Role と紐付け）
- **接続線**: 実線=データ流れ / 点線=制御・認可・暗号化

## 更新方針

設計変更時は **Mermaid と drawio の両方を更新**する。Mermaid は markdown レビュー用、drawio はプレゼン・印刷用。
