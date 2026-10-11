import numpy as np, pandas as pd, os, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrow, FancyBboxPatch, Arc, Polygon, Rectangle
from _paths import RAW as D, OUT
plt.rcParams["font.family"] = "Noto Sans CJK JP"
nodes = pd.read_csv(os.path.join(OUT, "nodes.csv"), dtype={"code": str}); S = nodes[nodes.level == 37].set_index("code")
T = lambda c, idx=None: float((S[c] if idx is None else S.loc[idx, c]).fillna(0).sum()) / 1000       # 兆円
INK, MUTED, SURF = "#0b0b0b", "#52514e", "#fcfcfb"
C = dict(家計="#2a78d6", 企業="#eb6834", 政府="#1baf7a", 海外="#6250d6", 仕入れ="#9b9a95", 償却="#f4b08f")

# ---- A: 全体の循環(兆円) ----
pay = dict(家計=T("fd_民間消費"), 企業=T("fd_民間固定資本形成") + T("fd_在庫純増"), 政府=T("fd_政府消費") + T("fd_公的固定資本形成"), 海外=T("fd_輸出"))
rec = dict(家計=T("va_雇用者所得"), 企業=T("va_営業余剰") + T("va_資本減耗引当"), 政府=T("va_間接税") + T("va_経常補助金(控除)") + T("import_duties"), 海外=T("imports_goods"))
mid = T("intermediate_sales"); X = T("output")
chk = (mid + sum(pay.values())) - (mid + sum(rec.values()))
print("A: 払う", {k: round(v, 1) for k, v in pay.items()}, "受け取る", {k: round(v, 1) for k, v in rec.items()}, "仕入れ", round(mid, 1), "生産額", round(X, 1), "収支差(家計外消費の丸め込み)", round(chk, 1))
assert abs(chk) < 3
tax_net = T("va_間接税") + T("va_経常補助金(控除)")

# ---- B/C: 産業グループ別 ----
GROUPS = [("資源・一次産業", ["01","06"]), ("素材", ["15","16","20","21","22","25","26","27","28"]), ("食品・生活関連製造", ["11","39","68"]),
          ("機械・電機・輸送機械", ["29","30","31","32","33","34","35"]), ("建設・エネルギー・環境", ["41","46","47","48"]),
          ("流通・金融・不動産・運輸通信", ["51","53","55","57","59"]), ("対事業所・対個人サービス等", ["66","67","65","69"]), ("公務・教育・医療", ["61","63","64"])]
rowsB, rowsC = [], []
for g, cs in GROUPS:
    s = lambda c: T(c, cs)
    b = dict(group=g, output=s("output"), 仕入れ=s("intermediate_sales"), 家計=s("fd_民間消費"), 政府=s("fd_政府消費") + s("fd_公的固定資本形成"), 企業=s("fd_民間固定資本形成") + s("fd_在庫純増"), 海外=s("fd_輸出"))
    c = dict(group=g, output=s("output"), 仕入れ=s("intermediate_purchases"), 賃金=s("va_雇用者所得"), 営業余剰=s("va_営業余剰"), 減価償却=s("va_資本減耗引当"), 税=s("va_間接税") + s("va_経常補助金(控除)"))
    rowsB.append(b); rowsC.append(c)
B = pd.DataFrame(rowsB); Cc = pd.DataFrame(rowsC)
for df, cols in ((B, ["仕入れ","家計","政府","企業","海外"]), (Cc, ["仕入れ","賃金","営業余剰","減価償却","税"])):
    tot = df[cols].clip(lower=0).sum(axis=1)
    for c in cols: df[c + "_%"] = df[c].clip(lower=0) / tot * 100
    print(df[["group"] + [c + "_%" for c in cols]].round(1).to_string(index=False)); print("最小値(負の値がないか):", round(df[cols].min().min(), 2))
B.round(2).to_csv(os.path.join(OUT, "group_sales_use.csv"), index=False, encoding="utf-8-sig"); Cc.round(2).to_csv(os.path.join(OUT, "group_cost_structure.csv"), index=False, encoding="utf-8-sig")

FH = 27; fr = lambda y: 1 - y / FH     # y は上端からのインチ数
fig = plt.figure(figsize=(16, FH), dpi=200, facecolor=SURF)
fig.text(0.04, fr(0.55), "日本のお金の循環:誰が何のために払い、誰に渡るか", fontsize=30, fontweight="bold", color=INK, va="center")
fig.text(0.04, fr(1.1), "令和2年(2020年)産業連関表(生産者価格評価表・統合大分類37部門)。単位は兆円。2020年はコロナ禍の年で、平年より小さく出ている業種があります。", fontsize=12.5, color=MUTED, va="center")
fig.text(0.04, fr(1.45), "この表に含まれない流れ(税・社会保険料の再分配、融資・投資の元本、家計や企業どうしの送金)は、図に出ていません。", fontsize=12.5, color=MUTED, va="center")

# ---- パネルA ----
ax = fig.add_axes([0, fr(12.45), 1, 10.75 / FH]); H = 10.75 / 4 / 2; ax.set_xlim(-2.0, 2.0); ax.set_ylim(-H, H); ax.set_aspect("equal"); ax.axis("off")
ax.text(-1.95, H - 0.04, "A. 全体の循環(1年間の合計)", fontsize=17, fontweight="bold", color=INK, va="top")
w = lambda a: 0.02 + 0.00058 * a
def arrow(x, y, dx, dy, a, col, alpha):
    ax.add_patch(FancyArrow(x, y, dx, dy, width=w(a), head_width=w(a) * 1.7 + 0.06, head_length=0.15, length_includes_head=True, fc=col, ec="none", alpha=alpha, zorder=3))
bx, by = 0.66, 0.32
ax.add_patch(FancyBboxPatch((-bx, -by), 2 * bx, 2 * by, boxstyle="round,pad=0.0,rounding_size=0.06", fc="#eeede9", ec="#9b9a95", lw=2, zorder=2))
ax.text(0, 0.205, "産業(37部門の合計)", ha="center", va="center", fontsize=18, fontweight="bold", color=INK, zorder=4)
ax.text(0, 0.095, f"国内生産額 {X:,.0f}兆円", ha="center", va="center", fontsize=13.5, color=MUTED, zorder=4)
cx, cy, r = -0.42, -0.085, 0.105
ax.add_patch(Arc((cx, cy), 2 * r, 2 * r, theta1=40, theta2=335, lw=1.5 + mid * 0.011, ec=C["仕入れ"], zorder=4))
th = np.deg2rad(335); tp = np.array([cx + r * np.cos(th), cy + r * np.sin(th)]); tv = np.array([-np.sin(th), np.cos(th)]); nv = np.array([-tv[1], tv[0]])
ax.add_patch(Polygon([tp + tv * 0.075, tp - tv * 0.01 + nv * 0.05, tp - tv * 0.01 - nv * 0.05], closed=True, fc=C["仕入れ"], ec="none", zorder=5))
ax.text(-0.25, -0.085, f"産業どうしの仕入れ {mid:,.0f}兆円\n(産業の中で回るお金)", ha="left", va="center", fontsize=12.5, color=INK, zorder=4, linespacing=1.4)
def actor(x, y, name, hw=0.3):
    ax.add_patch(FancyBboxPatch((x - hw, y - 0.15), 2 * hw, 0.3, boxstyle="round,pad=0.0,rounding_size=0.05", fc=SURF, ec=C[name], lw=5, zorder=4))
    ax.text(x, y, name if name != "海外" else "海外", ha="center", va="center", fontsize=20, fontweight="bold", color=INK, zorder=5)
YT, XS = 1.13, 1.58
actor(0, YT, "家計"); actor(0, -YT, "企業"); actor(-XS, 0, "政府"); actor(XS, 0, "海外")
off, y1 = 0.26, YT - 0.15
# 上(家計): 左=払う(下向き)、右=受け取る(上向き)
arrow(-off, y1, 0, -(y1 - by), pay["家計"], C["家計"], 1.0); arrow(off, by, 0, y1 - by, rec["家計"], C["家計"], 0.55)
ax.text(-off - 0.17, (y1 + by) / 2, f"家計が払う\n民間消費 {pay['家計']:,.0f}兆円", ha="right", va="center", fontsize=14, color=INK, linespacing=1.5)
ax.text(off + 0.17, (y1 + by) / 2, f"家計が受け取る\n賃金 {rec['家計']:,.0f}兆円", ha="left", va="center", fontsize=14, color=INK, linespacing=1.5)
# 下(企業): 左=払う(上向き)、右=受け取る(下向き)
arrow(-off, -y1, 0, y1 - by, pay["企業"], C["企業"], 1.0); arrow(off, -by, 0, -(y1 - by), rec["企業"], C["企業"], 0.55)
ax.text(-off - 0.17, -(y1 + by) / 2, f"企業が払う\n設備投資・在庫 {pay['企業']:,.0f}兆円", ha="right", va="center", fontsize=14, color=INK, linespacing=1.5)
ax.text(off + 0.17, -(y1 + by) / 2, f"企業が受け取る {rec['企業']:,.0f}兆円\n利益 {T('va_営業余剰'):,.0f} + 設備の減価償却 {T('va_資本減耗引当'):,.0f}", ha="left", va="center", fontsize=14, color=INK, linespacing=1.5)
# 左(政府): 上=払う(右向き)、下=受け取る(左向き)
xa = -XS + 0.3; dy = 0.17
arrow(xa, dy, (-bx) - xa, 0, pay["政府"], C["政府"], 1.0); arrow(-bx, -dy, xa - (-bx), 0, rec["政府"], C["政府"], 0.55)
ax.text((xa - bx) / 2 - 0.05, dy + 0.19, f"政府が払う {pay['政府']:,.0f}兆円\n政府消費 {T('fd_政府消費'):,.0f} + 公共投資 {T('fd_公的固定資本形成'):,.0f}", ha="center", va="bottom", fontsize=13, color=INK, linespacing=1.45)
ax.text((xa - bx) / 2 - 0.05, -dy - 0.19, f"政府が受け取る {rec['政府']:,.0f}兆円\n税(補助金控除後) {tax_net:,.0f} + 関税等 {T('import_duties'):,.1f}", ha="center", va="top", fontsize=13, color=INK, linespacing=1.45)
# 右(海外): 上=払う(左向き)、下=受け取る(右向き)
xb = XS - 0.3
arrow(xb, dy, bx - xb, 0, pay["海外"], C["海外"], 1.0); arrow(bx, -dy, xb - bx, 0, rec["海外"], C["海外"], 0.55)
ax.text((xb + bx) / 2 + 0.05, dy + 0.19, f"海外が払う\n輸出 {pay['海外']:,.0f}兆円", ha="center", va="bottom", fontsize=13, color=INK, linespacing=1.45)
ax.text((xb + bx) / 2 + 0.05, -dy - 0.19, f"海外が受け取る\n輸入 {rec['海外']:,.0f}兆円", ha="center", va="top", fontsize=13, color=INK, linespacing=1.45)
# 凡例(矢印の見方)
ax.add_patch(FancyArrow(-1.95, -H + 0.2, 0.28, 0, width=0.05, head_width=0.11, head_length=0.08, length_includes_head=True, fc="#52514e", ec="none", alpha=1.0))
ax.text(-1.6, -H + 0.2, "濃い矢印:産業へ払う(産業の売上)", fontsize=12, color=INK, va="center")
ax.add_patch(FancyArrow(-1.95, -H + 0.08, 0.28, 0, width=0.05, head_width=0.11, head_length=0.08, length_includes_head=True, fc="#52514e", ec="none", alpha=0.5))
ax.text(-1.6, -H + 0.08, "薄い矢印:産業から受け取る(産業の費用の行き先)    矢印の太さ=金額", fontsize=12, color=INK, va="center")

# ---- パネルB/C ----
def stacked(top, title, df, cols, labels, colors, note):
    fig.text(0.04, fr(top), title, fontsize=17, fontweight="bold", color=INK, va="center")
    x = 0.04
    for lab, col in zip(labels, colors):
        fig.patches.append(Rectangle((x, fr(top + 0.75) - 0.0035), 0.012, 0.0075, transform=fig.transFigure, fc=col, ec="none")); fig.text(x + 0.017, fr(top + 0.75), lab, fontsize=12.5, color=INK, va="center"); x += 0.017 + 0.0105 * len(lab) + 0.03
    a = fig.add_axes([0.285, fr(top + 1.2 + 4.6), 0.675, 4.6 / FH]); a.set_xlim(0, 100); a.set_ylim(len(df) - 0.45, -0.55); a.axis("off")
    for i, r in df.iterrows():
        left = 0
        for c, col in zip(cols, colors):
            v = max(r[c + "_%"], 0); a.barh(i, v, left=left, height=0.72, color=col, ec=SURF, lw=2)
            if v >= 6:
                lum = 0.2126 * int(col[1:3], 16) ** 2.2 / 255 ** 2.2 + 0.7152 * int(col[3:5], 16) ** 2.2 / 255 ** 2.2 + 0.0722 * int(col[5:7], 16) ** 2.2 / 255 ** 2.2
                a.text(left + v / 2, i, f"{v:.0f}%", ha="center", va="center", fontsize=12.5, color=("#ffffff" if lum < 0.25 else INK), fontweight="medium")
            left += v
        a.text(-1.2, i - 0.1, r["group"], ha="right", va="center", fontsize=13.5, color=INK); a.text(-1.2, i + 0.27, f"生産額 {r['output']:,.0f}兆円", ha="right", va="center", fontsize=11, color=MUTED)
    fig.text(0.04, fr(top + 1.2 + 4.6 + 0.35), note, fontsize=11, color=MUTED, va="center")
stacked(13.0, "B. 各産業は『何のために』買われているか(売上の用途内訳)", B, ["仕入れ","家計","政府","企業","海外"],
        ["産業どうしの仕入れ(原材料・サービス)","家計の消費","政府(消費・公共投資)","企業の設備投資・在庫","海外(輸出)"], [C["仕入れ"], C["家計"], C["政府"], C["企業"], C["海外"]], "輸入品の流通分を含む総額ベース。家計外消費支出(約9兆円)は含まない。")
stacked(20.0, "C. 各産業が受け取ったお金は『誰に』渡るか(費用の内訳)", Cc, ["仕入れ","賃金","営業余剰","減価償却","税"],
        ["他産業への仕入れ代金","賃金(家計へ)","利益(企業へ)","設備の減価償却(企業へ)","税(政府へ)"], [C["仕入れ"], C["家計"], C["企業"], C["償却"], C["政府"]], "税は補助金を差し引いた値。補助金が税を上回る一次産業・機械は0%で表示(実際は約-3%・-2%)。グループ分けは見やすさのための独自のもの(公式分類ではありません)。")
fig.text(0.04, fr(26.6), "出典:総務省ほか「令和2年(2020年)産業連関表」(e-Stat)。作成:本チャットでの集計。輸出入は競争輸入型の表の扱いに従い、輸入は海外へ、関税・輸入品商品税は政府へ振り分けた。", fontsize=10.5, color=MUTED, va="center")
fig.savefig(os.path.join(OUT, "money_circulation.png"), facecolor=fig.get_facecolor()); print("saved")
