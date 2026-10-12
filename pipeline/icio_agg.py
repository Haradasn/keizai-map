"""OECD ICIO 2025 edition (regular, 2016-2022 SML csv) から、5か国の仕入れ構成を集計する。
入力: {year}_SML.csv(OECDサイトの 2016-2022_SML.zip を展開)。出力: icio_summary_5countries.csv
実行: python3 -I icio_agg.py （CSVのあるディレクトリで）"""

import pandas as pd

C = ["JPN", "USA", "CHN", "DEU", "KOR"]
G = {
    "outsourcing": ["M", "N"],
    "digital": ["J58T60", "J61", "J62_63"],
    "energy": ["B05", "B06", "C19", "D"],
    "finance": ["K"],
    "logistics": ["H49", "H50", "H51", "H52", "H53"],
    "trade": ["G"],
}
FD = ("HFCE", "NPISH", "GGFC", "GFCF", "INVNT", "DPABR")
rows = []
for y in range(2016, 2023):
    df = pd.read_csv(f"{y}_SML.csv", index_col=0)
    ind_rows = [
        r
        for r in df.index
        if "_" in r and r.split("_", 1)[0] not in ("TLS", "VA", "OUT") and r not in ("TLS", "VA", "OUT")
    ]
    for c in C:
        cols = [k for k in df.columns if k.startswith(c + "_") and not k.endswith(FD)]
        sub = df.loc[ind_rows, cols]
        tot = sub.values.sum()
        rec = dict(year=y, country=c, intermediate_total=tot / 1e3)
        for g, codes in G.items():
            r = [x for x in ind_rows if x.split("_", 1)[1] in codes]
            tt = sub.loc[r].values.sum()
            dom = sub.loc[[x for x in r if x.startswith(c + "_")]].values.sum()
            rec[g + "_usd_bn"] = tt / 1e3
            rec[g + "_share_pct"] = tt / tot * 100
            rec[g + "_import_share_pct"] = (tt - dom) / tt * 100
        rows.append(rec)
pd.DataFrame(rows).round(3).to_csv("icio_summary_5countries.csv", index=False)
