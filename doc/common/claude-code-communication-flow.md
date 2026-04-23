# Claude Code 通信フロー (Dev Container 環境) / Claude Code Communication Flow (Dev Container)

Dev Container 上の VS Code 拡張として動作する Claude Code が、ホストの認証情報をどのように引き継ぎ、どのようなプロトコルで Anthropic API と通信しているかを整理したドキュメント。

This document describes how Claude Code — running as a VS Code extension inside a Dev Container — inherits credentials from the host and communicates with the Anthropic API.

関連ドキュメント / Related: [devcontainer-corporate-cert-setup.md](devcontainer-corporate-cert-setup.md)

---

## 日本語版

### なぜこのドキュメントが必要か

会社PCで Netskope（SSL インスペクション型 SWG/CASB）が有効な状態だと、**ブラウザからは claude.ai が使えるのに、Dev Container 内の VS Code 拡張機能（Claude Code）からは API に到達できない** という事象が発生した。

診断の過程で以下が分かった:

1. Claude Code は Node.js ベースのバイナリで、OS 証明書ストアを参照しない
2. Netskope は MITM 方式で TLS を復号・再暗号化し、独自 CA で再署名する
3. Dev Container は独立した Linux 環境で、ホスト (Windows) の証明書ストアは見えない
4. ホストで `NODE_EXTRA_CA_CERTS` を設定しても、**コンテナ内には伝わらない**

→ **対策として、コンテナ内に Netskope ルート CA を組み込む必要があった** ([devcontainer-corporate-cert-setup.md](devcontainer-corporate-cert-setup.md) 参照)。

根本原因を正確に把握するには、**Claude Code がどこからどこへ、どんなプロトコルで通信しているか** を理解している必要がある。本ドキュメントはそのリファレンスである。

### 全体アーキテクチャ

```mermaid
flowchart LR
    subgraph Host["ホスト (Windows / Mac)"]
        HC["~/.claude/<br/>.credentials.json<br/>(OAuth トークン)"]
        HA["~/.aws/<br/>(AWS 認証情報)"]
    end

    subgraph Container["Dev Container (node ユーザー)"]
        subgraph VSCode["VS Code Server + 拡張機能"]
            Ext["Claude Code 拡張機能"]
            Bin["claude バイナリ<br/>(Node.js)"]
            Ext <-->|stdio / stream-json| Bin
        end
        CC["/home/node/.claude/"]
        CA["/home/node/.aws/"]
    end

    subgraph Network["ネットワーク (Netskope 経由)"]
        NS["Netskope Proxy<br/>(SSL インスペクション)"]
    end

    subgraph API["Anthropic"]
        AP["api.anthropic.com<br/>/v1/messages"]
    end

    HC -.->|bind mount| CC
    HA -.->|bind mount| CA
    CC -->|OAuth トークン読み取り| Bin
    Bin -->|HTTPS + Bearer Token| NS
    NS -->|復号→再暗号化| AP
    AP -->|SSE ストリーミング| NS
    NS -->|再署名| Bin
```

### 認証: ホスト資格情報のバインドマウント

[.devcontainer/devcontainer.json](../../.devcontainer/devcontainer.json)

```jsonc
"mounts": [
  "source=${localEnv:HOME}${localEnv:USERPROFILE}/.aws,target=/home/node/.aws,type=bind",
  "source=${localEnv:HOME}${localEnv:USERPROFILE}/.claude,target=/home/node/.claude,type=bind",
  "source=/var/run/docker.sock,target=/var/run/docker.sock,type=bind"
]
```

| ホスト側 | コンテナ側 | 用途 |
|---|---|---|
| `~/.aws/` | `/home/node/.aws/` | AWS CLI / SDK の認証情報 |
| `~/.claude/` | `/home/node/.claude/` | Claude Code の OAuth トークン・セッション |
| `/var/run/docker.sock` | 同左 | Docker-outside-of-Docker |

**効果**: ホストで一度 `claude login` しておけば、コンテナ内では追加の認証操作なしに利用可能。

`${localEnv:HOME}${localEnv:USERPROFILE}` は Mac/Linux (`HOME`) と Windows (`USERPROFILE`) の両方に対応するためのトリック。片方しか定義されていないので文字列連結で吸収している。

### 認証プロトコル: OAuth 2.0

`~/.claude/.credentials.json` の構造:

```jsonc
{
  "claudeAiOauth": {
    "accessToken": "sk-ant-oat01-...",    // OAuth Access Token
    "refreshToken": "sk-ant-ort01-...",   // OAuth Refresh Token
    "expiresAt": 1776770257940,           // ms エポック
    "scopes": [
      "user:inference",
      "user:profile",
      "user:sessions:claude_code",
      "user:file_upload",
      "user:mcp_servers"
    ],
    "subscriptionType": "max",
    "rateLimitTier": "default_claude_max_5x"
  },
  "organizationUuid": "..."
}
```

- **認証方式**: OAuth 2.0（Authorization Code Flow + PKCE 想定）
- **トークン種別**: Anthropic 発行の Bearer トークン (`sk-ant-oat01-` / `sk-ant-ort01-`)
- **リフレッシュ**: `expiresAt` を過ぎると refresh token で自動再取得
- **スコープ**: モデル推論・プロファイル・MCP サーバー連携等

### 通信シーケンス

```mermaid
sequenceDiagram
    participant U as ユーザー (VS Code UI)
    participant Ext as Claude Code 拡張
    participant Bin as claude バイナリ
    participant Cred as /home/node/.claude/<br/>.credentials.json
    participant NS as Netskope
    participant API as api.anthropic.com

    U->>Ext: プロンプト入力
    Ext->>Bin: stream-json (stdin)
    Bin->>Cred: accessToken 読み取り
    alt トークン有効期限内
        Bin->>NS: HTTPS POST /v1/messages<br/>Authorization: Bearer sk-ant-oat01-...
    else 期限切れ
        Bin->>API: refreshToken で再取得
        API-->>Bin: 新 accessToken
        Bin->>Cred: 保存
        Bin->>NS: HTTPS POST /v1/messages
    end
    NS->>NS: TLS 復号 → 再暗号化<br/>(Netskope CA で再署名)
    NS->>API: HTTPS POST /v1/messages
    API-->>NS: SSE (text/event-stream)
    NS-->>Bin: SSE (Netskope 証明書)

    Note over Bin,NS: ★ここで Bin が Netskope CA を<br/>信頼していないと TLS エラー

    Bin-->>Ext: stream-json (stdout)<br/>差分トークンを逐次返却
    Ext-->>U: UI に表示
```

### プロセス構造

実行中のプロセスから確認できる内部構造:

```
VS Code Server
 └─ anthropic.claude-code 拡張機能 (Extension Host)
     └─ claude バイナリ (ネイティブ Node.js バイナリ)
         ├─ 引数: --output-format stream-json
         │        --input-format stream-json
         │        --permission-prompt-tool stdio
         │        --permission-mode acceptEdits
         │        --max-thinking-tokens 31999
         └─ HTTPS 通信 → api.anthropic.com
```

| 通信レイヤー | プロトコル | 備考 |
|---|---|---|
| Extension ↔ claude バイナリ | stdio + stream-json | JSON Lines 形式で双方向 |
| claude バイナリ → API | HTTPS (TLS 1.3) | `POST /v1/messages` |
| API → claude バイナリ | SSE (Server-Sent Events) | `text/event-stream` でストリーミング |
| 権限プロンプト | stdio | `--permission-prompt-tool stdio` |

### Netskope 経由で発生した問題との対応関係

```mermaid
flowchart TD
    P1["症状: VS Code 拡張で<br/>Claude に接続できない"] --> P2{ブラウザの claude.ai は?}
    P2 -->|使える| P3["→ API ブロックではない<br/>→ クライアント側の問題"]
    P3 --> P4{Netskope が有効?}
    P4 -->|Yes| P5["→ SSL インスペクションで<br/>MITM されている"]
    P5 --> P6{証明書を<br/>どこで信頼するか?}
    P6 -->|ホスト Windows| P7["❌ Dev Container には<br/>伝わらない"]
    P6 -->|コンテナ内 OS| P8["❌ Node.js は OS ストアを<br/>見ない"]
    P6 -->|NODE_EXTRA_CA_CERTS| P9["✅ 正解<br/>= 別ドキュメントの手順"]
    P9 --> P10["→ devcontainer-corporate-<br/>cert-setup.md へ"]
```

**結論**: Claude Code の通信は **(a) OAuth トークン** と **(b) Anthropic API への TLS 接続** の2軸で成立している。Netskope 環境では (b) の TLS 検証が壊れるため、**コンテナ内の Node.js に Netskope ルート CA を信頼させる必要がある**。(a) のトークンはバインドマウントで自動的に引き継がれるので追加設定は不要。

### トラブルシューティング早見表

| 症状 | 原因候補 | 確認方法 |
|---|---|---|
| TLS エラー (`UNABLE_TO_VERIFY_LEAF_SIGNATURE` 等) | Netskope CA 未信頼 | `echo $NODE_EXTRA_CA_CERTS` → [cert-setup](devcontainer-corporate-cert-setup.md) |
| `401 Unauthorized` | OAuth トークン期限切れ / 破損 | ホストで `claude login` 再実行 |
| 認証情報が見えない | バインドマウント失敗 | `ls /home/node/.claude/.credentials.json` |
| 応答が固まる | SSE 切断 / プロキシのバッファリング | Netskope 側の HTTP/2 設定を確認 |
| ブラウザは OK だが CLI はダメ | 企業ポリシーで API カテゴリブロック | Netskope 管理画面でログ確認 |

---

## English Version

### Why this document exists

On a corporate laptop with Netskope (SSL-inspecting SWG/CASB) enabled, we hit a strange state: **the `claude.ai` site worked in the browser, but the VS Code Claude Code extension running inside the Dev Container could not reach the Anthropic API.**

Diagnosis turned up several interacting facts:

1. Claude Code is a Node.js-based binary — it does **not** consult the OS trust store
2. Netskope performs TLS MITM, decrypting and re-signing traffic with its own CA
3. A Dev Container is an isolated Linux environment; the Windows host trust store is invisible to it
4. Setting `NODE_EXTRA_CA_CERTS` on the host does **not** propagate into the container

→ **Fix**: install the Netskope root CA inside the container (see [devcontainer-corporate-cert-setup.md](devcontainer-corporate-cert-setup.md)).

To understand the root cause, you need to know **what Claude Code actually talks to, and over which protocols**. This document is that reference.

### Overall Architecture

```mermaid
flowchart LR
    subgraph Host["Host (Windows / Mac)"]
        HC["~/.claude/<br/>.credentials.json<br/>(OAuth tokens)"]
        HA["~/.aws/<br/>(AWS credentials)"]
    end

    subgraph Container["Dev Container (node user)"]
        subgraph VSCode["VS Code Server + Extensions"]
            Ext["Claude Code Extension"]
            Bin["claude binary<br/>(Node.js)"]
            Ext <-->|stdio / stream-json| Bin
        end
        CC["/home/node/.claude/"]
        CA["/home/node/.aws/"]
    end

    subgraph Network["Network (via Netskope)"]
        NS["Netskope Proxy<br/>(SSL Inspection)"]
    end

    subgraph API["Anthropic"]
        AP["api.anthropic.com<br/>/v1/messages"]
    end

    HC -.->|bind mount| CC
    HA -.->|bind mount| CA
    CC -->|read OAuth token| Bin
    Bin -->|HTTPS + Bearer Token| NS
    NS -->|decrypt → re-encrypt| AP
    AP -->|SSE streaming| NS
    NS -->|re-signed response| Bin
```

### Authentication: Bind-Mounting Host Credentials

[.devcontainer/devcontainer.json](../../.devcontainer/devcontainer.json)

```jsonc
"mounts": [
  "source=${localEnv:HOME}${localEnv:USERPROFILE}/.aws,target=/home/node/.aws,type=bind",
  "source=${localEnv:HOME}${localEnv:USERPROFILE}/.claude,target=/home/node/.claude,type=bind",
  "source=/var/run/docker.sock,target=/var/run/docker.sock,type=bind"
]
```

| Host | Container | Purpose |
|---|---|---|
| `~/.aws/` | `/home/node/.aws/` | AWS CLI / SDK credentials |
| `~/.claude/` | `/home/node/.claude/` | Claude Code OAuth tokens & sessions |
| `/var/run/docker.sock` | same | Docker-outside-of-Docker |

**Effect**: log in once on the host (`claude login`) and the container picks up the same session — no extra auth inside the container.

The `${localEnv:HOME}${localEnv:USERPROFILE}` concatenation is a portability trick: Linux/Mac set `HOME`, Windows sets `USERPROFILE` — only one is defined at a time, so string concatenation resolves to the correct path on either OS.

### Authentication Protocol: OAuth 2.0

Structure of `~/.claude/.credentials.json`:

```jsonc
{
  "claudeAiOauth": {
    "accessToken": "sk-ant-oat01-...",    // OAuth Access Token
    "refreshToken": "sk-ant-ort01-...",   // OAuth Refresh Token
    "expiresAt": 1776770257940,           // ms epoch
    "scopes": [
      "user:inference",
      "user:profile",
      "user:sessions:claude_code",
      "user:file_upload",
      "user:mcp_servers"
    ],
    "subscriptionType": "max",
    "rateLimitTier": "default_claude_max_5x"
  },
  "organizationUuid": "..."
}
```

- **Auth**: OAuth 2.0 (Authorization Code Flow + PKCE)
- **Token format**: Anthropic-issued Bearer tokens (`sk-ant-oat01-*` / `sk-ant-ort01-*`)
- **Refresh**: when `expiresAt` passes, the refresh token is exchanged for a new access token automatically
- **Scopes**: model inference, profile, MCP servers, etc.

### Communication Sequence

```mermaid
sequenceDiagram
    participant U as User (VS Code UI)
    participant Ext as Claude Code Extension
    participant Bin as claude binary
    participant Cred as /home/node/.claude/<br/>.credentials.json
    participant NS as Netskope
    participant API as api.anthropic.com

    U->>Ext: Enter prompt
    Ext->>Bin: stream-json (stdin)
    Bin->>Cred: Read accessToken
    alt Token still valid
        Bin->>NS: HTTPS POST /v1/messages<br/>Authorization: Bearer sk-ant-oat01-...
    else Token expired
        Bin->>API: Exchange refreshToken
        API-->>Bin: New accessToken
        Bin->>Cred: Persist
        Bin->>NS: HTTPS POST /v1/messages
    end
    NS->>NS: TLS decrypt → re-encrypt<br/>(re-sign with Netskope CA)
    NS->>API: HTTPS POST /v1/messages
    API-->>NS: SSE (text/event-stream)
    NS-->>Bin: SSE (Netskope cert)

    Note over Bin,NS: ★ Bin must trust Netskope CA<br/>or TLS fails here

    Bin-->>Ext: stream-json (stdout)<br/>token deltas streamed
    Ext-->>U: Render in UI
```

### Process Structure

Observed from running processes:

```
VS Code Server
 └─ anthropic.claude-code extension (Extension Host)
     └─ claude binary (native Node.js binary)
         ├─ args: --output-format stream-json
         │        --input-format stream-json
         │        --permission-prompt-tool stdio
         │        --permission-mode acceptEdits
         │        --max-thinking-tokens 31999
         └─ HTTPS → api.anthropic.com
```

| Layer | Protocol | Notes |
|---|---|---|
| Extension ↔ claude binary | stdio + stream-json | JSON Lines, bidirectional |
| claude binary → API | HTTPS (TLS 1.3) | `POST /v1/messages` |
| API → claude binary | SSE (Server-Sent Events) | `text/event-stream` streaming |
| Permission prompts | stdio | `--permission-prompt-tool stdio` |

### Mapping to the Netskope Incident

```mermaid
flowchart TD
    P1["Symptom: VS Code extension<br/>can't reach Claude"] --> P2{Does browser claude.ai work?}
    P2 -->|Yes| P3["→ Not an API-level block<br/>→ Client-side issue"]
    P3 --> P4{Is Netskope enabled?}
    P4 -->|Yes| P5["→ TLS is being MITM'd<br/>by SSL inspection"]
    P5 --> P6{Where is the cert trusted?}
    P6 -->|Host Windows| P7["❌ Does not reach<br/>Dev Container"]
    P6 -->|Container OS store| P8["❌ Node.js does not read<br/>OS store"]
    P6 -->|NODE_EXTRA_CA_CERTS| P9["✅ Correct path<br/>= see sibling doc"]
    P9 --> P10["→ devcontainer-corporate-<br/>cert-setup.md"]
```

**Bottom line**: Claude Code's comms rest on two pillars — **(a) OAuth tokens** and **(b) a TLS connection to the Anthropic API**. Under Netskope, (b) breaks because Node.js in the container doesn't trust Netskope's signing CA, so **the container must be told to trust the Netskope root CA**. (a) comes for free via bind mounts and needs no extra setup.

### Troubleshooting Cheat Sheet

| Symptom | Likely cause | How to check |
|---|---|---|
| TLS error (`UNABLE_TO_VERIFY_LEAF_SIGNATURE` etc.) | Netskope CA not trusted | `echo $NODE_EXTRA_CA_CERTS` → see [cert setup](devcontainer-corporate-cert-setup.md) |
| `401 Unauthorized` | OAuth token expired / corrupt | Re-run `claude login` on host |
| Credentials not visible | Bind mount failure | `ls /home/node/.claude/.credentials.json` |
| Hangs with no response | SSE drop / proxy buffering | Review Netskope HTTP/2 settings |
| Browser works, CLI doesn't | Corporate policy blocks API category | Check Netskope admin logs |
