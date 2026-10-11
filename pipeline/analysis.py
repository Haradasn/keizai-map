"""産業連関分析のたたき台。out/nodes.csv と out/edges.csv だけから再現できる(グラフDBのエクスポートでも同じ計算が可能)。
使い方:  python3 analysis.py            -> out/analysis_37.csv, out/analysis_108.csv を出力
         from analysis import simulate  -> simulate(37, {"輸送機械": 1000})  # 最終需要を 1000(=1兆円, 単位は10億円)増やしたときの生産波及
"""
import numpy as np, pandas as pd, networkx as nx, os
D = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(D, "out")

def load(level):
    nodes = pd.read_csv(os.path.join(OUT, "nodes.csv"), dtype={"code": str}); e = pd.read_csv(os.path.join(OUT, "edges.csv"))
    nd = nodes[nodes.level == level].reset_index(drop=True); ids = list(nd.id); ix = {k: i for i, k in enumerate(ids)}
    Z = np.zeros((len(ids), len(ids)))
    for r in e[(e.type == "SUPPLIES") & (e.level == level)].itertuples(): Z[ix[r.src], ix[r.dst]] = r.amount
    fd = {c[3:]: nd[c].fillna(0).values for c in nd.columns if c.startswith("fd_")}
    va = nd[[c for c in nd.columns if c.startswith("va_") and c != "va_家計外消費(行)"]].fillna(0).sum(axis=1).values
    return nd, Z, nd.output.values, fd, nd.imports.fillna(0).values, va

def model(level):
    nd, Z, X, fd, IMP, va = load(level)
    A = Z / X                                              # 投入係数(列=買い手の費用1円あたりの仕入れ)
    Fd = sum(v for k, v in fd.items() if k != "輸出"); E = fd["輸出"]   # 国内最終需要 / 輸出
    m = IMP / (Z.sum(1) + Fd)                              # 輸入係数(国内需要に占める輸入の割合, 競争輸入型)
    I = np.eye(len(X)); B = np.linalg.inv(I - (I - np.diag(m)) @ A)      # 輸入控除型レオンチェフ逆行列
    return dict(nd=nd, Z=Z, X=X, A=A, Fd=Fd, E=E, m=m, B=B, va_ratio=va / X, fd=fd)

def simulate(level, shocks, kind="国内最終需要"):
    """shocks: {部門名 or コード: 最終需要の増減額(表と同じ単位=10億円)}。kind: 国内最終需要 or 輸出。返り値: 部門別の生産誘発額(直接+波及)と付加価値誘発額"""
    M = model(level); nd = M["nd"]; dF = np.zeros(len(nd))
    for k, v in shocks.items():
        hit = nd[(nd.name == k) | (nd.code == str(k))]
        assert len(hit) == 1, f"部門が特定できません: {k}"; dF[hit.index[0]] += v
    dX = M["B"] @ ((np.eye(len(nd)) - np.diag(M["m"])) @ dF if kind == "国内最終需要" else dF)
    res = pd.DataFrame({"name": nd.name, "code": nd.code, "生産誘発額": dX, "付加価値誘発額": dX * M["va_ratio"]})
    res["うち直接投入"] = dF if kind == "輸出" else (1 - M["m"]) * dF
    return res.sort_values("生産誘発額", ascending=False), dX.sum() / dF.sum()

def analyze(level):
    M = model(level); nd, B, X = M["nd"], M["B"], M["X"]
    # 検算: 最終需要から生産額を再現できるか(逆行列モデルの整合)
    Xhat = B @ ((np.eye(len(X)) - np.diag(M["m"])) @ M["Fd"] + M["E"])
    err = float(np.abs(Xhat - X).max() / X.max())
    avg = B.sum() / len(X)
    out = nd[["id", "code", "name", "output"]].copy()
    out["影響力係数(買う側としての波及力)"] = B.sum(0) / avg     # 1より大きい=その部門の需要が他部門を強く引っ張る
    out["感応度係数(売る側としての被波及)"] = B.sum(1) / avg    # 1より大きい=他部門の需要増の恩恵を受けやすい
    out["輸入依存度"] = M["m"]; out["付加価値率"] = M["va_ratio"]
    tot = sum(M["fd"].values()) - 0  # 最終需要合計(輸入控除前)
    for k in ("民間消費", "輸出", "民間固定資本形成", "公的固定資本形成", "政府消費"):
        if k in M["fd"]: out[f"最終需要比率:{k}"] = M["fd"][k] / X
    G = nx.DiGraph()   # お金の向き(買い手→売り手)で、取引額重みのPageRankを計算
    for i in range(len(X)):
        for j in range(len(X)):
            if i != j and M["Z"][i, j] > 0: G.add_edge(j, i, weight=M["Z"][i, j])
    pr = nx.pagerank(G, weight="weight"); out["PageRank(お金の集まりやすさ)"] = [pr.get(i, 0) for i in range(len(X))]
    return out, err

if __name__ == "__main__":
    for lv in (37, 108):
        o, err = analyze(lv); o.to_csv(os.path.join(OUT, f"analysis_{lv}.csv"), index=False, encoding="utf-8-sig")
        print(f"[{lv}部門] 逆行列モデルによる生産額の再現誤差(最大/最大部門比): {err:.2e}")
    # 例1: 公共投資(公的固定資本形成)として建設に1兆円(=1,000, 単位10億円)
    r, mult = simulate(37, {"建設": 1000}); print("\n例1 建設の最終需要+1兆円 -> 生産誘発倍率", round(mult, 2)); print(r.head(6).round(1).to_string(index=False))
    # 例2: 輸送機械の輸出を1兆円増やす
    r, mult = simulate(37, {"輸送機械": 1000}, kind="輸出"); print("\n例2 輸送機械の輸出+1兆円 -> 生産誘発倍率", round(mult, 2)); print(r.head(6).round(1).to_string(index=False))
