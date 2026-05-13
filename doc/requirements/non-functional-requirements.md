# 非機能要件一覧（non-functional-requirements.md）

> 最終更新: 2026-05-13（Cognito 2024-11 仕様変更反映 / Plus ティア追加課金 / Rate Limit 注記）
> 対象: 共有認証基盤（Cognito / Keycloak 比較）
> 関連: [keycloak-network-architecture.md](../common/keycloak-network-architecture.md)、[ADR-006](../adr/006-cognito-vs-keycloak-cost-breakeven.md)

---

## 凡例

### 状態
- ✅ **確定**: PoC 計測 / AWS SLA / 業界標準で迷いなし
- 🟡 **デフォルト**: 推奨値あり、ヒアリングで承認が必要
- 🔴 **TBD**: ヒアリングで顧客から確認必須

### 表記
- 値の前の `(D)` はデフォルト推奨値
- 値の前の `(TBD)` は要ヒアリング

### 前提（**共通認証基盤としての位置付け**）

本基盤は複数顧客が利用する共有プラットフォーム。非機能要件は「**最も厳しい要件を満たす顧客に合わせる**」のが原則。例えば:
- 1 社が SLA 99.99% を要求すれば、基盤全体で 99.99% を目指す（または個別構成にする）
- 1 社が FIPS 必須なら、基盤として FIPS 対応版（RHBK）採用が必須要因になる
- 1 社が 100 万 MAU 規模なら、その負荷を前提に設計

→ ヒアリングでは「**最も厳しい要件をどこに置くか**」を確認することが重要。

---

## 1. NFR-AVL（可用性）

| ID | 要件 | 推奨値 | Cognito | Keycloak | 状態 |
|----|------|------|--------|----------|:---:|
| NFR-AVL-001 | サービス稼働率 SLA | (TBD) **99.9% / 99.95% / 99.99%** | ✅ AWS 99.9% 保証 | ⚠ 自前 HA 設計（Multi-AZ + Auto Scaling） | 🔴 |
| NFR-AVL-002 | 計画メンテナンス窓 | (TBD) 月 N 時間 | ✅ AWS 透過 | ⚠ Realm 設定変更時の制約あり | 🔴 |
| NFR-AVL-003 | マルチ AZ 配置 | (D) **必須** | ✅ AWS 自動 | ⚠ ECS Multi-AZ + Aurora Multi-AZ 設計要 | 🟡 |
| NFR-AVL-004 | 自動復旧（コンテナ障害） | (D) **必須** | ✅ AWS 自動 | ✅ ECS Service Auto Heal（PoC 検証済） | ✅ |
| NFR-AVL-005 | 単一障害点の排除 | (D) **必須** | ✅ | ⚠ RDS / ALB 冗長化 | 🟡 |
| NFR-AVL-006 | デプロイ時のダウンタイム | (D) **ゼロダウン（Blue/Green）** | ✅ 透過 | ⚠ Rolling Update 設計 | 🟡 |

**ヒアリング論点**: NFR-AVL-001（SLA 目標）が最重要。99.9% なら Cognito、99.99% なら自前設計（Keycloak は構成次第）。

---

## 2. NFR-PERF（性能）

| ID | 要件 | 推奨値 | Cognito | Keycloak | 状態 |
|----|------|------|--------|----------|:---:|
| NFR-PERF-001 | 認証応答時間（P50 / P95 / P99） | (D) **P95 < 1s, P99 < 2s** | ✅ AWS 内 | ⚠ ECS スペック次第（PoC: 数百 ms 観測） | 🟡 |
| NFR-PERF-002 | 同時認証リクエスト処理能力 | (TBD) N req/s | ⚠ AWS スケーラブル（ただし一部 API に Account-level rate limit あり：`InitiateAuth` / `AdminInitiateAuth` 等。Service Quotas で要事前確認） | ⚠ ECS Auto Scaling 設計 | 🔴 |
| NFR-PERF-003 | Lambda Authorizer 応答時間 | (D) **キャッシュ HIT < 10ms / MISS < 100ms** | ✅ Phase 3 計測（15-60ms） | ✅ 同 Lambda（同性能） | ✅ |
| NFR-PERF-004 | JWT 検証スループット | (D) **>1,000 req/s** | ✅ Lambda 並列 | ✅ Lambda 並列 | ✅ |
| NFR-PERF-005 | JWKS キャッシュ TTL | (D) **1 時間（Lambda 内）** | ✅ | ✅ | ✅ |
| NFR-PERF-006 | API Gateway スロットリング | (TBD) 顧客別 / 全体 | ✅ Cognito API Rate Limit 別途 | — | 🔴 |
| NFR-PERF-007 | 認証ピーク時間帯への耐性 | (D) **始業時 N 倍想定** | ✅ AWS 自動スケール | ⚠ ECS 事前スケールアウト設計 | 🟡 |
| NFR-PERF-008 | DB 応答時間（Keycloak のみ） | (D) **P95 < 50ms** | — | ⚠ RDS チューニング | 🟡 |

**ヒアリング論点**: NFR-PERF-002（スループット）と NFR-PERF-007（ピーク時間帯）。MAU から逆算する。

---

## 3. NFR-SCL（拡張性 / スケーラビリティ）

| ID | 要件 | 推奨値 | Cognito | Keycloak | 状態 |
|----|------|------|--------|----------|:---:|
| NFR-SCL-001 | MAU スケール上限 | (TBD) **1 年後 / 3 年後** | ✅ 数千万 MAU まで実績 | ⚠ HA 設計次第 | 🔴 |
| NFR-SCL-002 | ピーク時同時セッション数 | (TBD) | ✅ AWS 透過 | ⚠ Sticky Session 不要だが ECS Task 数 | 🔴 |
| NFR-SCL-003 | 顧客テナント数（IdP 数）スケール | (TBD) **N 顧客 / 年** | ✅ User Pool に複数 IdP | ✅ Realm に複数 IdP | 🟡 |
| NFR-SCL-004 | IdP 追加リードタイム | (D) **< 1 営業日** | ✅ Console / IaC | ✅ Console / IaC | 🟡 |
| NFR-SCL-005 | 自動スケーリング | (D) **必須（負荷に応じて）** | ✅ AWS 透過 | ⚠ ECS Auto Scaling 設計要 | 🟡 |
| NFR-SCL-006 | マルチリージョン対応 | (TBD) **必要 / 不要** | ✅ User Pool 別リージョン | ⚠ Aurora Global DB 設計要 | 🔴 |
| NFR-SCL-007 | データベーススケール（Keycloak） | — | — | ⚠ Aurora Auto Scaling | 🟡 |

**ヒアリング論点**: NFR-SCL-001（MAU 規模）が**最重要**。コスト損益分岐 175,000 MAU（[ADR-006](../adr/006-cognito-vs-keycloak-cost-breakeven.md)）の判断材料。

---

## 4. NFR-SEC（セキュリティ）

| ID | 要件 | 推奨値 | Cognito | Keycloak | 状態 |
|----|------|------|--------|----------|:---:|
| NFR-SEC-001 | 通信暗号化 | (D) **TLS 1.2+** | ✅ AWS 強制 | ⚠ ACM + ALB 設定要（PoC は HTTP） | 🟡 |
| NFR-SEC-002 | データ暗号化（at-rest） | (D) **AES-256（KMS）** | ✅ 自動 | ✅ RDS storage_encrypted=true | ✅ |
| NFR-SEC-003 | トークン署名アルゴリズム | (D) **RS256** | ✅ | ✅（ES256 も可） | ✅ |
| NFR-SEC-004 | Access Token TTL | (D) **15〜60 分** | ✅ App Client 設定 | ✅ Realm 設定 | 🟡 |
| NFR-SEC-005 | Refresh Token TTL | (D) **30 日** | ✅ | ✅ | 🟡 |
| NFR-SEC-006 | ID Token TTL | (D) **15 分** | ✅ | ✅ | 🟡 |
| NFR-SEC-007 | Refresh Token Rotation | (D) **有効化** | ⚠ デフォルト OFF（要設定） | ✅ デフォルト ON | 🟡 |
| NFR-SEC-008 | トークン失効（Revocation） | (D) **対応必須** | ⚠ Refresh Token のみ | ✅ Token Revocation | 🟡 |
| NFR-SEC-009 | パスワード保管アルゴリズム | (D) **PBKDF2 / bcrypt / Argon2** | ✅ AWS 内部 | ✅ PBKDF2-SHA512（デフォルト） | ✅ |
| NFR-SEC-010 | ブルートフォース対策 | (D) **連続失敗で一時ロック** | ⚠ Plus ティア（$0.02/MAU 追加）必要（2024-12〜 Advanced Security は Plus に統合） | ✅ Realm Settings | 🟡 |
| NFR-SEC-011 | WAF 適用 | (D) **AWS WAF（CloudFront）** | ✅ | ⚠ ADR-013 で計画 | 🟡 |
| NFR-SEC-012 | DDoS 対策 | (D) **Shield Standard** | ✅ AWS 標準 | ✅ AWS 標準 | ✅ |
| NFR-SEC-013 | ペネトレーションテスト | (TBD) 年 N 回 | — | — | 🔴 |
| NFR-SEC-014 | 脆弱性スキャン | (D) **ECR Image Scan + Inspector** | — | ✅ ECR Scan | 🟡 |
| NFR-SEC-015 | シークレット管理 | (D) **AWS Secrets Manager** | ✅ | ✅ | ✅ |
| NFR-SEC-016 | ネットワーク分離（Private Subnet） | (D) **必須** | ✅ AWS 透過 | ✅ Phase Option B 移行済 | ✅ |
| NFR-SEC-017 | 管理画面アクセス制御 | (D) **IP 制限 + VPN/Bastion** | ✅ IAM | ⚠ ADR-011 で計画（N2） | 🟡 |
| NFR-SEC-018 | JWKS エンドポイント保護 | (D) **公開 + WAF レート制限** | ✅ 公開 | ✅ Phase ADR-012 | ✅ |
| NFR-SEC-019 | 内部通信の認証（Lambda → Keycloak） | (D) **VPC 内完結** | ✅ Cognito VPCE | ✅ Internal ALB（ADR-012） | ✅ |
| NFR-SEC-020 | セッション固定攻撃対策 | (D) **必須** | ✅ | ✅ | ✅ |

**詳細**: [keycloak-network-architecture.md](../common/keycloak-network-architecture.md)、[jwks-public-exposure.md](../common/jwks-public-exposure.md)

---

## 5. NFR-DR（災害復旧）

| ID | 要件 | 推奨値 | Cognito | Keycloak | 状態 |
|----|------|------|--------|----------|:---:|
| NFR-DR-001 | RTO（目標復旧時間） | (TBD) **N 分 / N 時間** | ✅ Cognito 別リージョン | ⚠ Aurora Global DB + ECS 設計 | 🔴 |
| NFR-DR-002 | RPO（目標復旧地点） | (TBD) **N 分 / 0** | ✅ ユーザーデータ複製可 | ⚠ Aurora Global DB（〜1 秒） | 🔴 |
| NFR-DR-003 | フェイルオーバー方式 | (TBD) **自動 / 手動** | ✅ Route 53 Health Check | ⚠ 設計要 | 🔴 |
| NFR-DR-004 | バックアップ保存期間 | (D) **30 日** | ✅ AWS 自動 | ✅ RDS Automated Backup | 🟡 |
| NFR-DR-005 | PITR（Point-in-Time Recovery） | (D) **5 分粒度 / 35 日** | ✅ | ✅ Aurora PITR | 🟡 |
| NFR-DR-006 | クロスリージョンバックアップ | (D) **必須** | ✅ User Pool 別リージョン | ⚠ Aurora Cross-Region Replica | 🟡 |
| NFR-DR-007 | DR 訓練 | (TBD) 年 N 回 | — | — | 🔴 |
| NFR-DR-008 | DR 切替時のセッション維持 | (D) **可能ならベスト** | ✅ Phase 5（Auth0 SSO 維持） | ⚠ 別検証 | 🟡 |

**ヒアリング論点**: NFR-DR-001 / 002 が最重要。RTO/RPO の確定で Cognito vs Keycloak の DR コスト差（$0.50/月 vs $890/月）が判断できる。

---

## 6. NFR-OPS（運用性）

| ID | 要件 | 推奨値 | Cognito | Keycloak | 状態 |
|----|------|------|--------|----------|:---:|
| NFR-OPS-001 | 監視・メトリクス | (D) **CloudWatch Metrics + Dashboard** | ✅ | ✅ Keycloak Metrics + CloudWatch | 🟡 |
| NFR-OPS-002 | アラート通知 | (D) **CloudWatch Alarm + SNS** | ✅ | ✅ | 🟡 |
| NFR-OPS-003 | ログ保存期間 | (TBD) **N ヶ月 / N 年** | ✅ CloudTrail + CloudWatch | ✅ Event Log + CloudWatch | 🔴 |
| NFR-OPS-004 | ログ検索性 | (D) **CloudWatch Insights / S3 + Athena** | ✅ | ⚠ Event Listener 自前 | 🟡 |
| NFR-OPS-005 | バージョンアップ方針 | (TBD) **N ヶ月毎 / LTS のみ** | ✅ AWS 透過 | ⚠ 手動（Docker image 更新） | 🔴 |
| NFR-OPS-006 | パッチ適用（CVE 対応） | (D) **緊急 N 日以内、定例 N 週間以内** | ✅ AWS 自動 | ⚠ 手動（CVE 監視 + Image 更新） | 🟡 |
| NFR-OPS-007 | 設定変更プロセス | (D) **IaC（Terraform）+ レビュー** | ✅ | ⚠ Realm は別管理（Admin Console / API） | 🟡 |
| NFR-OPS-008 | インシデント対応体制 | (TBD) **24/7 / 営業時間のみ** | ✅ AWS Premium Support | ⚠ 自前 or RHBK Premium | 🔴 |
| NFR-OPS-009 | 運用工数（人月） | (D) **Cognito: 1 人月 / Keycloak: 21 時間/月** | ✅ ほぼ不要 | ⚠ 月 N 時間（[ADR-006](../adr/006-cognito-vs-keycloak-cost-breakeven.md)） | 🟡 |
| NFR-OPS-010 | デプロイ自動化（CI/CD） | (D) **必須** | ✅ Terraform | ✅ Terraform + Docker | 🟡 |
| NFR-OPS-011 | テナント追加の運用 SLA | (TBD) **N 営業日以内** | ✅ | ✅ | 🔴 |

**ヒアリング論点**: NFR-OPS-008（24/7 サポート）が **RHBK 採用判断**（[ADR-015](../adr/015-rhbk-validation-deferred.md)）の決め手の 1 つ。

---

## 7. NFR-COMPLIANCE（コンプライアンス）

| ID | 要件 | 推奨値 | Cognito | Keycloak | 状態 |
|----|------|------|--------|----------|:---:|
| NFR-COMP-001 | 個人情報保護法対応 | (D) **必須** | ✅ | ✅ | 🟡 |
| NFR-COMP-002 | GDPR / CCPA（海外展開時） | (TBD) | ✅ | ✅ | 🔴 |
| NFR-COMP-003 | SOC 2 Type II | (TBD) | ✅ AWS 認定 | ⚠ 自前運用責任 | 🔴 |
| NFR-COMP-004 | ISO 27001 | (TBD) | ✅ AWS 認定 | ⚠ 自前運用責任 | 🔴 |
| NFR-COMP-005 | PCI DSS（金融） | (TBD) | ✅ AWS 認定 | ⚠ 自前 | 🔴 |
| NFR-COMP-006 | FIPS 140-2 認定 | (TBD) | ⚠ FIPS Endpoint 利用 | ⚠ **RHBK 必須** | 🔴 |
| NFR-COMP-007 | 監査ログ保存期間（法令要件） | (TBD) **業種次第（〜10 年）** | ✅ S3 ライフサイクル | ✅ S3 ライフサイクル | 🔴 |
| NFR-COMP-008 | データ所在地（リージョン制限） | (TBD) **国内 / 特定リージョン** | ✅ リージョン選択 | ✅ リージョン選択 | 🔴 |
| NFR-COMP-009 | 個人データ削除権（GDPR Right to Erasure） | (TBD) | ✅ AdminDeleteUser | ✅ Cascade Delete | 🟡 |
| NFR-COMP-010 | アクセス監査の追跡可能性 | (D) **全認証イベント記録** | ✅ CloudTrail | ✅ Event Listener | 🟡 |
| NFR-COMP-011 | 暗号鍵のローテーション | (D) **年 1 回以上** | ✅ KMS 自動 | ⚠ Realm Key Rotation 設定 | 🟡 |

**ヒアリング論点**: NFR-COMP-006（FIPS）が **RHBK 必要要因**。NFR-COMP-008（データ所在地）が **リージョン設計の決め手**。

---

## 8. NFR-COST（コスト）

| ID | 要件 | 推奨値 | Cognito | Keycloak (OSS) | Keycloak (RHBK) | 状態 |
|----|------|------|--------|----------|----------------|:---:|
| NFR-COST-001 | 初期構築費 | — | $5,000 | $30,000 | $30,000 + ライセンス | ✅ |
| NFR-COST-002 | 月額固定インフラ費 | — | $0 | ~$987（Option B + ADR-012）| ~$987 | ✅ |
| NFR-COST-003 | MAU あたりコスト（連携） | — | $0.015 / MAU | $0 | $0 | ✅ |
| NFR-COST-003-PLUS | **Cognito Plus ティア追加課金**（FR-AUTH-011 / FR-MFA-002 / FR-MFA-006 のいずれか Must の場合）| — | **+$0.02 / MAU**（無料枠なし、2024-12〜） | — | — | 🟡 |
| NFR-COST-004 | DR 追加月額 | — | $0.50 + MAU | $890 | $890 + RHBK サブスク | ✅ |
| NFR-COST-005 | 運用人件費 | (D) | ~$0 | ~$1,680/月 | ~$840/月（半減想定） | 🟡 |
| NFR-COST-006 | RHBK サブスクリプション | (TBD) | — | — | $5,000〜30,000/年/ノード | 🔴 |
| NFR-COST-007 | 損益分岐 MAU（連携のみ）| — | — | **175,000** ([ADR-006](../adr/006-cognito-vs-keycloak-cost-breakeven.md)) | **〜600,000**（RHBK 採用時） | ✅ |
| NFR-COST-007-PLUS | 損益分岐 MAU（**Plus ティア利用時** $0.035/MAU）| — | — | **〜75,000**（[ADR-006](../adr/006-cognito-vs-keycloak-cost-breakeven.md) §「Plus ティア採用時」） | — | ✅ |
| NFR-COST-008 | 3 年 TCO（10 万 MAU 想定） | — | $54K | $124K | $200K+ | ✅ |
| NFR-COST-009 | 3 年 TCO（50 万 MAU 想定） | — | $270K | $124K | $200K+ | ✅ |

**ヒアリング論点**: NFR-COST-006（RHBK 予算）と NFR-COMP-006（FIPS 要否）はセット。詳細: [keycloak-upstream-vs-rhbk.md](../reference/keycloak-upstream-vs-rhbk.md)

---

## 9. NFR-MIG（移行性）

| ID | 要件 | 推奨値 | Cognito | Keycloak | 状態 |
|----|------|------|--------|----------|:---:|
| NFR-MIG-001 | 既存認証システムからのユーザー移行 | (TBD) | ✅ ImportUsers + Lambda Trigger | ✅ Realm Import / SPI | 🔴 |
| NFR-MIG-002 | パスワード移行（ハッシュ持ち越し） | (TBD) | ⚠ ハッシュ形式制約 | ✅ Custom Hash Provider | 🔴 |
| NFR-MIG-003 | ベンダーロックイン回避 | (D) **OIDC 標準準拠** | ⚠ AWS 依存 | ✅ OSS / 移行可能 | ✅ |
| NFR-MIG-004 | データエクスポート | (D) **必要時に可能** | ✅ ListUsers + S3 Export | ✅ Realm Export | 🟡 |
| NFR-MIG-005 | 段階的移行（並行稼働） | (D) **可能** | ✅ | ✅ | 🟡 |

---

## 10. ヒアリング優先度マトリクス

要件定義時の確認すべき順位（プラットフォーム選定への影響度別）:

### 🔥 最重要（プラットフォーム選定に直結）

| ID | 要件 | 影響 |
|----|------|------|
| NFR-SCL-001 | MAU スケール（1〜3 年） | コスト損益分岐 |
| NFR-AVL-001 | SLA（99.9 / 99.95 / 99.99%） | Keycloak HA 設計 / RHBK 必要性 |
| NFR-DR-001 / 002 | RTO / RPO | DR コスト差 |
| NFR-COMP-006 | FIPS 認定 | RHBK 必須要因 |
| NFR-COMP-008 | データ所在地 | リージョン選定 |

### 🟡 重要（運用設計に直結）

| ID | 要件 | 影響 |
|----|------|------|
| NFR-OPS-008 | サポート体制 | RHBK 商用サポート要否 |
| NFR-OPS-003 | ログ保存期間 | コンプライアンス連動 |
| NFR-OPS-005 | バージョンアップ方針 | Keycloak 運用負荷 |
| NFR-COST-006 | RHBK 予算 | 上記と連動 |
| NFR-PERF-002 | スループット | スケール設計 |

### 🟢 デフォルト承認系（推奨値が妥当か確認）

| カテゴリ | 例 |
|---------|-----|
| トークン TTL | NFR-SEC-004 / 005 / 006 |
| バックアップ | NFR-DR-004 / 005 |
| 監視・アラート | NFR-OPS-001 / 002 |
| 暗号化 | NFR-SEC-001 / 002 / 003 |

---

## 11. 関連ドキュメント

- [functional-requirements.md](functional-requirements.md): 機能要件
- [keycloak-network-architecture.md](../common/keycloak-network-architecture.md): ネットワーク要件詳細
- [keycloak-upstream-vs-rhbk.md](../reference/keycloak-upstream-vs-rhbk.md): RHBK 比較
- [ADR-006](../adr/006-cognito-vs-keycloak-cost-breakeven.md): コスト損益分岐
- [ADR-011](../adr/011-auth-frontend-network-design.md): 前段ネットワーク設計
- [ADR-013](../adr/013-cloudfront-waf-ip-restriction.md): CloudFront + WAF
- [ADR-015](../adr/015-rhbk-validation-deferred.md): RHBK 検証先送り
