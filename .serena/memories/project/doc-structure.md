# ドキュメント管理方針

## ディレクトリ構成
```
doc/
├── old/                    # 過去の検討ドキュメント（参照用、編集しない）
├── design/                 # 最新の設計ドキュメント
│   ├── 00-index.md        # 設計ドキュメント一覧
│   ├── auth-flow.md       # 認証フロー設計（最新版）
│   ├── architecture.md    # 全体アーキテクチャ
│   └── poc-scope.md       # PoC範囲・制約
├── adr/                    # Architecture Decision Records
│   ├── 00-index.md        # ADR一覧
│   ├── 001-cognito-hybrid.md
│   ├── 002-lambda-authorizer.md
│   └── ...
└── reference/              # 参考情報・調査結果
    ├── 00-index.md        # 参考情報一覧
    ├── cognito-app-client.md
    └── ...
```

## ルール
- old/ は読み取り専用（過去の検討成果物）
- design/ は最新の設計を維持（PoC進行に合わせて更新）
- adr/ は意思決定を記録（変更理由・代替案を含む）
- reference/ は参考情報・学習メモ
- 各ディレクトリに00-index.mdを置き、一覧性を確保
