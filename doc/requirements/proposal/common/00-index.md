# 横断章（Common）一覧

> 上位 SSOT: [../00-index.md](../00-index.md)

---

## 章一覧

| 章 | ファイル | 内容 |
|---|---|---|
| §C-1 | [01-architecture.md](01-architecture.md) | アーキテクチャ — Identity Broker パターン（Hub-and-Spoke） |
| §C-2 | [02-platform.md](02-platform.md) | 実装プラットフォーム（Cognito / Keycloak OSS / RHBK）選定軸 |
| §C-3 | [03-tbd-summary.md](03-tbd-summary.md) | TBD / 要確認 事項サマリー（ヒアリング項目集約） |
| §C-4 | [04-schedule.md](04-schedule.md) | 想定スケジュール（合意 → ヒアリング → 設計 → 実装） |
| §C-5 | [05-poc-note.md](05-poc-note.md) | 弊社内の事前検証について（PoC 控えめに） |

---

## 横断章の役割

```mermaid
flowchart TB
    subgraph FR["機能要件 (fr/)"]
        FRn["§FR-1〜§FR-9"]
    end
    subgraph NFR["非機能要件 (nfr/)"]
        NFRn["§NFR-1〜§NFR-9"]
    end
    subgraph COMMON["横断章 (common/)"]
        C1["§C-1 アーキ"]
        C2["§C-2 プラットフォーム"]
        C3["§C-3 TBD サマリー"]
        C4["§C-4 スケジュール"]
        C5["§C-5 PoC 補足"]
    end

    FR -.要件入力.- C1
    FR -.要件入力.- C2
    NFR -.要件入力.- C1
    NFR -.要件入力.- C2
    FR -.確認事項.- C3
    NFR -.確認事項.- C3

    style COMMON fill:#fff3e0,stroke:#e65100
```

- **§C-1 / §C-2** は FR / NFR の要件を受けて、**実装の方向性**を決める章
- **§C-3** は FR / NFR の各 "TBD / 要確認" を **横断集約**
- **§C-4 / §C-5** は **プロセス／背景補足**

---

## 関連

- [../00-index.md](../00-index.md): proposal 全体 SSOT
- [../fr/00-index.md](../fr/00-index.md): 機能要件章一覧
- [../nfr/00-index.md](../nfr/00-index.md): 非機能要件章一覧
