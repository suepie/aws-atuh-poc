# §5 SSO・ログアウト

> 上位 SSOT: [00-index.md](00-index.md)
> 詳細: [../functional-requirements.md §4 FR-SSO](../functional-requirements.md)
> カバー範囲: FR-SSO §4.1 SSO / §4.2 ログアウト / §4.3 セッション管理
> ステータス: 📋 骨格のみ

---

## 5.1 SSO（→ FR-SSO §4.1）

### ベースライン（仮）

同一 IdP 内の複数 Client 間 SSO + Auth0/Entra 経由のクロス IdP SSO を Must で提供。

### TBD / 要確認（仮）

SSO で繋ぐシステム範囲

---

## 5.2 ログアウト（→ FR-SSO §4.2）

### ベースライン（仮）

ローカル / IdP RP-Initiated / フェデレーション連動 / Front-Channel / Back-Channel のレイヤー別対応。

### TBD / 要確認（仮）

どのレイヤーまでログアウトを伝播させるか（Back-Channel Logout の要否）

---

## 5.3 セッション管理（→ FR-SSO §4.3）

### ベースライン（仮）

セッションタイムアウト、トークン Revocation、管理者による強制全セッション破棄。

### TBD / 要確認（仮）

セッションタイムアウト目標値、強制無効化の業務要件
