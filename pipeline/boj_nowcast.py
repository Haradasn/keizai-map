"""日銀 時系列統計データ検索サイト 一括ダウンロード(sppi_m_jp.csv / cgpi_m_jp.csv / bp_m_jp.csv, cp932)から
最新動向ページ用の系列を抜き出し data/nowcast_chart.json を作る。
実行: python3 -I boj_nowcast.py <csvを置いたディレクトリ> <出力json>"""

import pandas as pd, json, sys

D = sys.argv[1]
OUT = sys.argv[2]


def load(f):
    d = pd.read_csv(f"{D}/{f}", encoding="cp932", dtype=str)
    d.columns = ["code", "name", "unit"] + list(d.columns[3:])
    return d


sp = load("sppi_m_jp.csv")
cg = load("cgpi_m_jp.csv")
# 企業向けサービス価格指数(SPPI)と企業物価指数(CGPI)は公表月がずれることがある(CGPI が1か月先に出るなど)。
# 両方の月を合わせた並びを共通の months にし、まだ公表されていない月は None にする
START = "202001"
MONTHS = sorted({c for d in (sp, cg) for c in d.columns[3:] if c >= START})


def series(d, code, months=None):
    r = d[d.code == code].iloc[0]
    m = months or MONTHS

    def val(c):
        if c not in d.columns or pd.isna(r[c]) or r[c] == "":
            return None
        return round(float(r[c].replace(",", "")), 1)

    return m, [val(c) for c in m]


def by_label(d, lvl, label, first=True):
    lab = d.unit.str.split("/", n=1).str[-1].str.replace("_", "", regex=False)
    k = d[(d.unit.str.contains(lvl)) & (lab == label)]
    return k.iloc[0].code


out = {}
out["months"] = MONTHS
out["sppi"] = {"総平均": series(sp, "PRCS20_5200000000")[1]}
for lvl, lab in [
    ("類別", "情報サービス"),
    ("類別", "通信"),
    ("類別", "技術サービス"),
    ("類別", "職業紹介・労働者派遣サービス"),
    ("類別", "専門サービス"),
]:
    out["sppi"][lab] = series(sp, by_label(sp, lvl, lab))[1]
out["cgpi"] = {
    "電力・都市ガス・水道": series(cg, "PRCG20_2202210001")[1],
    "石油・石炭製品": series(cg, "PRCG20_2200620001")[1],
    "石炭・原油・天然ガス": series(cg, "PRCG20_2202130001")[1],
}
bp = pd.read_csv(f"{D}/bp_m_jp.csv", encoding="cp932", dtype=str)
bp.columns = ["code", "name", "unit", "c3"] + list(bp.columns[4:])
mon = list(bp.columns[4:])


def annual(code):
    r = bp[bp.code == code].iloc[0]
    s = pd.to_numeric(r[mon].str.replace(",", ""), errors="coerce")
    res = {}
    for y in range(2019, 2027):
        v = s[[m for m in mon if m.startswith(str(y))]].dropna()
        res[y] = [round(float(v.sum()) / 1e4, 2), len(v)]  # 兆円
    return res


out["bp"] = {
    "digital_pay": annual("BPBP6JYNSD907"),
    "digital_rec": annual("BPBP6JYNSC907"),
    "digital_net": annual("BPBP6JYNSN907"),
    "consult_net": annual("BPBP6JYNSN9082"),
    "othbiz_net": annual("BPBP6JYNSN908"),
}
json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
print({k: (list(v) if isinstance(v, dict) else len(v)) for k, v in out.items()})
