"""円安(輸入品の円建て価格の上昇)が各産業のコストに与える影響の目安。2020年の産業連関表(37部門)から計算する。
- 直接: 生産額1円あたり、仕入れのうち輸入品の額(競争輸入型: 各品目の国内需要に占める輸入の割合 m を仕入れに掛ける)
- 波及込み: 国産の仕入れ品に含まれる輸入品も、さかのぼって合計したもの  t = m'A (I-(I-M)A)^-1
出力: data/import_content_37.json
"""

import json, os, numpy as np
from analysis import model
from _paths import OUT

M = model(37)
nd = M["nd"]
A = M["A"]
m = M["m"]
B = M["B"]
d = m @ A
t = d @ B
assert np.all(t >= d - 1e-12) and np.all(t < 1), "波及込みは直接以上、かつ1未満のはず"
rows = [
    dict(
        code=str(c),
        name=n,
        out=round(float(x) / 1000, 2),
        direct=round(float(a), 4),
        total=round(float(b), 4),
    )
    for c, n, x, a, b in zip(nd.code, nd.name, M["X"], d, t)
]
w = M["X"] / M["X"].sum()
res = dict(
    rows=rows,
    avg_total=round(float((t * w).sum()), 4),
    avg_direct=round(float((d * w).sum()), 4),
    unit="生産額に占める割合",
    year=2020,
)
json.dump(
    res,
    open(os.path.join(OUT, "import_content_37.json"), "w", encoding="utf-8"),
    ensure_ascii=False,
    indent=0,
)
for r in sorted(rows, key=lambda r: -r["total"])[:8]:
    print(r["name"], r["direct"], r["total"])
print("平均", res["avg_direct"], res["avg_total"])
