#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
設計書の整合性を機械照合する。手作業で 4 回繰り返した検査を自動化したもの。

検査:
  A サービス網羅  コスト見積り（=使用サービスの全量）に対し、各単元で言及ゼロのものを検出
  B 禁則の逆参照  禁則 K-* が主管単元の本文から参照されているか
  C 前提の追跡    前提 P-* の「影響単元」が実際にその前提 ID を参照しているか
  D 監視の網羅    監視観点 8 分類それぞれに U9 のメトリクスが存在するか
  E Runbook 整合  必須 N 冊の定義が 00a と U9 で一致するか
  F ADR の配布    ADR が設計書から参照されているか / ADR 索引に登録されているか

使い方: python3 tools/check_design_consistency.py [--strict]
  --strict を付けると検出時に exit 1（CI 用）
"""
import io, os, re, sys, glob
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BD = os.path.join(ROOT, "doc/basic-design")

def read(p):
    try: return io.open(p, encoding="utf-8").read()
    except OSError: return ""

UNITS = {}
for p in sorted(glob.glob(os.path.join(BD, "0[1-9]*.md"))) + sorted(glob.glob(os.path.join(BD, "10*.md"))):
    b = os.path.basename(p)
    if re.match(r"^(0[1-9]|10)-", b): UNITS[b[:2]] = read(p)

findings = []
def add(cat, msg): findings.append((cat, msg))

# ---- A サービス網羅 ----------------------------------------------------
SVC = {
 "EBS": ["EBS", "gp3"], "Aurora": ["Aurora"], "DynamoDB": ["DynamoDB"],
 "Secrets Manager": ["Secrets Manager"], "ACM Private CA": ["Private CA", "ACM PCA"],
 "AWS Backup": ["AWS Backup", "Backup Vault"], "EventBridge": ["EventBridge"],
 "Lambda": ["Lambda"], "API Gateway": ["API Gateway", "API GW"], "SES": ["SES"],
 "OpenSearch": ["OpenSearch"], "CloudWatch Logs": ["CloudWatch Logs", "CloudWatch ログ"],
 "Route 53": ["Route 53", "Route53"], "VPC エンドポイント": ["VPC エンドポイント", "VPCエンドポイント", "VPCE"],
 "CloudFront": ["CloudFront"], "WAF": ["WAF"], "KMS": ["KMS"], "S3": ["S3"],
 "ALB": ["ALB"], "NLB": ["NLB"], "PrivateLink": ["PrivateLink"],
}
# 主管単元（ここに無ければ設計漏れ）
OWNER = {"EBS": ["06"], "DynamoDB": ["06"], "Secrets Manager": ["06", "07"],
         "ACM Private CA": ["06"], "AWS Backup": ["08"], "EventBridge": ["06"],
         "Lambda": ["06"], "API Gateway": ["06"], "SES": ["06"], "OpenSearch": ["09"],
         "CloudWatch Logs": ["09"], "Route 53": ["06"], "VPC エンドポイント": ["06"]}
for svc, kws in SVC.items():
    for u in OWNER.get(svc, []):
        if u in UNITS and not any(k in UNITS[u] for k in kws):
            add("A サービス網羅", f"{svc} が主管単元 U{int(u)} に言及ゼロ")
    # DR 対象かどうか（U8）
    if svc in ("Secrets Manager", "ACM Private CA", "EventBridge", "SES", "DynamoDB") \
       and "08" in UNITS and not any(k in UNITS["08"] for k in kws):
        add("A サービス網羅", f"{svc} が U8（DR）に言及ゼロ — 切替時の扱いが未定義の可能性")

# ---- B 禁則の逆参照 ----------------------------------------------------
KOWNER = {"K-1": ["02", "08"], "K-2": ["06", "08"], "K-3": ["07", "08"], "K-4": ["08"],
          "K-5": ["08", "09"], "K-6": ["02"], "K-7": ["07"], "K-8": ["02"],
          "K-9": ["02", "09"], "K-10": ["06"], "K-11": ["02", "08"], "K-12": ["09"], "K-13": ["07", "09"]}
for k, owners in KOWNER.items():
    if not any(k in UNITS.get(u, "") for u in owners):
        add("B 禁則の逆参照", f"{k} が主管単元（{'/'.join('U'+str(int(o)) for o in owners)}）から参照されていない")

# ---- C 前提の追跡 ------------------------------------------------------
base = UNITS.get("01", "")
for pid, rest in re.findall(r"^\| \*{0,2}(P-\d+)\*{0,2} \|(.+)$", base, re.M):
    cells = [c.strip() for c in rest.split("|")]
    infl = cells[-2] if len(cells) >= 2 else ""
    for u in sorted(set(re.findall(r"U(\d+)", infl))):
        key = u.zfill(2)
        if key in UNITS and pid not in UNITS[key]:
            add("C 前提の追跡", f"{pid} の影響単元 U{u} が {pid} を参照していない")

# ---- D 監視の網羅（観点 8 分類）----------------------------------------
LENS = {
 "飽和": ["CPU", "メモリ", "ディスク", "接続プール", "コネクションプール", "スレッド"],
 "枯渇": ["クォータ", "サービス上限", "Service Quota", "レート上限"],
 "期限": ["有効期限", "残存有効期間", "証明書.*期限", "失効日"],
 "停止": ["ジョブ.*成否", "バッチ.*失敗", "実行失敗"],
 "滞留": ["DLQ", "滞留", "レプリケーション遅延", "キュー"],
 "逸脱": ["ドリフト", "drift"],
 "品質": ["エラー率", "レイテンシ", "Burn Rate", "p99"],
 "沈黙": ["無受信", "途絶", "ゼロ.*アラート", "来ない"],
}
u9 = UNITS.get("09", "")
for lens, kws in LENS.items():
    if not any(re.search(k, u9) for k in kws):
        add("D 監視の網羅", f"監視観点「{lens}」に対応するメトリクスが U9 に見当たらない")

# ---- E Runbook 整合 ----------------------------------------------------
a00 = read(os.path.join(BD, "00a-remaining-tasks-and-effort.md"))
def rb_set(txt):
    m = re.search(r"必須\s*(\d+)\s*冊[^（(]*[（(]([^）)]+)[）)]", txt)
    if not m: return None, None
    n = int(m.group(1)); body = m.group(2)
    cnt = 0
    for seg in re.findall(r"([A-Z]+)-(\d+)(?:[〜~](\d+))?", body):
        cnt += (int(seg[2]) - int(seg[1]) + 1) if seg[2] else 1
    for seg in re.findall(r"([A-Z]+)-((?:\d+/)+\d+)", body):
        cnt += len(seg[1].split("/")) - 1
    return n, cnt
for label, txt in (("00a", a00), ("U9", u9)):
    n, cnt = rb_set(txt)
    if n and cnt and n != cnt:
        add("E Runbook 整合", f"{label}: 「必須 {n} 冊」と記載だが列挙は {cnt} 冊")

# ---- F ADR の配布 ------------------------------------------------------
# 設計書 10 冊から参照されていない ADR を検出する。
# 「ADR で決めたのに設計へ配られていない」= 別名で二重起票される温床
#   （実例: ADR-047 の「暗号インベントリ」と D-U7-25 の「鍵インベントリ」が同一作業だった）
ADR_DIR = os.path.join(ROOT, "doc/adr")
# PoC 期・製品比較の記録。設計から参照されないのが正常
HISTORICAL = {"001","002","003","004","005","006","007","008","009","010",
              "011","012","013","014","015","016","032","058"}
# 意図的に無効化したもの（バナーで明示済み）
RETIRED_MARK = ("Superseded", "Scope Reduced", "凍結", "廃止", "Deprecated", "Out of Scope")
adr_index = read(os.path.join(ADR_DIR, "00-index.md"))
for fn in sorted(os.listdir(ADR_DIR)):
    m = re.match(r"^(\d{3})-(.+)\.md$", fn)
    if not m: continue
    num = m.group(1)
    body = read(os.path.join(ADR_DIR, fn))
    st = re.search(r"\*\*ステータス\*\*:\s*(.+)", body)
    status = st.group(1) if st else ""
    # 索引への登録漏れ（実例: ADR-061）
    if f"({num}-" not in adr_index and f"[{num}]" not in adr_index:
        add("F ADR の配布", f"ADR-{num} が ADR 索引（00-index.md）に未登録")
    if num in HISTORICAL: continue
    if any(k in status for k in RETIRED_MARK) or any(k in body[:1200] for k in RETIRED_MARK):
        continue  # 無効化済みは参照ゼロで正常
    if not any((f"adr/{num}-" in t) or (f"ADR-{num}" in t) for t in UNITS.values()):
        add("F ADR の配布", f"ADR-{num}（{status[:24]}）が設計書 10 冊から参照ゼロ")

# ---- 出力 --------------------------------------------------------------
by = defaultdict(list)
for c, m in findings: by[c].append(m)
print("=" * 66)
print("  設計整合性チェック")
print("=" * 66)
for c in ("A サービス網羅", "B 禁則の逆参照", "C 前提の追跡", "D 監視の網羅", "E Runbook 整合", "F ADR の配布"):
    items = by.get(c, [])
    print(f"\n■ {c}: {len(items)} 件")
    for m in items: print(f"   - {m}")
print(f"\n合計 {len(findings)} 件")
if "--strict" in sys.argv and findings: sys.exit(1)
