"""資金フロー表の作成。向きは「お金の向き」(払う側 → 受け取る側)。金額単位は10億円(表と同じ)。
actor: 家計 / 企業 / 政府 / 海外 / 家計外消費(企業の交際費・福利厚生等を経由する、産業連関表上の中継項目)
"""

import numpy as np, pandas as pd, os
from _paths import OUT

nodes = pd.read_csv(os.path.join(OUT, "nodes.csv"), dtype={"code": str})
edges = pd.read_csv(os.path.join(OUT, "edges.csv"))
ACT = {
    "A_家計": "家計",
    "A_企業": "企業",
    "A_政府": "政府",
    "A_海外": "海外",
    "A_家計外": "家計外消費(中継項目)",
}
rows = []


def g(r, c):
    v = r.get(c, 0)
    return 0.0 if pd.isna(v) else float(v)


def add(level, payer, payee, purpose, amt, names):
    if abs(amt) < 1e-9:
        return
    if amt < 0:
        payer, payee, purpose, amt = payee, payer, purpose + "(マイナス分・逆向き)", -amt
    rows.append(
        dict(
            level=level,
            payer=payer,
            payee=payee,
            purpose=purpose,
            amount=amt,
            payer_name=names.get(payer, payer),
            payee_name=names.get(payee, payee),
        )
    )


for level in (108, 37):
    nd = nodes[nodes.level == level]
    names = {**ACT, **dict(zip(nd.id, nd.name))}
    for r in nd.to_dict("records"):
        s = r["id"]
        add(level, "A_家計", s, "民間消費", g(r, "fd_民間消費"), names)
        add(
            level, "A_政府", s, "政府消費", g(r, "fd_政府消費") + g(r, "fd_政府消費(社会資本等減耗分)"), names
        )
        add(level, "A_政府", s, "公共投資(公的固定資本形成)", g(r, "fd_公的固定資本形成"), names)
        add(level, "A_企業", s, "設備投資等(民間固定資本形成)", g(r, "fd_民間固定資本形成"), names)
        add(level, "A_企業", s, "在庫純増", g(r, "fd_在庫純増"), names)
        add(level, "A_海外", s, "輸出", g(r, "fd_輸出"), names)
        add(level, "A_家計外", s, "家計外消費支出", g(r, "fd_家計外消費"), names)
        add(level, s, "A_家計", "賃金(雇用者所得)", g(r, "va_雇用者所得"), names)
        add(level, s, "A_企業", "営業余剰(利益)", g(r, "va_営業余剰"), names)
        add(level, s, "A_企業", "減価償却(資本減耗引当)", g(r, "va_資本減耗引当"), names)
        add(level, s, "A_政府", "減価償却(社会資本等)", g(r, "va_資本減耗引当(社会資本等)"), names)
        add(level, s, "A_政府", "間接税(関税等を除く)", g(r, "va_間接税"), names)
        add(level, "A_政府", s, "経常補助金", -g(r, "va_経常補助金(控除)"), names)
        add(level, s, "A_家計外", "家計外消費支出(費用として)", g(r, "va_家計外消費(行)"), names)
        add(level, s, "A_政府", "関税・輸入品商品税", g(r, "import_duties"), names)
        add(level, s, "A_海外", "輸入", g(r, "imports_goods"), names)
    for e in edges[(edges.type == "SUPPLIES") & (edges.level == level)].itertuples():
        add(level, e.dst, e.src, "仕入れ(中間投入)", e.amount, names)
F = pd.DataFrame(rows)
F.to_csv(os.path.join(OUT, "money_flows.csv"), index=False, encoding="utf-8-sig")
# --- 検算: 各部門で「受け取る額」=「支払う額」(競争輸入型のため、輸入は売り手側の行に計上している)
for level in (108, 37):
    f = F[F.level == level]
    ids = nodes[nodes.level == level].id
    rec = f.groupby("payee").amount.sum().reindex(ids).fillna(0)
    pay = f.groupby("payer").amount.sum().reindex(ids).fillna(0)
    print(
        f"[check] {level}部門: 受取-支払の最大差 {np.abs(rec - pay).max():.2f} / 全体の受取合計 {rec.sum() / 1000:,.0f}兆円"
    )
f37 = F[F.level == 37]
act = f37[f37.payer.str.startswith("A_") | f37.payee.str.startswith("A_")].copy()
act["actor"] = np.where(act.payer.str.startswith("A_"), act.payer, act.payee)
act["dir"] = np.where(act.payer.str.startswith("A_"), "actor→産業", "産業→actor")
summ = act.groupby(["actor", "dir", "purpose"]).amount.sum().reset_index()
summ["amount_兆円"] = summ.amount / 1000
summ[["actor", "dir", "purpose", "amount_兆円"]].round(2).to_csv(
    os.path.join(OUT, "circulation_summary.csv"), index=False, encoding="utf-8-sig"
)
print(summ.assign(a=summ.amount_兆円.round(1))[["actor", "dir", "purpose", "a"]].to_string(index=False))
print("仕入れ(中間)", round(f37[f37.purpose == "仕入れ(中間投入)"].amount.sum() / 1000, 1))
