# §11 アーキテクチャ — Identity Broker パターン

> 上位 SSOT: [00-index.md](00-index.md)
> 詳細: [../../common/identity-broker-multi-idp.md](../../common/identity-broker-multi-idp.md)
> ステータス: 📋 骨格のみ

---

## 11.1 なぜ Broker パターンか

### ベースライン（仮）

[§3](03-federation.md) で示した複数 IdP 接続と、[§10](10-integration.md) で示した「各システムは標準 OIDC JWT を検証するだけ」を両立するには、認証基盤を **Hub-and-Spoke 型 Identity Broker** にする必要がある。

- 顧客 IdP が増えても各システムは変更不要
- JWT の検証は 1 つの issuer のみ
- 業界標準パターン（Microsoft Azure Architecture Center 公式パターン、KuppingerCole Identity Fabrics）

---

## 11.2 アーキテクチャ概要

（埋める：[identity-broker-multi-idp.md §2](../../common/identity-broker-multi-idp.md) の図を簡素化）

---

## 11.3 TBD / 要確認

- アプローチに異論ないか
- 既存システムからの移行制約
- 組織横断 IdP 統合の運用主体
