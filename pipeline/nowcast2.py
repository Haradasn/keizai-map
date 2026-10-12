"""経産省 第3次産業活動指数(b2020_ksmj.xlsx) と 財務省 貿易統計 主要商品別(d61ma.csv, 世界・月別・輸入)から
最新動向ページ用の系列を作る。実行: python3 -I nowcast2.py <ディレクトリ> <出力json>"""

import openpyxl, pandas as pd, json, sys

D = sys.argv[1]
OUT = sys.argv[2]
wb = openpyxl.load_workbook(f"{D}/b2020_ksmj.xlsx", read_only=True, data_only=True)
rows = list(wb["ITA"].iter_rows(values_only=True))
months = [str(x) for x in rows[2][3:]]
keep = {
    "第３次産業総合": "J000000I",
    "情報通信業": "JG00000I",
    "ソフトウェア業": "DBCA000I",
    "インターネット附随サービス業": "DBD0000I",
    "職業紹介・労働者派遣業": "DFJ0000I",
    "技術サービス業": "DFE0000I",
    "広告業": "DFD0000I",
    "リース業": "DFA0000I",
}
meti = {}
for n, c in keep.items():
    r = [x for x in rows[3:] if x[0] == c][0]
    meti[n] = [None if not isinstance(v, (int, float)) else round(float(v), 1) for v in r[3:]]
raw = pd.read_csv(f"{D}/d61ma.csv", encoding="cp932", header=None, dtype=str)
h = raw.iloc[2].fillna("")
r0 = [i for i, x in enumerate(raw[0]) if str(x) == "1988/01"][0]


def num(s):
    return pd.to_numeric(s.astype(str).str.replace(",", "").str.replace("-", ""), errors="coerce")


def get(name):
    i = [k for k, x in enumerate(h) if x == name][0]
    d = pd.DataFrame(
        {"m": raw[0][r0:].values, "q": num(raw.iloc[r0:, i]).values, "v": num(raw.iloc[r0:, i + 1]).values}
    )
    d = d[d.m.str.match(r"^\d{4}/\d{2}$", na=False)].copy()
    d["y"] = d.m.str[:4].astype(int)
    d["mm"] = d.m.str[5:].astype(int)
    return d


trade = {"years": list(range(2019, 2026))}
for n, k in [
    ("原油及び粗油", "crude"),
    ("液化天然ガス", "lng"),
    ("石炭", "coal"),
    ("電算機類(含周辺機器)", "pc"),
    ("３．鉱物性燃料", "fuel"),
]:
    d = get(n)
    a = d[(d.y >= 2019) & (d.y <= 2025)].groupby("y")[["q", "v"]].sum()
    trade[k + "_v"] = [round(x / 1e9, 2) for x in a.v]
    if k != "fuel":
        trade[k + "_q_idx"] = [round(x, 1) for x in a.q / a.q.iloc[0] * 100]
        trade[k + "_p_idx"] = [round(x, 1) for x in (a.v / a.q) / (a.v.iloc[0] / a.q.iloc[0]) * 100]
    last = int(d[(d.y == 2026) & d.v.notna()].mm.max())
    trade[k + "_ytd"] = {
        "last_month": last,
        "v2026": round(d[(d.y == 2026) & (d.mm <= last)].v.sum() / 1e9, 2),
        "v2025": round(d[(d.y == 2025) & (d.mm <= last)].v.sum() / 1e9, 2),
    }
json.dump(
    {"months": months, "meti": meti, "trade": trade},
    open(OUT, "w"),
    ensure_ascii=False,
    separators=(",", ":"),
)
print(list(meti), {k: v for k, v in trade.items() if k.endswith("_ytd")})
