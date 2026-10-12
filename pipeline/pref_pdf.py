"""PDF でしか公表されていない県の取引基本表(生産者価格評価表)を読み取り、Excel にする。

  python3 pipeline/pref_pdf.py <slug>

pref_raw/SOURCES.json の <slug> の "pdf" に、元の PDF・ページ・列コードの意味を書く:
  "pdf": {"file": "yamagata_2020_report5.pdf", "pages": [14, 15, ...], "ocr": false,
          "cols": {"70": "内生部門計", "79": "県内需要合計", "81": "移輸出計",
                   "87": "（控除）移輸入計", "97": "県内生産額"}}
出力は SOURCES の "file"(例: yamagata_2020_39.xlsx、シート「表」)。pref_build.py が通常の Excel と同じく読み込み、
需給と費用の収支が合うことを検証する(読み取りの誤りがあればそこで止まる)。

文字が埋め込まれた PDF は pdftotext -layout で、画像だけの PDF(スキャン)は tesseract の OCR で読む。
表は列が数ページに分かれているので、各ページ冒頭の列コードの行と、行コードから始まる数値の行を集めてつなぐ。
"""

import json
import pathlib
import re
import subprocess
import sys

import openpyxl

R = pathlib.Path(__file__).resolve().parent.parent
RAW = R / "pref_raw"
NUM = re.compile(r"^[-−△▲]?[\d,]+$|^-$|^…$")


def page_text(pdf, p, ocr, engine="pdftotext"):
    if engine == "pdfplumber":  # pdftotext で文字が出ない PDF(フォントの埋め込みが壊れているもの)
        import pdfplumber

        with pdfplumber.open(str(pdf)) as d:
            return d.pages[p - 1].extract_text(layout=True) or ""
    if not ocr:
        return subprocess.run(
            ["pdftotext", "-f", str(p), "-l", str(p), "-layout", str(pdf), "-"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    img = pathlib.Path("/tmp") / f"pref_pdf_{p}"
    subprocess.run(
        [
            "pdftoppm",
            "-f",
            str(p),
            "-l",
            str(p),
            "-r",
            "300",
            "-gray",
            "-png",
            "-singlefile",
            str(pdf),
            str(img),
        ],
        check=True,
    )
    out = subprocess.run(
        ["tesseract", str(img) + ".png", "-", "--psm", "6", "-c", "preserve_interword_spaces=1"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return out


def to_num(t):
    t = t.replace(",", "").replace("−", "-").replace("△", "-").replace("▲", "-")
    if t in ("-", "…", ""):
        return 0.0
    return float(t)


def parse_page(text):
    """列コードの並びと、{行コード: (名前, [値...])} を返す。
    行コードが行頭にあるページと、行末にあるページ(見開きの右側)の両方に対応する。"""
    head, lines = None, []
    for line in text.splitlines():
        toks = line.split()
        if not toks:
            continue
        if head is None and len(toks) >= 3 and all(re.fullmatch(r"\d{2}", t) for t in toks):
            head = toks  # 列コードの行(ページ冒頭)
            continue
        if head is not None:
            lines.append(toks)

    def take(toks, code_last):
        toks = list(toks)
        if code_last:
            if not re.fullmatch(r"\d{2}", toks[-1]):
                return None
            code = toks.pop()
            vals = [t for t in toks if NUM.match(t)]
            return (code, "", vals) if len(vals) == len(toks) else None
        if not re.fullmatch(r"\d{2}", toks[0]):
            return None
        vals = []
        while len(toks) > 1 and NUM.match(toks[-1]):
            vals.insert(0, toks.pop())
        return (toks[0], "".join(toks[1:]), vals)

    best = {}
    for code_last in (False, True):
        rows = {}
        for toks in lines:
            r = take(toks, code_last)
            if r and r[2]:
                rows.setdefault(r[0], (r[1], [to_num(v) for v in r[2]]))
        if len(rows) > len(best):
            best = rows
    return head, best


def main(slug):
    src = json.loads((RAW / "SOURCES.json").read_text(encoding="utf-8"))[slug]
    spec = src["pdf"]
    names, table, col_order = {}, {}, []
    for p in spec["pages"]:
        head, rows = parse_page(
            page_text(RAW / spec["file"], p, spec.get("ocr", False), spec.get("engine", "pdftotext"))
        )
        assert head, (slug, p, "列コードの行が見つからない")
        col_order += [c for c in head if c not in col_order]
        for code, (name, vals) in rows.items():
            assert len(vals) <= len(head), (slug, p, code, name, len(vals), len(head))
            names.setdefault(code, name)
            for c, v in zip(head, vals):  # 右側が空欄の行(付加価値など)は左から詰める
                table.setdefault(code, {})[c] = v
    # 行の名前が無い表(山口県など、行コードだけのもの)は、全国の部門名と既定の名前で補う
    import pandas as pd

    nd = pd.read_csv(R / "data" / "nodes.csv", encoding="utf-8-sig", dtype={"code": str})
    fallback = dict(zip(nd[nd.level == 37].code, nd[nd.level == 37].name))
    fallback |= {"70": "内生部門計", "96": "粗付加価値部門計", "97": "県内生産額"}
    for c in names:
        if not names[c]:
            names[c] = fallback.get(c, f"行{c}")
    row_codes = list(names)
    sectors = [c for c in row_codes if int(c) < 70]
    label = {c: names[c] for c in sectors} | spec["cols"]
    missing = [c for c in spec["cols"] if c not in col_order]
    assert not missing, (slug, "列が見つからない", missing)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "表"
    ws.append([f"{src['name']} {src['year']}年 生産者価格評価表(PDF から読み取り)"])
    cols = [c for c in col_order if c in label]
    ws.append(["コード", "部門名"] + [label[c] for c in cols])
    for code in row_codes:
        ws.append([code, names[code]] + [table[code].get(c) for c in cols])
    out = RAW / src["file"]
    wb.save(out)
    print(slug, out.name, len(sectors), "部門", len(cols), "列")


if __name__ == "__main__":
    main(sys.argv[1])
