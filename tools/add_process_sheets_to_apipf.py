#!/usr/bin/env python3
"""認証実装確認処理 — 処理設計セクションを apipf.xlsx へ追記するジェネレータ

SSOT: doc/api-platform/basic-design/research/process-design-template.md
対象: doc/excel/apipf.xlsx（基本設計書。**既存 17 シートは触らない**）

追記するもの:
  18_処理一覧 / 19_処理共通仕様 / 処理シート 33 枚（巡回-*, 全量-*, 確認-*, 通知-*, 運用-*, 連携-*）

⚠ 再実行すると**追記分のシートのみ**作り直す（記入済みの処理シートは失われる）。
   既存 17 シート（01〜17）には一切手を触れない。
   実行前に Excel を閉じること。バックアップ: apipf.backup-*.xlsx
"""
from __future__ import annotations

import pathlib

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

OUT = pathlib.Path(__file__).resolve().parents[1] / "doc" / "excel" / "apipf.xlsx"
KEEP = 17  # 既存の基本設計シート数（01〜17）。これらは変更しない

# ---------------------------------------------------------------- styles
TITLE = Font(bold=True, size=14, color="FFFFFF")
TITLE_FILL = PatternFill("solid", fgColor="2F5597")
SEC = Font(bold=True, size=11, color="FFFFFF")
SEC_FILL = PatternFill("solid", fgColor="8EA9DB")
HDR = Font(bold=True, size=10)
HDR_FILL = PatternFill("solid", fgColor="D9E1F2")
LBL_FILL = PatternFill("solid", fgColor="F2F2F2")
TODO_FILL = PatternFill("solid", fgColor="FFF2CC")
BASE = Font(size=10)
LINK = Font(size=10, color="0563C1", underline="single")
WRAP = Alignment(vertical="top", wrap_text=True)
TOP = Alignment(vertical="top")
thin = Side(style="thin", color="BFBFBF")
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)

# ---------------------------------------------------------------- data
from process_catalog import GROUPS, PROCESSES  # noqa: E402

SEC_TABLES = {
    "2. 入力（I）": ["項目", "型", "必須", "取得元", "説明・例"],
    "3. 出力（O）": ["項目", "型", "出力先", "説明・例"],
    "4. 処理手順": ["#", "処理内容", "補足・参照"],
    "6. 例外・異常系": ["ケース", "検知方法", "動作", "通知", "参照"],
    "9. ログ・メトリクス": ["種別", "名称・項目", "内容", "備考"],
    "11. 未決事項": ["ID", "内容", "確認先", "期限"],
}


def style_title(ws, text, span=5):
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=span)
    c = ws.cell(row=1, column=1, value=text)
    c.font, c.fill, c.alignment = TITLE, TITLE_FILL, Alignment(vertical="center")
    ws.row_dimensions[1].height = 26


def section(ws, row, text, span=5):
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=span)
    c = ws.cell(row=row, column=1, value=text)
    c.font, c.fill = SEC, SEC_FILL
    return row + 1


def kv(ws, row, label, value, todo=False, span=5):
    lc = ws.cell(row=row, column=1, value=label)
    lc.font, lc.fill, lc.border, lc.alignment = HDR, LBL_FILL, BOX, WRAP
    ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=span)
    vc = ws.cell(row=row, column=2, value=value)
    vc.font, vc.border, vc.alignment = BASE, BOX, WRAP
    if todo:
        vc.fill = TODO_FILL
    for col in range(3, span + 1):
        ws.cell(row=row, column=col).border = BOX
    return row + 1


def table(ws, row, headers, blank_rows=3, rows=None):
    """rows を与えると白セルで記入済みとして描画し、そのあとに blank_rows 行の黄色枠を置く。"""
    for i, h in enumerate(headers, start=1):
        c = ws.cell(row=row, column=i, value=h)
        c.font, c.fill, c.border, c.alignment = HDR, HDR_FILL, BOX, WRAP
    r = row + 1
    for data in (rows or []):
        for i in range(1, len(headers) + 1):
            v = data[i - 1] if i - 1 < len(data) else None
            c = ws.cell(row=r, column=i, value=v)
            c.font, c.border, c.alignment = BASE, BOX, WRAP
        r += 1
    for rr in range(r, r + blank_rows):
        for i in range(1, len(headers) + 1):
            c = ws.cell(row=rr, column=i)
            c.border, c.fill, c.alignment = BOX, TODO_FILL, WRAP
    return r + blank_rows


def build_process_sheet(wb, p):
    pid, short, name = p["id"], p["sheet"], p["name"]
    summary, perm, seq, hint = p["summary"], p["perm"], p["seq"], p["hint"]
    # 詳細（process_catalog.py の d=... 。未記入の処理では空 dict）
    d = p.get("d") or {}

    def dv(key, default=""):
        v = d.get(key, default)
        return "\n".join(v) if isinstance(v, (list, tuple)) else v
    ws = wb.create_sheet(f"{pid}_{short}"[:31])
    ws.sheet_properties.tabColor = GROUPS[p["group"]][1]
    for col, w in zip("ABCDE", (22, 26, 20, 30, 46)):
        ws.column_dimensions[col].width = w

    style_title(ws, f"{pid}  {name}")
    r = 2
    r = section(ws, r, "0. 概要")
    r = kv(ws, r, "概要", summary)
    r = section(ws, r, "1. 基本情報")
    r = kv(ws, r, "系統", f"{p['group']}（{GROUPS[p['group']][0]}）")
    r = kv(ws, r, "実行契機", p["trigger"])
    r = kv(ws, r, "フロー内の位置", dv("position"), todo=not d.get("position"))
    r = kv(ws, r, "起動元", p["src"])
    r = kv(ws, r, "起動先", p["dst"])
    r = kv(ws, r, "呼び出し方式", p["mode"])
    r = kv(ws, r, "実行主体", p["actor"])
    r = kv(ws, r, "頻度・タイミング", p["freq"])
    r = kv(ws, r, "前提条件・事前状態", dv("pre"), todo=not d.get("pre"))
    r += 1
    r = section(ws, r, "2. 入力（I）")
    r = table(ws, r, SEC_TABLES["2. 入力（I）"], blank_rows=1 if d.get("inputs") else 3,
              rows=d.get("inputs"))
    r += 1
    r = section(ws, r, "3. 出力（O）")
    r = table(ws, r, SEC_TABLES["3. 出力（O）"], blank_rows=1 if d.get("outputs") else 3,
              rows=d.get("outputs"))
    r += 1
    r = section(ws, r, "4. 処理手順")
    if d.get("steps"):
        numbered = [[i, s[0], s[1] if len(s) > 1 else ""]
                    for i, s in enumerate(d["steps"], start=1)]
        r = table(ws, r, SEC_TABLES["4. 処理手順"], blank_rows=1, rows=numbered)
    else:
        r = table(ws, r, SEC_TABLES["4. 処理手順"], blank_rows=0)
        c = ws.cell(row=r, column=1, value=1)
        c.border, c.fill, c.alignment = BOX, TODO_FILL, WRAP
        c2 = ws.cell(row=r, column=2, value="")
        c2.border, c2.fill, c2.alignment = BOX, TODO_FILL, WRAP
        c3 = ws.cell(row=r, column=3, value=f"【設計時の要記載】{hint}")
        c3.border, c3.fill, c3.alignment = BOX, TODO_FILL, WRAP
        r += 1
        for extra in range(3):
            for i in range(1, 4):
                cc = ws.cell(row=r + extra, column=i)
                cc.border, cc.fill, cc.alignment = BOX, TODO_FILL, WRAP
        r += 3
    r += 1
    r = section(ws, r, "5. シーケンス（矢印記法。必要に応じて図を貼付）")
    ws.merge_cells(start_row=r, start_column=1, end_row=r + 4, end_column=5)
    sc = ws.cell(row=r, column=1, value=seq)
    sc.font, sc.border, sc.alignment = BASE, BOX, WRAP
    r += 6
    r = section(ws, r, "6. 例外・異常系")
    r = table(ws, r, SEC_TABLES["6. 例外・異常系"],
              blank_rows=1 if d.get("exceptions") else 3, rows=d.get("exceptions"))
    r += 1
    idem = d.get("idem") or ("", "")
    r = section(ws, r, "7. 冪等性・リトライ")
    r = kv(ws, r, "再実行時の振る舞い", idem[0], todo=not idem[0])
    r = kv(ws, r, "状態更新のタイミング", idem[1], todo=not idem[1])
    r += 1
    r = section(ws, r, "8. 権限・エンドポイント")
    r = kv(ws, r, "権限 / エンドポイント", perm)
    r = kv(ws, r, "認証方式・補足", dv("authnote"), todo=not d.get("authnote"))
    r += 1
    r = section(ws, r, "9. ログ・メトリクス")
    r = table(ws, r, SEC_TABLES["9. ログ・メトリクス"],
              blank_rows=1 if d.get("logs") else 2, rows=d.get("logs"))
    r += 1
    perf = d.get("perf") or ("", "")
    r = section(ws, r, "10. 性能・上限")
    r = kv(ws, r, "想定件数 / 所要時間", perf[0], todo=not perf[0])
    r = kv(ws, r, "上限・制約", perf[1], todo=not perf[1])
    r += 1
    r = section(ws, r, "11. 未決事項")
    table(ws, r, SEC_TABLES["11. 未決事項"],
          blank_rows=1 if d.get("opens") else 2, rows=d.get("opens"))
    return ws.title


def build_index_sheet(wb, titles):
    """18_処理一覧（本セクションのハブ）"""
    ws = wb.create_sheet("18_処理一覧")
    ws.sheet_properties.tabColor = "2F5597"
    for col, w in zip("ABCDEFGHIJ", (10, 30, 22, 20, 30, 30, 10, 44, 20, 12)):
        ws.column_dimensions[col].width = w
    style_title(ws, "処理一覧（処理設計セクションのハブ）", span=10)
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=10)
    note = ws.cell(row=2, column=1, value=(
        "本シート以降は「処理設計」セクション（シート 18〜）。1 処理 = 1 シートで I/O・シーケンス・例外を定義する。"
        "構成図は 03、リソース一覧は 04、データ定義は 07、IAM は 08、コストは 16/17 を参照（重複記載しない）。"
        "設計の正は md（doc/api-platform/basic-design/ 10〜18 章）。"
        "⚠ 本セクションは tools/add_process_sheets_to_apipf.py の生成物。"
        "記入は Excel でなく tools/process_catalog.py の d=dict(...) に書くこと（再生成で消えるため）。"))
    note.font, note.alignment = BASE, WRAP
    ws.row_dimensions[2].height = 40
    r = 4
    headers = ["処理ID", "処理名", "系統", "実行契機", "起動元", "起動先", "方式", "概要", "シート", "記入状態"]
    for i, h in enumerate(headers, start=1):
        c = ws.cell(row=r, column=i, value=h)
        c.font, c.fill, c.border, c.alignment = HDR, HDR_FILL, BOX, WRAP
    ws.freeze_panes = ws.cell(row=r + 1, column=1)
    for i, p in enumerate(PROCESSES):
        rr = r + 1 + i
        vals = (p["id"], p["name"], f"{p['group']}（{GROUPS[p['group']][0]}）", p["trigger"],
                p["src"], p["dst"], p["mode"], p["summary"])
        for j, v in enumerate(vals, start=1):
            c = ws.cell(row=rr, column=j, value=v)
            c.font, c.border, c.alignment = BASE, BOX, WRAP
        t = titles[i]
        c = ws.cell(row=rr, column=9, value=t)
        c.hyperlink = f"#'{t}'!A1"
        c.font, c.border, c.alignment = LINK, BOX, WRAP
        done = bool(p.get("d"))
        c = ws.cell(row=rr, column=10, value="✅ 記入済" if done else "記入待ち")
        c.font, c.border, c.alignment = BASE, BOX, WRAP
        if not done:
            c.fill = TODO_FILL
    ws.auto_filter.ref = f"A{r}:J{r + len(PROCESSES)}"


def build_common_spec_sheet(wb):
    """19_処理共通仕様（全処理に共通する規約・性能・監視）"""
    ws = wb.create_sheet("19_処理共通仕様")
    ws.sheet_properties.tabColor = "2F5597"
    for col, w in zip("ABCDE", (24, 60, 30, 20, 20)):
        ws.column_dimensions[col].width = w
    style_title(ws, "処理共通仕様（全処理に適用）")
    r = 2
    r = section(ws, r, "1. 全処理共通の規約")
    r = table(ws, r, ["項目", "規約", "参照", "", ""], blank_rows=0)
    commons = [
        ("命名規約", "", "04 章 / 組織標準"),
        ("ログ出力", "相関 ID を必ず出力。トークン・資格情報はマスクする", "06 章 OBS-1〜4"),
        ("ログ保持期間", "", "WBS A14-i"),
        ("エラー処理の原則", "アカウント単位・endpoint 単位で try-catch し、1 件の失敗で全体を止めない", "18 §18.5.2"),
        ("リトライ", "非同期呼び出しは Lambda 標準リトライ（2 回）+ DLQ", "18 §18.5.2"),
        ("冪等性", "at-least-once。状態（lastArtifactVersions）は後続処理の成功後にのみ更新", "18 §18.5.2"),
        ("タイムアウト", "", "設計時に確定"),
        ("環境変数", "", "設計時に確定"),
        ("タグ", "app-id / env / cost-center / owner を必須付与", "03 章 BL-1"),
        ("宛先 allowlist", "外向き通信の宛先は台帳の baseUrl と設定済み token URL のみ（コードで強制）", "10 §10.1.6 代償統制"),
    ]
    for i, (k, v, ref) in enumerate(commons):
        for j, val in enumerate((k, v, ref, "", "")):
            c = ws.cell(row=r + i, column=j + 1, value=val)
            c.font, c.border, c.alignment = BASE, BOX, WRAP
            if j == 1 and not val:
                c.fill = TODO_FILL
    r += len(commons) + 1
    r = section(ws, r, "2. 性能・上限")
    r = table(ws, r, ["項目", "値・方針", "根拠", "備考", ""], blank_rows=5)
    r += 1
    r = section(ws, r, "3. 監視・アラーム（メタ監視 MM-1〜5 ほか）")
    r = table(ws, r, ["ID", "検知対象", "手段", "閾値", "通知先"], blank_rows=6)
    r += 1
    r = section(ws, r, "4. 参照（重複記載しないもの）")
    for label, ref in (("構成図 / リソース一覧", "シート 03・04"), ("データ定義（台帳・認証構成情報）", "シート 07"),
                       ("IAM・権限", "シート 08"), ("コスト", "シート 16・17"),
                       ("設計判断 / 未決事項", "シート 10・11")):
        r = kv(ws, r, label, ref)


def main():
    from openpyxl import load_workbook
    if not OUT.exists():
        raise SystemExit(f"{OUT} が見つかりません")
    wb = load_workbook(OUT)
    base = wb.sheetnames[:KEEP]
    # 追記分のみ作り直す（既存 17 シートには触れない）
    for name in wb.sheetnames[KEEP:]:
        del wb[name]
    titles = [build_process_sheet(wb, p) for p in PROCESSES]
    build_index_sheet(wb, titles)
    build_common_spec_sheet(wb)
    wb._sheets = [wb[t] for t in base + ["18_処理一覧", "19_処理共通仕様"] + titles]
    wb.save(OUT)
    print(f"updated {OUT}: 既存 {len(base)} + 追記 {len(wb.sheetnames) - len(base)} = {len(wb.sheetnames)} sheets")


if __name__ == "__main__":
    main()
