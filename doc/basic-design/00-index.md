# 基本設計 ドキュメント目録

作成: 2026-07-24 / 基本設計 Wave 1〜3 完了時点(初版)

## 読み順

1. [00-basic-design-plan.md](00-basic-design-plan.md) — 計画書(単元分割 U1〜U10 + 暫定前提 P-01〜18 + 体制)
2. [01-architecture-baseline.md](01-architecture-baseline.md) — **Baseline v1(前提 SSOT)**: P-01〜P-18 凍結表 / 6 アカウント体系 / コア・エッジ基準 / **PoC・契約前ゲート表(G-* 9 種)** / 用語注意
3. 各設計書(02〜10)— 冒頭に「前提: Baseline v1」、決定は D-Ux-nn 採番、末尾に未決事項と他単元への引き渡し

## 設計書一覧

| # | ファイル | 単元 | 主な決定 |
|---|---------|------|---------|
| 02 | [02-keycloak-logical-design.md](02-keycloak-logical-design.md) | U2 Keycloak 論理 | Realm/Organizations 構成・2-tier 間フェデ(idpkc-oidc01)・Flow 5 系統・SPI 3 JAR 4 機能・Protocol Mapper・User Profile(SSOT=U3 D3-01)・1000+ IdP 制約 7 点 |
| 03 | [03-identity-provisioning-design.md](03-identity-provisioning-design.md) | U3 ID・プロビジョニング | 3 階層識別子 + idmap DB・プロビ 6 経路(provisioned_by 6 値)・アプリ発 CRUD=専用 API 層(D3-05)・**SCIM 自作 Facade(D3-11)**・S1-S10 + 3 段階削除・契約前ゲート追跡 |
| 04 | [04-auth-ux-design.md](04-auth-ux-design.md) | U4 認証体験・UX | Identifier-First ログイン(IdP 一覧非表示)・ブランディング A・MFA 4 ケース UX・Landing Pattern 1(判定=エンタイトルメント API)・**Sorry=基盤側 SPA 主実装**・A11y |
| 05 | [05-token-session-authz-design.md](05-token-session-authz-design.md) | U5 トークン・認可 | クレーム辞書(Stage 1 + **sid 確定**)・TTL 最終(AT 30 分)・Token Exchange Pattern 2/3・Revocation/ITDR L4 連携・**Back-Channel Logout 採用**・RP 実装ガイド(§5.6.6 Sorry 規約含む)・idm:* スコープ |
| 06 | [06-infra-network-design.md](06-infra-network-design.md) | U6 インフラ・NW | **A 部(自管理)/B 部(他組織要求仕様)の 2 部構成**・6 アカウント + クロスアカウント 6 経路・ROSA HCP×2(Machine Pool 2 系統)・Egress O-10(zero-egress 積極検討)・Aurora 直結(プール 30 等値)・/admin 3 層 + hostname-admin・REQ-IN-01〜12/REQ-OUT-01〜06 |
| 06a | [06a-network-flow-diagrams.md](06a-network-flow-diagrams.md) | U6 付属 | **ネットワークフロー詳細図(mermaid)**: 全体図(全フロー ID: B-I1〜/B-O1〜/I-I1〜/I-O1〜 + 追加 8 系統)・**ROSA HCP 内部詳細図(初出: 2 Machine Pool / RH CP 通信 / OVN IP レンジ)**・抜けチェック結果 |
| 07 | [07-security-compliance-design.md](07-security-compliance-design.md) | U7 セキュリティ | KMS 3 階層 6 Acct 写像・**JWT 署名=Realm Key 90 日**・ITDR Broker 集約(Phase 1a→1b)・Log scrubbing 辞書 M-1〜14・Golden 検知 4 シグナル・IRSA 規約・**PAM 統合(ADR-040)**・PCI ギャップ 3 点・zero-egress セキュリティ推奨 |
| 08 | [08-availability-dr-design.md](08-availability-dr-design.md) | U8 可用性・DR | **Realm Export 全廃 → 復元 2 経路(IaC 再適用 + Aurora Global)**・パイロットライト(KC Scale 0)・RTO 1h 条件付き成立(5 条件)・RB-DR-00〜05・REQ-DR-01〜05 |
| 09 | [09-operations-observability-design.md](09-operations-observability-design.md) | U9 運用・監視・IaC | OTel + IdP 数関数監視・SLO/Burn Rate・ログ 3 層 + SIEM・**Runbook 35 冊 + 禁則 K-1〜11**・IaC 2 層(**keycloak-config-cli 不採用**)・CI/CD(GitHub Actions/GitOps/ECR)・IdP オンボーディング 6 ステップ・**Canary=弊社監査 Acct** |
| 10 | [10-integration-migration-design.md](10-integration-migration-design.md) | U10 連携・移行 | ServiceNow パターン ②(CL-SN-01/並走 4 Phase/削除連鎖 T-1〜5)・idm-api v1(OpenAPI×2 デプロイ + /api/me/apps)・Webhook(HMAC+DLQ)・移行 4 集団(PW ハッシュ判定・legacy_user_id 廃止)・DSAR Phase 1 手動 |

## research/(調査・検討の一次記録)

- [research/rosa-hcp-adoption-research.md](research/rosa-hcp-adoption-research.md) — ROSA HCP 採用調査(HCP 一択 / 大阪対応 / RHBK サブスク内包 / IRSA / コスト)+ ADR-056 改訂骨子
- [research/keycloak-1000idp-scalability-research.md](research/keycloak-1000idp-scalability-research.md) — 1000+ IdP 条件付き成立(必須対策 7 点 + PoC P-1〜P-7)
- [research/rosa-hcp-machine-pool-egress-notes.md](research/rosa-hcp-machine-pool-egress-notes.md) — ユーザー検討: HCP Infra Node 不在 / Machine Pool 役割分離 / zero-egress / Aurora プール等値化

## 運用ルール

- **前提変更時**: 01 Baseline の P 表のみ差し替え → 「変更時の影響単元」列で影響先を特定 → 該当設計書を差分改訂
- **整合性管理**: Wave 完了ごとに横断レビューを実施(Wave 1: 2026-07-23 / Wave 2〜3: 2026-07-24 済み)。ADR・§C-7 への反映は各レビューの「ADR 反映一覧」に従う
- **§C-7 との関係**: §C-7(proposal/common/07)は要件定義側 SSOT として維持し、実装詳細は本ディレクトリへ委譲(2026-07-24 一括改訂)
- ADR-040(PAM)/ADR-036(Customer Audit)は別スレッド管理 — 本ディレクトリからは参照のみ
