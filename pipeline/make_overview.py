import numpy as np, pandas as pd, os, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.path import Path
from matplotlib.patches import PathPatch, Polygon, Circle, Rectangle
from _paths import RAW as D, OUT
plt.rcParams["font.family"] = "Noto Sans CJK JP"
nodes = pd.read_csv(os.path.join(OUT, "nodes.csv"), dtype={"code": str}); edges = pd.read_csv(os.path.join(OUT, "edges.csv"))
n37 = nodes[nodes.level == 37].reset_index(drop=True)

# 8グループ(筆者による見やすさ優先の独自グルーピング。公式分類ではない)
GROUPS = [("資源・一次産業", ["01","06"]), ("素材", ["15","16","20","21","22","25","26","27","28"]), ("食品・生活関連製造", ["11","39","68"]),
          ("機械・電機・輸送機械", ["29","30","31","32","33","34","35"]), ("建設・エネルギー・環境", ["41","46","47","48"]),
          ("流通・金融・不動産・運輸通信", ["51","53","55","57","59"]), ("対事業所・対個人サービス等", ["66","67","65","69"]), ("公務・教育・医療", ["61","63","64"])]
COL = ["#2a78d6","#eb6834","#1baf7a","#eda100","#e87ba4","#008300","#6250d6","#e34948"]   # 検証済みカテゴリ配色(ライト)の固定順
SHORT = {"他に分類されない会員制団体":"会員制団体","プラスチック・ゴム製品":"プラ・ゴム製品","その他の製造工業製品":"その他製造品","電気・ガス・熱供給":"電気・ガス・熱供給","パルプ・紙・木製品":"パルプ・紙・木製品"}
order = [c for _, cs in GROUPS for c in cs]; assert sorted(order) == sorted(n37.code), set(n37.code) ^ set(order)
gidx = {c: gi for gi, (_, cs) in enumerate(GROUPS) for c in cs}
info = n37.set_index("code")
N = len(order); gap = np.deg2rad(2.2); ang = {}
# グループ間に少し隙間を空けて円周に配置(上から時計回り)
total = N + len(GROUPS) * 0.9; step = 2 * np.pi / total; a = np.pi / 2; prev = None
for c in order:
    if prev is not None and gidx[c] != gidx[prev]: a -= step * 0.9
    ang[c] = a; a -= step; prev = c
pos = {c: np.array([np.cos(t), np.sin(t)]) for c, t in ang.items()}
X = info.output; Rn = {c: 0.016 + 0.042 * np.sqrt(X[c] / X.max()) for c in order}

E = edges[(edges.type == "SUPPLIES") & (edges.level == 37)].copy()
E["a"] = E.src.str[4:]; E["b"] = E.dst.str[4:]; E = E[(E.a != E.b) & (E.amount > 0) & E.a.isin(order) & E.b.isin(order)].sort_values("amount", ascending=False)
TOPN = 120; top = E.head(TOPN); cover = top.amount.sum() / E.amount.sum()
fig = plt.figure(figsize=(16, 20), dpi=200, facecolor="#fcfcfb"); ax = fig.add_axes([0, 0.205, 1, 0.72]); ax.set_xlim(-1.8, 1.8); ax.set_ylim(-1.62, 1.62); ax.set_aspect("equal"); ax.axis("off")

def bez(p0, p1, bend=0.30):
    c = (p0 + p1) / 2 * bend; return p0, c, p1
amax = top.amount.max()
for r in top.sort_values("amount").itertuples():
    p0, p1 = pos[r.a], pos[r.b]; d = p1 - p0; u = d / np.linalg.norm(d)
    s = p0 + u * Rn[r.a] * 0.9; t = p1 - u * (Rn[r.b] + 0.012)
    P0, C, P1 = bez(s, t); lw = 0.5 + 7.5 * np.sqrt(r.amount / amax); col = COL[gidx[r.a]]
    ax.add_patch(PathPatch(Path([P0, C, P1], [Path.MOVETO, Path.CURVE3, Path.CURVE3]), fc="none", ec=col, lw=lw, alpha=0.42, capstyle="round", zorder=2))
    tan = P1 - C; tan /= np.linalg.norm(tan); nrm = np.array([-tan[1], tan[0]]); hl = 0.022 + 0.0016 * lw; hw = 0.011 + 0.0011 * lw
    ax.add_patch(Polygon([P1, P1 - tan * hl + nrm * hw, P1 - tan * hl - nrm * hw], closed=True, fc=col, ec="none", alpha=0.75, zorder=3))
for c in order:
    ax.add_patch(Circle(pos[c], Rn[c], fc=COL[gidx[c]], ec="#fcfcfb", lw=2.2, zorder=5))
    t = ang[c]; ux, uy = np.cos(t), np.sin(t); deg = np.rad2deg(t); right = ux >= 0
    nmj = SHORT.get(info.name[c], info.name[c]); r0 = 1.0 + Rn[c] + 0.035; rot = deg if right else deg + 180; ha = "left" if right else "right"
    ax.text(ux * r0, uy * r0, nmj, rotation=rot, rotation_mode="anchor", ha=ha, va="center", fontsize=13.5, color="#0b0b0b", zorder=6, fontweight="medium")
    r1 = r0 + len(nmj) * 0.0475 + 0.03
    ax.text(ux * r1, uy * r1, f"{X[c]/1000:,.0f}兆円", rotation=rot, rotation_mode="anchor", ha=ha, va="center", fontsize=11, color="#52514e", zorder=6)
# タイトル・注記
fig.text(0.04, 0.965, "日本の産業どうしの取引の全体像(37部門)", fontsize=30, fontweight="bold", color="#0b0b0b", va="center")
fig.text(0.04, 0.944, "令和2年(2020年)産業連関表(総務省ほか・生産者価格評価表・統合大分類)より作成。2020年はコロナ禍の年のため、影響を受けた業種は平年より小さく出ている可能性があります。", fontsize=12.5, color="#52514e", va="center")
fig.text(0.04, 0.930, f"円の大きさ=国内生産額(下の数字は兆円)　線の太さ=取引額(上位{TOPN}本を表示、部門間取引全体の{cover*100:.0f}%)　矢印=売り手→買い手(代金は逆向きに流れる)　自部門内の取引は除外", fontsize=12.5, color="#52514e", va="center")
# 凡例
lx, ly = 0.04, 0.185
for gi, (g, cs) in enumerate(GROUPS):
    cx = lx + (gi % 4) * 0.235; cy = ly - (gi // 4) * 0.020
    fig.patches.append(Rectangle((cx, cy - 0.008), 0.014, 0.016, transform=fig.transFigure, fc=COL[gi], ec="none")); fig.text(cx + 0.02, cy, g, fontsize=12.5, color="#0b0b0b", va="center")
# 上位フロー(読み取りの手がかり)
fig.text(0.04, 0.140, "取引額が大きい流れ(売り手 → 買い手 / 兆円)", fontsize=13.5, fontweight="bold", color="#0b0b0b", va="center")
nm = lambda c: SHORT.get(info.name[c], info.name[c])
for k, r in enumerate(top.head(8).itertuples()):
    x = 0.04 + (k // 4) * 0.48; y = 0.118 - (k % 4) * 0.016
    fig.text(x, y, f"{nm(r.a)} → {nm(r.b)}　{r.amount/1000:.1f}", fontsize=12, color="#0b0b0b", va="center")
fig.text(0.96, 0.020, "色分けは見やすさのための独自グルーピング(公式分類ではありません)", fontsize=10, color="#52514e", ha="right", va="center")
fig.savefig(os.path.join(OUT, "industry_overview_37.png"), facecolor=fig.get_facecolor())
print("saved", f"top{TOPN} cover={cover:.3f}", "edges(non-self)", len(E))
