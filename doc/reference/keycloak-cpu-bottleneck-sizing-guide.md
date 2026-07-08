# Keycloak CPU 律速サイジングガイド（Broker / IdP-KC Tier 別）

> **目的**: Keycloak が CPU 律速となる技術的理由と、[ADR-033 の 2-tier アーキテクチャ](../adr/033-keycloak-2tier-broker-idp-architecture.md) に基づく Tier 別（Broker Keycloak / IdP Keycloak）のサイジング公式を整理する reference doc。
> **対象読者**: プラットフォーム設計者 / インフラサイジング担当 / 容量計画担当
> **位置付け**: [ADR-033 Keycloak 2-tier アーキテクチャ](../adr/033-keycloak-2tier-broker-idp-architecture.md) §G のサイジング根拠、[ADR-032 CIAM プラットフォーム選定](../adr/032-ciam-platform-cost-comparison-10m-mau.md) のコスト試算根拠として機能
> **関連**:
> - [ADR-032 10M MAU CIAM プラットフォーム選定](../adr/032-ciam-platform-cost-comparison-10m-mau.md)
> - [ADR-033 Keycloak 2-tier アーキテクチャ](../adr/033-keycloak-2tier-broker-idp-architecture.md)
> - [ADR-051 Multi-Region DR / Failover](../adr/051-multi-region-dr-failover.md)
> - [ADR-055 HRD 実装方式選定](../adr/055-hrd-implementation-method-selection.md)
> - [ADR-056 ROSA 採用判断](../adr/056-rosa-adoption-decision.md)
> - [ADR-058 認証プラットフォーム代替アーキ 6 パターン比較](../adr/058-auth-platform-alternatives-comparison.md)

---

## 目次

1. [「CPU 律速」とは](#1-cpu-律速とは)
2. [Keycloak の CPU 消費源トップ 5](#2-keycloak-の-cpu-消費源トップ-5)
3. [Password Hashing がなぜ重いか](#3-password-hashing-がなぜ重いか)
4. [ハードウェアアクセラレーションが効かない理由](#4-ハードウェアアクセラレーションが効かない理由)
5. [Broker Keycloak vs IdP Keycloak の CPU プロファイル](#5-broker-keycloak-vs-idp-keycloak-の-cpu-プロファイル)
6. [Tier 別サイジング公式](#6-tier-別サイジング公式)
7. [フェデ比率シナリオ別サイジング](#7-フェデ比率シナリオ別サイジング)
8. [EC2 インスタンス候補（Tier 別）](#8-ec2-インスタンス候補tier-別)
9. [容量監視メトリクス](#9-容量監視メトリクス)
10. [CPU 律速の軽減策](#10-cpu-律速の軽減策)
11. [参考文献](#11-参考文献)

---

## 1. 「CPU 律速」とは

Keycloak の負荷が上がったとき、**CPU が先にサチり、他のリソース（Memory / Network / Disk / DB）は余っている**状態。

```
[理想的な負荷状態]                [Keycloak の実態]
CPU     ████░░░░░░ 40%           CPU     ██████████ 100% ← ここでスケール限界
Memory  ████░░░░░░ 40%           Memory  ████░░░░░░ 40%
Network ████░░░░░░ 40%           Network ██░░░░░░░░ 20%
Disk    ████░░░░░░ 40%           Disk    █░░░░░░░░░ 10%
DB      ████░░░░░░ 40%           DB      ██░░░░░░░░ 20%
```

**実装的な帰結**:
- メモリ追加でも Login TPS は上がらない
- DB 強化でも Login TPS は上がらない
- **スケール戦略は「CPU を追加する」一択**
- Scale-Up（大 CPU node）より Scale-Out（多 node）が経済的

---

## 2. Keycloak の CPU 消費源トップ 5

Keycloak Benchmark（[keycloak-benchmark project](https://www.keycloak.org/keycloak-benchmark/)）と公式ドキュメントに基づく典型的な CPU 内訳:

| # | 処理 | 全 CPU 中の割合 | 特徴 |
|---|---|:-:|---|
| **1** | **Password Hashing**（bcrypt / Argon2id / PBKDF2）| **60-80%** | ★意図的に重い、キャッシュ不可 |
| **2** | **Cryptographic Signing**（JWT / SAML 署名）| 10-15% | ES256 / RS256 |
| **3** | **XML DSig**（SAML アサーション処理）| 5-10% | XML Canonicalization が重い |
| **4** | **JSON Serialization**（Jackson）| 3-5% | 全 API リクエスト |
| **5** | **JVM オーバーヘッド**（GC / JIT / Reflection）| 5-10% | 常時発生 |

→ **Password Hashing だけで CPU の過半数を消費**するのが最大の理由。

---

## 3. Password Hashing がなぜ重いか

### 意図的に重く設計されている

Password Hashing アルゴリズムは **オフライン攻撃（DB 漏洩後の総当り）を経済的に不可能にする**ために意図的に CPU/メモリを消費するよう設計されています。

OWASP 推奨:
- **意図的に 250ms - 1000ms かける**
- ユーザは待てるが、攻撃者が数十億回試すのは非現実的に
- 「速い hash = 脆弱」= MD5 / SHA-1 は認証用途で NG

### 各アルゴリズムのコスト（Modern CPU、単 vCPU）

| アルゴリズム | 設定 | 単 hash 時間 | vCPU あたり Login TPS | 用途 |
|---|---|---|---|---|
| MD5 / SHA-256（生）| — | 0.001 ms | 100,000+ | ❌ **使用禁止**（Rainbow Table 攻撃）|
| **bcrypt** cost 10 | 2^10 rounds | ~65 ms | ~15/sec | 旧デフォルト、まだ許容 |
| **bcrypt** cost 12 | 2^12 rounds | ~250 ms | ~4/sec | **OWASP 現行推奨最小** |
| **bcrypt** cost 14 | 2^14 rounds | ~1000 ms | ~1/sec | 高セキュリティ |
| **PBKDF2** 100k iter | SHA-256 | ~50 ms | ~20/sec | FIPS 認定向き |
| **PBKDF2** 600k iter | SHA-256 | ~300 ms | ~3/sec | **Keycloak 24+ default** |
| **Argon2id** t=1 m=64MB | メモリ 64 MB | ~100 ms | ~10/sec | OWASP 第一推奨 |
| **Argon2id** t=3 m=128MB | メモリ 128 MB | ~300 ms | ~3/sec | 高セキュリティ |

**驚くべき事実**: 1 vCPU で処理できる Login は「MD5 で 100,000/sec」に対し「bcrypt cost 12 で 4/sec」= **25,000 倍の差**。この違いがすべてを説明します。

### キャッシュできない

Password Hash はキャッシュできない設計です:

```
[通常のキャッシュ発想]
初回計算 → 結果をキャッシュ → 2 回目以降は cache hit で高速化

[Password Hashing の場合]
Login: user_input + salt → hash → DB stored_hash と比較
   ↑
   ★ 毎回計算する必要あり
   ★ 攻撃者にキャッシュ攻撃許すため、絶対にキャッシュしない
```

→ **同じユーザが 1000 回ログインしても、1000 回計算する**（セキュリティ上の要求）。

---

## 4. ハードウェアアクセラレーションが効かない理由

Intel AES-NI や ARM Crypto Extensions は AES / SHA を高速化しますが、**Password Hashing には効きません**:

| アルゴリズム | ハードウェア加速 | 理由 |
|---|:-:|---|
| AES（暗号化）| ✅ AES-NI で 10 倍高速 | 定義された命令セット |
| SHA-256（生ハッシュ）| ✅ ARM SHA Extensions で 5 倍高速 | 定義された命令セット |
| **bcrypt** | ❌ **ハードウェア加速効かない** | **メモリアクセスパターン依存**（Blowfish の Sbox テーブル）|
| **Argon2** | ❌ さらに効かない | **メモリハード設計**（64-128MB のランダムアクセス）|
| **PBKDF2** | △ SHA 部分だけ加速 | 反復回数がボトルネック |

→ **bcrypt / Argon2 は "メモリランダムアクセス" を強要することで GPU/ASIC/FPGA での並列化を阻止**する設計。CPU の SIMD 命令も、AES-NI も、まったく効きません。

---

## 5. Broker Keycloak vs IdP Keycloak の CPU プロファイル

[ADR-033](../adr/033-keycloak-2tier-broker-idp-architecture.md) の 2-tier アーキテクチャでは、Broker と IdP-KC の CPU プロファイルが**根本的に違います**:

```
                         [顧客ユーザ]
                              │
                              ▼
              ┌──────────────────────────────┐
              │ Broker Keycloak (Tier 1)      │
              │ ★ 全リクエストの入口          │
              │ ・IdP フェデ (SAML/OIDC 受信)  │
              │ ・JWT 発行                     │
              │ ・Password Hashing なし ★     │
              └───┬──────────────────────┬───┘
                  │                      │
        (Federation)                (Local User)
                  │                      │
                  ▼                      ▼
     ┌───────────────────┐      ┌───────────────────┐
     │ 顧客 IdP           │      │ IdP Keycloak (T2) │
     │ Entra ID / Okta   │      │ ★ Password 認証   │
     │ 等                │      │ ・bcrypt/Argon2   │
     │                   │      │ ・重い CPU 消費   │
     └───────────────────┘      └───────────────────┘
```

### CPU 消費源の Tier 別比較

| CPU 消費源 | Broker Keycloak | IdP Keycloak |
|---|---|---|
| **Password Hashing** | **~0%** ★（自身は password 持たない）| **60-80%** |
| **JWT Signing**（ES256）| 20-30% | 5-10% |
| **JWT Verification** | 15-20% | 5-10% |
| **SAML DSig 検証**（顧客 IdP の SAML Response 検証）| 20-30% | ~0%（外部 SAML 受けない）|
| **SAML DSig 生成**（本基盤が SAML SP に送る場合）| 10-15% | 0% |
| **Federation プロトコル処理** | 15-20% | 0% |
| **JSON Serialization** | 5% | 3% |
| **Session Cache** | 5-10% | 5% |
| **JVM オーバーヘッド** | 5-10% | 5-10% |

→ **Broker と IdP-KC は根本的に違うワークロード**:
- **Broker**: 軽い処理を大量に（Signing / Verification が中心、Password Hashing なし）
- **IdP-KC**: 重い処理を少量（Password Hashing が支配）

### Tier 別のスループット特性

| 処理 | Broker Keycloak | IdP Keycloak |
|---|---|---|
| **典型的な TPS/vCPU 上限** | ~500-1,500 /sec | ~50-100 /sec |
| **ボトルネック** | JWT signing / SAML DSig | **Password Hashing** |
| **メモリ要件** | 中（Session Cache 中心）| 大（User Storage + Session Cache）|
| **Scale-Out 動機** | 高スループット吸収 | Password Hashing 並列化 |
| **CPU 律速の程度** | 中〜高（可制御）| **超高**（制御しにくい）|

→ **同じ「Keycloak」でも Broker は IdP の 10-30 倍のスループット/vCPU**。

---

## 6. Tier 別サイジング公式

### 前提記号

- `L` = Peak Login TPS（目標値）
- `F` = Federation 比率（0.0-1.0）= フェデ顧客 / 全顧客
- `R` = Refresh TPS（typical: L の 3-5 倍）
- `M` = Safety Margin（推奨 1.5-2.0x）

### Broker Keycloak（Tier 1）

Broker はすべてのログインを pass-through + JWT/SAML 処理:

```
Broker 必要 vCPU = ceil(L / 500) × M + ceil(R / 800) × M + overhead
              ≈ (L × 0.003 + R × 0.002 + 1) × M
```

**簡易目安**:

| Peak Login TPS | 推奨 vCPU（Broker、Multi-AZ 3 node 合計）|
|---|---|
| 50 TPS | 6 vCPU（2 vCPU × 3 node）|
| 125 TPS | 6-9 vCPU（2-3 vCPU × 3 node）|
| 500 TPS | 12 vCPU（4 vCPU × 3 node）|
| 1,000 TPS | 18-24 vCPU（6-8 vCPU × 3 node）|
| 3,000 TPS | 36-48 vCPU（12-16 vCPU × 3 node）|

### IdP Keycloak（Tier 2）

IdP-KC は Local ユーザのみ、Password Hashing 中心:

```
IdP-KC Login TPS = L × (1 - F)  ← Local ユーザぶんだけ
IdP-KC 必要 vCPU = ceil(IdP-KC Login TPS / T_login) × M + overhead
```

`T_login` = 1 vCPU あたりの Login TPS（アルゴリズム依存）:
- bcrypt cost 10: 10-15 TPS/vCPU
- **bcrypt cost 12**: **5-8 TPS/vCPU** ★推奨
- PBKDF2 600k iter: 3-5 TPS/vCPU
- Argon2id t=1 m=64MB: 8-12 TPS/vCPU

**簡易目安**（bcrypt cost 12、F=0.7 = フェデ 70% 想定）:

| Peak Login TPS | Local TPS（30%）| 推奨 vCPU（IdP-KC、Multi-AZ 3 node 合計）|
|---|---|---|
| 50 TPS | 15 TPS | 6-9 vCPU（2-3 vCPU × 3 node）|
| 125 TPS | 37.5 TPS | 12-18 vCPU（4-6 vCPU × 3 node）|
| 500 TPS | 150 TPS | 36-54 vCPU（12-18 vCPU × 3 node）|
| 1,000 TPS | 300 TPS | 72-108 vCPU（24-36 vCPU × 3 node）|

---

## 7. フェデ比率シナリオ別サイジング

**フェデ比率は IdP-KC 負荷を直接決定**。ヒアリング B-BROK-1（顧客テナントのフェデ vs ローカル比率想定）で確認が必要。

### 1.5M ユーザ / Peak 125 Login TPS ケース

| フェデ比率 | Broker Login TPS | IdP-KC Login TPS | IdP-KC 必要 vCPU（bcrypt cost 12）| IdP-KC 推奨インスタンス |
|---|---|---|---|---|
| 100% フェデ / 0% ローカル | 125 | 0 | 0（IdP-KC 不要）| **IdP-KC 不要** |
| 90% フェデ / 10% ローカル | 125 | 12.5 | 3-5 | c7g.large × 3 |
| 70% フェデ / 30% ローカル ★典型 | 125 | 37.5 | 8-15 | **c7g.xlarge × 3** |
| 50% フェデ / 50% ローカル | 125 | 62.5 | 12-20 | c7g.xlarge × 3 or 2xlarge × 3 |
| 30% フェデ / 70% ローカル | 125 | 87.5 | 18-26 | **c7g.2xlarge × 3** |
| 10% フェデ / 90% ローカル | 125 | 112.5 | 23-33 | c7g.2xlarge × 3-4 |
| 0% フェデ / 100% ローカル | 125 | 125 | 25-35 | c7g.2xlarge × 4-5 |

→ **フェデ比率が下がるごとに IdP-KC の CPU 需要が急増**。ヒアリング B-BROK-1 の重要性がここに現れる。

### 10M MAU（ADR-033 §G と整合）

| フェデ比率 | Broker Login TPS | IdP-KC Login TPS | IdP-KC 必要 vCPU |
|---|---|---|---|
| 70% フェデ / 30% ローカル | 1,000-3,000 | 300-900 | 60-180 |
| 50% フェデ / 50% ローカル | 1,000-3,000 | 500-1,500 | 100-300 |

---

## 8. EC2 インスタンス候補（Tier 別）

3-year Standard RI No Upfront、東京リージョン想定。

### Broker Keycloak（軽い、高スループット、Multi-AZ 3 node）

| # | インスタンス | vCPU / RAM | 3y RI 月額 | 3 node 月額 | 妥当性（Peak 125 TPS）|
|---|---|---|---|---|---|
| **1 ★推奨（小規模）** | **c7g.large** | 2 / 4 GB | ~$31 | **$93** | 6 vCPU total、Peak 500 TPS まで対応 |
| 2 | c7g.xlarge | 4 / 8 GB | ~$62 | $186 | Peak 1,000 TPS まで対応、成長余地 |
| 3 | m7g.large | 2 / 8 GB | ~$41 | $123 | メモリ多め、Session Cache 大量時 |
| 4 | c7i.large（Intel）| 2 / 4 GB | ~$37 | $111 | Intel 互換要件時のみ |

### IdP Keycloak（重い、Password Hashing、Multi-AZ 3 node）

| # | インスタンス | vCPU / RAM | 3y RI 月額 | 3 node 月額 | 妥当性（Peak 125 TPS / フェデ 70%）|
|---|---|---|---|---|---|
| **1 ★推奨** | **c7g.xlarge** | 4 / 8 GB | ~$62 | **$186** | 12 vCPU = 需要 8-15 vCPU に margin 1-1.5x |
| 2 | c7g.2xlarge | 8 / 16 GB | ~$124 | $372 | 24 vCPU、10M ユーザ将来対応 |
| 3 | m7g.xlarge | 4 / 16 GB | ~$83 | $249 | メモリリッチ、Session 大量時 |
| 4 | m7i.xlarge（Intel）| 4 / 16 GB | ~$108 | $324 | Intel 互換 + メモリ、FIPS 等 |

### 1.5M ユーザ 2-tier 合計コスト試算

**Baseline 構成**（フェデ 70% 想定）:

| Tier | インスタンス × 台数 | 月額 |
|---|---|---|
| Broker | c7g.large × 3（3y CSP）| $93 |
| IdP-KC | c7g.xlarge × 3（3y CSP）| $186 |
| **Keycloak 合計** | 6 node | **$279** |
| Aurora Broker DB（Multi-AZ）| db.r6g.large × 2 | $200 |
| Aurora IdP-KC DB（Multi-AZ）| db.r6g.large × 2 | $200 |
| **Aurora 合計** | | $400 |
| ALB / CloudFront / WAF / NAT / etc | | $500 |
| Auto Scaling margin | | $100 |
| **月額合計** | | **~$1,279** |
| **年額** | | **~$15,348（¥230 万）** |

---

## 9. 容量監視メトリクス

CPU 律速なので、以下メトリクスをリアルタイム監視:

### Prometheus / CloudWatch Custom Metrics

| メトリクス | 意味 | アラート閾値 |
|---|---|---|
| **`process_cpu_seconds_total`** | プロセス CPU 消費 | 70% で warn、85% で critical |
| **`keycloak_login_attempts_total`**（Rate）| Login 試行 TPS | 想定超えを検知 |
| **`keycloak_login_success_total`**（Rate）| Login 成功 TPS | Password Hashing の実負荷 |
| **`http_server_requests_seconds`**（p95, p99）| API レイテンシ | p95 > 500ms で調査 |
| **`jvm_memory_used_bytes`** | ヒープ使用量 | 80% で調査 |
| **`jvm_gc_pause_seconds`**（sum）| GC 停止時間 | 500ms/min で調査 |
| **`infinispan_cache_hit_ratio`** | Session Cache 命中率 | 90% 下回りで警告 |

### Login TPS の Password vs Federation 内訳追跡

Custom メトリクスとして両方を分離監視:

```prometheus
# Password Login TPS
rate(keycloak_login_success_total{authtype="password"}[1m])

# Federation Login TPS
rate(keycloak_login_success_total{authtype="federated"}[1m])
```

→ **Password Login TPS の変動が IdP-KC 増設のトリガ**。Federation Login TPS は Broker 増設のトリガ。

### Auto Scaling メトリクス

**推奨**: Custom Metric ベースの Scale-Out（CPU 単独より正確）:

```
[Broker]
Scale Out Trigger: 
  - avg(request_rate) > 400 TPS/node for 3 min
  - OR CPU > 70% for 5 min

[IdP-KC]
Scale Out Trigger:
  - avg(login_success_password_rate) > 8 TPS/node for 3 min
  - OR CPU > 70% for 5 min
```

**注意**: IdP-KC は起動時間が長い（JVM warmup + Infinispan 参加）ため、**Scale-Out の予兆検知を早めに**（3 分閾値、5 分猶予等）。

---

## 10. CPU 律速の軽減策

### Level 1: 設計での軽減

| 対策 | 内容 | 効果 |
|---|---|---|
| **Federation 優先** | 顧客 IdP と連携するテナントを最大化 | Password Login TPS 減 |
| **SSO 有効化** | 同一 Realm 内で Access Token 再利用 | 再認証頻度減 |
| **長い Refresh Token 寿命** | Access Token 30 分、Refresh 30 日 | Login 頻度減 |
| **Session Sticky（Cookie）** | ブラウザセッション有効期間を長く | 再ログイン抑制 |
| **Client Sessions Persistent** | Infinispan 永続化を有効 | Node 再起動での再認証回避 |

### Level 2: アルゴリズム選択

| 選択 | 効果 | トレードオフ |
|---|---|---|
| **bcrypt cost 12 → cost 10** | CPU 消費 1/4 に | 攻撃コスト 1/4 に減（NIST 現行推奨最小レベル）|
| **PBKDF2 600k → 200k** | CPU 消費 1/3 に | セキュリティ低下、Keycloak 24+ 非推奨方向 |
| **Argon2id → PBKDF2** | メモリ節約、CPU は同等 | メモリハードネス失う |
| **Argon2id t=1 → 一括 t=2 or t=3** | セキュリティ向上 | CPU 2-3 倍 |

**注意**: セキュリティトレードオフは慎重に。[ADR-045 鍵管理戦略](../adr/045-cryptographic-key-management-strategy.md) と整合。監査対応可否も要確認。

### Level 3: 水平スケール

- Auto Scaling Group を **Custom Metric ベース**でトリガ
- CloudWatch で Login/sec を追跡（bcrypt cost が支配的なので RPS より Login 特化）
- Peak 時に +1-2 node 追加、通常時は Baseline に戻る

### Level 4: JVM チューニング

| 設定 | 推奨値 | 理由 |
|---|---|---|
| GC アルゴリズム | **G1GC** or **ZGC** | 低レイテンシ + スループット両立 |
| ヒープサイズ | `-XX:MaxRAMPercentage=60` | OS + Infinispan Off-heap に余裕 |
| ワーカスレッド数 | vCPU × 2-3 | Password Hashing は同期処理、CPU バウンド |
| メタスペース | `-XX:MetaspaceSize=256m` | Reflection 多用のため多め |

### Level 5: Session Cache Off-heap 化

Infinispan Session Cache を Off-heap に移す:
- GC 圧力軽減
- 大量セッション時の CPU 効率向上
- Keycloak 25+ で標準サポート

---

## 11. 参考文献

### Keycloak 公式

- [Keycloak Server Guide - Sizing your environment](https://www.keycloak.org/high-availability/concepts-memory-and-cpu-sizing)
- [Keycloak Benchmark Project](https://www.keycloak.org/keycloak-benchmark/)
- [Keycloak 26.4 Performance Benchmarks](https://www.keycloak.org/2025/10/keycloak-benchmark)
- [Concepts for configuring thread pools](https://www.keycloak.org/high-availability/concepts-threads)

### Password Hashing

- [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- [NIST SP 800-63B - Digital Identity Guidelines](https://pages.nist.gov/800-63-3/sp800-63b.html)
- [Argon2 Original Paper (RFC 9106)](https://datatracker.ietf.org/doc/html/rfc9106)
- [bcrypt Original Paper - Provos & Mazières](https://www.usenix.org/legacy/events/usenix99/provos/provos.pdf)

### AWS / インフラ

- [AWS Graviton3 Performance Benchmarks](https://aws.amazon.com/ec2/graviton/)
- [Keycloak on AWS Best Practices](https://aws.amazon.com/blogs/architecture/field-notes-deploying-and-migrating-workloads-across-aws-accounts-with-red-hat-keycloak/)

### 本プロジェクト内 関連 doc

- [ADR-032 CIAM プラットフォーム選定](../adr/032-ciam-platform-cost-comparison-10m-mau.md)
- [ADR-033 Keycloak 2-tier アーキテクチャ](../adr/033-keycloak-2tier-broker-idp-architecture.md) — 本 doc は §G のサイジング根拠の裏どり
- [ADR-051 Multi-Region DR / Failover](../adr/051-multi-region-dr-failover.md)
- [ADR-055 HRD 実装方式選定](../adr/055-hrd-implementation-method-selection.md)
- [ADR-056 ROSA 採用判断](../adr/056-rosa-adoption-decision.md)
- [ADR-058 認証プラットフォーム 代替アーキ 6 パターン比較](../adr/058-auth-platform-alternatives-comparison.md)
- [B-BROK 系ヒアリング項目（フェデ比率想定）](../requirements/hearing-checklist.md)

---

## 改訂履歴

- 2026-07-08: 初版作成。Keycloak が CPU 律速となる技術的理由（Password Hashing が 60-80% を占める意図的な設計、ハードウェア加速非対応、キャッシュ不可）を整理。ADR-033 の 2-tier アーキテクチャに基づく Broker vs IdP-KC の CPU プロファイル比較、Tier 別サイジング公式、フェデ比率シナリオ別サイジング（1.5M ユーザ / 10M MAU）、EC2 インスタンス候補、容量監視メトリクス、CPU 律速軽減策 5 レベルを体系化。ADR-033 §G のサイジング根拠の裏どり + フェデ比率ヒアリング B-BROK-1 の重要性を明示化
