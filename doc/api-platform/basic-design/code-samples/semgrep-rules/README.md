# semgrep-rules — アプリコード静的解析ルールセット

アプリコード（多言語）の認証実装漏れ・JWT 検証バグを **AST パターン**で検出する Semgrep ルール。
[04 章 静的解析ガイドライン](../../04-static-analysis-guidelines.md) §4.4 の実装物で、
死守事項 **SA-2**（アプリコードは Semgrep）/ **SA-3**（検知は deploy ブロック）に対応する。

構文は 04 章 §4.4.1 / [§C-6.6.6](../../../proposal/common/06-external-api-auth-architecture.md) で
検証済み（`id` / `pattern`（`pattern-either` / `pattern-not` / `patterns`）/ `message` /
`severity`（ERROR / WARNING / INFO）/ `languages` / `metadata`）。

## 各ルールの意味

| ファイル | ルール ID | 対象言語 | 検出内容 | 漏れパターン | severity |
|---|---|---|---|:---:|---|
| `python-auth.yaml` | `fastapi-missing-auth-middleware` | Python | FastAPI app に `add_middleware(AuthMiddleware, ...)` 欠落 | **P6** | ERROR |
| `python-auth.yaml` | `jwt-decode-without-verify` | Python | `verify=False` / `algorithms=["none"]` / 鍵未指定の `jwt.decode` | **P5** | ERROR |
| `python-auth.yaml` | `missing-tenant-validation` | Python | path の `tenant_id` を JWT クレームと未照合 | **P3** | ERROR |
| `nodejs-auth.yaml` | `express-route-missing-auth` | JS / TS | `/api/` route に `authMiddleware` 欠落 | **P6** | ERROR |
| `java-auth.yaml` | `spring-controller-missing-preauthorize` | Java | `@RestController` メソッドに `@PreAuthorize` / `@Secured` 欠落 | **P6** | WARNING |

> 漏れパターンは [§C-API-6 §C-6.6.1](../../../proposal/common/06-external-api-auth-architecture.md) の 6 分類:
> **P3** = Authorizer 通過後のアプリ内 2 段検証（scope / tenant）欠如、
> **P5** = JWT 検証ロジックのバグ、
> **P6** = ALB / Function URL で IAM/OIDC 設定なし かつアプリコード検証も不在。
> Static Code レイヤー（L3）は L1/L2（IaC/Config）で漏れる **P3 / P5 / P6** を担保する（§C-6.6.3）。

## `semgrep ci` 実行

```bash
# 自作ルールのみ（このディレクトリ全体）
semgrep ci --config .

# 言語別に個別実行
semgrep ci --config python-auth.yaml
semgrep ci --config nodejs-auth.yaml
semgrep ci --config java-auth.yaml

# ローカル開発時（差分ではなく全走査）
semgrep --config . path/to/src
```

`semgrep ci` は ERROR レベルの検知があると non-zero exit で終了し、
CI を fail させて deploy をブロックする（SA-3、04 章 §4.5.2）。

## owasp / security-audit pack の併用

自作ルールに加え、公式レジストリの標準 pack を併用する（04 章 §4.4.3）:

```bash
# 自作ルール + owasp-top-ten + security-audit を同時適用
semgrep ci \
  --config . \
  --config p/owasp-top-ten \
  --config p/security-audit
```

- `p/owasp-top-ten` — OWASP Top 10 相当の一般脆弱性
- `p/security-audit` — 幅広いセキュリティ監査ルール

自作ルール（本ディレクトリ）は「本標準固有の認証実装漏れ（P3/P5/P6）」を担い、
汎用脆弱性は公式 pack に委ねる住み分けとする。

## CI 統合（04 章 §4.5）

| CI | 組み込み |
|---|---|
| **GitHub Actions** | `semgrep ci`（`returntocorp/semgrep` action）を PR / push トリガで実行 |
| **GitLab CI** | Semgrep SAST template を include |
| **CodeBuild / CodePipeline** | buildspec に `semgrep ci` step を追加 |

GitHub Actions 例:

```yaml
- name: Semgrep
  uses: returntocorp/semgrep-action@v1
  with:
    config: >-
      semgrep-rules/
      p/owasp-top-ten
      p/security-audit
# ERROR 検知時は step が non-zero exit → PR ブロック（SA-3）
```

開発者ローカルでは pre-commit hook（04 章 §4.6）で同じルールセットを実行し、
CI 失敗の往復を削減する（`semgrep --config semgrep-rules/`）。

## 運用注意（04 章 §4.4 / §4.7）

- **段階導入**: False positive 多発リスクがあるため、既存コードは warn → 新規は error。
- **言語別整備**: Python / Node / Java を本セットで整備済み。Go 等の追加は BD-Q-04（04 章 §4.10）。
- **例外**: 誤検知・正当な例外は `# nosemgrep: <rule-id>` ではなく、
  §4.7 の例外承認プロセス（チケット ID 付き台帳化）を経ること。

## 参照

- [04 章 静的解析ガイドライン](../../04-static-analysis-guidelines.md) §4.4 / §4.5
- [§C-API-6 §C-6.6.6](../../../proposal/common/06-external-api-auth-architecture.md) — L3 Static Code 実装サンプル
- [Semgrep rule syntax](https://semgrep.dev/docs/writing-rules/rule-syntax)（構文確認元）
