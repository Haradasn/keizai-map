"""産業ごとの個別ページ(108産業・37部門)と産業一覧を生成する。 build_site.py から呼ばれる。
文章はデータからの機械的な生成で、事実(数値)のみ。解釈は既存の『ストーリー(仮説)』を転記し、仮説と明記する。
マークアップは templates/ にあり、ここでは表示する値(整形済みの文字列・座標)を用意して描画を呼ぶ。"""

import html
import json
import pathlib
import re
from types import SimpleNamespace

import pandas as pd

from _shell import breadcrumb_head
from _tpl import render

R = pathlib.Path(__file__).resolve().parents[2]
D = R / "data"

# 行き先の構成の分類(ラベル, 色)。順番が積み棒の並び順になる
DESTINATION_COLORS = {
    "他産業の材料・サービス": "#38bdf8",
    "家計消費": "#34d399",
    "設備投資・在庫": "#f59e0b",
    "政府（消費・公共投資）": "#a78bfa",
    "輸出": "#ef4444",
}


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


# ---------- データの読み込み


def load():
    """産業ページに使う CSV / JSON をまとめて読む。"""
    nodes = read_csv("nodes.csv", dtype={"code": str})
    edges = read_csv("edges.csv")
    return dict(
        n108=nodes[nodes.level == 108].set_index("code"),
        n37=nodes[nodes.level == 37].set_index("code"),
        ed=edges[(edges.level == 108) & (edges.type == "SUPPLIES")],
        ts=read_csv("sector_timeseries_108.csv", dtype={"code": str}).set_index("code"),
        an=read_csv("analysis_108.csv", dtype={"code": str}).set_index("code"),
        rk=read_csv("blue_ocean_ranking_108.csv", dtype={"code": str}).set_index("code"),
        ex=json.loads((D / "explorer_data.json").read_text(encoding="utf-8")),
        sim=json.loads((D / "similarity_map.json").read_text(encoding="utf-8")),
    )


# ---------- SVGグラフの座標計算(描画は templates/_charts.html.j2)


def stacked_bar_data(parts):
    """parts=[(ラベル, 割合, 色)] を、横積み棒の棒と凡例の座標にする。"""
    width = 640
    x = 0
    segments = []
    for _label, share, color in parts:
        seg_width = width * share
        if seg_width < 0.5:
            continue
        segments.append(
            dict(
                x=f"{x:.1f}",
                width=f"{seg_width:.1f}",
                color=color,
                label_x=f"{x + seg_width / 2:.1f}"
                if seg_width > 46
                else None,  # 幅が足りない棒には数字を入れない
                pct=f"{share * 100:.0f}",
            )
        )
        x += seg_width
    legend = []
    for i, (label, share, color) in enumerate(p for p in parts if p[1] >= 0.005):
        column, row = i % 3, i // 3
        legend.append(
            dict(
                x=column * 215,
                y=40 + row * 16,
                text_x=column * 215 + 13,
                text_y=48 + row * 16,
                color=color,
                label=label,
                pct=f"{share * 100:.0f}",
            )
        )
    return segments, legend


def column_chart_data(values, labels, color):
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
    return dict(width=width, height=height, color=color, label_y=height - 6, bars=bars)


# ---------- 108産業ページ


def destination_parts(row):
    """産業の製品の行き先(中間需要・家計・投資・政府・輸出)を、合計1の割合にして返す。"""

    def amount(column):
        return float(row.get(column, 0) or 0)

    raw = [
        ("他産業の材料・サービス", amount("intermediate_sales")),
        ("家計消費", amount("fd_民間消費") + amount("fd_家計外消費")),
        ("設備投資・在庫", amount("fd_民間固定資本形成") + amount("fd_在庫純増")),
        (
            "政府（消費・公共投資）",
            amount("fd_政府消費") + amount("fd_政府消費(社会資本等減耗分)") + amount("fd_公的固定資本形成"),
        ),
        ("輸出", amount("fd_輸出")),
    ]
    positive = [(label, max(value, 0), DESTINATION_COLORS[label]) for label, value in raw]
    total = sum(value for _, value, _ in positive) or 1
    return [(label, value / total, color) for label, value, color in positive]


def trade_rows(codes, amounts, shares, names):
    """主な販売先・仕入れ先の表の行(リンク, 金額(兆円), 割合)。codes は 'S108_xx' 形式。"""
    return [
        [industry_link(code[5:], names[code[5:]]), tril(amount), pct(share, 1)]
        for code, amount, share in zip(codes, amounts, shares)
    ]


def breadcrumb_for_industry(site_url, sector_id, sector_name, name):
    """108産業ページのパンくず(構造化データ)。"""
    return breadcrumb_head(
        [
            ("産業一覧", site_url + "/industries"),
            (str(sector_name), f"{site_url}/industry/{sector_id}"),
            (name, None),
        ]
    )


def build_industry_page(code, row, tables, page, palette, site_url):
    """108産業の1ページを書き出し、共有画像(OGP)用のデータを返す。"""
    L = tables
    sid = "S108_" + code
    name = short(row["name"])
    output = float(row.output)
    sector_id = "%02d" % int(row.parent37)
    sector_name = L.n37.loc[sector_id, "name"]
    analysis = L.an.loc[code]
    series = L.ts.loc[code] if code in L.ts.index else None
    edges = L.ed
    sell = edges[(edges.src == sid) & (edges.dst != sid)].sort_values("amount", ascending=False).head(6)
    buy = edges[(edges.dst == sid) & (edges.src != sid)].sort_values("amount", ascending=False).head(6)
    sell_rows = trade_rows(sell.dst, sell.amount, sell.share_of_seller_sales, L.names)
    buy_rows = trade_rows(buy.src, buy.amount, buy.share_of_buyer_cost, L.names)
    self_sales = edges[(edges.src == sid) & (edges.dst == sid)].share_of_seller_sales

    parts = destination_parts(L.n108.loc[code])
    top = max(parts, key=lambda part: part[1])
    segments, legend = stacked_bar_data(parts)

    growth = float(series.real_cagr_2015_2020) * 100 if series is not None else None
    growth_early = float(series.real_cagr_2011_2015) * 100 if series is not None else None
    trend = None
    if series is not None:
        outputs = [float(series.output_r11), float(series.output_r15), float(series.output_n20)]
        trend = dict(
            chart=column_chart_data(outputs, ["2011年", "2015年", "2020年"], palette["c"]["sky"]),
            growth_2011_2015=sg(growth_early),
            growth_2015_2020=sg(growth),
        )
    group = None
    if code in L.group_of:
        group_id = L.group_of[code]
        group = dict(id=group_id, name=L.blue_ocean[group_id]["name"])
    neighbors = [L.code_of.get(x) for x in L.sim_nodes[code]["nb"]]
    siblings = [c for c in L.n108.index if "%02d" % int(L.n108.loc[c].parent37) == sector_id and c != code]

    growth_text = (sg(growth) + "%/年") if growth is not None else "データなし"
    stats = [
        ["産出額（2020年）", tril(output) + "兆円"],
        ["実質成長（2015→20年）", growth_text],
        ["付加価値率", pct(float(analysis["付加価値率"]))],
        ["輸入依存度", pct(float(analysis["輸入依存度"]))],
    ]
    facts = render(
        "industry_facts.html.j2",
        name=name,
        sector_name=sector_name,
        output=tril(output),
        share=f"{output / L.total_output * 100:.1f}",
        growth=sg(growth) if growth is not None else None,
        sell_names=[short(L.names[i[5:]]) for i in sell.dst[:3]],
        buy_names=[short(L.names[i[5:]]) for i in buy.src[:3]],
    )
    body = render(
        "industry.html.j2",
        name=name,
        sector_id=sector_id,
        sector_name=sector_name,
        facts=facts,
        stats=stats,
        segments=segments,
        legend=legend,
        top_label=top[0],
        top_share=f"{top[1] * 100:.0f}",
        self_share=pct(float(self_sales.iloc[0]) if len(self_sales) else 0, 1),
        sell_rows=sell_rows,
        buy_rows=buy_rows,
        trend=trend,
        group=group,
        neighbors=[industry_link(c, L.names[c]) for c in neighbors if c],
        siblings=[industry_link(c, L.names[c]) for c in siblings],
    )
    description = re.sub(r"<[^>]+>", "", html.unescape(facts))[:150]
    page(
        f"industry/{code}.html",
        f"{name}の取引先・規模・成長｜Keizai Atlas",
        description,
        body,
        breadcrumb_for_industry(site_url, sector_id, sector_name, name),
    )
    return dict(
        id=code,
        title=name,
        kind="108産業の1つ｜" + sector_name,
        grp=int(L.group_of37.get(sector_id, 0) or 0),
        stats=stats,
        parts=[[label, round(share, 4), color] for label, share, color in parts],
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


def sector_trade_rows(edges, partner_key, node, nodes):
    """37部門の販売先・仕入れ先の表の行。partner_key は相手側('t'=販売先 / 's'=仕入れ先)。"""
    return [
        [
            {"href": f"industry/{e[partner_key]}.html", "text": nodes[e[partner_key]]["name"]},
            f"{e['v']:.1f}",
            f"{e['v'] / node['out'] * 100:.1f}%",
        ]
        for e in edges
    ]


def build_sector_page(sector_id, node, tables, page, site_url):
    """37部門の1ページを書き出し、共有画像(OGP)用のデータを返す。"""
    L = tables
    name = node["name"]
    children = L.kids_of.get(sector_id, [])
    all_edges = L.ex["edges"]
    sell = sorted(
        [e for e in all_edges if e["s"] == sector_id and e["t"] != sector_id and e.get("v")],
        key=lambda e: -e["v"],
    )[:6]
    buy = sorted(
        [e for e in all_edges if e["t"] == sector_id and e["s"] != sector_id and e.get("v")],
        key=lambda e: -e["v"],
    )[:6]
    group_name = L.group_names[node["grp"]]
    stats = [
        ["産出額（2020年）", f"{node['out']:.1f}兆円"],
        ["実質成長（2011→20年）", sg(node["cagr"]) + "%/年"],
        ["付加価値率", f"{node['va']:.0f}%"],
        ["輸入依存度", f"{node['imp']:.0f}%"],
    ]
    body = render(
        "sector.html.j2",
        name=name,
        group_name=group_name,
        output=f"{node['out']:.1f}",
        growth=sg(node["cagr"]),
        value_added=f"{node['va']:.0f}",
        export=f"{node['exp']:.0f}",
        consumption=f"{node['cons']:.0f}",
        import_dependence=f"{node['imp']:.0f}",
        stats=stats,
        sub_rows=[
            [
                industry_link(c["c"], c["n"]),
                f"{c['o']:.2f}",
                (sg(c["g"]) + "%") if c["g"] is not None else "−",
            ]
            for c in children
        ],
        sell_rows=sector_trade_rows(sell, "t", node, L.n37_nodes),
        buy_rows=sector_trade_rows(buy, "s", node, L.n37_nodes),
        stories=sector_stories(sell, L.n37_nodes) + sector_stories(buy, L.n37_nodes),
    )
    breadcrumb = breadcrumb_head([("産業一覧", site_url + "/industries"), (name, None)])
    page(
        f"industry/{sector_id}.html",
        f"{name}（37部門）の取引先・規模・成長｜Keizai Atlas",
        f"{name}（37部門の1つ）の2020年の産出額は{node['out']:.1f}兆円。主な販売先・仕入れ先、含まれる産業、取引の背景（仮説）。",
        body,
        breadcrumb,
    )
    return dict(
        id=sector_id,
        title=name,
        kind="37部門の1つ｜" + group_name,
        grp=int(node["grp"]),
        stats=stats,
        parts=[],
    )


# ---------- 産業一覧ページ


def build_index_page(tables, page, palette):
    """産業一覧(8つの大分類 > 37部門 > 108産業)を書き出す。"""
    L = tables
    groups = []
    for group_index, group_name in enumerate(L.group_names):
        ids = [i for i, n in L.n37_nodes.items() if n["grp"] == group_index]
        sectors = []
        for sector_id in sorted(ids, key=lambda i: -L.n37_nodes[i]["out"]):
            output = L.n37_nodes[sector_id]["out"]
            sectors.append(
                dict(
                    id=sector_id,
                    name=L.n37_nodes[sector_id]["name"],
                    output=f"{output:.1f}" if output < 10 else f"{output:.0f}",
                    industries=[industry_link(c["c"], c["n"]) for c in L.kids_of.get(sector_id, [])],
                )
            )
        groups.append(dict(color=palette["groups"][group_index], name=group_name, sectors=sectors))
    page(
        "industries.html",
        "産業一覧（37部門・108産業）｜Keizai Atlas",
        "日本の産業を8つの大分類・37部門・108産業に分けて、規模と取引先を見られる一覧。",
        render("industries.html.j2", groups=groups),
    )


# ---------- 全体


def prepare(palette):
    """ページ生成に使う表・辞書をまとめる(名前→コードの逆引き、37部門ごとの子産業など)。"""
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
    return L


def build(page, S, PAL, SITE_URL):
    """108産業・37部門・産業一覧のページを書き出し、ページのパス一覧を返す。"""
    tables = prepare(PAL)
    (S / "industry").mkdir(exist_ok=True)
    ogp_cards = []
    out_pages = []
    for code, row in tables.n108.iterrows():
        ogp_cards.append(build_industry_page(code, row, tables, page, PAL, SITE_URL))
        out_pages.append(f"industry/{code}")
    for sector_id, node in tables.n37_nodes.items():
        ogp_cards.append(build_sector_page(sector_id, node, tables, page, SITE_URL))
        out_pages.append(f"industry/{sector_id}")
    build_index_page(tables, page, PAL)
    (D / "ogp_cards.json").write_text(json.dumps(ogp_cards, ensure_ascii=False, indent=0), encoding="utf-8")
    return out_pages + ["industries"]
