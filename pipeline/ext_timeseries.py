"""延長産業連関表(2020年基準)97部門: 2020・2021・2022年の名目・実質(2020年価格)から部門別の推移を作る。"""

import pandas as pd, os
from _paths import RAW, OUT

D = RAW / "data"
F = {
    ("n", 2020): "ext2020base_io_20al97.xlsx",
    ("n", 2021): "ext_2021_97n.xlsx",
    ("r", 2021): "ext_2021_97r.xlsx",
    ("n", 2022): "ext2020base_r2_r04uio97n.xlsx",
    ("r", 2022): "ext2020base_r2_r04uio97r.xlsx",
}


def load(f):
    df = pd.read_excel(os.path.join(D, f), sheet_name="中分類", header=None)
    # 単位は100万円(2020年表も100万円)。10億円に直すため /1000
    st = [i for i in range(df.shape[0]) if str(df.iloc[i, 0]).strip() == "001"][0]
    hr = [i for i in range(st) if str(df.iloc[i, 2]).strip() == "農林業"][0]
    df.attrs["st"] = st
    df.attrs["hr"] = hr
    body = df.iloc[st:, :].copy()
    body[0] = body[0].astype(str).str.strip()
    body = body.set_index(0)
    return df, body, None


def sect(body):
    codes = [f"{i:03d}" for i in range(1, 98)]
    A = body.loc[codes].iloc[:, 1:98].astype(float)  # 列: 001..097
    A.index = codes
    A.columns = codes
    names = body.loc[codes, 1].astype(str).str.strip()
    return A, names


def rowof(df, label):
    for i in range(df.shape[0]):
        if str(df.iloc[i, 1]).strip() == label:
            return i
    raise KeyError(label)


rows = {}
meta = {}
for (k, y), f in F.items():
    df, body, cc = load(f)
    A, names = sect(body)
    out_row = body.loc["117"] if "117" in body.index else None
    # 国内生産額行(列方向): 行ラベル '国内生産額'
    r = rowof(df, "国内生産額")
    output = df.iloc[r, 2:99].astype(float).values
    # 列ヘッダから輸出計・輸入計の列位置
    st = df.attrs["st"]
    hdr = df.iloc[df.attrs["hr"], :].astype(str).str.strip().tolist()

    def col(label):
        return hdr.index(label)

    exp = df.iloc[st : st + 97, col("輸出計")].astype(float).values if "輸出計" in hdr else None
    imp = (
        df.iloc[st : st + 97, col("（控除）輸入計")].astype(float).values if "（控除）輸入計" in hdr else None
    )
    rows[(k, y)] = dict(
        A=A.values,
        names=names.values,
        output=output,
        export=exp,
        imp=imp,
        cons=df.iloc[st : st + 97, col("民間消費支出")].astype(float).values,
        wage=df.iloc[rowof(df, "雇用者所得"), 2:99].astype(float).values,
        prof=df.iloc[rowof(df, "営業余剰"), 2:99].astype(float).values,
    )
codes = [f"{i:03d}" for i in range(1, 98)]
names = rows[("n", 2020)]["names"]
res = pd.DataFrame({"code": codes, "name": names})
for (k, y), v in rows.items():
    res[f"output_{k}{y}"] = v["output"] / 1000.0  # 10億円
    if v["export"] is not None:
        res[f"export_{k}{y}"] = v["export"] / 1000.0
    if v["imp"] is not None:
        res[f"import_{k}{y}"] = v["imp"] / 1000.0
    res[f"wage_{k}{y}"] = v["wage"] / 1000.0
    res[f"profit_{k}{y}"] = v["prof"] / 1000.0
# 2020年の名目=実質(2020年価格)。実質は2020価格表を使う
res["output_r2020"] = res["output_n2020"]
res["real_cagr_2020_2022"] = (res["output_r2022"] / res["output_r2020"]) ** 0.5 - 1
res["real_growth_2020_2022"] = res["output_r2022"] / res["output_r2020"] - 1
res["price_chg_2020_2022"] = res["output_n2022"] / res["output_r2022"] - 1
res["nominal_growth_2020_2022"] = res["output_n2022"] / res["output_n2020"] - 1
res.to_csv(os.path.join(OUT, "ext_sector_97.csv"), index=False, encoding="utf-8-sig")
# 97部門の取引(名目)3時点を長形式
Ls = []
for y in (2020, 2021, 2022):
    A = rows[("n", y)]["A"] / 1000.0
    out = rows[("n", y)]["output"] / 1000.0
    for i, s in enumerate(codes):
        for j, b in enumerate(codes):
            if A[i, j] != 0:
                Ls.append((y, s, b, A[i, j], A[i, j] / out[j]))
L = pd.DataFrame(Ls, columns=["year", "seller", "buyer", "amount", "share_of_buyer_cost"])
W = L.pivot_table(index=["seller", "buyer"], columns="year", values=["amount", "share_of_buyer_cost"]).fillna(
    0
)
W.columns = [f"{a}_{b}" for a, b in W.columns]
W = W.reset_index()
nm = dict(zip(codes, names))
W["seller_name"] = W.seller.map(nm)
W["buyer_name"] = W.buyer.map(nm)
W["amount_chg_2020_2022"] = W.amount_2022 - W.amount_2020
W["share_chg_pt"] = (W.share_of_buyer_cost_2022 - W.share_of_buyer_cost_2020) * 100
W.to_csv(os.path.join(OUT, "ext_edges_97.csv"), index=False, encoding="utf-8-sig")
print(
    res[["code", "name", "output_n2020", "output_n2022", "real_cagr_2020_2022", "price_chg_2020_2022"]]
    .round(3)
    .to_string()
)
print(
    "合計 名目",
    res.output_n2020.sum(),
    res.output_n2021.sum(),
    res.output_n2022.sum(),
    "実質2022(2020価格)",
    res.output_r2022.sum(),
)
