#!/usr/bin/env python3
"""認証実装確認処理 — 処理設計書（Excel）雛形ジェネレータ

SSOT: doc/api-platform/basic-design/research/process-design-template.md
出力: doc/excel/apipf-process-design.xlsx

PROCESSES を更新したら上記 md の処理カタログも同時に更新すること。
再実行すると出力ファイルを作り直す（記入済みの内容は失われるので注意）。
"""
from __future__ import annotations

import pathlib

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

OUT = pathlib.Path(__file__).resolve().parents[1] / "doc" / "excel" / "apipf-process-design.xlsx"

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


def table(ws, row, headers, blank_rows=3):
    for i, h in enumerate(headers, start=1):
        c = ws.cell(row=row, column=i, value=h)
        c.font, c.fill, c.border, c.alignment = HDR, HDR_FILL, BOX, WRAP
    for r in range(row + 1, row + 1 + blank_rows):
        for i in range(1, len(headers) + 1):
            c = ws.cell(row=r, column=i)
            c.border, c.fill, c.alignment = BOX, TODO_FILL, WRAP
    return row + 1 + blank_rows


def build_process_sheet(wb, p):
    pid, short, name = p["id"], p["sheet"], p["name"]
    summary, perm, seq, hint = p["summary"], p["perm"], p["seq"], p["hint"]
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
    r = kv(ws, r, "フロー内の位置", "", todo=True)
    r = kv(ws, r, "起動元", p["src"])
    r = kv(ws, r, "起動先", p["dst"])
    r = kv(ws, r, "呼び出し方式", p["mode"])
    r = kv(ws, r, "実行主体", p["actor"])
    r = kv(ws, r, "頻度・タイミング", p["freq"])
    r = kv(ws, r, "前提条件・事前状態", "", todo=True)
    r += 1
    for title, headers in list(SEC_TABLES.items())[:2]:
        r = section(ws, r, title)
        r = table(ws, r, headers)
        r += 1
    r = section(ws, r, "4. 処理手順")
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
    r = table(ws, r, SEC_TABLES["6. 例外・異常系"])
    r += 1
    r = section(ws, r, "7. 冪等性・リトライ")
    r = kv(ws, r, "再実行時の振る舞い", "", todo=True)
    r = kv(ws, r, "状態更新のタイミング", "", todo=True)
    r += 1
    r = section(ws, r, "8. 権限・エンドポイント")
    r = kv(ws, r, "権限 / エンドポイント", perm)
    r = kv(ws, r, "認証方式・補足", "", todo=True)
    r += 1
    r = section(ws, r, "9. ログ・メトリクス")
    r = table(ws, r, SEC_TABLES["9. ログ・メトリクス"], blank_rows=2)
    r += 1
    r = section(ws, r, "10. 性能・上限")
    r = kv(ws, r, "想定件数 / 所要時間", "", todo=True)
    r = kv(ws, r, "上限・制約", "", todo=True)
    r += 1
    r = section(ws, r, "11. 未決事項")
    table(ws, r, SEC_TABLES["11. 未決事項"], blank_rows=2)
    return ws.title


def build_common_sheets(wb, sheet_titles):
    # 00 表紙
    ws = wb.create_sheet("00_表紙・改訂履歴")
    for col, w in zip("ABCDE", (18, 30, 18, 30, 40)):
        ws.column_dimensions[col].width = w
    style_title(ws, "API 認証実装確認処理　処理設計書")
    r = 3
    for label in ("システム名", "文書名", "版", "作成日", "作成者", "承認者", "参照設計書（md）", "参照コミット"):
        default = {"システム名": "API プラットフォーム / 認証実装確認処理",
                   "文書名": "処理設計書（処理単位の I/O・シーケンス）",
                   "参照設計書（md）": "doc/api-platform/basic-design/10〜18 章"}.get(label, "")
        r = kv(ws, r, label, default, todo=not default)
    r += 1
    r = section(ws, r, "改訂履歴")
    table(ws, r, ["版", "日付", "改訂内容", "作成者", "承認者"], blank_rows=5)

    # 01 位置づけ・前提
    ws = wb.create_sheet("01_位置づけ・前提")
    for col, w in zip("ABCDE", (22, 30, 24, 30, 40)):
        ws.column_dimensions[col].width = w
    style_title(ws, "本書の位置づけ・前提")
    r = 2
    r = section(ws, r, "1. 目的と読者")
    r = kv(ws, r, "目的", "10〜18 章の設計を処理単位に分解し、実装・単体テスト・運用手順の起点とする")
    r = kv(ws, r, "読者", "実装担当 / テスト担当 / 運用担当 / レビュア")
    r = kv(ws, r, "上位設計との関係", "設計の正は md（10〜18 章）。本書と矛盾した場合は md が優先する")
    r += 1
    r = section(ws, r, "2. 前提条件")
    r = table(ws, r, ["ID", "前提", "根拠・参照", "確定状況", "備考"], blank_rows=0)
    presets = [
        ("前提1", "実行基盤は Lambda 3 本（対象検索 / 認証実装チェック / アラート検知）、すべて VPC 外配置", "10 §10.1.6 D-M-10-4", "確定"),
        ("前提2", "変更検知は App アカウントの認証構成情報（S3）の版数比較のみ（資材オンリー原則）", "17 §17.2 / ADR-061 追記 2026-08-21", "確定"),
        ("前提3", "実行モードは 2 つ（自動差分検査＝モード1 / 全量検査＝モード2：日次定期＋手動）", "18 §18.1", "確定"),
        ("前提4", "台帳・API 仕様は共通基盤アカウントの認証構成情報配置バケット（S3 ×1）に集約", "12 / 13 章", "確定"),
        ("前提5", "認証構成情報の配置漏れ・内容誤りは原則アプリ（ベンダー）責任", "17 §17.2.2 / D-M-17-8（顧客合意 M-Q-17-7）", "合意待ち"),
        ("前提6", "検査は実利用者と同じ経路（CloudFront + WAF）を通過する", "10 §10.1.6 経路 A", "確定"),
    ]
    for i, (pid, txt, ref, st) in enumerate(presets):
        for j, v in enumerate((pid, txt, ref, st, "")):
            c = ws.cell(row=r + i, column=j + 1, value=v)
            c.font, c.border, c.alignment = BASE, BOX, WRAP
    r += len(presets) + 1
    r = section(ws, r, "3. 用語")
    r = table(ws, r, ["用語", "意味", "参照", "", ""], blank_rows=4)

    # 02 全体構成
    ws = wb.create_sheet("02_全体構成")
    for col, w in zip("ABCDE", (26, 20, 46, 24, 20)):
        ws.column_dimensions[col].width = w
    style_title(ws, "全体構成（アカウント・リソース・通信経路）")
    r = 2
    r = section(ws, r, "1. リソース一覧（10 §10.1.5 より転記）")
    r = table(ws, r, ["リソース", "サービス", "役割", "配置アカウント", "詳細章"], blank_rows=10)
    r += 1
    r = section(ws, r, "2. 通信経路（10 §10.1.6 より転記）")
    r = table(ws, r, ["#", "経路", "中身", "通る境界", "必要な許可"], blank_rows=5)
    r += 1
    r = section(ws, r, "3. 構成図（貼付領域）")
    ws.merge_cells(start_row=r, start_column=1, end_row=r + 14, end_column=5)
    c = ws.cell(row=r, column=1, value="※ 10 章 §10.1.6 の AWS リソース構成図を貼り付ける")
    c.font, c.border, c.alignment = BASE, BOX, WRAP

    # 03 処理一覧
    ws = wb.create_sheet("03_処理一覧")
    for col, w in zip("ABCDEFGHI", (10, 30, 22, 20, 30, 30, 10, 44, 16)):
        ws.column_dimensions[col].width = w
    style_title(ws, "処理一覧（本書のハブ）", span=9)
    r = 3
    headers = ["処理ID", "処理名", "系統", "実行契機", "起動元", "起動先", "方式", "概要", "シート"]
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
        title = sheet_titles[i]
        c = ws.cell(row=rr, column=9, value=title)
        c.hyperlink = f"#'{title}'!A1"
        c.font, c.border, c.alignment = LINK, BOX, WRAP
    ws.auto_filter.ref = f"A{r}:I{r + len(PROCESSES)}"

    # 04 共通仕様
    ws = wb.create_sheet("04_共通仕様")
    for col, w in zip("ABCDE", (24, 60, 30, 20, 20)):
        ws.column_dimensions[col].width = w
    style_title(ws, "共通仕様（全処理に適用）")
    r = 2
    r = section(ws, r, "1. 全処理共通の規約")
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
    r = table(ws, r, ["項目", "規約", "参照", "", ""], blank_rows=0)
    for i, (k, v, ref) in enumerate(commons):
        for j, val in enumerate((k, v, ref, "", "")):
            c = ws.cell(row=r + i, column=j + 1, value=val)
            c.font, c.border, c.alignment = BASE, BOX, WRAP
            if j == 1 and not val:
                c.fill = TODO_FILL

    # 05 データ定義
    ws = wb.create_sheet("05_データ定義")
    for col, w in zip("ABCDE", (24, 14, 12, 46, 30)):
        ws.column_dimensions[col].width = w
    style_title(ws, "データ定義")
    r = 2
    for title in ("1. 台帳スキーマ（registry/{appId}/{env}.json）",
                  "2. 監視資材（monitoring.yaml / openapi.yaml / deploy-info.json）",
                  "3. イベント payload（Lambda 間）",
                  "4. メトリクス"):
        r = section(ws, r, title)
        r = table(ws, r, ["項目", "型", "必須", "説明・例", "出典"], blank_rows=5)
        r += 1

    # 06 IAM
    ws = wb.create_sheet("06_IAM・権限一覧")
    for col, w in zip("ABCDE", (30, 24, 46, 24, 24)):
        ws.column_dimensions[col].width = w
    style_title(ws, "IAM・権限一覧")
    r = 2
    r = section(ws, r, "1. ロール一覧")
    r = table(ws, r, ["ロール", "使い手", "権限", "配置アカウント", "利用する処理（P-xx）"], blank_rows=8)
    r += 1
    r = section(ws, r, "2. 信頼関係")
    table(ws, r, ["ロール", "信頼元", "条件（ExternalId 等）", "参照", ""], blank_rows=5)

    # 07 非機能
    ws = wb.create_sheet("07_非機能")
    for col, w in zip("ABCDE", (26, 46, 24, 24, 24)):
        ws.column_dimensions[col].width = w
    style_title(ws, "非機能（性能・上限・コスト・監視）")
    r = 2
    for title, headers in (
        ("1. 性能・上限", ["項目", "値・方針", "根拠", "備考", ""]),
        ("2. 監視・アラーム", ["ID", "検知対象", "手段", "閾値", "通知先"]),
        ("3. コスト", ["項目", "算定", "月額", "負担アカウント", "備考"]),
        ("4. 保持期間", ["対象", "保持期間", "根拠", "備考", ""]),
    ):
        r = section(ws, r, title)
        r = table(ws, r, headers, blank_rows=5)
        r += 1


def main():
    wb = Workbook()
    wb.remove(wb.active)
    titles = [build_process_sheet(wb, p) for p in PROCESSES]
    build_common_sheets(wb, titles)
    order = ["00_表紙・改訂履歴", "01_位置づけ・前提", "02_全体構成", "03_処理一覧",
             "04_共通仕様", "05_データ定義", "06_IAM・権限一覧", "07_非機能"] + titles
    wb._sheets = [wb[t] for t in order]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    print(f"wrote {OUT} ({len(wb.sheetnames)} sheets)")


if __name__ == "__main__":
    main()
