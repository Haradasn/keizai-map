"""産業ごとの個別ページ(108産業・37部門)と産業一覧を生成する。 build_site.py から呼ばれる。
文章はデータからの機械的な生成で、事実(数値)のみ。解釈は既存の『ストーリー(仮説)』を転記し、仮説と明記する。
マークアップは templates/ にあり、ここでは表示する値(整形済みの文字列・座標)を用意して描画を呼ぶ。"""

import html
import json
import math
import pathlib
import re
from types import SimpleNamespace

import pandas as pd

from _shell import breadcrumb_head
from _tpl import render

R = pathlib.Path(__file__).resolve().parents[2]
D = R / "data"


def read_csv(filename, **kwargs):
    """data/ の CSV を読む。"""
    return pd.read_csv(D / filename, encoding="utf-8-sig", **kwargs)


# ---------- 数値・名前の整形


def short(name):
    """『（別掲を除く。）』などの注記を外した産業名。"""
    return re.sub(r"^（続き）", "", re.sub(r"（[^）]*(別掲|除く)[^）]*）", "", name))


def tril(x):
    """10億円→兆円。"""
    return f"{x / 1000:.1f}" if x >= 100 else f"{x / 1000:.2f}"


def pct(x, digits=0):
    """割合(0〜1)を「12%」の形に。"""
    return f"{x * 100:.{digits}f}%"


def sg(x, digits=1):
    """符号つきの数値(マイナスは全角風の「−」)。"""
    return ("+" if x >= 0 else "−") + f"{abs(x):.{digits}f}"


def industry_link(code, name):
    """表のセルに入れる産業ページへのリンク。"""
    return {"href": f"industry/{code}.html", "text": short(name)}


def rank_of(values, key):
    """values={id: 値} の中での、key の順位(値が大きい順。同じ値は同じ順位)。"""
    return 1 + sum(1 for v in values.values() if v > values[key])


# ---------- データの読み込み


def load():
    """産業ページに使う CSV / JSON をまとめて読む。"""
    nodes = read_csv("nodes.csv", dtype={"code": str})
    edges = read_csv("edges.csv")
    supplies = edges[edges.type == "SUPPLIES"]
    return dict(
        n108=nodes[nodes.level == 108].set_index("code"),
        n37=nodes[nodes.level == 37].set_index("code"),
        ed=supplies[supplies.level == 108],
        ed37=supplies[supplies.level == 37],
        ts=read_csv("sector_timeseries_108.csv", dtype={"code": str}).set_index("code"),
        an=read_csv("analysis_108.csv", dtype={"code": str}).set_index("code"),
        rk=read_csv("blue_ocean_ranking_108.csv", dtype={"code": str}).set_index("code"),
        ex=json.loads((D / "explorer_data.json").read_text(encoding="utf-8")),
        sim=json.loads((D / "similarity_map.json").read_text(encoding="utf-8")),
    )


# ---------- SVGグラフの座標計算(描画は templates/_charts.html.j2)


def column_chart_data(values, labels):
    """規模の推移の縦棒の座標。values は10億円、表示は兆円。"""
    width, height = 320, 120
    max_value = max(values)
    slot = width / len(values)
    bars = []
    for i, (value, label) in enumerate(zip(values, labels)):
        bar_height = (height - 34) * value / max_value
        x = i * slot + slot * 0.2
        bars.append(
            dict(
                x=f"{x:.1f}",
                y=f"{height - 22 - bar_height:.1f}",
                width=f"{slot * 0.6:.1f}",
                height=f"{bar_height:.1f}",
                text_x=f"{x + slot * 0.3:.1f}",
                value_y=f"{height - 22 - bar_height - 4:.1f}",
                value=f"{value / 1000:.1f}",
                label=label,
            )
        )
    return dict(width=width, height=height, label_y=height - 6, bars=bars)


# ---------- 出どころと行き先の図(産業連関表の需給バランスを、左右に並べた流れの図)
#
# 産業連関表では、どの産業(の製品・サービス)についても、次の式が成り立つ。
#   国内生産 + 輸入 = ほかの産業が使う分(中間需要) + 家計・投資・政府・輸出(最終需要)
#   国内生産 = ほかの産業からの仕入れ(中間投入) + 付加価値
# 左(出どころ)に「仕入れ・付加価値・輸入」、右(行き先)に「産業・家計・民間の投資・政府・輸出」を、金額に比例した太さで並べる。
# 仮定は置かない(表の数字をそのまま並べる)。在庫の取り崩しやくずの回収は、表ではマイナスの需要として記録されているので、
# 出どころの側に移す。企業の交際費・福利厚生費など(家計外消費支出)は、出どころでは「その他の仕入れ」、行き先では「家計」に含める
# (付加価値率の指標と同じ扱い)。

FLOW_NAMED = 4  # 名前を出す仕入れ先・販売先の数の上限
FLOW_NAMED_SHARE = 0.03  # 名前を出す下限(合計に対する割合)。これより小さい相手は「その他」にまとめる
FLOW_MIN_SHARE = 0.01  # 合計に対する割合がこれより小さい項目は、図に出さない

# 行き先の分類(最終需要)。(ラベル, 表の列)
FINAL_DEMAND = [
    ("家計", ["fd_民間消費", "fd_家計外消費"]),
    ("民間の投資", ["fd_民間固定資本形成", "fd_在庫純増"]),
    ("政府", ["fd_政府消費", "fd_政府消費(社会資本等減耗分)", "fd_公的固定資本形成"]),
    ("輸出", ["fd_輸出"]),
]
INTERMEDIATE = "産業の材料・サービス"  # 行き先の分類のうち、ほかの産業(同じ産業を含む)が生産に使う分


def yen(x):
    """10億円単位の金額を、兆円・億円の読みやすい形にする(1兆円未満は億円)。"""
    if x >= 995:
        return f"{x / 1000:.1f}兆円"
    oku = x * 10
    if oku >= 1000:
        return f"{round(oku, -2):,.0f}億円"
    if oku >= 100:
        return f"{round(oku, -1):,.0f}億円"
    return f"{oku:.0f}億円"


def destinations(row):
    """行き先の分類ごとの金額 [(ラベル, 金額)] と、マイナスの需要の合計(在庫の取り崩し・くずの回収)。金額は10億円。
    最初が産業(中間需要)、あとは最終需要(家計・民間の投資・政府・輸出)。マイナスの分類は 0 にして、合計を別に返す。"""

    def col(name):
        value = row.get(name, 0)
        return 0.0 if pd.isna(value) else float(value)

    final = [(label, sum(col(c) for c in columns)) for label, columns in FINAL_DEMAND]
    released = -sum(value for _, value in final if value < 0)
    return [(INTERMEDIATE, col("intermediate_sales"))] + [
        (label, max(value, 0.0)) for label, value in final
    ], released


def supply_demand(row, buy, sell, sid, link, self_label):
    """産業(部門)1つの、出どころと行き先を返す。金額は10億円。

    row=nodes.csv の行、buy/sell=その産業が買う側/売る側の取引(edges.csv。自分との取引を含む)、
    link(id)=相手の産業の {href, text}、self_label=同じ産業の中の取引の呼び名。
    返り値の left/right は [{label, href, value, kind}]、categories は行き先の分類ごとの金額 [(ラベル, 金額)]。
    kind: ind=産業どうしの取引、fin=付加価値と国内の最終需要、sea=海外(輸入・輸出)、etc=在庫・くず。"""

    def col(name):
        value = row.get(name, 0)
        return 0.0 if pd.isna(value) else float(value)

    output, imports = col("output"), max(col("imports"), 0.0)
    categories, released = destinations(row)
    intermediate, final = categories[0][1], categories[1:]
    total = output + imports + released

    def partners(edges, other):
        """名前を出す相手(金額の大きい順、合計の3%以上、4つまで)と、その合計。"""
        named = []
        ranked = edges[edges.amount > 0].sort_values("amount", ascending=False)
        for partner, amount in zip(ranked[other], ranked.amount):
            if len(named) >= FLOW_NAMED or amount / total < FLOW_NAMED_SHARE:
                break
            item = dict(label=self_label, href=None)
            if partner != sid:
                target = link(partner)
                item = dict(label=target["text"], href=target["href"])
            named.append(dict(item, value=float(amount), kind="ind"))
        return named, sum(item["value"] for item in named)

    suppliers, named_in = partners(buy, "src")
    buyers, named_out = partners(sell, "dst")
    # いちばん大きい買い手の産業(同じ産業の中の取引も含めて比べる)。冒頭の一文の補足に使う
    top_buyer = None
    if len(sell) and sell.amount.max() > 0:
        biggest = sell.loc[sell.amount.idxmax()]
        own = biggest.dst == sid
        top_buyer = dict(
            label=self_label if own else link(biggest.dst)["text"], own=own, value=float(biggest.amount)
        )
    # 付加価値は、付加価値率の指標と同じ定義(家計外消費支出を含めない)。家計外消費支出は「その他の仕入れ」に入れる
    value_added = col("value_added")
    left = suppliers + [
        dict(label="その他の仕入れ", href=None, value=output - value_added - named_in, kind="ind"),
        dict(label="付加価値", href=None, value=value_added, kind="fin"),
        dict(label="輸入", href=None, value=imports, kind="sea"),
        dict(label="在庫の取り崩し・くずの回収", href=None, value=released, kind="etc"),
    ]
    right = buyers + [dict(label="その他の産業", href=None, value=intermediate - named_out, kind="ind")]
    right += [
        dict(label=label, href=None, value=value, kind="sea" if label == "輸出" else "fin")
        for label, value in final
    ]
    # 検証: 出どころの合計と行き先の合計は一致する(産業連関表の需給バランス)
    supply = sum(item["value"] for item in left)
    demand = sum(item["value"] for item in right)
    assert abs(supply - demand) <= 0.002 * total + 0.5, (sid, supply, demand)
    return dict(
        left=left,
        right=right,
        categories=categories,
        top_buyer=top_buyer,
        output=output,
        imports=imports,
        released=released,
        total=demand,
    )


def text_em(text):
    """文字列の幅の見積もり(全角=1、英数字・記号=0.56)。"""
    return sum(1.0 if ord(ch) > 0x2E7F else 0.56 for ch in text)


def label_lines(label, amount, width_em):
    """ラベル(名前と金額)が、幅 width_em(全角の字数)の欄で何行になるかの見積もり。金額は途中で折り返さない。"""
    name_em = text_em(label)
    lines = max(1, math.ceil(name_em / width_em))
    last_line = name_em - (lines - 1) * width_em
    return lines + (1 if last_line + 0.5 + text_em(amount) > width_em else 0)


def flow_layout(left, right, px=230, gap=5, pad=4, line=15, label_em=9.5):
    """出どころ・行き先の項目を、流れの図の座標にする。

    px=合計を表す高さ、gap=項目のあいだ、pad=上下の余白、line=ラベル1行の高さ、label_em=ラベル1行に入る字数。
    既定の値はページ用(描画は templates/_charts.html.j2 の flow_figure。ラベルは、狭い画面の文字の大きさで見積もる)。
    共有画像(build_ogp.py)は、画像の大きさに合わせた値を渡す。
    帯の太さは金額に比例。ラベルが重ならないよう、細い項目にもラベルの行数ぶんの高さを割り当てる。
    返り値の項目には y(ラベルの中心)、a0/a1(外側の端での帯の上下)、c0/c1(中央での帯の上下)が付く。"""
    sides = []
    for items in (left, right):
        total = sum(item["value"] for item in items)
        sides.append([dict(item) for item in items if item["value"] / total >= FLOW_MIN_SHARE])
    scale = px / max(sum(item["value"] for item in side) for side in sides)
    for side in sides:
        for item in side:
            item["amount"] = yen(item["value"])
            item["h"] = max(1.5, item["value"] * scale)
            item["slot"] = max(item["h"], label_lines(item["label"], item["amount"], label_em) * line + 4)
    stacks = [sum(item["slot"] for item in side) + gap * (len(side) - 1) for side in sides]
    bands = [sum(item["h"] for item in side) for side in sides]
    height = max(stacks + bands) + pad * 2
    for side, stack, band in zip(sides, stacks, bands):
        y = (height - stack) / 2  # 項目の並びの上の端
        c = (height - band) / 2  # 中央(この産業)の側の、帯の上の端
        for item in side:
            item["a0"] = y + (item["slot"] - item["h"]) / 2
            item["a1"] = item["a0"] + item["h"]
            item["c0"], item["c1"] = c, c + item["h"]
            item["y"] = y + item["slot"] / 2
            y += item["slot"] + gap
            c = item["c1"]
    center = max(bands)
    return dict(
        left=sides[0], right=sides[1], height=height, center=((height - center) / 2, (height + center) / 2)
    )


def flow_paths(layout):
    """流れの図を、ひな形に渡す形(svg の path と線、整形済みの文字列)にする。横は 0〜100(50 がこの産業)、縦はピクセル。"""
    ribbons, bars = [], []
    for side, x_edge, x_ctrl in ((layout["left"], 0, 25), (layout["right"], 100, 75)):
        for item in side:
            a0, a1, c0, c1 = (f"{item[key]:.1f}" for key in ("a0", "a1", "c0", "c1"))
            ribbons.append(
                dict(
                    kind=item["kind"],
                    d=f"M{x_edge} {a0}C{x_ctrl} {a0} {x_ctrl} {c0} 50 {c0}L50 {c1}C{x_ctrl} {c1} {x_ctrl} {a1} {x_edge} {a1}Z",
                )
            )
            bars.append(dict(x=x_edge, y1=a0, y2=a1))
    label = lambda item: dict(
        label=item["label"], href=item["href"], amount=item["amount"], y=f"{item['y']:.1f}"
    )
    return dict(
        left=[label(item) for item in layout["left"]],
        right=[label(item) for item in layout["right"]],
        ribbons=ribbons,
        bars=bars,
        center=dict(y1=f"{layout['center'][0]:.1f}", y2=f"{layout['center'][1]:.1f}"),
        height=f"{layout['height']:.0f}",
    )


def flow_data(row, buy, sell, sid, link, self_label):
    """出どころと行き先の図と、冒頭の一文(いちばん大きい行き先)のデータ。"""
    sd = supply_demand(row, buy, sell, sid, link, self_label)
    total = sd["total"]
    top_label, top_value = max(sd["categories"], key=lambda c: c[1])
    figure = flow_paths(flow_layout(sd["left"], sd["right"]))
    # 合計の内訳の言い方: 「国内生産 A と輸入 B を合わせた T」
    sources = [f"国内生産 {yen(sd['output'])}"]
    if sd["imports"] / total >= 0.005:
        sources.append(f"輸入 {yen(sd['imports'])}")
    released = sd["released"] / total >= FLOW_MIN_SHARE
    if released:
        sources.append(f"在庫の取り崩し・くずの回収 {yen(sd['released'])}")
    base = sources[0]
    if len(sources) > 1:
        base = "、".join(sources[:-1]) + "と" + sources[-1] + "を合わせた" + yen(total)
    # 行き先の中心が産業のときは、いちばん大きい買い手を添える(行き先の5%以上のとき)
    detail = None
    buyer = sd["top_buyer"]
    if top_label == INTERMEDIATE and buyer and buyer["value"] / total >= 0.05:
        toward = "" if buyer["own"] else "向け"
        detail = f"なかでも{buyer['label']}{toward}が{buyer['value'] / total * 100:.0f}%。"
    return dict(
        figure,
        top_label=top_label,
        top_share=f"{top_value / total * 100:.0f}",
        detail=detail,
        base=base,
        total=yen(total),
        total_value=total,
        government=dict(sd["categories"])["政府"] / total >= 0.1,  # 政府の中身の注記を出すか
        released=released,  # 在庫・くずの注記を出すか
        # 共有画像用(build_ogp.py が、画像の大きさに合わせて座標を作り直す)
        items=dict(
            left=[[i["label"], round(i["value"], 1), i["kind"]] for i in sd["left"]],
            right=[[i["label"], round(i["value"], 1), i["kind"]] for i in sd["right"]],
        ),
    )


def trade_table(edges, other, sid, base, link):
    """主な仕入れ先・販売先の表の行(相手, 金額, base に対する割合)。自分との取引は除く。割合 0.1% 以上の上位6件。"""
    ranked = edges[(edges[other] != sid) & (edges.amount / base >= 0.001)]
    ranked = ranked.sort_values("amount", ascending=False).head(6)
    return [
        [link(partner), yen(amount), pct(amount / base, 1)]
        for partner, amount in zip(ranked[other], ranked.amount)
    ]


def self_trade(edges, sid, base):
    """同じ産業の中の取引(金額と、base に対する割合)。合計の1%に満たなければ None。"""
    amount = float(edges[(edges.src == sid) & (edges.dst == sid)].amount.sum())
    return dict(amount=yen(amount), share=pct(amount / base)) if amount / base >= 0.01 else None


# ---------- ものさし(全産業の中での位置)
#
# 指標1つにつき横1本。細い線が全産業(部門)のそれぞれ、朱の線がこの産業。数字だけでは「大きいのか小さいのか」が
# 分からないので、ほかの産業と並べて見せる。順位は値が大きい順。

RULER_WIDTH = 300  # ものさしの横幅(svg の座標。画面の幅に合わせて伸び縮みする)


def ruler_position(value, lo, hi, log):
    """値を、ものさしの上の位置(0〜RULER_WIDTH)にする。範囲の外は端に寄せる。"""
    if log:
        value, lo, hi = math.log10(max(value, lo)), math.log10(lo), math.log10(hi)
    return min(max((value - lo) / (hi - lo), 0), 1) * RULER_WIDTH


def ruler_scale(key, label, values, lo, hi, axis, log=False):
    """ものさし1本の、どのページでも同じ部分(全産業の線と目盛り)。values={id: 値}、axis=[(値, 目盛りの文字)]。"""
    position = lambda value: ruler_position(value, lo, hi, log)
    xs = sorted({round(position(value)) for value in values.values()})  # 近い値は1本にまとめる
    edges = {0: "start", len(axis) - 1: "end"}
    return dict(
        key=key,
        label=label,
        values=values,
        position=position,
        ticks="".join(f"M{x} 5V16" for x in xs),
        zero=f"{position(0):g}" if not log and lo < 0 < hi else None,
        axis=[
            dict(pos=f"{position(value) / RULER_WIDTH * 100:.1f}", text=text, edge=edges.get(i, "mid"))
            for i, (value, text) in enumerate(axis)
        ],
    )


def ruler_rows(scales, key, shown, unit):
    """1ページ分のものさし。shown={指標: 値の表示}、unit=「産業」「部門」。値のない指標(成長率を出せない産業)は行を出さない。"""
    rows = []
    for scale in scales:
        values = scale["values"]
        if key not in values:
            continue
        rows.append(
            dict(
                label=scale["label"],
                value=shown[scale["key"]],
                x=f"{scale['position'](values[key]):.1f}",
                ticks=scale["ticks"],
                zero=scale["zero"],
                axis=scale["axis"],
                rank=f"{len(values)}{unit}中 {rank_of(values, key)}位",
            )
        )
    return rows


def growth_axis(values):
    """成長率のものさしの範囲(5%きざみで、全部の値が入る範囲)と目盛り。"""
    lo = math.floor(min(values.values()) / 5) * 5
    hi = math.ceil(max(values.values()) / 5) * 5
    return lo, hi, [(lo, f"−{abs(lo)}%"), (0, "0"), (hi, f"+{hi}%")]


OUTPUT_AXIS = [(0.1, "0.1兆円"), (1, "1兆円"), (10, "10兆円"), (100, "100兆円")]
PERCENT_AXIS = [(0, "0%"), (50, "50%"), (100, "100%")]


# 名前だけでは中身が分かりにくい産業の、ひとこと説明(産業連関表の決まりごと)。キーは産業・部門のコード
INDUSTRY_NOTES = {
    "573": "自家輸送は、企業が自社の車で人や物を運ぶ活動を、1つの産業として取り出した仮の部門です。"
    "各産業は、燃料や修理を直接買ったのではなく、この部門から「運ぶサービス」を買ったものとして記録されています。",
    "553": "持ち家に住む人が、自分に家賃を払っているとみなして計算した額です（帰属家賃）。実際のお金のやり取りはありません。",
    "681": "事務用品は、各産業が使う文房具などを、まとめて1つの産業として扱う仮の部門です。",
    "68": "事務用品は、各産業が使う文房具などを、まとめて1つの部門として扱う仮の部門です。",
    "691": "分類不明は、ほかのどの産業にも分けられない取引と、表の誤差を集めた部門です。",
    "69": "分類不明は、ほかのどの部門にも分けられない取引と、表の誤差を集めた部門です。",
}


# ---------- 108産業ページ


def breadcrumb_for_industry(site_url, sector_id, sector_name, name):
    """108産業ページのパンくず(構造化データ)。"""
    return breadcrumb_head(
        [
            ("産業一覧", site_url + "/industries"),
            (str(sector_name), f"{site_url}/industry/{sector_id}"),
            (name, None),
        ]
    )


def build_industry_page(code, row, tables, page, site_url):
    """108産業の1ページを書き出し、共有画像(OGP)用のデータを返す。"""
    L = tables
    sid = "S108_" + code
    name = short(row["name"])
    output = float(row.output)
    sector_id = "%02d" % int(row.parent37)
    sector_name = L.n37.loc[sector_id, "name"]
    analysis = L.an.loc[code]
    series = L.ts.loc[code] if code in L.ts.index else None
    link = lambda partner: industry_link(partner[5:], L.names[partner[5:]])
    buy, sell = L.ed[L.ed.dst == sid], L.ed[L.ed.src == sid]
    flow = flow_data(row, buy, sell, sid, link, "同じ産業の中の取引")
    buy_rows = trade_table(buy, "src", sid, output, link)
    sell_rows = trade_table(sell, "dst", sid, flow["total_value"], link)

    growth = float(series.real_cagr_2015_2020) * 100 if series is not None else None
    growth_early = float(series.real_cagr_2011_2015) * 100 if series is not None else None
    trend = None
    if series is not None:
        outputs = [float(series.output_r11), float(series.output_r15), float(series.output_n20)]
        trend = dict(
            chart=column_chart_data(outputs, ["2011年", "2015年", "2020年"]),
            growth_2011_2015=sg(growth_early),
            growth_2015_2020=sg(growth),
        )
    group = None
    if code in L.group_of:
        group_id = L.group_of[code]
        group = dict(id=group_id, name=L.blue_ocean[group_id]["name"])
    neighbors = [L.code_of.get(x) for x in L.sim_nodes[code]["nb"]]
    siblings = [c for c in L.n108.index if "%02d" % int(L.n108.loc[c].parent37) == sector_id and c != code]

    shown = dict(
        output=yen(output),
        growth=f"年{sg(growth)}%" if growth is not None else None,
        va=pct(float(analysis["付加価値率"])),
        imp=pct(float(analysis["輸入依存度"])),
    )
    facts = render(
        "industry_facts.html.j2",
        name=name,
        sector_name=sector_name,
        output=tril(output),
        share=f"{output / L.total_output * 100:.1f}",
        growth=sg(growth) if growth is not None else None,
        top_label=flow["top_label"],
        top_share=flow["top_share"],
        buy_names=[r[0]["text"] for r in buy_rows[:3]],
        sell_names=[r[0]["text"] for r in sell_rows[:3]],
    )
    body = render(
        "industry.html.j2",
        name=name,
        sector_id=sector_id,
        sector_name=sector_name,
        facts=facts,
        note=INDUSTRY_NOTES.get(code),
        flow=flow,
        rulers=ruler_rows(L.rulers108, code, shown, "産業"),
        count=len(L.n108),
        buy_rows=buy_rows,
        sell_rows=sell_rows,
        self_trade=self_trade(L.ed, sid, flow["total_value"]),
        trend=trend,
        group=group,
        neighbors=[industry_link(c, L.names[c]) for c in neighbors if c],
        siblings=[industry_link(c, L.names[c]) for c in siblings],
    )
    description = re.sub(r"<[^>]+>", "", html.unescape(facts))[:150]
    page(
        f"industry/{code}.html",
        f"{name}の産業規模・取引先・成長率（統計で業界研究）｜Keizai Atlas",
        description,
        body,
        breadcrumb_for_industry(site_url, sector_id, sector_name, name),
    )
    return dict(
        id=code,
        title=name,
        kind="108産業の1つ｜" + sector_name,
        top_label=flow["top_label"],
        top_share=flow["top_share"],
        base=flow["base"],
        flow=flow["items"],
    )


# ---------- 37部門ページ


def sector_stories(edges, nodes):
    """取引のストーリー(筆者の仮説)が付いた辺を、表示用の dict にする。"""
    return [
        dict(
            source=nodes[e["s"]]["name"],
            target=nodes[e["t"]]["name"],
            value=f"{e['v']:.1f}",
            confidence=e["conf"],
            story=e["story"],
            basis=e.get("ver", ""),
        )
        for e in edges
        if e.get("story")
    ]


def prefecture_links():
    """部門ごとに、その部門が稼ぎ頭の県と、集中度(特化係数)が高い県。県別の表(data/pref_37.json)から作る。

    稼ぎ頭の決め方・全国の部門との対応は、県ページと同じ関数(build_pref)を使う。
    build_pref はこのファイルを読み込むので、循環しないよう、ここで読み込む。"""
    import build_pref

    data = json.loads((D / "pref_37.json").read_text(encoding="utf-8"))
    kasegi, dense = {}, {}
    for slug, p in data.items():
        link = {"href": f"prefecture/{slug}.html", "text": p["name"]}
        top, share = build_pref.kasegi(p)
        code = build_pref.national_code(top)
        if code:
            kasegi.setdefault(code, []).append((share, link))
        for o in build_pref.specialized_sectors(p["sectors"]):
            code = build_pref.national_code(o)
            if code:
                dense.setdefault(code, []).append((o["lq"], link))
    by_value = lambda pair: -pair[0]
    return dict(
        count=len(data),
        kasegi={
            c: [dict(link, value=pct(v)) for v, link in sorted(rows, key=by_value)]
            for c, rows in kasegi.items()
        },
        dense={
            c: [dict(link, value=f"{v:.1f}倍") for v, link in sorted(rows, key=by_value)[:5]]
            for c, rows in dense.items()
        },
    )


def build_sector_page(sector_id, node, tables, page, site_url):
    """37部門の1ページを書き出し、共有画像(OGP)用のデータを返す。

    産出額と取引は2020年の基本表(nodes.csv / edges.csv)。成長率は接続産業連関表(explorer_data.json の cagr)で、
    3時点の部門の範囲をそろえているため、基本表とは範囲が少し違う部門がある(運輸・郵便は自家輸送を含まない、など)。"""
    L = tables
    sid = "S37_" + sector_id
    row = L.n37.loc[sector_id]
    name = node["name"]
    output = float(row.output)
    children = L.kids_of.get(sector_id, [])
    link = lambda partner: {"href": f"industry/{partner[4:]}.html", "text": L.n37.loc[partner[4:], "name"]}
    buy, sell = L.ed37[L.ed37.dst == sid], L.ed37[L.ed37.src == sid]
    flow = flow_data(row, buy, sell, sid, link, "同じ部門の中の取引")
    buy_rows = trade_table(buy, "src", sid, output, link)
    sell_rows = trade_table(sell, "dst", sid, flow["total_value"], link)
    # 取引のストーリー(仮説)は、産業マップ(explorer_data.json)の、金額の大きい取引に付いている
    partners = lambda near, far: sorted(
        [e for e in L.ex["edges"] if e[near] == sector_id and e[far] != sector_id and e.get("v")],
        key=lambda e: -e["v"],
    )[:6]
    group_name = L.group_names[node["grp"]]
    shown = dict(
        output=yen(output),
        growth=f"年{sg(node['cagr'])}%",
        va=pct(L.va37[sector_id] / 100),
        imp=pct(L.imp37[sector_id] / 100),
    )
    body = render(
        "sector.html.j2",
        id=sector_id,
        name=name,
        group_name=group_name,
        output=tril(output),
        growth=sg(node["cagr"]),
        top_label=flow["top_label"],
        top_share=flow["top_share"],
        buy_names=[r[0]["text"] for r in buy_rows[:3]],
        sell_names=[r[0]["text"] for r in sell_rows[:3]],
        note=INDUSTRY_NOTES.get(sector_id),
        flow=flow,
        rulers=ruler_rows(L.rulers37, sector_id, shown, "部門"),
        count=len(L.n37),
        sub_rows=[
            [
                industry_link(c["c"], c["n"]),
                yen(c["o"] * 1000),
                (sg(c["g"]) + "%") if c["g"] is not None else "−",
            ]
            for c in children
        ],
        buy_rows=buy_rows,
        sell_rows=sell_rows,
        self_trade=self_trade(L.ed37, sid, flow["total_value"]),
        stories=sector_stories(partners("s", "t"), L.n37_nodes)
        + sector_stories(partners("t", "s"), L.n37_nodes),
        kasegi=L.pref["kasegi"].get(sector_id, []),
        dense=L.pref["dense"].get(sector_id, []),
        pref_count=L.pref["count"],
    )
    breadcrumb = breadcrumb_head([("産業一覧", site_url + "/industries"), (name, None)])
    page(
        f"industry/{sector_id}.html",
        f"{name}の産業規模・取引先・成長率（37部門）｜Keizai Atlas",
        f"{name}（37部門の1つ）の2020年の産出額は{tril(output)}兆円。行き先の{flow['top_share']}%は{flow['top_label']}。主な仕入れ先・販売先、含まれる産業、この部門が稼ぎ頭の県、取引の背景（仮説）。",
        body,
        breadcrumb,
    )
    return dict(
        id=sector_id,
        title=name,
        kind="37部門の1つ｜" + group_name,
        top_label=flow["top_label"],
        top_share=flow["top_share"],
        base=flow["base"],
        flow=flow["items"],
    )


# ---------- 産業一覧ページ


def build_index_page(tables, page, palette):
    """産業一覧(8つの大分類 > 37部門 > 108産業)を書き出す。"""
    L = tables
    groups = []
    for group_index, group_name in enumerate(L.group_names):
        ids = [i for i, n in L.n37_nodes.items() if n["grp"] == group_index]
        sectors = []
        for sector_id in sorted(ids, key=lambda i: -L.n37.loc[i, "output"]):
            output = float(L.n37.loc[sector_id, "output"]) / 1000
            # 行き先の内訳の帯: 産業 / 家計・投資・政府 / 輸出(部門ページの図の右側と同じ分類・同じ色)
            categories = dict(destinations(L.n37.loc[sector_id])[0])
            total = sum(categories.values())
            shares = [
                ("ind", "産業", categories[INTERMEDIATE] / total),
                ("fin", "家計・投資・政府", (total - categories[INTERMEDIATE] - categories["輸出"]) / total),
                ("sea", "輸出", categories["輸出"] / total),
            ]
            sectors.append(
                dict(
                    id=sector_id,
                    name=L.n37_nodes[sector_id]["name"],
                    output=f"{output:.1f}" if output < 10 else f"{output:.0f}",
                    strip=[dict(kind=kind, width=f"{share * 100:.1f}") for kind, _, share in shares],
                    strip_label="行き先："
                    + "、".join(f"{label}{share * 100:.0f}%" for _, label, share in shares),
                    industries=[industry_link(c["c"], c["n"]) for c in L.kids_of.get(sector_id, [])],
                )
            )
        groups.append(dict(color=palette["groups"][group_index], name=group_name, sectors=sectors))
    page(
        "industries.html",
        "産業一覧（業界研究に使える37部門・108産業の統計）｜Keizai Atlas",
        "日本の産業を8つの大分類・37部門・108産業に分けて、規模と取引先を見られる一覧。",
        render("industries.html.j2", groups=groups),
    )


# ---------- 全体


def prepare():
    """ページ生成に使う表・辞書をまとめる(名前→コードの逆引き、37部門ごとの子産業、ものさしの共通部分など)。"""
    L = SimpleNamespace(**load())
    L.group_names = L.ex["groups"]
    L.n37_nodes = {x["id"]: x for x in L.ex["nodes"]}
    L.group_of37 = {k: v["grp"] for k, v in L.n37_nodes.items()}
    L.total_output = float(L.n108.output.sum())
    L.names = {c: r["name"] for c, r in L.n108.iterrows()}
    L.code_of = {short(v): k for k, v in L.names.items()}
    L.sim_nodes = {x["c"]: x for x in L.sim["nodes"]}
    L.blue_ocean = L.sim["groups"]
    L.group_of = {c: g for g, v in L.blue_ocean.items() for c in v["codes"]}
    L.kids_of = {}
    for code, row in L.n108.iterrows():
        growth = float(L.ts.loc[code].real_cagr_2015_2020) * 100 if code in L.ts.index else None
        L.kids_of.setdefault("%02d" % int(row.parent37), []).append(
            dict(c=code, n=row["name"], o=float(row.output) / 1000, g=growth)
        )
    for children in L.kids_of.values():
        children.sort(key=lambda child: -child["o"])
    L.pref = prefecture_links()

    # ものさし。108産業は analysis_108.csv と時系列、37部門は基本表(nodes.csv)と産業マップの成長率
    growth108 = {c: float(r.real_cagr_2015_2020) * 100 for c, r in L.ts.iterrows() if c in L.n108.index}
    L.rulers108 = [
        ruler_scale(
            "output",
            "規模（産出額）",
            {c: float(v) / 1000 for c, v in L.n108.output.items()},
            0.1,
            100,
            OUTPUT_AXIS,
            True,
        ),
        ruler_scale("growth", "実質成長（2015→20年）", growth108, *growth_axis(growth108)),
        ruler_scale(
            "va",
            "付加価値率",
            {c: float(v) * 100 for c, v in L.an["付加価値率"].items()},
            0,
            100,
            PERCENT_AXIS,
        ),
        ruler_scale(
            "imp",
            "輸入依存度",
            {c: float(v) * 100 for c, v in L.an["輸入依存度"].items()},
            0,
            100,
            PERCENT_AXIS,
        ),
    ]
    n37 = L.n37.fillna(0)
    growth37 = {i: float(n["cagr"]) for i, n in L.n37_nodes.items()}
    # 付加価値率・輸入依存度の定義は 108産業(analysis_108.csv)と同じ: 付加価値/産出額、輸入/(産出額+輸入-輸出)
    va37 = {c: float(r.value_added / r.output * 100) if r.output else 0.0 for c, r in n37.iterrows()}
    imp37 = {c: float(r.imports / (r.output + r.imports - r["fd_輸出"]) * 100) for c, r in n37.iterrows()}
    L.va37, L.imp37 = va37, imp37
    L.rulers37 = [
        ruler_scale(
            "output",
            "規模（産出額）",
            {c: float(v) / 1000 for c, v in n37.output.items()},
            0.1,
            100,
            OUTPUT_AXIS,
            True,
        ),
        ruler_scale("growth", "実質成長（2011→20年）", growth37, *growth_axis(growth37)),
        ruler_scale("va", "付加価値率", va37, 0, 100, PERCENT_AXIS),
        ruler_scale("imp", "輸入依存度", imp37, 0, 100, PERCENT_AXIS),
    ]
    return L


def build(page, S, PAL, SITE_URL):
    """108産業・37部門・産業一覧のページを書き出し、ページのパス一覧を返す。"""
    tables = prepare()
    (S / "industry").mkdir(exist_ok=True)
    ogp_cards = []
    out_pages = []
    for code, row in tables.n108.iterrows():
        ogp_cards.append(build_industry_page(code, row, tables, page, SITE_URL))
        out_pages.append(f"industry/{code}")
    for sector_id, node in tables.n37_nodes.items():
        ogp_cards.append(build_sector_page(sector_id, node, tables, page, SITE_URL))
        out_pages.append(f"industry/{sector_id}")
    build_index_page(tables, page, PAL)
    (D / "ogp_cards.json").write_text(json.dumps(ogp_cards, ensure_ascii=False, indent=0), encoding="utf-8")
    return out_pages + ["industries"]
