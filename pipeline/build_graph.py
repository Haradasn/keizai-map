"""産業連関表(令和2年/2020年, 生産者価格評価表)から産業グラフを構築する。
入力: kihon_seisan_108.xlsx(統合中分類108部門), kihon_seisan_37.xlsx(統合大分類37部門), bumonbunrui.xlsx(部門分類表)
出力: out/ 以下にCSV(ノード・エッジ)、GraphML、Cypher
金額単位は表の値そのまま(10億円と想定: 国内生産額の合計から整合を確認)。
"""

import openpyxl, numpy as np, pandas as pd, networkx as nx, re, os
from _paths import RAW as D, OUT

KEYS = {
    108: dict(
        fd={
            "民間消費": "721",
            "政府消費": "731",
            "政府消費(社会資本等減耗分)": "732",
            "公的固定資本形成": "741",
            "民間固定資本形成": "751",
            "在庫純増": "761",
            "家計外消費": "711",
            "輸出": "801",
        },
        imp="870",
        imp_goods="841",
        duty=("851", "861"),
        x="970",
        va={
            "雇用者所得": "911",
            "営業余剰": "921",
            "資本減耗引当": "931",
            "資本減耗引当(社会資本等)": "932",
            "間接税": "941",
            "経常補助金(控除)": "951",
            "家計外消費(行)": "711",
        },
    ),
    37: dict(
        fd={
            "民間消費": "72",
            "政府消費": "73",
            "公的固定資本形成": "74",
            "民間固定資本形成": "75",
            "在庫純増": "76",
            "家計外消費": "71",
            "輸出": "80",
        },
        imp="87",
        imp_goods="84",
        duty=("85", "86"),
        x="97",
        va={
            "雇用者所得": "91",
            "営業余剰": "92",
            "資本減耗引当": "93",
            "間接税": "94",
            "経常補助金(控除)": "95",
            "家計外消費(行)": "71",
        },
    ),
}


def load_matrix(path, n):
    K = KEYS[n]
    ws = openpyxl.load_workbook(os.path.join(D, path), data_only=True).active
    codes = [ws.cell(2, c).value for c in range(3, 3 + n)]
    names = [ws.cell(3, c).value for c in range(3, 3 + n)]
    col = {ws.cell(2, c).value: c for c in range(3, ws.max_column + 1) if ws.cell(2, c).value}
    row = {ws.cell(r, 1).value: r for r in range(4, ws.max_row + 1) if ws.cell(r, 1).value}
    g = lambda r, c: float(ws.cell(r, c).value or 0)
    Z = np.array([[g(row[ci], col[cj]) for cj in codes] for ci in codes])
    fd_keys = {k: v for k, v in K["fd"].items() if v in col}
    FD = {k: np.array([g(row[ci], col[v]) for ci in codes]) for k, v in fd_keys.items()}
    IMP = np.array([g(row[ci], col[K["imp"]]) for ci in codes])
    IMPG = np.array([g(row[ci], col[K["imp_goods"]]) for ci in codes])  # (控除)輸入
    DUTY = np.array([sum(g(row[ci], col[k]) for k in K["duty"]) for ci in codes])  # (控除)関税+輸入品商品税
    X_row = np.array([g(row[ci], col[K["x"]]) for ci in codes])  # 行側の国内生産額
    X_col = np.array([g(row[K["x"]], col[cj]) for cj in codes])  # 列側の国内生産額
    VA = {k: np.array([g(row[v], col[cj]) for cj in codes]) for k, v in K["va"].items()}
    return dict(
        codes=codes, names=names, Z=Z, FD=FD, IMP=IMP, IMPG=IMPG, DUTY=DUTY, X_row=X_row, X_col=X_col, VA=VA
    )


M108 = load_matrix("kihon_seisan_108.xlsx", 108)
M37 = load_matrix("kihon_seisan_37.xlsx", 37)

# --- 分類対応(108 -> 37 -> 13) ---
wb = openpyxl.load_workbook(os.path.join(D, "bumonbunrui.xlsx"), data_only=True)
w = wb.worksheets[0]
mid2big = {}
cur_mid = cur_big = None
for r in w.iter_rows(min_row=8, values_only=True):
    if r[7]:
        cur_mid = str(r[7]).strip()
    if r[9]:
        cur_big = str(r[9]).strip()
    if cur_mid and cur_big:
        mid2big.setdefault(cur_mid, cur_big)
w13 = wb.worksheets[2]
big2b13 = {}
b13name = {}
cur13 = None
for r in w13.iter_rows(min_row=5, values_only=True):
    if r[2] and str(r[2]).strip().isdigit() and str(r[2]).strip() != "70" and r[3]:
        cur13 = str(r[2]).strip()
        b13name[cur13] = re.sub(r"\s+", "", str(r[3]))
    if r[0] and str(r[0]).strip().isdigit() and str(r[0]).strip() != "70" and cur13:
        big2b13[str(r[0]).strip()] = cur13
big_name = dict(zip(M37["codes"], M37["names"]))
missing = [c for c in M108["codes"] if c not in mid2big]
assert not missing, f"108->37 対応が取れない部門: {missing}"
for c in M108["codes"]:
    assert mid2big[c] in big_name, (c, mid2big[c])

# --- 検算 ---
chk = {}
idx = {c: i for i, c in enumerate(M37["codes"])}
agg = np.zeros((37, 37))
for i, ci in enumerate(M108["codes"]):
    for j, cj in enumerate(M108["codes"]):
        agg[idx[mid2big[ci]], idx[mid2big[cj]]] += M108["Z"][i, j]
chk["108を37に集約した行列 と 37部門表の最大差"] = float(np.abs(agg - M37["Z"]).max())
chk["108部門 行側と列側の国内生産額の最大差"] = float(np.abs(M108["X_row"] - M108["X_col"]).max())
Z = M108["Z"]
bal = Z.sum(1) + sum(v for v in M108["FD"].values()) + M108["IMP"] - M108["X_row"]
chk["108部門 需給バランス(中間+最終需要-輸入-生産額)の最大残差"] = float(np.abs(bal).max())
chk["輸入計=輸入+関税等 の最大差"] = float(np.abs(M108["IMP"] - M108["IMPG"] - M108["DUTY"]).max())
chk["国内生産額合計(表の単位)"] = float(M108["X_row"].sum())
for k, v in chk.items():
    print(f"[check] {k}: {v:,.3f}")
pd.Series(chk).to_csv(os.path.join(OUT, "checks.csv"), header=["value"], encoding="utf-8-sig")

# --- ノード ---
rows = []
for lvl, M, nm in [(108, M108, "Sector108"), (37, M37, "Sector37")]:
    for i, (c, n) in enumerate(zip(M["codes"], M["names"])):
        d = dict(
            id=f"S{lvl}_{c}",
            label=nm,
            level=lvl,
            code=c,
            name=n,
            output=M["X_row"][i],
            intermediate_sales=M["Z"][i].sum(),
            intermediate_purchases=M["Z"][:, i].sum(),
            imports=-M["IMP"][i],
            imports_goods=-M["IMPG"][i],
            import_duties=-M["DUTY"][i],
        )
        for k, v in M["FD"].items():
            d["fd_" + k] = v[i]
        for k, v in M["VA"].items():
            d["va_" + k] = v[i]
        if lvl == 108:
            d["parent37"] = mid2big[c]
            d["parent37_name"] = big_name[mid2big[c]]
        else:
            d["parent13"] = big2b13.get(c, "")
            d["parent13_name"] = b13name.get(big2b13.get(c, ""), "")
        rows.append(d)
for c13, n in b13name.items():
    rows.append(dict(id=f"S13_{c13}", label="Sector13", level=13, code=c13, name=n))
nodes = pd.DataFrame(rows)
nodes["value_added"] = nodes[
    [c for c in nodes.columns if c.startswith("va_") and c not in ("va_家計外消費(行)",)]
].sum(axis=1, min_count=1)
nodes.to_csv(os.path.join(OUT, "nodes.csv"), index=False, encoding="utf-8-sig")

# --- エッジ ---
E = []
for lvl, M in [(108, M108), (37, M37)]:
    Zm = M["Z"]
    X = M["X_col"]
    codes = M["codes"]
    for i in range(len(codes)):
        for j in range(len(codes)):
            if Zm[i, j] != 0:  # 負の値(くず・副産物の控除など)も符号つきで保持
                E.append(
                    dict(
                        src=f"S{lvl}_{codes[i]}",
                        dst=f"S{lvl}_{codes[j]}",
                        type="SUPPLIES",
                        level=lvl,
                        amount=Zm[i, j],
                        share_of_buyer_cost=Zm[i, j] / X[j] if X[j] else 0,
                        share_of_seller_sales=Zm[i, j] / M["X_row"][i] if M["X_row"][i] else 0,
                    )
                )
for c in M108["codes"]:
    E.append(dict(src=f"S108_{c}", dst=f"S37_{mid2big[c]}", type="PART_OF", level=0))
for c, b in big2b13.items():
    if c in big_name:
        E.append(dict(src=f"S37_{c}", dst=f"S13_{b}", type="PART_OF", level=0))
edges = pd.DataFrame(E)
edges.to_csv(os.path.join(OUT, "edges.csv"), index=False, encoding="utf-8-sig")
print(
    "nodes",
    len(nodes),
    "edges",
    edges.groupby("type").size().to_dict(),
    "supplies108",
    int(((edges.type == "SUPPLIES") & (edges.level == 108)).sum()),
)

# --- GraphML(37部門 + 108部門) ---
G = nx.DiGraph()
for r in nodes.itertuples(index=False):
    G.add_node(
        r.id,
        **{
            k: (
                float(v)
                if isinstance(v, (int, float, np.floating)) and not pd.isna(v)
                else ("" if pd.isna(v) else v)
            )
            for k, v in r._asdict().items()
            if k != "id"
        },
    )
for r in edges.itertuples(index=False):
    G.add_edge(r.src, r.dst, type=r.type, amount=float(r.amount) if not pd.isna(r.amount) else 0.0)
nx.write_graphml(G, os.path.join(OUT, "industry_graph.graphml"))

# --- Cypher ---
cy = """// Neo4jへの取り込み: nodes.csv と edges.csv を import ディレクトリに置いて実行
CREATE CONSTRAINT sector_id IF NOT EXISTS FOR (s:Sector) REQUIRE s.id IS UNIQUE;
LOAD CSV WITH HEADERS FROM 'file:///nodes.csv' AS r
CREATE (s:Sector {id:r.id, level:toInteger(r.level), code:r.code, name:r.name, output:toFloat(r.output),
  value_added:toFloat(r.value_added), imports:toFloat(r.imports), parent37:r.parent37, parent13:r.parent13});
LOAD CSV WITH HEADERS FROM 'file:///edges.csv' AS r WITH r WHERE r.type='SUPPLIES'
MATCH (a:Sector {id:r.src}), (b:Sector {id:r.dst})
CREATE (a)-[:SUPPLIES {amount:toFloat(r.amount), level:toInteger(r.level), share_of_buyer_cost:toFloat(r.share_of_buyer_cost)}]->(b);
LOAD CSV WITH HEADERS FROM 'file:///edges.csv' AS r WITH r WHERE r.type='PART_OF'
MATCH (a:Sector {id:r.src}), (b:Sector {id:r.dst}) CREATE (a)-[:PART_OF]->(b);
// 例: 輸送機械(37部門)の主な仕入先
// MATCH (s:Sector {id:'S37_35'})<-[r:SUPPLIES]-(x) WHERE x.id <> s.id RETURN x.name, r.amount ORDER BY r.amount DESC LIMIT 10;
"""
open(os.path.join(OUT, "import.cypher"), "w", encoding="utf-8").write(cy)
