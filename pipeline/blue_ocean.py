"""ブルーオーシャン候補(見えにくいが伸びていて、取り込みやすそうな領域)の探索。108部門が対象。
指標(すべて公的データから計算。『競合の少なさ』は直接測れないため、代理指標で近似):
  成長   : 実質成長率 2011-15 と 2015-20 の小さいほう(コロナ禍や一過性を割り引く)
  需要の引き: 売り先の産業(買い手)の成長を、売上の取引額で加重平均したもの
  需給ギャップ: 需要の引き - 自分の成長(買い手が伸びているのに自分は伸びていない=供給が追いついていない可能性)
  裏方度 : 産業向け販売の比率(消費者の目に触れにくい)
  収益性 : 付加価値率・営業余剰率(値決め力の代理)
  規模   : 生産額0.5〜20兆円を最も高く評価(小さすぎず、巨大すぎない)
  取引の広がり: 売上の9割を占める買い手部門の数(多いほど横断的)
"""

import numpy as np, pandas as pd, os
from _paths import OUT

nodes = pd.read_csv(os.path.join(OUT, "nodes.csv"), dtype={"code": str})
edges = pd.read_csv(os.path.join(OUT, "edges.csv"))
T = pd.read_csv(os.path.join(OUT, "sector_timeseries_108.csv"), dtype={"code": str, "parent37": str})
N = nodes[nodes.level == 108].reset_index(drop=True)
ids = list(N.id)
ix = {k: i for i, k in enumerate(ids)}
Z = np.zeros((len(ids), len(ids)))
for r in edges[(edges.type == "SUPPLIES") & (edges.level == 108)].itertuples():
    Z[ix[r.src], ix[r.dst]] = r.amount
np.fill_diagonal(Z, 0)
g = N.code.map(T.set_index("code").real_cagr_2011_2020)  # 買い手の成長
N["g_all"] = g
dp, breadth = [], []
for i in range(len(N)):
    w = Z[i].copy()
    ok = g.notna().values & (w > 0)
    tot = w[ok].sum()
    dp.append(float((w[ok] * g.values[ok]).sum() / tot) if tot > 0 else np.nan)
    s = np.sort(w[w > 0])[::-1]
    cs = np.cumsum(s) / s.sum() if len(s) else np.array([])
    breadth.append(int((cs < 0.9).sum() + 1) if len(s) else 0)
N["demand_pull"] = dp
N["buyer_breadth90"] = breadth
fd_dom = (
    N[["fd_民間消費", "fd_政府消費", "fd_公的固定資本形成", "fd_民間固定資本形成", "fd_在庫純増"]]
    .fillna(0)
    .sum(axis=1)
)
N["b2b_share"] = Z.sum(1) / (Z.sum(1) + fd_dom).replace(0, np.nan)  # 国内向け販売のうち、産業向けの割合(0〜1)
N["va_ratio"] = N.value_added / N.output
N["profit_ratio"] = N["va_営業余剰"] / N.output
N["import_dep"] = N.imports_goods.fillna(0) / (Z.sum(1) + fd_dom).replace(0, np.nan)
D = N.merge(
    T[
        [
            "code",
            "parent37",
            "output_n11",
            "output_n15",
            "output_n20",
            "real_cagr_2011_2015",
            "real_cagr_2015_2020",
            "real_cagr_2011_2020",
            "price_chg_2011_2020",
            "export_n11",
            "export_n20",
        ]
    ],
    on="code",
    suffixes=("", "_t"),
)
D["size_tril"] = D.output_n20 / 1000
D["growth_robust"] = D[["real_cagr_2011_2015", "real_cagr_2015_2020"]].min(axis=1)
D["export_cagr"] = np.where(
    (D.export_n11 > 50) & (D.export_n20 > 0), (D.export_n20 / D.export_n11) ** (1 / 9) - 1, np.nan
)

COVID = {
    "飲食サービス",
    "宿泊業",
    "航空輸送",
    "鉄道輸送",
    "娯楽サービス",
    "道路輸送（自家輸送を除く。）",
    "水運",
    "洗濯・理容・美容・浴場業",
    "運輸附帯サービス",
    "映画・ビデオ制作・配給業",
    "その他の対個人サービス",
}
PUBLIC = {"公務", "教育", "医療", "保健衛生", "社会保険・社会福祉", "介護", "廃棄物処理", "研究"}
EXCL = {
    "事務用品",
    "分類不明",
    "その他の対事業所サービス",
    "住宅賃貸料（帰属家賃）",
    "公務",
}  # 括りが不明確、統計上の擬制(帰属家賃)、市場とは言えない(公務)   # 実体が不明確な括り
D["flag_covid"] = D.name.isin(COVID) | ((D.real_cagr_2011_2015 - D.real_cagr_2015_2020) >= 0.08)
D["flag_public"] = D.name.isin(PUBLIC)
D["pull_missing"] = (
    D.demand_pull.isna()
)  # 産業向け販売がほぼない(消費者向け・公的需要中心)部門は、需要の引きを中央値で補う
D["demand_pull"] = D.demand_pull.fillna(D.demand_pull.median())
D["gap"] = D.demand_pull - D.real_cagr_2011_2020
D["eligible"] = (D.size_tril >= 0.5) & ~D.name.isin(EXCL) & D.growth_robust.notna()
# 成長の条件: 2011-20年の実質成長が年0.5%以上で、どちらの期間も年-0.5%を下回らない(ブルーオーシャンは「伸びている」ことが前提)
D["growing"] = (D.real_cagr_2011_2020 >= 0.005) & (D.growth_robust >= -0.005)
D["eligible"] = D.eligible & D.growing

# 『日経業界地図』目次(205項目)に、その部門を指す独立項目があるか。目次の見出しだけからの私の判定で、本文の記述までは確認していない。
MAP_COVERAGE = {
    "594": (1.0, "ポータル・ネット広告/SNS/クラウド 等に分散"),
    "662": (1.0, "広告"),
    "591": (1.0, "通信キャリア/格安スマホ"),
    "593": (1.0, "ITサービス/ソフトウエア/ビッグデータ"),
    "481": (0.0, "該当項目なし(環境の章にも見当たらない)"),
    "663": (0.0, "該当項目なし(自動車・中古車販売はあるが整備は見当たらない)"),
    "252": (1.0, "セメント"),
    "221": (0.5, "化学の一部として触れられる程度か"),
    "661": (0.5, "リース(金融)はあるが機器レンタルは見当たらない"),
    "577": (1.0, "倉庫"),
    "576": (0.25, "空運/海運/陸運の一部。フォワーダーとしての項目なし"),
    "675": (0.5, "ペット用品の周辺"),
    "113": (0.5, "農ビジネス(一部)"),
    "644": (1.0, "介護サービス"),
    "552": (0.5, "不動産の一部"),
    "208": (0.5, "化粧品・トイレタリーの一部"),
    "281": (0.25, "住設機器・建材・リフォームの周辺。金属製品としては見当たらない"),
    "207": (1.0, "医薬品/後発医薬品"),
    "329": (1.0, "電子部品"),
    "643": (0.5, "介護・保育の周辺"),
    "632": (0.5, "大学・中央省庁の周辺。研究機関としては見当たらない"),
    "331": (0.25, "電機の一部。重電・産業用電気機器の項目なし"),
    "531": (1.0, "銀行/保険/証券"),
    "333": (0.25, "MEMS/産業用ロボットの周辺。計測機器の項目なし"),
    "419": (0.75, "建設/国土強靭化"),
    "332": (1.0, "白物家電/AV・デジタル家電"),
    "111": (1.0, "食品各種"),
}
D["map_visibility"] = D.code.map(lambda c: MAP_COVERAGE.get(c, (np.nan, ""))[0])
D["map_note"] = D.code.map(lambda c: MAP_COVERAGE.get(c, (np.nan, ""))[1])
pr = lambda s: s.rank(pct=True)
E = D[D.eligible].copy()
size_score = (
    1 - (np.log10(E.size_tril) - np.log10(3)).abs() / 1.2
)  # 約3兆円付近が最大、0.5・20兆円付近でも0.3程度
E["s_growth"] = pr(E.growth_robust)
E["s_pull"] = pr(E.demand_pull)
E["s_gap"] = pr(E.gap)
assert E.map_visibility.notna().all(), E[E.map_visibility.isna()].name.tolist()
E["s_hidden"] = 0.5 * pr(E.b2b_share) + 0.5 * (1 - E.map_visibility)
E["s_margin"] = pr(E.va_ratio * 0.5 + E.profit_ratio * 0.5)
E["s_size"] = size_score.clip(0, 1)
E["s_import"] = 1 - pr(E.import_dep.fillna(E.import_dep.median()))
W = dict(s_growth=0.35, s_pull=0.10, s_gap=0.10, s_hidden=0.20, s_margin=0.10, s_size=0.10, s_import=0.05)
E["score"] = sum(E[k] * w for k, w in W.items()) * 100
E["score_adj"] = E.score - 8 * E.flag_covid.astype(
    int
)  # コロナ禍の影響が疑われる部門は減点(落ち込みが一時的な可能性は別途注記)
E = E.sort_values("score_adj", ascending=False).reset_index(drop=True)
E["rank"] = E.index + 1
cols = [
    "rank",
    "code",
    "name",
    "parent37",
    "size_tril",
    "real_cagr_2011_2015",
    "real_cagr_2015_2020",
    "real_cagr_2011_2020",
    "demand_pull",
    "gap",
    "b2b_share",
    "va_ratio",
    "profit_ratio",
    "import_dep",
    "buyer_breadth90",
    "export_cagr",
    "flag_covid",
    "flag_public",
    "map_visibility",
    "map_note",
    "score",
    "score_adj",
] + list(W)
E[cols].round(4).to_csv(os.path.join(OUT, "blue_ocean_ranking_108.csv"), index=False, encoding="utf-8-sig")

from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform

Zs = Z / np.where(Z.sum(1, keepdims=True) > 0, Z.sum(1, keepdims=True), 1)  # 売上に占める買い手の構成比
Zb = Z / np.where(Z.sum(0, keepdims=True) > 0, Z.sum(0, keepdims=True), 1)  # 仕入れに占める売り手の構成比
vec = np.hstack([Zs, Zb.T])
nrm = np.linalg.norm(vec, axis=1, keepdims=True)
vec = vec / np.where(nrm > 0, nrm, 1)
pos = [ix["S108_" + c] for c in E.code]
sim = vec[pos] @ vec[pos].T
dist = 1 - sim
np.fill_diagonal(dist, 0)
cl = fcluster(
    linkage(squareform(np.clip(dist, 0, None), checks=False), "average"), t=0.85, criterion="distance"
)
E["cluster"] = cl
print("\n--- 買い手・売り手の顔ぶれが似たグループ(自動) ---")
for k in sorted(set(cl)):
    print(k, "|", " / ".join(E[E.cluster == k].sort_values("rank").name))
E[cols + ["cluster"]].round(4).to_csv(
    os.path.join(OUT, "blue_ocean_ranking_108.csv"), index=False, encoding="utf-8-sig"
)
D[~D.eligible][
    ["code", "name", "size_tril", "real_cagr_2011_2015", "real_cagr_2015_2020", "real_cagr_2011_2020"]
].to_csv(os.path.join(OUT, "blue_ocean_excluded.csv"), index=False, encoding="utf-8-sig")
pd.set_option("display.width", 220)
show = E[
    [
        "rank",
        "name",
        "size_tril",
        "real_cagr_2011_2015",
        "real_cagr_2015_2020",
        "demand_pull",
        "b2b_share",
        "va_ratio",
        "flag_covid",
        "flag_public",
        "score_adj",
    ]
].copy()
for c in ("real_cagr_2011_2015", "real_cagr_2015_2020", "demand_pull"):
    show[c] = (show[c] * 100).round(1)
show["b2b_share"] = (show.b2b_share * 100).round(0)
show["va_ratio"] = (show.va_ratio * 100).round(0)
show["size_tril"] = show.size_tril.round(1)
show["score_adj"] = show.score_adj.round(1)
print("対象:", len(E), "部門(生産額0.5兆円以上・成長条件を満たす) / 対象外:", int((~D.eligible).sum()))
print(show.head(25).to_string(index=False))
