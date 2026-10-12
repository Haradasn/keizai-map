"""日銀 企業物価指数の一括ダウンロード(cgpi_m_jp.csv, cp932)から、輸入物価指数(円ベース・契約通貨ベース)を取り出す。
円ベース ÷ 契約通貨ベース は、輸入品の価格のうち「為替の動き」による部分の目安(2020年平均=100)。
使い方: python3 pipeline/fx_import.py <cgpi_m_jp.csv があるディレクトリ> data/fx_chart.json
"""

import csv, json, sys, pathlib

src = pathlib.Path(sys.argv[1]) / "cgpi_m_jp.csv"
dst = pathlib.Path(sys.argv[2])
rows = list(csv.reader(open(src, encoding="cp932")))
months = rows[0][3:]
S = {r[0]: r for r in rows[1:]}


def ser(code):
    r = S[code]
    assert "輸入物価指数" in r[1], (code, r[1])
    return [float(v) if v.strip() not in ("", "NA") else None for v in r[3:]]


yen, cc = ser("PRCG20_2600000000"), ser("PRCG20_2500000000")
assert "円ベース" in S["PRCG20_2600000000"][1] and "契約通貨ベース" in S["PRCG20_2500000000"][1]
n = (
    max(i for i, v in enumerate(yen) if v is not None and cc[i] is not None) + 1
)  # 両方そろっている最後の月まで
months, yen, cc = months[:n], yen[:n], cc[:n]
cats = {}
for r in rows[1:]:
    if "輸入物価指数/円ベース" in r[1] and r[2].startswith("類別/"):
        cats[r[2].split("_", 1)[1]] = float(r[3 + n - 1])
out = dict(
    months=months,
    yen=yen,
    contract=cc,
    fx=[round(a / b * 100, 1) for a, b in zip(yen, cc)],
    cats_last=cats,
    base="2020年平均=100",
    source="日本銀行「企業物価指数(2020年基準) 輸入物価指数」",
)
dst.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
print("fx_chart:", months[0], "〜", months[-1], "円", yen[-1], "契約", cc[-1])
